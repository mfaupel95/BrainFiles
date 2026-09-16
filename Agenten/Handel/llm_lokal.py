"""Der lokale Sprachmodell-Zugang der Handels-Spuren - eine Umsetzung fuer alle.

WARUM DIESE DATEI EXISTIERT
---------------------------
Die Sprachmodell-Agenten des geklonten Bot-Repos (`whale_agent`,
`liquidation_agent`, `sentiment_agent`, `coingecko_agent` ...) lassen ihr URTEIL
in einem Modell fallen - bei Anthropic, DeepSeek oder OpenAI, alle mit
Schluessel und Guthaben. Genau dieses Urteil fehlte den Haus-Spuren bisher; sie
haben es durch eine deterministische Regel ersetzt (siehe README von
`moondev_topmovers` / `moondev_marktlage`). Hier kommt das Urteil zurueck, aber
lokal:

  * **Modell**  : Ollama auf `127.0.0.1:11434` - kein Schluessel, kein Guthaben,
    kein fremder Rechner, keine laufenden Kosten je Abruf,
  * **Vertrag** : wortgleich der des Bots - genau drei Zeilen, Zeile 1
    `BUY`/`SELL`/`NOTHING`, Zeile 3 `Confidence: X%`,
  * **Fehler**  : KEIN Urteil heisst kein Handel. Diese Datei raet nie eine
    Richtung; sie gibt im Zweifel `None` zurueck und die Spur bucht nichts.

REGELN, DIE AUS FEHLERN STAMMEN
-------------------------------
1. `think: false` ist Pflicht. Ein Denk-Modell verbraucht das Token-Kontingent
   im Denken: mit `num_predict: 80` kam ein LEERER `content` zurueck, obwohl die
   Antwort nach 15 s da war (16.09.2026 gemessen, beide lokalen Modelle). Die
   Spur haette nichts gehandelt, und niemand haette gewusst, warum.
2. Temperatur 0 und fester Seed: dasselbe Marktbild ergibt dasselbe Urteil. Ein
   Signal mit Streuung ist nicht nachrechenbar.
3. Die Antwort wird STRENG gelesen. Eine unbekannte erste Zeile ist kein Signal
   (nicht "irgendwie long") - ein Modell, das den Vertrag nicht haelt, handelt
   nicht. Ohne Confidence-Zeile ebenfalls nicht.
4. Die Confidence ist ein GATE, keine Zierde: unter `llm_mindest_confidence`
   (Vorgabe 60 %) faellt das Urteil aus. Der Schwellwert steht in der
   `wachen.json` der Spur, nicht hier.
5. Nur Standardbibliothek (urllib): die Spuren laufen im gemeinsamen venv, das
   kein ollama-Paket kennt.

Werkzeug zum Nachmessen der Modellwahl: `Handel/llm_probe.py`.
"""

import hashlib
import json
import time
import urllib.request

OLLAMA = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"

# Vorgabe-Modell: qwen35-8k (4,3B). Gemessen am 17.09.2026 mit
# `Handel/llm_probe.py --wiederholungen 2` gegen drei Marktbilder (Wale,
# Liquidationen, Schlagzeilen), je 6 Aufrufe:
#   qwen35-8k             6/6 im Vertrag, kalt 7,4 s, im Mittel 1,5 s
#   qwen36-35b-a3b        6/6 im Vertrag, kalt 38,6 s, im Mittel 7,5 s
#   gemma-e4b-8k          2/6 im Vertrag, nach Nachfassen 4/6 ("BS" statt
#                         SELL, einmal ohne Confidence-Zeile)
# genommen ist damit das schnellste Modell, das den Vertrag VOLLSTAENDIG haelt.
# Die Richtungen stimmen ueber alle Modelle ueberein (BUY / SELL / SELL), das
# grosse Modell ist also nicht noetig - wer ein zweites Urteil will, traegt in
# der wachen.json der Spur `llm_modell` auf qwen36-35b-a3b:8k um.
MODELL_STANDARD = "qwen35-8k:latest"
ZEITGRENZE = 120
NUM_PREDICT = 200
SEED = 42
MINDEST_CONFIDENCE = 60.0

