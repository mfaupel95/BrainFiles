#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gegenprobe: die Pruefer MUESSEN bei Abweichungen rot werden.

Zwei Arten von Gegenprobe, weil zwei Arten von Verlust möglich sind:

1. AM PLAN (MUTATIONEN): der Plan wird verletzt - Zeile weg, doppelt,
   DoD geleert, fremder Assignee, Welle falsch gekennzeichnet, Abschnitt auf
   falscher Ebene. Erwartet wird jedes Mal ein roter Lauf mit Begruendung.
2. AN DER QUELLE (QUELLMUTATIONEN): TASKS.md traegt Kopfformen, die kein
   Muster kennt. Ein stillschweigend nicht gelesener Eintrag faellt auf BEIDEN
   Seiten weg und laesst die Zahlengleichheit gruen - genau so sind am
   04.10.2026 47 offene Punkte verschwunden. Deshalb wird eine Quelle
   gebaut, die GUELTIGE Zeilen enthaelt, die kein Muster liest: der Bauer
   muss abbrechen, der Pruefer muss rot melden.

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

# Kopfform, die wie ein Eintrag aussieht, aber von KEINEM Muster erfasst
# wird: kein Trennzeichen zwischen Nummer und Titel. Sie muss auch den
# WEITESTEN Leser (Titelanfang = ein beliebiges Zeichen) uebertreffen,
# sonst prueft die Gegenprobe nur die Enge, nicht die Regel.
UNLESBAR = '- [ ] **T-901** Kopf ohne Trennzeichen vor dem Titel'

# GUELTIGE Quellformen, die der alte Bauer/pruefer uebersah: ASCII-
# Bindestrich (fremde Hand) und ein Titel, der ohne schliessendes '**'
# umbricht. Beide muessen im Plan landen.
ASCII_FORM = '- [ ] **T-902 - Zweiter Punkt mit ASCII-Bindestrich**'
UMBROCHEN_FORM = ('- [ ] **T-903 — Dritter Punkt, Titel bricht ohne '
                  'schliessende Sternchen um')

# Der Roster des Hauspruefers - die Gegenprobe braucht ihn, um eine echte
# Profilspalte zu finden statt einen Namen zu raten.
ROSTER = ('hermes-wartung', 'basic-memory', 'agent-trade-kit',
          'markt-recherche', 'nerd', 'lotse', 'default')


def zeilen_mit_id(text, tid):
    return [z for z in text.split('\r\n') if re.match(r'^\| \d+ \|', z)
            and re.search(r'\b%s\b' % tid, z.split('|')[2])]


def mutieren(text, art):
    # Das Zeilenende kommt aus der Datei, nicht aus einer Annahme: der
    # Builder schreibt CRLF nur, weil TASKS.md CRLF traegt. Eine LF-Quelle
    # liess diese Funktion als EINE Zeile und liess sie leer aus - die
    # Gegenprobe meldete dann IndexError statt eines Befunds.
    nl = '\r\n' if '\r\n' in text else '\n'
    zeilen = [z for z in text.split(nl) if re.match(r'^\| \d+ \|', z)]
    if len(zeilen) < 5:
        raise ValueError('zu kleine Attrappe fuer die Gegenprobe: %d '
                         'Tabellenzeilen' % len(zeilen))
    if art == 'zeile_weg':
        return text.replace(zeilen[-1] + nl, '', 1), 'offener Eintrag entfernt'
    if art == 'zeile_doppelt':
        return text.replace(zeilen[1] + nl, zeilen[0] + nl + zeilen[1] + nl, 1), \
            'Eintrag doppelt gelistet'
    if art == 'dod_leer':
        sp = zeilen[3].split('|')
        sp[4] = '  '
        return text.replace(zeilen[3] + nl, '|'.join(sp) + nl, 1), \
            'Definition of Done geleert'
    if art == 'fremder_assignee':
        # Den Roster-Namen aus dem Plan SELBST nehmen. Eine Festlegung auf
        # 'markt-recherche' war eine Annahme: in einer Attrappe ohne
        # Marktpfad kommt das Wort nicht vor, die Mutation bleibt leer, der
        # Pruefer bleibt gruen - und die Gegenprobe meldete sich selbst
        # gruen, weil sie nur den Exitcode zaehlt.
        zeilen_ernst = [z for z in zeilen
                        if any('`%s`' % r in z for r in ROSTER)]
        if not zeilen_ernst:
            raise ValueError('keine Roster-Zeile in der Attrappe: %d'
                             % len(zeilen))
        alt = next('`%s`' % r for r in ROSTER if '`%s`' % r in zeilen_ernst[0])
        return text.replace(alt, '`maximilian`', 1), \
            'Assignee steht nicht im Roster (aus %s)' % alt
    if art == 'welle_falsch_gekennzeichnet':
        return text.replace('### Welle 1 — parallel', '### Welle 1 — sequenziell', 1), \
            '105 Eintraege als sequenziell gekennzeichnet'
    if art == 'abschnitt_fehlt':
        return text.replace('## (d) Leerzustand', '### (d) Leerzustand', 1), \
            'Abschnitt (d) auf falscher Ebene (nicht mehr als Abschnitt auffindbar)'
    raise ValueError(art)


