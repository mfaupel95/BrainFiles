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

Familie D (mehrere Kerzenreihen bzw. eigene Rechnung der Spur):
    python replay.py --spur mosaic --lauf t294      # 4H/30M/5M aus der 5m-Basis
    python replay.py --spur gitter --lauf t295      # faehrt gitters walk()

Die Familie erkennt der Replay am SPURNAMEN - kein Schalter, der vergessen
werden kann. `mosaic` braucht die 5m-Historie (`python 5m_historie_holen.py`,
120 Tage); `gitter` faehrt auf der 1H-Reihe wie die Indikatorspuren.
"""

import bisect
import csv
import datetime as dt
import importlib.util
import itertools
import json
import os
import sys
import types

import historie_binance
import historie_okx

HIER = os.path.dirname(os.path.abspath(__file__))

def historie_ordner_fehlt():
    """True, wenn der Historie-Ordner auf dieser Kopie des Baums fehlt.

    `historie_binance.ORDNER` ist `HIER/daten/historie` - RELATIV zur
    Modulposition. Ein Worktree bekommt alle .py-Dateien, aber daten/ ist
    nicht versioniert (git check-ignore belegt, git ls-files leer). Eine
    Modulkopie ohne daten/ laedt dann still 0 Kerzen, und der Lauf meldet
    "0 Runden" - ein falsches Messergebnis, das aussieht wie ein Befund.

    Die Naht: kerzen_fuer() prueft das VOR dem Laden und wirft HistorieFehlt
    mit dem klaren Text "Historie fehlt - Ordner nicht da". Ein Test in einem
    Worktree sieht dann den Fehler, nicht die leere Rechnung.
    """
    return not os.path.isdir(historie_binance.ORDNER)



# Spuren mit eigenem Buch im Modul (Familie A).
#
# `orb` und `orbk` standen hier bis zum 01.10.2026 und waren doch nicht
# fahrbar: ihre `handeln.py` haben kein `lade_wachen()`, ihre `wachen.json`
# nennt die Instrumente als DICT mit BOERSENnamen (`BTC_USDT` -> `BTC-USDT-SWAP`)
# statt als Liste von Spur-Namen, und ohne `kerzen_takt`/`mindest_kerzen`. Ein
# Replay endet damit in der Verweigerung "die Spur nennt kein Instrument". Sie
# stehen jetzt unter NICHT_NACHRECHENBAR mit Grund - eine angebotene Taste, die
# nur scheitern kann, ist schlechter als eine fehlende. orbk hat ausserdem
# einen eigenen Backtest (`orbk/backtest.py`).
SPUREN_TEIL_A = ("squeeze", "wavetrend", "macd_mtf", "supertrend")
# mosaic und gitter standen hier bis 01.10.2026 und waren doch nicht fahrbar:
# ihre Fahrweise passt nicht in den einen Aufruf `pruefe_einstieg(inst, k, z,
# w, faktor)` / `pruefe_ausstiege(z, k, w)`. mosaic braucht DREI Kerzenreihen,
# gitter hat gar kein `pruefe_einstieg` (die Rechnung liegt in `walk()`). Seit
# dem 01.10.2026 fahren beide ueber den Familie-D-Weg weiter unten
# (MEHRZEITRAHMEN/EIGENE_RECHNUNG) - erkannt am SPURNAMEN, nicht an einem
# Schalter. `--spur mosaic` und `--spur gitter` laufen damit direkt.

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
                 "moondev_liquidation", "moondev_sentiment",
                 "klassik_sma", "klassik_ema", "klassik_macd",
                 "klassik_bollinger", "klassik_donchian", "klassik_rsi",
                 "klassik_rsi2", "klassik_donchian_trend")

# Spuren, die der Replay NICHT fahren kann. Zwei Gruende stehen hier, jeder
# mit seinem Grund daneben (das Leitstand-Fenster zeigt diese Liste im Klartext):
# eine historisch nicht beschaffbare Datenquelle - oder eine Spur, die gar
# nicht fahrbar ist (kein `lade_wachen()`, keine Kerzen-Naht).
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
    "nautilus": "Einstiege haengen an Quote-Ticks, die es nur live gibt",
    "nautilus_kraken": "Einstiege haengen an Quote-Ticks, die es nur live gibt",
    "nautilus_kraken_futures": "Einstiege haengen an Quote-Ticks",
    "scanner": "keine Kerzen-Naht (Kern-Spur, eigener Zyklus)",
    # xperp war hier bis 06.10.2026 - jetzt ueber Familie E fahrbar
    # (OKX-Kerzen ueber historie_okx, Signal ueber bot.py)
    "swap": "keine Kerzen-Naht (Kern-Spur, eigener Zyklus)",
    "kraken": "keine Kerzen-Naht (Kern-Spur, eigener Zyklus)",
    "spiegel": "ausser Betrieb seit 21.09.2026",
    "spiegel_knapp": "ausser Betrieb seit 21.09.2026",
    "spiegel_weit": "ausser Betrieb seit 21.09.2026",
    # Nicht fahrbar (kein Kerzenweg im Modul), nicht "Datenquelle fehlt":
    "orb": "kein lade_wachen() in orb/handeln.py - so nicht fahrbar (01.10.2026)",
    "orbk": "kein lade_wachen() in orbk/handeln.py; eigener Backtest: orbk/backtest.py",
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
    # Schattenarme teilen den Ordner mit dem Hauptbuch und tragen Suffix
    # (squeeze_eth -> wachen.eth.json). 04.10.2026: hier stand fest
    # `<spur>/wachen.json`; fuer einen Arm gibt es die Datei nicht, es wurde
    # das HAUPTbuch gerechnet und der Arm still mit des Haupts Zahlen
    # gemessen. Gesucht wird wie in spiegelstand/pruefe_ratschen: von rechts
    # kuerzen, bis eine Datei da ist.
    ordner = spur
    quelle = os.path.join(HIER, spur, "wachen.json")
    if not os.path.isfile(quelle) and "_" in spur:
        teile = spur.split("_")
        for i in range(len(teile) - 1, 0, -1):
            kandidat = os.path.join(HIER, ordner,
                                    "wachen.%s.json" % "_".join(teile[i:]))
            if os.path.isfile(kandidat):
                quelle = kandidat
                break
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


def kennung_fest():
    """Positionskennungen im Backtest reproduzierbar machen.

    Rueckgabe: eine Funktion, die die Naht wieder zurueckstellt.

    Der Zufallsteil von `pos_kennung` ist im BETRIEB richtig - zwei Positionen
    im selben Instrument entstehen in derselben Sekunde, die Zeit allein waere
    kein eindeutiger Schluessel. Im Backtest macht er zwei Laeufe ueber
    DIESELBEN Kerzen ungleich: das Journal war bis auf `pos_id` Byte fuer Byte
    identisch (gemessen 01.10.2026 an mosaic). Die Naht dafuer ist
    ausdruecklich vorgesehen (`pos_kennung.erzeuger`), und der Zaehler macht
    die Kennung im Lauf weiterhin eindeutig.
    """
    import pos_kennung
    alt = pos_kennung.erzeuger
    zaehler = itertools.count(1)

    def _neu(zeit=None):
        return "%s-%06x" % (pos_kennung._stempel(zeit), next(zaehler))

    pos_kennung.erzeuger = _neu

    def _zurueck():
        pos_kennung.erzeuger = alt

    return _zurueck


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


# Kerzen, die eine Reihe ZUSAETZLICH zur Anforderung der Spur tragen muss.
# Der Grund ist die Schleife in `lauf_a`: sie laeuft von `mindest_kerzen` bis
# ans Ende, mit genau `mindest_kerzen` Kerzen gaebe es also keinen einzigen
# Schritt - und ein Lauf ohne Schritt meldet "0 Runden", was wie ein
# Messergebnis aussieht.
KERZEN_PUFFER = 20


def bedarf(w):
    """Kerzen, die eine Reihe haben MUSS: mindest_kerzen + Puffer."""
    return int(w.get("mindest_kerzen", 300)) + KERZEN_PUFFER


def bedarf_fuer(spur):
    """`bedarf()` einer Spur - OHNE ihr Modul zu laden, aus ihrer wachen.json.

    Fuer das Leitstand-Fenster gedacht, das die Grenze schon beim Tippen nennen
    soll: ein Import der Spur (samt Indikatoren) waere dafuer zu schwer und
    truege Nebenwirkungen in den GUI-Prozess. None, wenn keine wachen.json
    da ist - dann prueft der Replay beim Lauf, und der verweigert mit Grund.

    Eine Mehrzeitrahmen-Spur braucht ein Vielfaches: `bedarf()` zaehlt die
    Kerzen JE REIHE, die 5m-Basis muss sie aber fuer die 4H-Reihe 48-mal
    tragen. Ohne diese Verzweigung nennte das Fenster eine Grenze, unter der
    der Lauf trotzdem abbricht.
    """
    try:
        with open(os.path.join(HIER, spur, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
    except (OSError, ValueError, TypeError):
        return None
    if spur in MEHRZEITRAHMEN:
        return bedarf_mehrzeitrahmen(MEHRZEITRAHMEN[spur], w)
    return bedarf(w)


class HistorieFehlt(RuntimeError):
    """Keine Kerzen fuer den Lauf - mit dem GRUND im Text.

    Zwei Gruende verlangen zwei verschiedene Taten und duerfen nicht denselben
    Satz bekommen: fehlt die Historie auf der PLATTE, hilft
    `historie_binance.py --auffuellen`; ist das verlangte FENSTER zu klein
    (`--max-kerzen` unter dem, was die Spur braucht), hilft nur ein groesseres
    Fenster - Nachfuellen aendert dort nichts.
    """


def mangel_text(spur, w, fehlen, zu_klein, max_kerzen=None):
    """Der eine Satz, der sagt, warum der Lauf keine Kerzen hat."""
    brauch = bedarf(w)
    quelle = ("die Spur braucht mindestens %d Kerzen je Reihe "
              "(mindest_kerzen %s + %d)"
              % (brauch, w.get("mindest_kerzen", 300), KERZEN_PUFFER))
    if not fehlen and not zu_klein:
        # Kein Instrument in der Liste: das passiert, wenn das Spurenmodul kein
        # `lade_wachen()` hat (dann ist `w` leer) oder ihre wachen.json kein
        # `instrumente`/`instrument` traegt. Nachfuellen hilft hier nicht, und
        # "0 Runden" waere die dritte Falschaussage.
        return ("Keine Kerzen fuer %s: die Spur nennt kein Instrument - "
                "entweder hat ihr handeln.py kein lade_wachen() oder ihre "
                "wachen.json kein instrumente/instrument. So ist sie nicht "
                "fahrbar" % spur)
    if fehlen and not zu_klein:
        return ("Historie fehlt oder ist zu kurz fuer %s: %s - %s, erst "
                "'python historie_binance.py --auffuellen'"
                % (spur, ", ".join(fehlen), quelle))
    if zu_klein and not fehlen:
        rat = ("Mit --max-kerzen %d oder mehr (0 = alle) wiederholen" % brauch
               if max_kerzen else
               "Der verlangte Abschnitt ist zu kurz - weniger weit einschneiden")
        return ("Fenster zu klein fuer %s: %s - %s. %s"
                % (spur, ", ".join(zu_klein), quelle, rat))
    return ("Keine Kerzen fuer %s - die Historie ist zu kurz (%s) UND das "
            "Fenster zu klein (%s): %s"
            % (spur, ", ".join(fehlen) or "-", ", ".join(zu_klein) or "-",
               quelle))


def kerzen_fuer(spur, w, bis_ms=None, max_kerzen=None, abschnitt=None):
    """{inst: [kerzen]} aus der eigenen Historie, aufsteigend.

    Fehlt eine Reihe, wird sie GEMELDET und das Instrument faellt aus dem Lauf
    - nie still durch ein anderes Instrument ersetzt. Bleibt KEINE Reihe
    uebrig, wirft die Funktion `HistorieFehlt` mit dem Grund im Text (Historie
    zu kurz ODER verlangtes Fenster zu klein) - ein leerer Rueckgabewert waere
    ein Lauf mit 0 Runden und damit ein falsches Messergebnis.

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
    # T-368: Worktree-Blindheit - fehlt der Ordner, ist jede Reihe leer.
    # Ohne diese Pruefung laeuft der Lauf mit 0 Runden durch und meldet
    # ein falsches Messergebnis. HistorieFehlt zwingt den Aufrufer, die
    # Historie nachzuladen oder den Lauf abzubrechen.
    if historie_ordner_fehlt():
        raise HistorieFehlt(
            "Historie fehlt - Ordner %s nicht da. "
            "Diese Kopie des Baums hat kein daten/ (Worktree?). "
            "Erst 'python historie_binance.py --auffuellen'."
            % historie_binance.ORDNER)

    insts = _instrumente(w)
    takt = _takt(w)
    brauch = bedarf(w)
    aus, fehlen, zu_klein = {}, [], []
    for inst in insts:
        reihen = lade_reihen(inst, takt)
        # Die Laenge auf der PLATTE entscheidet, ob die Historie fehlt - erst
        # danach schneiden `bis_ms`, `abschnitt` und `max_kerzen`. Andersherum
        # gelesen entsteht ein falscher Befund: mit `--max-kerzen 200` blieben
        # 200 Kerzen uebrig, die Pruefung schlug an, und der Lauf meldete
        # "keine Historie fuer supertrend - erst auffuellen", waehrend 12.559
        # Kerzen auf der Platte lagen und nur das FENSTER zu klein war
        # (gemessen 01.10.2026). Der Leser folgt sonst einer Anweisung, die
        # nichts aendert.
        gehabt = len(reihen)
        if bis_ms:
            reihen = [r for r in reihen if r[0] <= bis_ms]
        if abschnitt:
            von, bis = abschnitt
            reihen = reihen[int(von):int(bis)]
        if max_kerzen:
            reihen = reihen[-int(max_kerzen):]
        if gehabt < brauch:
            fehlen.append("%s (%d Kerzen)" % (inst, gehabt))
            continue
        if len(reihen) < brauch:
            zu_klein.append("%s (%d Kerzen)" % (inst, len(reihen)))
            continue
        aus[inst] = reihen
    if fehlen:
        print("  ohne Historie: %s" % ", ".join(fehlen))
    if zu_klein:
        print("  Fenster zu klein: %s" % ", ".join(zu_klein))
    if not aus:
        # Kein stiller Rueckfall auf ein anderes Instrument und kein leerer
        # Lauf: wer 0 Runden sieht, haelt es sonst fuer ein Messergebnis.
        raise HistorieFehlt(mangel_text(spur, w, fehlen, zu_klein, max_kerzen))
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
        #
        # Jede Zeile traegt ihre `pos_id` mit. Die REIHENFOLGE allein genuegte
        # nicht: die Spuren schreiben erst die schlussgetriggerten Ausstiege
        # (`pruefe_ausstiege`) und danach die Docht-Ausstiege, waehrend die
        # Runde in der BUCHREIHENFOLGE gebucht wird. Steht im Buch eine
        # Docht-Position vorn, bekam sie den Stop-Kurs der Schluss-Position.
        # Gemessen 04.10.2026 an squeeze (1200 Kerzen): die Runden 17 und 18
        # tauschten ihre Kurse (BTC short bekam das Ziel, BTC long den Stop).
        self.marke_je_inst = {}

    def schritt_anfang(self):
        """Die Warteschlangen leeren - EINMAL je Kerzenschritt."""
        self.marke_je_inst.clear()

    def nimm_marke(self, inst, pos_id=None):
        """Der Kurs der Markenzeile dieser Position, sonst der naechste.

        Mit `pos_id` wird die Zeile der Position geholt, nicht einfach die
        naechste - die Reihenfolge im Journal ist die des SCHLUSS-Wegs, die
        gebuchte Reihenfolge die des BUCHS. Ohne `pos_id` (Aufrufer, die keine
        Kennung fuehren) bleibt die Warteschlange in Zeilenreihenfolge.
        """
        w = self.marke_je_inst.get(inst)
        if not w:
            return None
        if pos_id:
            for i, (kennung, _kurs) in enumerate(w):
                if kennung == pos_id:
                    return w.pop(i)[1]
            return None
        return w.pop(0)[1]

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
        self.marke_je_inst.setdefault(f.get("inst"), []).append(
            (str(f.get("pos_id") or ""), kurs))
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


