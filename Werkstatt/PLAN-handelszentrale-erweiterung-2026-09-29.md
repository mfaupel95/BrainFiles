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

## 8. Offene Fragen

1. **Omniportal:** Öffentlich verfügbar? Link zum Repo?
2. **FreqTrade-Strategie-Auswahl:** Sollen Strategien in die Handelszentrale oder nur Status angezeigt?
3. **Order-Ausführung:** Darf Handelszentrale Orders über Omniportal/FreqTrade platzieren oder nur Anzeige?
4. **Daten-Sync:** Bei Abweichung zwischen Systemen (z.B. Position in eigenem Buch vs. FreqTrade-Bot) — wer gewinnt?

---

## Abhängigkeiten

- [ ] FreqTrade lokal installiert + REST-API aktiv
- [ ] Omniportal Code-Zugriff (falls nicht öffentlich)
- [ ] agent-trade-kit MCP funktionsfähig
- [ ] Python 3.10+ mit asyncio (für Parallel-Polling der Systeme)

---

**Co-Authored-By:** Claude Haiku 4.5 <noreply@anthropic.com>  
**Session:** Rekonstruktion aus Brainstorming 28.09.2026  
