#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Gegenprobe: der Pruefer muss bei echten Verletzungen rot werden.

Ein Pruefer, der immer Exit 0 liefert, ist eine Behauptung. Jede Verletzung
wird in eine Kopie der echten Worklist eingebaut; danach muss der Pruefer
mit Exit 1 antworten UND die richtige Meldung nennen.

Aufruf: python routing_worklist_gegenprobe.py <tasks.md> <worklist.json>
"""
import os
import re
import sys
import json
import copy
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from routing_worklist_bauen import lies_text  # noqa: E402
from routing_worklist_pruefen import pruefe  # noqa: E402


def schreiben(dok, pfad):
    with open(pfad, 'w', encoding='utf-8', newline='') as fh:
        json.dump(dok, fh, ensure_ascii=False, indent=2)
    return pfad


def verletzung_fehlender_punkt(dok):
    d = copy.deepcopy(dok)
    d['items'] = [i for i in d['items'] if i['id'] != d['items'][0]['id']]
    d['anzahl'] = len(d['items'])
    d['buckets'] = {'PARALLEL': len([i for i in d['items'] if i['bucket'] == 'PARALLEL']),
                    'ORDERED': len([i for i in d['items'] if i['bucket'] == 'ORDERED'])}
    return d, 'fehlen in der Worklist'


def verletzung_doppelter_punkt(dok):
    d = copy.deepcopy(dok)
    d['items'].append(copy.deepcopy(d['items'][0]))
    d['anzahl'] = len(d['items'])
    return d, 'mehrfach in der Worklist'


def verletzung_erledigter_punkt(dok, erledigt_id):
    d = copy.deepcopy(dok)
    vorlage = copy.deepcopy(d['items'][0])
    vorlage['id'] = erledigt_id
    d['items'].append(vorlage)
    d['anzahl'] = len(d['items'])
    return d, 'nicht offen'


def verletzung_leeres_feld(dok):
    d = copy.deepcopy(dok)
    d['items'][0]['abnahmekriterium'] = '   '
    return d, 'ohne "abnahmekriterium"'


def verletzung_unbekannte_herkunft(dok):
    d = copy.deepcopy(dok)
    d['items'][0]['abnahmekriterium_herkunft'] = 'geraten'
    return d, 'unbekannter Herkunft'


def verletzung_ordered_mit_welle_1(dok):
    d = copy.deepcopy(dok)
    ziel = None
    for i in d['items']:
        if i['bucket'] == 'ORDERED':
            ziel = i
            break
    if ziel is None:
        ziel = d['items'][0]
    ziel['welle'] = 1
    return d, 'ORDERED-Eintrag/Eintraege mit Welle <= 1'


def verletzung_falscher_bucket(dok):
    d = copy.deepcopy(dok)
    d['items'][0]['bucket'] = 'IRGENDWANN'
    return d, 'ungueltigem bucket'


def verletzung_falscher_zaehler(dok):
    d = copy.deepcopy(dok)
    d['buckets']['PARALLEL'] = int(d['buckets'].get('PARALLEL', 0)) + 7
    return d, 'buckets.PARALLEL sagt'


def verletzung_falsche_anzahl(dok):
    d = copy.deepcopy(dok)
    d['anzahl'] = int(d.get('anzahl', 0)) + 3
    return d, 'anzahl sagt'


def verletzung_fremder_assignee(dok):
    d = copy.deepcopy(dok)
    d['items'][0]['assignee'] = 'nicht-im-roster'
    return d, 'ausserhalb des Roster'


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    tasks, worklist = sys.argv[1], sys.argv[2]
    with open(worklist, 'rb') as fh:
        dok = json.loads(fh.read().decode('utf-8'))
    erledigt_ids = re.findall(r'^- \[x\] \*\*(T-\d+)', '\n'.join(lies_text(tasks)), re.M)

    tmp = tempfile.mkdtemp(prefix='worklist_gegenprobe_')
    bauen = [
        verletzung_fehlender_punkt,
        verletzung_doppelter_punkt,
        verletzung_erledigter_punkt,
        verletzung_leeres_feld,
        verletzung_unbekannte_herkunft,
        verletzung_ordered_mit_welle_1,
        verletzung_falscher_bucket,
        verletzung_falscher_zaehler,
        verletzung_falsche_anzahl,
        verletzung_fremder_assignee,
    ]
    rot, gruen_geraten = 0, []
    for k, fn in enumerate(bauen, 1):
        if fn is verletzung_erledigter_punkt and not erledigt_ids:
            continue
        arg = erledigt_ids[0] if fn is verletzung_erledigter_punkt else None
        d, erwartet = fn(dok, arg) if arg else fn(dok)
        pfad = schreiben(d, os.path.join(tmp, 'v%02d.json' % k))
        fehler, _, _ = pruefe(tasks, pfad)
        getroffen = any(erwartet in f for f in fehler)
        if fehler and getroffen:
            rot += 1
            print('  ok   %-42s -> Exit 1, Meldung: %s'
                  % (fn.__name__, erwartet))
        elif fehler:
            rot += 1
            gruen_geraten.append('%s wurde rot, aber mit der FALSCHEN Meldung: %s'
                                 % (fn.__name__, fehler[0]))
            print('  TEIL %-41s -> rot, Meldung passt nicht: %s'
                  % (fn.__name__, fehler[0]))
        else:
            gruen_geraten.append('%s blieb gruen' % fn.__name__)
            print('  FEHL %-41s -> blieb gruen' % fn.__name__)
    print('\nGegenprobe: %d Verletzungen, %d mit der richtigen Meldung rot.'
          % (len(bauen) - 1 + 1, rot))
    if gruen_geraten:
        print('NICHT BELEGT:')
        for g in gruen_geraten:
            print('  ! %s' % g)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
