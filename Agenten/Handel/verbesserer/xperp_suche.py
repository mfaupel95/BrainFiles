"""Suchraum, Nachbarn, Sieb und Koordinatenabstieg fuer Spur 2 (XPERP).

Alles hier ist rein: keine Dateien, kein Netz. Die Grenzen je Schluessel kommen
aus der Whitelist in spuren.json (eine Wahrheit); hier stehen nur die
Schrittweiten. Die Verifikation ist bewusst von der Suche getrennt: das Sieb
und der Holdout sind eigene Stufen, die der Abstieg nie sieht (Spec,
Abschnitt 'Verifikation und Freigabe').

Nur Standardbibliothek (ausser xperp_ruecktest.bericht fuer die Kennzahlen).
"""

import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
for _p in (WURZEL, WURZEL.parent / "xperp"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import xperp_ruecktest as rt  # noqa: E402

TAG_MS = 86_400_000
MIN_ZIEL_DURCH_STOP = 1.5
RUECKLAUF_TOLERANZ = 1.10           # Regel e: hoechstens 10 % ueber der Basis

# Schrittweite je Suchschluessel. Ein Nachbar bewegt genau einen Schluessel
# um genau einen Schritt. vola_tor_pa und min_umsatz_24h_usd fehlen absichtlich:
# der Ruecktest liest sie nicht (siehe Plan, Abweichungen von der Spec).
SCHRITT = {
    "stop_atr_faktor": 0.25,
    "ziel_atr_faktor": 0.25,
    "einstieg_atr_abschlag": 0.05,
    "trailing_trigger_r": 0.25,
    "trailing_stop_prozent": 0.25,
    "trailing_abstand_floor_pct": 0.05,
    "trailing_min_hub_r": 0.05,
    "trailing_max_halten_pct": 1.0,
}


def basis_werte(wachen):
    """Die Suchschluessel aus der Wache; fehlt einer, ist das ein KeyError."""
    return {k: wachen[k] for k in SCHRITT}


def nachbarn(werte, grenzen):
    """Alle Saetze, die sich in genau einem Schluessel um genau einen Schritt
    unterscheiden, innerhalb ``grenzen[key] = [lo, hi]`` und mit
    ziel/stop >= 1.5."""
    aus = []
    for key in sorted(SCHRITT):
        lo, hi = grenzen[key]
        for vz in (-1, 1):
            neu = round(werte[key] + vz * SCHRITT[key], 4)
            if neu < lo - 1e-9 or neu > hi + 1e-9:
                continue
            kand = {**werte, key: neu}
            if (kand["ziel_atr_faktor"] / kand["stop_atr_faktor"]
                    < MIN_ZIEL_DURCH_STOP - 1e-9):
                continue
            aus.append(kand)
    return aus


def fenster_grenzen(ende_ms, konf):
    """([(von, bis), ...], (holdout_von, holdout_bis)).

    Der Holdout sind die letzten ``holdout_tage`` Tage; die Testfenster decken
    ``such_tage`` Rueckblick ab, enden vor dem Holdout und ruecken um
    ``schritt_tage`` vor. Zu wenig Rueckblick -> leere Fensterliste.

    simuliere() rechnet bis EINSCHLIESSLICH end_ms und liest dabei die 1H-
    Kerzen des letzten Schritts; ein Fenster endet deshalb einen Schritt vor
    der Grenze (halboffen). Sonst zaehlte der Grenzschritt in zwei Fenstern,
    und das letzte Fenster liesse vier Stunden Holdout-Daten in die Suche."""
    holdout_von = ende_ms - konf["holdout_tage"] * TAG_MS
    fenster = []
    von = ende_ms - konf["such_tage"] * TAG_MS
    while von + konf["test_tage"] * TAG_MS <= holdout_von:
        fenster.append((von, von + konf["test_tage"] * TAG_MS
                        - rt.SCHRITT_MS))
        von += konf["schritt_tage"] * TAG_MS
    return fenster, (holdout_von, ende_ms)


def kennzahlen(runden):
    b = rt.bericht(runden)
    n = b["anzahl_runden"]
    return {"n": n, "gv": b["gv_gesamt"],
            "je_runde": (b["gv_gesamt"] / n) if n else 0.0,
            "liquidationsanteil": b["liquidationsanteil"],
            "ruecklauf": b["groesster_ruecklauf_usd"]}


def bewerte_fenster(simulieren, w, fenster):
    """Auswertung eines Satzes: Kennzahlen je Fenster und im Aggregat.
    ``simulieren(w, von_ms, bis_ms)`` gibt die Runden des Fensters zurueck."""
    je_fenster, alle = [], []
    for von, bis in fenster:
        runden = simulieren(w, von, bis)
        je_fenster.append(kennzahlen(runden))
        alle.extend(runden)
    return {"fenster": je_fenster, "gesamt": kennzahlen(alle)}


def sieb_regeln(basis_ev, kand_ev, konf):
    """Die fuenf Siebregeln a-e als benannte Ausgaben. Urteilt nicht ueber
    das Ganze und korrigiert nichts."""
    b, k = basis_ev["gesamt"], kand_ev["gesamt"]
    paare = list(zip(kand_ev["fenster"], basis_ev["fenster"]))
    anz = sum(1 for kf, bf in paare if kf["je_runde"] > bf["je_runde"])
    fenster = len(paare)
    mehrheit = fenster // 2
    min_fenster = konf["overfit_min_fenster"]
    ruecklauf_grenze = b["ruecklauf"] * RUECKLAUF_TOLERANZ
    return [
        {"regel": "a", "text": "Aggregat schlaegt die Basis",
         "ist": "%.4f" % k["je_runde"], "soll": "> %.4f" % b["je_runde"],
         "ok": k["je_runde"] > b["je_runde"]},
        {"regel": "b", "text": "Mehrheit der Fenster besser",
         "ist": "%d von %d" % (anz, fenster),
         "soll": "> %d und >= %d" % (mehrheit, min_fenster),
         "ok": anz > mehrheit and anz >= min_fenster},
        {"regel": "c", "text": "genug Runden",
         "ist": str(k["n"]), "soll": ">= %d" % konf["overfit_min_runden"],
         "ok": k["n"] >= konf["overfit_min_runden"]},
        {"regel": "d", "text": "Liquidationsanteil nicht ueber der Basis",
         "ist": "%.1f %%" % (100 * k["liquidationsanteil"]),
         "soll": "<= %.1f %%" % (100 * b["liquidationsanteil"]),
         "ok": k["liquidationsanteil"] <= b["liquidationsanteil"]},
        {"regel": "e", "text": "groesster Ruecklauf hoechstens 10 % ueber Basis",
         "ist": "%.2f" % k["ruecklauf"], "soll": "<= %.2f" % ruecklauf_grenze,
         "ok": k["ruecklauf"] <= ruecklauf_grenze},
    ]


def sieb(basis_ev, kand_ev, konf):
    """Die nicht bestandenen Regeln; leer = Sieb bestanden."""
    return [r for r in sieb_regeln(basis_ev, kand_ev, konf) if not r["ok"]]


def _schluessel(werte):
    return tuple(sorted(werte.items()))


def abstieg(basis, bewerte, grenzen, budget):
    """Koordinatenabstieg von ``basis``. ``bewerte(werte) -> Auswertung``.
    Wie Spur 1: die Basis zaehlt in das Budget; ein schon bewerteter Satz
    wird nicht noch einmal gerechnet und kostet kein Budget."""
    gesehen = {}

    def auswerten(werte):
        k = _schluessel(werte)
        if k not in gesehen:
            gesehen[k] = bewerte(werte)
        return gesehen[k]

    basis_ev = auswerten(basis)
    bestes, bestes_ev = basis, basis_ev
    while len(gesehen) < budget:
        bester = bester_ev = None
        for kand in nachbarn(bestes, grenzen):
            if _schluessel(kand) not in gesehen and len(gesehen) >= budget:
                break
            ev = auswerten(kand)
            if (bester_ev is None
                    or ev["gesamt"]["je_runde"]
                    > bester_ev["gesamt"]["je_runde"]):
                bester, bester_ev = kand, ev
        if (bester_ev is None or not bester_ev["gesamt"]["je_runde"]
                > bestes_ev["gesamt"]["je_runde"]):
            break
        bestes, bestes_ev = bester, bester_ev
    return {"basis_ev": basis_ev, "bestes": bestes, "bestes_ev": bestes_ev,
            "auswertungen": len(gesehen)}


def entscheide(basis, bewerte, holdout, grenzen, konf):
    """Abstieg -> Sieb -> Holdout. ``holdout(werte) -> kennzahlen`` wird nur
    aufgerufen, wenn das Sieb bestanden ist, und genau einmal je Satz."""
    erg = abstieg(basis, bewerte, grenzen, konf["such_budget"])
    res = {"kandidat": None, "fast_kandidat": None, "grund": "",
           "regeln": [], "basis_ev": erg["basis_ev"],
           "kandidat_ev": erg["bestes_ev"], "holdout_basis": None,
           "holdout_kandidat": None, "auswertungen": erg["auswertungen"],
           "basis_werte": basis, "bestes": erg["bestes"]}
    if erg["bestes"] == basis:
        res["grund"] = "kein besserer Kandidat gefunden"
        return res

    res["regeln"] = sieb_regeln(erg["basis_ev"], erg["bestes_ev"], konf)
    verstoesse = [r["regel"] for r in res["regeln"] if not r["ok"]]
    if verstoesse:
        res["grund"] = "Sieb nicht bestanden: Regel " + ", ".join(verstoesse)
        return res

    res["holdout_basis"] = holdout(basis)
    res["holdout_kandidat"] = holdout(erg["bestes"])
    hb, hk = res["holdout_basis"], res["holdout_kandidat"]
    if not (hk["je_runde"] > hb["je_runde"]
            and hk["n"] >= konf["holdout_min_runden"]):
        res["fast_kandidat"] = erg["bestes"]
        res["grund"] = "Holdout nicht bestanden"
        return res

    res["kandidat"] = erg["bestes"]
    res["grund"] = ("Vorschlag: Sieb a-e und Holdout bestanden "
                    "(%d Auswertungen)" % erg["auswertungen"])
    return res
