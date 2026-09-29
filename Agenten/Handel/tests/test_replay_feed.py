"""Der Adapter muss GENAU die Felder liefern, die die Spur entscheidet.

Ein Adapter mit falschen Feldern laesst die Spur still ohne Signal laufen und
erzeugt eine Zahl, die wie ein Messwert aussieht. Deshalb wird hier gegen den
QUELLTEXT der Spur geprueft, nicht gegen eine gepflegte Liste: wer die Spur
umbaut, soll hier einen roten Test bekommen statt einen stillen Nullauf.

Kein Test dieses Moduls geht ins Netz: alles laeuft ueber Attrappen-Kerzen.
"""

import ast
import inspect
import json
import os
import sys
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import moondev_historie as mh                                      # noqa: E402
import replay                                                      # noqa: E402

SPUREN = ("moondev_topmovers", "moondev_marktlage", "moondev_signalwelle")

# wachen-Werte, wie die Spuren sie fuehren
W = {"anzahl_coins": 250, "mindest_volumen_usd": 2e7,
     "btc_schwelle_pct": 2.0, "breite_oben": 0.60, "breite_unten": 0.40}


class BestandMixin:
    """Ein Bestand aus Attrappen-Kerzen, Ablage im Temp-Ordner."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="feed_")
        self.alt = mh.ORDNER
        mh.ORDNER = self.tmp
        # Zwei Tage: Vortag flach, heute je Symbol eine andere Bewegung.
        # BTC +10 %, AAA -5 %, BBB +1 %, CCC +3 %  -> Breite 3/4 = 0.75
        for sym, vor, jetzt in (("BTCUSDT", 100.0, 110.0), ("AAAUSDT", 100.0, 95.0),
                                ("BBBUSDT", 100.0, 101.0), ("CCCUSDT", 100.0, 103.0)):
            mh.speichere_feed(sym, "1D", [[0, vor, vor, vor, vor, 1e7],
                                          [86400000, jetzt, jetzt, jetzt, jetzt, 2e7]])
        self.b = mh.Bestand()
        self.b.laden("1D")
        self.ts = 86400000

    def tearDown(self):
        mh.ORDNER = self.alt


class FeldTest(BestandMixin, unittest.TestCase):
    def test_adapter_liefert_was_die_entscheidung_liest(self):
        """Quelltext der Spur gegen die Felder des Adapters."""
        for spur in SPUREN:
            quelle = inspect.getsource(replay.spur_modul(spur).quelle)
            for feld in mh.FELDER[spur]:
                self.assertIn(feld, quelle,
                              "%s: Adapter liefert %r, die Spur liest es nicht"
                              % (spur, feld))

    def test_jede_feed_spur_hat_eine_quelle_und_eine_feldliste(self):
        self.assertEqual(sorted(SPUREN), sorted(mh.QUELLEN))
        self.assertEqual(sorted(SPUREN), sorted(mh.FELDER))


class TopmoversTest(BestandMixin, unittest.TestCase):
    def test_felder_werden_auf_die_namen_der_spur_uebersetzt(self):
        """Die Ablage heisst aenderung_pct/volumen_usd, die Spur liest
        aenderung_24h/volumen_24h. Ohne Uebersetzung sieht die Spur nichts."""
        daten, kurse, fehler = mh.quelle_topmovers(self.b, self.ts, W)
        self.assertEqual([], fehler)
        btc = daten["BTC"]
        self.assertAlmostEqual(10.0, btc["aenderung_24h"], places=6)
        self.assertAlmostEqual(2e7, btc["volumen_24h"], places=6)
        self.assertAlmostEqual(110.0, btc["kurs"], places=6)
        self.assertEqual("BTC", btc["name"])

    def test_kurse_tragen_ALLE_symbole_nicht_nur_die_kandidaten(self):
        """Eine offene Position ausserhalb der Kandidaten braucht ihren Kurs,
        sonst schliesst sie nie (spur_buch.pruefe_ausstiege)."""
        daten, kurse, _ = mh.quelle_topmovers(self.b, self.ts, dict(W, anzahl_coins=1))
        self.assertEqual(1, len(daten))
        self.assertEqual(["AAAUSDT", "BBBUSDT", "BTCUSDT", "CCCUSDT"],
                         sorted(self.b.symbole()))
        self.assertEqual(4, len(kurse))

    def test_erstes_kerzenpaar_ohne_vortag_liefert_None_statt_null(self):
        daten, _, _ = mh.quelle_topmovers(self.b, 0, W)
        self.assertIsNone(daten["BTC"]["aenderung_24h"])


class MarktlageTest(BestandMixin, unittest.TestCase):
    def test_breite_ist_ein_anteil_kein_prozentwert(self):
        """Die wachen liest 0.60/0.40 - 75 waere 7500 % und immer ueber der
        Schwelle, 0.75 ist richtig."""
        daten, _, fehler = mh.quelle_marktlage(self.b, self.ts, W)
        self.assertEqual([], fehler)
        self.assertAlmostEqual(0.75, daten["BTC"]["breite"], places=6)
        self.assertAlmostEqual(10.0, daten["BTC"]["btc_aenderung_24h"], places=6)

    def test_ohne_btc_kein_signal_statt_einer_erfundenen_zeile(self):
        mh.speichere_feed("ZZZUSDT", "1D", [[0, 1, 1, 1, 1, 1e7]])
        b = mh.Bestand()
        b.laden("1D")
        b._reihen.pop("BTCUSDT")
        daten, kurse, fehler = mh.quelle_marktlage(b, self.ts, W)
        self.assertEqual({}, daten)
        self.assertTrue(fehler)


class SignalwelleTest(unittest.TestCase):
    """Stundentakt: 26 Kerzen, damit 24h-Vorlauf da ist."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="feed_")
        self.alt = mh.ORDNER
        mh.ORDNER = self.tmp
        for sym in ("AAAUSDT", "BBBUSDT"):
            mh.speichere_feed(sym, "1H", [
                [i * 3600000, 100.0 + i, 100.0 + i, 100.0 + i, 100.0 + i, 10.0]
                for i in range(26)])
        self.b = mh.Bestand()
        self.b.laden("1H")
        self.ts = 25 * 3600000

    def tearDown(self):
        mh.ORDNER = self.alt

    def test_liefert_beide_aenderungen_und_das_volumen(self):
        daten, _, fehler = mh.quelle_signalwelle(self.b, self.ts, W)
        self.assertEqual([], fehler)
        z = daten["AAA"]
        self.assertAlmostEqual((125.0 / 124.0 - 1.0) * 100.0, z["aenderung_1h"], places=6)
        self.assertAlmostEqual((125.0 / 101.0 - 1.0) * 100.0, z["aenderung_24h"], places=6)
        self.assertAlmostEqual(240.0, z["volumen_24h"], places=6)
        self.assertAlmostEqual(125.0, z["kurs"], places=6)

    def test_ohne_24_kerzen_keine_kandidaten(self):
        daten, _, _ = mh.quelle_signalwelle(self.b, 5 * 3600000, W)
        self.assertEqual({}, daten)


