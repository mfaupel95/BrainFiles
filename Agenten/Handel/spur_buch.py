"""Das Haus-Buch der Bot-Spuren - eine Umsetzung fuer alle.

Jede Bot-Spur hat dieselbe Buchhaltung: Wachen (mit Risikostufe), Zustand,
Journal, Kopie ausser Haus (Bedingung 4), Groesse ueber die Ratsche, Stop und
Ziel, Positionsverwaltung. Was sie unterscheidet, ist allein die QUELLE und die
REGEL - und beides liefert die Spur selbst als zwei Funktionen:

    quelle(w)        -> {instrument: daten}       (Abruf, darf Fehler melden)
    signal(daten, w) -> "long" | "short" | None   (die Regel)

Warum eine gemeinsame Datei: drei Spuren mit drei Kopien derselben Buchhaltung
waeren drei Stellen, an denen ein Fehler (falscher G/V auf den Kurswert,
vergessene Spiegelung) einzeln auftreten kann. Dieselbe Ueberlegung wie bei
`ratschen.py` und `stoerungen.py`.

Grenze: `moondev_funding` fuehrt sein Buch noch selbst (es war die erste Spur
und ist einzeln getestet). Beim naechsten Anfassen gehoert es hierher.
"""

import csv
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

# --- Gemeinsame Abhaengigkeiten ueber den PFAD laden -----------------------
HANDEL = os.path.dirname(os.path.abspath(__file__))
SCANNER = os.path.join(HANDEL, "scanner")
# Bus fuer `ereignis.lauf` (Meldung an den Bus wie jede andere Spur). Er liegt
# neben dem Handel-Ordner; ohne den Pfad scheitert der Import im Test.
BUS = os.path.join(os.path.dirname(HANDEL), "Bus")
for _p in (SCANNER, HANDEL, BUS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from importlib.util import module_from_spec, spec_from_file_location  # noqa: E402

import wachen_pruefung as wp  # noqa: E402
import risikostufe  # noqa: E402
import atomar  # noqa: E402  (Zustand atomar schreiben, laut lesen)
import freigabefenster  # noqa: E402
import kill_gemeinsam as kg  # noqa: E402  (Kill-Frist/Reset/Opt-out, eine Stelle)
# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(os.path.abspath(__file__))
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
import basis_deckel_tor
import mae
import pos_kennung  # noqa: E402
import telemetrie  # noqa: E402  (Ereignisse nach tracking-plan.yaml, wirft nie)


def _lade_modul(name):
    spec = spec_from_file_location(name, os.path.join(HANDEL, name + ".py"))
    modul = module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


ratschen = _lade_modul("ratschen")
risikovorfilter = _lade_modul("risikovorfilter")
risikostufe = _lade_modul("risikostufe")

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund", "pos_id",
           # MFE/MAE seit 03.10.2026 - hier wirkt die Zeile auf alle 27
           # Spuren, die dieses Buch benutzen (T-119).
           "mfe_pct", "mae_pct", "haltetage"]

SCHREIBEN = True


def pformat(x):
    """Ein Preis ins Journal - mit genug Nachkommastellen, dass Einstieg und
    Stop unterscheidbar bleiben.

    `%.6f` reicht fuer BTC (60000.000000) nicht aber fuer die Mini-Preise der
    Sniper-Spur (~1e-6): dort stuerzen Einstieg und Stop beim Runden auf
    denselben String zusammen und die Auswertung liest G/V = 0. Die Zahl
    bestimmt die Nachkommastellen selbst: grosse Kurse bleiben 6 Stellen
    (unveraendert fuer die bestehenden Spuren), kleine bekommen mehr.
    """
    x = float(x or 0.0)
    ax = abs(x)
    if ax >= 1.0:
        return "%.6f" % x
    if ax >= 1e-6:
        return "%.8f" % x
    return "%.12f" % x

# Test-Seams, die jede Spur mitbenutzt: None -> echte Uhr/echte Quelle.
zeit_quelle = None


def jetzt():
    if zeit_quelle:
        return zeit_quelle()
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Dateien ---------------------------------------------------------------

def pfade(ordner):
    """(Wachen, Zustand, Journal) EINER Spur - Zustand/Journal je Risikostufe."""
    return (os.path.join(ordner, "wachen.json"),
            risikostufe.datei(os.path.join(ordner, "zustand.json")),
            risikostufe.datei(os.path.join(ordner, "handelsjournal.csv")))


def lade_wachen(wachen_pfad):
    with open(wachen_pfad, encoding="utf-8") as f:
        return risikostufe.skaliere(json.load(f))


def lade_zustand(zustand_pfad):
    return atomar.lade_json(zustand_pfad, lambda: {
        "positionen": [], "modus": "papier", "letzter_lauf": None,
        "verlust_usd": 0.0})


def schreibe_zustand(zustand_pfad, z):
    z["letzter_lauf"] = jetzt()
    atomar.schreibe_json(zustand_pfad, z)


