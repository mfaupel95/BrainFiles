"""Das Reconciliation-Werkzeug: die Regel, nicht ihr Ergebnis (T-356).

Der Test `test_eine_buchung.py` prueft die EIGENSCHAFT am echten Zyklus
(`spur_buch.buche()` als einzige Schreibstelle). Dieses Modul prueft die
zweite Haelfte der Abnahme: das Werkzeug, das den ALTSTAND aufloest.

Was hier geprueft wird - drei Dinge, alle als Regel:

  1. `befunde()` erkennt BEIDE Fehlerarten und entscheidet richtig, welche
     Seite fuehrt (Geist -> Zeile weg, Position bleibt; Doppelverkauf ->
     erste Zeile bleibt).
  2. Ein zweiter Lauf findet NICHTS mehr (Idempotenz). Ein Werkzeug, das
     beim zweiten Mal wieder anfaesst, ist kein Werkzeug.
  3. Die Gegenprobe: die Regel MUSS einen Befund finden. Ein Test gegen eine
     Regel, die immer "sauber" sagt, prueft nichts.

Gegenprobe auf dem echten Bestand: mit den Sicherungen von 20261005
(handelsjournal.bak-20261005.csv / zustand.bak-20261005.json, dem Stand VOR
der Reconciliation) meldet `befunde()` 2 Befunde, mit den echten Dateien 0.
Laeuft ohne Netz, ohne Schluessel, ohne den echten Spurenordner.
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

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)

_MOD = os.path.join(SPUR, "buch_reconcile.py")
_spec = importlib.util.spec_from_file_location("buch_reconcile", _MOD)
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)

KOPF = ["zeit", "modus", "aktion", "inst", "seite", "preis", "einsatz_usd",
        "stop", "ziel", "stop_pct", "grund", "pos_id", "mfe_pct", "mae_pct",
        "haltetage"]


def zeile(zeit, aktion, inst, pos_id, preis="1.0", grund="stop"):
    z = [""] * len(KOPF)
    z[0], z[1], z[2], z[3], z[4], z[5], z[10], z[11] = (
        zeit, "papier", aktion, inst, "long", preis, grund, pos_id)
    return z


class RegelTest(unittest.TestCase):
    """Die Regel auf nachgebauten Zeilen - der schnellste Weg zu beiden
    Fehlerarten, ohne Dateien und ohne Betriebsdaten."""

    def test_geist_journal_verschwindet_position_bleibt(self):
        daten = [zeile("2026-10-02T17:29:50+00:00", "kauf", "NIGHT", "p1"),
                 zeile("2026-10-05T00:26:36+00:00", "verkauf", "NIGHT", "p1")]
        offen = [{"inst": "NIGHT", "pos_id": "p1"}]
        befunde, ohne = br.befunde(daten, KOPF, offen)
        self.assertEqual(len(befunde), 1)
        b = befunde[0]
        self.assertEqual(b["art"], "geist")
        self.assertEqual(b["zeilen"], [1], "nur die Verkaufszeile, nicht der Kauf")
        self.assertIsNone(b["behalten"], "beim Geist fuehrt der Zustand")
        self.assertEqual(ohne, 0)

    def test_doppelverkauf_die_erste_zeile_bleibt(self):
        daten = [zeile("2026-10-02T01:12:19+00:00", "kauf", "AI", "p2"),
                 zeile("2026-10-02T03:03:05+00:00", "verkauf", "AI", "p2",
                       grund="ziel"),
                 zeile("2026-10-02T10:25:10+00:00", "verkauf", "AI", "p2")]
        b, _ = br.befunde(daten, KOPF, [])      # keine Position offen
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["art"], "doppelverkauf")
        self.assertEqual(b[0]["zeilen"], [2], "die spaetere Zeile ist zu verwerfen")
        self.assertEqual(b[0]["behalten"], 1, "die fruehere Ausstiegsnotiz fuehrt")

    def test_drei_verkaeufe_nur_der_erste_bleibt(self):
        daten = ([zeile("2026-10-02T01:12:19+00:00", "kauf", "AI", "p2")]
                 + [zeile("2026-10-02T%02d:00:10+00:00" % (3 + 5 * n),
                          "verkauf", "AI", "p2") for n in range(3)])
        b, _ = br.befunde(daten, KOPF, [])
        self.assertEqual([x["zeilen"][0] for x in b], [2, 3],
                         "nur die erste Verkaufszeile bleibt stehen")
        self.assertEqual({x["behalten"] for x in b}, {1})

    def test_ohne_pos_id_zaehlt_aber_repariert_nicht(self):
        daten = [zeile("2026-09-22T01:06:46+00:00", "verkauf", "BTW", ""),
                 zeile("2026-09-22T01:21:11+00:00", "verkauf", "BTW", "")]
        b, ohne = br.befunde(daten, KOPF, [])
        self.assertEqual(b, [], "eine Zeile ohne Kennung wird nie angefasst")
        self.assertEqual(ohne, 2, "aber sie wird gezaehlt und gemeldet")

    def test_kaufzeilen_tragen_nie_einen_befund(self):
        daten = [zeile("2026-10-03T09:11:02+00:00", "kauf", "AR", "p3")]
        b, ohne = br.befunde(daten, KOPF, [{"inst": "AR", "pos_id": "p3"}])
        self.assertEqual((b, ohne), ([], 0),
                         "eine offene Position ohne Verkauf ist in Ordnung")

    def test_pos_id_spalte_wird_über_kopf_gefunden(self):
        """Nicht die feste Spaltennummer, sondern die Kopfzeile gilt -
        der Altstand ohne `mfe_pct` verschiebt alle Spalten."""
        kopf = ["zeit", "modus", "aktion", "inst", "seite", "preis",
                "einsatz_usd", "stop", "ziel", "stop_pct", "grund", "pos_id"]
        daten = [["2026-09-30T15:29:56+00:00", "papier", "verkauf", "STX",
                  "long", "0.37", "71.43", "0.31", "0.37", "7.00", "ziel",
                  "20260930T152956-eefb20"]]
        b, _ = br.befunde(daten, kopf, [{"inst": "STX",
                                          "pos_id": "20260930T152956-eefb20"}])
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0]["art"], "geist")

    def test_regel_ist_nicht_blind(self):
        """Gegenprobe: dieselbe Regel gegen den Zustand vom 05.10. MUSS
        anschlagen - sonst prueft der Test nichts."""
        daten = [zeile("2026-10-05T00:26:36+00:00", "verkauf", "NIGHT", "p1")]
        sauber, _ = br.befunde(daten, KOPF, [])            # verkauft, zu
        schmutz, _ = br.befunde(daten, KOPF,
                                 [{"inst": "NIGHT", "pos_id": "p1"}])
        self.assertEqual(sauber, [])
        self.assertEqual([b["art"] for b in schmutz], ["geist"])


class WerkzeugTest(unittest.TestCase):
    """Das Schreiben selbst: Sicherung, verworfene Zeilen, Idempotenz."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="reconcile_")
        self.alt = self.tmp.name
        # Das Werkzeug schreibt ueber `HIER`; die Pfade biegen wir auf den
        # Tempordner. `lauf()` liest wachen.json nur fuer das Spiegelziel,
        # das ohne wachen.json None bleibt - also wird nicht gespiegelt.
        self.orig_hier = br.HIER
        br.HIER = self.alt
        self._schreibe("handelsjournal.csv", [KOPF,
            zeile("2026-10-02T01:12:19+00:00", "kauf", "AI", "p2"),
            zeile("2026-10-02T03:03:05+00:00", "verkauf", "AI", "p2"),
            zeile("2026-10-02T10:25:10+00:00", "verkauf", "AI", "p2")])
        self._schreibe("zustand.json", {"positionen": [], "letzter_lauf":
                                        "2026-10-05T01:15:17+00:00"})
        # Wachen OHNE journal_zweitziel: das Werkzeug spiegelt dann nicht und
        # ein Test fasst das echte Q: nicht an.
        self._schreibe("wachen.json", {"handel_erlaubt": True})

    def tearDown(self):
        br.HIER = self.orig_hier
        self.tmp.cleanup()

    def _schreibe(self, name, inhalt):
        p = os.path.join(self.alt, name)
        with open(p, "w", encoding="utf-8", newline="") as f:
            if name.endswith(".json"):
                json.dump(inhalt, f, ensure_ascii=False, indent=2)
            else:
                csv.writer(f).writerows(inhalt)

    def _zeilen(self, name):
        with open(os.path.join(self.alt, name), encoding="utf-8",
                  newline="") as f:
            return list(csv.reader(f))

    def test_vorschau_schreibt_nichts(self):
        self.assertEqual(br.lauf("basis"), 0)
        self.assertEqual(len(self._zeilen("handelsjournal.csv")), 4,
                         "Vorschau: Journal unveraendert")
        self.assertFalse([n for n in os.listdir(self.alt)
                          if n.startswith("handelsjournal.bak-")],
                         "Vorschau: keine Sicherung angelegt")

    def test_anwenden_verschiebt_und_bleibt_idempotent(self):
        rc = br.lauf("basis", anwenden=True)
        self.assertEqual(rc, 0, "nach dem Schreiben 0 Befunde")
        j = self._zeilen("handelsjournal.csv")
        self.assertEqual(len(j), 3, "Kopf + Kauf + EINE Verkaufszeile")
        self.assertEqual(j[2][3], "AI")
        verworfen = [n for n in os.listdir(self.alt)
                     if n.startswith("handelsjournal.verworfen-")]
        self.assertEqual(len(verworfen), 1)
        v = self._zeilen(verworfen[0])
        self.assertEqual(v[0], KOPF, "die verworfene Datei traegt die Kopfzeile")
        self.assertEqual(v[1][10], "stop", "die spaetere Zeile ist verworfen")
        # Sicherungen: Journal UND Zustand, beide mit Stempel
        for muster in ("handelsjournal.bak-", "zustand.bak-"):
            self.assertTrue([n for n in os.listdir(self.alt)
                             if n.startswith(muster)], muster)
        # Idempotenz: der zweite Lauf fasst nichts mehr an
        self.assertEqual(br.lauf("basis", anwenden=True), 0)
        self.assertEqual(len(self._zeilen("handelsjournal.csv")), 3)

    def test_letzter_lauf_bleibt_unberuehrt(self):
        br.lauf("basis", anwenden=True)
        with open(os.path.join(self.alt, "zustand.json"),
                  encoding="utf-8") as f:
            z = json.load(f)
        self.assertEqual(z["letzter_lauf"], "2026-10-05T01:15:17+00:00",
                         "ein Werkzeug ist kein Zyklus und darf den "
                         "Herzschlag nicht verjuengen")

    def test_crlf_und_ohne_bom(self):
        br.lauf("basis", anwenden=True)
        with open(os.path.join(self.alt, "handelsjournal.csv"), "rb") as f:
            b = f.read()
        self.assertNotIn(b"\xef\xbb\xbf", b, "kein BOM")
        self.assertEqual(b.count(b"\r\n"), b.count(b"\n"),
                         "CRLF durchgehend, wie spur_buch.journal() schreibt")

    def test_ohne_datei_ist_es_ein_freundlicher_nichttun(self):
        os.remove(os.path.join(self.alt, "zustand.json"))
        self.assertEqual(br.lauf("basis"), 0)


