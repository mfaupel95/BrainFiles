"""Vierte Spur: ORB Index-CFD ueber OANDA, gerichtet (long/short), gehebelt
(Hebel faellt aus der Positionsrechnung), in EUR.

Aufruf (aus diesem Ordner):
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --vorschau
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --papier
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --live
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --wachen

Neun Sperren muessen ALLE offen sein, sonst laeuft trotz --live nur Papier
(Liste in live_sperren, Task 11). Ausstiege laufen NIE durch das
Freigabefenster - ein Stop muss auch greifen, wenn niemand davorsitzt.

Ausstiegshaelfte (Task 9): Zustand, Journal, pruefe_ausstiege, flach_stellen
(Notausstieg), --wachen. Einstiegshaelfte (Task 10): live_range, breakout_signal,
positionsgroesse (Hebel faellt aus der Rechnung, wird nur gedeckelt),
pruefe_einstieg, vollstaendiger Zyklus in lauf(), --vorschau. Offen fuer Task 11:
das Live-Gate (live_sperren + Freigabefenster) - bis dahin handelt jeder Lauf
Papier, auch --live, und pruefe_einstieg wird direkt gerufen.

Kostenmodell (Fix-Runde 1): genau EIN Spread je Runde, deckungsgleich mit
backtest.mit_kosten. Einstieg zum Mid-Schluss der Bruchkerze (kein
Preisaufschlag); der halbe Einstiegs-Spread steht nur in der eur-Spalte des
einstieg-Journals, der halbe Ausstiegs-Spread nur in _erloes_eur. Ausstiege
werden zu Mid ((bid+ask)/2) bepreist, nicht zu bid/ask.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

import oanda
import session as sess
import wachen_orb as wp

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"
ZUSTAND = HIER / "zustand.json"
JOURNAL = HIER / "handelsjournal.csv"
FREIGABE_ZEITLIMIT_S = 120


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wachen():
    return json.loads(WACHEN.read_text("utf-8"))


def lade_zustand():
    if ZUSTAND.exists():
        return json.loads(ZUSTAND.read_text("utf-8"))
    return {"positionen": [], "letzte_stops": {}, "letzter_lauf": None, "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    ZUSTAND.write_text(json.dumps(z, ensure_ascii=False, indent=2), "utf-8")


def journal(*felder):
    neu = not JOURNAL.exists()
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        if neu:
            s.writerow(["zeit", "modus", "aktion", "inst", "richtung", "preis",
                        "eur", "units", "stop", "ziel", "grund"])
        s.writerow(felder)


def _inst_konf(w):
    return w["instrumente"][w["instrument_aktiv"]]


def _punkt_wert(w):
    return _inst_konf(w)["punkt_wert_eur"]


def _halber_spread_eur(w, units):
    return 0.5 * _inst_konf(w)["spread_punkte"] * _punkt_wert(w) * units


def _wert_eur(p, kurs, w):
    """Realisierter Wert der Position bei kurs, in EUR, VOR Spread."""
    diff = (kurs - p["einstieg"]) if p["richtung"] == "long" else (p["einstieg"] - kurs)
    return diff * _punkt_wert(w) * p["units"]


def _erloes_eur(p, kurs, w):
    """Realisierter G/V der Position bei kurs, in EUR, NACH Abzug des halben
    Spreads auf der Ausstiegsseite. Einzige Quelle fuer die Ausstiegsrechnung -
    _schliesse ruft nur hier."""
    return _wert_eur(p, kurs, w) - _halber_spread_eur(w, p["units"])


def _signierte_units(p):
    return p["units"] if p["richtung"] == "long" else -p["units"]


def _mid(preis):
    """Ausstiegskurs = Mid, wie im Backtest (backtest.mit_kosten rechnet
    Mid-zu-Mid). Der einzige Spread je Runde steht als Aufschlag in der
    einstieg-eur-Spalte plus dem _halber_spread_eur-Abzug in _erloes_eur -
    kein zusaetzlicher bid/ask-Abzug beim Ausstieg."""
    return (preis["bid"] + preis["ask"]) / 2.0


def _schliesse(p, kurs, w, live, grund, z):
    """Eine Position schliessen. Gibt True zurueck, wenn sie weg ist."""
    if live:
        try:
            oanda.markt_order(_inst_konf(w)["oanda"],
                              -_signierte_units(p), echt=True, live=True)
        except Exception as e:  # noqa: BLE001
            print("  Ausstieg %s fehlgeschlagen: %s" % (p["inst"], e), file=sys.stderr)
            return False
    gv = _erloes_eur(p, kurs, w)
    print("  ZU  %-10s %s @ %-10.5g (%s)  G/V %+.2f EUR"
          % (p["inst"], p["richtung"], kurs, grund, gv))
    journal(_jetzt(), "live" if live else "papier", "ausstieg", p["inst"],
            p["richtung"], "%.5f" % kurs, "%.2f" % (p["risiko_eur"] + gv),
            "%.4f" % p["units"], "", "", grund)
    if grund == "stop":
        z["letzte_stops"][p["inst"]] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return True


def pruefe_ausstiege(z, w, live):
    """Je offene Position: Stop / Ziel / Zwangsschluss. Ausstiege laufen nie
    durch das Freigabefenster. Zwangsschluss haengt an DER Position: sie schliesst
    spaetestens zum Cash-Close IHRES Eroeffnungstags - eine stehengebliebene
    Position (verpasster Lauf) geht damit im naechsten Lauf sofort zu, nie ueber
    Nacht (SPEC: kein Halten ueber Nacht)."""
    behalten = []
    jetzt = datetime.now(timezone.utc)
    ik = _inst_konf(w)
    for p in z["positionen"]:
        preis = oanda.preis(ik["oanda"], live)
        kurs = _mid(preis)                       # Touch-Vergleich gegen Mid, wie im Backtest
        grund = None
        if p["richtung"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif kurs <= p["ziel"]:
                grund = "ziel"
        if grund is None and jetzt >= sess.zwangsschluss(ik, date.fromisoformat(p["eroeffnet"])):
            grund = "zwangsschluss"
        if not grund or not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def flach_stellen(z, w, live, grund):
    """Alle offenen Positionen sofort schliessen - Notausstieg fuer den
    Kill-Switch (Ruecklauf >= Grenze) und den alten Herzschlag."""
    behalten = []
    ik = _inst_konf(w)
    for p in z["positionen"]:
        preis = oanda.preis(ik["oanda"], live)
        kurs = _mid(preis)
        if not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def positionsgroesse(einstieg, stop, w, faktor=1.0):
    """(units, hebel). units aus Risiko/Stopabstand, abgerundet auf ein
    Vielfaches von minimumTradeSize. Hebel ist ERGEBNIS der Rechnung, nie
    Eingabe: er wird nur gegen hebel_deckel geprueft und, wenn noetig, die
    Position so weit geschrumpft, dass der Deckel haelt (units bleibt ein
    Vielfaches von mts). Passt nicht einmal eine mts-Einheit in den Deckel,
    ist 0 das richtige Ergebnis (SPEC.md 34)."""
    konf = _inst_konf(w)
    stop_abstand = abs(einstieg - stop)
    if stop_abstand <= 0:
        return 0.0, 0.0
    pw = konf["punkt_wert_eur"]
    risiko = w["risiko_pro_trade_eur"] * faktor
    roh_units = risiko / (stop_abstand * pw)
    mts = oanda.instrument_details(konf["oanda"])["minimumTradeSize"]
    units = (int(roh_units / mts) * mts) if mts else roh_units
    positionswert = units * einstieg * pw
    marge = max(oanda.konto_marge_frei(), 1e-6)
    hebel = positionswert / marge
    if hebel > w["hebel_deckel"]:
        max_wert = w["hebel_deckel"] * marge
        units = ((int((max_wert / (einstieg * pw)) / mts) * mts) if mts
                 else max_wert / (einstieg * pw))
        positionswert = units * einstieg * pw
        hebel = positionswert / marge
    return units, hebel


def live_range(w, tag):
    """Opening Range = Hoch/Tief der ersten zwei ABGESCHLOSSENEN M15 im
    Session-Fenster von tag. Weniger als zwei -> None (keine Range, kein
    Einstieg)."""
    konf = _inst_konf(w)
    start, ende = sess.opening_range_fenster(konf, tag)
    ks = [k for k in oanda.kerzen(konf["oanda"], von=start, bis=ende) if k["complete"]]
    if len(ks) < 2:
        return None
    zwei = ks[:2]
    return max(k["h"] for k in zwei), min(k["l"] for k in zwei)


def breakout_signal(w, hoch, tief):
    """Erste abgeschlossene M15 seit Range-Ende, deren Schluss die Range
    verlaesst: > hoch -> ("long", schluss), < tief -> ("short", schluss).
    None, wenn keine solche Kerze - oder keine mehr vor letzter_einstieg."""
    konf = _inst_konf(w)
    heute = sess.handelstag(datetime.now(timezone.utc), konf["zone"])
    _, range_ende = sess.opening_range_fenster(konf, heute)
    letzt = sess.letzter_einstieg(konf, heute, w["letzter_einstieg_min_vor_schluss"])
    ks = [k for k in oanda.kerzen(konf["oanda"], von=range_ende,
                                  bis=datetime.now(timezone.utc))
          if k["complete"] and k["zeit"] <= letzt]
    for k in ks:
        if k["c"] > hoch:
            return "long", k["c"]
        if k["c"] < tief:
            return "short", k["c"]
    return None


def _schon_gehandelt_heute(z, w):
    """Eine Session je Handelstag: True, wenn schon eine Position von heute
    offen ist ODER heute ein einstieg fuer dieses Instrument im Journal steht."""
    konf = _inst_konf(w)
    heute = sess.handelstag(datetime.now(timezone.utc), konf["zone"]).isoformat()
    if any(p.get("eroeffnet") == heute for p in z["positionen"]):
        return True
    if not JOURNAL.exists():
        return False
    with JOURNAL.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r["aktion"] == "einstieg" and r["inst"] == w["instrument_aktiv"]
                    and r["zeit"][:10] == heute):
                return True
    return False


def _einstieg_stop_ziel(bruch, richtung, hoch, tief, w, key):
    """Aus dem Breakout die drei Preise. Einstieg = bruch, der Mid-Schluss der
    Bruchkerze - KEIN Preisaufschlag. Der Einstiegs-Spread (SPEC.md 165
    "Einstieg mit Aufschlag") lebt allein in der eur-Spalte des Journals
    (+ spread_auf); der Ausstiegs-Spread allein in _erloes_eur. Zusammen genau
    ein Spread je Runde, gleiches Kostenmodell wie backtest.mit_kosten.
    Stop = die verlassene Range-Seite. Ziel je ziel_modus. Von pruefe_einstieg
    und _zeige_vorschau geteilt, damit Vorschau und Handel nie auseinanderlaufen."""
    einstieg = bruch
    stop = tief if richtung == "long" else hoch
    if w["ziel_modus"] == "r_vielfaches":
        spanne = w["ziel_k"] * (hoch - tief)
    else:
        spanne = w["ziel_punkte"][key]
    ziel = einstieg + spanne if richtung == "long" else einstieg - spanne
    return einstieg, stop, ziel


def pruefe_einstieg(z, w, live, faktor=1.0):
    """Hoechstens EINE offene Position. Kein Einstieg wenn: schon eine offen /
    heute schon gehandelt / keine vollstaendige Range / Range ausserhalb Filter
    / kein Breakout / nach letzter_einstieg / Positionsgroesse 0.

    Einstiegskurs (Papier) = Mid-Schluss der Bruchkerze, ohne Aufschlag auf den
    Preis. Der halbe Einstiegs-Spread steht nur in der eur-Spalte des
    einstieg-Journals (+ spread_auf), der halbe Ausstiegs-Spread nur in
    _erloes_eur - zusammen genau ein Spread je Runde, deckungsgleich mit
    backtest.mit_kosten. Live ersetzt der echte fillpreis die Schaetzung."""
    if z["positionen"] or _schon_gehandelt_heute(z, w):
        return
    konf = _inst_konf(w)
    heute = sess.handelstag(datetime.now(timezone.utc), konf["zone"])
    hr = live_range(w, heute)
    if hr is None:
        print("  keine vollstaendige Opening Range - kein Einstieg.")
        return
    hoch, tief = hr
    key = w["instrument_aktiv"]
    if not wp.range_ok(hoch - tief, key, w):
        print("  Range %.1f Pkt ausserhalb [%s, %s] - Session ausgesetzt."
              % (hoch - tief, w["mindest_range_punkte"][key], w["max_range_punkte"][key]))
        return
    sig = breakout_signal(w, hoch, tief)
    if sig is None:
        print("  kein Breakout (oder nach letztem Einstieg) - kein Einstieg.")
        return
    richtung, bruch = sig
    einstieg, stop, ziel = _einstieg_stop_ziel(bruch, richtung, hoch, tief, w, key)

    units, hebel = positionsgroesse(einstieg, stop, w, faktor)
    if units <= 0:
        print("  Positionsgroesse 0 - kein Einstieg.")
        return

    order_id = fuellpreis = None
    if live:
        signiert = units if richtung == "long" else -units
        try:
            order_id, fuellpreis = oanda.markt_order(konf["oanda"], signiert,
                                                     echt=True, live=True)
        except Exception as e:  # noqa: BLE001
            print("  Einstieg %s fehlgeschlagen: %s" % (key, e), file=sys.stderr)
            return
        if fuellpreis:
            einstieg = fuellpreis           # echter Fill-Preis ersetzt die Schaetzung

    spread_auf = _halber_spread_eur(w, units)
    z["positionen"].append({
        "inst": key, "richtung": richtung, "einstieg": einstieg, "stop": stop,
        "ziel": ziel, "units": units, "risiko_eur": w["risiko_pro_trade_eur"] * faktor,
        "eroeffnet": heute.isoformat(), "order_id": order_id})
    print("  AUF %-10s %s @ %-10.5g  Stop %-10.5g  Ziel %-10.5g  %.4f units  Hebel %.1f"
          % (key, richtung, einstieg, stop, ziel, units, hebel))
    journal(_jetzt(), "live" if live else "papier", "einstieg", key, richtung,
            "%.5f" % einstieg, "%.2f" % (w["risiko_pro_trade_eur"] * faktor + spread_auf),
            "%.4f" % units, "%.5f" % stop, "%.5f" % ziel, "hebel %.1f" % hebel)


def _spiegeln(w):
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], w.get("journal_zweitziel"))
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))
    return ok


def _zeige_vorschau(z, w, s):
    konf = _inst_konf(w)
    key = w["instrument_aktiv"]
    heute = sess.handelstag(datetime.now(timezone.utc), konf["zone"])
    hr = live_range(w, heute)
    if hr is None:
        print("  Opening Range noch nicht vollstaendig (zwei abgeschlossene M15).")
    else:
        hoch, tief = hr
        print("  Opening Range %.6g - %.6g  (%.1f Pkt, Filter [%s, %s])"
              % (tief, hoch, hoch - tief,
                 w["mindest_range_punkte"][key], w["max_range_punkte"][key]))
        if not wp.range_ok(hoch - tief, key, w):
            print("  -> Range ausserhalb Filter - Session ausgesetzt.")
        else:
            sig = breakout_signal(w, hoch, tief)
            if sig is None:
                print("  kein Breakout seit Range-Ende (oder nach letztem Einstieg).")
            else:
                richtung, bruch = sig
                einstieg, stop, ziel = _einstieg_stop_ziel(bruch, richtung, hoch, tief, w, key)
                units, hebel = positionsgroesse(einstieg, stop, w, s["groessenfaktor"])
                print("  Signal %s  Einstieg %.6g  Stop %.6g  Ziel %.6g  ->  %.4f units  Hebel %.1f"
                      % (richtung, einstieg, stop, ziel, units, hebel))
    print("\nOffener Bestand: %d Position(en)" % len(z["positionen"]))
    print("Live-Gate (Sperren + Freigabefenster): kommt in Task 11.")


def sitzung_da():
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


def zeige_wachen(w):
    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)
    print("=== Wachen-Status ORB  %s ===" % _jetzt())
    print("  Freigabe voll (Backtest+Papier)  %s   (Papier %d Sessions / %.1f Wochen, EV %s)"
          % (s["freigabe_voll"], s["papier_sessions"], s["papier_wochen"],
             "n/a" if s["rollierender_ev"] is None else "%+.3f" % s["rollierender_ev"]))
    print("  Ruecklauf  %.2f EUR von Hoechst %.2f  -> Faktor %.2f%s"
          % (s["ruecklauf_eur"], s["hoechststand_eur"], s["groessenfaktor"],
             "   >>> KILL" if s["kill"] else ""))
    print("  Herzschlag frisch  %s  (%s min, Grenze %d)"
          % (s["herzschlag_frisch"],
             "?" if s["herzschlag_alter_min"] is None else "%.0f" % s["herzschlag_alter_min"],
             w.get("herzschlag_max_minuten", 45)))
    print("  Journal-Zweitziel  %s" % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], w.get("journal_zweitziel"))
    print("  Journal ausser Haus  %s (%s)" % ("ok" if ok else "--", info))
    if s["kill"] and wp.sperre_zu("Wochenlauf: Kill-Switch, Ruecklauf %.2f EUR" % s["ruecklauf_eur"]):
        print("  -> handel_erlaubt auf false.")
    if s["ev_negativ"] and wp.sperre_zu("Wochenlauf: rollierender EV %.3f < 0" % s["rollierender_ev"]):
        print("  -> handel_erlaubt auf false.")


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    w = _wachen()
    if modus == "wachen":            # reines Nachsehen - laeuft auch ohne aktives Instrument
        zeige_wachen(w)
        return
    if not w.get("instrument_aktiv"):
        print("instrument_aktiv ist null - Backtest (Task 7) hat noch kein Urteil. Kein Lauf.")
        return

    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)

    # --- Live-Gate: Task 11 ------------------------------------------------
    # Hier haengt Task 11 live_sperren + das Freigabefenster ein. Bis dahin
    # laeuft jeder Lauf auf Papier - auch --live - und pruefe_einstieg wird
    # direkt gerufen.
    live = False
    if modus == "live":
        print("--live: Sperrenpruefung und Freigabefenster kommen in Task 11 -")
        print("        dieser Lauf handelt Papier.")

    z["modus"] = "live" if live else "papier"
    faktor = s["groessenfaktor"]
    print("=== ORB handeln (%s) | Instrument %s | %s ==="
          % ("LIVE" if live else "Papier", w["instrument_aktiv"], _jetzt()))

    if modus == "vorschau":
        _zeige_vorschau(z, w, s)
        return

    # Kill-Switch (Ruecklauf >= Grenze): alles zu, Sperre zu, Schluss.
    if s["kill"]:
        print("- KILL-SWITCH: Ruecklauf %.2f EUR >= %g -> Notausstieg + Sperre -"
              % (s["ruecklauf_eur"], w["kill_switch_gesamt_eur"]))
        flach_stellen(z, w, live, "kill_switch")
        if wp.sperre_zu("kill_switch: Ruecklauf %.2f EUR" % s["ruecklauf_eur"]):
            print("  wachen.json handel_erlaubt -> false")
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):     # Notausstieg + Sperre: gerade jetzt zaehlt die Kopie ausser Haus
            _spiegeln(w)
        return

    # Herzschlag alt: alles zu, dieser Lauf handelt nicht mehr.
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser Lauf -"
              % ("?" if s["herzschlag_alter_min"] is None
                 else "%.0f" % s["herzschlag_alter_min"],
                 w.get("herzschlag_max_minuten", 45)))
        flach_stellen(z, w, live, "herzschlag_alt")
        z["modus"] = "papier"
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    # Ausstiege zuerst - sie laufen NIE durch das Freigabefenster: ein Stop
    # muss auch greifen, wenn niemand davorsitzt.
    print("- Ausstiege -")
    pruefe_ausstiege(z, w, live)

    # Einstieg. Task 11 haengt das Freigabefenster davor (nur live).
    print("- Einstieg -")
    if faktor != 1.0:
        print("  (Drawdown-Ratsche aktiv: Positionsgroesse x %.2f)" % faktor)
    pruefe_einstieg(z, w, live, faktor)

    print("\nStand: %d offene Position(en)" % len(z["positionen"]))
    schreibe_zustand(z)

    # Journal nach jedem Zyklus ausser Haus.
    if w.get("journal_zweitziel"):
        _spiegeln(w)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    for name in ("vorschau", "papier", "live", "wachen"):
        g.add_argument("--" + name, action="store_const", dest="modus", const=name)
    a = p.parse_args()
    lauf(a.modus or "papier")