def docht_beruehrung_ohne_schluss(kerze, seite, stop, ziel):
    """Zaehlernebennachfrage (T-202): Hat diese Kerze eine Marke NUR mit dem
    Docht beruehrt und darueber geschlossen - also ohne dass der Schluss
    jenseits der Marke stand?

    Das ist gerade NICHT der Fall eines Ausstiegs: der Ausloeser bleibt der
    Kerzenschluss. Eine Kerze, die eine Marke nur mit dem Docht streift (ihr
    Hoch/Tief die Marke kreuzt) und zurueckschlaegt, loest weiterhin nichts
    aus. Diese Funktion zaehlt genau diesen Fall als Messung - ein Ausstieg
    am Docht waere der naechste Schritt, macht die Zahlen aber strenger und
    weicht vom Live-Verhalten ab (Entscheidung Max, siehe TASKS.md T-202).

    Rueckgabe True, wenn die Kerze eine Marke nur mit dem Docht beruehrt hat
    (Hoch/Tief), der Schluss aber NICHT jenseits der Marke steht. False sonst
    (keine Beruehrung, oder die Kerze hat sie mit dem Schluss beruehrt).

    `kerze` ist eine Binance-Reihe [ts, o, h, l, c, v]; `seite` ist
    "long"/"short"; `stop` und `ziel` die Marken als Zahlen.
    """
    if not kerze or len(kerze) < 5:
        return False
    seite = str(seite or "").strip().lower()
    if seite not in ("long", "short"):
        return False
    hoch, tief, schluss = (_zahl(kerze[2]), _zahl(kerze[3]),
                           _zahl(kerze[4]))
    stop, ziel = _zahl(stop), _zahl(ziel)
    if None in (hoch, tief, schluss, stop, ziel):
        return False
    if seite == "long":
        # Stop unter dem Einstieg: Docht-Tief streift den Stop, Schluss darueber.
        if tief <= stop:
            return schluss > stop
        if hoch >= ziel:
            return schluss < ziel
    else:
        if hoch >= stop:
            return schluss < stop
        if tief <= ziel:
            return schluss > ziel
    return False


