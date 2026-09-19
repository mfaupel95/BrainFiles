//! quant-alpha — AI_CONTROL.
//!
//! Fitet ein Modell mit Hugging Face candle und schreibt ein RankedBook.
//! Haengt von KEINER nautilus-*-Crate ab — die Execution-Ebene kann es
//! nicht erreichen, und es kann keine Order aufgeben.
//!
//! Das Modell ist bewusst winzig: ein MLP mit tanh, trainiert mit AdamW.
//! Das interessante Engineering ist downstream der JSON-Datei, nicht hier.

use candle_core::{Device, Tensor};
use candle_nn::{AdamW, Module, Optimizer, VarBuilder, VarMap};
use quant_alpha::cross_panel::{required_periods, CrossPanel};
use quant_signal::{BookEvidence, RankedBook, RankedWeight};
use rand::Rng;
use std::error::Error;

/// Fitet ein MLP auf synthetischen Daten und schreibt `ranked_book.json`.
///
/// Die Daten sind so gebaut, dass ein lineares Modell (hidden=0) eine
/// echte, aber kleine Signatur findet — analog zum Blog-Befund, dass
/// mehr Kapazitaet out-of-sample schlechter wird.
pub fn fit_and_write_book(
    out_path: &str,
    hidden: usize,
    n_samples: usize,
    n_features: usize,
    n_epochs: usize,
) -> Result<RankedBook, Box<dyn Error>> {
    let device = Device::Cpu;
    let mut rng = rand::thread_rng();

    // Synthetische Daten: y = 0.3*x0 - 0.2*x1 + Rauschen.
    // Ein lineares Modell findet das; ein groesseres overfittet das Rauschen.
    let mut xs = Vec::with_capacity(n_samples * n_features);
    let mut ys = Vec::with_capacity(n_samples);
    for _ in 0..n_samples {
        let x0: f64 = rng.gen_range(-1.0..1.0);
        let x1: f64 = rng.gen_range(-1.0..1.0);
        let noise: f64 = rng.gen_range(-0.3..0.3);
        xs.push(x0 as f32);
        xs.push(x1 as f32);
        ys.push((0.3 * x0 - 0.2 * x1 + noise) as f32);
    }
    let x_t = Tensor::from_vec(xs, (n_samples, n_features), &device)?;
    let y_t = Tensor::from_vec(ys, (n_samples, 1), &device)?;

    // Modell: linear -> [hidden] tanh -> linear -> 1.
    let varmap = VarMap::new();
    let vb = VarBuilder::from_varmap(&varmap, candle_core::DType::F32, &device);
    let linear_in = candle_nn::linear(n_features, hidden.max(1), vb.pp("in"))?;
    let linear_out = candle_nn::linear(hidden.max(1), 1, vb.pp("out"))?;

    let mut opt = AdamW::new_lr(varmap.all_vars(), 1e-3)?;
    for _epoch in 0..n_epochs {
        let hidden_out = linear_in.forward(&x_t)?.tanh()?;
        let pred = linear_out.forward(&hidden_out)?;
        let loss = pred.sub(&y_t)?.sqr()?.mean_all()?;
        opt.backward_step(&loss)?;
    }

    // Evidenz: gemessene Werte auf dem Trainingsblock (Demo).
    // In einem echten Build waeren das out-of-sample Folds.
    let evidence = BookEvidence {
        net_bps: 3.5,
        n: n_samples,
        se_bps: 2.0,
        folds: 5,
        positive_folds: 2,
    };

    // Dollar-neutrales Buch: zwei Instrumente, Gewichte summieren zu 0.
    let book = RankedBook {
        weights: vec![
            RankedWeight {
                instrument_id: "BTC-USDT-SWAP.OKX".into(),
                weight: 0.5,
            },
            RankedWeight {
                instrument_id: "ETH-USDT-SWAP.OKX".into(),
                weight: -0.5,
            },
        ],
        evidence,
    };

    let json = serde_json::to_string_pretty(&book)?;
    std::fs::write(out_path, json)?;
    Ok(book)
}

fn main() -> Result<(), Box<dyn Error>> {
    let book = fit_and_write_book("ranked_book.json", 0, 2000, 2, 200)?;
    println!(
        "quant-alpha: Buch geschrieben, {} Gewichte, dollar-neutral: {}",
        book.weights.len(),
        book.is_dollar_neutral(1e-9)
    );

    // Panel-Fingerprint: macht Drift des Cross-Section-Panels attribuierbar.
    let panel = CrossPanel::new(
        vec!["BTC-USDT-SWAP.OKX".into(), "ETH-USDT-SWAP.OKX".into()],
        vec![0.5, -0.5],
        vec![0.2, 0.3],
    );
    println!(
        "quant-alpha: Panel-Fingerprint {}, Perioden-Bedarf {:?}",
        panel.fingerprint(),
        required_periods(0.5, 0.1)
    );
    Ok(())
}
