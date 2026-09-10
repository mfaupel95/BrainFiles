"""Prueft, dass jede geplante Routine den Bus ruft - und zwar an allen
Ausstiegen, nicht nur im Erfolgsfall. Direkt ausfuehrbar.
"""
import glob
import os

BUS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROUTINEN = os.path.join(os.path.dirname(BUS), "Routinen")


def geplante():
    for p in sorted(glob.glob(os.path.join(ROUTINEN, "*.ps1"))):
        name = os.path.basename(p)
        if (name.startswith("einmalig-") or name.endswith("-hook.ps1")
                or name == "bus.ps1"):
            continue
        yield p, name[:-4]


def test_es_gibt_ueberhaupt_routinen():
    assert len(list(geplante())) >= 15, "Ordner falsch gefunden?"


def test_jede_routine_meldet():
    fehlt = []
    for p, name in geplante():
        with open(p, encoding="utf-8") as f:
            inhalt = f.read()
        if ("Ereignis.ps1" not in inhalt or "Melde-Start" not in inhalt
                or "Melde-Ende" not in inhalt
                or ("routine/" + name) not in inhalt):
            fehlt.append(name)
    assert not fehlt, "ohne Bus-Anbindung: %s" % fehlt


def test_melde_ende_steht_an_jedem_ausstieg():
    # Eine Routine, die im Fehlerfall 'exit' ruft, ohne vorher zu melden,
    # sieht im Journal wie ein ausgebliebener Lauf aus. Das ist schlimmer als
    # gar keine Anbindung, weil es einen falschen Alarm erzeugt.
    schief = []
    for p, name in geplante():
        with open(p, encoding="utf-8") as f:
            zeilen = f.readlines()
        for i, z in enumerate(zeilen):
            if z.strip().startswith("exit "):
                if "Melde-Ende" not in "".join(zeilen[max(0, i - 4):i]):
                    schief.append("%s:%d" % (name, i + 1))
    assert not schief, "exit ohne vorheriges Melde-Ende: %s" % schief


def test_keine_absoluten_pfade_dazugekommen():
    treffer = []
    for p, name in geplante():
        with open(p, encoding="utf-8") as f:
            for i, z in enumerate(f):
                if "Ereignis.ps1" in z and ":\\" in z:
                    treffer.append("%s:%d" % (name, i + 1))
    assert not treffer, "absoluter Pfad zum Bus: %s" % treffer


if __name__ == "__main__":
    for name, f in sorted(list(globals().items())):
        if name.startswith("test_"):
            f()
            print("ok", name)
    print("alle Anbindungs-Tests Routinen bestanden")
