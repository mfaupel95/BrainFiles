"""Tests: fremde (Hand-)Positionen ins xperp-Buch uebernehmen (24.09.2026).

ANLASS, gemessen an der Boerse: Max eroeffnet Positionen in der OKX-App (OKX
kennzeichnet sie mit tag='OTversionB'); die Spur kennt nur ihr eigenes Journal.
Am 23.09.2026 standen so

    BZ-USD_UM_XPERP-310509   1467 Kontrakte @ 97.568   (drei Fillungen)
    CL-USD_UM_XPERP-310509    133 Kontrakte @ 91.625   (drei Fillungen)

offen - mit belegter Margin, ohne Buchplatz, ohne Ausstiegslogik und bei BZ
teilweise ohne Stop. `bueche_geister_aus` raeumt die Gegenrichtung auf; hier
wird die fehlende Richtung geprueft.

Die Tests schreiben NIE in die echten Dateien: `journal` und `okxf` sind
ersetzt, und ein Modulwaechter vergleicht den Spurenordner vorher/nachher.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SPUR = Path(__file__).resolve().parents[1]
HANDEL = SPUR.parent
sys.path.insert(0, str(HANDEL))
sys.path.insert(0, str(SPUR))

import handeln as h                                                  # noqa: E402

BZ = "BZ-USD_UM_XPERP-310509"
CL = "CL-USD_UM_XPERP-310509"
FREMD = "SUI-USDC"                       # Spot-Bestand einer anderen Spur

KERZEN = [[1, 10.0, 10.5, 9.5, 10.2, 1] for _ in range(40)]


def _boerse(inst, pos, avg=97.5, margin=140.0, sl=""):
    return {"instId": inst, "pos": str(pos), "avgPx": str(avg), "margin": str(margin),
            "notionalUsd": "1440", "slTriggerPx": sl}


def _wachen():
    return {"stop_atr_faktor": 1.5, "ziel_atr_faktor": 3.0}


class _Umgebung:
    """Stubbt okxf: Boersenliste, Kerzen, Kontrakt, Stop-Verhalten."""

    def __init__(self, buch, stoppe=(), vorhandener_stop=(), atr_ok=True):
        self.buch = buch
        self.stoppe = list(stoppe)
        self.vorhandener_stop = list(vorhandener_stop)
        self.atr_ok = atr_ok
        self.gestellte_stops = []
        self.journal = []

    def __enter__(self):
        self._p = [
            patch.object(h.okxf, "positionen", side_effect=lambda inst=None: self.buch),
            patch.object(h.okxf, "kerzen",
                         side_effect=lambda inst, bar="1H", anzahl=300: KERZEN if self.atr_ok else []),
            patch.object(h.okxf, "instrument",
                         side_effect=lambda basis: {"instId": basis, "tickSz": "0.01"}),
            patch.object(h.okxf, "auf_tick", side_effect=lambda instr, preis: round(preis, 2)),
            patch.object(h.okxf, "schutz_stops", side_effect=lambda inst=None: self.vorhandener_stop),
            patch.object(h.okxf, "schutz_stop_setzen",
                         side_effect=lambda *a, **k: self.gestellte_stops.append((a, k)) or {"algoId": "1"}),
            patch.object(h, "journal", side_effect=lambda **k: self.journal.append(k)),
        ]
        for p in self._p:
            p.start()
        return self

    def __exit__(self, *a):
        for p in self._p:
            p.stop()
        return False


class Uebernahme(unittest.TestCase):

    def _z(self, positionen=(), werte=None):
        return {"positionen": list(positionen),
                "rangliste": {"werte": werte if werte is not None
                              else [{"basis": "BZ", "kategorie": "rohstoff"},
                                    {"basis": "CL", "kategorie": "rohstoff"}]}}

    def test_fremde_position_wird_uebernommen(self):
        z = self._z()
        with _Umgebung([_boerse(BZ, 1467, avg=97.568)]) as u:
            n = h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(n, 1)
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        self.assertEqual(p["inst"], BZ)
        self.assertEqual(p["kontrakte"], 1467.0)
        self.assertEqual(p["einstieg"], 97.568)          # Boersenschnitt, nicht geschaetzt
        self.assertEqual(p["modus"], "live")
        self.assertEqual(p["herkunft"], "boerse_handgriff")
        self.assertEqual(p["familie"], "rohstoff")       # aus der Rangliste
        self.assertTrue(p["stop"] < p["einstieg"] < p["ziel"])
        self.assertEqual([q["grund"] for q in u.journal], ["fremdposition_uebernommen"])
        self.assertEqual(u.journal[0]["modus"], "live")
        self.assertEqual(len(u.gestellte_stops), 1)      # Stop fehlt -> gestellt

    def test_eigene_position_wird_nicht_erneut_uebernommen(self):
        z = self._z(positionen=[{"inst": BZ, "modus": "live", "kontrakte": 100.0}])
        with _Umgebung([_boerse(BZ, 1467)]) as u:
            n = h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(n, 0)
        self.assertEqual(len(z["positionen"]), 1)        # unveraendert
        self.assertEqual(u.gestellte_stops, [])

    def test_fremdes_instrument_bleibt_draussen(self):
        """Ein Spot-Bestand einer anderen Spur gehoert nicht in dieses Buch."""
        z = self._z()
        with _Umgebung([_boerse(FREMD, 500, avg=1.0)]) as u:
            n = h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(n, 0)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(u.gestellte_stops, [])

    def test_ohne_atr_keine_uebernahme(self):
        """Lieber ein gemeldeter Fremdbestand als ein erfundener Stop."""
        z = self._z()
        with _Umgebung([_boerse(BZ, 1467)], atr_ok=False) as u:
            n = h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(n, 0)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(u.gestellte_stops, [])

    def test_boersenfrage_faellt_aus_laesst_das_buch_in_ruhe(self):
        z = self._z()
        with patch.object(h.okxf, "positionen", side_effect=RuntimeError("Netz tot")):
            n = h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(n, 0)
        self.assertEqual(z["positionen"], [])

    def test_kein_zweiter_stop_wenn_einer_liegt(self):
        """Ein angehaengter oder bedingter Stop zaehlt - sonst doppelte Ausloesung."""
        z = self._z()
        with _Umgebung([_boerse(BZ, 1467, sl="96.62")]) as u:
            h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(u.gestellte_stops, [])
        z2 = self._z()
        with _Umgebung([_boerse(BZ, 1467)],
                       vorhandener_stop=[{"slTriggerPx": "96.62"}]) as u2:
            h.bueche_fremde_positionen_uebernehmen(z2, _wachen())
        self.assertEqual(u2.gestellte_stops, [])

    def test_oco_stop_wird_erkannt(self):
        """Ein OCO-Auftrag (ordType=oco) mit slTriggerPx zaehlt als Schutz.

        ANLASS (T-278, 01.10.2026): Beim Uebernehmen von Hand-Positionen
        standen fuer ZEC und ADA langst OCOs an der Boerse. Die Pruefung
        fragte nur 'conditional' und meldete 'Stop fehlt' - es wurde ein
        zweiter Stop daneben gestellt.
        """
        z = self._z()
        with _Umgebung([_boerse(BZ, 1467)],
                       vorhandener_stop=[{"ordType": "oco", "slTriggerPx": "96.62"}]) as u:
            h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(u.gestellte_stops, [])

    def test_move_order_stop_wird_erkannt(self):
        """Ein Trailing-Stop (ordType=move_order_stop) mit moveTriggerPx zaehlt.

        ANLASS (T-278, zweite Haelfte, 01.10.2026): Ein Trailing-Stop fuehrt
        KEIN slTriggerPx, sondern moveTriggerPx + callbackRatio. Wer nur
        slTriggerPx liest, haelt eine geschuetzte Position fuer nackt.
        """
        z = self._z()
        with _Umgebung([_boerse(BZ, 1467)],
                       vorhandener_stop=[{"ordType": "move_order_stop",
                                          "moveTriggerPx": "96.62"}]) as u:
            h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(u.gestellte_stops, [])

    def test_nackter_trigger_zaehlt_nicht(self):
        """Ein nackter trigger (weder slTriggerPx noch moveTriggerPx) ist kein Stop.

        Ein trigger kann auch ein Einstieg sein - er zaehlt nur, wenn er
        einen Ausloesepreis fuehrt.
        """
        z = self._z()
        with _Umgebung([_boerse(BZ, 1467)],
                       vorhandener_stop=[{"ordType": "trigger"}]) as u:
            h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(len(u.gestellte_stops), 1)  # Stop wird gestellt

    def test_vorschau_zeigt_ohne_zu_schreiben(self):
        z = self._z()
        with _Umgebung([_boerse(BZ, 1467)]) as u:
            n = h.bueche_fremde_positionen_uebernehmen(z, _wachen(), still=True)
        self.assertEqual(n, 1)                            # gezaehlt ...
        self.assertEqual(u.journal, [])                   # ... aber nichts gebucht
        self.assertEqual(u.gestellte_stops, [])           # ... und kein Stop gestellt

    def test_beide_richtungen_vertragen_sich(self):
        """Uebernahme und Geisterpruefung duerfen sich nicht widersprechen."""
        z = self._z(positionen=[{"inst": CL, "modus": "live", "kontrakte": 10.0,
                                 "ord_id": "1", "einstieg": 90.0}])
        with _Umgebung([_boerse(BZ, 1467), _boerse(CL, 133)]) as u:
            n = h.bueche_fremde_positionen_uebernehmen(z, _wachen())
        self.assertEqual(n, 1)                            # nur BZ ist neu
        self.assertEqual({p["inst"] for p in z["positionen"]}, {BZ, CL})
        # BZ ist neu und ohne Stop -> genau EIN Stop; CL bleibt unberuehrt.
        self.assertEqual([a[0] for a, _ in u.gestellte_stops], [BZ])
        self.assertEqual(len(u.journal), 1)


# --- Modulwaechter -----------------------------------------------------------

_VORHER = {p.name: p.stat().st_size for p in SPUR.iterdir() if p.is_file()}


def tearDownModule():
    nachher = {p.name: p.stat().st_size for p in SPUR.iterdir() if p.is_file()}
    neu = set(nachher) - set(_VORHER)
    weg = set(_VORHER) - set(nachher)
    geaendert = {n for n in set(_VORHER) & set(nachher) if _VORHER[n] != nachher[n]}
    assert not (neu or weg or geaendert), (
        "Tests haben in den echten Spurenordner geschrieben: neu=%s weg=%s geaendert=%s"
        % (sorted(neu), sorted(weg), sorted(geaendert)))


if __name__ == "__main__":
    unittest.main()