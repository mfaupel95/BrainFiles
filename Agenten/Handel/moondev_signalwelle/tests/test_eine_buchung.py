"""EINE Buchung je Ausstieg - die Eigenschaft, nicht ein Zustandsstand (T-356).

BEFUND 05.10.2026: `moondev_signalwelle` hatte eine Position doppelt im Buch.
Das Journal verkauft sie (`grund=stop`), der Zustand fuehrt sie weiter offen -
jeder Zyklus verkauft sie erneut. Zwei Stellen im Hausbuch trugen das:

  * `pruefe_ausstiege()` schrieb die Verkaufszeile sofort ins Journal,
  * der `--vorschau`-Zweig von `zyklus()` kehrte davor zurueck, ohne
    `schreibe_zustand()` aufzurufen.

Seit Commit ee3ff9be ist `spur_buch.buche()` die EINZIGE Schreibstelle: eine
Buchung sind Journalzeile UND Zustand in einem Aufruf, es gibt keinen
Rueckkehrpunkt dazwischen, und die Vorschau steht vor jeder Buchung.

DIE EIGENSCHAFT (was hier geprueft wird, nicht ein Dateistand):

  Ein Ausstieg erzeugt GENAU EINE Aussage ueber die Position - entweder
  Verkauf im Journal und die Position ist weg aus dem Zustand, oder
  gar nichts. Ein zweiter Zyklus mit demselben Kurs darf sie nicht noch
  einmal verkaufen.

  Als Datenregel auf dem echten Buch: je `pos_id` hoechstens EINE
  Verkaufszeile, und eine im Zustand offene Position darf keine
  Verkaufszeile tragen. Das liest die IST-Dateien, ohne sie zu aendern -
  die Reconciliation ist Handarbeit und gehoert nicht in einen Test.

Alle Buchungen laufen gegen einen Tempordner. `BestandTest` liest die
echten Dateien nur - der Modulwaechter (setUpModule/tearDownModule) belegt,
dass kein Test in den echten Spurenordner geschrieben hat.
"""

import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest

HIER = os.path.dirname(os.path.abspath(__file__))
SPUR = os.path.dirname(HIER)
HANDEL = os.path.dirname(SPUR)
# Die eigene Spur ZULETZT: ein spaeter eingefuegter Eintrag steht vorn und
# koennte ein gleichnamiges Modul aus `scanner/` oder `Handel/` verdecken
# (dieselbe Falle wie in xperp und trendwende_btc).
for p in (os.path.join(HANDEL, "scanner"), HANDEL, SPUR):
    if p not in sys.path:
        sys.path.insert(0, p)

import handeln as h           # noqa: E402
import spur_buch as buch      # noqa: E402
import ereignis               # noqa: E402

assert h.__file__.startswith(SPUR), "falsches handeln.py: %s" % h.__file__
assert buch.__file__.startswith(HANDEL), "falsches spur_buch.py: %s" % buch.__file__

ECHTE_ZUSTAND = os.path.join(SPUR, "zustand.json")
ECHTE_JOURNAL = os.path.join(SPUR, "handelsjournal.csv")

# Die echten Wachen als Vorlage, damit der Test dieselben Grenzen fahren
# muss wie der Betrieb (Pflicht-Stopp, R-Vielfaches, Kill, Ratsche).
_WACHEN_VORLAGE = json.load(open(os.path.join(SPUR, "wachen.json"),
                                encoding="utf-8"))


def wachen_fuer(zweitziel):
    """Echte Wachen, aber ohne Boerse und mit dem Spiegelziel im Tempordner.

    `boerse` weggelassen heisst: `spur_buch.orderweg()` gibt None zurueck
    und der Test laedt keinen Orderweg. Ein Test darf keinen Schluessel
    anfassen und keine Boerse erreichen.
    """
    w = dict(_WACHEN_VORLAGE)
    w.pop("boerse", None)
    w.pop("freigabe", None)
    w["journal_zweitziel"] = zweitziel
    w["grund"] = "test_eine_buchung"
    return w


