"""Doppelte und vergebene Nummern in MaxHirn/Archiv/TASKS.md finden (nur lesend).

Warum es das gibt: parallele Sitzungen vergeben die naechste Nummer unabhaengig
voneinander (`max+1`) und treffen denselben Wert. Am 29.09.2026 waren T-139,
T-142, T-145, T-153 und T-156 je ZWEIMAL vergeben - zwei verschiedene Aufgaben
unter einer Nummer, und Verweise aus Notizen zeigen auf die falsche.

Ausgabe:
  * hoechste vergebene Nummer und die naechsten freien
  * jede doppelte Nummer mit Titel, Abschnitt, Angelegt-Datum und Zeile je Block
    (der JUENGERE Eintrag weicht, der aeltere behaelt seine Nummer)
  * Abschnitte der Datei (## Offen / ## Erledigt) - fehlt einer, ist die Liste
    nach einem Umbau kaputt

Aufruf durch das `terminal`-Werkzeug (Standardpfad = Repo-Wurzel):
    python Agenten/Hermes/skills/aufgabenliste-pflegen/scripts/doppelte_nummern.py
    (... --pfad <datei>)      andere Datei pruefen
    (... --ruhig)             nur Zahlen, fuer Skripte

Rueckgabewert: 0 = jede Nummer genau einmal, 1 = Doppelte oder fehlender
Abschnitt gefunden (fuer einen Waechter geeignet).
"""

import argparse
import os
import re
import sys

# Das Statuszeichen ist KEIN [ x]: die Datei traegt auch [?] (wartet),
# [!] (wichtig) und [✓]. Das alte Musst `\[[ x]\]` uebersah damit 26 Eintraege
# und meldete T-318 als hoechste Nummer, wo doch T-330 dasteht - ein Pruefer,
# der gruen meldet und dabei den halben Bestand nicht liest. Die Leerstelle
# nach dem Zeichen ist optional (in der Datei stehen ein und drei).
KOPF = re.compile(r"^- \[[ x?!✓]\]\s*\*\*(T-\d+)\s*[—-]?\s*(.*?)\*\*", re.M)
ABSCHNITT = re.compile(r"^##\s+(.+)$", re.M)
DATUM = re.compile(r"Angelegt:?\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})")


def zerlege(text):
    """Bloccke in Reihenfolge: (zeile, nummer, titel, abschnitt, angelegt, blocktext)."""
    abschnitte = [(m.start(), m.group(1).strip()) for m in ABSCHNITT.finditer(text)]

    def abschnitt_bei(pos):
        treffer = [n for s, n in abschnitte if s <= pos]
        return treffer[-1] if treffer else "(ohne)"

    bloecke = []
    # Zeilen in einem ```-Zaun sind VORLAGE, keine Aufgabe: die Datei zeigt ihre
    # Eintragsform in einem Code-Block, und eine Vorlage mit einer echten Nummer
    # wuerde sonst als Kollision gemeldet (T-001 'Kurztitel' im Abschnitt Offen).
    zaun = [False] * (text.count("\n") + 1)
    offen = False
    for i, zeile in enumerate(text.split("\n")):
        if zeile.lstrip().startswith("```"):
            offen = not offen
            zaun[i] = True
            continue
        zaun[i] = offen
    treffer = [m for m in KOPF.finditer(text)
               if not zaun[max(0, text[:m.start()].count("\n"))]]
    for i, m in enumerate(treffer):
        ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
        block = text[m.start():ende]
        d = DATUM.search(block)
        bloecke.append({
            "zeile": text[:m.start()].count("\n") + 1,
            "nummer": m.group(1),
            "titel": m.group(2).strip().rstrip("*").strip(),
            "abschnitt": abschnitt_bei(m.start()),
            "angelegt": d.group(1) if d else "",
        })
    return bloecke, [n for _, n in abschnitte]


def zahl(nummer):
    return int(nummer.split("-")[1])


def pruefe(pfad, ruhig=False):
    with open(pfad, "rb") as f:
        roh = f.read()
    text = roh.decode("utf-8")
    bloecke, abschnitte = zerlege(text)
    nach_nummer = {}
    for b in bloecke:
        nach_nummer.setdefault(b["nummer"], []).append(b)
    doppelt = {n: bs for n, bs in nach_nummer.items() if len(bs) > 1}
    hoechste = max((zahl(n) for n in nach_nummer), default=0)
    # Erwaehnungen zaehlen: eine Nummer kann ausser im eigenen Block auch als
    # Verweis in fremden Bloecken stehen - dann ist sie NICHT doppelt, sondern
    # nur oft genannt. Beides muss man unterscheiden koennen.
    refs = {n: text.count(n) for n in list(nach_nummer) + list(doppelt)}

    if not ruhig:
        print("%s: %d Bloecke, CRLF %s" % (os.path.basename(pfad), len(bloecke),
                                          "ja" if b"\r\n" in roh else "NEIN"))
        print("Abschnitte: %s" % ", ".join(abschnitte) if abschnitte else "Abschnitte: KEINE")
        print("hoechste Nummer: T-%d" % hoechste)
        print("naechste freie: " + ", ".join(
            "T-%d" % n for n in range(hoechste + 1, hoechste + 1 + len(doppelt) + 3)
            if "T-%d" % n not in nach_nummer))
    fehlt = [a for a in ("Offen", "Erledigt") if not any(a == x for x in abschnitte)]
    if fehlt:
        print("FEHLT: Abschnitt %s" % ", ".join("## " + f for f in fehlt))
    for nummer in sorted(doppelt, key=zahl):
        bs = doppelt[nummer]
        print("" if ruhig else "\nDOPPELT %s (%dx)" % (nummer, len(bs)))
        if ruhig:
            print("doppelt %s: %s" % (nummer, " | ".join(b["titel"][:40] for b in bs)))
            continue
        for b in bs:
            print("  Zeile %-5d %-10s angelegt %-12s %s  (Nummer %dx im Text)" % (
                b["zeile"], b["abschnitt"], b["angelegt"] or "(kein Datum)",
                b["titel"][:60], refs.get(b["nummer"], 0)))
        print("  -> der juengere Eintrag weicht (neue Nummer ab T-%d), der aeltere behaelt %s"
              % (hoechste + 1, nummer))

    if not doppelt and not fehlt:
        print("OK: jede Nummer genau einmal, beide Abschnitte vorhanden")
        return 0
    return 1


def main(argv=None):
    hier = os.path.dirname(os.path.abspath(__file__))
    wurzel = os.path.abspath(os.path.join(hier, "..", "..", "..", "..", ".."))
    standard = os.path.join(wurzel, "MaxHirn", "Archiv", "TASKS.md")
    p = argparse.ArgumentParser(description="Doppelte Nummern in TASKS.md finden")
    p.add_argument("--pfad", default=standard)
    p.add_argument("--ruhig", action="store_true")
    a = p.parse_args(argv)
    if not os.path.exists(a.pfad):
        print("Datei fehlt: %s" % a.pfad)
        return 2
    return pruefe(a.pfad, a.ruhig)


if __name__ == "__main__":
    sys.exit(main())
