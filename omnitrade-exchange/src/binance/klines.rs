//! Öffentlicher Abruf historischer Kerzen (`GET /api/v3/klines`, ohne Zugangsdaten).

use crate::credentials::Network;
use crate::error::ExchangeError;
use omnitrade_core::Candle;
use serde_json::Value;
use std::time::Duration;

const REQUEST_TIMEOUT: Duration = Duration::from_secs(10);
const TESTNET_REST_URL: &str = "https://testnet.binance.vision";
const MAINNET_REST_URL: &str = "https://api.binance.com";
/// Obergrenze der Börse pro Abruf.
const MAX_LIMIT: usize = 1000;

fn base_url(network: Network) -> &'static str {
    match network {
        Network::Testnet => TESTNET_REST_URL,
        Network::Mainnet => MAINNET_REST_URL,
    }
}

/// Lädt die letzten `limit` Kerzen (älteste zuerst). Die letzte kann noch offen sein.
pub async fn fetch_klines(
    network: Network,
    symbol: &str,
    interval: &str,
    limit: usize,
) -> Result<Vec<Candle>, ExchangeError> {
    let url = format!("{}/api/v3/klines", base_url(network));
    let limit = limit.clamp(1, MAX_LIMIT).to_string();
    let client = reqwest::Client::builder()
        .timeout(REQUEST_TIMEOUT)
        .build()
        .map_err(|e| ExchangeError::ConnectionFailed {
            url: url.clone(),
            reason: e.to_string(),
        })?;
    let response = client
        .get(&url)
        .query(&[
            ("symbol", symbol.to_uppercase().as_str()),
            ("interval", interval),
            ("limit", limit.as_str()),
        ])
        .send()
        .await
        .map_err(|e| ExchangeError::ConnectionFailed {
            url: url.clone(),
            reason: e.to_string(),
        })?;
    let status = response.status();
    let body = response
        .text()
        .await
        .map_err(|e| ExchangeError::ConnectionFailed {
            url: url.clone(),
            reason: e.to_string(),
        })?;
    if !status.is_success() {
        return Err(ExchangeError::ApiError(format!("HTTP {status}: {body}")));
    }
    parse_klines(&body)
}

/// Parst die Klines-Antwort: Array von Arrays `[openTime, open, high, low, close, volume, ...]`.
fn parse_klines(body: &str) -> Result<Vec<Candle>, ExchangeError> {
    let parse_err = |reason: &str| ExchangeError::MessageParseFailed {
        raw: body.chars().take(200).collect(),
        reason: reason.to_string(),
    };
    let rows: Vec<Vec<Value>> =
        serde_json::from_str(body).map_err(|e| parse_err(&e.to_string()))?;
    rows.iter()
        .map(|row| {
            let num = |i: usize| -> Result<f64, ExchangeError> {
                row.get(i)
                    .and_then(Value::as_str)
                    .and_then(|s| s.parse::<f64>().ok())
                    .ok_or_else(|| parse_err("ungültiges Kerzenfeld"))
            };
            let open_time = row
                .first()
                .and_then(Value::as_u64)
                .ok_or_else(|| parse_err("ungültige Öffnungszeit"))?;
            Ok(Candle::new(
                open_time,
                num(1)?,
                num(2)?,
                num(3)?,
                num(4)?,
                num(5)?,
            ))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = r#"[
        [1499040000000,"0.01634790","0.80000000","0.01575800","0.01577100","148976.11427815",1499644799999,"2434.19055334",308,"1756.87402397","28.46694368","0"],
        [1499644800000,"0.01577100","0.01600000","0.01500000","0.01550000","100.0",1500249599999,"1.0",5,"1","1","0"]
    ]"#;

    #[test]
    fn parses_rows_into_candles_in_order() {
        // Act
        let candles = parse_klines(SAMPLE).expect("valid klines");

        // Assert
        assert_eq!(candles.len(), 2);
        assert_eq!(candles[0].timestamp_ms, 1499040000000);
        assert_eq!(candles[0].open, 0.0163479);
        assert_eq!(candles[0].high, 0.8);
        assert_eq!(candles[0].low, 0.015758);
        assert_eq!(candles[0].close, 0.015771);
        assert_eq!(candles[0].volume, 148976.11427815);
        assert_eq!(candles[1].close, 0.0155);
    }

    #[test]
    fn rejects_malformed_rows() {
        assert!(parse_klines("[[1,\"x\",\"1\",\"1\",\"1\",\"1\"]]").is_err());
        assert!(parse_klines("[[\"t\",\"1\",\"1\",\"1\",\"1\",\"1\"]]").is_err());
        assert!(parse_klines("{\"code\":-1121}").is_err());
    }

    #[test]
    fn empty_array_is_empty_vec() {
        assert!(parse_klines("[]").expect("valid").is_empty());
    }

    #[test]
    fn base_url_matches_network() {
        assert_eq!(base_url(Network::Testnet), TESTNET_REST_URL);
        assert_eq!(base_url(Network::Mainnet), MAINNET_REST_URL);
    }
}
