"""Die Spiegel-Spur: was waere, wenn man den Wallets des Feeds nachkauft?

Sie kopiert **nichts** und sie kauft **nichts**. Sie fuehrt ein Papierbuch:
Jeder Kauf eines verfolgten Wallets wird zu einer Buchzeile mit Slippage,
Gebuehr und eigenen Ausstiegsgrenzen. Was am Ende uebrig bleibt, ist die
Antwort auf die Frage, ob Nachahmen nach Kosten traegt - die einzige Frage,
die vor einem echten Kauf beantwortet sein muss.

Kein Orderpfad
--------------
Der Schreibbefehl des CLI (`swap`) wird beim Import stillgelegt: Ein Fehler in
der Steuerung kann aus diesem Prozess heraus kein Geld bewegen. `--live`
verweigert mit genau einem Grund, in dem das Wort Freigabefenster NICHT
vorkommt - so fragt der Dauerlauf keine Freigabe an, die nichts oeffnen kann.

Kosten, ehrlich gerechnet
-------------------------
Slippage und Gebuehr stehen in wachen.json und wirken zweimal: beim Kauf
teurer, beim Verkauf billiger. Ein Papierbuch mit glatten Kursen ist eine
Wunschrechnung, und genau daran scheitern Nachahmer in der Wirklichkeit.

Ablehnungen werden protokolliert
-------------------------------
Das Journal haelt nur, was gebucht wurde: 107 geschlossene Runden im
September 2026, und aus ihnen war nur noch abzuleiten, in welchem Band das
Buch getragen hat. WIE VIELE Kandidaten an welchem Tor haengen blieben, stand
nirgends - ein volles Buch und ein zu strenges Tor sahen im Journal gleich
aus. `ablehnungen.csv` schreibt je Zyklus, was die billigen Tore verworfen
haben (Alter, Marktkapitalisierung, doppelte Kopie), was das Buch mit den
bewerteten Kandidaten getan hat und fuer jeden Kandidaten, der bis zum
Risiko-Scan kam, eine Zeile mit Kennung und Grund. Die Datei ist
Laufzeitdaten wie das Journal, wird nur im echten Lauf geschrieben und wie
das Journal nach `journal_zweitziel` gespiegelt.

Aufruf:
    python spiegel.py --waehlen     # verfolgte.json aus dem Feed neu bauen
    python spiegel.py --wachen      # Grenzen als Momentaufnahme
    python spiegel.py --vorschau    # was waere dran, ohne zu schreiben
    python spiegel.py --papier      # ein Papierzyklus mit Journal
    python spiegel.py --bilanz      # welche Wallets haben getragen
    python spiegel.py --ablehnungen # warum Kandidaten NICHT gekauft wurden
    python spiegel.py --live        # verweigert, nennt den Grund
"""

import argparse
import collections
import csv
import importlib.util
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import PurePath

HIER = os.path.dirname(os.path.abspath(__file__))
BUS = os.path.join(HIER, os.pardir, os.pardir, "Bus")
for p in (HIER, BUS):
    if p not in sys.path:
        sys.path.insert(0, p)

import ereignis                                               # noqa: E402
import lesen                                                  # noqa: E402

# pos_kennung liegt im Handel-Ordner. Der eigene Spurenordner ist beim
# Start sys.path[0], darum wird der Ordner ANGEHAENGT (nicht vorne
# eingefuegt - ein Eintrag vorne koennte ein gleichnamiges Spurenmodul
# verdecken, siehe Handel/grid.py neben gitter/grid.py).
_handel_ordner = os.path.dirname(HIER)  # Agenten/Handel/, nicht der Spurenordner
if _handel_ordner not in sys.path:
    sys.path.append(_handel_ordner)
import pos_kennung                                              # noqa: E402


def _spiegelquelle():
    """scanner/wachen_pruefung.py per Dateipfad laden.

    Nicht ueber sys.path: scanner/ enthaelt okx.py, scan.py und handeln.py,
    die in dieser Spur fremde Namen verdecken koennen. Die Datei braucht nur
    die Standardbibliothek.
    """
    pfad = os.path.join(HIER, os.pardir, "scanner", "wachen_pruefung.py")
    spec = importlib.util.spec_from_file_location("wachen_pruefung_quelle",
                                                 pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul

# Risikostufe (HANDEL_RISIKO): Der Spiegel laeuft NUR in der Basis (Vorgabe
# Max, 15.09.2026: "alle mit groesseren Positionen je Spur ausser Spiegel").
# Er wird hier deswegen NICHT skaliert und seine Dateien bleiben die
# Basisdateien - ein zweites Buch mit demselben Inhalt waere dieselbe
# Beobachtung noch einmal. Ueber den PFAD geladen wie ratschen.py.
from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec
_rs_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "risikostufe.py")
_rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
risikostufe = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(risikostufe)

def _buch_datei(pfad):
    """Dateiname eines Schattenbuchs: `.../zustand.json` -> `.../zustand.knapp.json`.

    Die Schattenbuecher (V1, 18.09.2026) fahren dieselbe Signalquelle mit
    anderen Stop/Trailing-Parametern - das Hauptbuch bleibt die
    Vergleichsgrundlage. `HANDEL_BUCH` (leer = Hauptbuch) haengt den
    Arm-Namen vor die Endung, Muster `risikostufe.datei()`. Der Typ bleibt
    erhalten (str bleibt str, Path bleibt Path).
    """
    arm = (os.environ.get("HANDEL_BUCH") or "").strip()
    if not arm:
        return pfad
    war_path = isinstance(pfad, PurePath)
    basis, endung = os.path.splitext(os.fspath(pfad))
    neu = basis + "." + arm + endung
    return type(pfad)(neu) if war_path else neu


WACHEN = _buch_datei(os.path.join(HIER, "wachen.json"))
VERFOLGTE = _buch_datei(os.path.join(HIER, "verfolgte.json"))
ZUSTAND = _buch_datei(os.path.join(HIER, "zustand.json"))
JOURNAL = _buch_datei(os.path.join(HIER, "handelsjournal.csv"))
ABLEHNUNGEN = _buch_datei(os.path.join(HIER, "ablehnungen.csv"))

SPALTEN = ["zeit", "modus", "aktion", "kette", "wallet", "token", "symbol",
           "preis", "menge", "einsatz_usd", "wert_usd", "marktkap_usd",
           "slippage_pct", "gebuehr_pct", "grund", "pos_id"]

# Das Ablehnungsprotokoll ist eine EIGENE Datei, nicht das Journal. Die Leser
# des Journals zaehlen Zeilen als Buchungen (bilanz() rechnet jede
# Nicht-eroeffnen-Zeile als Runde, buchauswertung zaehlt je Aktion) - eine
# Ablehnung waere dort eine erfundene Runde und wuerde die Bilanz faelschen.
# Schema:
#   art="zyklus"  eine Zeile je Grund und Zyklus; `anzahl` ist die Zahl.
#   art="signal"  EIN Kandidat mit Kennung (Token, Wallet, tx) und Grund.
SPALTEN_ABLEHNUNG = ["zeit", "art", "grund", "anzahl", "kette", "wallet",
                     "token", "symbol", "marktkap_usd", "alter_s", "preis", "tx"]

# Wie weit zurueck das Protokoll vor dem Schreiben gelesen wird (siehe
# _gesehen): der Feed reicht Stunden zurueck, das deckt ihn ab.
ABLEHNUNG_TAIL = 2000
GESEHEN = None

# Ob geschrieben wird. Die Vorschau stellt das ab (siehe journal()).
SCHREIBEN = True


# --- Sicherheitsnetz --------------------------------------------------------

class Papierfehler(RuntimeError):
    """Ein Kauf wurde aus der Papierspur heraus versucht. Das ist ein Fehler."""


def _kein_schreiben(*a, **kw):
    raise Papierfehler("Diese Spur ist papierfest: Schreibbefehle sind "
                       "stillgelegt.")


