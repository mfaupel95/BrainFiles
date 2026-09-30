"""Bereich Optimieren im Backtest-Reiter des Leitstands.

Faehrt optimieren.py: erst automatisch den Trockenlauf (Plan und geschaetzte
Dauer), sobald der Bereich sichtbar ist; "Rechnen" wird erst danach frei und
sperrt wieder, wenn sich ein Wert aendert. Das Ergebnis aus
daten/backtest/<spur>/optimierung.json erscheint als Tabelle; fuer einen
ueberlebenden Kandidaten zeigt der Bereich den Unterschied zur heutigen
<spur>/wachen.json als Text zum Kopieren.

Dieses Modul schreibt NICHTS - keine wachen.json, keine andere Datei
(geprueft per AST in tests/test_leitstand_optimieren.py). optimieren.py selbst
schreibt nur die Vorschlagsdatei optimierung.json. Einen Kandidaten
uebernimmt Max von Hand: ein anderer Stop ist eine Entscheidung ueber Geld.
"""

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import leitstand_laeufe as ll
import leitstand_stil as stil
import replay
from leitstand_bedienung import Tabelle, Tooltip, setze_knopf, umbrechen

HIER = Path(__file__).resolve().parent
SPUR_OPT = HIER / "spur_opt.json"

FELDER = (("spur", "Spur"), ("monate", "Monate"), ("fenster", "Fenster"),
          ("kandidaten", "höchstens Kandidaten"),
          ("gebuehr", "Gebühr % (leer = Vorgabe)"))
VORGABEN = {"spur": "", "monate": "6", "fenster": "2", "kandidaten": "40",
            "gebuehr": ""}
GRENZEN = {"monate": (1, 60), "fenster": (2, 12), "kandidaten": (1, 500)}
ENTPRELL_MS = 800
KANDIDAT_SPALTEN = ("Nr", "Werte", "netto je Runde", "Fenster +/−/zu wenig",
                    "überlebt", "Grund")


# --- rein ------------------------------------------------------------------

def _als_dict(x):
    """Gespeicherte Werte koennen falsch typisiert sein: dann leer.
    (Wie in leitstand_backtests; dort importieren gaebe einen Kreis.)"""
    return x if isinstance(x, dict) else {}


