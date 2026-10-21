"""Prozessreiter des Leitstands - omnitrade-Lauf und Python-Dauerlauf.

Startet und stoppt beide als eigenstaendige OS-Prozesse: sie laufen weiter,
auch wenn der Leitstand geschlossen wird (CREATE_NEW_CONSOLE).

Schreibt nicht in wachen.json und handelt nie live - der Prozess selbst
entscheidet das (kein offenes Freigabefenster = Papierhandel).
"""

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from tkinter import messagebox, ttk
import tkinter as tk
import psutil

import dauerlauf
import handelszentrale as hz
import leitstand_stil as stil

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent          # BrainFiles/
_PY = HIER / "scanner" / ".venv" / "Scripts" / "python.exe"
_NAUTILUS_PY = HIER / "nautilus" / ".venv" / "Scripts" / "python.exe"
_CREATE_NEW_CONSOLE = 0x00000010
_KRAKEN_NODE = HIER / "nautilus_kraken" / "run_kraken_paper_node.py"
sys.path.insert(0, str(HIER / "nautilus_kraken"))
from papierbuch import lese_stand as lese_papierstand  # noqa: E402


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


def _produkt_aus_env(env):
    """Wie run_kraken_paper_node.produkt_typ(): ohne Angabe gilt spot."""
    wahl = (env.get("KRAKEN_PRODUKT") or "spot").strip().lower()
    return "futures" if wahl in ("futures", "future", "perpetual", "pf") else "spot"


class _KrakenQuoteNode:
    """Eigenstaendiger, read-only Kraken-Quote-Node fuer Spot oder Futures."""

    read_only = True

    def __init__(self, produkt, symbol):
        self.produkt = produkt
        self.symbol = symbol
        self.name = "Kraken Paper-Node (%s)" % produkt.upper()
        self._prozess = None
        self._pid_pfad = HIER / ("nautilus_kraken_node_%s.pid" % produkt)

    def zusatz(self):
        """PnL-Kurztext aus dem Papierbuch des Nodes, sonst leer."""
        stand = lese_papierstand(self.produkt, HIER / "nautilus_kraken")
        if not stand:
            return ""
        gesamt = stand["realisiert"] + stand["unrealisiert"]
        return "PnL %+.2f (%d Trades)" % (gesamt, stand["trades"])

    def _pid(self):
        try:
            return int(self._pid_pfad.read_text(encoding="ascii").strip().split()[0])
        except (OSError, ValueError, IndexError):
            return None

    def _persistiert_ist_eigener_node(self, pid):
        """PID nur akzeptieren, wenn exe, Skript und Produkt uebereinstimmen."""
        try:
            proc = psutil.Process(pid)
            exe = os.path.normcase(os.path.realpath(proc.exe()))
            erwartet_exe = os.path.normcase(os.path.realpath(str(_NAUTILUS_PY)))
            cmd = [os.path.normcase(os.path.realpath(a)) if os.path.exists(a) else a
                   for a in proc.cmdline()]
            skript = os.path.normcase(os.path.realpath(str(_KRAKEN_NODE)))
            return (exe == erwartet_exe and skript in cmd
                    and _produkt_aus_env(proc.environ()) == self.produkt)
        except (psutil.Error, OSError, PermissionError):
            return False

    def _suche_node(self):
        """PID des laufenden Nodes per Prozess-Scan, falls die PID-Datei veraltet ist.

        Der venv-python.exe ist ein Launcher, der den Basis-Python als Kind
        startet; beide tragen Skript und Produkt. Gemeldet wird der oberste.
        """
        skript = os.path.normcase(os.path.realpath(str(_KRAKEN_NODE)))
        treffer = set()
        for proc in psutil.process_iter():
            try:
                cmd = [os.path.normcase(os.path.realpath(a)) if os.path.exists(a) else a
                       for a in proc.cmdline()]
                if skript in cmd and _produkt_aus_env(proc.environ()) == self.produkt:
                    treffer.add((proc.pid, proc.ppid()))
            except (psutil.Error, OSError):
                continue
        pids = {pid for pid, _ in treffer}
        oberste = sorted(pid for pid, eltern in treffer if eltern not in pids)
        return oberste[0] if oberste else None

    def laeuft(self):
        if self._prozess is not None and self._prozess.poll() is None:
            return True
        pid = self._pid()
        if (pid is not None and hz.prozess_lebt(pid) is True
                and self._persistiert_ist_eigener_node(pid)):
            return True
        gefunden = self._suche_node()
        if gefunden is None:
            return False
        # Nur Merkhilfe fuer den naechsten Start: fehlt der Ordner, gilt die PID trotzdem.
        try:
            self._pid_pfad.write_text("%d\n" % gefunden, encoding="ascii")
        except OSError:
            pass
        return True

    def starten(self):
        if self.laeuft():
            return
        env = os.environ.copy()
        env["KRAKEN_PRODUKT"] = self.produkt
        env["KRAKEN_SYMBOL"] = self.symbol
        # Niemals einen Order-Client aktivieren: der Reiter ist Quotes/Papier.
        env["NAUTILUS_MIT_ORDER"] = ""
        # Quote-only child: keine Kraken-Schluessel aus der Parent-Shell erben.
        for key in ("KRAKEN_SPOT_API_KEY", "KRAKEN_SPOT_API_SECRET",
                    "KRAKEN_FUTURES_DEMO_API_KEY", "KRAKEN_FUTURES_DEMO_API_SECRET"):
            env.pop(key, None)
        self._prozess = subprocess.Popen(
            [str(_NAUTILUS_PY), str(_KRAKEN_NODE)], cwd=str(HIER), env=env,
            creationflags=_CREATE_NEW_CONSOLE, close_fds=True,
        )
        self._pid_pfad.parent.mkdir(parents=True, exist_ok=True)
        self._pid_pfad.write_text("%d\n" % self._prozess.pid, encoding="ascii")

    def stoppen(self):
        pid = self._prozess.pid if self._prozess is not None else self._pid()
        if pid is None or not hz.prozess_lebt(pid):
            pid = self._suche_node()
        if pid is None or not hz.prozess_lebt(pid):
            self._pid_pfad.unlink(missing_ok=True)
            return
        subprocess.run(
            [os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                          "System32", "taskkill.exe"),
             "/F", "/T", "/PID", str(pid)],
            capture_output=True, check=False,
        )
        self._pid_pfad.unlink(missing_ok=True)


