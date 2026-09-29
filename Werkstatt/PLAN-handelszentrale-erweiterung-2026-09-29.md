# Handelszentrale: Meta-Frontend-Architektur (Superpowers)

**Datum:** 29.09.2026  
**Status:** ⬜ In Planung  
**Ziel:** Handelszentrale als Orchestrator für mehrere Handels- und Strategie-Systeme

---

## 1. Architektur: Frontend für mehrere Systeme

Die **Handelszentrale** wird vom reinen Status-Dashboard zu einem **Meta-Frontend** erweitert:

### Aktuell eingebundene Systeme
| System | Typ | Komponente | Status |
|--------|-----|-----------|--------|
| **Eigene Spuren** | Backend | `Agenten/Handel/` (Papier/Live) | ✅ Aktiv |
| **OKX Agent Trade** | Backend/MCP | `agent-trade-kit` | ✅ Vorhanden |
| **MoonDev GUI** | Frontend | `Routinen/moondev-gui.ps1` | ✅ Lauffähig |
| **OmniQuant** | GUI-Modul | `omniquant/gui.py` | ✅ Vorhanden |
| **FreqTrade** | Daten-Provider | *einzubinden* | ⬜ NEU |

---

## 2. FreqTrade-Integration

### Ziel
FreqTrade als **Daten-Provider** für Signale, Strategien und Bot-Status einbinden.

### Schnittstellen
- **FreqTrade REST-API** → Strategie-Signale auslesen
- **FreqTrade Strategy-Loader** → Lokale Strategien registrieren
- **Bot-Status-Stream** → Live-Positionen, Trades, Performance

### Komponenten
- `Agenten/Handel/freqtrade_bridge.py` (neue Komponente)
- `Agenten/Handel/tests/test_freqtrade_bridge.py`
- `Werkstatt/Repos/<freqtrade-fork>/` (Shallow-Klon, `upstream` = Original)

---

## 3. Omniportal-Integration

### Ziel
Omniportal als **Börsen-Abstraktionsschicht** einbinden (Multi-Exchange-Trading).

### Verknüpfung
- Mit existierenden Spuren (OKX, Kraken, ?)
- Mit FreqTrade-Strategien
- Unified Order/Position API

### Status
*Zu recherchieren:* Ist Omniportal öffentlich? Wo liegt der Code?

---

## 4. Meta-Frontend-Design

### Komponenten der Handelszentrale

```
┌─ Handelszentrale (Orchestrator)
│
├─ Reiter: Spuren (eigene)
├─ Reiter: FreqTrade (Bot-Status, Strategien)
├─ Reiter: MoonDev (TopMovers, Liquidationen, Strategien)
├─ Reiter: OmniQuant (zusätzliche Analyse)
├─ Reiter: Omniportal (Multi-Exchange-Orders, Positions)
│
├─ Konsole (Log-Merge über alle Systeme)
├─ Charts (Kerzenchart, Equity-Kurve, Cross-System)
└─ Alerts (zentral: eigene Regeln + FreqTrade-Alerts + Omniportal-Warnungen)
```

### Implementierung
- **Datenschicht:** Jedes Subsystem bekommt eine `<name>_interface.py`
  - `freqtrade_interface.py` → REST-API zum FreqTrade-Server
  - `omniportal_interface.py` → REST-API zu Omniportal
  - `moondev_interface.py` → Bestehende MoonDev-Integration

- **View-Schicht:** Reiter-basierte GUI
  - Bereits vorhanden: Tkinter/PyQt-Struktur in `handelszentrale.py`
  - Neue Reiter: `TabFreqTrade`, `TabOmniportal`

---

## 5. Repo-Integration

### Was gehört wo?

| Repo | Aufgabe |
|------|---------|
| **handel-stack** | Hauptstack: Spuren, Auswertung, Handelszentrale |
| **agent-trade-kit** | OKX/Kraken/etc. Trade-APIs |
| **Werkstatt/Repos/freqtrade** | FreqTrade Shallow-Klon (origin=fork, upstream=official) |
| **Werkstatt/Repos/omniportal** | Omniportal Shallow-Klon (falls öffentlich) |
| **BrainFiles** | Maschinenraum: MCP-Server, Hermes-Skills, Routinen |

