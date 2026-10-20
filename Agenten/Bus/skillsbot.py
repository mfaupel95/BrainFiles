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
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# --- Pfade -----------------------------------------------------------------

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.abspath(os.path.join(HIER, os.pardir, os.pardir))
ENV_HERMES = os.path.join(WURZEL, "Agenten", "Hermes", ".env")
CONFIG_HERMES = os.path.join(WURZEL, "Agenten", "Hermes", "config.yaml")
LOG_PFAD = os.path.join(HIER, "skillsbot.log")
OFFSET_PFAD = os.path.join(HIER, "skillsbot.offset")
# Welcher Bot gerade "aktiv" ist (Auftrag Max 03.10.2026: /bot NAME
# ohne Auftrag war nur eine Syntaxhilfe, danach ging der Auftrag an den
# HAUPTAGENT - der Bot bekam ihn nie). ZIEL_PFAD ist ein Laufzeitstand
# wie der Offset, kein versionierter Zustand.
ZIEL_PFAD = os.path.join(HIER, "skillsbot.ziel.json")
ZIEL_FRIST_S = 1800      # ein Bot bleibt 30 min "aktiv"; danach gehoert
                         # der naechste Freitext wieder dem Hauptagenten
KONTEXT_PFAD = os.path.join(HIER, "skillsbot.kontext.json")
PID_PFAD = os.path.join(HIER, "skillsbot.pid")

A2A_URL = "http://127.0.0.1:9900/"
KARTE_URL = "http://127.0.0.1:9900/.well-known/agent-card.json"

TELEGRAM = "https://api.telegram.org/bot%s/%s"
MAX_ZEICHEN = 4000      # Telegram bricht bei 4096 hart ab
MAX_FEHLER = 4          # Telegram-Gegenstellenfehler hintereinander -> Pause
POLL_DAUER = 25         # getUpdates long polling
A2A_POLL_S = 3          # GetTask-Intervall
A2A_TIMEOUT_S = 300     # Zeitlimit EINES HTTP-Aufrufs zum Gateway
# SO LANGE DARF EIN FREITEXT-AUFTRAG LAUFEN (01.10.2026): Der Hauptagent braucht
# fuer echte Arbeit gemessen 400 s bis 25 min (Gateway-Log 01.10.2026: 401,4 s
# fuer "Omniquant Handel Freigabe auf kraken live", 1504,6 s fuer die Rueckfrage
# danach). Der SkillsBot gab nach 300 s auf und antwortete mit dem 16 Zeichen
# langen "(Aufgabe FAILED)" - der Auftrag war nicht gescheitert, die Frist zu
# kurz. Freitext bekommt deshalb DIESELBE Frist wie /bot: gleiche Arbeit,
# gleiche Grenze.
A2A_FRIST_S = 1800

BOT_FRIST_S = 1800      # so lange darf ein /bot-Auftrag laufen (Kaltstart + Arbeit)

# Bilder einer Nachricht (03.10.2026, Auftrag Max): "/bot openmontage mit dem
# Muster im 2. Bild den Boden im 1. Bild bedecken" kam als BILDUNTERSCHRIFT
# und wurde ersatzlos verworfen - die Schleife las nur message.text,|caption
# blieb None, `continue` verschluckte die Nachricht OHNE Log-Eintrag. Telegram
# verlangt fuer Medien zwingend eine caption, deshalb ist ein Bild ohne Text
# fuer Max der normale Fall ("hier, guck mal"). Der Bot braucht die Dateien
# auf der Platte, sonst kann er sie nicht sehen.
BILDER_PFAD = os.path.join(HIER, "bilder")
BILD_FENSTER = 6        # so viele Bilder bleiben je Chat liegen


def _bild_text(nachricht):
    """Der Text einer Nachricht: caption zaehlt genauso wie text."""
    return (nachricht.get("text") or nachricht.get("caption") or "").strip()


