"""Feste lesende Telegram-Befehle, ohne Agent oder Order-Import.

Der Text der Handelsbefehle steht in `Handel/befehle.py` - EINE Quelle fuer
den Handelsbot (dauerlauf.py) und den SkillsBot. Hier stehen nur die zwei
Befehle, die es NUR hier gibt (`status`, `papierstatus`) und die duennen
Durchreicher auf `befehle.py`. Eine zweite Fassung von /lage waere eine
zweite Wahrheit: der Handelsbot zeigte dann etwas anderes als der SkillsBot.

Geladen wird `befehle.py` erst beim Aufruf (nicht beim Import dieses Moduls):
so bleibt der Bus-Prozess schlank, und ein Fehler in der Handelsseite reisst
nicht den ganzen Bus mit.
"""
import json
import sys
from pathlib import Path
HANDEL = Path(__file__).resolve().parents[1] / 'Handel'


def _handel():
    """`Handel/befehle.py` laden - der Handel-Ordner muss im Suchpfad stehen."""
    if str(HANDEL) not in sys.path:
        sys.path.append(str(HANDEL))
    import befehle as handelsbefehle
    return handelsbefehle


def lage():
    return _handel().lage()


def live():
    """Nur die Spuren mit Orderweg - der reine Live-Stand."""
    return _handel().live()


def spur(name):
    return _handel().spur(name)


def strategien():
    return _handel().strategien()


def indikatoren():
    return _handel().indikatoren()


def markt():
    return _handel().markt()


def spuren():
    return _handel().spuren()


def klartext(text):
    """HTML-Marken fuer den SkillsBot entfernen (der sendet ohne parse_mode)."""
    return _handel().klartext(text)


def bericht():
    """Der volle Tagesbericht - derselbe Aufruf wie im Handelsbot."""
    return _handel().bericht()


def _spurliste():
    """Die Spurliste aus `dauerlauf.SPUREN` (ueber `befehle.py`).

    Die eigene Liste darunter bleibt als RUECKFALL: faellt die Handelsseite
    aus, soll /status weiter antworten statt zu verstummen. Eine Liste, die
    nur hier steht, altert beim naechsten neuen Spurordner still.
    """
    try:
        namen = _handel().spuren()
    except Exception:                                         # noqa: BLE001
        namen = []
    return namen or list(SPUREN)


# Reihenfolge der Ausgabe. xperp zuerst (Hauptweg), dann Spot, dann die beiden
# Papierspuren. Wie eine Spur gerade steht, steht in ihrer eigenen wachen.json
# und ihrem Zustand - nicht als fester Satz hier: SWAP hat seit dem 12.09.2026
# einen Live-Pfad, ein "ist Papier" waere die zweite Wahrheit, die als erste
# alt wird.
SPUREN = ('xperp', 'scanner', 'swap', 'spiegel', 'orbk', 'omniquant',
    'nautilus', 'gitter', 'kopier', 'kraken',
    'macd_mtf', 'squeeze', 'supertrend', 'wavetrend', 'mosaic')


def status(papier=False):
    lines = ['Lokaler Dateistand (kein Broker-Abgleich).']
    # Die Liste kommt aus dauerlauf.SPUREN (siehe _spurliste): eine neue Spur
    # erscheint hier damit von selbst - bis 15.09.2026 stand sie still.
    for spur in _spurliste():
        path = HANDEL / spur / 'zustand.json'
        try:
            d = json.loads(path.read_text(encoding='utf-8'))
            mode = d.get('modus', 'unbekannt')
            lines.append(f"{spur}: Modus {mode}, Stand {d.get('letzter_lauf', '?')}")
            if papier and mode != 'papier':
                lines.append('Kein separater Papierstand; Live-Daten nicht als Papier ausgeben.')
                continue
            # Die ORB-Spur fuehrt hoechstens eine Position unter 'position'
            # (Einzelwert), alle anderen unter 'positionen' (Liste).
            positions = d.get('positionen')
            if positions is None:
                einzel = d.get('position')
                positions = [einzel] if einzel else []
            lines.append(f'{len(positions)} gespeicherte Positionen')
            for p in positions:
                # Die Spuren benennen ihre Positionen verschieden: die
                # Kontraktspuren fuehren inst, die Spiegel-Spur ein Token je
                # Kette. Ohne diesen Griff stuende dort nur ein Fragezeichen.
                instrument = p.get('inst') or '%s %s' % (
                    p.get('symbol', '?'), p.get('kette', ''))
                stop = p.get('stop', p.get('stop_preis', '?'))
                ziel = p.get('ziel', p.get('ziel_preis', '?'))
                seite = p.get('seite') or p.get('richtung') or 'long'
                lines.append(f"  {instrument} {seite}: Stop {stop}, Ziel {ziel}")
        except (OSError, ValueError, TypeError):
            lines.append(f'{spur}: Zustand nicht lesbar, nicht als leer behandeln.')
    lines.append(papier_lage('swap', 'SWAP'))
    lines.append(papier_lage('spiegel', 'SPIEGEL'))
    lines.append(papier_lage('nautilus', 'NAUTILUS'))
    return '\n'.join(lines)


