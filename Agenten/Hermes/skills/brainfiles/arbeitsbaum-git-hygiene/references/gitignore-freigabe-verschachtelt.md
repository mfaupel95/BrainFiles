# .gitignore-Freigabe fuer verschachtelte Ordner (z.B. profiles/*/skills)

Eine Datei wird nicht freigegeben, solange ein darueber liegendes Verzeichnis
gesperrt ist. Bei einer Sperre wie `Agenten/Hermes/profiles/*/skills/**` reicht
eine einzelne Freigabe `!Agenten/Hermes/profiles/*/skills/` NICHT - sie gibt
nur das skills/-Verzeichnis selbst frei, die Unterverzeichnisse bleiben durch
`skills/**` gesperrt und die Dateien darin unsichtbar.

## Das Muster, das funktioniert

```gitignore
# Sperre (bestehend)
Agenten/Hermes/profiles/*/skills/**

# Freigabe NACH der Sperre (spaetere Regel gewinnt)
!Agenten/Hermes/profiles/*/skills/
!Agenten/Hermes/profiles/*/skills/**/
!Agenten/Hermes/profiles/*/skills/**/SKILL.md

# Cache-/Sonderordner wieder sperren - mit **/ -Muster, nicht nur direkt
# unter skills/ (sie liegen unter skills/<skill>/.sicherung-junctions/)
Agenten/Hermes/profiles/*/skills/**/.sicherung-junctions/
Agenten/Hermes/profiles/*/skills/**/.hub/
Agenten/Hermes/profiles/*/skills/**/.curator_backups/
Agenten/Hermes/profiles/*/skills/**/.archive/
```

## Regeln

- **`!dir/` allein reicht nicht.** Fuer Dateien in Unterordnern braucht es
  `!dir/**/` (Unterverzeichnisse freigeben) UND `!dir/**/SKILL.md` (die
  Dateien). `!dir/**/` gibt nur die Verzeichnisse frei, nicht die Dateien
  darin - die bleiben durch die allgemeine Sperre gesperrt, bis die
  Datei-Freigabe sie hebt.
- **Cache-/Sonderordner-Sperren brauchen `**/`-Muster.** Ein Cache-Ordner
  liegt oft unter `skills/<skill>/.sicherung-junctions/`, nicht direkt unter
  `skills/`. Eine Sperre `skills/.sicherung-junctions/` matcht das nicht -
  die Dateien rutschen durch die `**/SKILL.md`-Freigabe. `skills/**/.sicherung-junctions/`
  sperrt beide Lagen.
- **Gegenprobe mit `git check-ignore -v` auf vier Faelle:** (1) die
  freizugebende Datei (exit 1 = frei), (2) eine Datei in einem
  Cache-Ordner (exit 0 = gesperrt), (3) eine Nicht-Ziel-Datei (z.B. README.md,
  exit 0 = gesperrt), (4) eine Datei in `.archive` (exit 0 = gesperrt).
- **`git status --porcelain` fasst untracked Ordner zusammen** - die echte
  Dateizahl zeigt erst `git status --porcelain -uall`. Damit pruefen, ob
  unerwartete Dateien (Nicht-SKILL.md, Cache-Kopien) durchrutschen.
- **Nur die Ziel-Dateiart freigeben, nicht alle `.md`.** Eine pauschale
  `**/*.md`-Freigabe zieht README/Hilfsdateien mit (hier 88,5 MB statt
  23,7 MB fuer SKILL.md allein). Erst die Groesse der Kandidaten messen
  (`find ... -printf '%s\n' | awk '{s+=$1} END {print s/1048576}'`), dann
  entscheiden.
- **Vor der Freigabe Secrets-Scan** ueber die freizugebenden Dateien
  (`grep -lE 'sk-[A-Za-z0-9]{20,}|-----BEGIN ... PRIVATE KEY-----|...'`).
  SKILL.md sind Prozedurwissen, aber eine pauschale Freigabe sollte nie
  versehentlich einen Schluessel mitziehen.
```
