---
id: 20260919-nautilus-candle-rust
title: 'NautilusTrader + candle: Rust-KI-Stack (Zwei-Ebenen-Architektur)'
tags: [handel, system, ki-agenten]
created: 2026-09-19
related: [20260921-prognose-backtest, 20260921-archiv-trading-skills]
summary: 'Wie NautilusTrader (Rust-Crates) und Hugging Face candle (Rust-ML-Framework) in EINEM Cargo-Workspace zusammenarbeiten: Research-Ebene fitet das Modell, Execution-Ebene entscheidet, die Trennung erzwingt der Linker (Dependency-Graph), nicht eine Konvention. Referenz-Build: 4 Crates, 388 Tests, Modell verlor gegen Momentum-Faktor.'
updated: 2026-09-19
---

# NautilusTrader + candle: Rust-KI-Stack

## Was es ist

Die Kombination von **NautilusTrader** (Rust-Core, Python-API) und **candle**
(Hugging Face ML-Framework fuer Rust) zu einem **kompletten Rust-Trading-Stack**
ohne Python. NautilusTrader hat eine vollstaendige Rust-Implementierung unter
`crates/` — man kann Strategien, Actors, Backtests und Live-Trading **ohne
Python** schreiben. candle ist das Gegenstueck fuer das Modell-Fitting.

**WICHTIG — Namenskollision:** `candle` ist **NICHT** eine Candlestick-Charting-
Bibliothek. Es ist Hugging Faces minimalistisches ML-Framework fuer Rust
(Tensoren, Autograd, NN-Layer). Die Crates heissen `candle-core` und
`candle-nn` (Stand 0.11.0). Candlestick-Pattern (Doji, Hammer) haben damit
nichts zu tun.

## Die Kernidee: Zwei-Ebenen-Architektur

Der Referenz-Build (vadim.blog, 4 Crates, 388 Tests) trennt die Ebenen auf der
**Dependency-Ebene**, nicht per Konvention:

| Crate | Ebene | Haengt ab von |
|---|---|---|
| `quant-signal` | NEUTRAL | `serde` (nur das Schema: RankedBook, Abstain-Vokabular, RunReport) |
| `quant-alpha` | AI_CONTROL | `candle-core`, `candle-nn` — **kein** `nautilus-*` |
| `quant-strategy` | EXECUTION | `nautilus-model`, `nautilus-trading`, `nautilus-backtest` — **kein** candle |
| `quant-planes` | VERIFICATION | audit der anderen transitiv ueber `Cargo.lock` |

**Der Plane-Ban ist der Cargo-Dependency-Graph, kein Source-Scan.** `quant-
strategy` kann candle nicht aufrufen, weil `candle-core` nicht in seinem
Dependency-Graph ist — das Symbol ist nicht in die Binary gelinkt. `quant-
alpha` kann nicht an `OrderApi` kommen, aus demselben Grund. Eine
Ein-Prozess-Composition-Root, in der das Modell in die Execution greift, ist
hier **nicht darstellbar** — nicht nur unerwuenscht.

Das portiert NICHT nach Python: dort ist ein Plane-Ban ein Source-Scan plus
Code-Review plus Versprechen. Ein Import und die Grenze ist weg, ohne
Build-Fehler. In Cargo ist die Grenze eine Eigenschaft des Artefakts.

`quant-planes` prueft die zwei Dinge, die der Compiler nicht kann: (1) dass
der Ban **transitiv** durch `Cargo.lock` haelt (eine Dependency-of-a-
Dependency kann eine verbotene Crate einschmuggeln), (2) dass keine Crate dem
Workspace beitritt, ohne ihre Ebene zu deklarieren. `make lint-planes-rust`
meldet 4 Mitglieder, 0 Verstoesse.

## Was ueber die Grenze geht: Ranked Book, null Gewichte

Weil die zwei Haelfte sich nicht aufrufen koennen, kommunizieren sie ueber
eine **Datei**:

- `quant-alpha` schreibt `ranked_book.json` — **Zielgewichte** (plain numbers,
  Summe = 0), kein Modell, kein Score, kein Tensor.
- `quant-strategy` liest sie. Nichts auf der Execution-Seite muss wissen, dass
  ein neuronales Netz existierte; nichts auf der Research-Seite darf ein
  Instrument benennen, das die Engine nicht aufgenommen hat.

Das Fitting selbst ist bewusst unspektakulaer: kleines MLP mit `tanh`-
Aktivierung, trainiert mit `AdamW` (decoupled weight decay). Das interessante
Engineering ist alles downstream der JSON-Datei.

