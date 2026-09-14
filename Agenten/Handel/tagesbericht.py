"""Ein Bild aller Spuren - fuer das Handy, einmal am Tag.

Angelegt am 03.09.2026 auf Max' Anweisung ("taegliche Meldung mit Updates auf
mein Handy"). Liest nur; loest nichts aus, aendert keine Datei.

Der Bericht beantwortet drei Fragen in dieser Reihenfolge, weil sie am
Handy-Display in dieser Reihenfolge zaehlen:

  1. Was ist offen, und wie steht es?   - Positionen gegen den aktuellen Kurs
  2. Was hindert Live gerade?           - die Sperren, im Klartext
  3. Was waere heute dran?              - die Spitze der Rangliste

Robust gegen Ausfaelle: Jede Spur wird einzeln eingesammelt. Faellt eine aus
(kein Netz, kaputte Datei), steht das im Bericht und die anderen kommen
trotzdem. Ein Melder, der bei der ersten Stoerung schweigt, meldet genau dann
nichts, wenn es darauf ankommt.

Aufruf:
    python tagesbericht.py            # Bericht auf die Konsole
    python tagesbericht.py --senden   # zusaetzlich per Telegram
"""

import argparse
import datetime as dt
import json
import os
import sys
import traceback

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "scanner"))
# Die Module der Spur 2 (okxf, wachen_xperp). Sie werden hier auch fuer die
# SWAP-Spur gebraucht, deren eigener Ordner weder das eine noch das andere
# enthaelt. Ueber __file__ bestimmt und nicht ueber HIER: HIER zeigen die Tests
# auf einen Datenordner, die Module liegen trotzdem hier.
XPERP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xperp")

import melder                                            # noqa: E402
import spiegelstand                                     # noqa: E402


def _lies(pfad, vorgabe=None):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return vorgabe


def _prozent(jetzt, einstieg):
    return (jetzt / einstieg - 1) * 100 if einstieg else 0.0


# --- Die einzelnen Spuren ---------------------------------------------------

def spur_scanner():
    """Spur 1 - OKX Spot, USD."""
    ordner = os.path.join(HIER, "scanner")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    pos = z.get("positionen", [])

    kurse = {}
    try:
        sys.path.insert(0, ordner)
        import okx                                       # noqa: PLC0415
        for p in pos:
            try:
                kurse[p["inst"]] = float(okx.letzter_kurs(p["inst"]))
            except Exception:                            # noqa: BLE001
                pass
    except Exception:                                    # noqa: BLE001
        pass

    zeilen = []
    for p in pos:
        k = kurse.get(p["inst"])
        v = _prozent(k, p["einstieg"]) if k else None
        zeilen.append({
            "name": p["inst"], "einstieg": p["einstieg"], "kurs": k,
            "wert": p.get("usd", 0), "vh": v,
            "stop": p.get("stop"), "seit": p.get("eroeffnet"),
        })
    return {
        "name": "Spur 1  OKX Spot", "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "journal": os.path.join(ordner, "handelsjournal.csv"),
    }


def spur_kraken():
    """Spur 3 - Kraken Spot, EUR."""
    ordner = os.path.join(HIER, "kraken")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    pos = z.get("positionen", [])

    kurse = {}
    try:
        sys.path.insert(0, ordner)
        import kraken                                    # noqa: PLC0415
        for p in pos:
            try:
                kurse[p["paar"]] = float(kraken.letzter_kurs(p["paar"]))
            except Exception:                            # noqa: BLE001
                pass
    except Exception:                                    # noqa: BLE001
        pass

    zeilen = []
    for p in pos:
        k = kurse.get(p["paar"])
        zeilen.append({
            "name": p["paar"], "einstieg": p["einstieg"], "kurs": k,
            "wert": p.get("eur", 0), "vh": _prozent(k, p["einstieg"]) if k else None,
            "stop": p.get("stop"), "seit": p.get("eroeffnet"),
        })
    return {
        "name": "Spur 3  Kraken", "waehrung": "EUR", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": "wachen_kraken",
        "journal": os.path.join(ordner, "handelsjournal.csv"),
    }


