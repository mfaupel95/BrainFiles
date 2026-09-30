"""Markt-Reiter des Leitstands: zeigt den letzten Prognose-Bericht.

Liest prognose_berichte/neuester.json (streng) und, wenn vorhanden,
neuester.weit.json (weit). Schreibt nichts, startet nichts, holt keine
Kurse - den Bericht schreibt der Dauerlauf (prognose.py), die Kurse zeigt
der Ueberwachen-Reiter. prognose.py wird bewusst NICHT importiert: es zieht
okx nach, einen Boersen-Client (tests/test_leitstand_markt_rein_lesend.py).
"""

import json
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk

import leitstand_stil as stil
from leitstand_bedienung import Tabelle, Tooltip, setze_knopf, umbrechen

HIER = Path(__file__).resolve().parent
BERICHTE = HIER / "prognose_berichte"          # wie in prognose.py
DATEIEN = {"streng": "neuester.json", "weit": "neuester.weit.json"}
ALTER_WARNUNG_H = 26
TREFFER_FELDER = ("inst", "richtung", "preis", "score", "cr", "stop", "ziel",
                  "risiko_prozent", "umsatz_24h_usd")
TORE_SPALTEN = ("Tor", "Wert", "Erklärung")
LEER = "—"
ZUKUNFT_TOLERANZ_H = -0.1     # kleine Uhrabweichung ist kein Fehler


# --- rein ------------------------------------------------------------------

def lade_bericht(pfad):
    """(bericht, "") oder (None, "fehlt" | "nicht lesbar")."""
    pfad = Path(pfad)
    if not pfad.exists():
        return None, "fehlt"
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError):
        return None, "nicht lesbar"
    if not isinstance(d, dict) or not isinstance(d.get("treffer", []), list):
        return None, "nicht lesbar"
    return d, ""


def alter_h(bericht, jetzt):
    try:
        erzeugt = datetime.fromisoformat(str(bericht.get("erzeugt")))
    except ValueError:
        return None
    if erzeugt.tzinfo is None:
        return None
    return (jetzt - erzeugt).total_seconds() / 3600   # ungerundet: 25:59 h warnt nicht


def warnung(bericht, jetzt):
    alter = alter_h(bericht, jetzt)
    if alter is None:
        return "Erzeugungszeit nicht lesbar"
    if alter < ZUKUNFT_TOLERANZ_H:
        return "Erzeugungszeit liegt in der Zukunft"
    if alter >= ALTER_WARNUNG_H:
        return ("Bericht ist %d h alt — der Dauerlauf hat keinen neueren geschrieben"
                % alter)
    return ""


def kopfzeile(bericht, jetzt):
    alter = alter_h(bericht, jetzt)
    return "Bericht vom %s · erzeugt vor %s · %s Märkte geprüft · %d Treffer" % (
        bericht.get("datum", LEER),
        LEER if alter is None or alter < ZUKUNFT_TOLERANZ_H else "%.1f h" % alter,
        bericht.get("maerkte_geprueft", LEER),
        len([t for t in bericht.get("treffer", []) if isinstance(t, dict)]))


def treffer_zeilen(bericht):
    return [tuple(t.get(f, LEER) for f in TREFFER_FELDER)
            for t in bericht.get("treffer", []) if isinstance(t, dict)]


def tore_zeilen(bericht):
    tore = bericht.get("tore")
    if not isinstance(tore, dict):
        return []
    return [(k, v, str(tore.get("_" + k, ""))) for k, v in sorted(tore.items())
            if not k.startswith("_")]


# --- der Reiter ------------------------------------------------------------

