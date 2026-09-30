"""Das Fenster der Zentrale: Bereiche, Gruppen, Filter, Aktionen je Zeile.

Der Baum hat seit 30.09.2026 drei Ebenen:

    BEREICH (REPOS · WERKSTATT · HANDEL)
      GRUPPE (STARTBAR · EINRICHTEN · NEU · NUR DOKU · FEHLT)
        Projektzeile

Die Anzeigelogik (Filter, Gruppen, Bereichsbaum, Summenzeile) steht bewusst als
reine Funktionen oben - sie ist ohne Fenster pruefbar. Die Klasse `Fenster` baut
nur zusammen, was quellen/scan/manifest/aktionen liefern, und rechnet nichts
selbst.

Farben, Schrift, DPI und ttk-Stile kommen aus `Werkzeuge/fenster_design.py` -
dieselbe Quelle wie handelszentrale.py und leitstand.py.
"""

from __future__ import annotations

import importlib.util
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk

import aktionen
import befehle
import manifest
import quellen
import scan

_spec = importlib.util.spec_from_file_location(
    "fenster_design", Path(__file__).resolve().parent.parent / "fenster_design.py")
design = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(design)

FARBEN = design.FARBEN
SCHRIFT_ART = design.SCHRIFT_ART
SCHRIFT_GROESSE = design.SCHRIFT_GROESSE
ABSTAND = design.ABSTAND


def schrift(rel=0, fett=False):
    """Schriftart dieser Ansicht: Basis + relative Groesse."""
    return design.schrift(SCHRIFT_GROESSE, rel, fett)


dpi_bewusst = design.dpi_bewusst


GRUPPEN_TITEL = {
    "startbar": "STARTBAR",
    "einrichten": "EINRICHTEN",
    "neu": "NEU",
    "doku": "NUR DOKU",
    "fehlt": "FEHLT",
}
ERKLAERUNG = {
    "startbar": "Befehl belegt, alles da",
    "einrichten": "es fehlt noch etwas",
    "neu": "ohne Eintrag im Manifest",
    "doku": "kein Programm, nur Text",
    "fehlt": "Eintrag ohne Ordner",
}
# Die Gruppen, die Aufmerksamkeit brauchen - sie faerben Titel und Summenzeile.
AUFFAELLIGE_GRUPPEN = ("fehlt", "neu")
ALLE_BEREICHE = "Alle Bereiche"


# ------------------------------------------------------------------ Anzeigelogik
def gruppen_titel(gruppe: str, anzahl: int) -> str:
    """Ueberschrift einer Gruppe, mit dem Hinweis in Klammern: STARTBAR (4)."""
    return f"{GRUPPEN_TITEL.get(gruppe, gruppe.upper())} ({anzahl})"


def bereich_titel(kennung: str, anzahl: int) -> str:
    """Ueberschrift eines Bereichs, mit der Zahl aller Zeilen darunter."""
    return f"{kennung} - {anzahl}"


def sichtbare_zeilen(
    zeilen: list[manifest.Zeile], suchtext: str, bereich: str = ""
) -> list[manifest.Zeile]:
    """Filtern ueber Ordnername, Bot, Notiz, Art, Rolle und Pfad.

    `bereich` ist entweder leer/`ALLE_BEREICHE` oder der Name eines Bereichs
    (REPOS, WERKSTATT, HANDEL) - dann bleiben nur dessen Zeilen.
    """
    text = (suchtext or "").strip().lower()
    gefiltert = zeilen
    if bereich and bereich != ALLE_BEREICHE:
        gefiltert = [z for z in gefiltert if z.bereich == bereich]
    if not text:
        return list(gefiltert)
    return [
        z
        for z in gefiltert
        if text in z.ordner.lower()
        or text in (z.bot or "").lower()
        or text in (z.notiz or "").lower()
        or text in (z.anleitung or "").lower()
        or text in z.art.lower()
        or text in (z.rolle or "").lower()
        or text in bereichs_pfad(z).lower()
    ]


def bereichs_pfad(z: manifest.Zeile) -> str:
    """Der Ort einer Zeile, wie er in der Detailspalte steht."""
    if z.repo is not None:
        return str(z.repo.pfad)
    return f"{quellen.bereich(z.wurzel)}/{z.ordner}"


def nach_gruppen(zeilen: list[manifest.Zeile]) -> dict[str, list[manifest.Zeile]]:
    """Zeilen in die feste Gruppenreihenfolge legen; leere Gruppen fallen weg."""
    gruppen: dict[str, list[manifest.Zeile]] = {}
    for name in manifest.GRUPPEN_REIHENFOLGE:
        passende = [z for z in zeilen if z.gruppe == name]
        if passende:
            gruppen[name] = sorted(passende, key=lambda z: z.ordner.lower())
    return gruppen


