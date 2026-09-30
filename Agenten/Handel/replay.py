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

KERZEN sind Binance-Kerzen (Proxy, siehe historie_binance.py) - jedes Ergebnis traegt
deshalb `kerzenquelle: binance`.

Aufruf:
    python replay.py --spur squeeze --max-kerzen 1500
    python replay.py --spur squeeze --gegenprobe
"""

import bisect
import csv
import datetime as dt
import importlib.util
import json
import os
import sys

import historie_binance

HIER = os.path.dirname(os.path.abspath(__file__))

# Spuren mit eigenem Buch im Modul (Familie A).
SPUREN_TEIL_A = ("squeeze", "wavetrend", "macd_mtf", "supertrend", "gitter",
                 "orb", "orbk", "mosaic")

# Spuren mit eigenem `lauf(modus)` und eigenen Nahtnamen (Familie C). Sie
# fuehren kein Kerzenbuch: `moondev_funding` liest einen Funding-Satz je Symbol
# und haelt ihren Zustand selbst.
SPUREN_TEIL_C = ("moondev_funding",)

# Ein Funding-Satz aendert sich alle acht Stunden - so weit ist ein Schritt.
FUNDING_STUNDEN = 8

# Spuren ueber spur_buch (Familie B).
SPUREN_TEIL_B = ("trendwende_btc", "liq_wand", "iv_waelle", "robinhood_radar",
                 "moondev_listingarb", "moondev_topmovers", "moondev_marktlage",
                 "moondev_sniper", "moondev_signalwelle", "moondev_whale",
                 "moondev_liquidation", "moondev_sentiment")

# Spuren, deren Datenquelle sich historisch nicht beschaffen laesst. Sie
# bekommen einen Vermerk statt einer geschaetzten Zahl.
NICHT_NACHRECHENBAR = {
    # Feed-Spuren ohne historisch beschaffbare Quelle. Der GRUND gehoert
    # daneben - eine leere Zeile waere nicht zu deuten.
    "moondev_sniper": "pump.fun-Neulaunches mit Alter in Minuten - nur live",
    "moondev_listingarb": "Marktkapitalisierung frei nicht historisch abrufbar",
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


def wachen_von(spur):
    """Die Wachen einer Spur aus ihrer DATEI.

    Nicht ueber `modul.lade_wachen()`: das gibt es nur bei Familie A. Fuer die
    Feed-Spuren riss der Aufruf den Lauf mit AttributeError ab, bevor ein
    einziger Schritt gerechnet war (29.09.2026) - die Kostenrechnung haengt
    nicht an einer Spurenfamilie.
    """
    pfad = os.path.join(HIER, spur, "wachen.json")
    if not os.path.isfile(pfad):
        return {}
    with open(pfad, encoding="utf-8") as f:
        return json.load(f)


def buch_ordner(spur, lauf, setzen=None):
    """Der Backtest-Ordner einer Spur: Kopie der Wachen, sonst nichts.

    Die Wachen-KOPIE ist der Punkt: `journal_zweitziel` wird auf den
    Backtest-Ordner gebogen, damit selbst ein vergessener Spiegelungsaufruf
    nach innen kopiert und nie nach Q:.

    `setzen` ueberschreibt EINZELNE Werte in der KOPIE - die Wachen der Spur
    selbst werden nie angefasst. Wofuer das da ist: eine Spur, deren Kill-
    Schalter den Lauf nach sechs Tagen abwuergt (moondev_funding, gemessen am
    29.09.2026), ist sonst ueber den ganzen Zeitraum nicht messbar. Was gesetzt
    wurde, steht als `_backtest_gesetzt` in der Kopie - wer den Ordner spaeter
    liest, sieht den Unterschied zur echten Wachen, statt ihn zu ahnen.
    """
    ziel = os.path.join(wurzel(), spur, lauf)
    os.makedirs(ziel, exist_ok=True)
    quelle = os.path.join(HIER, spur, "wachen.json")
    if os.path.isfile(quelle):
        with open(quelle, encoding="utf-8") as f:
            w = json.load(f)
        w["journal_zweitziel"] = ziel
        w["handel_erlaubt"] = False          # im Backtest gibt es kein live
        if setzen:
            w["_backtest_gesetzt"] = dict(setzen)
            w.update(setzen)
        with open(os.path.join(ziel, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(w, f, indent=2, ensure_ascii=False)
            f.write("\n")
    return ziel


def setzen_aus(text):
    """`name=wert` (mehrfach) in ein Dict - Zahlen und Wahrheitswerte erkannt."""
    aus = {}
    for stueck in (text or ()):
        if "=" not in stueck:
            raise SystemExit("--setzen braucht name=wert, nicht %r" % stueck)
        name, wert = stueck.split("=", 1)
        wert = wert.strip()
        if wert.lower() in ("true", "false"):
            aus[name.strip()] = wert.lower() == "true"
        else:
            try:
                aus[name.strip()] = float(wert) if "." in wert else int(wert)
            except ValueError:
                aus[name.strip()] = wert
    return aus


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


def kerzen_fuer(spur, w, bis_ms=None, max_kerzen=None, abschnitt=None):
    """{inst: [kerzen]} aus der eigenen Historie, aufsteigend.

    Fehlt eine Reihe, wird sie GEMELDET und das Instrument faellt aus dem Lauf
    - nie still durch ein anderes Instrument ersetzt.

    `max_kerzen` schneidet die JUENGSTEN N Kerzen heraus. Das ist kein
    Schaetzen, sondern die Laufzeit: die Spuren rechnen ihre Indikatoren je
    Schritt ueber die ganze Reihe, ein Lauf ueber 50.000 Kerzen dauerte Stunden
    (derselbe Grund, aus dem es `bt_varianten_fast.py` gibt).

    `abschnitt=(von_index, bis_index)` schneidet einen Zeitabschnitt heraus -
    so bildet der Optimierer Such- und Prueffenster. Bewusst nach INDIZES und
    nicht nach Zeitstempeln: der Walk laeuft ueber die kuerzeste Reihe
    (`laenge = min(len(k))`), ein Index gilt also fuer alle Instrumente
    gleich. Ein Zeitstempel dagegen muss erst je Instrument gesucht werden -
    und ein Index, der versehentlich als `bis_ms` uebergeben wird, ergibt ein
    still falsches, winziges Fenster.
    """
    insts = _instrumente(w)
    takt = _takt(w)
    aus, fehlen = {}, []
    for inst in insts:
        reihen = historie_binance.lade(inst, takt)
        if bis_ms:
            reihen = [r for r in reihen if r[0] <= bis_ms]
        if abschnitt:
            von, bis = abschnitt
            reihen = reihen[int(von):int(bis)]
        if max_kerzen:
            reihen = reihen[-int(max_kerzen):]
        if len(reihen) < int(w.get("mindest_kerzen", 300)) + 20:
            fehlen.append("%s (%d Kerzen)" % (inst, len(reihen)))
            continue
        aus[inst] = reihen
    if fehlen:
        print("  ohne Historie: %s" % ", ".join(fehlen))
    return aus


# --- Ausstieg am BERUEHRTEN Kurs (Backtest-Regel) ---------------------------
#
# Der Replay kannte einen einzigen Ausstiegskurs: den SCHLUSS der Kerze, in der
# Stop oder Ziel beruehrt wurde. Das ueberschaetzt jeden Laeufer - belegt an
# ADA, Ziel +12 %, geschlossen +48 % - und damit jede Kennzahl, die auf dem
# Replay aufbaut.
#
# Richtig ist der Kurs der MARKEN selbst: steht die Marke in der Kerze, ist sie
# der Ausstieg. Gemessen wird am Hoch/Tief der Kerze, nicht am Schluss.
#
# Diese Regel liegt HIER und nicht in `spur_buch.pruefe_ausstiege()`: jene
# Funktion ist der LIVE-Pfad einer Spur. Im Backtest wird die Journalzeile
# berichtigt, bevor sie ins Backtest-Journal geht (Journal-Huelle unten) - die
# Spuren selbst bleiben unangetastet.
#
# Was diese Regel NICHT aendert: WANN ausgestiegen wird. Der Ausloeser bleibt
# der Schluss der Kerze, denn so entscheiden die Spuren live. Ein Ausstieg
# allein wegen eines Dochts ist damit weiterhin nicht abgebildet - das ist eine
# zweite, eigene Frage und keine Nebenwirkung dieser Regel.

def _zahl(x):
    """Eine Journalzelle als Zahl - None, wenn sie fehlt oder unlesbar ist."""
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def beruehrte_marke(kerze, seite, stop, ziel):
    """Welche Marke hat diese Kerze beruehrt - "stop", "ziel" oder None?

    Gemessen wird am HOCH und TIEF der Kerze, nicht an ihrem Schluss: der
    Schluss verraet nicht, ob die Marke ueberhaupt gestreift wurde. Liegen
    BEIDE Marken in derselben Kerze, gilt die KONSERVATIVE Reihenfolge (erst
    der Stop) - die guenstige waere genau der Schoenheitsfehler, den diese
    Regel beseitigt.

    `kerze` ist eine Binance-Reihe [ts, o, h, l, c, v].
    """
    if not kerze or len(kerze) < 5:
        return None
    seite = str(seite or "").strip().lower()
    if seite not in ("long", "short"):
        return None
    hoch, tief = _zahl(kerze[2]), _zahl(kerze[3])
    stop, ziel = _zahl(stop), _zahl(ziel)
    if None in (hoch, tief, stop, ziel):
        return None
    if seite == "long":
        if tief <= stop:
            return "stop"
        if hoch >= ziel:
            return "ziel"
    else:
        if hoch >= stop:
            return "stop"
        if tief <= ziel:
            return "ziel"
    return None


def kurs_der_marke(kerze, seite, stop, ziel):
    """Der Ausstiegskurs EINER Kerze: der Kurs der beruehrten Marke oder None.

    EINE Stelle fuer beide Rechenwege (`lauf_a` und `backtest_prognose.lauf`) -
    zwei Fassungen derselben Regel waeren zwei Wahrheiten.
    """
    marke = beruehrte_marke(kerze, seite, stop, ziel)
    if marke is None:
        return None
    return _zahl(stop) if marke == "stop" else _zahl(ziel)


def _preis_text(level, alt):
    """Den Ausstiegskurs in der SCHREIBWEISE der Zeile halten.

    Die Zeilen der Spuren tragen sechs Nachkommastellen (die Sniper mehr). Wer
    hier hart formatiert, macht aus einer Zahl einen anderen String - also
    uebernimmt diese Funktion die Zahl der Stellen vom alten Wert.
    """
    txt = str(alt if alt is not None else "")
    stellen = 0
    if "." in txt:
        stellen = len(txt.split(".")[1])
    # Die Marke selbst kann MEHR Stellen tragen als die alte Zelle
    # (0.68171040 gegen 0.681710). Wer auf die alte Stellenzahl rundet,
    # verschiebt den Ausstieg still wieder von der Marke weg - deshalb das
    # Maximum aus beiden.
    marke = repr(float(level))
    if "." in marke:
        stellen = max(stellen, len(marke.split(".")[1].rstrip("0")))
    return "%.*f" % (min(int(stellen) if stellen else 6, 12), float(level))


class Beruehrungsjournal:
    """Journal-Huelle: Ausstiege werden auf den BERUEHRTEN Kurs gezogen.

    Sie sitzt VOR dem Journal der Spur (Familie A) bzw. vor `spur_buch.journal`
    (Familie B) und sieht damit jede Zeile. Berichtigt werden nur Zeilen, die
    einen Ausstieg an einer MARKE aussprechen (`grund` stop/ziel): sie bekommen
    den Kurs der Marke und ihr `einsatz_usd` aus dem gemerkten Einstieg.
    Einstiege und alle uebrigen Ausstiegsgruende (Frist, Rueckdreh, Herzschlag,
    Buchbereinigung) gehen UNVERAENDERT durch - fuer sie gibt es keinen
    Markenpreis.

    `kerzen` ist ein VERANDERLICHES Dict {inst: Kerze des aktuellen Schritts};
    die Familie setzt es je Schritt, bevor sie den Zyklus fahren laesst.
    """

    def __init__(self, kerzen, weiter=None, kerze_fuer=None):
        self.kerzen = kerzen
        self.weiter = weiter       # None = Zeilen nur sammeln (Familie A)
        # Optional: die Kerze erst holen, wenn eine Markenzeile auftaucht.
        # Familie C rechnet je Schritt nur einen Preis aus - dort waere ein
        # Vorrat ueber alle Instrumente zehntausende Dateizugriffe wertlos.
        self.kerze_fuer = kerze_fuer
        self.einstiege = {}        # {inst: (einstieg, nominal)}
        self.berichtigt = 0        # berichtigte Ausstiegszeilen
        self.ohne_marke = 0        # Zeile ohne Kerze/Marke - BENANNT, nie still
        # Je Instrument die Kurse der berichtigten Markenzeilen DIESES
        # Schritts, in der Reihenfolge der Zeilen. Der Prognose-Backtest
        # baut seine RUNDE daraus (er rechnet sonst mit dem Kerzenschluss
        # weiter - Journal richtig, Ergebnis falsch). Eine LISTE, nicht ein
        # Einzelwert: schliesst ein Instrument in einem Schritt zwei
        # Positionen, braucht jede ihren eigenen Kurs.
        self.marke_je_inst = {}

    def schritt_anfang(self):
        """Die Warteschlangen leeren - EINMAL je Kerzenschritt."""
        self.marke_je_inst.clear()

    def nimm_marke(self, inst):
        """Kurs der naechsten Markenzeile dieses Instruments, sonst None."""
        w = self.marke_je_inst.get(inst)
        return w.pop(0) if w else None

    def __call__(self, *a, **f):
        f = self._berichtigen(dict(f))
        self._merken(f)
        if self.weiter is None:
            return None
        return self.weiter(*a, **f)

    def _merken(self, f):
        if str(f.get("aktion") or "").strip().lower() not in ("kauf", "einstieg",
                                                              "eroeffnen"):
            return
        einstieg, nominal = _zahl(f.get("preis")), _zahl(f.get("einsatz_usd"))
        if einstieg and nominal:
            self.einstiege[f.get("inst")] = (einstieg, nominal)

    def _kerze(self, inst):
        if self.kerze_fuer is not None:
            return self.kerze_fuer(inst)
        return (self.kerzen or {}).get(inst)

    def _berichtigen(self, f):
        grund = str(f.get("grund") or "").strip().lower()
        if grund not in ("stop", "ziel"):
            return f
        kerze = self._kerze(f.get("inst"))
        seite = str(f.get("seite") or "").strip().lower()
        marke = beruehrte_marke(kerze, seite, f.get("stop"), f.get("ziel"))
        if marke is None:
            # Keine Kerze zur Zeile (oder keine Marke in ihr): die Zeile bleibt
            # wie sie ist und wird GEZAEHLT - eine stille Nicht-Aenderung waere
            # von einer Nicht-Pruefung nicht zu unterscheiden.
            self.ohne_marke += 1
            return f
        kurs = _zahl(f.get("stop")) if marke == "stop" else _zahl(f.get("ziel"))
        neu = dict(f)
        neu["preis"] = _preis_text(kurs, f.get("preis"))
        neu["grund"] = marke
        ein = self.einstiege.get(f.get("inst"))
        if ein:
            einstieg, nominal = ein
            vz = 1.0 if seite == "long" else -1.0
            gv = nominal * ((kurs - einstieg) / einstieg) * vz
            if "einsatz_usd" in neu:
                neu["einsatz_usd"] = "%.2f" % (nominal + gv)
        self.berichtigt += 1
        self.marke_je_inst.setdefault(f.get("inst"), []).append(kurs)
        return neu


def _feed_kerze(inst, ts, takt="1H"):
    """Die Kerze des Schritts fuer eine Spur mit eigenem `lauf()`.

    Diese Spuren pruefen ihren Ausstieg gegen einen MARK-PREIS je Schritt
    (bei moondev_funding: je Funding-Zeitpunkt). Der Preis wird aus der
    Stunden-Reihe des Bestands gebildet - also ist genau DIESE Kerze der
    Massstab. Die uebrigen Stunden des Funding-Fensters (8 h) liefert die
    Reihe hier nicht mit; die Regel sieht damit nur die Stunde des
    Ausstiegs. Das ist eine Grenze der DATEN, nicht der Regel, und sie
    steht im Wiki.

    Kein Fehler, wenn nichts da ist: der Aufrufer zaehlt die Zeile dann als
    "ohne Marke" und laesst sie stehen.
    """
    try:
        import moondev_historie
        sym = historie_binance.symbol(inst)
        reihen = moondev_historie.lade_feed(sym, takt)
        if not reihen:
            return None
        zeiten = moondev_historie._reihen_zeiten(sym, takt)
        i = bisect.bisect_right(zeiten, int(ts)) - 1
        return reihen[i] if i >= 0 else None
    except Exception:                                   # noqa: BLE001
        return None


def auf_der_marke(journal_pfad):
    """Wie viele Ausstiege sitzen GENAU auf ihrer Marke (Stop bzw. Ziel)?

    Das ist die Gegenprobe zur Regel oben, aus dem Journal selbst gelesen: ein
    Ausstieg, der die Marke trifft, steht auf ihr; ein Ausstieg auf dem
    Kerzenschluss (die alte Rechnung) trifft sie so gut wie nie. Die Zahl steht
    deshalb neben jeder Kennzahl - sonst waere "die Regel wirkt" eine
    Behauptung.
    """
    trifft, ausstiege = 0, 0
    try:
        with open(journal_pfad, newline="", encoding="utf-8") as f:
            for zeile in csv.DictReader(f):
                grund = str(zeile.get("grund") or "").strip().lower()
                if grund not in ("stop", "ziel"):
                    continue
                ausstiege += 1
                preis = _zahl(zeile.get("preis"))
                marke = _zahl(zeile.get("stop") if grund == "stop"
                              else zeile.get("ziel"))
                if preis is None or marke is None:
                    continue
                if abs(preis - marke) <= 1e-8 * max(1.0, abs(marke)):
                    trifft += 1
    except FileNotFoundError:
        return {"ausstiege_an_marke": 0, "ausstiege": 0}
    return {"ausstiege_an_marke": trifft, "ausstiege": ausstiege}


def lauf_a(spur, gebuehr_pct, lauf, bis_ms=None, wachen_patch=None,
           max_kerzen=None, fenster=None, abschnitt=None):
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
    kerzen = kerzen_fuer(spur, w, bis_ms, max_kerzen, abschnitt)
    if not kerzen:
        raise RuntimeError("keine Historie fuer %s - erst "
                           "'python historie_binance.py --auffuellen'" % spur)
    if fenster is None:
        fenster = fenster_vorgabe(w)

    runden, offen, gesammelt = [], {}, []
    zustand_ts = {"ts": None}
    # Die Spur schreibt ihre Journalzeilen selbst (kauf/verkauf mit stop und
    # ziel). Wir fangen sie ab und schreiben sie hinterher in den Backtest-
    # Ordner - so entsteht KEINE zweite Journalform, und
    # kosten_wendepunkt.runden_aus_journal() kann sie paaren.
    #
    # Jede Zeile bekommt zusaetzlich `_kerzen_ts` (den Zeitstempel der Kerze, an
    # der sie entstand). Ohne den haengt eine spaetere Fensterteilung an der
    # Spalte `zeit` - und die traegt die WANDUHR, wenn die Spur ihre eigene
    # `_jetzt()` benutzt und die Uhr nicht gesetzt wurde (gemessen 2026-09-25:
    # ein 6-Monats-Lauf schrieb alle Zeilen mit der Uhrzeit des Laufs).
    # Der Ausstieg wird auf den BERUEHRTEN Kurs gezogen, BEVOR die Zeile ins
    # Backtest-Journal geht (Regel oben) - die Spur selbst bleibt unberuehrt.
    kerzen_jetzt = {}
    huelle = Beruehrungsjournal(
        kerzen_jetzt,
        lambda **f: gesammelt.append(dict(f, _kerzen_ts=zustand_ts["ts"])))
    modul.journal = huelle
    alt_zeit = getattr(modul, "zeit_quelle", None)
    hat_zeit = hasattr(modul, "zeit_quelle")
    z = {"positionen": [], "modus": "papier", "letzter_lauf": None,
         "verluste_usd": 0.0}
    laenge = min(len(k) for k in kerzen.values())
    mindest = int(w.get("mindest_kerzen", 300))

    for i in range(mindest, laenge):
        # DIESELBE NAHT WIE FAMILIE B: die Spuren lesen `zeit_quelle`, wenn sie
        # gesetzt ist. Ohne das schreibt das Journal die Uhrzeit des Backtest-
        # Laufs statt der Kerzenzeit - und jede Zeitrechnung darauf ist falsch.
        ts_schritt = max(k[i][0] for k in kerzen.values())
        zustand_ts["ts"] = ts_schritt
        if hat_zeit:
            modul.zeit_quelle = lambda _t=ts_schritt: dt.datetime.fromtimestamp(
                _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
        for inst, alle in kerzen.items():
            k = (alle[max(0, i + 1 - fenster):i + 1] if fenster
                 else alle[:i + 1])
            kerzen_jetzt[inst] = k[-1]
            vorher = {id(p): p for p in z["positionen"]}
            modul.pruefe_ausstiege(z, k, w, nur=inst)
            nachher = {id(p) for p in z["positionen"]}
            for pid, p in vorher.items():
                if pid not in nachher and pid in offen:
                    e = offen.pop(pid)
                    kerze = k[-1]
                    # Der Ausstieg geschieht am KURS DER MARKE (Stop bzw.
                    # Ziel), nicht am Kerzenschluss - siehe Regel oben.
                    # Ohne Marke in der Kerze bleibt es beim Schluss.
                    kurs = kurs_der_marke(kerze, e["seite"], e["stop"],
                                          e["ziel"])
                    if kurs is None:
                        kurs = kerze[4]
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
                                    "stop": p.get("stop"),
                                    "ziel": p.get("ziel"),
                                    "ts": k[-1][0]}
    if hat_zeit:
        modul.zeit_quelle = alt_zeit
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
        w = wachen_von(spur)
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
            reihen = [r for r in historie_binance.lade(inst, _takt(w))
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
           still=True, abschnitt=None):
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
    alle = {i: historie_binance.lade(i, takt) for i in _instrumente(w)
            if historie_binance.lade(i, takt)}
    if not alle:
        raise RuntimeError("keine Historie fuer %s - erst "
                           "'python historie_binance.py --auffuellen'" % spur)
    if bis_ms:
        alle = {i: [r for r in k if r[0] <= bis_ms] for i, k in alle.items()}
    if abschnitt:
        von, bis = abschnitt
        alle = {i: k[int(von):int(bis)] for i, k in alle.items()}
    if max_kerzen:
        alle = {i: k[-int(max_kerzen):] for i, k in alle.items()}

    alt_schreiben, alt_zeit = spur_buch.SCHREIBEN, spur_buch.zeit_quelle
    alt_spiegeln, alt_lauf = spur_buch.spiegeln, ereignis.lauf
    alt_journal = spur_buch.journal
    alt_risiko = os.environ.pop("HANDEL_RISIKO", None)
    zugriff = {"bis_ms": 0, "fenster": fenster, "kerzen": {}}
    quelle = historische_quelle(modul, spur, zugriff)
    puffer = io.StringIO()
    laenge = min(len(k) for k in alle.values())
    try:
        spur_buch.SCHREIBEN = True      # ins BACKTEST-Journal, nicht ins echte
        spur_buch.spiegeln = lambda *a, **k: None
        spur_buch.journal = Beruehrungsjournal(zugriff["kerzen"], alt_journal)
        ereignis.lauf = _kein_bus
        with contextlib.redirect_stdout(puffer if still else sys.stdout):
            for i in range(int(w.get("mindest_kerzen", 300)), laenge):
                ts = max(k[i][0] for k in alle.values())
                zugriff["bis_ms"] = ts
                # Die Kerze des Schritts je Instrument - die Journal-Huelle
                # zieht den Ausstieg damit auf den beruehrten Kurs.
                zugriff["kerzen"] = {name: kk[-1] for name, kk in alle.items()}
                spur_buch.zeit_quelle = lambda _t=ts: dt.datetime.fromtimestamp(
                    _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
                spur_buch.zyklus(ordner, quelle, modul.signal, "papier",
                                 "handel/" + spur)
    finally:
        spur_buch.SCHREIBEN, spur_buch.zeit_quelle = alt_schreiben, alt_zeit
        spur_buch.spiegeln, ereignis.lauf = alt_spiegeln, alt_lauf
        spur_buch.journal = alt_journal
        if alt_risiko is not None:
            os.environ["HANDEL_RISIKO"] = alt_risiko
    journal = os.path.join(ordner, "handelsjournal.csv")
    return kennzahlen(journal), len(puffer.getvalue().splitlines())


def _kein_bus(*a, **k):
    """Ersatz fuer `ereignis.lauf` im Backtest: tut nichts, meldet nichts."""
    import contextlib as _c
    return _c.nullcontext()


def lauf_feed(spur, gebuehr_pct, lauf, takt="1D", mindest_symbole=30,
              von_ms=None, bis_ms=None, still=True, setzen=None):
    """Familie B ueber den Marktquerschnitt: ein `spur_buch.zyklus` je Schritt.

    Der Unterschied zu `lauf_b`: dort ist eine Kerze ein Schritt je Instrument,
    hier ist ein ZEITPUNKT ein Schritt ueber alle Kandidaten - die Feed-Spuren
    entscheiden ueber einen Marktquerschnitt, nicht ueber eine Reihe. Die Tafel
    liefert genau die Felder, die ihre `quelle()` sonst von CoinGecko holt.

    `schritte` kommt aus dem Bestand (Zeitstempel mit mindestens
    `mindest_symbole` Reihen): ein Tag mit drei Reihen waere keine Marktbreite.
    Stilllegung wie in `lauf_b` - `ereignis.lauf`, `spur_buch.spiegeln` und die
    Risikostufe.

    ZUR GEBUEHR: `spur_buch.zyklus` schreibt Preise, keine Kosten - das
    Journal ist also BRUTTO, genau wie das Journal der Spur im Betrieb.
    `kennzahlen()` ist damit brutto; netto steht daneben als
    `netto_je_runde_pct` (zwei Seiten je Runde), damit die Zahl nicht mit der
    netto gerechneten Familie A verwechselt wird.
    """
    import contextlib
    import io

    # REIHENFOLGE IST PFLICHT: spur_buch legt beim Import Agenten/Bus auf den
    # Suchpfad - andersherum faellt "import ereignis" mit ModuleNotFoundError
    # um, und der Lauf stirbt vor dem ersten Schritt.
    import spur_buch
    import ereignis
    import moondev_historie

    if spur in NICHT_NACHRECHENBAR:
        raise RuntimeError("%s ist nicht nachrechenbar: %s"
                           % (spur, NICHT_NACHRECHENBAR[spur]))
    if spur not in moondev_historie.QUELLEN:
        raise KeyError("kein Quellen-Adapter fuer %r - bekannt: %s"
                       % (spur, ", ".join(sorted(moondev_historie.QUELLEN))))

    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf, setzen)
    with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)
    bestand = moondev_historie.Bestand()
    bestand.laden(takt)
    schritte = bestand.schritte(mindest_symbole, von_ms, bis_ms)
    if not schritte:
        raise RuntimeError("keine Schritte mit mindestens %d Reihen - "
                           "Universum zu klein oder Zeitraum falsch"
                           % mindest_symbole)

    # Das Journal fuehrt den BASISWERT (1INCH), die Tafel das Binance-Symbol
    # (1INCHUSDT). Ohne diese Zuordnung findet `bestand.kerze()` nichts und
    # die Beruehrungsregel wuerde in dieser Familie still gar nichts tun.
    basis_zu_sym = {}
    for _sym in bestand.symbole():
        _b = moondev_historie.basis_von(_sym)
        if _b:
            basis_zu_sym.setdefault(_b, _sym)
    quelle_adapter = moondev_historie.QUELLEN[spur]
    alt_schreiben, alt_zeit = spur_buch.SCHREIBEN, spur_buch.zeit_quelle
    alt_spiegeln, alt_lauf = spur_buch.spiegeln, ereignis.lauf
    alt_journal = spur_buch.journal
    alt_risiko = os.environ.pop("HANDEL_RISIKO", None)
    kerzen_jetzt = {}
    puffer = io.StringIO()
    leer = 0
    try:
        spur_buch.SCHREIBEN = True              # ins BACKTEST-Journal
        spur_buch.spiegeln = lambda *a, **k: None
        huelle = Beruehrungsjournal(kerzen_jetzt, alt_journal)
        spur_buch.journal = huelle
        ereignis.lauf = _kein_bus
        with contextlib.redirect_stdout(puffer if still else sys.stdout):
            for ts in schritte:
                daten, kurse, fehler = quelle_adapter(bestand, ts, w)
                if not daten:
                    leer += 1
                    continue
                # Die Kerze des Schritts je Kandidat - die Journal-Huelle
                # zieht den Ausstieg damit auf den beruehrten Kurs. Die Tafel
                # liefert Tagesfelder, die Kerze kommt aus dem Bestand.
                kerzen_jetzt.clear()
                for _i in daten:
                    _sym = basis_zu_sym.get(_i)
                    _k = bestand.kerze(_sym, ts) if _sym else None
                    if _k:
                        kerzen_jetzt[_i] = _k
                quelle = (lambda _w, _d=daten, _k=kurse, _f=fehler:
                          (_d, _k, _f))
                spur_buch.zeit_quelle = lambda _t=ts: dt.datetime.fromtimestamp(
                    _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
                spur_buch.zyklus(ordner, quelle, modul.signal, "papier",
                                 "handel/" + spur)
    finally:
        spur_buch.SCHREIBEN, spur_buch.zeit_quelle = alt_schreiben, alt_zeit
        spur_buch.spiegeln, ereignis.lauf = alt_spiegeln, alt_lauf
        spur_buch.journal = alt_journal
        if alt_risiko is not None:
            os.environ["HANDEL_RISIKO"] = alt_risiko
    journal = os.path.join(ordner, "handelsjournal.csv")
    k = kennzahlen(journal)
    runden = int(k.get("runden") or 0)
    if runden:
        je_runde = float(k.get("ergebnis_summe") or 0.0) / runden
        k["ergebnis_je_runde_pct"] = je_runde
        k["netto_je_runde_pct"] = je_runde - 2.0 * float(gebuehr_pct)
    k.update({"schritte": len(schritte), "schritte_ohne_kandidaten": leer,
              "takt": takt, "gebuehr_pct": float(gebuehr_pct),
              "universum": len(bestand.symbole()), "kerzenquelle": "binance",
              # Die Arbeit der Beruehrungsregel, damit ein Lauf nicht nur
              # nach seiner Zahl, sondern nach seiner Pruefung beurteilt
              # wird: `ohne_marke` > 0 heisst, dass Ausstiege NICHT
              # berichtigt werden konnten (Kerze fehlte).
              "berichtigt": huelle.berichtigt,
              "ohne_marke": huelle.ohne_marke})
    return k, len(puffer.getvalue().splitlines())


def lauf_c(spur, gebuehr_pct, lauf, von_ms=None, bis_ms=None, still=True,
           setzen=None):
    """Familie C: eine Spur mit eigenem `lauf(modus)` und eigenem Buch.

    Anders als in Familie A wird hier nichts abgefangen: die Spur schreibt ihr
    Journal und ihren Zustand SELBST - nur die DREI PFADE zeigen in den
    Backtest-Ordner. Damit liest `kosten_wendepunkt.runden_aus_journal()`
    dieselbe Zeilenform wie im Betrieb, und es entsteht keine zweite
    Journalform.

    `spiegeln` wird stillgelegt (Bedingung 4 hat im Backtest nichts zu suchen),
    `funding_quelle` und `zeit_quelle` werden gesetzt - genau die Nahten, die
    die Spur fuer ihre Tests schon benutzt.
    """
    import contextlib
    import io

    import moondev_historie

    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf, setzen)
    with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
        w = json.load(f)

    instrumente = _instrumente(w)
    reihen = {}
    for inst in instrumente:
        r = moondev_historie.lade_funding(inst)
        if r:
            reihen[inst] = r
    if not reihen:
        raise RuntimeError("keine Funding-Reihen fuer %s - erst "
                           "'python moondev_historie.py --funding %s'"
                           % (spur, ",".join(instrumente)))

    # Das laengste Instrument gibt den Zeitraum vor; kurze Reihen fallen raus.
    # Der Grund gehoert in die Antwort: ein stillschweigend gekuerzter Lauf
    # sieht aus wie ein langer.
    # Nicht "irgendwie lang genug", sondern: so lang wie der laengste Lauf
    # hergibt. HYPE liefert erst ab 2025-05-30 (2924 Saetze gegen 6294) und
    # wuerde den ganzen Lauf auf 2,7 Jahre kuerzen. Solche Reihen fallen raus
    # und werden BENANNT - eine stillschweigend gekuerzte Messung sieht wie
    # eine lange aus.
    lang_grenze = 0.8 * max(len(r) for r in reihen.values())
    lang = {i: r for i, r in reihen.items() if len(r) >= lang_grenze}
    zu_kurz = sorted(set(reihen) - set(lang))
    if not lang:
        raise RuntimeError("keine Funding-Reihe mit ausreichender Laenge")

    von = von_ms or min(r[0][0] for r in lang.values())
    bis = bis_ms or max(r[-1][0] for r in lang.values())
    schritte = sorted({t for r in lang.values() for t, _ in r if von <= t <= bis})

    box = {"ts": schritte[0]}
    zustand = os.path.join(ordner, "zustand.json")
    journal = os.path.join(ordner, "handelsjournal.csv")
    modul.WACHEN = os.path.join(ordner, "wachen.json")
    modul.ZUSTAND = zustand
    modul.JOURNAL = journal
    namen = ("SCHREIBEN", "spiegeln", "funding_quelle", "zeit_quelle",
             "journal")
    alt = {n: getattr(modul, n, None) for n in namen}
    puffer = io.StringIO()
    kill_gesehen = False
    try:
        modul.SCHREIBEN = True                  # ins BACKTEST-Journal
        modul.spiegeln = lambda *a, **k: None
        modul.funding_quelle = lambda inst: moondev_historie.funding_dict(
            inst, box["ts"])
        # Ebenso der Ausstieg: die Zeile wird auf den BERUEHRTEN Kurs gezogen
        # (Regel oben). Die Kerze kommt erst auf Abruf - diese Spur rechnet
        # je Schritt EINEN Preis aus, ein Vorrat waere hier nur Last.
        if alt.get("journal"):
            modul.journal = Beruehrungsjournal(
                {}, alt["journal"],
                kerze_fuer=lambda i: _feed_kerze(i, box["ts"]))
        with contextlib.redirect_stdout(puffer if still else sys.stdout):
            for ts in schritte:
                box["ts"] = ts
                modul.zeit_quelle = lambda _t=ts: dt.datetime.fromtimestamp(
                    _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
                modul.lauf("papier")
                if "Kill-Schwelle" in puffer.getvalue():
                    kill_gesehen = True
    finally:
        for n, wert in alt.items():
            if wert is not None:
                setattr(modul, n, wert)
    k = kennzahlen(journal)
    runden = int(k.get("runden") or 0)
    if runden:
        je_runde = float(k.get("ergebnis_summe") or 0.0) / runden
        k["ergebnis_je_runde_pct"] = je_runde
        k["netto_je_runde_pct"] = je_runde - 2.0 * float(gebuehr_pct)
    k.update({"schritte": len(schritte), "takt": "%dh" % FUNDING_STUNDEN,
              "gebuehr_pct": float(gebuehr_pct),
              "instrumente": sorted(lang), "symbole_zu_kurz": zu_kurz,
              "kill_ausgeloest": kill_gesehen, "kerzenquelle": "binance"})
    return k, len(puffer.getvalue().splitlines())


def kerzenlaenge(spur, w=None):
    """Laenge der KUERZESTEN Reihe - so weit reicht ein Abschnitt.

    Der Walk laeuft ueber `min(len(k))`; der Optimierer muss seine Fenster
    deshalb an derselben Zahl ausrichten, sonst liegen die Fenster fuer ein
    Instrument ausserhalb der Reihe.
    """
    if w is None:
        w = wachen_von(spur)
    takt = _takt(w)
    return min((len(historie_binance.lade(i, takt)) for i in _instrumente(w)), default=0)


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
    # Gegenprobe zur Beruehrungsregel, aus dem Journal gelesen: ein
    # Ausstieg, der die Marke trifft, steht GENAU auf ihr.
    k.update(auf_der_marke(journal_pfad))
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
    """Nur EIN Weg je Aufruf: die Familien brauchen verschiedene Daten.

    Familie A rechnet Kerzen (und braucht die Fensterbreite), Familie B den
    Marktquerschnitt, Familie C die Funding-Reihen. Ein gemeinsamer Vorlauf
    waere der Fehler - `lade_wachen()` gibt es nur bei A und riss die beiden
    anderen mit (29.09.2026 geschehen).
    """
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
    ap.add_argument("--feed", action="store_true",
                    help="Feed-Spur ueber den Marktquerschnitt (Familie B)")
    ap.add_argument("--familie-c", action="store_true",
                    help="Spur mit eigenem lauf() (moondev_funding)")
    ap.add_argument("--takt", default="1D", choices=("1D", "1H"))
    ap.add_argument("--mindest-symbole", type=int, default=30,
                    help="ab so vielen Reihen zaehlt ein Zeitpunkt als Schritt")
    ap.add_argument("--setzen", action="append", default=None,
                    metavar="NAME=WERT",
                    help="Wert in der BACKTEST-Kopie der Wachen setzen "
                         "(mehrfach moeglich); die Wachen der Spur bleiben "
                         "unberuehrt, das Gesetzte steht als _backtest_gesetzt "
                         "in der Kopie")
    a = ap.parse_args()
    mk = a.max_kerzen
    if a.gegenprobe:
        print(json.dumps(gegenprobe(a.spur, a.gebuehr, a.lauf, mk),
                         indent=2, ensure_ascii=False))
        return
    if a.familie_c:
        k, zeilen = lauf_c(a.spur, gebuehr_fuer(a.spur), a.lauf,
                           setzen=setzen_aus(a.setzen))
        print(json.dumps({"spur": a.spur, "kennzahlen": k, "zeilen": zeilen},
                         indent=2, ensure_ascii=False))
        return
    if a.feed:
        k, zeilen = lauf_feed(a.spur, gebuehr_fuer(a.spur), a.lauf,
                              takt=a.takt, mindest_symbole=a.mindest_symbole,
                              setzen=setzen_aus(a.setzen))
        print(json.dumps({"spur": a.spur, "kennzahlen": k, "zeilen": zeilen},
                         indent=2, ensure_ascii=False))
        return
    # Erst hier: `lade_wachen` gibt es nur bei den Kerzen-Spuren (Familie A).
    fenster = None if a.ganz else a.fenster
    if fenster is None and not a.ganz:
        w = dict(spur_modul(a.spur).lade_wachen())
        fenster = fenster_vorgabe(w)
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
