"""Stop-DECKUNG im Zyklus: die vierte Abgleichsstufe von xperp (T-362).

Warum dieser Test existiert
---------------------------
`handeln.bueche_abgleich()` laeuft in JEDEM Zyklus (T-277) - es sind die
Geister, die Groesse und die Fremdpositionen. Die vierte Stufe, die Frage
"WIEVIELE Kontrakte sind geschuetzt", fehlte: `_stop_vorhanden` sagt bei
Existenz EINER Schutz-Order "ja". Gemessen am 02.10.2026: ZEC mit 145
Kontrakten an der Boerse, sechs OCO-Stops ueber zusammen 126 - 19
Kontrakte bis zur Liquidation, waehrend der Lauf "ok" meldete.

Drei Eigenschaften werden festgenagelt:

  1. Es wird NICHTS gestellt. Ein Nachsetzen braucht einen Schutzpreis, den
     niemand genannt hat - das Werkzeug nimmt ihn ueber `--stop` und
     verweigert ohne den Schalter. Ein geratener Notausstieg ist eine Order,
     die jemand nicht bestellt hat.
  2. Eine fehlgeschlagene Boersenabfrage ist KEIN Befund. Sie liefert
     `abfrage_ok=False`; daraus darf niemand "kein Stop" ableiten.
  3. Ein toter Stop (auf/unter der Liquidation) ist ein Befund, auch wenn die
     Menge vollstaendig gedeckt ist - er schuetzt nichts.

Kein Netz, keine Order, keine echte Datei: `okxf` und `stopdeckung` werden
ersetzt, und der Modulwaechter vergleicht am Ende Dateiliste und Groessen des
echten Spurenordners.

Gegenproben (im Aufruf geprueft):
 * Stufe aus `buche_abgleich` entfernen  -> test_der_zyklus_ruft_die_deckung
 * Mengenvergleich in `deckung` entfernen -> test_teilmenge_ist_ein_befund

Lauf (aus dem xperp-Ordner):
    ../scanner/.venv/Scripts/python.exe -m unittest tests.test_deckung_zyklus
"""

import os
import sys
import unittest
from unittest import mock

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(os.path.dirname(HIER), "scanner"),
          os.path.dirname(HIER), HIER):
    sys.path.insert(0, p)

import handeln as h                       # noqa: E402
import stopdeckung as sd                  # noqa: E402

assert os.path.dirname(os.path.abspath(h.__file__)) == HIER, \
    "falsches handeln: %s" % h.__file__

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
    nach = _stand()
    neu = {k: v for k, v in nach.items() if _STAND_VOR.get(k) != v}
    assert not neu, "Tests haben in den echten Spurenordner geschrieben: %s" % neu


def _live(inst="X", kon=145.0, seite="long"):
    return {"inst": inst, "seite": seite, "kontrakte": kon, "modus": "live",
            "stop": 900.0, "ziel": 1500.0, "pos_id": "p1"}


def _okxf(positionen=None, stops=None):
    """okxf-Attrappe: Positionen und Schutzauftraege als Dicts."""
    m = mock.MagicMock()
    m.positionen.return_value = positionen or []
    m.schutz_stops.return_value = stops or []
    return m


def _auftrag(sz, stop, seite="sell", reduce=True, tp=None, ordType="oco"):
    d = {"instId": "X", "ordType": ordType, "side": seite,
         "sz": str(sz), "reduceOnly": "true" if reduce else "false",
         "state": "live"}
    if stop is not None:
        d["slTriggerPx"] = str(stop)
    if tp is not None:
        d["tpTriggerPx"] = str(tp)
    return d


