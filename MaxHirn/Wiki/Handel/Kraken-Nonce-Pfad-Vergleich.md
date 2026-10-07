# Kraken Nonce-Pfad: Sonde vs. hausinterne Implementierung

**Datum:** 2026-10-06
**Anlass:** Kanban-Karte t_70eb4163
**Quellen:** `Agenten/Handel/kraken/kraken.py`, `Agenten/Handel/kraken/nonce_pool.py`, `Agenten/Handel/kraken_abweisungs_sonde.py`

---

## 1. Nonce-Header-Pfad

### hausintern (`kraken.py`)

```
kraken.py
  |-- _monotone_nonce()          # Import aus nonce_pool (Zeile 41)
  |-- _vorwaerts(versuch)        # Import aus nonce_pool (Zeile 42)
  |
  |-- _roh_privat(methode, **parameter)
        |
        |-- Versuch 0: nonce = _monotone_nonce()
        |-- Versuch 1: nonce = _vorwaerts(1)
        |-- Versuch 2: nonce = _vorwaerts(2)
        |
        |-- Signatur: HMAC-SHA512(base64decode(secret), SHA256(nonce + formular + pfad))
        |-- Header: API-Key, API-Sign, Content-Type
        |
        |-- Bei "EAPI:Invalid nonce": naechster Versuch (max 3)
        |-- Bei HTTP 401/403: KrakenFehler (kein Retry)
```

**Eigenschaften:**
- 3-Versuchs-Loop mit `_vorwaerts()` als Ausweg
- `_vorwaerts()` schreibt den vorgeschobenen Wert in die gemeinsame Pool-Datei (Monotonie bleibt erhalten)
- Signatur-Pfad: `pfad.encode() + hashlib.sha256((nonce + formular).encode()).digest()`

### Sonde (`kraken_abweisungs_sonde.py`)

```
kraken_abweisungs_sonde.py
  |-- _lade(NONCE_POOL, "sonde_kraken_nonce_pool")   # per Pfad geladen
  |
  |-- privat_spot(kraken)
  |     |-- kraken.guthaben("ZEUR")                  # -> _roh_privat -> _monotone_nonce()
  |
  |-- _roh_spot(kraken, pool)                        # NUR IM FEHLERFALL (Zeuge)
        |-- Versuch 0: pool.monotone_nonce()
        |-- Versuch 1: pool.vorwaerts(1)
        |-- Versuch 2: pool.vorwaerts(2)
        |-- Signatur: identisch zu kraken.py
        |-- Header: API-Key, API-Sign, Content-Type
```

**Eigenschaften (seit 07.10.2026, Kanban t_2eb4971f):**
- 3-Versuchs-Loop wie `kraken.py`: bei "EAPI:Invalid nonce" schiebt der naechste
  Versuch den geteilten Zaehler mit `vorwaerts()` vor (identisch zu `_roh_privat`)
- Ein echter Befund (Permission denied, Lockout, HTTP-Fehler) wird NIE wiederholt
- Signatur-Pfad: identisch zu `kraken.py` (`pfad.encode() + hashlib.sha256((nonce + formular).encode()).digest()`)

### Kernunterschied

| Aspekt | `kraken.py` | Sonde |
|---|---|---|
| Nonce-Quelle | `_monotone_nonce()` + `_vorwaerts()` | `monotone_nonce()` + `vorwaerts()` (seit 07.10.2026) |
| Wiederholung bei Invalid nonce | 3 Versuche, ab 2. mit `_vorwaerts()` | 3 Versuche, ab 2. mit `_vorwaerts()` (identisch) |
| Zweck | Handelsausfuehrung (Order, Stops) | reine Beobachtung + Fehlerprotokoll |
| `_vorwaerts()`-Ausweg | ja | ja (seit 07.10.2026, Kanban t_2eb4971f) |

**Konsequenz:** Die Sonde kann einen `EAPI:Invalid nonce`-Befund wie der
Haus-Pfad selbst aufloesen: sie schiebt den geteilten Zaehler mit
`vorwaerts()` vor und wiederholt den Zeuge-Aufruf (bis zu drei Versuche).
Damit protokolliert sie die ECHTE Abweisung statt eines Nonce-Artefakts,
wenn ein fremdes Werkzeug (die offizielle kraken-cli) den Schluessel-Nonce
hochgesetzt hat. Sie bleibt ein Beobachter - sie ordert nichts, sie
verschiebt nur den gemeinsamen nonce-Zaehler, genau wie jeder Hausaufruf.

