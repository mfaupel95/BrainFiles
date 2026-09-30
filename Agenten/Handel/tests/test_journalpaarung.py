#!/usr/bin/env python3
"""Die Zuordnung Einstieg/Ausstieg - die Regel, nicht der Tagesstand (T-095).

Der Anlass ist eine stille Verlustquelle: die Auswertungen paarten je
Instrument, zwei gleichzeitige Positionen im selben Instrument ueberschrieben
einander. Im Backtest ueber 5,7 Jahre (squeeze) standen 1092 Einstiegen und
1088 Ausstiegen nur 759 ausgewertete Runden gegenueber.

Geprueft wird die REGEL in vier Stufen - und dass eine Zeile ohne Partner
ausgewiesen statt still verworfen wird. Kein Netz, keine echten Journale.
"""

import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import journalpaarung as jp                                          # noqa: E402


def zeile(aktion, inst, **rest):
    r = {"aktion": aktion, "inst": inst}
    r.update({k: str(v) for k, v in rest.items()})
    return r


class Stufe1KennungTest(unittest.TestCase):
    """Der Normalfall ab 30.09.2026: die Ausstiegszeile traegt ihre Kennung."""

    def test_kennung_entscheidet_auch_bei_zwei_gleichzeitigen_positionen(self):
        # Beide Positionen im selben Instrument - die alte Paarung nahm die
        # erste und verlor die zweite.
        z = [zeile("kauf", "BTC", pos_id="A", stop="100"),
             zeile("kauf", "BTC", pos_id="B", stop="200"),
             zeile("verkauf", "BTC", pos_id="B", stop="200"),
             zeile("verkauf", "BTC", pos_id="A", stop="100")]
        p = jp.Paarung()
        paare = p.zuordnen(z)
        self.assertEqual(2, len(paare))
        # Die Reihenfolge der Paare folgt den AUSSTIEGSzeilen - hier zaehlt
        # nur, WER mit WEM gepaart wurde.
        self.assertEqual([("A", "A"), ("B", "B")],
                         sorted((jp.kennung(e), jp.kennung(a)) for e, a in paare))
        self.assertEqual(0, p.unpaarig)
        self.assertEqual(0, p.offen)

    def test_die_reihenfolge_der_zeilen_entscheidet_nichts(self):
        # Der Ausstieg von B steht VOR dem Ausstieg von A - die Kennung macht
        # die Zuordnung unabhaengig von der Reihenfolge.
        z = [zeile("kauf", "BTC", pos_id="A"), zeile("kauf", "BTC", pos_id="B"),
             zeile("verkauf", "BTC", pos_id="B"), zeile("verkauf", "BTC", pos_id="A")]
        paare = jp.Paarung().zuordnen(z)
        # Die Reihenfolge der Paare folgt den AUSSTIEGSzeilen - hier zaehlt
        # nur, WER mit WEM gepaart wurde.
        self.assertEqual([("A", "A"), ("B", "B")],
                         sorted((jp.kennung(e), jp.kennung(a)) for e, a in paare))

    def test_ausstieg_ohne_passenden_einstieg_ist_unpaarig(self):
        z = [zeile("kauf", "BTC", pos_id="A"), zeile("verkauf", "BTC", pos_id="Z")]
        p = jp.Paarung()
        self.assertEqual([], p.zuordnen(z))
        self.assertEqual(1, p.unpaarig)
        self.assertEqual(1, p.offen)


class Stufe2EindeutigTest(unittest.TestCase):
    """Altjournal ohne Kennung, genau EIN offener Einstieg: eindeutig."""

    def test_ein_offener_einstieg_wird_gepaart(self):
        z = [zeile("eroeffnen", "ETH"), zeile("schliessen", "ETH")]
        p = jp.Paarung()
        self.assertEqual(1, len(p.zuordnen(z)))
        self.assertEqual(1, p.ohne_kennung)     # als Altbestand erkannt
        self.assertEqual(0, p.unpaarig)

    def test_zwei_instrumente_stoeren_sich_nicht(self):
        z = [zeile("eroeffnen", "ETH"), zeile("eroeffnen", "BTC"),
             zeile("schliessen", "BTC"), zeile("schliessen", "ETH")]
        paare = jp.Paarung().zuordnen(z)
        self.assertEqual([("BTC", "BTC"), ("ETH", "ETH")],
                         sorted((e["inst"], a["inst"]) for e, a in paare))


