#!/usr/bin/env python3
"""Zeitversatz messen: was der Kurs in der Wartezeit zwischen Signal und Kauf macht.

AUFTRAG Max 21.09.2026 ("zeitversatz messen"), die zweite Haelfte der
Slippage-Frage. Die erste war die Pool-Tiefe (`spiegel/slippage_messen.py`):
fuer 50 USD Order kostet sie im Median 0,33 % - wenig. Was bleibt, ist die
ZEIT: die Kopier-Spuren entdecken einen Kauf des Vorbilds erst beim naechsten
Abruf.

Gemessen ist der Verzug schon: in `kopier1zu1/handelsjournal.csv` steht je
Einstieg `trade_zeit` (Zeitpunkt des Vorbilds) und `zeit` (unsere Buchung) -
Median 566 s, p75 777 s. Was darin der KURS macht, weiss niemand: der Einstieg
wird nicht mit dem Marktpreis gebucht, sondern mit `preis_vorbild * 1,05`.
Die 5 % sind eine ANNAHME, und sie steht in jeder Zeile identisch da - genau
das Zeichen einer gesetzten Zahl, nicht einer gemessenen.

WAS DIESES SKRIPT TUT

  --sammeln (Vorgabe, fuer den Cron): holt fuer die juengsten Einstiege der
  Kopier-Spuren den JETZIGEN Marktpreis (pump.fun swap-api, dieselbe Quelle
  wie die Spur) und schreibt je Einstieg und Altersstufe EINE Zeile nach
  `Agenten/Handel/zeitversatz.csv`:

      signal_zeit, spur, symbol, token, alter_min, preis_signal, preis_jetzt

  Altersstufen: 0-5, 5-15, 15-30, 30-60, 60-180, 180-720 Minuten. Je Stufe
  wird nur der erste Treffer behalten - sonst fuellt der 5-Minuten-Takt die
  Datei mit hundert Zeilen je Einstieg und dasselbe Alter.

  --bericht: rechnet je Altersstufe den Median (und die Quartile) der
  Kursaenderung gegen den Signalpreis und stellt sie der 5-%-Annahme
  gegenueber. Das ist die Antwort auf "kostet der Zeitversatz wirklich 5 %?".

KEIN Live-Eingriff: liest Journale, holt oeffentliche Preise, schreibt eine
Messdatei. Keine Order, kein Zustand, keine Spurdatei.

Aufruf (aus Agenten/Handel):
    python zeitversatz_messen.py --sammeln        # Cron, leise wenn nichts
    python zeitversatz_messen.py --bericht
    python zeitversatz_messen.py --sammeln --trocken   # nichts schreiben
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import os
import statistics
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
MESSDATEI = HIER / "zeitversatz.csv"
SPALTEN = ["signal_zeit", "spur", "symbol", "token", "alter_min",
           "preis_signal", "preis_jetzt"]
# Altersstufen in Minuten: (von, bis)
STUFEN = [(0, 5), (5, 15), (15, 30), (30, 60), (60, 180), (180, 720)]
FENSTER_MIN = 720          # aeltere Einstiege werden nicht mehr gesammelt
MAX_ABRUFE = 12            # Preisabrufe je Lauf (Netz schonen)
QUELLEN = (("kopier1zu1", "kopier1zu1/handelsjournal.csv", "preis_vorbild"),
           ("kopier", "kopier/handelsjournal.csv", "preis"))


def _zeit(wert):
    if not wert:
        return None
    try:
        d = dt.datetime.fromisoformat(wert.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def einstiege(quelle, pfad, preis_spalte, jetzt=None):
    """Die Einstiege einer Kopier-Spur, die noch im Messfenster liegen."""
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    p = HIER / pfad
    if not p.is_file():
        return []
    aus = []
    with p.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("aktion") or "").strip().lower() not in ("eroeffnen", "kauf"):
                continue
            z = _zeit(r.get("zeit"))
            if z is None:
                continue
            alter = (jetzt - z).total_seconds() / 60.0
            if alter < 0 or alter > FENSTER_MIN:
                continue
            try:
                preis = float(r.get(preis_spalte) or 0)
            except (TypeError, ValueError):
                preis = 0.0
            if not preis or not r.get("token"):
                continue
            aus.append({"signal_zeit": r["zeit"], "spur": quelle,
                        "symbol": r.get("symbol") or "",
                        "token": r["token"], "alter_min": alter,
                        "preis_signal": preis,
                        "kette": r.get("kette") or "solana"})
    return aus


def stufe(alter_min):
    for von, bis in STUFEN:
        if von <= alter_min < bis:
            return "%d-%d" % (von, bis)
    return None


def schon_gemessen():
    """{(signal_zeit, spur, token, stufe)} aus der Messdatei."""
    vorhanden = set()
    if not MESSDATEI.is_file():
        return vorhanden
    with MESSDATEI.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            vorhanden.add((r.get("signal_zeit"), r.get("spur"), r.get("token"),
                           stufe(float(r.get("alter_min") or 0))))
    return vorhanden


def _preise(punkte):
    """Preisabruf ueber die Kopier-Spur (gleiche Quelle, kein zweiter Weg)."""
    sys.path.insert(0, str(HIER / "kopier"))
    import lesen                                                   # noqa: PLC0415
    return lesen.preise(punkte)


def sammeln(trocken=False):
    jetzt = dt.datetime.now(dt.timezone.utc)
    offen = []
    for quelle, pfad, spalte in QUELLEN:
        for e in einstiege(quelle, pfad, spalte, jetzt):
            offen.append(e)
    fertig = schon_gemessen()
    neu = [e for e in offen
           if (e["signal_zeit"], e["spur"], e["token"],
               stufe(e["alter_min"])) not in fertig]
    # die aeltesten zuerst waeren schnell ausserhalb jeder Stufe - die
    # juengsten zuerst, damit die feinen Stufen belegt werden
    neu.sort(key=lambda e: e["alter_min"])
    neu = neu[:MAX_ABRUFE]
    if not neu:
        return 0

    kurse = _preise([(e["kette"], e["token"]) for e in neu]) or {}
    zeilen, fehlend = [], 0
    for e in neu:
        kurs = kurse.get((e["kette"], e["token"]))
        if not kurs:
            fehlend += 1
            continue
        zeilen.append({"signal_zeit": e["signal_zeit"], "spur": e["spur"],
                       "symbol": e["symbol"], "token": e["token"],
                       "alter_min": "%.1f" % e["alter_min"],
                       "preis_signal": "%.12g" % e["preis_signal"],
                       "preis_jetzt": "%.12g" % kurs})
    if not zeilen:
        return 0
    if not trocken:
        neu_datei = not MESSDATEI.is_file()
        with MESSDATEI.open("a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=SPALTEN)
            if neu_datei:
                w.writeheader()
            for z in zeilen:
                w.writerow(z)
    return len(zeilen)


def bericht():
    if not MESSDATEI.is_file():
        print("Noch keine Messdaten: %s" % MESSDATEI)
        print("Erst sammeln: python zeitversatz_messen.py --sammeln")
        return 1
    je_stufe = {}
    with MESSDATEI.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                a = float(r["alter_min"])
                ps = float(r["preis_signal"])
                pj = float(r["preis_jetzt"])
            except (TypeError, ValueError, KeyError):
                continue
            if ps <= 0:
                continue
            s = stufe(a) or ">720"
            je_stufe.setdefault(s, []).append((pj / ps - 1.0) * 100.0)

    print("=== ZEITVERSATZ: Kursaenderung gegen den Signalpreis ===")
    print("Messdatei: %s" % MESSDATEI)
    if not je_stufe:
        print("Keine auswertbaren Zeilen.")
        return 1
    print()
    print("Alter      n    Median     p25      p75      min       max")
    for von, bis in STUFEN + [(720, 10 ** 9)]:
        schluessel = "%d-%d" % (von, bis) if bis < 10 ** 9 else ">720"
        werte = je_stufe.get(schluessel)
        if not werte:
            continue
        w = sorted(werte)
        print("%-9s %4d  %+7.2f  %+7.2f  %+7.2f  %+7.2f  %+8.2f"
              % (schluessel, len(w), statistics.median(w),
                 w[len(w) // 4], w[3 * len(w) // 4], w[0], w[-1]))
    print()
    print("Vergleich: die Kopier-Spuren buchen den Einstieg mit")
    print("`preis_vorbild * 1,05` - also 5,00 % Aufschlag je Seite, gesetzt, nicht")
    print("gemessen. Der Median je Altersstufe sagt, ob das reicht.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--sammeln", action="store_true", help="Messzeilen schreiben")
    p.add_argument("--bericht", action="store_true", help="Auswertung zeigen")
    p.add_argument("--trocken", action="store_true", help="nichts schreiben")
    a = p.parse_args()
    if a.bericht:
        return bericht()
    n = sammeln(trocken=a.trocken)
    if a.sammeln and not a.trocken:
        # im Cron-Betrieb (no_agent) ist LEERE Ausgabe = nichts senden; eine
        # Sammelzeile je Lauf waere Spam. Nur melden, was neu ist - und das
        # auch nur, wenn ausdruecklich gefragt wurde.
        if os.environ.get("ZEITVERSATZ_LAUT"):
            print("%d Messzeile(n) geschrieben" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())