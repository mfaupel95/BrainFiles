"""Die 1:1-Copy-Trade-Spur: Trader der Pump.fun-Rangliste auf TRADE-Ebene
nachmachen.

Anders als kopier/ arbeitet diese Spur auf trades/batch statt auf einem
Portfolio-Diff:

- Jeder KAUF-Trade eines verfolgten Traders (typ='buy' aus trades/batch),
  der neuer ist als max_alter_trade_sekunden und noch nicht gesehen wurde,
  oeffnet eine Papier-Position zum Vorbild-Kurs (mit Slippage + Gebuehr).
- Jeder VERKAUF-Trade (typ='sell') derselben Wallet auf demselben Token,
  der nach dem eigenen Einstieg liegt, schliesst ALLE offenen Kopien
  dieser (wallet, token) zum LETZTEN beobachteten Kurs (Portfolio-Preis).
  Kein Wunschdenken: der Verkauf des Vorbilds ist ein Ereignis, kein
  Preis-Signal - der eigene Ausstieg trifft den echten Kurs zum Zyklus.

Kein Orderpfad
--------------
Diese Spur teilt lesen.py mit kopier/ (per Import-Verweis auf
kopier/lesen.py) - der Waechter dort (Schreibwortliste + Pfad-Whitelist)
laesst keine Schreibpfade durch. `--live` verweigert mit einem Grund, in
dem das Wort Freigabefenster NICHT vorkommt.

Aufruf:
    python handeln.py --wachen      # Grenzen als Momentaufnahme
    python handeln.py --vorschau    # was waere dran, ohne zu schreiben
    python handeln.py --papier      # ein Papierzyklus mit Journal
    python handeln.py --bilanz      # welche Trader haben getragen
    python handeln.py --ablehnungen # warum Trades nicht gebucht wurden
    python handeln.py --live        # verweigert, nennt den Grund
"""

import argparse
import collections
import csv
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
KOPIER = os.path.join(HIER, os.pardir, "kopier")
BUS = os.path.join(HIER, os.pardir, os.pardir, "Bus")
for p in (HIER, KOPIER, BUS):
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
import ereignis                                                  # noqa: E402
import lesen                                                     # noqa: E402


def _spiegelquelle():
    """scanner/wachen_pruefung.py per Dateipfad laden (wie kopier).

    Nicht ueber sys.path: scanner/ enthaelt okx.py, scan.py und handeln.py,
    die in dieser Spur fremde Namen verdecken koennen. Die Datei braucht
    nur die Standardbibliothek.
    """
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
VERFOLGTE_KOPIER = os.path.join(KOPIER, "verfolgte.json")
ZUSTAND = risikostufe.datei(os.path.join(HIER, "zustand.json"))
JOURNAL = risikostufe.datei(os.path.join(HIER, "handelsjournal.csv"))
ABLEHNUNGEN = risikostufe.datei(os.path.join(HIER, "ablehnungen.csv"))

SPALTEN = ["zeit", "modus", "aktion", "kette", "wallet", "wallet_name",
           "token", "symbol", "tx", "trade_zeit",
           "preis_vorbild", "preis_einstieg", "kurs_ausstieg",
           "menge", "einsatz_usd", "wert_usd", "marktkap_usd",
           "slippage_pct", "gebuehr_pct", "grund", "pos_id"]

SPALTEN_ABLEHNUNG = ["zeit", "art", "grund", "anzahl", "kette", "wallet",
                     "token", "symbol", "marktkap_usd", "alter_s", "preis",
                     "tx"]

# Wie kopier: die letzten 2000 Zeilen der Ablehnungen sind unser Gedaechtnis
# gegen doppelte Signal-Zeilen im selben Zyklus.
ABLEHNUNG_TAIL = 2000
GESEHEN = None

# Ob geschrieben wird. Vorschau stellt das ab (siehe journal()).
SCHREIBEN = True


class Papierfehler(RuntimeError):
    """Ein Kauf wurde aus der Papierspur heraus versucht."""


