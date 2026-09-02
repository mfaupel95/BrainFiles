"""Dritte Spur: Kraken, Spot, nur Long, kein Hebel, in EUR.

Aufruf (aus diesem Ordner):
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --vorschau
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --papier    # Standard der Routine
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --live      # echte Orders
    ..\\scanner\\.venv\\Scripts\\python.exe handeln.py --wachen    # Wochenlauf

Diese Sperren muessen ALLE offen sein, sonst laeuft trotz --live nur Papier:
    1. wachen.json  handel_erlaubt == true
    2. KRAKEN_API_KEY / KRAKEN_API_SECRET gesetzt
    3. --live ausdruecklich auf der Kommandozeile
    4. wachen.json  freigabe.erfuellt == true      (Handelsregeln, Bedingung 1)
    5. Herzschlag frisch                            (Bedingung 3)
    6. rollierender Erwartungswert nicht negativ    (Bedingung 5)
    7. journal_zweitziel gesetzt und erreichbar     (Bedingung 4)
    8. mindestens mindest_guthaben_eur frei auf dem Konto
    9. eine Sitzung am Bildschirm, die das Freigabefenster bedienen kann
Fehlt eine, wird Papier gehandelt und es wird gesagt, welche Sperre zu war.

Sperre 7 und 8 hat diese Spur zusaetzlich zu Spur 1. Sperre 8, weil am
02.09.2026 nur 0,0094 EUR frei auf dem Konto lagen: ein Kauf-Automat ohne
Fiat kauft nichts, er scheitert nur - und zwar in jedem Lauf, mit einer
Fehlermeldung, die nach einem Schluesselproblem aussieht.

Der Unterschied zum Kraken-MCP-Server ist der ganze Punkt dieser Spur: Dort
liegt dieselbe API, aber ohne wachen.json, ohne Journal, ohne Herzschlag -
deshalb bleiben seine schreibenden Werkzeuge verboten (Wissen/Handelsregeln.md,
Abschnitt "Kraken"). Hier gelten die Wachen, deshalb darf hier gehandelt
werden.

Gebuehren stehen im Papierlauf mit drin: 0,40 % je Ausfuehrung, also 0,80 %
je Runde. Ein Papierlauf, der sie weglaesst, empfiehlt eine Strategie, die
live verliert - genau der Fehler aus Wissen/Handelsbots.md.

Der Live-Pfad ist mangels Freigabe und Guthaben noch NIE scharf gelaufen. Vor
dem ersten scharfen Lauf mit einem einzigen Paar und Kleinstbetrag gegenpruefen.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

import kraken
import scan
import wachen_kraken as wp

HIER = Path(__file__).resolve().parent
ZUSTAND = HIER / "zustand.json"
JOURNAL = HIER / "handelsjournal.csv"

# Sekunden ohne Bedienung, nach denen das Freigabefenster von selbst ablehnt.
FREIGABE_ZEITLIMIT_S = 120


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def lade_zustand():
    if ZUSTAND.exists():
        return json.loads(ZUSTAND.read_text("utf-8"))
    return {"positionen": [], "letzte_stops": {}, "letzter_lauf": None,
            "modus": None}


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    ZUSTAND.write_text(json.dumps(z, ensure_ascii=False, indent=2), "utf-8")


def journal(*felder):
    neu = not JOURNAL.exists()
    with JOURNAL.open("a", newline="", encoding="utf-8") as f:
        s = csv.writer(f)
        if neu:
            s.writerow(["zeit", "modus", "aktion", "paar", "preis", "eur",
                        "menge", "stop", "ziel", "grund"])
        s.writerow(felder)


# --- Vorschlaege ---------------------------------------------------------------

def stop_prozent(z, w):
    """Stop-Abstand aus der Volatilitaet, hart auf den Wachen-Rahmen gedeckelt.
    Die Untergrenze liegt hier bei 5 % statt 4 %: bei 0,80 % Gebuehr je Runde
    ist ein engerer Stop zu einem Sechstel Kosten."""
    vola = z["kennzahlen"]["volatilitaet_pa"]
    roh = 3.0 + 6.0 * min(vola, 1.5)
    return max(w["pflicht_stop_prozent_min"],
               min(w["pflicht_stop_prozent_max"], round(roh, 1)))


def vorschlaege(bericht, w):
    aus = []
    for z in bericht["werte"]:
        vola = z["kennzahlen"]["volatilitaet_pa"]
        if not (z["score"] >= w["mindest_score"]
                and vola <= w["max_volatilitaet_pa"]
                and z["verhaeltnis"] >= w["mindest_chance_risiko"]):
            continue
        einstieg = z["preis"]
        sp = stop_prozent(z, w)
        stop = round(einstieg * (1 - sp / 100.0), 8)
        ziel = round(einstieg + 2.0 * (einstieg - stop), 8)   # Chance/Risiko 2:1
        aus.append({"inst": z["inst"], "score": z["score"], "einstieg": einstieg,
                    "stop": stop, "stop_pct": sp, "ziel": ziel,
                    "eur": w["max_pro_trade_eur"]})
    return aus


# --- Mengen ----------------------------------------------------------------

def menge_fuer(paar, eur, kurs):
    """Wieviel Basiswaehrung kauft dieser Betrag? Abgerundet auf die
    Stellenzahl des Paares - aufrunden wuerde den Rahmen ueberschreiten.

    Gibt (menge, fehler) zurueck. Ein Fehler heisst: diese Order wuerde
    Kraken ablehnen, und zwar bevor sie Geld kostet."""
    try:
        info = kraken.paar_info(paar)
    except Exception as e:  # noqa: BLE001
        return 0.0, "Paar-Info nicht abrufbar (%s)" % e
    stellen = info["mengen_stellen"]
    roh = eur / kurs if kurs > 0 else 0.0
    menge = int(roh * 10 ** stellen) / 10 ** stellen
    if menge < info["mindestmenge"]:
        return 0.0, ("Menge %.8f unter Mindestmenge %.8f"
                     % (menge, info["mindestmenge"]))
    if menge * kurs < info["mindestwert"]:
        return 0.0, ("Wert %.2f EUR unter Mindestwert %.2f"
                     % (menge * kurs, info["mindestwert"]))
    return menge, None


# --- Ausstieg / Einstieg ---------------------------------------------------

def in_abklingzeit(paar, z, w):
    d = z["letzte_stops"].get(paar)
    if not d:
        return False
    tage = (date.fromisoformat(_heute()) - date.fromisoformat(d)).days
    return tage < w["abklingzeit_tage"]


def _erloes(p, kurs, w):
    """Verkaufserloes nach Gebuehr. Die Gebuehr steht im Papierlauf genauso
    drin wie live - sonst misst Bedingung 1 eine Strategie, die es nicht gibt."""
    return p["menge"] * kurs * (1.0 - w["gebuehr_taker"])


def _schliesse(p, kurs, w, live, grund, z):
    """Eine Position schliessen. Gibt True zurueck, wenn sie weg ist."""
    if live:
        try:
            if p.get("stop_txid"):
                kraken.order_stornieren(p["stop_txid"])   # Stop zuerst weg
            kraken.markt_verkauf(p["paar"], p["menge"], echt=True)
        except Exception as e:  # noqa: BLE001
            print("  Verkauf %s fehlgeschlagen: %s" % (p["paar"], e),
                  file=sys.stderr)
            return False
    erloes = _erloes(p, kurs, w)
    print("  ZU  %-10s @ %-12.6g (%s)  G/V %+.2f EUR"
          % (p["paar"], kurs, grund, erloes - p["eur"]))
    journal(_jetzt(), "live" if live else "papier", "verkauf", p["paar"],
            "%.8g" % kurs, "%.2f" % erloes, "%.8f" % p["menge"], "", "", grund)
    if grund == "stop":
        z["letzte_stops"][p["paar"]] = _heute()
    return True


def pruefe_ausstiege(z, w, live):
    behalten = []
    for p in z["positionen"]:
        kurs = kraken.letzter_kurs(p["paar"])
        grund = None
        if kurs <= p["stop"]:
            grund = "stop"
        elif kurs >= p["ziel"]:
            grund = "ziel"
        if not grund or not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def flach_stellen(z, w, live, grund):
    """Alle offenen Positionen sofort schliessen - Notausstieg fuer Bedingung 2
    (Kill-Switch) und Bedingung 3 (Herzschlag alt)."""
    behalten = []
    for p in z["positionen"]:
        kurs = kraken.letzter_kurs(p["paar"])
        if not _schliesse(p, kurs, w, live, grund, z):
            behalten.append(p)
    z["positionen"] = behalten


def pruefe_einstiege(z, vs, w, live, faktor=1.0):
    gehalten = {p["paar"] for p in z["positionen"]}
    eingesetzt = sum(p["eur"] for p in z["positionen"])
    if faktor != 1.0:
        print("  (Drawdown-Ratsche aktiv: Positionsgroesse x %.2f)" % faktor)
    for v in vs:
        if len(z["positionen"]) >= w["max_offene_positionen"]:
            break
        eur = round(v["eur"] * faktor, 2)
        if eingesetzt + eur > w["max_gesamt_eur"]:
            continue
        if v["inst"] in gehalten or in_abklingzeit(v["inst"], z, w):
            continue

        menge, fehler = menge_fuer(v["inst"], eur, v["einstieg"])
        if fehler:
            print("  -- %-10s uebersprungen: %s" % (v["inst"], fehler))
            continue

        kauf_txid = stop_txid = None
        if live:
            try:
                kauf_txid = kraken.markt_kauf(v["inst"], menge, echt=True)
                gefuellt = kraken.gefuellte_menge(kauf_txid) if kauf_txid else 0.0
                if gefuellt > 0:
                    menge = gefuellt
                    stop_txid = kraken.stop_setzen(v["inst"], menge, v["stop"],
                                                   echt=True)
            except Exception as e:  # noqa: BLE001
                print("  Kauf %s fehlgeschlagen: %s" % (v["inst"], e),
                      file=sys.stderr)
                continue

        kosten = eur * w["gebuehr_taker"]
        z["positionen"].append({
            "paar": v["inst"], "einstieg": v["einstieg"], "eur": eur,
            "menge": menge, "stop": v["stop"], "ziel": v["ziel"],
            "eroeffnet": _heute(), "kauf_txid": kauf_txid,
            "stop_txid": stop_txid,
        })
        eingesetzt += eur
        gehalten.add(v["inst"])
        print("  AUF %-10s @ %-12.6g Stop %-12.6g (-%.1f%%) Ziel %-12.6g %.2f EUR"
              % (v["inst"], v["einstieg"], v["stop"], v["stop_pct"],
                 v["ziel"], eur))
        journal(_jetzt(), "live" if live else "papier", "kauf", v["inst"],
                "%.8g" % v["einstieg"], "%.2f" % (eur + kosten), "%.8f" % menge,
                "%.8g" % v["stop"], "%.8g" % v["ziel"], "score %.1f" % v["score"])


# --- Freigabe von Hand (Handelsregeln Punkt 3) -------------------------------

def sitzung_da():
    """Sitzt jemand davor, der das Freigabefenster bedienen kann?

    Nur eine erste Huerde: isatty() meldet in der Git-Bash unter Windows auch
    bei umgeleitetem stdin ein Terminal (gemessen 02.09.2026). Der tragende
    Schutz ist FREIGABE_ZEITLIMIT_S. MAXHIRN_ROUTINE=1 setzt der Wrapper einer
    geplanten Aufgabe - die ausdrueckliche Ansage "hier sitzt niemand"."""
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


def hole_freigabe(vs, z, s):
    """Jeden Vorschlag im Fenster bestaetigen lassen. Leere Liste heisst
    abgelehnt - und abgelehnt heisst kein Einstieg. Faellt das Fenster aus,
    wird nicht gehandelt: ein Fehler darf nie zu einem ungefragten Kauf werden."""
    sys.path.insert(0, str(HIER.parent))
    try:
        import freigabe
    except Exception as e:  # noqa: BLE001
        print("  Freigabefenster nicht verfuegbar (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []
    bestand = {
        "gebunden": sum(p["eur"] for p in z["positionen"]),
        "offene_positionen": len(z["positionen"]),
        "verlust_gesamt": s["ruecklauf_eur"],
    }
    try:
        return freigabe.bestaetige(vs, "kraken", bestand,
                                   zeitlimit=FREIGABE_ZEITLIMIT_S)
    except Exception as e:  # noqa: BLE001
        print("  Freigabe abgebrochen (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []


# --- Wachen-Status (Bedingungen 2-5) ----------------------------------------

def _spiegeln(w):
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))
    return ok


def zeige_wachen(w):
    """handeln.py --wachen: alle fuenf Bedingungen als Momentaufnahme, dazu die
    beiden Automatik-Reaktionen des Wochenlaufs - Bedingung 4 (spiegeln) und
    Bedingung 5 (bei negativem Erwartungswert die Sperre schliessen)."""
    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)
    print("=== Wachen-Status Kraken  %s ===" % _jetzt())
    print("  1 Freigabe erfuellt      %s   (Runden gesamt %d, davon Papier %d, seit %s)"
          % (s["freigabe_erfuellt"], s["runden_gesamt"], s["runden_papier"],
             s["erste_runde"] or "-"))
    print("  2 Ruecklauf              %.2f EUR von Hoechststand %.2f  -> Faktor %.2f%s"
          % (s["ruecklauf_eur"], s["hoechststand_eur"], s["groessenfaktor"],
             "   >>> KILL-SWITCH" if s["kill"] else ""))
    print("  3 Herzschlag frisch      %s   (%s min alt, Grenze %d)"
          % (s["herzschlag_frisch"],
             "?" if s["herzschlag_alter_min"] is None
             else "%.0f" % s["herzschlag_alter_min"],
             w.get("herzschlag_max_minuten", 2880)))
    print("  4 Journal-Zweitziel      %s"
          % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  5 Rollierender EV        %s%s"
          % ("n/a (zu wenig Runden)" if s["rollierender_ev"] is None
             else "%+.3f EUR/Runde" % s["rollierender_ev"],
             "   >>> NEGATIV" if s["ev_negativ"] else ""))
    print("  + Guthaben               %s"
          % _guthaben_text(w))
    print()
    _spiegeln(w)
    if s["kill"] and wp.sperre_zu("Bedingung 2 (Wochenlauf): Ruecklauf %.2f EUR >= Kill-Switch"
                                  % s["ruecklauf_eur"]):
        print("  -> Bedingung 2: handel_erlaubt auf false gesetzt.")
    if s["ev_negativ"] and wp.sperre_zu("Bedingung 5 (Wochenlauf): rollierender EV %.3f EUR < 0"
                                        % s["rollierender_ev"]):
        print("  -> Bedingung 5: handel_erlaubt auf false gesetzt.")


def _guthaben_text(w):
    if not kraken.schluessel_vorhanden():
        return "unbekannt (kein Schluessel)"
    try:
        frei = kraken.guthaben("ZEUR")
    except Exception as e:  # noqa: BLE001
        return "nicht abrufbar (%s)" % e
    return "%.2f EUR frei, noetig %.2f" % (frei, w.get("mindest_guthaben_eur", 0))


# --- Hauptlauf ---------------------------------------------------------------

def live_sperren(w, s):
    """Alle Gruende, die diesen Lauf auf Papier zurueckwerfen. Leere Liste
    heisst: scharf, aber weiterhin nur mit Freigabefenster je Einstieg."""
    gruende = []
    if not w.get("handel_erlaubt"):
        gruende.append("wachen.json handel_erlaubt=false")
    if not kraken.schluessel_vorhanden():
        gruende.append("KRAKEN_API_KEY/SECRET nicht gesetzt")
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
        gruende.append("keine Sitzung am Bildschirm - Freigabefenster nicht "
                       "moeglich (Handelsregeln Punkt 3)")
    noetig = w.get("mindest_guthaben_eur", 0)
    if noetig and kraken.schluessel_vorhanden():
        try:
            frei = kraken.guthaben("ZEUR")
            if frei < noetig:
                gruende.append("nur %.2f EUR frei, noetig %.2f" % (frei, noetig))
        except Exception as e:  # noqa: BLE001
            gruende.append("Guthaben nicht abrufbar (%s)" % e)
    return gruende


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = scan.wachen()

    if modus == "wachen":
        zeige_wachen(w)
        return

    bpfad = scan.BERICHTE / "neuester.json"
    if not bpfad.exists():
        print("Kein Bericht. Erst scan.py laufen lassen.")
        return
    bericht = json.loads(bpfad.read_text("utf-8"))

    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)

    live = False
    if modus == "live":
        gruende = live_sperren(w, s)
        if gruende:
            print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    vs = vorschlaege(bericht, w)
    print("=== Kraken handeln (%s) | Bericht %s | %d Vorschlaege ==="
          % ("LIVE" if live else "Papier", bericht["datum"], len(vs)))

    z["modus"] = "live" if live else "papier"

    if modus == "vorschau":
        for v in vs:
            print("  %-10s Score %.1f  Einstieg %-12.6g Stop %-12.6g (-%.1f%%)  Ziel %.6g"
                  % (v["inst"], v["score"], v["einstieg"], v["stop"],
                     v["stop_pct"], v["ziel"]))
        eing = sum(p["eur"] for p in z["positionen"])
        print("\nOffener Bestand: %d Positionen, %.2f EUR gebunden"
              % (len(z["positionen"]), eing))
        print("Live waere gesperrt durch: %s"
              % ("; ".join(live_sperren(w, s)) or "nichts"))
        return

    # Bedingung 2 - Kill-Switch: alles zu, Sperre zu, Schluss.
    if s["kill"]:
        print("- KILL-SWITCH: Ruecklauf %.2f EUR >= %g -> Notausstieg + Sperre -"
              % (s["ruecklauf_eur"], w["kill_switch_gesamt_eur"]))
        flach_stellen(z, w, live, "kill_switch")
        if wp.sperre_zu("kill_switch: Ruecklauf %.2f EUR" % s["ruecklauf_eur"]):
            print("  wachen.json handel_erlaubt -> false")
        schreibe_zustand(z)
        return

    # Bedingung 3 - Herzschlag alt: alles zu, dieser Lauf handelt nicht mehr.
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser Lauf -"
              % ("?" if s["herzschlag_alter_min"] is None
                 else "%.0f" % s["herzschlag_alter_min"],
                 w.get("herzschlag_max_minuten", 2880)))
        flach_stellen(z, w, live, "herzschlag_alt")
        z["modus"] = "papier"
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    # Ausstiege laufen nie durch das Fenster: ein Stop muss greifen, auch
    # wenn niemand davorsitzt.
    print("- Ausstiege -")
    pruefe_ausstiege(z, w, live)

    print("- Einstiege -")
    faktor = s["groessenfaktor"]
    if live and vs:
        vs = [dict(v, eur=round(v["eur"] * faktor, 2), cr=2.0) for v in vs]
        faktor = 1.0
        vs = hole_freigabe(vs, z, s)
        if not vs:
            print("  Freigabe abgelehnt - kein Einstieg in diesem Lauf.")
    pruefe_einstiege(z, vs, w, live, faktor)

    eing = sum(p["eur"] for p in z["positionen"])
    print("\nStand: %d/%d Positionen, %.2f/%d EUR gebunden"
          % (len(z["positionen"]), w["max_offene_positionen"],
             eing, w["max_gesamt_eur"]))
    schreibe_zustand(z)

    # Bedingung 4 - Journal nach jedem Zyklus ausser Haus.
    if w.get("journal_zweitziel"):
        _spiegeln(w)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau", help="nur zeigen")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier", help="Papierhandel (Standard)")
    g.add_argument("--live", action="store_const", dest="modus",
                   const="live", help="echte Orders, wenn alle Sperren offen")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen", help="Bedingungen 2-5 zeigen und durchsetzen "
                                        "(Wochenlauf)")
    a = p.parse_args()
    lauf(a.modus or "papier")
