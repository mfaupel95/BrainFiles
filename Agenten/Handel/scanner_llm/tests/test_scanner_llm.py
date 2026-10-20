"""Tests fuer die Spur scanner_llm.

Deckt die vier geforderten Eigenschaften ab:
  (a) das LEICHTERE Regeltor laesst fuer dieselben bewerteten Daten MEHR
      Kandidaten durch als das Tor des Marktscanners,
  (b) der LLM-Filter: ohne Urteil -> nichts handelbar; Confidence unter der
      Schwelle -> uebersprungen; darueber -> handelbar (llm.entscheide wird
      gepatcht, nie das echte Modell gerufen),
  (c) der Papierzyklus oeffnet/schliesst Positionen im Buch ohne einen
      einzigen OKX-Aufruf,
  (d) die Vorschau nennt als Sperrgrund GENAU das Freigabefenster, wenn
      handel_erlaubt + freigabe.erfuellt wahr sind und nur das Fenster fehlt.

Kein Test ruft das echte LLM oder die Boerse: llm.entscheide und
handeln.marktkurs werden je Test ersetzt und in addCleanup zurueckgestellt.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent
SPUR_DIR = HIER.parent
sys.path.insert(0, str(SPUR_DIR))   # scanner_llm/ - handeln, scan

import handeln  # noqa: E402
import scan     # noqa: E402


def _w():
    """Die echte wachen.json der Spur, handel_erlaubt auf true fuer die
    Sperren-Tests (die Spur startet auf false)."""
    w = json.loads((SPUR_DIR / "wachen.json").read_text("utf-8"))
    w["handel_erlaubt"] = True
    return w


def _s(**over):
    base = {"freigabe_erfuellt": True, "herzschlag_frisch": True,
            "ev_negativ": False, "rollierender_ev": 1.0, "ruecklauf_usd": 0.0}
    base.update(over)
    return base


def _kennzahlen(vola=0.9, rsi=58.0, trend=1.0, ret=12.0, hoch=-3.0):
    return {"trend_ueber_sma": trend, "rsi14": rsi,
            "volatilitaet_pa": vola, "rendite_30t_pct": ret,
            "abstand_60t_hoch_pct": hoch}


def _wert(inst, score, verhaeltnis, vola=0.9, chance=60.0, risiko=40.0):
    return {"inst": inst, "score": score, "chance": chance, "risiko": risiko,
            "verhaeltnis": verhaeltnis, "kennzahlen": _kennzahlen(vola=vola)}


def _bericht(werte):
    return {"datum": "2026-10-13", "werte": werte}


def _scanner_tor(w):
    """Die Wachen mit den Toren des Marktscanners (60/2.0/1.5)."""
    t = dict(w)
    t.update({"mindest_score": 60.0, "max_volatilitaet_pa": 2.0,
              "mindest_chance_risiko": 1.5})
    return t


class TestLeichtesTor(unittest.TestCase):
    """(a) Das leichte Tor der Spur scanner_llm laesst mehr durch als das
    Tor des Marktscanners (60/2.0/1.5)."""

    def setUp(self):
        self.w = _w()
        self.w["mindest_score"] = 40.0
        self.w["max_volatilitaet_pa"] = 2.5
        self.w["mindest_chance_risiko"] = 1.2
        # marktkurs stubben: kein Netz im Test.
        self.addCleanup(setattr, handeln, "marktkurs", handeln.marktkurs)
        handeln.marktkurs = lambda inst: 10.0

    def test_leichtes_tor_laesst_mehr_durch_als_scanner_tor(self):
        # Ein Kandidat, der am Scanner-Tor scheitert (Score 50 < 60), aber
        # am leichten Tor besteht (50 >= 40).
        werte = [_wert("MID-USDC", score=50.0, verhaeltnis=1.4, vola=1.8)]
        leicht = handeln.vorschlaege(_bericht(werte), self.w)
        schwer = handeln.vorschlaege(_bericht(werte), _scanner_tor(self.w))
        self.assertEqual(len(leicht), 1)
        self.assertEqual(len(schwer), 0)

    def test_leichtes_tor_laesst_mehr_kandidaten_durch_als_scanner_tor(self):
        # Eine Mischung: einige bestehen nur am leichten Tor.
        werte = [
            _wert("A-USDC", score=55.0, verhaeltnis=1.4, vola=1.8),  # nur leicht
            _wert("B-USDC", score=70.0, verhaeltnis=2.0, vola=0.8),  # beide
            _wert("C-USDC", score=30.0, verhaeltnis=1.0, vola=0.5),  # keiner
        ]
        leicht = handeln.vorschlaege(_bericht(werte), self.w)
        schwer = handeln.vorschlaege(_bericht(werte), _scanner_tor(self.w))
        self.assertGreater(len(leicht), len(schwer))
        self.assertEqual(len(leicht), 2)
        self.assertEqual(len(schwer), 1)

    def test_leichtes_tor_haelt_vola_und_cr_grenzen_ein(self):
        # Vola ueber 2.5 und C/R unter 1.2 fallen auch am leichten Tor durch.
        werte = [
            _wert("V-USDC", score=80.0, verhaeltnis=2.0, vola=3.0),  # vola
            _wert("R-USDC", score=80.0, verhaeltnis=1.0, vola=0.5),  # cr
        ]
        aus = handeln.vorschlaege(_bericht(werte), self.w)
        self.assertEqual(len(aus), 0)


class TestLlmFilter(unittest.TestCase):
    """(b) Der LLM-Filter: ohne Urteil nichts handelbar, unter der Schwelle
    uebersprungen, darueber handelbar. llm.entscheide wird gepatcht."""

    def setUp(self):
        self.w = _w()
        self.w["llm_mindest_confidence"] = 65.0
        self.addCleanup(setattr, handeln, "entscheide_override",
                        handeln.entscheide_override)
        handeln.entscheide_override = None

    def _kandidat(self, inst="BTC-USDC"):
        return {"inst": inst, "score": 55.0, "einstieg": 10.0, "stop": 9.0,
                "ziel": 12.0, "stop_pct": 10.0, "usd": 60.0,
                "kennzahlen": _kennzahlen()}

    def test_ohne_urteil_nichts_handelbar(self):
        # entscheide liefert (None, info) - kein Urteil heisst kein Handel.
        handeln.entscheide_override = lambda prompt, w: (None, {"fehler": "kein Urteil"})
        aus = handeln.llm_sieben([self._kandidat()], self.w)
        self.assertEqual(len(aus), 0)

    def test_confidence_unter_schwelle_uebersprungen(self):
        # seite long, aber Confidence 50 < 65 -> uebersprungen.
        handeln.entscheide_override = lambda prompt, w: (
            "long", {"aktion": "BUY", "confidence": 50.0, "grund": "zu schwach"})
        aus = handeln.llm_sieben([self._kandidat()], self.w)
        self.assertEqual(len(aus), 0)

    def test_confidence_ueber_schwelle_handelbar(self):
        handeln.entscheide_override = lambda prompt, w: (
            "long", {"aktion": "BUY", "confidence": 80.0, "grund": "stark"})
        aus = handeln.llm_sieben([self._kandidat()], self.w)
        self.assertEqual(len(aus), 1)
        self.assertEqual(aus[0]["inst"], "BTC-USDC")

    def test_seite_short_nie_handelbar(self):
        # SELL/None ist fuer das long-only Buch nie handelbar.
        handeln.entscheide_override = lambda prompt, w: (
            "short", {"aktion": "SELL", "confidence": 90.0, "grund": "down"})
        aus = handeln.llm_sieben([self._kandidat()], self.w)
        self.assertEqual(len(aus), 0)

    def test_confidence_genau_an_schwelle_handelbar(self):
        handeln.entscheide_override = lambda prompt, w: (
            "long", {"aktion": "BUY", "confidence": 65.0, "grund": "grenze"})
        aus = handeln.llm_sieben([self._kandidat()], self.w)
        self.assertEqual(len(aus), 1)


class TestPapierzyklus(unittest.TestCase):
    """(c) Der Papierzyklus oeffnet/schliesst Positionen im Buch, ohne einen
    einzigen OKX-Aufruf. marktkurs wird gestubbt, das echte LLM nie gerufen."""

    def setUp(self):
        self.w = _w()
        self.w["llm_mindest_confidence"] = 65.0
        self.addCleanup(setattr, handeln, "marktkurs", handeln.marktkurs)
        self.addCleanup(setattr, handeln, "entscheide_override",
                        handeln.entscheide_override)
        handeln.entscheide_override = lambda prompt, w: (
            "long", {"aktion": "BUY", "confidence": 80.0, "grund": "stark"})
        # Zustand + Journal in ein temporaeres Verzeichnis legen.
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(setattr, handeln, "ZUSTAND", handeln.ZUSTAND)
        self.addCleanup(setattr, handeln, "JOURNAL", handeln.JOURNAL)
        handeln.ZUSTAND = Path(self.tmp.name) / "zustand.json"
        handeln.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"

    def test_papier_eroeffnet_und_schliesst_position(self):
        # Einstieg: Kurs 10.0, Stop 9.0, Ziel 12.0.
        handeln.marktkurs = lambda inst: 10.0
        z = handeln.lade_zustand()
        vs = [{"inst": "BTC-USDC", "score": 55.0, "einstieg": 10.0,
               "stop": 9.0, "ziel": 12.0, "stop_pct": 10.0, "usd": 60.0,
               "kennzahlen": _kennzahlen()}]
        handelbar = handeln.llm_sieben(vs, self.w)
        handeln.pruefe_einstiege(z, handelbar, self.w, live=False)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(z["positionen"][0]["inst"], "BTC-USDC")
        self.assertIsNone(z["positionen"][0]["kauf_ord_id"])  # Papier, keine Order

        # Ausstieg: Kurs faellt unter den Stop -> Position wird geschlossen.
        handeln.marktkurs = lambda inst: 8.5
        handeln.pruefe_ausstiege(z, live=False)
        self.assertEqual(len(z["positionen"]), 0)

        # Journal enthaelt Kopf + Kauf + Verkauf.
        zeilen = handeln.JOURNAL.read_text("utf-8").strip().splitlines()
        self.assertEqual(len(zeilen), 3)
        self.assertIn("kauf", zeilen[1])
        self.assertIn("verkauf", zeilen[2])

    def test_papier_ohne_llm_kein_einstieg(self):
        # Ohne LLM-Urteil (entscheide -> None) bleibt das Buch leer.
        handeln.entscheide_override = lambda prompt, w: (None, {"fehler": "kein Urteil"})
        handeln.marktkurs = lambda inst: 10.0
        z = handeln.lade_zustand()
        vs = [{"inst": "BTC-USDC", "score": 55.0, "einstieg": 10.0,
               "stop": 9.0, "ziel": 12.0, "stop_pct": 10.0, "usd": 60.0,
               "kennzahlen": _kennzahlen()}]
        handelbar = handeln.llm_sieben(vs, self.w)
        self.assertEqual(len(handelbar), 0)
        handeln.pruefe_einstiege(z, handelbar, self.w, live=False)
        self.assertEqual(len(z["positionen"]), 0)


class TestVorschauSperrgrund(unittest.TestCase):
    """(d) Die Vorschau nennt als Sperrgrund GENAU das Freigabefenster, wenn
    handel_erlaubt + freigabe.erfuellt wahr sind und nur das Fenster fehlt."""

    def setUp(self):
        self.w = _w()
        self.w["handel_erlaubt"] = True
        self.w["freigabe"]["erfuellt"] = True
        self.addCleanup(setattr, handeln, "sitzung_da", handeln.sitzung_da)
        self.addCleanup(setattr, handeln, "zeitfenster_offen",
                        handeln.zeitfenster_offen)
        self.addCleanup(setattr, handeln.okx, "schluessel_vorhanden",
                        handeln.okx.schluessel_vorhanden)
        handeln.sitzung_da = lambda: False
        handeln.zeitfenster_offen = lambda: False
        handeln.okx.schluessel_vorhanden = lambda: True

    def test_nur_freigabefenster_fehlt(self):
        g = handeln.sperren_live(self.w, _s())
        self.assertEqual(len(g), 1)
        self.assertIn("Freigabefenster", g[0])

    def test_zeitfenster_gibt_frei(self):
        handeln.zeitfenster_offen = lambda: True
        g = handeln.sperren_live(self.w, _s())
        self.assertEqual(g, [])

    def test_handel_erlaubt_false_ist_eigener_grund(self):
        self.w["handel_erlaubt"] = False
        g = handeln.sperren_live(self.w, _s())
        self.assertTrue(any("handel_erlaubt" in x for x in g))


if __name__ == "__main__":
    unittest.main()