def spur_swap():
    """SWAP-Spur - USD.

    Sie steht im Bericht wie jede andere Spur. Ob live etwas moeglich ist,
    entscheidet der Bericht nicht selbst: Er zeigt die Sperren, die die Spur
    fuehrt (handel_erlaubt, Freigabe, Journal-Zweitziel). Seit dem 12.09.2026
    hat diese Spur einen Live-Pfad nach xperp-Muster - ein festes "ist Papier"
    waere hier also die zweite Wahrheit, die als erste alt wird.

    Sonst dieselbe Rechnung wie bei Spur 2: Prozent auf die Margin, Betrag in
    USD, Hebel neben der Zahl. Eine zweite Formel waere der Anfang zweier
    Zahlenreihen, die sich nicht mehr vergleichen lassen.
    """
    ordner = os.path.join(HIER, "swap")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    pos = z.get("positionen", [])

    kurse = {}
    if pos:
        try:
            sys.path.insert(0, XPERP)
            sys.path.insert(0, ordner)
            import okxf                                   # noqa: PLC0415
            for p in pos:
                try:
                    kurse[p["inst"]] = float(okxf.letzter_kurs(p["inst"]))
                except Exception:                        # noqa: BLE001
                    pass
        except Exception:                                # noqa: BLE001
            pass

    zeilen = []
    for p in pos:
        k = kurse.get(p["inst"])
        vz = 1 if p["seite"] == "long" else -1
        bewegung = (vz * (k / p["einstieg"] - 1) * 100) if k else None
        zeilen.append({
            "name": "%s %s" % (p["basis"], p["seite"]),
            "einstieg": p["einstieg"], "kurs": k,
            "wert": p.get("margin", 0),
            "vh": bewegung * p.get("hebel", 1) if bewegung is not None else None,
            "stop": p.get("stop"), "seit": p.get("eroeffnet"),
            "hebel": p.get("hebel"), "familie": p.get("familie"),
            # seite traegt zeile_position - ohne sie rechnet der
            # Stop-Abstand jede Short wie einen Long (Fehlalarm "Stop
            # gerissen" an der Swap-XAU-Short, Befund 14.09.2026).
            "seite": p["seite"],
        })
    return {
        "name": "SWAP (%s)" % ("Papier" if (z.get("modus") or "papier") == "papier"
                               else z["modus"]),
        "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": "wachen_xperp",
        "journal": os.path.join(ordner, "handelsjournal.csv"),
    }


def spur_orbk():
    """ORB auf Kraken - Papierspur, USD.

    Kraken-Duplikation der ORB-Spur. Sie fuehrt hoechstens EINE Position:
    zustand.json hat 'position' (Einzelwert oder null), nicht 'positionen'
    wie die Kontraktspuren. Die Spur ist Papier - handel_erlaubt=false,
    kein Live-Zweig. Ein Backtest-Urteil steht noch aus, weil die
    oeffentliche Kraken-API nur rund 720 Kerzen je Intervall liefert.
    """
    ordner = os.path.join(HIER, "orbk")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    p = z.get("position")
    pos = [p] if p else []

    kurse = {}
    if pos:
        try:
            sys.path.insert(0, os.path.join(HIER, "kraken"))
            import kraken                                    # noqa: PLC0415
            for x in pos:
                konf = (w.get("instrumente") or {}).get(x.get("inst"), {})
                paar = konf.get("kraken")
                if paar:
                    try:
                        kurse[x["inst"]] = float(kraken.letzter_kurs(paar))
                    except Exception:                    # noqa: BLE001
                        pass
        except Exception:                                # noqa: BLE001
            pass

    zeilen = []
    for x in pos:
        k = kurse.get(x.get("inst"))
        vz = 1 if x.get("richtung") == "long" else -1
        if k and x.get("einstieg"):
            bewegung = vz * (k / x["einstieg"] - 1) * 100
        else:
            bewegung = None
        zeilen.append({
            "name": "%s %s" % (x.get("inst", "?"), x.get("richtung", "?")),
            "einstieg": x.get("einstieg"), "kurs": k,
            "wert": 0, "vh": bewegung,
            "stop": x.get("stop"), "seit": x.get("tag"),
        })
    return {
        "name": "ORB-Kraken (Papier)",
        "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": "wachen_orb",
        "journal": os.path.join(ordner, "handelsjournal.csv"),
    }

