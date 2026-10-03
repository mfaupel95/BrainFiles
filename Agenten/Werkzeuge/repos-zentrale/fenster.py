"""Das Fenster der Zentrale: Bereiche, Filter, Skalierung, Aktionen je Zeile.

Der Baum hat drei Ebenen:

    BEREICH (REPOS · WERKSTATT · HANDEL)
      GRUPPE (STARTBAR · EINRICHTEN · NEU · NUR DOKU · FEHLT)
        Projektzeile

Darueber eine Kopfzeile (Titel, Summen, **Skalierung**), darunter die
Filterzeile (Suchfeld, Bereich, Gruppe, **Filterchips**), unter dem Baum zwei
Karten: links "Was dieses Projekt kann", rechts **"Handel"** - dort stehen fuer
eine Handels-Spur ihr Stand, der Testlauf (`--vorschau`) und das Scharfschalten.

Die Anzeigelogik (Gruppen, Bereiche, Filter, Summenzeile, Spaltenbreiten) steht
bewusst als reine Funktionen oben - sie ist ohne Fenster pruefbar. Die Klasse
`Fenster` baut nur zusammen, was quellen/scan/manifest/auswahl/handelstand
liefern, und rechnet nichts selbst.

Farben, Schrift, DPI und ttk-Stile kommen aus `Werkzeuge/fenster_design.py` -
dieselbe Quelle wie handelszentrale.py. Runde Ecken und die Karten kommen aus
`rund.py`.
"""

from __future__ import annotations

import importlib.util
import json
import queue
import subprocess
import threading
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk

import aktionen
import auswahl
import befehle
import einstellungen
import handelstand
import manifest
import pflege
import quellen
import rund
import scan

_spec = importlib.util.spec_from_file_location(
    "fenster_design", Path(__file__).resolve().parent.parent / "fenster_design.py")
design = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(design)

FARBEN = design.FARBEN
SCHRIFT_ART = design.SCHRIFT_ART
SCHRIFT_GROESSE = design.SCHRIFT_GROESSE
ABSTAND = design.ABSTAND

# Frist fuer einen Vorschau-Testlauf. Grosszuegig: viele Spuren holen Kerzen
# und Kurse ueber das Netz. Der Dauerlauf bricht seine Zyklen bei 700 s ab -
# von Hand will man nicht so lange warten, und ein haengender Lauf soll das
# Fenster nicht blockieren (er laeuft in einem eigenen Faden).
VORSCHAU_FRIST_S = 240


def schrift(rel=0, fett=False):
    """Schriftart dieser Ansicht: Basis + relative Groesse."""
    return design.schrift(SCHRIFT_GROESSE, rel, fett)


dpi_bewusst = design.dpi_bewusst


GRUPPEN_TITEL = {
    "startbar": "STARTBAR",
    "einrichten": "EINRICHTEN",
    "neu": "NEU",
    "kein_start": "KEIN EIGENER START",
    "doku": "NUR DOKU",
    "fehlt": "FEHLT",
}
ERKLAERUNG = {
    "startbar": "Befehl belegt, alles da",
    "einrichten": "es fehlt noch etwas",
    "neu": "ohne Eintrag im Manifest",
    "kein_start": "richtig so: wird geladen oder ist nur lesbar",
    "doku": "kein Programm, nur Text",
    "fehlt": "Eintrag ohne Ordner",
}
# Die Gruppen, die Aufmerksamkeit brauchen - sie faerben Titel und Summenzeile.
AUFFAELLIGE_GRUPPEN = ("fehlt", "neu")
ALLE_BEREICHE = "Alle Bereiche"

# Die Filterchips in Anzeige-Reihenfolge. Kurz halten: acht Chips muessen in
# eine Zeile passen, ohne das Fenster zu sprengen.
CHIPS = (
    "auffaellig", "startbar", "mit_start", "mit_bot",
    "fremd", "handel", "spuren", "scharf",
)

# Die Knopfreihe unten. Der Name ist der Schluessel in `self.knoepfe` - Tests
# und Aufrufer haengen daran.
KNOPF_REIHE = (
    ("ordner", "Ordner", "ordner", "Explorer im Projektordner"),
    ("terminal", "Terminal", "terminal", "Terminal im Projektordner"),
    ("start", "Starten", "starten", "der belegte Startbefehl, Ausgabe ins Log"),
    ("bot", "Bot", "bot_chat", "hermes -p <bot> chat im Projektordner"),
    ("doku", "Doku", "doku", "die README des Projekts"),
)


# ------------------------------------------------------------------ Anzeigelogik
def gruppen_titel(gruppe: str, anzahl: int) -> str:
    """Ueberschrift einer Gruppe, mit dem Hinweis in Klammern: STARTBAR (4)."""
    return f"{GRUPPEN_TITEL.get(gruppe, gruppe.upper())} ({anzahl})"


def bereich_titel(kennung: str, anzahl: int) -> str:
    """Ueberschrift eines Bereichs, mit der Zahl aller Zeilen darunter."""
    return f"{kennung} - {anzahl}"


def bereichs_pfad(z: manifest.Zeile) -> str:
    """Der Ort einer Zeile, wie er in der Detailspalte steht."""
    if z.repo is not None:
        return str(z.repo.pfad)
    return f"{quellen.bereich(z.wurzel)}/{z.ordner}"


def sichtbare_zeilen(
    zeilen: list[manifest.Zeile], suchtext: str, bereich: str = "", filter_=None
) -> list[manifest.Zeile]:
    """Filtern ueber Ordnername, Bot, Notiz, Art, Rolle und Pfad.

    `bereich` ist entweder leer/`ALLE_BEREICHE` oder der Name eines Bereichs
    (REPOS, WERKSTATT, HANDEL) - dann bleiben nur dessen Zeilen. `filter_` ist
    ein `auswahl.Filter` mit weiteren Kennzeichen; er wird mit Suchtext und
    Bereich ZUSAMMENgefuehrt (die alte Zwei-Argument-Form bleibt gueltig).
    """
    grund = filter_ or auswahl.Filter()
    zusammen = auswahl.Filter(
        text=(suchtext or grund.text),
        bereich=(bereich or grund.bereich),
        gruppe=grund.gruppe,
        kennzeichen=tuple(grund.kennzeichen),
    )
    return auswahl.filtern(zeilen, zusammen)


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


def fremde_zeilen(zeilen: list[manifest.Zeile]) -> list[manifest.Zeile]:
    """Zeilen in fremdem Material (Kennzeichen setzt manifest._zeile).

    Sie bleiben sichtbar - sie sollen ja auffindbar sein - aber sie werden
    gezaehlt ausgewiesen, damit 'unser Code' eine Zahl mit Bedeutung hat.
    """
    return [z for z in zeilen if any(g.startswith("fremd:") for g in z.gruende)]


def spuren_zeilen(zeilen: list[manifest.Zeile]) -> list[manifest.Zeile]:
    """Zeilen, die eine Handels-Spur sind (Kennzeichen setzt `_spuren_markieren`)."""
    return [z for z in zeilen if getattr(z, "spur", "")]


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


def spuren_markieren(zeilen: list[manifest.Zeile], plan: dict, stand: dict) -> dict:
    """Jeder Zeile sagen, ob sie eine Handels-Spur ist (und welche).

    Die Namen kommen aus `dauerlauf.SPUREN` - gelesen, nicht geraten. Ein Ordner
    kann MEHRERE Spuren tragen (`nautilus_kraken` faehrt den Spot-Arm und die
    Futures-Variante); deshalb ist `spuren` eine Liste und `spur` der erste Name.

    Rueckgabe: die Karte Ordner -> Spurnamen (fuer weitere Leser, z. B.
    `repos_zentrale.py --pruefen`). Reine Funktion - kein Fenster noetig.
    """
    karte: dict[str, list[str]] = {}
    for name, eintrag in plan.items():
        karte.setdefault(eintrag.get("ordner") or name, []).append(name)
    for z in zeilen:
        namen = karte.get(z.ordner) or [] if z.bereich == "HANDEL" else []
        z.spuren = list(namen)
        z.spur = namen[0] if namen else ""
        z.scharf = bool(namen and any((stand.get(n) or {}).get("scharf") for n in namen))
    return karte


def hinweis(zeile: manifest.Zeile) -> str:
    """Was in der Hinweisspalte steht: erst der Grund, sonst die Notiz."""
    if zeile.gruende:
        return "; ".join(zeile.gruende)
    if zeile.gruppe in ("doku", "neu", "fehlt"):
        return zeile.notiz
    return ""


def spur_kurz(z: manifest.Zeile) -> str:
    """Die Handels-Kennzeichnung einer Zeile fuer die eigene Spalte (leer, wenn keine Spur)."""
    if not getattr(z, "spur", ""):
        return ""
    return "scharf" if getattr(z, "scharf", False) else "Papier"


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
    ("handel", "Handel", 88),
    ("hinweis", "Hinweis", 320),
)
BREITE_PROJEKT = 250
SPALTEN_MINIMUM = 60


