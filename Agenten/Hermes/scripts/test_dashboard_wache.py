"""Tests fuer die Dashboard-Wache (Agenten/Hermes/scripts/dashboard-wache.py).

Geprueft wird die REGEL, nicht ein Tageswert:

- gesund (antwortet)            -> LEERE Ausgabe (Watchdog: nichts senden),
- Dienst weg (kein Prozess)     -> heilt: Aufgabe starten, Meldung,
- haengt (idle, keine Antwort)  -> heilt: Kette beenden UND starten, Meldung,
- arbeitet (CPU steigt)         -> KEIN Eingriff (ein Bau laeuft), erst nach
                                   BUILD_GRACE_MIN eine Meldung,
- Heilung ohne Wirkung          -> Meldung mit "fehlgeschlagen", kein Absturz,
- ein `hermes update` laeuft    -> KEIN Eingriff (Gnadenfrist still, danach Meldung),
- Bremse                        -> hoechstens ein Heilversuch je Frist,
- dieselbe Feststellung         -> beim zweiten Lauf still,
- --nicht-heilen                -> meldet, greift aber nicht ein (Alarmrichtung),
- --selbsttest                  -> zeigt die Form, schreibt keinen Zustand,
- kette()                       -> nimmt die KINDER mit (dort laeuft der Bau),
- beenden()                     -> nur Stop-Process, nie taskkill.

Gemessen wird AUSSCHLIESSLICH mit Attrappen: kein Netz, kein Prozesskill, die
echte Aufgabe `Hermes_Dashboard` und die echte Zustandsdatei bleiben unberuehrt.

Start:  python -m unittest test_dashboard_wache  (aus diesem Ordner)
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHE_PFAD = HIER / "dashboard-wache.py"

_spec = importlib.util.spec_from_file_location("dashboard_wache", WACHE_PFAD)
wache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wache)

SEAMS = ("antwortet", "port_halter", "dashboard_pids", "beenden", "starten",
         "update_laeuft", "warten", "arbeitet", "_rotieren")


class Basis(unittest.TestCase):
    """Alle Seams ersetzt: die Wache darf in Tests NICHTS am Host tun."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dashboard-wache-"))
        self.stand = self.tmp / "stand.json"
        self.gestartet = []
        self.beendet = []
        self.gesund = True
        self.gesund_nach_start = True
        self.halter = []
        self.pids = []
        self.update = False
        self.arbeitet_flag = False

        self._alt = {name: getattr(wache, name) for name in SEAMS}
        wache.antwortet = lambda url=None, frist=None: self.gesund
        wache.port_halter = lambda port=None: list(self.halter)
        wache.dashboard_pids = lambda: list(self.pids)
        wache.beenden = lambda pids: (self.beenden_echt(pids), [])
        wache.starten = lambda: (self.gestartet.append(1) or "Aufgabe 'Hermes_Dashboard' gestartet")
        wache.update_laeuft = lambda: self.update
        wache.warten = lambda url=None, frist=None, schritt=None: self.gesund_nach_start
        wache.arbeitet = lambda pids=None, warte=None, schwelle=None: self.arbeitet_flag
        wache._rotieren = lambda pfad, **kw: None   # das echte Log unberuehrt

    def tearDown(self):
        for name, fn in self._alt.items():
            setattr(wache, name, fn)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def beenden_echt(self, pids):
        self.beendet.extend(pids)
        return list(pids)

    def stand_schreiben(self, daten):
        self.stand.write_text(json.dumps(daten), encoding="utf-8")

    def stand_lesen(self):
        return json.loads(self.stand.read_text(encoding="utf-8"))

    def lauf(self, *argumente):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = wache.main(["--stand", str(self.stand), *argumente])
        return code, puffer.getvalue()


