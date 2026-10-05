#!/usr/bin/env python3
"""Boersen-Bruecke fuer xperp: VERKAUFE buchen, wo bisher Geister gebucht wurden.

Die Luecke, die sie schliesst (gemessen in der Nacht 04./05.10.2026)
-------------------------------------------------------------------------
`buche_abgleich` hatte vier Stufen. `bueche_geister_aus` kennt nur ZWEI
Zustaende: eine Position steht an der Boerse, oder sie fehlt. Ein DRITTER
Zustand - die war da und ist kleiner geworden, weil Max verkauft hat - fiel
durch:

    18:43  Boerse 19.616  Buch 19.616  steht da   -> bleibt
    18:58  Boerse 12.033  Buch 12.033  steht da   -> bleibt
    22:32  Boerse  8.033  Buch  8.033  steht da   -> bleibt
    23:00  Boerse      0  Buch  8.033  FEHLT     -> "Geister" -> 0.00 Erloes

Und weil `bueche_groessen_abgleichen` (die vierte Stufe) ERST DANACH laeuft,
hatte die erste die Position schon geloescht. Die Bruecke existierte - sie lief
in jedem Zyklus - sie stand nur an der falschen Stelle und kannte den
Teilverkauf nicht.

Der Schaden war nicht die Ausbuchung, sondern der PREIS: ein Geist wird
neutral gebucht (Einsatz zurueck, `geister_nachziehen.py` macht das fuer
Erlos = 0.00). Die echten Ergebnisse der Boerse waren abrufbar:

    STRK   realizedPnl  +70,76 USD   (11.388 Stuecke mit Gewinn verkauft)
    SOL    realizedPnl   +0,96 USD
    QUANT  realizedPnl  -18,47 USD

Diese Datei bucht den Verkauf zum ECHTEN Kurs aus `/trade/fills`, das ist der
einzige Ort, an dem OKX den Ausfuehrungspreis fuehrt
(`positions-history` liefert `avgPx: None` - daran scheitert `_geist_erloes`
und bucht deshalb neutral).

WAS SIE NICHT TUT
-----------------
* Keine Order. Kein Stop, kein Storno, kein Kauf. Nur Buchhaltung.
* Im Papierlauf (`live=False`) exakt nichts: der Abgleich liest sonst die
  Boerse und schreibt Papierpositionen in den Live-Buchstand.
* Kein Geister-Filter-Ersatz. Was danach WIRKLICH fehlt, bleibt fuer
  `bueche_geister_aus` - diese Datei nimmt dem Filter nur die Faelle weg, bei
  denen die Boerse einen Verkauf bezeugen kann.
* Kein Buchen ohne Zeugen: ohne `fills` wird neutral gebucht, mit Vermerk.

MERKSATZ: ein Verkauf braucht den Kurs. Fehlt der Zeuge, ist die Buchung
neutral und wird als solche BENANNT - nie als "aufgeraeumt".

Aufruf (aus dem Handel-Ordner oder ueberall):
    ../scanner/.venv/Scripts/python.exe xperp/boersen_bruecke.py --trockenlauf
"""
from __future__ import annotations

import argparse
import collections
import datetime
import importlib.util
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)


def lade(pfad, name):
    """Fachmodule ueber den PFAD laden. `import okxf` wuerde bei einem
    gleichnamigen Modell in sys.path[0] das FALSCHE nehmen (Hausregel)."""
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


okxf = lade(os.path.join(HIER, "okxf.py"), "bruecke_okxf")

# Wie weit zurueck nach Fuellungen gesucht wird. 12 h deckt einen Takt des
# Dauerlaufs (15 min) mit Reserve ab; darueber hinaus waere eine Fuellung fuer
# die Bruecke zu alt und gehoert in die Tagesabrechnung.
FUELL_FRIST_MS = 12 * 3600 * 1000
# Unterhalb dieser Menge gilt eine Differenz als Rundung, nicht als Verkauf.
MENGEN_TOLERANZ = 1e-9


def zeit_ms(iso):
    """ISO-Zeitstempel -> Millisekunden seit Epoche (None bei Unlesbarem)."""
    if not iso:
        return None
    try:
        t = datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=datetime.timezone.utc)
    return int(t.timestamp() * 1000)


def jetzt_ms():
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)


