"""Bereich Urteile im Backtest-Reiter des Leitstands.

"Vorschau rechnen" faehrt backtest_urteile.py --vorschau --vorschau-datei:
Die Motoren laufen, geschrieben wird nur die Vorschau-Datei in der Ablage.
"Urteile eintragen ..." fragt nach (120 s, Esc = Abbruch, kein Kuerzel) und
startet erst dann backtest_urteile.py --aus-vorschau mit GENAU dieser Datei:
kein neuer Motorlauf. Nur so kommt der Leitstand an eine wachen.json, und
dort nur an die drei backtest-Felder der freigabe.

Dieses Modul schreibt selbst NICHTS (AST-Pruefung in
tests/test_leitstand_urteile.py). Die Pruefungen hier (Alter, Aenderungen)
sind Bequemlichkeit; massgeblich prueft backtest_urteile.py (Hash, Alter,
Zukunft) und meldet "nichts geschrieben - <Grund>".
"""

import json
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk

import backtest_urteile as bu
import leitstand_laeufe as ll
import leitstand_stil as stil
from leitstand_bedienung import Tabelle, Tooltip, ZeitDialog, setze_knopf, umbrechen

SPALTEN = ("Spur", "Urteil", "backtest_bestanden", "Text")
URTEIL_TEXT = {True: "bestanden", False: "nicht bestanden", None: "nicht ermittelbar"}


# --- rein ------------------------------------------------------------------

def urteile_befehl(spuren, datei):
    befehl = [str(bu.PY_SCANNER), "backtest_urteile.py"]
    for s in spuren:
        befehl += ["--spur", s]
    return befehl + ["--vorschau", "--vorschau-datei", str(datei)]


def eintragen_befehl(datei):
    return [str(bu.PY_SCANNER), "backtest_urteile.py", "--aus-vorschau", str(datei)]


def lade_vorschau(pfad):
    """Die Vorschau-Datei, oder None wenn sie fehlt, kaputt oder fremd ist."""
    try:
        d = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (not isinstance(d, dict) or d.get("art") != "urteile-vorschau"
            or not isinstance(d.get("spuren"), dict)):
        return None
    for e in d["spuren"].values():
        if isinstance(e, dict) and not isinstance(e.get("bestanden"), (bool, type(None))):
            return None
    return d


def _wert(v):
    if v is None:
        return "—"
    return "true" if v is True else "false" if v is False else str(v)


def _eintraege(daten):
    return [(s, e) for s, e in sorted(daten["spuren"].items()) if isinstance(e, dict)]


def vorschau_zeilen(daten):
    zeilen = []
    for spur, e in _eintraege(daten):
        neu = e.get("bestanden")
        wechsel = "%s → %s" % (_wert(e.get("alt")),
                               "bleibt" if neu is None else _wert(neu))
        zeilen.append((spur, URTEIL_TEXT.get(neu) if isinstance(neu, (bool, type(None))) else "?", wechsel,
                       str(e.get("urteil") or "")))
    return zeilen


def aenderungen(daten):
    """Was --aus-vorschau schreiben wuerde, je Spur eine Zeile."""
    aus = []
    for spur, e in _eintraege(daten):
        neu = e.get("bestanden")
        if neu is None:
            continue                    # nicht ermittelbar: alter Wert bleibt
        zeile = "%s/wachen.json: backtest_bestanden %s → %s" % (
            spur, _wert(e.get("alt")), _wert(neu))
        if e.get("alt") == neu:
            zeile += " (Urteilstext und Datum neu)"
        aus.append(zeile)
    return aus


def alter_min(daten, jetzt):
    try:
        stand = datetime.fromisoformat(str(daten.get("stand")))
    except ValueError:
        return None
    if stand.tzinfo is None:
        return None
    return (jetzt - stand).total_seconds() / 60


def darf_eintragen(datei, daten, jetzt):
    if datei is None:
        return False, "erst Vorschau rechnen"
    if daten is None:
        return False, "Vorschau nicht lesbar"
    alter = alter_min(daten, jetzt)
    if alter is None:
        return False, "Vorschau nicht lesbar"
    if alter < -bu.VORSCHAU_ZUKUNFT_MIN:
        return False, "Vorschau liegt in der Zukunft"
    if alter > bu.VORSCHAU_GUELTIG_MIN:
        return False, "Vorschau älter als %d min" % bu.VORSCHAU_GUELTIG_MIN
    if not aenderungen(daten):
        return False, "keine Änderung"
    return True, ""


