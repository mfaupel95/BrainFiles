# Selbstverbessernder Handelsagent — Entwurf

Stand: 2026-09-06
Pfad-Ziel des Moduls: `Agenten/Handel/verbesserer/`
Erste Ausbaustufe: vertikaler Schnitt TP1–TP5 für **Spur 1 (Scanner/OKX)**.

## Zweck

Eine wöchentliche Schleife, die aus dem Handelsjournal und historischen Kursen
lernt und **begründete Vorschläge** für bessere Parameter, Modellgewichte,
Watchlist und Positionsgrößen erzeugt. Sie wendet nichts von selbst an: ein
Vorschlag wird über Telegram (`/ja`) bestätigt, erst dann angewandt und
committet.

## Rahmen (unverhandelbar)

Aus `MaxHirn/Wissen/Handelsregeln.md`:

- Eine bessere Einstellung wird **vorgeschlagen — mit der Rechnung dazu —, nicht
  heimlich eingesetzt.**
- Jede `wachen.json`-Änderung ist Stufe 1: eigener Commit, `.bak` vorher, die
  neu gerechneten vier Pflichtzahlen in der Commit-Nachricht, nie mit anderer
  Arbeit gebündelt.
- Das Modul schreibt **nie** `handel_erlaubt: true`, hebt **nie** einen fixen
  Deckel, fasst die Blöcke `freigabe` / `drawdown` / `herzschlag` nicht an.
- `auto_anwenden` steht auf `false`. Den Schalter umzulegen braucht eine
  Änderung an `Handelsregeln.md` und ist nicht Teil dieser Ausbaustufe.