class GegenprobeJournalTest(unittest.TestCase):
    """Der Adapter gegen die Wirklichkeit - offline und wiederholbar.

    NAME: hiess bis zum 29.09.2026 `GegenprobeTest`. Eine zweite Sitzung baute
    am selben Tag eine zweite Gegenprobe unter demselben Namen; die spaetere
    Definition verdeckt die fruehere still, und eine der beiden Pruefungen lief
    dann NIE. Beide haben ihren eigenen Namen, beide laufen.

    Die Feed-Spuren holen ihre Preise im Betrieb von CoinGecko. Diese Preise
    stehen in ihren ECHTEN Journals (CoinGecko beantwortet Abrufe von diesem
    Rechner mit HTTP 403, ein neuer Abzug ist also nicht zu haben). Verglichen
    wird die Groessenordnung, nicht die Stelle hinter dem Komma: zwei Boersen
    sind zwei Preise, und CoinGecko mittelt ueber viele Preise. Eine Pruefung
    auf Gleichheit waere selbst falsch.

    Der Fall ist der gefaehrliche: ein Adapter mit vertauschten Feldern (Kurs
    und Volumen, 24h gegen 1h) sieht wie eine Messung aus und ist keine.
    """

    TOLERANZ = 0.25          # 25 % Abweichung sind erlaubt
    SPUREN = ("moondev_topmovers", "moondev_marktlage", "moondev_signalwelle")

    def _zeilen(self, spur):
        import csv
        pfad = os.path.join(HANDEL, spur, "handelsjournal.csv")
        if not os.path.isfile(pfad):
            return []
        with open(pfad, encoding="utf-8", newline="") as f:
            return [z for z in csv.DictReader(f) if z.get("preis")
                    and z.get("inst") and z.get("zeit")]

    def test_kurs_gegen_die_eigene_journalzeile(self):
        b = mh.Bestand()
        b.laden("1D")
        zu_basis = {}
        for sym in b.symbole():
            zu_basis.setdefault(mh.basis_von(sym) or sym, sym)
        geprueft, abweichungen = 0, []
        for spur in self.SPUREN:
            for z in self._zeilen(spur)[:40]:
                sym = zu_basis.get(str(z["inst"]).upper())
                if not sym:
                    continue
                ts = z["zeit"][:10]
                kurs = None
                for r in b._reihen[sym]:
                    tag = time.strftime("%Y-%m-%d", time.gmtime(r[0] / 1000.0))
                    if tag == ts:
                        kurs = float(r[4])          # Schlusskurs
                        break
                if kurs is None:
                    continue
                soll = float(z["preis"])
                if soll <= 0:
                    continue
                ab = abs(kurs - soll) / soll
                geprueft += 1
                if ab > self.TOLERANZ:
                    abweichungen.append("%s %s: Binance %.6f gegen CoinGecko "
                                        "%.6f (%.0f %%)"
                                        % (spur, z["inst"], kurs, soll, ab * 100))
        self.assertGreaterEqual(geprueft, 3,
                               "zu wenige gemeinsame Tage - nichts geprueft")
        self.assertEqual([], abweichungen)

    def test_probe_ist_als_beleg_da_oder_wird_benannt(self):
        """Fehlt der Abzug, wird das GEMELDET - nicht stillschweigend geprueft."""
        probe = os.path.join(HANDEL, "daten", "historie", "coingecko_probe.json")
        if os.path.isfile(probe):
            with open(probe, encoding="utf-8") as f:
                self.assertGreater(len(json.load(f)["maerkte"]), 50)
        else:
            self.skipTest("kein CoinGecko-Abzug aufgezeichnet (HTTP 403 vom "
                          "Netz) - die Journal-Gegenprobe oben traegt den Beweis")


