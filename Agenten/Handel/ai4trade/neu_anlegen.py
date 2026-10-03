"""Neuen ai4trade-Agenten anlegen (Auftrag Max 29.09.2026, T-116).

Warum neu statt Passwort aendern: Die Plattform hat KEINEN Endpunkt zum
Passwortwechsel (gemessen am App-Bundle: nur selfRegister, login, me, count).
Der bestehende Agent `HermesMax` (ID 25970) traegt ein Passwort, das durch eine
Fehlerantwort der API im Klartext in einem Sitzungsprotokoll steht.

Ablauf: neues Passwort erzeugen -> selfRegister -> /me gegenpruefen ->
Heartbeat probieren -> .env und Wissen/Zugaenge.md fortschreiben.
Die Werte werden NIE ausgegeben; gedruckt werden nur HTTP-Codes und die
agent_id. Bei Fehlern wird `detail` nur gezeigt, wenn es ein kurzer Text ohne
den Passwortwert ist (die API echot sonst das Feld `input` samt Passwort).
"""
from __future__ import annotations

import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request

HIER = os.path.dirname(os.path.abspath(__file__))
# Kein fester Benutzerpfad: die Wurzel liegt drei Ebenen ueber diesem Skript
# (Agenten\Handel\ai4trade), damit ein Umzug der Sammlung sie mitzieht.
BASIS = os.path.dirname(os.path.dirname(os.path.dirname(HIER)))
ENV = os.path.join(HIER, ".env")
ZUGAENGE = os.path.join(BASIS, "MaxHirn", "Wissen", "Zugaenge.md")
API = "https://ai4trade.ai/api"

NEUER_NAME = "HermesMax2"


def env_lesen(pfad):
    d = {}
    if not os.path.exists(pfad):
        return d
    with open(pfad, "r", encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#") or "=" not in zeile:
                continue
            k, v = zeile.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def ruf(pfad, nutzlast=None, token=None, methode=None):
    """Gibt (status, koerper-dict) zurueck. Wirft nicht."""
    url = API + pfad
    daten = json.dumps(nutzlast).encode("utf-8") if nutzlast is not None else None
    kopf = {"Content-Type": "application/json"}
    if token:
        kopf["Authorization"] = "Bearer %s" % token
    r = urllib.request.Request(url, data=daten, headers=kopf,
                               method=methode or ("POST" if daten else "GET"))
    try:
        with urllib.request.urlopen(r, timeout=30) as a:
            return a.status, json.loads(a.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        roh = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(roh or "{}")
        except Exception:
            return e.code, {"_roh": roh[:200]}
    except Exception as e:
        return 0, {"_fehler": type(e).__name__}


def main():
    env = env_lesen(ENV)
    basis_mail = env.get("AI4TRADE_EMAIL", "")
    if "@" not in basis_mail:
        print("ABBRUCH: keine gueltige AI4TRADE_EMAIL in der .env")
        return 2
    konto, domain = basis_mail.split("@", 1)
    konto = konto.split("+")[0]
    neue_mail = "%s+ai4trade2@%s" % (konto, domain)

    neues_pw = secrets.token_urlsafe(18)

    status, antwort = ruf("/claw/agents/selfRegister",
                          {"name": NEUER_NAME, "email": neue_mail, "password": neues_pw})
    print("selfRegister: HTTP %s" % status)
    token = antwort.get("token")
    if not token:
        d = antwort.get("detail")
        if isinstance(d, str) and neues_pw not in d:
            print("  detail:", d[:160])
        elif isinstance(d, list):
            print("  detail-Felder:", [x.get("loc") for x in d if isinstance(x, dict)])
        else:
            print("  kein Token in der Antwort")
        return 1

    st2, me = ruf("/claw/agents/me", token=token)
    agent_id = me.get("id") or me.get("agent_id") or me.get("agentId")
    print("/me: HTTP %s, agent_id %s" % (st2, agent_id))
    if st2 != 200 or not agent_id:
        print("  ABBRUCH: /me nicht bestaetigt")
        return 1

    # Heartbeat einmal echt (ohne Ausgabe des Inhalts)
    st3, _ = ruf("/claw/agents/heartbeat", {}, token=token)
    print("heartbeat: HTTP %s" % st3)

    # --- .env schreiben (Sicherung vorher) -------------------------------
    sicherung = ENV + ".bak-" + "20260929"
    if not os.path.exists(sicherung):
        with open(ENV, "rb") as f:
            alt = f.read()
        with open(sicherung, "wb") as f:
            f.write(alt)
    zeilen = [
        "# ai4trade.ai - Agent %s (angelegt 2026-09-29)" % NEUER_NAME,
        "# Der vorige Agent HermesMax (ID 25970) ist verworfen: die Plattform hat",
        "# keinen Passwortwechsel, und sein Passwort stand durch eine Fehlerantwort",
        "# der API im Klartext in einem Sitzungsprotokoll (T-116).",
        "AI4TRADE_NAME=%s" % NEUER_NAME,
        "AI4TRADE_EMAIL=%s" % neue_mail,
        "AI4TRADE_PASSWORD=%s" % neues_pw,
        "AI4TRADE_TOKEN=%s" % token,
        "AI4TRADE_AGENT_ID=%s" % agent_id,
    ]
    with open(ENV, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(zeilen) + "\n")
    print(".env geschrieben (Sicherung %s)" % os.path.basename(sicherung))

    # --- Zugaenge.md nachtragen ------------------------------------------
    with open(ZUGAENGE, "rb") as f:
        roh = f.read()
    nl = "\r\n" if b"\r\n" in roh else "\n"
    t = roh.decode("utf-8").replace("\r\n", "\n")
    abschnitt = "## ai4trade.ai"
    if abschnitt in t:
        i = t.index(abschnitt)
        j = t.find("\n## ", i + 1)
        j = len(t) if j < 0 else j
        block = """## ai4trade.ai (AI-Trader) - Papierhandel, kein Boersenzugang

Agent **%s**, agent_id **%s**, angelegt 29.09.2026.

- Adresse: https://ai4trade.ai (API-Basis https://ai4trade.ai/api)
- E-Mail: %s
- Passwort: %s
- Token (Bearer): %s
- Ablage der Kennung: `Agenten/Handel/ai4trade/.env` (in `.gitignore` gesperrt)
- Heartbeat: Hermes-Cron `ai4trade-heartbeat` (alle 5 min), Skript
  `Agenten/Handel/ai4trade/heartbeat.py` - Auth-Kopf ist `Authorization: Bearer`,
  NICHT das im Plattform-Skill genannte `X-Claw-Token` (liefert 401).
- ACHTUNG: Fehlerantworten der API echoten das Feld `input` samt Passwort.
  Nie rohe Antworten protokollieren.

Der vorige Agent `HermesMax` (ID 25970) ist am 29.09.2026 verworfen: die
Plattform hat keinen Passwortwechsel, und sein Passwort war durch so eine
Fehlerantwort sichtbar geworden. Ein Loeschen des alten Kontos ist ueber die
API nicht vorgesehen.
""" % (NEUER_NAME, agent_id, neue_mail, neues_pw, token)
        t = t[:i] + block + t[j:].lstrip("\n")
        if nl == "\r\n":
            t = t.replace("\n", "\r\n")
        with open(ZUGAENGE, "wb") as f:
            f.write(t.encode("utf-8"))
        print("Zugaenge.md: Abschnitt ersetzt")
    else:
        print("WARNUNG: Abschnitt '## ai4trade.ai' in Zugaenge.md nicht gefunden")
    return 0


if __name__ == "__main__":
    sys.exit(main())