# Kein Orderpfad. Der Schreibschutz sitzt in lesen.py und wird hier
# gegengeprueft: Wer ihn dort entfernt, bekommt beim Start dieser Spur einen
# Fehler - lieber kein Buch als ein Buch, das heimlich tauschen koennte.
if not getattr(lesen, "SCHREIBBEFEHLE", None):
    raise RuntimeError("lesen.py hat keinen Schreibschutz mehr - die "
                       "Spiegel-Spur startet nicht.")


# --- Dateien ----------------------------------------------------------------

def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


def _zahl(wert):
    """Zahl aus einer Zeichenkette mit vielen Stellen - oder None."""
    try:
        return float(str(wert).replace(",", ""))
    except (TypeError, ValueError):
        return None


def lade(pfad, vorgabe):
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return vorgabe


def schreibe(pfad, daten):
    atomar.schreibe_json(pfad, daten)


def journal(**felder):
    # In der Vorschau wird nichts geschrieben. Ohne diesen Schalter haette die
    # Vorschau Kopien im Journal geschlossen, die im Zustand offen bleiben -
    # zwei Wahrheiten, und die Vorschau waere keine Vorschau mehr.
    if not SCHREIBEN:
        return
    neu = not os.path.exists(JOURNAL)
    # Altjournal ohne `pos_id` behaelt seine Spalten, die Kennung wird dann
    # nicht geschrieben (pos_kennung.spalten), sonst wuerde jede Zeile die
    # Spalten verschieben (siehe pos_kennung.spalten).
    spalten = SPALTEN if neu else pos_kennung.spalten(JOURNAL, SPALTEN)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in spalten})


# --- Ablehnungsprotokoll ----------------------------------------------------

def journal_ablehnung(**felder):
    """Eine Zeile ins Ablehnungsprotokoll.

    Derselbe Schalter wie im Journal: eine Vorschau, die schreibt, ist keine
    Vorschau.
    """
    if not SCHREIBEN:
        return
    neu = not os.path.exists(ABLEHNUNGEN)
    with open(ABLEHNUNGEN, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=SPALTEN_ABLEHNUNG,
                           extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in SPALTEN_ABLEHNUNG})


def protokolliere(grund, anzahl=1):
    """Was EIN Zyklus abgelehnt hat - als Zahl, ohne Kennung.

    Der Ort fuer die Massenfaelle (Alter, Band): 700 Signale je Zyklus
    einzeln mit Kennung zu protokollieren waere ein Protokoll, das niemand
    liest, und es waechst mit jedem Zyklus weiter.
    """
    journal_ablehnung(zeit=_jetzt(), art="zyklus", grund=grund, anzahl=anzahl)


def _schluessel(felder, grund):
    """Kennung eines Kandidaten: seine Transaktion, sonst sein Token."""
    return (felder.get("tx") or felder.get("token") or "", grund or "")


def _gesehen():
    """Die (tx, grund)-Paare der letzten Protokollzeilen - einmal je Lauf.

    Ein Signal steht mehrere Zyklen im Feed; ohne diese Sperre traegt das
    Protokoll denselben Kandidaten alle 15 Minuten erneut ein, und die
    Zaehlung "wie viele Kandidaten hat das Tor verworfen" waere ein
    Vielfaches der Wahrheit.

    Gelesen wird nur der SCHLUSS der Datei (ABLEHNUNG_TAIL Zeilen): der Feed
    reicht Stunden zurueck, das deckt ihn ab, und die Datei waechst nicht in
    die Lesezeit hinein. Die erste gelesene Zeile faellt weg - sie ist
    entweder die Kopfzeile oder ein angeschnittenes Stueck.
    """
    global GESEHEN
    if GESEHEN is not None:
        return GESEHEN
    GESEHEN = set()
    try:
        with open(ABLEHNUNGEN, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - ABLEHNUNG_TAIL * 200))
            roh = f.read().decode("utf-8", "replace").splitlines()[1:]
    except OSError:
        return GESEHEN
    for zeile in csv.DictReader(roh, fieldnames=SPALTEN_ABLEHNUNG):
        if (zeile.get("art") or "").strip() == "signal":
            GESEHEN.add(_schluessel(zeile, zeile.get("grund")))
    return GESEHEN


def protokolliere_signal(sig, grund):
    """EIN Kandidat mit Kennung und Grund. True, wenn die Zeile neu ist.

    Nur fuer Kandidaten, die bis zum Risiko-Scan gekommen sind: das sind die
    wenigen je Zyklus, und es sind die, deren Grund man spaeter einzeln
    nachsehen will (Risikostufe, doppelt belegt).
    """
    schluessel = _schluessel(sig, grund)
    if schluessel in _gesehen():
        return False
    _gesehen().add(schluessel)
    journal_ablehnung(
        zeit=_jetzt(), art="signal", grund=grund, anzahl=1,
        kette=sig.get("kette"), wallet=sig.get("wallet"),
        token=sig.get("token"), symbol=sig.get("symbol"),
        marktkap_usd=("" if sig.get("marktkap_usd") is None
                      else "%.0f" % sig["marktkap_usd"]),
        alter_s=("" if sig.get("alter_s") is None
                 else "%.0f" % sig["alter_s"]),
        preis=("" if not sig.get("preis") else "%.10g" % sig["preis"]),
        tx=sig.get("tx"))
    return True


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
    z = atomar.lade_json(ZUSTAND, lambda: None)
    if not z:
        z = {"positionen": [], "letzter_lauf": None, "modus": "papier"}
    z.setdefault("positionen", [])
    return z


def schreibe_zustand(z):
    # Wie das Journal: in der Vorschau wird nichts geschrieben. Sonst haette
    # ein Vorschau-Lauf den Herzschlag gesetzt und den Bestand veraendert.
    if not SCHREIBEN:
        return
    z["letzter_lauf"] = _jetzt()
    schreibe(ZUSTAND, z)


def spiegeln(z, w):
    """Bedingung 4: Journal, Zustand und Ablehnungen nach journal_zweitziel.

    EINE Stelle fuer alle Pfade - auch den Notausstieg (Herzschlag alt,
    Kill-Switch): der aendert den Zustand, und eine Kopie ausser Haus, die
    dem Stand hinterherlaeuft, liest sich beim naechsten Vergleich als
    Abweichung. Bis zum 14.09.2026 spiegelte nur der normale Weg; das Muster
    steht in xperp/handeln.py und swap/handeln.py.

    Erst schreiben, dann kopieren: ein haengendes Zweitlaufwerk darf den
    Zyklus verzoegern, aber nicht den Herzschlag verschlucken. Ein fehlendes
    Ziel ist kein Fehler des Laufs - der Stand steht im Zustand. In der
    Vorschau wird nichts kopiert. Rueckgabe (ok, info) wie spiegele_journal.
    """
    if not SCHREIBEN:
        return False, "Vorschau schreibt nichts"
    basis = _spiegelquelle()
    ziel = w.get("journal_zweitziel")
    ok, info = basis.spiegele_journal([JOURNAL, ZUSTAND, ABLEHNUNGEN], ziel)
    if basis.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        # Der Vermerk ist juenger als die Kopie: einmal nachziehen, damit auf
        # Q: derselbe Stand liegt. Sonst waere die Kopie in genau dem Zyklus
        # aelter, in dem sich der Spiegelstand aendert.
        basis.spiegele_journal([ZUSTAND], ziel)
    return ok, info


# --- Auswahl (verfolgte.json) ----------------------------------------------

