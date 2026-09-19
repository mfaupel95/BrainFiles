# NautilusTrader + candle: Rust-KI-Stack

NautilusTrader hat eine vollstaendige Rust-Implementierung unter `crates/`
(Strategien, Actors, Backtests, Live-Trading OHNE Python). Die Crates sind
unabhaengig auf crates.io publiziert: `nautilus-backtest`, `nautilus-common`,
`nautilus-execution`, `nautilus-model`, `nautilus-trading` (Stand 0.64),
fuer Live `nautilus-live` + `nautilus-okx` (OKX-Adapter existiert in Rust).
MSRV 1.98.1. Referenz-Workspace: `Agenten/Handel/nautilus-rust/` (3 Crates).

## candle ist NICHT eine Candlestick-Bibliothek
`candle` = Hugging Faces minimalistisches ML-Framework fuer Rust (Tensoren,
Autograd, NN-Layer). Crates `candle-core`/`candle-nn` (0.11). Candlestick-
Pattern (Doji, Hammer) haben damit nichts zu tun — die Namenskollision kostet
Zeit.

## Zwei-Ebenen-Architektur (der Kern des Designs)
Trenne Research (Modell-Fitting) und Execution (Order) auf der
**Dependency-Ebene**, nicht per Konvention. In Cargo ist der Plane-Ban eine
Eigenschaft des Artefakts: `quant-strategy` kann candle nicht aufrufen, weil
`candle-core` nicht in seinem Dependency-Graph ist (Symbol nicht gelinkt);
`quant-alpha` kann nicht an `OrderApi` kommen, aus demselben Grund. Das
portiert NICHT nach Python — dort ist ein Plane-Ban ein Source-Scan plus
Versprechen, ein Import und die Grenze ist weg.

- `quant-signal` (NEUTRAL): das gemeinsame Schema (RankedBook, BookEvidence),
  haengt nur von serde ab.
- `quant-alpha` (AI_CONTROL): fitet mit candle, haengt von KEINER nautilus-*
  Crate ab.
- `quant-strategy` (EXECUTION): nautilus-Crates, haengt von KEINER candle-
  Crate ab.
- `quant-planes` (VERIFICATION): audit der anderen transitiv ueber
  `Cargo.lock` (eine Dependency-of-a-Dependency kann eine verbotene Crate
  einschmuggeln).

## Was ueber die Grenze geht: Ranked Book, null Gewichte
Die zwei Haelfte kommunizieren ueber eine DATEI, nicht ueber FFI/Prozess:
`quant-alpha` schreibt `ranked_book.json` (Zielgewichte, Summe = 0, plus
BookEvidence = was der Produzent GEMESSEN hat: net_bps, n, se_bps, folds,
positive_folds). Kein Modell, kein Score, kein Tensor. Die Engine bildet den
t-Wert SELBST und wendet ihren eigenen Boden an — `MIN_EVIDENCE_T = 2.0` ist
eine kompilierte Konstante, kein Config-Feld (eine Strategie, die ihre eigene
Evidenz-Huerde senken kann, hat keine). `MIN_EVIDENCE_FOLDS = 2` (ein Block
kann Skill nicht von Regime trennen).

## Fuenf Seam-Defekte (nur beim Verbinden sichtbar)
Jeder Defekt war fuer beide Seiten allein unsichtbar; das Verbinden der zwei
Haelfte fand alle fuenf. In allen fuenf Faellen waren die Tests gruen -
viermal ratifizierte die Testsuite den Bug als Spec (z. B. verbreiterte ein
Test das Risiko-Limit, um die Strategie ueberhaupt handeln zu lassen).
Quelle: vadim.blog/nautilustrader-candle-rust-ai-trading-stack/.

1. **Feiertage leeren das Universum.** Eine Gruppendatei ohne Ticker (Labor
   Day, Thanksgiving, Weihnachten, Trauertag, MLK) liess jeden
   ausgewaehlten Namen an dem Tag fehlen -> jeder Name fiel wegen
   Unvollstaendigkeit -> das ganze Panel war leer, und der Fehler
   beschuldigte Delistings.
2. **Nackte Ticker vs. venue-qualifizierte IDs.** Der Produzent schrieb
   "AEP"; die Engine kennt nur `SYMBOL.VENUE` -> jede Name des ersten
   echten Buches waere als `OutsideUniverse` abgelehnt worden. Die
   Alpha-Ebene hatte nie ein `InstrumentId` gesehen, und die Engine kannte
   nur selbst gebaute Buecher - denen stimmt sie per Konstruktion zu.
