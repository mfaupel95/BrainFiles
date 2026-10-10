"""Tests fuer den EINBAU der Boersen-Bruecke in `handeln.buche_abgleich`.

Der Testfall ist die Nacht 04./05.10.2026: eine echte Live-Position, an der
Boerse weg, mit einem bezeugten Verkauf. Vor dem Einbau buchte die
Geisterpruefung sie neutral (Erlos 0.00); jetzt muss die Verkaufszeile den
echten Kurs tragen.

Die Reihenfolge ist der eigentliche Test: der Aufruf steht VOR
`bueche_geister_aus`. Ein Modul-Waechter vergleicht Dateiliste und Groessen
des echten Spurordners vor/nach dem Lauf - diese Tests duerfen unter keinen
Umstaenden in die echten Dateien schreiben.

Ausfuehren (aus xperp/tests):
    ../../scanner/.venv/Scripts/python.exe test_einbau_bruecke.py
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HIER = os.path.dirname(os.path.abspath(__file__))
_XPERR = os.path.normpath(os.path.join(_HIER, ".."))
HANDEL = os.path.normpath(os.path.join(_XPERR, os.pardir))

for _p in (_HIER, _XPERR, os.path.join(_XPERR, os.pardir)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _lade():
    import handeln  # noqa: E402  (der Pfad oben traegt)
    return handeln


def _setze_plan(ergebnis):
    """`boersen_bruecke.plan` fuer DIESEN Test ersetzen.

    `handeln.buche_verkaeufe_aus_boerse` holt das Modul mit `import
    boersen_bruecke as bruecke` IM FUNKTIONSRUMPF` - der Name wird also bei
    jedem Aufruf neu gebunden und zeigt jedes Mal auf dasselbe Modulobjekt.
    Ein Ersetzen am Modul genuegt; `addCleanup` stellt den Originalwert
    wieder her, damit kein Test in den naechsten hineinragt.

    (Die erste Fassing dieses Tests hatte gar keine Attrappe gesetzt und las
    deshalb die ECHTE Boerse - 0,0567 statt 0,0537. Ein Test, der vom
    Boersenzugang abhaengt, prueft den Buchungspfad nicht.)
    """
    import boersen_bruecke

    def fake(zustand, live=True):
        return ergebnis
    alt = boersen_bruecke.plan
    boersen_bruecke.plan = fake

    class _Zurueck:
        def __init__(self, ziel, alt):
            self.ziel, self.alt = ziel, alt

        def __enter__(self):
            return None

        def __exit__(self, *a):
            self.ziel.plan = self.alt
            return False
    return _Zurueck(boersen_bruecke, alt)


class ModulWaechter:
    """Dateiliste + Groessen des echten Spurordners, vorher/nachher."""

    def __init__(self, ordner):
        self.ordner = ordner
        self.vor = self._stand(ordner)

    @staticmethod
    def _stand(ordner):
        z = {}
        for wurzel, _dirs, dateien in os.walk(ordner):
            if "__pycache__" in wurzel:
                continue
            for d in dateien:
                p = os.path.join(wurzel, d)
                try:
                    z[p] = os.path.getsize(p)
                except OSError:
                    pass
        return z

    def veraendert(self):
        nach = self._stand(self.ordner)
        neu = set(nach) - set(self.vor)
        weg = set(self.vor) - set(nach)
        geaendert = {p for p in set(nach) & set(self.vor)
                     if nach[p] != self.vor[p]}
        return neu, weg, geaendert


class EinbauTest(unittest.TestCase):
    def setUp(self):
        self.h = _lade()
        self.waechter = ModulWaechter(_XPERR)

    def tearDown(self):
        neu, weg, geaendert = self.waechter.veraendert()
        self.assertEqual((neu, weg, geaendert), (set(), set(), set()),
                         "Der Test hat den echten Spurordner angefasst: %s"
                         % (neu or weg or geaendert))

    # --- die Buchungsfunktion selbst ---------------------------------

    def test_verkauf_mit_zeuge_bucht_den_echten_kurs(self):
        """STRK: Buch 8.033, Boerse 0, Verkauf bezeugt zu 0,0537.
        Der Erloes muss 0,0537 * 8.033 sein - nicht 0.00 wie beim Geist.

        Die Bruecke wird hier Attrappe: dieser Test soll den BUCHUNGSPFAD
        pruefen, nicht OKX. Die erste Fassung liess die echte Boerse
        antworten (0,0567 statt 0,0537) und verglich dann gegen die Attrappe -
        ein Test, der von der Boerse abhaengt, prueft nichts."""
        z = {"positionen": [{
            "pos_id": "p1", "inst": "STRK-USD_UM_XPERP-310919",
            "seite": "long", "kontrakte": 8033.0, "einstieg": 0.05433,
            "preis": 0.05433, "nominal": 469.0, "margin": 469.0,
            "modus": "live", "eroeffnet_zeit": "2026-10-04T09:20:03+00:00",
        }]}
        zeilen = []
        self.h.journal = lambda **kw: zeilen.append(kw)
        with _setze_plan([{"pos_id": "p1", "inst": "STRK-USD_UM_XPERP-310919",
                           "buch": 8033.0, "boerse": 0.0, "differenz": 8033.0,
                           "aktion": "verkauf",
                           "verkauf": {"menge": 8033.0, "kurs": 0.0537,
                                       "anzahl": 1,
                                       "erloes": 0.0537 * 8033.0,
                                       "erste": 1, "letzte": 2}}]):
            self.h.buche_verkaeufe_aus_boerse(z, live=True, still=True)
        self.assertEqual(len(zeilen), 1, "es muss genau eine Verkaufszeile geben")
        z0 = zeilen[0]
        self.assertEqual(z0["grund"], "verkauf_von_hand")
        self.assertAlmostEqual(float(z0["preis"]), 0.0537, places=6)
        self.assertAlmostEqual(float(z0["kontrakte"]), 8033.0, places=2)
        # margin_usd = was von der Margin zurueckkommt (Einsatz + Ergebnis),
        # NICHT Kurs * Menge. Bis 07.10.2026 stand hier die falsche Erwartung
        # 0.0537 * 8033 - sie galt nur, weil Hebel und Kontraktgroesse 1 waren.
        erwartet = 469.0 + 469.0 * (0.0537 - 0.05433) / 0.05433
        self.assertAlmostEqual(float(z0["margin_usd"]), erwartet, places=2)
        self.assertAlmostEqual(float(z0["nominal_usd"]), 469.0, places=2)
        # Die Position ist ganz weg an der Boerse und muss auch aus dem Buch.
        self.assertEqual([p for p in z["positionen"] if p["pos_id"] == "p1"], [])

    def _hand_verkauf(self, pos, kurs, menge, boerse=0.0, bezeugt=True):
        """Eine Handschliessung durch die Buchung schicken, Journalzeile zurueck."""
        z = {"positionen": [dict(pos)]}
        zeilen = []
        self.h.journal = lambda **kw: zeilen.append(kw)
        eintrag = {"pos_id": pos["pos_id"], "inst": pos["inst"],
                   "buch": pos["kontrakte"], "boerse": boerse,
                   "differenz": menge, "aktion": "verkauf",
                   "verkauf": ({"menge": menge, "kurs": kurs, "anzahl": 1,
                                "erloes": kurs * menge, "erste": 1,
                                "letzte": 2} if bezeugt else None)}
        with _setze_plan([eintrag]):
            self.h.buche_verkaeufe_aus_boerse(z, live=True, still=True)
        self.assertEqual(len(zeilen), 1)
        return zeilen[0]

    # XAU vom 05.10.2026: 96 Kontrakte @ 4150,2, Nominal 398,42, Hebel 5.
    XAU = {"pos_id": "x1", "inst": "XAU-USD_UM_XPERP-310502", "seite": "short",
           "kontrakte": 96.0, "einstieg": 4150.2, "nominal": 398.42,
           "margin": 79.68, "hebel": 5, "modus": "live",
           "eroeffnet_zeit": "2026-10-05T06:20:56+00:00"}

    def test_hebel_und_kontraktgroesse_ruinieren_das_journal_nicht(self):
        """Der Fall, der +438.540 USD in die Auswertung brachte: die Zeile
        trug Kurs * Kontrakte = 398.419 als Margin. Richtig sind rund 80 USD."""
        z0 = self._hand_verkauf(self.XAU, 4150.2, 96.0)     # Kurs unveraendert
        self.assertAlmostEqual(float(z0["margin_usd"]), 79.68, places=2)
        self.assertAlmostEqual(float(z0["nominal_usd"]), 398.42, places=2)
        self.assertLess(float(z0["margin_usd"]), 1000.0)

    def test_short_gewinn_und_verlust_haben_das_richtige_vorzeichen(self):
        fallend = self._hand_verkauf(self.XAU, 4108.7, 96.0)   # -1 % = Short-Gewinn
        steigend = self._hand_verkauf(self.XAU, 4191.7, 96.0)  # +1 % = Short-Verlust
        self.assertAlmostEqual(float(fallend["margin_usd"]),
                               79.68 + 398.42 * 0.01, places=1)
        self.assertAlmostEqual(float(steigend["margin_usd"]),
                               79.68 - 398.42 * 0.01, places=1)

    def test_ohne_zeugen_geht_die_margin_neutral_zurueck(self):
        z0 = self._hand_verkauf(self.XAU, 0.0, 96.0, bezeugt=False)
        self.assertEqual(z0["grund"], "verkauf_ohne_zeuge_neutral")
        self.assertAlmostEqual(float(z0["margin_usd"]), 79.68, places=2)

    def test_teilverkauf_bucht_nur_den_verkauften_anteil(self):
        z0 = self._hand_verkauf(self.XAU, 4150.2, 48.0, boerse=48.0)
        self.assertAlmostEqual(float(z0["margin_usd"]), 79.68 / 2, places=2)
        self.assertAlmostEqual(float(z0["nominal_usd"]), 398.42 / 2, places=2)

    def test_teilverkauf_bucht_die_differenz_und_laesst_den_rest(self):
        z = {"positionen": [{
            "pos_id": "p2", "inst": "STRK-USD_UM_XPERP-310919",
            "seite": "long", "kontrakte": 8033.0, "einstieg": 0.05433,
            "nominal": 469.0, "margin": 469.0, "modus": "live",
            "eroeffnet_zeit": "2026-10-04T09:20:03+00:00",
        }]}
        zeilen = []
        self.h.journal = lambda **kw: zeilen.append(kw)

        self.addCleanup(_setze_plan([{
            "pos_id": "p2", "inst": "STRK-USD_UM_XPERP-310919",
            "buch": 8033.0, "boerse": 5000.0, "differenz": 3033.0,
            "aktion": "verkauf",
            "verkauf": {"menge": 3033.0, "kurs": 0.0537, "anzahl": 2,
                        "erloes": 162.87, "erste": 1, "letzte": 2}}]).__exit__)

        n = self.h.buche_verkaeufe_aus_boerse(z, live=True, still=True)
        self.assertEqual(n, 1)
        self.assertAlmostEqual(float(zeilen[0]["kontrakte"]), 3033.0, places=2)
        # Der Rest bleibt im Buch, auf die Boersengroesse zurueckgerechnet.
        self.assertEqual(len(z["positionen"]), 1, "der Rest muss stehen bleiben")
        self.assertAlmostEqual(z["positionen"][0]["kontrakte"], 5000.0, places=2)

    def test_geister_gehoeren_nicht_in_diese_funktion(self):
        """SOL: Buch 334, Boerse 0, KEIN Verkauf bezeugt -> "geister".

        Das ist der Fall, an dem die erste Fassung dieses Tests gescheitert
        ist (0 Zeilen statt 1): sie stellte `aktion: geister` ein und
        erwartete eine Buchung. Geister sind nicht die Aufgabe dieser
        Funktion - die gehoeren `bueche_geister_aus`, das DANACH laeuft und
        sie genau so bucht, wie es immer tat. Der Verkaufspfad greift nur
        bei `aktion: verkauf`, und ohne Zeuge wird dort neutral gebucht und
        als `verkauf_ohne_zeuge_neutral` BENANNT.

        Der Gegenfall - Verkauf MIT Zeuge, aber die Einstufung bleibt
        "geister" - ist in `test_boersen_bruecke.py` festgenagelt."""
        z = {"positionen": [{
            "pos_id": "p3", "inst": "SOL-USD_UM_XPERP-310404",
            "seite": "long", "kontrakte": 334.0, "einstieg": 121.21,
            "nominal": 405.0, "margin": 405.0, "modus": "live",
            "eroeffnet_zeit": "2026-10-04T12:32:00+00:00",
        }]}
        zeilen = []
        self.h.journal = lambda **kw: zeilen.append(kw)
        with _setze_plan([{
                "pos_id": "p3", "inst": "SOL-USD_UM_XPERP-310404",
                "buch": 334.0, "boerse": 0.0, "differenz": 334.0,
                "aktion": "geister", "verkauf": None}]):
            n = self.h.buche_verkaeufe_aus_boerse(z, live=True, still=True)
        self.assertEqual(n, 0, "ein Geist gehoert nicht in die Verkaufssumme")
        self.assertEqual(zeilen, [],
                         "die Geisterpruefung bucht, nicht diese Funktion")
        self.assertEqual(len(z["positionen"]), 1,
                         "ohne Verkauf bleibt das Buch unberuehrt")

    # --- die zwei Grenzen ----------------------------------------------

    def test_papierlauf_bucht_nichts(self):
        """`live=False` heisst: die Boerse wird nicht einmal gelesen. Sonst
        wuerde eine Papierposition gegen den echten Bestand gerechnet und am
        Ende als verkauft dastehen."""
        z = {"positionen": [{
            "pos_id": "p4", "inst": "SOL-USD_UM_XPERP-310404",
            "seite": "long", "kontrakte": 334.0, "modus": "live",
            "eroeffnet_zeit": "2026-10-04T12:32:00+00:00",
        }]}
        aufgerufen = []

        import boersen_bruecke

        def darf_nicht(zustand, live=True):
            aufgerufen.append(True)
            return []
        alt = boersen_bruecke.plan
        self.addCleanup(setattr, boersen_bruecke, "plan", alt)
        boersen_bruecke.plan = darf_nicht
        zeilen = []
        self.h.journal = lambda **kw: zeilen.append(kw)
        n = self.h.buche_verkaeufe_aus_boerse(z, live=False, still=True)
        self.assertEqual(n, 0)
        self.assertEqual(aufgerufen, [], "der Papierlauf darf die Boerse nicht fragen")
        self.assertEqual(zeilen, [], "der Papierlauf darf nichts buchen")
        self.assertEqual(len(z["positionen"]), 1, "das Buch bleibt unangetastet")

    def test_boerse_ausfall_bucht_nichts(self):
        z = {"positionen": [{
            "pos_id": "p5", "inst": "STRK-USD_UM_XPERP-310919",
            "seite": "long", "kontrakte": 8033.0, "modus": "live",
            "eroeffnet_zeit": "2026-10-04T09:20:03+00:00",
        }]}
        zeilen = []
        self.h.journal = lambda **kw: zeilen.append(kw)

        self.addCleanup(_setze_plan(None).__exit__)
        self.assertEqual(self.h.buche_verkaeufe_aus_boerse(z, live=True, still=True), 0)
        self.assertEqual(zeilen, [])
        self.assertEqual(len(z["positionen"]), 1)

    # --- die Reihenfolge, der ganze Fix -------------------------------

    def test_reihenfolge_verkauf_vor_geist(self):
        """Der Einbau ist an der REIHENFOLGE, nicht am Vorhandensein der
        Funktion: `buche_abgleich` muss die Bruecke VOR `bueche_geister_aus`
        aufrufen. Ein Test gegen den Quelltext ist hier die kleinste
        Zusicherung, die ohne echten Boersezugriff auskommt - und sie greift
        genau dann, wenn jemand die zwei Stufen vertauscht."""
        quelle = open(os.path.join(_XPERR, "handeln.py"), encoding="utf-8").read()
        # Seit a37b8802 laufen die Stufen ueber `_abgleich_stufe(name, fn, ...)`;
        # gesucht wird deshalb das Paar Stufenname + Funktion, nicht die Zuweisung.
        abgleich = quelle[quelle.find("def buche_abgleich("):]
        i_verkauf = abgleich.find("\"verkaeufe\", buche_verkaeufe_aus_boerse")
        i_geist = abgleich.find("\"geister\", bueche_geister_aus")
        self.assertTrue(i_verkauf > 0, "der Verkauf-Aufruf fehlt ganz")
        self.assertTrue(i_geist > 0, "der Geist-Aufruf fehlt ganz")
        self.assertLess(i_verkauf, i_geist,
                        "die Bruecke muss VOR der Geisterpruefung laufen")


if __name__ == "__main__":
    unittest.main(verbosity=2)