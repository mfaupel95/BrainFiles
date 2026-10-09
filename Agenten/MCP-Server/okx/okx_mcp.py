"""
OKX-MCP: stellt Max' OKX-Konto (Spot, Margin, Futures/Swap, Grid-Bots) als
MCP-Server bereit. Nach dem Vorbild von kraken_mcp.py gebaut - gleiche
Sicherheitsphilosophie, andere API.

Zugangsdaten kommen ausschliesslich aus den Umgebungsvariablen
OKX_API_KEY, OKX_API_SECRET und OKX_API_PASSPHRASE. Sie stehen nirgends in
dieser Datei, in keiner Konfiguration im Vault und in keiner Ausgabe dieses
Servers - auch nicht gekuerzt.

Was dieser Server bewusst NICHT kann:
  * Auszahlen (Withdrawal) ist nicht implementiert. Selbst wenn der
    API-Schluessel das Recht haette, gaebe es hier kein Werkzeug dafuer.
  * Ein- und Auszahlungsadressen abfragen oder anlegen.
  * Einen neuen Grid-Bot anlegen (order-algo) - das hat zu viele
    Stellschrauben (Range, Grid-Anzahl, Investition, Hebel), um es
    blind per Tool-Aufruf zu tun. Bestehende Bots lassen sich lesen und
    stoppen (`okx_grid_bots`, `okx_grid_bot_stoppen`).

Anders als Kraken kennt OKX fuer normale Orders keinen serverseitigen
Pruefmodus (kein `validate=true`). `okx_order_aufgeben` baut die Order
deshalb bei `echt_ausfuehren=False` (Standard) nur zusammen und zeigt den
aktuellen Marktpreis dazu - OHNE die Order-Route aufzurufen. Das ist eine
Simulation auf Client-Seite, keine Pruefung durch OKX selbst. Erst
`echt_ausfuehren=True` schickt die Order wirklich raus - diesen Schritt
macht Max.

Optionaler Demo-Modus: Ist die Umgebungsvariable OKX_DEMO auf "1" gesetzt,
gehen alle privaten Aufrufe mit dem Header `x-simulated-trading: 1` raus
(OKX Paper-Trading-Umgebung, braucht einen eigenen Demo-API-Key). Fuers
Testen der Anbindung ohne echtes Geld.

Aufruf (stdio):
    .venv\\Scripts\\python.exe okx_mcp.py

Testen:
    npx -y @modelcontextprotocol/inspector .venv\\Scripts\\python.exe okx_mcp.py
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from datetime import datetime, timezone

import httpx
from mcp.server.mcpserver import MCPServer

# stdout gehoert dem JSON-RPC-Protokoll. Jede Ausgabe dorthin zerstoert die
# Verbindung, und der Fehler sieht aus wie ein Verbindungsabbruch - deshalb
# gehen Diagnosemeldungen ausschliesslich nach stderr.
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASIS = "https://www.okx.com"
ZEITLIMIT = 20.0

# Zentrale .env-Datei: Max pflegt hier alle API-Keys fuer mehrere Tools an
# einer Stelle. Wird bei jedem Zugriff frisch von der Platte gelesen (kein
# Caching), damit eine Aenderung sofort wirkt, ohne den Server neu zu starten.
ENV_DATEI_PFAD = os.path.join(os.path.expanduser("~"), ".env")

mcp = MCPServer("OKX")


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------

def _ist_platzhalter(wert: str) -> bool:
    """Erkennt Platzhaltertext wie "<YOUR_OKX_API_KEY_HERE>" - kein echter
    Wert, sondern eine unausgefuellte Vorlagen-Zeile. Ohne diese Pruefung
    wuerde ein solcher Platzhalter als "gesetzt" durchgehen und einen echten
    Wert aus einer schwaecher priorisierten Quelle verdecken."""
    if not wert:
        return True
    kandidat = wert.strip()
    if kandidat.startswith("<") and kandidat.endswith(">"):
        return True
    ober = kandidat.upper()
    return "YOUR_" in ober and "_HERE" in ober


def _env_datei_lesen() -> dict:
    """Liest KEY=VALUE-Zeilen aus der zentralen .env-Datei. Kommentare (#)
    und leere Zeilen werden uebersprungen, Anfuehrungszeichen um den Wert
    entfernt. Existiert die Datei nicht oder ist sie nicht lesbar, wird
    stillschweigend ein leeres Ergebnis zurueckgegeben - die Registry bzw.
    die Umgebungsvariablen greifen dann als Fallback."""
    werte: dict[str, str] = {}
    try:
        with open(ENV_DATEI_PFAD, "r", encoding="utf-8") as datei:
            for zeile in datei:
                zeile = zeile.strip()
                if not zeile or zeile.startswith("#") or "=" not in zeile:
                    continue
                schluessel, _, wert = zeile.partition("=")
                schluessel = schluessel.strip()
                wert = wert.strip().strip('"').strip("'")
                if schluessel:
                    werte[schluessel] = wert
    except OSError:
        return {}
    return werte


def _variable(name: str) -> str:
    """Liest eine Zugangsdaten-Variable in dieser Reihenfolge: (1)
    Umgebungsvariable des Prozesses, (2) zentrale .env-Datei
    (%USERPROFILE%\\.env), (3) Windows-Registry (HKCU\\Environment) als
    letzter Fallback fuer Altwerte. Platzhalterwerte wie
    "<YOUR_KEY_HERE>" zaehlen dabei als nicht gesetzt und werden
    uebersprungen, damit sie keinen echten Wert aus einer niedriger
    priorisierten Quelle verdecken."""
    wert = os.environ.get(name, "").strip()
    if wert and not _ist_platzhalter(wert):
        return wert

    wert = _env_datei_lesen().get(name, "").strip()
    if wert and not _ist_platzhalter(wert):
        return wert

    try:
        import winreg
    except ImportError:
        return ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as schluessel:
            wert, _ = winreg.QueryValueEx(schluessel, name)
        wert = str(wert).strip()
        return wert if wert and not _ist_platzhalter(wert) else ""
    except OSError:
        return ""


def _quelle(name: str) -> str:
    """Nur fuer okx_status(): aus welcher Quelle _variable() den Wert
    holen wuerde - ohne den Wert selbst preiszugeben. Hilft beim
    Diagnostizieren, welche der drei Quellen (Prozessumgebung, .env-Datei,
    Registry) gerade tatsaechlich greift, wenn mehrere gleichzeitig
    existieren."""
    wert = os.environ.get(name, "").strip()
    if wert and not _ist_platzhalter(wert):
        return "Umgebungsvariable"
    if wert:
        return "Umgebungsvariable enthaelt nur Platzhalter"

    wert = _env_datei_lesen().get(name, "").strip()
    if wert and not _ist_platzhalter(wert):
        return ".env-Datei"
    env_hat_platzhalter = bool(wert)

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as schluessel:
            reg_wert, _ = winreg.QueryValueEx(schluessel, name)
        reg_wert = str(reg_wert).strip()
        if reg_wert and not _ist_platzhalter(reg_wert):
            return "Registry"
        if reg_wert:
            return ".env-Datei/Registry enthalten nur Platzhalter" if env_hat_platzhalter else "Registry enthaelt nur Platzhalter"
    except OSError:
        pass

    if env_hat_platzhalter:
        return ".env-Datei enthaelt nur Platzhalter"
    return "keine (fehlt in allen drei Quellen)"


def _zugangsdaten() -> tuple[str, str, str]:
    schluessel = _variable("OKX_API_KEY")
    geheim = _variable("OKX_API_SECRET")
    passphrase = _variable("OKX_API_PASSPHRASE")
    if not schluessel or not geheim or not passphrase:
        raise RuntimeError(
            "OKX_API_KEY, OKX_API_SECRET und/oder OKX_API_PASSPHRASE fehlen "
            "oder enthalten nur Platzhalter. Gesucht wird der Reihe nach in: "
            "Umgebungsvariable, zentraler .env-Datei "
            f"({ENV_DATEI_PFAD}), Windows-Registry. okx_status() zeigt, "
            "welche Quelle je Variable greift."
        )
    return schluessel, geheim, passphrase


def _demo_modus() -> bool:
    return _variable("OKX_DEMO") == "1"


def _zeitstempel() -> str:
    # OKX verlangt ISO-8601 UTC mit Millisekunden, z. B. 2020-12-08T09:08:57.123Z
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _signatur(zeitstempel: str, methode: str, pfad: str, koerper: str, geheim: str) -> str:
    """OKX-Signatur: HMAC-SHA256 ueber Zeitstempel+Methode+Pfad+Body, base64.

    Anders als bei Kraken wird der Secret NICHT base64-dekodiert - er wird
    direkt als UTF-8-Bytes fuer den HMAC verwendet.
    """
    nachricht = f"{zeitstempel}{methode}{pfad}{koerper}".encode()
    mac = hmac.new(geheim.encode(), nachricht, hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def _antwort_auswerten(antwort: httpx.Response) -> list:
    # OKX liefert auch bei 4xx/5xx meist einen JSON-Body mit "code"/"msg" -
    # der ist aussagekraeftiger als der nackte HTTP-Status. Nur wenn sich
    # der Body gar nicht als JSON lesen laesst, faellt das auf den
    # generischen HTTP-Fehler zurueck.
    try:
        nutzlast = antwort.json()
    except ValueError:
        antwort.raise_for_status()
        raise RuntimeError(f"OKX antwortet mit Status {antwort.status_code}, kein JSON-Body.")
    return _auswerten(nutzlast)


def _oeffentlich(pfad: str, **parameter) -> list:
    parameter = {k: v for k, v in parameter.items() if v is not None}
    antwort = httpx.get(BASIS + pfad, params=parameter, timeout=ZEITLIMIT)
    return _antwort_auswerten(antwort)


def _privat(methode: str, pfad: str, koerper: dict | list | None = None) -> list:
    schluessel, geheim, passphrase = _zugangsdaten()
    koerper_text = json.dumps(koerper) if koerper is not None else ""
    zeitstempel = _zeitstempel()
    kopf = {
        "OK-ACCESS-KEY": schluessel,
        "OK-ACCESS-SIGN": _signatur(zeitstempel, methode, pfad, koerper_text, geheim),
        "OK-ACCESS-TIMESTAMP": zeitstempel,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }
    if _demo_modus():
        kopf["x-simulated-trading"] = "1"
    if methode == "GET":
        antwort = httpx.get(BASIS + pfad, headers=kopf, timeout=ZEITLIMIT)
    else:
        antwort = httpx.post(BASIS + pfad, headers=kopf, content=koerper_text, timeout=ZEITLIMIT)
    return _antwort_auswerten(antwort)


def _auswerten(nutzlast: dict) -> list:
    # Erfolg/Fehler stecken bei OKX im JSON-Feld "code" (Anfrage-Ebene,
    # "0" = ok) bzw. pro Position in "data[i].sCode" - unabhaengig vom
    # HTTP-Status, der bei Auth-Fehlern durchaus 401/400 sein kann.
    code = nutzlast.get("code")
    if code not in ("0", 0, None):
        raise RuntimeError(f"OKX meldet Fehler {code}: {nutzlast.get('msg')}")
    return nutzlast.get("data") or []


def _kurspfad_zu_query(pfad: str, parameter: dict) -> str:
    parameter = {k: v for k, v in parameter.items() if v is not None}
    if not parameter:
        return pfad
    from urllib.parse import urlencode
    return f"{pfad}?{urlencode(parameter)}"


def _privat_get(pfad: str, **parameter) -> list:
    voller_pfad = _kurspfad_zu_query(pfad, parameter)
    return _privat("GET", voller_pfad)


# --------------------------------------------------------------------------
# Lesen - oeffentlich, ohne Schluessel
# --------------------------------------------------------------------------

@mcp.tool()
def okx_kurs(inst_id: str) -> dict:
    """Aktueller Kurs zu einem Handelspaar.

    Args:
        inst_id: OKX-Instrumenten-ID, z. B. "BTC-USDT" (Spot) oder
            "BTC-USDT-SWAP" (Perpetual Future). Unbekannt? Erst
            `okx_paare_suchen`.
    """
    roh = _oeffentlich("/api/v5/market/ticker", instId=inst_id)
    if not roh:
        raise ValueError(f"Keine Daten zu {inst_id!r}. Instrumenten-ID mit okx_paare_suchen pruefen.")
    w = roh[0]
    return {
        "instrument": w["instId"],
        "letzter_kurs": w["last"],
        "geld": w["bidPx"],
        "brief": w["askPx"],
        "hoch_24h": w["high24h"],
        "tief_24h": w["low24h"],
        "volumen_24h": w["vol24h"],
        "eroeffnung_24h": w.get("open24h"),
    }


@mcp.tool()
def okx_paare_suchen(inst_typ: str = "SPOT", suchbegriff: str = "", limit: int = 25) -> dict:
    """Findet OKX-Instrumenten-IDs.

    Args:
        inst_typ: "SPOT", "MARGIN", "SWAP" (Perpetual Futures), "FUTURES"
            (Termin-Kontrakte mit Verfall) oder "OPTION". Standard "SPOT".
        suchbegriff: Teilstring, Gross-/Kleinschreibung egal. Leer = erste `limit` Treffer.
        limit: Anzahl Treffer, Standard 25.
    """
    roh = _oeffentlich("/api/v5/public/instruments", instType=inst_typ.upper())
    such = suchbegriff.upper()
    treffer = {
        w["instId"]: {
            "basis": w.get("baseCcy") or w.get("ctValCcy"),
            "gegen": w.get("quoteCcy") or w.get("settleCcy"),
            "status": w.get("state"),
        }
        for w in roh
        if not such or such in w["instId"].upper()
    }
    gekuerzt = dict(list(treffer.items())[: max(1, min(limit, 200))])
    return {"anzahl_gesamt": len(treffer), "paare": gekuerzt}


@mcp.tool()
def okx_candles(inst_id: str, intervall: str = "1D", limit: int = 30) -> dict:
    """Kerzen (OHLCV) zu einem Instrument.

    Args:
        inst_id: OKX-Instrumenten-ID, z. B. "BTC-USDT".
        intervall: "1m","3m","5m","15m","30m","1H","2H","4H","6H","12H",
            "1D","1W","1M". Standard "1D" (Tageskerzen).
        limit: Anzahl der juengsten Kerzen, Standard 30 (Maximum 300).
    """
    roh = _oeffentlich("/api/v5/market/candles", instId=inst_id, bar=intervall, limit=max(1, min(limit, 300)))
    if not roh:
        raise ValueError(f"Keine Kerzen zu {inst_id!r}. Instrumenten-ID mit okx_paare_suchen pruefen.")
    return {
        "instrument": inst_id,
        "intervall": intervall,
        "kerzen": [
            {
                "zeit": time.strftime("%Y-%m-%d %H:%M", time.localtime(int(k[0]) / 1000)),
                "offen": k[1], "hoch": k[2], "tief": k[3], "schluss": k[4],
                "volumen": k[5],
            }
            for k in reversed(roh)
        ],
    }


# --------------------------------------------------------------------------
# Lesen - privat, braucht API-Schluessel-Recht "Lesen" (Read)
# --------------------------------------------------------------------------

@mcp.tool()
def okx_status() -> dict:
    """Prueft, ob die Anbindung steht - ohne die Zugangsdaten preiszugeben.

    Zeigt zusaetzlich je Variable, aus welcher der drei Quellen
    (Umgebungsvariable / zentrale .env-Datei / Registry) sie tatsaechlich
    gezogen wird - nuetzlich, wenn mehrere Quellen gleichzeitig existieren
    und nicht klar ist, welche gerade greift.
    """
    quellen = {
        "OKX_API_KEY": _quelle("OKX_API_KEY"),
        "OKX_API_SECRET": _quelle("OKX_API_SECRET"),
        "OKX_API_PASSPHRASE": _quelle("OKX_API_PASSPHRASE"),
    }
    gesetzt = {
        "OKX_API_KEY": bool(_variable("OKX_API_KEY")),
        "OKX_API_SECRET": bool(_variable("OKX_API_SECRET")),
        "OKX_API_PASSPHRASE": bool(_variable("OKX_API_PASSPHRASE")),
    }
    if not all(gesetzt.values()):
        return {
            "variablen_gesetzt": gesetzt,
            "quellen": quellen,
            "env_datei_pfad": ENV_DATEI_PFAD,
            "verbindung": "nicht geprueft - Variablen fehlen oder enthalten nur Platzhalter",
        }
    try:
        guthaben = _privat_get("/api/v5/account/balance")
        return {
            "variablen_gesetzt": gesetzt,
            "quellen": quellen,
            "env_datei_pfad": ENV_DATEI_PFAD,
            "verbindung": "ok",
            "demo_modus": _demo_modus(),
            "waehrungen_im_konto": len(guthaben[0].get("details", [])) if guthaben else 0,
        }
    except RuntimeError as fehler:
        return {
            "variablen_gesetzt": gesetzt,
            "quellen": quellen,
            "env_datei_pfad": ENV_DATEI_PFAD,
            "verbindung": "abgelehnt",
            "meldung": str(fehler),
        }


@mcp.tool()
def okx_guthaben(nur_belegte: bool = True) -> dict:
    """Kontostaende im Trading-Konto je Waehrung. Braucht API-Recht 'Lesen'.

    Args:
        nur_belegte: Nullbestaende ausblenden, Standard an.
    """
    roh = _privat_get("/api/v5/account/balance")
    details = roh[0].get("details", []) if roh else []
    return {
        w["ccy"]: {
            "verfuegbar": w["availBal"],
            "gesamt": w["cashBal"],
            "in_bewertung_eq_usd": w.get("eqUsd"),
        }
        for w in details
        if not nur_belegte or float(w["cashBal"] or 0) > 0
    }


@mcp.tool()
def okx_positionen() -> dict:
    """Offene Positionen bei Margin/Swap/Futures/Options - inkl. PnL, Hebel, Liq.-Preis.

    Braucht API-Recht 'Lesen'. Fuer reine Spot-Bestaende siehe `okx_guthaben`.
    """
    roh = _privat_get("/api/v5/account/positions")
    return {
        "anzahl": len(roh),
        "positionen": [
            {
                "instrument": w["instId"],
                "richtung": w["posSide"],
                "groesse": w["pos"],
                "einstandskurs": w.get("avgPx"),
                "hebel": w.get("lever"),
                "unrealisierter_pnl": w.get("upl"),
                "unrealisierter_pnl_prozent": w.get("uplRatio"),
                "liquidationskurs": w.get("liqPx"),
                "margin_modus": w.get("mgnMode"),
            }
            for w in roh
        ],
    }


@mcp.tool()
def okx_offene_orders(inst_typ: str | None = None) -> dict:
    """Alle offenen (regulaeren) Orders. Braucht API-Recht 'Lesen'.

    Args:
        inst_typ: Optional filtern nach "SPOT", "MARGIN", "SWAP", "FUTURES", "OPTION".
    """
    roh = _privat_get("/api/v5/trade/orders-pending", instType=inst_typ)
    return {
        "anzahl": len(roh),
        "orders": [
            {
                "order_id": w["ordId"],
                "instrument": w["instId"],
                "richtung": w["side"],
                "art": w["ordType"],
                "menge": w["sz"],
                "preis": w.get("px"),
                "ausgefuehrt": w.get("accFillSz"),
                "status": w.get("state"),
                "eroeffnet": time.strftime("%Y-%m-%d %H:%M", time.localtime(int(w["cTime"]) / 1000)),
            }
            for w in roh
        ],
    }


@mcp.tool()
def okx_geschlossene_orders(inst_typ: str = "SPOT", limit: int = 20) -> dict:
    """Zuletzt geschlossene/stornierte Orders der letzten 7 Tage. Braucht 'Lesen'.

    Args:
        inst_typ: "SPOT", "MARGIN", "SWAP", "FUTURES" oder "OPTION". Pflichtfeld bei OKX.
        limit: Anzahl, Standard 20 (Maximum 100).
    """
    roh = _privat_get("/api/v5/trade/orders-history", instType=inst_typ.upper(), limit=max(1, min(limit, 100)))
    return {
        "orders": [
            {
                "order_id": w["ordId"],
                "instrument": w["instId"],
                "richtung": w["side"],
                "status": w.get("state"),
                "menge": w["sz"],
                "ausgefuehrt": w.get("accFillSz"),
                "durchschnittskurs": w.get("avgPx"),
                "gebuehr": w.get("fee"),
                "geschlossen": (
                    time.strftime("%Y-%m-%d %H:%M", time.localtime(int(w["uTime"]) / 1000))
                    if w.get("uTime") else None
                ),
            }
            for w in roh
        ]
    }


@mcp.tool()
def okx_trades(inst_typ: str = "SPOT", limit: int = 20) -> dict:
    """Tatsaechlich ausgefuehrte Trades (Fills). Braucht API-Recht 'Lesen'.

    Args:
        inst_typ: "SPOT", "MARGIN", "SWAP", "FUTURES" oder "OPTION". Pflichtfeld bei OKX.
        limit: Anzahl, Standard 20 (Maximum 100).
    """
    roh = _privat_get("/api/v5/trade/fills", instType=inst_typ.upper(), limit=max(1, min(limit, 100)))
    return {
        "trades": [
            {
                "instrument": w["instId"],
                "richtung": w["side"],
                "kurs": w["fillPx"],
                "menge": w["fillSz"],
                "gebuehr": w.get("fee"),
                "zeit": time.strftime("%Y-%m-%d %H:%M", time.localtime(int(w["ts"]) / 1000)),
            }
            for w in roh
        ]
    }


@mcp.tool()
def okx_grid_bots() -> dict:
    """Status aller Grid-Bots (Spot- und Futures-Grid) - laufend und historisch.

    Braucht API-Recht 'Lesen'. Zeigt u. a. Investition, aktuellen Wert und
    PnL je Bot. Eine neue Grid-Strategie anlegen kann dieses Werkzeug bewusst
    nicht - das bleibt der OKX-App vorbehalten (siehe Modulbeschreibung).
    """
    def _bots(pfad: str, art: str) -> list:
        ergebnis = []
        for algo_typ in ("grid", "contract_grid"):
            try:
                roh = _privat_get(pfad, algoOrdType=algo_typ)
            except RuntimeError:
                continue
            for w in roh:
                ergebnis.append({
                    "algo_id": w.get("algoId"),
                    "instrument": w.get("instId"),
                    "typ": "Futures-Grid" if algo_typ == "contract_grid" else "Spot-Grid",
                    "status": w.get("state"),
                    "investition": w.get("investment"),
                    "pnl": w.get("pnl") or w.get("totalPnl"),
                    "pnl_prozent": w.get("pnlRatio"),
                    "hebel": w.get("lever"),
                    "range_unten": w.get("minPx"),
                    "range_oben": w.get("maxPx"),
                    "angelegt": (
                        time.strftime("%Y-%m-%d %H:%M", time.localtime(int(w["cTime"]) / 1000))
                        if w.get("cTime") else None
                    ),
                    "quelle": art,
                })
        return ergebnis

    laufend = _bots("/api/v5/tradingBot/grid/orders-algo-pending", "laufend")
    verlauf = _bots("/api/v5/tradingBot/grid/orders-algo-history", "beendet")
    return {"laufend": laufend, "beendet_zuletzt": verlauf[:20]}


# --------------------------------------------------------------------------
# Schreiben - braucht API-Recht 'Traden' (Trade)
# --------------------------------------------------------------------------

@mcp.tool()
def okx_order_aufgeben(
    inst_id: str,
    richtung: str,
    menge: str,
    art: str = "limit",
    preis: str | None = None,
    handelsmodus: str = "cash",
    hebel: str | None = None,
    echt_ausfuehren: bool = False,
) -> dict:
    """Gibt eine Order auf. OKX kennt keinen serverseitigen Pruefmodus wie Kraken.

    Mit `echt_ausfuehren=False` (Standard) wird NUR die Order-Struktur
    zusammengebaut und der aktuelle Marktpreis dazugestellt - es wird KEINE
    Anfrage an die Order-Route geschickt. Das ist eine Simulation auf
    Client-Seite, keine Pruefung durch OKX. Erst `echt_ausfuehren=True`
    platziert wirklich. Das echte Platzieren ist Max' Schritt; der Assistent
    setzt `echt_ausfuehren` nicht selbst.

    Args:
        inst_id: OKX-Instrumenten-ID, z. B. "BTC-USDT" oder "BTC-USDT-SWAP".
        richtung: "buy" oder "sell".
        menge: Menge als Zeichenkette. Bei Spot in der Basiswaehrung, bei
            Swap/Futures in Kontrakten.
        art: "limit" (Standard), "market", "post_only", "fok" oder "ioc".
        preis: Limitpreis - bei art="limit"/"post_only"/"fok"/"ioc" Pflicht.
        handelsmodus: "cash" (Spot, Standard), "cross" oder "isolated"
            (Margin/Swap/Futures).
        hebel: Optional - setzt vor der Order den Hebel fuer dieses
            Instrument (nur bei Margin/Swap/Futures relevant).
        echt_ausfuehren: False = nur zusammenbauen und Marktpreis zeigen
            (Standard). True = wirklich aufgeben.
    """
    if richtung not in ("buy", "sell"):
        raise ValueError('richtung muss "buy" oder "sell" sein.')
    if art not in ("limit", "market", "post_only", "fok", "ioc"):
        raise ValueError('art muss "limit", "market", "post_only", "fok" oder "ioc" sein.')
    if art != "market" and not preis:
        raise ValueError(f"Bei art={art!r} ist preis erforderlich.")

    order = {
        "instId": inst_id,
        "tdMode": handelsmodus,
        "side": richtung,
        "ordType": art,
        "sz": str(menge),
    }
    if art != "market":
        order["px"] = preis

    if not echt_ausfuehren:
        try:
            markt = okx_kurs(inst_id)
        except Exception:
            markt = None
        return {
            "modus": "nur zusammengebaut, nichts an OKX geschickt",
            "order_entwurf": order,
            "aktueller_marktkurs": markt,
        }

    if hebel:
        _privat("POST", "/api/v5/account/set-leverage", {
            "instId": inst_id, "lever": str(hebel), "mgnMode": handelsmodus,
        })

    ergebnis = _privat("POST", "/api/v5/trade/order", order)
    w = ergebnis[0] if ergebnis else {}
    if w.get("sCode") not in ("0", None):
        raise RuntimeError(f"OKX lehnt Order ab ({w.get('sCode')}): {w.get('sMsg')}")
    return {
        "modus": "wirklich aufgegeben",
        "order_id": w.get("ordId"),
        "client_order_id": w.get("clOrdId"),
    }


@mcp.tool()
def okx_order_stornieren(inst_id: str, order_id: str) -> dict:
    """Storniert eine offene Order. Bewegt kein Geld.

    Args:
        inst_id: OKX-Instrumenten-ID der Order.
        order_id: Order-ID aus `okx_offene_orders`.
    """
    ergebnis = _privat("POST", "/api/v5/trade/cancel-order", {"instId": inst_id, "ordId": order_id})
    w = ergebnis[0] if ergebnis else {}
    if w.get("sCode") not in ("0", None):
        raise RuntimeError(f"OKX lehnt Stornierung ab ({w.get('sCode')}): {w.get('sMsg')}")
    return {"storniert": True, "order_id": w.get("ordId")}


@mcp.tool()
def okx_grid_bot_stoppen(algo_id: str, inst_id: str, markt_glattstellung: bool = False) -> dict:
    """Stoppt einen laufenden Grid-Bot. Legt KEINEN neuen Bot an.

    Args:
        algo_id: Bot-ID aus `okx_grid_bots`.
        inst_id: OKX-Instrumenten-ID des Bots.
        markt_glattstellung: True = alle Positionen des Bots per Market-Order
            sofort glattstellen. False (Standard) = Positionen bleiben nach
            dem Stopp bestehen und muessen separat verwaltet werden.
    """
    ergebnis = _privat("POST", "/api/v5/tradingBot/grid/stop-order-algo", [{
        "algoId": algo_id, "instId": inst_id, "mktClose": markt_glattstellung,
    }])
    w = ergebnis[0] if ergebnis else {}
    if w.get("sCode") not in ("0", None):
        raise RuntimeError(f"OKX lehnt Stopp ab ({w.get('sCode')}): {w.get('sMsg')}")
    return {"gestoppt": True, "algo_id": w.get("algoId")}


if __name__ == "__main__":
    mcp.run()
