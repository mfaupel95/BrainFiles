"""Leitstand - ein Fenster fuer Ueberwachen, Freigaben, Backtests und Markt.

Handelt nie live und schreibt in keine wachen.json. Geschrieben wird nur an
drei Stellen, und keine davon liegt in diesem Rahmen:
  * freigabefenster.* aus dem Freigaben-Reiter (mit Sperre);
  * backtest_laeufe/ aus dem Backtest-Reiter;
  * backtest_urteile.py --aus-vorschau nach Bestaetigung (Bereich Urteile).
Der Rahmen selbst schreibt nur leitstand_zustand.json, ueber
leitstand_bedienung.Zustand.

Tastatur: Strg+1..8 Reiter, F5 sichtbaren Reiter auffrischen, Strg+Plus/Minus
Schrift. Notaus, Freigeben und Urteile eintragen haben bewusst KEIN Kuerzel.

Aufruf:  python leitstand.py
"""

import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk

import handelszentrale as hz
import leitstand_stil as stil
from leitstand_backtests import BacktestReiter
from leitstand_bedienung import Zustand, lage_gueltig, virtueller_schirm
from leitstand_freigaben import FreigabenReiter
from leitstand_freqtrade import FreqtradeReiter
from leitstand_markt import MarktReiter
from leitstand_nautilus import NautilusReiter
from leitstand_prozesse import ProzessReiter
from omniquant.gui import OmniquantReiter

TAKT_MS = 5000
SCHRIFT_MIN, SCHRIFT_MAX = 8, 16
HERZ_MAX_MIN = 30                  # wie die Handelszentrale: aelter = rot
MIN_B, MIN_H = 1000, 640
START_ANTEIL = 0.85                # Erststart: 85 % des Bildschirms, mittig

# Abschliessend: was hier nicht steht, hat kein Kuerzel.
KUERZEL = {
    "<Control-Key-1>": ("reiter", 0),
    "<Control-Key-2>": ("reiter", 1),
    "<Control-Key-3>": ("reiter", 2),
    "<Control-Key-4>": ("reiter", 3),
    "<Control-Key-5>": ("reiter", 4),
    "<Control-Key-6>": ("reiter", 5),
    "<Control-Key-7>": ("reiter", 6),
    "<Control-Key-8>": ("reiter", 7),
    "<F5>": ("auffrischen", None),
    "<Control-plus>": ("schrift", 1),
    "<Control-KP_Add>": ("schrift", 1),
    "<Control-minus>": ("schrift", -1),
    "<Control-KP_Subtract>": ("schrift", -1),
}

# Welcher Reiter im Takt aufgefrischt wird, haengt am Titel. Ueberwachen und
# Backtests takten sich selbst (15 s bzw. 200 ms). Omniquant und Nautilus
# lesen nur bei F5 neu - ohne Takt altert ihr Text, waehrend die Statusleiste
# weiterlaeuft. Sie gehoeren in TAKT_SICHTBAR: nur der sichtbare Reiter taktet,
# kein Netz im Hintergrund.
TAKT_IMMER = {"Freigaben"}         # Titel "Freigaben (n)" und Blinken auch im Hintergrund
TAKT_SICHTBAR = {"Markt", "Omniquant", "Nautilus", "Prozesse", "FreqTrade"}


class UeberwachenReiter(ttk.Frame):
    """Die Handelszentrale als Reiter; sie holt ihre Kurse selbst alle 15 s."""

    def __init__(self, eltern, leitstand):
        super().__init__(eltern)
        self.ls = leitstand
        self.hz = hz.Handelszentrale(self)

    def refresh(self):
        self.hz.refresh()

    def titel_zusatz(self):
        return ""

    def status(self):
        return ""


REITER = [("Überwachen", UeberwachenReiter),
          ("Freigaben", FreigabenReiter),
          ("Backtests", BacktestReiter),
          ("Markt", MarktReiter),
          ("Omniquant", OmniquantReiter),
          ("Nautilus", NautilusReiter),
          ("Prozesse", ProzessReiter),
          ("FreqTrade", FreqtradeReiter)]


def pid_aus_datei(pfad):
    """Die PID aus der Sperrdatei lesen.

    Die Datei traegt ZWEI Felder: `PID Zeitstempel` (sperre.py schreibt beides,
    damit ein Waechter eine verwaiste Sperre erkennt). `int()` auf die ganze
    Zeile scheitert still - ValueError, dann `pid = None`, und der Herzschlag
    meldet "laeuft nicht" fuer einen Dauerlauf, der laeuft.

    Deshalb hier das ERSTE Feld nehmen, nicht die ganze Zeile.
    """
    try:
        with open(pfad, encoding="ascii") as f:
            roh = (f.read() or "").strip()
    except OSError:
        return None
    if not roh:
        return None
    try:
        return int(roh.split()[0])
    except (ValueError, IndexError):
        return None