def waehlen(w):
    """Baut die Verfolgungsliste aus dem Feed - und schreibt nur diese Datei.

    Die Auswahl ist **der Feed**, nicht die Rangliste: Wer nur die Gewinner
    einer Rangliste kopiert, betreibt Zuchtauswahl nach dem Ergebnis
    (Survivorship). Die gemessenen Zahlen der Rangliste werden daneben
    geschrieben, damit die Bilanz spaeter zeigen kann, ob sie die Kopierbarkeit
    vorhersagen - das ist eine offene Frage, keine Annahme.

    Verkaeufe werden gebraucht, um zu sehen, wann ein Vorbild aussteigt. Ob
    ein Kauf kopiert wird, entscheidet das Buch, nicht diese Liste.
    """
    wallet_liste = {}
    zahlen = {}
    for kette in w["ketten"]:
        try:
            for e in lesen.leaderboard(kette):
                zahlen[(kette, e.get("walletAddress"))] = e
        except lesen.Lesefehler as e:
            print("  Rangliste %s nicht abrufbar: %s" % (kette, e))
        for art in ("smart_money", "kol"):
            try:
                trades = lesen.tracker(kette, art)
            except lesefehler_arten() as e:
                print("  Feed %s/%s nicht abrufbar: %s" % (kette, art, e))
                continue
            for t in trades:
                adresse = t.get("walletAddress")
                if not adresse:
                    continue
                schluessel = (kette, adresse)
                eintrag = wallet_liste.setdefault(schluessel, {
                    "kette": kette, "wallet": adresse, "quellen": [],
                    "letzte_sichtung": None})
                eintrag["quellen"].append("tracker/%s" % art)
                zeit = t.get("tradeTime")
                if zeit and (not eintrag["letzte_sichtung"]
                             or int(zeit) > int(eintrag["letzte_sichtung"])):
                    eintrag["letzte_sichtung"] = int(zeit)

    for eintrag in wallet_liste.values():
        eintrag["quellen"] = sorted(set(eintrag["quellen"]))
        z = zahlen.get((eintrag["kette"], eintrag["wallet"]))
        if z:
            eintrag["gemessen"] = True
            for feld, name in (("winRatePercent", "trefferquote_pct"),
                               ("txs", "trades"), ("realizedPnlUsd", "pnl_usd"),
                               ("realizedPnlPercent", "roi_pct"),
                               ("avgBuyValueUsd", "einsatz_schnitt_usd"),
                               ("lastActiveTimestamp", "zuletzt_aktiv_ms")):
                eintrag[name] = z.get(feld)
        else:
            eintrag["gemessen"] = False

    daten = {
        "stand": _jetzt(),
        "regel": ("Alle Wallets, die im Feed (smart_money/kol) handeln. "
                  "Keine Vorauswahl nach Ergebnis; die Ranglistenzahlen "
                  "stehen daneben, entscheiden aber nicht."),
        "ketten": w["ketten"],
        "wallets": sorted(wallet_liste.values(),
                          key=lambda x: (x["kette"], x["wallet"])),
    }
    schreibe(VERFOLGTE, daten)
    gemessen = sum(1 for x in daten["wallets"] if x["gemessen"])
    print("verfolgte.json: %d Wallets (%d davon mit Ranglistenzahlen)"
          % (len(daten["wallets"]), gemessen))
    print("  %s" % ", ".join("%s: %d" % (k, sum(1 for x in daten["wallets"]
                                                if x["kette"] == k))
                             for k in w["ketten"]))
    return daten


def lesefehler_arten():
    """Ein Tupel, damit aeltere und neue Fehlerklassen gefangen werden."""
    return (lesen.Lesefehler, OSError, ValueError)


# --- Umfang: Papier sammelt, live gilt das Muster ---------------------------

# Was den Durchsatz begrenzt, ist der PLATZ, nicht das Tor: am 14.09.2026 war
# das Buch mit 20 Kopien dauerhaft voll, der Zyklus brach beim ersten
# Platzmangel ab, und alles danach fiel als "kaufbar, aber nicht mehr erreicht"
# aus. Durchsatz = Plaetze x Umschlaege je Platz und Tag (beobachtet 1,3).
# Deshalb sammelt das Papierbuch mit mehr Plaetzen - ohne eine einzige
# Bedingung zu veraendern: Tore, Stop, Ziel, Frist und Kosten bleiben gleich,
# sonst waere die Messung eine andere Strategie und nicht mehr uebertragbar.
PAPIER_UMFANG = (("max_offen", "max_offen_papier"),
                 ("kill_switch_gesamt_usd", "kill_switch_gesamt_usd_papier"))


def _umfang(w, modus):
    """Papier-Umfang anwenden - solange die Spur Papier ist.

    Das Muster (die Werte ohne Suffix) gilt, sobald die Spur live ist
    (`handel_erlaubt: true`) oder `--live` angefordert wird. Der Schalter ist
    damit derselbe, der die Spur von Papier auf Geld stellt: wer ihn umlegt,
    bekommt das Muster, ohne dass jemand einen zweiten Wert nachziehen muss.
    Rueckgabe ist dasselbe Dict, wenn nichts zu tauschen war.
    """
    if modus == "live" or w.get("handel_erlaubt"):
        return w
    aus = dict(w)
    getauscht = False
    for muster, papier in PAPIER_UMFANG:
        if aus.get(papier) is not None:
            aus[muster] = aus[papier]
            getauscht = True
    return aus if getauscht else w


# --- Buch ------------------------------------------------------------------

def _gefolgt(w):
    d = lade(VERFOLGTE, {})
    return {(x["kette"], x["wallet"]): x for x in d.get("wallets", [])}


def verfolgte_zu_alt(w):
    """Ist die Verfolgungsliste aelter als erlaubt - oder nicht lesbar?

    Der Feed ist ein FENSTER auf die Wallets, die JETZT handeln, keine
    Stammkundschaft: eine einmal gebaute Liste laeuft dem Feed innerhalb von
    Stunden weg. Am 14.09.2026 gemessen: Liste vom 12.09. mit 305 Wallets, im
    Feed handelten 206 Wallets, davon 154 nicht in der Liste - 472 von 706
    Signalen je Zyklus fielen als "Wallet nicht verfolgt" aus. Ein fehlender
    oder unlesbarer Stand gilt als zu alt (dann wird neu gebaut), nicht als
    frisch.
    """
    grenze = w.get("verfolgte_max_alter_stunden", 12)
    stand = _bis_zeit((lade(VERFOLGTE, {}) or {}).get("stand"))
    if not stand:
        return True
    if stand.tzinfo is None:
        stand = stand.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - stand).total_seconds() > grenze * 3600


def _kaufpreis(preis, w):
    """Was ein Nachahmer wirklich zahlt: teurer als der Vorbildkurs."""
    return preis * (1 + w["slippage_pct"] / 100.0)


def _verkaeuflich(menge, kurs, w):
    """Was am Ende ankommt: billiger, und noch einmal Gebuehr."""
    return menge * kurs * (1 - w["slippage_pct"] / 100.0) * (
        1 - w["gebuehr_pct"] / 100.0)


def _vorpruefung(sig, w, z):
    """Die billigen Tore: Alter, Marktkapitalisierung, doppelte Kopie.

    Ruft NICHTS ab - kein Kurs, kein Risiko-Scan. Rueckgabe (Schluessel,
    Text): der Schluessel ist der gleichbleibende Name fuer die Zaehlung im
    Ablehnungsprotokoll, der Text das, was ein Mensch liest. Beides kommt aus
    DIESER Stelle, damit die Zaehlung nicht eine zweite Fassung derselben
    Grenze wird.
    """
    if sig["alter_s"] is not None and sig["alter_s"] > w["max_alter_signal_sekunden"]:
        return "zu alt", "Signal zu alt (%.0f s)" % sig["alter_s"]
    mk = sig["marktkap_usd"]
    unten, oben = w["marketcap_band_usd"]
    if mk is None:
        return "marktkap unbekannt", "Marktkapitalisierung unbekannt"
    if not unten <= mk <= oben:
        return ("marktkap ausserhalb",
                "Marktkapitalisierung %.0f ausserhalb %d-%d" % (mk, unten, oben))
    offen = [p for p in z["positionen"] if p["token"] == sig["token"]]
    if len(offen) >= w["max_kopien_je_token"]:
        return "token belegt", "schon %d Kopien auf diesem Token" % len(offen)
    if any(p["kette"] == sig["kette"] and p["token"] == sig["token"]
           and p["wallet"] == sig["wallet"] for p in z["positionen"]):
        return "wallet belegt", "diese Wallet steht hier schon auf diesem Token"
    return None, None


