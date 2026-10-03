"""Tests der Spur robinhood_radar - offline, ohne Netz, ohne echte Dateien.

Der Modulwaechter am Ende merkt die Dateiliste und Groessen des ECHTEN
Spurordners vor dem Testlauf und vergleicht danach. So faellt jeder Test auf,
der nach draussen schreibt (die Lehre vom 16.09.2026: Tests, die eine Funktion
mit Journalaufruf direkt pruefen, schreiben sonst in das echte Buch).
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(SPUR)
# Reihenfolge: eigene Spur ZULETZT, sonst gewinnt ein gleichnamiges Modul.
for _p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

import handeln                                                     # noqa: E402
import lesen                                                       # noqa: E402
import spur_buch                                                   # noqa: E402

assert handeln.__file__.startswith(SPUR), handeln.__file__

JETZT = time.time()


def datenbank(pfad: str, traders=None, trades=None) -> None:
    """Eine Radar-Datenbank im Kleinen: nur die Spalten, die gelesen werden."""
    con = sqlite3.connect(pfad)
    con.execute("DROP TABLE IF EXISTS traders")
    con.execute("DROP TABLE IF EXISTS trades")
    con.execute("CREATE TABLE traders (address TEXT, chain TEXT, score REAL,"
                " status TEXT)")
    con.execute("CREATE TABLE trades (sig TEXT, address TEXT, mint TEXT,"
                " side TEXT, token_amount REAL, usd_value REAL, ts REAL,"
                " chain TEXT)")
    for t in (traders or []):
        con.execute("INSERT INTO traders VALUES (?,?,?,?)", t)
    for t in (trades or []):
        con.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?)", t)
    con.commit()
    con.close()


def wachen(**abweichend) -> dict:
    w = json.loads(Path(SPUR, "wachen.json").read_text(encoding="utf-8"))
    w.update(abweichend)
    return w


def kauf(wallet, mint, usd, menge, ts, score=None, status=None,
         chain="robinhood", side="buy"):
    """Eine Kaufzeile in der Form, die lesen.kaeufe() liefert."""
    return {"sig": "sig-%s-%s-%d" % (wallet[-4:], mint[-5:], int(ts)),
            "wallet": wallet, "mint": mint, "usd": usd, "menge": menge,
            "ts": ts, "chain": chain, "score": score, "status": status,
            "side": side}


def zeile(k) -> tuple:
    """Dieselbe Zeile als SQL-Satz fuer die Testdatenbank."""
    return (k["sig"], k["wallet"], k["mint"], k["side"], k["menge"], k["usd"],
            k["ts"], k["chain"])


class KennzahlenTest(unittest.TestCase):
    """Die Auswahlregel - reine Rechnung, keine Datei, kein Netz."""

    def setUp(self):
        self.w = wachen()

    def test_zwei_bewertete_kaeufer_ergeben_einen_kandidaten(self):
        handeln.verkaufsdruck = {}
        handeln.kaeufe = [
            kauf("0xaaa", "0xmint1", 1000.0, 500.0, JETZT - 600),
            kauf("0xbbb", "0xmint1", 2000.0, 1000.0, JETZT - 300),
        ]
        trader = {"0xaaa": 70.0, "0xbbb": 80.0}
        for k in handeln.kaeufe:
            k["score"] = trader[k["wallet"]]
            k["status"] = "active"
        daten, kurse = handeln._kennzahlen(self.w, JETZT)
        self.assertIn("0xmint1", daten)
        self.assertEqual(daten["0xmint1"]["anzahl_kaeufer"], 2)
        self.assertEqual(daten["0xmint1"]["bester_score"], 80.0)
        self.assertIn("0xmint1", kurse)

    def test_ein_kaeufer_reicht_nicht(self):
        handeln.verkaufsdruck = {}
        handeln.kaeufe = [dict(kauf("0xaaa", "0xmint1", 1000.0, 500.0,
                                    JETZT - 600), score=90.0, status="active")]
        daten, _ = handeln._kennzahlen(self.w, JETZT)
        self.assertNotIn("0xmint1", daten)
        self.assertEqual(handeln._zyklus["ablehnung"]["zu wenige bewertete Kaeufer"], 1)

    def test_unbewertet_zaehlt_wie_unbekannt_nicht_mit(self):
        handeln.verkaufsdruck = {}
        handeln.kaeufe = [
            dict(kauf("0xaaa", "0xmint1", 1000.0, 500.0, JETZT - 600),
                 score=None, status="tracking"),
            dict(kauf("0xbbb", "0xmint1", 1000.0, 500.0, JETZT - 300),
                 score=90.0, status="active"),
        ]
        daten, _ = handeln._kennzahlen(self.w, JETZT)
        self.assertNotIn("0xmint1", daten)

    def test_zu_schwacher_score_reicht_nicht(self):
        handeln.verkaufsdruck = {}
        handeln.kaeufe = [
            dict(kauf("0xaaa", "0xmint1", 1000.0, 500.0, JETZT - 600),
                 score=40.0, status="active"),
            dict(kauf("0xbbb", "0xmint1", 1000.0, 500.0, JETZT - 300),
                 score=35.0, status="active"),
        ]
        daten, _ = handeln._kennzahlen(self.w, JETZT)
        self.assertNotIn("0xmint1", daten)

    def test_alter_kauf_ausserhalb_des_fensters_zaehlt_nicht(self):
        handeln.verkaufsdruck = {}
        alt = JETZT - 7 * 3600.0               # Fenster ist 6 h
        handeln.kaeufe = [
            dict(kauf("0xaaa", "0xmint1", 1000.0, 500.0, alt),
                 score=90.0, status="active"),
            dict(kauf("0xbbb", "0xmint1", 1000.0, 500.0, JETZT - 300),
                 score=90.0, status="active"),
        ]
        daten, _ = handeln._kennzahlen(self.w, JETZT)
        self.assertNotIn("0xmint1", daten)

    def test_verkaufsdruck_der_kohorte_blockt_das_signal(self):
        handeln.kaeufe = [
            dict(kauf("0xaaa", "0xmint1", 1000.0, 500.0, JETZT - 600),
                 score=70.0, status="active"),
            dict(kauf("0xbbb", "0xmint1", 1000.0, 500.0, JETZT - 300),
                 score=80.0, status="active"),
        ]
        handeln.verkaufsdruck = {"0xmint1": 1500.0}      # mehr verkauft als gekauft
        daten, _ = handeln._kennzahlen(self.w, JETZT)
        self.assertNotIn("0xmint1", daten)
        self.assertEqual(handeln._zyklus["ablehnung"]["Kohorte verkauft selbst"], 1)

    def test_dropped_wallet_zaehlt_nicht(self):
        handeln.verkaufsdruck = {}
        handeln.kaeufe = [
            dict(kauf("0xaaa", "0xmint1", 1000.0, 500.0, JETZT - 600),
                 score=70.0, status="dropped"),
            dict(kauf("0xbbb", "0xmint1", 1000.0, 500.0, JETZT - 300),
                 score=80.0, status="active"),
        ]
        daten, _ = handeln._kennzahlen(self.w, JETZT)
        self.assertNotIn("0xmint1", daten)

    def test_einstiegspreis_traegt_den_nachlauf(self):
        handeln.verkaufsdruck = {}
        handeln.kaeufe = [
            dict(kauf("0xaaa", "0xmint1", 100.0, 50.0, JETZT - 600),
                 score=70.0, status="active"),
            dict(kauf("0xbbb", "0xmint1", 100.0, 50.0, JETZT - 300),
                 score=80.0, status="active"),
        ]
        daten, kurse = handeln._kennzahlen(self.w, JETZT)
        # Preis des juengsten Kaufs 100/50 = 2,00 USD, mit 2 % Nachlauf.
        self.assertAlmostEqual(kurse["0xmint1"], 2.0 * 1.02, places=6)
        self.assertAlmostEqual(daten["0xmint1"]["preis"], 2.0 * 1.02, places=6)

    def test_nur_der_staerkste_kandidat_bekommt_ein_signal(self):
        handeln.verkaufsdruck = {}
        handeln.kaeufe = [
            dict(kauf("0xaaa", "0xklein", 100.0, 50.0, JETZT - 600),
                 score=70.0, status="active"),
            dict(kauf("0xbbb", "0xklein", 100.0, 50.0, JETZT - 300),
                 score=70.0, status="active"),
            dict(kauf("0xccc", "0xgross", 9000.0, 100.0, JETZT - 600),
                 score=95.0, status="active"),
            dict(kauf("0xddd", "0xgross", 9000.0, 100.0, JETZT - 300),
                 score=95.0, status="active"),
        ]
        daten, _ = handeln._kennzahlen(self.w, JETZT)
        self.assertEqual(handeln.signal(daten["0xklein"], self.w), None)
        self.assertEqual(handeln.signal(daten["0xgross"], self.w), "long")
        # Ein zweites Signal im selben Zyklus gibt es nicht.
        self.assertEqual(handeln.signal(daten["0xgross"], self.w), None)


class LesenTest(unittest.TestCase):
    """Der Leser darf nur lesen."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="radar_lesen_")
        self.db = os.path.join(self.dir, "fomo_agent.db")
        datenbank(self.db)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_schreiben_wird_verweigert(self):
        con = lesen.verbinde(self.db)
        try:
            with self.assertRaises(RuntimeError):
                lesen.anweisung(con, "INSERT INTO trades (sig) VALUES ('x')")
            with self.assertRaises(RuntimeError):
                lesen.anweisung(con, "DELETE FROM trades")
        finally:
            con.close()

    def test_fehlende_datenbank_wird_gemeldet(self):
        with self.assertRaises(lesen.DatenbankFehlt):
            lesen.verbinde(os.path.join(self.dir, "gibtsnicht.db"))

    def test_kaeufe_liest_mit_score(self):
        jetzt = time.time()
        k = kauf("0xaaa", "0xmint1", 500.0, 250.0, jetzt - 60)
        datenbank(self.db, traders=[("0xaaa", "robinhood", 88.0, "active")],
                  trades=[zeile(k)])
        con = lesen.verbinde(self.db)
        try:
            zeilen = lesen.kaeufe(con, jetzt - 3600)
            self.assertEqual(len(zeilen), 1)
            self.assertEqual(zeilen[0]["score"], 88.0)
            self.assertEqual(zeilen[0]["mint"], "0xmint1")
            self.assertEqual(lesen.verkaufsdruck(con, jetzt - 3600), {})
        finally:
            con.close()


