---
name: handelsspur-anlegen
description: "Use when eine neue Handelsspur gebaut wird."
version: 0.1.0
author: Hermes
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [Handel, Spur, Anlegen, Buch-Spur, Tests]
    related_skills: [handel-spuren, okx-orderweg-diagnose, handel-spur-studie, dauerprozess-bewachen]
---

# Eine neue Handelsspur anlegen

Der Weg von "bau mir einen Agenten, der X handelt" bis zur Spur, die im
Dauerlauf laeuft und ausser Haus gespiegelt ist. Gilt fuer jede neue Spur in
`Agenten/Handel/`.

**Abgrenzung:** die TIEFE Verdrahtungspruefung (Bus-Anbindung, Wachen, Auswertung)
und alle vorhandenen Spuren stehen in `handel-spuren`; eine neue Spur baut man
aber nach dem Geruest hier. Eine bestehende Spur aendern: `handel-spuren`.

## Wann

- "bau einen Agenten/Bot, der <Instrument> handelt, sobald <Bedingung>"
- "neue Spur", "weitere Strategie", "dieselbe Idee mit anderen Parametern"
- eine Signalidee soll Papierdaten sammeln, ohne gleich live zu gehen
- eine BESTEHENDE Spur soll eine ZWEITE Messung bekommen (weichere Tore, andere
  Ausstiegsform), ohne ihr Hauptbuch anzufassen — Schattenarm, Rezept in
  `references/schattenarm.md`
- eine Spur laeuft LIVE und soll mit anderen Parametern weiterlaufen, ein
  Schutz-Stop nachgezogen oder eine Wache eingerichtet werden —
  `references/live-lauf-betreiben.md`

## 1. Bauform waehlen (zuerst entscheiden)

**Buch-Spur ueber `Handel/spur_buch.py`** ist der Standard fuer alles, was aus
Signalen Einstiege macht: Buch, Ratsche, Risiko-Vorfilter, Groessenfaktor,
Live-Sperrenkette, Spiegelung und Ereignis-Meldung liegen dort EINMAL fuer alle
Spuren. Die Spur liefert nur Daten und ein Signal. Nur wer davon abweicht
(Eigene Buchhaltung, mehrere Buecher, Boersen-Node), baut eigenes — dann aber mit
denselben Feldnamen im Journal.

**Spurfamilie mit EINEM Kern** ist die dritte Bauform: mehrere Regeln, die sich
nur in der Rechnung unterscheiden (klassische Kursregeln aus Vorlagen, Varianten
derselben Idee). Dann liegt die Rechnung in EINEM Modul im Handel-Ordner —
Indikatoren, je Regel `einstieg(k, w)` und `ausstieg(k, seite, w)` als REINE
Funktionen, ein `REGELN`-Dict und ein gemeinsames `spur_main(name, ordner)` —
und jede Spur ist ein Zweizeiler, der `spur_main("<name>", HIER)` ruft. Buch,
Ratsche, Spiegelung und Vorfilter bleiben in `spur_buch.py`; der Kern ersetzt
nur das Signal. Warum: acht Kopien derselben Buchhaltung sind acht Stellen fuer
denselben Fehler. Die reinen Funktionen machen die Familie offline pruefbar.

## 2. Der Vertrag einer Buch-Spur (drei Funktionen, sonst nichts)

```python
quelle(w)   -> (daten, kurse, fehler)     # daten: {inst: {...}}, kurse: {inst: preis}
signal(d, w) -> "long" | "short" | None    # je Instrument, rein rechnend
spur_buch.zyklus(ordner, quelle, signal, modus, ereignis_name="handel/<spur>")
```

- `zyklus()` macht Ratsche, Ausstiege, Einstiege, Vorschau, Kill-Switch,
  Spiegelung und den Ereignisnamen (`handel/<spur>` WOERTLICH uebergeben — der
  Bus-Anbindungstest prueft genau diese Zeichenkette).