def _nein(sig, grund):
    """Die Zeile fuer einen abgelehnten Kandidaten - eine Fassung fuer beide
    Wege: die Vorschau druckt sie, der Papierlauf druckt sie beim ersten Mal.

    Kein Filterwort des Dauerlaufs darin (verkauf, stop, KILL, gesperrt,
    ausstieg): eine Zeile mit einem dieser Woerter geht nach Telegram, und
    eine Ablehnung ist keine Meldung wert. Ein Test haelt das fest.
    """
    return "  NEIN %-10s %-28s %s" % ((sig.get("symbol") or "?")[:10],
                                      sig.get("token"), grund)


def _zaehle_unerreicht(lage, rest):
    """Die Kandidaten hinter einem Abbruch: kaufbar, aber nicht mehr erreicht.

    Gezaehlt wird aus der Vorpruefung vom ZYKLUSBEGINN - die Duplikatstriche
    koennen sich inzwischen geaendert haben, weil im selben Zyklus schon
    gekauft wurde. Deshalb heisst der Zaehler "davon ... bei Zyklusbeginn":
    eine Zahl mit ihrem Vorbehalt statt einer stillen Behauptung. Das "davon"
    ist Absicht - es ist eine TEILMENGE der kaufbaren Signale, keine zweite
    Zahl zum Addieren.
    """
    kaufbar = sum(1 for schluessel, _ in rest if schluessel is None)
    if kaufbar:
        lage["davon kaufbar, aber nicht mehr erreicht"] += kaufbar


def _kopie(sig, w, z):
    """Ein Kauf wird zur Buchzeile - oder es gibt einen Grund, warum nicht."""
    _, grund = _vorpruefung(sig, w, z)
    if grund:
        return None, grund

    if w["risiko_pflicht"]:
        try:
            r = lesen.risiko(sig["token"], sig["kette"])
        except lesen.Lesefehler as e:
            return None, "Risikopruefung nicht moeglich: %s" % e
        if r["stufe"] not in w["max_risiko_stufen"]:
            return None, "Risikostufe %s (%s)" % (r["stufe"],
                                                  ",".join(r["merkmale"][:3]))
    else:
        r = {"stufe": "ungeprueft", "merkmale": []}

    mk = sig["marktkap_usd"]
    einsatz = w["max_einsatz_je_kopie_usd"]
    kauf = _kaufpreis(sig["preis"], w)
    gebuehr = einsatz * w["gebuehr_pct"] / 100.0
    menge = (einsatz - gebuehr) / kauf
    return {
        "kette": sig["kette"], "wallet": sig["wallet"], "token": sig["token"],
        "symbol": sig["symbol"], "quelle": sig["quelle"],
        "einsatz_usd": einsatz, "menge": menge, "preis_vorbild": sig["preis"],
        "preis_einstieg": kauf, "marktkap_usd": mk, "risiko": r["stufe"],
        "stop_usd": w.get("stop_usd"),
        "stop_preis": kauf * (1 - w["stop_pct"] / 100.0),
        # Seit 15.09.2026 kein festes Ziel mehr: Trailing-Stop, damit
        # theoretische 10x/100x laufen koennen. Die beiden Saetze sind ein
        # Schnappschuss beim Buchen; trail_aktiv_ab_pct misst gegen den
        # Einstieg (was WIR gezahlt haben, nicht der Vorbildkurs).
        "trail_aktiv_ab_pct": w["trail_aktiv_ab_pct"],
        "trail_abstand_pct": w["trail_abstand_pct"],
        "hoechster_kurs": kauf,
        "frist": _plus_stunden(w["haltedauer_stunden"]),
        "eroeffnet": _heute(), "eroeffnet_zeit": _jetzt(),
        "pos_id": pos_kennung.neu(_jetzt()),
    }, None


def _plus_stunden(stunden):
    from datetime import timedelta
    return (datetime.now(timezone.utc)
            + timedelta(hours=stunden)).isoformat(timespec="seconds")


def _lokal(wert):
    """Eine UTC-Zeit als lokale Zeit MIT Datum (Format 14.09. 15:22).

    Eine Uhrzeit ohne Datum und ohne Zone liest sich als Frist in der
    Vergangenheit: die Kopie PFCHAN wurde am 13.09.2026 13:22 UTC eroeffnet,
    ihre Frist lag 24 h spaeter - angezeigt wurde ``Frist 13:22`` (die
    UTC-Stunde), fuer Max in UTC+2 also zwei Stunden VOR der Meldung.
    """
    t = _bis_zeit(wert)
    return t.astimezone().strftime("%d.%m. %H:%M") if t else str(wert)


def _bis_zeit(wert):
    try:
        return datetime.fromisoformat(wert) if wert else None
    except (TypeError, ValueError):
        return None


def eroeffne(z, sig, w):
    p, grund = _kopie(sig, w, z)
    if not p:
        return grund
    z["positionen"].append(p)
    print("  AUF %-10s %-28s @ %.10g (Vorbild %.10g, %.1f%% Slippage) "
          "%.0f USD, %s"
          % (p["symbol"], p["token"], p["preis_einstieg"], p["preis_vorbild"],
             w["slippage_pct"], p["einsatz_usd"], p["risiko"]))
    print("      %-10s %-28s  Stop %.10g (max -%.0f%% nach Kosten)  "
          "Trail ab +%.0f%% (Abstand %.0f%%)  Frist %s lokal"
          % (p["symbol"], p["token"], p["stop_preis"], w["stop_pct"],
             w["trail_aktiv_ab_pct"], w["trail_abstand_pct"],
             _lokal(p["frist"])))
    journal(zeit=_jetzt(), modus="papier", aktion="eroeffnen", kette=p["kette"],
            wallet=p["wallet"], token=p["token"], symbol=p["symbol"],
            preis="%.10g" % p["preis_einstieg"], menge="%.6f" % p["menge"],
            einsatz_usd="%.2f" % p["einsatz_usd"],
            marktkap_usd="%.0f" % p["marktkap_usd"],
            slippage_pct=w["slippage_pct"], gebuehr_pct=w["gebuehr_pct"],
            grund="kopie", pos_id=p["pos_id"])
    return None


def _ausstiegsgrund(p, kurs, jetzt, w):
    """Der Ausstiegsgrund einer Kopie - EINE Stelle fuer alt und neu.

    Reihenfolge: zuerst der harte Stop (der Schaden ist begrenzt, der Gewinn
    nicht), dann Ziel oder Trailing, dann die Frist.

    Neue Kopien (ab 15.09.2026) tragen die Trailing-Felder: sobald der Kurs
    trail_aktiv_ab_pct ueber dem Einstieg lag, haengt der Ausstieg
    trail_abstand_pct unter dem hoechsten seither beobachteten Kurs - kein
    festes Ziel, ein 10x/100x laeuft weiter. Der hoechste Kurs wird hier
    fortgeschrieben; der geschlossene Altbestand (ohne die Felder) laeuft
    unter stop/ziel/frist aus und bleibt so mit dem Vorher vergleichbar.
    Ein gerissener Stop schliesst zum BEOBACHTETEN Kurs (erster Print unter
    dem Stop), nicht zum Stop-Preis - sofort, wie eine Stop-Market-Order.
    """
    if p.get("stop_usd") is not None:
        # Neue Ausstiegsform (15.09.2026 Max): Stop in USD statt Prozent.
        # Realisierter Verlust am Stop >= stop_usd -> raus. Bei hoher
        # Volatilitaet fliegen enge Prozent-Stops zu frueh.
        erloes = _verkaeuflich(p["menge"], kurs, w)
        if p["einsatz_usd"] - erloes >= p["stop_usd"]:
            return "stop"
    elif kurs <= p["stop_preis"]:
        return "stop"
    if p.get("trail_abstand_pct"):
        p["hoechster_kurs"] = max(p.get("hoechster_kurs") or kurs, kurs)
        peak = p["hoechster_kurs"] / p["preis_einstieg"] - 1
        if peak >= p["trail_aktiv_ab_pct"] / 100.0:
            trail_stop = p["hoechster_kurs"] * (
                1 - p["trail_abstand_pct"] / 100.0)
            if kurs <= trail_stop:
                return "trail"
    elif kurs >= p.get("ziel_preis", float("inf")):
        return "ziel"
    if jetzt >= (_bis_zeit(p["frist"]) or jetzt):
        return "frist"
    return None