def docht_ausstiege_anwenden(z, kerze, inst, huelle, zeit):
    """T-202: Positionen schliessen, deren Marke NUR am Docht beruehrt wurde.

    Der Ausloeser der Spuren ist der Kerzenschluss (`pruefe_ausstiege` prueft
    `k[-1][4]`). Eine Kerze, die eine Marke nur mit dem Docht streift (Hoch/Tief
    kreuzt die Marke) und darueber schliesst, loest dort nichts aus. Diese
    Funktion schliesst genau diese Positionen NACH `pruefe_ausstiege` - der
    Replay bildet damit den Docht-Ausstieg ab, ohne die Spur anzufassen.

    Der Ausstieg geschieht am KURS DER MARKE (wie die Beruehrungsregel T-177),
    nicht am Kerzenschluss. Die Journalzeile geht durch die Huelle, damit sie
    dieselbe Berichtigung bekommt wie jeder andere Markenausstieg.

    Rueckgabe: die Zahl der so geschlossenen Positionen.
    """
    geschlossen = 0
    behalten = []
    for p in z.get("positionen", []):
        if p.get("inst") != inst:
            behalten.append(p)
            continue
        marke = beruehrte_marke(kerze, p.get("seite"), p.get("stop"),
                                p.get("ziel"))
        if marke is None:
            behalten.append(p)
            continue
        # Nur der reine Docht-Fall: die Marke ist beruehrt, aber der Schluss
        # steht NICHT jenseits der Marke (sonst haette pruefe_ausstiege schon
        # geschlossen).
        if not docht_beruehrung_ohne_schluss(kerze, p.get("seite"),
                                             p.get("stop"), p.get("ziel")):
            behalten.append(p)
            continue
        kurs = round(_zahl(p.get("stop")) if marke == "stop"
                     else _zahl(p.get("ziel")), 6)
        vz = 1 if p.get("seite") == "long" else -1
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        erloes = p["nominal"] + gv
        # Die pos_id MUSS mit auf die Zeile: der Prognose-Backtest paart die
        # berichtigten Kurse ueber `nimm_marke(inst)` in der REIHENFOLGE der
        # Zeilen. Eine Zeile ohne Kennung war die Ursache der vertauschten
        # Ausstiege (gemessen 04.10.2026, squeeze, 1200 Kerzen: die Runden 17
        # und 18 tauschten ihre Kurse, weil die Docht-Zeile als Position ohne
        # `pos_id` aufkam und die FIFO-Reihenfolge nicht mehr zum Buch passte).
        huelle(zeit=zeit, modus="papier", aktion="verkauf", inst=inst,
               pos_id=p.get("pos_id", ""),
               seite=p.get("seite"), preis=_preis_text(kurs, "%.6f" % kurs),
               einsatz_usd="%.2f" % erloes, stop="%.6f" % p.get("stop"),
               ziel="%.6f" % p.get("ziel"),
               stop_pct="%.2f" % p.get("stop_pct", 0.0), grund=marke)
        geschlossen += 1
    z["positionen"] = behalten
    return geschlossen


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
    # Der Grund der Verweigerung kommt aus `kerzen_fuer` (Historie fehlt oder
    # Fenster zu klein) - hier keinen zweiten, schwaecheren Text daneben.
    kerzen = kerzen_fuer(spur, w, bis_ms, max_kerzen, abschnitt)
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
    zurueck_kennung = kennung_fest()
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
            docht_ausstiege_anwenden(
                z, k[-1], inst, huelle,
                dt.datetime.fromtimestamp(
                    ts_schritt / 1000.0, dt.timezone.utc)
                .isoformat(timespec="seconds"))
            _ausstiege_buchen(offen, runden, vorher, z, k[-1],
                              gebuehr_pct, inst)
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
    zurueck_kennung()
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
    "macd_mtf": "okx_spot", "supertrend": "okx_spot",
    # gitter stand hier bis 01.10.2026 falsch: es handelt BTC-USDT auf dem
    # OKX-SPOT (seine eigene wachen.json sagt es, und seine _kosten nennen
    # 0,1 %), bekam als Perp-Spur aber nur den halben Satz gerechnet.
    "gitter": "okx_spot", "iv_wand": "okx_spot",
    "moondev_topmovers": "okx_spot", "moondev_listingarb": "okx_spot",
    # OKX Perp/Swap und Deribit
    "liq_wand": "okx_perp", "trendwende_btc": "okx_perp",
    "swap": "okx_perp", "xperp": "okx_perp", "iv_waelle": "okx_perp",
    # orb handelt BTC-USDT-SWAP / ETH-USDT-SWAP (Perp), stand hier falsch
    # unter okx_spot - der eigene Wert (0.0005) hat Vorrang, die Zuordnung
    # greift nur, wenn kein Feld da ist.
    "orb": "okx_perp",
    "moondev_funding": "okx_perp", "moondev_whale": "okx_perp",
    "moondev_liquidation": "okx_perp", "moondev_sentiment": "okx_perp",
    "moondev_signalwelle": "okx_perp", "moondev_sniper": "okx_perp",
    "klassik_sma": "okx_perp", "klassik_ema": "okx_perp",
    "klassik_macd": "okx_perp", "klassik_bollinger": "okx_perp",
    "klassik_donchian": "okx_perp", "klassik_rsi": "okx_perp",
    "klassik_rsi2": "okx_perp", "klassik_donchian_trend": "okx_perp",
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
            reihen = [r for r in lade_reihen(inst, _takt(w))
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
    alle = {i: lade_reihen(i, takt) for i in _instrumente(w)
            if lade_reihen(i, takt)}
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

    # Dieselbe Lehre wie in `kerzen_fuer`, hier fuer Familie B: die Schleife
    # unten laeuft von `mindest_kerzen` bis ans Ende - ein Fenster unter dem,
    # was die Spur braucht, laesst sie LEER laufen und der Lauf meldet
    # "0 Runden". Das sieht wie ein Messergebnis aus und ist keins.
    laenge = min(len(k) for k in alle.values())
    if laenge < bedarf(w):
        zu_klein = ["%s (%d Kerzen)" % (i, len(k)) for i, k in alle.items()]
        raise HistorieFehlt(mangel_text(spur, w, [], zu_klein, max_kerzen))

    alt_schreiben, alt_zeit = spur_buch.SCHREIBEN, spur_buch.zeit_quelle
    alt_spiegeln, alt_lauf = spur_buch.spiegeln, ereignis.lauf
    alt_journal = spur_buch.journal
    alt_risiko = os.environ.pop("HANDEL_RISIKO", None)
    zugriff = {"bis_ms": 0, "fenster": fenster, "kerzen": {}}
    quelle = historische_quelle(modul, spur, zugriff)
    puffer = io.StringIO()
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
    # 04.10.2026 - Befund, kein Wunsch: `trigger_modus: "signal"` (eingefuehrt
    # am 03.10.2026, Auftrag Max "weniger handeln") stellt in `spur_buch.zyklus`
    # JEDES Signal in eine Queue und bucht dann `continue` - es entsteht
    # bewusst keine Position. Im Betrieb ist das richtig: der signal-executor
    # (Hermes-Cron) setzt den Einstieg. Ein Backtest hat keinen Executor.
    # `lauf_feed` las die Wachen unveraendert, also konnte jede Feed-Spur
    # strukturell nie buchen und jede daraus gezogene Runden-Zahl war 0.
    #
    # Die Regel, die hier gilt: EIN Signal-Wechsel ist ein EREIGNIS der Serie,
    # kein Zustand des Momentan. In der Serie wird beim ersten Auftreten einer
    # Richtung eingestiegen (das ist genau der Wechsel, den das Gatter im
    # Betrieb ausloest) - nicht bei jedem Zyklus erneut. Deshalb wird das
    # Feld aus der BACKTEST-Wachen-Datei entfernt, nicht nur aus einer lokalen
    # Kopie: `spur_buch.zyklus` laedt die Wachen selbst aus der Datei
    # (`lade_wachen(wachen_pfad)`), ein `w.pop` auf eine fluechtige Variable
    # waere wirkungslos. Wer die Queue-Logik im Backtest will, braucht eine
    # eigene Kennzahl; die Rundenzahl ist eine andere Frage.
    _bt_wachen = os.path.join(ordner, "wachen.json")
    with open(_bt_wachen, encoding="utf-8") as f:
        w = json.load(f)
    if w.pop("trigger_modus", None):
        w["_backtest_trigger_entfernt"] = (
            "trigger_modus 'signal' im Backtest entfernt: im Betrieb stellt das "
            "Gatter jedes Signal in die Queue und bucht nie, ein Backtest hat "
            "keinen signal-executor (04.10.2026)")
        with open(_bt_wachen, "w", encoding="utf-8") as f:
            json.dump(w, f, indent=2, ensure_ascii=False)
            f.write("\n")
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


# --- Familie D: mehrere Kerzenreihen oder eine eigene Rechnung --------------
#
# Zwei Spuren liessen sich bis 01.10.2026 nicht nachrechnen - beide aus
# demselben Grund: ihre Fahrweise passt nicht in den EINEN Aufruf
# `pruefe_einstieg(inst, k, z, w, faktor)` / `pruefe_ausstiege(z, k, w)`.
#
#   mosaic  braucht DREI Kerzenreihen (4H/30M/5M). Mit fuenf Argumenten riss
#           der Aufruf beim ersten Einstieg mit TypeError ab.
#   gitter  hat gar kein `pruefe_einstieg`: seine Rechnung liegt in `walk()`
#           (Leiter, Stufen, Kaeufe/Verkaeufe) - `handeln.py` kennt nur
#           `lade_wachen()`.
#
# Auch hier entscheidet die SPUR; der Replay liefert nur Zeit und Daten.
# Nichts wird nachgebaut.

# Kerzendauer der Takte, die `historie_binance.TAKTE` kennt.
MS_JE_TAKT = {"5M": 300_000, "15M": 900_000, "30M": 1_800_000,
              "1H": 3_600_000, "4H": 14_400_000, "1D": 86_400_000}

# Spuren mit mehreren Kerzenreihen. Die Reihen kommen aus EINER Basisreihe und
# werden auf dieselbe Zeitachse verdichtet - kein Versatz, keine zweite
# Datenquelle.
#
# Eine groebere Kerze zaehlt erst, wenn sie ABGESCHLOSSEN ist. Waere die
# laufende 4H-Kerze dabei, saehe der Backtest den Rest der Stunde, den die Spur
# live noch nicht kennt - ein Blick in die Zukunft, und er entwertet jede
# Kennzahl darauf.
MEHRZEITRAHMEN = {
    "mosaic": {
        "basis": "5M",
        "reihen": (("k4", "4H"), ("k30", "30M"), ("k5", "5M")),
        # Argumentordnung von pruefe_einstieg NACH `inst`
        # (mosaic/handeln.py: pruefe_einstieg(inst, k4, k30, k5, z, w, faktor)).
        "einstieg": ("k4", "k30", "k5"),
        # pruefe_ausstiege bekommt genau EINE Reihe (mosaic/handeln.py).
        "ausstieg": "k5",
    },
}

# Spuren, die ihre Rechnung SELBST mitbringen (`walk()`), aber keine
# pruefe_einstieg/-ausstiege haben.
EIGENE_RECHNUNG = ("gitter",)

# Raster der Boerse fuer gitter. Der Replay darf keine Boerse fragen; die
# Zahlen sind dieselben, die gitter/backtest_gitter.py fuer seinen Lauf
# benutzt (dort INST, Zeile 29).
GITTER_RASTER = {"BTC-USDT": {"instId": "BTC-USDT", "tickSz": 0.1,
                              "lotSz": 0.00000001, "minSz": 0.00001}}


def _marken_der_position(p, e):
    """Die MARKEN, die in diesem Schritt gelten - der LEBENDE Stand vor `e`.

    `skalieren.skaliere()` rechnet Stop und Ziel auf der Position selbst um
    (es mutiert das Dict im Buch) und schreibt die neuen Werte in die
    Kauftzeile des Journals. Der Eintrag in `offen` ist dagegen eine KOPIE vom
    Einstiegsschritt; bei einer spaeteren Skalierung blieb sie stehen.

    Gemessen am 04.10.2026 an squeeze (Fenster 700, 1200 Kerzen): 7 von 25
    Runden trugen die veraltete Marke, zwei davon ueberhaupt keine - die Kerze
    beruehrte die aktuelle Marke, nicht die Snapshot-Marke, also fiel
    `_ausstiege_buchen` auf den Kerzenschluss zurueck. `backtest_prognose`
    bucht dieselben Runden ueber das JOURNAL, das die aktuellen Marken traegt -
    daher die Gegenprobe "Rundenzahl/Bruttowerte weichen ab".

    Nur die MARKEN kommen von hier. Einstieg und Nominal bleiben der Snapshot:
    die Rechnung dieser Runde gehoert zum Ausstiegsschritt, und ein Umstellen
    des Einstiegs waere eine eigene (betrachtete) Entscheidung ueber die
    Bruttowerte - nicht die Korrektur, die hier auf dem Tisch liegt.
    """
    if not isinstance(p, dict):
        return e
    aus = dict(e)
    for feld in ("stop", "ziel"):
        wert = p.get(feld)
        if wert is not None:
            aus[feld] = wert
    return aus


def _ausstiege_buchen(offen, runden, vorher, z, kerze, gebuehr_pct, inst):
    """Ausgestiegene Positionen als Runde buchen - EINE Stelle fuer beide Wege.

    `vorher` ist das Buch VOR dem Ausstiegsaufruf ({id(position): position}),
    `kerze` die Kerze dieses Schritts. Der Ausstieg geschieht am KURS DER
    MARKE (Stop bzw. Ziel), nicht am Kerzenschluss - ohne Marke in der Kerze
    bleibt es beim Schluss. Die Marke ist der Stand der Position im
    Ausstiegsschritt (`_marken_der_position`), nicht der vom Einstieg.
    """
    nachher = {id(p) for p in z["positionen"]}
    for pid, p in vorher.items():
        if pid in nachher or pid not in offen:
            continue
        e = _marken_der_position(p, offen.pop(pid))
        kurs = kurs_der_marke(kerze, e["seite"], e["stop"], e["ziel"])
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
            "ein_ts": e["ts"], "aus_ts": kerze[0],
            "stunden": (kerze[0] - e["ts"]) / 3600000.0})