### Arbeitsablauf
```
1. Werkstatt/Repos/<repo>/ clonen (shallow, origin = mfaupel95/<repo>)
2. Agenten/Handel/interfaces/ → Integration in Handelszentrale
3. Tests: Agenten/Handel/tests/test_<system>_interface.py
4. Go-Live: neue SKILL.md für Hermes (Orchestration)
```

---

## 6. Strategie-Verbesserungen

### Aktuelle Strategien (in MoonDev GUI verfügbar)
- TopMovers (Momentum-Strategie)
- Liquidationen (Liquidations-Hunter)
- Weitere (zu recherchieren)

### Integration in Handelszentrale
- Strategie-Auswahl → FreqTrade Backtester → Ergebnis in Meta-Frontend anzeigen
- Performance-Vergleich (eigene Spuren vs. FreqTrade vs. MoonDev-Strategien)
- Hybride Strategien (z.B.: FreqTrade-Signal + eigene Risiko-Rules)

---

## 7. Abschlussprüfung

**Phase 1: Vorbereitung** ✅
- [ ] FreqTrade REST-API-Dokumentation durcharbeiten
- [ ] Omniportal recherchieren (öffentlich? Code-Zugriff?)
- [ ] Existierende `moondev_topmovers/`, `moondev_liquidation/` analysieren
- [ ] `agent-trade-kit` MCP-Interface verstehen

**Phase 2: Implementierung** ⬜
- [ ] `freqtrade_interface.py` + Tests (FreqTrade-Server läuft lokal)
- [ ] `omniportal_interface.py` + Tests (falls vorhanden)
- [ ] `TabFreqTrade`, `TabOmniportal` in Handelszentrale
- [ ] Konsole + Charts Multi-System-Logging

**Phase 3: Integration & Go-Live** ⬜
- [ ] Alle Subsystem-Interfaces in Master-Branch
- [ ] Neue SKILL für Hermes (Orchestration starten)
- [ ] Handelszentrale startet mit allen Reitern (fallback auf ⚠️ wenn Subsystem offline)
- [ ] Performance-Vergleich erste Woche dokumentieren

---

## 8. RECHERCHE-ERGEBNISSE

### FreqTrade ✅ EINFACHE INTEGRATION

**GitHub:** https://github.com/freqtrade/freqtrade (54.9k ⭐)  
**Lizenz:** GPL-3.0 (komplett kostenlos, Open Source)  
**Sprache:** Python 3.11+  
**Status:** Aktiv entwickelt (33.003 Commits, 22 offene Issues)

**REST API Endpoints verfügbar:**
```
/trades          → Alle Trades auslesen
/profit          → Profit/Loss Berechnung
/daily           → Tägliche Performance
/performance     → Bot-Performance-Statistik
/balance         → Wallet-Status
/whitelist       → Aktive Trading-Paare
/forceenter      → Manuellen Trade auslösen
/stop            → Bot pausieren/stoppen
/start           → Bot starten
WebSocket: /message/ws  → Echtzeit-Updates
```

**Unterstützte Börsen:** Binance, Kraken, OKX, Bybit, Gate, Bitget, HTX (27+ insgesamt)

**Strategie-Framework:**
- Python-basierte Strategy-Klassen
- Backtesting mit historischen OHLCV-Daten
- Hyperopt (Bayesian-Optimierung)
- FreqAI (Machine Learning: LightGBM, XGBoost)
- Dry-Run Validierung (7+ Tage empfohlen vor Live)

**Performance-Metriken:** CAGR, Sharpe Ratio, Sortino Ratio, Win Rate, Max Drawdown, Profit Factor

**Integrierbarkeits-Level:** ⭐⭐⭐ **EINFACH**
- REST API vollständig dokumentiert
- JSON Response Format
- Keine Auth-Komplexität (lokal JWT, Remote SSH)
- Python SDK verfügbar

### Omniportal ⚠️ RECHERCHE ERGEBNIS

**Status:** NICHT eindeutig im öffentlichen Internet gefunden!

**Möglichkeiten:**
1. **Proprietäres/internes System** — Wahrscheinlich auf der lokalen Maschine (`O:\Werkstatt\omnitrade`)
2. **Verwechslung möglich** mit:
   - OpenTradingPlatform (GitHub)
   - OmniTrader (Stock/Futures)
   - CCXT Multi-Exchange
   - Omniex (Institutionell, aktuell mit Gemini merged)

**Nächster Schritt:** Das lokale `Werkstatt/omnitrade`-Repo prüfen oder Spezifikation klären.