- Stop und Ziel kommen aus der `wachen.json`, nicht aus dem Signal:
  `einstieg()` wird mit `stop_pct=None` gerufen. Wer den Stop aus der Signallogik
  will, rechnet ihn in Prozent um und legt ihn in die Wachen — eine zweite
  Stop-Quelle neben der Buchfuehrung ist eine zweite Wahrheit.
- Ein optionaler vierter Baustein `ziel(daten, w)` liefert ein ZIEL ALS MARKTPUNKT
  (z. B. eine Optionswand); ein Ziel hinter dem Einstieg wird abgelehnt.

## 3. Nachbarmodule laden (Fallentraechtig)

Fremde Hausmodule ueber den PFAD laden, nicht per `sys.path`-Eintrag im Modulnamen:

```python
spec = importlib.util.spec_from_file_location("okx_<spur>", pfad)
modul = importlib.util.module_from_spec(spec); spec.loader.exec_module(modul)
```

`spec_from_file_location` mit einem EIGENEN Modulnamen verhindert, dass ein
gleichnamiges Modul aus einem Nachbarordner gewinnt. Trotzdem brauchen die
Nachbarn ihre ORDNER im Suchpfad, weil sie sich untereinander per Kurznamen
importieren (`xperp/indikatoren.py` holt `cvd`, `scanner/okx.py` seine
Geschwister):

```python
for _o in (HIER, HANDEL / "xperp", HANDEL / "scanner"):
    if str(_o) not in sys.path:
        sys.path.insert(0, str(_o))
```

Ohne das scheitert der Start mit `ModuleNotFoundError: No module named 'cvd'` —
und zwar erst beim Laden des Nachbarn, also NACH dem eigenen Import.

## 4. `wachen.json` — Zahlen, keine Schwellen im Code

Pflichtfelder einer Buch-Spur: `_zweck`, `_quelle`, `_regel`, `_kein_live`,
`waehrung`, `boerse`, Instrument/Parameter (z. B. `instrument`, `kerzen_zeitrahmen`,
Indikatorgroessen), `handel_erlaubt: false`, `freigabe: {erfuellt: false}`,
`herzschlag_max_minuten: 180`, `risiko_je_position_usd`, `max_offene_positionen`,
`max_pro_trade_usd`, `max_gesamt_usd`, `stop_prozent`,
`pflicht_stop_prozent_min/max`, `ziel_r_vielfaches`, `gebuehr_taker`,
`risikovorfilter: true` mit Fenster und Grenzen, `drawdown_halbierung_usd`,
`kill_switch_gesamt_usd`, `journal_zweitziel: "Q:\\Handel_Journal\\<spur>"`.

- `drawdown_halbierung_usd` = **1.0 x Buchrisiko** (`risiko_je_position_usd` x
  `max_offene_positionen`) als ausdruecklicher BETRAG, nicht als Prozentwert einer
  fremden Groesse.
- Neue Spur heisst **Papier**: `handel_erlaubt: false`, `freigabe.erfuellt: false`,
  und `--live` verweigert mit einem Grund, der NICHT das Wort "Freigabefenster"
  traegt — sonst liest der Dauerlauf ihn als Freigabebitte.

- **Die Position muss beim EIGENEN Stop baubar sein:**
  `risiko_je_position_usd / (stop_prozent / 100) <= max_pro_trade_usd`. Liegt
  `max_pro_trade_usd` unter `risiko / pflicht_stop_prozent_min`, deckelt ein Stop
  am unteren Rand das Risiko still — das ist ein Befund zum Melden, nicht ein
  stiller Zustand.
- `mindest_kerzen` deckt den **laengsten** Indikator der Regel, abgeleitet aus den
  Feldern selbst: `max(langsam_n, signal_n, bb_n, kanal_ein_n, rsi_n,
  trend_n + steigung_n)`. Wer die Zahl fest eintraegt, bricht sie beim naechsten
  Parameterwechsel.

## 5. Verdrahten (in dieser Reihenfolge)

1. **`dauerlauf.SPUREN`** — der einzige Ort, der sagt, was laeuft:
   `"<spur>": {"ordner": "<spur>", "waehrung": "USD", "skript": "handeln.py"}`.
   Erst danach zaehlen `spiegelstand.py` und die Auswertungen die Spur mit.