3. **Das Risiko-Limit war die Positionsgroesse.** `target_units`
   multiplizierte das Gewicht mit `max_units_per_name` (die GRENZE, kein
   Notional-Massstab): bei 0,01-Gewichten truncatet `0.01 * 3` auf NULL ->
   keine Targets fuer irgendein Buch mit mehr als drei Namen je Seite.
4. **Ein Per-Name-Cap band das ganze Buch.** Mit geheilter Groesse kamen
   nur 36 von 100 Orders durch (3 Kauf + 3 Short x 6 Rebalancen): ein Cap
   fuer EINE Position begrenzte still die Breite des Portfolios.
5. **Der Zensus zeigte auf das falsche Problem.** Jede Buch-Ablehnung trug
   `NoAdmissibleModel`, also las sich ein vorhandenes, gueltiges, bei
   t = 0,49 abgelehntes Buch wie "Datei fehlt". Instrumentation vermengte
   "Datei absent" mit "Modell unzureichend" - der falsche Bug wurde
   zuerst gefixt.

**Gemessener Ausgang des Referenz-Builds** (500 Tage, ~10.600 Ticker/Tag,
490 Namen, 226 Perioden, 5 Faktoren): Modell-Mittel **-2,505 bps** (nur
2/5 Folds positiv, 1/5 Bloecke head-to-head) gegen Momentum **+9,945 bps**.
Kapazitaets-Sweep monoton falsch herum (hidden=0 besser als 4 besser als 8,
je Schritt -3,392 bps): das ist Overfitting, kein Pech. Leg A bestanden:
ohne alle gelernten Modelle verliert das System nichts Demonstrierbares.

## candle-0.11-API (geaendert, kostete Compile-Fehler)
- `Linear::new(weight, bias)` ist jetzt eine FREIE Funktion
  `candle_nn::linear(in_dim, out_dim, vb)` (bzw. `linear_no_bias`/
  `linear_b`). `Linear::new` nimmt nur noch (Tensor, Option<Tensor>).
- `AdamW::new(vars, lr)` heisst jetzt `AdamW::new_lr(vars, lr)` (Config-Typ
  ist `ParamsAdamW`, nicht f64).
- Vor dem Schreiben die Signaturen in
  `~/.cargo/registry/src/index.crates.io-*/candle-nn-0.11.0/src/` pruefen,
  nicht aus dem Gedaechtnis.

## Nautilus-Rust-Backtest (BacktestEngine, low-level)
```rust
let mut engine = BacktestEngine::new(BacktestEngineConfig::default())?;
engine.add_venue(SimulatedVenueConfig::builder()
    .venue(Venue::from("SIM"))
    .oms_type(OmsType::Hedging)
    .account_type(AccountType::Margin)
    .book_type(BookType::L1_MBP)
    .starting_balances(vec![Money::from("1_000_000 USD")])
    .build()?)?;
let instrument = InstrumentAny::CurrencyPair(audusd_sim());
engine.add_instrument(&instrument)?;
engine.add_data(quotes, None, true, true)?;
engine.add_strategy(EmaCross::new(instrument_id, Quantity::from("100000"), 10, 20))?;
engine.run(None, None, None, false)?;
```
- `nautilus-model` braucht Feature `test-support` fuer `stubs::audusd_sim`;
  `nautilus-trading` Feature `examples` fuer `EmaCross`.
- Feature-Flags: `high-precision` (16-stellige Fixpunkt-Praezision, Standard 9;
  fuer Crypto noetig), `streaming` (BacktestNode/Catalog), `defi`.
- mimalloc als Allocator registrieren, um dem Nautilus-CLI zu entsprechen:
  `#[global_allocator] static GLOBAL: MiMalloc = MiMalloc;` +
  `register_allocator_mimalloc()` am Anfang von `main`.
- Rust-Strategie: `nautilus_strategy!`-Makro verdrahtet `StrategyCore`;
  `DataActor`-Trait fuer Daten-Handler (`on_bar`, `on_quote`, `on_trade`);
  Order-API ueber `self.order()` (market, limit, stop_market, bracket).

## 0.64-API-Drift im Demo-Code (kostete Compile-Fehler, nur beim ersten Build sichtbar)
Der quant-strategy-Demo-Backtest stammte aus einem aelteren Blog-Stand und
kompilierte NIE — erst der erste echte `cargo check` fand die geaenderte API.
- `engine.add_data()` nimmt `Vec<Data>`, nicht `Vec<QuoteTick>`: Ticks in
  `Data::Quote(tick)` einpacken, sonst Typfehler gegen die Engine-Signatur.
- `Price::from()`/`Quantity::from()` nehmen STRINGS (`"1.0"`), kein f64 -
  in 0.64 gibt es kein `From<f64>` fuer beide.
