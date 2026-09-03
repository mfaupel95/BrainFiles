"""Bedingungen 1-5 aus Wissen/Handelsregeln.md fuer die zweite Spur (XPERP).

Angelegt am 03.09.2026, zusammen mit handeln.py. Bis dahin hatte diese Spur
keinen Live-Pfad und damit nichts, woran die Bedingungen 2/3/5 haetten
greifen koennen - so stand es auch in T-019.

Die Rechnung steht nur einmal im Haus: sie kommt aus
scanner/wachen_pruefung.py und wird hier importiert, nicht abgeschrieben -
Drawdown-Kurve, Herzschlag-Alter, rollierender Erwartungswert, Spiegelung.
Genau so macht es kraken/wachen_kraken.py seit dem 02.09.2026.

DREI DINGE SIND HIER ANDERS ALS BEI SPOT
----------------------------------------
1. **Gerechnet wird auf Margin, nicht auf den Einsatz.** Der Rahmen
   max_margin_gesamt_usd begrenzt den Einschuss; der Positionswert liegt
   beim Hebelfachen davon. Wer hier Nominal gegen den Rahmen prueft, sperrt
   bei einem Fuenftel des erlaubten Risikos - wer umgekehrt Margin gegen das
   Nominal-Risiko prueft, laesst das Fuenffache zu.

2. **Eine Runde kann auch ohne Ausstieg Geld kosten: Funding.** Es faellt
   alle 8 Stunden an, ist im Journal eine eigene Zeile und geht in die
   Runden-Rechnung ein. Ein Papierlauf ohne Funding empfiehlt eine Strategie,
   die live verliert - dieselbe Falle wie die Gebuehr bei Spur 3.

3. **Short existiert.** Die Runde ist nicht "kauf dann verkauf", sondern
   "eroeffnen dann schliessen", und die Richtung steht in einer eigenen
   Spalte.

Kein Netz, kein OKX. Alles aus handelsjournal.csv und zustand.json.
Einziger Schreibzugriff auf wachen.json ist sperre_zu() - und nur in eine
Richtung: handel_erlaubt von true auf false.
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"

# Die geteilte Rechnung. Bricht dieser Import, ist scanner/wachen_pruefung.py
# umgebaut worden - dann gehoert diese Spur mitgezogen, nicht abgekoppelt.
sys.path.insert(0, str(HIER.parent / "scanner"))
import wachen_pruefung as basis  # noqa: E402

drawdown = basis.drawdown
herzschlag_frisch = basis.herzschlag_frisch
rollierender_ev = basis.rollierender_ev
spiegele_journal = basis.spiegele_journal
freigabe_erfuellt = basis.freigabe_erfuellt


# --- Runden aus dem Journal ------------------------------------------------

def runden_aus_journal(journal_pfad):
    """Jede abgeschlossene Runde mit ihrem Ergebnis in USD, FIFO je Kontrakt.

    Journalspalten: eroeffnen-Zeile margin_usd = eingesetzter Einschuss samt
    Eroeffnungsgebuehr, schliessen-Zeile margin_usd = was davon zurueckkommt,
    nach Gebuehr. Funding-Zeilen tragen aktion=funding und werden der offenen
    Position zugeschlagen, nicht als eigene Runde gezaehlt.

    Die Gebuehr steckt also in den Zahlen, nicht daneben - sonst sieht der
    Papierlauf besser aus als die Wirklichkeit, und genau daran ist in
    Wissen/Handelsbots.md schon eine Rueckrechnung gescheitert.
    """
    p = Path(journal_pfad)
    if not p.exists():
        return []
    offen = {}
    funding = {}
    runden = []
    with p.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            inst = r.get("inst")
            try:
                betrag = float(r["margin_usd"])
            except (TypeError, ValueError, KeyError):
                continue
            aktion = r.get("aktion")

            if aktion == "eroeffnen":
                offen.setdefault(inst, []).append(betrag)
                funding.setdefault(inst, []).append(0.0)
            elif aktion == "funding" and funding.get(inst):
                # Auf die aelteste offene Position dieses Kontrakts. Positiv
                # = gezahlt, negativ = bekommen.
                funding[inst][0] += betrag
            elif aktion == "schliessen" and offen.get(inst):
                einsatz = offen[inst].pop(0)
                fd = funding[inst].pop(0) if funding.get(inst) else 0.0
                runden.append({
                    "zeit": r["zeit"], "inst": inst, "modus": r["modus"],
                    "seite": r.get("seite", ""),
                    "einsatz": einsatz, "erloes": betrag,
                    "funding": fd,
                    "gv": betrag - einsatz - fd,
                    "grund": r.get("grund", ""),
                })
    return runden


# --- Grenzen dieser Spur ---------------------------------------------------

def groessenfaktor(ruecklauf_usd, w):
    """Bedingung 2, erste Stufe: ab drawdown_halbierung_prozent des Rahmens
    unter dem Hoechststand wird jede neue Position halbiert.

    Bezug ist max_margin_gesamt_usd - der Einschuss, nicht der Positionswert.
    """
    grenze = (w.get("drawdown_halbierung_prozent", 15.0) / 100.0
              * w["max_margin_gesamt_usd"])
    return 0.5 if ruecklauf_usd >= grenze > 0 else 1.0


def kill_ausgeloest(ruecklauf_usd, w):
    """Bedingung 2, zweite Stufe: bei kill_switch_gesamt_usd Gesamtverlust
    wird flach gestellt und die Sperre geschlossen."""
    ks = w.get("kill_switch_gesamt_usd")
    return ks is not None and ruecklauf_usd >= ks


def familien_belegung(positionen, w):
    """Wieviel Margin je Familie steht - gegen max_anteil_gesamt.

    Die Grenze ist neu am 03.09.2026 und betrifft nur Aktien und Rohstoffe:
    hoechstens die Haelfte des Rahmens in einer Familie, deren Basiswert
    nachts und am Wochenende nicht handelt. Der Grund steht in
    Wissen/XPERP-Handel.md - der Kontrakt driftet dann kaum, der Basiswert
    oeffnet Montag trotzdem woanders.
    """
    rahmen = w["max_margin_gesamt_usd"]
    je = {}
    for p in positionen:
        je[p.get("familie", "krypto")] = (je.get(p.get("familie", "krypto"), 0.0)
                                          + float(p.get("margin", 0)))
    aus = {}
    for name, f in (w.get("familien") or {}).items():
        anteil = f.get("max_anteil_gesamt", 1.0)
        aus[name] = {
            "margin": je.get(name, 0.0),
            "grenze": anteil * rahmen,
            "voll": je.get(name, 0.0) >= anteil * rahmen,
        }
    return aus


def wochenende_sperrt(w, jetzt=None):
    """Ab freitag_stopp_utc keine neuen Aktien- und Rohstoff-Anlaeufe.

    Kein Filter loest das Gap zum Wochenstart - nur Zurueckhaltung. Gilt von
    Freitag ab der genannten Stunde bis Montag 00:00 UTC.
    """
    jetzt = jetzt or datetime.now(timezone.utc)
    stopp = w.get("freitag_stopp_utc")
    if not stopp:
        return False
    try:
        std, minute = (int(x) for x in stopp.split(":"))
    except (ValueError, AttributeError):
        return False
    wt = jetzt.weekday()                       # Mo=0 .. So=6
    if wt == 4:                                # Freitag
        return (jetzt.hour, jetzt.minute) >= (std, minute)
    return wt in (5, 6)                        # Samstag, Sonntag


# --- Sperre schliessen (einziger Schreibzugriff auf wachen.json) ----------

def sperre_zu(grund):
    """handel_erlaubt von true auf false. Nur diese Richtung. Vermerkt Grund
    und Zeit. Gibt True zurueck, wenn tatsaechlich umgelegt wurde."""
    w = json.loads(WACHEN.read_text("utf-8"))
    if not w.get("handel_erlaubt"):
        return False
    w["handel_erlaubt"] = False
    w["_sperre_zu_ausgeloest"] = {
        "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "grund": grund,
    }
    WACHEN.write_text(json.dumps(w, ensure_ascii=False, indent=2), "utf-8")
    return True


# --- Gesamtbild ------------------------------------------------------------

def lage(w, journal_pfad, zustand):
    """Alle fuenf Bedingungen als ein Dict - fuer handeln.py --wachen und den
    Wochenlauf."""
    runden = runden_aus_journal(journal_pfad)
    papier = [r for r in runden if r["modus"] == "papier"]
    hoch, rueck = drawdown(runden)
    frisch, alter = herzschlag_frisch(
        zustand, w.get("herzschlag_max_minuten", 30))
    ev = rollierender_ev(runden)
    erste = runden[0]["zeit"][:10] if runden else None
    pos = (zustand or {}).get("positionen", [])
    return {
        "freigabe_erfuellt": freigabe_erfuellt(w),
        "runden_gesamt": len(runden),
        "runden_papier": len(papier),
        "erste_runde": erste,
        "hoechststand_usd": hoch,
        "ruecklauf_usd": rueck,
        "groessenfaktor": groessenfaktor(rueck, w),
        "kill": kill_ausgeloest(rueck, w),
        "herzschlag_frisch": frisch,
        "herzschlag_alter_min": alter,
        "rollierender_ev": ev,
        "ev_negativ": ev is not None and ev < 0,
        "funding_gesamt": sum(r["funding"] for r in runden),
        "familien": familien_belegung(pos, w),
        "wochenende": wochenende_sperrt(w),
    }
