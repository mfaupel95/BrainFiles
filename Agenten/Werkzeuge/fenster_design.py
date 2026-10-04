"""Gemeinsames Design der Desktop-Fenster (Handelszentrale, Repos-Zentrale, ...).

Eine Quelle fuer Farben, Schrift, Abstaende und ttk-Stile. Vorher stand die
Palette doppelt in `handelszentrale.py` und `repos-zentrale/fenster.py`; jede
Abweichung war ein Wartungsfehler. Beschreibung und Regeln:
Werkstatt/design-system-fenster-2026-09-30.md.

Diese Datei importiert tkinter NICHT. Die Tokens und die reinen Funktionen sind
damit ohne Fenster pruefbar; `stil_anwenden` bekommt das `ttk.Style`-Objekt vom
Aufrufer.

Verwendung (kein Paket, deshalb per Dateipfad laden - ein `sys.path`-Eintrag
auf Werkzeuge/ wuerde dort liegende Module wie `marktdaten` einblenden):

    spec = importlib.util.spec_from_file_location("fenster_design", PFAD)
    design = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(design)
"""

from __future__ import annotations

# ------------------------------------------------------------------ Farben
# Catppuccin Mocha. Farbe traegt Bedeutung (gruen/rot/gelb = Zustand), nie
# Dekoration - und Zustand nie NUR ueber Farbe, immer auch als Text.
FARBEN = {
    # Flaechen (dunkel -> hell)
    "blatt": "#181825",       # Datenflaeche: Tabelle, Eingabe, Chart
    "bg": "#1e1e2e",          # Fensterflaeche
    "gitter": "#313244",      # Trennlinien, Tabellenkopf, Tab
    "auswahl": "#45475a",     # Ausgewaehlte Zeile, aktiver Tab, Hover
    # Schrift
    "text": "#cdd6f4",
    "matt": "#a6adc8",        # Nebeninfo, Achsen, Fusszeile (7.37:1 auf bg)
    # Der hellere Ton fuer Nebeninfo, die auf einer FLAECHE steht (Tabellen-
    # koepfe, Zellen): 9.91:1 gegen blatt, 9.92:1 gegen bg. Bis 05.10.2026
    # gab der Leitstand dafuer einen zweiten Wert unter demselben Namen -
    # ein Name, zwei Werte, zwei hausweite Bedeutungen. Jetzt ist es eine
    # eigene Farbe mit eigener Bedeutung, gemessen mit kontrast_messen.py.
    "matt_flache": "#bac2de",
    # Bedeutung
    "akzent": "#89b4fa",      # Titel, Tabellenkopf, aktiver Tab
    "blau": "#89b4fa",        # Einstiegslinie im Chart (= akzent)
    "gruen": "#a6e3a1",       # Erfolg, Gewinn, long
    "rot": "#f38ba8",         # Fehler, Verlust, short
    "gelb": "#f9e2af",        # Warnung, Aufmerksamkeit
    # Zellhintergruende (dunkle Toene, damit Schrift lesbar bleibt)
    "zellgruen": "#1b4d3e",
    "zellrot": "#5c1f2b",
}

# ------------------------------------------------------------------ Schrift
SCHRIFT_ART = "Consolas"        # Festbreite: Zahlenspalten fluchten
SCHRIFT_GROESSE = 11            # Basis; 10 war zu klein (Befund 30.09.2026)
SCHRIFT_AUSWAHL = tuple(str(g) for g in range(8, 17))

# Stufen relativ zur Basis: Titel, Tabellen und Chart skalieren gemeinsam.
TITEL = 3                       # Fensterkopf
KLEIN = -1                      # Konsole, Fusszeile
TINY = -2                       # Chart-Beschriftung

# ------------------------------------------------------------------ Abstaende
# 4-Punkt-Raster. Kein anderer Wert fuer padx/pady.
ABSTAND = {"xs": 2, "s": 4, "m": 8, "l": 12, "xl": 16}
RAND = ABSTAND["m"]             # Fensterrand


def schrift(basis: int = SCHRIFT_GROESSE, rel: int = 0, fett: bool = False):
    """Schrift-Tupel fuer Tk: Basis + relative Stufe."""
    if fett:
        return (SCHRIFT_ART, basis + rel, "bold")
    return (SCHRIFT_ART, basis + rel)


def zeilenhoehe(basis: int = SCHRIFT_GROESSE) -> int:
    """Tabellenzeile: Schrift x 2, mindestens 18 - sonst werden Buchstaben
    angeschnitten."""
    return max(18, basis * 2)


