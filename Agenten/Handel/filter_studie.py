"""Eingangsfilter-Studie fuer die Kopier-Spuren (spiegel, kopier, kopier1zu1).

Prueft auf den vorhandenen Journalen, ob eine Aenderung des
Marktkapitalisierungs-Bands oder der Kette in BEIDEN Zeithaelfte traegt.
Aendert nichts - liefert nur Vorschlagswerte fuer wachen.json.

Die Buchhaltung wird NICHT nachgebaut: je Spur wird <spur>/auswertung.py
ueber den Pfad geladen, ihre lade_ausstiege() liefert die Paare und ihre
kennzahlen() die Zahlen (zwei Buchhaltungen derselben Sache waeren zwei
Wahrheiten).

Aufruf:
    python filter_studie.py                # alle Spuren, Bericht
    python filter_studie.py --spur spiegel
    python filter_studie.py --json         # zusaetzlich Ergebnisdatei
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
SPUREN = ("spiegel", "kopier", "kopier1zu1")
ERGEBNIS = HIER / "filter_studie_ergebnis.json"

MINDEST_JE_HALBE = 30
ANTEIL_ALT = 0.6
UNTERGRENZEN = (100_000, 150_000, 250_000, 500_000)
OBERGRENZEN = (1_000_000, 2_000_000, 5_000_000)

if str(HIER) not in sys.path:
    sys.path.insert(0, str(HIER))

from buchauswertung import kennzahlen as mod_kennzahlen   # noqa: E402


def kurz(betrag):
    """250000 -> 250k, 1000000 -> 1M (nur fuer Regelnamen)."""
    if betrag >= 1_000_000:
        return "%gM" % (betrag / 1_000_000.0)
    return "%gk" % (betrag / 1_000.0)


def zeit_halbieren(aus, anteil_alt=ANTEIL_ALT):
    """Suchhaelfte (aeltere) und Gegenprobe (juengere) nach Zeit."""
    sortiert = sorted(aus, key=lambda a: a.get("zeit") or "")
    grenze = int(round(len(sortiert) * anteil_alt))
    return sortiert[:grenze], sortiert[grenze:]


def masse(aus, kosten):
    """Kennzahlen einer Teilmenge - ueber die Buchhaltung der Spur."""
    if not aus:
        return {"n": 0, "quote": 0.0, "netto": 0.0, "brutto": 0.0,
                "median": 0.0, "gv_usd": 0.0}
    k = mod_kennzahlen(aus, kosten)
    return {"n": k["n"], "quote": round(k["quote"], 2),
            "netto": round(k["netto_pct"], 3),
            "brutto": round(k["brutto_pct"], 3),
            "median": round(k["median_pct"], 3),
            "gv_usd": round(k["gv_usd"], 2)}


def lade_auswertung(spur):
    """Das Auswertungsmodul einer Spur ueber den PFAD laden.

    Alle drei Spuren besitzen ein Modul `auswertung`; ueber sys.path
    gewaenne die zuletzt eingefuegte Spur. Darum je Spur ein eindeutiger
    Modulname.
    """
    pfad = HIER / spur / "auswertung.py"
    if not pfad.exists():
        raise ValueError("unbekannte Spur: %s" % spur)
    name = "auswertung_%s" % spur
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


def lade_spur(spur, journal=None):
    """Ausstiege und Kostensaetze einer Spur - aus ihrer eigenen Auswertung."""
    modul = lade_auswertung(spur)
    aus = (modul.lade_ausstiege(str(journal)) if journal is not None
           else modul.lade_ausstiege())
    return aus, modul._kosten()


def regeln():
    """Die geprueften Eingangsfilter (Spezifikation, Abschnitt 4.3).

    Die letzten zwei Regeln sind die Gegenprobe: ein Band zu VERSCHIEBEN
    statt zu oeffnen und die Kette zu drehen muss die Gegenrichtung zeigen.
    """
    r = []
    for u in UNTERGRENZEN:
        r.append({"name": "untergrenze %s" % kurz(u),
                  "pruef": lambda a, u=u: (a.get("marktkap_usd") or 0) >= u})
    for o in OBERGRENZEN[1:]:
        r.append({"name": "obergrenze %s" % kurz(o),
                  "pruef": lambda a, o=o: (a.get("marktkap_usd") or 1e18) <= o})
    r.append({"name": "nur solana",
              "pruef": lambda a: (a.get("kette") or "").lower() == "solana"})
    r.append({"name": "untergrenze 250k ohne solana",
              "pruef": lambda a: (a.get("marktkap_usd") or 0) >= 250_000
              and (a.get("kette") or "").lower() != "solana"})
    return r


def verdikt(alt, jung, rest_alt, rest_jung, mindest=MINDEST_JE_HALBE):
    """Darf diese Regel als Vorschlag gelten? (Spezifikation 4.2/4.4/5)

    Drei Bedingungen, alle in der Spezifikation begruendet: Besetzung in
    beiden Haelften, positives Vorzeichen in beiden Haelften, Vorsprung
    gegen die Restgruppe in beiden Haelften.
    """
    if alt["n"] < mindest or jung["n"] < mindest:
        return ("nicht entschieden",
                "Gruppe zu klein (%d/%d, mind. %d je Haelfte)"
                % (alt["n"], jung["n"], mindest))
    if alt["netto"] <= 0 or jung["netto"] <= 0:
        return "verworfen", "in einer Haelfte nicht positiv"
    if alt["netto"] <= rest_alt["netto"] or jung["netto"] <= rest_jung["netto"]:
        return "verworfen", "kein Vorsprung gegen die Restgruppe"
    return "traegt", "in beiden Haelften positiv und besser als der Rest"


def pruefe_regel(regel, aus, kosten, mindest=MINDEST_JE_HALBE):
    """Eine Regel auf beiden Haelften und der Restgruppe messen."""
    alt_alle, jung_alle = zeit_halbieren(aus)
    pruef = regel["pruef"]
    drin = [a for a in aus if pruef(a)]
    raus = [a for a in aus if not pruef(a)]
    alt = masse([a for a in alt_alle if pruef(a)], kosten)
    jung = masse([a for a in jung_alle if pruef(a)], kosten)
    rest_alt = masse([a for a in alt_alle if not pruef(a)], kosten)
    rest_jung = masse([a for a in jung_alle if not pruef(a)], kosten)
    urteil, grund = verdikt(alt, jung, rest_alt, rest_jung, mindest)
    return {"regel": regel["name"], "verdikt": urteil, "grund": grund,
            "ganz": masse(drin, kosten), "alt": alt, "jung": jung,
            "rest_alt": rest_alt, "rest_jung": rest_jung,
            "rest_ganz": masse(raus, kosten)}


def studie_aus(aus, kosten, regeln_liste=None, mindest=MINDEST_JE_HALBE):
    """Alle Regeln gegen eine Ausstiegsliste messen."""
    return [pruefe_regel(r, aus, kosten, mindest)
            for r in (regeln_liste if regeln_liste is not None else regeln())]


def studie(spur, journal=None, mindest=MINDEST_JE_HALBE):
    """Die ganze Studie fuer eine Spur."""
    aus, kosten = lade_spur(spur, journal=journal)
    return {"spur": spur, "n": len(aus), "ganz": masse(aus, kosten),
            "regeln": studie_aus(aus, kosten, mindest=mindest)}


def bericht(ergebnis):
    """Der Bericht als Liste von Zeilen (testbar, ohne Druck)."""
    zeilen = ["=== Eingangsfilter-Studie ==="]
    for spur, e in ergebnis.items():
        if e.get("fehler"):
            zeilen.append("%s: FEHLER %s" % (spur, e["fehler"]))
            continue
        g = e.get("ganz") or {}
        zeilen.append("")
        zeilen.append("%s: %d Ausstiege, Ø %.2f %% nach / %.2f %% vor Kosten"
                      % (spur, e.get("n", 0), g.get("netto", 0.0),
                         g.get("brutto", 0.0)))
        for r in e.get("regeln", []):
            zeilen.append(
                "  %-27s %-17s ganz %4d (Ø %+6.2f %%) | alt %4d (Ø %+6.2f %%)"
                " | jung %4d (Ø %+6.2f %%)  %s"
                % (r["regel"], r["verdikt"], r["ganz"]["n"],
                   r["ganz"]["netto"], r["alt"]["n"], r["alt"]["netto"],
                   r["jung"]["n"], r["jung"]["netto"], r["grund"]))
    return zeilen


def main(argv=None):
    p = argparse.ArgumentParser(description="Eingangsfilter-Studie")
    p.add_argument("--spur", action="append", default=None,
                   help="Spur (mehrfach moeglich), Vorgabe alle")
    p.add_argument("--json", action="store_true",
                   help="Ergebnis zusaetzlich als JSON schreiben")
    p.add_argument("--journal", default=None,
                   help="Testhaken: dieselbe Journaldatei fuer alle Spuren")
    p.add_argument("--mindest", type=int, default=MINDEST_JE_HALBE,
                   help="Mindestbesetzung je Haelfte (Vorgabe 30)")
    a = p.parse_args(argv)
    spuren = tuple(a.spur) if a.spur else SPUREN

    ergebnis = {}
    for spur in spuren:
        try:
            ergebnis[spur] = studie(spur, journal=a.journal,
                                    mindest=a.mindest)
        except Exception as exc:                      # noqa: BLE001
            ergebnis[spur] = {"spur": spur, "n": 0, "regeln": [],
                              "fehler": "%s: %s" % (type(exc).__name__, exc)}

    for zeile in bericht(ergebnis):
        print(zeile)
    if a.json:
        ERGEBNIS.write_text(json.dumps(ergebnis, ensure_ascii=False,
                                       indent=2), encoding="utf-8")
        print("\ngeschrieben: %s" % ERGEBNIS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
