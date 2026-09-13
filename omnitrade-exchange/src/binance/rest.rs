//! Binance REST API client for Spot trading.
//! Supports Testnet and Mainnet with automatic URL selection.

use super::signing::BinanceSigner;
use crate::credentials::ApiCredentials;
use crate::error::ExchangeError;
use crate::trading::{Account, AccountBalance, ExchangeTrading, OrderRequest};
use omnitrade_core::{Order, OrderStatus, OrderType, Side, TimeInForce};
use reqwest::{Client, Method};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Binance REST API base URLs.
const TESTNET_REST_URL: &str = "https://testnet.binance.vision";
const MAINNET_REST_URL: &str = "https://api.binance.com";

/// Binance REST API client.
pub struct BinanceRestClient {
    http_client: Client,
    base_url: String,
    credentials: ApiCredentials,
}

impl BinanceRestClient {
    /// Create a new Binance REST client.
    pub fn new(credentials: ApiCredentials) -> Result<Self, ExchangeError> {
        credentials.validate().map_err(|e| {
            ExchangeError::InvalidCredentials(format!("Invalid credentials: {}", e))
        })?;

        let base_url = if credentials.is_testnet() {
            TESTNET_REST_URL.to_string()
        } else {
            MAINNET_REST_URL.to_string()
        };

        Ok(Self {
            http_client: Client::new(),
            base_url,
            credentials,
        })
    }

    /// Send a signed request to the Binance API.
    async fn signed_request(
        &self,
        method: Method,
        endpoint: &str,
        params: Option<&HashMap<String, String>>,
    ) -> Result<reqwest::Response, ExchangeError> {
        let timestamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| ExchangeError::InvalidRequest("System time error".to_string()))?
            .as_millis() as i64;

        let mut query = String::new();
        if let Some(p) = params {
            let pairs: Vec<String> = p
                .iter()
                .map(|(k, v)| format!("{}={}", k, urlencoding::encode(v)))
                .collect();
            query = pairs.join("&");
        }

        let signed_query =
            BinanceSigner::sign_request(&query, &self.credentials.secret, timestamp)?;
        let url = format!("{}/api/v3{}", self.base_url, endpoint);

        let request = self
            .http_client
            .request(method.clone(), &url)
            .query(&[("signature_query", signed_query)])
            .header("X-MBX-APIKEY", &self.credentials.key);

        request
            .send()
            .await
            .map_err(|e| ExchangeError::ConnectionFailed {
                url: url.clone(),
                reason: e.to_string(),
            })
    }

    /// Parse Binance order response into our Order domain type.
    fn parse_order_response(&self, resp: &BinanceOrderResponse) -> Order {
        Order {
            id: resp.order_id as u64,
            symbol: resp.symbol.clone(),
            side: if resp.side == "BUY" {
                Side::Buy
            } else {
                Side::Sell
            },
            order_type: match resp.order_type.as_str() {
                "LIMIT" => OrderType::Limit,
                "MARKET" => OrderType::Market,
                _ => OrderType::Market,
            },
            time_in_force: TimeInForce::GTC,
            price: resp.price,
            stop_price: 0.0,
            status: match resp.status.as_str() {
                "NEW" => OrderStatus::New,
                "PARTIALLY_FILLED" => OrderStatus::PartiallyFilled,
                "FILLED" => OrderStatus::Filled,
                "CANCELED" => OrderStatus::Cancelled,
                "REJECTED" => OrderStatus::Rejected,
                _ => OrderStatus::New,
            },
            quantity: resp.orig_qty,
            filled_quantity: resp.executed_qty,
            created_at_ms: resp.time as u64,
            updated_at_ms: resp.update_time as u64,
            trailing_highest_price: None,
        }
    }
}

#[async_trait::async_trait]
impl ExchangeTrading for BinanceRestClient {
    async fn place_order(&self, req: &OrderRequest) -> Result<Order, ExchangeError> {
        if req.quantity <= 0.0 {
            return Err(ExchangeError::InvalidRequest(
                "Quantity must be positive".to_string(),
            ));
        }

        if req.order_type == OrderType::Limit && req.price.is_none() {
            return Err(ExchangeError::InvalidRequest(
                "Limit orders require price".to_string(),
            ));
        }

        let mut params = HashMap::new();
        params.insert("symbol".to_string(), req.symbol.clone());
        params.insert(
            "side".to_string(),
            if req.side == Side::Buy { "BUY" } else { "SELL" }.to_string(),
        );
        params.insert(
            "type".to_string(),
            match req.order_type {
                OrderType::Market => "MARKET",
                OrderType::Limit => "LIMIT",
                _ => "MARKET",
            }
            .to_string(),
        );
        params.insert("quantity".to_string(), req.quantity.to_string());

        if let Some(price) = req.price {
            params.insert("price".to_string(), price.to_string());
        }

        let response = self
            .signed_request(Method::POST, "/order", Some(&params))
            .await?;

        if !response.status().is_success() {
            let body = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(ExchangeError::ApiError(body));
        }

        let body = response.json::<BinanceOrderResponse>().await.map_err(|e| {
            ExchangeError::MessageParseFailed {
                raw: e.to_string(),
                reason: "Failed to parse order response".to_string(),
            }
        })?;

        Ok(self.parse_order_response(&body))
    }

