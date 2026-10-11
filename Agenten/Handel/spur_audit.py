#!/usr/bin/env python3
"""Spur-Audit: hat eine Spur Edge, und ist ihre Statistik ueberhaupt echt?

ANLASS (T-322, 03.10.2026)
--------------------------
Der Scanner galt als beste Spur des Hauses: +17,49 % auf den Einsatz, 85 %
Trefferquote, t = 15,3. Das war kein Signal, sondern ein Rechenfehler - der
Einstieg kam aus einem zwei Tage alten Tagesbericht, das Ziel war beim Kauf
schon erfuellt, und 82 Runden an einem einzigen Tag ergaben +1866 %.

Bis dahin gab es im Haus KEIN Werkzeug, das diese Fehlerklasse von selbst
findet. Es gab `auswertung_alle.py` (rechnet die Zahlen der Spuren), und es
gab Einzelfallbefunde (T-322 Scanner, T-178 Platzhalter-Einstiegsgrund). Wer
eine neue Spur baute, hatte keine Messung, an der er seine Runden vor der
Freigabe haette vorbeilegen lassen koennen. Genau darum ist die eine Spur mit
dem groessten Fehler auch die mit den schoensten Zahlen gewesen.

DAS WERKZEUG
------------
Es beantwortet zwei Fragen und beantwortet sie fuer ALLE Spuren in einem
Durchgang, statt je Spur eine eigene Messung zu bauen:

  FRAGE 1 - Ist die Statistik echt?
      Drei Alarme, jeder aus dem Journal allein lesbar, ohne Kursdaten:

      a) `SCHEIN`  Die Haltedauer der Runden liegt im Takt des Aufrufers.
         Ein echter Marktausstieg braucht Stunden bis Tage. Faellt der Median
         der Haltedauer unter das Doppelte des Aufrufertakts, sind die Runden
         Zyklen, keine Handelsentscheidungen. Gemessen am Scanner: Median
         0,25 h bei 0,25 h Aufrufertakt, 101 von 123 Runden unter 1 h.
      b) `EINER`   Ein Instrument traegt die Mehrheit aller Runden. Ein
         Streuportfolio kann das nicht - 81 von 123 Runden auf AVAX-USDT
         waren ein Kandidat, der im Viertelstundentakt gekauft und verkauft
         wurde, weil das Ziel sofort wieder erfuellt war.
      c) `PREIS`   Die Einstiegspreise einer Spur sind je (Instrument, Tag)
         IDENTISCH. Ein Marktkurs ist zweimal am Tag nie auf sechs
         Nachkommastellen gleich; das heisst, die Spur hat einen Preis
         UEBERNOMMEN statt geholt - der Snapshot-Fehler aus T-322. Geprueft
         wird nur, wo dieselbe Position mehrfach am Tag eroeffnet wurde,
         sonst waere ein Einmalkauf schon ein Alarm.

  FRAGE 2 - Hat die Spur Edge?
      Eine Trefferquote ist kein Edge. Eine Spur kann 70 % der Runden
      gewinnen und trotzdem weniger verdienen als der Markt, weil sie die
      Verlierer laenger haelt als die Gewinner (genau das war am Scanner
      der Fall: 93 % Treffer, aber +19 % Mean nur, weil die Scheinrunden
      mitzogen; ehrlich 38 % bei +1,99 %).

      Gemessen wird darum je Runde:
        - das Ergebnis der Runde in Prozent des Einsatzes
        - die Bewegung desselben Instruments ueber dieselbe Zeit (BUY & HOLD
          aus den gespeicherten Kerzen) - das ist die Basislinie
        - die EXCESS-Rendite: Rundenergebnis minus Marktbewegung
      Eine Spur hat Edge, wenn ihre Excess-Rendite im Mittel positiv ist und
      die Trefferquote ueber 50 % liegt. Beide Zahlen werden getrennt
      ausgewiesen; nennt man nur eine, ist das eine Auswertung ohne
      Gegenprobe.

BASISLINIE UND IHRE LÜCKE
--------------------------
Die Basislinie braucht Kerzen fuer jedes Instrument, das die Spur gespielt
hat. Im Haus lagen die nur fuer BTC/ETH/SOL (daten/historie/), also war eine
ehrliche Edge-Messung fuer alle anderen Spuren nicht moeglich - die Zahl
fehlte schlicht, und wer sie nicht hatte, hat sie nicht gemessen.

Dieses Werkzeug schliesst die Luecke selbst: `--historie` laedt fuer jedes
gefundene Instrument die fehlenden Kerzen nach (Binance, oeffentlich, ohne
Schluessel), und `fehlt()` benennt jedes Instrument, fuer das es keine
Binaerhistorie gibt. Ein Pump-Token ohne Binance-Paar wird NICHT durch ein
aehnliches Instrument ersetzt - das waere eine erfundene Basislinie. Er wird
als `ohne_basislinie` ausgewiesen und aus der Kennzahl genommen.

EIN ORDNER ZAEHLT NICHT ALS BEGRUENDUNG
----------------------------------------
Ein Instrument ohne Historie ist kein Befund gegen die Spur, sondern eine Luecke
in der Messung. Beide Faelle stehen getrennt in der Ausgabe, damit eine
gemessene Spur nicht mit einer unmessbaren verwechselt wird.

AUFruf (aus dem Handel-Ordner, damit die Pfade passen):
    scanner/.venv/Scripts/python.exe spur_audit.py                     # alle Spuren
    scanner/.venv/Scripts/python.exe spur_audit.py --spur scanner      # eine Spur
    scanner/.venv/Scripts/python.exe spur_audit.py --nur-befund        # nur die Alarme
    scanner/.venv/Scripts/python.exe spur_audit.py --json              # fuer Wachen
    scanner/.venv/Scripts/python.exe spur_audit.py --historie          # Kerzen nachladen
    scanner/.venv/Scripts/python.exe spur_audit.py --min-runden 20     # Schwelle

Liest nur. Schreibt nichts - `--historie` legt Kerzen unter daten/historie/
ab, das ist der einzige Schreibzugriff, und er ist reproduzierbar.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import auswertung_alle                     # noqa: E402  (die EINE Auswertung)
import historie_binance                    # noqa: E402
import journalpaarung                      # noqa: E402

# Der Takt des Aufrufers ist die Eine Zahl, gegen die die Haltedauer geprueft
# wird. Sie steht in `dauerlauf.TAKT_MAX_MINUTEN` - von dort lesen, nicht
# hierhinpflegen: eine eigene Zahl hier waere eine Behauptung.
try:
    import dauerlauf
    TAKT_MINUTEN = int(getattr(dauerlauf, "TAKT_MAX_MINUTEN", 15))
except Exception:                          # noqa: BLE001
    TAKT_MINUTEN = 15

MIN_RUNDE_PROBE = 1.0     # eine Runde unter 1 h ist primaer als Takt zu lesen
STREU_ANTEIL = 0.5        # ein Instrument ueber 50 % der Runden = Befund
PREIS_ANTEIL = 0.5        # mehr als die Haelfte der Mehrfachkoeufe gleich = Befund
# Nur Gruppen der letzten N Tage alarmeren (Anlass 10.10.2026: der Scanner-
# Alarm wertete Altbestand aus der Fehlerzeit - ein behobener Fehler
# alarmierte weiter. Ein aktueller Fehler hat frische Gruppen.) Das Fenster
# misst die AKTUALITAET des Fehlers, nicht die Historie: liegt der letzte
# identische Preis mehr als 14 Tage zurueck, verzerrt er die heutige
# Statistik nicht mehr (der Scanner-Fix kam am 03.10., der letzte
# Fehlvorfall am 21.09.).
PREIS_FENSTER_TAGE = 14
# Wenn mehr als dieser Anteil der Runden aelter als PREIS_FENSTER_TAGE ist,
# spricht die Statistik ueber Altbestand, nicht ueber die heutige Spur.
ALT_ANTEIL = 0.8


# ---------------------------------------------------------------- Spur holen

def spurordner():
    """Die Spuren, die der Dauerlauf tatsaechlich faehrt - aus SPUREN lesen."""
    try:
        return sorted(set(d for d, _ in _spuren_mit_ordner()))
    except Exception:                      # noqa: BLE001
        return sorted(d for d in os.listdir(HIER)
                      if os.path.isfile(os.path.join(HIER, d, "handeln.py")))


def _spuren_mit_ordner():
    for eintrag in dauerlauf.SPUREN.values():
        ordner = eintrag[0] if isinstance(eintrag, (list, tuple)) else eintrag
        if os.path.isfile(os.path.join(HIER, ordner, "handeln.py")):
            yield ordner, eintrag


def journalpfad(spur, datei="handelsjournal.csv"):
    """Das Journal einer Spur - ohne Sicherung, Verworfenes und Altstaende.

    Eine Sicherung (`handelsjournal.bak-20261002.csv`) und ein verworfenes
    Journal (`handelsjournal.verworfen-JJJJMMTT.csv`) sind KEINE Ergebnisdatei;
    mitzuzaehlen waere eine Auswertung ueber Daten, die die Spur selbst nicht
    mehr benutzt. Die Stufen-Buecher (`.mittel`, `.hoch`) gehoeren zu den
    Risikostufen und werden NICHT zur Basis gezaehlt.
    """
    p = os.path.join(HIER, spur, datei)
    if os.path.isfile(p):
        return p
    return None


def zeilen(spur):
    """Das Basis-Journal als dicts (leer, wenn keins da ist)."""
    p = journalpfad(spur)
    if not p:
        return []
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _zeit(zeile):
    try:
        return datetime.fromisoformat((zeile.get("zeit") or "").strip())
    except (ValueError, TypeError):
        return None


# ------------------------------------------------------ FRAGE 1: echt oder nicht

# Ein Instrument kommt in den Journalen in drei Schreibweisen vor:
#   BTC-USDT            (OKX Spot)        BTC-USD_UM_XPERP-310502  (OKX Kontrakt)
#   BTC-USDT-SWAP       (OKX Perpetual)   BTC/EUR                 (Kraken)
# fuer die Historie aber ist es EIN Basiswert. Ohne diese Reduktion beant-
# wortet die Basislinie die Frage nicht ("kein Binance-Paar fuer
# 'HBAR-USD_UM_XPERP-310815'"), obwohl HBAR ein gewoehnliches Paar ist -
# gemessen haben die Spuren 110 verschiedene Namen fuer 66 Basiswerte, und
# ohne Normalisierung war fuer 47 davon keine Basislinie moeglich.
_KONTRAKT = re.compile(r"-USD_UM_(XPERP|FUTURES|SWAP)(-\d+)?$")
_SWAP = re.compile(r"-(USDT|USDC|BTC|ETH)?_?SUM?-?SWAP$")
_QUOTE = re.compile(r"-(USDT|USDC|FDUSD|USD|EUR|GBP|BTC|ETH)$")


# Kraken fuehrt Krypto mit einem X im Namen und BTC/ETH mit doppeltem X
# (XXBTZEUR, XETHZEUR), Aktien ohne X (SOLEUR, ADAEUR). Eine Regel "fuehrendes
# X abschneiden" loest XXBT nicht auf - sie macht daraus XBT und wieder nur
# XBT, wenn man sie zweimal anwendet. Deshalb die PAARE-Tabelle: gemessen an
# den 33 Kraken-Paarnamen im Journal, jeder einzeln.
_KRAKEN = {
    "XXBT": "BTC", "XBT": "BTC", "XETH": "ETH", "ETH": "ETH",
    "XXLM": "XLM", "XLTC": "LTC", "XXRP": "XRP", "XXDG": "DOGE",
    "XTZ": "XTZ", "ZEUR": "ZEUR", "ZEZ": "ZEC", "XETC": "ETC",
}


def basisform(inst):
    """Der Basiswert eines Journal-Instruments, oder None wenn keiner ist.

    None ist ein echter Fall und kein Rechenfehler: eine Solana-Adresse
    (0x...) oder ein Platzhalter ('?') hat keinen Basiswert, weil es gar kein
    benanntes Instrument ist. Fuer diese Faelle wird KEIN Ersatz gesucht -
    eine Basislinie aus einem anderen Markt waere erfunden.
    """
    n = (inst or "").strip().upper()
    if not n or n == "?" or n.startswith("0X"):
        return None
    n = _KONTRAKT.sub("", n)
    n = _SWAP.sub("", n)
    n = _QUOTE.sub("", n)
    n = n.replace("/", "-").replace("_", "-")
    # Kraken-Paarnamen stehen OHNE Trenner: SOLEUR, ADAEUR, XXBTZEUR,
    # XLTCZEUR. Die Quote ist immer die LETZTE Vierbuchstabengruppe, und
    # das fuehrende X gehoert zum Basiswert (XBT/XETH sind Krakens
    # Schreibweisen fuer BTC/ETH) - `lstrip("X")` waere falsch, weil es auch
    # die Xs des Basiswerts frisst (XXBTZEUR -> BTZ statt BTC).
    #
    # Der Test laeuft NUR, wenn in der Kette kein Bindestrich steht: ein
    # OKX-Kontrakt wie `HBAR-USD_UM_XPERP-310815` ist davon nach den
    # bisherigen Abzuegen uebrig, und eine Regex auf "irgendwelche vier
    # Endbuchstaben" wuerde ihn zu "H" zerschneiden.
    if "-" not in n and len(n) > 4:
        # NUR eine echte Quote wird abgenommen. Ein pauschales `[:-3]` zerlegt
        # jeden Namen, der nicht mit EUR endet: CASHCAT -> CASH, META -> MA,
        # RENDER -> REN, UNITREE -> UNITR. Das ist derselbe Fehler eine
        # Ebene hoeher - eine Regel, die auf einen Fall passt und alle
        # anderen zerschneidet.
        for quote, kurz in (("USDC", 4), ("USDT", 4), ("USD", 3), ("EUR", 3)):
            if n.endswith(quote):
                basiswert = n[:-len(quote)]
                # Kraken haengt ein Z an die Fiat-Quote (XBTZUSD, XXBTZEUR)
                if basiswert.endswith("Z") and basiswert[:-1] in _KRAKEN:
                    basiswert = basiswert[:-1]
                return _KRAKEN.get(basiswert, basiswert) or None
    return n.split("-")[0] or None


def instrument_index(inst, takt="1H"):
    """Kerzenindex fuer ein Journal-Instrument - ueber den Basiswert.

    Der Index wird je (Basiswert, Takt) GEACHT, nicht je Aufruf neu gebaut:
    ein Audit ueber 46 Spuren mit je 30 Runden wuerde sonst dieselbe Reihe
    hundertfach aus der Platte lesen.
    """
    b = basisform(inst)
    if b is None:
        return {}
    schluessel = (b, takt)
    if schluessel in _INDEX_CACHE:
        return _INDEX_CACHE[schluessel]
    try:
        reihe = historie_binance.lade(b, takt)
    except KeyError:
        reihe = []
    except historie_binance.HistorieKaputt as e:
        # 05.10.2026: die Datei ist da, aber unlesbar (im Betrieb ein Moment,
        # in dem gerade geschrieben wird). Frueher gab `lade()` still [] zurueck
        # und der Audit rechnete mit leeren Kerzen - das ist die Basislinie,
        # also wurde ein Instrument als "keine Marktbewegung" gewertet und die
        # Spur als messbar ausgewiesen. Jetzt: Luecke melden, nicht raten.
        KAPUTTE_DATEIEN.add(str(e).split(" ist keine")[0])
        reihe = []
    idx = {int(r[0]): r for r in reihe}
    _INDEX_CACHE[schluessel] = idx
    return idx


_INDEX_CACHE = {}
KAPUTTE_DATEIEN = set()          # Instrument -> Meldung im Fuss des Berichts


def halte_dauer(ein, aus):
    """Stunden zwischen Einstieg und Ausstieg, oder None."""
    t0, t1 = _zeit(ein), _zeit(aus)
    if t0 is None or t1 is None:
        return None
    return (t1 - t0).total_seconds() / 3600.0


# Nicht jede Spur fuehrt das Instrument in `inst`. Gemessen 03.10.2026:
# `kraken` schreibt `paar` (ADAEUR, ALGOEUR, ...), `nautilus` fuehrt zusaetzlich
# `symbol` (KOP:JUDE, KOP:Jimothee) und `token`. Ein Audit, das blind `inst`
# liest, sieht dort eine LEERE Spalte und meldet "alle Runden auf EIN
# Instrument" - ein Befund aus dem Nichts, weil es kein Instrument gibt.
# Die Reihenfolge ist eine Rangfolge: das Feld, das wirklich besetzt ist,
# gewinnt. Deshalb wird hier NICHT blind ersetzt, sondern gemessen und der
# Befund beim Fehlen des Feldes gar nicht erst erzeugt.
INST_SPALTEN = ("inst", "paar", "symbol", "token", "kontrakt", "asset")


def instanzfeld(zeile):
    """Das Instrument einer Journalzeile, ueber die besetzte Spalte.

    Liefert (name, wert). `name` ist None, wenn die Zeile kein Instrument
    traegt - dann darf der Streuungs-Alarm nicht feuern, weil er sonst eine
    LEERE Spalte als Konzentration auf ein Instrument liest.
    """
    for name in INST_SPALTEN:
        wert = (zeile.get(name) or "").strip()
        if wert:
            return name, wert
    return None, ""


def preis(ein):
    try:
        return float(ein.get("preis") or "")
    except (ValueError, TypeError):
        return None


def score_von(zeile):
    """Der Score aus der Grund-Spalte ('score 64.7'), sonst None.

    Der Wert steht im Token DANACH, nicht im Token selbst: die Spalte laesst
    `score 64.7` schreiben, nicht `score=64.7`. Ein Test, der nur auf das
    Trennzeichen `=`/`:` prueft, liest deshalb NIE einen Score - und die
    Umkehrung des Scores (T-322: 60-69 war besser als 80+) bleibt dann
    ungeprueft. Beide Formen werden gelesen, weil ein fremder Schreiber auch
    die zweite schreiben kann.
    """
    teile = (zeile.get("grund") or "").replace(";", " ").replace(",", " ").split()
    for i, teil in enumerate(teile):
        if teil.lower().startswith("score"):
            rest = teil[5:].lstrip(":=")
            if not rest and i + 1 < len(teile):
                rest = teile[i + 1]
            try:
                return float(rest)
            except ValueError:
                return None
    return None


def alarm_preis(runden, fenster_tage=PREIS_FENSTER_TAGE):
    """SCHEIN-Preis: gleicher Einstiegspreis je (Instrument, Tag).

    Geprueft wird NUR, wo dieselbe Position an einem Tag mehrfach eroeffnet
    wurde - zwischen zwei Tagen kann der Preis gleich sein (Wochenende, illiquider
    Markt), an einem Tag zweimal nicht. Der Anteil ist der Anteil der
    (Instrument, Tag)-Gruppen, in denen JEDER Kauf denselben Preis trug.

    Zeitfenster (PREIS_FENSTER_TAGE, Standard 30): Nur Gruppen zaehlen,
    deren Einstieg innerhalb der letzten N Tage liegt. Anlass 10.10.2026:
    der Scanner-Alarm wertete den Altbestand aus der Fehlerzeit (letzter
    identischer Preis 21.09., Fix 03.10. via marktkurs()) - ein behobener
    Fehler alarmierte weiter. Ein HEUTIGER Fehler schlaegt dagegen sofort
    wieder an, weil seine Gruppen frisch sind.
    """
    grenze = datetime.now(timezone.utc) - timedelta(days=int(fenster_tage or 0))
    gruppen = defaultdict(list)
    for ein, _aus in runden:
        z = _zeit(ein)
        p = preis(ein)
        _f, inst = instanzfeld(ein)
        if z is None or p is None or not inst:
            continue
        if fenster_tage and z < grenze:
            continue
        gruppen[(inst, z.date())].append(p)
    mehrfach = [v for v in gruppen.values() if len(v) >= 2]
    if not mehrfach:
        return {"gruppen": 0, "gleich": 0, "anteil": 0.0, "beispiel": None}
    gleich = sum(1 for v in mehrfach if len(set(v)) == 1)
    # Das Beispiel kommt aus der ERSTEN Mehrfachgruppe - nicht aus der
    # Schleifenvariablen nach der Liste (die existiert dort nicht mehr).
    beispiel = sorted(mehrfach[0])[0]
    return {"gruppen": len(mehrfach), "gleich": gleich,
            "anteil": gleich / len(mehrfach), "beispiel": beispiel}


def alarm_streuung(runden):
    """EINER-Anteil: groesster Instrument-Anteil an den Runden.

    Ohne belegtes Instrument-Feld kommt KEIN Befund zurueck. Ein leeres Feld
    ist keine Konzentration auf ein Instrument, sondern eine unbekannte
    Spalte - und ein Befund aus dem Nichts ist schlimmer als keiner.
    """
    zaehler = Counter()
    ohne_feld = 0
    for ein, _ in runden:
        _name, wert = instanzfeld(ein)
        if not wert:
            ohne_feld += 1
            continue
        zaehler[wert] += 1
    if not zaehler:
        return {"anteil": 0.0, "inst": None, "n": 0,
                "ohne_feld": len(runden), "messbar": False}
    inst, n = zaehler.most_common(1)[0]
    # `zaehler.total()` zaehlt die Eintraege, nicht die Zeilen - und der
    # Counter traegt hier (Feldname, Wert)-Tupel, also waere es doppelt.
    # Die Zahl der GEMESSENEN Zeilen ist die Summe der Werte.
    gemessen = sum(zaehler.values())
    return {"anteil": n / gemessen, "inst": inst, "n": n,
            "ohne_feld": ohne_feld, "gemessen": gemessen,
            "messbar": gemessen >= 3 and ohne_feld <= len(runden) // 4}


def alarm_takt(runden):
    """SCHEIN-Takt: Haltedauer im Rhythmus des Aufrufers."""
    d = [h for h in (halte_dauer(e, a) for e, a in runden) if h is not None]
    if not d:
        return {"n": 0, "median": None, "unter_takt": 0, "takt_h": TAKT_MINUTEN / 60.0}
    d.sort()
    median = d[len(d) // 2]
    grenze = 2.0 * TAKT_MINUTEN / 60.0
    return {"n": len(d), "median": median,
            "unter_1h": sum(1 for x in d if x < MIN_RUNDE_PROBE),
            "unter_takt": sum(1 for x in d if x < grenze),
            "takt_h": TAKT_MINUTEN / 60.0,
            "scheint": median < grenze}


# ---------------------------------------------------- FRAGE 2: Edge gegen Markt

def markt_im_fenster(index, t0, t1, seite="long"):
    """Marktbewegung in Prozent zwischen zwei Zeitpunkten (BUY & HOLD).

    Nimmt den Schluss der Kerze VOR t0 als Einstieg und den Schluss der
    Kerze VOR t1 als Ausstieg - dieselbe Konvention wie der Backtest
    (`replay` steigt zum Schluss der Kerze auf). Fehlt eine der beiden
    Kerzen, kommt None zurueck: ein geraeteter Markt waere eine erfundene
    Basislinie.
    """
    if not index:
        return None
    ms0 = t0.timestamp() * 1000
    ms1 = t1.timestamp() * 1000
    # Einstieg: die LETZTE Kerze, die VOR t0 geschlossen ist. Ausstieg: die
    # LETZTE Kerze, die im Fenster liegt - und es MUSS eine nach t0 sein,
    # sonst waeren beide Stempel dieselbe Kerze und die Basislinie waere 0,0
    # (gemessen: genau das, 20 von 20 Runden bekamen 0,00 % "Marktbewegung").
    vor0 = [t for t in index if t < ms0]
    im0 = [t for t in index if ms0 <= t <= ms1]
    if not vor0 or not im0:
        return None
    a = index[max(vor0)][4]
    b = index[max(im0)][4]
    if not a or not b or a <= 0:
        return None
    roh = (b / a - 1.0) * 100.0
    return roh if seite == "long" else -roh


def basislinie_moeglich(inst, takt="1H"):
    """Hat dieses Instrument ueberhaupt eine gespeicherte Kerzereihe?"""
    return bool(instrument_index(inst, takt))


def edge(runden, takt="1H", ohne_basislinie_sammeln=True):
    """Rundenergebnis gegen Marktbewegung im selben Fenster.

    Liefert die Aggregate MIT und OHNE die Baseline, damit die Rohzahl nie
    allein dasteht: eine Spur, die nur deshalb gut aussieht, weil der Markt
    in their Richtung lief, ist daran erkennbar, dass die Excess-Rendite
    gegen 0 geht.
    """
    verfuegbar = []
    fehlt = Counter()
    for ein, aus in runden:
        t0, t1 = _zeit(ein), _zeit(aus)
        ergebnis = _ergebnis_pct(ein, aus)
        if t0 is None or t1 is None or ergebnis is None:
            continue
        _f, inst = instanzfeld(ein)
        index = instrument_index(inst, takt)
        markt = markt_im_fenster(index, t0, t1, (ein.get("seite") or "long").strip())
        if markt is None:
            fehlt[inst or "?"] += 1
            if ohne_basislinie_sammeln:
                continue
        verfuegbar.append({"ergebnis": ergebnis, "markt": markt, "inst": inst,
                           "halt": halte_dauer(ein, aus)})
    return verfuegbar, fehlt


def _ergebnis_pct(ein, aus):
    """Rundenergebnis in Prozent des Einsatzes - OHNE Gebuehr.

    Die Gebuehr gehoert in eine eigene Zeile der Bewertung; sie ist hier
    ausgeschlossen, damit die Edge-Zahl die Strategie beschreibt und nicht
    die Kostenkonfiguration. Gebuehr zusaetzlich: `auswertung_alle` rechnet
    sie, sobald die Kennzahl ausgewiesen wird.
    """
    p0 = preis(ein)
    p1 = preis(aus)
    if not p0 or p1 is None:
        return None
    seite = (ein.get("seite") or "long").strip().lower()
    if seite in ("short", "sell"):
        return (p0 / p1 - 1.0) * 100.0
    return (p1 / p0 - 1.0) * 100.0


def mittel(xs):
    return sum(xs) / len(xs) if xs else None


def stdabw(xs):
    """Stichproben-Standardabweichung (n-1) oder None bei weniger als 2 Werten."""
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def halbierung(excess):
    """Frueh/Spaet-Hälften der Excess-Liste (in Journalreihenfolge).

    Liefert Mittel und Anzahl je Haelfte; bei weniger als 2 Werten leere Felder.
    Die Reihenfolge der Journalpaarung ist chronologisch nach Schliessung, weil
    das Journal angehaengt wird.
    """
    n = len(excess)
    if n < 2:
        return {"n_frueh": 0, "n_spaet": 0,
                "mean_excess_frueh": None, "mean_excess_spaet": None}
    h = n // 2
    return {"n_frueh": h, "n_spaet": n - h,
            "mean_excess_frueh": mittel(excess[:h]),
            "mean_excess_spaet": mittel(excess[h:])}


def median(xs):
    if not xs:
        return None
    s = sorted(xs)
    return s[len(s) // 2]


def kennzahlen_ohne_markt(runden):
    """Rohkennzahlen: Ergebnis, Trefferquote, Median - ohne Baseline."""
    xs = [_ergebnis_pct(e, a) for e, a in runden]
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"n": len(xs), "mean": mittel(xs), "median": median(xs),
            "treffer": sum(1 for x in xs if x > 0) / len(xs)}


def score_baender(runden):
    """Ergebnis je Score-Band - die Umkehrung des Scores ist ein Alarm.

    Ein Signal, das mit hoeherer Ueberzeugung schlechter wird, ist keines:
    gemessen am Scanner 60-69: +18,78 %, 80+: -0,46 %.
    """
    baender = defaultdict(list)
    for ein, aus in runden:
        s = score_von(ein)
        x = _ergebnis_pct(ein, aus)
        if s is None or x is None:
            continue
        baender["60-69" if s < 70 else ("70-79" if s < 80 else "80+")].append(x)
    return {k: {"n": len(v), "mean": mittel(v)} for k, v in sorted(baender.items())}


# ------------------------------------------------------------------ Die Spur

def verzerrung(markt_paare):
    """Zwei Gruppen getrennt ausweisen - und die Verzerrung BENENNEN.

    ANLASS: 03.10.2026, eigener Befund am selben Werkzeug. Die Baseline-
    Abfrage braucht eine Kerze IM Zeitfenster der Runde. Eine Runde, die
    nach 15 Minuten endet, hat oft keine - und genau diese Runden sind die
    Scheinrunden. Ohne diese Aufteilung meldete das Werkzeug den Scanner mit
    +11,93 % Excess, weil es NUR die 40 sauberen Runden gemessen und die 121
    Scheinrunden stillschweigend weggelassen hatte.

    Das ist dieselbe Verzerrung wie in T-322, nur eine Ebene tiefer: dort
    war der Einstiegspreis falsch, hier die AUSWAHL. Eine Kennzahl, die nur
    die gemessenen Runden nennt, ohne die ungemessenen zu beziffern, ist
    schlimmer als keine - sie sieht sauber aus.

    Deshalb: Excess ueber alle Runden UND getrennt nach Haltedauer, plus die
    Zahl der Runden ohne Basislinie. Weicht die kurze Gruppe stark von der
    langen ab, ist das ein Befund, keine Rundenzahl.
    """
    mit = [r for r in markt_paare if r.get("markt") is not None]
    kurz = [r for r in mit if r.get("halt") is not None and r["halt"] < 1.0]
    lang = [r for r in mit if r.get("halt") is not None and r["halt"] >= 1.0]

    def _ex(group):
        v = [r["ergebnis"] - r["markt"] for r in group]
        return {"n": len(group), "excess": mittel(v), "mean": mittel([r["ergebnis"] for r in group]),
                "markt": mittel([r["markt"] for r in group])}

    kurz_erg, lang_erg = _ex(kurz), _ex(lang)
    abweichung = None
    if kurz_erg["excess"] is not None and lang_erg["excess"] is not None:
        abweichung = kurz_erg["excess"] - lang_erg["excess"]
    return {"kurz": kurz_erg, "lang": lang_erg, "abweichung": abweichung}


def pruefe(spur, takt="1H"):
    """Das vollstaendige Audit EINER Spur."""
    z = zeilen(spur)
    if not z:
        return {"spur": spur, "n": 0, "grund": "kein Journal"}

    # Die Zuordnung kommt aus `journalpaarung` - dieselbe, die
    # `kosten_wendepunkt` und `auswertung_alle` benutzen. Eine eigene
    # Warteschlange je Instrument waere eine zweite Wahrheit.
    p = journalpaarung.Paarung(einstieg_ok=lambda r: bool(r.get("preis")))
    paare = p.zuordnen(z)

    roh = kennzahlen_ohne_markt(paare)
    markt_paare, fehlt = edge(paare, takt)
    excess = [r["ergebnis"] - r["markt"] for r in markt_paare
              if r["markt"] is not None]

    a_takt = alarm_takt(paare)
    a_streu = alarm_streuung(paare)
    a_preis = alarm_preis(paare)
    verz = verzerrung(markt_paare)

    # Datenabdeckung: wie viel der Statistik spricht ueber die HEUTIGE Spur?
    # Anlass 10.10.2026: 182 von 190 Scanner-Kaeufen stammten aus der Zeit
    # vor dem Preis-Fix (03.10.) - die Statistik (+7,48 % Excess) beschrieb
    # Altbestand, nicht den heutigen Code. Die beiden Zahlen machen das
    # sichtbar, und der Befund darunter sagt es aus.
    grenze = datetime.now(timezone.utc) - timedelta(days=PREIS_FENSTER_TAGE)
    n_neu = n_alt = 0
    for ein, _aus in paare:
        z = _zeit(ein)
        if z is None:
            continue
        if z >= grenze:
            n_neu += 1
        else:
            n_alt += 1

    befunde = []
    if n_alt and n_neu == 0:
        befunde.append("Statistik ist ALT (alle %d Runden aelter als %d Tage) - "
                       "misst die Vergangenheit, nicht die heutige Spur"
                       % (n_alt, PREIS_FENSTER_TAGE))
    elif n_alt and n_neu and n_alt / (n_alt + n_neu) > ALT_ANTEIL:
        befunde.append("Statistik ueberwiegend ALT (%d von %d Runden aelter als "
                       "%d Tage, Anteil > %d%%)" % (
                           n_alt, n_alt + n_neu, PREIS_FENSTER_TAGE,
                           int(ALT_ANTEIL * 100)))
    if a_takt.get("scheint"):
        befunde.append("Haltedauer im Aufrufertakt (Median %.2f h bei %.2f h Takt)"
                       % (a_takt["median"], a_takt["takt_h"]))
    if (a_streu.get("messbar") and a_streu["anteil"] > STREU_ANTEIL
            and a_streu["n"] >= 5):
        befunde.append("%d von %d Runden auf EIN Instrument (%s)"
                       % (a_streu["n"], len(paare), a_streu["inst"]))
    if a_preis["anteil"] > PREIS_ANTEIL and a_preis["gruppen"] >= 2:
        befunde.append("Einstiegspreis je (Instrument, Tag) IDENTISCH "
                       "(%d von %d Gruppen) - Preis uebernommen statt geholt"
                       % (a_preis["gleich"], a_preis["gruppen"]))
    # Die Auswahl-Verzerrung: wenn die kurzen Runden einen voellig anderen
    # Excess haben als die langen, dann misst die Gesamtzahl nicht die Spur,
    # sondern die Auswahl. Das ist der eigene Befund vom 03.10.2026.
    if (verz["abweichung"] is not None
            and verz["kurz"]["n"] >= 5 and verz["lang"]["n"] >= 5
            and abs(verz["abweichung"]) > 5.0):
        befunde.append("Excess der Runden < 1 h weicht um %+.1f pp vom "
                       "Excess der Runden >= 1 h ab (%+.1f %% gegen %+.1f %%) "
                       "- die Gesamtzahl misst die Auswahl, nicht die Spur"
                       % (verz["abweichung"], verz["kurz"]["excess"],
                          verz["lang"]["excess"]))

    return {
        "spur": spur,
        "n": len(paare),
        "n_neu": n_neu,
        "n_alt": n_alt,
        "roh": roh,
        "basislinie_n": len([r for r in markt_paare if r["markt"] is not None]),
        # `fehlt` zaehlt je INSTRUMENT, nicht je Runde - ohne diese Umrechnung
        # waere die Kennzahl "Runden ohne Basislinie" kleiner als die Zahl der
        # betroffenen Instrumente und damit schon falsch.
        "ohne_basislinie": len([r for r in markt_paare if r["markt"] is None]),
        "fehlende_inst": sorted(fehlt),
        "mean_excess": mittel(excess),
        "std_excess": stdabw(excess),
        # Halbierung nach Journalreihenfolge (= Schliessungsreihenfolge): wer
        # nur in einer Haelfte Edge hat, hat sie vermutlich nicht.
        **halbierung(excess),
        "median_excess": median(excess),
        "n_excess": len(excess),
        "verzerrung": verz,
        "score_baender": score_baender(paare),
        "paarung": p.stand(),
        "alarme": {
            "takt": a_takt,
            "streuung": a_streu,
            "preis": a_preis,
        },
        "befunde": befunde,
    }


# ------------------------------------------------------------------- Ausgabe

def _fmt(x, stellen=2, prozent=False):
    if x is None:
        return "-"
    s = ("%." + str(stellen) + "f") % x
    return s + (" %" if prozent else "")


def text(ergebnisse, min_runden=8):
    zeilen_ = []
    zeilen_.append("Spur-Audit - Edge und Echtheit, alle Spuren in einem Lauf")
    zeilen_.append("Aufrufertakt %.0f min. Base line: BUY & HOLD desselben "
                   "Instruments aus den gespeicherten Kerzen." % TAKT_MINUTEN)
    zeilen_.append("")
    zeilen_.append("%-22s %4s %5s %8s %8s %9s %9s %7s %7s %s"
                   % ("spur", "n", "nNeu", "mean%", "treff%", "excess%",
                      "nBasis", "<1h", ">=1h", "Befund"))
    zeilen_.append("-" * 122)
    for e in ergebnisse:
        if e["n"] == 0:
            zeilen_.append("%-22s %4s  %s" % (e["spur"], "-", e.get("grund", "")))
            continue
        roh = e["roh"] or {}
        zu_klein = " (unter Schwelle)" if e["n"] < min_runden else ""
        v = e.get("verzerrung") or {}
        kurz_e = (v.get("kurz") or {}).get("excess")
        lang_e = (v.get("lang") or {}).get("excess")
        zeilen_.append("%-22s %4d %5d %8s %7.0f%% %9s %9d %7s %7s %s%s"
                       % (e["spur"], e["n"], e.get("n_neu") or 0,
                          _fmt(roh.get("mean"), prozent=True),
                          100 * (roh.get("treffer") or 0),
                          _fmt(e.get("mean_excess"), prozent=True),
                          e["basislinie_n"],
                          _fmt(kurz_e), _fmt(lang_e),
                          ("; ".join(e["befunde"]) if e["befunde"] else "ohne Befund"),
                          zu_klein))
    zeilen_.append("")
    zeilen_.append("Lesehilfe:")
    zeilen_.append("  nNeu      Runden mit Einstieg in den letzten %d Tagen -"
                   % PREIS_FENSTER_TAGE)
    zeilen_.append("            darunter leidet die Statistik, wenn sie ALT ist")
    zeilen_.append("  mean%     Rundenergebnis ohne Basislinie (brutto, ohne Gebuehr)")
    zeilen_.append("  treff%    Anteil der Runden mit Gewinn - allein KEIN Edge")
    zeilen_.append("  excess%   Rundenergebnis minus Marktbewegung im selben Fenster")
    zeilen_.append("  nBasis    Runden mit Basislinie; `ohne Basislinie` = Luecke, kein Befund")
    zeilen_.append("  <1h/>=1h Excess GETRENNT nach Runden, die unter bzw. ueber einer Stunde")
    zeilen_.append("            lagen. Weichen die Spalten stark ab, misst `excess%` nicht")
    zeilen_.append("            die Spur, sondern die Auswahl - das ist der Befund, nicht die Zahl.")
    zeilen_.append("")
    zeilen_.append("Bedeutung des Excess: ")
    for name, bedeutung in (
            ("positiv", "die Spur verdient mehr, als das Instrument getragen haette"),
            ("nahe 0", "die Spur ist die Marktbewegung selbst - sie hat keinen eigenen Vorteil"),
            ("negativ", "die Spur ist schlechter als das Instrument - Runden weglassen")):
        zeilen_.append("  %-9s %s" % (name, bedeutung))
    return "\n".join(zeilen_)


def nur_befund(ergebnisse):
    return [e for e in ergebnisse if e.get("befunde")]


# ---------------------------------------------------------- Historie nachladen

def fehlende_instumente(ergebnisse):
    """Alle Instrumente, fuer die das Audit keine Basislinie hatte."""
    fehlt = set()
    for e in ergebnisse:
        fehlt.update(e.get("fehlende_inst") or [])
    return sorted(fehlt)


def historie_nachladen(inst_namen, takte=("1H",), von="2021-01-01"):
    """Fehlende Kerzen fuer die gefundenen Instrumente beschaffen.

    NurInstrumente mit einem Binance-Paar kommen durch; jedes andere wird
    BENANNT und nicht ersetzt - eine Basislinie aus einem aehnlichen
    Instrument waere eine erfundene.
    """
    von_ms = int(time.mktime(time.strptime(von, "%Y-%m-%d"))) * 1000
    bis_ms = int(time.time() * 1000)
    geladen, nicht_moeglich = [], []
    # Die Basiswerte VOR dem Nachladen einsammeln: AAVE-USDT,
    # AAVE-USD_UM_XPERP-310704 und AAVE sind derselbe Wert, und dreimal
    # dasselbe Paar zu laden waere Zeit ohne Erkenntnis.
    pro_basis = {}
    for inst in inst_namen:
        b = basisform(inst)
        if b is None:
            nicht_moeglich.append((inst, "kein Basiswert (Adresse oder Platzhalter)"))
            continue
        pro_basis.setdefault(b, []).append(inst)
    for b, namen in sorted(pro_basis.items()):
        try:
            sym = historie_binance.symbol(b)
        except KeyError:
            nicht_moeglich.append(
                ("/".join(sorted(set(namen))[:2]),
                 "kein Binance-Paar - BLEIBT LUECKE, kein Ersatz"))
            continue
        try:
            bericht = historie_binance.auffuellen([b], list(takte),
                                                  von_ms=von_ms, bis_ms=bis_ms)
        except Exception as e:                       # noqa: BLE001
            nicht_moeglich.append((b, "Abruf scheiterte: %s" % e))
            continue
        kerzen = sum(v[t]["kerzen"] for v in bericht.values() for t in v)
        geladen.append((b, sym, kerzen, len(set(namen))))
    return geladen, nicht_moeglich


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spur", default=None, help="nur diese Spur")
    ap.add_argument("--nur-befund", action="store_true")
    ap.add_argument("--json", action="store_true", dest="als_json")
    ap.add_argument("--historie", action="store_true",
                    help="fehlende Kerzen nachladen, dann neu messen")
    ap.add_argument("--takt", default="1H", choices=sorted(historie_binance.TAKTE))
    ap.add_argument("--min-runden", type=int, default=8)
    a = ap.parse_args()

    spuren = [a.spur] if a.spur else spurordner()
    ergebnisse = [pruefe(s, a.takt) for s in spuren]

    if a.historie:
        fehlt = fehlende_instumente(ergebnisse)
        print("lade Historie fuer %d Instrument(e) nach ..." % len(fehlt))
        geladen, nicht_moeglich = historie_nachladen(fehlt, (a.takt,))
        for b, sym, kerzen, n_namen in geladen:
            print("  %-12s -> %-14s %6d Kerzen  (%d Journalname(n))"
                  % (b, sym, kerzen, n_namen))
        for inst, grund in nicht_moeglich:
            print("  %-16s -> %s (BLEIBT LÜCKE, kein Ersatz)" % (inst, grund))
        print()
        ergebnisse = [pruefe(s, a.takt) for s in spuren]

    if a.als_json:
        print(json.dumps(ergebnisse, indent=2, ensure_ascii=False, default=str))
        return
    if a.nur_befund:
        befunde = nur_befund(ergebnisse)
        if not befunde:
            print("keine Spur mit Befund")
            return
        print(text(befunde, a.min_runden))
        return
    print(text(ergebnisse, a.min_runden))


if __name__ == "__main__":
    main()