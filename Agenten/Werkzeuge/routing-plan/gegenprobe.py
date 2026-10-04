#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gegenprobe: der Pruefer MUSS bei Manipulationen am Plan rot werden.

Nimmt den erzeugten Plan, verletzt ihn fuenfmal auf verschiedene Art und
verlangt von jedem Lauf einen Exit != 0 mit einer benannten Begruendung.
Ein Pruefer, der immer gruen sagt, ist schlechter als keiner.

Aufruf: python gegenprobe.py <tasks.md> <plan.md>
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

MUTATIONEN = ('zeile_weg', 'zeile_doppelt', 'dod_leer', 'fremder_assignee',
               'welle_falsch_gekennzeichnet', 'abschnitt_fehlt')


def zeilen_mit_id(text, tid):
    return [z for z in text.split('\r\n') if re.match(r'^\| \d+ \|', z)
            and re.search(r'\b%s\b' % tid, z.split('|')[2])]


def mutieren(text, art):
    zeilen = [z for z in text.split('\r\n') if re.match(r'^\| \d+ \|', z)]
    if art == 'zeile_weg':
        return text.replace(zeilen[-1] + '\r\n', '', 1), 'offener Eintrag entfernt'
    if art == 'zeile_doppelt':
        return text.replace(zeilen[1] + '\r\n', zeilen[0] + '\r\n' + zeilen[1] + '\r\n', 1), \
            'Eintrag doppelt gelistet'
    if art == 'dod_leer':
        sp = zeilen[3].split('|')
        sp[4] = '  '
        return text.replace(zeilen[3] + '\r\n', '|'.join(sp) + '\r\n', 1), \
            'Definition of Done geleert'
    if art == 'fremder_assignee':
        return text.replace('`markt-recherche`', '`maximilian`', 1), \
            'Assignee steht nicht im Roster'
    if art == 'welle_falsch_gekennzeichnet':
        return text.replace('### Welle 1 — parallel', '### Welle 1 — sequenziell', 1), \
            '105 Eintraege als sequenziell gekennzeichnet'
    if art == 'abschnitt_fehlt':
        return text.replace('## (d) Leerzustand', '### (d) Leerzustand', 1), \
            'Abschnitt (d) auf falscher Ebene (nicht mehr als Abschnitt auffindbar)'
    raise ValueError(art)


def main():
    quelle, plan = sys.argv[1], sys.argv[2]
    original = open(plan, 'rb').read()
    fehler = []
    for art in MUTATIONEN:
        neu, was = mutieren(original.decode('utf-8'), art)
        pfad = os.path.join(tempfile.mkdtemp(), 'plan.md')
        with open(pfad, 'w', encoding='utf-8', newline='') as fh:
            fh.write(neu)
        r = subprocess.run([sys.executable, os.path.join(os.path.dirname(
            os.path.abspath(__file__)), 'routing_plan_pruefen.py'), quelle, pfad],
            capture_output=True, text=True)
        erkannt = [z for z in r.stdout.splitlines() if z.startswith('FEHL')]
        if r.returncode == 0:
            fehler.append('%s: Pruefer blieb GRUEN (%s)' % (art, was))
        elif not erkannt:
            fehler.append('%s: rot, aber ohne Begruendung' % art)
        else:
            print('OK   %-32s -> %s' % (art, erkannt[0][5:90]))
        shutil.rmtree(os.path.dirname(pfad), ignore_errors=True)

    # und zum Schluss das unveraenderte Original: muss gruen sein
    r = subprocess.run([sys.executable, os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'routing_plan_pruefen.py'), quelle, plan],
        capture_output=True, text=True)
    if r.returncode != 0:
        fehler.append('Original ist rot: %s' % r.stdout.strip()[-120:])
    else:
        print('OK   %-32s -> GRUEN (Exit 0)' % 'unveraendertes Original')
    for f in fehler:
        print('FEHL %s' % f)
    print('---')
    print('Ergebnis: %s (%d von %d Gegenproben unentdeckt)'
          % ('GRUEN' if not fehler else 'ROT', len(fehler), len(MUTATIONEN) + 1))
    sys.exit(1 if fehler else 0)


if __name__ == '__main__':
    main()