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

Seit dem Backtest-Fundament (s. unten) ist die Liste kurz. Was uebrig bleibt,
bleibt wirklich uebrig:

- **Alles, was im Betrieb passiert und nicht im Kurs steht:** Orderannahme, Teilmengen,
  Ablehnungen, Slippage in der eigenen Ordergroesse, Kontostand-Grenzen,
  Quote-Ticks. Der Backtest rechnet auf Kerzen - er zeigt die Signalqualitaet,
  nicht die Ausfuehrung.
- **Vorbild-/Wallet-Auswahl:** ohne Zeithalbierung und Mindestzahl Runden je
  Wallet ist es Nachschau-Auswahl (der Gewinner von gestern ist kein Kriterium).
- **Daten, deren Historie es frei nicht gibt** (Open Interest, Liquidationen,
  archivierte Schlagzeilen, Onchain nur wenige Tage, Options-Strike-OI). Dann
  bleibt nur der prospektive Weg: Schattenbuch mit den Alternativeinstellungen,
  mindestens 4 Wochen bzw. bis 30 Ausstiege je Zweig.

## Historisch nachrechnen (Backtest)

**Die Ausstiegsgeometrie IST rueckwirkend pruefbar** - ueber Kerzen, nicht ueber
das Journal. Das war frueher als unmoeglich vermerkt, weil die Preispfade nicht
journaliert werden; der Backtest braucht sie nicht, er fuehrt die Spur ueber
historische Kerzen neu.

```bash
cd Agenten/Handel
python historie_binance.py --auffuellen --instrumente BTC-USDC,ETH-USDC --takte 1H,4H
python replay.py --spur <spur> --lauf ganz        # ganze Historie
python replay.py --spur <spur> --gegenprobe       # Kern gegen backtest_prognose.py
python optimieren.py --spur <spur> --trocken      # Plan, rechnet nichts
python historie_probe.py --okx                    # zweite Boerse als Gegenprobe
```

Feed-Spuren (Marktquerschnitt) fahren mit `--feed` bzw. `--familie-c`, siehe
`references/backtest-fundament.md`.

Familie E (xperp) faehrt ueber OKX-Futures-Kerzen (`historie_okx.py`) und
`bot.py`; die Methode waehlt `--bot-methode {lage,trend,grid}` (Vorgabe
`trend`). Aufruf, Anforderungen, OKX-Unterschiede und Ausstiegslogik:
`references/backtest-fundament.md`, Abschnitt "Familie E".