QUELLE_KOPF = ('# Test\n\n## Offen\n\n'
               '- [ ] **T-900 — Erstpunkt in Hausform**\n'
               '      Kontext: reiner Attrappen-Eintrag fuer die Gegenprobe.\n'
               '      Naechster Schritt: nichts tun, die Gegenprobe laeuft nur.\n\n'
               '## Erledigt\n\n'
               '- [x] **T-950 — Alter Punkt, erledigt**\n')


def quelle_mit(zusatz):
    """Testquelle mit den gueltigen Fremdformen (ASCII, Umbruch)."""
    return QUELLE_KOPF.replace('## Erledigt', zusatz + '\n## Erledigt')


def lauf(werkzeug, args):
    ordner = os.path.dirname(os.path.abspath(__file__))
    return subprocess.run([sys.executable, os.path.join(ordner, werkzeug)] + args,
                          capture_output=True, text=True)


def quelle_gegenproben():
    """Gueltige Fremdformen muessen gelesen, eine fremde Form muss auffallen.

    Drei Laeufe gegen eine Attrappen-Quelle, die keine echte TASKS.md
    braucht: (a) Bauer baut aus ASCII- und Umbruch-Form, (b) Bauer bricht
    bei der unlesbaren Form ab, (c) Pruefer meldet die unlesbare Form rot -
    auch dann noch, wenn der Plan (gefaelscht) ohne sie gebaut wurde.
    """
    fehler = []
    ordner = tempfile.mkdtemp()
    quellen = {}
    try:
        pfad_gut = os.path.join(ordner, 'gut.md')
        with open(pfad_gut, 'w', encoding='utf-8', newline='') as fh:
            fh.write(quelle_mit(ASCII_FORM + '\n' + UMBROCHEN_FORM + '\n'))
        quellen['gut'] = pfad_gut

        ziel = os.path.join(ordner, 'plan.md')
        r = lauf('routing_plan_bauen.py', [pfad_gut, ziel])
        if r.returncode != 0:
            fehler.append('Bauer brach auf gueltigen Fremdformen ab: %s'
                          % r.stderr.strip()[-160:])
        else:
            text = open(ziel, encoding='utf-8').read()
            for tid, was in (('T-900', 'Hausform'),
                             ('T-902', 'ASCII-Bindestrich'),
                             ('T-903', 'Titel ohne schliessendes **')):
                if text.count(tid) < 2:      # Inventarzeile + Welle
                    fehler.append('%s (%s) fehlt im Plan' % (tid, was))
            if 'T-950' in text:
                fehler.append('erledigtes T-950 steht im Plan')
            if not fehler:
                print('OK   %-32s -> ASCII-Bindestrich und Umbruch-Titel '
                      'gelesen' % 'quellenform_ascii_und_umbruch')

        pfad_schlecht = os.path.join(ordner, 'unlesbar.md')
        with open(pfad_schlecht, 'w', encoding='utf-8', newline='') as fh:
            fh.write(quelle_mit(UNLESBAR + '\n'))
        r = lauf('routing_plan_bauen.py', [pfad_schlecht,
                                           os.path.join(ordner, 'plan2.md')])
        if r.returncode == 0:
            fehler.append('Bauer blieb bei einer unlesbaren Kopfform GRUEN')
        elif 'Abbruch' not in (r.stdout + r.stderr):
            fehler.append('Bauer brach ab, aber ohne benennten Grund: %s'
                          % (r.stdout + r.stderr).strip()[-140:])
        else:
            erst = [z for z in (r.stdout + r.stderr).splitlines()
                    if z.startswith('Abbruch')]
            print('OK   %-32s -> %s' % ('quellenform_unlesbar_baut_ab',
                                        erst[0][7:].lstrip(': ')[:80] if erst
                                        else '?'))

        # Der Plan aus dem Lauf ohne die unlesbare Form MUSS rot sein,
        # sobald dieselbe Quelle die unlesbare Zeile enthaelt.
        ziel3 = os.path.join(ordner, 'plan3.md')
        r = lauf('routing_plan_bauen.py', [pfad_gut, ziel3])
        r = lauf('routing_plan_pruefen.py', [pfad_schlecht, ziel3])
        if r.returncode == 0:
            fehler.append('Pruefer blieb GRUEN, obwohl die Quelle eine Zeile '
                          'enthaelt, die kein Muster liest')
        elif 'sehen wie ein Eintrag aus' not in r.stdout:
            fehler.append('Pruefer rot, aber ohne den Befund "sehen wie ein '
                          'Eintrag aus": %s' % r.stdout.strip()[-140:])
        else:
            print('OK   %-32s -> %s' % ('pruefer_meldet_unlesbar',
                                        [z for z in r.stdout.splitlines()
                                         if z.startswith('FEHL')][0][5:95]))

        r = lauf('routing_plan_unabhaengig.py', [pfad_schlecht, ziel3])
        if r.returncode == 0:
            fehler.append('Unabhaengiger Pruefer blieb bei unlesbarer Quelle '
                          'GRUEN')
        else:
            print('OK   %-32s -> unabhaengiger Pruefer rot' %
                  'unabhaengig_meldet_unlesbar')
    finally:
        shutil.rmtree(ordner, ignore_errors=True)
    return fehler


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

    fehler += quelle_gegenproben()

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
          % ('GRUEN' if not fehler else 'ROT', len(fehler),
             len(MUTATIONEN) + 5))
    sys.exit(1 if fehler else 0)


if __name__ == '__main__':
    main()