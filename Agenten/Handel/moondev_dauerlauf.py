"""
MoonDev-Agenten an den Haus-Dauerlauf anbinden (17.09.2026, Max).

Was das ist
-----------
Die geklonten Moon-Dev-Agenten (Werkstatt/moon-dev-ai-agents/src/agents)
sind eigenstaendige Endlos-Loops mit eigener main() - KEINE Haus-Spuren mit
Buch. Dieses Modul faehrt sie als Kindprozesse weiter, damit sie ueberleben:

  - Stoppt ein Kind (Absturz, Exception), wird es nach kurzer Pause neu
    gestartet (Laeuft-Pruefung mit Wartezeit).
  - Jeder Zyklus des Hauses prueft die Kinder und startet fehlende wieder.
  - MAXHIRN_ROUTINE=1 wird gesetzt (kein Freigabefenster aus dem Dienst).
  - Nur Standardbibliothek (subprocess), kein venv noetig.

Welche Agenten
--------------
EXAKT zwei, bewusst klein: nur die, die wir hier wirklich betreiben
(new_or_top und kraken). Das Repo enthaelt ~50 weitere Agenten; ein Teil
braucht bezahlte Schluessel (DEEPSEEK_KEY, ANTHROPIC_KEY, COINGECKO_API_KEY,
SOLANA_PRIVATE_KEY ...), ein Teil ist Spielfeld. Sie werden NICHT alle
gestartet - das wuerde Schluesselkosten fressen und Rauschen erzeugen.
Neue Agenten hier AUFNEHMEN heisst: sie laufen unter dem Haus-Dauerlauf,
mit derselben Wiederstart-Garantie.

Wichtig
-------
Jeder Agent ist ein UNENDLICHER Prozess (while True). Der Dauerlauf startet
ihn und wartet nicht - Der Haus-Dauerlauf ist der Treiber, der Prozess
lebt eigenstaendig.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent                      # Agenten/Handel
REPO = (HIER / ".." / ".." / "Werkstatt" / "moon-dev-ai-agents").resolve()

# WICHTIG: Die Agenten brauchen Pakete aus dem REPO-EIGENEN venv (requests,
# pandas, openai ...) - sys.executable ist hier der AUFRUFER-Interpreter
# (z.B. scanner/.venv, wenn der Haus-Dauerlauf startet) und hat diese Pakete
# NICHT. Fest auf den Repo-Interpreter zeigen (gemessen 17.09.2026:
# ModuleNotFoundError: requests, solange sys.executable verwendet wurde).
# python.exe (nicht pythonw) ZUSAMMEN mit creationflags=CREATE_NO_WINDOW am
# Popen unten: ein pythonw-Kind ist ein GUI-Subsystem-Prozess OHNE Konsole,
# dessen eigene Konsolen-Kinder (onchainos.exe, powershell) daher je ein
# SICHTBARES Fenster allozieren - der Fokus-Raeuber. python.exe mit
# CREATE_NO_WINDOW besitzt dagegen eine fensterlose Konsole, die alle
# Nachfahren erben: kein Popup, keine verwaisten Fenster (frueher der Grund
# fuer pythonw: 27 verwaiste Fenster nach Absturz; CREATE_NO_WINDOW behebt das
# an der Wurzel). Die Ausgabe laeuft weiter in die ag_log-Dateien.
REPO_PYTHON = str(REPO / ".venv" / "Scripts" / "python.exe")

def _repo_env() -> dict[str, str]:
    """Liest die WURZEL-.env des Repos direkt (nur OLLAMA_*).

    WICHTIG: new_or_top_agent.py ruft load_dotenv() ohne Pfad auf; das sucht
    per find_dotenv() aufwaerts ab dem Modulordner (src/agents/) und findet
    dabei src/.env (eigene Zugangsdaten, Restream-API - Stufe-0-Datei, NIE
    anfassen) VOR der Wurzel-.env, weil die naeher liegt. Gemessen
    17.09.2026: OLLAMA_MODEL blieb dadurch leer, der Agent verlangte den nie
    gesetzten DEEPSEEK_KEY und stuerzte ab (Neustart-Schleife alle 60 s).
    python-dotenv ueberschreibt bereits gesetzte Umgebungsvariablen NICHT
    (override=False ist die Vorgabe) - eine hier vorab gesetzte Variable
    bleibt unangetastet, unabhaengig davon, welche .env load_dotenv() findet.
    """
    werte: dict[str, str] = {}
    pfad = REPO / ".env"
    try:
        for zeile in pfad.read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if not zeile or zeile.startswith("#") or "=" not in zeile:
                continue
            schluessel, _, wert = zeile.partition("=")
            if schluessel.strip() in ("OLLAMA_MODEL", "OLLAMA_BASE_URL"):
                werte[schluessel.strip()] = wert.strip()
    except OSError:
        pass
    return werte

# Der LOKALE Weg. Ollama wurde am 11.10.2026 deinstalliert; die Haus-Laufzeit
# ist jetzt der verwaltete llama-server auf 127.0.0.1:18434. Der spricht NUR
# OpenAI - `/api/chat`, `/api/tags`, `/api/version` antworten dort mit HTTP 404
# (nachgemessen 12.10.2026). Die Agenten rufen aber genau Ollamas native Form.
# Deshalb steht hier jetzt ein Adapter, der Ollama-nativ annimmt und an
# llama-server weiterreicht - das Gegenstueck der alten Bruecke.
BRUECKE_PORT = 11498
BRUECKE_BASIS = "http://127.0.0.1:11498/v1"
BRUECKE_WERKZEUG = (HIER / ".." / "Werkzeuge" / "llamacpp-ollama-bruecke.py").resolve()

def _bruecke_laeuft(port: int = BRUECKE_PORT) -> bool:
    """Lauscht ueberhaupt jemand auf dem Port?

    Der Unterschied zu _bruecke_gesund ist die Kernreparatur vom 12.10.2026:
    "gesund" fragt die GEGENSTELLE, "laeuft" fragt den EIGENEN Port. Vorher
    entschied nur "gesund" - und als die Gegenstelle (Ollama) fehlte, konnte
    die Antwort nie gesund werden. Jeder Zyklus startete eine weitere Bruecke,
    keine wurde je beendet: 776 Prozesse, 7,4 GB, Commit-Limit am Anschlag.
    Wer nur nach "laeuft" entscheidet, startet hoechstens EINE.
    """
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2.0):
            return True
    except OSError:
        return False


def _bruecke_gesund(port: int = BRUECKE_PORT, frist: float = 5.0) -> bool:
    """Antwortet die OpenAI-Bruecke auf Ollama?

    Gefragt wird der eigene Gesundheitsweg - ein reiner TCP-Test wuerde auch
    einen fremden Lauscher auf dem Port fuer gesund halten.
    """
    try:
        with urllib.request.urlopen(
                "http://127.0.0.1:%d/gesundheit" % port, timeout=frist) as a:
            return bool(json.loads(a.read().decode("utf-8", "replace")).get("ok"))
    except Exception:                                              # noqa: BLE001
        return False


def _bruecke_sicherstellen() -> str:
    """Bruecke starten, falls sie nicht laeuft. Leere Rueckgabe = laeuft.

    Sie ist ein DIENST, kein Agent: sie laeuft in eigener Prozessgruppe und
    wird nicht als Kind gefuehrt (ein Kind stuerbe beim Aufraeumen des Treibers
    mit und muesste jeden Zyklus neu starten).
    """
    # ERST den Port fragen, dann die Gegenstelle. Ein belegter Port laesst
    # keinen zweiten Prozess zu - ein Start waere sinnlos und erzeugt genau
    # die Schwemme, die am 12.10.2026 776 Prozesse auf den Rechner brachte.
    if _bruecke_laeuft():
        if _bruecke_gesund():
            return ""
        return ("Bruecke laeuft auf Port %d, meldet aber ungesund - kein "
                "zweiter Start (der Port ist belegt). Gegenstelle pruefen: "
                "llama-server auf 127.0.0.1:18434." % BRUECKE_PORT)
    if not BRUECKE_WERKZEUG.exists():
        return ("WARNUNG: Bruecke fehlt (%s) - Sprachmodell-Aufrufe ueber den "
                "OpenAI-Zweig scheitern." % BRUECKE_WERKZEUG)
    umgebung = {k: v for k, v in os.environ.items()
                if k not in ("PYTHONHOME", "PYTHONPATH")}
    log = HIER / "moondev_bruecke.out"
    log.parent.mkdir(parents=True, exist_ok=True)
    flags = 0
    if os.name == "nt":
        flags = (getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                 | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
    try:
        with log.open("ab") as fh:
            fh.write(("\n--- Start durch den Treiber %s ---\n"
                      % time.strftime("%Y-%m-%d %H:%M:%S")).encode("utf-8"))
            subprocess.Popen([sys.executable, str(BRUECKE_WERKZEUG),
                              "--port", str(BRUECKE_PORT)],
                             stdout=fh, stderr=subprocess.STDOUT,
                             cwd=str(HIER.parent.parent), env=umgebung,
                             creationflags=flags, close_fds=True)
    except Exception as fehler:                                    # noqa: BLE001
        return "Bruecke liess sich nicht starten: %s" % fehler
    for _ in range(10):
        time.sleep(1.5)
        if _bruecke_gesund():
            return ("Bruecke gestartet (Port %d, think:false) - war nicht "
                    "erreichbar." % BRUECKE_PORT)
    return "Bruecke gestartet, antwortet aber nach 15 s nicht - Protokoll: %s" % log


# ---------------------------------------------------------------------------
# Modellweg je Agent (Max, 18.09.2026: "auf nous/deepseek wechseln, sonst lokal")
# ---------------------------------------------------------------------------
# new_or_top_agent.py kennt drei Wege (am Code nachgelesen, 18.09.2026):
#   if OLLAMA_MODEL:                     -> lokales Ollama, OpenAI-kompatibel
#   elif "deepseek" in AI_MODEL.lower(): -> openai.OpenAI(base_url=DEEPSEEK_BASE_URL,
#                                            api_key=DEEPSEEK_KEY)
#   else:                                -> anthropic.Anthropic(ANTHROPIC_KEY)
# Der Anthropic-Weg scheidet aus (kein Guthaben), und der lokale fuehrte heute
# ins Leere: die Repo-.env nannte glm4:9b-chat:latest, das im Ollama-Store
# NICHT liegt - der Agent lief, aber jeder Aufruf endete mit "HTTP Error 404"
# und er speicherte den Fehlertext als Analyse. Der Nous-Weg traegt: die
# Nous-Inferenz-API ist OpenAI-kompatibel und liefert deepseek/deepseek-v4-flash-0731
# (18.09.2026 mit einer echten Anfrage geprueft: HTTP 200, Antwort "OK").
NOUS_BASIS = "https://inference-api.nousresearch.com/v1"
NOUS_MODELL = "deepseek/deepseek-v4-flash-0731"
OLLAMA_TAGS = "http://127.0.0.1:11498/api/tags"
# Der Adapter, nicht Ollama: llm_lokal() haengt "/api" und "/chat" an, also
# muss hier die nackte Basis ohne /v1 stehen. Mit dem alten "/v1" entstand
# ".../v1/api/chat" - eine Adresse, die es nie gab.
LOKAL_STANDARD = "gemma-4-E4B-it-OBLITERATED-Q8_0"   # Hausmodell der llama-server-Laufzeit
LOKAL_BASIS = "http://127.0.0.1:11498"

def _nous_schluessel() -> str:
    """NOUS_API_KEY aus der Prozessumgebung, sonst aus HKCU\\Environment.

    Der Dauerlauf startet aus der Aufgabenplanung und erbt die Benutzerumgebung;
    ein Start von Hand aus einer Shell sieht den Wert dagegen nicht (gemessen
    18.09.2026). Die Registry ist die Quelle, die beide Wege kennen. Der Wert
    wird nur an das Kind weitergereicht - nie geschrieben, nie protokolliert.
    """
    wert = (os.environ.get("NOUS_API_KEY") or "").strip()
    if wert:
        return wert
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as schluessel:
            return (winreg.QueryValueEx(schluessel, "NOUS_API_KEY")[0] or "").strip()
    except OSError:
        return ""

def _vorhandene_ollama_modelle() -> set:
    """Namen, die Ollama wirklich hat. Leer, wenn Ollama nicht antwortet."""
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=5) as antwort:
            return {m.get("name", "") for m in json.load(antwort).get("models", [])}
    except Exception:                                              # noqa: BLE001
        return set()

def _lokal_modell(gewuenscht: str) -> str:
    """Nennt ein Modell, das Ollama WIRKLICH hat.

    Ein Name in einer .env ist keine Zusage: glm4:9b-chat:latest stand dort und
    war nicht installiert. Der Agent sterbt daran nicht - er liefert still
    Fehlertexte statt Urteile. Genau das soll hier auffallen.
    """
    vorhanden = _vorhandene_ollama_modelle()
    if not vorhanden:
        return gewuenscht                      # Ollama nicht erreichbar: nicht raten
    for kandidat in (gewuenscht, LOKAL_STANDARD, "gemma-e4b-8k:latest"):
        if kandidat and kandidat in vorhanden:
            return kandidat
    return gewuenscht

def _weg_fuer(name: str, umgebung: dict, wege: dict) -> str:
    """Setzt den Modellweg des Agenten und gibt ihn fuer das Log zurueck."""
    schluessel = _nous_schluessel()
    if name == "new_or_top" and schluessel:
        # OLLAMA_MODEL muss WEG: es entscheidet im Agenten den Zweig, und der
        # schlaegt DEEPSEEK_* sonst still aus.
        umgebung.pop("OLLAMA_MODEL", None)
        umgebung.pop("OLLAMA_BASE_URL", None)
        umgebung["AI_MODEL"] = NOUS_MODELL
        umgebung["DEEPSEEK_KEY"] = schluessel
        umgebung["DEEPSEEK_BASE_URL"] = NOUS_BASIS
        return "nous/deepseek (%s)" % NOUS_MODELL
    # kraken_agent.py spricht Ollama-native (/api/chat) - kein OpenAI-Weg,
    # also lokal. Die Handelsseite dieses Paares ist die Haus-Spur kraken.
    gewuenscht = (wege.get("OLLAMA_MODEL") or "").strip() or LOKAL_STANDARD
    modell = _lokal_modell(gewuenscht)
    umgebung["OLLAMA_MODEL"] = modell
    umgebung["OLLAMA_BASE_URL"] = (wege.get("OLLAMA_BASE_URL") or "").strip() or LOKAL_BASIS
    zusatz = ""
    if name == "new_or_top" and not schluessel:
        zusatz = " - kein NOUS_API_KEY gefunden, deshalb lokal"
    if modell != gewuenscht:
        zusatz += " - %s liegt nicht im Store" % gewuenscht
    return "lokal (%s)%s" % (modell, zusatz)

# ---------------------------------------------------------------------------
# Welche Agenten laufen
# ---------------------------------------------------------------------------
# name  -> (startbefehl, ordner)
# startbefehl: python <pfad>  (der REPO-Interpreter, nicht sys.executable)
# ordner:      wo der Agent arbeitet (Repowurzel)
AGENTEN = {
    # new_or_top: importiert "src.config" - direkter Skriptaufruf setzt
    # sys.path[0] auf src/agents/ und das schlaegt fehl (gemessen 17.09.2026:
    # ModuleNotFoundError: No module named 'src'). Nur -m findet das Paket.
    "new_or_top": {
        "cmd": [REPO_PYTHON, "-m", "src.agents.new_or_top_agent"],
        "cwd": str(REPO),
    },
    # kraken: seit Fork-Commit 0cb95b7 (04.10.2026) "from src.agents.
    # zyklus_watchdog import ..." - als Skriptpfad dieselbe Falle wie oben
    # (ModuleNotFoundError: No module named 'src', Neustart im Kreis bis
    # 09.10.2026). Deshalb ebenfalls -m.
    "kraken": {
        "cmd": [REPO_PYTHON, "-m", "src.agents.kraken_agent"],
        "cwd": str(REPO),
    },
    # sniper_agent (19.09.2026): scannt neue Solana-Launches ueber die
    # oeffentliche Pump.fun-API (kein Schluessel). Reiner Anzeige-Scanner,
    # kein Handel - die Haus-Spur moondev_sniper fuehrt das Buch. Als
    # Dauerlaeufer im Hintergrund: AUTO_OPEN_BROWSER=False, SOUND_ENABLED=False.
    "sniper": {
        "cmd": [REPO_PYTHON, "-m", "src.agents.sniper_agent"],
        "cwd": str(REPO),
    },
    # trading_agent (19.09.2026): LLM-Trading-Bot im PAPIER-MODUS. Der
    # Original-Bot hat echte Solana-Orders (market_buy/chunk_kill). Der Umbau
    # (staging-Patch) sperrt diese hinter der Haus-Freigabedatei
    # Agenten/Handel/moondev_trading_freigabe.json (handel_erlaubt=false).
    # Ohne Freigabe NUR Protokollierung, keine echten Orders. Marktdaten von
    # Birdeye brauchen einen Schluessel - fehlt er, macht der Bot NOTHING.
    "trading": {
        "cmd": [REPO_PYTHON, "-m", "src.agents.trading_agent"],
        "cwd": str(REPO),
    },
}

PAUSE_NEUSTART = 120         # s zwischen Absturz und Neustart
# Warum 120 statt 15 (gemessen 21.09.2026): der haeufigste Sterbegrund der
# Agenten ist die GRATIS-Rate-Limit-Grenze der Datenanbieter - new_or_top
# traegt 139 Rate-Limit-Meldungen im eigenen Log, der Absturz ist
# "You have exceeded the Rate Limit" von CoinGecko (HTTP 429), kraken_agent
# stirbt in kraken_roe_oeffentlich. Wer 15 s nach dem Absturz sofort wieder
# anfragt, laeuft in dieselbe Grenze; zwei Minuten geben dem Kontingent
# Luft. Die Agenten sind Scanner (kein Orderpfad) - die Pause kostet nur
# Datenluecken, keinen Handel.
PRUEF_ALLE = 60              # s: Kinder alle 60 s pruefen
MAXHIRN_ROUTINE = "1"        # keiner fragt nach einem Fenster

# --- Verwaiste Agentenprozesse (Leak gemessen 21.09.2026) -------------------
#
# BEFUND: Der Treiber startet je Zyklus ein Kind neu, wenn das vorige tot ist.
# Ein Kind besteht unter Windows aber aus ZWEI Prozessen (venv-Startprogramm +
# echter Interpreter, beide mit derselben Kommandozeile). Der Treiber hielt nur
# das Startprogramm; starb es, blieb der Interpreter als WAISE stehen. Ueber
# Nacht (20.09. 22:17 bis 21.09. 10:00) sammelten sich so 84 Agentenprozesse,
# 80 davon aelter als eine Stunde - sie frischen das Commit-Limit auf (1,94 GB
# frei von 89,8) und liessen das lokale Modell nicht mehr laden
# (ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate).
#
# Gegenmittel an zwei Stellen:
#   1. `_stoppe` beendet den ganzen BAUM (taskkill /T /F), nicht nur das
#      Startprogramm.
#   2. Jeder Zyklus raeumt zuerst auf: Agentenprozesse, die zu keinem lebenden
#      Kind gehoeren, werden beendet - aber erst nach SCHONFRIST_S, damit ein
#      frisch gestarteter Enkel nicht im eigenen Start erschlagen wird.
KENNUNG_AGENTEN = ("src.agents", "kraken_agent.py")
SCHONFRIST_S = 300           # s: so lange gilt ein fremder Agentenprozess als frisch
#                             (kurz gehalten: die Waisen des eigenen Baums
#                              beendet der Zyklus sofort, s. _kill_baum)

LOG = HIER / "moondev_dauerlauf.log"
# Ab dieser Groesse wird eine Agenten-Logdatei beim naechsten Start gedreht.
# Ein langlebiger Agent schreibt bis zu ~50 MB je Tag (gemessen 23.09.2026:
# moondev_sniper.log 160 MB nach vier Tagen), und niemand sah es, weil das
# Wachstum nicht am RAM und nicht an der Prozesszahl auffaellt - nur am Platz.
AG_LOG_MAX_MB = 50


def _log_drehen(pfad: Path, max_mb: int = AG_LOG_MAX_MB) -> str:
    """Zu grosse Logdatei nach <name>.1 umbenennen (die alte .1 faellt weg).

    Nur beim START aufrufen: laeuft der Agent noch, haelt er die Datei offen
    und Windows verweigert das Umbenennen (gemessen 23.09.2026). Rueckgabe:
    kurze Beschreibung fuer das Treiberlog.
    """
    try:
        if not pfad.exists():
            return ""
        groesse = pfad.stat().st_size
        if groesse <= max_mb * 1024 * 1024:
            return ""
        alt = pfad.with_name(pfad.name + ".1")
        if alt.exists():
            alt.unlink()
        pfad.rename(alt)
        return "%s gedreht (%.1f MB -> %s)" % (pfad.name, groesse / 1048576, alt.name)
    except OSError as e:
        return "%s nicht gedreht: %s" % (pfad.name, e)

# ---------------------------------------------------------------------------
# Prozessliste (fuer das Aufraeumen) - nur Standardbibliothek + PowerShell
# ---------------------------------------------------------------------------
def _powershell_pfad() -> str:
    """PowerShell mit ABSOLUTEM Pfad.

    Ein blosser Name haengt am PATH - und der ist unter der Aufgabenplanung ein
    anderer als in einer Sitzung. Am 21.09.2026 lief der Dauerlauf nach einem
    Neustart ohne Fehlermeldung weiter, raeumte aber nichts auf: die
    Prozessabfrage kam leer zurueck, und "leer" heisst in _prozesse()
    ausdruecklich "nicht aufraeumen, statt zu raten". Mit festem Pfad ist die
    Abfrage ueberall dieselbe.
    """
    fest = os.path.join(os.environ.get("SystemRoot", "C:" + os.sep + "Windows"),
                        "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    return fest if os.path.exists(fest) else "powershell"


def _prozesse() -> list[dict]:
    """Alle laufenden Prozesse mit Kommandozeile.

    PowerShell statt wmic: wmic ist auf Windows 11 abgekuendigt und liefert auf
    diesem Rechner keine Kommandozeilen mehr. Rueckgabe: Liste von dicts mit
    ProcessId, ParentProcessId, CreationDate, CommandLine - leer, wenn die
    Abfrage scheitert (dann raeumt der Treiber nicht auf, statt zu raten).
    """
    if os.name != "nt":
        return []
    # UTF-8 auf BEIDEN Seiten: Windows PowerShell 5 schreibt umgeleitet in der
    # OEM-Codepage (cp850), Python las cp1252 und brach am ersten Umlaut einer
    # Kommandozeile ab (Byte 0x81) - stdout None, Liste leer, Aufraeumen
    # uebersprungen ("Prozessliste nicht lesbar", gefunden 11.10.2026).
    skript = ("[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
              "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,"
              "CreationDate,Name,CommandLine | ConvertTo-Json -Compress")
    try:
        p = subprocess.run([_powershell_pfad(), "-NoProfile", "-NonInteractive",
                            "-Command", skript],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except Exception:                                          # noqa: BLE001
        return []
    roh = (p.stdout or "").strip()
    if not roh:
        return []
    try:
        daten = json.loads(roh)
    except ValueError:
        return []
    if isinstance(daten, dict):
        daten = [daten]
    return daten


def _ist_agentenprozess(eintrag: dict) -> bool:
    """Ist das ein MoonDev-Agentenprozess?

    ZWEI Bedingungen: Kennung in der Kommandozeile UND ein echter Interpreter.
    Die Kennung allein traf am 21.09.2026 auch eine PowerShell-Abfrage, die den
    Text enthielt - und ein Aufraeumer, der die eigene Suche fuer ein Kind haelt,
    BEENDET sie (taskkill /T). Deshalb zusaetzlich der Prozessname.
    """
    if (eintrag.get("Name") or "").lower() not in ("python.exe", "pythonw.exe"):
        return False
    cmd = eintrag.get("CommandLine") or ""
    return any(k in cmd for k in KENNUNG_AGENTEN)


def _alter_sekunden(eintrag: dict) -> float:
    """Alter des Prozesses in Sekunden; sehr gross, wenn unlesbar."""
    roh = str(eintrag.get("CreationDate") or "")
    # PowerShell liefert "/Date(1789979174000)/" ueber JSON, CIM direkt ISO.
    ziffern = "".join(c for c in roh if c.isdigit())
    if not ziffern:
        return 1e9
    try:
        stamp = datetime.fromtimestamp(int(ziffern) / 1000.0)
    except (ValueError, OSError, OverflowError):
        return 1e9
    return max(0.0, (datetime.now() - stamp).total_seconds())


def _kill_baum(pid: int) -> bool:
    """Prozess UND seine Nachfahren beenden (Windows: taskkill /T)."""
    try:
        if os.name == "nt":
            return subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)],
                                  capture_output=True, timeout=30,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0).returncode == 0
        os.kill(pid, 15)
        return True
    except Exception:                                          # noqa: BLE001
        return False


def _jetzt() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class MoonDevDauerlauf:
    """Faehrt die MoonDev-Agenten als langlebige Kindprozesse."""

    def __init__(self, risiko: str = "basis", stumm: bool = True,
                 trocken: bool = False) -> None:
        self.risiko = risiko
        self.stumm = stumm
        # TROCKEN (nur fuer Tests, gemessen 23.09.2026): eine Testsuite, die den
        # echten Treiber baut und zyklus() ruft, hat in den LAUFENDEN Betrieb
        # gegriffen - sie hat die lebenden Agenten als Waisen beendet (8 PIDs),
        # die Logdatei des Laufs gedreht und ihre Startzeilen ins Treiberlog
        # geschrieben. Im Trockenmodus entfaellt das Aufraeumen, Logs landen in
        # einem Temp-Ordner und es wird nicht ins Treiberlog geschrieben.
        self.trocken = trocken
        self._logbasis = Path(tempfile.mkdtemp(prefix="moondev-test-")) if trocken else HIER
        self.kinder: dict[str, subprocess.Popen] = {}
        self.letzter_neustart: dict[str, float] = {}
        self.ag_log: dict[str, Path] = {}
        self.protokoll: list[str] = []

    def protokolliere(self, zeile: str) -> None:
        marke = f"[{_jetzt()}] {zeile}"
        self.protokoll.append(marke)
        print(marke, flush=True)
        if self.trocken:
            return
        # Datei-Log: unter der Aufgabenplanung gibt es keine Konsole, die
        # print() abfaengt - ohne Datei ist ein Fehlstart nicht nachzuvoll-
        # ziehen (gemessen 17.09.2026: Task lief laut Scheduler, aber kein
        # Kindprozess kam hoch, und ohne Log war das nicht zu klaeren).
        try:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(marke + "\n")
        except OSError:
            pass

    # -- Kindprozesse -------------------------------------------------------
    def _starte(self, name: str, beschreibung: str) -> None:
        if name in self.kinder and self.kinder[name].poll() is None:
            return
        eintrag = AGENTEN[name]
        umgebung = dict(os.environ)
        umgebung["MAXHIRN_ROUTINE"] = MAXHIRN_ROUTINE
        umgebung["HANDEL_RISIKO"] = self.risiko
        # Haus-Ordner fuer CSV-Export der Agenten (Emppfehlungen/Urteile).
        umgebung["MOONDEV_HAUS_DIR"] = str(HIER)
        # stdout geht in eine Datei - ohne das Flag puffert Python 8 KB, und ein
        # wortkarger Agent (kraken) schreibt stundenlang keine Zeile ins Log.
        umgebung["PYTHONUNBUFFERED"] = "1"
        # PFLICHT: die Agenten drucken Emoji (print_fancy). Ueber eine PIPE
        # (subprocess.PIPE, kein echtes Konsolenfenster) faellt Python ohne
        # dieses Flag auf die Windows-ANSI-Codepage zurueck und stirbt beim
        # ersten Emoji mit UnicodeEncodeError - dieselbe Falle wie beim
        # PowerShell-Wrapper (moondev-agent.ps1), hier am Treiber selbst.
        umgebung["PYTHONIOENCODING"] = "utf-8"
        wege = _repo_env()
        umgebung.update(wege)
        # VORGABE fuer jeden Agenten mit OpenAI-/DeepSeek-Zweig: die lokale
        # Bruecke. Einen bezahlten DEEPSEEK_KEY gibt es im Haus nicht; ohne
        # diese Zeilen faellt der Zweig mit 'not found in environment
        # variables' um. Der Nous-Weg ueberschreibt beides danach.
        umgebung["DEEPSEEK_KEY"] = "lokal-ollama"
        umgebung["DEEPSEEK_BASE_URL"] = BRUECKE_BASIS
        # Welcher Modellweg? Steht danach im Log neben der PID - ohne diese
        # Zeile sieht ein 404 (Modell fehlt) wie ein gesunder Lauf aus.
        weg = _weg_fuer(name, umgebung, wege)
        # Pro Agent eine angehaengte Log-Datei. subprocess.PIPE wuerde die
        # Agenten-Ausgabe (Analyse + Empfehlungen) verlieren: der Driver liest
        # PIPE nie (nur stderr beim Absturz). Datei auch fuer den Absturz-Tail.
        ag_log = self._logbasis / ("moondev_%s.log" % name)
        self.ag_log[name] = ag_log
        # Gedreht wird HIER, nicht im Betrieb: jetzt ist der alte Baum beendet
        # und die Datei frei. Im Betrieb haelt der Agent sie offen und Windows
        # verweigert jedes Umbenennen.
        gedreht = _log_drehen(ag_log)
        if gedreht:
            self.protokolliere("Log: " + gedreht)
        try:
            with open(ag_log, "a", encoding="utf-8") as _:
                pass
            ag_datei = open(ag_log, "a", encoding="utf-8", errors="replace")
        except Exception as e:                                    # noqa: BLE001
            self.protokolliere(f"{name}: Log-Datei nicht oeffbar: {e}")
            ag_datei = subprocess.DEVNULL
        try:
            kind = subprocess.Popen(
                eintrag["cmd"], cwd=eintrag["cwd"],
                env=umgebung,
                stdout=ag_datei, stderr=subprocess.STDOUT,
                text=True, errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as e:                                    # noqa: BLE001
            self.protokolliere(f"{name}: Start fehlgeschlagen: {e}")
            return
        self.kinder[name] = kind
        self.letzter_neustart[name] = time.monotonic()
        self.protokolliere(f"{name}: gestartet (PID {kind.pid}) - {weg}")

    def _stoppe(self, name: str) -> None:
        kind = self.kinder.pop(name, None)
        if kind is None or kind.poll() is not None:
            return
        # GANZEN Baum beenden: das Startprogramm allein zu beenden liess den
        # echten Interpreter als Waise stehen (Leak vom 21.09.2026).
        _kill_baum(kind.pid)
        try:
            kind.wait(timeout=5)
        except subprocess.TimeoutExpired:
            kind.kill()
        self.protokolliere(f"{name}: gestoppt")

    # -- Aufraeumen verwaister Agentenprozesse ------------------------------
    def _baum(self, wurzel: int, alle: list[dict]) -> set:
        """Wurzel-PID und alle Nachfahren (ueber ParentProcessId verkettet)."""
        kinder: dict = {}
        for e in alle:
            kinder.setdefault(e.get("ParentProcessId"), []).append(e.get("ProcessId"))
        gesehen, stapel = set(), [wurzel]
        while stapel:
            pid = stapel.pop()
            if pid in gesehen or pid is None:
                continue
            gesehen.add(pid)
            stapel.extend(kinder.get(pid, []))
        return gesehen

    def fremde_agenten(self, alle: list[dict] | None = None) -> list[dict]:
        """Agentenprozesse, die zu KEINEM lebenden Kind des Treibers gehoeren.

        Sie sind die Waisen aus einem abgestuerzten oder ersetzten Kind. Frische
        Prozesse (juenger als SCHONFRIST_S) bleiben unangetastet - ein Enkel,
        der gerade startet, darf nicht im eigenen Start erschlagen werden.

        ZUSAEZTZICH (T-262): Prozesse, die sich im gemeinsamen Registrierungs-
        ordner (moondev_reg.py) eingetragen haben, werden NICHT als fremd
        behandelt - auch wenn sie nicht zu unseren Kindern gehoeren. Das ist
        z.B. der Fall fuer Agenten, die von der GUI (moongui.py) gestartet
        wurden: die GUI setzt sich selbst in den Ordner ein, und der Treiber
        lässt sie in Ruhe.
        """
        alle = _prozesse() if alle is None else alle
        behalten: set = set()
        for kind in self.kinder.values():
            if kind.poll() is None:
                behalten |= self._baum(kind.pid, alle)
        # (T-262) Zusätzlich: registrierte PIDs aus dem gemeinsamen Ordner
        try:
            import moondev_reg
            behalten |= moondev_reg.alle_registrierte_pids()
        except Exception:                                              # noqa: BLE001
            pass  # moondev_reg nicht verfügbar (z.B. Test) – ohne Registrierung schützen
        ich = os.getpid()
        raus = []
        for e in alle:
            if not _ist_agentenprozess(e):
                continue
            pid = e.get("ProcessId")
            if pid is None or pid == ich or pid in behalten:
                continue
            if _alter_sekunden(e) < SCHONFRIST_S:
                continue
            raus.append(e)
        return raus

    def aufraeumen(self, alle: list[dict] | None = None) -> int:
        """Waise beenden und die Zahl der Aufraeumten zurueckgeben (Beleg).

        NUR der laufende Treiber darf das aufrufen: eine frische Instanz kennt
        die Kinder des laufenden Treibers nicht und hielte sie fuer Waisen
        (ein Agent laeuft legitim stundenlang). Im Zyklus ist das unkritisch -
        dort sind `self.kinder` die Wahrheit; nach einem Neustart schuetzt die
        Schonfrist die frisch gestarteten Kinder.
        """
        fremde = self.fremde_agenten(alle)
        for e in fremde:
            _kill_baum(e["ProcessId"])
        if fremde:
            self.protokolliere(
                "Aufraeumen: %d verwaiste Agentenprozess(e) beendet (PIDs %s)"
                % (len(fremde), ", ".join(str(e["ProcessId"]) for e in fremde[:8])))
        return len(fremde)

    def _ist_tot(self, name: str) -> bool:
        kind = self.kinder.get(name)
        return kind is None or kind.poll() is not None

    # -- Zyklus -------------------------------------------------------------
    def zyklus(self) -> None:
        # Die Bruecke VOR die Agenten: sie traegt den lokalen
        # Sprachmodell-Weg. Eine leere Meldung heisst: sie lief schon.
        if not self.trocken:
            meldung = _bruecke_sicherstellen()
            if meldung:
                self.protokolliere(meldung)
        # ERST aufraeumen, dann starten: sonst lebt bei jedem Neustart die Waise
        # des vorigen Laufs weiter (Leak vom 21.09.2026).
        # EINE Abfrage je Zyklus: leer heisst "nicht aufraeumen, statt zu raten" -
        # das muss laut sein, sonst bleibt ein liegengebliebener Waise unbemerkt.
        alle = _prozesse()
        if not alle:
            self.protokolliere("WARNUNG: Prozessliste nicht lesbar - Aufraeumen "
                               "uebersprungen (verwaiste Agenten bleiben liegen)")
        if self.trocken:
            # Ein Test darf die Agenten des ECHTEN Laufs nicht als Waisen
            # beenden (das ist am 23.09.2026 passiert: 8 PIDs).
            self.protokolliere("Trockenlauf: Aufraeumen fremder Agenten uebersprungen")
        else:
            self.aufraeumen(alle)
        for name, eintrag in AGENTEN.items():
            if self._ist_tot(name):
                kind = self.kinder.get(name)
                if kind is not None:
                    # Die Wurzel dieses Agenten ist tot. Ihre Nachfahren koennen
                    # weiterleben (venv-Startprogramm + Interpreter) - sie sind
                    # die Quelle des Leaks. Vor dem Neustart den Baum beenden,
                    # sonst laufen mit jedem Zyklus zwei Agenten desselben Namens.
                    _kill_baum(kind.pid)
                    code = kind.poll()
                    if code not in (None, 0):
                        try:
                            fehler = ""
                            alog = self.ag_log.get(name) if hasattr(self, "ag_log") else None
                            if alog is not None and alog.exists():
                                fehler = alog.read_text(
                                    encoding="utf-8", errors="replace")[-1500:]
                        except Exception:                          # noqa: BLE001
                            fehler = ""
                        if fehler.strip():
                            self.protokolliere(f"{name}: Absturz (Code {code}): {fehler.strip()}")
                if name in self.letzter_neustart:
                    seit = time.monotonic() - self.letzter_neustart[name]
                    if seit < PAUSE_NEUSTART:
                        continue
                self._starte(name, eintrag.get("beschreibung", ""))

    def lauf(self, dauer: float | None = None) -> None:
        """Endlos laufen; optional nach `dauer` Sekunden beenden (Tests)."""
        self.protokolliere(
            f"MoonDev-Dauerlauf startet ({len(AGENTEN)} Agenten, "
            f"Risiko={self.risiko}, stumm={self.stumm})")
        start = time.monotonic()
        while True:
            self.zyklus()
            if dauer is not None and time.monotonic() - start >= dauer:
                break
            time.sleep(PRUEF_ALLE)
        for name in list(self.kinder):
            self._stoppe(name)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    risiko = "basis"
    if "--risiko" in sys.argv:
        i = sys.argv.index("--risiko") + 1
        if i < len(sys.argv):
            risiko = sys.argv[i]
    stumm = "--stumm" in sys.argv
    dauer = None
    if "--dauer" in sys.argv:
        i = sys.argv.index("--dauer") + 1
        if i < len(sys.argv):
            try:
                dauer = float(sys.argv[i])
            except ValueError:
                dauer = None
    lauf = MoonDevDauerlauf(risiko=risiko, stumm=stumm)
    lauf.lauf(dauer=dauer)

if __name__ == "__main__":
    main()