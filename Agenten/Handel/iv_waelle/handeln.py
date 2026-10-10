"""IV-Waelle-Spur (Deribit, Papier) - Fade an der Spannengrenze.

WAS DIE SPUR RECHNET
--------------------
Aus historischer Volatilitaet (HV) UND Options-Bepreisung (DVOL) wird die
erwartete Tagesspanne gebaut, danach die Waende aus der Optionskette
(Strikes mit hohem offenem Interesse). Ist der Kurs an einer handelbaren
Wand (Abstand zwischen 1 und 3 Sigma), wird gegen die Bewegung gehandelt:
Stop hinter die Wand, Ziel als halber Rueckweg zur Mitte (gemessener Hebel).
Liegen die Waende weiter als 3 Sigma entfernt, ist kein Geschaeft (kein_signal).

Haus-Buch ueber spur_buch (gemeinsame Zahnraeder): ZUSTAND, HANDELSJOURNAL,
Kopie ausser Haus (Q:\\Handel_Journal\\iv_waelle, Bedingung 4), Groesse ueber
die Ratsche. Kein Orderpfad, kein echtes Geld.

Aufruf:
  python handeln.py --vorschau   was waere dran, ohne schreiben
  python handeln.py --papier     Papierlauf mit Journal
  python handeln.py --wachen     Grenzen als Momentaufnahme
  python handeln.py --live       verweigert, nennt den Grund
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HANDEL, os.path.join(HANDEL, "scanner"), HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import spur_buch as buch  # noqa: E402
import kill_gemeinsam as kg  # noqa: E402  # Kill-Frist/Reset/Opt-out
import wachen_pruefung as wp  # noqa: E402
import ereignis  # noqa: E402
import iv_waelle as k  # noqa: E402
import daten as dt  # noqa: E402

# Test-Seams: None -> echte Quellen (daten.py / Deribit).
markt_quelle = None
zeit_quelle = None

# --- Pfade ---------------------------------------------------------------
wachen_pfad, zustand_pfad, journal_pfad = buch.pfade(HIER)


def _jetzt():
    if zeit_quelle:
        return zeit_quelle()
    return buch.jetzt()


# --- Markt und Signal ------------------------------------------------------

def tage_aus_kerzen(kerzen: dict) -> dict:
    """Stundenkerzen nach UTC-Tag buendeln (gleicher Weg wie im Backtest)."""
    tage: dict = {}
    for i, tick in enumerate(kerzen["ticks"]):
        tag = datetime.fromtimestamp(tick / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        tage.setdefault(tag, []).append({
            "open": kerzen["open"][i], "close": kerzen["close"][i],
        })
    return tage


def _closes_je_tag(kerzen: dict) -> list:
    """Letzter Schlusskurs je UTC-Tag, aufsteigend sortiert (fuer die HV)."""
    tage = tage_aus_kerzen(kerzen)
    return [tage[name][-1]["close"] for name in sorted(tage)]


def _tages_open(kerzen: dict, jetzt_iso: str) -> float | None:
    """Erstkurs des aktuellen UTC-Tags - die Basis der Tagesspanne.

    Die Spanne, in die der Handel gelegt wird, gehoert zum TAGESBEGINN und
    nicht zum laufenden Kurs: Nur so bleibt eine Wand (Strike mit hohem OI)
    ueber den Tag bei stabiler Sigma-Entfernung, waehrend der Kurs sich an sie
    heranbewegt. Steht der heutige Tag noch nicht im Bestand, fallt dieser
    Aufruf auf den laufenden Kurs zurueck (wird dann in spanne_und_signal
    entschieden, wenn kein basispreis uebergeben wird).
    """
    jetzt = datetime.fromisoformat(jetzt_iso)
    if jetzt.utcoffset() is None:
        jetzt = jetzt.replace(tzinfo=timezone.utc)
    heute = jetzt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    tag_kerzen = tage_aus_kerzen(kerzen).get(heute)
    return tag_kerzen[0]["open"] if tag_kerzen else None


def _hole_markt(w):
    """Spot, Jahres-IV, HV und Optionskette - alles, was die Signal-Regel braucht.

    Rueckgabe: (daten, kurse, fehler). daten[inst] = {"spot", "basispreis",
    "iv_prozent", "hv_prozent", "kette"}; kurse = {inst: spot}. Ein Fehler
    EINES Schritts (z. B. DVOL nicht erreichbar) bricht den Zyklus nicht ab -
    fehlt die IV, antwortet das Signal mit kein_signal statt zu raten.
    """
    if markt_quelle:
        return markt_quelle(w)
    inst = w.get("instrument", "BTC-PERPETUAL")
    waehrung = w.get("optionswaehrung", "BTC")
    fehler = []

    try:
        spot = float(dt.indexpreis(w.get("index_name", "btc_usd")))
    except Exception as e:                                        # noqa: BLE001
        return {}, {}, ["Indexpreis: %s" % str(e)[:120]]

    iv_prozent = hv_prozent = None
    kette = []
    basispreis = None
    try:
        reihe = dt.dvol_tagesreihe(waehrung,
                                   tage=int(w.get("hist_vol_fenster", 20)) + 10)
        iv_prozent = float(reihe[-1][4]) if reihe else None
    except Exception as e:                                        # noqa: BLE001
        fehler.append("DVOL: %s" % str(e)[:120])
    try:
        kerzen = dt.minutenkerzen(inst, "60", tage=35)
        closes = _closes_je_tag(kerzen)
        hv_prozent = k.hist_vol_prozent(
            closes, fenster=int(w.get("hist_vol_fenster", 20)))
        basispreis = _tages_open(kerzen, _jetzt())
    except Exception as e:                                        # noqa: BLE001
        fehler.append("Kerzen: %s" % str(e)[:120])
    try:
        kette = dt.optionskette(waehrung)
    except Exception as e:                                        # noqa: BLE001
        fehler.append("Optionskette: %s" % str(e)[:120])

    daten = {inst: {"spot": spot, "basispreis": basispreis,
                    "iv_prozent": iv_prozent, "hv_prozent": hv_prozent,
                    "kette": kette}}
    return daten, {inst: spot}, fehler


def spanne_und_signal(d, w) -> dict:
    """Die Signal-Regel AUS iv_waelle.py, unveraendert.

    Rueckgabe ist das dict von k.signal() - mit 'richtung' 'kein_signal',
    'short' oder 'long' samt einstieg/stop/ziel. Spanne aus der Mischung aus
    IV (DVOL) und HV (20-Tage-Volatilitaet), verankert am TAGESBEGINN
    (basispreis); die Wandlage prueft die 1-bis-3-Sigma-Handelbarkeit gegen
    diese Spanne, waehrend der laufende Kurs (spot) sich an die Wand
    heranbewegt.
    """
    basis = d.get("basispreis") or d["spot"]
    spot = d["spot"]
    jahres_iv = k.mische_iv_hv(d["iv_prozent"], d["hv_prozent"],
                               w.get("mischgewicht_iv", 0.5))
    if jahres_iv is None:
        return {"richtung": "kein_signal", "grund": "keine IV/HV",
                "spot": spot, "lagen": {}}
    spanne = k.spanne(basis, jahres_iv, k=float(w.get("grenz_k", k.K_90)))
    waende = k.waende(d["kette"], spot)
    sig = k.signal(
        spot, waende, spanne,
        naehe_prozent=float(w.get("naehe_prozent", 0.5)),
        stop_puffer_prozent=float(w.get("stop_puffer_prozent", 0.25)),
        ziel="mitte", ziel_anteil=float(w.get("ziel_anteil", 0.5)),
        nur_handelbare_wand=bool(w.get("nur_handelbare_wand", True)))
    if sig["richtung"] != "kein_signal":
        return sig

    # ZWEITER WEG: die Wand war nicht in Reichweite (oder keine da). Der
    # gemessene Handel dieser Spur ist der Fade an der SPANNENGRENZE - siehe
    # k.signal_an_der_spanne(). Der Wandgrund bleibt im Feld 'grund' erhalten,
    # damit im Journal steht, warum kein Wandgeschaeft zustande kam.
    if not w.get("einstieg_an_der_spanne", True):
        return sig
    spanne_sig = k.signal_an_der_spanne(
        spot, spanne, stop_sigma=float(w.get("stop_sigma", 0.5)),
        ziel_anteil=float(w.get("ziel_anteil", 0.5)))
    spanne_sig["ohne_wand"] = sig.get("grund")
    return spanne_sig


def _tag_utc(iso) -> str | None:
    """Der UTC-Tag eines Zeitstempels; None, wenn er nicht lesbar ist."""
    try:
        jetzt = datetime.fromisoformat(str(iso))
    except (TypeError, ValueError):
        return None
    if jetzt.utcoffset() is None:
        jetzt = jetzt.replace(tzinfo=timezone.utc)
    return jetzt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def tagesende(p, w) -> str | None:
    """Ausstieg am Tagesende - so rechnet auch der Backtest.

    Die Spanne, gegen die gefadet wird, gehoert zu EINEM UTC-Tag (sie wird aus
    dem Eroeffnungskurs dieses Tages gebaut). Eine Position, die in den naechsten
    Tag laeuft, handelt gegen eine Spanne, die es nicht mehr gibt - im
    Backtest kam das nicht vor, weil dort jede Runde im selben Tag endet.
    Ein unlesbarer Eroeffnungszeitpunkt gilt als Tagesende: lieber schliessen
    und es im Journal zeigen, als eine Position ohne Zeitbezug stehen lassen.
    """
    if not w.get("ausstieg_am_tagesende", True):
        return None
    if _tag_utc(p.get("eroeffnet_zeit")) == _tag_utc(_jetzt()):
        return None
    return "tagesende"


# --- Einstieg ---------------------------------------------------------------

def einstieg(z, inst, d, sig, w, faktor, journal_pfad, zustand_pfad):
    """Einstieg zum Signal: Stop hinter der Wand, Ziel der halbe Rueckweg.

    buch.einstieg kann den Stop NICHT als Marktpunkt setzen (nur als Prozent,
    dessen Unter-/Obergrenze fest in den Wachen liegt) - der Stop dieser Spur
    liegt HINTER der Wand, also nicht als feste Prozent-Spanne abbildbar.
    Deshalb baut diese Spur ihre Position wie moondev_funding selbst; die
    Ausstiege (buch.pruefe_ausstiege) kennen genau diese Felder (einstieg,
    stop, ziel, nominal, seite) und rechnen den G/V identisch auf den
    NOMINALWERT.
    """
    if not z.get("positionen"):
        z["positionen"] = []
    if len(z["positionen"]) >= w.get("max_offene_positionen", 4):
        return None
    if any(p.get("inst") == inst for p in z["positionen"]):
        return None

    seite = sig["richtung"]
    if seite not in ("long", "short"):
        return None
    einstieg_p = float(sig.get("einstieg") or 0.0)
    stop = float(sig.get("stop") or 0.0)
    ziel = float(sig.get("ziel") or 0.0)
    if einstieg_p <= 0 or stop <= 0 or ziel <= 0:
        return None

    stop_pct = abs(stop - einstieg_p) / einstieg_p * 100.0
    if stop_pct <= 0:
        return None

    nominal = w["risiko_je_position_usd"] / (stop_pct / 100.0)
    nominal = min(nominal, w["max_pro_trade_usd"]) * faktor
    if nominal <= 0:
        return None

    p = {"inst": inst, "seite": seite, "einstieg": einstieg_p,
         "stop": stop, "ziel": ziel, "stop_pct": round(stop_pct, 2),
         "nominal": nominal, "eroeffnet_zeit": _jetzt(),
         "wand": sig.get("wand"),
         # Woher das Geschaeft kommt: 'wand' (Wand in Reichweite) oder 'spanne'
         # (Fade an der Tagesspannengrenze, das gemessene Feld). Ohne dieses
         # Feld sieht im Journal jedes Geschaeft gleich aus, obwohl die zwei
         # Wege verschiedene Regeln sind - und ein Gewinn waere dem falschen
         # Weg zugeschrieben.
         "ausloeser": sig.get("ausloeser") or ("wand" if sig.get("wand")
                                               else "unbekannt"),
         "grund": (w.get("_grund") or w.get("grund") or "iv_waelle")}
    z["positionen"].append(p)
    print("EINSTIEG %s %s @ %.6f  Stop %.6f  Ziel %.6f  Nominal %.2f USD  "
          "(%s)" % (seite.upper(), inst, einstieg_p, stop, ziel, nominal,
                    p["ausloeser"]))
    # Journal UND Zustand zusammen (buch.buche): eine Buchung, die nur das
    # Journal erreicht, wuerde einen Geist erzeugen (T-356).
    buch.buche(z, zustand_pfad, journal_pfad, zeit=_jetzt(), modus="papier",
               aktion="kauf", inst=inst, seite=seite,
               preis="%.6f" % einstieg_p, einsatz_usd="%.2f" % nominal,
               stop="%.6f" % stop, ziel="%.6f" % ziel,
               stop_pct="%.2f" % stop_pct,
               grund="%s:%s" % (w.get("_grund") or w.get("grund") or
                                "iv_waelle", p["ausloeser"]))
    return p


# --- Lauf -------------------------------------------------------------------

def lauf(modus):
    """Ein Zyklus der IV-Waelle-Spur (Papier). 15-Minuten-Takt.

    Reihenfolge wie in spur_buch.zyklus: erst die Ratsche (Buch-Ruecklauf),
    dann Ausstiege, dann Einstiege. Bei --vorschau wird gerechnet und nichts
    geschrieben; ein --live gibt es in dieser Spur nicht.
    """
    w = buch.lade_wachen(wachen_pfad)
    z = buch.lade_zustand(zustand_pfad)
    z.setdefault("positionen", [])

    if modus == "wachen":
        print(json.dumps(wp.lage(w, journal_pfad, z), indent=2,
                         ensure_ascii=False))
        return 0

    s = wp.lage(w, journal_pfad, z)
    ruecklauf = s.get("ruecklauf_usd", 0.0)
    faktor = buch.groessenfaktor(ruecklauf, w)

    daten, kurse, fehler = _hole_markt(w)
    for f in fehler:
        print("Uebersprungen (%s)" % f, file=sys.stderr)

    if modus == "vorschau":
        # NUR schauen: keine Ausstiege buchen, kein Kill ausfuehren, nichts
        # spiegeln. buch.pruefe_ausstiege schreibt beim Exit ins Journal,
        # deshalb steht die Vorschau VOR dem Ausstiegspruefen - eine
        # Vorschau, die schreibt, ist keine Vorschau.
        if daten:
            for inst in sorted(daten):
                sig = spanne_und_signal(daten[inst], w)
                if sig["richtung"] != "kein_signal":
                    print("Vorschau: Einstieg waere %s %s  Stop %.6f  Ziel %.6f"
                          % (sig["richtung"].upper(), inst,
                             float(sig["stop"] or 0.0), float(sig["ziel"] or 0.0)))
        else:
            print("Vorschau: keine Marktdaten (%s)"
                  % ("; ".join(fehler)[:200] if fehler else "keine Instrumente"))
        print("Vorschau: keine Dateien geschrieben.")
        # Die Sperrenzeile gehoert in JEDE Vorschau: dauerlauf.nur_fenster_
        # fehlt liest genau sie (T-313, 02.10.2026).
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier)")
        return 0

    if not daten:
        print("Keine Marktdaten - Zyklus ohne Buchung beendet (%s)"
              % ("; ".join(fehler)[:200] if fehler else "keine Instrumente"))
        return 0

    if s.get("kill"):
        status, ruecklauf = kg.phase(z, w, ruecklauf, s.get("runden_gesamt", 0), buch.jetzt)
        if status == "frei":
            faktor = buch.groessenfaktor(ruecklauf, w)
        else:
            # Zwangsschluss zum Marktkurs MIT Buchung (bis 09.10.2026 ungebucht geleert).
            buch.pruefe_ausstiege(z, kurse, w, journal_pfad,
                                  zusatz=lambda p, w_: kg.KILL_GRUND,
                                  zustand_pfad=zustand_pfad)
            if z.get("positionen"):
                print("  %d Position(en) noch offen (kein Kurs) - naechster Zyklus "
                      "versucht es erneut." % len(z["positionen"]))
            buch.schreibe_zustand(zustand_pfad, z)
            buch.spiegeln(zustand_pfad, journal_pfad, z, w)
            return 0

    buch.pruefe_ausstiege(z, kurse, w, journal_pfad, zusatz=tagesende,
                          zustand_pfad=zustand_pfad)
    for inst in sorted(daten):
        sig = spanne_und_signal(daten[inst], w)
        if sig["richtung"] == "kein_signal":
            continue
        einstieg(z, inst, daten[inst], sig, w, faktor, journal_pfad,
                 zustand_pfad)

    buch.schreibe_zustand(zustand_pfad, z)
    buch.spiegeln(zustand_pfad, journal_pfad, z, w)
    return 0


# --- Main -------------------------------------------------------------------

def main():
    with ereignis.lauf("handel/iv_waelle"):
        return _main()


def _main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau",
                    dest="modus", help="was waere dran, ohne schreiben")
    ap.add_argument("--papier", action="store_const", const="papier",
                    dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen",
                    dest="modus")
    ap.set_defaults(modus="papier")
    a = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if a.modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier). Deribit ist ausschliesslich Papier gebucht, keine "
              "Order, kein echtes Geld. handel_erlaubt steht in wachen.json "
              "auf false.")
        return 0
    return lauf(a.modus) or 0


if __name__ == "__main__":
    raise SystemExit(main())