"""Quotewaehrung der Kraken-Spur: Ableitung aus der API und Guthaben-Tor.

Ohne Netz, ohne Order: AssetPairs und der Kontostand sind Attrappen. Die
Waende, um die es geht:

  - Die Quote kommt JE PAAR aus der API (quote.py), nicht aus einer Liste.
  - Das Guthaben-Tor prueft in der WAEHRUNG DES PAARES, nicht in EUR.
  - Ein Buch fuehrt EINE Waehrung - sonst waere der Ruecklauf eine Summe aus
    EUR und USDC, und die Drawdown-Ratsche rechnete darauf.
  - Ein PAPIERLAUF haengt NICHT am Kontostand. Waere er es, wuerde ein
    Netzausfall oder ein fehlender Schluessel ihn stillstellen, und niemand
    saehe den Unterschied zu "kein Signal".
  - Dasselbe Instrument in zwei Waehrungen ist EIN Instrument (Basis).

Anlass (30.09.2026, Auftrag Max "kraken auch mit eurc/usdc handel"): Das
Kraken-Konto traegt Kapital in EUR, EURC und USDC, die Spur kannte nur EUR -
Kapital lag brach, und das Tor sperrte gegen einen EUR-Betrag, der nie
erreicht wurde.

Direkt ausfuehrbar (aus dem kraken-Ordner):  python tests/test_quote.py
"""

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HIER = Path(__file__).resolve().parent
SPUR = HIER.parent
sys.path.insert(0, str(SPUR))

import handeln as h                                            # noqa: E402
import quote                                                   # noqa: E402

assert h.__file__.startswith(str(SPUR)), h.__file__
assert quote.__file__.startswith(str(SPUR)), quote.__file__


# --- Modulwaechter ---------------------------------------------------------
# Diese Suiten schreiben ins Journal. Sie zeigen es auf einen Temp-Ordner -
# der Waechter belegt, dass keine Zeile in der ECHTEN Spur landet.

JOURNAL_ECHT = h.JOURNAL


def _journal_stand():
    return {p.name: p.stat().st_size for p in SPUR.glob("handelsjournal*")}


_STAND_VOR = _journal_stand()


def tearDownModule():
    nach = _journal_stand()
    assert nach == _STAND_VOR, \
        "Test hat in die ECHTE Spur geschrieben: %r -> %r" % (_STAND_VOR, nach)


# --- Attrappen -------------------------------------------------------------

PAARE = {
    "XXBTZEUR": {"quote": "ZEUR", "base": "XXBT", "wsname": "XBT/EUR"},
    "XBTEURC":  {"quote": "EURC", "base": "XBT",  "wsname": "XBT/EURC"},
    "XBTUSDC":  {"quote": "USDC", "base": "XBT",  "wsname": "XBT/USDC"},
    "SOLEUR":   {"quote": "ZEUR", "base": "SOL",  "wsname": "SOL/EUR"},
    "SOLUSDC":  {"quote": "USDC", "base": "SOL",  "wsname": "SOL/USDC"},
    "ETHEUR":   {"wsname": "ETH/EUR"},            # ohne quote-Feld -> wsname
    "EURCHF":   {"quote": "CHF", "base": "EUR",   "wsname": "EUR/CHF"},
}

# Der echte Stand vom 30.09.2026: jede Waehrung unter dem Tor von 60.
STEHENDE = {"ZEUR": 46.83, "USDC": 25.08, "EURC": 0.0, "XXBT": 0.001,
            "SOL": 0.5, "ZCHF": 3.0}

# Nur die Form: welche Felder liest der Lauf.
W = {"max_pro_trade_eur": 50, "max_gesamt_eur": 200, "max_offene_positionen": 4,
     "gebuehr_taker": 0.0, "abklingzeit_tage": 3, "mindest_score": 65,
     "max_volatilitaet_pa": 1.20, "mindest_chance_risiko": 2.0,
     "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
     "bericht_max_alter_tage": 3, "waehrung": "EUR",
     "mindest_guthaben_eur": 60,
     "mindest_guthaben_je_quote": {"EUR": 60, "USDC": 60, "EURC": 60},
     "quote_vorrang": ["EUR", "USDC", "EURC"],
     "watchlist": ["XXBTZEUR", "XBTEURC", "XBTUSDC", "SOLEUR", "SOLUSDC"]}


def _abruf():
    return PAARE


