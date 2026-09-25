"""Pruefstand fuer die lokale Modellwahl der LLM-Spuren - reine Diagnose.

Fragt jedes im Ollama-Bestand vorhandene Modell mit DENSELBEN Marktbildern, die
die Spuren stellen (Wale, Liquidationen, Schlagzeilen) und misst drei Dinge:

  1. **Vertragstreue** - genau drei Zeilen, Zeile 1 BUY/SELL/NOTHING, Zeile 3
     "Confidence: X%". Ein Modell, das hier streut, wuerde in der Spur nichts
     handeln. Gemessen wird ZWEIMAL: die erste Antwort und - falls sie unlesbar
     war - die Antwort nach dem Nachfassen (siehe `llm_lokal.NACHFASSEN`).
  2. **Urteil** - welche Richtung und welche Confidence es vergibt.
  3. **Dauer** - Sekunden je Aufruf, kalt (erstes Mal, Modell muss in den
     Speicher) und warm.

Wiederholbar: Temperatur 0 und fester Seed (siehe llm_lokal). Mehrere
Durchlaeufe mit `--wiederholungen 3` zeigen, ob das Modell bei gleichem Bild
kippt.

Kein Schalter, der etwas in eine Spur schreibt: der Pruefstand liest nur.

Aufruf:
  ..\\scanner\\.venv\\Scripts\\python.exe llm_probe.py --wiederholungen 2
  ..\\scanner\\.venv\\Scripts\\python.exe llm_probe.py --modelle gemma-e4b-8k:latest
"""

import argparse
import os
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
for p in (HIER, os.path.join(HIER, "scanner")):
    if p not in sys.path:
        sys.path.insert(0, p)

import llm_lokal as llm  # noqa: E402

# Dieselben Marktbilder wie in den Spuren - nur mit festen Zahlen, damit zwei
# Modelle wirklich dasselbe lesen.
BILDER = {
    "wale": llm.VERTRAG + """
Analyze BTC with +4.10% OI change in 15m:
Current OI: $3,120,000,000
Previous OI: $2,997,000,000
Price 1h: +0.8%, volume rising
""",
    "liquidation": llm.VERTRAG + """
Analyze BTC liquidations:
Total liquidated: $1,431,060 over the last 112 minutes
(767,931 USD per hour, 100 events)

Current Long Liquidations: $606,423
Current Short Liquidations: $824,638
Long share: 0.42 of the total

Market Data (last 5 15m candles):
  15.09. 23:30 UTC  o=75700.4 h=75714.8 l=75521.2 c=75648.7 vol=64278
  16.09. 00:30 UTC  o=75822.3 h=75840.4 l=75764.3 c=75796.0 vol=10037

Large long liquidations often indicate potential bottoms (shorts taking profit)
Large short liquidations often indicate potential tops (longs taking profit)
Consider the ratio of long vs short liquidations and their relative changes
""",
    "schlagzeilen": llm.VERTRAG + """
Analyze the sentiment of the latest crypto headlines for BTC:

1. "Spot Bitcoin ETFs See Third Straight Day of Outflows"
2. "Exchange Reserves Fall to Lowest Level Since 2021"
3. "Analysts Warn of Leverage Build-Up in Perpetual Futures"

Market: BTC 24h -2.40%, 1h -0.50%

Judge the TONE of the headlines, not the price alone.
If the headlines point in no clear direction, answer NOTHING.
""",
}


def frage(modell, prompt, mit_denken=False, tokens=None):
    """Eine rohe Frage ohne Zwischenspeicher. Rueckgabe: (text, dauer, fehler).

    Der WEG gehoert dazu (25.09.2026): die Sonde rief frueher `_echte_anfrage`
    direkt und damit IMMER Ollama - ein zweites Modell wie Bonsai (nur /v1)
    konnte sie nicht messen und meldete es als "(leer)". Jetzt entscheidet
    `llm.weg_aus`, und der Denk-Schalter wird je Weg uebersetzt (Ollama:
    `num_predict`, Bonsai: `reasoning_effort`).
    """
    t0 = time.time()
    weg = llm.weg_aus(modell)
    try:
        llm.leere_cache()
        if weg == "bonsai":
            alt = llm.BONSAI_REASONING
            llm.BONSAI_REASONING = "medium" if mit_denken else "none"
            try:
                text = llm._bonsai_anfrage(prompt, modell, llm.ZEITGRENZE)
            finally:
                llm.BONSAI_REASONING = alt
        elif mit_denken:
            alt = llm.NUM_PREDICT
            llm.NUM_PREDICT = tokens or 80
            try:
                text = llm._echte_anfrage(prompt, modell, llm.ZEITGRENZE)
            finally:
                llm.NUM_PREDICT = alt
        else:
            text = llm._echte_anfrage(prompt, modell, llm.ZEITGRENZE)
    except Exception as e:                                     # noqa: BLE001
        return None, time.time() - t0, str(e)[:120]
    return text, time.time() - t0, None


