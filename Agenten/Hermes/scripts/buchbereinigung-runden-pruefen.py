"""Gegenprobe: sind die 9 Buchbereinigungs-Zeilen echte Runden?

Gemessen 05.10.2026. Offene Frage aus dem Bereinigungslauf: `paarung()`
lieferte 8 Paare, `runden_aus_journal` 2 Eintraege - und die Form ist ein
Tupel, kein Dict. Diese Skript fragt deshalb die RUNDENZAHL der
Hausrechnung und prueft, ob die Buchbereinigungs-Zeilen darin als
Buchhaltung gefuehrt werden (das ist der ganze Zweck von
`grund=buchbereinigung`).

Kein Raten: Die Rundenzahl kommt aus `kosten_wendepunkt`, die Einordnung
aus `stoerungen.ist_stoerung` - beide die Hausfunktionen, keine eigene.
"""
import importlib.util
import sys
from pathlib import Path

HANDEL = Path(r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel")
JOURNAL = HANDEL / "omniquant" / "handelsjournal.csv"


def lade(name):
    spec = importlib.util.spec_from_file_location(name, str(HANDEL / (name + ".py")))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def main():
    sys.path.insert(0, str(HANDEL))
    st = lade("stoerungen")
    kw = lade("kosten_wendepunkt")

    print("=== 1. Die Merkmale, die den Grund erkennen ===")
    print("  STOERUNG_MERKMAL: %s" % (st.STOERUNG_MERKMAL,))
    print("  BUCHHALTUNG:     %s" % (st.BUCHHALTUNG,))
    print("  ist_stoerung('buchbereinigung')  = %s" % st.ist_stoerung("buchbereinigung"))
    print("  ist_stoerung('prognose-treffer') = %s" % st.ist_stoerung("prognose-treffer"))
    print("  -> OHNE den Grund 'buchbereinigung' waere jede Zeile eine Runde.")

    print("\n=== 2. Paarung und Runden im Journal ===")
    paare = kw.paarung(JOURNAL)
    print("  paarung(): %d Paare (Instanz-Gruppen)" % len(paare))
    runden = list(kw.runden_aus_journal(JOURNAL))
    print("  runden_aus_journal(): %d Runden" % len(runden))
    if runden:
        r0 = runden[0]
        print("  Form einer Runde: %s" % type(r0).__name__)
        print("  Element: %s" % (str(r0)[:140],))

    print("\n=== 3. Die Rundenzahl der HAUSrechnung ===")
    for name in ("kennzahlen", "kennzahlen_fuer"):
        f = getattr(kw, name, None)
        if f is None:
            continue
        try:
            k = f(runden) if name == "kennzahlen" else f("omniquant")
        except TypeError:
            continue
        except Exception as e:                                # noqa: BLE001
            print("  %s: %s" % (name, str(e)[:70]))
            continue
        print("  %s ->" % name)
        for feld in sorted(k):
            if feld in ("inst", "gueltig"):
                continue
            print("     %-16s %s" % (feld, k[feld]))
        break

    print("\n=== 4. Gegenprobe: die Buchbereinigungs-Zeilen in der Paarung ===")
    import csv
    zeilen = list(csv.DictReader(open(JOURNAL, encoding="utf-8")))
    bb = [z for z in zeilen if z.get("grund") == "buchbereinigung"]
    print("  Zeilen mit grund=buchbereinigung: %d" % len(bb))
    print("  Summe wert_usd: %.2f USD" % sum(float(z["wert_usd"]) for z in bb))
    print("  Summe einsatz_usd: %.2f USD" % sum(float(z["einsatz_usd"]) for z in bb))
    neutral = all(abs(float(z["wert_usd"]) - float(z["einsatz_usd"])) < 0.01 for z in bb)
    print("  neutral (wert == einsatz, je Zeile): %s" % neutral)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())