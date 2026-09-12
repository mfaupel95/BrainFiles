"""Feste lesende Telegram-Befehle, ohne Agent oder Order-Import."""
import json
from pathlib import Path
HANDEL = Path(__file__).resolve().parents[1] / 'Handel'

# Reihenfolge der Ausgabe. xperp zuerst (Hauptweg), dann Spot, dann SWAP.
# SWAP wird gelesen wie jede andere Spur; dass sie nicht live geht, steht in
# ihrer eigenen wachen.json und nicht als fester Satz hier - ein Satz, der den
# Stand von gestern behauptet, faellt niemandem auf, wenn die Spur sich bewegt.
SPUREN = ('xperp', 'scanner', 'swap', 'spiegel')


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
                # Die Spuren benennen ihre Positionen verschieden: die
                # Kontraktspuren fuehren inst, die Spiegel-Spur ein Token je
                # Kette. Ohne diesen Griff stuende dort nur ein Fragezeichen.
                instrument = p.get('inst') or '%s %s' % (
                    p.get('symbol', '?'), p.get('kette', ''))
                stop = p.get('stop', p.get('stop_preis', '?'))
                ziel = p.get('ziel', p.get('ziel_preis', '?'))
                lines.append(f"  {instrument} {p.get('seite', 'long')}: Stop {stop}, Ziel {ziel}")
        except (OSError, ValueError, TypeError):
            lines.append(f'{spur}: Zustand nicht lesbar, nicht als leer behandeln.')
    lines.append(papier_lage('swap', 'SWAP'))
    lines.append(papier_lage('spiegel', 'SPIEGEL'))
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
        return ('%s: Papierpfad, kein Live-Zweig. handel_erlaubt=%s, '
                'kein Freigabeblock.' % (anzeige, w.get('handel_erlaubt')))
    return ('%s: Papierpfad, kein Live-Zweig. handel_erlaubt=%s, '
            'Freigabe erfuellt=%s.' % (anzeige, w.get('handel_erlaubt'),
                                       erfuellt))


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