def vorzeichen_farbe(wert, neutral: str = "matt") -> str:
    """Farbname fuer eine Zahl: Gewinn gruen, Verlust rot, sonst neutral.

    Nicht Zahl (None, "") -> neutral. Der Aufrufer zeigt das Vorzeichen
    trotzdem als Text (Farbe allein ist kein Zustand)."""
    try:
        w = float(wert)
    except (TypeError, ValueError):
        return neutral
    if w > 0:
        return "gruen"
    if w < 0:
        return "rot"
    return neutral


def skalierung(root) -> float:
    """Der Anzeige-Faktor: 1.0 bei 96 dpi, 1.25 bei 120 dpi, 1.5 bei 144 dpi.

    Ein Fenster mit `dpi_bewusst()` setzt Schrift und Zeilenhoehe in
    Geraetepixeln; fest eingetragene Breiten (Spalten, Eingabefelder) werden
    dadurch zu schmal. Wer Pixelmasse setzt, streckt sie mit diesem Faktor.
    Nie kleiner als 1.0 - ein kleinerer Faktor wuerde Text verkleinern, statt
    ihn lesbar zu halten.
    """
    try:
        return max(1.0, float(root.winfo_fpixels("1i")) / 96.0)
    except Exception:                                        # noqa: BLE001
        return 1.0


def dpi_bewusst() -> None:
    """Windows sagen, dass wir selbst skalieren - VOR dem ersten `Tk()`.

    Ohne den Aufruf streckt Windows das fertige Bild (150-%-Monitor), jede
    Schrift wird unscharf. Fehlertolerant: fehlt shcore oder laeuft das auf
    Linux, bleibt es beim Standard.
    """
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)      # type: ignore[attr-defined]
    except Exception:                                        # noqa: BLE001
        pass


def stil_anwenden(st, basis: int = SCHRIFT_GROESSE) -> None:
    """Alle ttk-Stile aus den Tokens setzen. `st` ist ein `ttk.Style`.

    Widgets, die nichts Eigenes setzen, erben von "." - die Schrift steht also
    zentral hier. Aufrufen: einmal beim Aufbau und erneut, wenn sich die
    Schriftgroesse aendert.
    """
    f = FARBEN
    try:
        st.theme_use("clam")
    except Exception:                                        # noqa: BLE001
        pass
    st.configure(".", background=f["bg"], foreground=f["text"],
                 fieldbackground=f["blatt"], bordercolor=f["gitter"],
                 lightcolor=f["gitter"], darkcolor=f["gitter"],
                 troughcolor=f["blatt"], font=schrift(basis))

    st.configure("TLabel", background=f["bg"], foreground=f["text"],
                 font=schrift(basis))
    st.configure("TFrame", background=f["bg"])
    st.configure("TLabelframe", background=f["bg"], bordercolor=f["gitter"])
    st.configure("TLabelframe.Label", background=f["bg"],
                 foreground=f["akzent"], font=schrift(basis, 0, True))

    st.configure("Treeview", background=f["blatt"], fieldbackground=f["blatt"],
                 foreground=f["text"], rowheight=zeilenhoehe(basis),
                 borderwidth=0)
    st.configure("Treeview.Heading", background=f["gitter"],
                 foreground=f["akzent"], font=schrift(basis, 0, True),
                 relief="flat")
    st.map("Treeview", background=[("selected", f["auswahl"])],
           foreground=[("selected", f["text"])])
    st.map("Treeview.Heading", background=[("active", f["auswahl"])])

    st.configure("TNotebook", background=f["bg"], borderwidth=0)
    st.configure("TNotebook.Tab", background=f["gitter"],
                 foreground=f["text"], padding=(ABSTAND["l"], ABSTAND["s"] - 1))
    st.map("TNotebook.Tab", background=[("selected", f["auswahl"])],
           foreground=[("selected", f["akzent"])])

    st.configure("TButton", background=f["gitter"], foreground=f["text"],
                 font=schrift(basis), padding=(ABSTAND["m"], ABSTAND["s"]),
                 borderwidth=0)
    st.map("TButton", background=[("active", f["auswahl"]),
                                  ("disabled", f["blatt"])],
           foreground=[("disabled", f["matt"])])

    st.configure("TEntry", fieldbackground=f["blatt"], foreground=f["text"],
                 insertcolor=f["text"], font=schrift(basis))
    st.configure("TCombobox", fieldbackground=f["blatt"],
                 background=f["gitter"], foreground=f["text"],
                 arrowcolor=f["akzent"], font=schrift(basis))
    st.map("TCombobox", fieldbackground=[("readonly", f["blatt"])],
           foreground=[("readonly", f["text"])])

    for name in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        st.configure(name, background=f["gitter"], arrowcolor=f["matt"],
                     bordercolor=f["bg"], troughcolor=f["blatt"])
        st.map(name, background=[("active", f["auswahl"])])

