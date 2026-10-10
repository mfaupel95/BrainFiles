"""Korrigiert die Handschliessungen im xperp-Journal, die vor dem Fix in
xperp/handeln.py (_hand_erloes, 07.10.2026) mit margin_usd = nominal_usd =
Kurs * Kontrakte gebucht wurden.

Standard ist ein TROCKENLAUF: zeigt nur, welche Zeilen sich aendern.
Schreiben erst mit --schreiben; vorher wird eine Sicherung
handelsjournal.csv.bak-<datum> neben das Journal gelegt.

    python journal_korrektur_xperp.py              # nur anzeigen (aus xperp/)
    python journal_korrektur_xperp.py --schreiben  # sichern + korrigieren
    python journal_korrektur_xperp.py --journal <pfad>   # anderes Journal

Gefunden werden die Zeilen ueber pos_id und die Fehlersignatur (aktion
schliessen, grund verkauf_von_hand, nominal_usd == margin_usd und weit weg vom
Sollwert), nicht ueber Zeilennummern. Sollwert wie _hand_erloes: Margin +
Nominal * Kursbewegung (Short mit umgekehrtem Vorzeichen), beides aus der
Eroeffnungszeile derselben pos_id. Das Journal ist CRLF; nur die betroffenen
Zeilen werden ersetzt, alles andere bleibt Byte fuer Byte. Haengt der Dauerlauf
waehrend des Laufs eine Zeile an, wird neu gelesen (bis 5 Versuche).
"""
import argparse
import csv
import io
import os
import shutil
import sys
import time
from datetime import date

# Das Skript liegt neben dem Journal (Agenten/Handel/xperp/).
JOURNAL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "handelsjournal.csv")
GRUENDE = ("verkauf_von_hand", "verkauf_ohne_zeuge_neutral")


def korrigiere(raw):
    zeilen = raw.decode("utf-8").split("\r\n")
    kopf = next(csv.reader([zeilen[0]]))
    ix = {k: i for i, k in enumerate(kopf)}
    op = {}
    for z in zeilen[1:]:
        if z:
            r = next(csv.reader([z]))
            if r[ix["aktion"]] == "eroeffnen" and r[ix["pos_id"]]:
                op[r[ix["pos_id"]]] = r
    aend = []
    for n, z in enumerate(zeilen):
        if n == 0 or not z:
            continue
        r = next(csv.reader([z]))
        if r[ix["aktion"]] != "schliessen" or r[ix["grund"]] not in GRUENDE:
            continue
        o = op.get(r[ix["pos_id"]])
        if not o or r[ix["nominal_usd"]] != r[ix["margin_usd"]]:
            continue
        nom = float(o[ix["nominal_usd"]])
        mar = float(o[ix["margin_usd"]])
        vz = 1 if o[ix["seite"]] == "long" else -1
        ep = float(o[ix["preis"]])
        soll = mar + nom * vz * (float(r[ix["preis"]]) - ep) / ep
        if abs(float(r[ix["margin_usd"]]) - soll) < max(1.0, 0.05 * abs(soll)):
            continue                                   # schon plausibel
        alt = (r[ix["nominal_usd"]], r[ix["margin_usd"]])
        r[ix["nominal_usd"]] = "%.2f" % nom
        r[ix["margin_usd"]] = "%.2f" % soll
        buf = io.StringIO()
        csv.writer(buf, lineterminator="").writerow(r)
        zeilen[n] = buf.getvalue()
        aend.append((n + 1, r[ix["inst"]], r[ix["pos_id"]], alt,
                     (r[ix["nominal_usd"]], r[ix["margin_usd"]])))
    return "\r\n".join(zeilen).encode("utf-8"), aend


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--schreiben", action="store_true")
    p.add_argument("--journal", default=JOURNAL,
                   help="Standard: handelsjournal.csv neben dem Skript")
    a = p.parse_args()
    journal = a.journal
    for _ in range(5):
        raw = open(journal, "rb").read()
        neu, aend = korrigiere(raw)
        if os.path.getsize(journal) != len(raw):
            time.sleep(1)
            continue
        break
    else:
        sys.exit("Journal aendert sich ununterbrochen - nichts geschrieben")
    for z in aend:
        print("Zeile %d  %s  %s\n    ist  nominal/margin %s / %s\n    soll nominal/margin %s / %s"
              % (z[0], z[1], z[2], z[3][0], z[3][1], z[4][0], z[4][1]))
    print("%d Zeile(n) betroffen." % len(aend))
    if not aend or not a.schreiben:
        if aend:
            print("Trockenlauf - mit --schreiben ausfuehren.")
        return
    sicherung = journal + ".bak-" + date.today().strftime("%Y%m%d")
    shutil.copy2(journal, sicherung)
    if os.path.getsize(journal) != len(raw):
        sys.exit("Journal hat sich seit dem Lesen geaendert - nichts geschrieben "
                 "(Sicherung liegt: %s)" % sicherung)
    open(journal, "wb").write(neu)
    print("Geschrieben. Sicherung: %s" % sicherung)


if __name__ == "__main__":
    main()
