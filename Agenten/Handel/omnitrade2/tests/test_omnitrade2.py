"""Tests fuer die omnitrade2-Spur - ohne Netz, ohne laufenden Rust-Prozess.

Die Spur liest Statusdateien und spiegelt deren Position. Beides wird im Test
ersetzt:
  * `lesen.lebt_override` - die Prozessabfrage (tasklist) ist im Test ein
    Lambda, sonst haengt jeder Test an einer echten PID,
  * `handeln.lage_override` - die Statusdateien kommen aus einem Temp-Ordner,
  * der Buch-Zyklus laeuft in einem TEMP-Spurenordner (spur_buch leitet
    Wachen, Zustand und Journal aus dem uebergebenen Ordner ab).

Ein Modulwaechter (setUpModule/tearDownModule) vergleicht die Dateiliste des
ECHTEN Spurenordners vor und nach der Suite: ein Test, der dort hineinschreibt,
faellt auf, statt als Handelsrunde im echten Journal zu landen.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
# Reihenfolge: zuletzt eingefuegt = vorne. SPUR MUSS vorne stehen, sonst
# gewinnt scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    while p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

import handeln as h      # noqa: E402
import lesen as l        # noqa: E402
import spur_buch as buch  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py geladen: %s" % h.__file__
assert l.__file__.startswith(SPUR), "falsches lesen.py geladen: %s" % l.__file__


def _bestand(ordner):
    aus = {}
    for name in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, name)
        if os.path.isfile(p):
            aus[name] = os.path.getsize(p)
    return aus


_ECHT_VORHER = None


def setUpModule():
    global _ECHT_VORHER
    _ECHT_VORHER = _bestand(SPUR)


def tearDownModule():
    nachher = _bestand(SPUR)
    assert nachher == _ECHT_VORHER, (
        "Test hat im echten Spurenordner geschrieben: %s" % (
            set(nachher) - set(_ECHT_VORHER) or
            {k for k in nachher if nachher[k] != _ECHT_VORHER.get(k)}))


class TestOrdner(unittest.TestCase):
    """Der Statusordner: Standard und Umgebungsvariable."""

    def test_standard_ordner(self):
        """Standard ist Werkstatt/omnitrade2/status (relativ zu BrainFiles)."""
        # Die Umgebungsvariable muss nicht gesetzt sein - dann gilt Standard.
        os.environ.pop("OMNITRADE2_STATUS_ORDNER", None)
        ordner = l.ordner()
        self.assertTrue(ordner.endswith(os.path.join("Werkstatt", "omnitrade2", "status")),
                        "Standard-Ordner falsch: %s" % ordner)

    def test_umgebungsvariable(self):
        """OMNITRADE2_STATUS_ORDNER gewinnt ueber den Standard."""
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["OMNITRADE2_STATUS_ORDNER"] = tmp
            try:
                self.assertEqual(l.ordner(), os.path.normpath(tmp))
            finally:
                os.environ.pop("OMNITRADE2_STATUS_ORDNER", None)

    def test_ordner_ist_normpath(self):
        """Der Ordner ist normpath'd (kein .., kein Doppel-Slash)."""
        ordner = l.ordner()
        self.assertEqual(ordner, os.path.normpath(ordner))


