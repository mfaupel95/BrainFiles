"""Nautilus-Reiter des Leitstands.

Betet den OKX-DEMO-Node von `nautilus/nautilus_gui.py` als Reiter ein. Das
Modul liegt in einem eigenen Repo (Agenten/Handel/nautilus/, siehe .gitignore)
und braucht `nautilus_trader` - der Leitstand laeuft im Handel-.venv, in dem
es seit dem 04.10.2026 ebenfalls installiert ist.

Fehlt nautilus_trader (frisches venv, fremde Maschine), darf der LEITSTAND
deshalb nicht sterben: der Reiter baut dann eine erklärende Zeile statt einer
Traceback. Genau das ist der Grund fuer diese Datei - `leitstand.py` selbst
laedt Nautilus nicht, sonst waere ein fehlendes Rad ein toter Leitstand.

Schreibt nichts, startet nichts von sich aus: der Node laeuft erst, wenn Max
"Start DEMO-Node" anklickt. Der Reiter hat keinen Taktbedarf (NautilusFrame
pollt seine Queue selbst alle 120 ms).

Ausbau 11.10.2026: Drei Tabs - OKX-DEMO (GUI), Kraken Spot, Kraken Futures.
Die Kraken-Nodes laufen als Kindprozesse (wie im Prozesse-Reiter), nicht als
eingebettete Frames. Sie brauchen keine GUI: Start/Stop + Status reicht.
"""

import os
import subprocess
import sys
from pathlib import Path
from tkinter import ttk

import leitstand_stil as stil

NAUTILUS = Path(__file__).resolve().parent / "nautilus"
KRAKEN_NODE = Path(__file__).resolve().parent / "nautilus_kraken" / "run_kraken_paper_node.py"
NAUTILUS_PY = Path(__file__).resolve().parent / "nautilus" / ".venv" / "Scripts" / "python.exe"
_CREATE_NEW_CONSOLE = 0x00000010


def nautilus_gui_laden():
    """nautilus_gui als Modul holen. Gibt (modul, grund) zurueck.

    Der Pfad-Eintrag ist noetig: `run_okx_paper_node` liegt als flache Datei
    im Ordner und ist kein Paket (`nautilus/__init__.py` gibt es nicht).
    """
    pfad = str(NAUTILUS)
    if pfad not in sys.path:
        sys.path.insert(0, pfad)
    try:
        import nautilus_gui
    except ImportError as e:
        return None, "nautilus_trader fehlt: %s" % e
    return nautilus_gui, ""


class _KrakenNodeFrame(ttk.Frame):
    """Start/Stop-UI fuer einen Kraken-Paper-Node (Spot oder Futures).

    Read-only: keine Order, nur Quotes. Laueft als Kindprozess mit
    CREATE_NEW_CONSOLE - ueberlebt den Leitstand.
    """

    def __init__(self, eltern, produkt, symbol):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.produkt = produkt
        self.symbol = symbol
        self._prozess = None
        self._pid_pfad = Path(__file__).resolve().parent / ("nautilus_kraken_node_%s.pid" % produkt)

        # Kopf
        kopf = ttk.Frame(self)
        kopf.pack(fill="x", pady=(0, 8))
        ttk.Label(kopf, text="Kraken %s (%s)" % (produkt.upper(), symbol),
                  style="Titel.TLabel", anchor="w").pack(side="left")
        self.w_status = ttk.Label(kopf, text="", width=20, anchor="w")
        self.w_status.pack(side="left", padx=(12, 0))

        # Buttons
        ctrls = ttk.Frame(self)
        ctrls.pack(fill="x", pady=(0, 8))
        self.btn_start = ttk.Button(ctrls, text="\u25b6 Start", command=self._starten, width=10)
        self.btn_start.pack(side="left", padx=(0, 6))
        self.btn_stop = ttk.Button(ctrls, text="\u25a0 Stop", command=self._stoppen, width=10)
        self.btn_stop.pack(side="left")

        # Hinweis
        ttk.Label(self, text="Read-only: Quotes/Papier, keine Order. Keine API-Keys n\u00f6tig.",
                  foreground="#555", anchor="w").pack(fill="x", pady=(0, 6))

        # Log
        log_frame = ttk.LabelFrame(self, text="Log", padding=4)
        log_frame.pack(fill="both", expand=True)
        from tkinter import scrolledtext
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, font=("Consolas", 9),
                                                  wrap="none", state="disabled")
        self.log_text.pack(fill="both", expand=True)

        self._refresh()

    def _pid(self):
        try:
            return int(self._pid_pfad.read_text(encoding="ascii").strip().split()[0])
        except (OSError, ValueError, IndexError):
            return None

    def _log(self, msg):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", "[%s] %s\n" % (ts, msg))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _refresh(self):
        laeuft = self._laeuft()
        self.w_status.config(text="\u25cf l\u00e4uft" if laeuft else "\u25cb gestoppt")
        self.btn_start.configure(state="disabled" if laeuft else "normal")
        self.btn_stop.configure(state="normal" if laeuft else "disabled")

    def _laeuft(self):
        if self._prozess is not None and self._prozess.poll() is None:
            return True
        pid = self._pid()
        if pid is None:
            return False
        try:
            import psutil
            proc = psutil.Process(pid)
            return (proc.is_running()
                    and proc.environ().get("KRAKEN_PRODUKT") == self.produkt)
        except Exception:
            return False

    def _starten(self):
        if self._laeuft():
            return
        env = os.environ.copy()
        env["KRAKEN_PRODUKT"] = self.produkt
        env["KRAKEN_SYMBOL"] = self.symbol
        env["NAUTILUS_MIT_ORDER"] = ""
        for key in ("KRAKEN_SPOT_API_KEY", "KRAKEN_SPOT_API_SECRET",
                     "KRAKEN_FUTURES_DEMO_API_KEY", "KRAKEN_FUTURES_DEMO_API_SECRET"):
            env.pop(key, None)
        self._log("Starte Kraken %s-Node (%s) ..." % (self.produkt, self.symbol))
        try:
            self._prozess = subprocess.Popen(
                [str(NAUTILUS_PY), str(KRAKEN_NODE)],
                cwd=str(KRAKEN_NODE.parent), env=env,
                creationflags=_CREATE_NEW_CONSOLE, close_fds=True,
            )
            self._pid_pfad.write_text("%d\n" % self._prozess.pid, encoding="ascii")
            self._log("PID %d gestartet." % self._prozess.pid)
        except Exception as e:
            self._log("FEHLER: %s" % e)
        self._refresh()

    def _stoppen(self):
        if not self._laeuft():
            return
        pid = self._prozess.pid if self._prozess is not None else self._pid()
        self._log("Stoppe PID %s ..." % pid)
        try:
            import psutil
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                import subprocess as sp
                sp.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            except Exception:
                pass
        self._pid_pfad.unlink(missing_ok=True)
        self._prozess = None
        self._log("Gestoppt.")
        self._refresh()