- `QuoteTick::new(..., ts, ts)` will `UnixNanos`, nicht `u64`: `ts.into()`.
- Merkregel: API-Formen in den Quellen unter
  `~/.cargo/registry/src/index.crates.io-*/nautilus-*-0.64.0/src/` pruefen,
  NICHT aus dem Gedaechtnis oder aus Blog-Code abtippen.

## Guards gegen Seam-Defekte 2 und 3 (im Referenz-Workspace gebaut)
Die fuenf Defekte (Abschnitt oben) sind im Workspace als Guards VOR der
Engine verdrahtet, damit der spätere Modell-Anschluss sie nicht wieder
einfuehrt:
- **Defekt 2 (nackte Ticker):** `validiere_instrument_ids()` laeuft direkt
  nach dem Einlesen von `ranked_book.json` und lehnt das GANZE Buch ab,
  sobald eine `instrument_id` nicht `SYMBOL.VENUE` ist (genau ein Punkt,
  beide Teile nicht leer) — der Fehler sagt dann "falsches Format" statt
  spaeter "OutsideUniverse". Kein Buch mit nacktem Ticker erreicht die
  Engine.
- **Defekt 3 (Risiko-Limit = Positionsgroesse):** `zielgroesse(gewicht) =
  |gewicht| * MAX_UNITS_PER_NAME` rechnet kontinuierlich als f64, nie als
  Integer-Multiplikation — 0,01-Gewichte ergeben 0,03, nicht 0. Das
  VORZEICHEN des Gewichts gehoert der Richtung, nie der Menge: ein Test,
  der negative Gewichte (Short-Seite) durchreicht, deckt eine
  Vorzeichen-Uebernahme als Menge auf (`abs()` war der Fix).
- Weg, der funktioniert: Guards als freie Funktionen + Tests ZUERST
  schreiben (RED), dann in `main()` an der Seam-Stelle einhaengen — nicht
  erst nachtraeglich. Ein Guard, der nur im Testmodul lebt, ist
  dead_code in der Binary.

## Ehrlichkeits-Disziplin (aus dem Referenz-Build)
- **Removal-Test (Leg A):** alle gelernten Modelle loeschen — ueberlebt das
  System, ist es nicht AI-native. Ein Modell, das nicht geloescht werden kann
  ohne das System zu brechen, ist ein Geisel, kein Asset.
- **Fingerprint jedes Datensatzes** (SHA-256 ueber Assets, Matrizen, Spec,
  Horizont) vor jedem Vergleich zweier Laeufe: anderer Fingerprint = nicht
  dasselbe Panel (Zahlen nicht vergleichbar); gleicher Fingerprint, Zahlen
  bewegt = der Code bewegte sich (Regression). Toleranz 0.1 bps statt 0
  (Float-Reassoziierung durch Compiler-Optimierung ist nicht bit-identisch).
- **Jede Genauigkeits-Statistik auf Preisniveau wird von einem
  Persistenz-Pass besiedelt.** R²=0.9975 behauptet -> Persistenz gibt 0.99979.
  Vor jeder Modell-Behauptung den Persistenz-Baseline rechnen.
- **Monotonicity ist eine Behauptung ueber Form, Overfitting ueber
  Selektion.** Eine monotone Flaeche ueber 186k Kandidaten sagt nichts ueber
  die Echtheit ihres Peaks — das Maximum einer Zero-Edge-Menge ist nie echt.
- **Ein einzelner Testblock ist ein Muenzwurf.** Walk-forward in disjunkte
  Bloecke; ein sauberer 5/5-Sweep ist p=0.0625, 6 Folds ist die kleinste Zahl,
  die 0.05 klaert.
- **Der Vergleich muss einfache Alternativen einschliessen.** Kein Modell
  ausliefern, ohne den Faktor zu nennen, den es schlug, und die
  Same-Period-Tabelle zu zeigen.

## Entscheidungs-Framework
Nutze das Zwei-Ebenen-Design, wenn: ein survivorship-diszipliniertes
Universum existiert; das Modell entfernbar sein muss; die Evidenz-Huerde
ausserhalb des Produzenten-Prozesses lebt; Datenaenderungen von
Codeaenderungen unterscheidbar sind. NICHT nutzen, wenn: der Edge ein
Moving-Average-Crossover ist (der Overhead macht ihn nur langsam zu aendern);
kleine Daten + enge Frist; die AI entscheiden soll (hier schlaegt candle vor,
NautilusTrader verfuegt).

## Ablage
Lauffaehiger Rust-Code gehoert nach `Agenten/Handel/` (versioniert, in der
Sicherung), nicht in die Werkstatt. Neuer Ordner `nautilus-rust/` braucht
`.gitignore`-Freigabe (Whitelist-Falle: sonst unsichtbar fuer git).
