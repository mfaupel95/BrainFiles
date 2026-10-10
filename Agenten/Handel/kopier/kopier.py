"""Die Kopier-Spur: was waere, wenn man die Trader der Pump.fun-Rangliste
nachkauft?

Sie kopiert **nichts** und sie kauft **nichts**. Sie fuehrt ein Papierbuch:
Jede NEUE Position eines verfolgten Traders (gesehen im user-portfolio,
bestaetigt ueber den letzten Kauf auf Transaktionsebene) wird zu einer
Buchzeile mit Slippage, Gebuehr und eigenen Ausstiegsgrenzen. Was am Ende
uebrig bleibt, ist die Antwort auf die Frage, ob das Nachahmen dieser Trader
nach Kosten traegt - die einzige Frage, die vor einem echten Kauf beantwortet
sein muss.

Kein Orderpfad
--------------
lesen.py kennt keine Schreibpfade - die Spur haelt keine Schluessel. Der
Waechter (SCHREIBBEFEHLE + Pfad-Whitelist) wird beim Import gegengeprueft:
Wer ihn entfernt, bekommt beim Start dieser Spur einen Fehler. `--live`
verweigert mit genau einem Grund, in dem das Wort Freigabefenster NICHT
vorkommt - so fragt der Dauerlauf keine Freigabe an, die nichts oeffnen kann.

Was ein Signal ist
------------------
Ein Signal ist eine Position, die im Portfolio eines verfolgten Traders
**neu auftaucht** und deren letzter Kauf des Vorbilds nicht aelter ist als
max_alter_signal_sekunden. Ein gehaltener Altbestand (Kauf vor Wochen) ist
kein Signal: ihn nachzukaufen waere Zuchtauswahl nach dem Ergebnis. Am Ende
jedes Zyklus wird der gesehene Bestand registriert; nur was die Tore passiert
hat, kann gebucht werden. Beim ersten Zyklus einer neuen Wallet wird deren
Bestand still uebernommen (Einlauf) - kein Kauf, nur Sicht.

Preise kommen aus den Portfolio-Snapshots (tokenPriceUsd), nicht aus einem
eigenen Abruf: der Zyklus liest das Portfolio ohnehin. Eine Kopie schliesst
sich ueber Stop, Ziel, Frist - oder wenn die Position des Vorbilds aus
dessen Portfolio verschwindet (vorbild_ausstieg, schaltbar in wachen.json).

Aufruf:
    python kopier.py --waehlen     # verfolgte.json aus dem Feed neu bauen
    python kopier.py --wachen      # Grenzen als Momentaufnahme
    python kopier.py --vorschau    # was waere dran, ohne zu schreiben
    python kopier.py --papier      # ein Papierzyklus mit Journal
    python kopier.py --bilanz      # welche Trader haben getragen
    python kopier.py --ablehnungen # warum Kandidaten NICHT gekauft wurden
    python kopier.py --messen      # Nachlauf gegen die Slippage-Annahme
    python kopier.py --live        # verweigert, nennt den Grund
"""

import argparse
import collections
import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

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
    import importlib.util
    pfad = os.path.join(HIER, os.pardir, "scanner", "wachen_pruefung.py")
    spec = importlib.util.spec_from_file_location("wachen_pruefung_quelle",
                                                  pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


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
VERFOLGTE = os.path.join(HIER, "verfolgte.json")
ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand.json"))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal.csv"))
ABLEHNUNGEN = risikostufe.datei(os.path.join(HIER, "ablehnungen.csv"))

SPALTEN = ["zeit", "modus", "aktion", "kette", "wallet", "token", "symbol",
           "preis", "menge", "einsatz_usd", "wert_usd", "marktkap_usd",
           "slippage_pct", "gebuehr_pct", "grund", "pos_id"]

# Das Ablehnungsprotokoll ist eine EIGENE Datei, nicht das Journal (die
# Leser des Journals zaehlen Zeilen als Buchungen). Schema wie bei spiegel:
#   art="zyklus"  eine Zeile je Grund und Zyklus; `anzahl` ist die Zahl.
#   art="signal"  EIN Kandidat mit Kennung (Token, Wallet) und Grund.
SPALTEN_ABLEHNUNG = ["zeit", "art", "grund", "anzahl", "kette", "wallet",
                     "token", "symbol", "marktkap_usd", "alter_s", "preis",
                     "tx"]

ABLEHNUNG_TAIL = 2000
GESEHEN = None

# Ob geschrieben wird. Die Vorschau stellt das ab (siehe journal()).
SCHREIBEN = True


# --- Sicherheitsnetz --------------------------------------------------------

class Papierfehler(RuntimeError):
    """Ein Kauf wurde aus der Papierspur heraus versucht. Das ist ein Fehler."""


def _kein_schreiben(*a, **kw):
    raise Papierfehler("Diese Spur ist papierfest: Schreibpfade sind "
                       "stillgelegt.")


if not getattr(lesen, "SCHREIBBEFEHLE", None):
    raise RuntimeError("lesen.py hat keinen Schreibschutz mehr - die "
                       "Kopier-Spur startet nicht.")


# --- Dateien ----------------------------------------------------------------

def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


def _zahl(wert):
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
    journal_ablehnung(zeit=_jetzt(), art="zyklus", grund=grund, anzahl=anzahl)


def _schluessel(felder, grund):
    """Kennung eines Kandidaten: (Wallet, Token, Grund)."""
    return (felder.get("wallet") or "", felder.get("token") or "",
            grund or "")


