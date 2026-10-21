---
name: fundus-zugriff
description: "Use when eine Faehigkeit fehlt: Skill-Fundus (Documents/GitHub + Werkstatt) durchsuchen."
---

# Skill-Fundus (Documents/GitHub + Werkstatt) nutzen

**Der Fundus liegt seit 18.09.2026 unter `%USERPROFILE%\Documents\GitHub`**
(ausserhalb BrainFiles; der fruehere Ordner `MaxHirn/skills` existiert nicht
mehr). Dazu die Bot-Klone `Werkstatt`. Der aktuelle Pfad steht IMMER in
`fundus-suche.ps1` (`$fundus`/`$werkstatt`), nicht in einer Notiz. Stand
11.10.2026: Fundus 1 SKILL.md, Werkstatt 34 Repos / 871 eindeutige
Skills / 1022 Dateien - nachmessbar mit dem `-Index`-Lauf des Skripts, nie
aus dem Gedaechtnis.

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
   pwsh -NoProfile -File \
     "Agenten/Werkzeuge/fundus-suche.ps1" -Begriff "<suchwort>"  # aus der Repo-Wurzel

   **Nur pwsh 7 - powershell.exe 5.1 meldet STILL 0 Treffer** (dort fehlt
   `Get-FileHash`, kein Fehlertext, falsche Aussage).
   ```

   Die Ausgabe nennt je Treffer Quelle (Fundus/Werkstatt), Repo, Namen, Pfad
   und die erste Beschreibungszeile; ein Vermerk `[auch im Fundus]` zeigt
   byte-identische Kopien im anderen Baum. Ohne `-Begriff`: Uebersicht je Baum
   und Repo. `-MitKopien` zeigt auch die zusammengefassten Doppelpfade,
   `-Max <n>` mehr Treffer.

2. **Erst dann lesen, und nur die eine Datei.** Den Trefferpfad mit
   `read_file` oeffnen - nie ein ganzes Repo oder mehrere SKILL.md laden.
   *Fertig, wenn* aus dem Fundus in der Sitzung nur die tatsaechlich genutzte
   Datei im Kontext liegt.

3. **Uebersicht fuer Menschen und fuer Agenten ohne Terminal:**
   `MaxHirn/Wissen/Fundus-Index.md` (Fundus) und
   `MaxHirn/Wissen/Fundus-Index-Werkstatt.md` (Werkstatt), je Repo
   gruppiert. Beide neu bauen: `-Index` am selben Skript - auch nach `git pull`
   in einem Klon; die Kopfzeile nennt die echten Repos-/Skill-Zahlen, die
   Doku im Skriptkopf darf nicht davon abweichen.

4. **Nach der Nutzung einordnen.** Fremd-Skills richten sich an fremde
   Werkzeuge und Pfade. Uebernehmen heisst: pruefen, auf Hermes-Werkzeugnamen
   und eigene Pfade umsetzen, danach als eigenen Skill unter
   `Agenten/Hermes/skills/<kategorie>/` ablegen - oder bewusst nur einmalig
   anwenden und nichts speichern.

5. **Klone aktuell halten:** der Hermes-Cron `repo-updates-check` (montags
   09:15, `no_agent`) meldet, welche Werkstatt hinter upstream
   zurueckliegen; nach einem `git pull` den `-Index` neu bauen lassen.

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
- **PowerShell 5.1: `.Count` auf einem Einzelobjekt aus der Pipeline ist
  LEER** (gemessen 16.09.2026) - Gruppen mit `@(...)` erzwingen, sonst
  stehen 1-Skill-Repos als "(0)" da. Ebenso: `@("# " + $var, ...)` - das
  Komma gewinnt gegen das Plus und der ganze Kopf wird EIN String; die
  Titelzeile vorher in eine Variable legen.
- **Ohne `-Encoding UTF8` liest `Get-Content` UTF-8-Dateien als ANSI**
  (Mojibake, gemessen an chinesischen Skill-Beschreibungen am 16.09.2026).
- **Erfolg ist messbar.** `-Index` nennt Repos, eindeutige Skills, Dateien und
  Zeichen - Zahlen nachmessen statt Tokens zu schaetzen. Kein Treffer heisst
  meist falsche Schreibweise (Substring-Suche, keine Wortstammbildung).