if not getattr(lesen, "SCHREIBBEFEHLE", None):
    raise RuntimeError("kopier/lesen.py hat keinen Schreibschutz mehr - die "
                       "1:1-Kopier-Spur startet nicht.")


# --- Dateien ----------------------------------------------------------------

def _jetzt():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _heute():
    return datetime.now(timezone.utc).date().isoformat()


def _bis_zeit(iso):
    try:
        return datetime.fromisoformat(str(iso)) if iso else None
    except (TypeError, ValueError):
        return None


def _zahl(w):
    try:
        return float(str(w).replace(",", ""))
    except (TypeError, ValueError):
        return None


def lade(pfad, vorgabe=None):
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
    # Der Kopf der DATEI entscheidet, was geschrieben wird (T-095): ein
    # Altjournal ohne `pos_id` behaelt seine Spalten (pos_kennung.spalten).
    spalten = SPALTEN if neu else pos_kennung.spalten(JOURNAL, SPALTEN)
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        s = csv.DictWriter(f, fieldnames=spalten, extrasaction="ignore")
        if neu:
            s.writeheader()
        s.writerow({k: felder.get(k, "") for k in spalten})


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
    z.setdefault("positionen", [])
    # gesehene Trades: {wallet: {token: [tx1, tx2, ...]}} - damit ein Trade
    # nicht mehrfach gebucht wird, wenn er ueber mehrere Zyklen im Fenster
    # bleibt. Nur die tx-Kennung reicht (Solana-Tx sind eindeutig).
    z.setdefault("gesehene_tx", {})
    # Zeitstempel: bis wohin wir Trades gelesen haben - alles davor gilt als
    # abgehandelt (Einlauf beim ERSTEN Kontakt).
    z.setdefault("gesehen_bis_ms", {})
    z.setdefault("modus", "papier")
    return z


def schreibe_zustand(z):
    if not SCHREIBEN:
        return
    z["letzter_lauf"] = _jetzt()
    schreibe(ZUSTAND, z)


def spiegeln(z, w):
    """Bedingung 4: Journal, Zustand und Ablehnungen nach journal_zweitziel."""
    if not SCHREIBEN:
        return False, "Vorschau schreibt nichts"
    basis = _spiegelquelle()
    ziel = w.get("journal_zweitziel")
    ok, info = basis.spiegele_journal([JOURNAL, ZUSTAND, ABLEHNUNGEN], ziel)
    if basis.vermerke_spiegelung(z, ziel, ok, info, schreibe_zustand) and ok:
        basis.spiegele_journal([ZUSTAND], ziel)
    return ok, info


# --- Verfolgte: geerbt aus kopier/ ------------------------------------------

def gefolgt():
    """Die verfolgten Wallets aus kopier/verfolgte.json.

    Kein zweiter Rangliste-Abruf; kopier laeuft parallel und pflegt die
    Liste alle 4 h. Fehlt sie, meldet die Spur das und der Zyklus endet.
    """
    d = lade(VERFOLGTE_KOPIER, {})
    return {x["wallet"]: x for x in d.get("wallets", [])}


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


# --- Buchmathematik ---------------------------------------------------------

def _kaufpreis(preis, w):
    return preis * (1 + w["slippage_pct"] / 100.0)


def _verkaeuflich(menge, kurs, w):
    return menge * kurs * (1 - w["slippage_pct"] / 100.0) * (
        1 - w["gebuehr_pct"] / 100.0)


def _plus_stunden(stunden):
    return (datetime.now(timezone.utc)
            + timedelta(hours=stunden)).isoformat(timespec="seconds")


