"""Skalierungsfehler in den vier Indikatorspuren beheben (15.09.2026).

ZWEI FEHLER, beide in allen vier Spuren (wavetrend, macd_mtf, squeeze,
supertrend), beide beim Abschreiben aus einer Vorlage entstanden:

1. `gv = (kurs - p["einstieg"]) * vz` rechnet die ROHE KURSDIFFERENZ. Richtig
   ist der Anteil am Nominalwert: eine Kursbewegung von x Prozent bewegt x
   Prozent des Nominalwerts. Mit der rohen Differenz landete bei BTC ein
   Erloes in Kurshoehe im Journal (Beispiel: 100 USD Nominal, Verkauf mit
   75911,19 USD "Erloes").

2. `pruefe_ausstiege(z, k, w)` lief ueber ALLE offenen Positionen, obwohl `k`
   die Kerzen EINES Instruments sind. Eine SOL-Position wurde so mit dem
   BTC-Kurs bewertet. Jetzt prueft der Aufruf nur die Positionen des
   Instruments, dessen Kerzen gerade vorliegen.

Das Skript ist idempotent: was schon richtig ist, bleibt unveraendert. Vor
jeder Aenderung entsteht eine Sicherung <datei>.bak-20260915.
"""
import shutil
from pathlib import Path

SPUREN = ("wavetrend", "macd_mtf", "squeeze", "supertrend")
HIER = Path(__file__).resolve().parent

ALT_FORMEL = """        gv = (kurs - p["einstieg"]) * vz
        erloes = p["nominal"] + gv
"""
NEU_FORMEL = """        # G/V auf den NOMINALWERT: eine Kursbewegung von x Prozent bewegt
        # x Prozent des Nominalwerts. Bis zum 15.09.2026 stand hier die rohe
        # Kursdifferenz - bei BTC ein Faktor von rund 70.000, der Erloes
        # landete in Kurshoehe im Journal.
        gv = p["nominal"] * (kurs - p["einstieg"]) / p["einstieg"] * vz
        erloes = p["nominal"] + gv
"""

ALT_KOPF = """def pruefe_ausstiege(z, k, w):
    behalten = []
    for p in z.get("positionen", []):
"""
NEU_KOPF = """def pruefe_ausstiege(z, k, w, nur=None):
    \"\"\"Prueft offene Positionen gegen die Kerzen von `nur`.

    `k` sind die Kerzen EINES Instruments. Ohne die Einschraenkung wurde jede
    offene Position gegen diesen einen Kurs geprueft - eine SOL-Position mit
    dem BTC-Kurs bewertet (15.09.2026). `nur=None` behaelt das alte Verhalten
    fuer Aufrufer, die wirklich alle Positionen meinen.
    \"\"\"
    behalten = []
    for p in z.get("positionen", []):
        if nur is not None and p.get("inst") != nur:
            behalten.append(p)
            continue
"""

ALT_AUFRUF = "            pruefe_ausstiege(z, k, w)\n"
NEU_AUFRUF = "            pruefe_ausstiege(z, k, w, nur=inst)\n"


def main():
    for spur in SPUREN:
        p = HIER / spur / "handeln.py"
        if not p.exists():
            print("%-11s FEHLT" % spur)
            continue
        text = p.read_text(encoding="utf-8")
        schritte = []
        if ALT_FORMEL in text:
            text = text.replace(ALT_FORMEL, NEU_FORMEL)
            schritte.append("Formel")
        if ALT_KOPF in text:
            text = text.replace(ALT_KOPF, NEU_KOPF)
            schritte.append("Kopf")
        if ALT_AUFRUF in text:
            text = text.replace(ALT_AUFRUF, NEU_AUFRUF)
            schritte.append("Aufruf")
        if not schritte:
            print("%-11s schon richtig" % spur)
            continue
        bak = p.with_suffix(".py.bak-20260915")
        if not bak.exists():
            shutil.copy2(p, bak)
        p.write_text(text, encoding="utf-8", newline="")
        print("%-11s %s  (Sicherung %s)" % (spur, " + ".join(schritte),
                                            bak.name))


if __name__ == "__main__":
    main()
