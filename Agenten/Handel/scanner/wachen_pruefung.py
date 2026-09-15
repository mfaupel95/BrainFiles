"""Bedingungen 2-5 aus Wissen/Handelsregeln.md, Abschnitt "Damit der Automat
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


def halbierungsschwelle(w):
    """Absoluter Ruecklauf in USD, ab dem neue Positionen halbiert werden.

    Vorrang hat der absolute Wert drawdown_halbierung_usd. Die Ratsche misst den
    Ruecklauf der realisierten GEWINNKURVE (siehe drawdown()), der Kapitaldeckel
    ist eine davon unabhaengige Groesse. Ein Prozentsatz davon koppelt beide und
    verschiebt den Ausloeser lautlos, sobald jemand max_gesamt_usd aendert: am
    15.09.2026 hob die Erhoehung von 400 auf 1000 die Schwelle von 60 auf 150
    USD. Das war NICHT unerreichbar - drawdown() rechnet hoch minus kum, und die
    kumulierte Kurve darf ins Minus laufen, also waechst der Ruecklauf ueber den
    Hoechststand hinaus. Die 150 haetten aber erst gegriffen, wenn die Spur bei
    -9.76 USD gestanden haette, also nach mehr Verlust als ihr gesamter
    Hoechstgewinn von 140.24 USD: die Sicherung haette keinen GEWINN mehr
    geschuetzt, sondern nur noch einen Nettoverlust gefangen. Genau dafuer ist
    der Kill-Switch da. Deshalb ist der Ausloeser jetzt ein Betrag und keine
    Quote, und lage() meldet mit halbierung_im_gewinn, ob die Halbierung
    ueberhaupt noch innerhalb des Gewinns greifen kann.

    Ohne absoluten Wert gilt weiter der Prozentsatz - rueckwaertsvertraeglich
    fuer Spuren, die den neuen Schluessel nicht kennen.
    """
    usd = w.get("drawdown_halbierung_usd")
    if usd is not None:
        return float(usd)
    rahmen = w.get("max_gesamt_usd", w.get("max_gesamt_eur", 0.0))
    return w.get("drawdown_halbierung_prozent", 15.0) / 100.0 * rahmen


def groessenfaktor(ruecklauf_usd, w):
    """Bedingung 2, erste Stufe: ab der Halbierungsschwelle unter dem
    Hoechststand wird jede neue Position halbiert."""
    grenze = halbierungsschwelle(w)
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


def vermerke_spiegelung(z, ziel, ok, info, schreiben):
    """Ergebnis der Spiegelung in den Zustand schreiben - nur bei Aenderung.

    `schreiben(z)` ist die Schreibfunktion der jeweiligen Spur; jede Spur
    schreibt ihren eigenen Zustand. Rueckgabe: True, wenn geschrieben wurde.

    Warum ueberhaupt: der Dauerlauf protokolliert bei Rueckgabe 0 nur "ok"
    und zeigt die Spurausgabe nicht. Eine ausgefallene Kopie nach Q: waere
    damit unsichtbar - sichtbar ist sie nur, wenn sie im Zustand steht
    (`journal_zweitziel_ok`, `journal_zweitziel_info`). Geschrieben wird nur
    beim Wechsel, sonst waere jeder Zyklus ein zweiter Schreibvorgang ohne
    neue Aussage.
    """
    felder = {"journal_zweitziel": ziel, "journal_zweitziel_ok": ok,
              "journal_zweitziel_info": info}
    if all(z.get(k) == v for k, v in felder.items()):
        return False
    z.update(felder)
    schreiben(z)
    return True


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
        "halbierungsschwelle_usd": halbierungsschwelle(w),
        "halbierung_im_gewinn": hoch == 0 or halbierungsschwelle(w) <= hoch,
        "groessenfaktor": groessenfaktor(rueck, w),
        "kill": kill_ausgeloest(rueck, w),
        "herzschlag_frisch": frisch,
        "herzschlag_alter_min": alter,
        "rollierender_ev": ev,
        "ev_negativ": ev is not None and ev < 0,
    }
