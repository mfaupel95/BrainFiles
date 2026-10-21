---
name: handel-spur-studie
category: brainfiles
description: "Use when eine Handels-Spur mathematisch zu pruefen ist."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [handel, spuren, auswertung, statistik, brainfiles]
    related_skills: [handel-spuren, arbeitsbaum-git-hygiene, brainstorming]
---

# Handels-Spur rueckwirkend pruefen und Parameter vorschlagen

Fuer Auftraege wie "Spur mathematisch optimieren", "Filter pruefen", "traegt
Parameter X?". Ergebnis ist ein BELEGTER Vorschlag (Wert, Zeithalbierung,
Paritaet gegen die Spur) - ausdruecklich NICHT der geaenderte Parameter: das
Setzen in `wachen.json` ist eine eigene Entscheidung des Nutzers, und eine
`wachen.json` gehoert zur Stufe-1-Dateiengruppe.

## Ablauf

1. **Feldinventar zuerst.** Spalten von `handelsjournal.csv` und
   `ablehnungen.csv` der Spur lesen: welcher Hebel ist daraus beweisbar?
   Ein Merkmal, das nur fuer ABGELEHNTE Signale protokolliert wird, hat kein
   Ergebnis und ist rueckwirkend nicht pruefbar. Nicht pruefbare Hebel gehoeren
   als Grenze in die Spezifikation, nicht in die Umsetzung.
2. **Buchhaltung wiederverwenden, nie nachbauen.** Je Spur
   `<spur>/auswertung.py` ueber den PFAD laden
   (`importlib.util.spec_from_file_location`, eindeutiger Modulname wie
   `auswertung_<spur>`) - alle Spuren besitzen ein Modul `auswertung`, ueber
   `sys.path` gewaenne der zuletzt eingefuegte Ordner. Ausstiege ueber
   `<modul>.lade_ausstiege(pfad)`, Kostensaetze ueber `<modul>._kosten()`,
   Kennzahlen je Teilmenge ueber `buchauswertung.kennzahlen(aus, k)` (Felder
   `n`, `quote`, `netto_pct`, `brutto_pct`, `median_pct`, `gv_usd`).
3. **Zeithalbierung.** Ausstiege nach `zeit` sortieren; aeltere 60 % =
   Suchhaelfte, juengere 40 % = Gegenprobe. Eine Regel ist nur dann ein
   Vorschlag, wenn sie in BEIDEN Haelften dasselbe Vorzeichen hat UND besser ist
   als die Restgruppe. Mindestbesetzung 30 Ausstiege je Gruppe JE Haelfte -
   sonst lautet das Verdikt "nicht entschieden"; bei kleinen Buechern kein
   erfundenes Verdikt.
4. **Gegenprobe als eigene Regel mitfahren.** Eine Regel, die sich nicht
   umkehren laesst, ist kein Beleg: bei invertierter Datenlage muss das Verdikt
   kippen. Im synthetischen Testfall mit bekanntem Ausgang pruefen.
5. **Paritaetstor.** Gesamtzahl und Gesamt-Oe der Studie muessen exakt der
   Ausgabe der Spurauswertung entsprechen (`python <spur>/auswertung.py`) - im
   selben Lauf, weil der Dauerlauf das Buch staendig weiterschreibt. Weicht es
   ab, ist die Studie falsch, nicht die Spur.
6. **Bericht und Vorschlag.** Je Regel das Verdikt (traegt / nicht entschieden /
   verworfen) mit Anzahl und Oe je Haelfte, dazu die vorgeschlagenen
   Wachen-Werte und der ehrliche Vorbehalt. Unangetastet lassen: die Wachen der
   Spur, laufende Prozesse, fremde Dateien im Arbeitsbaum.

## Nicht rueckwirkend pruefbar

- **Ausstiegsgeometrie** (Stop-Hoehe, Trailing-Aktivierung): braucht die
  Preispfade je Position, die nicht journaliert werden. Weg: Schattenbuch mit den
  Alternativeinstellungen, mindestens 4 Wochen bzw. bis 30 Ausstiege je Zweig.
- **Vorbild-/Wallet-Auswahl:** ohne Zeithalbierung und Mindestzahl Runden je
  Wallet ist es Nachschau-Auswahl (der Gewinner von gestern ist kein Kriterium).

## Fallen

- **Die Stichprobe waechst waehrend der Arbeit** (Dauerlauf schreibt weiter):
  Zahlen aus zwei Laeufen zu verschiedenen Minuten sind nicht vergleichbar,
  Paritaet und Verdikt nur aus EINEM Lauf berichten.
- **Kosten dominieren das Ergebnis.** Oe vor und nach Kosten getrennt ausweisen:
  eine Filteraenderung kann in Wahrheit eine Slippage-Korrektur sein.
- **Tests schreiben nur in Tempdateien** und belegen das mit einem Modulwaechter
  (Dateiliste + Groessen der Spurenordner vor/nach vergleichen). Ein Test, der
  ins echte Journal schreibt, verfaelscht das Buch - und faellt danach niemandem auf.
- **Ein geaendertes Eingangstor wirkt nur auf NEUE Positionen**; offene laufen
  unter ihrem gebuchten Stop und ihrer Frist aus. Das im Vorschlag nennen.

## Hauswerkzeug

- `Agenten/Handel/filter_studie.py` (`--spur NAME`, mehrfach; `--json`), Ergebnis
  `filter_studie_ergebnis.json`. Tests: `Agenten/Handel/tests/test_filter_studie.py`,
  laufen aus dem `tests`-Ordner mit dem Spur-venv.
- Rezept (Regeln, Testfixture, Befehle, Whitelist):
  `references/filter-studie-rezept.md`.
