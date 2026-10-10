"""Tests fuer Agenten/Werkzeuge/breite.py - die REIHE, nicht die Tageszahl.

OHNE NETZ: geprueft werden `merken` (eine Zeile je Kerzentag), `reihe`,
`verlauf` (Veraenderung in Punkten), `fenster_von`, `reihe_rechnen`
(Nachrechnung), `kennzahlen`, `serie_ueber` und `vorwaerts`. `messen()` wird
NICHT gerufen - ein Test, der die echte Breite prueft, waere jeden Tag rot oder
gruen, ohne dass sich etwas geaendert haette. `fuellen()` wird gerufen, aber mit
gefaelschtem `hole` - die Naht ist das Modulattribut.

Die Naht ist das Modulattribut `REIHE`: der Test biegt es auf einen Temp-Ordner
um. Zusaetzlich merkt sich der Test Groesse und Aenderungszeit der ECHTEN Reihe
und prueft am Ende, dass sie unberuehrt ist - ein Test darf nie in den echten
Laufzeitstand schreiben.

Aufruf: python -m unittest discover -s tests -t tests   (aus Agenten/Werkzeuge)
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
WERKZEUG = os.path.join(os.path.dirname(HIER), "breite.py")
TAG = 86400000                                # ein Tag in Millisekunden


def lade():
    spec = importlib.util.spec_from_file_location("breite_werkzeug_test",
                                                  WERKZEUG)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


b = lade()

_echte_reihe = (os.path.getsize(b.REIHE), os.path.getmtime(b.REIHE)) \
    if os.path.exists(b.REIHE) else None


def messung(breite, kerze="2026-09-25", unter=(), ueber=(("BTC-USDT", 84.0),),
            ts="2026-09-25T17:00:00+00:00"):
    """Messung in der Form, die messen() liefert (ohne Netz)."""
    ueber_s = [{"inst": i, "kurs": k, "ema": k / 1.2, "abstand": 20.0}
               for i, k in ueber]
    unter_s = [{"inst": i, "kurs": k, "ema": k * 1.05, "abstand": -5.0}
               for i, k in unter]
    return {
        "ts": ts, "kerze": kerze, "ueber": ueber_s, "unter": unter_s,
        "offen": [], "n_ueber": len(ueber_s),
        "n_gesamt": len(ueber_s) + len(unter_s), "breite": breite,
    }


def tagesreihe(werte, start=0):
    """[(ts_ms, schluss)] aus einer Wertfolge, ein Tag je Wert."""
    return [(TAG * (start + i + 1), float(w)) for i, w in enumerate(werte)]


class ReiheTest(unittest.TestCase):
    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="breite-test-")
        self.echt = b.REIHE
        b.REIHE = os.path.join(self.ordner, "breite-reihe.jsonl")

    def tearDown(self):
        b.REIHE = self.echt
        shutil.rmtree(self.ordner, ignore_errors=True)

    def test_zweite_messung_derselben_kerze_ersetzt(self):
        b.merken(messung(100.0))
        b.merken(messung(96.5))
        zeilen = b.reihe(None)
        self.assertEqual(len(zeilen), 1,
                         "zwei Messungen EINES Kerzentags sind EINE Zeile")
        self.assertEqual(zeilen[0]["breite"], 96.5,
                         "die spaetere Messung gewinnt")

    def test_zwei_kerzen_geben_zwei_zeilen(self):
        b.merken(messung(100.0, kerze="2026-09-24"))
        b.merken(messung(93.0, kerze="2026-09-25"))
        zeilen = b.reihe(None)
        self.assertEqual([z["kerze"] for z in zeilen],
                         ["2026-09-24", "2026-09-25"])

    def test_alte_kerze_wird_an_ihrer_stelle_ersetzt(self):
        b.merken(messung(100.0, kerze="2026-09-24"))
        b.merken(messung(93.0, kerze="2026-09-25"))
        b.merken(messung(88.0, kerze="2026-09-24"))       # Nachlauf
        zeilen = b.reihe(None)
        self.assertEqual([z["kerze"] for z in zeilen],
                         ["2026-09-24", "2026-09-25"],
                         "die Reihe bleibt zeitlich sortiert")
        self.assertEqual(zeilen[0]["breite"], 88.0)

    def test_zeile_traegt_die_abstaende(self):
        b.merken(messung(50.0, ueber=(("BTC-USDT", 84.0),),
                         unter=(("APT-USDT", 0.81),)))
        z = b.reihe(None)[0]
        self.assertEqual(z["abstand"]["BTC-USDT"], 20.0)
        self.assertEqual(z["abstand"]["APT-USDT"], -5.0)
        self.assertEqual(z["unter"], ["APT-USDT"])

    def test_verlauf_rechnet_die_veraenderung(self):
        b.merken(messung(100.0, kerze="2026-09-24"))
        b.merken(messung(91.0, kerze="2026-09-25"))
        tage = b.verlauf()
        self.assertEqual(len(tage), 2)
        self.assertIsNone(tage[0]["delta"], "der erste Tag hat keinen Vorgaenger")
        self.assertEqual(tage[1]["delta"], -9.0)

    def test_verlauf_zaehlt_die_messungen_je_tag(self):
        for wert in (100.0, 99.0, 97.0):
            b.merken(messung(wert))
        tage = b.verlauf()
        self.assertEqual(len(tage), 1)
        self.assertEqual(tage[0]["messungen"], 1,
                         "ersetzt heisst: eine Zeile, nicht drei")

    def test_verlauf_nennt_die_art(self):
        b.merken(messung(100.0, kerze="2026-09-24"))
        with open(b.REIHE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"kerze": "2026-09-25", "breite": 90.0,
                                "art": "nachgerechnet"}) + "\n")
        tage = b.verlauf()
        self.assertEqual([z["art"] for z in tage], ["live", "nachgerechnet"],
                         "eine nachgerechnete Zeile ist als solche erkennbar")

    def test_zeile_ohne_kerze_zaehlt_nicht_als_tag(self):
        with open(b.REIHE, "w", encoding="utf-8") as f:
            f.write(json.dumps(messung(50.0, kerze=None)) + "\n")
        self.assertEqual(b.verlauf(), [])

    def test_kaputte_zeile_killt_die_reihe_nicht(self):
        b.merken(messung(100.0))
        with open(b.REIHE, "a", encoding="utf-8") as f:
            f.write("{kein json\n")
        self.assertEqual(len(b.reihe(None)), 1)

    def test_reihe_ohne_datei_ist_leer(self):
        self.assertEqual(b.reihe(None), [])
        self.assertEqual(b.verlauf(), [])

    def test_live_messung_behaelt_das_nachgerechnete_ergebnis(self):
        with open(b.REIHE, "w", encoding="utf-8") as f:
            f.write(json.dumps({"kerze": "2026-09-25", "breite": 86.21,
                                "art": "nachgerechnet",
                                "nachgerechnet_am":
                                "2026-09-30T05:00:00+00:00"}) + "\n")
        b.merken(messung(86.21))
        z = b.reihe(None)[0]
        self.assertNotIn("art", z, "eine Messung ist keine Nachrechnung")
        self.assertEqual(z["nachgerechnet_alt"]["breite"], 86.21,
                         "der nachgerechnete Wert bleibt als Beleg stehen")
        self.assertEqual(z["nachgerechnet_am"], "2026-09-30T05:00:00+00:00")

    def test_live_ueber_live_traegt_keinen_beleg(self):
        b.merken(messung(100.0))
        b.merken(messung(96.5))
        self.assertNotIn("nachgerechnet_alt", b.reihe(None)[0])

    def test_verlauf_n_grenzt_auf_die_letzten_tage(self):
        for i, k in enumerate(("2026-09-21", "2026-09-22", "2026-09-23")):
            b.merken(messung(100.0 - i, kerze=k))
        self.assertEqual([z["kerze"] for z in b.verlauf(2)],
                         ["2026-09-22", "2026-09-23"])


class FensterTest(unittest.TestCase):
    """Das FENSTER ist die Rechenregel - live und Nachrechnung muessen sie teilen.

    Vorher war das Fenster "was OKX in EINEM Aufruf zurueckgibt" (299 Kerzen).
    Der Startwert der EMA hat darin ein Gewicht von ~37 % - gemessen am
    30.09.2026 ergab das fuer APT-USDT einen Abstand von -1,24 % statt -11,52 %
    (Fenster 600) bzw. -12,18 % (Fenster 1200). Die kurze Reihe war also nicht
    nur ungenauer, sie hat Paare auf die falsche Seite der EMA gestellt.
    """

    def test_fenster_nimmt_die_letzten_n(self):
        r = tagesreihe(range(1000))               # Zeitstempel TAG*1 .. TAG*1000
        s = b.fenster_von(r, 799, fenster=600)
        self.assertEqual(len(s), 600)
        self.assertEqual(s[-1], r[799][1])
        self.assertEqual(s[0], r[200][1], "200 Schritte vor dem Zieltag")

    def test_fenster_kuerzere_geschichte_nimmt_was_da_ist(self):
        r = tagesreihe(range(250))
        s = b.fenster_von(r, 249, fenster=600)
        self.assertEqual(len(s), 250,
                         "kuerzere Geschichte ist kein Fehler, solange LAENGE "
                         "erreicht wird")

    def test_fenster_unter_der_ema_laenge_gibt_none(self):
        r = tagesreihe(range(b.LAENGE - 1))
        self.assertIsNone(b.fenster_von(r, len(r) - 1, fenster=600),
                          "ohne LAENGE Kerzen gibt es keinen Mittelwert")

    def test_fenster_ausserhalb_der_reihe(self):
        r = tagesreihe(range(300))
        self.assertIsNone(b.fenster_von(r, 999))
        self.assertIsNone(b.fenster_von(r, None))

    def test_live_und_nachrechnung_rechnen_dasselbe_fenster(self):
        """Die eine Zusage: der Live-Lauf misst mit DERSELBEN Regel."""
        verlauf = {"AAA-USDT": tagesreihe(range(800, 1600)),
                   "BBB-USDT": tagesreihe(range(1600, 800, -1))}
        gerechnet = b.reihe_rechnen(verlauf, tage=1)
        letzter = sorted(gerechnet)[-1]
        # So rechnet messen(): letzter Index des Verlaufs, fenster_von.
        for inst in verlauf:
            s = b.fenster_von(verlauf[inst], len(verlauf[inst]) - 1)
            kurs, _e, a = b._messe_fenster(s)
            self.assertEqual(gerechnet[letzter]["abstand"][inst], round(a, 2),
                             "%s: Live-Weg und Nachrechnung muessen dasselbe "
                             "Fenster benutzen" % inst)
        self.assertEqual(gerechnet[letzter]["n_gesamt"], 2)
        self.assertEqual(gerechnet[letzter]["n_ueber"], 1,
                         "eines steigt, eines faellt")


class NachrechnenTest(unittest.TestCase):
    def test_alle_steigend_ist_hundert_prozent(self):
        verlauf = {i: tagesreihe(range(800, 1600))
                   for i in ("A-USDT", "B-USDT", "C-USDT")}
        r = b.reihe_rechnen(verlauf, tage=1)
        satz = list(r.values())[0]
        self.assertEqual((satz["n_ueber"], satz["n_gesamt"]), (3, 3))
        self.assertEqual(satz["breite"], 100.0)
        self.assertEqual(satz["art"], "nachgerechnet")

    def test_fallendes_paar_zaehlt_unter(self):
        verlauf = {"A-USDT": tagesreihe(range(800, 1600)),
                   "B-USDT": tagesreihe(range(1600, 800, -1))}
        satz = list(b.reihe_rechnen(verlauf, tage=1).values())[0]
        self.assertEqual(satz["n_ueber"], 1)
        self.assertEqual(satz["unter"], ["B-USDT"])
        self.assertEqual(satz["breite"], 50.0)

    def test_paar_ohne_genug_geschichte_ist_offen(self):
        verlauf = {"A-USDT": tagesreihe(range(800, 1600)),
                   "JUNG-USDT": tagesreihe(range(10, 60))}
        satz = list(b.reihe_rechnen(verlauf, tage=1).values())[0]
        self.assertEqual(satz["n_gesamt"], 1,
                         "ein junges Paar aendert die Grundgesamtheit nicht")
        self.assertEqual(satz["offen"], ["JUNG-USDT"])

    def test_mehrere_tage_und_determinismus(self):
        verlauf = {"A-USDT": tagesreihe(range(800, 1600))}
        r1 = b.reihe_rechnen(verlauf, tage=5)
        r2 = b.reihe_rechnen(verlauf, tage=5)
        self.assertEqual(len(r1), 5)
        self.assertEqual(r1, r2, "gleiche Eingabe, gleiche Ausgabe")

    def test_erster_kerzentag_der_reihe(self):
        verlauf = {"A-USDT": tagesreihe(range(800, 1600))}
        r = b.reihe_rechnen(verlauf, tage=2)
        self.assertEqual(list(r), [b.kerzentag(TAG * 799),
                                   b.kerzentag(TAG * 800)],
                         "die letzten zwei Kerzentage stehen in der Reihe")


class FuellenTest(unittest.TestCase):
    """`fuellen` laeuft ohne Netz - `hole` ist die Naht."""

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="breite-fuellen-")
        self.echt_reihe, self.echt_hole = b.REIHE, b.hole
        self.echt_paare = b.PAARE
        b.REIHE = os.path.join(self.ordner, "breite-reihe.jsonl")
        b.PAARE = ["A-USDT", "B-USDT"]

        def falsches_hole(inst, anzahl=None):
            n = int(anzahl or b.FENSTER)
            return tagesreihe(range(800, 800 + n) if inst == "A-USDT"
                              else range(800 + n, 800, -1))
        b.hole = falsches_hole

    def tearDown(self):
        b.REIHE, b.hole, b.PAARE = (self.echt_reihe, self.echt_hole,
                                    self.echt_paare)
        shutil.rmtree(self.ordner, ignore_errors=True)

    def _junger_tag(self):
        """Der NEUESTE Tag, den die gefaelschte Geschichte hergibt.

        `fuellen(tage=5)` holt FENSTER + 5 + 5 Kerzen je Paar; der neueste
        Zeitstempel der gefaelschten Reihen ist damit TAG * (800 + FENSTER + 10).
        """
        return b.kerzentag(TAG * (b.FENSTER + 10))

    def test_fehlende_tage_werden_ergaenzt(self):
        r = b.fuellen(tage=5)
        self.assertEqual(len(b.verlauf()), 5)
        self.assertEqual(r["gefuellt"], 5)

    def test_live_zeile_bleibt_stehen(self):
        jung = self._junger_tag()
        b.merken(messung(100.0, kerze=jung))
        b.fuellen(tage=5)
        zeilen = {z["kerze"]: z for z in b.reihe(None)}
        self.assertEqual(zeilen[jung]["breite"], 100.0,
                         "ohne --ueberschreiben wird kein gemessener Tag "
                         "angefasst")
        self.assertNotIn("live_alt", zeilen[jung])
        self.assertEqual(len(b.verlauf()), 5, "die uebrigen Tage kommen dazu")

    def test_ueberschreiben_behaelt_die_alte_messung_als_beleg(self):
        jung = self._junger_tag()
        b.merken(messung(100.0, kerze=jung))
        b.fuellen(tage=5, ueberschreiben=True)
        z = {x["kerze"]: x for x in b.reihe(None)}[jung]
        self.assertEqual(z["art"], "nachgerechnet")
        self.assertEqual(z["live_alt"], 100.0,
                         "der alte Live-Wert bleibt als Beleg in der Zeile")
        self.assertIn("nachgerechnet_am", z)

    def test_mitgegebene_verlaeufe_sparen_den_zweiten_abruf(self):
        """`messen(mit_verlauf=True)` liefert die Kerzen gleich mit - die
        Nachrechnung darf sie nicht noch einmal holen."""
        def platzt(*_a, **_k):
            raise AssertionError("hole wurde trotz mitgegebener Verlaeufe "
                                 "gerufen")
        b.hole = platzt
        n = b.FENSTER + b.VERLAUF_MIT
        verlaeufe = {"A-USDT": tagesreihe(range(800, 800 + n)),
                     "B-USDT": tagesreihe(range(800 + n, 800, -1))}
        r = b.fuellen(tage=5, verlauf_je_inst=verlaeufe)
        self.assertEqual(r["gefuellt"], 5)


    def test_abgleich_nennt_die_abweichung(self):
        jung = self._junger_tag()
        b.merken(messung(100.0, kerze=jung))
        r = b.fuellen(tage=5)
        self.assertEqual(len(r["abgleich"]), 1)
        self.assertEqual(r["abgleich"][0]["kerze"], jung)
        self.assertEqual(r["abgleich"][0]["live"], 100.0)
        self.assertEqual(r["abgleich"][0]["nachgerechnet"],
                         r["abgleich"][0]["live"] + r["abgleich"][0]["diff"])


class MitVerlaufTest(unittest.TestCase):
    """`messen(mit_verlauf=True)` gibt die geholten Kerzen mit zurueck."""

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="breite-mitverlauf-")
        self.echt_reihe, self.echt_hole = b.REIHE, b.hole
        b.REIHE = os.path.join(self.ordner, "breite-reihe.jsonl")

    def tearDown(self):
        b.REIHE, b.hole = self.echt_reihe, self.echt_hole
        shutil.rmtree(self.ordner, ignore_errors=True)

    def test_kerzen_kommen_mit_und_haben_reserve(self):
        gefragt = []

        def falsches_hole(inst, anzahl=None):
            gefragt.append(anzahl)
            return tagesreihe(range(800, 800 + int(anzahl or b.FENSTER)))
        b.hole = falsches_hole
        m = b.messen(paare=["A-USDT", "B-USDT"], still=True, mit_verlauf=True)
        self.assertEqual(set(m["_verlauf"]), {"A-USDT", "B-USDT"})
        self.assertEqual(gefragt, [b.FENSTER + b.VERLAUF_MIT] * 2,
                         "fuer die Nachrechnung werden Zusatzkerzen geholt")
        self.assertEqual(m["n_gesamt"], 2)
        self.assertEqual(m["breite"], 100.0)

    def test_ohne_mit_verlauf_bleibt_der_schluessel_weg(self):
        b.hole = lambda inst, anzahl=None: tagesreihe(
            range(800, 800 + int(anzahl or b.FENSTER)))
        m = b.messen(paare=["A-USDT"], still=True)
        self.assertNotIn("_verlauf", m,
                         "--json und die Wachenausgabe bleiben unveraendert")

    def test_merken_schreibt_den_schluessel_nicht_in_die_zeile(self):
        b.hole = lambda inst, anzahl=None: tagesreihe(
            range(800, 800 + int(anzahl or b.FENSTER)))
        m = b.messen(paare=["A-USDT"], still=True, mit_verlauf=True)
        b.merken(m)
        zeile = b.reihe(None)[0]
        self.assertNotIn("_verlauf", zeile,
                         "der Verlauf ist Rechenhilfe, nicht Buchhaltung")


class LueckenTest(unittest.TestCase):
    """Fehlende Kerzentage in der Reihe (T-204) - reine Rechnung plus Ausgabe."""

    def setUp(self):
        self.ordner = tempfile.mkdtemp(prefix="breite-luecken-")
        self.echt = b.REIHE
        b.REIHE = os.path.join(self.ordner, "breite-reihe.jsonl")

    def tearDown(self):
        b.REIHE = self.echt
        shutil.rmtree(self.ordner, ignore_errors=True)

    def reihe(self, kerzen):
        with open(b.REIHE, "w", encoding="utf-8") as f:
            for k in kerzen:
                f.write(json.dumps({"kerze": k, "breite": 90.0}) + "\n")

    def test_vollstaendige_reihe_hat_keine_luecke(self):
        self.reihe(["2026-07-01", "2026-07-02", "2026-07-03"])
        luecken, erster, letzter = b.fehlende_tage(b.verlauf())
        self.assertEqual(luecken, [])
        self.assertEqual((erster, letzter), ("2026-07-01", "2026-07-03"))

    def test_luecke_wird_gefunden(self):
        self.reihe(["2026-07-01", "2026-07-04"])
        luecken, erster, letzter = b.fehlende_tage(b.verlauf())
        self.assertEqual(luecken, ["2026-07-02", "2026-07-03"])
        self.assertEqual((erster, letzter), ("2026-07-01", "2026-07-04"))

    def test_bis_verlaengert_das_ende(self):
        """Der Waechter kennt die gemessene Kerze, auch vor dem Schreiben."""
        self.reihe(["2026-07-01"])
        luecken, _e, letzter = b.fehlende_tage(b.verlauf(), bis="2026-07-03")
        self.assertEqual(luecken, ["2026-07-02", "2026-07-03"])
        self.assertEqual(letzter, "2026-07-03")

    def test_bis_vor_dem_ersten_tag_ist_keine_luecke(self):
        self.reihe(["2026-07-05"])
        self.assertEqual(b.fehlende_tage(b.verlauf(), bis="2026-07-01")[0], [])

    def test_leere_reihe(self):
        self.assertEqual(b.fehlende_tage([]), ([], None, None))
        self.assertEqual(b.fehlende_tage(b.verlauf()), ([], None, None))

    def test_bereiche_fassen_zusammen(self):
        self.assertEqual(b.luecken_bereiche(["2026-07-01", "2026-07-02",
                                             "2026-07-05"]),
                         [("2026-07-01", "2026-07-02"), ("2026-07-05",
                                                         "2026-07-05")])

    def test_text_nennt_bereich_und_zahl(self):
        self.assertEqual(b.luecken_text(["2026-07-01", "2026-07-02",
                                         "2026-07-05"]),
                         ["2026-07-01 .. 2026-07-02 (2 Kerzentage)",
                          "2026-07-05 (1 Kerzentag)"])

    def test_reihe_ausgabe_nennt_die_luecke(self):
        """`--reihe` muss die Luecke nennen - sonst faellt sie nur beim Lesen auf."""
        self.reihe(["2026-07-01", "2026-07-04"])
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            b.main(["--reihe"])
        text = puffer.getvalue()
        self.assertIn("LUECKEN: 2 Kerzentag(e) fehlen zwischen 2026-07-01 "
                      "und 2026-07-04", text)
        self.assertIn("2026-07-02 .. 2026-07-03 (2 Kerzentage)", text)

    def test_reihe_ausgabe_ohne_luecke_sagt_es(self):
        self.reihe(["2026-07-01", "2026-07-02"])
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            b.main(["--reihe"])
        self.assertIn("Keine Luecke zwischen 2026-07-01 und 2026-07-02 (2 "
                      "Kerzentage)", puffer.getvalue())


class KennzahlenTest(unittest.TestCase):
    def reihe_aus(self, paare):
        return [{"kerze": "2026-09-%02d" % (i + 1), "breite": wert,
                 "delta": delta, "n_ueber": 0, "n_gesamt": 0, "unter": []}
                for i, (wert, delta) in enumerate(paare)]

    def test_verteilung(self):
        tage = self.reihe_aus([(0.0, None), (10.0, 10.0), (90.0, 80.0),
                               (100.0, 10.0)])
        k = b.kennzahlen(tage)
        self.assertEqual(k["n_tage"], 4)
        self.assertEqual(k["mittel"], 50.0)
        self.assertEqual(k["median"], 50.0)
        self.assertEqual((k["min"], k["min_tag"]), (0.0, "2026-09-01"))
        self.assertEqual((k["max"], k["max_tag"]), (100.0, "2026-09-04"))
        self.assertEqual(k["n_ueber_90"], 2)
        # Hochphasen-Tage: 90.0 und 100.0 >= 60 (0.0 und 10.0 nicht)
        self.assertEqual(k["n_ueber_60"], 2)
        self.assertEqual(k["n_unter_60"], 2)

    def test_tagesrauschen_und_zehn_punkte(self):
        """Die Frage hinter der Meldeschwelle von 10 Punkten."""
        tage = self.reihe_aus([(50.0, None), (51.0, 1.0), (49.0, -2.0),
                               (60.0, 11.0), (70.0, 10.0), (30.0, -40.0)])
        k = b.kennzahlen(tage)
        self.assertEqual(k["n_delta"], 5)
        self.assertEqual(k["n_ueber_10"], 3)
        self.assertEqual(k["anteil_ueber_10"], 60.0)
        self.assertEqual(k["delta_median_abs"], 10.0)
        self.assertEqual(k["delta_max_abs"], 40.0)
        self.assertEqual(k["n_gefallen"], 2)

    def test_serie_ueber_zaehlt_die_laengste_folge(self):
        tage = self.reihe_aus([(95.0, None), (92.0, None), (50.0, None),
                               (91.0, None), (94.0, None), (96.0, None)])
        s = b.serie_ueber(tage, 90.0)
        self.assertEqual((s["n"], s["von"], s["bis"]),
                         (3, "2026-09-04", "2026-09-06"))

    def test_leere_reihe(self):
        self.assertEqual(b.kennzahlen([]), {"n_tage": 0})
        self.assertEqual(b.serie_ueber([], 90.0)["n"], 0)


class VorwaertsTest(unittest.TestCase):
    def test_gruppen_und_horizont(self):
        tage = [{"kerze": "2026-01-%02d" % (i + 1), "breite": b_}
                for i, b_ in enumerate((95.0, 10.0, 95.0, 10.0, 95.0))]
        kurse = {"2026-01-%02d" % (i + 1): 100.0 + 10 * i for i in range(5)}
        v = b.vorwaerts(tage, kurse, horizont=1, schwelle=90.0)
        self.assertEqual(v["alle"]["n"], 4, "der letzte Tag hat keine Zukunft")
        self.assertEqual(v["hoch"]["n"], 2)
        self.assertEqual(v["niedrig"]["n"], 2)
        # i=0 -> +10 %, i=2 -> +8.33 % (i=4 hat keine Zukunft mehr)
        self.assertEqual(v["hoch"]["mittel"], 9.17)
        self.assertEqual(v["niedrig"]["mittel"], 8.39)
        self.assertEqual(v["horizont"], 1)

    def test_tage_ohne_kurs_werden_uebersprungen(self):
        tage = [{"kerze": "2026-01-01", "breite": 50.0},
                {"kerze": "2026-01-02", "breite": None}]
        v = b.vorwaerts(tage, {"2026-01-01": 1.0, "2026-01-02": 2.0}, 1)
        self.assertEqual(v["alle"]["n"], 1,
                         "ohne Breite kein Vergleich, ohne Zukunft kein "
                         "Ergebnis")


class EchteReiheUnberuehrtTest(unittest.TestCase):
    def test_test_schreibt_nicht_in_den_echten_stand(self):
        if _echte_reihe is None:
            self.skipTest("keine echte Reihe vorhanden")
        self.assertEqual((os.path.getsize(b.REIHE), os.path.getmtime(b.REIHE)),
                         _echte_reihe,
                         "die echte breite-reihe.jsonl wurde angefasst")


if __name__ == "__main__":
    unittest.main()