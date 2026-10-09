"""Die Kraken-Spur: Kraken-Paper-Node als Papierzyklus im Dauerlauf.

Zwei Produkttypen, ein Kern: Spot (BTC/EUR, kein Hebel, EUR) und Futures
(PF_XBTUSD Perpetual, Hebel, USD). Symbol, Waehrung und Grenzen kommen aus
wachen.json. Jeder Lauf startet den Node fuer eine begrenzte Zeit (~30 s),
sammelt Quotes vom oeffentlichen Websocket und schreibt Zustand (Herzschlag)
und Journal. Mehr ist auf Papier nicht zu tun: Die Strategie fuehrt ein
Papierbuch, es gibt keinen Live-Orderpfad.

KEIN ORDERPFAD
--------------
--live verweigert mit genau einem Grund, in dem das Wort Freigabefenster
NICHT vorkommt - so fragt der Dauerlauf keine Freigabe an, die nichts
oeffnen kann (Muster: spiegel-Spur, omniquant-Spur, papierfest).

JOURNAL AUSSER HAUS (Bedingung 4)
---------------------------------
Nach jedem Zyklus gehen handelsjournal.csv und zustand.json zusaetzlich nach
`journal_zweitziel` aus wachen.json (Q:). Die Kopie entsteht NACH dem
Schreiben von Herzschlag und Journal.

Aufruf:
    python handeln.py --vorschau   # was waere dran, ohne zu schreiben
    python handeln.py --papier     # ein Papierzyklus mit Journal
    python handeln.py --wachen     # Grenzen als Momentaufnahme
    python handeln.py --live       # verweigert, nennt den Grund
"""

import argparse
import csv
import importlib.util
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone

# OpenBLAS-Speichersturz (24.09.2026): nautilus_trader zieht numpy -> OpenBLAS
# und oeffnet beim Import so viele Thread-Buffer wie Kerne da sind. Drei
# nautilus-Spuren x Basis+Mittel laufen im Dauerlauf ZYKLUS-WEISE parallel;
# jedes Lademal "Memory allocation still failed" (heute ~2x so viele
# Fehlschlaege wie Erfolge). Mit Threads=1 laeuft der Import zuverlaessig
# durch. setdefault: ein bewusster Themenaufsatz gewinnt.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")


HIER = os.path.dirname(os.path.abspath(__file__))
BUS = os.path.join(HIER, os.pardir, os.pardir, "Bus")
for p in (HIER, BUS):
    if p not in sys.path:
        sys.path.insert(0, p)

import ereignis                                                       # noqa: E402
import run_kraken_paper_node as node_mod                              # noqa: E402
import trailing_stop_strategie                                        # noqa: E402

from nautilus_trader.config import LoggingConfig                      # noqa: E402
from nautilus_trader.config import TradingNodeConfig                  # noqa: E402
from nautilus_trader.model.identifiers import InstrumentId            # noqa: E402
from nautilus_trader.trading.config import StrategyConfig             # noqa: E402
from nautilus_trader.trading.strategy import Strategy                 # noqa: E402

# Risikostufe (HANDEL_RISIKO): Faktor auf die Betraege, Suffix auf Zustand
# und Journal. Ueber den PFAD geladen wie ratschen.py.
from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec
_rs_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "risikostufe.py")
_rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
risikostufe = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(risikostufe)

# Freigabefenster und Freigabe-Beleg ueber den PFAD laden - Handel/ liegt im
# Spurlauf NICHT auf sys.path (nur <spur>/../../Bus). Ein blankes 'import
# freigabefenster' wuerde still einen anderen Ordner treffen oder scheitern.
_fw_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "freigabefenster.py")
_fw_spec_obj = _rs_spec("freigabefenster", _fw_datei)
freigabefenster = _rs_mod(_fw_spec_obj)
_fw_spec_obj.loader.exec_module(freigabefenster)

_fb_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "freigabebeleg.py")
_fb_spec_obj = _rs_spec("freigabebeleg", _fb_datei)
freigabebeleg = _rs_mod(_fb_spec_obj)
_fb_spec_obj.loader.exec_module(freigabebeleg)

# Kraken-REST-Orderweg (laedt kraken/kraken.py ueber den Pfad).
import kraken_rest                                                       # noqa: E402

WACHEN = os.path.join(HIER, os.environ.get("KRAKEN_WACHEN", "wachen.json"))
# Spurname fuer Freigabefenster/-beleg (Spot=nautilus_kraken, Futures=..._futures).
SPUR_NAME = os.environ.get("KRAKEN_SPUR_NAME", "nautilus_kraken")
# Futures-Variante fuehrt getrennte Zustand/Journal-Dateien (Suffix .futures),
# damit Spot und Futures nicht denselben Zustand teilen (Muster: spiegel_knapp/weit).
_SUFFIX = os.environ.get("KRAKEN_SUFFIX", "")
ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand%s.json" % _SUFFIX))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal%s.csv" % _SUFFIX))

