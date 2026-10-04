"""Die Erhebung je Spur - an EINER Stelle.

Liest, rechnet nicht und formatiert nicht. Wer Text will, nimmt
tagesbericht.py oder wochenbericht.py; beide bekommen ihre Zahlen von hier.
Vor dem 18.09.2026 stand diese Erhebung in tagesbericht.py und waere fuer
den Wochenbericht ein zweites Mal entstanden.
"""

import json
import os
import sys

import auswertung_alle
import risikostufe
import zeitfenster

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HIER, "scanner"))
# Die Module der Spur 2 (okxf, wachen_xperp). Sie werden hier auch fuer die
# SWAP-Spur gebraucht, deren eigener Ordner weder das eine noch das andere
# enthaelt. Ueber __file__ bestimmt und nicht ueber HIER: HIER zeigen die Tests
# auf einen Datenordner, die Module liegen trotzdem hier.
XPERP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xperp")

_UNGESETZT = object()

# Das Fenster der Berichtszahlen. Sieben Tage, weil "seit Anfang" jede
# Aenderung der letzten Woche unter dem Gewicht der Historie verschwinden
# laesst. Darstellungsgroesse, keine Handelsgroesse - deshalb hier und
# nicht in einer wachen.json.
FENSTER_TAGE = 7


def _buch(pfad):
    """Pfad eines Buchs: Zustand und Journal mit Stufensuffix, sonst unveraendert.

    Gesetzt wird das Suffix ueber `HANDEL_RISIKO` (Handel/risikostufe.py): eine
    Risikostufe schreibt `zustand.mittel.json` und `handelsjournal.mittel.csv`.
    Ein Bericht, der die Stufe zeigen soll, muss DIESE Dateien lesen - sonst
    zeigt er mit dem Kopf "Faktor 4" die Zahlen der Basis.

    `wachen.json` ausdruecklich NICHT: die Wachen werden beim Laden skaliert
    (`risikostufe.skaliere`), die Datei behaelt ihren Namen. Mit Suffix gelesen
    waere die Wachenlage jedes Stufenberichts leer - und damit jede Sperre
    falsch.
    """
    name = os.path.basename(os.fspath(pfad))
    if name.startswith("zustand") or name.startswith("handelsjournal"):
        return risikostufe.datei(pfad)
    return pfad


def _lies(pfad, vorgabe=None):
    try:
        with open(_buch(pfad), encoding="utf-8") as f:
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
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
    }


def _kraken_buch_waehrung(z):
    """Die Waehrung, in der das Kraken-Buch steht - fuer die ANZEIGE.

    Die Regel steht in `auswertung_alle.kraken_buch_waehrung()` und NUR dort:
    der Tagesbericht rechnet ueber `auswertung_alle.kennzahlen_fuer()` mit
    derselben Waehrung, und zwei Fassungen derselben Regel laufen auseinander.
    Seit 30.09.2026 kann die Spur in EUR, USDC und EURC handeln; Positionen aus
    der Zeit davor tragen kein Feld - damals war EUR die einzige Waehrung der
    Spur, also ist EUR die richtige Antwort und nicht "unbekannt"."""
    return auswertung_alle.kraken_buch_waehrung(z)


def spur_kraken():
    """Spur 3 - Kraken Spot, in der Waehrung des Buchs."""
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
        "name": "Spur 3  Kraken", "waehrung": _kraken_buch_waehrung(z),
        "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": "wachen_kraken",
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
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
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
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
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
    }

def spur_orb():
    """ORB auf OKX-Perpetuals - Papierspur, USDT, angeschlossen 21.09.2026.

    Dieselbe Strategie wie orbk, andere Boerse: BTC-/ETH-USDT-SWAP, Session
    ist die 00:00-UTC-Tagesgrenze. Sie fuehrt hoechstens EINE Position
    ('position' in zustand.json, kein 'positionen'). Papier ohne Live-Pfad;
    das eigene Backtest-Urteil ist fuer beide Instrumente negativ, die Spur
    laeuft nur zur Beobachtung des gemessenen Erwartungswerts.
    """
    ordner = os.path.join(HIER, "orb")
    w = _lies(os.path.join(ordner, "wachen.json"), {})
    z = _lies(os.path.join(ordner, "zustand.json"), {}) or {}
    p = z.get("position")
    pos = [p] if p else []

    kurse = {}
    if pos:
        try:
            sys.path.insert(0, os.path.join(HIER, "xperp"))
            import okxf                                          # noqa: PLC0415
            for x in pos:
                konf = (w.get("instrumente") or {}).get(x.get("inst"), {})
                if konf.get("okx"):
                    try:
                        kurse[x["inst"]] = float(okxf.letzter_kurs(konf["okx"]))
                    except Exception:                            # noqa: BLE001
                        pass
        except Exception:                                        # noqa: BLE001
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
        "name": "ORB-OKX (Papier)",
        "waehrung": "USDT", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": "wachen_orb",
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
    }


