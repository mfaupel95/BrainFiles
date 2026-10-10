# Spec: Verbesserer Spur 2 (XPERP) – wöchentliche Optimierungsschleife (Spec B)

**Datum:** 2026-10-09
**Status:** Entwurf, zur Durchsicht
**Vorgänger:** Spec A, `Werkstatt/spec-verbesserer-spur2-xperp-ruecktest-2026-10-07.md`
(Rücktest-Engine `Agenten/Handel/verbesserer/xperp_ruecktest.py`, committet).
**Zweig:** `claude/verbesserer-spur2-schleife` (eigener Arbeitsbaum `.worktrees/spur2-schleife`).

## Zweck

Spur 1 und 3 haben eine wöchentliche Schleife, die Parameter-Vorschläge für
`wachen.json` macht. Spur 2 (XPERP) hat seit Spec A eine Rücktest-Engine, aber
keine Schleife. Diese Spec baut sie: Sie sucht im festen, engen Parameterraum
einen Satz Werte, der die heutige `xperp/wachen.json` im Walk-Forward schlägt,
und legt daraus **einen Vorschlag** ab. Angewendet wird nichts von selbst: der
Vorschlag geht per Telegram an Max und wird erst mit `/ja` scharf.

## Abgrenzung

- **Nur Trend-Modus** (Long/Short), **ohne LLM-Filter**, **CVD-4h neutral** –
  wie Spec A. Ein Vorschlag gilt für die Strategie OHNE LLM-Filter.
- **Kein Grid.** `grid_*` bleibt gesperrt.
- **Kein automatisches Anwenden.** `auto_anwenden` bleibt `false`.
- **Spur 1 und 3 bleiben unberührt.** `suche.py`, `lauf.py` und deren Tests
  werden nicht verändert (Weg A). Mitgenutzt werden `vorschlag.py`-Bausteine,
  `anwenden.py` (Denylist, Baumprüfung, `.bak`, `git apply`) und der
  Telegram-Weg der Anfrage `verbesserung`.

## Architektur

Neu: `xperp_suche.py` (Kandidatenraum, Nachbarn, Sieb, Koordinatenabstieg),
`xperp_lauf.py` (Orchestrator), `xperp_merkmale.py` (Merkmals-Cache).
Geändert: `spuren.json` (Eintrag `spur2`), Engine (`trailing_aktiv`-Schalter),
`anwenden.py`/`vorschlag.py` nur soweit, dass sie `spur2` und `wachen.json` im
`xperp`-Ordner kennen; bestehendes Verhalten für `spur1`/`spur3` bleibt gleich.

### Datenfluss

1. **Kerzen und Funding** aus dem Cache von `xperp_kerzen.py`; nur erneuert,
   wenn der Abruf gelingt. Fehlt der Cache ganz: harter Abbruch.
2. **Merkmals-Matrix** (`xperp_merkmale.py`): je Instrument und 4H-Schritt die
   von `wachen.json` unabhängigen Kennzahlen (`auswahl.kennzahlen`, Lage,
   `mae_tage`), einmal vorgerechnet. Das ist die teure Stelle (20–35 min).
   Gecacht mit einem Hash über Kerzen- und Universumsdaten; unveränderte
   Daten → Wiederverwendung.
3. **Kandidatenbewertung:** Ein Kandidat (geänderter Parameter-Satz) wird nur
   aus der Matrix bewertet und simuliert (`bewerte`, Tore, Einstieg, Ausstieg,
   Trailing, Funding). Die Rangliste wird nicht neu gerechnet.
4. **Suche:** Koordinatenabstieg über Nachbarwerte, festes Budget
   (`such_budget`), Start bei der Basis (= heutige `wachen.json`).
5. **Sieb → Vorschlag:** `berichte/<datum>-spur2/` mit `bericht.md`,
   `wachen.neu.json`, `commit.txt` (ohne `bewertung.patch`: Spur 2 hat keine
   Gewichte). Zur Not nur ein Kein-Vorschlag-Bericht.

## Suchraum (Whitelist in `spuren.json`, Eintrag `spur2`)

Jeder Wert ist um den heutigen Wert begrenzt:

| Schlüssel | heute | erlaubter Bereich |
|---|---|---|
| `stop_atr_faktor` | 1.5 | 1.0 – 2.5 |
| `ziel_atr_faktor` | 3.0 | 2.0 – 4.5 |
| `einstieg_atr_abschlag` | 0.25 | 0.0 – 0.5 |
| `trailing_trigger_r` | 1.0 | 0.5 – 2.0 |
| `trailing_stop_prozent` | 1.5 (bis 09.10.2026: 0.4) | 0.75 – 3.0, Schritt 0.25 (nachgezogen 10.10.2026, vorher 0.2 – 1.0) |
| `trailing_abstand_floor_pct` | 0.25 | 0.15 – 0.6 |
| `trailing_min_hub_r` | 0.25 | 0.1 – 0.6 |
| `trailing_max_halten_pct` | 5.0 | 3.0 – 8.0 |

