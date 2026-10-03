"""Gegenprobe: fallen die Bildtests ohne den Fix wirklich auf?

Aufruf: python Agenten/Bus/tests/gegenprobe_bilder.py
Legt skillsbot.py dreimal um (altes Verwerfen, keine Bilddurchreichung,
Original) und misst den Testlauf. Danach muss die Datei wieder bytegleich
dem Ausgangsstand entsprechen.
"""
import os
import shutil
import subprocess
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
BUS = os.path.dirname(HIER)
QUELLE = os.path.join(BUS, "skillsbot.py")
SICHERUNG = QUELLE + ".gegenprobe"


def lauf():
    r = subprocess.run([sys.executable, "-m", "unittest",
                        "tests.test_skillsbot_bilder"],
                       cwd=BUS, capture_output=True, text=True)
    z = [x for x in r.stderr.strip().splitlines() if x.strip()]
    return z[-1] if z else "?"


def main():
    roh = open(QUELLE, "rb").read()
    shutil.copy2(QUELLE, SICHERUNG)
    try:
        a = roh.decode("utf-8").replace(
            "text = _bild_text(nachricht)\r\n                if chat is None:",
            "text = nachricht.get(\"text\")\r\n"
            "                if chat is None or text is None:")
        assert a != roh.decode("utf-8"), "Gegenprobe A passt nicht"
        open(QUELLE, "wb").write(a.encode("utf-8"))
        print("A ohne Caption-Lesen     :", lauf())

        b = roh.decode("utf-8").replace(
            "bearbeite(_mit_bildern(text, bilder), chat)",
            "bearbeite(text, chat)")
        assert b != roh.decode("utf-8"), "Gegenprobe B passt nicht"
        open(QUELLE, "wb").write(b.encode("utf-8"))
        print("B ohne Bilddurchreichung :", lauf())
    finally:
        open(QUELLE, "wb").write(roh)
        if os.path.exists(SICHERUNG):
            os.remove(SICHERUNG)
    print("Original wiederhergestellt:", lauf())
    print("bytegleich:", open(QUELLE, "rb").read() == roh)


if __name__ == "__main__":
    main()