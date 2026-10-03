"""Das Guthaben-Tor des Scanners und die Quote als Parameter.

Anlass (02.10.2026, Auftrag Max "OKX Scanner auf USDC stellen, USDT
funktioniert nicht"): zwei getrennte Befunde, die dieser Test beide festhaelt.

1. Die Wachen fragten "USDT" ab, das Konto hat 438 USDC und 0,00 USDT. Die
   Antwort 0,0 sah wie ein leeres Konto aus. okx.guthaben() nimmt die
   abzufragende Waehrung als Parameter; okx.quote() liest sie aus dem
   Instrument, damit kein Instrument eine fremde Waehrung abfragt.

2. Der Scanner hatte gar kein Guthaben-Tor. Nur max_gesamt_usd begrenzte; bei
   442 von 444 USDC gebunden und 1,76 frei lief er in jeden Kandidaten und
   bekam "insufficient balance" von der Boerse.

Die Gegenprobe steckt in JEDEM Test: ohne das Tor, oder mit der alten festen
Waehrung, muss er rot werden.
"""
import importlib.util
import json
import os
import sys
import unittest

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(SPUR)
for _p in (SPUR, HANDEL):          # die Spur ZULETZT einsortieren (PY-TEST-
    if _p not in sys.path:         # FALLE: sonst laedt der Test
        sys.path.insert(0, _p)     # scanner/handeln.py statt des eigenen)
import handeln as h
assert h.__file__.startswith(SPUR), h.__file__


