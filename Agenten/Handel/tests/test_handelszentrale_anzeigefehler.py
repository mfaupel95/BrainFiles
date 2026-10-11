r"""Anzeigefehler der Handelszentrale, am 30.09./01.10.2026 nachgemessen und behoben.

Eine Datei fuer die Klasse "das Fenster sagt etwas, das nicht stimmt" - jeder
Fall hat eine reine Funktion oder einen Pfad, der ohne Bildschirm pruefbar ist:

  * Risikostufe: `refresh()` las hart `zustand.json` - in der Ansicht "mittel"
    und "hoch" standen dort die Basis-Buecher, obwohl dieselbe Zentrale fuer
    Journale und das omnitrade-Haus-Buch ueber `stufenname()` die richtigen
    Dateien las. Zwei Lesarten in einem Fenster.
  * Waehrung: Spaltenkopf "Wert USD" und Fuss "Nominal ... USD" fuer ein
    Kraken-Buch in EUR (und seit 30.09. auch USDC/EURC). Die Regel liegt in
    `auswertung_alle.einheit_fuer()` - der Bericht nutzt sie laengst.
  * Winzigpreise: `kurs_fmt` endete bei "%.5f"; ein Einstieg von 3,14e-06
    (Memcoin-Spuren) stand als "0.00000" da - Einstieg, Stop und Ziel einer
    Position als drei Nullen.
  * Kursweg: `moondev_sniper` fuehrt seine Solana-Mints als `inst` und wurde
    als OKX-Instrument behandelt (kein Kurs, Chart ins Leere);
    `robinhood_radar` notiert auf einer Kette, die kein Hausleser kennt -
    beides sagt jetzt, was es ist.
  * Log: das ganze Protokoll wurde je Takt zweimal voll gelesen (85 KB laufend,
    1,0 MB rotiert), und jede Zeile ohne " ok" war rot - damit standen
    Betriebsmeldungen wie "Auto-Freigabe scanner" in Alarmfarbe.

Aufruf aus `Agenten/Handel/tests`:
    ..\scanner\.venv\Scripts\python.exe -m unittest test_handelszentrale_anzeigefehler
"""

import json
import os
import queue
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

HANDEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import handelszentrale as hz  # noqa: E402

UTC = timezone.utc


class StufenPfadTest(unittest.TestCase):
    """Die Ansicht einer Stufe muss die Buecher DIESER Stufe lesen."""

    def setUp(self):
        self.ursprung = hz.RISIKO

    def tearDown(self):
        hz.RISIKO = self.ursprung

    def test_Basis_Ohne_Suffix_Sonnst_mit(self):
        hz.RISIKO = None
        self.assertEqual(hz.stufenname("zustand.json"), "zustand.json")
        hz.RISIKO = "mittel"
        self.assertEqual(hz.stufenname("zustand.json"), "zustand.mittel.json")
        hz.RISIKO = "hoch"
        self.assertEqual(hz.stufenname("handelsjournal.csv"),
                         "handelsjournal.hoch.csv")

    def test_die_Wachen_bekommen_kein_Suffix(self):
        # Die Wachen werden beim Laden skaliert, nicht umbenannt
        # (Handel/risikostufe.py) - mit Suffix gelesen waere jede Sperre leer.
        hz.RISIKO = "mittel"
        self.assertEqual(hz.stufenname("wachen.json"), "wachen.json")

    def test_refresh_Liest_die_Zustandsdatei_der_Stufe(self):
        """Der gemerkte Pfad von `lade_json` - nicht die Anzeige, der Lesevorgang.

        Vor dem Fix stand in refresh() hart "zustand.json": die Spurtabelle,
        die Positionstabelle und die Fuss-Summe zeigten in "mittel"/"hoch" die
        Basis-Buecher, waehrend Konsole und omnitrade-Reiter laengst die
        Stufendateien lasen.
        """
        hz.RISIKO = "mittel"
        gesehen = []
        echt = hz.lade_json

        def merke(pfad):
            gesehen.append(pfad)
            return echt(pfad)

        try:
            root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        self.addCleanup(root.destroy)
        for methode in ("_starte_kurs_worker", "_starte_freqtrade_worker"):
            patcher = mock.patch.object(hz.Handelszentrale, methode)
            patcher.start()
            self.addCleanup(patcher.stop)
        with mock.patch.object(hz, "lade_json", merke):
            app = hz.Handelszentrale(root)
            app.refresh()
        zustands_dateien = [p for p in gesehen
                            if os.path.basename(p).startswith("zustand.")
                            and ".live." not in os.path.basename(p)]
        self.assertTrue(zustands_dateien,
                        "refresh() hat keine einzige Zustandsdatei gelesen")
        self.assertTrue(all(os.path.basename(p) == "zustand.mittel.json"
                            for p in zustands_dateien),
                        "die Stufe liest Basis-Dateien: %s"
                        % sorted({os.path.basename(p) for p in zustands_dateien}))
        basis = [p for p in gesehen if os.path.basename(p) == "zustand.json"]
        self.assertEqual(basis, [], "neben der Stufe wurde auch die Basis gelesen")


