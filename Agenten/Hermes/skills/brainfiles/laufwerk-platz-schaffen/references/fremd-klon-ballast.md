# Fremd-Klone und Plugin-Ordner bewerten, dann entfernen

Gilt fuer Sammlungen wie `Werkstatt/repos-verschoben-aus-skills/`,
`Agenten/Hermes/plugins/`, `Agenten/Hermes/skills/*` (Fremd-Klone) und jeden
Ordner, der ein geklontes Fremd-Repo enthaelt. Ziel: die Zahl nennen, die weg
kann, **ohne** einen Ordner zu loeschen, den ein Werkzeug liest.

## 1. Bestandsaufnahme (eine Zeile je Ordner)

```bash
cd <sammlung>
for d in */; do
  n="${d%/}"
  s=$(du -sh "$d" | cut -f1)
  g=""; [ -d "$d/.git" ] && g="git"
  c=$(find "$d" -maxdepth 4 -name SKILL.md -not -path "*/.git/*" | wc -l)
  m=""
  [ -f "$d/plugin.yaml" ] && m="hermes-plugin"
  [ -f "$d/.claude-plugin/plugin.json" ] && m="$m claude-plugin"
  [ -f "$d/.claude-plugin/marketplace.json" ] && m="$m market"
  printf "%-32s %8s %-5s SKILLs:%-3s %s\n" "$n" "$s" "$g" "$c" "$m"
done
```

`-maxdepth 4` ist Untergrenze: Skills liegen in Unterordnern der Klone, eine
Zaehlung mit `-maxdepth 2` liefert falsche Nullen.

## 2. Nachweise vor dem Loeschen (kein Schluss aus dem Ordnernamen)

| Frage | Befehl | Was die Antwort heisst |
|---|---|---|
| Ist er ein benutztes Hermes-Plugin? | `unset PYTHONHOME PYTHONPATH; ./bin/hermes.exe plugins list --json` | `source: bundled` = steckt im Paket, Ordner unnoetig; `catalog:…`/Pfad = Ordner ist die Quelle |
| Fuehrt Hermes diesen Ordner als Installation? | `plugins/.install-metadata.json` (kleine Datei, direkt lesen) | Eingetragener `source` + `revision` = Hermes hält Revision/Pin darauf: **bleibt**, auch wenn `pinned: false` |
| Ist er die lebende Claude-Marketplace-Quelle? | `~/.claude/plugins/known_marketplaces.json` + `installed_plugins.json` (kleine Dateien, direkt lesen) | `installLocation` zeigt unter `~/.claude/plugins/marketplaces/…` — eine Kopie anderswo ist nicht die Quelle |
| Ist er versioniert oder gesichert? | `git status --porcelain --ignored <ordner>` in der Wurzel | `!!` = git-ignoriert, kein Commit-/Sicherungseffekt |
| Ist er ein anderer Klon derselben Sache? | `git -C <ordner> remote -v; git -C <ordner> log -1 --format='%h %ci'` | gleicher Remote + gleicher Commit = inhaltsgleicher Zwilling; einer von beiden kann weg |

## 3. Einordnung

- **weg**: kein Plugin-Marker, kein `SKILL.md`, eigenes `.git` mit Remote →
  re-clonbarer Ballast. Vorher den Remote in den Bericht schreiben (so ist die
  Rueckholung eine Zeile).
- **pruefen**: hat `SKILL.md` → kann Skill-Quelle sein. Erst vergleichen, ob die
  geladenen Skills Kopien oder Junctions dieses Ordners sind (Junctions mit
  `os.path.isjunction` pruefen; Python meldet sie nicht als Symlink).
- **bleiben**: Plugin-Marker, aktiver Katalogeintrag, oder Ordner mit
  Nutzerarbeit.

## 4. Loeschen mit Nachweis

Groesse vorher, `rm -rf` (oder `cmd /c rd /s /q` bei langen Pfaden), danach
`ls` des Elternordners, Groesse der Sammlung und freier Platz nachher. Die
Summe der geloeschten Ordner und die Zahl der uebrigen in den Bericht.
Nach dem Loeschen eines Zwillings: die **uebrig gebliebene** Kopie frisch
pruefen (`git log -1`, `git status --porcelain`) und das Ergebnis nennen —
sonst steht die Loeschung ohne Beleg da, dass die andere Kopie vollstaendig ist.

