"""Bedingungen 1-5 aus Wissen/Handelsregeln.md fuer die dritte Spur (Kraken).

Die waehrungsneutrale Rechnung steht nur einmal im Haus: sie kommt aus
scanner/wachen_pruefung.py und wird hier importiert, nicht abgeschrieben -
Drawdown-Kurve, Herzschlag-Alter, rollierender Erwartungswert, Spiegelung.

Eigen ist hier nur, was die Waehrung oder die Datei kennt:

  * das Journal - die Betragsspalte heisst eur, nicht usd
  * die Grenzen  - max_gesamt_eur, kill_switch_gesamt_eur
  * sperre_zu    - schreibt in kraken/wachen.json, nicht in die des Scanners

Kein Netz, kein Kraken. Alles aus handelsjournal.csv und zustand.json. Der
einzige Schreibzugriff auf wachen.json ist sperre_zu() - und nur in eine
Richtung: handel_erlaubt von true auf false. So verlangt es die Schutzregel.
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
vermerke_spiegelung = basis.vermerke_spiegelung
freigabe_erfuellt = basis.freigabe_erfuellt


# --- Runden aus dem Journal ------------------------------------------------

def runden_aus_journal(journal_pfad):
    """Jede abgeschlossene Runde (Kauf gefolgt von Verkauf desselben Paares)
    mit ihrem Gewinn/Verlust in EUR. FIFO je Paar.

    handelsjournal.csv: Kauf-Zeile eur = Einsatz inklusive Gebuehr,
    Verkauf-Zeile eur = Erloes nach Gebuehr. Die Gebuehr steckt also in den
    Zahlen, nicht daneben - sonst sieht der Papierlauf besser aus als die
    Wirklichkeit, und genau daran ist in Wissen/Handelsbots.md schon einmal
    eine Rueckrechnung gescheitert."""
    p = Path(journal_pfad)
    if not p.exists():
        return []
    offen = {}
    runden = []
    with p.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            paar = r["paar"]
            try:
                eur = float(r["eur"])
            except (TypeError, ValueError):
                continue
            if r["aktion"] == "kauf":
                offen.setdefault(paar, []).append(eur)
            elif r["aktion"] == "verkauf" and offen.get(paar):
                einsatz = offen[paar].pop(0)
                runden.append({
                    "zeit": r["zeit"], "inst": paar, "modus": r["modus"],
                    "einsatz": einsatz, "erloes": eur, "gv": eur - einsatz,
                    "grund": r.get("grund", ""),
                })
    return runden


# --- Grenzen dieser Spur ---------------------------------------------------

def groessenfaktor(ruecklauf_eur, w):
    """Bedingung 2, erste Stufe: ab drawdown_halbierung_prozent des Rahmens
    unter dem Hoechststand wird jede neue Position halbiert."""
    grenze = w.get("drawdown_halbierung_prozent", 15.0) / 100.0 * w["max_gesamt_eur"]
    return 0.5 if ruecklauf_eur >= grenze > 0 else 1.0


def kill_ausgeloest(ruecklauf_eur, w):
    """Bedingung 2, zweite Stufe: bei kill_switch_gesamt_eur Gesamtverlust
    wird flach gestellt und die Sperre geschlossen."""
    ks = w.get("kill_switch_gesamt_eur")
    return ks is not None and ruecklauf_eur >= ks


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


# --- Gesamtbild fuer die Ausgabe ----------------------------------------

def lage(w, journal_pfad, zustand):
    """Alle fuenf Bedingungen als ein Dict - fuer handeln.py --wachen und den
    Wochenlauf."""
    runden = runden_aus_journal(journal_pfad)
    papier = [r for r in runden if r["modus"] == "papier"]
    hoch, rueck = drawdown(runden)
    frisch, alter = herzschlag_frisch(zustand, w.get("herzschlag_max_minuten", 2880))
    ev = rollierender_ev(runden)
    erste = runden[0]["zeit"][:10] if runden else None
    return {
        "freigabe_erfuellt": freigabe_erfuellt(w),
        "runden_gesamt": len(runden),
        "runden_papier": len(papier),
        "erste_runde": erste,
        "hoechststand_eur": hoch,
        "ruecklauf_eur": rueck,
        "groessenfaktor": groessenfaktor(rueck, w),
        "kill": kill_ausgeloest(rueck, w),
        "herzschlag_frisch": frisch,
        "herzschlag_alter_min": alter,
        "rollierender_ev": ev,
        "ev_negativ": ev is not None and ev < 0,
    }