class WaehrungTest(unittest.TestCase):
    """Der Betrag nennt seine Waehrung; eine Summe ueber EUR und USD ist keine."""

    def test_kraken_Buch_in_USDC_ist_nicht_USD(self):
        z = {"positionen": [{"paar": "SOLUSDC", "waehrung": "USDC", "usd": 50.0}]}
        self.assertEqual(hz.waehrung_fuer("kraken", z), "USDC")

    def test_Kraken_Altbestand_ohne_Feld_ist_EUR(self):
        # Die Spur handelte bis 30.09.2026 nur in EUR - die richtige Antwort
        # fuer Positionen ohne Feld, nicht "unbekannt".
        z = {"positionen": [{"paar": "ATOMEUR", "eur": 50.0}]}
        self.assertEqual(hz.waehrung_fuer("kraken", z), "EUR")

    def test_Kontraktspur_ist_USD(self):
        self.assertEqual(hz.waehrung_fuer("xperp", {"positionen": []}), "USD")

    def test_unbekannte_Spur_ohne_Absturz(self):
        # Die Zentrale darf an der Berichtsregel nicht scheitern: sie zeigt
        # dann USD, aber sie steht still.
        self.assertEqual(hz.waehrung_fuer("gibt-es-nicht", None), "USD")

    def test_gruppen_nach_Waehrung_getrennt(self):
        positionen = [{"spur": "xperp", "wert_usd": 120.0},
                      {"spur": "xperp", "wert_usd": 30.0},
                      {"spur": "kraken", "wert_usd": 150.0}]
        zustaende = {"xperp": {},
                     "kraken": {"positionen": [{"paar": "SOLEUR", "eur": 150.0}]}}
        gruppen = hz.nominal_gruppen(positionen, zustaende)
        self.assertEqual([g[0] for g in gruppen], ["EUR", "USD"])
        self.assertEqual(gruppen[0][1], 150.0)
        self.assertEqual(gruppen[1][1], 150.0)     # 120 + 30
        self.assertEqual(gruppen[1][2], 2)

    def test_ohne_Positionen_keine_Summe(self):
        self.assertEqual(hz.nominal_gruppen([], {}), [])

    def test_wert_anzeige_ohne_Wert_ist_kein_Null_Betrag(self):
        self.assertEqual(hz.wert_anzeige(None, "USD"), "-")
        self.assertEqual(hz.wert_anzeige(0, "USD"), "-")
        self.assertEqual(hz.wert_anzeige(150.0, "EUR"), "150 EUR")


class WinzigPreisTest(unittest.TestCase):
    """Ein Token-Kurs von 3e-06 darf nicht als "0.00000" dastehen."""

    def test_skala_bis_ganz_klein(self):
        self.assertEqual(hz.kurs_fmt(2471.0), "2471.0")
        self.assertEqual(hz.kurs_fmt(42.5), "42.50")
        self.assertEqual(hz.kurs_fmt(2.5), "2.500")
        self.assertEqual(hz.kurs_fmt(0.05697), "0.05697")
        self.assertEqual(hz.kurs_fmt(0.00012), "0.00012")

    def test_Kleinstpreise_behalten_ihre_Ziffern(self):
        for wert in (3.1399080741348308e-06, 4.258775833450569e-05, 1.5e-08):
            text = hz.kurs_fmt(wert)
            self.assertNotEqual(text, "0.00000", "%s verliert alles" % wert)
            self.assertIn("e", text, "%s = %s: keine exponentielle Form" % (wert, text))

    def test_Einstieg_Stop_Ziel_sind_verschieden(self):
        # Der Fall aus moondev_sniper: alle drei Werte waren "0.00000" - die
        # Zeile las sich wie eine Position ohne Grenzen.
        p = {"einstieg": 3.1399080741348308e-06, "stop": 2.8887154282040443e-06,
             "ziel": 3.6422933659964036e-06}
        anzeige = {k: hz.kurs_fmt(v) for k, v in p.items()}
        self.assertEqual(len(set(anzeige.values())), 3, anzeige)

    def test_Kein_Wert_bleibt_Strich(self):
        self.assertEqual(hz.kurs_fmt(None), "-")
        self.assertEqual(hz.kurs_fmt("x"), "-")


