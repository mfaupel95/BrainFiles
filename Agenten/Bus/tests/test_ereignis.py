"""Test fuer ereignis.py - der Bus ist hier absichtlich tot.
Die wichtigste Zusicherung der ganzen Stufe wird hier geprueft:
ein toter Bus bricht niemals einen Lauf ab.
Direkt ausfuehrbar: python tests/test_ereignis.py
"""
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ereignis  # noqa: E402
import journal   # noqa: E402

TOT = 1          # dort lauscht nichts


def test_toter_bus_schreibt_selbst_und_wirft_nicht():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        weg = ereignis.melden(journal.neu("handel/xperp", "start"),
                              port=TOT, wurzel=w)
        assert weg == "journal", weg
        assert len(journal.lesen(wurzel=w)) == 1


def test_gemerkter_fehlschlag_beschleunigt_den_naechsten_aufruf():
    # Befund 1: nach einem Fehlschlag muss der zweite Aufruf messbar
    # schneller sein (kein neuer Verbindungsversuch bis ZEITLIMIT) und
    # trotzdem im Journal landen.
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        t0 = time.monotonic()
        weg1 = ereignis.melden(journal.neu("a", "start"), port=TOT, wurzel=w)
        dauer1 = time.monotonic() - t0

        t0 = time.monotonic()
        weg2 = ereignis.melden(journal.neu("a", "start"), port=TOT, wurzel=w)
        dauer2 = time.monotonic() - t0

        assert weg1 == "journal", weg1
        assert weg2 == "journal", weg2
        assert dauer2 < dauer1 / 2, (dauer1, dauer2)
        assert len(journal.lesen(wurzel=w)) == 2


def test_abgelaufene_merkzeit_klopft_wieder_an():
    # Befund 1: die Merkzeit ist kein Dauerverzicht - nach ihrem Ablauf
    # (hier kuenstlich zurueckgedreht statt 60 s zu warten) wird wieder
    # angeklopft, was sich wieder in der vollen ZEITLIMIT-Wartezeit zeigt.
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        ereignis.melden(journal.neu("a", "start"), port=TOT, wurzel=w)
        assert ereignis._zuletzt_toter_versuch is not None

        ereignis._zuletzt_toter_versuch -= ereignis.MERKZEIT + 1

        t0 = time.monotonic()
        ereignis.melden(journal.neu("a", "start"), port=TOT, wurzel=w)
        dauer = time.monotonic() - t0
        assert dauer >= ereignis.ZEITLIMIT * 0.5, dauer


def test_lauf_meldet_start_und_ende():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        with ereignis.lauf("routine/sicherung", port=TOT, wurzel=w):
            pass
        z = journal.lesen(wurzel=w)
        assert [e["was"] for e in z] == ["start", "ende"], z
        assert z[1]["code"] == 0
        assert z[1]["dauer_s"] is not None


def test_lauf_reicht_die_ausnahme_durch_und_meldet_fehler():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        gefangen = None
        try:
            with ereignis.lauf("handel/orb", port=TOT, wurzel=w):
                raise ValueError("kaputt")
        except ValueError as f:
            gefangen = f
        # Der Aufrufer muss den Fehler weiterhin sehen - wir verschlucken nichts.
        assert isinstance(gefangen, ValueError)
        z = journal.lesen(wurzel=w)
        assert z[1]["was"] == "ende" and z[1]["code"] == 1
        assert "kaputt" in z[1]["text"]


def test_lauf_mit_sauberem_systemexit_meldet_erfolg():
    # Befund 3: sys.exit(0) bzw. sys.exit() ist kein Fehler - sonst meldet
    # das Journal faelschlich code: 1 fuer einen sauberen Lauf.
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        gefangen = None
        try:
            with ereignis.lauf("routine/aufraeumen", port=TOT, wurzel=w):
                raise SystemExit(0)
        except SystemExit as f:
            gefangen = f
        assert gefangen is not None and gefangen.code == 0
        z = journal.lesen(wurzel=w)
        assert z[1]["was"] == "ende"
        assert z[1]["code"] == 0, z[1]
        assert z[1]["text"] == "", z[1]


def test_lauf_mit_systemexit_ungleich_null_uebernimmt_code():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        gefangen = None
        try:
            with ereignis.lauf("routine/aufraeumen", port=TOT, wurzel=w):
                raise SystemExit(3)
        except SystemExit as f:
            gefangen = f
        assert gefangen is not None and gefangen.code == 3
        z = journal.lesen(wurzel=w)
        assert z[1]["was"] == "ende" and z[1]["code"] == 3, z[1]


def test_auch_unschreibbares_journal_bricht_nicht_ab():
    # Weder Bus noch Journal erreichbar: der Lauf muss trotzdem durchlaufen.
    # wurzel zeigt auf eine Datei (nicht auf ein nicht vorhandenes Laufwerk -
    # Befund 4): journal.anhaengen haengt daran einen Dateinamen an und
    # os.makedirs scheitert zuverlaessig, weil der Pfad bereits eine Datei
    # ist. Das traegt auf jedem System, ohne von der Laufwerksbelegung
    # abzuhaengen.
    ereignis._merkzustand_zuruecksetzen()
    mit_datei = tempfile.NamedTemporaryFile(delete=False)
    mit_datei.close()
    try:
        gelaufen = False
        with ereignis.lauf("a", port=TOT, wurzel=mit_datei.name):
            gelaufen = True
        assert gelaufen
    finally:
        os.remove(mit_datei.name)


def test_melden_gibt_nichts_wenn_weder_bus_noch_journal_erreichbar():
    # Befund 2: der dritte Rueckgabewert "nichts" ist bislang ungetestet -
    # Bus tot und Journal unschreibbar (wurzel ist eine Datei, siehe oben).
    ereignis._merkzustand_zuruecksetzen()
    mit_datei = tempfile.NamedTemporaryFile(delete=False)
    mit_datei.close()
    try:
        weg = ereignis.melden(journal.neu("a", "start"),
                              port=TOT, wurzel=mit_datei.name)
        assert weg == "nichts", weg
    finally:
        os.remove(mit_datei.name)


def test_hinweis_traegt_text():
    ereignis._merkzustand_zuruecksetzen()
    with tempfile.TemporaryDirectory() as w:
        ereignis.hinweis("handel/xperp", "SNDK ueber SuperTrend",
                         port=TOT, wurzel=w)
        z = journal.lesen(wurzel=w)
        assert z[0]["was"] == "hinweis" and z[0]["code"] is None
        assert "SNDK" in z[0]["text"]


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Ereignis-Tests bestanden")
