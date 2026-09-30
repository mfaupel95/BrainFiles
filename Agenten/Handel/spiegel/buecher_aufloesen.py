"""Die drei Spiegel-Buecher aufloesen (Max, 01.10.2026: "ja weg mit spiegel").

WARUM: Die Arme sind seit 01.10. aus dem Dauerlauf. Beim kurzen Wiederanschalten
hat ein Zyklus die alten Positionen abgewickelt und NEUE eroeffnet (6/3/3) -
die stehen jetzt als offene Karteileichen im Buch und werden nie geschlossen,
weil niemand mehr dafuer zustaendig ist.

WAS DAS SKRIPT TUT, je Buch:
  1. Sicherung von zustand*.json und handelsjournal*.csv (.bak-20261001).
  2. Je offener Position eine Journalzeile "papier,schliessen,...,buchbereinigung"
     mit dem EINSTIEGSPREIS - also NEUTRAL (Wert = Einsatz), damit die
     Buchbereinigung die Bilanz nicht veraendert.
  3. positionen = [] im Zustand.

WAS ES NICHT TUT: Die Journals und die Historie bleiben stehen (2.432 Zeilen im
Hauptbuch sind Daten, keine Karteileichen). Nichts wird geloescht. Die
Q:-Kopie bleibt unberuehrt - sie ist eine Ausser-Haus-Sicherung, kein Zustand.

journal_zweitziel wird mitgeschrieben, falls gesetzt; sonst bleibt es leer.
"""
import csv
import datetime as dt
import json
import os
import shutil

HIER = os.path.dirname(os.path.abspath(__file__))
GEBUEHR = ""

FELDER = ["zeit", "modus", "aktion", "kette", "wallet", "token", "symbol", "preis",
          "menge", "einsatz_usd", "wert_usd", "marktkap_usd", "slippage_pct",
          "gebuehr_pct", "grund"]

BUECHER = [
    ("zustand.json", "handelsjournal.csv"),
    ("zustand.knapp.json", "handelsjournal.knapp.csv"),
    ("zustand.weit.json", "handelsjournal.weit.csv"),
]


def _zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return 0.0


def aufloesen(zustand_pfad, journal_pfad, anwenden):
    with open(zustand_pfad, encoding="utf-8") as f:
        zustand = json.load(f)
    offen = zustand.get("positionen") or []
    if not offen:
        print("  %-24s schon leer" % os.path.basename(zustand_pfad))
        return 0

    if anwenden:
        shutil.copy2(zustand_pfad, zustand_pfad + ".bak-20261001")
        if os.path.exists(journal_pfad):
            shutil.copy2(journal_pfad, journal_pfad + ".bak-20261001")

        jetzt = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        with open(journal_pfad, "a", newline="", encoding="utf-8") as f:
            schreiber = csv.DictWriter(f, fieldnames=FELDER)
            for p in offen:
                preis = _zahl(p.get("preis_einstieg"))
                einsatz = _zahl(p.get("einsatz_usd"))
                schreiber.writerow({
                    "zeit": jetzt,
                    "modus": "papier",
                    "aktion": "schliessen",
                    "kette": p.get("kette") or "",
                    "wallet": p.get("wallet") or "",
                    "token": p.get("token") or "",
                    "symbol": p.get("symbol") or "",
                    # Einstiegspreis = neutral: die Buchbereinigung darf die
                    # Bilanz nicht veraendern, es gab keinen Verkauf.
                    "preis": repr(preis),
                    "menge": p.get("menge") or "",
                    "einsatz_usd": einsatz,
                    "wert_usd": einsatz,
                    "marktkap_usd": "",
                    "slippage_pct": "",
                    "gebuehr_pct": GEBUEHR,
                    "grund": "buchbereinigung",
                })

        zustand["positionen"] = []
        zustand["buchbereinigung"] = {
            "zeit": jetzt,
            "anzahl": len(offen),
            "grund": "spiegel stillgelegt (Max, 01.10.2026)",
        }
        with open(zustand_pfad, "w", encoding="utf-8") as f:
            json.dump(zustand, f, ensure_ascii=False, indent=2)

    print("  %-24s %2d Positionen -> %s"
          % (os.path.basename(zustand_pfad), len(offen),
             "ausgetragen" if anwenden else "auszutragen (Trockenlauf)"))
    return len(offen)


def main():
    import sys
    anwenden = "--anwenden" in sys.argv
    print("Buecher aufloesen%s" % ("" if anwenden else " (TROCKENLAUF)"))
    gesamt = 0
    for zustand_datei, journal_datei in BUECHER:
        zp = os.path.join(HIER, zustand_datei)
        if not os.path.exists(zp):
            print("  %-24s fehlt" % zustand_datei)
            continue
        gesamt += aufloesen(zp, os.path.join(HIER, journal_datei), anwenden)
    print("Summe: %d Positionen" % gesamt)
    if not anwenden:
        print("Mit --anwenden schreiben.")


if __name__ == "__main__":
    main()