def nach_bereichen(
    zeilen: list[manifest.Zeile],
) -> dict[str, dict[str, list[manifest.Zeile]]]:
    """Bereich -> Gruppe -> Zeilen. Leere Bereiche und Gruppen fallen weg."""
    ergebnis: dict[str, dict[str, list[manifest.Zeile]]] = {}
    for kennung in (quellen.bereich(w) for w in quellen.REIHENFOLGE):
        passende = [z for z in zeilen if z.bereich == kennung]
        if not passende:
            continue
        ergebnis[kennung] = nach_gruppen(passende)
    return ergebnis


def bereichsnamen(zeilen: list[manifest.Zeile]) -> list[str]:
    """Die Bereichsnamen, die wirklich Zeilen haben - in fester Reihenfolge."""
    return list(nach_bereichen(zeilen))


def auffaellige(zeilen: list[manifest.Zeile]) -> list[manifest.Zeile]:
    """Zeilen, die Achtung brauchen: Gruppe NEU oder FEHLT."""
    return [z for z in zeilen if z.gruppe in AUFFAELLIGE_GRUPPEN]


def zusammenfassung(zeilen: list[manifest.Zeile]) -> str:
    """Eine Zeile ueber allem: wie viel wo liegt und was auffaellt.

    Kurz gehalten - die Zeile steht rechts oben neben Bereichsauswahl und
    Suchfeld und darf dort nicht abgeschnitten werden. 'auffaellig' kommt nur
    vor, wenn es etwas gibt; sonst waere die Zeile laenger als noetig.
    """
    if not zeilen:
        return "nichts gefunden"
    bereiche = nach_bereichen(zeilen)
    teile = [
        f"{kennung} {sum(len(g) for g in gruppen.values())}"
        for kennung, gruppen in bereiche.items()
    ]
    text = f"{len(zeilen)} Zeilen · " + " · ".join(teile)
    fremde = fremde_zeilen(zeilen)
    if fremde:
        text += f" · {len(fremde)} fremd"
    auffall = len(auffaellige(zeilen))
    if auffall:
        text += f" · {auffall} auffaellig"
    return text


def fremde_zeilen(zeilen: list[manifest.Zeile]) -> list[manifest.Zeile]:
    """Zeilen in fremdem Material (Kennzeichen setzt manifest._zeile).

    Sie bleiben sichtbar - sie sollen ja auffindbar sein - aber sie werden
    gezaehlt ausgewiesen, damit 'unser Code' eine Zahl mit Bedeutung hat.
    """
    return [z for z in zeilen if any(g.startswith("fremd:") for g in z.gruende)]


def hinweis(zeile: manifest.Zeile) -> str:
    """Was in der Hinweisspalte steht: erst der Grund, sonst die Notiz."""
    if zeile.gruende:
        return "; ".join(zeile.gruende)
    if zeile.gruppe in ("doku", "neu", "fehlt"):
        return zeile.notiz
    return ""


# Die Spalten der Tabelle. Die Breiten sind in PIXELN bei 100 % Anzeige
# angegeben und werden mit dem DPI-Faktor gestreckt - ein fest eingetragener
# Wert wird auf einem skalierten Monitor zu schmal, weil Tk die Schrift in
# Geraetepixeln setzt (Befund 30.09.2026: 41 Zeichen brauchten 410 px in einer
# 366-px-Spalte, der Text war abgeschnitten).
SPALTEN = (
    ("art", "Art", 100),
    ("rolle", "Rolle", 108),
    ("bot", "Bot", 130),
    ("lauf", "letzter Start", 104),
    ("hinweis", "Hinweis", 366),
)
BREITE_PROJEKT = 250
SPALTEN_MINIMUM = 60


