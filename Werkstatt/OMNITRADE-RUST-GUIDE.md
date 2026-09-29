# Omnitrade Rust Workspace — Setup & Integration

**Datum:** 29.09.2026  
**Location:** `Agenten/Handel/nautilus-rust/`  
**Workspace Crates:** 5 Module für Quant-Trading

---

## Workspace-Struktur

```
nautilus-rust/
├── Cargo.toml                    # Workspace-Definition
├── Cargo.lock                    # Dependency-Locks
│
├── omnitrade-risk/               # 🎯 Risk Management (Kernmodul)
│   ├── src/lib.rs                # Sizing, Drawdown, Kill-Switch
│   └── Cargo.toml
│
├── quant-strategy/               # Strategy Evaluation & Signals
│   ├── src/lib.rs
│   └── Cargo.toml
│
├── quant-alpha/                  # Alpha Generation
│   ├── src/lib.rs
│   └── Cargo.toml
│
├── quant-signal/                 # Signal Processing
│   ├── src/lib.rs
│   └── Cargo.toml
│
└── quant-planes/                 # Quant-Ebenen/Layers
    ├── src/lib.rs
    └── Cargo.toml
```

---

## Installation & Build

### Voraussetzungen
```
- Rust 1.70+ (https://rustup.rs)
- Cargo (kommt mit Rust)
- C/C++ Compiler (optional, für native Dependencies)
```

### Installation Rust
```bash
# Linux/macOS
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Oder: Update bestehende Installation
rustup update
```

### Build durchführen
```bash
cd Agenten/Handel/nautilus-rust

# Development Build (schneller, weniger optimiert)
cargo build

# Release Build (optimiert, für Production)
cargo build --release

# Spezifisches Crate bauen
cargo build -p omnitrade-risk
cargo build -p quant-strategy

# Tests durchführen
cargo test
```

### Build-Output
```
nautilus-rust/
├── target/
│   ├── debug/
│   │   ├── libomnitrade_risk.rlib
│   │   ├── libquant_strategy.rlib
│   │   └── ...
│   └── release/
│       ├── libomnitrade_risk.rlib  # Optimiert
│       └── ...
```

---

## Module Deep Dive

### 1. omnitrade-risk (Kernmodul)

**Funktion:** Sizing, Drawdown-Management, Kill-Switches

**Haupttypen:**
```rust
pub struct OrderRequest {
    pub units: u64,              // Bestellmenge
    pub name: String,            // Asset-Name
}

pub struct RiskLimits {
    pub max_units_per_name: u64, // Max Units pro Asset
    pub drawdown_halbierung_usd: f64, // Drawdown-Schwelle
}

pub struct RiskViolation(pub String); // Error-Typ
```

**Core-Funktionen:**
```rust
// Order gegen Limits prüfen
limits.check(&order_request) -> Result<(), RiskViolation>

// Größenfaktor bei Drawdown
groessenfaktor(drawdown_schwelle, current_drawdown) -> f64
// Faktor < 1.0 → reduzierte Größe bei Drawdown
// Faktor = 0.0 → Stop bei max Drawdown
```

**Integration:**
```python
# Python-Wrapper (via PyO3 oder HTTP-API)
from omnitrade_risk import RiskLimits, OrderRequest

limits = RiskLimits(max_units_per_name=100, drawdown_halbierung_usd=5000)
order = OrderRequest(units=50, name="BTC/USDT")

try:
    limits.check(order)  # OK, 50 < 100
except RiskViolation as e:
    print(f"Risk check failed: {e}")
    # Order wird nicht platziert
```

---

### 2. quant-strategy

**Funktion:** Strategy Evaluation und Signal-Generierung

**Typische Logik:**
- Strategie-Parameter auswerten
- Evidenz-basierte Urteile fällen ("Verdict")
- Signale generieren (BUY/SELL/HOLD)

**Imports aus omnitrade-risk:**
```rust
use omnitrade_risk::{OrderRequest, RiskLimits};
use quant_strategy::evidence::Verdict;
```

---

### 3. quant-alpha, quant-signal, quant-planes

**Spekulativ basierend auf Namen:**
- **quant-alpha:** Alpha-Generierung (Überrendite)
- **quant-signal:** Signal-Processing (technische Indikatoren?)
- **quant-planes:** Ebenen der Quant-Logik (Pre-Trade, Trade, Post-Trade?)

**Zu erforschen:** Siehe Kommentare in den `lib.rs` Dateien

---

## Python-Binding via PyO3 (Optional)

### Rust Seite (omnitrade-risk/src/lib.rs)

```rust
use pyo3::prelude::*;

#[pyclass]
pub struct RiskLimitsWrapper {
    inner: RiskLimits,
}

#[pymethods]
impl RiskLimitsWrapper {
    #[new]
    fn new(max_units: u64, drawdown_schwelle: f64) -> Self {
        RiskLimitsWrapper {
            inner: RiskLimits {
                max_units_per_name: max_units,
                drawdown_halbierung_usd: drawdown_schwelle,
            }
        }
    }
    
    fn check(&self, units: u64, name: &str) -> PyResult<()> {
        let order = OrderRequest {
            units,
            name: name.to_string(),
        };
        self.inner.check(&order)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.0))
    }
}

#[pymodule]
fn omnitrade_risk(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RiskLimitsWrapper>()?;
    Ok(())
}
```

### Python Seite

