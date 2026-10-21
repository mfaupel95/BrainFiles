# Fremde Skills finden und einstufen (Scan-Rezept)

Zweck: "suche ab <pfade> nach noch nicht uebernommenen skills und weiterem" -
eine Bestandsaufnahme des unbekannten Raums, bevor ueber eine Uebernahme
entschieden wird. Rein lesend, nichts kopieren, kein Index-Umbau; Ergebnis
ist ein Bericht nach Ort getrennt plus TASKS-Eintraege mit Entscheidungsfrage.

## Bekannte Baeume (byte-identisch = bereits uebernommen)

- `C:\Users\faupe\Documents\BrainFiles\MaxHirn\skills` (Fundus)
- `...\Werkstatt` (Bot-Klon-Flotte; `O:\Werkstatt` ist die Junction auf
  denselben Baum - EIN Ort, nicht doppelt scannen)
- `...\Agenten\Hermes\skills` (geladene Hausbibliothek)
- `...\MaxHirn\.claude\skills`, `...\MaxHirn\.agents\skills`,
  `...\MaxHirn\.claude\skills-sicherung`, `...\MaxHirn\optional-skills`

## Scan-Ablauf

1. SHA-256 je SKILL.md der bekannten Baeume -> `known{hash: pfad}`. Junctions
   nicht verfolgen, ABER deren Ziele mit abgleichen (okx-*-Junctions im
   Skill-Baum zeigen auf `~/.agents/skills` - die dortigen Dateien sind fuer
   die Hausbibliothek geladen und gehoeren in die bekannte Menge).
2. `os.walk(followlinks=False)` ueber die Ziele (C:\Users\faupe, O:\Modelle,
   O:\Werkstatt) mit PRUNE = {.venv, venv, node_modules, .git, __pycache__,
   site-packages, .cache, .npm, .cargo, .rustup, Temp, tmp, blobs, manifests,
   dist, build, target, win-unpacked, .next, .nuxt, .turbo}. os.walk folgt
   den Windows-Junctions standardmaessig nicht; wersicherheitshalber
   `os.path.isjunction` pruefen, bevor ein Ordner betreten wird.
3. BrainFiles-Pfade aus dem Ziel-Scan ausschliessen (bekannter Baum).
4. Funde gruppieren: Ort = die ersten zwei Pfadsegmente hinter der Wurzel
   (z. B. `AppData/Local/copilot/marketplaces`). Erst gruppieren, dann
   klassifizieren - eine flache Liste von 6000+ Pfaden ist unlesbar.
5. Identitaet je Gruppe ziehen: `git remote -v`, `git log -1 --format=%ci %h`,
   erste README-Zeile, `description:` aus dem SKILL.md-Frontmatter. Das
   unterscheidet einen echten Klon von einem App-Bundle.
6. Ergebnis als JSON ablegen (cache/scratch), Bericht getrennt ausweisen:
   echte Kandidaten / bekannt-in-neuem-Gewand / Rauschen. Dann TASKS-Eintraege
   mit der Entscheidungsfrage (welche Sammlung, welcher Weg
   halten/finden/benutzen) - die Uebernahme selbst ist ein eigener Auftrag.

## Klassifikation

| Fundort | Bedeutung |
|---|---|
| O:\Werkstatt\<name> mit .git + plugins/ oder skills/ | ECHTER KANDIDAT (z. B. trailofbits-skills mit 83 SKILL.md) |
| ~/.claude/skills, ~/.agents/skills | Claude-/Codex-Benutzerebene der Haus-Skills; bekannte Namen = Spiegel, neuer Name = Kandidat |
| Documents\GitHub | parallele Klon-Flotte; gegen Werkstatt pruefen, dort Unbekannte = Kandidat |
| AppData\Local\copilot\marketplaces, AppData\Roaming\Code\agentPlugins, .codex\.tmp, .codex\plugins, .vscode\agent-plugins, .lmstudio | Install-/Cache-Kopien - Rauschen |
| ~/.claude/plugins/marketplaces/temp_<ts> | Ueberbleibsel fehlgeschlagener Marketplace-Setups (wiederholte Klone desselben Repos) - Rauschen |
| Elektron-App-Bundles (resources/), tests/-Verzeichnisse von Werkzeugen | tragen SKILL.md-Dateien, sind aber keine Sammlung (App-Bundle einer Desktop-App; Test-Fixtures eines Analyse-Tools) |
| Werkstatt\Ausgemustert, Werkstatt\Worktrees, Werkstatt\OmniRoute, O:\Modelle | bewusst weggelegt, Worktree-Kopien, produktiver Router-Klon, Modell-/Installationsbaum - kein Handlungsbedarf |

## Fallen

- **SKILL.md im Dateinamen ist kein Sammlungs-Indikator.** Erst die
   ORDNER-Identitaet (git origin/HEAD, README, Struktur) entscheidet; ein
   Elektron-App-Bundle kann 8 SKILL.md in resources/ tragen und ist trotzdem
   eine App.
- **Rohzaehlen nie als Befund melden.** Gemessen: 6.294 "neue" SKILL.md,
   davon ~90 % Install-/Cache-Kopien; die echten Kandidaten waren 3 Ordner in
   der Werkstatt-Wurzel plus je ein neuer Einzel-Skill in ~/.claude und
   ~/.agents. Erst die Klassifikation macht aus einer Anzahl eine Aussage.
- **Analyse-/Probe-Skripte mit Backslash-lastigen Pfaden nie als
   `python -c "..."` oder Heredoc durch die Werkzeugschicht schicken** -
   Escape-Ketten brechen mit 'unterminated string literal'. Skript per
   write_file in cache/scratch anlegen, dann ausfuehren; Backslash-Strings
   mit chr(92) bauen.
- **Hash-Abgleich ohne Junction-Ziele meldet Geladenes als NEU** (okx-*
   in ~/.agents/skills). Vor der Kandidaten-Liste pruefen, ob der Fundort
   Junction-Ziel einer bekannten Ablage ist.
- **Der Bericht ist der Arbeitsauftrag:** nach dem Scan nichts still
   uebernehmen - die Entscheidung, welche Sammlung auf welchem Weg
   (halten/finden/benutzen) eingebunden wird, gehoert als TASKS-Eintrag zu
   Max.