class TestDateien(unittest.TestCase):
    """Statusdateien finden: leere Liste bei fehlendem Ordner."""

    def test_fehlender_ordner(self):
        """Ein fehlender Ordner ergibt eine leere Liste, nie einen Fehler."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "gibts_nicht")
            self.assertEqual(l.dateien(pfad), [])

    def test_leerer_ordner(self):
        """Ein leerer Ordner ergibt eine leere Liste."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(l.dateien(tmp), [])

    def test_live_dateien(self):
        """Namen mit 'live' und '.json' werden gefunden, andere nicht."""
        with tempfile.TemporaryDirectory() as tmp:
            for n in ("live.json", "live_BTCUSDC.json", "live_abc.json"):
                with open(os.path.join(tmp, n), "w") as f:
                    f.write("{}")
            with open(os.path.join(tmp, "other.json"), "w") as f:
                f.write("{}")
            with open(os.path.join(tmp, "live.txt"), "w") as f:
                f.write("{}")
            dateien = l.dateien(tmp)
            self.assertEqual(len(dateien), 3)
            self.assertTrue(all(os.path.basename(d).startswith("live") for d in dateien))
            self.assertTrue(all(d.endswith(".json") for d in dateien))

    def test_einzelne_datei(self):
        """OMNITRADE2_STATUS kann eine einzelne Datei sein."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "live.json")
            with open(pfad, "w") as f:
                f.write("{}")
            self.assertEqual(l.dateien(pfad), [pfad])


class TestInstrument(unittest.TestCase):
    """Symbol-Zerlegung: bekannte und unbekannte Symbole."""

    def test_bekannte_symbole(self):
        self.assertEqual(l.instrument("BTCUSDC"), "BTC-USDC")
        self.assertEqual(l.instrument("ETHUSDC"), "ETH-USDC")
        self.assertEqual(l.instrument("SOLUSDT"), "SOL-USDT")

    def test_unbekannte_symbole(self):
        """Ein unbekanntes Symbol wird generisch zerlegt, wenn moeglich."""
        self.assertEqual(l.instrument("XRPUSDC"), "XRP-USDC")
        self.assertEqual(l.instrument("DOGEUSDT"), "DOGE-USDT")

    def test_nicht_zerlegbar(self):
        """Ein Symbol ohne bekannte Quote ergibt None."""
        self.assertIsNone(l.instrument(""))
        self.assertIsNone(l.instrument("BTC"))
        self.assertIsNone(l.instrument("USDC"))


class TestLauf(unittest.TestCase):
    """Eine Statusdatei lesen: ok, offen, laeuft."""

    def _statusdatei(self, ordner, name="live.json", **felder):
        """Eine minimale Statusdatei schreiben (Schema 1)."""
        daten = {
            "schema": 1,
            "state": "running",
            "symbol": "BTCUSDC",
            "net_quantity": 0.05,
            "last_close": 65000.0,
            "last_signal": "long",
            "pid": 12345,
            "updated_ms": 0,  # wird gesetzt
            "recent_candles": [],
            "recent_orders": [],
            "orders_placed": 1,
            "orders_rejected": 0,
            "last_error": "",
            "script": "test.omni",
        }
        daten.update(felder)
        pfad = os.path.join(ordner, name)
        with open(pfad, "w") as f:
            json.dump(daten, f)
        return pfad

    def test_lesbarer_lauf(self):
        """Ein lesbarer Lauf mit net_quantity > 0 ist offen."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._statusdatei(tmp, updated_ms=0)
            jetzt = 0  # nicht veraltet
            e = l.lauf(pfad, jetzt_ms=jetzt, prozess_pruefen=False)
            self.assertTrue(e["ok"])
            self.assertTrue(e["offen"])
            self.assertEqual(e["inst"], "BTC-USDC")
            self.assertEqual(e["netto"], 0.05)
            self.assertEqual(e["kurs"], 65000.0)

    def test_leere_position(self):
        """net_quantity = 0 ist nicht offen."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._statusdatei(tmp, net_quantity=0.0, updated_ms=0)
            e = l.lauf(pfad, jetzt_ms=0, prozess_pruefen=False)
            self.assertTrue(e["ok"])
            self.assertFalse(e["offen"])

    def test_falsches_schema(self):
        """Ein falsches Schema wird abgelehnt."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._statusdatei(tmp, schema=99, updated_ms=0)
            e = l.lauf(pfad, jetzt_ms=0, prozess_pruefen=False)
            self.assertFalse(e["ok"])
            self.assertIn("Schema", e["fehler"])

    def test_unbekanntes_symbol(self):
        """Ein unbekanntes Symbol wird abgelehnt."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._statusdatei(tmp, symbol="UNKNOWN", updated_ms=0)
            e = l.lauf(pfad, jetzt_ms=0, prozess_pruefen=False)
            self.assertFalse(e["ok"])
            self.assertIn("Symbol", e["fehler"])

    def test_pid_pruefung_ohne_prozess(self):
        """Ohne Prozesspruefung gilt state=running als laeuft."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._statusdatei(tmp, updated_ms=0)
            e = l.lauf(pfad, jetzt_ms=0, prozess_pruefen=False)
            self.assertTrue(e["laeuft"])

    def test_pid_pruefung_mit_override(self):
        """Mit lebt_override wird die PID-Pruefung ersetzt."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._statusdatei(tmp, updated_ms=0)
            l.lebt_override = lambda pid: True
            try:
                e = l.lauf(pfad, jetzt_ms=0, prozess_pruefen=True)
                self.assertTrue(e["laeuft"])
            finally:
                l.lebt_override = None

    def test_verkauf_letzter_preis(self):
        """Der letzte Verkaufspreis wird aus recent_orders gelesen."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = self._statusdatei(tmp, updated_ms=0, recent_orders=[
                {"side": "buy", "outcome": "filled", "time_ms": 1000, "price": 64000.0},
                {"side": "sell", "outcome": "filled", "time_ms": 2000, "price": 66000.0},
            ])
            e = l.lauf(pfad, jetzt_ms=0, prozess_pruefen=False)
            self.assertEqual(e["verkauf"], 66000.0)


class TestLage(unittest.TestCase):
    """Alle Laeufe lesen: Liste und Fehler."""

    def test_leere_liste(self):
        """Ohne Statusdateien gibt es eine leere Liste und keinen Fehler."""
        with tempfile.TemporaryDirectory() as tmp:
            laeufe, fehler = l.lage(tmp, prozess_pruefen=False)
            self.assertEqual(laeufe, [])
            self.assertEqual(fehler, [])

    def test_mit_fehlern(self):
        """Fehler werden als Textzeilen gemeldet."""
        with tempfile.TemporaryDirectory() as tmp:
            # Eine kaputte Datei
            with open(os.path.join(tmp, "live_broken.json"), "w") as f:
                f.write("kein json")
            laeufe, fehler = l.lage(tmp, prozess_pruefen=False)
            self.assertEqual(laeufe, [])
            self.assertTrue(len(fehler) > 0)