class DeckungImZyklusTest(unittest.TestCase):
    """Die vierte Stufe: die MENGE, gemessen in jedem Zyklus."""

    def _z(self, positionen=None):
        return {"positionen": positionen if positionen is not None
                else [_live()]}

    def test_vollstaendig_geschuetzt_ist_kein_befund(self):
        z = self._z()
        attr = _okxf(positionen=[{"instId": "X", "pos": "145"}],
                     stops=[_auftrag(100, 900), _auftrag(45, 880)])
        with mock.patch.object(h.okxf, "positionen", attr.positionen), \
                mock.patch.object(h.okxf, "schutz_stops", attr.schutz_stops):
            befunde, ok = h.bueche_stopdeckung(z, {}, live=True, still=True)
        self.assertTrue(ok)
        self.assertEqual(befunde, [], "145 Kontrakte sind vollstaendig gedeckt")

    def test_teilmenge_ist_ein_befund(self):
        """DER Fall vom 02.10.2026: 145 an der Boerse, 126 geschuetzt."""
        z = self._z()
        attr = _okxf(positionen=[{"instId": "X", "pos": "145"}],
                     stops=[_auftrag(100, 900), _auftrag(26, 880)])
        with mock.patch.object(h.okxf, "positionen", attr.positionen), \
                mock.patch.object(h.okxf, "schutz_stops", attr.schutz_stops):
            befunde, ok = h.bueche_stopdeckung(z, {}, live=True, still=True)
        self.assertTrue(ok)
        self.assertEqual(len(befunde), 1)
        self.assertAlmostEqual(befunde[0]["deckung"]["fehlt"], 19.0)

    def test_es_wird_nie_gestellt(self):
        """Eine Pruefung, die nebenbei ordert, ist keine Pruefung."""
        z = self._z()
        attr = _okxf(positionen=[{"instId": "X", "pos": "145"}],
                     stops=[_auftrag(100, 900)])
        with mock.patch.object(h.okxf, "positionen", attr.positionen), \
                mock.patch.object(h.okxf, "schutz_stops", attr.schutz_stops), \
                mock.patch.object(h.okxf, "schutz_stop_setzen") as setzen:
            h.bueche_stopdeckung(z, {}, live=True, still=False)
        setzen.assert_not_called()

    def test_boersenfrage_aus_ist_kein_befund(self):
        """Ein Netzfehler darf nicht als 'kein Stop' gelesen werden."""
        z = self._z()
        with mock.patch.object(h.okxf, "positionen",
                               side_effect=OSError("no route to host")):
            befunde, ok = h.bueche_stopdeckung(z, {}, live=True, still=True)
        self.assertEqual(befunde, [])
        self.assertFalse(ok, "abfrage_ok muss False sein - 'unbekannt' ist "
                             "ein dritter Zustand, kein Befund")

    def test_toter_stop_ist_auch_bei_voller_menge_ein_befund(self):
        """Deckt die Menge, liegt aber an/unter der Liquidation: tot."""
        z = self._z()
        attr = _okxf(positionen=[{"instId": "X", "pos": "145",
                                  "liqPx": "950"}],
                     stops=[_auftrag(145, 900)])
        with mock.patch.object(h.okxf, "positionen", attr.positionen), \
                mock.patch.object(h.okxf, "schutz_stops", attr.schutz_stops):
            befunde, ok = h.bueche_stopdeckung(z, {}, live=True, still=True)
        self.assertTrue(ok)
        self.assertEqual(len(befunde), 1, "eine vollstaendige, tote Deckung "
                                           "ist kein Schutz")
        self.assertEqual(len(befunde[0]["tote"]), 1)

    def test_papierposition_wird_nicht_geprueft(self):
        """Ohne Boersen-Stop fuer eine Papierposition - sonst meldet die
        Spur eine Luecke, die sie nie haben kann."""
        z = self._z([_live(kon=100.0)])
        z["positionen"][0]["modus"] = "papier"
        attr = _okxf(positionen=[{"instId": "X", "pos": "100"}], stops=[])
        with mock.patch.object(h.okxf, "positionen", attr.positionen), \
                mock.patch.object(h.okxf, "schutz_stops", attr.schutz_stops):
            befunde, ok = h.bueche_stopdeckung(z, {}, live=True, still=True)
        self.assertTrue(ok)
        self.assertEqual(befunde, [])

    def test_der_zustand_traegt_die_zahl(self):
        """Damit die Vorschau und `--wachen` die Lage zeigen koennen."""
        z = self._z()
        attr = _okxf(positionen=[{"instId": "X", "pos": "145"}],
                     stops=[_auftrag(100, 900)])
        with mock.patch.object(h.okxf, "positionen", attr.positionen), \
                mock.patch.object(h.okxf, "schutz_stops", attr.schutz_stops):
            h.bueche_stopdeckung(z, {}, live=True, still=True)
        self.assertEqual(z["stopdeckung"], {"geprueft": 1, "luecken": 1})


class AbgleichRuftDieDeckungTest(unittest.TestCase):
    """Die Reihenfolge ist die Regel: die vierte Stufe haengt am Abgleich."""

    def test_der_zyklus_ruft_die_deckung(self):
        """Ohne diesen Aufruf ist die Stufe toter Code."""
        z = {"positionen": []}
        with mock.patch.object(h, "bueche_stopdeckung",
                               return_value=([], True)) as dec, \
                mock.patch.object(h, "wartende_auftraege", return_value=0), \
                mock.patch.object(h, "bueche_geister_aus", return_value=0), \
                mock.patch.object(h, "bueche_fremde_positionen_uebernehmen",
                                  return_value=0), \
                mock.patch.object(h, "bueche_groessen_abgleichen",
                                  return_value=[]):
            stand = h.buche_abgleich(z, {}, live=False, still=True)
        dec.assert_called_once()
        self.assertIn("deckung", stand)

    def test_der_abfragezustand_steht_im_stand(self):
        """`deckung_abfrage=False` heisst 'nicht gelesen' und muss als
        solches im Stand stehen - sonst ist 0 Luecken dasselbe wie 'leer'."""
        z = {"positionen": []}
        with mock.patch.object(h, "bueche_stopdeckung",
                               return_value=([], False)), \
                mock.patch.object(h, "wartende_auftraege", return_value=0), \
                mock.patch.object(h, "bueche_geister_aus", return_value=0), \
                mock.patch.object(h, "bueche_fremde_positionen_uebernehmen",
                                  return_value=0), \
                mock.patch.object(h, "bueche_groessen_abgleichen",
                                  return_value=[]):
            stand = h.buche_abgleich(z, {}, live=False, still=True)
        self.assertFalse(stand["deckung_abfrage"])


if __name__ == "__main__":
    unittest.main()