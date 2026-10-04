"""Tests fuer die Risikostufen (Agenten/Handel/risikostufe.py).

WARUM DIESE TESTS
-----------------
Die Stufen skalieren Geldbetraege in einer laufenden Handelssimulation. Zwei
Fehler waeren hier teuer:
1. Ein Feld skalieren, das gar kein Einsatz ist (Marktkapazitaet, Messwert,
   Kontoschwelle) - dann handelt die Spur aus einem falschen Grund.
2. Die Ratsche (drawdown_halbierung_usd) oder den Kill-Schalter stehen lassen -
   dann sperrt die doppelte Position sich selbst und die Stufe liefert keine
   Daten mehr.

Der wichtigste Test ist deshalb der GEGEN DIE ECHTEN WACHEN: er laeuft ueber
jede vorhandene wachen.json und prueft beide Richtungen.
"""

import glob
import json
import os
import sys
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.insert(0, HANDEL)

import risikostufe  # noqa: E402


class StufenTest(unittest.TestCase):

    def setUp(self):
        self.alt = os.environ.get("HANDEL_RISIKO")
        os.environ.pop("HANDEL_RISIKO", None)

    def tearDown(self):
        if self.alt is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = self.alt

    def test_ohne_variable_ist_basis(self):
        self.assertEqual(risikostufe.stufe(), "niedrig")
        self.assertEqual(risikostufe.faktor(), 1.0)
        self.assertTrue(risikostufe.ist_basis())
        self.assertEqual(risikostufe.suffix(), "")

    def test_tippfehler_bleibt_basis(self):
        # "mitel" darf nicht als 4x durchgehen.
        os.environ["HANDEL_RISIKO"] = "mitel"
        self.assertEqual(risikostufe.stufe(), "niedrig")
        self.assertEqual(risikostufe.faktor(), 1.0)

    def test_faktoren(self):
        for stufe, faktor in (("niedrig", 1.0), ("mittel", 2.0), ("hoch", 4.0)):
            os.environ["HANDEL_RISIKO"] = stufe
            self.assertEqual(risikostufe.faktor(), faktor)

    def test_basis_aendert_nichts(self):
        w = {"risiko_je_position_usd": 6.0, "marketcap_band_usd": [50000, 1000000]}
        self.assertEqual(risikostufe.skaliere(w), w)

    def test_mittel_verdoppelt_das_risiko(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        w = {"risiko_je_position_usd": 6.0, "max_pro_trade_usd": 120,
             "drawdown_halbierung_usd": 36.0, "kill_switch_gesamt_usd": 200}
        aus = risikostufe.skaliere(w)
        self.assertEqual(aus["risiko_je_position_usd"], 12.0)
        self.assertEqual(aus["max_pro_trade_usd"], 240)
        # Die Ratsche MUSS mit: sonst sperrt die doppelte Position sich selbst.
        self.assertEqual(aus["drawdown_halbierung_usd"], 72.0)
        self.assertEqual(aus["kill_switch_gesamt_usd"], 400)
        # Vorlage unveraendert - sonst waere die Basis nach einem Aufruf kaputt.
        self.assertEqual(w["risiko_je_position_usd"], 6.0)

    def test_marktdaten_bleiben(self):
        os.environ["HANDEL_RISIKO"] = "hoch"
        w = {"marketcap_band_usd": [50000, 1000000],
             "groesster_ruecklauf_papierlauf_usd": 3.21,
             "mindest_guthaben_eur": 10.0,
             "umsatz_bezug_usd": 10000,
             "punkt_wert_usd": 0.01,
             "risiko_je_position_usd": 6.0}
        aus = risikostufe.skaliere(w)
        self.assertEqual(aus["marketcap_band_usd"], [50000, 1000000])
        self.assertEqual(aus["groesster_ruecklauf_papierlauf_usd"], 3.21)
        self.assertEqual(aus["mindest_guthaben_eur"], 10.0)
        self.assertEqual(aus["umsatz_bezug_usd"], 10000)
        self.assertEqual(aus["punkt_wert_usd"], 0.01)
        self.assertEqual(aus["risiko_je_position_usd"], 24.0)

    def test_dokumentierte_vorwerte_bleiben(self):
        # Felder mit fuehrendem Unterstrich sind der dokumentierte Vorwert.
        os.environ["HANDEL_RISIKO"] = "hoch"
        w = {"_risiko_je_position_usd": 6.0, "_max_pro_trade_usd": 120}
        self.assertEqual(risikostufe.skaliere(w), w)

    def test_texte_und_listen_bleiben(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        w = {"handel_erlaubt": False, "modus": "papier", "paare": ["BTC/USD"],
             "risiko_je_position_usd": 6.0}
        aus = risikostufe.skaliere(w)
        self.assertIs(aus["handel_erlaubt"], False)
        self.assertEqual(aus["modus"], "papier")
        self.assertEqual(aus["paare"], ["BTC/USD"])

    def test_dateiname_bekommt_suffix(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        self.assertTrue(risikostufe.datei("C:/x/zustand.json").endswith("zustand.mittel.json"))
        self.assertTrue(risikostufe.datei("C:/x/handelsjournal.csv").endswith("handelsjournal.mittel.csv"))
        os.environ["HANDEL_RISIKO"] = "niedrig"
        self.assertTrue(risikostufe.datei("C:/x/zustand.json").endswith("zustand.json"))
        self.assertNotIn(".niedrig", risikostufe.datei("C:/x/zustand.json"))

    def test_never_liste_gewinnt(self):
        # Beide Listen zusammen: NIE gewinnt. Doppelte Eintraege sind also
        # harmlos, statt still zu skalieren.
        for feld in risikostufe.NIE_SKALIEREN:
            self.assertNotIn(feld, risikostufe.SKALIEREN, feld)


class EchteWachenTest(unittest.TestCase):
    """Der eigentliche Nachweis: gegen jede vorhandene wachen.json."""

    def setUp(self):
        self.alt = os.environ.get("HANDEL_RISIKO")

    def tearDown(self):
        if self.alt is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = self.alt

    def _wachen(self):
        for pfad in sorted(glob.glob(os.path.join(HANDEL, "*", "wachen.json"))):
            try:
                with open(pfad, "r", encoding="utf-8") as f:
                    yield pfad, json.load(f)
            except (OSError, ValueError) as fehler:
                raise AssertionError("wachen.json nicht lesbar: %s (%s)" % (pfad, fehler))

    def test_mindestens_zehn_wachen_vorhanden(self):
        self.assertGreaterEqual(len(list(self._wachen())), 10)

    def test_verdoppelt_genau_das_risiko(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        getroffen = 0
        for pfad, w in self._wachen():
            aus = risikostufe.skaliere(w)
            for feld in ("risiko_je_position_usd", "risiko_je_position_eur",
                         "risiko_pro_trade_usd", "risiko_je_anlauf_usd"):
                if isinstance(w.get(feld), (int, float)):
                    getroffen += 1
                    self.assertAlmostEqual(aus[feld], w[feld] * 2, places=4,
                                           msg="%s: %s" % (pfad, feld))
        self.assertGreater(getroffen, 0, "kein Risikofeld in den Wachen gefunden?")

    def test_marktkapazitaet_bleibt_ueberall(self):
        os.environ["HANDEL_RISIKO"] = "hoch"
        for pfad, w in self._wachen():
            aus = risikostufe.skaliere(w)
            if "marketcap_band_usd" in w:
                self.assertEqual(aus["marketcap_band_usd"], w["marketcap_band_usd"], pfad)

    def test_ratsche_und_kill_wachsen_mit(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        geprueft = 0
        for pfad, w in self._wachen():
            aus = risikostufe.skaliere(w)
            for feld in ("drawdown_halbierung_usd", "kill_switch_gesamt_usd"):
                if isinstance(w.get(feld), (int, float)):
                    geprueft += 1
                    self.assertAlmostEqual(aus[feld], w[feld] * 2, places=4, msg=pfad)
        self.assertGreater(geprueft, 0)

    def test_struktur_bleibt_gleich(self):
        # Kein Feld darf verschwinden oder dazukommen - sonst liest eine Spur
        # ploetzlich ins Leere.
        os.environ["HANDEL_RISIKO"] = "hoch"
        for pfad, w in self._wachen():
            self.assertEqual(set(risikostufe.skaliere(w).keys()), set(w.keys()), pfad)


class DateiTypTest(unittest.TestCase):
    """datei()/datei_fuer(): Typ bleibt, Basis bleibt, Stufe wirkt."""

    def setUp(self):
        self.alt = os.environ.get("HANDEL_RISIKO")
        os.environ.pop("HANDEL_RISIKO", None)

    def tearDown(self):
        if self.alt is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = self.alt

    def test_path_bleibt_path(self):
        # scanner/handeln.py ruft .read_text() auf dem Ergebnis auf - ein
        # zurueckgegebener str waere dort ein Attributfehler.
        from pathlib import Path
        os.environ["HANDEL_RISIKO"] = "mittel"
        aus = risikostufe.datei(Path("C:/x/zustand.json"))
        self.assertIsInstance(aus, Path)
        self.assertEqual(aus.name, "zustand.mittel.json")

    def test_str_bleibt_str(self):
        os.environ["HANDEL_RISIKO"] = "hoch"
        aus = risikostufe.datei("C:/x/handelsjournal.csv")
        self.assertIsInstance(aus, str)
        self.assertTrue(aus.endswith("handelsjournal.hoch.csv"))

    def test_datei_fuer_kennt_jede_stufe(self):
        # Werkzeuge (spiegelstand, auswertung_alle) pruefen eine FREMDE Stufe,
        # ohne die Umgebung zu verbiegen.
        self.assertTrue(risikostufe.datei_fuer("zustand.json", "mittel")
                        .endswith("zustand.mittel.json"))
        self.assertEqual(risikostufe.datei_fuer("zustand.json", "niedrig"),
                         "zustand.json")
        self.assertEqual(risikostufe.datei_fuer("zustand.json", "tippfehler"),
                         "zustand.json")

    def test_live_nur_in_der_basis(self):
        # Eine Stufe ist ein Messwerkzeug: nie echtes Geld.
        self.assertTrue(risikostufe.live_erlaubt())
        for stufe in ("mittel", "hoch"):
            os.environ["HANDEL_RISIKO"] = stufe
            self.assertFalse(risikostufe.live_erlaubt(), stufe)


# Welche Datei je Spur die Dateinamen traegt, und welche Funktion die Wachen
# liefert. Beides wird am Modul der Spur geprueft, nicht nachgebaut.
SPUR_DATEIEN = {
    "xperp": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "scanner": ("handeln.py", ("ZUSTAND", "JOURNAL", "ABLEHNUNGEN")),
    "swap": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "kraken": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "kopier": ("kopier.py", ("ZUSTAND", "JOURNAL", "ABLEHNUNGEN")),
    "orbk": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "omniquant": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "nautilus": ("handeln.py", ("ZUSTAND", "JOURNAL", "KOPIER_JOURNAL",
                                "KOPIER_ZUSTAND")),
    "gitter": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "squeeze": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "supertrend": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "wavetrend": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "macd_mtf": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "mosaic": ("handeln.py", ("ZUSTAND", "JOURNAL")),
    "moondev_funding": ("handeln.py", ("ZUSTAND", "JOURNAL")),
}  # die Kern-Spuren (listingarb/topmovers/marktlage/iv_wand) fuehren ihre
# Dateinamen in spur_buch.pfade() - dafuer steht BuchSpurenTest unten.  # die drei weiteren Bot-Spuren nutzen den gemeinsamen Kern (spur_buch)
# und fuehren ihre Dateinamen dort - separat geprueft in BuchSpurenTest.

SPUR_WACHEN = {
    "xperp": ("bot.py", "wachen"),
    "scanner": ("scan.py", "wachen"),
    "swap": ("handeln.py", "wachen"),
    "kraken": ("scan.py", "wachen"),
    "kopier": ("kopier.py", "lade_wachen"),
    "orbk": ("handeln.py", "_wachen"),
    "omniquant": ("handeln.py", "lade_wachen"),
    "nautilus": ("handeln.py", "lade_wachen"),
    "gitter": ("handeln.py", "lade_wachen"),
    "squeeze": ("handeln.py", "lade_wachen"),
    "supertrend": ("handeln.py", "lade_wachen"),
    "wavetrend": ("handeln.py", "lade_wachen"),
    "macd_mtf": ("handeln.py", "lade_wachen"),
    "mosaic": ("handeln.py", "lade_wachen"),
    "moondev_funding": ("handeln.py", "lade_wachen"),
}  # iv_wand nutzt den gemeinsamen Kern (spur_buch), geprueft in BuchSpurenTest

# Spuren, die unter DIESEM Interpreter nicht ladbar sind. nautilus braucht
# sein eigenes venv (nautilus_trader). Eine Spur hier einzutragen heisst:
# "nicht geprueft" - das muss sichtbar bleiben und darf nicht still passieren.
AUSNAHMEN = {"nautilus": "braucht nautilus_trader (eigenes venv)"}

# spiegel wird NICHT gesuffixt: er laeuft nur in der Basis (Vorgabe Max).
NUR_BASIS = ("spiegel",)


def _lade(spur, datei):
    """Modul einer Spur laden - wie der Betrieb: eigener Ordner als sys.path[0]."""
    from importlib.util import module_from_spec, spec_from_file_location
    ordner = os.path.join(HANDEL, spur)
    spec = spec_from_file_location(
        "risiko_%s_%s" % (spur, datei.replace(".", "_")),
        os.path.join(ordner, datei))
    modul = module_from_spec(spec)
    sys.path.insert(0, ordner)
    try:
        spec.loader.exec_module(modul)
    finally:
        if sys.path and sys.path[0] == ordner:
            sys.path.pop(0)
    return modul


class VerdrahtungTest(unittest.TestCase):
    """DIE Spur traegt die Stufe - nicht eine Formel im Test.

    Ein Test, der die Skalierung hier nachbaut, prueft die Formel und nicht
    die Spur. Deshalb wird jede Spurendatei geladen und gefragt: heissen
    deine Dateien in dieser Stufe anders, und liefert deine Wachen-Funktion
    die groesseren Betraege?
    """

    def setUp(self):
        self.alt = os.environ.get("HANDEL_RISIKO")
        os.environ.pop("HANDEL_RISIKO", None)

    def tearDown(self):
        if self.alt is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = self.alt

    def test_basis_hat_ueberall_die_alten_namen(self):
        nicht_geprueft = []
        for spur, (datei, namen) in SPUR_DATEIEN.items():
            try:
                m = _lade(spur, datei)
            except ImportError as e:
                nicht_geprueft.append((spur, e))
                continue
            for name in namen:
                wert = str(getattr(m, name))
                self.assertNotIn(".mittel", wert, "%s.%s" % (spur, name))
                self.assertNotIn(".hoch", wert, "%s.%s" % (spur, name))
                self.assertNotIn(".niedrig", wert, "%s.%s" % (spur, name))
        self._erwartete_ausnahmen(nicht_geprueft)

    def test_stufe_trennt_die_dateien(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        nicht_geprueft = []
        for spur, (datei, namen) in SPUR_DATEIEN.items():
            try:
                m = _lade(spur, datei)
            except ImportError as e:
                nicht_geprueft.append((spur, e))
                continue
            for name in namen:
                wert = str(getattr(m, name))
                self.assertTrue(wert.endswith(".mittel.json")
                                or wert.endswith(".mittel.csv"),
                                "%s.%s = %s" % (spur, name, wert))
        self._erwartete_ausnahmen(nicht_geprueft)

    def test_spiegel_bleibt_bei_den_basisnamen(self):
        # Gegenprobe: der Spiegel haelt sich absichtlich heraus. Waere er hier
        # gesuffixt, laege sein Buch doppelt und der Basislauf bekaeme einen
        # zweiten Schreiber auf dieselbe Datei.
        os.environ["HANDEL_RISIKO"] = "mittel"
        m = _lade("spiegel", "spiegel.py")
        self.assertTrue(m.ZUSTAND.endswith("zustand.json"), m.ZUSTAND)
        self.assertTrue(m.JOURNAL.endswith("handelsjournal.csv"), m.JOURNAL)
        self.assertFalse(m.risikostufe.ist_basis())

    def test_wachenfunktion_skaliert(self):
        nicht_geprueft = []
        for spur, (datei, fn) in SPUR_WACHEN.items():
            try:
                m = _lade(spur, datei)
            except ImportError as e:
                nicht_geprueft.append((spur, e))
                continue
            os.environ.pop("HANDEL_RISIKO", None)
            basis = getattr(m, fn)()
            os.environ["HANDEL_RISIKO"] = "mittel"
            mittel = getattr(m, fn)()
            gefunden = 0
            for feld, wert in basis.items():
                if feld in risikostufe.NIE_SKALIEREN:
                    self.assertEqual(mittel[feld], wert, "%s: %s" % (spur, feld))
                if feld in risikostufe.SKALIEREN and isinstance(wert, (int, float)) \
                        and not isinstance(wert, bool):
                    gefunden += 1
                    self.assertAlmostEqual(mittel[feld], wert * 2, places=4,
                                           msg="%s: %s" % (spur, feld))
            self.assertGreater(gefunden, 0,
                               "%s: keine skalierbaren Felder in den Wachen" % spur)
        self._erwartete_ausnahmen(nicht_geprueft)

    def _erwartete_ausnahmen(self, nicht_geprueft):
        """Nicht ladbare Spuren sind erlaubt - aber nur die bekannten."""
        ueberraschung = [s for s, _ in nicht_geprueft if s not in AUSNAHMEN]
        self.assertFalse(
            ueberraschung,
            "unerwartet nicht ladbar (Verdrahtung kaputt?): %s"
            % ", ".join("%s: %s" % (s, e) for s, e in nicht_geprueft
                        if s in ueberraschung))
        self.assertGreaterEqual(len(SPUR_DATEIEN) - len(nicht_geprueft), 14,
                                "zu wenige Spuren wirklich geprueft")


class BuchSpurenTest(unittest.TestCase):
    """Die Spuren am gemeinsamen Buch tragen die Risikostufe ebenfalls.

    Sie haben keine eigenen ZUSTAND/JOURNAL-Konstanten - ihre Dateinamen
    entstehen in `spur_buch.pfade(ordner)`. Genau das wird hier gefragt: der
    echte Weg, nicht eine nachgebaute Formel.
    """

    SPUREN = ("moondev_listingarb", "moondev_topmovers", "moondev_marktlage",
              "iv_wand", "moondev_whale", "moondev_liquidation",
              "moondev_sentiment", "moondev_sniper")

    def setUp(self):
        self.alt = os.environ.get("HANDEL_RISIKO")
        os.environ.pop("HANDEL_RISIKO", None)

    def tearDown(self):
        if self.alt is None:
            os.environ.pop("HANDEL_RISIKO", None)
        else:
            os.environ["HANDEL_RISIKO"] = self.alt

    def _buch(self):
        from importlib.util import module_from_spec, spec_from_file_location
        pfad = os.path.join(HANDEL, "spur_buch.py")
        spec = spec_from_file_location("spur_buch_test", pfad)
        modul = module_from_spec(spec)
        spec.loader.exec_module(modul)
        return modul

    def test_basis_hat_die_basisnamen(self):
        buch = self._buch()
        for spur in self.SPUREN:
            _, zustand, journal = buch.pfade(os.path.join(HANDEL, spur))
            self.assertTrue(zustand.endswith("zustand.json"), zustand)
            self.assertTrue(journal.endswith("handelsjournal.csv"), journal)

    def test_stufe_trennt_die_dateien(self):
        os.environ["HANDEL_RISIKO"] = "mittel"
        buch = self._buch()
        for spur in self.SPUREN:
            _, zustand, journal = buch.pfade(os.path.join(HANDEL, spur))
            self.assertTrue(zustand.endswith("zustand.mittel.json"), zustand)
            self.assertTrue(journal.endswith("handelsjournal.mittel.csv"), journal)


if __name__ == "__main__":
    unittest.main(verbosity=2)
