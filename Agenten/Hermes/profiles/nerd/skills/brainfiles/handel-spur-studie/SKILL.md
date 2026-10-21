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

## Was eine Spur an Kosten traegt (Kosten-Wendepunkt)

Jede Auswertung endet mit der Frage, wie viel Gebuehr das Buch ueberhaupt traegt
- mehrere Spuren sind nur wegen einer Gebuehrenbefreiung (Abo, Pro-Tarif) positiv.
Die Rechnung ist eine Zeile und gehoert in jeden Bericht:

```
EV je Runde      = p*(C - f) - (1-p)*(R + f)
=> f_max         = p*C - (1-p)*R        # Gebuehr je Runde, ab der nur die Nullinie bleibt
```

R = mittlerer Stop-Abstand (Einstieg -> Stop) in Prozent, C = mittlerer
Ziel-Abstand, p = gemessene Trefferquote, f = Gebuehr JE RUNDE (Kauf + Verkauf).
Werkzeug: `Agenten/Handel/kosten_wendepunkt.py` (rein lesend) - **je JOURNAL eine
Zeile**, nicht je Ordner (ein Ordner fuehrt Basis/Mittel/knapp/weit/futures, ein
Sammel-glob zaehlt dasselbe Buch mehrfach), und umskalierte Altbestaende
(`*.falsch-skaliert-*`) nie mitzaehlen. Unter 8 Runden ist f_max ein Befund,
keine Messung.

Lesart: `f_max` deutlich unter der naechsten realistischen Runde (0,4 % fuer
Kauf+Verkauf ohne Abo) heisst, die Spur steht nur auf der Gebuehrenfreiheit -
das ausdruecklich sagen, denn sie kippt, sobald das Abo endet.

## Eine Spur OHNE geschlossene Runden beurteilen

Ausloeser: "analysiere Spur X", und im Journal stehen nur `zyklus`-Zeilen. Dann
ist keine Trefferquote, kein EV und kein Verdikt moeglich — aber sehr wohl eine
Aussage. Diese vier Schritte statt einer erfundenen Kennzahl:

1. **Bestand zaehlen, nicht Runden.** Je Buch (`zustand*.json`, je Risikostufe eine)
   Zahl der offenen Positionen, Summe des Einsatzes und den **unrealisierten** G/V
   ausweisen. Ein Buch mit `n` Einstiegen und 0 Ausstiegen liefert nur eine Aussage
   ueber den offenen Bestand — das ausdruecklich sagen.
2. **Die Entscheidung mit der REINEN Funktion nachrechnen, nie mit dem Schreibpfad.**
   Die Ausstiegslogik liegt als reine Funktion vor (hier
   `trailing_stop_strategie.ausstiegsgrund(p, kurs, jetzt, w)`, daneben
   `stop_preis_fuer`, `verkaeuflich`). Auf **Kopien** der Positionen aufrufen
   (`copy.deepcopy`) — die Funktion schreibt in das uebergebene dict
   (`hoechster_kurs`-Maximum) — und NIE `handeln.py --vorschau` als Probe nehmen:
   der Ausstiegspfad schreibt beim Erkennen sofort Journalzeilen und bucht die
   Position aus. Der Import braucht das venv der Spur (`nautilus_trader` steht im
   Kopf des Moduls) — sonst `ModuleNotFoundError` auf den ersten Import.
3. **Erreichbarkeit der Ausstiegsgeometrie pruefen — der billigste, schaerfste Befund.**
   Den seit Einstieg beobachteten Hoechststand gegen die Trailing-Aktivierung
   halten: +30 % Aktivierung bei beobachtetem Peak +8,5 % heisst Faktor 3,5 zu weit —
   das Trailing greift NIE, wirksamer Ausstieg ist allein die Frist. Damit ist die
   Spur faktisch "N Tage halten" und misst das nicht, was auf dem Etikett steht. Diese
   Rechnung gehoert in jeden Bericht ueber eine Spur mit Stop/Trailing — sie ist in
   Minuten zu machen und entscheidet ueber den Wert der ganzen Spur.