`vola_tor_pa` und `min_umsatz_24h_usd` sind nicht im Suchraum: der Rücktest
liest das Vola-Tor aus `auswahl.KATEGORIEN`, und die Krypto-Familie
überschreibt den Umsatz-Bezug - eine Änderung hätte keine Wirkung.

Zusatzbedingung: `ziel_atr_faktor / stop_atr_faktor ≥ 1.5`.

**Immer gesperrt (Denylist in `anwenden.py`, gewinnt vor der Whitelist):**
`max_hebel`, `max_margin_*`, `max_offene_anlaeufe`, `risiko_je_anlauf_usd`,
`kill_switch*`, `drawdown*`, `freigabe`, `herzschlag*`, `handel_erlaubt`,
`trailing_aktiv`, `llm_*`, `papier_faktor`, `familien` (Anteile/Aktivschalter),
alle `grid_*`. `anwenden.py` prüft beim Anwenden jeden geänderten Wert erneut.

## Bewertung und Sieb

- **Maß:** `netto_gv_je_runde` (USD je Runde nach Gebühren und Funding), im
  Walk-Forward mit den Fenstern aus dem Block `spur2` in `konfig.json`
  (`such_tage`, `test_tage`, `schritt_tage`, `holdout_tage`). Auswahl und Prüfung nutzen dieselben Fenster („schwaches
  Sieb“, wie Spur 1; der Holdout-Block unten schließt die Lücke).
- **Ein Kandidat wird nur vorgeschlagen, wenn:** (a) er die Basis im Aggregat
  schlägt, (b) in mehr als der Hälfte der Fenster, mindestens
  `overfit_min_fenster`, (c) mindestens `overfit_min_runden` Runden hat,
  (d) sein Liquidationsanteil nicht über dem der Basis liegt, (e) sein größter
  Rücklauf höchstens 10 % über dem der Basis liegt.
- Die Datenlage (älteste XPERP seit Mai 2026, ~90 Testtage nach 60 Tagen
  Warmup) lässt oft nur wenige Fenster zu; die Fensterzahl steht im Bericht,
  und „kein Vorschlag“ ist ein regulärer Ausgang.

## Verifikation und Freigabe (Atlas-Konsultation 2026-10-10)