## Die Engine entscheidet (wer hat das Sagen)

`BookEvidence` traegt, was der Produzent **gemessen** hat: `net_bps`, `n`,
`se_bps`, `folds`, `positive_folds`. Bewusst **kein** t, kein p-Wert, kein
Verdikt, kein `admissible` — das sind Schlussfolgerungen, und ein Produzent,
der seine eigene Schlussfolgerung liefert, zertifiziert sich selbst.

Die Engine bildet den t-Wert selbst und wendet ihren eigenen Boden an:

- `MIN_EVIDENCE_T = 2.0` ist eine **kompilierte Konstante**, kein Config-Feld —
  eine Strategie, die ihre eigene Evidenz-Huerde senken kann, hat keine.
- `MIN_EVIDENCE_FOLDS = 2` — ein Block kann Skill nicht von Regime trennen.

Live-Ausgabe des Backtests:
```
book state   book has no demonstrated skill: t = 0.49 on 3.477 bps over n=84,
             below the 2.0 floor
rebalances   0
positions    0 opened at the venue
```

**Das Modell schlaegt vor, die Engine verfuegt.** Die Autoritaet des ML-Layers
endet an der JSON-Datei. Der Dependency-Graph stimmt fuer die Risk-Layer —
auch wenn das Modell zufaellig recht hat.

## Das Ergebnis (ehrlich gemessen)

Das Modell hat seinen Platz NICHT verdient — und das ist der Punkt:

| Signal | net (bps) | t |
|---|---|---|
| `rev_1m` (−1) | +14.851 | 0.84 |
| `amihud` (+1) | +10.911 | 1.36 |
| `log_dollar_volume` (−1) | +7.261 | 0.69 |
| `mom_12_1` (+1) | −3.857 | −0.15 |
| `vol_60d` (−1) | −5.462 | −0.35 |
| **candle hidden=0** | **−9.124** | −0.52 |
| **candle hidden=4** | **−9.330** | −0.57 |
| **candle hidden=8** | **−12.516** | −0.70 |

- Modell-Mittel ueber 5 Regime: **−2.505 bps**, nur 2 von 5 Folds positiv.
- Momentum: **+9.945 bps**. Modell gewann 1 von 5 Bloechen head-to-head.
- Kapazitaets-Sweep monoton in die falsche Richtung: hidden=0 > hidden=4 >
  hidden=8. Ein Modell, das mit mehr Parametern konsistent schlechter wird,
  **overfittet** den Trainingsblock und zahlt out-of-sample dafuer.
- **Leg A (Removal-Test):** alle gelernten Modelle loeschen — das System
  verlor nichts Demonstrierbares. Es ueberlebte, also ist es per Definition
  **nicht AI-native**. Das ist eine gemessene Eigenschaft, keine Behauptung.

## Fuenf Defekte, die nur an der Naht existierten

Jeder war fuer beide Seiten allein unsichtbar. Verbinden fand alle fuenf:

1. **Marktfeiertage leerten das Universum.** 6 von 117 Gruppendateien listen
   keine Ticker (Labor Day, Thanksgiving, Weihnachten, Neujahr, MLK Day). Der
   Leser nannte das "eine kaputte Datei" — aber ein Feiertag listet keine
   Ticker, also fehlt jeder Name an dem Tag, also wird jeder Name wegen
   Unvollstaendigkeit verworfen, und das Universum leert sich komplett. Ein
   Labor Day reduzierte ein 500-Namen-Panel auf nichts — und der Fehler
   beschuldigte Delistings.
2. **Bare Ticker vs. venue-qualifizierte IDs.** Der Produzent schrieb `"AEP"`;
   die Engine identifiziert Instrumente als `SYMBOL.VENUE`. Jeder Name im
   ersten echten Buch waere als `OutsideUniverse` abgelehnt worden.
3. **Das Risiko-Limit war die Positionsgroesse.** `target_units` multiplizierte
   das Gewicht mit `max_units_per_name` — der **Bound**, keine notional scale.
   Bei 0.01-Gewichten eines Dezil-Buchs: `0.01 * 3` = 0. Die Strategie
   berechnete keine Targets fuer jedes Buch mit mehr als 3 Namen pro Seite.
4. **Ein Per-Name-Cap, der den ganzen Korb begrenzte.** Nur 36 von 100 Orders
   gingen durch: 3 Buys + 3 Shorts x 6 Rebalances. Ein Cap, geschrieben um das
   Risiko EINER Position zu begrenzen, begrenzte still die Breite des
   Portfolios — und die Testsuite feierte es.
