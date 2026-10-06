"""Historische OKX-FUTURES-Kerzen (XPERP) fuer den Backtest (replay.py).

Schwesterdatei zu historie_binance.py, aber fuer die XPERP-Kontrakte, die
xperp handelt (instType=FUTURES, ruleType=xperp). Die Unterschiede, die
zaehlen:

  - Ein XPERP-instId traegt ein Ablaufdatum und heisst z.B.
    "RE-USD_UM_XPERP-310620" (2031). Eine Spur nennt den BASISWERT ("RE")
    oder den vollen instId; `instid()` loest beide auf. Gespeichert wird
    unter dem VOLLEN instId - zwei Kontrakte desselben Basiswerts sind zwei
    Reihen, ein Rollover (OKX legt den Kontrakt neu auf, okxf.py
    letzter_kurs_mit_fallback) darf die alte Reihe nicht ueberschreiben.
  - Die Quelle ist /api/v5/market/history-candles (100 je Abruf, blaettert
    mit `after` rueckwaerts), nicht die Binance-klines. XPERP-Kontrakte
    laufen erst seit Mai 2026 - weiter zurueck gibt es keine Kerzen, das
    ist eine Datengrenze, kein Fehler.
  - Der Abruf geht ueber okxf.py (Drosselungs- und Transportbehandlung der
    Spur, samt okx_takt-Bremse). Der Loader hat eine eigene Naht fuer
    Tests, damit kein Test das echte OKX beruehrt.

Format: daten/historie_okx/<instId>_<takt>.json, Reihen [ts_ms, o, h, l, c,
v], aufsteigend, ts als int und die fuenf Werte als float - GENAU die Form,
die scanner/okx.kerzen() und okxf.kerzen() liefern und die replay.lade_reihen
erwartet. Ein `kerzenquelle: okx` im Bericht unterscheidet die Reihen von den
Binance-Kerzen der uebrigen Spuren.

wachen.json-Struktur: xperp traegt KEIN `instrumente`-Feld, sondern
`familien` (krypto/aktie/rohstoff) mit je instCategory und `aktiv`.
`instrumente_fuer(w)` liest beides: ein `instrumente`-Feld (Liste, Dict oder
Komma-String, wie replay._instrumente) ODER die aktiven Familien und loest
sie ueber okxf.instrumente(kat) in die vollen instIds auf. Damit kann der
Replay (Familie E) die Instrumente aus derselben wachen.json ableiten, aus
der die Spur live schoepft - keine zweite Liste, die auseinanderlaufen kann.

Aufruf:
    python historie_okx.py --auffuellen --instrumente RE,BTC --takte 1H,4H
    python historie_okx.py --stand
"""

import importlib.util
import json
import os
import sys
import time
import urllib.parse

HIER = os.path.dirname(os.path.abspath(__file__))
ORDNER = os.path.join(HIER, "daten", "historie_okx")

# Gleiche Abstraktion wie historie_binance.TAKTE: Hausname -> OKX-bar.
TAKTE = {"5M": "5m", "15M": "15m", "30M": "30m", "1H": "1H", "4H": "4H",
         "1D": "1D"}

# history-candles liefert hoechstens 100 Kerzen je Abruf.
GRENZE = 100
# Rate-Limit von history-candles ist eng (HTTP 429), deshalb Pause je Seite.
PAUSE_S = 0.25

# -- okxf (lazy) ------------------------------------------------------------

_OKXF = None


def _okxf():
    """okxf.py der Spur ueber den PFAD laden - sys.path bleibt unberuehrt.

    okxf importiert seinerseits okx_takt aus Agenten/Handel (ueber seinen
    eigenen _HANDEL-Pfad) - das passiert beim ersten echten Abruf, nicht
    beim Import dieses Moduls. Tests faelschen `abruf` und kommen nie hier
    an.
    """
    global _OKXF
    if _OKXF is None:
        pfad = os.path.join(HIER, "xperp", "okxf.py")
        s = importlib.util.spec_from_file_location("ho_okxf", pfad)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        _OKXF = m
    return _OKXF


class HistorieKaputt(Exception):
    """Datei da, aber kein gueltiges JSON - identisch zu historie_binance."""


# Naht fuer Tests: None -> echter OKX-Abruf ueber okxf.
abruf = None


