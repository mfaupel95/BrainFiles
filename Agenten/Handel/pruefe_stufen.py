"""Kann die Stufen-Kontrolle auf den BESTAND ueberhaupt reissen? (PLAN §4.2)

DIE FRAGE, DIE DIESES WERKZEUG BEANTWORTET
`spur_buch.pruefe_stufen` schliesst das offene Buch, wenn sein Risiko ueber der
Grenze der Stufe liegt. Diese Grenze ist per Vorgabe das BUCHRISIKO der Spur
(Risiko je Position x Hoechstzahl Positionen). Nur: `einstieg()` setzt die
Nominale auf `risiko_je_position_usd / (stop_pct/100)` - das Risiko einer
Position ist damit per Konstruktion hoechstens `risiko_je_position_usd`, das
offene Buch hoechstens `risiko x Plaetze` = Buchrisiko.

EIN DECKEL AUF DEM BUCHRISIKO KANN DESHALB NIE REISSEN. Die Pruefung ist eine
DRIFT-Bremse (das Buch passt nicht mehr zur Konfiguration: Risiko oder Platzzahl
nach dem Eroeffnen gesenkt, Stufe gewechselt, Position aus einem aelteren Stand).
Damit der Kill wirklich bindet, muss die Grenze UNTER das Buchrisiko - und das
ist eine Betreiber-Entscheidung, keine Code-Frage. Genau das rechnet dieses
Werkzeug je Wachen-Datei nach, statt es zu behaupten.

Gemessen am 19.10.2026 ueber 56 Wachen-Dateien: 45 konnten nicht reissen, 10
hatten keine herleitbare Grenze, genau 1 (moondev_funding, Grenze 15.00 gegen
Buchrisiko 20.00) konnte. Dieselbe Rechnung hat fuer den Kapitaldeckel
`max_gesamt_usd` gegolten (2x bis 65x ueber dem Buchrisiko).

Kein Schreiber: liest nur wachen*.json und zustand*.json.
Aufruf aus dem Handel-Ordner: scanner/.venv/Scripts/python.exe pruefe_stufen.py
"""

import argparse
import glob
import json
import os
import sys
from importlib.util import module_from_spec, spec_from_file_location

HIER = os.path.dirname(os.path.abspath(__file__))

for _p in (os.path.join(HIER, "scanner"), HIER):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _lade(name):
    spec = spec_from_file_location(name, os.path.join(HIER, name + ".py"))
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


SB = _lade("spur_buch")          # stufen_schwelle - die EINE Definition
RATSCHEN = _lade("ratschen")
RS = _lade("risikostufe")        # skaliere/datei_fuer - die EINE Skalierung


def _zahl(wert, standard=None):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return standard


