"""Stoerungen von Handelsrunden trennen - fuer die Kennzahlen UND die Fehlersuche.

Warum das noetig ist: ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung.
Er entsteht, weil der Dauerlauf laenger stand als die Herzschlagregel erlaubt,
und der Waechter die Spur flachstellt. Diese Zeile landet trotzdem im Journal
und wird von jeder Zaehlung als "Runde" mitgezaehlt.

Belegter Schaden (Stand 15.09.2026):
  xperp   23 Ausstiege, davon 12 herzschlag_alt  -> faktisch 11 Handelsrunden
  kraken  10 Ausstiege, davon  8 herzschlag_alt  -> faktisch  2 Handelsrunden
  swap     5 Ausstiege, davon  1 herzschlag_alt  -> faktisch  4 Handelsrunden
Wer diese Zeilen gegen die Freigabebedingung papierlauf_min_runden 50 zaehlt,
misst Stoerungen statt Strategie.

DIESE DATEI RECHNET NICHTS NACH und schreibt nichts. Sie liest die Journale
und teilt die Ausstiege ein. Die Unterscheidung gehoert ausserdem in jede
Auswertung: eine Trefferquote, in der Zwangsschluesse mitzaehlen, ist zu
niedrig (die Zwangsschluesse sitzen meist im Verlust) - und die Rundenzahl ist
zu hoch.

DIE RICHTUNG DER VERZERRUNG IST NICHT VORHERSAGBAR, deshalb wird BEIDES gezeigt
und nichts still weggelassen: bei kraken waren die Zwangsschluesse +4,59 EUR
POSITIV und die zwei echten Runden -4,50 EUR negativ (das Buch sah geschminkt
aus), bei xperp umgekehrt, aber schwaecher: 11 Handelsrunden +39,50 USD
gegen 12 Stoerungen +4,73 USD, je Runde +3,59 gegen +1,92. Eine Bilanz, die
nur eine der beiden Zahlen nennt, haengt von der Vorfallshistorie ab.

WO DIE TRENNUNG GILT - und wo ausdruecklich nicht:
  Kennzahlen - Rundenzahl, Trefferquote, Erwartungswert: nur Handelsrunden
  (`teile_runden`, unten).
  Kapitalkurve - Drawdown-Ratsche, Kill-Switch: ALLE Buchungen. Ein
  Zwangsschluss ist gebucht und hat Geld bewegt.

Aufruf:
  python stoerungen.py              Uebersicht je Spur + Liste
  python stoerungen.py --liste      nur die Stoerungen, chronologisch
"""

import argparse
import collections
import csv
import datetime as dt
import os

HANDEL = os.path.dirname(os.path.abspath(__file__))

# Ausstieg heisst je Spur anders - das ist die einzige Stelle, an der die
# Schreibweisen stehen muessen.
AUSSTIEG = {"schliessen", "verkauf", "AUSSTIEG", "ausstieg"}
EINSTIEG = {"eroeffnen", "kauf", "KAUF", "EINSTIEG", "einstieg"}

# Kein Handel, nur Betrieb: Funding, Rollover, Herzschlagmeldungen.
BETRIEB = {"funding", "rollover", "zyklus", "quotes"}

# Woran eine Stoerung zu erkennen ist. "herzschlag" trifft herzschlag,
# herzschlag_alt und jede spaetere Schreibweise mit demselben Wort.
STOERUNG_MERKMAL = ("herzschlag", "zwangsschluss", "notaus")

# Zweite Klasse derselben Sache: BUCHHALTUNGS-Korrekturen. Sie sind weder
# Handelsentscheidung noch Waechter-Reaktion, sondern eine Bereinigung des
# Buchs - eine Position ohne echte Order (Papier-Altlast im Live-Buch) wird
# ausgebucht (scanner/handeln.bueche_papier_altlasten_aus, Muster
# buchbereinigung.py). Fuer jede Zaehlung gilt dasselbe wie fuer eine Stoerung:
# das ist keine Runde. Eigener Name, weil die Ursache eine andere ist - wer die
# Fehlersuche macht, soll sehen, WELCHE der beiden Klassen vorliegt.
BUCHHALTUNG = ("buchbereinigung",)


def ist_stoerung(grund):
    g = (grund or "").strip().lower()
    return any(m in g for m in STOERUNG_MERKMAL + BUCHHALTUNG)


