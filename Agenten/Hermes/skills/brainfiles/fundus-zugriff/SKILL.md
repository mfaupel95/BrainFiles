---
name: fundus-zugriff
description: "Use when eine Faehigkeit fehlt: Skill-Fundus in MaxHirn/skills durchsuchen."
---

# Skill-Fundus (MaxHirn/skills) nutzen

`MaxHirn/skills/` sind **geklonte Fremd-Repos**: 238 SKILL.md, davon **182
eindeutige** (56 byte-identische Kopien) in 10 Repos - financial-services 67,
OmniRoute 47, claude-plugins-official 31, cli 12, claude-code 10,
onchainos-skills 7, context7 5, Rest einzelne. Dazu rund 660 MB Repo-Inhalt.

Sie sind **absichtlich nicht** in die Hermes-Bibliothek importiert: ihre Namen
und Beschreibungen wuerden bei **jeder Anfrage** rund **14.700 Tokens** kosten.
Die geladene Bibliothek kostet nach dem Ausmisten 59 Skills / rund 1.200 Tokens
je Anfrage (vorher 127 / 3.000): 70 nie genutzte Skills liegen unter
`Agenten/Hermes/skills/.archive/` und kommen mit `hermes curator restore <name>`
zurueck. Vor jedem Import also erst `hermes curator usage` fragen. Dieser Skill
ist der einzige Preisposten des Fundus - sein Text wird nur bei Bedarf geladen,
die Fremdinhalte erst, wenn wirklich gebraucht.

## Vorgehen

1. **Suchen, nicht stoebern.** Ein Suchlauf statt eines Baumdurchgangs:

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File `
     "Agenten\Werkzeuge\fundus-suche.ps1" -Begriff "<suchwort>"  # aus der Repo-Wurzel
   ```

   Die Ausgabe nennt je Treffer Repo, Namen, Pfad und die erste
   Beschreibungszeile. Ohne `-Begriff`: Uebersicht je Repo. `-MitKopien` zeigt
   auch die zusammengefassten Doppelpfade, `-Max <n>` mehr Treffer.

2. **Erst dann lesen, und nur die eine Datei.** Den Trefferpfad mit
   `read_file` oeffnen - nie ein ganzes Repo oder mehrere SKILL.md laden.
   *Fertig, wenn* aus dem Fundus in der Sitzung nur die tatsaechlich genutzte
   Datei im Kontext liegt.

3. **Uebersicht fuer Menschen und fuer Agenten ohne Terminal:**
   `MaxHirn/Wissen/Fundus-Index.md` (alle 182 Skills, je Repo gruppiert,
   48 KB). Neu bauen: `-Index` am selben Skript - nach `git pull` in einem Repo.

4. **Nach der Nutzung einordnen.** Fremd-Skills richten sich an fremde
   Werkzeuge und Pfade. Uebernehmen heisst: pruefen, auf Hermes-Werkzeugnamen
   und eigene Pfade umsetzen, danach als eigenen Skill unter
   `Agenten/Hermes/skills/<kategorie>/` ablegen - oder bewusst nur einmalig
   anwenden und nichts speichern.

## Fallen

- **Nichts blind importieren.** Der etablierte Grundsatz steht in
  `skill-library-sync`: aus fremden Baeumen wird nichts uebernommen.
  Ein Symlink des Fundus in `Agenten/Hermes/skills/` hebelt genau diesen Schutz
  aus und kostet sofort die 14.700 Tokens je Anfrage.
- **Reihenfolge:** erst pruefen, ob die geladene Bibliothek oder `Wissen/`
  die Antwort schon hat - der Fundus ist die dritte Stufe, nicht die erste.
- **Das Skript gehoert nicht nach `Agenten/Routinen/`.** Jede `*.ps1` dort gilt
  als Routine und muss an den Bus angebunden sein, sonst reisst
  `tests/test_ende_zu_ende.py` die Meldung `ohne Bus-Anbindung`.
- **PowerShell ist case-insensitiv.** Ein Schalter `-Alle` und eine Variable
  `$alle` sind dieselbe Variable: die Zuweisung der Liste ueberschreibt den
  Schalter, und der Fundus schrumpft still auf einen Treffer. Schalter und
  Datenvariablen immer unterschiedlich benennen (`-MitKopien` / `$skills`).
- **Erfolg ist messbar.** `-Index` nennt Repos, eindeutige Skills, Dateien und
  Zeichen - Zahlen nachmessen statt Tokens zu schaetzen. Kein Treffer heisst
  meist falsche Schreibweise (Substring-Suche, keine Wortstammbildung).