def spur_spiegel():
    """Spiegel-Spur - Papierbuch fuer Copy-Trading, USD je Kopie.

    Sie hat kein Pruefmodul und keine fuenf Bedingungen: ihr Ergebnis ist eine
    Bilanz, keine Wache. Der Betrag je Kopie ist der Einsatz (was gebunden
    waere), der Prozentwert das Ergebnis nach Slippage und Gebuehr - gerechnet
    mit derselben Formel wie das Buch selbst, damit der Bericht nicht
    schoenrechnet, was die Spur richtig rechnet.
    """
    return _spur_spiegel_arm("")


def spur_spiegel_knapp():
    """Schattenbuch 'knapp' der Spiegel-Spur (V1 Ausstiegsgeometrie).

    Dieselbe Signalquelle wie spiegel, engere Stop/Trailing-Parameter
    (wachen.knapp.json). Liest zustand.knapp.json und handelsjournal.knapp.csv.
    """
    return _spur_spiegel_arm("knapp")


def spur_spiegel_weit():
    """Schattenbuch 'weit' der Spiegel-Spur (V1 Ausstiegsgeometrie).

    Dieselbe Signalquelle wie spiegel, weitere Stop/Trailing-Parameter
    (wachen.weit.json). Liest zustand.weit.json und handelsjournal.weit.csv.
    """
    return _spur_spiegel_arm("weit")


def _spur_spiegel_arm(suffix):
    """Gemeinsamer Leser fuer spiegel und seine Schattenbuecher.

    `suffix` ist "" (Hauptbuch), "knapp" oder "weit". Die Dateinamen tragen
    dann das Suffix vor der Endung (zustand.knapp.json, wachen.knapp.json).
    """
    ordner = os.path.join(HIER, "spiegel")
    def _arm(n):
        if not suffix:
            return n
        stamm, endung = os.path.splitext(n)
        return "%s.%s%s" % (stamm, suffix, endung)
    w = _lies(os.path.join(ordner, _arm("wachen.json")), {})
    z = _lies(os.path.join(ordner, _arm("zustand.json")), {}) or {}
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
    name = "Spiegel (Papier, Copy)"
    if suffix:
        name = "Spiegel-%s (Papier, Copy)" % suffix
    return {
        "name": name, "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        # Kein Pruefmodul: die anderen Spuren wachen ueber fuenf Bedingungen,
        # diese fuehrt ein Buch. Ohne diesen Eintrag wuerde der Bericht eine
        # fremde Wachenrechnung auf sie anwenden und "Wachen nicht lesbar"
        # schreiben.
        "pruefmodul": None,
        "papierfest": True,
        "journal": _buch(os.path.join(ordner, _arm("handelsjournal.csv"))),
        "bilanz": _bilanz("spiegel" + (".%s" % suffix if suffix else ""),
                          ordner=ordner,
                          journal=_buch(os.path.join(ordner, _arm("handelsjournal.csv")))),
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
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
        "bilanz": _bilanz("kopier"),
    }


def _bilanz(spur, ordner=None, journal=None):
    """Die Bilanzzeile einer Buch-Spur - rein lesend, aus EINER Quelle.

    Sie kommt aus <spur>/auswertung.py: derselbe Aufruf, den eine GUI zeigt.
    Eine zweite Formel fuer dieselbe Frage waere eine zweite Wahrheit.
    Faellt das Modul aus, steht der Grund da und nicht gar nichts.

    Geladen wird ueber den DATEIPFAD, nicht ueber den Modulnamen: mehrere
    Spuren haben ein auswertung.py, und sys.modules gaebe beim zweiten
    Import das erste zurueck - die Spiegel-Zeile traege dann die Zahlen von
    Omniquant.

    `ordner`/`journal` ueberschreiben den Standard (Spurname als Ordner,
    handelsjournal.csv): die Spiegel-Schattenbuecher (18.09.2026) teilen den
    Ordner von spiegel, lesen aber ihr eigenes Journal (handelsjournal.knapp.csv).
    """
    ordner = ordner or os.path.join(HIER, spur)
    journal = journal or _buch(os.path.join(ordner, "handelsjournal.csv"))
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
        return modul.kernzeile(journal)
    except Exception as e:                                 # noqa: BLE001
        return "Auswertung nicht lesbar: %s" % str(e)[:80]
    finally:
        sys.dont_write_bytecode = alt


