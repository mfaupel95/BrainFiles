"""Was die Buecher hergeben - Spur fuer Spur, mit ihrer eigenen Kostenrechnung.

Warum es dieses Modul gibt: spiegel, omniquant und gitter haben eigene
Auswertungen, die drei Buecher mit den groessten Journalen (xperp, swap,
scanner, kraken) hatten keine. Die haeufigste Frage im Handel-Baum - traegt
das Buch nach Kosten? - stand damit fuer sie offen.

Die gemeinsame Mechanik (Bilanz, Trefferquote, Gruppen, Baender, die Regel
"unter MIN_AUSSTIEGE wird nichts behauptet") steht in buchauswertung.py. Hier
steht nur, was jede Spur anders macht: welches Feld der Einsatz ist, welches
der Erloes, und welcher Satz an Kosten in der Zahl schon steckt.

WICHTIG - die Kosten sind NICHT geschaetzt, sondern stehen in der Zeile:
  xperp/swap  Gebuehr auf den Nominalwert (beide Seiten) und Funding, beides
              als Spalte im Journal; gerechnet wird aus margin_usd und preis.
  scanner     GEBUEHR_PCT = 0.0005 je Seite, im Journal schon eingerechnet
              (kauf: usd*(1+g), verkauf: erloes).
  kraken      Gebuehr aus wachen.json (seit 14.09.2026 0 % dank Kraken-Pro),
              ebenfalls schon in der Zeile.
  orbk        gv_usd steht fertig in der Zeile.

Aufruf (aus dem Handel-Ordner):
    scanner/.venv/Scripts/python.exe auswertung_alle.py
    scanner/.venv/Scripts/python.exe auswertung_alle.py --spur xperp
"""

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import stoerungen  # gleicher Ordner: trennt Zwangsschluesse von Handelsrunden
import risikostufe  # gleicher Ordner: Dateinamen der Risikostufen
import zeitfenster  # gleicher Ordner: Fenstergrenzen und Zeilenfilter
import journalpaarung as jp  # gleicher Ordner: EINE Paarung fuer alle Auswertungen

# Risikostufe dieser Auswertung: None = Basis. Setzt main() aus --risiko.
STUFE = None

HIER = Path(__file__).resolve().parent

# Ab wie vielen geschlossenen Runden eine Spur ueberhaupt etwas aussagt.
# Dieselbe Schwelle wie buchauswertung.MIN_AUSSTIEGE - zwei Schwellen fuer
# dieselbe Frage laufen sonst auseinander.
MIN_RUNDEN = 8

# Spuren, deren Journal NICHT im gleichnamigen Ordner liegt. Grund: eine Spur
# kann eine zweite Strategie im selben Ordner fahren (nautilus_kraken faehrt
# Spot in handelsjournal.csv und Futures in handelsjournal.futures.csv; squeeze
# faehrt BTC/ETH/SOL und der Schattenarm squeeze_eth fest auf ETH). Ohne diese
# Zuordnung sucht die Auswertung einen Ordner, den es nicht gibt, und meldet
# "kein Buch", obwohl das Journal gefuellt ist. 04.10.2026: squeeze_eth stand
# in keiner der fuenf Hand-listen und wurde hier als vermisst gemeldet.
FREMDES_BUCH = {
    "nautilus_kraken_futures": ("nautilus_kraken", "handelsjournal.futures.csv"),
    "squeeze_eth": ("squeeze", "handelsjournal.eth.csv"),
}

# Dasselbe fuer die WACHEN: der Futures-Arm faehrt aus demselben Ordner, seine
# Grenzen und seine Gebuehr stehen aber in `wachen.futures.json`. Ohne diesen
# Griff las `gebuehr_fuer()` die SPOT-Wachen und der Bericht meldete fuer ein
# Buch mit bekannter Gebuehr "BRUTTO und UNBEKANNT" (gemessen 01.10.2026).
WACHEN_SUFFIX = {"nautilus_kraken_futures": "wachen.futures.json",
                 "squeeze_eth": "wachen.eth.json"}


def _ort(spur, datei):
    """Ordner und Dateiname des Journals einer Spur."""
    if spur in FREMDES_BUCH:
        ordner, eigene = FREMDES_BUCH[spur]
        if datei == "handelsjournal.csv":
            return ordner, eigene
        if datei == "wachen.json" and spur in WACHEN_SUFFIX:
            return ordner, WACHEN_SUFFIX[spur]
        return ordner, datei
    return spur, datei


def gebuehr_fuer(spur):
    """Gebuehr JE SEITE aus der wachen.json der Spur (0.0, wenn keine steht).

    EINE Stelle fuer diese Frage: `runden_fuer()` braucht sie fuer die Anzeige
    der Kosten (scanner/kraken) und `kennzahlen_fuer()` fuer den NETTO-Ausweis.
    Zwei eigene Lesevorgaenge haetten beim naechsten Feld auseinanderlaufen
    koennen - und dann stuende im Bericht eine andere Gebuehr als im Buch.
    """
    ordner, datei = _ort(spur, "wachen.json")
    try:
        w = json.loads((HIER / ordner / datei).read_text("utf-8"))
    except (OSError, ValueError):
        return 0.0
    try:
        return float(w.get("gebuehr_taker") or 0.0)
    except (TypeError, ValueError):
        return 0.0


# DIESE SPUREN RECHNEN DIE GEBUEHR SCHON IM JOURNAL EIN: scanner/kraken im
# Betrag der Ausstiegszeile, xperp/swap ueber `gebuehr_pct`/`funding_pct` der
# Zeile. ALLE ANDEREN Papierbuecher schreiben BRUTTO - ihre Zeilen tragen keine
# Kosten (siehe `runden_indikator`, `runden_orbk`, `runden_nautilus`).
# Ohne diese Unterscheidung stuenden brutto und netto in derselben Summe.
GEBUEHR_SCHON_DRIN = ("xperp", "swap", "scanner", "kraken")

SPUREN = ("xperp", "swap", "scanner", "kraken", "orb", "orbk", "gitter", "nautilus", "nautilus_kraken", "nautilus_kraken_futures")

# Die vier Indikator-Spuren journalisieren kauf/verkauf mit `einsatz_usd`
# (beim Kauf der Einsatz, beim Verkauf der Erloes). Sie stehen getrennt,
# weil IHR JOURNAL anders heisst, nicht weil anders gerechnet wird - der
# Rechenweg steht in runden_indikator() an einer Stelle.
INDIKATOR_SPUREN = ("squeeze", "wavetrend", "macd_mtf", "supertrend", "mosaic",
                   # Prophet-Signal (02.10.2026): EMA30-Trend + Saisonalitaet als
                   # Kursregel (prophet_regeln.py), schreibt dieselbe Journalform.
                   "prophet_signal",
                   "fib_retrace",
                   # Schattenarm squeeze_eth (03.10.2026, Auftrag Max
                   # "Schattenarm"): dieselbe Regel fest auf ETH, damit sich
                   # fragegt, ob sie Coin-spezifisch ist. Schreibt dieselbe
                   # Journalform in handelsjournal.eth.csv (FREMDES_BUCH) -
                   # 04.10.2026 fehlte der Arm in ALLEN fuenf Hand-listen und
                   # wurde von test_verdrahtung als vermisst gemeldet.
                   "squeeze_eth")

