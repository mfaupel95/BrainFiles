"""Tests der Handelszentrale (Handel/handelszentrale.py): lesen die
Bindungen das, was
die Spuren wirklich schreiben?

Kein Fenster, kein Netz. Geprueft werden die reinen Funktionen - die ganze
Deutung der GUI liegt in ihnen - und die Form gegen die ECHTEN
zustand.json/handelsjournal.csv aller Spuren.

Warum Form und nicht Werte: die Zustandsdateien aendern sich mit jedem
Zyklus. Ein Test, der eine Positionszahl behauptet, bricht beim naechsten
Einstieg. Geprueft wird, dass keine Position still verschwindet und dass jede
gelesene Zeile ein Instrument und eine Richtung traegt.

Lauf:
    scanner/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"
"""

import csv
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import handelszentrale as gui                                 # noqa: E402

UTC = timezone.utc
JETZT = datetime(2026, 9, 13, 18, 30, 0, tzinfo=UTC)


def _schreibe(pfad, inhalt):
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        f.write(inhalt)


class PositionsformTest(unittest.TestCase):
    """Die Zustandsformen der Spuren, eine nach der anderen.

    Jede Form ist die echte Schreibweise ihrer Spur (aus zustand.json
    abgelesen), keine erfundene:
      xperp/swap/omniquant  positionen[] + seite + nominal
      scanner               positionen[] ohne seite, Einsatz als usd
      spiegel               symbol/kette/token, preis_einstieg, stop_preis
      orbk                  EINE Position unter 'position' + richtung
      gitter                positionen[] je Gitterstufe (abgeleitet aus 'lose')
      nautilus              leer
    """

    def test_gitterstufe_mit_ziel_statt_stop(self):
        # Die Gitter-Spur schreibt je belegter Stufe eine Position; einen Stop
        # gibt es nicht (verkauft wird eine Stufe hoeher), dafuer ein Ziel.
        # Ohne Ziel-Leser stuende in der Anzeige ein Strich fuer den Verkauf.
        z = {"positionen": [{"inst": "BTC-USDT", "seite": "long", "stufe": 3,
                             "einstieg": 74321.5, "menge": 0.0134,
                             "nominal": 996.21, "ziel": 80681.0,
                             "eroeffnet": "2026-09-13"}]}
        p = gui.positionen_aus(z)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["seite"], "long")
        self.assertEqual(p[0]["schluessel"], "BTC-USDT")
        self.assertAlmostEqual(p[0]["wert_usd"], 996.21)
        self.assertAlmostEqual(p[0]["ziel"], 80681.0)
        self.assertIsNone(p[0]["stop"])

    def test_okx_kontraktspur(self):
        z = {"positionen": [{"inst": "FIL-USD_UM_XPERP-310808", "seite": "long",
                             "einstieg": 0.8279, "stop": 0.8031, "ziel": 0.8775,
                             "nominal": 249.94, "hebel": 5}]}
        p = gui.positionen_aus(z)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["instrument"], "FIL-USD_UM_XPERP-310808")
        self.assertEqual(p[0]["seite"], "long")
        self.assertAlmostEqual(p[0]["wert_usd"], 249.94)
        self.assertAlmostEqual(p[0]["stop"], 0.8031)

    def test_scanner_ohne_seite_und_mit_usd(self):
        # Die Scanner-Spur schreibt keine Seite (immer Kauf) und den Einsatz
        # als 'usd'. Ohne Vorgabe waere hier ueberall '-' gestanden.
        z = {"positionen": [{"inst": "LTC-USDC", "einstieg": 54.22, "usd": 100.0,
                             "stop": 51.07, "ziel": 60.5}]}
        p = gui.positionen_aus(z)[0]
        self.assertEqual(p["seite"], "long")
        self.assertAlmostEqual(p["wert_usd"], 100.0)

    def test_spiegel_token_mit_eigenen_feldnamen(self):
        z = {"positionen": [{"kette": "solana", "token": "FMqh9mqR6dr",
                             "symbol": "world", "einsatz_usd": 50,
                             "preis_einstieg": 0.000949,
                             "stop_preis": 0.000712,
                             "ziel_preis": 0.001519}]}
        p = gui.positionen_aus(z)[0]
        # Der Schluessel ist das Token - zwei Kopien desselben Symbols sind
        # zwei Positionen, nicht eine.
        self.assertEqual(p["schluessel"], "FMqh9mqR6dr")
        self.assertEqual(p["instrument"], "world (solana)")
        self.assertAlmostEqual(p["einstieg"], 0.000949)
        self.assertAlmostEqual(p["stop"], 0.000712)
        self.assertAlmostEqual(p["ziel"], 0.001519)
        self.assertAlmostEqual(p["wert_usd"], 50.0)

    def test_orbk_einzelposition_mit_richtung(self):
        # ORB fuehrt hoechstens EINE Position unter 'position' und nennt die
        # Richtung 'richtung'. Beides wird mitgelesen - sonst zeigte die
        # zentrale Tabelle fuer diese Spur dauerhaft "0 Positionen".
        z = {"position": {"inst": "ETH_USD", "richtung": "short",
                          "einstieg": 2523.44, "stop": 2527.0, "ziel": 2519.5}}
        p = gui.positionen_aus(z)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["seite"], "short")
        self.assertEqual(p[0]["instrument"], "ETH_USD")

    def test_leerer_zustand_ist_keine_position(self):
        self.assertEqual(gui.positionen_aus({}), [])
        self.assertEqual(gui.positionen_aus({"positionen": []}), [])
        self.assertEqual(gui.positionen_aus({"position": None}), [])

    def test_jede_echte_spur_verliert_keine_position(self):
        """Formpruefung gegen die echten Dateien: zaehlt die GUI dasselbe?

        Die Zahl wird NICHT behauptet (sie aendert sich je Zyklus), sondern
        gegen den Rohzustand gestellt: wer eine Form nicht kennt, zeigt
        weniger Positionen als in der Datei stehen - und genau das faellt
        hier auf.
        """
        for spur in gui.SPUREN:
            ordner = os.path.join(HANDEL, gui.dauerlauf.SPUREN[spur]["ordner"])
            pfad = os.path.join(ordner, "zustand.json")
            if not os.path.exists(pfad):
                continue                      # Spur noch nie gelaufen
            with open(pfad, encoding="utf-8") as f:
                z = json.load(f)
            roh = z.get("positionen")
            if roh is None:
                roh = [z["position"]] if z.get("position") else []
            aus = gui.positionen_aus(z)
            self.assertEqual(len(aus), len(roh),
                             "%s: GUI zaehlt %d, Datei hat %d"
                             % (spur, len(aus), len(roh)))
            for p in aus:
                self.assertTrue(p["instrument"] and p["instrument"] != "?",
                                "%s: Position ohne Namen" % spur)
                self.assertIn(p["seite"], ("long", "short"),
                              "%s: unbekannte Richtung" % spur)


