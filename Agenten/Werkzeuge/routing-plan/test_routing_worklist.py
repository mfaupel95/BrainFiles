#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests fuer Bauen und Pruefen der Routing-Worklist.

Aufruf (aus dem Werkzeugordner):
  python -m unittest test_routing_worklist
"""
import io
import os
import json
import shutil
import unittest
import tempfile
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routing_worklist_bauen as bau  # noqa: E402
from routing_worklist_pruefen import pruefe as wl_pruefe  # noqa: E402
from routing_worklist_gegenprobe import main as gegenprobe_main  # noqa: E402

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

TASKS_KOPFFORMEN = """# TASKS.md

## Offen

- [ ] **T-010 — Hausform, mit naechstem Schritt**
      Kontext: erster Kontext
      Naechster Schritt: erste Datei anfassen, Test gruen
- [ ] **T-011 - ASCII-Bindestrich, ohne Schritt**
      Kontext: zweiter Kontext
- [ ]   **T-012 - fuehrende Leerzeichen, nur Kontext**
      Kontext: dritter Kontext
- [ ] **T-013 — wartet auf T-010 (ORDERED)**
      Kontext: vierter Kontext
      Naechster Schritt: Max fragen, dann T-010 abarbeiten
- [ ] **T-014 — Hausform ohne jedes Feld**
- [ ] **T-015 — verweist auf T-064 (fehlt)**
      Kontext: fuenfter Kontext
- [x] **T-016 — erledigt**
      Kontext: sechster Kontext

## Erledigt

- [x] **T-001 - lang erledigt**
"""

TASKS_LEER = """# TASKS.md

## Offen

## Erledigt

- [x] **T-001 - etwas Erledigtes**
      Kontext: fertig
"""

TASKS_UNTERMITTELT = """# TASKS.md

## Offen

- [ ] **T-064 — Nautilus-Kraken-Orderweg: WebSocket-Token verweigert, REST traegt
      Kontext: untermittelte Ueberschrift
      Naechster Schritt: REST bleibt, Exec-Client aufgeben

## Erledigt
"""

PLAN = """# Routing-Plan

### Welle 1 — parallel (2 Eintraege)

- **T-010 — Hausform, mit naechstem Schritt** · offen · Aufwand M · Profil `hermes-wartung` · keine
- **T-013 — wartet auf T-010** · offen · Aufwand S · Profil `markt-recherche` · keine

### Welle 2 — sequenziell (1 Eintrag)

