"""Tests: Geisterpruefung und Fuellungspruefung in xperp/handeln.py.

ANLASS (21.09.2026, gemeldet von Max): "Spur xperp zeigt 2 Positionen. Live ist
aber nur BZ da." Nachgemessen an der Boerse:

    Book:   HBAR-USD_UM_XPERP-310815, BZ-..., CRCL-...
    Boerse: CRCL (1.1), BZ (208), SUI (1066 - nicht vom Bot)

HBAR war ein GEIST: die Limit-Order lag offen und war nie gefuellt
(accFillSz = 0, state = live), /account/positions kennt das Instrument nicht.
xperp hatte die Position beim ANNEHMEN der Order gebucht, nicht beim Fuellen.

Die Tests schreiben nie in die echten Dateien: `journal` wird ersetzt und
`okxf` gestubbt.
"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(SPUR))
sys.path.insert(0, str(HANDEL))

import handeln as h                                                  # noqa: E402


def _pos(inst, modus="live", zeit=None):
    p = {"inst": inst, "seite": "long", "familie": "krypto", "einstieg": 1.0,
         "nominal": 100.0, "margin": 20.0, "hebel": 5.0, "kontrakte": 10.0,
         "modus": modus}
    if zeit:
        p["eroeffnet_zeit"] = zeit
        p["eroeffnet"] = zeit[:10]
    return p


class Geister(unittest.TestCase):
    def setUp(self):
        self.geschrieben = []
        self.j = patch.object(h, "journal",
                              side_effect=lambda **k: self.geschrieben.append(k))
        self.j.start()
        self.addCleanup(self.j.stop)

    def test_position_ohne_bestand_wird_ausgebucht(self):
        # Handgriff: die Boerse bezeugt die Schliessung (realizedPnl) - nur
        # dann wird eine fehlende Live-Position ausgebucht (Regel Max
        # 09.10.2026: ohne Boersenbeleg bleibt sie als UNKLAR stehen).
        p = _pos("HBAR-100", zeit="2026-09-21T14:06:51+00:00")
        z = {"positionen": [p, _pos("BZ-200")]}
        boerse = [{"instId": "BZ-200", "pos": "208"}]
        satz = {"realizedPnl": "-2.50", "closeTotalPos": "9.4"}
        with patch.object(h.okxf, "positionen", return_value=boerse), \
                patch.object(h.okxf, "geschlossene_position", return_value=satz), \
                patch.object(h.okxf, "order_stornieren") as storno:
            n = h.bueche_geister_aus(z, {})
        storno.assert_not_called()
        self.assertEqual(n, 1)
        self.assertEqual([p["inst"] for p in z["positionen"]], ["BZ-200"])
        self.assertEqual(self.geschrieben[0]["grund"], "buchbereinigung_geist")

    def test_gefuellte_order_bleibt_trotz_fehlender_position(self):
        """Die Wettlaufsituation vom 21.09.2026 (HBAR).

        Beim Pruefen war accFillSz 0, Sekunden spaeter war die Order
        gefuellt. Haette die Pruefung die Position ausgebucht, liefe sie
        ohne Buch weiter - genau das ist an dem Abend passiert.
        """
        p = _pos("HBAR-100"); p["ord_id"] = "3942552192558157824"
        z = {"positionen": [p]}
        with patch.object(h.okxf, "positionen", return_value=[]),                 patch.object(h.okxf, "gefuellte_kontrakte", return_value=9.4),                 patch.object(h.okxf, "order_stornieren") as storno:
            n = h.bueche_geister_aus(z, {})
        self.assertEqual(n, 0, "eine gefuellte Order ist keine Leiche")
        self.assertEqual(len(z["positionen"]), 1)
        storno.assert_not_called()

    def test_offene_order_des_geists_wird_storniert(self):
        # Bleibt die Order liegen, kann sie spaeter fuellen und eine Position
        # ohne Buch erzeugen (genau der HBAR-Fall: state=live, accFillSz=0).
        p = _pos("HBAR-100", zeit="2026-09-21T14:06:51+00:00")
        p["ord_id"] = "3942552192558157824"
        z = {"positionen": [p]}
        satz = {"realizedPnl": "1.50", "closeTotalPos": "9.4"}
        with patch.object(h.okxf, "positionen", return_value=[]), \
                patch.object(h.okxf, "geschlossene_position", return_value=satz), \
                patch.object(h.okxf, "order_stornieren") as storno:
            h.bueche_geister_aus(z, {})
        storno.assert_called_once_with("HBAR-100", "3942552192558157824")

    def test_position_mit_groesse_null_ist_ein_geist(self):
        # OKX behaelt geschlossene Positionen als Zeile mit pos=0 (am 21.09.2026
        # bei ZEC/LINK gesehen) - das ist kein Bestand. Ausgebucht nur mit
        # Boersenbeleg (Regel Max 09.10.2026).
        z = {"positionen": [_pos("ZEC-300", zeit="2026-09-21T14:06:51+00:00")]}
        satz = {"realizedPnl": "3.00", "closeTotalPos": "12.0"}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "ZEC-300", "pos": "0"}]), \
                patch.object(h.okxf, "geschlossene_position", return_value=satz):
            self.assertEqual(h.bueche_geister_aus(z, {}), 1)
        self.assertEqual(z["positionen"], [])

    def test_papierpositionen_werden_nicht_angefasst(self):
        z = {"positionen": [_pos("ALT-1", modus="papier")]}
        with patch.object(h.okxf, "positionen", return_value=[]):
            self.assertEqual(h.bueche_geister_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_netzfehler_laesst_das_buch_in_ruhe(self):
        z = {"positionen": [_pos("HBAR-100"), _pos("BZ-200")]}
        with patch.object(h.okxf, "positionen", side_effect=RuntimeError("kein Netz")):
            self.assertEqual(h.bueche_geister_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 2, "ein Netzfehler darf nichts loeschen")

    def test_echte_position_bleibt(self):
        z = {"positionen": [_pos("CRCL-1")]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "CRCL-1", "pos": "1.1"}]):
            self.assertEqual(h.bueche_geister_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 1)


    def test_alte_position_ohne_boersenbeleg_bleibt_unklar(self):
        """Die Karteileiche OHNE Boersenbeleg (Regel Max 09.10.2026).

        Anlass: am 05.10.2026 hat die neutrale Ausbuchung (Erloes 0.00,
        Einsatz zurueck) sechs ECHTE Live-Positionen aus dem Buch geloescht,
        weil die Boersenabfrage sie kurz nicht zeigte; an der Boerse blieben
        sie offen. Seither gilt: ausgebucht wird NUR mit Boersenbeleg
        (realizedPnl). Fehlt er, bleibt die Position als UNKLAR im Buch -
        eine Karteileiche blockiert hoechstens einen Platz, eine echte
        Position ohne Buch liefe unbewacht weiter.
        """
        p = _pos("BZ-100")
        p.update({"ord_id": "394338698122", "margin": 39.82, "kontrakte": 208.0,
                  "eroeffnet_zeit": "2026-09-21T21:48:29+00:00"})
        z = {"positionen": [p]}
        with patch.object(h.okxf, "positionen", return_value=[]), \
                patch.object(h.okxf, "gefuellte_kontrakte", return_value=208.0), \
                patch.object(h.okxf, "geschlossene_position", return_value=None):
            n = h.bueche_geister_aus(z, {})
        self.assertEqual(n, 0, "ohne Boersenbeleg wird NICHT ausgebucht")
        self.assertEqual([x["inst"] for x in z["positionen"]], ["BZ-100"],
                         "Position bleibt als UNKLAR im Buch stehen")

    def test_frisch_gefuellte_order_bleibt(self):
        # Eroeffnung vor zwei Minuten: der Wettlauf Order->Position gilt weiter.
        frisch = (datetime.now(timezone.utc)
                  - timedelta(minutes=2)).isoformat(timespec="seconds")
        p = _pos("NEU-1"); p.update({"ord_id": "1", "eroeffnet_zeit": frisch})
        z = {"positionen": [p]}
        with patch.object(h.okxf, "positionen", return_value=[]), \
                patch.object(h.okxf, "gefuellte_kontrakte", return_value=9.4):
            self.assertEqual(h.bueche_geister_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_position_ohne_eroeffnungszeit_bleibt_konservativ(self):
        # Unbekanntes Alter: NICHT ausbuchen. Eine echte Position ohne Buch
        # liefe unbewacht - das wiegt schwerer als eine Karteileiche.
        p = _pos("OHNE-ZEIT"); p["ord_id"] = "1"
        z = {"positionen": [p]}
        with patch.object(h.okxf, "positionen", return_value=[]), \
                patch.object(h.okxf, "gefuellte_kontrakte", return_value=9.4):
            self.assertEqual(h.bueche_geister_aus(z, {}), 0)
        self.assertEqual(len(z["positionen"]), 1)


class GeistErgebnis(unittest.TestCase):
    """Das ERGEBNIS einer von Hand geschlossenen Position.

    ANLASS (22.09.2026): Die Geisterpruefung buchte `margin_usd = 0.00`.
    wachen_xperp liest die schliessen-Zeile als ERLoes - eine von Hand
    geschlossene Position zaehlte damit als TOTALVERLUST ihres Einsatzes
    (HBAR: -16.84 USD in der Drawdown-Kurve, aus der der Kill-Switch liest).
    Max schliesst auch kuenftig von Hand, also muss das Ergebnis stimmen.
    """

    def setUp(self):
        self.geschrieben = []
        self.j = patch.object(h, "journal",
                              side_effect=lambda **k: self.geschrieben.append(k))
        self.j.start()
        self.addCleanup(self.j.stop)

    def _p(self, margin=16.84, kontrakte=9.4):
        p = _pos("HBAR-100")
        p.update({"margin": margin, "kontrakte": kontrakte,
                  "eroeffnet_zeit": "2026-09-21T14:06:51+00:00"})
        return p

    def test_boersenergebnis_kommt_ins_buch(self):
        with patch.object(h.okxf, "geschlossene_position",
                          return_value={"realizedPnl": "1.50",
                                        "closeTotalPos": "9.4"}):
            erloes, quelle, anteil = h._geist_erloes(self._p())
        self.assertEqual(quelle, "boerse")
        self.assertAlmostEqual(erloes, 18.34, places=6)
        self.assertAlmostEqual(anteil, 1.0, places=6)

    def test_ohne_boersensatz_wird_neutral_gebucht(self):
        with patch.object(h.okxf, "geschlossene_position", return_value=None):
            erloes, quelle, _ = h._geist_erloes(self._p())
        self.assertEqual(quelle, "neutral")
        self.assertAlmostEqual(erloes, 16.84, places=6,
                               msg="der Einsatz kommt zurueck, kein Verlust")

    def test_netzfehler_wird_neutral(self):
        with patch.object(h.okxf, "geschlossene_position",
                          side_effect=RuntimeError("kein Netz")):
            erloes, quelle, _ = h._geist_erloes(self._p())
        self.assertEqual(quelle, "neutral")
        self.assertAlmostEqual(erloes, 16.84, places=6)

    def test_anteil_bei_groesserer_boersenposition(self):
        """Stand an der Boerse mehr als im Buch, gehoert uns nur unser Anteil."""
        with patch.object(h.okxf, "geschlossene_position",
                          return_value={"realizedPnl": "10.0",
                                        "closeTotalPos": "47.0"}):
            erloes, quelle, anteil = h._geist_erloes(self._p(kontrakte=9.4))
        self.assertEqual(quelle, "boerse")
        self.assertAlmostEqual(anteil, 0.2, places=6)
        self.assertAlmostEqual(erloes, 16.84 + 2.0, places=6)

    def test_ausbuchung_schreibt_das_ergebnis_ins_journal(self):
        z = {"positionen": [self._p()]}
        with patch.object(h.okxf, "positionen", return_value=[]),                 patch.object(h.okxf, "geschlossene_position",
                          return_value={"realizedPnl": "1.50",
                                        "closeTotalPos": "9.4"}):
            h.bueche_geister_aus(z, {})
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.geschrieben[0]["grund"], "buchbereinigung_geist")
        self.assertEqual(self.geschrieben[0]["margin_usd"], "18.34",
                         "0.00 war der Totalverlust - das ist der Bug")

    def test_ohne_boersensatz_keine_ausbuchung(self):
        """Regel Max 09.10.2026: ohne realizedPln-Beleg bleibt die Position.

        Vorher wurde sie NEUTRAL ausgebucht (Einsatz zurueck) - genau dieser
        Weg hat am 05.10.2026 sechs echte Live-Positionen still geloescht.
        """
        z = {"positionen": [self._p()]}
        with patch.object(h.okxf, "positionen", return_value=[]),                 patch.object(h.okxf, "geschlossene_position", return_value=None):
            n = h.bueche_geister_aus(z, {})
        self.assertEqual(n, 0)
        self.assertEqual(len(z["positionen"]), 1, "Position bleibt stehen")
        self.assertEqual(self.geschrieben, [], "keine Journalzeile ohne Beleg")


class Groessenabgleich(unittest.TestCase):
    """Handgriffe an einer offenen Position: das Buch folgt der Boerse.

    Auftrag Max (22.09.2026): "Auch zukuenftig moechte ich noch per Hand
    Positionen veraendern koennen." Gemessen an dem Tag: CL Buch 20 / Boerse 19,
    BZ Buch 208 / Boerse 727, HBAR Buch 9.4 / Boerse 47.1 - geprueft wurde
    bisher nur, ob eine Position ueberhaupt existiert.
    """

    def setUp(self):
        self.geschrieben = []
        self.j = patch.object(h, "journal",
                              side_effect=lambda **k: self.geschrieben.append(k))
        self.j.start()
        self.addCleanup(self.j.stop)

    def _p(self, kontrakte=20.0):
        p = _pos("CL-100")
        p.update({"kontrakte": kontrakte, "nominal": 183.5, "margin": 36.7,
                  "stop": 89.9, "ziel": 99.97, "einstieg": 92.18})
        return p

    def test_teilweise_geschlossen_buch_folgt_der_boerse(self):
        z = {"positionen": [self._p(20.0)]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "CL-100", "pos": "19"}]):
            abw = h.bueche_groessen_abgleichen(z, {})
        self.assertEqual(len(abw), 1)
        self.assertEqual(z["positionen"][0]["kontrakte"], 19.0)
        self.assertAlmostEqual(z["positionen"][0]["nominal"], 183.5 * 19 / 20,
                               places=4)

    def test_handgriff_laesst_stop_und_ziel_unangetastet(self):
        z = {"positionen": [self._p(9.4)]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "CL-100", "pos": "47.1"}]):
            h.bueche_groessen_abgleichen(z, {})
        p = z["positionen"][0]
        self.assertEqual(p["kontrakte"], 47.1)
        self.assertEqual(p["stop"], 89.9, "Handelsentscheidung bleibt die der Spur")
        self.assertEqual(p["ziel"], 99.97)
        self.assertEqual(p["einstieg"], 92.18)

    def test_aufstocken_wird_uebernommen(self):
        z = {"positionen": [self._p(9.4)]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "CL-100", "pos": "47.1"}]):
            h.bueche_groessen_abgleichen(z, {})
        self.assertEqual(z["positionen"][0]["kontrakte"], 47.1)
        self.assertEqual(self.geschrieben[0]["aktion"], "anpassen")
        self.assertEqual(self.geschrieben[0]["grund"], "handanpassung")

    def test_gleiche_groesse_bleibt_unberuehrt(self):
        z = {"positionen": [self._p(19.0)]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "CL-100", "pos": "19"}]):
            self.assertEqual(h.bueche_groessen_abgleichen(z, {}), [])
        self.assertEqual(self.geschrieben, [])

    def test_api_rauschen_ist_kein_handgriff(self):
        z = {"positionen": [self._p(19.0)]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "CL-100", "pos": "19.0000001"}]):
            self.assertEqual(h.bueche_groessen_abgleichen(z, {}), [])

    def test_netzfehler_laesst_das_buch_in_ruhe(self):
        z = {"positionen": [self._p(20.0)]}
        with patch.object(h.okxf, "positionen", side_effect=RuntimeError("kein Netz")):
            self.assertEqual(h.bueche_groessen_abgleichen(z, {}), [])
        self.assertEqual(z["positionen"][0]["kontrakte"], 20.0)

    def test_fehlende_position_ist_nicht_meine_aufgabe(self):
        # Eine ganz verschwundene Position bucht die Geisterpruefung aus.
        z = {"positionen": [self._p(20.0)]}
        with patch.object(h.okxf, "positionen", return_value=[]):
            self.assertEqual(h.bueche_groessen_abgleichen(z, {}), [])
        self.assertEqual(z["positionen"][0]["kontrakte"], 20.0)

    def test_papierposition_bleibt_unberuehrt(self):
        p = self._p(20.0); p["modus"] = "papier"
        z = {"positionen": [p]}
        with patch.object(h.okxf, "positionen",
                          return_value=[{"instId": "CL-100", "pos": "19"}]):
            self.assertEqual(h.bueche_groessen_abgleichen(z, {}), [])
        self.assertEqual(z["positionen"][0]["kontrakte"], 20.0)


class Fuellung(unittest.TestCase):
    def test_nicht_gefuellte_order_ergibt_null(self):
        with patch.object(h.okxf, "gefuellte_kontrakte", return_value=0.0):
            self.assertEqual(h._warten_auf_fuellung("X", "1", 10, versuche=1), 0.0)

    def test_gefuellte_order_gibt_menge(self):
        with patch.object(h.okxf, "gefuellte_kontrakte", return_value=9.4):
            self.assertEqual(h._warten_auf_fuellung("X", "1", 10, versuche=1), 9.4)

    def test_unbekannt_zaehlt_als_nicht_gefuellt(self):
        # None = Abfrage unmoeglich. Dann wird NICHT gebucht: lieber eine
        # Order zu viel stornieren als eine Position erfinden.
        with patch.object(h.okxf, "gefuellte_kontrakte", return_value=None):
            self.assertEqual(h._warten_auf_fuellung("X", "1", 10, versuche=1), 0.0)

    def test_langsame_fuellung_wird_erwartet(self):
        folge = [0.0, 0.0, 5.0]
        with patch.object(h.okxf, "gefuellte_kontrakte", side_effect=lambda i, o: folge.pop(0)):
            self.assertEqual(
                h._warten_auf_fuellung("X", "1", 10, versuche=3, warte=0), 5.0)


class PapierlaufLaesstEchtePositionenInRuhe(unittest.TestCase):
    """Ein Papierlauf darf keine echte Position ausbuchen.

    ANLASS (gemessen 21.09.2026, 20:52): xperp lief mit handel_erlaubt=false
    im PAPER, der Kill-Switch loeste aus und schrieb
    "papier,schliessen,HBAR-...,grund kill_switch" ins Journal - waehrend
    /account/positions die 9.4 Kontrakte unveraendert hielt. Die echte Position
    war damit aus dem Buch, aber nicht an der Boerse geschlossen.
    """

    def setUp(self):
        self.geschrieben = []
        self.j = patch.object(h, "journal",
                              side_effect=lambda **k: self.geschrieben.append(k))
        self.j.start()
        self.addCleanup(self.j.stop)
        self.storno = patch.object(h.okxf, "markt_schliessen")
        self.storno.start()
        self.addCleanup(self.storno.stop)

    def test_flach_stellen_papier_laesst_live_stehen(self):
        z = {"positionen": [_pos("HBAR-100"), _pos("ALT-1", modus="papier")]}
        self.j.stop()   # der echte journal()-Aufruf wuerde schreiben
        h.journal = lambda **k: None
        with patch.object(h, "_kurs_aktuell", return_value=1.0):
            h.flach_stellen(z, live=False, grund="kill_switch")
        self.assertEqual([p["inst"] for p in z["positionen"]], ["HBAR-100"])
        h.okxf.markt_schliessen.assert_not_called()

    def test_pruefe_ausstiege_papier_laesst_live_stehen(self):
        z = {"positionen": [_pos("HBAR-100")]}
        z["positionen"][0]["stop"] = 99.0     # Kurs 1.0 -> Stop laengst gerissen
        z["positionen"][0]["ziel"] = 99.0
        h.journal = lambda **k: None
        with patch.object(h, "_kurs_aktuell", return_value=1.0):
            h.pruefe_ausstiege(z, live=False, w={})
        self.assertEqual(len(z["positionen"]), 1,
                         "Papierlauf darf eine echte Position nicht schliessen")


if __name__ == "__main__":
    unittest.main()