def _bilder(nachricht):
    """GENAU EIN Bild aus dieser Nachricht - die groesste Fassung.

    Telegram liefert pro Foto bis zu vier Stufen in EINER `photo`-Liste
    (thumb/klein/mittel/gross). Sie sind Fassungen DESSELBEN Bildes; wer alle
    nimmt, laedt fuenfmal dieselbe Datei und nennt sie fuenf Bilder. Max hat
    zudem zwei Fotos als zwei Nachrichten geschickt (Bild 1, Bild 2) - eine
    Nachricht ist ein Bild, die Gruppe ergibt sich aus der Reihenfolge.
    """
    fotos = nachricht.get("photo") or []
    if fotos:
        return [max(fotos, key=lambda x: x.get("file_size", 0))["file_id"]]
    for gruppe in ("document", "video", "audio", "voice"):
        d = nachricht.get(gruppe)
        if isinstance(d, dict) and d.get("file_id"):
            return [d["file_id"]]
    return []


def _bilder_holen(nachricht, cache_key):
    """Das Bild als Datei ablegen. (Pfad, Grund bei Fehler).

    Die Ablage ist ein ROLLIERENDES FENSTER je Chat: Max schickt Bild 1 und
    Bild 2 als zwei Nachrichten ("das Muster im 2. Bild, der Boden im 1.").
    Ein Fenster je Nachricht wuerde Bild 1 sofort wieder loeschen - dann sieht
    der Agent nur ein Bild und kann den Auftrag nicht ausfuehren.

    Ein Fehler wird NICHT verschluckt: gemeldet wurde "Betrachte das Bild"
    und dann lief ein Auftrag ohne Bild. Der Grund wandert ins Protokoll.
    """
    ids = _bilder(nachricht)
    if not ids:
        return "", ""
    ziel = os.path.join(BILDER_PFAD, cache_key)
    pfad = ""
    try:
        os.makedirs(ziel, exist_ok=True)
        # _ruf() gibt das "result" bereits entpackt zurueck - ein
        # .get("result") darueber ergaebe {} und der Auftrag laeuft ohne Bild.
        info = _ruf("getFile", {"file_id": ids[0]}) or {}
        pfad_rel = info.get("file_path")
        if not pfad_rel:
            return "", "Telegram gab keinen Pfad"
        endung = os.path.splitext(pfad_rel)[1] or ".jpg"
        nummer = 1
        while True:
            pfad = os.path.join(ziel, "bild%d%s" % (nummer, endung))
            if not os.path.exists(pfad):
                break
            nummer += 1
        url = ("https://api.telegram.org/file/bot%s/%s"
               % (token(), pfad_rel))
        with urllib.request.urlopen(url, timeout=60) as q:
            inhalt = q.read()
        with open(pfad, "wb") as f:
            f.write(inhalt)
    except Exception as e:                                # noqa: BLE001
        # Kein Pfad zurueck: eine halb geschriebene Datei als Bild zu
        # melden waere schlimmer als gar keins - der Agent liest dann
        # ins Leere und raeiselt am falschen Grund.
        if pfad and os.path.exists(pfad):
            try:
                os.remove(pfad)
            except OSError:
                pass
        return "", str(e)[:120]
    # Fenster schliessen: die letzten BILD_FENSTER bleiben, der Rest weg.
    try:
        for datei in sorted(os.listdir(ziel)):
            alt = os.path.join(ziel, datei)
            num = _bild_nummer(alt)
            if num > BILD_FENSTER:
                os.remove(alt)
    except OSError:
        pass
    return pfad, ""


def _bild_nummer(pfad):
    """Die laufende Nummer aus 'bild3.jpg' - 0 bei allem anderen."""
    name = os.path.basename(pfad)
    if not name.startswith("bild") or "." not in name:
        return 0
    try:
        return int(name[4:name.index(".")])
    except ValueError:
        return 0


def _fenster_bilder(cache_key):
    """Alle Bilder im Fenster dieses Chats, in Reihenfolge der Sendung."""
    ziel = os.path.join(BILDER_PFAD, cache_key)
    try:
        dateien = [os.path.join(ziel, d) for d in os.listdir(ziel)]
    except OSError:
        return []
    return sorted(dateien, key=_bild_nummer)