def _modus_der_spur(zustand):
    """Oberer `modus` der Spur; fehlt er, die Modi der Positionen.

    mosaic etc. tragen den Modus nur je Position - ohne diesen Rueckgriff
    stuende dort faelschlich '-'.
    """
    oben = zustand.get("modus")
    if oben:
        return str(oben)
    modi = sorted({str(p.get("modus")) for p in zustand.get("positionen") or []
                   if isinstance(p, dict) and p.get("modus")})
    return "/".join(modi) if modi else "-"


def spuren_status(jetzt=None):
    """Rein lesende Statuszeilen fuer jede Spur aus dauerlauf.SPUREN (Basis).

    Die Spurliste ist die eine Wahrheit. Fehlende oder unlesbare Dateien
    bleiben sichtbar als 'unbekannt', statt still aus der Tabelle zu fallen.
    """
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    zeilen = []
    for spur in dauerlauf.SPUREN:
        beschreibung = dauerlauf.SPUREN[spur]
        ordner = HIER / beschreibung.get("ordner", spur)
        suffix = ".futures" if beschreibung.get("skript") == "handeln_futures.py" else ""
        zustand = hz.lade_json(str(ordner / ("zustand%s.json" % suffix)))
        wachen = hz.lade_json(str(ordner / ("wachen%s.json" % suffix)))
        lage, alter, grenze = hz.herzschlag_lage(spur, zustand, wachen, jetzt)
        positionen = hz.positionen_der_spur(spur, zustand, wachen)
        zeilen.append({
            "spur": spur,
            "modus": _modus_der_spur(zustand),
            "herzschlag": lage,
            "alter_minuten": alter,
            "positionen": len(positionen),
            "handel_erlaubt": wachen.get("handel_erlaubt"),
        })
    return zeilen


def filter_spuren(zeilen, auswahl):
    """Statusfilter fuer die Nautilus-Familie oder die ganze Flotte."""
    if auswahl == "Nautilus":
        return [z for z in zeilen if z["spur"].startswith("nautilus")]
    return list(zeilen)


