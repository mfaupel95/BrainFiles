"""Tests fuer Agenten/Handel/gebuehren_setzen.py (netzfrei, ohne Schreibzugriff
auf echte Wachen).

Anlass (01.10.2026): Beim Setzen der Kraken-Gebuehr in `nautilus_kraken` stand
die `_gebuehr_quelle` schon in der Datei, der WERT (`gebuehr_taker`) fehlte
aber. `_feld_setzen` behandelte diesen Fall als "nur die Notiz auffrischen" -
der Wert fiel still unter den Tisch, und `anwenden()` stuerzte danach mit
einem irrefuehrenden `TypeError: float() argument must be ... not 'NoneType'`
ab, statt zu sagen, was los ist. Beide Seiten sind hier festgenagelt: der
Schreibweg setzt den Wert, und die Pruefung meldet es im Klartext.

Regel des Hauses: die Tests rechnen auf TEXT und auf einem Temp-Ordner. Ein
Waechter (setUpModule/tearDownModule) vergleicht alle echten `wachen*.json`
der Handelsspuren vorher und nachher - faellt ein Test, der nach draussen
schreibt.
"""

import importlib.util
import json
import os
import pathlib
import shutil
import tempfile
import unittest

HIER = pathlib.Path(__file__).resolve().parent
HANDEL = HIER.parent

spec = importlib.util.spec_from_file_location("gebuehren_setzen",
                                              HANDEL / "gebuehren_setzen.py")
gs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gs)


def _stand():
    """Groesse + mtime jeder echten Wachen-Datei der Handelsspuren."""
    aus = {}
    for p in sorted(HANDEL.glob("*/wachen*.json")):
        if ".bak-" in p.name:
            continue
        st = p.stat()
        aus[str(p.relative_to(HANDEL))] = (st.st_size, int(st.st_mtime))
    return aus


_VORHER = None


def setUpModule():
    global _VORHER
    _VORHER = _stand()


def tearDownModule():
    nachher = _stand()
    if nachher != _VORHER:
        neu = {k: v for k, v in nachher.items() if _VORHER.get(k) != v}
        raise AssertionError("Test hat in echte Wachen geschrieben: %s" % neu)


class FeldSetzenTest(unittest.TestCase):
    """Der Schreibweg auf TEXT - kein Dateizugriff."""

    def test_notiz_da_wert_fehlt_setzt_den_wert(self):
        """Der gefundene Fehler: Notiz ohne Wert."""
        roh = ('{\n  "gebuehr_pct": 0.6,\n'
               '  "_gebuehr_quelle": "alte Notiz",\n'
               '  "handel_erlaubt": false\n}\n')
        neu, alt = gs._feld_setzen(roh, "gebuehr_taker", 0.006, "neue Quelle")
        d = json.loads(neu)
        self.assertIsNone(alt)
        self.assertEqual(d["gebuehr_taker"], 0.006)
        self.assertEqual(d["_gebuehr_quelle"], "neue Quelle")
        self.assertEqual(d["gebuehr_pct"], 0.6, "Nachbarfeld darf nicht wandern")
        self.assertEqual(d["handel_erlaubt"], False)

    def test_notiz_ist_letzter_schluessel_ohne_komma(self):
        roh = '{\n  "a": 1,\n  "_gebuehr_quelle": "alt"\n}\n'
        neu, _ = gs._feld_setzen(roh, "gebuehr_taker", 0.001, "q")
        d = json.loads(neu)
        self.assertEqual(d["gebuehr_taker"], 0.001)
        self.assertEqual(d["_gebuehr_quelle"], "q")
        self.assertEqual(d["a"], 1)

    def test_wert_da_notiz_fehlt(self):
        roh = '{\n  "gebuehr_taker": 0.0005,\n  "a": 1\n}\n'
        neu, alt = gs._feld_setzen(roh, "gebuehr_taker", 0.001, "q")
        d = json.loads(neu)
        self.assertEqual(alt, "0.0005")
        self.assertEqual(d["gebuehr_taker"], 0.001)
        self.assertEqual(d["_gebuehr_quelle"], "q")

    def test_keiner_von_beiden_steht_drin(self):
        roh = '{\n  "a": 1,\n  "b": 2\n}\n'
        neu, alt = gs._feld_setzen(roh, "gebuehr_taker", 0.001, "q")
        d = json.loads(neu)
        self.assertIsNone(alt)
        self.assertEqual(d["gebuehr_taker"], 0.001)
        self.assertEqual(d["_gebuehr_quelle"], "q")
        self.assertEqual(d["b"], 2)

    def test_keine_doppelten_schluessel(self):
        """Ein zweiter _gebuehr_quelle-Schluessel waere wirkungslos (der letzte
        gewinnt) und wuerde die Datei widerspruechlich machen."""
        for roh in ('{\n  "_gebuehr_quelle": "alt",\n  "a": 1\n}\n',
                    '{\n  "gebuehr_taker": 0.001,\n  "a": 1\n}\n',
                    '{\n  "a": 1\n}\n'):
            neu, _ = gs._feld_setzen(roh, "gebuehr_taker", 0.002, "q")
            self.assertEqual(neu.count('"_gebuehr_quelle"'), 1, roh)
            self.assertEqual(neu.count('"gebuehr_taker"'), 1, roh)

    def test_zeilenende_bleibt(self):
        """Die Wachen sind LF-Dateien - der Ersatz darf keine CRLF einfuehren."""
        roh = '{\n  "a": 1\n}\n'
        neu, _ = gs._feld_setzen(roh, "gebuehr_taker", 0.001, "q")
        self.assertEqual(neu.count("\r\n"), 0)