def _frist_ohne_kurs(p, jetzt):
    """Ist die Frist einer Kopie abgelaufen, obwohl sie keinen Kurs hat?

    Bis 09.10.2026 stand der Zweig "kein Kurs - Kopie bleibt" VOR der Frist: eine
    Kopie, deren Token nie oder nicht mehr bewertet wurde (Pool leer, delisted),
    blieb fuer immer im Buch und belegte einen Platz - das Sicherheitsnetz gegen
    tote Positionen griff genau bei den toten nicht. Jetzt wird sie nach der Frist
    mit Erloes 0 geschlossen (Totalverlust, Grund `frist_ohne_kurs`, damit sie im
    Journal von einem regulaeren Stop-Verlust unterscheidbar bleibt).
    """
    return jetzt >= (_bis_zeit(p["frist"]) or jetzt)


def _schliesse_ohne_kurs(p):
    print("  AUSSTIEG (frist_ohne_kurs)%s: %s %s  G/V %+.2f USD auf %.0f USD "
          "(kein Kurs seit Fristablauf, Erloes 0)"
          % ("" if SCHREIBEN else " [nur Vorschau]", p["symbol"], p["token"],
             -p["einsatz_usd"], p["einsatz_usd"]))
    journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
            kette=p["kette"], wallet=p["wallet"], token=p["token"],
            symbol=p["symbol"], preis="", menge="%.6f" % p["menge"],
            einsatz_usd="%.2f" % p["einsatz_usd"], wert_usd="0.00",
            grund="frist_ohne_kurs", pos_id=p.get("pos_id", ""))


def pruefe_ausstiege(z, w):
    """Stop, Trailing, Frist - und der Kill-Switch ueber das ganze Buch."""
    offen = z["positionen"]
    if not offen:
        return
    kurse = {}
    try:
        kurse = lesen.preise([(p["kette"], p["token"]) for p in offen])
    except lesen.Lesefehler as e:
        print("  Kurse nicht abrufbar (%s) - Bestand bleibt" % e)
        return

    behalten, jetzt = [], datetime.now(timezone.utc)
    for p in offen:
        kurs = kurse.get((p["kette"], p["token"]))
        grund = None
        if kurs is None:
            if _frist_ohne_kurs(p, jetzt):
                _schliesse_ohne_kurs(p)
                continue
            print("  %-10s %-28s kein Kurs - Kopie bleibt" % (p["symbol"],
                                                             p["token"]))
            behalten.append(p)
            continue
        grund = _ausstiegsgrund(p, kurs, jetzt, w)
        if not grund:
            behalten.append(p)
            continue
        erloes = _verkaeuflich(p["menge"], kurs, w)
        print("  AUSSTIEG (%s)%s: %s %s @ %.10g  G/V %+.2f USD auf %.0f USD"
              % (grund, "" if SCHREIBEN else " [nur Vorschau]", p["symbol"],
                 p["token"], kurs, erloes - p["einsatz_usd"],
                 p["einsatz_usd"]))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                kette=p["kette"], wallet=p["wallet"], token=p["token"],
                symbol=p["symbol"], preis="%.10g" % kurs,
                menge="%.6f" % p["menge"], einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes, grund=grund,
                pos_id=p.get("pos_id", ""))
    z["positionen"] = behalten


def _kurse_holen(z):
    """Aktuelle Kurse aller offenen Positionen, {(kette, token): preis}. Leer bei Lesefehler."""
    if not z["positionen"]:
        return {}
    try:
        return lesen.preise([(p["kette"], p["token"]) for p in z["positionen"]]) or {}
    except lesen.Lesefehler:
        return {}


def kill_switch(z, w, kurse=None):
    """Ruecklauf des Buches gegen die Grenze: dann alles flach.

    `kurse` darf der Aufrufer mitgeben (dann kein zweiter Abruf); der Kill-Zweig
    reicht dieselben Kurse an `flach_stellen` weiter.
    """
    if not z["positionen"]:
        return False
    if kurse is None:
        kurse = _kurse_holen(z)
    if not kurse:
        return False
    wert = sum(_verkaeuflich(p["menge"], kurse[(p["kette"], p["token"])], w)
               for p in z["positionen"]
               if (p["kette"], p["token"]) in kurse)
    einsatz = sum(p["einsatz_usd"] for p in z["positionen"]
                  if (p["kette"], p["token"]) in kurse)
    if wert - einsatz > -w["kill_switch_gesamt_usd"]:
        return False
    print("- Kill-Schwelle erreicht (%+.2f USD) -> alle Kopien zu -"
          % (wert - einsatz))
    return True


def flach_stellen(z, w, grund, kurse=None):
    """Alle Kopien zuschreiben.

    `kurse` = die Kurse, auf denen die Entscheidung beruht (Kill); ohne sie wird je
    Position abgerufen. Fehlt der Kurs einer Position, BLEIBT sie im Buch: bis
    09.10.2026 wurde sie mit Erloes 0 gebucht, also als Totalverlust - auch wenn der
    Kurs eine Sekunde vorher noch da war und nur ein Abruf kurz scheiterte. Der
    naechste Zyklus versucht es erneut.
    """
    behalten = []
    for p in list(z["positionen"]):
        schluessel = (p["kette"], p["token"])
        if kurse is not None:
            kurs = kurse.get(schluessel)
        else:
            try:
                kurs = lesen.preise([schluessel]).get(schluessel)
            except lesen.Lesefehler:
                kurs = None
        if not kurs:
            print("  %s %s: kein Kurs - Kopie bleibt im Buch, naechster Zyklus "
                  "versucht es erneut" % (p["symbol"], p["token"]), file=sys.stderr)
            behalten.append(p)
            continue
        erloes = _verkaeuflich(p["menge"], kurs, w)
        print("  AUSSTIEG (%s): %s %s  G/V %+.2f USD"
              % (grund, p["symbol"], p["token"], erloes - p["einsatz_usd"]))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                kette=p["kette"], wallet=p["wallet"], token=p["token"],
                symbol=p["symbol"], preis="%.10g" % kurs,
                menge="%.6f" % p["menge"], einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes, grund=grund,
                pos_id=p.get("pos_id", ""))
    z["positionen"] = behalten


# --- Bilanz ----------------------------------------------------------------

def bilanz(w):
    """Welche Wallets haben getragen - und welche gemessenen Zahlen luegen."""
    if not os.path.exists(JOURNAL):
        print("Noch keine Buchzeile - kein Journal.")
        return
    gefolgt = {k: v for k, v in _gefolgt(w).items()}
    je_wallet = {}
    offen = {}
    with open(JOURNAL, newline="", encoding="utf-8") as f:
        for zeile in csv.DictReader(f):
            schluessel = (zeile["kette"], zeile["wallet"])
            if zeile["aktion"] == "eroeffnen":
                offen[schluessel] = offen.get(schluessel, 0) + int(
                    float(zeile["einsatz_usd"] or 0) * 100)
                continue
            einsatz = int(float(zeile["einsatz_usd"] or 0) * 100)
            wert = int(float(zeile["wert_usd"] or 0) * 100)
            e = je_wallet.setdefault(schluessel, {"runden": 0, "gv": 0,
                                                  "symbole": set()})
            e["runden"] += 1
            e["gv"] += wert - einsatz
            e["symbole"].add(zeile["symbol"])
    if not je_wallet:
        print("Keine abgeschlossene Kopie im Journal.")
        return
    print("Bilanz aus %d abgeschlossenen Kopien (Zahlen in USD):" % sum(
        e["runden"] for e in je_wallet.values()))
    for (kette, wallet), e in sorted(je_wallet.items(),
                                     key=lambda x: -x[1]["gv"]):
        z = gefolgt.get((kette, wallet), {})
        zahlen = ("Trefferquote %s%%, %s Trades" % (z.get("trefferquote_pct"),
                                                    z.get("trades"))
                  if z.get("gemessen") else "nicht in der Rangliste")
        print("  %-9s %-44s %3d Runden  G/V %+8.2f  (%s)"
              % (kette, wallet, e["runden"], e["gv"] / 100.0, zahlen))


