"""Backtest-Kern: die Spur entscheidet, der Replay liefert nur Zeit und Daten.

Zwei Spurenfamilien (gemessen 2026-09-24):

  Familie A fuehrt ihr Buch im eigenen Modul (lade_wachen, lade_zustand,
  schreibe_zustand, journal, pruefe_einstieg, pruefe_ausstiege) und holt ihre
  Daten ueber eine *_quelle-Naht.

  Familie B fuehrt das Buch ueber spur_buch.zyklus(ordner, quelle, signal, ...)
  und bekommt `quelle` und `signal` ALS ARGUMENTE - der Replay schiebt dort
  eine historische Quelle unter, ohne die Spur zu veraendern.

Geschrieben wird ausschliesslich unter daten/backtest/<spur>/<lauf>/. Der echte
Spurenordner und Q:\\Handel_Journal werden nie beruehrt; der Test
`NichtsAusserhalbTest` vergleicht das Inventar vor und nach dem Lauf.

KERZEN sind Binance-Kerzen (Proxy, siehe historie.py) - jedes Ergebnis traegt
deshalb `kerzenquelle: binance`.

Aufruf:
    python replay.py --spur squeeze --max-kerzen 1500
    python replay.py --spur squeeze --gegenprobe
"""

import csv
import datetime as dt
import importlib.util
import json
import os
import sys

import historie

HIER = os.path.dirname(os.path.abspath(__file__))

# Spuren mit eigenem Buch im Modul (Familie A).
SPUREN_TEIL_A = ("squeeze", "wavetrend", "macd_mtf", "supertrend", "gitter",
                 "orb", "orbk", "mosaic", "moondev_funding")

# Spuren ueber spur_buch (Familie B).
SPUREN_TEIL_B = ("trendwende_btc", "liq_wand", "iv_waelle", "robinhood_radar",
                 "moondev_listingarb", "moondev_topmovers", "moondev_marktlage",
                 "moondev_sniper", "moondev_signalwelle", "moondev_whale",
                 "moondev_liquidation", "moondev_sentiment")

# Spuren, deren Datenquelle sich historisch nicht beschaffen laesst. Sie
# bekommen einen Vermerk statt einer geschaetzten Zahl.
NICHT_NACHRECHENBAR = {
    "moondev_whale": "OKX-OI-Historie antwortet 50030 Illegal time range",
    "moondev_liquidation": "keine frei abrufbare Liquidationshistorie",
    "moondev_sentiment": "RSS-Titel von damals nicht archiviert",
    "liq_wand": "keine frei abrufbare Liquidationshistorie",
    "iv_wand": "Strike-OI-Historie (Deribit) nicht abrufbar",
    "iv_waelle": "Strike-OI-Historie (Deribit) nicht abrufbar",
    "robinhood_radar": "fremde SQLite haelt nur den Sammelzeitraum",
    "kopier": "Solana-Onchain-Historie nur wenige Tage",
    "kopier1zu1": "Solana-Onchain-Historie nur wenige Tage",
    "nautilus": "Einstiege haengen an Quote-Ticks, die es nur live gibt",
    "nautilus_kraken": "Einstiege haengen an Quote-Ticks, die es nur live gibt",
    "nautilus_kraken_futures": "Einstiege haengen an Quote-Ticks",
    "scanner": "keine Kerzen-Naht (Kern-Spur, eigener Zyklus)",
    "xperp": "keine stuendliche Kerzen-Naht (Kern-Spur, eigener Zyklus)",
    "swap": "keine Kerzen-Naht (Kern-Spur, eigener Zyklus)",
    "kraken": "keine Kerzen-Naht (Kern-Spur, eigener Zyklus)",
    "spiegel": "ausser Betrieb seit 21.09.2026",
    "spiegel_knapp": "ausser Betrieb seit 21.09.2026",
    "spiegel_weit": "ausser Betrieb seit 21.09.2026",
}

# Naht fuer Tests: None -> HIER/daten/backtest.
verzeichnis = None


