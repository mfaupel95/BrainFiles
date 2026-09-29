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

## Workstream 2: Omniportal-Clarification

### Aufgabe 2.1: Lokales Repo recherchieren
- [ ] `O:\Werkstatt\omnitrade` durchsuchen (auf lokaler Maschine)
  - README.md lesen
  - Architektur-Diagramm finden
  - API-Spezifikation suchen
- [ ] GitHub-Link oder interne Repo-URL dokumentieren
- [ ] Version und Lizenz notieren

**Erfolgs-Kriterium:** Omniportal eindeutig identifiziert

**Verantwortlich:** Nutzer (Max)  
**Geschätzte Zeit:** 30 Minuten  
**Status:** ⬜ PENDING INPUT

---

### Aufgabe 2.2: API-Spezifikation erfassen
- [ ] Dokumentation durcharbeiten:
  - Verfügbare Endpoints
  - Authentifizierungsmethode
  - Unterstützte Börsen/Paare
  - Order-Routing-Logik
  - Response-Format (JSON, Protobuf?)
- [ ] Rate-Limits dokumentieren
- [ ] Error-Codes auflisten

**Erfolgs-Kriterium:** API-Spec in Markdown verfügbar

**Verantwortlich:** Claude Code (nach Input vom Nutzer)  
**Geschätzte Zeit:** 2-4 Stunden  
**Status:** ⬜ BLOCKED (warten auf Klarifikation)

---

### Aufgabe 2.3: Omniportal-Interface Design
- [ ] Erste Version: `Agenten/Handel/omniportal_interface.py`
  ```python
  class OmniportalClient:
      def __init__(self, api_url, credentials)
      def list_exchanges() -> List[Exchange]
      def create_order(exchange, symbol, side, size) -> Order
      def get_positions(exchange) -> List[Position]
      def cancel_order(order_id) -> bool
      def get_account_balance() -> Dict
  ```
- [ ] Dummy-Implementation für Testing

**Erfolgs-Kriterium:** Schnittstellendefinition festgelegt

**Verantwortlich:** Claude Code  
**Geschätzte Zeit:** 2 Stunden  
**Status:** ⬜ BLOCKED

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
| | Backtest | ⬜ TODO | 1. fertig |
| | Client | ⬜ TODO | — |
| **2. Omniportal** | Recherche | ⬜ PENDING | Input von Max |
| | API-Spec | ⬜ BLOCKED | 2.1 fertig |
| | Interface | ⬜ BLOCKED | 2.2 fertig |
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
