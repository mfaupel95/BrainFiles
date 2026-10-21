"""Risiko-Vorfilter - die Regeln des Moon-Dev `risk_agent`, ohne Sprachmodell.

WOHER DIE REGELN KOMMEN
-----------------------
`Werkstatt/moon-dev-ai-agents/src/agents/risk_agent.py` ueberwacht dort
jede offene Position und stoppt den Handel, wenn ueber die letzten
`MAX_LOSS_GAIN_CHECK_HOURS` (12) ein Limit gerissen wird:

    MAX_LOSS_USD   = 25     MAX_GAIN_USD   = 25
    MAX_LOSS_PCT   = 5      MAX_GAIN_PCT   = 5

Ob das Limit ueberstimmen werden darf, fragt der Bot ein Sprachmodell
(`should_override_limit`, alle 15 Minuten, Antwort OVERRIDE oder
RESPECT_LIMIT). Dieses Modul nimmt dieselben Zahlen und dieselbe Frist - aber
**ohne Sprachmodell**: das Limit gilt. Wer es nicht will, setzt in seiner
`wachen.json` einen anderen Betrag; geraten wird nichts.

WARUM ALS VORFILTER
-------------------
Die Haus-Spuren begrenzen die Buchgroesse (Risiko je Position, Plaetze,
Gesamtdeckel, Ratsche). Was ihnen fehlte, ist die ZEIT: ein Tag, an dem schon
dreimal der Stop traf, handelte munter weiter. Der Vorfilter setzt genau dort
an - **vor** dem Einstieg, nicht danach:

1. **Verlustgrenze** im Fenster erreicht -> kein neuer Einstieg.
2. **Gewinnziel** im Fenster erreicht -> kein neuer Einstieg (Gewinn sichern;
   der Bot stoppt hier ebenfalls).
3. **Buchrisiko**: offene Risiken + neues Risiko > Deckel -> kein Einstieg.

Er schliesst KEINE Position und aendert keine Wache - er verhindert nur neue.
Das ist die Grenze zwischen Vorfilter und Notaus: der Notaus (Kill-Schalter,
Ratsche) gehoert den Wachen, die Positionen schliessen.
"""

import csv
import json
import os
from datetime import datetime, timedelta, timezone
from importlib.util import module_from_spec, spec_from_file_location

_HANDEL = os.path.dirname(os.path.abspath(__file__))


def _ratschen():
    """`ratschen.py` ueber den PFAD laden - dasselbe Muster wie in spur_buch.py.

    Ueber den Pfad und nicht per `import`, weil jede Spur ihren eigenen Ordner
    als sys.path[0] hat; ein gleichnamiges Modul dort wuerde sonst gewinnen.
    """
    _s = spec_from_file_location("ratschen", os.path.join(_HANDEL, "ratschen.py"))
    _m = module_from_spec(_s)
    _s.loader.exec_module(_m)
    return _m


RATSCHEN = _ratschen()

# Felder, die eine Wache setzen kann. Ohne sie ist der Vorfilter AUS - eine
# stillschweigend drosselnde Neuerung waere schlimmer als keine.
STANDARD = {
    "risikovorfilter": False,
    "risiko_fenster_stunden": 12.0,
    "risiko_verlust_max_usd": 25.0,
    "risiko_verlust_max_pct": 5.0,
    "risiko_gewinn_ziel_usd": 25.0,
    "risiko_gewinn_ziel_pct": 5.0,
    "risiko_buchdeckel_usd": None,       # None -> max_gesamt_usd der Spur
}


def _zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None


def _zeit(wert):
    try:
        t = datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def runden(journal_pfad, fenster_stunden, jetzt=None):
    """Abgeschlossene Runden im Fenster: [(zeit, ergebnis_usd, einsatz_usd)].

    Gezaehlt werden nur VERKAEUFE (die Zeile mit dem Erloes), je Instrument
    gegen den letzten Kauf gestellt - dieselbe Paarung wie in der Auswertung.
    Eine Zeile ohne Einsatz zaehlt nicht: ohne Einsatz gibt es kein Ergebnis.
    """
    jetzt = jetzt or datetime.now(timezone.utc)
    grenze = jetzt - timedelta(hours=float(fenster_stunden))
    offen = {}
    aus = []
    try:
        with open(journal_pfad, newline="", encoding="utf-8") as f:
            for z in csv.DictReader(f):
                t = _zeit(z.get("zeit"))
                if t is None:
                    continue
                inst = z.get("inst") or z.get("paar") or ""
                art = (z.get("aktion") or z.get("ausgang") or "").lower()
                einsatz = _zahl(z.get("einsatz_usd")) or _zahl(z.get("usd")) \
                    or _zahl(z.get("eur"))
                if einsatz is None:
                    continue
                if art in ("kauf", "eroeffnen", "einstieg"):
                    offen[inst] = einsatz
                elif art in ("verkauf", "schliessen", "ausstieg", "ausgang"):
                    ein = offen.pop(inst, None)
                    if ein is None or t < grenze:
                        continue
                    aus.append((t, einsatz - ein, ein))
    except OSError:
        return []
    return aus


