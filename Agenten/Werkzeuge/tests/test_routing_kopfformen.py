#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests fuer die Kopfregel von TASKS.md (routing-plan/kopfformen.py).

Warum dieser Test existiert: `routing_plan_bauen.py` und
`routing_plan_pruefen.py` teilten sich eine zu enge Kopf-Regex. Ergebnis war
ein Plan, dem 47 von 170 offenen Punkten fehlten - und ein Pruefer, der den
unvollstaendigen Plan GRUEN meldete, weil er mit derselben Enge zaehlte
(04.10.2026). Dieselbe Fehlerklasse wie T-332 (`doppelte_nummern.py` sah 26
Eintraege nicht).

Die Tests bauen echte Temp-Dateien, kein Mock: die Regel besteht aus einer
Regex und einer Datei, und nur ein echter Lauf kann sie brechen. Kein Test
fasst `MaxHirn/Archiv/TASKS.md` an - die Quelle wird nachgebaut, und die
Auszahlung am echten Hausfile laeuft nur lesend.

Gegenprobe ist Pflicht, nicht Kür: `GegenprobeOhneFixTest` rechnet mit dem
ALTEN Muster (Gevrierstrich UND schliessendes '**') und verlangt, dass es
an Attrappen mit ASCII-Bindestrich und umbrochenem Titel scheitert. Faellt
der Test nicht, prueft er nichts.

Ausfuehren (aus der Repo-Wurzel):
    python -m unittest discover -s Agenten/Werkzeuge/tests -p "test_routing_kopfformen.py" -v
    oder:
    python Agenten/Werkzeuge/tests/test_routing_kopfformen.py
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

WURZEL = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       '..', '..', '..'))
PLAN_ORDNER = os.path.join(WURZEL, 'Agenten', 'Werkzeuge', 'routing-plan')
if PLAN_ORDNER not in sys.path:
    sys.path.insert(0, PLAN_ORDNER)

import kopfformen  # noqa: E402  (Pfad steht absichtlich oben)

# Das Muster, das den Befund erzeugt hat: nur Hausform, nur mit '**'.
KOPF_ALT = re.compile(r'^-\s*\[(.)\]\s+\*\*(T-(\d+))\s+—\s*(.+?)\*\*\s*$')

HAUSFORM = '- [ ] **T-900 — Hausform mit Gevrierstrich**'
ASCII_FORM = '- [ ] **T-902 - Fremde Hand, ASCII-Bindestrich**'
UMBROCHEN = '- [ ] **T-903 — Titel bricht ohne schliessendes ** um'
UNLESBAR = '- [ ] **T-901 _ Kopfform, die kein Muster liest**'
ERLEDIGT = '- [x] **T-950 — Alter Punkt**'

QUELLE = '\n'.join([
    '# Attrappe', '', '## Offen', '',
    HAUSFORM,
    '      Kontext: reiner Testeintrag.',
    '      Naechster Schritt: nichts, nur Gegenprobe.', '',
    '## Erledigt', '', ERLEDIGT, '',
])


def lade(werkzeug):
    pfad = os.path.join(PLAN_ORDNER, werkzeug)
    spec = importlib.util.spec_from_file_location(werkzeug[:-3], pfad)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class KopfformenTest(unittest.TestCase):
    """Die Regel liest alle drei Haus-Schreibweisen."""

    def test_liest_die_drei_hausformen(self):
        for zeile, tid in ((HAUSFORM, 'T-900'), (ASCII_FORM, 'T-902'),
                           (UMBROCHEN, 'T-903')):
            with self.subTest(zeile=zeile):
                m = kopfformen.KOPF.match(zeile)
                self.assertIsNotNone(m, 'nicht gelesen: %s' % zeile)
                self.assertEqual(m.group(2), tid)

    def test_titel_bleibt_vollstaendig(self):
        """Ein umbrochener Titel wird nicht gekuerzt und nicht geraten."""
        rest = kopfformen.KOPF.match(UMBROCHEN).group(4)
        self.assertEqual(kopfformen.titel_aus(rest),
                         'Titel bricht ohne schliessendes ** um')

    def test_titel_schneidet_sternchenpaar_und_erledigt_vermerk(self):
        self.assertEqual(kopfformen.titel_aus('Titel**'),
                         'Titel')
        self.assertEqual(kopfformen.titel_aus('*Titel - erledigt 2026-09-19'),
                         'Titel')

    def test_blocktraegt_vollen_text_bis_zum_naechsten_eintrag(self):
        # '## Erledigt' begrenzt den Abschnitt: T-950 gehoert nicht dazu.
        bloecke, ungelesen = kopfformen.eintraege(
            QUELLE.split('\n'))
        self.assertEqual([b['id'] for b in bloecke], ['T-900'])
        self.assertEqual(ungelesen, [])
        self.assertIn('Kontext:', bloecke[0]['text'][1])
        self.assertIn('Naechster Schritt', bloecke[0]['text'][2])
        self.assertEqual(bloecke[0]['zeile'], 5)

    def test_zeile_ohne_muster_wird_als_befund_gemeldet_nicht_verschluckt(self):
        bloecke, ungelesen = kopfformen.eintraege(
            QUELLE.replace(HAUSFORM, UNLESBAR).split('\n'))
        self.assertEqual([b['id'] for b in bloecke], [])
        self.assertEqual(len(ungelesen), 1)
        self.assertIn('T-901', ungelesen[0][1])

    def test_gelesen_plus_ungelesen_ergaenzt_alle_statuszeilen(self):
        """Die Zaehlung ist vollstaendig: nichts verschwindet zwischen
        'gelesen' und 'Befund' - je Eintrag im Abschnitt Offen genau eins."""
        zeilen = QUELLE.replace(HAUSFORM, UNLESBAR).split('\n')
        bloecke, ungelesen = kopfformen.eintraege(zeilen)
        a = zeilen.index('## Offen')
        b = zeilen.index('## Erledigt')
        statuszeilen = [z for z in zeilen[a:b] if re.match(r'^-\s*\[.\]', z)]
        self.assertEqual(len(bloecke) + len(ungelesen), len(statuszeilen))
        self.assertEqual(len(statuszeilen), 1)

    def test_erledigter_abschnitt_wird_nicht_gezaehlt(self):
        bloecke, ungelesen = kopfformen.eintraege(QUELLE.split('\n'))
        self.assertNotIn('T-950', [b['id'] for b in bloecke])
        self.assertEqual(ungelesen, [])


