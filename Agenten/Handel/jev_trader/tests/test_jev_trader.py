"""Tests fuer die jev_trader-Papier-Spur.

Synthetische Daten - der echte 50-MB-Log wird in Tests NIE gelesen. Geprueft
wird: (a) Roundtrip-Rekonstruktion aus dem position-Feld, (b) Idempotenz des
Journals, (c) Journal-Format, (d) Auswertung.

Lauf (aus dem jev_trader-Ordner):
    ../scanner/.venv/Scripts/python.exe -m unittest discover -s tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))

import einlesen  # noqa: E402


def _event(block, ts, side, size, entry, mid, realized):
    """Ein Block-Event im Format des echten Logs (nur die relevanten Felder)."""
    return {
        "block": block, "ts": ts, "mid": mid,
        "position": {"side": side, "size": size,
                     "entryPrice": entry if side != "flat" else None},
        "totals": {"realizedUsd": realized},
    }


def _zeile(e):
    return json.dumps(e)


class RekonstruktionTest(unittest.TestCase):
    """(a) Roundtrips aus dem position-Feld korrekt rekonstruieren."""

    def test_flat_zu_long_zu_flat(self):
        # flat -> long (Einstieg) -> long skaliert -> flat (Schluss)
        zeilen = [
            _zeile(_event(1, 1000, "flat", 0, None, 0.10, 0.0)),
            _zeile(_event(2, 2000, "long", 10, 0.10, 0.10, 0.0)),
            _zeile(_event(3, 3000, "long", 20, 0.10, 0.12, 0.0)),   # skaliert
            _zeile(_event(4, 4000, "flat", 0, None, 0.12, 0.20)),   # Schluss
        ]
        runden = einlesen.zeilen_eines_events(zeilen)
        self.assertEqual(len(runden), 1)
        r = runden[0]
        self.assertEqual(r["side"], "long")
        self.assertEqual(r["einstieg"], 0.10)
        self.assertEqual(r["ausstieg"], 0.12)
        self.assertEqual(r["gv_usd"], 0.20)          # realized-Delta
        self.assertEqual(r["ausgang"], "ziel")       # Kurs stieg
        self.assertEqual(r["haltetage"], (4000 - 2000) / 86400.0)

    def test_long_zu_short_ist_ein_schluss_und_ein_neuer_einstieg(self):
        # long -> short (Dreh): das long-Bein schliesst, ein short-Bein oeffnet.
        zeilen = [
            _zeile(_event(1, 1000, "flat", 0, None, 0.10, 0.0)),
            _zeile(_event(2, 2000, "long", 10, 0.10, 0.10, 0.0)),
            _zeile(_event(3, 3000, "short", 10, 0.10, 0.08, 0.30)),  # Dreh
            _zeile(_event(4, 4000, "flat", 0, None, 0.08, 0.30)),   # short zu
        ]
        runden = einlesen.zeilen_eines_events(zeilen)
        self.assertEqual(len(runden), 2)
        # long-Bein: schloss beim Dreh, Kurs fiel -> stop
        self.assertEqual(runden[0]["side"], "long")
        self.assertEqual(runden[0]["ausgang"], "stop")
        self.assertEqual(runden[0]["gv_usd"], 0.30)
        # short-Bein: oeffnete beim Dreh, schloss flat
        self.assertEqual(runden[1]["side"], "short")
        self.assertEqual(runden[1]["einstieg"], 0.10)
        self.assertEqual(runden[1]["gv_usd"], 0.0)

    def test_skalieren_erzeugt_keine_runde(self):
        # Nur Groessenwechsel innerhalb derselben Seite: kein Roundtrip.
        zeilen = [
            _zeile(_event(1, 1000, "flat", 0, None, 0.10, 0.0)),
            _zeile(_event(2, 2000, "short", 5, 0.10, 0.10, 0.0)),
            _zeile(_event(3, 3000, "short", 8, 0.10, 0.09, 0.0)),   # skaliert
            _zeile(_event(4, 4000, "short", 3, 0.10, 0.11, 0.0)),   # skaliert
        ]
        runden = einlesen.zeilen_eines_events(zeilen)
        self.assertEqual(len(runden), 0)   # nichts geschlossen

    def test_kaputte_zeile_wird_uebersprungen(self):
        zeilen = [
            _zeile(_event(1, 1000, "flat", 0, None, 0.10, 0.0)),
            "kein-json{",
            _zeile(_event(2, 2000, "long", 10, 0.10, 0.10, 0.0)),
            _zeile(_event(3, 3000, "flat", 0, None, 0.11, 0.10)),
        ]
        runden = einlesen.zeilen_eines_events(zeilen)
        self.assertEqual(len(runden), 1)
        self.assertEqual(runden[0]["gv_usd"], 0.10)

    def test_offenes_bein_am_ende_zaehlt_nicht(self):
        # Ein Bein, das am Log-Ende noch offen ist, ist KEINE geschlossene Runde.
        zeilen = [
            _zeile(_event(1, 1000, "flat", 0, None, 0.10, 0.0)),
            _zeile(_event(2, 2000, "long", 10, 0.10, 0.10, 0.0)),
        ]
        runden = einlesen.zeilen_eines_events(zeilen)
        self.assertEqual(len(runden), 0)


class JournalFormatTest(unittest.TestCase):
    """(c) Das Journal hat das richtige Kopf-/Zeilenformat."""

    def test_kopf_und_zeile(self):
        r = {"side": "long", "open_ts": 1000, "close_ts": 2000,
             "einstieg": 0.10, "ausstieg": 0.12, "gv_usd": 0.20,
             "ausgang": "ziel", "haltetage": 0.0116}
        zeile = einlesen.journal_zeile(r)
        self.assertEqual(len(zeile), 13)
        # Spaltenreihenfolge wie im Haus-Schema (orb/handelsjournal.csv)
        self.assertEqual(zeile[0], "1970-01-01T00:00:02+00:00")  # zeit
        self.assertEqual(zeile[1], "JEV_TRADER")                 # inst
        self.assertEqual(zeile[2], "long")                       # richtung
        self.assertEqual(zeile[3], "0.100000")                   # einstieg
        self.assertEqual(zeile[6], "ziel")                       # ausgang
        self.assertEqual(zeile[7], "0.120000")                   # ausstieg
        self.assertEqual(zeile[9], "0.200000")                   # gv_usd


class IdempotenzTest(unittest.TestCase):
    """(b) Zweimal laufen bucht keine doppelten Zeilen."""

    def _schreibe_log(self, pfad):
        zeilen = [
            _zeile(_event(1, 1000, "flat", 0, None, 0.10, 0.0)),
            _zeile(_event(2, 2000, "long", 10, 0.10, 0.10, 0.0)),
            _zeile(_event(3, 3000, "flat", 0, None, 0.12, 0.20)),
        ]
        pfad.write_text("\n".join(zeilen) + "\n", encoding="utf-8")

    def test_zweiter_lauf_haengt_nichts_an(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            log = tmp / "events.jsonl"
            self._schreibe_log(log)
            journal = tmp / "handelsjournal.csv"

            import handeln
            # Wachen-Ersatz: quelle zeigt auf das synthetische Log.
            w = {"quelle": str(log), "journal_zweitziel": None}
            # Journal in den temp-Ordner umlenken (nicht das echte anfassen).
            handeln.JOURNAL = journal

            # Erster Lauf: 1 Runde buchen.
            z1 = {"letzte_runde_ts": None}
            anzahl1 = handeln.buch_runden(
                handeln.rekonstruiere(w), z1)
            self.assertEqual(anzahl1, 1)
            self.assertEqual(z1["letzte_runde_ts"], 3000)

            # Zweiter Lauf ueber dieselbe Datei: nichts Neues.
            z2 = dict(z1)
            anzahl2 = handeln.buch_runden(
                handeln.rekonstruiere(w), z2)
            self.assertEqual(anzahl2, 0)
            self.assertEqual(z2["letzte_runde_ts"], 3000)


class AuswertungTest(unittest.TestCase):
    """(d) Auswertung rechnet Runden/Treffer/Ergebnis aus einem bekannten Buch."""

    def test_kennzahlen_aus_bekanntem_journal(self):
        import auswertung
        zeilen = [
            {"zeit": "2026-10-01T00:00:00+00:00", "richtung": "long",
             "einstieg": "0.10", "ausstieg": "0.12", "ausgang": "ziel",
             "gv_usd": "0.20", "haltetage": "0.01"},
            {"zeit": "2026-10-02T00:00:00+00:00", "richtung": "short",
             "einstieg": "0.12", "ausstieg": "0.10", "ausgang": "stop",
             "gv_usd": "-0.10", "haltetage": "0.02"},
            {"zeit": "2026-10-03T00:00:00+00:00", "richtung": "long",
             "einstieg": "0.10", "ausstieg": "0.11", "ausgang": "ziel",
             "gv_usd": "0.05", "haltetage": "0.03"},
        ]
        runden = auswertung.runden_aus_journal(zeilen)
        k = auswertung.kennzahlen(runden)
        self.assertEqual(k["n"], 3)
        self.assertAlmostEqual(k["ergebnis"], 0.15)      # 0.20 - 0.10 + 0.05
        self.assertAlmostEqual(k["ev"], 0.05)            # 0.15 / 3
        self.assertEqual(k["treffer"], 2)                # 0.20 und 0.05
        self.assertAlmostEqual(k["treffer_pct"], 66.6667, places=3)
        self.assertAlmostEqual(k["best"], 0.20)
        self.assertAlmostEqual(k["schlecht"], -0.10)
        self.assertEqual(k["gruende"], {"ziel": 2, "stop": 1})

    def test_leeres_journal_gibt_none(self):
        import auswertung
        self.assertIsNone(auswertung.kennzahlen([]))


if __name__ == "__main__":
    unittest.main()