def _kopie_aus_trade(sig, trade, w):
    """Papier-Position aus einem Kauf-Trade des Vorbilds."""
    einsatz = w["max_einsatz_je_kauf_usd"]
    kaufpreis = _kaufpreis(trade["preis"], w)
    gebuehr = einsatz * w["gebuehr_pct"] / 100.0
    menge = (einsatz - gebuehr) / kaufpreis
    return {
        "kette": sig["kette"], "wallet": sig["wallet"],
        "wallet_name": sig["wallet_name"], "token": sig["token"],
        "symbol": sig["symbol"], "einsatz_usd": einsatz, "menge": menge,
        "preis_vorbild": trade["preis"], "preis_einstieg": kaufpreis,
        "marktkap_usd": sig.get("marktkap_usd"),
        "tx_einstieg": trade["tx"], "trade_zeit_ms": trade["zeit_ms"],
        "stop_usd": w.get("stop_usd"),
        # `stop_pct` ist das MASS, `stop_usd` ein fester Betrag. Ohne Prozent
        # waere "stop 60" bei 30 USD Einsatz 60 %, bei 90 USD aber nur noch 20 %
        # - die Regel waere von der Positionsgroesse abhaengig. Deshalb hat das
        # Prozent Vorrang (Auftrag Max 02.10.2026).
        "stop_pct": w.get("stop_pct"),
        "trail_aktiv_ab_pct": w["trail_aktiv_ab_pct"],
        "trail_abstand_pct": w["trail_abstand_pct"],
        "hoechster_kurs": kaufpreis,
        "frist": _plus_stunden(w["haltedauer_stunden"]),
        "letzter_kurs": trade["preis"],
        "eroeffnet": _heute(), "eroeffnet_zeit": _jetzt(),
    }


# --- Vorpruefung (billige Tore) --------------------------------------------

def _vorpruefung(sig, w, z):
    """Kette + Marktkap-Band + Deckel pro Token."""
    if sig["kette"] not in w["ketten"]:
        return "kette nicht unterstuetzt"
    mk = sig.get("marktkap_usd")
    unten, oben = w["marketcap_band_usd"]
    if mk is None:
        return "marktkap unbekannt"
    if not unten <= mk <= oben:
        return "marktkap ausserhalb"
    offen = [p for p in z["positionen"] if p["token"] == sig["token"]]
    if len(offen) >= w["max_kaeufe_je_token"]:
        return "token belegt"
    return None


# --- Sicht auf trades/batch je Wallet ---------------------------------------

def sammle_trades(w, gefolgt_map, z):
    """Fuer jede verfolgte Wallet die letzten Trades sammeln.

    Ein Abruf je Wallet pro Zyklus. Rueckgabe:
      trades[(wallet, token)] = liste von Trade-Objekten (neueste zuerst).
    Die verfolgten Tokens ergeben sich aus dem PORTFOLIO der Wallet (ein
    Abruf) - trades/batch braucht (mint, wallets)-Paare, das Portfolio
    liefert die mints.
    """
    trades = {}
    zaehler = 0
    for wallet, eintrag in gefolgt_map.items():
        if zaehler >= w.get("max_trader_je_zyklus", 10):
            break
        zaehler += 1
        try:
            pf = lesen.portfolio(wallet)
        except lesen.Lesefehler as e:
            print("  Portfolio %s nicht abrufbar: %s" % (wallet[:14], e))
            continue
        mints = list(pf["positions"].keys())
        # Nur Solana: 'native' ist SOL selbst, '0x...' sind EVM-Tokens
        # (Pump.fun ist Solana-only; trades/batch antwortet 404 bzw. leer).
        mints = [m for m in mints if m and m != "native"
                 and not m.startswith("0x")]
        if not mints:
            continue
        # trades/batch: EIN Token je Anfrage. Kappen bei 5 Tokens je
        # Wallet, sonst kostet ein aktiver Trader den ganzen Zyklus.
        # Zwischen Anfragen 1 s atmen, sonst antwortet Pump.fun mit 429.
        # (Der Dauerlauf-Takt ist 15 min - hier stimmt Sekunden-Kosten.)
        import time as _t
        for mint in mints[:5]:
            _t.sleep(1.0)
            try:
                t = lesen.trade_batch(mint, [wallet])
            except lesen.Lesefehler as e:
                print("  trades/batch %s/%s: %s"
                      % (wallet[:8], mint[:8], e))
                continue
            liste = (t or {}).get(wallet) or []
            if liste:
                po = pf["positions"].get(mint, {})
                trades[(wallet, mint)] = {
                    "wallet": wallet,
                    "wallet_name": eintrag.get("username") or wallet[:8],
                    "token": mint,
                    "symbol": po.get("symbol") or "?",
                    "kette": po.get("kette") or "solana",
                    "marktkap_usd": po.get("marktkap_usd"),
                    "preis_jetzt": po.get("preis"),
                    "trades": liste,
                }
    return trades


