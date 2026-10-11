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
"""

import sys
from pathlib import Path
from tkinter import ttk

import leitstand_stil as stil

NAUTILUS = Path(__file__).resolve().parent / "nautilus"


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


class NautilusReiter(ttk.Frame):
    """Reiter mit dem Nautilus-Inhalt - oder mit der Begruendung, warum nicht.

    Ohne installiertes nautilus_trader steht hier ein lesbarer Text statt
    eines Absturzes: ein Werkzeug darf den Rahmen nicht mitnehmen.
    """

    def __init__(self, eltern, leitstand):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.ls = leitstand
        self.frame = None
        self._grund = ""
        modul, grund = nautilus_gui_laden()
        if modul is None:
            self._grund = grund
            self._zeige_grund(grund)
        else:
            self.frame = modul.NautilusFrame(self)

    def _zeige_grund(self, grund):
        ttk.Label(self, text="Nautilus nicht verfügbar", style="Titel.TLabel",
                  anchor="w").pack(fill="x")
        ttk.Label(self, text=grund or "unbekannter Grund", anchor="w",
                  wraplength=520, justify="left").pack(fill="x", pady=(6, 0))
        ttk.Label(self, text="Nötig: pip install nautilus_trader==1.231.0 "
                  "in Agenten/Handel/.venv", anchor="w",
                  wraplength=520, justify="left").pack(fill="x", pady=(6, 0))

    # --- Reiter-Schnittstelle --------------------------------------------
    def refresh(self):
        # NautilusFrame pollt seine Queue selbst (120 ms). Ein Refresh hier
        # wuerde nur den Zustand erneut lesen, ohne etwas zu bewirken.
        pass

    def titel_zusatz(self):
        if self._grund:
            return " (fehlt)"
        laeuft = getattr(self.frame, "_running", False)
        return " ●" if laeuft else ""

    def status(self):
        if self._grund:
            return "Nautilus: %s" % self._grund
        if self.frame is not None and getattr(self.frame, "_running", False):
            return "Nautilus: Node läuft (OKX DEMO)"
        return ""

    def abbrechbar(self):
        """Solange ein Node laeuft, nicht ohne Rueckfrage schliessen."""
        return not getattr(self.frame, "_running", False)
