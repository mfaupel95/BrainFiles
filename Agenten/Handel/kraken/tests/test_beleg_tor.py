"""Das Freigabe-Tor in der kraken-Spur: Beleg vor dem Kauf, Order an die Hand.

Drei Dinge muessen stimmen, sonst ist der Beleg-Weg entweder wirkungslos oder
gefaehrlich:

1. OHNE BELEG KEIN KAUF. Kann die Spur keinen Beleg ausstellen (kein offenes
   Freigabefenster, handel_erlaubt=false), faellt der Einstieg aus - auch wenn
   `live=True` ankommt.
2. `order_ueber: "mcp"` heisst: die Spur ordert NICHT, sie stellt den Beleg aus
   und schreibt eine Journalzeile. Ausgefuehrt wird von der Hand.
3. AUF DEM EIGENEN WEG wird der Beleg SOFORT verbraucht (einmalig). Bliebe er
   liegen, koennte die Hand dieselbe Order ein zweites Mal ausfuehren.

Ohne Netz, ohne Order, ohne echte Datei: `handeln.freigabebeleg` ist ein Stub,
`menge_fuer` liefert feste Werte, `kraken.markt_kauf` ist ein Recorder, das
Journal zeigt in einen Temp-Ordner.

Ausfuehrbar (aus dem kraken-Ordner):  python tests/test_beleg_tor.py
"""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER.parent))

import handeln as h                                            # noqa: E402

W = {"max_pro_trade_eur": 50, "max_gesamt_eur": 200, "max_offene_positionen": 4,
     "gebuehr_taker": 0.004, "abklingzeit_tage": 3, "mindest_score": 65,
     "max_volatilitaet_pa": 1.20, "mindest_chance_risiko": 2.0,
     "pflicht_stop_prozent_min": 5.0, "pflicht_stop_prozent_max": 12.0,
     "bericht_max_alter_tage": 3, "handel_erlaubt": True}

V = {"inst": "XETHZEUR", "einstieg": 3000.0, "eur": 50.0, "stop": 2790.0,
     "ziel": 3420.0, "stop_pct": 7.0, "score": 80.0}


class BelegStub:
    """Steht fuer freigabebeleg: zeichnet auf, was die Spur verlangt."""

    def __init__(self, erlaubt=True, offen=None):
        self.erlaubt = erlaubt
        self.offen = offen                # der noch gueltige Beleg (oder None)
        self.ausgestellt = []
        self.geprueft = []
        self.verbraucht = []

    def offener(self, spur):
        return self.offen

    def schreibe(self, spur, seite, paar, menge, preis_max, grund,
                 gueltig_sekunden=600, preis_min=None, zusatz=None):
        if not self.erlaubt:
            return {"ok": False, "grund": "kein offenes Freigabefenster fuer %s" % spur}
        self.ausgestellt.append({"spur": spur, "seite": seite, "paar": paar,
                                 "menge": menge, "preis_max": preis_max,
                                 "zusatz": zusatz})
        return {"kennung": "B-%d" % len(self.ausgestellt), "spur": spur,
                "paar": paar, "seite": seite, "menge": menge,
                "preis_max": preis_max, "zusatz": zusatz or {}}

    def pruefe(self, kennung, spur, seite, paar, menge, preis=None):
        self.geprueft.append((kennung, spur, seite, paar, menge, preis))
        return True, "ok"

    def verbrauche(self, spur, kennung, ergebnis=""):
        self.verbraucht.append((spur, kennung, ergebnis))
        return True


class TorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal_pfad = Path(self.tmp.name) / "handelsjournal.csv"
        self.echt_journal = h.JOURNAL
        h.JOURNAL = self.journal_pfad
        self.addCleanup(setattr, h, "JOURNAL", self.echt_journal)

        self.stub = BelegStub()
        self.echt_beleg = h.freigabebeleg
        h.freigabebeleg = self.stub
        self.addCleanup(setattr, h, "freigabebeleg", self.echt_beleg)

        self.kauf = []
        self.echt_markt_kauf = h.kraken.markt_kauf
        h.kraken.markt_kauf = lambda paar, menge, echt=False: (
            self.kauf.append((paar, menge, echt)) or "TX-1")
        self.addCleanup(setattr, h.kraken, "markt_kauf", self.echt_markt_kauf)

        self.echt_menge_fuer = h.menge_fuer
        h.menge_fuer = lambda paar, eur, kurs: (0.0166, None)
        self.addCleanup(setattr, h, "menge_fuer", self.echt_menge_fuer)

        self.echt_gefuellt = h.kraken.gefuellte_menge
        h.kraken.gefuellte_menge = lambda txid: 0.0166
        self.addCleanup(setattr, h.kraken, "gefuellte_menge", self.echt_gefuellt)

        # STOLPERDRAHT: kein Test darf die Boerse anfassen. Jede signierte
        # Abfrage bricht hier ab und nennt den Methodennamen - so faellt auf,
        # wenn ein Test an einer Attrappe vorbei doch nach draussen greift.
        self.echt_roh = h.kraken._roh_privat
        self.roh_aufrufe = []

        def verboten(methode, **parameter):
            self.roh_aufrufe.append(methode)
            raise AssertionError("Test darf die Boerse nicht anfassen (%s)" % methode)

        h.kraken._roh_privat = verboten
        self.addCleanup(setattr, h.kraken, "_roh_privat", self.echt_roh)

    def _zeilen(self):
        if not self.journal_pfad.exists():
            return []
        return [z.strip() for z in self.journal_pfad.read_text(encoding="utf-8").splitlines()[1:]]

    def test_ohne_beleg_kein_kauf(self):
        """Der Kernsatz: kein Beleg (kein Fenster / handel_erlaubt aus) = kein Kauf."""
        self.stub.erlaubt = False
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V)], dict(W), live=True)
        self.assertEqual(self.kauf, [], "ohne Beleg darf keine Order rausgehen")
        self.assertEqual(z["positionen"], [])

    def test_hand_uebernimmt_bei_order_ueber_mcp(self):
        w = dict(W, order_ueber="mcp")
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V)], w, live=True)
        self.assertEqual(self.kauf, [], "order_ueber=mcp heisst: die Spur ordert nicht")
        self.assertEqual(z["positionen"], [], "ohne Fuellung keine Buchung")
        self.assertEqual(self.stub.verbraucht, [], "der Beleg bleibt fuer die Hand liegen")
        zeilen = self._zeilen()
        self.assertEqual(len(zeilen), 1)
        self.assertIn("kauf_beleg", zeilen[0])
        self.assertIn("beleg B-1", zeilen[0])
        self.assertEqual(self.stub.ausgestellt[0]["paar"], "XETHZEUR")
        self.assertAlmostEqual(self.stub.ausgestellt[0]["zusatz"]["stop"], 2790.0)

    def test_eigener_weg_verbraucht_den_beleg_sofort(self):
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V)], dict(W), live=True)   # order_ueber fehlt -> "spur"
        self.assertEqual(len(self.kauf), 1, "auf dem eigenen Weg wird geordert")
        self.assertEqual(self.kauf[0][2], True, "und zwar echt (live=True)")
        self.assertEqual(self.stub.verbraucht, [("kraken", "B-1", "spur")],
                         "der Beleg wird VOR der Order verbraucht (einmalig)")

    def test_beleg_traegt_stop_und_ziel(self):
        h._beleg_zur_order("XETHZEUR", 0.0166, 3000.0, 2790.0, 3420.0)
        a = self.stub.ausgestellt[-1]
        self.assertAlmostEqual(a["preis_max"], 3150.0)   # 5 % Luft ueber dem Einstieg
        self.assertEqual(a["zusatz"], {"inst": "XETHZEUR", "stop": 2790.0,
                                       "ziel": 3420.0})

    def test_beleg_traegt_den_einsatz(self):
        """Der Einsatz gehoert in den Beleg (T-283): er reserviert Kapital."""
        h._beleg_zur_order("XETHZEUR", 0.0166, 3000.0, 2790.0, 3420.0, eur=50.0)
        self.assertAlmostEqual(self.stub.ausgestellt[-1]["zusatz"]["eur"], 50.0)