# --- Ausstieg: Verkauf des Vorbilds -----------------------------------------

def pruefe_verkaeufe(z, trades, w):
    """Wurde eine offene Kopie durch einen VERKAUF des Vorbilds ausgeloest?

    Bedingung: es gibt einen Trade typ='sell' auf (wallet, token), der
    NACH unserem Einstieg (trade_zeit_ms) liegt und noch nicht in
    z['gesehene_tx'] steht. Dann schliesst die Kopie zum letzten
    beobachteten Kurs.
    """
    behalten = []
    for p in z["positionen"]:
        sichtung = trades.get((p["wallet"], p["token"]))
        verkauf = None
        if sichtung:
            for t in sichtung["trades"]:
                if t.get("typ") != "sell":
                    continue
                if not t.get("zeit_ms") or t["zeit_ms"] <= p.get(
                        "trade_zeit_ms", 0):
                    continue
                verkauf = t
                break
        if not verkauf:
            behalten.append(p)
            continue
        kurs = p.get("letzter_kurs") or verkauf.get("preis")
        if not kurs:
            print("  Vorbild verkauft %s/%s, aber kein Kurs - Kopie bleibt"
                  % (p["symbol"], p["token"][:12]))
            behalten.append(p)
            continue
        erloes = _verkaeuflich(p["menge"], kurs, w)
        print("  AUSSTIEG (verkauft): %s %s @ %.10g  G/V %+.2f USD auf "
              "%.0f USD" % (p["symbol"], p["token"], kurs,
                            erloes - p["einsatz_usd"], p["einsatz_usd"]))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                pos_id=p.get("pos_id", ""),
                kette=p["kette"], wallet=p["wallet"],
                wallet_name=p.get("wallet_name", ""),
                token=p["token"], symbol=p["symbol"],
                tx=verkauf.get("tx"),
                kurs_ausstieg="%.10g" % kurs,
                menge="%.6f" % p["menge"],
                einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes,
                slippage_pct="%.2f" % w["slippage_pct"],
                gebuehr_pct="%.2f" % w["gebuehr_pct"],
                grund="verkauft")
    z["positionen"] = behalten


def _ausstiegsgrund(p, kurs, jetzt, w):
    """Stop (USD), Trailing, Frist - das Sicherheitsnetz."""
    erloes = _verkaeuflich(p["menge"], kurs, w)
    verlust = p["einsatz_usd"] - erloes
    if p.get("stop_pct"):
        # PROZENT des Einsatzes - gilt fuer jede Positionsgroesse.
        if verlust >= p["einsatz_usd"] * p["stop_pct"] / 100.0:
            return "stop"
    elif p.get("stop_usd") is not None:
        # Fester Betrag - Rueckfall, wenn kein Prozent gesetzt ist.
        if verlust >= p["stop_usd"]:
            return "stop"
    if p.get("trail_abstand_pct"):
        p["hoechster_kurs"] = max(p.get("hoechster_kurs") or kurs, kurs)
        peak = p["hoechster_kurs"] / p["preis_einstieg"] - 1
        if peak >= p["trail_aktiv_ab_pct"] / 100.0:
            trail_stop = p["hoechster_kurs"] * (
                1 - p["trail_abstand_pct"] / 100.0)
            if kurs <= trail_stop:
                return "trail"
    if jetzt >= (_bis_zeit(p["frist"]) or jetzt):
        return "frist"
    return None