def _v(inst, waehrung, basis, eur=50.0):
    """Ein Vorschlag, wie vorschlaege() ihn baut - waehrung ist der ROHCODE."""
    return {"inst": inst, "waehrung": waehrung, "basis": basis, "score": 80.0,
            "einstieg": 100.0, "stop": 93.0, "stop_pct": 7.0, "ziel": 114.0,
            "eur": eur}


# --- Ableitung aus der API -------------------------------------------------

class QuoteAbleitung(unittest.TestCase):

    def test_quote_kommt_aus_dem_feld_quote(self):
        self.assertEqual(quote.quote_von_paar("XXBTZEUR", _abruf), "ZEUR")
        self.assertEqual(quote.quote_von_paar("XBTUSDC", _abruf), "USDC")
        self.assertEqual(quote.quote_von_paar("XBTEURC", _abruf), "EURC")

    def test_ohne_quote_feld_entscheidet_der_wsname(self):
        # ETHEUR traegt in der Attrappe kein quote-Feld - so sieht ein
        # unvollstaendiger API-Eintrag aus. Geraten wird trotzdem nicht.
        self.assertEqual(quote.quote_von_paar("ETHEUR", _abruf), "EUR")

    def test_unbekanntes_paar_ist_ein_fehler_kein_rueckfall(self):
        with self.assertRaises(quote.QuoteUnbekannt):
            quote.quote_von_paar("GIBTSNICHT", _abruf)
        with self.assertRaises(quote.QuoteUnbekannt):
            quote.quote_von_paar(None, _abruf)

    def test_basis_ist_ueber_die_waehrung_hinweg_dieselbe(self):
        for paar in ("XXBTZEUR", "XBTEURC", "XBTUSDC"):
            self.assertEqual(quote.basis_von_paar(paar, _abruf), "XBT")

    def test_lesbare_namen_treffen_fiat_und_stablecoins(self):
        self.assertEqual(quote.lesbar("ZEUR"), "EUR")
        self.assertEqual(quote.lesbar("ZUSD"), "USD")
        self.assertEqual(quote.lesbar("ZCHF"), "CHF")
        self.assertEqual(quote.lesbar("USDC"), "USDC")
        self.assertEqual(quote.lesbar("EURC"), "EURC")
        self.assertEqual(quote.lesbar("USDT"), "USDT")
        self.assertEqual(quote.lesbar(""), "")
        self.assertEqual(quote.lesbar(None), "")

    def test_guthaben_schluessel_findet_auch_das_fuehrende_z(self):
        # Gemessen: EURCHF traegt die Quote "CHF", der Kontostand heisst "ZCHF".
        self.assertEqual(quote.guthaben_asset("CHF", {"ZCHF": 3.0}), "ZCHF")
        self.assertEqual(quote.guthaben_asset("ZEUR", {"ZEUR": 1.0}), "ZEUR")
        self.assertEqual(quote.guthaben_asset("USDC", {"USDC": 1.0}), "USDC")
        self.assertIsNone(quote.guthaben_asset("EURC", {"ZEUR": 1.0}))
        self.assertIsNone(quote.guthaben_asset("", {"ZEUR": 1.0}))

    def test_frei_rechnet_und_bleibt_bei_muell_bei_null(self):
        self.assertEqual(quote.frei({"ZEUR": "12.5"}, "ZEUR"), 12.5)
        self.assertEqual(quote.frei({"ZEUR": 46.83}, "ZEUR"), 46.83)
        self.assertEqual(quote.frei({"ZEUR": "keine Zahl"}, "ZEUR"), 0.0)
        self.assertEqual(quote.frei({}, "ZEUR"), 0.0)
        self.assertEqual(quote.frei(None, "ZEUR"), 0.0)

    def test_quoten_der_watchlist_entdoppelt_und_haelt_die_reihenfolge(self):
        wl = ["XXBTZEUR", "XBTUSDC", "XBTEURC", "GIBTSNICHT", "SOLEUR"]
        self.assertEqual(quote.quoten_der_watchlist(wl, _abruf),
                         ["ZEUR", "USDC", "EURC"])

    def test_basen_der_watchlist_uebergeht_unbekannte_paare(self):
        aus = quote.basen_der_watchlist(["XXBTZEUR", "GIBTSNICHT"], _abruf)
        self.assertEqual(aus, {"XXBTZEUR": "XBT"})


