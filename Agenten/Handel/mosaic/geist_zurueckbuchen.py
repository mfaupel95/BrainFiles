"""Die echte BTC-Position zurueck ins Buch holen (Befund 23.09.2026).

WAS PASSIERT IST
  Das Freigabefenster lief am 23.09.2026 um 19:29 ab; der Zyklus 19:33:43 lief
  deshalb PAPIER. Dieser Papierzweig buchte die ECHTE Position BTC-USDC
  (modus=live) mit grund=ziel aus dem Buch. An der Boerse blieb sie offen:

      XXBT       0.00066027   (Kraken-Guthaben, 23.09.2026)
      Stop-Algo  O3QKG4-P6QVQ-6SLH5V   sell 0.00066027 XBTEUR @ 71940.1

  Beweis: das Journal hat KEINEN Live-Verkauf - die letzte BTC-Zeile ist
  'papier,verkauf,BTC-USDC ... ziel'. Ein Papierverkauf bewegt nichts.

WAS DIESES SKRIPT TUT
  1. Die Position mit den BOERSENWERTEN zurueck ins Buch (modus=live) - danach
     entscheidet der Live-Zweig wieder regulaer: der Kurs (84088.80 am
     23.09.2026) liegt ueber dem Ziel 83299.04, also verkauft der naechste
     Live-Zyklus echt.
  2. Die Falschbuchung (papier/verkauf) wandert in eine Sicherungsdatei
     `handelsjournal.verworfen-JJJJMMTT.csv` und wird durch eine
     'live,anpassen,buch_nachgezogen_boerse'-Zeile ersetzt (Auswertungen
     paaren nur kauf/verkauf - 'anpassen' stoert keine Runde).

Vorschau ist der Standard, geschrieben wird nur mit --anwenden. Vorher wird
das Journal als .bak-JJJJMMTT kopiert.
"""

import argparse
import csv
import json
import os
import shutil
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
ZUSTAND = os.path.join(HIER, "zustand.json")
JOURNAL = os.path.join(HIER, "handelsjournal.csv")

# Belegte Werte: Kaufzeile im Journal + Kraken-Guthaben/OpenOrders vom
# 23.09.2026. Nichts davon ist geschaetzt.
POSITION = {
    "inst": "BTC-USDC", "seite": "long", "einstieg": 75726.4,
    "stop": 71940.08, "ziel": 83299.04, "stop_pct": 5.0,
    "nominal": 50.0, "menge": 0.00066027,
    "modus": "live", "kauf_ord_id": "",                     # Kraken-TxID nie im Journal gefuehrt
    "stop_algo_id": "O3QKG4-P6QVQ-6SLH5V",
    "boersen_stop_fehlt": False,
    "eroeffnet_zeit": "2026-09-23T01:08:20+00:00",
    "_quelle": "boerse_nachzug 23.09.2026 (XXBT 0.00066027 + Stop-Algo O3QKG4)",
}
FALSCHE_ZEILE = "2026-09-23T17:33:43+00:00"


def _jetzt():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anwenden", action="store_true",
                    help="wirklich schreiben (sonst nur zeigen)")
    a = ap.parse_args()

    with open(ZUSTAND, "rb") as f:
        roh = f.read()
    crlf = b"\r\n" in roh
    z = json.loads(roh.decode("utf-8"))
    vorhanden = [p for p in z.get("positionen", [])
                 if p.get("inst") == POSITION["inst"] and p.get("modus") == "live"]
    print("Buch zeigt %d Position(en), davon %d live-%s"
          % (len(z.get("positionen", [])), len(vorhanden), POSITION["inst"]))

    with open(JOURNAL, "rb") as f:
        roh_j = f.read()
    crlf_j = b"\r\n" in roh_j
    zeilen = roh_j.decode("utf-8").splitlines()
    falsch = [i for i, t in enumerate(zeilen) if t.startswith(FALSCHE_ZEILE)]
    print("Journal: %d Zeile(n) mit Zeitstempel %s" % (len(falsch), FALSCHE_ZEILE))
    for i in falsch:
        print("  " + zeilen[i])

    if vorhanden:
        print("Nichts zu tun: die Position steht schon im Buch.")
        return 0
    if not falsch:
        print("Keine Falschbuchung gefunden - nichts angefasst.")
        return 1

    print("\nVorschlag:")
    print("  Position zurueckbuchen: %s %s Menge %s Einstieg %.2f Stop %.2f "
          "Ziel %.2f" % (POSITION["inst"], POSITION["seite"], POSITION["menge"],
                         POSITION["einstieg"], POSITION["stop"], POSITION["ziel"]))
    print("  Falschbuchung ersetzen durch: live,anpassen,buch_nachgezogen_boerse")

    if not a.anwenden:
        print("\nTrockenlauf - nichts geschrieben (--anwenden schreibt).")
        return 0

    stempel = datetime.now().strftime("%Y%m%d")
    shutil.copy2(JOURNAL, JOURNAL + ".bak-" + stempel)
    shutil.copy2(ZUSTAND, ZUSTAND + ".bak-" + stempel)

    z.setdefault("positionen", []).append(POSITION)
    z["_nachzug"] = ("23.09.2026: BTC-USDC live zurueckgebucht (Papierzweig hatte "
                     "sie faelschlich verkauft, an der Boerse lag sie offen)")
    text = json.dumps(z, indent=2, ensure_ascii=False) + "\n"
    if crlf:
        text = text.replace("\n", "\r\n")
    with open(ZUSTAND, "wb") as f:
        f.write(text.encode("utf-8"))

    ersatz = ("%s,live,anpassen,%s,%s,,,,,,buch_nachgezogen_boerse"
              % (_jetzt(), POSITION["inst"], POSITION["seite"]))
    neu = [t for i, t in enumerate(zeilen) if i not in falsch] + [ersatz]
    with open(JOURNAL + ".verworfen-" + stempel, "wb") as f:
        f.write(("\n".join(zeilen[i] for i in falsch) + "\n").encode("utf-8"))
    jtext = "\n".join(neu) + "\n"
    if crlf_j:
        jtext = jtext.replace("\n", "\r\n")
    with open(JOURNAL, "wb") as f:
        f.write(jtext.encode("utf-8"))

    print("\nGeschrieben: Position im Buch, Falschbuchung nach "
          "handelsjournal.verworfen-%s.csv, Sicherungen .bak-%s" % (stempel, stempel))
    return 0


if __name__ == "__main__":
    sys.exit(main())