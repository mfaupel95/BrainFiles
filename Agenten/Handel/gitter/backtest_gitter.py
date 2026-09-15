"""Backtest der Gitter-Spur auf echten Kerzen - fuer die Optimierung.

FAHRT gitter/handeln.py SELBST: leiter_bauen(), arme() und walk() werden
importiert und auf historische Kerzen gestellt. Keine Nachbildung der
Gitterlogik - eine zweite Umsetzung waere eine zweite Wahrheit, und optimiert
waere dann die Nachbildung, nicht die Spur.

Kosten kommen aus gitter/wachen.json (Gebuehr 0,1 %, Slippage 0,05 %, beide
Seiten), nicht aus Schaetzung. Der Walk zieht sie ueber kostenfaktoren().

Zwei Vergleichswerte, beide aus DEMSELBEN Einsatz:
  - Gitter:  Buchwert am Ende (Kasse + Bestand zum Schlusskurs)
  - Halten:  der Einsatz am ersten Kurs gekauft, am letzten bewertet
Beide ohne Nachschuss - sonst stehen sie auf verschiedenen Grundlagen.
"""

import argparse
import datetime as dt
import importlib.util
import json
import os
import urllib.parse
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
OKX = "https://www.okx.com"
INST = {"instId": "BTC-USDT", "tickSz": 0.1, "lotSz": 0.00000001,
        "minSz": 0.00001}


def lade(name, pfad):
    """Ein Modul ueber den PFAD laden - nicht ueber sys.path.

    Ein Eintrag auf Handel/ koennte gleichnamige Spurenmodule verdecken
    (gitter/ hat grid.py neben Handel/grid.py) - dieselbe Falle wie bei
    ratschen.py.
    """
    s = importlib.util.spec_from_file_location(name, pfad)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


h = lade("gitter_handeln", os.path.join(HIER, "handeln.py"))


def kerzen_holen(inst, bar, stueck):
    """Kerzen von OKX oeffentlich, [ts, o, h, t, c], aufsteigend.

    OKX liefert hoechstens 300 je Abruf, der Parameter `after` blaettert
    rueckwaerts (aelter als der uebergebene Stempel). Ohne das bekaeme man nur
    die letzten 300 Stunden - rund 12 Tage statt acht Wochen.
    """
    reihen, grenze = [], None
    while len(reihen) < stueck:
        q = {"instId": inst, "bar": bar, "limit": "300"}
        if grenze:
            q["after"] = str(grenze)
        url = OKX + "/api/v5/market/candles?" + urllib.parse.urlencode(q)
        anf = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(anf, timeout=20) as a:
            d = json.loads(a.read().decode("utf-8"))
        if d.get("code") not in ("0", 0):
            raise SystemExit("OKX %s: %s" % (d.get("code"), d.get("msg")))
        seite = d.get("data") or []
        if not seite:
            break
        reihen += [[int(r[0])] + [float(x) for x in r[1:6]] for r in seite]
        grenze = min(int(r[0]) for r in seite)
    reihen = sorted({r[0]: r for r in reihen}.values(), key=lambda r: r[0])
    if len(reihen) < stueck:
        # OKX gibt oeffentlich nur 1440 Stundenkerzen heraus (60 Tage) - die
        # Blaetterung laeuft ins Leere, ohne zu melden. Wer das uebersieht,
        # haelt ein 4-Tage-Fenster fuer acht Wochen und baut darauf eine
        # Aussage. Deshalb hier laut, nicht still.
        raise SystemExit(
            "OKX liefert nur %d von %d Kerzen (%.1f statt %.1f Wochen).\n"
            "Oeffentlich sind hoechstens 1440 Stundenkerzen abrufbar.\n"
            "Fuer aeltere Fenster --lokal benutzen (mitgelieferte Reihe)."
            % (len(reihen), stueck, len(reihen) / 168.0, stueck / 168.0))
    return reihen[-stueck:]


def kerzen_lokal(pfad, stueck):
    """Rueckfall: die mitgelieferte Reihe (5 Felder, Volumen fehlt).

    walk() liest nur k[0..4], das Volumen braucht es nicht - aber die Datei
    endet am 24.08.2026, ist also NICHT die letzten acht Wochen bis heute.
    """
    roh = json.load(open(pfad, "r", encoding="utf-8"))
    reihen = [[int(r[0])] + [float(x) for x in r[1:6]] for r in roh]
    return sorted(reihen, key=lambda r: r[0])[-stueck:]


def leiter_zustand(kurs, w):
    """Zustand mit gebauter Leiter - genau die Struktur, die walk erwartet."""
    l = h.leiter_bauen(kurs, w, INST)
    return {
        "instrument": INST["instId"], "modus": "backtest",
        "kasse_usd": float(w.get("einsatz_usd", 1000.0)),
        "startwert_usd": float(w.get("einsatz_usd", 1000.0)),
        "leiter": {k: l[k] for k in ("unten", "oben", "stufen", "preise",
                                    "mengen", "zustand", "schritt_prozent",
                                    "einsatz_in_orders", "stufen_ohne_menge")},
        "lose": {}, "kaeufe": 0, "verkaeufe": 0, "zyklen": 0,
        "gw_usd": 0.0, "verluste_usd": 0.0, "bestand": 0.0,
        "letzte_kerze_ts": -1, "letzter_kurs": None,
    }


