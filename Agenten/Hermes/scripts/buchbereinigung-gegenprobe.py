"""Gegenprobe nach der Buchbereinigung von omniquant (05.10.2026).

Zwei Fragen, zwei Zeilen als Antwort:

  1. Hat die Bereinigung eine neue HANDELSRUNDE erzeugt?
     Das entscheidet der Grund `buchbereinigung` in der Journalzeile:
     `stoerungen.ist_stoerung` erkennt ihn, und
     `kosten_wendepunkt.paarung` (Zeile 115) verwirft solche Zeilen aus
     der Rundenzahl. Ohne diesen Grund waere jede Zeile eine Runde.

  2. Hat sich das Ergebnis der Spur verschoben?
     Die Bilanz lebt im Journal, nicht im Zustand - der Zustand fuehrt nur
     den gebundenen Einsatz. Ein Einsatz, der auf 0 sinkt, ist die gewollte
     Wirkung, keine Verlustbuchung.

Die HAUSrechnung wird benutzt, nicht eine eigene:
`auswertung_alle.kennzahlen_fuer('omniquant')` ist dieselbe Funktion, die
der Tagesbericht zeigt. Fuer den Vorher-Zustand laeuft sie auf einer KOPIE
der Spur in einem Temp-Ordner - die echten Dateien werden nicht angefasst.

ANLASS fuer dieses Skript: mein Bereinigungswerkzeug meldete selbst
"Bilanz unveraendert: NEIN (Differenz -450.00)". Das war ein Fehler IM
WERKZEUG: verglichen wurde `Runden-Bestand` (Summe der Einsatzes offener
Positionen + verluste_usd) VORHER mit demselben Wert NACHHER. Diese
Rechnung kann nie stimmen - sie zieht per Definition genau das ab, was
gerade ausgetragen wurde. Die eigentliche Frage (Rundenzahl, Ergebnis)
wird hier beantwortet.
"""
import csv
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HANDEL = r"C:\Users\faupe\Documents\BrainFiles\Agenten\Handel"
SPUR = os.path.join(HANDEL, "omniquant")
STAMP = "20261005"


def lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def kennzahlen_auf(journal_datei):
    """`kennzahlen_fuer('omniquant')` mit umgebogenem Journal-Pfad.

    Der Umweg ist noetig: auswertung_alle holt den Journal-Pfad aus dem
    SPURMODUL, nicht aus einem Argument. Also wird das Modul in einem
    Temp-Ordner geladen, dessen Journal die gewuenschte Kopie ist.
    """
    tmp = tempfile.mkdtemp(prefix="omni_vorher_")
    alt_module = {n: sys.modules[n] for n in
                  ("handeln", "auswertung", "kraken_perp", "live_perp")
                  if n in sys.modules}
    try:
        for name in ("handeln.py", "kraken_perp.py", "live_perp.py",
                     "auswertung.py", "wachen.json", "zustand.json"):
            src = os.path.join(SPUR, name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(tmp, name))
        shutil.copy2(journal_datei, os.path.join(tmp, "handelsjournal.csv"))

        sys.path.insert(0, tmp)
        sys.path.insert(0, HANDEL)
        try:
            for n in alt_module:
                sys.modules.pop(n, None)
            import auswertung_alle as aa
            return aa.kennzahlen_fuer("omniquant")
        finally:
            for p in (HANDEL, tmp):
                if p in sys.path:
                    sys.path.remove(p)
            sys.modules.update(alt_module)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def einsatzsumme(positionen):
    s = 0.0
    for q in positionen or []:
        for f in ("einsatz_usd", "nominal"):
            if q.get(f) not in (None, ""):
                s += float(q[f])
                break
    return s


def main():
    bak_journal = os.path.join(SPUR, "handelsjournal.csv.bak-" + STAMP)
    bak_zustand = os.path.join(SPUR, "zustand.json.bak-" + STAMP)
    journal = os.path.join(SPUR, "handelsjournal.csv")

    print("=== 1. Zustand: die gewollte Wirkung ===")
    z_vor = json.load(open(bak_zustand, encoding="utf-8"))
    z_nach = json.load(open(os.path.join(SPUR, "zustand.json"), encoding="utf-8"))
    v = z_vor.get("positionen") or []
    n = z_nach.get("positionen") or []
    print("  offene Positionen:  %2d -> %2d" % (len(v), len(n)))
    print("  gebundener Einsatz:  %.2f -> %.2f USD"
          % (einsatzsumme(v), einsatzsumme(n)))
    print("  verluste_usd:       %.4f -> %.4f  (UNVERAENDERT)"
          % (float(z_vor.get("verluste_usd") or 0),
             float(z_nach.get("verluste_usd") or 0)))
    print("  -> Der Einsatz sinkt um %.2f USD. Das ist die Bereinigung;"
          % (einsatzsumme(v) - einsatzsumme(n)))
    print("     es gab keinen Verkauf, deshalb bewegt sich verluste_usd nicht.")

    print("\n=== 2. Die neuen Journal-Zeilen ===")
    alt = list(csv.DictReader(open(bak_journal, encoding="utf-8")))
    neu = list(csv.DictReader(open(journal, encoding="utf-8")))
    added = neu[len(alt):] if len(neu) > len(alt) else []
    print("  Zeilen: %d -> %d (%d neu)" % (len(alt), len(neu), len(added)))
    gruende = {}
    for r in added:
        gruende[r.get("grund")] = gruende.get(r.get("grund"), 0) + 1
    print("  Gruende: %s" % (gruende or "keine"))

    print("\n=== 3. Sind es echte Runden? (stoerungen.BUCHHALTUNG) ===")
    stoer = lade(os.path.join(HANDEL, "stoerungen.py"), "st_omni_probe")
    alle = all(stoer.ist_stoerung(r.get("grund")) for r in added)
    print("  alle %d Zeilen als Buchhaltung erkannt: %s" % (len(added), alle))
    print("  Stoerungs-Merkmale:  %s" % (stoer.STOERUNG_MERKMAL,))
    print("  Buchhaltungs-Merkmale: %s" % (stoer.BUCHHALTUNG,))
    if not alle:
        print("  -> NEIN: die Zeilen wuerden als Handelsrunde zaehlen. FEHLER.")
        return 1

    print("\n=== 4. Die HAUSrechnung, vorher gegen nachher ===")
    kv = kennzahlen_auf(bak_journal)
    kn = kennzahlen_auf(journal)
    felder = sorted(set(kv) | set(kn))
    print("  %-16s %18s %18s" % ("Feld", "vorher", "nachher"))
    bewegt = []
    for f in felder:
        a, b = kv.get(f), kn.get(f)
        marke = ""
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
                and not isinstance(a, bool):
            if abs(float(a) - float(b)) > 0.005:
                marke = "   <- BEWEGT"
                bewegt.append(f)
        print("  %-16s %18s %18s%s" % (f, a, b, marke))

    print("\n=== 5. Fazit ===")
    n_vor = kv.get("n", kv.get("runden"))
    n_nach = kn.get("n", kn.get("runden"))
    if n_vor is not None and n_nach is not None:
        print("  Rundenzahl %s -> %s" % (n_vor, n_nach))
        print("  %s" % ("NEUTRAL - keine neue Handelsrunde."
                        if n_nach == n_vor else
                        "NICHT NEUTRAL: die Bereinigung hat Runden erzeugt."))
    print("  bewegte Felder: %s" % (bewegt or "keine"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())