def spur_spiegel():
    """Spiegel-Spur - Papierbuch fuer Copy-Trading, USD je Kopie.

    Sie hat kein Pruefmodul und keine fuenf Bedingungen: ihr Ergebnis ist eine
    Bilanz, keine Wache. Der Betrag je Kopie ist der Einsatz (was gebunden
    waere), der Prozentwert das Ergebnis nach Slippage und Gebuehr - gerechnet
    mit derselben Formel wie das Buch selbst, damit der Bericht nicht
    schoenrechnet, was die Spur richtig rechnet.
    """
    ordner = os.path.join(HIER, "spiegel")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    pos = z.get("positionen", [])

    kurse, buch = {}, None
    if pos:
        try:
            sys.path.insert(0, ordner)
            import spiegel as buch                        # noqa: PLC0415
            kurse = buch.lesen.preise([(p["kette"], p["token"]) for p in pos])
        except Exception:                                # noqa: BLE001
            kurse, buch = {}, None

    zeilen = []
    for p in pos:
        kurs = kurse.get((p["kette"], p["token"]))
        wert = None
        if kurs and buch:
            try:
                wert = buch._verkaeuflich(p["menge"], kurs, w)
            except Exception:                            # noqa: BLE001
                wert = None
        zeilen.append({
            "name": "%s %s" % (p.get("symbol", "?"), p.get("kette", "")),
            "einstieg": p.get("preis_vorbild"), "kurs": kurs,
            "wert": p.get("einsatz_usd", 0),
            "vh": ((wert / p["einsatz_usd"] - 1) * 100
                   if wert and p.get("einsatz_usd") else None),
            "stop": p.get("stop_preis"), "seit": p.get("eroeffnet"),
            "familie": p.get("risiko"),
        })
    return {
        "name": "Spiegel (Papier, Copy)", "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        # Kein Pruefmodul: die anderen Spuren wachen ueber fuenf Bedingungen,
        # diese fuehrt ein Buch. Ohne diesen Eintrag wuerde der Bericht eine
        # fremde Wachenrechnung auf sie anwenden und "Wachen nicht lesbar"
        # schreiben.
        "pruefmodul": None,
        "papierfest": True,
        "journal": os.path.join(ordner, "handelsjournal.csv"),
        "bilanz": _bilanz("spiegel"),
    }


def spur_kopier():
    """Kopier-Spur - Papierbuch fuer Copy-Trading der Pump.fun-Rangliste,
    USD je Kopie.

    Wie die Spiegel-Spur: ein Buch statt fuenf Bedingungen, papierfest.
    Der Betrag je Kopie ist der Einsatz, der Prozentwert das Ergebnis nach
    Slippage und Gebuehr - gerechnet mit derselben Formel wie das Buch.
    """
    ordner = os.path.join(HIER, "kopier")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    pos = z.get("positionen", [])

    kurse, buch = {}, None
    if pos:
        try:
            sys.path.insert(0, ordner)
            import kopier as buch                        # noqa: PLC0415
            kurse = buch.lesen.preise([(p["kette"], p["token"]) for p in pos])
        except Exception:                                # noqa: BLE001
            kurse, buch = {}, None

    zeilen = []
    for p in pos:
        kurs = kurse.get((p["kette"], p["token"]))
        wert = None
        if kurs and buch:
            try:
                wert = buch._verkaeuflich(p["menge"], kurs, w)
            except Exception:                            # noqa: BLE001
                wert = None
        zeilen.append({
            "name": "%s %s" % (p.get("symbol", "?"), p.get("kette", "")),
            "einstieg": p.get("preis_vorbild"), "kurs": kurs,
            "wert": p.get("einsatz_usd", 0),
            "vh": ((wert / p["einsatz_usd"] - 1) * 100
                   if wert and p.get("einsatz_usd") else None),
            "stop": p.get("stop_preis"), "seit": p.get("eroeffnet"),
            "familie": p.get("risiko"),
        })
    return {
        "name": "Kopier (Papier, Pump.fun)", "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": None,
        "papierfest": True,
        "journal": os.path.join(ordner, "handelsjournal.csv"),
        "bilanz": _bilanz("kopier"),
    }


