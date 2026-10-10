"""T-351: signal-executor raeumt Queues von nicht-live Spuren ab.

ANLASS (07.10.2026)
-------------------
Eine Spur, die von live auf papier zurueckgeschaltet wird, legt weiter
Eintraege in die Queue, die niemand abholt. Sie sammeln sich bis zum
30-Minuten-Verfall. Der Executor leert die Queue sofort, wenn die Spur
nicht live ist (handel_erlaubt=false ODER freigabe nicht erfuellt).

DIE REGELN
----------
1. handel_erlaubt=false -> Queue wird geleert, Meldung "Queue abgeraeumt"
2. freigabe nicht erfuellt -> Queue wird geleert, Meldung "Queue abgeraeumt"
3. handel_erlaubt=true + freigabe erfuellt -> Queue bleibt, normaler Ablauf
4. Die Meldung "Queue abgeraeumt" darf die Spur nicht dauerhaft merken -
   die Wiederholungssperre gilt hier nicht (ein Wechsel ist ein Ereignis).
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "signal-executor.py")


def lade():
    spec = importlib.util.spec_from_file_location("sigexec_queue_test", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    sys.modules["sigexec_queue_test"] = m
    spec.loader.exec_module(m)
    return m


class QueueRaeumenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.m = lade()
        self.m.MERK_ECHT = self.m.MERK
        self.m.MERK = os.path.join(self.tmp, "merk.json")
        self.ordner_papier = os.path.join(self.tmp, "spur_papier")
        self.ordner_live = os.path.join(self.tmp, "spur_live")
        os.makedirs(self.ordner_papier)
        os.makedirs(self.ordner_live)
        # Wachen anlegen: papier (handel_erlaubt=false) und live (true+freigabe)
        with open(os.path.join(self.ordner_papier, "wachen.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"handel_erlaubt": False,
                       "freigabe": {"erfuellt": False}}, fh)
        with open(os.path.join(self.ordner_live, "wachen.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"handel_erlaubt": True,
                       "freigabe": {"erfuellt": True}}, fh)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _patch_wachen(self, spur, pfad):
        """HANDEL der Spur auf den Temp-Ordner zeigen lassen."""
        def _wachen(spur_name):
            if spur_name == "spur_papier":
                return os.path.join(self.ordner_papier, "wachen.json")
            if spur_name == "spur_live":
                return os.path.join(self.ordner_live, "wachen.json")
            return os.path.join(HANDEL_ECHT, spur_name, "wachen.json")
        return _wachen

    def test_handel_erlaubt_false_leert_queue(self):
        """handel_erlaubt=false -> kein Orderweg, Queue wird geleert."""
        # Pfad des Handels-Ordners umbiegen, damit ausfuehren() die Temp-Wachen
        # findet und die ECHTE spur_buch.py NICHT geladen wird (keine Order).
        # Wir testen die Bedingung, nicht den Orderweg: die Funktion muss
        # zurueckkehren, BEVOR sie den Orderweg importiert.
        HANDEL_ECHT = self.m.HANDEL
        self.m.HANDEL = os.path.join(self.tmp, "handel")
        os.makedirs(self.m.HANDEL)
        spur = "spur_papier"
        # Wachen sporadisch: fuer den Test muss wachen.json lesbar sein.
        # Wir legen die Temp-Wachen an der Stelle ab, wo ausfuehren() sie
        # sucht: HANDEL/<spur>/wachen.json
        ordner_spur = os.path.join(self.m.HANDEL, spur)
        os.makedirs(ordner_spur)
        shutil.copy(os.path.join(self.ordner_papier, "wachen.json"),
                    os.path.join(ordner_spur, "wachen.json"))
        ok, meldung = self.m.ausfuehren(spur, ["BTC-USDT", "long", 100.0])
        self.assertFalse(ok, "nicht-live Spur darf nicht ausfuehren")
        self.assertIn("Queue abgeraeumt", meldung)

    def test_freigabe_nicht_erteilt_leert_queue(self):
        """freigabe=false -> kein Orderweg, Queue wird geleert."""
        HANDEL_ECHT = self.m.HANDEL
        self.m.HANDEL = os.path.join(self.tmp, "handel2")
        os.makedirs(self.m.HANDEL)
        spur = "spur_live"  # handel_erlaubt=true, aber freigabe=false
        ordner_spur = os.path.join(self.m.HANDEL, spur)
        os.makedirs(ordner_spur)
        # freigabe=false setzen
        with open(os.path.join(self.ordner_live, "wachen.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"handel_erlaubt": True,
                       "freigabe": {"erfuellt": False}}, fh)
        shutil.copy(os.path.join(self.ordner_live, "wachen.json"),
                    os.path.join(ordner_spur, "wachen.json"))
        ok, meldung = self.m.ausfuehren(spur, ["BTC-USDT", "long", 100.0])
        self.assertFalse(ok)
        self.assertIn("Queue abgeraeumt", meldung)

    def test_queue_abgeraeumt_ist_ein_ereignis(self):
        """'Queue abgeraeumt' wird IMMER gemeldet, auch unveraendert.

        Das ist die Gegenprobe zur Wiederholungssperre: ein Wechsel auf
        papier ist ein Ereignis (wie eine Order), kein Zustand, der taeglich
        wiederholt werden muss.
        """
        zeilen = {"spur": "spur: handel_erlaubt=false, Queue abgeraeumt"}
        r1 = self.m.melde_neu(dict(zeilen), 1000.0)
        r2 = self.m.melde_neu(dict(zeilen), 1001.0)
        self.assertEqual(len(r1), 1)
        self.assertEqual(len(r2), 1,
                         "ein Queue-Aufraeumen ist ein Ereignis wie eine Order")


if __name__ == "__main__":
    unittest.main()