class MainReihenfolgeTest(unittest.TestCase):
    def test_familien_zweige_stehen_vor_dem_familie_a_vorlauf(self):
        """`lade_wachen()` gibt es nur bei Familie A.

        Stand der Vorlauf davor, riss er die beiden anderen Familien mit:
        am 29.09.2026 starben beide Feed-Laeufe mit AttributeError, bevor ein
        einziger Schritt gerechnet war. Der Test prueft die REIHENFOLGE, nicht
        das Ergebnis - die Ursache lag in der Reihenfolge.
        """
        quelle = inspect.getsource(replay.main)
        self.assertIn("if a.feed:", quelle)
        self.assertIn("if a.familie_c:", quelle)
        # Auf den AUFRUF ankern, nicht auf den Namen: "lade_wachen" steht auch
        # in dieser Begruendung und im Docstring - ein Test, der Prosa mitliest,
        # findet den Namen dort zuerst und meldet falsch (29.09.2026 passiert).
        aufruf = quelle.index(".lade_wachen()")
        # spur_buch legt Agenten/Bus auf den Suchpfad - andersherum faellt der
        # ereignis-Import mit ModuleNotFoundError um (29.09.2026).
        #
        # Geparst statt gesucht: eine Textsuche nach dem Importnamen findet ihn
        # zuerst im KOMMENTAR, der ihn begruendet - derselbe Fehlschluss ist an
        # diesem Tag zweimal passiert. Der Baum kennt nur echten Code.
        baum = ast.parse(inspect.getsource(replay.lauf_feed))
        reihenfolge = [n.names[0].name for n in ast.walk(baum)
                       if isinstance(n, ast.Import)]
        self.assertIn("spur_buch", reihenfolge)
        self.assertIn("ereignis", reihenfolge)
        self.assertLess(reihenfolge.index("spur_buch"),
                        reihenfolge.index("ereignis"))
        self.assertLess(quelle.index("if a.feed:"), aufruf)
        self.assertLess(quelle.index("if a.familie_c:"), aufruf)


