---
name: fundus-zugriff
description: "Use when eine Faehigkeit fehlt: Skill-Fundus (Documents/GitHub + Werkstatt/Repos) durchsuchen."
---

# Skill-Fundus (MaxHirn/skills + Werkstatt/Repos) nutzen

`%USERPROFILE%\Documents\GitHub` ist der Skill-Fundus (**geklonte
Fremd-Repos**; seit 18.09.2026 dort). Achtung: der Ordner liegt AUSSERHALB
BrainFiles - nicht in der G:-Sicherung. Inhalt (Stand 22.09.2026): **398
eindeutige SKILL.md** in 15 Repos (568 Dateien, 170 byte-identische Kopien),
groesste: gbrain 223, financial-services 120, OmniRoute 75, kraken-cli 59
(offizielles Kraken-Skillpack), claude-plugins-official 31; ohne Skills:
data-mcp (reiner Daten-MCP) u.a.
**`Werkstatt/Repos/`** (die Bot-Klone): **505 eindeutige** in 22 Repos
(705 Dateien), davon 216 byte-identisch auch im Fundus (geprueft 22.09.2026).

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
   `MaxHirn/Wissen/Fundus-Index.md` (Fundus, 398 Skills, je Repo
   gruppiert) und `MaxHirn/Wissen/Fundus-Index-Werkstatt.md` (Werkstatt/Repos,
   505 Skills, mit `*(auch im Fundus)*`-Markern). Beide neu bauen: `-Index` am
   selben Skript - auch nach `git pull` in einem Klon. Die Pfade im Index sind
   relativ zur jeweiligen Wurzel (Fundus-Pfade ab dem Repo-Namen).

4. **Nach der Nutzung einordnen.** Fremd-Skills richten sich an fremde
   Werkzeuge und Pfade. Uebernehmen heisst: pruefen, auf Hermes-Werkzeugnamen
   und eigene Pfade umsetzen, danach als eigenen Skill unter
   `Agenten/Hermes/skills/<kategorie>/` ablegen - oder bewusst nur einmalig
   anwenden und nichts speichern.

5. **Klone aktuell halten:** der Hermes-Cron `repo-updates-check` (montags
   09:15, `no_agent`) meldet, welche Werkstatt/Repos hinter upstream
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
