"""Marktbreite: Anteil der Top-Paare ueber ihrer EMA200 (Tageskerzen).

Rein lesend, nur Standardbibliothek, kein Schluessel. Oeffentliche OKX-Kerzen.

    python alt_breite.py                 # 30 Paare, Tageskerzen, EMA200
    python alt_breite.py --laenge 100    # kuerzerer Durchschnitt

Ausgabe: je Paar eine Zeile (Schluss, EMA, Abstand), am Ende BREITE, DECKUNG und
ZEITBEZUG. Paare, die nicht aufloesen, werden namentlich genannt - verschwiegen
wuerde aus einem Totalausfall eine Quote von 0 %.

Drei Dinge, die die Zahl tragen:
  * nur GESCHLOSSENE Kerzen (confirm == "1"), sonst wandert das Ergebnis;
  * der Zeitbezug wird mitgedruckt (OKX-Tag beginnt 16:00 UTC = 00:00 UTC+8);
  * der Kopf traegt einen User-Agent - OKX beantwortet urllib sonst mit 403.
"""
import argparse
import datetime
import json
import time
import urllib.request

PAARE = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "BNB-USDT",
    "DOGE-USDT", "ADA-USDT", "LINK-USDT", "AVAX-USDT", "TON-USDT",
    "DOT-USDT", "POL-USDT", "LTC-USDT", "TRX-USDT", "SHIB-USDT",
    "ATOM-USDT", "UNI-USDT", "NEAR-USDT", "APT-USDT", "ARB-USDT",
    "OP-USDT", "FIL-USDT", "INJ-USDT", "SUI-USDT", "SEI-USDT",
    "TIA-USDT", "PEPE-USDT", "ETC-USDT", "XLM-USDT", "ALGO-USDT",
]

BASEN = ("https://eea.okx.com", "https://www.okx.com")


def _anfrage(url):
    """OKX blockt den urllib-Standardkopf mit HTTP 403 - Kopf mitgeben."""
    return urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) marktanalyse",
        "Accept": "application/json",
    })


def kerzen(inst, basis, limit=300):
    """Geschlossene Tagesschluesse (aufsteigend) plus Zeit der letzten Kerze."""
    url = ("%s/api/v5/market/candles?instId=%s&bar=1D&limit=%d"
           % (basis, inst, limit))
    with urllib.request.urlopen(_anfrage(url), timeout=20) as a:
        daten = json.loads(a.read().decode("utf-8"))
    if daten.get("code") != "0":
        raise RuntimeError("OKX %s: %s" % (daten.get("code"), daten.get("msg")))
    reihen = [r for r in daten.get("data", []) if r[8] == "1"]   # unfertige weg
    reihen.reverse()                                            # neueste zuerst
    zu = [float(r[4]) for r in reihen]
    letzte = datetime.datetime.fromtimestamp(
        int(reihen[-1][0]) / 1000, datetime.timezone.utc)
    return zu, letzte


def ema(werte, n):
    """EMA mit SMA-Vorlauf der ersten n Werte (Standardform)."""
    if len(werte) < n:
        return None
    k = 2.0 / (n + 1)
    e = sum(werte[:n]) / n
    for x in werte[n:]:
        e = x * k + e * (1 - k)
    return e


def hole(inst, limit):
    fehler = []
    for basis in BASEN:
        try:
            return kerzen(inst, basis, limit) + (basis,)
        except Exception as f:                # noqa: BLE001
            fehler.append("%s (%s)" % (f, basis.split("//")[1]))
    raise RuntimeError("; ".join(fehler))


def main():
    p = argparse.ArgumentParser(description="Marktbreite ueber der EMA")
    p.add_argument("--laenge", type=int, default=200,
                   help="Laenge des Durchschnitts (Standard 200)")
    p.add_argument("--limit", type=int, default=300,
                   help="Kerzen je Paar abrufen (Standard 300)")
    a = p.parse_args()

    ueber, unter, offen = [], [], []
    bezug = None
    for inst in PAARE:
        try:
            werte, letzte, _basis = hole(inst, a.limit)
        except Exception as f:                # noqa: BLE001
            offen.append((inst, str(f)[:70]))
            continue
        bezug = bezug or letzte
        e = ema(werte, a.laenge)
        if e is None:
            offen.append((inst, "nur %d geschlossene Tageskerzen" % len(werte)))
            continue
        kurs = werte[-1]
        abstand = (kurs / e - 1.0) * 100.0
        (ueber if kurs > e else unter).append((inst, kurs, e, abstand))
        time.sleep(0.05)

    print("== UEBER der EMA%d ==" % a.laenge)
    for inst, kurs, e, ab in sorted(ueber, key=lambda z: -z[3]):
        print("  %-10s %14.8f   EMA %14.8f   %+8.2f %%" % (inst, kurs, e, ab))
    print("== UNTER der EMA%d ==" % a.laenge)
    for inst, kurs, e, ab in sorted(unter, key=lambda z: z[3]):
        print("  %-10s %14.8f   EMA %14.8f   %+8.2f %%" % (inst, kurs, e, ab))
    if offen:
        print("== NICHT GEMESSEN ==")
        for inst, warum in offen:
            print("  %-10s %s" % (inst, warum))

    gesamt = len(ueber) + len(unter)
    print("")
    print("BREITE: %d von %d Paaren ueber der EMA%d = %.1f %%"
          % (len(ueber), gesamt, a.laenge,
             100.0 * len(ueber) / gesamt if gesamt else 0.0))
    print("DECKUNG: %d von %d abgefragt, %d nicht messbar"
          % (gesamt, len(PAARE), len(offen)))
    if bezug is not None:
        print("ZEITBEZUG: letzte geschlossene Tageskerze endete %s "
              "(OKX-Tag ab 16:00 UTC)" % bezug.strftime("%Y-%m-%d %H:%M UTC"))
    print("HINWEIS: ein Messpunkt ist keine Richtung - fuer 'die Breite "
          "schrumpft' taeglich festhalten.")


if __name__ == "__main__":
    main()