class RegelTest(Basis):

    def test_gesund_ist_still(self):
        code, ausgabe = self.lauf()
        self.assertEqual(code, 0)
        self.assertEqual(ausgabe.strip(), "", "ein gesundes Dashboard darf nichts melden")
        self.assertEqual(self.gestartet, [], "gesund: kein Start")
        self.assertIn("letzter_gesund", self.stand_lesen())

    def test_gesund_loescht_die_ausfallspur(self):
        self.stand_schreiben({"ausgefallen_seit": (datetime.now() - timedelta(hours=3)).isoformat(),
                              "letzter_versuch": datetime.now().isoformat()})
        _, ausgabe = self.lauf()
        self.assertEqual(ausgabe.strip(), "")
        stand = self.stand_lesen()
        self.assertNotIn("ausgefallen_seit", stand)
        self.assertNotIn("letzter_versuch", stand)

    def test_dienst_weg_wird_gestartet_und_gemeldet(self):
        self.gesund = False
        self.gesund_nach_start = True
        _, ausgabe = self.lauf()
        self.assertEqual(len(self.gestartet), 1, "die Aufgabe muss gestartet werden")
        self.assertEqual(self.beendet, [], "ohne Prozess gibt es nichts zu beenden")
        self.assertIn("laeuft nicht", ausgabe)
        self.assertIn("antwortet wieder", ausgabe)

    def test_haenger_wird_beendet_und_neu_gestartet(self):
        self.gesund = False
        self.halter = [27864]
        self.pids = [15372, 16768, 27864]
        _, ausgabe = self.lauf()
        self.assertEqual(sorted(self.beendet), [15372, 16768, 27864])
        self.assertEqual(len(self.gestartet), 1)
        self.assertIn("haengt", ausgabe)
        self.assertIn("Kette beendet", ausgabe)

    def test_heilung_ohne_wirkung_wird_gemeldet(self):
        self.gesund = False
        self.gesund_nach_start = False
        self.halter = [27864]
        _, ausgabe = self.lauf()
        self.assertIn("fehlgeschlagen", ausgabe)
        self.assertIn("dashboard-restart.log", ausgabe)
        self.assertIn("ausgefallen_seit", self.stand_lesen(), "der Ausfall bleibt vermerkt")

    def test_zweiter_lauf_bei_gleicher_lage_ist_still(self):
        self.gesund = False
        self.gesund_nach_start = False
        self.halter = [27864]
        _, erster = self.lauf()
        self.assertNotEqual(erster.strip(), "")
        _, zweiter = self.lauf()
        self.assertEqual(zweiter.strip(), "",
                         "dieselbe Feststellung darf nicht wiederholt werden")
        self.assertEqual(len(self.gestartet), 1, "auch der zweite Lauf heilt nicht noch einmal")


class BauLaeuftTest(Basis):
    """Ein laufender Bau ist kein Haenger: er darf Minuten dauern und wird
    NICHT abgerissen (sonst bliebe ein halb gebautes dist zurueck)."""

    def test_bau_wird_nicht_abgerissen(self):
        self.gesund = False
        self.arbeitet_flag = True
        self.pids = [75336, 60008]
        self.halter = []
        _, ausgabe = self.lauf()
        self.assertEqual(ausgabe.strip(), "", "ein frischer Bau darf still sein")
        self.assertEqual(self.gestartet, [], "kein Neustart waehrend eines Baus")
        self.assertEqual(self.beendet, [], "kein Abbruch waehrend eines Baus")
        self.assertIn("arbeitet", self.stand_lesen().get("grund", ""))

    def test_bau_ueber_der_frist_wird_gemeldet_ohne_eingriff(self):
        self.gesund = False
        self.arbeitet_flag = True
        self.pids = [75336, 60008]
        alt = datetime.now() - timedelta(minutes=wache.BUILD_GRACE_MIN + 5)
        self.stand_schreiben({"ausgefallen_seit": alt.isoformat()})
        _, ausgabe = self.lauf()
        self.assertIn("Bau/Start laeuft", ausgabe)
        self.assertIn("kein Eingriff", ausgabe)
        self.assertEqual(self.gestartet, [])
        self.assertEqual(self.beendet, [])

    def test_frische_instanz_die_baut_ist_kein_fehlschlag(self):
        """Nach dem Neustart baut die neue Instanz denselben Kram - das ist
        kein 'Heilversuch fehlgeschlagen'."""
        self.gesund = False
        self.gesund_nach_start = False
        self.halter = [27864]
        self.arbeitet_flag = False           # im ersten Lauf: echter Haenger
        self.pids = [27864]
        ergebnis = {}

        def arbeitet_nach_start(pids=None, warte=None, schwelle=None):
            # erster Aufruf (Vorpruefung) = False, danach (frische Instanz) True
            ergebnis["n"] = ergebnis.get("n", 0) + 1
            return ergebnis["n"] > 1

        wache.arbeitet = arbeitet_nach_start
        _, ausgabe = self.lauf()
        self.assertEqual(ausgabe.strip(), "",
                         "eine bauende frische Instanz darf keinen Fehlschlag melden")
        self.assertEqual(len(self.gestartet), 1)


