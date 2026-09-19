//! quant-strategy — EXECUTION.
//!
//! Liest das RankedBook der Research-Ebene, bildet den t-Wert SELBST und
//! wendet seine eigene Evidenz-Huerde an. Haengt von KEINER candle-Crate ab —
//! das Modell ist nicht in diesem Dependency-Graph, also nicht in der Binary.

pub mod evidence;