def formatiere_spuren_status(zeilen):
    """Monospace-Statusmatrix aus der dauerlauf.SPUREN-Liste."""
    # Breite nach dem laengsten Namen, sonst verrutschen Spalten bei
    # nautilus_kraken_futures / klassik_donchian_trend.
    breite = max([20] + [len(z["spur"]) for z in zeilen])
    aus = ["%-*s MODUS     HERZSCHLAG          POSITIONEN  HANDEL_ERLAUBT" % (breite, "SPUR"),
           "-" * (breite + 59)]
    for z in zeilen:
        erlaubt = z.get("handel_erlaubt")
        live = "-" if erlaubt is None else ("true" if erlaubt else "false")
        alter = z.get("alter_minuten")
        lage = ("%s (%d min)" % (z["herzschlag"], alter)
                if alter is not None else z["herzschlag"])
        aus.append("%-*s %-9s %-20s %10d  %s" %
                   (breite, z["spur"], z["modus"], lage, z["positionen"], live))
    return "\n".join(aus)


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


PROZESSE = [_OmnitradetLauf(), _PythonDauerlauf(),
            _KrakenQuoteNode("spot", "BTC/EUR"),
            _KrakenQuoteNode("futures", "PF_SOLUSD")]


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class _ProzessZeile(ttk.Frame):
    """Statusanzeige + Start/Stopp fuer einen Prozess."""

    def __init__(self, eltern, prozess):
        super().__init__(eltern)
        self._p = prozess
        ttk.Label(self, text=prozess.name, width=22, anchor="w").pack(side="left")
        self.w_zustand = ttk.Label(self, text="", width=40, anchor="w")
        self.w_zustand.pack(side="left", padx=(0, 12))
        self.w_start = ttk.Button(self, text="Start", command=self._starten, width=7)
        self.w_start.pack(side="left", padx=(0, 4))
        self.w_stopp = ttk.Button(self, text="Stopp", command=self._stoppen, width=7)
        self.w_stopp.pack(side="left")
        self.refresh()

    def refresh(self):
        laeuft = self._p.laeuft()
        text = "\u25cf l\u00e4uft" if laeuft else "\u25cb gestoppt"
        zusatz = getattr(self._p, "zusatz", lambda: "")()
        self.w_zustand.config(text=text + ("  " + zusatz if zusatz else ""))
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
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(10, 8))
        filterzeile = ttk.Frame(self)
        filterzeile.pack(fill="x", pady=(0, 4))
        ttk.Label(filterzeile, text="Handelsspuren — nur Status; gesteuert vom Dauerlauf",
                  style="Titel.TLabel", anchor="w").pack(side="left")
        self._spur_filter = tk.StringVar(value="Alle")
        self._spur_auswahl = ttk.Combobox(filterzeile, textvariable=self._spur_filter,
                                          values=("Nautilus", "Alle"),
                                          state="readonly", width=12)
        self._spur_auswahl.pack(side="right")
        self._spur_auswahl.bind("<<ComboboxSelected>>", lambda _e: self._zeige_spuren())
        tabelle = ttk.Frame(self)
        tabelle.pack(fill="both", expand=True)
        self._spur_text = tk.Text(tabelle, height=18, wrap="none", state="disabled",
                                  font=stil.MONO)
        scroll = ttk.Scrollbar(tabelle, orient="vertical", command=self._spur_text.yview)
        self._spur_text.configure(yscrollcommand=scroll.set)
        self._spur_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._zeige_spuren()

    def _zeige_spuren(self):
        text = formatiere_spuren_status(filter_spuren(
            spuren_status(), self._spur_filter.get()))
        self._spur_text.configure(state="normal")
        self._spur_text.delete("1.0", "end")
        self._spur_text.insert("1.0", text)
        self._spur_text.configure(state="disabled")

    def refresh(self):
        for z in self._zeilen:
            z.refresh()
        self._zeige_spuren()

    def titel_zusatz(self):
        return " \u25cf" if any(z._p.laeuft() for z in self._zeilen) else ""

    def status(self):
        laufende = [z._p.name for z in self._zeilen if z._p.laeuft()]
        return ("L\u00e4uft: " + ", ".join(laufende)) if laufende else ""

    def abbrechbar(self):
        # Prozesse laufen weiter, auch wenn der Leitstand schliesst.
        return True
