"""Tests des Mosaic-Live-Zweigs (Stufe A, OKX-Spot). Kein Netz, kein echtes Ziel.

Geprueft wird:
 (a) live_sperren: nennt jede offene Sperre namentlich; bei voll geoeffneter
     Kette leer. Demo-Modus ist eine Hard-Sperre (OKX_DEMO/OKX_SIMULATED).
 (b) _live_grenze: live_*-Feld bevorzugt, sonst das Basis-Feld.
 (c) live_einstiege: bei bestaetigter Freigabe kauft es echt (via OP-Seams),
     legt den Boersen-Stop, bucht die Position (modus=live) + Journal kauf.
 (d) live_ausstiege: verkauft eine Stop-/Ziel-Position und storniert den
     Boersen-Stop zuerst; ein fehlgeschlagener Verkauf laesst die Position.
 (e) flach_stellen_live: raeumt NUR Live-Positionen, Papier bleibt stehen.
 (f) Demo-Sperre: --live mit aktiver Demo-Variable bleibt Papier (kein ECHT).

Alle Order-/Boorse-Funktionen sind Seams (handeln.op_kauf usw.) und werden
hier durch Fake-Funktionen ersetzt - kein Test spricht je echt mit OKX. Wachen,
Zustand und Journal zeigen in jedem Test auf ein Temp-Verzeichnis, nie auf den
echten Spurenordner.

Lauf (aus mosaic/tests):
 ..\\..\\scanner\\.venv\\Scripts\\python.exe unittest test_live_zweig -v
"""

import json
import os
import shutil
import sys
import tempfile
import csv
import unittest

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL, HIER):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln  # noqa: E402
import okx_spot  # noqa: E402


# --- Modulwaechter: kein Test darf in den echten Spurenordner schreiben ----

def _ordner_stand():
    """Dateiname+Groesse des echten Spurenordners (zustand, journal)."""
    out = {}
    for name in ("zustand.json", "zustand.mittel.json",
                 "handelsjournal.csv", "handelsjournal.mittel.csv"):
        p = os.path.join(HIER, name)
        out[name] = os.path.getsize(p) if os.path.exists(p) else None
    return out


def setUpModule():
    global _vorher
    _vorher = _ordner_stand()


def tearDownModule():
    global _vorher
    nach = _ordner_stand()
    verletzt = {k for k in _vorher if _vorher[k] != nach.get(k)}
    if verletzt:
        raise AssertionError(
            "Live-Test hat in den echten Spurenordner geschrieben: %s"
            % sorted(verletzt))


# --- Kerzen-Helfer (auch ohne Netz) -----------------------------------------

def _kerze(open_, high, low, close, ts=0):
    return [ts, open_, high, low, close, 0.0]


def _aufwaerts(n, basis=100.0, schritt=0.01, ts0=1700000000000,
               intervall=3600000):
    out = []
    for i in range(n):
        phase = i % 8
        welle = 0.0
        if phase == 4:
            welle = -0.05
        elif phase == 7:
            welle = 0.05
        o = basis + i * schritt + welle * 0.4
        c = o + schritt
        h = max(o, c) + 0.01
        l = min(o, c) - 0.01
        out.append(_kerze(o, h, l, c, ts0 + i * intervall))
    return out


def _pullback_zone(k30, zone, ts0=1700000000000, intervall=1800000):
    untere, obere = zone
    n = len(k30)
    start = k30[-1][4]
    ziele = [start, (untere + start) / 2, untere, untere, (untere + obere) / 2]
    for j, ziel in enumerate(ziele):
        o = start if j == 0 else k30[-1][4]
        c = ziel
        h = max(o, c) + 0.005
        l = min(o, c) - 0.005
        k30.append(_kerze(o, h, l, c, ts0 + (n + j) * intervall))
    return k30