class NurEinBelegJeZyklusTest(TorTest):
    """T-283: die kraken-Spur stellt HOECHSTENS EINEN Beleg je Zyklus aus.

    Am 01.10.2026 11:25:51 entstanden neun Belege in einem Lauf (ALGO/AVAX/
    LINK/TRX/DOT/SUI/LTC/ADA/SOL, je 50 EUR = 450 EUR bei max_gesamt_eur 200);
    acht davon verschwanden mit dem naechsten `schreibe()`, weil eine Spur nur
    EINE Belegdatei hat. Das Journal fuehrte neun Kaeufe, ausgefuehrt wurde
    einer. Ein offener Beleg ist eine beschlossene, noch nicht ausgefuehrte
    Kaufentscheidung - er belegt einen Platz und bindet Kapital.
    """

    V2 = {"inst": "XXBTZEUR", "einstieg": 50000.0, "eur": 50.0, "stop": 46000.0,
          "ziel": 60000.0, "stop_pct": 8.0, "score": 75.0}

    def test_nur_ein_beleg_je_zyklus(self):
        w = dict(W, order_ueber="mcp")
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V), dict(self.V2)], w, live=True)
        self.assertEqual(len(self.stub.ausgestellt), 1,
                         "ein Zyklus darf nur EINEN Beleg ausstellen: %s"
                         % [a["paar"] for a in self.stub.ausgestellt])
        self.assertEqual(self.stub.ausgestellt[0]["paar"], "XETHZEUR")

    def test_offener_beleg_belegt_einen_platz(self):
        """Ein offener Beleg zaehlt als belegter Platz - auch ohne Position."""
        self.stub.offen = {"kennung": "ALT", "paar": "ETHEUR", "seite": "buy",
                           "erstellt": "2026-10-01T11:25:51+00:00",
                           "gueltig_bis": "2026-10-01T11:35:51+00:00",
                           "zusatz": {"eur": 50.0}}
        w = dict(W, order_ueber="mcp", max_offene_positionen=1)
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V), dict(self.V2)], w, live=True)
        self.assertEqual(self.stub.ausgestellt, [],
                         "ein reservierter Platz darf nicht doppelt verplant werden")

    def test_offener_beleg_verhindert_neuen_beleg_auch_bei_platz(self):
        """T-102: ein offener Beleg blockiert einen neuen Beleg in DIESEM
        Zyklus - auch wenn Plaetze frei sind. Die Spur hat nur EINE
        Belegdatei (T-283); ein zweiter `schreibe()` wuerde den ersten
        ueberschreiben und in Fehlerzeilen stuerzen."""
        self.stub.offen = {"kennung": "ALT", "paar": "ETHEUR", "seite": "buy",
                           "erstellt": "2026-10-01T11:25:51+00:00",
                           "gueltig_bis": "2026-10-01T11:35:51+00:00",
                           "zusatz": {"eur": 50.0}}
        w = dict(W, order_ueber="mcp", max_offene_positionen=4)
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V), dict(self.V2)], w, live=True)
        self.assertEqual(self.stub.ausgestellt, [],
                         "bei offenem Beleg darf kein neuer Beleg entstehen")

    def test_offener_beleg_reserviert_kapital(self):
        """Der reservierte Einsatz zaehlt gegen max_gesamt_eur."""
        self.stub.offen = {"kennung": "ALT", "paar": "ETHEUR", "seite": "buy",
                           "erstellt": "2026-10-01T11:25:51+00:00",
                           "gueltig_bis": "2026-10-01T11:35:51+00:00",
                           "zusatz": {"eur": 50.0}}
        w = dict(W, order_ueber="mcp", max_gesamt_eur=50)
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V)], w, live=True)
        self.assertEqual(self.stub.ausgestellt, [],
                         "50 reserviert + 50 neu > max_gesamt_eur 50")

    def test_verfallener_beleg_blockiert_nicht(self):
        """Ein abgelaufener/verbrauchter Beleg ist keine Reservierung."""
        self.stub.offen = None            # freigabebeleg.offener() liefert nur Gueltige
        w = dict(W, order_ueber="mcp", max_offene_positionen=1)
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V)], w, live=True)
        self.assertEqual(len(self.stub.ausgestellt), 1,
                         "nach dem Verfall muss wieder ein Beleg entstehen")

    def test_im_papierlauf_wird_kein_beleg_gezaehlt(self):
        """Papier kennt keine Belege: die Reservierung gilt nur im Live-Zweig."""
        self.stub.offen = {"kennung": "ALT", "paar": "ETHEUR", "seite": "buy",
                           "zusatz": {"eur": 50.0}}
        w = dict(W, order_ueber="mcp", max_offene_positionen=1)
        z = {"positionen": [], "letzte_stops": {}}
        h.pruefe_einstiege(z, [dict(V)], w, live=False)
        self.assertEqual(len(z["positionen"]), 1,
                         "der Papierlauf darf vom Belegzustand nicht abhaengen")


if __name__ == "__main__":
    unittest.main()