def spaltenbreiten(
    verfuegbar: int, s: float = 1.0, *, projekt: int = BREITE_PROJEKT, spalten=SPALTEN
) -> tuple[int, list[tuple[str, str, int]]]:
    """Spaltenbreiten fuer die verfuegbare Breite: erst skalieren, dann kuerzen.

    `verfuegbar` ist die Breite, die der Baum wirklich hat. Reicht sie nicht,
    wird in DIESER Reihenfolge gekuerzt: erst die Nebenspalten (Art, Rolle, Bot,
    letzter Start, Handel), dann die Projektspalte, zuletzt die Hinweisspalte -
    sie traegt den Grund und ist die einzige, deren Abschneiden Information
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


def bildschirmmasse(root) -> tuple[int, int]:
    """Die Bildschirmgroesse in Pixeln (Rueckfall 1920x1080)."""
    try:
        return root.winfo_screenwidth(), root.winfo_screenheight()
    except Exception:                                        # noqa: BLE001
        return 1920, 1080


def groesse_masse(bildschirm: tuple[int, int], name: str, s: float = 1.0) -> tuple[int, int]:
    """Die Pixelmasse eines Fenster-Presets, auf den Bildschirm begrenzt.

    Reine Rechnung (ohne Fenster pruefbar): Wunschgroesse aus
    `einstellungen.fenster_masse`, gestreckt mit dem DPI-Faktor, danach auf
    Bildschirm minus 80 px gedeckelt und nach unten auf 900x560 begrenzt - so
    liegt das Fenster auch auf einem kleinen Monitor vollstaendig im Bild.
    """
    breite, hoehe = einstellungen.fenster_masse(name, bildschirm)
    sw, sh = bildschirm
    b = max(int(900 * s), min(int(round(breite * s)), max(int(900 * s), sw - 80)))
    h = max(int(560 * s), min(int(round(hoehe * s)), max(int(560 * s), sh - 80)))
    return b, h


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
        einstellungen_pfad: Path | str | None = None,
        handel_zustand_lader=None,
        vorschau_lauf=None,
    ):
        self.brainfiles = Path(brainfiles)
        self.manifest_pfad = Path(manifest_pfad)
        self.profile_dir = Path(profile_dir)
        self.log_ordner = Path(log_ordner)
        self.einstellungen_pfad = Path(
            einstellungen_pfad or (self.manifest_pfad.parent / "einstellungen.json")
        )
        self.lauf = lauf or self._popen
        self.jetzt = jetzt or datetime.now
        self.handel_zustand_lader = handel_zustand_lader or (
            lambda: handelstand.zustand(self.brainfiles)
        )
        self.vorschau_lauf = vorschau_lauf or self._vorschau_echt
        self.zeilen: list[manifest.Zeile] = []
        self.kinder: dict[str, manifest.Zeile] = {}   # Item-Id -> Zeile

        self.einst = einstellungen.laden(self.einstellungen_pfad)
        self.schriftgroesse = int(self.einst["schrift"])
        self.kennzeichen: set[str] = set(self.einst["filter"])
        self._handel_da: dict | None = None
        self._handel_laeuft = False
        self._handel_gelesen = None       # Zeitpunkt des letzten Lesens
        self._handel_takt_ms = 60000      # Selbst-Nachziehen: 60 s
        self._handel_takt_an = True
        self._handel_takt_id = None
        self._vorschau_laeuft = False
        self._pflege_laeuft = False
        self._spurnamen: dict[str, list[str]] = {}
        self._plan: dict = {}          # dauerlauf.SPUREN, einmal gelesen
        # Aus einem Faden darf man NICHT `root.after` rufen (Tk ist nicht
        # threadsicher; ohne laufende Hauptschleife bricht es mit "main thread
        # is not in main loop" ab). Faeden legen ihren Aufruf hier ab, die
        # Hauptschleife holt ihn ab (`_post_pollen`).
        self._post: queue.Queue = queue.Queue()
        self._post_id = None           # der laufende after-Auftrag der Abholschleife

        dpi_bewusst()
        self.root = tk.Tk()
        self.s = design.skalierung(self.root)
        self.root.title("Zentrale · Repos · Werkstatt · Handel")
        rund.fenster_ecken(self.root)
        self.root.minsize(int(900 * self.s), int(560 * self.s))
        self._groesse_setzen(self.einst["fenster"], beim_start=True)
        self._bauen()
        self.aktualisieren()
        # Die Abholschleife fuer Faeden starten (siehe `_post_pollen`) und beim
        # Zerstoeren des Fensters wieder abbestellen (sonst meckert Tk).
        self.root.bind("<Destroy>", self._post_stoppen)
        self._post_id = self.root.after(80, self._post_pollen)

    # ------------------------------------------------------------- Aufbau
    def _stil(self) -> ttk.Style:
        """Alle Stile setzen - Grundstile UND Karten-Stile aus fenster_design.

        Die Karten haben eine eigene Flaeche (`blatt`); die Stile dafuer stehen
        seit 30.09.2026 in `fenster_design.karten_stile` (Praefix `Karte.`),
        damit Repos-Zentrale und Handelszentrale dieselben Karten zeigen.
        """
        st = ttk.Style()
        design.stil_anwenden(st, self.schriftgroesse)
        hoehe = self._zeilenhoehe()
        st.configure("Treeview", rowheight=hoehe)
        design.karten_stile(st, self.schriftgroesse, zeilenhoehe_px=hoehe)
        return st

    def _zeilenhoehe(self) -> int:
        """Zeilenhoehe aus Schrift und Dichte (die Dichte aendert nur den Abstand)."""
        grund = design.zeilenhoehe(self.schriftgroesse)
        return max(16, int(round(grund * einstellungen.dichte_faktor(self.einst["dichte"]))))

    def schrift(self, rel=0, fett=False):
        """Die Schrift DIESES Fensters (folgt dem Skalierungsregler)."""
        return design.schrift(self.schriftgroesse, rel, fett)

    def _bauen(self) -> None:
        self._stil()
        self.root.configure(background=FARBEN["bg"])
        self.knoepfe: dict[str, rund.RunderKnopf] = {}
        self.handel_knoepfe: dict[str, rund.RunderKnopf] = {}
        self.pflege_knoepfe: dict[str, rund.RunderKnopf] = {}
        self.chip_knoepfe: dict[str, rund.RunderKnopf] = {}
        self._alle_knoepfe: list[rund.RunderKnopf] = []
        self._karten: list[rund.Karte] = []

        self._bauen_kopf()
        self._bauen_filter()
        self._bauen_baum()
        self._bauen_karten()
        self._bauen_leiste()
        self.status = ttk.Label(self.root, text="", anchor="w", foreground=FARBEN["matt"])
        self.status.pack(fill="x", padx=ABSTAND["m"], pady=(0, ABSTAND["m"]))

        self.root.bind("<F5>", lambda _: self.aktualisieren())
        self.root.bind("<Control-f>", lambda _: self.suchfeld.focus_set())
        self.root.bind("<Return>", lambda _: self.starten())
        self.root.bind("<F7>", lambda _: self.pflege_pruefen())
        self.root.bind("<F9>", lambda _: self.handel_testen())
        self.root.bind("<F10>", lambda _: self.scharf_dialog())
        self.root.bind("<Control-plus>", lambda _: self.schrift_groesser())
        self.root.bind("<Control-equal>", lambda _: self.schrift_groesser())
        self.root.bind("<Control-minus>", lambda _: self.schrift_kleiner())
        self.root.bind("<Control-Key-0>", lambda _: self.schrift_setzen(SCHRIFT_GROESSE))
        self.root.bind("<Control-MouseWheel>", self._mausrad)
        self.root.bind("<Escape>", lambda _: self.suchtext.set(""))
        self.root.protocol("WM_DELETE_WINDOW", self._schliessen)

    # ------------------------------------------------------------- Kopfzeile
    def _bauen_kopf(self) -> None:
        kopf = tk.Frame(self.root, background=FARBEN["bg"])
        kopf.pack(fill="x", padx=ABSTAND["m"], pady=(ABSTAND["m"], ABSTAND["s"]))

        links = tk.Frame(kopf, background=FARBEN["bg"])
        links.pack(side="left")
        ttk.Label(links, text="Zentrale", foreground=FARBEN["akzent"],
                  font=self.schrift(design.TITEL, True)).pack(side="left")
        ttk.Label(links, text="  Repos · Werkstatt · Handel", foreground=FARBEN["matt"],
                  font=self.schrift(-1)).pack(side="left", pady=(6, 0))

        rechts = tk.Frame(kopf, background=FARBEN["bg"])
        rechts.pack(side="right")
        self.zusammenfassung = ttk.Label(rechts, text="", foreground=FARBEN["akzent"])
        self.zusammenfassung.pack(side="right", padx=(ABSTAND["m"], 0))
        self._bauen_skalierung(rechts)

    def _bauen_skalierung(self, eltern) -> None:
        """Schrift, Dichte, Fenstergroesse - die Skalierungsoptionen."""
        rahmen = tk.Frame(eltern, background=FARBEN["bg"])
        rahmen.pack(side="right")

        self._knopf(rahmen, "schrift_minus", "−", self.schrift_kleiner,
                    variante="flach", breite=int(30 * self.s),
                    hinweis="Schrift kleiner (Strg-Minus)").pack(side="left")
        self.schrift_label = ttk.Label(rahmen, text="", width=6, anchor="center",
                                       foreground=FARBEN["text"])
        self.schrift_label.pack(side="left")
        self._knopf(rahmen, "schrift_plus", "+", self.schrift_groesser,
                    variante="flach", breite=int(30 * self.s),
                    hinweis="Schrift groesser (Strg-Plus)").pack(side="left")

        ttk.Label(rahmen, text="Dichte", foreground=FARBEN["matt"]).pack(
            side="left", padx=(ABSTAND["l"], ABSTAND["xs"]))
        self.dichte = tk.StringVar(value=self.einst["dichte"])
        dichte_wahl = ttk.Combobox(rahmen, textvariable=self.dichte, state="readonly",
                                   width=9, values=tuple(einstellungen.DICHTEN))
        dichte_wahl.pack(side="left")
        dichte_wahl.bind("<<ComboboxSelected>>", lambda _: self.dichte_setzen(self.dichte.get()))

        ttk.Label(rahmen, text="Fenster", foreground=FARBEN["matt"]).pack(
            side="left", padx=(ABSTAND["l"], ABSTAND["xs"]))
        self.groesse = tk.StringVar(value=self.einst["fenster"])
        groesse_wahl = ttk.Combobox(rahmen, textvariable=self.groesse, state="readonly",
                                    width=11, values=tuple(einstellungen.FENSTERGROESSEN))
        groesse_wahl.pack(side="left")
        groesse_wahl.bind("<<ComboboxSelected>>", lambda _: self.groesse_setzen(self.groesse.get()))
        self._schrift_anzeigen()

    # ------------------------------------------------------------- Filterzeile
    def _bauen_filter(self) -> None:
        zeile = tk.Frame(self.root, background=FARBEN["bg"])
        zeile.pack(fill="x", padx=ABSTAND["m"])
        ttk.Label(zeile, text="Filtern:").pack(side="left")
        self.suchtext = tk.StringVar(value=self.einst.get("text", ""))
        self.suchtext.trace_add("write", lambda *_: self.anzeigen())
        self.suchfeld = ttk.Entry(zeile, textvariable=self.suchtext, width=28)
        self.suchfeld.pack(side="left", padx=ABSTAND["s"])

        ttk.Label(zeile, text="Bereich:").pack(side="left", padx=(ABSTAND["m"], 0))
        self.bereich = tk.StringVar(value=ALLE_BEREICHE)
        self.bereich_wahl = ttk.Combobox(zeile, textvariable=self.bereich, state="readonly",
                                         width=18, values=(ALLE_BEREICHE,))
        self.bereich_wahl.pack(side="left", padx=ABSTAND["s"])
        self.bereich_wahl.bind("<<ComboboxSelected>>", lambda _: self.anzeigen())

        ttk.Label(zeile, text="Gruppe:").pack(side="left", padx=(ABSTAND["m"], 0))
        self.gruppe = tk.StringVar(value=auswahl.ALLE_GRUPPEN)
        self.gruppe_wahl = ttk.Combobox(zeile, textvariable=self.gruppe, state="readonly",
                                        width=16, values=(auswahl.ALLE_GRUPPEN,))
        self.gruppe_wahl.pack(side="left", padx=ABSTAND["s"])
        self.gruppe_wahl.bind("<<ComboboxSelected>>", lambda _: self.anzeigen())

        self._knopf(zeile, "aktualisieren", "Aktualisieren (F5)", self.aktualisieren,
                    hinweis="Platte und Manifest neu lesen").pack(side="left", padx=ABSTAND["s"])
        self._knopf(zeile, "filter_aus", "Filter aus", self.filter_zuruecksetzen,
                    variante="flach",
                    hinweis="Suchtext, Bereich, Gruppe und Chips zuruecksetzen"
                    ).pack(side="left", padx=ABSTAND["xs"])

        chips = tk.Frame(self.root, background=FARBEN["bg"])
        chips.pack(fill="x", padx=ABSTAND["m"], pady=(ABSTAND["xs"], ABSTAND["s"]))
        ttk.Label(chips, text="nur zeigen:", foreground=FARBEN["matt"],
                  font=self.schrift(-1)).pack(side="left", padx=(0, ABSTAND["s"]))
        for kennung in CHIPS:
            knopf = self._knopf(
                chips, f"chip_{kennung}", auswahl.KENNZEICHEN_TITEL.get(kennung, kennung),
                lambda k=kennung: self.kennzeichen_umschalten(k),
                variante="flach",
                hinweis=f"Filter: {auswahl.KENNZEICHEN_TITEL.get(kennung, kennung)}",
            )
            knopf.pack(side="left", padx=ABSTAND["xs"])
            self.chip_knoepfe[kennung] = knopf
        self._chips_anzeigen()

    # ------------------------------------------------------------- Baum
    def _bauen_baum(self) -> None:
        tabelle = ttk.Frame(self.root)
        tabelle.pack(fill="both", expand=True, padx=ABSTAND["m"])
        self.baum = ttk.Treeview(
            tabelle,
            columns=tuple(k for k, _, _ in SPALTEN),
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
        self.baum.tag_configure("spur_scharf", foreground=FARBEN["gruen"])
        self.baum.pack(side="left", fill="both", expand=True)
        rollbalken = ttk.Scrollbar(tabelle, orient="vertical", command=self.baum.yview)
        rollbalken.pack(side="right", fill="y")
        self.baum.configure(yscrollcommand=rollbalken.set)
        self.baum.bind("<<TreeviewSelect>>", lambda _: self._auswahl_geaendert())
        self.baum.bind("<Double-Button-1>", lambda _: self.doppelklick())
        # Die Spaltenbreiten folgen der WIRKLICHEN Breite des Baums: nur so
        # passen Schrift (DPI) und Spalten auf jedem Monitor zusammen.
        self.baum.bind("<Configure>", self._spalten_setzen)

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
            spalten = [(k, t, b + rest if k == "hinweis" else b) for k, t, b in spalten]
        self.baum.column("#0", width=projekt)
        for kennung, _titel, breite in spalten:
            self.baum.column(kennung, width=breite)

    # ------------------------------------------------------------- Karten
    def _bauen_karten(self) -> None:
        """Zwei Karten nebeneinander: das Projekt und der Handelsteil.

        Ein `tk.PanedWindow` (nicht ttk) - nur so lassen sich die Canvas-Karten
        als Scheiben einsetzen, und die Teilung laesst sich ziehen.
        """
        self.teilung = tk.PanedWindow(
            self.root, orient="horizontal", sashwidth=6, bd=0,
            background=FARBEN["bg"], sashrelief="flat",
        )
        self.teilung.pack(fill="both", expand=False, padx=ABSTAND["m"],
                          pady=(ABSTAND["s"], 0))
        self._bauen_karte_projekt()
        self._bauen_karte_rechts()

    def _karte(self, titel: str, hoehe: int, breite: int) -> rund.Karte:
        """Eine Karte bauen. `breite` ist die Wunschbreite im PanedWindow.

        Ohne eigene Breite nehmen beide Karten die Tk-Vorgabe (378 px) - die
        Teilung startete dann bei zwei schmalen Scheiben, obwohl das Fenster
        1750 px breit ist. Die Breite bestimmt hier den ANFANGS-Schnitt; ziehen
        laesst er sich danach frei.
        """
        karte = rund.Karte(self.teilung, titel=titel, farben=FARBEN,
                           schrift_tupel=self.schrift(),
                           radius=design.KARTE["radius"],
                           rand=design.KARTE["innen"],
                           hoehe=int(hoehe * self.s), breite=int(breite * self.s))
        self._karten.append(karte)
        return karte

    def _bauen_karte_projekt(self) -> None:
        """Links: Ablauf in Worten + anklickbare Befehle."""
        karte = self._karte("Was dieses Projekt kann", 205, 1000)
        self.teilung.add(karte, minsize=int(320 * self.s), stretch="always")

        links = tk.Frame(karte.inhalt, background=FARBEN["blatt"])
        links.pack(side="left", fill="both", expand=True, padx=(0, 3))
        self.anleitung_text = tk.Text(
            links, height=8, width=38, wrap="word", relief="flat",
            background=FARBEN["blatt"], foreground=FARBEN["text"],
            insertbackground=FARBEN["text"], selectbackground=FARBEN["auswahl"],
            font=self.schrift(), borderwidth=0, highlightthickness=0,
        )
        self.anleitung_text.pack(side="left", fill="both", expand=True)
        self.anleitung_text.configure(state="disabled")
        leiste = ttk.Scrollbar(links, orient="vertical", command=self.anleitung_text.yview)
        leiste.pack(side="right", fill="y")
        self.anleitung_text.configure(yscrollcommand=leiste.set)

        rechts = tk.Frame(karte.inhalt, background=FARBEN["blatt"])
        rechts.pack(side="left", fill="both", expand=True, padx=(3, 0))
        self.befehlsbaum = ttk.Treeview(
            rechts, columns=("was", "befehl", "hinweis"), show="headings",
            selectmode="browse", style="Karte.Treeview",
        )
        for spalte, titel, breite in (
            ("was", "Was", 130), ("befehl", "Befehl", 170), ("hinweis", "Hinweis", 110),
        ):
            self.befehlsbaum.heading(spalte, text=titel)
            self.befehlsbaum.column(spalte, width=breite, anchor="w")
        self.befehlsbaum.pack(side="left", fill="both", expand=True)
        self.befehlsbaum.bind("<Double-Button-1>", lambda _: self.befehl_ausfuehren())
        self.befehlsbaum.bind("<<TreeviewSelect>>", lambda _: self._befehl_gewaehlt())
        rollbalken = ttk.Scrollbar(rechts, orient="vertical", command=self.befehlsbaum.yview)
        rollbalken.pack(side="right", fill="y")
        self.befehlsbaum.configure(yscrollcommand=rollbalken.set)

        leiste2 = tk.Frame(karte.inhalt, background=FARBEN["blatt"])
        leiste2.pack(side="left", fill="y", padx=(3, 0))
        self.befehl_knoepfe = {}
        for name, text, befehl, hinweis in (
            ("ausfuehren", "Befehl ausfuehren", self.befehl_ausfuehren,
             "im Terminal im Projektordner, Ausgabe ins Log"),
            ("kopieren", "Befehl kopieren", self.befehl_kopieren, "in die Zwischenablage"),
            ("bot", "Bot damit beauftragen", self.befehl_an_bot,
             "der Repo-Bot fuehrt aus und erklaert"),
        ):
            knopf = self._knopf(leiste2, f"befehl_{name}", text, befehl,
                                variante="flach", hinweis=hinweis)
            knopf.pack(side="top", fill="x", pady=ABSTAND["xs"])
            self.befehl_knoepfe[name] = knopf
        self.befehl_kinder: dict[str, befehle.Kommando] = {}

    def _bauen_karte_rechts(self) -> None:
        """Rechts zwei Reiter: der Handelsteil und die Pflege.

        Ein Notebook, weil beide Teile dasselbe Fensterstueck brauchen und
        selten gleichzeitig wichtig sind: der Handelsteil gilt nur fuer Spuren,
        die Pflege (einrichten, bauen, pruefen) fuer jedes Projekt.
        """
        karte = self._karte("Handel · Pflege", 205, 700)
        self.teilung.add(karte, minsize=int(320 * self.s), stretch="always")

        self.reiter = ttk.Notebook(karte.inhalt, style="Karte.TNotebook")
        self.reiter.pack(fill="both", expand=True)
        handel = tk.Frame(self.reiter, background=FARBEN["blatt"])
        pflege_rahmen = tk.Frame(self.reiter, background=FARBEN["blatt"])
        self.reiter.add(handel, text="Handel · Testen")
        self.reiter.add(pflege_rahmen, text="Einrichten · Reparatur")
        self._bauen_reiter_handel(handel)
        self._bauen_reiter_pflege(pflege_rahmen)

    def _bauen_reiter_handel(self, eltern) -> None:
        """Der Handelsteil: Stand der Spur, Testlauf, Scharfschalten."""
        self.handel_kopf = tk.Label(
            eltern, text="", anchor="w", justify="left",
            background=FARBEN["blatt"], foreground=FARBEN["text"], font=self.schrift(),
        )
        self.handel_kopf.pack(fill="x")

        leiste = tk.Frame(eltern, background=FARBEN["blatt"])
        leiste.pack(fill="x", pady=(ABSTAND["xs"], ABSTAND["xs"]))
        for name, text, befehl, variante, hinweis in (
            ("test", "Vorschau testen (F9)", self.handel_testen, "normal",
             "handeln.py --vorschau mit MAXHIRN_ROUTINE=1 - der einzige Beleg fuer den Modus"),
            ("stand", "Stand neu lesen", self.handel_neu_laden, "flach",
             "Buch, Fenster und Schalter der Spuren neu von der Platte lesen"),
            ("scharf", "Scharf schalten ...", self.scharf_dialog, "warnung",
             "Fenster mit Checkliste und Bestaetigung (F10)"),
            ("entschaerfen", "Entschaerfen", self.entschaerfen, "gefahr",
             "handel_erlaubt auf false - der Haken freigabe.erfuellt bleibt stehen"),
            ("auto", "Auto: an", self.handel_takt_umschalten, "flach",
             "den Stand alle 60 s selbst nachziehen (nur solange der Reiter sichtbar ist)"),
        ):
            knopf = self._knopf(leiste, f"handel_{name}", text, befehl,
                                variante=variante, hinweis=hinweis)
            knopf.pack(side="left", padx=(0, ABSTAND["xs"]))
            self.handel_knoepfe[name] = knopf

        self.handel_text = tk.Text(
            eltern, height=6, wrap="word", relief="flat",
            background=FARBEN["blatt"], foreground=FARBEN["matt"],
            insertbackground=FARBEN["text"], selectbackground=FARBEN["auswahl"],
            font=self.schrift(-1), borderwidth=0, highlightthickness=0,
        )
        self.handel_text.pack(fill="both", expand=True)
        self.handel_text.configure(state="disabled")

    def _bauen_reiter_pflege(self, eltern) -> None:
        """Einrichten, bauen, pruefen und reparieren - je Projekt."""
        self.pflege_kopf = tk.Label(
            eltern, text="", anchor="w", justify="left", wraplength=1,
            background=FARBEN["blatt"], foreground=FARBEN["text"], font=self.schrift(),
        )
        self.pflege_kopf.pack(fill="x")

        leiste = tk.Frame(eltern, background=FARBEN["blatt"])
        leiste.pack(fill="x", pady=(ABSTAND["xs"], ABSTAND["xs"]))
        for name, text, befehl, variante, hinweis in (
            ("pruefen", "Pruefen (F7)", self.pflege_pruefen, "normal",
             "Zustand messen: venv, node_modules, Pflichtpfad, Git, Bot, Port - rein lesend"),
            ("einrichten", "Einrichten", self.pflege_einrichten, "haupt",
             "die Einrichtungsschritte ausfuehren (Manifest oder aus package.json/requirements.txt)"),
            ("bauen", "Bauen", self.pflege_bauen, "haupt",
             "den Bau-Schritt ausfuehren (Cargo.toml, go.mod, npm run build, Makefile)"),
            ("alle", "Alles pruefen", self.pflege_alle, "flach",
             "alle Projekte messen und einen Pruefbericht nach logs/ schreiben"),
        ):
            knopf = self._knopf(leiste, f"pflege_{name}", text, befehl,
                                variante=variante, hinweis=hinweis)
            knopf.pack(side="left", padx=(0, ABSTAND["xs"]))
            self.pflege_knoepfe[name] = knopf

        self.pflege_text = tk.Text(
            eltern, height=6, wrap="word", relief="flat",
            background=FARBEN["blatt"], foreground=FARBEN["matt"],
            insertbackground=FARBEN["text"], selectbackground=FARBEN["auswahl"],
            font=self.schrift(-1), borderwidth=0, highlightthickness=0,
        )
        self.pflege_text.pack(fill="both", expand=True)
        self.pflege_text.configure(state="disabled")

    def _bauen_leiste(self) -> None:
        unten = tk.Frame(self.root, background=FARBEN["bg"])
        unten.pack(fill="x", padx=ABSTAND["m"], pady=ABSTAND["m"])
        for name, text, methode, hinweis in KNOPF_REIHE:
            knopf = self._knopf(unten, name, text, getattr(self, methode), hinweis=hinweis)
            knopf.pack(side="left", padx=ABSTAND["xs"])
            self.knoepfe[name] = knopf
        self._knopf(unten, "log", "Log", self._log_oeffnen,
                    variante="flach", hinweis="den letzten Startbeleg oeffnen").pack(
            side="left", padx=(ABSTAND["l"], ABSTAND["xs"]))
        self._knopf(unten, "wiki", "Wiki", self._wiki,
                    variante="flach", hinweis="die Hausdoku dieses Werkzeugs").pack(
            side="left", padx=ABSTAND["xs"])

    def _knopf(self, eltern, name, text, befehl, *, variante="normal", breite=None,
               hinweis="") -> rund.RunderKnopf:
        """Einen runden Knopf bauen und im Register `_alle_knoepfe` merken.

        Gemerkt wird er, damit die Skalierung ihn wiederfindet: aendert sich die
        Schriftgroesse, muss JEDER Knopf neu gezeichnet werden - ein vergessener
        bliebe in der alten Groesse stehen.
        """
        knopf = rund.RunderKnopf(
            eltern, text, befehl, variante=variante, farben=FARBEN,
            schrift_tupel=self.schrift(), breite=breite,
            padx=int(9 * self.s), pady=int(4 * self.s), radius=int(rund.RADIUS * self.s),
            hinweis=hinweis,
        )
        knopf.bei_hinweis = self._hinweis_zeigen
        self._alle_knoepfe.append(knopf)
        return knopf

    def _hinweis_zeigen(self, text: str) -> None:
        """Beim Zeigen auf einen Knopf seinen Hinweis in die Statuszeile schreiben."""
        if not hasattr(self, "status"):
            return
        if text:
            self.status.configure(text=text, foreground=FARBEN["matt"])

    # ------------------------------------------------------------- Faden -> Hauptschleife
    def _nach_main(self, aufruf) -> None:
        """Einen Aufruf aus einem Faden in die Hauptschleife schieben."""
        self._post.put(aufruf)

    def _post_pollen(self) -> None:
        """Alle wartenden Aufrufe aus Faeden abarbeiten (im Hauptfaden).

        Der Takt ist 80 ms - schnell genug, dass ein fertiger Testlauf sofort
        erscheint, und selten genug, dass er nichts kostet. Beim Schliessen des
        Fensters wird der Auftrag abbestellt (`_post_stoppen`); sonst ruft Tk
        ihn nach dem Zerstoeren auf und schreibt "invalid command name" auf die
        Fehlerausgabe.
        """
        while True:
            try:
                aufruf = self._post.get_nowait()
            except queue.Empty:
                break
            try:
                aufruf()
            except Exception:                                # noqa: BLE001
                pass
        try:
            self._post_id = self.root.after(80, self._post_pollen)
        except Exception:                                    # noqa: BLE001
            self._post_id = None

    def _post_stoppen(self, ereignis=None) -> None:
        """Den Abholauftrag abbestellen - beim Zerstoeren des Fensters."""
        if ereignis is not None and getattr(ereignis, "widget", None) is not self.root:
            return
        if self._post_id is not None:
            try:
                self.root.after_cancel(self._post_id)
            except Exception:                                # noqa: BLE001
                pass
            self._post_id = None

    # ------------------------------------------------------------- Skalierung
    def _schrift_anzeigen(self) -> None:
        if hasattr(self, "schrift_label"):
            self.schrift_label.configure(text=f"{self.schriftgroesse} pt")

    def schrift_setzen(self, groesse: int) -> None:
        """Schriftgroesse setzen (8..16) und alles neu zeichnen."""
        neu = max(einstellungen.SCHRIFT_MIN, min(einstellungen.SCHRIFT_MAX, int(groesse)))
        if neu == self.schriftgroesse:
            return
        self.schriftgroesse = neu
        self._ansicht_erneuern()

    def schrift_groesser(self) -> None:
        self.schrift_setzen(self.schriftgroesse + 1)

    def schrift_kleiner(self) -> None:
        self.schrift_setzen(self.schriftgroesse - 1)

    def _mausrad(self, ereignis) -> None:
        """Strg-Mausrad: zoomen (nach oben groesser)."""
        self.schrift_setzen(self.schriftgroesse + (1 if ereignis.delta > 0 else -1))

    def dichte_setzen(self, name: str) -> None:
        """Zeilenabstand umstellen (Schrift bleibt)."""
        self.einst["dichte"] = name if name in einstellungen.DICHTEN else "normal"
        self.dichte.set(self.einst["dichte"])
        self._ansicht_erneuern()

    def groesse_setzen(self, name: str) -> None:
        """Fenstergroesse umstellen (Vorgabe-Presets)."""
        self.einst["fenster"] = name if name in einstellungen.FENSTERGROESSEN else "mittel"
        self.groesse.set(self.einst["fenster"])
        self._groesse_setzen(self.einst["fenster"])
        self._speichern()

    def _groesse_setzen(self, name: str, *, beim_start: bool = False) -> None:
        if beim_start:
            breite, hoehe = einstellungen.fenster_masse(name, bildschirmmasse(self.root))
            self.root.geometry(fenstergroesse(self.root, breite, hoehe, self.s))
            return
        b, h = groesse_masse(bildschirmmasse(self.root), name, self.s)
        self.root.geometry(f"{b}x{h}")

    def _ansicht_erneuern(self) -> None:
        """Nach einer Skalierungsaenderung: Stile, Schriften, Breiten, Anzeige."""
        self._stil()
        for knopf in self._alle_knoepfe:
            knopf.schrift_tupel = self.schrift()
            knopf.radius = int(rund.RADIUS * self.s)
            knopf.zeichnen()
        for karte in self._karten:
            karte.schrift_tupel = self.schrift()
            karte.zeichnen()
        self.anleitung_text.configure(font=self.schrift())
        self.handel_text.configure(font=self.schrift(-1))
        self.pflege_text.configure(font=self.schrift(-1))
        self._schrift_anzeigen()
        self.anzeigen()
        self._handel_anzeigen()
        self._speichern()

    def _speichern(self) -> None:
        """Den Stand der Ansicht sichern (Laufzeitstand, nicht versioniert)."""
        self.einst.update({
            "schrift": self.schriftgroesse,
            "dichte": self.dichte.get(),
            "fenster": self.groesse.get(),
            "bereich": self.bereich.get(),
            "gruppe": self.gruppe.get(),
            "filter": sorted(self.kennzeichen),
            "text": self.suchtext.get(),
        })
        einstellungen.speichern(self.einstellungen_pfad, self.einst)

    def _schliessen(self) -> None:
        self._speichern()
        self.root.destroy()

    # ------------------------------------------------------------- Filter
    def kennzeichen_umschalten(self, kennung: str) -> None:
        """Einen Filterchip an- oder ausschalten."""
        if kennung in self.kennzeichen:
            self.kennzeichen.discard(kennung)
        else:
            self.kennzeichen.add(kennung)
            if kennung in ("scharf", "spuren") and self._handel_da is None:
                self._handel_im_hintergrund()
        self._chips_anzeigen()
        self.anzeigen()
        self._speichern()

    def _chips_anzeigen(self) -> None:
        for kennung, knopf in self.chip_knoepfe.items():
            knopf.setze_variante("haupt" if kennung in self.kennzeichen else "flach")

    def filter_zuruecksetzen(self) -> None:
        """Suchtext, Bereich, Gruppe und Chips auf Anfang stellen."""
        self.suchtext.set("")
        self.bereich.set(ALLE_BEREICHE)
        self.gruppe.set(auswahl.ALLE_GRUPPEN)
        self.kennzeichen.clear()
        self._chips_anzeigen()
        self.anzeigen()
        self._speichern()

    def _filter(self) -> auswahl.Filter:
        return auswahl.Filter(
            text=self.suchtext.get(), bereich=self.bereich.get(),
            gruppe=self.gruppe.get(), kennzeichen=tuple(sorted(self.kennzeichen)),
        )

    # ------------------------------------------------------------- Daten
    def aktualisieren(self) -> None:
        """Platte und Manifest neu lesen (Knopf 'Aktualisieren')."""
        plaetze = [
            (w, scan.tief_scannen(w, pfad))
            for w, pfad in quellen.alle(self.brainfiles)
        ]
        eintraege = manifest.manifest_laden(self.manifest_pfad)
        self.zeilen = manifest.zeilen_bauen(plaetze, eintraege, self.profile_dir)
        # Den Laufplan EINMAL lesen (Datei + ast) und merken: `anzeigen()` laeuft
        # bei jedem Tastendruck im Suchfeld und darf keine Datei lesen.
        self._plan = handelstand.laufplan(self.brainfiles)
        self._spuren_markieren()

        namen = [ALLE_BEREICHE] + [
            f"{k} ({sum(len(g) for g in gruppen.values())})"
            for k, gruppen in nach_bereichen(self.zeilen).items()
        ]
        self.bereich_wahl.configure(values=tuple(namen))
        if self.bereich.get() not in namen:
            self.bereich.set(ALLE_BEREICHE)
        gruppen = [auswahl.ALLE_GRUPPEN] + [
            gruppen_titel(g, 0).split(" (")[0]
            for g in manifest.GRUPPEN_REIHENFOLGE
            if any(z.gruppe == g for z in self.zeilen)
        ]
        self.gruppe_wahl.configure(values=tuple(gruppen))
        if self.gruppe.get() not in gruppen:
            self.gruppe.set(auswahl.ALLE_GRUPPEN)

        self.anzeigen()
        self.uebersicht = zusammenfassung(self.zeilen)
        self.status.configure(
            text=f"{sum(len(r) for _, r in plaetze)} Ordner auf der Platte, "
                 f"{len(eintraege)} Manifest-Eintraege | {self.uebersicht} | "
                 f"{self.manifest_pfad}"
        )

    def _spuren_markieren(self) -> None:
        """Die Spurkennzeichen an die Zeilen schreiben (reine Rechnung in `spuren_markieren`)."""
        self._spurnamen = spuren_markieren(self.zeilen, self._plan, self._handel_da or {})

    def anzeigen(self) -> None:
        """Die gefilterten Zeilen in den Baum schreiben (Bereich -> Gruppe)."""
        # Erst die Spurkennzeichen auffrischen: seit dem Laden des Handelsstands
        # kann eine Spur scharf sein, und der Chip 'scharf' und die Farbe der
        # Zeile haengen daran. Die Rechnung ist billig (gemerkter Laufplan).
        self._spuren_markieren()
        self.baum.delete(*self.baum.get_children())
        self.kinder.clear()
        wahl = self.bereich.get().split(" (")[0]
        sichtbar = sichtbare_zeilen(self.zeilen, self.suchtext.get(), wahl, self._filter())
        for kennung, gruppen in nach_bereichen(sichtbar).items():
            anzahl = sum(len(g) for g in gruppen.values())
            kopf = self.baum.insert(
                "", "end", text=bereich_titel(kennung, anzahl), open=True,
                values=("", "", "", "", "", quellen.BEREICH_ERKLAERUNG.get(kennung, "")),
                tags=("bereich",),
            )
            for name, zeilen in gruppen.items():
                gruppe = self.baum.insert(
                    kopf, "end", text=gruppen_titel(name, len(zeilen)), open=name != "doku",
                    values=("", "", "", "", "", ERKLAERUNG.get(name, "")),
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
                            spur_kurz(z) or "-",
                            hinweis(z),
                        ),
                        tags=(self._farbe(z),),
                    )
                    self.kinder[item] = z
        beschreibung = auswahl.beschreibung(self._filter())
        self.zusammenfassung.configure(
            text=f"{len(sichtbar)} von {len(self.zeilen)} Zeilen"
            + (f" · {beschreibung}" if beschreibung else "")
        )
        self._details_fuellen(None)
        self._handel_anzeigen()
        self._pflege_anzeigen()

    def _farbe(self, z: manifest.Zeile) -> str:
        """Farbmarke einer Zeile - Zustand, nie Dekoration."""
        if z.gruppe == "fehlt":
            return "fehlt"
        if getattr(z, "scharf", False):
            return "spur_scharf"
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
        auswahl_ = self.baum.selection()
        if not auswahl_:
            return None
        return self.kinder.get(auswahl_[0])

    # ------------------------------------------------------------- Handelsteil
    def handel_zustand(self, *, neu: bool = False) -> dict:
        """Der Stand aller Spuren (erst beim ersten Bedarf geladen).

        Das Laden liest `spuren_stand.sammle()` - das laeuft ueber alle
        Spurordner und braucht ein paar Sekunden. Es passiert deshalb NICHT beim
        Aufbau des Fensters, sondern wenn jemand den Handelsteil braucht.
        """
        if neu:
            self._handel_da = None
        if self._handel_da is None:
            self._handel_da = self.handel_zustand_lader() or {}
            # Jetzt ist bekannt, welche Spur scharf ist - die Kennzeichen der
            # Zeilen nachziehen (der Chip 'scharf' und die Zeilenfarbe haengen
            # daran). Reine Rechnung, kein Dateizugriff.
            if self.zeilen:
                self._spuren_markieren()
        return self._handel_da

    def handel_neu_laden(self) -> None:
        """Den Stand im Hintergrund neu lesen (Knopf 'Stand neu lesen')."""
        self._handel_im_hintergrund(neu=True)

    def _handel_im_hintergrund(self, *, neu: bool = False, leise: bool = False) -> None:
        if self._handel_laeuft:
            return
        self._handel_laeuft = True
        if not leise:
            self.status.configure(text="Handelsstand wird gelesen ...",
                                  foreground=FARBEN["matt"])

        def arbeit():
            daten = {}
            try:
                daten = self.handel_zustand(neu=neu)
            except Exception as e:                           # noqa: BLE001
                self._nach_main(lambda: self.status.configure(
                    text=f"Handelsstand nicht lesbar: {type(e).__name__}: {e}",
                    foreground=FARBEN["rot"]))
            self._nach_main(lambda: self._handel_fertig(daten, leise=leise))

        threading.Thread(target=arbeit, daemon=True).start()

    def _handel_fertig(self, daten: dict, leise: bool = False) -> None:
        self._handel_laeuft = False
        self._handel_gelesen = datetime.now()
        self._spuren_markieren()
        self.anzeigen()
        if leise:
            self.status.configure(
                text=f"Stand im Hintergrund nachgezogen ({self._handel_gelesen:%H:%M:%S})",
                foreground=FARBEN["matt"])
        else:
            self.status.configure(
                text=f"Handelsstand gelesen: {len(daten)} Spuren "
                     f"({sum(1 for d in daten.values() if d.get('scharf'))} mit Orderweg und Schalter)",
                foreground=FARBEN["matt"])
        self.handel_takt_starten()

    # ------------------------------------------- Selbst-Nachziehen (Takt)
    def handel_takt_starten(self) -> None:
        """Das Nachziehen neu aufziehen (nach jedem Lauf, nicht parallel)."""
        self.handel_takt_stoppen()
        if not self._handel_takt_an:
            return
        try:
            self._handel_takt_id = self.root.after(self._handel_takt_ms, self._handel_takt)
        except Exception:                                    # noqa: BLE001
            self._handel_takt_id = None

    def handel_takt_stoppen(self) -> None:
        if self._handel_takt_id is not None:
            try:
                self.root.after_cancel(self._handel_takt_id)
            except Exception:                                # noqa: BLE001
                pass
            self._handel_takt_id = None

    def _handel_takt(self) -> None:
        """Ein Takt: nur lesen, wenn die Handels-Karte auch zu sehen ist.

        Sonst kostet der Lauf alle 60 s ein paar Sekunden, ohne dass ihn jemand
        liest. Der Takt zieht sich danach selbst wieder auf.
        """
        self._handel_takt_id = None
        if self._handel_takt_an and self._handel_sichtbar() and not self._handel_laeuft:
            self._handel_im_hintergrund(neu=True, leise=True)
        else:
            self.handel_takt_starten()

    def _handel_sichtbar(self) -> bool:
        """Steht die Handels-Karte gerade im Vordergrund?"""
        try:
            return self.reiter.index(self.reiter.select()) == 0
        except Exception:                                    # noqa: BLE001
            return False

    def handel_takt_umschalten(self) -> None:
        """Selbst-Nachziehen an- oder abschalten."""
        self._handel_takt_an = not self._handel_takt_an
        knopf = self.handel_knoepfe.get("auto")
        if knopf is not None:
            knopf.setze_text("Auto: an" if self._handel_takt_an else "Auto: aus")
        if self._handel_takt_an:
            self.handel_takt_starten()
            self.status.configure(
                text=f"Der Stand wird alle {self._handel_takt_ms // 1000} s selbst "
                     "nachgezogen, solange dieser Reiter sichtbar ist.",
                foreground=FARBEN["matt"])
        else:
            self.handel_takt_stoppen()
            self.status.configure(
                text="Selbst-Nachziehen aus - 'Stand neu lesen' holt ihn von Hand.",
                foreground=FARBEN["matt"])

    def _handel_anzeigen(self) -> None:
        """Die Handels-Karte auf die gewaehlte Zeile umstellen."""
        if not hasattr(self, "handel_text"):
            return
        z = self._gewaehlt()
        spur = getattr(z, "spur", "") if z is not None else ""
        self.handel_text.configure(state="normal")
        self.handel_text.delete("1.0", "end")
        if z is None:
            self.handel_kopf.configure(text="Links eine Zeile waehlen.",
                                       foreground=FARBEN["text"])
        elif not spur:
            self.handel_kopf.configure(text="Keine Handels-Spur.", foreground=FARBEN["matt"])
            self.handel_text.insert(
                "1.0",
                "Testen und Scharfschalten gibt es nur fuer Spuren aus dauerlauf.SPUREN "
                "(Ordner unter Agenten/Handel). Diese Zeile ist etwas anderes: Werkzeug, "
                "Ausgabe, Ablage oder Projekt.",
            )
        else:
            stand = self.handel_zustand().get(spur) or {}
            self.handel_kopf.configure(
                text=self._handel_kopfzeile(spur, stand),
                foreground=FARBEN["gruen"] if stand.get("scharf") else FARBEN["text"],
            )
            self.handel_text.insert("1.0", self._handel_fliesstext(spur, stand))
        self.handel_text.configure(state="disabled")
        self._handel_knoepfe_setzen(z, spur)

    def _handel_kopfzeile(self, spur: str, stand: dict) -> str:
        teile = [f"Spur {spur}"]
        teile.append("Orderweg " + (stand.get("art") or "keiner"))
        teile.append("handel_erlaubt=" + ("true" if stand.get("erlaubt") else "false"))
        teile.append("freigabe.erfuellt=" + ("true" if stand.get("frei") else "false"))
        if stand.get("fenster"):
            teile.append(str(stand["fenster"]))
        if stand.get("buch"):
            teile.append("Buch " + ", ".join(f"{k} {v}" for k, v in stand["buch"].items()))
        if stand.get("alter") is not None:
            teile.append(f"Zyklus vor {stand['alter']} min")
        if stand.get("auto"):
            teile.append("AUTO_FREIGABE")
        if self._handel_gelesen:
            teile.append(f"gelesen {self._handel_gelesen:%H:%M:%S}")
        return " · ".join(teile)

    def _handel_fliesstext(self, spur: str, stand: dict) -> str:
        w = self._wachen(spur)
        punkte = handelstand.pruefpunkte(
            w, stand, buch=stand.get("buch"), alter=stand.get("alter"))
        zeilen = [f"{self._punkt_zeichen(p.stand)} {p.name}: {p.text}" for p in punkte]
        zeilen.append("")
        zeilen.append("Scharf schalten wuerde: " + handelstand.wirkung(stand, erlaubt=True))
        zeilen.append("F9 testet die Spur (--vorschau, schreibt nichts). "
                      "F10 oeffnet das Scharfschalten-Fenster.")
        return "\n".join(zeilen)

    @staticmethod
    def _punkt_zeichen(stand: str) -> str:
        return {"ok": "ok  ", "fehlt": "FEHLT", "warnung": "WARN ", "unbekannt": "?   "}.get(
            stand, "?   ")

    def _wachen(self, spur: str) -> dict:
        """Die Wachen-Datei einer Spur lesen (leer, wenn sie fehlt oder kaputt ist)."""
        pfad = handelstand.wachen_pfad(self.brainfiles, self._ordner_von(spur))
        try:
            return json.loads(pfad.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            return {}

    def _ordner_von(self, spur: str) -> str:
        return (self._plan.get(spur) or {}).get("ordner") or spur

    def _handel_knoepfe_setzen(self, z, spur: str) -> None:
        """Nur was jetzt etwas bewirken kann, ist an."""
        stand = (self.handel_zustand().get(spur) or {}) if spur else {}
        hat_spur = bool(spur)
        self.handel_knoepfe["test"].setze_aktiv(hat_spur)
        self.handel_knoepfe["stand"].setze_aktiv(True)
        self.handel_knoepfe["scharf"].setze_aktiv(hat_spur and not stand.get("erlaubt"))
        self.handel_knoepfe["entschaerfen"].setze_aktiv(hat_spur and bool(stand.get("erlaubt")))

    def handel_testen(self) -> None:
        """`handeln.py --vorschau` der gewaehlten Spur laufen lassen (schreibt nichts)."""
        z = self._gewaehlt()
        spur = getattr(z, "spur", "") if z is not None else ""
        if not spur:
            self.status.configure(text="Keine Handels-Spur gewaehlt - nichts getestet",
                                  foreground=FARBEN["gelb"])
            return
        if self._vorschau_laeuft:
            self.status.configure(text="Ein Testlauf laeuft schon", foreground=FARBEN["gelb"])
            return
        self._vorschau_laeuft = True
        self.handel_text.configure(state="normal")
        self.handel_text.delete("1.0", "end")
        self.handel_text.insert(
            "1.0",
            f"Vorschau {spur} laeuft ...\n"
            + " ".join(handelstand.vorschau_argv(self.brainfiles, spur)),
        )
        self.handel_text.configure(state="disabled")
        self.status.configure(text=f"Vorschau {spur} laeuft (Frist {VORSCHAU_FRIST_S} s) ...",
                              foreground=FARBEN["matt"])

        def arbeit():
            ok, text = self.vorschau_lauf(spur)
            self._nach_main(lambda: self._vorschau_fertig(spur, ok, text))

        threading.Thread(target=arbeit, daemon=True).start()

    def _vorschau_echt(self, spur: str) -> tuple[bool, str]:
        """Der echte Vorschau-Lauf: Ausgabe und Belegdatei, kein Schreibzugriff der Spur."""
        argv = handelstand.vorschau_argv(self.brainfiles, spur)
        cwd = handelstand.handel_ordner(self.brainfiles)
        log = aktionen.log_pfad(self.log_ordner, f"{spur}-vorschau", self.jetzt())
        Path(self.log_ordner).mkdir(parents=True, exist_ok=True)
        try:
            p = subprocess.run(
                argv, cwd=str(cwd), env=handelstand.vorschau_umgebung(),
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=VORSCHAU_FRIST_S,
            )
            text = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
            code = p.returncode
        except subprocess.TimeoutExpired:
            text = f"ABBRUCH nach {VORSCHAU_FRIST_S} s - die Spur hat nicht geantwortet."
            code = "Zeitfrist"
        except OSError as e:
            text = f"{type(e).__name__}: {e}"
            code = "Startfehler"
        try:
            with open(log, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"# Vorschau {spur} {self.jetzt():%Y-%m-%d %H:%M:%S} "
                        f"argv={argv} code={code}\n{text}\n")
        except OSError:
            pass
        return code == 0, text

    def _vorschau_fertig(self, spur: str, ok: bool, text: str) -> None:
        self._vorschau_laeuft = False
        self.handel_text.configure(state="normal")
        self.handel_text.delete("1.0", "end")
        self.handel_text.insert("1.0", text or "(keine Ausgabe)")
        self.handel_text.configure(state="disabled")
        self.status.configure(
            text=f"Vorschau {spur} {'beendet' if ok else 'mit Fehler beendet'} - "
                 f"Ausgabe in logs/{spur}-vorschau-*.log",
            foreground=FARBEN["gruen"] if ok else FARBEN["rot"],
        )

    def scharf_dialog(self) -> None:
        """Das Scharfschalten-Fenster oeffnen (Checkliste, Bestaetigung, Beleg)."""
        z = self._gewaehlt()
        spur = getattr(z, "spur", "") if z is not None else ""
        if not spur:
            self.status.configure(text="Keine Handels-Spur gewaehlt", foreground=FARBEN["gelb"])
            return
        import schalter

        stand = self.handel_zustand().get(spur) or {}
        schalter.ScharfFenster(
            self.root, spur=spur, wachen=self._wachen(spur), stand=stand,
            farben=FARBEN, schrift_tupel=self.schrift(),
            radius=int(rund.RADIUS * self.s), s=self.s,
            ausfuehren=self._schalter_ausfuehren, jetzt=self.jetzt,
        )

    def _schalter_ausfuehren(self, spur: str, aenderungen: dict, vermerk: str):
        """Den Schreibvorgang aus dem Dialog ausfuehren und belegen."""
        pfad = handelstand.wachen_pfad(self.brainfiles, self._ordner_von(spur))
        ergebnis = handelstand.wachen_setzen(
            pfad, aenderungen, vermerk=vermerk,
            notiz_schluessel="_scharfgeschaltet" if aenderungen.get("handel_erlaubt")
            else "_entschaerft",
            jetzt=self.jetzt(),
        )
        handelstand.beleg(
            self.log_ordner,
            f"{'OK' if ergebnis.ok else 'FEHLER'} {spur}: "
            f"{ergebnis.fehler or '; '.join(ergebnis.geaendert)} ({vermerk})",
            jetzt=self.jetzt(),
        )
        if ergebnis.ok:
            self.handel_stand_auffrischen(spur, aenderungen)
        return ergebnis

    def handel_stand_auffrischen(self, spur: str, aenderungen: dict) -> None:
        """Den gelesenen Stand an die Aenderung anpassen, ohne alles neu zu lesen."""
        stand = (self._handel_da or {}).get(spur)
        if not stand:
            return
        if "handel_erlaubt" in aenderungen:
            stand["erlaubt"] = bool(aenderungen["handel_erlaubt"])
            stand["scharf"] = bool(stand.get("order")) and stand["erlaubt"]
        if "freigabe.erfuellt" in aenderungen:
            stand["frei"] = bool(aenderungen["freigabe.erfuellt"])
        if "herzschlag_max_minuten" in aenderungen:
            stand["hs"] = aenderungen["herzschlag_max_minuten"]

    def entschaerfen(self) -> None:
        """`handel_erlaubt` auf false setzen - nach Rueckfrage im eigenen Fenster."""
        z = self._gewaehlt()
        spur = getattr(z, "spur", "") if z is not None else ""
        if not spur:
            self.status.configure(text="Keine Handels-Spur gewaehlt", foreground=FARBEN["gelb"])
            return
        import schalter

        schalter.EntschaerfenFenster(
            self.root, spur=spur, farben=FARBEN, schrift_tupel=self.schrift(),
            radius=int(rund.RADIUS * self.s), s=self.s,
            ausfuehren=self._schalter_ausfuehren, jetzt=self.jetzt,
        )

    # ------------------------------------------------------------- Pflege
    def _pflege_text_setzen(self, inhalt: str) -> None:
        self.pflege_text.configure(state="normal")
        self.pflege_text.delete("1.0", "end")
        self.pflege_text.insert("1.0", inhalt)
        self.pflege_text.configure(state="disabled")

    def _pflege_schritte(self, z: manifest.Zeile, feld: str) -> tuple[list[list[str]], str]:
        """Die Schritte fuer 'einrichten' oder 'bauen' - und woher sie kommen.

        Reihenfolge: die Kette aus dem Manifest, sonst der einzelne Befehl aus
        dem Manifest, sonst der Vorschlag aus den Dateien des Projekts. Was
        nicht belegt und nicht ableitbar ist, bleibt leer - geraten wird nichts.
        """
        kette = list(getattr(z, f"{feld}_kette", None) or [])
        if kette:
            return kette, "Manifest (Kette)"
        einzeln = getattr(z, feld, None)
        if einzeln:
            return [list(einzeln)], "Manifest"
        pfad = Path(z.repo.pfad) if z.repo is not None else None
        if pfad is None or not pfad.is_dir():
            return [], "kein Ordner"
        vorschlag = (pflege.vorschlag_einrichten(pfad) if feld == "einrichten"
                     else pflege.vorschlag_bauen(pfad))
        grund = (pflege.einrichten_grund(pfad) if feld == "einrichten"
                 else pflege.bauen_grund(pfad))
        return list(vorschlag), grund

    def _pflege_anzeigen(self) -> None:
        """Den Pflegereiter auf die gewaehlte Zeile umstellen."""
        if not hasattr(self, "pflege_text"):
            return
        z = self._gewaehlt()
        if z is None or z.repo is None:
            self.pflege_kopf.configure(
                text="Links ein Projekt waehlen.", foreground=FARBEN["matt"])
            self._pflege_text_setzen(
                "Pruefen misst den Zustand: venv (laeuft sie?), node_modules,\n"
                "Pflichtpfad, Git-Zweig und Rueckstand, README, Bot-Profil, Port.\n\n"
                "Einrichten und Bauen fuehren die Schritte aus, die im Manifest\n"
                "stehen oder sich aus den Dateien des Projekts ergeben\n"
                "(package.json, requirements.txt, pyproject.toml, Cargo.toml).\n\n"
                "Nach einem erfolgreichen Lauf wird der Befehl im Manifest\n"
                "belegt - dann steht er beim naechsten Mal als Befehl da.")
            self._pflege_knoepfe_setzen(None, [], [])
            return
        ein, ein_quelle = self._pflege_schritte(z, "einrichten")
        bau, bau_quelle = self._pflege_schritte(z, "bauen")
        teile = [f"{z.bereich}/{z.ordner}", z.art or "-"]
        teile.append("venv" if z.repo.venv else "keine venv")
        if z.repo.node_modules:
            teile.append("node_modules")
        self.pflege_kopf.configure(text=" · ".join(t for t in teile if t),
                                   foreground=FARBEN["text"])
        zeilen = []
        zeilen.append(f"Einrichten: {len(ein)} Schritt(e) - {ein_quelle}"
                      if ein else f"Einrichten: kein Befehl - {ein_quelle}")
        for s in ein:
            zeilen.append("   " + " ".join(s))
        zeilen.append(f"Bauen: {len(bau)} Schritt(e) - {bau_quelle}"
                      if bau else f"Bauen: kein Befehl - {bau_quelle}")
        for s in bau:
            zeilen.append("   " + " ".join(s))
        zeilen.append("")
        zeilen.append("F7 prueft den Zustand. Einrichten/Bauen laufen im Hintergrund,")
        zeilen.append("die Ausgabe landet zusaetzlich in logs/ und belegt den Befehl.")
        self._pflege_text_setzen("\n".join(zeilen))
        self._pflege_knoepfe_setzen(z, ein, bau)

    def _pflege_knoepfe_setzen(self, z, ein=None, bau=None) -> None:
        """Nur was jetzt etwas bewirken kann, ist an."""
        da = z is not None and z.repo is not None
        laeuft = self._pflege_laeuft
        self.pflege_knoepfe["pruefen"].setze_aktiv(bool(da) and not laeuft)
        self.pflege_knoepfe["einrichten"].setze_aktiv(bool(da and ein) and not laeuft)
        self.pflege_knoepfe["bauen"].setze_aktiv(bool(da and bau) and not laeuft)
        self.pflege_knoepfe["alle"].setze_aktiv(not laeuft)

    def pflege_pruefen(self) -> None:
        """Den Zustand eines Projekts messen (rein lesend)."""
        z = self._gewaehlt()
        if z is None or z.repo is None:
            self.status.configure(text="Kein Projekt gewaehlt", foreground=FARBEN["gelb"])
            return
        if self._pflege_laeuft:
            self.status.configure(text="Ein Pflege-Lauf laeuft schon",
                                  foreground=FARBEN["gelb"])
            return
        self._pflege_laeuft = True
        self._pflege_knoepfe_setzen(z)
        self._pflege_text_setzen(f"Pruefe {z.ordner} ...")
        self.status.configure(text=f"Pruefe {z.ordner} (venv, Git, Port ...)",
                              foreground=FARBEN["matt"])

        def arbeit():
            punkte = pflege.pruefen(z, log_ordner=self.log_ordner, jetzt=self.jetzt())
            text = pflege.bericht(z, punkte)
            offen = len(pflege.offene_punkte(punkte))
            self._nach_main(lambda: self._pflege_fertig(
                z.ordner, text, f"{z.ordner}: {offen} offene(r) Punkt(e)", offen == 0))

        threading.Thread(target=arbeit, daemon=True).start()

    def pflege_einrichten(self) -> None:
        """Die Einrichtungsschritte ausfuehren (Manifest oder Vorschlag)."""
        self._pflege_auftrag("einrichten")

    def pflege_bauen(self) -> None:
        """Den Bau-Schritt ausfuehren."""
        self._pflege_auftrag("bauen")

    def _pflege_auftrag(self, feld: str) -> None:
        z = self._gewaehlt()
        if z is None or z.repo is None:
            self.status.configure(text="Kein Projekt gewaehlt", foreground=FARBEN["gelb"])
            return
        if self._pflege_laeuft:
            self.status.configure(text="Ein Pflege-Lauf laeuft schon",
                                  foreground=FARBEN["gelb"])
            return
        schritte, quelle = self._pflege_schritte(z, feld)
        if not schritte:
            self.status.configure(
                text=f"{z.ordner}: kein {feld}-Befehl belegt - {quelle}",
                foreground=FARBEN["gelb"])
            return
        self._pflege_laeuft = True
        self._pflege_knoepfe_setzen(z)
        log = aktionen.log_pfad(self.log_ordner, f"{z.ordner}-{feld}", self.jetzt())
        self._pflege_text_setzen(
            f"{feld} in {z.ordner} laeuft ...\nQuelle: {quelle}\n\n"
            + "\n".join(" ".join(s) for s in schritte)
            + f"\n\nAusgabe: {log.name}")
        self.status.configure(text=f"{feld} {z.ordner}: {' '.join(schritte[0])} ...",
                              foreground=FARBEN["matt"])

        def arbeit():
            ok, text = pflege.ausfuehren(schritte, Path(z.repo.pfad), log=log,
                                         jetzt=self.jetzt())
            belegt = False
            if ok and len(schritte) > 1 and not getattr(z, f"{feld}_kette", None):
                belegt = pflege.eintragen(self.manifest_pfad, z.ordner,
                                          f"{feld}_kette", schritte, wurzel=z.wurzel,
                                          vermerk=quelle, jetzt=self.jetzt())
                if belegt:
                    setattr(z, f"{feld}_kette", [list(s) for s in schritte])
            elif ok and len(schritte) == 1 and not getattr(z, feld, None):
                belegt = pflege.eintragen(self.manifest_pfad, z.ordner, feld, schritte[0],
                                          wurzel=z.wurzel, vermerk=quelle, jetzt=self.jetzt())
                if belegt:
                    setattr(z, feld, list(schritte[0]))
            self._nach_main(lambda: self._pflege_fertig(
                z.ordner, text,
                f"{feld} {z.ordner} " + ("fertig" if ok else "mit Fehler beendet")
                + (" - Befehl im Manifest belegt" if belegt else ""), ok))

        threading.Thread(target=arbeit, daemon=True).start()

    def pflege_alle(self) -> None:
        """Alle gezeigten Projekte messen und einen Pruefbericht schreiben."""
        if self._pflege_laeuft:
            self.status.configure(text="Ein Pflege-Lauf laeuft schon",
                                  foreground=FARBEN["gelb"])
            return
        zeilen = [z for z in self.zeilen if z.repo is not None
                  and auswahl.trifft(z, self._filter())]
        if not zeilen:
            self.status.configure(text="Nichts zu pruefen (Filter ist leer)",
                                  foreground=FARBEN["gelb"])
            return
        self._pflege_laeuft = True
        self._pflege_knoepfe_setzen(None)
        self._pflege_text_setzen(f"Pruefe {len(zeilen)} Projekte ... (kann Minuten dauern)")
        self.status.configure(text=f"Pruefbericht ueber {len(zeilen)} Projekte laeuft ...",
                              foreground=FARBEN["matt"])
        ziel = aktionen.log_pfad(self.log_ordner, "pruefbericht", self.jetzt())

        def arbeit():
            text, auffaellig = pflege.sammelbericht(zeilen, log_ordner=self.log_ordner,
                                                    jetzt=self.jetzt())
            try:
                Path(self.log_ordner).mkdir(parents=True, exist_ok=True)
                with open(ziel, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            except OSError:
                pass
            kurz = text if len(text) < 4000 else text[:4000] + "\n... (gekuerzt)"
            self._nach_main(lambda: self._pflege_fertig(
                None, kurz,
                f"Pruefbericht: {len(zeilen)} geprueft, {len(auffaellig)} auffaellig "
                f"-> {ziel.name}", not auffaellig))

        threading.Thread(target=arbeit, daemon=True).start()

    def _pflege_fertig(self, ordner, text: str, meldung: str, gut: bool) -> None:
        """Ein Pflege-Ergebnis anzeigen - nur, wenn die Zeile noch gewaehlt ist."""
        self._pflege_laeuft = False
        z = self._gewaehlt()
        passt = ordner is None or (z is not None and z.ordner == ordner)
        if passt:
            self._pflege_text_setzen(text)
            ein, bau = ([], [])
            if z is not None and z.repo is not None:
                ein = self._pflege_schritte(z, "einrichten")[0]
                bau = self._pflege_schritte(z, "bauen")[0]
            self._pflege_knoepfe_setzen(z, ein, bau)
        else:
            self._pflege_anzeigen()
        self.status.configure(text=meldung,
                              foreground=FARBEN["gruen"] if gut else FARBEN["gelb"])

    # ------------------------------------------------------------- Detailbereich
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
        auswahl_ = self.befehlsbaum.selection()
        if not auswahl_:
            return None
        return self.befehl_kinder.get(auswahl_[0])

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
        """Den gewaehlten Befehl in einem Terminal-Tab im Projekt starten."""
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
        self._handel_anzeigen()
        self._pflege_anzeigen()
        if getattr(z, "spur", "") and self._handel_da is None:
            self._handel_im_hintergrund()
        if z is None or z.repo is None:
            for b in self.knoepfe.values():
                b.configure(state="disabled")
            return
        self.knoepfe["ordner"].configure(state="normal")
        self.knoepfe["terminal"].configure(state="normal")
        self.knoepfe["start"].configure(state="normal" if z.start_da else "disabled")
        self.knoepfe["bot"].configure(state="normal" if z.bot_da else "disabled")
        self.knoepfe["doku"].configure(state="normal" if z.repo.readme else "disabled")
        teile = [z.bereich, z.ordner, z.art]
        if z.rolle:
            teile.append(z.rolle)
        if getattr(z, "spur", ""):
            teile.append("Handels-Spur")
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
        for name in ("Repos-Zentrale.md", "repos-zentrale.md"):
            seite = self.brainfiles / "MaxHirn" / "Wiki" / "Werkzeuge" / name
            if seite.is_file():
                aktionen.doku_oeffnen(seite)
                self.status.configure(text=f"Wiki: {seite}", foreground=FARBEN["matt"])
                return
        self.status.configure(
            text="Wiki-Seite fehlt: MaxHirn/Wiki/Werkzeuge/repos-zentrale.md",
            foreground=FARBEN["gelb"],
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
            self._nach_main(lambda: self._start_fertig(z, ergebnis))
            return
        self._nach_main(
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
        self._nach_main(
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