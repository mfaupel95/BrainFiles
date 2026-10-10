"""Backtest-Reiter des Leitstands.

Vier Bereiche teilen sich eine Laufsteuerung (ein Lauf gleichzeitig), ein
Ausgabefeld und die Laufliste: Replay (Hauptweg), Einzelskripte, Optimieren,
Urteile. Jeder Bereich ist ein Frame mit TITEL, lauf_wechsel(laeuft) und
refresh(); er startet ueber reiter.starte(...).

Backtest-Runden zaehlen NICHT fuer die Freigabe (Design Backtest-Fundament);
der Reiter sagt das in einer festen Zeile.
"""

import json
import re
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import leitstand_laeufe as ll
import replay
import leitstand_stil as stil
from leitstand_bedienung import Tabelle, Tooltip, setze_knopf, umbrechen
from leitstand_optimieren import OptimierenBereich
from leitstand_urteile import UrteileBereich

HIER = Path(__file__).resolve().parent
HINWEIS_FREIGABE = ("Backtest-Runden zählen nicht für die Freigabe — dafür zählen "
                    "nur Papier-Runden und der Freigaben-Reiter.")
TAKT_MS = 200
MAX_TEXT_ZEILEN = 5000
REPLAY_VORGABEN = {"spur": replay.SPUREN_TEIL_A[0], "max_kerzen": "0",
                   "gebuehr": "", "gegenprobe": False}
LISTE = HIER / "leitstand_backtests.json"
# Laeufe, die wachen.json schreiben: ein Abbruch mittendrin hilft niemandem.
UNABBRECHBAR = {"urteile-eintragen"}
NICHT_ABBRECHBAR = "Urteile werden eingetragen — nicht abbrechbar"
VERBOTENE_FLAGS = ("--json", "--cache", "--lokal")
EIGENE_BEREICHE = ("optimieren.py", "backtest_urteile.py")
TYPEN = ("float", "int", "text", "wahl", "schalter")
_TEXT = re.compile(r"^[A-Za-z0-9](?!.*\.\.)[A-Za-z0-9_./-]{0,39}$")


# --- Replay: reine Funktionen -----------------------------------------------

def replay_spuren():
    """Alle Spuren, die der Replay fahren kann - Familie A, D und E.

    Familie D (mosaic, gitter) und Familie E (xperp) brauchen KEINEN eigenen
    Schalter: der Replay erkennt sie am Spurnamen (replay.MEHRZEITRAHMEN/
    EIGENE_RECHNUNG/SPUREN_TEIL_E). Hier steht nur die Liste, damit das
    Fenster sie anbietet.
    """
    return (list(replay.SPUREN_TEIL_A) + list(replay.MEHRZEITRAHMEN)
            + list(replay.EIGENE_RECHNUNG) + list(replay.SPUREN_TEIL_E))


def nicht_nachrechenbar():
    return sorted(replay.NICHT_NACHRECHENBAR.items())


def gegenprobe_moeglich(spur):
    """`--gegenprobe` vergleicht gegen `backtest_prognose` - das gibt es nur
    fuer Familie A. Fuer eine Spur mit eigener Rechnung waere der Aufruf ein
    Fehler, den der Nutzer erst nach dem Start sieht."""
    return spur in replay.SPUREN_TEIL_A


