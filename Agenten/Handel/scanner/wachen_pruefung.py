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


# --- Betriebsstoerung oder Handelsrunde ------------------------------------
#
# Die eine Definition steht in Handel/stoerungen.py und wird ueber den PFAD
# geladen, nicht ueber sys.path: eine Spur startet mit ihrem eigenen Ordner als
# sys.path[0], und Handel/ waere nur ueber einen Eintrag erreichbar, der
# gleichnamige Spurenmodule verdecken koennte - derselbe Grund wie bei
# Handel/ratschen.py.
_STOERUNGEN = None


def stoerungen_modul():
    """Handel/stoerungen.py - einmal geladen, dann gemerkt."""
    global _STOERUNGEN
    if _STOERUNGEN is None:
        import importlib.util
        p = HIER.parent / "stoerungen.py"
        spec = importlib.util.spec_from_file_location("handel_stoerungen", p)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        _STOERUNGEN = modul
    return _STOERUNGEN


def teile_runden(runden):
    """(echt, stoerungen) - siehe stoerungen.teile_runden (gleiche Fassung)."""
    return stoerungen_modul().teile_runden(runden)


# --- Runden aus dem Journal ------------------------------------------------

def runden_aus_journal(journal_pfad):
    """Jede abgeschlossene Runde (Kauf gefolgt von Verkauf desselben Werts) mit
    ihrem Gewinn/Verlust in USD. FIFO je Instrument.

    handelsjournal.csv: Kauf-Zeile = Einsatz, Verkauf-Zeile = Erloes. Die
    Spalte heisst je Spur anders: `usd` (scanner, xperp, swap, kraken) oder
    `einsatz_usd` (die Indikator-Spuren, spiegel, omniquant). Beide lesen -
    eine zweite Fassung dieser Rechnung waere eine zweite Wahrheit.
    """
    p = Path(journal_pfad)
    if not p.exists():
        return []
    offen = {}          # inst -> Liste offener Einsaetze (FIFO)
    runden = []
    with p.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            inst = r.get("inst") or r.get("paar") or ""
            if not inst:
                continue
            roh = r.get("usd")
            if roh in (None, ""):
                roh = r.get("einsatz_usd")
            try:
                usd = float(roh)
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


def _ratschen():
    """Laedt Handel/ratschen.py ueber den PFAD statt ueber sys.path.

    Die Spur wird mit ihrem eigenen Ordner als sys.path[0] gestartet. Handel/
    waere nur ueber einen sys.path-Eintrag erreichbar, und der koennte
    gleichnamige Spurenmodule verdecken (gitter/ importiert ein eigenes grid.py,
    daneben liegt Handel/grid.py).
    """
    import os
    from importlib.util import spec_from_file_location, module_from_spec
    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "ratschen.py")
    _s = spec_from_file_location("ratschen", _p)
    _m = module_from_spec(_s)
    _s.loader.exec_module(_m)
    return _m


RATSCHEN = _ratschen()


def halbierungsschwelle(w):
    """Absoluter Ruecklauf, ab dem neue Positionen halbiert werden.

    Delegiert an ratschen.py - EINE Umsetzung fuer alle Spuren. Der Wert ist
    ein Betrag (drawdown_halbierung_usd), hergeleitet als 1.0 x Buchrisiko =
    risiko_je_position_usd 6.0 x max_offene_positionen 6 = 36.00 USD.

    Warum das vorher falsch war: hier stand drawdown_halbierung_prozent/100 *
    max_gesamt_usd. Die Ratsche misst den Ruecklauf der realisierten
    GEWINNKURVE (siehe drawdown()), der Kapitaldeckel ist davon unabhaengig -
    ein Prozentsatz davon koppelt beide und verschiebt den Ausloeser lautlos,
    sobald jemand max_gesamt_usd aendert. Am 15.09.2026 hob die Erhoehung von
    400 auf 1000 die Schwelle von 60 auf 150 USD. Die 150 waren NICHT
    unerreichbar - drawdown() rechnet hoch minus kum, die kumulierte Kurve darf
    ins Minus laufen, der Ruecklauf waechst also ueber den Hoechststand hinaus -
    aber sie haetten erst bei einem Stand von -9.76 USD gegriffen, also nach
    mehr Verlust als dem gesamten Gewinnhoechststand von 140.24 USD: kein
    Gewinnschutz mehr, sondern ein zweiter Kill-Switch.

    Kann None sein, wenn eine Spur weder den Betrag noch ein herleitbares
    Buchrisiko nennt - dann gibt es KEINE Ratsche, und lage() meldet das
    sichtbar (halbierung_im_gewinn bleibt True, groessenfaktor 1.0). Eine
    stillschweigende Ersatzschwelle waere schlimmer als keine: sie saehe aus
    wie Schutz.
    """
    return RATSCHEN.halbierungsschwelle(w)