def _modul(name):
    s = importlib.util.spec_from_file_location(
        "scanner_" + name, os.path.join(SPUR, name + ".py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


okx = _modul("okx")


class QuoteTest(unittest.TestCase):
    """Die Binningswaehrung kommt aus dem Instrument, nicht aus einer Konstante."""

    def test_quote_aus_inst(self):
        for inst, q in (("BTC-USDC", "USDC"), ("ZEC-USDC", "USDC"),
                        ("BTC-USDT", "USDT"), ("ETH-EUR", "EUR")):
            self.assertEqual(okx.quote(inst), q, inst)

    def test_quote_ohne_trennzeichen(self):
        self.assertEqual(okx.quote("BTC"), "")
        self.assertEqual(okx.quote(""), "")
        self.assertEqual(okx.quote(None), "")

    def test_quote_ist_keine_feste_waehrung(self):
        # Genau der Fehler, den die Festung verhindert: aus 'BTC-USDT' ein
        # festes USDC machen und dessen Guthaben fuer einen USDT-Kauf lesen.
        self.assertNotEqual(okx.quote("BTC-USDT"), "USDC")
        self.assertNotEqual(okx.quote("ETH-EUR"), "USDC")


class GuthabenTest(unittest.TestCase):
    """guthaben() fragt die GENANNTE Waehrung ab - ohne Netzzugriff."""

    def test_fragt_die_genannte_waehrung_ab(self):
        rufe = []

        def fake(pfad, signiert=False):
            rufe.append((pfad, signiert))
            return [{"details": [{"availBal": "438.2523"}]}]

        alt = okx._mit_wiederholung
        okx._mit_wiederholung = fake
        try:
            wert = okx.guthaben("USDC")
        finally:
            okx._mit_wiederholung = alt
        self.assertAlmostEqual(wert, 438.2523)
        self.assertEqual(len(rufe), 1)
        self.assertIn("ccy=USDC", rufe[0][0])
        self.assertTrue(rufe[0][1], "Guthaben ist ein signierter Abruf")

    def test_unbekannte_waehrung_liefert_null_nicht_leer(self):
        """USDT auf Max' Konto: der Pfad wird gerufen und liefert 0,0.

        Der Unterschied ist der RUF: Code, der gar nicht nach der Waehrung
        fragt oder nach der falschen, kann diesen Test nicht bestehen.
        """
        rufe = []

        def fake(pfad, signiert=False):
            rufe.append(pfad)
            return [{"details": []}]          # OKX: unbekannte ccy -> leer

        alt = okx._mit_wiederholung
        okx._mit_wiederholung = fake
        try:
            self.assertEqual(okx.guthaben("USDT"), 0.0)
        finally:
            okx._mit_wiederholung = alt
        self.assertEqual(rufe, ["/api/v5/account/balance?ccy=USDT"])

    def test_altname_bleibt_und_liest_weiterhin_usdt(self):
        rufe = []

        def fake(pfad, signiert=False):
            rufe.append(pfad)
            return [{"details": [{"availBal": "7.0"}]}]

        alt = okx._mit_wiederholung
        okx._mit_wiederholung = fake
        try:
            self.assertAlmostEqual(okx.guthaben_usdt(), 7.0)
        finally:
            okx._mit_wiederholung = alt
        self.assertIn("ccy=USDT", rufe[0])

    def test_leere_antwort_ist_null(self):
        alt = okx._mit_wiederholung
        okx._mit_wiederholung = lambda p, signiert=False: []
        try:
            self.assertEqual(okx.guthaben("USDC"), 0.0)
        finally:
            okx._mit_wiederholung = alt


def _attrappen(freie, kaeufe):
    """Fake-okx mit einer Guthaben-Tabelle je Waehrung."""
    return type("FakeOKX", (), {
        "quote": staticmethod(okx.quote),
        "letzter_kurs": staticmethod(lambda inst: 100.0),
        "guthaben": staticmethod(lambda ccy: freie.get(ccy, 0.0)),
        "markt_kauf": staticmethod(
            lambda inst, usd: (kaeufe.append((inst, usd)) or "TX")),
        "order_details": staticmethod(lambda inst, oid: {"accFillSz": "1.0"}),
        "stop_setzen": staticmethod(lambda inst, menge, stop: "STOP"),
        "stop_stornieren": staticmethod(lambda oid: oid),
        "stop_details": staticmethod(lambda oid: {"accFillSz": "0"}),
    })()


class GuthabenTorTest(unittest.TestCase):
    """Ohne freies Guthaben der Quote wird nicht gekauft."""

    def setUp(self):
        self.alt = {n: getattr(h, n) for n in
                    ("protokolliere", "protokolliere_kandidat", "journal",
                     "schreibe_zustand", "_spiegeln", "okx")}
        self.zeilen = []
        self.kaeufe = []
        h.protokolliere = self._notiere
        h.protokolliere_kandidat = self._notiere
        h.journal = lambda *a, **k: None
        h.schreibe_zustand = lambda z: None
        h._spiegeln = lambda w: None
        h.okx = _attrappen({"USDC": 1000.0}, self.kaeufe)

    def tearDown(self):
        for n, v in self.alt.items():
            setattr(h, n, v)

    def _notiere(self, *a, **k):
        self.zeilen.append(" ".join(str(x) for x in a))

    @staticmethod
    def _zustand():
        # vollstaendig, weil pruefe_einstiege auch in_abklingzeit und
        # in_zielsperre liest - ein halbes Fixture bricht an KeyError ab und
        # sagt nichts ueber das Tor aus.
        return {"positionen": [], "letzte_stops": {}, "letzte_ziele": {}}

    @staticmethod
    def _vs(n=3, quote="USDC", usd=100.0):
        return [{"inst": "W%d-%s" % (i, quote), "score": 90, "einstieg": 100.0,
                 "stop": 95.0, "stop_pct": 5.0, "ziel": 110.0, "usd": usd}
                for i in range(n)]

    @staticmethod
    def _wachen(**extra):
        w = {"max_offene_positionen": 5, "max_gesamt_usd": 600,
             "abklingzeit_tage": 4, "mindest_score": 60,
             "max_volatilitaet_pa": 2.0, "mindest_chance_risiko": 1.5,
             "risiko_je_position_usd": 6.0, "max_pro_trade_usd": 120,
             "kill_switch_gesamt_usd": 200, "herzschlag_max_minuten": 180,
             "freigabe": {"erfuellt": True}, "drawdown_halbierung_usd": 30.0}
        w.update(extra)
        return w

    def test_ohne_guthaben_wird_nicht_gekauft(self):
        h.okx = _attrappen({"USDC": 1.76}, self.kaeufe)
        h.pruefe_einstiege(self._zustand(), self._vs(),
                           self._wachen(min_guthaben_quote=30.0), live=True)
        self.assertEqual(self.kaeufe, [], "bei 1,76 USDC darf kein Kauf laufen")
        self.assertTrue(any("zu wenig USDC frei" in z for z in self.zeilen),
                        self.zeilen)

    def test_genug_guthaben_wird_gekauft(self):
        h.pruefe_einstiege(self._zustand(), self._vs(n=2),
                           self._wachen(min_guthaben_quote=30.0), live=True)
        self.assertEqual(len(self.kaeufe), 2, self.kaeufe)

    def test_tor_aus_0_ist_aus(self):
        """Alte Regel ohne Tor: der Gesamtdeckel allein begrenzt."""
        h.okx = _attrappen({"USDC": 0.0}, self.kaeufe)
        h.pruefe_einstiege(self._zustand(), self._vs(n=1),
                           self._wachen(min_guthaben_quote=0), live=True)
        self.assertEqual(len(self.kaeufe), 1,
                         "min_guthaben_quote=0 heisst: kein Guthaben-Tor")

    def test_jede_waehrung_hat_ihr_eigenes_guthaben(self):
        """USDC frei, EUR nicht: der EUR-Kandidat wird abgelehnt."""
        h.okx = _attrappen({"USDC": 500.0, "EUR": 2.0}, self.kaeufe)
        vs = [{"inst": "BTC-USDC", "score": 90, "einstieg": 100.0, "stop": 95.0,
               "stop_pct": 5.0, "ziel": 110.0, "usd": 100.0},
              {"inst": "BTC-EUR", "score": 90, "einstieg": 100.0, "stop": 95.0,
               "stop_pct": 5.0, "ziel": 110.0, "usd": 100.0}]
        h.pruefe_einstiege(self._zustand(), vs,
                           self._wachen(min_guthaben_quote=30.0), live=True)
        self.assertEqual([i for i, _ in self.kaeufe], ["BTC-USDC"],
                         "freies USDC ist kein Guthaben fuer einen EUR-Kauf")

    def test_papierlauf_braucht_kein_guthaben(self):
        """Papier rechnet lokal - ein Kontoreiz waere dort ein Fehler."""
        aufrufe = []
        alt = h.okx

        class KeinNetz:
            quote = staticmethod(okx.quote)
            letzter_kurs = staticmethod(lambda inst: 100.0)

            @staticmethod
            def guthaben(ccy):
                aufrufe.append(ccy)
                raise AssertionError("Papierlauf fragt das Konto nicht ab")

        h.okx = KeinNetz
        try:
            h.pruefe_einstiege(self._zustand(), self._vs(n=1),
                               self._wachen(min_guthaben_quote=30.0),
                               live=False)
        finally:
            h.okx = alt
        self.assertEqual(aufrufe, [])


class WachenKonfigurationTest(unittest.TestCase):
    """Die Quote des Handelswegs steht in der Wachen - und nur dort.

    Ein USDT-Paar im Scanner ist ein Wert, den das Konto nicht bezahlen
    kann: Max' OKX-Konto hat 0,00 USDT (gemessen 02.10.2026). Der Test liest
    die echte Datei, damit die Konfiguration nicht zur Doku verhaertet.
    """
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(SPUR, "wachen.json"), encoding="utf-8") as f:
            cls.w = json.load(f)

    def test_universum_ist_reines_usdc(self):
        q = (self.w.get("universum") or {}).get("quotes") or []
        self.assertEqual(q, ["USDC"],
                         "nur USDC hat auf dem Konto Guthaben UND Markt")
        self.assertNotIn("EURC", q,
                         "EURC hat bei OKX null Spotpaare - Waehrung ohne Markt")

    def test_watchlist_ist_ebenfalls_usdc(self):
        for inst in self.w["watchlist"]:
            self.assertTrue(inst.endswith("-USDC"), inst)

    def test_guthabentor_ist_gesetzt(self):
        self.assertGreater(float(self.w.get("min_guthaben_quote") or 0), 0.0,
                           "ohne Schwelle kaempft die Boerse die Orders ab")


if __name__ == "__main__":
    unittest.main()