class ZyklusTest(unittest.TestCase):
    """Ein echter Papierzyklus, aber auf Temp-Pfaden - nie im echten Buch."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="radar_zyklus_")
        self.ziel = os.path.join(self.dir, "Q-Ziel")
        os.makedirs(self.ziel, exist_ok=True)
        self.db = os.path.join(self.dir, "fomo_agent.db")
        jetzt = time.time()
        datenbank(
            self.db,
            traders=[("0xaaa", "robinhood", 80.0, "active"),
                     ("0xbbb", "robinhood", 90.0, "active")],
            trades=[zeile(kauf("0xaaa", "0xmint1", 400.0, 200.0, jetzt - 600)),
                    zeile(kauf("0xbbb", "0xmint1", 400.0, 200.0, jetzt - 300))])
        w = wachen(journal_zweitziel=self.ziel, handel_erlaubt=False,
                   freigabe={"erfuellt": False})
        Path(self.dir, "wachen.json").write_text(json.dumps(w), encoding="utf-8")
        Path(self.dir, "zustand.json").write_text("{}", encoding="utf-8")
        os.environ["FOMO_RADAR_DB"] = self.db
        handeln.datenquelle = None

    def tearDown(self):
        os.environ.pop("FOMO_RADAR_DB", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_papierzyklus_bucht_eine_position_und_spiegelt_in_den_temp_ordner(self):
        rc = spur_buch.zyklus(self.dir, handeln.quelle, handeln.signal, "papier",
                              ereignis_name="handel/robinhood_radar")
        self.assertEqual(rc, 0)
        journal = Path(self.dir, "handelsjournal.csv")
        self.assertTrue(journal.exists(), "kein Journal geschrieben")
        text = journal.read_text(encoding="utf-8")
        self.assertIn("0xmint1", text)
        self.assertIn("kauf", text)
        zustand = json.loads(Path(self.dir, "zustand.json").read_text(encoding="utf-8"))
        self.assertEqual(len(zustand.get("positionen", [])), 1)
        p = zustand["positionen"][0]
        self.assertEqual(p["seite"], "long")
        self.assertAlmostEqual(p["einstieg"], 2.0 * 1.02, places=6)
        self.assertEqual(p["modus"], "papier")
        # Bedingung 4: die Kopie ausser Haus liegt im TEMP-Ziel.
        self.assertTrue(list(Path(self.ziel).glob("*")))

    def test_vorschau_schreibt_nichts(self):
        journal = Path(self.dir, "handelsjournal.csv")
        rc = spur_buch.zyklus(self.dir, handeln.quelle, handeln.signal,
                              "vorschau", ereignis_name="handel/robinhood_radar")
        self.assertEqual(rc, 0)
        self.assertFalse(journal.exists(), "die Vorschau hat geschrieben")
        zustand = json.loads(Path(self.dir, "zustand.json").read_text(encoding="utf-8"))
        self.assertEqual(zustand.get("positionen", []), [])

    def test_live_ist_gesperrt_und_handelt_papier(self):
        # Die ausgelieferte wachen.json der Spur erlaubt kein Live.
        echt = json.loads(Path(SPUR, "wachen.json").read_text(encoding="utf-8"))
        self.assertFalse(echt.get("handel_erlaubt"))
        self.assertFalse((echt.get("freigabe") or {}).get("erfuellt"))
        rc = spur_buch.zyklus(self.dir, handeln.quelle, handeln.signal, "live",
                              ereignis_name="handel/robinhood_radar")
        self.assertEqual(rc, 0)
        zustand = json.loads(Path(self.dir, "zustand.json").read_text(encoding="utf-8"))
        for p in zustand.get("positionen", []):
            self.assertEqual(p.get("modus"), "papier")


class RaeumTest(unittest.TestCase):
    """T-299: eine Position ohne frischen Kurs darf nicht ewig stehen.

    Die Kette liefert fuer einen Token nur dann einen Preis, wenn er
    gehandelt wurde. Ohne Rueumung bleibt die Position im Buch, wird von
    `pruefe_ausstiege` uebersprungen und blockiert einen der drei Plaetze.
    """

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="radar_raeum_")
        self.ziel = os.path.join(self.dir, "Q-Ziel")
        os.makedirs(self.ziel, exist_ok=True)
        self.db = os.path.join(self.dir, "fomo_agent.db")
        jetzt = time.time()
        self.jetzt = jetzt
        # 0xfrisch: vor 2 h beobachtet -> bleibt. 0xalt: vor 100 h -> wird geraeumt.
        # 0xnie: gar keine Fuellung -> wird neutral geraeumt.
        datenbank(
            self.db,
            traders=[("0xaaa", "robinhood", 80.0, "active")],
            trades=[zeile(kauf("0xaaa", "0xfrisch", 400.0, 200.0, jetzt - 7200)),
                    zeile(kauf("0xaaa", "0xalt", 1000.0, 500.0, jetzt - 100 * 3600))])
        w = wachen(journal_zweitziel=self.ziel, handel_erlaubt=False,
                   freigabe={"erfuellt": False},
                   beobachtung_max_alter_stunden=24.0)
        Path(self.dir, "wachen.json").write_text(json.dumps(w), encoding="utf-8")
        Path(self.dir, "zustand.json").write_text(json.dumps({
            "positionen": [
                {"inst": "0xfrisch", "seite": "long", "einstieg": 2.0,
                 "stop": 1.5, "ziel": 3.0, "stop_pct": 25.0, "nominal": 20.0,
                 "modus": "papier", "eroeffnet_zeit": "2026-10-02T00:00:00+00:00",
                 "pos_id": "p-frisch"},
                {"inst": "0xalt", "seite": "long", "einstieg": 2.0,
                 "stop": 1.5, "ziel": 3.0, "stop_pct": 25.0, "nominal": 20.0,
                 "modus": "papier", "eroeffnet_zeit": "2026-09-22T00:00:00+00:00",
                 "pos_id": "p-alt"},
                {"inst": "0xnie", "seite": "long", "einstieg": 2.0,
                 "stop": 1.5, "ziel": 3.0, "stop_pct": 25.0, "nominal": 20.0,
                 "modus": "papier", "eroeffnet_zeit": "2026-09-22T00:00:00+00:00",
                 "pos_id": "p-nie"},
            ], "modus": "papier", "letzter_lauf": None, "verlust_usd": 0.0}),
            encoding="utf-8")
        os.environ["FOMO_RADAR_DB"] = self.db

    def tearDown(self):
        os.environ.pop("FOMO_RADAR_DB", None)
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_nur_die_zu_alten_und_die_unbeobachteten_werden_geraeumt(self):
        w = json.loads(Path(self.dir, "wachen.json").read_text(encoding="utf-8"))
        geraeumt, befund, fehler = handeln.raeume_ohne_kurs(
            w, ordner=self.dir, jetzt_ts=self.jetzt)
        self.assertEqual(fehler, [])
        self.assertEqual(sorted(geraeumt), ["0xalt", "0xnie"])
        z = json.loads(Path(self.dir, "zustand.json").read_text(encoding="utf-8"))
        self.assertEqual([p["inst"] for p in z["positionen"]], ["0xfrisch"])
        # Der Zustand traegt die Position als GERAEUMT, damit die Zentrale
        # nicht weiter eine offene Position ohne Kurs zeigt.
        text = Path(self.dir, "handelsjournal.csv").read_text(encoding="utf-8")
        self.assertIn("buchbereinigung_kein_kurs", text)
        self.assertEqual(text.count("buchbereinigung_kein_kurs"), 2)

    def test_die_geraeumten_zaehlen_nicht_als_handelsrunde(self):
        import stoerungen
        w = json.loads(Path(self.dir, "wachen.json").read_text(encoding="utf-8"))
        handeln.raeume_ohne_kurs(w, ordner=self.dir, jetzt_ts=self.jetzt)
        with open(os.path.join(self.dir, "handelsjournal.csv"), encoding="utf-8") as f:
            zeilen = list(csv.DictReader(f))
        ausstiege = [z for z in zeilen if z["aktion"] == "verkauf"]
        self.assertTrue(ausstiege)
        echt, stoer = stoerungen.teile_runden(
            [{"grund": z["grund"]} for z in ausstiege])
        self.assertEqual(len(echt), 0, "eine Buchbereinigung ist keine Runde")
        self.assertEqual(len(stoer), len(ausstiege))

    def test_der_geraeumte_preis_ist_der_letzte_beobachtete_handel(self):
        w = json.loads(Path(self.dir, "wachen.json").read_text(encoding="utf-8"))
        _geraeumt, befund, _fehler = handeln.raeume_ohne_kurs(
            w, ordner=self.dir, jetzt_ts=self.jetzt)
        preis = dict((i, p) for i, p, _a in befund)
        # 1000 USD / 500 Token = 2.0 - der Kurs, zu dem zuletzt gehandelt wurde.
        self.assertAlmostEqual(preis["0xalt"], 2.0, places=9)
        # Ohne jede Fuellung neutral zum Einstieg.
        self.assertAlmostEqual(preis["0xnie"], 2.0, places=9)

    def test_leeres_buch_ist_ein_fall_fuer_sich(self):
        Path(self.dir, "zustand.json").write_text('{"positionen": []}',
                                                  encoding="utf-8")
        w = json.loads(Path(self.dir, "wachen.json").read_text(encoding="utf-8"))
        geraeumt, befund, fehler = handeln.raeume_ohne_kurs(
            w, ordner=self.dir, jetzt_ts=self.jetzt)
        self.assertEqual((geraeumt, befund, fehler), ([], [], []))
        self.assertFalse(Path(self.dir, "handelsjournal.csv").exists())

    def test_quelle_liefert_den_kurs_einer_offenen_position(self):
        """T-299, zweite Haelfte: die laufende Pruefung braucht denselben Preis."""
        z = json.loads(Path(self.dir, "zustand.json").read_text(encoding="utf-8"))
        z["positionen"] = [p for p in z["positionen"] if p["inst"] == "0xfrisch"]
        Path(self.dir, "zustand.json").write_text(json.dumps(z), encoding="utf-8")
        w = json.loads(Path(self.dir, "wachen.json").read_text(encoding="utf-8"))
        alt = handeln.HIER
        handeln.HIER = self.dir
        try:
            daten, kurse, fehler = handeln.quelle(w)
        finally:
            handeln.HIER = alt
        self.assertEqual(fehler, [])
        # 400 USD / 200 Token = 2.0
        self.assertAlmostEqual(kurse["0xfrisch"], 2.0, places=9)
        # Der Kurs gehoert in `kurse`, NICHT in `daten` - er darf keinen
        # neuen Einstieg ausloesen.
        self.assertNotIn("0xfrisch", daten)


def _stand(ordner: str) -> dict:
    stand = {}
    for name in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, name)
        if os.path.isfile(p):
            stand[name] = os.path.getsize(p)
    return stand


_VORHER = _stand(SPUR)


def tearDownModule():
    nachher = _stand(SPUR)
    neu = {k: v for k, v in nachher.items() if k not in _VORHER}
    geaendert = {k: (v, nachher[k]) for k, v in _VORHER.items()
                 if k in nachher and nachher[k] != v}
    assert not neu and not geaendert, (
        "Die Tests haben in den ECHTEN Spurordner geschrieben: neu=%s geaendert=%s"
        % (neu, geaendert))


class NachlaufMessungTest(unittest.TestCase):
    """T-268: der Nachlauf auf der eigenen Sammlung - rein rechnend.

    Nur die reine Funktion: die echte Messung (handeln.messen) schreibt
    daten/messung.json in den ECHTEN Spurordner und wuerde vom Modulwaechter
    zu Recht als Schreibzugriff gemeldet.
    """

    def test_naechster_handel_setzt_den_nachlauf(self):
        fills = [{"mint": "M", "wallet": "W", "seite": "buy", "preis": 1.0,
                  "ts": 100.0},
                 {"mint": "M", "wallet": "V", "seite": "sell", "preis": 1.1,
                  "ts": 160.0}]
        aus = handeln.nachlauf_messen(fills)
        self.assertEqual(len(aus), 1)
        self.assertAlmostEqual(aus[0]["nachlauf_pct"], 10.0, places=6)
        self.assertAlmostEqual(aus[0]["abstand_s"], 60.0, places=6)

    def test_kauf_ohne_naechste_beobachtung_zaehlt_nicht(self):
        fills = [{"mint": "M", "wallet": "W", "seite": "buy", "preis": 1.0,
                  "ts": 100.0}]
        self.assertEqual(handeln.nachlauf_messen(fills), [])

    def test_ein_verkauf_ist_kein_ausloeser(self):
        fills = [{"mint": "M", "wallet": "W", "seite": "sell", "preis": 1.0,
                  "ts": 1.0},
                 {"mint": "M", "wallet": "W", "seite": "sell", "preis": 2.0,
                  "ts": 2.0}]
        self.assertEqual(handeln.nachlauf_messen(fills), [])

    def test_trigger_filter_nimmt_nur_die_signal_tokens(self):
        fills = [{"mint": "A", "wallet": "W", "seite": "buy", "preis": 1.0,
                  "ts": 1.0},
                 {"mint": "A", "wallet": "W", "seite": "buy", "preis": 1.2,
                  "ts": 2.0},
                 {"mint": "B", "wallet": "W", "seite": "buy", "preis": 1.0,
                  "ts": 1.0},
                 {"mint": "B", "wallet": "W", "seite": "buy", "preis": 1.2,
                  "ts": 2.0}]
        aus = handeln.nachlauf_messen(fills, trigger_ts={"A"})
        self.assertEqual({x["mint"] for x in aus}, {"A"})
        # Der letzte Kauf eines Tokens hat keine naechste Beobachtung mehr.
        self.assertEqual(len(aus), 1)

    def test_verteilung_meldet_die_raender_nicht_nur_den_schnitt(self):
        v = handeln._verteilung([-80.0, -10.0, 0.0, 30.0])
        self.assertEqual((v["min"], v["max"]), (-80.0, 30.0))
        self.assertAlmostEqual(v["median"], -5.0, places=6)
        self.assertIsNone(handeln._verteilung([]))


if __name__ == "__main__":
    unittest.main()