def journal(journal_pfad, **felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(journal_pfad)
    # Die bestehende Datei behaelt ihre Kopfzeile (Altjournal ohne `pos_id`
    # bleibt lesbar, siehe pos_kennung.spalten) - eine Zeile mit mehr Feldern
    # als der Kopf waere keine Erweiterung, sondern eine Verschiebung aller
    # Spalten.
    spalten = pos_kennung.spalten(journal_pfad, SPALTEN) if not neu else SPALTEN
    with open(journal_pfad, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
        if neu:
            w.writeheader()
        w.writerow(felder)


def buche(z, zustand_pfad, journal_pfad, **felder):
    """EINE Buchung: Journalzeile UND Zustand in einem Aufruf.

    WARUM ES DAS GIBT (T-356, 05.10.2026): `pruefe_ausstiege()` schrieb die
    Verkaufszeile direkt ins Journal, `schreibe_zustand()` kam erst am Ende
    des Zyklus. Eine Vorschau, die zwischen den beiden zurueckkehrte, liess
    das Journal den Verkauf fuehren und der Zustand die Position noch offen -
    der Dauerlauf verkaufte sie dann jede Runde neu (NIGHT doppelt gebucht).

    Diese Funktion ist der EINZIGE Weg, eine Buchung zu schreiben: die Zeile
    und der dazugehoerige Zustand entstehen in einem Aufruf, es gibt keinen
    Rueckkehrpunkt dazwischen. `zustand_pfad` ist Pflicht - eine Buchung
    ohne Zustand ist ein Geist und bricht laut ab statt still zu schreiben.
    `SCHREIBEN=False` (Replay, Tests) schreibt gar nichts.
    """
    if not SCHREIBEN:
        return
    if zustand_pfad is None:
        raise ValueError("Buchung ohne Zustandspfad: Journal und Zustand "
                         "gehoeren zusammen (T-356)")
    journal(journal_pfad, **felder)
    schreibe_zustand(zustand_pfad, z)


def lege_journal_an(journal_pfad):
    """Das Journal anlegen, falls es fehlt - mit Kopfzeile, ohne Buchung.

    WARUM (Auftrag Max 02.10.2026, "alle duerfen auch journal fuehren"):
    `journal()` legt die Datei beim ersten SCHREIBEN an. Eine Spur, die noch
    nie ein Signal hatte, hatte deshalb gar kein Journal - und damit auch
    nichts ausser Haus (Bedingung 4). Am 02.10.2026 waren das 7 von 38 Spuren
    (klassik_donchian, klassik_donchian_trend, klassik_pmax, klassik_rsi,
    klassik_rsi2, klassik_sr_breaks, trendwende_btc): lokal wie auf Q: nur
    zustand.json, kein Journal. Das ist kein Defekt, aber es ist auch nicht
    beantwortbar - man kann nicht unterscheiden "noch nie ein Signal" von
    "das Journal ist kaputt".

    Die leere Datei macht genau das unterscheidbar: sie existiert, hat null
    Zeilen und wird gespiegelt. Ein Leser sieht damit denselben Stand wie
    bei einer Spur mit Runden, nur eben bei null.

    `SCHREIBEN=False` (Replay, Tests) legt nichts an - ein Test darf nie in
    einen echten Zielpfad schreiben.
    """
    if not SCHREIBEN or os.path.exists(journal_pfad):
        return False
    with open(journal_pfad, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=SPALTEN).writeheader()
    return True


def spiegeln(zustand_pfad, journal_pfad, z, w):
    """Bedingung 4: Journal und Zustand ausser Haus (Muster swap/handeln.py)."""
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([journal_pfad, zustand_pfad], ziel)
    if wp.vermerke_spiegelung(z, ziel, ok, info,
                              lambda zz: schreibe_zustand(zustand_pfad, zz)) and ok:
        wp.spiegele_journal([zustand_pfad], ziel)


# --- Positionen ------------------------------------------------------------

def groessenfaktor(ruecklauf, w):
    return ratschen.groessenfaktor(ruecklauf, w)


# --- Der Grund des Einstiegs ------------------------------------------------
#
# T-142/T-178 (gemsessen 29.09.2026, 18 Einstiegszeilen der Feed-Spuren): die
# Spalte `grund` der Einstiegszeile trug den Satz "Der Grund, der im Journal
# steht." - der Platzhalter stand auch im ECHTEN Journal vom 15.09.2026, kam
# also aus `spur_buch` und nicht aus dem Backtest. Folge: wer ein Buch liest,
# kann nicht sagen, welches Signal gegriffen hat; eine Auswertung, die den
# Grund lesen will, liest Nichts.
#
# Die Reihenfolge ist eine Prioritaeten-Kette, kein_if-Fallback:
#   1. `_grund` in der wachen - die Spur weiss mehr als der Kern. Die drei
#      LLM-Spuren (moondev_whale/-liquidation/-sentiment) schreiben hier
#      Aktion und Confidence des Modells hinein, IV-Waelle den Ausloeser.
#   2. `begruendung(d, w, seite)` - eine Spur, die einen ausformulierten
#      Grund liefert (Signal + gemessene Groesse in einem Satz).
#   3. der gemessene Ersatz: Spurname, Richtung und die Groessen, an denen das
#      Signal gehangen hat. Auch das ist eine Auskunft - im Gegensatz zum
#      Platzhalter nennt es Zahlen, an denen man den Einstieg nachrechnen kann.
#
# Der Platzhalter-Satz selbst wird erkannt und NIEMALS geschrieben: ein
# zukünftiger `_grund` in einer wachen darf die Angabe nicht wieder kippen.

PLATZHALTER = ("der grund, der im journal steht", "platzhalter")

# Die Felder, die ein Signal typischerweise ausloesen - in dieser Reihenfolge,
# damit die wichtigste Groesse vorn steht. Alles Weitere wird danach
# alphabetisch nachgezogen, damit auch eine unbekannte Spur eine Zahl liefert.
MESSFELDER = ("aenderung_1h", "aenderung_24h", "btc_aenderung_24h", "breite",
              "oi_aenderung_pct", "rate_usd_pro_stunde", "anteil_long",
              "anzahl_schlagzeilen", "abstand_prozent", "alter_minuten",
              "volumen_24h", "market_cap_usd", "marktkap")

FELDNAME = {"aenderung_1h": "1h", "aenderung_24h": "24h",
            "btc_aenderung_24h": "BTC 24h", "breite": "Breite",
            "oi_aenderung_pct": "OI", "rate_usd_pro_stunde": "Liq USD/h",
            "anteil_long": "Long-Anteil", "anzahl_schlagzeilen": "Schlagzeilen",
            "abstand_prozent": "Abstand", "alter_minuten": "Alter",
            "volumen_24h": "Vol 24h", "market_cap_usd": "MCap",
            "marktkap": "MCap"}


def _zahl_text(x):
    """Eine Messgrösse als kurzer, lesbarer Text - ohne Rauschen."""
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        if x != x:                       # NaN
            return None
        if x == int(x) and abs(x) < 1e9:
            return "%d" % int(x)
        if abs(x) >= 1e6:
            return "%.2f Mio" % (x / 1e6)
        return ("%.2f" % x).rstrip("0").rstrip(".")
    if isinstance(x, str) and 0 < len(x) <= 40:
        return x
    return None


def messwerte(d, hoechstens=3):
    """Die Groessen aus dem Daten-Dict, an denen das Signal gehangen hat.

    `d` ist die INNERE Karte (`daten[inst]`) - `spur_buch` ruft
    `signal(daten[inst], w)`. Kerzen, Wand-Dictionaries und Liquidationslisten
    werden nicht ausgegeben (zu lang, kein Messwert), aber eine Liste mit
    Laenge (z. B. die Zahl der Liquidierungen) schon - das ist eine Groesse,
    die eine Regel belegt.
    """
    if not isinstance(d, dict):
        return []
    keys = [k for k in MESSFELDER if k in d]
    keys += sorted(k for k in d if k not in MESSFELDER)
    raus = []
    for k in keys:
        v = d.get(k)
        if isinstance(v, (list, tuple)):
            v = len(v)
            k = k if k in FELDNAME else "%s n" % k
        text = _zahl_text(v)
        if text is None:
            continue
        raus.append("%s %s" % (FELDNAME.get(k, k), text))
        if len(raus) >= hoechstens:
            break
    return raus


def einstiegsgrund(w, d, seite, spur_name=None, begruendung=None):
    """Der Grund fuer die Einstiegszeile - der wahre, nicht der Platzhalter."""
    roh = str((w or {}).get("_grund") or "").strip()
    klein = roh.lower()
    if roh and not any(p in klein for p in PLATZHALTER):
        return roh
    if begruendung is not None:
        try:
            text = str(begruendung(d, w, seite) or "").strip()
        except Exception as e:                              # noqa: BLE001
            print("  Begruendung nicht rechenbar (%s)" % e, file=sys.stderr)
            text = ""
        if text:
            return text
    mess = messwerte(d)
    name = spur_name or (w or {}).get("grund") or "spur"
    if mess:
        return "%s %s (%s)" % (name, seite, ", ".join(mess))
    return "%s %s (signal)" % (name, seite)


# --- Orderweg (Live) --------------------------------------------------------
#
# EINE Fassung fuer ALLE Buch-Spuren. Welche Boerse gilt, steht in der wachen
# (`boerse`): "okx" (Spot gegen USDC, Standard) oder "kraken" (Spot gegen EUR).
# Beide Module sind Adapter mit DENSELBEN Funktionsnamen (markt_kauf,
# markt_verkauf, algo_stop_setzen, algo_stornieren, gefuellte_menge,
# guthaben_waehrung, letzter_kurs, menge_fuer, schluessel_vorhanden,
# demo_modus) - die Strategie merkt den Unterschied nicht.
#
# Warum hier und nicht je Spur: die Buch-Spuren (moondev_*, iv_*) teilen sich
# dieses Modul ohnehin; eine zweite Live-Fassung je Spur waere N Stellen, an
# denen dieselbe Sperrenkette nachgezogen werden muss.
_ORDER_MODULE = {}


def orderweg(w):
    """Das Boersenmodul zur `boerse` aus der wachen. None = kein Live-Weg."""
    name = str(w.get("boerse") or "okx").strip().lower()
    if name in _ORDER_MODULE:
        return _ORDER_MODULE[name]
    # _lade_modul haengt ".py" selbst an und sucht unter HANDEL - deshalb der
    # relative Name mit Unterordner, kein absoluter Pfad.
    pfad = {"okx": "mosaic/okx_spot", "kraken": "mosaic/kraken_spot",
            "kraken_futures": "omnitrade_futures/weg",
            # OKX-Perpetuals (moondev_whale/-liquidation/-sentiment): die
            # Buch-Spuren handeln BTC-USDT-SWAP, kein Spot. Adapter in
            # mosaic/okx_perp.py ueber xperp/okxf.py.
            "okx_perp": "mosaic/okx_perp",
            # signalwelle waehlt ihre Instrumente laufend aus den
            # CoinGecko-Top-Movern; 7 von 16 haben keinen OKX-Markt, und
            # dieser Weg verweigert statt auf ein anderes Paar
            # auszuweichen (siehe moondev_signalwelle/weg.py).
            "signalwelle": "moondev_signalwelle/weg"}.get(name)
    if not pfad or not (Path(HANDEL) / (pfad + ".py")).is_file():
        return None
    _ORDER_MODULE[name] = _lade_modul(pfad)
    return _ORDER_MODULE[name]


def venue_inst(inst, w):
    """Das Instrument in der Schreibweise der BOERSE.

    Die Buch-Spuren fuehren Kurzzeichen ("XMR", "ZRO"), die Boerse will das
    Paar ("XMR-USDC"). Gemerkt wird beides: `inst` bleibt der Weg, ueber den die
    Spur ihre Kurse holt, `venue_inst` geht an die Boerse. Ohne diese Trennung
    laeuft der Live-Einstieg in einen OKX-Fehler (Instrument unbekannt) - oder
    schlimmer: in ein anderes Paar mit demselben Namen.
    """
    boerse = str(w.get("boerse") or "okx").strip().lower()
    if boerse == "kraken_futures":
        # Kontraktnamen der Kraken-Futures-Maerkte: PF_<Basis>USD, nur BTC
        # heisst dort XBT (gemessen 25.09.2026 an PF_XBTUSD/PF_SOLUSD). Der
        # Check VOR dem Bindestrich-Zweig: die omnitrade-Laeufe liefern
        # "SOL-USDC" - ein fruehes "return inst" wuerde den Kontraktnamen
        # nie bauen und die Order in einen Markt schicken, den es nicht gibt.
        basis = inst.split("-")[0]
        return "PF_%sUSD" % ("XBT" if basis == "BTC" else basis)
    if "-" in inst:
        return inst
    return "%s-%s" % (inst, "EUR" if boerse == "kraken" else "USDC")


def live_grenze(w, name, ersatz):
    """Live-Grenze aus der wachen: `live_<name>`, sonst der Papierwert."""
    return float(w.get("live_" + name, w.get(name, ersatz)) or ersatz)


# Luft, die beim Deckeln auf das freie Guthaben zusaetzlich zur Gebuehr bleibt
# (Rundung der Menge, Kursrutsch zwischen Abruf und Order).
GUTHABEN_PUFFER = 0.002


def einsatz_gedeckelt(weg, w, betrag):
    """Der Live-Einsatz, der in das FREIE Guthaben passt.

    WARUM DAS HIER STEHT (25.09.2026): `mindest_guthaben` ist eine Schwelle
    ("darf ich ueberhaupt anfangen"), KEINE Aussage darueber, dass der GEPLANTE
    Betrag bezahlbar ist. An diesem Tag stand das Tor von moondev_listingarb
    auf 5 USDC, der geplante Einsatz aber bei bis zu 50 (und 71,43 aus der
    Risikorechnung) - eine Order waere an der Boerse gescheitert (OKX:
    insufficient balance), und zwar erst NACH dem Kaufversuch. Das Tor haette
    also offen gestanden und trotzdem nicht gehandelt.

    Gedeckelt wird auf `frei * (1 - Gebuehr - Puffer)`; ein kleinerer Einsatz
    senkt nur das Risiko, nie das Schutzniveau (die Positionsgroesse haengt an
    `risiko_je_position_usd / stop_pct`, und die bleibt unveraendert). ACHTUNG:
    Was hier fehlt, muss der Aufrufer SICHTBAR melden - ein Filter, der still
    drosselt, sieht aus wie ein Fehler. Dasselbe Muster wie
    mosaic.betrag_gedeckelt() und moondev_marktlage/live_kraken.einsatz_gedeckelt().
    """
    frei = float(weg.guthaben_waehrung(w.get("guthaben_waehrung", "USDC")) or 0.0)
    gebuehr = float(w.get("gebuehr_taker", 0.006) or 0.0)
    luft = frei * max(0.0, 1.0 - gebuehr - GUTHABEN_PUFFER)
    return max(0.0, min(float(betrag), luft))


def sperren_live(w, s, spur):
    """Alles, was --live gerade verschliesst. Leere Liste = frei.

    Dieselbe Kette wie scanner/mosaic/swap/kraken: Risikostufe, Schalter,
    Schluessel, Freigabe, Herzschlag, EV, Journal-Zweitziel, Demo-Modus,
    Guthaben - und zuletzt, mit dem Wort Freigabefenster fuer
    dauerlauf.nur_fenster_fehlt, das Zeitfenster.
    """
    g = []
    weg = orderweg(w)
    if not risikostufe.live_erlaubt():
        g.append("Risikostufe %s: kein Live-Pfad in einer Stufe"
                 % risikostufe.stufe())
    if not w.get("handel_erlaubt"):
        g.append("wachen.json handel_erlaubt=false")
    if weg is None:
        g.append("kein Orderweg fuer boerse=%s" % w.get("boerse"))
    elif not weg.schluessel_vorhanden():
        g.append("%s-Schluessel nicht gesetzt" % (w.get("boerse") or "okx"))
    if not s.get("freigabe_erfuellt"):
        g.append("freigabe.erfuellt=false (Bedingung 1)")
    if not s.get("herzschlag_frisch"):
        g.append("Herzschlag alt (Bedingung 3)")
    if s.get("ev_negativ"):
        g.append("rollierender EV negativ (Bedingung 5)")
    if w.get("journal_zweitziel") is None:
        g.append("journal_zweitziel nicht gesetzt (Bedingung 4)")
    if weg is not None and weg.demo_modus():
        g.append("Demo-Modus gesetzt - keine echten Orders")
    try:
        if not freigabefenster.lade(spur).offen():
            g.append("kein offenes Freigabefenster (Handelsregeln Punkt 3)")
    except Exception:                                          # noqa: BLE001
        g.append("freigabefenster.py nicht erreichbar")
    wegsperren = orderweg(w)
    # BASIS-DECKEL (03.10.2026, Auftrag Max "Basis deckel 20%"): ist eine
    # Basis ueber 20 % des Kapitals, bekommt sie keinen neuen Einstieg.
    # Bestehende Positionen laufen weiter - sie zu schliessen waere eine
    # Order und gehoert in die Freigabekette wie jede andere.
    #
    # Der Deckel wird an dieser Stelle und nicht in der Signalberechnung
    # geprueft: eine Spur, die ein Signal sieht und es nicht handelt, sieht
    # fuer tot aus - der stille-spuren-wache wuerde sie als tot melden,
    # ohne zu wissen warum. Hier wird der Einstieg abgelehnt und
    # protokolliert, die Spur laeuft weiter und sieht gesund aus.
    if wegsperren is not None:
        try:
            for _inst in sorted(s.get("instrumente") or s.get("watchlist") or []):
                _gesperrt, _grund = basis_deckel_tor.ueber_dem_deckel(_inst)
                if _gesperrt:
                    g.append(_grund)
        except Exception as e:                              # noqa: BLE001
            g.append("Basis-Deckel nicht pruefbar (%s)" % str(e)[:80])
    noetig = float(w.get("mindest_guthaben", 0) or 0)
    if noetig and weg is not None and weg.schluessel_vorhanden():
        try:
            frei = weg.guthaben_waehrung(w.get("guthaben_waehrung", "USDC"))
            if frei < noetig:
                g.append("nur %.2f %s frei, noetig %.2f"
                         % (frei, w.get("guthaben_waehrung", "USDC"), noetig))
        except Exception as e:                                 # noqa: BLE001
            g.append("Guthaben nicht abrufbar (%s)" % e)
    return g


def signal_gatter_gilt(w, live):
    """True, wenn `trigger_modus: signal` in DIESEM Zyklus greift.

    DIE REGEL (T-347, gemessen 04.10.2026): das Gatter schuetzt vor
    Ueberhandelung mit GELD. Im Papier ist das Ueberhandeln harmlos - und
    das Gatter hat dort sogar die Messung verhindert: es legte den Auftrag
    in die signal_queue und kehrte zurueck, also konnte eine Spur mit
    `handel_erlaubt=false` strukturell NIE eine Papierrunde buchen. Fuenf
    Spuren standen so bei 0 Runden (nautilus_emacross, omnitrade,
    omnitrade_futures, trendwende_btc, iv_waelle), obwohl ihr Signal da war;
    ihr Auftrag wartete auf einen signal-executor, der sie nie abholt, weil
    er selbst an handel_erlaubt/freigabe scheitert.

    `live` ist der VORLAEUFIGE Live-Zustand aus `zyklus` - ein Auftrag, der
    am Live-Weg scheitert, wird ohnehin Papier gebucht und gehoert damit
    unter dieselbe Regel.

    Die Funktion ist eine eigene Zeile, damit die Regel pruefbar ist, ohne
    einen ganzen Zyklus zu fahren.
    """
    return bool(live) and str(w.get("trigger_modus") or "").lower() == "signal"


def signal_gewechselt(z, inst, seite, w):
    """True, wenn dieser Auftrag das Signal-Gatter passiert (Live-Weg).

    Merkt sich die GESEHENE Richtung in `z["vor_signal"][inst]` - bei JEDER
    Pruefung, auch bei der verweigerten. Sonst waere ein verweigerter
    Auftrag beim naechsten Takt wieder "neu" (dieselbe Klasse wie der Fehler
    vom 03.10.2026, der jede Spur ohne Flag sperrte).

    Die Regel gilt je Instrument getrennt: ein zweites Instrument darf nicht
    am ersten scheitern.
    """
    vorher = z.setdefault("vor_signal", {})
    alt = vorher.get(inst)
    vorher[inst] = seite
    return alt is None or alt != seite


def einstieg(z, inst, seite, kurs, w, faktor, grund, stop_pct=None,
            ziel_preis=None, journal_pfad=None, live=False, weg=None):
    """Eine Position eroeffnen - Stop in Prozent, Ziel als Preis oder Vielfaches.

    `ziel_preis` gibt es fuer Signale, deren Ziel ein MARKTPUNKT ist (die
    IV-Wand: der Strike mit dem groessten Open Interest). Ohne ihn gilt das
    R-Vielfache aus den Wachen. Beide Wege setzen denselben Stop - daran haengt
    die Groesse, und die muss zur Ausstiegslinie passen.
    """
    if not z.get("positionen"):
        z["positionen"] = []
    if len(z["positionen"]) >= w.get("max_offene_positionen", 3):
        return None
    if any(p.get("inst") == inst for p in z["positionen"]):
        return None
    if not kurs or kurs <= 0 or seite not in ("long", "short"):
        return None

    pct = float(stop_pct if stop_pct is not None else w.get("stop_prozent", 6.0))
    pct = max(pct, w.get("pflicht_stop_prozent_min", 5.0))
    pct = min(pct, w.get("pflicht_stop_prozent_max", 12.0))
    vz = 1 if seite == "long" else -1
    abstand = kurs * pct / 100.0
    r = float(w.get("ziel_r_vielfaches", 1.5))
    stop = kurs - vz * abstand
    if ziel_preis:
        # Ein Marktziel muss auf der richtigen Seite liegen: ein Ziel hinter
        # dem Einstieg waere sofort erreicht (oder nie) - beides ist kein
        # Handel, sondern ein Rechenfehler.
        if (seite == "long" and float(ziel_preis) <= kurs) or \
                (seite == "short" and float(ziel_preis) >= kurs):
            return None
        ziel = float(ziel_preis)
    else:
        ziel = kurs + vz * r * abstand

    nominel = w["risiko_je_position_usd"] / (pct / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"]) * faktor
    if nominel <= 0:
        return None

    # Risiko-VORFILTER (Regeln des Moon-Dev risk_agent, ohne Sprachmodell):
    # greift VOR dem Buchen und nur, wenn die Wache ihn einschaltet
    # (`risikovorfilter: true`).
    #
    # `risiko` ist der Betrag, der bei einem Stop verloren ginge. Er wird auch
    # von der Stufen-Grenze unten gebraucht, deshalb steht er hier - und nicht
    # erst im Vorfilter.
    risiko = nominel * pct / 100.0
    if journal_pfad and w.get("risikovorfilter"):
        ok, warum = risikovorfilter.pruefe(w, journal_pfad, z, risiko)
        if not ok:
            print("VORFILTER: %s" % warum)
            return None

    # STUFEN-GRENZE (PLAN §4.2, Einstiegsseite): dieselbe Zahl wie die
    # Bestandskontrolle in `pruefe_stufen()` - sonst schliesst der Stufen-Kill
    # ein Buch, das der naechste Zyklus sofort wieder aufbaut (Pendeln im
    # Journal). Ohne ausdrueckliche Grenze ist sie das Buchrisiko der Spur
    # (Risiko je Position x Plaetze) und damit genau die Platzzahl - die
    # Pruefung aendert dann NICHTS. Sie greift, sobald eine Wache
    # `max_offenes_risiko_usd` (oder `risiko_buchdeckel_usd`) UNTER das
    # Buchrisiko setzt; das ist der einzige Fall, in dem ein Deckel binden
    # kann, und es ist eine Konfigurationsentscheidung, keine Reparatur.
    grenze, grenze_quelle = stufen_schwelle(w)
    if grenze is not None:
        offen = ratschen.offenes_risiko(z)
        if offen + risiko > grenze:
            print("STUFEN-GRENZE: offenes Buchrisiko %.2f + %.2f > %.2f (%s) "
                  "- kein Einstieg" % (offen, risiko, grenze, grenze_quelle))
            return None

    p = {"inst": inst, "seite": seite, "einstieg": kurs, "stop": stop,
         "ziel": ziel, "stop_pct": pct, "nominal": nominel,
         "modus": "live" if live else "papier",
         # Die Kennung dieser Position (T-095). Sie entsteht HIER, einmal je
         # Einstieg, steht im Zustand und wird in der Ausstiegszeile
         # mitgefuehrt - nur so ist die Zuordnung eindeutig, wenn zwei
         # Positionen im selben Instrument gleichzeitig offen sind.
         "pos_id": pos_kennung.neu(jetzt()),
         "eroeffnet_zeit": jetzt()}

    if live:
        # ERST die Order, DANN ins Buch. Scheitert sie, entsteht keine Position -
        # ein Buch, das eine Order behauptet, die es nicht gibt, ist genau der
        # Zustand, den xperp am 21.09.2026 hatte.
        if weg is None:
            return None
        vinst = venue_inst(inst, w)
        # Im Live-Lauf den BOERSEN-Kurs verwenden, nicht den aus quelle().
        # Zwei Grunde: (1) CoinGecko liefert USD, Kraken-Stop-Loss braucht EUR
        # - ein Stop bei USD-Preis 158 wuerde bei Kraken als 158 EUR gesetzt
        # und sofort reissen, wenn der Markt bei 497 EUR steht.
        # (2) Zwischen quelle() und dem Kauf liegen Netzabfragen; ein
        # veralteter Kurs kann die Menge falsch rechnen.
        # Faellt der Abruf aus, wird der Einstieg uebersprungen.
        if weg is not None:
            try:
                kurs_live = float(weg.letzter_kurs(vinst))
                if kurs_live > 0:
                    kurs = kurs_live
                    # Stop und Ziel neu rechnen auf Basis des Boersen-Kurses:
                    abstand = kurs * pct / 100.0
                    stop = kurs - vz * abstand
                    if ziel_preis:
                        if (seite == "long" and float(ziel_preis) <= kurs) or \
                                (seite == "short" and float(ziel_preis) >= kurs):
                            return None
                        ziel = float(ziel_preis)
                    else:
                        ziel = kurs + vz * r * abstand
                    # Nominale ebenfalls neu - der Betrag bleibt an pct gebunden.
                    nominel = w["risiko_je_position_usd"] / (pct / 100.0)
                    nominel = min(nominel, w["max_pro_trade_usd"]) * faktor
                    p["einstieg"] = kurs
                    p["stop"] = stop
                    p["ziel"] = ziel
                    p["nominal"] = nominel
            except Exception as e:                             # noqa: BLE001
                print("  Boersen-Kurs %s nicht abrufbar (%s) - Einstieg uebersprungen"
                      % (inst, e), file=sys.stderr)
                return None
        # Der Einsatz steht hier, NICHT oben: der Boersen-Kurs hat die Nominale
        # gerade neu gerechnet, und der Betrag haengt an der Nominale. Gedeckelt
        # wird zuletzt, auf das FREIE Guthaben: eine Order, die groesser ist als
        # das Konto, scheitert erst an der Boerse - und ein Buch, das sie schon
        # gebucht haette, behauptet eine Position, die es nie gab (xperp,
        # 21.09.2026).
        betrag = min(nominel, live_grenze(w, "max_pro_trade_usd", nominel))
        try:
            betrag = einsatz_gedeckelt(weg, w, betrag)
        except Exception as e:                                 # noqa: BLE001
            # Ohne Guthabenzahl wird NICHT geordert - blind zu kaufen ist die
            # eine Sache, die dieser Deckel verhindern soll.
            print("  Live-Einstieg %s uebersprungen (Guthaben nicht abrufbar: %s)"
                  % (inst, e), file=sys.stderr)
            return None
        if betrag <= 0:
            print("  Live-Einstieg %s uebersprungen: kein freies Guthaben in %s"
                  % (inst, w.get("guthaben_waehrung", "USDC")))
            return None
        if betrag < nominel:
            # Sichtbar drosseln, nicht still: ein gedeckelter Einsatz ist eine
            # Auskunft ueber das Konto, kein Fehler.
            print("  Einsatz %s auf %.2f gedeckelt (geplant %.2f)"
                  % (inst, betrag, nominel))
        # Das BUCH fuehrt, was WIRKLICH geordert wurde. Vorher stand hier die
        # ungedeckelte Nominale: bei moondev_listingarb (Risiko 5 USD, Stop 7 %
        # = 71,43 Nominale, Live-Grenze 50) haette das Buch 71,43 gefuehrt und
        # die Boerse 50 bekommen - jeder Ausstieg haette den G/V auf einen
        # Einsatz gerechnet, den es nicht gab.
        p["nominal"] = betrag
        try:
            menge, fehler = weg.menge_fuer(vinst, betrag, kurs)
        except Exception as e:                                 # noqa: BLE001
            # Ein Live-Weg darf den Zyklus NIE reissen: ein unbekanntes Paar,
            # ein Netzfehler oder eine abgelehnte Abfrage endet hier als
            # uebersprungener Einstieg, nicht als Absturz der Spur.
            print("  Live-Einstieg %s uebersprungen (Menge nicht bestimmbar: %s)"
                  % (inst, e), file=sys.stderr)
            return None
        if fehler:
            print("  Live-Einstieg %s uebersprungen: %s" % (inst, fehler))
            return None
        try:
            ord_id = weg.markt_kauf(vinst, menge)
        except Exception as e:                                 # noqa: BLE001
            print("  Live-Einstieg %s fehlgeschlagen (%s) - nicht gebucht"
                  % (inst, e), file=sys.stderr)
            return None
        if not ord_id:
            print("  Live-Einstieg %s: keine Order-Kennung - nicht gebucht" % inst)
            return None
        p["ord_id"] = str(ord_id)
        p["menge"] = menge
        p["venue_inst"] = vinst
        try:
            stop_id = weg.algo_stop_setzen(vinst, menge, seite, stop)
            p["stop_id"] = str(stop_id) if stop_id else ""
        except Exception as e:                                 # noqa: BLE001
            # Ohne Boersen-Stop wird sofort zurueckverkauft (Hausregel: eine
            # Position ohne Stop an der Boerse ist unbewacht).
            print("  Stop fuer %s fehlgeschlagen (%s) - zurueckverkauft"
                  % (inst, e), file=sys.stderr)
            try:
                weg.markt_verkauf(vinst, menge)
            except Exception:                                  # noqa: BLE001
                pass
            return None

    z["positionen"].append(p)
    return p


def pruefe_ausstiege(z, kurse, w, journal_pfad, nur=None, live=False,
                    weg=None, zusatz=None, zustand_pfad=None):
    """Stop und Ziel pruefen. Der G/V laeuft auf den NOMINALWERT.

    Die rohe Kursdifferenz war der Fehler vom 15.09.2026: bei BTC ein Faktor
    von Zehntausenden, der Erloes stand in Kurshoehe im Journal.
    """
    behalten = []
    buchungen = []   # Ausstiege, die nach der Schleife GEMEINSAM gebucht werden
    for p in z.get("positionen", []):
        if nur is not None and p.get("inst") != nur:
            behalten.append(p)
            continue
        kurs = kurse.get(p["inst"])
        if kurs:
            # MAE/MFE ueber die LEBENDAUER messen, nicht erst beim
            # Ausstieg - sonst waere die Zahl der Ausstiegskurs selbst.
            mae.merke_extrem(p, kurs)
        if not kurs:
            # Kein Kurs heisst NICHT "nichts passiert": die Position wird
            # uebersprungen und kann so beliebig lange stehen bleiben. Bis zum
            # 28.09.2026 schwieg dieser Zweig - bei den Indikator-Spuren
            # verhinderten vier Positionen ohne Kurs wochenlang jeden
            # Journalzuwachs, ohne dass es irgendwo stand. Deshalb jetzt laut
            # nach stderr, mit Instrument und Einstiegszeit.
            print("  %s: kein Kurs - Position wird NICHT geprueft (seit %s)"
                  % (p.get("inst"), p.get("eroeffnet_zeit") or "?"),
                  file=sys.stderr)
            behalten.append(p)
            continue
        grund = None
        # festes_ziel false (Auftrag Max 08.10.2026, Trendspuren): das Ziel ist
        # nur noch Richtmarke im Buch, der Ausstieg kommt von Stop und Regel.
        # Standard true - jede Spur ohne das Feld verhaelt sich wie bisher.
        fest = w.get("festes_ziel", True)
        if p["seite"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif fest and kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif fest and kurs <= p["ziel"]:
                grund = "ziel"
        if not grund and zusatz is not None:
            # ZUSATZ-AUSSTIEG (21.09.2026): Stop und Ziel haben Vorrang -
            # sie sind die teurere Wahrheit und muessen im Journal stehen,
            # wenn sie gerissen sind. Erst danach darf ein Signal die
            # Position beenden (z. B. der Rueckdreh des Trends).
            try:
                grund = zusatz(p, w)
            except Exception as e:  # noqa: BLE001
                print("  %s: Zusatz-Ausstieg nicht rechenbar (%s)"
                      % (p.get("inst"), e), file=sys.stderr)
                grund = None

        if not grund and live and weg is not None and p.get("stop_id"):
            # TRAILING AN DER BOERSE (T-286, 01.10.2026): der stp-Stop wird
            # NACHGEZOGEN, nicht neu gerechnet im Buch. Nur LONG (die Buch-Spuren
            # eroeffnen nur long), nur NACH OBEN, und nur wenn der neue Stop
            # spuerbar ueber dem alten liegt. Scheitert das Nachziehen, bleibt
            # der ALTE Stop an der Boerse stehen - die Position ist dann
            # weiter geschuetzt; ein stiller Verlust des Schutzes waere die
            # ZEC-Lektion vom 26.09.2026.
            # `trailing_stop_prozent` ist ein PROZENTWERT (3.0 = 3 %), wie in
            # trailing.py und im Namen. Bis 09.10.2026 wurde er hier als Bruchteil
            # gelesen: bei 3.0 kam `hoch * (1 - 3.0)` = negativ heraus, die
            # Bedingung `neu > stop` war nie erfuellt und der Trailing lief in
            # omnitrade_futures nie - ohne Meldung.
            try:
                pct = float(w.get("trailing_stop_prozent") or 0.0) / 100.0
            except (TypeError, ValueError):
                pct = 0.0
            if pct > 0.0 and p.get("seite") == "long":
                hoch = max(float(p.get("hoechstkurs") or kurs), kurs)
                p["hoechstkurs"] = hoch
                neu = hoch * (1.0 - pct)
                if neu > float(p["stop"]):
                    try:
                        kennung = weg.stop_nachziehen(
                            p["stop_id"], p.get("venue_inst") or p["inst"],
                            p.get("menge") or 0, neu)
                        if kennung:
                            p["stop"] = neu
                            p["stop_id"] = str(kennung)
                            print("  TRAILING %s Stop -> %.6f (Hoch %.6f)"
                                  % (p["inst"], neu, hoch))
                    except Exception as e:                     # noqa: BLE001
                        print("  Trailing %s nicht nachziehbar (%s) - Stop %.6f bleibt"
                              % (p["inst"], e, p["stop"]), file=sys.stderr)

        if not grund:
            behalten.append(p)
            continue

        vz = 1 if p["seite"] == "long" else -1
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        ist_live = bool(live and p.get("modus") == "live" and weg is not None)
        if ist_live:
            # Boersen-Stop zuerst stornieren, dann verkaufen. Schlaegt der
            # Verkauf fehl, bleibt die Position im Buch (sie ist ja noch da).
            # Die Boerse kennt das Paar (venue_inst), die Spur ihr Kurzzeichen.
            vinst = p.get("venue_inst") or p["inst"]
            try:
                if p.get("stop_id"):
                    weg.algo_stornieren(vinst, p["stop_id"])
            except Exception as e:                             # noqa: BLE001
                print("  Stop %s nicht stornierbar (%s)" % (p["inst"], e),
                      file=sys.stderr)
            try:
                weg.markt_verkauf(vinst, p.get("menge") or 0)
            except Exception as e:                             # noqa: BLE001
                print("  Verkauf %s fehlgeschlagen (%s) - bleibt im Buch"
                      % (p["inst"], e), file=sys.stderr)
                behalten.append(p)
                continue
        buchungen.append((p, kurs, grund, gv, ist_live))

    z["positionen"] = behalten
    # GEMEINSAM buchen: erst verschwindet die Position aus dem Zustand, dann
    # kommt die Verkaufszeile ins Journal - beides in EINEM Aufruf (buche).
    # Vorher schrieb das Journal hier sofort, der Zustand erst am Ende des
    # Zyklus; eine Vorschau oder ein Absturz dazwischen liess die Position
    # offen, waehrend das Journal sie verkauft hatte (T-356).
    for p, kurs, grund, gv, ist_live in buchungen:
        print("AUSSTIEG (%s) %s %.6f G/V %+.2f USD"
              % (grund, p["inst"], kurs, gv))
        buche(z, zustand_pfad, journal_pfad, zeit=jetzt(),
              modus="live" if ist_live else "papier", aktion="verkauf",
              inst=p["inst"], seite=p["seite"], preis=pformat(kurs),
              # Die Kennung der Position, die hier endet (T-095). Ohne sie
              # waere diese Zeile bei zwei offenen Positionen im selben
              # Instrument nicht mehr zuzuordnen.
              pos_id=p.get("pos_id", ""),
              einsatz_usd="%.2f" % (p["nominal"] + gv),
              # `stop_pct` ist NICHT bei jeder Position gesetzt: am 19.10.2026
              # fehlte es bei 14 von 139 offenen Positionen (gitter, kraken,
              # omniquant, scanner). Hier stand `"%.2f" % p["stop_pct"]` - ein
              # fehlendes Feld riss damit den ganzen Zyklus ab, und die Position
              # blieb offen (TypeError statt Buchung). Jetzt wird der Abstand
              # ueber `ratschen.stop_prozent` aus der STOP-LINIE geholt, wenn
              # das Feld fehlt - dieselbe Herleitung wie in der Bestandsgrenze.
              stop=pformat(p.get("stop") or 0.0),
              ziel=pformat(p.get("ziel") or 0.0),
              stop_pct="%.2f" % ratschen.stop_prozent(p),
              grund=grund, **mae.felder(p))
        if SCHREIBEN:
            telemetrie.geschlossen(journal_pfad, p,
                                   "live" if ist_live else "papier", grund, gv,
                                   kurs, mae.felder(p)["haltetage"],
                                   risikostufe.stufe())


# --- Kill: Zwangsschluss mit Buchung -----------------------------------------

KILL_GRUND = kg.KILL_GRUND

# --- Stufen-Kontrolle: der BESTAND gegen die Grenze der Stufe (PLAN §4.2) ----

# Eigener Grund mit "zwangsschluss" im Wort: `stoerungen.ist_stoerung` erkennt
# die Zeile damit als Stoerung - sie zaehlt in der Kapitalkurve (gebucht) und
# NICHT als Handelsrunde. Der Praefix nennt die Ursache, weil die Fehlersuche
# sonst nicht unterscheiden kann, ob der Drawdown-Kill oder die Stufe geschlossen
# hat. (Dieselbe Ueberlegung wie bei `buchbereinigung` in stoerungen.py.)
STUFEN_GRUND = "stufenueberschreitung_zwangsschluss"

# Schluessel, die eine Wache fuer das OFFENE Buchrisiko nennen darf. Beide
# meinen dieselbe Groesse - den Betrag, der bei gleichzeitigem Stop aller
# Positionen verloren ginge. `risiko_buchdeckel_usd` ist derselbe Deckel, den
# `risikovorfilter.pruefe` schon auf der EINSTIEGSSEITE liest: eine Zahl, zwei
# Seiten. `max_gesamt_usd` steht hier absichtlich NICHT - das ist ein
# Kapitaldeckel, kein Risikodeckel (er liegt in 45 von 56 Wachen 2x bis 65x
# ueber dem Buchrisiko und kann deshalb nie binden).
STUFEN_SCHLUESSEL = ("max_offenes_risiko_usd", "risiko_buchdeckel_usd")


def stufen_schwelle(w):
    """(Betrag, Quelle) der Bestandsgrenze - oder (None, None).

    Reihenfolge: ausdrueckliche Grenze, sonst das BUCHRISIKO der Spur
    (Risiko je Position x Hoechstzahl Positionen).

    Bewusst NICHT die `drawdown_halbierungsschwelle`: die ist ein RUECKLAUF
    (realisierte Gewinnkurve), die Grenze hier ist ein OFFENES RISIKO - zwei
    verschiedene Groessen, die nur zufaellig denselben Betrag tragen. Waere die
    Ratsche hier angehaengt, verschoebe ein geaenderter Ratschen-Betrag lautlos
    den Notaus.
    """
    for schluessel in STUFEN_SCHLUESSEL:
        wert = w.get(schluessel)
        if wert is None:
            continue
        try:
            betrag = float(wert)
        except (TypeError, ValueError):
            continue
        if betrag > 0:
            return betrag, schluessel
    buch = ratschen.buch_risiko(w)
    if buch and buch > 0:
        return buch, "buchrisiko"
    return None, None


def pruefe_stufen(z, w):
    """Bestandskontrolle: traegt das offene Buch mehr Risiko, als die Stufe erlaubt?

    Rueckgabe `(offen, erlaubt, quelle)`. `erlaubt is None` heisst: die Spur
    nennt weder eine Grenze noch die beiden Zahlen des Buchrisikos - dann wird
    NICHTS geschlossen. Eine geratene Grenze waere schlimmer als keine: sie
    sieht aus wie Schutz (dieselbe Regel wie in ratschen.py).

    WAS DIESE PRUEFUNG LEISTET - und was nicht (gemessen am 19.10.2026):
    `einstieg()` setzt die Nominale auf `risiko_je_position_usd / (stop_pct/100)`,
    gedeckelt auf `max_pro_trade_usd`. Das Risiko EINER Position ist damit
    hoechstens `risiko_je_position_usd`, das offene Buch also hoechstens
    `risiko x Plaetze` = Buchrisiko. Ein Deckel AUF dem Buchrisiko kann deshalb
    nie reissen - er ist eine DRIFT-BREMSE: er feuert, wenn das Buch nicht mehr
    zur Konfiguration passt (Risiko je Position oder Platzzahl nach dem
    Eroeffnen gesenkt, Position aus einem aelteren Stand, Stufe gewechselt).
    Damit der Kill wirklich bindet, muss die Grenze UNTER das Buchrisiko - und
    das ist eine Entscheidung des Betreibers, keine Code-Frage.
    """
    offen = ratschen.offenes_risiko(z)
    erlaubt, quelle = stufen_schwelle(w)
    return offen, erlaubt, quelle


def kill_schliessen(z, w, quelle, preis_fuer, journal_pfad, zustand_pfad,
                    live=False, weg=None, grund=KILL_GRUND, kurse=None):
    """Offene Positionen zum Marktkurs schliessen UND buchen (Grund `kill_zwangsschluss`).

    Vorher (bis 09.10.2026) leerte der Kill nur `z["positionen"]`: keine
    Verkaufszeile, der gebuchte Ruecklauf blieb stehen, die Spur kam nie mehr
    unter die Schwelle. Jetzt laeuft der Zwangsschluss ueber `pruefe_ausstiege`
    wie jeder andere Ausstieg - Stop/Ziel vor Zwangsschluss, im Live-Betrieb mit
    echtem Verkauf an der Boerse. Der Grund enthaelt "zwangsschluss": die Runde
    zaehlt damit in der Kapitalkurve (Ruecklauf, Kill), aber nicht in den
    Kennzahlen (stoerungen.ist_stoerung).

    `grund` ist austauschbar, weil zwei verschiedene Waechter denselben Weg
    benutzen: der Drawdown-Kill (KILL_GRUND) und die Stufen-Kontrolle
    (STUFEN_GRUND). Der Grund steht im Journal und ist die einzige Stelle, an
    der die Ursache fuer die Fehlersuche noch zu sehen ist.

    `kurse` uebergeht den Abruf: ein Zyklus, der die Kurse schon geholt hat,
    darf sie nicht ein zweites Mal holen (der zweite Abruf kann scheitern und
    den Zwangsschluss dann grundlos aufschieben).

    Fehlt der Kurs einer Position oder schlaegt der Verkauf fehl, bleibt sie im
    Buch; der naechste Zyklus der Sperre versucht es erneut. Rueckgabe: Zahl der
    Positionen, die noch offen sind.
    """
    if not z.get("positionen"):
        return 0
    if kurse is None:
        try:
            _daten, kurse, _fehler = quelle(w)
        except Exception as e:                                     # noqa: BLE001
            print("  Kill: Kurse nicht abrufbar (%s) - %d Position(en) bleiben, "
                  "naechster Zyklus versucht es erneut"
                  % (str(e)[:80], len(z["positionen"])), file=sys.stderr)
            return len(z["positionen"])
    # Eigene Kopie: der Aufrufer braucht sein Kursbild unveraendert weiter
    # (der Zyklus rechnet danach die Einstiege damit).
    kurse = dict(kurse)
    if preis_fuer:
        for p in z["positionen"]:
            inst = p.get("inst")
            if not inst or inst in kurse:
                continue
            try:
                preis = preis_fuer(inst)
            except Exception:                                      # noqa: BLE001
                preis = None
            if preis and preis > 0:
                kurse[inst] = preis
    # LIVE-POSITIONEN GEHOEREN DER BOERSE (wie mosaic, Auftrag Max 09.10.2026):
    # Ohne freie Live-Kette (`live` falsch) darf der Kill sie weder als Papier
    # verbuchen noch aus dem Buch nehmen - sie stuenden sonst ungeschuetzt in der
    # Boerse, im Buch fehlte sie. Der Verkauf ist eine Order und gehoert in die
    # Freigabekette (sperren_live), nicht in einen Papierzyklus. Sie bleiben
    # stehen, ihr Boersen-Stop schuetzt sie; sobald ein Live-Zyklus laeuft,
    # schliesst der Kill sie mit echtem Verkauf.
    zurueck = []
    if not live:
        zurueck = [p for p in z["positionen"] if p.get("modus") == "live"]
        if zurueck:
            z["positionen"] = [p for p in z["positionen"] if p.get("modus") != "live"]
            print("  Kill: %d Live-Position(en) bleiben stehen (%s) - kein Verkauf "
                  "ausserhalb der Live-Kette; der Boersen-Stop schuetzt sie, der "
                  "naechste freie Live-Zyklus schliesst sie."
                  % (len(zurueck), ", ".join(str(p.get("inst")) for p in zurueck)),
                  file=sys.stderr)
    pruefe_ausstiege(z, kurse, w, journal_pfad, zustand_pfad=zustand_pfad,
                     live=live, weg=weg, zusatz=lambda p, w_: grund)
    z["positionen"] = z["positionen"] + zurueck
    return len(z["positionen"])


# --- Das Lauf-Geruest ------------------------------------------------------

def zyklus(ordner, quelle, signal, modus, ereignis_name, ziel=None,
           zusatz_ausstieg=None, datenlage=None, preis_fuer=None):
    """Ein Zyklus einer Spur. `quelle(w)`, `signal(daten, w)` kommen von ihr.

    `ziel(daten, w)` ist optional und liefert ein Ziel ALS MARKTPUNKT (die
    IV-Wand) - dann steht im Buch nicht das R-Vielfache, sondern diese Linie.
    Ohne `ziel` bleibt es beim Vielfachen aus den Wachen.

    `preis_fuer(inst)` ist optional und liefert den Kurs EINES Symbols. Er
    wird nach `quelle(w)` fuer jede offene Position aufgerufen, die keinen
    Kurs mehr hat (T-160: Symbolwechsel im Feed). Die Spur liefert die
    Preisquelle (CoinGecko, OKX, Pump, Robinhood-DB).

    Reihenfolge: erst die Ratsche (Buch-Ruecklauf), dann Ausstiege, dann die
    Stufen-Kontrolle auf den BESTAND (§4.2: das offene Buchrisiko gegen die
    Grenze der Stufe - `pruefe_stufen`), dann Einstiege. Bei `--vorschau` wird
    gerechnet und nichts geschrieben. `--live` laeuft ueber `sperren_live()`
    und `orderweg()` (Boerse aus der wachen); jede Sperre, die noch steht,
    laesst den Zyklus Papier handeln und nennt den Grund.
    """
    import ereignis

    wachen_pfad, zustand_pfad, journal_pfad = pfade(ordner)

    def _lauf():
        w = lade_wachen(wachen_pfad)
        z = lade_zustand(zustand_pfad) or {"positionen": [], "modus": "papier",
                                           "letzter_lauf": None, "verlust_usd": 0.0}
        z.setdefault("positionen", [])
        # Das Journal existiert ab dem ersten Zyklus, nicht erst ab dem ersten
        # Kauf (Auftrag Max 02.10.2026). Der Vorschau-Pfad kehrt weiter unten
        # VOR jedem Schreibvorgang zurueck - hier wird nichts geschrieben.
        if modus in ("papier", "live"):
            lege_journal_an(journal_pfad)

        if modus == "wachen":
            print(json.dumps(wp.lage(w, journal_pfad, z), indent=2,
                             ensure_ascii=False))
            return 0

        s = wp.lage(w, journal_pfad, z)
        ruecklauf = s.get("ruecklauf_usd", 0.0)
        faktor = groessenfaktor(ruecklauf, w)

        # Live nur, wenn die Spur --live anfordert UND die Sperrenkette leer ist.
        # Der Name der Spur kommt aus dem Ordner - so braucht zyklus() keinen
        # weiteren Parameter und jede Buch-Spur meldet unter ihrem eigenen Namen
        # (das Freigabefenster haengt an diesem Namen).
        spur_name = os.path.basename(os.path.abspath(ordner))
        live, weg = False, None
        if modus == "live":
            gruende = sperren_live(w, s, spur_name)
            if gruende:
                print("--live angefordert, aber gesperrt: " + "; ".join(gruende))
                print("-> es wird Papier gehandelt.")
            else:
                live, weg = True, orderweg(w)
        elif modus == "vorschau":
            # Die Vorschau nennt ihren Sperrstand - dieselbe Zeile wie scanner,
            # mosaic und kraken. Ohne sie kann dauerlauf.nur_fenster_fehlt()
            # nichts finden (es liest diese Zeile) und AUTO_FREIGABE greift
            # fuer keine Buch-Spur: die Freigabe wird nie beantragt, das
            # Fenster nie geoeffnet, --live nie gefahren.
            gruende = sperren_live(w, s, spur_name)
            print("Live waere gesperrt durch: " + ("; ".join(gruende) if gruende
                                                  else "nichts"))

        # Die Vorschau ist der lesende Blick: sie darf auch einen Kill-Stand
        # nicht flachlegen - alles, was hier steht, SCHREIBT (T-356).
        #
        # T-176 (29.09.2026): der Kill war ein DAUERSPERRER. Er leerte die
        # Positionen, aber die Kapitalkurve erholt sich nur durch neue
        # Trades - genau die sperrt der Kill.
        #
        # Die Frist (`kill_frist_stunden`, Standard 168 h) allein half nicht,
        # und das ist am 09.10.2026 mit dem echten Code nachgestellt worden
        # (tests/test_kill_nach_frist.py): Der Kill loeschte die Positionen OHNE
        # Buchung, der gebuchte Ruecklauf blieb stehen, nach der Frist lief ein
        # Zyklus frei und im naechsten griff der Kill sofort wieder - die dabei
        # eroeffnete Position wurde wieder ungebucht geloescht. Der Kill war
        # faktisch dauerhaft (Backtest PR #20: vier von fuenf Klassikspuren
        # stehen so binnen eines Jahres still).
        #
        # Jetzt (Auftrag Max 09.10.2026, Weg c):
        #   1. Der Kill schliesst offene Positionen zum Marktkurs und BUCHT sie
        #      (Grund `kill_zwangsschluss`, `kill_schliessen`).
        #   2. Nach Ablauf der Frist beginnt der Ruecklauf bei 0
        #      (`kill_ab_runde` im Zustand, gelesen von wachen_pruefung.lage):
        #      die Spur handelt weiter und der Kill greift erst bei einem NEUEN
        #      Rueckgang in Hoehe der Schwelle.
        if modus != "vorschau" and s.get("kill"):
            status, ruecklauf = kg.phase(z, w, ruecklauf, s.get("runden_gesamt", 0), jetzt)
            if status == "frei":
                faktor = groessenfaktor(ruecklauf, w)
            else:
                # Notausstieg ohne Freigabekette (Auftrag Max 14.10.2026,
                # Entscheidung 2): `kill_verkauf_ohne_freigabekette` erlaubt dem
                # Kill, echte Live-Positionen reduceOnly zu verkaufen, auch wenn
                # die Kette (Freigabefenster, EV, Herzschlag ...) zu ist. Es
                # bleiben: nur die Basisstufe, ein Orderweg mit gesetztem
                # Schluessel, und verkauft wird nur, was modus=live ist
                # (pruefe_ausstiege) - Papierpositionen nur im Buch.
                kill_live, kill_weg = live, weg
                if (not live and w.get("kill_verkauf_ohne_freigabekette")
                        and risikostufe.live_erlaubt()):
                    nw = orderweg(w)
                    if nw is not None and nw.schluessel_vorhanden():
                        kill_live, kill_weg = True, nw
                offen = kill_schliessen(z, w, quelle, preis_fuer, journal_pfad,
                                        zustand_pfad, live=kill_live, weg=kill_weg)
                if offen:
                    print("  %d Position(en) noch offen (kein Kurs oder Verkauf "
                          "fehlgeschlagen) - naechster Zyklus versucht es erneut." % offen)
                schreibe_zustand(zustand_pfad, z)
                spiegeln(zustand_pfad, journal_pfad, z, w)
                return 0

        daten, kurse, fehler = quelle(w)
        for f in fehler:
            print("Uebersprungen (%s)" % f, file=sys.stderr)
        # T-160: Kursverlust bei Symbolwechsel. `quelle()` baut `kurse` aus
        # den heutigen Kandidaten - faellt ein Symbol aus dem Feed, bekommt
        # seine offene Position keinen Kurs mehr. `pruefe_ausstiege` behaelt
        # sie dann (seit 29.09.2026 mit Meldung auf stderr) - sie wird nie
        # geschlossen, belegt einen Platz und das Journal friert ein.
        #
        # `preis_fuer(inst)` liefert den Kurs EINES Symbols aus der Spur
        # (CoinGecko, OKX, Pump, Robinhood-DB). Er wird NUR fuer offene
        # Positionen aufgerufen, die keinen Kurs haben - die Spur entscheidet,
        # welche Preisquelle gilt. Fehler werden gemeldet, nicht geworfen.
        if preis_fuer:
            for p in z.get("positionen", []):
                inst = p.get("inst")
                if not inst or inst in kurse:
                    continue
                try:
                    preis = preis_fuer(inst)
                except Exception as e:                             # noqa: BLE001
                    fehler.append("Preis %s: %s" % (str(inst)[:8], str(e)[:80]))
                    continue
                if preis and preis > 0:
                    kurse[inst] = preis
        if not daten:
            grund = "; ".join(fehler)[:200] if fehler else "keine Instrumente"
            print("Keine Daten - Zyklus ohne Buchung beendet (%s)" % grund)
            if modus == "vorschau":
                print("Vorschau: keine Dateien geschrieben.")
                return 0
            # Der Zyklus ist GELAUFEN, auch wenn er nichts zu buchen hatte.
            # Ohne diesen Schreibvorgang fror `letzter_lauf` ein, und die
            # stille-spuren-wache meldete "TOT" fuer eine Spur, die alle
            # 15 Minuten arbeitet (23.09.2026, robinhood_radar: der Radar hatte
            # schlicht keine Kaeufe von bewerteten Wallets). Ein trockener
            # Zulauf ist keine tote Spur - und der GRUND gehoert in den
            # Zustand, sonst ist Stille nicht zu deuten.
            z["datenlage"] = {"keine_daten": True, "grund": grund,
                              "hinweis": datenlage() if datenlage else None}
            schreibe_zustand(zustand_pfad, z)
            spiegeln(zustand_pfad, journal_pfad, z, w)
            return 0

        if modus == "vorschau":
            # NICHTS schreiben - auch keine Ausstiege. Genau das war der
            # Geist vom 05.10.2026 (T-356): `pruefe_ausstiege()` buchte die
            # Verkaufszeile, der Vorschau-Zweig kehrte danach ohne
            # `schreibe_zustand()` zurueck - das Journal hatte den Verkauf,
            # der Zustand die Position noch offen, und der Dauerlauf
            # verkaufte sie jede Runde neu. Die Vorschau steht deshalb VOR
            # jeder Buchung: sie rechnet nur. Auch dauerlauf.nur_fenster_
            # fehlt() ruft sie auf - lesend, fuer die Sperrenzeile.
            for inst in sorted(daten):
                seite = signal(daten[inst], w)
                if seite:
                    linie = ziel(daten[inst], w) if ziel else None
                    print("Vorschau: Einstieg waere %s %s%s"
                          % (seite.upper(), inst,
                             ("  Ziel %.2f" % linie) if linie else ""))
            print("Vorschau: keine Dateien geschrieben.")
            return 0

        pruefe_ausstiege(z, kurse, w, journal_pfad, zustand_pfad=zustand_pfad,
                         live=live, weg=weg, zusatz=zusatz_ausstieg)

        # STUFEN-KONTROLLE (PLAN §4.2), HINTER den Ausstiegen: Stop und Ziel
        # sind die teurere Wahrheit (ZUSATZ-AUSSTIEG in pruefe_ausstiege) -
        # erst wenn sie gerissen sind, darf die Stufe den Rest schliessen.
        # Stuende sie davor, stuende "stufenueberschreitung" im Journal, wo die
        # ehrliche Ursache "stop" heisst; genau diese Verzerrung soll §4.1
        # abbauen (gepinnt durch tests/test_kill_nach_frist.py::
        # test_stop_hat_vorrang_vor_zwangsschluss).
        stufen_kill = False
        offen_risiko, stufen_grenze, stufen_quelle = pruefe_stufen(z, w)
        if stufen_grenze is not None and offen_risiko > stufen_grenze:
            print("STUFEN-KILL: offenes Buchrisiko %.2f > %.2f (%s) - "
                  "%d Position(en) werden zum Marktkurs geschlossen."
                  % (offen_risiko, stufen_grenze, stufen_quelle,
                     len(z["positionen"])))
            kill_schliessen(z, w, quelle, preis_fuer, journal_pfad, zustand_pfad,
                            live=live, weg=weg, grund=STUFEN_GRUND, kurse=kurse)
            stufen_kill = True
            # Der Nachweis fuer die Nachsicht: der Zustand traegt, WANN mit
            # welcher Zahl geschlossen wurde - sonst ist ein leeres Buch nach
            # dem naechsten Zyklus nicht mehr zu deuten.
            z["stufen_kill"] = {"zeit": jetzt(),
                                "offenes_risiko_usd": round(offen_risiko, 2),
                                "grenze_usd": round(stufen_grenze, 2),
                                "quelle": stufen_quelle}

        # TRIGGER_MODUS (seit 03.10.2026, Auftrag Max "weniger handeln"):
        # Im Signal-Modus wird nur dann gehandelt, wenn sich die Richtung des
        # Indikators GEAENDERT hat. Das verhindert, dass ein erfuelltes Signal
        # alle 15 Minuten den selben Einstieg ausloest. Ohne diesen Check
        # waere jede Spur latent ueberhandelnd, ohne dass die Signale selbst
        # falsch waeren.
        #
        # NUR IM LIVE-BETRIEB (T-347, Regel in `signal_gatter_gilt`).
        signal_gatter = signal_gatter_gilt(w, live)
        for inst in sorted(daten):
            # Nach einem Stufen-Kill wird in DIESEM Zyklus nicht neu eroeffnet.
            # Das Buch war gerade ueber der Grenze; sofort wieder aufzubauen
            # waere ein auf-zu-auf im Journal, und der Zwangsschluss ist eine
            # Meldung, keine Einladung.
            if stufen_kill:
                break
            seite = signal(daten[inst], w)
            if not seite:
                continue
            # TRIGGER_MODUS-Signal-Wechsel (siehe Doku oben)
            if signal_gatter:
                if not signal_gewechselt(z, inst, seite, w):
                    continue  # Signal unveraendert -> kein neuer Einstieg
                # Signal-Wechsel in die Queue schreiben, damit der
                # signal-executor (Hermes-Cron) unabhaengig vom Dauerlauf ausfuehrt.
                _signal_queue(ordner, inst, seite, kurse.get(inst))
                if SCHREIBEN:
                    telemetrie.signal_ausgewaehlt(journal_pfad, inst, seite,
                                                  "live", risikostufe.stufe())
                continue
            p = einstieg(z, inst, seite, kurse.get(inst), w, faktor,
                         None,
                         ziel_preis=(ziel(daten[inst], w) if ziel else None),
                         journal_pfad=journal_pfad, live=live, weg=weg)
            if p:
                print("EINSTIEG %s %s @ %.6f  Stop %.2f%%  Ziel %.6f  "
                      "Nominal %.2f USD"
                      % (seite.upper(), inst, p["einstieg"], p["stop_pct"],
                         p["ziel"], p["nominal"]))
                # T-178: der echte Einstiegsgrund aus der Datenkarte, nicht
                # der Platzhalter. `einstiegsgrund` liest `_grund` aus der
                # Wache (LLM-Spuren schreiben Aktion+Confidence hinein),
                # dann `begruendung(d, w, seite)` der Spur, dann die
                # Messwerte aus dem Signal. Der Platzhalter-Satz wird
                # erkannt und nie geschrieben.
                grund = einstiegsgrund(w, daten[inst], seite, spur_name)
                buche(z, zustand_pfad, journal_pfad, zeit=jetzt(),
                        modus="live" if live else "papier",
                        aktion="kauf", inst=inst, seite=seite,
                        # Die Kennung entsteht in `einstieg()` und steht in
                        # JEDER Zeile dieser Position (T-095).
                        pos_id=p["pos_id"],
                        preis=pformat(p["einstieg"]),
                        einsatz_usd="%.2f" % p["nominal"],
                        stop=pformat(p["stop"]), ziel=pformat(p["ziel"]),
                        stop_pct="%.2f" % p["stop_pct"],
                        grund=grund)
                if SCHREIBEN:
                    modus_text = "live" if live else "papier"
                    telemetrie.signal_ausgewaehlt(journal_pfad, inst, seite,
                                                  modus_text,
                                                  risikostufe.stufe())
                    telemetrie.eroeffnet(journal_pfad, p, modus_text, inst,
                                         seite, risikostufe.stufe())

        z["datenlage"] = {"keine_daten": False, "kandidaten": len(daten),
                          "hinweis": datenlage() if datenlage else None}
        schreibe_zustand(zustand_pfad, z)
        spiegeln(zustand_pfad, journal_pfad, z, w)
        return 0

    begonnen = time.monotonic()
    ergebnis = "fehler"
    try:
        with ereignis.lauf(ereignis_name):
            rc = _lauf()
            ergebnis = "ok" if rc in (0, None) else "fehler"
            return rc
    finally:
        if SCHREIBEN and modus in ("papier", "live") and ergebnis == "fehler":
            telemetrie.lauf_fehlgeschlagen(journal_pfad,
                                           time.monotonic() - begonnen, modus,
                                           risikostufe.stufe())
def _signal_queue(ordner, inst, seite, kurs):
    """Signal-Wechsel in die Queue schreiben (vom signal-executor abgeholt).

    STUENENFaeHIG - und das war ein Fehler in der ersten Fassung: die Datei
    hiess fest `signal_queue.json`, waehrend `pfade()` Zustand und Journal
    je Risikostufe ablegt. Die drei Stufen (Basis, mittel, hoch) fahren
    dieselbe Spur mit eigener `vor_signal` und schrieben deshalb alle in
    EINE Queue: gemessen am 03.10.2026 drei Eintraege innerhalb von acht
    Minuten, alle "long", alle vom selben Instrument. Ohne Stufen-Suffix
    ist die Queue kein Signal, sondern ein Dreifach-Echo.
    """
    import datetime, json
    pfad = risikostufe.datei(os.path.join(ordner, "signal_queue.json"))
    preis = float(kurs) if kurs else 0.0
    eintrag = [inst, seite, preis, datetime.datetime.now().isoformat()]
    try:
        with open(pfad, encoding="utf-8") as fh:
            q = json.load(fh)
    except (OSError, ValueError):
        q = []
    if not isinstance(q, list):
        q = []
    q.append(eintrag)
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(q, fh, ensure_ascii=False, indent=1)
    print("  Signal %s %s -> Queue (%d Eintraege)" % (seite.upper(), inst, len(q)))