**Vor jedem Lauf die Fahrbarkeits-Landkarte pruefen, nicht einzelne Spuren.**
Jede Spur muss in GENAU EINER von zwei Listen stehen: fahrbar oder mit Grund
vermerkt (`replay.NICHT_NACHRECHENBAR`). Eine Spur in keiner der beiden Listen
sieht fahrbar aus und scheitert erst beim Lauf - und eine Fahrweise in der
Tabelle ohne Route aus `main()` ist toter Code (gemessen: `SPUREN_TEIL_B` listet
rund zwanzig spur_buch-Spuren, `lauf_b()` ist gebaut, aber `main()` ruft es nie
auf; alle zwanzig laufen in den falschen Weg und melden "die Spur nennt kein
Instrument"). Die Landkarte programmatisch gegen `dauerlauf.SPUREN` UND
`auswertung_alle.SPUREN` vergleichen - Rezept, drei Fallen und der stehende
Auftrag dahinter unter `references/backtest-fundament.md`, Abschnitt
"Die Fahrbarkeits-Landkarte".

**Eine Messung ueber N Spuren und T Kerzen in EINEM Vordergrundaufruf reisst das
Werkzeug-Timeout, nicht die Rechnung.** Gemessen: sechs Spuren x 1200 Kerzen in
einem Aufruf liefen in den Timeout, ohne dass eine einzige Zahl zurueckkam. In
Haeppchen fahren (eine bis zwei Spuren je Aufruf), den Zwischenstand in eine
JSON-Datei schreiben und am Ende zusammensetzen - so ueberlebt das Ergebnis
einen Abbruch. Fuer den vollen Walk ohnehin Hintergrund + `persist_on_release`.

Fuenf Regeln, ohne die jede Zahl wertlos ist (Einzelheiten, Werkzeugfallen und
die Nachweisprozedur: `references/backtest-fundament.md`):

1. **Die Spur selbst fahren, nie nachbauen.** Modul ueber den PFAD laden und
   seine eigenen `pruefe_*`/`signal`-Funktionen rufen; eine zweite Umsetzung
   waere eine zweite Wahrheit, und optimiert waere dann die Nachbildung.
2. **Nichts nach aussen lassen.** `ereignis.lauf` (Bus-Meldungen aus dem
   Backtest), die `Q:`-Spiegelung, die Risikostufe und der Schreibpfad muessen
   stillgelegt sein; das mit einem Inventarvergleich vor/nach belegen.
3. **Die Uhr der Spur setzen** (`zeit_quelle`) und zu jeder Zeile den
   Kerzenstempel schreiben - sonst traegt das Journal die Wanduhr des Laufs und
   jede Zeitrechnung darauf ist still falsch.
4. **Ein rollierendes Fenster, das die `mindest_kerzen` der Spur respektiert.**
   Ein zu kleines Fenster laesst die Spur nie ein Signal bilden; der Lauf meldet
   dann "0 Runden", was wie ein Messergebnis aussieht.
5. **Gegenprobe gegen den bestehenden Rechner** (`backtest_prognose.py`) auf
   denselben Kerzen: der neue Kern muss Runde fuer Runde dasselbe liefern.

Merksatz: der Normalfall eines Backtest-Fehlers ist ein Ergebnis, das wie eine
Messung aussieht. "0 Runden" und "kein Hebel" sind zwei verschiedene Dinge -
vor dem Bericht die fuenf Gegenproben fahren, die in
`references/backtest-fundament.md` stehen. **Und die ZAHL, die die Anzeige zeigt,
ist nicht automatisch die gueltige:** die Ausgabe waehlt den Ordner mit den
meisten Zeilen, ein abgeloester Lauf gewinnt also weiter. Eine Zeile ohne
Zeitraum ist keine Messung — den Neulauf veranlassen, statt sie zu zitieren.

## Die Kennzahl pruefen, BEVOR man sie empfiehlt

Der Normalfall ist nicht, dass die Zahl falsch gerechnet ist — sondern dass sie
richtig gerechnet wurde aus einer falschen Eingabe. Belegt: eine Spur fuehrte als
beste des Hauses mit rund +17 % Rundenergebnis, 85 % Trefferquote und t um 15;
das Audit zeigte, dass der Einstiegspreis je (Instrument, Tag) **identisch
uebernommen statt geholt** war, 87 von 161 Runden auf **einem** Instrument lagen
und die Haltedauer dem Aufrufertakt folgte (Median 0,25 h bei 0,25 h Takt). Der
Excess der Runden unter einer Stunde wich um 15 Prozentpunkte vom Rest ab.

```bash
cd /c/Users/faupe/Documents/BrainFiles/Agenten/Handel && ./scanner/.venv/Scripts/python.exe spur_audit.py --spur <name>
```

Drei Merkmale, an denen eine Kennzahl zu schoen aussieht, BEVOR sie in eine
Empfehlung geht:
1. **Konzentration** — eine „diversifizierte" Bilanz, deren Runden zur Haelfte auf
   einem Instrument liegen, ist keine Streuung.
2. **Haltedauer gegen den Aufrufertakt** — eine Haltedauer auf der Scheduler-
   Periode misst den Scheduler, nicht die Strategie.
3. **Excess gespalten nach Haltedaauer** — weichen die Spalten stark ab, traegt der
   Gesamt-Excess die Auswahl, nicht die Spur.

**Und die Folge ziehen.** Wer eine Grenze, ein Budget oder eine Empfehlung auf
eine solche Zahl gestellt hat, nimmt sie zurueck — mit datiertem Vermerk in der
Wache. Eine niedrigere Obergrenze schliesst keine offene Position, sie verhindert
nur neue Einstiege.

## Fallen

- **Ein Altjournal verliert neue Spalten still.** `pos_kennung.spalten` haelt bei
  einer vorhandenen Journaldatei die **bestehende** Kopfzeile, und der Schreibpfad
  mit `extrasaction="ignore"` verwirft dann jedes zusaetzliche Feld: die Messung
  laeuft, rechnet und erreicht nie eine Zeile. Beim Erweitern eines Journals um
  Spalten (MAE/MFE, Haltetage) die Altbestande einmalig mitziehen — Kopfzeile
  ergaenzen, alle Zeilen erhalten, Sicherung `.bak-<datum>` — und danach die Zahl
  der Zeilen gegen die Quelle halten.
- **Ein gemeinsames Buch deckt viele Spuren mit EINER Aenderung.** Wer eine
  Buchform teilt (`spur_buch.py`), wirkt damit auf alle Spuren, die es nutzen —
  das ist der Hebel, es ist aber auch der Grund, warum dort kein Test fehlen
  darf. Spuren mit eigener Buchform (eigene Journalzeile, `richtung` statt
  `seite`, Positionsliste statt Einzelposition) sind eigene Eingriffe; sie
  grundsaetzlich als eigene benennen statt sie still zu ueberspringen.

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

## Eine Prognosequelle gegen die NULLINIE stellen

Ausloeser: ein Modell, ein Indikator oder ein Fremd-Repo wird als Signalquelle
vorgeschlagen ("koennen wir das auch schaffen?"). Untergrenze jeder Bewertung
ist die **Nullinie** — die Annahme „der naechste Kurs ist der letzte". Wer die
nicht schlaegt, hat nichts; sie ist kein Messziel, sondern die Ausscheidung.

Rezept (auf den eigenen Kerzen der Spur, z. B.
`Agenten/Handel/kerzen_BTC-USDT_1H_8760.json`, Format `[ts_ms, open, high, low,
close]`):

1. **Nicht ueberlappende Hold-outs steppen**, Kontext z. B. 400 Kerzen,
   Horizont 24, **mindestens 100 Fenster**. Ein Fenster ist kein Befund, zwei
   sind ein Muenzwurf mit Meinung.
2. Je Fenster DREI Werte erheben: Horizont-Richtung richtig (ja/nein), mittlerer
   Fehler in Prozent und die Nullinie desselben Fensters (Fehler der
   „letzter-Kurs"-Annahme). Nur der Vergleich je Fenster ist fair — die
   Nullinie schwankt mit der Volatilitaet des Fensters.
3. Gesamt: Anteil Fenster mit kleinerem Fehler als die Nullinie, mittlerer
   Fehler gegen mittlere Nullinie (Differenz in Prozentpunkten), Richtung je
   Kerze als Nebenmass.
4. **Ein generatives Modell braucht Proben-Mittelung.** `sample_count=1` ist die
   pessimistischste Einstellung; denselben Lauf mit 5 Proben fahren, sonst ist
   der Verriss nicht fair.
5. Zwischenstand fortlaufend in eine JSON-Datei schreiben, damit ein Abbruch die
   gerechneten Fenster nicht verliert.

Verdikt-Regel: Richtung ≈ 50 % UND Fehler ueber der Nullinie = **als Signal
wertlos** — das so sagen. Umgekehrt gilt: solange die Stichprobe klein ist,
lautet das Verdikt „Befund, keine Messung", nie „traegt".

In denselben Satz gehoeren die **Grenzen der Aussage**: geprueft sind EIN Modell,
EINE Reihe, ohne Nachtrainieren. Sonst liest der Nutzer ein Urteil ueber die
Gattung, wo eines ueber eine Einstellung steht.

Vorlage (nachbaubar, nicht importieren):
`Agenten/Hermes/cache/scratch/kronos_fenster.py` (100 Fenster) und
`kronos_fenster2.py` (Proben-Mittelung, Modellgroesse als Argument). Die Sonde
im Fremd-Klon nach der Messung wieder entfernen, die nachrechenbare Fassung im
Cache behalten und im Wiki verlinken.

## Eine fremde Strategie pruefen, bevor sie Spur wird

Ausloeser: "schau mal bei <Ideenquelle> nach neuen Strategien", "bauen wir das?".
Ergebnis ist ein Verdikt (traegt / Kandidat / verworfen) mit Zahlen von den
EIGENEN Kerzen - nie die Zahl der Quelle.

**Der Paperwert ist nicht der Handelswert.** Jede Strategie-Seite einer
Ideenquelle traegt neben der Paper-Kennzahl eine Gegenprobe auf fremden Daten,
und die beiden gehen weit auseinander (gemessen: Paper +7,65 % p.a. gegen
Gegenprobe CAGR −18,8 % bei 63 % Rueckgang). Immer beide lesen und beide nennen.
Ein Guete-Etikett wie "Confidence: Strong" gilt der Anomalie, nicht der
Handelbarkeit.

**Erst die Rundenzahl, dann die Guete.** In dieser Reihenfolge pruefen:

1. Signale pro Jahr aus der Regel AUSRECHNEN, nicht schaetzen.
2. Kante je Runde gegen die Gebuehr JE RUNDE stellen: die Kante muss groesser
   sein als der Rundlauf (Kauf + Verkauf).
3. Zeithalbierung: dasselbe Vorzeichen in beiden Haelften.
4. Erst danach bauen.

**Die Kante ist INSTRUMENTGEBUNDEN — und das Messinstrument ist der Aufbaugrund.**
Dieselbe Regel auf demselben Takt kann auf einem Instrument Geld verdienen und
auf einem anderen exakt nichts, bei praktisch gleicher Trefferquote. Gemessen an
adx_macd 15 min ueber 60 Tage bei 0,05 % je Seite: BTC 44 Runden / 29,6 %
Treffer / **+755,71 USD**, SOL 42 Runden / 28,6 % / **+1,61 USD**. Die Quote
unterscheidet sich um ein Prozentpunkt, das Ergebnis um das 470-fache.

Deshalb **vor dem Bau auf dem Instrument messen, das die Zielboerse
ueberhaupt handeln kann** — nicht auf dem, auf dem die Quelle gemessen hat. Das
ist keine Feinheit: der Aufbaugrund ist meist die Verfuegbarkeit (Kontraktgroesse,
Mindestmenge, Margin), und ein Instrument, das die Boerse nicht fuehrt, ist kein
Gegenstand einer Sparentscheidung. Widerspricht die Messung dem vorgeschlagenen
Instrument, wird das Instrument gewechselt und die Abweichung **benannt** — nicht
stillschweigend die Zahl des Auftraggebers uebernommen. Wer stattdessen beide
Instrumente nennt, schiebt die Entscheidung auf, statt sie zu treffen.

**Eine zweite Seite wird GEMESSEN, nicht angenommen.** „Long und Short
abwechselnd" ist eine eigene Regel mit eigenem Vorzeichen, und sie kann die
erste verschlechtern. Derselbe Bot auf Futures (mit Funding-Rate), dreimal
gefahren, nur die Seite unterschieden: long **-20,68 %**, short **-34,50 %**,
beides **-48,13 %**. Die kurze Seite verliert mehr als die lange, die Kombination
mehr als jede Seite einzeln — also wurde sie nicht gebaut, obwohl sie plausibel
klang. Und fuer zwei der drei Bots gab es darueber hinaus gar keine dokumentierte
Short-Regel: eine zu erfinden waere eine neue Strategie und keine Uebertragung.

**Wenn nur EINE Seite belegt ist**, wird sie so benannt und die zweite als offene
Entscheidung stehengelassen (Wortlaut: „trägt nur, wenn jemand die Regel
beschrieben hat — eine erfundene wäre eine andere Strategie"). Der Umstieg auf
Futures selbst bleibt trotzdem richtig, wenn er die Kosten senkt: er erzeugt
keine Kante, aber er macht eine vorhandene weniger untragfaehig — beides
getrennt ausweisen.

**Die Kosten wachsen mit der Rundenzahl, der Ertrag nicht.** Deshalb dieselbe
Idee in der traegsten Fassung messen: ein Tagesausbruch mit 4-6 Signalen/Jahr
ueberlebt die Gebuehr, dieselbe Familie mit einem Tag Haltedauer und 60+
Signalen stirbt an ihr. Netto p.a. bei drei Saetzen ausweisen (0,05 % / 0,1 % /
0,6 % je Seite) - der Kraken-Satz entscheidet ueber eine Kraken-Spur.

**Immer gegen Buy & Hold stellen.** Ein Kandidat, der weniger verdient und dafuer
den Rueckgang halbiert, ist eine Aussage ueber Risiko, nicht ueber Rendite - das
so sagen, sonst liest der Nutzer eine Renditeaussage, wo eine
Rueckgangsaussage steht. Und t < 2 bei unter 30 Runden heisst "Kandidat", nie
"traegt".

**Zeitmuster in zwei Schritten.** Bei Saisonalitaet (Tageszeit, Wochentag, Monat)
zuerst das PROFIL rechnen (Mittelwert und t je Stunde/Tag): es zeigt, ob die
Richtung der Quelle ueberhaupt existiert, bevor Zeit in die handelbare Regel
geht. Das Fenster der Quelle kann um eine Stunde verschoben sein (andere Boerse,
andere Zeitzone) - die eigene Messung entscheidet. Ein bestaetigtes Profil ist
noch keine Strategie: die Kante je Tag liegt oft unter dem Rundlauf.

Quellen lesen: `references/fremdstrategie-pruefen.md`.
Werkzeug: `Agenten/Handel/quantpedia_probe.py` (`stunde|fenster|donchian|vergleich`)
- rechnet auf `daten/historie/`, ohne Netz, jede Zahl nachvollziehbar.

## Mehrere Buecher vergleichen (Risikostufen, Arme)

Ausloeser: "Stufe A gegen Stufe B", "alle drei gegeneinander". Der naheliegende
Weg — die Summen nebeneinanderstellen — misst ZWEI Ursachen in einer Zahl.

- **Die Stufen sind unabhaengige Buecher, keine Skalierung derselben Trades.**
  Jede Stufe eroeffnet in ihren EIGENEN Zyklen; gemessen hatte die Basis bei
  einer Spur 20 geschlossene Runden, die groessere Stufe 11, bei einer anderen
  123 gegen 229. Eine groessere Summe kann deshalb aus "mehr je Runde" ODER aus
  "andere Trades" kommen. Vor jeder Gegenueberstellung sagen, dass zwei Buecher
  verglichen werden.
- **Auf die RUNDE normalisieren, nicht auf die Summe.** G/V je Runde (oder je
  Position in Prozent) ist die einzige Zahl, die den Groesseneffekt
  herausrechnet; die Summe gehoert daneben, mit dem Hinweis, dass sie den Einsatz
  mitzaehlt.
- **Paaren, wenn es um den Effekt geht.** Fuer "bringt die groessere Stufe
  mehr?" Runden nach Instrument und ueberlappendem Zeitfenster paaren — gleiche
  Bewegung, zwei Groessen. Ein Summenvergleich ist nur zulaessig, wenn beide
  Buecher dieselben Instrumente im selben Zeitraum gehalten haben.
- **Rauschen skaliert mit.** Ein Ein-Runden-Ergebnis ist auf jeder Stufe
  Rauschen, bei dreifacher Groesse dreifaches Rauschen: gemessen stand dieselbe
  Spur auf zwei Stufen mit je EINER Runde bei +254 und −103. Gegensaetzliche
  Vorzeichen auf je einer Runde beweisen, dass die Stufen nicht dieselben Trades
  machen — nicht, dass eine Stufe besser ist.
- **Erst ab 8 Runden je Buch** (dieselbe Schwelle wie ueberall) ist ein
  Stufenvergleich ein Befund, keine Messung. Eine frisch gestartete Stufe hat im
  ersten Zyklus schon Ausstiege: das sind ihre ersten Datenpunkte, nicht ihr
  Ergebnis.

## Hauswerkzeug

- `Agenten/Handel/filter_studie.py` (`--spur NAME`, mehrfach; `--json`), Ergebnis
  `filter_studie_ergebnis.json`. Tests: `Agenten/Handel/tests/test_filter_studie.py`,
  laufen aus dem `tests`-Ordner mit dem Spur-venv.
- Rezept (Regeln, Testfixture, Befehle, Whitelist):
  `references/filter-studie-rezept.md`.
- Historische Nachrechnung ueber Jahre statt Wochen, samt Parametersuche:
  `references/backtest-fundament.md` (`historie_binance.py`, `replay.py`,
  `optimieren.py`, Ausgabe in `auswertung_alle.py` unter "Backtest (historisch)").
  Dort auch der Zuschnitt fuer **Spuren ohne Kerzenreihe** (Marktquerschnitt:
  Top-Movers, Marktbreite, 1h-Welle, Funding) — mit den Fallen, die dort anders
  sind als im Kerzen-Walk (`kurse` gegen `daten`, Quote- gegen Basisvolumen,
  eigene Familie C). Dazu die drei Befunde des 29.09.2026: der **Kill-Schalter
  geht nie wieder auf** (Messung nur ueber `--setzen` in der Wachen-KOPIE), die
  Gegenprobe gegen eine **zweite Boerse** (OKX-Tagesgrenze UTC+8!) und die
  Grenze, dass **Ausstiege zum Kerzenschluss die Gewinner zu gut rechnen**.