SPALTEN_BASIS = ["zeit", "modus", "aktion", "inst", "bid", "ask", "quotes",
                 "grund", "symbol", "token", "preis", "menge"]

# Eine begrenzte Node-Session. 30 s Quoten sammeln (OKX-Spur: 41 Ticks);
# der Dauerlauf-Timeout liegt bei 600 s, die Session ist also ein Bruchteil.
LAUFZEIT_S = 30

# Einstiegs-Signale und Herzschlag-Fallback: die KOPIER-Spur (Pump.fun
# Copy Trade). Frische Kaeufe dort werden zu Papier-Positionen; faellt der
# Kraken-Quote-Feed aus, haelt die Spur ihren Herzschlag ueber die
# Kopier-Daten am Leben, statt still totzugehen.
KOPIER_JOURNAL = risikostufe.datei(os.path.join(HIER, os.pardir, "kopier", "handelsjournal.csv"))
KOPIER_ZUSTAND = risikostufe.datei(os.path.join(HIER, os.pardir, "kopier", "zustand.json"))
FEED_SCHONFRIST_S = 15 * 60     # ein Dauerlauf-Takt

# Der Log-Pegel der begrenzten Node-Session. Bewusst ERROR, nicht WARNING:
# dauerlauf.zyklus() filtert die AUSGABE jeder Spur zeilenweise nach den
# Stichwoertern verkauf/stop/KILL/gesperrt/ausstieg und schickt jede
# Trefferzeile nach Telegram.
LOG_PEGEL = "ERROR"

# Ob geschrieben wird. Die Vorschau stellt das ab (siehe journal()).
SCHREIBEN = True


def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _bis_zeit(iso):
    try:
        return datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def lade(pfad, vorgabe=None):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return vorgabe


# Zustand atomar schreiben und laut lesen (atomar.py, 30.09.2026). Ueber den
# PFAD geladen wie risikostufe.py: die Spur hat ihren eigenen Ordner als
# sys.path[0]. Defekte Datei -> Sicherung .bak, sonst laute Ausnahme statt
# leerem Bestand.
from importlib.util import module_from_spec as _at_mod, \
    spec_from_file_location as _at_spec
_at_obj = _at_spec("atomar", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "atomar.py"))
atomar = _at_mod(_at_obj)
_at_obj.loader.exec_module(atomar)


def lade_zustand():
    z = atomar.lade_json(ZUSTAND, lambda: None) or {}
    z.setdefault("modus", "papier")
    z.setdefault("letzter_lauf", None)
    z.setdefault("zyklen", 0)
    z.setdefault("positionen", [])
    z.setdefault("letzte_quote", None)
    z.setdefault("feed_quelle", "kraken")
    return z


def lies_kopier_signale(seit_iso):
    """Frische Kopier-Kaeufe als Einstiegs-Signale (Pump.fun Copy Trade)."""
    if not seit_iso or not os.path.exists(KOPIER_JOURNAL):
        return []
    aus = []
    try:
        with open(KOPIER_JOURNAL, newline="", encoding="utf-8") as f:
            for zeile in csv.DictReader(f):
                if (zeile.get("aktion") or "").strip().lower() != "eroeffnen":
                    continue
                if (zeile.get("zeit") or "") <= seit_iso:
                    continue
                aus.append({"zeit": zeile.get("zeit", ""),
                            "token": zeile.get("token", ""),
                            "symbol": zeile.get("symbol", "")})
    except OSError:
        return []
    return aus


def kopier_frisch():
    """Ist die Kopier-Spur am Leben? (Herzschlag-Fallback)"""
    z = lade(KOPIER_ZUSTAND, None) or {}
    t = _bis_zeit(z.get("letzter_lauf"))
    if t is None:
        return False
    return (datetime.now(timezone.utc) - t).total_seconds() <= FEED_SCHONFRIST_S


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def journal(w, **felder):
    if not SCHREIBEN:
        return
    waehrung = w.get("waehrung", "usd").lower()
    spalten = SPALTEN_BASIS + ["einsatz_%s" % waehrung, "wert_%s" % waehrung]
    neu = not os.path.exists(JOURNAL)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in spalten})


# --- Bedingung 4: Journal ausser Haus ---------------------------------------

