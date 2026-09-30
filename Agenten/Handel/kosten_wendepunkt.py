#!/usr/bin/env python3
"""Wie viel Gebuehr traegt eine Spur? - die Kosten-Wendepunkte aller Spuren.

WARUM: Mehrere Papier-Spuren sind nur wegen der Kraken-Pro-Gebuehr von 0 %
positiv (orbk ist die auffaelligste: die Runden sind rund 0,5 % breit). Faellt
das Abo weg, kommt die Gebuehr zurueck und die Spuren kippen - bisher stand das
nur als Merksatz in den Handelsregeln, nicht als Zahl je Spur.

Die Rechnung ist eine Zeile:  EV = p*(C - f) - (1-p)*(R + f)
                              =>  f_max = p*C - (1-p)*R
Darin sind R der mittlere Risikoabstand (Einstieg -> Stop), C der mittlere
Chancenabstand (Einstieg -> Ziel), p die gemessene Trefferquote und f die
Gebuehr je Runde (Kauf + Verkauf, in Prozent des Einsatzes). f_max ist die
Gebuehr, ab der die Spur bei UNSERER gemessenen Trefferquote nur noch die
Nullinie trifft.

WAS ES NICHT TUT: keine Prognose, keine Strategie. Es rechnet die eigene
Vergangenheit der Spur nach - und nur Spuren, deren Journal Stop und Ziel
mitschreibt.

Aufruf (aus dem Handel-Ordner):
    python kosten_wendepunkt.py
    python kosten_wendepunkt.py --spuren orbk,gitter,moondev_topmovers
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stoerungen  # gleicher Ordner: Zwangsschluesse sind keine Runden
import journalpaarung as jp  # gleicher Ordner: EINE Paarung fuer alle Auswertungen

HIER = Path(__file__).resolve().parent

EINSTIEG = ("kauf", "eroeffnen", "KAUF", "EINSTIEG", "buy")
AUSSTIEG = ("verkauf", "schliessen", "AUSSTIEG", "sell", "exit")


def _zahl(r, *namen):
    for n in namen:
        v = r.get(n)
        if v not in (None, ""):
            try:
                return float(v)
            except ValueError:
                continue
    return None


def _kennung(r):
    """Die Positionskennung einer Zeile ('' bei Altjournalen)."""
    return jp.kennung(r)


def _grenzen(r):
    """Stop und Ziel einer Zeile - Stop aus `stop_pct`, wenn die Spalte fehlt.

    Einstieg UND Ausstieg gehen durch DIESE Funktion: die Ausstiegszeile fuehrt
    Stop und Ziel als Kopie mit, und der Vergleich in `journalpaarung` (Stufe 3)
    muss denselben Wert sehen wie die Einstiegszeile. Eine Nachbildung waere ein
    zweiter Preis fuer dieselbe Zeile.
    """
    s, z = _zahl(r, "stop"), _zahl(r, "ziel")
    if s is None and r.get("stop_pct"):
        preis = _zahl(r, "preis")
        if preis:
            s = preis * (1 - float(r["stop_pct"]) / 100)
    return s, z


def _paarung_form_b(rows):
    """Form B: Einstieg und Ausstieg zusammenfuehren.

    DIE REGEL STEHT IN `journalpaarung.Paarung` (Kennung zuerst, sonst nur
    eindeutige Faelle) - hier bleibt nur, was diese Auswertung anders rechnet
    (R, C und das Ergebnis in Prozent).

    WARUM NICHT MEHR HIER (T-095, 30.09.2026): bis hierher stand hier
    `offen[inst] = (preis, stop, ziel)`. Zwei gleichzeitige Positionen im selben
    Instrument haben einander damit UEBERSCHRIEBEN - der erste Ausstieg paarte
    mit dem falschen Einstieg oder fiel ganz weg. Gemessen im Backtest ueber
    5,7 Jahre (squeeze): 1092 Einstiege, 1088 Ausstiege, aber nur 759 Runden;
    330 Einstiege waren ueberschrieben, 329 Ausstiege fanden keinen Partner.
    Trefferquote und f_max standen damit auf einer nicht zufaelligen Teilmenge -
    gleichzeitige Positionen im selben Instrument sind eher gleichgerichtet.
    """
    def einstieg_ok(r):
        s, z = _grenzen(r)
        return bool(s and z)

    # Zeilen ohne Instrument oder ohne Preis sind keine Position und kommen gar
    # nicht erst in die Zuordnung (wie vor der Umstellung).
    brauchbar = [r for r in rows if jp.schluessel(r) and _zahl(r, "preis")]
    p = jp.Paarung(einstieg_ok=einstieg_ok)
    raus, zwang = [], []
    ohne_seite = 0
    for ein, r in p.zuordnen(brauchbar):
        inst = jp.schluessel(ein)
        e = _zahl(ein, "preis")
        preis = _zahl(r, "preis")
        s, z = _grenzen(ein)
        # ZWANGSSCHLUESSE ZAEHLEN NICHT MIT: ein Ausstieg mit "herzschlag" im
        # Grund ist keine Handelsentscheidung, sondern die Folge eines Ausfalls.
        # Sie sitzen meist im Verlust - wer sie mitzaehlt, macht die
        # Trefferquote kuenstlich schlecht (gemessen am 21.09.2026: omniquant
        # stand mit 8 solcher Zeilen als "25 % Treffer, nicht tragfaehig" in der
        # Tabelle, obwohl ALLE acht Zwangsschluesse der Ausfaelle vom
        # 16./17.09. waren).
        if stoerungen.ist_stoerung(r.get("grund")):
            zwang.append((inst, (r.get("grund") or "").strip()))
            continue
        # DIE RICHTUNG GEHOERT DAZU (gefunden am 30.09.2026). Ohne Vorzeichen
        # war `(preis/e - 1)` bei einem SHORT verkehrt: ein Short, der im Ziel
        # schliesst, stand als Verlust im Buch. Gemessen an wavetrend
        # (2021-2026, gemischte Richtungen): Summe der Runden mit Vorzeichen
        # -513, ohne Vorzeichen +679 - und `f_max`, `p` und jede Summe darauf
        # waren damit fuer jede gemischt handelnde Spur falsch. Die Seite steht
        # in der EINSTIEGSzeile (`seite`, Werte long/short); fehlt sie, gilt
        # long wie bisher, und die Zahl wird als `ohne_seite` ausgewiesen.
        seite = str(ein.get("seite") or "").strip().lower()
        if seite not in ("long", "short"):
            ohne_seite += 1
            vorz = 1.0
        else:
            vorz = -1.0 if seite == "short" else 1.0
        raus.append((abs(e - s) / e * 100, abs(z - e) / e * 100,
                     (preis / e - 1) * 100 * vorz))
    stand = p.stand()
    return {"runden": raus, "zwang": zwang, "unpaarig": stand["unpaarig"],
            "offen": stand["offen"], "ohne_kennung": stand["ohne_kennung"],
            "zweideutig": stand["zweideutig"], "ohne_seite": ohne_seite}


def paarung(pfad: Path):
    """Die vollstaendige Paarung EINES Journals (Kennung, sonst Instrument).

    Rueckgabe: {"runden", "zwang", "unpaarig", "offen", "ohne_kennung",
                "form_a"}. `unpaarig` sind Ausstiegszeilen OHNE Partner - die
    Zahl, die vorher niemand ausgewiesen hat (sie fehlten still in der
    Trefferquote). `ohne_kennung` sind Einstiege aus Altjournalen.
    """
    leer = {"runden": [], "zwang": [], "unpaarig": 0, "offen": 0,
            "ohne_kennung": 0, "form_a": False}
    if not pfad.is_file():
        return leer
    with pfad.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return leer
    if {"einstieg", "stop", "ziel", "ausgang"} <= set(rows[0]):
        # Form A (orbk/orb): eine Zeile je FERTIGER Runde, nichts zu paaren.
        raus = []
        for r in rows:
            e = _zahl(r, "einstieg")
            s = _zahl(r, "stop")
            z = _zahl(r, "ziel")
            if not e or not s or not z:
                continue
            ergebnis = ((_zahl(r, "ausstieg") or e) / e - 1) * 100
            raus.append((abs(e - s) / e * 100, abs(z - e) / e * 100, ergebnis))
        leer["runden"] = raus
        leer["form_a"] = True
        return leer
    aus = _paarung_form_b(rows)
    aus["form_a"] = False
    return aus


def runden_aus_journal(pfad: Path):
    """((R, C, ergebnis_prozent), zwangsschluesse) - aus beiden Journalformen.

    Form A (orbk): eine Zeile je FERTIGER Runde mit einstieg/stop/ziel/ausgang.
    Form B (Spuren mit spur_buch): je Einstieg eine Zeile mit stop/ziel, je
    Ausstieg eine Zeile mit preis - gepaart wird ueber `pos_id`, und nur ohne
    Kennung (Altjournal) ueber das Instrument. Die Einzelheiten stehen in
    `paarung()`; diese Funktion bleibt die alte Schnittstelle fuer die
    Aufrufer, die nur Runden und Zwangsschluesse brauchen.
    """
    p = paarung(pfad)
    return p["runden"], p["zwang"]


def wendepunkt(runden):
    if not runden:
        return None
    R = statistics.fmean(r[0] for r in runden)
    C = statistics.fmean(r[1] for r in runden)
    p = len([r for r in runden if r[2] > 0]) / len(runden)
    f_max = p * C - (1 - p) * R          # in Prozent des Einsatzes je Runde
    ev_ohne = p * C - (1 - p) * R
    return {"runden": len(runden), "R": R, "C": C, "p": p,
            "f_max": f_max, "ev_ohne": ev_ohne,
            "ergebnis_summe": sum(r[2] for r in runden)}


def urteil(geb, f_max):
    """Der Hinweis zu einer Spur - reine Funktion, damit pruefbar.

    ZWEI EINHEITEN, die nicht verwechselt werden duerfen: `gebuehr_taker` ist
    ein BRUCH je Seite (0.0005 = 0,05 %, 0.006 = 0,6 %), `f_max` dagegen
    Prozent JE RUNDE (Kauf + Verkauf). Bis zum 30.09.2026 druckte das Werkzeug
    den Bruch unveraendert mit Prozentzeichen ("0.001 %" statt "0.050 %") und
    verglich ihn direkt mit f_max - jede Gebuehrenaussage war damit um Faktor
    100 zu klein und der Vergleich bedeutungslos.
    """
    text = ""
    if f_max <= 0:
        text = "  <<< schon bei 0 % Gebuehr nicht tragfaehig"
    elif f_max < 0.4:
        # 0,4 % sind die Taker-Gebuehr beider Seiten ohne Abo - wer darunter
        # liegt, handelt nur, solange die Gebuehr 0 ist.
        text = "  <<< haengt an der Gebuehrfreiheit (unter 0,4 %)"
    if not geb or geb <= 0:
        return text
    geb_runde = 2.0 * geb * 100.0
    if geb_runde >= f_max:
        text += (" UND die gesetzte Gebuehr %.3f %% je Runde (%.3f %% je Seite)"
                 " liegt darueber" % (geb_runde, geb * 100.0))
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spuren", help="Komma-Liste; sonst alle mit Journal")
    a = ap.parse_args()
    # Je JOURNAL eine Zeile, nicht je Ordner: ein Ordner kann mehrere Buecher
    # fuehren (Basis/Mittel, knapp/weit, futures). Ein Sammel-glob ueber
    # handelsjournal*.csv zaehlt sonst dasselbe Buch mehrfach - und die
    # umskalierten Altbestaende (".falsch-skaliert-*") gehoeren nie in eine
    # Kennzahl.
    dateien = []
    for s in sorted(HIER.glob("*/handelsjournal*.csv")):
        if "falsch" in s.name or ".bak-" in s.name:
            continue
        if a.spuren and s.parent.name not in [x.strip() for x in a.spuren.split(",")]:
            continue
        teil = s.name.replace("handelsjournal", "").replace(".csv", "")
        dateien.append((s.parent.name + teil.replace(".", "/"), s))
    if not dateien and a.spuren:
        print("keine Journale zu: %s" % a.spuren)
        return 2

    print("%-22s %6s %6s %6s %6s   %s" % (
        "Spur", "Runden", "R %", "C %", "Treffer", "Gebuehr, ab der die Spur kippt"))
    zeilen = []
    for name, pfad in dateien:
        p = paarung(pfad)
        runden, zwang = p["runden"], p["zwang"]
        w = wendepunkt(runden)
        if not w:
            print("%-22s %6s   -      -      -      keine messbare Runde" % (name, 0))
            continue
        wachen = pfad.parent / "wachen.json"
        geb = None
        if wachen.is_file():
            d = json.loads(wachen.read_text(encoding="utf-8"))
            geb = d.get("gebuehr_taker")
        hinweis = urteil(geb, w["f_max"])
        # Was NICHT in die Quote kam, wird ausgewiesen: ein Zwangsschluss ist
        # keine Handelsentscheidung, eine Ausstiegszeile ohne Partner ist ein
        # Befund (Altjournal ohne Kennung) - beides stillschweigend
        # wegzulassen hiesse, die Trefferquote auf einer kleineren Stichprobe
        # zu behaupten, als im Journal steht (T-095).
        teile = []
        if zwang:
            teile.append("%d Zwangsschluss-Zeile(n) nicht mitgezaehlt" % len(zwang))
        if p["unpaarig"]:
            teile.append("%d Ausstiegszeile(n) OHNE Partner" % p["unpaarig"])
        if p["ohne_kennung"]:
            teile.append("%d Einstieg(e) ohne pos_id" % p["ohne_kennung"])
        zahl = ("  (%s)" % "; ".join(teile)) if teile else ""
        print("%-22s %6d %6.2f %6.2f %5.0f%%   %+.2f %% je Runde%s%s" % (
            name, w["runden"], w["R"], w["C"], w["p"] * 100, w["f_max"], hinweis, zahl))
        zeilen.append((name, w))

    print("\nLesart: f_max ist die Gebuehr JE RUNDE (Kauf+Verkauf) in Prozent des "
          "Einsatzes,\nbei der die gemessene Trefferquote nur noch die Nullinie "
          "trifft. Kraken-Pro: 0 %;\nohne Abo 0,4 % (Taker 0,2 % je Seite). "
          "Spuren mit f_max unter 0,4 %\nhaengen an der Gebuehrfreiheit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