class Stufe3MerkmaleTest(unittest.TestCase):
    """Mehrere offene, aber genau EINE passt zur Kopie der Position."""

    def test_stop_und_ziel_trennen_zwei_gleichzeitige_positionen(self):
        # Genau der Fall, der im Backtest 330 Runden gekostet hat: zwei
        # gleichzeitige Positionen im selben Instrument, Ausstieg ohne Kennung.
        z = [zeile("kauf", "BTC", stop="100", ziel="120"),
             zeile("kauf", "BTC", stop="200", ziel="260"),
             zeile("verkauf", "BTC", stop="200", ziel="260"),
             zeile("verkauf", "BTC", stop="100", ziel="120")]
        p = jp.Paarung()
        paare = p.zuordnen(z)
        self.assertEqual(2, len(paare))
        self.assertEqual(["100", "200"], sorted(e["stop"] for e, a in paare))
        self.assertEqual(0, p.unpaarig)
        self.assertEqual(0, p.ohne_partner_alt)

    def test_die_kontraktzahl_trennt_ebenso(self):
        # xperps Journal fuehrt Stop und Ziel nicht in der Ausstiegszeile, aber
        # die Kontraktzahl - sie ist der Beleg.
        z = [zeile("eroeffnen", "CL-USDT-SWAP", kontrakte="3"),
             zeile("eroeffnen", "CL-USDT-SWAP", kontrakte="9"),
             zeile("schliessen", "CL-USDT-SWAP", kontrakte="9"),
             zeile("schliessen", "CL-USDT-SWAP", kontrakte="3")]
        p = jp.Paarung()
        paare = p.zuordnen(z)
        self.assertEqual(["3", "9"], sorted(e["kontrakte"] for e, a in paare))

    def test_zahl_gegen_zahl_25_ist_25_0(self):
        # Ein Kontraktstand wird je nach Spur "25" oder "25.0" geschrieben.
        self.assertTrue(jp.passt(jp.merkmale_standard({"kontrakte": "25"}),
                                 jp.merkmale_standard({"kontrakte": "25.0"})))

    def test_ohne_gemeinsames_merkmal_kein_beleg(self):
        # Kein Merkmal auf beiden Seiten -> nicht raten.
        self.assertFalse(jp.passt(jp.merkmale_standard({"stop": "100"}),
                                  jp.merkmale_standard({"grund": "ziel"})))

    def test_ein_abweichendes_merkmal_zerstoert_den_beleg(self):
        self.assertFalse(jp.passt(jp.merkmale_standard({"stop": "100", "ziel": "120"}),
                                  jp.merkmale_standard({"stop": "100", "ziel": "121"})))

    def test_nominal_und_margin_sind_kein_merkmal(self):
        # Sie werden beim Ausstieg neu gerechnet - als Beleg waeren sie falsch.
        self.assertNotIn("nominal", jp.MERKMAL_FELDER)
        self.assertNotIn("margin", jp.MERKMAL_FELDER)
        self.assertNotIn("einsatz_usd", jp.MERKMAL_FELDER)

    def test_mehrere_gleichartige_positionen_werden_nicht_geraten(self):
        # Zwei Positionen mit denselben Grenzen: die Zeile ist zweideutig und
        # wird als solche gezaehlt - NICHT nach Warteschlange zugeordnet.
        z = [zeile("kauf", "BTC", stop="100", ziel="120"),
             zeile("kauf", "BTC", stop="100", ziel="120"),
             zeile("verkauf", "BTC", stop="100", ziel="120")]
        p = jp.Paarung()
        self.assertEqual([], p.zuordnen(z))
        self.assertEqual(1, p.unpaarig)
        self.assertEqual(1, p.ohne_partner_alt)
        self.assertEqual(2, p.offen)


class AusweisenTest(unittest.TestCase):
    """Was fehlt, wird gesagt - nicht verschwiegen."""

    def test_ausstieg_ohne_instrument_wird_gezaehlt(self):
        p = jp.Paarung()
        p.zuordnen([{"aktion": "verkauf", "inst": ""}])
        self.assertEqual(1, p.ausstiege_ohne_inst)

    def test_stand_nennt_alle_fuenf_zahlen(self):
        s = jp.Paarung().stand()
        self.assertEqual({"unpaarig", "offen", "ohne_kennung", "zweideutig",
                          "ohne_instrument"}, set(s))

    def test_keine_zeile_verschwindet(self):
        # Jede Einstiegszeile ist entweder gepaart oder offen, jede
        # Ausstiegszeile gepaart, unpaarig oder ohne Instrument.
        z = [zeile("kauf", "BTC", pos_id="A", stop="1"),
             zeile("kauf", "BTC", stop="2"),
             zeile("kauf", "BTC", stop="2"),
             zeile("verkauf", "BTC", pos_id="A", stop="1"),
             zeile("verkauf", "BTC", stop="2"),
             zeile("verkauf", "BTC", stop="9"),
             {"aktion": "verkauf", "inst": ""}]
        p = jp.Paarung()
        paare = p.zuordnen(z)
        einstiege = sum(1 for r in z if r["aktion"] == "kauf")
        ausstiege = sum(1 for r in z if r["aktion"] == "verkauf")
        self.assertEqual(einstiege, len(paare) + p.offen)
        self.assertEqual(ausstiege, len(paare) + p.unpaarig + p.ausstiege_ohne_inst)