def pruefe_replay(werte):
    """(Argumente ohne Interpreter und --lauf, "") oder (None, Fehlertext)."""
    spur = werte.get("spur")
    if spur not in replay_spuren():
        return None, "Spur %r ist nicht nachrechenbar" % spur
    try:
        mk = int(str(werte.get("max_kerzen") or "0").strip())
    except ValueError:
        return None, "Max. Kerzen: ganze Zahl erwartet (0 = alle)"
    # Leeres Feld heisst: der GEMESSENE Satz der Spur gilt (replay nimmt ihn
    # selbst aus der wachen.json). Eine Zahl im Feld schlaegt die Vorgabe.
    roh_geb = str(werte.get("gebuehr", "")).strip().replace(",", ".")
    g = None
    if roh_geb:
        try:
            g = float(roh_geb)
        except ValueError:
            return None, "Gebühr: Zahl erwartet (Prozent je Seite) - oder leer lassen"
        if not 0 <= g <= 5:
            return None, "Gebühr: 0 bis 5 %"
    if not 0 <= mk <= 1_000_000:
        return None, "Max. Kerzen: 0 bis 1 000 000"
    if werte.get("gegenprobe") and not gegenprobe_moeglich(spur):
        return None, ("Gegenprobe gibt es nur für die Indikator-Spuren (%s) — "
                      "%s fährt einen eigenen Weg"
                      % (", ".join(replay.SPUREN_TEIL_A), spur))
    # Die Grenze der SPUR: unter `mindest_kerzen + Puffer` kann der Lauf keinen
    # einzigen Schritt rechnen (die Schleife laeuft von mindest_kerzen bis ans
    # Ende). Der Replay verweigert das selbst - hier wird der Lauf gar nicht
    # erst gestartet, sonst sieht der Nutzer statt eines Satzes einen Traceback.
    if mk:
        minimum = replay.bedarf_fuer(spur)
        if minimum and mk < minimum:
            return None, ("Max. Kerzen: %d ist zu klein — %s braucht mindestens "
                          "%d Kerzen je Reihe (0 = alle)" % (mk, spur, minimum))
    teile = ["--spur", spur]
    if g is not None:
        teile += ["--gebuehr", repr(g)]
    if mk:
        teile += ["--max-kerzen", str(mk)]
    if werte.get("gegenprobe"):
        teile.append("--gegenprobe")
    return teile, ""


def replay_befehl(teile, stempel):
    """Eigener Laufname: ein Leitstand-Lauf ueberschreibt keinen anderen."""
    return [sys.executable, "replay.py"] + list(teile) + ["--lauf",
                                                         "leitstand-" + stempel]


# --- Bereich Replay ---------------------------------------------------------

class ReplayBereich(ttk.Frame):
    TITEL = "Replay"

    def __init__(self, eltern, reiter):
        super().__init__(eltern, padding=8)
        self.reiter = reiter
        g = dict(REPLAY_VORGABEN,
                 **_als_dict(_als_dict(reiter.zustand.get("werte")).get("replay")))
        if g["spur"] not in replay_spuren():
                    g["spur"] = REPLAY_VORGABY_VORGABEN["spur"]
        self.w_spur = tk.StringVar(value=g["spur"])
        self.w_kerzen = tk.StringVar(value=str(g["max_kerzen"]))
        self.w_gebuehr = tk.StringVar(value=str(g["gebuehr"]))
        self.w_gegen = tk.BooleanVar(value=bool(g["gegenprobe"]))

        ttk.Label(self, text="Spur").grid(row=0, column=0, sticky="w")
        ttk.Combobox(self, textvariable=self.w_spur, values=replay_spuren(),
                     state="readonly", width=18).grid(row=0, column=1, sticky="w")
        ttk.Label(self, text="Max. Kerzen (0 = alle)").grid(row=1, column=0,
                                                           sticky="w")
        ttk.Spinbox(self, textvariable=self.w_kerzen, from_=0, to=1_000_000,
                    increment=500, width=10).grid(row=1, column=1, sticky="w")
        ttk.Label(self, text="Gebühr % je Seite (leer = Satz der Spur)").grid(
            row=2, column=0, sticky="w")
        ttk.Entry(self, textvariable=self.w_gebuehr, width=10).grid(row=2, column=1,
                                                                    sticky="w")
        self.w_satz = tk.StringVar()
        ttk.Label(self, textvariable=self.w_satz, foreground=stil.FARBEN["matt"]).grid(
            row=2, column=2, sticky="w", padx=(12, 0))
        # `--gegenprobe` vergleicht gegen `backtest_prognose` - das gibt es nur
        # fuer Familie A. Ein Kaestchen, das bei mosaic nur in einen Fehler
        # laeuft, wird ausgegraut statt angeboten.
        self.k_gegen = ttk.Checkbutton(
            self, text="Gegenprobe (alter gegen neuen Kern)",
            variable=self.w_gegen)
        self.k_gegen.grid(row=3, column=0, columnspan=2, sticky="w")
        # ERST hier: `_satz_hinweis_setzen` schaltet auch das Kaestchen um und
        # braucht es deshalb schon (14 Fehler am 01.10.2026, weil der Aufruf
        # davor stand).
        self._satz_hinweis_setzen()
        self.w_spur.trace_add("write", lambda *_: self._satz_hinweis_setzen())
        self.k_start = ttk.Button(self, text="Replay starten", command=self.starten)
        self.k_start.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.tip = Tooltip(self.k_start)

        ttk.Label(self, text="Nicht nachrechenbar:").grid(row=0, column=2,
                                                          sticky="nw", padx=(24, 4))
        grau = tk.Text(self, height=6, width=60, foreground=stil.FARBEN["matt"],
                       relief="flat", wrap="word")
        grau.insert("1.0", "\n".join("%s — %s" % p for p in nicht_nachrechenbar()))
        grau.configure(state="disabled")
        grau.grid(row=0, column=3, rowspan=5, sticky="nsew")
        self.columnconfigure(3, weight=1)

    def _satz_hinweis_setzen(self):
        """Welcher Satz gilt, wenn das Feld leer bleibt - sichtbar, nicht geraten.

        Ein festes 0.1 im Feld war bis 01.10.2026 der stille Fehler: `mosaic`
        handelt auf Kraken (0,60 %/Seite), rechnete im Backtest aber mit einem
        Sechstel der Kosten.
        """
        spur = self.w_spur.get()
        if not gegenprobe_moeglich(spur):
            self.w_gegen.set(False)
            self.k_gegen.state(["disabled"])
        else:
            self.k_gegen.state(["!disabled"])
        try:
            satz = replay.gebuehr_fuer(spur)
        except Exception as e:                                   # noqa: BLE001
            self.w_satz.set("Satz unbekannt: %s" % str(e)[:60])
            return
        self.w_satz.set("Satz der Spur: %g %%/Seite" % satz)

    def werte(self):
        return {"spur": self.w_spur.get(),
                "max_kerzen": self.w_kerzen.get().strip() or "0",
                "gebuehr": self.w_gebuehr.get().strip(),
                "gegenprobe": bool(self.w_gegen.get())}

    def starten(self):
        teile, fehler = pruefe_replay(self.werte())
        if teile is None:
            self.reiter.ls.melde(fehler)
            return
        self.reiter.zustand.merke_in("werte", "replay", self.werte())
        stempel = ll.zeitstempel()
        self.reiter.starte("replay-%s" % self.w_spur.get(),
                           replay_befehl(teile, stempel),
                           auswerten=ll.json_aus_ausgabe, stempel=stempel)

    def lauf_wechsel(self, laeuft):
        setze_knopf(self.k_start, self.tip, not laeuft, "es läuft schon ein Lauf")

    def refresh(self):
        pass


