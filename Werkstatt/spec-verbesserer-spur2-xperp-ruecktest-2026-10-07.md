# Spec: Verbesserer Spur 2 (XPERP) – Rücktest-Engine

**Datum:** 2026-10-07
**Status:** Entwurf, zur Durchsicht
**Vorgänger:** Ausbaustufe 2a (Spur 3, Kraken-EUR), abgeschlossen 2026-10-07 –
siehe `Werkstatt/spec-verbesserer-spur3-kraken-eur-2026-10-07.md`.
**Nachfolger (eigene, spätere Spec):** Spur 2, woechentliche Optimierungsschleife
– baut auf dieser Engine auf, siehe Abschnitt "Danach".

## Zweck

Der selbstverbessernde Handelsagent (`Agenten/Handel/verbesserer/`) hat für
Spur 1 (Scanner/OKX-Spot) und Spur 3 (Kraken/EUR) eine wöchentliche
Rückblick-Schleife, die Parameter-Vorschläge für `wachen.json` macht. Spur 2
(XPERP, OKX-Futures mit Hebel, `Agenten/Handel/xperp/`) hat bisher **keinen
Rücktest** – nur den Live-/Papier-Pfad (`bot.py`, `handeln.py`).

Diese Spec liefert den ersten Baustein dafür: eine eigenständige
Rücktest-Engine, die die **aktuelle** xperp-Strategie (Trend-Modus) über
historische Kerzen nachrechnet und einen Leistungsbericht liefert. Sie
verändert `wachen.json` noch nicht und ist noch nicht an die
Optimierungsschleife (`suche.py`) angeschlossen – das ist die nächste,
eigene Ausbaustufe (Spec B, siehe "Danach").

## Abgrenzung (was diese Spec NICHT tut)

Reihe von Entscheidungen aus dem Brainstorming, damit sie nicht erneut
aufgemacht werden:

- **Nur Trend-Modus.** Grid-Modus (`zeige_grid`/`bot.groesse` mit
  Stufen-Geometrie) ist eine eigene, spätere Ausbaustufe.
- **Kein LLM-Filter.** `llm_filter` lässt sich nicht deterministisch auf
  historische Kerzen anwenden (kein historisches Urteil, Live-Aufruf pro
  Rücktest-Tag unbezahlbar). Die Engine verhält sich wie `llm_aktiv=false`.
- **CVD-4h-Komponente neutral.** `okxf.taker_volumen()` liefert nur ~16 Tage
  Historie (100 Eimer à 4h) – zu kurz für eine Walk-Forward-Prüfung mit
  mehreren Out-of-Sample-Fenstern. `indikatoren.lage()` wird mit
  `cvd_lage={"richtung": 0, ...}` (die vorhandene `cvd.leer()`-Form)
  aufgerufen, genau der Fallback, der bei einem echten Quellenausfall auch
  live greift. Das Signal entsteht aus SuperTrend, EMA, RSI, Saisonalität
  und Volumen-Drift.
- **Universum = heutige ~164 Kontrakte, historisch neu bewertet.** Welche
  Kontrakte zu einem früheren Zeitpunkt gelistet waren, lässt sich nicht
  zuverlässig rekonstruieren (OKX führt keine historische Kontraktliste).
  Der Instrumentenkreis ist fest (heutige `auswahl.sammle()`-Kandidaten),
  die Auswahl *innerhalb* dieses Kreises ist an jedem Zeitschritt dynamisch
  (Rangliste neu berechnet aus den bis dahin verfügbaren Kerzen).
  **Bekannte Grenze:** Survivorship-Bias – heute delistete Kontrakte fehlen.
- **Keine Optimierung.** Diese Engine berichtet, wie die Strategie mit der
  AKTUELLEN `wachen.json` gelaufen wäre. Kein Hügel-Klettern, kein neues
  `aenderbar`-Set, keine Anbindung an `bewertung.py`.
- **Keine Live-Order-Mechanik.** "Wartende Aufträge" (Limit hinter dem Markt,
  Timeout, Storno), Rollover-Erkennung, Handpositionen, Buchbereinigung sind
  Betriebslogik einer echten Börsenverbindung und werden nicht nachgebildet
  (siehe Vereinfachung unten).

