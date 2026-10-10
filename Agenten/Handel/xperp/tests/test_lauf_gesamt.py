"""Gesamttest fuer `handeln.lauf()`: Abgleich -> Kill -> Herzschlag -> Einstiege.

WARUM (09.10.2026): zwei getrennte Fixes beruehren denselben Ablauf.
  * Eine Abgleichsstufe, die an der Boerse scheitert, darf Kill-Switch und
    Herzschlag-Notausstieg nicht ueberspringen (`_abgleich_stufe`).
  * Eine Stop-Luecke sperrt neue Live-Einstiege, aber nichts davon
    (`stopluecken_sperre`).
Einzeltests pruefen je eine Funktion. Dieser Test laesst `lauf()` und
`buche_abgleich()` ECHT laufen und ersetzt nur Rand und Schreibzugriffe, damit
die Reihenfolge und das Zusammenspiel festgenagelt sind.

Kein Netz, keine Order, keine echte Datei: Zustand, Wachen, Journal, Boerse
und alle Schreibwege sind ersetzt.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SPUR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SPUR.parent))
sys.path.insert(0, str(SPUR))

import handeln as h                                                  # noqa: E402

assert h.__file__.startswith(str(SPUR)), "falsches handeln: %s" % h.__file__

LAGE_OK = {"kill": False, "herzschlag_frisch": True, "herzschlag_alter_min": 1.0,
           "ruecklauf_usd": 0.0, "groessenfaktor": 1.0}


def lauf_mit(lage, modus="live", wartende=None, stopdeckung=(([], True)),
             order_stand_wirft=False):
    """`lauf(modus)` mit echtem Ablauf; liefert die Mocks der Seiteneffekte."""
    z = {"positionen": [], "wartende": wartende or []}
    m = {n: MagicMock(name=n) for n in (
        "flach_stellen", "pruefe_ausstiege", "pruefe_einstiege",
        "schreibe_zustand", "buche_funding", "spiegeln", "sperre_zu", "hinweis")}
    m["sperre_zu"].return_value = False
    stufen_null = dict(wartende_auftraege=0, buche_verkaeufe_aus_boerse=0,
                       bueche_geister_aus=0, bueche_fremde_positionen_uebernehmen=0,
                       bueche_groessen_abgleichen=[])
    with patch.object(h.bot, "wachen", return_value={
            "max_margin_gesamt_usd": 100, "kill_switch_gesamt_usd": 50}), \
         patch.object(h, "lade_zustand", return_value=z), \
         patch.object(h.wx, "lage", return_value=dict(lage)), \
         patch.object(h, "sperren_live", return_value=[]), \
         patch.object(h, "bueche_papier_altlasten_aus", return_value=0), \
         patch.object(h, "rangliste", return_value=([], 0.0)), \
         patch.object(h, "kandidaten", return_value=[]), \
         patch.object(h, "bueche_stopdeckung", return_value=stopdeckung), \
         patch.object(h, "flach_stellen", m["flach_stellen"]), \
         patch.object(h, "pruefe_ausstiege", m["pruefe_ausstiege"]), \
         patch.object(h, "pruefe_einstiege", m["pruefe_einstiege"]), \
         patch.object(h, "schreibe_zustand", m["schreibe_zustand"]), \
         patch.object(h, "buche_funding", m["buche_funding"]), \
         patch.object(h, "_spiegeln", m["spiegeln"]), \
         patch.object(h.wx, "sperre_zu", m["sperre_zu"]), \
         patch.object(h.ereignis, "hinweis", m["hinweis"]):
        patches = [patch.object(h, n, return_value=v)
                   for n, v in stufen_null.items() if not (
                       n == "wartende_auftraege" and order_stand_wirft)]
        if order_stand_wirft:
            patches.append(patch.object(h.okxf, "order_stand",
                                        side_effect=RuntimeError("Netz weg")))
        for p in patches:
            p.start()
        try:
            h.lauf(modus)
        finally:
            for p in patches:
                p.stop()
    return z, m


WARTEND = [{"inst": "XRP-USD_UM_XPERP-310404", "ord_id": "1", "kontrakte": 1}]


class LaufGesamt(unittest.TestCase):
    def test_normalfall_handelt_und_schreibt(self):
        _, m = lauf_mit(LAGE_OK)
        m["pruefe_ausstiege"].assert_called_once()
        m["pruefe_einstiege"].assert_called_once()
        m["schreibe_zustand"].assert_called_once()
        m["flach_stellen"].assert_not_called()

    def test_kill_laeuft_trotz_ausfall_im_abgleich(self):
        lage = dict(LAGE_OK, kill=True, ruecklauf_usd=60.0)
        _, m = lauf_mit(lage, wartende=WARTEND, order_stand_wirft=True)
        m["flach_stellen"].assert_called_once()
        self.assertEqual(m["flach_stellen"].call_args[0][2], "kill_switch")
        m["sperre_zu"].assert_called_once()
        m["pruefe_einstiege"].assert_not_called()
        m["pruefe_ausstiege"].assert_not_called()

    def test_herzschlag_notausstieg_trotz_ausfall_im_abgleich(self):
        lage = dict(LAGE_OK, herzschlag_frisch=False, herzschlag_alter_min=99.0)
        _, m = lauf_mit(lage, wartende=WARTEND, order_stand_wirft=True)
        m["flach_stellen"].assert_called_once()
        self.assertEqual(m["flach_stellen"].call_args[0][2], "herzschlag_alt")
        m["pruefe_einstiege"].assert_not_called()

    def test_stop_luecke_sperrt_einstiege_nicht_ausstiege(self):
        z, m = lauf_mit(LAGE_OK, stopdeckung=([{"position": {}}], True))
        m["pruefe_einstiege"].assert_not_called()
        m["pruefe_ausstiege"].assert_called_once()
        m["schreibe_zustand"].assert_called_once()
        m["hinweis"].assert_called_once()
        self.assertTrue(z["stopluecke_gemeldet"])

    def test_stop_luecke_im_papierlauf_sperrt_nicht(self):
        _, m = lauf_mit(LAGE_OK, modus="papier",
                        stopdeckung=([{"position": {}}], True))
        m["pruefe_einstiege"].assert_called_once()
        m["hinweis"].assert_not_called()

    def test_abruffehler_der_deckung_sperrt_nicht(self):
        _, m = lauf_mit(LAGE_OK, stopdeckung=([], False))
        m["pruefe_einstiege"].assert_called_once()

    def test_kill_geht_vor_stop_luecke(self):
        lage = dict(LAGE_OK, kill=True, ruecklauf_usd=60.0)
        _, m = lauf_mit(lage, stopdeckung=([{"position": {}}], True))
        m["flach_stellen"].assert_called_once()
        m["pruefe_ausstiege"].assert_not_called()


if __name__ == "__main__":
    unittest.main()
