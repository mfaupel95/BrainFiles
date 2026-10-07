# Spec: Verbesserer Ausbaustufe 2a — Spur 3 (Kraken, Mehrwaehrung)

Stand 07.10.2026. Status: Entwurf, wartet auf Abnahme durch Max.
Bereich `handel` (`Agenten/Handel/verbesserer/`). Vorgaenger: Ausbaustufe 1.5
(F7 Ausrichten, F4 Holdout; Commits `a0f4d6ad`..`b815a197`). Spur 2 (XPERP:
Margin/Funding/Liquidation) ist eigene Folgespec — diese Stufe legt nur die
Interface-Stelle dafuer an, baut die Logik nicht.

## Ziel

Den woechentlichen Verbesserer auf die dritte, bereits **live laufende**
Handelsspur ausweiten (`Agenten/Handel/kraken/`, `handel_erlaubt: true` seit
01.10.2026). Mechanisch ist Spur 3 ein naher Verwandter von Spur 1 (identische
Stop-Formel, identisches 2:1-Chance/Risiko-Ziel, gemeinsames Scoring in
`scanner/bewertung.py`) — der Unterschied liegt in vier Annahmen, die
`ruecktest.py` heute fest verdrahtet: Gebuehr, Deckel-Feldnamen, Kerzenquelle,
Waehrung. Diese Stufe generalisiert sie **einmal**, mit Spur 2 (XPERP) als
zweitem, noch unbekanntem Verbraucher im Blick — ohne XPERPs Logik
vorwegzunehmen (YAGNI).

**Erfolg:** Der Verbesserer kann fuer Spur 3 denselben woechentlichen Zyklus
(`lauf.einmal("spur3")`) fahren wie fuer Spur 1 — Kerzen holen, ausrichten,
Suche mit Holdout-Sperre, Vorschlag oder Grund — und rechnet dabei korrekt in
EUR, unabhaengig davon, in welcher Quotewaehrung (EUR/USDC/EURC) ein
Kandidat-Instrument notiert.

## Nicht Teil dieser Stufe

- Spur 2 (XPERP): Margin, Hebel, Funding, Liquidation als dritter
  Ausstiegsgrund. Nur die Interface-Stelle (`modell=`-Parameter in
  `simuliere()`) entsteht, keine XPERP-spezifische Implementierung.
- Das Signalwechsel-Gatter (`Handel/signal_wechsel.py`, seit 03.10.2026 fuer
  alle Live-Spuren inkl. Spur 1 verdrahtet) und der 15-Minuten-Takt der
  Kraken-Spur. Das ist eine **modulweite** Genauigkeitsluecke des
  Tages-Walk-Forward-Modells, die auch Spur 1 schon betrifft — eigene
  Folgearbeit, nicht Teil dieser Ausweitung.
- `anwenden.py`, die Denylist-Felder, `handel_erlaubt`, `stillgelegt`,
  `bedingung_5_aktiv`, `trigger_modus`, `quote_vorrang`,
  `mindest_guthaben_je_quote` — bleiben auerhalb jeder Whitelist, unveraendert
  durch Weglassen aus `spuren.json["spur3"]["aenderbar"]`.
- `auto_anwenden` bleibt `false`.

## Das Kostenmodell-Plugin (fuer Spur 3 UND spaeter Spur 2)

`ruecktest.simuliere()` nimmt einen neuen optionalen Parameter `modell` —
vier Hook-Funktionen statt fest verdrahteter Spot-Annahmen:

| Hook | Default (`SPOT_MODELL`, heutiges Verhalten) | Spur 3 (`KrakenModell`) | Spur 2 spaeter (nicht hier gebaut) |
|---|---|---|---|
| `gebuehr_pct(inst, tag)` | `kosten.GEBUEHR_PCT` (0,05 %), konstant | liest `gebuehr_taker` **live** aus Kraken-`wachen.json` (variiert seit 03.09.2026 mehrfach) | OKX-Taker + Funding getrennt |
| `pruefe_ausstieg(position, kerze)` | Stop am Tagestief vor Ziel am Tageshoch (heutige Logik aus `simuliere()`) | unveraendert | zusaetzlich Liquidation pruefen, vor Stop |
| `laufende_kosten(position, tag)` | `0.0` | `0.0` | Funding-Satz je gehaltenem Tag |
| `in_basiswaehrung(betrag, inst, tag)` | Identitaet (eine Waehrung) | USDC-/EURC-Betraege am Tagesschlusskurs nach EUR | Identitaet (USD) |

`simuliere(matrix, kerzen_je_inst, kandidat, start_tag, end_tag, modell=SPOT_MODELL)`.
Ruft Spur 1 ohne `modell` auf, bleibt das Verhalten exakt wie heute — alle
122 Bestandstests laufen unveraendert. `walk_forward()` und `holdout()`
reichen `modell` durch (eigener optionaler Parameter, Default `SPOT_MODELL`).

