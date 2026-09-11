"""Test fuer auffaellig.py - reine Rechnung, kein Netz.
Direkt ausfuehrbar: python tests/test_auffaellig.py
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import auffaellig  # noqa: E402

R = {"deckel_je_stunde": 20, "dauer_faktor": 2.0, "dauer_mindestlaeufe": 5,
     "erwartet": {"routine/sicherung": 30}}


def e(was, code=None, dauer=None, text=""):
    return {"id": "x", "zeit": "", "wer": "routine/sicherung", "was": was,
            "code": code, "dauer_s": dauer, "text": text, "log": None}


def hist(*dauern):
    return [e("ende", code=0, dauer=d) for d in dauern]


FAELLE = [
    # (Name, Ereignis, Historie, auffaellig?)
    ("Fehlercode meldet immer",     e("ende", code=1, dauer=3), hist(3, 3, 3, 3, 3), True),
    ("Erfolg in normaler Zeit",     e("ende", code=0, dauer=3), hist(3, 3, 3, 3, 3), False),
    ("doppelte Dauer meldet",       e("ende", code=0, dauer=7), hist(3, 3, 3, 3, 3), True),
    ("knapp darunter schweigt",     e("ende", code=0, dauer=6), hist(3, 3, 3, 3, 3), False),
    ("zu wenig Historie schweigt",  e("ende", code=0, dauer=99), hist(3, 3), False),
    ("Start ist nie auffaellig",    e("start"), hist(3, 3, 3, 3, 3), False),
    ("Hinweis ist immer auffaellig", e("hinweis", text="ATR steigt"), [], True),
]


def test_tabelle():
    for name, ereignis, historie, erwartet in FAELLE:
        grund = auffaellig.bewerte(ereignis, historie, R)
        assert bool(grund) == erwartet, "%s -> %r" % (name, grund)
        if erwartet:
            assert isinstance(grund, str) and grund, name


def test_median_nicht_mittelwert():
    # Ein einzelner Ausreisser darf die Schwelle nicht hochziehen.
    assert auffaellig.bewerte(e("ende", code=0, dauer=10),
                              hist(3, 3, 3, 3, 300), R)


def test_ausbleibender_lauf():
    jetzt = datetime(2026, 9, 9, 12, 0)
    spaet = {"routine/sicherung": jetzt - timedelta(hours=40)}
    puenktlich = {"routine/sicherung": jetzt - timedelta(hours=2)}
    assert auffaellig.ausbleibend(spaet, R, jetzt) == ["routine/sicherung"]
    assert auffaellig.ausbleibend(puenktlich, R, jetzt) == []
    # Nie gelaufen ist auch ausgeblieben.
    assert auffaellig.ausbleibend({}, R, jetzt) == ["routine/sicherung"]


def test_fehlertext_steht_in_der_meldung():
    # Befund 10.09.2026: "Ergebniscode 1" ohne Ursache war nicht zu deuten.
    ereignis = e("ende", code=1, dauer=263,
                 text="URLError: <urlopen error timed out>")
    grund = auffaellig.bewerte(ereignis, hist(3, 3, 3, 3, 3), R)
    assert "1" in grund, grund
    assert "URLError" in grund, grund
    assert "urlopen error timed out" in grund, grund


def test_protokollpfad_steht_in_der_meldung():
    ereignis = e("ende", code=1, dauer=1, text="")
    ereignis["log"] = "Agenten/Routinen/logs/sicherung-letzter-lauf.log"
    grund = auffaellig.bewerte(ereignis, hist(3, 3, 3, 3, 3), R)
    assert "sicherung-letzter-lauf.log" in grund, grund


def test_regeln_datei_ist_lesbar():
    r = auffaellig.regeln()
    for schluessel in ("deckel_je_stunde", "dauer_faktor",
                       "dauer_mindestlaeufe", "erwartet"):
        assert schluessel in r, r


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Auffaelligkeits-Tests bestanden")