def wurzel():
    return (verzeichnis() if verzeichnis
            else os.path.join(HIER, "daten", "backtest"))


def spur_modul(spur):
    """Ein Spurenmodul ueber den PFAD laden, nicht ueber sys.path.

    sys.path waere falsch: die Spuren haben gleichnamige Module (gitter/grid.py
    und Handel/grid.py, dazu in jeder Spur ein handeln.py) - eine Reihenfolge
    entscheidet dann, welche Fassung geladen wird. Ueber den Pfad gibt es die
    Frage nicht.
    """
    pfad = os.path.join(HIER, spur, "handeln.py")
    if not os.path.isfile(pfad):
        raise FileNotFoundError("Spur %r hat kein handeln.py: %s" % (spur, pfad))
    s = importlib.util.spec_from_file_location("bt_" + spur, pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def buch_ordner(spur, lauf):
    """Der Backtest-Ordner einer Spur: Kopie der Wachen, sonst nichts.

    Die Wachen-KOPIE ist der Punkt: `journal_zweitziel` wird auf den
    Backtest-Ordner gebogen, damit selbst ein vergessener Spiegelungsaufruf
    nach innen kopiert und nie nach Q:.
    """
    ziel = os.path.join(wurzel(), spur, lauf)
    os.makedirs(ziel, exist_ok=True)
    quelle = os.path.join(HIER, spur, "wachen.json")
    if os.path.isfile(quelle):
        with open(quelle, encoding="utf-8") as f:
            w = json.load(f)
        w["journal_zweitziel"] = ziel
        w["handel_erlaubt"] = False          # im Backtest gibt es kein live
        with open(os.path.join(ziel, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(w, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return ziel


def schuetze(modul, ordner):
    """Alle Schreibwege einer Spur lahmlegen.

    `SCHREIBEN=False` allein reicht NICHT: es sichert nur `journal()`. Eine Spur
    schreibt auch Zustand und spiegelt - beides muss ebenfalls ins Leere laufen,
    sonst landet ein Backtest im Betriebsstand.
    """
    if hasattr(modul, "SCHREIBEN"):
        modul.SCHREIBEN = False
    if hasattr(modul, "journal"):
        modul.journal = lambda **f: None
    if hasattr(modul, "schreibe_zustand"):
        modul.schreibe_zustand = lambda *a, **k: None
    if hasattr(modul, "spiegeln"):
        modul.spiegeln = lambda *a, **k: None
    namen = {"WACHEN": "wachen.json", "ZUSTAND": "zustand.json",
             "JOURNAL": "handelsjournal.csv"}
    for name, datei in namen.items():
        if hasattr(modul, name):
            setattr(modul, name, os.path.join(ordner, datei))


def _feld(w, *namen, vorgabe=None):
    """Den ERSTEN gesetzten Namen nehmen.

    Die Spuren benennen dieselbe Sache verschieden (`kerzen_takt`,
    `kerzen_zeitrahmen`, `instrumente` als Liste ODER als Dict). Wer hier einen
    Namen fest verdrahtet, laesst eine Spur still ohne Kerzen laufen.
    """
    for n in namen:
        if w.get(n) not in (None, "", [], {}):
            return w[n]
    return vorgabe


def _instrumente(w):
    i = _feld(w, "instrumente", "instrument", "paare", vorgabe=[])
    if isinstance(i, dict):
        return list(i)
    if isinstance(i, str):
        return [x.strip() for x in i.split(",") if x.strip()]
    return list(i)


def _takt(w):
    return _feld(w, "kerzen_takt", "kerzen_zeitrahmen", "takt", "intervall",
                 vorgabe="1H")


def fenster_vorgabe(w):
    """Kerzen je Schritt, wenn keine Zahl angegeben wurde.

    Die Vorgabe MUSS die eigene Anforderung der Spur respektieren: ein Fenster
    unter `mindest_kerzen` laesst die Spur nie ein Signal bilden und der Lauf
    meldet "0 Runden" - das sieht wie ein Messergebnis aus, ist aber ein
    abgeschnittenes Fenster. Genau so gemessen am 2026-09-25: macd_mtf braucht
    fuer seinen 16er-Rahmen ~560 Basiskerzen, mit Fenster 400 kam kein einziger
    Handel zustande.
    """
    anzahl = int(_feld(w, "kerzen_anzahl", "anzahl_kerzen", vorgabe=400))
    return max(anzahl, int(w.get("mindest_kerzen", 300)) + 40)


def kerzen_fuer(spur, w, bis_ms=None, max_kerzen=None):
    """{inst: [kerzen]} aus der eigenen Historie, aufsteigend.

    Fehlt eine Reihe, wird sie GEMELDET und das Instrument faellt aus dem Lauf
    - nie still durch ein anderes Instrument ersetzt.

    `max_kerzen` schneidet die JUENGSTEN N Kerzen heraus. Das ist kein
    Schaetzen, sondern die Laufzeit: die Spuren rechnen ihre Indikatoren je
    Schritt ueber die ganze Reihe, ein Lauf ueber 50.000 Kerzen dauerte Stunden
    (derselbe Grund, aus dem es `bt_varianten_fast.py` gibt).
    """
    insts = _instrumente(w)
    takt = _takt(w)
    aus, fehlen = {}, []
    for inst in insts:
        reihen = historie.lade(inst, takt)
        if bis_ms:
            reihen = [r for r in reihen if r[0] <= bis_ms]
        if max_kerzen:
            reihen = reihen[-int(max_kerzen):]
        if len(reihen) < int(w.get("mindest_kerzen", 300)) + 20:
            fehlen.append("%s (%d Kerzen)" % (inst, len(reihen)))
            continue
        aus[inst] = reihen
    if fehlen:
        print("  ohne Historie: %s" % ", ".join(fehlen))
    return aus


def lauf_a(spur, gebuehr_pct, lauf, bis_ms=None, wachen_patch=None,
           max_kerzen=None, fenster=None):
    """Familie A ueber die Historie. Rueckgabe wie backtest_prognose.lauf().

    `wachen_patch` ueberschreibt einzelne Wachen-Werte - so setzt der Optimierer
    seine Kandidaten, ohne eine wachen.json anzufassen (Muster:
    `backtest_prognose.fahre(wachen_patch=...)`).

    `fenster` ist die Zahl der Kerzen, die die Spur je Schritt SIEHT (None =
    alles bis hierher). Das Fenster ist keine Abkuerzung, sondern die Wahrheit:
    im Betrieb fordert jede Spur eine feste `kerzen_anzahl` an, sie sieht nie
    die ganze Geschichte. Zwei Gruende, es auch hier zu tun:

      * TREUE - ein Praefix von 50.000 Kerzen ist ein Zustand, den die Spur im
        Betrieb nie hat; ihre Indikatoren rechnen dort auf anderem Material.
      * LAUFZEIT - die Spuren rechnen ihre Indikatoren je Schritt ueber die
        ganze Reihe, ein Praefixwachstum ist O(n^2). Gemessen 2026-09-25:
        900 Schritte ueber 1.200 Kerzen = 20 s; hochgerechnet auf 50.000 Kerzen
        waeren es ~16 Stunden. Mit Fenster bleibt der Schritt konstant.
    """
    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf)
    schuetze(modul, ordner)
    w = dict(modul.lade_wachen()) if hasattr(modul, "lade_wachen") else {}
    if wachen_patch:
        w.update(wachen_patch)
    kerzen = kerzen_fuer(spur, w, bis_ms, max_kerzen)
    if not kerzen:
        raise RuntimeError("keine Historie fuer %s - erst "
                           "'python historie.py --auffuellen'" % spur)
    if fenster is None:
        fenster = fenster_vorgabe(w)

    runden, offen, gesammelt = [], {}, []
    # Die Spur schreibt ihre Journalzeilen selbst (kauf/verkauf mit stop und
    # ziel). Wir fangen sie ab und schreiben sie hinterher in den Backtest-
    # Ordner - so entsteht KEINE zweite Journalform, und
    # kosten_wendepunkt.runden_aus_journal() kann sie paaren.
    modul.journal = lambda **f: gesammelt.append(f)
    z = {"positionen": [], "modus": "papier", "letzter_lauf": None,
         "verluste_usd": 0.0}
    laenge = min(len(k) for k in kerzen.values())
    mindest = int(w.get("mindest_kerzen", 300))

    for i in range(mindest, laenge):
        for inst, alle in kerzen.items():
            k = (alle[max(0, i + 1 - fenster):i + 1] if fenster
                 else alle[:i + 1])
            vorher = {id(p): p for p in z["positionen"]}
            modul.pruefe_ausstiege(z, k, w, nur=inst)
            nachher = {id(p) for p in z["positionen"]}
            for pid, p in vorher.items():
                if pid not in nachher and pid in offen:
                    e = offen.pop(pid)
                    kurs = k[-1][4]
                    vz = 1 if e["seite"] == "long" else -1
                    roh = (kurs - e["einstieg"]) / e["einstieg"] * 100.0 * vz
                    runden.append({
                        "inst": inst, "seite": e["seite"],
                        "einstieg": e["einstieg"], "ausstieg": kurs,
                        "nominal": e["nominal"], "stop_pct": e["stop_pct"],
                        "brutto_pct": roh, "netto_pct": roh - 2 * gebuehr_pct,
                        "gv_brutto": e["nominal"] * roh / 100.0,
                        "gv_netto": e["nominal"] * (roh - 2 * gebuehr_pct) / 100.0,
                        "ein_ts": e["ts"], "aus_ts": k[-1][0],
                        "stunden": (k[-1][0] - e["ts"]) / 3600000.0})
            vor_ids = {id(p) for p in z["positionen"]}
            modul.pruefe_einstieg(inst, k, z, w, 1.0)
            for p in z["positionen"]:
                if id(p) not in vor_ids:
                    offen[id(p)] = {"seite": p["seite"],
                                    "einstieg": p["einstieg"],
                                    "nominal": p["nominal"],
                                    "stop_pct": p.get("stop_pct", 0.0),
                                    "ts": k[-1][0]}
    _journal_schreiben(ordner, gesammelt)
    return runden, len(z["positionen"])


# Spaltenform des Hauses (spur_buch.SPALTEN). Diese Form ist Absicht:
# kosten_wendepunkt.runden_aus_journal() liest sie direkt, also gibt es fuer
# Backtest und Betrieb EINE Kennzahlenrechnung.
SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund"]


def _journal_schreiben(ordner, gesammelt):
    """Die Journalzeilen der Spur in den Backtest-Ordner schreiben.

    Geschrieben werden die Zeilen, die die SPUR selbst gebildet hat (kauf MIT
    stop/ziel, verkauf mit Endpreis). Eine selbst gebaute Zeilenform waere eine
    zweite Wahrheit - und eine Journalform mit nur Ausstiegszeilen haette fuer
    `runden_aus_journal()` NULL Runden ergeben, weil es nichts zu paaren gibt.
    """
    felder = [s for s in SPALTEN if any(s in r for r in gesammelt)]
    for r in gesammelt:
        for k in r:
            if k not in felder:
                felder.append(k)
    with open(os.path.join(ordner, "handelsjournal.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=felder, extrasaction="ignore")
        w.writeheader()
        for r in gesammelt:
            w.writerow(r)
    return len(gesammelt)


# Boersensatz je Spur, wenn die wachen.json keine Gebuehr traegt. Prozent je
# Seite. Quelle der Saetze: eigene Fuellungen und Boersenseiten (Kraken SOLEUR
# am 22.09.2026: 0,30012 EUR auf 50,01954 EUR = 0,6000 % je Seite).
BOERSENSAETZE = {
    "okx_spot": 0.10,        # scanner, squeeze, wavetrend, macd_mtf, supertrend
    "okx_perp": 0.05,        # liq_wand, trendwende_btc, swap, xperp
    "kraken": 0.60,          # orbk, kraken, mosaic, moondev_marktlage
}

SPUR_BOERSE = {
    # OKX Spot (USDC-Paare)
    "scanner": "okx_spot", "squeeze": "okx_spot", "wavetrend": "okx_spot",
    "macd_mtf": "okx_spot", "supertrend": "okx_spot", "orb": "okx_spot",
    # OKX Perp/Swap und Deribit
    "gitter": "okx_perp", "liq_wand": "okx_perp", "trendwende_btc": "okx_perp",
    "swap": "okx_perp", "xperp": "okx_perp", "iv_waelle": "okx_perp",
    "moondev_funding": "okx_perp", "moondev_listingarb": "okx_perp",
    "moondev_topmovers": "okx_perp", "moondev_sniper": "okx_perp",
    "moondev_signalwelle": "okx_perp", "moondev_whale": "okx_perp",
    "moondev_liquidation": "okx_perp", "moondev_sentiment": "okx_perp",
    # Kraken Spot (EUR)
    "orbk": "kraken", "kraken": "kraken", "mosaic": "kraken",
    "moondev_marktlage": "kraken",
}


def gebuehr_fuer(spur, w=None):
    """Gebuehr je Seite in Prozent.

    Reihenfolge: eigener Wert aus der wachen.json -> Boersensatz der Spur.
    Einen pauschalen Ersatz gibt es NICHT: fuer eine Perp-Spur waere die oft
    benutzte 0,10-%-Annahme der zwanzigfache Satz, und jedes Nettoergebnis
    damit zu schlecht.
    """
    if w is None:
        w = dict(spur_modul(spur).lade_wachen())
    wert = w.get("gebuehr_taker")
    if wert is not None:
        return round(float(wert) * 100.0, 4)
    satz = SPUR_BOERSE.get(spur)
    if satz is None:
        raise KeyError("kein Boersensatz fuer %r - bitte gebuehr_taker in die "
                       "wachen.json eintragen" % spur)
    return BOERSENSAETZE[satz]


def historische_quelle(modul, spur, zugriff):
    """Eine `quelle(w)`-Funktion, die aus der Historie speist statt zu laden.

    `zugriff` traegt den Stand des Walks: {"bis_ms", "fenster"}.

    Die Funktion wird bei JEDEM Schritt gerufen und schneidet die Kerzen auf den
    aktuellen Stand - die Spur sieht also nie die Zukunft, genau wie im Betrieb.

    Spuren mit reicheren Daten (Funding, Top-Mover, Volumen) brauchen je eigene
    Felder. Wer hier ein falsches Dict liefert, laesst die Spur STILL ohne
    Signal laufen und erzeugt ein Ergebnis, das wie ein Messwert aussieht -
    deshalb steht in NICHT_NACHRECHENBAR, was sich nicht bauen laesst, und
    `lauf_b` verweigert diese Spuren, statt zu raten.
    """
    def quelle(w):
        daten, kurse, fehler = {}, {}, []
        for inst in _instrumente(w):
            reihen = [r for r in historie.lade(inst, _takt(w))
                      if r[0] <= zugriff["bis_ms"]]
            if zugriff.get("fenster"):
                reihen = reihen[-int(zugriff["fenster"]):]
            if not reihen:
                fehler.append("%s: keine Historie" % inst)
                continue
            daten[inst] = {"kerzen": reihen, "bar": _takt(w)}
            kurse[inst] = float(reihen[-1][4])
        return daten, kurse, fehler

    return quelle


def lauf_b(spur, gebuehr_pct, lauf, bis_ms=None, max_kerzen=None, fenster=400,
           still=True):
    """Familie B ueber die Historie: ein `spur_buch.zyklus` je Kerze.

    Drei Dinge werden waehrend des Laufs stillgelegt, jedes aus einem konkreten
    Grund:

      * `ereignis.lauf` - jeder Zyklus oeffnet eine Bus-Meldung. Ueber 50.000
        Schritte waere das eine Flut im Bus-Journal und Telegram-Nachrichten aus
        einem Backtest.
      * `spur_buch.spiegeln` - Bedingung 4 spiegelt nach Q:. Der Backtest hat
        dort nichts zu suchen (die Wachen-Kopie zeigt ohnehin nach innen).
      * die Risikostufe - ein Backtest laeuft immer auf der Basis
        (`risikostufe.datei()` wuerde sonst `.mittel`-Dateien anlegen).

    `fenster` ist die Zahl der Kerzen, die die Spur je Schritt sieht (siehe
    `lauf_a`); im Betrieb fordert sie eine feste Anzahl an, nie die ganze
    Geschichte.
    """
    import contextlib
    import io

    # REIHENFOLGE IST PFLICHT: `spur_buch` legt beim Import den Bus-Ordner
    # (Agenten/Bus) in sys.path - dort liegt `ereignis.py`. Ein `import ereignis`
    # davor faellt mit ModuleNotFoundError um, obwohl das Modul existiert.
    import spur_buch
    import ereignis

    if spur in NICHT_NACHRECHENBAR:
        raise RuntimeError("%s ist nicht nachrechenbar: %s"
                           % (spur, NICHT_NACHRECHENBAR[spur]))

    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf)
    with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)
    takt = _takt(w)
    alle = {i: historie.lade(i, takt) for i in _instrumente(w)
            if historie.lade(i, takt)}
    if not alle:
        raise RuntimeError("keine Historie fuer %s - erst "
                           "'python historie.py --auffuellen'" % spur)
    if bis_ms:
        alle = {i: [r for r in k if r[0] <= bis_ms] for i, k in alle.items()}
    if max_kerzen:
        alle = {i: k[-int(max_kerzen):] for i, k in alle.items()}

    alt_schreiben, alt_zeit = spur_buch.SCHREIBEN, spur_buch.zeit_quelle
    alt_spiegeln, alt_lauf = spur_buch.spiegeln, ereignis.lauf
    alt_risiko = os.environ.pop("HANDEL_RISIKO", None)
    zugriff = {"bis_ms": 0, "fenster": fenster}
    quelle = historische_quelle(modul, spur, zugriff)
    puffer = io.StringIO()
    laenge = min(len(k) for k in alle.values())
    try:
        spur_buch.SCHREIBEN = True      # ins BACKTEST-Journal, nicht ins echte
        spur_buch.spiegeln = lambda *a, **k: None
        ereignis.lauf = _kein_bus
        with contextlib.redirect_stdout(puffer if still else sys.stdout):
            for i in range(int(w.get("mindest_kerzen", 300)), laenge):
                ts = max(k[i][0] for k in alle.values())
                zugriff["bis_ms"] = ts
                spur_buch.zeit_quelle = lambda _t=ts: dt.datetime.fromtimestamp(
                    _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
                spur_buch.zyklus(ordner, quelle, modul.signal, "papier",
                                 "handel/" + spur)
    finally:
        spur_buch.SCHREIBEN, spur_buch.zeit_quelle = alt_schreiben, alt_zeit
        spur_buch.spiegeln, ereignis.lauf = alt_spiegeln, alt_lauf
        if alt_risiko is not None:
            os.environ["HANDEL_RISIKO"] = alt_risiko
    journal = os.path.join(ordner, "handelsjournal.csv")
    return kennzahlen(journal), len(puffer.getvalue().splitlines())


def _kein_bus(*a, **k):
    """Ersatz fuer `ereignis.lauf` im Backtest: tut nichts, meldet nichts."""
    import contextlib as _c
    return _c.nullcontext()


def kennzahlen(journal_pfad):
    """Kennzahlen aus dem Backtest-Journal - EINE Rechnung fuer beide Welten.

    Gerufen wird `kosten_wendepunkt.runden_aus_journal()`: dieselbe Funktion,
    die der Betrieb fuer die echten Journale benutzt.
    """
    import kosten_wendepunkt
    from pathlib import Path
    runden, zwang = kosten_wendepunkt.runden_aus_journal(Path(journal_pfad))
    if not runden:
        return {"runden": 0, "zwang": len(zwang)}
    k = dict(kosten_wendepunkt.wendepunkt(runden) or {})
    k["zwang"] = len(zwang)
    return k


def gegenprobe(spur, gebuehr_pct, lauf="gegenprobe", max_kerzen=None):
    """Dieselben Kerzen durch beide Rechenwege, Runde fuer Runde verglichen.

    Verglichen werden Anzahl, Instrument, Seite, Einstieg und Bruttoprozente -
    die Felder, die beide Wege unabhaengig voneinander bilden. Ein Unterschied
    ist ein Fehler im neuen Kern, nicht im alten: `backtest_prognose.py` faehrt
    seit 21.09.2026 im Betrieb.
    """
    import backtest_prognose

    neu, _ = lauf_a(spur, gebuehr_pct, lauf, max_kerzen=max_kerzen)
    alt_modul = spur_modul(spur)
    schuetze(alt_modul, buch_ordner(spur, lauf + "_alt"))
    w = dict(alt_modul.lade_wachen())
    kerzen = kerzen_fuer(spur, w, None, max_kerzen)
    alt, _ = backtest_prognose.lauf(spur, kerzen, w, gebuehr_pct,
                                    modul=alt_modul)
    abw = []
    if len(neu) != len(alt):
        abw.append("Rundenzahl: neu %d, alt %d" % (len(neu), len(alt)))
    for i, (a, b) in enumerate(zip(neu, alt)):
        for feld in ("inst", "seite"):
            if a[feld] != b[feld]:
                abw.append("Runde %d %s: %r != %r" % (i, feld, a[feld], b[feld]))
        for feld in ("einstieg", "brutto_pct"):
            if abs(float(a[feld]) - float(b[feld])) > 1e-9:
                abw.append("Runde %d %s: %.10f != %.10f"
                           % (i, feld, a[feld], b[feld]))
    return {"gleich": not abw, "abweichungen": abw,
            "runden": len(neu), "runden_alt": len(alt),
            "kerzenquelle": "binance"}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spur", required=True)
    ap.add_argument("--lauf", default="lauf")
    ap.add_argument("--gebuehr", type=float, default=0.1)
    ap.add_argument("--max-kerzen", type=int, default=None)
    ap.add_argument("--fenster", type=int, default=None,
                    help="Kerzen je Schritt; Vorgabe: kerzen_anzahl der Spur")
    ap.add_argument("--ganz", action="store_true",
                    help="ganze Praefix-Historie je Schritt (sehr langsam)")
    ap.add_argument("--gegenprobe", action="store_true")
    a = ap.parse_args()
    mk = a.max_kerzen
    fenster = None if a.ganz else a.fenster
    if fenster is None and not a.ganz:
        w = dict(spur_modul(a.spur).lade_wachen())
        fenster = fenster_vorgabe(w)
    if a.gegenprobe:
        print(json.dumps(gegenprobe(a.spur, a.gebuehr, a.lauf, mk),
                         indent=2, ensure_ascii=False))
        return
    runden, offen = lauf_a(a.spur, a.gebuehr, a.lauf, max_kerzen=mk,
                           fenster=fenster)
    print(json.dumps({"spur": a.spur, "runden": len(runden),
                      "offen": offen, "gebuehr_pct": a.gebuehr,
                      "fenster": fenster, "kerzenquelle": "binance",
                      "kennzahlen": kennzahlen(os.path.join(
                          buch_ordner(a.spur, a.lauf), "handelsjournal.csv"))},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