5. **Der Census zeigte auf das falsche Problem.** Jede Buch-Ablehnung
   protokollierte `NoAdmissibleModel`, also kam ein Buch, das vorhanden,
   gueltig, venue-sourced und bei t=0.49 abgelehnt war, als "kein admissibles
   Modell" zurueck — liest sich wie eine fehlende Datei. Die Instrumentierung
   verwechselte "Datei fehlt" mit "Modell unzureichend".

**Gemeinsamkeit von 3 und 4: die Tests bestanden.** Vier Tests kodierten den
Bug aktiv als Spezifikation. Eine Testsuite, die dieselbe Person schrieb, die
das Missverstaendnis hatte, ratifiziert es — das staerkste Argument dafuer,
die zwei Ebenen auf Artefakt-Ebene uneins sein zu lassen, nicht auf
Assertion-Ebene.

## Sieben Inversionen und der Fingerprint

Der Datensatz wuchs waehrend der Session. Der Fold-Mittel des Modells las
**+6.527, +3.477, +1.427, −7.528** ueber vier Laeufe unveraenderten Codes.
Momentums t ging **2.21 → 1.63 → 2.00 → 1.44** — ueber die Huerde, dann
darunter. Gleicher Code, gleicher "Backtest", vier verschiedene Antworten.

`CrossPanel::fingerprint()` — SHA-256 ueber Assets, beide Matrizen, Spec und
Horizont — machte die Drift **attributierbar**:

- **Anderer Fingerprint** → nicht dasselbe Panel. Zahlen nicht vergleichbar;
  eine Differenz eine Regression zu nennen waere falsch.
- **Gleicher Fingerprint, Zahlen bewegt** → der Code bewegte sich. Nur das ist
  eine Regression.

Toleranz 0.1 bps statt 0, weil eine von einem anderen Compiler-Optimizer
reassoziierte Float-Summe nicht bit-identisch ist — eine Null-Toleranz meldete
ein Compiler-Flag als Regression.

## Statistik-Werkzeuge (fuer Ehrlichkeit gebaut)

- `required_periods()` — wieviel Daten einen Faktor besiedeln koennten. Drei
  von fuenf Faktoren brauchen 32 bis 512 Jahre. Gibt `None` fuer einen
  falsch-signierten Effekt zurueck, nie eine grosse Zahl — ein Faktor, der in
  die falsche Richtung zeigt, kann nicht durch Warten signifikant werden.
- `bonferroni_z(n)` — Signifikanz-Huerde aus der deklarierten Testzahl via
  Acklams inverse Normalverteilung. Eine hartkodierte 2.50 veraltet, sobald
  ein fuenfter Faktor dazukommt — in die Richtung, die Ergebnisse besser
  aussehen laesst.
- `walk_forward_cross` — fuenf disjunkte Bloecke. Ein einzelner Testblock ist
  ein Muenzwurf: Fold 2 las −23.6 bps bei t=−2.63, Fold 3 +5.0 bps. Gleiche
  Strategie, benachbarte Bloecke, gegensaetzliche Urteile.
- `sign_test_p` — distribution-free head-to-head. Ein sauberer 5/5-Sweep ist
  p=0.0625; 6 Folds ist die kleinste Zahl, die 0.05 klaert. Selbst ein
  PERFEKTER Sweep ueber fuenf Fenster klaert keine konventionelle Huerde —
  jedes Ein-Fenster-Ergebnis in irgendeinem Backtest ist ein Muenzwurf mit
  Dezimalpunkt.
- `permutation_null` — shuffelt Forward-Returns **innerhalb jedes Datums**,
  erhaelt die cross-sectionale Struktur des Markts, zerstoert nur die
  Feature-Return-Verbindung. p = (exceeded+1)/(draws+1), weil 0 Ueberschreitungen
  in 200 Ziehungen nicht p=0 beweist, sondern p < ~0.005.

## Der Paper-Loop: 20 Papiere, jedes eine Sackgasse

Ein zweiter, nie stoppender Loop liest 2026er-Forschungspapiere, testet je eine
Behauptung, protokolliert in JSON + LanceDB. 20 Papiere: **13 TESTED_NULL,
6 NOT_IMPLEMENTABLE, 1 PAPER_UNREADABLE**. 96 Messungen, jede mit n und
Baseline.

Wiederkehrender Befund (5 Papiere, 3 Metriken): **jede Genauigkeits-Statistik
auf Preisniveau wird von einem Persistenz-Pass besiedelt.**