# --- Einzelskripte ----------------------------------------------------------

def eintrag_fehler(e):
    """"" oder der Grund, warum der Eintrag nicht startbar ist."""
    if not isinstance(e, dict) or not isinstance(e.get("name"), str):
        return "Eintrag ohne Namen"
    name, skript = e["name"], e.get("skript")
    if (not isinstance(skript, str) or Path(skript).is_absolute()
            or ".." in Path(skript).parts
            or not (HIER / skript).resolve().is_relative_to(HIER.resolve())):
        return "%s: Skriptpfad ungültig" % name
    if Path(skript).name in EIGENE_BEREICHE:
        return "%s: hat einen eigenen Bereich" % name
    if not (HIER / skript).is_file():
        return "%s: %s fehlt" % (name, skript)
    felder = e.get("felder")
    if not isinstance(felder, list):
        return "%s: felder fehlt" % name
    for f in felder:
        if (not isinstance(f, dict) or f.get("typ") not in TYPEN
                or not str(f.get("flag", "")).startswith("--")):
            return "%s: Feld ungültig" % name
        for grenze in ("min", "max"):
            if grenze in f and (isinstance(f[grenze], bool)
                                or not isinstance(f[grenze], (int, float))):
                return "%s: %s von %s ist keine Zahl" % (name, grenze, f["flag"])
        if f["flag"] in VERBOTENE_FLAGS:
            return "%s: %s ist gesperrt" % (name, f["flag"])
        if f["typ"] == "wahl" and not isinstance(f.get("werte"), list):
            return "%s: %s ohne werte" % (name, f["flag"])
    return ""


def lade_liste(pfad=None):
    """(gueltige Eintraege, Fehlertext). Ungueltige fallen weg und werden genannt."""
    try:
        roh = json.loads(Path(pfad or LISTE).read_text(encoding="utf-8"))
        eintraege = roh["eintraege"]
        if not isinstance(eintraege, list):
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        return [], "leitstand_backtests.json nicht lesbar"
    gut, fehler = [], []
    for e in eintraege:
        grund = eintrag_fehler(e)
        if grund:
            fehler.append(grund)
        else:
            gut.append(e)
    return gut, "; ".join(fehler)