class UpdateTest(Basis):

    def test_kein_eingriff_waehrend_eines_updates(self):
        self.gesund = False
        self.update = True
        self.stand_schreiben({"ausgefallen_seit": datetime.now().isoformat()})
        _, ausgabe = self.lauf()
        self.assertEqual(ausgabe.strip(), "",
                         "innerhalb der Gnadenfrist muss die Wache schweigen")
        self.assertEqual(self.gestartet, [], "waehrend eines Updates NIE starten")

    def test_update_ueber_der_gnadenfrist_meldet_ohne_eingriff(self):
        self.gesund = False
        self.update = True
        alt = datetime.now() - timedelta(minutes=wache.UPDATE_GRACE_MIN + 5)
        self.stand_schreiben({"ausgefallen_seit": alt.isoformat()})
        _, ausgabe = self.lauf()
        self.assertIn("hermes update", ausgabe)
        self.assertIn("kein Eingriff", ausgabe)
        self.assertEqual(self.gestartet, [], "auch nach der Frist nicht starten")


class BremseTest(Basis):

    def test_zweiter_heilversuch_wartet_die_bremse_ab(self):
        self.gesund = False
        self.gesund_nach_start = False
        self.halter = [27864]
        self.stand_schreiben({
            "ausgefallen_seit": (datetime.now() - timedelta(hours=2)).isoformat(),
            "letzter_versuch": (datetime.now() - timedelta(minutes=5)).isoformat(),
        })
        _, ausgabe = self.lauf()
        self.assertEqual(self.gestartet, [], "die Bremse muss den zweiten Versuch verhindern")
        self.assertEqual(self.beendet, [])
        self.assertEqual(ausgabe.strip(), "", "in der Bremse gibt es nichts Neues zu melden")
        self.assertIn("Bremse", self.stand_lesen().get("grund", ""))

    def test_nach_ablauf_der_bremse_wird_wieder_geheilt(self):
        self.gesund = False
        self.gesund_nach_start = True
        self.stand_schreiben({
            "ausgefallen_seit": (datetime.now() - timedelta(hours=2)).isoformat(),
            "letzter_versuch": (datetime.now() - timedelta(minutes=wache.HEIL_BREMSE_MIN + 1)).isoformat(),
        })
        _, ausgabe = self.lauf()
        self.assertEqual(len(self.gestartet), 1)
        self.assertIn("antwortet wieder", ausgabe)


class AlarmrichtungTest(Basis):

    def test_nicht_heilen_meldet_ohne_einzugreifen(self):
        self.gesund = False
        self.halter = [27864]
        _, ausgabe = self.lauf("--nicht-heilen")
        self.assertIn("--nicht-heilen", ausgabe)
        self.assertEqual(self.gestartet, [])
        self.assertEqual(self.beendet, [])

    def test_selbsttest_zeigt_form_und_schreibt_nichts(self):
        self.gesund = False
        _, ausgabe = self.lauf("--selbsttest")
        self.assertIn("Selbsttest", ausgabe)
        self.assertFalse(self.stand.exists(), "der Selbsttest darf keinen Zustand schreiben")
        self.assertEqual(self.gestartet, [])


class ReineFunktionenTest(unittest.TestCase):
    """Die Prozesskette wird OHNE PowerShell geprueft - die Baumregel ist reine
    Rechnung, und genau sie entscheidet, ob der Bau mitgemessen wird."""

    def test_kette_nimmt_die_kinder_mit(self):
        eltern = {100: 4, 101: 100, 102: 101, 999: 4, 103: 0}
        self.assertEqual(wache.kette([100], eltern), {100, 101, 102})
        self.assertEqual(wache.kette([], eltern), set())
        self.assertEqual(wache.kette([103], eltern), {103})

    def test_kette_ohne_elternangabe_bleibt_bei_den_wurzeln(self):
        # ein Prozess, dessen Vater 0 ist (Wurzel), zieht nichts nach
        self.assertEqual(wache.kette([7], {}), {7})