class EchterBestandTest(unittest.TestCase):
    """Das echte Buch von moondev_signalwelle - NUR LESEND.

    Der Abnahmetest: nach der Reconciliation gilt die Regel auf den echten
    Dateien. `test_eine_buchung.BestandTest` sagt dasselbe ueber das
    Journal/Zustand-Paar; dieser Test sagt es ueber das Werkzeug, das die
    Aufloesung gemacht hat - und er vergleicht mit den Sicherungen von
    20261005, damit ein "gruen" nicht durch Wegschreiben entstehen kann.
    """

    def test_echtes_buch_ist_sauber(self):
        jp, zp = br.pfade("basis")
        kopf, daten = br.lies(jp)
        with open(zp, encoding="utf-8") as f:
            z = json.load(f)
        befunde, ohne = br.befunde(daten, kopf, z.get("positionen"))
        self.assertEqual(
            [b["art"] for b in befunde], [],
            "im echten Buch steht eine Aussage je Ausstieg - gefunden: %s"
            % [(b["art"], b["pos_id"]) for b in befunde])
        self.assertGreater(ohne, 0,
                           "die Regel muss blind sein koennen, sonst prueft "
                           "sie nichts: ohne pos_id gibt es im Altjournal "
                           "Zeilen, die sie NICHT meldet")

    def test_die_sicherung_zeigt_die_zwei_befunde(self):
        """Gegenprobe auf dem echten Material: der Stand VOR der
        Reconciliation (die .bak-20261005-Dateien) MUSS zwei Befunde
        tragen. Sonst waere der gruene Test oben eine Aussage ueber nichts.
        """
        js, zs = "handelsjournal.bak-20261005.csv", "zustand.bak-20261005.json"
        jp, zp = os.path.join(SPUR, js), os.path.join(SPUR, zs)
        if not (os.path.exists(jp) and os.path.exists(zp)):
            self.skipTest("Sicherung 20261005 nicht mehr da (Karte schon "
                          "abgeschlossen und Sicherungen entfernt)")
        kopf, daten = br.lies(jp)
        with open(zp, encoding="utf-8") as f:
            z = json.load(f)
        befunde, _ = br.befunde(daten, kopf, z.get("positionen"))
        self.assertEqual(sorted((b["art"], b["inst"]) for b in befunde),
                         [("doppelverkauf", "AI"), ("geist", "NIGHT")],
                         "die Sicherung traegt genau die zwei Befunde vom "
                         "05.10.2026")

    def test_die_verworfenen_zeilen_sind_nicht_verloren(self):
        v = [n for n in os.listdir(SPUR)
             if n.startswith("handelsjournal.verworfen-")]
        self.assertTrue(v, "die verworfenen Zeilen liegen als Datei daneben")
        with open(os.path.join(SPUR, sorted(v)[-1]), encoding="utf-8",
                  newline="") as f:
            zeilen = list(csv.reader(f))
        self.assertEqual(zeilen[0], KOPF)
        self.assertEqual(len(zeilen), 3, "Kopf + die zwei verworfenen Zeilen")
        for z in zeilen[1:]:
            self.assertEqual(z[2], "verkauf")
            self.assertIn(z[11].strip(), ("20261002T011219-969294",
                                          "20261002T172950-b356a4"))


if __name__ == "__main__":
    unittest.main(verbosity=2)