- R²=0.9975 behauptet → Persistenz gibt 0.99979 auf 1.447.520 echten
  Minuten-Bars, ueber alle vier Namen.
- Scaled MAE 0.0271 behauptet → Persistenz gibt 0.0222, schlaegt das behauptete
  Modell auf 8 von 12 Namen.
- 94.97% Drei-Klassen-Genauigkeit → ein konstanter Mehrheits-Klassifikator
  scoret 96.51%.
- "Hoechster Sharpe 0.091757 von acht Strategien" → Equal Weight scoret
  0.09343; zwei Sharpes zu trennen, die sich um 0.01 unterscheiden, braucht
  306 Jahre Daten.
- "Monotonicity schliesst Overfitting aus" ueber 186.000 Kombinationen → die
  gleiche monotone Struktur erscheint in geschuffelten Returns, und die beste
  von 186.000 Zero-Edge-Strategien sitzt per Konstruktion 4.93 Standardfehler
  ueber Null.

Monotonicity ist eine Behauptung ueber **Form**; Overfitting ueber
**Selektion**. Eine glatte, ordentliche, wunderschoen monotone Flaeche ueber
186.000 Kandidaten sagt nichts darueber, ob ihr Peak echt ist — und wenn man
das Maximum waehlt, ist er es nie.

## Entscheidungs-Framework: Wann dieser Stack sich lohnt

**Nutze das Zwei-Ebenen-Design, wenn:**
- Ein survivorship-diszipliniertes Universum existiert (500 Tage, ~10.600
  Ticker/Tag gaben dem Vergleich Raum, ehrlich zu sein).
- Das Modell entfernbar sein muss. Leg A — jedes gelernte Modell loeschen —
  ist der Abnahme-Test. Bricht das System, ist die AI tragend und man wartet
  eine Blackbox, die man nicht auditieren kann.
- Die Evidenz-Huerde ausserhalb des Produzenten-Prozesses lebt.
- Datenaenderungen von Codeaenderungen unterscheidbar sind (Fingerprint).
- Der Vergleich einfache Alternativen einschliesst. Kein Modell sollte
  ausgeliefert werden, ohne den Faktor zu nennen, den es schlug, und die
  Same-Period-Tabelle zu zeigen.

**Nutze ihn NICHT, wenn:**
- Dein Edge ein einfacher Moving-Average-Crossover ist. Vier Crates, ein
  Plane-Ban und ein Fingerprint machen ihn nicht profitabel; sie machen ihn
  langsam zu aendern.
- Du kleine Daten und eine enge Frist hast. Der Overhead existiert, um Fehler
  zu fangen, die nur im Massstab auftauchen.
- Du erwartest, dass die AI entscheidet. Hier schlaegt candle vor und
  NautilusTrader verfuegt. Wenn deine These verlangt, dass das Modell Risk
  ueberstimmt, baust du eine andere Architektur.

## NautilusTrader Rust-Crates (praktisch)

- Crates auf crates.io: `nautilus-backtest`, `nautilus-common`,
  `nautilus-execution`, `nautilus-model`, `nautilus-trading` (Stand 0.63).
  Fuer Live: `nautilus-live`, `nautilus-okx` (OKX-Adapter existiert in Rust).
- **MSRV 1.98.1** — passt zur installierten Toolchain (cargo/rustc 1.98.1).
- Feature-Flags: `high-precision` (16-stellige Fixpunkt-Praezision, Standard 9;
  fuer Crypto noetig), `test-support`, `examples`, `streaming`, `defi`.
- **mimalloc** als Allocator registrieren, um dem Nautilus-CLI zu entsprechen:
  `#[global_allocator] static GLOBAL: MiMalloc = MiMalloc;` +
  `register_allocator_mimalloc()` am Anfang von `main`.
- Rust-Strategie: `nautilus_strategy!`-Makro verdrahtet `StrategyCore` in den
  Runtime-Vertrag; `DataActor`-Trait fuer Daten-Handler (`on_bar`, `on_quote`,
  `on_trade`, ...). Order-API ueber `self.order()` (market, limit, stop_market,
  bracket, ...).
- Backtest: `BacktestEngine` (low-level) oder `BacktestNode` (high-level,
  Catalog-Streaming mit `streaming`-Flag).
- Built-in-Strategien aus Python: `node.add_builtin_strategy("GridMarketMaker",
  config)` — existiert, ist aber kein erster-Klasse-Erweiterungspfad fuer
  native Strategien.

## Verwandt

[[Handel-Stack-Repo]], [[Routinen]], [[Verbindungen]], [[Projekte]]
