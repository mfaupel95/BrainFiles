# Spec: Web-Dashboard für alle Handelsspuren

**Stand:** 2026-10-10  
**Bereich:** `handel` → `Agenten/Handel/dashboard/`  
**Status:** Umgesetzt (Commits 72df4623, e99a31a5, 4cce0df7); am 12.10.2026 an den gebauten Stand angeglichen.

---

## Ziel

Ein optionales Web-Dashboard (`localhost:7788`) das den bestehenden tkinter-Leitstand
(`leitstand.py`) ergänzt — nicht ersetzt. Alle Handelsspuren (Stand 12.10.2026: 45) sind auf einen Blick
sichtbar; Backtest, Training und Reparatur sind ohne tkinter-Fenster aufrufbar.
Fremdrepo-Signale erscheinen automatisch sobald ihre Schema-JSON-Datei existiert.

---

## Kontext & Abgrenzung

| Vorhanden | Was das Dashboard NICHT macht |
|---|---|
| `spuren_stand.py --json` gibt alle Spuren maschinenlesbar aus | wachen.json schreiben (außer Not-Aus) |
| `leitstand_prozesse.py` hat bewährte Start/Stop-Logik | Live-Handel freigeben |
| `leitstand_backtests.py` hat Backtest-Logik | tkinter-Leitstand ersetzen |
| `leitstand_zustand.json` hält UI-Zustand | neue Handelsstrategie einführen |

---

## Architektur

```
Agenten/Handel/dashboard/
├── schutz.py         # Host-Allowlist, CSRF, Basic Auth (Middleware)
├── __main__.py          # python -m dashboard startet app.py
├── app.py               # FastAPI-App, Routen registrieren, Lifespan
├── quellen/
│   ├── spuren.py        # importiert spuren_stand → Dict[str, SpurStatus]
│   ├── prozesse.py      # laeuft()/starten()/stoppen() je Spur (aus leitstand_prozesse)
│   ├── jobs.py          # Hintergrundjobs (Backtest/Training) per Popen, Doppelstart-Sperre
│   └── reparatur.py     # Checks: PID-Datei, Log-Alter, wachen-Herzschlag
├── routen/
│   ├── monitor.py       # GET / + GET /stream (SSE)
│   ├── prognosen.py     # GET /prognosen
│   ├── steuerung.py     # GET /steuerung + POST /api/spur/{id}/start|stop|notaus
│   ├── backtest.py      # GET /backtest + POST /api/backtest/run + GET /api/backtest/log
│   ├── training.py      # GET /training + POST /api/training/run + GET /api/training/log
│   └── reparatur.py     # GET /reparatur + POST /api/repair/{check}
├── templates/
│   ├── basis.html       # Layout: Nav-Leiste, Catppuccin Mocha, HTMX-CDN
│   ├── monitor.html
│   ├── prognosen.html
│   ├── steuerung.html
│   ├── backtest.html
│   ├── training.html
│   └── reparatur.html
└── static/
    └── style.css        # Catppuccin Mocha-Tokens (konsistent mit fenster_design.py)
```

---

## Datenquellen (`quellen/`)

### `spuren.py`

Importiert `spuren_stand` als Modul (kein Subprocess-Overhead) und gibt
`list[dict]` zurück — dasselbe Schema wie `spuren_stand --json`:

```json
{
  "spur":    "xperp",
  "erlaubt": true,
  "hs":      45,
  "fenster": "zu",
  "frei":    true,
  "order":   ["bot.py", "handeln.py"],
  "auto":    true,
  "buch":    {".hoch": 3, "haupt": 5},
  "alter":   3,
  "art":     "haus",
  "scharf":  true
}
```

Stale-Regel: `alter > hs` → Status `"veraltet"`, im Monitor gelb markiert.
Fehlende JSON-Datei → Status `"nicht konfiguriert"`, grau.
Fremdrepo-Signale: `quellen/spuren.py` sucht zusätzlich nach
`Agenten/Handel/fremdrepos-signal-*.json` und hängt deren Einträge an (Schema:
`signal_schema.py`). Stand 12.10.2026 existiert noch keine solche Datei — nur per
Test abgedeckt.

### `prozesse.py`

Eigene Prozesslogik ohne Import von `leitstand_prozesse.py` (das Modul importiert
tkinter auf oberster Ebene; seine Klassen `_OmnitradetLauf`/`_PythonDauerlauf` sind
privat). Liest `dauerlauf.pid`, fragt `omnitrade_lauf.beurteile()` ab, beendet per
`taskkill`. Exponiert: `laeuft(spur) → bool`, `starten(spur)`, `stoppen(spur)`.

**Not-Aus**: schreibt `"handel_erlaubt": false` in die `wachen.json` der Spur
und ruft `stoppen()`. Nie `mode: live` setzen — Gate weist das zurück.

### `jobs.py` (Backtest und Training)

- Startet Läufe via `subprocess.Popen` als eigenen Prozess, ein Lauf je Name zur Zeit;
  Log per SSE streambar.
- Backtest: `verbesserer/xperp_ruecktest.py` (nur xperp).
- Training: `verbesserer/lauf.py --spur <spur>`; Ergebnis aus
  `verbesserer/lauf_ergebnis.json`.

### `reparatur.py`

Führt folgende Checks durch (kein Fix ohne expliziten API-Aufruf):