def sma_reihe(kerzen, n):
    """SMA je Kerzenstempel, nur aus Kerzen DAVOR - kein Blick nach vorn.

    Ohne das waere der Filter ein Hellseher: ein Mittelwert, der die Kerze
    schon enthaelt, auf die er angewendet wird, kennt das Ergebnis.
    """
    aus, s = {}, 0.0
    for i, k in enumerate(kerzen):
        s += float(k[4])
        if i >= n:
            s -= float(kerzen[i - n][4])
        if i >= n - 1:
            aus[int(k[0])] = s / n
    return aus


_ECHTER_ARME = h.arme


def _arme_setzen(kerzen, filter_):
    """h.arme durch eine gefilterte Fassung ersetzen (oder zurueckstellen).

    walk() ruft arme() als Modulglobal - der Haken sitzt deshalb genau an der
    Stelle, an der eine echte Spur ihre Kaufstufen belegt. Der Filter wirkt
    damit auf die ECHTE Logik, nicht auf eine Nachbildung daneben.
    """
    if not filter_:
        h.arme = _ECHTER_ARME
        return
    sma = sma_reihe(kerzen, filter_["n"])
    weite = filter_["abstand_pct"]

    def gefiltert(z, kurs):
        m = sma.get(int(z.get("letzte_kerze_ts") or 0))
        if m and abs(kurs / m - 1.0) * 100 < weite:
            _ECHTER_ARME(z, kurs)
    h.arme = gefiltert


def lauf(kerzen, w, filter_=None, still=True):
    """Ein Durchlauf. Rueckgabe: Kennzahlen als dict."""
    z = leiter_zustand(kerzen[0][4], w)
    h.journal = lambda **k: None          # keine Journalzeilen schreiben
    h._heute = lambda: "backtest"
    _arme_setzen(kerzen, filter_)
    zeilen, zahlen = h.walk(z, kerzen, w, "1H")
    ein = float(w.get("einsatz_usd", 1000.0))
    kurs_ende = kerzen[-1][4]
    buch = h.buchwert(z, kurs_ende)
    lose = sum(1 for v in z["lose"].values())
    return {
        "start": kerzen[0][4], "ende": kurs_ende,
        "buchwert": buch, "ergebnis": buch - ein,
        "rendite_pct": (buch / ein - 1) * 100,
        "halten_pct": (kurs_ende / kerzen[0][4] - 1) * 100,
        "kaeufe": zahlen["kaeufe"], "verkaeufe": zahlen["verkaeufe"],
        "zyklen": zahlen["zyklen"], "offen": lose,
        "verluste_usd": z.get("verluste_usd", 0.0),
        "schritt_pct": z["leiter"]["schritt_prozent"],
        "stufen": z["leiter"]["stufen"],
        "kerzen": zahlen["kerzen"],
    }


def wachen(pfad=None):
    p = pfad or os.path.join(HIER, "wachen.json")
    return json.load(open(p, "r", encoding="utf-8"))


def zeige(e, titel):
    print("%s" % titel)
    print("  Kerzen        %d   %.4f -> %.4f" % (e["kerzen"], e["start"], e["ende"]))
    print("  Stufen        %d   Schrittweite %.2f %%" % (e["stufen"], e["schritt_pct"]))
    print("  Kaeufe/Verkaeufe  %d / %d   offen %d" % (e["kaeufe"], e["verkaeufe"], e["offen"]))
    print("  Buchwert      %.2f   Ergebnis %+.2f  (%+.2f %%)"
          % (e["buchwert"], e["ergebnis"], e["rendite_pct"]))
    print("  Halten        %+.2f %%   Vorsprung %+.2f %%"
          % (e["halten_pct"], e["rendite_pct"] - e["halten_pct"]))
    print("  Verluste      %.2f" % e["verluste_usd"])


def main():
    p = argparse.ArgumentParser(description="Gitter-Backtest (faehrt die Spur selbst)")
    p.add_argument("--wochen", type=float, default=8.0)
    p.add_argument("--stufen", type=int, default=None)
    p.add_argument("--spanne-prozent", type=float, default=None)
    p.add_argument("--lokal", action="store_true", help="mitgelieferte Reihe statt OKX")
    p.add_argument("--json", action="store_true", help="Kennzahlen als JSON")
    a = p.parse_args()

    w = wachen()
    if a.stufen:
        w["stufen"] = a.stufen
    if a.spanne_prozent:
        w["spanne_prozent"] = a.spanne_prozent
    stueck = int(a.wochen * 7 * 24)
    if a.lokal:
        k = kerzen_lokal(os.path.join(HANDEL, "kerzen_BTC-USDT_1H_8760.json"), stueck)
    else:
        k = kerzen_holen(INST["instId"], "1H", stueck)
    e = lauf(k, w)
    if a.json:
        print(json.dumps(e))
    else:
        t = "%s - %s" % (dt.datetime.fromtimestamp(k[0][0] / 1000, dt.timezone.utc).strftime("%Y-%m-%d"),
                         dt.datetime.fromtimestamp(k[-1][0] / 1000, dt.timezone.utc).strftime("%Y-%m-%d"))
        zeige(e, "Gitter %.1f Wochen (%s), Spanne %.1f %%, %d Stufen"
              % (a.wochen, t, w.get("spanne_prozent"), w.get("stufen")))


if __name__ == "__main__":
    main()
