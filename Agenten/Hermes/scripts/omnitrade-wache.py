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

VORSCHAU ZUERST, DANN AENDERN (T-352, 07.10.2026):
- Ein Aufruf OHNE Argument ist die VORSCHAU: er zeigt die berechneten
  Anker-Aenderungen (welcher benannte Lauf nach dem Anker-Urteil steht und
  neu gestartet wuerde) und aendert NICHTS - in diesem Modus wird nie ein
  Rust-Prozess gestartet oder gestoppt.
- Erst `--anwenden` fuehrt den Neustart toter Laeufe aus.
- Der Hermes-Cron `omnitrade-waechter` ruft den Wrapper
  `omnitrade-wache-anwenden.py` auf, weil das Cron-Feld `script` nur den
  Dateinamen nimmt und keine Argumente durchreicht.

Sicherheitsregeln aus dem Haus (siehe omnitrade_start.py):
- Ein Lauf, der laeuft (Prozess mit --status-file-Marke), wird NIE zweimal
  gestartet - ein Testlauf hat das am 30.09.2026 erzeugt (Duplikat, sofort
  beendet).
- `zustand()` wirft nie; ist die Prozessliste nicht lesbar, wird
  sicherheitshalber NICHT gestartet.
- Der Waechter startet nur benannte LAEUFE, nie alles was eine Statusdatei
  hat - sonst wuerde er verwaiste Experimente (rsi_long_only SOL) ohne
  Rueckfrage wiederbeleben.
"""
import argparse
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
    """(laeuft, grund) - die echte Entscheidung aus dem Wrapper (zwei Zeugen:
    Prozess mit --status-file-Marke ODER Statusdatei + PID + Altersgrenze)."""
    return start.zustand(n)


def berechnen():
    """Anker-Urteile je benanntem Lauf - rein lesend, keine Seiteneffekte.

    `wiederbeleben` = laeuft nicht UND Statusdatei existiert. Das zweite Tor
    verhindert, dass der Waechter Betrieb erfindet: ein benannter Lauf OHNE
    Statusdatei wurde nie gestartet (05.10.2026: die sechs pine_*-Relais
    stehen in LAEUFE, hatten aber nie eine Datei).
    """
    urteile = []
    for n in start.LAEUFE:
        laeuft, grund = _lauf(n)
        datei = start.statusdatei(n)
        urteile.append({
            "name": n,
            "laeuft": bool(laeuft),
            "grund": grund,
            "statusdatei": datei,
            "wiederbeleben": (not laeuft) and bool(datei)
                              and os.path.isfile(datei),
        })
    return urteile


def vorschau_text(urteile):
    """Anzeige der berechneten Anker-Aenderungen - die Vorschau IST der Text.

    Leer zurueck, wenn nichts zu aendern waere (Hausregel: leere Ausgabe =
    nichts senden). Gezeigt wird dann nur, was der Anker zum Aendern bestimmt.
    """
    wieder = [u for u in urteile if not u["laeuft"] and u["wiederbeleben"]]
    if not wieder:
        return []
    laufend = sum(1 for u in urteile if u["laeuft"])
    still = [u for u in urteile if not u["laeuft"] and not u["wiederbeleben"]]
    z = ["omnitrade-Waechter VORSCHAU (berechnet, nichts geaendert - kein Start/Stopp)",
         "  %d laufen, %d wuerden neu gestartet, %d ohne Statusdatei (nicht angefasst)"
         % (laufend, len(wieder), len(still))]
    for u in wieder:
        z.append("  NEU STARTEN: %s (%s)" % (u["name"], u["grund"]))
    for u in still:
        z.append("  stehen lassen: %s (%s)" % (u["name"], u["grund"] or "keine Statusdatei"))
    z.append("Anwenden: omnitrade-wache.py --anwenden (der Cron macht das automatisch)")
    return z


def haupt(modus="vorschau"):
    """Berechnet die Anker-Urteile und zeigt sie (vorschau) oder setzt sie um.

    modus "vorschau":  Rueckgabe der berechneten Aenderungen, NIE starten/
                       stoppen, NIE die Merkdatei anfassen.
    modus "anwenden":  tote Laeufe mit Statusdatei neu starten (der
                       Cron-Wrapper omnitrade-wache-anwenden.py).
    Rueckgabe: Text fuer Telegram (leer = nichts senden).
    """
    urteile = berechnen()
    if modus == "vorschau":
        return "\n".join(vorschau_text(urteile))

    merk = _lade_merk()
    jetzt = time.time()
    zeilen = []
    tote = [u for u in urteile if u["wiederbeleben"]]
    for u in tote:
        n = u["name"]
        schluessel = "tot_" + n
        letzte = merk.get(schluessel, 0)
        if jetzt - letzte < TAKTZEITRAUM:
            continue
        merk[schluessel] = jetzt
        try:
            meldung = start.starte(n)
        except Exception as e:  # starte() kann werfen, z.B. Popen
            meldung = "%s: NEUSTART FEHLGESCHLAGEN: %s" % (n, e)
        zeilen.append(meldung)
    if zeilen:
        _schreibe_merk(merk)

    if not zeilen:
        return ""
    kopf = "omnitrade-Waechter: %d Lauf(e) waren tot, neu gestartet" % len(tote)
    return kopf + "\n" + "\n".join(zeilen)


def main(argv=None):
    p = argparse.ArgumentParser(description="Waechter fuer die benannten omnitrade-Laeufe")
    p.add_argument("--anwenden", action="store_true",
                   help="tote Laeufe mit Statusdatei wirklich neu starten "
                        "(ohne diesen Schalter ist die Vorschau Standard)")
    p.add_argument("--vorschau", action="store_true",
                   help="Vorschau ausdruecklich verlangen (Standard ohnehin)")
    p.add_argument("--trocken", action="store_true",
                   help="Alias fuer die Vorschau (frueherer Name)")
    a = p.parse_args(argv)

    modus = "anwenden" if a.anwenden else "vorschau"
    if a.trocken:
        modus = "vorschau"
    text = haupt(modus=modus)
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