def verdichten(basis, takt):
    """Groebere Kerzen aus der Basisreihe: [start_ts, o, h, t, c, v]."""
    dauer = MS_JE_TAKT[takt]
    aus = []
    for r in basis:
        b = (int(r[0]) // dauer) * dauer
        if aus and aus[-1][0] == b:
            k = aus[-1]
            if r[2] > k[2]:
                k[2] = r[2]
            if r[3] < k[3]:
                k[3] = r[3]
            k[4] = r[4]
            k[5] = k[5] + r[5]
        else:
            aus.append([b, r[1], r[2], r[3], r[4], r[5]])
    return aus


def bedarf_mehrzeitrahmen(spec, w):
    """Basis-Kerzen, die noetig sind - die groebere Reihe bestimmt sie.

    mosaic sieht je Reihe `mindest_kerzen` Kerzen; fuer 300 4H-Kerzen braucht
    die 5m-Basis 300 x 48. Wer hier nur `bedarf()` fragt, laesst den Lauf mit
    halb gefuellten 4H-Reihen starten - und mosaic rechnet dann auf einem
    Zustand, den es im Betrieb nie gibt.
    """
    grund = int(w.get("mindest_kerzen", 300)) + KERZEN_PUFFER
    faktor = max(MS_JE_TAKT[t] // MS_JE_TAKT[spec["basis"]]
                 for _n, t in spec["reihen"])
    return grund * max(1, faktor)


def kerzen_mehrzeitrahmen(spur, spec, w, bis_ms=None, max_kerzen=None):
    """{inst: basisreihe} - dieselbe Pruefung wie `kerzen_fuer`, andere Basis."""
    insts = _instrumente(w)
    brauch = bedarf_mehrzeitrahmen(spec, w)
    aus, fehlen, zu_klein = {}, [], []
    for inst in insts:
        reihen = lade_reihen(inst, spec["basis"])
        gehabt = len(reihen)
        if bis_ms:
            reihen = [r for r in reihen if r[0] <= bis_ms]
        if max_kerzen:
            reihen = reihen[-int(max_kerzen):]
        if gehabt < brauch:
            fehlen.append("%s (%d Kerzen)" % (inst, gehabt))
            continue
        if len(reihen) < brauch:
            zu_klein.append("%s (%d Kerzen)" % (inst, len(reihen)))
            continue
        aus[inst] = reihen
    if fehlen:
        print("  ohne Historie: %s" % ", ".join(fehlen))
    if zu_klein:
        print("  Fenster zu klein: %s" % ", ".join(zu_klein))
    if not aus:
        raise HistorieFehlt(
            "Historie fehlt oder ist zu kurz fuer %s: %s - die Spur braucht "
            "%d Kerzen der %s-Basis (mindest_kerzen %s je Reihe, die groebere "
            "Reihe bestimmt den Faktor). Erst nachladen: "
            "'python historie_binance.py --auffuellen --takte %s'"
            % (spur, ", ".join(fehlen + zu_klein) or "-", brauch,
               spec["basis"], w.get("mindest_kerzen", 300), spec["basis"]))
    return aus


def lauf_mehrzeitrahmen(spur, gebuehr_pct, lauf, bis_ms=None, max_kerzen=None,
                        wachen_patch=None, fenster=None):
    """Familie D, Fall 1: die Spur sieht MEHRERE Kerzenreihen je Schritt.

    Rueckgabe wie `lauf_a`: (runden, Zahl der offenen Positionen).
    """
    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf)
    schuetze(modul, ordner)
    spec = MEHRZEITRAHMEN[spur]
    w = dict(modul.lade_wachen()) if hasattr(modul, "lade_wachen") else {}
    if wachen_patch:
        w.update(wachen_patch)
    if fenster is None:
        fenster = int(w.get("mindest_kerzen", 300))
    kerzen = kerzen_mehrzeitrahmen(spur, spec, w, bis_ms, max_kerzen)

    verdichtet, starts = {}, {}
    for _name, takt in spec["reihen"]:
        if takt == spec["basis"]:
            continue
        verdichtet[takt] = {i: verdichten(r, takt) for i, r in kerzen.items()}
        starts[takt] = {i: [k[0] for k in v]
                        for i, v in verdichtet[takt].items()}

    runden, offen, gesammelt = [], {}, []
    zustand_ts = {"ts": None}
    kerzen_jetzt = {}
    huelle = Beruehrungsjournal(
        kerzen_jetzt,
        lambda **f: gesammelt.append(dict(f, _kerzen_ts=zustand_ts["ts"])))
    modul.journal = huelle
    zurueck_kennung = kennung_fest()
    alt_zeit = getattr(modul, "zeit_quelle", None)
    hat_zeit = hasattr(modul, "zeit_quelle")
    z = {"positionen": [], "modus": "papier", "letzter_lauf": None,
         "verluste_usd": 0.0}

    for inst, basis in kerzen.items():
        zeitachse = [b[0] for b in basis]
        # Erster Schritt: erst wenn JEDE Reihe `fenster` Kerzen hat.
        beginn = fenster - 1
        for _name, takt in spec["reihen"]:
            if takt == spec["basis"]:
                continue
            st = starts[takt][inst]
            if len(st) < fenster:
                raise HistorieFehlt(
                    "Reihe %s zu kurz fuer %s: %d statt %d Kerzen - "
                    "Historie nachladen" % (takt, spur, len(st), fenster))
            grenze = st[fenster - 1] + MS_JE_TAKT[takt]
            beginn = max(beginn, bisect.bisect_left(zeitachse, grenze))
        for i in range(beginn, len(basis)):
            ts = basis[i][0]
            zustand_ts["ts"] = ts
            if hat_zeit:
                modul.zeit_quelle = lambda _t=ts: dt.datetime.fromtimestamp(
                    _t / 1000.0, dt.timezone.utc).isoformat(timespec="seconds")
            jetzt = {}
            for name, takt in spec["reihen"]:
                if takt == spec["basis"]:
                    jetzt[name] = basis[max(0, i + 1 - fenster):i + 1]
                else:
                    n = bisect.bisect_right(starts[takt][inst],
                                            ts - MS_JE_TAKT[takt])
                    jetzt[name] = verdichtet[takt][inst][max(0, n - fenster):n]
            kerzen_jetzt[inst] = jetzt[spec["ausstieg"]][-1]
            vorher = {id(p): p for p in z["positionen"]}
            modul.pruefe_ausstiege(z, jetzt[spec["ausstieg"]], w, nur=inst)
            _ausstiege_buchen(offen, runden, vorher, z,
                              jetzt[spec["ausstieg"]][-1], gebuehr_pct, inst)
            vor_ids = {id(p) for p in z["positionen"]}
            modul.pruefe_einstieg(
                inst, *[jetzt[n] for n in spec["einstieg"]], z, w, 1.0)
            for p in z["positionen"]:
                if id(p) not in vor_ids:
                    offen[id(p)] = {"seite": p["seite"],
                                    "einstieg": p["einstieg"],
                                    "nominal": p["nominal"],
                                    "stop_pct": p.get("stop_pct", 0.0),
                                    "stop": p.get("stop"),
                                    "ziel": p.get("ziel"),
                                    "ts": jetzt[spec["ausstieg"]][-1][0]}
    if hat_zeit:
        modul.zeit_quelle = alt_zeit
    zurueck_kennung()
    _journal_schreiben(ordner, gesammelt)
    return runden, len(z["positionen"])