def _k5_bos(basis=100.0, ts0=1700000000000, intervall=300000):
    out = []
    for i in range(60):
        if i < 50:
            phase = i / 20.0 * 2 * 3.14159 if i < 20 else \
                (i - 20) / 30.0 * 2 * 3.14159
            welle = 0.03 * (phase if i < 20
                            else (1 - abs(phase - 3.14159) / 3.14159))
            o = basis + welle
            c = o + 0.002
            h = o + 0.015
            l = o - 0.015
        else:
            o = basis + 0.20 + (i - 50) * 0.004
            c = o + 0.012
            h = o + 0.03
            l = o - 0.008
        out.append(_kerze(o, h, l, c, ts0 + i * intervall))
    return out


def _setup_kerzen(w):
    """Erzeugen eines Long-Setups: (k4, k30, k5), mit dem signal()='long'."""
    k4 = _aufwaerts(40)
    k30 = _aufwaerts(40, intervall=1800000)
    zone = handeln.nachfrage_zone(k30, w)
    k30 = _pullback_zone(k30, zone)
    k5 = _k5_bos()
    return k4, k30, k5


class _Basis(unittest.TestCase):
    """Temporaere Wachen/Zustand/Journal, SCHREIBEN=False, OP-Seams fake."""

    def setUp(self):
        # Die echten Seams ZUERST sichern - nach dem Patchen waeren hier die
        # Fakes drin und das Zuruecksetzen im tearDown wirkungslos.
        self._seams_alt = (handeln.op_kauf, handeln.op_verkauf, handeln.op_stop,
                           handeln.op_stop_stornieren, handeln.op_gefuellt,
                           handeln.op_guthaben, handeln.live_kurs_quelle,
                           handeln.live_menge_fuer, handeln.hole_freigabe)
        self._zf_alt = handeln.zeitfenster_offen
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.w = {
            "waehrung": "USD", "handel_erlaubt": True,
            "herzschlag_max_minuten": 45,
            "risiko_je_position_usd": 5.0,
            "max_offene_positionen": 4, "max_pro_trade_usd": 150.0,
            "max_gesamt_usd": 600.0, "kill_switch_gesamt_usd": 40.0,
            "pflicht_stop_prozent_min": 5.0,
            "pflicht_stop_prozent_max": 12.0, "ziel_r_vielfaches": 2.0,
            "mindest_kerzen": 30, "kerzen_takt_4h": "4H",
            "kerzen_takt_30m": "30m", "kerzen_takt_5m": "5m",
            "trend_kerzen_4h": 1, "trend_min_kerzen_4h": 0,
            "zone_schwung_kerzen_30m": 20, "zone_beruehrung_kerzen_30m": 30,
            "zone_typ": "swing", "struktur_shift_kerzen_5m": 30,
            "instrumente": ["TEST-USDT"],
            "journal_zweitziel": r"Q:\Handel_Journal\mosaic",
            "drawdown_halbierung_usd": 20.0,
            "live_max_pro_trade_usd": 10.0, "live_max_offene_positionen": 5,
            "live_max_gesamt_usd": 200.0, "mindest_guthaben_usdc": 30.0,
            "freigabe": {"erfuellt": True},
        }
        self._saved = (handeln.WACHEN, handeln.ZUSTAND, handeln.JOURNAL,
                       handeln.SCHREIBEN, handeln.kerzen_quelle)
        # VENUE ist eine MODULGLOBALE (venue_binden() setzt sie): ein Test, der
        # die Boerse wechselt (z. B. test_boersenwahl), laesst sie stehen. Dann
        # prueft live_sperren() die Demo-Sperre der ANDEREN Boerse, und
        # test_demo_ist_harte_sperre faellt um - je nach Reihenfolge. Deshalb
        # hier sichern und im tearDown zuruecksetzen; der Demo-Test bindet die
        # Boerse zusaetzlich ausdruecklich selbst.
        self._venue_alt = handeln.VENUE
        handeln.WACHEN = os.path.join(self.tmp, "wachen.json")
        handeln.ZUSTAND = os.path.join(self.tmp, "zustand.json")
        handeln.JOURNAL = os.path.join(self.tmp, "handelsjournal.csv")
        handeln.SCHREIBEN = False
        # OP-Seams auf Fakes (kein echter OKX-Kontakt)
        self.aufrufe = []
        handeln.op_kauf = self._fake_kauf
        handeln.op_verkauf = self._fake_verkauf
        handeln.op_stop = self._fake_stop
        handeln.op_stop_stornieren = self._fake_stop_stornieren
        handeln.op_gefuellt = self._fake_gefuellt
        handeln.op_guthaben = lambda: 500.0
        handeln.live_kurs_quelle = lambda inst: 105.0
        handeln.live_menge_fuer = lambda inst, usdt, kurs: (0.12345, None)
        handeln.hole_freigabe = lambda vs, z, s: vs  # bestaetigt unveraendert
        # Das Zeitfenster (freigabefenster.py) zeigt in Tests NIE auf das echte
        # freigabe_fenster.json: sonst haengt das Ergebnis davon ab, ob Max
        # gerade live freigegeben hat - ein Test, der bei offenem Fenster anders
        # laeuft, prueft den Kalender, nicht den Code.
        handeln.zeitfenster_offen = lambda: False
        # Registry kann Demo-Variable UND Keys tragen (Umgebungs-pop loescht
        # sie nicht). Fuer deterministische Tests das Modul direkt mocken; in
        # tearDown zuruecksetzen.
        self._okx = okx_spot
        self._okx_demo_alt = okx_spot.demo_modus
        self._okx_keys_alt = okx_spot.schluessel_vorhanden
        okx_spot.demo_modus = lambda: False
        okx_spot.schluessel_vorhanden = lambda: True
        # Umgebung: kein Risiko -> Live erlaubt
        self._env = os.environ.copy()
        for k in ("OKX_SIMULATED", "OKX_DEMO", "HANDEL_RISIKO"):
            os.environ.pop(k, None)
        # Kerzen (Long-Setup). Schon beim Laden der Wachen-Indizes gebaut.
        handeln.kerzen_quelle = self._fake_kerzen
        self._k4, self._k30, self._k5 = None, None, None

    def _fake_kerzen(self, inst, iv, n):
        if self._k4 is None:
            self._k4, self._k30, self._k5 = _setup_kerzen(self.w)
        return {"4H": self._k4, "30m": self._k30, "5m": self._k5}[iv]

    def test_gescheiterter_kauf_wird_journalisiert(self):
        """Ein gescheiterter Live-Kauf MUSS eine Journalzeile hinterlassen.

        Ohne sie meldet der Dauerlauf die Spur als "ok", stderr wird verworfen,
        und der Grund fuer einen ausbleibenden Einstieg waere spaeter nicht
        feststellbar (Auftrag Max 21.09.2026: "erste order melden"; der Waechter
        mosaic-live-wache liest genau diese Zeile).
        """
        handeln.SCHREIBEN = True
        handeln.op_kauf = lambda inst, menge: (_ for _ in ()).throw(
            RuntimeError("50101 APIKey does not match current environment"))
        z = {"positionen": [], "modus": "papier"}
        s = {"kill": False, "herzschlag_frisch": True, "rollierender_ev": 1.0,
             "ruecklauf_usd": 0.0}
        handeln.live_einstiege(z, self.w, s)
        self.assertEqual(z["positionen"], [], "kein Einstieg ins Buch")
        with open(handeln.JOURNAL, newline="", encoding="utf-8") as f:
            zeilen = [r for r in csv.DictReader(f) if r["aktion"] == "fehler"]
        self.assertEqual(len(zeilen), 1, "genau eine Fehlerzeile")
        self.assertIn("50101", zeilen[0]["grund"])
        self.assertEqual(zeilen[0]["modus"], "live")

    def _fake_kauf(self, inst, menge):
        self.aufrufe.append(("kauf", inst, menge))
        return "ORD1"

    def _fake_verkauf(self, inst, menge):
        self.aufrufe.append(("verkauf", inst, menge))
        return "ORD2"

    def _fake_stop(self, inst, menge, seite, trigger):
        self.aufrufe.append(("stop", inst, menge, seite, trigger))
        return "ALGO1"

    def _fake_stop_stornieren(self, inst, algo_id):
        self.aufrufe.append(("stop_stornieren", inst, algo_id))
        return True

    def _fake_gefuellt(self, inst, ord_id):
        return 0.11234

    def tearDown(self):
        handeln.VENUE = self._venue_alt
        os.environ.clear()
        os.environ.update(self._env)
        self._okx.demo_modus = self._okx_demo_alt
        self._okx.schluessel_vorhanden = self._okx_keys_alt
        (handeln.WACHEN, handeln.ZUSTAND, handeln.JOURNAL, handeln.SCHREIBEN,
         handeln.kerzen_quelle) = self._saved
        handeln.zeitfenster_offen = self._zf_alt
        (handeln.op_kauf, handeln.op_verkauf, handeln.op_stop,
         handeln.op_stop_stornieren, handeln.op_gefuellt,
         handeln.op_guthaben, handeln.live_kurs_quelle,
         handeln.live_menge_fuer, handeln.hole_freigabe) = self._seams_alt
        self._saved = None
        self._tmp.cleanup()