# Oeffentlicher Name fuer dieselbe Funktion: `befehle.py` (/spur, /strategien)
# zitiert die Bilanzzeile einer Buch-Spur. Ein zweiter NAME, kein zweiter
# Aufruf - die Rechnung bleibt EINE.
bilanz = _bilanz


# --- Indikator-Spuren (15.09.2026 angeschlossen) ---------------------------
# Vier Spuren mit demselben Aufbau: ein Signal je Indikator, ATR-Stop,
# Ziel = R x Stop, Papier ohne Live-Zweig. Sie teilen sich EINE Funktion -
# vier Abschriften waeren vier Wahrheiten fuer dieselbe Frage.

def _kurs_ueber_varianten(okx_modul, inst):
    """Bare Symbole ("AAVE") auf OKX-InstIds aufloesen: Symbol, -USDT, -USDC.

    Manche Spuren tragen nur das Symbol in `zustand.json` (Bot-Spuren auf
    CoinGecko-Daten), `okx.letzter_kurs` braucht aber eine InstId
    ("AAVE-USDT"). Der erste Treffer gewinnt; keiner -> None. Ein Ausfall
    ist still - der Bericht haengt nicht am Netz und zeigt sonst "(kein
    Kurs)".
    """
    for versuch in (inst, inst + "-USDT", inst + "-USDC"):
        try:
            wert = float(okx_modul.letzter_kurs(versuch))
        except Exception:                                       # noqa: BLE001
            continue
        if wert > 0:
            return wert
    return None


def _boerse_von(p, w):
    """Die Boerse einer Position: ihr eigenes Feld, sonst die erste der Spur.

    Wichtig fuer den Kurs: OKX notiert in USDC, Kraken in EUR. Ein Mix aus
    beiden zeigt Prozente, die es nicht gibt (23.09.2026 stand die BTC-Position
    im Bericht +11 %, real -2 %).
    """
    name = str(p.get("boerse") or "").strip().lower()
    if name:
        return name
    roh = w.get("boersen") or ([w.get("boerse")] if w.get("boerse") else [])
    return str(roh[0]).strip().lower() if roh else ""


def _spur_indikator(ordner, name, live_faehig=False, arm=""):
    """Eine der vier Indikator-Spuren: Bestand gegen den aktuellen Kurs.

    Derselbe Rechenweg wie bei der Gitter-Spur (kein eigener). Kein
    Wachenblock: ihre `wachen.json` fuehrt weder `freigabe` noch die fuenf
    Bedingungen, und `wachenlage()` wuerde die fremde Rechnung auf sie
    anwenden.

    `live_faehig=True` fuer Spuren MIT Live-Zweig (mosaic): sonst meldet der
    Bericht "kein Live-Zweig (Papierpfad)" und Max liest eine Unwahrheit -
    mosaic handelt seit dem 22.09.2026 live bei Kraken (Befund 23.09.2026).

    `arm` ist das Dateisuffix eines Schattenbuchs, das den Ordner mit dem
    Hauptbuch teilt (squeeze_eth -> zustand.eth.json). Ohne diesen Griff las
    der Bericht fuer den Arm das Buch des Hauptbuchs und nannte dessen
    Positionen seine eigenen - 04.10.2026.
    """
    pfad = os.path.join(HIER, ordner)
    def datei(stamm):
        teile = os.path.splitext(stamm)
        return "%s.%s%s" % (teile[0], arm, teile[1]) if arm else stamm
    w = _lies(os.path.join(pfad, datei("wachen.json")), {})
    z = _lies(os.path.join(pfad, datei("zustand.json")), {}) or {}
    pos = z.get("positionen", []) or []

    if live_faehig:
        # Modus aus den Wachen, nicht aus dem Buch: eine Spur ohne offene
        # Position ist trotzdem live bereit.
        bereit = bool(w.get("handel_erlaubt")
                      and (w.get("freigabe") or {}).get("erfuellt"))
        # `boersen` (Liste, Vorrang) oder das alte einzelne `boerse`.
        roh = w.get("boersen") or ([w.get("boerse")] if w.get("boerse") else [])
        boerse = ", ".join(str(b).strip() for b in roh if str(b).strip())
        name = "%s (%s)" % (name,
                            "live ueber %s" % boerse if bereit and boerse
                            else "Papier")

    kurse = {}
    kraken_kurse = {}
    if pos:
        if any(_boerse_von(p, w) == "kraken" for p in pos):
            # Positionen an der Boerse Kraken werden mit KRAKEN-Kursen gerechnet
            # (EUR). Das Modul uebersetzt mosaics OKX-Namen auf Kraken-Paare und
            # wird per Pfad geladen - kein sys.path-Eintrag, der gleichnamige
            # Module verdecken koennte.
            try:
                import importlib.util                             # noqa: PLC0415
                pfad = os.path.join(HIER, "mosaic", "kraken_spot.py")
                spec = importlib.util.spec_from_file_location(
                    "lage_mosaic_kraken_spot", pfad)
                ks = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ks)
                for p in pos:
                    if _boerse_von(p, w) != "kraken":
                        continue
                    try:
                        kraken_kurse[p.get("inst")] = float(
                            ks.letzter_kurs(p.get("inst")))
                    except Exception:                         # noqa: BLE001
                        pass
            except Exception:                                 # noqa: BLE001
                pass
        try:
            sys.path.insert(0, os.path.join(HIER, "scanner"))
            import okx                                          # noqa: PLC0415
            for p in pos:
                inst = (p.get("inst") or "").strip()
                if not inst or inst in kraken_kurse:
                    continue
                k = _kurs_ueber_varianten(okx, inst)
                if k:
                    kurse[inst] = k
        except Exception:                                       # noqa: BLE001
            pass
    kurse.update(kraken_kurse)

    zeilen = []
    for p in pos:
        k = kurse.get(p.get("inst"))
        einstieg = p.get("einstieg")
        vz = 1 if (p.get("seite") or "long") == "long" else -1
        bewegt = (vz * (k / einstieg - 1) * 100) if (k and einstieg) else None
        zeilen.append({
            "name": "%s %s%s" % (p.get("inst", "?"), p.get("seite", ""),
                                 " (live)" if p.get("modus") == "live" else ""),
            "einstieg": einstieg, "kurs": k, "wert": p.get("nominal", 0),
            "vh": bewegt, "stop": p.get("stop"), "ziel": p.get("ziel"),
            "seit": (p.get("eroeffnet_zeit") or "")[:10],
            "seite": p.get("seite"),
        })
    return {
        "name": name, "waehrung": w.get("waehrung", "USD"), "w": w, "z": z,
        "positionen": zeilen, "ordner": pfad, "pruefmodul": None,
        "papierfest": not live_faehig,
        "journal": _buch(os.path.join(pfad, "handelsjournal.csv")),
    }


