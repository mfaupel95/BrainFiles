"""Stufen-Kontrolle auf den BESTAND (PLAN §4.2, gebaut am 19.10.2026).

WAS HIER GEPRUEFT WIRD
Die Einstiegsseite war da (`risikovorfilter` + Platzzahl), der BESTAND war
ungedeckt: ein offenes Buch, das die Grenze der Stufe ueberzog, wurde nicht
angefasst. `spur_buch.pruefe_stufen` schliesst es jetzt ueber denselben Weg wie
der Drawdown-Kill (`kill_schliessen`) - mit EIGENEM Grund, damit im Journal
sichtbar bleibt, welcher Waechter geschlossen hat.

DIE REIHENFOLGE IST DER PUNKT
`pruefe_stufen` laeuft HINTER `pruefe_ausstiege`. Stop und Ziel sind die
teurere Wahrheit; ein Stufen-Kill davor wuerde "stufenueberschreitung" buchen,
wo die ehrliche Ursache "stop" heisst - genau die Verzerrung, die §4.1 abbaut.

WAS DIE PRUEFUNG LEISTET
`offenes_risiko` ist hoechstens `risiko_je_position x Plaetze` = Buchrisiko
(die Nominale ist risikonormiert). Ein Deckel AUF dem Buchrisiko kann also nie
reissen - er ist eine DRIFT-Bremse und feuert, wenn das Buch nicht mehr zur
Konfiguration passt. Gemessen ueber alle 56 Wachen-Dateien: 45 koennen nicht
feuern, 10 haben keine Ratsche, genau 1 (moondev_funding, 15 gegen 20) kann.
Damit der Kill wirklich bindet, muss die Grenze UNTER das Buchrisiko - das ist
eine Betreiber-Entscheidung, keine Code-Frage.

Alles gegen den echten `spur_buch.zyklus` in einem Temp-Verzeichnis, ohne Netz.
"""

import csv
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
for p in (os.path.join(HANDEL, "scanner"), HANDEL):
    if p not in sys.path:
        sys.path.insert(0, p)


def _lade(name, datei):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HANDEL, datei))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


sb = _lade("spur_buch_stufen", "spur_buch.py")
RATSCHEN = _lade("ratschen_stufen", "ratschen.py")
STOERUNGEN = _lade("stoerungen_stufen", "stoerungen.py")

KERZEN = [[0, 100, 101, 99, 100, 1.0]] * 100
INST, INST2, INST3 = "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"


def position(inst=INST, **kw):
    """Eine Position mit Risiko 5.00 USD (nominal 100 x stop_pct 5)."""
    p = {"inst": inst, "seite": "long", "einstieg": 100.0, "stop": 95.0,
         "ziel": 110.0, "stop_pct": 5.0, "nominal": 100.0, "modus": "papier",
         "pos_id": "s-" + inst[:3]}
    p.update(kw)
    return p