class GebuehrTest(unittest.TestCase):
    def test_gebuehr_kommt_ohne_lade_wachen_aus(self):
        """Die Kostenrechnung darf nicht an einer Spurenfamilie haengen.

        `lade_wachen()` gibt es nur bei Familie A; die Feed-Spuren haben es
        nicht. Der Aufruf riss am 29.09.2026 beide Laeufe ab, bevor ein Schritt
        gerechnet war - die Wachen kommen jetzt aus der DATEI.
        """
        for spur in ("moondev_topmovers", "moondev_marktlage", "moondev_funding"):
            self.assertGreater(replay.gebuehr_fuer(spur), 0.0)

    def test_jede_spur_hat_einen_boersensatz(self):
        """Ohne Satz waere die Kostenrechnung still null."""
        for spur in replay.SPUREN_TEIL_A + replay.SPUREN_TEIL_C:
            self.assertGreater(replay.gebuehr_fuer(spur, {}), 0.0)

    def test_funding_ist_eigene_familie_und_nicht_teil_a(self):
        self.assertIn("moondev_funding", replay.SPUREN_TEIL_C)
        self.assertNotIn("moondev_funding", replay.SPUREN_TEIL_A)

    def test_schrittweite_ist_der_funding_takt(self):
        """Acht Stunden - der Takt, in dem sich ein Funding-Satz aendert."""
        self.assertEqual(8, replay.FUNDING_STUNDEN)


class LaufFeedTest(BestandMixin, unittest.TestCase):
    def test_adapter_sieht_den_stand_des_schritts_nicht_den_letzten(self):
        """Zwei Zeitpunkte muessen zwei verschiedene Tafeln ergeben.

        Waere der Zeitpunkt fest verdrahtet, saehe jeder Schritt denselben
        Markt - und der Lauf saehe wie eine Messung aus.
        """
        daten, _, _ = mh.QUELLEN["moondev_topmovers"](self.b, 86400000, W)
        self.assertAlmostEqual(10.0, daten["BTC"]["aenderung_24h"], places=6)
        self.assertAlmostEqual(-5.0, daten["AAA"]["aenderung_24h"], places=6)

    def test_ohne_vortag_keine_kandidaten_am_ersten_schritt(self):
        """Der erste Tag hat keine 24h-Aenderung - er zaehlt nicht als Signal."""
        daten, _, _ = mh.QUELLEN["moondev_topmovers"](self.b, 0, W)
        self.assertTrue(all(v["aenderung_24h"] is None for v in daten.values()))

    def test_unbekannte_spur_wird_gemeldet(self):
        with self.assertRaises(KeyError):
            replay.lauf_feed("diegibtesnicht", 0.05, "t")

    def test_verweigerte_spur_wird_nicht_geraten(self):
        with self.assertRaises(RuntimeError):
            replay.lauf_feed("moondev_sniper", 0.05, "t")

    def test_verweigerte_spuren_nennen_einen_grund(self):
        for spur in ("moondev_sniper", "moondev_listingarb"):
            self.assertIn(spur, replay.NICHT_NACHRECHENBAR)
            self.assertGreater(len(replay.NICHT_NACHRECHENBAR[spur]), 20)


