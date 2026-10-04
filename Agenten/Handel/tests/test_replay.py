"""Schreibschutz, Backtest-Ordner und Gegenprobe des Replay-Kerns.

Der wichtigste Test dieser Datei ist `NichtsAusserhalbTest`: er vergleicht
Dateiliste und Groessen des ECHTEN Spurenordners und der Q:-Spiegelung vor und
nach einem Replay-Lauf. Ein Test, der in ein echtes Ziel schreibt, hat hier
nichts zu suchen (Lehre vom 14.09.2026, TEST-Q:-FALLE).

`replay.verzeichnis` zeigt in JEDEM Test auf einen Temp-Ordner - auch der
Backtest-Bereich selbst wird nicht angefasst.
"""

import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, HANDEL)

import replay                                                     # noqa: E402

# Kurze Reihe = schneller Lauf. Die Spuren rechnen ihre Indikatoren je Schritt
# ueber die ganze Reihe; die volle Historie dauerte Stunden.
KERZEN = 1200


def _inventar(ordner):
    """{pfad: groesse} eines Ordners, ohne __pycache__."""
    aus = {}
    for wurzel, _, dateien in os.walk(ordner):
        if "__pycache__" in wurzel:
            continue
        for d in dateien:
            p = os.path.join(wurzel, d)
            try:
                aus[p] = os.path.getsize(p)
            except OSError:
                aus[p] = -1
    return aus


class ReplayTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = replay.verzeichnis
        replay.verzeichnis = lambda: self.tmp.name

    def tearDown(self):
        replay.verzeichnis = self.alt
        self.tmp.cleanup()


class NichtsAusserhalbTest(ReplayTest):
    def test_replay_ruehrt_den_echten_spurenordner_nicht_an(self):
        spur = os.path.join(HANDEL, "supertrend")
        vorher = _inventar(spur)
        replay.lauf_a("supertrend", gebuehr_pct=0.1, lauf="test", max_kerzen=KERZEN)
        self.assertEqual(vorher, _inventar(spur))

    def test_replay_ruehrt_die_auss_er_haus_kopie_nicht_an(self):
        ziel = "Q:\\Handel_Journal\\supertrend"
        if not os.path.isdir(ziel):
            self.skipTest("Q: nicht angeschlossen")
        vorher = _inventar(ziel)
        replay.lauf_a("supertrend", gebuehr_pct=0.1, lauf="test", max_kerzen=KERZEN)
        self.assertEqual(vorher, _inventar(ziel))

    def test_replay_schreibt_in_den_backtest_ordner(self):
        runden, offen = replay.lauf_a("supertrend", gebuehr_pct=0.1,
                                      lauf="test", max_kerzen=KERZEN)
        ordner = replay.buch_ordner("supertrend", "test")
        self.assertTrue(os.path.isfile(os.path.join(ordner, "handelsjournal.csv")))
        self.assertTrue(ordner.startswith(self.tmp.name))
        self.assertGreater(len(runden), 0)

    def test_das_journal_ist_lesbar_und_liefert_runden(self):
        replay.lauf_a("supertrend", gebuehr_pct=0.1, lauf="test", max_kerzen=KERZEN)
        k = replay.kennzahlen(os.path.join(replay.buch_ordner("supertrend", "test"),
                                           "handelsjournal.csv"))
        # Der eigentliche Punkt: das Journal hat EIN-/AUSSTIEGSZEILEN, sonst
        # gaebe es nichts zu paaren und die Runden waeren 0.
        self.assertGreater(k["runden"], 0)
        self.assertIn("f_max", k)


class BuchOrdnerTest(ReplayTest):
    def test_wachen_kopie_zeigt_nach_innen(self):
        ordner = replay.buch_ordner("supertrend", "a")
        with open(os.path.join(ordner, "wachen.json"), encoding="utf-8") as f:
            w = json.load(f)
        self.assertNotIn("Q:", str(w.get("journal_zweitziel")))
        self.assertEqual(ordner, w["journal_zweitziel"])
        self.assertFalse(w["handel_erlaubt"])
        self.assertTrue(ordner.startswith(self.tmp.name))

    def test_spur_ohne_handeln_wird_benannt(self):
        with self.assertRaises(FileNotFoundError):
            replay.spur_modul("gibtesnicht")


