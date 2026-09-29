# Phase 1: Handelszentrale-Erweiterung — Vorbereitung & Clarification

**Status:** 🟡 IN ARBEIT  
**Zeitraum:** 29.09. - 03.10.2026  
**Ziel:** FreqTrade Setup, Omniportal klären, Schnittstellen dokumentieren

---

## Workstream 1: FreqTrade Setup & Integration Testing

### Aufgabe 1.1: Installation & Basis-Test
- [ ] FreqTrade Docker Image pullen oder lokal installieren
  ```bash
  pip install freqtrade
  ```
- [ ] Test-Konfiguration erstellen (config_test.json)
  - `enable_api: true`
  - JWT Secret generieren (32+ Zeichen)
  - Testnet Börsen-Credentials (OKX Testnet?)
- [ ] REST API aktivieren und testen
  ```bash
  curl -H "Authorization: Bearer <token>" http://localhost:8080/api/v1/status
  ```
- [ ] WebSocket-Stream testen

**Erfolgs-Kriterium:** REST API antwortet auf alle Standard-Endpoints

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 2 Stunden  
**Status:** ⬜ TODO

---

### Aufgabe 1.2: Erste Strategie backtesten
- [ ] Example Strategy aus FreqTrade Repo laden
  - `SampleStrategy` oder `BBRSIStrategy`
- [ ] Backtest-Daten herunterladen (1-3 Monate historisch)
- [ ] Backtest durchführen
  ```bash
  freqtrade backtesting --strategy SampleStrategy --timeframe 5m
  ```
- [ ] Ergebnisse dokumentieren (Win Rate, Sharpe Ratio, Drawdown)
- [ ] Dry-Run Validierung starten (7 Tage papiergeld)

**Erfolgs-Kriterium:** Backtest-Ergebnis verfügbar, Dry-Run läuft

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 3 Stunden  
**Status:** ⬜ TODO

---

### Aufgabe 1.3: FreqTrade-Interface Python-Client
- [ ] `Agenten/Handel/freqtrade_interface.py` erstellen
  ```python
  class FreqTradeClient:
      def __init__(self, api_url, jwt_token)
      def get_trades(self) -> List[Trade]
      def get_profit() -> float
      def get_performance() -> Dict
      def get_balance() -> Dict
      def get_status() -> str
  ```
- [ ] WebSocket-Client für Echtzeit-Updates
- [ ] Error Handling & Retry Logic

**Erfolgs-Kriterium:** Client erfolgreich mit REST API getestet

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 4 Stunden  
**Status:** ⬜ TODO

---

## Workstream 2: Omnitrade + OpenTerminal Integration

### Aufgabe 2.1: Omnitrade-Rust-Workspace analysieren ✅
- [ ] Workspace-Struktur verstehen:
  - `omnitrade-risk` — Sizing, Drawdown, Kill-Switch
  - `quant-strategy` — Strategy Evaluation
  - `quant-alpha`, `quant-signal`, `quant-planes`
- [ ] Build-Dependencies prüfen (Rust 1.70+, Cargo)
- [ ] FFI (Foreign Function Interface) für Python dokumentieren
- [ ] Test-Build durchführen: `cargo build --release`

**Erfolgs-Kriterium:** Omnitrade-Workspace lädt, Struktur verstanden

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 2 Stunden  
**Status:** ⬜ TODO

---

### Aufgabe 2.2: OpenTerminalUI Recherche & Integration ✅
- [ ] GitHub-Repo klonen: https://github.com/Hitheshkaranth/OpenTerminalUI
  - Oder: existierendes Repo in `Werkstatt/Repos/OpenTerminal` nutzen
- [ ] MCP-Server-Dokumentation lesen
  - 45 verfügbare Tools katalogisieren
  - Read-Only vs Read-Write Tools unterscheiden
- [ ] Lokales Setup: `npm install`, `npm run dev` (oder `python -m uvicorn`)
- [ ] REST-API Endpoints dokumentieren (auf `http://localhost:8000/docs`)

**Erfolgs-Kriterium:** OpenTerminal UI läuft lokal, MCP-Tools verfügbar

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 3 Stunden  
**Status:** ⬜ TODO

---