def _lage(w):
    """Ein wp.lage-artiges dict, das live_sperren versteht (kein Netz)."""
    return {"freigabe_erfuellt": w.get("freigabe", {}).get("erfuellt", False),
            "herzschlag_frisch": True, "ev_negativ": False,
            "rollierender_ev": 0.5, "ruecklauf_usd": 0.0}


class LiveSperrenTest(_Basis):

    def test_gesperrt_bei_handel_erlaubt_false(self):
        self.w["handel_erlaubt"] = False
        g = handeln.live_sperren(self.w, _lage(self.w))
        self.assertTrue(any("handel_erlaubt" in x for x in g))

    def test_gesperrt_bei_freigabe_false(self):
        self.w["freigabe"]["erfuellt"] = False
        g = handeln.live_sperren(self.w, _lage(self.w))
        self.assertTrue(any("freigabe" in x and "false" in x for x in g))

    def test_demo_ist_harte_sperre(self):
        # Die Boerse ausdruecklich binden: live_sperren() fragt VENUE.demo_modus(),
        # und VENUE ist eine Modulglobale (siehe setUp).
        handeln.VENUE = self._okx
        self._okx.demo_modus = lambda: True
        g = handeln.live_sperren(self.w, _lage(self.w))
        # Demo -> keine echten Orders, Grund wird namentlich genannt.
        self.assertTrue(any("OKX_DEMO" in x or "Demo" in x for x in g))

    def test_frische_kette_leer(self):
        os.environ.pop("OKX_DEMO", None)
        gespeichert = handeln.sitzung_da
        handeln.sitzung_da = lambda: True  # im Test gilt: jemand sitzt dran
        try:
            g = handeln.live_sperren(self.w, _lage(self.w))
        finally:
            handeln.sitzung_da = gespeichert
        self.assertEqual(g, [])

    def test_zeitfenster_ohne_bildschirm_ist_eine_freigabe(self):
        """Punkt 3 der Handelsregeln hat zwei Fassungen - im Dauerbetrieb
        zaehlt das Zeitfenster.

        Unter MAXHIRN_ROUTINE=1 ist sitzung_da() immer False. Ohne die zweite
        Fassung sperrte sich mosaic damit in jedem Zyklus selbst, obwohl der
        Dauerlauf zu Recht ein Fenster geoeffnet hatte (Befund 21.09.2026).
        """
        os.environ["MAXHIRN_ROUTINE"] = "1"
        handeln.zeitfenster_offen = lambda: True
        g = handeln.live_sperren(self.w, _lage(self.w))
        self.assertEqual(g, [], "offenes Zeitfenster muss die Kette leeren")
        # Gegenprobe: ohne Zeitfenster bleibt dieselbe Lage gesperrt.
        handeln.zeitfenster_offen = lambda: False
        g = handeln.live_sperren(self.w, _lage(self.w))
        self.assertTrue(any("Freigabefenster" in x for x in g))

    def test_live_grenze_bevorzugt(self):
        self.assertEqual(handeln._live_grenze(self.w, "max_pro_trade_usd", 9),
                         10.0)
        self.assertEqual(handeln._live_grenze(self.w, "max_offene_positionen",
                                              1), 5)
        self.assertEqual(handeln._live_grenze(self.w, "max_gesamt_usd", 1), 200)