class FensterTest(ReplayTest):
    """Das rollierende Fenster: schnell, treu und plausibel.

    Im Betrieb sieht eine Spur nie die ganze Geschichte, sondern ihre feste
    `kerzen_anzahl`. Das Fenster bildet das nach - und macht den Lauf ueber
    Jahre erst bezahlbar (ohne Fenster ist jeder Schritt O(n), der Lauf O(n^2)).
    """

    def test_fenster_liefert_runden_und_keine_unmoeglichen_werte(self):
        runden, offen = replay.lauf_a("supertrend", 0.1, "fenster",
                                      max_kerzen=3000, fenster=400)
        self.assertGreater(len(runden), 10)
        for r in runden:
            # Stop 5 %, Ziel 10 % - mehr als 50 % Bewegung ist bei diesen
            # Regeln unmoeglich und waere das Zeichen eines Instrumenten-
            # Durcheinanders (Kerzen des einen, Position des anderen).
            self.assertLess(abs(r["ausstieg"] / r["einstieg"] - 1.0), 0.5)
            self.assertIn(r["inst"], ("BTC-USDC", "ETH-USDC", "SOL-USDC"))

    def test_fenster_begrenzt_die_kerzen_je_schritt(self):
        """Die EIGENSCHAFT, auf die es ankommt - nicht die Wanduhr.

        Vorher verglich dieser Test zwei Laufzeiten (mit Fenster < ohne). Gemessen
        am 29.09.2026 auf drei Durchgaengen ergab das Verhaeltnis 0.97, also fast
        nichts: bei 2000 Kerzen dominiert die Ausfuehrungszeit, und der
        O(n)-gegen-O(n^2)-Unterschied waechst erst mit der Laenge. Ein Test auf
        die Uhr meldet damit die Maschinenlast (hier laufen drei Risikostufen
        parallel), nicht die Regel.

        Geprueft wird stattdessen, was das Fenster tut: die Spur sieht je Schritt
        hoechstens `fenster` Kerzen; ohne Fenster waechst die Zahl mit dem Lauf.
        """
        # ACHTUNG: `spur_modul()` laedt das Spurenmodul bei JEDEM Aufruf NEU
        # (`module_from_spec` auf einen frischen Spec). Ein Patch am zurueck-
        # gegebenen Objekt trifft deshalb ein anderes als das, mit dem `lauf_a`
        # arbeitet - der erste Versuch zaehlte genau deshalb nichts. Gepatcht
        # wird darum `replay.spur_modul` selbst: so bekommt JEDES von `lauf_a`
        # erzeugte Modul die zaehlende Huelle.
        echt_spur_modul = replay.spur_modul
        gesehen = []

        def gefaelscht(spur):
            m = echt_spur_modul(spur)
            echt = m.pruefe_ausstiege

            def zaehlend(z, k, w, **kw):
                gesehen.append(len(k))
                return echt(z, k, w, **kw)

            m.pruefe_ausstiege = zaehlend
            return m

        replay.spur_modul = gefaelscht
        self.addCleanup(setattr, replay, "spur_modul", echt_spur_modul)
        try:
            replay.lauf_a("supertrend", 0.1, "fenster", max_kerzen=2000, fenster=400)
        finally:
            replay.spur_modul = echt_spur_modul
        self.assertTrue(gesehen, "pruefe_ausstiege wurde nie gerufen - Aufbau geaendert?")
        self.assertLessEqual(max(gesehen), 400,
                             "mit Fenster sah die Spur %d Kerzen" % max(gesehen))

        # Ein "ohne Fenster" gibt es nicht: fehlt die Zahl, setzt `lauf_a` die
        # Vorgabe der Spur (`fenster_vorgabe`) - der Lauf sieht nie die ganze
        # Reihe. Die Gegenprobe muss deshalb ein GROSSES Fenster setzen.
        gesehen.clear()
        replay.spur_modul = gefaelscht
        try:
            replay.lauf_a("supertrend", 0.1, "weit", max_kerzen=2000, fenster=2000)
        finally:
            replay.spur_modul = echt_spur_modul
        self.assertGreater(max(gesehen), 400,
                           "ein weites Fenster sieht nicht mehr Kerzen - wirkt der Parameter ueberhaupt?")

    def test_vorgabe_respektiert_die_mindestkerzen_der_spur(self):
        """Die Lehre vom 25.09.2026, als Regel festgenagelt.

        `fenster_vorgabe` darf nicht unter die eigene Anforderung der Spur
        fallen: macd_mtf braucht fuer seinen 16er-Rahmen ~560 Basiskerzen, mit
        Fenster 400 kam kein einziger Handel zustande - der Lauf meldete
        "0 Runden", und das sieht wie ein Messergebnis aus.
        """
        self.assertGreaterEqual(replay.fenster_vorgabe({"kerzen_anzahl": 400,
                                                        "mindest_kerzen": 600}), 640)
        self.assertEqual(replay.fenster_vorgabe({"kerzen_anzahl": 900,
                                                  "mindest_kerzen": 300}), 900)


