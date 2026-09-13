"""Die Omniquant-Spur: handelt die Signale, die prognose.py findet - als Papierbuch.

Angelegt am 13.09.2026 auf Max' Anweisung ("Omniquant AI trader in Handel/
implementieren"). "Omniquant" ist hier keine externe API und kein fremder
Feed - es ist die Idee aus der Recherche vom 10.09.2026 (omniquant.trade):
ein Trader, der nur handelt, was eine probabilistische Bewertung mit Toren
als guenstig ausweist, und der sich enthaelt, wenn kein frisches Signal da
ist. Damalige Empfehlung, umgesetzt: dieselbe Kategorie Werkzeug auf eigenen
Daten und unter eigener Kontrolle, nicht der kommerzielle Dienst.

WAS ER IST
----------
Die Signalquelle ist der volle Prognose-Bericht (prognose_berichte/
neuester.json), den der Lauf von prognose.py schreibt: Treffer mit Richtung,
Einstieg, Stop und Ziel, alle Tore offen. Diese Spur bucht sie als
Papierpositionen - mit Kosten (Gebuehr + Slippage) auf beiden Seiten, einem
Zwangsschluss nach max_halte_dauer_tagen und einem Kill-Switch ueber die
kumulierten Verluste. Was am Ende uebrig bleibt, ist die Antwort auf die
Frage, ob die Prognose-Treffer nach Kosten tragen.

WAS ER NICHT IST
----------------
Kein Orderpfad. Kein Broker-Aufruf, keine Position am Markt. `--live`
verweigert mit genau einem Grund, in dem das Wort Freigabefenster NICHT
vorkommt - so fragt der Dauerlauf keine Freigabe an, die nichts oeffnen
kann (Muster: spiegel-Spur, papierfest).

GLEICHE WAHRHEIT
----------------
Die Spur erfindet keine zweite Formel: Stop und Ziel kommen aus dem Bericht
(dort gerechnet gegen 20-/60-Tage-Extrema), nicht neu geschaetzt. Der
Einstieg ist der aktuelle Kurs - aber nur, wenn er noch zwischen Stop und
Ziel liegt (long: stop < kurs < ziel; short: ziel < kurs < stop). Liegt er
dahinter, ist das Signal verfallen und wird uebersprungen.

Aufruf:
    python handeln.py --vorschau    # was waere dran, ohne zu schreiben
    python handeln.py --papier      # ein Papierzyklus mit Journal
    python handeln.py --wachen      # Grenzen als Momentaufnahme
    python handeln.py --live        # verweigert, nennt den Grund
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (HIER, HANDEL, os.path.join(HANDEL, "scanner"),
          os.path.join(HANDEL, os.pardir, "Bus")):
    if p not in sys.path:
        sys.path.insert(0, p)

import ereignis                                            # noqa: E402
import okx                                                 # noqa: E402

WACHEN = os.path.join(HIER, "wachen.json")
ZUSTAND = os.path.join(HIER, "zustand.json")
JOURNAL = os.path.join(HIER, "handelsjournal.csv")
DEFAULT_BERICHT = os.path.join(HANDEL, "prognose_berichte", "neuester.json")

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "wert_usd", "stop", "ziel", "grund"]

# Ob geschrieben wird. Die Vorschau stellt das ab (siehe journal()).
SCHREIBEN = True

# --- Test-Seams -------------------------------------------------------------
# None -> echte Quelle. Tests setzen Lambda/dict und stellen in tearDown
# zurueck (Mechanik wie kerzen_quelle bei den anderen Spuren).
letzter_kurs_quelle = None     # f(inst) -> float
bericht_quelle = None          # None -> DEFAULT_BERICHT lesen, sonst dict


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


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
        s = csv.DictWriter(f, fieldnames=SPALTEN, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in SPALTEN})


# --- Signalquelle -----------------------------------------------------------

def lade_bericht():
    """Der volle Prognose-Bericht. None, wenn er zu alt ist - Abstention."""
    if bericht_quelle is not None:
        b = bericht_quelle
    else:
        try:
            with open(DEFAULT_BERICHT, encoding="utf-8") as f:
                b = json.load(f)
        except (OSError, ValueError):
            return None, "kein Bericht (prognose_berichte/neuester.json fehlt)"
    try:
        erzeugt = datetime.fromisoformat(b.get("erzeugt", ""))
    except ValueError:
        return None, "Bericht ohne Zeitstempel (erzeugt fehlt)"
    alter_h = (datetime.now(timezone.utc) - erzeugt).total_seconds() / 3600
    w = lade_wachen()
    max_alter = w.get("max_bericht_alter_stunden", 26)
    if alter_h > max_alter:
        return None, "Bericht %.1f h alt, Grenze %g h" % (alter_h, max_alter)
    return b, None


def kandidaten(z, w):
    """Treffer aus dem Bericht als Kandidaten, frisch und noch gueltig.

    Ein Treffer ohne Richtung ist keine Auskunft (Befund aus prognose.py):
    er wird uebersprungen, nicht geraten. Einstieg ist der aktuelle Kurs,
    aber nur, wenn er noch zwischen Stop und Ziel liegt - sonst ist das
    Signal verfallen. Bereits offene oder schon einmal eroeffnete Paare
    kommen nicht doppelt (Merkliste je inst+Richtung im Zustand).
    """
    b, fehler = lade_bericht()
    if b is None:
        return [], fehler

    aus = []
    for t in b.get("treffer", []):
        richtung = t.get("richtung")
        if richtung not in ("long", "short"):
            continue                       # altes Format oder kaputt: ueberspringen
        inst = t.get("inst")
        if not inst:
            continue
        stop = t.get("stop")
        ziel = t.get("ziel")
        if not stop or not ziel:
            continue
        try:
            kurs = (letzter_kurs_quelle or okx.letzter_kurs)(inst)
            kurs = float(kurs)
        except Exception as e:             # noqa: BLE001
            print("  %-14s Kurs nicht abrufbar (%s) - Kandidat uebersprungen"
                  % (inst, e))
            continue
        if richtung == "long" and not (stop < kurs < ziel):
            continue
        if richtung == "short" and not (ziel < kurs < stop):
            continue
        offen = any(p.get("inst") == inst and p.get("seite") == richtung
                    for p in z.get("positionen", []))
        if offen:
            continue
        # Merkliste: nur Eintraege vom HEUTIGEN Tag sperren den
        # Wiedereinstieg. Ein frischer Bericht morgen mit neuen Kerzen und
        # neuen Grenzen ist eine neue Lage - ein Eintrag von gestern darf
        # sie nicht fuer immer blockieren (Tor, das nie aufgeht).
        heute = _heute()
        if any(m.get("inst") == inst and m.get("seite") == richtung
               and m.get("am") == heute
               for m in z.get("erledigt", [])):
            continue
        aus.append({"inst": inst, "seite": richtung, "kurs": kurs,
                    "stop": stop, "ziel": ziel, "score": t.get("score"),
                    "cr": t.get("cr")})
    return aus, None


# --- Einstieg ---------------------------------------------------------------

def _nominal(inst, kurs):
    """Positionsgroesse: fester Einsatz je Position (Spot, ohne Hebel)."""
    w = lade_wachen()
    return w.get("max_einsatz_je_position_usd", 50)


def _kostenfaktor(w, seite):
    """Kosten auf einer Seite: Slippage + Gebuehr, in Prozent des Einsatzes.

    Long kauft zum Kurs * (1 + kosten), short zum Kurs * (1 - kosten) -
    der unguenstigere Preis je Richtung. Beim Ausstieg wirkt derselbe
    Faktor noch einmal (siehe _ergebnis).
    """
    kosten = (w.get("slippage_pct", 0.15) + w.get("gebuehr_pct", 0.1)) / 100.0
    return 1.0 + kosten if seite == "long" else 1.0 - kosten


def eroeffne(z, w, kand):
    vz = 1 if kand["seite"] == "long" else -1
    nominal = _nominal(kand["inst"], kand["kurs"])
    p = {
        "inst": kand["inst"], "seite": kand["seite"],
        "einstieg": kand["kurs"],
        "stop": kand["stop"], "ziel": kand["ziel"],
        "nominal": nominal,
        "eroeffnet": _heute(),
        "score": kand.get("score"), "cr": kand.get("cr"),
    }
    z.setdefault("positionen", []).append(p)
    journal(zeit=_jetzt(), modus="papier", aktion="EINSTIEG",
            inst=p["inst"], seite=p["seite"], preis=p["einstieg"],
            einsatz_usd=nominal, stop=p["stop"], ziel=p["ziel"],
            grund="prognose-treffer")
    print("OMNIQUANT EINSTIEG: %s %s @ %.6g, Stop %.6g, Ziel %.6g, "
          "Einsatz %.2f USD"
          % (p["inst"], p["seite"], p["einstieg"], p["stop"], p["ziel"],
             nominal))


# --- Ausstieg ---------------------------------------------------------------

def _ergebnis(p, kurs, w):
    """Was vom Einsatz zurueckkommt. Kosten auf beiden Seiten.

    Long: erloes = nominal * (1 + bewegung) * (1 - kosten)
    Short: erloes = nominal * (1 - bewegung) * (1 - kosten)
    Die Kosten sind beim Einstieg bereits eingepreist (siehe _kostenfaktor),
    hier wirkt der zweite Faktor - zusammen sind es zwei Seiten wie im
    echten Handel.
    """
    vz = 1 if p["seite"] == "long" else -1
    bewegung = vz * (kurs - p["einstieg"]) / p["einstieg"]
    kosten = (w.get("slippage_pct", 0.15) + w.get("gebuehr_pct", 0.1)) / 100.0
    return p["nominal"] * (1.0 + bewegung) * (1.0 - kosten)


def schliesse(z, p, grund, kurs, w, live):
    ergebnis = _ergebnis(p, kurs, w)
    verlust = p["nominal"] - ergebnis
    if verlust > 0:
        z["verluste_usd"] = z.get("verluste_usd", 0.0) + verlust
    z["positionen"] = [x for x in z["positionen"] if x is not p]
    z.setdefault("erledigt", []).append(
        {"inst": p["inst"], "seite": p["seite"], "am": _heute(),
         "grund": grund, "wert_usd": round(ergebnis, 2)})
    journal(zeit=_jetzt(), modus="papier", aktion="AUSSTIEG",
            inst=p["inst"], seite=p["seite"], preis=kurs,
            einsatz_usd=p["nominal"], wert_usd=round(ergebnis, 2),
            stop=p["stop"], ziel=p["ziel"], grund=grund)
    print("AUSSTIEG (%s): %s %s @ %.6g, wert %.2f USD"
          % (grund, p["inst"], p["seite"], kurs, ergebnis))


def pruefe_ausstiege(z, w):
    behalten = []
    for p in z.get("positionen", []):
        try:
            kurs = float((letzter_kurs_quelle or okx.letzter_kurs)(p["inst"]))
        except Exception as e:                           # noqa: BLE001
            print("  Kurs %s nicht abrufbar (%s) - Position bleibt"
                  % (p["inst"], e))
            behalten.append(p)
            continue
        vz = 1 if p["seite"] == "long" else -1
        grund = None
        if vz * (kurs - p["stop"]) <= 0:
            grund = "stop"
        elif vz * (kurs - p["ziel"]) >= 0:
            grund = "ziel"
        else:
            # Zwangsschluss: ein Signal, das sich in max_halte_dauer_tagen
            # nicht bewegt hat, ist verfallen.
            try:
                eroeffnet = datetime.fromisoformat(p["eroeffnet"]).date()
            except (TypeError, ValueError):
                eroeffnet = None
            if eroeffnet is not None:
                dauer = (datetime.now(timezone.utc).date() - eroeffnet).days
                if dauer >= w.get("max_halte_dauer_tage", 14):
                    grund = "zwangsschluss"
        if grund:
            schliesse(z, p, grund, kurs, w, live=False)
        else:
            behalten.append(p)
    z["positionen"] = behalten
    # Merkliste aufraeumen: nur Eintraege von heute behalten. Alles aeltere
    # blockiert ohnehin nichts mehr (kandidaten prueft nur am == heute) und
    # waere nur Rauschen im Zustand.
    z["erledigt"] = [m for m in z.get("erledigt", [])
                     if m.get("am") == _heute()]


def herzschlag_alt(z, w):
    """Bedingung 3: der letzte Lauf darf nicht zu lange zurueckliegen."""
    letzter = z.get("letzter_lauf")
    if not letzter:
        return False
    try:
        alter_min = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(letzter)).total_seconds() / 60
    except ValueError:
        return False
    return alter_min > w.get("herzschlag_max_minuten", 90)


# --- Sperren ----------------------------------------------------------------

def sperren_live(w, z):
    """Gruende, warum --live nicht scharf schalten kann. Kein Freigabefenster.

    Das Wort "Freigabefenster" darf hier NICHT vorkommen: dauerlauf.nur_
    fenster_fehlt() liest die --vorschau-Zeile und fragt nur dann eine
    Freigabe an, wenn genau ein Grund "Freigabefenster" enthaelt. Diese Spur
    hat keinen Live-Zweig - also keinen Grund, jemals zu fragen.
    """
    g = []
    if not w.get("handel_erlaubt"):
        g.append("kein Live-Zweig: Omniquant fuehrt ein Papierbuch auf dem "
                 "Prognose-Bericht (handel_erlaubt=false)")
    if z.get("verluste_usd", 0.0) >= w.get("max_gesamt_risiko_usd", 500):
        g.append("Kill-Switch: Verluste %.2f USD >= %g"
                 % (z.get("verluste_usd", 0.0),
                    w.get("max_gesamt_risiko_usd", 500)))
    return g


def zeige_wachen(w):
    print("=== OMNIQUANT Wachen ===")
    for k in ("handel_erlaubt", "max_einsatz_je_position_usd", "max_offen",
              "max_neu_je_zyklus", "max_gesamt_risiko_usd", "gebuehr_pct",
              "slippage_pct", "max_halte_dauer_tage", "herzschlag_max_minuten",
              "max_bericht_alter_stunden"):
        print("  %-28s %s" % (k, w.get(k)))
    print("  Signalquelle: %s" % w.get("signal_quelle", "prognose_berichte/neuester.json"))


# --- Lauf -------------------------------------------------------------------

def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = lade_wachen()

    if modus == "wachen":
        zeige_wachen(w)
        return

    z = lade_zustand()

    live = False
    if modus == "live":
        g = sperren_live(w, z)
        if g:
            print("--live angefordert, aber gesperrt: " + "; ".join(g))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    if herzschlag_alt(z, w):
        print("- Herzschlag alt -> Papierbuch flachgestellt -")
        for p in list(z.get("positionen", [])):
            try:
                kurs = float((letzter_kurs_quelle or okx.letzter_kurs)(p["inst"]))
            except Exception as e:                       # noqa: BLE001
                kurs = p["einstieg"]
                print("  Kurs %s nicht abrufbar (%s) - zum Einstiegskurs "
                      "geschlossen" % (p["inst"], e))
            schliesse(z, p, "herzschlag", kurs, w, live=False)
        z["modus"] = "papier"
        schreibe_zustand(z)
        return

    # Kill-Switch: keine neuen Einstiege, wenn die kumulierten Verluste die
    # Grenze erreicht haben. Offene Positionen laufen weiter aus.
    kill = z.get("verluste_usd", 0.0) >= w.get("max_gesamt_risiko_usd", 500)

    kand, fehler = kandidaten(z, w)
    print("=== OMNIQUANT handeln (%s) | %d Kandidaten | %s ==="
          % ("LIVE" if live else "Papier", len(kand),
             fehler or "Bericht frisch"))
    if kill:
        print("- KILL-SWITCH: Verluste %.2f USD >= %g, keine neuen Einstiege -"
              % (z.get("verluste_usd", 0.0), w.get("max_gesamt_risiko_usd", 500)))

    if modus == "vorschau":
        for k in kand[:10]:
            print("  %-14s %-5s @ %.6g  Stop %.6g  Ziel %.6g  Score %s  C/R %s"
                  % (k["inst"], k["seite"], k["kurs"], k["stop"], k["ziel"],
                     k.get("score") if k.get("score") is not None else "?",
                     k.get("cr") if k.get("cr") is not None else "?"))
        gebunden = sum(p.get("nominal", 0) for p in z.get("positionen", []))
        print("\nOffener Bestand: %d Positionen, %.2f von %g USD Einsatz"
              % (len(z.get("positionen", [])), gebunden,
                 w.get("max_gesamt_risiko_usd", 500)))
        g = sperren_live(w, z)
        if g:
            print("Live waere gesperrt durch: " + "; ".join(g))
        return  # bewusst kein schreibe_zustand: eine Vorschau schreibt nicht

    z["modus"] = "live" if live else "papier"
    pruefe_ausstiege(z, w)

    if not kill:
        freie = w.get("max_offen", 10) - len(z.get("positionen", []))
        for k in kand[:max(0, min(freie, w.get("max_neu_je_zyklus", 5)))]:
            eroeffne(z, w, k)

    gebunden = sum(p.get("nominal", 0) for p in z.get("positionen", []))
    print("\nBestand: %d Positionen, %.2f von %g USD Einsatz, "
          "kumulierte Verluste %.2f USD"
          % (len(z.get("positionen", [])), gebunden,
             w.get("max_gesamt_risiko_usd", 500),
             z.get("verluste_usd", 0.0)))
    schreibe_zustand(z)


def main():
    # omniquant/handeln.py ist der automatische Einstieg (dauerlauf.py ruft
    # dieses Skript per subprocess auf) - es meldet sich damit am Bus.
    with ereignis.lauf("handel/omniquant"):
        return _main()


def _main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier")
    g.add_argument("--live", action="store_const", dest="modus", const="live")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen")
    a = p.parse_args()
    lauf(a.modus or "papier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
