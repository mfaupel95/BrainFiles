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

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent                      # Agenten/Handel
REPO = (HIER / ".." / ".." / "Werkstatt" / "Repos" / "moon-dev-ai-agents").resolve()

# WICHTIG: Die Agenten brauchen Pakete aus dem REPO-EIGENEN venv (requests,
# pandas, openai ...) - sys.executable ist hier der AUFRUFER-Interpreter
# (z.B. scanner/.venv, wenn der Haus-Dauerlauf startet) und hat diese Pakete
# NICHT. Fest auf den Repo-Interpreter zeigen (gemessen 17.09.2026:
# ModuleNotFoundError: requests, solange sys.executable verwendet wurde).
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
        # PFLICHT: die Agenten drucken Emoji (print_fancy). Ueber eine PIPE
        # (subprocess.PIPE, kein echtes Konsolenfenster) faellt Python ohne
        # dieses Flag auf die Windows-ANSI-Codepage zurueck und stirbt beim
        # ersten Emoji mit UnicodeEncodeError - dieselbe Falle wie beim
        # PowerShell-Wrapper (moondev-agent.ps1), hier am Treiber selbst.
        umgebung["PYTHONIOENCODING"] = "utf-8"
        umgebung.update(_repo_env())
        try:
            kind = subprocess.Popen(
                eintrag["cmd"], cwd=eintrag["cwd"],
                env=umgebung,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, errors="replace",
            )
        except Exception as e:                                    # noqa: BLE001
            self.protokolliere(f"{name}: Start fehlgeschlagen: {e}")
            return
        self.kinder[name] = kind
        self.letzter_neustart[name] = time.monotonic()
        self.protokolliere(f"{name}: gestartet (PID {kind.pid}) - {beschreibung}")

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
                            fehler = (kind.stderr.read() or "")[-1500:]
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