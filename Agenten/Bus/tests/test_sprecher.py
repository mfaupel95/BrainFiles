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


def test_deckelnotiz_pro_stunde_neu():
    # Befund 1: die Deckelnotiz-Marke darf nicht fuer immer stehen bleiben -
    # jedes neue Stundenfenster braucht wieder genau eine eigene Notiz.
    # time.monotonic wird durch eine steuerbare Uhr ersetzt, damit das
    # Verstreichen einer Stunde nicht wirklich abgewartet werden muss.
    uhr = {"t": 1000.0}
    orig = sprecher.time.monotonic
    sprecher.time.monotonic = lambda: uhr["t"]
    try:
        with tempfile.TemporaryDirectory() as w:
            d = Doppelgaenger()
            s = _sprecher(d, w)
            # Erstes Stundenfenster: drei Meldungen raus, die vierte gedeckelt.
            for i in range(4):
                uhr["t"] = 1000.0 + i
                s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1))
            assert len(d.gesendet) == 4, d.gesendet
            assert "gedeckelt" in d.gesendet[-1].lower()
            # Eine Stunde und mehr weiter: neues Fenster, alle alten
            # Zeitstempel fallen aus der Rolle - genau wie in _darf_senden.
            uhr["t"] = 1000.0 + 3 + 3601
            for i in range(4):
                uhr["t"] += i
                s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1))
            # Erwartet: zweite Deckelnotiz, nicht kommentarloses Verwerfen.
            assert len(d.gesendet) == 8, d.gesendet
            deckelnotizen = [t for t in d.gesendet if "gedeckelt" in t.lower()]
            assert len(deckelnotizen) == 2, deckelnotizen
    finally:
        sprecher.time.monotonic = orig


def test_tagesmeldung_nicht_doppelt_nach_neustart():
    # Befund 2: letzter_tag muss in stand.json ueberleben - sonst meldet ein
    # nach 20 Uhr neu gestarteter Sprecher den Tag ein zweites Mal.
    import datetime as dt_modul
    with tempfile.TemporaryDirectory() as w:
        stand = os.path.join(w, "stand.json")
        jetzt = dt_modul.datetime.now().replace(hour=21, minute=0, second=0,
                                                 microsecond=0)
        d1 = Doppelgaenger()
        s1 = _sprecher(d1, w)
        assert s1._tagesmeldung_faellig(jetzt) is True
        s1.letzter_tag = jetzt.strftime("%Y-%m-%d")
        s1._stand_schreiben()
        # Neustart: zweite Instanz auf demselben stand.json, wieder nach 20 Uhr.
        d2 = Doppelgaenger()
        s2 = _sprecher(d2, w)
        assert s2._tagesmeldung_faellig(jetzt) is False


def test_totes_telegram_bricht_nichts_ab():
    class Stumm(Doppelgaenger):
        def sende(self, text, stumm=False):
            raise RuntimeError("Telegram tot")

    with tempfile.TemporaryDirectory() as w:
        s = _sprecher(Stumm(), w)
        # Darf nicht werfen - das Journal ist geschrieben, das genuegt.
        assert s.verarbeite(journal.neu("a", "ende", code=7, dauer_s=1)) is False


def test_spitze_klammern_werden_escaped():
    # Befund 10.09.2026: melder.sende nutzt parse_mode=HTML. Ein Fehlertext
    # mit "<urlopen error timed out>" haette Telegram mit 400 abgelehnt.
    with tempfile.TemporaryDirectory() as w:
        d = Doppelgaenger()
        s = _sprecher(d, w)
        s.verarbeite(journal.neu("a", "ende", code=1, dauer_s=1,
                                 text="URLError: <urlopen error timed out>"))
        assert d.gesendet, "nichts gesendet"
        assert "<urlopen" not in d.gesendet[0], d.gesendet[0]
        assert "&lt;urlopen" in d.gesendet[0], d.gesendet[0]


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Sprecher-Tests bestanden")