def _spiegelquelle():
    """scanner/wachen_pruefung.py laden - die eine Spiegel-Implementierung
    des Hauses, statt sie hier abzuschreiben."""
    pfad = os.path.join(HIER, os.pardir, "scanner", "wachen_pruefung.py")
    spec = importlib.util.spec_from_file_location("wachen_pruefung_quelle",
                                                 pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def spiegle_journal(ziel, dateien=(JOURNAL, ZUSTAND)):
    """Journal und Zustand nach `ziel` kopieren. (ok, Pfad-oder-Grund)."""
    if not ziel:
        return False, "journal_zweitziel nicht gesetzt"
    try:
        return _spiegelquelle().spiegele_journal(list(dateien), ziel)
    except Exception as e:                                   # noqa: BLE001
        return False, "%s: %s" % (type(e).__name__, e)


def vermerke_spiegelung(z, ziel, ok, info, pfad=None):
    """Ergebnis der Spiegelung in den Zustand schreiben - nur bei Aenderung."""
    def schreiben(zustand):
        atomar.schreibe_json(pfad or ZUSTAND, zustand)

    return _spiegelquelle().vermerke_spiegelung(z, ziel, ok, info, schreiben)


# --- Der begrenzte Node-Lauf ------------------------------------------------

class QuoteSammler(Strategy):
    """Abonniert Kraken-Quotes und haelt die Ticks in einer Liste."""

    def __init__(self, config, symbol):
        super().__init__(config)
        self.quotes = []
        self.ziel = None
        self.symbol = symbol

    def on_start(self):
        ziel = InstrumentId.from_str("%s.KRAKEN" % self.symbol)
        for inst in self.cache.instruments():
            if self.symbol in str(inst.id):
                ziel = inst.id
                break
        self.ziel = ziel
        self.subscribe_quote_ticks(ziel)
        self.log.info(f"Subscribed quotes: {ziel}")

    def on_quote_tick(self, tick):
        self.quotes.append(tick)

    def on_stop(self):
        """Muss ueberschrieben sein - sonst warnt die Engine."""
        if self.ziel is not None:
            try:
                self.unsubscribe_quote_ticks(self.ziel)
            except Exception:                                  # noqa: BLE001
                pass
        self.log.info(f"Zyklus beendet, {len(self.quotes)} Quotes gesammelt")


def baue_node_config(daten, ausfuehrung):
    """Die Node-Config eines Zyklus - ausgelagert, damit ein Test sie pruefen
    kann, ohne einen Node (und damit das Netz) zu starten."""
    return TradingNodeConfig(
        environment="sandbox",
        logging=LoggingConfig(log_level=LOG_PEGEL),
        data_clients=daten,
        exec_clients=ausfuehrung,
    )


def sammle_quoten(sekunden=LAUFZEIT_S, wachen=None, positionen=None,
                  signale=None, buchungen=None):
    """Eine begrenzte Node-Session; gibt ein Tupel zurueck:
    (quotes, positionen, buchungen).

    Bewusst ohne Order-Client (mit_order_client=False) und ohne Zugangsdaten
    am Data-Client - das ist der gemessene saubere Quotenpfad.
    """
    symbol = wachen.get("symbol", "BTC/EUR") if wachen else "BTC/EUR"
    data_clients, exec_clients = node_mod.load_client_configs(
        symbol, mit_order_client=False)
    config = baue_node_config(data_clients, exec_clients)
    node = node_mod.KrakenPaperNode(config=config)
    strat = QuoteSammler(StrategyConfig(strategy_id="kraken-zyklus"), symbol)
    node.trader.add_strategy(strat)
    handel = None
    if wachen is not None:
        from trailing_stop_strategie import TrailingStopStrategie
        handel = TrailingStopStrategie(
            StrategyConfig(strategy_id="kraken-strategie"),
            wachen, positionen or [], signale or [], buchungen or [])
        node.trader.add_strategy(handel)
    node.build()

    fehler = []

    def lauf():
        try:
            node.run()
        except Exception as exc:                              # noqa: BLE001
            fehler.append(exc)

    t = threading.Thread(target=lauf, daemon=True,
                         name="kraken-zyklus")
    t.start()
    time.sleep(sekunden)
    try:
        node.stop()
    except Exception:                                        # noqa: BLE001
        pass
    time.sleep(1)
    if fehler:
        raise RuntimeError("Node-Lauf fehlgeschlagen: %r" % (fehler[0],))
    if handel is None:
        return strat.quotes, positionen or [], buchungen or []
    return strat.quotes, handel.positionen, handel.buchungen


# --- Ausgabe und Lauf -------------------------------------------------------

def zeige_wachen(w):
    print("Grenzen aus wachen.json (Momentaufnahme):")
    for k in ("symbol", "waehrung", "produkt", "max_risiko_pro_trade",
              "max_risiko_gesamt", "max_offene_positionen", "max_hebel",
              "kill_switch_gesamt", "herzschlag_max_minuten", "slippage_pct",
              "gebuehr_pct", "stop_pct", "trail_aktiv_ab_pct",
              "trail_abstand_pct", "haltedauer_stunden", "signalquelle",
              "einfall_herzschlag_kopier"):
        print("  %-28s %s" % (k, w.get(k)))
    print("  %-28s %s" % ("handel_erlaubt", w.get("handel_erlaubt")))
    freigabe = w.get("freigabe") or {}
    print("  %-28s %s" % ("freigabe.erfuellt", freigabe.get("erfuellt")))
    # Live rechnet mit eigenen Grenzen (live_wachen): der Papier-Einsatz von
    # 50 EUR geht live NICHT raus - sonst zeigt --wachen eine Zahl, die der
    # Live-Lauf gar nicht benutzt.
    if w.get("live_einsatz_eur") or w.get("live_max_risiko_gesamt_eur"):
        lw = live_wachen(w)
        print("  %-28s %s" % ("live_einsatz_eur", w.get("live_einsatz_eur")))
        print("  %-28s %s" % ("  live max_risiko_pro_trade",
                              lw.get("max_risiko_pro_trade")))
        print("  %-28s %s" % ("  live max_risiko_gesamt",
                              lw.get("max_risiko_gesamt")))
    z = lade_zustand()
    print("  %-28s %s" % ("journal_zweitziel",
                          w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  %-28s %s" % ("  letzte Kopie",
                          "%s (%s)" % (z.get("journal_zweitziel_ok"),
                                       z.get("journal_zweitziel_info"))))


def lade_wachen():
    """Wachen dieser Spur samt Risikostufe."""
    return risikostufe.skaliere(lade(WACHEN, None))


def live_wachen(w):
    """Wachen fuer den LIVE-Lauf: eigener Einsatz, eigener Gesamtdeckel.

    Der Papierlauf bleibt bei max_risiko_pro_trade 50 EUR und
    max_risiko_gesamt 200 EUR; live wird in Cent-Hoehe geprueft
    (live_einsatz_eur, T-065). max_risiko_gesamt gilt live NICHT - bei
    1-EUR-Einsaetzen waere er wirkungslos und bei einem spaeteren Anheben
    zu weit. Rueckgabe ist eine KOPIE: der Aufrufer schreibt w nicht
    zurueck in die Datei.
    """
    if not (w.get("live_einsatz_eur") or w.get("live_max_risiko_gesamt_eur")
            or w.get("live_einsatz_usd") or w.get("live_max_risiko_gesamt_usd")):
        return w
    lw = dict(w)
    # Beide Waehrungsnamen: Spot-Spuren (kraken, mosaic) rechnen in EUR, die
    # Futures-Spur in USD. Gelesen wird derselbe Gedanke - der Einsatz je
    # Position und der Deckel des Live-Buchs.
    einsatz = lw.get("live_einsatz_eur") or lw.get("live_einsatz_usd")
    deckel = lw.get("live_max_risiko_gesamt_eur") or lw.get("live_max_risiko_gesamt_usd")
    if einsatz:
        lw["max_risiko_pro_trade"] = float(einsatz)
    if deckel:
        lw["max_risiko_gesamt"] = float(deckel)
    return lw


def sperren_zeile(w):
    """Sperrgruende fuer den Live-Modus - oder None, wenn live erlaubt.

    Die Sperrenkette: handel_erlaubt, freigabe.erfuellt, offenes
    Freigabefenster. Nur wenn ALLE offen sind, darf die Spur echte Orders
    ueber kraken_rest aufgeben. Ein Chat kann kein Fenster oeffnen -
    freigabefenster.oeffnen verweigert ohne wartende Anfrage, die stellt nur
    der laufende Dauerlauf (Muster: kraken-Spur).
    """
    sperren = []
    if not w.get("handel_erlaubt"):
        sperren.append("handel_erlaubt=false")
    freigabe = w.get("freigabe") or {}
    if not freigabe.get("erfuellt"):
        sperren.append("freigabe.erfuellt=false")
    try:
        fenster = freigabefenster.lade(SPUR_NAME)
        if not fenster.offen():
            sperren.append("Freigabefenster zu")
    except Exception as e:                                   # noqa: BLE001
        sperren.append("Freigabefenster nicht lesbar (%s)" % e)
    if kraken_rest.produkt() == "futures":
        # Futures besichert aus dem CASH-Konto der Futures-Boerse. Ohne freies
        # USD ist jede Order abgelehnt - das ist ein Guthaben-Grund, kein
        # Fenster-Grund (Muster moondev_marktlage). Geprueft wird der KLEINSTE
        # handelbare Satz (1 Kontrakt = 1 Einheit der Basiswaehrung, gemessen
        # 25.09.2026): 1 Kontrakt PF_SOLUSD braucht rund 11,75 USD Einschuss,
        # PF_XBTUSD rund 8.450 USD. Der Sperrtext nennt die Zahl, damit
        # "Guthaben reicht nicht" nachpruefbar ist.
        try:
            frei = kraken_rest.guthaben()
            grund = kraken_rest.handelbar(w.get("paar"), 1, frei=frei)
            if grund:
                sperren.append(grund)
            else:
                # Zweite Sperre: ein Einsatz, der unter EINEM Kontrakt liegt,
                # wird beim Senden aufgerundet - die echte Position waere dann
                # ein Vielfaches des gedachten Einsatzes. Das ist keine
                # Rundung, das ist ein anderer Handel.
                einsatz = float(w.get("live_einsatz_usd")
                                or w.get("live_einsatz_eur") or 0)
                noetig = kraken_rest.einschuss(w.get("paar"), 1)
                if einsatz and noetig and einsatz < noetig:
                    sperren.append(
                        "Einsatz %.2f kleiner als 1 Kontrakt %s (%.2f USD "
                        "Einschuss) - Mindestgroesse der Boerse"
                        % (einsatz, w.get("paar"), noetig))
        except Exception as e:                                   # noqa: BLE001
            sperren.append("Futures-Guthaben nicht abrufbar (%s)" % e)
    else:
        # Spot: der Einsatz kommt aus dem freien EUR-Guthaben. Kraken
        # reserviert die Menge erst bei der Order - ohne freies Guthaben
        # scheitert sie mit 'EOrder:Insufficient funds' und die Spur saehe
        # trotzdem 'ok' aus. Muster kraken/mosaic.
        try:
            noetig = float(w.get("live_einsatz_eur")
                           or w.get("mindest_guthaben_eur") or 0)
            if noetig:
                frei = kraken_rest.guthaben()
                if frei < noetig:
                    sperren.append(
                        "Guthaben zu klein (%.2f EUR frei, noetig %.2f)"
                        % (frei, noetig))
        except Exception as e:                               # noqa: BLE001
            sperren.append("Guthaben nicht abrufbar (%s)" % e)
    return "; ".join(sperren) if sperren else None


def bueche_papier_altlasten_aus(z, w):
    """Positionen OHNE modus=live aus dem Live-Buch buchen.

    Anlass (25.09.2026, gemessen): Vier Papier-Positionen aus der
    Kopier-Signalphase belegten alle vier Plaetze (max_offene_positionen 4).
    Die Spur ist armiert (handel_erlaubt=true, freigabe.erfuellt=true) - jeder
    Live-Zyklus lief aber in "Buch voll", eine echte Order kam nie zustande.
    Dieselbe Klasse wie scanner/xperp/kraken am 21.09.2026.

    Deshalb zu Beginn JEDES Live-Laufs ausbuchen, als PAPIER-Verkauf mit Grund
    "buchbereinigung": die Positionen hat nie eine Order gekauft, an der Boerse
    gibt es nichts zu verkaufen. Positionen mit modus=live (echte Bestaende,
    txid) bleiben unangetastet. Idempotent.
    """
    positionen = z.get("positionen") or []
    if not [p for p in positionen if p.get("modus") != "live"]:
        return 0
    waehrung = (w.get("waehrung") or "eur").lower()
    einsatz_feld = "einsatz_%s" % waehrung
    wert_feld = "wert_%s" % waehrung
    paar = w.get("paar", "BTC/EUR")
    behalten = []
    gebucht = 0
    for p in positionen:
        if p.get("modus") == "live":
            behalten.append(p)
            continue
        kurs = None
        try:
            kurs = kraken_rest.letzter_kurs(p.get("token") or paar)
        except Exception as e:                                 # noqa: BLE001
            print("  Buchbereinigung %s: kein Kurs (%s)" % (p.get("token"), e))
        kurs = kurs or p.get("letzter_kurs")
        if not kurs:
            print("  Buchbereinigung %s: kein Kurs - bleibt liegen"
                  % p.get("token"), file=sys.stderr)
            behalten.append(p)
            continue
        einstieg = float(p.get("preis_einstieg") or kurs)
        einsatz = float(p.get(einsatz_feld) or 0.0)
        erloes = einsatz * (float(kurs) / einstieg)
        print("  Buchbereinigung: %s %s (ohne Live-Order) @ %.10g  "
              "G/V %+.2f %s" % (p.get("symbol", "?"), p.get("token"), kurs,
                                erloes - einsatz, waehrung.upper()))
        journal(w, zeit=_jetzt(), modus="papier", aktion="schliessen",
                inst=p.get("token") or paar, grund="buchbereinigung",
                symbol=p.get("symbol", ""), token=p.get("token", ""),
                preis="%.10g" % kurs, menge="%.6f" % p.get("menge", 0.0),
                **{einsatz_feld: "%.2f" % einsatz,
                   wert_feld: "%.2f" % erloes})
        gebucht += 1
    z["positionen"] = behalten
    return gebucht


def lauf(modus):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = lade_wachen()
    if not w:
        print("wachen.json fehlt oder ist unlesbar - kein Lauf.")
        return 1

    symbol = w.get("symbol", "BTC/EUR")
    waehrung = w.get("waehrung", "usd").lower()
    einsatz_feld = "einsatz_%s" % waehrung
    wert_feld = "wert_%s" % waehrung

    if modus == "wachen":
        zeige_wachen(w)
        return 0

    # EINMAL je Zyklus fragen und das Ergebnis weiterverwenden: sperren_zeile
    # liest das Guthaben ueber die Boerse - zweimal fragen kostet eine
    # ueberfluessige Runde und kann zwischen den Aufrufen kippen.
    live_vorab = False
    if modus == "live":
        sperren = sperren_zeile(w)
        live_vorab = not sperren
        if sperren:
            print("--live angefordert, aber gesperrt: %s" % sperren)
            print("-> es wird Papier gefahren.")
        else:
            print("--live: Freigabekette offen - echte Orders ueber "
                  "Kraken-REST (kraken_rest).")
            w = live_wachen(w)

    if modus == "vorschau":
        print("Waere: Node-Session %d s, %s-Quotes sammeln, Herzschlag und "
              "Journal schreiben, danach Journal + Zustand nach %s kopieren "
              "(Bedingung 4). Keine Order, keine Zugangsdaten am "
              "Data-Client." % (LAUFZEIT_S, symbol,
                                w.get("journal_zweitziel") or "-- nicht gesetzt"))
        print("Live waere gesperrt durch: %s"
              % (sperren_zeile(w) or "nichts"))
        return 0

    # Papierzyklus: Signale aus der Kopier-Spur, begrenzter Node-Lauf mit
    # der Trailing-Stop-Strategie, dann Herzschlag, Journal und Buchungen.
    z = lade_zustand()
    seit = z.get("kopier_signale_seit") or z.get("letzter_lauf") or ""
    signale = lies_kopier_signale(seit)
    positionen = z.get("positionen") or []
    # Ein Live-Lauf uebernimmt kein Papierbuch (Muster kraken/scanner/xperp):
    # die Papier-Positionen belegen sonst die Plaetze und live wird nie
    # gekauft. VOR sammle_quoten - die Platzzahl wird dort geprueft.
    if live_vorab:
        n_alt = bueche_papier_altlasten_aus(z, w)
        if n_alt:
            print("  %d Papier-Altlast(en) aus dem Live-Buch gebucht" % n_alt)
            positionen = z["positionen"]
            schreibe_zustand(z)
        # Boersenabgleich (T-227): Buch gegen Boerse, nur im Live-Modus.
        # Laeuft nach dem Buchabgleich, vor den Ausstiegen. Ist die Boerse
        # nicht lesbar, bleibt alles unangetastet.
        try:
            import boersenabgleich
            boersenabgleich.pruefe(z, wachen=w, anwenden=True,
                                   journal=lambda **f: journal(w, **f),
                                   standard="kraken")
            schreibe_zustand(z)
        except Exception as e:
            print("  Boersenabgleich gescheitert (%s) - weiter ohne" % e)
    # Papierstand im gemeinsamen Buch: Positionen ohne modus=live stammen aus
    # dem Papierlauf. Ein Live-Lauf darf sie NICHT anfassen - sonst verkauft
    # der erste echte Zyklus BTC, das nie gekauft wurde (scanner/xperp hatten
    # genau diesen Fall).
    papier_tokens = {p.get("token") for p in positionen
                     if p.get("modus") != "live"}
    buchungen = []
    feed_ok = False
    try:
        quotes, positionen, buchungen = sammle_quoten(
            wachen=w, positionen=positionen, signale=signale,
            buchungen=buchungen)
        feed_ok = bool(quotes)
    except Exception as e:                                   # noqa: BLE001
        print("Kraken-Zyklus gescheitert (%s) - Fallback pruefen" % e)

    jetzt = _jetzt()

    if not feed_ok:
        # Herzschlag-Fallback: lebt die Kopier-Spur, bleibt die Spur am
        # Leben. Positionen ruhen ohne Kurse - nur abgelaufene Fristen
        # werden zum letzten Kurs geschlossen.
        if not kopier_frisch():
            print("  KEINE Quote angekommen und Kopier-Spur tot - "
                  "Quotenpfad pruefen (run_kraken_paper_node.py).")
            return 1
        jetzt_dt = datetime.now(timezone.utc)
        rest = []
        for p in positionen:
            if jetzt_dt < (_bis_zeit(p.get("frist")) or jetzt_dt):
                rest.append(p)
                continue
            kurs = p.get("letzter_kurs")
            if not kurs:
                rest.append(p)
                continue
            from trailing_stop_strategie import verkaeuflich
            erloes = verkaeuflich(p["menge"], kurs, w)
            print("  AUSSTIEG (frist): %s %s @ %.10g  G/V %+.2f %s auf "
                  "%.0f %s"
                  % (p.get("symbol", "?"), p["token"], kurs,
                     erloes - p[einsatz_feld], waehrung.upper(),
                     p[einsatz_feld], waehrung.upper()))
            journal(w, zeit=jetzt, modus="papier", aktion="schliessen",
                    inst=symbol, grund="frist", symbol=p.get("symbol", ""),
                    token=p["token"], preis="%.10g" % kurs,
                    menge="%.6f" % p["menge"],
                    **{einsatz_feld: "%.2f" % p[einsatz_feld],
                       wert_feld: "%.2f" % erloes})
        positionen = rest
        z["modus"] = "papier"
        z["zyklen"] = z.get("zyklen", 0) + 1
        z["quotes_letzter_zyklus"] = 0
        z["feed_quelle"] = "fallback_kopier"
        z["positionen"] = positionen
        z["kopier_signale_seit"] = jetzt
        schreibe_zustand(z)
        journal(w, zeit=jetzt, modus="papier", aktion="zyklus", inst=symbol,
                quotes=0, grund="fallback_kopier")
        ziel = w.get("journal_zweitziel")
        gespiegelt, info = spiegle_journal(ziel)
        if vermerke_spiegelung(z, ziel, gespiegelt, info) and gespiegelt:
            spiegle_journal(ziel, dateien=(ZUSTAND,))
        print("=== Kraken (PAPIER) | Feed tot, Herzschlag ueber "
              "Kopier-Daten | %d Positionen, %d Signale ===\n"
              % (len(positionen), len(signale)))
        print("  Journal ausser Haus: %s"
              % (info if gespiegelt else "nicht kopiert - %s" % info))
        return 0

    z["modus"] = "papier"          # unten auf den echten Buchmodus gezogen
    z["zyklen"] = z.get("zyklen", 0) + 1
    z["quotes_letzter_zyklus"] = len(quotes)
    z["feed_quelle"] = "kraken"
    if quotes:
        letzte = quotes[-1]
        z["letzte_quote"] = {
            "bid": str(letzte.bid_price),
            "ask": str(letzte.ask_price),
            "zeit": str(letzte.ts_event),
        }
    live = live_vorab
    z["modus"] = "live" if live else "papier"
    # Buchungen der Strategie (Kaeufe und Schluesse) ins Journal.
    for b in buchungen:
        # Eine Papier-Position wird im Live-Lauf NICHT geordert. Sie bleibt im
        # Buch stehen und steigt im Papierlauf aus; der Live-Lauf fasst sie
        # nicht an (sonst: echter Verkauf fuer einen nie gekauften Bestand).
        if live and b.get("token") in papier_tokens:
            print("  PAPIER-POSITION im Live-Lauf nicht geordert: %s %s (%s)"
                  % (b["symbol"], b["token"], b["grund"]))
            live_buchung = False
        else:
            live_buchung = live
        if live_buchung:
            # Echte Order ueber Kraken-REST (kraken_rest) - der Nautilus-
            # Adapter kann Fills nicht lesen (postxid-Bug, 24.09.2026),
            # die Order laeuft deshalb direkt ueber die Kraken-REST-API.
            paar = w.get("paar", "BTC/EUR")
            try:
                if b["aktion"] == "schliessen":
                    txid = kraken_rest.markt_verkauf(paar, b["menge"],
                                                     echt=True)
                else:
                    txid = kraken_rest.markt_kauf(paar, b["menge"],
                                                  echt=True)
                b["txid"] = txid
                if b["aktion"] != "schliessen":
                    # Ein nackter Live-Kauf gibt es nicht: der boersenseitige
                    # Stop gehoert zum Kauf. Ohne ihn laeuft die Position bis
                    # zum naechsten Zyklus ungeschuetzt - und der kann bei
                    # einem Rechner-Ausfall Stunden spaeter kommen.
                    stop_pct = float(w.get("stop_pct") or 0)
                    if stop_pct:
                        stop_preis = b["kurs"] * (1 - stop_pct / 100.0)
                        b["stop_id"] = kraken_rest.stop_setzen(
                            paar, b["menge"], stop_preis, echt=True)
                        print("  SCHUTZ-STOP gesetzt: %s %.8f @ %.8f (%s)"
                              % (paar, b["menge"], stop_preis, b["stop_id"]))
            except Exception as e:                   # noqa: BLE001
                print("  LIVE-ORDER GESCHEITERT (%s): %s %s - %s"
                      % (b["aktion"], b["symbol"], b["token"], e))
                # Ein Live-Fehler gehoert ins Journal, nicht nur auf die
                # Konsole: sonst faellt die Buchung still weg und niemand
                # sieht, dass eine Entscheidung nicht ausgefuehrt wurde.
                journal(w, zeit=jetzt, modus="live", aktion="fehler",
                        inst=symbol, grund="order_gescheitert",
                        symbol=b["symbol"], token=b["token"],
                        preis="%.10g" % b["kurs"], menge="%.6f" % b["menge"],
                        **{einsatz_feld: "%.2f" % b[einsatz_feld],
                           wert_feld: ""})
                continue
        modus_buch = "live" if live_buchung else "papier"
        if b["aktion"] == "schliessen":
            print("  AUSSTIEG (%s): %s %s @ %.10g  G/V %+.2f %s auf "
                  "%.0f %s"
                  % (b["grund"], b["symbol"], b["token"], b["kurs"],
                     b[wert_feld] - b[einsatz_feld], waehrung.upper(),
                     b[einsatz_feld], waehrung.upper()))
            journal(w, zeit=jetzt, modus=modus_buch, aktion="schliessen",
                    inst=symbol, grund=b["grund"], symbol=b["symbol"],
                    token=b["token"], preis="%.10g" % b["kurs"],
                    menge="%.6f" % b["menge"],
                    **{einsatz_feld: "%.2f" % b[einsatz_feld],
                       wert_feld: "%.2f" % b[wert_feld]})
        else:
            journal(w, zeit=jetzt, modus=modus_buch, aktion="eroeffnen",
                    inst=symbol, grund=b["grund"], symbol=b["symbol"],
                    token=b["token"], preis="%.10g" % b["kurs"],
                    menge="%.6f" % b["menge"],
                    **{einsatz_feld: "%.2f" % b[einsatz_feld]})
    # Neue Positionen tragen ihren Buchmodus. Alles ohne Stempel ist
    # Papier-Altbestand: der Live-Lauf hat es nie gekauft, also darf er es
    # auch nicht als live fuehren.
    neu_eroeffnet = {b["token"] for b in buchungen
                     if b["aktion"] != "schliessen"}
    for pos in positionen:
        if "modus" not in pos:
            pos["modus"] = ("live" if (live and pos.get("token") in neu_eroeffnet)
                            else "papier")
    z["positionen"] = positionen
    z["kopier_signale_seit"] = jetzt
    schreibe_zustand(z)
    journal(w, zeit=jetzt, modus=("live" if live else "papier"),
            aktion="zyklus", inst=symbol,
            bid=z.get("letzte_quote", {}).get("bid", ""),
            ask=z.get("letzte_quote", {}).get("ask", ""),
            quotes=len(quotes),
            grund="quotes" if quotes else "keine_quotes")

    # Bedingung 4: Journal und Zustand ausser Haus.
    ziel = w.get("journal_zweitziel")
    gespiegelt, info = spiegle_journal(ziel)
    if vermerke_spiegelung(z, ziel, gespiegelt, info) and gespiegelt:
        spiegle_journal(ziel, dateien=(ZUSTAND,))

    print("=== Kraken (%s) | %d Quotes in %d s | %d Signale | "
          "%d Positionen | Herzschlag gesetzt ==="
          % ("LIVE" if live else "PAPIER", len(quotes), LAUFZEIT_S,
             len(signale), len(positionen)))
    print("  Journal ausser Haus: %s"
          % (info if gespiegelt else "nicht kopiert - %s" % info))
    if quotes:
        q = z["letzte_quote"]
        print("  Letzte Quote %s bid=%s ask=%s" % (symbol, q["bid"], q["ask"]))
        return 0
    print("  KEINE Quote angekommen - Quotenpfad pruefen "
          "(run_kraken_paper_node.py).")
    return 1


def main():
    # nautilus_kraken/handeln.py ist der automatische Einstieg (dauerlauf.py
    # ruft dieses Skript per subprocess auf) - es meldet sich damit am Bus.
    # Der Futures-Launcher setzt KRAKEN_BUS_NAME=handel/nautilus_kraken_futures.
    bus_name = os.environ.get("KRAKEN_BUS_NAME", "handel/nautilus_kraken")
    with ereignis.lauf(bus_name):
        return _main()


def _main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--vorschau", action="store_const", dest="modus",
                   const="vorschau")
    g.add_argument("--papier", action="store_const", dest="modus",
                   const="papier")
    g.add_argument("--live", action="store_const", dest="modus", const="live")
    g.add_argument("--wachen", action="store_const", dest="modus",
                   const="wachen")
    a = p.parse_args()
    return lauf(a.modus or "papier")


if __name__ == "__main__":
    raise SystemExit(main())