## Architekturentscheidung

Die bestehende `verbesserer/ruecktest.py`-Engine (Spur 1/3) geht von
long-only, prozentualem Stop und einer festen Watchlist mit Score-Schwelle
aus – das passt nicht zu Long/Short, Hebel/Margin/Liquidation und einer
universumsweiten Platzbeschränkung. Statt die bestehende Schleife zu
verbiegen, entsteht ein **eigenes Modul**, das die bestehenden, reinen
Rechenfunktionen aus `xperp/` **unverändert direkt importiert**:

- `indikatoren.lage()` – Signal (SuperTrend/EMA/RSI/Saisonalität/
  Volumen-Drift), reine Berechnung auf einer Kerzenliste.
- `auswahl.kennzahlen()` / `auswahl.bewerte()` / `auswahl.mae_tage()` /
  `auswahl.hebel_deckel()` – Rangliste und Hebel-Deckel.
- `bot.groesse()` / `bot.liquidationspreis()` / `bot.pruefpflicht()` –
  Positionsgröße, Liquidationspreis, Pflichtzahlen.
- `trailing_modul` (`Handel/trailing.py`) – Trailing-Stop-Rechnung.
- `signal_wechsel.zugelassen()` – Signal-Wechsel-Gatter.

Dadurch rechnet der Rücktest exakt dieselbe Logik wie live; es gibt keine
zweite, parallel gepflegte Fassung, die auseinanderlaufen könnte (dasselbe
Risiko, das `kraken_modell.py`s Docstring für die Gebühr schon nennt).

Externe Backtest-Bibliotheken scheiden aus (Projektlinie "Nur
Standardbibliothek", siehe `ruecktest.py`-Docstring).

## Datenbeschaffung

### Instrumentenkreis

Einmalig (und bei jedem wöchentlichen Cache-Refresh neu) die aktuell
gelisteten Kontrakte aus allen drei Familien einsammeln
(`okxf.instrumente(kategorie)` für `KRYPTO`/`AKTIE`/`ROHSTOFF`, wie
`auswahl.sammle()` es tut) und als feste Liste cachen. Neue Kontrakte, die
nach dem letzten Refresh gelistet werden, erscheinen erst im nächsten
Refresh – keine Nachbildung ihrer Vorgeschichte nötig, sie haben keine.

### Kerzen-Cache

Neues Modul `verbesserer/xperp_kerzen.py` (Vorbild `kraken_kerzen.py`,
gleiche `hole()`/`laden()`-Form). Pro Instrument:

- **1H-Kerzen** über `okxf.kerzen_lang()` (paginiert über
  `history-candles`), so viele Seiten wie der gewünschte Rückblickzeitraum
  braucht. Dienen der Ausstiegsprüfung (Stop/Ziel/Liquidation/Trailing) in
  feinerer Auflösung als das Signal.
- **4H-Kerzen**, ebenfalls nativ über `okxf.kerzen_lang()` (NICHT aus den
  1H-Kerzen zusammengefasst – das würde ein Phasen-Risiko gegenüber OKX'
  echten 4H-Grenzen eingehen). Treiben die Signal-Neuberechnung, phasengleich
  mit live.
- **Tageskerzen** (`okxf.kerzen(inst, "1D", 300)`) für `auswahl.mae_tage()`
  und den Hebel-Deckel, wie `hebel_deckel()` in `bot.py`/`auswahl.py` es live
  tut.

Jede Reihe wird als eigene JSON-Datei gecacht (Instrument × Granularität),
wöchentlicher Refresh wie bei Spur 1/3.

### Funding-Historie (neu)

`okxf.py` hat bisher nur `funding(inst)` für den AKTUELLEN Satz. Neue
Funktion `okxf.funding_historie(inst, seiten=N)`, paginiert über den
historischen Funding-Rate-Endpunkt (Vorbild: `kerzen_lang()`s
Blätter-Schema über `after`-Parameter), gecacht wie die Kerzen.

### Takt und Laufzeit

~164 Instrumente × (mehrere Seiten 1H-Kerzen + mehrere Seiten 4H-Kerzen +
1D-Kerzen + Funding-Historie-Seiten) läuft durch die gemeinsame Haus-Bremse
`okx_takt` (eine IP, mehrere Prozesse). Das ist ein geduldiger, einmaliger
bzw. wöchentlicher Hintergrund-Cache-Aufbau (Minuten bis niedrige
zweistellige Minutenzahl), kein Schritt, der bei jedem Testlauf inline
läuft. Der Plan behandelt den Cache-Aufbau als eigenen Schritt mit
eigenem CLI-Aufruf, der VOR einem Rücktest-Lauf einmal ausgeführt wird.

## Simulationsschleife

### Zeittakt

Äußere Schleife in 4H-Schritten (eine Iteration je 4H-Kerze, deckt sich mit
der Live-Taktung von Signal und Rangliste). Innerhalb jedes 4H-Schritts
werden die vier enthaltenen 1H-Kerzen durchlaufen für:

- Ausstiegsprüfung (siehe Vorrang unten) in feinerer Auflösung als das
  4H-Signal.
- Trailing-Stop-Nachführung (`trailing_modul`) bei jedem 1H-Schritt.
- Funding-Abrechnung an den 8h-Grenzen (00/08/16 UTC) mit dem historischen
  Satz aus `funding_historie()` für genau diese Periode (genauer als
  live's Vereinfachung, die den AKTUELLEN Satz auf alle fälligen Perioden
  anwendet – siehe `handeln.buche_funding()`).

### Rangliste und Auswahl (je 4H-Schritt)

Für jedes Instrument im Cache: `auswahl.kennzahlen()` auf den bis zu diesem
Zeitpunkt verfügbaren 4H-Kerzen (point-in-time, kein Vorgriff auf
spätere Kerzen), `auswahl.bewerte()` für die Punkte, `auswahl.mae_tage()`
auf den bis dahin verfügbaren Tageskerzen für den Hebel-Deckel. Danach
dieselben Tore wie `handeln.kandidaten()`: Vola-Tor der Familie, Familie
aktiv, Umsatz-Bezug der Familie, Hebel-Deckel ≥ `max_hebel`.

### Einstiegskette (je Kandidat, in dieser Reihenfolge – 1:1 aus
`handeln.pruefe_einstiege()` übernommen)

