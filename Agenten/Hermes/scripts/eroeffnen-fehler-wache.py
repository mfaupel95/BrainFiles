#!/usr/bin/env python3
"""Wache auf wiederholte Handels-Fehlschlaege (Dauerlauf-Ereignisprotokoll).

DER FEHLER-DETEKTOR (28.09.2026, Auftrag Max "waecher-cron anlegen"):

Der Dauerlauf meldet "fehlgeschlagen"-Zeilen zwar als Zyklus-Meldung per
Telegram, speichert sie aber nirgends - ein einzelner transienter Fehler
(z.B. der XAG-Kontraktwechsel am 20.09.) ist deshalb nicht von einem
wiederholten, echten Fehler zu unterscheiden. Seit 28.09.2026 haengt der
Dauerlauf jede neue Fehlschlag-Zeile an `Handel/cache/ereignis-fehler.jsonl`
(protokolliere_fehler). Diese Wache wertet sie aus.

REGEL: gemeldet wird nur, was WIEDERHOLT auftritt - derselbe Basiswert
(aus der Zeile extrahiert) mit mindestens 2 Fehlschlaege innerhalb von
WIEDERHOLEN_FENSTER_STUNDEN. Ein einzelner transienter Fehler wird ignoriert.
Leere Ausgabe = nichts senden (Watchdog-Muster).

Der Begriff "waechter-cron mcp" (Anfrage 28.09.2026): der Waechter nutzt als
Quelle das MCP-nahe Ereignisprotokoll des Dauerlaufs, nicht das eigene
Werkzeug.

Aufruf:
    python eroeffnen-fehler-wache.py              # Standard: 24h-Fenster, >=2
    python eroeffnen-fehler-wache.py --immer     # auch ohne Neues eine Zeile
    python eroeffnen-fehler-wache.py --probe     # nur letzte Eintraege zeigen
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
# scripts liegt unter Agenten/Hermes/scripts -> zwei Stufen hoch nach Agenten,
# dann in den Handels-Ordner (Agenten/Handel) - der Dauerlauf schreibt dorthin
# (sein HIER = Agenten/Handel), der Waechter muss DIESELBE Datei lesen.
AGENTEN = os.path.dirname(os.path.dirname(HIER))
HANDEL = os.path.join(AGENTEN, "Handel")
DATEI = os.path.join(HANDEL, "cache", "ereignis-fehler.jsonl")
MERKE = os.path.join(HIER, "cache", "eroeffnen-fehler-wache.json")

# Ein Fehler gilt als "wiederholt", wenn derselbe Basiswert mindestens so oft
# im Fenster fehlschlug.
WIEDERHOLEN_FENSTER_STUNDEN = 24.0
WIEDERHOLEN_ANZAHL = 2

# Basiswert aus einer Zeile ziehen: "Eroeffnen XAG-USD_UM_XPERP-310509
# fehlgeschlagen: ..." -> das erste Token nach "Eroeffnen"/"Schliessen"/
# "Storno"/"Notausstieg". Rueckfall: das erste instrument-artige Wort.
_TOKEN_MUSTER = re.compile(
    r"(?:Eroeffnen|Verkauf|Kauf|Schliessen|Storno|Notausstieg)\s+"
    r"([A-Za-z0-9._-]+)", re.IGNORECASE)


def basis_aus(zeile: str) -> str | None:
    """Der Basiswert einer Fehlschlag-Zeile (oder None, wenn nicht erkennbar)."""
    m = _TOKEN_MUSTER.search(zeile)
    if m:
        return m.group(1)
    # Rueckfall: erstes Wort, das ein Instrument/Paar zu sein scheint.
    for wort in zeile.split():
        if re.fullmatch(r"[A-Za-z]{2,10}(?:USD|EUR|USDT|USDC)?[-_.][A-Z0-9._-]+", wort):
            return wort
    return None


def lese_fehler(stunden: float) -> list[dict]:
    """Die Eintraege der letzten `stunden` Stunden aus der Protokolldatei."""
    if not os.path.exists(DATEI):
        return []
    import datetime as dt
    grenze = dt.datetime.now() - dt.timedelta(hours=stunden)
    out = []
    with open(DATEI, encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile:
                continue
        out = []  # noqa: not used
    # Neu lesen (sauberer):
    out = []
    try:
        with open(DATEI, encoding="utf-8") as f:
            for zeile in f:
                zeile = zeile.strip()
                if not zeile:
                    continue
                try:
                    e = json.loads(zeile)
                    zt = e.get("zeit", "")
                    try:
                        t = dt.datetime.fromisoformat(zt)
                    except ValueError:
                        continue
                    if t >= grenze:
                        out.append(e)
                except (json.JSONDecodeError, TypeError):
                    continue
    except OSError:
        return []
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--immer", action="store_true",
                   help="auch ohne wiederholten Fehler eine Zeile ausgeben")
    p.add_argument("--probe", action="store_true",
                   help="nur die letzten Eintraege zeigen, nichts schliessen")
    a = p.parse_args()

    if a.probe:
        eintraege = lese_fehler(WIEDERHOLEN_FENSTER_STUNDEN)
        print("Ereignis-Fehlerprotokoll (%d Eintraege in %g h):" %
              (len(eintraege), WIEDERHOLEN_FENSTER_STUNDEN))
        for e in eintraege[-10:]:
            print("  %s %s: %s" % (e.get("zeit", "?"), e.get("spur", "?"),
                                   e.get("zeile", "")[:90]))
        return 0

    eintraege = lese_fehler(WIEDERHOLEN_FENSTER_STUNDEN)
    if not eintraege:
        print("keine Fehlschlaege im Fenster, alles ok", flush=True) if a.immer else None
        return 0

    # Nach Spur + Basiswert gruppieren, nur Wiederholungen zaehlen.
    gruppen = {}
    for e in eintraege:
        b = basis_aus(e.get("zeile", ""))
        schluessel = (e.get("spur", "?"), b or "?")
        gruppen.setdefault(schluessel, []).append(e)

    # Wiederholte Fehler: dieselbe (spur, basis) >= WIEDERHOLEN_ANZAHL.
    wiederholt = []
    beginn = eintraege[0].get("zeit", "") if eintraege else ""
    for (spur, basis), liste in sorted(gruppen.items()):
        if len(liste) >= WIEDERHOLEN_ANZAHL:
            liste.sort(key=lambda e: e.get("zeit", ""))
            wiederholt.append({
                "spur": spur, "basis": basis, "anzahl": len(liste),
                "letzte": liste[-1].get("zeile", ""),
                "erstes": liste[0].get("zeit", ""),
                "letzte_zeit": liste[-1].get("zeit", ""),
            })

    # Statisch: einmal gemeldete (spur, basis) nicht erneut senden, bis der
    # Fehler > BERUHIGUNGS_STUNDEN nicht mehr auftrat.
    BERUHIGUNG_STUNDEN = 24.0
    import datetime as dt
    franken = {}
    if os.path.exists(MERKE):
        try:
            with open(MERKE, encoding="utf-8") as f:
                franken = json.load(f)
        except (json.JSONDecodeError, OSError):
            franken = {}
    gemeldet = franken
    neu = False
    zeilen = []
    jetzt = dt.datetime.now()
    for w in wiederholt:
        kennung = "%s:%s" % (w["spur"], w["basis"])
        zuletzt_gemeldet = franken.get(kennung)
        if zuletzt_gemeldet:
            # Nur melden, wenn der Fehler seit der letzten Meldung wieder
            # aufgetreten ist (die Datei ist ja nach Anhaengen "neu" genug).
            try:
                lt = dt.datetime.fromisoformat(zuletzt_gemeldet)
                if (jetzt - lt).total_seconds() < BERUHIGUNG_STUNDEN * 3600:
                    continue  # bereits gemeldet, Fehler haelt nicht an
            except ValueError:
                pass
        zeilen.append("%s: %s (%dx in %gh)" % (w["spur"].upper(),
                                               w["basis"], w["anzahl"],
                                               WIEDERHOLEN_FENSTER_STUNDEN))
        zeilen.append("  letzter Fehler (%s): %s" % (w["letzte_zeit"],
                                                     w["letzte"]))
        zeilen.append("  erster Fehler: %s" % w["erstes"])
        franken[kennung] = jetzt.isoformat(timespec="seconds")
        neu = True

    # Merke-Stand ablegen (nur wenn wirklich neue Meldungen erzeugt wurden).
    try:
        os.makedirs(os.path.dirname(MERKE), exist_ok=True)
        with open(MERKE, "w", encoding="utf-8") as f:
            json.dump(gemeldet, f, ensure_ascii=False, indent=1)
    except OSError:
        pass

    if not neu:
        if a.immer:
            print("kein wiederholter Fehler im Fenster (nur Einzelfaelle: %d)" %
                  len(eintraege))
        return 0

    print("<b>Wiederholte Handels-Fehlschlaege</b> " +
          "(%gh-Fenster, ab %s):" % (WIEDERHOLEN_FENSTER_STUNDEN, beginn))
    print("\n".join(zeilen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
