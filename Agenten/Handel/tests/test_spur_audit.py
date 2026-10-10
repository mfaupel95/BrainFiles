#!/usr/bin/env python3
"""Tests fuer `spur_audit.py` - die Regeln, nicht die Tageswerte.

ANLASS: T-322 (03.10.2026). Der Scanner galt als beste Spur des Hauses
(+17,49 %, t = 15,3), weil sein Einstieg aus einem zwei Tage alten Bericht
kam. Die Fehlerklasse war im Journal SICHTBAR, nur nirgends geprueft.

Geprueft wird deshalb jede Regel an einem GEBAUTEN Fall, nicht an einem
gemessenen: ein Test, der die Zahlen von heute einfriert, meldet morgen
Aenderung statt Fehler.

  1. Die drei Alarme greifen an gebauten Scheinrunden ...
  2. ... und bleiben still an gebauten ehrlichen Runden (Gegenprobe).
  3. `basisform()` fuehrt jede Schreibweise auf einen Basiswert.
  4. Die Basislinie ist die Marktbewegung, und fehlt sie, wird sie NICHT
     geraten (das ist der Luecken-Fall aus T-323).
  5. Ein Instrument ohne Basiswert (Adresse, Platzhalter) wird benannt,
     nicht durch ein anderes ersetzt.

Laeuft ohne Netz, ohne Buch, ohne Schreiben. Der Start aus dem tests-Ordner
ist nicht noetig (im Gegensatz zu den Spur-Suiten): das Werkzeug haengt
nicht am cwd.

    scanner/.venv/Scripts/python.exe tests/test_spur_audit.py
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

SPUR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SPUR)

import spur_audit as sa                       # noqa: E402


# --------------------------------------------------------------- Testdaten

def kauf(ts, inst="AVAX-USDT", preis=100.0, seite=None, score=None):
    z = {"zeit": ts, "inst": inst, "preis": "%.6f" % preis}
    if seite:
        z["seite"] = seite
    if score is not None:
        z["grund"] = "score %.1f" % score
    return z


def verkauf(ts, inst="AVAX-USDT", preis=110.0):
    return {"zeit": ts, "inst": inst, "preis": "%.6f" % preis}


class BasisformTest(unittest.TestCase):
    """Alle drei Schreibweisen eines Instruments sind EIN Basiswert."""

    def test_okx_spot_und_kontrakt_und_swap(self):
        for name in ("BTC-USDT", "BTC-USD_UM_XPERP-310502", "BTC-USDT-SWAP",
                     "BTC/EUR", "BTC_USDT", "BTC"):
            self.assertEqual(sa.basisform(name), "BTC", name)

    def test_kraken_x_praefix(self):
        self.assertEqual(sa.basisform("XXBTZEUR"), "BTC")
        self.assertEqual(sa.basisform("XETHZEUR"), "ETH")
        self.assertEqual(sa.basisform("SOLEUR"), "SOL")
        self.assertEqual(sa.basisform("XLTCZEUR"), "LTC")
        self.assertEqual(sa.basisform("XXLMZEUR"), "XLM")
        self.assertEqual(sa.basisform("XXRPZEUR"), "XRP")
        # Ein Buchstaben-Basiswert, damit die feste '-3'-Regel nicht traegt:
        self.assertEqual(sa.basisform("ADAEUR"), "ADA")
        self.assertEqual(sa.basisform("XBTZUSD"), "BTC")

    def test_ein_name_ohne_quote_wird_nicht_zerschnitten(self):
        """Gegenprobe: `[:-3]` zerschneidet jeden Nicht-EUR-Namen.

        CASHCAT wurde zu CASH, META zu MA, RENDER zu REN - derselbe Fehler
        eine Ebene hoeher: eine Regel, die auf einen Fall passt und alle
        anderen zerlegt.
        """
        for name in ("CASHCAT", "META", "RENDER", "UNITREE", "FARTCOIN",
                     "GRASS", "OKB", "MON", "XDC", "DRV"):
            self.assertEqual(sa.basisform(name), name,
                             "%s traegt keine Quote und darf nicht zerlegt werden" % name)

    def test_ohne_basiswert_steht_none(self):
        """Eine Solana-Adresse oder ein Platzhalter ist KEIN Instrument."""
        self.assertIsNone(sa.basisform("0x48f413c32a7b5b3c5008866846943a75c0188425"))
        self.assertIsNone(sa.basisform("?"))
        self.assertIsNone(sa.basisform(""))
        self.assertIsNone(sa.basisform(None))

    def test_der_und_ersatz_allein_genuegt_nicht(self):
        """Ohne den Trenner-Ersatz bleiben OKX-Kontrakte unaufgeloest.

        `HBAR-USD_UM_XPERP-310815` ist nach dem Kontrakt-Abzug `HBAR-USD` -
        erst das Ersetzen von `_` und `/` macht daraus den Basiswert. Ohne
        diesen Schritt faellt die Basislinie aus, und zwar still: der Name ist
        unauffaellig, es gibt nur keine Kerze dazu.
        """
        self.assertEqual(sa.basisform("HBAR-USD_UM_XPERP-310815"), "HBAR")
        # Die Regel, nicht eine Python-Regex: JEDER Schritt allein genuegt
        # nicht. Ohne Kontrakt-Abzug traegt die Query-Waehrung; ohne
        # Trenner-Ersatz bleibt der Unterstrich. Beide Zwischenstaende sind
        # keine gueltigen Mapping-Schluessel - und genau darin liegt die
        # stille Luecke, wenn nur einer der drei Schritte fehlt.
        paare = __import__("historie_binance").PAARE
        ziel = sa.basisform("HBAR-USD_UM_XPERP-310815")
        self.assertIn(ziel, paare, "der ENDWERT muss ein Schluessel sein")
        # Zwischenstaende, die NICHT als Schluessel taugen:
        for zwischen in ("HBAR-USD_UM_XPERP-310815", "HBAR-USD", "HBAR_UM_XPERP"):
            if zwischen != ziel:
                self.assertNotIn(zwischen, paare,
                                 "%r ist ein Zwischenstand, kein Basiswert" % zwischen)

    def test_gross_klein_und_leerzeichen_egal(self):
        self.assertEqual(sa.basisform(" hbar-usdt "), "HBAR")


class AlarmTaktTest(unittest.TestCase):
    """Die Haltedauer im Rhythmus des Aufrufers ist ein Befund."""

    def test_runden_im_zyklustakt_werden_erkannt(self):
        # 15 Minuten zwischen Ein- und Ausstieg = exakt ein Aufrufertakt.
        runden = [(kauf("2026-10-01T10:00:00+00:00"),
                   verkauf("2026-10-01T10:15:00+00:00"))]
        for _ in range(5):
            runden.append((kauf("2026-10-01T11:00:00+00:00"),
                           verkauf("2026-10-01T11:15:00+00:00")))
        a = sa.alarm_takt(runden)
        self.assertTrue(a["scheint"],
                        "Runden im Viertelstundentakt muessen auffallen")
        self.assertEqual(a["n"], 6)

    def test_ehrliche_runden_bleiben_still(self):
        """Gegenprobe: eine Runde ueber zwei Tage darf NICHT als Schein gelten."""
        runden = []
        for i in range(6):
            tag = 1 + i * 4
            runden.append((
                kauf("2026-10-%02dT10:00:00+00:00" % tag),
                verkauf("2026-10-%02dT10:00:00+00:00" % (tag + 3))))
        a = sa.alarm_takt(runden)
        self.assertFalse(a["scheint"],
                         "eine Haltedauer von Tagen ist der Normalfall")
        self.assertEqual(a["median"], 72.0)

    def test_schwelle_ist_das_doppelte_des_takts(self):
        """Die Schwelle haengt am Aufrufertakt, nicht an einer eigenen Zahl."""
        runden = [(kauf("2026-10-01T10:00:00+00:00"),
                   verkauf("2026-10-01T10:29:00+00:00"))]
        a = sa.alarm_takt(runden)
        self.assertEqual(a["takt_h"], sa.TAKT_MINUTEN / 60.0)
        # 29 min liegt knapp unter dem Doppelten (30 min bei 15-min-Takt)
        self.assertTrue(a["median"] < 2 * a["takt_h"])


class AlarmPreisTest(unittest.TestCase):
    """Identische Einstiegspreise je (Instrument, Tag) = Snapshot-Fehler.

    Die Preis-Logik wird OHNE Zeitfilter geprueft (fenster_tage=0) - die
    Zeitfalle gehoert in eigene Tests weiter unten (test_alter_bestand...),
    sonst wird eine spätere Datumsaenderung hier zum Fehlschlag.
    """

    def test_uebernommener_preis_wird_erkannt(self):
        # Der Fehler aus T-322: derselbe Berichtspreis fuer jeden Kauf.
        runden = []
        for i in range(6):
            ts = "2026-10-01T%02d:%02d:00+00:00" % (10 + i // 2, (i % 2) * 15)
            runden.append((kauf(ts, preis=7.531000),
                           verkauf(ts, preis=8.6)))
        a = sa.alarm_preis(runden, fenster_tage=0)
        self.assertEqual(a["gruppen"], 1)
        self.assertEqual(a["gleich"], 1)
        self.assertEqual(a["anteil"], 1.0)

    def test_bewegter_markt_bleibt_still(self):
        """Gegenprobe: zwei Kaeufe am Tag mit verschiedenen Preisen."""
        runden = [
            (kauf("2026-10-01T10:00:00+00:00", preis=100.0),
             verkauf("2026-10-02T10:00:00+00:00", preis=110.0)),
            (kauf("2026-10-01T12:00:00+00:00", preis=101.5),
             verkauf("2026-10-02T12:00:00+00:00", preis=111.0)),
        ]
        a = sa.alarm_preis(runden, fenster_tage=0)
        self.assertEqual(a["gleich"], 0)
        self.assertEqual(a["anteil"], 0.0)

    def test_echter_preisfehler_wird_ebenfalls_erkannt(self):
        """Gegenprobe zum Geben: der Fehler aus T-322 war 12 % Abstand.

        Ein Alarm, der nur auf Nachkommastellen vergleicht, sieht einen
        12-%-Fehler nicht, wenn er an einer runden Stelle liegt - und
        `round(x, 1)` verdaechtigt genau das. Der Alarm muss die RELATIVE
        Abweichung zweier Kaeufe am selben Tag sehen, sonst waere er eine
        Genauigkeitspruefung statt einer Fehlererkennung.
        """
        # Der Berichtspreis (7.531) und der Markt (8.60) am selben Tag:
        # der Fehler ist hier die GROSSE Abweichung, nicht die Kleinheit.
        runden = [
            (kauf("2026-10-01T10:00:00+00:00", preis=7.531),
             verkauf("2026-10-01T11:00:00+00:00", preis=8.6)),
            (kauf("2026-10-01T12:00:00+00:00", preis=8.612),
             verkauf("2026-10-01T13:00:00+00:00", preis=8.7)),
        ]
        a = sa.alarm_preis(runden, fenster_tage=0)
        self.assertEqual(a["gruppen"], 1)
        self.assertEqual(a["gleich"], 0,
                         "zwei Preise, die 14 % auseinanderliegen, sind nicht gleich")

    def test_einmalkauf_ist_kein_befund(self):
        """Ein Instrument einmal am Tag kann den Preis nicht behalten haben."""
        runden = [
            (kauf("2026-10-01T10:00:00+00:00", inst="BTC-USDT", preis=100.0),
             verkauf("2026-10-02T10:00:00+00:00", inst="BTC-USDT", preis=110.0)),
            (kauf("2026-10-02T10:00:00+00:00", inst="ETH-USDT", preis=200.0),
             verkauf("2026-10-03T10:00:00+00:00", inst="ETH-USDT", preis=220.0)),
        ]
        a = sa.alarm_preis(runden, fenster_tage=0)
        self.assertEqual(a["gruppen"], 0, "zwei Einmal-Tage sind keine Gruppe")

    # --- Zeitfenster (10.10.2026): Altbestand aus der Fehlerzeit alarmiert
    # nicht mehr, ein frischer Fehler sofort.

    def test_alter_identischer_preis_alarmiert_nicht(self):
        """Der Scanner-Fall: identische Preise nur vor dem Fix (21.09.).

        Gemessen 10.10.2026: 182 von 190 Scanner-Kaeufen stammten aus der
        Zeit vor dem 03.10.-Fix (marktkurs). Der Alarm wertete diesen
        Altbestand und meldete weiter 'Preis uebernommen' - ein behobener
        Fehler. Mit dem Zeitfenster zaehlen alte Gruppen nicht mehr.
        """
        # 60 Tage zurueck: sicher ausserhalb des 30-Tage-Fensters, egal
        # wann der Test laeuft (ein festes Datum wandert in das Fenster).
        alt = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
        runden = [
            (kauf(alt + "T10:00:00+00:00", inst="AVAX-USDT", preis=7.531),
             verkauf(alt + "T11:00:00+00:00", inst="AVAX-USDT", preis=8.6)),
            (kauf(alt + "T12:00:00+00:00", inst="AVAX-USDT", preis=7.531),
             verkauf(alt + "T13:00:00+00:00", inst="AVAX-USDT", preis=8.7)),
        ]
        a = sa.alarm_preis(runden)          # Default-Fenster 30 Tage
        self.assertEqual(a["gruppen"], 0,
                         "alte Gruppen gehoeren nicht mehr in den Alarm")

    def test_frischer_identischer_preis_alarmiert_weiter(self):
        """Gegenprobe: derselbe Fehler HEUTE wird sofort wieder gemeldet."""
        heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        runden = [
            (kauf(heute + "T10:00:00+00:00", inst="AVAX-USDT", preis=7.531),
             verkauf(heute + "T10:15:00+00:00", inst="AVAX-USDT", preis=8.6)),
            (kauf(heute + "T11:00:00+00:00", inst="AVAX-USDT", preis=7.531),
             verkauf(heute + "T11:15:00+00:00", inst="AVAX-USDT", preis=8.7)),
        ]
        a = sa.alarm_preis(runden)          # Default-Fenster 30 Tage
        self.assertEqual(a["gruppen"], 1)
        self.assertEqual(a["gleich"], 1)


class AlarmStreuungTest(unittest.TestCase):

    def test_ein_instrument_traegt_die_mehrheit(self):
        runden = [(kauf("2026-10-01T10:00:00+00:00", inst="AVAX-USDT"),
                   verkauf("2026-10-02T10:00:00+00:00", inst="AVAX-USDT"))
                  for _ in range(8)]
        a = sa.alarm_streuung(runden)
        self.assertEqual(a["anteil"], 1.0)
        self.assertEqual(a["inst"], "AVAX-USDT")

    def test_ohne_instrumentfeld_kein_befund(self):
        """Gegenprobe: eine LEERE Spalte ist keine Konzentration.

        Gemessen 03.10.2026: `kraken` fuehrt `paar`, nicht `inst`. Ein Audit,
        das blind `inst` liest, sieht eine leere Spalte und meldet "alle 54
        Runden auf EIN Instrument" - ein Befund aus dem Nichts.
        """
        runden = [({"zeit": "2026-10-01T10:00:00+00:00", "preis": "1.0"},
                   {"zeit": "2026-10-02T10:00:00+00:00", "preis": "1.1"})
                  for _ in range(8)]
        a = sa.alarm_streuung(runden)
        self.assertFalse(a["messbar"],
                         "ohne belegtes Instrument-Feld darf kein Befund kommen")
        self.assertEqual(a["inst"], None)
        self.assertEqual(a["ohne_feld"], 8,
                         "alle acht Zeilen tragen kein Instrument - das ist die"
                         " Luecke, nicht die Konzentration")

    def test_messbar_verlangt_mindestens_drei_zeilen(self):
        """Ein Instrument an zwei Runden ist noch keine Konzentration.

        Sonst wuerde eine frisch angelegte Spur mit zwei Runden auf einem
        Instrument sofort als Befund gelten - und jeder neue Start einer
        BTC-Spur waere ein Alarm.
        """
        runden = [({"zeit": "2026-10-01T10:00:00+00:00", "preis": "1.0",
                    "inst": "BTC-USDT"},
                   {"zeit": "2026-10-02T10:00:00+00:00", "preis": "1.1",
                    "inst": "BTC-USDT"})]
        a = sa.alarm_streuung(runden)
        self.assertFalse(a["messbar"],
                         "zwei Runden sind keine belastbare Konzentrationsmessung")

    def test_paar_spalte_wird_gelesen(self):
        """Gegenprobe zum selben Fall: `paar` ist bei kraken der Traeger."""
        # Fuenf Paare, je eine Runde: gestreut, also KEIN Befund. Der Anteil
        # ist 1/5 = 0,2 - genau das soll die Korrektur belegen.
        paare = ["ADAEUR", "ALGOEUR", "ATOMEUR", "AVAXEUR", "DOTEUR"]
        runden = [({"zeit": "2026-10-0%dT10:00:00+00:00" % (i + 1),
                    "preis": "1.0", "paar": p},
                   {"zeit": "2026-10-1%dT10:00:00+00:00" % (i + 1),
                    "preis": "1.1", "paar": p})
                  for i, p in enumerate(paare)]
        a = sa.alarm_streuung(runden)
        self.assertTrue(a["messbar"])
        self.assertEqual(a["n"], 1)
        self.assertAlmostEqual(a["anteil"], 0.2, places=6,
                               msg="fuenf Paare sind keine Konzentration")
        self.assertFalse(a["anteil"] > 0.5)

    def test_gestreute_runden_bleiben_still(self):
        runden = [(kauf("2026-10-01T10:00:00+00:00", inst="BTC-%d" % i),
                   verkauf("2026-10-02T10:00:00+00:00", inst="BTC-%d" % i))
                  for i in range(8)]
        a = sa.alarm_streuung(runden)
        self.assertLess(a["anteil"], 0.5)


class ErgebnissTest(unittest.TestCase):
    """Long und Short bekommen entgegengesetzte Vorzeichen - T-230."""

    def test_long_und_short(self):
        self.assertAlmostEqual(
            sa._ergebnis_pct(kauf("t", preis=100.0), verkauf("t", preis=110.0)),
            10.0, places=6)
        self.assertAlmostEqual(
            sa._ergebnis_pct(kauf("t", preis=100.0, seite="short"),
                             verkauf("t", preis=90.0)),
            11.111111, places=5)
        # Ein Verkaufspreis unter dem Einstieg ist fuer einen SHORT ein Gewinn,
        # kein Verlust - ohne das Vorzeichen stuende jede Short-Runde verkehrt.
        self.assertGreater(
            sa._ergebnis_pct(kauf("t", preis=100.0, seite="short"),
                             verkauf("t", preis=90.0)), 0)

    def test_ohne_preis_kein_ergebnis(self):
        self.assertIsNone(sa._ergebnis_pct({"preis": ""},
                                           {"preis": "110.0"}))
        self.assertIsNone(sa._ergebnis_pct({"preis": "100.0"},
                                           {"preis": ""}))


class ScoreTest(unittest.TestCase):

    def test_score_aus_der_grundspalte(self):
        self.assertEqual(sa.score_von({"grund": "score 64.7"}), 64.7)
        self.assertEqual(sa.score_von({"grund": "score=70"}), 70.0)
        self.assertIsNone(sa.score_von({"grund": "liq_wand"}))
        self.assertIsNone(sa.score_von({}))

    def test_hoeherer_score_wird_nicht_als_besser_behauptet(self):
        """Gegenprobe zu T-322: die Baender MUESSEN getrennt ausgegeben werden."""
        runden = [
            (kauf("2026-10-01T10:00:00+00:00", preis=100.0, score=65),
             verkauf("2026-10-01T10:01:00+00:00", preis=118.0)),
            (kauf("2026-10-01T11:00:00+00:00", preis=100.0, score=85),
             verkauf("2026-10-01T11:01:00+00:00", preis=99.0)),
        ]
        b = sa.score_baender(runden)
        self.assertGreater(b["60-69"]["mean"], b["80+"]["mean"])


class BasislinieTest(unittest.TestCase):
    """Die Basislinie ist die Marktbewegung - und fehlt sie, wird sie NICHT
    geraten. Genau das war die stille Luecke aus T-323."""

    def test_markt_im_fenster_long_und_short(self):
        # Stunden-Kerzen: ts_ms, o, h, l, c, v
        basis = 1_700_000_000_000
        index = {basis: [basis, 100, 100, 100, 100.0, 1],
                 basis + 3600000: [basis + 3600000, 100, 100, 100, 110.0, 1]}
        # Der Einstieg liegt MITTEN in der Stunde, das Fenster endet eine
        # Stunde spaeter: der Einstiegskurs ist die Kerze DA VOR, der
        # Ausstiegskurs die LETZTE KERZE IM FENSTER.
        von = datetime_utc(basis + 1800000)
        bis = datetime_utc(basis + 3600000)
        self.assertAlmostEqual(sa.markt_im_fenster(index, von, bis, "long"),
                               10.0, places=6)
        self.assertAlmostEqual(sa.markt_im_fenster(index, von, bis, "short"),
                               -10.0, places=6)

    def test_leerer_index_liefert_none(self):
        von = datetime_utc(1_700_000_000_000)
        self.assertIsNone(sa.markt_im_fenster({}, von, von))
        self.assertIsNone(sa.markt_im_fenster(None, von, von))

    def test_fehlende_kerze_liefert_none_statt_geraten(self):
        """Ohne eine Kerze IM Fenster gibt es keine Basislinie.

        Der Fehler, den dieser Test faengt: nimmt man fuer Ein- und Ausstieg
        dieselbe (letzte vorhandene) Kerze, kommt 0,0 % heraus - die Basislinie
        waere dann die Nullinie, und jede Spur schaete besser aus als sie ist.
        """
        basis = 1_700_000_000_000
        index = {basis: [basis, 100, 100, 100, 100.0, 1]}
        von = datetime_utc(basis + 3_600_000)
        bis = datetime_utc(basis + 5_400_000)
        self.assertIsNone(sa.markt_im_fenster(index, von, bis),
                          "keine Kerze im Fenster -> keine Basislinie, nicht 0")

    def test_null_ist_nicht_die_basislinie(self):
        """Gegenprobe: Fenster exakt auf der Kerze = 0 %, das ist ein Befund."""
        basis = 1_700_000_000_000
        index = {basis: [basis, 100, 100, 100, 100.0, 1]}
        von = datetime_utc(basis)
        bis = datetime_utc(basis)
        self.assertIsNone(sa.markt_im_fenster(index, von, bis))


def datetime_utc(ts_ms):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)


class VerzerrungTest(unittest.TestCase):
    """Die Auswahl-Verzerrung - der eigene Befund vom 03.10.2026.

    Das Werkzeug meldete den Scanner mit +11,9 % Excess, weil es nur die 40
    sauberen Runden gemessen hatte: eine Runde von 15 Minuten Dauer hat oft
    keine volle Stunde in ihrem Fenster, also keine Basislinie - und genau
    diese Runden sind die Scheinrunden aus T-322. Ohne die Trennung nach
    Haltedauer misste die Zahl die Auswahl statt der Spur, und das sah
    sauber aus. Das ist dieselbe Verzerrung eine Ebene tiefer.
    """

    def _paare(self):
        return [{"ergebnis": 19.0, "markt": 0.7, "halt": 0.25},
                {"ergebnis": 19.0, "markt": 0.7, "halt": 0.25},
                {"ergebnis": 18.0, "markt": 0.5, "halt": 0.5},
                {"ergebnis": 2.4, "markt": 0.03, "halt": 6.0},
                {"ergebnis": 2.3, "markt": 0.03, "halt": 8.0}]

    def test_die_beiden_gruppen_werden_getrennt(self):
        v = sa.verzerrung(self._paare())
        self.assertEqual(v["kurz"]["n"], 3)
        self.assertEqual(v["lang"]["n"], 2)

    def test_ohne_trennung_waere_die_zahl_falsch(self):
        """Gegenprobe: die Gesamtzahl ist der Mittelwert beider Gruppen."""
        paare = self._paare()
        v = sa.verzerrung(paare)
        gesamt = sa.mittel([r["ergebnis"] - r["markt"] for r in paare])
        naehe = abs(gesamt - v["kurz"]["excess"]) < abs(gesamt - v["lang"]["excess"])
        self.assertTrue(naehe,
                        "die Gesamtzahl liegt bei den KURZEN Runden - ohne die")
        self.assertGreater(abs(v["abweichung"]), 5.0,
                           "die Gruppen muessen weit auseinanderliegen, damit")
        self.assertGreater(v["kurz"]["excess"], v["lang"]["excess"])

    def test_ohne_haltedauer_geht_nichts_in_eine_gruppe(self):
        """Eine Runde OHNE Haltedauer gehoert in KEINE Gruppe.

        Sonst wuerde sie in der einen oder anderen landen und die Gruppen
        waeren gemischt - der Befund waere dann eine Zufallsgroesse.
        """
        paare = [{"ergebnis": 19.0, "markt": 0.7, "halt": None}]
        v = sa.verzerrung(paare)
        self.assertEqual(v["kurz"]["n"], 0)
        self.assertEqual(v["lang"]["n"], 0)
        self.assertIsNone(v["abweichung"])


class NormalisierungTrägtTest(unittest.TestCase):
    """Die Normalisierung ist der Grund, dass 47 Instrumente messbar wurden.

    Gemessen haben die Spuren 110 verschiedene Journalnamen fuer 66
    Basiswerte. Ohne die Reduktion auf den Basiswert beantwortet die
    Basislinie die Frage nicht - `historie_binance.PAARE` kennt `HBAR`, aber
    nicht `HBAR-USD_UM_XPERP-310815`. Dieser Test legt beide Schreibweisen
    in denselben Index und verlangt, dass sie dieselbe Reihe sehen.
    """

    def test_die_gleiche_basis_teilt_sich_den_index(self):
        sa._INDEX_CACHE.clear()
        a = sa.instrument_index("BTC-USDT")
        b = sa.instrument_index("BTC-USD_UM_XPERP-310502")
        c = sa.instrument_index("BTC/EUR")
        self.assertIs(a, b, "beide Namen sind BTC und muessen dieselbe Reihe sehen")
        self.assertIs(a, c)

    def test_alle_drei_schreibweisen_ergeben_denselben_basiswert(self):
        """Ohne diese Gleichheit faellt jede Basislinie aus."""
        sa._INDEX_CACHE.clear()
        for name in ("HBAR-USDT", "HBAR-USD_UM_XPERP-310815", "HBAR"):
            self.assertEqual(sa.basisform(name), "HBAR", name)
        # und die Basisform entscheidet ueber den Zugriff, nicht der Name
        a = sa.instrument_index("HBAR-USDT")
        b = sa.instrument_index("HBAR-USD_UM_XPERP-310815")
        self.assertIs(a, b)

    def test_ohne_normalisierung_waere_es_leer(self):
        """Gegenprobe: ein unnormalisierter Name liefert keine Reihe."""
        sa._INDEX_CACHE.clear()
        self.assertEqual(sa.instrument_index("0x48f4..."), {})
        self.assertEqual(sa.instrument_index("?"), {})


class PaarungTest(unittest.TestCase):
    """Das Audit benutzt die EINE Zuordnung des Hauses."""

    def test_es_ist_die_hauspaarung(self):
        import journalpaarung
        self.assertIs(sa.journalpaarung, journalpaarung)
        self.assertTrue(callable(sa.journalpaarung.Paarung))


if __name__ == "__main__":
    unittest.main(verbosity=2)