def spur_macd_mtf():
    return _spur_indikator("macd_mtf", "MACD-MTF (Indikator)")


def spur_squeeze():
    return _spur_indikator("squeeze", "Squeeze (Indikator)")


def spur_squeeze_eth():
    """Schattenarm 'eth' (03.10.2026, Auftrag Max "Schattenarm") - dieselbe
    Regel fest auf ETH, eigenes Buch (zustand.eth.json). Der Bericht las fuer
    den Arm das Buch des Hauptbuchs, als waere es sein eigenes."""
    return _spur_indikator("squeeze", "Squeeze-ETH (Schattenarm)", arm="eth")


def spur_supertrend():
    return _spur_indikator("supertrend", "SuperTrend (Indikator)")


def spur_trendwende_btc():
    return _spur_indikator("trendwende_btc",
                           "Trendwende BTC (Short bei Wende)")


def spur_liq_wand():
    return _spur_indikator("liq_wand",
                           "Liquidations-Wand (BTC)")


def spur_robinhood_radar():
    return _spur_indikator("robinhood_radar",
                           "Robinhood-Radar (Wallet-Kohorte)")


def spur_omnitrade():
    # live_faehig: die Spur HAT einen Live-Zweig (Kraken-Spot ueber den
    # gemeinsamen Kern, boerse=kraken in der wachen.json) - ohne dieses Flag
    # meldet der Bericht "kein Live-Zweig (Papierpfad)" und Max liest eine
    # Unwahrheit. Scharf ist er nicht: handel_erlaubt=false, freigabe offen.
    return _spur_indikator("omnitrade",
                           "omnitrade (Rust-Lauf gespiegelt)", live_faehig=True)


# PROPHET-SIGNAL (02.10.2026): Prophet-Idee als Kursregel ueber prophet_regeln.py
# (saisonale Zerlegung + EMA30-Trend, CryptoPredictions-Papier). Gleiche
# Journalform wie die Indikator-Spuren, deshalb derselbe Leser. Kein Live-Zweig.
def spur_prophet_signal():
    return _spur_indikator("prophet_signal", "Prophet-Signal (EMA30+Saisonalitaet)")