    async fn cancel_order(&self, order_id: &str, symbol: &str) -> Result<(), ExchangeError> {
        let mut params = HashMap::new();
        params.insert("symbol".to_string(), symbol.to_string());
        params.insert("orderId".to_string(), order_id.to_string());

        let response = self
            .signed_request(Method::DELETE, "/order", Some(&params))
            .await?;

        if !response.status().is_success() {
            let body = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(ExchangeError::ApiError(body));
        }

        Ok(())
    }

    async fn get_open_orders(&self) -> Result<Vec<Order>, ExchangeError> {
        let response = self
            .signed_request(Method::GET, "/openOrders", None)
            .await?;

        if !response.status().is_success() {
            let body = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(ExchangeError::ApiError(body));
        }

        let orders: Vec<BinanceOrderResponse> =
            response
                .json()
                .await
                .map_err(|e| ExchangeError::MessageParseFailed {
                    raw: e.to_string(),
                    reason: "Failed to parse orders response".to_string(),
                })?;

        Ok(orders
            .iter()
            .map(|o| self.parse_order_response(o))
            .collect())
    }

    async fn get_balance(&self) -> Result<Account, ExchangeError> {
        let response = self.signed_request(Method::GET, "/account", None).await?;

        if !response.status().is_success() {
            let body = response
                .text()
                .await
                .unwrap_or_else(|_| "Unknown error".to_string());
            return Err(ExchangeError::ApiError(body));
        }

        let account_resp: BinanceAccountResponse =
            response
                .json()
                .await
                .map_err(|e| ExchangeError::MessageParseFailed {
                    raw: e.to_string(),
                    reason: "Failed to parse account response".to_string(),
                })?;

        let mut balances = HashMap::new();
        for balance in account_resp.balances {
            balances.insert(
                balance.asset.clone(),
                AccountBalance {
                    free: balance.free,
                    locked: balance.locked,
                },
            );
        }

        Ok(Account { balances })
    }
}

/// Binance API order response.
#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct BinanceOrderResponse {
    symbol: String,
    order_id: i64,
    client_order_id: String,
    price: f64,
    orig_qty: f64,
    executed_qty: f64,
    cum_quote_asset_transacted_qty: f64,
    status: String,
    time_in_force: String,
    #[serde(rename = "type")]
    order_type: String,
    side: String,
    time: i64,
    update_time: i64,
}

/// Binance API account response.
#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct BinanceAccountResponse {
    balances: Vec<BinanceBalance>,
    #[serde(default)]
    account_commission_btc: String,
    #[serde(default)]
    account_commission_bnb: String,
    #[serde(default)]
    account_commission_usdt: String,
}

/// Binance balance entry.
#[derive(Debug, Serialize, Deserialize)]
struct BinanceBalance {
    asset: String,
    free: f64,
    locked: f64,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_base_url_testnet() {
        let creds = ApiCredentials::new(
            "test_key".to_string(),
            "test_secret".to_string(),
            crate::Network::Testnet,
        );
        let client = BinanceRestClient::new(creds).expect("Failed to create client");
        assert_eq!(client.base_url, TESTNET_REST_URL);
    }

    #[test]
    fn test_base_url_mainnet() {
        let creds = ApiCredentials::new(
            "test_key".to_string(),
            "test_secret".to_string(),
            crate::Network::Mainnet,
        );
        let client = BinanceRestClient::new(creds).expect("Failed to create client");
        assert_eq!(client.base_url, MAINNET_REST_URL);
    }

    #[test]
    fn test_client_creation_empty_key() {
        let creds = ApiCredentials::new(
            "".to_string(),
            "secret".to_string(),
            crate::Network::Testnet,
        );
        let result = BinanceRestClient::new(creds);
        assert!(result.is_err());
    }
}