class RechnungTest(unittest.TestCase):
    """Die zwei Rechnungen, die jede Zeile zur Behauptung machen."""

    def test_abstand_short_ist_positiv_wenn_luft_da_ist(self):
        # Stop ueber dem Kurs bei short = normale Luft. Ohne Richtungsfaktor
        # waere das Produkt negativ und jede gesunde Position saehe aus wie
        # ein gerissener Stop (Befund an omniquant, 13.09.2026).
        self.assertGreater(gui.abstand_prozent("short", 100.0, 105.0), 0)
        self.assertGreater(gui.abstand_prozent("long", 100.0, 95.0), 0)

    def test_abstand_wird_negativ_wenn_der_stop_durchlaufen_ist(self):
        self.assertLess(gui.abstand_prozent("long", 90.0, 95.0), 0)
        self.assertLess(gui.abstand_prozent("short", 110.0, 105.0), 0)

    def test_abstand_auf_dem_stop_ist_null(self):
        self.assertAlmostEqual(gui.abstand_prozent("long", 95.0, 95.0), 0.0)

    def test_gv_richtungsbewusst(self):
        self.assertAlmostEqual(gui.gv_prozent("long", 110.0, 100.0), 10.0)
        self.assertAlmostEqual(gui.gv_prozent("short", 90.0, 100.0), 10.0)
        self.assertAlmostEqual(gui.gv_prozent("short", 110.0, 100.0), -10.0)

    def test_ohne_kurs_keine_zahl(self):
        # Kein Kurs heisst "nicht bekannt", nicht 0 % - sonst stuende in der
        # Tabelle eine Behauptung, die niemand gemessen hat.
        self.assertIsNone(gui.gv_prozent("long", None, 100.0))
        self.assertIsNone(gui.abstand_prozent("long", 100.0, None))