2. **`.gitignore`-Freigabeliste** — vier Eintraege (`*.py`, `*.md`, `wachen.json`,
   `tests/*.py`) und `zustand.json` + `handelsjournal.csv` ausdruecklich GESPERRT.
   Gegenprobe nach jedem Anlegen:
   `git check-ignore -v <spur>/zustand.json` **muss** die Sperre nennen und
   `git ls-files 'Agenten/Handel/*/zustand*.json'` **muss leer** sein.
3. **`README.md`** der Spur: Regel, Groessen, Buch/Ausstieg, Aufrufe, und was
   bewusst noch fehlt.
4. **Sofort committen, auch wenn die Spur noch nie gehandelt hat.** Eine neue
   Spur ist eine Handvoll ungetrackter Dateien; die Routine
   `fremdarbeit-einziehen.ps1` greift alles, was laenger als ~30 min unberuehrt im
   Baum liegt, und committet es als `Andere Sitzung <fremd@local>` — inhaltlich
   richtig, aber falsch beschriftet und von der eigenen Arbeit nicht mehr zu
   trennen. Erst stagen (namentlich, nie `git add -A`), dann committen, dann
   `git show --stat` gegen die eigene Pfadliste lesen.

Fuer eine Spur, die auf den BUS meldet oder in Auswertung/Tagesbericht auftauchen
soll, danach die Verdrahtungsstellen aus `handel-spuren` abarbeiten (Bus-Familie,
Ratschenteil, Auswertungsfamilie, Bericht-Holer) — sonst laeuft sie, ist aber
unsichtbar.

## 6. Tests (die Regel, nicht den Datenlauf)

Ablage `<spur>/tests/`, Aufruf **immer aus diesem Ordner**:
`python -m unittest test_<spur>` (aus dem Spurenordner scheitert discover mit
"Start directory is not importable").

- **Je Fall ein Test:** Signal feuert / feuert nicht, zu wenig Daten, Filter greift,
  Wachenplausibilitaet (Ratsche = Buchrisiko, Stop innerhalb min/max, Zweitziel auf Q:).
- **Fixtures SUCHEN, nicht raten.** Wenn die Regel "genau am letzten Wert" greift
  (Trendwechsel, Schwellen), gibt es Serien, die das treffen — die Parameter
durchprobieren und die gefundenen Zahlen in den Test schreiben, mit einem Satz
Herkunft. Eine willkuerliche Reihe prueft die Laune der Reihe, nicht die Regel.
- **Modulwaechter:** die reinen Funktionen duerfen keine Datei anlegen
  (Ordner vorher/nachher vergleichen). Tests, die Buchfunktionen direkt rufen,
  schreiben sonst in das ECHTE Journal der Spur.
- **Kein Test darf die BOERSE anfassen - und die Attrappe muss an der UNTERSTEN
  Schicht sitzen.** Eine Attrappe fuer die hochwertige Funktion (`markt_kauf`)
  reicht NICHT: die Spur ruft darin weiter innen echte Abfragen
  (`gefuellte_menge` -> `QueryOrders`, Stop-Pruefung), und der Test spricht
  trotzdem mit der Boerse - bei `echt=True` heisst das: er KANN kaufen. Zwei
  Massnahmen zusammen: die hochwertigen Funktionen ersetzen UND einen
  Stolperdraht auf den Transport legen (`kraken._roh_privat` bzw. `okxf._roh`),
  der jede signierte Abfrage mit `AssertionError` abbricht und den Methodennamen
  sammelt. Muster: `kraken/tests/test_beleg_tor.py`. Nebeneffekt: die Suite
  laeuft in 0,2 s statt 22 s, weil die echten Wiederholversuche wegfallen. Wer
  nur die Attrappe patcht, merkt davon nichts - der Test ist gruen und hat
  draussen gefragt.
