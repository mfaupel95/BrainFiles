"""Tests fuer die Moon-Dev-Sniper-Spur - ohne Netz, ohne den Bot.

Die Spur holt neue Solana-Launches ueber die oeffentliche Pump.fun-API. Im
Test wird diese Quelle durch ein Lambda ersetzt (`quelle_override`), damit
kein Test an einer lebenden Boerse haengt.

Was hier belegt wird:
  * das Regel-Gate (jung / nicht gebannt / Marktwert im Band / Preis vorhanden),
  * dass nur Kandidaten in `daten` landen und gehaltene Mints einen Kurs behalten,
  * Einstieg, Stop, Ziel und Nominal in Prozent,
  * Ausstieg an Stop und Ziel mit G/V auf den NOMINALWERT,
  * dass --vorschau nichts schreibt.

Tests schreiben nie in den ECHTEN Spurenordner: SCHREIBEN=False beim direkten
Buch-Code und ein Modulwaechter, der jede Abweichung nach draussen faengt.
"""

import json
import os
import sys
import tempfile
import unittest
import urllib.error

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
# Reihenfolge: zuletzt eingefuegt = vorne. SPUR MUSS vorne stehen, sonst
# gewinnt scanner/handeln.py gegen das handeln.py dieser Spur.
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as h  # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py geladen: %s" % h.__file__


def _bestand(ordner):
    """Dateien (Name, Groesse) eines Ordners - ohne Zwischenspeicher."""
    aus = {}
    for name in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, name)
        if os.path.isfile(p) and not name.endswith((".pyc", ".pyo")):
            aus[name] = os.path.getsize(p)
    return aus


_ECHT_VORHER = None


def setUpModule():
    """Vor dem ersten Test: den echten Spurenordner merken."""
    global _ECHT_VORHER
    _ECHT_VORHER = _bestand(SPUR)


def tearDownModule():
    nachher = _bestand(SPUR)
    assert nachher == _ECHT_VORHER, (
        "Ein Test hat in den echten Spurenordner geschrieben!\nvorher: %s\n"
        "nachher: %s" % (_ECHT_VORHER, nachher))


WACHEN = {
    "waehrung": "USD",
    "handel_erlaubt": False,
    "risiko_je_position_usd": 5.0,
    "max_offene_positionen": 3,
    "max_pro_trade_usd": 100.0,
    "max_gesamt_usd": 300.0,
    "kill_switch_gesamt_usd": 45.0,
    "stop_prozent": 8.0,
    "pflicht_stop_prozent_min": 5.0,
    "pflicht_stop_prozent_max": 12.0,
    "ziel_r_vielfaches": 2.0,
    "max_alter_minuten": 60.0,
    "marktkap_band_usd": [200.0, 100000.0],
    "abruf_grenze": 40,
}


def token(mint="AAA", mk=1000.0, alter_min=10.0, preis=1e-5, banned=False,
          nsfw=False):
    # Zwei Felder sind noetig: quelle() rechnet das Alter selbst aus
    # created_timestamp, signal() liest das vorberechnete alter_minuten.
    augenblick = __import__("time").time() * 1000.0
    return {
        "mint": mint, "symbol": mint, "name": mint,
        "created_timestamp": augenblick - alter_min * 60000.0,
        "alter_minuten": alter_min,
        "market_cap_usd": mk, "real_sol_reserves": 1.0,
        "is_banned": banned, "nsfw": nsfw, "complete": False,
        "kurs": preis,
    }


def _abbruch(mint, *a, **k):
    """Steht fuer einen abgerissenen Kursabruf (WinError 10054)."""
    raise urllib.error.URLError(ConnectionResetError(10054, "reset"))