class LaufFeedEchtTest(unittest.TestCase):
    """Ein echter Durchlauf ueber Attrappen-Kerzen, Ablage im Temp-Ordner.

    Beweist die Verdrahtung: Adapter -> spur_buch.zyklus -> Journal im
    BACKTEST-Ordner. Ohne diesen Test waere ein Adapter denkbar, der die Spur
    still ohne Signal laufen laesst.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="feed_")
        self.alt = mh.ORDNER
        mh.ORDNER = self.tmp
        # Alle drei Symbole springen an Tag 20 von 100 auf 112 (+12 %): das ist
        # ein Top-Mover-Signal (+8..40 %) bei Volumen ueber 2e7 USD.
        for sym in ("AAAUSDT", "BBBUSDT", "CCCUSDT"):
            mh.speichere_feed(sym, "1D", [
                [i * 86400000, *(100.0 if i < 20 else 112.0,) * 4, 2e7]
                for i in range(40)])
        self.bt = tempfile.mkdtemp(prefix="bt_")
        self.alt_v = replay.verzeichnis
        replay.verzeichnis = lambda: self.bt

    def tearDown(self):
        mh.ORDNER = self.alt
        replay.verzeichnis = self.alt_v

    def test_durchlauf_schreibt_ein_journal_und_zaehlt_die_schritte(self):
        k, _ = replay.lauf_feed("moondev_topmovers", 0.1, "takt",
                                mindest_symbole=2)
        self.assertGreater(k["schritte"], 30)
        self.assertEqual(3, k["universum"])
        self.assertEqual("1D", k["takt"])
        self.assertAlmostEqual(0.1, k["gebuehr_pct"], places=9)
        journal = os.path.join(self.bt, "moondev_topmovers", "takt",
                               "handelsjournal.csv")
        self.assertTrue(os.path.isfile(journal), "kein Journal geschrieben")
        with open(journal, encoding="utf-8") as f:
            zeilen = [z for z in f.read().splitlines() if z.strip()]
        self.assertGreater(len(zeilen), 1, "Journal ohne eine einzige Buchung")

    def test_ein_tag_mit_zu_wenig_reihen_ist_kein_schritt(self):
        """Drei Reihen sind keine Marktbreite."""
        b = mh.Bestand()
        b.laden("1D")
        self.assertGreaterEqual(len(b.schritte(mindest_symbole=3)), 30)
        self.assertEqual([], b.schritte(mindest_symbole=4))

    def test_zu_wenig_reihen_wird_gemeldet_statt_gerechnet(self):
        with self.assertRaises(RuntimeError):
            replay.lauf_feed("moondev_topmovers", 0.1, "takt",
                             mindest_symbole=99)


class LaufCTest(unittest.TestCase):
    def test_ohne_funding_reihen_wird_der_befehl_genannt(self):
        tmp = tempfile.mkdtemp(prefix="feed_")
        alt = mh.ORDNER
        mh.ORDNER = tmp
        bt = tempfile.mkdtemp(prefix="bt_")
        alt_v = replay.verzeichnis
        replay.verzeichnis = lambda: bt
        try:
            with self.assertRaises(RuntimeError) as c:
                replay.lauf_c("moondev_funding", 0.04, "takt")
            self.assertIn("--funding", str(c.exception))
        finally:
            mh.ORDNER = alt
            replay.verzeichnis = alt_v


class SetzenTest(unittest.TestCase):
    """`--setzen` aendert NUR die Kopie - die Wachen der Spur bleibt unberuehrt.

    Der Grund fuer diesen Test: eine Spur, deren Kill-Schalter den Lauf nach
    sechs Tagen abwuergt (moondev_funding, gemessen am 29.09.2026), ist sonst
    nicht ueber den ganzen Zeitraum messbar. Die Verlockung waere, den Deckel
    einfach in der ECHTEN Wachen zu heben - das waere ein Eingriff in den
    laufenden Betrieb. Geprueft wird deshalb beides: der Wert landet in der
    Kopie, und die Quelle bleibt Byte fuer Byte gleich.
    """

    SPUR = "moondev_topmovers"
    LAUF = "_test_setzen"

    def setUp(self):
        self.wachen = os.path.join(HANDEL, self.SPUR, "wachen.json")
        with open(self.wachen, "rb") as f:
            self.vorher = f.read()
        self.ordner = replay.buch_ordner(self.SPUR, self.LAUF,
                                          setzen={"kill_switch_gesamt_usd": 999999})

    def tearDown(self):
        import shutil
        shutil.rmtree(os.path.join(HANDEL, "daten", "backtest", self.SPUR,
                                   self.LAUF), ignore_errors=True)

    def test_quelle_bleibt_unberuehrt(self):
        with open(self.wachen, "rb") as f:
            self.assertEqual(self.vorher, f.read(),
                             "die echte Wachen wurde angefasst")

    def test_kopie_traegt_den_wert_und_die_herkunft(self):
        with open(os.path.join(self.ordner, "wachen.json"), encoding="utf-8") as f:
            kopie = json.load(f)
        self.assertEqual(999999, kopie["kill_switch_gesamt_usd"])
        self.assertEqual({"kill_switch_gesamt_usd": 999999},
                         kopie["_backtest_gesetzt"],
                         "was gesetzt wurde, muss in der Kopie nachlesbar sein")

    def test_ohne_setzen_keine_spur(self):
        ordner = replay.buch_ordner(self.SPUR, self.LAUF)
        with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
            kopie = json.load(f)
        self.assertNotIn("_backtest_gesetzt", kopie)

    def test_setzen_liest_zahlen_und_wahrheitswerte(self):
        aus = replay.setzen_aus(["a=1", "b=2.5", "c=true", "d=Wort"])
        self.assertEqual({"a": 1, "b": 2.5, "c": True, "d": "Wort"}, aus)

    def test_setzen_ohne_gleichheitszeichen_bricht_ab(self):
        with self.assertRaises(SystemExit):
            replay.setzen_aus(["kaputt"])


class GegenprobeBoerseTest(unittest.TestCase):
    """Die Tafel gegen eine zweite Boerse.

    Ein Adapter, den niemand gegen die Wirklichkeit gehalten hat, ist eine
    Behauptung. Verglichen wird die GROESSENORDNUNG, nicht die Stelle hinter
    dem Komma: zwei Boersen sind zwei Preise, und CoinGecko mittelt ueber
    viele. Ein Vergleich, der Gleichheit verlangt, waere selbst falsch.

    Der Abzug wird EINMAL aufgezeichnet (daten/historie/coingecko_probe.json)
    und ist damit reproduzierbar. Fehlt er, faellt der Test als SKIP auf -
    nicht als gruen, denn eine fehlende Probe ist keine bestandene Probe.
    """

    PROBE = os.path.join(HANDEL, "daten", "historie", "coingecko_probe.json")
    TOLERANZ = 0.25      # 25 % Abweichung je Feld sind erlaubt

    def test_kurs_gegen_okx_in_der_groessenordnung(self):
        """Zweite Boerse, engerer Massstab.

        OKX und Binance sind zwei Boersen fuer dieselbe Muenze - fuer den
        Schlusskurs desselben Tages duerfen sie nur wenig auseinanderliegen.
        Der Abzug muss ZEITNAH an der letzten Kerze liegen, sonst vergleicht
        man zwei verschiedene Tage und der Test waere selbst falsch.
        """
        pfad = os.path.join(HANDEL, "daten", "historie", "okx_probe.json")
        if not os.path.isfile(pfad):
            self.skipTest("kein OKX-Abzug aufgezeichnet: %s" % pfad)
        with open(pfad, encoding="utf-8") as f:
            probe = json.load(f)
        b = mh.Bestand()
        b.laden("1D")
        schritte = b.schritte(30)
        # Der LETZTE abgeschlossene Tag: die heutige Tageskerze laeuft noch,
        # ihr Schlusskurs ist der Stand des Abrufs und nicht der Tageschluss
        # (genau daran scheiterte der erste Vergleich am 29.09.2026).
        fertig = [t for t in schritte if t + 86400000 <= probe["stand_ms"]]
        if not fertig:
            self.skipTest("kein abgeschlossener Tag im Bestand")
        ts = fertig[-1]
        if probe["stand_ms"] - ts > 5 * 86400000:
            self.skipTest("Abzug ist %d Tage juenger als der letzte Tag"
                          % round((probe["stand_ms"] - ts) / 86400000))
        tafel = {z["basis"]: z for z in b.tafel(ts, top=300).values()}
        geprueft, abweichungen, ohne_kurs = 0, [], []
        for m in probe["maerkte"]:
            sym = (m.get("symbol") or "").upper()
            if sym not in tafel:
                continue
            # DERSELBE Tagesschluss auf beiden Boersen - nicht "letzte Kerze
            # gegen Ticker jetzt". Genau dieser Vergleich lag am 29.09.2026 bei
            # vier Symbolen 10 % daneben, ohne dass die Daten falsch waren.
            # Binances Tageskerze oeffnet um 00:00 UTC und schliesst 24 h
            # spaeter; die OKX-Stunde, die auf dieser Grenze endet, ist
            # ts + 24 h. Beide Zahlen sind derselbe Zeitpunkt.
            grenze = ts + 24 * 3600000
            kurs = m["schluss"].get(str(grenze)) or m["schluss"].get(grenze)
            if not kurs:
                ohne_kurs.append(sym)
                continue
            soll, ist = float(kurs), tafel[sym]["kurs"]
            if soll <= 0 or not ist:
                continue
            quote = abs(ist - soll) / soll
            geprueft += 1
            if quote >= 0.05:
                abweichungen.append("%s: Binance %.6f gegen OKX %.6f (%.1f %%)"
                                    % (sym, ist, soll, quote * 100))
        self.assertGreater(geprueft, 20,
                           "zu wenige gemeinsame Stunden (%d), ohne Kurs: %s"
                           % (geprueft, ",".join(ohne_kurs[:5])))
        self.assertEqual([], abweichungen,
                         "ausserhalb der Toleranz: " + "; ".join(abweichungen[:5]))

    def test_kurs_in_der_groessenordnung(self):
        # Die Pruefung gehoert in DEN Test, nicht in setUp: ein skip in setUp
        # nimmt die ganze Klasse mit, und der OKX-Test lief dann nie
        # (gemessen am 29.09.2026: 168 gemeinsame Symbole lagen ungeprueft da).
        if not os.path.isfile(self.PROBE):
            self.skipTest("kein CoinGecko-Abzug aufgezeichnet: %s" % self.PROBE)
        with open(self.PROBE, encoding="utf-8") as f:
            probe = json.load(f)
        b = mh.Bestand()
        b.laden("1D")
        schritte = b.schritte(30)
        self.assertTrue(schritte, "kein Zeitpunkt mit genug Reihen")
        ts = schritte[-1]
        tafel = {z["basis"]: z for z in b.tafel(ts, top=300).values()}
        geprueft, abweichungen = 0, []
        for m in probe["maerkte"]:
            sym = (m.get("symbol") or "").upper()
            if sym not in tafel:
                continue
            soll, ist = float(m["current_price"]), tafel[sym]["kurs"]
            if soll <= 0 or not ist:
                continue
            quote = abs(ist - soll) / soll
            geprueft += 1
            if quote >= self.TOLERANZ:
                abweichungen.append("%s: Binance %.6f gegen CoinGecko %.6f (%.0f %%)"
                                    % (sym, ist, soll, quote * 100))
        self.assertGreater(geprueft, 10,
                           "zu wenige gemeinsame Symbole (nur %d)" % geprueft)
        self.assertEqual([], abweichungen,
                         "ausserhalb der Toleranz: " + "; ".join(abweichungen[:5]))


if __name__ == "__main__":
    unittest.main()