Die vier Pflichtzahlen (Handelsregeln, „Prüfpflicht"): Liquidationsabstand
gegen größten 7-Tage-Rücklauf, Funding über die Haltedauer, Gebühren je Runde
gegen erwarteten Gewinn, nötige gegen beobachtete Trefferquote. Für Spur 1
(Spot, kein Hebel) entfallen Liquidation und Funding; es bleiben Gebühren und
Trefferquote, die anderen beiden werden als „n/a (Spot)" ausgewiesen.

## Architektur

### Ansatz

Eigenständiges, spur-neutrales Modul mit fester Kette:
Auswerter → Walk-Forward-Backtest → beschränkte Suche → Vorschlags-Bauer →
LLM-Digest → Telegram-Bestätigung → CRLF-schonendes Anwenden + eigener Commit.

Verworfen: (B) nur Auswerter + LLM ohne Backtest — Vorschläge ohne
Out-of-sample-Prüfung, genau der Fehler aus `Handelsbots.md`. (C) Integration in
`dauerlauf.py` mit kontinuierlicher Optimierung — höchste Komplexität,
stärkster Regelkonflikt, Overfitting durch Dauerlauf auf denselben Daten.

### Modulaufbau

| Datei | Zweck |
|---|---|
| `spuren.json` | Spur-neutrale Konfig: je Spur Pfade zu Journal, `zustand.json`, `wachen.json`, Bewertungsmodul, Kerzenquelle — und die Whitelist der änderbaren Schlüssel je Spur |
| `konfig.json` | `auto_anwenden: false`, `llm`-Block, `such_budget`, OOS-Fensterparameter, `segment_mindest_n` |
| `kerzen.py` | Tageshistorie je Watchlist-Wert von OKX holen (paginiert), Cache unter `kerzen/` |
| `auswerter.py` | TP1 — geschlossene Runden segmentieren, Ausreißer als Befund |
| `ruecktest.py` | TP2 — Walk-Forward-Harness, Merkmals-Matrix, Simulation |
| `suche.py` | TP3 — Kandidaten erzeugen, Koordinatenabstieg, Overfitting-Sperre |
| `vorschlag.py` | TP3 — Diff, `wachen.neu.json`, `bewertung.patch`, `commit.txt`, `bericht.md` |
| `digest.py` | TP5 — wöchentlicher LLM-Aufruf, Annotation des Berichts |
| `anwenden.py` | TP4 — rein, testbar: Denylist-Prüfung, `.bak`, CRLF-schonend anwenden, committen |
| `lauf.py` | Orchestrator, aufgerufen von Routine und `dauerlauf.py` |
| `berichte/` | Ausgabe (nicht versioniert): offene Vorschläge, `erledigt/`, `abgelehnt/` |
| `bak/` | zeitgestempelte Sicherungen vor jedem Anwenden |
| `README.md` | wie die anderen Module |

Eigenes stdlib-only venv (Python 3.13) wie `scanner/`. Das Modul importiert
`scanner/wachen_pruefung.py` statt Logik zu duplizieren — dieselbe Linie wie
`xperp/` und `kraken/`.

`lauf.py` erzeugt **nur Artefakte** in `berichte/`. Anwenden passiert
ausschließlich über `anwenden.py`, aufgerufen aus dem Telegram-Pfad von
`dauerlauf.py`.

## TP1 — Auswerter

Eingang: `scanner/handelsjournal.csv` + `scanner/berichte/` (Score und
Kennzahlen zum Einstiegszeitpunkt). `wachen_pruefung.runden_aus_journal()`
liefert geschlossene Runden mit G/V; der Auswerter hängt je Runde die
Einstiegs-Merkmale an und bildet Segmente:

- Richtung (Spur 1 nur Long — Feld für Spur 2/3 vorbereitet)
- Volatilitätsband zum Einstieg (Terzile aus `bewertung.py`)
- Score-Band (60–70 / 70–80 / 80+)
- Chance/Risiko-Band
- Haltedauer-Band
- Instrument, Wochentag
- Ausstiegsgrund (Stop / Ziel)

Je Segment: Anzahl Runden, mittlerer G/V nach Kosten, Trefferquote,
Erwartungswert gegen Gesamtschnitt. Ein Segment ist **Befund**, wenn
n ≥ `segment_mindest_n` (Vorgabe 8) **und** der Unterschied zum Rest einen
Permutationstest besteht (eigener Shuffle-Test mit festem Seed, kein SciPy).

Ausgabe: `berichte/JJJJ-MM-TT-befund-spur1.json` — Rohmaterial für Suche und
Digest. Kein Netz, alles aus lokalen Dateien, reproduzierbar.

## TP2 — Walk-Forward-Backtest

`ruecktest.py` bildet die Einstiegs-/Ausstiegslogik aus `handeln.py` **exakt**
nach — sonst misst der Backtest eine andere Strategie.

### Kerzen

`kerzen.py` holt je Watchlist-Wert so viel Tageshistorie wie OKX hergibt
(History-Candles, paginiert, ~1–2 Jahre) und legt sie unter
`verbesserer/kerzen/` ab. Abruf schlägt fehl → Cache, Alter im Bericht
vermerkt. Kein Cache → Abbruch ohne Vorschlag.

### Merkmals-Matrix

Die 5 Chance- und 4 Risiko-Rohkomponenten je (Wert, Tag) werden **einmal**
vorberechnet. Einen Kandidaten auszuwerten ist dann nur noch Gewichtung + Tore.
Gewichtssuche wird dadurch fast kostenlos.

Dafür bekommt `scanner/bewertung.py` einen optionalen Parameter `gewichte=None`
(Vorgabe = heutige Konstanten). Rückwärtskompatibel; Scanner-Verhalten
unverändert. Regressionstest: `bewerten(k) == bewerten(k, gewichte=None)`.

Die Rohkomponenten (vor Gewichtung), die die Matrix hält:
Chance — `c_trend`, `c_momentum`, `c_ruecksetzer`, `c_nicht_ueberkauft`,
`c_volumen`. Risiko — `r_vola`, `r_drawdown`, `r_extrem_rsi`,
`r_absturz_momentum`. Dazu `vola_pa` (Tor), `preis`.

### Simulation

Je Testtag alle Werte bewerten, Kandidaten-Tore anwenden
(`score >= mindest_score AND vola_pa <= max_volatilitaet_pa AND verhaeltnis >= mindest_chance_risiko`),
Einstieg zum Schlusskurs des Tages. Stop-Prozent wie `handeln.stop_prozent()`:
`clamp(3 + 6*min(vola, 1.5), stop_min, stop_max)`. Stop = Einstieg·(1−sp/100),
Ziel = Einstieg + 2·(Einstieg−Stop).

Danach Tag für Tag: Stop getroffen, wenn Tagestief ≤ Stop; Ziel, wenn Tageshoch
≥ Ziel; beides am selben Tag → **Stop zuerst** (konservativ, wie die
Liquidationsprüfung in `dca.py`). `abklingzeit_tage`,
`max_offene_positionen`, `max_gesamt_usd` gelten wie live.

### Kosten — und Angleichung von `handeln.py`

Konstante `GEBUEHR_PCT = 0.0005` (0,05 % OKX Taker, gemessen 02.09.2026),
je Seite abgezogen. `ruecktest.py` spiegelt genau diese Konstante.

`scanner/handeln.py` rechnet im Papierpfad heute **ohne** Gebühr — das nennt
`Handelsregeln.md` einen Fehler. Deshalb ist Teil dieser Ausbaustufe eine
**kleine Angleichung von `handeln.py`**: der Papierpfad zieht dieselbe
`GEBUEHR_PCT` je Seite ab, eingerechnet in die journalisierten Beträge
(Kauf-Zeile mit Gebühr, Verkauf-Zeile nach Gebühr — wie Spur 3). Damit rechnen
Backtest und laufender Papierlauf gleich.
`wachen_pruefung.runden_aus_journal()` bleibt unberührt (`erloes − einsatz`,
jetzt inklusive Gebühr). Der Auswerter vermerkt das Umstellungsdatum: Runden
davor tragen keine Gebühr und sind nicht direkt vergleichbar.

### Fenster

Training 120 Tage → Test 30 Tage out-of-sample → Schritt 30. Bei ~1–2 Jahren
OKX-Historie ergibt das rund 14–20 Testfenster. OOS-Runden aller Fenster werden
aggregiert. Werte in `konfig.json`.

### Kennzahlen je Fenster und gesamt

Netto-G/V je Runde, Trefferquote, Rundenzahl, max. Drawdown, dazu die vier
Pflichtzahlen (für Spur 1: Gebühren je Runde, nötige/beobachtete Trefferquote;
Liquidation/Funding = „n/a (Spot)").

## TP3 — Suche + Vorschlags-Bauer

### Suche

`suche.py` — **Koordinatenabstieg**, kein volles Raster:

1. Tore: `mindest_score` 55–75 (Schritt 2,5), `max_volatilitaet_pa` 0,9–1,4
   (0,1), `mindest_chance_risiko` 1,3–2,2 (0,1), Stop-Band (`stop_min` ≥ 4,
   `stop_max` ≤ 15), `abklingzeit_tage` 2–5.
2. Gewichte: ±0,05-Schritte, je Gruppe (Chance / Risiko) auf Summe 1
   renormiert, jedes in [0; 0,5].
3. Watchlist: Werte mit negativem OOS-Beitrag über ≥ 2 Fenster streichen.
   Aufnahme neuer Werte: Phase 2, nicht in dieser Ausbaustufe.
4. Sizing-Kurve: `flach` (heute) / `score-linear` / `vola-invers`, jeweils
   gedeckelt durch `max_pro_trade_usd` und `max_gesamt_usd`.

Budget `such_budget` Auswertungen (Vorgabe 300). Suchraum-Grenzen stehen in
`spuren.json`. Die fixen Deckel (`max_pro_trade_usd`, `max_gesamt_usd`,
`max_offene_positionen`) sind **nicht** im Suchraum.

Zielfunktion: mittlerer Netto-G/V je OOS-Runde, Abzug bei OOS-Drawdown über dem
aktuellen und bei Rundenzahl unter der Schwelle.

### Overfitting-Sperre

Ein Kandidat wird nur zum Vorschlag, wenn er die aktuelle Konfig
- im OOS-Aggregat schlägt **und**
- in ≥ `overfit_min_fenster` (Vorgabe 3) einzelnen Testfenstern schlägt **und**
- ≥ `overfit_min_runden` (Vorgabe 20) OOS-Runden hat.

Sonst: `berichte/JJJJ-MM-TT-kein-vorschlag-spur1.md` mit den Zahlen, warum
nichts trägt. Der Digest läuft trotzdem (Lehren).

### Vorschlags-Bauer

`vorschlag.py` schreibt nach `berichte/JJJJ-MM-TT-vorschlag-spur1/`:

| Datei | Inhalt |
|---|---|
| `bericht.md` | Was sich ändert; OOS vorher/nachher je Fenster + gesamt; die vier Pflichtzahlen; Ergebnis der Overfitting-Sperre; Warnungen (Kostenmodell, dünne Historie, Survivorship) |
| `wachen.neu.json` | vorgeschlagene Fassung — nur für Diff/Vorschau, wird hier nicht angewandt |
| `bewertung.patch` | Unified-Diff für Gewichtsänderungen (leer, wenn keine) |
| `commit.txt` | Entwurf der Commit-Nachricht mit den vier Zahlen und dem OOS-Delta |

Schreibt nie nach `scanner/`. Nur nach `berichte/`.

## TP4 — Anwenden + Telegram

### `anwenden.py` (rein, testbar)

`anwenden(vorschlag_ordner)` in dieser Reihenfolge:

1. `git status --porcelain` — ist etwas gestaged oder eine Zieldatei schmutzig
   → **Abbruch**, Rückgabe „Arbeitsbaum nicht sauber".
2. **Denylist-Prüfung** (fest im Code, schlägt jede Whitelist): berührt der
   Diff `handel_erlaubt`, `freigabe.*`, `drawdown_*`, `kill_switch_*`,
   `herzschlag_*`, `max_pro_trade_usd`, `max_gesamt_usd`,
   `max_offene_positionen`, `journal_zweitziel` → Abbruch. Danach gegen die
   Whitelist in `spuren.json` prüfen; jeder Wert gegen seinen Deckel.
3. Zeitgestempeltes `.bak` jeder betroffenen Datei nach `verbesserer/bak/`.
4. **CRLF-schonend anwenden:** `wachen.json` per gezielter Text-Ersetzung der
   betroffenen Schlüssel (Regex auf den Wert), **kein** `json.dump` — das
   stellt CRLF auf LF um (`MaxHirn/Wissen/`-Regel, Memory `crlf-im-vault`).
   `bewertung.py` per Patch.
5. `git add` **nur** die betroffenen Dateien; `git commit -F commit.txt`.
   Commit-Nachricht endet mit
   `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`.
6. Vorschlagsordner → `berichte/erledigt/`. Rückgabe: Commit-Hash.

`/nein` → Ordner nach `berichte/abgelehnt/`, Grund vermerkt.

### `dauerlauf.py`

Neuer Anfrage-Typ `verbesserung` in `pruefe_anfragen()`: liegt ein frischer
Vorschlagsordner und keine offene Anfrage vor, geht eine Telegram-Nachricht
raus — Kurzfassung + „`/ja` wendet an und committet, `/nein` archiviert".
`/ja` ruft `anwenden.anwenden()`, `/nein` verschiebt nach `abgelehnt/`. Die
Änderung am Dauerlauf-Kern bleibt auf diesen einen Anfrage-Typ und den
Aufruf begrenzt.

`auto_anwenden: true` (Zukunft) würde Schritt 1–6 ohne Telegram fahren — Zweig
dokumentiert, in dieser Ausbaustufe nicht aktiv und nicht getestet.

## TP5 — LLM-Digest

`digest.py`, wöchentlich nach der Suche, vor der Telegram-Anfrage.

- **Modellzugang** aus `konfig.json` → `llm.modus`: `"ollama"`
  (localhost:11434, Modellname) / `"cliproxy"` (`base_url` + Schlüssel aus
  Env-Variable) / `"aus"`.
- **Eingabe:** Befund des Auswerters + Suchergebnis (Baseline vs. Kandidat,
  OOS-Tabelle) + Liste der Änderungen.
- **Auftrag** (deutsch, knapp): (a) 2–4 priorisierte Empfehlungen mit je einer
  Zeile Begründung, (b) Klartext-Lehren, (c) ausdrücklicher „nicht
  anfassen"-Hinweis, wenn die Datenlage zu dünn ist.
- **Nicht erreichbar / `"aus"`:** Digest übersprungen, Notiz im Bericht, der
  Vorschlag bleibt gültig. Der angewandte Diff ist immer das deterministische
  Suchergebnis; das LLM annotiert nur, es entscheidet nichts.
- **Ausgabe:** Abschnitt „## Priorisierte Empfehlungen (LLM)" vorn in
  `bericht.md`; Lehren an `Werkstatt/handelslehren-eingang.md` angehängt
  (datiert, append-only). Nicht direkt nach `Wissen/` — das kuratiert Max.

## Fehlerbehandlung

| Lage | Reaktion |
|---|---|
| OKX-Abruf weg | Cache + Altersvermerk; kein Cache → Abbruch, kein Vorschlag |
| Journal < 20 Runden | kein Backtest-Vorschlag; Auswerter + Digest laufen; Bericht „zu wenig Historie" |
| Suche findet nichts Besseres | `kein-vorschlag`-Bericht; Digest läuft |
| Modell weg | Digest übersprungen, Notiz; Vorschlag bleibt gültig |
| Git-Arbeitsbaum schmutzig | Vorschlag wartet; Telegram sagt warum |
| Vorschlag berührt Denylist-Schlüssel | Abbruch beim Anwenden, Meldung |

## Konfiguration

- `spuren.json` — je Spur: Pfade + Whitelist änderbarer Schlüssel +
  Suchraum-Grenzen.
- `konfig.json` — `auto_anwenden: false`, `llm`-Block, `such_budget: 300`,
  `oos_training_tage: 120`, `oos_test_tage: 30`, `oos_schritt_tage: 30`,
  `segment_mindest_n: 8`, `overfit_min_runden: 20`, `overfit_min_fenster: 3`.
- Eigenes stdlib-only venv.

## Wiring

- `Agenten/Routinen/verbesserer.ps1` — wöchentlich, nach `handel-wachen.ps1`,
  ruft `verbesserer/lauf.py --spur spur1`. Setzt `MAXHIRN_ROUTINE=1`.
- `lauf.py`: Kerzen auffrischen → Auswerter → Backtest Baseline → Suche →
  bei bestandener Overfitting-Sperre `vorschlag.py`, sonst `kein-vorschlag` →
  `digest.py` → Vorschlagsordner ablegen.
- `dauerlauf.py` nimmt den Vorschlagsordner im nächsten Zyklus auf und stellt
  die Telegram-Anfrage.

## Tests (TDD)

| Modul | Prüft |
|---|---|
| `auswerter` | Fixture-Journale → erwartete Segmenttabellen; Permutationstest mit festem Seed reproduzierbar; Segment unter `segment_mindest_n` wird nicht zum Befund; Runden vor dem Gebühren-Umstellungsdatum getrennt ausgewiesen |
| `ruecktest` | Golden-Test (synthetische Kerzen + feste Konfig → exakte Kennzahlen); Merkmals-Matrix == direktes `bewerten()` innerhalb Rundung; Stop-vor-Ziel am selben Tag; `bewerten(k) == bewerten(k, gewichte=None)`; `GEBUEHR_PCT` wirkt je Seite und stimmt mit der Konstante in `handeln.py` überein |
| `handeln.py` (Angleichung) | Papier-Runde: journalisierte Kauf-Zeile enthält Gebühr, Verkauf-Zeile ist nach Gebühr; G/V einer Runde = 2× `GEBUEHR_PCT` kleiner als ohne Angleichung; Live-Pfad unverändert |
| `suche` | nie ein Wert außerhalb Whitelist / über Deckel (Property-Test über zufällige Suchzustände); Overfitting-Sperre lehnt Ein-Fenster-Treffer ab; Gewichtssumme je Gruppe == 1 |
| `vorschlag` | angewandter Diff ergibt exakt `wachen.neu.json`; `commit.txt` enthält die vier Zahlen; schreibt nichts nach `scanner/` |
| `anwenden` | Abbruch bei schmutzigem Baum; Abbruch bei Denylist-Schlüssel; `.bak` geschrieben; CRLF bleibt CRLF (Fixture mit `\r\n`); nur betroffene Dateien gestaged; Commit-Nachricht trägt die Co-Authored-By-Zeile |
| `digest` | gemockter Endpunkt → Bericht annotiert; Endpunkt weg → Vorschlag vollständig, Notiz vorhanden; LLM-Ausgabe ändert den Diff nicht |

## Spätere Ausbaustufen (nicht in dieser Spec)

- TP6 — Ausweitung auf Spur 2 (XPERP: Margin statt Einsatz, Funding als eigene
  Journalzeile, Liquidation als dritter Ausstiegsgrund) und Spur 3 (Kraken:
  EUR, 0,80 % je Runde).
- Watchlist-Aufnahme neuer Werte aus einem Kandidatenpool.
- `auto_anwenden`-Zweig scharf schalten — braucht Änderung an
  `Handelsregeln.md`.
