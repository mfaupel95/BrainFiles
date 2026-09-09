"""Test fuer ereignis.py - der Bus ist hier absichtlich tot.
Die wichtigste Zusicherung der ganzen Stufe wird hier geprueft:
ein toter Bus bricht niemals einen Lauf ab.
Direkt ausfuehrbar: python tests/test_ereignis.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ereignis  # noqa: E402
import journal   # noqa: E402

TOT = 1          # dort lauscht nichts


def test_toter_bus_schreibt_selbst_und_wirft_nicht():
    with tempfile.TemporaryDirectory() as w:
        weg = ereignis.melden(journal.neu("handel/xperp", "start"),
                              port=TOT, wurzel=w)
        assert weg == "journal", weg
        assert len(journal.lesen(wurzel=w)) == 1


def test_lauf_meldet_start_und_ende():
    with tempfile.TemporaryDirectory() as w:
        with ereignis.lauf("routine/sicherung", port=TOT, wurzel=w):
            pass
        z = journal.lesen(wurzel=w)
        assert [e["was"] for e in z] == ["start", "ende"], z
        assert z[1]["code"] == 0
        assert z[1]["dauer_s"] is not None


def test_lauf_reicht_die_ausnahme_durch_und_meldet_fehler():
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


def test_auch_unschreibbares_journal_bricht_nicht_ab():
    # Weder Bus noch Journal erreichbar: der Lauf muss trotzdem durchlaufen.
    gelaufen = False
    with ereignis.lauf("a", port=TOT, wurzel="Z:\\gibt-es-nicht\\journal"):
        gelaufen = True
    assert gelaufen


def test_hinweis_traegt_text():
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
