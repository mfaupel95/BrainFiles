"""Alt-Breite: Anteil der Top-Paare ueber ihrer EMA200 (Tageskerzen).

WOFUER
------
Ein einzelner Messpunkt sagt nichts ueber die Richtung. Dieses Werkzeug misst
und kann den Wert in eine REIHE schreiben (`--merken`), damit "die Breite
schrumpft" belegbar wird statt behauptet.

WOHER
-----
Oeffentliche OKX-Tageskerzen (`/api/v5/market/candles`), nur Standardbibliothek,
kein Schluessel, keine Kosten. Der EEA-Host ist der Haushost; faellt er aus,
wird www.okx.com probiert.

Zeitbezug: gerechnet wird auf der letzten GESCHLOSSENEN Tageskerze, nicht auf
dem laufenden Kurs. Die Kerze steht in der Ausgabe.

FALLE (gemessen 25.09.2026)
---------------------------
OKX beantwortet `urllib` ohne User-Agent mit HTTP 403. Ohne den Kopf liefern
ALLE Paare einen Fehler und die Breite waere "0 von 0" - eine glatte
Falschaussage. Darum nennt die Ausgabe immer die Deckung: wie viele Paare
gemessen wurden und welche nicht.

AUFRUF (aus Agenten/Handel heraus: ..\\Werkzeuge\\breite.py)
    python breite.py                    # messen und zeigen (schreibt nichts)
    python breite.py --merken           # messen und an die Reihe anhaengen
    python breite.py --reihe            # die letzten 30 Messungen
    python breite.py --json             # Maschinenform fuer die Wache
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

REIHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "breite-reihe.jsonl")

PAARE = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "BNB-USDT",
    "DOGE-USDT", "ADA-USDT", "LINK-USDT", "AVAX-USDT", "TON-USDT",
    "DOT-USDT", "POL-USDT", "LTC-USDT", "TRX-USDT", "SHIB-USDT",
    "ATOM-USDT", "UNI-USDT", "NEAR-USDT", "APT-USDT", "ARB-USDT",
    "OP-USDT", "FIL-USDT", "INJ-USDT", "SUI-USDT", "SEI-USDT",
    "TIA-USDT", "PEPE-USDT", "ETC-USDT", "XLM-USDT", "ALGO-USDT",
]

BASEN = ("https://eea.okx.com", "https://www.okx.com")
LAENGE = 200


def _anfrage(url):
    """OKX blockt den urllib-Standardkopf mit HTTP 403 - Kopf mitgeben."""
    return urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) marktdaten",
        "Accept": "application/json",
    })


def kerzen(inst, basis, limit=300):
    """Schluesse der abgeschlossenen Tageskerzen, aelteste zuerst.

    Rueckgabe: (schluesse, zeitstempel_der_letzten_kerze_ms)
    """
    url = ("%s/api/v5/market/candles?instId=%s&bar=1D&limit=%d"
           % (basis, inst, limit))
    with urllib.request.urlopen(_anfrage(url), timeout=20) as a:
        daten = json.loads(a.read().decode("utf-8"))
    if daten.get("code") != "0":
        raise RuntimeError("OKX %s: %s" % (daten.get("code"), daten.get("msg")))
    reihen = [r for r in daten.get("data", []) if r[8] == "1"]
    if not reihen:
        raise RuntimeError("keine abgeschlossene Kerze")
    reihen.reverse()
    return [float(r[4]) for r in reihen], int(reihen[-1][0])


def ema(werte, n=LAENGE):
    """Exponentieller Mittelwert, Start = einfacher Mittel der ersten n."""
    if len(werte) < n:
        return None
    k = 2.0 / (n + 1)
    e = sum(werte[:n]) / n
    for x in werte[n:]:
        e = x * k + e * (1 - k)
    return e


def hole(inst):
    fehler = []
    for basis in BASEN:
        try:
            return kerzen(inst, basis)
        except Exception as f:                 # noqa: BLE001
            fehler.append("%s@%s" % (f, basis.split("//")[1]))
        time.sleep(0.1)
    raise RuntimeError("; ".join(fehler))


def messen(paare=None, still=False):
    """Misst die Breite. Rueckgabe: dict (Maschinenform)."""
    ueber, unter, offen = [], [], []
    kerzen_zeit = None
    for inst in (paare or PAARE):
        try:
            werte, ts = hole(inst)
        except Exception as f:                 # noqa: BLE001
            offen.append({"inst": inst, "grund": str(f)[:70]})
            continue
        kerzen_zeit = kerzen_zeit or ts
        e = ema(werte)
        if e is None:
            offen.append({"inst": inst, "grund": "nur %d Tageskerzen" % len(werte)})
            continue
        kurs = werte[-1]
        abstand = (kurs / e - 1.0) * 100.0
        satz = {"inst": inst, "kurs": kurs, "ema": e, "abstand": abstand}
        (ueber if kurs > e else unter).append(satz)
        if not still:
            time.sleep(0.05)
    gesamt = len(ueber) + len(unter)
    return {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kerze": (datetime.fromtimestamp(kerzen_zeit / 1000, timezone.utc)
                  .strftime("%Y-%m-%d") if kerzen_zeit else None),
        "ueber": sorted(ueber, key=lambda z: -z["abstand"]),
        "unter": sorted(unter, key=lambda z: z["abstand"]),
        "offen": offen,
        "n_ueber": len(ueber),
        "n_gesamt": gesamt,
        "breite": (100.0 * len(ueber) / gesamt) if gesamt else None,
    }


def zeige(m):
    print("== UEBER der EMA200 (%d) ==" % LAENGE)
    for s in m["ueber"]:
        print("  %-10s %14.6f   EMA200 %14.6f   %+7.2f %%"
              % (s["inst"], s["kurs"], s["ema"], s["abstand"]))
    print("== UNTER der EMA200 ==")
    for s in m["unter"]:
        print("  %-10s %14.6f   EMA200 %14.6f   %+7.2f %%"
              % (s["inst"], s["kurs"], s["ema"], s["abstand"]))
    if m["offen"]:
        print("== NICHT GEMESSEN ==")
        for o in m["offen"]:
            print("  %-10s %s" % (o["inst"], o["grund"]))
    print("")
    if m["n_gesamt"]:
        print("BREITE: %d von %d ueber der EMA200 = %.1f %%"
              % (m["n_ueber"], m["n_gesamt"], m["breite"]))
    print("(Deckung %d von %d, Kerze %s, gemessen %s)"
          % (m["n_gesamt"], len(PAARE), m["kerze"], m["ts"]))


def merken(m):
    """Eine Zeile je Messung. Abstaende mit, sonst ist der Verlauf blind."""
    satz = {
        "ts": m["ts"], "kerze": m["kerze"],
        "n_ueber": m["n_ueber"], "n_gesamt": m["n_gesamt"],
        "breite": round(m["breite"], 2) if m["breite"] is not None else None,
        "unter": [s["inst"] for s in m["unter"]],
        "offen": [o["inst"] for o in m["offen"]],
        "abstand": {s["inst"]: round(s["abstand"], 2)
                    for s in m["ueber"] + m["unter"]},
    }
    with open(REIHE, "a", encoding="utf-8") as f:
        f.write(json.dumps(satz, ensure_ascii=False) + "\n")
    return satz


def reihe(n=30):
    if not os.path.exists(REIHE):
        return []
    with open(REIHE, encoding="utf-8") as f:
        zeilen = [z for z in (l.strip() for l in f) if z]
    return [json.loads(z) for z in zeilen[-n:]]


def main(argv):
    if "--reihe" in argv:
        saetze = reihe()
        if not saetze:
            print("Keine Reihe vorhanden - noch nichts gemessen.")
            return 0
        print("== Breite-Reihe (%d Messungen) ==" % len(saetze))
        for s in saetze:
            print("  %s  Kerze %s  %5.1f %%  (%d/%d)%s"
                  % (s["ts"][:16].replace("T", " "), s["kerze"],
                     s["breite"] if s["breite"] is not None else -1,
                     s["n_ueber"], s["n_gesamt"],
                     "  unter: " + ",".join(s["unter"]) if s["unter"] else ""))
        if len(saetze) >= 2:
            print("  Veraenderung gegenueber der Messung davor: %+.1f pp"
                  % (saetze[-1]["breite"] - saetze[-2]["breite"]))
        return 0

    m = messen()
    if "--json" in argv:
        print(json.dumps(m, ensure_ascii=False))
    else:
        zeige(m)
    if "--merken" in argv:
        s = merken(m)
        print("In der Reihe vermerkt: %s (%.1f %%)" % (s["ts"], s["breite"]))
    return 0 if m["n_gesamt"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))