def _bilanz(spur):
    """Die Bilanzzeile einer Buch-Spur - rein lesend, aus EINER Quelle.

    Sie kommt aus <spur>/auswertung.py: derselbe Aufruf, den eine GUI zeigt.
    Eine zweite Formel fuer dieselbe Frage waere eine zweite Wahrheit.
    Faellt das Modul aus, steht der Grund da und nicht gar nichts.

    Geladen wird ueber den DATEIPFAD, nicht ueber den Modulnamen: mehrere
    Spuren haben ein auswertung.py, und sys.modules gaebe beim zweiten
    Import das erste zurueck - die Spiegel-Zeile traege dann die Zahlen von
    Omniquant.
    """
    ordner = os.path.join(HIER, spur)
    # Ein Bericht LIEST. Python legt beim Laden eines Moduls aus einer Datei
    # einen Bytecode-Cache an - im Spurordner, also neben dem Journal. Das
    # schaltet der Import fuer die Dauer des Ladens ab (der Test
    # "bericht_schreibt_nichts" hat genau das aufgedeckt).
    alt = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        import importlib.util                              # noqa: PLC0415
        pfad = os.path.join(ordner, "auswertung.py")
        spec = importlib.util.spec_from_file_location(
            "auswertung_%s" % spur, pfad)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul.kernzeile(os.path.join(ordner, "handelsjournal.csv"))
    except Exception as e:                                 # noqa: BLE001
        return "Auswertung nicht lesbar: %s" % str(e)[:80]
    finally:
        sys.dont_write_bytecode = alt


def spur_omniquant():
    """Omniquant-Spur - Papierbuch auf dem Prognose-Bericht, USD.

    Sie hat kein Pruefmodul und keine fuenf Bedingungen (wie die
    Spiegel-Spur): ihr Ergebnis ist ein Buch, keine Wache. Der Betrag je
    Position ist der Einsatz (nominal), der Prozentwert die Bewegung am
    Kurs - ohne Hebel, Spot-Paare aus dem Prognose-Bericht. papierfest=True,
    damit der Bericht "kein Live-Zweig" sagt statt "GESPERRT - wartet auf
    /ja".
    """
    ordner = os.path.join(HIER, "omniquant")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    pos = z.get("positionen", [])

    kurse = {}
    if pos:
        try:
            sys.path.insert(0, os.path.join(HIER, "scanner"))
            import okx                                      # noqa: PLC0415
            for p in pos:
                try:
                    kurse[p["inst"]] = float(okx.letzter_kurs(p["inst"]))
                except Exception:                           # noqa: BLE001
                    pass
        except Exception:                                   # noqa: BLE001
            pass

    zeilen = []
    for p in pos:
        k = kurse.get(p["inst"])
        vz = 1 if p["seite"] == "long" else -1
        bewegung = (vz * (k / p["einstieg"] - 1) * 100) if k else None
        zeilen.append({
            "name": "%s %s" % (p["inst"], p["seite"]),
            "einstieg": p["einstieg"], "kurs": k,
            "wert": p.get("nominal", 0),
            "vh": bewegung,
            "stop": p.get("stop"), "seit": p.get("eroeffnet"),
            "seite": p.get("seite"),
        })
    return {
        "name": "Omniquant (%s)" % (z.get("modus") or "papier"),
        "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": None,
        "papierfest": True,
        "journal": os.path.join(ordner, "handelsjournal.csv"),
        "bilanz": _bilanz("omniquant"),
    }


def spur_gitter():
    """Gitter-Spur - Papierbuch auf einem statischen Preisgitter, USDT.

    Sie hat kein Pruefmodul und keine fuenf Bedingungen (wie spiegel und
    omniquant): ihr Ergebnis ist ein Buch. Gezeigt werden die belegten Stufen
    mit dem Abstand zu ihrem Verkauf - ein Gitter hat keinen Stop, sondern
    eine Stufe hoeher als Ziel. papierfest=True, damit der Bericht "kein
    Live-Zweig" sagt statt "GESPERRT - wartet auf /ja".
    """
    ordner = os.path.join(HIER, "gitter")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    pos = z.get("positionen", []) or []

    kurse = {}
    if pos:
        try:
            sys.path.insert(0, os.path.join(HIER, "scanner"))
            import okx                                      # noqa: PLC0415
            for p in pos:
                try:
                    kurse[p["inst"]] = float(okx.letzter_kurs(p["inst"]))
                except Exception:                           # noqa: BLE001
                    pass
        except Exception:                                   # noqa: BLE001
            pass

    zeilen = []
    for p in pos:
        k = kurse.get(p["inst"])
        einstieg = p.get("einstieg")
        vz = 1 if (p.get("seite") or "long") == "long" else -1
        bewegung = (vz * (k / einstieg - 1) * 100) if (k and einstieg) else None
        zeilen.append({
            "name": "%s St%d" % (p["inst"], p.get("stufe", "?")),
            "einstieg": einstieg, "kurs": k,
            "wert": p.get("nominal", 0),
            "vh": bewegung,
            "stop": None, "ziel": p.get("ziel"),
            "seit": p.get("eroeffnet"), "seite": p.get("seite"),
        })

    return {
        "name": "Gitter (%s)" % (z.get("modus") or "papier"),
        "waehrung": w.get("waehrung", "USDT"), "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": None,
        "papierfest": True,
        "journal": os.path.join(ordner, "handelsjournal.csv"),
        "bilanz": _bilanz("gitter"),
    }