# KLASSIK-SPUREN (30.09.2026): alle Kursregeln ueber klassik_regeln.py.
KLASSIK_SPUREN = (
    ("klassik_sma", "Klassik SMA-Kreuz 20/50"),
    ("klassik_ema", "Klassik EMA-Kreuz 12/26"),
    ("klassik_macd", "Klassik MACD-Kreuz"),
    ("klassik_bollinger", "Klassik Bollinger-Ausbruch"),
    ("klassik_donchian", "Klassik Donchian 20/10"),
    ("klassik_rsi", "Klassik RSI-Rueckkehr"),
    ("klassik_rsi2", "Klassik RSI(2) im Trend"),
    ("klassik_donchian_trend", "Klassik Donchian + EMA200"),
    ("klassik_sr_breaks", "Klassik S/R-Breaks"),
    ("klassik_pmax", "Klassik PMax Explorer"),
    ("klassik_supertrend", "Klassik Supertrend Explorer"),
)


def _klassik_holer(ordner, name):
    def holer():
        return _spur_indikator(ordner, name)
    # befehle.py leitet den Spurnamen aus dem Funktionsnamen ab (spur_<name>).
    holer.__name__ = "spur_" + ordner
    return holer


HOLER_KLASSIK = tuple(_klassik_holer(o, n) for o, n in KLASSIK_SPUREN)
# befehle._holer_fuer sucht spur_<name> als Modulattribut.
for _h in HOLER_KLASSIK:
    globals()[_h.__name__] = _h


def spur_wavetrend():
    return _spur_indikator("wavetrend", "WaveTrend (Indikator)")


def spur_moondev_funding():
    """Die Bot-Spur: Papierbuch auf den Funding-Extremen von Hyperliquid.

    Dieselbe Journalform wie die Indikator-Spuren (kauf/verkauf mit
    einsatz_usd, Positionsliste im Zustand) - deshalb derselbe Leser.
    """
    return _spur_indikator("moondev_funding", "Moon-Dev Funding")


def spur_moondev_listingarb():
    return _spur_indikator("moondev_listingarb", "Moon-Dev Listingarb")


def spur_moondev_topmovers():
    return _spur_indikator("moondev_topmovers", "Moon-Dev Top-Mover")


def spur_moondev_signalwelle():
    return _spur_indikator("moondev_signalwelle", "Signalwelle (1h)")


def spur_moondev_marktlage():
    return _spur_indikator("moondev_marktlage", "Moon-Dev Marktlage")


def spur_iv_wand():
    """Die IV-Wand: Optionszone als Kursmagnet. Journalform wie die
    Indikator-Spuren (kauf/verkauf mit einsatz_usd)."""
    return _spur_indikator("iv_wand", "IV-Wand (Optionszone)")


def spur_iv_waelle():
    """Die IV-Waelle (Deribit): erwartete Tagesspanne aus HV plus
    Options-Bepreisung (DVOL), dann an den Waenden (Strikes mit hohem OI)
    gegen die Bewegung. Dieselbe Journalform wie die Indikator-Spuren
    (kauf/verkauf mit einsatz_usd) - derselbe Leser."""
    return _spur_indikator("iv_waelle", "IV-Waelle (Deribit, Optionszone)")


def spur_omnitrade_futures():
    """Das Hebel-Bein der omnitrade-Spur (Kraken Futures, Hebel 7)."""
    return _spur_indikator("omnitrade_futures",
                           "omnitrade-Hebel (Kraken Futures, 7x)",
                           live_faehig=True)


def spur_moondev_whale():
    """Sprachmodell-Spur: Open-Interest-Anomalie. Journalform wie die
    Bot-Spuren (kauf/verkauf mit einsatz_usd) - derselbe Leser."""
    return _spur_indikator("moondev_whale", "Wale (OI, LLM-Urteil)")


def spur_moondev_liquidation():
    return _spur_indikator("moondev_liquidation",
                           "Liquidationen (LLM-Urteil)")


def spur_moondev_sentiment():
    return _spur_indikator("moondev_sentiment", "Schlagzeilen (LLM-Urteil)")


def spur_moondev_sniper():
    """Moon-Dev-Sniper-Spur: neue Solana-Launches (Pump.fun) als Papierbuch.

    Dieselbe Journalform wie die Bot-Spuren (kauf/verkauf mit einsatz_usd) -
    derselbe Leser.
    """
    return _spur_indikator("moondev_sniper", "Moon-Dev Sniper")


def spur_mosaic():
    """Mosaic-Spur: Mehr-Zeitrahmen-Preisaktion (4H/30M/5M), USD.

    Gleicher Buch-Aufbau wie die Indikator-Spuren: liest zustand.json,
    bewertet Bestand gegen den aktuellen Kurs, kein Wachenblock (keine
    fuenf Bedingungen). EIGENHEIT seit 21.09.2026: mosaic hat einen echten
    Live-Zweig (boerse in der wachen.json, Orderweg kraken_spot.py bzw.
    okx_spot.py) - der Bericht darf sie deshalb nicht als Papierpfad
    ausgeben (live_faehig=True).
    """
    return _spur_indikator("mosaic", "Mosaic (4H/30M/5M)", live_faehig=True)