class ChartBereichTest(unittest.TestCase):

    def test_stop_und_ziel_fallen_nie_aus_dem_bild(self):
        kerzen = [[0, 100, 101, 99, 100, 1], [0, 100, 102, 98, 101, 1]]
        tief, hoch = gui.chart_bereich(kerzen, [90.0, 130.0, None])
        self.assertLessEqual(tief, 90.0)
        self.assertGreaterEqual(hoch, 130.0)

    def test_leere_kerzen_ergeben_leeren_bereich(self):
        self.assertEqual(gui.chart_bereich([], [None]), (0.0, 0.0))


class DauerlaufStandTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gui-test-")
        self.log = os.path.join(self.tmp, "dauerlauf.log")
        # Das Log traegt LOKALE Zeit ohne Jahr. Der Vergleich muss in
        # derselben Zone stattfinden - sonst liest sich ein frischer Eintrag
        # als Zukunft (negatives Alter).
        self.jetzt = datetime(2026, 9, 13, 18, 30, tzinfo=UTC).astimezone()

    def _zeile(self, wann):
        return wann.strftime("%d.%m. %H:%M:%S") + "  xperp (papier) ok\n"

    def test_letzte_zeile_und_alter(self):
        _schreibe(self.log,
                  self._zeile(self.jetzt - timedelta(minutes=5.1))
                  + self._zeile(self.jetzt - timedelta(minutes=65)))
        text, alt = gui.dauerlauf_stand(self.log, self.jetzt)
        self.assertEqual(text, (self.jetzt - timedelta(minutes=65)
                                ).strftime("%d.%m. %H:%M:%S"))
        self.assertAlmostEqual(alt, 65.0, places=1)

    def test_frischer_eintrag_ist_nicht_negativ(self):
        # Befund vor dem Fix: der letzte Logeintrag stand in Lokalzeit, das
        # Alter wurde gegen UTC gerechnet - "-120 min" bei laufendem Dienst.
        _schreibe(self.log, self._zeile(self.jetzt - timedelta(minutes=1)))
        _, alt = gui.dauerlauf_stand(self.log, self.jetzt)
        self.assertGreaterEqual(alt, 0)

    def test_zeitstempel_ohne_jahr_liest_nicht_als_zukunft(self):
        # Ein Altbestand vom Vorjahr darf nicht als "in der Zukunft"
        # erscheinen - sonst zeigt die Kopfzeile ein negatives Alter.
        _schreibe(self.log, "31.12. 23:59:00  xperp (papier) ok\n")
        jetzt = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC).astimezone()
        _, alt = gui.dauerlauf_stand(self.log, jetzt)
        self.assertIsNotNone(alt)
        self.assertGreater(alt, 0)

    def test_fehlende_datei_ist_kein_fehler(self):
        self.assertEqual(gui.dauerlauf_stand(os.path.join(self.tmp, "weg.log"),
                                             JETZT), (None, None))


class ZeitKurzTest(unittest.TestCase):
    """Die Journale schreiben zwei Zeitformen - beide muessen lesbar sein."""

    def test_iso_zeitstempel_ergibt_uhrzeit(self):
        self.assertEqual(gui.zeit_kurz("2026-09-13T10:57:58+00:00"), "10:57")

    def test_reines_datum_ergibt_tag_und_monat(self):
        # Die ORB-Spur schreibt nur "2026-09-13" - ein starres [11:16] haette
        # dort eine leere Spalte gelesen.
        self.assertEqual(gui.zeit_kurz("2026-09-13"), "13.09.")

    def test_unlesbares_bleibt_leer_aber_nicht_kaputt(self):
        self.assertEqual(gui.zeit_kurz(""), "--:--")
        self.assertEqual(gui.zeit_kurz(None), "--:--")


class ProzessTest(unittest.TestCase):

    def test_eigener_prozess_lebt(self):
        self.assertTrue(gui.prozess_lebt(os.getpid()))

    def test_unmoegliche_pid_lebt_nicht(self):
        self.assertFalse(gui.prozess_lebt(999999999))

    def test_ohne_pid_kein_urteil(self):
        self.assertIsNone(gui.prozess_lebt(None))