# Bot-Spuren (16.09.2026): Papierbuecher auf den Signalen geklonter Fremd-Bots
# (Werkstatt/Repos/moon-dev-ai-agents). Ihr Journal hat dieselbe Form wie das
# der Indikator-Spuren (kauf/verkauf mit einsatz_usd), deshalb derselbe
# Rechenweg - nur der NAME der Gruppe ist ein anderer.
BOT_SPUREN = ("moondev_funding", "moondev_listingarb", "moondev_topmovers",
              "moondev_signalwelle",
              "moondev_marktlage", "iv_wand",
              # IV-WAELLE (18.09.2026): Deribit-IV-Waende, dieselbe
              # Journalform (kauf/verkauf mit einsatz_usd) - derselbe Weg.
              "iv_waelle",
              # Die drei Sprachmodell-Spuren (17.09.2026) fuehren dasselbe
              # Journal (kauf/verkauf mit einsatz_usd) - derselbe Rechenweg.
              "moondev_whale", "moondev_liquidation", "moondev_sentiment",
              # MOONDEV_SNIPER (19.09.2026): neue Solana-Launches, dasselbe
              # Journal - derselbe Weg.
              "moondev_sniper",
              # ROBINHOOD_RADAR (22.09.2026): Buch ueber
              # Handel/spur_buch.py, Journalform kauf/verkauf mit
              # einsatz_usd - derselbe Rechenweg.
              "robinhood_radar",
              # OMNITRADE (30.09.2026): Buch ueber Handel/spur_buch.py,
              # Journalform kauf/verkauf mit einsatz_usd - derselbe Rechenweg.
              "omnitrade",
              # OMNITRADE_FUTURES (30.09.2026): dasselbe Buch, ganze Kontrakte.
              "omnitrade_futures",
              # KLASSIK-SPUREN (30.09.2026): spur_buch, dieselbe Journalform.
              "klassik_sma", "klassik_ema", "klassik_macd", "klassik_bollinger",
              "klassik_donchian", "klassik_rsi", "klassik_rsi2",
              "klassik_donchian_trend", "klassik_sr_breaks", "klassik_pmax",
              "klassik_supertrend",
              # LIQ_WAND (21.09.2026): Liquidationswand als Beschleuniger,
              # Spur ueber spur_buch.py, Journalform kauf/verkauf mit
              # einsatz_usd - derselbe Weg. TRENDWENDE_BTC (21.09.2026):
              # SuperTrend-Wende auf BTC, dieselbe Form.
              # NAUTILUS_EMACROSS (03.10.2026): EMA10/20 mit
              # Close-and-Reverse, dieselbe Form.
              # Die drei fehlten hier und ihre Runden tauchten in KEINER
              # Auswertung auf - liq_wand hatte 32 geschlossene Runden im
              # Journal und 0 in der Zahl (gemessen 03.10.2026).
              "liq_wand", "trendwende_btc", "nautilus_emacross")
SPUREN = SPUREN + INDIKATOR_SPUREN + BOT_SPUREN


# Die drei nautilus-Arme buchen eroeffnen/schliessen (Betrag in
# einsatz_usd/wert_usd bzw. einsatz_eur/wert_eur). Bis zum 28.09.2026 hatten
# sie KEINEN Rechenweg in kennzahlen_fuer() und fielen in den else-Zweig:
# "keine geschlossene Runde", obwohl im Journal sieben (nautilus) bzw. vier
# (nautilus_kraken) geschlossene Runden standen.
NAUTILUS_SPUREN = ("nautilus", "nautilus_kraken", "nautilus_kraken_futures")

# Waehrung der Anzeige je Spur - der Kraken-Arm fuehrt EUR, die anderen USD.
# Diese Tabelle ist die VORGABE. Fuer die kraken-Spur gilt sie seit dem
# 30.09.2026 nicht mehr: die Spur kann in EUR, USDC und EURC handeln, und die
# Einheit ihrer Zahlen steht am BUCH (einheit_fuer()).
EINHEIT = {"kraken": "EUR", "nautilus_kraken": "EUR",
           # ORB-SPUREN (T-192, 01.10.2026): orb und orbk fuehren ein
           # PUNKTE-Buch - `gv_usd` ist die Kursstrecke mal punkt_wert_usd
           # (1:1), also der Gewinn JE EINHEIT. "USD" an dieser Stelle war
           # eine Behauptung: die Summe der Strecken ist kein Geldbetrag.
           "orb": "Punkte", "orbk": "Punkte"}


def _zustand_pfad(spur):
    """Pfad zu `zustand.json` dieser Spur, in der Risikostufe der Auswertung."""
    datei = "zustand.json"
    if STUFE:
        datei = risikostufe.datei_fuer(datei, STUFE)
    ordner, datei = _ort(spur, datei)
    return HIER / ordner / datei


def kraken_buch_waehrung(z=None):
    """Die Waehrung, in der das Kraken-Buch steht - fuer die ANZEIGE.

    Jede Position traegt seit dem 30.09.2026 ihre Waehrung (EUR, USDC oder
    EURC). Positionen aus der Zeit davor tragen kein Feld - damals war EUR die
    einzige Waehrung der Spur, also ist EUR die richtige Antwort und nicht
    "unbekannt". Ohne `z` wird der Zustand DIESER Risikostufe gelesen, nicht
    geraten.

    Die Regel steht hier, weil `lage.spur_kraken()` fuer den Bericht dieselbe
    braucht: dort wird sie aufgerufen, nicht ein zweites Mal gefuehrt.
    """
    if z is None:
        try:
            with open(_zustand_pfad("kraken"), encoding="utf-8") as f:
                z = json.load(f)
        except (OSError, ValueError):
            z = {}
    if not isinstance(z, dict):
        z = {}
    for p in z.get("positionen") or []:
        w_ = str(p.get("waehrung") or "").strip().upper()
        if w_:
            return w_
    return "EUR"


def scanner_buch_quote(z=None):
    """Die Quote, in der das Scanner-Buch steht - fuer die ANZEIGE.

    T-311: das OKX-Konto (EEA) fuehrt kein USDT. Gemessen am 05.10.2026:
    302,39 USDC frei, 0,00 USDT, 0,0003 EURC. Das Buch handelt USDC-Paare
    (Scanner seit 02.10.2026, `universum.quotes`), und die Positionen tragen
    seitdem ihr Instrument in dieser Form ("ETH-USDC"). Eine Anzeige "USD"
    war eine BEHAUPTUNG: sie behauptete einen Kontostand in einer Waehrung,
    die auf diesem Konto nicht existiert - dieselbe Klasse wie der
    Kraken-BTC-Kurs aus der OKX-Tabelle am 23.09.2026.

    Die Regel steht hier und NUR hier, wie bei `kraken_buch_waehrung()`:
    Tagesbericht, Handelszentrale, Strategiekennzahlen und der
    Guthabenabgleich lesen dieselbe Funktion, sonst laufen vier Anzeigen
    auseinander.

    GRENZE, die man kennen muss (T-311): das JOURNAL mischt zwei Buecher.
    277 Zeilen tragen USDT-Paare (bis 01.10.2026, dem Tag vor der Umstellung),
    80 USDC-Paare danach. Beide sind 1:1 zum Dollar, aber nur die USDC-Zeilen
    sind Guthaben dieses Kontos. Diese Funktion sagt die WAHRHEIT UEBER HEUTE
    (das gebundene Geld) - sie behauptet NICHT, dass die Historie in USDC
    gebucht wurde. Die Umrechnung der Historie ist offen (T-311 bleibt
    teilweise offen) und waere eine Buchwanderung, keine Anzeigekorrektur.
    """
    if z is None:
        z = _lies_zustand("scanner")
    for p in (z or {}).get("positionen") or []:
        inst = str(p.get("inst") or "")
        if "-" in inst:
            return inst.rsplit("-", 1)[-1].upper()
    # Keine Position, kein Instrument: die Quote der WACHEN ist die naechste
    # belegbare Quelle, und ohne sie waere jede Antwort geraten.
    return _scanner_wachen_quote()


