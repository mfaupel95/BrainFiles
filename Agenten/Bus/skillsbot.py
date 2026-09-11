"""SkillsBot: Telegram <-> A2A-Bruecke zu hermes-maks-pc (Port 9900).

Was der Bot tut
---------------
Er nimmt Nachrichten von Max per Telegram entgegen, schickt sie als
A2A-SendMessage an den lokalen Hermes-Agenten (der alle Skills hat) und
antwortet mit dessen Antwort. Damit hat Max von jedem Ort A2A-Zugriff
auf die Skills (archiv, notiz, geld, ...), ohne die Desktop-App zu brauchen.

Angelegt am 11.09.2026. Vorbild: Agenten/Handel/melder.py (Telegram-Zugang
ueber Benutzervariablen, Freigabeliste, nur Standardbibliothek).

EINRICHTEN (einmalig, von Max)
------------------------------
  1. In Telegram @BotFather anschreiben, /newbot, Namen vergeben.
     BotFather antwortet mit einem Token der Form 123456:ABC-DEF...
  2. Den NEUEN Bot anschreiben (irgendetwas, z.B. "hallo").
  3. Als Benutzervariable setzen (HKCU, wie melder.py). WICHTIG:
     TELEGRAM_TOKEN NICHT ueberschreiben - das ist der Freigaben-Bot von
     melder.py/dauerlauf.py, der laufend pollt. Der SkillsBot braucht
     einen EIGENEN Bot:

       setx SKILLSBOT_TOKEN "123456:ABC-DEF..."
       python skillsbot.py --chat-id-suchen
       setx TELEGRAM_CHAT_ID "123456789"   (gleiche ID wie beim melder)

  4. Probe:

       python skillsbot.py --probe

  Neues Terminal noetig, damit setx sichtbar wird.

A2A-Zugangsdaten kommen aus Agenten/Hermes/.env (A2A_PEER_TOKENS), der
Wahrheit fuer den lokalen A2A-Server. Der Bot druckt niemals ein Token.

SICHERHEIT
----------
TELEGRAM_CHAT_ID ist die Zugangssperre, wie im melder: Nachrichten von
anderen Chat-IDs werden verworfen und gezaehlt, nicht beantwortet. Der Bot
hat keine eigenen Rechte: Alles was er kann, kann der A2A-Agent, an den er
weiterreicht - und der ist derselbe, der auch die Telegram-Gateway-Bot-
Nachrichten beantwortet (Wissen/Hermes.md). Keine Orderausloesung, keine
Freigaben: Das bleibt bei melder.py/freigabe.py.

Dauerbetrieb NUR mit eigenem Bot (SKILLSBOT_TOKEN): Wer den geteilten
TELEGRAM_TOKEN nutzt, konkurriert mit dauerlauf.py um getUpdates und kann
eine Order-Freigabe verschlucken. Deshalb verweigert die Schleife den Start
ohne SKILLSBOT_TOKEN; nur --probe/--chat-id-suchen duerfen den geteilten
Bot lesen.

Betrieb: python skillsbot.py (laenger laufen lassen; als geplanter Task
ueber Agenten/Routinen/skillsbot.ps1 registrierbar).
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --- Pfade -----------------------------------------------------------------

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, os.pardir, os.pardir))
ENV_HERMES = os.path.join(WURZEL, "Agenten", "Hermes", ".env")
LOG_PFAD = os.path.join(HIER, "skillsbot.log")
OFFSET_PFAD = os.path.join(HIER, "skillsbot.offset")
KONTEXT_PFAD = os.path.join(HIER, "skillsbot.kontext.json")
PID_PFAD = os.path.join(HIER, "skillsbot.pid")

A2A_URL = "http://127.0.0.1:9900/"
KARTE_URL = "http://127.0.0.1:9900/.well-known/agent-card.json"

TELEGRAM = "https://api.telegram.org/bot%s/%s"
MAX_ZEICHEN = 4000      # Telegram bricht bei 4096 hart ab
MAX_FEHLER = 4          # Telegram-Gegenstellenfehler hintereinander -> Pause
POLL_DAUER = 25         # getUpdates long polling
A2A_POLL_S = 3          # GetTask-Intervall
A2A_TIMEOUT_S = 300     # so lange auf eine Antwort warten


class SkillsBotFehler(RuntimeError):
    """Fachlicher Fehler aus einer gueltigen Telegram-Antwort (ok=false)."""


# --- Schluessel -------------------------------------------------------------

def _aus_registry(name):
    try:
        import winreg
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _variable(name):
    return os.environ.get(name) or _aus_registry(name)


def token():
    """Eigener SKILLSBOT_TOKEN; TELEGRAM_TOKEN nur als Test-Fallback."""
    return _variable("SKILLSBOT_TOKEN") or _variable("TELEGRAM_TOKEN")


def eigener_bot_gesetzt():
    return bool(_variable("SKILLSBOT_TOKEN"))


def chat_id():
    v = _variable("TELEGRAM_CHAT_ID")
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _a2a_token():
    """Erstes name:token-Paar aus A2A_PEER_TOKENS der Hermes-.env."""
    try:
        with open(ENV_HERMES, "r", encoding="utf-8") as f:
            for zeile in f:
                zeile = zeile.strip()
                if zeile.startswith("A2A_PEER_TOKENS=") and "=" in zeile:
                    wert = zeile.split("=", 1)[1].strip()
                    erster = wert.split(",")[0]
                    if ":" in erster:
                        return erster.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


def bereit():
    """Was brauchen wir? (Namen, nie Werte.)"""
    fehlt = []
    if not token():
        fehlt.append("TELEGRAM_TOKEN/SKILLSBOT_TOKEN")
    if not chat_id():
        fehlt.append("TELEGRAM_CHAT_ID")
    if not _a2a_token():
        fehlt.append("A2A_PEER_TOKENS in " + ENV_HERMES)
    return fehlt


# --- Telegram-Verkehr --------------------------------------------------------

def _ruf(methode, daten=None, zeit=30):
    t = token()
    if not t:
        raise SkillsBotFehler("Token nicht gesetzt (SKILLSBOT_TOKEN)")
    url = TELEGRAM % (t, methode)
    leib = json.dumps(daten or {}).encode("utf-8")
    req = urllib.request.Request(url, data=leib, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=zeit) as ant:
        erg = json.loads(ant.read().decode("utf-8"))
    if not erg.get("ok"):
        raise SkillsBotFehler(erg.get("description") or "unbekannter Fehler")
    return erg.get("result")


def sende(chat, text):
    import html
    text = html.escape(text)
    for i in range(0, len(text), MAX_ZEICHEN):
        _ruf("sendMessage", {"chat_id": chat, "text": text[i:i + MAX_ZEICHEN],
                             "parse_mode": "HTML"})


def _nachrichten(offset):
    daten = {"timeout": POLL_DAUER, "offset": offset,
             "allowed_updates": ["message"]}
    return _ruf("getUpdates", daten, zeit=POLL_DAUER + 10)


# --- A2A-Verkehr -------------------------------------------------------------

def _a2a_ruf(methode, params, zeit=A2A_TIMEOUT_S + 30):
    tok = _a2a_token()
    if not tok:
        raise SkillsBotFehler("A2A-Peer-Token fehlt (" + ENV_HERMES + ")")
    leib = json.dumps({"jsonrpc": "2.0", "id": 1, "method": methode,
                       "params": params}).encode("utf-8")
    req = urllib.request.Request(A2A_URL, data=leib, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=zeit) as ant:
        erg = json.loads(ant.read().decode("utf-8"))
    if "error" in erg:
        raise SkillsBotFehler(str(erg["error"]))
    return erg.get("result", {})


def _aufgabe_abholen(aufgabe):
    """Task bis TASK_STATE_COMPLETED verfolgen, Antworttext zurueckgeben."""
    tid = aufgabe.get("id")
    kontext = aufgabe.get("contextId")
    for _ in range(A2A_TIMEOUT_S // A2A_POLL_S):
        zustand = aufgabe.get("status", {}).get("state", "")
        if zustand == "TASK_STATE_COMPLETED":
            teile = aufgabe.get("status", {}).get("message", {}).get("parts", [])
            texte = [p.get("text", "") for p in teile if p.get("text")]
            if not texte:
                for art in aufgabe.get("artifacts", []):
                    texte += [p.get("text", "") for p in art.get("parts", [])
                              if p.get("text")]
            return ("\n\n".join(texte) if texte else "(leere Antwort)"), kontext
        if zustand in ("TASK_STATE_FAILED", "TASK_STATE_REJECTED",
                       "TASK_STATE_CANCELED"):
            return ("(Aufgabe " + zustand.replace("TASK_STATE_", "") + ")"), kontext
        time.sleep(A2A_POLL_S)
        aufgabe = _a2a_ruf("GetTask", {"id": tid}).get("task", {})
    return "(Zeitueberschreitung nach " + str(A2A_TIMEOUT_S) + " s)", kontext


def frage(text, kontext_id=None):
    """SendMessage an den A2A-Agenten; (Antwort, contextId) zurueck."""
    msg = {"messageId": "tg-" + str(int(time.time() * 1000)),
           "role": "ROLE_USER", "parts": [{"text": text}]}
    params = {"message": msg}
    if kontext_id:
        params["contextId"] = kontext_id
    aufgabe = _a2a_ruf("SendMessage", params).get("task", {})
    return _aufgabe_abholen(aufgabe)


def karten_skills():
    """Namen der Skills von der Agent-Card holen (fuer /skills)."""
    with urllib.request.urlopen(KARTE_URL, timeout=10) as ant:
        karte = json.loads(ant.read().decode("utf-8"))
    return [s.get("name") for s in karte.get("skills", []) if s.get("name")]


# --- Zustand ----------------------------------------------------------------

def _lade_json(pfad, sonst):
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return sonst


def _speichere_json(pfad, wert):
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(wert, f, ensure_ascii=False)
    os.replace(tmp, pfad)


def _log(chat, kommando, dauer_s, status, zeichen):
    eintrag = {"zeit": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "chat": chat, "kommando": kommando, "dauer_s": dauer_s,
               "status": status, "zeichen": zeichen}
    try:
        with open(LOG_PFAD, "a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    except OSError:
        pass


class Sperre:
    """Einfache PID-Sperre gegen zwei gleichzeitige Bot-Prozesse."""

    def __enter__(self):
        if os.path.exists(PID_PFAD):
            try:
                with open(PID_PFAD, "r") as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)
                raise SkillsBotFehler(
                    "Laueft bereits (PID " + str(pid) + "). skillsbot.pid "
                    "loeschen, falls sicher gestoppt.")
            except (OSError, ValueError):
                pass  # verwaiste PID-Datei
        with open(PID_PFAD, "w") as f:
            f.write(str(os.getpid()))
        return self

    def __exit__(self, *a):
        try:
            os.remove(PID_PFAD)
        except OSError:
            pass


# --- Befehle ----------------------------------------------------------------

def bearbeite(text, chat):
    """Antwort auf eine Nachricht; (text, neuer_kontext) oder None."""
    kontexte = _lade_json(KONTEXT_PFAD, {})
    kontext = kontexte.get(str(chat))
    t = text.strip()
    if t.split() and t.split()[0] == "/prognose":
        import handel_befehle
        return handel_befehle.prognose(t), kontext
    if t in ("/status", "/papierstatus"):
        import handel_befehle
        return handel_befehle.status(papier=t == "/papierstatus"), kontext
    if t in ("/hilfe", "/start"):
        return ("Ich reiche deine Nachrichten per A2A an den lokalen Hermes-"
                "Agenten (hermes-maks-pc) weiter - der hat alle Skills."
                "\n\n/status - lokaler Zustand, xperp zuerst\n/papierstatus - nur Papierstand"
                "\n/prognose [N] - Marktanalyse ohne Order (bis 240 s)"
                "\n/skills - Skills\n/hilfe - Hilfe"
                "\nFreigaben im Handelsbot: /freigabe_xperp, /ja_xperp STUNDEN, /nein_xperp, /stop_xperp."
                "\nSWAP-Live bleibt gesperrt. Freitext geht weiterhin an Hermes."), kontext
    if t == "/skills":
        try:
            namen = karten_skills()
            return "Skills (%d):\n%s" % (len(namen), ", ".join(namen)), kontext
        except Exception as e:  # noqa: BLE001
            return "Skills-Abruf fehlgeschlagen: %s" % e, kontext
    if t.startswith("/"):
        return ("Kein SkillsBot-Befehl. /status /papierstatus /prognose [N] /skills /hilfe.\n"
                "Freigaben nur im Handelsbot: /freigabe_xperp, /ja_xperp STUNDEN, /nein_xperp, /stop_xperp.\n"
                "SWAP-Live ist nicht angebunden. Kein Auftrag an den Agenten gesendet."), kontext
    antwort, neuer_kontext = frage(t, kontext)
    if neuer_kontext:
        kontexte[str(chat)] = neuer_kontext
        _speichere_json(KONTEXT_PFAD, kontexte)
    return antwort, neuer_kontext


# --- Schleife ---------------------------------------------------------------

def schleife():
    if not eigener_bot_gesetzt():
        raise SkillsBotFehler(
            "Dauerbetrieb verweigert: SKILLSBOT_TOKEN nicht gesetzt. "
            "Der geteilte TELEGRAM_TOKEN gehoert dauerlauf.py/melder.py; "
            "zwei Poller an einem Bot verschlucken Order-Freigaben. "
            "Eigenen Bot anlegen (BotFather, /newbot) und setzen: "
            "setx SKILLSBOT_TOKEN <token>")
    offset = _lade_json(OFFSET_PFAD, 0) or 0
    fehler_reihe = 0
    while True:
        try:
            nachrichten = _nachrichten(offset)
            fehler_reihe = 0
            for n in nachrichten:
                offset = n["update_id"] + 1
                chat = (n.get("message") or {}).get("chat", {}).get("id")
                text = (n.get("message") or {}).get("text")
                if chat is None or text is None:
                    continue
                if chat != chat_id():
                    _log(chat, "(fremd)", 0, "abgewiesen", len(text))
                    continue
                start = time.time()
                try:
                    antwort, _ = bearbeite(text, chat)
                    sende(chat, antwort)
                    _log(chat, text[:40], round(time.time() - start, 1),
                         "ok", len(antwort))
                except Exception as e:  # noqa: BLE001
                    fehler = "Fehler: %s" % e
                    try:
                        sende(chat, fehler)
                    except Exception:  # noqa: BLE001
                        pass
                    _log(chat, text[:40], round(time.time() - start, 1),
                         "fehler", 0)
            _speichere_json(OFFSET_PFAD, offset)
        except SkillsBotFehler as e:
            fehler_reihe += 1
            if fehler_reihe >= MAX_FEHLER:
                time.sleep(30)
                fehler_reihe = 0
            else:
                time.sleep(3)
        except Exception:  # noqa: BLE001 - Netzwerk usw.: weiter, nie sterben
            time.sleep(5)


# --- Aufrufe ----------------------------------------------------------------

def chat_id_suchen():
    antwort = _ruf("getUpdates", {"timeout": 20}, zeit=35)
    for n in antwort:
        chat = (n.get("message") or {}).get("chat", {})
        if chat:
            print("Chat-ID: %s (%s)" % (chat.get("id"), chat.get("type")))
    if not antwort:
        print("Keine Nachricht gefunden - schreib dem Bot zuerst irgendetwas.")


def probe():
    fehlt = bereit()
    if fehlt:
        print("Es fehlt: %s" % ", ".join(fehlt))
    if token():
        try:
            info = _ruf("getMe")
            quelle = "SKILLSBOT_TOKEN" if eigener_bot_gesetzt() else "TELEGRAM_TOKEN (geteilt!)"
            print("Telegram-Bot: @%s (%s)" % (info.get("username", "?"), quelle))
        except Exception as e:  # noqa: BLE001
            print("Telegram nicht erreichbar: %s" % e)
    if chat_id():
        print("Freigabeliste: Chat-ID %s" % chat_id())
    try:
        namen = karten_skills()
        print("A2A-Agent erreichbar, %d Skills (z.B. %s)"
              % (len(namen), ", ".join(namen[:5])))
    except Exception as e:  # noqa: BLE001
        print("A2A-Karte nicht erreichbar: %s" % e)
        return 2
    try:
        antwort, _ = frage("Antworte nur mit: PONG")
        print("A2A-Ping: %s" % antwort[:60])
        return 0 if antwort and not antwort.startswith("(") else 1
    except Exception as e:  # noqa: BLE001
        print("A2A-Ping fehlgeschlagen: %s" % e)
        return 2


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="SkillsBot Telegram<->A2A")
    parser.add_argument("--chat-id-suchen", action="store_true")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.chat_id_suchen:
        chat_id_suchen()
    elif args.probe:
        sys.exit(probe())
    else:
        try:
            with Sperre():
                print("SkillsBot laeuft (Chat-ID %s)" % chat_id(),
                      flush=True)
                schleife()
        except SkillsBotFehler as e:
            print(str(e))
            sys.exit(1)
