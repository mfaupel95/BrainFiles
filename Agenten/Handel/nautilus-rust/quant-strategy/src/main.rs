//! quant-strategy — EXECUTION.
//!
//! Liest das RankedBook der Research-Ebene, bildet den t-Wert SELBST und
//! wendet seine eigene Evidenz-Huerde an. Haengt von KEINER candle-Crate ab —
//! das Modell ist nicht in diesem Dependency-Graph, also nicht in der Binary.
//!
//! Die Huerde ist eine kompilierte Konstante, kein Config-Feld: eine
//! Strategie, die ihre eigene Evidenz-Huerde senken kann, hat keine.

use anyhow::Result;
use nautilus_backtest::{config::BacktestEngineConfig, engine::BacktestEngine};
use nautilus_model::{
    enums::{AccountType, BookType, OmsType},
    identifiers::Venue,
    instruments::{stubs::audusd_sim, Instrument, InstrumentAny},
    types::Money,
};
use nautilus_trading::examples::strategies::EmaCross;
use quant_signal::RankedBook;
use quant_strategy::evidence::{EvidenceGate, Verdict, MIN_EVIDENCE_T};

/// Bildet den t-Wert aus den gemessenen Werten des Produzenten.
fn t_stat(book: &RankedBook) -> f64 {
    if book.evidence.se_bps <= 0.0 {
        return 0.0;
    }
    book.evidence.net_bps / book.evidence.se_bps
}

/// Prueft, ob eine Instrument-ID venue-qualifiziert ist (SYMBOL.VENUE).
///
/// Seam-Defekt 2 (vadim.blog, Fuenf Seam-Defekte): der Produzent schreibt
/// "AEP", die Engine kennt nur `SYMBOL.VENUE` — jede Name waere als
/// `OutsideUniverse` abgelehnt, und der Fehler meldete "nicht im Universum"
/// statt "falsches Format". Der Guard faengt das VOR der Engine.
fn venue_qualifiziert(id: &str) -> bool {
    let mut teile = id.split('.');
    match (teile.next(), teile.next(), teile.next()) {
        (Some(sym), Some(ven), None) => !sym.is_empty() && !ven.is_empty(),
        _ => false,
    }
}

/// Validiert das ganze Buch: jede Instrument-ID muss venue-qualifiziert sein.
fn validiere_instrument_ids(book: &RankedBook) -> anyhow::Result<()> {
    for w in &book.weights {
        if !venue_qualifiziert(&w.instrument_id) {
            anyhow::bail!(
                "Buch abgelehnt: '{}' ist keine SYMBOL.VENUE-ID \
                 (die Engine kennt nur venue-qualifizierte Instrumente)",
                w.instrument_id
            );
        }
    }
    Ok(())
}

/// Notional-Massstab der Zielgroesse — bewusst f64, keine Integer-Anzahl.
///
/// Seam-Defekt 3: `target_units = weight * max_units_per_name` als
/// Integer-Multiplikation truncatet 0.01 * 3 auf NULL und erzeugt fuer
/// jedes Buch mit mehr als drei Namen je Seite keine Targets. Die Grenze
/// ist ein Massstab, kein Stueckzahl-Limit: kontinuierlich rechnen.
const MAX_UNITS_PER_NAME: f64 = 3.0;

/// Zielgroesse aus einem Gewicht (kontinuierlich, nie vorher auf Integer
/// gerundet — sonst Defekt 3). Das Vorzeichen des Gewichts gehoert der
/// Richtung (negativ = Short), nie der Menge: Zielgroesse = |gewicht| x
/// Massstab.
fn zielgroesse(gewicht: f64) -> f64 {
    gewicht.abs() * MAX_UNITS_PER_NAME
}

