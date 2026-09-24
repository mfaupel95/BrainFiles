"""Kraken-Positionen (mosaic) auf Stop-Loss 7,5 % unter dem Einstieg stellen.

Auftrag Max 24.09.2026: "Kraken positionen mit stop loss 7,5% ausstatten".

Ablauf je Position (bewusst in DIESER Reihenfolge):
  1. NEUEN Stop-Loss setzen (echt),
  2. pruefen, dass er in den offenen Orders steht,
  3. ERST DANN den alten Stop stornieren.
So ist die Position zu keinem Zeitpunkt ungeschuetzt. Ein kurzes Doppel ist
harmlos: ein Stop-Loss reserviert die Menge nicht, beim Ausloesen fuellt einer
und der andere verfaellt.

Aufruf aus Agenten/Handel:
    scanner/.venv/Scripts/python.exe mosaic/kraken_stops_7_5.py            # nur rechnen
    scanner/.venv/Scripts/python.exe mosaic/kraken_stops_7_5.py --anwenden
"""

import argparse
import importlib.util
import json
import math
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
sys.path.insert(0, os.path.join(HANDEL, "scanner"))
import wachen_pruefung as wp                                       # noqa: E402

ZIEL_PROZENT = 7.5
LOT_STELLEN = 8      # XBTEUR/XETHZEUR/SOLEUR: Kraken nimmt 8 Nachkommastellen


def stop_menge(soll, verfuegbar):
    """Die Menge, die ein Stop-Loss wirklich haben darf.

    Gemessen am 24.09.2026: das Buch fuehrte 0.00066027 BTC, die Brieftasche
    0.0006527067 - die Gebuehr ging vom Zufluss ab. Ein Stop ueber die
    Buchmenge scheitert mit 'EOrder:Insufficient funds', und dann steht die
    Position OHNE Stop da. Deshalb: nie mehr als verfuegbar, abgerundet.
    """
    menge = min(float(soll), float(verfuegbar))
    faktor = 10 ** LOT_STELLEN
    return math.floor(menge * faktor) / faktor
ZUSTAND = os.path.join(HIER, "zustand.json")
WACHEN = os.path.join(HIER, "wachen.json")


VERMOEGEN = {"XXBTZEUR": "XXBT", "XETHZEUR": "XETH", "SOLEUR": "SOL"}

# Kraken nennt DASSELBE Paar zweimal verschieden: in der Order-Anfrage
# "XXBTZEUR"/"XETHZEUR", in der offenen Order (descr.pair) "XBTEUR"/"ETHEUR".
# Ein Vergleich der rohen Zeichenketten haelt ein geschuetztes Paar deshalb fuer
# ungeschuetzt (Falle aus mosaic/stops_nachziehen.py, 24.09.2026).
_ALIAS = {"XBT": "BTC", "XXBT": "BTC", "XETH": "ETH", "XXDG": "DOGE",
          "XDG": "DOGE", "XXLM": "XLM", "XXRP": "XRP"}


def normal(paar):
    """(Basis, Quote) - die einzige Form, in der zwei Paarschreibweisen passen."""
    p = str(paar or "").upper()
    if len(p) > 3:
        for kurz, lang in (("ZUSD", "USD"), ("ZEUR", "EUR"), ("ZUSDT", "USDT"),
                           ("ZUSDC", "USDC")):
            if p.endswith(kurz):
                basis, quote = p[:-len(kurz)], lang
                break
        else:
            for kurz, lang in (("USDT", "USDT"), ("USDC", "USDC"),
                               ("EUR", "EUR"), ("USD", "USD")):
                if p.endswith(kurz):
                    basis, quote = p[:-len(kurz)], lang
                    break
            else:
                return (p, "")
        return (_ALIAS.get(basis, basis), quote)
    return (p, "")