class AktionsnamenTest(unittest.TestCase):
    """Zwei Vokabulare im Haus - beide muessen erkannt werden."""

    def test_eroeffnen_schliessen_und_kauf_verkauf(self):
        for ein, aus in (("eroeffnen", "schliessen"), ("kauf", "verkauf")):
            p = jp.Paarung()
            self.assertEqual(1, len(p.zuordnen([zeile(ein, "BTC"),
                                                zeile(aus, "BTC")])),
                             "%s/%s nicht erkannt" % (ein, aus))

    def test_funding_und_zyklus_sind_kein_handel(self):
        p = jp.Paarung()
        p.zuordnen([zeile("kauf", "BTC"), zeile("funding", "BTC"),
                    zeile("zyklus", "BTC"), zeile("quotes", "BTC")])
        self.assertEqual(1, p.offen)
        self.assertEqual(0, p.unpaarig)

    def test_schluesselfeld_paar_und_token(self):
        # kraken fuehrt "paar", kopier "token".
        p = jp.Paarung()
        self.assertEqual(1, len(p.zuordnen([{"aktion": "kauf", "paar": "SOLEUR"},
                                            {"aktion": "verkauf", "paar": "SOLEUR"}])))
        self.assertEqual(1, len(p.zuordnen([{"aktion": "kauf", "token": "ABC"},
                                            {"aktion": "verkauf", "token": "ABC"}])))


class EinlesenTest(unittest.TestCase):
    """`zeilen()` liest ein Journal oder liefert leer - nie einen Fehler."""

    def test_fehlende_datei_ist_leer(self):
        self.assertEqual([], jp.zeilen(os.path.join(HIER, "gibt-es-nicht.csv")))

    def test_kennung_und_zahl_lesen(self):
        self.assertEqual("A", jp.kennung({"pos_id": " A "}))
        self.assertEqual("", jp.kennung({}))
        self.assertEqual(3.0, jp.zahl({"x": "3"}, "x"))
        self.assertIsNone(jp.zahl({"x": ""}, "x"))
        self.assertIsNone(jp.zahl({}, "x"))


class GegenprobeTest(unittest.TestCase):
    """Die ALTE Paarung gegen die neue - dieselben Zeilen, nur die Regel wechselt.

    Die alte Regel stand bis zum 30.09.2026 in `kosten_wendepunkt.py` und
    `auswertung_alle.py`: ein Dict `offen[inst]`. Sie ist hier als Referenz
    nachgebaut, damit der Unterschied MESSBAR bleibt und nicht nur behauptet.
    Ohne diesen Test koennte die neue Fassung still wieder zur alten werden.
    """

    ZEILEN = [
        {"aktion": "kauf", "inst": "BTC-USDT", "preis": "100",
         "stop": "95", "ziel": "110", "pos_id": "A"},
        {"aktion": "kauf", "inst": "BTC-USDT", "preis": "101",
         "stop": "96", "ziel": "111", "pos_id": "B"},
        {"aktion": "verkauf", "inst": "BTC-USDT", "preis": "110", "pos_id": "B"},
        {"aktion": "verkauf", "inst": "BTC-USDT", "preis": "95", "pos_id": "A"},
    ]

    @staticmethod
    def alt(zeilen):
        """Die alte Regel je Instrument: offen[inst] - gibt die Rundenzahl."""
        offen, runden = {}, 0
        for r in zeilen:
            akt = (r.get("aktion") or "").strip()
            inst = (r.get("inst") or "").strip()
            if akt in jp.EINSTIEG:
                offen[inst] = r
            elif akt in jp.AUSSTIEG and inst in offen:
                offen.pop(inst)
                runden += 1
        return runden

    def test_zwei_gleichzeitige_positionen_alt_eins_neu_zwei(self):
        p = jp.Paarung()
        neu = len(list(p.zuordnen(self.ZEILEN)))
        self.assertEqual(1, self.alt(self.ZEILEN))       # der Verlust von T-095
        self.assertEqual(2, neu)                          # je Position eine Runde

    def test_ohne_kennung_und_zwei_offenen_wird_nicht_geraten(self):
        # Altbestand ohne Kennung, zwei gleichzeitige Positionen: die alte Regel
        # hat eine davon beliebig zugeordnet (geraten), die neue paart keine und
        # ZAEHLT die Zweideutigkeit.
        zeilen = [dict(r) for r in self.ZEILEN]
        for r in zeilen:
            r.pop("pos_id")
        self.assertEqual(1, self.alt(zeilen))              # geraten
        p = jp.Paarung()
        self.assertEqual(0, len(list(p.zuordnen(zeilen))))  # nicht geraten
        self.assertEqual(2, p.ohne_partner_alt)


if __name__ == "__main__":
    unittest.main()