fn main() -> Result<()> {
    // 1. Das Buch der Research-Ebene lesen.
    let raw = std::fs::read_to_string("ranked_book.json")?;
    let book: RankedBook = serde_json::from_str(&raw)?;
    // Seam-Guard: keine nackte Instrument-ID darf zur Engine durchkommen.
    validiere_instrument_ids(&book)?;
    let t = t_stat(&book);

    println!(
        "quant-strategy: Buch gelesen, {} Gewichte, dollar-neutral: {}",
        book.weights.len(),
        book.is_dollar_neutral(1e-9)
    );
    println!(
        "  evidence: net={:.3} bps, n={}, se={:.3}, folds={}, positive={}",
        book.evidence.net_bps,
        book.evidence.n,
        book.evidence.se_bps,
        book.evidence.folds,
        book.evidence.positive_folds
    );
    println!("  t = {:.2} (Huerde {:.1})", t, MIN_EVIDENCE_T);

    // 2. Die Engine entscheidet. Kein Modell, kein Score — nur die Zahl.
    match EvidenceGate::decide(&book.evidence) {
        Verdict::Refuse { reason } => {
            println!(
                "  book state   book has no demonstrated skill: {} (net={:.3} bps over n={})",
                reason, book.evidence.net_bps, book.evidence.n
            );
            println!("  rebalances   0");
            println!("  positions    0 opened at the venue");
            println!("  -> Leg A: das Modell ist entfernbar, das System ueberlebt.");
            return Ok(());
        }
        Verdict::Admit => {}
    }

    // 3. Nur wenn die Evidenz haelt: Zielgroessen aus den Gewichten bilden
    //    (Seam-Guard Defekt 3, kontinuierlich) und Backtest fahren. Der
    //    echte Modell-Anschluss haengt hier ein: w.gewicht -> Richtung,
    //    zielgroesse(w.gewicht) -> Menge.
    println!("  -> Evidenz haelt, Backtest laeuft.");
    for w in &book.weights {
        let richtung = if w.weight >= 0.0 { "long" } else { "short" };
        println!(
            "    ziel {} {} x {:.2}",
            richtung,
            w.instrument_id,
            zielgroesse(w.weight)
        );
    }
    let mut engine = BacktestEngine::new(BacktestEngineConfig::default())?;
    engine.add_venue(
        nautilus_backtest::config::SimulatedVenueConfig::builder()
            .venue(Venue::from("SIM"))
            .oms_type(OmsType::Hedging)
            .account_type(AccountType::Margin)
            .book_type(BookType::L1_MBP)
            .starting_balances(vec![Money::from("1_000_000 USD")])
            .build()?,
    )?;

    let instrument = InstrumentAny::CurrencyPair(audusd_sim());
    let instrument_id = instrument.id();
    engine.add_instrument(&instrument)?;

    // Demo-Daten: ein paar synthetische Quotes.
    let quotes = generate_quotes(instrument_id);
    engine.add_data(quotes, None, true, true)?;

    let strategy = EmaCross::new(
        instrument_id,
        nautilus_model::types::Quantity::from("100000"),
        10,
        20,
    );
    engine.add_strategy(strategy)?;
    engine.run(None, None, None, false)?;
    println!("  -> Backtest abgeschlossen.");
    Ok(())
}

/// Erzeugt synthetische Quote-Ticks fuer den Demo-Backtest.
fn generate_quotes(
    instrument_id: nautilus_model::identifiers::InstrumentId,
) -> Vec<nautilus_model::data::Data> {
    use nautilus_model::{
        data::{Data, QuoteTick},
        types::{Price, Quantity},
    };
    let mut quotes = Vec::new();
    let mut bid = 1.0000_f64;
    for i in 0..2000 {
        let ts = 1_600_000_000_000_000_000_u64 + (i as u64) * 1_000_000_000;
        bid += 0.0001 * ((i % 3) as f64 - 1.0);
        let ask = bid + 0.0002;
        let tick = QuoteTick::new(
            instrument_id,
            Price::from(bid.to_string()),
            Price::from(ask.to_string()),
            Quantity::from("1.0"),
            Quantity::from("1.0"),
            ts.into(),
            ts.into(),
        );
        quotes.push(Data::Quote(tick));
    }
    quotes
}