class Basis(unittest.TestCase):
    kurs = 100.0
    signal_seite = "long"

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="stufen-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with open(os.path.join(HANDEL, "klassik_ema", "wachen.json"),
                  encoding="utf-8") as f:
            self.w = json.load(f)
        # Der Drawdown-Kill wird stillgelegt - dieser Test handelt von der
        # Stufe, nicht von der Kapitalkurve. Ebenso der Vorfilter: die
        # Einstiegsseite der Stufe ist von ihm unabhaengig.
        self.w.update(journal_zweitziel=None, risikovorfilter=False,
                      handel_erlaubt=False, kill_switch_gesamt_usd=100000.0)
        # risiko_je_position_usd 5.0 x max_offene_positionen 3 -> Buchrisiko 15.00
        self.schreibe_wachen()
        self.jp = os.path.join(self.tmp, "handelsjournal.csv")
        self.zp = os.path.join(self.tmp, "zustand.json")
        sb.lege_journal_an(self.jp)

    def schreibe_wachen(self):
        with open(os.path.join(self.tmp, "wachen.json"), "w", encoding="utf-8") as f:
            json.dump(self.w, f)

    def zustand(self, **kw):
        z = {"positionen": [], "modus": "papier", "letzter_lauf": None,
             "verlust_usd": 0.0}
        z.update(kw)
        with open(self.zp, "w", encoding="utf-8") as f:
            json.dump(z, f)

    def zyklus(self, modus="papier", kurse=None, signal=None, mehrere=False):
        alle = (INST, INST2, INST3)
        if mehrere:
            daten = {i: {"kerzen": KERZEN} for i in alle}
        else:
            daten = {INST: {"kerzen": KERZEN}}
        # Kurse fuer ALLE Instrumente: ein Instrument ohne Kurs wird von
        # pruefe_ausstiege uebersprungen (kein Ausstieg, kein Stufen-Kill) -
        # genau die Falle, die diesen Test zuerst scheitern liess.
        if kurse is None:
            kurse = {i: self.kurs for i in alle}
        else:
            kurse = dict(kurse)
            for i in alle:
                kurse.setdefault(i, self.kurs)

        def quelle(w):
            return daten, dict(kurse), []

        sig = (lambda d, w: self.signal_seite) if signal is None else signal
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            sb.zyklus(self.tmp, quelle, sig, modus, "stufen-test")
        self.ausgabe = puffer.getvalue()
        with open(self.zp, encoding="utf-8") as f:
            return json.load(f)

    def zeilen(self):
        with open(self.jp, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def verkaeufe(self):
        return [r for r in self.zeilen() if r.get("aktion") == "verkauf"]

    def kaeufe(self):
        return [r for r in self.zeilen() if r.get("aktion") == "kauf"]


class OhneDriftTest(Basis):
    def test_volles_buch_auf_der_grenze_bleibt_stehen(self):
        # 3 x Risiko 5.00 = 15.00 = Buchrisiko: genau auf der Grenze, nicht darueber
        self.zustand(positionen=[position(INST), position(INST2), position(INST3)])
        z = self.zyklus()
        self.assertEqual(len(z["positionen"]), 3)
        self.assertNotIn("stufen_kill", z)
        self.assertEqual(self.verkaeufe(), [])
        self.assertNotIn("STUFEN-KILL", self.ausgabe)

    def test_leeres_buch_loest_nichts_aus(self):
        self.zustand()
        z = self.zyklus()
        self.assertNotIn("stufen_kill", z)


class DriftTest(Basis):
    """Das Buch passt nicht mehr zur Konfiguration - der Fall, fuer den die Pruefung da ist."""

    def test_gesenkte_platzzahl_schliesst_das_buch(self):
        self.w["max_offene_positionen"] = 2          # Buchrisiko 10.00, Buch traegt 15.00
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2), position(INST3)])
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(self.verkaeufe()), 3)
        for v in self.verkaeufe():
            self.assertEqual(v["grund"], sb.STUFEN_GRUND)
        self.assertIn("STUFEN-KILL", self.ausgabe)
        self.assertEqual(z["stufen_kill"]["quelle"], "buchrisiko")
        self.assertAlmostEqual(z["stufen_kill"]["grenze_usd"], 10.0)
        self.assertAlmostEqual(z["stufen_kill"]["offenes_risiko_usd"], 15.0)

    def test_gesenktes_risiko_je_position_schliesst_das_buch(self):
        self.w["risiko_je_position_usd"] = 2.0       # Buchrisiko 6.00
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2)])
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(self.verkaeufe()), 2)

    def test_position_ohne_stop_pct_zaehlt_mit(self):
        # Altbestand (gitter, kraken, omniquant, scanner: 14 von 139 offenen
        # Positionen am 19.10.2026): Risiko aus der STOP-LINIE, nicht 0.00.
        self.w["max_offene_positionen"] = 2
        self.schreibe_wachen()
        ohne = position(INST, stop_pct=None, stop=95.0)      # 100 -> 95 = 5 %
        self.zustand(positionen=[ohne, position(INST2), position(INST3)])
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertEqual(len(self.verkaeufe()), 3)


