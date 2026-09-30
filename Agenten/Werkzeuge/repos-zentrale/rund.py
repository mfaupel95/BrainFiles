"""Runde Ecken fuer die Zentrale: Geometrie, Knoepfe, Karten, Fensterrand.

Warum eine eigene Datei: Tk/ttk kennt keine runden Ecken. Ein Knopf ist ein
Rechteck, ein Rahmen ist ein Rechteck. Wer runde Ecken will, zeichnet sie - und
zwar an EINER Stelle, damit Knopf, Karte und Auswahlblase denselben Radius und
dieselbe Farblogik benutzen.

Drei Teile:

| Teil | Was |
|---|---|
| `ecken_punkte` | die Umrisspunkte eines Rechtecks mit runden Ecken (reine Rechnung, ohne Fenster pruefbar) |
| `RunderKnopf`, `Karte` | Canvas-Widgets, die damit gezeichnet werden |
| `fenster_ecken` | der Fensterrahmen selbst - Windows 11 rundet ihn nur auf Anforderung |

Die Farblogik kommt aus `fenster_design.FARBEN` (dieselbe Quelle wie
handelszentrale.py); hier stehen nur die Form (Radius, Rand) und die
Bedeutungs-Varianten (normal, haupt, gut, gefahr, warnung, flach).
"""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import font as tkfont

# Eckenradius in Pixeln bei 100 % Anzeige. Jeder Radius wird mit dem
# DPI-Faktor gestreckt (fenster_design.skalierung) - sonst wirken die Ecken auf
# einem 150-%-Monitor wie abgeschnitten.
RADIUS = 9
RADIUS_KLEIN = 6
RAND = 1

# Die Varianten eines Knopfes: Flaeche, Schrift und Rand. Bedeutung, nicht
# Dekoration - "haupt" ist der eine naechste Schritt, "gefahr" schaltet etwas
# ab oder gibt etwas frei, "warnung" verlangt einen Blick.
VARIANTEN = {
    "normal": {"flaeche": "gitter", "schrift": "text", "rand": "auswahl",
               "hover": "auswahl"},
    "haupt": {"flaeche": "akzent", "schrift": "blatt", "rand": "akzent",
              "hover": "blau"},
    "gut": {"flaeche": "zellgruen", "schrift": "gruen", "rand": "gruen",
            "hover": "gruen"},
    "gefahr": {"flaeche": "zellrot", "schrift": "rot", "rand": "rot",
               "hover": "rot"},
    "warnung": {"flaeche": "gitter", "schrift": "gelb", "rand": "gelb",
                "hover": "auswahl"},
    "flach": {"flaeche": "bg", "schrift": "matt", "rand": "bg",
              "hover": "gitter"},
}


def ecken_punkte(x0, y0, x1, y1, r, schritte: int = 6) -> list[tuple[float, float]]:
    """Die Umrisspunkte eines Rechtecks mit runden Ecken.

    Reihenfolge: oben links -> oben rechts -> unten rechts -> unten links, also
    im Uhrzeigersinn (Tk zeichnet ein Polygon in dieser Reihenfolge richtig).
    `r` wird auf die halbe kurze Seite begrenzt - ein Radius groesser als die
    Flaeche ergaebe eine Raute. `schritte` ist die Zahl der Zwischenpunkte JE
    Ecke: 6 genuegt fuer eine glatte Rundung und haelt die Punktliste klein.
    """
    r = max(0.0, min(float(r), (x1 - x0) / 2.0, (y1 - y0) / 2.0))
    if r <= 0:
        return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

    def bogen(cx: float, cy: float, von: float, bis: float):
        return [
            (cx + r * math.cos(von + (bis - von) * i / schritte),
             cy + r * math.sin(von + (bis - von) * i / schritte))
            for i in range(schritte + 1)
        ]

    punkte: list[tuple[float, float]] = [(x0 + r, y0), (x1 - r, y0)]
    punkte += bogen(x1 - r, y0 + r, -math.pi / 2, 0.0)          # Ecke oben rechts
    punkte += [(x1, y1 - r)]
    punkte += bogen(x1 - r, y1 - r, 0.0, math.pi / 2)           # unten rechts
    punkte += [(x0 + r, y1)]
    punkte += bogen(x0 + r, y1 - r, math.pi / 2, math.pi)       # unten links
    punkte += [(x0, y0 + r)]
    punkte += bogen(x0 + r, y0 + r, math.pi, 3 * math.pi / 2)   # oben links
    # Die Bogenenden treffen die Geradenpunkte genau - doppelte Punkte wuerden
    # das Polygon nur laenger machen, nicht falsch. Deshalb hier entfernen.
    sauber: list[tuple[float, float]] = []
    for p in punkte:
        if not sauber or abs(p[0] - sauber[-1][0]) > 1e-9 or abs(p[1] - sauber[-1][1]) > 1e-9:
            sauber.append(p)
    return sauber