- **Eine Pflicht an JEDEM Ausgang als Quellen-Test.** Gilt eine Pflicht fuer jeden
  Weg des Zyklus (Spiegelung, Zustandsdatei, Protokollzeile), liest der Test die
  QUELLE: die Funktion per `ast` finden, ihren Rumpf zeilenweise durchgehen und
  verlangen, dass vor JEDEM `return` die Pflicht steht. Ein Verhaltenstest waere hier
  teuer (Netz, Bericht, Zeit) UND wuerde den neuen Ausgang uebersehen; der
  Quellen-Test faellt genau darauf. Muster: `scanner/tests/test_spiegelung_jeder_zyklus.py`.

- **Eine Spurfamilie bekommt EINEN Vertragstest, nicht acht Einzeltests.** Liegt
  eine Familie mit gemeinsamem Kern vor, wandert der Test nach
  `Agenten/Handel/tests/test_<familie>_spuren.py` (Aufruf dort:
  `python -m unittest test_<datei>`), iteriert die Ordner per `glob` und prueft je
  Ordnername, `_grund`, `journal_zweitziel` auf `Q:`,
  `handel_erlaubt`/`freigabe.erfuellt` False, Herzschlag 180, `gebuehr_taker > 0`,
  Stop innerhalb `pflicht_stop_prozent_min/max`, Ratsche == Buchrisiko,
  Kill > Ratsche, Gesamtdeckel passt zu den Plaetzen, `mindest_kerzen` >= laengster
  Indikator, Anmeldung in `dauerlauf.SPUREN`, kein Orderweg im Quelltext — und
  `--live` verweigert im ECHTEN Kindprozess (Exit 0 plus Klartext). Ordnermenge
  und `REGELN`-Schluessel in BEIDE Richtungen vergleichen, sonst bleibt eine Waise
  unbemerkt.
- **Beim ersten roten Lauf zuerst rechnen, ob die eigene Fixture falsch ist.**
  Ein neuer Test schlaegt entweder wegen des Codes oder wegen der Reihe fehl; die
  Arithmetik entscheidet, nicht das Gefuehl. Zwei Faelle, die so auffielen: ein
  Band-Kreuz entsteht nur mit EINER Sprungkerze (bei drei steht der Schluss schon
  vorher ueber dem Band — Zustand statt Kreuz), und ein Signal, das der EMA einer
  Linie ist, beginnt konstruktiv `signal_n - 1` Werte NACH ihr. Wer die Reihe
  geradezieht, ohne das nachzurechnen, verbiegt den Code.

## 7. Nachweis (erst dann "fertig")

Ein Schattenarm wird GENAU SO nachgewiesen wie eine neue Spur — plus eine
Gegenprobe, die nur er braucht: **zweimal denselben Zyklus fahren** und
verlangen, dass der zweite Lauf NICHT doppelt kauft (die Kandidaten muessen als
"gefiltert" erscheinen). Rezept: `references/schattenarm.md`.

```bash
cd Agenten/Handel/<spur> && ../scanner/.venv/Scripts/python.exe handeln.py --vorschau
cd Agenten/Handel/<spur> && ../scanner/.venv/Scripts/python.exe handeln.py --papier
cd Agenten/Handel && scanner/.venv/Scripts/python.exe spiegelstand.py   # byte-gleich (Q:)
```

Dazu der erste Zyklus im Log des Dauerlaufs (`<spur> (papier) ok`) und der Stand
aussen (`Q:\Handel_Journal\<spur>` enthaelt `zustand.json`). Eine neue Spur in
`SPUREN` wirkt **erst nach einem Neustart** des Dauerlaufs (die Tabelle wird beim
Start gelesen) — ein Fix in `<spur>/handeln.py` dagegen im naechsten Zyklus.

## Pitfalls

- **Eine Vorlage nicht woertlich nachbauen.** Pine rechnet
  `ta.highest(high, 20)` INKLUSIVE der laufenden Kerze — der Schluss kann nie
  ueber dem Hoch der eigenen Kerze liegen, `crossover(close, high20)` wird damit
  nie wahr und die Regel handelt nie. Der Kanal muss die Kerzen DAVOR nehmen.
  Jede Abweichung von der Vorlage im Modulkopf begruenden (welche Zeile, warum),
  und die laufende Kerze immer verwerfen — sonst flackert ein Signal innerhalb
  der Stunde.