class BauerUndPrueferTest(unittest.TestCase):
    """Bauer und Pruefer MUESSEN beide die Fremdformen aufnehmen.

    Geprueft ueber echte Kindprozesse - die beiden Werkzeuge lesen eine
    Datei und schreiben eine Datei, das kann kein Aufruf im Test ersetzen.
    """

    def setUp(self):
        self.ordner = tempfile.mkdtemp()
        self.quelle = os.path.join(self.ordner, 'tasks.md')
        # Hausform PLUS die beiden Fremdformen: drei Eintraege, damit der
        # Test beweisen kann, dass die Hausform nicht die anderen zwei
        # verdraengt (eine Quelle mit nur Fremdformen wuerde das nicht zeigen).
        with open(self.quelle, 'w', encoding='utf-8', newline='') as fh:
            fh.write(QUELLE.replace(
                '## Erledigt',
                ASCII_FORM + '\n' + UMBROCHEN + '\n\n## Erledigt'))
        self.plan = os.path.join(self.ordner, 'plan.md')
        r = self._bauen()
        if r.returncode != 0:            # setUp darf nicht stillschweigend weiterlaufen
            shutil.rmtree(self.ordner, ignore_errors=True)
            raise AssertionError('Bauer schon im setUp rot: %s%s'
                                 % (r.stdout, r.stderr))

    def tearDown(self):
        shutil.rmtree(self.ordner, ignore_errors=True)

    def _laufe(self, werkzeug, *args):
        return subprocess.run(
            [sys.executable, os.path.join(PLAN_ORDNER, werkzeug),
             self.quelle] + list(args),
            capture_output=True, text=True, cwd=WURZEL)

    def _bauen(self):
        return self._laufe('routing_plan_bauen.py', self.plan)

    def test_bauer_nimmt_ascii_und_umbruch_auf(self):
        with open(self.plan, encoding='utf-8') as fh:
            text = fh.read()
        for tid in ('T-900', 'T-902', 'T-903'):
            # Inventarzeile UND Wellenzeile: zweimal im Plan.
            self.assertGreaterEqual(text.count(tid), 2, tid)
        self.assertNotIn('T-950', text)          # erledigt gehoert nicht hinein

    def test_pruefer_ist_gruen_und_zaehlt_alle_drei_punkte(self):
        r = self._laufe('routing_plan_pruefen.py', self.plan)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('Tabellenzeilen == offene Eintraege: 3', r.stdout)
        self.assertIn('0 unlesbar', r.stdout)

    def test_unabhaengiger_pruefer_ist_gruen(self):
        r = self._laufe('routing_plan_unabhaengig.py', self.plan)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_bauer_bricht_ab_wenn_er_eine_kopfform_nicht_kennt(self):
        with open(self.quelle, 'w', encoding='utf-8', newline='') as fh:
            fh.write(QUELLE.replace(HAUSFORM, UNLESBAR))
        r = self._bauen()
        self.assertNotEqual(r.returncode, 0, 'Bauer blieb bei %r gruen' % UNLESBAR)
        self.assertIn('Abbruch', r.stdout + r.stderr)

    def test_pruefer_meldet_die_unbekannte_kopfform_rot(self):
            """Der Kern des Befunds: der Plan ist richtig, die QUELLE traegt eine
            Form, die kein Muster liest. Beide Seiten muessen es benennen."""
            guter_plan = os.path.join(self.ordner, 'plan_gut.md')
            shutil.copy(self.plan, guter_plan)
            with open(self.quelle, 'w', encoding='utf-8', newline='') as fh:
                fh.write(QUELLE.replace(HAUSFORM, UNLESBAR))
            for werkzeug in ('routing_plan_pruefen.py',
                             'routing_plan_unabhaengig.py'):
                r = self._laufe(werkzeug, guter_plan)
                with self.subTest(werkzeug=werkzeug):
                    self.assertNotEqual(r.returncode, 0, werkzeug)
                    # Der Hauspruefer nennt es im eigenen Befund; der unabhaengige
                    # listet die Zeile als 'fehlend im Plan'. Beides belegt
                    # denselben Verlust - die Form muss nicht derselbe Satz sein.
                    verliert = ('sehen wie ein Eintrag aus' in r.stdout
                                or ('fehlen im Plan' in r.stdout
                                    and 'T-901' in r.stdout))
                    self.assertTrue(verliert, r.stdout)


