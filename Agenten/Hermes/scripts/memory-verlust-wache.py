#!/usr/bin/env python3
"""Wache: meldet NEUE Memory-Verluste und eine verrottende Vorschlags-Queue, sonst nichts.

Ein `replace` mit falsch gewaehltem `old_text` loescht einen fremden Eintrag
vollstaendig (30.09.2026: 'HERMES-CONFIG 30.09.2026', 1117 Zeichen). Das Werkzeug
memory-verlust.py kann das messen - diese Wache ruft es auf und meldet nur, was
SEIT DEM LETZTEN LAUF neu dazugekommen ist.

Zweite Messung: `pending/memory/` (Konsolidierungsvorschlaege aus `background_review`).
Ein Vorschlag verfaellt mit seinem Anker, und ungepinnte Vorschlaege (aus der Zeit vor
`matched_entry`) kann `/memory approve` nie anwenden - 25 solche Dateien lagen vom 09. bis
24.09.2026 unbemerkt herum (T-245/T-247). Gemeldet wird: Queue aelter als QUEUE_MAX_TAGE
Tage, Vorschlaege ohne Pin, unlesbare Dateien. Ein frischer, gepinnter Vorschlag ist
KEIN Befund.

Bauart (Hausregel): leere Ausgabe = nichts senden. Der erste Lauf legt die
Merkdatei an und schweigt (die Altfaelle sind bekannt, siehe T-246).

Aufruf:
  python memory-verlust-wache.py            # meldet nur Neues
  python memory-verlust-wache.py --alles    # zeigt auch die Altfaelle (Handbetrieb)
  python memory-verlust-wache.py --queue    # nur der Zustand der Queue (Handbetrieb)
  python memory-verlust-wache.py --neu-baseline   # Merkdatei neu setzen
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HERMES = os.path.dirname(HIER)
MERKER = os.path.join(HERMES, "cache", "memory-verlust-wache.json")
WERKZEUG = os.path.join(HIER, "memory-verlust.py")
QUEUE = os.path.join(HERMES, "pending", "memory")
QUEUE_MAX_TAGE = 7
MAX_ZEILEN = 5
PRO_ZEILE = 160


def werkzeug_laden(pfad=WERKZEUG):
    spec = importlib.util.spec_from_file_location("memory_verlust", pfad)
    m = importlib.util.module_from_spec(spec)
    sys.modules["memory_verlust"] = m
    spec.loader.exec_module(m)
    return m


def kennung(eintrag):
    """Stabile Kennung eines Verlusts: der Anfang seines Textes."""
    roh = " ".join(eintrag["text"].split())[:200].lower()
    return hashlib.sha1(roh.encode("utf-8")).hexdigest()


def merker_lesen(pfad=MERKER):
    try:
        with open(pfad, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get("bekannt"), list):
        return None
    return d


def merker_schreiben(d, pfad=MERKER):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8", newline="") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def _destructive_ops(payload):
    """Dieselbe Regel wie `tools/memory_tool.destructive_ops` im Hermes-Checkout:
    `replace`/`remove`, einzeln oder in einem Batch. Eine solche Operation wird beim
    Genehmigen NUR angewandt, wenn sie beim Einlagern gepinnt wurde (`matched_entry`)."""
    ops = (payload.get("operations") or []) if payload.get("action") == "batch" else [payload]
    return [op for op in ops if (op or {}).get("action") in ("replace", "remove")]


def queue_lage(ordner=QUEUE, jetzt=None):
    """Zustand der Vorschlags-Queue `pending/memory/`.

    Ein Vorschlag verfaellt mit seinem Anker: er traegt `old_text`/`content`, und
    `matched_entry` gibt es nur bei Vorschlaegen, die NACH dem Pin eingelagert wurden.
    Ungepinnte Vorschlaege kann `/memory approve` nie anwenden (Verweigerung in
    `tools/memory_tool.apply_memory_pending`) - sie muessen geprueft oder geloescht werden.
    """
    import time as _time
    jetzt = _time.time() if jetzt is None else jetzt
    lage = {"anzahl": 0, "aeltester_tage": None, "ungepinnt": [], "unlesbar": []}
    if not os.path.isdir(ordner):
        return lage
    for name in sorted(os.listdir(ordner)):
        if not name.endswith(".json"):
            continue
        pfad = os.path.join(ordner, name)
        try:
            with open(pfad, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            lage["unlesbar"].append(name)
            continue
        lage["anzahl"] += 1
        try:
            alter = (jetzt - float(d.get("created_at") or jetzt)) / 86400.0
        except (TypeError, ValueError):
            alter = 0.0
        if lage["aeltester_tage"] is None or alter > lage["aeltester_tage"]:
            lage["aeltester_tage"] = alter
        payload = d.get("payload") or {}
        if any(not op.get("matched_entry") for op in _destructive_ops(payload)):
            lage["ungepinnt"].append(str(d.get("id") or name[:-5]))
    return lage


def queue_befunde(lage, max_tage=QUEUE_MAX_TAGE):
    """Befunde als (Schluessel, Text) - der Schluessel traegt KEINE Zahl, damit eine
    wachsende Queue nicht jeden Tag erneut meldet. Leere Liste = nichts zu melden."""
    befunde = []
    if lage["unlesbar"]:
        befunde.append(("unlesbar",
                        "Memory-Queue: %d Datei(en) nicht lesbar (%s) - diese Vorschlaege "
                        "koennen nie angewandt werden."
                        % (len(lage["unlesbar"]), ", ".join(lage["unlesbar"][:5]))))
    if lage["ungepinnt"]:
        befunde.append(("ungepinnt",
                        "Memory-Queue: %d Vorschlag/Vorschlaege ohne Pin (%s) - sie stammen aus "
                        "der Zeit vor `matched_entry`, `/memory approve` verweigert sie; Inhalt "
                        "von Hand pruefen und nachziehen oder die Datei loeschen."
                        % (len(lage["ungepinnt"]), ", ".join(lage["ungepinnt"][:5]))))
    if lage["aeltester_tage"] is not None and lage["aeltester_tage"] > max_tage:
        befunde.append(("verrottet",
                        "Memory-Queue verrottet: %d Vorschlag/Vorschlaege, aeltester %.0f Tage alt "
                        "(Grenze %d) - ein Vorschlag verfaellt mit seinem Anker."
                        % (lage["anzahl"], lage["aeltester_tage"], max_tage)))
    return befunde


def queue_meldung(befunde):
    zeilen = ["Pending-Memory-Queue (%d Befund(e)):" % len(befunde)]
    zeilen.extend("- " + text for _, text in befunde)
    zeilen.append("Stand: python Agenten/Hermes/scripts/memory-verlust-wache.py --queue")
    return "\n".join(zeilen)


def meldung(neu):
    zeilen = ["Memory-Verlust: %d neue(r) Eintrag/Eintraege fehlen im Gedaechtnis." % len(neu)]
    for v in neu[:MAX_ZEILEN]:
        text = " ".join(v["text"].split())
        zeilen.append("- %s | %s | %s | %d Zeichen\n  %s"
                      % (v["ts"], v["art"], v["sid"], len(v["text"]),
                         text[:PRO_ZEILE] + ("..." if len(text) > PRO_ZEILE else "")))
    if len(neu) > MAX_ZEILEN:
        zeilen.append("... und %d weitere" % (len(neu) - MAX_ZEILEN))
    zeilen.append("Volltexte: python Agenten/Hermes/scripts/memory-verlust.py --alles")
    zeilen.append("Ursache pruefen: im Ergebnis des replace/remove steht unter "
                  "replaced_entries, WELCHER Eintrag getroffen wurde.")
    return "\n".join(zeilen)


def lauf(db=None, memory=None, merkerpfad=MERKER, alles=False, neu_baseline=False,
         queue_ordner=QUEUE, jetzt=None):
    """Gibt den Meldetext zurueck - leer heisst: nichts senden.

    Zwei Messungen: NEUE Memory-Verluste (Merkdatei `bekannt`) und der Zustand der
    Vorschlags-Queue (Merkdatei `queue`). Jeder Befund wird genau EINMAL gemeldet; die
    Schluessel tragen keine Zahlen, damit eine wachsende Queue nicht taeglich meldet.
    """
    mv = werkzeug_laden()
    kwargs = {}
    if db:
        kwargs["db"] = db
    if memory:
        kwargs["memory"] = memory
    try:
        verluste = mv.verluste(**kwargs)
    except Exception as e:                                  # noqa: BLE001 - Wache muss melden
        return "Memory-Wache FEHLER: Verluste nicht messbar (%s: %s)" % (type(e).__name__, e)

    try:
        befunde = queue_befunde(queue_lage(queue_ordner, jetzt=jetzt))
    except Exception as e:                                  # noqa: BLE001 - Wache muss melden
        return "Memory-Wache FEHLER: Queue nicht messbar (%s: %s)" % (type(e).__name__, e)

    merker = merker_lesen(merkerpfad)
    if merker is None or neu_baseline:
        merker_schreiben({"bekannt": [kennung(v) for v in verluste],
                          "queue": [k for k, _ in befunde],
                          "stand": "Baseline gesetzt"}, merkerpfad)
        if neu_baseline:
            return ("Memory-Wache: Merkdatei neu gesetzt, %d Altfaelle und %d Queue-Befund(e) "
                    "als bekannt vermerkt." % (len(verluste), len(befunde)))
        return ""                                           # erster Lauf schweigt

    bekannt = set(merker.get("bekannt") or [])
    neu = [v for v in verluste if kennung(v) not in bekannt]
    gemeldet = set(merker.get("queue") or [])
    jetzt_keys = {k for k, _ in befunde}
    neue_befunde = [b for b in befunde if b[0] not in gemeldet]

    if not neu and not neue_befunde and not (gemeldet - jetzt_keys):
        return ""
    merker["bekannt"] = sorted(bekannt | {kennung(v) for v in neu})
    merker["queue"] = sorted(jetzt_keys)
    merker_schreiben(merker, merkerpfad)

    stuecke = []
    if alles and verluste:
        stuecke.append(meldung(verluste))
    elif neu:
        stuecke.append(meldung(neu))
    if neue_befunde:
        stuecke.append(queue_meldung(neue_befunde))
    elif gemeldet - jetzt_keys:
        # Erholung: die gemeldeten Queue-Befunde sind weg - einmal sagen, damit Stille
        # nicht von einer kaputten Messung zu unterscheiden ist.
        stuecke.append("Memory-Queue: keine Befunde mehr (%s erledigt)."
                       % ", ".join(sorted(gemeldet - jetzt_keys)))
    return "\n\n".join(stuecke)


def queue_stand(ordner=QUEUE, jetzt=None):
    """Handbetrieb: Zustand der Queue, unabhaengig von der Merkdatei."""
    lage = queue_lage(ordner, jetzt=jetzt)
    zeilen = ["Vorschlaege: %d" % lage["anzahl"],
              "aeltester: %s" % ("-" if lage["aeltester_tage"] is None
                                 else "%.1f Tage" % lage["aeltester_tage"]),
              "ohne Pin: %d%s" % (len(lage["ungepinnt"]),
                                  (" (%s)" % ", ".join(lage["ungepinnt"][:8])) if lage["ungepinnt"] else ""),
              "unlesbar: %d" % len(lage["unlesbar"])]
    befunde = queue_befunde(lage)
    zeilen.append("Befunde: %d" % len(befunde))
    zeilen.extend("  - " + text for _, text in befunde)
    return "\n".join(zeilen)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--alles", action="store_true", help="auch die bekannten Altfaelle zeigen")
    ap.add_argument("--neu-baseline", action="store_true", help="Merkdatei neu setzen")
    ap.add_argument("--merker", default=MERKER)
    ap.add_argument("--queue", action="store_true",
                    help="nur den Zustand der Vorschlags-Queue zeigen (Handbetrieb)")
    a = ap.parse_args(argv)
    if a.queue:
        print(queue_stand())
        return 0
    text = lauf(merkerpfad=a.merker, alles=a.alles, neu_baseline=a.neu_baseline)
    if text:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())