class JournalTest(unittest.TestCase):
    """Die Journalkoepfe der Spuren sind verschieden - jede Form muss lesbar
    sein. Gelesen werden die ECHTEN Kopfzeilen, die Zeilen sind Beispielwerte."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gui-journal-")
        self.pfad = os.path.join(self.tmp, "handelsjournal.csv")

    def test_omniquant_form(self):
        _schreibe(self.pfad,
                  "zeit,modus,aktion,inst,seite,preis,einsatz_usd,wert_usd,"
                  "stop,ziel,grund,score,cr,mfe_pct,mae_pct,haltetage\n"
                  "2026-09-13T10:57:58+00:00,papier,AUSSTIEG,SOL-USDC,long,"
                  "110.0,50,55,94.5,110.0,ziel,,,,,\n")
        e = gui.journal_ereignisse("omniquant", self.pfad)[0]
        self.assertEqual(e["aktion"], "AUSSTIEG")
        self.assertEqual(e["instrument"], "SOL-USDC")
        self.assertAlmostEqual(e["einsatz"], 50.0)
        self.assertAlmostEqual(gui.ereignis_gv(e), 10.0)

    def test_orbk_form_mit_ausgang_und_gv_usd(self):
        _schreibe(self.pfad,
                  "zeit,inst,richtung,einstieg,stop,ziel,ausgang,ausstieg,"
                  "gv_punkte,gv_usd\n"
                  "2026-09-13,ETH_USD,short,2523.44,2527.0,2519.495,ziel,"
                  "2519.495,3.945,3.95\n")
        e = gui.journal_ereignisse("orbk", self.pfad)[0]
        self.assertEqual(e["aktion"], "ZIEL")
        self.assertEqual(e["seite"], "short")
        self.assertAlmostEqual(e["preis"], 2519.495)

    def test_spiegel_form_mit_symbol_und_kette(self):
        _schreibe(self.pfad,
                  "zeit,modus,aktion,kette,wallet,token,symbol,preis,menge,"
                  "einsatz_usd,wert_usd,marktkap_usd,slippage_pct,gebuehr_pct,"
                  "grund\n"
                  "2026-09-13T12:00:00+00:00,papier,schliessen,solana,W,Tok,"
                  "world,0.0012,52152,50,60,900000,3,1,ziel\n")
        e = gui.journal_ereignisse("spiegel", self.pfad)[0]
        self.assertEqual(e["instrument"], "world (solana)")
        self.assertAlmostEqual(gui.ereignis_gv(e), 20.0)

    def test_zeile_nennt_instrument_und_seite(self):
        # Der Dauerlauf meldet zeilenweise nach Telegram - hier ist es die
        # Konsole. Eine Zeile ohne Instrument ist nicht zuzuordnen.
        _schreibe(self.pfad,
                  "zeit,modus,aktion,kette,wallet,token,symbol,preis,menge,"
                  "einsatz_usd,wert_usd,marktkap_usd,slippage_pct,gebuehr_pct,"
                  "grund\n"
                  "2026-09-13T12:00:00+00:00,papier,schliessen,solana,W,Tok,"
                  "world,0.0012,52152,50,60,900000,3,1,ziel\n")
        zeile = gui.ereignis_zeile(gui.journal_ereignisse("spiegel",
                                                          self.pfad)[0])
        self.assertIn("world", zeile)
        self.assertIn("SCHLIESSEN", zeile)

    def test_fehlende_datei_ist_leer(self):
        self.assertEqual(gui.journal_ereignisse("x", os.path.join(self.tmp,
                                                                  "weg.csv")),
                         [])


class KurswegTest(unittest.TestCase):
    """Jede Spur holt ihre Kurse dort, wo sie handelt."""

    def test_quelle_je_spur(self):
        self.assertEqual(gui.quelle_fuer("orbk"), "kraken")
        self.assertEqual(gui.quelle_fuer("spiegel"), "feed")
        for spur in ("xperp", "scanner", "swap", "omniquant", "nautilus"):
            self.assertEqual(gui.quelle_fuer(spur), "okx")

    def test_orbk_fragt_den_kraken_namen_aus_den_wachen(self):
        # Die ORB-Spur fuehrt als inst nur den Schluessel ETH_USD; den
        # Kraken-Paarnamen traegt der Instrumentenblock in wachen.json.
        z = {"position": {"inst": "ETH_USD", "richtung": "long",
                          "einstieg": 2500.0, "stop": 2490.0, "ziel": 2540.0}}
        w = {"instrumente": {"ETH_USD": {"kraken": "ETHUSD"}}}
        p = gui.positionen_der_spur("orbk", z, w)[0]
        self.assertEqual(p["kurs_schluessel"], "ETHUSD")
        self.assertEqual(p["quelle"], "kraken")

    def test_okx_spur_fragt_den_instid(self):
        z = {"positionen": [{"inst": "CHIP-USDT-SWAP", "seite": "long",
                             "einstieg": 1.0, "stop": 0.9, "ziel": 1.2}]}
        p = gui.positionen_der_spur("swap", z, {})[0]
        self.assertEqual(p["kurs_schluessel"], "CHIP-USDT-SWAP")
        self.assertEqual(p["quelle"], "okx")


class SpurtabelleTest(unittest.TestCase):

    def _spanne(self, zustand, wachen, jetzt=JETZT):
        f = gui.freigabefenster.Fenster("xperp", {})
        return gui.spur_stand("xperp", zustand, wachen, f, jetzt)

    def test_herzschlag_gegen_die_eigene_grenze(self):
        # Grenze aus wachen.json, Messwert aus letzter_lauf - nichts erfunden.
        z = {"letzter_lauf": "2026-09-13T18:00:00+00:00", "positionen": []}
        w = {"herzschlag_max_minuten": 30}
        stand = self._spanne(z, w)
        self.assertEqual(stand["herzschlag"], "ok")
        z["letzter_lauf"] = "2026-09-13T16:00:00+00:00"
        self.assertEqual(self._spanne(z, w)["herzschlag"], "ueberfaellig")

    def test_unlesbarer_stand_ist_unbekannt_nicht_ok(self):
        self.assertEqual(self._spanne({}, {})["herzschlag"], "unbekannt")

    def test_zeile_hat_so_viele_zellen_wie_spalten(self):
        """Nicht eine feste Zahl, sondern die EIGENSCHAFT (30.09.2026/05.10.).

        Der Test stand hier auf "7", als die Zentrale drei Bilanzspalten
        bekam (Auftrag Max "die PnL% etc als Auswahl"). Eine feste Zahl meldet
        jede Spaltenerweiterung als Fehler und jede Kuerzung als Erfolg - sie
        prueft nicht, ob die Anzeige stimmt, sondern nur, dass sie unveraendert
        ist. Bei einem Tuple zu kurz verliert ttk.Treeview die hinteren Spalten
        OHNE Fehlermeldung, das ist das, was hier auffallen muss.
        """
        zeile = gui.spur_zeile(self._spanne({}, {}))
        spalten = gui.spalten_der_spurtabelle()
        self.assertEqual(len(zeile), len(spalten))
        # und jede Spalte hat auch wirklich eine Ueberschrift
        self.assertEqual(len(set(spalten)), len(spalten), "Doppelte Spalte")
        self.assertTrue(all(s for s in spalten), "Leere Spaltenueberschrift")


class VerbotsnamenTest(unittest.TestCase):
    """Erfundene Feldnamen sind hier schon einmal durchgerutscht (omniquant:
    einsatz_pro_position, kumulierte_verluste, kill_switch). Die zentrale GUI
    liest ueber alle Spuren - ein falscher Name faellt hier noch weniger auf.
    """

    VERBOTEN = ("einsatz_pro_position", "kumulierte_verluste", "kill_switch",
                "gewinn_usd", "pnl_usd", "positionswert")

    def test_verbotene_feldnamen_kommen_nicht_vor(self):
        with open(gui.__file__, encoding="utf-8") as f:
            quelle = f.read()
        for name in self.VERBOTEN:
            self.assertNotIn(name, quelle,
                             "handelszentrale.py liest '%s' - dieses Feld schreibt keine "
                             "Spur" % name)


class NamensfalleTest(unittest.TestCase):
    """Kein zweites Modul mit dem Namen einer Spur-Datei am Handel-Kopf.

    Befund 13.09.2026: dieses Fenster hiess zuerst `gui.py` - genau wie
    `omniquant/gui.py`. Mit `Handel/` auf `sys.path` fing der Import das
    falsche Modul ab, und fuenf Omniquant-Tests brachen mit
    `module 'gui' has no attribute 'fuss_texte'`. Sie waren nicht kaputt - sie
    liefen gegen das falsche Fenster.
    """

    def test_kein_modulname_einer_spur_doppelt_am_handel_kopf(self):
        spur_module = set()
        for spur in gui.SPUREN:
            ordner = os.path.join(HANDEL, gui.dauerlauf.SPUREN[spur]["ordner"])
            if os.path.isdir(ordner):
                spur_module.update(n[:-3] for n in os.listdir(ordner)
                                   if n.endswith(".py"))
        eigene = {n[:-3] for n in os.listdir(HANDEL) if n.endswith(".py")}
        self.assertEqual(sorted(eigene.intersection(spur_module)), [],
                         "gleicher Modulname am Handel-Kopf und in einer Spur")


class FensterAufbauTest(unittest.TestCase):
    """Ein ECHTER Aufbau des Fensters - ohne Bildschirm uebersprungen.

    Ein tk-Mock im Importtest verdeckt genau die zwei Fehler, die erst beim
    echten Start auftreten: ein fehlendes `from tkinter import ttk` und ein
    `root` in einer Builder-Methode, die nur `self.root` kennt. Hier wird das
    Fenster deshalb wirklich gebaut (unsichtbar), einmal gezeichnet und
    wieder geschlossen.
    """

    def test_fenster_wird_gebaut_und_gefuellt(self):
        try:
            root = gui.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            app = gui.Handelszentrale(root)
            root.update()
            self.assertEqual(len(app.t_spuren.get_children()), len(gui.SPUREN))
            self.assertEqual(len(app.t_pos.get_children()),
                             len(app.positionen))
            self.assertIn("Handelszentrale", root.title())
            # Der Titel nennt den Modus: ein Fenster, das Zahlen zeigt und
            # die Leserichtung verschweigt, ist eine Falle.
            self.assertIn("nur lesend", root.title())
        finally:
            root.destroy()

    def test_nach_vorn_hebt_ein_verstecktes_fenster(self):
        # Ein von einem Skript gestartetes Fenster hat kein Vordergrundrecht
        # und steht hinter allem - sichtbar, aber unauffindbar. nach_vorn()
        # setzt den Topmost-Impuls; der Rueckfall nach 700 ms haengt an der
        # Ereignisschleife und wird hier nicht abgewartet.
        try:
            root = gui.tk.Tk()
        except Exception as e:                               # noqa: BLE001
            self.skipTest("kein Bildschirm: %s" % e)
        root.withdraw()
        try:
            gui.nach_vorn(root)
            root.update()
            self.assertTrue(bool(int(root.attributes("-topmost"))))
        finally:
            root.destroy()


class PrueflaufTest(unittest.TestCase):
    """Der Kopf-Aufruf '--pruefen' muss gegen die echten Dateien laufen."""

    def test_pruefen_listet_jede_spur(self):
        aus = gui.pruefe(JETZT)
        self.assertGreater(len(aus), len(gui.SPUREN))
        for spur in gui.SPUREN:
            self.assertTrue(any(zeile.strip().startswith(spur) for zeile in aus),
                            "%s fehlt in der Ausgabe" % spur)


class SchriftTest(unittest.TestCase):
    """Die Schrift-Option: eine Basis, alles relativ, kein hart kodierter Wert."""

    def test_basis_ohne_relativ(self):
        art, groesse = gui.schrift()
        self.assertEqual(art, "Consolas")
        self.assertEqual(groesse, gui.SCHRIFT_GROESSE)

    def test_relativ_verschiebt_groesse(self):
        self.assertEqual(gui.schrift(gui.TINY)[1],
                         gui.SCHRIFT_GROESSE + gui.TINY)
        self.assertEqual(gui.schrift(gui.TITEL)[1],
                         gui.SCHRIFT_GROESSE + gui.TITEL)

    def test_fett_ist_drittes_element(self):
        tupel = gui.schrift(0, fett=True)
        self.assertEqual(tupel[2], "bold")

    def test_auswahl_enthaelt_die_vorgabe(self):
        self.assertIn(str(gui.SCHRIFT_GROESSE), gui.SCHRIFT_AUSWAHL)

    def test_kein_hart_kodierter_consolas_ausser_der_art(self):
        # Ein hart kodierter Font an einer Stelle wuerde nicht mit der Option
        # mitwandern - und genau das ist der Fehler, den die Option behebt.
        with open(gui.__file__, encoding="utf-8") as f:
            quelle = f.read()
        for n in quelle.split("\n"):
            if '("Consolas"' in n and "SCHRIFT_ART" not in n:
                self.fail("harter Font: %s" % n.strip())


if __name__ == "__main__":
    unittest.main()