def spaltenbreiten(
    verfuegbar: int, s: float = 1.0, *, projekt: int = BREITE_PROJEKT, spalten=SPALTEN
) -> tuple[int, list[tuple[str, str, int]]]:
    """Spaltenbreiten fuer die verfuegbare Breite: erst skalieren, dann kuerzen.

    `verfuegbar` ist die Breite, die der Baum wirklich hat. Reicht sie nicht,
    wird in DIESER Reihenfolge gekuerzt: erst die Nebenspalten (Art, Rolle, Bot,
    letzter Start), dann die Projektspalte, zuletzt die Hinweisspalte - sie
    traegt den Grund und ist die einzige, deren Abschneiden Information
    vernichtet. Keine Spalte faellt unter `SPALTEN_MINIMUM`.
    """
    skaliert = int(round(projekt * s))
    wunsch = [(k, t, max(SPALTEN_MINIMUM, int(round(b * s)))) for k, t, b in spalten]
    gesamt = skaliert + sum(b for _, _, b in wunsch)
    if verfuegbar <= 0 or verfuegbar >= gesamt:
        return skaliert, wunsch

    ueber = gesamt - verfuegbar
    projekt_min = max(SPALTEN_MINIMUM, int(round(150 * s)))
    ergebnis = []
    # 1) Nebenspalten (alles ausser Hinweis)
    for k, t, b in wunsch:
        if ueber > 0 and k != "hinweis":
            nimm = min(b - SPALTEN_MINIMUM, ueber)
            b, ueber = b - nimm, ueber - nimm
        ergebnis.append([k, t, b])
    # 2) Projektspalte
    if ueber > 0:
        nimm = min(skaliert - projekt_min, ueber)
        skaliert, ueber = skaliert - nimm, ueber - nimm
    # 3) Hinweisspalte
    if ueber > 0:
        for eintrag in ergebnis:
            if eintrag[0] == "hinweis":
                eintrag[2] = max(SPALTEN_MINIMUM, eintrag[2] - ueber)
                break
    return skaliert, [(k, t, b) for k, t, b in ergebnis]


def fenstergroesse(root, breite: int = 1400, hoehe: int = 900, s: float = 1.0) -> str:
    """Die Startgroesse: so gross wie noetig, aber immer im Bild.

    Die Wunschgroesse wird mit dem DPI-Faktor gestreckt, damit Titel, Tabelle
    und Zeilenhoehe zusammenpassen; danach wird sie an den Bildschirm angepasst
    (Rand 80 px) und mittig gesetzt.
    """
    b, h = int(round(breite * s)), int(round(hoehe * s))
    try:
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    except Exception:                                        # noqa: BLE001
        return f"{b}x{h}"
    b = max(900, min(b, sw - 80))
    h = max(600, min(h, sh - 80))
    return f"{b}x{h}+{max(0, (sw - b) // 2)}+{max(0, (sh - h) // 3)}"


