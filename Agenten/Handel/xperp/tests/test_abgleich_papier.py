"""Tests: der Buchabgleich laeuft in JEDEM Zyklus (T-277, 01.10.2026).

ANLASS, an der Boerse gemessen: xperp lief seit dem 29.09.2026 12:00 Papier.
Die vier Abgleichsfunktionen standen aber im `if live:`-Zweig, also erreichte
kein HANDGRIFF aus der OKX-App das Buch. Stand am 01.10.2026 abends:

    Buch:   XRP 704, ADA 235, VVV 217, ZEC 38   + zwei wartende Auftraege
    Boerse: ZEC 145                              (sonst nichts)

Alle vier Handgriffe stehen in /account/positions-history (XRP 891 Kontrakte,
ADA 235, VVV 217, ZEC 55 geschlossen). Der Abgleich ist Buchhaltung, keine
Handelsentscheidung - er gehoert in jeden Zyklus, aber OHNE Boerseneingriff:
im Papierlauf wird kein Stop gestellt und nichts storniert.

Die Tests schreiben NIE in die echten Dateien: `journal`, `_geist_erloes` und
`okxf` sind ersetzt, und ein Modulwaechter vergleicht den Spurenordner
vorher/nachher.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(SPUR))

import handeln as h                                                  # noqa: E402

assert h.__file__.startswith(str(SPUR)), "falsches handeln: %s" % h.__file__

XRP = "XRP-USD_UM_XPERP-310404"
ZEC = "ZEC-USD_UM_XPERP-310530"
NEU = "AAVE-USD_UM_XPERP-310704"

KERZEN = [[1, 10.0, 10.5, 9.5, 10.2, 1] for _ in range(40)]


def _stand():
    aus = {}
    for name in sorted(os.listdir(SPUR)):
        p = SPUR / name
        if p.is_file():
            aus[name] = p.stat().st_size
    return aus


_STAND_VOR = None


def setUpModule():
    global _STAND_VOR
    _STAND_VOR = _stand()


def tearDownModule():
    neu = {k: v for k, v in _stand().items() if _STAND_VOR.get(k) != v}
    assert not neu, "Tests haben in den echten Spurenordner geschrieben: %s" % neu


def _pos(inst, modus="live", kontrakte=10.0, ord_id="", zeit=None):
    p = {"inst": inst, "seite": "long", "familie": "krypto", "einstieg": 1.0,
         "nominal": 100.0, "margin": 20.0, "hebel": 5.0, "kontrakte": kontrakte,
         "stop": 0.9, "ziel": 1.2, "modus": modus, "ord_id": ord_id}
    if zeit:
        p["eroeffnet_zeit"] = zeit
        p["eroeffnet"] = zeit[:10]
    return p


def _boerse(inst, pos, avg=1.5):
    return {"instId": inst, "pos": str(pos), "avgPx": str(avg),
            "margin": "20", "notionalUsd": "100", "slTriggerPx": ""}


class Umgebung:
    """Stubbt okxf und journal - eine einzige Fassung fuer alle Tests.

    `positionen` ist die Boersenliste, `storniert`/`gestellte_stops` sammeln
    jeden Boerseneingriff. Ein Test, der hier etwas eintraegt, hat bewiesen,
    dass im Papierlauf etwas passiert ist, was nicht passieren darf.
    """

    def __init__(self, boerse, vorhandener_stop=(), order_stand=None,
                 positionen_fehler=None):
        self.boerse = list(boerse)
        self.vorhandener_stop = list(vorhandener_stop)
        self.order_stand = order_stand or {}
        self.positionen_fehler = positionen_fehler
        self.storniert = []
        self.gestellte_stops = []
        self.journal = []

    def _positionen(self, inst=None):
        if self.positionen_fehler:
            raise RuntimeError(self.positionen_fehler)
        return self.boerse

    def __enter__(self):
        self._p = [
            patch.object(h.okxf, "positionen", side_effect=self._positionen),
            patch.object(h.okxf, "order_stornieren",
                         side_effect=lambda inst, oid: self.storniert.append(
                             (inst, oid)) or {}),
            patch.object(h.okxf, "kerzen",
                         side_effect=lambda inst, bar="1H", anzahl=300: KERZEN),
            patch.object(h.okxf, "instrument",
                         side_effect=lambda basis: {"instId": basis,
                                                    "tickSz": "0.01"}),
            patch.object(h.okxf, "auf_tick",
                         side_effect=lambda instr, preis: round(preis, 2)),
            patch.object(h.okxf, "schutz_stops",
                         side_effect=lambda inst=None: self.vorhandener_stop),
            patch.object(h.okxf, "schutz_stop_setzen",
                         side_effect=lambda *a, **k: self.gestellte_stops.append(
                             (a, k)) or {"algoId": "1"}),
            patch.object(h.okxf, "gefuellte_kontrakte", return_value=0.0),
            patch.object(h.okxf, "order_stand",
                         side_effect=lambda inst, oid: self.order_stand.get(oid, {})),
            patch.object(h, "journal",
                         side_effect=lambda **k: self.journal.append(k)),
            patch.object(h, "_geist_erloes",
                         side_effect=lambda p: (20.0, "boerse", 1.0)),
        ]
        for p in self._p:
            p.start()
        return self

    def __exit__(self, *a):
        for p in self._p:
            p.stop()
        return False


WACHEN = {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0,
          "max_offene_anlaefe": 4}


class PapierGleichtAbTest(unittest.TestCase):
    """Der Kern von T-277: der Abgleich laeuft auch im Papierlauf."""

    def test_geist_wird_im_papierlauf_ausgebucht(self):
        """XRP/ADA/VVV: an der Boerse weg, im Buch noch da."""
        z = {"positionen": [_pos(XRP, kontrakte=704.0), _pos(ZEC, kontrakte=38.0)],
             "wartende": []}
        with Umgebung([_boerse(ZEC, 145)]) as u:
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["geister"], 1)
        self.assertEqual([p["inst"] for p in z["positionen"]], [ZEC])
        self.assertEqual(u.storniert, [])                    # keine Boersenaktion
        self.assertEqual([j["grund"] for j in u.journal],
                         ["buchbereinigung_geist", "handanpassung"])

    def test_geist_ohne_boersenbeleg_bleibt_im_papierlauf(self):
        """Regel Max 09.10.2026: nur mit Boersenbeleg wird ausgebucht.

        Vorher buchte der Abgleich eine fehlende Live-Position NEUTRAL aus
        (Einsatz zurueck) - am 05.10.2026 verschwanden so sechs echte
        Positionen aus dem Buch, waehrend sie an der Boerse offen blieben.
        Ohne realizedPnl-Beleg bleibt die Position als UNKLAR stehen.
        """
        z = {"positionen": [_pos(XRP, kontrakte=704.0), _pos(ZEC, kontrakte=38.0)],
             "wartende": []}
        with Umgebung([_boerse(ZEC, 145)]) as u, \
                patch.object(h, "_geist_erloes",
                             side_effect=lambda p: (p.get("margin") or 0.0,
                                                    "neutral", None)):
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["geister"], 0, "ohne Beleg zaehlt kein Geist")
        self.assertEqual(sorted(p["inst"] for p in z["positionen"]),
                         sorted([XRP, ZEC]),
                         "beide bleiben im Buch, keine Ausbuchung")
        gruende = [j["grund"] for j in u.journal]
        self.assertNotIn("buchbereinigung_geist", gruende,
                         "ohne Beleg keine Geist-Ausbuchung")
        self.assertEqual([g for g in gruende if g != "handanpassung"], [],
                         "nur die legitime Groessen-Anpassung von ZEC ist erlaubt")

    def test_groesse_folgt_der_boerse_im_papierlauf(self):
        """ZEC: Buch 38, Boerse 145 - der Handgriff war ein Zukauf."""
        z = {"positionen": [_pos(ZEC, kontrakte=38.0)], "wartende": []}
        with Umgebung([_boerse(ZEC, 145)]) as u:
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["groessen"], 1)
        self.assertEqual(z["positionen"][0]["kontrakte"], 145.0)
        self.assertEqual(u.journal[0]["grund"], "handanpassung")

    def test_papierlauf_storniert_keine_order(self):
        """Ein Storno ist ein echter Boerseneingriff - im Papier verboten."""
        z = {"positionen": [_pos(XRP, ord_id="999", zeit="2026-09-01T00:00:00+00:00")],
             "wartende": []}
        with Umgebung([]) as u:
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["geister"], 1)
        self.assertEqual(u.storniert, [])

    def test_live_storniert_die_order(self):
        """Gegenprobe: derselbe Fall im Live-Lauf storniert sehr wohl."""
        z = {"positionen": [_pos(XRP, ord_id="999", zeit="2026-09-01T00:00:00+00:00")],
             "wartende": []}
        with Umgebung([]) as u:
            h.buche_abgleich(z, WACHEN, live=True)
        self.assertEqual(u.storniert, [(XRP, "999")])

    def test_fremde_position_ohne_stop_im_papierlauf(self):
        """Von Hand eroeffnet: ins Buch, aber KEIN Stop (keine Order)."""
        z = {"positionen": [], "wartende": [],
             "rangliste": {"werte": [{"basis": "AAVE", "kategorie": "krypto"}]}}
        with Umgebung([_boerse(NEU, 4.5, avg=170.33)]) as u:
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["fremde"], 1)
        self.assertEqual(z["positionen"][0]["inst"], NEU)
        self.assertEqual(z["positionen"][0]["modus"], "live")
        self.assertEqual(u.gestellte_stops, [])              # keine Order
        self.assertEqual(u.journal[0]["grund"], "fremdposition_uebernommen")

    def test_live_stellt_den_stop(self):
        """Gegenprobe: im Live-Lauf wird der fehlende Schutz gestellt."""
        z = {"positionen": [], "wartende": [],
             "rangliste": {"werte": [{"basis": "AAVE", "kategorie": "krypto"}]}}
        with Umgebung([_boerse(NEU, 4.5, avg=170.33)]) as u:
            h.buche_abgleich(z, WACHEN, live=True)
        self.assertEqual(len(u.gestellte_stops), 1)

    def test_netzfehler_laesst_das_buch_unberuehrt(self):
        """Faellt die Boersenfrage aus, wird nichts gebucht - nie leeren.

        Geprueft wird die EIGENSCHAFT, nicht ein Schlüsselsatz: der Abgleich
        waechst mit seinen Stufen (zwei neue am 05.10.2026, T-362), und ein
        Test gegen ein festes Dikt wird bei jeder Erweiterung rot und trainiert
        den Reflex, rote Tests wegzuklicken. Aussage bleibt: keine Zaehlung ist
        ungleich 0, das Buch ist unveraendert, nichts gebucht - und der
        Abfragezustand steht als `False` da, damit "nicht lesbar" nicht wie
        "leer" aussieht.
        """
        z = {"positionen": [_pos(XRP, kontrakte=704.0)], "wartende": []}
        with Umgebung([], positionen_fehler="Netz weg") as u:
            stand = h.buche_abgleich(z, WACHEN, live=False)
        for stufe in ("wartende", "geister", "fremde", "groessen", "deckung"):
            self.assertEqual(stand[stufe], 0, "%s darf bei Netzfehler nicht "
                                               "zaehlen" % stufe)
        self.assertFalse(stand["deckung_abfrage"],
                         "'nicht lesbar' ist ein dritter Zustand und muss "
                         "so im Stand stehen")
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(u.journal, [])

    def test_papier_position_wird_nicht_angefasst(self):
        """Nur modus=live geht gegen die Boerse - Papier bleibt Papier."""
        z = {"positionen": [_pos("FOO-USD_UM_XPERP-1", modus="papier")],
             "wartende": []}
        with Umgebung([]) as u:
            stand = h.buche_abgleich(z, WACHEN, live=False)
        self.assertEqual(stand["geister"], 0)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(u.journal, [])


class BoersenwerteTest(unittest.TestCase):
    """Margin und Nennwert kommen von der BOERSE, wenn sie dort stehen."""

    def test_boersenwerte_schlagen_die_verhaeltnisrechnung(self):
        """Gemessen 01.10.2026: Verhaeltnis 302.35 gegen Boerse 238.45."""
        z = {"positionen": [_pos(ZEC, kontrakte=38.0)]}
        boerse = [{"instId": ZEC, "pos": "145", "margin": "238.45",
                   "notionalUsd": "1935.40"}]
        with Umgebung(boerse):
            h.bueche_groessen_abgleichen(z, {})
        p = z["positionen"][0]
        self.assertEqual(p["kontrakte"], 145.0)
        self.assertAlmostEqual(p["margin"], 238.45, places=4)
        self.assertAlmostEqual(p["nominal"], 1935.40, places=4)

    def test_ohne_boersenfeld_bleibt_die_verhaeltnisrechnung(self):
        """Alte Boersenform: lieber ein mitgezogener Wert als ein Nullwert."""
        z = {"positionen": [_pos(ZEC, kontrakte=38.0)]}
        with Umgebung([{"instId": ZEC, "pos": "145"}]):
            h.bueche_groessen_abgleichen(z, {})
        p = z["positionen"][0]
        self.assertAlmostEqual(p["margin"], 20.0 * 145 / 38, places=4)
        self.assertAlmostEqual(p["nominal"], 100.0 * 145 / 38, places=4)

    def test_werte_folgen_der_boerse_auch_ohne_groessenunterschied(self):
        """Sonst bliebe eine einmal falsch mitgezogene Margin stehen."""
        p = _pos(ZEC, kontrakte=145.0)
        p["margin"], p["nominal"] = 298.02, 2066.31
        z = {"positionen": [p]}
        boerse = [{"instId": ZEC, "pos": "145", "margin": "238.45",
                   "notionalUsd": "1935.40"}]
        with Umgebung(boerse) as u:
            abw = h.bueche_groessen_abgleichen(z, {})
        self.assertEqual(abw, [], "die Kontraktzahl stimmt - keine Groesse")
        self.assertAlmostEqual(p["margin"], 238.45, places=4)
        self.assertAlmostEqual(p["nominal"], 1935.40, places=4)
        self.assertEqual(u.journal[0]["grund"], "handanpassung")

    def test_kleine_rundung_loest_keinen_eintrag_aus(self):
        """Unter 1 % ist es Rundung, kein Handgriff."""
        p = _pos(ZEC, kontrakte=145.0)
        p["margin"], p["nominal"] = 238.45, 1935.40
        z = {"positionen": [p]}
        boerse = [{"instId": ZEC, "pos": "145", "margin": "239.10",
                   "notionalUsd": "1936.00"}]
        with Umgebung(boerse) as u:
            self.assertEqual(h.bueche_groessen_abgleichen(z, {}), [])
        self.assertEqual(u.journal, [])


class WartendeAuftraegeTest(unittest.TestCase):
    """T-277, zweiter Teil: ein ueber Nacht gefuellter Auftrag."""

    def _z(self):
        return {"positionen": [], "wartende": [
            {"inst": NEU, "basis": "AAVE", "seite": "long", "familie": "krypto",
             "einstieg": 170.33, "stop": 162.11, "ziel": 186.77,
             "kontrakte": 4.5, "nominal": 76.65, "margin": 15.33, "hebel": 5,
             "ord_id": "3965486318600704000"}]}

    def test_gefuellter_auftrag_bucht_mit_der_boersenzeit(self):
        """Eroeffnet wird mit der FUELLUNG, nicht mit dem Abarbeiten.

        Vorher stand die Position mit "jetzt" im Buch: die Haltedauer war zu
        kurz, und die Geisterpruefung fand kein Boersenergebnis mehr, weil sie
        nur Schliessungen NACH dem Eroeffnen sucht.
        """
        stand = {"state": "filled", "accFillSz": "4.5", "avgPx": "170.33",
                 "uTime": "1790694709335"}          # 2026-09-29T15:11:49Z
        with Umgebung([], order_stand={"3965486318600704000": stand}) as u:
            n = h.wartende_auftraege(self._z(), False, WACHEN)
        self.assertEqual(n, 1)
        self.assertEqual(u.journal[0]["grund"], "order_gefuellt")

    def test_boersenzeit_landet_in_der_position(self):
        z = self._z()
        stand = {"state": "filled", "accFillSz": "4.5", "avgPx": "170.33",
                 "uTime": "1790694709335"}
        with Umgebung([], order_stand={"3965486318600704000": stand}):
            h.wartende_auftraege(z, False, WACHEN)
        p = z["positionen"][0]
        self.assertTrue(p["eroeffnet_zeit"].startswith("2026-09-29T15:11:49"),
                        p["eroeffnet_zeit"])
        self.assertEqual(p["eroeffnet"], "2026-09-29")

    def test_ohne_boersenzeit_bleibt_es_beim_alten_weg(self):
        z = self._z()
        stand = {"state": "filled", "accFillSz": "4.5", "avgPx": "170.33"}
        with Umgebung([], order_stand={"3965486318600704000": stand}):
            h.wartende_auftraege(z, False, WACHEN)
        self.assertTrue(z["positionen"][0]["eroeffnet_zeit"])

    def test_toter_auftrag_wird_vergessen(self):
        z = self._z()
        stand = {"state": "canceled"}
        with Umgebung([], order_stand={"3965486318600704000": stand}):
            h.wartende_auftraege(z, False, WACHEN)
        self.assertEqual(z["wartende"], [])
        self.assertEqual(z["positionen"], [])


if __name__ == "__main__":
    unittest.main()