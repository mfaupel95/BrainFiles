"""Das Haus-Buch der Bot-Spuren - eine Umsetzung fuer alle.

Jede Bot-Spur hat dieselbe Buchhaltung: Wachen (mit Risikostufe), Zustand,
Journal, Kopie ausser Haus (Bedingung 4), Groesse ueber die Ratsche, Stop und
Ziel, Positionsverwaltung. Was sie unterscheidet, ist allein die QUELLE und die
REGEL - und beides liefert die Spur selbst als zwei Funktionen:

    quelle(w)        -> {instrument: daten}       (Abruf, darf Fehler melden)
    signal(daten, w) -> "long" | "short" | None   (die Regel)

Warum eine gemeinsame Datei: drei Spuren mit drei Kopien derselben Buchhaltung
waeren drei Stellen, an denen ein Fehler (falscher G/V auf den Kurswert,
vergessene Spiegelung) einzeln auftreten kann. Dieselbe Ueberlegung wie bei
`ratschen.py` und `stoerungen.py`.

Grenze: `moondev_funding` fuehrt sein Buch noch selbst (es war die erste Spur
und ist einzeln getestet). Beim naechsten Anfassen gehoert es hierher.
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone

# --- Gemeinsame Abhaengigkeiten ueber den PFAD laden -----------------------
HANDEL = os.path.dirname(os.path.abspath(__file__))
SCANNER = os.path.join(HANDEL, "scanner")
# Bus fuer `ereignis.lauf` (Meldung an den Bus wie jede andere Spur). Er liegt
# neben dem Handel-Ordner; ohne den Pfad scheitert der Import im Test.
BUS = os.path.join(os.path.dirname(HANDEL), "Bus")
for _p in (SCANNER, HANDEL, BUS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from importlib.util import module_from_spec, spec_from_file_location  # noqa: E402

import wachen_pruefung as wp  # noqa: E402


def _lade_modul(name):
    spec = spec_from_file_location(name, os.path.join(HANDEL, name + ".py"))
    modul = module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


ratschen = _lade_modul("ratschen")
risikostufe = _lade_modul("risikostufe")

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund"]

SCHREIBEN = True

# Test-Seams, die jede Spur mitbenutzt: None -> echte Uhr/echte Quelle.
zeit_quelle = None


def jetzt():
    if zeit_quelle:
        return zeit_quelle()
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Dateien ---------------------------------------------------------------

def pfade(ordner):
    """(Wachen, Zustand, Journal) EINER Spur - Zustand/Journal je Risikostufe."""
    return (os.path.join(ordner, "wachen.json"),
            risikostufe.datei(os.path.join(ordner, "zustand.json")),
            risikostufe.datei(os.path.join(ordner, "handelsjournal.csv")))


def lade_wachen(wachen_pfad):
    with open(wachen_pfad, encoding="utf-8") as f:
        return risikostufe.skaliere(json.load(f))


def lade_zustand(zustand_pfad):
    try:
        with open(zustand_pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"positionen": [], "modus": "papier", "letzter_lauf": None,
                "verlust_usd": 0.0}


def schreibe_zustand(zustand_pfad, z):
    z["letzter_lauf"] = jetzt()
    with open(zustand_pfad, "w", encoding="utf-8") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")


def journal(journal_pfad, **felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(journal_pfad)
    with open(journal_pfad, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN)
        if neu:
            w.writeheader()
        w.writerow(felder)


def spiegeln(zustand_pfad, journal_pfad, z, w):
    """Bedingung 4: Journal und Zustand ausser Haus (Muster swap/handeln.py)."""
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([journal_pfad, zustand_pfad], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info,
                              lambda zz: schreibe_zustand(zustand_pfad, zz)) and ok:
        wp.spiegele_journal([zustand_pfad], ziel)


# --- Positionen ------------------------------------------------------------

def groessenfaktor(ruecklauf, w):
    return ratschen.groessenfaktor(ruecklauf, w)


def einstieg(z, inst, seite, kurs, w, faktor, grund, stop_pct=None,
            ziel_preis=None):
    """Eine Position eroeffnen - Stop in Prozent, Ziel als Preis oder Vielfaches.

    `ziel_preis` gibt es fuer Signale, deren Ziel ein MARKTPUNKT ist (die
    IV-Wand: der Strike mit dem groessten Open Interest). Ohne ihn gilt das
    R-Vielfache aus den Wachen. Beide Wege setzen denselben Stop - daran haengt
    die Groesse, und die muss zur Ausstiegslinie passen.
    """
    if not z.get("positionen"):
        z["positionen"] = []
    if len(z["positionen"]) >= w.get("max_offene_positionen", 3):
        return None
    if any(p.get("inst") == inst for p in z["positionen"]):
        return None
    if not kurs or kurs <= 0 or seite not in ("long", "short"):
        return None

    pct = float(stop_pct if stop_pct is not None else w.get("stop_prozent", 6.0))
    pct = max(pct, w.get("pflicht_stop_prozent_min", 5.0))
    pct = min(pct, w.get("pflicht_stop_prozent_max", 12.0))
    vz = 1 if seite == "long" else -1
    abstand = kurs * pct / 100.0
    r = float(w.get("ziel_r_vielfaches", 1.5))
    stop = kurs - vz * abstand
    if ziel_preis:
        # Ein Marktziel muss auf der richtigen Seite liegen: ein Ziel hinter
        # dem Einstieg waere sofort erreicht (oder nie) - beides ist kein
        # Handel, sondern ein Rechenfehler.
        if (seite == "long" and float(ziel_preis) <= kurs) or \
                (seite == "short" and float(ziel_preis) >= kurs):
            return None
        ziel = float(ziel_preis)
    else:
        ziel = kurs + vz * r * abstand

    nominel = w["risiko_je_position_usd"] / (pct / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"]) * faktor
    if nominel <= 0:
        return None

    p = {"inst": inst, "seite": seite, "einstieg": kurs, "stop": stop,
         "ziel": ziel, "stop_pct": pct, "nominal": nominel,
         "eroeffnet_zeit": jetzt()}
    z["positionen"].append(p)
    return p


def pruefe_ausstiege(z, kurse, w, journal_pfad, nur=None):
    """Stop und Ziel pruefen. Der G/V laeuft auf den NOMINALWERT.

    Die rohe Kursdifferenz war der Fehler vom 15.09.2026: bei BTC ein Faktor
    von Zehntausenden, der Erloes stand in Kurshoehe im Journal.
    """
    behalten = []
    for p in z.get("positionen", []):
        if nur is not None and p.get("inst") != nur:
            behalten.append(p)
            continue
        kurs = kurse.get(p["inst"])
        if not kurs:
            behalten.append(p)
            continue
        grund = None
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
        if not grund:
            behalten.append(p)
            continue

        vz = 1 if p["seite"] == "long" else -1
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        print("AUSSTIEG (%s) %s %.6f G/V %+.2f USD"
              % (grund, p["inst"], kurs, gv))
        journal(journal_pfad, zeit=jetzt(), modus="papier", aktion="verkauf",
                inst=p["inst"], seite=p["seite"], preis="%.6f" % kurs,
                einsatz_usd="%.2f" % (p["nominal"] + gv),
                stop="%.6f" % p["stop"], ziel="%.6f" % p["ziel"],
                stop_pct="%.2f" % p["stop_pct"], grund=grund)

    z["positionen"] = behalten


# --- Das Lauf-Geruest ------------------------------------------------------

def zyklus(ordner, quelle, signal, modus, ereignis_name, ziel=None):
    """Ein Zyklus einer Spur. `quelle(w)`, `signal(daten, w)` kommen von ihr.

    `ziel(daten, w)` ist optional und liefert ein ZIEL ALS MARKTPUNKT (die
    IV-Wand) - dann steht im Buch nicht das R-Vielfache, sondern diese Linie.
    Ohne `ziel` bleibt es beim Vielfachen aus den Wachen.

    Reihenfolge: erst die Ratsche (Buch-Ruecklauf), dann Ausstiege, dann
    Einstiege. Bei `--vorschau` wird gerechnet und nichts geschrieben; ein
    `--live` gibt es in diesen Spuren nicht (siehe die README der Spur).
    """
    import ereignis

    wachen_pfad, zustand_pfad, journal_pfad = pfade(ordner)

    def _lauf():
        w = lade_wachen(wachen_pfad)
        z = lade_zustand(zustand_pfad)
        z.setdefault("positionen", [])

        if modus == "wachen":
            print(json.dumps(wp.lage(w, journal_pfad, z), indent=2,
                             ensure_ascii=False))
            return 0

        s = wp.lage(w, journal_pfad, z)
        ruecklauf = s.get("ruecklauf_usd", 0.0)
        faktor = groessenfaktor(ruecklauf, w)

        if s.get("kill"):
            print("- Kill-Schwelle erreicht (%.2f USD Ruecklauf). Alles flach."
                  % ruecklauf)
            z["positionen"] = []
            schreibe_zustand(zustand_pfad, z)
            spiegeln(zustand_pfad, journal_pfad, z, w)
            return 0

        daten, kurse, fehler = quelle(w)
        for f in fehler:
            print("Uebersprungen (%s)" % f, file=sys.stderr)
        if not daten:
            print("Keine Daten - Zyklus ohne Buchung beendet (%s)"
                  % ("; ".join(fehler)[:200] if fehler else "keine Instrumente"))
            if modus == "vorschau":
                print("Vorschau: keine Dateien geschrieben.")
            return 0

        pruefe_ausstiege(z, kurse, w, journal_pfad)
        if modus == "vorschau":
            for inst in sorted(daten):
                seite = signal(daten[inst], w)
                if seite:
                    linie = ziel(daten[inst], w) if ziel else None
                    print("Vorschau: Einstieg waere %s %s%s"
                          % (seite.upper(), inst,
                             ("  Ziel %.2f" % linie) if linie else ""))
            print("Vorschau: keine Dateien geschrieben.")
            return 0

        for inst in sorted(daten):
            seite = signal(daten[inst], w)
            if not seite:
                continue
            p = einstieg(z, inst, seite, kurse.get(inst), w, faktor,
                         w.get("grund", "moondev_bot"),
                         ziel_preis=(ziel(daten[inst], w) if ziel else None))
            if p:
                print("EINSTIEG %s %s @ %.6f  Stop %.2f%%  Ziel %.6f  "
                      "Nominal %.2f USD"
                      % (seite.upper(), inst, p["einstieg"], p["stop_pct"],
                         p["ziel"], p["nominal"]))
                journal(journal_pfad, zeit=jetzt(), modus="papier",
                        aktion="kauf", inst=inst, seite=seite,
                        preis="%.6f" % p["einstieg"],
                        einsatz_usd="%.2f" % p["nominal"],
                        stop="%.6f" % p["stop"], ziel="%.6f" % p["ziel"],
                        stop_pct="%.2f" % p["stop_pct"],
                        # Der Grund stand hier fest auf "moondev_bot", obwohl
                        # jede Spur in ihrer wachen.json einen eigenen Namen
                        # fuehrt. Ein Feld, das immer dasselbe sagt, ist keine
                        # Auskunft. `_grund` setzt eine Spur, die etwas
                        # Genaueres weiss (die LLM-Spuren schreiben Aktion und
                        # Confidence hinein).
                        grund=(w.get("_grund") or w.get("grund")
                               or "moondev_bot"))

        schreibe_zustand(zustand_pfad, z)
        spiegeln(zustand_pfad, journal_pfad, z, w)
        return 0

    with ereignis.lauf(ereignis_name):
        return _lauf()
