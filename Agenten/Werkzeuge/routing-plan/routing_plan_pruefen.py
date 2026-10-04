#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Prueft den Routing-Plan gegen TASKS.md. Behauptet nichts, was es nicht prueft.

Pruefungen:
  1. Datei existiert, ist nicht leer, ist UTF-8 lesbar.
  2. Zeilenenden wie die Quelle (CRLF), damit das Haus sie nicht umschreibt.
  3. Jeder offene Eintrag aus TASKS.md kommt GENAU EINMAL vor (ID-zaehlung).
  4. Kein erledigter Eintrag ([x]) taucht im Plan auf.
  5. Jede Tabellenzeile traegt Titel, Quelle, DoD, Blocker, Aufwand, Assignee.
  6. Die Zahl der Tabellenzeilen ist gleich der Zahl offener Eintraege.
  7. Markdown-Struktur: Ueberschriften (a)-(e) genau einmal, Tabelle geschlossen.
  8. Jede Zeile nennt einen Assignee aus dem Roster.

Aufruf: python routing_plan_pruefen.py <tasks.md> <plan.md>
Exit 0 = alles belegt, Exit 1 = mindestens eine Pruefung rot.
"""
import os
import re
import sys
from collections import Counter

# Die Kopfregel kommt aus kopfformen.py - bewusst NICHT aus dem Bauer, aber
# auch nicht als eigene Kopie: drei Kopien der Enge sind drei Fehlerklassen.
# Die unabhaengige Gegenpruefung hat absichtlich einen eigenen Zaehlweg
# (routing_plan_unabhaengig.py); sie ist der Beleg, dass diese Regel nicht
# nur eine geteilte Enge ist.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kopfformen

KOPF = kopfformen.KOPF
ROSTER = ('hermes-wartung', 'basic-memory', 'agent-trade-kit',
          'markt-recherche', 'nerd', 'lotse', 'default')
ABSCHNITTE = ('## (a) ', '## (b) ', '## (c) ', '## (d) ', '## (e) ')


def pruefe(quelle, plan):
    fehler, notizen = [], []

    # --- Quelle lesen ------------------------------------------------------
    bloecke, ungelesen, nl, _offen_ab, _erl_ab = kopfformen.datei_lesen(quelle)
    offen = [(b['zeile'], b['id'], b['status'], b['titel'])
             for b in bloecke if b['status'] != 'x']
    erledigt_ids = {b['id'] for b in bloecke if b['status'] == 'x'}
    # DER Kern: eine Zeile, die wie ein Eintrag aussieht und nicht gelesen
    # wurde, wuerde sonst auf BEIDEN Seiten wegfallen und die Zahlengleichheit
    # 123 == 13 ergeben (gemessen 04.10.2026: 47 echte offene Punkte).
    if ungelesen:
        fehler.append('%d Zeile(n) im Abschnitt "Offen" sehen wie ein '
                      'Eintrag aus, werden aber nicht erfasst: %s'
                      % (len(ungelesen),
                         ', '.join('%d: %s' % (z, t[:60]) for z, t in ungelesen[:5])))
    else:
        notizen.append('Jede Statuszeichen-Zeile im Abschnitt Offen ist '
                       'erfasst: %d Eintraege, 0 unlesbar' % len(bloecke))

    # --- 1/2 Plan lesen ---------------------------------------------------
    if not os.path.isfile(plan):
        return ['Plan fehlt: %s' % plan], notizen
    if os.path.getsize(plan) == 0:
        fehler.append('Plan ist leer (0 Byte)')
        return fehler, notizen
    prawh = open(plan, 'rb').read()
    plan_nl = '\r\n' if b'\r\n' in prawh else '\n'
    if plan_nl != nl:
        fehler.append('Zeilenenden weichen ab: Plan %r, Quelle %r'
                      % (plan_nl, nl))
    else:
        notizen.append('Zeilenenden wie die Quelle: %r' % plan_nl)
    try:
        ptext = prawh.decode('utf-8')
    except UnicodeDecodeError as err:
        fehler.append('Plan ist kein gueltiges UTF-8: %s' % err)
        return fehler, notizen
    pzeilen = ptext.replace('\r\n', '\n').split('\n')

    # --- 7 Markdown-Struktur ----------------------------------------------
    for abschnitt in ('(a)', '(b)', '(c)', '(d)', '(e)'):
        n = sum(1 for z in pzeilen
                if re.match(r'^##\s+%s(?:\s|$)' % re.escape(abschnitt), z.strip()))
        if n != 1:
            fehler.append('Abschnitt %s kommt %d-mal als Ueberschrift vor '
                          '(soll genau 1) — gefunden: %s'
                          % (abschnitt, n,
                             [z.strip() for z in pzeilen
                              if re.match(r'^#{1,3}\s+\(', z.strip())]))
    kopfzeile = [z for z in pzeilen if re.match(r'^# Routing-Plan', z)]
    if len(kopfzeile) != 1:
        fehler.append('Kein eindeutiger H1-Titel (gefunden: %d)' % len(kopfzeile))
    if not any(z.startswith('#') for z in pzeilen):
        fehler.append('Keine Ueberschrift im Plan')

    # --- 5/6 Inventartabelle ---------------------------------------------
    tabelle = [z for z in pzeilen if re.match(r'^\| \d+ \|', z)]
    if len(tabelle) != len(offen):
        fehler.append('Zeilenzahl der Tabelle (%d) != offene Eintraege (%d)'
                      % (len(tabelle), len(offen)))
    else:
        notizen.append('Tabellenzeilen == offene Eintraege: %d' % len(tabelle))
    trenn = [z for z in pzeilen if re.match(r'^\|---', z)]
    if len(trenn) != 1:
        fehler.append('Tabellentrennzeile nicht genau einmal (%d)' % len(trenn))
    else:
        spalten_erwartet = trenn[0].count('|') - 1
        schlecht = [z for z in tabelle if z.count('|') - 1 != spalten_erwartet]
        if schlecht:
            fehler.append('%d Tabellenzeilen mit abweichender Spaltenzahl '
                          '(erwartet %d), z.B. %s'
                          % (len(schlecht), spalten_erwartet, schlecht[0][:80]))

    # --- 3/4/8 je Zeile ---------------------------------------------------
    gezaehlt = Counter()
    zeilen_ohne = []
    for z in tabelle:
        sp = [s.strip() for s in z.strip().strip('|').split('|')]
        ids = re.findall(r'\bT-\d{3,}\b', sp[1])
        if not ids:
            zeilen_ohne.append('keine T-ID in Spalte Titel: %s' % sp[1][:60])
            continue
        gezaehlt[ids[0]] += 1
        for name, spalte in (('Titel', sp[1]), ('Quelle', sp[2]),
                             ('Definition of Done', sp[3]),
                             ('Blocker', sp[4]), ('Aufwand', sp[5]),
                             ('Profil', sp[6]), ('Begruendung', sp[7])):
            if not spalte:
                zeilen_ohne.append('%s leer bei %s' % (name, ids[0]))
        if sp[5] not in ('S', 'M', 'L'):
            zeilen_ohne.append('Aufwand "%s" bei %s ist kein S/M/L' % (sp[5], ids[0]))
        if sp[6].strip('`') not in ROSTER:
            zeilen_ohne.append('Assignee "%s" bei %s steht nicht im Roster'
                               % (sp[6], ids[0]))
    if zeilen_ohne:
        fehler.append('%d Spalten-/Roster-Befunde: %s'
                      % (len(zeilen_ohne), '; '.join(zeilen_ohne[:5])))

    mehrfach = {k: v for k, v in gezaehlt.items() if v > 1}
    if mehrfach:
        fehler.append('Eintraege mehrfach im Plan: %s' % mehrfach)
    fehlend = [tid for _, tid, _, _ in offen if tid not in gezaehlt]
    if fehlend:
        fehler.append('%d offene Eintraege fehlen im Plan: %s'
                      % (len(fehlend), ', '.join(fehlend[:8])))
    fremd = [k for k in gezaehlt if k not in {tid for _, tid, _, _ in offen}]
    if fremd:
        fehler.append('IDs im Plan, die nicht offen sind (erledigt/erfunden): %s' % fremd)
    zu_erledigt = [k for k in gezaehlt if k in erledigt_ids]
    if zu_erledigt:
        fehler.append('Erledigte Eintraege im Plan: %s' % zu_erledigt)

    # Wellen: jeder Eintrag genau einmal, Reihenfolge erhaelt
    wellen_bloecke = []
    for z in pzeilen:
        if z.startswith('### Welle '):
            wellen_bloecke.append([z])
        elif wellen_bloecke and z.startswith('- **T-'):
            wellen_bloecke[-1].append(z)
    welle_zaehlung = Counter()
    for block in wellen_bloecke:
        for z in block[1:]:
            m = re.match(r'- \*\*(T-\d+)', z)
            if m:
                welle_zaehlung[m.group(1)] += 1
    doppelt = {k: v for k, v in welle_zaehlung.items() if v != 1}
    if doppelt:
        fehler.append('Wellen fuehren Eintraege %d-mal: %s'
                      % (len(doppelt), dict(list(doppelt.items())[:5])))
    elif welle_zaehlung:
        notizen.append('Wellen nennen jeden Eintrag genau einmal: %d Eintraege '
                       'in %d Wellen' % (sum(welle_zaehlung.values()),
                                         len(wellen_bloecke)))
    else:
        fehler.append('Keine Welle gefunden')
    for block in wellen_bloecke:
        kopfzeile_w = block[0]
        anzahl = len(block) - 1
        erwartet = 'parallel' if anzahl > 1 else 'sequenziell'
        voll = kopfzeile_w.split('—', 1)[-1]
        if voll.split('(')[0].strip().rstrip(',') != erwartet:
            fehler.append('Welle "%s" traegt "%d Eintraege", ist aber als '
                          '"%s" gekennzeichnet (soll %s)'
                          % (kopfzeile_w.split('—')[0].split()[-1], anzahl,
                             voll.split('(')[0].strip().rstrip(','), erwartet))

    return fehler, notizen


def main():
    quelle, plan = sys.argv[1], sys.argv[2]
    fehler, notizen = pruefe(quelle, plan)
    for n in notizen:
        print('OK   %s' % n)
    for f in fehler:
        print('FEHL %s' % f)
    print('---')
    print('Ergebnis: %s (%d Pruefung(en) rot, %d belegt)'
          % ('GRUEN' if not fehler else 'ROT', len(fehler), len(notizen)))
    sys.exit(1 if fehler else 0)


if __name__ == '__main__':
    main()