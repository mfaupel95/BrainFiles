"""Bedingungen 2-5 aus Wissen/Schutzregeln.md, Abschnitt "Damit der Automat
unbeaufsichtigt laufen darf: fuenf messbare Bedingungen" (angeordnet
01.09.2026). Reine Funktionen, aufgerufen von handeln.py.

  1  Freigabe Papier -> Live : wachen.json  freigabe.erfuellt   (nur gelesen)
  2  Drawdown-Ratsche        : realisierte Kurve aus dem Journal -> Faktor 0.5,
                               und ab kill_switch_gesamt_usd flach + Sperre zu
  3  Herzschlag              : Alter von zustand.json  letzter_lauf
  4  Journal ausser Haus     : Kopie von Journal + Zustand nach journal_zweitziel
  5  Soll-Ist-Abgleich       : rollierender Erwartungswert der letzten N Runden;
                               < 0 -> Sperre zu (im Wochenlauf handeln.py --wachen)

Kein Netz, kein OKX. Alles aus handelsjournal.csv und zustand.json. Der
einzige Schreibzugriff auf wachen.json ist sperre_zu() - und nur in eine
Richtung: handel_erlaubt von true auf false. So verlangt es die Schutzregel.
"""

import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"


# --- Runden aus dem Journal ------------------------------------------------

def runden_aus_journal(journal_pfad):
    """Jede abgeschlossene Runde (Kauf gefolgt von Verkauf desselben Werts) mit
    ihrem Gewinn/Verlust in USD. FIFO je Instrument.

    handelsjournal.csv: Kauf-Zeile usd = Einsatz, Verkauf-Zeile usd = Erloes.
    """
    p = Path(journal_pfad)
    if not p.exists():
        return []
    offen = {}          # inst -> Liste offener Einsaetze (FIFO)
    runden = []
    with p.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            inst = r["inst"]
            try:
                usd = float(r["usd"])
            except (TypeError, ValueError):
                continue
            if r["aktion"] == "kauf":
                offen.setdefault(inst, []).append(usd)
            elif r["aktion"] == "verkauf" and offen.get(inst):
                einsatz = offen[inst].pop(0)
                runden.append({
                    "zeit": r["zeit"], "inst": inst, "modus": r["modus"],
                    "einsatz": einsatz, "erloes": usd, "gv": usd - einsatz,
                    "grund": r.get("grund", ""),
                })
    return runden


def drawdown(runden):
    """(hoechststand_usd, aktueller_ruecklauf_usd) auf der realisierten Kurve.

    Ruecklauf = Hoechststand der kumulierten Kurve minus aktueller Stand.
    Nur realisierte Runden - offene Buchverluste zaehlen hier nicht.
    """
    kum = hoch = 0.0
    for r in runden:
        kum += r["gv"]
        hoch = max(hoch, kum)
    return hoch, max(0.0, hoch - kum)


def groessenfaktor(ruecklauf_usd, w):
    """Bedingung 2, erste Stufe: ab drawdown_halbierung_prozent des Rahmens
    unter dem Hoechststand wird jede neue Position halbiert."""
    grenze = w.get("drawdown_halbierung_prozent", 15.0) / 100.0 * w["max_gesamt_usd"]
    return 0.5 if ruecklauf_usd >= grenze > 0 else 1.0


def kill_ausgeloest(ruecklauf_usd, w):
    """Bedingung 2, zweite Stufe: bei kill_switch_gesamt_usd Gesamtverlust
    wird flach gestellt und die Sperre geschlossen."""
    ks = w.get("kill_switch_gesamt_usd")
    return ks is not None and ruecklauf_usd >= ks


# --- Herzschlag ----------------------------------------------------------

def herzschlag_frisch(zustand, max_minuten):
    """Bedingung 3: liegt der letzte gesunde Lauf laenger als max_minuten
    zurueck, ist der Herzschlag alt. Ohne letzten Lauf (erster Start) gilt er
    als frisch."""
    ll = (zustand or {}).get("letzter_lauf")
    if not ll:
        return True, None
    try:
        t = datetime.fromisoformat(ll)
    except ValueError:
        return True, None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    alter_min = (datetime.now(timezone.utc) - t).total_seconds() / 60.0
    return alter_min <= max_minuten, alter_min


# --- Soll-Ist ----------------------------------------------------------

def rollierender_ev(runden, n=30, mindest=5):
    """Bedingung 5: mittlerer Gewinn/Verlust je Runde ueber die letzten n.
    None, solange weniger als `mindest` Runden vorliegen - dann ist nichts
    gemessen und nichts wird gesperrt."""
    if len(runden) < mindest:
        return None
    letzte = runden[-n:]
    return sum(r["gv"] for r in letzte) / len(letzte)


# --- Freigabe ----------------------------------------------------------

def freigabe_erfuellt(w):
    """Bedingung 1: der von Hand gesetzte Haken aus dem Papierlauf."""
    return (w.get("freigabe") or {}).get("erfuellt") is True


# --- Journal ausser Haus ------------------------------------------------

def spiegele_journal(dateien, ziel):
    """Bedingung 4: Journal und Zustand nach jedem Zyklus auf ein zweites
    Ziel kopieren. ziel None oder nicht erreichbar -> (False, Grund)."""
    if not ziel:
        return False, "journal_zweitziel nicht gesetzt"
    zpfad = Path(ziel)
    try:
        zpfad.mkdir(parents=True, exist_ok=True)
        for d in dateien:
            d = Path(d)
            if d.exists():
                shutil.copy2(d, zpfad / d.name)
    except OSError as e:
        return False, str(e)
    return True, str(zpfad)


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
    frisch, alter = herzschlag_frisch(zustand, w.get("herzschlag_max_minuten", 30))
    ev = rollierender_ev(runden)
    erste = runden[0]["zeit"][:10] if runden else None
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
    }