class BildschirmFreigabeTest(_Basis):

    def test_hole_freigabe_erreicht_das_modul(self):
        """hole_freigabe scheiterte bis zum 21.09.2026 am eigenen Pfad.

        Dort stand str(HIER.parent); HIER ist in handeln.py ein String
        (os.path.dirname), also AttributeError - und zwar VOR dem try, sodass
        jede Bildschirm-Freigabe mit "Freigabefenster nicht verfuegbar"
        endete: kein Einstieg, ohne dass es auffiel. Geprueft wird der Weg bis
        zum Freigabe-Modul; das Fenster selbst ist ersetzt (kein Klick, keine
        Anzeige).
        """
        import freigabe
        gerufen = []

        def fake_bestaetige(vs, spur, bestand, zeitlimit=None):
            gerufen.append((spur, bestand, zeitlimit))
            return list(vs)

        alt = freigabe.bestaetige
        freigabe.bestaetige = fake_bestaetige
        try:
            v = [{"inst": "TEST-USDT", "einstieg": 105.0, "stop_pct": 5.0,
                  "stop": 99.75, "ziel": 115.5, "cr": 2.0, "usd": 10.0}]
            # Die ECHTE Funktion, nicht den Seam-Fake aus setUp: nur so wird
            # der Pfad bis zum Freigabe-Modul wirklich durchlaufen.
            echt = self._seams_alt[8]
            raus = echt(v, {"positionen": []}, _lage(self.w))
        finally:
            freigabe.bestaetige = alt
        self.assertEqual(raus, v, "bestätigter Auftrag kommt zurueck")
        self.assertEqual(gerufen[0][0], "mosaic")
        self.assertEqual(gerufen[0][2], handeln.FREIGABE_ZEITLIMIT_S,
                         "Zeitlimit geht mit (ohne Bedienung wird abgelehnt)")


