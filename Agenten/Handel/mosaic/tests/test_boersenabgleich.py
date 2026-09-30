"""Buch gegen Boerse fuer mosaic - die Regeln, nicht die Werte (T-207).

Befund 30.09.2026: die drei Kraken-Stops der Spur (BTC/ETH/SOL, rund 258 EUR)
trugen an der Boerse den Status ``canceled``, waehrend ``zustand.json`` weiter
``boersen_stop_fehlt: false`` meldete. Ein Feld im Buch ist eine Behauptung,
die altert - nur die Boerse weiss, ob der Notausstieg noch steht.

Geprueft werden die REGELN aus ``scanner/boersenstops.py``, kraken-seitig:

  (a) gesunder Fall: Bestand da + Stop offen -> nichts tun;
  (b) stornierter Stop -> neu setzen, und zwar ueber den GEHALTENEN Bestand;
  (c) Position ohne Bestand + Stop gefeuert -> mit ECHTEM Erloes ausbuchen;
  (d) Position ohne Bestand, Stop nicht gefeuert -> NICHT buchen (kein Beleg);
  (e) Waisenstop (Buch kennt die Kennung, keine Live-Position mehr) -> stornieren;
  (f) ein Stop, den das Buch NICHT kennt, wird nie angefasst (Max' Handstops);
  (g) Papiermodus: keine Live-Position -> kein einziger Boersenabruf;
  (h) Vorschau schreibt nichts, ordert nichts;
  (i) unlesbare Boerse/Bestand -> Buch unangetastet, nur gemeldet.

Kein Netz: die Boerse ist eine Attrappe, ``laden`` ist die Naht. Ein
Modulwaechter vergleicht danach den echten Spurenordner.

Lauf (aus mosaic/tests):
 ..\\..\\scanner\\.venv\\Scripts\\python.exe -m unittest test_boersenabgleich -v
"""

import os
import sys
import tempfile
import time
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import boersenabgleich  # noqa: E402
import handeln        # noqa: E402


class Schreibgeschuetzt(unittest.TestCase):
    """Setzt ``handeln.SCHREIBEN`` nur fuer die Dauer des Tests aus.

    NICHT auf Modulebene: ``unittest discover`` laedt alle Testmodule in EINEM
    Prozess, eine Zuweisung beim Import schaltet auch die Schreibpfade der
    Nachbarmodule ab (genau das liess test_papier_laesst_live_stehen mit
    '0 statt 1 Journalzeile' rot werden).
    """

    def setUp(self):
        self._schreiben_alt = handeln.SCHREIBEN
        handeln.SCHREIBEN = False

    def tearDown(self):
        handeln.SCHREIBEN = self._schreiben_alt


# --- Modulwaechter: kein Test darf in den echten Spurenordner schreiben ----

def _ordner_stand():
    out = {}
    for name in ("zustand.json", "handelsjournal.csv", "zustand.mittel.json",
                 "handelsjournal.mittel.csv"):
        p = os.path.join(HIER, name)
        out[name] = os.path.getsize(p) if os.path.exists(p) else None
    return out


def setUpModule():
    global _vorher
    _vorher = _ordner_stand()


def tearDownModule():
    nach = _ordner_stand()
    geaendert = [k for k in nach if nach[k] != _vorher.get(k)]
    assert not geaendert, ("Test hat in den ECHTEN Spurenordner geschrieben: %s"
                           % geaendert)


# --- Attrappen --------------------------------------------------------------