1. Platzlimit: `len(offene Positionen) < max_offene_anlaeufe` (kein
   Wartende-Aufträge-Konzept im Rücktest, siehe Vereinfachung unten).
2. Signal-Wechsel-Gatter: `signal_wechsel.zugelassen()` – nur wenn sich die
   Richtung für diese Basis seit dem letzten Einstieg geändert hat.
3. Nicht schon offen für diese Basis, nicht in Abklingzeit
   (`abklingzeit_tage` nach dem letzten Stop/Liquidation).
4. Wochenend-Sperre für Familien `aktie`/`rohstoff` ab `freitag_stopp_utc`.
5. Familien-Anteilsdeckel (`max_anteil_gesamt`).
6. `anlauf()`-Äquivalent: Signal aus `indikatoren.lage()` muss der
   Kandidaten-Richtung entsprechen; Einstieg/Stop/Ziel aus ATR
   (`einstieg_atr_abschlag`/`stop_atr_faktor`/`ziel_atr_faktor`), Größe aus
   `bot.groesse()`.
7. Gesamt-Margin-Deckel (`max_margin_gesamt_usd`).
8. Pflichtzahlen (`bot.pruefpflicht()`): beobachtete Trefferquote muss die
   nötige um mehr als 2 Prozentpunkte übersteigen (`traegt`).
9. Hebel unter dem Deckel (`hebel_traegt`).

### Ausstiegsvorrang (je 1H-Kerze, 1:1 aus `handeln.pruefe_ausstiege()`)

**Liquidation > Stop > Ziel.** Liquidation geht vor, weil ihre Schwelle
immer hinter dem Stop liegt – wird sie erreicht, hat der Kurs den Stop auf
dem Weg dorthin schon durchlaufen. Erst wenn keiner der drei greift, wird
der Trailing-Stop nachgezogen (kann den Stop-Preis für die nächste Prüfung
verschieben, löst selbst keinen Ausstieg aus).

### Vereinfachung gegenüber Live