// ---------------------------------------------------------------------------
// Tests: Seam-Guards gegen die Fuenf Seam-Defekte (vadim.blog). Diese Tests
// existieren, BEVOR ein echtes Modell an die Engine angeschlossen wird — der
// Anschluss muss von Anfang an auf den Guards aufbauen.
// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;
    use quant_signal::BookEvidence;

    fn buch(ids: &[&str]) -> RankedBook {
        RankedBook {
            weights: ids
                .iter()
                .map(|id| quant_signal::RankedWeight {
                    instrument_id: (*id).to_string(),
                    weight: 0.5,
                })
                .collect(),
            evidence: BookEvidence {
                net_bps: 3.5,
                n: 84,
                se_bps: 1.0,
                folds: 5,
                positive_folds: 3,
            },
        }
    }

    // Defekt 2: nackte Ticker vs. venue-qualifizierte IDs. Der Produzent
    // schrieb "AEP", die Engine kennt nur SYMBOL.VENUE — ohne Guard waere
    // jede Name als OutsideUniverse abgelehnt, mit falscher Fehlermeldung.
    #[test]
    fn nackter_ticker_wird_abgelehnt() {
        assert!(!venue_qualifiziert("AEP"));
        assert!(!venue_qualifiziert("BTC-USDT-SWAP"));
        assert!(!venue_qualifiziert(""));
        assert!(!venue_qualifiziert(".SIM"));
        assert!(!venue_qualifiziert("AEP."));
        assert!(!venue_qualifiziert("A.SIM.X")); // zwei Punkte
    }

    #[test]
    fn venue_qualifizierte_id_kommt_durch() {
        assert!(venue_qualifiziert("AEP.SIM"));
        assert!(venue_qualifiziert("BTC-USDT-SWAP.OKX"));
        assert!(venue_qualifiziert("ETH-USDT-SWAP.OKX"));
    }

    #[test]
    fn buch_mit_nacktem_ticker_wird_als_ganzes_abgelehnt() {
        let b = buch(&["AEP", "XOM.SIM"]);
        assert!(validiere_instrument_ids(&b).is_err());
    }

    #[test]
    fn buch_mit_qualifizierten_ids_ist_gueltig() {
        let b = buch(&["AEP.SIM", "XOM.SIM"]);
        assert!(validiere_instrument_ids(&b).is_ok());
    }

    // Defekt 3: target_units = weight * max_units_per_name als Integer
    // truncatet 0.01 * 3 auf NULL -> keine Targets bei >3 Namen je Seite.
    // Die Grenze ist ein Notional-Massstab, keine Stueckzahl.
    #[test]
    fn kleine_gewichte_erzeugen_keine_nullziele() {
        let g = zielgroesse(0.01);
        assert!(g > 0.0, "0.01 * 3.0 muss > 0 sein, war {}", g);
        assert!(!zielgroesse(0.0).is_nan());
    }

    #[test]
    fn zielgroesse_ist_kontinuierlich_kein_integer_truncate() {
        // 0.01 * 3 = 0.03 — nicht 0. Und 10 Namen je Seite a 0.01 ergeben
        // je ein ZIEL (10 * 0.03 = 0.30 gesamt), nicht null Targets.
        assert!((zielgroesse(0.01) - 0.03).abs() < 1e-12);
        let ziele: Vec<f64> = (0..10).map(|_| zielgroesse(0.01)).collect();
        assert!(zieles_sum(ziele) > 0.0);
    }

    fn zieles_sum(v: Vec<f64>) -> f64 {
        v.iter().sum()
    }

    #[test]
    fn negative_gewichte_short_seite_erzeugen_ebenso_ziele() {
        // Short-Seite: negatives Gewicht. Nur |gewicht| * Massstab ist
        // eine Zielgroesse; das Vorzeichen gehoert der Richtung, nicht der
        // Menge. Ohne Absolutwert waere die Short-Seite negativ und wuerde
        // die Long-Seite aufrechnen — hier zaehlt nur, dass > 0 Ziele
        // entstehen.
        let z: f64 = zielgroesse(-0.01);
        assert!(z > 0.0, "Short-Seite muss Ziele erzeugen, war {}", z);
    }
}