class FakeBoerse:
    """Ein Boersenzugang ohne Netz - dieselbe Oberflaeche wie KrakenBoerse."""

    def __init__(self, bestaende=None, stops=None, fremd=(), fehler=None):
        self.bestaende = dict(bestaende or {})     # {inst: menge}
        self.stops = dict(stops or {})             # {txid: {...}}
        self.fremd = list(fremd)
        self.fehler = fehler                       # Bestand nicht lesbar
        self.gesetzt = []
        self.storniert = []
        self.gelesen = 0

    def basis(self, inst):
        return inst

    def bestand(self, inst):
        self.gelesen += 1
        if self.fehler:
            raise RuntimeError(self.fehler)
        return float(self.bestaende.get(inst, 0.0))

    def stop_wirksam(self, txid):
        if not txid:
            return False
        d = self.stops.get(txid)
        if d is None or d.get("unbekannt"):
            return None                    # nicht lesbar, NICHT "fehlt"
        if float(d.get("vol_exec") or 0) > 0:
            return False
        return d.get("status") == "open"

    def stop_gefuellt(self, txid):
        return float((self.stops.get(txid) or {}).get("vol_exec") or 0) > 0

    def ausstieg(self, inst, txid):
        d = self.stops.get(txid) or {}
        menge = float(d.get("vol_exec") or 0)
        cost = float(d.get("cost") or 0)
        if menge <= 0 or cost <= 0:
            return None
        return {"menge": menge, "preis": cost / menge,
                "erloes": cost - float(d.get("fee") or 0), "art": "stop-loss",
                "misc": "stopped"}

    def menge_gerundet(self, inst, menge):
        m = float("%.8f" % float(menge))
        return m if m > 0 else None

    def stop_setzen(self, inst, menge, preis):
        self.gesetzt.append((inst, menge, preis))
        return "NEU-%d" % len(self.gesetzt)

    def stop_stornieren(self, inst, txid):
        self.storniert.append((inst, txid))

    def fremde_stops(self, bekannt):
        return list(self.fremd)


class Journal:
    def __init__(self):
        self.zeilen = []

    def __call__(self, **felder):
        self.zeilen.append(felder)


def live(inst="BTC-USDC", **abweichend):
    p = {"inst": inst, "seite": "long", "einstieg": 100.0, "stop": 95.0,
         "ziel": 110.0, "stop_pct": 5.0, "nominal": 50.0, "modus": "live",
         "boerse": "kraken", "stop_algo_id": "S1", "stop_txid": "S1",
         "boersen_stop_fehlt": False}
    p.update(abweichend)
    return p


def papier(inst="ETH-USDC", **abweichend):
    p = {"inst": inst, "seite": "long", "einstieg": 100.0, "stop": 95.0,
         "ziel": 110.0, "stop_pct": 5.0, "nominal": 50.0}
    p.update(abweichend)
    return p


def buch(*positionen):
    return {"positionen": list(positionen)}


def laufe(z, boerse, journal=None, anwenden=True, standard="kraken"):
    return boersenabgleich.pruefe(
        z, anwenden=anwenden, journal=journal, standard=standard,
        laden=lambda namen: {n: boerse for n in namen})


def offener_stop(preis=95.0, menge=0.5):
    return {"status": "open", "vol_exec": 0, "preis": preis, "menge": menge}


# --- Tests ------------------------------------------------------------------

class GesunderFallTest(Schreibgeschuetzt):
    def test_bestand_da_stop_offen_nichts_zu_tun(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5}, stops={"S1": offener_stop()})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["ok"], 1)
        self.assertEqual(bilanz["nachgesetzt"], 0)
        self.assertEqual(b.gesetzt, [])
        self.assertEqual(len(z["positionen"]), 1)
        self.assertFalse(z["positionen"][0]["boersen_stop_fehlt"])

    def test_alte_behauptung_wird_berichtigt(self):
        """Ein veraltetes boersen_stop_fehlt wird beim Nachsehen geloescht."""
        z = buch(live(boersen_stop_fehlt=True))
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5}, stops={"S1": offener_stop()})
        laufe(z, b)
        self.assertFalse(z["positionen"][0]["boersen_stop_fehlt"])