def pruefe_ausstiege(z, w):
    behalten, jetzt = [], datetime.now(timezone.utc)
    for p in z["positionen"]:
        kurs = p.get("letzter_kurs")
        if not kurs:
            behalten.append(p)
            continue
        grund = _ausstiegsgrund(p, kurs, jetzt, w)
        if not grund:
            behalten.append(p)
            continue
        erloes = _verkaeuflich(p["menge"], kurs, w)
        print("  AUSSTIEG (%s)%s: %s %s @ %.10g  G/V %+.2f USD auf %.0f USD"
              % (grund, "" if SCHREIBEN else " [nur Vorschau]",
                 p["symbol"], p["token"], kurs,
                 erloes - p["einsatz_usd"], p["einsatz_usd"]))
        journal(zeit=_jetzt(), modus="papier", aktion="schliessen",
                pos_id=p.get("pos_id", ""),
                kette=p["kette"], wallet=p["wallet"],
                wallet_name=p.get("wallet_name", ""),
                token=p["token"], symbol=p["symbol"],
                kurs_ausstieg="%.10g" % kurs,
                menge="%.6f" % p["menge"],
                einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes,
                slippage_pct="%.2f" % w["slippage_pct"],
                gebuehr_pct="%.2f" % w["gebuehr_pct"],
                grund=grund)
    z["positionen"] = behalten


# --- Einstieg: Kauf des Vorbilds -------------------------------------------

def eroeffne(z, sig, trade, w):
    """Position aus einem Kauf-Trade buchen; None wenn erfolgreich."""
    kopie = _kopie_aus_trade(sig, trade, w)
    kopie["pos_id"] = pos_kennung.neu(_jetzt())
    z["positionen"].append(kopie)
    journal(zeit=_jetzt(), modus="papier", aktion="eroeffnen",
            pos_id=kopie.setdefault("pos_id", pos_kennung.neu(_jetzt())),
            kette=kopie["kette"], wallet=kopie["wallet"],
            wallet_name=kopie["wallet_name"],
            token=kopie["token"], symbol=kopie["symbol"],
            tx=trade["tx"],
            trade_zeit=datetime.fromtimestamp(
                trade["zeit_ms"] / 1000,
                tz=timezone.utc).isoformat(timespec="seconds"),
            preis_vorbild="%.10g" % trade["preis"],
            preis_einstieg="%.10g" % kopie["preis_einstieg"],
            menge="%.6f" % kopie["menge"],
            einsatz_usd="%.2f" % kopie["einsatz_usd"],
            marktkap_usd=("" if kopie.get("marktkap_usd") is None
                          else "%.0f" % kopie["marktkap_usd"]),
            slippage_pct="%.2f" % w["slippage_pct"],
            gebuehr_pct="%.2f" % w["gebuehr_pct"],
            grund="1zu1_kauf")
    return None


def kill_switch(z, w):
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
                pos_id=p.get("pos_id", ""),
                kette=p["kette"], wallet=p["wallet"],
                wallet_name=p.get("wallet_name", ""),
                token=p["token"], symbol=p["symbol"],
                kurs_ausstieg="" if not kurs else "%.10g" % kurs,
                menge="%.6f" % p["menge"],
                einsatz_usd="%.2f" % p["einsatz_usd"],
                wert_usd="%.2f" % erloes,
                slippage_pct="%.2f" % w["slippage_pct"],
                gebuehr_pct="%.2f" % w["gebuehr_pct"],
                grund=grund)
    z["positionen"] = []


# --- Wachen-Anzeige --------------------------------------------------------

