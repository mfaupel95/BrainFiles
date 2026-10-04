"""Gemeinsame Bausteine des Leitstands.

Sortieren, Filtern, Kopieren, die Zustandsdatei, Tooltip, sortierbare
Tabelle und der Dialog mit Zeitablauf - damit die Reiter sie nicht je
einzeln bauen und sich nicht je anders verhalten.

Die Zustandsdatei `leitstand_zustand.json` ist nicht versioniert und wird
von keinem Betriebsteil gelesen.
"""

import csv
import ctypes
import json
import os
import re
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

import handelszentrale as hz                                # noqa: E402
import leitstand_stil as stil

HIER = Path(__file__).resolve().parent
ZUSTAND_DATEI = HIER / "leitstand_zustand.json"
SPEICHER_ABSTAND_S = 5.0          # Zustand hoechstens alle 5 s schreiben
# Spaltenbreiten beim ersten Befuellen aus dem Inhalt; Pfad- und SHA-Spalten
# bleiben schmal (wer sie braucht, zieht sie auf), lange Texte gedeckelt.
SCHMAL, BREIT_MAX, BREIT_MUSTER = 90, 420, 200
SCHMALE_SPALTEN = ("datei", "pfad", "sha")
ZEITLIMIT_S = 120                 # Dialoge: ohne Bedienung zu, nichts geschrieben