class GegenprobeOhneFixTest(unittest.TestCase):
    """Das alte Muster MUSS an den Fremdformen scheitern.

    Ohne diesen Test prueft die Suite nur, dass die neue Regel die neuen
    Formen liest - nicht, dass die alte Regel zu eng WAR. Das ist der
    Unterschied zwischen 'funktioniert' und 'repariert etwas'.
    """

    def test_altes_muster_verschluckt_ascii_und_umbruch(self):
        fehlend = [z for z in (ASCII_FORM, UMBROCHEN) if not KOPF_ALT.match(z)]
        self.assertEqual(len(fehlend), 2, 'das alte Muster liest heute mehr '
                                         'als zur Zeit des Befunds')

    def test_altes_muster_liest_die_hausform(self):
        self.assertIsNotNone(KOPF_ALT.match(HAUSFORM))


class GegenprobeSkriptTest(unittest.TestCase):
    """Die Gegenprobe selbst muss mit dem neuen Quellentest gruen sein.

    Die Quelle traegt bewusst MEHR Eintraege als die uebrigen Tests: die
    Plan-Mutationen brauchen fuenf Tabellenzeilen und eine Welle 1 mit mehr
    als einem Eintrag. Sonst meldet die Gegenprobe einen Attrappen-Mangel
    statt eines Pruefer-Befunds.
    """

    def _quelle(self, n=8):
        zeilen = ['# Attrappe', '', '## Offen', '']
        for k in range(n):
            zeilen.append('- [ ] **T-90%d — Attrappenpunkt %d**' % (k, k))
            zeilen.append('      Kontext: Testeintrag %d.' % k)
            zeilen.append('      Naechster Schritt: nichts tun.')
            zeilen.append('')
        zeilen += ['## Erledigt', '']
        return '\n'.join(zeilen) + '\n'

    def test_gegenprobe_laeft_gruen(self):
        ordner = tempfile.mkdtemp()
        try:
            quelle = os.path.join(ordner, 'tasks.md')
            with open(quelle, 'w', encoding='utf-8', newline='') as fh:
                fh.write(self._quelle())
            plan = os.path.join(ordner, 'plan.md')
            subprocess.run([sys.executable,
                            os.path.join(PLAN_ORDNER, 'routing_plan_bauen.py'),
                            quelle, plan], capture_output=True, text=True,
                           cwd=WURZEL)
            r = subprocess.run(
                [sys.executable, os.path.join(PLAN_ORDNER, 'gegenprobe.py'),
                 quelle, plan], capture_output=True, text=True, cwd=WURZEL)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn('quellenform_ascii_und_umbruch', r.stdout)
        finally:
            shutil.rmtree(ordner, ignore_errors=True)


class HausdateiTest(unittest.TestCase):
    """Das echte TASKS.md - nur lesend, ohne jeden Schreibzugriff."""

    def setUp(self):
        self.pfad = os.path.join(WURZEL, 'MaxHirn', 'Archiv', 'TASKS.md')
        if not os.path.isfile(self.pfad):
            self.skipTest('TASKS.md nicht im Baum')

    def test_keine_ungelesenen_kopfzeilen_im_hausfile(self):
        _, ungelesen, _nl, _a, _b = kopfformen.datei_lesen(self.pfad)
        self.assertEqual(ungelesen, [],
                         'im Hausfile stehen Zeilen, die wie ein Eintrag '
                         'aussehen, aber von keinem Muster erfasst werden')

    def test_hausfile_wird_nicht_beschrieben(self):
        with open(self.pfad, 'rb') as fh:
            vorher = fh.read()
        kopfformen.datei_lesen(self.pfad)
        with open(self.pfad, 'rb') as fh:
            self.assertEqual(fh.read(), vorher)


if __name__ == '__main__':
    unittest.main(verbosity=2)