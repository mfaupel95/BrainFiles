#!/usr/bin/env python3
"""Waechter fuer die benannten omnitrade-Laeufe (LAEUFE in omnitrade_start.py).

Befund 05.10.2026: Es liefen 7 omnitrade-cli-Prozesse, davon 4 mit toten
Prozessen (rsi30_stop5 BTC/ETH seit 17 h, rsi_noema seit 16 h, live.json
seit Minuten) - und KEIN Waechter startete sie neu. Die Statusdatei behauptet
`state: running`, aber der Prozess ist weg. Der Wrapper `omnitrade_start.py`
hat `zustand()` (zwei Zeugen: Prozessliste + Statusdatei) und `starte()`
(Duplikatschutz, Pruefung der Demo-Keys) - es fehlte nur der Aufrufer.

Dieses Skript ist der Aufrufer. Es laeuft als Hermes-Cron (no_agent), leere
Ausgabe = nichts senden. Gemeldet wird nur der WECHSEL gegen die letzte
Meldung (Merkdatei), nicht jede Wiederholung.

Sicherheitsregeln aus dem Haus (siehe omnitrade_start.py):
- Ein Lauf, der laeuft (Prozess mit --status-file-Marke), wird NIE zweimal
  gestartet - ein Testlauf hat das am 30.09.2026 erzeugt (Duplikat, sofort
  beendet).
- `zustand()` wirft nie; ist die Prozessliste nicht lesbar, wird
  sicherheitshalber NICHT gestartet.
- Der Waechter startet nur benannte LAEUFE, nie alles was eine Statusdatei
  hat - sonst wuerde er verwaiste Experimente (rsi_long_only SOL) ohne
  Rückfrage wiederbeleben.
"""
import json
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
# omnitrade_start.py liegt unter Agenten/Handel/
HANDEL = os.path.abspath(os.path.join(HIER, "..", "..", "Handel"))
for p in (HANDEL,):
    if p not in sys.path:
        sys.path.insert(0, p)

import omnitrade_start as start  # noqa: E402

MERK = os.path.join(HIER, "cache", "omnitrade-wache.json")
TAKTZEITRAUM = 3600 * 2  # Wiederholung derselben Meldung erst nach 2 h


def _lade_merk():
    try:
        with open(MERK, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _schreibe_merk(merk):
    os.makedirs(os.path.dirname(MERK), exist_ok=True)
    with open(MERK, "w", encoding="utf-8") as f:
        json.dump(merk, f, ensure_ascii=False, indent=1)


def _lauf(n):
    """(laeuft, grund) - die echte Entscheidung aus dem Wrapper."""
    return start.zustand(n)


def haupt(trocken=False):
    """Prueft alle benannten Laeufe; ohne --anwenden nur melden was fehlt.

    Rueckgabe: Text fuer Telegram (leer = nichts senden).
    """
    merk = _lade_merk()
    jetzt = time.time()
    zeilen = []

    tote = []
    for n in start.LAEUFE:
        laeuft, grund = _lauf(n)
        if laeuft:
            continue
        datei = start.statusdatei(n)
        # NUR wiederbeleben, was schon einmal lief: Die Statusdatei existiert,
        # aber der Prozess ist tot (Grund enthaelt "veraltet"/"kein
        # Lebenszeichen"). Ein benannter Lauf OHNE Statusdatei wurde nie
        # gestartet - der Waechter erfindet keinen Betrieb (05.10.2026: die
        # sechs pine_*-Relais stehen in LAEUFE, hatten aber nie eine Datei).
        if not datei or not os.path.isfile(datei):
            continue
        tote.append((n, grund))

    for n, grund in tote:
        schluessel = "tot_" + n
        letzte = merk.get(schluessel, 0)
        if jetzt - letzte < TAKTZEITRAUM:
            continue
        merk[schluessel] = jetzt
        if not trocken:
            try:
                meldung = start.starte(n)
            except Exception as e:  # starte() kann werfen, z.B. Popen
                meldung = "%s: NEUSTART FEHLGESCHLAGEN: %s" % (n, e)
        else:
            meldung = "%s: wuerde neu gestartet (%s)" % (n, grund)
        zeilen.append(meldung)

    # verwaiste Statusdateien (Prozess tot, kein benannter Lauf) - nur nennen
    # wenn sie JEMALS einen lebenden Prozess bezeugt hatten; ohne Beweis nicht
    # melden (sonst Alarm bei jeder alten Datei).
    if not trocken and zeilen:
        _schreibe_merk(merk)

    if not zeilen:
        return ""
    kopf = "omnitrade-Waechter: %d Lauf(e) waren tot, neu gestartet" % len(tote) if not trocken else \
           "omnitrade-Waechter (Trockenlauf): %d tote Laeufe erkannt" % len(tote)
    return kopf + "\n" + "\n".join(zeilen)


if __name__ == "__main__":
    trocken = "--trocken" in sys.argv
    text = haupt(trocken=trocken)
    if text:
        print(text)