| Check | Befund | Fix-Button |
|---|---|---|
| `dauerlauf.pid` vorhanden, Prozess tot | "Zombie-PID" | PID-Datei löschen |
| Log-Alter > `hs * 2` Minuten | "Log veraltet" | Neustart anbieten |
| `wachen.json`-Herzschlag abgelaufen | "Heartbeat abgelaufen" | Manuelle Bestätigung |
| Freigabefenster offen aber Prozess tot | "Fenster offen, kein Prozess" | Fenster schließen |

---

## Seiten (`routen/` + `templates/`)

### Monitor (`/`)

Live-Tabelle aller Spuren. Spalten: Spur, Status (grün/gelb/grau/rot),
Herzschlag, Fenster, Positionen (Buch), Log-Alter. SSE-Endpoint `/stream`
pusht alle 5 s; HTMX tauscht Tabelle aus ohne Seiten-Reload.

### Prognosen (`/prognosen`)

Je aktiver Spur: letztes Signal (Richtung, Konfidenz, Instrument, Zeitstempel).
Liest `prognose.json`, `xperp/prognose.json` o.ä. HTMX-Poll alle 30 s.

### Steuerung (`/steuerung`)

Tabelle aller Spuren mit Start/Stop/Pause-Buttons. Not-Aus-Button oben
(POST `/api/spur/alle/notaus`) stoppt alle erlaubten Spuren.
Freigabefenster-Status (offen/zu) je Spur. Keine Schreibrechte in wachen.json
außer bei Not-Aus.

### Backtest (`/backtest`)

Dropdown: Spur wählen. Parameter-Felder (vorausgefüllt aus `leitstand_zustand.json`).
Run-Button → POST `/api/backtest/run` → SSE-Log-Stream.
Ergebnis: Kennzahlen-Tabelle + P&L-Linienchart (TradingView Lightweight Charts via CDN).

### Training (`/training`)

Dropdown: Verbesserer-Spur wählen. Run-Button → SSE-Log-Stream.
Ergebnis: Kandidat-Tabelle (Fenster, OOS-Score, Holdout), Vergleich mit Basis.

### Reparatur (`/reparatur`)

Befund-Liste (automatisch beim Seitenaufruf geprüft). Je Befund: Beschreibung
und Fix-Button (POST `/api/repair/{check_id}`). Kein automatischer Fix.

---

## Technische Details

**Framework:** FastAPI + Jinja2 + `sse-starlette`. Abhängigkeiten in
`dashboard/requirements.txt`, eigene Umgebung `dashboard/.venv` (Tests und
`omnitrade.cmd` nutzen sie; mit der Scanner-venv scheitern die Tests).

**Charts:** TradingView Lightweight Charts per CDN (`cdn.jsdelivr.net`),
kein npm-Build.

**HTMX:** Per CDN, kein Build.

**Prozesssteuerung:** `subprocess.Popen(..., creationflags=CREATE_NEW_CONSOLE)`
wie `leitstand_prozesse.py` — Prozess läuft weiter wenn Dashboard geschlossen.

**Start:**
```
omnitrade.cmd dashboard          # localhost:7788
omnitrade.cmd dashboard --lan    # 0.0.0.0:7788, DASHBOARD_PASS aus Env
```
`omnitrade.cmd` bekommt einen neuen `:dashboard`-Zweig.

**Optional:** Dashboard startet nur auf expliziten Befehl — kein Autostart,
keine Änderung am bestehenden Lauf-Verhalten.

**Sicherheit:** Localhost-Default ohne Auth. LAN-Modus: HTTP Basic Auth
via `DASHBOARD_PASS`-Env. Kein HTTPS in dieser Spec; kein externer Zugang.
Keine Keys/Credentials in Templates oder Logs.

---

## Tests

`tests/test_dashboard/` — läuft über `handel-tests.ps1`:

- `test_quellen_spuren.py` — `spuren.py` mit Mock-JSON; stale-Erkennung.
- `test_quellen_reparatur.py` — jeden Check mit Mock-Fixtures.
- `test_quellen_prozesse.py` — `laeuft()`/`starten()`/`stoppen()` mit Stub-Prozess.
- `test_api_monitor.py` — FastAPI TestClient, GET `/`, GET `/stream` (3 Events).
- `test_api_steuerung.py` — Not-Aus schreibt `handel_erlaubt: false`.

Kein Browser-Test, kein Playwright.

---

## Integration

1. `omnitrade.cmd`: neuer Block `:dashboard`.
2. `Agenten/Routinen/systempruefung.ps1`: optionaler Check ob Dashboard erreichbar
   (nur wenn PID-Datei existiert).
3. Keine Änderung an `leitstand.py`, `spuren_stand.py` oder anderen bestehenden
   Dateien außer den unter 1. und 2. genannten. Punkt 2 ist offen (nicht umgesetzt).

---

## Abnahmekriterien

- [x] `python -m dashboard` startet ohne Fehler auf Port 7788.
- [x] Monitor zeigt alle Spuren aus `spuren_stand --json`.
- [x] SSE-Stream liefert Update spätestens nach 6 s.
- [x] Not-Aus schreibt `handel_erlaubt: false` in wachen.json der Spur.
- [ ] Backtest für xperp startet, Log streamt, Ergebnis erscheint. (am System ungeprüft)
- [x] Reparatur-Check erkennt Zombie-PID korrekt.
- [x] Alle Tests in `tests/test_dashboard/` grün.
- [x] `omnitrade.cmd dashboard` startet das Dashboard.
- [x] Leitstand.py funktioniert unverändert neben dem Dashboard.
