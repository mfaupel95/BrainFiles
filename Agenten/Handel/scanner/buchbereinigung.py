"""Einmalige Buchbereinigung fuer scanner: Papier-Altlasten ausbuchen.

WARUM (Auftrag Max, 20.09.2026)
Das scanner-Buch trug 6 offene Positionen, von denen KEINE eine echte
OKX-Order hinter sich hatte (alle kauf_ord_id = null) - sie stammen aus
Papier-Zyklen, waehrend der Modus inzwischen auf "live" steht. Folge:
das Buch war mit 6 von 5 Plaetzen ueberfuellt, der Scanner kaufte auch
live nichts Neues, und jeder Ausstiegsversuch lief in denselben Fehler
wie AVAX (OKX 51020: Menge unter Mindestordergroesse), weil live gar
keine Position existiert.

WAS ES TUT
Jede Position mit kauf_ord_id = null wird zum aktuellen Marktkurs als
PAPIER-Verkauf ausgebucht: Journalzeile mit modus "papier", Grund
"buchbereinigung", echtes G/V. Positionen MIT kauf_ord_id werden
ausdruecklich NICHT angefasst - dort haengt echtes Geld, das gehoert
ueber den normalen Ausstiegspfad geschlossen.

WAS ES NICHT TUT
Keine Order an die Boerse. Kein Loeschen von Journalzeilen - die
Historie bleibt vollstaendig, die Runden zaehlen weiter. Der Q:-Spiegel
wird vom naechsten regulaeren Zyklus nachgezogen.

AUFRUF
    ../scanner/.venv/Scripts/python.exe buchbereinigung.py --vorschau
    ../scanner/.venv/Scripts/python.exe buchbereinigung.py --anwenden
"""

import sys
import os

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import handeln
import okx


def bereinige(anwenden=False):
    z = handeln.lade_zustand()
    positionen = z.get("positionen", [])
    if not positionen:
        print("Buch ist leer - nichts zu tun.")
        return 0

    papier = [p for p in positionen if not p.get("kauf_ord_id")]
    echt = [p for p in positionen if p.get("kauf_ord_id")]

    print("Buch: %d Positionen (%d ohne Order = Papier-Altlast, %d echt)"
          % (len(positionen), len(papier), len(echt)))
    if echt:
        print("NICHT angefasst (echte Order dahinter):")
        for p in echt:
            print("   %s  ord_id=%s" % (p["inst"], p["kauf_ord_id"]))

    if not papier:
        print("Keine Papier-Altlasten - nichts zu tun.")
        return 0

    summe = 0.0
    behalten = list(echt)
    for p in papier:
        kurs = okx.letzter_kurs(p["inst"])
        if kurs is None:
            print("   %-12s KEIN KURS - Position bleibt liegen" % p["inst"])
            behalten.append(p)
            continue
        erloes = p["usd"] * (kurs / p["einstieg"])
        gv = erloes - p["usd"]
        summe += gv
        print("   %-12s Einstieg %.6f -> Kurs %.6f   G/V %+.2f USD"
              % (p["inst"], p["einstieg"], kurs, gv))
        if anwenden:
            handeln.journal(
                handeln._jetzt(), "papier", "verkauf", p["inst"],
                "%.6f" % kurs, "%.2f" % erloes, "", "", "buchbereinigung",
                "%.4f" % p.get("mfe_pct", 0.0),
                "%.4f" % p.get("mae_pct", 0.0),
                handeln._haltetage(p))

    print("Summe G/V: %+.2f USD" % summe)

    if not anwenden:
        print("\nVORSCHAU - nichts geschrieben. Mit --anwenden ausfuehren.")
        return 0

    z["positionen"] = behalten
    handeln.schreibe_zustand(z)
    print("\nGebucht. Buch jetzt: %d Positionen" % len(behalten))
    return 0


if __name__ == "__main__":
    sys.exit(bereinige(anwenden="--anwenden" in sys.argv))
