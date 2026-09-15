"""SuperTrend-Spur: Richtungswechsel plus Trailing-Stop auf der Linie.

Signal: supertrend(k, n=10, faktor=3.0) aus xperp/indikatoren.py.
LONG beim Wechsel der SuperTrend-Richtung von -1 auf +1.
SHORT von +1 auf -1.
Besonderheit: der SuperTrend-WERT ist zugleich der Trailing-Stop
(Ausstieg, wenn der Schluss die Linie kreuzt).

Zeitrahmen: 4H. Instrumente: BTC-USDT, ETH-USDT, SOL-USDT.
Papier: handel_erlaubt=false.

Aufruf:
  python handeln.py --vorschau   waere dran, ohne schreiben
  python handeln.py --papier     Papierlauf mit Journal
  python handeln.py --wachen     Grenzen als Momentaufnahme
  python handeln.py --live       verweigert, nennt den Grund
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
# Reihenfolge zaehlt: sys.path.insert(0, ...) dreht die Liste um, deshalb
# rueckwaerts einfuegen. HIER muss ganz vorne stehen, sonst gewinnt
# scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, os.pardir, "Bus"),
          os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import wachen_pruefung as wp  # noqa: E402

# ratschen.py ueber den PFAD laden, nicht ueber sys.path: die Datei liegt
# eine Ebene hoeher und heisst wie kein Paket. Ein Import ueber sys.path
# haenge davon ab, wer vorher was eingefuegt hat.
from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "ratschen.py")
_s = spec_from_file_location("ratschen", _p)
ratschen = module_from_spec(_s)
_s.loader.exec_module(ratschen)

WACHEN = os.path.join(HIER, "wachen.json")
ZUSTAND = os.path.join(HIER, "zustand.json")
JOURNAL = os.path.join(HIER, "handelsjournal.csv")

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund"]

SCHREIBEN = True

# --- Test-Seams -----------------------------------------------------------
kerzen_quelle = None
zeit_quelle = None


# --- Zeit ------------------------------------------------------------------

def _jetzt():
    if zeit_quelle:
        return zeit_quelle()
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Dateien ---------------------------------------------------------------

def lade_wachen():
    with open(WACHEN, encoding="utf-8") as f:
        return json.load(f)


def lade_zustand():
    try:
        with open(ZUSTAND, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"positionen": [], "modus": "papier", "letzter_lauf": None,
                "verluste_usd": 0.0}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    with open(ZUSTAND, "w", encoding="utf-8") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")


def journal(**felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN)
        if neu:
            w.writeheader()
        w.writerow(felder)


def spiegeln(z, w):
    """Bedingung 4: Journal und Zustand ausser Haus."""
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand)


# --- Kerzen ----------------------------------------------------------------

def lade_kerzen(inst, intervall, anzahl):
    if kerzen_quelle:
        k = kerzen_quelle(inst, intervall, anzahl)
    else:
        try:
            import okx
            k = okx.kerzen(inst, intervall, anzahl)
        except Exception as e:
            print("Netzfehler: Kerzen fuer %s nicht abrufbar (%s)" % (inst, e),
                  file=sys.stderr)
            return []
    return [r if len(r) == 6 else r + [0.0] for r in k]


# --- Signallogik -----------------------------------------------------------

def atr_abs(k, idx, n=14):
    if idx < n:
        return None
    summ = 0.0
    for j in range(idx - n + 1, idx + 1):
        summ += k[j][2] - k[j][3]
    return summ / n


def signal(k, idx):
    """SuperTrend-Signal an Kerze idx. Gibt 'long', 'short' oder None."""
    if idx < 1:
        return None
    try:
        sys.path.insert(0, HANDEL)
        import indikatoren as xi
    except ImportError:
        return None
    linie, richtung = xi.supertrend(k, n=10, faktor=3.0)
    if richtung[idx - 1] is None or richtung[idx] is None:
        return None
    # LONG: Wechsel -1 -> +1
    if richtung[idx - 1] == -1 and richtung[idx] == 1:
        return "long", linie[idx]
    # SHORT: Wechsel +1 -> -1
    if richtung[idx - 1] == 1 and richtung[idx] == -1:
        return "short", linie[idx]
    return None


def trailing_ausstieg(p, k, linie, richtung):
    """SuperTrend-Wert als Trailing-Stop: Schluss kreuzt die Linie."""
    kurs = k[-1][4]
    if p["seite"] == "long":
        # Long: Linie von unten angefasst
        if richtung[-1] == -1 or kurs <= linie[-1]:
            return "trailing"
    else:
        if richtung[-1] == 1 or kurs >= linie[-1]:
            return "trailing"
    return None


# --- Positionen ------------------------------------------------------------

def pruefe_einstieg(inst, k, z, w, faktor):
    if not z.get("positionen"):
        z["positionen"] = []
    if len(z["positionen"]) >= w.get("max_offene_positionen", 4):
        return
    if not k or len(k) < w.get("mindest_kerzen", 300):
        return

    idx = len(k) - 1
    sig = signal(k, idx)
    if not sig:
        return
    seite, _linie = sig

    einstieg = k[idx][4]
    atr = atr_abs(k, idx, 14)
    if not atr or atr <= 0:
        return

    # Der Stop-Abstand kommt aus dem ATR, wird aber in den Pflichtrahmen
    # gezwungen. Stop UND Ziel entstehen danach aus demselben Prozentsatz -
    # sonst stuende im Journal ein Stop-Preis, der nicht zu stop_pct passt,
    # und die Groesse waere gegen eine andere Zahl gerechnet als der Ausstieg.
    stop_pct = atr / einstieg * 100.0
    stop_pct = max(stop_pct, w.get("pflicht_stop_prozent_min", 5.0))
    stop_pct_eff = min(stop_pct, w.get("pflicht_stop_prozent_max", 12.0))

    vz = 1 if seite == "long" else -1
    abstand = einstieg * stop_pct_eff / 100.0
    r = w.get("ziel_r_vielfaches", 2.0)
    stop = einstieg - vz * abstand
    ziel = einstieg + vz * r * abstand

    nominel = w["risiko_je_position_usd"] / (stop_pct_eff / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"])
    nominel *= faktor
    if nominel <= 0:
        return

    z["positionen"].append({
        "inst": inst, "seite": seite, "einstieg": einstieg,
        "stop": stop, "ziel": ziel, "stop_pct": stop_pct_eff,
        "nominal": nominel, "eroeffnet_zeit": _jetzt(),
    })

    print("EINSTIEG %s %.6f Stop %.2f%% Ziel R=2 (%.6f) Nominal %.2f USD" % (
        seite.upper(), einstieg, stop_pct_eff, ziel, nominel))
    journal(zeit=_jetzt(), modus="papier", aktion="kauf", inst=inst, seite=seite,
            preis="%.6f" % einstieg, einsatz_usd="%.2f" % nominel,
            stop="%.6f" % stop, ziel="%.6f" % ziel,
            stop_pct="%.2f" % stop_pct_eff, grund="supertrend")


def pruefe_ausstiege(z, k, w):
    """Ausstiege: Stop/Ziel UND SuperTrend-Trailing."""
    behalten = []
    try:
        sys.path.insert(0, HANDEL)
        import indikatoren as xi
        linie, richtung = xi.supertrend(k, n=10, faktor=3.0)
    except Exception:
        linie, richtung = None, None

    for p in z.get("positionen", []):
        kurs = k[-1][4] if k else None
        if not kurs:
            behalten.append(p)
            continue

        grund = None
        vz = 1 if p["seite"] == "long" else -1
        if p["seite"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif kurs <= p["ziel"]:
                grund = "ziel"

        if not grund and linie is not None:
            t = trailing_ausstieg(p, k, linie, richtung)
            if t:
                grund = t

        if not grund:
            behalten.append(p)
            continue

        gv = (kurs - p["einstieg"]) * vz
        erloes = p["nominal"] + gv
        print("AUSSTIEG (%s) %.6f G/V %+.2f USD" % (grund, kurs, gv))
        journal(zeit=_jetzt(), modus="papier", aktion="verkauf", inst=p["inst"],
                seite=p["seite"], preis="%.6f" % kurs,
                einsatz_usd="%.2f" % erloes, stop="%.6f" % p["stop"],
                ziel="%.6f" % p["ziel"],
                stop_pct="%.2f" % p["stop_pct"], grund=grund)

    z["positionen"] = behalten


# --- Laeuf -----------------------------------------------------------------

def lauf(modus):
    w = lade_wachen()
    z = lade_zustand()
    z.setdefault("positionen", [])

    if modus == "wachen":
        print(json.dumps(wp.lage(w, JOURNAL, z), indent=2, ensure_ascii=False))
        return

    s = wp.lage(w, JOURNAL, z)
    ruecklauf = s.get("ruecklauf_usd", 0.0)
    faktor = groessenfaktor(ruecklauf, w)

    if s.get("kill"):
        print("- Kill-Schwelle erreicht (%.2f USD Ruecklauf). Alles flach." % ruecklauf)
        z["positionen"] = []
        schreibe_zustand(z)
        spiegeln(z, w)
        return

    if modus == "vorschau":
        print("Vorschau: keine Dateien geschrieben.")
        return

    for inst in w.get("instrumente", []):
        intervall = w.get("kerzen_takt", "4H")
        anzahl = w.get("mindest_kerzen", 300)
        try:
            k = lade_kerzen(inst, intervall, anzahl)
        except Exception as e:
            print("Uebersprungen (%s): %s" % (inst, e), file=sys.stderr)
            continue
        if not k:
            print("Uebersprungen (%s): keine Kerzen" % inst, file=sys.stderr)
            continue

        bestehend = [p for p in z["positionen"] if p["inst"] == inst]
        if bestehend:
            z["positionen"] = [p for p in z["positionen"] if p["inst"] != inst]
            z["positionen"].extend(bestehend)
            pruefe_ausstiege(z, k, w)

        pruefe_einstieg(inst, k, z, w, faktor)

    schreibe_zustand(z)
    spiegeln(z, w)


def groessenfaktor(ruecklauf, w):
    """Drawdown-Ratsche aus ratschen.py - eine Umsetzung fuer alle Spuren."""
    return ratschen.groessenfaktor(ruecklauf, w)


# --- Main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau",
                    dest="modus", help="was waere dran, ohne schreiben")
    ap.add_argument("--papier", action="store_const", const="papier", dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    ap.set_defaults(modus="vorschau")
    a = ap.parse_args()

    if a.modus == "live":
        print("--live verweigert: Papier-Spur, keine Orders moeglich.")
        return 1

    lauf(a.modus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())