class StornierterStopTest(Schreibgeschuetzt):
    def test_stornierter_stop_wird_ueber_den_bestand_nachgesetzt(self):
        # Buch 0,5 Stueck (nominal 50 / einstieg 100), Boerse hat nur 0,4
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC-USDC": 0.4},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["nachgesetzt"], 1)
        self.assertEqual(b.gesetzt, [("BTC-USDC", 0.4, 95.0)])
        p = z["positionen"][0]
        self.assertEqual(p["stop_algo_id"], "NEU-1")
        self.assertEqual(p["stop_txid"], "NEU-1")
        self.assertFalse(p["boersen_stop_fehlt"])

    def test_stop_wird_nie_ueber_mehr_als_den_bestand_gesetzt(self):
        z = buch(live(nominal=100.0))          # Buch 1,0 Stueck
        b = FakeBoerse(bestaende={"BTC-USDC": 0.4},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        laufe(z, b)
        self.assertEqual(b.gesetzt[0][1], 0.4)

    def test_fehlende_kennung_setzt_ebenfalls(self):
        z = buch(live(stop_algo_id="", stop_txid=""))
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5}, stops={})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["nachgesetzt"], 1)
        self.assertEqual(len(b.gesetzt), 1)

    def test_bestand_unter_ordermin_bleibt_ohne_stop_gemeldet(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        b.menge_gerundet = lambda inst, menge: None
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["fehlt_weiter"], 1)
        self.assertEqual(bilanz["nachgesetzt"], 0)
        self.assertEqual(b.gesetzt, [])
        self.assertTrue(z["positionen"][0]["boersen_stop_fehlt"])


class PositionWegTest(Schreibgeschuetzt):
    def test_gefeuerter_stop_bucht_mit_echtem_erloes_aus(self):
        z = buch(live())
        b = FakeBoerse(bestaende={}, stops={"S1": {
            "status": "closed", "vol_exec": 0.5, "cost": 47.5, "fee": 0.285}})
        j = Journal()
        bilanz = laufe(z, b, journal=j)
        self.assertEqual(bilanz["ausgebucht"], 1)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(j.zeilen), 1)
        zeile = j.zeilen[0]
        self.assertEqual(zeile["modus"], "live")
        self.assertEqual(zeile["aktion"], "verkauf")
        self.assertEqual(zeile["grund"], "boersen_stop")
        # Das Journal fuehrt zwei Nachkommastellen (Hausformat).
        self.assertAlmostEqual(float(zeile["einsatz_usd"]), 47.22, places=2)
        self.assertAlmostEqual(float(zeile["preis"]), 95.0, places=6)

    def test_ohne_beleg_kein_buch(self):
        """Stop nicht gefeuert (Handverkauf?) - ohne Ausstiegspreis keine Buchung."""
        z = buch(live())
        b = FakeBoerse(bestaende={},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        j = Journal()
        bilanz = laufe(z, b, journal=j)
        self.assertEqual(bilanz["ausgebucht"], 0)
        self.assertEqual(bilanz["unklar"], 1)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(j.zeilen, [])

    def test_nachgesetzter_stop_kommt_bei_einer_weg_position_nicht_mehr(self):
        """Reihenfolge: erst weg -> ausbuchen, kein zweiter Stop."""
        z = buch(live())
        b = FakeBoerse(bestaende={}, stops={"S1": {
            "status": "closed", "vol_exec": 0.5, "cost": 47.5, "fee": 0.285}})
        laufe(z, b)
        self.assertEqual(b.gesetzt, [])


class WaisenstopTest(Schreibgeschuetzt):
    def test_stop_ohne_position_wird_storniert(self):
        # Die Papierposition traegt eine Kennung, die an der Boerse offen steht.
        z = buch(live(inst="SOL-USDC", stop_algo_id="S9", stop_txid="S9"),
                 papier(stop_algo_id="P1", stop_txid="P1"))
        b = FakeBoerse(bestaende={"SOL-USDC": 0.5},
                       stops={"S9": offener_stop(), "P1": offener_stop()})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["waisen"], 1)
        self.assertEqual(b.storniert, [("ETH-USDC", "P1")])

    def test_fremder_stop_wird_nie_angefasst(self):
        """Ein Stop, den das Buch nicht kennt, ist fremde Absicherung."""
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5}, stops={"S1": offener_stop()},
                       fremd=[("FREMD-1", {"paar": "XLMEUR"})])
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["waisen"], 0)
        self.assertEqual(b.storniert, [])

    def test_erledigter_waisenstop_wird_vergessen(self):
        z = buch(live(inst="SOL-USDC", stop_algo_id="S9", stop_txid="S9"),
                 papier(stop_algo_id="P1", stop_txid="P1"))
        b = FakeBoerse(bestaende={"SOL-USDC": 0.5},
                       stops={"S9": offener_stop(),
                              "P1": {"status": "closed", "vol_exec": 1.0}})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["waisen"], 0)
        self.assertEqual(b.storniert, [])


