#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Prueft die Worklist gegen TASKS.md. Behauptet nichts, was es nicht prueft.

Aufruf:
  python routing_worklist_pruefen.py <tasks.md> <worklist.json> [--plan <plan.md>]

Pruefungen:
  1. Datei existiert, ist nicht leer, ist gueltiges JSON.
  2. Jeder offene Eintrag aus TASKS.md kommt GENAU EINMAL vor (ID-Menge und
     ID-Haeufigkeit) - die Karte verlangt 'genau einmal', nicht 'mindestens
     einmal'.
  3. Kein erledigter Eintrag ([x]) taucht in der Worklist auf.
  4. Jeder Eintrag traegt id, titel, abnahmekriterium, assignee und bucket.
  5. Jeder Eintrag traegt ein Abnahmekriterium mit offengelegter Herkunft
     (explicit / derived_kontext / derived_titel).
  6. bucket ist genau PARALLEL oder ORDERED; PARALLEL hat Welle 1, ORDERED
     hat Welle > 1 - ein ORDERED mit Welle 1 waere eine Behauptung ohne
     Querverweis.
  7. Die gemeldeten Buckets stimmen mit der Zahl der Eintraege ueberein.
  8. Assignee steht im Roster der Profile.
  9. Die Kopfzeilenzahl stimmt mit der Zahl der Eintraege ueberein.
 10. Leerfall: TASKS.md ohne offene Punkte -> leere Worklist mit Befund.