def _lies_zustand(spur):
    """Der Zustand dieser Spur in der Risikostufe DIESER Auswertung.

    Derselbe Weg wie `_zustand_pfad()` - dieselbe Stufe, dieselbe Datei. Eine
    eigene Lesefunktion waere eine zweite Wahrheit: mit STUFE 'mittel' laesst
    sie die .mittel-Datei lesen und der Tagesbericht spricht ueber die Basis.
    Fehlt die Datei, ist das ein leeres Buch, nicht ein Fehler - deshalb `{}`
    statt einer Exception, und der Aufrufer faellt auf die Wachen zurueck.
    """
    try:
        with open(_zustand_pfad(spur), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _scanner_wachen_quote():
    """`universum.quotes` aus der Scanner-Wache - die Handelswaehrung."""
    ordner, datei = _ort("scanner", "wachen.json")
    try:
        with open(HIER / ordner / datei, encoding="utf-8") as f:
            w = json.load(f)
        quotes = (w.get("universum") or {}).get("quotes") or []
        if quotes:
            return str(quotes[0]).upper()
    except (OSError, ValueError):
        pass
    return "USDC"       # laeferweise USDC (02.10.2026): Guthaben UND Markt


def einheit_fuer(spur, z=None):
    """Die Waehrung, in der die Zahlen dieser Spur stehen.

    Fuer kraken und scanner wird sie aus dem BUCH abgeleitet, nicht aus der
    Tabelle: steht das Buch einmal in USDC, sind die Betraege richtig und ihre
    Einheit waere in der Tabelle falsch - genau die Klasse Anzeigefehler, die
    am 23.09.2026 bei mosaic einen BTC-Kurs aus der falschen Boerse zeigte
    und die am 05.10.2026 beim Guthabenabgleich 0,00 USDT statt 302,39 USDC
    auswies (T-311).
    """
    if spur == "kraken":
        return kraken_buch_waehrung(z)
    if spur == "scanner":
        return scanner_buch_quote(z)
    return EINHEIT.get(spur, "USD")


def runden_fuer(spur, z=None, gebuehr=None, stand=None):
    """Die GESCHLOSSENEN Runden einer Spur als Liste - die Zuordnung Spur ->
    Rechenweg steht hier und NUR hier (bis 29.09.2026 stand sie in
    `kennzahlen_fuer`; ein zweiter Aufrufer haette sie abschreiben muessen).

    Rueckgabe: Liste von dicts mit `ergebnis`, `einsatz`, `grund` usw. - die
    Form, die die `runden_*`-Funktionen liefern. `kennzahlen()` rechnet daraus
    die Aggregate, `kennzahlen_strategie.py` die Verteilung (t-Statistik,
    Stop aus der MAE der Gewinner).
    """
    if z is None:
        z = zeilen(spur)
    if gebuehr is None:
        gebuehr = gebuehr_fuer(spur)
    if not z:
        return []
    if spur in ("xperp", "swap"):
        return runden_xperp(z, stand=stand)
    if spur == "scanner":
        return runden_spot(z, 0.0005, stand=stand)
    if spur == "kraken":
        return runden_spot(z, gebuehr, einsatz_feld="eur", stand=stand)
    if spur in ("orb", "orbk"):
        return runden_orbk(z)
    if spur == "omniquant":
        return runden_omniquant(z, stand=stand)
    if spur in INDIKATOR_SPUREN or spur in BOT_SPUREN:
        return runden_indikator(z, stand=stand)
    if spur in NAUTILUS_SPUREN:
        return runden_nautilus(z, stand=stand)
    if spur == "gitter":
        return gitter_zyklen(z)
    return []


# AB WANN EIN JOURNAL ETWAS BELEGT. Der Scanner nahm bis zum 03.10.2026 als
# Einstieg den Preis des Vortagesberichts statt des Marktkurses (Befund
# scanner/BEFUND-einstiegspreis-20261003.md): Ziel lag beim Kauf schon im
# Markt, ein Instrument wurde alle 15 Minuten neu gekauft und im "Ziel"
# verkauft. Die Runden davor messen den Rechenfehler, nicht das Signal
# (t = 15,3 bei Haltedauer-Median 0,0 Tage). Gilt der EINSTIEG vor diesem
# Zeitpunkt, zaehlt die Runde nicht - auch wenn sie danach ausstieg, denn
# der falsche Einstiegspreis steckt dann in ihrem Ergebnis. Zeitpunkt = Commit
# 5c8dc582 (02.10.2026 22:23:13 UTC); der Dauerlauf startet das Skript je
# Zyklus neu, die Wirkung setzte also binnen Minuten ein.
# `--alles` schaltet den Filter ab (Vergleich mit den alten Zahlen).
GUELTIG_AB = {"scanner": "2026-10-02T22:23:13+00:00"}


def _vor_fix(r, grenze):
    """Gehoert die Runde in die Fehlerzeit? Ohne lesbare Einstiegszeit: ja -
    ihre Unschuld ist nicht belegbar (gleiche Linie wie zeitfenster)."""
    d = zeitfenster.parse(r.get("einstieg_zeit"))
    return d is None or d < grenze


def kennzahlen_fuer(spur, von=None, bis=None, nur_gueltige=True):
    """Die Kennzahlen EINER Spur - Zuordnung Spur -> Rechenweg an EINER Stelle.

    Der Weg stand bis zum 15.09.2026 nur in `main()`. Ein zweiter Aufrufer
    (die Telegram-Befehle in `befehle.py`) haette die Zuordnung abschreiben
    muessen - und beim naechsten neuen Feld nur an einer Stelle mitgezogen.
    `main()` und `befehle.py` rufen jetzt beide diese Funktion.

    von/bis mit Vorgabe None: ohne Angabe bleibt alles wie vorher.

    nur_gueltige: Runden, deren Einstieg vor `GUELTIG_AB[spur]` liegt, werden
    nicht mitgerechnet, aber AUSGEWIESEN (`paarung["vor_fix"]`, `"vor_fix_ergebnis"`).
    Nur Spuren in GUELTIG_AB sind betroffen; alle anderen rechnen unveraendert.

    DAS FENSTER SCHNEIDET RUNDEN, NICHT ZEILEN. Eine Runde gehoert in das
    Fenster ihres AUSSTIEGS - dort faellt ihr Ergebnis an. Der Schnitt
    passiert deshalb NACH der Paarung. Ein Schnitt davor (bis 18.09.2026)
    verwarf jede Runde, die vor dem Fenster einstieg und darin ausstieg:
    _paare() sah einen Ausstieg ohne Einstieg und liess ihn fallen. Die
    Zahl war zu klein, und niemand erfuhr davon. Dieselbe Lesart hat
    buchauswertung.lade_zeilen(), das ohnehin nur Ausstiegszeilen liest -
    erst damit beantworten beide Wege in gesamtbilanz.summe() dieselbe
    Frage.

    Rueckgabe: das dict aus `kennzahlen()`, oder None wenn die Spur keine
    geschlossenen Runden hat (bzw. gar kein Journal).
    """
    z = zeilen(spur)
    if not z:
        return None
    stand = {}
    runden = runden_fuer(spur, z, stand=stand)
    runden = [r for r in runden if zeitfenster.im_fenster(r, von, bis)]
    if nur_gueltige and spur in GUELTIG_AB:
        grenze = zeitfenster.parse(GUELTIG_AB[spur])
        alt = [r for r in runden if _vor_fix(r, grenze)]
        runden = [r for r in runden if not _vor_fix(r, grenze)]
        stand["vor_fix"] = len(alt)
        stand["vor_fix_ergebnis"] = sum(r["ergebnis"] for r in alt)
    k = kennzahlen(runden, einheit_fuer(spur),
                   gebuehr=gebuehr_fuer(spur),
                   brutto=spur not in GEBUEHR_SCHON_DRIN)
    # Die Zuordnung wird MITGELIEFERT, nicht verschwiegen: eine Runde, die
    # keinen Partner fand, fehlt sonst still in der Quote (T-095). `kennzahlen`
    # gibt None zurueck, wenn nur Zwangsschluesse im Journal stehen - dann gibt
    # es keine Kennzahl, an die man die Zahlen haengen koennte.
    if k is not None:
        k["paarung"] = stand
    return k


def belastbar(k, min_runden=None):
    """Sagt die Spur im gewaehlten Fenster ueberhaupt etwas?

    Die Schwelle gilt JE FENSTER. Ein Monat mit drei Runden ist keine
    Aussage, auch wenn die Spur insgesamt fuenfzig hat - sonst erzeugt die
    Zeitachse genau die Scheingenauigkeit, die MIN_RUNDEN verhindern soll.
    """
    if not k:
        return False
    return k.get("n", 0) >= (MIN_RUNDEN if min_runden is None else min_runden)


def hat_buch(spur, datei="handelsjournal.csv"):
    """Fuehrt die Spur ueberhaupt ein Journal?

    Getrennt von "hat Runden": eine Spur ohne Datei und eine Spur mit leerer
    Datei sind verschiedene Befunde, und nur der erste ist ein
    Betriebsfehler.
    """
    if STUFE:
        datei = risikostufe.datei_fuer(datei, STUFE)
    ordner, datei = _ort(spur, datei)
    return (HIER / ordner / datei).exists()


def buch_seit(spur):
    """Seit wann die Spur laeuft, soweit der Baum es hergibt.

    Quelle ist die Aenderungszeit von `zustand.json` - ohne Journal gibt es
    keine andere. Das ist ein Anhaltspunkt, keine Anmeldung: die Datei wird
    bei jedem Lauf angefasst. Sie beantwortet trotzdem die Frage, auf die es
    ankommt - laeuft die Spur, obwohl sie nichts schreibt?
    """
    p = HIER / spur / "zustand.json"
    if not p.exists():
        return None
    return datetime.fromtimestamp(p.stat().st_mtime).date()


def lage_der_spur(spur, k):
    """Eine von drei Kategorien - nie ein blosser Strich."""
    if not hat_buch(spur):
        return "kein Buch"
    if not belastbar(k):
        return "zu wenige Runden"
    return "belastbar"


def offene_positionen(spur):
    """Wie viele Positionen im Buch stehen, obwohl keine Runde geschlossen ist.

    Warum (29.09.2026): "keine geschlossene Runde" liest sich wie "diese Spur
    tut nichts". Am selben Tag standen bei macd_mtf vier und bei supertrend vier
    Positionen im Buch - beide Spuren ARBEITEN, ihr Stop wurde nur noch nicht
    erreicht. Und bei nautilus_kraken standen vier AUSBUCHUNGEN (buchbereinigung)
    im Journal: auch die sind keine Handelsrunde, aber sie sind etwas anderes als
    ein leeres Journal. Ohne diese Zahl sind wartender Stop, Ausbuchung und tote
    Spur nicht zu unterscheiden.
    """
    p = HIER / spur / "zustand.json"
    try:
        with open(p, encoding="utf-8") as f:
            z = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(z, dict):
        return None
    pos = z.get("positionen")
    return len(pos) if isinstance(pos, list) else None


def anzeige_fuer(spur, k):
    """Der Text der Lage-Spalte in der Uebersicht - eine von vier
    Kategorien, an genau dieser Stelle entschieden.

    lage_der_spur() kennt nur drei: sie geht von einem Journal aus. Die
    vierte - ein vorhandenes Buch ganz ohne geschlossene Runde (`k is
    None`) - liegt zwischen "kein Buch" und "zu wenige Runden" und braucht
    einen eigenen Text, sonst sieht sie wie "kein Buch" aus.
    """
    if not hat_buch(spur):
        return "kein Buch"
    if k is None:
        return "keine geschlossene Runde"
    return lage_der_spur(spur, k)


def prozent(x, stellen=2):
    """Eine Zahl mit Vorzeichen, oder n/a. Kein Lambda: die Verkettung
    'Pattern bauen' + 'formatieren' hat hier still den Rohling ausgegeben."""
    if x is None:
        return "n/a"
    return ("%+." + str(stellen) + "f") % x


def zahl(x):
    """Ein Feld als Zahl, oder None. Leere Zellen sind keine Null."""
    if x is None:
        return None
    s = str(x).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def zeilen(spur, datei="handelsjournal.csv"):
    """Die Journalzeilen einer Spur - alle, ungeschnitten.

    Kein Zeitfenster. Wer in Runden zaehlt, braucht ALLE Zeilen: die
    Paarung in _paare() findet den Einstieg sonst nicht, wenn er vor dem
    Fenster liegt, und verwirft die Runde stillschweigend. Geschnitten wird
    nach der Paarung, an der Ausstiegszeit - siehe kennzahlen_fuer().
    """
    if STUFE:
        # Risikostufe: dieselbe Auswertung auf den Dateien der Stufe
        # (handelsjournal.mittel.csv). Der Rechenweg bleibt derselbe - die
        # Betraege sind groesser, die Regeln nicht anders.
        datei = risikostufe.datei_fuer(datei, STUFE)
    ordner, datei = _ort(spur, datei)
    p = HIER / ordner / datei
    if not p.exists():
        return []
    with p.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def tage(von, bis):
    """Haltedauer in Tagen aus zwei ISO-Zeitstempeln."""
    try:
        a = datetime.fromisoformat(von)
        b = datetime.fromisoformat(bis)
    except (TypeError, ValueError):
        return None
    return (b - a).total_seconds() / 86400.0


def kennzahlen(runden, einheit, gebuehr=None, brutto=None):
    """Die gemeinsame Ausgabe. runden = Liste von dicts mit ergebnis/einsatz.

    ZWANGSSCHLUESSE ZAEHLEN NICHT MIT. Ein Ausstieg mit herzschlag im Grund
    ist keine Handelsentscheidung, sondern die Folge eines Ausfalls (der
    Waechter stellt die Spur flach, wenn der Dauerlauf zu lange stand). Er
    steht trotzdem im Journal und wuerde sonst als Runde mitgezaehlt: die
    Rundenzahl waere zu hoch, die Trefferquote zu niedrig, weil die
    Zwangsschluesse meist im Verlust sitzen. Beides wird deshalb getrennt
    ausgewiesen - nicht versteckt, nur nicht vermischt.

    BRUTTO ODER NETTO (T-192, 01.10.2026): Die meisten Papierbuecher schreiben
    ihre Zeilen OHNE Kosten - die Summe ist dann brutto und mit einer
    Live-Rechnung nicht vergleichbar. Hier wird die Gebuehr deshalb NICHT
    stillschweigend abgezogen, sondern als eigene Zahl daneben gestellt:
    `brutto` sagt, ob das Ergebnis die Gebuehr noch enthaelt, `netto` ist das
    Ergebnis nach `2 x gebuehr x einsatz` (Kauf und Verkauf). Fuer Spuren, die
    die Gebuehr schon im Journal tragen (GEBUEHR_SCHON_DRIN), wird NICHT
    gerechnet - zweimal abziehen waere genauso falsch wie gar nicht.
    """
    echt = [r for r in runden if not stoerungen.ist_stoerung(r.get("grund"))]
    stoer = [r for r in runden if stoerungen.ist_stoerung(r.get("grund"))]
    if not echt:
        return None
    runden = echt
    ergebnisse = [r["ergebnis"] for r in runden]
    einsatz = sum(r["einsatz"] for r in runden)
    erloes = sum(r["ergebnis"] + r["einsatz"] for r in runden)
    pcts = [100.0 * r["ergebnis"] / r["einsatz"] for r in runden
            if r["einsatz"]]
    treffer = sum(1 for r in runden if r["ergebnis"] > 0)
    halten = [r["halten"] for r in runden if r.get("halten") is not None]
    if brutto is None:
        # VORGABE BRUTTO: diese Funktion zieht NIE etwas von `ergebnis` ab -
        # die Zahl ist genau die aus dem Journal. Ob darin schon eine Gebuehr
        # steckt, weiss nur der Aufrufer (`GEBUEHR_SCHON_DRIN`) und sagt es
        # ueber diesen Parameter. Ohne Angabe ist die ehrliche Antwort
        # "brutto" (die Gebuehr ist nicht nachweislich enthalten).
        brutto = True
    gebuehr = float(gebuehr or 0.0)
    # Bei brutto=False steckt die Gebuehr schon in der Journalzahl - dann wird
    # sie NICHT noch einmal abgezogen. Zweimal abziehen waere so falsch wie
    # gar nicht: dieselbe Rechnung, nur mit dem anderen Vorzeichen.
    kosten_netto = einsatz * 2.0 * gebuehr if brutto else 0.0
    ergebnis = erloes - einsatz
    return {
        "n": len(runden), "einheit": einheit, "einsatz": einsatz,
        "erloes": erloes, "ergebnis": ergebnis,
        "pct": 100.0 * ergebnis / einsatz if einsatz else 0.0,
        # Brutto/Netto: brutto=True heisst, `ergebnis` enthaelt die Gebuehr
        # noch. `netto` wird nur gerechnet, wenn eine Gebuehr bekannt ist.
        "brutto": brutto,
        "gebuehr": gebuehr,
        "kosten_netto": kosten_netto,
        "netto": ergebnis - kosten_netto,
        "netto_pct": (100.0 * (ergebnis - kosten_netto) / einsatz
                      if einsatz else None),
        "median_pct": statistics.median(pcts) if pcts else None,
        "treffer": treffer,
        "treffer_pct": 100.0 * treffer / len(runden),
        "best": max(pcts) if pcts else None,
        "schlecht": min(pcts) if pcts else None,
        "halten_tage": statistics.median(halten) if halten else None,
        "gruende": _zaehle(r["grund"] for r in runden),
        "kosten_anteil": _kosten_anteil(runden),
        # Ergebnis in R, wenn das Buch KEINEN Einsatz fuehrt (ORB-Spuren).
        "r": r_kennzahlen(runden),
        # Separat, nicht eingerechnet: die Fehleranalyse.
        "n_stoerung": len(stoer),
        "stoerung_ergebnis": sum(r["ergebnis"] for r in stoer) if stoer else 0.0,
        "runden_gesamt": len(echt) + len(stoer),
    }


def paarung_text(p):
    """Die Paarungszahlen als EINE Zeile - 'was nicht gepaart wurde, wird
    ausgewiesen' (T-095). Ohne sie sieht ein Journal mit vielen uebersprungenen
    Zeilen aus wie eine kleine Stichprobe."""
    teile = []
    if p.get("unpaarig"):
        zusatz = ""
        if p.get("zweideutig"):
            zusatz = " (davon %d zweideutig - nicht geraten)" % p["zweideutig"]
        teile.append("%d Ausstieg(e) ohne Partner%s" % (p["unpaarig"], zusatz))
    if p.get("ohne_kennung"):
        teile.append("%d Einstieg(e) ohne pos_id (Altjournal)"
                     % p["ohne_kennung"])
    if p.get("offen"):
        teile.append("%d Position(en) offen" % p["offen"])
    if p.get("vor_fix"):
        teile.append("%d Runde(n) mit Einstieg vor dem Preisfix NICHT mitgezaehlt "
                     "(Scheinergebnis %+.2f; --alles zeigt sie)"
                     % (p["vor_fix"], p.get("vor_fix_ergebnis") or 0.0))
    return "; ".join(teile) or "vollstaendig gepaart"


def _zaehle(werte):
    aus = {}
    for w in werte:
        w = (w or "ohne").strip() or "ohne"
        aus[w] = aus.get(w, 0) + 1
    return dict(sorted(aus.items(), key=lambda kv: -kv[1]))


def _kosten_anteil(runden):
    """Kosten in Prozent des Einsatzes, soweit das Journal sie hergibt."""
    if any(r.get("kosten") is None for r in runden):
        return None
    einsatz = sum(r["einsatz"] for r in runden)
    if not einsatz:
        return None
    return 100.0 * sum(r["kosten"] for r in runden) / einsatz


def _paare(zeilen_, einstieg_namen, ausstieg_namen, einsatz_feld, ergebnis_fn,
           einheit, grund_feld="grund", stand=None):
    """Einstiege und Ausstiege einander zuordnen und daraus Runden bauen.

    DIE ZUORDNUNG STEHT IN `journalpaarung.Paarung` (Kennung zuerst, sonst nur
    eindeutige Faelle) - hier bleibt nur, was diese Auswertung rechnet: Einsatz,
    Erloes, Ergebnis. Kein Nachrechnen von Kursen: Erloes und Einsatz stehen in
    den Zeilen - was nicht in den Zeilen steht, wird nicht erfunden.

    WARUM NICHT MEHR HIER (T-095, 30.09.2026): bis hierher lag jede offene
    Position in einem Dict `offen[inst]` - zwei gleichzeitige Positionen im
    selben Instrument ueberschrieben einander, der erste Ausstieg paarte mit dem
    falschen Einstieg oder fiel ganz weg. Gemessen im Backtest ueber 5,7 Jahre:
    squeeze 1092 Einstiege und 1088 Ausstiege, aber nur 759 ausgewertete Runden
    (macd_mtf 774 von 1209, wavetrend 1128 von 1506). Die Quote stand damit auf
    einer nicht zufaelligen Teilmenge - gleichzeitige Positionen im selben
    Instrument sind eher gleichgerichtet.

    `stand` ist ein dict, das die Zahlen der Zuordnung aufnimmt (`unpaarig`,
    `zweideutig`, `ohne_kennung`, `offen`) - sie werden AUSGEWIESEN, nicht
    verschwiegen. Ohne `stand` aendert sich am Ergebnis nichts.
    """
    p = jp.Paarung(einstieg=einstieg_namen, ausstieg=ausstieg_namen)
    runden = []
    for ein, r in p.zuordnen(zeilen_):
        schluessel = jp.schluessel(ein)
        if isinstance(einsatz_feld, tuple):
            # Mehrere Schreibweisen desselben Betrags: der OKX-Arm der
            # Nautilus-Gruppe fuehrt `einsatz_usd`, der Kraken-Arm
            # `einsatz_eur`. Der erste gefuellte Name gewinnt.
            einsatz = next((zahl(ein.get(f)) for f in einsatz_feld
                            if zahl(ein.get(f))), None)
        else:
            einsatz = zahl(ein.get(einsatz_feld))
        if not einsatz:
            continue
        ergebnis, kosten = ergebnis_fn(ein, r)
        if ergebnis is None:
            continue
        runden.append({
            "inst": schluessel, "einsatz": einsatz, "ergebnis": ergebnis,
            "kosten": kosten, "grund": (r.get(grund_feld) or "").strip() or None,
            "halten": tage(ein.get("zeit"), r.get("zeit")),
            "einstieg_zeit": ein.get("zeit") or "",
            # Die Zeit der Runde ist die ihres AUSSTIEGS - dort faellt das
            # Ergebnis an. Der Name `zeit` ist der der Journalspalte, damit
            # zeitfenster.im_fenster() die Runde ohne Sonderfall liest.
            "zeit": r.get("zeit") or "",
        })
    if stand is not None:
        stand.update(p.stand())
    return runden


def runden_xperp(zeilen_, stand=None):
    """Hebelspuren: Einsatz ist die Margin, Erloes die Margin beim Ausstieg."""
    def ergebnis(ein, aus):
        margin = zahl(ein.get("margin_usd"))
        erloes = zahl(aus.get("margin_usd"))
        if not (margin and erloes):
            return None, None
        nominal = zahl(ein.get("nominal_usd")) or 0.0
        gebuehr = (zahl(ein.get("gebuehr_pct")) or 0.0) + \
                  (zahl(aus.get("gebuehr_pct")) or 0.0)
        funding = zahl(aus.get("funding_pct")) or 0.0
        kosten = nominal * gebuehr + nominal * abs(funding)
        return erloes - margin, kosten

    return _paare(zeilen_, {"eroeffnen"}, {"schliessen"}, "margin_usd", ergebnis,
                  "USD", stand=stand)


def runden_spot(zeilen_, kosten_pct=0.0, einsatz_feld="usd", stand=None):
    """Spot (scanner, kraken): Einsatz und Erloes stehen als Betrag in der Zeile.
    Die Gebuehr ist bei scanner/kraken schon eingerechnet; kosten_pct ist nur
    fuer die Anzeige, wie viel davon Gebuehr war."""
    def ergebnis(ein, aus):
        einsatz = zahl(ein.get("usd") if ein.get("usd") is not None
                       else ein.get("eur"))
        erloes = zahl(aus.get("usd") if aus.get("usd") is not None
                      else aus.get("eur"))
        if not (einsatz and erloes is not None):
            return None, None
        return erloes - einsatz, einsatz * kosten_pct

    return _paare(zeilen_, {"kauf"}, {"verkauf"}, einsatz_feld, ergebnis,
                  "USD", stand=stand)


def runden_indikator(zeilen_, stand=None):
    """Indikatorspuren: kauf/verkauf, Betrag in `einsatz_usd`.

    Derselbe Feldname traegt beim Kauf den Einsatz und beim Verkauf den Erloes.
    Eine Gebuehr fuehren diese Spuren nicht (kein `gebuehr_taker` in ihrer
    wachen.json), also wird auch keine behauptet - kosten = 0. Sobald eine
    Gebuehr im Journal steht, gehoert sie hier gelesen, nicht geschaetzt.

    ACHTUNG: Bis zum 15.09.2026 schrieb die Spur den Erloes als
    `nominal + (kurs - einstieg)` - die rohe Kursdifferenz, bei BTC ein Faktor
    von rund 70.000. Zeilen aus jener Zeit liegen als
    `handelsjournal.falsch-skaliert-20260915.csv` daneben und zaehlen nicht.
    """
    def ergebnis(ein, aus):
        einsatz = zahl(ein.get("einsatz_usd"))
        erloes = zahl(aus.get("einsatz_usd"))
        if not einsatz or erloes is None:
            return None, None
        return erloes - einsatz, 0.0

    # SKALIERTE POSITIONEN (03.10.2026): dieselbe pos_id kann mehrere
    # Kaufzeilen tragen - die zweite ist eine Vergroesserung und rechnet den
    # KUMULATIVEN Einsatz mit dem GEWOGENEN Einstieg. Die Zuordnung in
    # journalpaarung nimmt dann die LETZTE dieser Zeilen, also den Stand
    # der Position; gegengeprobt in tests/test_skalieren.py (mit
    # zurueckgenommener Skalierungsregel wird derselbe Test rot, nicht
    # dieser Weg - er war nie der Weg, der es richtig machte).
    return _paare(zeilen_, {"kauf"}, {"verkauf"}, "einsatz_usd", ergebnis, "USD",
                  stand=stand)


def runden_nautilus(zeilen_, stand=None):
    """Die drei Papier-Arme der Nautilus-Gruppe: eroeffnen/schliessen.

    Einsatz und Erloes stehen als BETRAG in der Zeile - `einsatz_usd`/`wert_usd`
    beim OKX- und beim Futures-Arm, `einsatz_eur`/`wert_eur` beim Kraken-Spot-Arm.
    Der G/V ist die Differenz, dieselbe Rechnung wie bei den Indikator-Spuren.

    WARUM ES DIESE FUNKTION GIBT (28.09.2026): die drei Arme standen in SPUREN,
    hatten aber keinen Zweig in kennzahlen_fuer() und fielen in den else-Zweig -
    sie meldeten "keine geschlossene Runde", obwohl im Journal sieben (nautilus)
    bzw. vier (nautilus_kraken) geschlossene Runden standen. Eine Auswertung,
    die eine ganze Spurgruppe still auf null setzt, ist der Grund, warum eine
    Verbesserung nicht sichtbar wird: niemand kann eine Zahl beurteilen, die
    nie gerechnet wurde.
    """
    def ergebnis(ein, aus):
        einsatz = zahl(ein.get("einsatz_usd"))
        if einsatz is None:
            einsatz = zahl(ein.get("einsatz_eur"))
        erloes = zahl(aus.get("wert_usd"))
        if erloes is None:
            erloes = zahl(aus.get("wert_eur"))
        if not einsatz or erloes is None:
            return None, None
        return erloes - einsatz, 0.0

    return _paare(zeilen_, {"eroeffnen"}, {"schliessen"},
                  ("einsatz_usd", "einsatz_eur"), ergebnis, "USD", stand=stand)


def runden_omniquant(zeilen_, stand=None):
    """omniquant: EINSTIEG/eroeffnen (Einstieg) und AUSSTIEG/schliessen (Ausstieg).

    Die Spur schreibt im Papierzweig EINSTIEG/AUSSTIEG (handeln.py), im
    Live-Zweig eroeffnen/schliessen (live_perp.py). Einsatz steht in
    `einsatz_usd`, der Erloes in `wert_usd` - der G/V ist die Differenz,
    dieselbe Rechnung wie bei den Indikator-Spuren.

    WARUM ES DIESE FUNKTION GIBT (T-389, 11.10.2026): omniquant stand in
    BOT_SPUREN und fiel damit in runden_indikator, der kauf/verkauf paart.
    Die Spur schreibt aber EINSTIEG/AUSSTIEG und eroeffnen/schliessen -
    die Auswertung meldete 0 Runden trotz 37 EINSTIEG- und 20 AUSSTIEG-Zeilen.
    Eine Auswertung, die eine ganze Spur still auf null setzt, macht jede
    Verbesserung unsichtbar.

    buchbereinigung-Zeilen (schliessen mit grund=buchbereinigung) zaehlen
    NICHT als Runde: sie sind Buchhaltung, keine Handelsentscheidung
    (stoerungen.ist_stoerung erkennt den Grund). Der reale Verlust einer
    nachgebuchten Position steht in zustand.json `verluste_usd`, nicht hier.
    """
    def ergebnis(ein, aus):
        einsatz = zahl(ein.get("einsatz_usd"))
        erloes = zahl(aus.get("wert_usd"))
        if not einsatz or erloes is None:
            return None, None
        return erloes - einsatz, 0.0

    zeilen_ = [r for r in zeilen_ if (r.get("grund") or "") != "buchbereinigung"]
    return _paare(zeilen_, {"EINSTIEG", "eroeffnen"}, {"AUSSTIEG", "schliessen"},
                  "einsatz_usd", ergebnis, "USD", stand=stand)


def runden_orbk(zeilen_):
    """orb/orbk journalisieren die fertige Runde - hier wird nichts gepaart.

    DIESE BUECHER FUEHREN PUNKTE, KEIN GELD (T-192): `gv_usd` ist die
    Kursdifferenz mal `punkt_wert_usd` (bei den ORB-Instrumenten 1:1), also der
    Gewinn JE EINHEIT - eine Positionsgroesse gibt es in diesem Buch nicht.
    Deshalb steht hier `einsatz: 0.0` und KEIN erfundener Einsatz: die
    Positionsgroesse kaeme aus `risiko_pro_trade / stop_abstand` (SPEC.md), und
    der ORB-Stop ist die Range-Hoehe - bei ETH oft 0,4 %, das ergaebe ein
    Nominal von einigen tausend USD. Das ist eine Design-Entscheidung, keine
    Reparatur. Statt dessen steht das Ergebnis daneben in R:
    `gv / |einstieg - stop|`, groessenunabhaengig und zwischen beiden
    ORB-Spuren vergleichbar.
    """
    runden = []
    for r in zeilen_:
        gv = zahl(r.get("gv_usd"))
        if gv is None:
            gv = zahl(r.get("gv_punkte"))
        if gv is None:
            continue
        einstieg = zahl(r.get("einstieg"))
        stop = zahl(r.get("stop"))
        risiko = abs(einstieg - stop) if (einstieg and stop) else None
        runden.append({"inst": r.get("inst", ""), "einsatz": 0.0,
                       "ergebnis": gv, "kosten": 0.0,
                       "risiko": risiko,
                       "r_vielfaches": (gv / risiko) if risiko else None,
                       "grund": (r.get("ausgang") or "").strip() or None,
                       "halten": None, "zeit": r.get("zeit") or ""})
    return runden


def r_kennzahlen(runden):
    """Ergebnis in R (Vielfache des Risikos) - fuer Buecher ohne Einsatz.

    Rueckgabe None, wenn keine Zeile eine Risikostrecke traegt (dann wird
    nichts behauptet). Ein R ist der Gewinn geteilt durch den Abstand
    Einstieg->Stop, also die Groesse, die ein risikonormiertes Buch ohnehin
    anstrebt - hier ohne Positionsgroesse gerechnet.
    """
    rs = [r["r_vielfaches"] for r in runden
          if r.get("r_vielfaches") is not None]
    if not rs:
        return None
    return {"n": len(rs), "summe": sum(rs), "mittel": statistics.mean(rs),
            "best": max(rs), "schlecht": min(rs),
            "treffer_pct": 100.0 * sum(1 for x in rs if x > 0) / len(rs)}


# Die Aktionsnamen, mit denen gitter/handeln.py eine Stufe schliesst.
# `AUSSTIEG` ist der, den es wirklich schreibt (gitter/handeln.py:377);
# `VERKAUF` stand hier allein und traf damit keine einzige Zeile - der
# Rundenweg meldete fuer gitter immer null Zyklen, waehrend die eigene
# Auswertung der Spur dieselben Zeilen zaehlte.
GITTER_AUSSTIEG = ("AUSSTIEG", "VERKAUF")


def gitter_zyklen(zeilen_):
    """Ein Gitter-Zyklus ist der Ausstieg aus einer vorher gekauften Stufe.
    Der Gewinn steht als gw_usd in der Ausstiegszeile."""
    offen = {}
    zyklen = []
    for r in zeilen_:
        art = (r.get("aktion") or "").strip().upper()
        stufe = r.get("stufe")
        if art == "KAUF":
            offen.setdefault(stufe, []).append(r)
        elif art in GITTER_AUSSTIEG:
            kette = offen.get(stufe) or []
            if not kette:
                continue
            ein = kette.pop(0)
            gw = zahl(r.get("gw_usd"))
            einsatz = zahl(ein.get("einsatz_usd"))
            if gw is None or not einsatz:
                continue
            zyklen.append({"inst": r.get("inst", ""), "einsatz": einsatz,
                           "ergebnis": gw, "kosten": 0.0,
                           "grund": "Stufe %s" % stufe,
                           "halten": tage(ein.get("zeit"), r.get("zeit")),
                           "zeit": r.get("zeit") or ""})
    return zyklen


def _brutto_netto_text(k):
    """EINE Zeile, die sagt, ob die ausgewiesene Zahl brutto oder netto ist.

    T-192: Die Papierbuecher schreiben ihre Zeilen ohne Kosten, die Live-Spuren
    rechnen sie ein. Ohne diesen Hinweis liest man zwei Zahlen, die
    Verschiedenes bedeuten, als waeren sie vergleichbar.
    """
    geb = k.get("gebuehr") or 0.0
    if not k.get("brutto"):
        return ("Kosten im Journal enthalten - die Zahlen sind NETTO "
                "(%.3f %% je Seite)" % (100.0 * geb))
    if not geb:
        return ("BRUTTO und UNBEKANNT: kein gebuehr_taker in der wachen.json "
                "- die Zahl ist nicht als netto lesbar")
    if not k.get("einsatz"):
        return ("Gebuehr laut wachen.json %.3f %% je Seite - hier NICHT "
                "abziehbar (das Buch fuehrt keinen Einsatz)" % (100.0 * geb))
    if k.get("netto_pct") is None:
        return ("BRUTTO im Journal; netto nach %.3f %% je Seite: %+.2f %s"
                % (100.0 * geb, k["netto"], k["einheit"]))
    return ("BRUTTO im Journal; netto nach %.3f %% je Seite (Kauf+Verkauf): "
            "%+.2f %s (%+.2f %%)"
            % (100.0 * geb, k["netto"], k["einheit"], k["netto_pct"]))


def zeige(spur, k):
    if k is None:
        print("\n=== %s ===" % spur.upper())
        print("  keine geschlossenen Runden im Journal")
        offen = offene_positionen(spur)
        if offen:
            print("  aber %d offene Position(en) im Buch - die Spur arbeitet, "
                  "Stop/Ziel ist noch nicht erreicht." % offen)
        elif offen == 0:
            print("  und keine offene Position - die Spur wartet auf ihr "
                  "erstes Signal.")
        # Ausbuecher sind keine Runden, aber etwas anderes als ein leeres
        # Journal (nautilus_kraken, 29.09.2026: vier buchbereinigung-Zeilen).
        # kennzahlen() nimmt sie heraus, deshalb faellt die Spur hierher - die
        # Zeile sagt jetzt, dass daneben etwas passiert ist.
        try:
            daneben = sum(1 for r in runden_fuer(spur)
                          if stoerungen.ist_stoerung(r.get("grund")))
        except Exception:      # eine Anzeigezeile darf den Lauf nicht kippen
            daneben = 0
        if daneben:
            print("  daneben %d Ausstiege ohne Handelsentscheidung "
                  "(Buchhaltung/Zwang) - nicht in der Quote." % daneben)
        return
    p = prozent
    print("\n=== %s ===" % spur.upper())
    print("  %-28s %d" % ("geschlossene Runden", k["n"]))
    if k.get("n_stoerung"):
        print("  %-28s %d   (nicht mitgezaehlt: Ergebnis %+.2f %s)"
              % ("davon Zwangsschluesse", k["n_stoerung"],
                 k["stoerung_ergebnis"], k["einheit"]))
        print("  %-28s %d" % ("Runden mit Stoerungen", k["runden_gesamt"]))
    if k["einsatz"]:
        print("  %-28s %s" % ("Ergebnis", "%+.2f %s (%+.2f %%)"
                              % (k["ergebnis"], k["einheit"], k["pct"])))
    else:
        # OHNE EINSATZ GIBT ES KEINEN PROZENTWERT (T-192). Die Zahl ist die
        # Summe der Kursstrecken, kein Geldbetrag; "(+0.00 %)" waere eine
        # Behauptung ueber eine Rechnung, die nie stattfand.
        print("  %-28s %s" % ("Ergebnis", "%+.2f %s - kein Geldbetrag"
                              % (k["ergebnis"], k["einheit"])))
    print("  %-28s %.0f %%  (%d von %d)"
          % ("Treffer (Gewinn > 0)", k["treffer_pct"], k["treffer"], k["n"]))
    if k["einsatz"]:
        print("  %-28s %s %%   Median %s %%"
              % ("Ergebnis auf den Einsatz (gesamt)",
                 p(100.0 * k["ergebnis"] / k["einsatz"]),
                 p(k["median_pct"])))
    elif k.get("r"):
        r = k["r"]
        print("  %-28s kein Einsatz im Buch (Punktebuch) - Prozent nicht "
              "rechenbar" % "Ergebnis in Prozent")
        print("  %-28s %+.2f R gesamt, %+.3f R je Runde (Treffer %.0f %%, "
              "%d Runden mit Risikostrecke)"
              % ("Ergebnis in R", r["summe"], r["mittel"], r["treffer_pct"],
                 r["n"]))
    else:
        print("  %-28s kein Einsatz im Journal" % "Ergebnis in Prozent")
    if k["best"] is not None:
        print("  %-28s %s %% / %s %%"
              % ("beste / schlechteste Runde", p(k["best"]), p(k["schlecht"])))
    elif k.get("r"):
        print("  %-28s %+.2f R / %+.2f R"
              % ("beste / schlechteste Runde", k["r"]["best"],
                 k["r"]["schlecht"]))
    if k["kosten_anteil"] is not None:
        print("  %-28s %.2f %% vom Einsatz"
              % ("Kosten (aus den Zeilen)", k["kosten_anteil"]))
    print("  %-28s %s" % ("Brutto/Netto", _brutto_netto_text(k)))
    if k["halten_tage"] is not None:
        print("  %-28s %.1f Tage" % ("Haltedauer (Median)", k["halten_tage"]))
    print("  Ausstiegsgruende: %s"
          % ", ".join("%s %d" % (g, n) for g, n in k["gruende"].items()))
    p = k.get("paarung") or {}
    if p.get("unpaarig") or p.get("zweideutig") or p.get("ohne_kennung"):
        print("  %-28s %s" % ("Paarung", paarung_text(p)))
    if not belastbar(k):
        print("  -> nur %d Runden: das ist ein Befund, keine Messung. "
              "Belastbar wird es ab %d." % (k["n"], MIN_RUNDEN))


# --- Backtest (historisch) --------------------------------------------------
# Der Backtest ist eine MESSUNG, keine Live-Erfahrung: seine Runden zaehlen
# NICHT fuer die Freigabe-Bedingungen (Bedingung 1, Wissen/Handelsregeln.md).
# Deshalb steht er hier in einer EIGENEN Sektion und wird nirgends zu den
# Live-Runden addiert. Werkzeuge: replay.py, optimieren.py; Doku:
# Wiki/Handel/Backtest-Fundament.md
BACKTEST_WURZEL = Path(__file__).resolve().parent / "daten" / "backtest"


def _markenanteil(pfad):
    """Anteil der Stop-/Ziel-Ausstiege, die GENAU auf ihrer Marke liegen.

    Ein Lauf OHNE die Beruehrungsregel (vor T-177) schreibt dort den
    Kerzenschluss und kommt auf 0. Das ist der Unterschied, der bei
    gleicher Zeilenzahl entscheiden MUSS: sonst entscheidet der Name,
    und 'vor177' gewinnt gegen 'nach177', obwohl es der schlechtere Lauf
    ist. Ohne Stop-/Ziel-Zeilen gibt es nichts zu vergleichen -> 0.0.
    """
    import replay                                                # noqa: PLC0415

    try:
        z = replay.auf_der_marke(pfad)
    except Exception:                                            # noqa: BLE001
        return 0.0
    if not z.get("ausstiege"):
        return 0.0
    return z["ausstiege_an_marke"] / z["ausstiege"]


def backtest_stand(spur):
    """Ein Satz je Spur: was der Backtest sagt - oder warum er nichts sagt.

    Der Grund wird IMMER genannt. "kein Lauf" und "nicht nachrechenbar" sind
    verschiedene Dinge, und ein leeres Feld waere von einem Messwert nicht zu
    unterscheiden.
    """
    import replay                                                # noqa: PLC0415

    grund = replay.NICHT_NACHRECHENBAR.get(spur)
    if grund:
        return "nicht nachrechenbar (%s)" % grund
    ordner = BACKTEST_WURZEL / spur
    if not ordner.is_dir():
        return "kein Lauf - python replay.py --spur %s --lauf ganz" % spur
    # Der Lauf mit den MEISTEN Zeilen gewinnt, nicht der neueste: die
    # Parametersuche schreibt viele kurze Fensterlaeufe (6 Monate), deren
    # Zahlen neben einem Lauf ueber die ganze Historie irrefuehrend klein
    # waeren. Die Zeilenzahl ist der beste vorhandene Massstab fuer den
    # abgedeckten Zeitraum - und der wird mitgenannt.
    laeufe = []
    for name in sorted(p.name for p in ordner.iterdir() if p.is_dir()):
        pfad = ordner / name / "handelsjournal.csv"
        if pfad.is_file():
            with pfad.open(encoding="utf-8", newline="") as f:
                zeilen = sum(1 for _ in csv.reader(f)) - 1      # ohne Kopf
            # Bei GLEICHER Zeilenzahl entscheidet zuerst die Kerzenuhr (ein
            # alter Lauf ohne Zeitraum kann einen datierten verdecken - am
            # 2026-09-26 lagen zwei Laeufe mit je 2180 Zeilen nebeneinander,
            # der aeltere hiess 'ganz' und gewann; die Zeile sagte 'Zeitraum
            # unbekannt', obwohl daneben ein datierter lag), dann der ANTEIL
            # der Ausstiege auf der Marke (T-177: der Lauf mit der Regel
            # gewinnt gegen seinen Vorgaenger - vorher entschied der Name,
            # und 'vor177' stand hinter 'nach177'), zuletzt der Name.
            laeufe.append((zeilen, 1 if _hat_kerzenuhr(pfad) else 0,
                           round(_markenanteil(pfad), 6), name, pfad))
    if not laeufe:
        return "kein Lauf mit Journal"
    zeilen_zahl, _uhr, _marken, name, pfad = max(laeufe)
    try:
        k = replay.kennzahlen(pfad)
    except Exception as e:                                       # noqa: BLE001
        return "Journal nicht lesbar (%s)" % str(e)[:60]
    if not k.get("runden"):
        return "Lauf '%s' ohne auswertbare Runde" % name
    # Die Beruehrungsregel (T-177, 2026-09-30): steht die Marke in der Kerze,
    # ist sie der Ausstieg. Ein ALTER Lauf ohne die Regel schreibt dort den
    # Kerzenschluss - und ist an den Gewinnern zu gut. Die Quote steht deshalb
    # in jeder Zeile: `0/1506` verraet den Lauf von vorher.
    marken = ""
    if k.get("ausstiege"):
        marken = ", Ausstiege auf der Marke %d/%d" % (
            k.get("ausstiege_an_marke", 0), k["ausstiege"])
    return ("%d Runden, %.0f %% Treffer, %+.3f %% je Runde, %s (%d Zeilen, "
            "Lauf '%s'%s)"
            % (k["runden"], 100 * k.get("p", 0.0),
               k.get("ergebnis_summe", 0.0) / k["runden"],
               _backtest_zeitraum(pfad), zeilen_zahl, name, marken))


def _hat_kerzenuhr(pfad):
    """Traegt das Journal die Spalte `_kerzen_ts`? Nur der Kopf wird gelesen."""
    try:
        with pfad.open(encoding="utf-8", newline="") as f:
            kopf = f.readline()
    except OSError:
        return False
    return "_kerzen_ts" in kopf


def _backtest_zeitraum(pfad):
    """Der abgedeckte Zeitraum eines Backtest-Journals - aus den Kerzenstempeln."""
    try:
        with pfad.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except (OSError, ValueError):
        return "Zeitraum unbekannt"
    stempel = []
    for r in rows:
        ts = r.get("_kerzen_ts")
        if ts:
            try:
                stempel.append(float(ts))
            except (TypeError, ValueError):
                pass
    if not stempel:
        # Laeufe vor dem 2026-09-25 haben den Kerzenstempel nicht. Die Spalte
        # `zeit` waere die WANDUHR des Laufs - sie als Zeitraum auszugeben waere
        # eine falsche Aussage, deshalb steht hier der Grund.
        return "Zeitraum unbekannt (Lauf vor der Kerzenuhr)"
    fmt = lambda ms: datetime.fromtimestamp(ms / 1000.0, timezone.utc).strftime("%Y-%m")  # noqa: E731
    return "%s bis %s" % (fmt(min(stempel)), fmt(max(stempel)))


def main():
    global MIN_RUNDEN, STUFE
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(
        description="Auswertung der Spuren, die keine eigene haben")
    p.add_argument("--spur", action="append", choices=list(SPUREN),
                   help="nur diese Spur(en)")
    p.add_argument("--min", type=int, default=MIN_RUNDEN,
                   help="Schwelle fuer 'belastbar' (Standard %d)" % MIN_RUNDEN)
    p.add_argument("--risiko", choices=sorted(risikostufe.FAKTOREN),
                   default=risikostufe.STANDARD,
                   help="Risikostufe auswerten (Vorgabe %s = Basis). Liest "
                        "dieselben Spalten aus handelsjournal.mittel.csv - "
                        "die Runden sind andere, die Rechnung nicht."
                        % risikostufe.STANDARD)
    p.add_argument("--tage", type=int,
                   help="nur die letzten N Tage auswerten")
    p.add_argument("--alles", action="store_true",
                   help="auch Runden vor dem Preisfix (GUELTIG_AB) mitrechnen")
    p.add_argument("--seit", help="Fensteranfang, JJJJ-MM-TT")
    p.add_argument("--bis", help="Fensterende, JJJJ-MM-TT (einschliesslich)")
    a = p.parse_args()
    try:
        von, bis = zeitfenster.fenster(tage=a.tage, seit=a.seit, bis=a.bis)
    except ValueError as e:
        p.error(str(e))
    if von or bis:
        print("Fenster: %s bis %s\n"
              % (von.date() if von else "Anfang",
                 bis.date() if bis else "heute"))
    MIN_RUNDEN = a.min
    STUFE = None if a.risiko == risikostufe.STANDARD else a.risiko
    if STUFE:
        print("Risikostufe %s: eigene Journale je Spur "
              "(handelsjournal.%s.csv)\n" % (STUFE, STUFE))

    spuren = a.spur or list(SPUREN)
    zahlen = {}
    for spur in spuren:
        # Ein Weg fuer beide Aufrufer: hier stand die Zuordnung Spur ->
        # Rechenweg bis 15.09.2026 ein zweites Mal (siehe kennzahlen_fuer).
        k = kennzahlen_fuer(spur, von=von, bis=bis, nur_gueltige=not a.alles)
        zahlen[spur] = k
        zeige(spur, k)

    print("\n=== Uebersicht ===")
    print("  %-10s %6s %8s %10s %8s  %s"
          % ("Spur", "Runden", "Treffer", "Ergebnis", "Treffer %", "Lage"))
    ohne_buch = []
    for spur, k in zahlen.items():
        # Der Text kommt immer aus anzeige_fuer(); hier wird nur die
        # Zeilenform gewaehlt. Ein Vergleich auf den Text waere eine
        # zweite Heimat der Entscheidung - ein Umbenennen wuerde still
        # den Ablauf verbiegen.
        anzeige = anzeige_fuer(spur, k)
        if not hat_buch(spur):
            ohne_buch.append(spur)
            print("  %-10s %6s %8s %10s %8s  %s"
                  % (spur, "-", "-", "-", "-", anzeige))
            continue
        if k is None:
            print("  %-10s %6d %8s %10s %8s  %s"
                  % (spur, 0, "-", "-", "-", anzeige))
            continue
        print("  %-10s %6d %8d %10.2f %7.0f %%  %s"
              % (spur, k["n"], k["treffer"], k["ergebnis"],
                 k["treffer_pct"], anzeige))
    if ohne_buch:
        # ZWEI Faelle, die frueher in einen Topf geworfen wurden (21.09.2026):
        # Diese Spuren schreiben NUR Handelszeilen, keine Zykluszeilen - ein
        # fehlendes Journal heisst bei ihnen zuerst "noch kein Signal" und nicht
        # "kaputt" (supertrend, iv_wand, iv_waelle). Ein Betriebsfehler ist es
        # erst, wenn die Spur auch nicht mehr laeuft.
        heute = datetime.now().date()
        wartend, kaputt = [], []
        for spur in ohne_buch:
            seit = buch_seit(spur)
            frisch = seit is not None and (heute - seit).days <= 1
            (wartend if frisch else kaputt).append((spur, seit))
        if wartend:
            print("\n  WARTET AUF DAS ERSTE SIGNAL - diese Spuren schreiben nur "
                  "Handelszeilen:")
            for spur, seit in wartend:
                print("    %-10s Zustand zuletzt %s - laeuft, hat aber noch "
                      "nichts gekauft" % (spur, seit.isoformat() if seit else "nie"))
            print("  Kein Fehler: das Journal entsteht beim ersten Handel. Wer "
                  "wissen will, woran es haengt, fragt das Tor der Spur.")
        if kaputt:
            print("\n  KEIN BUCH UND LAEUFT NICHT - das ist ein Betriebsfehler:")
            for spur, seit in kaputt:
                print("    %-10s Zustand zuletzt %s"
                      % (spur, seit.isoformat() if seit else "nie"))
            print("  Erst den Betrieb pruefen (Dauerlauf-Log, Herzschlag), dann "
                  "das Buch - eine stehende Spur schreibt keine Zeilen.")
    print("\n  kopier, spiegel, omniquant und gitter haben eigene "
          "Auswertungen (auswertung.py im jeweiligen Ordner). kopier kommt "
          "hier NICHT vor: ihr Journal traegt token/symbol statt inst, eine "
          "Paarung ueber runden_nautilus ergab 107 Runden mit falscher "
          "Zuordnung (gemessen 03.10.2026).")
    if STUFE:
        print("  Gezaehlt wurde die Risikostufe %s - der Basislauf laeuft "
              "daneben unveraendert weiter." % STUFE)

    print("\n=== Backtest (historisch) - zaehlt NICHT fuer die Freigabe ===")
    for spur in spuren:
        print("  %-14s %s" % (spur, backtest_stand(spur)))
    print("  Runden aus historischen Daten sind eine Messung, keine "
          "Live-Erfahrung: sie fuellen keine Freigabe-Bedingung.")
    print("  Fahren: python replay.py --spur <spur> --lauf ganz | "
          "Suchen: python optimieren.py --spur <spur>")


if __name__ == "__main__":
    main()