class LiveEinstiegeTest(_Basis):

    def test_einstieg_kauft_bucht_stop(self):
        z = {"positionen": []}
        handeln.live_einstiege(z, self.w, _lage(self.w))
        self.assertEqual(len(z["positionen"]), 1)
        p = z["positionen"][0]
        self.assertEqual(p["modus"], "live")
        self.assertEqual(p["seite"], "long")
        self.assertEqual(p["inst"], "TEST-USDT")
        # Kauf + Stop wurden echt aufgerufen (Seams).
        self.assertIn(("kauf", "TEST-USDT", 0.12345), self.aufrufe)
        self.assertIn(("stop", "TEST-USDT", 0.11234, "long", p["stop"]),
                      self.aufrufe)

    def test_ohne_freigabe_kein_kauf(self):
        handeln.hole_freigabe = lambda vs, z, s: []  # abgelehnt
        z = {"positionen": []}
        handeln.live_einstiege(z, self.w, _lage(self.w))
        self.assertEqual(z["positionen"], [])
        self.assertNotIn(("kauf", "TEST-USDT", 0.12345), self.aufrufe)

    def test_einstieg_ueber_zeitfenster_ohne_bildschirm(self):
        """Kein Bildschirm + offenes Zeitfenster = Einstieg ohne Tk-Fenster.

        Geprueft wird der Weg, der im Dauerbetrieb laeuft: hole_freigabe darf
        dabei NICHT gerufen werden (es wuerde 600 s auf einen Klick warten und
        dann ablehnen), und der Einstieg muss im Protokoll stehen.
        """
        os.environ["MAXHIRN_ROUTINE"] = "1"     # hier sitzt niemand
        handeln.zeitfenster_offen = lambda: True

        def nie_gerufen(*a, **k):
            raise AssertionError("Freigabefenster am Bildschirm wurde gerufen")
        handeln.hole_freigabe = nie_gerufen

        protokoll = []
        import freigabe
        alt_audit = freigabe.audit
        freigabe.audit = protokoll.append
        try:
            z = {"positionen": []}
            handeln.live_einstiege(z, self.w, _lage(self.w))
        finally:
            freigabe.audit = alt_audit
        self.assertEqual(len(z["positionen"]), 1, "Einstieg erfolgt")
        self.assertEqual(z["positionen"][0]["modus"], "live")
        self.assertIn(("kauf", "TEST-USDT", 0.12345), self.aufrufe)
        self.assertTrue(protokoll, "Freigabe muss protokolliert sein")
        self.assertEqual(protokoll[0]["quelle"], "zeitfenster")
        self.assertEqual(protokoll[0]["spur"], "mosaic")

    def test_zeitfenster_zu_kein_kauf(self):
        os.environ["MAXHIRN_ROUTINE"] = "1"
        handeln.zeitfenster_offen = lambda: False
        handeln.hole_freigabe = lambda vs, z, s: []      # niemand bestaetigt
        z = {"positionen": []}
        handeln.live_einstiege(z, self.w, _lage(self.w))
        self.assertEqual(z["positionen"], [])

    def test_max_offene_respektiert(self):
        z = {"positionen": [
            {"inst": "OTHER-USDT", "modus": "live", "nominal": 100.0,
             "seite": "long", "einstieg": 100.0, "stop": 90.0, "ziel": 120.0}
            for _ in range(5)]}
        handeln.live_einstiege(z, self.w, _lage(self.w))
        # 5 belegt (live_max_offene_positionen=5) -> kein 6. Einstieg.
        self.assertEqual(len(z["positionen"]), 5)

    def test_stop_fehlt_fuehrt_zu_rueckverkauf(self):
        def stop_fehlt(inst, menge, seite, trigger):
            raise RuntimeError("algo kaputt")
        handeln.op_stop = stop_fehlt
        z = {"positionen": []}
        handeln.live_einstiege(z, self.w, _lage(self.w))
        # Kein Einstieg, zurueckverkauft.
        self.assertEqual(z["positionen"], [])
        self.assertIn(("verkauf", "TEST-USDT", 0.11234), self.aufrufe)