# Der Vertrag des Bots, wortgleich - jede Spur haengt ihr Marktbild darunter.
VERTRAG = ("You must respond in exactly 3 lines:\n"
           "Line 1: Only write BUY, SELL, or NOTHING\n"
           "Line 2: One short reason why\n"
           'Line 3: Only write "Confidence: X%" where X is 0-100\n')

# Nachfassen: ein kleines lokales Modell haelt den Vertrag nicht immer ein
# (gemessen am 17.09.2026: gemma-e4b-8k antwortete auf ein echtes
# Liquidationsbild mit "LONGLY" statt "LONG"). Statt das Wort zu raten, wird
# EINMAL nachgefasst - mit derselben Frage und einer haerteren Fassung des
# Vertrags. Bleibt es unlesbar, faellt das Urteil aus (kein Handel).
NACHFASSEN = ("Answer again, exactly 3 lines, nothing else.\n"
              "Line 1 must be ONE word: BUY, SELL or NOTHING.\n"
              "Line 2: one short reason.\n"
              'Line 3: exactly "Confidence: X%" with X between 0 and 100.')

# Zeile 1 -> Hausrichtung. Die Worte des Bots zuerst; LONG/SHORT/HOLD stehen
# daneben, weil ein lokales Modell sie als dasselbe schreibt. Alles andere ist
# KEIN Signal.
AKTIONEN = {"BUY": "long", "LONG": "long",
            "SELL": "short", "SHORT": "short",
            "NOTHING": None, "NONE": None, "HOLD": None, "NEUTRAL": None}

# Test-Seam: None -> echter HTTP-Aufruf. Tests setzen eine Funktion
# (prompt, modell, zeitgrenze) -> Text. Kein Test darf Ollama brauchen.
ANFRAGE = None

# Ein Zyklus fragt dasselbe Marktbild zweimal (Vorschau-Frage des Dauerlaufs
# und Papierlauf). Der Zwischenspeicher spart den zweiten Aufruf und stellt
# sicher, dass beide Laeufe DASSELBE Urteil sehen.
CACHE_SEKUNDEN = 300
_CACHE = {}


def _schluessel(prompt, modell):
    roh = (modell + "\x00" + prompt).encode("utf-8")
    return hashlib.sha1(roh).hexdigest()


def leere_cache():
    _CACHE.clear()


def _aus_cache(schluessel):
    eintrag = _CACHE.get(schluessel)
    if not eintrag:
        return None
    zeit, text = eintrag
    if time.monotonic() - zeit > CACHE_SEKUNDEN:
        del _CACHE[schluessel]
        return None
    return text


def _echte_anfrage(prompt, modell, zeitgrenze):
    koerper = {
        "model": modell,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,           # Regel 1: sonst kommt ein leerer content
        "options": {"temperature": 0, "seed": SEED, "num_predict": NUM_PREDICT},
    }
    daten = json.dumps(koerper).encode("utf-8")
    anfrage = urllib.request.Request(
        OLLAMA, data=daten, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as antwort:
        roh = json.loads(antwort.read().decode("utf-8", "replace"))
    return ((roh.get("message") or {}).get("content") or "").strip()


def frage(prompt, modell=None, zeitgrenze=None):
    """Rohtext des Modells, oder None. Wirft nie - ein Fehler ist kein Urteil."""
    modell = modell or MODELL_STANDARD
    zg = float(zeitgrenze or ZEITGRENZE)
    schluessel = _schluessel(prompt, modell)
    aus_cache = _aus_cache(schluessel)
    if aus_cache is not None:
        return aus_cache
    try:
        text = (ANFRAGE(prompt, modell, zg) if ANFRAGE
                else _echte_anfrage(prompt, modell, zg))
    except Exception as e:                                     # noqa: BLE001
        print("LLM nicht erreichbar (%s): %s" % (modell, str(e)[:150]))
        return None
    if text:
        _CACHE[schluessel] = (time.monotonic(), text)
    return text


def modelle():
    """Die im Ollama-Bestand vorhandenen Modelle, oder None."""
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=10) as antwort:
            daten = json.loads(antwort.read().decode("utf-8", "replace"))
    except Exception:                                          # noqa: BLE001
        return None
    return [m.get("name") for m in daten.get("models", []) if m.get("name")]