```python
# setup.py
from maturin import build

# Build-Befehl
python setup.py build

# Dann:
from omnitrade_risk import RiskLimitsWrapper

limits = RiskLimitsWrapper(max_units=100, drawdown_schwelle=5000)
try:
    limits.check(50, "BTC/USDT")
except ValueError as e:
    print(f"Risk violation: {e}")
```

---

## Alternative: HTTP-API

Wenn PyO3 zu komplex: Rust-Daemon + REST-API

```rust
// Server
use actix_web::{web, App, HttpServer, HttpResponse};

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .route("/check-risk", web::post().to(check_risk_handler))
            .route("/get-limits", web::get().to(get_limits_handler))
    })
    .bind("127.0.0.1:9001")?
    .run()
    .await
}

async fn check_risk_handler(body: web::Json<OrderRequest>) -> HttpResponse {
    let limits = RiskLimits { /* ... */ };
    match limits.check(&body) {
        Ok(()) => HttpResponse::Ok().finish(),
        Err(e) => HttpResponse::BadRequest().json(serde_json::json!({"error": e.0}))
    }
}
```

```python
# Python Client
import httpx

async def check_risk(units: int, name: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:9001/check-risk",
            json={"units": units, "name": name}
        )
        return response.status_code == 200
```

---

## Testing

### Unit Tests (Rust)

```bash
cargo test                          # Alle Tests
cargo test -p omnitrade-risk        # Nur omnitrade-risk
cargo test --test integration       # Integration Tests
```

### Test-Beispiel (omnitrade-risk/tests/)

```rust
#[test]
fn test_risk_check_pass() {
    let limits = RiskLimits {
        max_units_per_name: 100,
        drawdown_halbierung_usd: 5000.0,
    };
    let order = OrderRequest { units: 50, name: "BTC".to_string() };
    assert!(limits.check(&order).is_ok());
}

#[test]
fn test_risk_check_fail() {
    let limits = RiskLimits {
        max_units_per_name: 100,
        drawdown_halbierung_usd: 5000.0,
    };
    let order = OrderRequest { units: 150, name: "BTC".to_string() };
    assert!(limits.check(&order).is_err());
}

#[test]
fn test_groessenfaktor() {
    let faktor = RiskLimits::groessenfaktor(5000.0, 2500.0);
    assert_eq!(faktor, 0.5);  // 50% Reduktion bei halbenem Drawdown
}
```

---

## Integration in Handelszentrale

### Workflow

```
1. FreqTrade generiert Buy-Signal
   ↓
2. Omnitrade-Risk prüft Order-Größe
   ├─ OK: Order wird platziert
   └─ FAIL: Order reduziert oder gecancelt
   ↓
3. OpenTerminal UI zeigt Position
   ↓
4. Quant-Strategy evaluated Performance
   ↓
5. Risk-Management passt Drawdown an
```

### Python-Integration (Zentrale)

```python
# handelszentrale_integration.py
from freqtrade_interface import FreqTradeClient
from omnitrade_interface import OmnitradeRiskClient  # HTTP oder PyO3
from openterminal_interface import OpenTerminalClient

class TradeOrchestrator:
    def __init__(self):
        self.freqtrade = FreqTradeClient(jwt_token="...")
        self.omnitrade = OmnitradeRiskClient(api_url="http://localhost:9001")
        self.terminal = OpenTerminalClient(api_url="http://localhost:8000")
    
    async def execute_trade(self, symbol: str, size: int):
        # 1. Risk-Check
        risk_ok = await self.omnitrade.check_risk(size, symbol)
        if not risk_ok:
            print(f"Risk limit exceeded for {symbol}")
            return
        
        # 2. Trade platzieren (FreqTrade oder direkt)
        order = await self.freqtrade.place_order(symbol, size)
        
        # 3. UI aktualisieren
        await self.terminal.add_to_watchlist(symbol)
        
        # 4. Performance überwachen
        performance = await self.terminal.get_performance()
        print(f"Current P&L: {performance}")
```

---

## Deployment

### Debug Build (für Entwicklung)
```bash
cargo build
./target/debug/omnitrade-risk
```

### Release Build (für Production)
```bash
cargo build --release
./target/release/omnitrade-risk

# Größe reduzieren
cargo build --release -C opt-level=z -C lto
```

### Docker (optional)

```dockerfile
FROM rust:latest
WORKDIR /build
COPY . .
RUN cargo build --release
FROM debian:bookworm-slim
COPY --from=0 /build/target/release/omnitrade-risk /app/
ENTRYPOINT ["/app/omnitrade-risk"]
```

---

## Troubleshooting

### Problem: "Failed to compile: linker not found"
**Lösung:** C-Compiler installieren:
```bash
# Ubuntu
sudo apt-get install build-essential

# macOS
xcode-select --install
```

### Problem: "PyO3 build fails"
**Lösung:** Python-Development Headers installieren:
```bash
# Ubuntu
sudo apt-get install python3-dev

# macOS
brew install python3
```

### Problem: "Dependency version conflict"
**Lösung:**
```bash
cargo update        # Aktualisiere Dependencies
cargo clean         # Lösche Build-Cache
cargo build         # Neu bauen
```

---

## Next Steps

1. **Build testen:** `cargo build`
2. **Tests ausführen:** `cargo test`
3. **Module erforschen:** Code-Review der `lib.rs` Dateien
4. **Python-Binding:** Evtl. PyO3 oder HTTP-API einrichten
5. **Integration:** In Zentrale einbinden

---

**Co-Authored-By:** Claude Haiku 4.5 <noreply@anthropic.com>