Das Sieb oben prüft auf denselben Fenstern, auf denen gesucht wurde: der
Vorschlagende bewertet sich selbst. Der Atlas sagt dazu: der Prüfer muss vom
Vorschlagenden getrennt sein ([verification-asymmetry § model-and-claims](https://agentic-atlas.dev/nodes/verification-asymmetry#model-and-claims)).
Daraus folgt:

- **Holdout als zweite deterministische Stufe.** Die letzten `holdout_tage`
  Tage werden vor Suche und Walk-Forward abgeschnitten (wie Spur 1,
  `ruecktest.holdout()` / `suche.py`) und pro Vorschlag genau einmal bewertet,
  nie in die Suche zurückgespeist. Reihenfolge der Stufen: fünf Siebregeln,
  dann Holdout, zuletzt Max ([verification-asymmetry § model-and-claims](https://agentic-atlas.dev/nodes/verification-asymmetry#model-and-claims)).
  Reicht die Historie nach Abzug nicht, endet der Lauf mit
  `grund="zu wenig Historie fuer Holdout"` statt still ohne Holdout.
- **Holdout-Verschleiß.** Jede Wochenbewertung gibt dem Vorschlagenden
  Information preis; der Atlas nennt den Mechanismus, aber kein Budget
  ([verification-asymmetry § scope-and-boundaries-where-the-asymmetry-fails](https://agentic-atlas.dev/nodes/verification-asymmetry#scope-and-boundaries-where-the-asymmetry-fails)).
  Entwurfsannahme, von Max zu bestätigen: der Bericht zählt die Holdout-
  Auswertungen und meldet den Block nach `holdout_max_nutzungen` (Vorschlag 8)
  als „verbraucht"; der Wert steht in `konfig.json`.
- **Bestanden heißt „Vertrag erfüllt", nicht „besser".** Der Bericht legt neben
  den Diff ([verification-asymmetry § scope-and-boundaries-where-the-asymmetry-fails](https://agentic-atlas.dev/nodes/verification-asymmetry#scope-and-boundaries-where-the-asymmetry-fails)):
  Ergebnis je Fenster (nicht nur das Aggregat), Abstand zur Grenze je Regel,
  das Holdout-Ergebnis und einen festen Absatz „Nicht geprüft" (Fensterzahl,
  geteilte Daten, offene Positionen am Fensterende, nur Trend-Modus ohne
  LLM-Filter).
- **Verstöße bleiben benannte Ausgaben je Regel.** Das Sieb urteilt nicht und
  korrigiert nicht; `anwenden.py` darf einen gescheiterten Vorschlag nicht
  anpassen ([no-duck-left-behind § verification](https://agentic-atlas.dev/nodes/no-duck-left-behind#verification)).

## Wiederherstellung je Stufe

Vor dem Lauf festgelegt, welcher Zug je Stufe gilt
([effect-discipline § implications-the-consequence-map](https://agentic-atlas.dev/nodes/effect-discipline#implications-the-consequence-map)):

| Stufe | Zug | Wirkung nach außen |
|---|---|---|
| Merkmals-Cache | Wiederholen / verwerfen | nur Cache-Datei |
| Suche, Sieb, Holdout | Verwerfen | keine |
| Berichtsordner, `wachen.neu.json` | isoliert, liegt bis zur Freigabe unter `berichte/` | keine Wirkung auf Live |
| Anwenden | Tor (`/ja`) davor, Denylist-Prüfung im Anwenden, Rücknahme danach | ändert `xperp/wachen.json` |

Das Tor sitzt vor der unumkehrbaren Wirkung, nicht danach
([effect-discipline § model-and-claims](https://agentic-atlas.dev/nodes/effect-discipline#model-and-claims)).
**Rücknahme:** `anwenden.py` legt vor dem Schreiben ein zeitgestempeltes `.bak`
an und stellt bei Fehlschlag beide Zieldateien daraus wieder her; für Spur 2
gilt derselbe Pfad, und ein späteres Zurückrollen erfolgt aus diesem `.bak`
bzw. per `git revert` des Anwende-Commits. Ein abgelehnter oder veralteter
Vorschlag kostet nichts, weil er nie in der Live-Datei stand.

## Engine-Änderung: `trailing_aktiv`

Die Engine ruft `trailing.kandidat` heute unabhängig vom Schalter auf. Sie
beachtet künftig `w["trailing_aktiv"]` (aus: kein Nachziehen). Der Schalter
selbst wird nie vorgeschlagen. Test: Basis mit Schalter an/aus liefert
unterschiedliche Ergebnisse bei gleichem Kerzenpfad.

## Fehlerverhalten

Laut, nie still. Fehlt Kerzen-, Funding- oder Merkmals-Cache oder tritt eine
`FundingLuecke` auf, bricht der Lauf mit klarer Meldung ab: kein Vorschlag, kein
Auffüllen mit 0.0. Offene Positionen am Fensterende werden nicht bewertet
(Hinweis im Bericht, bekannte Lücke aus Spec A). Ein Lauf endet in jedem Fall
mit einem Ordner unter `berichte/`. Ein Abbruch schreibt einen Berichtsordner mit dem Grund, aber kein
`commit.txt`. Instrumente ohne vollständigen Cache werden ausgelassen und im
Bericht benannt; unter 3 verbleibenden Instrumenten Abbruch.

## Betrieb

Wöchentlich durch eine eigene Routine `Agenten/Routinen/verbesserer-spur2.ps1`
(setzt `MAXHIRN_ROUTINE=1`, loggt nach `Routinen/logs/`), nach
`handel-wachen.ps1` und getrennt vom Spur-1-Lauf wegen der langen Laufzeit.
Die Routine zeigt auf `verbesserer/.venv/Scripts/python.exe`.

## Tests

- Reine Funktionen mit festen Fixtures: Nachbarn und Wertebereich,
  Zusatzbedingung, Sieb (a–e), Whitelist/Denylist, Patch-Bau für
  `xperp/wachen.json`.
- Merkmals-Cache: Hash-Treffer und -Fehlschlag.
- Ende-zu-Ende mit kleinem synthetischem Universum, ohne Netz.
- Die bestehenden 246 Tests (verbesserer) und 170 Tests (xperp) bleiben
  unverändert grün.

## Nicht Teil dieser Spec

Grid-Modus; LLM-Filter im Rücktest; vollständiger Train/Test-Split über den Holdout hinaus; Bewertung offener
Positionen am Fensterende; Korrektur der 8h-Funding-Annahme im Live-Pfad
(`handeln.buche_funding`, `bot.py:208`) – das ist ein eigener Live-Befund.