def _gitter_zustand(modul, kurs, w, inst):
    """Zustand mit gebauter Leiter - die Struktur, die `walk()` erwartet.

    Wortgleich zu gitter/backtest_gitter.py::leiter_zustand; nur das Raster
    kommt aus GITTER_RASTER statt aus einer festen Konstanten.
    """
    raster = dict(GITTER_RASTER.get(inst, GITTER_RASTER["BTC-USDT"]))
    raster["instId"] = inst
    leiter = modul.leiter_bauen(kurs, w, raster)
    einsatz = float(w.get("einsatz_usd", 1000.0))
    return {
        "instrument": inst, "modus": "backtest",
        "kasse_usd": einsatz, "startwert_usd": einsatz,
        "leiter": {k: leiter[k] for k in ("unten", "oben", "stufen", "preise",
                                          "mengen", "zustand",
                                          "schritt_prozent",
                                          "einsatz_in_orders",
                                          "stufen_ohne_menge")},
        "lose": {}, "kaeufe": 0, "verkaeufe": 0, "zyklen": 0,
        "gw_usd": 0.0, "verluste_usd": 0.0, "bestand": 0.0,
        "letzte_kerze_ts": -1, "letzter_kurs": None,
    }


def lauf_eigene_rechnung(spur, gebuehr_pct, lauf, bis_ms=None, max_kerzen=None,
                         wachen_patch=None):
    """Familie D, Fall 2: die Spur bringt ihr eigenes `walk()` mit (gitter).

    Der Replay liefert Kerzen und Uhr; entschieden und gebucht wird in der
    Spur. `walk()` laeuft je KERZE einmal (nicht einmal ueber alles): nur so
    laesst sich die Uhr vor jeden Schritt setzen, und das Journal ist
    reproduzierbar statt von der Wanduhr abhaengig.

    Rueckgabe: Kennzahlen des Gitters (dieselben Groessen wie
    gitter/backtest_gitter.py) - `kosten_wendepunkt` kann dieses Journal NICHT
    auswerten, weil eine Gitterstufe keinen Stop und kein Ziel hat.
    """
    modul = spur_modul(spur)
    ordner = buch_ordner(spur, lauf)
    schuetze(modul, ordner)
    w = wachen_von(spur)
    if wachen_patch:
        w.update(wachen_patch)
    # Der Gebuehrensatz des Replays gilt; die Slippage bleibt die der Spur
    # (sie ist eine Annahme der Spur, kein Messwert des Replays).
    w["gebuehr_pct"] = float(gebuehr_pct)
    kerzen = kerzen_fuer(spur, w, bis_ms, max_kerzen)

    gesammelt = []
    uhr = {"ts": 0}
    zustand_ts = {"ts": None}

    def _journal(**f):
        gesammelt.append(dict(f, _kerzen_ts=uhr["ts"]))

    modul.journal = _journal
    alt_jetzt = modul._jetzt
    alt_raster = modul.instrument_quelle
    modul._jetzt = lambda: dt.datetime.fromtimestamp(uhr["ts"] / 1000.0,
                                                     dt.timezone.utc)
    modul.instrument_quelle = lambda inst: dict(
        GITTER_RASTER.get(inst, GITTER_RASTER["BTC-USDT"]))
    fkauf, _fverkauf = modul.kostenfaktoren(w)
    takt = _takt(w)

    zahlen = {"kaeufe": 0, "verkaeufe": 0, "zyklen": 0, "gw_usd": 0.0,
              "kerzen": 0, "verluste_usd": 0.0, "buchwert": 0.0,
              "einsatz": float(w.get("einsatz_usd", 1000.0)),
              "start": None, "ende": None, "offen": 0, "stufen": None,
              "schritt_pct": None}
    try:
        for inst, reihen in kerzen.items():
            z = _gitter_zustand(modul, reihen[0][4], w, inst)
            for k in reihen:
                uhr["ts"] = k[0]
                zustand_ts["ts"] = k[0]
                _z, za = modul.walk(z, [k], w, takt)
                for feld in ("kaeufe", "verkaeufe", "zyklen", "kerzen"):
                    zahlen[feld] += za[feld]
                zahlen["gw_usd"] += za["gw_usd"]
            zahlen["offen"] += len(z.get("lose") or {})
            zahlen["verluste_usd"] += float(z.get("verluste_usd", 0.0))
            zahlen["buchwert"] += modul.buchwert(z, reihen[-1][4])
            if zahlen["start"] is None:
                zahlen["start"] = reihen[0][4]
                zahlen["stufen"] = z["leiter"]["stufen"]
                zahlen["schritt_pct"] = z["leiter"]["schritt_prozent"]
            zahlen["ende"] = reihen[-1][4]
    finally:
        modul._jetzt = alt_jetzt
        modul.instrument_quelle = alt_raster
    _journal_schreiben(ordner, gesammelt)

    ein = zahlen.pop("einsatz")
    buch = zahlen["buchwert"]
    zahlen["runden"] = zahlen["zyklen"]
    zahlen["ergebnis"] = buch - ein
    zahlen["rendite_pct"] = (buch / ein - 1) * 100.0 if ein else 0.0
    zahlen["halten_pct"] = ((zahlen["ende"] / zahlen["start"] - 1) * 100.0
                            if zahlen["start"] else 0.0)
    zahlen["gebuehr_pct"] = float(gebuehr_pct)
    zahlen["slippage_pct"] = float(w.get("slippage_pct", 0.0))
    zahlen["kerzenquelle"] = "binance"
    zahlen["journalzeilen"] = len(gesammelt)
    return zahlen


def lade_reihen(inst, takt):
    """lade_reihen() mit DEUTBARER Ausnahme.

    Seit dem 05.10.2026 wirft `lade()` bei einer vorhandenen, aber unlesbaren
    Datei `HistorieKaputt` statt still `[]` zurueck zu geben. Das ist richtig
    (leere Kerzen als "keine Historie" ist eine Falschaussage), aber es
    braucht eine Stelle, an der der Replay sie in seine eigene Sprache
    uebersetzt: "die Historie fehlt - erst auffuellen" ist eine AKTION fuer
    den Menschen, "die Datei wird gerade geschrieben" ist KEINE.

    Deshalb EIN Aufrufer hier im Replay-Modul, und jeder Aufrufer im Haus
    ruft das hier auf, nicht `lade_reihen()` direkt.
    """
    try:
        return historie_binance.lade(inst, takt)
    except historie_binance.HistorieKaputt as e:
        raise RuntimeError(
            "Historie unlesbar fuer %s/%s: %s - laeuft der Nachfueller "
            "(historie_binance.py --auffuellen)? Das ist KEIN 'Historie fehlt'."
            % (inst, takt, e)) from e


def lade_reihen_okx(inst, takt):
    """OKX-Kerzen fuer Familie E (xperp) - dieselbe Ausnahme wie lade_reihen.

    historie_okx.lade() liefert [] bei fehlender Datei, aber wirft
    HistorieKaputt bei unlesbarer Datei. Beide Faelle werden hier in die
    Sprache des Replays uebersetzt.
    """
    try:
        return historie_okx.lade(inst, takt)
    except historie_okx.HistorieKaputt as e:
        raise RuntimeError(
            "Historie unlesbar fuer %s/%s: %s - laeuft der Nachfueller "
            "(historie_okx.py --auffuellen)? Das ist KEIN 'Historie fehlt'."
            % (inst, takt, e)) from e