# --- Ablehnungs-Bilanz -----------------------------------------------------

def ablehnungsbilanz(stunden=24.0):
    """Was das Ablehnungsprotokoll hergibt - lesend, ohne Netz.

    Zwei Aussagen, die getrennt bleiben muessen: die LAGE (was die Zyklen an
    Signalen mitbrachten und woran sie haengen blieben - reine Rechnung) und
    die ENTSCHEIDUNG (was das Buch mit den bewerteten Kandidaten getan hat,
    inklusive Platzmangel). Wer beides zusammenwirft, haelt ein volles Buch
    fuer ein zu strenges Tor - und dreht dann an der falschen Grenze.

    Die Kontrollzeile am Ende haelt die beiden Seiten zusammen: kaufbar ist
    die Summe aus dem, was das Buch bewertet hat, und dem, was es nicht mehr
    erreicht hat.
    """
    if not os.path.exists(ABLEHNUNGEN):
        print("Noch kein Ablehnungsprotokoll: %s" % ABLEHNUNGEN)
        print("Es entsteht im ersten Papierzyklus - die Vorschau schreibt nichts.")
        return 1

    grenze = (datetime.now(timezone.utc) - timedelta(hours=stunden)
              if stunden and stunden > 0 else None)
    zeilen = []
    with open(ABLEHNUNGEN, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            t = _bis_zeit(r.get("zeit"))
            if grenze and t and t < grenze:
                continue
            zeilen.append(r)
    if not zeilen:
        print("Keine Zeile im Zeitraum (%s)." %
              ("gesamt" if grenze is None else "letzte %g h" % stunden))
        return 0

    lage, entscheidung, kandidaten = (collections.Counter(),
                                      collections.Counter(),
                                      collections.Counter())
    zyklen = fehlend = 0
    for r in zeilen:
        art = (r.get("art") or "").strip()
        grund = (r.get("grund") or "").strip()
        anzahl = int(_zahl(r.get("anzahl")) or 0)
        if art == "signal":
            kandidaten[grund] += 1
        elif art != "zyklus":
            fehlend += 1
        elif grund == "Signale gesehen":
            zyklen += 1
        elif grund.startswith("Lage: "):
            lage[grund[len("Lage: "):]] += anzahl
        elif grund.startswith("Entscheidung: "):
            entscheidung[grund[len("Entscheidung: "):]] += anzahl

    print("=== Spiegel: Ablehnungsprotokoll ===")
    print("Zeitraum: %s, %d Zyklen, %d Zeilen"
          % ("gesamt" if grenze is None else "letzte %g h" % stunden,
             zyklen, len(zeilen)))
    print()
    print("Lage - was die Zyklen mitbrachten (billige Tore, kein Abruf):")
    for name, anzahl in lage.most_common():
        print("  %-46s %8d" % (name, anzahl))
    print()
    print("Entscheidung - was das Buch mit den bewerteten Kandidaten tat:")
    if not entscheidung:
        print("  (keine - kein Kandidat wurde in diesem Zeitraum bewertet)")
    for name, anzahl in entscheidung.most_common():
        zusatz = ("  (%d von %d Zyklen)" % (anzahl, zyklen)
                  if zyklen and name.endswith("nicht bewertet") else "")
        print("  %-46s %8d%s" % (name, anzahl, zusatz))
    print()
    if kandidaten:
        print("Einzelne Kandidaten: %d Zeilen" % sum(kandidaten.values()))
        for name, anzahl in kandidaten.most_common(10):
            print("  %-46s %8d" % (name, anzahl))
    else:
        print("Einzelne Kandidaten: keine - kein Signal kam bis zum "
              "Risiko-Scan.")
    print()
    kaufbar = lage.get("kaufbar", 0)
    nicht_erreicht = lage.get("davon kaufbar, aber nicht mehr erreicht", 0)
    # Die Kapazitaets-Zaehler zaehlen EREIGNISSE (ein Abbruch je Zyklus), nicht
    # Kandidaten - sie gehoeren deshalb nicht in die Bilanz der Kandidaten.
    kapazitaet = {k for k in entscheidung if k.endswith("nicht bewertet")}
    bewertet = sum(n for k, n in entscheidung.items() if k not in kapazitaet)
    print("Kontrolle: kaufbar %d = bewertet %d + nicht mehr erreicht %d"
          % (kaufbar, bewertet, nicht_erreicht))
    if kaufbar != bewertet + nicht_erreicht:
        print("  Achtung: die beiden Seiten gehen nicht auf (%+d). Ein neuer "
              "Zweig im Zyklus, der keinen Zaehler setzt?"
              % (kaufbar - bewertet - nicht_erreicht))
    if fehlend:
        print("  %d Zeilen ohne bekannte Form (art weder zyklus noch signal)"
              % fehlend)
    return 0


# --- Lauf ------------------------------------------------------------------

def zeige_wachen(w):
    print("Grenzen der Spiegel-Spur (Papier):")
    for name in ("ketten", "max_einsatz_je_kopie_usd", "max_offen",
                 "max_neu_je_zyklus", "max_kopien_je_token",
                 "kill_switch_gesamt_usd", "slippage_pct", "gebuehr_pct",
                 "stop_pct", "trail_aktiv_ab_pct", "trail_abstand_pct",
                 "haltedauer_stunden", "max_alter_signal_sekunden",
                 "marketcap_band_usd", "max_risiko_stufen",
                 "herzschlag_max_minuten", "max_offen_papier",
                 "kill_switch_gesamt_usd_papier"):
        print("  %-30s %s" % (name, w.get(name)))
    print("  %-30s %s" % ("handel_erlaubt", w.get("handel_erlaubt")))
    print("  %-30s %s" % ("Umfang gilt jetzt",
                          "Papier" if _umfang(w, "papier") is not w
                          else "Muster (live)"))
    z = lade_zustand()
    print("  %-30s %s" % ("journal_zweitziel",
                          w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  %-30s %s (%s)" % ("letzte Kopie", z.get("journal_zweitziel_ok"),
                               z.get("journal_zweitziel_info")))


def signale_sammeln(w):
    aus, gesehen = [], set()
    for kette in w["ketten"]:
        for art in ("smart_money", "kol"):
            try:
                sig = lesen.signale(kette, art)
            except lesefehler_arten() as e:
                print("  Feed %s/%s nicht abrufbar: %s" % (kette, art, e))
                continue
            for s in sig:
                if not s["tx"] or s["tx"] in gesehen:
                    continue
                gesehen.add(s["tx"])
                aus.append(s)
    return aus


def lauf(modus, stunden=24.0):
    global SCHREIBEN, GESEHEN
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Die Vorschau liest und rechnet, schreibt aber nichts - kein Journal,
    # kein Zustand. Alles andere schreibt (Papier ist ein Lauf, kein Entwurf).
    SCHREIBEN = modus != "vorschau"
    # Die Sperre gegen doppelte Protokollzeilen wird je Lauf neu aus der
    # Datei gelesen: die Datei ist die Wahrheit, nicht der Prozess.
    GESEHEN = None

    # Risikostufen: Der Spiegel kennt nur die Basis. Liefe er in einer Stufe
    # mit, schriebe er in dieselben Dateien wie der Basislauf (sie werden
    # hier absichtlich nicht gesuffixt) und die zwei Laeufe ueberschrieben
    # sich die Positionen. Frueher abbrechen als still ein Buch zerstoeren.
    if not risikostufe.ist_basis():
        print("HANDEL_RISIKO=%s: Der Spiegel laeuft nur in der Basis "
              "(gleicher Einsatz in jeder Stufe). Kein Lauf."
              % risikostufe.stufe())
        return 1

    w = lade(WACHEN, None)
    if not w:
        print("wachen.json fehlt oder ist unlesbar - kein Lauf.")
        return 1

    if modus == "waehlen":
        waehlen(w)
        return 0
    if modus == "wachen":
        zeige_wachen(w)
        return 0
    if modus == "bilanz":
        bilanz(w)
        return 0
    if modus == "ablehnungen":
        return ablehnungsbilanz(stunden)
    if modus == "messen":
        return messen(w, lade_zustand())

    # Papier sammelt mit groesserem Umfang, live gilt das Muster (siehe
    # _umfang). Die Zeile nennt den geltenden Umfang in jedem Zyklus - ohne das
    # Wort "kill" (der Dauerlauf schickt jede Zeile mit diesem Wort nach
    # Telegram) und in jedem Modus, den ein Aufrufer parst.
    roh = w
    w = _umfang(w, modus)
    if w is not roh:
        print("  Umfang: Papier - %d Plaetze, Notbremse %.0f USD "
              "(Muster fuer live: %d Plaetze, %.0f USD)"
              % (w["max_offen"], w["kill_switch_gesamt_usd"],
                 roh["max_offen"], roh["kill_switch_gesamt_usd"]))

    z = lade_zustand()

    if modus == "live":
        # Genau ein Grund, und das Wort Freigabefenster kommt darin nicht vor:
        # dauerlauf.nur_fenster_fehlt fragt nur, wenn der Grund dieses Wort
        # traegt. Es gibt hier keinen Live-Pfad, den eine Freigabe oeffnen
        # koennte.
        print("--live angefordert, aber gesperrt: kein Live-Pfad in dieser "
              "Spur (Papier)")
        print("-> es wird Papier gebucht.")

    if z["positionen"] and not _frisch(z, w):
        print("- Herzschlag alt (%s) -> alle Kopien zu, kein Neuerwerb dieser "
              "Lauf -" % z.get("letzter_lauf"))
        flach_stellen(z, w, "herzschlag_alt")
        schreibe_zustand(z)
        # Bedingung 4 gilt auch hier: der Notausstieg aendert den Zustand, und
        # eine Kopie ausser Haus, die dem Stand hinterherlaeuft, liest sich
        # beim naechsten Vergleich als Abweichung (Muster: xperp/handeln.py).
        spiegeln(z, w)
        return 0

    pruefe_ausstiege(z, w)
    kurse_kill = _kurse_holen(z)
    if kill_switch(z, w, kurse_kill):
        flach_stellen(z, w, "kill_switch", kurse_kill)
        schreibe_zustand(z)
        spiegeln(z, w)
        return 0

    # Die Verfolgungsliste ist ein Fenster auf den Feed, kein Stammbuch (siehe
    # verfolgte_zu_alt): ist sie zu alt, wird sie hier neu gebaut - im
    # SCHREIBENDEN Lauf. Die Vorschau baut nichts: `waehlen` schreibt die Datei
    # direkt und kennt den Schreibschalter nicht.
    if SCHREIBEN and verfolgte_zu_alt(w):
        print("  Verfolgungsliste aelter als %s h - wird aus dem Feed neu gebaut"
              % w.get("verfolgte_max_alter_stunden", 12))
        waehlen(w)
        print("  Rueckkehr zum Zyklus")
    gefolgt = _gefolgt(w)
    if not gefolgt:
        print("verfolgte.json ist leer - erst '--waehlen' laufen lassen.")
        return 1
    sig = signale_sammeln(w)
    # Die billige Vorpruefung laeuft EINMAL ueber alle Signale (reine Rechnung,
    # kein Abruf): sie sagt, wie viele Kandidaten der Zyklus mitgebracht hat
    # und woran sie haengen bleiben. Der Entscheidungszaehler daneben sagt,
    # was das Buch mit den bewerteten Kandidaten getan hat. Zwei verschiedene
    # Aussagen - beide gehoeren ins Protokoll, keine ersetzt die andere.
    # JEDES Signal landet in GENAU EINEM Lage-Zaehler: erst die Zugehoerigkeit
    # (wallet nicht verfolgt), dann die billigen Tore. Ohne diese Reihenfolge
    # zaehlt ein Signal doppelt (Befund am ersten echten Zyklus: kaufbar 58,
    # bewertet 12, nicht erreicht 54 - die drei zu viel waren nicht verfolgte
    # Wallets, die auch unter "kaufbar" standen).
    vorpruefung = []
    for s in sig:
        if (s["kette"], s["wallet"]) not in gefolgt:
            vorpruefung.append(("wallet nicht verfolgt",
                                "Wallet steht nicht in verfolgte.json"))
        else:
            vorpruefung.append(_vorpruefung(s, w, z))
    lage = collections.Counter(g or "kaufbar" for g, _ in vorpruefung)
    entscheidung = collections.Counter()
    neu = 0
    for i, s in enumerate(sig):
        if len(z["positionen"]) >= w["max_offen"]:
            print("  Buch voll (%d Kopien) - Rest faellt aus"
                  % w["max_offen"])
            entscheidung["Buch voll - Kandidat nicht bewertet"] += 1
            _zaehle_unerreicht(lage, vorpruefung[i:])
            break
        if neu >= w["max_neu_je_zyklus"]:
            print("  Zyklusdeckel erreicht (%d neue Kopien)" % w["max_neu_je_zyklus"])
            entscheidung["Zyklusdeckel - Kandidat nicht bewertet"] += 1
            _zaehle_unerreicht(lage, vorpruefung[i:])
            break
        if (s["kette"], s["wallet"]) not in gefolgt:
            # Steht als Lage-Zaehler im Protokoll - hier keine zweite Zeile.
            continue
        if modus == "vorschau":
            p, grund = _kopie(s, w, z)
            print("  WAERE %-10s %-28s %d USD"
                  % (s["symbol"][:10], s["token"],
                     w["max_einsatz_je_kopie_usd"]) if p else _nein(s, grund))
            if p:
                neu += 1
                z["positionen"].append(p)      # nur im Speicher, kein Schreiben
            continue
        grund = eroeffne(z, s, w)
        if grund is None:
            neu += 1
            entscheidung["kopiert"] += 1
            continue
        if vorpruefung[i][0] is not None:
            # Schon am billigen Tor gescheitert: das steht als Zahl in der Lage
            # (700 Signale je Zyklus wuerden als Einzelzeilen das Protokoll
            # fluten und die Ausgabe unlesbar machen).
            continue
        entscheidung[grund] += 1
        # Die Zeile steht im Papierlauf sonst nirgends (der Dauerlauf
        # protokolliert nur "ok"), und genau sie fehlte: WELCHER Kandidat
        # woran scheitert. Gedruckt wird nur das erste Mal - dasselbe Signal
        # steht Stunden im Feed.
        if protokolliere_signal(s, grund):
            print(_nein(s, grund))

    if SCHREIBEN:
        # Was der Zyklus gesehen hat und woran es hing. Geschrieben wird in
        # jedem Zyklus (auch bei 0 Signalen): die Null ist die Aussage "Feed
        # hatte nichts" und die Grundlage fuer den Anteil der Zyklen mit
        # vollem Buch.
        protokolliere("Signale gesehen", len(sig))
        for name, anzahl in sorted(lage.items()):
            protokolliere("Lage: %s" % name, anzahl)
        for name, anzahl in sorted(entscheidung.items()):
            protokolliere("Entscheidung: %s" % name, anzahl)

    print("=== Spiegel (PAPIER%s) | %d Signale, %d verfolgte Wallets | "
          "%d Kopien offen, %d neu ==="
          % ("" if modus != "vorschau" else ", Vorschau", len(sig), len(gefolgt),
             len(z["positionen"]), neu))
    if modus == "vorschau":
        print("Live waere gesperrt durch: kein Live-Pfad in dieser Spur (Papier)")
        return 0
    # Im Papierlauf steht die Zeile NICHT. Der Dauerlauf schickt jede
    # Ausgabezeile mit dem Wort "gesperrt" nach Telegram (dauerlauf.zyklus) -
    # bei einem Lauf alle 15 Minuten war das Spam (aufgefallen 13.09.2026).
    # Gelesen wird sie nur von dauerlauf.nur_fenster_fehlt(), und das fragt
    # seine Spuren mit --vorschau ab.
    schreibe_zustand(z)
    # Bedingung 4: Journal, Zustand und Ablehnungen ausser Haus - nach dem
    # Herzschlag.
    ok, info = spiegeln(z, w)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))
    return 0


