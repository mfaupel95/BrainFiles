"""Regime-Studie fuer die vier Prognose-Spuren (T-101).

Frage (T-101): laesst sich das schlechte Regime VORHER erkennen? Die erste
Parametersuche (2026-09-25) zeigte, dass in JEDER Spur ein Halbjahr fuer
JEDEN Parameter negativ ist; die Stop-Breite ist eine Risikoeinstellung,
kein Hebel. Hier wird geprueft, ob ein Marktzustand am EINSTIEG das
negative Fenster ankuendigt - drei Kandidaten:

  * Trendlage gegen den 200er  (Schluss > SMA200 der 1H-Kerzen)
  * Volatilitaet               (ATR14 / Schluss, geteilt am Median)
  * Marktbreite                (Anteil des Historien-Universums ueber SMA200)

Fundament: replay.py (lauf_a) faehrt jede Spur ueber die volle Historie und
legt das Journal in daten/backtest/<spur>/regime_studie/. Dieses Skript liest
nur - es paart Einstieg/Ausstieg je pos_id und legt die Regime-Merkmale an
den EINSTIEG-Zeitpunkt. Kein Parameter wird angepasst: getestet wird die
Spur, wie sie heute laeuft.

Disziplin wie beim Gitter-Befund (15.09.2026): Suchfenster -> ungesehenes
Prueffenster. Schwellen (Median von Volatilitaet/Breite) werden NUR auf dem
Suchfenster bestimmt und dann auf beide Fenster angewandt. "Kein Filter
haelt" ist ein vollwertiges Ergebnis.

Aufruf (aus dem Handel-Ordner, NACH den Replay-Laeufen):
    python regime_studie.py                # Bericht auf stdout
    python regime_studie.py --json        # Zahlen nach regime_studie.json
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
# DATEN kann ueber die Umgebung auf den Hauptbaum zeigen: der Worktree hat
# kein daten/ (gitignored). Nur fuer die Ausfuehrung - der Code bleibt gleich.
DATEN = os.environ.get("REGIME_DATEN") or os.path.join(HIER, "daten")
HISTORIE = os.path.join(DATEN, "historie")

SPUREN = ["squeeze", "wavetrend", "macd_mtf", "supertrend"]
LAUF = "regime_studie"
GEBUEHR_PCT = 0.1                      # je Seite, wie bei den Laeufen

# Suchfenster 60 %, Prueffenster 40 % der Zeitachse (nach Einstiegszeit).
SUCH_ANTEIL = 0.60
# Mindestzahl Runden je Seite und Fenster fuer ein belastbares Urteil
# (gemessen 25.09.: 6 Monate lieferten nur 8-49 Runden je Fenster).
MINDEST_RUNDEN = 20
# Mindest-Differenz (Prozentpunkte Mittelwert netto) zwischen guter und
# schlechter Seite, damit ein Filter "haelt" (rund doppelte Trefferquote-
# Streuung bei 20 Runden).
MINDEST_DIFF_PP = 0.20

# Historien-Universum: was unter daten/historie liegt. Nur Reihen, die >= 80 %
# der Zeitachse abdecken, zaehlen (eine Reihe, die erst 2024 anfaengt, wuerde
# die Breite im Suchfenster systematisch leer machen).
ABDECKUNG = 0.80


def _ts(iso: str) -> int:
    """ISO-Zeit -> ms-Epoche (Kerzenzeit). Die Journal-`zeit` traegt die
    Kerzenzeit, weil der Replay `zeit_quelle` setzt (gemessen 25.09.2026)."""
    try:
        return int(datetime.fromisoformat(iso).timestamp() * 1000)
    except (TypeError, ValueError):
        return 0


def lade_journal(spur: str) -> list[dict]:
    pfad = os.path.join(DATEN, "backtest", spur, LAUF, "handelsjournal.csv")
    if not os.path.isfile(pfad):
        raise FileNotFoundError("Journal fehlt: %s - erst replay.py fahren" % pfad)
    with open(pfad, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def paare_runden(zeilen: list[dict]) -> list[dict]:
    """Einstieg/Ausstieg je pos_id paaren. Gibt je Runde:
    {inst, seite, ein_ts, ein_preis, aus_preis, brutto_pct, netto_pct}."""
    offen: dict[str, dict] = {}
    runden = []
    for r in zeilen:
        aktion = (r.get("aktion") or "").strip().lower()
        if aktion not in ("kauf", "verkauf"):
            continue
        pid = (r.get("pos_id") or "").strip()
        preis = float(r.get("preis") or 0.0) or 0.0
        if aktion == "kauf":
            if not pid or not preis:
                continue
            offen[pid] = {"inst": r.get("inst"), "seite": r.get("seite"),
                          "ein_ts": _ts(r.get("zeit") or ""),
                          "ein_preis": preis}
        else:
            if not pid or pid not in offen:
                continue
            e = offen.pop(pid)
            if not e["ein_preis"] or not preis:
                continue
            vz = -1.0 if (e.get("seite") or "").strip().lower() == "short" else 1.0
            roh = (preis / e["ein_preis"] - 1.0) * 100.0 * vz
            runden.append({"inst": e["inst"], "seite": e.get("seite"),
                           "ein_ts": e["ein_ts"], "ein_preis": e["ein_preis"],
                           "aus_preis": preis, "brutto_pct": roh,
                           "netto_pct": roh - 2.0 * GEBUEHR_PCT})
    return runden


def _symbol(inst: str) -> str:
    """OKX-Instrument -> Binance-Symbolname der Historie (nur diese Spuren)."""
    for alt in ("-USDC", "-USDT"):
        if inst.endswith(alt):
            return inst[: -len(alt)] + "USDT"
    return inst + "USDT"


def lade_historie(symbol: str) -> list[list]:
    pfad = os.path.join(HISTORIE, "%s_1H.json" % symbol)
    if not os.path.isfile(pfad):
        return []
    with open(pfad, encoding="utf-8") as f:
        roh = json.load(f)
    return sorted(roh, key=lambda k: k[0])


def sma200(reihe: list[list], ts: int) -> float | None:
    """SMA200 der 1H-Schluesse bis einschliesslich ts - sonst None."""
    if len(reihe) < 200:
        return None
    # binsearch: letzter Index mit ts_k <= ts
    lo, hi = 0, len(reihe) - 1
    letzter = -1
    while lo <= hi:
        m = (lo + hi) // 2
        if reihe[m][0] <= ts:
            letzter = m
            lo = m + 1
        else:
            hi = m - 1
    if letzter < 199:
        return None
    fenster = reihe[letzter - 199:letzter + 1]
    return sum(k[4] for k in fenster) / 200.0


def atr14_normalisiert(reihe: list[list], ts: int) -> float | None:
    """ATR-14 (Wilder, naeherungsweise Mittel der TR) geteilt durch Schluss."""
    lo, hi = 0, len(reihe) - 1
    letzter = -1
    while lo <= hi:
        m = (lo + hi) // 2
        if reihe[m][0] <= ts:
            letzter = m
            lo = m + 1
        else:
            hi = m - 1
    if letzter < 14:
        return None
    fenster = reihe[letzter - 13:letzter + 1]
    trs = []
    vorher = fenster[0][4]
    for k in fenster[1:]:
        hoch, tief, schluss = k[2], k[3], k[4]
        trs.append(max(hoch - tief, abs(hoch - vorher), abs(tief - vorher)))
        vorher = schluss
    atr = sum(trs) / len(trs)
    return atr / fenster[-1][4] if fenster[-1][4] else None


def letzter_index(reihe: list[list], ts: int) -> int:
    """Letzter Index mit Kerzenzeit <= ts, sonst -1. Kein Listen-Kopieren."""
    lo, hi = 0, len(reihe) - 1
    letzter = -1
    while lo <= hi:
        m = (lo + hi) // 2
        if reihe[m][0] <= ts:
            letzter = m
            lo = m + 1
        else:
            hi = m - 1
    return letzter


def merkmale_bei(reihen: dict[str, list[list]], inst: str, ts: int) -> dict:
    """Die drei Regime-Merkmale am Zeitpunkt ts (kein Blick in die Zukunft)."""
    eigene = reihen.get(_symbol(inst), [])
    idx = letzter_index(eigene, ts)
    schluss = eigene[idx][4] if idx >= 0 and eigene else None
    sma = sma200(eigene, ts)
    trend = (schluss is not None and sma is not None and schluss > sma)
    vol = atr14_normalisiert(eigene, ts)
    # Marktbreite: Anteil des Universums ueber seiner SMA200.
    ueber = gesamt = 0
    for symbol, reihe in reihen.items():
        s = sma200(reihe, ts)
        i = letzter_index(reihe, ts)
        k = reihe[i][4] if i >= 0 and reihe else None
        if s is None or k is None or not k:
            continue
        gesamt += 1
        if k > s:
            ueber += 1
    breite = ueber / gesamt if gesamt else None
    return {"trend_200": trend, "vol": vol, "breite": breite}


def universum(reihen: dict[str, list[list]], min_ts: int, max_ts: int) -> dict:
    spanne = max_ts - min_ts
    aus = {}
    for name, reihe in sorted(reihen.items()):
        if not reihe or not spanne:
            continue
        deckung = (reihe[-1][0] - reihe[0][0]) / spanne
        if deckung >= ABDECKUNG:
            aus[name] = reihe
    return aus


def auswerten(runden: list[dict], fenster: tuple[int, int]) -> dict:
    von, bis = fenster
    drin = [r for r in runden if von <= r["ein_ts"] <= bis]
    return {"n": len(drin),
            "mittel": statistics.fmean(r["netto_pct"] for r in drin) if drin else None,
            "treffer": sum(1 for r in drin if r["netto_pct"] > 0) if drin else 0}


def spalte(runden: list[dict], fenster: tuple[int, int], zeiger: dict) -> tuple[dict, dict]:
    """Runden nach Merkmal teilen: (gut, schlecht) je Fenster."""
    gut, schlecht = [], []
    for r in runden:
        if fenster[0] <= r["ein_ts"] <= fenster[1]:
            if zeiger.get(r["ein_ts"], False):
                gut.append(r)
            else:
                schlecht.append(r)
    return (auswerten(gut, fenster), auswerten(schlecht, fenster))


def haelt(gut: dict, schlecht: dict) -> bool:
    """Ein Filter haelt, wenn er in DIESEM Fenster trennt (Vorzeichen und
    Mindest-Differenz) und beide Seiten genug Runden haben."""
    if gut["n"] < MINDEST_RUNDEN or schlecht["n"] < MINDEST_RUNDEN:
        return False
    if gut["mittel"] is None or schlecht["mittel"] is None:
        return False
    return gut["mittel"] - schlecht["mittel"] >= MINDEST_DIFF_PP


def zeile(merkmalsname: str, such: tuple[dict, dict], pruef: tuple[dict, dict]) -> str:
    def zelle(w: dict) -> str:
        if w["n"] < MINDEST_RUNDEN:
            return "n=%d (zu wenig)" % w["n"]
        mittel = "-" if w["mittel"] is None else "%.2f" % w["mittel"]
        treffer = "%.0f%%" % (100.0 * w["treffer"] / w["n"])
        return "n=%d, %s, %s" % (w["n"], mittel, treffer)

    h = "JA" if (haelt(such[0], such[1]) and haelt(pruef[0], pruef[1])) else "nein"
    return ("| %-22s | %-20s | %-20s | %-20s | %-20s | %s |"
            % (merkmalsname, zelle(such[0]), zelle(such[1]),
               zelle(pruef[0]), zelle(pruef[1]), h))


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--json", action="store_true",
                   help="Zahlen nach regime_studie.json schreiben")
    args = a.parse_args()

    # Historien laden (nur 1H).
    reihen = {}
    if os.path.isdir(HISTORIE):
        for name in os.listdir(HISTORIE):
            if name.endswith("_1H.json"):
                symbol = name[:-len("_1H.json")]
                reihen[symbol] = lade_historie(symbol)

    ergebnis_je_spur = {}
    for spur in SPUREN:
        try:
            zeilen = lade_journal(spur)
        except FileNotFoundError as e:
            print("== %s: %s" % (spur, e))
            continue
        runden = paare_runden(zeilen)
        if not runden:
            print("== %s: KEINE Runden (Journal leer?)" % spur)
            continue
        ein_ts = sorted(r["ein_ts"] for r in runden)
        min_ts, max_ts = ein_ts[0], ein_ts[-1]
        grenze = min_ts + (max_ts - min_ts) * SUCH_ANTEIL
        such = (min_ts, int(grenze))
        pruef = (int(grenze), max_ts)
        uni = universum(reihen, min_ts, max_ts)
        if len(uni) < 3:
            print("== %s: Universum zu duenn (%d) - keine Breite" % (spur, len(uni)))
            continue

        # Merkmale je Einstieg NUR fuer das Suchfenster bestimmen (Median),
        # dann auf BEIDE Fenster anwenden.
        such_runden = [r for r in runden if such[0] <= r["ein_ts"] <= such[1]]
        vols = [m["vol"] for r in such_runden
                if (m := _merkmale_bei_cached(reihen, uni, r)) and m["vol"]]
        vol_median = statistics.median(vols) if vols else 0.0
        breiten = [m["breite"] for r in such_runden
                   if (m := _merkmale_bei_cached(reihen, uni, r)) and m["breite"] is not None]
        breite_median = statistics.median(breiten) if breiten else 1.0

        zeiger = {}
        for r in runden:
            m = _merkmale_bei_cached(reihen, uni, r)
            zeiger[r["ein_ts"]] = {
                "trend_200": bool(m and m["trend_200"]),
                "vol_hoch": bool(m and m["vol"] is not None and m["vol"] >= vol_median),
                "breite_hoch": bool(m and m["breite"] is not None and m["breite"] >= breite_median),
                "trend_und_breite": bool(m and m["trend_200"]
                                         and m["breite"] is not None
                                         and m["breite"] >= breite_median),
            }

        print("== %s  (%d Runden, %s bis %s, Such-%s / Pruef-%s)"
              % (spur, len(runden),
                 datetime.fromtimestamp(min_ts / 1000, timezone.utc).date(),
                 datetime.fromtimestamp(max_ts / 1000, timezone.utc).date(),
                 datetime.fromtimestamp(grenze / 1000, timezone.utc).date(),
                 datetime.fromtimestamp(max_ts / 1000, timezone.utc).date()))
        print("| Merkmal (gut = ...)      | Such: gut        | Such: schlecht   | Pruef: gut       | Pruef: schlecht  | haelt |")
        print("|--------------------------|-------------------|-------------------|-------|")
        tabellen = []
        for name, zkey in (("Trend > SMA200", "trend_200"),
                           ("Vol >= Median", "vol_hoch"),
                           ("Breite >= Median", "breite_hoch"),
                           ("Trend UND Breite", "trend_und_breite")):
            zt = {t: zeiger[t][zkey] for t in zeiger}
            s_gut, s_schlecht = spalte(runden, such, zt)
            p_gut, p_schlecht = spalte(runden, pruef, zt)
            tabellen.append((name, s_gut, s_schlecht, p_gut, p_schlecht))
            print(zeile(name, (s_gut, s_schlecht), (p_gut, p_schlecht)))
        ergebnis_je_spur[spur] = {
            "runden": len(runden),
            "such": {"von": min_ts, "bis": int(grenze)},
            "pruef": {"von": int(grenze), "bis": max_ts},
            "vol_median": vol_median, "breite_median": breite_median,
            "universum": len(uni),
            "merkmale": [{"name": n, "such": {"gut": s_gut, "schlecht": s_schlecht},
                          "pruef": {"gut": p_gut, "schlecht": p_schlecht}}
                         for n, s_gut, s_schlecht, p_gut, p_schlecht in tabellen],
        }
        print()

    if args.json:
        with open(os.path.join(HIER, "regime_studie.json"), "w",
                  encoding="utf-8", newline="\n") as f:
            json.dump(ergebnis_je_spur, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("Zahlen nach regime_studie.json geschrieben.")
    return 0


_CACHE: dict = {}


def _merkmale_bei_cached(reihen, uni, r) -> dict | None:
    key = (r["inst"], r["ein_ts"])
    if key not in _CACHE:
        _CACHE.clear()                          # nie mehr als ein Satz
        m = merkmale_bei(uni, r["inst"], r["ein_ts"])
        _CACHE[key] = m
    return _CACHE[key]


if __name__ == "__main__":
    raise SystemExit(main())