def herzschlag(jetzt=None):
    """Laeuft der Dauerlauf? Gelesen wie in der Handelszentrale (PID + Log)."""
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    pid_pfad, log_pfad = hz.dauerlauf_dateien()
    pid = pid_aus_datei(pid_pfad)
    lebt = hz.prozess_lebt(pid)
    _text, alt = hz.dauerlauf_stand(log_pfad, jetzt)
    if lebt and alt is not None and alt <= HERZ_MAX_MIN:
        return "Dauerlauf läuft (letzter Zyklus vor %.0f min)" % alt
    return "Dauerlauf läuft nicht"


def start_lage(schirm_b, schirm_h):
    b = max(MIN_B, round(schirm_b * START_ANTEIL))
    h = max(MIN_H, round(schirm_h * START_ANTEIL))
    return "%dx%d+%d+%d" % (b, h, max(0, (schirm_b - b) // 2),
                            max(0, (schirm_h - h) // 2))


class Leitstand:
    def __init__(self, root, zustand=None, reiter=None, uhr=None, herz=herzschlag):
        self.root = root
        self.zustand = zustand or Zustand()
        self.uhr = uhr or dt.datetime.now
        self.herz = herz
        self._meldung = ""
        self._zuletzt = ""
        self._fehler = []
        self._takt_id = None

        root.title("Leitstand — Papier, handelt nie live")
        root.minsize(MIN_B, MIN_H)
        stil.anwenden(root, hz.SCHRIFT_GROESSE)   # vor den Reitern: Optionsdatenbank
        geo = self.zustand.get("geometrie")
        if geo and lage_gueltig(geo, virtueller_schirm(root)):
            root.geometry(geo)
        else:
            root.geometry(start_lage(root.winfo_screenwidth(),
                                     root.winfo_screenheight()))

        # Statusleiste zuerst packen, sonst draengt das Notebook sie hinaus.
        self.w_status = ttk.Label(root, anchor="w", padding=(6, 2))
        self.w_status.pack(side="bottom", fill="x")
        self.buch = ttk.Notebook(root)
        self.buch.pack(fill="both", expand=True)

        # Die Schrift wird VOR den Reitern gesetzt, nicht danach. Das ist
        # keine Reihenfolge-Aesthetik: `Tabelle._breiten()` rechnet beim
        # ERSTEN Befuellen und merkt sich `_breiten_da = True` - ab dann
        # wird nie wieder gerechnet. Mit der alten Reihenfolge lief das
        # Befuellen mit der Vorgabe (Consolas 11) und der gespeicherte Wert
        # wurde erst danach gerendert. Nachgemessen bei Max' Wert 13:
        # Spalte `Spur` blieb 177 px, der Bedarf fuer
        # `nautilus_kraken_futures` ist 200 px - und Strg+Plus/Minus
        # aenderten nur die Schrift, nie die Breiten (bei 13 sind es 59
        # echte Abschneidungen, nicht 37 wie bei 11).
        #
        # `setze_schrift` bleibt VOR dem Reiterbau: `_zentrale()` gibt dann
        # None zurueck (die Reiterliste ist noch leer) und faellt auf
        # `stil.anwenden` zurueck - das ist der gewuenschte Weg.
        self.reiter, self.titel = [], []
        self.schrift = hz.SCHRIFT_GROESSE
        n = self.zustand.get("schrift")
        if isinstance(n, int) and SCHRIFT_MIN <= n <= SCHRIFT_MAX:
            self.schrift = n
        # Zwei Anwendungen, zwei Gruende, in dieser Reihenfolge:
        #   1. die Schrift VOR den Reitern, weil `Tabelle._breiten()` beim
        #      ersten Befuellen misst und sich dann nicht mehr aendert
        #      (sonst 100 Abschneidungen bei Max' gespeicherter Schrift 13);
        #   2. den Stil nochmal NACH den Reitern, weil ein Reiter in
        #      seinem Aufbau sein eigenes Treeview-Theme setzt und der
        #      Leitstand ihn ueberschreiben muss. `stil.anwenden` ist fuer
        #      beides dieselbe Funktion - sie wird hier zweimal gerufen,
        #      weil die Reihenfolge der beiden Gruende sich nicht
        #      vereinigen laesst. Nur 2. zu verschieben hat die Reiter ohne
        #      Farbe auf dem Tisch gelassen (gemessen '#ffffff' statt
        #      '#181825').
        stil.anwenden(root, self.schrift)

        for titel, klasse in (reiter or REITER):
            r = klasse(self.buch, self)
            self.buch.add(r, text=titel)
            self.reiter.append(r)
            self.titel.append(titel)
        stil.anwenden(root, self.schrift)   # nach den Reitern: sie setzen
                                           # ihr eigenes Treeview-Theme

        i = self.zustand.get("reiter")
        if isinstance(i, int) and 0 <= i < len(self.reiter):
            self.buch.select(i)
        self.buch.bind("<<NotebookTabChanged>>", self._gewechselt, add="+")

        for seq in KUERZEL:
            root.bind(seq, lambda _e, s=seq: self.kuerzel(s))
        root.protocol("WM_DELETE_WINDOW", self.schliessen)
        self._rahmen()
        self._takt_id = root.after(TAKT_MS, self._takt)
        # Am Notebook, nicht am Root: root.bind() gehoert allein den Kuerzeln.
        self.buch.bind("<Destroy>", self._abbrechen, add="+")

    def _abbrechen(self, _event=None):
        if self._takt_id is not None:
            try:
                self.root.after_cancel(self._takt_id)
            except tk.TclError:
                pass
            self._takt_id = None

    # --- Reiter -------------------------------------------------------------

    def sichtbarer_index(self):
        return self.buch.index(self.buch.select())

    def _gewechselt(self, _event=None):
        i = self.sichtbarer_index()
        self.zustand.merke("reiter", i)
        self._auffrischen(i)
        self._rahmen()

    def _auffrischen(self, i):
        try:
            self.reiter[i].refresh()
        except Exception as e:                               # noqa: BLE001
            self._fehler.append("%s: Fehler beim Auffrischen (%s)"
                                % (self.titel[i], e))

    def kuerzel(self, seq):
        was, arg = KUERZEL[seq]
        if was == "reiter":
            if arg < len(self.reiter):
                self.buch.select(arg)
        elif was == "auffrischen":
            self._auffrischen(self.sichtbarer_index())
            self._rahmen()
        elif was == "schrift":
            self.setze_schrift(self.schrift + arg)
        return "break"

    # --- Schrift ------------------------------------------------------------

    def _zentrale(self):
        for r in self.reiter:
            if isinstance(getattr(r, "hz", None), hz.Handelszentrale):
                return r.hz
        return None

    def setze_schrift(self, n, merken=True):
        n = max(SCHRIFT_MIN, min(SCHRIFT_MAX, int(n)))
        self.schrift = n
        z = self._zentrale()
        if z is not None:
            z.w_schrift.set(str(n))
            z._schrift_gewaehlt()
        stil.anwenden(self.root, n)
        if merken:
            self.zustand.merke("schrift", n)

    # --- Takt und Statusleiste ----------------------------------------------

    def melde(self, text):
        self._meldung = text
        self._rahmen()

    def _takt(self):
        try:
            sichtbar = self.sichtbarer_index()
            for i, titel in enumerate(self.titel):
                if titel in TAKT_IMMER or (titel in TAKT_SICHTBAR and i == sichtbar):
                    self._auffrischen(i)
            self._zuletzt = self.uhr().strftime("%H:%M:%S")
            self._rahmen()
            self.zustand.nachholen()
        finally:
            self._abbrechen()
            self._takt_id = self.root.after(TAKT_MS, self._takt)

    def _rahmen(self):
        """Reitertitel und Statusleiste aus dem Stand der Reiter."""
        for i, (titel, r) in enumerate(zip(self.titel, self.reiter)):
            self.buch.tab(i, text=titel + r.titel_zusatz())
        teile = [self.herz()]
        if self._zuletzt:
            teile.append("aktualisiert %s" % self._zuletzt)
        teile += [s for s in (r.status() for r in self.reiter) if s]
        teile += self._fehler
        self._fehler = []
        if self._meldung:
            teile.append(self._meldung)
        self.w_status.config(text="   |   ".join(teile))

    # --- Schliessen ---------------------------------------------------------

    def schliessen(self, frage=messagebox.askyesno):
        if any(not getattr(r, "abbrechbar", lambda: True)() for r in self.reiter):
            self.melde("Urteile werden gerade eingetragen — bitte warten")
            return False
        laeufe = [r.steuerung for r in self.reiter
                  if getattr(r, "steuerung", None) is not None
                  and r.steuerung.laeuft()]
        if laeufe:
            if not frage("Leitstand schließen",
                         "Ein Backtest läuft noch. Abbrechen und schließen?",
                         parent=self.root):
                return False
            for s in laeufe:
                s.abbrechen()
        self.zustand.daten["geometrie"] = self.root.geometry()
        self.zustand.speichern(sofort=True)
        self.root.destroy()
        return True


def main():
    # `dpi_bewusst()` statt `tk scaling 1.1` (Auftrag Max, 05.10.2026).
    # Gemessen: der Monitor ist 120 dpi, ein dpi-unawares Fenster sieht
    # 36 % weniger Bildschirm und Windows stretcht das fertige Bitmap.
    # Der Aufruf muss VOR dem ersten `Tk()` laufen; `tk scaling`
    # entfaellt (zusammen mit dpi_bewusst ergibt es 1.666 statt 1.25).
    hz.design.dpi_bewusst()
    root = tk.Tk()
    Leitstand(root)
    hz.nach_vorn(root)
    root.mainloop()


if __name__ == "__main__":
    main()