def messen(w, z):
    """Die Kosten-Annahmen gegen echte Bucheindruecke halten.

    Zwei Messungen, weil zwei verschiedene Kosten zusammenkommen:

      1. **Tiefe.** Wie stark bewegt ein Einsatz von X USD den Preis im Pool?
         Naeherung fuer ein Constant-Product-Buch: 2 x Einsatz / Liquiditaet
         (in Prozent). Das ist eine *untere* Grenze - konzentrierte
         Liquiditaet, Spread und Prioritaetsgebuehren stecken nicht darin.
      2. **Nachlauf.** Wie weit ist der Kurs schon weg von dem Kurs, den das
         Vorbild bekommen hat? Das ist die eigentliche Strafe beim Nachahmen,
         und sie steht in keiner Pool-Tiefe. Gemessen an den frischesten
         Signalen: Kurs jetzt gegen Kurs im Signal.

    Gibt beide Verteilungen aus und schreibt sie nach daten/messung.json.
    Geschrieben wird nichts anderes - die Messung aendert kein Buch.
    """
    sig = signale_sammeln(w)
    frisch = [s for s in sig if s["alter_s"] is not None
              and s["alter_s"] <= w["max_alter_signal_sekunden"]]
    auswahl = []
    for s in frisch:
        if s["token"] not in [x["token"] for x in auswahl]:
            auswahl.append(s)
        if len(auswahl) >= 15:
            break
    lesen_je_kette = auswahl
    print("Tiefe und Nachlauf, %d frische Signale" % len(frisch))
    if not auswahl:
        print("  Keine frischen Signale - nichts zu messen.")
        return 1

    zeilen = []
    try:
        # Jede Kette fuer sich: die Stapelabfrage nimmt Kettenindex und Adresse.
        kurse = {}
        for kette in sorted({s["kette"] for s in auswahl}):
            kurse.update(lesen.preise([(kette, s["token"]) for s in auswahl
                                       if s["kette"] == kette]))
    except lesen.Lesefehler as e:
        print("  Kurse nicht abrufbar: %s" % e)
        kurse = {}

    for s in lesen_je_kette:
        t = s["token"]
        try:
            i = lesen.preise_info(t, s["kette"])
        except (lesen.Lesefehler, KeyError, TypeError) as e:
            print("  %s: keine Tiefe (%s)" % (t[:12], e))
            continue
        liq = _zahl(i.get("liquidity"))
        einsatz = w["max_einsatz_je_kopie_usd"]
        tiefe = (2 * einsatz / liq * 100) if liq else None
        kurs_jetzt = kurse.get((s["kette"], t))
        nachlauf = None
        if kurs_jetzt:
            nachlauf = (kurs_jetzt / s["preis"] - 1) * 100
        zeilen.append({"kette": s["kette"], "token": t, "symbol": s["symbol"],
                       "liquiditaet_usd": liq, "einsatz_usd": einsatz,
                       "tiefe_pct": tiefe, "nachlauf_pct": nachlauf,
                       "alter_s": s["alter_s"],
                       "marktkap_usd": _zahl(i.get("marketCap")),
                       "halter": i.get("holders")})
        print("  %-10s %-9s Liq %10s  Tiefe %7s  Nachlauf %8s  (Alter %ss, %s Halter)"
              % (s["symbol"][:10], s["kette"],
                 "?" if liq is None else "%.0f" % liq,
                 "?" if tiefe is None else "%.3f%%" % tiefe,
                 "?" if nachlauf is None else "%+.2f%%" % nachlauf,
                 "?" if s["alter_s"] is None else "%.0f" % s["alter_s"],
                 zeilen[-1]["halter"]))

    def schnitt(feld):
        werte = [z[feld] for z in zeilen if z[feld] is not None]
        if not werte:
            return None
        werte.sort()
        return (sum(werte) / len(werte), werte[len(werte) // 2], werte[-1])

    print()
    for name, feld in (("Tiefe (untere Grenze)", "tiefe_pct"),
                       ("Nachlauf", "nachlauf_pct")):
        m = schnitt(feld)
        print("  %-22s Schnitt %s, Median %s, groesster %s"
              % (name, "?" if not m else "%.2f%%" % m[0],
                 "?" if not m else "%.2f%%" % m[1],
                 "?" if not m else "%.2f%%" % m[2]))
    print("  Annahme in wachen.json: %.1f%% Slippage + %.1f%% Gebuehr"
          % (w["slippage_pct"], w["gebuehr_pct"]))

    ordner = os.path.join(HIER, "daten")
    if not os.path.isdir(ordner):
        os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "messung.json"), "w", encoding="utf-8") as f:
        json.dump({"zeit": _jetzt(), "einsatz_usd": w["max_einsatz_je_kopie_usd"],
                   "annahme_slippage_pct": w["slippage_pct"],
                   "annahme_gebuehr_pct": w["gebuehr_pct"],
                   "werte": zeilen}, f, indent=2, ensure_ascii=False)
    print("  -> daten/messung.json geschrieben (nicht versioniert)")
    return 0


