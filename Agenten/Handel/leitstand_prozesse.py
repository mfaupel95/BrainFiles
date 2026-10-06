"""Prozessreiter des Leitstands - omnitrade-Lauf und Python-Dauerlauf.

Startet und stoppt beide als eigenstaendige OS-Prozesse: sie laufen weiter,
auch wenn der Leitstand geschlossen wird (CREATE_NEW_CONSOLE).

Schreibt nicht in wachen.json und handelt nie live - der Prozess selbst
entscheidet das (kein offenes Freigabefenster = Papierhandel).
"""

import os
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox, ttk

import handelszentrale as hz
import leitstand_stil as stil

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent          # BrainFiles/
_PY = HIER / "scanner" / ".venv" / "Scripts" / "python.exe"
_CREATE_NEW_CONSOLE = 0x00000010


# ---------------------------------------------------------------------------
# Prozessbeschreibungen
# ---------------------------------------------------------------------------

class _OmnitradetLauf:
    """omnitrade-cli.exe live (Rust-Handelsagent, OKX DEMO)."""
    name = "omnitrade live"

    def laeuft(self):
        try:
            _pfad = str(HIER)
            if _pfad not in sys.path:
                sys.path.insert(0, _pfad)
            import omnitrade_lauf
            return omnitrade_lauf.beurteile()["laeuft"]
        except Exception:
            return False

    def starten(self):
        subprocess.Popen(
            ["cmd.exe", "/c", str(WURZEL / "omnitrade.cmd"), "start"],
            creationflags=_CREATE_NEW_CONSOLE,
            close_fds=True,
        )

    def stoppen(self):
        try:
            _pfad = str(HIER)
            if _pfad not in sys.path:
                sys.path.insert(0, _pfad)
            import omnitrade_lauf
            erg = omnitrade_lauf.beurteile()
            pid = erg.get("pid")
            if pid:
                subprocess.run(
                    [os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                  "System32", "taskkill.exe"),
                     "/F", "/PID", str(pid)],
                    capture_output=True,
                )
        except Exception:
            pass


class _PythonDauerlauf:
    """Python 24/7-Bot (dauerlauf.py) - analysiert, meldest, haelt Freigaben."""
    name = "Python-Dauerlauf"
    _pid_pfad = str(HIER / "dauerlauf.pid")

    def _pid(self):
        try:
            with open(self._pid_pfad, encoding="ascii") as f:
                return int(f.read().strip().split()[0])
        except Exception:
            return None

    def laeuft(self):
        pid = self._pid()
        return pid is not None and hz.prozess_lebt(pid)

    def starten(self):
        subprocess.Popen(
            [str(_PY), str(HIER / "dauerlauf.py")],
            creationflags=_CREATE_NEW_CONSOLE,
            cwd=str(HIER),
            close_fds=True,
        )

    def stoppen(self):
        pid = self._pid()
        if pid:
            subprocess.run(
                [os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                              "System32", "taskkill.exe"),
                 "/F", "/PID", str(pid)],
                capture_output=True,
            )


PROZESSE = [_OmnitradetLauf(), _PythonDauerlauf()]


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class _ProzessZeile(ttk.Frame):
    """Statusanzeige + Start/Stopp fuer einen Prozess."""

    def __init__(self, eltern, prozess):
        super().__init__(eltern)
        self._p = prozess
        ttk.Label(self, text=prozess.name, width=22, anchor="w").pack(side="left")
        self.w_zustand = ttk.Label(self, text="", width=22, anchor="w")
        self.w_zustand.pack(side="left", padx=(0, 12))
        self.w_start = ttk.Button(self, text="Start", command=self._starten, width=7)
        self.w_start.pack(side="left", padx=(0, 4))
        self.w_stopp = ttk.Button(self, text="Stopp", command=self._stoppen, width=7)
        self.w_stopp.pack(side="left")
        self.refresh()

    def refresh(self):
        laeuft = self._p.laeuft()
        self.w_zustand.config(text="\u25cf l\u00e4uft" if laeuft else "\u25cb gestoppt")
        self.w_start.config(state="disabled" if laeuft else "normal")
        self.w_stopp.config(state="normal" if laeuft else "disabled")

    def _starten(self):
        if self._p.laeuft():
            return
        self._p.starten()
        self.after(2000, self.refresh)

    def _stoppen(self):
        if not self._p.laeuft():
            return
        if not messagebox.askyesno(
            "Prozess beenden",
            "%s wirklich beenden?" % self._p.name,
        ):
            return
        self._p.stoppen()
        self.after(2000, self.refresh)


class ProzessReiter(ttk.Frame):
    """Reiter: Start und Stopp fuer omnitrade und Python-Dauerlauf."""

    def __init__(self, eltern, leitstand):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.ls = leitstand
        ttk.Label(self, text="Prozesse", style="Titel.TLabel",
                  anchor="w").pack(fill="x", pady=(0, 12))
        self._zeilen = []
        for p in PROZESSE:
            z = _ProzessZeile(self, p)
            z.pack(fill="x", pady=4)
            self._zeilen.append(z)

    def refresh(self):
        for z in self._zeilen:
            z.refresh()

    def titel_zusatz(self):
        return " \u25cf" if any(z._p.laeuft() for z in self._zeilen) else ""

    def status(self):
        laufende = [z._p.name for z in self._zeilen if z._p.laeuft()]
        return ("L\u00e4uft: " + ", ".join(laufende)) if laufende else ""

    def abbrechbar(self):
        # Prozesse laufen weiter, auch wenn der Leitstand schliesst.
        return True
