"""Marktlage-Live-Zweig an Kraken-Spot - der ERSTE echte Geldpfad im System.

Was das ist
-----------
marktlage entscheidet deterministisch (BTC-Regime). Der Papierlauf laeuft
weiter ueber spur_buch.zyklus (Handel/moondev_marktlage/handeln.py --papier).
Dieses Modul ist der einzigartige, ABGETRENNTE Live-Zweig: er wird NUR von
`handeln.py --live` gerufen und kauft bei einem long-Signal echtes Geld an
Kraken-Spot (XBT/USD), kleiner Betrag.

Kein Short, kein Hebel (Stufe A, Plan KRAKEN-LIVE-PLAN.md). Ein short-Signal
schliesst nur eine evtl. offene Long-Position (verkauft die gehaltene Menge)
und steigt nicht neu ein.

Warum ein eigenes Modul statt spur_buch zu erweitern
----------------------------------------------------
spur_buch.py ist fuer ALLE Bot-Spuren der gemeinsame Kern und traegt im Kopf
"KEIN Live-Zweig". Einen Live-Pfad dort hineinbauen wuerde neun Papier-Spuren
treffen. Dieser Live-Stamm hat sein EIGENES Zustand/Journal (zustand.live.json,
handelsjournal.live.csv) - so bleibt jede echte Runde von jeder Papier-Runde
unterscheidbar (Stufe C der Auswertung, Bedingung 1 zaehlt nie einen Mix).

Wiederverwendet statt neu geschrieben (Skill: ein Kern, nicht drei Kopien):
  - Orderanbindung    Agenten/Handel/kraken/kraken.py  (Spot, signiert)
  - Wachen-Rechnung   Agenten/Handel/scanner/wachen_pruefung.py (Bedingungen 1-5)
  - Freigabe-Fenster  Agenten/Handel/freigabe.py
  - Bus-Meldung       Agenten/Bus/ereignis.py
  - Ratsche           Agenten/Handel/ratschen.py

Sperrenkette (wie kraken/handeln.py, 9 Stufen) - ALLE muessen offen sein,
sonst wird Papier gehandelt und der Grund gesagt:
  1. handel_erlaubt == true        (wachen.json)
  2. KRAKEN_API_KEY/SECRET gesetzt
  3. --live auf der Kommandozeile
  4. freigabe.erfuellt == true     (Bedingung 1: 50 Runden netto positiv)
  5. Herzschlag frisch             (45 min)
  6. rollierender EV nicht negativ (Bedingung 5)
  7. journal_zweitziel gesetzt     (Bedingung 4)
  8. mindest_guthaben_eur frei
  9. Sitzung am Bildschirm (Freigabefenster bedienbar)

Ein "ja" auf einen Plan ist NICHT die Freigabe. handel_erlaubt gehoert nie
hierher geschrieben - nur wachen_pruefung.sperre_zu() darf true->false.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
SCANNER = os.path.join(HANDEL, "scanner")
BUS = os.path.join(os.path.dirname(HANDEL), "Bus")
_KRAKEN = os.path.join(HANDEL, "kraken")  # kraken.py liegt im Spur-Ordner
for p in (HANDEL, SCANNER, BUS, HIER, _KRAKEN):
    if p not in sys.path:
        sys.path.insert(0, p)

# Vorsicht: es gibt auch einen Spur-Unterordner mit demselben Namen. Der
# Import muss aus _KRAKEN kommen (dort liegt kraken.py mit den Market-Orders).
import kraken  # noqa: E402  (Agenten/Handel/kraken/kraken.py - Spot-Order)
import wachen_pruefung as wp  # noqa: E402  (Bedingungen 1-5, waehrungsneutral)
import moondev_daten as daten  # noqa: E402  (Marktlage-Daten: CoinGecko)
import risikostufe  # noqa: E402  (Dateinamen der Risikostufen)

from importlib.util import module_from_spec, spec_from_file_location  # noqa: E402

def _lade(name, pfad):
    spec = spec_from_file_location(name, pfad)
    m = module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

_ereignis = _lade("ereignis", os.path.join(BUS, "ereignis.py"))
_freigabe = _lade("freigabe", os.path.join(HANDEL, "freigabe.py"))

# --- Dateien (Live-Buch getrennt vom Papier) --------------------------------
ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand.live.json"))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal.live.csv"))

WAEHRUNG = "EUR"          # Kraken-Spot rechnet in EUR-Paaren
PAAR = "XBTUSD"           # BTC an Kraken-Spot
GRUND = "moondev_marktlage_long"

# Einsatz: 10..30 EUR, dynamisch nach Signalstaerke (Plan Punkt 2).
EINSATZ_MIN = 10.0
EINSATZ_MAX = 30.0


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def lade_zustand():
    try:
        with open(ZUSTAND, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"positionen": [], "letzter_lauf": None, "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    with open(ZUSTAND, "w", encoding="utf-8") as f:
        json.dump(z, f, ensure_ascii=False, indent=2)
        f.write("\n")


def journal(**felder):
    neu = not os.path.exists(JOURNAL)
    spalten = ["zeit", "modus", "aktion", "pair", "seite", "preis", "eur",
               "menge", "stop", "ziel", "grund"]
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=spalten)
        if neu:
            w.writeheader()
        w.writerow({k: felder.get(k, "") for k in spalten})


def signal(w):
    """Marktlage-Signal; True = long (Kraken-Spot kauft nur, Stufe A)."""
    d, kurse, fehler = daten_holen(w)
    if fehler or not d.get("BTC"):
        return None, None
    btc = d["BTC"]
    pct = btc.get("btc_aenderung_24h")
    breite = btc.get("breite")
    if pct is None or breite is None:
        return None, None
    schwelle = float(w.get("btc_schwelle_pct", 2.0))
    oben = float(w.get("breite_oben", 0.60))
    if pct >= schwelle and breite >= oben:
        return True, {"pct": pct, "breite": breite}
    return None, None


def daten_holen(w):
    try:
        maerkte = daten.maerkte(anzahl=100)
    except Exception as e:                                   # noqa: BLE001
        return {}, {}, ["CoinGecko: %s" % str(e)[:120]]
    if not maerkte:
        return {}, {}, ["CoinGecko: leere Antwort"]
    plus = sum(1 for m in maerkte
               if (daten.zahl(m.get("price_change_percentage_24h")) or 0) > 0)
    breite = plus / float(len(maerkte))
    aus = {}
    for m in maerkte:
        symbol = (m.get("symbol") or "").upper()
        if symbol == "BTC":
            aus["BTC"] = {
                "btc_aenderung_24h": daten.zahl(m.get("price_change_percentage_24h")),
                "breite": breite,
                "kurs": daten.zahl(m.get("current_price")),
            }
    return aus, aus, []


def signalstaerke(staerke):
    """Einsatz in EUR: 10..30 nach Signalstaerke (Plan Punkt 2).

    staerke ist ein (pct, breite)-Dict. Je weiter BTC ueber der Schwelle und
    je breiter der Markt, desto mehr Einsatz. Hart zwischen EINSATZ_MIN und
    EINSATZ_MAX gedeckelt; werte unter der Schwelle kleben am Minimum.
    """
    pct = float(staerke.get("pct") or 0.0)
    breite = float(staerke.get("breite") or 0.0)
    # Signalueberhang: wie weit ueber der +2-%-Schwelle, 0..+4 pp skaliert.
    ueberhang = max(0.0, min(4.0, pct - 2.0)) / 4.0
    # Marktbreite: 0.60..1.00 skaliert als zweiter Faktor.
    breiten_teil = max(0.0, min(1.0, (breite - 0.60) / 0.40))
    t = 0.5 * ueberhang + 0.5 * breiten_teil
    return round(EINSATZ_MIN + t * (EINSATZ_MAX - EINSATZ_MIN), 2)


def lade_wachen():
    with open(risikostufe.datei(os.path.join(HIER, "wachen.json")),
              encoding="utf-8") as f:
        return json.load(f)


# --- Sperrenkette -----------------------------------------------------------

def sitzung_da():
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


def live_sperren(w, z):
    """Alle Gruende, die diesen Lauf auf Papier/Ausstellen zurueckwerfen."""
    gruende = []
    if not risikostufe.live_erlaubt():
        gruende.append("Risikostufe %s: kein Live-Pfad in einer Stufe" % risikostufe.stufe())
    if not w.get("handel_erlaubt"):
        gruende.append("wachen.json handel_erlaubt=false")
    if not kraken.schluessel_vorhanden():
        gruende.append("KRAKEN_API_KEY/SECRET nicht gesetzt")
    s = wp.lage(w, JOURNAL, z)
    if not s["freigabe_erfuellt"]:
        gruende.append("freigabe.erfuellt=false (Bedingung 1)")
    if not s["herzschlag_frisch"]:
        gruende.append("Herzschlag alt (Bedingung 3)")
    if s["ev_negativ"]:
        gruende.append("rollierender EV %.3f EUR < 0 (Bedingung 5)"
                       % s["rollierender_ev"])
    if not w.get("journal_zweitziel"):
        gruende.append("journal_zweitziel nicht gesetzt (Bedingung 4)")
    if not sitzung_da():
        gruende.append("keine Sitzung am Bildschirm - Freigabefenster nicht moeglich")
    noetig = w.get("mindest_guthaben_eur", 0)
    if noetig and kraken.schluessel_vorhanden():
        try:
            frei = kraken.guthaben("ZEUR")
            if frei < noetig:
                gruende.append("nur %.2f EUR frei, noetig %.2f" % (frei, noetig))
        except Exception as e:                                   # noqa: BLE001
            gruende.append("Guthaben nicht abrufbar (%s)" % e)
    return gruende


# --- Order / Stops ----------------------------------------------------------

def menge_fuer(eur, kurs):
    """XBT-Menge fuer den Einsatz, von Kraken abgerundet + Minimum geprueft."""
    try:
        info = kraken.paar_info(PAAR)
    except Exception as e:                                       # noqa: BLE001
        return 0.0, "Paar-Info nicht abrufbar (%s)" % e
    stellen = info["mengen_stellen"]
    roh = eur / kurs if kurs > 0 else 0.0
    menge = int(roh * 10 ** stellen) / 10 ** stellen
    if menge < info["mindestmenge"]:
        return 0.0, "Menge %.8f unter Mindestmenge %.8f" % (menge, info["mindestmenge"])
    if menge * kurs < info["mindestwert"]:
        return 0.0, "Wert %.2f EUR unter Mindestwert %.2f" % (menge * kurs, info["mindestwert"])
    return menge, None


def hole_freigabe(vorschlag, z, s):
    """Ein Vorschlag im Freigabefenster bestaetigen. Leer = abgelehnt.

    Folgt exakt dem Muster der Haus-Kraken-Spur (kraken/handeln.py
    hole_freigabe): spur="kraken" (SPOTARTIG), Vorschlag traegt eur + cr.
    Faellt das Fenster aus, wird nicht gehandelt - ein Fehler darf nie zu
    einem ungefragten Kauf werden.
    """
    vs = [dict(vorschlag, cr=2.0)]
    bestand = {
        "gebunden": sum(p["eur"] for p in z["positionen"]),
        "offene_positionen": len(z["positionen"]),
        "verlust_gesamt": s.get("ruecklauf_eur", 0.0),
    }
    try:
        return _freigabe.bestaetige(vs, "kraken", bestand, zeitlimit=600)
    except Exception as e:                                       # noqa: BLE001
        print("  Freigabe abgebrochen (%s) - kein Einstieg." % e, file=sys.stderr)
        return []


def hole_freigabe_stdin(vorschlag, z, s):  # pragma: no cover
    """Ersatz ohne Fenster fuer Tests/Kopfzeile: liest ja/nein von stdin."""
    return [vorschlag] if input("Einstieg %s EUR erlauben? (ja/nein) "
                                % vorschlag["eur"]).strip().lower() == "ja" else []


# --- Ausstiege --------------------------------------------------------------

def pruefe_ausstiege(z, w, live):
    """Stop/Ziel auf dem Live-Paar. Ein getroffener Stop/Ziel verkauft echt."""
    behalten = []
    for p in z.get("positionen", []):
        try:
            kurs = kraken.letzter_kurs(PAAR)
        except Exception:                                        # noqa: BLE001
            behalten.append(p)
            continue
        grund = None
        if p["seite"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        if not grund:
            behalten.append(p)
            continue
        if live:
            try:
                kraken.markt_verkauf(PAAR, p["menge"], echt=True)
            except Exception as e:                               # noqa: BLE001
                print("  Verkauf %s fehlgeschlagen: %s" % (PAAR, e),
                      file=sys.stderr)
                behalten.append(p)
                continue
        gv = p["eur"] * (kurs - p["einstieg"]) / p["einstieg"]
        print("AUSSTIEG (%s) %s %.6f G/V %+.2f EUR" % (grund, PAAR, kurs, gv))
        journal(zeit=_jetzt(), modus="live" if live else "papier", aktion="verkauf",
                pair=PAAR, seite=p["seite"], preis="%.6f" % kurs,
                eur="%.2f" % (p["eur"] + gv), menge="%.8f" % p["menge"],
                stop="%.6f" % p["stop"], ziel="%.6f" % p["ziel"], grund=grund)
    z["positionen"] = behalten


# --- Einstiege --------------------------------------------------------------

def pruefe_einstiege(z, w, live):
    """EIN long-Signal -> EIN Kauf (max_offene_positionen=1)."""
    long, staerke = signal(w)
    if not long:
        print("- kein long-Signal - kein Einstieg")
        return
    if len(z.get("positionen", [])) >= w.get("max_offene_positionen", 1):
        print("- Buch voll - kein Einstieg")
        return
    kurs = kraken.letzter_kurs(PAAR)
    if not kurs or kurs <= 0:
        print("- Kurs %s nicht abrufbar - kein Einstieg" % PAAR, file=sys.stderr)
        return
    eur = signalstaerke(staerke)
    menge, fehler = menge_fuer(eur, kurs)
    if fehler:
        print("- Menge fuer %.2f EUR: %s - kein Einstieg" % (eur, fehler),
              file=sys.stderr)
        return
    stop_pct = float(w.get("stop_prozent", 6.0))
    # Vorschlag fuer das Freigabefenster: rechne_spot (cr) berechnet daraus
    # gehoerige stop/ziel/gebunden/risiko - das Fenster zeigt genau das, was
    # ausgefuehrt wird. Named-Feld "inst" wie die Haus-Kraken-Spur.
    vorschlag = {"inst": PAAR, "einstieg": kurs, "eur": eur,
                 "stop_pct": stop_pct, "cr": float(w.get("cr", 2.0))}
    zustand_lage = wp.lage(w, JOURNAL, z)
    bestaetigt = hole_freigabe(vorschlag, z, zustand_lage)
    if not bestaetigt:
        print("- Freigabe abgelehnt - kein Einstieg")
        return
    a = bestaetigt[0]
    # Bestaetigte Auftragswerte uebernehmen (das Fenster hat sie berechnet).
    eur = float(a["gebunden"])
    stop = float(a["stop"])
    ziel = float(a["ziel"])
    menge, fehler = menge_fuer(eur, kurs)
    if fehler:
        print("- Menge fuer bestaetigte %.2f EUR: %s - kein Einstieg" % (eur, fehler),
              file=sys.stderr)
        return
    if live:
        try:
            txid = kraken.markt_kauf(PAAR, menge, echt=True)
            gefuellt = kraken.gefuellte_menge(txid) if txid else 0.0
        except Exception as e:                                   # noqa: BLE001
            print("  Kauf %s fehlgeschlagen: %s" % (PAAR, e), file=sys.stderr)
            return
        if gefuellt <= 0:
            print("  Kauf %s ohne Fuellung - kein Eintrag" % PAAR, file=sys.stderr)
            return
        menge = gefuellt
        try:
            kraken.stop_setzen(PAAR, menge, stop, echt=True)
        except Exception as e:                                   # noqa: BLE001
            try:
                kraken.markt_verkauf(PAAR, menge, echt=True)
                print("  Stop fehlgeschlagen (%s) - zurueckverkauft, kein Eintrag" % e)
                return
            except Exception as e2:                              # noqa: BLE001
                print("  Stop und Rueckverkauf fehlgeschlagen (%s / %s)"
                      % (e, e2), file=sys.stderr)
    z["positionen"].append({
        "pair": PAAR, "einstieg": kurs, "eur": eur, "menge": menge,
        "stop": stop, "ziel": ziel, "seite": "long",
        "eroeffnet": _heute(), "txid": locals().get("txid"),
    })
    print("EINSTIEG %s %s @ %.6f Stop %.2f%% Ziel %.6f Nominal %.2f EUR"
          % ("LONG", PAAR, kurs, stop_pct, ziel, eur))
    journal(zeit=_jetzt(), modus="live" if live else "papier", aktion="kauf",
            pair=PAAR, seite="long", preis="%.6f" % kurs, eur="%.2f" % eur,
            menge="%.8f" % menge, stop="%.6f" % stop, ziel="%.6f" % ziel,
            grund=GRUND)


# --- Hauptlauf --------------------------------------------------------------

def spiegeln(w, z):
    """Bedingung 4: Live-Buch ausser Haus (Q:\\Handel_Journal)."""
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    print("  Live-Journal ausser Haus: %s (%s)" % ("ok" if ok else "--", info))
    return ok


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    w = lade_wachen()
    z = lade_zustand()
    z.setdefault("positionen", [])
    s = wp.lage(w, JOURNAL, z)

    if modus == "wachen":
        print(json.dumps(s, indent=2, ensure_ascii=False))
        return 0

    live = False
    if modus == "live":
        gruende = live_sperren(w, z)
        if gruende:
            print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
            print("-> es wird Papier (Live-Buch) gehandelt.")
        else:
            live = True

    # Kill-Switch
    if s.get("kill"):
        print("- KILL-SWITCH: Ruecklauf %.2f EUR -> Notausstieg + Sperre -"
              % s.get("ruecklauf_eur", 0.0))
        if wp.sperre_zu("kill_switch: Ruecklauf %.2f EUR" % s.get("ruecklauf_eur", 0.0)):
            print("  wachen.json handel_erlaubt -> false")
        return 0

    # Herzschlag alt -> kein Handel dieser Lauf
    if not s.get("herzschlag_frisch"):
        print("- Herzschlag alt -> kein Handel dieser Lauf -")
        return 0

    print("- Ausstiege -")
    pruefe_ausstiege(z, w, live)

    print("- Einstiege -")
    if modus != "vorschau":
        pruefe_einstiege(z, w, live)

    schreibe_zustand(z)
    if w.get("journal_zweitziel"):
        spiegeln(w, z)
    print("Stand: %d/%d Position, %.2f EUR gebunden"
          % (len(z.get("positionen", [])), w.get("max_offene_positionen", 1),
             sum(p["eur"] for p in z.get("positionen", []))))
    return 0


def main():
    with _ereignis.lauf("handel/moondev_marktlage"):
        return _main()


def _main():
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus", const="vorschau")
    g.add_argument("--papier", action="store_const", dest="modus", const="papier")
    g.add_argument("--live", action="store_const", dest="modus", const="live")
    g.add_argument("--wachen", action="store_const", dest="modus", const="wachen")
    ap.set_defaults(modus="papier")
    a = ap.parse_args()
    return lauf(a.modus)


if __name__ == "__main__":
    raise SystemExit(main())