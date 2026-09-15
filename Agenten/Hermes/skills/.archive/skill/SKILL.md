---
name: skill
description: Macht aus einem erledigten Anwendungsfall eine wiederholbare Aufgabe — legt einen Skill nach Hausformat an, überarbeitet einen bestehenden oder trennt Verfahren, Wissen und Skript sauber auf. Benutzen bei "mach daraus einen Skill", "entwickel einen Skill", "das soll wiederholbar sein", "automatisier das", "schraube am Skill", oder am Ende jeder Aufgabe, die ein zweites Mal vorkommen wird.
---

# Aus einem Anwendungsfall eine wiederholbare Aufgabe machen

Dies geschieht **ungefragt**, nicht als Angebot. Am Ende einer Aufgabe, die ein
zweites Mal vorkommen wird, entsteht der Skill und die Ablage wird in einem Satz
gemeldet — nicht „ich könnte daraus einen Skill machen".

## 1. Zuerst: Gehört es überhaupt in einen Skill?

Drei Ablageorte, drei verschiedene Zwecke. Die häufigste Fehlentscheidung ist,
alles in den Skill zu schreiben:

| Art | Ort | Beispiel |
|---|---|---|
| **Verfahren** — wie man vorgeht, welche Fallen es gibt | `.claude/skills/<name>/SKILL.md` | „Ereignisanzeige gezielt abfragen" |
| **Wissen** — Zahlen, Zustände, Befunde mit Datum | `Wissen/<Thema>.md` (Skill `notiz`) | „RTX 3060 Ti, WMI meldet falsch 4 GB" |
| **Ausführung** — was ohne Nachdenken laufen soll | `Routinen/*.ps1`, `ArchivSuche/*.py` | `arbeitsbaum-pruefen.ps1` |

Ein Skill, der Zahlen enthält, veraltet still — die Notiz wird gepflegt, die
Kopie im Skill nicht. Deshalb: **Der Skill verweist, er wiederholt nicht.**
Verlinkt wird mit `[[Hardware]]`, damit Obsidian den Graphen aufbaut.

Nicht jeder Fall verdient einen Skill. Prüffragen:

- Kam es in **mehreren** Sitzungen vor? Einmal ist ein Vorfall.
- Gab es beim zweiten Mal **denselben Umweg**? Der Umweg ist der Inhalt.
- Deckt ein vorhandener Skill es schon ab? Dann dort ergänzen, nicht neu anlegen.

Die Häufigkeit wird gemessen, nicht geschätzt — mit dem Skill `rueckschau`.

## 2. Das Hausformat

```markdown
---
name: kurzwort
description: Was der Skill tut, in einem Satz. Benutzen bei "…", "…", "…".
---

# Titel

## 1. Der Befehl, der wirklich läuft
## 2. Die Fallen, die Zeit gekostet haben
## 3. Grenzen — was der Skill nicht tut
```

**Die `description` entscheidet, ob der Skill je gefunden wird.** Sie muss die
Worte enthalten, die Max tatsächlich benutzt — einschließlich der schiefen
diktierten Varianten. Nicht „Analyse von Systemereignissen", sondern „der PC ist
abgestürzt", „warum hängt", „wird nicht erkannt". Der Skill-Name ist ein
deutsches Kurzwort in Kleinbuchstaben, keine Abkürzung.

**Inhalt sind Befehle und Fallen, keine Erklärungen.** Ein Skill, der erklärt,
was ein Prozess ist, verbraucht Kontext ohne Wirkung. Wertvoll ist die Zeile
„`-ErrorAction SilentlyContinue` gehört dazu, sonst bricht die Abfrage ab" —
also genau das, was beim ersten Mal schiefging.

**Negativbefunde gehören hinein.** „Thumbnail-Cache geleert: 36,1 MB → 3 MB,
wirkungslos" spart beim nächsten Mal Stunden. Was nicht half, ist so wertvoll
wie was half.

**Zahlen gemessen, mit Datum.** „62.401 Dateien in 33 Sekunden", nicht „schnell".

## 3. Immer lokal ausführbar

Ziel ist, dass jede Operation ohne fremden Dienst läuft. Konkret:

- Vorhandenes Werkzeug benutzen statt ein neues zu erfinden — erst
  `ls ArchivSuche/*.py` und `ls Routinen/`, dann entscheiden.
- Was mehr als drei Schritte hat, wird ein **Skript**, nicht eine Befehlsfolge im
  Chat. Mit `-Testlauf`/`--dry-run` und, wo möglich, `-Rueckgaengig`.
- Keine absoluten Pfade (`C:\Users\...`) in Skills und Skripten — der Vault soll
  unverändert auf eine externe SSD umziehen können. Heimatverzeichnis über
  `$env:USERPROFILE` bzw. `os.path.expanduser("~")`.
- Lange Läufe: Zwischenstände speichern, **bevor** der teure Teil kommt. Externe
  Programme mit hartem Zeitlimit als Unterprozess.

## 4. Anlegen

Skills des Vaults liegen in `.claude/skills/<name>/SKILL.md`; ein zugehöriges
Skript kommt daneben (`<name>/skript.py`), ein zeitgesteuerter Ablauf nach
`Routinen/`. Skills unter `~/.claude/skills/` gelten überall, ziehen aber beim
Umzug nicht mit — Vault-Skills sind der Regelfall.

Nach dem Anlegen: mit dem Skill `sichern` committen und in einem Satz melden,
was entstanden ist und wodurch es ausgelöst wird.

## 5. Überarbeiten

Ein Skill wird geändert, sobald sein Verfahren beim Anwenden nicht mehr stimmte.
Das ist kein Nebenprodukt, sondern Teil der Aufgabe: **Fällt beim Arbeiten auf,
dass ein Skill einen überholten Stand behauptet, wird er sofort korrigiert und
die Korrektur gemeldet** — auch wenn es nicht zur laufenden Aufgabe gehört.

Beim Kürzen zuerst streichen, was allgemeines Weltwissen ist. Was bleibt, ist
das Projektspezifische: Pfade, Messwerte, Fallen, Grenzen.

Ein Umbau auf das Hausformat ist kein Ersatz für gewachsenen Inhalt. Beim
Anpassen von `archiv` am 11.09.2026 fielen 53 Zeilen weg — die gemessene Zahl,
die Optionen, eine Ausnahme; aufgefallen ist das nur, weil die Bytezahl
dastand. Deshalb vor und nach jedem Umbau vergleichen
(`(Get-Item <pfad>).Length`) und jede Differenz einzeln begründen. Geändert
wird in `.claude/skills/`, nie im Spiegel `.agents/skills/`: ein Umbau dort
erzeugt Drift gegen die Quelle und wird beim nächsten Abgleich überschrieben.
