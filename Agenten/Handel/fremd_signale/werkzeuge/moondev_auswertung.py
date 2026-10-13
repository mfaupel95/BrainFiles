"""Auswertung der moon-dev-Empfehlungen (ai_analysis_buys.csv, Jan 2025) gegen CoinGecko-Verlauf.
Vorab: Signalzeit = timestamp (UTC angenommen), Einstiegspreis = Spalte price (CSV), Ausstieg = Preis nach 1/3/7 Tagen
(CoinGecko market_chart/range, naechster Datenpunkt). Gruppen: Konsens BUY/BUY, nur ein Agent BUY. Kosten 1 % je Seite
(Memecoin-Spread/Slippage, grobe Annahme). Token ohne Kursdaten = 'tot' (Survivorship-Bias, getrennt gezaehlt)."""
import csv, json, os, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone
import statistics as st

QUELLE = r"O:\Werkstatt\Repos\moon-dev-ai-agents\src\data\ai_analysis_buys.csv"
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "moondev_preise.json")
HORIZONTE = (1, 3, 7)
KOSTEN = 0.01

rows = list(csv.DictReader(open(QUELLE, encoding="utf-8")))
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def ts(t):
    return int(datetime.fromisoformat(t).replace(tzinfo=timezone.utc).timestamp())


def holen(token, t0):
    k = "%s@%d" % (token, t0)
    if k in cache:
        return cache[k]
    url = "https://api.coingecko.com/api/v3/coins/%s/market_chart/range?vs_currency=usd&from=%d&to=%d" % (token, t0 - 3600, t0 + 8 * 86400)
    for versuch in range(4):
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "brainfiles/1.0"}), timeout=25))
            cache[k] = d.get("prices", [])
            break
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(30)
                continue
            cache[k] = "fehler%d" % e.code
            break
        except Exception as e:
            cache[k] = "fehler"
            break
    else:
        return None
    json.dump(cache, open(CACHE, "w"))
    time.sleep(2.5)
    return cache.get(k)


def preis_nach(serie, t_ms):
    for p in serie:
        if p[0] >= t_ms:
            return p[1]
    return None


erg = {"konsens": [], "einer": []}
tot = {"konsens": 0, "einer": 0}
for r in rows:
    g = "konsens" if r["agent_one_recommendation"].upper() == "BUY" and r["agent_two_recommendation"].upper() == "BUY" else "einer"
    t0 = ts(r["timestamp"])
    serie = holen(r["token_id"], t0)
    if serie is None:
        print("429 Abbruch bei", r["token_id"]); break
    if not isinstance(serie, list) or len(serie) < 3:
        tot[g] += 1
        continue
    p0 = serie[0][1]   # erster Punkt nach Signal (gleiche Quelle, vergleichbar)
    zeile = {"token": r["token_id"]}
    for h in HORIZONTE:
        p1 = preis_nach(serie, (t0 + h * 86400) * 1000)
        if p1:
            zeile[h] = p1 / p0 - 1 - 2 * KOSTEN
    erg[g].append(zeile)

for g in ("konsens", "einer"):
    print("\n== %s: %d mit Daten, %d ohne Daten (tot/unbekannt)" % (g, len(erg[g]), tot[g]))
    for h in HORIZONTE:
        v = [z[h] for z in erg[g] if h in z]
        if v:
            print("  +%dd: n=%d Mittel %+.1f%% Median %+.1f%% positiv %d/%d (nach 2%% Kosten)" % (h, len(v), st.mean(v) * 100, st.median(v) * 100, sum(x > 0 for x in v), len(v)))
