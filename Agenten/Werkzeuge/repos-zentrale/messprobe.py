"""Messprobe: passen Spalten, Summenzeile und Befehlsliste in das Fenster?

Kein Test - eine Messung am echten Fenster. Sie beantwortet die Frage
'ist hier etwas abgeschnitten?' mit Zahlen statt mit einem Blick auf ein Bild.
"""

from __future__ import annotations

import sys
from pathlib import Path
from tkinter import font as tkfont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fenster  # noqa: E402

HIER = Path(__file__).resolve().parent


def main() -> int:
    p = dict(
        brainfiles=HIER.parents[2],
        manifest_pfad=HIER / "repos-zentrale.json",
        profile_dir=HIER.parents[1] / "Hermes" / "profiles",
        log_ordner=HIER / "logs",
    )
    f = fenster.Fenster(**p)
    f.root.update()
    f.root.update_idletasks()
    baum = f.baum
    schrift = tkfont.Font(family=fenster.SCHRIFT_ART, size=fenster.SCHRIFT_GROESSE)

    print(f"Fenster {f.root.winfo_width()}x{f.root.winfo_height()}  "
          f"Baum {baum.winfo_width()} px  DPI-Faktor {f.s:.3f}")
    spalten = ["#0"] + [k for k, _, _ in fenster.SPALTEN]
    summe = 0
    for k in spalten:
        b = baum.column(k, "width")
        summe += b
        print(f"   {k:<8} {b:>5} px")
    platz = baum.winfo_width() - 22
    print(f"   Summe   {summe:>5} px   (Platz im Baum: {platz} px) "
          f"{'PASST' if summe <= platz else 'ZU BREIT'}")

    def passt(text: str, spalte: str) -> bool:
        return schrift.measure(text) <= baum.column(spalte, "width") - 8

    kandidaten = []
    for z in f.zeilen:
        h = fenster.hinweis(z) or fenster.ERKLAERUNG.get(z.gruppe, "")
        if h:
            kandidaten.append((schrift.measure(h), len(h), h, z.ordner))
    for kennung, gruppen in fenster.nach_bereichen(f.zeilen).items():
        for gruppe in gruppen:
            for text in (fenster.ERKLAERUNG.get(gruppe, ""),
                         __import__("quellen").BEREICH_ERKLAERUNG.get(kennung, "")):
                if text:
                    kandidaten.append((schrift.measure(text), len(text), text, kennung))
    kandidaten.sort(reverse=True)
    if kandidaten:
        breite, lang, text, wo = kandidaten[0]
        print(f"\nlaengster Hinweistext: {lang} Zeichen / {breite} px -> "
              f"Spalte {baum.column('hinweis', 'width')} px: "
              f"{'PASST' if passt(text, 'hinweis') else 'ZU SCHMAL'}")
        print(f"   ({wo}) {text}")
        zu_schmal = [k for k in kandidaten[:200] if not passt(k[2], "hinweis")]
        print(f"   davon zu schmal: {len(zu_schmal)} von {len(kandidaten)}")

    zeile = f.zusammenfassung["text"]
    lw = f.zusammenfassung.winfo_width()
    print(f"\nSummenzeile: Text {schrift.measure(zeile)} px, Platz {lw} px -> "
          f"{'PASST' if schrift.measure(zeile) <= lw else 'ZU SCHMAL'}")
    print(f"   '{zeile}'")

    bb = f.befehlsbaum
    unten = sum(bb.column(k, "width") for k in ("was", "befehl", "hinweis"))
    print(f"\nBefehlsliste: Summe {unten} px, Widget {bb.winfo_width()} px, "
          f"'Hinweis'-Kopf {schrift.measure('Hinweis')} px in "
          f"{bb.column('hinweis', 'width')} px")
    f.root.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