class PapiermodusTest(Schreibgeschuetzt):
    def test_ohne_live_position_kein_boersenabruf(self):
        z = buch(papier(), papier(inst="SOL-USDC"))
        gerufen = []

        def laden(namen):
            gerufen.append(namen)
            return {}

        bilanz = boersenabgleich.pruefe(z, anwenden=True, laden=laden)
        self.assertEqual(gerufen, [])
        self.assertEqual(bilanz["geprueft"], 0)
        self.assertEqual(len(z["positionen"]), 2)

    def test_papierposition_wird_nicht_ausgebucht(self):
        z = buch(live(), papier(inst="SOL-USDC"))
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5, "SOL-USDC": 0.0},
                       stops={"S1": offener_stop()})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["geprueft"], 1)      # nur die Live-Position
        self.assertEqual(len(z["positionen"]), 2)


class VorschauTest(Schreibgeschuetzt):
    def test_vorschau_setzt_keinen_stop_und_bucht_nicht(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5},
                       stops={"S1": {"status": "canceled", "vol_exec": 0}})
        j = Journal()
        bilanz = laufe(z, b, journal=j, anwenden=False)
        self.assertEqual(bilanz["fehlt_weiter"], 1)
        self.assertEqual(b.gesetzt, [])
        self.assertEqual(j.zeilen, [])
        # die Kennung bleibt die alte - die Vorschau erfindet keine
        self.assertEqual(z["positionen"][0]["stop_algo_id"], "S1")

    def test_vorschau_bucht_weg_position_nicht_aus(self):
        z = buch(live())
        b = FakeBoerse(bestaende={}, stops={"S1": {
            "status": "closed", "vol_exec": 0.5, "cost": 47.5, "fee": 0.285}})
        j = Journal()
        bilanz = laufe(z, b, journal=j, anwenden=False)
        self.assertEqual(bilanz["weg"], 1)
        self.assertEqual(bilanz["ausgebucht"], 0)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(j.zeilen, [])


class UnklarerFallTest(Schreibgeschuetzt):
    def test_unlesbarer_bestand_laesst_das_buch_in_ruhe(self):
        z = buch(live())
        b = FakeBoerse(fehler="Netzfehler")
        j = Journal()
        bilanz = laufe(z, b, journal=j)
        self.assertEqual(bilanz["unklar"], 1)
        self.assertEqual(bilanz["ok"], 0)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(b.gesetzt, [])
        self.assertEqual(j.zeilen, [])

    def test_unbekannte_boerse_wird_gemeldet_statt_geraten(self):
        z = buch(live(boerse="bitfinex"))
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5}, stops={"S1": offener_stop()})
        # wie lade_boersen: unbekannter Name -> None (nicht der Attrappen-Zugang)
        bilanz = boersenabgleich.pruefe(
            z, anwenden=True,
            laden=lambda namen: {n: (b if n == "kraken" else None)
                                 for n in namen})
        self.assertEqual(bilanz["unklar"], 1)
        self.assertEqual(bilanz["ok"], 0)
        self.assertEqual(len(z["positionen"]), 1)

    def test_nicht_lesbarer_stop_gilt_nicht_als_fehlt(self):
        z = buch(live())
        b = FakeBoerse(bestaende={"BTC-USDC": 0.5},
                       stops={"S1": {"unbekannt": True}})
        bilanz = laufe(z, b)
        self.assertEqual(bilanz["unklar"], 1)
        self.assertEqual(b.gesetzt, [])