class NautilusReiter(ttk.Frame):
    """Reiter mit dem Nautilus-Inhalt - oder mit der Begruendung, warum nicht.

    Ohne installiertes nautilus_trader steht hier ein lesbarer Text statt
    eines Absturzes: ein Werkzeug darf den Rahmen nicht mitnehmen.

    Drei Tabs: OKX-DEMO (GUI), Kraken Spot, Kraken Futures.
    """

    def __init__(self, eltern, leitstand):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.ls = leitstand
        self._grund = ""
        self._tabs = {}
        self._kraken_frames = {}

        modul, grund = nautilus_gui_laden()
        if modul is None:
            self._grund = grund
            self._zeige_grund(grund)
        else:
            self._baue_tabs(modul)

    def _zeige_grund(self, grund):
        ttk.Label(self, text="Nautilus nicht verf\u00fcgbar", style="Titel.TLabel",
                  anchor="w").pack(fill="x")
        ttk.Label(self, text=grund or "unbekannter Grund", anchor="w",
                  wraplength=520, justify="left").pack(fill="x", pady=(6, 0))
        ttk.Label(self, text="N\u00f6tig: pip install nautilus_trader==1.231.0 "
                  "in Agenten/Handel/.venv", anchor="w",
                  wraplength=520, justify="left").pack(fill="x", pady=(6, 0))

    def _baue_tabs(self, modul):
        buch = ttk.Notebook(self)
        buch.pack(fill="both", expand=True)

        # Tab 1: OKX-DEMO (GUI)
        okx_frame = ttk.Frame(buch, padding=stil.ABSTAND_GROSS)
        buch.add(okx_frame, text="OKX DEMO")
        self._tabs["okx"] = okx_frame
        nautilus_frame = modul.NautilusFrame(okx_frame)
        nautilus_frame.pack(fill="both", expand=True)
        self._okx_frame = nautilus_frame

        # Tab 2: Kraken Spot
        spot_frame = _KrakenNodeFrame(buch, "spot", "BTC/EUR")
        buch.add(spot_frame, text="Kraken Spot")
        self._kraken_frames["spot"] = spot_frame

        # Tab 3: Kraken Futures
        futures_frame = _KrakenNodeFrame(buch, "futures", "PF_SOLUSD")
        buch.add(futures_frame, text="Kraken Futures")
        self._kraken_frames["futures"] = futures_frame

    # --- Reiter-Schnittstelle --------------------------------------------
    def refresh(self):
        # NautilusFrame pollt seine Queue selbst (120 ms). Ein Refresh hier
        # wuerde nur den Zustand erneut lesen, ohne etwas zu bewirken.
        pass

    def titel_zusatz(self):
        if self._grund:
            return " (fehlt)"
        if hasattr(self, "_okx_frame"):
            laeuft = getattr(self._okx_frame, "_running", False)
            if laeuft:
                return " \u25cf"
        for f in self._kraken_frames.values():
            if f._laeuft():
                return " \u25cf"
        return ""

    def status(self):
        if self._grund:
            return "Nautilus: %s" % self._grund
        teile = []
        if hasattr(self, "_okx_frame") and getattr(self, "_okx_frame", "_running", False):
            teile.append("OKX DEMO l\u00e4uft")
        for name, f in self._kraken_frames.items():
            if f._laeuft():
                teile.append("Kraken %s l\u00e4uft" % name)
        if teile:
            return "Nautilus: " + ", ".join(teile)
        return ""

    def abbrechbar(self):
        """Solange ein Node laeuft, nicht ohne Rueckfrage schliessen."""
        if hasattr(self, "_okx_frame") and getattr(self, "_okx_frame", "_running", False):
            return False
        for f in self._kraken_frames.values():
            if f._laeuft():
                return False
        return True
