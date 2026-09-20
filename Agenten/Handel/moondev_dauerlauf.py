"""
MoonDev-Agenten an den Haus-Dauerlauf anbinden (17.09.2026, Max).

Was das ist
-----------
Die geklonten Moon-Dev-Agenten (Werkstatt/Repos/moon-dev-ai-agents/src/agents)
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
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent                      # Agenten/Handel
REPO = (HIER / ".." / ".." / "Werkstatt" / "Repos" / "moon-dev-ai-agents").resolve()

# WICHTIG: Die Agenten brauchen Pakete aus dem REPO-EIGENEN venv (requests,
# pandas, openai ...) - sys.executable ist hier der AUFRUFER-Interpreter
# (z.B. scanner/.venv, wenn der Haus-Dauerlauf startet) und hat diese Pakete
# NICHT. Fest auf den Repo-Interpreter zeigen (gemessen 17.09.2026:
# ModuleNotFoundError: requests, solange sys.executable verwendet wurde).
# pythonw statt python: die Kinder laufen als Konsolen-Fensterprozesse und
# poppen bei jedem Start fuer den Nutzer auf (gemessen 20.09.2026: 27
# verwaiste Konsolenfenster nach einem Treiber-Absturz). pythonw zeigt kein
# Fenster; die Ausgabe laeuft weiter in die ag_log-Dateien, nichts geht verloren.
REPO_PYTHON = str(REPO / ".venv" / "Scripts" / "pythonw.exe")

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
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"
LOKAL_STANDARD = "qwen35-8k:latest"          # im Store vorhanden (Hausstandard)
LOKAL_BASIS = "http://127.0.0.1:11434/v1"

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
    "kraken": {
        "cmd": [REPO_PYTHON, str(REPO / "src" / "agents" / "kraken_agent.py")],
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

PAUSE_NEUSTART = 15          # s zwischen Absturz und Neustart
PRUEF_ALLE = 60              # s: Kinder alle 60 s pruefen
MAXHIRN_ROUTINE = "1"        # keiner fragt nach einem Fenster

LOG = HIER / "moondev_dauerlauf.log"

def _jetzt() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class MoonDevDauerlauf:
    """Faehrt die MoonDev-Agenten als langlebige Kindprozesse."""

    def __init__(self, risiko: str = "basis", stumm: bool = True) -> None:
        self.risiko = risiko
        self.stumm = stumm
        self.kinder: dict[str, subprocess.Popen] = {}
        self.letzter_neustart: dict[str, float] = {}
        self.ag_log: dict[str, Path] = {}
        self.protokoll: list[str] = []

    def protokolliere(self, zeile: str) -> None:
        marke = f"[{_jetzt()}] {zeile}"
        self.protokoll.append(marke)
        print(marke, flush=True)
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
        # PFLICHT: die Agenten drucken Emoji (print_fancy). Ueber eine PIPE
        # (subprocess.PIPE, kein echtes Konsolenfenster) faellt Python ohne
        # dieses Flag auf die Windows-ANSI-Codepage zurueck und stirbt beim
        # ersten Emoji mit UnicodeEncodeError - dieselbe Falle wie beim
        # PowerShell-Wrapper (moondev-agent.ps1), hier am Treiber selbst.
        umgebung["PYTHONIOENCODING"] = "utf-8"
        wege = _repo_env()
        umgebung.update(wege)
        # Welcher Modellweg? Steht danach im Log neben der PID - ohne diese
        # Zeile sieht ein 404 (Modell fehlt) wie ein gesunder Lauf aus.
        weg = _weg_fuer(name, umgebung, wege)
        # Pro Agent eine angehaengte Log-Datei. subprocess.PIPE wuerde die
        # Agenten-Ausgabe (Analyse + Empfehlungen) verlieren: der Driver liest
        # PIPE nie (nur stderr beim Absturz). Datei auch fuer den Absturz-Tail.
        ag_log = HIER / ("moondev_%s.log" % name)
        self.ag_log[name] = ag_log
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
        kind.terminate()
        try:
            kind.wait(timeout=5)
        except subprocess.TimeoutExpired:
            kind.kill()
        self.protokolliere(f"{name}: gestoppt")

    def _ist_tot(self, name: str) -> bool:
        kind = self.kinder.get(name)
        return kind is None or kind.poll() is not None

    # -- Zyklus -------------------------------------------------------------
    def zyklus(self) -> None:
        for name, eintrag in AGENTEN.items():
            if self._ist_tot(name):
                kind = self.kinder.get(name)
                if kind is not None:
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