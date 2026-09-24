"""Warum liegt die Liquidationswand oft auf der falschen Seite?

Reine Messung an den oeffentlichen OKX-Daten (kein Schluessel, keine Order).
Bildet dieselben Baender wie liq_wand und stellt je Band fest, auf welcher
Seite des Spots es liegt und ob die Spur daraus ein Signal machen wuerde.
"""

import collections
import importlib.util
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)
sys.path.insert(0, os.path.join(HANDEL, "scanner"))   # okx.py liegt dort
sys.path.insert(0, HIER)          # eigene Spur ZULETZT: gewinnt

import okx                                                          # noqa: E402

spec = importlib.util.spec_from_file_location(
    "liq_wand_handeln", os.path.join(HIER, "handeln.py"))
spur = importlib.util.module_from_spec(spec)
sys.modules["liq_wand_handeln"] = spur
spec.loader.exec_module(spur)
assert spur.__file__.startswith(HIER)

w = json.load(open(os.path.join(HIER, "wachen.json"), encoding="utf-8"))
inst = w.get("instrument", "BTC-USDT-SWAP")
familie = w.get("inst_familie", "BTC-USDT")
breite = float(w.get("bandbreite_prozent", 0.25))

spot = okx.letzter_kurs(inst)
liqs = spur.liquidationen(familie, int(w.get("liq_grenze", 100)))
print("Spot %.1f | %d Zwangsschluesse | Band %.2f %% (= %.0f USD)"
      % (spot, len(liqs), breite, spot * breite / 100))

if not liqs:
    raise SystemExit("keine Daten")

zeiten = sorted(float(x.get("ts") or 0) for x in liqs if x.get("ts"))
if zeiten:
    dauer = (zeiten[-1] - zeiten[0]) / 60000.0
    alter = (datetime.now(timezone.utc).timestamp() * 1000 - zeiten[-1]) / 60000.0
    print("Zeitspanne der 100 Eintraege: %.1f min, juengster vor %.1f min"
          % (dauer, alter))

kurz = sum(1 for x in liqs if (x.get("seite") or "").lower() == "short")
lang = sum(1 for x in liqs if (x.get("seite") or "").lower() == "long")
print("davon Shorts liquidiert: %d | Longs liquidiert: %d" % (kurz, lang))


def band_je(gruppe):
    band = spot * breite / 100.0
    masse = collections.defaultdict(float)
    for x in gruppe:
        px = float(x.get("preis") or 0)
        if px > 0:
            masse[round(px / band) * band] += float(x.get("kontrakte") or 0)
    return masse


# Wie oft liegt der groesste Einzelpreis-Punkt ueber / unter dem Spot?
alle = band_je(liqs)
print("\nBaender (Masse absteigend, Abstand zum Spot):")
for preis, menge in sorted(alle.items(), key=lambda t: -t[1])[:6]:
    gruppe = [x for x in liqs
              if abs(round(float(x.get("preis") or 0) / (spot * breite / 100.0))
                     * (spot * breite / 100.0) - preis) < 1e-9]
    s_kurz = sum(float(x.get("kontrakte") or 0) for x in gruppe
                 if (x.get("seite") or "").lower() == "short")
    s_lang = sum(float(x.get("kontrakte") or 0) for x in gruppe
                 if (x.get("seite") or "").lower() == "long")
    seite = "short" if s_kurz >= s_lang else "long"
    abstand = (preis / spot - 1) * 100
    urteil = spur.signal({"spot": spot, "liqs": gruppe}, w)
    print("  %10.1f  %8.1f Kontrakte  %-5s liquidiert  %+6.2f %%  %s"
          % (preis, menge, seite, abstand,
             "Signal %s" % urteil if urteil else "kein Signal"))

# Kernfrage: wo sitzen die Liquidierungen relativ zum Spot?
ueber = sum(1 for x in liqs if float(x.get("preis") or 0) > spot)
print("\n%d von %d Eintraegen liegen UEBER dem Spot, %d darunter"
      % (ueber, len(liqs), len(liqs) - ueber))
print("Schwelle: mindestens %d Eintraege, mindestens %.0f %% Masse im Band, "
      "hoechstens %.1f %% Abstand"
      % (w.get("mindest_liquidationen", 20), w.get("mindest_anteil", 0.30) * 100,
         w.get("max_abstand_prozent", 2.0)))
