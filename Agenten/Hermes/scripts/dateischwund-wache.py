#!/usr/bin/env python3
"""Wache auf verschwundene Dateien in ``Agenten/Hermes/scripts/`` (T-100).

WARUM: Sechs Testdateien sind dort zwischen dem 21. und 26.09.2026 aus dem
Arbeitsbaum verschwunden - jedes Mal lag danach nur noch der Bytecode in
``__pycache__``. Zwei Faelle sind belegt (``test_breite_wache.py``, zweimal am
25.09.2026). Der Loescher selbst ist bis heute NICHT gefasst; ausgeschlossen
wurden Defender, die 41 Cron-Auftraege, ``git reset``/``checkout``/``clean``
und jedes Haus-Werkzeug (Befundbericht im Wiki, ``Wiki/Lektionen/Git-und-Textdateien.md``).

Die zweite Haelfte des Schadens ist dagegen bewiesen und war die schlimmere:
``Agenten/Routinen/fremdarbeit-einziehen.ps1`` sieht eine geloeschte Datei nach
30 Minuten als "ruhende Fremdarbeit" an und **committet die Loeschung** auf
master. Eine Luecke von einer Sekunde wird so zur dauerhaften Loeschung.
Beleg: ``455e0fe`` (test_breite_wache.py), ``22e5f7d`` (test_waisen_wache.py),
``3ef372b`` (test_spiegelfrist_wache.py, test_spur_wache.py), ``aae26a9``
(test_live_wache_stops.py), ``cc70977`` (test_hermes_doctor.py).

Diese Wache ist die Netzhaut davor. Sie prueft ZWEI Soll-Zustaende:

  1. **Git-Soll** - jede Datei, die in HEAD unter dem Ordner liegt und im
     Arbeitsbaum fehlt. Das ist genau der T-100-Fall, und er ist ab dem Moment
     sichtbar, in dem die Datei weg ist - also mindestens 30 Minuten BEVOR die
     Routine die Loeschung festnagelt.
  2. **Merkliste** - jede Datei, die beim letzten Lauf noch da war und jetzt
     fehlt. Das faengt auch noch nicht committete Dateien (der Fall vom
     29.09.2026: frisch geschrieben, Minuten spaeter weg, nie in Git gewesen).

Sie **aendert nichts**: kein ``git checkout``, kein Zurueckholen, keine
Loeschung. Sie meldet nur, mit dem fertigen Befehl zum Zurueckholen.

MELDET NUR BEI AUFFAELLIGKEIT (leere Ausgabe = nichts senden). Dieselbe
Feststellung hoechstens einmal je ``RUHE_STUNDEN``; danach erneut, damit ein
offener Befund nicht in Vergessenheit geraet.

Aufruf (Hermes-Cron, no_agent, alle 15 Minuten):
    python Agenten/Hermes/scripts/dateischwund-wache.py
    python Agenten/Hermes/scripts/dateischwund-wache.py --alle      # Lage immer zeigen
    python Agenten/Hermes/scripts/dateischwund-wache.py --ordner <pfad> --merk <datei>
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]                       # scripts -> Hermes -> Agenten -> BrainFiles

RUHE_STUNDEN = 6.0        # dieselbe Feststellung hoechstens alle 6 h
# Bytecode ist kein Soll-Zustand. Die uebrigen Namen sind fuer den zweiten
# Waechter (dateischwund-wache-handel.py) da: ohne sie muesste der Handel
# Ordner samt .venv und Datenbestand gehasht werden, und der Lauf waere so
# teuer, dass die Wache abgeschaltet wird - der Ausfall, den sie verhindern
# soll. Eine Ausnahme kann nur die Sicht verengen, nie eine Datei ausblenden,
# die vorher gemeldet wurde.
AUSLASSEN = {'__pycache__', '.venv', 'venv', 'node_modules', 'target',
             'logs', 'daten', 'cache', 'state', 'docs', '.git'}
# Endungen, die der zweite Waechter gar nicht erst zu sehen bekommt. Der
# erste Grund ist der Laufaufwand: ohne diese Grenze brauchte ein Lauf ueber
# Agenten/Handel viereinhalb MINUTEN, alle fuenfzehn - das ist kein Waechter
# mehr, das ist Last. Der zweite Grund ist die Meldeklasse: Tagessaetze und
# Protokolle werden laufend umgeschrieben und wuerden jeden Lauf als
# "geaendert" fuehren, auch wenn nichts verloren ging.
AUSLASSEN_ENDE = frozenset()
MERK_VORGABE = HIER.parent / 'cache' / 'dateischwund-wache.json'


def _git(wurzel: Path, *args: str) -> str:
    try:
        p = subprocess.run(['git', '-C', str(wurzel), *args],
                           capture_output=True, text=True, errors='replace',
                           timeout=60)
    except (OSError, subprocess.SubprocessError):
        return ''
    return p.stdout if p.returncode == 0 else ''


def git_soll(wurzel: Path, ordner: Path) -> set:
    """Pfade (relativ zur Wurzel), die in HEAD unter ``ordner`` liegen.

    Leere Menge, wenn der Ordner ausserhalb des Repos liegt (Tests) oder git
    nicht antwortet - dann entfaellt die Pruefung still, statt falsch zu melden.
    """
    try:
        rel = ordner.resolve().relative_to(wurzel.resolve()).as_posix()
    except ValueError:
        return set()
    if not rel:
        return set()
    roh = _git(wurzel, 'ls-tree', '-r', '--name-only', 'HEAD', '--', rel)
    return {z.strip() for z in roh.splitlines() if z.strip()}


def ist_ausgelassen(pfad: Path, ordner: Path) -> bool:
    if AUSLASSEN_ENDE and pfad.suffix.lower() in AUSLASSEN_ENDE:
        return True
    return any(t in AUSLASSEN for t in pfad.relative_to(ordner).parts)


def _kennung(pfad: Path) -> tuple:
    try:
        roh = pfad.read_bytes()
    except OSError:
        return (-1, '')
    return (len(roh), hashlib.sha256(roh).hexdigest()[:16])


def stand(ordner: Path) -> dict:
    """{relativer Pfad: [Groesse, SHA256-Kurz]} aller Dateien im Ordner."""
    aus: dict = {}
    if not ordner.is_dir():
        return aus
    for p in sorted(ordner.rglob('*')):
        if not p.is_file() or ist_ausgelassen(p, ordner):
            continue
        groesse, kurz = _kennung(p)
        aus[p.relative_to(ordner).as_posix()] = [groesse, kurz]
    return aus


def _lade(merk: Path) -> dict:
    try:
        d = json.loads(merk.read_text(encoding='utf-8'))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _speichere(merk: Path, d: dict) -> None:
    try:
        merk.parent.mkdir(parents=True, exist_ok=True)
        merk.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                        encoding='utf-8')
    except OSError:
        pass


def _faellig(gemeldet: dict, schluessel: str, jetzt: dt.datetime) -> bool:
    alt = gemeldet.get(schluessel)
    if not alt:
        return True
    try:
        wann = dt.datetime.fromisoformat(alt)
    except (ValueError, TypeError):
        return True
    return (jetzt - wann).total_seconds() >= RUHE_STUNDEN * 3600


def pruefe(ordner: Path, merk: Path, jetzt: dt.datetime | None = None,
           wurzel: Path = WURZEL) -> tuple:
    """Rein rechnend: (Befundzeilen, neuer Merkstand). Schreibt nichts."""
    jetzt = jetzt or dt.datetime.now()
    alt = _lade(merk)
    vorher = alt.get('stand') or {}
    gemeldet = alt.get('gemeldet') or {}
    nachher = stand(ordner)

    befunde = []

    # 1) Git-Soll: in HEAD, aber nicht auf der Platte
    for rel in sorted(git_soll(wurzel, ordner)):
        try:
            voll = wurzel / rel
        except TypeError:                                   # pragma: no cover
            continue
        if not voll.exists():
            befunde.append((
                'git:' + rel,
                'FEHLT, steht aber in HEAD: %s - die Routine fremdarbeit-einziehen '
                'committet das nach 30 Minuten als Loeschung. Zurueckholen: '
                'git checkout HEAD -- %s' % (rel, rel)))

    # 2) Merkliste: beim letzten Lauf da, jetzt weg
    for rel, wert in sorted(vorher.items()):
        if rel in nachher:
            continue
        befunde.append((
            'merk:' + rel,
            'verschwunden seit dem letzten Lauf: %s (war %s B)' % (rel, wert[0])))

    # 3) Datei noch da, Inhalt aber leer geworden (halber Schreibvorgang)
    for rel, wert in sorted(nachher.items()):
        alt_wert = vorher.get(rel)
        if alt_wert and alt_wert[0] > 0 and wert[0] == 0:
            befunde.append((
                'leer:' + rel,
                'auf 0 Byte zusammengefallen: %s (war %s B) - abgebrochener '
                'Schreibvorgang' % (rel, alt_wert[0])))

    neue = []
    for schluessel, text in befunde:
        if _faellig(gemeldet, schluessel, jetzt):
            neue.append(text)
            gemeldet[schluessel] = jetzt.isoformat(timespec='seconds')
    # Aufraeumen: Merker fuer Dateien, die wieder da sind
    for schluessel in list(gemeldet):
        art, _, rel = schluessel.partition(':')
        if art == 'merk' and rel in nachher:
            del gemeldet[schluessel]
    neuer_stand = {'stand': nachher, 'gemeldet': gemeldet,
                   'lauf': jetzt.isoformat(timespec='seconds')}
    return neue, neuer_stand


def pruefe_und_merken(ordner: Path, merk: Path, jetzt: dt.datetime | None = None,
                      wurzel: Path = WURZEL) -> tuple:
    """Pruefen UND den Merkstand schreiben - der Weg, den die Wache geht.

    Liefert (Befundzeilen, neuer Merkstand).
    """
    neue, neuer_stand = pruefe(ordner, merk, jetzt=jetzt, wurzel=wurzel)
    _speichere(merk, neuer_stand)
    return neue, neuer_stand


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Wache auf verschwundene Dateien (T-100)')
    ap.add_argument('--ordner', default=str(HIER),
                    help='zu bewachender Ordner (Vorgabe: dieser Ordner)')
    ap.add_argument('--merk', default=str(MERK_VORGABE),
                    help='Merkdatei (Vorgabe: Hermes/cache/dateischwund-wache.json)')
    ap.add_argument('--alle', action='store_true',
                    help='Lage immer ausgeben, auch ohne Befund')
    ap.add_argument('--jetzt', default=None,
                    help='Bezugszeit (ISO) - nur fuer Gegenproben')
    a = ap.parse_args(argv)

    ordner = Path(a.ordner).resolve()
    merk = Path(a.merk)
    jetzt = None
    if a.jetzt:
        try:
            jetzt = dt.datetime.fromisoformat(a.jetzt)
        except ValueError:
            jetzt = None

    neue, neuer_stand = pruefe_und_merken(ordner, merk, jetzt=jetzt)

    anzahl = len(neuer_stand['stand'])
    if not neue and not a.alle:
        return 0

    print('Dateischwund-Wache %s - %d Datei(en) in %s'
          % (dt.datetime.now().strftime('%d.%m. %H:%M'), anzahl, ordner.name))
    if neue:
        for z in neue:
            print('  - ' + z)
        print('  Nichts wurde geaendert - diese Wache holt nichts zurueck und '
              'loescht nichts.')
    else:
        print('  kein Befund: kein Git-Soll offen, keine Datei seit dem '
              'letzten Lauf verschwunden')
    return 0


if __name__ == '__main__':
    sys.exit(main())