# ------------------------------------------------------------------ Fenster
class Fenster:
    """Die Oberflaeche. `lauf` und `jetzt` sind fuer Tests ersetzbar."""

    def __init__(
        self,
        brainfiles: Path | str,
        manifest_pfad: Path | str,
        profile_dir: Path | str,
        log_ordner: Path | str,
        *,
        lauf=None,
        jetzt=None,
    ):
        self.brainfiles = Path(brainfiles)
        self.manifest_pfad = Path(manifest_pfad)
        self.profile_dir = Path(profile_dir)
        self.log_ordner = Path(log_ordner)
        self.lauf = lauf or self._popen
        self.jetzt = jetzt or datetime.now
        self.zeilen: list[manifest.Zeile] = []
        self.kinder: dict[str, manifest.Zeile] = {}   # Item-Id -> Zeile

        dpi_bewusst()
        self.root = tk.Tk()
        self.s = design.skalierung(self.root)
        self.root.title("Zentrale - Repos · Werkstatt · Handel")
        self.root.geometry(fenstergroesse(self.root, s=self.s))
        self._bauen()
        self.aktualisieren()

    # ------------------------------------------------------------- Aufbau
    def _bauen(self) -> None:
        # Schrift und Farben ZENTRAL (fenster_design): alles, was nicht
        # ausdruecklich gesetzt wird, erbt von "." - die Zeilenhoehe folgt der
        # Schrift, sonst werden Buchstaben angeschnitten.
        design.stil_anwenden(ttk.Style(), SCHRIFT_GROESSE)
        self.root.configure(background=FARBEN["bg"])

        oben = ttk.Frame(self.root)
        oben.pack(fill="x", padx=ABSTAND["m"], pady=(ABSTAND["m"], ABSTAND["s"]))
        ttk.Label(oben, text="Bereich:").pack(side="left")
        self.bereich = tk.StringVar(value=ALLE_BEREICHE)
        self.bereich_wahl = ttk.Combobox(
            oben, textvariable=self.bereich, state="readonly", width=18,
            values=(ALLE_BEREICHE,),
        )
        self.bereich_wahl.pack(side="left", padx=(ABSTAND["s"], ABSTAND["l"]))
        self.bereich_wahl.bind("<<ComboboxSelected>>", lambda _: self.anzeigen())

        ttk.Label(oben, text="Filtern:").pack(side="left")
        self.suchtext = tk.StringVar()
        self.suchtext.trace_add("write", lambda *_: self.anzeigen())
        self.suchfeld = ttk.Entry(oben, textvariable=self.suchtext, width=26)
        self.suchfeld.pack(side="left", padx=ABSTAND["s"])
        ttk.Button(oben, text="Aktualisieren (F5)", command=self.aktualisieren).pack(
            side="left", padx=ABSTAND["s"]
        )
        self.zusammenfassung = ttk.Label(oben, text="", foreground=FARBEN["akzent"])
        self.zusammenfassung.pack(side="right")
        tabelle = ttk.Frame(self.root)
        tabelle.pack(fill="both", expand=True, padx=ABSTAND["m"])
        self.baum = ttk.Treeview(
            tabelle,
            columns=("art", "rolle", "bot", "lauf", "hinweis"),
            show="tree headings",
            selectmode="browse",
        )
        self.baum.heading("#0", text="Projekt")
        self.baum.column("#0", width=BREITE_PROJEKT, anchor="w", stretch=False)
        for spalte, titel, breite in SPALTEN:
            self.baum.heading(spalte, text=titel)
            # stretch=False: sonst verteilt Tk die Restbreite selbst und die
            # gerechnete Breite gilt nicht mehr (gemessen 30.09.2026).
            self.baum.column(spalte, width=breite, anchor="w", stretch=False)
        self._spalten_setzen()
        self.baum.tag_configure("bereich", foreground=FARBEN["akzent"])
        self.baum.tag_configure("gruppe", foreground=FARBEN["matt"])
        self.baum.tag_configure("auffaellig", foreground=FARBEN["gelb"])
        self.baum.tag_configure("fehlt", foreground=FARBEN["rot"])
        self.baum.tag_configure("startbar", foreground=FARBEN["text"])
        self.baum.pack(side="left", fill="both", expand=True)
        rollbalken = ttk.Scrollbar(tabelle, orient="vertical", command=self.baum.yview)
        rollbalken.pack(side="right", fill="y")
        self.baum.configure(yscrollcommand=rollbalken.set)
        self.baum.bind("<<TreeviewSelect>>", lambda _: self._auswahl_geaendert())
        self.baum.bind("<Double-Button-1>", lambda _: self.doppelklick())
        # Die Spaltenbreiten folgen der WIRKLICHEN Breite des Baums: nur so
        # passen Schrift (DPI) und Spalten auf jedem Monitor zusammen.
        self.baum.bind("<Configure>", self._spalten_setzen)

        self._bauen_details()

        unten = ttk.Frame(self.root)
        unten.pack(fill="x", padx=ABSTAND["m"], pady=ABSTAND["m"])
        self.knoepfe = {}
        for name, text, befehl in (
            ("ordner", "Ordner", self.ordner),
            ("terminal", "Terminal", self.terminal),
            ("start", "Starten", self.starten),
            ("bot", "Bot", self.bot_chat),
            ("doku", "Doku", self.doku),
        ):
            b = ttk.Button(unten, text=text, command=befehl, state="disabled")
            b.pack(side="left", padx=ABSTAND["xs"])
            self.knoepfe[name] = b
        ttk.Button(unten, text="Log oeffnen", command=self._log_oeffnen).pack(
            side="left", padx=ABSTAND["xs"]
        )
        ttk.Button(unten, text="Wiki", command=self._wiki).pack(side="left", padx=ABSTAND["xs"])

        self.status = ttk.Label(self.root, text="", anchor="w", foreground=FARBEN["matt"])
        self.status.pack(fill="x", padx=ABSTAND["m"], pady=(0, ABSTAND["m"]))

        self.root.bind("<F5>", lambda _: self.aktualisieren())
        self.root.bind("<Control-f>", lambda _: self.suchfeld.focus_set())
        self.root.bind("<Return>", lambda _: self.starten())

    def _spalten_setzen(self, _ereignis=None) -> None:
        """Die Spaltenbreiten an die wirkliche Baumbreite anpassen.

        Die 40 px sind Rollbalken und Innenrand - ohne den Abzug laeuft die
        letzte Spalte um genau diese Breite aus dem Fenster (gemessen:
        1715 px Spalten in 1697 px Platz).
        """
        verfuegbar = self.baum.winfo_width()
        if verfuegbar <= 1:
            return
        platz = verfuegbar - 40
        projekt, spalten = spaltenbreiten(platz, self.s)
        # Restbreite an die Hinweisspalte: dann fuellt die Tabelle das Fenster
        # genau aus, statt rechts eine Luecke zu lassen (gemessen: 376 px frei).
        rest = platz - projekt - sum(b for _, _, b in spalten)
        if rest > 0:
            spalten = [
                (k, t, b + rest if k == "hinweis" else b) for k, t, b in spalten
            ]
        self.baum.column("#0", width=projekt)
        for kennung, _titel, breite in spalten:
            self.baum.column(kennung, width=breite)

    # ------------------------------------------------------------- Daten
    def aktualisieren(self) -> None:
        """Platte und Manifest neu lesen (Knopf 'Aktualisieren')."""
        plaetze = [
            (w, scan.tief_scannen(w, pfad))
            for w, pfad in quellen.alle(self.brainfiles)
        ]
        eintraege = manifest.manifest_laden(self.manifest_pfad)
        self.zeilen = manifest.zeilen_bauen(plaetze, eintraege, self.profile_dir)
        namen = [ALLE_BEREICHE] + [
            f"{k} ({sum(len(g) for g in gruppen.values())})"
            for k, gruppen in nach_bereichen(self.zeilen).items()
        ]
        self.bereich_wahl.configure(values=tuple(namen))
        if self.bereich.get() not in namen:
            self.bereich.set(ALLE_BEREICHE)
        self.anzeigen()
        self.uebersicht = zusammenfassung(self.zeilen)
        self.status.configure(
            text=f"{sum(len(r) for _, r in plaetze)} Ordner auf der Platte, "
                 f"{len(eintraege)} Manifest-Eintraege | {self.uebersicht} | "
                 f"{self.manifest_pfad}"
        )

    def anzeigen(self) -> None:
        """Die gefilterten Zeilen in den Baum schreiben (Bereich -> Gruppe)."""
        self.baum.delete(*self.baum.get_children())
        self.kinder.clear()
        wahl = self.bereich.get().split(" (")[0]
        sichtbar = sichtbare_zeilen(self.zeilen, self.suchtext.get(), wahl)
        for kennung, gruppen in nach_bereichen(sichtbar).items():
            anzahl = sum(len(g) for g in gruppen.values())
            kopf = self.baum.insert(
                "", "end", text=bereich_titel(kennung, anzahl), open=True,
                values=("", "", "", "", quellen.BEREICH_ERKLAERUNG.get(kennung, "")),
                tags=("bereich",),
            )
            for name, zeilen in gruppen.items():
                gruppe = self.baum.insert(
                    kopf, "end", text=gruppen_titel(name, len(zeilen)), open=name != "doku",
                    values=("", "", "", "", ERKLAERUNG.get(name, "")),
                    tags=("gruppe",),
                )
                for z in zeilen:
                    item = self.baum.insert(
                        gruppe, "end", text=z.ordner,
                        values=(
                            z.art,
                            z.rolle or "-",
                            (f"{z.bot}{'' if z.bot_da else ' (fehlt)'}" if z.bot else "-"),
                            self._letzter_start(z),
                            hinweis(z),
                        ),
                        tags=(self._farbe(z),),
                    )
                    self.kinder[item] = z
        self.zusammenfassung.configure(text=f"{len(sichtbar)} von {len(self.zeilen)} Zeilen")
        self._details_fuellen(None)

    def _farbe(self, z: manifest.Zeile) -> str:
        """Farbmarke einer Zeile - Zustand, nie Dekoration."""
        if z.gruppe == "fehlt":
            return "fehlt"
        if z.gruppe == "neu":
            return "auffaellig"
        if z.gruende:
            return "auffaellig"
        return "startbar"

    def _beleg_name(self, z: manifest.Zeile) -> str:
        """Der Name, unter dem Starts dieses Projekts im Log liegen."""
        return z.ordner

    def _letzter_start(self, z: manifest.Zeile) -> str:
        """Der letzte Startbeleg: neueste Logdatei dieses Projekts, sonst leer."""
        treffer = sorted(
            self.log_ordner.glob(f"{self._beleg_name(z)}-*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not treffer:
            return ""
        zeit = datetime.fromtimestamp(treffer[0].stat().st_mtime)
        return f"{zeit:%d.%m. %H:%M}"

    def _gewaehlt(self) -> manifest.Zeile | None:
        auswahl = self.baum.selection()
        if not auswahl:
            return None
        return self.kinder.get(auswahl[0])

    # ------------------------------------------------------------- Detailbereich
    def _bauen_details(self) -> None:
        """Der Bereich unter der Tabelle: Ablauf in Worten + anklickbare Befehle."""
        rahmen = ttk.LabelFrame(self.root, text="Was dieses Projekt kann")
        rahmen.pack(fill="both", expand=False, padx=ABSTAND["m"], pady=(ABSTAND["s"], 0))

        links = ttk.Frame(rahmen)
        links.pack(side="left", fill="both", expand=True, padx=(ABSTAND["s"], 3), pady=ABSTAND["s"])
        self.anleitung_text = tk.Text(
            links, height=9, width=58, wrap="word", relief="flat",
            background=FARBEN["blatt"], foreground=FARBEN["text"],
            insertbackground=FARBEN["text"], selectbackground=FARBEN["auswahl"],
            font=schrift(),
        )
        self.anleitung_text.pack(side="left", fill="both", expand=True)
        self.anleitung_text.configure(state="disabled")
        leiste = ttk.Scrollbar(links, orient="vertical", command=self.anleitung_text.yview)
        leiste.pack(side="right", fill="y")
        self.anleitung_text.configure(yscrollcommand=leiste.set)

        rechts = ttk.Frame(rahmen)
        rechts.pack(side="left", fill="both", expand=True, padx=(3, ABSTAND["s"]), pady=ABSTAND["s"])
        self.befehlsbaum = ttk.Treeview(
            rechts, columns=("was", "befehl", "hinweis"), show="headings", selectmode="browse"
        )
        for spalte, titel, breite in (
            ("was", "Was", 170),
            ("befehl", "Befehl", 250),
            ("hinweis", "Hinweis", 150),
        ):
            self.befehlsbaum.heading(spalte, text=titel)
            self.befehlsbaum.column(spalte, width=breite, anchor="w")
        self.befehlsbaum.pack(side="left", fill="both", expand=True)
        self.befehlsbaum.bind("<Double-Button-1>", lambda _: self.befehl_ausfuehren())
        self.befehlsbaum.bind("<<TreeviewSelect>>", lambda _: self._befehl_gewaehlt())
        rollbalken = ttk.Scrollbar(rechts, orient="vertical", command=self.befehlsbaum.yview)
        rollbalken.pack(side="right", fill="y")
        self.befehlsbaum.configure(yscrollcommand=rollbalken.set)

        leiste2 = ttk.Frame(rahmen)
        leiste2.pack(side="left", fill="y", padx=(0, ABSTAND["s"]), pady=ABSTAND["s"])
        self.befehl_knoepfe = {}
        for name, text, befehl in (
            ("ausfuehren", "Befehl ausfuehren", self.befehl_ausfuehren),
            ("kopieren", "Befehl kopieren", self.befehl_kopieren),
            ("bot", "Bot damit beauftragen", self.befehl_an_bot),
        ):
            b = ttk.Button(leiste2, text=text, command=befehl, state="disabled")
            b.pack(side="top", fill="x", pady=ABSTAND["xs"])
            self.befehl_knoepfe[name] = b
        self.befehl_kinder: dict[str, befehle.Kommando] = {}

    def _details_fuellen(self, z: manifest.Zeile | None) -> None:
        """Text und Befehlsliste auf die gewaehlte Zeile umstellen."""
        self.anleitung_text.configure(state="normal")
        self.anleitung_text.delete("1.0", "end")
        self.befehlsbaum.delete(*self.befehlsbaum.get_children())
        self.befehl_kinder.clear()
        if z is None:
            self.anleitung_text.insert("1.0", "Links ein Projekt waehlen.")
        else:
            self.anleitung_text.insert("1.0", befehle.anleitung(z))
            for k in befehle.kommandos(z):
                item = self.befehlsbaum.insert(
                    "", "end", values=(k.was, befehle.befehl_text(k.cmd), k.hinweis)
                )
                self.befehl_kinder[item] = k
        self.anleitung_text.configure(state="disabled")
        self._befehl_gewaehlt()

    def _gewaehlter_befehl(self) -> befehle.Kommando | None:
        auswahl = self.befehlsbaum.selection()
        if not auswahl:
            return None
        return self.befehl_kinder.get(auswahl[0])

    def _befehl_gewaehlt(self) -> None:
        k = self._gewaehlter_befehl()
        z = self._gewaehlt()
        zustand = "normal" if k is not None else "disabled"
        self.befehl_knoepfe["ausfuehren"].configure(state=zustand)
        self.befehl_knoepfe["kopieren"].configure(
            state="normal" if k is not None and k.cmd else "disabled"
        )
        self.befehl_knoepfe["bot"].configure(
            state="normal" if k is not None and z is not None and z.bot_da else "disabled"
        )
        if k is not None and k.hinweis:
            self.status.configure(text=f"{k.was}: {k.hinweis}", foreground=FARBEN["matt"])

    def befehl_ausfuehren(self) -> None:
        """Den gewaehlten Befehl in einem sichtbaren Terminal im Projekt starten."""
        k = self._gewaehlter_befehl()
        z = self._gewaehlt()
        if k is None or z is None or z.repo is None:
            return
        if k.art == "ordner":
            self.ordner()
            return
        if k.art == "doku":
            self.doku()
            return
        if k.art == "terminal":
            self.terminal()
            return
        if k.art == "bot":
            self.bot_chat()
            return
        if k.art == "start":
            self.starten()
            return
        # Befehl ausfuehren: Tab mit `/c` (schliesst sich wieder), Ausgabe
        # zusaetzlich ins Log - sonst waere sie mit dem Tab weg.
        log = aktionen.log_pfad(self.log_ordner, f"{z.ordner}-befehl", self.jetzt())
        self._ruf(
            aktionen.argv_befehl_im_terminal(z.repo.pfad, k.cmd, log),
            f"{k.was}: {befehle.befehl_text(k.cmd)} - Ausgabe in {log.name}",
        )

    def befehl_kopieren(self) -> None:
        """Den Befehl in die Zwischenablage legen - zum Einfuegen von Hand."""
        k = self._gewaehlter_befehl()
        if k is None or not k.cmd:
            return
        text = befehle.befehl_text(k.cmd)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        self.status.configure(text=f"Kopiert: {text}", foreground=FARBEN["matt"])

    def befehl_an_bot(self) -> None:
        """Den Befehl als Auftrag an den Repo-Bot geben - er fuehrt aus und erklaert."""
        k = self._gewaehlter_befehl()
        z = self._gewaehlt()
        if k is None or z is None or z.repo is None or not (z.bot_da and z.bot):
            return
        if k.art in ("ordner", "doku", "terminal", "bot"):
            auftrag = (
                f"Im Ordner {z.ordner}: {k.was}. Erklaere mir in drei Saetzen, "
                f"was hier zu tun ist und was dabei herauskommt."
            )
        else:
            auftrag = (
                f"Im Ordner {z.ordner} den Befehl `{befehle.befehl_text(k.cmd)}` ausfuehren "
                f"und mir in drei Saetzen sagen, was herauskam."
            )
        self._ruf(
            aktionen.argv_bot_auftrag(z.bot, z.repo.pfad, auftrag),
            f"Bot {z.bot} beauftragt: {k.was}",
        )

    # ------------------------------------------------------------- Knoepfe
    def _auswahl_geaendert(self) -> None:
        z = self._gewaehlt()
        self._details_fuellen(z)
        if z is None or z.repo is None:
            for b in self.knoepfe.values():
                b.configure(state="disabled")
            return
        self.knoepfe["ordner"].configure(state="normal")
        self.knoepfe["terminal"].configure(state="normal")
        self.knoepfe["start"].configure(state="normal" if z.start_da else "disabled")
        self.knoepfe["bot"].configure(state="normal" if z.bot_da else "disabled")
        self.knoepfe["doku"].configure(
            state="normal" if z.repo.readme else "disabled"
        )
        teile = [z.bereich, z.ordner, z.art]
        if z.rolle:
            teile.append(z.rolle)
        if z.notiz:
            teile.append(z.notiz)
        if z.gruende:
            teile.append("Hinweis: " + "; ".join(z.gruende))
        if z.start:
            teile.append("Start: " + " ".join(z.start))
        self.status.configure(
            text=" | ".join(teile),
            foreground=FARBEN["rot"] if z.gruppe == "fehlt" else FARBEN["matt"],
        )

    def doppelklick(self) -> None:
        """Doppelklick: starten, wenn ein Start belegt ist - sonst den Ordner zeigen."""
        z = self._gewaehlt()
        if z is not None and z.start_da:
            self.starten()
        else:
            self.ordner()

    def _popen(self, argv: list[str]) -> subprocess.Popen:
        return subprocess.Popen(argv)

    def ordner(self) -> None:
        z = self._gewaehlt()
        if z and z.repo:
            datei = z.repo.datei if getattr(z.repo, "ist_datei", False) else None
            self._ruf(aktionen.argv_ordner(z.repo.pfad, datei), f"Ordner: {z.repo.pfad}")

    def terminal(self) -> None:
        z = self._gewaehlt()
        if z and z.repo:
            self._ruf(aktionen.argv_terminal(z.repo.pfad), "Terminal im Projektordner")

    def bot_chat(self) -> None:
        z = self._gewaehlt()
        if z and z.repo and z.bot_da and z.bot:
            # Ein Bauplatz fuer den Bot im Terminal - der Aufruf liegt in aktionen
            # (frueher stand er hier inline, und damit ohne Fensterwahl).
            self._ruf(
                aktionen.argv_bot_chat(z.bot, z.repo.pfad),
                f"Bot-Chat '{z.bot}' im Projektordner",
            )

    def doku(self) -> None:
        z = self._gewaehlt()
        if z and z.repo and z.repo.readme:
            fehler = aktionen.doku_oeffnen(z.repo.pfad / z.repo.readme)
            self.status.configure(
                text=fehler or f"Doku geoeffnet: {z.repo.readme}", foreground=FARBEN["matt"]
            )

    def _log_oeffnen(self) -> None:
        z = self._gewaehlt()
        if not z:
            return
        treffer = sorted(
            self.log_ordner.glob(f"{self._beleg_name(z)}-*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not treffer:
            self.status.configure(
                text=f"Kein Startbeleg fuer {z.ordner} - noch nie gestartet",
                foreground=FARBEN["gelb"],
            )
            return
        aktionen.doku_oeffnen(treffer[0])
        self.status.configure(text=f"Log: {treffer[0]}", foreground=FARBEN["matt"])

    def _wiki(self) -> None:
        """Die Hausdoku dieses Werkzeugs im Wiki oeffnen."""
        seite = self.brainfiles / "MaxHirn" / "Wiki" / "Werkzeuge" / "Repos-Zentrale.md"
        if seite.is_file():
            aktionen.doku_oeffnen(seite)
            self.status.configure(text=f"Wiki: {seite}", foreground=FARBEN["matt"])
        else:
            self.status.configure(
                text=f"Wiki-Seite fehlt: {seite}", foreground=FARBEN["gelb"]
            )

    def starten(self) -> None:
        z = self._gewaehlt()
        if z is None or not z.start_da:
            self.status.configure(
                text="Kein Startbefehl belegt - nichts gestartet", foreground=FARBEN["gelb"]
            )
            return
        self.status.configure(
            text=f"Starte {z.ordner}: {' '.join(z.start or [])} ...", foreground=FARBEN["matt"]
        )
        threading.Thread(target=self._starten_im_hintergrund, args=(z,), daemon=True).start()

    def _starten_im_hintergrund(self, z: manifest.Zeile) -> None:
        ergebnis = aktionen.start_ausfuehren(z, self.log_ordner, jetzt=self.jetzt())
        if ergebnis.fehler:
            self.root.after(0, lambda: self._start_fertig(z, ergebnis))
            return
        self.root.after(
            0,
            lambda: self.status.configure(
                text=f"{z.ordner} gestartet (PID {ergebnis.pid}) - Ausgabe in {ergebnis.log}",
                foreground=FARBEN["gruen"],
            ),
        )
        # Auf das Ende warten und den Exit-Code in dieselbe Logdatei schreiben -
        # das ist der Beleg, dass der Start echt war (und wann er endete).
        prozess = ergebnis.prozess
        if prozess is None:
            return
        try:
            code = prozess.wait()
        except OSError as e:  # pragma: no cover - nur bei Prozessverlust
            code = f"unbekannt ({type(e).__name__})"
        aktionen.ereignis_anhaengen(ergebnis.log, f"beendet (Code {code})")
        self.root.after(
            0,
            lambda: (
                self.anzeigen(),
                self.status.configure(
                    text=f"{z.ordner} beendet (Code {code}). Log: {ergebnis.log}",
                    foreground=FARBEN["matt"],
                ),
            ),
        )

    def _ruf(self, argv: list[str], was: str) -> None:
        """Ein Fenster/Programm starten - Fehler landen in der Statuszeile."""
        try:
            self.lauf(argv)
        except OSError as e:
            self.status.configure(
                text=f"{was}: {type(e).__name__}: {e}", foreground=FARBEN["rot"]
            )
            return
        self.status.configure(text=f"{was} gestartet", foreground=FARBEN["matt"])

    def _start_fertig(self, z: manifest.Zeile, ergebnis) -> None:
        self.status.configure(
            text=f"Startfehler bei {z.ordner}: {ergebnis.fehler}", foreground=FARBEN["rot"]
        )
