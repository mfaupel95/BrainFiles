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
vermerke_spiegelung = basis.vermerke_spiegelung
freigabe_erfuellt = basis.freigabe_erfuellt
teile_runden = basis.teile_runden


# --- Runden aus dem Journal ------------------------------------------------

HAND = "handgriff"
STRATEGIE = "strategie"


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
    herkunft = {}
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
                # Herkunft steht in der Eroeffnungszeile: eine von Hand an der
                # Boerse eroeffnete und ins Buch uebernommene Position
                # (`fremdposition_uebernommen`) ist keine Entscheidung der
                # Strategie. Kein neues Journalfeld noetig - der Kopf einer
                # bestehenden Datei bestimmt, welche Spalten geschrieben werden.
                herkunft.setdefault(inst, []).append(
                    HAND if str(r.get("grund") or "").startswith("fremdposition")
                    else STRATEGIE)
            elif aktion == "funding" and funding.get(inst):
                # Auf die aelteste offene Position dieses Kontrakts. Positiv
                # = gezahlt, negativ = bekommen.
                funding[inst][0] += betrag
            elif aktion == "schliessen" and offen.get(inst):
                einsatz = offen[inst].pop(0)
                fd = funding[inst].pop(0) if funding.get(inst) else 0.0
                her = herkunft[inst].pop(0) if herkunft.get(inst) else STRATEGIE
                runden.append({
                    "zeit": r["zeit"], "inst": inst, "modus": r["modus"],
                    "seite": r.get("seite", ""), "herkunft": her,
                    "einsatz": einsatz, "erloes": betrag,
                    "funding": fd,
                    "gv": betrag - einsatz - fd,
                    "grund": r.get("grund", ""),
                })
    return runden


# --- Grenzen dieser Spur ---------------------------------------------------

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


def groessenfaktor(ruecklauf_usd, w):
    """Bedingung 2, erste Stufe: ab der Halbierungsschwelle unter dem
    Hoechststand wird jede neue Position halbiert.

    Die Schwelle kommt aus ratschen.py - EINE Umsetzung fuer alle Spuren. Sie
    ist ein absoluter Betrag (drawdown_halbierung_usd), hergeleitet als 1.0 x
    Buchrisiko = risiko_je_anlauf_usd x max_offene_anlaeufe = 30.0 USD.

    Vorher stand hier drawdown_halbierung_prozent x max_margin_gesamt_usd. Das
    war derselbe Fehler wie beim scanner: eine Quote von einer fremden Groesse
    verschiebt eine Schutzschwelle lautlos, sobald jemand den Einschuss aendert.
    Hier ergab sie zufaellig denselben Betrag - das macht sie nicht richtig.
    """
    return RATSCHEN.groessenfaktor(ruecklauf_usd, w)


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


# --- Hebel und Stopweite je Familie (Auftrag Max 08.10.2026) ---------------

def hebel_grenze(w, kategorie):
    """Hebel-Obergrenze einer Familie; ohne eigenen Wert gilt max_hebel.

    Auftrag Max 08.10.2026: Rohstoffe (XAU, XAG, CL, BZ) mit 10x. Der Wert
    steht in familien.<name>.max_hebel der wachen.json, nicht im Code. Seit
    10.10.2026 ("darf auch weniger, aber so hoch wie moeglich") ist er eine
    OBERGRENZE: der Hebel ist min(Grenze, Volatilitaets-Deckel) in
    bot.groesse(); zugelassen wird ab hebel_mindest(). Vorher musste der
    Deckel die 10 erreichen - in 60 Tagen Ruecktest schaffte das kein
    Rohstoff, die Familie handelte praktisch nicht mehr.
    """
    fam = (w.get("familien") or {}).get(kategorie) or {}
    return float(fam.get("max_hebel", w["max_hebel"]))


def hebel_mindest(w, kategorie):
    """Kleinster Volatilitaets-Deckel, mit dem ein Wert noch Kandidat wird.

    Das globale max_hebel (5) fuer alle Familien - fuer Krypto/Aktie
    unveraendert, fuer Rohstoffe der Stand vor dem 10x-Auftrag. Ein Wert,
    dessen 7-Tage-Ruecklauf nicht einmal den traegt, faellt aus der Rangliste.
    """
    return float(w["max_hebel"])


def stop_max_pct(w, kategorie):
    """Hoechste Stopweite einer Familie in % des Kurses, oder None (keine Grenze).

    Beim 10x-Hebel liegt die Liquidation grob bei 9-9,5 % gegen die Position
    (isoliert, Wartungsmarge 0,5 %). Ein Stop weiter als diese Grenze liegt
    zu nah an der Liquidation, um noch zu schuetzen - der Anlauf entfaellt.
    """
    fam = (w.get("familien") or {}).get(kategorie) or {}
    v = fam.get("stop_max_pct")
    return None if v is None else float(v)


def fuer_familie(w, kategorie):
    """Kopie der Wachen mit der Hebel-Grenze der Familie als max_hebel.

    Fuer bot.groesse() und bot.pruefpflicht(), die max_hebel aus den Wachen
    lesen. Die Originaldatei wird nie veraendert.
    """
    return dict(w, max_hebel=hebel_grenze(w, kategorie))


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
    echt, stoer = teile_runden(runden)
    # STRATEGIE-KAPITALKURVE (Auftrag Max 14.10.2026, Variante C): Ergebnisse
    # von Positionen, die von Hand eroeffnet und ins Buch uebernommen wurden,
    # steuern Halbierung und Kill der Strategie NICHT mit
    # (`handergebnis_in_kapitalkurve: false`). Anlass: Der Kill vom 06.10.2026
    # (Ruecklauf 835 USD) kam von einer uebernommenen Handposition (STRK), und
    # die Halbierung (30 USD) lag mit rund -400 USD Handergebnis dauerhaft
    # darunter. Ohne das Feld (Standard true) bleibt alles wie bisher: die
    # Kurve zaehlt alle gebuchten Runden.
    if w.get("handergebnis_in_kapitalkurve", True):
        kurve = runden
    else:
        kurve = [r for r in runden if r.get("herkunft") != HAND]
    hoch, rueck = drawdown(kurve)
    # KONTO-RUECKLAUF: dieselbe Rechnung auf ALLEN Runden. Nur zum Melden, nie
    # zum Handeln - er schliesst nichts und sperrt nichts.
    konto_hoch, konto_rueck = drawdown(runden)
    schwelle = w.get("konto_warnschwelle_usd")
    konto_warnung = bool(schwelle) and konto_rueck >= float(schwelle)
    frisch, alter = herzschlag_frisch(
        zustand, w.get("herzschlag_max_minuten", 30))
    # Bedingung 5 rechnet auf HANDELSRUNDEN: ein Herzschlag-Zwangsschluss
    # ist keine Handelsentscheidung und darf den Erwartungswert nicht ins
    # Negative ziehen (Entscheidung Max, 15.09.2026).
    ev = rollierender_ev(echt)
    erste = runden[0]["zeit"][:10] if runden else None
    pos = (zustand or {}).get("positionen", [])
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
        "runden_hand": len([r for r in runden if r.get("herkunft") == HAND]),
        "konto_hoechststand_usd": konto_hoch,
        "konto_ruecklauf_usd": konto_rueck,
        "konto_warnung": konto_warnung,
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
