#!/usr/bin/env python3
"""Tests fuer die Dateischwund-Wache (T-100).

Prueft die REGELN, nicht den Tag. Alle Faelle laufen in einem Temp-Ordner mit
einem ECHTEN kleinen Git-Repo, damit die Git-Soll-Pruefung nicht nachgebaut
wird, sondern dieselbe bleibt. Am Ende vergleicht ein Modulwaechter die Liste
des ECHTEN Ordners vor und nach dem Lauf: ein Test, der nach draussen schreibt,
faellt damit auf.

Aufruf: python -m unittest test_dateischwund_wache   (aus diesem Ordner)
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HIER = Path(__file__).resolve().parent
MODUL = HIER / 'dateischwund-wache.py'

_echter_stand = None


def _liste(ordner: Path):
    if not ordner.is_dir():
        return None
    return sorted((p.relative_to(ordner).as_posix(), p.stat().st_size)
                  for p in ordner.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts)


def setUpModule():
    global _echter_stand
    _echter_stand = _liste(HIER)


def tearDownModule():
    jetzt = _liste(HIER)
    if jetzt != _echter_stand:
        vorher = dict(_echter_stand or [])
        nachher = dict(jetzt or [])
        neu = sorted(set(nachher) - set(vorher))
        weg = sorted(set(vorher) - set(nachher))
        raise AssertionError(
            'Der Testlauf hat den echten Ordner veraendert - neu: %s, weg: %s'
            % (neu, weg))


def _lade():
    spec = importlib.util.spec_from_file_location('dateischwund_wache', MODUL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


w = _lade()


def _git(repo: Path, *args):
    return subprocess.run(['git', '-C', str(repo), *args],
                          capture_output=True, text=True)


class TempRepo:
    """Ein echtes Mini-Repo mit einem Ordner ``scripts`` darin."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='t100-')
        self.wurzel = Path(self._tmp.name)
        self.ordner = self.wurzel / 'Agenten' / 'Hermes' / 'scripts'
        self.ordner.mkdir(parents=True)
        self.merk = self.wurzel / 'merk.json'
        _git(self.wurzel, 'init', '-q')
        _git(self.wurzel, 'config', 'user.email', 'test@local')
        _git(self.wurzel, 'config', 'user.name', 'Test')

    def schreibe(self, name: str, inhalt: str = 'x = 1\n'):
        p = self.ordner / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(inhalt, encoding='utf-8')
        return p

    def committe(self, text: str = 'stand'):
        _git(self.wurzel, 'add', '-A')
        _git(self.wurzel, 'commit', '-q', '-m', text)

    def lauf(self, **kw):
        """Ein voller Wachlauf (pruefen UND Merkstand schreiben).

        Liefert (Befundzeilen, Merkstand) - dieselbe Form wie pruefe().
        """
        return w.pruefe_und_merken(self.ordner, self.merk,
                                   wurzel=self.wurzel, **kw)

    def merk_json(self):
        return json.loads(self.merk.read_text(encoding='utf-8'))

    def schliesse(self):
        self._tmp.cleanup()


class GitSollTest(unittest.TestCase):
    """Eine Datei, die in HEAD steht und fehlt, ist der T-100-Fall."""

    def setUp(self):
        self.r = TempRepo()
        self.addCleanup(self.r.schliesse)

    def test_fehlende_datei_aus_head_wird_gemeldet(self):
        self.r.schreibe('test_wache.py')
        self.r.schreibe('wache.py', 'y = 2\n')
        self.r.committe()
        (self.r.ordner / 'test_wache.py').unlink()

        neue, stand = self.r.lauf()
        self.assertEqual(len(neue), 1, neue)
        self.assertIn('test_wache.py', neue[0])
        self.assertIn('steht aber in HEAD', neue[0])
        self.assertIn('git checkout HEAD -- ', neue[0])
        # die verbliebene Datei steht im neuen Merkstand
        self.assertIn('wache.py', stand['stand'])

    def test_vollstaendiger_baum_ergibt_keinen_befund(self):
        self.r.schreibe('test_wache.py')
        self.r.committe()
        neue, _ = self.r.lauf()
        self.assertEqual(neue, [])

    def test_neue_datei_ist_kein_befund_wird_aber_gemerkt(self):
        self.r.schreibe('wache.py')
        self.r.committe()
        self.r.lauf()
        self.r.schreibe('test_neu.py')                    # frisch, untracked
        neue, stand = self.r.lauf()
        self.assertEqual(neue, [])
        self.assertIn('test_neu.py', stand['stand'])

    def test_ordner_ausserhalb_des_repos_entfaellt_still(self):
        with tempfile.TemporaryDirectory(prefix='t100-fremd-') as d:
            fremd = Path(d)
            (fremd / 'test_a.py').write_text('x\n', encoding='utf-8')
            soll = w.git_soll(self.r.wurzel, fremd)
            self.assertEqual(soll, set())

    def test_gleiche_feststellung_wiederholt_sich_nicht(self):
        p = self.r.schreibe('test_a.py')
        self.r.committe()
        p.unlink()
        erste, _ = self.r.lauf()
        zweite, _ = self.r.lauf()
        self.assertEqual(len(erste), 1, erste)
        self.assertEqual(zweite, [])

    def test_nach_der_ruhefrist_meldet_sie_wieder(self):
        p = self.r.schreibe('test_a.py')
        self.r.committe()
        p.unlink()
        erste, _ = self.r.lauf()
        self.assertEqual(len(erste), 1, erste)
        spaeter = dt.datetime.now() + dt.timedelta(hours=w.RUHE_STUNDEN + 0.1)
        neue, _ = self.r.lauf(jetzt=spaeter)
        self.assertEqual(len(neue), 1, neue)


