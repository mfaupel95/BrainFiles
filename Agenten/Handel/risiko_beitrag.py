"""Risiko-Beitrag: welchen Teil des Risikos traegt jede Spur?

Die Frage, die die Handelszentrale seit Wochen nicht beantwortet:
31 offene Positionen auf sieben Spuren, jede mit ihrem eigenen Deckel, jede
mit ihrem eigenen Journal - und daraus wird eine Summe gemacht, als waeren
es 31 unabhaengige Risiken. Sind es nicht.

WAS HIER GEZAEHLT WIRD
----------------------
Je offener Position der Abstand zwischen Einstieg und Stop, in der
Waehrung der Spur:

    Risiko = |Einstieg - Stop| / Einstieg * Nominal

Das ist der Betrag, den die Position verliert, wenn der Stop greift. Bei
Positionen OHNE Stop ist das nicht 0 und auch nicht unendlich - dort wird
der Deckel der Wachen angesetzt und die Position als `ohne Stop` gemeldet,
denn sie ist das eigentliche Risiko im Haus (T-273).

WARUM PRO SPUR UND NICHT NUR DIE SUMME
--------------------------------------
Beides, und das ist der Punkt. Die Summe allein sagt, dass 840 USD Risiko
im Buch stehen; sie sagt nicht, dass eine Spur davon 610 traegt und die
sechs anderen zusammen 230. Der Beitrag JE Spur ist die Zahl, an der man
etwas aendern kann - und an der man sieht, wenn eine Spur zur Haelfte des
Gesamtrisikos geworden ist, ohne dass jemand es bemerkt hat.

Ein Deckel je Spur wird mitgefuehrt: `kill_switch_gesamt_usd` (Rücklauf
seit Hochstand) und `max_gesamt_usd` (Buchdeckel). Der Beitrag wird gegen
den Deckel gestellt, nicht nur gegen null - eine Spur, die 60 % ihres
Deckels belegt, ist meldepflichtig, auch wenn das Gesamtrisiko klein klingt.

WENN DIE POSITIONEN STAPELN
---------------------------
Faellt dieselbe Basis in mehreren Spuren auf, zaehlt jede ihren vollen
Betrag, und die Summe enthaelt die Position mehrfach. Genau das ist der
Punkt der Wache: sie weist die Doppelzaehlung aus, statt sie zu verbergen -
sie ersetzt keine Zusammenfassung, sie macht sichtbar, dass man eine
braucht.
"""

import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
# Diese Datei liegt IN Agenten/Handel. `dirname(HIER)` waere Agenten/ - und
# dann findet die Schleife ueber die Spuren nichts, weil unter Agenten/ nur
# Unterordner ohne wachen.json liegen. Der Bericht meldete daraufhin
# "Keine offenen Positionen im Haus", was schlimmer war als ein Absturz: die
# Zahl sah aus wie ein Befund und war keiner.
HANDEL = HIER
if HANDEL not in sys.path:
    sys.path.append(HANDEL)