def pruefe_feld(feld, wert):
    """(Argumente, "") oder (None, Fehler). Leer oder None: Flag weglassen."""
    typ, flag = feld["typ"], feld["flag"]
    if wert is None:
        return [], ""
    if typ == "schalter":
        return ([flag] if wert in (True, 1, "1", "true") else []), ""
    text = str(wert).strip()
    if text == "":
        return [], ""
    if typ == "wahl":
        if text not in [str(w) for w in feld["werte"]]:
            return None, "%s: %r nicht erlaubt" % (flag, text)
        return [flag, text], ""
    if typ == "text":
        if not _TEXT.match(text):
            return None, "%s: nur Buchstaben, Ziffern und _ . / -" % flag
        return [flag, text], ""
    try:
        zahl = int(text) if typ == "int" else float(text.replace(",", "."))
    except ValueError:
        return None, "%s: %s erwartet" % (flag, "ganze Zahl" if typ == "int"
                                          else "Zahl")
    lo, hi = feld.get("min"), feld.get("max")
    if (lo is not None and zahl < lo) or (hi is not None and zahl > hi):
        return None, "%s: erlaubt %s bis %s" % (flag, lo, hi)
    return [flag, str(zahl)], ""


def einzel_befehl(eintrag, werte):
    """werte: Flag -> Text/bool. (Befehl, "") oder (None, Fehler)."""
    args = []
    for f in eintrag["felder"]:
        teil, fehler = pruefe_feld(f, werte.get(f["flag"], f.get("vorgabe")))
        if teil is None:
            return None, fehler
        args += teil
    return [sys.executable, eintrag["skript"]] + args, ""


def _als_dict(x):
    """Gespeicherte Werte koennen falsch typisiert sein: dann leer."""
    return x if isinstance(x, dict) else {}


class EinzelBereich(ttk.Frame):
    TITEL = "Einzelskripte"

    def __init__(self, eltern, reiter, pfad=None):
        super().__init__(eltern, padding=8)
        self.reiter = reiter
        self.eintraege, fehler = lade_liste(pfad)
        self.vars = {}
        oben = ttk.Frame(self)
        oben.pack(fill="x")
        ttk.Label(oben, text="Skript").pack(side="left")
        namen = [e["name"] for e in self.eintraege]
        gemerkt = self._werte().get("einzel_name")
        self.w_name = tk.StringVar(value=gemerkt if gemerkt in namen
                                   else (namen[0] if namen else ""))
        wahl = ttk.Combobox(oben, textvariable=self.w_name, values=namen,
                            state="readonly", width=24)
        wahl.pack(side="left", padx=stil.ABSTAND)
        wahl.bind("<<ComboboxSelected>>", lambda _e: self._felder_bauen())
        self.k_start = ttk.Button(oben, text="Starten", command=self.starten)
        self.k_start.pack(side="left", padx=stil.ABSTAND)
        self.tip = Tooltip(self.k_start)
        ttk.Label(self, text=fehler, style="Fehler.TLabel").pack(anchor="w")
        self.rahmen = ttk.Frame(self)
        self.rahmen.pack(fill="x", pady=(6, 0))
        self._felder_bauen()
        self.lauf_wechsel(False)

    def _werte(self):
        return _als_dict(self.reiter.zustand.get("werte"))

    def eintrag(self):
        return next((e for e in self.eintraege if e["name"] == self.w_name.get()),
                    None)

    def _felder_bauen(self):
        for k in self.rahmen.winfo_children():
            k.destroy()
        self.vars = {}
        e = self.eintrag()
        if e is None:
            return
        gemerkt = _als_dict(_als_dict(self._werte().get("einzel")).get(e["name"]))
        for r, f in enumerate(e["felder"]):
            vorgabe = gemerkt.get(f["flag"], f.get("vorgabe"))
            if f["typ"] == "schalter":
                v = tk.BooleanVar(value=bool(vorgabe))
                ttk.Checkbutton(self.rahmen, text=f["flag"], variable=v).grid(
                    row=r, column=0, columnspan=2, sticky="w")
            else:
                v = tk.StringVar(value="" if vorgabe is None else str(vorgabe))
                ttk.Label(self.rahmen, text=f["flag"]).grid(row=r, column=0,
                                                            sticky="w", padx=(0, 8))
                if f["typ"] == "wahl":
                    ttk.Combobox(self.rahmen, textvariable=v, state="readonly",
                                 values=[str(w) for w in f["werte"]],
                                 width=22).grid(row=r, column=1, sticky="w")
                else:
                    ttk.Entry(self.rahmen, textvariable=v, width=24).grid(
                        row=r, column=1, sticky="w")
            self.vars[f["flag"]] = v
        if not e["felder"]:
            ttk.Label(self.rahmen, text="ohne Einstellungen").grid(row=0, column=0,
                                                                  sticky="w")

    def werte(self):
        return {flag: v.get() for flag, v in self.vars.items()}

    def starten(self):
        e = self.eintrag()
        if e is None:
            return
        befehl, fehler = einzel_befehl(e, self.werte())
        if befehl is None:
            self.reiter.ls.melde(fehler)
            return
        zustand = self.reiter.zustand
        if not isinstance(zustand.daten.get("werte"), dict):
            zustand.daten["werte"] = {}
        alle = dict(_als_dict(self._werte().get("einzel")))
        alle[e["name"]] = self.werte()
        zustand.merke_in("werte", "einzel", alle)
        zustand.merke_in("werte", "einzel_name", e["name"])
        self.reiter.starte("einzel-%s" % e["name"], befehl)

    def lauf_wechsel(self, laeuft):
        if not self.eintraege:
            setze_knopf(self.k_start, self.tip, False, "keine Einträge in der Liste")
        else:
            setze_knopf(self.k_start, self.tip, not laeuft, "es läuft schon ein Lauf")

    def refresh(self):
        pass