class TestSignal(unittest.TestCase):
    """Die Signal-Logik: long nur bei laufendem Lauf und offener Position."""

    def test_signal_long(self):
        d = {"laeuft": True, "offen": True}
        self.assertEqual(h.signal(d, {}), "long")

    def test_signal_kein_lauf(self):
        d = {"laeuft": False, "offen": True}
        self.assertIsNone(h.signal(d, {}))

    def test_signal_keine_position(self):
        d = {"laeuft": True, "offen": False}
        self.assertIsNone(h.signal(d, {}))

    def test_signal_kein_short(self):
        """Es gibt kein short - omnitrade2 handelt nur long."""
        d = {"laeuft": True, "offen": True}
        self.assertNotEqual(h.signal(d, {}), "short")


class TestAusstieg(unittest.TestCase):
    """Die Ausstiegslogik: omnitrade2 flat bei beendetem Lauf."""

    def test_ausstieg_flat(self):
        """Ein gestoppter Lauf ohne Position loest 'omnitrade2 flat' aus."""
        h.lage_override = lambda: ([{
            "ok": True, "inst": "BTC-USDC", "state": "stopped",
            "offen": False, "netto": 0.0, "laeuft": False,
            "datei": "live.json", "fehler": "",
        }], [])
        try:
            grund = h.ausstieg_grund({"inst": "BTC-USDC"}, {})
            self.assertEqual(grund, "omnitrade2 flat")
        finally:
            h.lage_override = None

    def test_kein_ausstieg_bei_leerem_lauf(self):
        """Ohne Laeufe gibt es keinen Ausstieg."""
        h.lage_override = lambda: ([], [])
        try:
            grund = h.ausstieg_grund({"inst": "BTC-USDC"}, {})
            self.assertIsNone(grund)
        finally:
            h.lage_override = None

    def test_kein_ausstieg_bei_offener_position(self):
        """Ein laufender Lauf mit Position loest keinen Ausstieg aus."""
        h.lage_override = lambda: ([{
            "ok": True, "inst": "BTC-USDC", "state": "running",
            "offen": True, "netto": 0.05, "laeuft": True,
            "datei": "live.json", "fehler": "",
        }], [])
        try:
            grund = h.ausstieg_grund({"inst": "BTC-USDC"}, {})
            self.assertIsNone(grund)
        finally:
            h.lage_override = None


class TestQuelle(unittest.TestCase):
    """Die quelle()-Funktion: Instrumente mit Kurs und Positionsstand."""

    def test_quelle_leer(self):
        """Ohne Laeufe gibt es keine Instrumente."""
        h.lage_override = lambda: ([], [])
        try:
            aus, kurse, fehler = h.quelle({})
            self.assertEqual(aus, {})
            self.assertEqual(kurse, {})
        finally:
            h.lage_override = None

    def test_quelle_mit_lauf(self):
        """Ein Lauf wird als Instrument aufgenommen."""
        h.lage_override = lambda: ([{
            "ok": True, "inst": "BTC-USDC", "state": "running",
            "offen": True, "netto": 0.05, "laeuft": True,
            "kurs": 65000.0, "signal": "long", "script": "test.omni",
            "datei": "live.json", "alter_s": 10.0, "fehler": "",
            "verkauf": None,
        }], [])
        try:
            aus, kurse, fehler = h.quelle({})
            self.assertIn("BTC-USDC", aus)
            self.assertEqual(kurse["BTC-USDC"], 65000.0)
            self.assertTrue(aus["BTC-USDC"]["laeuft"])
            self.assertTrue(aus["BTC-USDC"]["offen"])
        finally:
            h.lage_override = None


class TestWachen(unittest.TestCase):
    """Die wachen.json: Tore und Zahlen."""

    def test_wachen_json_lesbar(self):
        """Die wachen.json ist lesbar und traegt die Pflichtfelder."""
        pfad = os.path.join(SPUR, "wachen.json")
        with open(pfad, "r", encoding="utf-8") as f:
            w = json.load(f)
        self.assertIn("handel_erlaubt", w)
        self.assertIn("risiko_je_position_usd", w)
        self.assertIn("max_offene_positionen", w)
        self.assertIn("stop_prozent", w)
        self.assertIn("ziel_r_vielfaches", w)
        self.assertIn("journal_zweitziel", w)

    def test_handel_erlaubt_false(self):
        """handel_erlaubt ist false - die Spur ist neu."""
        pfad = os.path.join(SPUR, "wachen.json")
        with open(pfad, "r", encoding="utf-8") as f:
            w = json.load(f)
        self.assertFalse(w["handel_erlaubt"])

    def test_journal_zweitziel(self):
        """Die Spiegelung zeigt nach Q:\\Handel_Journal\\omnitrade2."""
        pfad = os.path.join(SPUR, "wachen.json")
        with open(pfad, "r", encoding="utf-8") as f:
            w = json.load(f)
        self.assertEqual(w["journal_zweitziel"], "Q:\\Handel_Journal\\omnitrade2")


if __name__ == "__main__":
    unittest.main()
