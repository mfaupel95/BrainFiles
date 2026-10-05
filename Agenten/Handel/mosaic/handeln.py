"""Mosaic-Spur: Mehr-Zeitrahmen-Preisaktion (Top-Down).

Bias und Ausfuehrung werden getrennt gerechnet, damit jede Schicht einzeln
messbar bleibt und spaeter optimiert werden kann, ohne die anderen zu
verfaelschen.

Signalkette (alles lange Kerzen = Aufwaertstrend):
1. 4H: die letzte Kerze ist gruen (close > open)  -> Aufwaerts-Bias.
2. 30M: ein Pullback hat eine Nachfragezone beruehrt und sich dort
       umgedreht; die Zone sind die Swing-Tiefs der letzten 20 Kerzen.
3. 5M: die letzte Kerze schliesst ueber dem letzten relevanten Swing-High
       des 5M-Charts (Break of Structure, BOS) im Sinne des Bias.

Ein Einstieg verlangt ALLE drei. Ausstieg: ATR-Stop, Ziel 2R.

Papier-Handel: handel_erlaubt=false. Keine Orders. Der Live-Pfad (--live)
stellt echte OKX-Spot-Orders erst, wenn die volle Sperrenkette offen ist
(handel_erlaubt, freigabe.erfuellt, Herzschlag, EV, Guthaben, Sitzung, kein
Demo-Modus). Siehe MOSAIC-LIVE-PLAN-OKX.md, Stufe A. Papier laeuft parallel
unveraendert weiter.

Aufruf:
 python handeln.py --vorschau   waere dran, ohne schreiben
 python handeln.py --papier     Papierlauf mit Journal
 python handeln.py --wachen     Grenzen als Momentaufnahme
 python handeln.py --live       echte OKX-Spot-Orders, wenn alle Sperren offen
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
# Reihenfolge zaehlt: sys.path.insert(0, ...) dreht die Liste um, deshalb
# rueckwaerts einfuegen. HIER muss ganz vorne stehen, sonst gewinnt
# scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, os.pardir, "Bus"),
          os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(          # Handel/, nicht der Spurenordner
    os.path.dirname(os.path.abspath(__file__)))
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
import pos_kennung
import mae                                         # noqa: E402
from signal_wechsel import ERLAEUT, zugelassen  # noqa: E402  # noqa: E402
import wachen_pruefung as wp  # noqa: E402
import ereignis  # noqa: E402
import okx_spot  # noqa: E402

# ratschen.py ueber den PFAD laden, nicht ueber sys.path: die Datei liegt
# eine Ebene hoeher und heisst wie kein Paket. Ein Import ueber sys.path
# haenge davon ab, wer vorher eingefuegt hat.
from importlib.util import spec_from_file_location, module_from_spec  # noqa: E402

_spec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "ratschen.py")
_spec = spec_from_file_location("ratschen", _spec_path)
ratschen = module_from_spec(_spec)
_spec.loader.exec_module(ratschen)

# Risikostufe (HANDEL_RISIKO): Faktor auf die Betraege, Suffix auf Zustand
# und Journal. OHNE die Variable aendert sich nichts (Faktor 1.0, kein
# Suffix) - das ist die Bedingung, unter der diese Umstellung in laufenden
# Handelscode darf. Ueber den PFAD geladen wie ratschen.py: die Spur hat ihren
# eigenen Ordner als sys.path[0], ein 'import risikostufe' haenge an der
# Reihenfolge der Eintraege.
from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec
_rs_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "risikostufe.py")
_rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
risikostufe = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(risikostufe)

WACHEN = os.path.join(HIER, "wachen.json")
ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand.json"))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal.csv"))

# Buch gegen BOERSE (T-207, 30.09.2026): hat jede Live-Position ihren
# Notausstieg noch, ist sie ueberhaupt noch da? Liegt im eigenen Ordner, ist
# aber NICHT von diesem Modul abhaengig - kein Ringimport.
import boersenabgleich  # noqa: E402

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "stop", "ziel", "stop_pct", "grund", "pos_id",
           # MAE/MFE seit 04.10.2026 (T-119). Die Spur hat die Spalten schon
           # seit 15.09.2026 im Kopf, schrieb aber nie Werte hinein - ohne
           # mae_pct ist kein Stop aus Daten begruendbar (strategie_metrics.
           # stop_from_mae). Siehe mae.py: der Richtungsfaktor gehoert dazu,
           # mosaic handelt auch short.
           "mfe_pct", "mae_pct", "haltetage"]

# Schreib-Flag: False in Tests, True im Betrieb.
SCHREIBEN = True

# --- Test-Seams -----------------------------------------------------------
# Kerzenquelle: None = echte Quelle (okx). Tests setzen eine Lambda.
kerzen_quelle = None
# Zeit-Quelle: None = utcnow. Tests koennen setzen.
zeit_quelle = None
# Live-Orderweg: Tests ersetzen die Funktionen, damit kein Test je eine echte
# Order an OKX stellt und kein Test ein Netzgewicht traegt. Der Betrieb laeuft
# auf den echten okx_spot-Funktionen.
op_kauf = okx_spot.markt_kauf
op_verkauf = okx_spot.markt_verkauf
op_stop = okx_spot.algo_stop_setzen
op_stop_stornieren = okx_spot.algo_stornieren
op_gefuellt = okx_spot.gefuellte_menge
# Freies Guthaben der Handelswaehrung (USDC seit 21.09.2026).
op_guthaben = okx_spot.guthaben_waehrung
live_kurs_quelle = okx_spot.letzter_kurs
live_menge_fuer = okx_spot.menge_fuer

# --- Boerse des Live-Wegs ---------------------------------------------------
#
# Die Strategie ist boersenunabhaengig; nur der Orderweg wechselt. Welcher gilt,
# steht in der wachen.json (`boerse`): "okx" (Standard, Spot gegen USDC) oder
# "kraken" (Spot gegen EUR). Beide Module stellen dieselben Funktionsnamen
# bereit - okx_spot.markt_kauf wie kraken_spot.markt_kauf -, sodass der Rest der
# Datei unveraendert bleibt.
#
# WARUM UEBER EINE BINDEFUNKTION und nicht ueber einen Import: Die Bindung haengt
# an der wachen.json, nicht am Programmstart. Tests ersetzen genau diese Namen
# (siehe Test-Seams oben) und keine echte Order wird je gestellt.
import kraken_spot  # noqa: E402

# OKX-FUTURES-WEG (05.10.2026, Auftrag Max: 'mosaic auf futures ... anbinden').
# Dritte Boerse neben okx_spot (SPOT) und kraken_spot (SPOT EUR). Sie stellt
# dieselben Funktionsnamen bereit, damit der Rest der Spur unveraendert bleibt
# - aber zwei ihrer Funktionen BEDEUTEN etwas anderes als bei den beiden
# anderen, und diese beiden Stellen sind der ganze Aufbau:
#   * `menge_fuer(inst, betrag, kurs)` rechnet bei Spot die MARGIN aus, bei
#     Futures den NOMINALWERT. Derselbe Aufruf, zwei Bedeutungen: 600 USD
#     heissen hier 600 USD Nennwert, nicht 600 USD Margin. Wer das verwechselt,
#     kauft eine 6-fache Wette mit der Margin eines Spottkaufes.
#   * `guthaben_waehrung` liefert die FREIE MARGIN, nicht den Spotbestand.
# Darum steht der Hebel in der wachen.json (`hebel`) und wird VOR der Order an
# das Modul uebergeben - niemals als Wert in der Wache, den der Code als
# Nominal missversteht.
import okx_perp  # noqa: E402

# EINE Paar-Tabelle fuer alle Kraken-Nutzer im Haus (EUR-Vorgabe, USDC waehlbar).
KRAKEN_PAARE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            os.pardir, "kraken_paare.py")
_kp_spec = spec_from_file_location("kraken_paare", KRAKEN_PAARE)
kraken_paare = module_from_spec(_kp_spec)
_kp_spec.loader.exec_module(kraken_paare)

# Modul je Boersenname. Alle drei stellen dieselben Funktionsnamen bereit.
# `okx_perp` traegt dieselbe Nummer wie die beiden Spot-Wege - siehe BOERSEN
# weiter unten fuer die Sonderfaelle des gehebelten Wegs.
BOERSEN = {"okx": okx_spot, "kraken": kraken_spot, "okx_perp": okx_perp}
# Kontowaehrung je Boerse, wenn die wachen.json keine nennt: Kraken handelt in
# EUR, OKX-Spot gegen USDC, OKX-Futures mit USDC-Margin.
WAEHRUNG_JE_BOERSE = {"kraken": "EUR", "okx": "USDC", "okx_perp": "USDC"}
# Wege, deren `menge_fuer` den NOMINALWERT statt der Margin rechnet. Nur an
# diesen drei Orten wird daraus der Einstiegsbetrag berechnet.
NOMINAL_STATT_MARGINAL = {"okx_perp"}

# Der Hebel des gehebelten Wegs. Er wird an `markt_kauf` uebergeben und dort
# VOR der Order gesetzt - als Modulwert, nicht aus einer Wache, damit kein
# Aufrufer einen gehebelten Kauf mit einem ungehebelten ausloest. Der Wert
# kommt in live_einstiege() aus der Wache (Feld `hebel`), mit diesem Deckel.
HEBEL = 6
HEBEL_MAX = 6

VENUE = okx_spot                       # aktives Boersenmodul (fuer die Sperren)
VENUE_NAME = "okx"                     # Name des aktiven Moduls
GUTHABEN_WAEHRUNG = "USDC"             # Kontowaehrung des Live-Wegs
MINDEST_GUTHABEN = 0.0                 # Tor aus der wachen.json


def boersen_liste(w):
    """Die Boersen des Live-Wegs in Vorrang-Reihenfolge.

    `boersen: ["kraken", "okx"]` = erste einsatzbereite gewinnt (Auftrag Max
    23.09.2026: "Mosaic live schalten, gerne auf okx und kraken"). Ein altes
    einzelnes `boerse` gilt weiter; fehlt beides, bleibt es bei OKX.
    """
    roh = w.get("boersen")
    if not roh:
        roh = [w.get("boerse")] if w.get("boerse") else ["okx"]
    namen = [str(x).strip().lower() for x in roh if str(x).strip()]
    unbekannt = [n for n in namen if n not in BOERSEN]
    if unbekannt:
        raise ValueError("unbekannte Boerse(n) in der wachen.json: %s "
                         "(bekannt: %s)" % (unbekannt, sorted(BOERSEN)))
    return namen


def _waehrung_fuer(w, name):
    je = w.get("guthaben_waehrung_je_boerse") or {}
    return str(je.get(name) or w.get("guthaben_waehrung")
               or WAEHRUNG_JE_BOERSE.get(name) or "USDC")


def _mindest_fuer(w, name):
    je = w.get("mindest_guthaben_je_boerse") or {}
    if name in je:
        return float(je[name] or 0)
    return float(w.get("mindest_guthaben",
                       w.get("mindest_guthaben_usdc",
                             w.get("mindest_guthaben_eur", 0))) or 0)


def _guthaben_roh(name, ccy):
    """Freies Guthaben einer Boerse - Naht fuer Tests (kein Netz im Test)."""
    return BOERSEN[name].guthaben_waehrung(ccy)


def boerse_bereit(name, w):
    """(bereit, grund) fuer eine Boerse: Schluessel, Demo, freies Guthaben.

    Das Guthaben wird hier NICHT abgefragt, wenn die Boerse schon an einem
    harten Tor scheitert - jede Abfrage ist ein signierter Aufruf.
    """
    modul = BOERSEN[name]
    if not modul.schluessel_vorhanden():
        return False, "%s-Schluessel nicht gesetzt" % name
    if modul.demo_modus():
        return False, "%s im Demo-Modus - keine echten Orders" % name
    noetig = _mindest_fuer(w, name)
    if not noetig:
        return True, None
    try:
        frei = _guthaben_roh(name, _waehrung_fuer(w, name))
    except Exception as e:                                        # noqa: BLE001
        return False, "%s: Guthaben nicht abrufbar (%s)" % (name, e)
    if frei < noetig:
        return False, "%s: nur %.2f %s frei, noetig %.2f" % (
            name, frei, _waehrung_fuer(w, name), noetig)
    return True, None


def venue_binden(w, name=None):
    """Live-Orderweg und Kontowaehrung an die wachen.json haengen.

    Ohne `name` gewinnt die ERSTE einsatzbereite Boerse der Liste; ist keine
    bereit, bleibt es bei der ersten (die Sperrenkette nennt dann deren Grund,
    damit im Bericht nicht drei Gruende stehen).
    """
    global VENUE, VENUE_NAME, GUTHABEN_WAEHRUNG, MINDEST_GUTHABEN
    global op_kauf, op_verkauf, op_stop, op_stop_stornieren, op_gefuellt
    global op_guthaben, live_kurs_quelle, live_menge_fuer
    namen = boersen_liste(w)
    gewaehlt = None
    if name:
        gewaehlt = str(name).strip().lower()
        if gewaehlt not in BOERSEN:
            raise ValueError("unbekannte Boerse: %s" % name)
    elif len(namen) == 1:
        # Eine Boerse: keine zusaetzliche Netzabfrage, altes Verhalten.
        gewaehlt = namen[0]
    else:
        # Mehrere Boersen: die erste einsatzbereite gewinnt. Ist keine bereit,
        # bleibt es bei der ersten - die Sperrenkette nennt dann deren Grund,
        # damit im Bericht nicht drei Gruende stehen.
        for kandidat in namen:
            bereit, _grund = boerse_bereit(kandidat, w)
            if bereit:
                gewaehlt = kandidat
                break
        if gewaehlt is None:
            gewaehlt = namen[0]
    modul = BOERSEN[gewaehlt]
    VENUE = modul
    VENUE_NAME = gewaehlt
    GUTHABEN_WAEHRUNG = _waehrung_fuer(w, gewaehlt)
    MINDEST_GUTHABEN = _mindest_fuer(w, gewaehlt)
    # Kraken-Quote aus der wachen: EUR ist Vorgabe, USDC waehlt man mit
    # "kraken_quote": "USDC" (kraken_paare.quote_aus_wachen). Ein unbekannter
    # Wert ist ein Fehler - ein Tippfehler darf nicht still in EUR ordern.
    if gewaehlt == "kraken" and hasattr(modul, "setze_quote"):
        modul.setze_quote(kraken_paare.quote_aus_wachen(w))
    op_kauf = modul.markt_kauf
    op_verkauf = modul.markt_verkauf
    op_stop = modul.algo_stop_setzen
    op_stop_stornieren = modul.algo_stornieren
    op_gefuellt = modul.gefuellte_menge
    op_guthaben = modul.guthaben_waehrung
    live_kurs_quelle = modul.letzter_kurs
    live_menge_fuer = modul.menge_fuer
    return gewaehlt


def venue_fuer_position(p, w):
    """Die Boerse EINER Position binden, wenn sie eine andere ist.

    Eine Position traegt seit dem 23.09.2026 ihr `boerse`-Feld; verkauft wird
    an der Boerse, an der sie liegt - nicht an der, die gerade gewaehlt ist.
    Rueckgabe: None (nichts zu tun, Seams bleiben unberuehrt), sonst der Name.
    Alte Positionen ohne Feld laufen weiter ueber die gebundene Boerse.
    """
    name = str(p.get("boerse") or "").strip().lower()
    if not name or name == VENUE_NAME:
        return None
    venue_binden(w, name)
    return name


# --- Zeit ------------------------------------------------------------------

def _jetzt():
    if zeit_quelle:
        return zeit_quelle()
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


# --- Dateien ---------------------------------------------------------------

def lade_wachen():
    with open(WACHEN, encoding="utf-8") as f:
        return risikostufe.skaliere(json.load(f))


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
    return atomar.lade_json(ZUSTAND, lambda: {"positionen": [], "modus": "papier", "letzter_lauf": None,
                "verluste_usd": 0.0})


def schreibe_zustand(z):
    z["letzter_lauf"] = _jetzt()
    atomar.schreibe_json(ZUSTAND, z)


def journal(**felder):
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    # Der Kopf der DATEI entscheidet, was geschrieben wird (T-095): ein
    # Altjournal ohne `pos_id` behaelt seine Spalten, die Kennung wird dann
    # NICHT geschrieben - sichtbar als Warnung, statt alle Spalten zu
    # verschieben (siehe pos_kennung.spalten).
    spalten = SPALTEN if neu else pos_kennung.spalten(JOURNAL, SPALTEN)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
        if neu:
            w.writeheader()
        w.writerow(felder)


def spiegeln(z, w):
    """Bedingung 4: Journal und Zustand ausser Haus.

    Erst schreiben, dann kopieren. Der Vermerk ist juenger als die Kopie:
    wechselt er, wird der Zustand einmal nachgezogen, damit auf derselbe
    Stand liegt. Ohne den Nachzug meldet spiegelstand.py JEDEM Zyklus eine
    Abweichung, dem sich der Spiegelstand aendert (Muster: swap/handeln.py).
    """
    ziel = w.get("journal_zweitziel")
    ok, info = wp.spiegele_journal([JOURNAL, ZUSTAND], ziel)
    wp.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand)
    if ok:
        wp.spiegele_journal([ZUSTAND], ziel)


# --- Kerzen ----------------------------------------------------------------

def lade_kerzen(inst, intervall, anzahl):
    """Kerzen laden: entweder Seam oder echte Quelle."""
    if kerzen_quelle:
        return kerzen_quelle(inst, intervall, anzahl)
    try:
        import okx
        return okx.kerzen(inst, intervall, anzahl)
    except Exception as e:
        print("Netzfehler: Kerzen fuer %s nicht abrufbar (%s)" % (inst, e),
              file=sys.stderr)
        return []


# --- Preisaktions-Bausteine -------------------------------------------------

def _schluss(k, idx):
    """Schlusskurs der Kerze idx (auch negativ = von hinten), oder None."""
    if idx < -len(k) or idx >= len(k):
        return None
    return k[idx][4]


def _kerze_gruen(k, idx):
    """True, wenn Kerze idx gruen ist (close > open). Auch negativ idx."""
    if idx < -len(k) or idx >= len(k):
        return False
    return k[idx][4] > k[idx][1]


def _swing_tiefs(k, fenster):
    """Swing-Tiefs (lokale Minima) der letzten Kerzen.

    Ein Index i ist ein Swing-Tief, wenn sein Low das Minimum in einem
    Fenster von `fenster` Kerzen LINKS (oder bis zum Rand) und RECHTS
    (oder bis zum Rand) ist. Der Fenster-Rand wird nicht ueberschritten -
    dadurch sind auch Tiefs nahe am Ende der Serie erlaubt, wo rechts
    weniger Kerzen liegen als `fenster` (fuer BOS-Referenzen wichtig).

    Monotone Reihen liefern so keine Tiefs (bewusst): ein Aufwaerts-Markt
    ohne Pullback hat keine Nachfragezone, an der ein Einstieg Sinn ergibt.
    """
    if len(k) < 3:
        return []
    ergebnis = []
    start = max(1, len(k) - 2 * fenster)
    for i in range(start, len(k) - 1):
        links_von = max(0, i - fenster + 1)
        links_bis = i + 1
        rechts_von = i
        rechts_bis = min(len(k), i + fenster)
        links = min(k[j][3] for j in range(links_von, links_bis))
        rechts = min(k[j][3] for j in range(rechts_von, rechts_bis))
        if k[i][3] <= links and k[i][3] <= rechts:
            ergebnis.append(i)
    return ergebnis


def _swing_hochs(k, fenster):
    """Swing-Hochs (lokale Maxima) der letzten Kerzen. Rand erlaubt."""
    if len(k) < 3:
        return []
    ergebnis = []
    start = max(1, len(k) - 2 * fenster)
    for i in range(start, len(k) - 1):
        links_von = max(0, i - fenster + 1)
        links_bis = i + 1
        rechts_von = i
        rechts_bis = min(len(k), i + fenster)
        links = max(k[j][2] for j in range(links_von, links_bis))
        rechts = max(k[j][2] for j in range(rechts_von, rechts_bis))
        if k[i][2] >= links and k[i][2] >= rechts:
            ergebnis.append(i)
    return ergebnis


def nachfrage_zone(k30, w):
    """Nachfragezone auf dem 30M-Chart.

    Zone = Preisspanne der Swing-Tiefs der letzten `zone_schwung_kerzen_30m`
    Kerzen. Damit ein Pullback-Zone-Setup Sinn macht, muss die Zone einen
    Puffer haben (untere < obere). Liefert (untere, obere) oder None, wenn
    die Kerzen fehlen.

    Der Fallback fuer Fehlanzeigen (keine echten Swing-Tiefs, z.B. weil der
    Pullback gerade erst unterwegs ist) nimmt die untere Haelfte der Spanne
    der letzten Fenster-Kerzen. So ist die Zone auch waehrend eines
    laufenden Pullbacks definiert, und `zone_beruehrt` entscheidet, ob der
    Kurs sie tatsaechlich erreicht hat.
    """
    fenster = int(w.get("zone_schwung_kerzen_30m", 20))
    if len(k30) < fenster:
        return None
    tiefs = _swing_tiefs(k30, fenster)
    if tiefs:
        werte = [k30[i][3] for i in tiefs]
        untere = min(werte)
        obere = max(werte)
        # Nur die untere Haelfte der Spanne ist echte Nachfrage. Degeneriert
        # die Spanne (ein einzelnes Tief, alle gleich), faellt der Code in
        # den Fenster-Fallback darunter - eine Zone ohne Puffer ist keine.
        if obere > untere:
            return (untere, untere + (obere - untere) * 0.5)
    # Fallback: die untere Haelfte der letzten Fenster-Kerzen-Lows
    werte = [k30[i][3] for i in range(max(0, len(k30) - fenster), len(k30))]
    if not werte:
        return None
    untere = min(werte)
    obere = max(werte)
    if obere <= untere:
        return None
    return (untere, untere + (obere - untere) * 0.5)


def zone_beruehrt(k30, w, zone):
    """True, wenn eine der letzten `zone_beruehrung_kerzen_30m` Kerzen die
    Zone beruehrt hat (Low <= obere Grenze und High >= untere)."""
    if not zone:
        return False
    fenster = int(w.get("zone_beruehrung_kerzen_30m", 30))
    untere, obere = zone
    for kerze in k30[-fenster:]:
        if kerze[3] <= obere and kerze[2] >= untere:
            return True
    return False


def letztes_relevantes_swing_hoch(k5, fenster):
    """Hoechstes Swing-Hoch der letzten `fenster` 5M-Kerzen (fuer BOS).

    Fallback, wenn die Serie keine echten Swing-Hochs hat (monoton, zu
    kurz): das hoechste High der letzten `fenster` Kerzen. Ein BOS ist
    dann der Schluss ueber dem hoechsten Punkt der jüngsten Vergangenheit
    - eine sinnvolle Referenz auch ohne lokale Maxima.
    """
    hochs = _swing_hochs(k5, fenster)
    if hochs:
        return max(k5[i][2] for i in hochs)
    if len(k5) <= fenster:
        return None
    return max(k5[j][2] for j in range(len(k5) - fenster, len(k5)))


def structure_shift(k5, w):
    """Structure Shift auf dem 5M-Chart (Break of Structure, BOS).

    True, wenn die letzte Kerze ueber dem hoechsten relevanten Swing-High
    der letzten `struktur_shift_kerzen_5m` Kerzen schliesst.
    """
    fenster = int(w.get("struktur_shift_kerzen_5m", 30))
    if len(k5) < fenster + 1:
        return False
    swing_hoch = letztes_relevantes_swing_hoch(k5[:-1], fenster)
    if swing_hoch is None:
        return False
    return k5[-1][4] > swing_hoch


def bias_4h(k4, w):
    """4H-Bias: letzte Kerze gruen -> long, rot -> short, sonst None."""
    if len(k4) < 1:
        return None
    if _kerze_gruen(k4, -1):
        mindest = int(w.get("trend_min_kerzen_4h", 0))
        if len(k4) < 1 + mindest:
            return None
        # Die letzten `mindest` 4H-Kerzen vor der letzten muessen gruen sein.
        for i in range(len(k4) - mindest - 1, len(k4) - 1):
            if not _kerze_gruen(k4, i):
                return None
        return "long"
    return "short"


def signal(k4, k30, k5, w):
    """Mosaic-Signal: 'long', 'short' oder None.

    Top-down: Bias (4H) -> Nachfragezone mit Beruehrung (30M) -> BOS (5M).
    Aktuell nur LONG verlangt: Bias long + Nachfragezone + BOS nach oben.
    SHORT ist absichtlich noch nicht verdrahtet, bis die Long-Seite belegt
    ist.
    """
    if bias_4h(k4, w) != "long":
        return None
    zone = nachfrage_zone(k30, w)
    if not zone or not zone_beruehrt(k30, w, zone):
        return None
    if not structure_shift(k5, w):
        return None
    return "long"


# --- Positionen ------------------------------------------------------------

def atr_abs(k, idx, n=14):
    """Einfacher ATR ueber die letzten Kerzen bis idx."""
    if idx < n:
        return None
    s = 0.0
    for j in range(idx - n + 1, idx + 1):
        s += k[j][2] - k[j][3]  # hoch - tief
    return s / n


def position_groesse(einstieg, stop_pct, w):
    """Risiko-normierte Groesse, gedeckelt und mit Drawdown-Ratsche."""
    stop_pct_eff = max(stop_pct, w.get("pflicht_stop_prozent_min", 5.0))
    stop_pct_eff = min(stop_pct_eff, w.get("pflicht_stop_prozent_max", 12.0))
    nominel = w["risiko_je_position_usd"] / (stop_pct_eff / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"])
    return nominel


def groessenfaktor(ruecklauf, w):
    """Drawdown-Ratsche aus ratschen.py - eine Umsetzung fuer alle Spuren."""
    return ratschen.groessenfaktor(ruecklauf, w)


def pruefe_einstieg(inst, k4, k30, k5, z, w, faktor):
    """Prueft, ob eine neue Position eroeffnet werden soll."""
    if not z.get("positionen"):
        z["positionen"] = []
    if len(z["positionen"]) >= w.get("max_offene_positionen", 4):
        return

    sig = signal(k4, k30, k5, w)
    if not sig:
        return

    einstieg = k5[-1][4]  # Schluss als Einstieg (Papier)
    atr = atr_abs(k5, len(k5) - 1, 14)
    if not atr or atr <= 0:
        return

    # Stop-Abstand aus dem ATR, in den Pflichtrahmen gezwungen.
    stop_pct = atr / einstieg * 100.0
    stop_pct = max(stop_pct, w.get("pflicht_stop_prozent_min", 5.0))
    stop_pct_eff = min(stop_pct, w.get("pflicht_stop_prozent_max", 12.0))

    vz = 1 if sig == "long" else -1
    abstand = einstieg * stop_pct_eff / 100.0
    ziel_r = w.get("ziel_r_vielfaches", 2.0)
    stop = einstieg - vz * abstand
    ziel = einstieg + vz * abstand * ziel_r

    nominel = w["risiko_je_position_usd"] / (stop_pct_eff / 100.0)
    nominel = min(nominel, w["max_pro_trade_usd"])
    nominel *= faktor
    if nominel <= 0:
        return

    # Die Kennung dieser Position (T-095): sie entsteht beim Einstieg und
    # steht in JEDER Zeile dieser Position (Kauf UND Verkauf).
    _p = {
        "inst": inst, "seite": sig, "einstieg": einstieg,
        "stop": stop, "ziel": ziel, "stop_pct": stop_pct_eff,
        "nominal": nominel, "eroeffnet_zeit": _jetzt(),
        "pos_id": pos_kennung.neu(_jetzt()),
    }
    # Signal-Wechsel-Gatter (03.10.2026, Auftrag Max "Erweitern"):
    # ein Einstieg nur bei Richtungswechsel fuer dieses Instrument.
    if zugelassen(z, w, inst, sig) is not ERLAEUT:
        return
    z["positionen"].append(_p)

    print("EINSTIEG %s %.6f Stop %.2f%% Ziel R=%.1f (%.6f) Nominal %.2f USD" % (
        sig.upper(), einstieg, stop_pct_eff, ziel_r, ziel, nominel))
    journal(zeit=_jetzt(), modus="papier", aktion="kauf", inst=inst,
            pos_id=_p["pos_id"], seite=sig,
            preis="%.6f" % einstieg, einsatz_usd="%.2f" % nominel,
            stop="%.6f" % stop, ziel="%.6f" % ziel,
            stop_pct="%.2f" % stop_pct_eff, grund="mosaic")


def nur_papier_verwerfen(z):
    """Alle PAPIER-Positionen aus dem Buch nehmen - Live-Positionen bleiben.

    Ein Papierlauf darf eine echte Position nicht aus dem Buch werfen: an der
    Boerse bliebe sie offen und im Buch waere sie verschwunden (genau das ist
    am 23.09.2026 mit der BTC-Position passiert). Eigene Funktion, damit die
    Regel pruefbar ist statt als Zeile in lauf() zu stehen.
    """
    z["positionen"] = [p for p in z.get("positionen", [])
                       if p.get("modus") == "live"]


def bueche_papier_altlasten_aus(z, w=None):
    """Papier-Positionen aus dem Buch buchen, die einen Live-Platz belegen.

    Anlass (25.09.2026): Das Buch fuehrt Live UND Papier in einer Liste; die
    Platzzahl von `live_einstiege` zaehlt beide. Eine Papier-Position, die
    keine Live-Order hat, nimmt damit einem echten Kauf den Platz weg - genau
    wie scanner/xperp am 21.09.2026.

    Sie wird als PAPIER-Verkauf mit Grund "buchbereinigung" gebucht (Kurs von
    der Boerse, deren Kerzen den Einstieg gebildet haben: der Papierzweig
    rechnet auf OKX) - an der Boerse gibt es nichts zu verkaufen, weil nie
    eine Order lief. Positionen mit modus=live und die drei live gefuehrten
    Kraken-Positionen bleiben unangetastet. Idempotent.
    """
    positionen = z.get("positionen") or []
    if not [p for p in positionen if p.get("modus") != "live"]:
        return 0
    behalten = []
    gebucht = 0
    for p in positionen:
        if p.get("modus") == "live":
            behalten.append(p)
            continue
        kurs = None
        try:
            import okx
            kurs = okx.letzter_kurs(p["inst"])
        except Exception as e:                                 # noqa: BLE001
            print("  Buchbereinigung %s: kein Kurs (%s)" % (p.get("inst"), e))
        if not kurs:
            print("  Buchbereinigung %s: kein Kurs - bleibt liegen"
                  % p.get("inst"), file=sys.stderr)
            behalten.append(p)
            continue
        einstieg = float(p.get("einstieg") or kurs)
        nominal = float(p.get("nominal") or 0.0)
        vz = 1 if p.get("seite") == "long" else -1
        gv = nominal * (float(kurs) - einstieg) / einstieg * vz
        erloes = nominal + gv
        print("  Buchbereinigung: %s %s (ohne Order) @ %.6f  G/V %+.2f USD"
              % (p.get("seite"), p.get("inst"), kurs, gv))
        journal(zeit=_jetzt(), modus="papier", aktion="verkauf",
                inst=p["inst"], pos_id=p.get("pos_id", ""),
                seite=p.get("seite", "long"),
                preis="%.6f" % kurs, einsatz_usd="%.2f" % erloes,
                stop="%.6f" % p.get("stop", 0.0),
                ziel="%.6f" % p.get("ziel", 0.0),
                stop_pct="%.2f" % p.get("stop_pct", 0.0),
                grund="buchbereinigung")
        gebucht += 1
    z["positionen"] = behalten
    return gebucht


def pruefe_ausstiege(z, k5, w, nur=None):
    """Bestehende Positionen auf Stop/Ziel pruefen.

    `k5` sind die Kerzen EINES Instruments (5M); `nur` grenzt die Pruefung
    darauf ein. Ohne die Einschraenkung wuerde jede offene Position gegen
    diesen einen Kurs geprueft (Befund 15.09.2026).
    """
    behalten = []
    uebersprungen = 0
    for p in z.get("positionen", []):
        # Eine Live-Position gehoert der BOERSE, nicht dem Papierzweig: dieser
        # Lauf verkauft nichts echt, er wuerde sie nur aus dem Buch nehmen.
        # Genau das ist am 23.09.2026 passiert - der Zyklus 19:33 lief Papier
        # (Freigabefenster-Luecke), buchte die ECHTE BTC-Position mit
        # grund=ziel aus, und an der Boerse blieb sie mit Stop stehen. Muster
        # wie xperp (bueche_geister_aus): stehen lassen und melden.
        if p.get("modus") == "live":
            behalten.append(p)
            # Gezaehlt wird nur, was zu DIESEM Aufruf gehoert: pruefe_ausstiege
            # laeuft je Instrument einmal ueber ALLE Positionen, ohne die
            # Einschraenkung meldete ein Zyklus dieselbe Live-Position dreimal
            # (Befund 25.09.2026, Zyklus 21 der Basis).
            if nur is None or p.get("inst") == nur:
                uebersprungen += 1
            continue
        if nur is not None and p.get("inst") != nur:
            behalten.append(p)
            continue

        kurs = k5[-1][4] if len(k5) else None
        if not kurs:
            behalten.append(p)
            continue
        # MAE/MFE ueber die LEBENDAUER messen (T-119), nicht erst beim
        # Ausstieg - sonst waere die Zahl der Ausstiegskurs selbst.
        mae.merke_extrem(p, kurs)

        grund = None
        vz = 1 if p["seite"] == "long" else -1
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

        if not grund:
            behalten.append(p)
            continue

        # G/V auf den NOMINALWERT: eine Kursbewegung von x Prozent bewegt
        # x Prozent des Nominalwerts (Befund 15.09.2026, siehe squeeze).
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        erloes = p["nominal"] + gv
        print("AUSSTIEG (%s) %.6f G/V %+.2f USD" % (grund, kurs, gv))
        journal(zeit=_jetzt(), modus="papier", aktion="verkauf", inst=p["inst"],
                pos_id=p.get("pos_id", ""),
                seite=p["seite"], preis="%.6f" % kurs,
                einsatz_usd="%.2f" % erloes, stop="%.6f" % p["stop"],
                ziel="%.6f" % p["ziel"], stop_pct="%.2f" % p["stop_pct"],
                grund=grund, **mae.felder(p))

    z["positionen"] = behalten
    # Kein print hier: der Aufrufer meldet EINMAL je Zyklus (siehe lauf()),
    # sonst steht die Zeile einmal je Instrument im Chat.
    return uebersprungen


# --- Live (Stufe A, OKX-Spot) ------------------------------------------------

# Sekunden ohne Bedienung, nach denen das Freigabefenster von selbst ablehnt.
# MUSS unter dauerlauf.TIMEOUT_S bleiben (700): ein Abbruch des Aufrufers
# toetet den Lauf mitten in der Wartezeit und reisst die Spiegelung mit
# (21.09.2026, scanner: Fenster 600 s > Abbruch 300 s).
FREIGABE_ZEITLIMIT_S = 600


def _live_grenze(w, name, ersatz):
    """Live-Grenze aus den Wachen: live_<name> bevorzugt, sonst <name>.

    Papier rechnet mit den Basis-Werten (max_pro_trade_usd 150, Max-Offen 4,
    max_gesamt_usd 600); der Live-Pfad darf eigene, kleinere Grenzen
    tragen (Stufe A: 10/5/200). So bleibt Papier aussagekraeftig, ohne die
    Live-Betraege mitzuschleifen.
    """
    return w.get("live_" + name, w.get(name, ersatz))


def nominal_aus_betrag(betrag, w):
    """Was `betrag` als NOMINALWERT bedeutet - oder als Margin.

    Der gehebelte Weg rechnet in Nominalwerten, die beiden Spot-Wege in
    Margin. Ohne diese Umrechnung wuerde ein 100-EUR-Betrag auf dem
    gehebelten Weg 100 EUR Nennwert kaufen - 100 statt 600 USD Wette bei
    6x. Der Betrag aus der Wache ist die MARGIN des Spuren-Gebots (so hat
    Max 'Mosaic 100' verstanden); auf dem gehebelten Weg wird er mit dem
    Hebel zum Nennwert.

    Rueckgabe: (nominal, hinweis oder None).
    """
    h = hebel_aus(w)
    if VENUE_NAME not in NOMINAL_STATT_MARGINAL:
        return betrag, None
    return betrag * h, ("Einsatz %.2f %s sind bei %dx Nennwert %.2f %s "
                        "(Margin x Hebel)"
                        % (betrag, GUTHABEN_WAEHRUNG, h, betrag * h,
                           GUTHABEN_WAEHRUNG))


def hebel_aus(w):
    """Der Hebel des gehebelten Wegs aus der Wache, gedeckelt.

    Vorgabe ist HEBEL, nicht die Wache: eine Spur, deren Wache keinen Hebel
    nennt, laeuft auf dem gehebelten Weg nie ungehebelt - das waere der
    schlimmste Fehler dieser Verdrahtung. Der Deckel HEBEL_MAX ist hart.
    """
    if VENUE_NAME not in BOERSEN or not hasattr(VENUE, "hebel_setzen"):
        return 1
    roh = w.get("hebel", HEBEL)
    try:
        h = float(roh)
    except (TypeError, ValueError):
        h = float(HEBEL)
    return max(1.0, min(float(HEBEL_MAX), h))


def betrag_gedeckelt(betrag, w):
    """Den Live-Einsatz auf das FREIE Guthaben deckeln (Gebuehr + etwas Luft).

    Auftrag Max 23.09.2026 ("Mosaic 100"): live_max_pro_trade_usd 50 -> 100.
    Ein 100-EUR-Kauf bei 88,56 EUR frei waere eine von Kraken abgelehnte Order -
    kein Handel, aber im Journal eine Fehlerzeile, die wie ein Defekt aussieht.
    Deshalb wird der Betrag vor dem Freigabefenster auf
    `frei * (1 - gebuehr - 0,2 %)` gedeckelt. Reicht auch das nicht fuer die
    Mindestmenge des Paares, lehnt live_menge_fuer ab - ein eigener
    Mindestbetrag ist dafuer nicht noetig.

    Rueckgabe: (betrag, hinweis oder None). Unlesbares Guthaben aendert NICHTS -
    die Sperrenkette hat denselben Abruf schon gemacht und dort gemeldet.
    """
    try:
        frei = op_guthaben(GUTHABEN_WAEHRUNG)
    except Exception as e:                                     # noqa: BLE001
        return betrag, "Guthaben nicht abrufbar (%s) - Einsatz unveraendert" % e
    if not frei:
        return betrag, ("kein freies %s-Guthaben gemeldet - Einsatz "
                        "unveraendert" % GUTHABEN_WAEHRUNG)
    geb = float(w.get("gebuehr_taker", 0.006) or 0.0)
    deckel = frei * (1 - geb - 0.002)
    if betrag <= deckel:
        return betrag, None
    return deckel, ("Einsatz %.2f -> %.2f EUR gedeckelt (%.2f EUR frei)"
                    % (betrag, deckel, frei))


def sitzung_da():
    """Sitzt jemand davor, der das Freigabefenster bedienen kann?

    Nur eine erste Huerde (isatty() taegt auch bei umgeleitetem stdin).
    Der tragende Schutz ist FREIGABE_ZEITLIMIT_S; MAXHIRN_ROUTINE=1 setzt der
    Wrapper einer geplanten Aufgabe = "hier sitzt niemand".
    """
    if os.environ.get("MAXHIRN_ROUTINE"):
        return False
    try:
        return bool(sys.stdin and sys.stdin.isatty())
    except (ValueError, AttributeError):
        return False


# Spur, unter der diese Datei im Dauerlauf und in freigabefenster.py steht.
SPUR = "mosaic"


def zeitfenster_offen():
    """Hat Max am Handy freigegeben (freigabefenster.py)?

    Das ist die ZWEITE Fassung von Punkt 3 der Handelsregeln. Am Bildschirm
    fragt freigabe.py je Einstieg; im Dauerbetrieb, wo niemand sitzen kann,
    ist das scharf geschaltete Zeitfenster die Freigabe - genau wie bei
    scanner und kraken. Best effort: fehlt das Modul oder wirft es, gilt
    *nicht* freigegeben. Im Zweifel Papier - ein Lesefehler darf nie zu einer
    Order fuehren.
    """
    try:
        # HANDEL statt str(HIER.parent): HIER und HANDEL sind in dieser
        # Datei STRINGS, keine Path-Objekte.
        sys.path.insert(0, HANDEL)
        import freigabefenster
        return bool(freigabefenster.lade(SPUR).offen())
    except Exception:                                   # noqa: BLE001
        return False


def freigabe_protokoll(vs, z, s):
    """Haelt fest, dass Einstiege ueber das Zeitfenster freigegeben wurden.

    Ohne diese Zeilen waere im Protokoll nicht zu sehen, welche Einstiege ohne
    Fenster am Bildschirm durchgingen. Best effort wie in freigabe.py: ein
    Schreibfehler darf den Einstieg nicht verhindern.
    """
    try:
        # HANDEL statt str(HIER.parent): HIER und HANDEL sind in dieser
        # Datei STRINGS, keine Path-Objekte.
        sys.path.insert(0, HANDEL)
        import freigabe
        for v in vs:
            freigabe.audit({
                "spur": SPUR, "ergebnis": "bestaetigt",
                "quelle": "zeitfenster", "modus": "live",
                "waehrung": GUTHABEN_WAEHRUNG, "inst": v.get("inst"),
                "einstieg": v.get("einstieg"), "stop": v.get("stop"),
                "ziel": v.get("ziel"), "stop_pct": v.get("stop_pct"),
                "gebunden": v.get("usd"),
                "gebunden_gesamt": sum(p["nominal"] for p in z["positionen"]),
                "offene_positionen": len(z["positionen"]),
                "ruecklauf_usd": s.get("ruecklauf_usd")})
    except Exception:                                   # noqa: BLE001
        pass


def hole_freigabe(vs, z, s):
    """Jeden Einstieg im Fenster bestaetigen lassen. Leer = abgelehnt - und
    abgelehnt heisst kein Einstieg. Faellt das Fenster aus, wird nicht
    gehandelt: ein Fehler darf nie zu einem ungefragten Kauf werden."""
    # HANDEL statt str(HIER.parent): HIER und HANDEL sind in dieser Datei
    # STRINGS (os.path.dirname), keine Path-Objekte - str(HIER.parent)
    # wirft AttributeError. Die Zeile kam mit dem Kraken-Umbau
    # (28e23b1, 21.09.2026) herein, stand VOR dem try und liess jede
    # Bildschirm-Freigabe mit 'Freigabefenster nicht verfuegbar' enden:
    # kein Einstieg, ohne dass es jemandem auffiel.
    sys.path.insert(0, HANDEL)
    try:
        import freigabe
    except Exception as e:  # noqa: BLE001
        print("  Freigabefenster nicht verfuegbar (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []
    bestand = {
        "gebunden": sum(p["nominal"] for p in z["positionen"]),
        "offene_positionen": len(z["positionen"]),
        "verlust_gesamt": s["ruecklauf_usd"],
    }
    try:
        return freigabe.bestaetige(vs, "mosaic", bestand,
                                   zeitlimit=FREIGABE_ZEITLIMIT_S)
    except Exception as e:  # noqa: BLE001
        print("  Freigabe abgebrochen (%s) - kein Einstieg." % e,
              file=sys.stderr)
        return []


def live_sperren(w, s):
    """Gruende, die --live auf Papier zurueckwerfen. Leer = scharf, aber
    weiterhin nur mit Freigabefenster je Einstieg."""
    g = []
    if not risikostufe.live_erlaubt():
        # Eine Risikostufe geht NIE live: ihre Betraege sind zum Messen da und
        # ihr Buch ist getrennt. Grund traegt keinen Wort 'Freigabefenster',
        # damit der Dauerlauf keine Fenster-Bitte stellt.
        g.append("Risikostufe %s: kein Live-Pfad in einer Stufe"
                 % risikostufe.stufe())
    if not w.get("handel_erlaubt"):
        g.append("wachen.json handel_erlaubt=false")
    if not VENUE.schluessel_vorhanden():
        g.append("%s-Schluessel nicht gesetzt" % VENUE.__name__)
    if not s["freigabe_erfuellt"]:
        g.append("freigabe.erfuellt=false (Bedingung 1)")
    if not s["herzschlag_frisch"]:
        g.append("Herzschlag alt (Bedingung 3)")
    if s["ev_negativ"]:
        g.append("rollierender EV %s < 0 (Bedingung 5)"
                 % ("%.3f USD" % s["rollierender_ev"]
                    if s["rollierender_ev"] is not None else "n/a"))
    if not w.get("journal_zweitziel"):
        g.append("journal_zweitziel nicht gesetzt (Bedingung 4)")
    if VENUE.demo_modus():
        g.append("%s im Demo-Modus - keine echten Orders" % VENUE.__name__)
    # Punkt 3 der Handelsregeln in ZWEI Fassungen: am Bildschirm das
    # Freigabefenster, im Dauerbetrieb das Zeitfenster (AUTO_FREIGABE oder
    # /ja am Handy). Eine muss offen sein. Bis zum 21.09.2026 fehlte hier die
    # zweite Fassung: unter MAXHIRN_ROUTINE=1 ist sitzung_da() immer False,
    # also lief mosaic in JEDEM Zyklus Papier - waehrend der Dauerlauf wegen
    # genau dieser Zeile ein Freigabefenster nach dem anderen oeffnete.
    if not sitzung_da() and not zeitfenster_offen():
        g.append("Freigabefenster nicht offen - keine Sitzung am "
                 "Bildschirm und kein Zeitfenster (Handelsregeln Punkt 3)")
    noetig = MINDEST_GUTHABEN
    if noetig and VENUE.schluessel_vorhanden():
        try:
            frei = op_guthaben(GUTHABEN_WAEHRUNG)
            if frei < noetig:
                # Die BOERSE NENNEN und die uebrigen der Liste mitnennen.
                # "nur 0,71 EUR frei, noetig 60.00" allein liest sich wie die
                # andere Boerse der Liste (Kraken notiert in EUR, OKX in USDC) -
                # genau daran ist die Meldung am 25.09.2026 missverstanden
                # worden, obwohl Kraken gefragt war und OKX ebenfalls leer.
                text = "%s: nur %.2f %s frei, noetig %.2f" % (
                    VENUE_NAME, frei, GUTHABEN_WAEHRUNG, noetig)
                weitere = [n for n in boersen_liste(w) if n != VENUE_NAME]
                if weitere:
                    teile = []
                    for n in weitere:
                        _bereit, grund = boerse_bereit(n, w)
                        teile.append(grund or ("%s einsatzbereit" % n))
                    text += " - dazu " + " und ".join(teile)
                g.append(text)
        except Exception as e:  # noqa: BLE001
            g.append("Guthaben nicht abrufbar (%s)" % e)
    return g


def _kurs_live(inst):
    """Lebender Kurs fuer den Live-Pfad (nicht der 5M-Schluss)."""
    return float(live_kurs_quelle(inst))


def live_ausstiege(z, w):
    """Live-Positionen auf Stop/Ziel pruefen und echt verkaufen.

    Papier-Positionen im selben Buch bleiben unberuehrt (modus=['papier']).
    Der Boersen-Stop wird zuerst storniert, dann beim aktuellen Kurs
    verkauft. Schlaegt der Verkauf fehl, bleibt die Position im Buch.
    """
    behalten = []
    wechsel = False
    for p in z["positionen"]:
        if p.get("modus") != "live":
            behalten.append(p)
            continue
        # Liegt die Position an einer ANDEREN Boerse, wird fuer sie umgebunden
        # (beide Boersen sind seit 23.09.2026 konfigurierbar).
        if venue_fuer_position(p, w):
            wechsel = True
        try:
            kurs = _kurs_live(p["inst"])
        except Exception as e:  # noqa: BLE001
            print("  Kursausfall fuer %s (%s) - Position bleibt" % (p["inst"], e),
                  file=sys.stderr)
            behalten.append(p)
            continue
        mae.merke_extrem(p, kurs)
        grund = None
        vz = 1 if p["seite"] == "long" else -1
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
        if not grund:
            behalten.append(p)
            continue
        # Boersen-Stop zuerst weg.
        if p.get("stop_algo_id"):
            try:
                op_stop_stornieren(p["inst"], p["stop_algo_id"])
            except Exception as e:  # noqa: BLE001
                print("  Stop-Algo %s nicht stornierbar: %s"
                      % (p["stop_algo_id"], e), file=sys.stderr)
        try:
            op_verkauf(p["inst"], p["menge"])
        except Exception as e:  # noqa: BLE001
            print("  Verkauf %s fehlgeschlagen: %s" % (p["inst"], e),
                  file=sys.stderr)
            journal(zeit=_jetzt(), modus="live", aktion="fehler",
                    inst=p["inst"], seite=p["seite"], preis="", einsatz_usd="",
                    stop="", ziel="", stop_pct="",
                    grund="verkauf fehlgeschlagen: %s" % e)
            behalten.append(p)
            continue
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        erloes = p["nominal"] + gv
        print("  AUSSTIEG (%s): %s @ %.6g  G/V %+.2f USD"
              % (grund, p["inst"], kurs, gv))
        journal(zeit=_jetzt(), modus="live", aktion="verkauf", inst=p["inst"],
                pos_id=p.get("pos_id", ""),
                seite=p["seite"], preis="%.6f" % kurs,
                einsatz_usd="%.2f" % erloes, stop="%.6f" % p["stop"],
                ziel="%.6f" % p["ziel"], stop_pct="%.2f" % p["stop_pct"],
                grund=grund, **mae.felder(p))
    z["positionen"] = behalten
    if wechsel:
        # Standardwahl der Spur wiederherstellen (Seams/Einstiege danach).
        venue_binden(w)


def flach_stellen_live(z, w, grund):
    """Alle Live-Positionen sofort echt verkaufen - Notausstieg fuer
    Kill-Switch und alten Herzschlag. Papier-Positionen bleiben stehen."""
    behalten = []
    wechsel = False
    for p in z["positionen"]:
        if p.get("modus") != "live":
            behalten.append(p)
            continue
        if venue_fuer_position(p, w):
            wechsel = True
        try:
            kurs = _kurs_live(p["inst"])
        except Exception as e:  # noqa: BLE001
            print("  Kursausfall %s (%s) - bleibt im Buch" % (p["inst"], e),
                  file=sys.stderr)
            behalten.append(p)
            continue
        if p.get("stop_algo_id"):
            try:
                op_stop_stornieren(p["inst"], p["stop_algo_id"])
            except Exception as e2:  # noqa: BLE001
                print("  Stop-Algo %s nicht stornierbar: %s"
                      % (p["stop_algo_id"], e2), file=sys.stderr)
        try:
            op_verkauf(p["inst"], p["menge"])
        except Exception as e:  # noqa: BLE001
            print("  Verkauf %s fehlgeschlagen (%s) - bleibt im Buch"
                  % (p["inst"], e), file=sys.stderr)
            behalten.append(p)
            continue
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"]
        print("  NOTAUS (%s): %s @ %.6g  G/V %+.2f USD"
              % (grund, p["inst"], kurs, gv))
        journal(zeit=_jetzt(), modus="live", aktion="verkauf", inst=p["inst"],
                pos_id=p.get("pos_id", ""),
                seite=p["seite"], preis="%.6f" % kurs,
                einsatz_usd="%.2f" % (p["nominal"] + gv),
                stop="%.6f" % p["stop"], ziel="%.6f" % p["ziel"],
                stop_pct="%.2f" % p["stop_pct"], grund=grund)
    z["positionen"] = behalten
    if wechsel:
        venue_binden(w)


def live_einstiege(z, w, s):
    """Echte OKX-Spot-Einstiege nach dem Mosaic-Signal.

    Jeder Einstieg laeuft durch das Freigabefenster; erst danach wird gekauft
    und der Boersen-Stop (conditional order) gelegt. Schlaegt der Stop fehl,
    wird zurueckverkauft (Muster kraken/handeln.py) - nie eine Position ohne
    Bewachung im Buch lassen.
    """
    betrag = float(_live_grenze(w, "max_pro_trade_usd", 10.0))
    betrag, deckel_hinweis = betrag_gedeckelt(betrag, w)
    if deckel_hinweis:
        print("  " + deckel_hinweis)
    # Der gehebelte Weg rechnet in Nominalwerten (Margin x Hebel), die beiden
    # Spot-Wege in Margin. Der GEBOCHENE Betrag ist die Grenze in beiden
    # Faellen - deshalb wird hier nur der Betrag an `menge_fuer` gereicht,
    # der gebundene Wert im Buch bleibt der Betrag, nicht der Nominalwert.
    nominal, nominal_hinweis = nominal_aus_betrag(betrag, w)
    if nominal_hinweis:
        print("  " + nominal_hinweis)
    maxoffen = int(_live_grenze(w, "max_offene_positionen", 4))
    maxges = float(_live_grenze(w, "max_gesamt_usd", 200.0))
    ziel_r = float(w.get("ziel_r_vielfaches", 2.0))
    gebunden = sum(p["nominal"] for p in z["positionen"])

    for inst in w.get("instrumente", []):
        if len(z["positionen"]) >= maxoffen:
            break
        if any(p["inst"] == inst for p in z["positionen"]):
            continue
        k4 = lade_kerzen(inst, w.get("kerzen_takt_4h", "4H"),
                         w.get("mindest_kerzen", 300))
        k30 = lade_kerzen(inst, w.get("kerzen_takt_30m", "30m"),
                          w.get("mindest_kerzen", 300))
        k5 = lade_kerzen(inst, w.get("kerzen_takt_5m", "5m"),
                         w.get("mindest_kerzen", 300))
        if not k4 or not k30 or not k5:
            continue
        if signal(k4, k30, k5, w) != "long":
            continue
        try:
            kurs = _kurs_live(inst)
        except Exception as e:  # noqa: BLE001
            print("  Kursausfall %s (%s) - kein Einstieg" % (inst, e),
                  file=sys.stderr)
            continue
        atr = atr_abs(k5, len(k5) - 1, 14)
        if not atr or atr <= 0:
            continue
        stop_pct = atr / kurs * 100.0
        stop_pct = max(stop_pct, w.get("pflicht_stop_prozent_min", 5.0))
        stop_pct = min(stop_pct, w.get("pflicht_stop_prozent_max", 12.0))
        abstand = kurs * stop_pct / 100.0
        stop = kurs - abstand
        ziel = kurs + abstand * ziel_r
        if gebunden + betrag > maxges:
            continue
        # Der Pflicht-Stop muss VOR der Liquidationsmarke liegen - auf dem
        # gehebelten Weg ist das eine zusaetzliche Pruefung, die es bei Spot
        # nicht gibt. Sie laeuft VOR dem Kauf, nicht danach: ein verweigerter
        # Einstieg kostet nichts, eine Position ohne wirksamen Stop kostet die
        # Margin.
        if hasattr(VENUE, "stop_vor_liq"):
            h = hebel_aus(w)
            stop_ok, stop_grund = VENUE.stop_vor_liq(stop, kurs, h, "long")
            if not stop_ok:
                print("  -- %-9s uebersprungen: %s" % (inst, stop_grund))
                continue
        menge, fehler = live_menge_fuer(inst, nominal, kurs)
        if fehler:
            print("  -- %-9s uebersprungen: %s" % (inst, fehler))
            continue
        vorschlag = [{"inst": inst, "einstieg": kurs,
                      "stop_pct": stop_pct, "stop": stop, "ziel": ziel,
                      "cr": ziel_r, "usd": betrag}]
        if not sitzung_da() and zeitfenster_offen():
            # Kein Bildschirm, aber ein offenes Zeitfenster. Es wurde beim
            # Sperrenpruefen schon geprueft; hier noch einmal, weil dazwischen
            # Netzabfragen liegen und das Fenster in der Zeit zulaufen kann.
            try:
                import freigabefenster
                stand = freigabefenster.lade(SPUR).text()
            except Exception:                           # noqa: BLE001
                stand = "offen"
            print("  Freigabe ueber das Zeitfenster (%s) - Einstieg %s ohne "
                  "Fenster am Bildschirm." % (stand, inst))
            freigabe_protokoll(vorschlag, z, s)
            vs = vorschlag
        else:
            vs = hole_freigabe(vorschlag, z, s)
        if not vs:
            print("  Freigabe abgelehnt/leer - kein Einstieg %s" % inst)
            continue
        try:
            if hasattr(VENUE, "hebel_setzen"):
                ord_id = op_kauf(inst, menge, hebel_aus(w))
            else:
                ord_id = op_kauf(inst, menge)
            gefuellt = op_gefuellt(inst, ord_id)
            menge = gefuellt if gefuellt and gefuellt > 0 else menge
            algo_id = None
            try:
                algo_id = op_stop(inst, menge, "long", stop)
            except Exception as e:  # noqa: BLE001
                print("  Stop fuer %s fehlgeschlagen (%s) - zurueckverkauft"
                      % (inst, e), file=sys.stderr)
                try:
                    op_verkauf(inst, menge)
                except Exception as e2:  # noqa: BLE001
                    stop_fehlt = True
                    journal(zeit=_jetzt(), modus="live", aktion="fehler",
                            inst=inst, seite="long", preis="", einsatz_usd="",
                            stop="", ziel="", stop_pct="",
                            grund="stop fehlgeschlagen (%s) UND Rueckverkauf "
                                  "fehlgeschlagen (%s) - Position ohne Stop "
                                  "offen" % (e, e2))
                else:
                    journal(zeit=_jetzt(), modus="live", aktion="fehler",
                            inst=inst, seite="long", preis="", einsatz_usd="",
                            stop="", ziel="", stop_pct="",
                            grund="stop fehlgeschlagen (%s) - zurueckverkauft" % e)
                    continue
        except Exception as e:  # noqa: BLE001
            print("  Kauf %s fehlgeschlagen: %s" % (inst, e), file=sys.stderr)
            # Ins Journal, nicht nur auf stderr: ein gescheiterter Live-Kauf
            # hinterlaesst sonst KEINE Spur (der Dauerlauf meldet die Spur als
            # "ok", stderr wird verworfen), und niemand kann spaeter sagen,
            # warum kein Einstieg kam. Der Waechter mosaic-live-wache meldet
            # genau diese Zeile (Auftrag Max, 21.09.2026: "erste order melden").
            journal(zeit=_jetzt(), modus="live", aktion="fehler", inst=inst,
                    seite="long", preis="", einsatz_usd="", stop="", ziel="",
                    stop_pct="", grund="kauf fehlgeschlagen: %s" % e)
            continue
        nominal = menge * kurs
        _p = {
            "inst": inst, "seite": "long", "einstieg": kurs, "stop": stop,
            "ziel": ziel, "stop_pct": stop_pct, "nominal": nominal,
            "menge": menge, "kauf_ord_id": ord_id,
            "stop_algo_id": algo_id, "modus": "live",
            "boerse": VENUE_NAME,
            "boersen_stop_fehlt": algo_id is None,
            "eroeffnet_zeit": _jetzt(),
            "pos_id": pos_kennung.neu(_jetzt()),
        }
        # Signal-Wechsel-Gatter, Livezweig: dieselbe Regel wie im
        # Papierzweig. Es steht VOR dem Buchen, damit die Anzeige
        # "EINSTIEG" nicht von einer gebliebenen Position spricht.
        if zugelassen(z, w, inst, "long") is not ERLAEUT:
            return
        z["positionen"].append(_p)
        gebunden += betrag
        print("  AUF %-9s @ %.6g Stop %.6g (-%.1f%%) Ziel %.6g  %.2f USDC%s"
              % (inst, kurs, stop, stop_pct, ziel, betrag,
                 "  [KEIN BOERSEN-STOP - unbewacht]" if algo_id is None else ""))
        journal(zeit=_jetzt(), modus="live", aktion="kauf", inst=inst,
                pos_id=_p["pos_id"],
                seite="long", preis="%.6f" % kurs,
                einsatz_usd="%.2f" % nominal, stop="%.6f" % stop,
                ziel="%.6f" % ziel, stop_pct="%.2f" % stop_pct,
                grund="mosaic")


# --- Laeufe -----------------------------------------------------------------

def lauf(modus):
    """Ein Zyklus der Mosaic-Spur."""
    w = lade_wachen()
    z = lade_zustand()
    z.setdefault("positionen", [])
    # Boerse des Live-Wegs aus der wachen.json (okx oder kraken) - VOR jeder
    # Sperrenpruefung, damit Schluessel-, Demo- und Guthaben-Tor die richtige
    # Boerse fragen.
    venue_binden(w)

    if modus == "wachen":
        print(json.dumps(wp.lage(w, JOURNAL, z), indent=2, ensure_ascii=False))
        return

    # Drawdown-Ratsche
    s = wp.lage(w, JOURNAL, z)
    ruecklauf = s.get("ruecklauf_usd", 0.0)
    faktor = groessenfaktor(ruecklauf, w)

    # Live-Sperrenkette: --live wird nur scharf, wenn nichts sperrt. Sonst
    # laeuft dieser Zyklus Papier (Muster kraken/handeln.py). live bleibt
    # False fuer alle papier/vorschau/wachen-Modi.
    live = False
    if modus == "live":
        g = live_sperren(w, s)
        if g:
            print("--live angefordert, aber gesperrt: " + "; ".join(g))
            print("-> es wird Papier gehandelt.")
        else:
            live = True

    if s.get("kill"):
        print("- Kill-Schwelle erreicht (%.2f USD Ruecklauf). Alles flach." % ruecklauf)
        if live:
            flach_stellen_live(z, w, "kill_switch")
        else:
            # Nur PAPIER-Positionen verwerfen: eine Live-Position gehoert der
            # Boerse, ein Papierlauf darf sie nicht aus dem Buch werfen (siehe
            # pruefe_ausstiege).
            nur_papier_verwerfen(z)
        schreibe_zustand(z)
        spiegeln(z, w)
        return

    # Bedingung 3 - Herzschlag alt: Live-Positionen glatt stellen, dieser Lauf
    # handelt nicht mehr. (Papier wird von wachen_pruefung ueber den
    # Herzschlag nicht automatisch flachgestellt - das ist die Live-Regel.)
    if live and not s["herzschlag_frisch"]:
        print("- Herzschlag alt (%s min > %d) -> Live-Notausstieg, kein Handel "
              "dieser Lauf -"
              % ("?" if s["herzschlag_alter_min"] is None
                 else "%.0f" % s["herzschlag_alter_min"],
                 w.get("herzschlag_max_minuten", 180)))
        flach_stellen_live(z, w, "herzschlag_alt")
        schreibe_zustand(z)
        spiegeln(z, w)
        return

    if modus == "vorschau":
        print("Vorschau: keine Dateien geschrieben.")
        print("Live waere gesperrt durch: %s"
              % ("; ".join(live_sperren(w, s)) or "nichts"))
        return

    # Buch gegen BOERSE (T-207, 30.09.2026): hat jede Live-Position ihren
    # Notausstieg noch, ist sie ueberhaupt noch da?
    #
    # Der Abgleich steht ABSICHTLICH ausserhalb von `if live:` und laeuft in
    # JEDEM Zyklus der Basis. Grund (der eigentliche Befund): die drei Kraken-
    # Stops der Spur standen am 30.09.2026 auf 'canceled', waehrend das Buch
    # weiter 'boersen_stop_fehlt: false' meldete - und der Live-Zweig laeuft
    # nur, wenn die ganze Sperrenkette offen ist. Genau dann, wenn eine Sperre
    # zu ist (kein Guthaben in der Waehrung, kein Fenster, Herzschlag), waeren
    # die echten Positionen ungeschuetzt und niemand saehe es.
    #
    # Angefasst werden ausschliesslich Positionen mit modus == "live": ein
    # Papierlauf bucht keine echte Position aus (23.09.2026). Und nur die
    # BASIS handelt auf der Boerse - die Stufen mittel/hoch fuehren Kopien des
    # Buchs und duerfen keine Order auf dieselben Positionen setzen.
    if risikostufe.ist_basis():
        try:
            _bs = boersenabgleich.pruefe(
                z, anwenden=True, journal=journal,
                standard=boersen_liste(w)[0],
                quote=kraken_paare.quote_aus_wachen(w))
            # Immer eine Zeile, auch wenn alles in Ordnung ist: ein stiller
            # Abgleich ist von einem, der gar nicht lief, nicht zu
            # unterscheiden (Lehre aus der treiberlosen Zeit der Spur-Wachen).
            print("  Boersen-Abgleich: %d Live-Position(en), Stop wirksam %d, "
                  "nachgesetzt %d, ausgebucht %d, Waisen %d, unklar %d, "
                  "ohne Stop %d"
                  % (_bs["geprueft"], _bs["ok"], _bs["nachgesetzt"],
                     _bs["ausgebucht"], _bs["waisen"], _bs["unklar"],
                     _bs["fehlt_weiter"]))
            if _bs["unklar"] or _bs["fehlt_weiter"] or _bs["weg"] > _bs["ausgebucht"]:
                print("  Boersen-Abgleich: HANDLUNGSBEDARF - %d ohne wirksamen "
                      "Stop, %d unklar, %d weggelaufen ohne Buchung"
                      % (_bs["fehlt_weiter"], _bs["unklar"],
                         _bs["weg"] - _bs["ausgebucht"]))
        except Exception as e:                                 # noqa: BLE001
            # Ein Fehler im Abgleich darf den Zyklus nicht abwuergen: der
            # Ausstiegspfad danach ist wichtiger als die Buchhaltung.
            print("  Boersen-Abgleich nicht moeglich (%s) - Buch unveraendert"
                  % e)

    if live:
        # Erst aufraeumen, dann handeln (Muster kraken/scanner): eine
        # Papier-Position im Buch belegt sonst einen der Live-Plaetze.
        n_alt = bueche_papier_altlasten_aus(z, w)
        if n_alt:
            print("  %d Papier-Altlast(en) aus dem Live-Buch gebucht" % n_alt)
        # Echte Orders. Ausstiege zuerst (ein Stop muss greifen, auch wenn
        # niemand davorsitzt), dann Einstiege mit Freigabefenster je Stueck.
        # Der Boersen-Abgleich ist oben schon gelaufen - eine Position, die
        # ihr Boersen-Stop geschlossen hat, steht hier nicht mehr im Buch.
        live_ausstiege(z, w)
        live_einstiege(z, w, s)
    else:
        # Papier-Zyklus: Kerzen fuer alle Instrumente laden (drei Zeitrahmen
        # je Instrument), Ausstiege vor Einstiegen.
        uebersprungen = 0
        # Geprueft wird der PLAN plus alles, was im Buch steht - sonst wird eine
        # Position unsichtbar, sobald ihr Instrument aus der Liste genommen wird
        # (dieselbe Falle wie in den vier Indikatorspuren am 29.09.2026: sie
        # wurden nie wieder angesehen, nie geschlossen und belegten die Plaetze).
        # Eingestiegen wird weiter NUR auf den Plan-Instrumenten.
        plan = wp.plan_instrumente(w)
        verwaist = wp.verwaiste_instrumente(w, z)
        if verwaist:
            print("  Verwaiste Instrumente (nicht mehr im Plan, Position bleibt "
                  "im Buch): %s" % ", ".join(verwaist), file=sys.stderr)
        for inst in wp.pruef_instrumente(w, z):
            k4 = lade_kerzen(inst, w.get("kerzen_takt_4h", "4H"),
                             w.get("mindest_kerzen", 300))
            k30 = lade_kerzen(inst, w.get("kerzen_takt_30m", "30m"),
                              w.get("mindest_kerzen", 300))
            k5 = lade_kerzen(inst, w.get("kerzen_takt_5m", "5m"),
                             w.get("mindest_kerzen", 300))
            if not k4 or not k30 or not k5:
                print("Uebersprungen (%s): keine Kerzen" % inst, file=sys.stderr)
                continue

            # Ausstiege zuerst
            bestehend = [p for p in z["positionen"] if p["inst"] == inst]
            if bestehend:
                z["positionen"] = [p for p in z["positionen"] if p["inst"] != inst]
                z["positionen"].extend(bestehend)
                uebersprungen += pruefe_ausstiege(z, k5, w, nur=inst)

            # Neue Einstiege
            if inst in plan:
                pruefe_einstieg(inst, k4, k30, k5, z, w, faktor)

        if uebersprungen:
            print("  %d Live-Position(en) bleiben stehen - der Papierzweig "
                  "verkauft sie nicht (nur der Live-Lauf schliesst sie)."
                  % uebersprungen)

    schreibe_zustand(z)
    spiegeln(z, w)


# --- Main -------------------------------------------------------------------

def main():
    # Meldet sich am Bus wie jede andere Spur im Dauerlauf (Muster
    # kraken/handeln.py). Ein toter Bus bricht den Lauf nicht ab.
    with ereignis.lauf("handel/mosaic"):
        return _main()


def _main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vorschau", action="store_const", const="vorschau",
                    dest="modus", help="was waere dran, ohne schreiben")
    ap.add_argument("--papier", action="store_const", const="papier", dest="modus")
    ap.add_argument("--live", action="store_const", const="live", dest="modus")
    ap.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    ap.set_defaults(modus="vorschau")
    a = ap.parse_args()

    # --live wird von lauf() ueber die Sperrenkette entschieden: bei einem
    # gesperrten Zustand wird Papier gehandelt und der Grund gesagt.
    lauf(a.modus)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())