class LiveAusstiegeTest(_Basis):

    def _pos(self, kurs=104.0):
        return {"inst": "TEST-USDT", "seite": "long", "einstieg": 105.0,
                "stop": 100.0, "ziel": 110.0, "stop_pct": 5.0,
                "nominal": 10.0, "menge": 0.1, "modus": "live",
                "stop_algo_id": "ALGO1"}

    def test_zielausstieg_verkauft(self):
        handeln.live_kurs_quelle = lambda inst: 111.0  # ueber Ziel
        z = {"positionen": [self._pos()]}
        handeln.SCHREIBEN = True  # temp-Ziel ist sicher, Waechter prueft echtes
        handeln.live_ausstiege(z, self.w)
        self.assertEqual(z["positionen"], [])
        self.assertIn(("stop_stornieren", "TEST-USDT", "ALGO1"),
                      self.aufrufe)
        self.assertIn(("verkauf", "TEST-USDT", 0.1), self.aufrufe)
        with open(handeln.JOURNAL, encoding="utf-8") as f:
            zeilen = [l for l in f.read().splitlines() if l and "aktion" not in l]
        self.assertTrue(any("live" in l and "verkauf" in l and "ziel" in l
                            for l in zeilen))

    def test_papier_position_unberuehrt(self):
        handeln.live_kurs_quelle = lambda inst: 111.0
        pap = self._pos(); pap["modus"] = "papier"
        z = {"positionen": [pap]}
        handeln.live_ausstiege(z, self.w)
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(z["positionen"][0]["modus"], "papier")
        self.assertEqual(self.aufrufe, [])

    def test_verkauf_fehlt_haelt_position(self):
        def kaputt(inst, menge):
            raise RuntimeError("netz weg")
        handeln.live_kurs_quelle = lambda inst: 111.0
        handeln.op_verkauf = kaputt
        z = {"positionen": [self._pos()]}
        handeln.live_ausstiege(z, self.w)
        self.assertEqual(len(z["positionen"]), 1)