def teile_runden(runden):
    """(echt, stoerungen) - fertige Runden nach ihrem Grund trennen.

    Die EINE Fassung des Merkmals steht oben in `ist_stoerung`; Auswertungen und
    Wachen holen sie ueber diese Funktion, statt das Wort noch einmal zu
    schreiben. `runden` sind Dicts mit dem Feld `grund` - so liefert sie
    `scanner/wachen_pruefung.runden_aus_journal` und so baut sie
    `auswertung_alle._paare`.

    Die Trennung gilt fuer KENNZAHLEN (Rundenzahl, Trefferquote, Erwartungswert)
    - ausdruecklich NICHT fuer die Kapitalkurve. Ein Zwangsschluss ist gebucht
    und hat Geld bewegt; wer ihn aus Drawdown und Kill-Switch nimmt, schoenet
    genau das Risiko, gegen das die Sicherung gebaut ist.
    """
    echt, stoer = [], []
    for r in runden or []:
        (stoer if ist_stoerung((r or {}).get("grund")) else echt).append(r)
    return echt, stoer


def zeilen(spur):
    p = os.path.join(HANDEL, spur, "handelsjournal.csv")
    if not os.path.isfile(p):
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def teile(spur):
    """(echt, stoerung) - zwei Listen von Ausstiegszeilen.

    Eine Zeile zaehlt nur als Ausstieg, wenn die aktion-Spalte es sagt. Die
    funding-/rollover-Zeilen der Kontraktspuren sind kein Handel und wuerden
    jede Trefferquote verzerren.
    """
    echt, stoer = [], []
    for z in zeilen(spur):
        akt = (z.get("aktion") or "").strip()
        if akt not in AUSSTIEG and akt not in ("",):
            continue
        if akt == "" and not z.get("ausgang"):
            continue
        g = z.get("grund") or z.get("ausgang") or ""
        (stoer if ist_stoerung(g) else echt).append(z)
    return echt, stoer


def wann(z):
    t = z.get("zeit") or ""
    return t[:16].replace("T", " ") if t else "?"


def tag(z):
    t = z.get("zeit") or ""
    return t[:10] if t else "?"


def uebersicht():
    print("%-12s %7s %8s %8s %8s" %
          ("Spur", "Zeilen", "Ausstieg", "echt", "Stoerung"))
    print("-" * 50)
    gesamt = [0, 0]
    for spur in sorted(os.listdir(HANDEL)):
        if not os.path.isdir(os.path.join(HANDEL, spur)):
            continue
        alle = zeilen(spur)
        if not alle:
            continue
        echt, stoer = teile(spur)
        if not echt and not stoer:
            continue
        gesamt[0] += len(echt)
        gesamt[1] += len(stoer)
        marke = ""
        if stoer and len(stoer) >= len(echt):
            marke = "  <- Kennzahl unbrauchbar"
        print("%-12s %7d %8d %8d %8d%s" %
              (spur, len(alle), len(echt) + len(stoer), len(echt), len(stoer),
               marke))
    print("-" * 50)
    print("%-12s %7s %8s %8d %8d" % ("Summe", "", "", gesamt[0], gesamt[1]))
    print()
    print("  Kennzahlen (Trefferquote, Rundenzahl) gehoeren auf die Spalte")
    print("  'echt'. Die Stoerungen stehen darunter, nicht darin.")


def liste():
    alle = []
    for spur in sorted(os.listdir(HANDEL)):
        if not os.path.isdir(os.path.join(HANDEL, spur)):
            continue
        _, stoer = teile(spur)
        for z in stoer:
            alle.append((z.get("zeit") or "", spur, z))
    alle.sort(key=lambda x: (x[0], x[1]))
    if not alle:
        print("keine Stoerungen im Journal")
        return
    print("Stoerungen chronologisch (%d) - die Haeufung IST die Fehlersuche:"
          % len(alle))
    print()
    print("%-17s %-12s %-22s %s" % ("Zeit (UTC)", "Spur", "Instrument", "Grund"))
    print("-" * 70)
    for zeit, spur, z in alle:
        inst = (z.get("inst") or z.get("paar") or "?")[:22]
        print("%-17s %-12s %-22s %s" %
              (zeit[:16].replace("T", " "), spur, inst, z.get("grund")))
    print()
    je_tag = collections.Counter(tag(z) for _, _, z in alle)
    print("  Nach Tag:")
    for t, n in sorted(je_tag.items()):
        print("    %s  %2d Stoerung(en)" % (t, n))
    je_spur = collections.Counter(s for _, s, _ in alle)
    print("  Nach Spur:")
    for s, n in je_spur.most_common():
        print("    %-12s %2d" % (s, n))


def main():
    p = argparse.ArgumentParser(description="Stoerungen von Handelsrunden trennen")
    p.add_argument("--liste", action="store_true", help="nur die Stoerungen")
    a = p.parse_args()
    if a.liste:
        liste()
    else:
        uebersicht()
        print()
        liste()


if __name__ == "__main__":
    main()