def _bilder_fuer_auftrag(nachricht, text, cache_key):
    """Bilder, die zu DIESEM Auftrag gehoeren - nicht das ganze Chat-Fenster.

    GEMESSEN 04.10.2026: Max schickte Fliesenbilder, dann einen Handelsauftrag
    ("Spuren: Auswertung"). Der Bot haengte die Fliesenbilder an den
    Handelsauftrag, weil er das GANZE Fenster an JEDE Nachricht haengte.

    Regel: Bilder kommen nur mit, wenn die Nachricht selbst ein Bild
    MITBRACHTE (dann ist der Text die Bildunterschrift) ODER der Text
    ausdruecklich auf "Bild" verweist ("Muster im 2. Bild"). Ein reiner
    Textauftrag ohne Bild und ohne "Bild"-Wort bekommt KEINE Bilder.
    """
    if not _bilder(nachricht) and "Bild" not in text:
        return []
    return _fenster_bilder(cache_key)


def _mit_bildern(frage, pfade):
    """Die Bildpfade an den Auftrag haengen - der Agent soll sie SEHEN."""
    if not pfade:
        return frage
    beschriftung = ", ".join(
        "Bild %d = %s" % (_bild_nummer(p), os.path.basename(p))
        for p in pfade)
    return (frage + "\n\nBilder aus diesem Chat (in dieser Reihenfolge):\n"
            + beschriftung
            + "\nLies jede Datei mit dem vision/image-Tool - nur den "
              "Dateinamen zu lesen reicht nicht.\n"
            + "\n".join("- %s" % p for p in pfade))


HERMES_EXE = os.path.join(WURZEL, "Agenten", "Hermes", "bin", "hermes.exe")
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


def chat_erlaubt(chat):
    """Ob eine Chat-ID bedient wird: die DM (TELEGRAM_CHAT_ID) und seit
    20.10.2026 die Telegram-Gruppe 'MaximilianundClaude-Code'
    (-1003980261765, Entscheidung Max zu T-411). Der SkillsBot bedient
    damit auch Gruppenauftraege; der bots-Verteiler bleibt fuer /bot-Dispatch."""
    if chat == chat_id():
        return True
    return chat == -1003980261765


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


def _a2a_status():
    """Kurzstatus der A2A-Bruecke: Port 9900 + Agent-Card. Nur lesend, schnell.

    Kein SendMessage (das wuerde einen echten Agenten-Task anstossen und
    Sekunden kosten); ein offener Port plus lesbare Agent-Card beweisen, dass
    der Gateway steht und Freitext//run ihn erreichen.
    """
    port_offen = False
    try:
        with socket.create_connection(("127.0.0.1", 9900), timeout=2):
            port_offen = True
    except OSError:
        port_offen = False
    if not port_offen:
        return ("A2A-Gateway (127.0.0.1:9900) ist DOWN - Freitext und /run "
                "erreichen hermes-maks-pc nicht. Der Waechter "
                "(MaxHirn-Gateway-Waechter) startet ihn alle 2 min neu; "
                "sonst: VBS Hermes_Gateway_2ef9d0b7.vbs.")
    agent = "unbekannt"
    try:
        with urllib.request.urlopen(KARTE_URL, timeout=3) as ant:
            karte = json.loads(ant.read().decode("utf-8"))
            agent = karte.get("name") or "unbekannt"
    except Exception:  # noqa: BLE001
        agent = "(Agent-Card nicht lesbar)"
    return ("A2A-Bruecke OK: Port 9900 offen, Agent-Card = %s. "
            "Freitext und /run erreichen den Agenten." % agent)


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