class ZeitwacheTest(Schreibgeschuetzt):
    def test_frische_zustandsdatei_verhindert_das_schreiben(self):
        """--anwenden darf nicht in einen laufenden Zyklus schreiben."""
        with tempfile.TemporaryDirectory() as d:
            pfad = os.path.join(d, "zustand.json")
            with open(pfad, "w", encoding="utf-8") as f:
                f.write('{"positionen": []}\n')
            os.utime(pfad, (time.time(), time.time()))
            rc = boersenabgleich.main(["--anwenden", "--pfad", pfad])
            self.assertEqual(rc, 2)
            with open(pfad, encoding="utf-8") as f:
                self.assertEqual(json_laden(f.read()), {"positionen": []})

    def test_leeres_buch_ohne_boersenabruf(self):
        with tempfile.TemporaryDirectory() as d:
            pfad = os.path.join(d, "zustand.json")
            with open(pfad, "w", encoding="utf-8") as f:
                f.write('{"positionen": []}\n')
            self.assertEqual(boersenabgleich.main(["--pfad", pfad]), 0)


def json_laden(text):
    import json
    return json.loads(text)


class EinbauTest(Schreibgeschuetzt):
    """Der Abgleich muss in JEDEM Zyklus der Basis laufen - nicht nur im
    Live-Zweig (Regel aus der Karte: Punkt 4, 'Fehler nicht abwuergen')."""

    def _quelle(self):
        with open(os.path.join(HIER, "handeln.py"), encoding="utf-8") as f:
            return f.read()

    def test_abgleich_wird_gerufen_und_ist_abgesichert(self):
        q = self._quelle()
        self.assertIn("boersenabgleich.pruefe(", q)
        i = q.index("boersenabgleich.pruefe(")
        block = q[q.rindex("if risikostufe.ist_basis():", 0, i):i + 1200]
        self.assertIn("anwenden=True", block)
        self.assertIn("journal=journal", block)
        self.assertIn("except Exception", block)

    def test_abgleich_steht_ausserhalb_des_live_zweigs(self):
        """Steht er IM Live-Zweig, laeuft er genau dann nicht, wenn eine
        Sperre zu ist - und dann sind die echten Positionen ungeschuetzt."""
        q = self._quelle()
        i = q.index("boersenabgleich.pruefe(")
        zwischen = q[q.rindex("if risikostufe.ist_basis():", 0, i):i]
        self.assertNotIn("if live:", zwischen)
        self.assertLess(i, q.index("if live:", i))

    def test_abgleich_laeuft_vor_buchabgleich_und_ausstiegen(self):
        """Eine vom Boersen-Stop geschlossene Position darf der Ausstiegspfad
        nicht ein zweites Mal verkaufen wollen."""
        q = self._quelle()
        i = q.index("boersenabgleich.pruefe(")
        self.assertLess(i, q.index("live_ausstiege(z, w)", i))
        self.assertLess(i, q.index("bueche_papier_altlasten_aus(z, w)", i))

    def test_nur_die_basis_fasst_die_boerse_an(self):
        """Die Stufen mittel/hoch fuehren Kopien des Buchs - eine Order von
        dort traefe dieselben echten Positionen ein zweites Mal."""
        q = self._quelle()
        i = q.index("boersenabgleich.pruefe(")
        self.assertIn("ist_basis()", q[q.rindex("if risikostufe.ist_basis():", 0, i):i])


if __name__ == "__main__":
    unittest.main()