class SignalTest(unittest.TestCase):
    def test_junger_launch_mit_wert_ist_long(self):
        self.assertEqual(h.signal(token(), dict(WACHEN)), "long")

    def test_zu_alt_kein_signal(self):
        w = dict(WACHEN)
        w["max_alter_minuten"] = 5.0
        self.assertIsNone(h.signal(token(alter_min=60.0), w))

    def test_ohne_alter_kein_signal(self):
        t = token()
        t["alter_minuten"] = None
        self.assertIsNone(h.signal(t, dict(WACHEN)))

    def test_marktwert_ausserhalb_kein_signal(self):
        w = dict(WACHEN)
        self.assertIsNone(h.signal(token(mk=1.0), w))            # zu niedrig
        self.assertIsNone(h.signal(token(mk=1_000_000.0), w))    # zu hoch

    def test_kein_preis_kein_signal(self):
        self.assertIsNone(h.signal(token(preis=None), dict(WACHEN)))

    def test_ohne_mint_kein_signal(self):
        t = token()
        t["mint"] = None
        self.assertIsNone(h.signal(t, dict(WACHEN)))


class QuelleTest(unittest.TestCase):
    """quelle() filtert und versorgt gehaltene Positionen mit Kursen."""

    def setUp(self):
        self.alt = None
        self.alt_wachen = None

    def _quelle(self, roh, wachen=None):
        w = dict(WACHEN)
        if wachen:
            w.update(wachen)
        # pump_neue_token und pump_letzter_preis patchen.
        urspr_t = h.daten.pump_neue_token
        urspr_p = h.daten.pump_letzter_preis
        h.daten.pump_neue_token = lambda s=40: roh
        preise = {}
        for c in roh:
            preise[c.get("mint")] = c.get("kurs")
        h.daten.pump_letzter_preis = lambda m: preise.get(m)
        try:
            return h.quelle(w)
        finally:
            h.daten.pump_neue_token = urspr_t
            h.daten.pump_letzter_preis = urspr_p

    def test_kandidaten_nur_erlaubte(self):
        roh = [
            token("A", mk=1000.0, alter_min=5.0),          # ok
            token("B", mk=1000.0, alter_min=5.0, banned=True),
            token("C", mk=1000.0, alter_min=5.0, nsfw=True),
            token("D", mk=1.0, alter_min=5.0),             # Marktwert zu niedrig
            token("E", mk=1000.0, alter_min=999.0),        # zu alt
            token("F", mk=1000.0, alter_min=5.0, preis=None),  # kein Preis
        ]
        daten, kurse, fehler = self._quelle(roh)
        self.assertEqual(fehler, [])
        self.assertEqual(sorted(daten.keys()), ["A"])
        self.assertEqual(kurse.get("A"), 1e-5)

    def test_gehaltene_position_behaelt_kurs(self):
        roh = [token("A", mk=1000.0, alter_min=5.0)]
        # Position auf ein Nicht-Kandidaten-Mint: dessen Preis muss trotzdem
        # geliefert werden, damit Stop/Ziel laufen.
        alt_lade = h.buch.lade_zustand
        h.buch.lade_zustand = lambda _p: {"positionen": [
            {"inst": "ALT", "seite": "long", "einstieg": 1e-5,
             "stop": 0.9e-5, "ziel": 1.2e-5, "stop_pct": 8.0,
             "nominal": 100.0}]}
        urspr_t = h.daten.pump_neue_token
        urspr_p = h.daten.pump_letzter_preis
        h.daten.pump_neue_token = lambda s=40: roh
        # Preis-Provider: "A" ist ein Kandidat aus roh, "ALT" die gehaltene
        # Position, die NICHT in der Neuesten-Liste steht.
        h.daten.pump_letzter_preis = lambda m: {"A": 1e-5, "ALT": 2e-5}.get(m)
        try:
            daten, kurse, fehler = h.quelle(dict(WACHEN))
        finally:
            h.buch.lade_zustand = alt_lade
            h.daten.pump_neue_token = urspr_t
            h.daten.pump_letzter_preis = urspr_p
        self.assertEqual(fehler, [])
        self.assertEqual(sorted(daten.keys()), ["A"])
        self.assertEqual(kurse.get("ALT"), 2e-5)   # gehaltene Position bekam Kurs

    def test_fehler_werden_gemeldet(self):
        urspr_t = h.daten.pump_neue_token
        h.daten.pump_neue_token = lambda s=40: (_ for _ in ()).throw(
            RuntimeError("Boerse weg"))
        try:
            daten, kurse, fehler = h.quelle(dict(WACHEN))
        finally:
            h.daten.pump_neue_token = urspr_t
        self.assertEqual((daten, kurse), ({}, {}))
        self.assertEqual(len(fehler), 1)


