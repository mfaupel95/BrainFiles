"""Tests fuer den Neustart-Teil der omnitrade2-sol-wache.

Geprueft wird die REGEL und der Ablauf, nicht ein Tageswert. Kein Test startet
einen echten Prozess: der Nachzieher wird durch eine Attrappe ersetzt, die jeden
Aufruf mitschreibt (loop_beenden, lauf_starten).

Regeln (Entscheidung Max 21.10.2026):
  - gesunder Lauf wird nie angefasst
  - offene, NICHT vollstaendig gedeckte Position: kein Neustart, nur Meldung
  - unbekannte Position (Boerse nicht lesbar): kein Neustart
  - hoechstens ein Neustart je NEUSTART_ABSTAND_S
  - nach dem Start muss ein frischer Status kommen, sonst Warnung ohne Sperre
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import time
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
WACHE_PFAD = HIER / "omnitrade2-sol-wache.py"

_spec = importlib.util.spec_from_file_location("omnitrade2_sol_wache", WACHE_PFAD)
wache = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wache)

JETZT = 1_800_000_000.0


class NachzieherAttrappe:
    """Ersetzt das nachziehen-Modul: zeichnet auf, was mit Prozess/Start passiert."""

    LAUF_DATEI = "lauf.json"

    def __init__(self, pid=None, lebt=False, beenden_ok=True, status_schreiben=True):
        self.pid = pid
        self.lebt = lebt
        self.beenden_ok = beenden_ok
        self.status_schreiben = status_schreiben
        self.rufe = []

    # --- Lesen -----------------------------------------------------------
    def lies_json(self, pfad, vorgabe):
        return {"inst": "SOL-USD_UM_XPERP-310404"}

    def okxf_laden(self):
        return object()

    def position(self, okxf, inst):
        return getattr(self, "pos", None)

    def deckung(self, okxf, inst, seite=None):
        return (getattr(self, "gedeckt", 0.0), 1, [])

    # --- Prozess/Start ---------------------------------------------------
    def loop_pid(self):
        self.rufe.append("loop_pid")
        return self.pid

    def pid_lebt(self, pid):
        self.rufe.append("pid_lebt")
        return self.lebt

    def loop_beenden(self, pid):
        self.rufe.append("loop_beenden")
        return self.beenden_ok

    def lauf_starten(self):
        self.rufe.append("lauf_starten")
        if self.status_schreiben:
            _status_schreiben(alter_s=1.0)
        return "GESTARTET PID 999 phase=voll\nStatus: irgendwo"


def _status_schreiben(alter_s=1.0, state="running", pid=999):
    """Schreibt eine Statusdatei mit frischem/altem updated_ms an wache.STATUS_FILE."""
    if not wache.STATUS_FILE:
        wache.STATUS_FILE = _tempdatei("status.json")
    with open(wache.STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "state": state,
                "pid": pid,
                "updated_ms": int((time.time() - alter_s) * 1000),
                "candles_seen": 300,
                "last_error": "",
                "recent_orders": [],
                "net_quantity": 0.0,
                "orders_placed": 0,
                "orders_rejected": 0,
            },
            f,
        )


_ANGELEGT = []


def _tempdatei(name):
    import tempfile

    pfad = str(Path(tempfile.mkdtemp(prefix="wache2-")) / name)
    _ANGELEGT.append(pfad)
    return pfad


class RegelTest(unittest.TestCase):
    """neustart_grund: reine Entscheidung, ohne Prozess und ohne Netz."""

    def test_gesunder_lauf_wird_nicht_angefasst(self):
        self.assertIsNone(wache.neustart_grund(None, (0.0, 0.0), JETZT, {}))

    def test_stehender_lauf_ohne_position_wird_neu_gestartet(self):
        grund = wache.neustart_grund("Status 42 min alt, state=running", (0.0, 0.0), JETZT, {})
        self.assertEqual(grund, "Status 42 min alt, state=running")

    def test_ungedeckte_position_wird_nur_gemeldet(self):
        # 10 Kontrakte offen, kein Schutz: ein Neustart wuerde die Position
        # unbewacht lassen, wenn der Prozess sie nicht mehr kennt.
        self.assertIsNone(
            wache.neustart_grund("state=running", (10.0, 0.0), JETZT, {})
        )

    def test_teilweise_gedeckte_position_wird_nicht_neu_gestartet(self):
        self.assertIsNone(
            wache.neustart_grund("state=running", (10.0, 6.0), JETZT, {})
        )

    def test_voll_gedeckte_position_wird_neu_gestartet(self):
        # Der Schutz liegt als conditional Order an der Boerse und ueberlebt
        # einen Prozesswechsel.
        self.assertEqual(
            wache.neustart_grund("state=running", (10.0, 10.0), JETZT, {}),
            "state=running",
        )

    def test_unbekannte_position_wird_nicht_neu_gestartet(self):
        self.assertIsNone(wache.neustart_grund("state=running", None, JETZT, {}))

    def test_sperre_gegen_startschleife(self):
        merk = {"neustart_ts": JETZT - 60}
        self.assertIsNone(wache.neustart_grund("Status 12 min alt", (0.0, 0.0), JETZT, merk))

    def test_nach_der_sperre_wieder_erlaubt(self):
        merk = {"neustart_ts": JETZT - wache.NEUSTART_ABSTAND_S - 1}
        self.assertEqual(
            wache.neustart_grund("Status 12 min alt", (0.0, 0.0), JETZT, merk),
            "Status 12 min alt",
        )


class AblaufTest(unittest.TestCase):
    """neustart_ausfuehren / haupt: Ablauf mit Attrappe, nie ein echter Prozess."""

    def setUp(self):
        self.alt_status = wache.STATUS_FILE
        self.alt_merk = wache.MERK_FILE
        self.alt_warten = wache.NEUSTART_WARTE_S
        self.alt_nachzieher = wache._nachzieher
        wache.STATUS_FILE = _tempdatei("status.json")
        wache.MERK_FILE = _tempdatei("merk.json")
        wache.NEUSTART_WARTE_S = 1
        self.merk = {}

    def tearDown(self):
        wache.STATUS_FILE = self.alt_status
        wache.MERK_FILE = self.alt_merk
        wache.NEUSTART_WARTE_S = self.alt_warten
        wache._nachzieher = self.alt_nachzieher

    def _binden(self, attrappe):
        wache._nachzieher = lambda: (attrappe, None)

    def test_haengender_prozess_wird_beendet_und_neu_gestartet(self):
        self._binden(NachzieherAttrappe(pid=4242, lebt=True))
        texte = wache.neustart_ausfuehren("Status 42 min alt", self.merk, jetzt_s=JETZT)
        zusammen = "\n".join(texte)

        self.assertIn("PID 4242 beendet", zusammen)
        self.assertIn("NEU GESTARTET", zusammen)
        self.assertIn("neuer Status frisch", zusammen)
        self.assertEqual(self.merk.get("neustart_ts"), JETZT)

    def test_start_ohne_prozess_beendet_nichts(self):
        attrappe = NachzieherAttrappe(pid=None, lebt=False)
        self._binden(attrappe)
        texte = wache.neustart_ausfuehren("state=stopped", self.merk, jetzt_s=JETZT)

        self.assertNotIn("loop_beenden", attrappe.rufe)
        self.assertIn("lauf_starten", attrappe.rufe)
        self.assertIn("NEU GESTARTET", "\n".join(texte))

    def test_prozess_laesst_sich_nicht_beenden_dann_kein_start(self):
        attrappe = NachzieherAttrappe(pid=4242, lebt=True, beenden_ok=False)
        self._binden(attrappe)
        texte = wache.neustart_ausfuehren("state=running", self.merk, jetzt_s=JETZT)

        self.assertIn("loop_beenden", attrappe.rufe)
        self.assertNotIn("lauf_starten", attrappe.rufe, "ohne beendeten Prozess nicht starten")
        self.assertIn("abgebrochen", "\n".join(texte))
        self.assertNotIn("neustart_ts", self.merk)

    def test_start_ohne_frischen_status_warnt_und_sperrt_nicht(self):
        self._binden(NachzieherAttrappe(pid=None, lebt=False, status_schreiben=False))
        _status_schreiben(alter_s=3600.0)  # alter Stand bleibt stehen
        texte = wache.neustart_ausfuehren("Status 60 min alt", self.merk, jetzt_s=JETZT)

        self.assertIn("WARNUNG", "\n".join(texte))
        self.assertNotIn("neustart_ts", self.merk, "ohne frischen Status keine Sperre setzen")

    def test_haupt_startet_den_haengenden_lauf(self):
        # Alter Status, Prozess haengt, keine Position -> Meldung + Neustart.
        self._binden(NachzieherAttrappe(pid=4242, lebt=True))
        _status_schreiben(alter_s=2400.0, state="running", pid=4242)

        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            wache.haupt()

        aus = puffer.getvalue()
        self.assertIn("Loop HAENGT", aus)
        self.assertIn("NEU GESTARTET", aus)
        self.assertEqual(self.merk_stand().get("letzter_neustart_pid"), 999)

    def merk_stand(self):
        try:
            with open(wache.MERK_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}


if __name__ == "__main__":
    unittest.main(verbosity=2)
