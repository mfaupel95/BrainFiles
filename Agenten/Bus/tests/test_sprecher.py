"""Test fuer sprecher.py - gegen einen Melder-Doppelgaenger, der statt zu
senden protokolliert. Kein Telegram, kein Token.
Direkt ausfuehrbar: python tests/test_sprecher.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import journal   # noqa: E402
import sprecher  # noqa: E402

R = {"deckel_je_stunde": 3, "dauer_faktor": 2.0, "dauer_mindestlaeufe": 5,
     "erwartet": {}}


class Doppelgaenger:
    """Sieht aus wie melder.py, sendet aber nichts."""

    def __init__(self):
        self.gesendet = []

    def sende(self, text, stumm=False):
        self.gesendet.append(text)
        return True


def _sprecher(d, w):
    return sprecher.Sprecher(d, R, wurzel=w, stand=os.path.join(w, "stand.json"))


def test_fehler_wird_gemeldet_erfolg_nicht():
    with tempfile.TemporaryDirectory() as w:
        d = Doppelgaenger()
        s = _sprecher(d, w)
        assert s.verarbeite(journal.neu("a", "ende", code=0, dauer_s=1)) is False
        assert s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1)) is True
        assert len(d.gesendet) == 1
        assert "7" in d.gesendet[0] and "a" in d.gesendet[0]


def test_entdopplung_ueber_id():
    with tempfile.TemporaryDirectory() as w:
        d = Doppelgaenger()
        s = _sprecher(d, w)
        e = journal.neu("a", "ende", code=7, dauer_s=1)
        assert s.verarbeite(e) is True
        assert s.verarbeite(e) is False      # dieselbe id kommt nicht zweimal
        assert len(d.gesendet) == 1


def test_deckel_greift():
    with tempfile.TemporaryDirectory() as w:
        d = Doppelgaenger()
        s = _sprecher(d, w)
        for _ in range(10):
            s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1))
        # Drei Meldungen plus genau eine Notiz, dass jetzt gedeckelt wird.
        assert len(d.gesendet) == 4, d.gesendet
        assert "gedeckelt" in d.gesendet[-1].lower()


def test_nachholen_ab_der_marke():
    with tempfile.TemporaryDirectory() as w:
        stand = os.path.join(w, "stand.json")
        for code in (0, 5):
            journal.anhaengen(journal.neu("a", "ende", code=code, dauer_s=1),
                              wurzel=w)
        d1 = Doppelgaenger()
        sprecher.Sprecher(d1, R, wurzel=w, stand=stand).nachholen()
        assert len(d1.gesendet) == 1
        # Neustart: dieselbe Zeile darf nicht noch einmal kommen.
        d2 = Doppelgaenger()
        sprecher.Sprecher(d2, R, wurzel=w, stand=stand).nachholen()
        assert d2.gesendet == []


def test_tagesmeldung_listet_alle_laeufe():
    with tempfile.TemporaryDirectory() as w:
        for wer in ("routine/sicherung", "handel/xperp"):
            journal.anhaengen(journal.neu(wer, "ende", code=0, dauer_s=4),
                              wurzel=w)
        t = _sprecher(Doppelgaenger(), w).tagesmeldung()
        assert "routine/sicherung" in t and "handel/xperp" in t


def test_totes_telegram_bricht_nichts_ab():
    class Stumm(Doppelgaenger):
        def sende(self, text, stumm=False):
            raise RuntimeError("Telegram tot")

    with tempfile.TemporaryDirectory() as w:
        s = _sprecher(Stumm(), w)
        # Darf nicht werfen - das Journal ist geschrieben, das genuegt.
        assert s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1)) is False


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Sprecher-Tests bestanden")