Exit 0 = alles belegt, Exit 1 = mindestens eine Pruefung rot.
"""
import os
import re
import sys
import json
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from routing_worklist_bauen import plan_wellen, lies_text  # eine Quelle fuer beides

KOPF = re.compile(r'^-\s*\[(.)\]\s+\*\*(T-(\d+))\s+[\u2014\u2013-]\s*(.+?)\*\*(.*)$')
KOPF_UNTERMITT = re.compile(r'^-\s*\[(.)\]\s+\*\*(T-(\d+))\s+[\u2014\u2013-]\s*(.+?)\s*$')
ROSTER = ('hermes-wartung', 'basic-memory', 'agent-trade-kit',
          'markt-recherche', 'nerd', 'lotse', 'default')
PFICHT = ('id', 'titel', 'abnahmekriterium', 'assignee', 'bucket')
HERKUNFT = ('explicit', 'derived_kontext', 'derived_titel')


def offene_aus_tasks(pfad):
    """Alle offenen IDs aus TASKS.md, mit Haeufigkeit (Doppelpunkte zaehlen)."""
    zeilen = lies_text(pfad)
    offen = next(i for i, z in enumerate(zeilen) if z.strip() == '## Offen')
    erledigt = next(i for i, z in enumerate(zeilen) if z.strip() == '## Erledigt')
    offen_ids, erledigt_ids, untermittelt = [], [], []
    for i in range(offen, erledigt):
        m = KOPF.match(zeilen[i]) or KOPF_UNTERMITT.match(zeilen[i])
        if not m:
            continue
        status = m.group(1).strip()
        if KOPF.match(zeilen[i]) is None:
            untermittelt.append(m.group(2).strip())
        (erledigt_ids if status == 'x' else offen_ids).append(m.group(2).strip())
    return offen_ids, erledigt_ids, untermittelt


def pruefe(tasks, worklist, plan=None):
    fehler, notizen, belege = [], [], []

    if not os.path.isfile(worklist):
        return ['Worklist fehlt: %s' % worklist], notizen, belege
    if os.path.getsize(worklist) == 0:
        return ['Worklist ist leer (0 Byte)'], notizen, belege
    try:
        with open(worklist, 'rb') as fh:
            dok = json.loads(fh.read().decode('utf-8'))
    except ValueError as e:
        return ['Worklist ist kein gueltiges JSON: %s' % e], notizen, belege
    if not isinstance(dok, dict) or 'items' not in dok:
        return ['Worklist traegt kein Feld "items"'], notizen, belege

    offen_ids, erledigt_ids, untermittelt = offene_aus_tasks(tasks)
    items = dok['items']
    ids = [i.get('id') for i in items]

    # --- 2 genau einmal ------------------------------------------------------
    haeufig = Counter(ids)
    doppelt = sorted([i for i, n in haeufig.items() if n > 1],
                     key=lambda s: int(re.sub(r'\D', '', s) or 0))
    fehlend = sorted(set(offen_ids) - set(ids), key=lambda s: int(re.sub(r'\D', '', s) or 0))
    ueber = sorted(set(ids) - set(offen_ids), key=lambda s: int(re.sub(r'\D', '', s) or 0))
    if doppelt:
        fehler.append('%d ID(s) mehrfach in der Worklist: %s'
                      % (len(doppelt), ', '.join(doppelt[:8])))
    if fehlend:
        fehler.append('%d offene(r) Punkt(e) aus TASKS.md fehlen in der Worklist: %s'
                      % (len(fehlend), ', '.join(fehlend[:8])))
    if ueber:
        fehler.append('%d Eintrag/Eintraege in der Worklist sind in TASKS.md nicht '
                      'offen: %s' % (len(ueber), ', '.join(ueber[:8])))
    if not fehler:
        notizen.append('jeder offene Punkt genau einmal: %d' % len(offen_ids))
        belege.append('offen=%d, eindeutig=%d, doppelt=%d'
                      % (len(offen_ids), len(set(offen_ids)), len(doppelt)))

    # --- 3 keine erledigten --------------------------------------------------
    erledigt_drin = sorted(set(ids) & set(erledigt_ids))
    if erledigt_drin:
        fehler.append('erledigte(r) Punkt(e) in der Worklist: %s'
                      % ', '.join(erledigt_drin[:8]))

    # --- 4/5 Pflichtfelder + Herkunft ----------------------------------------
    fehlfeld = Counter()
    schlechtes_herkunft = []
    for i in items:
        for f in PFICHT:
            if not str(i.get(f, '') or '').strip():
                fehlfeld[f] += 1
        h = i.get('abnahmekriterium_herkunft')
        if h not in HERKUNFT:
            schlechtes_herkunft.append('%s=%r' % (i.get('id'), h))
    for f, n in sorted(fehlfeld.items()):
        fehler.append('%d Eintrag/Eintraege ohne "%s"' % (n, f))
    if schlechtes_herkunft:
        fehler.append('%d Eintrag/Eintraege mit unbekannter Herkunft des '
                      'Abnahmekriteriums: %s'
                      % (len(schlechtes_herkunft), ', '.join(schlechtes_herkunft[:6])))

    # --- 6/7 Buckets ---------------------------------------------------------
    schlecht = [i['id'] for i in items
                if i.get('bucket') not in ('PARALLEL', 'ORDERED')]
    if schlecht:
        fehler.append('%d Eintrag/Eintraege mit ungueltigem bucket: %s'
                      % (len(schlecht), ', '.join(str(s) for s in schlecht[:8])))
    falsch_0 = [i['id'] for i in items
                if i.get('bucket') == 'ORDERED' and int(i.get('welle') or 1) <= 1]
    falsch_1 = [i['id'] for i in items
                if i.get('bucket') == 'PARALLEL' and int(i.get('welle') or 1) > 1]
    if falsch_0:
        fehler.append('%d ORDERED-Eintrag/Eintraege mit Welle <= 1: %s'
                      % (len(falsch_0), ', '.join(falsch_0[:8])))
    if falsch_1:
        fehler.append('%d PARALLEL-Eintrag/Eintraege mit Welle > 1: %s'
                      % (len(falsch_1), ', '.join(falsch_1[:8])))
    gemessen = Counter(i.get('bucket') for i in items)
    angegeben = dok.get('buckets') or {}
    for b in ('PARALLEL', 'ORDERED'):
        if int(angegeben.get(b, -1)) != gemessen.get(b, 0):
            fehler.append('buckets.%s sagt %r, die Eintraege zaehlen %d'
                          % (b, angegeben.get(b), gemessen.get(b, 0)))
    if not (schlecht or falsch_0 or falsch_1):
        notizen.append('Buckets stimmen: PARALLEL=%d, ORDERED=%d'
                       % (gemessen.get('PARALLEL', 0), gemessen.get('ORDERED', 0)))

    # --- 8 Roster ------------------------------------------------------------
    fremd = sorted({i.get('assignee') for i in items
                    if i.get('assignee') not in ROSTER})
    if fremd:
        fehler.append('Assignee ausserhalb des Roster: %s' % ', '.join(map(str, fremd)))

    # --- 9 Kopfzahl ----------------------------------------------------------
    if dok.get('anzahl') is not None and int(dok['anzahl']) != len(items):
        fehler.append('anzahl sagt %r, die Worklist traegt %d Eintraege'
                      % (dok['anzahl'], len(items)))

    # --- 10 Leerfall ---------------------------------------------------------
    if not offen_ids:
        if items:
            fehler.append('TASKS.md ohne offene Punkte, die Worklist traegt %d '
                          'Eintraege' % len(items))
        elif not (dok.get('befunde') or {}).get('leerfall'):
            fehler.append('Leerfall ohne den Befund "leerfall" - die Folgekarten '
                          'noepen dann nicht erkennbar')
        else:
            notizen.append('Leerfall korrekt behandelt: %s'
                           % (dok['befunde']['leerfall']))

    # --- Plan: Vollstaendigkeit nur als BEFUND, nie als Gruen ----------------
    # Gezaehlt wird mit derselben Funktion, mit der der Bauer den Plan liest.
    # Zwei Zaehlweisen fuer dieselbe Sache ergaben 46 gegen 47 - wer eine
    # Zahl nachrechnen will, muss sie nur an EINER Stelle finden.
    if plan and os.path.isfile(plan):
        plan_ids = set(plan_wellen(plan))
        fehlend_plan = sorted(set(offen_ids) - plan_ids,
                              key=lambda s: int(re.sub(r'\D', '', s) or 0))
        if fehlend_plan:
            notizen.append('BEFUND Plan unvollstaendig: %d offene Punkte fehlen '
                           'darin (%s ...) - die Worklist traegt sie, der Plan '
                           'nicht.' % (len(fehlend_plan), ', '.join(fehlend_plan[:5])))
            belege.append('plan_fehlt=%d' % len(fehlend_plan))
    elif plan:
        fehler.append('Plan fehlt: %s' % plan)

    if untermittelt:
        notizen.append('BEFUND TASKS.md: %d untermittelte Kopfzeile(n) (%s) - '
                       'mitgelesen, aber die Datei ist zu reparieren'
                       % (len(untermittelt), ', '.join(untermittelt[:5])))

    return fehler, notizen, belege


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    tasks, worklist = sys.argv[1], sys.argv[2]
    plan = None
    if '--plan' in sys.argv:
        plan = sys.argv[sys.argv.index('--plan') + 1]
    fehler, notizen, belege = pruefe(tasks, worklist, plan)
    for n in notizen:
        print('  - %s' % n)
    for b in belege:
        print('    Beleg: %s' % b)
    if fehler:
        print('\nFEHLER (%d):' % len(fehler))
        for f in fehler:
            print('  ! %s' % f)
        return 1
    print('\nOK: Worklist deckt TASKS.md vollstaendig ab.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