_ZAHL = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*([^\d.,:\-]*)$")
_LAGE = re.compile(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$")


# --- Sortieren, Filtern, Kopieren ------------------------------------------

def sortier_schluessel(wert):
    """Zahlen (auch "12,5 %", "50 USD") numerisch, alles andere als Text.

    Datum ("2026-09-29") und Dauer ("1:30 h") sind Text: lexikalisch
    sortieren sie richtig, numerisch waere nur die erste Zahl gelesen.
    """
    if wert is None:
        return (1, 0.0, "")
    if isinstance(wert, bool):
        return (1, 0.0, str(wert).lower())
    if isinstance(wert, (int, float)):
        return (0, float(wert), "")
    text = str(wert)
    m = _ZAHL.match(text)
    if m:
        return (0, float(m.group(1).replace(",", ".")), "")
    return (1, 0.0, text.lower())


# Zelle ist eine Zahl: ganz, ohne Datum/Dauer ("1:30 h" bleibt Text)
_NUR_ZAHL = re.compile(r"^\s*[+\-−]?\d+(?:[.,]\d+)?\s*%?\s*$")
_PUNKTZAHL = re.compile(r"^[+\-]?\d+(?:\.(\d+))?$")
_LEER = {"", "—", "-", "–"}
MAX_STELLEN = 4


def ist_zahl(wert):
    if isinstance(wert, bool) or wert is None:
        return False
    if isinstance(wert, (int, float)):
        return True
    return bool(_NUR_ZAHL.match(str(wert)))


def zahl_spalten(zeilen, n):
    """Spalten, in denen jede nicht leere Zelle eine Zahl ist (mindestens eine)."""
    aus = set()
    for i in range(n):
        werte = [z[i] for z in zeilen if i < len(z) and str(z[i]).strip() not in _LEER]
        if werte and all(ist_zahl(w) for w in werte):
            aus.add(i)
    return aus


def feste_stellen(werte):
    """Punktzahlen einer Spalte auf gleich viele Nachkommastellen (hoechstens 4).

    Nur fuer die Anzeige - Kopieren und CSV bleiben roh. Andere Zellen
    ("12,5 %", Text) bleiben, wie sie sind.
    """
    treffer = [_PUNKTZAHL.match(str(w)) for w in werte]
    stellen = min(MAX_STELLEN, max((len(m.group(1) or "") for m in treffer if m),
                                   default=0))
    return ["%.*f" % (stellen, float(w)) if m and stellen else str(w)
            for w, m in zip(werte, treffer)]


def passt(zeile, text):
    worte = (text or "").lower().split()
    gesamt = " ".join(str(z) for z in zeile).lower()
    return all(w in gesamt for w in worte)


def sortiere(zeilen, spalte, umgekehrt):
    return sorted(zeilen, key=lambda z: sortier_schluessel(z[spalte]),
                  reverse=umgekehrt)


def _zelle(wert):
    return (str(wert).replace("\t", " ").replace("\r", " ")
            .replace("\n", " "))


def als_tsv(spalten, zeilen):
    return "\n".join("\t".join(_zelle(c) for c in z)
                     for z in [tuple(spalten)] + list(zeilen))


def csv_schreiben(pfad, spalten, zeilen):
    """Semikolon und BOM: so oeffnet Excel mit deutschem Gebietsschema richtig."""
    with open(pfad, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(spalten)
        w.writerows(zeilen)


# --- Fenster ----------------------------------------------------------------

def lage_gueltig(geometrie, schirm):
    """Liegt die Titelleiste auf dem (virtuellen) Schirm, mind. 100 px breit?"""
    m = _LAGE.match(geometrie or "")
    if not m:
        return False
    b, _h, x, y = (int(g) for g in m.groups())
    sx, sy, sb, sh = schirm
    ueberlappung = min(x + b, sx + sb) - max(x, sx)
    return ueberlappung >= 100 and sy <= y <= sy + sh - 30


def virtueller_schirm(root):
    """(x, y, Breite, Hoehe) ueber alle Monitore; ohne Windows der Hauptschirm."""
    try:
        m = ctypes.windll.user32.GetSystemMetrics      # type: ignore[attr-defined]
        x, y, b, h = m(76), m(77), m(78), m(79)
        if b > 0 and h > 0:
            return (x, y, b, h)
    except Exception:                                        # noqa: BLE001
        pass
    return (0, 0, root.winfo_screenwidth(), root.winfo_screenheight())


class _FLASHWINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("hwnd", ctypes.c_void_p),
                ("dwFlags", ctypes.c_uint), ("uCount", ctypes.c_uint),
                ("dwTimeout", ctypes.c_uint)]


FLASHW_TRAY = 0x2


def blinken(root):
    """Einmal (3 Takte) in der Taskleiste blinken. False ohne Windows."""
    try:
        u = ctypes.windll.user32                          # type: ignore[attr-defined]
        u.GetParent.restype = ctypes.c_void_p
        u.GetParent.argtypes = [ctypes.c_void_p]
        hwnd = u.GetParent(root.winfo_id()) or root.winfo_id()
        info = _FLASHWINFO(ctypes.sizeof(_FLASHWINFO), hwnd, FLASHW_TRAY, 3, 0)
        u.FlashWindowEx(ctypes.byref(info))
        return True
    except Exception:                                        # noqa: BLE001
        return False


# --- Zustand ----------------------------------------------------------------

class Zustand:
    """leitstand_zustand.json: gebuendelt, atomar, unlesbar -> Vorgaben."""

    VORGABEN = {"reiter": 0, "geometrie": "", "schrift": 0,
                "werte": {}, "sortierung": {}, "teiler": {}}

    def __init__(self, pfad=ZUSTAND_DATEI, uhr=time.monotonic):
        self.pfad = Path(pfad)
        self.uhr = uhr
        self._zuletzt = None
        self._faellig = False
        self.daten = self.lade()

    def lade(self):
        aus = json.loads(json.dumps(self.VORGABEN))            # tiefe Kopie
        try:
            roh = json.loads(self.pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return aus
        if not isinstance(roh, dict):
            return aus
        for k, v in roh.items():
            if k in aus and type(v) is type(aus[k]):
                aus[k] = v
        return aus

    def get(self, k):
        return self.daten.get(k)

    def merke(self, k, v):
        self.daten[k] = v
        self.speichern()

    def merke_in(self, k, schluessel, v):
        self.daten.setdefault(k, {})[schluessel] = v
        self.speichern()

    def speichern(self, sofort=False):
        jetzt = self.uhr()
        if (not sofort and self._zuletzt is not None
                and jetzt - self._zuletzt < SPEICHER_ABSTAND_S):
            self._faellig = True
            return False
        tmp = self.pfad.with_name(self.pfad.name + ".tmp")
        try:
            tmp.write_text(json.dumps(self.daten, ensure_ascii=False, indent=2)
                           + "\n", encoding="utf-8")
            os.replace(tmp, self.pfad)
        except OSError:
            return False
        self._zuletzt = jetzt
        self._faellig = False
        return True

    def nachholen(self):
        """Vom Takt des Leitstands gerufen: einen gebuendelten Wunsch nachholen."""
        return self.speichern() if self._faellig else False


# --- Tk-Bausteine -----------------------------------------------------------

def umbrechen(label, rand=8):
    """Langer Hinweis bricht an der Breite um, statt abgeschnitten zu werden.
    Das Label muss mit fill="x" gepackt sein, sonst waechst es nicht mit."""
    label.bind("<Configure>", lambda e: label.configure(
        wraplength=max(e.width - rand, 120)), add="+")
    return label


class Tooltip:
    def __init__(self, widget, text=""):
        self.widget, self.text, self.fenster = widget, text, None
        widget.bind("<Enter>", self._zeigen, add="+")
        widget.bind("<Leave>", self._weg, add="+")

    def setze(self, text):
        self.text = text

    def _zeigen(self, _e=None):
        if not self.text or self.fenster:
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.fenster = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry("+%d+%d" % (x, y))
        tk.Label(tw, text=self.text, background=stil.FARBEN["gitter"],
                 foreground=stil.FARBEN["text"], font=stil.TEXT,
                 relief="solid", borderwidth=1, padx=6, pady=3).pack()

    def _weg(self, _e=None):
        if self.fenster:
            self.fenster.destroy()
            self.fenster = None


def setze_knopf(knopf, tip, erlaubt, grund):
    """Knopf frei/gesperrt; gesperrt nennt der Tooltip den Grund."""
    knopf.state(["!disabled"] if erlaubt else ["disabled"])
    tip.setze("" if erlaubt else grund)


class Tabelle(ttk.Frame):
    """Treeview mit Filterfeld, Sortieren per Spaltenkopf, Kopieren und CSV."""

    def __init__(self, eltern, spalten, zustand, name, hoehe=10,
                 auswahl="browse"):
        super().__init__(eltern)
        self.spalten, self.zustand, self.name = tuple(spalten), zustand, name
        self._alle, self._tags, self._sichtbar = [], [], []
        self._anzeige, self._breiten_da = [], False
        s = (zustand.get("sortierung") or {}).get(name)
        self.sortierung = (tuple(s) if isinstance(s, list) and len(s) == 2
                           and s[0] in self.spalten else None)

        kopf = ttk.Frame(self)
        kopf.pack(fill="x", pady=(0, 4))
        ttk.Label(kopf, text="Filter:").pack(side="left")
        self.w_filter = tk.StringVar()
        self.w_filter.trace_add("write", lambda *_: self._zeigen())
        ttk.Entry(kopf, textvariable=self.w_filter, width=24).pack(side="left",
                                                                   padx=4)
        ttk.Button(kopf, text="CSV …", command=self.csv_speichern).pack(side="right")
        ttk.Button(kopf, text="Kopieren", command=self.kopieren).pack(side="right",
                                                                     padx=4)
        self.baum = ttk.Treeview(self, columns=self.spalten, show="headings",
                                 height=hoehe, selectmode=auswahl)
        for sp in self.spalten:
            self.baum.heading(sp, text=sp,
                              command=lambda sp=sp: self.sortiere_nach(sp))
            self.baum.column(sp, width=110, anchor="w")
        # Leiste senkrecht UND waagerecht plus Mausrad (T-301): eine Tabelle
        # ohne waagerechte Leiste schneidet lange Zeilen ab (Pfadspalten,
        # Grund-Texte), und ohne `rad_selbst` reagiert sie nicht auf das Rad.
        # `rad_selbst` kommt aus `handelszentrale` - DIESE eine Quelle teilen
        # sich beide Fenster (fenster_design.py bleibt bewusst tkinter-frei).
        laenger = ttk.Scrollbar(self, orient="vertical", command=self.baum.yview)
        breiter = ttk.Scrollbar(self, orient="horizontal", command=self.baum.xview)
        self.baum.configure(yscrollcommand=laenger.set, xscrollcommand=breiter.set)
        breiter.pack(side="bottom", fill="x")
        self.baum.pack(side="left", fill="both", expand=True)
        laenger.pack(side="right", fill="y")
        hz.rad_selbst(self.baum)
        stil.tags(self.baum)
        self._pfeile()

    def setze(self, zeilen, tags=None):
        self._alle = [tuple(z) for z in zeilen]
        self._tags = [tuple(t) for t in tags] if tags else [()] * len(self._alle)
        zahlen = zahl_spalten(self._alle, len(self.spalten))
        spalten = [[z[i] if i < len(z) else "" for z in self._alle]
                   for i in range(len(self.spalten))]
        spalten = [feste_stellen(s) if i in zahlen else s
                   for i, s in enumerate(spalten)]
        self._anzeige = [tuple(z) for z in zip(*spalten)] if self._alle else []
        for i, sp in enumerate(self.spalten):
            self.baum.column(sp, anchor="e" if i in zahlen else "w")
            self.baum.heading(sp, anchor="e" if i in zahlen else "w")
        if self._alle and not self._breiten_da:
            self._breiten()
        self._zeigen()

    def _breiten(self):
        """Einmal, beim ersten Befuellen: danach gehoeren die Breiten dem Nutzer."""
        self._breiten_da = True
        try:
            f = tkfont.nametofont(stil.TABELLE, self)
            kopf = tkfont.nametofont(stil.FETT, self)
        except tk.TclError:                      # ohne stil.anwenden (Tests)
            f = kopf = tkfont.nametofont("TkDefaultFont", self)
        muster = self._anzeige[:BREIT_MUSTER]
        for i, sp in enumerate(self.spalten):
            inhalt = max((f.measure(str(z[i])) for z in muster), default=0)
            b = max(kopf.measure(sp + " ▲") + 24, inhalt + 16)
            schmal = any(s in sp.lower() for s in SCHMALE_SPALTEN)
            # Restplatz nur fuer die letzte Spalte (meist Erklaerung/Ergebnis)
            self.baum.column(sp, width=min(b, SCHMAL if schmal else BREIT_MAX),
                             stretch=i == len(self.spalten) - 1)

    def _zeigen(self):
        gewaehlt = {str(z[0]) for z in self.auswahl()}
        paare = [(z, t, a) for z, t, a in zip(self._alle, self._tags, self._anzeige)
                 if passt(z, self.w_filter.get())]
        if self.sortierung:
            i = self.spalten.index(self.sortierung[0])
            paare.sort(key=lambda p: sortier_schluessel(p[0][i]),
                       reverse=self.sortierung[1])
        self.baum.delete(*self.baum.get_children())
        self._sichtbar = [z for z, _t, _a in paare]
        for n, (z, t, a) in enumerate(paare):
            # zebra zuerst: der spaetere Tag (wartet, ueberlebt ...) gewinnt
            iid = self.baum.insert("", "end", values=a,
                                   tags=(("zebra",) if n % 2 else ()) + tuple(t))
            if str(z[0]) in gewaehlt:
                self.baum.selection_add(iid)

    def sichtbare(self):
        return list(self._sichtbar)

    def auswahl(self):
        kinder = self.baum.get_children()
        return [self._sichtbar[kinder.index(i)] for i in self.baum.selection()
                if i in kinder and kinder.index(i) < len(self._sichtbar)]

    def sortiere_nach(self, spalte):
        umgekehrt = bool(self.sortierung and self.sortierung[0] == spalte
                         and not self.sortierung[1])
        self.sortierung = (spalte, umgekehrt)
        self.zustand.merke_in("sortierung", self.name, [spalte, umgekehrt])
        self._pfeile()
        self._zeigen()

    def _pfeile(self):
        for sp in self.spalten:
            zeichen = ""
            if self.sortierung and self.sortierung[0] == sp:
                zeichen = " ▼" if self.sortierung[1] else " ▲"
            self.baum.heading(sp, text=sp + zeichen)

    def kopieren(self):
        text = als_tsv(self.spalten, self.sichtbare())
        self.clipboard_clear()
        self.clipboard_append(text)
        return text

    def csv_speichern(self):
        pfad = filedialog.asksaveasfilename(parent=self, defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")])
        if not pfad:
            return
        try:
            csv_schreiben(pfad, self.spalten, self.sichtbare())
        except OSError as e:
            messagebox.showerror("CSV", "nicht geschrieben: %s" % e, parent=self)


class ZeitDialog(tk.Toplevel):
    """Modaler Dialog, der sich nach `zeitlimit_s` ohne Bedienung schliesst.

    Jede Taste und jeder Klick setzt die Uhr zurueck. Esc und das
    Fensterkreuz ergeben "abgebrochen", der Ablauf "zeitablauf" - in beiden
    Faellen schreibt der Aufrufer nichts. Kein Return-Kuerzel: Bestaetigen
    geht nur per Mausklick auf den Knopf.
    """

    def __init__(self, eltern, titel, zeitlimit_s=ZEITLIMIT_S, uhr=time.monotonic):
        super().__init__(eltern)
        self.title(titel)
        self.transient(eltern)
        self.zeitlimit_s, self.uhr = zeitlimit_s, uhr
        self.ergebnis = None
        self._letzte = uhr()
        self.inhalt = ttk.Frame(self, padding=10)
        self.inhalt.pack(fill="both", expand=True)
        self.w_rest = ttk.Label(self, text="")
        self.w_rest.pack(anchor="e", padx=10, pady=(0, 6))
        self.bind("<KeyPress>", self._bedient, add="+")
        self.bind("<ButtonPress>", self._bedient, add="+")
        self.bind("<Escape>", lambda _e: self.fertig("abgebrochen"))
        self.protocol("WM_DELETE_WINDOW", lambda: self.fertig("abgebrochen"))
        self._takt_id = self.after(250, self._takt)

    def _bedient(self, _e=None):
        self._letzte = self.uhr()

    def rest_s(self):
        return max(0.0, self.zeitlimit_s - (self.uhr() - self._letzte))

    def _takt(self):
        if self.ergebnis is not None:
            return
        rest = self.rest_s()
        if rest <= 0:
            self.fertig("zeitablauf")
            return
        self.w_rest.config(text="schließt ohne Bedienung in %d s" % rest)
        self._takt_id = self.after(250, self._takt)

    def fertig(self, wert):
        if self.ergebnis is not None:
            return
        self.ergebnis = wert
        try:
            self.after_cancel(self._takt_id)
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()

    def zeige_modal(self):
        self.grab_set()
        self.focus_set()
        self.wait_window()
        return self.ergebnis