def groessenfaktor(ruecklauf_usd, w):
    """Bedingung 2, erste Stufe: ab der Halbierungsschwelle unter dem
    Hoechststand wird jede neue Position halbiert. Ohne Schwelle 1.0."""
    return RATSCHEN.groessenfaktor(ruecklauf_usd, w, halbierungsschwelle(w))


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
    echt, stoer = teile_runden(runden)
    # Kill-Reset (09.10.2026): nach Ablauf der Kill-Frist setzt spur_buch
    # `kill_ab_runde` auf die Zahl der bis dahin gebuchten Runden. Der Ruecklauf
    # (und damit Halbierung und Kill) beginnt dann bei 0, statt fuer immer an dem
    # Verlust zu haengen, der den Kill ausgeloest hat. Ohne das Feld: unveraendert.
    try:
        ab = max(0, int((zustand or {}).get("kill_ab_runde") or 0))
    except (TypeError, ValueError):
        ab = 0
    hoch, rueck = drawdown(runden[ab:])
    frisch, alter = herzschlag_frisch(zustand, w.get("herzschlag_max_minuten", 30))
    # Bedingung 5 rechnet auf HANDELSRUNDEN: ein Herzschlag-Zwangsschluss
    # ist keine Handelsentscheidung und darf den Erwartungswert nicht ins
    # Negative ziehen (Entscheidung Max, 15.09.2026).
    ev = rollierender_ev(echt)
    erste = runden[0]["zeit"][:10] if runden else None
    return {
        "freigabe_erfuellt": freigabe_erfuellt(w),
        "runden_gesamt": len(runden),
        "runden_papier": len(papier),
        # Kennzahl auf den Handelsrunden, Kapitalkurve auf allen Buchungen:
        # drawdown(runden) oben bleibt absichtlich ungefiltert.
        "runden_echt": len(echt),
        "runden_stoerung": len(stoer),
        "runden_papier_echt": len([r for r in echt if r["modus"] == "papier"]),
        "rollierender_ev_alle": rollierender_ev(runden),
        "erste_runde": erste,
        "hoechststand_usd": hoch,
        "ruecklauf_usd": rueck,
        "kill_ab_runde": ab,
        "halbierungsschwelle_usd": halbierungsschwelle(w),
        "halbierung_im_gewinn": hoch == 0 or halbierungsschwelle(w) <= hoch,
        "groessenfaktor": groessenfaktor(rueck, w),
        "kill": kill_ausgeloest(rueck, w),
        "herzschlag_frisch": frisch,
        "herzschlag_alter_min": alter,
        "rollierender_ev": ev,
        "ev_negativ": ev is not None and ev < 0,
    }


# --- Instrumente eines Zyklus ----------------------------------------------
#
# EINE Stelle fuer die Frage "wer wird geprueft, wer darf neu einsteigen".
# Befund 28.09.2026: macd_mtf, squeeze und wavetrend prueften ihre Ausstiege
# nur ueber w["instrumente"]. Als die Liste von USDT- auf USDC-Paare umgestellt
# wurde, blieben je Spur vier Positionen auf ETH-USDT/SOL-USDT/BTC-USDT im Buch:
# sie wurden nie wieder geprueft, nie geschlossen und belegten alle vier
# Plaetze. Folge: das Journal fror ein (letzte Zeile 20./21.09.), die Spur
# konnte nicht mehr einsteigen und stand in der Auswertung mit "keine
# geschlossene Runde" - nicht weil die Strategie versagt, sondern weil niemand
# mehr hinsah.

def plan_instrumente(w):
    """Die Instrumente, auf denen der Zyklus NEU einsteigen darf."""
    return [i for i in (w.get("instrumente") or []) if i]


def verwaiste_instrumente(w, z):
    """Instrumente OFFENER Positionen, die nicht mehr im Plan stehen."""
    offen = {p.get("inst") for p in (z.get("positionen") or []) if p.get("inst")}
    return sorted(offen - set(plan_instrumente(w)))


def pruef_instrumente(w, z):
    """Instrumente, die auf AUSSTIEGE geprueft werden MUESSEN.

    Das sind die Instrumente der Wachen UND die der offenen Positionen.
    Reihenfolge: Plan zuerst (in seiner Reihenfolge), danach die verwaisten
    alphabetisch - so sieht der Aufrufer sofort, wer nicht mehr im Plan steht.
    Ein Aufrufer, der nur einsteigen will, nimmt plan_instrumente();
    Ausstiege nehmen IMMER diese Liste.
    """
    return plan_instrumente(w) + verwaiste_instrumente(w, z)