`gebuehr_pct`/`laufende_kosten` wirken je Runde in `simuliere()` an der
Stelle, an der heute `GEBUEHR_PCT` direkt gelesen wird (Einstieg: Gebuehr auf
den Einsatz; Ausstieg: Gebuehr auf den Erloes plus `laufende_kosten` summiert
ueber die Haltedauer). `in_basiswaehrung` wird auf `gv`/`einsatz`/`erloes`
jeder fertigen Runde angewendet, **bevor** sie in `kennzahlen()` einfliesst —
`kennzahlen()` selbst bleibt waehrungsblind und unveraendert.

## Kraken-Kerzenquelle

Neues Modul `verbesserer/kraken_kerzen.py`, Signatur identisch zu
`kerzen.py` (`hole(inst, tage, cache_dir) -> kerzen`, `laden(inst, cache_dir)
-> (kerzen, alter)`), gleiche Zeilenform `[ts, o, h, l, c, vol]`. Quelle ist
Krakens eigene OHLC-API (`kraken/kraken.py`, Intervall 1440 = Tageskerzen)
statt OKX `history-candles`. `ausrichten()`/`simuliere()` sehen keinen
Unterschied zur OKX-Quelle.

`lauf.py` waehlt die Kerzenquelle **je Spur** statt sie fest auf `kerzen.hole`
zu verdrahten: ein neuer Schluessel `spuren.json["spur3"]["kerzen_modul"] =
"kraken_kerzen"`, `lauf.einmal()` importiert das benannte Modul dynamisch
(Default `"kerzen"` fuer Bestandsspuren, kein Verhaltensunterschied fuer
Spur 1).

## Waehrungsumrechnung

Watchlist fuer Spur 3 enthaelt **alle drei Quote-Varianten einzeln** (17 EUR +
3 EURC + 13 USDC = 33 Eintraege) — bewusste Entscheidung (Ruling): die Suche
kann dieselbe Basis (z. B. XBT) gleichzeitig in mehreren Waehrungen als
getrennte Kandidaten halten, anders als das echte Buch (das genau eine
Waehrung je Buch faehrt, `_quote_vorrang`). Jede Runde wird vor `kennzahlen()`
nach EUR umgerechnet (`in_basiswaehrung`):

- **USDC -> EUR**: Tagesschlusskurs des Kraken-Paares `EURUSDC` (oder
  `USDCEUR`, je nachdem wie Kraken es listet — bei Implementierung gegen
  `AssetPairs` pruefen, analog `kraken/quote.py`).
- **EURC -> EUR**: Tagesschlusskurs des Kraken-Paares `EURCEUR` falls
  vorhanden; EURC ist ein Euro-Stablecoin, die Abweichung von 1,0 ist
  typischerweise klein, wird aber **gemessen, nicht angenommen** — kein
  hartcodiertes 1:1.
- Beide Kursreihen werden ueber `kraken_kerzen.hole()`/`laden()` wie jedes
  andere Instrument geholt und gecacht.
- Fehlt ein Tageskurs fuer einen Umrechnungstag (Luecke), gilt dieselbe Regel
  wie bei `ausrichten()`: nicht stillschweigend mit 1,0 auffuellen, sondern
  die Runde mit einem Hinweis im Bericht markieren (Grenzfall, kein
  Blocker fuer diese Stufe — Verhalten im Plan festlegen).

## Konfiguration

- `spuren.json["spur3"]`:
  - `name`: `"Kraken/EUR"`, `waehrung`: `"EUR"`.
  - `journal`/`zustand`/`wachen`/`berichte` -> `../kraken/...` (analog Spur 1).
  - `bewertung_datei` -> `../scanner/bewertung.py` (**dieselbe** Datei wie
    Spur 1 — gemeinsames Scoring, siehe naechster Punkt).
  - `kerzen_modul`: `"kraken_kerzen"`.
  - `aenderbar.wachen.json`: nur Spur-3-eigene Gates (`mindest_score`,
    `max_volatilitaet_pa`, `mindest_chance_risiko`,
    `pflicht_stop_prozent_min/max`, `abklingzeit_tage`, `watchlist`) —
    **keine** `bewertung.py`-Gewichte.
- `konfig.json`: neuer Schalter `gewichte_durchsuchbar` (Default `true`).
  `suche.nachbarn()` erzeugt Gewichts-Nachbarn nur, wenn
  `konfig.get("gewichte_durchsuchbar", True)` — Spur 3 setzt ihn in ihrem
  Lauf-Konfig-Override auf `false` (Ruling: Gewichte sind shared mit Spur 1,
  ein Kraken-Befund darf Spur 1s Live-Scoring nicht lautlos mitaendern).
- `suche.DENYLIST` erweitert um die EUR-Deckel-Namen aus `kraken/wachen.json`:
  `max_pro_trade_eur`, `max_gesamt_eur`, `drawdown_halbierung_usd` (Kraken
  nennt sein EUR-Drawdown-Feld historisch `_usd` — siehe
  `kraken/wachen.json`-Kommentar, nicht unsere Aufgabe das umzubenennen),
  `kill_switch_gesamt_eur`. Zweite Verteidigungslinie zusaetzlich zur
  Whitelist.