def modell_da(name):
    """Ist das Modell da? Unbekannter Bestand (kein Ollama) heisst NEIN."""
    namen = modelle() or []
    return any(n == name or n.split(":")[0] == name.split(":")[0]
               for n in namen)


def urteil(text):
    """Antwort des Modells streng lesen -> dict, oder None.

    Rueckgabe: {"aktion": "BUY", "seite": "long", "confidence": 65.0,
                "grund": "..."}. `grund` ist Zeile 2, wenn vorhanden.
    """
    if not text:
        return None
    zeilen = [z.strip() for z in text.splitlines() if z.strip()]
    if not zeilen:
        return None
    wort = zeilen[0].strip("`*_.: ").upper()
    if wort not in AKTIONEN:
        return None
    confidence = None
    for zeile in zeilen:
        if "conf" not in zeile.lower():
            continue
        ziffern = ""
        for zeichen in zeile:
            if zeichen.isdigit():
                ziffern += zeichen
            elif ziffern:
                break
        if ziffern:
            wert = float(ziffern[:3])
            confidence = wert if 0 <= wert <= 100 else None
            break
    grund = zeilen[1] if len(zeilen) > 1 else ""
    return {"aktion": wort, "seite": AKTIONEN[wort],
            "confidence": confidence, "grund": grund[:200]}


def entscheide(prompt, w=None):
    """Marktbild -> (seite, info). seite ist 'long', 'short' oder None.

    `info` traegt Confidence, Aktion, Begruendung und ob nachgefasst wurde
    (fuer Konsole und Journal-Grund) oder den Grund des Ausfalls - nie eine
    geratene Richtung. Ein unlesbares Urteil wird EINMAL nachgefasst
    (`llm_nachfassen: false` in der wachen.json schaltet das ab).
    """
    w = w or {}
    modell = w.get("llm_modell") or MODELL_STANDARD
    zg = w.get("llm_zeitgrenze_s", ZEITGRENZE)
    roh = frage(prompt, modell, zg)
    if not roh:
        return None, {"fehler": "kein Urteil (%s)" % modell}

    u = urteil(roh)
    info = {}
    if u is None or u["confidence"] is None:
        if not w.get("llm_nachfassen", True):
            return None, {"fehler": "Antwort nicht im Vertrag",
                          "roh": roh.replace("\n", " | ")[:150]}
        zweiter = frage(prompt + "\n\n" + NACHFASSEN, modell, zg)
        u2 = urteil(zweiter) if zweiter else None
        if u2 is None or u2["confidence"] is None:
            return None, {"fehler": "Antwort nicht im Vertrag (auch nach "
                                    "Nachfassen)",
                          "roh": (zweiter or roh).replace("\n", " | ")[:150]}
        u = u2
        info["nachgefasst"] = True

    schwelle = float(w.get("llm_mindest_confidence", MINDEST_CONFIDENCE))
    if u["confidence"] < schwelle:
        info.update({"fehler": "zu unsicher (%.0f%% < %.0f%%)"
                               % (u["confidence"], schwelle),
                     "aktion": u["aktion"], "grund": u["grund"]})
        return None, info
    info.update({"aktion": u["aktion"], "confidence": u["confidence"],
                 "grund": u["grund"], "modell": modell})
    return u["seite"], info


def zeile(info):
    """Kurzfassung fuer die Konsole (nie None)."""
    if not info:
        return "-"
    if info.get("fehler"):
        return "kein Urteil: %s" % info["fehler"]
    return "%s %.0f%% - %s" % (info.get("aktion"), info.get("confidence", 0),
                               (info.get("grund") or "")[:80])
