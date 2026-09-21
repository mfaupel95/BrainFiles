"""Offline-Pruefung der SkillsBot-Befehlspfade (sendet nichts an Telegram)."""
import io
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skillsbot as s  # noqa: E402

gesendet = []
# Die ECHTE sende() merken: Abschnitt 2 unten prueft genau ihren
# Laengenschnitt - mit dem Stummel von hier wuerde er ins Leere greifen
# (0 Teile, IndexError).
echte_sende = s.sende
s.sende = lambda chat, text: gesendet.append(text)

befehle = ["/hilfe", "/skills", "/skills handel", "/skill systemdiagnose",
           "/status", "/papierstatus", "/markt", "/spuren", "/strategien",
           "/indikatoren", "/lage", "/live", "/model", "/modeö", "/",
           "/run gibt-es-nicht", "/run"]

for b in befehle:
    gesendet.clear()
    t0 = time.time()
    try:
        antwort, ktx = s.bearbeite(b, 1)
        dauer = round(time.time() - t0, 1)
        print("%-24s %6.1fs  len=%5d ktx=%s" % (b, dauer, len(antwort or ""),
                                                bool(ktx)))
        if len(antwort or "") > s.MAX_ZEICHEN:
            print("    !! laenger als ein Telegram-Aufruf: %d" % len(antwort))
        erste = (antwort or "").replace("\n", " | ")[:110]
        print("    %s" % erste)
    except Exception as e:  # noqa: BLE001
        print("%-24s AUSNAHME %s: %s" % (b, type(e).__name__, e))

# --- Laengenschnitt: bleibt der Text zusammen und an Zeilengrenzen? --------
print("\n=== sende(): Schnittverhalten ===")
text = "\n".join("Zeile %03d" % i for i in range(900))


class FakeRuf:
    def __init__(self):
        self.rufe = []

    def __call__(self, methode, daten=None, zeit=30):
        self.rufe.append(daten)
        return {}


s.sende = echte_sende        # Stummel aus Abschnitt 1 zuruecknehmen
fake = FakeRuf()
orig = s._ruf
s._ruf = fake
s.sende(1, text)
s._ruf = orig
teile = [d["text"] for d in fake.rufe]
print("Teile: %d, Laengen: %s" % (len(teile), [len(t) for t in teile]))
print("Zusammengesetzt identisch:", "".join(teile) == text)
schnitt = teile[0][-30:].replace("\n", "\\n")
print("Ende Teil 1: ...%s" % schnitt)
print("Anfang Teil 2: %s" % teile[1][:30].replace("\n", "\\n"))
