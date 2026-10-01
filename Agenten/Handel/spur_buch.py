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
# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(os.path.abspath(__file__))
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
import pos_kennung  # noqa: E402


def _lade_modul(name):
    spec = spec_from_file_location(name, os.path.join(HANDEL, name + ".py"))
    modul = module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


ratschen = _lade_modul("ratschen")
risikovorfilter = _lade_modul("risikovorfilter")
risikostufe = _lade_modul("risikostufe")

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund", "pos_id"]

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
            "kraken_futures": "omnitrade_futures/weg"}.get(name)
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
    # (`risikovorfilter: true`). Geprueft wird das Risiko dieses Einstiegs -
    # das ist der Betrag, der bei einem Stop verloren ginge.
    if journal_pfad and w.get("risikovorfilter"):
        risiko = nominel * pct / 100.0
        ok, warum = risikovorfilter.pruefe(w, journal_pfad, z, risiko)
        if not ok:
            print("VORFILTER: %s" % warum)
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
                    weg=None, zusatz=None):
    """Stop und Ziel pruefen. Der G/V laeuft auf den NOMINALWERT.

    Die rohe Kursdifferenz war der Fehler vom 15.09.2026: bei BTC ein Faktor
    von Zehntausenden, der Erloes stand in Kurshoehe im Journal.
    """
    behalten = []
    for p in z.get("positionen", []):
        if nur is not None and p.get("inst") != nur:
            behalten.append(p)
            continue
        kurs = kurse.get(p["inst"])
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
        if p["seite"] == "long":
            if kurs <= p["stop"]:
                grund = "stop"
            elif kurs >= p["ziel"]:
                grund = "ziel"
        else:
            if kurs >= p["stop"]:
                grund = "stop"
            elif kurs <= p["ziel"]:
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
            try:
                pct = float(w.get("trailing_stop_prozent") or 0.0)
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
        print("AUSSTIEG (%s) %s %.6f G/V %+.2f USD"
              % (grund, p["inst"], kurs, gv))
        journal(journal_pfad, zeit=jetzt(),
                modus="live" if ist_live else "papier", aktion="verkauf",
                inst=p["inst"], seite=p["seite"], preis=pformat(kurs),
                # Die Kennung der Position, die hier endet (T-095). Ohne sie
                # waere diese Zeile bei zwei offenen Positionen im selben
                # Instrument nicht mehr zuzuordnen.
                pos_id=p.get("pos_id", ""),
                einsatz_usd="%.2f" % (p["nominal"] + gv),
                stop=pformat(p["stop"]), ziel=pformat(p["ziel"]),
                stop_pct="%.2f" % p["stop_pct"], grund=grund)

    z["positionen"] = behalten


# --- Das Lauf-Geruest ------------------------------------------------------

def zyklus(ordner, quelle, signal, modus, ereignis_name, ziel=None,
           zusatz_ausstieg=None, datenlage=None):
    """Ein Zyklus einer Spur. `quelle(w)`, `signal(daten, w)` kommen von ihr.

    `ziel(daten, w)` ist optional und liefert ein ZIEL ALS MARKTPUNKT (die
    IV-Wand) - dann steht im Buch nicht das R-Vielfache, sondern diese Linie.
    Ohne `ziel` bleibt es beim Vielfachen aus den Wachen.

    Reihenfolge: erst die Ratsche (Buch-Ruecklauf), dann Ausstiege, dann
    Einstiege. Bei `--vorschau` wird gerechnet und nichts geschrieben. `--live`
    laeuft ueber `sperren_live()` und `orderweg()` (Boerse aus der wachen);
    jede Sperre, die noch steht, laesst den Zyklus Papier handeln und nennt den
    Grund.
    """
    import ereignis

    wachen_pfad, zustand_pfad, journal_pfad = pfade(ordner)

    def _lauf():
        w = lade_wachen(wachen_pfad)
        z = lade_zustand(zustand_pfad)
        z.setdefault("positionen", [])

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

        if s.get("kill"):
            print("- Kill-Schwelle erreicht (%.2f USD Ruecklauf). Alles flach."
                  % ruecklauf)
            z["positionen"] = []
            schreibe_zustand(zustand_pfad, z)
            spiegeln(zustand_pfad, journal_pfad, z, w)
            return 0

        daten, kurse, fehler = quelle(w)
        for f in fehler:
            print("Uebersprungen (%s)" % f, file=sys.stderr)
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

        pruefe_ausstiege(z, kurse, w, journal_pfad, live=live, weg=weg,
                         zusatz=zusatz_ausstieg)
        if modus == "vorschau":
            for inst in sorted(daten):
                seite = signal(daten[inst], w)
                if seite:
                    linie = ziel(daten[inst], w) if ziel else None
                    print("Vorschau: Einstieg waere %s %s%s"
                          % (seite.upper(), inst,
                             ("  Ziel %.2f" % linie) if linie else ""))
            print("Vorschau: keine Dateien geschrieben.")
            return 0

        for inst in sorted(daten):
            seite = signal(daten[inst], w)
            if not seite:
                continue
            p = einstieg(z, inst, seite, kurse.get(inst), w, faktor,
                         w.get("grund", "moondev_bot"),
                         ziel_preis=(ziel(daten[inst], w) if ziel else None),
                         journal_pfad=journal_pfad, live=live, weg=weg)
            if p:
                print("EINSTIEG %s %s @ %.6f  Stop %.2f%%  Ziel %.6f  "
                      "Nominal %.2f USD"
                      % (seite.upper(), inst, p["einstieg"], p["stop_pct"],
                         p["ziel"], p["nominal"]))
                journal(journal_pfad, zeit=jetzt(),
                        modus="live" if live else "papier",
                        aktion="kauf", inst=inst, seite=seite,
                        # Die Kennung entsteht in `einstieg()` und steht in
                        # JEDER Zeile dieser Position (T-095).
                        pos_id=p["pos_id"],
                        preis=pformat(p["einstieg"]),
                        einsatz_usd="%.2f" % p["nominal"],
                        stop=pformat(p["stop"]), ziel=pformat(p["ziel"]),
                        stop_pct="%.2f" % p["stop_pct"],
                        # Der Grund stand hier fest auf "moondev_bot", obwohl
                        # jede Spur in ihrer wachen.json einen eigenen Namen
                        # fuehrt. Ein Feld, das immer dasselbe sagt, ist keine
                        # Auskunft. `_grund` setzt eine Spur, die etwas
                        # Genaueres weiss (die LLM-Spuren schreiben Aktion und
                        # Confidence hinein).
                        grund=(w.get("_grund") or w.get("grund")
                               or "moondev_bot"))

        z["datenlage"] = {"keine_daten": False, "kandidaten": len(daten),
                          "hinweis": datenlage() if datenlage else None}
        schreibe_zustand(zustand_pfad, z)
        spiegeln(zustand_pfad, journal_pfad, z, w)
        return 0

    with ereignis.lauf(ereignis_name):
        return _lauf()
