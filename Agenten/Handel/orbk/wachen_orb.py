"""Bedingungen der vierten Spur (ORB auf OKX-Perpetuals, USDT).

Die waehrungsneutrale Rechnung steht nur einmal im Haus: sie kommt aus
scanner/wachen_pruefung.py und wird hier importiert, nicht abgeschrieben.
Eigen ist hier nur, was Waehrung, Datei oder Strategie kennt: die eur-Spalte
im Journal, die Range-Filter, sperre_zu auf orb/wachen.json.

Kein Netz. Alles aus handelsjournal.csv und zustand.json. Einziger
Schreibzugriff auf wachen.json: sperre_zu, nur true -> false.
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHEN = HIER / "wachen.json"

sys.path.insert(0, str(HIER.parent / "scanner"))
import wachen_pruefung as basis  # noqa: E402

drawdown = basis.drawdown
herzschlag_frisch = basis.herzschlag_frisch
rollierender_ev = basis.rollierender_ev
spiegele_journal = basis.spiegele_journal
vermerke_spiegelung = basis.vermerke_spiegelung
freigabe_erfuellt = basis.freigabe_erfuellt


def runden_aus_journal(journal_pfad):
    """Jede abgeschlossene Runde aus dem orbk-Journal.

    orbk/handeln.py schreibt je abgeschlossener Runde EINE Zeile im Schema
    zeit,inst,richtung,einstieg,stop,ziel,ausgang,ausstieg,gv_punkte,gv_usd
    - anders als das alte orb-Journal (aktion einstieg/ausstieg, Spalte
    eur), fuer das dieser Leser urspruenglich gebaut war. Der Mis-Match
    schlug als KeyError: 'eur' im Bericht auf (Befund 14.09.2026).

    Die Spur ist papierfest: jede Zeile ist eine Papierrunde. gv_usd ist
    das Ergebnis der Runde (punkt_wert_usd=1.0, USD). Die
    ausgange sind ziel/stop/zwangsschluss.
    """
    p = Path(journal_pfad)
    if not p.exists():
        return []
    runden = []
    with p.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if not r.get("ausgang"):
                continue                        # keine abgeschlossene Runde
            try:
                gv_usd = float(r["gv_usd"])
            except (TypeError, ValueError, KeyError):
                continue
            runden.append({
                "zeit": r.get("zeit", ""), "inst": r.get("inst", ""),
                "modus": "papier",              # papierfest, keine modus-Spalte
                "einsatz": 0.0, "erloes": gv_usd, "gv": gv_usd,
                "grund": r.get("ausgang", ""),
            })
    return runden


def groessenfaktor(ruecklauf_usd, w):
    grenze = w.get("drawdown_halbierung_prozent", 15.0) / 100.0 * w["kill_switch_gesamt_usd"]
    return 0.5 if ruecklauf_usd >= grenze > 0 else 1.0


def kill_ausgeloest(ruecklauf_usd, w):
    ks = w.get("kill_switch_gesamt_usd")
    return ks is not None and ruecklauf_usd >= ks


def range_ok(range_punkte, inst_key, w):
    return (w["mindest_range_punkte"][inst_key] <= range_punkte
            <= w["max_range_punkte"][inst_key])


def freigabe_voll_erfuellt(w, gehandelte_wochen, gehandelte_sessions):
    f = w.get("freigabe") or {}
    return bool(f.get("backtest_bestanden") and f.get("netto_positiv")
                and gehandelte_wochen >= f.get("papierlauf_min_wochen", 6)
                and gehandelte_sessions >= f.get("papierlauf_min_sessions", 50))


def sperre_zu(grund):
    w = json.loads(WACHEN.read_text("utf-8"))
    if not w.get("handel_erlaubt"):
        return False
    w["handel_erlaubt"] = False
    w["_sperre_zu_ausgeloest"] = {
        "zeit": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "grund": grund}
    WACHEN.write_text(json.dumps(w, ensure_ascii=False, indent=2), "utf-8")
    return True


def _wochen_und_sessions(runden):
    papier = [r for r in runden if r["modus"] == "papier"]
    if not papier:
        return 0.0, 0
    from datetime import date
    tage = [date.fromisoformat(r["zeit"][:10]) for r in papier]
    return (max(tage) - min(tage)).days / 7.0, len(papier)


def lage(w, journal_pfad, zustand):
    runden = runden_aus_journal(journal_pfad)
    papier = [r for r in runden if r["modus"] == "papier"]
    hoch, rueck = drawdown(runden)
    frisch, alter = herzschlag_frisch(zustand, w.get("herzschlag_max_minuten", 45))
    ev = rollierender_ev(runden)
    wochen, sessions = _wochen_und_sessions(runden)
    return {
        "freigabe_erfuellt": freigabe_erfuellt(w),   # Bed. 1 - Haken aus wachen.json
        "runden_gesamt": len(runden), "runden_papier": len(papier),
        "hoechststand_usd": hoch, "ruecklauf_usd": rueck,
        "groessenfaktor": groessenfaktor(rueck, w), "kill": kill_ausgeloest(rueck, w),
        "herzschlag_frisch": frisch, "herzschlag_alter_min": alter,
        "rollierender_ev": ev, "ev_negativ": ev is not None and ev < 0,
        "papier_wochen": wochen, "papier_sessions": sessions,
        "freigabe_voll": freigabe_voll_erfuellt(w, wochen, sessions),
    }