def _frisch(z, w):
    letzte = _bis_zeit(z.get("letzter_lauf"))
    if not letzte:
        return False
    grenze = w.get("herzschlag_max_minuten", 90)
    return (datetime.now(timezone.utc) - letzte).total_seconds() <= grenze * 60


def main():
    # Der Dauerlauf startet dieses Skript als eigenen Prozess (SPUREN
    # ["spiegel"], skript=spiegel.py) - Start und Ende melden sich deshalb
    # hier am Bus.
    # Muster: xperp/handeln.py. Ein toter Bus bricht den Lauf nicht ab.
    with ereignis.lauf("handel/spiegel"):
        return _main()


def _main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--waehlen", action="store_const", const="waehlen",
                   dest="modus", help="verfolgte.json aus dem Feed bauen")
    p.add_argument("--wachen", action="store_const", const="wachen", dest="modus")
    p.add_argument("--vorschau", action="store_const", const="vorschau",
                   dest="modus")
    p.add_argument("--papier", action="store_const", const="papier", dest="modus")
    p.add_argument("--bilanz", action="store_const", const="bilanz", dest="modus")
    p.add_argument("--ablehnungen", action="store_const", const="ablehnungen",
                   dest="modus",
                   help="warum Kandidaten nicht gekauft wurden (Protokoll)")
    p.add_argument("--stunden", type=float, default=24.0,
                   help="Zeitraum der Ablehnungsbilanz in Stunden")
    p.add_argument("--messen", action="store_const", const="messen", dest="modus",
                   help="Tiefe und Nachlauf gegen die Kostenannahmen messen")
    p.add_argument("--live", action="store_const", const="live", dest="modus")
    p.set_defaults(modus="vorschau")
    a = p.parse_args()
    return lauf(a.modus, a.stunden)


if __name__ == "__main__":
    raise SystemExit(main())
