"""Aus der Rangliste des Scans Vorschlaege bauen und - im Rahmen der Wachen -
ausfuehren.

Aufruf:
    python scanner\\handeln.py --vorschau          # nur zeigen, was er taete
    python scanner\\handeln.py --papier            # Papierhandel, Standard der Routine
    python scanner\\handeln.py --live              # echte Orders (siehe Sperren unten)

Diese Sperren muessen ALLE offen sein, sonst laeuft trotz --live nur Papier:
    1. wachen.json  handel_erlaubt == true
    2. OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE als Benutzervariablen
    3. --live ausdruecklich auf der Kommandozeile
    4. wachen.json  freigabe.erfuellt == true      (Handelsregeln, Bedingung 1)
    5. Herzschlag frisch                            (Bedingung 3)
    6. rollierender Erwartungswert nicht negativ    (Bedingung 5)
    7. eine Freigabe von Hand - am Bildschirm das Fenster (freigabe.py)
       oder im Dauerbetrieb das Zeitfenster (freigabefenster.py, /ja am
       Handy). Eine von beiden muss offen sein.
Fehlt eine, wird Papier gehandelt und es wird gesagt, welche Sperre zu war.

Punkt 3 der Handelsregeln laesst sich auf zwei Wegen erfuellen, und welcher
gilt, sagt die Lage:

  * **Sitzung am Bildschirm** - vor jedem Einstieg zeigt freigabe.py das
    Bestaetigungsfenster. Bedient es niemand, lehnt es nach
    FREIGABE_ZEITLIMIT_S von selbst ab; eine geplante Aufgabe bleibt so nie
    an einem Fenster haengen.
  * **Kein Bildschirm, aber offenes Zeitfenster** - freigabefenster.py
    traegt die Freigabe: Max hat sie am Handy mit /ja erteilt, sie laeuft
    nach spaetestens 24 h ab und /stop schliesst sie sofort. Dann tritt
    das Zeitfenster an die Stelle des Fensters - sonst bliebe der
    Dauerbetrieb dauerhaft auf Papier (Befund 10.09.2026).

Kein Weg fuehrt am Bildschirm vorbei, ohne dass jemand geantwortet hat:
das Zeitfenster oeffnet sich nur auf eine Anfrage des Dauerlaufs hin, und
der fragt nur, wenn sonst nichts mehr fehlt. Ausstiege laufen nie durch
eine Freigabe: ein Stop muss auch dann greifen, wenn niemand davorsitzt.

Bedingungen 2-5 aus Wissen/Handelsregeln.md rechnet wachen_pruefung.py:
    2  Drawdown-Ratsche : Positionsgroesse x0.5 ab drawdown_halbierung_prozent,
       Notausstieg + Sperre ab kill_switch_gesamt_usd
    3  Herzschlag       : letzter_lauf zu alt -> alles zu, dann Papier
    4  Journal ausser Haus : nach jedem Zyklus nach journal_zweitziel kopiert
    5  Soll-Ist         : handeln.py --wachen (Wochenlauf) sperrt bei EV < 0

Jede Aktion landet in handelsjournal.csv. Der offene Bestand steht in
zustand.json. Beide werden nicht versioniert (Rauschen), aber gesichert.

Der Live-Pfad (okx.markt_kauf / markt_verkauf / stop_setzen) ist mangels
gueltiger Schluessel noch NICHT gegen echte Orders getestet. Vor dem ersten
scharfen Lauf mit einem einzigen Wert und Kleinstbetrag gegenpruefen.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone, date
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, os.pardir, "Bus"))
import ereignis                                            # noqa: E402

import okx
import scan
import wachen_pruefung as wp

HIER = Path(__file__).resolve().parent
ZUSTAND = HIER / "zustand.json"
JOURNAL = HIER / "handelsjournal.csv"

# 0,05 % OKX Taker (Volumen < 10.000), gemessen 02.09.2026 - Handelsregeln.md
# nennt einen Papierlauf ohne Gebuehr einen Fehler. Identisch mit
# verbesserer/kosten.py (dort test_kosten_gleich.py). Bewusst nicht importiert:
# handeln.py bleibt ohne den Verbesserer lauffaehig.
GEBUEHR_PCT = 0.0005


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
            s.writerow(["zeit", "modus", "aktion", "inst", "preis", "usd",
                        "stop", "ziel", "grund"])
        s.writerow(felder)


# --- Vorschlaege ---------------------------------------------------------------

def stop_prozent(z, w):
    """Stop-Abstand: aus Volatilitaet und Drawdown, hart gedeckelt."""
    vola = z["kennzahlen"]["volatilitaet_pa"]
    roh = 3.0 + 6.0 * min(vola, 1.5)          # ~5 % ruhig, ~12 % wild
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
        stop = round(einstieg * (1 - sp / 100.0), 6)
        ziel = round(einstieg + 2.0 * (einstieg - stop), 6)   # Chance/Risiko 2:1
        aus.append({"inst": z["inst"], "score": z["score"], "einstieg": einstieg,
                    "stop": stop, "stop_pct": sp, "ziel": ziel,
                    "usd": w["max_pro_trade_usd"]})
    return aus


# --- Ausstieg / Einstieg ---------------------------------------------------

def in_abklingzeit(inst, z, w):
    d = z["letzte_stops"].get(inst)
    if not d:
        return False
    tage = (date.fromisoformat(_heute()) - date.fromisoformat(d)).days
    return tage < w["abklingzeit_tage"]


def pruefe_ausstiege(z, live):
    behalten = []
    for p in z["positionen"]:
        kurs = okx.letzter_kurs(p["inst"])
        grund = None
        if kurs <= p["stop"]:
            grund = "stop"
        elif kurs >= p["ziel"]:
            grund = "ziel"
        if not grund:
            behalten.append(p)
            continue
        # Nur die journalisierte Zeile traegt die Gebuehr; p["usd"] bleibt
        # nominal fuer Deckel- und G/V-Rechnung.
        erloes = p["usd"] * kurs / p["einstieg"] * (1 - GEBUEHR_PCT)
        gv = erloes - p["usd"]
        if live:
            try:
                d = okx.order_details(p["inst"], p["kauf_ord_id"])
                menge = float(d.get("accFillSz") or 0) or p["usd"] / p["einstieg"]
                okx.markt_verkauf(p["inst"], round(menge, 8))
            except Exception as e:  # noqa: BLE001
                print("  Verkauf %s fehlgeschlagen: %s" % (p["inst"], e),
                      file=sys.stderr)
                behalten.append(p)
                continue
        print("  ZU  %-10s @ %.6f  (%s)  G/V %+.2f USD"
              % (p["inst"], kurs, grund, gv))
        journal(_jetzt(), "live" if live else "papier", "verkauf", p["inst"],
                "%.6f" % kurs, "%.2f" % erloes, "", "", grund)
        if grund == "stop":
            z["letzte_stops"][p["inst"]] = _heute()
    z["positionen"] = behalten


def flach_stellen(z, live, grund):
    """Alle offenen Positionen sofort schliessen - Notausstieg fuer Bedingung 2
    (Kill-Switch) und Bedingung 3 (Herzschlag alt). Im Papierlauf zum aktuellen
    Kurs verbucht, live per Market-Verkauf. Ein fehlgeschlagener Live-Verkauf
    laesst die Position stehen und wird gemeldet."""
    behalten = []
    for p in z["positionen"]:
        kurs = okx.letzter_kurs(p["inst"])
        # Wie in pruefe_ausstiege: Gebuehr nur in der journalisierten Zeile.
        erloes = p["usd"] * kurs / p["einstieg"] * (1 - GEBUEHR_PCT)
        if live:
            try:
                d = okx.order_details(p["inst"], p["kauf_ord_id"])
                menge = float(d.get("accFillSz") or 0) or p["usd"] / p["einstieg"]
                okx.markt_verkauf(p["inst"], round(menge, 8))
            except Exception as e:  # noqa: BLE001
                print("  Notausstieg %s fehlgeschlagen: %s" % (p["inst"], e),
                      file=sys.stderr)
                behalten.append(p)
                continue
        print("  NOT-ZU %-10s @ %.6f  G/V %+.2f USD  (%s)"
              % (p["inst"], kurs, erloes - p["usd"], grund))
        journal(_jetzt(), "live" if live else "papier", "verkauf", p["inst"],
                "%.6f" % kurs, "%.2f" % erloes, "", "", grund)
    z["positionen"] = behalten


def pruefe_einstiege(z, vs, w, live, faktor=1.0):
    gehalten = {p["inst"] for p in z["positionen"]}
    eingesetzt = sum(p["usd"] for p in z["positionen"])
    if faktor != 1.0:
        print("  (Drawdown-Ratsche aktiv: Positionsgroesse x %.2f)" % faktor)
    for v in vs:
        if len(z["positionen"]) >= w["max_offene_positionen"]:
            break
        usd = round(v["usd"] * faktor, 2)
        if eingesetzt + usd > w["max_gesamt_usd"]:
            continue
        if v["inst"] in gehalten or in_abklingzeit(v["inst"], z, w):
            continue
        kauf_id = None
        if live:
            try:
                kauf_id = okx.markt_kauf(v["inst"], usd)
                d = okx.order_details(v["inst"], kauf_id)
                menge = float(d.get("accFillSz") or 0)
                if menge > 0:
                    okx.stop_setzen(v["inst"], round(menge, 8), v["stop"])
            except Exception as e:  # noqa: BLE001
                print("  Kauf %s fehlgeschlagen: %s" % (v["inst"], e),
                      file=sys.stderr)
                continue
        z["positionen"].append({
            "inst": v["inst"], "einstieg": v["einstieg"], "usd": usd,
            "stop": v["stop"], "ziel": v["ziel"], "eroeffnet": _heute(),
            "kauf_ord_id": kauf_id,
        })
        eingesetzt += usd
        gehalten.add(v["inst"])
        print("  AUF %-10s @ %.6f  Stop %.6f (-%.1f%%)  Ziel %.6f  %.2f USD"
              % (v["inst"], v["einstieg"], v["stop"], v["stop_pct"],
                 v["ziel"], usd))
        journal(_jetzt(), "live" if live else "papier", "kauf", v["inst"],
                "%.6f" % v["einstieg"], "%.2f" % (usd * (1 + GEBUEHR_PCT)),
                "%.6f" % v["stop"], "%.6f" % v["ziel"], "score %.1f" % v["score"])


# --- Freigabe von Hand (Handelsregeln Punkt 3) -------------------------------

# Sekunden ohne Bedienung, nach denen das Freigabefenster von selbst ablehnt.
# Das ist der tragende Schutz - nicht die Erkennung darunter: geht das Fenster
# je versehentlich in einer geplanten Aufgabe auf, blockiert es sie nicht,
# sondern sagt Nein und der Lauf handelt nicht.
FREIGABE_ZEITLIMIT_S = 120


def sitzung_da():
    """Sitzt jemand davor, der das Freigabefenster bedienen kann?

    Nur eine erste Huerde, keine Garantie: isatty() ist unter Windows nicht
    verlaesslich - in der Git-Bash meldet es auch dann ein Terminal, wenn
    stdin umgeleitet wurde (gemessen 02.09.2026). Verlassen wird sich
    deshalb auf FREIGABE_ZEITLIMIT_S, nicht auf diese Funktion.

    MAXHIRN_ROUTINE=1 setzt der Wrapper einer geplanten Aufgabe. Das ist die
    ausdrueckliche Ansage "hier sitzt niemand" und schlaegt alles andere."""
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


# Spur, unter der diese Datei im Dauerlauf und in freigabefenster.py steht.
SPUR = "scanner"


def zeitfenster_offen():
    """Hat Max am Handy freigegeben (freigabefenster.py)?

    Best effort: fehlt das Modul oder wirft es, gilt *nicht* freigegeben.
    Im Zweifel Papier - ein Fehler beim Lesen darf nie zu einer Order
    fuehren."""
    try:
        import freigabefenster
        return bool(freigabefenster.lade(SPUR).offen())
    except Exception:                                   # noqa: BLE001
        return False


def sperren_live(w, s):
    """Alles, was --live gerade verschliesst. Leere Liste = frei."""
    g = []
    if not w.get("handel_erlaubt"):
        g.append("wachen.json handel_erlaubt=false")
    if not okx.schluessel_vorhanden():
        g.append("OKX-Schluessel nicht gesetzt")
    if not s["freigabe_erfuellt"]:
        g.append("freigabe.erfuellt=false (Bedingung 1)")
    if not s["herzschlag_frisch"]:
        g.append("Herzschlag alt (Bedingung 3)")
    if s["ev_negativ"]:
        g.append("rollierender EV %.3f USD < 0 (Bedingung 5)"
                 % s["rollierender_ev"])
    # Punkt 3 der Handelsregeln, in zwei Fassungen: am Bildschirm das
    # Freigabefenster, im Dauerbetrieb das Zeitfenster. Eine muss offen
    # sein. Die Begruendung nennt immer das Freigabefenster, weil
    # dauerlauf.nur_fenster_fehlt genau darauf prueft, ob allein die
    # Freigabe noch fehlt - und nur dann fragt er am Handy nach.
    if not sitzung_da() and not zeitfenster_offen():
        g.append("Freigabefenster nicht offen - keine Sitzung am "
                 "Bildschirm und kein Zeitfenster (Handelsregeln Punkt 3)")
    return g


def freigabe_protokoll(vs, z, s):
    """Haelt fest, dass das Zeitfenster die Freigabe war.

    Der Bildschirmweg hat sein Protokoll in freigabe.py. Ohne diese Zeilen
    waere im Journal nicht zu sehen, welche Einstiege ohne Fenster
    freigegeben wurden. Best effort wie dort: ein Schreibfehler darf den
    Einstieg nicht verhindern."""
    try:
        sys.path.insert(0, str(HIER.parent))
        import freigabe
        for v in vs:
            freigabe.audit({
                "spur": SPUR, "ergebnis": "bestaetigt",
                "quelle": "zeitfenster", "modus": "live",
                "waehrung": "USD", "inst": v.get("inst"),
                "einstieg": v.get("einstieg"), "stop": v.get("stop"),
                "ziel": v.get("ziel"), "stop_pct": v.get("stop_pct"),
                "gebunden": v.get("usd"),
                "gebunden_gesamt": sum(p["usd"] for p in z["positionen"]),
                "offene_positionen": len(z["positionen"]),
                "ruecklauf_usd": s.get("ruecklauf_usd")})
    except Exception:                                   # noqa: BLE001
        pass


def hole_freigabe(vs, z, s):
    """Jeden Vorschlag im Fenster bestaetigen lassen. Gibt die bestaetigten
    zurueck - abgelehnt heisst leere Liste, und leer heisst kein Einstieg.

    Faellt das Fenster aus (Tk fehlt, Anzeige weg), wird nicht gehandelt.
    Ein Fehler beim Bestaetigen darf nie zu einem ungefragten Kauf werden."""
    sys.path.insert(0, str(HIER.parent))
    try:
        import freigabe
    except Exception as e:  # noqa: BLE001
        print("  Freigabefenster nicht verfuegbar (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []
    # Betraege in der Waehrung der Spur - hier USD, bei Spur 3 EUR. Die
    # Schluessel sind deshalb waehrungsneutral.
    bestand = {
        "gebunden": sum(p["usd"] for p in z["positionen"]),
        "offene_positionen": len(z["positionen"]),
        "verlust_gesamt": s["ruecklauf_usd"],
    }
    try:
        return freigabe.bestaetige(vs, "spot", bestand,
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


def zeige_wachen(w):
    """handeln.py --wachen: alle fuenf Bedingungen als Momentaufnahme, dazu die
    beiden Automatik-Reaktionen des Wochenlaufs - Bedingung 4 (spiegeln) und
    Bedingung 5 (bei negativem Erwartungswert die Sperre schliessen)."""
    z = lade_zustand()
    s = wp.lage(w, JOURNAL, z)
    print("=== Wachen-Status  %s ===" % _jetzt())
    print("  1 Freigabe erfuellt      %s   (Runden gesamt %d, davon Papier %d, seit %s)"
          % (s["freigabe_erfuellt"], s["runden_gesamt"], s["runden_papier"],
             s["erste_runde"] or "-"))
    print("  2 Ruecklauf              %.2f USD von Hoechststand %.2f  -> Faktor %.2f%s"
          % (s["ruecklauf_usd"], s["hoechststand_usd"], s["groessenfaktor"],
             "   >>> KILL-SWITCH" if s["kill"] else ""))
    print("  3 Herzschlag frisch     %s   (%s min alt, Grenze %d)"
          % (s["herzschlag_frisch"],
             "?" if s["herzschlag_alter_min"] is None
             else "%.0f" % s["herzschlag_alter_min"],
             w.get("herzschlag_max_minuten", 30)))
    print("  4 Journal-Zweitziel     %s" % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  5 Rollierender EV       %s%s"
          % ("n/a (zu wenig Runden)" if s["rollierender_ev"] is None
             else "%+.3f USD/Runde" % s["rollierender_ev"],
             "   >>> NEGATIV" if s["ev_negativ"] else ""))
    print()
    _spiegeln(w)
    if s["kill"] and wp.sperre_zu("Bedingung 2 (Wochenlauf): Ruecklauf %.2f USD >= Kill-Switch"
                                  % s["ruecklauf_usd"]):
        print("  -> Bedingung 2: handel_erlaubt auf false gesetzt.")
    if s["ev_negativ"] and wp.sperre_zu("Bedingung 5 (Wochenlauf): rollierender EV %.3f USD < 0"
                                        % s["rollierender_ev"]):
        print("  -> Bedingung 5: handel_erlaubt auf false gesetzt.")


# --- Hauptlauf ---------------------------------------------------------------

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

    # Live-Sperren pruefen - die sechs alten plus die Freigabe von Hand
    # (Punkt 3): am Bildschirm oder als Zeitfenster.
    live = False
    if modus == "live":
        gruende = sperren_live(w, s)
        if gruende:
            print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    vs = vorschlaege(bericht, w)
    print("=== Handeln (%s) | Bericht %s | %d Vorschlaege ==="
          % ("LIVE" if live else "Papier", bericht["datum"], len(vs)))

    z["modus"] = "live" if live else "papier"

    if modus == "vorschau":
        for v in vs:
            print("  %-10s Score %.1f  Einstieg %.6f  Stop %.6f (-%.1f%%)  Ziel %.6f"
                  % (v["inst"], v["score"], v["einstieg"], v["stop"],
                     v["stop_pct"], v["ziel"]))
        eing = sum(p["usd"] for p in z["positionen"])
        print("\nOffener Bestand: %d Positionen, %d USD gebunden"
              % (len(z["positionen"]), eing))
        # Auch hier die Sperren nennen, nicht nur unter --live:
        # dauerlauf.nur_fenster_fehlt liest genau diese Zeile, um zu
        # entscheiden, ob sich eine Freigabe-Anfrage ueberhaupt lohnt.
        # Ohne sie wurde nie gefragt - und ein /ja blieb folgenlos.
        g = sperren_live(w, s)
        if g:
            print("Live waere gesperrt durch: " + "; ".join(g))
        return

    # Bedingung 2 - Kill-Switch: alles zu, Sperre zu, Schluss.
    if s["kill"]:
        print("- KILL-SWITCH: Ruecklauf %.2f USD >= %g -> Notausstieg + Sperre -"
              % (s["ruecklauf_usd"], w["kill_switch_gesamt_usd"]))
        flach_stellen(z, live, "kill_switch")
        if wp.sperre_zu("kill_switch: Ruecklauf %.2f USD" % s["ruecklauf_usd"]):
            print("  wachen.json handel_erlaubt -> false")
        schreibe_zustand(z)
        # Bedingung 4 gilt auch hier: gerade der Notausstieg gehoert ausser
        # Haus (Muster: der Herzschlag-Zweig direkt darunter).
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    # Bedingung 3 - Herzschlag alt: alles zu, dieser Lauf handelt nicht mehr.
    # Der naechste Lauf mit frischem Herzschlag faengt normal wieder an.
    if not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Notausstieg, kein Handel dieser Lauf -"
              % ("?" if s["herzschlag_alter_min"] is None
                 else "%.0f" % s["herzschlag_alter_min"],
                 w.get("herzschlag_max_minuten", 30)))
        flach_stellen(z, live, "herzschlag_alt")
        z["modus"] = "papier"
        schreibe_zustand(z)
        if w.get("journal_zweitziel"):
            _spiegeln(w)
        return

    # Ausstiege laufen nie durch das Fenster: ein Stop muss greifen, auch
    # wenn niemand davorsitzt.
    print("- Ausstiege -")
    pruefe_ausstiege(z, live)

    print("- Einstiege -")
    faktor = s["groessenfaktor"]
    if live and vs:
        # Punkt 3 der Handelsregeln: scharf geschaltet wird von Hand. Der
        # Faktor der Drawdown-Ratsche wird vorher eingerechnet, damit im
        # Fenster die Zahl steht, die auch gekauft wird.
        vs = [dict(v, usd=round(v["usd"] * faktor, 2), cr=2.0) for v in vs]
        faktor = 1.0
        if sitzung_da():
            # Am Bildschirm: das Fenster fragt je Einstieg einzeln.
            vs = hole_freigabe(vs, z, s)
            if not vs:
                print("  Freigabe abgelehnt - kein Einstieg in diesem Lauf.")
        else:
            # Kein Bildschirm, aber ein offenes Zeitfenster. Es wurde beim
            # Sperrenpruefen geprueft; hier noch einmal, weil dazwischen
            # Netzabfragen liegen und /stop in der Zeit greifen kann.
            if zeitfenster_offen():
                try:
                    import freigabefenster
                    stand = freigabefenster.lade(SPUR).text()
                except Exception:                       # noqa: BLE001
                    stand = "offen"
                print("  Freigabe ueber das Zeitfenster (%s) - %d Einstieg(e) "
                      "ohne Fenster am Bildschirm." % (stand, len(vs)))
                freigabe_protokoll(vs, z, s)
            else:
                print("  Zeitfenster ist inzwischen zu - kein Einstieg.")
                vs = []
    pruefe_einstiege(z, vs, w, live, faktor)

    eing = sum(p["usd"] for p in z["positionen"])
    print("\nStand: %d/%d Positionen, %d/%d USD gebunden"
          % (len(z["positionen"]), w["max_offene_positionen"],
             eing, w["max_gesamt_usd"]))
    schreibe_zustand(z)

    # Bedingung 4 - Journal nach jedem Zyklus ausser Haus.
    if w.get("journal_zweitziel"):
        _spiegeln(w)


def main():
    with ereignis.lauf("handel/scanner"):
        return _main()


def _main():
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


if __name__ == "__main__":
    main()