class KurswegTest(unittest.TestCase):
    """Woher eine Spur ihre Kurse holt, ist eine Aussage ueber die Spur."""

    def test_Sniper_Token_geht_ueber_den_Feed_mit_Kette(self):
        z = {"positionen": [{"inst": "5XXvCxzrRSVEHpmXAFanyRHpkN99WViXnrbZLpMQpump",
                             "seite": "long", "einstieg": 3.1e-06, "nominal": 62.5}]}
        pos = hz.positionen_der_spur("moondev_sniper", z, {})[0]
        self.assertEqual(pos["quelle"], "feed")
        self.assertEqual(pos["kette"], "solana")
        self.assertEqual(pos["kurs_schluessel"],
                         "5XXvCxzrRSVEHpmXAFanyRHpkN99WViXnrbZLpMQpump")

    def test_Spiegel_Token_behaelt_seine_eigene_Kette(self):
        z = {"positionen": [{"token": "abc", "kette": "ethereum", "symbol": "X",
                             "usd": 10.0}]}
        pos = hz.positionen_der_spur("spiegel", z, {})[0]
        self.assertEqual(pos["kette"], "ethereum")
        self.assertEqual(pos["kurs_schluessel"], "abc")

    def test_Robinhood_Radar_gibt_Keinen_OKX_Weg_vor(self):
        """Ein Instrument ohne Haus-Kursweg heisst "keine", nicht "okx"."""
        z = {"positionen": [{"inst": "0x48f413c32a7b5b3c5008866846943a75c0188425",
                             "seite": "long", "einstieg": 4.2e-05, "nominal": 20.0}]}
        pos = hz.positionen_der_spur("robinhood_radar", z, {})[0]
        self.assertEqual(pos["quelle"], "keine")
        self.assertIsNone(pos["kurs_schluessel"],
                          "ein leerer Kursweg ist die Aussage - nicht eine Adresse")

    def test_Kontraktspur_behaelt_den_Paar_Namen(self):
        z = {"positionen": [{"inst": "BTC-USDT-SWAP", "einstieg": 80000.0,
                             "nominal": 100.0}]}
        pos = hz.positionen_der_spur("xperp", z, {})[0]
        self.assertEqual(pos["quelle"], "okx")
        self.assertEqual(pos["kurs_schluessel"], "BTC-USDT-SWAP")


class LogSchwanzTest(unittest.TestCase):
    """Das Protokoll wird am Ende gelesen, nicht ganz - und fehlt, ist es leer."""

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.addCleanup(self.ordner.cleanup)
        self.pfad = os.path.join(self.ordner.name, "dauerlauf.log")

    def _schreibe(self, zeilen):
        with open(self.pfad, "wb") as f:
            f.write(("\r\n".join(zeilen)).encode("utf-8"))

    def test_letzte_Zeilen_in_Reihenfolge(self):
        self._schreibe(["%04d ok" % i for i in range(200)])
        self.assertEqual(hz.log_ende(self.pfad, 3), ["0197 ok", "0198 ok", "0199 ok"])

    def test_Fehlende_Datei_ist_leer_nicht_ein_Fehler(self):
        self.assertEqual(hz.log_ende(os.path.join(self.ordner.name, "weg.log")), [])

    def test_an_geschnittene_Erste_Zeile_Faellt_weg(self):
        # Der Schwanz beginnt mitten in einer Zeile; dieser Bruchstueck ist
        # kein Inhalt, sondern ein Schnitt.
        self._schreibe(["x" * 200 + " ZEILE", "y" * 200 + " ZEILE",
                        "kurz ZEILE", "kurz2 ZEILE"])
        teile = hz.log_ende(self.pfad, zeilen=4, grenze=120)
        self.assertTrue(all(t.endswith(" ZEILE") for t in teile), teile)
        self.assertNotIn("ZEILE", [t for t in teile if t == " ZEILE"])
        self.assertEqual(teile[-1], "kurz2 ZEILE")

    def test_dauerlauf_stand_findet_den_letzten_Zeitstempel(self):
        # Der Zeitstempel im Log hat keine Zone; gemessen wird gegen JETZT,
        # sonst vergleicht die Zentrale Ortszeit mit einer UTC-Vorgabe.
        self._schreibe(["01.10. 09:00:00  x (papier) ok",
                        "01.10. 09:15:00  y (papier) ok",
                        "keine Zeitmarke"])
        text, alt = hz.dauerlauf_stand(self.pfad, datetime.now(UTC))
        self.assertEqual(text, "01.10. 09:15:00")
        self.assertIsNotNone(alt)

    def test_dauerlauf_stand_ohne_Zeitstempel_ist_leer(self):
        self._schreibe(["nur text", "und mehr text"])
        self.assertEqual(hz.dauerlauf_stand(self.pfad,
                                            datetime(2026, 10, 1, 9, 30, tzinfo=UTC)),
                         (None, None))