def _seite(pfad):
    """EINE history-candles-Seite als rohe OKX-Antwort (Liste von Listen)."""
    if abruf is not None:
        return abruf(pfad)
    return _okxf()._mit_wiederholung(pfad)


# -- Namensaufloesung -------------------------------------------------------

def instid(inst):
    """Der volle OKX-instId zu einem Spur-Namen.

    - voller instId ("RE-USD_UM_XPERP-310620"): bleibt, wie er ist.
    - Basiswert ("RE" oder "REUSD"): wird ueber okxf.instrument() aufgeloest
      (der LAEBENDE Kontrakt; XPERP-Kontrakte wechseln ihren instId beim
      Rollover, okxf kennt die drei Namensformen).
    - unbekannt: KeyError mit der Liste der bekannten Namen - kein stiller
      Ersatz, ein falscher Kontrakt waere ein falscher Backtest.

    NEIN zu einer festen Tabelle hier: die XPERP-Kontraktliste aendert sich
    (OKX legt Kontrakte neu auf und ab), eine Tabelle waere beim zweiten
    Lauf schon der Stand von gestern. Die Wahrheit liegt in der API.
    """
    inst = str(inst).strip()
    if not inst:
        raise KeyError("leerer Instrumentenname")
    if inst.upper().endswith("-SWAP") or "_XPERP-" in inst.upper():
        return inst
    try:
        return _okxf().instrument(inst)["instId"]
    except Exception as e:                                    # noqa: BLE001
        raise KeyError(
            "kein OKX-XPERP-Kontrakt zu %r (Fehler: %s) - bekannte Namen "
            "nennt 'python xperp/okxf.py <basis>'" % (inst, e)) from None


def instrumente_fuer(w):
    """InstIds aus einer wachen.json - `instrumente` ODER `familien`.

    xperp-wachen haben kein `instrumente`-Feld: die Instrumente kommen aus
    den AKTIVEN Familien (krypto/aktie/rohstoff) und deren instCategory.
    `instrumente_fuer` loest genau das auf und gibt die vollen instIds
    zurueck (aufsteigend sortiert, entdoppelt) - der Replay (Familie E)
    braucht keine zweite Instrumentenliste neben der wachen.

    Ein `instrumente`/`instrument`/`paare`-Feld (Liste, Dict oder
    Komma-String) hat Vorrang - Spuren, die ihre Liste fest fuehren,
    bleiben unveraendert lesbar.
    """
    liste = None
    for name in ("instrumente", "instrument", "paare"):
        wert = w.get(name)
        if wert not in (None, "", [], {}):
            liste = wert
            break
    if isinstance(liste, str):
        liste = [x.strip() for x in liste.split(",") if x.strip()]
    if isinstance(liste, dict):
        liste = list(liste)
    if liste:
        return sorted({instid(x) for x in liste})
    familien = w.get("familien")
    if not isinstance(familien, dict):
        return []
    kategorien = [f.get("instCategory")
                  for f in familien.values()
                  if f.get("aktiv") and f.get("instCategory")]
    aus = set()
    for kat in kategorien:
        for x in _okxf().instrumente(kat):
            aus.add(x["instId"])
    return sorted(aus)


# -- Instrument-Metadaten ----------------------------------------------------
#
# Die Kerzen tragen KEINE Kontraktgroessen (ctVal/lotSz/tickSz) - die braucht
# bot.groesse() fuer die Positionsgroesse (kontrakte_aus_nominal) und auf_tick.
# Ohne sie bricht der Replay mit KeyError ab. Die Metadaten werden beim
# --auffuellen einmal mitgeschrieben (je instId das rohe OKX-Instrument-Dict)
# und liegen unter `_instrumente.json` - Netzfreiheit fuer den Replay-Ordner.

def _lade_instrumente():
    try:
        with open(os.path.join(ORDNER, "_instrumente.json"), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def alle_instrumente():
    """{instId: rohes OKX-Instrument-Dict} aus der Metadaten-Datei.

    Oeffentliche Lesung von `_lade_instrumente`: der Replay (Familie E)
    loest seine Instrumentenliste netzfrei daraus auf - dieselbe Kontrakt-
    liste, die das --auffuellen einmal mitgeschrieben hat. Fehlende Datei
    ist kein Fehler, sondern ein leeres Dict (der Aufrufer nennt dann den
    Nachlade-Befehl).
    """
    return _lade_instrumente()


def _speichere_instrumente(insts):
    """Roh-Dicts ergaenzen und atomar ablegen."""
    d = _lade_instrumente()
    for x in insts or []:
        if x and x.get("instId"):
            d[x["instId"]] = x
    os.makedirs(ORDNER, exist_ok=True)
    ziel = os.path.join(ORDNER, "_instrumente.json")
    tmp = ziel + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ziel)
    return d