def ergebnis_zeile(exit_code, ausgabe):
    zeilen = [z.strip() for z in (ausgabe or "").splitlines() if z.strip()]
    if exit_code == 2:
        return next((z for z in reversed(zeilen) if z.startswith("nichts geschrieben")),
                    "nichts geschrieben (Exit 2)")
    treffer = "; ".join(z for z in zeilen if z.startswith(
        ("geschrieben:", "unveraendert:", "nicht geschrieben:",
            "Urteile-Datei nicht geschrieben")))
    if exit_code == 0:
        return treffer or "nichts zu schreiben"
    return "Exit %s — %s" % (exit_code, treffer or "Ausgabe oben")


# --- Dialog ----------------------------------------------------------------

class EintragenDialog(ZeitDialog):
    """Ergebnis: "ja" | "abgebrochen" | "zeitablauf". Kein Return-Kuerzel."""

    def __init__(self, eltern, aenderungen, **kw):
        super().__init__(eltern, "Urteile eintragen", **kw)
        i = self.inhalt
        ttk.Label(i, text="Diese Urteile in die wachen.json schreiben?",
                  style="Titel.TLabel").pack(anchor="w")
        for zeile in aenderungen:
            ttk.Label(i, text=zeile).pack(anchor="w", padx=(10, 0))
        ttk.Label(i, text="handel_erlaubt und freigabe.erfuellt bleiben unberührt.",
                  style="Matt.TLabel").pack(anchor="w", pady=(stil.ABSTAND, 0))
        knoepfe = ttk.Frame(i)
        knoepfe.pack(anchor="e", pady=(10, 0))
        # Kein Tab-Fokus auf "Ja": Tab/Leertaste bestaetigen nie, den Anfangsfokus
        # hat "Abbrechen".
        self.k_ja = ttk.Button(knoepfe, text="Ja, eintragen", takefocus=0,
                               command=lambda: self.fertig("ja"))
        self.k_ja.pack(side="left", padx=4)
        self.k_abbruch = ttk.Button(knoepfe, text="Abbrechen",
                                    command=lambda: self.fertig("abgebrochen"))
        self.k_abbruch.pack(side="left", padx=4)

    def zeige_modal(self):
        self.grab_set()
        self.k_abbruch.focus_set()
        self.wait_window()
        return self.ergebnis


# --- der Bereich -----------------------------------------------------------

