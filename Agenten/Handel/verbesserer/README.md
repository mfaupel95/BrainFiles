# Verbesserer

Woechentliche Selbstverbesserung fuer **Spur 1** (Scanner/OKX Spot). Liest das
Handelsjournal, schneidet die geschlossenen Runden in Segmente, sucht in einem
fest begrenzten Parameterraum einen Kandidaten, der die heutige Einstellung im
Walk-Forward schlaegt, und legt daraus **einen Vorschlag** ab. Angewandt wird
nichts von selbst -- der Vorschlag geht per Telegram an Max und wird erst mit
`/ja` im Dauerlauf scharf.

Stand: 2026-09-06. Erster Ausbau. Ein Lauf endet immer mit einem Ordner unter
`berichte/<datum>-spur1/` -- zur Not nur mit einem kein-Vorschlag-Bericht.

## Die Grundlinie kennen

Aus [[Handelsbots]] (`Wissen/Handelsbots.md`): jede mechanische Krypto-Strategie
lag ueber lange Zeitraeume **nahe null, leicht darunter**. Ein Backtest ueber
ein einzelnes gutes Fenster misst vor allem dieses Fenster. Der Verbesserer
sucht deshalb nicht den grossen Wurf, sondern kleine, belegbare Verschiebungen
und siebt den Rest aus:

- **Segmente** werden nur zum Befund, wenn sie mindestens `segment_mindest_n`
  Runden umfassen **und** der Permutationstest gegen den Rest p < 0.05 liefert.
- **Overfitting-Sperre** (`suche.py`): ein schwaches Sieb -- Auswahl und
  Pruefung nutzen dieselben Fenster, ein echter Train/Test-Split ist Folgearbeit
  (siehe Spec). Ein Kandidat wird nur vorgeschlagen, wenn er die Basis im
  Aggregat **und** in einer Mehrheit der Einzelfenster schlaegt (mehr als die
  Haelfte, mindestens `overfit_min_fenster`) und dabei `>= overfit_min_runden`
  OOS-Runden hat. Sonst: kein Vorschlag mit Begruendung.

Die Zahlen stehen in `konfig.json`; der Walk-Forward zieht Training/Test/Schritt
aus `oos_*`.

## Dateien

| Datei | Zweck |
|---|---|
| `konfig.json` | Modulweite Parameter (Suchbudget, OOS-Fenster, Segment- und Overfit-Schwellen, LLM-Modus). Von Hand geaendert. Enthaelt `auto_anwenden: false`. |
| `spuren.json` | Je Spur: Pfade zu Journal/Zustand/Wachen/Berichten/Bewertung und die Whitelist der aenderbaren Schluessel mit Wertebereich. Deckel stehen hier **nicht**. |
| `kosten.py` | Die eine Gebuehrenzahl (`GEBUEHR_PCT = 0.0005`), identisch mit `scanner/handeln.py`. |
| `kerzen.py` | OKX-Tageshistorie ueber `history-candles` rueckwaerts blaettern und lokal cachen; faellt der Abruf aus, arbeitet der Cache weiter. |
| `auswerter.py` | TP1: geschlossene Runden aus dem Journal in Segmente schneiden, Permutationstest, Befund-JSON in den Vorschlagsordner. |
| `ruecktest.py` | TP2: Merkmals-Matrix einmal vorrechnen, Kandidat ueber ein Fenster simulieren (Ein-/Ausstieg wie `scanner/handeln.py`), Walk-Forward. |
| `suche.py` | TP3: bounded Kandidatenraum, Nachbarschaft, Koordinatenabstieg, Overfitting-Sperre. |
| `vorschlag.py` | TP3: aus dem Suchergebnis `bericht.md`, `wachen.neu.json`, `bewertung.patch`, `commit.txt` bauen -- nie neben die Quelldateien. |
| `anwenden.py` | TP4: der **einzige** schreibende Pfad. Baum-Pruefung, fest verdrahtete Denylist, `.bak`, byteweises Schreiben, `git apply`, Commit. |
| `anfrage.py` | TP4: reine Ordner-/Textlogik fuer den Anfrage-Typ `verbesserung` im Dauerlauf (offenen Vorschlag finden, markieren, Telegram-Kurztext). |
| `digest.py` | TP5: woechentlicher LLM-Aufruf, der nur *annotiert* (Empfehlungen priorisieren, Lehren nach `Werkstatt/`). Bei `modus: aus` bleibt alles leer. |
| `lauf.py` | Orchestrator: `kerzen -> auswerter -> suche -> vorschlag -> digest`. Harter Abbruch nur ohne Kerzen-Cache. |
| `requirements.txt` | Leer bis auf Kommentar -- nur Standardbibliothek, eigenes venv wie `scanner/.venv`. |
| `tests/` | rund 100 Tests (`python -m unittest discover -s tests`), Fixtures unter `tests/fixtures/`. |
| `.venv/` | Eigenes venv (Python 3.13, nur Standardbibliothek). Die Routine zeigt auf `.venv/Scripts/python.exe`. |

