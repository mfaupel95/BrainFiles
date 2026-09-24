#!/usr/bin/env python3
"""Wache auf ein Live-Buch einer Handelsspur - eine Fassung fuer alle.

Warum eine gemeinsame Datei: die Wache ist bei jeder Spur dieselbe Rechnung
(neue Live-Zeile? Fensterwechsel? Buchbereinigung?) und unterscheidet sich nur
in Pfaden und Waehrung. Zwei Kopien waeren zwei Stellen, an denen dieselbe
Verbesserung nachgezogen werden muss.

Angeschlossen sind:
  - mosaic (Live seit 21.09.2026, 10 USDC je Position)
  - kraken (Live seit 21.09.2026 08:43, 50 EUR je Position, Gebuehr 0 via Pro)

Noch offen: `mosaic-live-wache.py` traegt seine eigene, aeltere Fassung
(dieselbe Rechnung, aber ein zweiter Ort fuer Verbesserungen). Es laeuft und
wird nicht angetastet, solange es laeuft - beim naechsten Anlass auf diese
Fassung umstellen.

Aufruf je Spur ueber eine duenne Huelle (der Hermes-Cron startet nur Skripte aus
`Agenten/Hermes/scripts/`):

    python kraken-live-wache.py
    python mosaic-live-wache.py

LEERE AUSGABE = nichts senden. Zustand je Spur in
`Agenten/Hermes/cache/<spur>-live-wache.json`.

WAS GEMELDET WIRD
  1. jede neue LIVE-Zeile im Journal (der erste echte Einstieg ist zugleich der
     Beweis, dass der Schluesselsatz ordern darf) - Fehlerzeilen als
     LIVE-FEHLER mit Grund,
  2. neue Zeilen mit Grund `buchbereinigung`: Papier-Ueberbleibsel im Live-Buch
     (sie belegen Plaetze und lassen den Live-Ausstieg ins Leere greifen),
  3. Fensterwechsel (live -> Papier, Papier -> live).
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

HANDEL = Path(__file__).resolve().parents[2] / "Handel"
STAND_ORDNER = Path(__file__).resolve().parents[1] / "cache"

# spur -> (Journal, Fenster-Schluessel, Waehrung, Mindestguthaben-Funktion)
SPUREN = {
    "mosaic": {"journal": HANDEL / "mosaic" / "handelsjournal.csv",
               "fenster": "mosaic", "waehrung": "USDC"},
    # scanner: OKX-Spot, das aktivste Live-Buch (7 Tage 118 Runden). Sein
    # Journal hat die Betragsspalte `usd` statt `eur`/`einsatz_usd` - deshalb
    # liest _text() alle drei Namen.
    "scanner": {"journal": HANDEL / "scanner" / "handelsjournal.csv",
                "fenster": "scanner", "waehrung": "USDC"},
    # xperp: XPERP-Kontrakte auf OKX, USD-marginiert (USDC), live seit 17.09.
    # Sein Journal schreibt Betraege als `nominal_usd` und alle 8 h eine
    # `funding`-Zeile mit modus=live - die ist kein Handel und wird uebersprungen.
    "xperp": {"journal": HANDEL / "xperp" / "handelsjournal.csv",
              "fenster": "xperp", "waehrung": "USDC"},
    "kraken": {"journal": HANDEL / "kraken" / "handelsjournal.csv",
               "fenster": "kraken", "waehrung": "EUR"},
    # Die beiden Buch-Spuren (Feed-Signal -> spur_buch.py) seit 21.09.2026 live:
    # 50 USDC je Trade, 150 gesamt, 3 Plaetze. Ihr Risiko-Vorfilter kann den
    # Einstieg sperren, obwohl das Fenster offen ist - deshalb meldet die Wache
    # bei ihnen zusaetzlich den VORFILTER-Grund (siehe vorfilter_grund()).
    "moondev_listingarb": {"journal": HANDEL / "moondev_listingarb" / "handelsjournal.csv",
                           "fenster": "moondev_listingarb", "waehrung": "USDC",
                           "vorfilter": True},
    "moondev_topmovers": {"journal": HANDEL / "moondev_topmovers" / "handelsjournal.csv",
                          "fenster": "moondev_topmovers", "waehrung": "USDC",
                          "vorfilter": True},
    # swap: OKX-Perp, live seit 21.09.2026 11:11 (Freigabe per Auftrag). War die
    # einzige LIVE handelnde Spur OHNE Wache (Befund 24.09.2026) - deshalb hier
    # nachgetragen statt eine zweite Wache-Datei zu bauen.
    "swap": {"journal": HANDEL / "swap" / "handelsjournal.csv",
             "fenster": "swap", "waehrung": "USDC"},
}


# Aktionen ohne Handelsentscheidung - sie stehen mit modus=live im Journal
# (z. B. Funding alle 8 h), sind aber keine Runde. Wortgleich zu stoerungen.py.
KEIN_HANDEL = {"funding", "rollover", "zyklus", "quotes", "info"}


def _lies(pfad):
    try:
        return json.loads(Path(pfad).read_text(encoding="utf-8"))
    except Exception:                                          # noqa: BLE001
        return {}


def _zeit(wert):
    if not wert:
        return None
    try:
        d = dt.datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def live_zeilen(journal):
    if not Path(journal).is_file():
        return []
    with Path(journal).open("r", newline="", encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)
                if (r.get("modus") or "").strip().lower() == "live"]


def fenster_lage(schluessel):
    d = _lies(HANDEL / "freigabe_fenster.json").get(schluessel) or {}
    bis = d.get("offen_bis")
    ende = _zeit(bis)
    if ende is None:
        return False, bis
    return ende > dt.datetime.now(dt.timezone.utc), bis


def _text(r):
    """Eine Live-Zeile als Meldung - Instrument und Betrag je Spuren-Schema."""
    aktion = (r.get("aktion") or "").strip()
    if aktion == "fehler":
        return "LIVE-FEHLER: %s %s  %s" % ((r.get("zeit") or "")[:16],
                                           r.get("inst") or r.get("paar") or "?",
                                           r.get("grund") or "")
    inst = r.get("inst") or r.get("paar") or r.get("symbol") or "?"
    betrag = (r.get("einsatz_usd") or r.get("eur") or r.get("usd")
              or r.get("nominal_usd") or "")
    return "LIVE: %s %s %s @ %s  %s  (%s)" % (
        (r.get("zeit") or "")[:16], aktion, inst,
        r.get("preis") or r.get("einstieg") or "", betrag, r.get("grund") or "")


def vorfilter_grund(spur):
    """Warum die Spur gerade NICHT einsteigt - aus ihrer eigenen Rechnung.

    Wichtig: nicht nachgebaut. Es wird `Handel/risikovorfilter.py` mit den
    echten Wachen, dem echten Journal und dem echten Zustand gefragt, so wie
    `spur_buch.py` es vor jedem Einstieg tut. Eine nachgebaute Formel wuerde
    die Formel pruefen, nicht die Spur.

    Rueckgabe: Text, wenn der Vorfilter sperrt; sonst None.
    """
    import importlib.util

    ordner = HANDEL / spur
    try:
        spec = importlib.util.spec_from_file_location(
            "risikovorfilter_wache", HANDEL / "risikovorfilter.py")
        rv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rv)
        w = json.loads((ordner / "wachen.json").read_text(encoding="utf-8"))
        z = json.loads((ordner / "zustand.json").read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return "%s: Vorfilter nicht lesbar (%s)" % (spur, e)
    if not w.get("risikovorfilter"):
        return None
    journal = ordner / "handelsjournal.csv"
    # Das Risiko eines geplanten Einstiegs: Nominal x Stop-Abstand.
    nominal = float(w.get("live_max_pro_trade_usd") or w.get("max_pro_trade_usd") or 0)
    stop_pct = float(w.get("stop_prozent") or w.get("pflicht_stop_prozent_min") or 5)
    erlaubt, grund = rv.pruefe(w, journal, z, nominal * stop_pct / 100.0)
    if erlaubt:
        return None
    return "%s: VORFILTER haelt den Einstieg zurueck - %s" % (spur, grund)


# --- Stops: Merker und Boersenlage ------------------------------------------
#
# Befund 23.09.2026: `scanner/zustand.json` trug 23 Kopien DESSELBEN Stops, und
# der Live-Lauf meldete jede Runde "offener Stop ... bleibt liegen: OKX 50014".
# Aufgefallen ist das erst Max - es gab keine Wache auf diesen Merker. Ein
# Stop, den nur das Buch kennt oder den nur die Boerse kennt, ist der teure
# Fall: der eine kann eine spaetere Position zum alten Preis verkaufen, der
# andere fehlt als Notausstieg ganz.

OKX_BUCH = "scanner"        # fuehrt Stop-Kennungen, die an OKX liegen


def _buch_stops(z):
    """Stop-Kennungen der OFFENEN Positionen aus dem Zustand."""
    aus = set()
    for p in z.get("positionen") or []:
        for feld in ("stop_ord_id", "stop_algo_id", "stop_txid"):
            if p.get(feld):
                aus.add(str(p[feld]))
    return aus


def boersenstops():
    """Aktive Conditional-Algos des OKX-Kontos, lesend. None = nicht lesbar.

    Ueber das okx-Modul der scanner-Spur, weil es denselben Zugang liest wie
    die Order selbst (`OKX_LIVE_*` + `OKX_BASE`). Es wird NICHTS veraendert.
    """
    import importlib.util

    try:
        spec = importlib.util.spec_from_file_location(
            "okx_wache", HANDEL / OKX_BUCH / "okx.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod._roh("/api/v5/trade/orders-algo-pending?ordType=conditional",
                        "GET", signiert=True) or []
    except Exception:                                          # noqa: BLE001
        return None


def _lage_gleich(vorher, jetzt):
    """Hat sich die Stop-Lage wirklich geaendert?

    Verglichen werden nur die Zahlen und die Kennungen - `abruf_ok` und der
    Zeitstempel allein sind kein Grund fuer eine Telegram-Nachricht.
    """
    felder = ("offene_stops", "boerse", "buch")
    for f in felder:
        if int(vorher.get(f) or 0) != int(jetzt.get(f) or 0):
            return False
    for f in ("waisen", "ohne_stop"):
        if sorted(vorher.get(f) or []) != sorted(jetzt.get(f) or []):
            return False
    return True


def stop_lage(spur):
    """(Meldungen, Zustand) zur Stop-Lage einer Spur.

    Gemeldet wird nur der WECHSEL (wie beim Vorfilter) - sonst stuende dieselbe
    Zeile alle 10 Minuten im Telegram.
    """
    z = _lies(HANDEL / spur / "zustand.json")
    offen = [e for e in (z.get("offene_stops") or []) if e.get("stop_ord_id")]
    lage = {"offene_stops": len(offen)}
    meldungen = []
    if offen:
        kennungen = sorted({str(e["stop_ord_id"]) for e in offen})
        meldungen.append(
            "%s: %d offener Stop(s) im Merker (%s, seit %s) - der Storno geht "
            "nicht durch. Sie gehoeren mit scanner/stops_bereinigen.py "
            "abgeglichen." % (spur, len(kennungen), ", ".join(kennungen[:3]),
                              (offen[0].get("seit") or "?")))

    if spur != OKX_BUCH:
        return meldungen, lage

    boerse = boersenstops()
    lage["abruf_ok"] = boerse is not None
    if boerse is None:
        return meldungen, lage
    kennungen = {str(a.get("algoId")) for a in boerse if a.get("algoId")}
    buch = _buch_stops(z)
    waisen = sorted(kennungen - buch)
    ohne = sorted(buch - kennungen)
    lage.update({"boerse": len(kennungen), "buch": len(buch),
                 "waisen": waisen, "ohne_stop": ohne})
    if waisen:
        meldungen.append(
            "%s: %d Stop(s) liegen an der Boerse, die zu keiner Position im Buch "
            "gehoeren (%s) - ein Waisenstop kann eine spaetere Position zum "
            "alten Preis verkaufen." % (spur, len(waisen), ", ".join(waisen[:3])))
    if ohne:
        meldungen.append(
            "%s: %d Position(en) im Buch ohne Boersenstop (%s) - kein "
            "Notausstieg." % (spur, len(ohne), ", ".join(ohne[:3])))
    return meldungen, lage


def wache(spur: str) -> int:
    cfg = SPUREN.get(spur)
    if not cfg:
        print("Unbekannte Spur: %s (bekannt: %s)" % (spur, ", ".join(SPUREN)))
        return 2
    journal = cfg["journal"]
    zeilen = live_zeilen(journal)
    offen, bis = fenster_lage(cfg["fenster"])
    stand_pfad = STAND_ORDNER / ("%s-live-wache.json" % spur)
    stand = _lies(stand_pfad)
    erstlauf = not stand

    meldungen = []
    vorher = int(stand.get("live_runden", 0))
    neu = zeilen[vorher:] if len(zeilen) > vorher else []
    for r in neu:
        # Funding/Rollover/Zyklus sind kein Handel (dieselben Wortlaute wie in
        # Handel/stoerungen.py) - sonst meldet die Wache alle 8 h eine
        # "Live-Zeile", die keine Order ist.
        if (r.get("aktion") or "").strip() in KEIN_HANDEL:
            continue
        meldungen.append(_text(r))
    bereinigt = [r for r in neu if (r.get("grund") or "") == "buchbereinigung"]
    if bereinigt:
        meldungen.append(
            "%s: %d Buchbereinigung(en) - Papier-Ueberbleibsel standen im "
            "Live-Buch und wurden ausgebucht." % (spur, len(bereinigt)))
    if erstlauf and zeilen:
        meldungen.append("%s hat %d Live-Zeile(n) im Journal - Beobachtung "
                         "laeuft ab jetzt." % (spur, len(zeilen)))

    war_offen = bool(stand.get("fenster_offen"))
    if not erstlauf and war_offen and not offen:
        meldungen.append("%s: Freigabefenster zu (war bis %s) - laeuft wieder "
                         "Papier, bis die Auto-Freigabe neu oeffnet." % (spur, bis))
    if not erstlauf and not war_offen and offen:
        meldungen.append("%s: Freigabefenster offen bis %s - live." % (spur, bis))

    # Bei den Buch-Spuren ist ein offenes Fenster nicht genug: ihr eigener
    # Risiko-Vorfilter kann den Einstieg sperren. Gemeldet wird nur der
    # WECHSEL des Grundes - sonst stuende dieselbe Zeile alle 10 Minuten da.
    if cfg.get("vorfilter"):
        grund = vorfilter_grund(spur)
        if grund != stand.get("vorfilter_grund"):
            if grund:
                meldungen.append(grund)
            elif not erstlauf:
                meldungen.append("%s: Vorfilter gibt den Weg frei - der "
                                 "naechste Kandidat kann live gekauft werden."
                                 % spur)
        vorfilter_stand = grund
    else:
        vorfilter_stand = None

    # Stop-Lage: derselbe Merker waechst sonst unbemerkt (Befund 23.09.2026).
    # Gemeldet wird nur bei Aenderung - sonst stuende dieselbe Zeile alle 10 min.
    stop_roh, stop_stand = stop_lage(spur)
    if not _lage_gleich(stand.get("stop_lage") or {}, stop_stand):
        meldungen += stop_roh

    STAND_ORDNER.mkdir(parents=True, exist_ok=True)
    stand_pfad.write_text(json.dumps({
        "live_runden": len(zeilen), "fenster_offen": offen, "offen_bis": bis,
        "vorfilter_grund": vorfilter_stand, "stop_lage": stop_stand,
        "geprueft": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    for m in meldungen:
        print(m)
    return 0


def main(spur: str) -> int:
    return wache(spur)


if __name__ == "__main__":
    # Direktaufruf: --spur NAME (die Cron-Huellen rufen main() mit festem Namen)
    import argparse
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--spur", required=True, choices=sorted(SPUREN))
    sys.exit(wache(p.parse_args().spur))