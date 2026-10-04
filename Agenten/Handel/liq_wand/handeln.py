#!/usr/bin/env python3
"""Liquidations-Wand (liq_wand): gegen den Zwangsschluss-Cluster handeln.

AUFTRAG Max 21.09.2026: "Bau liq_wand". Schwesterspur zu iv_wand - dort ist
die Wand der Options-Strike mit dem groessten offenen Interesse, hier der
Preis, an dem sich gerade Zwangsschluesse haeufen.

DIE REGEL, nachrechenbar
------------------------
OKX liefert oeffentlich (kein Schluessel) die letzten ausgefuehrten
Liquidationen je Instrument:
    /api/v5/public/liquidation-orders?instType=SWAP&uly=BTC-USDT&state=filled
Gemessen 21.09.2026: 100 Eintraege je Abruf ueber rund 78 Minuten, mit
Preis (bkPx), Groesse (sz) und Seite (posSide).

1. Die Liquidationen werden in Preisbaender (Vorgabe 0,25 %) gelegt und je
   Band die Kontraktmenge summiert. Das groesste Band ist die WAND.
2. Gehandelt wird nur, wenn die Wand
   - genug Masse hat (mindest_anteil der gesamten Menge im Fenster) und
   - nahe genug am Spot liegt (max_abstand_prozent).
3. RICHTUNG - und das ist der Kern: eine Liquidationswand ist kein
   Widerstand, sondern ein Beschleuniger. Werden dort SHORTS
   zwangsgeschlossen (posSide short), entsteht Kaufdruck nach oben; werden
   LONGS geschlossen, entsteht Verkaufsdruck nach unten. Die Spur geht also
   MIT der Richtung des Clusters, nicht dagegen.
   Gemessen am 21.09.2026 20:26-21:44: 71 Short-Liquidationen mit 4.897
   Kontrakten gegen 29 Long-Liquidationen mit 116 Kontrakten - also ein
   klarer Aufwaertsdruck, und die Wand lag 0,75 % ueber dem Spot.
4. Ziel ist die Wand selbst (als Marktpunkt uebergeben), Stop auf der
   anderen Seite des Spot.

Papier, kein Orderpfad. --live verweigert mit Grund. Buch, Ratsche,
Risikovorfilter und Spiegelung nach Q:\\Handel_Journal\\liq_wand kommen aus
Handel/spur_buch.py.

Aufruf:
    python handeln.py --vorschau     # rechnen, nichts schreiben
    python handeln.py --papier       # Papierzyklus (Standard)
    python handeln.py --wachen       # Grenzen zeigen
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
# Reihenfolge: die eigene Spur ZULETZT, sonst gewinnt ein gleichnamiges
# Modul aus scanner/ (dieselbe Falle wie in den Spurtests).
for _p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

import spur_buch                                                   # noqa: E402
import moondev_daten as md                                         # noqa: E402
import okx                                                         # noqa: E402

# Test-Seam: None = echte Quelle (OKX, oeffentlich).
liq_quelle = None


def liquidationen(inst_familie, grenze=100):
    """Zwangsschluesse: [{"seite", "preis", "kontrakte", "usd", "ts"}, ...].

    Der Abruf liegt bewusst NICHT hier, sondern in moondev_daten - dort holt
    ihn schon die Spur moondev_liquidation, samt Umrechnung der Kontrakte in
    USD ueber ctVal. Zwei Abrufe derselben Zahlen waeren zwei Wahrheiten.
    """
    if liq_quelle is not None:
        return liq_quelle(inst_familie, grenze)
    return md.okx_liquidationen(uly=inst_familie, grenze=grenze)


def wand(liqs, spot, bandbreite_prozent):
    """(Preis, Kontrakte, Seite) des groessten Liquidationsbandes.

    Die Seite ist die des liquidierten Bestands: 'short' heisst, dort wurden
    Shorts glattgestellt - also Kaufdruck.
    """
    if not liqs or spot <= 0:
        return None
    band = spot * (bandbreite_prozent / 100.0)
    if band <= 0:
        return None
    masse = collections.defaultdict(float)
    seiten = collections.defaultdict(lambda: collections.defaultdict(float))
    for x in liqs:
        try:
            px = float(x.get("preis") or 0)
            sz = float(x.get("kontrakte") or 0)
        except (TypeError, ValueError):
            continue
        if px <= 0 or sz <= 0:
            continue
        schlussel = round(px / band) * band
        masse[schlussel] += sz
        seiten[schlussel][(x.get("seite") or "").lower()] += sz
    if not masse:
        return None
    preis, menge = max(masse.items(), key=lambda t: t[1])
    seite = max(seiten[preis].items(), key=lambda t: t[1])[0] or ""
    return preis, menge, seite


def quelle(w):
    """Spot und Liquidationen. Rueckgabe wie bei allen Buch-Spuren."""
    inst = w.get("instrument", "BTC-USDT-SWAP")
    familie = w.get("inst_familie", "BTC-USDT")
    daten, kurse, fehler = {}, {}, []
    try:
        spot = okx.letzter_kurs(inst)
    except Exception as e:                                         # noqa: BLE001
        return {}, {}, ["%s: Spot nicht abrufbar (%s)" % (inst, e)]
    if not spot:
        return {}, {}, ["%s: kein Spotkurs" % inst]
    try:
        liqs = liquidationen(familie, int(w.get("liq_grenze", 100)))
    except Exception as e:                                         # noqa: BLE001
        return {}, {}, ["%s: Liquidationen nicht abrufbar (%s)" % (familie, e)]
    daten[inst] = {"spot": spot, "liqs": liqs}
    kurse[inst] = spot
    return daten, kurse, fehler


def signal(d, w):
    """'long'/'short', wenn eine nahe Liquidationswand mit Masse da ist."""
    spot = float(d.get("spot") or 0)
    liqs = d.get("liqs") or []
    if spot <= 0 or len(liqs) < int(w.get("mindest_liquidationen", 20)):
        return None

    treffer = wand(liqs, spot, float(w.get("bandbreite_prozent", 0.25)))
    if not treffer:
        return None
    preis, menge, seite = treffer

    gesamt = 0.0
    for x in liqs:
        try:
            gesamt += float(x.get("kontrakte") or 0)
        except (TypeError, ValueError):
            pass
    if gesamt <= 0:
        return None
    if menge / gesamt < float(w.get("mindest_anteil", 0.30)):
        return None                       # zu verstreut - keine Wand

    abstand = abs(preis / spot - 1) * 100
    if abstand > float(w.get("max_abstand_prozent", 2.0)):
        return None                       # zu weit weg, um sie zu erreichen

    # Eine Liquidationswand ist ein BESCHLEUNIGER, kein Widerstand:
    # geschlossene Shorts = Kaufdruck, geschlossene Longs = Verkaufsdruck.
    #
    # Die Wand darf ein Stueck HINTER dem Kurs liegen (hinter_dem_spot_prozent).
    # Messung 24.09.2026 an 100 echten Zwangsschluessen: das groesste Band lag
    # 0,25 % UEBER dem Spot und bestand zu 100 % aus liquidierten LONGS - die
    # Verkaeufe liefen also durch dieses Band, der Kurs war schon darunter.
    # Genau das ist der Normalfall: ein Band entsteht dort, wo der Kurs gerade
    # war, nicht dort, wo er hinwill. Die strenge Fassung ("Wand muss vor dem
    # Kurs liegen") verlangte deshalb etwas, das der Datenstrom fast nie
    # hergibt - die Spur blieb tagelang stumm. Mit der Toleranz zaehlt der
    # Cluster als Beschleuniger, auch wenn er knapp hinter dem Kurs sitzt; die
    # 2-%-Grenze (max_abstand_prozent) deckelt weiterhin die Entfernung.
    toleranz = spot * float(w.get("hinter_dem_spot_prozent", 0.5)) / 100.0
    if seite == "short":
        return "long" if preis >= spot - toleranz else None
    if seite == "long":
        return "short" if preis <= spot + toleranz else None
    return None


def ziel(d, w):
    """Die Wand selbst als Zielpunkt - aber in die RICHTUNG des Einstiegs.

    GEMESSEN 04.10.2026 (43 Runden, -1,16 % Summe): 29 Ziel-Ausstiege
    brachten -0,16 % im Mittel, die 14 Stop-Ausstiege +0,24 %. Vertauscht.

    Ursache: `wand()` liefert den Preis des groessten Bandes, und das liegt
    je nach Marktlage OBER oder UNTER dem Spot. Der Einstieg folgt der Wand
    (bei Liquidierter-Seite 'short' geht die Spur long - die Wand liegt dann
    ueber dem Einstieg, das Ziel war korrekt; liegt die Wand unter dem Spot,
    ist es umgekehrt). Der alte Code nahm den Wandpreis blind als Ziel - bei
    der unteren Wand lag das Ziel dann UNTER dem Einstieg, und die Runde
    schloss mit minus.

    Regel: das Ziel muss in Handelsrichtung liegen. Liegt der Wandpreis
    falsch herum, wird das Ziel aus Abstand zum Einstieg gerechnet
    (ziel_r_vielfaches R), nicht aus dem Wandpreis - sonst bleibt es bei
    einem Ziel, das nie erreicht werden kann.
    """
    spot = float(d.get("spot") or 0)
    treffer = wand(d.get("liqs") or [], spot,
                   float(w.get("bandbreite_prozent", 0.25)))
    if not treffer:
        return None
    wandpreis = float(treffer[0])
    seite = (treffer[2] or "").lower()       # 'short' -> long, 'long' -> short
    # Zielrichtung: long heisst Ziel UEBER dem Einstieg
    long_ = (seite == "short")
    r = float(w.get("ziel_r_vielfaches", 2.0))
    if long_:
        # Die Wand ueber dem Spot: Einstieg darunter, Ziel = Wand.
        return wandpreis if wandpreis > spot else spot * (1 + r / 100.0)
    # Die Wand unter dem Spot: Einstieg darueber, Ziel = Wand.
    return wandpreis if wandpreis < spot else spot * (1 - r / 100.0)


def _live_erlaubt() -> bool:
    w = json.loads((Path(HIER) / "wachen.json").read_text(encoding="utf-8"))
    return bool(w.get("handel_erlaubt")) and bool(
        (w.get("freigabe") or {}).get("erfuellt"))


# Diese Spur hat KEINEN Orderaufruf. Seit dem Auftrag Max vom 21./22.09.2026
# stehen handel_erlaubt und freigabe.erfuellt aber in JEDER Spur auf true -
# _live_erlaubt() allein wuerde '--live' also durchlassen und ein Buch mit
# modus=live OHNE Boersenauftrag schreiben. Genau das war der Fehler, der am
# 21.09.2026 bei xperp und scanner auffiel ("Buch war Fiktion"): die Positionen
# standen nur im Buch. Deshalb entscheidet hier der ORDERWEG, nicht der Schalter.
LIVE_ORDERWEG = False


def live_gate(modus):
    """(modus, meldung): 'live' wird ohne Orderweg IMMER zu Papier.

    Reine Funktion - kein Dateizugriff, damit sie ohne Nebenwirkung pruefbar ist
    (ein Test darf nie in ein echtes Buch schreiben).
    """
    if modus != "live":
        return modus, None
    if not LIVE_ORDERWEG:
        return "papier", ("--live verweigert: diese Spur hat keinen Orderaufruf "
                          "(Papierbuch auf dem Liquidations-Signal). Ein Buch "
                          "mit modus=live ohne Boersenauftrag waere Fiktion.")
    if not _live_erlaubt():
        return "papier", ("--live verweigert: handel_erlaubt ist false und "
                          "freigabe.erfuellt ist nicht gesetzt - Handelsregeln "
                          "Punkt 3 (scharf schalten von Hand).")
    return "live", None


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau", help="nur rechnen, nichts schreiben")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier", help="Papierbuch (Standard)")
    g.add_argument("--live", action="store_const", dest="modus", const="live",
                   help="verweigert: diese Spur hat keinen Live-Zweig")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen", help="nur den Wachenstand zeigen")
    a = p.parse_args()
    modus = a.modus or "papier"
    modus, meldung = live_gate(modus)
    if meldung:
        print(meldung)
    return spur_buch.zyklus(HIER, quelle, signal, modus,
                            ereignis_name="handel/liq_wand",
                            ziel=ziel)


if __name__ == "__main__":
    raise SystemExit(main())
