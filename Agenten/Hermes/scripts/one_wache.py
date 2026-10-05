#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ONE-Wache (OKX ONE-USDT, Harmony) - rein lesend, keine Orders.

Basis "ab jetzt" (Max, 19.09.2026): Referenzkurs = aktueller OKX-Kurs beim
Einrichten. Positionswert 9.268 EUR bei 10x Hebel.

Was dieses Skript tut: holt den oeffentlichen OKX-Ticker, rechnet Gewinnstufen
relativ zur Referenz und die Sicherungsschwelle (Trailing unter Hochpunkt +
Liquidationsnaehe bei 10x Hebel). Ausgabe ist LEER, wenn nichts Neues passiert
(Watchdog-Muster) - nur bei einem neuen Ereignis erscheint eine Zeile.
"""
import json
import os
# Die Haus-Bremse gegen OKX-Drosselung: sie begrenzt ALLE OKX-Abrufe des
# Hauses prozessuebergreifend (Fensterspiegel in Agenten/Handel/cache/okx-takt),
# damit Wache, Handelszentrale und die drei Dauerlauf-Stufen sich nicht
# gegenseitig in die Drosselung laufen. Gemessen 05.10.2026: 6 parallene
# Threads -> 93x 'OKX 50011', nacheinander 120 Abrufe -> 0 Fehler.
#
# Der Pfad wird nicht GEZAEHLT, sondern GESUCHT: aus Agenten/Hermes/scripts/ fuehren
# zwei Ebenen hoch zur Wurzel, aus einer Spur unter Handel/ faengt es die
# Schleife bei "Handel". Ein Zaehlen aus der Quelle heraus war an drei von
# vier Stellen falsch (Lehre: cache/scratch-Skripte brauchen drei Ebenen, ein
# Werkzeug unter Agenten zwei) - gesucht wird nie falsch.
import os as _os
import sys as _sys
import importlib.util as _ilu


def _lade_okx_takt():
    hier = _os.path.dirname(_os.path.abspath(__file__))
    kandidat = _os.path.join(hier, "..", "Handel", "okx_takt.py")
    if not _os.path.exists(kandidat):
        kandidat = _os.path.join(hier, "..", "..", "Handel", "okx_takt.py")
    if not _os.path.exists(kandidat):
        raise RuntimeError("Haus-Bremse nicht gefunden (gesucht ab %s)" % hier)
    _s = _ilu.spec_from_file_location("okx_takt", _os.path.normpath(kandidat))
    _m = _ilu.module_from_spec(_s)
    _sys.modules["okx_takt"] = _m
    _s.loader.exec_module(_m)
    return _m


okx_takt = _lade_okx_takt()

import urllib.request

BASELINE = 0.00340          # Referenz "ab jetzt" (OKX-Kurs beim Einrichten)
POSITION_EUR = 9268.0       # Positionswert bei 10x Hebel
TICKER = "https://www.okx.com/api/v5/market/ticker?instId=ONE-USDT"
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "_one_wache_state.json")

# Gewinnstufen: (Gewinnfaktor gegenueber Referenz, empfohlener Anteil sichern von 1/...)
# +25% -> 1/3 raus, +50% -> weitere 1/3, +100% -> Rest absichern
TIERS = [(0.25, "sichere 1/3 deiner Position"), (0.50, "sichere weitere 1/3"),
         (1.00, "Gewinn voll absichern")]
SAFETY_DROP = 0.30          # 30% unter Hochpunkt -> Sicherungswarnung
LAQ_DROP = 0.10             # ~10% unter Hochpunkt -> Liquidationsgefahr (10x Hebel)


def fetch_ticker():
    req = urllib.request.Request(
        TICKER,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    okx_takt.reserviere()
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode("utf-8"))
    t = d["data"][0]
    return (float(t["last"]), float(t["high24h"]), float(t["low24h"]),
            float(t["sodUtc0"]))


def load_state():
    if os.path.exists(STATE):
        try:
            with open(STATE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"high_water": BASELINE, "alerted": [], "laq_alerted": False}


def save_state(s):
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(s, f)


def usd(x):
    return "${:.5f}".format(x)


def eur(x):
    return "{:,.0f} EUR".format(x)


def main():
    try:
        last, high24, low24, sod = fetch_ticker()
    except Exception as e:
        # Netz-/API-Fehler: nichts senden (kein Fehlalarm); Wache schweigt
        return ""
    st = load_state()
    pct = (last / BASELINE) - 1.0
    gain_eur = POSITION_EUR * pct
    high_water = max(st["high_water"], last)
    st["high_water"] = high_water
    msgs = []

    # Gewinnstufen
    for factor, tip in TIERS:
        if pct >= factor and factor not in st["alerted"]:
            st["alerted"].append(factor)
            msgs.append(
                "TAKE-PROFIT: ONE bei {}  {:+d} % gegenueber Ref {}  "
                "(Gewinn ~{}) - {}".format(
                    usd(last), round(pct * 100), usd(BASELINE), eur(gain_eur), tip))

    if len(st["alerted"]) == len(TIERS):
        st["alerted"].clear()      # Zyklus wiederholbar, falls Kurs erneut steigt

    # Sicherungsschwelle (Trailing): gefallen aus dem Hochpunkt
    if last <= high_water * (1.0 - SAFETY_DROP) and high_water > BASELINE * 1.5:
        msgs.append(
            "SICHERUNG: ONE bei {}  {:.0f}% unter Hochpunkt {}  (Tages-High {}). "
            "Gewinn nicht zurueckgeben - Teil sichern.".format(
                usd(last), round((1 - last / high_water) * 100),
                usd(high_water), usd(high24)))

    # Liquidationsnaehe (10x Hebel)
    if last <= st["high_water"] * (1.0 - LAQ_DROP):
        if not st["laq_alerted"]:
            st["laq_alerted"] = True
            msgs.append(
                "LIQUIDATIONSWARNUNG: ONE {} ist {:.0f}% unter den Bestwert {} "
                "gefallen - bei 10x Hebel droht die Boersen-Schliessung. "
                "Position sichern oder verkleinern!".format(
                    usd(last), round((1 - last / st["high_water"]) * 100),
                    usd(st["high_water"])))
    elif last >= st["high_water"] * (1.0 - LAQ_DROP + 0.05):
        st["laq_alerted"] = False   # aus der Gefahr wieder raus

    save_state(st)
    if not msgs:
        return ""
    return "\n".join(msgs)


if __name__ == "__main__":
    out = main()
    if out:
        print(out)