"""Der XPERP-Zwilling muss die Zwischenlagerung der Rangliste ueberleben.

Anlass (25.09.2026): `handeln.py` holte den Zwilling (den auf diesem EEA-Konto
allein handelbaren Kontrakt) in `kandidaten.sammle()` - und warf ihn beim
Zwischenlagern weg: `rangliste()` schrieb nur die schlanken Kennzahlen nach
`zustand.json`. Jeder Zyklus innerhalb der zwei Stunden Gueltigkeit fiel damit
in `anlauf()` auf den gewoehnlichen Perpetual zurueck (`XAU-USDT-SWAP`,
`META-USDT-SWAP`) - und OKX antwortet darauf mit 50124 "does not have trading
permission for the market". Der Fix vom Vormittag wirkte so nur auf den ersten
Lauf; die Vorschau zeigte weiter die Reihennamen.

Ohne Netz: `kandidaten.sammle` und jeder Boersenzugriff sind Attrappen.
"""

import os
import sys
import unittest
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
# Die eigene Spur MUSS vorn stehen - `python -m` setzt das Arbeitsverzeichnis
# in sys.path, ein reines `if p not in sys.path: insert(0, p)` laesst die Spur
# dann hinten liegen und der Import holt scanner/handeln.py.
for p in (os.path.join(SPUR, os.pardir, "scanner"), os.path.dirname(SPUR),
          SPUR):
    while p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

import handeln as h                                            # noqa: E402
import kandidaten                                              # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln: %s" % h.__file__

ZWILLING = {"instId": "XAU-USD_UM_XPERP-310502", "ruleType": "xperp",
            "state": "live", "instCategory": "4", "lever": "50",
            "ctVal": "0.1", "tickSz": "0.01"}


def rohe_zeile(mit_zwilling=True):
    """Eine Zeile in der Form, die `kandidaten.sammle()` liefert."""
    # mae 0,10 heisst Hebel-Deckel ~9,9 - die Reihe besteht die Tore, damit
    # ein Ausfall in den Tests unten NICHT an den Toren liegt, sondern am
    # fehlenden Zwilling.
    z = {"basis": "XAU", "instId": "XAU-USDT-SWAP", "kategorie": "rohstoff",
         "punkte": {"long": 63.5, "short": 32.9}, "vola": 0.4, "vola_tor": 0.6,
         "umsatz": 10_700_000.0, "ruhe": 0.0, "mae_long": 0.10,
         "mae_short": 0.12}
    if mit_zwilling:
        z["handels_instId"] = ZWILLING["instId"]
        z["handels_instr"] = dict(ZWILLING)
        z["max_lever"] = 50.0
    return z


class RanglisteBehaeltDenZwilling(unittest.TestCase):

    def setUp(self):
        self.sammle = kandidaten.sammle
        self.aufrufe = []

    def tearDown(self):
        kandidaten.sammle = self.sammle

    def _sammle_attrappe(self, *a, **k):
        self.aufrufe.append(1)
        return [rohe_zeile()]

    def test_zwischengelagerte_zeile_traegt_den_zwilling(self):
        kandidaten.sammle = self._sammle_attrappe
        z = {"rangliste": None}
        werte, _ = h.rangliste(z)
        self.assertEqual(1, len(self.aufrufe))
        self.assertTrue(werte[0].get("handels_instr"),
                        "handels_instr fehlt in der Zwischenlagerung")
        self.assertEqual(ZWILLING["instId"], werte[0]["handels_instId"])

    def test_alter_stand_ohne_zwilling_wird_verworfen(self):
        """Ein Stand aus der Zeit vor dem Zwilling darf nicht gelten.

        Sonst liefe er bis zu zwei Stunden weiter, jede Zeile ueber den
        Rueckfall auf den nicht handelbaren Perpetual.
        """
        from datetime import timedelta
        kandidaten.sammle = self._sammle_attrappe
        vor = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(
            timespec="seconds")
        z = {"rangliste": {"zeit": vor, "werte": [
            {"basis": "XAU", "instId": "XAU-USDT-SWAP", "kategorie": "rohstoff",
             "punkte": {"long": 63.5, "short": 32.9}, "vola": 0.4,
             "vola_tor": 0.6, "umsatz": 10_700_000.0,
             "mae_long": 0.4, "mae_short": 0.6}]}}
        werte, _ = h.rangliste(z)
        self.assertEqual(1, len(self.aufrufe), "alter Stand wurde nicht ersetzt")
        self.assertTrue(werte[0].get("handels_instr"))

    def test_frischer_stand_mit_zwilling_wird_nicht_neu_geholt(self):
        kandidaten.sammle = self._sammle_attrappe
        z = {"rangliste": {"zeit": datetime.now(timezone.utc).isoformat(
            timespec="seconds"), "werte": [rohe_zeile()]}}
        werte, alter = h.rangliste(z)
        self.assertEqual([], self.aufrufe, "Stand wurde unnoetig neu geholt")
        self.assertTrue(werte[0].get("handels_instr"))


class KandidatenOhneZwilling(unittest.TestCase):

    WACHEN = {"max_hebel": 5, "min_umsatz_24h_usd": 3_000_000,
              "familien": {"rohstoff": {"aktiv": True,
                                        "umsatz_bezug_usd": 1_000_000,
                                        "vola_tor": 0.6}}}

    def test_reihe_ohne_zwilling_faellt_aus_der_liste(self):
        aus = h.kandidaten_aus([rohe_zeile(mit_zwilling=False)], self.WACHEN)
        self.assertEqual([], aus,
                         "ohne Zwilling darf kein Vorschlag entstehen")

    def test_reihe_mit_zwilling_traegt_ihn_weiter(self):
        """Gegenprobe zum Test darueber: dieselben Zahlen, nur mit Zwilling.

        Ohne diese Gegenprobe waere 'faellt aus der Liste' auch dann gruen,
        wenn die Reihe an einem der Tore scheitert.
        """
        aus = h.kandidaten_aus([rohe_zeile()], self.WACHEN)
        self.assertEqual(2, len(aus), "je Richtung ein Vorschlag erwartet")
        for a in aus:
            self.assertEqual(ZWILLING["instId"], a["handels_instId"])
            self.assertTrue(a["handels_instr"])
            self.assertNotEqual("XAU-USDT-SWAP", a["handels_instId"])