def spur_nautilus():
    """Nautilus-Spur - OKX-DEMO-Node als Papierzyklus, USD.

    Sie hat kein Pruefmodul und keine fuenf Bedingungen (wie die
    Spiegel-Spur): ihr Ergebnis ist ein Herzschlag, keine Wache. papierfest,
    damit der Bericht "kein Live-Zweig" sagt statt "GESPERRT - wartet auf
    /ja". Gezeigt wird die letzte gesammelte Quote statt einer Bilanz.
    """
    ordner = os.path.join(HIER, "nautilus")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}

    q = z.get("letzte_quote") or {}
    if q:
        zeile = "letzte Quote bid=%s ask=%s" % (q.get("bid"), q.get("ask"))
    else:
        zeile = "noch kein Papierzyklus gelaufen"
    if z.get("letzter_lauf"):
        zeile += "  (Herzschlag %s)" % z["letzter_lauf"]

    return {
        "name": "Nautilus (%s)" % (z.get("modus") or "papier"),
        "waehrung": "USD", "w": w, "z": z,
        "positionen": [], "ordner": ordner,
        "pruefmodul": None,
        "papierfest": True,
        "journal": os.path.join(ordner, "handelsjournal.csv"),
        "bilanz": zeile,
    }


def spur_xperp_positionen():
    """Spur 2 - offene Anlaeufe gegen den aktuellen Kurs.

    Seit 03.09.2026 hat diese Spur einen Live-Pfad und damit Positionen. Sie
    rechnet in Margin, nicht in Einsatz: Der Prozentwert bezieht sich auf den
    Positionswert, der Betrag auf den Einschuss - bei 5x Hebel wirkt eine
    Kursbewegung von 1 % also mit 5 % auf die Margin.
    """
    ordner = os.path.join(HIER, "xperp")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    pos = z.get("positionen", [])

    kurse = {}
    if pos:
        try:
            sys.path.insert(0, ordner)
            import okxf                                   # noqa: PLC0415
            for p in pos:
                try:
                    # Rollover-fest: wechselt OKX den XPERP-Kontrakt
                    # (14.09.2026: 51001 bei XAU/BZ), liefert der alte
                    # instId keinen Kurs. Der Fallback loest den lebenden
                    # Kontrakt des Basiswerts auf und nimmt dessen Kurs.
                    _, k = okxf.letzter_kurs_mit_fallback(
                        p["inst"], p.get("basis"))
                    kurse[p["inst"]] = k
                except Exception:                        # noqa: BLE001
                    pass
        except Exception:                                # noqa: BLE001
            pass

    zeilen = []
    for p in pos:
        k = kurse.get(p["inst"])
        vz = 1 if p["seite"] == "long" else -1
        bewegung = (vz * (k / p["einstieg"] - 1) * 100) if k else None
        zeilen.append({
            "name": "%s %s" % (p["basis"], p["seite"]),
            "einstieg": p["einstieg"], "kurs": k,
            "wert": p.get("margin", 0),
            # Auf die Margin gerechnet - das ist die Zahl, die zaehlt.
            "vh": bewegung * p.get("hebel", 1) if bewegung is not None else None,
            "stop": p.get("stop"), "seit": p.get("eroeffnet"),
            "hebel": p.get("hebel"), "familie": p.get("familie"),
            # seite traegt zeile_position: ohne sie rechnet der
            # Stop-Abstand jede Short wie eine Long ("Stop gerissen"-
            # Fehlalarm, Befund 14.09.2026 an der Swap-XAU-Short).
            "seite": p["seite"],
        })
    return {
        "name": "Spur 2  XPERP", "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": "wachen_xperp",
        "journal": os.path.join(ordner, "handelsjournal.csv"),
    }