- `basis_kandidat()` liest die Deckel-Feldnamen generisch statt hartcodiert
  `_usd`: ein kleines Mapping (`spur["deckel_felder"]` oder Erkennung ueber
  vorhandene Schluessel) statt vier Einzelnamen im Code.

## Tests

- `tests/test_simuliere_modell.py` (neu): `SPOT_MODELL`-Default verhaelt sich
  exakt wie die bisherige `simuliere()`-Logik (Regressionstest gegen die
  Fixtures aus `test_ruecktest_sim.py`); ein Fake-Modell mit abweichender
  `gebuehr_pct` aendert `gv` nachvollziehbar; `in_basiswaehrung` wird auf
  jede Runde angewendet, bevor `kennzahlen()` sie sieht.
- `tests/test_kraken_kerzen.py` (neu): `hole()`/`laden()` liefern dieselbe
  Zeilenform wie `kerzen.py`, Cache-Verhalten identisch (Fake-HTTP wie
  `test_kerzen.py`).
- `tests/test_waehrungsumrechnung.py` (neu): USDC-Runde wird korrekt nach
  EUR skaliert; fehlender Umrechnungstag wird gemeldet, nicht mit 1,0
  aufgefuellt; EUR-Runden bleiben unveraendert (Identitaet).
- `tests/test_suche_gewichte_schalter.py` (neu): `gewichte_durchsuchbar=false`
  -> `nachbarn()` liefert keine Gewichts-Varianten; Default `true` ->
  Bestandsverhalten unveraendert (Regression gegen `test_suche_raum.py`).
- Bestand: alle 122 Modul-Tests bleiben gruen. Lauf:
  `cd Agenten/Handel && scanner/.venv/Scripts/python.exe -m unittest discover
  -s verbesserer/tests`.

## Risiken

- Zwei Positionen in derselben Basis (z. B. `XXBTZEUR` und `XBTUSDC`)
  gleichzeitig sind ein akzeptiertes Ruling, kein Bug — weicht aber vom
  echten Buch ab, das nur eine Quotewaehrung faehrt. Ergebnisse sind
  entsprechend als "was waere, wenn alle drei Waehrungen parallel liefen"
  zu lesen, nicht als Prognose fuer das tatsaechliche Buch.
- Wechselkurs-Luecken (USDC/EURC-Paar fehlt an einem Tag) koennen die
  Holdout-Sperre haeufiger "zu wenig Historie" melden, wenn sie nicht
  ausnahmsweise mit dem letzten bekannten Kurs ueberbrueckt werden duerfen —
  Entscheidung dazu im Plan explizit treffen, nicht stillschweigend im Code.
- Kraken-Gebuehr ist seit 03.09.2026 dreimal geaendert worden
  (`gebuehr_taker` 0,004 -> 0 -> 0,006); das Live-Lesen aus `wachen.json`
  macht den Backtest in Zukunft zwar aktuell, aber auch vom aktuellen Stand
  abhaengig — ein Rueckvergleich ueber mehrere Monate rechnet implizit mit
  der HEUTIGEN Gebuehr, nicht der historisch gueltigen. Dasselbe Risiko trug
  Spur 1 schon vor `gebuehr_umstellung_datum`; hier nicht geloest, nur
  benannt.
- Diese Stufe baut die Interface-Stelle fuer Spur 2, legt sich aber nicht auf
  deren genaue Form fest — es ist moeglich, dass XPERPs Bedarf
  (`pruefe_ausstieg` mit Liquidation VOR Stop, Funding ueber Haltedauer) eine
  kleine Anpassung der Hook-Signaturen erzwingt. Das ist eingeplant, kein
  Zeichen fuer einen falschen Entwurf.

## Umsetzungsreihenfolge (Vorschlag fuer den Plan)

1. `SPOT_MODELL`/`modell`-Parameter in `simuliere()`/`walk_forward()`/
   `holdout()`, Regressionstest gegen Bestand.
2. `kraken_kerzen.py` + Test.
3. `KrakenModell` (Gebuehr live, Waehrungsumrechnung) + Test.
4. `gewichte_durchsuchbar`-Schalter in `suche.nachbarn()` + Test.
5. Denylist-Erweiterung, `basis_kandidat()`-Deckel-Mapping.
6. `spuren.json["spur3"]`, `lauf.py` Kerzenquelle-Dispatch je Spur.
7. End-to-End: `lauf.einmal("spur3", kerzen_holen=False)` gegen einen
   gecachten Testbestand, Bericht enthaelt EUR-Zahlen.

Je Schritt eigener Commit, `git add` namentlich. Versionierte Dateien nur per
gezieltem Ersatz aendern (CRLF/LF).