def instrument_meta(iid):
    """Das rohe OKX-Instrument-Dict zu einem instId - oder KeyError mit Rat.

    Ohne ctVal/lotSz/minSz/tickSz kann der Replay weder Positionsgroessen
    noch Preise runden. Fehlt der Eintrag, ist die Aktion das Nachladen des
    KONKRETEN Instruments - kein stiller Rueckfall auf Attrappenwerte.
    """
    d = _lade_instrumente()
    eintrag = d.get(iid)
    if not eintrag:
        basis = (iid or "").split("-")[0]
        raise KeyError(
            "keine Instrument-Metadaten zu %s - erst "
            "'python historie_okx.py --auffuellen --instrumente %s' "
            "(schreibt ctVal/lotSz/tickSz nach _instrumente.json)"
            % (iid, basis or iid))
    return eintrag


# -- Speicher ---------------------------------------------------------------

def datei(inst, takt):
    if takt not in TAKTE:
        raise KeyError("unbekannter Takt %r - bekannt: %s"
                       % (takt, ", ".join(sorted(TAKTE))))
    return os.path.join(ORDNER, "%s_%s.json" % (instid(inst), takt))


def lade(inst, takt):
    """Gespeicherte Kerzen, aufsteigend. Fehlende Datei ist kein Fehler."""
    try:
        with open(datei(inst, takt), encoding="utf-8") as f:
            roh = f.read()
    except (FileNotFoundError, OSError):
        return []
    if not roh.strip():
        return []
    try:
        reihen = json.loads(roh)
    except json.JSONDecodeError:
        raise HistorieKaputt(
            "%s ist keine gueltige JSON-Datei (%d Zeichen gelesen) - "
            "entweder wird gerade geschrieben oder die Datei ist kaputt"
            % (datei(inst, takt), len(roh)))
    return sorted(reihen, key=lambda r: r[0])


def speichere(inst, takt, reihen):
    """Anhaengen, entdoppelt ueber den Zeitstempel. Gibt den Gesamtbestand.

    ATOMAR (os.replace) - ein Leser, der waehrend des Schreibens laed,
    sieht die alte komplette Datei statt einer halben (die Lehre aus
    historie_binance 05.10.2026, T-297).
    """
    bestand = {r[0]: r for r in lade(inst, takt)}
    for r in reihen:
        bestand[int(r[0])] = [int(r[0])] + [float(x) for x in r[1:6]]
    os.makedirs(ORDNER, exist_ok=True)
    ziel = datei(inst, takt)
    tmp = ziel + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump([bestand[t] for t in sorted(bestand)], f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, ziel)
    return len(bestand)


def _normalisiere(seite):
    """OKX-Rohzeilen ([ts,o,h,l,c,v,...]) -> [ts, o, h, l, c, v]."""
    return [[int(r[0])] + [float(x) for x in r[1:6]] for r in seite]


# -- Abruf ------------------------------------------------------------------