---

## 8. Offene Fragen

1. **Omniportal:** Ist das ein proprietäres/internes System? Repo-URL oder Spezifikation?
2. **FreqTrade-Dry-Run:** Sollen Strategien über Zentrale backtestet oder nur Status angezeigt?
3. **Order-Execution-Delegation:** Darf Zentrale Orders über FreqTrade/Omniportal platzieren oder nur Anzeige+Bestätigung?
4. **Konflikt-Handling:** Bei Abweichung (Position in eigenem Buch vs. FreqTrade) — Priorität?
5. **Strategie-Sharing:** Können Strategien zwischen FreqTrade und eigenen Spuren portiert werden?

---

## 9. Implementierungs-Roadmap

### Phase 1: Vorbereitung & Clarification (Diese Woche)

**FreqTrade Setup:**
- [ ] FreqTrade lokal/Docker installieren: `pip install freqtrade`
- [ ] Erste Strategie backtesten (Beispiel aus Repo)
- [ ] REST API aktivieren (`enable_api: true` in config)
- [ ] JWT Secret konfigurieren
- [ ] Test-Börsen-Verbindung (Testnet-Kreds, z.B. OKX Testnet)

**Omniportal Klärung:**
- [ ] `O:\Werkstatt\omnitrade` auf lokaler Maschine durchsuchen
- [ ] README oder Dokumentation des Omnitrade-Repos lesen
- [ ] API-Spezifikation oder Architektur-Diagramm finden
- [ ] Falls nicht vorhanden: Alternative (CCXT Multi-Exchange) erwägen

**Existierende Systeme auflisten:**
- [ ] MoonDev TopMovers API-Schnittstelle dokumentieren
- [ ] OmniQuant GUI API-Schnittstelle dokumentieren
- [ ] agent-trade-kit MCP-Funktionen auflisten

### Phase 2: Proof of Concept (Nächste 1-2 Wochen)

**FreqTrade-Bridge bauen:**
- [ ] `freqtrade_interface.py` erstellen
  - REST API-Client (JWT)
  - Trade-History auslesen
  - Performance-Metriken sammeln
- [ ] WebSocket-Stream implementieren (Echtzeit-Trades)
- [ ] Unit Tests: `test_freqtrade_interface.py`

**Omniportal-Bridge bauen (nach Klärung):**
- [ ] `omniportal_interface.py` erstellen
- [ ] Multi-Exchange Order-Routing
- [ ] Execution-Logging

**GUI-Erweiterung:**
- [ ] `TabFreqTrade` → Bot-Status, Trades, Performance-Chart
- [ ] `TabOmniportal` → Multi-Exchange Orders, Positions
- [ ] Chart-Merge (Equity-Kurven von all Systemen)
- [ ] Zentrale Konsole (Log-Merge)

### Phase 3: Integration & Go-Live (Wochen 3-4)

**Risk Management:**
- [ ] Kill-Switch zwischen Systemen
- [ ] Drawdown-Limits implementieren
- [ ] Dry-Run Validierung (mindestens 7 Tage)

**Monitoring & Alerts:**
- [ ] Prometheus Metrics exportieren
- [ ] Grafana Dashboards bauen
- [ ] Slack/Email Alerts bei Problemen

**Skill für Hermes erstellen:**
- [ ] `Agenten/Hermes/skills/brainfiles/handelszentrale-orchestration/SKILL.md`
- [ ] Start-Workflow dokumentieren
- [ ] Multi-System Orchestration beschreiben

---

## 10. Abhängigkeiten

**Erforderlich:**
- [ ] FreqTrade lokal installiert + REST-API aktiv
- [ ] Omniportal-Spezifikation (Repo oder interne Docs)
- [ ] agent-trade-kit MCP funktionsfähig
- [ ] Python 3.11+ mit asyncio
- [ ] HTTP-Client: `httpx` oder `aiohttp` (async requests)

**Optional (für volle Feature-Set):**
- [ ] PostgreSQL (für Trade-History-Persistierung)
- [ ] Redis (für Message-Queuing)
- [ ] Docker Compose (für FreqTrade-Deployment)
- [ ] Prometheus + Grafana (für Monitoring)

---

**Co-Authored-By:** Claude Haiku 4.5 <noreply@anthropic.com>  
**Session:** Rekonstruktion aus Brainstorming 28.09.2026  