# ------------------------------------------------------------------ Karte
# Die Karte ist der gemeinsame Baustein aller Fenster: eine abgerundete Flaeche
# mit Titel, darin ein Reiter oder eine Tabelle. Radien und Innenabstand stehen
# HIER - vorher lagen sie in `repos-zentrale/fenster.py`, die Handelszentrale
# hatte eigene Werte.
KARTE = {
    "radius": 12,             # Ecken der Kartenflaeche
    "radius_knopf": 8,        # Ecken der Knoepfe darauf
    "rand": 1,                # Rahmenstaerke in Pixeln
    "innen": ABSTAND["m"],    # Abstand zwischen Kartenrand und Inhalt
}
STIL_PRAEFIX = "Karte"


def karten_stile(st, basis: int = SCHRIFT_GROESSE, zeilenhoehe_px: int | None = None) -> str:
    """ttk-Stile fuer den Inhalt einer Karte (Praefix `Karte.`).

    Die Karte hat eine eigene Flaeche (`blatt`, dunkler als das Fenster). Ein
    ttk-Widget darin braucht einen Stil mit DIESEM Hintergrund - sonst steht ein
    Rechteck in Fensterfarbe auf der Karte. Gibt das Praefix zurueck, damit der
    Aufrufer `style=f"{p}.Treeview"` schreiben kann statt den Namen zu raten.
    """
    f = FARBEN
    p = STIL_PRAEFIX
    hoehe = zeilenhoehe_px or zeilenhoehe(basis)
    st.configure(f"{p}.TFrame", background=f["blatt"])
    st.configure(f"{p}.TLabel", background=f["blatt"], foreground=f["text"],
                 font=schrift(basis))
    st.configure(f"{p}Titel.TLabel", background=f["blatt"], foreground=f["akzent"],
                 font=schrift(basis, 0, True))
    st.configure(f"{p}.Treeview", background=f["blatt"], fieldbackground=f["blatt"],
                 foreground=f["text"], rowheight=hoehe, borderwidth=0)
    st.configure(f"{p}.Treeview.Heading", background=f["gitter"],
                 foreground=f["akzent"], font=schrift(basis, 0, True), relief="flat")
    st.map(f"{p}.Treeview", background=[("selected", f["auswahl"])],
           foreground=[("selected", f["text"])])
    st.configure(f"{p}.TNotebook", background=f["blatt"], borderwidth=0,
                 tabmargins=(ABSTAND["s"], ABSTAND["s"], ABSTAND["s"], 0))
    st.configure(f"{p}.TNotebook.Tab", background=f["gitter"], foreground=f["text"],
                 font=schrift(basis, KLEIN), padding=(ABSTAND["m"], ABSTAND["xs"]))
    st.map(f"{p}.TNotebook.Tab", background=[("selected", f["blatt"])],
           foreground=[("selected", f["akzent"])])
    st.configure(f"{p}.TCheckbutton", background=f["blatt"], foreground=f["text"],
                 font=schrift(basis))
    st.map(f"{p}.TCheckbutton", background=[("active", f["blatt"])],
           foreground=[("disabled", f["matt"])])
    st.configure(f"{p}.TButton", background=f["gitter"], foreground=f["text"],
                 font=schrift(basis), padding=(ABSTAND["m"], ABSTAND["s"]),
                 borderwidth=0)
    st.map(f"{p}.TButton", background=[("active", f["auswahl"])],
           foreground=[("disabled", f["matt"])])
    st.configure(f"{p}.TEntry", fieldbackground=f["blatt"], foreground=f["text"],
                 insertcolor=f["text"], font=schrift(basis))
    for name in ("Vertical", "Horizontal"):
        st.configure(f"{p}.{name}.TScrollbar", background=f["gitter"],
                     arrowcolor=f["matt"], bordercolor=f["blatt"],
                     troughcolor=f["blatt"])
        st.map(f"{p}.{name}.TScrollbar", background=[("active", f["auswahl"])])
    return p