class GrenzeTest(Basis):
    def test_ausdrueckliche_grenze_gewinnt_und_wird_genannt(self):
        self.w["max_offenes_risiko_usd"] = 8.0
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2)])
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["stufen_kill"]["quelle"], "max_offenes_risiko_usd")

    def test_buchdeckel_des_vorfilters_ist_dieselbe_zahl(self):
        self.w["risiko_buchdeckel_usd"] = 8.0
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2)])
        z = self.zyklus()
        self.assertEqual(z["positionen"], [])
        self.assertEqual(z["stufen_kill"]["quelle"], "risiko_buchdeckel_usd")

    def test_ohne_herleitbare_grenze_wird_nicht_geschlossen(self):
        for k in ("risiko_je_position_usd", "max_offene_positionen",
                  "max_risiko_gesamt_usd"):
            self.w.pop(k, None)
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2)])
        z = self.zyklus(signal=lambda d, w: None)     # kein Einstieg: die Wache
        self.assertEqual(len(z["positionen"]), 2)     # hat keine Risikozahlen mehr
        self.assertNotIn("stufen_kill", z)

    def test_kaputte_grenze_wird_ignoriert(self):
        self.w["max_offenes_risiko_usd"] = "kaputt"
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2)])
        z = self.zyklus(signal=lambda d, w: None)
        self.assertNotIn("stufen_kill", z)             # faellt auf das Buchrisiko zurueck

    def test_max_gesamt_usd_ist_kein_risikodeckel(self):
        # 1050 ist ein Kapitaldeckel und liegt 70x ueber dem Buchrisiko - er darf
        # den Stufen-Kill nicht ausloesen (sonst waere die Pruefung an eine Zahl
        # gebunden, die nie binden kann).
        self.w["max_gesamt_usd"] = 1.0
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST)])
        z = self.zyklus(signal=lambda d, w: None)
        self.assertNotIn("stufen_kill", z)


class ReihenfolgeTest(Basis):
    def test_stop_hat_vorrang_vor_stufen_kill(self):
        # Buch ueber der Grenze UND ein gerissener Stop: die gerissene Position
        # traegt ihren ehrlichen Grund, der Rest den des Waechters.
        self.w["max_offene_positionen"] = 1
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST, stop=95.0),          # reisst bei 94
                                 position(INST2, stop=90.0),
                                 position(INST3, stop=90.0)])
        self.kurs = 94.0
        z = self.zyklus()
        gruende = sorted(v["grund"] for v in self.verkaeufe())
        self.assertEqual(gruende, ["stop",
                                   "stufenueberschreitung_zwangsschluss",
                                   "stufenueberschreitung_zwangsschluss"])
        self.assertEqual(z["positionen"], [])

    def test_ein_gerissener_stop_allein_loest_keinen_stufen_kill_aus(self):
        # Nach dem Stop ist das Buch wieder unter der Grenze: 2 x 5.00 = 10.00
        self.w["max_offene_positionen"] = 2
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST, stop=95.0),
                                 position(INST2, stop=90.0)])
        self.kurs = 94.0
        z = self.zyklus()
        self.assertEqual(len(self.verkaeufe()), 1)
        self.assertEqual(self.verkaeufe()[0]["grund"], "stop")
        self.assertNotIn("stufen_kill", z)

    def test_stufen_kill_bucht_zum_marktkurs(self):
        self.w["max_offene_positionen"] = 2
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2), position(INST3)])
        self.kurs = 98.0
        self.zyklus()
        self.assertAlmostEqual(float(self.verkaeufe()[0]["einsatz_usd"]), 98.0, places=2)

    def test_vorschau_aendert_nichts(self):
        self.w["max_offene_positionen"] = 2
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2), position(INST3)])
        vorher_z = open(self.zp, encoding="utf-8").read()
        vorher_j = open(self.jp, encoding="utf-8").read()
        self.zyklus(modus="vorschau")
        self.assertEqual(open(self.zp, encoding="utf-8").read(), vorher_z)
        self.assertEqual(open(self.jp, encoding="utf-8").read(), vorher_j)


class ZaehlungTest(Basis):
    def test_stufen_kill_ist_keine_handelsrunde(self):
        self.w["max_offene_positionen"] = 2
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2), position(INST3)])
        self.zyklus()
        for v in self.verkaeufe():
            self.assertTrue(STOERUNGEN.ist_stoerung(v["grund"]), v["grund"])
        runden = [{"grund": v["grund"]} for v in self.verkaeufe()]
        echt, stoer = STOERUNGEN.teile_runden(runden)
        self.assertEqual((len(echt), len(stoer)), (0, 3))

    def test_drawdown_kill_und_stufen_kill_sind_unterscheidbar(self):
        self.assertNotEqual(sb.STUFEN_GRUND, sb.KILL_GRUND)
        self.assertIn("zwangsschluss", sb.STUFEN_GRUND)