# --- Familie E: xperp (OKX-Futures, bot.py, familien) -----------------------
#
# xperp ist die einzige Spur, die ihr Signal nicht in handeln.py, sondern in
# bot.py berechnet (zeige_lage/zeige_trend/zeige_grid), und ihre Kerzen nicht
# aus Binance, sondern aus der OKX-Futures-API holt (historie_okx). Die
# wachen.json traegt `familien` (krypto/aktie/rohstoff) statt `instrumente`.
#
# Die Familie E wickelt die drei bot.py-Methoden ein:
#   lage  -> bot.zeige_lage(w, inst):  das Signal (z["signal"]), keine Order
#   trend -> bot.zeige_trend(w, inst, sammle=orders): EINE Order mit
#            Limit/Stop/Ziel aus den wachen-Faktoren (einstieg_atr_abschlag,
#            stop_atr_faktor, ziel_atr_faktor)
#   grid  -> bot.zeige_grid(w, inst, sammle=orders): eine Leiter von
#            Long-Stufen mit gemeinsamem Boden-Stop
# `sammle` ist die von bot.py GEBaUTE Naht fuer programmatischen Zugriff -
# die Orders kommen aus bot.py, nicht aus einer Nachbildung. Die
# Replay-Schleife entscheidet nur, wann eine Order gefuellt wird und wann
# eine Position geschlossen wird. bot_methode ist ueber das CLI waehlbar
# (Vorgabe "trend", der Live-Pfad der Spur).
#
# FILL-MODELL: bot.py legt LIMIT-Orders (der Long-Einstieg liegt
# einstieg_atr_abschlag unter dem Markt). Eine Order wird erst gebucht, wenn
# eine Kerze das Limit beruehrt (Long: Tief <= Limit) - wie im Betrieb, wo
# handeln.py wartende Auftraege fuehrt, sobald die Boerse fuellt. Nach
# order_gueltig_kerzen (wachen-Feld, Vorgabe ORDER_GUELTIG_KERZEN = 24 =
# 4 Tage bei 4H) verfaellt eine ungefuellte Order. Ein Instant-Fill zum
# Limitpreis waere die in T-096 dokumentierte Falle (besser als live
# moeglich).
#
# OKX-Unterschiede, die hier (und nur hier) behandelt werden:
#   - instIds tragen ein Ablaufdatum (RE-USD_UM_XPERP-310620); Kerzen liegen
#     unter dem VOLLEN instId - Basisnamen werden ueber die Metadaten
#     aufgeloest, nicht ueber eine Rate-Tabelle.
#   - Positionsgroessen und Tick-Raster (ctVal/lotSz/minSz/tickSz) kommen aus
#     historie_okx.instrument_meta() - einer DATEI, nicht aus der API.
#   - bot.py rechnet auf 4H-Kerzen (bot.BAR), nicht auf dem wachen-Takt.
#   - Der Hebel-Deckel (hebel_deckel) will Tageskerzen; die kommen aus der
#     gleichen 4H-Reihe VERDICHTET ueber die Test-Seam `tages_kerzen_quelle`
#     (eine Seam, die bot.py fuer genau diese Ersetzung vorsieht).
#   - Der 24h-Umsatz (Tor in zeige_lage) ist aus den Kerzen geschaetzt, nicht
#     von einem Ticker: volCcy24h = Summe (Volumen x Schlusskurs) der letzten
#     24 Stunden der Reihe. Es gibt keine historischen Ticker.
#   - CVD faehrt ueber die Naht `indikatoren.cvd_quelle`: die Komponente
#     faellt im Replay aus (keine Taker-Volumen-Historie in den Kerzen) -
#     das Signal bleibt also vollstaendig, nur "kein CVD" steht im Grund.
#
# ZWEI ANGEFUEGTE, DOKUMENTIERTE GRENZEN (T-096 legt sie offen):
#   1. Funding ist nicht in den Kerzen (funding() -> None): die Pruefpflicht
#      rechnet ohne Funding-Kosten, und das Journal fuehrt keinen
#      Funding-Beitrag. Live zahlt eine gehaltene XPERP-Position alle 8 h.
#   2. Der Kill-Switch (kill_switch_gesamt_usd) wird NICHT abgebildet -
#      wie in allen uebrigen Familien. Ein Lauf kann also ueber den Deckel
#      hinaus weiterhandeln, den die lebende Wache haette schliessen lassen.
#
# Geschrieben wird ausschliesslich unter daten/backtest/<spur>/<lauf>/
# (buch_ordner biegt journal_zweitziel um). Der echte Spurenordner bleibt
# unberuehrt.

SPUREN_TEIL_E = ("xperp",)

# Wie viele Kerzen eine ungefuellte Limit-Order liegen bleibt (Vorgabe,
# ueberschreibbar ueber wachen-Feld order_gueltig_kerzen - 24 4H-Kerzen
# sind 4 Tage).
ORDER_GUELTIG_KERZEN = 24


def _bot_modul():
    """bot.py der xperp-Spur ueber den PFAD laden - xperp kurz auf sys.path.

    bot.py importiert seinerseits okxf, indikatoren, auswahl, historie, cvd
    - alles Module aus dem xperp-ORDNER, die ueber sys.path gefunden werden
    muessen. Wird bot.py als Skript gestartet, ist der eigene Ordner
    sys.path[0]; im Replay-Prozess ist er es nicht. Der Ordner wird also
    NUR waehrend des Ladens eingefuegt und danach wieder entfernt - im
    Speicher bleiben die Modulobjekte, der Suchpfad des Replays bleibt
    unberuehrt. Das ist die Lehre aus spur_modul(): eine Reihenfolge der
    Eintraege entscheidet, welche Fassung geladen wird.
    """
    pfad = os.path.join(HIER, "xperp", "bot.py")
    if not os.path.isfile(pfad):
        raise FileNotFoundError("xperp/bot.py nicht gefunden: %s" % pfad)
    xperp = os.path.join(HIER, "xperp")
    drin = xperp in sys.path
    if not drin:
        sys.path.insert(0, xperp)
    try:
        s = importlib.util.spec_from_file_location("bt_xperp_bot", pfad)
        m = importlib.util.module_from_spec(s)
        s.loader.exec_module(m)
        return m
    finally:
        if not drin:
            try:
                sys.path.remove(xperp)
            except ValueError:
                pass


def _okxf_ersatz(okx, stand, metas, bhist, takt="4H"):
    """Ein okxf-Ersatz, der die HISTORISCHEN Kerzen liefert - kein Netz.

    bot.py's zeige_* rufen okxf.instrument(), okxf.kerzen(), okxf.tickers()
    und okxf.funding(). Alle vier werden hier aus dem Bestand beantwortet;
    `stand` ist ein veraenderliches Dict, das die Schleife je Schritt auf
    den aktuellen Zeitstempel stellt - so sieht der Bot nie die Zukunft.

    Die reinen Rechenfunktionen (auf_tick, kontrakte_aus_nominal) bleiben
    die ECHTEN aus xperp/okxf.py (uebergeben als `okx`): sie brauchen kein
    Netz und sind die eine Wahrheit der Kontraktgroessen. taker_volumen
    (fuer die CVD) liefert bewusst eine leere Liste - die Replay-Kerzen
    tragen kein Taker-Volumen (deshalb faellt CVD ueber die cvd_quelle-Naht
    komplett aus; diese Funktion ist nur der Rueckfall dafuer).
    """

    def instrument(wert):
        w = str(wert).upper()
        for iid in metas:
            if iid.upper() == w:
                return metas[iid]
        for iid in metas:
            if iid.upper().split("-")[0] == w:
                return metas[iid]
        raise okx.OKXFehler("kein XPERP-Kontrakt zu %r im Replay-Bestand" % wert)

    def kerzen(inst, bar="1H", anzahl=300):
        iid = instrument(inst)["instId"]
        basis = bhist.get(iid) or []
        bis = stand.get("bis_ms")
        if bis:
            basis = [r for r in basis if r[0] <= bis]
        if bar.upper() == "1D":
            basis = verdichten(basis, "1D")
        return basis[-int(anzahl):]

    def tickers(inst_type="FUTURES"):
        aus = {}
        for iid, reihen in bhist.items():
            bis = stand.get("bis_ms")
            letzte = [r for r in reihen if r[0] <= bis][-6:]   # 24 h bei 4H
            # OKX volCcy24h ist das 24h-Volumen in der BASIS-Waehrung
            # (Kontrakte x ctVal); zeige_lage multipliziert es mit dem Kurs,
            # um den USD-Umsatz des Umsatz-Tors zu bekommen. Aus den Kerzen
            # geschaetzt - es gibt keine historischen Ticker.
            ctval = float((metas.get(iid) or {}).get("ctVal") or 1.0)
            aus[iid] = {"volCcy24h": "%.4f" % sum(
                (r[5] or 0.0) * ctval for r in letzte)}
        return aus

    def funding(inst):
        # Keine Funding-Historie in den Kerzen; pruefpflicht() behandelt
        # None als "nicht abrufbar" und laesst Funding aus der Rechnung.
        return None

    def taker_volumen(inst, period="4H"):
        return []

    return types.SimpleNamespace(
        instrument=instrument, kerzen=kerzen, tickers=tickers,
        funding=funding, taker_volumen=taker_volumen,
        auf_tick=okx.auf_tick, kontrakte_aus_nominal=okx.kontrakte_aus_nominal,
        OKXFehler=okx.OKXFehler, KRYPTO=okx.KRYPTO, AKTIE=okx.AKTIE,
        ROHSTOFF=okx.ROHSTOFF)


def instrument_id(wert, metas):
    """Voller instId zu einem Namen, aus den Metadaten - die eine Tabelle."""
    w = str(wert).upper()
    for iid in metas:
        if iid.upper() == w:
            return iid
    for iid in metas:
        if iid.upper().split("-")[0] == w:
            return iid
    raise KeyError("kein XPERP-Kontrakt zu %r im Replay-Bestand" % wert)


def _insts_okx(w):
    """Voll-InstIds aus der wachen.json - netzfrei ueber die Metadaten-Datei.

    Ein `instrumente`-Feld (voller instId) hat Vorrang: historie_okx.instid()
    laesst volle XPERP-InstIds unveraendert durch, kein Netz. Fehlt es, werden
    die AKTIVEN familien ueber ihre instCategory auf die _instrumente.json
    abgebildet - die beim --auffuellen mitgeschriebene Kontraktliste, keine
    Live-Abfrage.
    """
    liste = _instrumente(w)
    if liste:
        return sorted({historie_okx.instid(str(x)) for x in liste})
    datei = historie_okx.alle_instrumente()
    if not datei:
        raise RuntimeError(
            "keine Instrument-Metadaten-Datei (%s) - erst "
            "'python historie_okx.py --auffuellen'"
            % os.path.join(historie_okx.ORDNER, "_instrumente.json"))
    kats = {f.get("instCategory")
            for f in (w.get("familien") or {}).values()
            if f.get("aktiv") and f.get("instCategory")}
    return sorted(iid for iid, m in datei.items()
                  if m.get("instCategory") in kats)


