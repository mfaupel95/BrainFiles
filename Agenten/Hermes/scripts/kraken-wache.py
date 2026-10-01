#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wache auf die LIVE-Seite der kraken-Spur.

WARUM: kraken handelt seit dem 01.10.2026 wieder live (Auftrag Max, "kraken
scharf" + "bedingung 5 entfaellt"). Es ist die einzige Spur, deren Kaufweg ueber
einen BELEG laeuft: die Spur stellt den Beleg aus, ausgefuehrt wird er von einer
anderen Hand (Cron `beleg-hand`, alle 5 Minuten, oder das MCP-Werkzeug). Damit
gibt es zwei Stellen, an denen echtes Geld bewegt wird, und beide sind im
Journal sichtbar - aber niemand sieht von selbst hinein.

Gemeldet wird NUR, was neu ist:
  1. jeder neue LIVE-Kauf und jeder LIVE-Verkauf (mit Grund),
  2. jede neue Zeile mit `aktion=fehler` - die einzige Sorte, die einen Eingriff
     verlangen kann,
  3. eine LIVE-Position OHNE Boersen-Stop (`boersen_stop_fehlt` oder kein
     `stop_txid`) - das ist der gefaehrlichste Zustand der Spur,
  4. das Guthaben-Tor: keine Quotewaehrung ueber `mindest_gaben_je_quote`,
  5. STILLSTAND: kein Zyklus seit 45 min (die Spur schreibt alle ~6,5 min),
  6. der BELEG-VERFALL: mehr als 5 neue Belege ohne Ausfuehrung seit der letzten
     Meldung. Seit dem 01.10.2026 stehen 109 Belege gegen 5 Kaeufe - die Frist
     ist 180 s, der ausfuehrende Cron laeuft aber alle 5 Minuten (T-283).

Was NICHT gemeldet wird: Papierzeilen (die Spur schreibt auch im Papierlauf,
wenn das Fenster zu ist) und der laufende Belegzaehler als solcher.

LEERE AUSGABE = nichts senden (Watchdog-Muster). Zustand in
Agenten/Hermes/cache/kraken-wache.json.

Aufruf (Hermes-Cron, no_agent, alle 30 Minuten):
    python kraken-wache.py            # pruefen und melden, was neu ist
    python kraken-wache.py --jetzt    # zeigen, nichts schreiben
    python kraken-wache.py --ohne-netz  # nur Journal/Zustand, keine Abrufe
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERMES = Path(__file__).resolve().parents[1]
HANDEL = HERMES.parents[0] / "Handel"
CACHE = HERMES / "cache"
SPUR = "kraken"

STILL_MIN = 45           # ~sieben verpasste Laeufe bei ~6,5 min Takt
BELEG_ALARM = 5          # so viele neue Belege ohne Ausfuehrung sind eine Meldung


# --- Lesen ----------------------------------------------------------------

def _lies(pfad: Path):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _zeilen(pfad: Path):
    try:
        with pfad.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return []


def _zeit(wert):
    try:
        return dt.datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
    except Exception:
        return None


def _kurz(wert):
    """'2026-10-01T11:27:22+00:00' -> '01.10. 13:27' (Ortszeit)."""
    z = _zeit(wert)
    if z is None:
        return str(wert)[:16]
    if z.tzinfo is not None:
        z = z.astimezone()
    return z.strftime("%d.%m. %H:%M")


# --- Die Regeln (reine Funktion, ohne Netz und ohne Dateien) ---------------

def neue_zeilen(rows, stand):
    """Journalzeilen, die seit dem letzten Stand dazugekommen sind."""
    n = int(stand.get("zeilen", 0))
    return rows[n:], len(rows)


def stop_luecken(z, offene_stops=None):
    """Paare von LIVE-Positionen, die keinen Schutzauftrag (mehr) haben.

    Zwei Zeugen: das Feld `boersen_stop_fehlt` im Buch und - wenn uebergeben -
    die Liste der offenen Auftraege an der Boerse. Ein Buch kann den Stop
    fuehren, waehrend er an der Boerse storniert wurde; der zweite Zeuge faellt
    nur, wenn er vorliegt.
    """
    luecken = []
    for p in (z.get("positionen") or []):
        if not isinstance(p, dict):
            continue
        if not p.get("kauf_txid") and not p.get("stop_txid"):
            continue                        # Altbestand ohne Boersenbezug
        if p.get("boersen_stop_fehlt") or not p.get("stop_txid"):
            luecken.append("%s (kein stop_txid)" % p.get("paar"))
            continue
        if offene_stops is not None:
            menge = float(p.get("menge") or 0)
            # Toleranz statt Gleichheit: die Boerse fuehrt `vol` mit ihren
            # eigenen Stellen, das Buch mit seinen. 1e-6 ist gross genug fuer
            # die Rundung und klein genug, um einen fehlenden Auftrag zu sehen.
            hat = any(abs(float(s.get("menge") or 0) - menge) <= max(1e-6, menge * 1e-9)
                      for s in offene_stops)
            if not hat:
                luecken.append("%s (Stop nicht mehr an der Boerse)" % p.get("paar"))
    return luecken


def tor_zu(guthaben):
    """True, wenn KEINE Quotewaehrung ueber ihrem Tor steht.

    `guthaben` ist {name: (frei, noetig)} - die Form aus
    kraken/handeln.guthaben_lage(). Ein leeres Dict heisst 'nicht abrufbar',
    das ist kein geschlossenes Tor (sonst meldet die Wache bei jedem
    Netzfehler).
    """
    if not guthaben:
        return False
    return not any(float(frei) >= float(noetig) and float(frei) > 0
                   for frei, noetig in guthaben.values())


def stillstand(letzter_lauf, jetzt, grenze_min=STILL_MIN):
    z = _zeit(letzter_lauf)
    if z is None:
        return None
    if z.tzinfo is None:
        z = z.replace(tzinfo=dt.timezone.utc)
    minuten = (jetzt - z).total_seconds() / 60.0
    return minuten if minuten > grenze_min else None


def meldungen_bauen(rows, stand, z=None, guthaben=None, offene_stops=None,
                    jetzt=None, geprueft_boerse=True):
    """(meldungen, neuer_stand) - reine Funktion, damit sie pruefbar ist.

    `geprueft_boerse=False` heisst: der Aufrufer konnte die Boerse nicht fragen.
    Dann wird der Stop-Zustand NICHT behauptet (weder gemeldet noch
    freigegeben) - eine Wache, die ohne Abruf 'kein Stop' meldet, meldet einen
    Netzfehler als Gefahr.
    """
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    z = z or {}
    stand = dict(stand)
    meldungen = []
    neu, gesamt = neue_zeilen(rows, stand)
    stand["zeilen"] = gesamt

    # 1./2. neue LIVE-Zeilen und Fehler
    belege_neu = 0
    for r in neu:
        if (r.get("modus") or "").strip() != "live":
            continue
        aktion = (r.get("aktion") or "").strip()
        if aktion == "kauf":
            meldungen.append(
                "kraken: LIVE-KAUF %s zu %s EUR (Menge %s, Stop %s, Ziel %s) %s"
                % (r.get("paar"), r.get("preis"), r.get("menge"),
                   r.get("stop"), r.get("ziel"), _kurz(r.get("zeit"))))
        elif aktion == "verkauf":
            meldungen.append(
                "kraken: LIVE-VERKAUF %s zu %s EUR (Erloes %s) - Grund %s %s"
                % (r.get("paar"), r.get("preis"), r.get("eur"),
                   r.get("grund") or "?", _kurz(r.get("zeit"))))
        elif aktion == "fehler":
            meldungen.append(
                "kraken: FEHLER %s - %s %s"
                % (r.get("paar"), r.get("grund") or r.get("preis"),
                   _kurz(r.get("zeit"))))
        elif aktion == "kauf_beleg":
            belege_neu += 1

    # 6. Belegverfall - nur wenn es sich haeuft
    beleg_kennung = "%d" % (belege_neu // BELEG_ALARM)
    if belege_neu >= BELEG_ALARM and stand.get("beleg_alarm") != beleg_kennung:
        meldungen.append(
            "kraken: %d neue Belege in einem Lauf, keiner davon ausgefuehrt. "
            "Die Beleg-Frist ist 180 s, der ausfuehrende Cron laeuft alle 5 min "
            "- ein Beleg nach einem Lauf ist beim naechsten schon abgelaufen "
            "(T-283)." % belege_neu)
        stand["beleg_alarm"] = beleg_kennung

    # 3. Live-Position ohne Stop
    if geprueft_boerse:
        luecken = stop_luecken(z, offene_stops)
        if luecken:
            kennung = "|".join(sorted(luecken))
            if kennung != stand.get("stop_luecke"):
                meldungen.append(
                    "kraken: LIVE-POSITION OHNE SCHUTZ - %s. Der Notausstieg "
                    "fehlt an der Boerse, die Position liegt ungeschuetzt im "
                    "Markt." % ", ".join(luecken))
                stand["stop_luecke"] = kennung
        else:
            stand.pop("stop_luecke", None)

    # 4. Guthaben-Tor
    if guthaben is not None:
        if tor_zu(guthaben):
            kennung = "|".join("%s=%.2f" % (k, float(v[0]))
                               for k, v in sorted(guthaben.items()))
            if stand.get("tor_zu") != kennung:
                meldungen.append(
                    "kraken: Guthaben-Tor ZU in jeder Quotewaehrung (%s) - die "
                    "Spur kann nicht einsteigen, bis eine Waehrung ueber ihr "
                    "Tor kommt." % ", ".join(
                        "%s %.2f/%.0f" % (k, float(v[0]), float(v[1]))
                        for k, v in sorted(guthaben.items())))
                stand["tor_zu"] = kennung
        else:
            stand.pop("tor_zu", None)

    # 5. Stillstand - einmal je Ereignis, mit Erholung
    alter = stillstand(z.get("letzter_lauf"), jetzt)
    if alter is not None:
        if not stand.get("stillstand"):
            meldungen.append(
                "kraken: STILLSTAND - letzter Zyklus vor %.0f min (%s). Der "
                "Dauerlauf schreibt alle ~6,5 min; pruefen, ob er laeuft."
                % (alter, _kurz(z.get("letzter_lauf"))))
            stand["stillstand"] = True
    elif stand.get("stillstand"):
        meldungen.append("kraken: Zyklus laeuft wieder.")
        stand.pop("stillstand", None)

    return meldungen, stand


# --- Boerse fragen (der einzige Netzzugriff) -------------------------------

def kraken_modul():
    """kraken/kraken.py ueber den PFAD laden - nicht ueber sys.path.

    Ein Eintrag auf Handel/ koennte ein gleichnamiges Modul verdecken; die Spur
    selbst macht es genauso (siehe kraken/handeln.py).
    """
    import importlib.util
    pfad = HANDEL / "kraken" / "kraken.py"
    spec = importlib.util.spec_from_file_location("kraken_wache_modul", pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["kraken_wache_modul"] = modul
    spec.loader.exec_module(modul)
    return modul


def boerse_fragen():
    """(guthaben, offene_stops) - oder (None, None), wenn nicht abrufbar.

    Zwei Fallen, beide am 01.10.2026 in der ersten Fassung gestanden:
      * `kontostaende()` liefert die KRAKEN-Namen (ZEUR, XXBT), nicht die
        lesbaren (EUR, XBT). Wer `staende["EUR"]` liest, bekommt 0.00 und
        meldet ein geschlossenes Tor, das weit offen ist. Richtig ist die
        Haus-Funktion `handeln.guthaben_lage(w)` - sie loest ueber
        `quote.lesbar` auf.
      * `offene_orders()` gibt FERTIG {txid: {paar, seite, art, menge, preis}}
        zurueck. Ein zweites `.get("open")` darauf findet nichts, und die
        Feldnamen sind `seite`/`menge`, nicht `type`/`vol`. Beides zusammen
        meldete JEDEN Schutz-Stop als fehlend.
    """
    try:
        k = kraken_modul()
        if not k.schluessel_vorhanden():
            return None, None
        w = _lies(HANDEL / SPUR / "wachen.json")
        handeln = _spur_modul()
        guthaben = handeln.guthaben_lage(w)
        stops = [{"menge": e.get("menge"), "seite": e.get("seite")}
                 for e in k.offene_orders().values()
                 if (e.get("seite") or "").lower() == "sell"]
        return guthaben, stops
    except Exception as e:                                     # noqa: BLE001
        print("kraken-wache: Boerse nicht abrufbar (%s)" % e, file=sys.stderr)
        return None, None


def _spur_modul():
    """kraken/handeln.py ueber den PFAD laden (wie kraken_modul())."""
    import importlib.util
    pfad = HANDEL / "kraken" / "handeln.py"
    if "kraken_wache_spur" in sys.modules:
        return sys.modules["kraken_wache_spur"]
    spec = importlib.util.spec_from_file_location("kraken_wache_spur", pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["kraken_wache_spur"] = modul
    spec.loader.exec_module(modul)
    return modul


# --- Lauf -----------------------------------------------------------------

def lauf(schreiben: bool = True, mit_netz: bool = True):
    ordner = HANDEL / SPUR
    stand_datei = CACHE / "kraken-wache.json"
    erstlauf = not stand_datei.exists()
    stand = _lies(stand_datei)

    rows = _zeilen(ordner / "handelsjournal.csv")
    z = _lies(ordner / "zustand.json")

    if erstlauf:
        # Beim ersten Lauf NICHT das ganze Journal nachmelden: die 225 Zeilen
        # enthalten fuenf echte Kaeufe aus der Vorgeschichte. Statt einer
        # Lawine gibt es einen Grundstand und eine Zeile, die sagt, wo die
        # Wache anfaengt.
        stand = {"zeilen": len(rows)}
        if schreiben:
            stand_datei.parent.mkdir(parents=True, exist_ok=True)
            stand_datei.write_text(
                json.dumps(stand, ensure_ascii=False, indent=2), encoding="utf-8")
        live = [r for r in rows
                if (r.get("modus") or "").strip() == "live"
                and (r.get("aktion") or "").strip() in ("kauf", "verkauf")]
        return ["kraken-wache eingerichtet: %d Journalzeilen, davon %d echte "
                "Live-Kaeufe/-Verkaeufe in der Vorgeschichte. Ab jetzt wird nur "
                "noch NEUES gemeldet (Kauf, Verkauf, Fehler, Position ohne "
                "Stop, Guthaben-Tor, Stillstand, Belegverfall)."
                % (len(rows), len(live))]

    guthaben = offene_stops = None
    geprueft_boerse = False
    if mit_netz:
        guthaben, offene_stops = boerse_fragen()
        geprueft_boerse = offene_stops is not None

    meldungen, neu = meldungen_bauen(rows, stand, z=z, guthaben=guthaben,
                                     offene_stops=offene_stops,
                                     geprueft_boerse=geprueft_boerse)
    if schreiben:
        stand_datei.parent.mkdir(parents=True, exist_ok=True)
        stand_datei.write_text(json.dumps(neu, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    return meldungen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jetzt", action="store_true",
                   help="nur zeigen, den Merkstand nicht schreiben")
    p.add_argument("--ohne-netz", action="store_true",
                   help="nur Journal und Zustand lesen, die Boerse nicht fragen")
    a = p.parse_args()
    for zeile in lauf(schreiben=not a.jetzt, mit_netz=not a.ohne_netz):
        print(zeile)
    return 0


if __name__ == "__main__":
    sys.exit(main())