---

## 2. Zeitstempel-Format

### Nonce-Pool (`nonce_pool.py`)

```python
nonce = max(int(time.time() * 1_000_000_000), letzter + 1)
```

- **Format:** Integer, Nanosekunden seit Unix-Epoche
- **Beispiel:** `1791306578720000000`
- **Einheit:** Nanosekunden (seit 22.09.2026; vorher Mikrosekunden)
- **Grund:** Die offizielle kraken-cli signiert in Nanosekunden. Kraken merkt sich je Schluessel den hoechsten gesehenen Wert — jeder Mikrosekunden-nonc waere rund tausendfach kleiner und wuerde als "EAPI:Invalid nonce" abgelehnt.

### Sonde-Protokoll (`kraken_abweisungs_sonde.py`)

```python
def _jetzt():
    return datetime.now().astimezone().replace(microsecond=0).isoformat()
```

- **Format:** ISO-8601 String, ohne Mikrosekunden
- **Beispiel:** `2026-10-06T19:05:00+02:00`
- **Verwendung:** Protokollzeilen (`cache/kraken-abweisungen.jsonl`), Stand-Datei (`cache/kraken-abweisungs-sonde.json`)

### Vergleich

| Stelle | Format | Beispiel |
|---|---|---|
| `nonce_pool.monotone_nonce()` | Nanosekunden-Integer | `1791306578720000000` |
| `nonce_pool.vorwaerts()` | Nanosekunden-Integer | `1791306578720000000` |
| Sonde `_jetzt()` | ISO-8601 ohne Mikrosekunden | `2026-10-06T19:05:00+02:00` |
| Sonde Protokoll | ISO-8601 ohne Mikrosekunden | `2026-10-06T19:05:00+02:00` |

**Kernunterschied:** Der Nonce-Pool rechnet in Nanosekunden-Integer (Wallclock). Die Sonde schreibt ihre Protokoll-Zeitstempel in ISO-8601 ohne Mikrosekunden. Beide Systeme koexistieren, aber die Sonde koennte bei einem `EAPI:Invalid nonce`-Befund nicht selbst vorwaerts schieben, um den Zeuge-Aufruf zu wiederholen.

---

## 3. Signatur-Pfad (identisch)

Beide Stellen verwenden denselben Signatur-Pfad:

```python
roh = (nonce + formular).encode()
nachricht = pfad.encode() + hashlib.sha256(roh).digest()
sig = base64.b64encode(
    hmac.new(base64.b64decode(geheim), nachricht, hashlib.sha512).digest()
).decode()
```

- `pfad` = `"/0/private/Balance"` (Spot) bzw. `"/accounts"` (Futures)
- `formular` = `urllib.parse.urlencode({"nonce": nonce, ...})`
- `geheim` = `base64.b64decode(KRAKEN_SPOT_API_SECRET)`

**Kein Unterschied** — die Signatur-Logik ist konsistent.

---

## 4. Zusammenfassung

1. **Nonce-Pfad:** `kraken.py` nutzt den Pool mit 3-Versuchs-Logik inkl. `_vorwaerts()`-Ausweg. Die Sonde nutzt seit 07.10.2026 (Kanban t_2eb4971f) denselben Weg: Versuch 0 aus dem Pool, ab Versuch 1 mit `vorwaerts()` vorgeschoben — nur bei einem `EAPI:Invalid nonce`-Befund, echte Abweisungen werden nie wiederholt.
2. **Zeitstempel:** Nonce = Nanosekunden-Integer (Wallclock, gemeinsamer Pool). Sonde-Protokoll = ISO-8601 ohne Mikrosekunden. Beide Systeme koexistieren; die Sonde kann bei einem `EAPI:Invalid nonce`-Befund den Zaehler selbst vorwaerts schieben und den Zeuge-Aufruf wiederholen.
3. **Signatur:** Identisch in beiden Stellen — kein Unterschied.
