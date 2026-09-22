"""
Kraken-MCP: stellt Max' Kraken-Pro-Konto als MCP-Server bereit.

Zugangsdaten kommen ausschliesslich aus den Umgebungsvariablen
KRAKEN_API_KEY und KRAKEN_API_SECRET. Sie stehen nirgends in dieser Datei,
in keiner Konfiguration im Vault und in keiner Ausgabe - auch nicht gekuerzt.

Was dieser Server bewusst NICHT kann:
  * Auszahlen (`Withdraw`, `WithdrawFunds`) ist nicht implementiert. Selbst
    wenn der API-Schluessel das Recht haette, gaebe es hier kein Werkzeug dafuer.
  * Ein- und Auszahlungsadressen abfragen oder anlegen.

Orders: `kraken_order_aufgeben` laeuft standardmaessig als Pruefung
(validate=True). Kraken rechnet die Order dann komplett durch und meldet
Fehler, legt sie aber nicht ins Buch. Nur ein ausdrueckliches
`echt_ausfuehren=True` platziert wirklich - und diesen Schritt macht Max.

Aufruf (stdio):
    .venv\\Scripts\\python.exe kraken_mcp.py

Testen:
    npx -y @modelcontextprotocol/inspector .venv\\Scripts\\python.exe kraken_mcp.py
"""

import base64
import hashlib
import hmac
import os
import sys
import time
import urllib.parse

import httpx
from mcp.server.mcpserver import MCPServer

# Gemeinsamer Kraken-nonce-Pool mit dem Handel-Dauerlauf: derselbe
# KRAKEN_API_KEY, deshalb dieselbe monotone nonce-Quelle (sonst ueberholt
# ein Prozess den anderen und Kraken antwortet "EAPI:Invalid nonce").
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "Handel", "kraken"))
from nonce_pool import monotone_nonce as _monotone_nonce

# stdout gehoert dem JSON-RPC-Protokoll. Jede Ausgabe dorthin zerstoert die
# Verbindung, und der Fehler sieht aus wie ein Verbindungsabbruch - deshalb
# gehen Diagnosemeldungen ausschliesslich nach stderr.
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASIS = "https://api.kraken.com"
ZEITLIMIT = 20.0

mcp = MCPServer("Kraken")

# --------------------------------------------------------------------------
# Freigabe-Beleg: das Tor fuer echte Orders aus dem MCP
# --------------------------------------------------------------------------
# Ein MCP-Werkzeug ist aus JEDER Sitzung aufrufbar - aus einem Chat, aus einem
# Bot, aus einer A2A-Nachricht. Die Sperrenkette der Handels-Spuren haengt aber
# am Skript. Deshalb gilt: der MCP fuehrt NUR aus, was eine Spur vorher
# beschlossen und mit einem Beleg versehen hat (Agenten/Handel/freigabebeleg.py).
# Ohne Beleg bleibt es beim Trockenlauf. Das Modul stellt keine Belege aus -
# das kann nur die Spur, und nur bei offenem Freigabefenster.
HANDEL = os.environ.get("MAXHIRN_HANDEL") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "Handel")