def umriss(breite: int, hoehe: int, r: int) -> list[float]:
    """Dieselbe Rechnung als flache Tk-Punktliste fuer ein Widget dieser Groesse."""
    return [t for p in ecken_punkte(0, 0, breite, hoehe, r) for t in p]


def flaeche(
    canvas: tk.Canvas,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    r: float,
    fuellung: str,
    rand: str | None = None,
    rand_breite: int = RAND,
    tags=(),
) -> int:
    """Ein Rechteck mit runden Ecken auf ein Canvas zeichnen; gibt die Item-Id.

    `fuellung` ist eine FERTIGE Farbangabe (nicht der Name eines Tokens) -
    die Zuordnung Name -> Token macht der Aufrufer.
    """
    punkte = [t for p in ecken_punkte(x0, y0, x1, y1, r) for t in p]
    return canvas.create_polygon(
        *punkte,
        fill=fuellung,
        outline=rand or fuellung,
        width=rand_breite,
        tags=tags,
    )


def text_breite(widget, schrift_tupel, text: str) -> int:
    """Wie breit ist dieser Text in dieser Schrift? (Fallback: 0,62 x Hoehe je Zeichen)."""
    try:
        f = tkfont.Font(root=widget, font=schrift_tupel)
        return int(f.measure(text))
    except Exception:                                        # noqa: BLE001
        groesse = schrift_tupel[1] if isinstance(schrift_tupel, tuple) else 11
        return int(len(text) * groesse * 0.62)


def zeilen_hoehe(widget, schrift_tupel) -> int:
    """Die Hoehe einer Zeile in dieser Schrift (fuer Knopf und Karte gerechnet)."""
    try:
        f = tkfont.Font(root=widget, font=schrift_tupel)
        return int(f.metrics("linespace"))
    except Exception:                                        # noqa: BLE001
        groesse = schrift_tupel[1] if isinstance(schrift_tupel, tuple) else 11
        return int(groesse * 1.7)


