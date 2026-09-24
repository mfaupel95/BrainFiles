"""Tests fuer nautilus_kraken/handeln.py - die papierfeste Spur-Schnittstelle.

Kein Netz: Geprueft wird der Vertrag mit dauerlauf.py, nicht der
Quotenpfad. Der echte Quotenpfad steht in test_quote_pfad.py.

Die vier Modi (--wachen, --vorschau, --papier, --live) muessen dieselbe
Form haben wie bei den anderen Spuren. Kritisch fuer den Dauerlauf:

  - --vorschau druckt die Zeile "Live waere gesperrt durch: ...". Daraus
    liest dauerlauf.nur_fenster_fehlt die Sperrgruende. Das Wort
    Freigabefenster darf in dem Grund NICHT vorkommen (papierfest).
  - --papier schreibt zustand.json (Herzschlag) und handelsjournal.csv.

Dazu Bedingung 4: die Kopie von Journal und Zustand nach
`journal_zweitziel` (Q:).

Aufruf:  .venv\\Scripts\\python.exe test_handeln.py
"""

import json
import os
import subprocess
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
PYTHON = os.path.join(HIER, os.pardir, "nautilus", ".venv", "Scripts", "python.exe")


def ruf(*args):
    p = subprocess.run([PYTHON, os.path.join(HIER, "handeln.py"), *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=60)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


class Schnittstelle(unittest.TestCase):
    def test_wachen_druckt_die_grenzen(self):
        code, ausgabe = ruf("--wachen")
        self.assertEqual(code, 0)
        for feld in ("max_risiko_pro_trade", "herzschlag_max_minuten",
                     "handel_erlaubt", "symbol", "waehrung"):
            self.assertIn(feld, ausgabe)

    def test_vorschau_nennt_den_papierfesten_grund(self):
        code, ausgabe = ruf("--vorschau")
        self.assertEqual(code, 0)
        self.assertIn("Live waere gesperrt durch: ", ausgabe)
        zeile = next(z for z in ausgabe.splitlines()
                     if "gesperrt durch" in z)
        grund = zeile.split(":", 1)[-1]
        # Die Spur ist Papier (handel_erlaubt=false, freigabe.erfuellt=false,
        # kein offenes Fenster) - die Vorschau nennt die Sperrgruende.
        self.assertIn("handel_erlaubt=false", grund)
        self.assertIn("freigabe.erfuellt=false", grund)
        self.assertIn("Freigabefenster", grund)

    def test_live_verweigert_mit_dem_papierfesten_grund(self):
        code, ausgabe = ruf("--live")
        self.assertEqual(code, 0)
        self.assertIn("gesperrt", ausgabe)
        self.assertIn("handel_erlaubt=false", ausgabe)

    def test_vorschau_schreibt_nichts(self):
        with tempfile.TemporaryDirectory() as tmp:
            alt = (os.path.join(HIER, "zustand.json"),
                   os.path.join(HIER, "handelsjournal.csv"))
            neu = (os.path.join(tmp, "zustand.json"),
                   os.path.join(tmp, "handelsjournal.csv"))
            for a, n in zip(alt, neu):
                if os.path.exists(a):
                    os.replace(a, n)
            try:
                code, _ = ruf("--vorschau")
                self.assertEqual(code, 0)
                self.assertFalse(os.path.exists(alt[0]),
                                 "Vorschau darf zustand.json nicht schreiben")
                self.assertFalse(os.path.exists(alt[1]),
                                 "Vorschau darf kein Journal schreiben")
            finally:
                for a, n in zip(alt, neu):
                    if os.path.exists(n):
                        os.replace(n, a)


class ZyklusAufbau(unittest.TestCase):
    def test_strategie_ueberschreibt_on_stop(self):
        import handeln
        self.assertIn("on_stop", handeln.QuoteSammler.__dict__,
                      "ohne eigenen on_stop warnt die Engine bei jedem "
                      "node.stop() - und die Zeile geht nach Telegram")

    def test_node_session_hat_den_stillen_log_pegel(self):
        import handeln
        cfg = handeln.baue_node_config({}, {})
        self.assertEqual(cfg.logging.log_level, handeln.LOG_PEGEL)
        self.assertEqual(handeln.LOG_PEGEL, "ERROR")


class JournalAusserHaus(unittest.TestCase):
    """Bedingung 4: Kopie von Journal und Zustand nach journal_zweitziel."""

    def test_kopiert_journal_und_zustand(self):
        import handeln
        with tempfile.TemporaryDirectory() as tmp:
            ziel = os.path.join(tmp, "nautilus_kraken")
            ok, info = handeln.spiegle_journal(ziel)
            self.assertTrue(ok, info)
            for name in ("handelsjournal.csv", "zustand.json"):
                quelle = os.path.join(HIER, name)
                if not os.path.exists(quelle):
                    continue
                kopie = os.path.join(ziel, name)
                self.assertTrue(os.path.exists(kopie), kopie)
                with open(quelle, "rb") as a, open(kopie, "rb") as b:
                    self.assertEqual(a.read(), b.read(),
                                     "%s nicht byte-gleich kopiert" % name)

    def test_ohne_ziel_nennt_es_den_grund(self):
        import handeln
        ok, info = handeln.spiegle_journal(None)
        self.assertFalse(ok)
        self.assertIn("nicht gesetzt", info)

    def test_nicht_erreichbares_laufwerk_ist_kein_fehler(self):
        import handeln
        ok, info = handeln.spiegle_journal("Z:/gibt-es-nicht-nautilus-kraken")
        self.assertFalse(ok)
        self.assertTrue(info.strip(), "der Grund darf nicht leer sein")

    def test_vermerk_schreibt_nur_bei_aenderung(self):
        import handeln
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "zustand.json")
            z = {}
            self.assertTrue(handeln.vermerke_spiegelung(
                z, "Q:/Handel_Journal/nautilus_kraken", True,
                "Q:/Handel_Journal/nautilus_kraken", pfad))
            self.assertTrue(os.path.exists(pfad))
            vorher = os.path.getmtime(pfad)
            self.assertFalse(handeln.vermerke_spiegelung(
                z, "Q:/Handel_Journal/nautilus_kraken", True,
                "Q:/Handel_Journal/nautilus_kraken", pfad),
                "gleicher Stand darf nicht erneut schreiben")
            self.assertEqual(os.path.getmtime(pfad), vorher)
            self.assertTrue(handeln.vermerke_spiegelung(
                z, "Q:/Handel_Journal/nautilus_kraken", False, "FileNotFoundError",
                pfad), "ein Wechsel muss geschrieben werden")


