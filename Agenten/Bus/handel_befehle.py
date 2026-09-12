"""Feste lesende Telegram-Befehle, ohne Agent oder Order-Import."""
import json
from pathlib import Path
HANDEL = Path(__file__).resolve().parents[1] / 'Handel'

# Reihenfolge der Ausgabe. xperp zuerst (Hauptweg), dann Spot, dann SWAP.
# SWAP wird gelesen wie jede andere Spur; dass sie nicht live geht, steht in
# ihrer eigenen wachen.json und nicht als fester Satz hier - ein Satz, der den
# Stand von gestern behauptet, faellt niemandem auf, wenn die Spur sich bewegt.
SPUREN = ('xperp', 'scanner', 'swap')


def status(papier=False):
    lines = ['Lokaler Dateistand (kein Broker-Abgleich).']
    for spur in SPUREN:
        path = HANDEL / spur / 'zustand.json'
        try:
            d = json.loads(path.read_text(encoding='utf-8'))
            mode = d.get('modus', 'unbekannt')
            lines.append(f"{spur}: Modus {mode}, Stand {d.get('letzter_lauf', '?')}")
            if papier and mode != 'papier':
                lines.append('Kein separater Papierstand; Live-Daten nicht als Papier ausgeben.')
                continue
            positions = d.get('positionen', [])
            lines.append(f'{len(positions)} gespeicherte Positionen')
            for p in positions:
                lines.append(f"  {p.get('inst', '?')} {p.get('seite', 'long')}: Stop {p.get('stop', '?')}, Ziel {p.get('ziel', '?')}")
        except (OSError, ValueError, TypeError):
            lines.append(f'{spur}: Zustand nicht lesbar, nicht als leer behandeln.')
    lines.append(swap_lage())
    return '\n'.join(lines)


def swap_lage():
    """Was die SWAP-Spur ist und was sie sperrt - aus ihrer wachen.json.

    Kein fester Satz im Code: Beim Bau dieser Datei gab es die Spur noch nicht,
    und die damalige Zeile ("bewachte Anbindung unvollstaendig") waere nach dem
    Bau des Papierpfads stehen geblieben - sie haette gestimmt, als sie
    geschrieben wurde, und danach nichts mehr bedeutet. Gelesen werden die zwei
    Werte, die die Spur selbst fuehrt.

    Der fehlende Live-Zweig steht als Tatsache daneben, nicht als Wert in der
    Datei: swap/handeln.py verweigert --live mit genau einem Grund. Nachweisbar
    mit `python handeln.py --live` im Ordner der Spur.
    """
    try:
        w = json.loads((HANDEL / 'swap' / 'wachen.json').read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return ('SWAP: wachen.json nicht lesbar - Lage unbekannt, nicht als '
                '"gesperrt" ausgeben.')
    freigabe = w.get('freigabe') or {}
    return ('SWAP: Papierpfad, kein Live-Zweig. handel_erlaubt=%s, '
            'Freigabe erfuellt=%s.' % (w.get('handel_erlaubt'),
                                       freigabe.get('erfuellt')))


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
    return ('Prognose: bestehende Spot-Marktbeobachtung, kein SWAP-Signal, keine Order.\n'
            + (p.stdout or 'Keine Ausgabe.')
            + ('\nTeilabfragen fehlgeschlagen; Ergebnis unvollstaendig.' if p.stderr else ''))