def _gesehen():
    """Die (wallet, token, grund)-Triple der letzten Protokollzeilen.

    Ein Kandidat steht mehrere Zyklen im Portfolio-Fenster; ohne diese Sperre
    traegt das Protokoll denselben Kandidaten alle 15 Minuten erneut ein.
    Gelesen wird nur der SCHLUSS der Datei (ABLEHNUNG_TAIL Zeilen).
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
    """EIN Kandidat mit Kennung und Grund. True, wenn die Zeile neu ist."""
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
        z = {"positionen": [], "gesehen_portfolios": {}, "letzter_lauf": None,
             "modus": "papier"}
    z.setdefault("positionen", [])
    z.setdefault("gesehen_portfolios", {})
    return z


def schreibe_zustand(z):
    if not SCHREIBEN:
        return
    z["letzter_lauf"] = _jetzt()
    schreibe(ZUSTAND, z)


def spiegeln(z, w):
    """Bedingung 4: Journal, Zustand und Ablehnungen nach journal_zweitziel.

    EINE Stelle fuer alle Pfade - auch den Notausstieg (Herzschlag alt,
    Kill-Switch). Erst schreiben, dann kopieren. In der Vorschau wird nichts
    kopiert. Rueckgabe (ok, info) wie spiegele_journal.
    """
    if not SCHREIBEN:
        return False, "Vorschau schreibt nichts"
    basis = _spiegelquelle()
    ziel = w.get("journal_zweitziel")
    ok, info = basis.spiegele_journal([JOURNAL, ZUSTAND, ABLEHNUNGEN], ziel)
    if basis.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        basis.spiegele_journal([ZUSTAND], ziel)
    return ok, info


# --- Auswahl (verfolgte.json) ----------------------------------------------

def waehlen(w):
    """Baut die Verfolgungsliste aus der taeglichen Rangliste.

    Verfolgt wird der FEED, nicht eine Handauswahl: die taegliche
    PnL-Rangliste IST das Feld der aktiven Trader. Die gemessenen Zahlen
    (Rang, PnL, Positionen) stehen daneben in verfolgte.json, damit die
    Bilanz spaeter zeigen kann, ob die Ranglistenzahlen die Kopierbarkeit
    vorhersagen - eine offene Frage, keine Annahme.
    """
    try:
        eintraege = lesen.leaderboard(periode=w.get("rangliste_periode",
                                                    "daily"),
                                      limit=w.get("anzahl_trader", 10))
    except lesen.Lesefehler as e:
        print("  Rangliste nicht abrufbar: %s" % e)
        return None

    wallets = []
    for e in eintraege:
        adresse = e.get("walletAddress")
        if not adresse:
            continue
        wallets.append({
            "wallet": adresse,
            "username": e.get("username") or "?",
            "gemessen": True,
            "rank": e.get("rank"),
            "pnl_usd": _zahl(e.get("pnlUsd")),
            "pnl_percent": _zahl(e.get("pnlPercent")),
            "positionen": e.get("positionsCount"),
            "buy_spend_sol": _zahl(e.get("buySpendSol")),
            "realisiert_usd": _zahl(e.get("realizedPnlUsd")),
            "unrealisiert_usd": _zahl(e.get("unrealizedPnlUsd")),
        })

    daten = {
        "stand": _jetzt(),
        "regel": ("Die Top %d der taeglichen Pump.fun-PnL-Rangliste. "
                  "Die Ranglistenzahlen stehen daneben, entscheiden aber "
                  "nicht: Der Einlauf uebernimmt den Bestand still, gekauft "
                  "wird nur, was der Trader JETZT neu oeffnet."
                  % w.get("anzahl_trader", 10)),
        "periode": w.get("rangliste_periode", "daily"),
        "ketten": w["ketten"],
        "wallets": wallets,
    }
    schreibe(VERFOLGTE, daten)
    print("verfolgte.json: %d Trader aus der %s-Rangliste"
          % (len(wallets), daten["periode"]))
    for x in wallets[:5]:
        print("  %2d. %-14s %10.0f USD" % (x["rank"], x["username"][:14],
                                           x["pnl_usd"] or 0))
    return daten


def _gefolgt(w):
    d = lade(VERFOLGTE, {})
    return {x["wallet"]: x for x in d.get("wallets", [])}


def verfolgte_zu_alt(w):
    """Ist die Verfolgungsliste aelter als erlaubt - oder nicht lesbar?"""
    grenze = w.get("verfolgte_max_alter_stunden", 4)
    stand = _bis_zeit((lade(VERFOLGTE, {}) or {}).get("stand"))
    if not stand:
        return True
    if stand.tzinfo is None:
        stand = stand.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - stand).total_seconds() > grenze * 3600


# --- Umfang: Papier sammelt, live gilt das Muster ---------------------------

PAPIER_UMFANG = (("max_offen", "max_offen_papier"),
                 ("kill_switch_gesamt_usd", "kill_switch_gesamt_usd_papier"))


def _umfang(w, modus):
    if modus == "live" or w.get("handel_erlaubt"):
        return w
    aus = dict(w)
    getauscht = False
    for muster, papier in PAPIER_UMFANG:
        if aus.get(papier) is not None:
            aus[muster] = aus[papier]
            getauscht = True
    return aus if getauscht else w


# --- Buch -------------------------------------------------------------------

def _kaufpreis(preis, w):
    """Was ein Nachahmer wirklich zahlt: teurer als der Vorbildkurs."""
    return preis * (1 + w["slippage_pct"] / 100.0)


def _verkaeuflich(menge, kurs, w):
    """Was am Ende ankommt: billiger, und noch einmal Gebuehr."""
    return menge * kurs * (1 - w["slippage_pct"] / 100.0) * (
        1 - w["gebuehr_pct"] / 100.0)


def _vorpruefung(sig, w, z):
    """Die billigen Tore: Kette, Marktkapitalisierung, doppelte Kopie.

    Ruft NICHTS ab - kein trades/batch, kein Coin-Abruf. Rueckgabe
    (Schluessel, Text): der Schluessel ist der gleichbleibende Name fuer die
    Zaehlung im Ablehnungsprotokoll, der Text das, was ein Mensch liest.
    """
    if sig["kette"] not in w["ketten"]:
        return "kette nicht unterstuetzt", "Kette %s wird nicht kopiert" % (
            sig.get("kette") or "unbekannt")
    mk = sig["marktkap_usd"]
    unten, oben = w["marketcap_band_usd"]
    if mk is None:
        return "marktkap unbekannt", "Marktkapitalisierung unbekannt"
    if not unten <= mk <= oben:
        return ("marktkap ausserhalb",
                "Marktkapitalisierung %.0f ausserhalb %d-%d"
                % (mk, unten, oben))
    offen = [p for p in z["positionen"] if p["token"] == sig["token"]]
    if len(offen) >= w["max_kopien_je_token"]:
        return "token belegt", "schon %d Kopien auf diesem Token" % len(offen)
    if any(p["wallet"] == sig["wallet"] and p["token"] == sig["token"]
           for p in z["positionen"]):
        return "wallet belegt", "diese Wallet steht hier schon auf diesem Token"
    return None, None


def _nein(sig, grund):
    """Die Zeile fuer einen abgelehnten Kandidaten - eine Fassung fuer beide
    Wege (Vorschau druckt, Papierlauf druckt einmal). Kein Filterwort des
    Dauerlaufs darin (verkauf, stop, KILL, gesperrt, ausstieg): eine
    Ablehnung ist keine Meldung wert. Ein Test haelt das fest.
    """
    return "  NEIN %-10s %-28s %s" % ((sig.get("symbol") or "?")[:10],
                                      sig.get("token"), grund)


def _zaehle_unerreicht(lage, rest):
    """Die Kandidaten hinter einem Abbruch: kaufbar, aber nicht mehr erreicht."""
    kaufbar = sum(1 for schluessel, _ in rest if schluessel is None)
    if kaufbar:
        lage["davon kaufbar, aber nicht mehr erreicht"] += kaufbar


def _signal_alter(sig, w, z):
    """Das Alter des Signals: letzter Kauf des Vorbilds, Transaktionsebene.

    Ein Abruf (trades/batch) - deshalb gehoert das Alter zur TEUREN Pruefung
    und nicht zu den billigen Toren. Rueckgabe (alter_s, kauf) oder
    (None, grund): grund ist der Ablehnungstext, wenn sich kein Kauf finden
    laesst (kein Trade sichtbar, Abruf fehlgeschlagen).
    """
    try:
        kaeufe = lesen.letzter_kauf(sig["token"], [sig["wallet"]])
    except lesen.Lesefehler as e:
        return None, None, "Kaufabruf nicht moeglich: %s" % e
    kauf = (kaeufe or {}).get(sig["wallet"])
    if not kauf or not kauf.get("zeit_ms"):
        return None, None, "kein Kauf des Vorbilds sichtbar"
    alter = max(0.0, time.time() - kauf["zeit_ms"] / 1000)
    return alter, kauf, None


def _kopie(sig, w, z):
    """Ein Kandidat wird zur Buchzeile - oder es gibt einen Grund, warum nicht.

    Rueckgabe (position, grund): position ist None, wenn grund gesetzt ist.
    Jeder hier gesetzte Grund gilt als ENDGUELTIG fuer diesen (wallet, token):
    der Kandidat wird registriert und nie wieder geprueft.
    """
    alter, kauf, grund = _signal_alter(sig, w, z)
    if grund:
        sig["alter_s"] = None
        return None, grund
    sig["alter_s"] = alter
    if alter is not None and alter > w["max_alter_signal_sekunden"]:
        # Die genaue Zahl steht in der Ablehnungszeile; als Grund reicht der
        # kurze Name fuer die Zaehlung.
        return None, "zu alt"
    sig["tx"] = (kauf or {}).get("tx")
    sig["vorbild_kurs"] = (kauf or {}).get("preis") or sig["preis"]

    if w["risiko_pflicht"]:
        try:
            r = lesen.risiko(sig["token"])
        except lesen.Lesefehler as e:
            return None, "Risikopruefung nicht moeglich: %s" % e
        if r["stufe"] not in w["max_risiko_stufen"]:
            return None, "Risikostufe %s (%s)" % (r["stufe"],
                                                  ",".join(r["merkmale"][:3]))
    else:
        r = {"stufe": "ungeprueft", "merkmale": []}

    einsatz = w["max_einsatz_je_kopie_usd"]
    kaufpreis = _kaufpreis(sig["preis"], w)
    gebuehr = einsatz * w["gebuehr_pct"] / 100.0
    menge = (einsatz - gebuehr) / kaufpreis
    return {
        "kette": sig["kette"], "wallet": sig["wallet"],
        "wallet_name": sig.get("wallet_name") or sig["wallet"],
        "token": sig["token"], "symbol": sig["symbol"],
        "quelle": sig["quelle"], "einsatz_usd": einsatz, "menge": menge,
        "preis_vorbild": sig["vorbild_kurs"], "preis_einstieg": kaufpreis,
        "marktkap_usd": sig["marktkap_usd"], "risiko": r["stufe"],
        "stop_usd": w.get("stop_usd"),
        "stop_preis": kaufpreis * (1 - w["stop_pct"] / 100.0),
        # Seit 15.09.2026 kein festes Ziel mehr: Trailing-Stop, damit
        # theoretische 10x/100x laufen koennen (siehe wachen.json, _ausstieg).
        "trail_aktiv_ab_pct": w["trail_aktiv_ab_pct"],
        "trail_abstand_pct": w["trail_abstand_pct"],
        "hoechster_kurs": kaufpreis,
        "frist": _plus_stunden(w["haltedauer_stunden"]),
        "letzter_kurs": sig["preis"],
        "eroeffnet": _heute(), "eroeffnet_zeit": _jetzt(),
        "pos_id": pos_kennung.neu(_jetzt()),
    }, None


def _plus_stunden(stunden):
    return (datetime.now(timezone.utc)
            + timedelta(hours=stunden)).isoformat(timespec="seconds")


def _lokal(wert):
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
    journal(zeit=_jetzt(), modus="papier", aktion="eroeffnen",
            kette=p["kette"], wallet=p["wallet"], token=p["token"],
            symbol=p["symbol"], preis="%.10g" % p["preis_einstieg"],
            menge="%.6f" % p["menge"], einsatz_usd="%.2f" % p["einsatz_usd"],
            marktkap_usd="%.0f" % p["marktkap_usd"],
            slippage_pct=w["slippage_pct"], gebuehr_pct=w["gebuehr_pct"],
            grund="kopie", pos_id=p["pos_id"])
    return None


def pruefe_vorbild_ausstiege(z, sicht, w):
    """Kopien schliessen, deren Position der Vorbild-Trader gerade beendet hat.

    follow_ausstieg in wachen.json schaltet das. Geschlossen wird zum letzten
    beobachteten Kurs (der Portfoliostand dieses Zyklus ist die Wahrheit,
    die wir kennen) - der Kurs des Vorbild-Ausstiegs laege ausserhalb unserer
    Beobachtung.
    """
    if not w.get("follow_ausstieg", True) or not z["positionen"]:
        return
    behalten = []
    for p in z["positionen"]:
        sicht_wallet = sicht.get(p["wallet"])
        if sicht_wallet is not None and p["token"] not in sicht_wallet:
            kurs = p.get("letzter_kurs")
            if not kurs:
                print("  %-10s %-28s Vorbild ausgestiegen, aber kein Kurs "
                      "bekannt - Kopie bleibt" % (p["symbol"], p["token"]))
                behalten.append(p)
                continue
            erloes = _verkaeuflich(p["menge"], kurs, w)
            print("  AUSSTIEG (vorbild_ausstieg)%s: %s %s @ %.10g  "
                  "G/V %+.2f USD auf %.0f USD"
                  % ("" if SCHREIBEN else " [nur Vorschau]", p["symbol"],
                     p["token"], kurs, erloes - p["einsatz_usd"],
                     p["einsatz_usd"]))
            journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                    kette=p["kette"], wallet=p["wallet"], token=p["token"],
                    symbol=p["symbol"], preis="%.10g" % kurs,
                    menge="%.6f" % p["menge"],
                    einsatz_usd="%.2f" % p["einsatz_usd"],
                    wert_usd="%.2f" % erloes, grund="vorbild_ausstieg",
                    pos_id=p.get("pos_id", ""))
            continue
        behalten.append(p)
    z["positionen"] = behalten


def _ausstiegsgrund(p, kurs, jetzt, w):
    """Der Ausstiegsgrund einer Kopie - EINE Stelle fuer alt und neu.

    Reihenfolge: zuerst der harte Stop (Schaden begrenzen), dann Ziel oder
    Trailing, dann die Frist. Neue Kopien (ab 15.09.2026) tragen die
    Trailing-Felder: sobald der Kurs trail_aktiv_ab_pct ueber dem Einstieg
    lag, haengt der Ausstieg trail_abstand_pct unter dem hoechsten seither
    beobachteten Kurs - kein festes Ziel, ein 10x/100x laeuft weiter.
    Altbestand (ohne die Felder) laeuft unter stop/ziel/frist aus. Ein
    gerissener Stop schliesst zum BEOBACHTETEN Kurs, nicht zum Stop-Preis.
    """
    if p.get("stop_usd") is not None:
        # Ausstiegsform 15.09.2026 (Max): Stop als Verlust in USD, keine
        # Prozent. Bei Pump.fun-Volatilitaet fliegen Prozent-Stops zu frueh.
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
    """Stop, Trailing, Frist - gemessen am letzten beobachteten Kurs."""
    offen = z["positionen"]
    if not offen:
        return
    behalten, jetzt = [], datetime.now(timezone.utc)
    for p in offen:
        kurs = p.get("letzter_kurs")
        if not kurs:
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
              % (grund, "" if SCHREIBEN else " [nur Vorschau]",
                 p["symbol"], p["token"], kurs, erloes - p["einsatz_usd"],
                 p["einsatz_usd"]))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                kette=p["kette"], wallet=p["wallet"], token=p["token"],
                symbol=p["symbol"], preis="%.10g" % kurs,
                menge="%.6f" % p["menge"], einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes, grund=grund,
                pos_id=p.get("pos_id", ""))
    z["positionen"] = behalten


def kill_switch(z, w):
    """Ruecklauf des Buches gegen die Grenze: dann alles flach."""
    if not z["positionen"]:
        return False
    wert = einsatz = 0.0
    gesehen = 0
    for p in z["positionen"]:
        kurs = p.get("letzter_kurs")
        if not kurs:
            continue
        gesehen += 1
        wert += _verkaeuflich(p["menge"], kurs, w)
        einsatz += p["einsatz_usd"]
    if gesehen == 0 or wert - einsatz > -w["kill_switch_gesamt_usd"]:
        return False
    print("- Kill-Schwelle erreicht (%+.2f USD) -> alle Kopien zu -"
          % (wert - einsatz))
    return True


def flach_stellen(z, w, grund):
    for p in list(z["positionen"]):
        kurs = p.get("letzter_kurs")
        erloes = _verkaeuflich(p["menge"], kurs, w) if kurs else 0.0
        print("  AUSSTIEG (%s): %s %s  G/V %+.2f USD"
              % (grund, p["symbol"], p["token"], erloes - p["einsatz_usd"]))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                kette=p["kette"], wallet=p["wallet"], token=p["token"],
                symbol=p["symbol"], preis="" if not kurs else "%.10g" % kurs,
                menge="%.6f" % p["menge"], einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes, grund=grund,
                pos_id=p.get("pos_id", ""))
    z["positionen"] = []


# --- Bilanz ----------------------------------------------------------------

def bilanz(w):
    """Welche Trader haben getragen - und luegen die Ranglistenzahlen?"""
    if not os.path.exists(JOURNAL):
        print("Noch keine Buchzeile - kein Journal.")
        return
    gefolgt = _gefolgt(w)
    je_wallet = {}
    with open(JOURNAL, newline="", encoding="utf-8") as f:
        for zeile in csv.DictReader(f):
            wallet = zeile["wallet"]
            if zeile["aktion"] == "eroeffnen":
                continue
            einsatz = int(float(zeile["einsatz_usd"] or 0) * 100)
            wert = int(float(zeile["wert_usd"] or 0) * 100)
            e = je_wallet.setdefault(wallet, {"runden": 0, "gv": 0,
                                              "symbole": set()})
            e["runden"] += 1
            e["gv"] += wert - einsatz
            e["symbole"].add(zeile["symbol"])
    if not je_wallet:
        print("Keine abgeschlossene Kopie im Journal.")
        return
    print("Bilanz aus %d abgeschlossenen Kopien (Zahlen in USD):" % sum(
        e["runden"] for e in je_wallet.values()))
    for wallet, e in sorted(je_wallet.items(), key=lambda x: -x[1]["gv"]):
        z = gefolgt.get(wallet, {})
        zahlen = ("Rang %s, PnL %s USD" % (z.get("rank"), z.get("pnl_usd"))
                  if z.get("gemessen") else "nicht in der Rangliste")
        name = z.get("username") or wallet[:8]
        print("  %-16s %-44s %3d Runden  G/V %+8.2f  (%s)"
              % (name, wallet, e["runden"], e["gv"] / 100.0, zahlen))


# --- Ablehnungs-Bilanz ------------------------------------------------------

def ablehnungsbilanz(stunden=24.0):
    """Was das Ablehnungsprotokoll hergibt - lesend, ohne Netz.

    Zwei Aussagen, getrennt: die LAGE (was die Zyklen an Kandidaten
    mitbrachten und woran sie haengen blieben) und die ENTSCHEIDUNG (was das
    Buch mit den bewerteten Kandidaten getan hat). Die Kontrollzeile am Ende
    haelt die beiden Seiten zusammen: kaufbar = bewertet + nicht erreicht.
    """
    if not os.path.exists(ABLEHNUNGEN):
        print("Noch kein Ablehnungsprotokoll: %s" % ABLEHNUNGEN)
        print("Es entsteht im ersten Papierzyklus - die Vorschau schreibt "
              "nichts.")
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

    print("=== Kopier: Ablehnungsprotokoll ===")
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
        print("Einzelne Kandidaten: keine - kein Signal kam bis zur "
              "teuren Pruefung.")
    print()
    kaufbar = lage.get("kaufbar", 0)
    nicht_erreicht = lage.get("davon kaufbar, aber nicht mehr erreicht", 0)
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


# --- Lauf -------------------------------------------------------------------

def zeige_wachen(w):
    print("Grenzen der Kopier-Spur (Papier):")
    for name in ("ketten", "anzahl_trader", "rangliste_periode",
                 "max_einsatz_je_kopie_usd", "max_offen", "max_neu_je_zyklus",
                 "max_signale_je_zyklus", "max_kopien_je_token",
                 "kill_switch_gesamt_usd", "slippage_pct", "gebuehr_pct",
                 "stop_pct", "trail_aktiv_ab_pct", "trail_abstand_pct",
                 "haltedauer_stunden", "follow_ausstieg",
                 "max_alter_signal_sekunden", "marketcap_band_usd",
                 "max_risiko_stufen", "herzschlag_max_minuten",
                 "max_offen_papier", "kill_switch_gesamt_usd_papier",
                 "verfolgte_max_alter_stunden"):
        print("  %-30s %s" % (name, w.get(name)))
    print("  %-30s %s" % ("handel_erlaubt", w.get("handel_erlaubt")))
    w2 = _umfang(w, "papier")
    print("  %-30s %s" % ("Umfang gilt jetzt",
                          "Papier" if w2 is not w else "Muster (live)"))
    z = lade_zustand()
    print("  %-30s %s" % ("journal_zweitziel",
                          w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  %-30s %s (%s)" % ("letzte Kopie", z.get("journal_zweitziel_ok"),
                               z.get("journal_zweitziel_info")))


def sicht_lesen(w, gefolgt, z):
    """Die Portfolios aller zu lesenden Wallets - die Sicht auf den Feed.

    Gelesen werden die verfolgten Trader PLUS die Wallets offener Kopien
    (eine Wallet, die aus der Rangliste faellt, muss ihre Kopien weiter
    mit Preisen versorgen duerfen). Rueckgabe: {wallet: {mint: position}}.
    """
    wallets = list(gefolgt)
    for p in z["positionen"]:
        if p["wallet"] not in wallets:
            wallets.append(p["wallet"])
    sicht = {}
    for wallet in wallets:
        try:
            pf = lesen.portfolio(wallet)
        except lesen.Lesefehler as e:
            print("  Portfolio %s nicht abrufbar: %s" % (wallet[:14], e))
            continue
        sicht[wallet] = {mint: po for mint, po in pf["positions"].items()
                         if not po["is_exited"] and not po["dust"]
                         and not po["vermutlich_verloren"]}
    return sicht


def signale_sammeln(w, sicht, gefolgt, z):
    """Der Diff: welche Positionen sind NEU im Portfolio-Fenster.

    Rueckgabe (kandidaten, einlauf): einlauf ist die Zahl der Positionen,
    die beim ERSTEN Kontakt mit einer Wallet still uebernommen wurden (kein
    Kauf - hinterherlaufende Ersteinrichtung waere Zuchtauswahl). Fuer die
    uebrigen ist jede Position ein Kandidat, solange sie nicht registriert
    ist; das Alter entscheidet die teure Pruefung.
    """
    kandidaten, einlauf = [], 0
    for wallet, pos_map in sicht.items():
        eintrag = gefolgt.get(wallet, {})
        name = eintrag.get("username") or wallet[:8]
        alt = z["gesehen_portfolios"].get(wallet)
        for mint, po in pos_map.items():
            if alt is None:
                einlauf += 1
                continue
            if mint in alt:
                continue
            kandidaten.append({
                "quelle": "portfolio/%s" % name,
                "wallet_name": name,
                "kette": po["kette"],
                "wallet": wallet,
                "token": mint,
                "symbol": po["symbol"] or "?",
                "preis": po["preis"],
                "marktkap_usd": po["marktkap_usd"],
                "alter_s": None,
                "tx": None,
                "vorbild_kurs": None,
            })
    return kandidaten, einlauf


def registriere_sicht(z, sicht, ausgenommen):
    """Den gesehenen Bestand auf die aktuelle Sicht bringen.

    Jeder Kandidat, der bewertet oder still uebernommen wurde, ist damit
    registriert; ausgenommen sind die, die an Kapazitaet scheiterten (Buch
    voll, Zyklusdeckel, Bewertungsdeckel) - die sollen im naechsten Zyklus
    wieder Kandidat sein duerfen, solange ihre Position noch frisch ist.
    """
    gesehen = {}
    for wallet, pos_map in sicht.items():
        gesehen[wallet] = {}
        for mint, po in pos_map.items():
            if (wallet, mint) in ausgenommen:
                continue
            alt = z["gesehen_portfolios"].get(wallet, {}).get(mint)
            gesehen[wallet][mint] = {
                "seit": (alt or {}).get("seit") or _jetzt(),
                "letzter_kurs": po["preis"],
            }
    z["gesehen_portfolios"] = gesehen


def lade_wachen():
    """Wachen dieser Spur samt Risikostufe.

    Der Faktor gehoert an EINE Stelle, nicht in `lauf()`: so kann ein Test
    dieselbe Funktion befragen, die der Betrieb benutzt (sonst prueft der
    Test eine Nachbildung).
    """
    return risikostufe.skaliere(lade(WACHEN, None))


def lauf(modus, stunden=24.0, stichprobe=40, nur_bestand=False):
    global SCHREIBEN, GESEHEN
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    SCHREIBEN = modus != "vorschau"
    GESEHEN = None

    w = lade_wachen()
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
        return messen(w, lade_zustand(), stichprobe, nur_bestand=nur_bestand)

    roh = w
    w = _umfang(w, modus)
    if w is not roh:
        print("  Umfang: Papier - %d Plaetze, Notbremse %.0f USD "
              "(Muster fuer live: %d Plaetze, %.0f USD)"
              % (w["max_offen"], w["kill_switch_gesamt_usd"],
                 roh["max_offen"], roh["kill_switch_gesamt_usd"]))

    z = lade_zustand()

    if modus == "live":
        print("--live angefordert, aber gesperrt: kein Live-Pfad in dieser "
              "Spur (Papier)")
        print("-> es wird Papier gebucht.")

    if z["positionen"] and not _frisch(z, w):
        print("- Herzschlag alt (%s) -> alle Kopien zu, kein Neuerwerb "
              "dieser Lauf -" % z.get("letzter_lauf"))
        flach_stellen(z, w, "herzschlag_alt")
        schreibe_zustand(z)
        spiegeln(z, w)
        return 0

    if SCHREIBEN and verfolgte_zu_alt(w):
        print("  Verfolgungsliste aelter als %s h - wird aus dem Feed neu "
              "gebaut" % w.get("verfolgte_max_alter_stunden", 4))
        waehlen(w)
        print("  Rueckkehr zum Zyklus")
    gefolgt = _gefolgt(w)
    if not gefolgt:
        print("verfolgte.json ist leer - erst '--waehlen' laufen lassen.")
        return 1

    # 1) Sicht: die Portfolios aller zu lesenden Wallets.
    sicht = sicht_lesen(w, gefolgt, z)
    if not sicht:
        print("  Kein Portfolio lesbar - Zyklus ohne Buchung (Stand bleibt).")
        schreibe_zustand(z)
        spiegeln(z, w)
        return 0

    # 2) Preise fuers Buch: letzter beobachteter Kurs je offener Kopie.
    for p in z["positionen"]:
        po = sicht.get(p["wallet"], {}).get(p["token"])
        if po and po["preis"]:
            p["letzter_kurs"] = po["preis"]

    # 3) Ausstiege zuerst: Platz wird frei, bevor neue Kopien bewertet werden.
    pruefe_vorbild_ausstiege(z, sicht, w)
    pruefe_ausstiege(z, w)
    if kill_switch(z, w):
        flach_stellen(z, w, "kill_switch")
        schreibe_zustand(z)
        spiegeln(z, w)
        return 0

    # 4) Kandidaten: der Diff gegen den registrierten Bestand.
    kandidaten, einlauf = signale_sammeln(w, sicht, gefolgt, z)
    if einlauf:
        protokolliere("Lage: Einlauf - Bestand still uebernommen", einlauf)
        print("  Einlauf: %d Positionen uebernommen (kein Kauf im ersten "
              "Zyklus einer Wallet)" % einlauf)

    vorpruefung = [_vorpruefung(s, w, z) for s in kandidaten]
    lage = collections.Counter(g or "kaufbar" for g, _ in vorpruefung)
    entscheidung = collections.Counter()
    neu = bewertet = 0
    # Nicht registriert werden nur die Kandidaten, die an KAPAZITAET
    # scheiterten (Buch voll, Zyklusdeckel, Bewertungsdeckel): ihre Position
    # ist deshalb nicht 'gesehen' und darf im naechsten Zyklus wieder
    # Kandidat sein, solange sie noch frisch ist. Jede andere Entscheidung
    # (billiges Tor, zu alt, Risiko, gekauft) ist endgueltig fuer
    # (wallet, token) - sie wird registriert, sonst traegt das Protokoll
    # denselben Kandidaten jeden Zyklus erneut ein, und die Zaehlung waere
    # ein Vielfaches der Wahrheit.
    unbearbeitet = []
    for i, s in enumerate(kandidaten):
        if len(z["positionen"]) >= w["max_offen"]:
            print("  Buch voll (%d Kopien) - Rest faellt aus" % w["max_offen"])
            entscheidung["Buch voll - Kandidat nicht bewertet"] += 1
            unbearbeitet = [(s2["wallet"], s2["token"])
                            for s2 in kandidaten[i:]]
            _zaehle_unerreicht(lage, vorpruefung[i:])
            break
        if neu >= w["max_neu_je_zyklus"]:
            print("  Zyklusdeckel erreicht (%d neue Kopien)"
                  % w["max_neu_je_zyklus"])
            entscheidung["Zyklusdeckel - Kandidat nicht bewertet"] += 1
            unbearbeitet = [(s2["wallet"], s2["token"])
                            for s2 in kandidaten[i:]]
            _zaehle_unerreicht(lage, vorpruefung[i:])
            break
        if bewertet >= w.get("max_signale_je_zyklus", 30):
            print("  Bewertungsdeckel erreicht (%d teure Pruefungen)"
                  % w.get("max_signale_je_zyklus", 30))
            entscheidung["Bewertungsdeckel - Kandidat nicht bewertet"] += 1
            unbearbeitet = [(s2["wallet"], s2["token"])
                            for s2 in kandidaten[i:]]
            _zaehle_unerreicht(lage, vorpruefung[i:])
            break
        if vorpruefung[i][0] is not None:
            # Billiges Tor: steht als Zahl in der Lage, keine Einzelzeile.
            # Endgueltig - siehe oben: wird registriert.
            continue
        if modus == "vorschau":
            p, grund = _kopie(s, w, z)
            print("  WAERE %-10s %-28s %d USD"
                  % (s["symbol"][:10], s["token"],
                     w["max_einsatz_je_kopie_usd"]) if p else _nein(s, grund))
            if p:
                bewertet += 1
                neu += 1
                z["positionen"].append(p)      # nur im Speicher
            else:
                entscheidung[grund] += 1
            continue
        bewertet += 1
        grund = eroeffne(z, s, w)
        if grund is None:
            neu += 1
            entscheidung["kopiert"] += 1
            continue
        entscheidung[grund] += 1
        if protokolliere_signal(s, grund):
            print(_nein(s, grund))

    registriere_sicht(z, sicht, set(unbearbeitet))

    if SCHREIBEN:
        protokolliere("Signale gesehen", len(kandidaten))
        for name, anzahl in sorted(lage.items()):
            protokolliere("Lage: %s" % name, anzahl)
        for name, anzahl in sorted(entscheidung.items()):
            protokolliere("Entscheidung: %s" % name, anzahl)

    print("=== Kopier (PAPIER%s) | %d Kandidaten, %d verfolgte Trader | "
          "%d Kopien offen, %d neu, %d bewertet ==="
          % ("" if modus != "vorschau" else ", Vorschau", len(kandidaten),
             len(gefolgt), len(z["positionen"]), neu, bewertet))
    if modus == "vorschau":
        print("Live waere gesperrt durch: kein Live-Pfad in dieser Spur "
              "(Papier)")
        return 0
    schreibe_zustand(z)
    ok, info = spiegeln(z, w)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))
    return 0


def _bestand_als_stichprobe(w, sicht, z, grenze):
    """Der Bestand der verfolgten Trader als Messstichprobe.

    Der Diff liefert nur etwas zu messen, wenn ein Vorbild GERADE neu gekauft
    hat - der Nachlauf ist aber an JEDER gehaltenen Position ablesbar. Ohne
    diesen Rueckfall ist die Messung nur an manchen Tagen fahrbar und die
    Annahme bleibt ungeprueft (Regel 8 der Tor-Kalibrierung). Genommen werden
    die Positionen im Marktkap-Band, je Token nur EINE Wallet (die mit dem
    groessten Wert - sonst steht dasselbe Token mehrfach in der Stichprobe),
    hoechstens `grenze` Stueck nach Wert sortiert.
    """
    band = w.get("marketcap_band_usd") or [0, 10 ** 12]
    je_token = {}
    for wallet, positionen in (sicht or {}).items():
        for mint, po in positionen.items():
            if not po.get("preis"):
                continue
            kap = po.get("marktkap_usd") or 0
            if not (band[0] <= kap <= band[1]):
                continue
            wert = po.get("wert_usd") or 0
            alt = je_token.get(mint)
            if alt is None or wert > alt["wert_usd"]:
                je_token[mint] = {"wallet": wallet, "token": mint,
                                  "symbol": po.get("symbol") or "?",
                                  "preis": po["preis"], "wert_usd": wert}
    return sorted(je_token.values(), key=lambda s: -s["wert_usd"])[:grenze]


def _verteilung(werte):
    """min, p10, p25, Median, p75, max und Schnitt - die Verteilung, nicht nur
    ein Mittelwert. Ein Mittelwert allein verdeckt genau das, was hier zaehlt:
    die wenigen weit weggelaufenen Positionen."""
    werte = sorted(werte)
    if not werte:
        return None

    def q(anteil):
        # Lineare Interpolation: der Median zweier mittlerer Werte ist ihr
        # Mittel, nicht der obere von beiden (sonst verschiebt sich die Zahl
        # bei gerader Anzahl nach oben und die Dokumentation dazu passt nicht).
        x = anteil * (len(werte) - 1)
        unten = int(x)
        oben = min(len(werte) - 1, unten + 1)
        rest = x - unten
        return werte[unten] * (1 - rest) + werte[oben] * rest
    return {"n": len(werte), "min": werte[0], "p10": q(0.10), "p25": q(0.25),
            "median": q(0.50), "p75": q(0.75), "max": werte[-1],
            "schnitt": sum(werte) / len(werte)}


def _kauf_mit_geduld(s, versuche=3, pause_s=6.0):
    """trades/batch mit Geduld - die API antwortet bei zu vielen Abrufen 429.

    Die Spur teilt sich diesen Zugang mit dem laufenden Zyklus (10 Wallets,
    jeder Zyklus ein Abruf je Token). Eine Messung darf ihn nicht zustellen,
    und ein 429 ist kein Messwert, sondern eine Absage: er wird wiederholt,
    nicht als Zahl gebucht.
    """
    letzter = None
    for n in range(versuche):
        try:
            kaeufe = lesen.letzter_kauf(s["token"], [s["wallet"]])
            return (kaeufe or {}).get(s["wallet"])
        except lesen.Lesefehler as e:
            letzter = e
            if "429" not in str(e):
                break
            time.sleep(pause_s * (n + 1))
    raise letzter


def messen(w, z, stichprobe=40, pause_s=2.0, nur_bestand=False):
    """Den Nachlauf gegen die Slippage-Annahme halten.

    Nachlauf = wie weit der Kurs schon weg ist von dem, was der Trader
    bezahlt hat - die eigentliche Strafe beim Nachahmen. Gemessen an den
    Kandidaten des Diff: aktueller Portfoliokurs gegen den letzten Kauf des
    Vorbilds aus trades/batch. Gibt die Verteilung aus und schreibt sie nach
    daten/messung.json - das Buch wird nicht angefasst.

    Hat der Diff nichts Frisches (Normalfall an ruhigen Tagen), wird ueber
    den BESTAND gemessen (_bestand_als_stichprobe) - sonst waere die Messung
    nicht wiederholbar und die Annahme bliebe fuer immer ungeprueft.
    `nur_bestand=True` erzwingt diese breitere Stichprobe.

    GEMESSEN 01.10.2026: Die Kandidaten des Diff tragen haeufig KEINEN
    sichtbaren Kauf - trades/batch liefert nur die letzten 50 Trades, und bei
    einem Vorbild, das gerade verkauft, stehen dort nur Verkaeufe. Deshalb ist
    der Bestand die verlaesslichere Stichprobe und die Zahlen werden gezaehlt
    statt still uebersprungen.
    """
    gefolgt = _gefolgt(w)
    if not gefolgt:
        print("verfolgte.json ist leer - erst '--waehlen' laufen lassen.")
        return 1
    sicht = sicht_lesen(w, gefolgt, z)
    kandidaten, _ = signale_sammeln(w, sicht, gefolgt, z)
    herkunft = "frische Kandidaten des Diff"
    if nur_bestand:
        kandidaten = []
    if not kandidaten:
        kandidaten = _bestand_als_stichprobe(w, sicht, z, stichprobe)
        herkunft = ("Bestand der verfolgten Trader (%s - dieselbe Rechnung, "
                    "breitere Stichprobe)" % ("erzwungen" if nur_bestand
                                              else "der Diff hatte nichts Frisches"))
        if not kandidaten:
            print("Weder frische Kandidaten noch ein Bestand im Marktkap-Band - "
                  "nichts zu messen. Der Einlauf des ersten Zyklus zaehlt nicht "
                  "als Messung.")
            return 1
        print("  Gemessen wird ueber den Bestand (%d Positionen im Band)."
              % len(kandidaten))

    zeilen = []
    ohne_kauf = 0
    fehler = 0
    geprueft = 0
    # Bis zu dreimal so viele Kandidaten ansehen, wie gebraucht werden: bei
    # stark gehandelten Tokens stehen in den letzten 50 Trades nur Verkaeufe,
    # ein Kauf ist dann nicht sichtbar. Das ist ein Ergebnis, keine Stille -
    # es wird gezaehlt und ausgegeben (Regel 6 der Tor-Kalibrierung).
    for s in kandidaten[:stichprobe * 3]:
        if len(zeilen) >= stichprobe:
            break
        if geprueft:
            time.sleep(pause_s)          # Hoeflichkeit gegenueber dem Zyklus
        geprueft += 1
        try:
            kauf = _kauf_mit_geduld(s)
        except lesen.Lesefehler as e:
            fehler += 1
            print("  %s: kein Kaufabruf (%s)" % (s["token"][:12], e))
            continue
        if not kauf or not kauf.get("preis") or not s["preis"]:
            ohne_kauf += 1
            continue
        nachlauf = (s["preis"] / kauf["preis"] - 1) * 100
        zeilen.append({"wallet": s["wallet"], "token": s["token"],
                       "symbol": s["symbol"], "preis_jetzt": s["preis"],
                       "preis_vorbild": kauf["preis"],
                       "nachlauf_pct": nachlauf,
                       "alter_s": (None if not kauf.get("zeit_ms") else max(
                           0.0, time.time() - kauf["zeit_ms"] / 1000))})
        print("  %-10s %-9s Vorbild %10.6g  jetzt %10.6g  Nachlauf %+8.2f%%"
              % (s["symbol"][:10], s["wallet"][:8], kauf["preis"],
                 s["preis"], nachlauf))
    if not zeilen:
        print("  Keine messbare Kandidatenkette - nichts geschrieben.")
        print("  Geprueft %d Kandidaten: %d ohne sichtbaren Kauf in den letzten "
              "50 Trades, %d Abrufe gescheitert." % (geprueft, ohne_kauf, fehler))
        return 1

    v = _verteilung([x["nachlauf_pct"] for x in zeilen])
    print()
    print("  Stichprobe: %s" % herkunft)
    print("  Geprueft %d Kandidaten: %d verwertet, %d ohne sichtbaren Kauf in "
          "den letzten 50 Trades, %d Abrufe gescheitert."
          % (geprueft, len(zeilen), ohne_kauf, fehler))
    print("  Nachlauf (n=%d)  min %+.2f%%  p25 %+.2f%%  Median %+.2f%%  "
          "p75 %+.2f%%  max %+.2f%%  Schnitt %+.2f%%"
          % (v["n"], v["min"], v["p25"], v["median"], v["p75"], v["max"],
             v["schnitt"]))
    print("  Annahme in wachen.json: %.1f%% Slippage + %.1f%% Gebuehr je Seite"
          % (w["slippage_pct"], w["gebuehr_pct"]))

    # Nachlauf waechst mit dem Abstand zwischen Signal und eigenem Kauf - das
    # ist der Posten, den ein Nachahmer wirklich verliert (Regel 8). Nach
    # Signalalter getrennt ausweisen, sonst verdeckt der Schnitt den Trend.
    alter_toepfe = [("<= 5 min", 0, 300), ("5-30 min", 300, 1800),
                    ("30-120 min", 1800, 7200), ("> 2 h", 7200, 10 ** 9)]
    print("  Nach Signalalter:")
    for name, von, bis in alter_toepfe:
        teil = [x["nachlauf_pct"] for x in zeilen
                if x["alter_s"] is not None and von <= x["alter_s"] < bis]
        if teil:
            print("    %-11s n=%-3d Median %+.2f%%  Schnitt %+.2f%%"
                  % (name, len(teil), _verteilung(teil)["median"],
                     _verteilung(teil)["schnitt"]))

    ordner = os.path.join(HIER, "daten")
    os.makedirs(ordner, exist_ok=True)
    with open(os.path.join(ordner, "messung.json"), "w",
              encoding="utf-8") as f:
        json.dump({"zeit": _jetzt(), "stichprobe": herkunft,
                   "annahme_slippage_pct": w["slippage_pct"],
                   "annahme_gebuehr_pct": w["gebuehr_pct"],
                   "verteilung": v, "werte": zeilen}, f, indent=2,
                  ensure_ascii=False)
    return 0


def _frisch(z, w):
    letzte = _bis_zeit(z.get("letzter_lauf"))
    if not letzte:
        return False
    grenze = w.get("herzschlag_max_minuten", 180)
    return (datetime.now(timezone.utc) - letzte).total_seconds() <= grenze * 60


def main():
    with ereignis.lauf("handel/kopier"):
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
                   help="Nachlauf gegen die Slippage-Annahme messen")
    p.add_argument("--stichprobe", type=int, default=40,
                   help="wie viele Positionen die Nachlauf-Messung hoechstens "
                        "abfragt (je Position ein trades/batch-Abruf)")
    p.add_argument("--bestand", action="store_true",
                   help="die Nachlauf-Messung ueber den Bestand der verfolgten "
                        "Trader fahren statt ueber den Diff (breitere Stichprobe)")
    p.add_argument("--live", action="store_const", const="live", dest="modus")
    p.set_defaults(modus="vorschau")
    a = p.parse_args()
    return lauf(a.modus, a.stunden, a.stichprobe, a.bestand)


if __name__ == "__main__":
    raise SystemExit(main())