def papier_lage(spur, anzeige):
    """Was eine Papierspur ist und was sie sperrt - aus ihrer wachen.json.

    Kein fester Satz im Code: Beim Bau dieser Datei gab es die Spuren noch
    nicht, und die damalige Zeile ("bewachte Anbindung unvollstaendig") waere
    nach dem Bau der Papierpfade stehen geblieben - sie haette gestimmt, als
    sie geschrieben wurde, und danach nichts mehr bedeutet. Gelesen werden die
    zwei Werte, die die Spur selbst fuehrt.

    Der fehlende Live-Zweig steht als Tatsache daneben, nicht als Wert in der
    Datei: das jeweilige --live verweigert mit genau einem Grund.
    Nachweisbar mit `python <skript>.py --live` im Ordner der Spur.
    """
    try:
        w = json.loads((HANDEL / spur / 'wachen.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return ('%s: wachen.json nicht lesbar - Lage unbekannt, nicht als '
                '"gesperrt" ausgeben.' % anzeige)
    freigabe = w.get('freigabe') or {}
    erfuellt = freigabe.get('erfuellt')
    if erfuellt is None:
        # Eine Spur ohne Freigabeblock (die Spiegel-Spur kennt keine
        # Bedingung 1, sie hat keinen Live-Zweig): "None" waere hier eine
        # Auskunft, die wie ein fehlender Wert aussieht.
        return ('%s: handel_erlaubt=%s, kein Freigabeblock.'
                % (anzeige, w.get('handel_erlaubt')))
    # Kein Satz ueber den Live-Zweig: SWAP hat seit dem 12.09.2026 einen
    # (nach xperp-Muster, mit eigener Freigabekette). Ob einer da ist, steht
    # nicht in dieser Datei - was hier steht, sind die zwei Werte, die die
    # Spur fuehrt.
    return ('%s: handel_erlaubt=%s, Freigabe erfuellt=%s.'
            % (anzeige, w.get('handel_erlaubt'), erfuellt))


def prognose(text):
    import os
    import subprocess
    parts = text.split()
    if len(parts) > 2 or (len(parts) == 2 and (not parts[1].isdigit() or not 1 <= int(parts[1]) <= 200)):
        return 'Syntax: /prognose [1..200], ohne Zahl ganzer Markt. Nur Analyse.'
    args = [str(HANDEL / 'scanner' / '.venv' / 'Scripts' / 'python.exe'), str(HANDEL / 'prognose.py'), '--kurz']
    if len(parts) == 2:
        args += ['--werte', parts[1]]
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    env['PYTHONIOENCODING'] = 'utf-8'
    try:
        p = subprocess.run(args, cwd=str(HANDEL), env=env, capture_output=True,
                           text=True, encoding='utf-8', errors='replace', timeout=240)
    except subprocess.TimeoutExpired:
        return 'Prognose nach 240 s abgebrochen. Mit /prognose 20 kleiner pruefen.'
    if p.returncode not in (0, 1):
        return 'Prognose gescheitert (Code %s). Lokal pruefen.' % p.returncode
    return ('Prognose: Marktbeobachtung ueber alle Spot-Paare, long und short '
            '(Richtung steht in der Tabelle), keine Order.\n'
            + (p.stdout or 'Keine Ausgabe.')
            + ('\nTeilabfragen fehlgeschlagen; Ergebnis unvollstaendig.' if p.stderr else ''))