- **Nur den WECHSEL handeln, nicht den ZUSTAND.** "Short, sobald der Trend dreht"
  heisst: Richtung vorher +1, jetzt -1. Wer den Zustand abfragt, eroeffnet in
  jedem Zyklus dieselbe Position neu.
- **Ein Filter braucht eine Begruendung im Namen des Feldes**, z. B. EMA-Laenge:
  "Wendepunkt gegen einen intakten Aufwaertstrend ist meist ein Ruecksetzer".
  Ohne Filter feuert die Spur im Seitwaertsmarkt dauernd.
- **Zu wenig Kerzen = kein Signal**, nie ein Notbehelf aus einem kuerzeren Fenster.
  Die Indikatoren brauchen ihre Aufwaermzeit; der Code prueft das VOR dem Rechnen.
- **Ein Ziel relativ zum Stop (R-Vielfaches) traegt nur, wenn Stop und Ziel
  zusammenpassen** — der Stop liegt in den Wachen, das Ziel ist ein Vielfaches
  davon. Beide Zahlen im Test gegen die Stop-Grenzen pruefen.
- **Kein Live-Zweig auf Vorrat.** Live braucht Orderweg, Sperrenkette,
  Freigabefenster und den von Hand gesetzten Haken (`freigabe.erfuellt`), sonst ist
  `handel_erlaubt` wirkungslos und die Spur sieht nur scharf aus.
  Muster und Reihenfolge: `okx-orderweg-diagnose`.
- **Zahlen gehoeren in die `wachen.json`.** Eine Schwelle im Code ist eine zweite
  Wahrheit; wer sie dort findet, meldet das.
- **„Die Spur handelt nicht" erst diagnostizieren, dann bauen.** Drei Zeugen,
  bevor irgendetwas entsteht: die Vorschau-Sperrzeile (`MAXHIRN_ROUTINE=1 …
  --vorschau`), das JOURNAL (gibt es Einstiegszeilen der letzten Tage) und die
  Schwellen gegen die gemessene Verteilung des Instruments. Ein leeres Buch am
  Tagesende ist bei einem Tagesmuster die Bauart, ein alter generierter Bericht
  ein Kadenz-Problem (kein fehlendes Signal), und eine Kennzahl aus
  `herzschlag`-Zwangsschluessen ist keine Handelsmessung. Zahlenbeispiele:
  `references/schattenarm.md`.
- **Zahlen ueber `Agenten/Handel` nie roh zaehlen - erst die Fremd-Grenze anwenden.**
  Fremd-Material liegt mitten im eigenen Ordner (`OpenAlice` allein sind 81 % der
  Zeilen in `Agenten/Handel`, 482 Dateien / 513.266 Zeilen). Eine Bestandsfrage
  ohne die Grenze liefert 634.815 Zeilen statt 121.509 und macht jede Aussage
  darueber falsch. Quelle ist `Agenten/FREMD-Liste.json`, Leser
  `Agenten/Werkzeuge/fremd.py`, Messung `Agenten/Werkzeuge/bestand.py` (Vorgabe
  ohne Fremdes, `--mit-fremd` zum Vergleich). Fremdes wird BENANNT und nicht
  mitgezaehlt - und nie aufgeraeumt. Ein Eintrag ist eine Aussage ueber Herkunft
  und wird nie geraten: was wie ein Fremdbaum aussieht (Spur ohne Tests,
  ungetrackt), kann eigener Code vom selben Tag sein.
- **Antwortform an Max:** zuerst was jetzt laeuft (mit dem Beleg des ersten
  Zyklus), dann die Regel in einem Satz mit den ZAHLEN dieser Maschine, dann was
  absichtlich NICHT gebaut wurde (Live-Pfad, Signal-Ausstieg) und was dafuer fehlt.
