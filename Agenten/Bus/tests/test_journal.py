"""Test fuer journal.py - reine Datei-Arbeit, kein Netz.
Direkt ausfuehrbar: python tests/test_journal.py
"""
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal  # noqa: E402

FELDER = {"id", "zeit", "wer", "was", "code", "dauer_s", "text", "log"}


def test_neu_hat_alle_felder():
    e = journal.neu("handel/xperp", "start")
    assert set(e) == FELDER, e
    assert e["code"] is None and e["dauer_s"] is None
    assert len(e["id"]) == 32
    # Die Zeitangabe muss eine Zeitzone tragen, sonst ist sie spaeter nicht
    # sortierbar. Auf das Pluszeichen zu pruefen traegt nicht: bei negativem
    # Versatz steht dort ein Minus.
    assert datetime.fromisoformat(e["zeit"]).tzinfo is not None


def test_ids_sind_verschieden():
    assert journal.neu("a", "start")["id"] != journal.neu("a", "start")["id"]


def test_anhaengen_und_lesen():
    with tempfile.TemporaryDirectory() as w:
        journal.anhaengen(journal.neu("routine/sicherung", "start"), wurzel=w)
        journal.anhaengen(journal.neu("routine/sicherung", "ende", code=0,
                                      dauer_s=12), wurzel=w)
        zeilen = journal.lesen(wurzel=w)
        assert len(zeilen) == 2, zeilen
        assert zeilen[1]["code"] == 0 and zeilen[1]["dauer_s"] == 12


def test_halbe_zeile_wird_uebersprungen():
    # Nach einem Stromausfall kann die letzte Zeile abgeschnitten sein.
    # Das darf das Lesen der guten Zeilen nicht verhindern.
    with tempfile.TemporaryDirectory() as w:
        journal.anhaengen(journal.neu("a", "start"), wurzel=w)
        with open(journal.pfad(wurzel=w), "a", encoding="utf-8") as f:
            f.write('{"id": "abc", "wer"\n')
        assert len(journal.lesen(wurzel=w)) == 1


def test_lesen_ohne_datei_ist_leer():
    with tempfile.TemporaryDirectory() as w:
        assert journal.lesen(wurzel=w) == []


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Journal-Tests bestanden")