class UrteileBereich(ttk.Frame):
    TITEL = "Urteile"

    def __init__(self, eltern, reiter, dialog=EintragenDialog, uhr=None):
        super().__init__(eltern, padding=8)
        self.reiter, self.dialog = reiter, dialog
        self.uhr = uhr or (lambda: datetime.now(timezone.utc))
        self._laeuft = False
        self.datei, self.daten = None, None      # die angezeigte Vorschau

        oben = ttk.Frame(self)
        oben.pack(fill="x")
        ttk.Label(oben, text="Spuren").pack(side="left")
        gemerkt = (reiter.zustand.get("werte") or {}).get("urteile_spuren")
        self.vars = {}
        for s in sorted(bu.MOTOREN):
            v = tk.BooleanVar(value=(s in gemerkt) if isinstance(gemerkt, list)
                              else True)
            ttk.Checkbutton(oben, text=s, variable=v,
                            command=self._knoepfe).pack(side="left", padx=4)
            self.vars[s] = v
        self.k_vorschau = ttk.Button(oben, text="Vorschau rechnen",
                                     command=self.vorschau)
        self.k_vorschau.pack(side="left", padx=(12, 0))
        self.tip_vorschau = Tooltip(self.k_vorschau)
        umbrechen(ttk.Label(self, text="Die Vorschau schreibt nichts. Eintragen "
                                       "übernimmt genau diese Vorschau — kein "
                                       "neuer Lauf.", style="Matt.TLabel")).pack(
            fill="x", pady=(stil.ABSTAND, 0))

        self.tabelle = Tabelle(self, SPALTEN, reiter.zustand, "urteile", hoehe=4)
        self.tabelle.pack(fill="both", expand=True, pady=(4, 0))
        unten = ttk.Frame(self)
        unten.pack(fill="x", pady=(4, 0))
        self.k_eintragen = ttk.Button(unten, text="Urteile eintragen …",
                                      command=self.eintragen)
        self.k_eintragen.pack(side="left")
        self.tip_eintragen = Tooltip(self.k_eintragen)
        self.w_ergebnis = ttk.Label(unten, text="")
        self.w_ergebnis.pack(side="left", padx=12)
        self._knoepfe()

    def gewaehlte(self):
        return [s for s, v in self.vars.items() if v.get()]

    def _knoepfe(self):
        if not self.gewaehlte():
            setze_knopf(self.k_vorschau, self.tip_vorschau, False, "keine Spur gewählt")
        else:
            setze_knopf(self.k_vorschau, self.tip_vorschau, not self._laeuft,
                        "es läuft schon ein Lauf")
        erlaubt, grund = darf_eintragen(self.datei, self.daten, self.uhr())
        if erlaubt and self._laeuft:
            erlaubt, grund = False, "es läuft schon ein Lauf"
        setze_knopf(self.k_eintragen, self.tip_eintragen, erlaubt, grund)

    # Bereich-Schnittstelle
    def lauf_wechsel(self, laeuft):
        self._laeuft = laeuft
        self._knoepfe()

    def refresh(self):
        self._knoepfe()                          # die Vorschau altert

    # Vorschau
    def vorschau(self):
        spuren = self.gewaehlte()
        if not spuren or self._laeuft:
            return
        self.reiter.zustand.merke_in("werte", "urteile_spuren", spuren)
        stempel = ll.zeitstempel()
        datei = self.reiter.ablage() / ("%s-urteile%s" % (stempel, ll.VORSCHAU_ENDUNG))
        self.datei, self.daten = None, None
        self.tabelle.setze([])
        if self.reiter.starte("urteile", urteile_befehl(spuren, datei),
                              fertig=lambda _p, d: self._vorschau_fertig(datei, d),
                              stempel=stempel):
            self.w_ergebnis.config(text="Vorschau läuft …")
        self._knoepfe()

    def _vorschau_fertig(self, datei, daten):
        if daten.get("exit_code") != 0:
            self.w_ergebnis.config(text="Vorschau ohne Ergebnis (Exit %s) — Ausgabe oben"
                                   % daten.get("exit_code"))
        else:
            d = lade_vorschau(datei)
            if d is None:
                self.w_ergebnis.config(text="Vorschau nicht lesbar")
            else:
                self.datei, self.daten = datei, d
                self.tabelle.setze(vorschau_zeilen(d))
                self.w_ergebnis.config(text="Vorschau gilt %d min"
                                       % bu.VORSCHAU_GUELTIG_MIN)
        self._knoepfe()

    # Eintragen
    def eintragen(self):
        erlaubt, grund = darf_eintragen(self.datei, self.daten, self.uhr())
        if not erlaubt or self._laeuft:
            self.reiter.ls.melde(grund or "es läuft schon ein Lauf")
            return
        datei, daten = self.datei, self.daten
        antwort = self.dialog(self, aenderungen(daten)).zeige_modal()
        # Der Dialog kann bis zu 120 s offen gewesen sein: noch einmal pruefen.
        erlaubt, grund = darf_eintragen(self.datei, self.daten, self.uhr())
        if antwort == "ja" and (self.datei != datei
                                or (erlaubt and lade_vorschau(datei) != self.daten)):
            # Neue Vorschau oder Datei veraendert: nur eintragen, was die Tabelle zeigt.
            if self.datei == datei:
                self.datei, self.daten = None, None
            self.w_ergebnis.config(
                text="Vorschau-Datei hat sich geändert — neu rechnen")
            self._knoepfe()
            return
        if antwort != "ja" or not erlaubt:
            text = "Urteile nicht eingetragen — nichts geschrieben"
            if antwort == "ja" and grund:
                text += " (%s)" % grund
            self.w_ergebnis.config(text=text)
            self._knoepfe()
            return
        self.datei, self.daten = None, None      # verbraucht: kein zweites Mal
        if self.reiter.starte("urteile-eintragen", eintragen_befehl(datei),
                              fertig=lambda _p, d: self._eintragen_fertig(d)):
            self.w_ergebnis.config(text="trage ein …")
        else:
            self.datei, self.daten = datei, daten
        self._knoepfe()

    def _eintragen_fertig(self, daten):
        if daten.get("abgebrochen"):
            self.w_ergebnis.config(text="abgebrochen — Stand der wachen.json prüfen")
            self._knoepfe()
            return
        self.w_ergebnis.config(text=ergebnis_zeile(daten.get("exit_code"),
                                                   daten.get("ausgabe", "")))
        self._knoepfe()