def _bot_orders(bot, w, inst, methode, metas, puffer):
    """Die Orders EINES Schritts aus der gewaehlten bot.py-Methode.

    Rueckgabe: Liste von {"seite", "einstieg", "stop", "ziel", "kontrakte",
    "nominal"} - leer, wenn die Methode keine Order vorschlaegt (Signal
    "kein", zu kleine Position, Grid-Abbruch).

    bot.py's zeige_* drucken fuer den Menschen; im Replay geht diese
    Ausgabe in den Puffer und wird verworfen. `sammle` ist die gebaute Naht
    fuer die maschinenlesbare Order.
    """
    sammle = []
    if methode == "trend":
        bot.zeige_trend(w, inst, sammle=sammle)
    elif methode == "grid":
        bot.zeige_grid(w, inst, sammle=sammle)
    else:  # "lage": Signal rechnen, keine Order erzeugen (CLI-Wahrheit)
        bot.zeige_lage(w, inst)
        return []
    orders = []
    for eintrag in sammle:
        meta = metas[instrument_id(inst, metas)]
        ctval = float(meta.get("ctVal") or 1.0)
        for seite, kontrakte, einstieg, ziel, stop in eintrag["orders"]:
            einstieg, ziel, stop = (float(einstieg), float(ziel),
                                    float(stop))
            orders.append({
                "seite": "long" if seite == "buy" else "short",
                "einstieg": einstieg, "ziel": ziel, "stop": stop,
                "kontrakte": float(kontrakte),
                "nominal": float(kontrakte) * ctval * einstieg})
    return orders


def lauf_e(spur, gebuehr_pct, lauf, bis_ms=None, max_kerzen=None, fenster=None,
           wachen_patch=None, methode="trend", bot=None):
    """Familie E: xperp ueber OKX-Futures-Kerzen, Signal aus bot.py.

    Rueckgabe wie lauf_a: (runden, Zahl der offenen Positionen).

    Die Spur entscheidet (bot.zeige_lage/zeige_trend/zeige_grid), der Replay
    liefert Zeit und Daten:
    - OKX-Kerzen kommen aus historie_okx.lade()
    - Die Instrumente kommen aus historie_okx (Metadata-Datei, familien)
    - Kontraktgroessen aus historie_okx.instrument_meta() (Datei, kein Netz)
    - Die Orders kommen aus bot.py (sammle-Naht), gefuellt am Limit
    - Ausstiege ueber Stop/Ziel an den Kerzen (Beruehrungsregel T-177)

    `bot` ist die Test-Naht (ein vorbereitetes bot-Modul); ohne Angabe wird
    xperp/bot.py ueber den Pfad geladen.
    """
    import contextlib
    import io
    import pos_kennung

    if bot is None:
        bot = _bot_modul()
    ordner = buch_ordner(spur, lauf)
    w = wachen_von(spur)
    if wachen_patch:
        w.update(wachen_patch)
    if w.get("mindest_kerzen") is None:
        # bot.py holt in hole() 300 Kerzen - das ist seine Anforderung.
        w["mindest_kerzen"] = 300

    insts = _insts_okx(w)
    if not insts:
        raise RuntimeError(
            "keine Instrumente fuer %s - die wachen.json traegt weder "
            "instrumente noch familien" % spur)

    takt = getattr(bot, "BAR", "4H")
    alle = {}
    metas = {}
    for inst in insts:
        reihen = lade_reihen_okx(inst, takt)
        if not reihen:
            continue
        if bis_ms:
            reihen = [r for r in reihen if r[0] <= bis_ms]
        if max_kerzen:
            reihen = reihen[-int(max_kerzen):]
        if reihen:
            alle[inst] = reihen
            metas[inst] = historie_okx.instrument_meta(inst)

    if not alle:
        raise RuntimeError(
            "keine Historie fuer %s - erst 'python historie_okx.py "
            "--auffuellen --instrumente %s --takte 4H'"
            % (spur, ",".join(insts[:5])))

    laenge = min(len(k) for k in alle.values())
    brauch = bedarf(w)
    if laenge < brauch:
        zu_klein = ["%s (%d Kerzen)" % (i, len(k)) for i, k in alle.items()]
        raise HistorieFehlt(mangel_text(spur, w, [], zu_klein, max_kerzen))

    runden, gesammelt = [], []
    zustand_ts = {"ts": None}
    stand = {"bis_ms": None}
    kerzen_jetzt = {}
    huelle = Beruehrungsjournal(
        kerzen_jetzt,
        lambda **f: gesammelt.append(dict(f, _kerzen_ts=zustand_ts["ts"])))
    puffer = io.StringIO()
    ersatz = _okxf_ersatz(bot.okxf, stand, metas, alle, takt)
    alt_okxf = bot.okxf
    alt_tages = bot.tages_kerzen_quelle
    alt_cvd = getattr(bot.indikatoren, "cvd_quelle", None)
    bot.okxf = ersatz
    # Tageskerzen fuer den Hebel-Deckel: aus der 4H-Reihe verdichtet, ueber
    # die Seam, die bot.py dafuer vorsieht. NUR Kerzen bis zum aktuellen
    # Stand - die Zukunft bleibt unsichtbar.
    bot.tages_kerzen_quelle = lambda inst, n=300: verdichten(
        [r for r in (alle.get(instrument_id(inst, metas)) or [])
         if r[0] <= (stand.get("bis_ms") or 10 ** 15)], "1D")[-int(n):]
    # CVD faellt aus (keine Taker-Historie in Kerzen) - Signal bleibt ganz.
    bot.indikatoren.cvd_quelle = lambda inst: bot.indikatoren.cvd.leer(
        "Replay: keine Taker-Volumen-Historie")
    zurueck_kennung = kennung_fest()
    gueltig_kerzen = int(w.get("order_gueltig_kerzen", ORDER_GUELTIG_KERZEN))
    z = {"positionen": [], "modus": "papier", "letzter_lauf": None,
         "verluste_usd": 0.0}
    wartend = []          # ungefuellte Limit-Orders: {inst, seite, ...,
                          # einstieg, stop, ziel, nominal, gelegt_i}
    try:
        for i in range(int(w["mindest_kerzen"]), laenge):
            ts_schritt = max(k[i][0] for k in alle.values())
            zustand_ts["ts"] = ts_schritt
            stand["bis_ms"] = ts_schritt
            for inst, alle_kerzen in alle.items():
                k = alle_kerzen[max(0, i + 1 - (fenster or 300)):i + 1]
                kerzen_jetzt[inst] = k[-1]
                zeit = dt.datetime.fromtimestamp(
                    ts_schritt / 1000.0, dt.timezone.utc).isoformat(
                    timespec="seconds")
                # 1) Offene Limits fuehlen: beruehrt eine Kerze das Limit,
                #    wird die Order jetzt gebucht (wie live, wo die Boerse
                #    die wartende Order fuellt). Verfall nach
                #    order_gueltig_kerzen.
                erfuellt, rest = [], []
                for a in wartend:
                    if a["inst"] != inst:
                        rest.append(a)
                        continue
                    kerze = k[-1]
                    if (a["seite"] == "long" and _zahl(kerze[3]) <= a["einstieg"]) \
                            or (a["seite"] == "short"
                                and _zahl(kerze[2]) >= a["einstieg"]):
                        erfuellt.append(a)
                    elif i - a["gelegt_i"] < gueltig_kerzen:
                        rest.append(a)
                wartend = rest
                for a in erfuellt:
                    pos = dict(a, inst=inst,
                               pos_id=pos_kennung.neu(zeit), ts=k[-1][0])
                    z["positionen"].append(pos)
                    huelle(zeit=zeit, modus="papier", aktion="kauf",
                           inst=inst, pos_id=pos["pos_id"],
                           seite=pos["seite"],
                           preis="%.6f" % pos["einstieg"],
                           einsatz_usd="%.2f" % pos["nominal"],
                           stop="%.6f" % pos["stop"],
                           ziel="%.6f" % pos["ziel"],
                           grund="limit_gefuellt")
                # 2) Ausstiege: Stop/Ziel an der Kerze (Beruehrungsregel).
                for p in list(z["positionen"]):
                    if p.get("inst") != inst:
                        continue
                    marke = beruehrte_marke(
                        k[-1], p.get("seite"), p.get("stop"), p.get("ziel"))
                    if marke is None:
                        continue
                    kurs = _zahl(p.get("stop")) if marke == "stop" \
                        else _zahl(p.get("ziel"))
                    vz = 1 if p.get("seite") == "long" else -1
                    gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
                    erloes = p["nominal"] + gv
                    huelle(zeit=zeit, modus="papier", aktion="verkauf",
                           inst=inst, pos_id=p.get("pos_id", ""),
                           seite=p.get("seite"),
                           preis=_preis_text(kurs, "%.6f" % kurs),
                           einsatz_usd="%.2f" % erloes,
                           stop="%.6f" % p.get("stop", 0),
                           ziel="%.6f" % p.get("ziel", 0),
                           grund=marke)
                    z["positionen"].remove(p)
                    runden.append({
                        "inst": inst, "seite": p["seite"],
                        "einstieg": p["einstieg"], "ausstieg": kurs,
                        "nominal": p["nominal"],
                        "brutto_pct": (kurs - p["einstieg"]) / p["einstieg"]
                        * 100.0 * vz,
                        "netto_pct": (kurs - p["einstieg"]) / p["einstieg"]
                        * 100.0 * vz - 2 * gebuehr_pct,
                        "gv_brutto": p["nominal"] * (kurs - p["einstieg"])
                        / p["einstieg"] * vz / 100.0,
                        "gv_netto": p["nominal"] * ((kurs - p["einstieg"])
                        / p["einstieg"] * vz - 2 * gebuehr_pct / 100.0),
                        "ein_ts": p.get("ts"), "aus_ts": k[-1][0],
                        "stunden": (k[-1][0] - p.get("ts", k[-1][0]))
                        / 3600000.0})
                # 3) Neue Orders: nur wenn das Instrument weder Position
                #    noch offenes Limit hat (Live: ein Anlauf je Wert).
                if any(p.get("inst") == inst for p in z["positionen"]):
                    continue
                if any(a["inst"] == inst for a in wartend):
                    continue
                with contextlib.redirect_stdout(puffer):
                    orders = _bot_orders(bot, w, inst, methode, metas, puffer)
                for o in orders:
                    wartend.append(dict(o, inst=inst, gelegt_i=i))
    finally:
        bot.okxf = alt_okxf
        bot.tages_kerzen_quelle = alt_tages
        if alt_cvd is not None:
            bot.indikatoren.cvd_quelle = alt_cvd
        zurueck_kennung()
    _journal_schreiben(ordner, gesammelt)
    return runden, len(z["positionen"])