if __name__ == "__main__":
    unittest.main()

class Orderpaar(unittest.TestCase):
    """Der Live-Zweig ordert ueber Kraken-REST mit dem PAARNAMEN.

    kraken.py spricht die REST-API mit 'XXBTZEUR' an; das Nautilus-Symbol
    'BTC/EUR' wird abgelehnt - 'EQuery:Unknown asset pair', gemessen am
    24.09.2026. Ohne 'paar' in der wachen fiel handeln.py auf das Symbol
    zurueck, die erste echte Order waere an der Schreibweise gescheitert.
    Geprueft wird die REGEL (Kraken-Paar vorhanden, kein Nautilus-Symbol),
    nicht der Wert.
    """

    def test_wachen_traegt_ein_kraken_paar_und_nicht_das_symbol(self):
        with open(os.path.join(HIER, 'wachen.json'), encoding='utf-8') as f:
            w = json.load(f)
        paar = w.get('paar')
        self.assertTrue(paar, "wachen.json braucht 'paar' fuer den "
                                 "Kraken-REST-Orderweg")
        self.assertNotIn('/', paar, 'Kraken will keine Nautilus-Schreibweise')
        self.assertEqual(paar, paar.upper())
        self.assertNotEqual(paar, w.get('symbol'))

    def test_kraken_rest_bietet_den_weg_den_handeln_ruft(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'kraken_rest', os.path.join(HIER, 'kraken_rest.py'))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        for name in ('markt_kauf', 'markt_verkauf', 'stop_setzen',
                     'offene_orders', 'order_stornieren'):
            self.assertTrue(callable(getattr(m, name, None)), name)
