"""Papier-Ausfuehrung fuer Fremd-Signale (kraken-cli, OKX Agent Trade Kit).

Nimmt Journal-Zeilen `was="signal"` (vom Bus, nach dem Tor), prueft das Tor
bei der Ausfuehrung ERNEUT und fuehrt sie in einem eigenen Papierbuch aus.
Es gibt hier keinen Orderweg: der Kurs wird uebergeben, nichts geht an eine
Boerse, `live` kann dieses Modul nicht.

Regeln (Hausregeln, Werte in fremd_signale/wachen.json)
------------------------------------------------------
* Stop ist Pflicht: `stop_prozent` muss in [pflicht_stop_prozent_min,
  pflicht_stop_prozent_max] liegen, sonst keine Position.
* Groesse: min(risiko_je_position_usd / stop%, size_pct * max_pro_trade_usd).
* Grenzen: max_offene_positionen, max_gesamt_usd, ein Instrument nur einmal,
  Kill-Switch: realisierter Verlust >= kill_switch_gesamt_usd -> keine neuen.
* Gebuehr: gebuehr_taker auf beide Seiten.
* Jedes Signal (Journal-id) wird genau einmal verarbeitet.
* Ein Kursausfall haelt Positionen offen und wirft nie.
"""
import json
import math

import fremd_tor


def leer():
    return {"offen": {}, "geschlossen": [], "verarbeitet": [], "pnl_usd": 0.0}


def _zahl(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _stop_prozent(wache):
    s = wache.get("stop_prozent")
    lo, hi = wache.get("pflicht_stop_prozent_min"), wache.get("pflicht_stop_prozent_max")
    if not (_zahl(s) and _zahl(lo) and _zahl(hi)) or not (0 < lo <= s <= hi):
        return None
    return float(s)


def _gebuehr(menge, wache):
    g = wache.get("gebuehr_taker")
    return 2 * menge * g if _zahl(g) else 0.0


def _schliesse(zustand, inst, preis, grund, jetzt, wache):
    p = zustand["offen"].pop(inst)
    r = (preis - p["einstieg"]) / p["einstieg"]
    if p["richtung"] == "short":
        r = -r
    pnl = p["menge_usd"] * r - _gebuehr(p["menge_usd"], wache)
    zustand["geschlossen"].append({
        "instrument": inst, "richtung": p["richtung"], "einstieg": p["einstieg"],
        "ausstieg": preis, "menge_usd": p["menge_usd"], "pnl_usd": pnl,
        "grund": grund, "signal_id": p["signal_id"], "zeit": jetzt})
    zustand["pnl_usd"] += pnl
    return pnl


def eroeffne(zustand, signal, preis, wache, sig_id, jetzt):
    """Fuehrt ein Signal im Papierbuch aus. (ok, grund). Aendert nur bei ok."""
    inst = signal["instrument"]
    if not _zahl(preis) or preis <= 0:
        return False, "kein gueltiger Preis"
    if signal["direction"] == "flat":
        if inst not in zustand["offen"]:
            return False, "nichts offen zum Schliessen"
        _schliesse(zustand, inst, float(preis), "signal_flat", jetzt, wache)
        return True, "ok"
    stop_pct = _stop_prozent(wache)
    if stop_pct is None:
        return False, "Stop-Regel fehlt oder ausserhalb der Pflichtgrenzen"
    if inst in zustand["offen"]:
        return False, "Instrument schon offen"
    n = wache.get("max_offene_positionen")
    if not _zahl(n) or len(zustand["offen"]) >= n:
        return False, "max_offene_positionen erreicht"
    kill = wache.get("kill_switch_gesamt_usd")
    if _zahl(kill) and zustand["pnl_usd"] <= -kill:
        return False, "Kill-Switch: Verlust %.2f USD" % -zustand["pnl_usd"]
    risiko, deckel = wache.get("risiko_je_position_usd"), wache.get("max_pro_trade_usd")
    if not (_zahl(risiko) and risiko > 0 and _zahl(deckel) and deckel > 0):
        return False, "Risiko-/Deckelwerte fehlen in der Wache"
    menge = min(risiko / (stop_pct / 100.0), signal["size_pct"] * deckel)
    offen = sum(p["menge_usd"] for p in zustand["offen"].values())
    gesamt = wache.get("max_gesamt_usd")
    if not _zahl(gesamt) or offen + menge > gesamt:
        return False, "max_gesamt_usd ueberschritten"
    long_ = signal["direction"] == "long"
    stop = preis * (1 - stop_pct / 100.0) if long_ else preis * (1 + stop_pct / 100.0)
    zustand["offen"][inst] = {
        "richtung": signal["direction"], "einstieg": float(preis), "stop": stop,
        "menge_usd": menge, "signal_id": sig_id, "quelle": signal["source"],
        "mode": signal["mode"], "zeit": jetzt}
    return True, "ok"


def stops_pruefen(zustand, kurs_fn, wache, jetzt):
    """Schliesst jede Position, deren Stop gerissen wurde. Kursausfall = halten."""
    for inst in list(zustand["offen"]):
        try:
            preis = float(kurs_fn(inst))
        except Exception:                                   # noqa: BLE001
            continue
        if not math.isfinite(preis) or preis <= 0:
            continue
        p = zustand["offen"][inst]
        if (p["richtung"] == "long" and preis <= p["stop"]) or \
           (p["richtung"] == "short" and preis >= p["stop"]):
            _schliesse(zustand, inst, preis, "stop", jetzt, wache)


def verarbeite(zustand, zeilen, kurs_fn, wache, jetzt):
    """Journal-Zeilen abarbeiten. Gibt die Liste der Ergebnisse (id, ok, grund)."""
    ergebnis = []
    for z in zeilen:
        if not isinstance(z, dict) or z.get("was") != "signal":
            continue
        sid = z.get("id")
        if not sid or sid in zustand["verarbeitet"]:
            continue
        zustand["verarbeitet"].append(sid)
        try:
            signal = json.loads(z.get("text") or "")
        except ValueError:
            ergebnis.append((sid, False, "Text kein JSON"))
            continue
        ok, grund = fremd_tor.entscheide(signal, wache, jetzt)
        if ok:
            try:
                preis = kurs_fn(signal["instrument"])
            except Exception as f:                          # noqa: BLE001
                ok, grund = False, "Kurs nicht lesbar: %s" % type(f).__name__
            else:
                ok, grund = eroeffne(zustand, signal, preis, wache, sid, jetzt)
        ergebnis.append((sid, ok, grund))
    zustand["verarbeitet"] = zustand["verarbeitet"][-500:]
    return ergebnis