def kerzenlaenge(spur, w=None):
    """Laenge der KUERZESTEN Reihe - so weit reicht ein Abschnitt.

    Der Walk laeuft ueber `min(len(k))`; der Optimierer muss seine Fenster
    deshalb an derselben Zahl ausrichten, sonst liegen die Fenster fuer ein
    Instrument ausserhalb der Reihe.
    """
    if w is None:
        w = wachen_von(spur)
    takt = _takt(w)
    return min((len(lade_reihen(i, takt)) for i in _instrumente(w)), default=0)


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


def gebuehr_aufloesen(gebuehr=None, spur=None):
    """(Satz in Prozent je Seite, woher er kommt).

    Vorgabe ist der GEMESSENE Satz der Spur (`gebuehr_taker` aus ihrer
    wachen.json, mal 100) - nicht eine Zahl von der Kommandozeile. Bis
    01.10.2026 stand hier fest 0.1: fuer die vier Indikator-Spuren (OKX-Spot)
    war das richtig, fuer `mosaic` (Kraken, 0,60 %/Seite) rechnete jeder
    Backtest damit sechsmal zu guenstig. Ein ausdrueckliches `--gebuehr`
    schlaegt die Vorgabe (auch `--gebuehr 0`, um die Kosten wegzulassen).
    """
    if gebuehr is not None:
        return float(gebuehr), "--gebuehr (von Hand gesetzt)"
    return gebuehr_fuer(spur), "wachen.json der Spur (gebuehr_taker)"


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
    ap.add_argument("--gebuehr", type=float, default=None,
                    help="Prozent je Seite; Vorgabe: der GEMESSENE Satz aus der "
                         "wachen.json der Spur (gebuehr_taker). Ein eigener Wert "
                         "schlaegt die Vorgabe, auch 0.")
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
    ap.add_argument("--familie-e", action="store_true",
                    help="Spur mit bot.py und OKX-Kerzen (xperp)")
    ap.add_argument("--bot-methode", default="trend",
                    choices=("lage", "trend", "grid"),
                    help="bot.py-Methode fuer Familie E (xperp): lage, "
                         "trend (Vorgabe), grid")
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
    geb, geb_quelle = gebuehr_aufloesen(a.gebuehr, a.spur)
    if a.gegenprobe:
        print(json.dumps(gegenprobe(a.spur, geb, a.lauf, mk),
                         indent=2, ensure_ascii=False))
        return
    if a.familie_c:
        k, zeilen = lauf_c(a.spur, gebuehr_fuer(a.spur), a.lauf,
                           setzen=setzen_aus(a.setzen))
        print(json.dumps({"spur": a.spur, "kennzahlen": k, "zeilen": zeilen},
                         indent=2, ensure_ascii=False))
        return
    if a.familie_e or a.spur in SPUREN_TEIL_E:
        # Familie E wird am SPURNAMEN erkannt, nicht an einem Schalter: die
        # Fahrweise ist eine Eigenschaft der Spur. Ein Schalter waere eine
        # zweite Wahrheit - und `--spur xperp` ohne ihn liefe genau in den
        # Fehler, den dieser Abschnitt behebt.
        runden, offen = lauf_e(a.spur, geb, a.lauf, max_kerzen=mk,
                               fenster=a.fenster,
                               methode=a.bot_methode,
                               wachen_patch=setzen_aus(a.setzen))
        print(json.dumps(
            {"spur": a.spur, "runden": len(runden), "offen": offen,
             "bot_methode": a.bot_methode,
             "gebuehr_pct": geb, "gebuehr_quelle": geb_quelle,
             "fenster": (a.fenster if a.fenster is not None
                         else int(wachen_von(a.spur).get("mindest_kerzen") or 300)),
             "kerzenquelle": "okx",
             "kennzahlen": kennzahlen(os.path.join(
                 buch_ordner(a.spur, a.lauf), "handelsjournal.csv"))},
            indent=2, ensure_ascii=False))
        return
    if a.feed:
        k, zeilen = lauf_feed(a.spur, gebuehr_fuer(a.spur), a.lauf,
                              takt=a.takt, mindest_symbole=a.mindest_symbole,
                              setzen=setzen_aus(a.setzen))
        print(json.dumps({"spur": a.spur, "kennzahlen": k, "zeilen": zeilen},
                         indent=2, ensure_ascii=False))
        return
    if a.spur in MEHRZEITRAHMEN or a.spur in EIGENE_RECHNUNG:
        # Familie D wird am SPURNAMEN erkannt, nicht an einem Schalter: die
        # Fahrweise ist eine Eigenschaft der Spur. Ein Schalter waere eine
        # zweite Wahrheit - und `--spur mosaic` ohne ihn liefe genau in den
        # TypeError, den dieser Abschnitt behebt.
        #
        # Zwei Fahrweisen unter einem Weg: Mehrzeitrahmen (mosaic) und eigene
        # Rechnung (gitter). Ein gemeinsamer Vorlauf waere der Fehler - die
        # zweite braucht keine Kerzenreihen, die erste keine Leiter.
        if a.spur in MEHRZEITRAHMEN:
            runden, offen = lauf_mehrzeitrahmen(a.spur, geb, a.lauf,
                                                max_kerzen=mk,
                                                fenster=a.fenster,
                                                # siehe lauf_a: der Schalter
                                                # heisst hier `wachen_patch`
                                                wachen_patch=setzen_aus(a.setzen))
            print(json.dumps(
                {"spur": a.spur, "runden": len(runden), "offen": offen,
                 "gebuehr_pct": geb, "gebuehr_quelle": geb_quelle,
                 # Das WIRKSAME Fenster, nicht das Argument: ohne --fenster
                 # setzt die Spur ihre eigene Anforderung (mindest_kerzen).
                 "fenster": (a.fenster if a.fenster is not None
                             else int(wachen_von(a.spur).get("mindest_kerzen", 300))),
                 "kerzenquelle": "binance",
                 "kennzahlen": kennzahlen(os.path.join(
                     buch_ordner(a.spur, a.lauf), "handelsjournal.csv"))},
                indent=2, ensure_ascii=False))
            return
        if a.spur in EIGENE_RECHNUNG:
            k = lauf_eigene_rechnung(a.spur, geb, a.lauf, max_kerzen=mk,
                                      wachen_patch=setzen_aus(a.setzen))
            print(json.dumps({"spur": a.spur, "kennzahlen": k,
                              "gebuehr_quelle": geb_quelle},
                             indent=2, ensure_ascii=False))
            return
    # Erst hier: `lade_wachen` gibt es nur bei den Kerzen-Spuren (Familie A).
    modul = spur_modul(a.spur)
    w = dict(modul.lade_wachen()) if hasattr(modul, "lade_wachen") else {}
    fenster = None if a.ganz else a.fenster
    if fenster is None and not a.ganz:
        fenster = fenster_vorgabe(w)
    if fenster is not None and fenster < bedarf(w):
        # Dieselbe Regel wie bei `max_kerzen`: ein Fenster unter dem, was die
        # Spur braucht, ergibt keinen einzigen Schritt. `fenster_vorgabe`
        # respektiert die Anforderung der Spur, ein von Hand gesetztes
        # `--fenster` tat es nicht - der Lauf meldete dann still "0 Runden".
        raise HistorieFehlt(
            "Fenster zu klein fuer %s: --fenster %d - die Spur braucht "
            "mindestens %d Kerzen je Reihe (mindest_kerzen %s + %d). "
            "--fenster weglassen oder auf %d oder mehr setzen"
            % (a.spur, fenster, bedarf(w), w.get("mindest_kerzen", 300),
               KERZEN_PUFFER, bedarf(w)))
    runden, offen = lauf_a(a.spur, geb, a.lauf, max_kerzen=mk,
                           fenster=fenster,
                           # Der Parameter heisst bei den Kerzenspuren
                           # `wachen_patch`, NICHT `setzen` (das gibt es nur
                           # bei lauf_c/lauf_feed). Vorher stand hier kein
                           # Patch: `--setzen` wurde stillschweigend
                           # verworfen, jeder Kandidat lief mit den HEUTIGEN
                           # Werten, und die Suche meldete "kein Hebel",
                           # ohne dass sich je etwas bewegt hat -
                           # genau die stille Fehlalarmausnahme, vor der
                           # der Optimierungs-Skill warnt. Gemessen am
                           # 04.10.2026: Stop 3,0 %/Ziel 1,5R und
                           # 5,0 %/2,0R lieferten bitgleiche Kennzahlen.
                           wachen_patch=setzen_aus(a.setzen))
    print(json.dumps({"spur": a.spur, "runden": len(runden),
                      "offen": offen, "gebuehr_pct": geb,
                      "gebuehr_quelle": geb_quelle,
                      "fenster": fenster, "kerzenquelle": "binance",
                      "kennzahlen": kennzahlen(os.path.join(
                          buch_ordner(a.spur, a.lauf), "handelsjournal.csv"))},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except HistorieFehlt as e:
        # Ein Eingabefehler (Fenster zu klein) oder eine fehlende Historie ist
        # kein Absturz. Eine Zeile statt eines Tracebacks, Exit 2 - der
        # Leitstand liest stderr mit und zeigt damit denselben Satz.
        sys.stdout.flush()          # die Meldungszeilen zuerst, dann der Grund
        print("replay: %s" % e, file=sys.stderr)
        sys.exit(2)