def eine_runde(modell, prompt, mit_denken=False):
    """Erste Antwort, bei Unlesbarkeit nachfassen. Rueckgabe: dict."""
    text, dauer, fehler = frage(modell, prompt, mit_denken)
    aus = {"dauer": dauer, "fehler": fehler, "roh": text,
           "erste_ok": False, "zweite_ok": False, "nachgefasst": False,
           "aktion": None, "confidence": None, "grund": "", "dauer2": None}
    if fehler:
        return aus
    u = llm.urteil(text)
    if u is not None and u["confidence"] is not None:
        aus.update({"erste_ok": True, "aktion": u["aktion"],
                    "confidence": u["confidence"], "grund": u["grund"]})
        return aus
    zweiter, dauer2, fehler2 = frage(modell, prompt + "\n\n" + llm.NACHFASSEN,
                                     mit_denken)
    aus.update({"nachgefasst": True, "dauer2": dauer2, "roh2": zweiter,
                "fehler2": fehler2})
    u2 = llm.urteil(zweiter) if zweiter else None
    if u2 is not None and u2["confidence"] is not None:
        aus.update({"zweite_ok": True, "aktion": u2["aktion"],
                    "confidence": u2["confidence"], "grund": u2["grund"]})
    return aus


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelle", nargs="*", default=None,
                    help="Modelle (Vorgabe: alle im Ollama-Bestand)")
    ap.add_argument("--wiederholungen", type=int, default=1)
    ap.add_argument("--mit-denken", action="store_true",
                    help="Denken AN lassen (Gegenbeweis zu Regel 1)")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    vorhanden = llm.modelle()
    if vorhanden is None:
        print("Ollama auf %s nicht erreichbar - kein Vergleich moeglich."
              % llm.OLLAMA)
        return 2
    modelle = a.modelle or vorhanden
    print("Ollama-Bestand: %s" % ", ".join(vorhanden))
    print("Denken: %s   Wiederholungen je Bild: %d"
          % ("AN" if a.mit_denken else "aus", a.wiederholungen))
    print()

    zeilen = []
    for modell in modelle:
        gesamt = erste = zweite = 0
        dauern, richtungen, beispiele = [], [], []
        for name, prompt in BILDER.items():
            for _ in range(max(1, a.wiederholungen)):
                r = eine_runde(modell, prompt, a.mit_denken)
                gesamt += 1
                if r["dauer"] is not None:
                    dauern.append(r["dauer"])
                if r["erste_ok"]:
                    erste += 1
                if r["zweite_ok"]:
                    zweite += 1
                ok = r["erste_ok"] or r["zweite_ok"]
                if ok:
                    richtungen.append(r["aktion"])
                    beispiele.append("%s=%s %.0f%%%s"
                                     % (name, r["aktion"], r["confidence"],
                                        " (nachgefasst)"
                                        if r["nachgefasst"] else ""))
                else:
                    roh = (r.get("roh") or "").replace("\n", " | ")[:70]
                    beispiele.append("%s=UNLESBAR: %s" % (name, roh or "(leer)"))
        lesbar = erste + zweite
        schnitt = sum(dauern) / float(len(dauern)) if dauern else 0.0
        kalt = dauern[0] if dauern else 0.0
        zeilen.append((modell, gesamt, erste, lesbar, kalt, schnitt, beispiele))
        print("=== %s ===" % modell)
        print("  Vertragstreue erste Antwort: %d/%d   nach Nachfassen: %d/%d"
              % (erste, gesamt, lesbar, gesamt))
        print("  Dauer: kalt %.1f s, im Mittel %.1f s" % (kalt, schnitt))
        for b in beispiele:
            print("    %s" % b)
        print()

    print("ZUSAMMENFASSUNG")
    print("%-24s %8s %10s %8s" % ("Modell", "lesbar", "kalt s", "mittel s"))
    for modell, gesamt, erste, lesbar, kalt, schnitt, _ in zeilen:
        print("%-24s %5d/%-3d %9.1f %8.1f"
              % (modell, lesbar, gesamt, kalt, schnitt))
    bestes = None
    for z in zeilen:
        if z[3] < z[1]:
            continue
        if bestes is None or z[3] > bestes[3] or (z[3] == bestes[3]
                                                  and z[5] < bestes[5]):
            bestes = z
    if bestes:
        print("\nEmpfehlung: %s (Vertrag vollstaendig gehalten, im Mittel "
              "%.1f s)" % (bestes[0], bestes[5]))
    else:
        print("\nKein Modell hielt den Vertrag in allen Aufrufen - die "
              "Nachfassen-Regel in llm_lokal ist noetig.")
    print("Vorgabe in llm_lokal.MODELL_STANDARD: %s" % llm.MODELL_STANDARD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
