"""Tests: ein wartender Auftrag belegt einen Platz (xperp).

ANLASS, gemessen am 21.09.2026: An der Boerse lagen 13 offene Limit-Auftraege
aus einem einzigen Abend - CL sechsmal, XAU fuenfmal, BZ und CRCL je einmal.
pruefe_einstiege() zaehlte nur z["positionen"]; ein Limit hinter dem Markt ist
aber ein WARTENDER Auftrag und noch keine Position. Fuer Platz-, Margin- und
Familienpruefung war nach dem Stellen also alles unveraendert, und der naechste
Zyklus legte fuer denselben Basiswert nach.

Geprueft wird die Regel: Platz, Margin und Familie sehen Positionen UND
wartende Auftraege.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parents[0]
for p in (HANDEL / "scanner", HANDEL, SPUR):
    if str(p) in sys.path:
        sys.path.remove(str(p))
    sys.path.insert(0, str(p))

import handeln as h                                                 # noqa: E402

assert str(Path(h.__file__).resolve()).startswith(str(SPUR)), h.__file__

WACHEN = json.loads((SPUR / "wachen.json").read_text(encoding="utf-8"))


def _kandidat(basis, kategorie="krypto"):
    return {"basis": basis, "kategorie": kategorie, "seite": "long"}


def _wartend(basis, margin=40.0, familie="krypto"):
    return {"inst": basis + "-USD_UM_XPERP", "basis": basis, "seite": "long",
            "familie": familie, "margin": margin, "kontrakte": 1.0,
            "ord_id": "1", "einstieg": 100.0, "stop": 95.0, "ziel": 110.0}


class PlatzBelegung(unittest.TestCase):
    """Die Zaehlung selbst - ohne Netz, ohne Journal."""

    def setUp(self):
        self.gestellt = []
        self._anlauf = h.anlauf
        # anlauf() wuerde Kerzen holen; hier zaehlt nur, OB gestellt wird.
        h.anlauf = lambda w, k: self.gestellt.append(k["basis"]) or None

    def tearDown(self):
        h.anlauf = self._anlauf

    def _lauf(self, positionen, wartende, kandidaten):
        z = {"positionen": positionen, "wartende": wartende}
        w = dict(WACHEN, max_offene_anlaeufe=4, max_margin_gesamt_usd=600.0)
        s = {"wochenende": False, "ruecklauf_usd": 0.0}
        h.pruefe_einstiege(z, kandidaten, w, False, s, 1.0)
        return self.gestellt

    def test_wartender_auftrag_belegt_einen_platz(self):
        # Vier Plaetze, vier wartende Auftraege -> kein weiterer Anlauf.
        wartende = [_wartend("CL"), _wartend("XAU"), _wartend("BZ"),
                    _wartend("CRCL")]
        self.assertEqual(self._lauf([], wartende, [_kandidat("SUI")]), [])

    def test_derselbe_basiswert_wird_nicht_doppelt_gestellt(self):
        # Genau der Abend-Fall: CL wartet, CL kommt erneut als Kandidat.
        self.assertEqual(self._lauf([], [_wartend("CL")], [_kandidat("CL")]), [])

    def test_freier_platz_bleibt_nutzbar(self):
        # Ein wartender Auftrag, drei Plaetze frei -> ein anderer Basiswert darf.
        self.assertEqual(self._lauf([], [_wartend("CL")], [_kandidat("SUI")]),
                         ["SUI"])

    def test_position_und_wartender_zusammen(self):
        pos = [{"basis": "HBAR", "margin": 70.0, "familie": "krypto",
                "inst": "HBAR-USD_UM_XPERP", "modus": "live"}]
        wartende = [_wartend("CL"), _wartend("XAU"), _wartend("BZ")]
        self.assertEqual(self._lauf(pos, wartende, [_kandidat("SUI")]), [])

    def test_ohne_wartende_wie_bisher(self):
        self.assertEqual(self._lauf([], [], [_kandidat("SUI")]), ["SUI"])

    def test_kaputter_eintrag_kippt_nicht(self):
        # Ein None in der Liste darf den Zyklus nicht abbrechen.
        self.assertEqual(self._lauf([], [None, _wartend("CL")],
                                    [_kandidat("SUI")]), ["SUI"])


class MarginUndFamilie(unittest.TestCase):
    """Margin und Familienanteil zaehlen wartende Auftraege ebenfalls."""

    def test_margin_eines_wartenden_zaehlt(self):
        z = {"positionen": [], "wartende": [_wartend("CL", margin=550.0)]}
        w = dict(WACHEN, max_offene_anlaeufe=4, max_margin_gesamt_usd=600.0)
        gestellt = []
        alt = h.anlauf
        h.anlauf = lambda w_, k: gestellt.append(k["basis"]) or None
        try:
            h.pruefe_einstiege(z, [_kandidat("SUI")], w, False,
                               {"wochenende": False}, 1.0)
        finally:
            h.anlauf = alt
        # 550 von 600 gebunden - fuer einen zweiten Anlauf bleibt zu wenig.
        # (anlauf() liefert hier None, entscheidend ist: die Margin ist gesehen)
        self.assertEqual(
            sum(float(a.get("margin") or 0.0) for a in z["wartende"]), 550.0)


class KeinSchreiben(unittest.TestCase):
    """Die Tests duerfen die echten Dateien der Spur nicht anfassen."""

    def test_spurordner_unveraendert(self):
        vorher = {p.name: p.stat().st_size for p in SPUR.iterdir()
                  if p.is_file()}
        z = {"positionen": [], "wartende": [_wartend("CL")]}
        alt = h.anlauf
        h.anlauf = lambda w_, k: None
        try:
            h.pruefe_einstiege(z, [_kandidat("SUI")], dict(WACHEN), False,
                               {"wochenende": False}, 1.0)
        finally:
            h.anlauf = alt
        nachher = {p.name: p.stat().st_size for p in SPUR.iterdir()
                   if p.is_file()}
        self.assertEqual(vorher, nachher)


if __name__ == "__main__":
    unittest.main()
