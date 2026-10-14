"""omnitrade2-Statusdateien lesen - rein lesend, wirft nie.

WARUM DIESE DATEI EXISTIERT
---------------------------
`Werkstatt/omnitrade2` (Rust, Phase 5 egui UI) ist ein Fork von `Womnitrade`.
Sein CLI kennt aktuell nur `backtest` und `validate` - es schreibt KEINE
Statusdatei. Diese Spur ist trotzdem verdrahtet: sie liest den definierten
Statuspfad `Werkstatt/omnitrade2/status/live.json` und meldet sauber
"keine Statusdatei", solange der Rust-Klon keinen Live-Modus bekommt.

Der Statuspfad ist analog zum bestehenden omnitrade-Fork definiert:
- Umgebungsvariable `OMNITRADE2_STATUS_ORDNER` verschiebt den Ordner
- Standard: `Werkstatt/omnitrade2/status/live.json` (relativ zu BrainFiles)

Dieselbe Brücke wie omnitrade: `omnitrade_bridge.py` (Schema 1) und
`omnitrade_lauf.py` (PID + Status). Beide liegen auf Handel-Ebene und werden
von beiden Spuren geteilt.

Aufruf:  python lesen.py            -> Lage aller Laeufe als JSON
"""

import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import importlib.util  # noqa: E402

# Die Bruecke ueber den PFAD laden, nicht ueber sys.path: `Handel/` traegt
# gleichnamige Module (omnitrade_bridge liegt dort), und ein sys.path-Eintrag
# kann sie verdecken.
_b_spec = importlib.util.spec_from_file_location(
    "omnitrade_bridge", os.path.join(HANDEL, "omnitrade_bridge.py"))
bruecke = importlib.util.module_from_spec(_b_spec)
_b_spec.loader.exec_module(bruecke)

# Zweiter Zeuge: die Prozessliste. `state: running` allein ist KEIN Beweis -
# nach einem harten Ende bleibt die Statusdatei mit einer TOTEN PID auf
# "running" stehen. Die Entscheidung steht in `omnitrade_lauf` (zwei Zeugen,
# Altersgrenze aus dem Kerzenabstand) - hier wird sie nur benutzt.
_l_spec = importlib.util.spec_from_file_location(
    "omnitrade_lauf", os.path.join(HANDEL, "omnitrade_lauf.py"))
lauf_modul = importlib.util.module_from_spec(_l_spec)
_l_spec.loader.exec_module(lauf_modul)

# Test-Seam: None -> echte Prozessabfrage (tasklist). Tests setzen ein Lambda.
lebt_override = None


def _lebt(pid):
    if lebt_override is not None:
        return bool(lebt_override(pid))
    # Mit Programmnamen: Windows vergibt PIDs neu, eine reine Existenzpruefung
    # haelt einen toten Lauf fuer lebend.
    return lauf_modul.pid_lebt(pid, "omnitrade-cli.exe")


# Statusordner: Umgebungsvariable gewinnt, sonst der Klon in der Werkstatt.
# Kein absoluter Pfad im Code - die Wurzel ist zwei Ebenen ueber Handel/.
# WICHTIG: omnitrade2 schreibt aktuell KEINE Statusdatei. Der Ordner ist
# DEFINIERT, aber die Datei existiert nicht. Die Spur meldet dann
# "keine Statusdatei" und tut nichts - sie erfindet keine Position.
STANDARD_ORDNER = os.path.normpath(os.path.join(
    HANDEL, "..", "..", "Werkstatt", "omnitrade2", "status"))

# Quote-Schluessel, an denen ein omnitrade2-Symbol zerlegt wird.
QUOTEN = ("USDC", "USDT", "EUR", "USD")

# Fertige Zuordnungen fuer die Laeufe. Der generische Weg unten deckt alles
# Uebrige ab - diese Tabelle ist die Abkuerzung fuer die bekannten Namen.
SYMBOLE = {
    "BTCUSDC": "BTC-USDC",
    "ETHUSDC": "ETH-USDC",
    "SOLUSDC": "SOL-USDC",
    "BTCUSDT": "BTC-USDT",
    "ETHUSDT": "ETH-USDT",
    "SOLUSDT": "SOL-USDT",
}


def ordner():
    """Der Statusordner: OMNITRADE2_STATUS_ORDNER, sonst der Standard."""
    return os.path.normpath(
        os.environ.get("OMNITRADE2_STATUS_ORDNER") or STANDARD_ORDNER)


def dateien(pfad=None):
    """Alle Statusdateien, aelteste zuerst. Eine einzelne Datei (OMNITRADE2_STATUS)
    geht genauso. Nie werfen: ein fehlender Ordner ergibt eine leere Liste."""
    pfad = pfad or os.environ.get("OMNITRADE2_STATUS") or ordner()
    if os.path.isfile(pfad):
        return [pfad]
    try:
        namen = sorted(os.listdir(pfad))
    except OSError:
        return []
    aus = []
    for n in namen:
        if n.startswith("live") and n.endswith(".json"):
            aus.append(os.path.join(pfad, n))
    return aus


