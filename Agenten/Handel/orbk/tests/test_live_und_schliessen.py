"""orbk: --live faellt bei geschlossenen Sperren auf Papier zurueck, und ein
Ausstieg darf nicht abstuerzen.

Zwei Regressionen aus dem 13.09.2026, plus der Live-Umbau:

1. `_schliesse()` scheiterte an `p["tag"].isoformat()`, weil `zustand.json`
   alles zu Strings serialisiert - die Position liess sich nie schliessen,
   jeder Papierlauf endete mit Rueckgabe 1.
2. `--live` war dem Skript unbekannt. Der Dauerlauf ruft eine Spur mit
   `--live` auf, sobald ihr Zeitfenster offen ist. Seit dem Live-Umbau nennt
   ein --live-Aufruf mit geschlossenen Sperren die Sperrgruende und laeuft
   als Papier weiter (kein argparse-Fehler, keine Order). Der Dauerlauf
   (dauerlauf.nur_fenster_fehlt) fragt nur nach einer Freigabe, wenn GENAU
   EIN Grund fehlt - und der ist das Freigabefenster.

Kein Netz: die Wachen und der Lauf werden ersetzt, das Journal in einen
temporaeren Ordner umgebogen.
"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import handeln

W = {"letzter_einstieg_min_vor_schluss": 60,
     "mindest_range_punkte": {"ETH_USD": 1.0},
     "max_range_punkte": {"ETH_USD": 40.0},
     "ziel_modus": "r_vielfaches", "ziel_k": 1.5,
     "instrument_aktiv": "ETH_USD",
     "handel_erlaubt": False,
     "instrumente": {"ETH_USD": {"okx": "ETH-USDT-SWAP", "punkt_wert_usdt": 1.0}}}


def _ausgabe(argv):
    """Ruft _main mit ersetzten Wachen/Lauf und gibt die Ausgabe zurueck."""
    puffer = io.StringIO()
    with patch.object(handeln, "_wachen", lambda: W), \
            patch.object(handeln, "lauf", lambda modus="papier": []), \
            patch.object(handeln, "zeitfenster_offen", lambda: False), \
            patch.object(handeln.okxf, "schluessel_vorhanden",
                         lambda: True):
        with redirect_stdout(puffer):
            code = handeln._main(argv)
    return code, puffer.getvalue()


class VerweigerungTest(unittest.TestCase):

    def test_live_gesperrt_nennt_gruende_und_faellt_auf_papier(self):
        code, aus = _ausgabe(["--live"])
        self.assertEqual(code, 0, "kein Abbruch - es wird Papier gebucht")
        # Der --live-Fallsafe nennt die Gruende in der Zeile
        # "--live angefordert, aber gesperrt: ..." (kraken-Format).
        self.assertIn("gesperrt", aus)
        self.assertIn("handel_erlaubt=false", aus)

    def test_live_als_positional_und_als_flag(self):
        # Der Dauerlauf ruft "--live" als Argument der Liste auf.
        for form in (["--live"], ["live"]):
            code, aus = _ausgabe(form)
            self.assertEqual(code, 0, form)
            self.assertIn("gesperrt", aus, form)

    def test_vorschau_druckt_den_grund_papier_nicht(self):
        """Der Dauerlauf liest die Sperrgruende mit --vorschau.

        Im Papierlauf darf das Wort "gesperrt" NICHT stehen: der Filter in
        dauerlauf.zyklus() schickt jede Zeile mit dem Wort "gesperrt" nach
        Telegram - bei einem Lauf alle 15 Minuten waere das Spam.
        """
        _, vorschau = _ausgabe(["--vorschau"])
        self.assertIn("gesperrt durch", vorschau)
        _, papier = _ausgabe(["--papier"])
        self.assertNotIn("gesperrt", papier)
        _, standard = _ausgabe([])
        self.assertNotIn("gesperrt", standard)


class SchliessenTest(unittest.TestCase):

    def test_ausstieg_vertraegt_tag_als_string(self):
        """Der Zustand kommt aus JSON - 'tag' ist dort ein String, kein date."""
        with tempfile.TemporaryDirectory() as w:
            alt = handeln.JOURNAL
            handeln.JOURNAL = Path(w) / "handelsjournal.csv"
            try:
                p = {"inst": "ETH_USD", "richtung": "long", "einstieg": 100.0,
                     "stop": 98.0, "ziel": 103.0, "tag": "2026-09-13",
                     "letzter_kurs": 103.0}
                handeln._schliesse(p, p["ziel"], "ziel")
                inhalt = handeln.JOURNAL.read_text(encoding="utf-8")
            finally:
                handeln.JOURNAL = alt
        self.assertIn("2026-09-13", inhalt)
        self.assertIn("ziel", inhalt)

    def test_ausstieg_vertraegt_tag_als_date(self):
        from datetime import date
        with tempfile.TemporaryDirectory() as w:
            alt = handeln.JOURNAL
            handeln.JOURNAL = Path(w) / "handelsjournal.csv"
            try:
                p = {"inst": "ETH_USD", "richtung": "short", "einstieg": 100.0,
                     "stop": 103.0, "ziel": 98.0, "tag": date(2026, 9, 13),
                     "letzter_kurs": 98.0}
                handeln._schliesse(p, p["ziel"], "ziel")
                inhalt = handeln.JOURNAL.read_text(encoding="utf-8")
            finally:
                handeln.JOURNAL = alt
        self.assertIn("2026-09-13", inhalt)


if __name__ == "__main__":
    unittest.main()