def doppelbuchungen(journal_pfad, zustand_pfad):
    """Die Datenregel als reine Funktion: [(art, pos_id, inst, anzahl)].

    Zwei Fehlerarten, beide derselbe Fehler (eine Position, zwei Aussagen):

      doppelverkauf - dieselbe `pos_id` traegt mehr als eine Verkaufszeile
                      (die Position wurde zweimal beendet)
      geist         - eine `pos_id` hat eine Verkaufszeile UND steht im
                      Zustand weiter offen (Journal verkauft, Buch nicht)

    Zeilen OHNE `pos_id` (der Altstand vor T-095) lassen sich nicht zuordnen
    und werden gezaehlt, aber nie als Fehler gemeldet - sonst waere der
    Bestand seit dem 20.09. dauerhaft rot.
    """
    verkaeufe = {}
    ohne_kennung = 0
    if os.path.exists(journal_pfad):
        with open(journal_pfad, encoding="utf-8", newline="") as f:
            for z in csv.DictReader(f):
                if (z.get("aktion") or "") != "verkauf":
                    continue
                pid = (z.get("pos_id") or "").strip()
                if not pid:
                    ohne_kennung += 1
                    continue
                verkaeufe.setdefault(pid, []).append(z)
    offen = {}
    if os.path.exists(zustand_pfad):
        with open(zustand_pfad, encoding="utf-8") as f:
            for p in (json.load(f).get("positionen") or []):
                pid = (p.get("pos_id") or "").strip()
                if pid:
                    offen[pid] = p
    befunde = []
    for pid, zs in sorted(verkaeufe.items()):
        if len(zs) > 1:
            befunde.append(("doppelverkauf", pid, zs[0].get("inst"), len(zs)))
        if pid in offen:
            befunde.append(("geist", pid, offen[pid].get("inst"),
                            len(zs)))
    return befunde, ohne_kennung


# --- Der Test darf nie in den echten Spurenordner schreiben ---------------

def _bestand(ordner):
    aus = {}
    for n in sorted(os.listdir(ordner)):
        p = os.path.join(ordner, n)
        if os.path.isfile(p) and not n.endswith(".pyc"):
            aus[n] = os.path.getmtime(p), os.path.getsize(p)
    return aus


_ECHTE_VORHER = None


def setUpModule():
    global _ECHTE_VORHER
    _ECHTE_VORHER = _bestand(SPUR)
    os.environ.pop("HANDEL_RISIKO", None)   # die Basis, unabhaengig vom Takt


def tearDownModule():
    nachher = _bestand(SPUR)
    assert nachher == _ECHTE_VORHER, (
        "Ein Test hat in den echten Spurenordner geschrieben! vorher=%s "
        "nachher=%s" % (_ECHTE_VORHER, nachher))


