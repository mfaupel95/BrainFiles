"""Tests: Zielmarkt-Auskunft und Freigabe der Instrument-Ableitung (T-282).

ANLASS, gemessen am 01.10.2026: omniquant lief live (Fenster offen, Margin da),
konnte aber nichts eroeffnen - jedes Zyklus schrieb

    live,fehler,HBAR-USDT,,,...,"Kurs nicht abrufbar: unbekanntes Instrument
    fuer Kraken Futures: 'HBAR-USDT' (bekannt: DOGE-USDT, ETC-USDT, ...)"

Die Kandidaten des weiten Prognose-Berichts (HBAR-USDT, ONDO-USDT) fehlten in
`kraken_perp.PAARE` - obwohl BEIDE am Zielmarkt handelbar sind (PF_HBARUSD,
PF_ONDOUSD, gegen /instruments geprueft). Die Spur war damit live und armlos.

Dieser Test haelt die drei Regeln der Reparatur fest:
  1. Ohne geprueften Markt wird NICHT gehandelt (nie ersatzweise).
  2. Ohne Marktliste wird nicht abgeleitet (nicht nachweisbar = kein Markt).
  3. Ohne ausdrueckliche Freigabe (`live_pf_ableitung`) wird ein abgeleitetes
     Instrument nicht geordert - auch wenn der Markt existiert.

Kein Netz, keine Order: die Marktliste wird per Naht gesetzt, alle
Boersen-Funktionen sind Attrappen.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
while HIER in sys.path:
    sys.path.remove(HIER)
sys.path.insert(0, HIER)          # eigene Spur ZULETZT vorne - nicht scanner/

import kraken_perp as kp                            # noqa: E402
import live_perp as lp                              # noqa: E402

assert kp.__file__.startswith(HIER), "falsches kraken_perp: %s" % kp.__file__

_SPURORDNER = HIER


def _stand():
    aus = {}
    for name in sorted(os.listdir(_SPURORDNER)):
        p = os.path.join(_SPURORDNER, name)
        if os.path.isfile(p):
            aus[name] = os.path.getsize(p)
    return aus


_STAND_VOR = None


def setUpModule():
    global _STAND_VOR
    _STAND_VOR = _stand()


def tearDownModule():
    neu = {k: v for k, v in _stand().items() if _STAND_VOR.get(k) != v}
    assert not neu, "Tests haben in den echten Spurenordner geschrieben: %s" % neu


class ZustandZuruecksetzen(unittest.TestCase):
    """Modulzustand (Marktliste, Freigabe) nach JEDEM Test zuruecksetzen."""

    def setUp(self):
        kp.setze_ableitung(False)
        kp.merke_maerkte(set())

    def tearDown(self):
        kp.setze_ableitung(False)
        kp.merke_maerkte(set())


class AbleitungTest(ZustandZuruecksetzen):
    def test_name_wird_zu_pf_symbol(self):
        self.assertEqual("PF_HBARUSD", kp.ableitung("HBAR-USDT"))
        self.assertEqual("PF_ONDOUSD", kp.ableitung("ondo-usdc"))

    def test_unbrauchbare_namen_ergeben_nichts(self):
        for name in ("HBAR", "FOO-BAR-BAZ", "", None, "A B-USDT", "A/B-USDT"):
            self.assertIsNone(kp.ableitung(name), name)

    def test_eingetragen_kennt_nur_die_gepruefte_tabelle(self):
        self.assertTrue(kp.eingetragen("STRK-USDT"))
        self.assertFalse(kp.eingetragen("HBAR-USDT"))


class AuskunftTest(ZustandZuruecksetzen):
    def test_ohne_marktliste_bleibt_es_bei_unbekannt(self):
        with self.assertRaises(ValueError) as c:
            kp.paar_fuer("HBAR-USDT")
        self.assertIn("unbekanntes Instrument", str(c.exception))
        self.assertIn("Marktliste nicht geladen", str(c.exception))

    def test_markt_fehlt_in_der_liste(self):
        kp.merke_maerkte({"PF_SOLUSD", "PF_XRPUSD"})
        kp.setze_ableitung(True)
        with self.assertRaises(ValueError) as c:
            kp.paar_fuer("HBAR-USDT")
        self.assertIn("gibt es am Zielmarkt nicht", str(c.exception))

    def test_markt_da_aber_nicht_freigegeben(self):
        kp.merke_maerkte({"PF_HBARUSD"})
        with self.assertRaises(ValueError) as c:
            kp.paar_fuer("HBAR-USDT")
        self.assertIn("live_pf_ableitung=false", str(c.exception))
        self.assertIn("PF_HBARUSD", str(c.exception))

    def test_markt_da_und_freigegeben(self):
        kp.merke_maerkte({"PF_HBARUSD"})
        kp.setze_ableitung(True)
        self.assertEqual("PF_HBARUSD", kp.paar_fuer("HBAR-USDT"))

    def test_eingetragene_brauchen_liste_und_freigabe_nicht(self):
        """Der gepruefte Kern bleibt unabhaengig - sonst waere die Tabelle sinnlos."""
        with self.assertRaises(ValueError):
            kp.paar_fuer("HBAR-USDT")            # ohne Liste: abgelehnt
        self.assertEqual("PF_STRKUSD", kp.paar_fuer("STRK-USDT"))
        self.assertEqual("PF_ZECUSD", kp.paar_fuer("ZEC-USDC"))

    def test_kein_markt_bleibt_kein_markt(self):
        kp.merke_maerkte({"PF_HBARUSD"})
        kp.setze_ableitung(True)
        with self.assertRaises(ValueError) as c:
            kp.paar_fuer("MAGIC-USDT")
        self.assertIn("keinen Markt", str(c.exception))

    def test_stop_setzen_umgeht_das_einstiegs_gate(self):
        """T-306-Regel fuer den Nachsatz: eine OFFENE abgeleitete Position
        muss ihren Schutz-Stop nachsetzen koennen, auch wenn der Prozess neu
        gestartet ist und `ABLEITUNG_ERLAUBT` (prozesslokal, nur beim
        Einstieg gesetzt) wieder False ist. Ohne `fuer_ausstieg` wuerde
        `stop_setzen` hier mit 'live_pf_ableitung=false' scheitern - genau
        die SICHERHEITSLUECKE, die omniquant seit 05.10.2026 fuer NEAR-USDC
        jede Viertelstunde meldete."""
        kp.merke_maerkte({"PF_NEARUSD"})
        kp.setze_ableitung(False)          # frischer Prozess: Gate zu
        # paar_fuer ohne Ausstieg scheitert am Gate (Gegenprobe):
        with self.assertRaises(ValueError) as c:
            kp.paar_fuer("NEAR-USDC")
        self.assertIn("live_pf_ableitung=false", str(c.exception))
        # stop_setzen reicht fuer_ausstieg durch und kommt durch:
        self.assertEqual("PF_NEARUSD", kp.paar_fuer("NEAR-USDC", fuer_ausstieg=True))


class BasisUmbenennungTest(ZustandZuruecksetzen):
    """Die Basen, die am Zielmarkt ANDERS heissen (05.10.2026, gemessen).

    ANLASS: Omniquant fuehrt OKX-Namen, Kraken Futures PF_-Namen. Zwei der
    Basen tragen dort einen anderen Namen, und genau daran scheiterte die
    Spur still: `ableitung()` baute `PF_BTCUSD` und `PF_CTUSD`, beide gibt es
    nicht, die Meldung lautete "gibt es am Zielmarkt nicht" - fuer
    Instrumente, die sehr wohl handelbar sind. Ein toter Markt im Haus sieht
    genauso aus wie ein echter Fehlstand.

    GEMESSEN am 05.10.2026 gegen GET /derivatives/api/v3/instruments
    (204 tradeable PF_-Maerkte):
        BTC -> PF_BTCUSD fehlt, PF_XBTUSD steht
        CT  -> PF_CTUSD fehlt, PF_CTSIUSD steht
        XMSTR und MAGIC: kein PF_-Markt ueberhaupt

    Diese Tests fragen die EIGENSCHAFT (ein in PAARE stehender Name loest
    ohne Marktliste und ohne Tor auf), nicht die eben eingetragene
    Konstante - sonst waere der Test bei jeder Erweiterung rot.
    """

    def test_btc_loest_auf_xbt_auf(self):
        self.assertEqual("PF_XBTUSD", kp.paar_fuer("BTC-USDC"))
        self.assertEqual("PF_XBTUSD", kp.paar_fuer("BTC-USDT"))

    def test_ct_loest_auf_ctsi_auf(self):
        self.assertEqual("PF_CTSIUSD", kp.paar_fuer("CT-USDC"))
        self.assertEqual("PF_CTSIUSD", kp.paar_fuer("CT-USDT"))

    def test_basis_trägt_beide_quote_arten(self):
        """Eine Basis, beide Quotes - der Zielmarkt hat nur eine (USD)."""
        for inst in ("BTC-USDC", "BTC-USDT", "CT-USDC", "CT-USDT"):
            self.assertTrue(kp.eingetragen(inst), inst)
            self.assertTrue(kp.paar_fuer(inst).startswith("PF_"), inst)

    def test_magier_und_xmstr_bleiben_laut_papier(self):
        kp.merke_maerkte({"PF_XBTUSD"})
        kp.setze_ableitung(True)
        for inst in ("MAGIC-USDT", "MAGIC-USDC", "XMSTR-USDT", "XMSTR-USDC"):
            with self.assertRaises(ValueError) as c:
                kp.paar_fuer(inst)
            self.assertIn("keinen Markt", str(c.exception), inst)
        self.assertEqual({"MAGIC-USDC", "MAGIC-USDT", "XMSTR-USDC",
                          "XMSTR-USDT"}, set(kp.KEIN_MARKT))

    def test_abgeleitete_basis_stoesst_nicht_zurueck(self):
        """Ein eingetragenes Instrument braucht weder Liste noch Freigabe."""
        for inst in ("BTC-USDC", "CT-USDT"):
            kp.merke_maerkte(set())
            kp.setze_ableitung(False)
            self.assertEqual("PF_XBTUSD" if inst.startswith("BTC")
                             else "PF_CTSIUSD", kp.paar_fuer(inst))

    def test_geprueft_gegen_die_echte_marktliste(self):
        """Der Kern des Tests: keine Konstante, sondern die BOERSE.

        `merke_maerkte` nimmt eine Attrappe an - hier ist sie die Liste, die
        der Messlauf am 05.10.2026 von /instruments geholt hat. Ein Eintrag,
        der dort nicht steht, ist FALSCH, egal wie plausibel er aussieht.
        """
        GEMESSEN = {"PF_STRKUSD", "PF_DOGEUSD", "PF_XRPUSD", "PF_WUSD",
                    "PF_FILUSD", "PF_ETCUSD", "PF_WLDUSD", "PF_ZECUSD",
                    "PF_ORDIUSD", "PF_XBTUSD", "PF_CTSIUSD"}
        fehlend = {i: s for i, s in kp.PAARE.items() if s not in GEMESSEN}
        self.assertEqual({}, fehlend,
                         "PAARE-Eintrag nicht in der gemessenen Marktliste: %s"
                         % fehlend)

    def test_aus_der_messung_entfernte_maerkte_benennen_ihren_grund(self):
        """XMSTR/MAGIC: kein Markt. Der Fehler muss das sagen, nicht 'unbekannt'."""
        for inst in ("XMSTR-USDT", "MAGIC-USDT"):
            with self.assertRaises(ValueError) as c:
                kp.paar_fuer(inst)
            self.assertIn("Kraken Futures fuehrt keinen Markt", str(c.exception))
            self.assertIn("05.10.2026", str(c.exception))


class _HandelnAttrappe:
    """Nur was `live_perp.kaufe` anfasst - keine echte Buchhaltung."""

    def __init__(self):
        self.zeilen = []

    def _jetzt(self):
        return "2026-10-01T22:00:00+00:00"

    def _heute(self):
        return "2026-10-01"

    def journal(self, **felder):
        self.zeilen.append(felder)


class KaufeTorTest(ZustandZuruecksetzen):
    """`kaufe` ist der EINZIGE Ort, an dem diese Spur Geld ausgibt."""

    W = {"live_einsatz_usd": 50, "hebel": 6, "live_max_gesamt_usd": 50,
         "live_max_offene_positionen": 1, "mindest_guthaben_usd": 31}

    KAND = {"inst": "HBAR-USDT", "stop": 0.090693, "ziel": 0.13101,
            "score": 67.0, "cr": 2.26}

    def test_ohne_freigabe_keine_order(self):
        h = _HandelnAttrappe()
        with patch.object(kp, "markt_kauf") as kauf, \
                patch.object(kp, "letzter_kurs") as kurs:
            p = lp.kaufe(h, dict(self.W, live_pf_ableitung=False), {}, self.KAND)
        self.assertIsNone(p)
        kauf.assert_not_called()
        kurs.assert_not_called()                 # gar nicht erst gefragt
        self.assertEqual(h.zeilen[0]["grund"], "live_pf_ableitung=false")
        self.assertEqual(h.zeilen[0]["inst"], "HBAR-USDT")

    def test_mit_freigabe_geht_es_weiter(self):
        """Gegenprobe: das Tor ist die Freigabe, nicht der Name.

        Der Lauf kommt bis zum Kurs - der hier absichtlich scheitert, damit
        NICHTS geordert wird. Vorher (ohne Freigabe) wurde nicht einmal gefragt.
        """
        h = _HandelnAttrappe()
        with patch.object(kp, "lade_maerkte", return_value=204), \
                patch.object(kp, "letzter_kurs",
                             side_effect=ValueError("kein Kurs (Test)")), \
                patch.object(kp, "markt_kauf") as kauf:
            p = lp.kaufe(h, dict(self.W, live_pf_ableitung=True), {}, self.KAND)
        self.assertIsNone(p)
        kauf.assert_not_called()
        self.assertIn("Kurs nicht abrufbar", h.zeilen[0]["grund"])

    def test_eingetragenes_instrument_umgeht_das_tor(self):
        """XRP steht in der geprueften Tabelle - kein Flag noetig."""
        h = _HandelnAttrappe()
        with patch.object(kp, "lade_maerkte") as laden, \
                patch.object(kp, "letzter_kurs",
                             side_effect=ValueError("kein Kurs (Test)")):
            lp.kaufe(h, dict(self.W), {}, {"inst": "XRP-USDC", "stop": 1.4,
                                           "ziel": 1.7})
        laden.assert_not_called()                # keine Netzfrage noetig
        self.assertIn("Kurs nicht abrufbar", h.zeilen[0]["grund"])


if __name__ == "__main__":
    unittest.main()