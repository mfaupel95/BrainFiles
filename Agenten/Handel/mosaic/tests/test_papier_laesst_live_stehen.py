"""Ein Papierlauf darf eine ECHTE Position nicht aus dem Buch werfen.

Befund 23.09.2026 (echt passiert): das Freigabefenster lief um 19:29 ab, der
Zyklus 19:33:43 lief deshalb PAPIER - und dieser Papierzweig buchte die echte
BTC-Position (modus=live, an der Boerse mit Stop offen) mit grund=ziel aus dem
Buch. Das Buch war flach, die Boerse hielt 0.00066027 XXBT weiter.

Geprueft wird:
 (a) pruefe_ausstiege verkauft eine LIVE-Position NICHT (weder am Ziel noch am
     Stop) und laesst sie im Buch;
 (b) daneben liegende PAPIER-Positionen werden weiter verkauft;
 (c) nur_papier_verwerfen (Kill-Pfad des Papierzweigs) raeumt nur Papier;
 (d) die Zahl der stehen gelassenen Live-Positionen wird EINMAL gezaehlt und
     EINMAL gemeldet (Zaehler je Instrument, Meldung im Aufrufer).

Kein Netz, kein echtes Ziel: Journal und Zustand zeigen auf ein
Temp-Verzeichnis, ein Modulwaechter vergleicht danach den echten Spurenordner.

Lauf (aus mosaic/tests):
 ..\\..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_papier_laesst_live_stehen -v
"""

import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln  # noqa: E402


# --- Modulwaechter: kein Test darf in den echten Spurenordner schreiben ----

def _ordner_stand():
    out = {}
    for name in ("zustand.json", "zustand.mittel.json",
                 "handelsjournal.csv", "handelsjournal.mittel.csv"):
        p = os.path.join(HIER, name)
        out[name] = os.path.getsize(p) if os.path.exists(p) else None
    return out


def setUpModule():
    global _vorher
    _vorher = _ordner_stand()


def tearDownModule():
    nach = _ordner_stand()
    geaendert = [k for k in nach if nach[k] != _vorher.get(k)]
    assert not geaendert, ("Test hat in den ECHTEN Spurenordner geschrieben: %s"
                           % geaendert)


def _kerzen(kurs):
    """Eine 5M-Kerze mit dem gewuenschten Schlusskurs (Index 4 = Schluss)."""
    return [[1, kurs, kurs, kurs, kurs, 1.0]]


def _live(inst="BTC-USDC", einstieg=100.0, stop=90.0, ziel=110.0):
    return {"inst": inst, "seite": "long", "einstieg": einstieg, "stop": stop,
            "ziel": ziel, "stop_pct": 5.0, "nominal": 50.0, "menge": 0.00066,
            "modus": "live", "kauf_ord_id": "X", "stop_algo_id": "A",
            "boersen_stop_fehlt": False, "eroeffnet_zeit": "2026-09-23T01:08:20+00:00"}


def _papier(inst="ETH-USDT", einstieg=100.0, stop=90.0, ziel=110.0):
    return {"inst": inst, "seite": "long", "einstieg": einstieg, "stop": stop,
            "ziel": ziel, "stop_pct": 5.0, "nominal": 100.0,
            "eroeffnet_zeit": "2026-09-17T07:08:46+00:00"}


class PapierLaesstLiveStehenTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self._saved = (handeln.ZUSTAND, handeln.JOURNAL)
        handeln.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        handeln.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")

    def tearDown(self):
        handeln.ZUSTAND, handeln.JOURNAL = self._saved
        self._tmp.cleanup()

    def _journal(self):
        """Datenzeilen des Journals (ohne Kopfzeile)."""
        if not os.path.exists(handeln.JOURNAL):
            return []
        with open(handeln.JOURNAL, encoding="utf-8") as f:
            zeilen = [z for z in f.read().splitlines() if z.strip()]
        return [z for z in zeilen if "zeit,modus,aktion" not in z]

    # (a) Ziel erreicht: Live bleibt, Papier geht
    def test_live_position_am_ziel_bleibt_stehen(self):
        z = {"positionen": [_live()]}
        handeln.pruefe_ausstiege(z, _kerzen(120.0), {}, nur="BTC-USDC")
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(z["positionen"][0]["modus"], "live")
        self.assertEqual(self._journal(), [])

    # (a) Stop gerissen: Live bleibt ebenfalls
    def test_live_position_am_stop_bleibt_stehen(self):
        z = {"positionen": [_live()]}
        handeln.pruefe_ausstiege(z, _kerzen(80.0), {}, nur="BTC-USDC")
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(self._journal(), [])

    # (b) Die Papier-Position daneben wird weiter verkauft
    def test_papier_position_wird_weiter_verkauft(self):
        z = {"positionen": [_live(), _papier()]}
        handeln.pruefe_ausstiege(z, _kerzen(120.0), {}, nur="ETH-USDT")
        namen = [p["inst"] for p in z["positionen"]]
        self.assertEqual(namen, ["BTC-USDC"])
        self.assertEqual(len(self._journal()), 1)
        self.assertIn(",papier,verkauf,ETH-USDT,", self._journal()[0])

    # (c) Kill-Pfad des Papierzweigs
    def test_nur_papier_verwerfen_laesst_live_stehen(self):
        z = {"positionen": [_live(), _papier()]}
        handeln.nur_papier_verwerfen(z)
        self.assertEqual([p["inst"] for p in z["positionen"]], ["BTC-USDC"])

    # (d) Der Zaehler darf nicht dreifach zaehlen (Befund Zyklus 21, 25.09.2026:
    #     ein Zyklus meldete dieselbe Live-Position dreimal, weil lauf() je
    #     Instrument einmal ueber ALLE Positionen prueft).
    def test_live_position_zaehlt_nur_einmal(self):
        z = {"positionen": [_live(), _live("ETH-USDC"), _live("SOL-USDC")]}
        self.assertEqual(handeln.pruefe_ausstiege(
            z, _kerzen(120.0), {}, nur="BTC-USDC"), 1)
        self.assertEqual(len(z["positionen"]), 3)
        self.assertEqual(self._journal(), [])

    def test_ohne_einschraenkung_zaehlt_alle_live(self):
        z = {"positionen": [_live(), _live("ETH-USDC"), _live("SOL-USDC")]}
        self.assertEqual(handeln.pruefe_ausstiege(
            z, _kerzen(120.0), {}, nur=None), 3)

    def test_meldet_nichts_selbst(self):
        """Die Zeile schreibt der Aufrufer - sonst steht sie je Instrument da."""
        import io
        from contextlib import redirect_stdout
        z = {"positionen": [_live(), _live("ETH-USDC")]}
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            handeln.pruefe_ausstiege(z, _kerzen(120.0), {}, nur="BTC-USDC")
        self.assertEqual(puffer.getvalue().strip(), "")

    # Gegenprobe: ein leeres Buch bleibt leer (kein KeyError)
    def test_leeres_buch(self):
        z = {}
        handeln.nur_papier_verwerfen(z)
        self.assertEqual(z["positionen"], [])


if __name__ == "__main__":
    unittest.main()