def spur_omniquant(arm=""):
    """Omniquant-Spur - Papierbuch auf dem Prognose-Bericht, USD.

    Sie hat kein Pruefmodul und keine fuenf Bedingungen (wie die
    Spiegel-Spur): ihr Ergebnis ist ein Buch, keine Wache. Der Betrag je
    Position ist der Einsatz (nominal), der Prozentwert die Bewegung am
    Kurs - ohne Hebel, Spot-Paare aus dem Prognose-Bericht. papierfest=True,
    damit der Bericht "kein Live-Zweig" sagt statt "GESPERRT - wartet auf
    /ja".
    """
    ordner = os.path.join(HIER, "omniquant")
    suf = (".%s" % arm) if arm else ""
    w = _lies(os.path.join(ordner, "wachen%s.json" % suf), {})
    z = _lies(os.path.join(ordner, "zustand%s.json" % suf), {}) or {}
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
        "name": "Omniquant%s (%s)" % ((" " + arm) if arm else "",
                                      z.get("modus") or "papier"),
        "waehrung": "USD", "w": w, "z": z,
        "positionen": zeilen, "ordner": ordner,
        "pruefmodul": None,
        "papierfest": True,
        "journal": _buch(os.path.join(ordner, "handelsjournal%s.csv" % suf)),
        "bilanz": _bilanz("omniquant", ordner,
                          _buch(os.path.join(ordner, "handelsjournal%s.csv" % suf))),
    }


def spur_omniquant_weit():
    """Schattenarm 'weit' - dasselbe Buch, aber die WEICHE Prognose-Fassung.

    Angelegt am 24.09.2026: die strenge Fassung hatte bei 71 geprueften Maerkten
    0 Treffer (Ruecksetzer-Kaeufer ohne Ruecksetzer), der Arm soll Papierrunden
    erzeugen. Gleiche Groessen, gleiches Risiko, nur weitere Tore - der Vergleich
    misst damit die Tore. Eigenes Journal (handelsjournal.weit.csv).
    """
    return spur_omniquant("weit")


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
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
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
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
        "bilanz": zeile,
    }


def _spur_nautilus_kraken_arm(suffix, name, waehrung):
    """Kraken-Spur (Spot/Futures) - Papierzyklus, Herzschlag statt Wache.

    Wie spur_nautilus: kein Pruefmodul, papierfest, zeigt die letzte Quote.
    suffix "" = Spot (wachen.json/zustand.json), ".futures" = Futures.
    """
    ordner = os.path.join(HIER, "nautilus_kraken")
    w = _lies(os.path.join(ordner, "wachen%s.json" % suffix), {})
    z = _lies(os.path.join(ordner, "zustand%s.json" % suffix), {}) or {}

    q = z.get("letzte_quote") or {}
    if q:
        zeile = "letzte Quote bid=%s ask=%s" % (q.get("bid"), q.get("ask"))
    else:
        zeile = "noch kein Papierzyklus gelaufen"
    if z.get("letzter_lauf"):
        zeile += "  (Herzschlag %s)" % z["letzter_lauf"]

    return {
        "name": "%s (%s)" % (name, z.get("modus") or "papier"),
        "waehrung": waehrung, "w": w, "z": z,
        "positionen": [], "ordner": ordner,
        "pruefmodul": None,
        "papierfest": True,
        "journal": _buch(os.path.join(ordner, "handelsjournal%s.csv" % suffix)),
        "bilanz": zeile,
    }


def spur_nautilus_kraken():
    """Kraken-Spot (BTC/EUR, EUR, kein Hebel)."""
    return _spur_nautilus_kraken_arm("", "Kraken-Spot (EUR)", "EUR")


def spur_nautilus_kraken_futures():
    """Kraken-Futures (PF_XBTUSD, USD, Hebel)."""
    return _spur_nautilus_kraken_arm(".futures", "Kraken-Futures (USD)", "USD")


def spur_nautilus_emacross():
    """EMA-Cross aus nautilus_trader, 1H-Kerzen, USDT, Papier.

    Standardbuch ueber spur_buch - dieselbe Form wie die uebrigen
    Buch-Spuren. Die Spur steht als VERGLEICH neben den drei
    Nautilus-Armen, die Kopier-Signale als BTC-Proxy buchen.
    """
    return _spur_indikator("nautilus_emacross", "EMA-Cross 10/20 (1H, USDT)")


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
        "journal": _buch(os.path.join(ordner, "handelsjournal.csv")),
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