4. **Doppelte Arme sind EINE Wette, nicht Diversifikation.** Mehrere Arme mit
   derselben Signalquelle und demselben Instrument (oder Index-Abbildern davon) zu
   denselben Minuten: die Anzahl unabhaengiger Positionen ist EINS. Das im Bericht
   sagen, sonst liest der Leser vier Bestaetigungen, wo eine steht.

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
- **Zwangsschluesse sind keine Runden - in JEDEM Werkzeug, das Runden zaehlt.**
  Ein Ausstieg mit `herzschlag`/`zwangsschluss`/`notaus`/`buchbereinigung` im
  Grund ist die Folge eines Ausfalls oder einer Buchkorrektur, keine
  Handelsentscheidung; sie sitzen meist im Verlust und machen die Trefferquote
  kuenstlich schlecht. Die EINE Fassung ist `Agenten/Handel/stoerungen.py`
  (`ist_stoerung(grund)`, `teile_runden`). Wer ein neues Auswertungsskript baut,
  muss sie aufrufen - `auswertung_alle.py` tut es, eine eigene Neuentwicklung
  vergisst es gern und liefert dann ein falsches Verdikt. Gegenprobe: sind ALLE
  Ausstiege einer Spur Zwangsschluesse, hat die Spur **gar keine Messung** -
  das sagen, statt aus Fremdschliessen eine Quote zu erfinden.
- **Ein fehlendes Journal ist nicht automatisch ein Betriebsfehler.** Viele
  Spuren schreiben NUR Handelszeilen (kein Zyklus-Eintrag): ohne Signal gibt es
  keine Datei, und das ist der Normalfall. Zwei Faelle trennen - die Spur laeuft
  (Zustand heute/gestern angefasst) = "wartet auf das erste Signal"; die Spur
  laeuft auch nicht (Zustand alt/leer) = echter Fehler. Wer beides in einen Topf
  wirft, meldet einen Defekt, wo nur Ruhe ist.
- **Tests schreiben nur in Tempdateien** und belegen das mit einem Modulwaechter
  (Dateiliste + Groessen der Spurenordner vor/nach vergleichen). Ein Test, der
  ins echte Journal schreibt, verfaelscht das Buch - und faellt danach niemandem auf.
- **Ein geaendertes Eingangstor wirkt nur auf NEUE Positionen**; offene laufen
  unter ihrem gebuchten Stop und ihrer Frist aus. Das im Vorschlag nennen.

## Eine Kennzahl ist erst eine Messung, wenn das Modell sie nicht gesehen hat

Vor jeder Bewertung, die auf trainierten Modellen beruht (AUC, Trefferquote, EV),
zuerst fragen: **welche Zeilen hat das Modell beim Vorhersagen schon gesehen?**
Ein Lauf, der auf denselben Daten vorhersagt, auf denen er trainiert wurde, ist
keine Messung - der Abstand ist bei Kursdaten riesig (gemessen: AUC 0,83
in-sample gegen 0,51 walk-forward bei BTC 1 h).

Wer selbst nachrechnen will, hat dafuer einen fertigen, NICHT in den Dauerlauf
eingebundenen Pruefstand: `Werkstatt/intelligent-trading-bot` (venv fertig,
Kette `download` -> `merge` -> `features` -> `labels` -> `train` -> `predict`
-> `predict_rolling` -> `signals` -> `simulate`, Binance-Kurse oeffentlich mit
`api_key: "dummy"`). Er nutzt Binance und MetaTrader 5 - fuer den eigenen
OKX-/Kraken-Handel ist er ein Massstab, kein Orderweg.

Zahlen und Befehle: [[Handel/Lektionen]] Abschnitt 13.

## Hauswerkzeug

- `Agenten/Handel/filter_studie.py` (`--spur NAME`, mehrfach; `--json`), Ergebnis
  `filter_studie_ergebnis.json`. Tests: `Agenten/Handel/tests/test_filter_studie.py`,
  laufen aus dem `tests`-Ordner mit dem Spur-venv.
- Rezept (Regeln, Testfixture, Befehle, Whitelist):
  `references/filter-studie-rezept.md`.