def spur_xperp(anzahl=3):
    """Spur 2 - die Rangliste dazu."""
    ordner = os.path.join(HIER, "xperp")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    spitzen = {}
    try:
        sys.path.insert(0, ordner)
        import auswahl                                   # noqa: PLC0415
        d = auswahl.sammle(still=True)
        for zweck in ("long", "short", "grid"):
            beste = sorted(d, key=lambda x: -x["punkte"][zweck])[:anzahl]
            spitzen[zweck] = [{
                "basis": b["basis"],
                "kategorie": b.get("kategorie", "krypto"),
                "punkte": b["punkte"][zweck],
                "deckel": auswahl.hebel_deckel(
                    b["mae_short"] if zweck == "short" else b["mae_long"]),
                "vola": b["vola"], "tor": b.get("vola_tor", 1.2),
                "ruhe": b.get("ruhe", 0),
            } for b in beste]
    except Exception as e:                               # noqa: BLE001
        spitzen["fehler"] = str(e)
    return {"name": "Rangliste  XPERP", "w": w, "spitzen": spitzen,
            "ordner": ordner}


# --- Wachen -----------------------------------------------------------------

def wachenlage(spur):
    """Die fuenf Bedingungen einer Spur, oder None wenn nicht ermittelbar.

    Jede Spur bringt ihr eigenes Pruefmodul mit. Spur 3 rechnet dieselbe
    Logik, liest aber ein Journal mit anderen Spalten: 'paar' statt 'inst',
    Betraege in EUR. Wer hier stur wachen_pruefung nimmt, bekommt einen
    KeyError - und beim ersten Bauversuch am 03.09.2026 verschluckte ein
    blankes except ihn, sodass Spur 3 im Bericht einfach ohne Zahlen dastand.
    Deshalb gibt der Fehler jetzt einen Text zurueck, der im Bericht landet.
    """
    modul = spur.get("pruefmodul", "wachen_pruefung")
    try:
        sys.path.insert(0, os.path.join(HIER, "scanner"))
        # wachen_xperp liegt in xperp/ - die SWAP-Spur liest dieselbe Rechnung
        # ueber ihre eigene wachen.json, hat aber einen eigenen Ordner. Ohne
        # diese Zeile faellt der Import aus und der Bericht schreibt "Wachen
        # nicht lesbar", obwohl nur der Pfad fehlte.
        sys.path.insert(0, XPERP)
        sys.path.insert(0, spur["ordner"])
        p = __import__(modul)
        return p.lage(spur["w"], spur["journal"], spur["z"])
    except Exception as e:                               # noqa: BLE001
        return {"fehler": "%s: %s" % (type(e).__name__, e)}


def sperren(spur, lage):
    """Was Live gerade verschliesst - im Klartext, kurz."""
    w, aus = spur["w"], []
    if not w.get("handel_erlaubt"):
        aus.append("handel_erlaubt=false")
    if lage and "fehler" not in lage:
        if not lage["freigabe_erfuellt"]:
            aus.append("Freigabe offen (Bed. 1)")
        if not lage["herzschlag_frisch"]:
            aus.append("Herzschlag alt (Bed. 3)")
        if lage["kill"]:
            aus.append("KILL-SWITCH erreicht")
        if lage["ev_negativ"]:
            aus.append("EV negativ (Bed. 5)")
    if w.get("journal_zweitziel") is None:
        aus.append("Journal-Zweitziel fehlt (Bed. 4)")
    return aus


# --- Text -------------------------------------------------------------------