def _stufe_der_umgebung():
    """Die Risikostufe dieses Prozesses als `auswertung_alle.STUFE`.

    `None` heisst Basis - so erwartet es `auswertung_alle` (dort ist STUFE
    eine Modulvariable, die nur die Kommandozeile setzt). Der Bericht muss
    die Stufe aber ueber DIESELBE Quelle beziehen wie seine Buchdateien
    (`HANDEL_RISIKO`), sonst zeigt ein Stufenbericht die Positionen der Stufe
    und die Runden der Basis.
    """
    return None if risikostufe.stufe() == risikostufe.STANDARD \
        else risikostufe.stufe()


def zu_lage(roh, schluessel, tage=FENSTER_TAGE, kennzahlen=_UNGESETZT):
    """Eine spur_*()-Rueckgabe in die feste Form bringen.

    Der Aufbau selbst steht in `_zu_lage`; hier steht nur die Risikostufe
    drumherum. `auswertung_alle.STUFE` ist eine MODULVARIABLE (die
    Kommandozeile setzt sie, Vorgabe None = Basis), und `kennzahlen_fuer` und
    `hat_buch` lesen sie. Ohne diese Zeilen zeigte ein Stufenbericht die
    Positionen der Stufe und die Runden der Basis.
    """
    alt_stufe = auswertung_alle.STUFE
    if schluessel:
        auswertung_alle.STUFE = _stufe_der_umgebung()
    try:
        return _zu_lage(roh, schluessel, tage, kennzahlen)
    finally:
        # Auch bei einem Fehler zurueckstellen: der Bericht ist ein Leser und
        # darf den Prozess (Handelszentrale!) nicht umstellen.
        auswertung_alle.STUFE = alt_stufe


def _zu_lage(roh, schluessel, tage, kennzahlen):
    """Die feste Form einer spur_*()-Rueckgabe.

    kennzahlen wird nur von Tests gesetzt; im Betrieb holt die Funktion sie
    selbst. Der Wachtposten _UNGESETZT unterscheidet "nicht uebergeben" von
    "ausdruecklich keine" - None ist eine gueltige Antwort.
    """
    if kennzahlen is _UNGESETZT:
        kennzahlen = None
        if schluessel and auswertung_alle.hat_buch(schluessel):
            von, bis = zeitfenster.fenster(tage=tage)
            kennzahlen = auswertung_alle.kennzahlen_fuer(schluessel,
                                                         von=von, bis=bis)

    if schluessel and not auswertung_alle.hat_buch(schluessel):
        buchlage = "kein_buch"
        kennzahlen = None
    elif not kennzahlen or not kennzahlen.get("n"):
        buchlage = "zu_wenige_runden"
    elif auswertung_alle.belastbar(kennzahlen):
        buchlage = "belastbar"
    else:
        buchlage = "zu_wenige_runden"

    return {
        "schluessel": schluessel,
        "name": roh["name"],
        "waehrung": roh["waehrung"],
        "positionen": roh.get("positionen", []),
        "wachen": None,
        "sperren": [],
        "stillgelegt": bool(roh.get("w", {}).get("stillgelegt")),
        "kennzahlen": kennzahlen,
        "buchlage": buchlage,
        "buch_seit": auswertung_alle.buch_seit(schluessel) if schluessel else None,
        "bilanz": roh.get("bilanz"),
        "fehler": None,
        # Passthrough der Kopie-Familie: zu_lage normalisiert sonst auf eine
        # feste Form und wuerde diese zwei Felder still verwerfen (18.09.2026,
        # Berichts-Schlankung). Ohne "familie" rendert _block die Familie als
        # Positionen-Liste statt als schlanken Block.
        "familie": roh.get("familie"),
        "familie_offen": roh.get("familie_offen", 0),
        "roh": roh,
    }


def _schluessel_von(roh):
    """Der Ordnername der Spur, oder None. auswertung_alle kennt Spuren
    unter diesem Namen; ohne ihn gibt es keine Kennzahlen."""
    ordner = roh.get("ordner")
    if not ordner:
        return None
    name = os.path.basename(ordner.rstrip(os.sep))
    return name if name in auswertung_alle.SPUREN else None