def spuren(pfad=None):
    """Spuren mit Suchbereich in spur_opt.json; [] wenn fehlend oder unlesbar."""
    try:
        d = json.loads(Path(pfad or SPUR_OPT).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(d, dict):
        return []
    return sorted(k for k, v in d.items()
                  if not k.startswith("_") and isinstance(v, dict))


def _ganz(text, name):
    try:
        zahl = int(str(text).strip())
    except ValueError:
        return None, "%s: ganze Zahl erwartet" % name
    lo, hi = GRENZEN[name]
    if not lo <= zahl <= hi:
        return None, "%s: erlaubt %d bis %d" % (name, lo, hi)
    return zahl, ""


def pruefe_werte(werte, spur_datei=None):
    """"" wenn die Werte gueltig sind, sonst die erste Fehlermeldung."""
    if werte.get("spur") not in spuren(spur_datei):
        return "Spur %r hat keinen Eintrag in spur_opt.json" % werte.get("spur")
    for name in ("monate", "fenster", "kandidaten"):
        _zahl, fehler = _ganz(werte.get(name, ""), name)
        if fehler:
            return fehler
    g = str(werte.get("gebuehr", "")).strip()
    if g:
        try:
            zahl = float(g.replace(",", "."))
        except ValueError:
            return "gebuehr: Zahl erwartet"
        if not 0 <= zahl <= 5:                    # auch NaN faellt hier heraus
            return "gebuehr: erlaubt 0 bis 5"
    return ""


def optimieren_befehl(werte, trocken):
    """Befehl fuer gueltige Werte (vorher pruefe_werte)."""
    b = [sys.executable, "optimieren.py", "--spur", werte["spur"],
         "--monate", str(int(str(werte["monate"]).strip())),
         "--fenster", str(int(str(werte["fenster"]).strip())),
         "--max-kandidaten", str(int(str(werte["kandidaten"]).strip()))]
    g = str(werte.get("gebuehr", "")).strip()
    if g:
        b += ["--gebuehr", str(float(g.replace(",", ".")))]
    if trocken:
        b.append("--trocken")
    return b


def angehoben(text):
    """Die Zeile "Zeitraum angehoben: ..." aus der Ausgabe, sonst ""."""
    for z in (text or "").splitlines():
        if z.startswith("Zeitraum angehoben:"):
            return z.strip()
    return ""


def _dauer(sek):
    try:
        m, s = divmod(int(sek), 60)
    except (TypeError, ValueError):
        return "?"
    return "%d:%02d min" % (m, s)


def plan_text(plan, hinweis=""):
    text = ("%s Kandidaten · %s Fenster · Takt %s · %s Kerzen · etwa %s"
            % (plan.get("kandidaten", "?"), plan.get("n_fenster", "?"),
               plan.get("takt", "?"), plan.get("kerzen", "?"),
               _dauer(plan.get("geschaetzte_sekunden"))))
    return text + ("\n" + hinweis if hinweis else "")


def lade_optimierung(spur, wurzel=None):
    """(Daten, "") oder (None, Grund). Liest nur."""
    pfad = Path(wurzel or replay.wurzel()) / spur / "optimierung.json"
    if not pfad.exists():
        return None, "noch keine Optimierung für %s" % spur
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "optimierung.json nicht lesbar"
    if not isinstance(d, dict) or not isinstance(d.get("kandidaten"), list):
        return None, "optimierung.json nicht lesbar"
    return d, ""


def _werte_text(werte):
    if not isinstance(werte, dict):
        return ""
    return ", ".join("%s=%s" % (k, ll._fmt(v)) for k, v in sorted(werte.items()))


def kandidaten_zeilen(opt):
    """Grundlinie zuerst, dann je Kandidat eine Zeile; Nr bleibt int."""
    zeilen = [("heute", "heutige Einstellung",
               ll._fmt(opt.get("grundlinie_netto_je_runde")), "", "", "Grundlinie")]
    tags = [("grundlinie",)]
    for nr, k in enumerate(opt.get("kandidaten") or [], 1):
        if not isinstance(k, dict):
            continue
        if "fehler" in k:
            zeilen.append((nr, _werte_text(k.get("werte")), "", "", "nein",
                           "Fehler: %s" % k["fehler"]))
            tags.append(())
            continue
        fenster = ("%s/%s/%s" % (k.get("fenster_gewonnen"), k.get("fenster_verloren"),
                                 k.get("fenster_zu_wenig"))
                   if "fenster_gewonnen" in k else "")
        ueberlebt = bool(k.get("ueberlebt"))
        zeilen.append((nr, _werte_text(k.get("werte")),
                       ll._fmt(k.get("netto_je_runde")), fenster,
                       "ja" if ueberlebt else "nein", str(k.get("grund", ""))))
        tags.append(("ueberlebt",) if ueberlebt else ())
    return zeilen, tags


def ohne_wirkung_text(opt):
    return "; ".join("Feld %s ändert nichts" % f
                     for f in (opt.get("ohne_wirkung") or []))


def alte_werte(spur, schluessel, hier=None):
    """Heutige Werte dieser Schluessel aus <spur>/wachen.json; None wenn unlesbar.
    Fehlt ein Schluessel, fehlt er auch im Ergebnis."""
    try:
        d = json.loads((Path(hier or HIER) / spur / "wachen.json")
                       .read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(d, dict):
        return None
    return {k: d[k] for k in schluessel if k in d}


def diff_text(spur, alt, neu):
    if alt is None:
        return "%s/wachen.json nicht lesbar" % spur
    zeilen = ["%s/wachen.json" % spur]
    for k in sorted(neu):
        if k not in alt or alt[k] != neu[k]:
            zeilen.append("  %s: %s → %s" % (k, ll._fmt(alt[k]) if k in alt else "fehlt",
                                             ll._fmt(neu[k])))
    if len(zeilen) == 1:
        return "%s/wachen.json: keine Änderung gegenüber heute" % spur
    return "\n".join(zeilen)


class TrockenPruefung:
    """Merkt die Werte des letzten gelungenen Trockenlaufs."""

    def __init__(self):
        self.werte = None

    def merke(self, werte):
        self.werte = dict(werte)

    def vergiss(self):
        self.werte = None

    def darf_rechnen(self, werte):
        if self.werte is None:
            return False, "erst Trockenlauf"
        if dict(werte) != self.werte:
            return False, "Werte geändert — Trockenlauf läuft neu"
        return True, ""


# --- der Bereich -----------------------------------------------------------

class OptimierenBereich(ttk.Frame):
    TITEL = "Optimieren"

    def __init__(self, eltern, reiter, spur_datei=None, wurzel=None, hier=None):
        super().__init__(eltern, padding=8)
        self.reiter = reiter
        self.spur_datei, self.wurzel, self.hier = spur_datei, wurzel, hier
        self.pruefung = TrockenPruefung()
        self._laeuft = False
        self._versucht = None           # Werte des letzten Trockenlauf-Starts
        self._entprell = None
        self._leerlauf = None
        self._spur_angezeigt = None
        self._opt = None

        liste = spuren(spur_datei)
        g = dict(VORGABEN, **_als_dict(_als_dict(reiter.zustand.get("werte"))
                                       .get("optimieren")))
        if g["spur"] not in liste:
            g["spur"] = liste[0] if liste else ""

        oben = ttk.Frame(self)
        oben.pack(fill="x")
        self.vars = {}
        for spalte, (name, text) in enumerate(FELDER):
            ttk.Label(oben, text=text).grid(row=0, column=spalte, sticky="w",
                                            padx=(0, 8))
            v = tk.StringVar(value=str(g[name]))
            if name == "spur":
                ttk.Combobox(oben, textvariable=v, values=liste, state="readonly",
                             width=16).grid(row=1, column=spalte, sticky="w",
                                            padx=(0, 8))
            else:
                ttk.Entry(oben, textvariable=v, width=10).grid(
                    row=1, column=spalte, sticky="w", padx=(0, 8))
            self.vars[name] = v
        self.w_spur = self.vars["spur"]

        zeile = ttk.Frame(self)
        zeile.pack(fill="x", pady=(6, 0))
        self.k_rechnen = ttk.Button(zeile, text="Rechnen", command=self.rechnen)
        self.k_rechnen.pack(side="left")
        self.tip = Tooltip(self.k_rechnen)
        ttk.Button(zeile, text="Ergebnis zeigen",
                   command=lambda: self.zeige(self.w_spur.get())).pack(
                       side="left", padx=stil.ABSTAND)
        self.w_plan = ttk.Label(zeile, text="", justify="left")
        self.w_plan.pack(side="left", padx=stil.ABSTAND_GROSS)
        self.w_hinweis = umbrechen(ttk.Label(self, text="", style="Hinweis.TLabel"))
        self.w_hinweis.pack(fill="x", pady=(stil.ABSTAND, 0))

        teiler = ttk.PanedWindow(self, orient="horizontal")
        teiler.pack(fill="both", expand=True, pady=(stil.ABSTAND, 0))
        self.tabelle = Tabelle(teiler, KANDIDAT_SPALTEN, reiter.zustand,
                               "optimieren", hoehe=8)
        self.tabelle.baum.bind("<<TreeviewSelect>>", self._auswahl, add="+")
        teiler.add(self.tabelle, weight=3)
        rechts = ttk.Frame(teiler)
        teiler.add(rechts, weight=2)
        ttk.Label(rechts, text="Übernahme von Hand — der Leitstand schreibt "
                               "nie in eine wachen.json").pack(anchor="w")
        self.w_diff = tk.Text(rechts, height=8, width=40, wrap="none",
                              state="disabled", font=stil.MONO)
        self.w_diff.pack(fill="both", expand=True)
        ttk.Button(rechts, text="Kopieren", command=self.kopieren).pack(
            anchor="e", pady=(4, 0))

        reiter.arten.bind("<<NotebookTabChanged>>", self._wenn_sichtbar, add="+")
        for v in self.vars.values():
            v.trace_add("write", lambda *_: self._geaendert())
        self._knopf()

    def destroy(self):
        for name in ("_entprell", "_leerlauf"):
            if getattr(self, name) is not None:
                try:
                    self.after_cancel(getattr(self, name))
                except tk.TclError:
                    pass
                setattr(self, name, None)
        super().destroy()

    # Werte und Knopf
    def werte(self):
        return {name: v.get().strip() for name, v in self.vars.items()}

    def _knopf(self):
        w = self.werte()
        fehler = pruefe_werte(w, self.spur_datei)
        if fehler:
            erlaubt, grund = False, fehler
        else:
            erlaubt, grund = self.pruefung.darf_rechnen(w)
            if erlaubt and self._laeuft:
                erlaubt, grund = False, "es läuft schon ein Lauf"
        setze_knopf(self.k_rechnen, self.tip, erlaubt, grund)

    def _geaendert(self):
        self._knopf()
        if self._entprell is not None:
            self.after_cancel(self._entprell)
        self._entprell = self.after(ENTPRELL_MS, self._entprell_feuert)

    # Trockenlauf automatisch, aber nur sichtbar
    def sichtbar(self):
        return str(self.reiter.arten.select()) == str(self)

    def _entprell_feuert(self):
        self._entprell = None                       # der Timer ist verbraucht
        self._wenn_sichtbar()

    def _wenn_sichtbar(self, _e=None):
        if self._entprell is not None:              # direkter Aufruf: Timer weg
            try:
                self.after_cancel(self._entprell)
            except tk.TclError:
                pass
            self._entprell = None
        try:
            if not self.sichtbar():
                return
        except tk.TclError:
            return                                  # Fenster ist zu
        spur = self.w_spur.get()
        if spur and spur != self._spur_angezeigt:
            self.zeige(spur)
        self._trocken_jetzt()

    def _trocken_jetzt(self):
        w = self.werte()
        fehler = pruefe_werte(w, self.spur_datei)
        if fehler:
            self.w_plan.config(text=fehler)
            self._knopf()
            return
        if self._laeuft or self.pruefung.werte == w or self._versucht == w:
            return
        self._versucht = w
        self.pruefung.vergiss()
        self.w_plan.config(text="Trockenlauf läuft …")
        gestartet = self.reiter.starte(
            "optimieren-trocken-%s" % w["spur"],
            optimieren_befehl(w, trocken=True),
            fertig=lambda _p, d: self._trocken_fertig(w, d))
        if gestartet is False:
            self._versucht = None
            self.w_plan.config(text="Start nicht möglich")
        self._knopf()

    def _trocken_fertig(self, w, daten):
        ausgabe = daten.get("ausgabe", "")
        plan = ll.json_aus_ausgabe(ausgabe) if daten.get("exit_code") == 0 else None
        if not isinstance(plan, dict) or "kandidaten" not in plan:
            self.pruefung.vergiss()
            self.w_plan.config(text="Trockenlauf ohne Plan (Exit %s)"
                               % daten.get("exit_code"))
        else:
            self.pruefung.merke(w)
            self.w_plan.config(text=plan_text(plan, angehoben(ausgabe)))
        self._knopf()

    # Bereich-Schnittstelle
    def lauf_wechsel(self, laeuft):
        self._laeuft = laeuft
        self._knopf()
        if not laeuft:
            self._leerlauf = self.after_idle(self._wenn_sichtbar)

    def refresh(self):
        self._knopf()
        self._wenn_sichtbar()

    # Rechnen
    def rechnen(self):
        w = self.werte()
        erlaubt, _grund = self.pruefung.darf_rechnen(w)
        if pruefe_werte(w, self.spur_datei) or not erlaubt or self._laeuft:
            return
        self.reiter.zustand.merke_in("werte", "optimieren", w)
        self.reiter.starte("optimieren-%s" % w["spur"],
                           optimieren_befehl(w, trocken=False),
                           fertig=lambda _p, d: self._rechnen_fertig(w["spur"], d))

    def _rechnen_fertig(self, spur, daten):
        if daten.get("exit_code") == 0:
            self.zeige(spur)
        else:
            self.w_hinweis.config(text="Optimierung ohne Ergebnis (Exit %s) — "
                                       "Ausgabe oben" % daten.get("exit_code"))

    # Anzeige
    def zeige(self, spur):
        self._spur_angezeigt = spur
        self._diff_setzen("")
        self._opt, fehler = lade_optimierung(spur, self.wurzel)
        if self._opt is None:
            self.tabelle.setze([])
            self.w_hinweis.config(text=fehler)
            return
        zeilen, tags = kandidaten_zeilen(self._opt)
        self.tabelle.setze(zeilen, tags)
        self.w_hinweis.config(text=ohne_wirkung_text(self._opt))

    def _diff_setzen(self, text):
        self.w_diff.configure(state="normal")
        self.w_diff.delete("1.0", "end")
        self.w_diff.insert("1.0", text)
        self.w_diff.configure(state="disabled")

    def _auswahl(self, _e=None):
        zeilen = self.tabelle.auswahl()
        if not zeilen or self._opt is None:
            return
        nr = zeilen[0][0]
        kand = self._opt.get("kandidaten") or []
        k = kand[nr - 1] if isinstance(nr, int) and 1 <= nr <= len(kand) else None
        if not isinstance(k, dict) or not k.get("ueberlebt"):
            self._diff_setzen("nur überlebende Kandidaten werden verglichen")
            return
        neu = k.get("werte") or {}
        spur = self._spur_angezeigt
        self._diff_setzen(diff_text(spur, alte_werte(spur, list(neu), self.hier), neu))

    def kopieren(self):
        text = self.w_diff.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.reiter.ls.melde("Unterschied kopiert")
        return text