Nicht versioniert (in `.gitignore`, Rauschen): `kerzen/` (Kerzen-Cache),
`berichte/` (Vorschlagsordner samt `erledigt/` und `abgelehnt/`), `bak/`
(Sicherungen von `anwenden.py`), `.venv/`.

## Aufrufe

```powershell
cd Agenten\Handel\verbesserer

.venv\Scripts\python.exe lauf.py --spur spur1   # ein Wochenlauf -> berichte/<datum>-spur1/
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Woechentlich uebernimmt das die Routine `Agenten/Routinen/verbesserer.ps1`
(setzt `MAXHIRN_ROUTINE=1`, loggt nach `Routinen/logs/`). Sie laeuft **nach**
`handel-wachen.ps1` und wird von der Windows-Aufgabenplanung aufgerufen.

## Was er selbst nicht tut

- **Wendet nichts an.** `lauf.py` schreibt nur in `berichte/`. Der einzige
  schreibende Pfad in die Scanner-Dateien ist `anwenden.py`, und der laeuft
  erst nach einem `/ja` von Max im Dauerlauf.
- **Fasst keine Deckel an.** `spuren.json` erlaubt nur Tore, Gewichte und die
  Watchlist in einem festen Wertebereich. `max_pro_trade_usd`,
  `max_gesamt_usd`, `max_offene_positionen`, `handel_erlaubt` und die
  `freigabe/drawdown/herzschlag/kill_switch`-Bloecke stehen auf einer **fest
  verdrahteten Denylist** in `anwenden.py`, die immer gewinnt -- egal, was
  `spuren.json` deklariert. Der Pflicht-Stop laesst sich nur innerhalb des in
  `spuren.json` deklarierten Bereichs (`pflicht_stop_prozent_min`/`_max`)
  verschieben, nie abschalten. `anwenden.py` prueft beim Anwenden jeden
  geaenderten Wert erneut gegen diese Whitelist -- zusaetzlich zur fest
  verdrahteten Denylist fuer Deckel und Schalter.
- **`auto_anwenden` ist `false`** (`konfig.json`) und es gibt keinen Code, der
  `true` auswertet. Automatisches Anwenden braeuchte erst eine Aenderung an
  `Wissen/Handelsregeln.md`.
- **Der Telegram-Push in `dauerlauf.py`** weicht nur einer offenen
  *Scharfschalt-Anfrage* aus (`anfrage_offen()`), nicht einem bereits offenen
  Live-Fenster -- ein Vorschlag kann also gepusht werden, waehrend eine Spur
  scharf ist. Das ist trotzdem sicher: die Denylist sperrt jeden harten
  Schalter, und `anwenden` bricht bei einem unsauberen Arbeitsbaum ab.

Vollstaendige Begruendung und Abnahmekriterien:
`Werkstatt/spec-selbstverbessernder-handelsagent-2026-09-06.md`.