class MerklisteTest(unittest.TestCase):
    """Auch eine nie committete Datei darf nicht still verschwinden."""

    def setUp(self):
        self.r = TempRepo()
        self.addCleanup(self.r.schliesse)

    def test_verschwundene_untracked_datei_wird_gemeldet(self):
        p = self.r.schreibe('test_breite_wache.py', 'a' * 120)
        self.r.lauf()   # Lauf 1
        p.unlink()                                                   # Lauf 2
        neue, _ = self.r.lauf()
        self.assertEqual(len(neue), 1, neue)
        self.assertIn('verschwunden seit dem letzten Lauf', neue[0])
        self.assertIn('test_breite_wache.py', neue[0])
        self.assertIn('120 B', neue[0])

    def test_verschwundene_datei_wird_einmal_gemeldet(self):
        # Die Merkliste wird bei JEDEM Lauf neu geschrieben: eine einmal
        # verschwundene, nie committete Datei steht danach nicht mehr im Soll,
        # sie wird deshalb genau EINMAL gemeldet. Die Wiederholung nach der
        # Ruhefrist gilt fuer die Git-Soll-Klasse - dort steht die Datei in HEAD.
        p = self.r.schreibe('test_a.py')
        self.r.lauf()
        p.unlink()
        erste, _ = self.r.lauf()
        zweite, _ = self.r.lauf()
        self.assertEqual(len(erste), 1, erste)
        self.assertEqual(zweite, [])

    def test_wieder_da_loescht_den_merker(self):
        p = self.r.schreibe('test_a.py')
        self.r.lauf()
        p.unlink()
        self.r.lauf()
        self.r.schreibe('test_a.py')                     # kommt zurueck
        neue, stand = self.r.lauf()
        self.assertEqual(neue, [])
        self.assertNotIn('merk:test_a.py', stand['gemeldet'])

    def test_auf_null_byte_zusammengefallen(self):
        p = self.r.schreibe('wache.py', 'z = 3\n')
        self.r.lauf()
        p.write_text('', encoding='utf-8')
        neue, _ = self.r.lauf()
        self.assertEqual(len(neue), 1, neue)
        self.assertIn('0 Byte', neue[0])

    def test_kaputte_merkdatei_ist_kein_absturz(self):
        self.r.merk.write_text('{kein json', encoding='utf-8')
        self.r.schreibe('wache.py')
        neue, stand = self.r.lauf()
        self.assertEqual(neue, [])
        self.assertIn('wache.py', stand['stand'])

    def test_pycache_zaehlt_nicht(self):
        self.r.schreibe('__pycache__/wache.cpython-314.pyc', 'x')
        neue, stand = self.r.lauf()
        self.assertEqual(neue, [])
        self.assertEqual(stand['stand'], {})


class AusgabeTest(unittest.TestCase):
    """Leere Ausgabe = nichts senden (Muster der uebrigen Wachen)."""

    def setUp(self):
        self.r = TempRepo()
        self.addCleanup(self.r.schliesse)
        self.merk = str(self.r.merk)

    def _lauf(self, *args):
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            code = w.main(['--ordner', str(self.r.ordner),
                           '--merk', self.merk, *args])
        return code, puffer.getvalue()

    def test_ohne_befund_leere_ausgabe(self):
        self.r.schreibe('wache.py')
        code, aus = self._lauf()
        self.assertEqual(code, 0)
        self.assertEqual(aus.strip(), '')

    def test_alle_zeigt_die_lage_auch_ohne_befund(self):
        self.r.schreibe('wache.py')
        code, aus = self._lauf('--alle')
        self.assertEqual(code, 0)
        self.assertIn('Dateischwund-Wache', aus)
        self.assertIn('kein Befund', aus)

    def test_befund_wird_ausgegeben_und_geaendert_wird_nichts(self):
        p = self.r.schreibe('test_a.py', 'a' * 40)
        self._lauf()
        p.unlink()
        code, aus = self._lauf()
        self.assertEqual(code, 0)
        self.assertIn('test_a.py', aus)
        self.assertIn('Nichts wurde geaendert', aus)
        self.assertFalse(p.exists(), 'die Wache darf nichts zurueckholen')

    def test_merkdatei_wird_geschrieben(self):
        self.r.schreibe('wache.py')
        self._lauf()
        d = json.loads(Path(self.merk).read_text(encoding='utf-8'))
        self.assertIn('stand', d)
        self.assertIn('wache.py', d['stand'])


class EchterOrdnerTest(unittest.TestCase):
    """Gegenprobe am echten Ordner: kein Befund, wenn der Baum stimmt."""

    def test_echter_ordner_ohne_auffaelligkeit(self):
        with tempfile.TemporaryDirectory(prefix='t100-echt-') as d:
            neue, stand = w.pruefe(HIER, Path(d) / 'merk.json')
        self.assertEqual(neue, [], 'Befund im echten Ordner: %s' % neue)
        self.assertGreater(len(stand['stand']), 20)

    def test_wache_script_selbst_ist_erfasst(self):
        with tempfile.TemporaryDirectory(prefix='t100-echt-') as d:
            _, stand = w.pruefe(HIER, Path(d) / 'merk.json')
        self.assertIn('dateischwund-wache.py', stand['stand'])


if __name__ == '__main__':
    sys.exit(unittest.main(verbosity=2))