def zeile_position(p, waehrung):
    if p["kurs"] is None:
        return "  %-12s %s  (kein Kurs)" % (p["name"], p["einstieg"])
    pfeil = "+" if p["vh"] >= 0 else ""
    # Stop-Abstand richtungsbewusst: bei long liegt der Stop unter dem Kurs
    # (kurs/stop - 1 positiv = Luft), bei short ueber dem Kurs (kurs/stop - 1
    # negativ, obwohl der Stop NICHT gerissen ist). Ohne den Richtungsfaktor
    # zeigt der Bericht jede gesunde short-Position als "Stop gerissen" -
    # Befund 13.09.2026 an der ersten omniquant-short-Position.
    vz = 1 if (p.get("seite") or p.get("richtung") or "long") == "long" else -1
    abstand = (vz * (p["kurs"] / p["stop"] - 1) * 100) if p.get("stop") else None
    entfernung = None
    if not p.get("stop") and p.get("ziel"):
        # Eine Buch-Spur ohne Stop (Gitter: verkauft wird eine Stufe hoeher)
        # braucht trotzdem eine Marke am Kurs: ohne sie steht in der Zeile
        # nur die Bewegung und niemand sieht, wie weit der Verkauf entfernt
        # ist. Richtungsbewusst wie der Stop-Abstand.
        ziel = p["ziel"]
        if ziel and p["kurs"]:
            entfernung = vz * (ziel / p["kurs"] - 1) * 100
    text = "  %-12s %s%.1f%%  %.0f %s" % (
        p["name"], pfeil, p["vh"], p["wert"], waehrung)
    if p.get("hebel") and p["hebel"] > 1:
        text += " Margin @%.0fx" % p["hebel"]
    if entfernung is not None:
        text += "  Verkauf in %.1f %%" % abs(entfernung)
    if abstand is not None:
        if abstand < 0:
            # Der Kurs steht jenseits des Stops. Bei den Kontraktspuren
            # schliesst der naechste Lauf, aber solange gilt: nicht als
            # negativen Prozentsatz zeigen - das liest sich wie ein Fehler.
            text += "  Stop gerissen (%.1f%%)" % abs(abstand)
        else:
            # Bei Hebel ist der Stop-Abstand am Kurs gemessen, der Gewinn an
            # der Margin. Ohne den Hebel danebenzuschreiben liest sich
            # "+1,3 % bei 4,1 % Stop" wie viel Luft - tatsaechlich sind es
            # 0,8 % Kurs.
            text += "  Stop %.1f%% (Kurs)" % abs(abstand)
    return text


def spiegelzeile():
    """Eine Zeile zum Stand der Kopie ausser Haus (Bedingung 4).

    Gelesen wird die Kopie selbst (byte-genau) und der Vermerk im Zustand der
    Spur - beides lokal, kein Netz. Ein Fehler darf den Bericht nicht kippen:
    dann steht der Grund in der Zeile statt eines Tracebacks.
    """
    try:
        e = spiegelstand.stand(HIER)
    except Exception as fehler:                          # noqa: BLE001
        return "Journal ausser Haus: nicht geprueft (%s)" % str(fehler)[:80]
    text = spiegelstand.kurz(e)
    if e.get("fehler") or e["abweichend"]:
        return "<b>Journal ausser Haus: %s</b>" % text
    return "Journal ausser Haus: %s" % text