class MarktReiter(ttk.Frame):
    def __init__(self, eltern, leitstand, ordner=None, uhr=None):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.ls, self.zustand = leitstand, leitstand.zustand
        self.ordner = Path(ordner) if ordner else BERICHTE
        self.uhr = uhr or (lambda: datetime.now(timezone.utc))
        self._status = ""

        gemerkt = (self.zustand.get("werte") or {}).get("markt_fassung")
        self.fassung = tk.StringVar(value=gemerkt if gemerkt in DATEIEN else "streng")
        oben = ttk.Frame(self)
        oben.pack(fill="x")
        ttk.Label(oben, text="Fassung").pack(side="left")
        ttk.Radiobutton(oben, text="streng", value="streng", variable=self.fassung,
                        command=self.umschalten).pack(side="left", padx=4)
        self.r_weit = ttk.Radiobutton(oben, text="weit", value="weit",
                                      variable=self.fassung, command=self.umschalten)
        self.r_weit.pack(side="left", padx=4)
        self.tip_weit = Tooltip(self.r_weit)

        self.w_kopf = umbrechen(ttk.Label(self, text="", style="Kopf.TLabel"))
        self.w_kopf.pack(fill="x", pady=(stil.ABSTAND_GROSS, 0))
        # Nur sichtbar, wenn es etwas zu warnen gibt - sonst kein leeres Band.
        self.w_warnung = umbrechen(ttk.Label(self, text="", anchor="w",
                                             style="Warnung.TLabel"), rand=24)

        self.teiler = teiler = ttk.PanedWindow(self, orient="vertical")
        teiler.pack(fill="both", expand=True, pady=(stil.ABSTAND, 0))
        self.treffer = self._block(teiler, "Treffer", 3, TREFFER_FELDER,
                                   "markt_treffer")
        self.tore = self._block(teiler, "Tore", 1, TORE_SPALTEN, "markt_tore", hoehe=6)
        self.refresh()

    def _block(self, teiler, titel, gewicht, spalten, schluessel, **kw):
        rahmen = ttk.Frame(teiler, padding=(0, stil.ABSTAND, 0, 0))
        teiler.add(rahmen, weight=gewicht)
        ttk.Label(rahmen, text=titel, style="Kopf.TLabel").pack(anchor="w",
                                                                pady=(0, 4))
        t = Tabelle(rahmen, spalten, self.zustand, schluessel, **kw)
        t.pack(fill="both", expand=True)
        return t

    def umschalten(self):
        self.zustand.merke_in("werte", "markt_fassung", self.fassung.get())
        self.refresh()

    def refresh(self):
        weit_da = (self.ordner / DATEIEN["weit"]).exists()
        setze_knopf(self.r_weit, self.tip_weit, weit_da,
                    "kein %s" % DATEIEN["weit"])
        if not weit_da and self.fassung.get() == "weit":
            self.fassung.set("streng")
        name = DATEIEN[self.fassung.get()]
        bericht, fehler = lade_bericht(self.ordner / name)
        jetzt = self.uhr()
        if bericht is None:
            self.w_kopf.config(text=(
                "Kein Marktbericht: %s fehlt — ihn schreibt der Dauerlauf (prognose.py)"
                % name) if fehler == "fehlt" else "Marktbericht nicht lesbar: %s" % name)
            self._warne("")
            self.treffer.setze([])
            self.tore.setze([])
            return
        self.w_kopf.config(text=kopfzeile(bericht, jetzt))
        self._warne(warnung(bericht, jetzt))
        alter = alter_h(bericht, jetzt)
        hinweis = warnung(bericht, jetzt)
        self._status = ("Marktbericht %d h alt" % alter
                        if alter is not None and alter >= ALTER_WARNUNG_H else hinweis)
        self.treffer.setze(treffer_zeilen(bericht))
        self.tore.setze(tore_zeilen(bericht))

    def _warne(self, text):
        self.w_warnung.config(text=text)
        if text:
            self.w_warnung.pack(fill="x", pady=(stil.ABSTAND, 0), before=self.teiler)
        else:
            self.w_warnung.pack_forget()
            self._status = ""

    def titel_zusatz(self):
        return ""

    def status(self):
        return self._status
