"""LLM-Filter fuer xperp - das Sprachmodell als zusaetzliches Gatter.

ANLASS (06.10.2026, Auftrag Max: "xperp mit KI"): xperp hat 81 Runden,
Excess +1,39 % - die einzige Spur mit positivem Excess. Das LLM soll die
Kandidaten filtern, nicht die Einstiegslogik ersetzen.

WIE ES FUNKTIONIERT
-------------------
1. `filter_kandidaten()` bekommt eine Liste von Kandidaten (aus `anlauf()`)
2. Fuer jeden Kandidaten wird ein Prompt gebaut (Marktbild + Kandidat)
3. `llm_lokal.entscheide()` fragt das Modell und gibt (seite, info) zurueck
4. Nur wenn die Richtung des Modells mit der Richtung des Kandidaten
   uebereinstimmt, wird der Kandidat weitergegeben

KONFIGURATION (wachen.json)
----------------------------
- `llm_aktiv`: True/False - schaltet den Filter ein/aus
- `llm_mindest_confidence`: 0-100 - Schwelle (Vorgabe 60)
- `llm_modell`: Modellname (Vorgabe "bonsai")
- `llm_weg`: "bonsai" oder "ollama" (Vorgabe aus Modellname)

REGELN
------
- Das LLM ersetzt KEINE Risikosteuerung, nur die Richtungsentscheidung
- Ein NEUTRAL oder eine falsche Richtung heisst: kein Trade
- Das LLM ist langsam (1-3 s) -> nur fuer langsamere Zeitraeume (1H, 4H, 1D)
- Der Prompt ist deterministisch: dieselben Kerzen = dieselbe Antwort
"""

import os
import sys
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
if HANDEL not in sys.path:
    sys.path.append(HANDEL)

from llm_lokal import entscheide as _llm_entscheide, VERTRAG


def _marktbild_prompt(a, kerzen=None, indikatoren=None, position=None):
    """Baut den Prompt fuer das LLM.

    `a` ist das Ergebnis von `anlauf()` - es enthaelt Basis, Seite, Punkte, etc.
    `kerzen` ist eine Liste [ts, o, h, l, c, v] (wie okxf.kerzen()).
    `indikatoren` ist ein Dict {"RSI": 45.2, "MACD": 0.001, ...}.
    `position` ist die aktuelle Position (falls vorhanden).
    """
    zeilen = []
    zeilen.append("Marktbild fuer %s (%s):" % (a["basis"], a["seite"]))
    zeilen.append("")

    # Kerzen
    if kerzen:
        zeilen.append("Letzte %d Kerzen (1H):" % len(kerzen))
        for k in kerzen[-20:]:
            ts, o, h, l, c, v = k
            zeilen.append("  %s  O %.4f  H %.4f  L %.4f  C %.4f  V %.2f" % (
                datetime.fromtimestamp(ts / 1000, timezone.utc).strftime("%m-%d %H:%M"),
                o, h, l, c, v))
        zeilen.append("")

    # Indikatoren
    if indikatoren:
        zeilen.append("Indikatoren:")
        for name, wert in indikatoren.items():
            if wert is not None:
                zeilen.append("  %s: %.4f" % (name, wert))
        zeilen.append("")

    # Kandidat
    zeilen.append("Kandidat: %s %s (Punkte: %.1f)" % (
        a["basis"], a["seite"], a.get("punkte", 0)))
    zeilen.append("")

    # Position (falls vorhanden)
    if position:
        zeilen.append("Aktuelle Position: %s %s @ %.6f (Stop %.6f, Ziel %.6f)" % (
            position.get("inst", ""), position.get("seite", ""),
            position.get("einstieg", 0), position.get("stop", 0),
            position.get("ziel", 0)))
        zeilen.append("")

    # Vertrag
    zeilen.append(VERTRAG)

    return "\n".join(zeilen)


def urteile_kandidat(kandidat, lage, k, w, position=None):
    """LLM-Urteil fuer einen einzelnen Kandidaten.

    `kandidat` ist das Ergebnis von `kandidaten()` (basis, seite, punkte, ...).
    `lage` ist das Ergebnis von `indikatoren.lage()` (signal, rsi, macd, ...).
    `k` ist eine Liste von Kerzen [ts, o, h, l, c, v] (wie okxf.kerzen()).
    `position` ist die aktuelle Position (falls vorhanden).

    Rueckgabe: (seite, info)
    - seite: 'long', 'short' oder None (None = kein Trade)
    - info: Dict mit Confidence, Aktion, Begruendung oder Fehler
    """
    if not w.get("llm_aktiv"):
        return None, {"fehler": "llm_aktiv false"}

    prompt = _marktbild_prompt(kandidat, kerzen=k, indikatoren=lage, position=position)
    seite, info = _llm_entscheide(prompt, w)

    if seite is None:
        return None, info

    # Richtung muss zum Kandidaten passen
    if seite != kandidat.get("seite"):
        return None, {"fehler": "Richtung passt nicht", "llm_seite": seite}

    return seite, info


def filter_kandidaten(kandidaten, w, kerzen=None, indikatoren=None, position=None):
    """Filtert eine Liste von Kandidaten durch das LLM.

    Rueckgabe: (gefilterte_kandidaten, befunde)
    - gefilterte_kandidaten: Kandidaten, deren Richtung das LLM bestaetigt hat
    - befunde: Liste von {"kandidat": k, "seite": seite, "info": info} fuer alle
    """
    if not w.get("llm_aktiv"):
        return kandidaten, []

    gefiltert = []
    befunde = []
    for k in kandidaten:
        prompt = _marktbild_prompt(k, kerzen, indikatoren, position)
        seite, info = _llm_entscheide(prompt, w)
        befunde.append({"kandidat": k, "seite": seite, "info": info})
        if seite == k["seite"]:
            gefiltert.append(k)
    return gefiltert, befunde