def baue(mit_xperp=True):
    """Der ganze Bericht als Text. Kein Netz noetig fuer den Rahmen."""
    heute = dt.datetime.now()
    t = ["<b>Handel  %s</b>" % heute.strftime("%d.%m.%Y %H:%M")]

    gesamt_offen = 0
    for hole in (spur_xperp_positionen, spur_scanner, spur_kraken, spur_swap,
                 spur_spiegel, spur_orbk, spur_omniquant, spur_nautilus,
                 spur_gitter, spur_kopier):
        try:
            s = hole()
        except Exception as e:                           # noqa: BLE001
            t.append("\n<b>%s</b>\n  AUSFALL: %s" % (hole.__name__, e))
            continue

        # Eine Spur ohne Pruefmodul (die Spiegel-Spur fuehrt ein Buch statt
        # fuenf Bedingungen) wird ohne Wachenblock gezeigt - statt eine fremde
        # Rechnung auf sie anzuwenden und "Wachen nicht lesbar" zu schreiben.
        lage = wachenlage(s) if s.get("pruefmodul", "wachen_pruefung") else None
        still = s["w"].get("stillgelegt")
        t.append("\n<b>%s</b>%s" % (s["name"],
                                    "  — STILLGELEGT" if still else ""))
        if s["positionen"]:
            gesamt_offen += len(s["positionen"])
            summe = sum(p["wert"] for p in s["positionen"])
            mit = [p for p in s["positionen"] if p["vh"] is not None]
            schnitt = sum(p["vh"] for p in mit) / len(mit) if mit else None
            for p in s["positionen"]:
                t.append(zeile_position(p, s["waehrung"]))
            if schnitt is not None:
                t.append("  = %d Positionen, %.0f %s gebunden, im Schnitt %+.1f%%"
                         % (len(s["positionen"]), summe, s["waehrung"], schnitt))
        else:
            t.append("  keine offene Position")

        # Ein Buch ohne Bilanz ist eine halbe Auskunft. Spuren ohne
        # Auswertung tragen das Feld nicht - sie bleiben unveraendert.
        if s.get("bilanz"):
            t.append("  " + s["bilanz"])

        if lage and "fehler" in lage:
            t.append("  Wachen nicht lesbar: %s" % lage["fehler"][:100])
        elif lage:
            # Der Ruecklauf traegt die Waehrung im Namen - _usd bei Spur 1,
            # _eur bei Spur 3. Das ist Absicht (kraken/wachen.json: "Wer hier
            # USD liest, liest falsch") und darf hier nicht geraten werden.
            rueck = lage.get("ruecklauf_%s" % s["waehrung"].lower())
            t.append("  Runden %d (Papier %d), Ruecklauf %.2f %s, Faktor %.2f"
                     % (lage["runden_gesamt"], lage["runden_papier"],
                        rueck if rueck is not None else 0.0, s["waehrung"],
                        lage["groessenfaktor"]))
        if still:
            # Die Positionen stehen noch da - sie sind Papier und wurden
            # nicht fiktiv verkauft, das haette falsche Zahlen ins Journal
            # geschrieben. Sie bleiben sichtbar, damit klar ist, womit die
            # Spur aufgehoert hat.
            t.append("  Kein Lauf mehr, weder Papier noch Live.")
        else:
            auf = sperren(s, lage)
            if s.get("papierfest"):
                # Der starkste Grund zuerst: Es fehlt nicht eine Freigabe, es
                # fehlt der Zweig. Ohne diesen Zusatz liest sich "GESPERRT -
                # handel_erlaubt=false" wie eine Spur, die auf ein /ja wartet.
                auf.insert(0, "kein Live-Zweig (Papierpfad)")
            t.append("  Live: %s" % ("GESPERRT - " + "; ".join(auf) if auf
                                     else "offen"))

    if mit_xperp:
        try:
            x = spur_xperp()
            t.append("\n<b>%s</b>  (legt vor, handelt nicht)" % x["name"])
            if "fehler" in x["spitzen"]:
                t.append("  Rangliste nicht erreichbar: %s"
                         % x["spitzen"]["fehler"][:120])
            else:
                for zweck, titel in (("long", "Long"), ("short", "Short"),
                                     ("grid", "Grid")):
                    beste = x["spitzen"].get(zweck, [])
                    if not beste:
                        continue
                    teile = []
                    for b in beste:
                        kz = {"krypto": "K", "aktie": "A",
                              "rohstoff": "R"}[b["kategorie"]]
                        warn = "!" if (b["vola"] > b["tor"]
                                       or b["deckel"] < 5) else ""
                        teile.append("%s·%s %.0f%s" % (b["basis"], kz,
                                                       b["punkte"], warn))
                    t.append("  %-6s %s" % (titel, "  ".join(teile)))
                t.append("  K/A/R = Krypto/Aktie/Rohstoff, ! = Tor zu")
        except Exception as e:                           # noqa: BLE001
            t.append("\n<b>Rangliste XPERP</b>\n  AUSFALL: %s" % e)

    t.append("")
    t.append(spiegelzeile())
    t.append("\n%d offene Position(en) insgesamt." % gesamt_offen)
    if not melder.bereit():
        t.append("Melder nicht eingerichtet: %s fehlt." % melder.fehlt())
    return "\n".join(t)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--senden", action="store_true",
                   help="zusaetzlich per Telegram schicken")
    p.add_argument("--ohne-xperp", action="store_true",
                   help="die Rangliste weglassen (schneller, kein Vollscan)")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        text = baue(mit_xperp=not a.ohne_xperp)
    except Exception:                                    # noqa: BLE001
        # Auch ein kaputter Bericht wird gemeldet. Stille ist die
        # schlechteste Meldung.
        text = ("<b>Handel</b>\nDer Tagesbericht ist gescheitert:\n<pre>%s</pre>"
                % traceback.format_exc()[-800:])
        print(text)
        if a.senden:
            melder.sende(text)
        return 1

    # Fuer die Konsole die HTML-Marken wieder heraus.
    print(text.replace("<b>", "").replace("</b>", ""))

    if a.senden:
        if melder.sende(text):
            print("\n-> per Telegram gesendet")
        else:
            print("\n-> nicht gesendet: %s fehlt" % melder.fehlt())
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