### Aufgabe 2.3: MCP-Bridge für Handelsystem erstellen
- [ ] `Agenten/Hermes/skills/brainfiles/openterminal-mcp/SKILL.md`
  - MCP-Server registrieren (OpenTerminal MCP)
  - Trading-Tools mappen: `get_watchlist`, `create_alert`, `get_portfolio`
- [ ] Hermes-Bot-Profil für OpenTerminal erstellen
  - Terminal-Zugriff für Hermes über MCP

**Erfolgs-Kriterium:** Hermes kann OpenTerminal-Tools aufrufen

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 2 Stunden  
**Status:** ⬜ TODO

---

### Aufgabe 2.4: Omnitrade-Risk Python-Wrapper (optional)
- [ ] Rust-Bindings für Python erwägen (PyO3)
  - Oder: HTTP-API zu Rust-Dienst
- [ ] Risk-Checks in Python aufrufen:
  ```python
  from omnitrade_risk import RiskLimits
  limits = RiskLimits(max_units=100, drawdown_halbierung=5000)
  limits.check(OrderRequest(units=50, name="BTC"))
  ```

**Erfolgs-Kriterium:** Risk-Checks von Python aus aufrufbar

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 3 Stunden  
**Status:** ⬜ TODO (optional)

---

## Workstream 3: Existierende Systeme dokumentieren

### Aufgabe 3.1: MoonDev TopMovers API-Mapping
- [ ] `moondev_topmovers/handeln.py` analysieren
  - Entry/Exit Logik
  - Signale (welche Indikatoren?)
  - Performance-Tracking
- [ ] API-Schnittstelle definieren
  ```python
  class MoonDevTopMovers:
      def get_signals() -> List[Signal]
      def get_performance() -> Dict
      def is_active() -> bool
  ```

**Erfolgs-Kriterium:** TopMovers-Integration verstanden

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 2 Stunden  
**Status:** ⬜ TODO

---

### Aufgabe 3.2: OmniQuant GUI-API dokumentieren
- [ ] `omniquant/gui.py` analysieren
  - Welche Daten zeigt es an?
  - Welche APIs für externe Integration?
  - Performance-Metriken Quelle?
- [ ] Schnittstelle für Zentrale definieren

**Erfolgs-Kriterium:** OmniQuant Integration dokumentiert

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 2 Stunden  
**Status:** ⬜ TODO

---

### Aufgabe 3.3: agent-trade-kit MCP Funktionen
- [ ] OKX Agent Trade Kit MCP-Werkzeuge auflisten
  - Order-Platzierung
  - Balance-Abfrage
  - Trade-History
- [ ] Integration in Zentrale planen

**Erfolgs-Kriterium:** MCP-Funktionen katalogisiert

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 1 Stunde  
**Status:** ⬜ TODO

---

## Status-Übersicht

| Workstream | Aufgabe | Status | Blocker |
|-----------|---------|--------|---------|
| **1. FreqTrade** | Setup | ⬜ TODO | — |
| | Backtest | ⬜ TODO | 1.1 fertig |
| | Client | ⬜ TODO | — |
| **2. Omnitrade + OpenTerminal** | Omnitrade analysieren | ⬜ TODO | — |
| | OpenTerminal Setup | ⬜ TODO | — |
| | MCP-Bridge | ⬜ TODO | 2.2 fertig |
| | Risk-Wrapper | ⬜ TODO (optional) | — |
| **3. Systeme** | MoonDev | ⬜ TODO | — |
| | OmniQuant | ⬜ TODO | — |
| | agent-trade-kit | ⬜ TODO | — |

---

## Kritischer Pfad

```
1. Omniportal klären (Input Max) → 2.2/2.3 unblockieren
2. FreqTrade Setup parallel → 1.2/1.3 ermöglichen
3. Existierende Systeme dokumentieren → Gesamtbild
4. Interfaces in Code gießen → PoC vorbereiten
```

---

## Nächste Milestones

- **29.09.** (Heute): Phase 1 kickoff
- **01.10.**: FreqTrade & Systeme-Doku erledigt
- **02.10.**: Omniportal geklärt, Interfaces designed
- **03.10.**: Phase 1 abgeschlossen, Phase 2 briefing

---

**Co-Authored-By:** Claude Haiku 4.5 <noreply@anthropic.com>  
**Phase 1 Plan:** https://github.com/mfaupel95/BrainFiles/pull/5