def boersen_mengen():
    """{instId: pos} von der Boerse. Bei einem Netzfehler None - der
    Aufrufer fasst das Buch dann nicht an."""
    try:
        return {p["instId"]: float(p.get("pos") or 0.0)
                for p in okxf.positionen()}
    except Exception as e:                                       # noqa: BLE001
        print("  Boersenabfrage fehlgeschlagen (%s) - Buch bleibt unberuehrt" % e)
        return None


def verkaeufe_seit(seit_ms, bis_ms=None):
    """Fuellungen, die VERKAEUFE sind, gruppiert je Instrument.

    Aus OKX `/trade/fills`: `side` ist die Seite der Order (sell = Verkauf
    einer Long-Position), `fillSz`/`fillPx` sind Menge und Kurs. Ein Kauf
    (side=buy) schliesst eine Short-Position und zaehlt hier nicht mit - der
    Geister-Filter dieser Spur sieht Long-Positionen, und eine Short-Position
    waere ein eigener Fall.

    Rueckgabe: {instId: {"menge": float, "kurs": float (gewichtet),
                        "anzahl": int, "erloes": float, "erste": ms,
                        "letzte": ms}}
    """
    if bis_ms is None:
        bis_ms = jetzt_ms()
    pfad = "/api/v5/trade/fills?begin=%d&end=%d" % (
        max(0, (seit_ms or bis_ms - FUELL_FRIST_MS)), bis_ms)
    try:
        roh = okxf._mit_wiederholung(pfad, signiert=True)
    except Exception as e:                                       # noqa: BLE001
        print("  Fuellungsabfrage fehlgeschlagen (%s) - wird neutral gebucht" % e)
        return {}
    agg = {}
    for f in roh or []:
        if (f.get("side") or "").lower() != "sell":
            continue
        inst = f.get("instId")
        try:
            menge = float(f.get("fillSz") or 0.0)
            kurs = float(f.get("fillPx") or 0.0)
            ts = int(f.get("ts") or 0)
        except (TypeError, ValueError):
            continue
        if not inst or menge <= 0:
            continue
        a = agg.setdefault(inst, {"menge": 0.0, "volumen": 0.0,
                                  "anzahl": 0, "erste": ts, "letzte": ts})
        a["menge"] += menge
        a["volumen"] += menge * kurs
        a["anzahl"] += 1
        a["erste"] = min(a["erste"], ts)
        a["letzte"] = max(a["letzte"], ts)
    for a in agg.values():
        a["kurs"] = a["volumen"] / a["menge"] if a["menge"] else 0.0
        a["erloes"] = a["volumen"]
    return agg


def plan(z, live=True, jetzt=None):
    """Der Abgleich-Plan: je Live-Position im Buch, was die Boerse sagt.

    Rueckgabe: Liste von Dicts mit `aktion` in
      "verkauf"   - Buchmenge groesser als die Boerse, Verkauf bezeugt
      "geister"   - die Boerse fuehrt die Position nicht mehr
      "unveraendert" - Mengen stimmen
    oder None, wenn die Boerse nicht antwortet. None ist KEIN leerer Plan:
    ein leerer Plan wuerde "alles stimmt" bedeuten und der Aufrufer wuerde
    einen Netzausfall als Bestaetigung lesen.
    """
    try:
        an_der_boerse = boersen_mengen()
    except Exception as e:                                       # noqa: BLE001
        print("  Boersenabfrage nicht auswertbar (%s) - Buch bleibt unberuehrt"
              % e)
        return None
    if an_der_boerse is None:
        return None
    jetzt = jetzt if jetzt is not None else jetzt_ms()
    aus = []
    for p in z.get("positionen", []):
        if p.get("modus") != "live":
            continue
        inst = p.get("inst")
        soll = abs(float(p.get("kontrakte") or 0.0))
        ist = abs(an_der_boerse.get(inst, 0.0))
        eintrag = {
            "pos_id": p.get("pos_id"),
            "inst": inst,
            "buch": soll,
            "boerse": ist,
            "eroeffnet_zeit": p.get("eroeffnet_zeit"),
            "einstand": float(p.get("preis") or 0.0),
            "margin": float(p.get("margin_usd") or p.get("margin") or 0.0),
        }
        if abs(ist - soll) <= MENGEN_TOLERANZ:
            eintrag["aktion"] = "unveraendert"
            eintrag["differenz"] = 0.0
            aus.append(eintrag)
            continue
        eintrag["differenz"] = soll - ist
        if ist >= MENGEN_TOLERANZ:
            eintrag["aktion"] = "verkauf"      # noch Rest offen
        else:
            eintrag["aktion"] = "geister"      # ganz weg
        aus.append(eintrag)
    # Fuellungen nur fuer die Positionen holen, die eine Differenz haben.
    betroffen = [e for e in aus if e["aktion"] in ("verkauf", "geister")]
    if betroffen:
        frueheste = min([zeit_ms(e["eroeffnet_zeit"]) or 0 for e in betroffen])
        since = frueheste or (jetzt - FUELL_FRIST_MS)
        verkaeufe = verkaeufe_seit(max(0, min(since, jetzt - FUELL_FRIST_MS)))
        for e in betroffen:
            v = verkaeufe.get(e["inst"])
            e["verkauf"] = v
            # DER Kern des ganzen Problems, und der erste Testlauf hat ihn
            # gefunden: eine GANZ verkaufte Position hat an der Boerse 0, und
            # `ist >= 1e-9` ist damit falsch - sie bleibt "Geister", obwohl die
            # Boerse den Verkauf bezeugt. Genau dorthin gehoeren die Positionen
            # dieser Nacht (STRK 8.033 -> 0), und genau dort ging der Erloes
            # verloren. Die Einstufung entscheidet sich deshalb am ZEUGEN, nicht
            # am Restbestand: bezeugt die Boerse einen Verkauf in der Menge der
            # Differenz, ist es ein Verkauf.
            if e["aktion"] == "geister" and v and v["menge"] >= e["differenz"] - 1e-6:
                e["aktion"] = "verkauf"
    return aus