class PendelTest(Basis):
    """Die Einstiegsseite traegt dieselbe Zahl - sonst schliesst der Kill und
    der naechste Zyklus baut dasselbe Buch wieder auf."""

    def test_nach_stufen_kill_wird_im_selben_zyklus_nicht_neu_eroeffnet(self):
        self.w["max_offene_positionen"] = 2
        self.schreibe_wachen()
        self.zustand(positionen=[position(INST), position(INST2), position(INST3)])
        z = self.zyklus(mehrere=True)
        self.assertEqual(z["positionen"], [])
        self.assertEqual(self.kaeufe(), [])

    def test_einstieg_blockt_an_derselben_grenze(self):
        self.w["max_offenes_risiko_usd"] = 8.0        # eine Position (5.00) passt, zwei nicht
        self.schreibe_wachen()
        self.zustand()
        z1 = self.zyklus(mehrere=True)
        self.assertEqual(len(z1["positionen"]), 1)
        self.assertIn("STUFEN-GRENZE", self.ausgabe)
        z2 = self.zyklus(mehrere=True)
        self.assertEqual(len(z2["positionen"]), 1)     # kein Aufbauen, kein Pendeln
        self.assertNotIn("stufen_kill", z2)
        self.assertEqual(len(self.verkaeufe()), 0)

    def test_ohne_grenze_bleibt_die_platzzahl_bindend(self):
        self.zustand()
        z = self.zyklus(mehrere=True)
        self.assertEqual(len(z["positionen"]), 3)      # max_offene_positionen 3
        self.assertEqual(len(self.kaeufe()), 3)


class RechnungTest(unittest.TestCase):
    """Die eine Definition des offenen Buchrisikos (ratschen.offenes_risiko)."""

    def test_nominal_mal_stop(self):
        z = {"positionen": [position(), position()]}
        self.assertAlmostEqual(RATSCHEN.offenes_risiko(z), 10.0)

    def test_fehlendes_stop_pct_kommt_aus_der_linie(self):
        p = position(stop_pct=None, einstieg=100.0, stop=95.0)
        self.assertAlmostEqual(RATSCHEN.stop_prozent(p), 5.0)
        self.assertAlmostEqual(RATSCHEN.offenes_risiko({"positionen": [p]}), 5.0)

    def test_kaputte_werte_zaehlen_null_und_werfen_nicht(self):
        z = {"positionen": [{"nominal": "x"}, {"nominal": None}, {},
                            {"nominal": 100.0, "stop_pct": None,
                             "einstieg": None, "stop": None}]}
        self.assertEqual(RATSCHEN.offenes_risiko(z), 0.0)

    def test_buch_risiko_und_offenes_risiko_treffen_sich_am_vollen_buch(self):
        # Der Kern der Messung: ein volles Buch liegt GENAU auf dem Buchrisiko,
        # nie darueber - deshalb kann ein Deckel auf dem Buchrisiko nicht reissen.
        w = {"risiko_je_position_usd": 5.0, "max_offene_positionen": 3}
        z = {"positionen": [position(INST), position(INST2), position(INST3)]}
        self.assertAlmostEqual(RATSCHEN.offenes_risiko(z), RATSCHEN.buch_risiko(w))


class KeinSchreiberTest(unittest.TestCase):
    """Dieser Test darf die echte Spur nicht anfassen (Hauslektion 16.09.2026)."""

    def test_echte_klassik_ema_dateien_unveraendert(self):
        ordner = os.path.join(HANDEL, "klassik_ema")
        vorher = {n: os.path.getsize(os.path.join(ordner, n))
                  for n in sorted(os.listdir(ordner))
                  if os.path.isfile(os.path.join(ordner, n))}
        OhneDriftTest("test_leeres_buch_loest_nichts_aus").run()
        DriftTest("test_gesenkte_platzzahl_schliesst_das_buch").run()
        nachher = {n: os.path.getsize(os.path.join(ordner, n))
                   for n in sorted(os.listdir(ordner))
                   if os.path.isfile(os.path.join(ordner, n))}
        self.assertEqual(vorher, nachher)


if __name__ == "__main__":
    unittest.main()