class RunderKnopf(tk.Canvas):
    """Ein Knopf mit runden Ecken - der Ersatz fuer ttk.Button.

    Warum nicht ttk.Button: dessen Ecken sind feste Rechtecke, und ein eigener
    ttk-Stil mit runden Ecken braucht Bilder je Zustand. Ein Canvas mit einem
    Polygon kann alles: Radius, Farbe je Bedeutung, Hover, Aus-Zustand - und
    passt sich der Schriftgroesse an.

    Attribute:
        breite/hoehe   Pixel; ohne Angabe aus Text und Schrift gerechnet
        variante       "normal", "haupt", "gut", "gefahr", "warnung", "flach"
        nummer         Text rechts neben der Beschriftung (z. B. eine Zahl)
    """

    def __init__(
        self,
        master,
        text: str,
        command=None,
        *,
        variante: str = "normal",
        farben: dict | None = None,
        schrift_tupel=("Consolas", 11),
        radius: int = RADIUS,
        breite: int | None = None,
        hoehe: int | None = None,
        padx: int = 10,
        pady: int = 4,
        fett: bool = False,
        hinweis: str = "",
        **kwargs,
    ) -> None:
        self.farben = farben or {}
        self.variante = variante
        self.schrift_tupel = schrift_tupel
        self.radius = radius
        self.text = text
        self.hinweis = hinweis
        self.command = command
        self.bei_hinweis = None          # Rueckruf(text) beim Zeigen - z. B. Statuszeile
        self.aktiv = True
        self._zeiger_drauf = False
        self._gedrueckt = False
        self._groesse = (0, 0)       # zuletzt gezeichnete Groesse
        self._flaeche_items = []     # Kennungen der Flaechen-Elemente
        self._text_item = None

        hoehe = hoehe or (zeilen_hoehe(master, schrift_tupel) + 2 * pady + 2)
        breite = breite or (text_breite(master, schrift_tupel, text) + 2 * padx + 2)
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("background", self._farbe("umgebung"))
        super().__init__(master, width=breite, height=hoehe, **kwargs)

        self.bind("<Enter>", self._hinein)
        self.bind("<Leave>", self._heraus)
        self.bind("<ButtonPress-1>", self._druck)
        self.bind("<ButtonRelease-1>", self._loslassen)
        self.bind("<Configure>", lambda _e: self.zeichnen())
        self.zeichnen()

    # ------------------------------------------------------------- Farben
    def _farbe(self, rolle: str) -> str:
        """Eine Farbe aus der Palette holen (fehlende Palette -> Tk-Standard)."""
        return self.farben.get(rolle, "#313244")

    def _plan(self, *, hover: bool = False, gedrueckt: bool = False) -> dict:
        v = VARIANTEN.get(self.variante, VARIANTEN["normal"])
        if not self.aktiv:
            return {"flaeche": self._farbe("blatt"), "schrift": self._farbe("matt"),
                    "rand": self._farbe("gitter")}
        if gedrueckt:
            return {"flaeche": self._farbe(v["hover"]), "schrift": self._farbe(v["schrift"]),
                    "rand": self._farbe(v["hover"])}
        if hover:
            return {"flaeche": self._farbe(v["hover"]), "schrift": self._farbe(v["schrift"]),
                    "rand": self._farbe(v["hover"])}
        return {"flaeche": self._farbe(v["flaeche"]), "schrift": self._farbe(v["schrift"]),
                "rand": self._farbe(v["rand"])}

    # ------------------------------------------------------------- Zeichnen
    def zeichnen(self, erzwingen: bool = False) -> None:
        """Den Knopf zeichnen - Geometrie nur bei geaenderter Groesse.

        **Der Grund ist gemessen, nicht geraten:** Ein `delete("all")` unter dem
        Mauszeiger zerstoert das Element, auf dem der Zeiger steht; Tk schickt
        daraufhin `<Leave>`, das zeichnet erneut, das erzeugt `<Enter>` - der
        Knopf flackert, solange der Zeiger auf ihm steht. Hover und Druck
        tauschen deshalb nur noch die FARBEN der bestehenden Elemente
        (`itemconfigure`), ohne sie zu loeschen.
        """
        b = max(1, self.winfo_width() or int(self["width"]))
        h = max(1, self.winfo_height() or int(self["height"]))
        if not erzwingen and (b, h) == self._groesse and self._text_item is not None:
            self._farben_setzen()
            return
        self._groesse = (b, h)
        plan = self._plan(hover=self._zeiger_drauf, gedrueckt=self._gedrueckt)
        self.delete("all")
        rand = int(self.radius)
        flaeche(self, 0, 0, b - 1, h - 1, rand, plan["flaeche"], plan["rand"])
        self._flaeche_items = self.find_all()
        self._text_item = self.create_text(
            b // 2, h // 2, text=self.text, fill=plan["schrift"],
            font=self.schrift_tupel,
        )
        self.configure(cursor="hand2" if (self.aktiv and self.command) else "")

    def _farben_setzen(self) -> None:
        """Nur die Farben der bestehenden Elemente tauschen - loescht nichts."""
        plan = self._plan(hover=self._zeiger_drauf, gedrueckt=self._gedrueckt)
        for kennung in self._flaeche_items:
            self.itemconfigure(kennung, fill=plan["flaeche"], outline=plan["rand"])
        if self._text_item is not None:
            self.itemconfigure(self._text_item, fill=plan["schrift"])

    # ------------------------------------------------------------- Zustand
    def setze_aktiv(self, aktiv: bool) -> None:
        """Ein- oder ausschalten. Ein ausgeschalteter Knopf nennt seinen Grund."""
        neu = bool(aktiv)
        if neu == self.aktiv:
            return
        self.aktiv = neu
        self.zeichnen()
        self.configure(cursor="hand2" if (self.aktiv and self.command) else "")

    def setze_text(self, text: str) -> None:
        self.text = text
        self.zeichnen()

    def setze_variante(self, variante: str) -> None:
        if variante == self.variante:
            return
        self.variante = variante
        self.zeichnen()

    def configure(self, cnf=None, **kwargs):        # noqa: A003 - Tk-Namen
        """`state=` wie bei ttk (normal/disabled) - der Rest geht an Tk."""
        if "state" in kwargs:
            self.setze_aktiv(str(kwargs.pop("state")) != "disabled")
        if "text" in kwargs:
            self.setze_text(str(kwargs.pop("text")))
        if kwargs or cnf:
            return super().configure(cnf, **kwargs)
        return None

    config = configure

    def cget(self, schluessel):
        """`state` und `text` wie bei einem ttk-Widget beantworten.

        Notwendig, weil Aufrufer (und Tests) `knopf["state"]` lesen - ein
        Canvas kennt diese Optionen nicht und wuerde mit TclError abbrechen.
        """
        if schluessel == "state":
            return "normal" if self.aktiv else "disabled"
        if schluessel == "text":
            return self.text
        return super().cget(schluessel)

    def __getitem__(self, schluessel):
        return self.cget(schluessel)

    # ------------------------------------------------------------- Ereignisse
    def _hinein(self, _e=None) -> None:
        if self._zeiger_drauf:
            return
        self._zeiger_drauf = True
        self._farben_setzen()
        if self.bei_hinweis and self.hinweis:
            self.bei_hinweis(self.hinweis)

    def _heraus(self, _e=None) -> None:
        if not self._zeiger_drauf and not self._gedrueckt:
            return
        self._zeiger_drauf = False
        self._gedrueckt = False
        self._farben_setzen()

    def _druck(self, _e=None) -> None:
        if not self.aktiv or self._gedrueckt:
            return
        self._gedrueckt = True
        self._farben_setzen()

    def _loslassen(self, _e=None) -> None:
        war = self._gedrueckt
        self._gedrueckt = False
        self.zeichnen()
        if war and self.aktiv and self.command:
            self.command()