class FensterOderHistorieTest(ReplayTest):
    """Ein zu kleines Fenster ist KEINE fehlende Historie (01.10.2026).

    Gemessen: `--max-kerzen 200` bei mindest_kerzen 300 schnitt die Reihe VOR
    der Pruefung auf 200 Kerzen; die Pruefung schlug an und der Lauf meldete
    "keine Historie fuer supertrend - erst auffuellen", obwohl 12.559 Kerzen
    auf der Platte lagen. Genau diese Anweisung aendert in diesem Fall nichts -
    der Grund gehoert in den Text, sonst folgt der Leser einer Sackgasse.
    """

    def _wachen(self, spur):
        with open(os.path.join(HANDEL, spur, "wachen.json"), encoding="utf-8") as f:
            return json.load(f)

    def _kerzen_fuer(self, spur, w, max_kerzen):
        """kerzen_fuer ohne die Meldungszeilen auf stdout."""
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            return replay.kerzen_fuer(spur, w, None, max_kerzen)

    def test_fenster_unter_dem_bedarf_nennt_das_fenster(self):
        w = self._wachen("supertrend")
        with self.assertRaises(replay.HistorieFehlt) as ctx:
            self._kerzen_fuer("supertrend", w, 200)
        text = str(ctx.exception)
        self.assertIn("Fenster zu klein", text)
        self.assertIn(str(replay.bedarf(w)), text)
        self.assertNotIn("auffuellen", text)      # Nachfuellen hilft hier NICHT

    def test_zu_kleines_fenster_kommt_nicht_bis_zum_lauf(self):
        import contextlib
        import io
        with self.assertRaises(replay.HistorieFehlt), \
                contextlib.redirect_stdout(io.StringIO()):
            replay.lauf_a("supertrend", 0.1, "test", max_kerzen=200)

    def test_fehlende_historie_behaelt_die_auffuell_anweisung(self):
        """Der ANDERE Grund - hier ist Nachfuellen wirklich die Tat.

        GEMESSEN 04.10.2026: dieser Test las die ECHTE Historie und brauchte
        ein Instrument, von dem es KEINE gibt. Nach dem Nachladen der Daten
        (BNB 1H hat inzwischen 50.422 Kerzen) faellt die Annahme, und der
        Test wurde rot - ohne dass sich am Code etwas geaendert hatte. Ein
        Test, der einen Datenstand einfriert, meldet den Datenbestand, nicht
        die Regel.

        Jetzt traegt der Attrappen-Leser den Fall: `_nur()` behauptet
        12 Kerzen fuer jedes Instrument, die 3x weniger als `bedarf`. Damit
        entscheidet allein die Regel, welcher der beiden Gruende gemeldet wird.
        """
        w = dict(self._wachen("supertrend"), instrumente=["BNB"],
                 kerzen_takt="1H")
        alt = replay.historie_binance.lade
        replay.historie_binance.lade = lambda inst, takt: [[0, 1.0] * 1] * 12
        try:
            with self.assertRaises(replay.HistorieFehlt) as ctx:
                self._kerzen_fuer("supertrend", w, None)
        finally:
            replay.historie_binance.lade = alt
        text = str(ctx.exception)
        self.assertIn("auffuellen", text)
        self.assertNotIn("Fenster zu klein", text)

    def test_gegenprobe_meldet_bei_leeren_kerzen_nicht_mehr_gleich(self):
        """Vorher lief `gegenprobe` mit leerem Kerzen-Dict durch und meldete
        zweimal null Runden als "gleich: true" - ein falscher Freispruch."""
        import contextlib
        import io
        with self.assertRaises(replay.HistorieFehlt), \
                contextlib.redirect_stdout(io.StringIO()):
            replay.gegenprobe("supertrend", 0.1, "test", max_kerzen=200)

    def test_kleines_fenster_auf_der_kommandozeile_ist_ein_eingabefehler(self):
        """`--fenster 100` kann keinen Schritt rechnen. Vorher lief das durch
        und meldete still "0 Runden"; jetzt eine Zeile und Exit 2 statt eines
        Tracebacks."""
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(HANDEL, "replay.py"),
                            "--spur", "supertrend", "--gebuehr", "0.1",
                            "--fenster", "100", "--lauf", "test_fenster"],
                           cwd=HANDEL, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("Fenster zu klein", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_eine_spur_ohne_instrumente_sagt_das(self):
        """orb und orbk stehen in der Replay-Liste des Leitstands, ihr
        handeln.py hat aber kein `lade_wachen` - die Verweigerung muss den
        Grund nennen, statt ihn zu raten („Historie zu kurz UND Fenster zu
        klein" war zweimal falsch)."""
        import subprocess
        r = subprocess.run([sys.executable, os.path.join(HANDEL, "replay.py"),
                            "--spur", "orb", "--gebuehr", "0.1", "--lauf", "x"],
                           cwd=HANDEL, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("nennt kein Instrument", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_bedarf_ist_mindestkerzen_plus_puffer(self):
        self.assertEqual(replay.bedarf({"mindest_kerzen": 600}), 620)
        self.assertEqual(replay.bedarf({}), 320)          # Vorgabe 300 + 20

    def test_bedarf_fuer_liest_die_wachen_ohne_das_modul_zu_laden(self):
        self.assertEqual(replay.bedarf_fuer("supertrend"),
                         replay.bedarf(self._wachen("supertrend")))
        self.assertIsNone(replay.bedarf_fuer("gibt-es-nicht"))


class FamilieBTest(ReplayTest):
    """Familie B laeuft ueber `spur_buch.zyklus` - und darf nichts nach aussen.

    Drei Dinge muessen nach dem Lauf unveraendert sein: der Bus (kein Eintrag),
    die Zeituhr von `spur_buch` und das echte Q:-Ziel.
    """

    def test_zu_kleines_fenster_ist_kein_stilles_null_runden(self):
        """Familie B hatte dieselbe Luecke wie Familie A: `max_kerzen` schnitt
        VOR der Schleife, die Schleife lief leer und der Lauf meldete
        "0 Runden" - eine Zahl, die wie ein Messergebnis aussieht."""
        import contextlib
        import io
        with self.assertRaises(replay.HistorieFehlt) as ctx, \
                contextlib.redirect_stdout(io.StringIO()):
            replay.lauf_b("trendwende_btc", gebuehr_pct=0.05,
                          lauf="test_kurz", max_kerzen=100, fenster=100)
        self.assertIn("Fenster zu klein", str(ctx.exception))

    def test_lauf_b_bucht_in_den_backtest_ordner(self):
        k, zeilen = replay.lauf_b("trendwende_btc", gebuehr_pct=0.05,
                                  lauf="test", max_kerzen=1000, fenster=400)
        ordner = replay.buch_ordner("trendwende_btc", "test")
        self.assertTrue(os.path.isfile(os.path.join(ordner, "handelsjournal.csv")))
        self.assertTrue(ordner.startswith(self.tmp.name))
        self.assertIn("runden", k)

    def test_lauf_b_oeffnet_keine_bus_meldung(self):
        # spur_buch zuerst: es legt den Bus-Ordner in sys.path (ereignis.py).
        import spur_buch
        import ereignis
        gerufen = []
        alt_bus, alt_spiegel = ereignis.lauf, spur_buch.spiegeln
        ereignis.lauf = lambda name: gerufen.append(name)
        try:
            replay.lauf_b("trendwende_btc", gebuehr_pct=0.05, lauf="test2",
                          max_kerzen=700, fenster=400)
        finally:
            ereignis.lauf, spur_buch.spiegeln = alt_bus, alt_spiegel
        self.assertEqual([], gerufen)

    def test_lauf_b_stellt_die_zeituhr_wieder_her(self):
        import spur_buch
        vorher = spur_buch.zeit_quelle
        replay.lauf_b("trendwende_btc", gebuehr_pct=0.05, lauf="test3",
                      max_kerzen=700, fenster=400)
        self.assertIs(vorher, spur_buch.zeit_quelle)

    def test_die_uhr_laeuft_mit_den_kerzen_nicht_mit_der_wanduhr(self):
        """Beweis, dass die Zeituhr gesetzt wird: die Journalzeiten spannen
        den historischen Zeitraum ab, nicht die Minuten des Laufs."""
        import csv
        replay.lauf_b("trendwende_btc", gebuehr_pct=0.05, lauf="test4",
                      max_kerzen=1500, fenster=400)
        pfad = os.path.join(replay.buch_ordner("trendwende_btc", "test4"),
                            "handelsjournal.csv")
        with open(pfad, encoding="utf-8", newline="") as f:
            zeiten = sorted(r["zeit"] for r in csv.DictReader(f) if r.get("zeit"))
        self.assertGreater(len(zeiten), 0)
        import datetime as dt
        erste = dt.datetime.fromisoformat(zeiten[0])
        letzte = dt.datetime.fromisoformat(zeiten[-1])
        self.assertGreater((letzte - erste).days, 20)

    def test_nicht_nachrechenbare_spur_wird_verweigert_statt_geraten(self):
        with self.assertRaises(RuntimeError) as ctx:
            replay.lauf_b("moondev_whale", gebuehr_pct=0.05, lauf="test5")
        self.assertIn("nicht nachrechenbar", str(ctx.exception))
        self.assertIn("50030", str(ctx.exception))


class GebuehrTest(unittest.TestCase):
    """Die Gebuehr ist der teuerste Fehler eines Backtests - sie muss stimmen."""

    def test_wachen_wert_hat_vorrang(self):
        self.assertEqual(0.6, replay.gebuehr_fuer("kraken", {"gebuehr_taker": 0.006}))
        self.assertEqual(0.05, replay.gebuehr_fuer("xperp", {"gebuehr_taker": 0.0005}))

    def test_fehlender_wert_faellt_auf_den_boersensatz_der_spur(self):
        self.assertEqual(0.1, replay.gebuehr_fuer("squeeze", {}))
        self.assertEqual(0.05, replay.gebuehr_fuer("liq_wand", {}))
        self.assertEqual(0.6, replay.gebuehr_fuer("orbk", {}))

    def test_kein_pauschalwert_und_keine_stille_null(self):
        for spur in replay.SPUREN_TEIL_A:
            self.assertGreater(replay.gebuehr_fuer(spur, {}), 0.0)

    def test_unbekannte_spur_wird_gemeldet_statt_geraten(self):
        with self.assertRaises(KeyError):
            replay.gebuehr_fuer("diegibtesnicht", {})


class GegenprobeTest(ReplayTest):
    """Der neue Kern muss dasselbe rechnen wie der alte - sonst luegt er."""

    def test_squeeze_stimmt_mit_backtest_prognose_ueberein(self):
        e = replay.gegenprobe("squeeze", gebuehr_pct=0.1, max_kerzen=KERZEN)
        self.assertTrue(e["gleich"], "Abweichungen: %s" % e["abweichungen"][:3])
        self.assertGreater(e["runden"], 0)
        self.assertEqual(e["runden"], e["runden_alt"])


if __name__ == "__main__":
    unittest.main()

class GebuehrVorgabeTest(unittest.TestCase):
    """Die Vorgabe der Gebuehr ist der GEMESSENE Satz der Spur (01.10.2026).

    Vorher stand im Argument `--gebuehr` fest 0.1. Fuer die vier
    Indikator-Spuren (OKX-Spot, 0,10 %/Seite) war das richtig, fuer `mosaic`
    (Kraken, 0,60 %/Seite) rechnete jeder Backtest damit SECHSMAL zu guenstig -
    und niemand sah es, weil die Zahl plausibel aussah.
    """

    def test_vorgabe_kommt_aus_der_wachen_der_spur(self):
        # 04.10.2026: mosaic stand hier mit 0,6 (Kraken). Die Spur handelt seit
        # dem 30.09.2026 (Commit e6f2715c, Auftrag Max "nur noch omnitrade auf
        # kraken") auf OKX-Spot, gemessen 0,10 %/Seite (01.10.2026). Die Zahl
        # kommt aus wachen.json - sie wandert mit der Börse und darf hier nicht
        # festgeschrieben stehen, sonst prueft der Test den alten Stand.
        for spur, soll in (("mosaic", 0.1), ("supertrend", 0.1),
                           ("orbk", 0.6), ("liq_wand", 0.05)):
            satz, quelle = replay.gebuehr_aufloesen(None, spur)
            self.assertEqual(soll, satz, spur)
            self.assertIn("wachen.json", quelle, spur)

    def test_eigener_wert_schlaegt_die_vorgabe(self):
        satz, quelle = replay.gebuehr_aufloesen(0.25, "mosaic")
        self.assertEqual(0.25, satz)
        self.assertIn("--gebuehr", quelle)

    def test_null_ist_ein_erlaubter_eigener_wert(self):
        satz, _ = replay.gebuehr_aufloesen(0.0, "supertrend")
        self.assertEqual(0.0, satz)

    def test_der_aufruf_ohne_gebuehr_bleibt_moeglich(self):
        """Kein stiller Rueckfall auf 0: der Satz MUSS aus der Spur kommen."""
        satz, _ = replay.gebuehr_aufloesen(None, "gitter")
        self.assertNotEqual(0.0, satz)
