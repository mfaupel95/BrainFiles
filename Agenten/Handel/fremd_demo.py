"""Plan fuer eine OKX-Demo-Spot-Order aus einem freigegebenen Fremd-Signal.

Rechnet nur, sendet nichts: Hermes (okx-agentkit, spot_place_order) fuehrt den Plan aus
und meldet den Fill zurueck. Gleiche Regeln wie das Papierbuch (fremd_papier.eroeffne):
Tor, Stop-Pflicht, Risiko je Position, Positionszahl, Gesamtdeckel, Kill-Switch.
Spot kann nicht short: direction=short wird abgelehnt. Nur mode=demo, nie live.
"""
import fremd_papier
import fremd_tor


def plane(zustand, signal, preis, wache, sig_id, jetzt):
    """(ok, grund_oder_plan). Bei ok wird das Demo-Buch (zustand) vorgemerkt."""
    ok, grund = fremd_tor.entscheide(signal, wache, jetzt)
    if not ok:
        return False, grund
    if signal["mode"] != "demo":
        return False, "nur mode=demo"
    inst = signal["instrument"]
    if "-" not in inst:
        return False, "kein OKX-Spot-Instrument: %r" % (inst,)
    if signal["direction"] == "short":
        return False, "Spot kann nicht short"
    if signal["direction"] == "flat":
        pos = zustand["offen"].get(inst)
        if not pos:
            return False, "nichts offen zum Schliessen"
        return True, {"aktion": "schliessen", "tool": "spot_place_order", "args": {
            "instId": inst, "tdMode": "cash", "side": "sell", "ordType": "market",
            "sz": "%.8f" % (pos["menge_usd"] / pos["einstieg"])}, "algo_stornieren": True,
            "signal_id": sig_id}
    ok, grund = fremd_papier.eroeffne(zustand, signal, preis, wache, sig_id, jetzt)
    if not ok:
        return False, grund
    pos = zustand["offen"][inst]
    return True, {"aktion": "eroeffnen", "tool": "spot_place_order", "args": {
        "instId": inst, "tdMode": "cash", "side": "buy", "ordType": "market",
        "sz": "%.2f" % pos["menge_usd"], "tgtCcy": "quote_ccy",
        "slTriggerPx": "%.2f" % pos["stop"], "slOrdPx": "-1"}, "signal_id": sig_id}