class ZwillingNieDerGewoehnlichePerpetual(unittest.TestCase):

    def setUp(self):
        self.instrument = h.okxf.instrument
        self.gerufen = []

    def tearDown(self):
        h.okxf.instrument = self.instrument
        h._ZWILLINGE = None

    def test_aus_der_zeile(self):
        self.assertEqual(ZWILLING["instId"],
                         h._zwilling({"basis": "XAU", "instId": "XAU-USDT-SWAP",
                                      "handels_instr": dict(ZWILLING)})["instId"])

    def test_nur_die_kennung_loest_ueber_die_kennung_auf(self):
        def attrappe(inst):
            self.gerufen.append(inst)
            return dict(ZWILLING) if inst == ZWILLING["instId"] else None
        h.okxf.instrument = attrappe
        k = h._zwilling({"basis": "XAU", "instId": "XAU-USDT-SWAP",
                         "handels_instId": ZWILLING["instId"]})
        self.assertEqual(ZWILLING["instId"], k["instId"])
        self.assertNotIn("XAU-USDT-SWAP", self.gerufen,
                         "der gewoehnliche Perpetual wurde aufgeloest")

    def test_ohne_zwilling_und_ohne_tabelle_kommt_none(self):
        def attrappe(inst):
            self.gerufen.append(inst)
            return {"instId": inst}          # wuerde JEDEN Namen annehmen
        h.okxf.instrument = attrappe
        h._ZWILLINGE = {}
        k = h._zwilling({"basis": "XAU", "instId": "XAU-USDT-SWAP"})
        self.assertIsNone(k)
        self.assertEqual([], self.gerufen,
                         "ohne Kennung darf kein Instrument aufgeloest werden")


class AnlaufHandeltDenZwilling(unittest.TestCase):
    """Der Kern: die Order geht an den Zwilling, nicht an den Reihennamen."""

    def setUp(self):
        self.alt = {n: getattr(h.okxf, n) for n in ("kerzen", "auf_tick")}
        self.alt_ind = h.indikatoren.lage
        self.alt_groesse = h.bot.groesse
        self.alt_pflicht = h.bot.pruefpflicht
        self.alt_bar = h.bot.BAR
        h.okxf.kerzen = lambda *a, **k: [100.0] * 100
        h.okxf.auf_tick = lambda instr, preis: preis
        h.indikatoren.lage = lambda k, inst=None, **kw: {
            "signal": "long", "atr": 1.0, "kurs": 100.0, "grund": "test"}
        h.bot.BAR = "4H"
        h.bot.groesse = lambda w, instr, einstieg, stop, seite, deckel: {
            "hebel": 5, "kontrakte": 10, "nominal": 100.0, "margin": 20.0,
            "liq": 80.0, "abstand": 0.03}
        h.bot.pruefpflicht = lambda w, instr, k, seite, einstieg, stop, ziel, \
            hebel, still=True: {"traegt": True, "hebel_traegt": True,
                                "liq_abstand": 0.19, "funding_pct": 0.0,
                                "gebuehren_pct": 0.001, "quote_noetig": 0.35,
                                "quote_beobachtet": 0.66, "hebel": 5,
                                "hebel_deckel": 5.9}

    def tearDown(self):
        for n, f in self.alt.items():
            setattr(h.okxf, n, f)
        h.indikatoren.lage = self.alt_ind
        h.bot.groesse = self.alt_groesse
        h.bot.pruefpflicht = self.alt_pflicht
        h.bot.BAR = self.alt_bar
        h._ZWILLINGE = None

    def _wachen(self):
        return {"einstieg_atr_abschlag": 0.25, "stop_atr_faktor": 1.5,
                "ziel_atr_faktor": 3.0, "max_hebel": 5}

    def test_inst_ist_der_zwilling(self):
        a = h.anlauf(self._wachen(), {
            "basis": "XAU", "instId": "XAU-USDT-SWAP", "seite": "long",
            "kategorie": "rohstoff", "punkte": 63.5, "deckel": 5.9,
            "handels_instId": ZWILLING["instId"],
            "handels_instr": dict(ZWILLING)})
        self.assertIsNotNone(a)
        self.assertEqual(ZWILLING["instId"], a["inst"])
        self.assertNotEqual("XAU-USDT-SWAP", a["inst"])

    def test_zeile_aus_altem_stand_holt_den_zwilling_frisch(self):
        h._ZWILLINGE = {"XAU": dict(ZWILLING)}
        a = h.anlauf(self._wachen(), {
            "basis": "XAU", "instId": "XAU-USDT-SWAP", "seite": "long",
            "kategorie": "rohstoff", "punkte": 63.5, "deckel": 5.9})
        self.assertIsNotNone(a)
        self.assertEqual(ZWILLING["instId"], a["inst"])

    def test_ohne_zwilling_kein_anlauf(self):
        h._ZWILLINGE = {}
        a = h.anlauf(self._wachen(), {
            "basis": "NICHTS", "instId": "NICHTS-USDT-SWAP", "seite": "long",
            "kategorie": "rohstoff", "punkte": 63.5, "deckel": 5.9})
        self.assertIsNone(a)


if __name__ == "__main__":
    unittest.main()