def frist_meldung():
    """Was nach A2A_FRIST_S gesagt wird - EINE Stelle, damit die Meldung
    pruefbar ist (ein Text im Funktionsrumpf laesst sich nicht testen).

    Sie sagt drei Dinge: es laeuft noch, es ist NICHT gescheitert, und womit
    es weitergeht. Das nackte "(Aufgabe FAILED)" (16 Zeichen) hat am
    01.10.2026 genau das Gegenteil behauptet.
    """
    return ("Der lokale Agent arbeitet noch (fuer echte Arbeit braucht er oft "
            "7 bis 25 Minuten) - hier wurde nach %d Minuten abgebrochen. Der "
            "Auftrag ist NICHT gescheitert: er laeuft dort weiter. Fuer lange "
            "Auftraege nimm die Desktop-App oder /bot NAME - beide setzen fort, "
            "diese Schnittstelle nicht." % (A2A_FRIST_S // 60))


def _aufgabe_abholen(aufgabe):
    """Task bis TASK_STATE_COMPLETED verfolgen, Antworttext zurueckgeben."""
    tid = aufgabe.get("id")
    kontext = aufgabe.get("contextId")
    for _ in range(A2A_FRIST_S // A2A_POLL_S):
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
    warnung = frist_meldung()
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

# SCHREIBWEISEN (01.10.2026): Max tippt am Handy auch die Einzahl - am 01.10.
# kam "/strategie" und der Bot antwortete "Kein SkillsBot-Befehl" (207 Zeichen).
# Ein anderer Name darf keine Auskunft kosten; intern heisst der Befehl
# weiterhin /strategien, damit /hilfe und handel_befehle EINE Quelle bleiben.
HANDELS_ALIASE = {"/lage": "/lage", "/live": "/live",
                  "/bericht": "/bericht", "/spuren": "/spuren",
                  "/strategien": "/strategien", "/strategie": "/strategien",
                  "/strat": "/strategien", "/indikatoren": "/indikatoren",
                  "/indikator": "/indikatoren", "/markt": "/markt"}


def _handelsbefehl(wort):
    """Der kanonische Name eines lesenden Handelsbefehls, oder None.

    Die Schreibweisen stehen hier an EINER Stelle - die Liste der Befehle
    selbst bleibt in `_handelsantwort` (und damit bei handel_befehle).
    """
    return HANDELS_ALIASE.get(wort)


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
    if wort == "/live":
        return handel_befehle.live()
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


def _ziel_lesen(chat):
    """Der gerade aktive Bot je Chat; abgelaufen oder unbekannt -> None."""
    ziel = _lade_json(ZIEL_PFAD, {}).get(str(chat))
    if not isinstance(ziel, dict):
        return None
    name = ziel.get("name") or ""
    if name not in bot_namen():
        return None
    if time.time() - float(ziel.get("zeit") or 0) > ZIEL_FRIST_S:
        return None
    return name


def _ziel_setzen(chat, name):
    """Bot merken (Dauerbetrieb); leere Name loescht."""
    ziele = _lade_json(ZIEL_PFAD, {})
    if not name:
        ziele.pop(str(chat), None)
    else:
        ziele[str(chat)] = {"name": name, "zeit": time.time()}
    _speichere_json(ZIEL_PFAD, ziele)
    return name or None


def _ziel_meldung(name):
    """Was nach /bot NAME ohne Auftrag gesagt wird - EINE Stelle.

    Beide Richtungen nennen die Syntax: /bot NAME schaltet ein, /bot NAME
    NACHRICHT fragt sofort, /bot (allein) schaltet ab. Wer die Form nicht
    sieht, tippt sie am Handy nicht.
    """
    if not name:
        return ("Bot abgeschaltet - der naechste Freitext geht wieder an "            "den Hauptagenten.\n\n"            "Syntax: /bot NAME NACHRICHT (Beispiel: /bot openterminal Was steht in der README?)\n"            "/bot NAME schaltet den Bot ein, /bots zeigt die Namen.")
    return ("Bot %s ist jetzt der Adressat. Sende den Auftrag als naechste "            "Nachricht - Text ODER Bild. Er geht an %s, nicht an den "            "Hauptagenten. Antwort in 30 bis 60 s plus Arbeitszeit (bis %d "            "min).\n\nAbschalten: /bot aus" % (name, name, BOT_FRIST_S // 60))


def _bot_profil_ordner():
    """Agenten/Hermes/profiles/ - die Wahrheit fuer Bot-Namen (kein Raten)."""
    return os.path.join(WURZEL, "Agenten", "Hermes", "profiles")


def bot_namen():
    """Namen aller Hermes-Profile (Unterordner mit config.yaml)."""
    wurzel = _bot_profil_ordner()
    ergebnis = []
    try:
        for name in os.listdir(wurzel):
            # Versteckte Ordner sind keine Profile: `.deleted`, `.sicherung`
            # und die Staging-Reste eines abgebrochenen
            # `hermes profile create` (.nerd.staging-<pid>) tragen eine
            # config.yaml und stuenden sonst als Phantom-Bot in /bots.
            if name.startswith("."):
                continue
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


def _bot_fragen(name, text, frist=BOT_FRIST_S):
    """Eine Frage an das Profil <name> - der Bot antwortet selbst.

    Der Weg ist ein frischer Einzelauftrag (chat -q): keine Sitzung, kein
    Kontext, kein Gateway. Was der Bot kann, kann er hier; der SkillsBot
    fuehrt nichts aus, er stellt nur die Verbindung her.
    """
    exe = HERMES_EXE
    if not os.path.isfile(exe):
        raise SkillsBotFehler("hermes.exe nicht gefunden: %s" % exe)
    # NICHT mit subprocess.run(timeout=...) arbeiten: das killt den Bot
    # mitten in der Arbeit und die ganze Aufgabe ist verloren. Gemessen am
    # 21.09.2026 lag die alte Grenze bei A2A_TIMEOUT_S + 30 = 330 s; ein Bot,
    # der ein Repo liest oder ein Buch auswertet, braucht laenger - die
    # Befehle brachen deshalb "wegen Zeitlimit" ab, ohne dass etwas kaputt war.
    # Jetzt laeuft der Bot bis BOT_FRIST_S; erst danach wird abgebrochen, und
    # die Meldung sagt, was zu tun ist.
    try:
        lauf = subprocess.Popen(
            [exe, "-p", name, "chat", "-q", text, "-Q"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace", env=_hermes_umgebung(),
            cwd=WURZEL,
            creationflags=subprocess.CREATE_NO_WINDOW)
    except OSError as e:
        raise SkillsBotFehler("Bot %s nicht startbar: %s" % (name, e))
    try:
        aus, fehler = lauf.communicate(timeout=frist)
    except subprocess.TimeoutExpired:
        lauf.kill()
        lauf.communicate()
        raise SkillsBotFehler(
            "Bot %s hat nach %d Minuten nicht geantwortet - der Auftrag war "
            "zu gross. Teile ihn in Teilstuecke (z.B. erst lesen, dann "
            "aendern) oder nimm fuer lange Laeufe einen Cronjob."
            % (name, frist // 60))
    if lauf.returncode != 0:
        stderr = (fehler or "").strip().splitlines()
        grund = stderr[-1][:200] if stderr else "Exit-Code %s" % lauf.returncode
        raise SkillsBotFehler("Bot %s ist gescheitert: %s" % (name, grund))
    antwort = (aus or "").strip()
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
        alt = _ziel_setzen(chat, None)
        return _ziel_meldung(alt), None
    name = rest[0].lstrip("/")
    texte = " ".join(rest[1:]).strip()
    if name in ("aus", "off", "stop"):
        _ziel_setzen(chat, None)
        return _ziel_meldung(None), None
    if name not in bot_namen():
        return ("Kein Profil %r. /bots zeigt die Namen." % name), None
    if not texte:
        # Bot einschalten, NICHT fragen: am Handy kommt der Auftrag als
        # naechste Nachricht (oft ein Bild) - dafuer ist dieser Weg da.
        _ziel_setzen(chat, name)
        return _ziel_meldung(name), None
    # Erst sagen, dann tun: ein frischer Agent braucht 30-60 s Kaltstart.
    sende(chat, "Bot %s uebernimmt: 30-60 s Kaltstart, eine echte Aufgabe "
              "darf bis %d min dauern. Ergebnis kommt, sobald er fertig "
              "ist." % (name, BOT_FRIST_S // 60))
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


def _provider_kontext(zeilen, provider, modell):
    """context_length eines Modells aus dem providers-Block, sonst None."""
    in_provider = in_models = in_modell = False
    for zeile in zeilen:
        roh = zeile.rstrip()
        if not roh or roh.lstrip().startswith("#"):
            continue
        tiefe = len(roh) - len(roh.lstrip())
        name = roh.strip().split(":", 1)[0].strip()
        if tiefe == 2 and roh.endswith(":"):
            in_provider = name == provider
            in_models = in_modell = False
            continue
        if not in_provider:
            continue
        if tiefe == 4 and name == "models":
            in_models = True
            continue
        if in_models and tiefe == 6 and roh.endswith(":"):
            in_modell = name == modell
            continue
        if in_modell and tiefe >= 8 and name == "context_length":
            wert = roh.split(":", 1)[1].strip()
            return wert or None
    return None


def modell_text(pfad=None):
    """Modell und Fallback-Kette DES SKILLSBOTS - rein lesend (21.09.2026).

    Der Bot hat kein eigenes Modell: er reicht per A2A an den Gateway weiter,
    und der bedient das default-Profil. Gewechselt wird deshalb in der
    Hermes-config, nicht hier.
    """
    pfad = pfad or CONFIG_HERMES
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            zeilen = f.read().splitlines()
    except OSError as e:
        return "Hermes-config nicht lesbar: %s" % str(e)[:120]

    block = {}
    im_modell = False
    rueckfall = []
    im_rueckfall = False
    # Subagenten (delegate_task) fahren ein EIGENES Modell, nicht das des
    # Hauptagenten. Wer nach "welches Modell" fragt, meint oft genau das -
    # deshalb wird der delegation:-Block mitgelesen.
    delegation = {}
    im_delegation = False
    for zeile in zeilen:
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        if not zeile.startswith(" "):
            im_modell = zeile.strip() == "model:"
            im_rueckfall = zeile.strip() == "fallback_providers:"
            im_delegation = zeile.strip() == "delegation:"
            continue
        if im_delegation and zeile.startswith("  ") and not zeile.startswith("   "):
            s, _, w = zeile.strip().partition(":")
            if s in ("model", "provider"):
                delegation[s] = w.strip().strip("\"'")
        if im_modell and zeile.startswith("  ") and not zeile.startswith("   "):
            schluessel, _, wert = zeile.strip().partition(":")
            block[schluessel] = wert.strip()
        if im_rueckfall:
            if zeile.strip().startswith("- provider:"):
                rueckfall.append({"provider": zeile.split(":", 1)[1].strip()})
            elif zeile.strip().startswith("model:") and rueckfall:
                rueckfall[-1]["model"] = zeile.split(":", 1)[1].strip()

    provider = block.get("provider", "?")
    modell = block.get("default", "?")
    aus = ["Modell des SkillsBots (default-Profil, A2A nach 127.0.0.1:9900):",
           "%s  ueber  %s" % (modell, provider)]
    if block.get("base_url"):
        aus.append("Endpunkt: " + block["base_url"])
    kontext = _provider_kontext(zeilen, provider, modell)
    aus.append("Kontext: %s Token" % kontext if kontext
               else "Kontext: nicht in der config angegeben")
    if rueckfall:
        aus.append("Fallback: " + " -> ".join(
            "%s/%s" % (r.get("provider", "?"), r.get("model", "?")) for r in rueckfall))
    if delegation.get("model"):
        aus.append("Subagenten: %s ueber %s" % (delegation["model"],
                                                delegation.get("provider", "?")))
    aus.append("Der Bot selbst hat kein Modell; gewechselt wird in")
    aus.append("Agenten/Hermes/config.yaml (hermes config set model.provider /")
    aus.append("model.default). Nur lesend, kein A2A-Aufruf.")
    return "\n".join(aus)


def hilfe_text():
    # Kein HTML: der SkillsBot sendet ohne parse_mode - Marken staenden
    # woertlich in der Nachricht (der Handelsbot nutzt dafuer befehle.hilfe()).
    return ("Ich reiche deine Nachrichten per A2A an den lokalen Hermes-"
            "Agenten (hermes-maks-pc) weiter - der hat alle Skills.\n"
            "\nHandel (lesend, aus dem Handel-Ordner)\n"
            "/lage - offene Positionen je Spur, Live-Tore, Freigaben\n"
            "/live - NUR die Spuren mit Orderweg: Fenster, Buch, letzter "
            "echter Vorgang\n"
            "/bericht - voller Tagesbericht (dauert, mit Rangliste)\n"
            "/spuren - alle Spur-Namen\n"
            "/spur NAME - eine Spur in der Tiefe\n"
            "/strategien - Bilanz aller Strategien nebeneinander\n"
            "/indikatoren - die vier Indikator-Spuren: Signale und Treffer\n"
            "/markt - Kurs, 24 h, Trend, Volatilitaet\n"
            "/status - gespeicherter Dateistand (alle Spuren)\n"
            "/papierstatus - nur Papierspuren\n"\
            "/a2a - Status der A2A-Bruecke (Port 9900 + Agent-Card)\n"
            "/model - Modell und Fallback-Kette dieses Bots (lesend)\n"
            "/prognose [N] - Marktbeobachtung long/short (bis 240 s)\n"
            "/skills [SUCHE] - die gelernten Skills, nach Gruppen\n"
            "/skill NAME - ein Skill im Volltext\n"
            "/run NAME [Auftrag] - einen Skill AUSFUEHREN (bis 5 min)\n"
            "/bots - alle Hermes-Profile (Repo-Bots)\n"
            "/bot NAME NACHRICHT - Frage an einen Repo-Bot (bis 5 min)\n"
            "/bot NAME - schaltet den Bot EIN; der naechste Auftrag\n"
            "  (Text ODER Bild, ohne Schraegstrich) geht an IHN, nicht\n"
            "  an den Hauptagenten. /bot aus schaltet wieder ab.\n"
            "/hilfe - diese Liste\n"
            "\nFreigaben nur im Handelsbot: /freigabe_xperp, /ja_xperp STUNDEN, "
            "/nein_xperp, /stop_xperp.\n"
            "SWAP-Live bleibt gesperrt. Freitext ohne aktiven Bot geht an Hermes.")


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


def _freitext_im_thread(text, chat, kontext):
    """Freitext-Auftrag asynchron an den A2A-Agenten geben (T-288).

    Der SkillsBot wartet sonst bis A2A_FRIST_S (30 min) synchron auf den
    Hauptagenten und kann in der Zeit nichts anderes beantworten - /lage,
    /strategien und jede weitere Nachricht haengen. Stattdessen laeuft der
    Auftrag hier in einem Hintergrund-Thread: `sende()` ist thread-fest, die
    Kontext-ID wird im Thread fortgeschrieben. Das Ergebnis kommt als eigene
    Nachricht, sobald der Agent fertig ist.
    """
    try:
        antwort, neuer_kontext = frage(text, kontext)
    except Exception as fehler:                               # noqa: BLE001
        try:
            sende(chat, "Freitext gescheitert: %s" % str(fehler)[:150])
        except Exception:                                     # noqa: BLE001
            pass
        return
    if neuer_kontext:
        kontexte = _lade_json(KONTEXT_PFAD, {})
        kontexte[str(chat)] = neuer_kontext
        _speichere_json(KONTEXT_PFAD, kontexte)
    try:
        sende(chat, ohne_denken(antwort) or "Keine Antwort vom Agenten.")
    except Exception:                                         # noqa: BLE001
        pass


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
    if t == "/a2a":
        # Kurzstatus der A2A-Bruecke (Port 9900 + Agent-Card), rein lesend.
        return _a2a_status(), kontext
    if wort == "/model":
        # Das Modell des SkillsBots ist das des default-Profils (der Bot hat
        # keins). Rein lesend - ein Schreibpfad aus Telegram heraus wuerde die
        # Hermes-config anfassen, das bleibt Handarbeit.
        return modell_text(), kontext
    if wort == "/spur":
        import handel_befehle
        try:
            return handel_befehle.klartext(
                handel_befehle.spur(" ".join(teile[1:]))), kontext
        except Exception as e:                                # noqa: BLE001
            return "Spur nicht lesbar: %s" % str(e)[:120], kontext
    if _handelsbefehl(wort):
        try:
            import handel_befehle
            return handel_befehle.klartext(
                _handelsantwort(_handelsbefehl(wort))), kontext
        except Exception as e:                                # noqa: BLE001
            return ("Auskunft nicht lesbar: %s\nIm Handelsbot geht %s weiter."
                    % (str(e)[:120], _handelsbefehl(wort))), kontext
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
        ziel = _ziel_lesen(chat)
        if ziel:
            # Max hat vermutlich eine Bot-Nachricht mit Schraegstrich
            # geschickt, waehrend der Bot aktiv war: /lage gehoert zum
            # Hauptagenten, /bot NAME zum Bot.
            return ("%r ist kein Befehl. Aktiv ist gerade Bot %s - ein "
                    "Auftrag ohne Schraegstrich geht an ihn; /bot %s "
                    "NACHRICHT schaltet direkt auf ihn.\n\nKein Auftrag "
                    "an den Agenten gesendet." % (wort, ziel, ziel)), kontext
        return ("Kein SkillsBot-Befehl. /hilfe zeigt die Liste.\n"
                "Freigaben nur im Handelsbot: /freigabe_xperp, /ja_xperp STUNDEN, "
                "/nein_xperp, /stop_xperp.\n"
                "Einen Bot rufst du mit /bot NAME (schaltet ihn ein), danach "                "kommt der Auftrag ohne Schraegstrich - Text oder Bild.\n"
                "SWAP-Live ist nicht angebunden. Kein Auftrag an den Agenten gesendet."), kontext
    # Aktiver Bot? Dann geht der Auftrag an ihn, nicht an den Hauptagenten
    # (Auftrag Max 03.10.2026). Nach EINEM Auftrag ist er abgeschaltet,
    # damit der naechste Freitext nicht im falschen Bot landet.
    ziel = _ziel_lesen(chat)
    if ziel:
        _ziel_setzen(chat, None)
        sende(chat, "Bot %s uebernimmt: 30-60 s Kaltstart, eine echte "
                   "Aufgabe darf bis %d min dauern. Ergebnis kommt, sobald "
                   "er fertig ist." % (ziel, BOT_FRIST_S // 60))
        try:
            antwort = _bot_fragen(ziel, t)
        except Exception as fehler:                     # noqa: BLE001
            return ("Bot %s gescheitert: %s"
                    % (ziel, str(fehler)[:150])), kontext
        return ohne_denken(antwort), kontext
    # Erst sagen, dann tun (Muster von /run): der Hauptagent braucht fuer echte
    # Arbeit Minuten. Ohne diese Zeile sieht es aus, als haenge der Bot.
    sende(chat, "Angenommen - der Hauptagent arbeitet daran (oft 7 bis 25 "
         "Minuten). Das Ergebnis kommt als eigene Nachricht, sobald er fertig "
         "ist; der Bot bleibt in der Zeit fuer andere Anfragen erreichbar.")
    # T-288: Freitext in einen Hintergrund-Thread geben, sofort antworten und
    # das Ergebnis als eigene Nachricht senden. Der Bot ist damit nicht mehr
    # bis zu 30 Minuten blockiert (Muster: der Dauerlauf meldet asynchron;
    # sende() ist thread-fest, die Kontext-ID wird im Thread fortgeschrieben).
    threading.Thread(target=_freitext_im_thread, args=(t, chat, kontext),
                     daemon=True).start()
    return "Angenommen.", kontext


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
                nachricht = n.get("message") or {}
                chat = nachricht.get("chat", {}).get("id")
                text = _bild_text(nachricht)
                if chat is None:
                    continue
                if not text:
                    # Bild OHNE Bildunterschrift: kein Auftrag, aber sichtbar.
                    # Nur melden, wenn die Ablage etwas gibt - sonst ist es ein
                    # Stickerspam und der Log laeuft voll.
                    if not _bilder(nachricht):
                        continue
                    text = "(Bild ohne Unterschrift)"
                if not chat_erlaubt(chat):
                    _log(chat, "(fremd)", 0, "abgewiesen", len(text))
                    offset = uid + 1
                    continue
                cache_key = "chat%s" % chat
                _neu, bild_fehler = _bilder_holen(nachricht, cache_key)
                if bild_fehler:
                    _log(chat, text[:40], 0, "bildfehler", 0,
                         fehler=bild_fehler)
                # Bilder NUR wenn die Nachricht selbst ein Bild hat oder der
                # Text auf "Bild" verweist. Das GANZE Fenster an JEDE Nachricht
                # zu haengen klebte am 04.10.2026 Fliesenbilder an einen
                # Handelsauftrag ("Spuren: Auswertung").
                bilder = _bilder_fuer_auftrag(nachricht, text, cache_key)
                start = time.time()
                try:
                    antwort, _ = bearbeite(_mit_bildern(text, bilder),
                                           chat)
                    # ZUERST senden, dann loggen und den Offset
                    # vorruecken. Ohne diese Zeile wurde die Antwort
                    # verarbeitet, protokolliert und der Offset
                    # gespeichert - aber NIE an Telegram geschickt:
                    # die Nachricht war fuer den Bot erledigt und bei
                    # Max kam nichts an. Gefunden am 03.10.2026 durch
                    # den Test test_netzfehler_nachricht_geht_nicht_verloren
                    # (erwartet eine gesendete Antwort, bekam keine).
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