class BuchTest(unittest.TestCase):
    """Einstieg/Ausstieg ueber den gemeinsamen Kern auf einem Temp-Zustand."""

    def setUp(self):
        self.z = {"positionen": []}
        self.alt_schreiben = h.buch.SCHREIBEN
        h.buch.SCHREIBEN = False

    def tearDown(self):
        h.buch.SCHREIBEN = self.alt_schreiben

    def _daten(self):
        return {"AAA": token(mint="AAA", mk=1000.0, alter_min=5.0)}

    def test_langer_einstieg_mit_stop_ziel_nominal(self):
        daten = self._daten()
        inst = "AAA"
        # signal() plus spur_buch.einstieg wie im Zyklus.
        seite = h.signal(daten[inst], dict(WACHEN))
        self.assertEqual(seite, "long")
        p = h.buch.einstieg(self.z, inst, seite, daten[inst]["kurs"],
                            dict(WACHEN), 1.0, "moondev_sniper", None,
                            journal_pfad="unbenutzt.csv")
        self.assertIsNotNone(p)
        self.assertEqual(p["seite"], "long")
        # stop 8% unter Einstieg, ziel 2R (=16% nominal davon entfernt).
        self.assertAlmostEqual(p["stop"], 1e-5 * 0.92, places=10)
        self.assertAlmostEqual(p["ziel"], 1e-5 * 1.16, places=10)

    def test_long_stop_und_gv_auf_dem_nominal(self):
        p = {"inst": "AAA", "seite": "short", "einstieg": 1e-5,
             "stop": 1.08e-5, "ziel": 0.84e-5, "stop_pct": 8.0,
             "nominal": 100.0, "eroeffnet_zeit": "2026-01-01T00:00:00+00:00"}
        z = {"positionen": [p]}
        h.buch.pruefe_ausstiege(z, {"AAA": 1.08e-5}, dict(WACHEN),
                                "unbenutzt.csv")
        self.assertEqual(z["positionen"], [])