# --- Guthaben-Tor in der Waehrung des Paares -------------------------------

class GuthabenLage(unittest.TestCase):

    def test_lage_je_quotewaehrung_aus_einem_abruf(self):
        with patch.object(h.quote, "_CACHE", {"paare": PAARE}), \
                patch.object(h.kraken, "kontostaende", return_value=STEHENDE):
            lage = h.guthaben_lage(W)
        self.assertEqual(lage["EUR"], (46.83, 60.0))
        self.assertEqual(lage["USDC"], (25.08, 60.0))
        self.assertEqual(lage["EURC"], (0.0, 60.0))
        # CHF steht in keiner Watchlist dieser Attrappe - also kein Eintrag.
        self.assertNotIn("CHF", lage)

    def test_ohne_karte_gilt_der_alte_eur_wert_fuer_jede_waehrung(self):
        w = dict(W)
        del w["mindest_guthaben_je_quote"]
        with patch.object(h.quote, "_CACHE", {"paare": PAARE}), \
                patch.object(h.kraken, "kontostaende", return_value=STEHENDE):
            lage = h.guthaben_lage(w)
        # Eine wachen.json von vor dem 30.09.2026 bleibt benutzbar - und das
        # Tor geht dabei NICHT still auf.
        self.assertEqual(lage["USDC"], (25.08, 60.0))

    def test_bevorzugte_waehrung_folgt_dem_vorrang_und_dem_geld(self):
        keine = {"EUR": (46.83, 60.0), "USDC": (25.08, 60.0), "EURC": (0.0, 60.0)}
        self.assertIsNone(h.bevorzugte_waehrung(W, keine))
        self.assertEqual(h.bevorzugte_waehrung(
            W, {"EUR": (100.0, 60.0), "USDC": (100.0, 60.0)}), "EUR")
        self.assertEqual(h.bevorzugte_waehrung(
            W, {"EUR": (10.0, 60.0), "USDC": (100.0, 60.0)}), "USDC")
        # Genau auf der Schwelle ist gedeckt, nicht darunter.
        self.assertEqual(h.bevorzugte_waehrung(W, {"EUR": (60.0, 60.0)}), "EUR")
        self.assertIsNone(h.bevorzugte_waehrung(W, {"EUR": (59.99, 60.0)}))

    def test_zielwaehrung_buch_schlaegt_vorrang(self):
        z = {"positionen": [{"paar": "XBTUSDC", "eur": 50.0, "waehrung": "USDC"}]}
        # Das Buch steht in USDC - auch wenn EUR vorne im Vorrang steht.
        self.assertEqual(h.ziel_waehrung(z, W, {"EUR": (500.0, 60.0)}, True),
                         "USDC")
        self.assertEqual(h.ziel_waehrung(z, W, {}, False), "USDC")

    def test_zielwaehrung_live_nimmt_die_gedeckte(self):
        z = {"positionen": []}
        self.assertEqual(h.ziel_waehrung(z, W, {"USDC": (100.0, 60.0)}, True),
                         "USDC")

    def test_zielwaehrung_papier_haengt_nicht_am_konto(self):
        # Ohne lesbares Guthaben entscheidet die Konfiguration, nicht das Netz.
        self.assertEqual(h.ziel_waehrung({"positionen": []}, W, {}, False), "EUR")


