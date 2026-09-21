# GBrain lokal installieren (WSL2 archlinux)

GBrain (garrytan/gbrain) ist eine Gehirnschicht fuer Agenten. Der lokale
Install-Weg laeuft ueber den mitgelieferten `scripts/setup-in-agent.sh`
(harness `grok-bot` oder `muse`), der eine private Bun-Runtime + PGLite-Brain
in einem Root anlegt. Auf diesem Windows-Host: im WSL2-`archlinux` ausfuehren
(siehe SKILL.md, Abschnitt „Linux-gated Installer/CLI").

## Ablauf

1. Root waehlen: absoluter POSIX-Pfad mit existierendem Elternordner, leer
   oder abwesend fuer Neuinstallation, kein Symlink, kein Temp. Auf diesem
   Host `/workspace/gbrain` (WSL-Rootfs).
2. Helper holen und ausfuehren (im WSL):
   ```
   curl -fsSL https://raw.githubusercontent.com/garrytan/gbrain/latest-stable/scripts/setup-in-agent.sh -o /tmp/gbrain-setup.sh
   bash /tmp/gbrain-setup.sh --root /workspace/gbrain --harness grok-bot
   ```
   Braucht Bash, curl, unzip, git im WSL. `--pglite --no-embedding` ist der
   keyless-Modus (kein API-Key noetig fuer erste Fact/Recall-Runde).
3. **Suchmodus-Matrix aus dem Init an den Operator weiterreichen und die
   Wahl bestaetigen lassen** — nicht still den Default akzeptieren. Init
   waehlt `conservative` vor, wenn kein expansion-faehiger API-Key
   (Anthropic/OpenAI/Google) konfiguriert ist. Wechsel per
   `gbrain config set search.mode <conservative|balanced|tokenmax>`,
   verifizieren mit `gbrain search modes`. Kostenmatrix: 25x-Spreizung
   zwischen den Ecken; tokenmax schaltet LLM-Expansion ein (braucht spaeter
   einen Key).
4. Launcher: `/workspace/gbrain/bin/gbrain` — IMMER diesen absoluten Pfad
   nutzen, nie ein `gbrain` vom PATH. Von Windows aus:
   `wsl.exe -d archlinux /workspace/gbrain/bin/gbrain <cmd>`.
5. Round trip beweisen: harmlose randomisierte Phrase mit Provenance
   schreiben, in einem SEPARATEN Prozess zurueckholen:
   ```
   /workspace/gbrain/bin/gbrain remember "My setup test phrase is <zufall>" \
     --entity projects/gbrain-setup --provenance "explicit setup test, <JJJJ-MM-TT>" --json
   /workspace/gbrain/bin/gbrain recall projects/gbrain-setup --json
   ```
   Die Write-Meldung muss `status: inserted`/`committed` liefern, der Recall
   die exakte Phrase mit `source`.
6. Skill anhaengen: `instructions/gbrain-skill.md` als native Skill speichern
   und fuer den Bot aktivieren; in einer FRISCHEN Konversation die Phrase ohne
   Vorgabe abfragen und den CLI-Aufruf pruefen. `native_runtime` bleibt im
   Receipt `unverified`, bis dieser Test gelingt.
7. Backup in den BrainFiles-Baum (nicht in die WSL-Rootfs):
   ```
   /workspace/gbrain/bin/gbrain backup create --output /mnt/c/Users/faupe/Documents/BrainFiles/Agenten/gbrain-backups/brain-<JJJJMMTT>.gbrain-backup --json
   ```
   Die Live-DB liegt in der WSL-Rootfs, die die G:-Sicherung nie sieht — das
   Backup ist der einzige Weg, den Speicher in das Sicherungsschema zu
   bringen. Der Ordner ist git-ignored.

## Reparatur

- Runtime verschwunden/korrupt: `bash /workspace/gbrain/bin/gbrain-setup`
  (oder den Helper erneut mit demselben `--root`/`--harness` holen).
  Repariert die aufgezeichnete Bun-Version, erhaelt Fakten/Config.
- Receipt im Zustand `installing` mit korrupter Runtime: den im Receipt
  aufgezeichneten Recovery-Befehl ausfuehren — er repariert, ohne den
  Speicher neu zu initialisieren. Nicht den Root loeschen.
- `pglite_busy`: ein anderer Befehl haelt die DB; warten und erneut versuchen,
  nie den Lock entfernen.
- Upgrade nur explizit nach verifiziertem Backup: `gbrain-setup --upgrade`.

## Wichtige Pfade (WSL-Linux)

- Launcher: `/workspace/gbrain/bin/gbrain`
- Receipt: `/workspace/gbrain/.gbrain/agent-install/receipt.json`
- DB: `/workspace/gbrain/.gbrain/brain.pglite`
- Generierte Anweisungen: `/workspace/gbrain/instructions/{gbrain-skill,maintenance}.md`
- Backup-Ziel (Windows): `Agenten/gbrain-backups/`