def _lade(pfad):
    try:
        with open(pfad, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def spuren():
    """Alle Spuren mit einem Zustand."""
    d = {}
    for name in sorted(os.listdir(HANDEL)):
        ordner = os.path.join(HANDEL, name)
        if not os.path.isdir(ordner):
            continue
        if os.path.isfile(os.path.join(ordner, "wachen.json")):
            d[name] = ordner
    return d


def beitrag_der_spur(name, ordner):
    z = _lade(os.path.join(ordner, "zustand.json"))
    w = _lade(os.path.join(ordner, "wachen.json"))
    pos = z.get("positionen") or ([z["position"]] if z.get("position") else [])
    # gitter fuehrt seine offenen Stufen in `lose`, NICHT in `positionen`
    # (gitter/handeln.py: z["lose"][str(i)] beim KAUF). Ein Werkzeug, das nur
    # `positionen` liest, sieht diese Spur als leer - am 04.10.2026 mit 0
    # Positionen, obwohl ein BTC-Bestand ohne Stop im Haus stand, den keine
    # Wache finden konnte, weil niemand ihn zaehlte. Der Notaus steht in
    # z["_notaus"] und wird beim KAUF gesetzt, nicht von Hand eingetragen.
    #
    # BEIDE Formen sind gemessen (04.10.2026): `lose` ist ein DICT mit dem
    # Stufennummer als Schluessel, `leiter.zustand` ist eine LISTE, deren Index
    # die Stufennummer ist. Der erste Versuch nahm fuer beides eine Liste
    # und zaehlte 0 Positionen - dieselbe Zahl wie vorher, nur aus einem
    # anderen Grund. Ein geaenderter Code, der dieselbe Zahl liefert, ist
    # kein Fortschritt, sondern ein zweiter Irrtum.
    leiter = z.get("leiter") or {}
    zustaende = leiter.get("zustand") or {}
    for stufe, los in (z.get("lose") or {}).items():
        if not isinstance(los, dict):
            continue
        st = str(stufe)
        if st in zustaende:
            zustand_stufe = zustaende[st]
        elif isinstance(zustaende, list) and st.isdigit():
            i = int(st)
            zustand_stufe = zustaende[i] if 0 <= i < len(zustaende) else None
        else:
            continue
        if str(zustand_stufe) != "gekauft":
            continue
        pos.append({"inst": z.get("instrument"), "seite": "long",
                    "einstieg": los.get("einstieg"), "nominal": los.get("brutto"),
                    "stop": z.get("_notaus"), "modus": z.get("modus", "papier")})
    zeilen = []
    for p in pos:
        try:
            ein = float(p.get("einstieg") or 0)
            stop = float(p.get("stop") or 0)
            nom = float(p.get("nominal") or p.get("usd") or p.get("eur")
                        or p.get("nominal_usd") or 0)
        except (TypeError, ValueError):
            continue
        if not ein or not nom:
            continue
        if stop:
            anteil = abs(ein - stop) / ein
            risiko = anteil * nom
            marke = ""
        else:
            # Ohne Stop ist das Risiko der Deckel, nicht null.
            anteil = 1.0
            risiko = nom
            marke = " OHNE STOP"
        zeilen.append({"inst": p.get("inst") or p.get("paar") or "?",
                       "seite": p.get("seite") or "?",
                       "einstieg": ein, "stop": stop, "nominal": nom,
                       "risiko": risiko, "anteil": anteil, "marke": marke,
                       "modus": p.get("modus") or "papier"})
    summe = sum(z["risiko"] for z in zeilen)
    return {"spur": name, "positionen": zeilen, "risiko": summe,
            "nominal": sum(z["nominal"] for z in zeilen),
            "waehrung": w.get("waehrung") or "USD",
            "deckel": float(w.get("kill_switch_gesamt_usd")
                            or w.get("max_gesamt_usd")
                            or w.get("budget_usd") or 0) or None,
            "trigger": str(w.get("trigger_modus") or ""),
            "live": bool(w.get("handel_erlaubt"))}


def ermittle():
    daten = []
    for name, ordner in spuren().items():
        b = beitrag_der_spur(name, ordner)
        if b["positionen"]:
            daten.append(b)
    daten.sort(key=lambda d: -d["risiko"])
    gesamt = sum(d["risiko"] for d in daten)
    for d in daten:
        d["anteil_am_gesamt"] = (d["risiko"] / gesamt * 100.0) if gesamt else 0.0
    return daten, gesamt


def basisform(inst):
    """Die BASIS hinter dem Instrument - BTC, ETH, SOL, ...

    Fuenf Spuren mit "BTC-USDT-SWAP", vier mit "BTC-USDC" und zwei mit
    "BTC-USDT" sind EINE Wette auf BTC, nicht elf. Die Summe der
    Positionsrisiken zaehlt sie elfmal; erst diese Zusammenfassung macht
    daraus eine Zahl, mit der man etwas anfangen kann.
    """
    s = str(inst or "?").upper()
    # Der Perp-Zuendstoerter "-SWAP" und die Perp-Bindung "_UM_XPERP"
    s = s.replace("-SWAP", "").replace("_UM_XPERP", "")
    for trenner in ("-USDC", "-USDT", "-USD", "-EUR", "-USD_UM_"):
        s = s.split(trenner)[0]
    if "_" in s:
        s = s.split("_")[0]
    # XBT ist BTC. Kraken fuehrt Bitcoin unter dem Kuerzel XBT; ohne diese
    # Zuordnung gehoeren xperp-Positionen zur Basis "XBT" und der Deckel
    # sperrt BTC-USDT-SWAP, laesst XBT-USD aber durch - ein Deckel, den man
    # mit einem anderen Namen umgeht.
    if s in ("XBT", "XBTUSD"):
        s = "BTC"
    return s or "?"


def bericht():
    daten, gesamt = ermittle()
    if not daten:
        return "Keine offenen Positionen im Haus."
    z = []
    z.append("%-24s %4s %10s %10s %8s %10s  %s"
             % ("Spur", "Pos", "Nominal", "Risiko", "Anteil", "Deckel", "Modus"))
    z.append("-" * 100)
    for d in daten:
        z.append("%-24s %4d %10.2f %10.2f %7.1f%% %10s  %s"
                 % (d["spur"], len(d["positionen"]), d["nominal"], d["risiko"],
                    d["anteil_am_gesamt"],
                    ("%.0f" % d["deckel"]) if d["deckel"] else "-",
                    ("LIVE" if d["live"] else "Papier")
                    + (" / " + d["trigger"] if d["trigger"] else "")))
    z.append("-" * 100)
    z.append("%-24s %4d %10s %10.2f" % ("SUMME der Spuren", sum(
        len(d["positionen"]) for d in daten), "-", gesamt))
    # Die eigentliche Zahl: je BASIS einmal
    nach_basis = {}
    for d in daten:
        for p in d["positionen"]:
            b = basisform(p["inst"])
            eintrag = nach_basis.setdefault(
                b, {"risiko": 0.0, "nominal": 0.0, "n": 0, "spuren": set(),
                    "ohne_stop": False, "schlimm": 0.0})
            eintrag["risiko"] += p["risiko"]
            eintrag["nominal"] += p["nominal"]
            eintrag["n"] += 1
            eintrag["spuren"].add(d["spur"])
            if p["marke"]:
                eintrag["ohne_stop"] = True
            # Was EINE Bewegung kostet: der weiteste Stop der Gruppe
            eintrag["schlimm"] = max(eintrag["schlimm"], p["risiko"])
    echt = sum(e["risiko"] for e in nach_basis.values())
    z.append("%-24s %4d %10s %10.2f" % ("davon je BASIS gebuendelt",
                                        len(nach_basis), "-", echt))
    z.append("")
    z.append("DIE EIGENTLICHE ZAHL: was auf EINEN Kurs liegt.")
    z.append("Fuenf Spuren mit BTC-USDT-SWAP, vier mit BTC-USDC und zwei mit")
    z.append("BTC-USDT sind EINE Wette - sie fällt oder steigt zusammen. Das")
    z.append("Risiko addiert sich zwar (jede Position hat ihren Stop), aber")
    z.append("AUSGELOEST wird es von EINER Bewegung. Die Spalte 'im schlimmsten")
    z.append("Fall' nennt, was diese eine Bewegung kostet: Nominal mal dem")
    z.append("weitesten Stop der Gruppe.")
    z.append("")
    z.append("%-10s %4s %10s %10s %14s  %s"
             % ("Basis", "Pos", "Nominal", "Risiko", "schlimmster Fall", "in Spuren"))
    z.append("-" * 100)
    for b in sorted(nach_basis, key=lambda k: -nach_basis[k]["nominal"])[:12]:
        e = nach_basis[b]
        z.append("%-10s %4d %10.2f %10.2f %14s  %d Spuren%s"
                 % (b, e["n"], e["nominal"], e["risiko"],
                    ("%.2f" % e["schlimm"]) if e.get("schlimm") else "-",
                    len(e["spuren"]),
                    "  OHNE STOP" if e["ohne_stop"] else ""))
    z.append("")
    z.append("Kapital auf den groessten Basis: %s"
             % ("%s %.2f USD in %d Spuren"
                % (sorted(nach_basis, key=lambda k: -nach_basis[k]["nominal"])[0],
                   nach_basis[sorted(nach_basis,
                                    key=lambda k: -nach_basis[k]["nominal"])[0]]["nominal"],
                   len(nach_basis[sorted(nach_basis,
                                        key=lambda k: -nach_basis[k]["nominal"])[0]]["spuren"]))
                if nach_basis else "-"))
    # Stapel: dieselbe Basis mehrfach
    treffer = {}
    for d in daten:
        for p in d["positionen"]:
            treffer.setdefault(p["inst"], []).append(d["spur"])
    doppelt = {k: v for k, v in treffer.items() if len(v) > 1}
    if doppelt:
        z.append("")
        z.append("STAPEL (dieselbe Basis in mehreren Spuren, Risiko mehrfach gezaehlt):")
        for inst, spuren in sorted(doppelt.items()):
            z.append("  %-14s %s" % (inst, ", ".join(spuren)))
        mehrfach = sum(sum(d["risiko"] for d in daten
                           for p in d["positionen"] if p["inst"] == k)
                      for k in doppelt)
        z.append("  -> %.2f USD der Gesamtsumme sind gestapelt, %.1f %%"
                 % (mehrfach, mehrfach / gesamt * 100.0 if gesamt else 0))
    # Deckel
    ueber = [d for d in daten
             if d["deckel"] and d["risiko"] > d["deckel"]]
    if ueber:
        z.append("")
        z.append("UEBER DEM DECKEL:")
        for d in ueber:
            z.append("  %-22s %.2f von %.2f" % (d["spur"], d["risiko"], d["deckel"]))
    return "\n".join(z)


if __name__ == "__main__":
    print(bericht())