class DateienTest(unittest.TestCase):
    """Die Spur schreibt in ihre eigenen Dateien - und nur dort."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = h.quelle_override
        # Voruebergehend einen temp jar; das echte Buch patchen wir NICHT -
        # wir pruefen den vollen zyklus-Pfad auf einen temp-Wurzelordner.
        self.orig_buch_zyklus = h.buch.zyklus
        self.aufrufe = []

        def zyklus_ersatz(ordner, quelle, signal, modus, ereignis_name):
            self.aufrufe.append((ordner, modus, ereignis_name))
            return 0
        h.buch.zyklus = zyklus_ersatz

    def tearDown(self):
        h.quelle_override = self.alt
        h.buch.zyklus = self.orig_buch_zyklus
        self.tmp.cleanup()

    def test_main_ruft_kern_mit_eigenem_namen(self):
        # main() mit --wachen aufrufen; der Kern wird ersetzt, damit kein
        # echter Zyklus startet.
        sys.argv = ["handeln.py", "--wachen"]
        rc = h.main()
        self.assertEqual(rc, 0)
        (ordner, modus, nama) = self.aufrufe[0]
        self.assertEqual(ordner, SPUR)
        self.assertEqual(modus, "wachen")
        self.assertEqual(nama, "handel/moondev_sniper")

    def test_live_verweigert(self):
        sys.argv = ["handeln.py", "--live"]
        self.assertEqual(h.main(), 0)
        self.assertEqual(self.aufrufe, [])
        # Bus-Ereignis darf bei --live nicht entstehen.


class NetzabbruchTest(unittest.TestCase):
    """Ein Verbindungsabbruch beim Kursabruf darf den Zyklus nicht kippen.

    Befund 22.09.2026: `pump_letzter_preis` fing nur HTTP 429. Ein Abbruch der
    Verbindung (WinError 10054) flog durch `quelle()` bis in den Dauerlauf und
    machte aus einem Zyklus eine Rueckgabe 1 - dreimal an einem Tag, jedes Mal
    eine Bus-Meldung. Ein Netzfehler ist kein Fehler der Spur.
    """

    def test_kursausfall_wird_gemeldet_statt_geworfen(self):
        urspr_t = h.daten.pump_neue_token
        urspr_p = h.daten.pump_letzter_preis
        urspr_l = h.buch.lade_zustand
        h.daten.pump_neue_token = lambda s=40: [token("A", mk=1000.0, alter_min=5.0)]
        h.daten.pump_letzter_preis = _abbruch
        h.buch.lade_zustand = lambda _p: {"positionen": []}
        try:
            daten, kurse, fehler = h.quelle(dict(WACHEN))
        finally:
            h.daten.pump_neue_token = urspr_t
            h.daten.pump_letzter_preis = urspr_p
            h.buch.lade_zustand = urspr_l
        self.assertEqual((daten, kurse), ({}, {}))
        self.assertEqual(len(fehler), 1)
        self.assertIn("10054", fehler[0])

    def test_gehaltene_position_ueberlebt_den_kursausfall(self):
        urspr_t = h.daten.pump_neue_token
        urspr_p = h.daten.pump_letzter_preis
        urspr_l = h.buch.lade_zustand
        h.daten.pump_neue_token = lambda s=40: []
        h.daten.pump_letzter_preis = _abbruch
        h.buch.lade_zustand = lambda _p: {"positionen": [
            {"inst": "ALT", "seite": "long", "einstieg": 1e-5, "stop": 0.9e-5,
             "ziel": 1.2e-5, "stop_pct": 8.0, "nominal": 100.0}]}
        try:
            daten, kurse, fehler = h.quelle(dict(WACHEN))
        finally:
            h.daten.pump_neue_token = urspr_t
            h.daten.pump_letzter_preis = urspr_p
            h.buch.lade_zustand = urspr_l
        self.assertEqual((daten, kurse), ({}, {}))
        self.assertEqual(len(fehler), 1)


class ZyklusBeiNetzabbruchTest(unittest.TestCase):
    """Der ganze Papierlauf gegen einen Temp-Ordner - mit abgerissener Leitung.

    Das ist der Beweis, der zaehlt: der Zyklus endet mit 0, statt den
    Dauerlauf mit einer Rueckgabe 1 und einer Bus-Meldung zu beschweren.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt_schreiben = h.buch.SCHREIBEN
        h.buch.SCHREIBEN = True
        w = dict(WACHEN)
        w["journal_zweitziel"] = os.path.join(self.tmp.name, "zweitziel")
        w["grund"] = "test"
        with open(os.path.join(self.tmp.name, "wachen.json"), "w",
                  encoding="utf-8") as f:
            json.dump(w, f)
        self.alt_t = h.daten.pump_neue_token
        self.alt_p = h.daten.pump_letzter_preis
        h.daten.pump_neue_token = lambda s=40: [token("AAA", mk=1000.0, alter_min=5.0)]

    def tearDown(self):
        h.daten.pump_neue_token = self.alt_t
        h.daten.pump_letzter_preis = self.alt_p
        h.buch.SCHREIBEN = self.alt_schreiben
        self.tmp.cleanup()

    def _lauf(self):
        return h.buch.zyklus(self.tmp.name, h.daten_holen, h.signal, "papier",
                             "handel/moondev_sniper")

    def test_abbruch_ergibt_rueckgabe_null(self):
        h.daten.pump_letzter_preis = _abbruch
        self.assertEqual(self._lauf(), 0)

    def test_gesunde_leitung_bucht_weiter(self):
        h.daten.pump_letzter_preis = lambda m: 1e-5
        self.assertEqual(self._lauf(), 0)
        with open(os.path.join(self.tmp.name, "handelsjournal.csv"),
                  encoding="utf-8") as f:
            self.assertIn("AAA", f.read())


if __name__ == "__main__":
    unittest.main(verbosity=2)