def bericht(plan_, kopf="TROCKENLAUF"):
    z = []
    z.append(kopf)
    if plan_ is None:
        z.append("  Boerse nicht erreichbar - Buch bleibt unberuehrt")
        return "\n".join(z)
    if not plan_:
        z.append("  keine Live-Positionen im Buch")
        return "\n".join(z)
    verk = [e for e in plan_ if e["aktion"] == "verkauf"]
    geis = [e for e in plan_ if e["aktion"] == "geister"]
    z.append("  %d Live-Position(en): %d unveraendert, %d Teilverkauf, %d ganz weg"
             % (len(plan_), len(plan_) - len(verk) - len(geis), len(verk), len(geis)))
    for e in verk + geis:
        v = e.get("verkauf")
        bezeugt = ""
        if v:
            bezeugt = (" | Boerse bezeugt %.0f Stuecke @ %.6g (%d Fuellung/en)"
                       % (v["menge"], v["kurs"], v["anzahl"]))
        else:
            bezeugt = " | KEINE Fuellung - wuerde NEUTRAL gebucht"
        z.append("  %-30s Buch %9.2f -> Boerse %9.2f (%s)%s"
                 % (str(e["inst"])[:30], e["buch"], e["boerse"], e["aktion"], bezeugt))
        if e["aktion"] == "verkauf":
            z.append("      -> %d Stueck VERKAUF zum echten Kurs, Rest bleibt offen"
                     % round(e["differenz"]))
    return "\n".join(z)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Boersen-Bruecke: Verkaeufe buchen, wo bisher Geister gebucht wurden.")
    ap.add_argument("--trockenlauf", action="store_true",
                    help="nur zeigen (Vorgabe: es wird ohnehin nichts geschrieben)")
    ap.add_argument("--zustand", default=None,
                    help="Zustandsdatei (Vorgabe: die aktive Risikostufe)")
    ap.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    args = ap.parse_args(argv)

    pfad = args.zustand
    if not pfad:
        # Die Stufe folgt der Umgebung, die der Aufrufer gesetzt hat - dieselbe
        # Reihenfolge wie im Rest des Hauses: erst Stufe, dann Arm.
        arm = os.environ.get("HANDEL_BUCH", "")
        pfad = os.path.join(HIER, "zustand%s.json" % (("." + arm) if arm else ""))
    if not os.path.exists(pfad):
        print("Zustand fehlt: %s" % pfad)
        return 2
    with open(pfad, encoding="utf-8") as f:
        z = json.load(f)
    p = plan(z, live=True)
    if args.json:
        print(json.dumps(p, ensure_ascii=False, indent=2))
        return 0
    print(bericht(p, "BOERSEN-BRUECKE (nur gelesen, nichts gebucht)"))
    print()
    print("Buchen tut das erst `handeln.buche_abgleich()` - und dort VOR")
    print("`bueche_geister_aus`. Diese Datei schreibt aus Sicherheitsgruern")
    print("nichts selbst: sie soll erst am Trockenlauf-Pfad geprueft sein.")
    return 0


if __name__ == "__main__":
    sys.exit(main())