Eine Limit-Order gilt im Rücktest als sofort gefüllt, sobald der Kurs die
Einstiegsmarke innerhalb der Kerze berührt. Die Live-Mechanik aus
`handeln._warten_auf_fuellung()`/`wartende_auftraege()` (Order bleibt
liegen, Timeout, Storno) ist Betriebslogik einer echten Börsenverbindung
und für einen historischen Rücktest ohne echte Order nicht sinnvoll
nachzubilden.

## Ausgabe

Ein Leistungsbericht für die AKTUELLE `xperp/wachen.json` über den
gewählten Rückblickzeitraum, analog zu den bestehenden
`berichte/<datum>-<spur>/`-Ordnern, aber ohne Vorschlag (es wird nichts
geändert):

- Gesamt-G/V, Anzahl Runden, Trefferquote (Ziel/Stop/Liquidation getrennt
  ausgewiesen), größter Rücklauf (Drawdown), je Familie aufgeschlüsselt.
- Je Ausstiegsgrund-Anteil (wie viele Runden endeten in Liquidation –
  ein hoher Anteil wäre ein Befund über den Hebel-Deckel, kein Fehler der
  Engine).
- Funding-Anteil am Gesamtergebnis separat ausgewiesen (Spur 3 hat
  gezeigt, dass Kosten, die Live mitlaufen, im Rücktest sichtbar bleiben
  müssen, sonst empfiehlt der Rücktest eine Strategie, die live schlechter
  abschneidet).

## Tests

TDD wie der Rest des Projekts. Testordner-Konvention wie der übrige
xperp-Code: `test_*.py` neben dem jeweiligen Modul und zusätzlich unter
`tests/`, beide `unittest`. Synthetische Kerzenreihen (kein Netzzugriff in
Tests) nach demselben Muster wie `tests/test_kraken_modell.py` und die
bestehenden xperp-Tests (`tages_kerzen_quelle`-Seam in `bot.py`,
`cvd_quelle`-Seam in `indikatoren.py` – beide bereits für Tests vorgesehen
und im Rücktest wiederverwendbar).

## Risiken (für die Final Review explizit zu prüfen)

- **Survivorship-Bias:** heute delistete Kontrakte fehlen im Universum –
  bewusst akzeptiert, siehe Abgrenzung.
- **CVD/LLM ausgeklammert:** der Rücktest bewertet eine Teilmenge der
  Live-Strategie (ohne diese beiden hochgewichteten Komponenten). Ein
  Vorschlag aus dieser Engine (spätere Spec B) gilt für die Strategie OHNE
  CVD/LLM, nicht für die volle Live-Fassung.
- **Funding-Endpunkt unverifiziert:** der genaue OKX-Endpunkt und sein
  Paginierungsschema für historische Funding-Sätze sind beim Schreiben
  dieser Spec nicht gegen die echte API geprüft (kein Netzzugriff in der
  Planungssitzung) – das Implementierungsteam prüft ihn beim Bau von
  `funding_historie()` gegen die echte OKX-Dokumentation/Antwort.
- **Rechenlast der Rangliste je Zeitschritt:** `auswahl.kennzahlen()` über
  ~164 Instrumente bei JEDEM 4H-Schritt über einen mehrmonatigen
  Rückblickzeitraum kann je nach Fenstergröße spürbar Rechenzeit kosten
  (reine Python-Schleifen, kein Netzzugriff mehr nach dem Cache-Aufbau) –
  im Plan als Punkt für einen Performance-Check vorzusehen, nicht vorab zu
  lösen.

## Danach

**Spec B (eigene, spätere Spec):** Die woechentliche Optimierungsschleife
auf dieser Engine – neues `aenderbar`-Set in `spuren.json` für Spur 2
(`stop_atr_faktor`, `ziel_atr_faktor`, `max_hebel`, `trailing_*`, ggf.
`vola_tor_pa` je Familie), Anbindung an `suche.py`s Hügel-Klettern,
Wochenbericht/Vorschlag wie Spur 1/3.

**Grid-Modus (eigene, spätere Ausbaustufe):** eigene Konstruktion (Stufen,
gemeinsamer Boden, Kill-Switch-Prüfung über alle Stufen) – nicht Teil
dieser oder der nächsten Spec.
