"""Stop-DECKUNG pruefen und ergaenzen (Buch gegen Boerse, dritte Stufe).

ANLASS (gemessen 02.10.2026, xperp): `bueche_geister_aus` und
`bueche_groessen_abgleichen` fragen beide, OB eine Position an der Boerse ist
und OB die Kontraktzahl stimmt. Sie fragen nicht, ob die POSITION GESCHUETZT
ist - und `_stop_vorhanden` (handeln.py) sagt bei Existenz EINER Schutz-Order
"ja", ohne die Menge zu zaehlen.

Gemessener Fall ZEC-USD_UM_XPERP-310530:

    Position an der Boerse        145 Kontrakte
    sechs OCO-Stops an der Boerse  45 + 11 + 1 + 29 + 12 + 28 = 126
    ungedeckt                                    19 Kontrakte

19 Kontrakte laufen bis zur Liquidation, wenn der Rechner ausfaellt - und der
faellt aus (Kernel-Power 41, Wissen/Hardware.md). Das ist genau der Zustand,
den die beiden anderen Funktionen nicht sehen koennen.

Zwei Grenzen, die dieses Werkzeug einhaelt:

1. Ein Stop, der auf der FALSCHEN Seite liegt, wird nicht gestellt. Ein
   long-Stop muss UNTER dem Kurs liegen, sonst verkauft er sofort zum
   Markt. Ein Stop unterhalb `liqPx` ist ebenfalls wertlos: die Liquidation
   kommt vorher. Beide Faelle werden verweigert und gemeldet, statt eine
   scheinbare Sicherung zu bauen.
2. Das Werkzeug stellt NUR die fehlende Menge. Bestehende Schutzaeufege werden
   nie angefasst, nie storniert und nie nachgezogen (T-278: der engere Stop
   feuert zuerst und zieht den Schutz unbemerkt enger).

Vorschau ist der Standard, sie schreibt nichts und stellt keine Order. Erst
`--anwenden` schickt die Order - und nur, wenn der Preis die beiden Grenzen
oben besteht. Ohne `--stop` im Anwendungsfall wird NICHTS gestellt: das
Werkzeug erfindet keinen Preis, es zeigt die Luecke und den erlaubten Korridor.

Aufruf aus dem xperp-Ordner:

    ../scanner/.venv/Scripts/python.exe stopdeckung.py
    ../scanner/.venv/Scripts/python.exe stopdeckung.py --anwenden --stop 1289.63
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Eigene Spur ZULETZT einfuegen: scanner/ hat ebenfalls ein handeln.py.
HIER = os.path.dirname(os.path.abspath(__file__))


def _lade():
    """handeln + wachen_xperp, VERZOEGERT.

    Grund: `handeln.py` ruft seit dem 05.10.2026 (T-362) `deckung()` und
    `tote_stops()` im Zyklus auf, also importiert diese Datei - und importierte
    hier schon `handeln`. Das ist ein Zirkel: beim Laden von `handeln` laeuft
    der Rumpf, trifft `import stopdeckung`, und dessen `import handeln` holt
    eine HALBE fertige Instanz.

    Der Umweg ist der Nachweis, kein Umweg: die Rechnung
    (`schutz_auftraege`/`deckung`/`tote_stops`/`preis_pruefbar`) braucht nur
    `okxf`. `handeln` und `wachen_xperp` werden erst in `main()` gebraucht,
    also erst dort geladen.
    """
    # Reihenfolge ist Absicht und muss UNBEDINGT sein: `import handeln` nimmt
    # den ersten Treffer, und `Agenten/Handel/scanner/handeln.py` heisst genauso
    # wie `Agenten/Handel/xperp/handeln.py`. Ohne das erzwungene Einfuegen
    # bleibt der Pfad des Werkzeuglaufs (xperp) an Position 0, `scanner/`
    # rutscht davor und der Guard laeuft mit der FALSCHEN Datei auf.
    # Gemessen 05.10.2026.
    for p in (os.path.join(os.path.dirname(HIER), "scanner"),
              os.path.dirname(HIER), HIER):
        sys.path.insert(0, p)
    import okxf
    import handeln as h
    import wachen_xperp as wx
    assert os.path.dirname(os.path.abspath(h.__file__)) == HIER, \
        "falsches handeln.py geladen: %s" % h.__file__
    return okxf, h, wx


def _okxf():
    """Das Borsenmodul, mit der Testnaht als Modulattribut.

    Die 21 Tests in `tests/test_stopdeckung.py` setzen `stopdeckung.okxf =
    attrappe`. Deshalb wird ZUERST das Modulattribut geprueft und erst danach
    geladen - sonst muessten 21 Tests umgeschrieben werden, nur weil der Import
    spaeter kommt. Gelesen wird aus `globals()`, nicht aus einem Cache: so sieht
    ein Test die Attrappe auch nach jedem anderen Test.
    """
    attrappe = globals().get("okxf")
    if attrappe is not None:
        return attrappe
    return _lade()[0]


def __getattr__(name):
    """`stopdeckung.okxf` lesbar halten, ohne es beim Import zu erzwingen.

    PEP 562: diese Funktion wird nur befragt, wenn das Attribut NICHT im
    Modulraum existiert. Sobald ein Test `sd.okxf = attrappe` gesetzt hat, ist
    es ein echtes Attribut und der Name wird nie wieder hierher kommen.
    """
    if name == "okxf":
        return _lade()[0]
    raise AttributeError("module %r hat kein Attribut %r" % (__name__, name))


# Rundung, nicht Handgriff: OKX rechnet die Kontraktzahl in Schritten.
_MENGE_TOLERANZ = 1e-6

# Ab dieser relativen Abweichung der Stueckzahl gilt der Bestand als veraendert.
_PREIS_TOLERANZ = 0.0015


def schutz_auftraege(inst, seite):
    """Die offenen Schutz-Auftraege einer Position, mit ihrer Menge.

    Nur was tatsaechlich schuetzt, zaehlt:
      * `reduceOnly=true` - ohne das waere es eine Wette, kein Schutz,
      * eine Ausloesung in BEIDEN Richtungen ist bei OKX nicht moeglich, also
        zaehlt `slTriggerPx` ODER `tpTriggerPx` (der Trailing traegt kein
        `slTriggerPx`, siehe okxf.ist_schutz_stop),
      * die Seite muss GEGEN die Position laufen.

    Der Filter ist derselbe wie `okxf.ist_schutz_stop`, aber mit der Menge -
    `_stop_vorhanden` wirft die Menge weg und genau daran scheitert es.
    """
    okxf = _okxf()
    gegenteil = "sell" if seite == "long" else "buy"
    raus = []
    for a in okxf.schutz_stops(inst) or []:
        if str(a.get("reduceOnly")).lower() not in ("true", "1"):
            continue
        if a.get("side") != gegenteil:
            continue
        # Nur ein STOP schuetzt. Ein reiner Take-Profit (tpTriggerPx ohne
        # slTriggerPx) loest nur im Gewinn aus - bis 11.10.2026 zaehlte er mit
        # und ETH meldete "alle geschuetzt" bei 203 von 884 Kontrakten ohne
        # Stop (442 davon hingen an einem reinen Ziel-Auftrag).
        if not any(str(a.get(f) or "").strip() for f in
                   ("slTriggerPx", "moveTriggerPx", "trailingTriggerPx")):
            continue
        try:
            menge = abs(float(a.get("sz") or 0.0))
        except (TypeError, ValueError):
            continue
        if menge <= _MENGE_TOLERANZ:
            continue
        raus.append({
            "ordType": a.get("ordType"),
            "menge": menge,
            "stop": a.get("slTriggerPx") or a.get("trailingTriggerPx"),
            "ziel": a.get("tpTriggerPx"),
        })
    return raus


def deckung(p, roh):
    """Wie viele Kontrakte der Buchposition sind an der Boerse geschuetzt?"""
    auftraege = schutz_auftraege(p["inst"], p.get("seite") or "long")
    gedeckt = sum(a["menge"] for a in auftraege)
    # Die Buchgroesse kann hinter der Boerse liegen (Handgriff). Gemessen wird
    # deshalb GEGEN die Boerse, nicht gegen das Buch: was die Boerse haelt und
    # nicht schuetzt, ist ungeschuetzt - unabhaengig davon, was das Buch sagt.
    soll = abs(float(p.get("kontrakte") or 0.0))
    an_der_boerse = abs(float((roh.get(p["inst"]) or {}).get("pos") or 0.0))
    if an_der_boerse > soll:
        soll = an_der_boerse
    return {"auftraege": auftraege, "gedeckt": gedeckt, "soll": soll,
            "fehlt": max(0.0, soll - gedeckt)}


def preis_pruefbar(inst, seite, stop, liq):
    """Darf dieser Stop ueberhaupt gestellt werden? Gibt (ok, grund) zurueck."""
    try:
        stop = float(stop)
    except (TypeError, ValueError):
        return False, "kein lesbarer Preis (%r)" % (stop,)
    if stop <= 0:
        return False, "Preis %s ist nicht positiv" % stop
    okxf = _okxf()
    try:
        kurs = float(okxf.letzter_kurs(inst))
    except Exception as e:                                      # noqa: BLE001
        return False, "Kurs nicht abrufbar (%s) - es wird nichts gestellt" % e
    if seite == "long" and stop >= kurs:
        return False, ("Stop %.2f liegt auf/ueber dem Kurs %.2f - er wuerde "
                       "sofort ausloesen; das ist kein Schutz" % (stop, kurs))
    if seite == "short" and stop <= kurs:
        return False, ("Stop %.2f liegt auf/unter dem Kurs %.2f - er wuerde "
                       "sofort ausloesen; das ist kein Schutz" % (stop, kurs))
    if liq is not None and liq > 0:
        if seite == "long" and stop <= liq:
            return False, ("Stop %.2f liegt UNTER der Liquidation %.2f - die "
                           "Liquidation kommt vorher, der Stop ist tot"
                           % (stop, liq))
        if seite == "short" and stop >= liq:
            return False, ("Stop %.2f liegt UEBER der Liquidation %.2f - die "
                           "Liquidation kommt vorher, der Stop ist tot"
                           % (stop, liq))
    return True, "Stop %.2f liegt %s vom Kurs %.2f, %s der Liquidation %.2f" % (
        stop,
        "unter" if seite == "long" else "ueber",
        kurs,
        "ueber" if seite == "long" else "unter",
        liq if liq is not None else float("nan"))


def tote_stops(inst, seite, liq):
    """Schutzaeufege, die zwar liegen, aber nie feuern koennen."""
    raus = []
    if not liq or liq <= 0:
        return raus
    for a in schutz_auftraege(inst, seite):
        try:
            p = float(a["stop"])
        except (TypeError, ValueError):
            continue
        tot = (seite == "long" and p <= liq) or (seite == "short" and p >= liq)
        if tot:
            raus.append(dict(a, liq=float(liq)))
    return raus


def pruefe(z, still=False):
    """Alle Live-Positionen des Buchs gegen die Boerse. Rein lesend."""
    okxf = _okxf()
    try:
        roh = {p["instId"]: p for p in okxf.positionen()}
    except Exception as e:                                      # noqa: BLE001
        print("Boersenfrage fehlgeschlagen (%s) - es wird nichts gemacht" % e)
        return None
    befunde = []
    for p in z.get("positionen") or []:
        if p.get("modus") != "live":
            continue
        inst = p.get("inst")
        if inst not in roh:
            continue                      # das ist die Geisterpruefung, nicht unsere
        d = deckung(p, roh)
        liq = None
        try:
            liq = float(roh[inst].get("liqPx") or 0.0) or None
        except (TypeError, ValueError):
            liq = None
        if d["fehlt"] <= _MENGE_TOLERANZ and not tote_stops(inst, p.get("seite") or "long", liq):
            if not still:
                print("  %-26s %6.1f Kontrakte, alle geschuetzt"
                      % (inst, d["soll"]))
            continue
        befunde.append({"position": p, "deckung": d, "liq": liq})
        if still:
            continue
        print("  %-26s %6.1f Kontrakte, geschuetzt %6.1f -> UNGESCHUETZT %.1f"
              % (inst, d["soll"], d["gedeckt"], d["fehlt"]))
        for a in d["auftraege"]:
            print("      %-18s %8.1f  Stop %s  Ziel %s"
                  % (a["ordType"], a["menge"], a["stop"], a["ziel"]))
        for t in tote_stops(inst, p.get("seite") or "long", liq):
            print("      TOT: %-18s %8.1f  Stop %s liegt an/unter der "
                  "Liquidation %.2f" % (t["ordType"], t["menge"], t["stop"], t["liq"]))
    return befunde


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--anwenden", action="store_true",
                   help="die fehlende Deckung als Stop nachsetzen (echte Order)")
    p.add_argument("--stop", type=float, default=None,
                   help="Preis fuer den nachgesetzten Stop. Ohne diesen "
                        "Schalter stellt --anwenden NICHTS - das Werkzeug "
                        "erfindet keinen Schutzpreis")
    a = p.parse_args()

    _, h, wx = _lade()
    with open(wx.WACHEN, encoding="utf-8") as fh:
        w = json.load(fh)
    z = h.lade_zustand()
    print("Buch: %d Position(en), modus=%s | live davon: %d"
          % (len(z.get("positionen") or []), z.get("modus"),
             sum(1 for x in z.get("positionen") or [] if x.get("modus") == "live")))
    print("\n=== Stop-Deckung (Buch gegen Boerse) ===")
    befunde = pruefe(z, still=a.anwenden)
    if befunde is None:
        return 2
    if not befunde:
        print("\nAlles gedeckt - nichts nachzusetzen.")
        return 0

    if not a.anwenden:
        print("\nVORSCHAU: %d Position(en) mit Luecke. Keine Order, kein "
              "Schreibzugriff." % len(befunde))
        print("Naechster Schritt: --anwenden --stop <preis> (der Preis muss "
              "unter dem Kurs und ueber der Liquidation liegen).")
        return 0

    if a.stop is None:
        print("\n--anwenden OHNE --stop: es wird nichts gestellt. Das Werkzeug "
              "raten keinen Schutzpreis.\nDie Luecken sind oben genannt - bitte "
              "einen Preis je Position nennen.")
        return 0

    print("\n=== ANWENDEN ===")
    bak = h.ZUSTAND + ".bak-%s" % datetime.now().strftime("%Y%m%d-%H%M%S")
    import shutil
    shutil.copy2(h.ZUSTAND, bak)
    gestellt = 0
    for b in befunde:
        p_ = b["position"]
        inst = p_["inst"]
        seite = p_.get("seite") or "long"
        fehlt = b["deckung"]["fehlt"]
        if fehlt <= _MENGE_TOLERANZ:
            continue
        ok, grund = preis_pruefbar(inst, seite, a.stop, b["liq"])
        if not ok:
            print("  %-26s nicht gestellt: %s" % (inst, grund))
            continue
        try:
            d = _okxf().schutz_stop_setzen(inst, seite, fehlt, a.stop)
        except Exception as e:                                  # noqa: BLE001
            print("  %-26s FEHLGESCHLAGEN (%s) - die Position bleibt teilweise "
                  "ungeschuetzt" % (inst, e))
            continue
        algo = d.get("algoId") or d.get("algoIdOrds") or ""
        print("  %-26s %.1f Kontrakte nachgeschuetzt bei %s (algoId %s)"
              % (inst, fehlt, a.stop, algo))
        print("      %s" % grund)
        p_["stop_nachgesetzt"] = {"menge": fehlt, "preis": a.stop,
                                  "algoId": algo,
                                  "zeit": datetime.now().isoformat(timespec="seconds")}
        gestellt += 1

    if not gestellt:
        print("\nKeine Order abgesetzt. Buch unveraendert (nur die Sicherung %s)"
              % os.path.basename(bak))
        return 0
    h.schreibe_zustand(z)
    ziel = w.get("journal_zweitziel")
    if ziel:
        ok, info = wx.spiegele_journal([h.ZUSTAND], ziel)
        print("Spiegelung nach %s: %s" % (ziel, "ok" if ok else "NICHT ok (%s)" % info))
    print("\n%d Position(en) nachgeschuetzt. Sicherung: %s" % (gestellt, os.path.basename(bak)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())