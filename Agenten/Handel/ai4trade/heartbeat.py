"""ai4trade.ai-Heartbeat pollen - nur NEUES melden (leere Ausgabe = nichts).

Warum (T-113): Der Agent ``HermesMax2`` (ID 25973, angelegt 29.09.2026) ist auf
https://ai4trade.ai angemeldet, aber niemand pollt seinen Heartbeat. Der
Plattform-Skill nennt ihn "part of normal operation": Antworten auf eigene
Beitraege, Erwaehnungen, neue Follower und Aufgaben kommen AUSSCHLIESSLICH dort
an, nicht per Mail. Ohne Polling ist der Agent passiv.

Zwei Fallen, die beim Bauen Zeit gekostet haben
-----------------------------------------------
1. Der Skill sagt ``Header: X-Claw-Token: <token>`` - die API antwortet damit
   am 28.09.2026 **401 Invalid token**. Richtig ist
   ``Authorization: Bearer <token>`` (gemessen: derselbe Aufruf mit Bearer
   liefert 200 + agent_id). Deshalb probiert dieses Skript BEIDE Wege, damit es
   bei einer spaeteren Umstellung der Plattform nicht still ausfaellt.
2. Die Login-Antwort echot bei einem 422 das Passwort im Feld ``input`` zurueck.
   Ein Fehlerausdruck dieser Antwort kann also ein Geheimnis ins Protokoll
   schreiben - hier wird nur ``detail.loc`` ausgewertet, nie ``input``.

Aufruf (aus ``Agenten/Handel/ai4trade``):

    python heartbeat.py                 # meldet nur Neues, sonst leer
    python heartbeat.py --alles         # zeigt auch, was schon bekannt war
    python heartbeat.py --pruefen       # nur Zugang/Zustand, keine Ausgabe

Zustand: ``cache/heartbeat-stand.json`` (gesehene Nachrichten-Kennungen,
zuletzt gesehener Zeitpunkt). Damit wiederholt der naechste Lauf nichts.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(HIER, ".env")
CACHE = os.path.join(HIER, "cache")
STAND = os.path.join(CACHE, "heartbeat-stand.json")
BASIS = "https://ai4trade.ai"
HEARTBEAT = "/api/claw/agents/heartbeat"
MAX_MELDUNG = 6          # so viele Ereignisse im Klartext, der Rest als Zahl


def _env(pfad=ENV):
    """Schluessel/Werte aus der .env. Werte werden NIE ausgegeben."""
    d = {}
    if not os.path.exists(pfad):
        return d
    with open(pfad, "r", encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#") or "=" not in zeile:
                continue
            k, _, v = zeile.partition("=")
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def zugang(pfad=ENV):
    """Zugangsdaten. Die Umgebung hat Vorrang, die .env ist nur der Rueckfall.

    Damit laeuft der Heartbeat auch dann, wenn keine Datei mit Geheimnissen
    im Projektordner liegt. Werte werden NIE ausgegeben.
    """
    d = _env(pfad)
    for k, v in os.environ.items():
        if k.startswith("AI4TRADE_") and v:
            d[k] = v
    return d


def _post(pfad, koerper, kopf, url=BASIS):
    r = urllib.request.Request(url + pfad,
                               data=json.dumps(koerper).encode("utf-8"))
    r.add_header("Content-Type", "application/json")
    for k, v in kopf.items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=25) as a:
            return a.status, json.loads(a.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        roh = e.read().decode("utf-8", "replace")
        try:
            j = json.loads(roh)
        except ValueError:
            j = {"detail": roh[:200]}
        # Nie das input-Feld (echot das Passwort zurueck).
        if isinstance(j.get("detail"), list):
            j = {"felder": [d.get("loc") for d in j["detail"]]}
        return e.code, j
    except Exception as e:                                      # noqa: BLE001
        return None, {"fehler": str(e)[:200]}


def hole(tok, agent_id, kopf_name="Authorization", wert=None):
    """Ein Heartbeat-Aufruf. Rueckgabe (status, antwort)."""
    kopf = {kopf_name: wert if wert is not None else "Bearer " + tok}
    return _post(HEARTBEAT, {"agent_id": agent_id, "status": "alive"}, kopf)


def heartbeat(env=None):
    """Heartbeat mit beiden Auth-Wegen. Rueckgabe (status, antwort, weg)."""
    env = zugang() if env is None else env
    tok = env.get("AI4TRADE_TOKEN")
    aid = env.get("AI4TRADE_AGENT_ID") or 25973   # HermesMax2 seit 29.09.2026
    if not tok:
        return None, {"fehler": "AI4TRADE_TOKEN fehlt (weder Umgebung noch .env)"}, None
    s, a = hole(tok, int(aid))
    if s == 200:
        return s, a, "Bearer"
    s2, a2 = hole(tok, int(aid), "X-Claw-Token", tok)
    if s2 == 200:
        return s2, a2, "X-Claw-Token"
    return s, a, "Bearer"          # der erste Weg ist der aussagekraeftige


def _kennung(eintrag):
    for feld in ("id", "message_id", "task_id"):
        if eintrag.get(feld) is not None:
            return "%s:%s" % (feld, eintrag[feld])
    return json.dumps(eintrag, sort_keys=True, ensure_ascii=False)[:120]


def neu_gegen_stand(antwort, stand):
    """(neue Ereignisse, neuer Stand). Schon Gesehenes faellt raus.

    Gemerkt wird hoechstens das Ende der Liste - die Liste kommt neueste
    zuerst. Ohne Kennung (kein id-Feld) wird der Inhalt selbst verglichen.
    """
    gesehen = set(stand.get("gesehen") or [])
    neue = []
    for art in ("messages", "tasks"):
        for e in (antwort.get(art) or []):
            if not isinstance(e, dict):
                continue
            k = _kennung(e)
            if k in gesehen:
                continue
            e = dict(e)
            e["_art"] = art
            neue.append(e)
            gesehen.add(k)
    # Der Stand darf nicht unbegrenzt wachsen.
    neuer_stand = {"gesehen": sorted(gesehen)[-500:],
                   "zuletzt": datetime.now(timezone.utc).isoformat(
                       timespec="seconds")}
    return neue, neuer_stand


def _zeile(e):
    art = "Aufgabe" if e.get("_art") == "tasks" else "Nachricht"
    typ = e.get("type") or e.get("title") or ""
    text = (e.get("content") or e.get("body") or e.get("description") or "")
    text = " ".join(str(text).split())[:200]
    kopf = ("%s %s" % (art, typ)).strip()
    return "%s: %s" % (kopf, text) if text else kopf


def _lade_stand(pfad=STAND):
    if os.path.exists(pfad):
        try:
            with open(pfad, "r", encoding="utf-8") as f:
                return json.load(f)
        except ValueError:
            return {}
    return {}


def _speichere_stand(stand, pfad=STAND):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8", newline="\n") as f:
        json.dump(stand, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alles", action="store_true",
                    help="auch schon Gemeldetes zeigen")
    ap.add_argument("--pruefen", action="store_true",
                    help="nur Zugang pruefen, nichts merken")
    ap.add_argument("--env", default=ENV)
    ap.add_argument("--stand", default=STAND)
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    env = zugang(a.env)
    s, antwort, weg = heartbeat(env)
    if a.pruefen:
        print("Heartbeat: HTTP %s ueber %s" % (s, weg))
        if s == 200:
            print("agent_id %s, Empfehlung %ss, %d Nachricht(en), %d Aufgabe(n)"
                  % (antwort.get("agent_id"),
                     antwort.get("recommended_poll_interval_seconds"),
                     len(antwort.get("messages") or []),
                     len(antwort.get("tasks") or [])))
        else:
            print("Antwort: %s" % json.dumps(antwort, ensure_ascii=False)[:200])
        return 0 if s == 200 else 1

    if s != 200:
        # Ein Fehlschlag MUSS sichtbar sein - sonst haelt man Stille fuer Ruhe.
        print("ai4trade-Heartbeat fehlgeschlagen (HTTP %s ueber %s): %s"
              % (s, weg, json.dumps(antwort, ensure_ascii=False)[:200]))
        return 1

    stand = _lade_stand(a.stand) if not a.alles else {}
    neue, neuer_stand = neu_gegen_stand(antwort, stand)
    if not neue:
        if a.alles:
            print("ai4trade: nichts Neues (agent_id %s)" % antwort.get("agent_id"))
        _speichere_stand(neuer_stand, a.stand)
        return 0
    print("ai4trade: %d neue(s) Ereignis(se)" % len(neue))
    for e in neue[:MAX_MELDUNG]:
        print("  " + _zeile(e))
    if len(neue) > MAX_MELDUNG:
        print("  ... und %d weitere" % (len(neue) - MAX_MELDUNG))
    _speichere_stand(neuer_stand, a.stand)
    return 0


if __name__ == "__main__":
    sys.exit(main())