def _lese(pfad):
    try:
        with open(pfad, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def buchrisiko_zahlen(w):
    """(risiko je Position, Hoechstzahl Positionen) der Wache - oder (None, None)."""
    for risiko_schluessel, anzahl_schluessel in RATSCHEN.BUCHRISIKO_PAARE:
        if risiko_schluessel in w and anzahl_schluessel in w:
            return _zahl(w[risiko_schluessel]), _zahl(w[anzahl_schluessel])
    return None, None


def max_offenes_risiko(w):
    """Das hoechste offene Buchrisiko, das diese Wache ueberhaupt zulaesst.

    = Plaetze x min(Risiko je Position, max_pro_trade_usd x Mindest-Stop/100).
    Der zweite Teil ist noetig, weil `einstieg()` die Nominale zusaetzlich auf
    `max_pro_trade_usd` deckelt - dort ist das Risiko einer Position KLEINER
    als `risiko_je_position_usd`.
    """
    risiko, plaetze = buchrisiko_zahlen(w)
    if risiko is None or plaetze is None:
        return None
    max_pro = _zahl(w.get("max_pro_trade_usd"), 0.0) or 0.0
    min_stop = _zahl(w.get("pflicht_stop_prozent_min"), 5.0) or 5.0
    return plaetze * min(risiko, max_pro * min_stop / 100.0)


def skaliert(w, stufe_):
    """Die Wachen, wie die Stufe sie sieht - ueber `risikostufe.skaliere`.

    Ueber die ECHTE Skalierung, nicht nachgebaut: `skaliere` liest die Stufe aus
    der Umgebungsvariable, deshalb wird sie hier kurz gesetzt und danach
    zurueckgestellt. Eine nachgebaute Skalierung wuerde die Skalierung pruefen,
    nicht die Spur (Hausregel, siehe pruefe_ratschen.py).
    """
    alt = os.environ.get("HANDEL_RISIKO")
    os.environ["HANDEL_RISIKO"] = stufe_
    try:
        return RS.skaliere(w)
    finally:
        if alt is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = alt


def zustand_fuer(wachen_pfad, stufe_):
    """Die Zustandsdatei DIESER Stufe neben dieser Wachen-Datei - oder None."""
    ordner, name = os.path.split(wachen_pfad)
    stamm = name[len("wachen"):-len(".json")]          # "", ".knapp", ".weit", ...
    kandidat = RS.datei_fuer(os.path.join(ordner, "zustand" + stamm + ".json"),
                             stufe_)
    return kandidat if os.path.exists(kandidat) else None


def nutzt_das_hausbuch(spur_ordner):
    """Laeuft diese Spur ueber `spur_buch.zyklus`?

    Nur dann greift der Stufen-Kill. Fuenfzehn Dauerlauf-Spuren bringen ihren
    eigenen Zyklus mit (scanner, xperp, kraken, gitter, omniquant, orb, orbk,
    mosaic, kopier, prophet_signal, macd_mtf, wavetrend, nautilus*) - dort ist
    die Pruefung NICHT eingebaut, und genau dort stand am 19.10.2026 der
    Altbestand ueber der Grenze. Die Spalte gehoert in dieses Werkzeug, weil
    "0 koennen reissen" sonst wie eine Entwarnung aussieht, obwohl die Frage
    nur fuer einen Teil der Flotte beantwortet ist.
    """
    ordner = os.path.join(HIER, spur_ordner)
    for name in sorted(os.listdir(ordner)) if os.path.isdir(ordner) else []:
        if not (name.startswith("handeln") and name.endswith(".py")):
            continue
        try:
            with open(os.path.join(ordner, name), encoding="utf-8",
                      errors="replace") as fh:
                if "spur_buch" in fh.read():
                    return True
        except OSError:
            continue
    return False


def zeilen():
    """Eine Zeile je Wachen-Datei - die Struktur-Frage ist stufeninvariant.

    `kann_binden` haengt nicht an der Stufe: die Skalierung multipliziert Grenze
    UND erreichbares Buchrisiko mit demselben Faktor. Deshalb genuegt hier die
    Vorlage; die Bestandszahlen kommen weiter unten je Stufe.
    """
    for wachen_pfad in sorted(glob.glob(os.path.join(HIER, "*", "wachen*.json"))):
        w = _lese(wachen_pfad)
        if not isinstance(w, dict):
            continue
        risiko, plaetze = buchrisiko_zahlen(w)
        buch = RATSCHEN.buch_risiko(w)
        grenze, quelle = SB.stufen_schwelle(w)
        max_offen = max_offenes_risiko(w)
        bestand = []
        for stufe_ in RS.FAKTOREN:
            zp = zustand_fuer(wachen_pfad, stufe_)
            if zp is None:
                continue
            z = _lese(zp)
            if not isinstance(z, dict) or not z.get("positionen"):
                continue
            w_s = skaliert(w, stufe_)
            g_s, _q = SB.stufen_schwelle(w_s)
            o_s = RATSCHEN.offenes_risiko(z)
            bestand.append({"stufe": stufe_, "offen": o_s, "grenze": g_s,
                            "datei": os.path.basename(zp),
                            "positionen": len(z["positionen"]),
                            "ueber": (g_s is not None and o_s > g_s + 1e-9)})
        yield {
            "spur": os.path.relpath(wachen_pfad, HIER).replace("\\", "/"),
            "ordner": os.path.basename(os.path.dirname(wachen_pfad)),
            "risiko": risiko, "plaetze": plaetze, "buch": buch,
            "grenze": grenze, "quelle": quelle, "max_offen": max_offen,
            "bestand": bestand,
            "erfasst": nutzt_das_hausbuch(os.path.basename(os.path.dirname(wachen_pfad))),
            "kann_binden": (max_offen is not None and grenze is not None
                            and max_offen > grenze + 1e-9),
        }


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--still", action="store_true",
                   help="nur die Zeilen, die reissen koennen oder es gerade tun")
    args = p.parse_args()

    alle = list(zeilen())
    binden = [z for z in alle if z["kann_binden"]]
    tot = [z for z in alle if not z["kann_binden"] and z["grenze"] is not None]
    ohne = [z for z in alle if z["grenze"] is None]
    ueber = [(z, b) for z in alle for b in z["bestand"] if b["ueber"]]

    if not args.still:
        print("%-36s %-16s %10s %10s  %-8s %s"
              % ("wachen", "grenze (Quelle)", "buch", "max_offen",
                 "Hausbuch", "kann reissen?"))
        for z in alle:
            print("%-36s %-16s %10s %10s  %-8s %s"
                  % (z["spur"],
                     ("%.2f (%s)" % (z["grenze"], z["quelle"])) if z["grenze"] is not None
                     else "(keine)",
                     "%.2f" % z["buch"] if z["buch"] else "-",
                     "%.2f" % z["max_offen"] if z["max_offen"] is not None else "-",
                     "ja" if z["erfasst"] else "NEIN",
                     "JA" if z["kann_binden"] else "nein"))
        print()

    print("--- Bestand jetzt (je Stufe, gegen die Grenze DIESER Stufe) ---")
    for z in alle:
        for b in z["bestand"]:
            if args.still and not b["ueber"]:
                continue
            print("%-6s %-34s %-8s offen %9.2f  Grenze %8.2f  %d Pos.  %-22s %s"
                  % ("REISST" if b["ueber"] else "", z["spur"], b["stufe"],
                     b["offen"], b["grenze"] if b["grenze"] is not None else -1,
                     b["positionen"], b["datei"],
                     "" if z["erfasst"] else "<- NICHT erfasst (eigener Zyklus)"))
    print()
    print("%d Wachen-Dateien: %d koennen reissen, %d koennen es nicht, "
          "%d haben keine herleitbare Grenze."
          % (len(alle), len(binden), len(tot), len(ohne)))
    print("%d von %d laufen ueber `spur_buch.zyklus` - nur dort ist der "
          "Stufen-Kill eingebaut." % (len([z for z in alle if z["erfasst"]]), len(alle)))
    nicht_erfasst_ueber = [(z, b) for z, b in ueber if not z["erfasst"]]
    if nicht_erfasst_ueber:
        print("%d Bestand/Bestaende ueber der Grenze liegen in Spuren mit EIGENEM "
              "Zyklus: %s. Der Stufen-Kill in `spur_buch` erreicht sie nicht - sie "
              "brauchen denselben Aufruf in ihrer eigenen Ausstiegsfunktion."
              % (len(nicht_erfasst_ueber),
                 ", ".join(sorted({z["ordner"] for z, _b in nicht_erfasst_ueber}))))
    if ueber:
        erfasst_ueber = [(z, b) for z, b in ueber if z["erfasst"]]
        print("%d Bestand/Bestände stehen JETZT ueber ihrer Grenze: %d davon in "
              "erfassten Spuren (der naechste Zyklus schliesst sie, Grund %s), "
              "%d unwirksam (eigener Zyklus)."
              % (len(ueber), len(erfasst_ueber), SB.STUFEN_GRUND,
                 len(ueber) - len(erfasst_ueber)))
    if not binden and not ueber:
        print("Damit der Kill bindet, muss `max_offenes_risiko_usd` UNTER das "
              "Buchrisiko der Spur gesetzt werden - auf dem Buchrisiko kann er "
              "per Konstruktion nicht reissen. Das ist eine Entscheidung des "
              "Betreibers, keine Code-Frage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