def _beleg_modul():
    """freigabebeleg.py ueber den PFAD laden (kein sys.path-Eintrag, der
    gleichnamige Spurenmodule verdecken koennte). Der Cache-Schluessel enthaelt
    den Pfad - zwei verschiedene Ordner duerfen sich nicht denselben Eintrag
    teilen (sonst liest der MCP spaeter aus dem falschen Ordner)."""
    import importlib.util
    schluessel = "freigabebeleg_mcp@%s" % os.path.abspath(HANDEL)
    if schluessel in sys.modules:
        return sys.modules[schluessel]
    pfad = os.path.join(HANDEL, "freigabebeleg.py")
    spec = importlib.util.spec_from_file_location(schluessel, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[schluessel] = modul
    spec.loader.exec_module(modul)
    return modul


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------

def _variable(name: str) -> str:
    """Liest eine Benutzervariable - notfalls direkt aus der Registry.

    Der MCP-Client startet Server-Prozesse mit einer bereinigten Umgebung:
    selbst gesetzte Benutzervariablen kommen dort nicht an (geprueft
    19.08.2026 - KRAKEN_API_KEY steht unter HKEY_CURRENT_USER, Environment
    und ist im
    Kindprozess trotzdem leer). Deshalb faellt diese Funktion auf die
    Registry zurueck, statt die Zugangsdaten in eine Konfigurationsdatei
    zu schreiben.
    """
    wert = os.environ.get(name, "").strip()
    if wert:
        return wert
    try:
        import winreg
    except ImportError:
        return ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as schluessel:
            wert, _ = winreg.QueryValueEx(schluessel, name)
        return str(wert).strip()
    except OSError:
        return ""


def _zugangsdaten() -> tuple[str, str]:
    schluessel = _variable("KRAKEN_SPOT_API_KEY")
    geheim = _variable("KRAKEN_SPOT_API_SECRET")
    if not schluessel or not geheim:
        raise RuntimeError(
            "KRAKEN_SPOT_API_KEY und/oder KRAKEN_SPOT_API_SECRET fehlen. Beide als "
            "Windows-Benutzervariablen setzen - der "
            "Server liest sie auch direkt aus der Registry."
        )
    return schluessel, geheim


def _signatur(pfad: str, daten: dict, geheim: str) -> str:
    """Kraken-Signatur: HMAC-SHA512 ueber Pfad + SHA256(nonce + Formulardaten).

    Der Secret ist base64-kodiert und muss vor dem HMAC dekodiert werden -
    wird das vergessen, antwortet Kraken mit 'Invalid key', was wie ein
    falscher Schluessel aussieht und nicht wie ein Signaturfehler.
    """
    formular = urllib.parse.urlencode(daten)
    roh = (str(daten["nonce"]) + formular).encode()
    nachricht = pfad.encode() + hashlib.sha256(roh).digest()
    mac = hmac.new(base64.b64decode(geheim), nachricht, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode()


def _oeffentlich(methode: str, **parameter) -> dict:
    pfad = f"/0/public/{methode}"
    antwort = httpx.get(BASIS + pfad, params=parameter, timeout=ZEITLIMIT)
    antwort.raise_for_status()
    return _auswerten(antwort.json())


def _privat(methode: str, **parameter) -> dict:
    schluessel, geheim = _zugangsdaten()
    pfad = f"/0/private/{methode}"
    # Kraken verlangt streng monotone Nonces je Schluessel. Der Dauerlauf
    # (Handel/kraken.py) und dieser MCP-Server teilen denselben
    # KRAKEN_SPOT_API_KEY - jeder erhebt die nonce deshalb ueber den gemeinsamen
    # nonce_pool (spezierende Datei), sonst antwortet Kraken
    # "EAPI:Invalid nonce" (gemessen 2026-09-19).
    daten = {"nonce": str(_monotone_nonce()), **{
        k: v for k, v in parameter.items() if v is not None
    }}
    kopf = {
        "API-Key": schluessel,
        "API-Sign": _signatur(pfad, daten, geheim),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    antwort = httpx.post(BASIS + pfad, data=daten, headers=kopf, timeout=ZEITLIMIT)
    antwort.raise_for_status()
    return _auswerten(antwort.json())


def _auswerten(nutzlast: dict) -> dict:
    fehler = nutzlast.get("error") or []
    if fehler:
        # EGeneral:Permission denied heisst fast immer: dem Schluessel fehlt
        # das passende Recht, nicht dass der Schluessel falsch ist.
        raise RuntimeError("Kraken meldet: " + "; ".join(fehler))
    return nutzlast.get("result") or {}


# --------------------------------------------------------------------------
# Lesen - oeffentlich, ohne Schluessel
# --------------------------------------------------------------------------

@mcp.tool()
def kraken_kurs(paare: str) -> dict:
    """Aktuelle Kurse zu einem oder mehreren Handelspaaren.

    Args:
        paare: Kraken-Paarnamen, mit Komma getrennt, z. B. "XBTUSD" oder
            "XBTEUR,ETHEUR". Unbekannter Name? Erst `kraken_paare_suchen`.

    Returns:
        Je Paar: letzter Kurs, Geld/Brief, Tageshoch/-tief, 24h-Volumen.
    """
    roh = _oeffentlich("Ticker", pair=paare)
    ergebnis = {}
    for name, w in roh.items():
        ergebnis[name] = {
            "letzter_kurs": w["c"][0],
            "geld": w["b"][0],
            "brief": w["a"][0],
            "hoch_24h": w["h"][1],
            "tief_24h": w["l"][1],
            "volumen_24h": w["v"][1],
            "eroeffnung": w.get("o"),
        }
    return ergebnis


@mcp.tool()
def kraken_paare_suchen(suchbegriff: str = "", limit: int = 25) -> dict:
    """Findet Kraken-Paarnamen. Kraken nutzt eigene Kuerzel (XXBTZEUR statt BTCEUR).

    Args:
        suchbegriff: Teilstring, Gross-/Kleinschreibung egal. Leer = erste `limit` Paare.
        limit: Anzahl Treffer, Standard 25.
    """
    alle = _oeffentlich("AssetPairs")
    such = suchbegriff.upper()
    treffer = {
        name: {"basis": w.get("base"), "gegen": w.get("quote"), "anzeigename": w.get("wsname")}
        for name, w in alle.items()
        if not such or such in name.upper() or such in str(w.get("wsname", "")).upper()
    }
    gekuerzt = dict(list(treffer.items())[: max(1, min(limit, 200))])
    return {"anzahl_gesamt": len(treffer), "paare": gekuerzt}


@mcp.tool()
def kraken_candles(paar: str, intervall: int = 1440, limit: int = 30) -> dict:
    """OHLC-Kerzen zu einem Paar - fuer Trend- und Volatilitaetsbetrachtungen.

    Args:
        paar: Kraken-Paarname, z. B. "XBTEUR".
        intervall: Minuten je Kerze. Erlaubt: 1, 5, 15, 30, 60, 240, 1440,
            10080, 21600. Standard 1440 (Tageskerzen).
        limit: Anzahl der juengsten Kerzen, Standard 30.
    """
    erlaubt = (1, 5, 15, 30, 60, 240, 1440, 10080, 21600)
    if intervall not in erlaubt:
        raise ValueError(f"Intervall {intervall} nicht erlaubt. Moeglich: {erlaubt}")
    roh = _oeffentlich("OHLC", pair=paar, interval=intervall)
    schluessel = next((k for k in roh if k != "last"), None)
    if schluessel is None:
        raise ValueError(f"Keine Daten zu {paar!r}. Paarname mit kraken_paare_suchen pruefen.")
    kerzen = roh[schluessel][-max(1, min(limit, 720)):]
    return {
        "paar": schluessel,
        "intervall_minuten": intervall,
        "kerzen": [
            {
                "zeit": time.strftime("%Y-%m-%d %H:%M", time.localtime(k[0])),
                "offen": k[1], "hoch": k[2], "tief": k[3], "schluss": k[4],
                "volumen": k[6],
            }
            for k in kerzen
        ],
    }


# --------------------------------------------------------------------------
# Lesen - privat, braucht Query-Rechte
# --------------------------------------------------------------------------

@mcp.tool()
def kraken_status() -> dict:
    """Prueft, ob die Anbindung steht - ohne die Zugangsdaten preiszugeben.

    Meldet nur, OB Schluessel und Secret gesetzt sind und ob Kraken sie
    akzeptiert. Die Werte selbst werden nie ausgegeben, auch nicht gekuerzt.
    """
    gesetzt = {
            "KRAKEN_SPOT_API_KEY": bool(_variable("KRAKEN_SPOT_API_KEY")),
            "KRAKEN_SPOT_API_SECRET": bool(_variable("KRAKEN_SPOT_API_SECRET")),
        }
    if not all(gesetzt.values()):
        return {"variablen_gesetzt": gesetzt, "verbindung": "nicht geprueft - Variablen fehlen"}
    try:
        guthaben = _privat("Balance")
        return {
            "variablen_gesetzt": gesetzt,
            "verbindung": "ok",
            "positionen_im_konto": len(guthaben),
        }
    except RuntimeError as fehler:
        return {"variablen_gesetzt": gesetzt, "verbindung": "abgelehnt", "meldung": str(fehler)}


@mcp.tool()
def kraken_guthaben(nur_belegte: bool = True) -> dict:
    """Kontostaende je Waehrung. Braucht das Recht 'Query Funds'.

    Args:
        nur_belegte: Nullbestaende ausblenden, Standard an.
    """
    roh = _privat("Balance")
    return {
        w: b for w, b in sorted(roh.items())
        if not nur_belegte or float(b) > 0
    }


@mcp.tool()
def kraken_offene_orders() -> dict:
    """Alle offenen Orders. Braucht das Recht 'Query Open Orders & Trades'."""
    roh = _privat("OpenOrders").get("open", {})
    return {
        "anzahl": len(roh),
        "orders": {
            kennung: {
                "paar": w["descr"]["pair"],
                "richtung": w["descr"]["type"],
                "art": w["descr"]["ordertype"],
                "menge": w["vol"],
                "ausgefuehrt": w["vol_exec"],
                "beschreibung": w["descr"]["order"],
                "eroeffnet": time.strftime("%Y-%m-%d %H:%M", time.localtime(w["opentm"])),
            }
            for kennung, w in roh.items()
        },
    }


@mcp.tool()
def kraken_geschlossene_orders(limit: int = 20) -> dict:
    """Zuletzt geschlossene Orders. Braucht 'Query Closed Orders & Trades'.

    Args:
        limit: Anzahl, Standard 20.
    """
    roh = _privat("ClosedOrders").get("closed", {})
    auswahl = list(roh.items())[: max(1, min(limit, 50))]
    return {
        "orders": {
            kennung: {
                "paar": w["descr"]["pair"],
                "richtung": w["descr"]["type"],
                "status": w["status"],
                "menge": w["vol"],
                "ausgefuehrt": w["vol_exec"],
                "kosten": w.get("cost"),
                "gebuehr": w.get("fee"),
                "durchschnittskurs": w.get("price"),
                "geschlossen": (
                    time.strftime("%Y-%m-%d %H:%M", time.localtime(w["closetm"]))
                    if w.get("closetm") else None
                ),
            }
            for kennung, w in auswahl
        }
    }


@mcp.tool()
def kraken_trades(limit: int = 20) -> dict:
    """Tatsaechlich ausgefuehrte Trades (Fills). Braucht 'Query Closed Orders & Trades'.

    Args:
        limit: Anzahl, Standard 20.
    """
    roh = _privat("TradesHistory").get("trades", {})
    auswahl = list(roh.items())[: max(1, min(limit, 50))]
    return {
        "trades": {
            kennung: {
                "paar": w["pair"],
                "richtung": w["type"],
                "kurs": w["price"],
                "menge": w["vol"],
                "kosten": w["cost"],
                "gebuehr": w["fee"],
                "zeit": time.strftime("%Y-%m-%d %H:%M", time.localtime(w["time"])),
            }
            for kennung, w in auswahl
        }
    }


@mcp.tool()
def kraken_ledger(limit: int = 20) -> dict:
    """Kontobewegungen: Ein-/Auszahlungen, Trades, Gebuehren. Braucht 'Query Ledger Entries'.

    Args:
        limit: Anzahl, Standard 20.
    """
    roh = _privat("Ledgers").get("ledger", {})
    auswahl = list(roh.items())[: max(1, min(limit, 50))]
    return {
        "eintraege": {
            kennung: {
                "art": w["type"],
                "waehrung": w["asset"],
                "betrag": w["amount"],
                "gebuehr": w["fee"],
                "saldo_danach": w["balance"],
                "zeit": time.strftime("%Y-%m-%d %H:%M", time.localtime(w["time"])),
            }
            for kennung, w in auswahl
        }
    }


# --------------------------------------------------------------------------
# Schreiben - braucht 'Create & Modify Orders'
# --------------------------------------------------------------------------

@mcp.tool()
def kraken_order_aufgeben(
    paar: str,
    richtung: str,
    menge: str,
    art: str = "limit",
    preis: str | None = None,
    echt_ausfuehren: bool = False,
) -> dict:
    """Gibt eine Order auf - NUR als PRUEFUNG, niemals echt (Tor seit 22.09.2026).

    Dieses Werkzeug schickt die Order durch die komplette Validierung von Kraken
    und meldet jeden Fehler, legt sie aber NICHT ins Buch. Es kann seit dem
    22.09.2026 auch nicht mehr echt ausfuehren: echte Orders laufen
    ausschliesslich ueber `kraken_order_mit_beleg`, und das verlangt einen
    Beleg, den nur eine Handels-Spur bei offenem Freigabefenster ausstellen
    kann. Grund: ein MCP-Werkzeug ist aus jeder Sitzung aufrufbar, die
    Sperrenkette der Spuren haengt aber am Skript.

    Args:
        paar: Kraken-Paarname, z. B. "XBTEUR".
        richtung: "buy" oder "sell".
        menge: Menge in der Basiswaehrung, als Zeichenkette, z. B. "0.01".
        art: "limit" (Standard) oder "market".
        preis: Limitpreis - bei art="limit" Pflicht, bei "market" weglassen.
        echt_ausfuehren: wird nicht mehr unterstuetzt - immer nur Pruefung.
    """
    if richtung not in ("buy", "sell"):
        raise ValueError('richtung muss "buy" oder "sell" sein.')
    if art not in ("limit", "market"):
        raise ValueError('art muss "limit" oder "market" sein.')
    if art == "limit" and not preis:
        raise ValueError("Bei art='limit' ist preis erforderlich.")
    if echt_ausfuehren:
        return {
            "modus": "abgelehnt",
            "grund": "Echte Orders nur ueber kraken_order_mit_beleg (Beleg der "
                     "Spur bei offenem Freigabefenster). Dieses Werkzeug prueft "
                     "nur.",
        }

    parameter = {
        "pair": paar,
        "type": richtung,
        "ordertype": art,
        "volume": str(menge),
        "price": preis if art == "limit" else None,
    }
    # Kraken wertet die blosse Anwesenheit von 'validate' als Pruefmodus -
    # "false" als Text wuerde ebenfalls pruefen. Deshalb den Schluessel im
    # Echtfall komplett weglassen statt ihn auf false zu setzen.
    if not echt_ausfuehren:
        parameter["validate"] = "true"

    ergebnis = _privat("AddOrder", **parameter)
    return {
        "modus": "wirklich aufgegeben" if echt_ausfuehren else "nur geprueft, nichts platziert",
        "beschreibung": ergebnis.get("descr", {}).get("order"),
        "order_kennungen": ergebnis.get("txid", []),
    }


@mcp.tool()
def kraken_beleg_uebersicht() -> dict:
    """Zeigt die Freigabe-Belege, die JETZT gelten (rein lesend).

    Ein Beleg ist die Erlaubnis einer Handels-Spur, eine bestimmte Order
    auszufuehren. Er gilt nur kurz, nur fuer eine Seite, ein Paar, eine
    Hoechstmenge und einen Hoechstpreis, und nur einmal. Ohne gueltigen Beleg
    kann `kraken_order_mit_beleg` nichts ausfuehren.
    """
    try:
        module = _beleg_modul()
    except Exception as e:                                        # noqa: BLE001
        return {"fehler": "freigabebeleg nicht ladbar: %s" % e}
    offen = module.offene()
    return {"anzahl": len(offen), "belege": offen}


@mcp.tool()
def kraken_order_mit_beleg(
    spur: str,
    beleg: str,
    paar: str,
    richtung: str,
    menge: str,
    art: str = "limit",
    preis: str | None = None,
    echt_ausfuehren: bool = False,
) -> dict:
    """Fuehrt eine Order aus, die eine Spur mit einem Beleg freigegeben hat.

    Das ist der EINZIGE Weg, auf dem der MCP wirklich handeln darf. Der Beleg
    kommt von der Spur (Agenten/Handel/freigabebeleg.py) und beweist, dass die
    Entscheidung unter deren Wachen gefallen ist: offenes Freigabefenster und
    `handel_erlaubt=true`. Dieses Werkzeug stellt KEINE Belege aus - es prueft
    nur und fuehrt aus.

    Ohne gueltigen Beleg passiert nichts (Absage mit Grund). Mit
    `echt_ausfuehren=False` (Standard) wird nur durchgerechnet, der Beleg
    bleibt bestehen. Erst `echt_ausfuehren=True` platziert wirklich und
    verbraucht den Beleg.

    Args:
        spur: Name der Handels-Spur, die den Beleg ausgestellt hat.
        beleg: Beleg-Kennung aus `kraken_beleg_uebersicht`.
        paar: Kraken-Paarname, z. B. "XBTEUR" - muss der Beleg tragen.
        richtung: "buy" oder "sell" - muss der Beleg tragen.
        menge: Menge in der Basiswaehrung; darf die Hoechstmenge des Belegs
            nicht ueberschreiten.
        art: "limit" (Standard) oder "market".
        preis: Limitpreis; beim Kauf darf er den Hoechstpreis des Belegs nicht
            ueberschreiten (0,1 % Rundungstoleranz).
        echt_ausfuehren: True platziert wirklich und verbraucht den Beleg.
    """
    try:
        module = _beleg_modul()
    except Exception as e:                                        # noqa: BLE001
        return {"modus": "abgelehnt", "grund": "freigabebeleg nicht ladbar: %s" % e}

    if richtung not in ("buy", "sell"):
        raise ValueError('richtung muss "buy" oder "sell" sein.')
    if art not in ("limit", "market"):
        raise ValueError('art muss "limit" oder "market" sein.')
    if art == "limit" and not preis:
        raise ValueError("Bei art='limit' ist preis erforderlich.")

    try:
        volumen = float(menge)
        kurs = float(preis) if preis else None
    except ValueError:
        return {"modus": "abgelehnt",
                "grund": "menge/preis sind keine Zahlen - Absage"}

    ok, grund = module.pruefe(beleg, spur, richtung, paar, volumen, kurs)
    if not ok:
        return {"modus": "abgelehnt", "grund": grund, "spur": spur}

    parameter = {
        "pair": paar,
        "type": richtung,
        "ordertype": art,
        "volume": str(menge),
        "price": preis if art == "limit" else None,
    }
    if not echt_ausfuehren:
        parameter["validate"] = "true"

    ergebnis = _privat("AddOrder", **parameter)
    kennungen = ergebnis.get("txid", []) or []
    satz = {
        "spur": spur, "beleg": beleg, "paar": paar, "richtung": richtung,
        "menge": menge, "art": art, "preis": preis,
        "echt": bool(echt_ausfuehren), "order_kennungen": kennungen,
        "beschreibung": ergebnis.get("descr", {}).get("order"),
    }
    if echt_ausfuehren:
        # Erst verbrauchen, dann protokollieren: der Beleg ist EINMALIG, auch
        # wenn das Protokoll nicht geschrieben werden kann (die Bindung zaehlt,
        # nicht die Akte).
        module.verbrauche(spur, beleg, ergebnis=" ".join(kennungen) or "ohne Kennung")
    module.protokolliere(spur, satz)
    return {
        "modus": "wirklich aufgegeben (Beleg verbraucht)" if echt_ausfuehren
                 else "nur geprueft, nichts platziert (Beleg unberuehrt)",
        "beschreibung": satz["beschreibung"],
        "order_kennungen": kennungen,
        "spur": spur,
    }


@mcp.tool()
def kraken_order_stornieren(kennung: str) -> dict:
    """Storniert EINE offene Order. Nimmt Risiko heraus und bewegt kein Geld.

    Kuerzt nur Risiko: eine einzelne Order zu stornieren ist erlaubt, auch aus
    einer Sitzung. "all" ist es nicht - ein Sammelstorno kann den Schutz-Stop
    einer offenen Position mitnehmen und eine nackte Position hinterlassen.
    Sammelstorno deshalb nur von Hand ueber das Kraken-Portal.

    Args:
        kennung: Order-ID aus `kraken_offene_orders`. "all" wird abgelehnt.
    """
    if kennung.lower() == "all":
        return {"storniert": 0, "abgelehnt": "Sammelstorno ist gesperrt - er "
                "kann den Schutz-Stop einer offenen Position mitnehmen. "
                "Einzelkennungen stornieren oder im Kraken-Portal."}
    ergebnis = _privat("CancelOrder", txid=kennung)
    return {"storniert": ergebnis.get("count", 0), "ausstehend": ergebnis.get("pending")}


if __name__ == "__main__":
    mcp.run()