class AusstiegTest(unittest.TestCase):
    """Die Eigenschaft am ECHTEN Zyklus, mit den Wachen der Spur."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="eine_buchung_")
        self.ordner = os.path.join(self.tmp.name, "probespur")
        os.makedirs(self.ordner)
        self.zweitziel = os.path.join(self.tmp.name, "spiegel")
        self._json("wachen.json", wachen_fuer(self.zweitziel))
        self._json("zustand.json", {"positionen": [self._position("NIGHT")],
                                    "letzter_lauf": None})
        # Kein echter Bus, kein echter Journal-Eintrag aus dem Testlauf.
        self._alt_lauf = ereignis.lauf
        ereignis.lauf = lambda *a, **k: contextlib.nullcontext()
        self._alt_schreiben = buch.SCHREIBEN
        buch.SCHREIBEN = True
        # Nur der Exit soll rechnen: signal() liefert nie eine Richtung,
        # sonst bucht der Zyklus nach dem Ausstieg sofort wieder ein.
        self._alt_signal = h.signal
        h.signal = lambda d, w: None
        self._alt_override = h.quelle_override

    def tearDown(self):
        ereignis.lauf = self._alt_lauf
        buch.SCHREIBEN = self._alt_schreiben
        h.signal = self._alt_signal
        h.quelle_override = self._alt_override
        self.tmp.cleanup()

    # -- Hilfen ----------------------------------------------------------

    @staticmethod
    def _position(inst="NIGHT", pos_id="20261002T172950-b356a4"):
        """Die NIGHT-Position aus dem Befund vom 05.10.2026, unveraendert."""
        return {"inst": inst, "seite": "long", "einstieg": 0.04799818,
                "stop": 0.0446383074, "ziel": 0.0530379889, "stop_pct": 7.0,
                "nominal": 71.42857142857142, "modus": "papier",
                "pos_id": pos_id, "eroeffnet_zeit": "2026-10-02T17:29:50+00:00"}

    def _json(self, name, inhalt):
        with open(os.path.join(self.ordner, name), "w", encoding="utf-8") as f:
            json.dump(inhalt, f)

    @property
    def _journal(self):
        return os.path.join(self.ordner, "handelsjournal.csv")

    def _zustand(self):
        with open(os.path.join(self.ordner, "zustand.json"),
                  encoding="utf-8") as f:
            return json.load(f)

    def _zeilen(self):
        if not os.path.exists(self._journal):
            return []
        with open(self._journal, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def _verkaeufe(self):
        return [z for z in self._zeilen() if z["aktion"] == "verkauf"]

    def _lauf(self, modus="papier", kurs=0.04441202):
        h.quelle_override = lambda w: ({"NIGHT": {"aenderung_1h": 5.0,
                                                  "volumen_24h": 5e7}},
                                      {"NIGHT": kurs}, [])
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = buch.zyklus(self.ordner, h.daten_holen, h.signal, modus,
                             "handel/probespur")
        self.assertEqual(rc, 0)
        return puffer.getvalue()

    # -- Die Eigenschaft ------------------------------------------------

    def test_ausstieg_bucht_einmal_und_nur_einmal(self):
        """Der Kern: EIN Ausstieg = EINE Buchung, und der naechste Zyklus
        verkauft nicht noch einmal.

        Vor dem Fix (ee3ff9be^) schrieb `pruefe_ausstiege()` die Zeile sofort,
        der Zustand blieb bis zum Zyklusende unberuehrt - dieser Test war
        dann genau der Geist, den NIGHT am 05.10. ueber Tage behielt.
        """
        self._lauf()
        v = self._verkaeufe()
        self.assertEqual(len(v), 1, "genau eine Verkaufszeile")
        self.assertEqual(v[0]["inst"], "NIGHT")
        self.assertEqual(v[0]["grund"], "stop")
        self.assertEqual(v[0]["pos_id"], "20261002T172950-b356a4",
                         "die Zeile traegt die Kennung der Position")
        self.assertEqual(self._zustand()["positionen"], [],
                         "die Position ist aus dem Zustand verschwunden")
        # Der Zweite Zyklus mit demselben Stop-Kurs: keine Position mehr,
        # also auch keine zweite Zeile.
        self._lauf()
        self.assertEqual(len(self._verkaeufe()), 1,
                         "der zweite Zyklus hat die Position nicht noch "
                         "einmal verkauft")
        befunde, _ = doppelbuchungen(self._journal,
                                     os.path.join(self.ordner, "zustand.json"))
        self.assertEqual(befunde, [],
                         "die Regel 'eine Buchung je Ausstieg' haelt")

    def test_doppelbuchung_ist_die_gegenprobe(self):
        """Gegenprobe: die Regel MUSS einen doppelt gebuchten Zustand finden.

        Ein Test gegen eine Regel, die immer 'sauber' sagt, prueft nichts.
        Der Attrappen-Zustand entspricht dem Befund vom 05.10. (Journal hat
        den Verkauf, der Zustand die Position) - hier MUSS ein Befund
        herauskommen.
        """
        z = self._zustand()
        with open(self._journal, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=buch.SPALTEN)
            w.writeheader()
            w.writerow({"zeit": "2026-10-05T00:26:36+00:00", "modus": "papier",
                        "aktion": "verkauf", "inst": "NIGHT", "seite": "long",
                        "preis": "0.04441202", "grund": "stop",
                        "pos_id": "20261002T172950-b356a4"})
        befunde, ohne = doppelbuchungen(self._journal,
                                         os.path.join(self.ordner, "zustand.json"))
        self.assertEqual([b[0] for b in befunde], ["geist"],
                         "der Zustand 'Journal verkauft, Buch offen' wird "
                         "als Geist erkannt (gefunden: %s)" % befunde)
        self.assertEqual(befunde[0][1], "20261002T172950-b356a4")
        self.assertEqual(ohne, 0)

    def test_vorschau_bucht_gar_nichts(self):
        """Die Vorschau rechnet und schreibt nichts - auch keinen Ausstieg.

        `dauerlauf.nur_fenster_fehlt()` ruft sie je Takt fuer die
        Sperrenzeile auf; am 05.10. hat genau dieser Aufruf die NIGHT-Zeile
        geschrieben.
        """
        self._lauf(modus="vorschau")
        self.assertEqual(self._zeilen(), [],
                         "die Vorschau hat keine Journalzeile geschrieben")
        z = self._zustand()
        self.assertEqual([p["inst"] for p in z["positionen"]], ["NIGHT"],
                         "die Position steht weiter im Zustand")
        self.assertIsNone(z.get("letzter_lauf"),
                          "auch der Zustand blieb unberuehrt")

    def test_vorschau_beendet_keinen_kill_stand(self):
        """Auch das Flachlegen des Buchs ist eine Buchung - die Vorschau
        darf es nicht tun."""
        # Ruecklauf ueber der Kill-Schwelle (45.0 USD) setzen: dazu eine
        # geschlossene Runde mit Verlust im Journal.
        with open(self._journal, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=buch.SPALTEN)
            w.writeheader()
            w.writerow({"zeit": "2026-10-04T00:00:00+00:00", "modus": "papier",
                        "aktion": "verkauf", "inst": "ALT", "seite": "long",
                        "preis": "1.0", "einsatz_usd": "1.00",
                        "grund": "stop", "pos_id": "alt-1"})
        z = self._zustand()
        z["verlust_usd"] = 60.0
        self._json("zustand.json", z)
        self._lauf(modus="vorschau")
        self.assertEqual([p["inst"] for p in self._zustand()["positionen"]],
                         ["NIGHT"],
                         "die Vorschau hat das Buch nicht flachgelegt")

    def test_papier_und_zustand_sagen_dasselbe(self):
        """Ein Zyklus ohne Ausstieg: Journal und Zustand bleiben zusammen -
        die Position steht in beiden nicht doppelt."""
        self._lauf(kurs=0.048)
        self.assertEqual(self._verkaeufe(), [], "kein Ausstieg, keine Zeile")
        self.assertEqual([p["inst"] for p in self._zustand()["positionen"]],
                         ["NIGHT"])
        befunde, _ = doppelbuchungen(self._journal,
                                     os.path.join(self.ordner, "zustand.json"))
        self.assertEqual(befunde, [])


class BestandTest(unittest.TestCase):
    """Das ECHTE Buch von moondev_signalwelle - nur lesend.

    Dieser Test ist die Abnahme der Datenreconciliation: nach dem Fix muss
    die Regel auf den echten Dateien gelten. Er schreibt nie.
    """

    def test_echtes_buch_hat_eine_buchung_je_ausstieg(self):
        befunde, ohne_kennung = doppelbuchungen(ECHTE_JOURNAL, ECHTE_ZUSTAND)
        if befunde:
            self.fail(
                "Doppelbuchung im echten Buch von moondev_signalwelle:\n"
                + "\n".join("  %s pos_id=%s inst=%s (%d Verkaufszeile(n))"
                            % b for b in befunde)
                + "\nJe Ausstieg gehoert genau eine Buchung: der Verkauf bleibt "
                  "im Journal und die Position wandert aus dem Zustand - "
                  "oder die Journalzeile wandert nach "
                  "handelsjournal.verworfen-JJJJMMTT.csv. "
                  "Nicht tun: die Positionszeile im Zustand loeschen "
                  "(Taschenregel der Karte t_0f4fa35d).\n"
                  "Altstand ohne pos_id (nicht zuordenbar, kein Befund): %d"
                  % ohne_kennung)
        # Die Regel darf auch hier nicht blind sein: der Bestand traegt
        # Verkaufzeilen, es muss also etwas zu sehen geben.
        with open(ECHTE_JOURNAL, encoding="utf-8", newline="") as f:
            zeilen = list(csv.DictReader(f))
        self.assertGreater(len(zeilen), 0, "das Journal ist nicht leer")
        self.assertTrue(any(z["aktion"] == "verkauf" for z in zeilen))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Lesender Einmalcheck fuer die Reconciliation, ohne unittest:
        #   python test_eine_buchung.py --pruefe
        b, ohne = doppelbuchungen(ECHTE_JOURNAL, ECHTE_ZUSTAND)
        for x in b:
            print("%s pos_id=%s inst=%s (%d Verkaufszeile(n))" % x)
        print("%d Befund(e), %d Verkaufszeile(n) ohne pos_id" % (len(b), ohne))
        raise SystemExit(1 if b else 0)
    unittest.main(verbosity=2)