def _lade(name, pfad):
    schluessel = "%s@%s" % (name, os.path.abspath(pfad))
    if schluessel in sys.modules:
        return sys.modules[schluessel]
    spec = importlib.util.spec_from_file_location(schluessel, pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules[schluessel] = m
    spec.loader.exec_module(m)
    return m


kraken = _lade("kraken", os.path.join(HANDEL, "kraken", "kraken.py"))
kraken_spot = _lade("kraken_spot", os.path.join(HIER, "kraken_spot.py"))


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--anwenden", action="store_true",
                   help="wirklich ordern (sonst nur rechnen)")
    p.add_argument("--nur-buch", action="store_true",
                   help="Buch aus den OFFENEN Orders nachziehen, nichts ordern")
    a = p.parse_args()

    with open(ZUSTAND, encoding="utf-8") as f:
        z = json.load(f)
    live = [q for q in z.get("positionen", []) if q.get("modus") == "live"]
    if not live:
        print("Keine Live-Position im Buch - nichts zu tun.")
        return 0

    offen = kraken.offene_orders()

    if a.nur_buch:
        for pos in live:
            paar = kraken_spot.PAARE.get(pos.get("inst"))
            treffer = [tx for tx, o in offen.items()
                       if normal(o["paar"]) == normal(paar)
                       and o["art"] == "stop-loss"]
            if not treffer:
                print("%-10s KEIN Stop an der Boerse - Buch bleibt unberuehrt"
                      % pos["inst"])
                continue
            tx = treffer[0]
            pos["stop"] = float(offen[tx]["preis"])
            pos["stop_txid"] = tx
            pos["menge"] = float(offen[tx]["menge"])
            print("%-10s Stop %s auf %s, Menge %s"
                  % (pos["inst"], tx, pos["stop"], pos["menge"]))
        with open(ZUSTAND, "w", encoding="utf-8", newline=chr(10)) as f:
            json.dump(z, f, indent=2, ensure_ascii=False)
            f.write(chr(10))
        with open(WACHEN, encoding="utf-8") as f:
            ziel = json.load(f).get("journal_zweitziel")
        ok, info = wp.spiegele_journal([ZUSTAND], ziel)
        print("Spiegelung: %s" % ("ok" if ok else "FEHLER " + str(info)))
        return 0

    geaendert = []
    for pos in live:
        paar = kraken_spot.PAARE.get(pos.get("inst"))
        if not paar:
            print("%-10s kein Kraken-Paar im Abbild - uebersprungen" % pos["inst"])
            continue
        einstieg = float(pos["einstieg"])
        menge = stop_menge(pos["menge"], kraken.guthaben(
            VERMOEGEN.get(paar, "")))
        kurs = kraken.letzter_kurs(paar)
        neu = float(kraken.preis_gerundet(paar, einstieg * (1 - ZIEL_PROZENT / 100.0),
                                          richtung="auf"))
        alt_txid = pos.get("stop_txid")
        alt_preis = float(pos.get("stop") or 0)
        print("%-10s %-10s Einstieg %-10s Stop alt %-9s -> neu %-9s "
              "(%+.2f %% unter dem Kurs %s)"
              % (pos["inst"], paar, einstieg, alt_preis, neu,
                 (neu / kurs - 1) * 100, kurs))
        if neu >= kurs:
            print("   ABBRUCH: der neue Stop liegt nicht unter dem Kurs")
            return 1
        if abs(neu - alt_preis) < 1e-9:
            print("   unveraendert")
            continue
        if not a.anwenden:
            continue
        # Kraken RESERVIERT die Menge fuer einen Stop-Loss: ein zweiter Stop auf
        # dieselbe Menge scheitert mit "EOrder:Insufficient funds" (gemessen
        # 24.09.2026). Deshalb bleibt nur: alten Stop stornieren, neuen setzen -
        # und wenn das Setzen scheitert, den ALTEN sofort wiederherstellen, damit
        # die Position nicht ungeschuetzt stehen bleibt.
        if alt_txid and alt_txid in offen:
            kraken.order_stornieren(alt_txid)
            print("   alter Stop %s storniert" % alt_txid)
        try:
            antwort = kraken.stop_setzen(paar, menge, neu, echt=True)
        except Exception as e:                                    # noqa: BLE001
            print("   FEHLER beim Setzen (%s) - alten Stop wiederherstellen" % e)
            kraken.stop_setzen(paar, menge, alt_preis, echt=True)
            return 1
        neu_txid = None
        if isinstance(antwort, dict):
            neu_txid = (antwort.get("txid") or [None])[0]
        print("   neuer Stop gesetzt: %s" % neu_txid)
        geaendert.append((pos, neu, neu_txid, alt_txid))

    if not a.anwenden:
        print("\nVORSCHAU - keine Order gestellt. Mit --anwenden ausfuehren.")
        return 0
    if not geaendert:
        print("\nNichts zu tun.")
        return 0

    # Erst pruefen, dann die alten Stornos - sonst waere die Position kurz ohne Stop.
    kontrolle = kraken.offene_orders()
    for pos, neu, neu_txid, alt_txid in geaendert:
        if neu_txid not in kontrolle:
            print("WARNUNG: %s nicht in den offenen Orders - alter Stop BLEIBT"
                  % neu_txid)
            continue
        if alt_txid and alt_txid in kontrolle:
            kraken.order_stornieren(alt_txid)
            print("   alter Stop %s storniert" % alt_txid)
        pos["stop"] = neu
        pos["stop_txid"] = neu_txid

    with open(ZUSTAND, "w", encoding="utf-8", newline="\n") as f:
        json.dump(z, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with open(WACHEN, encoding="utf-8") as f:
        ziel = json.load(f).get("journal_zweitziel")
    ok, info = wp.spiegele_journal([ZUSTAND], ziel)
    print("\nBuch nachgezogen, Spiegelung: %s" % ("ok" if ok else "FEHLER " + str(info)))
    print("Offene Orders jetzt: %d" % len(kraken.offene_orders()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
