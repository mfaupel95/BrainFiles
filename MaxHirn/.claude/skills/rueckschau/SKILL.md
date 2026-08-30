---
name: rueckschau
description: Wertet die gespeicherten Claude-Sitzungen aus, um wiederkehrende Arbeit zu finden und daraus Skills abzuleiten. Benutzen bei "geh die Gespräche durch", "was haben wir schon gemacht", "was wiederholt sich", "wo verliere ich Zeit", "leite Skills ab", oder bevor ein neuer Skill entworfen wird.
---

# Sitzungen auswerten

Die Transkripte liegen unter `~/.claude/projects/<projekt>/*.jsonl`, eine Zeile
je Nachricht. **Nie von Hand durchlesen** — 53 Sitzungen sind 74 MB.

```
.venv\Scripts\python.exe .claude\skills\rueckschau\sitzungen_auswerten.py
```

Ausgabe: Zahl der Sitzungen, Anweisungen, Befehle, dazu ein Themen-Cluster mit
Anzahl. Optionen: `--seit 2026-08-20`, `--anweisungen` (jede Anweisung auf 170
Zeichen gekürzt), `--ausgabe ORDNER` (Volltexte in Dateien statt in den Kontext).

Gemessen am 28.08.2026: 53 Sitzungen, 362 Anweisungen, 4.017 Befehle — die
Auswertung lief in unter zehn Sekunden.

## Wie man daraus einen Skill ableitet

**Die Befehlszahl ist das harte Signal, nicht die Erinnerung.** Ein Thema, das
sich subjektiv oft anfühlt, kann fünf Befehle haben; „Git/Sichern" hatte allein
seit dem 20.08.2026 **103**. Aus dieser Rangfolge entstanden am 28.08.2026 die
Skills `system`, `verbindungen`, `vergleich` und `sichern`.

Drei Filter, bevor ein Thema ein Skill wird:

1. **Kam es in mehreren Sitzungen vor?** Einmal ist ein Vorfall, dreimal ist ein
   Muster.
2. **Gab es beim zweiten Mal denselben Umweg?** Genau dieser Umweg ist der
   Inhalt des Skills — nicht das Vorgehen, das am Ende funktioniert hat.
3. **Existiert das Wissen schon in einer Notiz?** Dann verweist der Skill darauf
   und wiederholt es nicht. Duplizierte Zahlen veralten getrennt.

## Fallen bei der Auswertung

**Die Hälfte der Anweisungen ist Mechanik.** „Continue from where you left off",
„Erneut versuchen", eingespielte Skill-Texte, Nachrichten anderer Sitzungen —
das Skript filtert sie heraus (`RAUSCHEN`). Ohne den Filter wirken die Themen
verzerrt: 362 Anweisungen, aber nur 200 eigenständige.

**Sitzungen liegen mehrfach vor.** Bei einem Fork trägt jede Kopie die volle
Vorgeschichte; die Anweisungen vom 05./06.08. erscheinen dadurch in vier
Sitzungsdateien wortgleich. Häufigkeiten über Anweisungen sind deshalb
unbrauchbar — **über Befehle zählen**, nicht über Nachrichten.

**Anweisungen enthalten Zugangsdaten.** In den Transkripten stehen API-Schlüssel
und Tokens im Klartext, weil Max sie eingetippt hat. Ausgabedateien gehören ins
Scratchpad, **nie** in den Vault und nie in einen Commit. Fällt beim Auswerten
ein Schlüssel auf, der noch gültig sein könnte: melden, nicht zitieren.

## Danach

Neue Skills nach `.claude/skills/`, mit dem Skill `skill`. Erkenntnisse über
Arbeitsweise (nicht über einen Einzelfall) gehören in die globale `CLAUDE.md`,
Erkenntnisse über den Bestand in eine Notiz unter `Wissen/`.