## 5. Werkzeugfallen

- `grep -rn` ueber die Sammlung reisst die Zeitgrenze, sobald ein 400-MB-Klon
  darin liegt, und liefert nichts. Auf die Wahrheitsdateien begrenzen:
  `grep -rIl --exclude-dir=plugins -e "plugins/" config.yaml profile.yaml`.
- Rekursives Lesen von `~/.claude` laeuft ebenfalls in die Grenze — die drei
  Index-Dateien (`known_marketplaces.json`, `installed_plugins.json`,
  `plugin-catalog-cache.json`) genuegen.
- JSON-Ausgaben in den Scratch-Ordner mit nativem Pfad schreiben; `/tmp/…` aus
  der Shell ist fuer `python` nicht vorhanden.
- Fremd-Klone in einem versionierten Baum muessen in der `.gitignore` gesperrt
  sein, sonst bricht `git add -A` an einem Klon ohne ausgecheckten Commit ab
  (Exitcode 128). Fruehwarnung: `git add -A --dry-run`.

## 6. Ein skill-tragender Klon: nur den Ballast schneiden

Ein Klon, aus dem geladene Skills stammen, wird nicht geloescht — er wird
verkleinert. Reihenfolge: erst `.git`, dann erst (nach Pruefung) der Rumpf.

**a) `.git` entfernen.** Meist der groesste Einzelposten (ein 828-MB-Klon: 570 MB
`.git`). Zwei Vorbedingungen, beide mit Belegen:

```bash
cd <klon>
git log --oneline origin/HEAD..HEAD | wc -l    # muss 0 sein: keine eigenen Commits
git status --porcelain                          # " D <pfad>" = Dateien wurden getrimmt
```

Die ` D`-Zeilen sind der Grund fuer den zweiten Blick: sie sagen, dass Dateien
aus dem Baum entfernt wurden. **Vor** dem Loeschen von `.git` pruefen, dass
diese Dateien anderswo liegen (z. B. `skills/.archive/<repo>/...`) — sonst ist
die Historie die letzte Kopie. Danach: `rm -rf .git`. Der Arbeitsbaum bleibt
vollstaendig stehen, Skills laden weiter; verloren geht nur `pull`/`diff`.

Ebenso wichtig: pruefen, ob eine **Routine diesen Baum vorwaerts spult**
(`grep -rIn --include=*.py --include=*.ps1 -e "<pfad>" Routinen/ Werkzeuge/`).
Ein Baum, den ein Update-Lauf per `git pull` pflegt, braucht sein `.git` — die
Skill-Baeume unter `Agenten/Hermes/skills/` werden von keinem Lauf erfasst
(`repos-updaten` deckt `Werkstatt`, der Fundus `MaxHirn/skills`).

**b) Rumpf nur nach Verweis-Pruefung.** Die Skills eines Klons zeigen oft in den
Rumpf hinein (Beispiel: drei Skills verwiesen auf `docs/openapi.yaml`,
`docs/frameworks/MCP-SERVER.md`, `src/lib/agentSkills/generator.ts` — damit war
`docs/` mit 114 MB Referenzmaterial, nicht Ballast):

```bash
grep -ohE "\.\./|scripts/[A-Za-z0-9_./-]+|src/[A-Za-z0-9_./-]+|docs/[A-Za-z0-9_./-]+" \
  <klon>/skills/*/SKILL.md | sort -u
```

Treffer heisst: Rumpf bleibt. Der eigentliche Skill-Ordner ist meist winzig
(4–16 KB); die Gigabyte stecken in `.git`, `docs/`, `src/`, `tests/`.

**c) Die Zahl, die zaehlt, ist die des Skill-Verzeichnisses, nicht die des
Laufwerks.** Nach dem Schnitt `hermes skills list` laufen lassen und die
Namen der zuvor geladenen Skills **einzeln** treffen (Tabelle umbricht lange
Namen — nach dem Anzeigenamen suchen, z. B. `MCP Integration`, nicht nach dem
Ordnernamen `mcp-integration`; ein `grep -c 0` ist sonst ein Fehlalarm).
Schlusszeile vergleichen: `N hub-installed, M builtin, K local — X enabled`.
