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
import subprocess
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
NACHRICHT_VERSUCHE = 3  # Netzfehler erneut versuchen, dann verwerfen


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
    # Klartext verhindert zerschnittene HTML-Entities; Emojis zaehlen doppelt.
    teil, laenge = [], 0
    for zeichen in text:
        breite = 2 if ord(zeichen) > 0xFFFF else 1
        if laenge + breite > MAX_ZEICHEN:
            _ruf("sendMessage", {"chat_id": chat, "text": "".join(teil)})
            teil, laenge = [], 0
        teil.append(zeichen)
        laenge += breite
    if teil:
        _ruf("sendMessage", {"chat_id": chat, "text": "".join(teil)})


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
    warnung = ("Das Ergebnis des lokalen Agenten kam nicht rechtzeitig an " + "und wurde abgebrochen. Tipp: Lange Auftraege gehen besser an die Desktop-App - die Telegram-Schnittstelle bricht nach " + str(A2A_TIMEOUT_S) + " Sekunden ab und setzt nicht fort. Teile den Auftrag lieber in Teilstuecke.")
    return warnung, kontext


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


def _log(chat, kommando, dauer_s, status, zeichen, fehler=None):
    eintrag = {"zeit": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
               "chat": chat, "kommando": kommando, "dauer_s": dauer_s,
               "status": status, "zeichen": zeichen}
    if fehler:
        eintrag["fehler"] = fehler[:300]
    try:
        with open(LOG_PFAD, "a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ist_netzfehler(fehler):
    """Verbindungsfehler zum A2A-Gateway - darf erneut versucht werden.

    Nur solche Fehler werden automatisch wiederholt. Ein fachlicher Fehler
    (SkillsBotFehler) kann bedeuten, dass der Agent die Aufgabe schon
    angenommen hat - eine Wiederholung koennte sie doppelt ausfuehren.
    Netzfehler dagegen heisst: die Anfrage kam nie an (Gateway im Neustart,
    Port kurz zu). Seit 19.09.2026 prueft der Gateway-Waechter den Prozess
    am Namen UND am Port 9900; trotzdem bleibt der SkillsBot gegen kurze
    Aussetzer gewappnet.
    """
    return isinstance(fehler, (urllib.error.URLError, ConnectionError,
                               TimeoutError, OSError))


class Sperre:
    """OS-Dateisperre; bei Prozessende automatisch frei, ohne PID-Signale."""

    def __enter__(self):
        self.datei = open(PID_PFAD, "a+b")
        try:
            if os.fstat(self.datei.fileno()).st_size == 0:
                self.datei.write(b"0")
                self.datei.flush()
            self.datei.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.datei.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.datei.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as e:
            self.datei.close()
            raise SkillsBotFehler("SkillsBot-Sperre belegt oder nicht zugreifbar.") from e
        # Die Datei bleibt bestehen: Loeschen wuerde einen zweiten Lock erlauben.
        return self

    def __exit__(self, *a):
        self.datei.close()


# --- Befehle ----------------------------------------------------------------

def _handelsantwort(wort):
    """Eine lesende Handelsauskunft holen - Text aus `Handel/befehle.py`.

    Keine zweite Fassung hier: /lage im SkillsBot ist derselbe Text wie /lage
    im Handelsbot (eine Quelle, zwei Bots). Der Handelsbot sendet HTML, der
    SkillsBot nicht - deshalb laeuft das Ergebnis durch `handel_befehle.
    klartext()`.
    """
    import handel_befehle                                     # noqa: PLC0415
    if wort == "/lage":
        return handel_befehle.lage()
    if wort == "/bericht":
        return handel_befehle.bericht()
    if wort == "/spuren":
        namen = handel_befehle.spuren()
        return ("Spuren: %s" % ", ".join(namen)) if namen \
            else "Spurliste nicht lesbar (SPUREN in dauerlauf.py)."
    if wort == "/strategien":
        return handel_befehle.strategien()
    if wort == "/indikatoren":
        return handel_befehle.indikatoren()
    if wort == "/markt":
        return handel_befehle.markt()
    raise SkillsBotFehler("kein Handelsbefehl: %s" % wort)


def _bot_profil_ordner():
    """Agenten/Hermes/profiles/ - die Wahrheit fuer Bot-Namen (kein Raten)."""
    return os.path.join(WURZEL, "Agenten", "Hermes", "profiles")


def bot_namen():
    """Namen aller Hermes-Profile (Unterordner mit config.yaml)."""
    wurzel = _bot_profil_ordner()
    ergebnis = []
    try:
        for name in os.listdir(wurzel):
            if os.path.isfile(os.path.join(wurzel, name, "config.yaml")):
                ergebnis.append(name)
    except OSError:
        return []
    return sorted(ergebnis)


def _bot_beschreibung(name):
    """`description:` aus profile.yaml - die Rolle, nicht der Name."""
    try:
        with open(os.path.join(_bot_profil_ordner(), name,
                               "profile.yaml"), "r",
                  encoding="utf-8") as f:
            for zeile in f:
                if zeile.startswith("description:"):
                    return zeile.split(":", 1)[1].strip()[:120]
    except OSError:
        return ""
    return ""


def _hermes_umgebung():
    """Saubere Umgebung fuer hermes.exe: PYTHONHOME/PYTHONPATH raus.

    Aus einer Session, die durch den MCP-Supervisor laeuft, startet hermes.exe
    sonst mit 'Fatal Python error: init_import_site' (das venv ist gesund,
    die Umgebung ist es nicht). HERMES_HOME zeigen lassen, wo die Profile
    liegen, damit der Aufruf nicht vom cwd des SkillsBot abhaengt.
    """
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env["HERMES_HOME"] = os.path.join(WURZEL, "Agenten", "Hermes")
    return env


def _bot_fragen(name, text, zeit=A2A_TIMEOUT_S + 30):
    """Eine Frage an das Profil <name> - der Bot antwortet selbst.

    Der Weg ist ein frischer Einzelauftrag (chat -q): keine Sitzung, kein
    Kontext, kein Gateway. Was der Bot kann, kann er hier; der SkillsBot
    fuehrt nichts aus, er stellt nur die Verbindung her.
    """
    exe = os.path.join(WURZEL, "Agenten", "Hermes", "bin", "hermes.exe")
    if not os.path.isfile(exe):
        raise SkillsBotFehler("hermes.exe nicht gefunden: %s" % exe)
    try:
        lauf = subprocess.run(
            [exe, "-p", name, "chat", "-q", text, "-Q"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=zeit, env=_hermes_umgebung())
    except subprocess.TimeoutExpired:
        raise SkillsBotFehler(
            "Bot %s hat nicht innerhalb von %s s geantwortet."
            % (name, A2A_TIMEOUT_S))
    except OSError as e:
        raise SkillsBotFehler("Bot %s nicht startbar: %s" % (name, e))
    if lauf.returncode != 0:
        stderr = (lauf.stderr or "").strip().splitlines()
        grund = stderr[-1][:200] if stderr else "Exit-Code %s" % lauf.returncode
        raise SkillsBotFehler("Bot %s ist gescheitert: %s" % (name, grund))
    antwort = (lauf.stdout or "").strip()
    # hermes -q druckt die reine Antwort; eine session_id-Zeile ist Status.
    zeilen = [z for z in antwort.splitlines()
              if not z.startswith("session_id:")]
    return "\n".join(zeilen).strip() or "(leere Antwort)"


def _bot_befehl(rest, chat):
    """/bot NAME NACHRICHT - eine Frage an das genannte Profil.

    Rueckgabe wie `bearbeite`: (Text, neuer A2A-Kontext). Der A2A-Kontext
    bleibt unveraendert - der Bot spricht mit seinem eigenen Verlauf.
    """
    if not rest:
        return ("Syntax: /bot NAME NACHRICHT\n"
                "Beispiel: /bot openterminal Was ist in der README?\n"
                "Die Namen stehen in /bots."), None
    name = rest[0].lstrip("/")
    texte = " ".join(rest[1:]).strip()
    if name not in bot_namen():
        return ("Kein Profil %r. /bots zeigt die Namen." % name), None
    if not texte:
        return ("Was soll ich Bot %s fragen? Syntax: /bot %s NACHRICHT"
                % (name, name)), None
    # Erst sagen, dann tun: ein frischer Agent braucht 30-60 s Kaltstart.
    sende(chat, "Spreche mit Bot %s - das kann bis 5 min dauern." % name)
    try:
        antwort = _bot_fragen(name, texte)
    except Exception as fehler:                           # noqa: BLE001
        return ("Bot %s gescheitert: %s" % (name, str(fehler)[:150])), None
    return ohne_denken(antwort), None


def _bot_liste():
    """/bots - alle Profile mit Rolle (Name + description)."""
    namen = bot_namen()
    if not namen:
        return "Keine Profile gefunden (%s)." % _bot_profil_ordner()
    zeilen = []
    for n in namen:
        beschreibung = _bot_beschreibung(n)
        zeilen.append(n + ((" - " + beschreibung) if beschreibung else ""))
    return "Bots (%d):\n%s" % (len(namen), "\n".join(zeilen))


def hilfe_text():
    # Kein HTML: der SkillsBot sendet ohne parse_mode - Marken staenden
    # woertlich in der Nachricht (der Handelsbot nutzt dafuer befehle.hilfe()).
    return ("Ich reiche deine Nachrichten per A2A an den lokalen Hermes-"
            "Agenten (hermes-maks-pc) weiter - der hat alle Skills.\n"
            "\nHandel (lesend, aus dem Handel-Ordner)\n"
            "/lage - offene Positionen je Spur, Live-Tore, Freigaben\n"
            "/bericht - voller Tagesbericht (dauert, mit Rangliste)\n"
            "/spuren - alle Spur-Namen\n"
            "/spur NAME - eine Spur in der Tiefe\n"
            "/strategien - Bilanz aller Strategien nebeneinander\n"
            "/indikatoren - die vier Indikator-Spuren: Signale und Treffer\n"
            "/markt - Kurs, 24 h, Trend, Volatilitaet\n"
            "/status - gespeicherter Dateistand (alle Spuren)\n"
            "/papierstatus - nur Papierspuren\n"
            "/prognose [N] - Marktbeobachtung long/short (bis 240 s)\n"
            "/skills [SUCHE] - die gelernten Skills, nach Gruppen\n"
            "/skill NAME - ein Skill im Volltext\n"
            "/run NAME [Auftrag] - einen Skill AUSFUEHREN (bis 5 min)\n"
            "/bots - alle Hermes-Profile (Repo-Bots)\n"
            "/bot NAME NACHRICHT - Frage an einen Repo-Bot (bis 5 min)\n"
            "/hilfe - diese Liste\n"
            "\nFreigaben nur im Handelsbot: /freigabe_xperp, /ja_xperp STUNDEN, "
            "/nein_xperp, /stop_xperp.\n"
            "SWAP-Live bleibt gesperrt. Freitext geht weiterhin an Hermes.")


DENKEN = "\U0001f4ad **Reasoning:**"


def ohne_denken(text):
    """Den Reasoning-Block des Agenten entfernen - Arbeitsnotiz, keine Antwort.

    Der A2A-Agent stellt seiner Antwort seinen Denkblock voran (in ``` gefasst).
    Auf dem Handy ist das der halbe Text, und es liest sich wie das Ergebnis.
    Entfernt wird nur der Block; fehlt er, bleibt der Text unveraendert - ein
    anderer Aufbau darf keine Antwort kosten.
    """
    if not text or DENKEN not in text:
        return text
    kopf, _, rest = text.partition(DENKEN)
    auf = rest.find("```")
    if auf < 0:
        return kopf.strip() or text
    zu = rest.find("```", auf + 3)
    if zu < 0:
        return kopf.strip() or text
    return (kopf + rest[zu + 3:]).strip() or text


def _run(rest, chat, kontext):
    """Einen Skill AUSFUEHREN statt ihn nur zu zeigen.

    Der Weg ist derselbe wie bei Freitext (A2A an hermes-maks-pc) - nur mit
    einer Anweisung davor, damit der Agent den Skill zieht und nicht frei
    antwortet. Ausgefuehrt wird ausschliesslich, was im Katalog steht UND
    ladbar ist; ein Teiltreffer muss eindeutig sein. Sonst raet der Bot einen
    Skill - und der Nutzer erfaehrt nie, dass ein anderer lief.

    Rueckgabe wie `bearbeite`: (Text, neuer A2A-Kontext).
    """
    if not rest:
        return ("Syntax: /run NAME [Auftrag]\n"
                "Beispiel: /run systemdiagnose\n"
                "Die Namen stehen in /skills (Teiltreffer sind erlaubt, wenn "
                "eindeutig)."), kontext
    name = rest[0].lstrip("/")
    auftrag = " ".join(rest[1:]).strip()
    try:
        import skillkatalog
        e = skillkatalog.finde(name)
    except Exception as fehler:                               # noqa: BLE001
        return "Skill-Katalog nicht lesbar: %s" % str(fehler)[:120], kontext
    if e is None:
        return ("Kein eindeutiger Skill %r. /skills [SUCHE] zeigt die Liste - "
                "Teiltreffer sind erlaubt, muessen aber eindeutig sein."
                % name), kontext
    if not e.get("ladbar", True):
        return ("Skill %s gehoert einem anderen System (%s) - hier nicht "
                "ausfuehrbar." % (e["name"], e.get("gruppe"))), kontext

    # Erst sagen, dann tun: eine Skill-Ausfuehrung dauert (Systemcheck ~1 min,
    # Marktanalyse bis 4 min). Ohne diese Zeile sieht es aus, als haenge der Bot.
    sende(chat, "Fuehre den Skill %s aus - das kann bis 5 min dauern."
         % e["name"])
    text = ("Fuehre den Skill '%s' aus.%s\n\n"
            "Antworte knapp in dieser Reihenfolge: was getan wurde, was jetzt "
            "nachweisbar funktioniert, was noch eine Entscheidung braucht. "
            "Wenn der Skill ohne weitere Angaben nicht ausfuehrbar ist, sage "
            "genau, was fehlt - statt zu raten."
            % (e["name"], (" Auftrag dazu: " + auftrag) if auftrag else ""))
    try:
        antwort, neuer_kontext = frage(text, kontext)
    except Exception as fehler:                               # noqa: BLE001
        return ("Skill %s gescheitert: %s"
                % (e["name"], str(fehler)[:150])), kontext
    return (ohne_denken(antwort) or "Keine Antwort vom Agenten."), neuer_kontext


def bearbeite(text, chat):
    """Antwort auf eine Nachricht; (text, neuer_kontext) oder None."""
    kontexte = _lade_json(KONTEXT_PFAD, {})
    kontext = kontexte.get(str(chat))
    t = text.strip()
    teile = t.split()
    wort = teile[0].lower() if teile else ""
    if wort == "/run" or wort == "/mach":
        # Ein Skill wird AUSGEFUEHRT, nicht angezeigt (Auftrag Max, 16.09.2026).
        # Der A2A-Kontext laeuft wie bei Freitext weiter und wird hier
        # gespeichert - /run und Freitext teilen denselben Verlauf.
        antwort, neuer_kontext = _run(teile[1:], chat, kontext)
        if neuer_kontext:
            kontexte[str(chat)] = neuer_kontext
            _speichere_json(KONTEXT_PFAD, kontexte)
        return antwort, neuer_kontext
    if wort == "/bots":
        # Alle Hermes-Profile: eine Liste, kein A2A-Aufruf. Der Bot-Name ist
        # danach das Argument von /bot - die Wahrheit liegt auf der Platte,
        # nicht in einer gepflegten Liste (die wuerde altern).
        return _bot_liste(), kontext
    if wort == "/bot":
        # Eine Frage an EIN Profil: der SkillsBot ist nur die Bruecke, der
        # andere Agent antwortet mit seinem eigenen Verlauf. Der A2A-Kontext
        # von hermes-maks-pc bleibt deshalb unveraendert.
        antwort, _ = _bot_befehl(teile[1:], chat)
        return antwort, kontext
    if wort == "/prognose":
        import handel_befehle
        return handel_befehle.prognose(t), kontext
    if t in ("/status", "/papierstatus"):
        import handel_befehle
        return handel_befehle.status(papier=t == "/papierstatus"), kontext
    if wort == "/spur":
        import handel_befehle
        try:
            return handel_befehle.klartext(
                handel_befehle.spur(" ".join(teile[1:]))), kontext
        except Exception as e:                                # noqa: BLE001
            return "Spur nicht lesbar: %s" % str(e)[:120], kontext
    if wort in ("/lage", "/bericht", "/spuren", "/strategien",
                "/indikatoren", "/markt"):
        try:
            import handel_befehle
            return handel_befehle.klartext(_handelsantwort(wort)), kontext
        except Exception as e:                                # noqa: BLE001
            return ("Auskunft nicht lesbar: %s\nIm Handelsbot geht %s weiter."
                    % (str(e)[:120], wort)), kontext
    if t in ("/hilfe", "/start"):
        return hilfe_text(), kontext
    if wort == "/skills":
        # Der Katalog liest die SKILL.md-Dateien. Die frueher benutzte
        # Agent-Card zaehlt WERKZEUGSAETZE auf (42 Zeilen "toolset.x"),
        # nicht die gelernten Skills - daher wirkte /skills wie eine
        # Zufallsliste. Mit Suchbegriff filtert der Katalog.
        try:
            import skillkatalog
            return skillkatalog.katalog(t[7:].strip() or None), kontext
        except Exception as e:  # noqa: BLE001
            return "Skill-Katalog nicht lesbar: %s" % str(e)[:120], kontext
    if wort == "/skill":
        try:
            import skillkatalog
            return skillkatalog.volltext(t[6:].strip()), kontext
        except Exception as e:  # noqa: BLE001
            return "Skill nicht lesbar: %s" % str(e)[:120], kontext
    if t.startswith("/"):
        return ("Kein SkillsBot-Befehl. /hilfe zeigt die Liste.\n"
                "Freigaben nur im Handelsbot: /freigabe_xperp, /ja_xperp STUNDEN, "
                "/nein_xperp, /stop_xperp.\n"
                "SWAP-Live ist nicht angebunden. Kein Auftrag an den Agenten gesendet."), kontext
    antwort, neuer_kontext = frage(t, kontext)
    if neuer_kontext:
        kontexte[str(chat)] = neuer_kontext
        _speichere_json(KONTEXT_PFAD, kontexte)
    return ohne_denken(antwort), neuer_kontext


# --- Schleife ---------------------------------------------------------------

def schleife():
    if (_variable("SKILLSBOT_TOKEN") and
            _variable("SKILLSBOT_TOKEN") == _variable("TELEGRAM_TOKEN")):
        raise SkillsBotFehler("SkillsBot und Handelsbot duerfen nicht denselben Token nutzen.")
    if not eigener_bot_gesetzt():
        raise SkillsBotFehler(
            "Dauerbetrieb verweigert: SKILLSBOT_TOKEN nicht gesetzt. "
            "Der geteilte TELEGRAM_TOKEN gehoert dauerlauf.py/melder.py; "
            "zwei Poller an einem Bot verschlucken Order-Freigaben. "
            "Eigenen Bot anlegen (BotFather, /newbot) und setzen: "
            "setx SKILLSBOT_TOKEN <token>")
    offset = _lade_json(OFFSET_PFAD, 0) or 0
    fehler_reihe = 0
    versuche = {}          # update_id -> bisherige Netzfehler-Versuche
    while True:
        try:
            nachrichten = _nachrichten(offset)
            fehler_reihe = 0
            netzfehler = False
            for n in nachrichten:
                uid = n["update_id"]
                chat = (n.get("message") or {}).get("chat", {}).get("id")
                text = (n.get("message") or {}).get("text")
                if chat is None or text is None:
                    continue
                if chat != chat_id():
                    _log(chat, "(fremd)", 0, "abgewiesen", len(text))
                    offset = uid + 1
                    continue
                start = time.time()
                try:
                    antwort, _ = bearbeite(text, chat)
                    sende(chat, antwort)
                    _log(chat, text[:40], round(time.time() - start, 1),
                         "ok", len(antwort))
                    versuche.pop(uid, None)
                    offset = uid + 1
                except Exception as e:  # noqa: BLE001
                    grund = str(e)[:200]
                    if (_ist_netzfehler(e)
                            and versuche.get(uid, 0) < NACHRICHT_VERSUCHE - 1):
                        # Gateway kurz weg (Neustart/Port zu): Nachricht NICHT
                        # verwerfen. Der Offset bleibt stehen, die fehlgeschlagene
                        # Nachricht kommt beim naechsten Poll erneut. Eine Pause
                        # gibt dem Gateway Zeit, hochzukommen.
                        versuche[uid] = versuche.get(uid, 0) + 1
                        _log(chat, text[:40], round(time.time() - start, 1),
                             "fehler", 0,
                             fehler="%s (Netzversuch %d/%d)"
                             % (grund, versuche[uid] + 1, NACHRICHT_VERSUCHE))
                        netzfehler = True
                        break
                    fehlertext = "Fehler: %s" % e
                    try:
                        sende(chat, fehlertext)
                    except Exception:  # noqa: BLE001
                        pass
                    _log(chat, text[:40], round(time.time() - start, 1),
                         "fehler", 0, fehler=grund)
                    versuche.pop(uid, None)
                    offset = uid + 1
            if netzfehler:
                time.sleep(20)
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
        return 2
    if token():
        try:
            info = _ruf("getMe")
            quelle = "SKILLSBOT_TOKEN" if eigener_bot_gesetzt() else "TELEGRAM_TOKEN (geteilt!)"
            print("Telegram-Bot: @%s (%s)" % (info.get("username", "?"), quelle))
        except Exception as e:  # noqa: BLE001
            print("Telegram nicht erreichbar: %s" % e)
            return 2
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