def zeige_wachen(w):
    print("Grenzen der 1:1-Kopier-Spur (Papier):")
    for name in ("ketten", "verfolgte_aus_kopier",
                 "max_einsatz_je_kauf_usd", "max_offen", "max_offen_papier",
                 "max_neu_je_zyklus", "max_kaeufe_je_token",
                 "kill_switch_gesamt_usd", "slippage_pct", "gebuehr_pct",
                 "stop_usd", "trail_aktiv_ab_pct", "trail_abstand_pct",
                 "haltedauer_stunden", "max_alter_trade_sekunden",
                 "max_trader_je_zyklus", "marketcap_band_usd",
                 "herzschlag_max_minuten"):
        print("  %-30s %s" % (name, w.get(name)))
    print("  %-30s %s" % ("handel_erlaubt", w.get("handel_erlaubt")))
    z = lade_zustand()
    print("  %-30s %s" % ("journal_zweitziel",
                          w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print("  %-30s %s (%s)" % ("letzte Kopie",
                               z.get("journal_zweitziel_ok"),
                               z.get("journal_zweitziel_info")))
    print("  %-30s %d" % ("offene Positionen", len(z.get("positionen", []))))


def _frisch(z, w):
    letzte = _bis_zeit(z.get("letzter_lauf"))
    if not letzte:
        return False
    grenze = w.get("herzschlag_max_minuten", 180)
    return (datetime.now(timezone.utc) - letzte).total_seconds() <= grenze * 60


# --- Bilanz ----------------------------------------------------------------

def bilanz(w):
    if not os.path.exists(JOURNAL):
        print("Noch keine Buchzeile - kein Journal.")
        return
    gefolgt_map = gefolgt()
    je_wallet = {}
    with open(JOURNAL, newline="", encoding="utf-8") as f:
        for zeile in csv.DictReader(f):
            if zeile["aktion"] != "schliessen":
                continue
            wallet = zeile["wallet"]
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
        z = gefolgt_map.get(wallet, {})
        zahlen = ("Rang %s, PnL %s USD"
                  % (z.get("rank"), z.get("pnl_usd"))
                  if z.get("gemessen") else "nicht in der Rangliste")
        name = z.get("username") or wallet[:8]
        print("  %-16s %-44s %3d Runden  G/V %+8.2f  (%s)"
              % (name, wallet, e["runden"], e["gv"] / 100.0, zahlen))


# --- Lauf ------------------------------------------------------------------

def lade_wachen():
    """Wachen dieser Spur samt Risikostufe.

    Der Faktor gehoert an EINE Stelle, nicht in `lauf()`: so kann ein Test
    dieselbe Funktion befragen, die der Betrieb benutzt (sonst prueft der
    Test eine Nachbildung).
    """
    return risikostufe.skaliere(lade(WACHEN, None))


def lauf(modus):
    global SCHREIBEN, GESEHEN
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    SCHREIBEN = modus != "vorschau"
    GESEHEN = None

    w = lade_wachen()
    if not w:
        print("wachen.json fehlt oder ist unlesbar - kein Lauf.")
        return 1

    if modus == "wachen":
        zeige_wachen(w)
        return 0
    if modus == "bilanz":
        bilanz(w)
        return 0

    roh = w
    w = _umfang(w, modus)

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

    gefolgt_map = gefolgt()
    if not gefolgt_map:
        print("kopier/verfolgte.json ist leer - erst kopier --waehlen "
              "laufen lassen.")
        return 1

    print("Verfolge %d Trader (aus kopier/verfolgte.json)"
          % len(gefolgt_map))

    # 1) Trades sammeln (portfolio + trades/batch je Wallet).
    trades = sammle_trades(w, gefolgt_map, z)
    print("  %d (wallet, token)-Paare mit Trade-Historie geholt"
          % len(trades))

    # 2) Preise fortschreiben (aus portfolio-Snapshot).
    for p in z["positionen"]:
        sicht = trades.get((p["wallet"], p["token"]))
        if sicht and sicht.get("preis_jetzt"):
            p["letzter_kurs"] = sicht["preis_jetzt"]

    # 3) Ausstiege ZUERST: Verkauf des Vorbilds > Stop/Trail/Frist.
    pruefe_verkaeufe(z, trades, w)
    pruefe_ausstiege(z, w)
    if kill_switch(z, w):
        flach_stellen(z, w, "kill_switch")
        schreibe_zustand(z)
        spiegeln(z, w)
        return 0

    # 4) Einstiege: neue Kauf-Trades im Fenster verarbeiten.
    jetzt_ms = int(time.time() * 1000)
    alter_grenze_ms = w["max_alter_trade_sekunden"] * 1000
    neu = 0
    entscheidung = collections.Counter()
    lage = collections.Counter()
    einlauf = 0

    for (wallet, token), sicht in trades.items():
        # Einlauf: beim ersten Kontakt merken wir uns die aktuelle Zeit;
        # aeltere Trades sind stille Uebernahme (kein Kauf).
        alter_bis = z["gesehen_bis_ms"].get(wallet, {}).get(token)
        if alter_bis is None:
            einlauf += 1
            z["gesehen_bis_ms"].setdefault(wallet, {})[token] = jetzt_ms
            continue

        sig = {"kette": sicht["kette"], "wallet": wallet,
               "wallet_name": sicht["wallet_name"], "token": token,
               "symbol": sicht["symbol"],
               "marktkap_usd": sicht.get("marktkap_usd")}

        for trade in reversed(sicht["trades"]):
            if trade.get("typ") != "buy" or not trade.get("zeit_ms"):
                continue
            if trade["zeit_ms"] <= alter_bis:
                continue
            if jetzt_ms - trade["zeit_ms"] > alter_grenze_ms:
                lage["Kauf zu alt"] += 1
                z["gesehen_bis_ms"].setdefault(wallet, {})[token] = max(
                    z["gesehen_bis_ms"].setdefault(wallet, {}).get(token, 0),
                    trade["zeit_ms"])
                continue

            if len(z["positionen"]) >= w["max_offen"]:
                entscheidung["Buch voll - Kauf nicht gebucht"] += 1
                break
            if neu >= w["max_neu_je_zyklus"]:
                entscheidung["Zyklusdeckel - Kauf nicht gebucht"] += 1
                break

            grund = _vorpruefung(sig, w, z)
            if grund is not None:
                entscheidung[grund] += 1
                continue

            if modus == "vorschau":
                print("  WAERE %-10s %-28s Trade %s"
                      % (sig["symbol"][:10], sig["token"], trade["tx"][:12]))
                neu += 1
            else:
                if eroeffne(z, sig, trade, w) is None:
                    neu += 1
                    entscheidung["kopiert"] += 1
                    print("  KAUF (1:1) %-10s %-28s Vorbild @ %.10g"
                          % (sig["symbol"][:10], sig["token"],
                             trade["preis"]))
            # gesehene tx eintragen + gesehen_bis_ms fortschreiben
            z["gesehene_tx"].setdefault(wallet, {}).setdefault(
                token, []).append(trade["tx"])
            z["gesehen_bis_ms"].setdefault(wallet, {})[token] = max(
                z["gesehen_bis_ms"].setdefault(wallet, {}).get(token, 0),
                trade["zeit_ms"])

    if einlauf:
        protokolliere("Lage: Einlauf - Bestand still uebernommen", einlauf)
        print("  Einlauf: %d (wallet, token)-Paare uebernommen (kein Kauf "
              "beim ersten Kontakt)" % einlauf)

    if SCHREIBEN:
        for name, anzahl in sorted(lage.items()):
            protokolliere("Lage: %s" % name, anzahl)
        for name, anzahl in sorted(entscheidung.items()):
            protokolliere("Entscheidung: %s" % name, anzahl)

    print("=== Kopier1zu1 (PAPIER%s) | %d Trader, %d Trade-Paare | "
          "%d Kopien offen, %d neu ==="
          % ("" if modus != "vorschau" else ", Vorschau",
             len(gefolgt_map), len(trades),
             len(z["positionen"]), neu))

    if modus == "vorschau":
        print("Live waere gesperrt durch: kein Live-Pfad in dieser Spur "
              "(Papier)")
        return 0

    schreibe_zustand(z)
    ok, info = spiegeln(z, w)
    print("  Journal ausser Haus:  %s (%s)" % ("ok" if ok else "--", info))
    return 0


def main():
    with ereignis.lauf("handel/kopier1zu1"):
        return _main()


def _main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--wachen", action="store_const", const="wachen",
                   dest="modus")
    p.add_argument("--vorschau", action="store_const", const="vorschau",
                   dest="modus")
    p.add_argument("--papier", action="store_const", const="papier",
                   dest="modus")
    p.add_argument("--bilanz", action="store_const", const="bilanz",
                   dest="modus")
    p.add_argument("--live", action="store_const", const="live", dest="modus")
    p.set_defaults(modus="vorschau")
    a = p.parse_args()
    return lauf(a.modus)


if __name__ == "__main__":
    raise SystemExit(main())