class Karte(tk.Canvas):
    """Eine Flaeche mit runden Ecken, die Inhalt aufnimmt.

    `inhalt` ist ein `tk.Frame`, der ueber `create_window` in die Karte gelegt
    wird - so liegt echter Tk-Inhalt IN der runden Flaeche. Der Rahmen wird bei
    jeder Groessenaenderung neu gezeichnet; `rand` ist der Innenabstand.
    """

    def __init__(
        self,
        master,
        *,
        titel: str = "",
        farben: dict | None = None,
        schrift_tupel=("Consolas", 11),
        radius: int = RADIUS,
        rand: int = 10,
        fuellung: str = "blatt",
        randfarbe: str = "gitter",
        hoehe: int = 120,
        breite: int = 0,
        **kwargs,
    ) -> None:
        self.farben = farben or {}
        self.radius = radius
        self.rand = rand
        self.titel = titel
        self.schrift_tupel = schrift_tupel
        self.randfarbe = randfarbe
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("background", self.farben.get("bg", "#1e1e2e"))
        super().__init__(master, height=hoehe, width=(breite or 378), **kwargs)
        self.inhalt = tk.Frame(self, background=self.farben.get(fuellung, "#181825"))
        self._id = self.create_window(0, 0, anchor="nw", window=self.inhalt)
        self.bind("<Configure>", lambda _e: self.zeichnen())
        self.zeichnen()

    def zeichnen(self) -> None:
        b = max(1, self.winfo_width())
        h = max(1, self.winfo_height())
        self.delete("flaeche")
        flaeche(self, 0, 0, b - 1, h - 1, self.radius,
                self.farben.get("blatt", "#181825"),
                self.farben.get(self.randfarbe, "#313244"), tags=("flaeche",))
        self.tag_lower("flaeche")
        if self.titel:
            self.delete("titel")
            self.create_text(
                self.rand, 12, anchor="w", text=self.titel,
                fill=self.farben.get("akzent", "#89b4fa"),
                font=(self.schrift_tupel[0], self.schrift_tupel[1], "bold"),
                tags=("titel",),
            )
        self.coords(self._id, self.rand, self.rand + (14 if self.titel else 0))
        self.itemconfigure(
            self._id,
            width=max(1, b - 2 * self.rand),
            height=max(1, h - 2 * self.rand - (14 if self.titel else 0)),
        )


def fenster_ecken(root, praeferenz: int = 2) -> bool:
    """Dem eigenen Fenster runde Ecken geben (Windows 11, DWMWA 33).

    Windows 11 rundet Fenster nicht von selbst - ein Tk-Fenster ist ein
    Rechteck, auch wenn das System Menues und Dialoge rund zeichnet. Der Aufruf
    setzt `DWMWA_WINDOW_CORNER_PREFERENCE` (2 = rund) auf das Top-Level-Fenster
    hinter dem Tk-Handle. Rueckgabe: True, wenn Windows zugestimmt hat.

    Fehlertolerant: auf Windows 10, Linux oder ohne `dwmapi` gibt es die
    Funktion nicht - dann bleibt das Fenster eckig, und das ist kein Fehler.
    """
    try:
        import ctypes

        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        if not hwnd:
            hwnd = root.winfo_id()
        wert = ctypes.c_int(int(praeferenz))
        hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), 33, ctypes.byref(wert), ctypes.sizeof(wert)
        )
        return hr == 0
    except Exception:                                        # noqa: BLE001
        return False