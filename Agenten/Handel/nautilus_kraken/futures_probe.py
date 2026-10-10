"""Kleiner echter Round-Trip im Kraken-FUTURES-Konto - der Nachweis, den es ohne
`validate` nicht gibt.

Wann: T-066 (Gebuehr an einer ECHTEN Fuellung messen) und der letzte Schritt von
T-067 (Orderweg live beweisen). Der Spot-Weg hat dafuer `AddOrder validate=true`;
die Futures-REST hat KEINEN Trockenschalter, deshalb dieser winzige echte Handel.

Ablauf (Vorschau ist Standard, `--anwenden` handelt):
    1. Lage lesen: Kurs, freies Guthaben, offene Positionen/Orders. Sind welche
       da, bricht das Werkzeug ab - es prueft seinen eigenen Vorgang.
    2. Kauf `markt` ueber N Kontrakte. **1 Kontrakt ist EINE Einheit der
       Basiswaehrung** (gemessen 25.09.2026): 1 Kontrakt PF_XBTUSD ist 1 BTC
       und kostet rund 84.600 USD Nennwert, 1 Kontrakt PF_STRKUSD dagegen
       0,04 USD. Diese Datei behauptete bis 01.10.2026 das Gegenteil und
       haette mit der Vorgabe 8 Kontrakte einen Kauf ueber 676.816 USD
       ausgeloest - bei frei verfuegbarer Margin von 83 USD. **Fuer einen
       Nachweis also immer einen BILLIGEN Markt nehmen:**
       `--symbol PF_STRKUSD --kontrakte 1`.
    3. Fuellung abwarten (pollt /fills, begrenzt), Kaufpreis und Groesse zeigen.
    4. Verkauf `markt` + `reduceOnly` - dasselbe N.
    5. Gebuehren aus `/accountlogcsv` lesen (das Journal des Kontos) und
       Netto-Ergebnis rechnen.

Sicherheit:
    * Nebeneffekt-arme Groesse: Standard 8 Kontrakte = 8 USD Nominal, Gebuehr im
      Bereich von Tausendstel Cent.
    * Scheitert der Verkauf, wird SOFORT ein Schutz-Stop 1,5 % unter dem
      Einstieg gesetzt und der Zustand laut gemeldet - eine offene Position
      ohne Stop waere das eigentliche Risiko dieses Werkzeugs.
    * Es wird nichts als Position "gemerkt": das Werkzeug bucht in kein Buch,
      setzt keine Spur-Werte, oeffnet kein Freigabefenster.

    python futures_probe.py                 # Vorschau
    python futures_probe.py --anwenden      # fuehrt aus (echtes Geld)
    python futures_probe.py --anwenden --kontrakte 4
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kraken_futures as kf        # noqa: E402

SYMBOL = "PF_XBTUSD"          # Vorgabe; --symbol ueberschreibt
KONTRAKTE_STANDARD = 8


def _iso(zeitpunkt):
    return zeitpunkt.strftime("%Y-%m-%dT%H:%M:%SZ")


def fuelungen(order_id, seit, frist_s=15):
    """Fuellungen dieser Orderkennung, bis sie da sind (begrenztes Warten).

    T-312 (01.10.2026): /fills antwortet sporadisch mit authenticationError,
    waehrend /accounts und /openpositions durchgehen. Vorher propagierte die
    Exception aus `lauf()` und der Notausstieg wurde nie erreicht - die
    Position blieb ohne Schutz offen. Jetzt wird der Fehler protokolliert und
    als leere Liste zurueckgegeben; der Aufrufer behandelt das als
    'Fuellung nicht lesbar' und sichert ab.
    """
    letzter_fehler = None
    ende = time.time() + frist_s
    while time.time() < ende:
        try:
            daten = kf._roh("/fills?lastFillTime=%s" % _iso(seit))
        except Exception as fehler:                  # noqa: BLE001
            letzter_fehler = fehler
            time.sleep(1)
            continue
        meine = [f for f in (daten.get("fills") or [])
                 if f.get("order_id") == order_id]
        if meine:
            return meine
        time.sleep(1)
    if letzter_fehler:
        print("  /fills nicht lesbar (letzter Fehler: %s) - als 'keine "
              "Fuellung' behandelt." % letzter_fehler)
    return []


def gebuehren(seit):
    """Kontojournal: Zeilen mit Symbol oder Gebuehr (die Quelle echter Kosten)."""
    try:
        daten = kf._roh("/accountlogcsv?startTime=%s" % _iso(seit))
    except Exception as fehler:                       # noqa: BLE001
        return None, "Accountlog nicht lesbar: %s" % fehler
    zeilen = daten.get("logs") or []
    betreff = [z for z in zeilen if SYMBOL in z or "fee" in z.lower()
               or "commission" in z.lower()]
    return betreff, None


def lage(symbol, kontrakte):
    kurs = kf.letzter_kurs(symbol)
    frei = kf.guthaben("usd")
    positionen = kf.offene_positionen(symbol)
    orders = kf.offene_orders(symbol)
    # 1 Kontrakt = 1 Einheit der Basiswaehrung. Der Nennwert ist Kontraktzahl
    # x Kurs, der Einschuss kommt aus dem Margenplan des Marktes - bei
    # PF_XBTUSD sind das rund 12,5 %, nicht 10 %.
    nominal = float(kontrakte) * float(kurs)
    einschuss = kf.einschuss(symbol, kontrakte, kurs)
    return {"kurs": kurs, "frei": frei, "positionen": positionen,
            "orders": orders, "nominal": nominal, "einschuss": einschuss}


def vorpruefen(l, kontrakte):
    gruende = []
    if l["positionen"]:
        gruende.append("%d offene Position(en) in %s" % (len(l["positionen"]), SYMBOL))
    if l["orders"]:
        gruende.append("%d offene Order(s) in %s" % (len(l["orders"]), SYMBOL))
    noetig = 2 * l["einschuss"]
    if l["frei"] < noetig:
        gruende.append("nur %.2f USD frei, noetig %.2f (2 x %.2f Einschuss fuer "
                       "%s x %.4f USD Nennwert)"
                       % (l["frei"], noetig, l["einschuss"], l["kurs"],
                          l["nominal"]))
    return gruende


def notausstieg(kurs, kontrakte, grund=""):
    """Schutz-Stop 1,5 % unter dem Einstieg, wenn der Verkauf scheitert.

    T-312 (01.10.2026): dieser Aufruf hing am Fill-Polling. Der Kauf war
    angenommen und gefuellt, das anschliessende Lesen von `/fills` scheiterte
    an `authenticationError`, der except-Zweig sprang aber VOR den Verkauf
    weg - die Position blieb ohne Schutz offen. Deshalb ruft der Aufrufer die
    Absicherung jetzt in JEDEM Abbruchpfad nach dem Kauf auf, auch wenn die
    Fuellung nicht lesbar war; `kurs` ist dann der letzte BEKANNTE Kurs
    (aus der Lage von vor dem Kauf), nicht ein gemessener Fuellungskurs.
    """
    stop = kurs * 0.985
    try:
        kennung = kf.stop_setzen(SYMBOL, kontrakte / kurs, stop, echt=True)
        return ("Schutz-Stop gesetzt (%s, etwa %s)%s"
                % (kennung, kf.preis_gerundet(SYMBOL, stop),
                   (" - GEGENUEBER: " + grund) if grund else ""))
    except Exception as fehler:                      # noqa: BLE001
        return ("AUCH DER SCHUTZ-STOP SCHEITERTE: %s%s - Position von Hand "
                "schliessen!" % (fehler,
                                 (" (Gegenueber: %s)" % grund) if grund else ""))


def lauf(kontrakte, anwenden):
    l = lage(SYMBOL, kontrakte)
    print("Lage: %s  Kurs %s  frei %.4f USD  Positionen %d  Orders %d"
          % (SYMBOL, l["kurs"], l["frei"], len(l["positionen"]), len(l["orders"])))
    gruende = vorpruefen(l, kontrakte)
    if gruende:
        print("ABBRUCH: %s" % "; ".join(gruende))
        return 1

    grund = kf.instrument(SYMBOL)
    print("Kontrakt: contractSize %s  tickSize %s  -> %d Kontrakte = %.2f USD Nominal"
          % (grund.get("contractSize"), grund.get("tickSize"), kontrakte,
             kontrakte * float(grund.get("contractSize") or 1)))
    if not anwenden:
        print()
        print("VORSCHAU - es wird nicht gehandelt. Mit --anwenden ausfuehren.")
        print("Waere: kauf %d, dann Verkauf %d reduceOnly, danach Gebuehren aus"
              " /accountlogcsv." % (kontrakte, kontrakte))
        return 0

    start = datetime.now(timezone.utc) - timedelta(minutes=1)

    kauf_id = kf._order_aufgeben({"orderType": "mkt", "symbol": SYMBOL,
                                  "side": "buy", "size": kontrakte})
    print("Kauf  gesendet: %s" % kauf_id)
    # T-312: ab hier ist die Position moeglicherweise OFFEN. Jeder weitere
    # Abbruchpfad muss absichern - unabhaengig davon, ob die Fuellung lesbar
    # war. `l["kurs"]` ist der letzte BEKANNTE Kurs (aus der Lage von vor dem
    # Kauf), nicht die Fuellung.
    kauf_fills = fuelungen(kauf_id, start)
    if not kauf_fills:
        # T-312: die Position kann trotzdem offen sein. Der Verkauf darf
        # NICHT vom Fill-Polling abhaengen - reduceOnly schliesst nur die
        # eigene Position und ist der sicherste Weg. Erst wenn auch der
        # Verkauf scheitert, greift der Schutz-Stop.
        print("KEINE Kauf-Fuellung gelesen - die Position kann trotzdem offen sein.")
        print("Order pruefen: %s" % kauf_id)
        kauf_preis = l["kurs"]   # letzter BEKANNTER Kurs, nicht die Fuellung
        kauf_menge = float(kontrakte)
        try:
            verkauf_id = kf._order_aufgeben({"orderType": "mkt", "symbol": SYMBOL,
                                             "side": "sell", "size": kontrakte,
                                             "reduceOnly": "true"})
        except Exception as fehler:                  # noqa: BLE001
            print("VERKAUF GESCHEITERT: %s" % fehler)
            print(notausstieg(kauf_preis, kontrakte,
                              "Kauf-Fuellung unlesbar, Verkauf abgelehnt"))
            return 1
        print("Verkauf gesendet (Kauf-Fuellung unlesbar): %s" % verkauf_id)
        verkauf_fills = fuelungen(verkauf_id, start)
        if not verkauf_fills:
            print("KEINE Verkaufsfuellung - Position pruefen! %s" % verkauf_id)
            print(notausstieg(kauf_preis, kontrakte,
                              "Kauf-Fuellung unlesbar, Verkaufsfuellung unlesbar"))
            return 1
        verkauf_menge = sum(float(f["size"]) for f in verkauf_fills)
        verkauf_preis = (sum(float(f["price"]) * float(f["size"]) for f in verkauf_fills)
                         / verkauf_menge if verkauf_menge else 0.0)
        print("Verkauf gefuellt: %s Kontrakte @ %s" % (verkauf_menge, verkauf_preis))
    else:
        kauf_preis = sum(float(f["price"]) * float(f["size"]) for f in kauf_fills)
        kauf_menge = sum(float(f["size"]) for f in kauf_fills)
        kauf_preis = kauf_preis / kauf_menge if kauf_menge else 0.0
        print("Kauf  gefuellt: %s Kontrakte @ %s" % (kauf_menge, kauf_preis))

        try:
            verkauf_id = kf._order_aufgeben({"orderType": "mkt", "symbol": SYMBOL,
                                             "side": "sell", "size": kontrakte,
                                             "reduceOnly": "true"})
        except Exception as fehler:                  # noqa: BLE001
            print("VERKAUF GESCHEITERT: %s" % fehler)
            print(notausstieg(kauf_preis, kontrakte, "Verkauf abgelehnt"))
            return 1
        print("Verkauf gesendet: %s" % verkauf_id)
        verkauf_fills = fuelungen(verkauf_id, start)
        if not verkauf_fills:
            print("KEINE Verkaufsfuellung - Position pruefen! %s" % verkauf_id)
            print(notausstieg(kauf_preis, kontrakte,
                              "Verkaufsfuellung nicht lesbar fuer %s" % verkauf_id))
            return 1
        verkauf_menge = sum(float(f["size"]) for f in verkauf_fills)
        verkauf_preis = (sum(float(f["price"]) * float(f["size"]) for f in verkauf_fills)
                         / verkauf_menge if verkauf_menge else 0.0)
        print("Verkauf gefuellt: %s Kontrakte @ %s" % (verkauf_menge, verkauf_preis))

    brutto = (verkauf_preis - kauf_preis) * min(kauf_menge, verkauf_menge)
    print()
    print("Brutto (ohne Gebuehr): %.6f USD  (%+.4f USD Nominal je Kontrakt)"
          % (brutto, verkauf_preis - kauf_preis))

    zeilen, fehler = gebuehren(start)
    if fehler:
        print("Gebuehren: %s" % fehler)
        print("Ersatzrechnung (NICHT gemessen): 2 x %.4f%% x %.2f USD = %.6f USD"
              % (0.05, kontrakte, 2 * 0.0005 * kontrakte))
    else:
        print("Kontojournal (%d Zeile(n)):" % len(zeilen))
        for z in zeilen:
            print("   %s" % z)

    print()
    print("Netto ohne Gebuehren: %.6f USD" % brutto)
    print("Restpositionen in %s: %d, offene Orders: %d"
          % (SYMBOL, len(kf.offene_positionen(SYMBOL)), len(kf.offene_orders(SYMBOL))))
    return 0


def main():
    global SYMBOL
    p = argparse.ArgumentParser(description="Kleiner echter Kraken-Futures-Round-Trip")
    p.add_argument("--anwenden", action="store_true",
                   help="wirklich handeln (Standard: nur Vorschau)")
    p.add_argument("--kontrakte", type=int, default=KONTRAKTE_STANDARD,
                   help="Kontrakte je Seite (1 Kontrakt = 1 USD Nominal)")
    p.add_argument("--symbol", default=SYMBOL,
                   help="Futures-Symbol (Vorgabe %s)" % SYMBOL)
    args = p.parse_args()
    SYMBOL = args.symbol
    if args.kontrakte < 1:
        print("--kontrakte muss mindestens 1 sein")
        return 2
    return lauf(args.kontrakte, args.anwenden)


if __name__ == "__main__":
    sys.exit(main())