class FlachStellenTest(_Basis):

    def test_raeumt_nur_live(self):
        handeln.live_kurs_quelle = lambda inst: 103.0
        live = self._pos_live()
        pap = self._pos_live(); pap["modus"] = "papier"
        z = {"positionen": [live, pap]}
        handeln.flach_stellen_live(z, self.w, "test")
        self.assertEqual(len(z["positionen"]), 1)
        self.assertEqual(z["positionen"][0]["modus"], "papier")
        self.assertIn(("verkauf", "TEST-USDT", live["menge"]), self.aufrufe)

    def _pos_live(self):
        return {"inst": "TEST-USDT", "seite": "long", "einstieg": 105.0,
                "stop": 100.0, "ziel": 110.0, "stop_pct": 5.0,
                "nominal": 10.0, "menge": 0.1, "modus": "live",
                "stop_algo_id": "ALGO2"}


class BetragGedeckeltTest(unittest.TestCase):
    """Auftrag Max 23.09.2026 ("Mosaic 100"): live_max_pro_trade_usd 50 -> 100.

    Ein 100-EUR-Kauf bei 88,56 EUR frei waere eine von Kraken abgelehnte Order.
    Deshalb deckelt handeln.betrag_gedeckelt() den Einsatz VOR dem
    Freigabefenster auf das freie Guthaben minus Gebuehr und 0,2 % Luft.
    """

    def setUp(self):
        self.alt_guthaben = handeln.op_guthaben
        self.alt_waehrung = handeln.GUTHABEN_WAEHRUNG
        handeln.GUTHABEN_WAEHRUNG = "EUR"
        self.addCleanup(setattr, handeln, "op_guthaben", self.alt_guthaben)
        self.addCleanup(setattr, handeln, "GUTHABEN_WAEHRUNG", self.alt_waehrung)

    def test_deckelt_auf_das_freie_guthaben(self):
        handeln.op_guthaben = lambda ccy="EUR": 88.56
        betrag, hinweis = handeln.betrag_gedeckelt(100.0, {"gebuehr_taker": 0.006})
        self.assertLessEqual(betrag, 88.56)
        self.assertGreater(betrag, 87.0)
        self.assertIn("gedeckelt", hinweis)

    def test_kleiner_betrag_bleibt_unveraendert(self):
        handeln.op_guthaben = lambda ccy="EUR": 200.0
        betrag, hinweis = handeln.betrag_gedeckelt(50.0, {"gebuehr_taker": 0.006})
        self.assertEqual(betrag, 50.0)
        self.assertIsNone(hinweis)

    def test_unlesbares_guthaben_aendert_nichts(self):
        def kaputt(ccy="EUR"):
            raise RuntimeError("Netz weg")
        handeln.op_guthaben = kaputt
        betrag, hinweis = handeln.betrag_gedeckelt(100.0, {"gebuehr_taker": 0.006})
        self.assertEqual(betrag, 100.0)
        self.assertIn("nicht abrufbar", hinweis)

    def test_kein_guthaben_meldet_statt_zu_raten(self):
        handeln.op_guthaben = lambda ccy="EUR": 0.0
        betrag, hinweis = handeln.betrag_gedeckelt(100.0, {"gebuehr_taker": 0.006})
        self.assertEqual(betrag, 100.0)
        self.assertIn("kein freies", hinweis)

    def test_gebuehr_und_luft_sind_eingerechnet(self):
        handeln.op_guthaben = lambda ccy="EUR": 100.0
        betrag, _ = handeln.betrag_gedeckelt(100.0, {"gebuehr_taker": 0.01})
        self.assertAlmostEqual(betrag, 100.0 * (1 - 0.01 - 0.002), places=6)

    def test_der_deckel_steht_vor_der_order(self):
        """Ein Deckel nach dem Kauf waere kein Deckel."""
        with open(os.path.join(HIER, "handeln.py"), encoding="utf-8") as f:
            quelle = f.read()
        self.assertIn("betrag, deckel_hinweis = betrag_gedeckelt(betrag, w)",
                      quelle)
        self.assertLess(quelle.index("betrag_gedeckelt(betrag, w)"),
                        quelle.index("op_kauf(inst, menge)"),
                        "der Deckel muss VOR der Order stehen")


if __name__ == "__main__":
    unittest.main()