def spur_kopier_familie():
    """Die Kopie-Familie (Spiegel + 2 Schattenbuecher + 2 Kopier) als EIN Block.

    Die Positionen aller Buecher bleiben in `positionen` (Schnappschuss und
    Gesamtsumme zaehlen sie weiter), gerendert wird aber je Buch nur eine
    schlanke Zeile aus `familie`. Keine zweite Formel: die Bilanzzeile jedes
    Buchs kommt aus seiner eigenen Auswertung (lage._bilanz) - dieselbe, die
    der Bericht heute schon zeigt.

    Bewusst KEIN "ordner": der Schluessel kaeme sonst aus dem Ordnernamen und
    kollidierte mit "spiegel" (_schluessel_von). Die Familie hat keinen
    auswertung_alle-Eintrag - ihr Schluessel bleibt None (Bericht nimmt den
    Namen).
    """
    quellen = (spur_spiegel, spur_spiegel_knapp, spur_spiegel_weit,
               spur_kopier)
    glieder, positionen = [], []
    for hole in quellen:
        try:
            b = hole()
        except Exception:                                 # noqa: BLE001
            continue
        name = b.get("name", "?")
        offen = len(b.get("positionen") or [])
        glieder.append({"name": name, "offen": offen,
                        "bilanz": b.get("bilanz") or "keine Auswertung"})
        for p in b.get("positionen") or []:
            pos = dict(p)
            pos["buch"] = name
            positionen.append(pos)
    offen = len(positionen)
    return {
        "name": "Kopie-Familie (Spiegel/Copy)", "waehrung": "USD",
        "w": {}, "positionen": positionen, "pruefmodul": None,
        "papierfest": True, "familie": glieder, "familie_offen": offen,
        "bilanz": "Kopie-Familie: %d offene Position ueber %d Buecher"
                  % (offen, len(glieder)),
    }


def erhebe(mit_xperp=True, tage=FENSTER_TAGE, holer=None):
    """Alle Spuren in fester Form. Ein Ausfall kostet eine Spur, nicht den Lauf.

    mit_xperp=False laesst den Xperp-Holer aus - der ruft fuer jede offene
    Position einen Live-Kurs bei OKX ab (Netzabfrage), was Aufrufer wie
    dauerlauf.py und wochenbericht.py sich ausdruecklich sparen wollen.
    """
    aus = []
    quellen = holer if holer is not None else HOLER
    if not mit_xperp:
        quellen = tuple(h for h in quellen
                        if getattr(h, "__name__", None)
                        != "spur_xperp_positionen")
    for hole in quellen:
        try:
            roh = hole()
        except Exception as e:                           # noqa: BLE001
            # Die Form kommt aus zu_lage() - EINE Quelle fuer die Felder.
            # Der Fehlerfall setzt nur, was er anders weiss: keine Kennzahlen
            # (deshalb kein_buch statt der sonst berechneten Kategorie), den
            # Fehlertext und ein leeres roh statt der echten Rueckgabe.
            fehl = zu_lage({"name": hole.__name__, "waehrung": "",
                            "positionen": [], "w": {}},
                           schluessel=None, tage=tage, kennzahlen=None)
            fehl["buchlage"] = "kein_buch"
            fehl["fehler"] = "%s: %s" % (type(e).__name__, e)
            fehl["roh"] = {}
            aus.append(fehl)
            continue
        e = zu_lage(roh, _schluessel_von(roh), tage=tage)
        e["wachen"] = (wachenlage(roh)
                       if roh.get("pruefmodul", "wachen_pruefung") else None)
        e["sperren"] = sperren(roh, e["wachen"])
        if roh.get("papierfest"):
            e["sperren"].insert(0, "kein Live-Zweig (Papierpfad)")
        aus.append(e)
    return aus


HOLER = (spur_xperp_positionen, spur_scanner, spur_kraken, spur_swap,
    spur_orb, spur_orbk, spur_omniquant, spur_omniquant_weit, spur_nautilus,
    spur_gitter, spur_kopier_familie,
    spur_macd_mtf, spur_squeeze, spur_squeeze_eth, spur_supertrend, spur_wavetrend,
    spur_trendwende_btc, spur_liq_wand, spur_robinhood_radar,
    spur_omnitrade, spur_omnitrade_futures,
    spur_nautilus_kraken, spur_nautilus_kraken_futures,
    spur_nautilus_emacross,
    spur_mosaic, spur_moondev_funding, spur_moondev_listingarb,
    spur_moondev_topmovers, spur_moondev_signalwelle, spur_moondev_marktlage, spur_iv_wand,
    spur_iv_waelle,
    spur_moondev_whale, spur_moondev_liquidation, spur_moondev_sentiment,
    spur_moondev_sniper,
    # Prophet-Signal (02.10.2026), Papierspur ueber prophet_regeln.py.
    spur_prophet_signal) + HOLER_KLASSIK

