"""Tests fuer die Spur-Wache: die zwei neuen Spuren supertrend und iv_waelle.

ANLASS (Auftrag Max, 22.09.2026: "Ja aufnehmen"). Beide Spuren sind still, und
bei beiden ist Stille der Normalfall:

  * `supertrend` stand nach einem stillen `ImportError` FUENF TAGE ohne Signal,
    ohne dass es auffiel.
  * `iv_waelle` hat seit dem 19.09. keine einzige Journalzeile geschrieben.

Ohne Wache ist "wartet korrekt" nicht von "kaputt" zu unterscheiden. Geprueft
wird hier die ENTSCHEIDUNG der beiden Funktionen — ohne Netz, mit
nachgebauten Spuren (`_spur_laden` wird ersetzt) und einem Temp-Ordner fuer
den Zustand. Die echten Buecher werden nur gelesen, nie geschrieben.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
HANDEL = HIER.parent
WACHE = HIER.parents[1] / "Hermes" / "scripts" / "spur-wache.py"


def _lade(pfad, name="spur_wache_t"):
    spec = importlib.util.spec_from_file_location(name, str(pfad))
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name] = modul
    spec.loader.exec_module(modul)
    return modul


KERZEN = [[str(1700000000 + i * 3600), "1", "1", "1", "100", "1"]
          for i in range(400)]


def _supertrend_stub(signal_wert):
    return types.SimpleNamespace(
        lade_kerzen=lambda inst, takt, anzahl: KERZEN,
        signal=lambda k, idx: signal_wert,
        atr_abs=lambda k, idx, n=14: 1.0,
    )


def _ivwaelle_stub(daten, sig):
    return types.SimpleNamespace(
        _hole_markt=lambda w: (daten, {}, []),
        spanne_und_signal=lambda d, w: sig,
    )


class SupertrendZurueckgehalten(unittest.TestCase):
    def setUp(self):
        self.m = _lade(WACHE)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.alt = self.m.HANDEL
        self.m.HANDEL = Path(self.tmp.name)
        self.addCleanup(lambda: setattr(self.m, "HANDEL", self.alt))
        self.w = {"instrument": "BTC-USDT-SWAP", "mindest_kerzen": 300,
                  "max_offene_positionen": 4}

    def _zustand(self, n):
        p = self.m.HANDEL / "supertrend"
        p.mkdir(parents=True, exist_ok=True)
        (p / "zustand.json").write_text(
            json.dumps({"positionen": [{"inst": "X%d" % i} for i in range(n)]}),
            encoding="utf-8")

    def test_wende_mit_vollem_buch_wird_gemeldet(self):
        self._zustand(4)
        self.m._spur_laden = lambda spur: _supertrend_stub(("short", 100.0))
        kennung, text = self.m._zurueck_supertrend(self.w)
        self.assertTrue(kennung)
        self.assertIn("Buch voll", text)

    def test_ohne_wende_bleibt_es_still(self):
        self._zustand(0)
        self.m._spur_laden = lambda spur: _supertrend_stub(None)
        self.assertEqual(self.m._zurueck_supertrend(self.w), (None, None))

    def test_fehler_wird_gemeldet_nicht_verschluckt(self):
        def platzt(spur):
            raise ImportError("indikatoren fehlen")
        self.m._spur_laden = platzt
        kennung, text = self.m._zurueck_supertrend(self.w)
        self.assertIsNone(kennung, "kein Signal, sondern ein Fehler")
        self.assertIn("nicht ladbar", text)

    def test_zu_wenige_kerzen_sind_kein_befund(self):
        self._zustand(0)
        self.m._spur_laden = lambda spur: types.SimpleNamespace(
            lade_kerzen=lambda inst, takt, anzahl: KERZEN[:10],
            signal=lambda k, idx: ("short", 1.0),
            atr_abs=lambda k, idx, n=14: 1.0)
        self.assertEqual(self.m._zurueck_supertrend(self.w), (None, None))


class IvWaelleZurueckgehalten(unittest.TestCase):
    def setUp(self):
        self.m = _lade(WACHE)
        self.w = {"instrument": "BTC-PERPETUAL", "naehe_prozent": 0.5}

    def _sig(self, lage, strike, sigma=1.5, richtung="kein_signal", spot=100000.0):
        return ({"richtung": richtung, "spot": spot,
                 "lagen": {"call_wand": {"lage": lage, "strike": strike,
                                         "abstand_sigma": sigma}}},
                {"BTC-PERPETUAL": {"spot": spot}})

    def test_handelbare_wand_in_der_ferne_wird_gemeldet(self):
        sig, daten = self._sig("handelbar", 105000.0)
        self.m._spur_laden = lambda spur: _ivwaelle_stub(daten, sig)
        kennung, text = self.m._zurueck_ivwaelle(self.w)
        self.assertTrue(kennung, "einmal je Tag und Wand")
        self.assertIn("handelbare Wand", text)
        self.assertIn("5.00 %", text)

    def test_kurs_an_der_wand_ist_kein_befund(self):
        sig, daten = self._sig("handelbar", 100200.0)
        self.m._spur_laden = lambda spur: _ivwaelle_stub(daten, sig)
        self.assertEqual(self.m._zurueck_ivwaelle(self.w), (None, None))

    def test_signal_da_heisst_die_spur_handelt(self):
        sig, daten = self._sig("handelbar", 100200.0, richtung="short")
        self.m._spur_laden = lambda spur: _ivwaelle_stub(daten, sig)
        self.assertEqual(self.m._zurueck_ivwaelle(self.w), (None, None))

    def test_nicht_handelbare_wand_ist_melde_rauschen(self):
        # "zu weit" (mehr als 3 Sigma) ist eine Lage, kein Signal - taeglich
        # gemeldet waere es Rauschen.
        sig, daten = self._sig("zu_weit", 200000.0, sigma=9.0)
        self.m._spur_laden = lambda spur: _ivwaelle_stub(daten, sig)
        self.assertEqual(self.m._zurueck_ivwaelle(self.w), (None, None))

    def test_datenfehler_wird_nicht_als_signal_gemeldet(self):
        self.m._spur_laden = lambda spur: types.SimpleNamespace(
            _hole_markt=lambda w: ({}, {}, ["DVOL nicht erreichbar"]),
            spanne_und_signal=lambda d, w: {})
        self.assertEqual(self.m._zurueck_ivwaelle(self.w), (None, None))


class BeideSpurenSindAngemeldet(unittest.TestCase):
    def test_wache_kennt_vier_spuren(self):
        m = _lade(WACHE)
        # Die Zahl "vier" stand hier fest und ist bei jeder neuen Spur
        # kaputtgegangen - ein Test gegen eine feste Anzahl meldet
        # Aenderung, nicht Fehler. Geprueft werden die zwei Eigenschaften,
        # die gelten SOLLEN:
        #
        # 1. Keine Phantomspur - die Wache darf nichts melden, was es auf
        #    der Platte nicht gibt.
        # 2. Keine stumme Spur - wo eine signal_queue.json liegt, muss die
        #    Wache die Spur kennen, sonst meldet sie deren Wechsel nie.
        import json
        import os
        handel = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              os.pardir)
        phantome = sorted(n for n in m.SPUREN
                          if not os.path.isdir(os.path.join(handel, n)))
        self.assertEqual(phantome, [],
                         "Wache meldet Spuren, die es nicht gibt: %s" % phantome)

        mit_queue = set()
        for name in os.listdir(handel):
            ordner = os.path.join(handel, name)
            if not os.path.isdir(ordner):
                continue
            for datei in os.listdir(ordner):
                if datei.startswith("signal_queue") and \
                        datei.endswith(".json") and \
                        os.path.getsize(os.path.join(ordner, datei)) > 2:
                    mit_queue.add(name)
        stumm = sorted(n for n in mit_queue if n not in m.SPUREN)
        self.assertEqual(stumm, [],
                         "Spuren mit Warteschlange, aber ohne Wache: %s" % stumm)


    def test_jede_queuespur_hat_eine_wache(self):
        """DIE EIGENSCHAFT, um die es geht (Befund 04.10.2026, T-348).

        Die Fassung oben fragt nur Spuren mit einer GEFUELLTEN Queue ab. Eine
        Spur mit einer LEEREN Queue faellt dadurch durch - und genau daran ist
        `omnitrade_futures` am 04.10. gescheitert: die Warteschlange stand
        leer, die Wache fehlte, und das leere Warten ist nicht von einer
        kaputten Spur zu unterscheiden.

        REGEL: wer ueber `trigger_modus: signal` echte Warteschlangen
        erzeugt, wird beobachtet - unabhaengig davon, ob heute etwas drin
        liegt.

        WICHTIG, und der Grund fuer diese Fassung: `trigger_modus: signal`
        allein ist NICHT das Merkmal einer Warteschlange. Sieben Spuren
        tragen das Feld, aber nur vier erzeugen eine `signal_queue.json`:
        die anderen fuehren ein eigenes `handeln.py` und benutzen
        `signal_wechsel.zugelassen()` - ein Gatter AM Einstieg, das sperrt
        statt zu melden. Diese Spuren erzeugen keine Warteschlange und
        brauchen deshalb keine Wache. Eine Fassung, die nur auf das Feld
        schaut, meldet sieben statt vier Spuren und wird beim naechsten
        Umbau wieder still.

        Die Warteschlangen-Dateien sind Laufzeitstand und nicht versioniert,
        darum baut der Test seine eigene: er liest die Liste der Spuren mit
        Signal-Modus aus den echten Wachen und legt die Queue in einem
        Tempordner an. Sonst prueft der Test nichts - genau das war der
        Befund, den er aufdecken sollte.
        """
        import json
        import os
        import shutil
        import tempfile
        handel = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              os.pardir)
        m = _lade(WACHE)
        tmp = tempfile.mkdtemp(prefix="queuespuren-")
        self.addCleanup(shutil.rmtree, tmp, True)
        alt_handel = m.HANDEL
        m.HANDEL = Path(tmp)
        self.addCleanup(setattr, m, "HANDEL", alt_handel)

        signal_spuren = []
        for name in sorted(os.listdir(handel)):
            pfad = os.path.join(handel, name, "wachen.json")
            if not os.path.isfile(pfad):
                continue
            try:
                with open(pfad, encoding="utf-8") as fh:
                    w = json.load(fh) or {}
            except (OSError, ValueError):
                continue
            if str(w.get("trigger_modus") or "").lower() == "signal":
                signal_spuren.append(name)
        self.assertTrue(signal_spuren,
                        "keine Spur traegt trigger_modus - dann prueft "
                        "dieser Test nichts")
        # NUR die Spuren bekommen eine Queue, die sie auch erzeugen. Das ist
        # `spur_buch.zyklus`: dort liegt `_signal_queue`, und nur dieser Weg
        # legt eine Warteschlange an. Die Spuren mit eigenem `handeln.py`
        # und `signal_wechsel.zugelassen()` sperren am Einstieg und melden
        # nirgends hin - fuer die waere eine Queue erfunden. Genau das war
        # der Fehler der ersten Fassung dieses Tests: sie legte fuer ALLE
        # sieben Spuren mit `trigger_modus` eine Queue an und beanstandete
        # dann zu Recht sieben fehlende Wachen.
        erzeuger = []
        for name in signal_spuren:
            handeln = os.path.join(handel, name, "handeln.py")
            if not os.path.isfile(handeln):
                continue
            with open(handeln, encoding="utf-8") as fh:
                text = fh.read()
            if ".zyklus(" in text:
                erzeuger.append(name)
        self.assertTrue(erzeuger, "keine Spur erzeugt eine Queue - dann "
                                  "prueft dieser Test nichts")
        for name in erzeuger:
            (Path(tmp) / name).mkdir(parents=True, exist_ok=True)
            # LEER auf dem Platz: genau der Fall, den die alte Fassung
            # uebersehen hat - die Warteschlange existiert, ist aber leer.
            (Path(tmp) / name / "signal_queue.json").write_text(
                "[]", encoding="utf-8")
        stumm = sorted(n for n in erzeuger if n not in m.SPUREN)
        self.assertEqual(stumm, [],
                         "Spuren mit Signal-Queue, aber ohne Wache: %s" % stumm)


if __name__ == "__main__":
    unittest.main()