def von_okx(inst, takt, von_ms, bis_ms):
    """Kerzen des Kontrakts auf [von_ms, bis_ms], aufsteigend.

    history-candles blaettert mit `after` RUECKWAERTS: `after` ist der
    Zeitstempel, AELTERE Daten kommen zurueck. Start ist `bis_ms`, Schritt
    ist der aelteste Zeitstempel der Seite. Gestoppt wird, wenn eine Seite
    keine neuen Zeitstempel bringt (gegen eine Attrappe, die dieselbe Seite
    wiederholt, waere jede andere Bedingung eine Endlosschleife).
    """
    bar = TAKTE[takt]
    # instId EINMAL aufloesen - bei einem Basiswert-Namen ist jeder
    # instid()-Aufruf ein API-Abruf (okxf.instrument), in der Schleife
    # waere das einer je Seite.
    iid = instid(inst)
    # OKX 'after=N' ist STRENG 'aelter als N' (ts < N): um die Kerze genau
    # auf bis_ms mitzunehmen, startet die Grenze einen Millisekunde spaeter.
    reihen, grenze = [], int(bis_ms) + 1
    while True:
        w = {"instId": iid, "bar": bar, "limit": str(GRENZE)}
        if grenze is not None:
            w["after"] = str(grenze)
        pfad = "/api/v5/market/history-candles?" + urllib.parse.urlencode(w)
        seite = _seite(pfad)
        if not seite:
            break
        neu = _normalisiere(seite)
        alt = {r[0] for r in reihen}
        frisch = [r for r in neu if r[0] not in alt and int(von_ms) <= r[0] <= int(bis_ms)]
        if not frisch:
            break
        reihen += frisch
        grenze = min(r[0] for r in frisch)
        if grenze <= int(von_ms):
            break
        time.sleep(PAUSE_S)
    return sorted(reihen, key=lambda r: r[0])


# -- Bestand ----------------------------------------------------------------

def auffuellen(insts, takte, von_ms=None, bis_ms=None):
    """Kerzen nachladen und speichern. Bericht nennt je Reihe neu/gesamt.

    ohne von_ms: 2021-01-01 - fuer XPERP gleichbedeutend mit "ab Listing",
    die API liefert ohnehin nicht weiter zurueck.
    """
    von_ms = von_ms or int(time.mktime(time.strptime("2021-01-01", "%Y-%m-%d"))) * 1000
    bis_ms = bis_ms or int(time.time() * 1000)
    bericht = {}
    metas = []
    for inst in insts:
        iid = instid(inst)
        # Instrument-Metadaten einmal mitschreiben (ctVal/lotSz/tickSz fuer
        # den Replay). Fehlt der Abruf, laeuft das Auffuellen trotzdem -
        # nur der Replay beklaegt sich spaeter mit einem klaren KeyError.
        try:
            metas.append(_okxf().instrument(iid))
        except Exception as e:                                    # noqa: BLE001
            print("  Instrument-Metadaten %s nicht abrufbar (%s) - Replay "
                  "braucht sie fuer ctVal/lotSz" % (iid, e))
        for takt in takte:
            neu = von_okx(iid, takt, von_ms, bis_ms)
            gesamt = speichere(iid, takt, neu)
            bericht.setdefault(inst, {})[takt] = {
                "instId": iid, "neu": len(neu), "kerzen": gesamt}
    _speichere_instrumente(metas)
    _schreibe_stand()
    return bericht


def _schreibe_stand():
    reihen = {}
    namen = sorted(os.listdir(ORDNER)) if os.path.isdir(ORDNER) else []
    for name in namen:
        if not name.endswith(".json") or name == "_stand.json":
            continue
        try:
            with open(os.path.join(ORDNER, name), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(d, list) or not d or not isinstance(d[0], list):
            continue
        reihen[name[:-5]] = {"kerzen": len(d),
                             "von": d[0][0] if d else None,
                             "bis": d[-1][0] if d else None,
                             "herkunft": "okx",
                             "stand_ms": int(time.time() * 1000)}
    stan = {"reihen": reihen, "takte": dict(TAKTE)}
    os.makedirs(ORDNER, exist_ok=True)
    with open(os.path.join(ORDNER, "_stand.json"), "w",
              encoding="utf-8") as f:
        json.dump(stan, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return stan


def stand():
    try:
        with open(os.path.join(ORDNER, "_stand.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"reihen": {}}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--auffuellen", action="store_true")
    ap.add_argument("--stand", action="store_true")
    ap.add_argument("--instrumente", default="BTC,ETH,SOL")
    ap.add_argument("--takte", default="1H,4H")
    ap.add_argument("--von", default="2021-01-01")
    a = ap.parse_args()
    if a.stand:
        print(json.dumps(stand(), indent=2, ensure_ascii=False))
        return
    if not a.auffuellen:
        ap.print_help()
        return
    von = int(time.mktime(time.strptime(a.von, "%Y-%m-%d"))) * 1000
    b = auffuellen([x for x in a.instrumente.split(",") if x],
                   [x for x in a.takte.split(",") if x], von_ms=von)
    print(json.dumps(b, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
