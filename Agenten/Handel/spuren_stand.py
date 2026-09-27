#!/usr/bin/env python3
"""Stand aller Handelsspuren: erlaubt, Fenster, Live-Pfad, Buch, Zyklus.

WARUM: "welche Spur ist live, welche duerfte, und woran haengt sie?" war bisher
aus vier Dateien zusammenzusuchen (dauerlauf.SPUREN, wachen.json je Spur,
freigabe_fenster.json, dauerlauf.log). Hier steht es in einer Tabelle, rein
LESEND - das Werkzeug oeffnet kein Fenster, setzt nichts und handelt nicht.

SPALTEN
  erlaubt   handel_erlaubt aus der wachen.json (der Schalter der Spur)
  hs        herzschlag_max_minuten (Ausfalltoleranz; Hausregel 180 seit 19.09.2026)
  fenster   offen bis ... / zu / - (keine Sitzung; aus freigabe_fenster.json)
  frei      freigabe.erfuellt (der von Hand gesetzte Endhaken)
  Order     Dateien des Ordners, die eine Orderfunktion AUFRUFEN = Live-Pfad.
            Testdateien (demo_order_test.py) zaehlen nicht - sie pruefen nur die
            Anbindung. Die Art steht daneben: haus (eigene Orderanbindung der
            Spur) oder fremd (Fremd-Laufzeit ordert, z.B. der Nautilus-DEMO-Node)
  Auto      gehoert zu dauerlauf.AUTO_FREIGABE (oeffnet sein Fenster selbst)
  Buch      offene Positionen im zustand*.json
  Zyklus    Alter der letzten Zeile in dauerlauf.log (min)

Aufruf (aus dem Handel-Ordner):
    python spuren_stand.py
    python spuren_stand.py --json
    python spuren_stand.py --nur live        # nur Spuren mit Orderweg im Code
    python spuren_stand.py --nur scharf      # Orderweg UND handel_erlaubt=true
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent

# Wortlaute, an denen ein Live-Pfad erkennbar ist: die NAMEN der Orderfunktionen,
# nicht die Namen fremder Bibliotheken. Bis 21.09.2026 stand hier eine Liste
# (order_aufgeben, place_order, submit_order, ...), die im Baum fast nichts traf -
# die Haus-Module heissen okxf.order_limit, okx.markt_kauf, kraken.markt_verkauf,
# mosaic.kraken_spot.algo_stop_setzen. Getroffen wurden damit nur die
# Nautilus-TESTDATEIEN (demo_order_test.py, kraken_order_test.py): die Spalte
# "Order-Code" war also genau verkehrt herum - sie zeigte Tests statt Orderwege
# und verschwieg xperp/scanner/swap/kraken/mosaic/moondev_marktlage.
ORDER_MUSTER = ("markt_kauf", "markt_verkauf", "markt_schliessen",
                "order_limit", "order_aufgeben", "order_senden",
                "algo_stop_setzen", "stop_setzen", "_add_order",
                "kauf_ausfuehren", "verkauf_ausfuehren",
                "place_order", "submit_order", "create_order", "new_order")

# Welche dieser Namen sind HAUS-Funktionen (eigene Orderanbindung der Spur) und
# welche sind Methoden einer fremden Bibliothek. Das entscheidet, ob die Spur
# selbst an die Boerse schreibt oder eine Fremd-Laufzeit (Nautilus-Node) fuer
# sich ordern laesst - der Unterschied zwischen echtem Geldpfad und DEMO-Node.
HAUS_ORDERS = ("markt_kauf", "markt_verkauf", "markt_schliessen", "order_limit",
               "order_aufgeben", "order_senden", "algo_stop_setzen",
               "stop_setzen", "_add_order")
FREMD_ORDERS = ("place_order", "submit_order", "create_order", "new_order",
                "kauf_ausfuehren", "verkauf_ausfuehren")


def spurenliste():
    """Spuren aus dauerlauf.SPUREN - gelesen, nicht geraten."""
    t = (HIER / "dauerlauf.py").read_text(encoding="utf-8")
    i = t.index("SPUREN = {")
    block = t[i:i + 20000]
    namen, tiefe, ende = [], 0, None
    for nr, zeile in enumerate(block.splitlines()):
        if nr == 0:
            tiefe = 1
            continue
        tiefe += zeile.count("{") - zeile.count("}")
        if tiefe <= 0:
            ende = nr
            break
        m = re.match(r'\s{4}"([A-Za-z0-9_]+)":\s*\{', zeile)
        if m:
            namen.append(m.group(1))
    m = re.search(r"AUTO_FREIGABE\s*=\s*\(([^)]*)\)", t)
    auto = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    return namen, auto


def orderweg(ordner: Path, nur_dateien: bool = True):
    """Dateien des Spurordners, die eine Orderfunktion aufrufen oder definieren.

    Das ist die EINE Erkennung eines Live-Pfads (spuren_stand.py und
    befehle.live() benutzen sie) - bewusst nicht als zweite Liste gepflegt.

    Testdateien zaehlen NICHT: `demo_order_test.py` und `kraken_order_test.py`
    rufen submit_order, um die Anbindung zu PRUEFEN. Wer sie mitzaehlt, haelt
    Nautilus fuer eine Live-Spur und uebersieht, dass die Spur selbst nur Papier
    bucht. Ausgeschlossen sind deshalb `test_*.py` und alles unter `tests/`.
    """
    treffer, arten = [], set()
    # spur_buch-Nutzer: Die Orderfunktionen liegen im GEMEINSAMEN Kern
    # (spur_buch.py -> orderweg() -> mosaic/okx_spot oder kraken_spot), nicht im
    # Spurordner. Eine Spur, die spur_buch importiert UND eine `boerse` in der
    # wachen.json traegt, hat einen echten Live-Pfad - auch wenn im Ordner keine
    # Orderfunktion steht. Ohne diese Erkennung meldet spuren_stand.py solche
    # Spuren faelschlich als "keiner" (moondev_listingarb/-topmovers, 27.09.).
    wachen = ordner / "wachen.json"
    if wachen.is_file():
        try:
            w = json.loads(wachen.read_text(encoding="utf-8"))
            if w.get("boerse") and any(
                ("import spur_buch" in f.read_text(encoding="utf-8", errors="ignore")
                 or "spur_buch.py" in f.read_text(encoding="utf-8", errors="ignore"))
                for f in ordner.glob("handeln.py")
            ):
                treffer.append("spur_buch")
                arten.add("haus")
        except Exception:
            pass
    for f in sorted(ordner.rglob("*.py")):
        p = str(f).replace("\\", "/")
        if "test" in f.name or "/tests/" in p or "/.venv/" in p:
            continue
        txt = f.read_text(encoding="utf-8", errors="ignore")
        gefunden = [m for m in ORDER_MUSTER
                    if re.search(r"\b%s\s*\(" % m, txt)]
        if not gefunden:
            continue
        treffer.append(f.name)
        arten.add("haus" if any(m in HAUS_ORDERS for m in gefunden)
                  else "fremd")
    return treffer, ("haus" if "haus" in arten else "fremd" if arten else None)


def fensterlage(name, fenster):
    e = fenster.get(name) or {}
    bis = e.get("offen_bis")
    if not bis:
        return "-"
    try:
        d = dt.datetime.fromisoformat(bis)
    except ValueError:
        return str(bis)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    jetzt = dt.datetime.now(dt.timezone.utc)
    return ("offen bis %s" % d.astimezone().strftime("%H:%M")) if d > jetzt else "zu"


def buecher(ordner: Path):
    """Offene Positionen ueber alle zustand*.json des Ordners."""
    anzahl = {}
    for f in sorted(ordner.glob("zustand*.json")):
        if ".bak-" in f.name:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            continue
        p = d.get("positionen")
        if isinstance(p, list):
            anzahl[f.name.replace("zustand", "").replace(".json", "") or "haupt"] = len(p)
        elif isinstance(d.get("position"), dict):
            anzahl[f.name.replace("zustand", "").replace(".json", "") or "haupt"] = 1
    return anzahl


def zyklusalter(name, zeilen):
    for z in reversed(zeilen):
        if re.search(r"\b%s\b" % re.escape(name), z):
            m = re.match(r"(\d{2}\.\d{2}\.)\s+(\d{2}:\d{2}):(\d{2})", z.strip())
            if not m:
                continue
            heute = dt.datetime.now()
            uhr = "%s:%s" % (m.group(2), m.group(3))
            for tag in (heute, heute - dt.timedelta(days=1)):
                try:
                    kandidat = dt.datetime.strptime("%s %s" % (tag.strftime("%Y-%m-%d"), uhr),
                                                    "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    continue
                if kandidat <= heute:
                    return int((heute - kandidat).total_seconds() // 60)
    return None


def sammle(nur=None):
    spuren, auto = spurenliste()
    fp = HIER / "freigabe_fenster.json"
    fenster = json.loads(fp.read_text(encoding="utf-8")) if fp.is_file() else {}
    log = (HIER / "dauerlauf.log")
    zeilen = log.read_text(encoding="utf-8", errors="ignore").splitlines()[-400:] if log.is_file() else []

    raus = []
    for s in spuren:
        ordner = HIER / s
        w = ordner / "wachen.json"
        e = {"spur": s, "erlaubt": None, "hs": None, "fenster": fensterlage(s, fenster),
             "frei": None, "order": [], "auto": s in auto, "buch": {}, "alter": zyklusalter(s, zeilen)}
        if w.is_file():
            try:
                d = json.loads(w.read_text(encoding="utf-8"))
                e["erlaubt"] = d.get("handel_erlaubt")
                e["hs"] = d.get("herzschlag_max_minuten")
                e["frei"] = (d.get("freigabe") or {}).get("erfuellt")
            except Exception as ex:                                # noqa: BLE001
                e["fehler"] = str(ex)[:80]
        e["order"], e["art"] = orderweg(ordner)
        e["buch"] = buecher(ordner)
        e["scharf"] = bool(e["order"]) and e["erlaubt"] is True
        if nur == "live" and not e["order"]:
            continue
        if nur == "scharf" and not e["scharf"]:
            continue
        raus.append(e)
    return raus


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--json", action="store_true")
    p.add_argument("--nur", choices=["live", "scharf"],
                   help="live = Orderweg im Code; scharf = Orderweg UND handel_erlaubt")
    a = p.parse_args()
    daten = sammle(a.nur)
    if a.json:
        print(json.dumps(daten, indent=1, ensure_ascii=False, default=str))
        return 0
    print("%-17s %-7s %-4s %-16s %-6s %-20s %-5s %s" % (
        "Spur", "erlaubt", "hs", "Fenster", "frei", "Order-Code", "Alter", "Buch"))
    for e in daten:
        buch = ",".join("%s=%d" % kv for kv in e["buch"].items()) or "-"
        print("%-17s %-7s %-4s %-16s %-6s %-20s %-5s %s" % (
            e["spur"], str(e["erlaubt"]), str(e["hs"]), e["fenster"], str(e["frei"]),
            ",".join(e["order"])[:20] or "keiner",
            ("%s min" % e["alter"]) if e["alter"] is not None else "-", buch))
    mit = [e for e in daten if e["order"]]
    print("\n%d von %d Spuren haben einen Live-Pfad im Code: %s" % (
        len(mit), len(daten), ", ".join(e["spur"] for e in mit)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
