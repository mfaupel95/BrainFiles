#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Unabhaengige Pruefung des Routing-Plans gegen TASKS.md.

Absichtlich ANDERS gebaut als routing_plan_pruefen.py: eigener Zaehlweg,
eigene Markdown-Pruefung, kein Import des Hauspruefers.
Aufruf: python routing_plan_unabhaengig.py <tasks.md> <plan.md>
Exit 0 = gruen, Exit 1 = rot.
"""
import os
import re
import sys

# EIGENER Zaehlweg, aber gemeinsames Warnauge: `VERDAECHTIG` benennt eine
# Zeile, die wie ein Eintrag aussieht und von KEINEM Muster erfasst wurde.
# Geteilt wird nur die Tuer, durch die ein unbemerkter Verlust laufen muss -
# die Breite des Musters bleibt hier bewusst eigenstaendig. Sonst waere
# dieser Weg keine Gegenprobe mehr, sondern dieselbe Enge ein zweites Mal.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kopfformen

KOPF = re.compile(r"^-\s*\[(.)\]\s+\*\*(T-(\d+))\s+(\S)\s*(.*)$")


def offene_ids(tasks):
    zeilen = tasks.replace('\r\n', '\n').split('\n')
    a = next(i for i, z in enumerate(zeilen) if z.strip() == '## Offen')
    b = next(i for i, z in enumerate(zeilen) if z.strip() == '## Erledigt')
    offen, erledigt, ungelesen = [], [], []
    for i, z in enumerate(zeilen[a:b], start=a):
        m = KOPF.match(z)
        if m:
            (erledigt if m.group(1) == 'x' else offen).append(m.group(2))
        elif kopfformen.VERDAECHTIG.match(z):
            ungelesen.append((i + 1, z.strip()))
    return offen, erledigt, ungelesen


def main(tasks_pfad, plan_pfad):
    fehler = []
    roh = open(plan_pfad, 'rb').read()
    if not roh:
        print('ROT: Plan ist 0 Byte')
        return 1
    try:
        text = roh.decode('utf-8')
    except UnicodeDecodeError as e:
        print('ROT: kein UTF-8: %s' % e)
        return 1
    zeilen = text.replace('\r\n', '\n').split('\n')

    offen, erledigt, ungelesen = offene_ids(
        open(tasks_pfad, encoding='utf-8').read())
    if ungelesen:
        fehler.append('%d Zeile(n) im Abschnitt Offen sehen wie ein Eintrag '
                      'aus, werden aber von keinem Muster erfasst: %s'
                      % (len(ungelesen),
                         ', '.join('%d: %s' % (z, t[:60]) for z, t in ungelesen[:5])))
    else:
        print('OK   jede Statuszeichen-Zeile gelesen, 0 unlesbar (%d offen, '
              '%d erledigt)' % (len(offen), len(erledigt)))

    # Markdown: genau eine H1, Ueberschriften-Hierarchie nicht springend,
    # Tabelle mit Kopf/Trennzeile und geschlossener letzter Zeile.
    h1 = [z for z in zeilen if re.match(r'^#\s+\S', z)]
    if len(h1) != 1:
        fehler.append('H1 nicht genau einmal: %d' % len(h1))
    else:
        print('OK   H1: %s' % h1[0][:70])
    ebene = 0
    for z in zeilen:
        m = re.match(r'^(#{1,6})\s+\S', z)
        if m:
            e = len(m.group(1))
            if ebene and e > ebene + 1:
                fehler.append('Ueberschrift springt Ebene %d -> %d: %s' % (ebene, e, z[:50]))
            ebene = e
    kopfz = [i for i, z in enumerate(zeilen) if re.match(r'^\|\s*\d+\s*\|', z)]
    if not kopfz:
        fehler.append('keine Inventartabelle gefunden')
        return report(fehler)
    kopf, trenn = kopfz[0], kopfz[0] - 1
    if not re.match(r'^\|[\s:|-]+\|\s*$', zeilen[trenn]):
        fehler.append('Trennzeile vor der Inventartabelle fehlt/malformed')
    else:
        print('OK   Markdown-Tabelle mit Trennzeile, %d Zeilen'
              % len(kopfz))
    spalten = zeilen[trenn].count('|') - 1
    plan_ids = []
    for z in zeilen[kopf:kopf + len(kopfz)]:
        sp = [s.strip() for s in z.strip().strip('|').split('|')]
        if len(sp) != spalten:
            fehler.append('Spaltenzahl %d != %d: %s' % (len(sp), spalten, z[:60]))
            continue
        ids = re.findall(r'\bT-\d{3,}\b', sp[1])
        if len(ids) != 1:
            fehler.append('Titel ohne genau eine T-ID: %s' % sp[1][:60])
            continue
        plan_ids.append(ids[0])
        for name, inhalt in (('Titel', sp[1]), ('Quelle', sp[2]), ('DoD', sp[3]),
                             ('Blocker', sp[4]), ('Aufwand', sp[5]),
                             ('Profil', sp[6]), ('Begruendung', sp[7])):
            if not inhalt:
                fehler.append('%s leer bei %s' % (name, ids[0]))
        if not re.search(r'`[a-z0-9-]+`', sp[6]):
            fehler.append('Profil ohne Namen bei %s: %s' % (ids[0], sp[6][:40]))

    doppelt = {i for i in plan_ids if plan_ids.count(i) > 1}
    fehlend = [i for i in offen if i not in plan_ids]
    fremd = [i for i in plan_ids if i not in offen]
    tot = [i for i in plan_ids if i in set(erledigt)]
    if doppelt:
        fehler.append('mehrfach im Plan: %s' % sorted(doppelt))
    if fehlend:
        fehler.append('%d offene fehlen im Plan, z.B. %s' % (len(fehlend), fehlend[:5]))
    if fremd:
        fehler.append('nicht-offene im Plan: %s' % fremd[:5])
    if tot:
        fehler.append('erledigte im Plan: %s' % tot[:5])

    # DER Kern der Karte: Zahlengleichheit, explizit.
    gleich = len(plan_ids) == len(offen)
    print('%s   Itemzahl: Plan %d == TASKS.md offen %d -> %s'
          % ('OK  ' if gleich else 'ROT', len(plan_ids), len(offen),
             'GLEICH' if gleich else 'UNGLEICH'))
    if not gleich:
        fehler.append('Itemzahl Plan %d != offen %d' % (len(plan_ids), len(offen)))

    if not fehler:
        print('OK   jeder offene Eintrag genau einmal, kein erledigter dabei, '
              'alle Pflichtspalten gefuellt')
    return report(fehler)


def report(fehler):
    if fehler:
        print('---')
        for f in fehler:
            print('ROT  %s' % f)
        print('Ergebnis: ROT (%d Befund(e))' % len(fehler))
        return 1
    print('Ergebnis: GRUEN')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))