- **T-011 - ASCII-Bindestrich, ohne Schritt** · offen · Aufwand L · Profil `default` · keine
"""


class Basis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='wl_test_')
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def datei(self, name, inhalt):
        p = os.path.join(self.tmp, name)
        with open(p, 'w', encoding='utf-8', newline='') as fh:
            fh.write(inhalt)
        return p

    def json_dokument(self, name):
        with open(os.path.join(self.tmp, name), 'rb') as fh:
            return json.loads(fh.read().decode('utf-8'))


class LesenTest(Basis):
    def test_liest_alle_drei_kopfformen(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        bloecke, _, _, _, unter = bau.bloecke_lesen(p)
        ids = [b['id'] for b in bloecke]
        for erwartet in ('T-010', 'T-011', 'T-012', 'T-013', 'T-014', 'T-015', 'T-016'):
            self.assertIn(erwartet, ids, '%s wurde nicht gelesen' % erwartet)

    def test_ascii_bindestrich_ist_kein_verlust(self):
        """Die Hausform allein verliert offene Punkte - der Bau muss alle lesen."""
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        bloecke, _, _, _, _ = bau.bloecke_lesen(p)
        ascii_ids = [b['id'] for b in bloecke if b['titel'].startswith('ASCII')]
        self.assertEqual(ascii_ids, ['T-011'])

    def test_untermittelte_ueberschrift_wird_als_befund_gelesen(self):
        p = self.datei('tasks.md', TASKS_UNTERMITTELT)
        bloecke, _, _, _, unter = bau.bloecke_lesen(p)
        self.assertEqual([b['id'] for b in bloecke], ['T-064'])
        self.assertEqual([tid for _, tid in unter], ['T-064'])

    def test_fehlende_abschnitte_sind_ein_klarer_fehler(self):
        p = self.datei('tasks.md', '# TASKS.md\n\n## Offen\n')
        with self.assertRaises(SystemExit):
            bau.bloecke_lesen(p)


class AbnahmekriteriumTest(Basis):
    def test_naechster_schritt_ist_explicit(self):
        f = bau.felder(['- [ ] **T-010 — Titel**',
                        '      Naechster Schritt: Datei anfassen, Test laeuft',
                        '      Kontext: egal'])
        k, herkunft = bau.abnahmekriterium(f, 'Titel')
        self.assertEqual(herkunft, 'explicit')
        self.assertIn('Datei anfassen', k)

    def test_kontext_ist_als_abgeleitet_gekennzeichnet(self):
        f = bau.felder(['- [ ] **T-011 — Titel**', '      Kontext: nur Kontext'])
        k, herkunft = bau.abnahmekriterium(f, 'Titel')
        self.assertEqual(herkunft, 'derived_kontext')
        self.assertIn('abgeleitet', k)

    def test_ohne_jedes_feld_ist_es_aus_dem_titel(self):
        f = bau.felder(['- [ ] **T-014 — Titel**'])
        k, herkunft = bau.abnahmekriterium(f, 'Titel')
        self.assertEqual(herkunft, 'derived_titel')
        self.assertIn('Titel', k)

    def test_umgebrochener_feld_text_gehrt_vollstaendig(self):
        """Ein Feld laeuft bis zur naechsten Feldzeile, nicht bis zum Zeilenende."""
        f = bau.felder(['- [ ] **T-010 — Titel**',
                        '      Naechster Schritt: erster Teil des',
                        '      Satzes, der hier weiterlaeuft',
                        '      Kontext: egal'])
        k, _ = bau.abnahmekriterium(f, 'Titel')
        self.assertIn('weiterlaeuft', k)


class BucketsTest(Basis):
    def test_querverweis_erzeugt_ordered(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        items, _ = bau.auflisten(p)
        nach = {i['id']: i for i in items}
        self.assertEqual(nach['T-013']['bucket'], 'ORDERED')
        self.assertEqual(nach['T-013']['welle'], 2)
        self.assertEqual(nach['T-010']['bucket'], 'PARALLEL')
        self.assertEqual(nach['T-010']['welle'], 1)

    def test_plan_welle_gewinnt_gegen_querverweis(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        plan = self.datei('plan.md', PLAN)
        items, _ = bau.auflisten(p, plan)
        nach = {i['id']: i for i in items}
        # T-011 verweist im Text auf niemanden (Welle 1), der Plan sagt Welle 2.
        self.assertEqual(nach['T-011']['welle'], 2)
        self.assertEqual(nach['T-011']['welle_herkunft'], 'plan')

    def test_ohne_plan_kommt_die_welle_aus_den_querverweisen(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        items, _ = bau.auflisten(p)
        self.assertTrue(all(i['welle_herkunft'] == 'querverweis' for i in items))

    def test_profil_aus_plan_und_fallback(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        plan = self.datei('plan.md', PLAN)
        items, _ = bau.auflisten(p, plan)
        nach = {i['id']: i for i in items}
        self.assertEqual(nach['T-010']['assignee'], 'hermes-wartung')
        self.assertTrue(nach['T-010']['profil_aus_plan'])
        # T-012 steht nicht im Plan -> default, ausdruecklich als nicht aus dem Plan.
        self.assertEqual(nach['T-012']['assignee'], 'default')
        self.assertFalse(nach['T-012']['profil_aus_plan'])


class LeerfallTest(Basis):
    def test_leerer_backlog_ergibt_leere_worklist(self):
        p = self.datei('tasks.md', TASKS_LEER)
        items, meta = bau.auflisten(p)
        self.assertEqual(items, [])
        self.assertEqual(meta['untermittelt'], [])


class GegenprobeTest(Basis):
    def test_gegenprobe_bekommt_jede_verletzung_als_rot(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        ziel = os.path.join(self.tmp, 'wl.json')
        bau_main([p, ziel])
        argv = sys.argv
        sys.argv = ['gegenprobe', p, ziel]
        try:
            rc = gegenprobe_main()
        finally:
            sys.argv = argv
        self.assertEqual(rc, 0, 'die Gegenprobe selbst blieb nicht gruen')

    def test_pruefer_ist_rot_bei_fehlendem_punkt(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        ziel = os.path.join(self.tmp, 'wl.json')
        bau_main([p, ziel])
        dok = self.json_dokument('wl.json')
        dok['items'] = dok['items'][1:]
        dok['anzahl'] = len(dok['items'])
        with open(ziel, 'w', encoding='utf-8') as fh:
            json.dump(dok, fh, ensure_ascii=False)
        fehler, _, _ = wl_pruefe(p, ziel)
        self.assertTrue(any('fehlen in der Worklist' in f for f in fehler), fehler)

    def test_pruefer_ist_rot_bei_doppeltem_punkt(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        ziel = os.path.join(self.tmp, 'wl.json')
        bau_main([p, ziel])
        dok = self.json_dokument('wl.json')
        dok['items'].append(dok['items'][0])
        dok['anzahl'] = len(dok['items'])
        with open(ziel, 'w', encoding='utf-8') as fh:
            json.dump(dok, fh, ensure_ascii=False)
        fehler, _, _ = wl_pruefe(p, ziel)
        self.assertTrue(any('mehrfach in der Worklist' in f for f in fehler), fehler)

    def test_pruefer_ist_rot_bei_ordered_mit_welle_1(self):
        p = self.datei('tasks.md', TASKS_KOPFFORMEN)
        ziel = os.path.join(self.tmp, 'wl.json')
        bau_main([p, ziel])
        dok = self.json_dokument('wl.json')
        for i in dok['items']:
            if i['bucket'] == 'ORDERED':
                i['welle'] = 1
        with open(ziel, 'w', encoding='utf-8') as fh:
            json.dump(dok, fh, ensure_ascii=False)
        fehler, _, _ = wl_pruefe(p, ziel)
        self.assertTrue(any('Welle <= 1' in f for f in fehler), fehler)


class EchterBestandTest(Basis):
    """Der Lauf gegen das Haus: TASKS.md traegt 170 offene Punkte."""

    def haus(self):
        return os.path.join(WURZEL, 'MaxHirn', 'Archiv', 'TASKS.md')

    def test_hausbestand_wird_vollstaendig_gedeckt(self):
        p = self.haus()
        if not os.path.isfile(p):
            self.skipTest('TASKS.md nicht im Worktree')
        items, meta = bau.auflisten(p)
        ids = [i['id'] for i in items]
        self.assertEqual(len(ids), len(set(ids)), 'eine ID steht zweimal drin')
        self.assertTrue(all(i['abnahmekriterium'].strip() for i in items))
        # Der Plan traegt nicht alles - das ist ein BEFUND, kein Testfehler,
        # aber es muss auffallen, sonst glaubt jemand, der Plan decke alles.
        plan = os.path.join(WURZEL, 'MaxHirn', 'Archiv',
                            'ROUTING_PLAN_2026-10-04.md')
        if os.path.isfile(plan):
            fehlend = {i['id'] for i in items} - set(bau.plan_wellen(plan))
            self.assertTrue(fehlend,
                            'der Plan traegt inzwischen alles - die Notiz '
                            '"Plan verliert Punkte" im Bericht waere dann falsch')


def bau_main(argv):
    argv = list(argv)
    old = sys.argv
    sys.argv = ['routing_worklist_bauen.py'] + argv
    try:
        rc = bau.main()
    finally:
        sys.argv = old
    return rc


if __name__ == '__main__':
    unittest.main()