# --- der Reiter -------------------------------------------------------------

TEILER_ERSTSTART = (0.36, 0.6)          # Anteile der Hoehe fuer die zwei Teiler


class BacktestReiter(ttk.Frame):
    def __init__(self, eltern, leitstand, steuerung=None, bereiche=None):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.ls, self.zustand = leitstand, leitstand.zustand
        self.steuerung = steuerung or ll.Steuerung()
        self._fertig = None
        self._abbrechbar = True
        self._liste = []
        self._takt_id = None

        umbrechen(ttk.Label(self, text=HINWEIS_FREIGABE, style="Hinweis.TLabel")).pack(
            fill="x", pady=(0, stil.ABSTAND))
        teiler = self.teiler = ttk.PanedWindow(self, orient="vertical")
        teiler.pack(fill="both", expand=True)
        # Lage im Zustand: gemerkt beim Loslassen, hergestellt bei jeder
        # Groessenaenderung der Anlaufphase (umbrechende Hinweise verschieben
        # das Layout noch) - bis der Nutzer zieht oder eine Sekunde nach dem
        # ersten Zeigen (der Reiter ist beim Start meist verdeckt).
        self._teiler_anlauf, self._teiler_gezeigt = True, False
        teiler.bind("<ButtonRelease-1>", self._teiler_merken, add="+")
        teiler.bind("<Configure>", self._teiler_herstellen, add="+")
        teiler.bind("<Map>", self._teiler_zeigen, add="+")

        self.arten = ttk.Notebook(teiler)
        teiler.add(self.arten, weight=1)
        self.bereiche = []
        for klasse in (BEREICHE if bereiche is None else bereiche):
            b = klasse(self.arten, self)
            self.arten.add(b, text=b.TITEL)      # Instanz: Fabriken erlaubt
            self.bereiche.append(b)

        mitte = ttk.Frame(teiler)
        teiler.add(mitte, weight=2)
        kopf = ttk.Frame(mitte)
        kopf.pack(fill="x", pady=(stil.ABSTAND, 4))
        ttk.Label(kopf, text="Protokoll", style="Kopf.TLabel").pack(side="left")
        self.w_lauf = ttk.Label(kopf, text="kein Lauf")
        self.w_lauf.pack(side="left", padx=stil.ABSTAND_GROSS)
        self.k_abbrechen = ttk.Button(kopf, text="Abbrechen", command=self.abbrechen)
        self.k_abbrechen.pack(side="right")
        self.tip_abbrechen = Tooltip(self.k_abbrechen)
        self.w_ausgabe = tk.Text(mitte, height=10, wrap="none", state="disabled",
                                 font=stil.MONO)
        leiste = ttk.Scrollbar(mitte, orient="vertical", command=self.w_ausgabe.yview)
        self.w_ausgabe.configure(yscrollcommand=leiste.set)
        self.w_ausgabe.pack(side="left", fill="both", expand=True)
        leiste.pack(side="right", fill="y")

        unten = ttk.PanedWindow(teiler, orient="horizontal")
        teiler.add(unten, weight=2)
        links = ttk.Frame(unten, padding=(0, stil.ABSTAND, stil.ABSTAND, 0))
        unten.add(links, weight=1)
        ttk.Label(links, text="Läufe", style="Kopf.TLabel").pack(anchor="w",
                                                                 pady=(0, 4))
        self.liste = Tabelle(links, ll.LISTE_SPALTEN, self.zustand, "laeufe",
                             hoehe=6, auswahl="extended")
        self.liste.pack(fill="both", expand=True)
        knoepfe = ttk.Frame(links)
        knoepfe.pack(fill="x", pady=(stil.ABSTAND, 0))
        ttk.Button(knoepfe, text="Anzeigen", command=self.anzeigen).pack(side="left")
        ttk.Button(knoepfe, text="Vergleichen",
                   command=self.vergleichen).pack(side="left", padx=stil.ABSTAND)
        rechts = ttk.Frame(unten, padding=(stil.ABSTAND, stil.ABSTAND, 0, 0))
        unten.add(rechts, weight=1)
        ttk.Label(rechts, text="Kennzahlen", style="Kopf.TLabel").pack(anchor="w",
                                                                       pady=(0, 4))
        self.ergebnis = Tabelle(rechts, ll.KENNZAHL_SPALTEN, self.zustand,
                                "kennzahlen", hoehe=6)
        self.ergebnis.pack(fill="both", expand=True)

        self._lauf_wechsel(self.steuerung.laeuft())
        self.refresh()
        self._takt_id = self.after(TAKT_MS, self._takt)

    def _teiler_merken(self, _event=None):
        self._teiler_anlauf = False
        lage = [self.teiler.sashpos(i) for i in range(len(self.teiler.panes()) - 1)]
        self.zustand.merke_in("teiler", "backtests", lage)

    def _teiler_aus(self):
        """Aufrollen des Teiler-Starts sicher nachziehen.

        Das Widget kann schon zerstört sein, wenn der Timer eintrifft. Dann
        darf kein Tcl-Callback mehr auf einer toten Instanz laufen.
        """
        try:
            if getattr(self, "winfo_exists", lambda: False)():
                self._teiler_anlauf = False
        except Exception:                                   # noqa: BLE001
            pass

    def _teiler_zeigen(self, _event=None):
        if not self._teiler_gezeigt:
            self._teiler_gezeigt = True
            self.after(1000, self._teiler_aus)

    def _teiler_herstellen(self, _event=None):
        if not self._teiler_anlauf:
            return
        lage = (self.zustand.get("teiler") or {}).get("backtests")
        if not isinstance(lage, list):
            # Erststart: die Wunschhoehen der Bereiche wuerden dem Kopf fast
            # alles geben; Protokoll und Tabellen brauchen den Platz mehr.
            h = self.teiler.winfo_height()
            lage = [round(h * a) for a in TEILER_ERSTSTART] if h > 100 else []
        try:
            for i, pos in enumerate(lage[:len(self.teiler.panes()) - 1]):
                if isinstance(pos, int) and pos > 0:
                    self.teiler.sashpos(i, pos)
        except tk.TclError:
            pass

    # Reiter-Schnittstelle
    def refresh(self):
        self.refresh_liste()
        for b in self.bereiche:
            b.refresh()

    def titel_zusatz(self):
        return " ●" if self.steuerung.laeuft() else ""

    def status(self):
        return self.steuerung.status()

    # fuer die Bereiche
    def ablage(self):
        return Path(self.steuerung.ablage or ll.ABLAGE)

    def starte(self, name, befehl, auswerten=None, fertig=None, stempel=None):
        try:
            lauf = self.steuerung.starte(name, befehl, auswerten, stempel)
        except RuntimeError as e:
            self.ls.melde(str(e))
            return False
        except OSError as e:
            self.ls.melde("Start fehlgeschlagen: %s" % e)
            return False
        self._fertig = fertig
        self._abbrechbar = name not in UNABBRECHBAR
        self._leeren()
        self.schreibe("$ %s\n" % " ".join(lauf.befehl[1:]))
        self._lauf_wechsel(True)
        return True

    def schreibe(self, text):
        w = self.w_ausgabe
        w.configure(state="normal")
        w.insert("end", text)
        zeilen = int(w.index("end-1c").split(".")[0])
        if zeilen > MAX_TEXT_ZEILEN:
            w.delete("1.0", "%d.0" % (zeilen - MAX_TEXT_ZEILEN))
        w.see("end")
        w.configure(state="disabled")

    def _leeren(self):
        self.w_ausgabe.configure(state="normal")
        self.w_ausgabe.delete("1.0", "end")
        self.w_ausgabe.configure(state="disabled")

    # Ablauf
    def destroy(self):
        if self._takt_id is not None:
            try:
                self.after_cancel(self._takt_id)
            except tk.TclError:
                pass
            self._takt_id = None
        super().destroy()

    def _takt(self):
        try:
            neu, ende = self.steuerung.takt()
            if neu:
                self.schreibe("".join(neu))
            if ende:
                self._lauf_ende(*ende)
            self.w_lauf.config(text=self.steuerung.status() or "kein Lauf")
        finally:
            try:
                self._takt_id = self.after(TAKT_MS, self._takt)
            except tk.TclError:
                pass                       # Fenster ist zu

    def _lauf_ende(self, pfad, daten):
        rueck, self._fertig = self._fertig, None
        name = daten.get("name", "Lauf")
        if daten.get("abgebrochen"):
            self.ls.melde("%s abgebrochen" % name)
        elif daten.get("exit_code") == 0:
            self.ls.melde("%s fertig" % name)
        else:
            self.ls.melde("%s endete mit Exit %s" % (name, daten.get("exit_code")))
        if "ablage_fehler" in daten:
            self.ls.melde("%s: Ergebnis NICHT abgelegt — %s"
                          % (name, daten["ablage_fehler"]))
        if "ergebnis" in daten:
            self.ergebnis.setze(ll.ergebnis_zeilen(daten))
        self._lauf_wechsel(False)
        self.refresh_liste()
        if rueck:
            rueck(pfad, daten)

    def _lauf_wechsel(self, laeuft):
        setze_knopf(self.k_abbrechen, self.tip_abbrechen,
                    laeuft and self._abbrechbar,
                    NICHT_ABBRECHBAR if laeuft else "kein Lauf")
        for b in self.bereiche:
            b.lauf_wechsel(laeuft)

    def abbrechbar(self):
        """False, solange ein Lauf aus UNABBRECHBAR laeuft."""
        return self._abbrechbar or not self.steuerung.laeuft()

    def abbrechen(self):
        if not self.abbrechbar():
            self.ls.melde(NICHT_ABBRECHBAR)
            return
        if self.steuerung.laeuft():
            self.steuerung.abbrechen()
            self.ls.melde("Abbruch angefordert")

    # Laufliste
    def refresh_liste(self):
        self._liste = ll.laufliste(self.ablage())
        self.liste.setze(ll.listen_zeilen(self._liste))

    def _gewaehlte_laeufe(self):
        aus = []
        for zeile in self.liste.auswahl():
            d = ll.lade_lauf(self.ablage() / zeile[0])
            if d is None:
                self.ls.melde("%s nicht lesbar" % zeile[0])
                return None
            aus.append(dict(d, datei=zeile[0]))
        return aus

    def anzeigen(self):
        laeufe = self._gewaehlte_laeufe()
        if not laeufe:
            return
        d = laeufe[0]
        self._leeren()
        self.schreibe(d.get("ausgabe", ""))
        self.ergebnis.setze(ll.ergebnis_zeilen(d))

    def vergleichen(self):
        laeufe = self._gewaehlte_laeufe()
        if laeufe is None:
            return
        if len(laeufe) != 2:
            self.ls.melde("Vergleichen: genau zwei Läufe markieren")
            return
        # aelterer Lauf = A; Dateiname (beginnt mit dem Zeitstempel) als Ersatz
        a, b = sorted(laeufe, key=lambda d: (d.get("start", ""), d["datei"]))
        try:
            self.ergebnis.setze(ll.vergleich(a, b))
        except ValueError as e:
            self.ls.melde(str(e))


BEREICHE = [ReplayBereich, EinzelBereich, OptimierenBereich, UrteileBereich]