class KonsoleFarbeTest(unittest.TestCase):
    """Nur ein echtes Fehlermerkmal wird rot; Betriebsmeldungen nicht."""

    FALSCHE_ALARME = [
        "01.10. 11:56:06  Auto-Freigabe scanner (720 min)",
        "01.10. 13:22:19  Dauerlauf startet, Takt 15 min",
        "01.10. 13:28:53  Tagesbericht",
    ]

    def test_Betriebsmeldung_ist_nicht_rot(self):
        for zeile in self.FALSCHE_ALARME:
            self.assertNotEqual(hz.log_marke(zeile), "schlecht",
                                "%r war rot, ohne dass etwas fehlschlug" % zeile)

    def test_Fehlermerkmale_werden_rot(self):
        for zeile in ("xperp FEHLER: ConnectionReset", "Traceback (most recent call last):",
                      "scanner TIMEOUT (exceeded 700s limit)", "kraken nicht erreichbar",
                      "moondev_sniper abgestuerzt", "OKX-Transportfehler 1/6"):
            self.assertEqual(hz.log_marke(zeile), "schlecht", zeile)

    def test_Erfolg_bleibt_matt(self):
        self.assertEqual(hz.log_marke("01.10. 18:58:30  klassik_ema (papier) ok"),
                         "matt")

    def test_neutrale_Zeile_ohne_Marke(self):
        self.assertEqual(hz.log_marke("Dauerlauf startet, Takt 15 min"), "")


class TaktTest(unittest.TestCase):
    """Ein Takt, der wirft, darf nicht der letzte gewesen sein."""

    def setUp(self):
        try:
            self.root = hz.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        self.root.withdraw()
        for methode in ("_starte_kurs_worker", "_starte_freqtrade_worker",
                        "_zeige_omnitrade"):
            patcher = mock.patch.object(hz.Handelszentrale, methode)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.root.destroy)

    def _app_mit_geplanter_Teilnahme(self):
        with mock.patch.object(hz.Handelszentrale, "refresh"):
            app = hz.Handelszentrale(self.root)
        return app

    def test_Kurs_Sperre_faellt_erst_mit_der_Antwort(self):
        app = self._app_mit_geplanter_Teilnahme()
        app._kurs_laeuft = True
        app._planer()                      # kein Kursstueck im Korb
        self.assertTrue(app._kurs_laeuft,
                        "die Sperre fiel ohne Antwort - damit stapeln sich die "
                        "Kurs-Threads, genau was der Worker verbieten will")
        app.q_kurse.put({"okx": 1})
        app._planer()
        self.assertFalse(app._kurs_laeuft)
        self.assertEqual(app.kurse.get("okx"), 1)

    def test_refresh_Werfen_stoppt_den_Takt_nicht(self):
        app = self._app_mit_geplanter_Teilnahme()
        plane = []
        with mock.patch.object(app.root, "after",
                               side_effect=lambda *a: plane.append(a)):
            with mock.patch.object(hz.Handelszentrale, "refresh",
                                   side_effect=RuntimeError("Lesefehler")):
                app._planer()
        # Der Neustart des Timers steht im finally - nicht, weil der Fall
        # selten waere, sondern weil ein Fenster, das still aufhoert sich
        # zu erneuern, von einem abgeschalteten nicht zu unterscheiden ist.
        self.assertTrue(plane, "nach einem Lesefehler wurde der naechste Takt nicht geplant")

    def test_FreqTrade_Sperre_faellt_mit_dem_Stueck(self):
        app = self._app_mit_geplanter_Teilnahme()
        app._ft_laeuft = True
        app.q_freqtrade.put(([], {"erreichbar": False, "fehler": "x"}, [], {}, {}))
        with mock.patch.object(hz.Handelszentrale, "_zeige_freqtrade"):
            app._planer()
        self.assertFalse(app._ft_laeuft)


if __name__ == "__main__":
    unittest.main()