def zerlege_symbol(symbol):
    """'BTCUSDC' -> ('BTC', 'USDC'). None, wenn keine Quote erkennbar ist."""
    s = str(symbol or "").strip().upper()
    for q in QUOTEN:
        if s.endswith(q) and len(s) > len(q):
            return s[:-len(q)], q
    return None


def instrument(symbol):
    """omnitrade2-Symbol in Haus-Schreibweise ('BTCUSDC' -> 'BTC-USDC').

    Unbekannt = None. Der Aufrufer meldet das als Fehler; ein geratener Name
    wuerde die Order in einen anderen Markt schicken.
    """
    s = str(symbol or "").strip().upper()
    if s in SYMBOLE:
        return SYMBOLE[s]
    teile = zerlege_symbol(s)
    if not teile:
        return None
    return "%s-%s" % teile


def letzter_verkauf(lage):
    """Preis der juengsten gefuellten/platzierten sell-Order, sonst None.

    WARUM DAS GEBRAUCHT WIRD: der Ausstieg des Rust-Laufs ist eine echte Order
    mit echtem Preis. Wer stattessen `last_close` als Verkaufskurs bucht,
    schreibt einen Kurs ins Journal, den es nie gab.
    """
    orders = lage.get("recent_orders") or []
    if not isinstance(orders, list):
        return None
    kandidaten = []
    for o in orders:
        if not isinstance(o, dict):
            continue
        if str(o.get("side") or "").strip().lower() != "sell":
            continue
        if str(o.get("outcome") or "").strip().lower() not in ("filled", "placed"):
            continue
        try:
            kandidaten.append((float(o.get("time_ms") or 0), float(o.get("price"))))
        except (TypeError, ValueError):
            continue
    if not kandidaten:
        return None
    kandidaten.sort()
    preis = kandidaten[-1][1]
    return preis if preis > 0 else None


def lauf(datei, jetzt_ms=None, prozess_pruefen=True):
    """Eine Statusdatei als schmales Dict. Nie werfen.

    Felder: ok, fehler, datei, symbol, inst, state, netto, offen, kurs, signal,
    alter_s, laeuft, pid, orders_placed, orders_rejected, last_error, script.

    `laeuft` ist das Urteil aus ZWEI Zeugen (Statusdatei UND lebende PID). Nur
    ein Lauf mit `laeuft=True` darf gespiegelt werden.
    """
    lage = bruecke.lage(datei=datei, jetzt_ms=jetzt_ms)
    aus = {
        "ok": False, "fehler": lage.get("fehler") or "", "datei": datei,
        "symbol": lage.get("symbol"), "inst": None, "state": lage.get("state"),
        "netto": 0.0, "offen": False, "kurs": None, "signal": lage.get("last_signal"),
        "alter_s": lage.get("alter_s"), "pid": lage.get("pid"), "laeuft": False,
        "orders_placed": lage.get("orders_placed"),
        "orders_rejected": lage.get("orders_rejected"),
        "last_error": lage.get("last_error") or "", "script": lage.get("script"),
    }
    if not lage.get("ok"):
        return aus
    aus["inst"] = instrument(aus["symbol"])
    if not aus["inst"]:
        aus["fehler"] = "Symbol %r nicht zerlegbar" % aus["symbol"]
        return aus
    try:
        aus["netto"] = float(lage.get("net_quantity") or 0.0)
    except (TypeError, ValueError):
        aus["fehler"] = "net_quantity unlesbar"
        return aus
    aus["offen"] = aus["netto"] > 0
    kurs = lage.get("last_close")
    try:
        aus["kurs"] = float(kurs) if kurs is not None else None
    except (TypeError, ValueError):
        aus["kurs"] = None
    if prozess_pruefen:
        urteil = lauf_modul.beurteile(lage, lebt=_lebt)
        aus["laeuft"] = urteil["laeuft"]
        if not urteil["laeuft"]:
            aus["fehler"] = urteil["grund"]
    else:
        aus["laeuft"] = lage.get("state") == "running"
    aus["verkauf"] = letzter_verkauf(lage)
    aus["ok"] = True
    return aus


def lage(pfad=None, jetzt_ms=None, prozess_pruefen=True):
    """Alle Laeufe: (liste_der_laeufe, fehler). Fehler sind Textzeilen."""
    aus, fehler = [], []
    for d in dateien(pfad):
        e = lauf(d, jetzt_ms=jetzt_ms, prozess_pruefen=prozess_pruefen)
        if e["ok"]:
            aus.append(e)
        else:
            fehler.append("%s: %s" % (os.path.basename(d), e["fehler"]))
    return aus, fehler


def main():
    laeufe, fehler = lage()
    json.dump({"ordner": ordner(), "laeufe": laeufe, "fehler": fehler},
              sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
