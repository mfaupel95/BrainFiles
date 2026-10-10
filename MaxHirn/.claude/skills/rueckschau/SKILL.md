---
name: rueckschau
description: Wertet die gespeicherten Claude-Sitzungen aus, um wiederkehrende Arbeit zu finden und daraus Skills abzuleiten. Benutzen bei "geh die Gespräche durch", "was haben wir schon gemacht", "was wiederholt sich", "wo verliere ich Zeit", "leite Skills ab", oder bevor ein neuer Skill entworfen wird.
---

# Sitzungen auswerten

Die Transkripte liegen unter `~/.claude/projects/<projekt>/*.jsonl`, eine Zeile
je Nachricht. **Nie von Hand durchlesen** — am 30.09.2026 waren es 390 Dateien
und 341 MB.

```
# aus der BrainFiles-Wurzel; Hermes vorher: cd "$HERMES_HOME/../.."
python Agenten/Hermes/skills/claude-code-imports/rueckschau/sitzungen_auswerten.py
```

Ausgabe: Zahl der Sitzungen, Anweisungen, Befehle, dazu ein Themen-Cluster mit
Anzahl. Optionen: `--seit 2026-08-20`, `--anweisungen` (jede Anweisung auf 170
Zeichen gekürzt), `--ausgabe ORDNER` (Volltexte in Dateien statt in den Kontext),
`--werkzeuge` (Aufrufe je MCP-Server und Skill), `--umwege` (Fehlersignaturen).

Gemessen am 30.09.2026: 390 Dateien, 832 Anweisungen (677 eigenständig),
11.735 Befehle, Laufzeit rund zwei Minuten.

## Wie man daraus einen Skill ableitet

**Der Umweg ist der Fund, nicht die Befehlshäufigkeit.** Die Befehlszahl zeigt,
WO gearbeitet wurde; erst die Fehlersignaturen zeigen, WORAN es hing:

```
python …/sitzungen_auswerten.py --umwege --seit 2026-09-01
  Modul nicht gefunden     41 Sitzungen / 14 Tage / 251 Treffer
  Zeilenden/Whitelist      54 Sitzungen / 14 Tage / 440 Treffer
  Zeitfenster/Timeout      52 Sitzungen / 13 Tage / 212 Treffer
```

Gezaehlt wird je Signatur die Zahl **verschiedener Sitzungen und Tage**: ein
Problem in 40 Sitzungen ueber 14 Tage ist ein Muster, in einer Sitzung ein
Vorfall. Beides zusammen ergibt den Kandidaten — die Haeufigkeit nennt das
Thema, der Umweg nennt den Inhalt.

Drei Filter, bevor ein Thema ein Skill wird:

1. **Kam es in mehreren Sitzungen vor?** Einmal ist ein Vorfall, dreimal ist ein
   Muster.
2. **Gab es beim zweiten Mal denselben Umweg?** Genau dieser Umweg ist der
   Inhalt des Skills — nicht das Vorgehen, das am Ende funktioniert hat.
3. **Existiert das Wissen schon in einer Notiz oder einem Skill?** Dann verweist
   der Skill darauf und wiederholt es nicht. Duplizierte Zahlen veralten getrennt.
   Vor dem Bauen die Bibliothek durchsuchen (`grep -rl "<stichwort>"
   Agenten/Hermes/skills --include=SKILL.md`) — am 30.09.2026 waren vier der
   fünf häufigsten Umwege bereits abgedeckt, nur einer hatte kein Zuhause.

## Fallen bei der Auswertung

**Die Hälfte der Anweisungen ist Mechanik.** „Continue from where you left off",
„Erneut versuchen", eingespielte Skill-Texte, Nachrichten anderer Sitzungen,
Fortsetzungs-Zusammenfassungen — das Skript filtert sie heraus (`RAUSCHEN`) und
verwirft Anweisungen über 2000 Zeichen (`MAX_ANWEISUNG`). Ohne diese Grenzen
zählt der Bericht Werkzeug-Ausgaben als Auftrag: die längste „Anweisung" war
gemessen 360.909 Zeichen lang. 1259 Anweisungen roh, 832 nach dem Filter.

**Die Themen-Liste (`THEMEN`) muss mit dem Betrieb mitwachsen.** Sie ist der
eigentliche Wert des Skripts — und sie veraltet: am 30.09.2026 fehlte „Hermes"
darin, obwohl es mit 63 Sitzungen das häufigste Thema war. Ein Thema, das fehlt,
lässt den Bericht genau dort untertreiben, wo am meisten gearbeitet wurde.

**Sitzungen liegen mehrfach vor.** Bei einem Fork trägt jede Kopie die volle
Vorgeschichte; die Anweisungen vom 05./06.08. erscheinen dadurch in vier
Sitzungsdateien wortgleich. Häufigkeiten über Anweisungen sind deshalb
unbrauchbar — **über Befehle und über Sitzungen zählen**, nicht über Nachrichten.

**Anweisungen enthalten Zugangsdaten.** In den Transkripten stehen API-Schlüssel
und Tokens im Klartext, weil Max sie eingetippt hat. Ausgabedateien gehören ins
Scratchpad, **nie** in den Vault und nie in einen Commit. Fällt beim Auswerten
ein Schlüssel auf, der noch gültig sein könnte: melden, nicht zitieren.

**Die Rückschau sieht nur Claude.** Sie liest `~/.claude/projects/`; die
Hermes-Sitzungen liegen in `Agenten/Hermes/state.db` und kommen hier nicht vor.
Für die Zeit ab 21.09.2026 (Hermes als Hauptagent) ist der Blick damit blind —
die Zahlen oben beschreiben die Claude-Zeit, nicht die Gegenwart.

## Danach

Neue Skills nach `Agenten/Hermes/skills/<rubrik>/`, mit dem Skill `skill`
(die Claude-Ablage `.claude/skills/` wird nicht mehr benutzt). Erkenntnisse über
**Arbeitsweise** gehören ins Wiki (`MaxHirn/Wiki/Lektionen/`), Erkenntnisse über
den **Bestand** in eine Wiki-Seite der passenden Rubrik (Skill `wiki-pflege`) —
Zahlen und Pfade dorthin, der Skill verweist darauf und wiederholt sie nicht.
Was offen bleibt, als Eintrag in `MaxHirn/Archiv/TASKS.md`.