def fenster_pnl(journal_pfad, w, jetzt=None):
    """(Ergebnis in USD, Einsatz in USD) der Runden im Fenster."""
    runden_ = runden(journal_pfad, w.get("risiko_fenster_stunden",
                                         STANDARD["risiko_fenster_stunden"]),
                     jetzt)
    ergebnis = sum(r[1] for r in runden_)
    einsatz = sum(r[2] for r in runden_)
    return ergebnis, einsatz, len(runden_)


def grenzen(w):
    """Die wirksamen Grenzen als dict - Standard, wo die Wache nichts sagt."""
    aus = dict(STANDARD)
    for k in STANDARD:
        if w.get(k) is not None:
            aus[k] = w[k]
    return aus


def pruefe(w, journal_pfad, z, neues_risiko_usd, jetzt=None):
    """(erlaubt, grund) fuer EINEN geplanten Einstieg.

    `neues_risiko_usd` ist der Betrag, der bei einem Stop verloren ginge
    (Risiko, nicht Nominal).
    """
    g = grenzen(w)
    if not w.get("risikovorfilter"):
        return True, "Vorfilter aus (risikovorfilter nicht gesetzt)"

    ergebnis, einsatz, n = fenster_pnl(journal_pfad, w, jetzt)
    verlust_max = _zahl(g["risiko_verlust_max_usd"])
    gewinn_ziel = _zahl(g["risiko_gewinn_ziel_usd"])
    verlust_pct = _zahl(g["risiko_verlust_max_pct"])
    gewinn_pct = _zahl(g["risiko_gewinn_ziel_pct"])

    if verlust_max is not None and ergebnis <= -abs(verlust_max):
        return False, ("Tagesverlust %.2f USD (Grenze -%.2f) im Fenster von "
                       "%.0f h - kein neuer Einstieg"
                       % (ergebnis, abs(verlust_max), g["risiko_fenster_stunden"]))
    if gewinn_ziel is not None and ergebnis >= abs(gewinn_ziel):
        return False, ("Tagesgewinn %.2f USD (Ziel %.2f) erreicht - Gewinn "
                       "sichern, kein neuer Einstieg"
                       % (ergebnis, abs(gewinn_ziel)))
    if einsatz > 0 and verlust_pct is not None \
            and ergebnis / einsatz * 100.0 <= -abs(verlust_pct):
        return False, ("Verlust %.2f %% des Einsatzes (Grenze -%.2f %%) - kein "
                       "neuer Einstieg" % (ergebnis / einsatz * 100.0,
                                           abs(verlust_pct)))
    if einsatz > 0 and gewinn_pct is not None \
            and ergebnis / einsatz * 100.0 >= abs(gewinn_pct):
        return False, ("Gewinn %.2f %% des Einsatzes (Ziel %.2f %%) erreicht - "
                       "kein neuer Einstieg" % (ergebnis / einsatz * 100.0,
                                                abs(gewinn_pct)))

    deckel = _zahl(w.get("risiko_buchdeckel_usd")) \
        or _zahl(w.get("max_gesamt_usd"))
    offen = RATSCHEN.offenes_risiko(z)
    if deckel and offen + (neues_risiko_usd or 0.0) > deckel:
        return False, ("Buchrisiko %.2f + %.2f > Deckel %.2f - kein neuer "
                       "Einstieg" % (offen, neues_risiko_usd or 0.0, deckel))
    return True, ("Vorfilter frei (%d Runden, Ergebnis %+.2f USD im Fenster)"
                  % (n, ergebnis))


def lage(w, journal_pfad, z, jetzt=None):
    """Kurzbild fuer Doku und Berichte - rechnet, urteilt nicht."""
    g = grenzen(w)
    if not w.get("risikovorfilter"):
        return {"aktiv": False}
    ergebnis, einsatz, n = fenster_pnl(journal_pfad, w, jetzt)
    return {"aktiv": True, "runden": n, "ergebnis_usd": round(ergebnis, 2),
            "einsatz_usd": round(einsatz, 2),
            "fenster_stunden": g["risiko_fenster_stunden"],
            "verlust_max_usd": g["risiko_verlust_max_usd"],
            "gewinn_ziel_usd": g["risiko_gewinn_ziel_usd"],
            "buchdeckel_usd": g["risiko_buchdeckel_usd"],
            "offenes_risiko_usd": round(RATSCHEN.offenes_risiko(z), 2)}