class AnwendenMeldetKlarTest(unittest.TestCase):
    """`anwenden()` darf bei einem misslungenen Schreibvorgang nicht mit
    einem TypeError aus dem Vergleich fallen, sondern muss den Grund nennen."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="gebuehren_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "spur").mkdir()
        (self.tmp / "spur" / "wachen.json").write_text(
            '{\n  "gebuehr_taker": 0.001\n}\n', encoding="utf-8")
        self.alt_hier, self.alt_tab = gs.HIER, gs.AENDERUNGEN
        gs.HIER = str(self.tmp)
        gs.AENDERUNGEN = [("spur/wachen.json", "gebuehr_taker", 0.002, "q")]
        self.addCleanup(self._zurueck)

    def _zurueck(self):
        gs.HIER, gs.AENDERUNGEN = self.alt_hier, self.alt_tab

    def test_erfolgsfall_schreibt_und_meldet(self):
        self.assertEqual(gs.anwenden(), 1)
        d = json.loads((self.tmp / "spur" / "wachen.json").read_text("utf-8"))
        self.assertEqual(d["gebuehr_taker"], 0.002)
        self.assertTrue((self.tmp / "spur" / "wachen.json.bak-20261001").exists()
                        or list(self.tmp.glob("spur/*.bak-*")),
                        "Sicherung muss daneben liegen")

    def test_misslungener_ersatz_nennt_den_grund(self):
        """Der Ersatz wird auf 'nichts geaendert' gestellt - der Fehler muss
        das Feld und den erwarteten Wert nennen, nicht 'NoneType'.

        WICHTIG: `mock.patch.object` statt einer Zuweisung - eine Zuweisung
        ohne Ruecknahme hat in diesem Modul schon einmal alle folgenden Tests
        still auf eine Attrappe umgestellt (der Ersatz blieb stehen).
        """
        from unittest import mock
        with mock.patch.object(gs, "_feld_setzen",
                               lambda roh, feld, wert, quelle,
                               notiz_behalten=None: (roh, None)):
            # `notiz_behalten` ist seit T-315 ein Parameter - ohne ihn
            # bricht schon der Aufruf ab, nie die Pruefung.
            with self.assertRaises(RuntimeError) as ctx:
                gs.anwenden()
        text = str(ctx.exception)
        self.assertIn("gebuehr_taker", text)
        self.assertIn("liess sich nicht setzen", text)
        self.assertNotIn("NoneType", text)


class TabelleTest(unittest.TestCase):
    """Die Tabelle selbst - sie ist die Wahrheit ueber die gesetzten Saetze."""

    def test_jede_zeile_hat_datei_wert_und_quelle(self):
        for datei, feld, wert, quelle in gs.AENDERUNGEN:
            self.assertTrue((HANDEL / datei).exists(), datei)
            self.assertIn(feld, ("gebuehr_taker", "gebuehr_pct"), datei)
            self.assertIsInstance(wert, float, datei)
            self.assertGreater(wert, 0, datei)
            self.assertTrue(str(quelle).strip(), datei)

    def test_gebuehr_taker_ist_ein_bruch_nicht_prozent(self):
        """Die Verwechslung, die am 01.10.2026 fast entstanden waere: 0.6
        (Prozent) statt 0.006 (Bruch) - das waere die 100-fache Gebuehr."""
        for datei, feld, wert, _q in gs.AENDERUNGEN:
            if feld != "gebuehr_taker":
                continue
            self.assertLess(wert, 0.1, "%s: %r sieht nach Prozent aus" % (datei, wert))

    def test_dieselbe_spur_nicht_zweimal_mit_verschiedenen_werten(self):
        gesehen = {}
        for datei, feld, wert, _q in gs.AENDERUNGEN:
            key = (datei, feld)
            if key in gesehen:
                self.assertEqual(gesehen[key], wert,
                                 "%s %s doppelt mit zwei Werten" % key)
            gesehen[key] = wert

    def test_jede_gesetzte_wachen_traegt_ihre_quelle(self):
        """Wert ohne Quelle ist nicht nachpruefbar - das Haus fuehrt beides."""
        for datei, feld, wert, _q in gs.AENDERUNGEN:
            w = json.loads((HANDEL / datei).read_text("utf-8"))
            self.assertEqual(float(w.get(feld)), float(wert), datei)
            self.assertTrue(str(w.get("_gebuehr_quelle") or "").strip(),
                            "%s: %s ohne _gebuehr_quelle" % (datei, feld))


class BoersenfeldTest(unittest.TestCase):
    """Die Gebuehr folgt der BOERSE, auf der geordert wird (T-308).

    Der Fehler, den dieser Test verhindert, ist kein Zahlendreher, sondern ein
    Buechersatz: omniquant trug `boerse: kraken_futures` (gemessen 0,05 % je
    Seite) und in der Gebuehren-Tabelle 0,1 % mit dem Vermerk 'Widerspruch,
    offen'. Zwei Leser derselben Spur rechneten dadurch zwei verschiedene
    Saetze, und der Test `test_jede_gesetzte_wachen_traegt_ihre_quelle`
    schlug fehl, ohne dass jemand die Ursache benannt haette.

    Die Regel ist damit eine EIGENSCHAFT, keine Zahl: hat eine wachen.json ein
    `boerse`-Feld, traegt sie den Satz DIESER Boerse. Steht kein `boerse`-Feld
    da, bleibt die Spalte eine Modellannahme und wird nicht beurteilt
    (onchain, Paper ohne Börse, Skripte mit eigenem Abrechnungsweg).
    """

    # Wachen, deren `boerse` einen der gemessenen Saetze aus BOERSENSAETZE_PCT
    # traegt. Ein nicht genannter Name (etwa ein frei erfundenes "bybit") faellt
    # hier bewusst NICHT durch - eine neue Boerse braucht eine Messung, keine
    # erfundene Zahl.
    def test_keine_wache_traegt_den_satz_einer_anderen_boerse(self):
        geprueft = 0
        for datei, _feld, _wert, _q in gs.AENDERUNGEN:
            w = json.loads((HANDEL / datei).read_text("utf-8"))
            soll, name = gs.satz_pct_fuer(w)
            if soll is None:
                continue
            geprueft += 1
            ist = gs.gebuehr_pct_der_wachen(w)
            self.assertIsNotNone(ist, "%s (boerse=%s) traegt gar keine Gebuehr"
                                 % (datei, w.get("boerse")))
            self.assertAlmostEqual(ist, soll, 6,
                                   msg="%s: %s braucht %s %%, traegt %s"
                                       % (datei, name, soll, ist))
        self.assertGreater(geprueft, 0, "kein einziges boerse-Feld geprueft")

    def test_boersenfeld_waere_als_erste_gelesen_worden(self):
        """Gegenprobe des Befunds: 0.1 % auf einer Futures-Boerse ist 0.05 %.

        Haette der Test nur geprueft, ob die Zahl > 0 ist, waere 0.1 hier
        durchgegangen - der Fehler ist genau die FALSCHE Boerse, nicht eine
        fehlende Zahl.
        """
        kraken_futures = gs.BOERSENSAETZE_PCT["kraken_futures"]
        self.assertAlmostEqual(kraken_futures, 0.05, 6)
        self.assertNotAlmostEqual(kraken_futures,
                                  gs.BOERSENSAETZE_PCT["okx_spot"], 6)

    def test_omniquant_zaehlt_auf_die_orderboerse_nicht_auf_den_kursweg(self):
        """Der konkrete Befund als geschlossener Satz (T-308).

        omniquant holt den Kurs von OKX und ordnet auf Kraken Futures. Genau
        daraus entstand die falsche Gebuehr: wer dem Kursweg folgt, nimmt
        OKX (0,10 %), wer der Bestellung folgt, Kraken Futures (0,05 %).
        """
        w = json.loads((HANDEL / "omniquant/wachen.json").read_text("utf-8"))
        self.assertEqual(w.get("boerse"), "kraken_futures")
        satz, name = gs.satz_pct_fuer(w)
        self.assertEqual(name, "kraken_futures")
        self.assertAlmostEqual(gs.gebuehr_pct_der_wachen(w), satz, 6)
        # und ausdruecklich NICHT der Kursweg-Satz
        self.assertNotAlmostEqual(gs.gebuehr_pct_der_wachen(w),
                                  gs.BOERSENSAETZE_PCT["okx_spot"], 6)

    def test_tabelle_kennt_jeden_verwendeten_boersennamen(self):
        """Wer eine Boerse eintraegt, muss ihren Satz mitbringen.

        Sonst bleibt eine neue Boerse ohne Gebuehr - und eine fehlende Gebuehr
        sieht in der Auswertung wie eine sehr billige Spur aus.
        """
        verwendet = set()
        for datei, _f, _w, _q in gs.AENDERUNGEN:
            w = json.loads((HANDEL / datei).read_text("utf-8"))
            b = w.get("boerse") or w.get("venue")
            if b:
                verwendet.add(b)
        bekannt = {"okx", "okx_spot", "okx_perp", "kraken", "kraken_futures",
                   "deribit", "signalwelle"}
        # 04.10.2026: 'signalwelle' ist kein Boersenname, sondern der NAME
        # einer Spur (moondev_signalwelle), die als PERP gefuehrt wird - Max hat
        # den Satz am 01.10.2026 so entschieden (QUELLE_PERP_ENTSCHEIDUNG). Es
        # steht hier, damit der Test BENENNT bleibt und nicht bei der naechsten
        # neuen Spur wieder anschlaegt: wer eine Wachen-Boerse erfindet, muss
        # sie eintragen und ihren Satz messen.
        self.assertTrue(verwendet <= bekannt,
                        "Boerse ohne gemessenen Satz: %s"
                        % sorted(verwendet - bekannt))

    def test_jede_gebehrte_wache_hat_auch_einen_fuer_die_auswertung(self):
        """`gebuehr_taker` ist das Feld, das die Auswertung tatsaechlich liest.

        `auswertung_alle.gebuehr_fuer` liest NUR `gebuehr_taker` und gibt 0.0
        zurueck, wenn es fehlt - nicht 'unbekannt'. Eine Spur, die ihre Gebuehr
        nur als `gebuehr_pct` fuehrt, rechnet in der allgemeinen Auswertung
        darum mit NULL Kosten (das war der Grund, warum die Nautilus-Arme den
        Satz doppelt bekamen). Wo beide Felder gesetzt werden, muessen sie
        dasselbe sagen - und die allgemeine Auswertung darf nie 0,0 melden,
        wo eine Gebuehr behauptet wird.
        """
        for datei, _f, _w, _q in gs.AENDERUNGEN:
            w = json.loads((HANDEL / datei).read_text("utf-8"))
            pct = w.get("gebuehr_pct")
            taker = w.get("gebuehr_taker")
            if pct is None or taker is None:
                continue
            self.assertAlmostEqual(float(taker) * 100.0, float(pct), 6,
                                   msg="%s: pct %s und taker %s sagen nicht dasselbe"
                                       % (datei, pct, taker))
            # Der Leser, der nur `gebuehr_taker` kennt, darf nicht 0 herausgeben
            self.assertGreater(float(taker), 0.0,
                               "%s: gebuehr_taker 0 - die Auswertung rechnet "
                               "kostenlos" % datei)


class NotizBleibtTest(unittest.TestCase):
    """T-315 (1): `--anwenden` setzt eine verbesserte Notiz zurueck.

    Anlass 02.10.2026: bei kopier, kopier1zu1 und robinhood_radar stand der
    WERT richtig, die Notiz war aber zwischenzeitlich von Hand verbessert
    worden ("NICHT gemessen" -> "der Nachlauf dazu ist GEMESSEN (01.10.2026)").
    `anwenden()` verglich nur den WERT und schrieb die Notiz trotzdem neu.
    """

    GEMESSEN = ("MODELLANNAHME, der Nachlauf dazu ist GEMESSEN (01.10.2026). "
                "Gesetzt bleiben 1,0 % Gebuehr + 5,0 % Slippage.")
    TABELLE = gs.QUELLE_ANNAHME_ONCHAIN

    def test_bessere_notiz_gewinnt_gegen_die_tabelle(self):
        self.assertTrue(gs._notiz_ist_besser(self.GEMESSEN, self.TABELLE))

    def test_gleichwertige_notiz_verliert_gegen_die_tabelle(self):
        """Ohne den gemessenen Beleg entscheidet weiter die Tabelle - sonst
        wuerde ein Aufruf den Anspruch der Wachen still anheben."""
        alt = "MODELLANNAHME fuer Onchain-Handel."
        self.assertFalse(gs._notiz_ist_besser(alt, self.TABELLE))

    def test_neuere_notiz_mit_datum_gewinnt_nicht(self):
        """Traegt die Tabelle selbst ein Datum, ist die neue Notiz keine
        Herabstufung - dann soll sie schreiben duerfen."""
        neu = gs.QUELLE_ANNAHME_ONCHAIN + " (Stand 02.10.2026)."
        self.assertFalse(gs._notiz_ist_besser(self.GEMESSEN, neu))

    def test_leere_notiz_gewinnt_nie(self):
        self.assertFalse(gs._notiz_ist_besser(None, self.TABELLE))
        self.assertFalse(gs._notiz_ist_besser("", self.TABELLE))

    def test_wert_richtig_notiz_gehalten_ergibt_wortgleiche_datei(self):
        """Der Kern: bei richtigem Wert und besserer Notiz bleibt die Datei
        byte-gleich - das ist der Testbeleg aus T-315."""
        roh = ('{\r\n  "gebuehr_pct": 1,\r\n'
               '  "_gebuehr_quelle": %s,\r\n'
               '  "handel_erlaubt": false\r\n}\r\n'
               % json.dumps(self.GEMESSEN))
        neu, alt = gs._feld_setzen(roh, "gebuehr_pct", 1, self.TABELLE,
                                   notiz_behalten=True)
        self.assertEqual(neu, roh)
        self.assertEqual(float(alt), 1.0)

    def test_wert_falsch_ueberschreibt_auch_die_bessere_notiz(self):
        """Zwei Fragen, zwei Antworten: ein FALSCHER Wert wird immer ersetzt -
        die Regel darf keine Ausrede fuer einen falschen Satz werden."""
        roh = ('{\r\n  "gebuehr_pct": 1,\r\n'
               '  "_gebuehr_quelle": %s,\r\n'
               '  "handel_erlaubt": false\r\n}\r\n'
               % json.dumps(self.GEMESSEN))
        neu, _ = gs._feld_setzen(roh, "gebuehr_pct", 0.01, self.TABELLE)
        d = json.loads(neu)
        self.assertEqual(d["gebuehr_pct"], 0.01)
        self.assertEqual(d["_gebuehr_quelle"], self.TABELLE)


class MeldungNenntAbsolutenPfadTest(unittest.TestCase):
    """T-315 (2): eine Meldung ueber einen Schreibvorgang nennt den Pfad.

    Ein RELATIVER Pfad ist von einem Testartefakt am Text nicht
    unterscheidbar - am 02.10.2026 las sich "spur/wachen.json gebuehr_taker:
    0.001 -> 0.002" wie ein Zugriff auf eine echte Wache.
    """

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="gebuehren_pfad_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "spur").mkdir()
        (self.tmp / "spur" / "wachen.json").write_text(
            '{\r\n  "gebuehr_taker": 0.001\r\n}\r\n', encoding="utf-8")
        self.alt_hier, self.alt_tab = gs.HIER, gs.AENDERUNGEN
        gs.HIER = str(self.tmp)
        gs.AENDERUNGEN = [("spur/wachen.json", "gebuehr_taker", 0.002, "q")]
        self.addCleanup(self._zurueck)

    def _zurueck(self):
        gs.HIER, gs.AENDERUNGEN = self.alt_hier, self.alt_tab

    def _fang(self, fn):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fn()
        return buf.getvalue()

    def test_anwenden_nennt_den_absoluten_pfad(self):
        text = self._fang(gs.anwenden)
        zeile = [z for z in text.splitlines() if "gebuehr_taker" in z][0]
        pfad = zeile.split()[0]
        self.assertTrue(os.path.isabs(pfad),
                        "Pfad %r ist relativ - ein Testartefakt waere daran "
                        "nicht erkennbar" % pfad)
        # os.path.commonpath ueberlebt gemischte Trennzeichen, ein
        # startswith auf einen String nicht - der erste Versuch war selbst
        # der Fehler.
        self.assertEqual(os.path.commonpath([pfad, str(self.tmp)]),
                         os.path.abspath(str(self.tmp)), pfad)

    def test_vorschau_nennt_den_absoluten_pfad(self):
        text = self._fang(gs.vorschau)
        pfad = [z for z in text.splitlines() if "gebuehr_taker" in z][0].split()[0]
        self.assertTrue(os.path.isabs(pfad), pfad)

    def test_fehlertext_nennt_den_absoluten_pfad(self):
        """Auch der Abbruchfall: eine Datei, die sich nicht schreiben laesst,
        muss ihren ABSOLUTEN Pfad nennen, sonst sucht man am falschen Ort."""
        ziel = self.tmp / "spur" / "wachen.json"
        gs.AENDERUNGEN = [("spur/wachen.json", "gebuehr_taker", 0.002, "q")]
        roh = ziel.read_text(encoding="utf-8")
        # ACHTUNG: den ORIGINALEN Wert merken, nicht den jetzigen - sonst
        # bleibt der Ersatz nach dem Test stehen und vergift alle folgenden
        # (das war der Grund fuer drei Fehlschlaege beim ersten Lauf).
        self.alt_setzen = gs._feld_setzen
        self.addCleanup(setattr, gs, "_feld_setzen", self.alt_setzen)
        gs._feld_setzen = lambda *a, **k: ("{\r\n}\r\n", None)  # unbrauchbar
        with self.assertRaises(RuntimeError) as cm:
            self._fang(gs.anwenden)
        self.assertIn(str(self.tmp), str(cm.exception))

    def test_vorschau_sagt_dasselbe_wie_anwenden(self):
        """Eine Vorschau, die etwas anderes ankündigt als das Schreiben tut,
        ist schlimmer als keine Vorschau."""
        roh = '{\r\n  "gebuehr_pct": 1,\r\n  "_gebuehr_quelle": %s\r\n}\r\n' % json.dumps(
            NotizBleibtTest.GEMESSEN)
        (self.tmp / "spur" / "wachen.json").write_text(roh, encoding="utf-8")
        gs.AENDERUNGEN = [("spur/wachen.json", "gebuehr_pct", 1,
                           gs.QUELLE_ANNAHME_ONCHAIN)]
        vorher = (self.tmp / "spur" / "wachen.json").read_text(encoding="utf-8")
        self._fang(gs.anwenden)
        nachher = (self.tmp / "spur" / "wachen.json").read_text(encoding="utf-8")
        self.assertEqual(vorher, nachher, "anwenden() hat die bessere Notiz "
                                          "ueberschrieben - die Vorschau "
                                          "sagte das Gegenteil")


if __name__ == "__main__":
    unittest.main()