class EinstiegInEinerWaehrung(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.alt = h.JOURNAL
        h.JOURNAL = Path(self.tmp.name) / "handelsjournal.csv"

    def tearDown(self):
        h.JOURNAL = self.alt
        self.tmp.cleanup()

    def _lauf(self, vs, z, live=False, lage=None, w=None, live_naht=False):
        puffer = io.StringIO()
        with contextlib.ExitStack() as stapel:
            stapel.enter_context(
                patch.object(h, "menge_fuer", return_value=(0.5, None)))
            if live_naht:
                # Die Naehte des Live-Orderwegs: Beleg, Einloesung, Boerse.
                # Ohne sie bricht der Live-Zweig VOR dem Buchen ab - und der
                # Test pruefte dann nichts.
                stapel.enter_context(patch.object(
                    h, "_beleg_zur_order", return_value={"kennung": "B-1"}))
                stapel.enter_context(patch.object(
                    h.freigabebeleg, "pruefe", return_value=(True, "")))
                stapel.enter_context(patch.object(
                    h.freigabebeleg, "verbrauche", return_value=None))
                stapel.enter_context(patch.object(
                    h.kraken, "markt_kauf", return_value="TX1"))
                stapel.enter_context(patch.object(
                    h.kraken, "gefuellte_menge", return_value=0.5))
                stapel.enter_context(patch.object(
                    h.kraken, "stop_setzen", return_value="ST1"))
            stapel.enter_context(patch("sys.stdout", puffer))
            h.pruefe_einstiege(z, vs, w or W, live, 1.0, lage)
        return puffer.getvalue()

    def test_papier_kauft_auch_ohne_kontostand(self):
        """Der Kern der Regel: ein Papierlauf haengt NICHT am Konto.

        Waere er es, wuerde ein Netzausfall oder ein fehlender Schluessel ihn
        stillstellen - und in der Rangliste saehe das aus wie "kein Signal"."""
        z = {"positionen": [], "letzte_stops": {}}
        self._lauf([_v("XXBTZEUR", "ZEUR", "XBT")], z)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(z["positionen"][0]["waehrung"], "EUR")
        self.assertEqual(z["positionen"][0]["basis"], "XBT")

    def test_fremde_waehrung_wird_uebersprungen(self):
        z = {"positionen": [], "letzte_stops": {}}
        text = self._lauf([_v("XBTUSDC", "USDC", "XBT")], z)
        self.assertEqual(z["positionen"], [])
        self.assertIn("notiert in USDC", text)

    def test_live_nimmt_die_gedeckte_waehrung(self):
        z = {"positionen": [], "letzte_stops": {}}
        lage = {"EUR": (10.0, 60.0), "USDC": (100.0, 60.0), "EURC": (0.0, 60.0)}
        self._lauf([_v("XXBTZEUR", "ZEUR", "XBT"), _v("XBTUSDC", "USDC", "XBT")],
                   z, live=True, lage=lage, live_naht=True)
        self.assertEqual([p["paar"] for p in z["positionen"]], ["XBTUSDC"])
        self.assertEqual(z["positionen"][0]["waehrung"], "USDC")
        self.assertEqual(z["positionen"][0]["kauf_txid"], "TX1")
        self.assertEqual(z["positionen"][0]["stop_txid"], "ST1")

    def test_zu_wenig_guthaben_in_der_buchwaehrung(self):
        z = {"positionen": [], "letzte_stops": {}}
        lage = {"EUR": (10.0, 60.0), "USDC": (0.0, 60.0), "EURC": (0.0, 60.0)}
        text = self._lauf([_v("XXBTZEUR", "ZEUR", "XBT")], z, live=True,
                          lage=lage, live_naht=True)
        self.assertEqual(z["positionen"], [])
        self.assertIn("10.00 EUR frei, 50.00 noetig", text)

    def test_ohne_gelesenes_guthaben_bindet_das_geld_nicht(self):
        """Gegenprobe zum vorigen Test: lage leer = Papier = keine Geldsperre."""
        z = {"positionen": [], "letzte_stops": {}}
        self._lauf([_v("XXBTZEUR", "ZEUR", "XBT")], z, live=False, lage={})
        self.assertEqual(len(z["positionen"]), 1)

    def test_dasselbe_instrument_in_zwei_waehrungen_ist_ein_instrument(self):
        # Waehrung unbekannt (Handaufruf, Altbestand) -> der Waehrungsfilter
        # greift nicht, die Basis-Regel muss halten.
        z = {"positionen": [{"paar": "SOLEUR", "eur": 50.0, "waehrung": "EUR"}],
             "letzte_stops": {}}
        self._lauf([_v("SOLUSDC", "", "SOL")], z)
        self.assertEqual([p["paar"] for p in z["positionen"]], ["SOLEUR"])

    def test_journalzeile_nennt_die_waehrung(self):
        z = {"positionen": [], "letzte_stops": {}}
        lage = {"EUR": (0.0, 60.0), "USDC": (100.0, 60.0), "EURC": (0.0, 60.0)}
        self._lauf([_v("XBTUSDC", "USDC", "XBT")], z, live=True, lage=lage,
                   live_naht=True)
        zeilen = [x for x in h.JOURNAL.read_text("utf-8").splitlines()
                  if ",kauf," in x]
        self.assertEqual(len(zeilen), 1)
        self.assertIn("score 80.0 | USDC", zeilen[0])

    def test_abklingzeit_gilt_ueber_die_waehrung_hinweg(self):
        # Ein Stop in SOLEUR und ein Kauf in SOLUSDC sind dasselbe Instrument.
        self.assertTrue(h.in_abklingzeit("SOLUSDC", {"letzte_stops": {
            "SOLEUR": h._heute()}}, W))
        self.assertTrue(h.in_abklingzeit("SOLEUR", {"letzte_stops": {
            "SOLUSDC": h._heute()}}, W))
        self.assertFalse(h.in_abklingzeit("XXBTZEUR", {"letzte_stops": {
            "SOLEUR": h._heute()}}, W))

    def test_abklingzeit_mit_unlesbarem_datum_sperrt_nicht_dauerhaft(self):
        self.assertFalse(h.in_abklingzeit("SOLEUR", {"letzte_stops": {
            "SOLEUR": "kein datum"}}, W))

    def test_abklingzeit_laeuft_ab(self):
        alt = "2020-01-01"
        self.assertFalse(h.in_abklingzeit("SOLEUR", {"letzte_stops": {
            "SOLEUR": alt}}, W))


class GuthabenTorLive(unittest.TestCase):

    def test_ein_grund_nennt_alle_waehrungen(self):
        """Der Dauerlauf oeffnet sein Auto-Freigabefenster nur, wenn GENAU EIN
        Grund fehlt. Drei Waehrungen duerfen deshalb nicht drei Gruende
        ergeben - und der Grund darf nicht wie eine Fenster-Bitte aussehen."""
        w = dict(W)
        w["handel_erlaubt"] = True
        w["journal_zweitziel"] = "C:/gibt-es-nicht/handel"
        s = {"kill": False, "herzschlag_frisch": True, "rollierender_ev": None,
             "ev_negativ": False, "ruecklauf_eur": 0.0, "hoechststand_eur": 0.0,
             "groessenfaktor": 1.0, "freigabe_erfuellt": True}
        with patch.object(h.quote, "_CACHE", {"paare": PAARE}), \
                patch.object(h.kraken, "kontostaende", return_value=STEHENDE), \
                patch.object(h.kraken, "schluessel_vorhanden", return_value=True), \
                patch.object(h, "sitzung_da", return_value=True), \
                patch.object(h, "zeitfenster_offen", return_value=True), \
                patch.object(h.risikostufe, "live_erlaubt", return_value=True):
            gruende = h.live_sperren(w, s)
        guthaben = [g for g in gruende if "Guthaben" in g]
        self.assertEqual(len(guthaben), 1, "genau EIN Guthaben-Grund: %r" % gruende)
        for name in ("EUR", "USDC", "EURC"):
            self.assertIn(name, guthaben[0])
        self.assertNotIn("Freigabefenster", guthaben[0])

    def test_gedeckte_waehrung_ergibt_keinen_guthaben_grund(self):
        w = dict(W)
        w["handel_erlaubt"] = True
        w["journal_zweitziel"] = "C:/gibt-es-nicht/handel"
        s = {"kill": False, "herzschlag_frisch": True, "rollierender_ev": None,
             "ev_negativ": False, "ruecklauf_eur": 0.0, "hoechststand_eur": 0.0,
             "groessenfaktor": 1.0, "freigabe_erfuellt": True}
        voll = dict(STEHENDE)
        voll["USDC"] = 500.0
        with patch.object(h.quote, "_CACHE", {"paare": PAARE}), \
                patch.object(h.kraken, "kontostaende", return_value=voll), \
                patch.object(h.kraken, "schluessel_vorhanden", return_value=True), \
                patch.object(h, "sitzung_da", return_value=True), \
                patch.object(h, "zeitfenster_offen", return_value=True), \
                patch.object(h.risikostufe, "live_erlaubt", return_value=True):
            gruende = h.live_sperren(w, s)
        self.assertEqual([g for g in gruende if "Guthaben" in g], [])

    def test_anzeige_nennt_jede_waehrung(self):
        with patch.object(h.quote, "_CACHE", {"paare": PAARE}), \
                patch.object(h.kraken, "kontostaende", return_value=STEHENDE), \
                patch.object(h.kraken, "schluessel_vorhanden", return_value=True):
            text = h._guthaben_text(W)
        self.assertIn("EUR 46.83/60.00", text)
        self.assertIn("USDC 25.08/60.00", text)
        self.assertIn("EURC 0.00/60.00", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)