class BeendenTest(unittest.TestCase):
    """Eine Wache beendet per Stop-Process (nativ) - `taskkill` tut aus einer
    Sitzung still nichts (22.09.2026, zweimal erlebt)."""

    def test_beendet_nur_per_stop_process(self):
        gesehen = []
        alt_ps, alt_sleep = wache._ps, wache.time.sleep
        wache._ps = lambda skript, frist=60: (gesehen.append(skript) or "")
        wache.time.sleep = lambda *_: None
        try:
            beendet, uebrig = wache.beenden([111, 222])
        finally:
            wache._ps, wache.time.sleep = alt_ps, alt_sleep
        befehle = [s for s in gesehen if "Stop-Process" in s]
        self.assertEqual(len(befehle), 1, "es muss genau ein Beende-Befehl abgesetzt werden")
        self.assertIn("Stop-Process -Id 111", befehle[0])
        self.assertIn("Stop-Process -Id 222", befehle[0])
        self.assertFalse([s for s in gesehen if "taskkill" in s],
                         "taskkill beendet aus einer Sitzung nichts")
        self.assertEqual(beendet, [111, 222])
        self.assertEqual(uebrig, [])


class RotationTest(unittest.TestCase):
    """_rotieren() haelt dashboard-restart.log unter der Frist (T-196):
    unterhalb nichts tun, oberhalb die alte Fassung nach <name>.1 wandern,
    eine bestehende <name>.1 ersetzbar, kein Absturz bei fehlender Datei."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="wache-rotation-"))
        self.log = self.tmp / "dashboard-restart.log"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_unter_der_frist_bleibt_die_datei(self):
        self.log.write_text("a" * 10, encoding="utf-8")
        wache._rotieren(self.log, byte_frist=1024)
        self.assertTrue(self.log.exists(), "kleines Log wird nicht rotiert")
        self.assertFalse((self.tmp / "dashboard-restart.log.1").exists())

    def test_ueber_der_frist_wandert_nach_dot1(self):
        self.log.write_text("a" * 5000, encoding="utf-8")
        wache._rotieren(self.log, byte_frist=4096)
        self.assertFalse(self.log.exists(), "grosses Log wird umbenannt")
        self.assertTrue((self.tmp / "dashboard-restart.log.1").exists())
        self.assertEqual((self.tmp / "dashboard-restart.log.1").stat().st_size, 5000)

    def test_bestehende_dot1_wird_ersetzt(self):
        (self.tmp / "dashboard-restart.log.1").write_text("alt", encoding="utf-8")
        self.log.write_text("a" * 5000, encoding="utf-8")
        wache._rotieren(self.log, byte_frist=4096)
        self.assertEqual((self.tmp / "dashboard-restart.log.1").stat().st_size, 5000,
                         "eine alte Generation wird ueberschrieben, nicht angehaengt")

    def test_fehlt_die_datei_geschieht_nichts(self):
        wache._rotieren(self.log, byte_frist=4096)   # darf nicht werfen
        self.assertFalse((self.tmp / "dashboard-restart.log.1").exists())


class RotationInLaufTest(Basis):
    """Der Eigen-Lauf der Wache erhaelt die Protokollgrenze: main() ruft
    _rotieren auf (getrennt, weil die Zustands-Laeufe die echte Datei
    unberuehrt lassen muessen)."""

    def test_der_eigenlauf_ruft_rotation(self):
        alt = wache._rotieren
        gerufen = []
        wache._rotieren = lambda pfad, **kw: gerufen.append(str(pfad))
        try:
            code, ausgabe = self.lauf()
        finally:
            wache._rotieren = alt
        self.assertEqual(code, 0)
        self.assertTrue(any("dashboard-restart.log" in p for p in gerufen))

    def test_selbsttest_ruft_rotation_ohne_netz(self):
        alt = wache._rotieren
        gerufen = []
        wache._rotieren = lambda pfad, **kw: gerufen.append(str(pfad))
        try:
            code, ausgabe = self.lauf("--selbsttest")
        finally:
            wache._rotieren = alt
        self.assertEqual(code, 0)
        self.assertIn("Selbsttest", ausgabe)
        self.assertTrue(any("dashboard-restart.log" in p for p in gerufen))


if __name__ == "__main__":
    unittest.main(verbosity=2)