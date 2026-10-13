"""LLM-Entscheid auf den Einstieg. Ein Ausfall heisst NOTHING, nie der Regelarm."""
import hashlib
import json
import re
import urllib.request

VORLAGE = """You are a trading assistant. Decide on the candidate signal below.

Market data (last closed 1H candle):
{daten}

Answer in this exact format:
1. First line must be one of: BUY, SELL, or NOTHING
2. Then your reasoning in 2-3 sentences
3. Last line: Confidence: NN%
"""


def _sma(werte, n):
    return sum(werte[-n:]) / n if len(werte) >= n else None


def momentaufnahme(kerzen, variante, kandidat_seite, stop_pct):
    """Kennzahlen nach dem Vorbild moondev trading_agent: MA20/MA40, Volumen, 24-h-Rendite."""
    c = [float(z[4]) for z in kerzen]
    # Ohne Volumenspalte (Bestandsdatei mit 5 Spalten) bleibt das Feld leer, statt zu brechen.
    v = [float(z[5]) for z in kerzen] if all(len(z) > 5 for z in kerzen) else None
    kurs = c[-1]
    return {
        "variante": variante,
        "kandidat": kandidat_seite,
        "schluss": kurs,
        "ma20": _sma(c, 20),
        "ma40": _sma(c, 40),
        "stop_prozent": round(stop_pct, 2),
        "rendite_24h_pct": round((kurs / c[-25] - 1) * 100, 2) if len(c) > 24 else None,
        "volumen_rel_20": round(v[-1] / (_sma(v, 20) or 1.0), 2) if v else None,
    }


def prompt(snap):
    daten = "\n".join(f"{k}: {snap[k]}" for k in sorted(snap))
    return VORLAGE.format(daten=daten)


def lies_antwort(text):
    """(BUY|SELL|NOTHING|FEHLER, Konfidenz oder None). Ohne Kopfzeile gilt FEHLER."""
    if not text or not text.strip():
        return "FEHLER", None
    kopf = text.strip().splitlines()[0].strip().upper()
    urteil = next((u for u in ("BUY", "SELL", "NOTHING") if kopf.startswith(u)), None)
    if urteil is None:
        return "FEHLER", None
    m = re.search(r"confidence\s*:\s*(\d{1,3})\s*%", text, re.IGNORECASE)
    return urteil, int(m.group(1)) if m else None


def _rufe_bruecke(p, llm_w):
    body = json.dumps({"model": llm_w["modell"], "temperature": llm_w["temperatur"],
                       "messages": [{"role": "user", "content": p}]}).encode("utf-8")
    req = urllib.request.Request(llm_w["bruecke"] + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=llm_w["timeout_s"]) as r:
        antwort = json.loads(r.read().decode("utf-8"))
    return antwort["choices"][0]["message"]["content"] or ""


def frage(snap, w, aufrufer=None):
    """Fragt das Modell. Jeder Fehler wird zu urteil=FEHLER, nie zu einer Exception."""
    p = prompt(snap)
    h = hashlib.sha256(p.encode("utf-8")).hexdigest()[:16]
    try:
        roh = (aufrufer or _rufe_bruecke)(p, w["llm"])
    except Exception as e:  # noqa: BLE001 - ein Ausfall darf nie zum Einstieg werden
        return {"urteil": "FEHLER", "konfidenz": None,
                "grund": f"{type(e).__name__}: {e}", "prompt_hash": h, "roh": ""}
    urteil, konf = lies_antwort(roh)
    return {"urteil": urteil, "konfidenz": konf, "grund": roh[:300],
            "prompt_hash": h, "roh": roh}


def darf_einsteigen(erg, w):
    """Nur BUY mit Konfidenz ab der Schwelle. Alles andere: kein Einstieg."""
    return erg["urteil"] == "BUY" and (erg["konfidenz"] or 0) >= w["llm"]["konfidenz_min"]
