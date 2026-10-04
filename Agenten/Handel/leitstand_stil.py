"""Stil des Leitstands: ein dunkles ttk-Theme in den Farben der Zentrale.

Schriften sind benannt: ein Widget mit font=TEXT (o. ae.) waechst beim
Schriftwechsel von selbst mit, ohne dass es jemand einsammeln muss.
anwenden() ist wiederholbar - der Leitstand ruft es vor dem Aufbau, nach dem
Aufbau (die Zentrale setzt in _baue ihr eigenes Theme) und nach jedem
Schriftwechsel. Farben stehen nur hier; die Reiter nennen Stil- und Tagnamen.
"""

import tkinter as tk
from tkinter import font as tkfont, ttk

import handelszentrale as hz

# Zwei Regeln, beide am 04.10.2026 am Fenster gemessen
# (`leitstand_palette_check.py`):

# 1. `matt` hat hier einen ANDEREN Wert als die Hausquelle - ein Name, zwei
#    Werte, zwei hausweite Bedeutungen. Das ist der eigentliche
#    Wartungsfehler; der hellere Ton (#bac2de statt #a6adc8, 9.91:1 statt
#    7.37:1 auf der Datenflaeche) war eine Begruendung, kein Zufall, und
#    bleibt - nur mit ausdruecklichem Grund an der Quelle, damit ein
#    hausweites Umstellen eine bewusste Entscheidung bleibt.
# 2. `wahl` und `rand` waren zwei Namen fuer denselben Wert, den die Quelle
#    `auswahl` nennt. Drei Namen, eine Farbe - jetzt zwei, weil `rand` der
#    Quellenschluessel ist.
#
# `gedaempft` ist der Vordergrund GESPERRTER Knoepfe und der Grundlinie:
# ein gesperrter Knopf soll lesbar bleiben und aus der Reihe fallen, der
# Wert unter dem Standardtext ist dafuer die Absicht (4.75:1 auf der
# Datenflaeche). `zebra`, `dunkelgelb`, `rand` und `wahl` sind Flaechen,
# Rahmen und Auswahl - sie tragen keinen Text und werden nicht gegen
# 4.5:1 geprueft.
FARBEN = dict(hz.FARBEN,
              # `matt_flache` kommt aus der Quelle (9.91:1 auf blatt). Bis
              # 05.10.2026 stand hier `matt="#bac2de"` und ueberschrieb den
              # Quellwert - dieselbe Farbe unter zwei Namen. Der hellere Ton
              # ist geblieben, nur mit eigener Bedeutung.
              matt=hz.FARBEN["matt_flache"],
              gedaempft="#7f849c",     # Grundlinie, gesperrte Knoepfe
              # `auswahl` kommt aus der Hausquelle; `wahl` war ein zweiter
              # Name fuer denselben Wert (#45475a) und wird nicht mehr
              # gesetzt. Die Verwendungen (Text-Auswahl, Combobox-Liste,
              # Treeview, Reiter, Rollbalken) stehen jetzt auf `auswahl`.
              rand="#45475a",          # Rahmen
              zebra="#202031",
              hinweis="#fab387",       # statt #b35c00 auf Weiss
              dunkelgelb="#4a4128",
              # Beide Notaus-Toene tragen weissen Text mit 5.44:1. Bis
              # 05.10.2026 war der aktive heller (#e74c3c, 3.82:1) - an
              # dem einen Knopf, der sofort lesbar sein muss. Der
              # Unterschied liegt jetzt in der Helligkeit des Randes, nicht
              # in der Lesbarkeit der Beschriftung.
              notaus="#c0392b", notaus_aktiv="#c0392b")

# Benannte Schriften: (Name, Familie, relative Groesse, fett)
TEXT, FETT, TITEL, MONO, TABELLE = ("LeitText", "LeitFett", "LeitTitel",
                                    "LeitMono", "LeitTabelle")
_SCHRIFTEN = ((TEXT, "Segoe UI", 0, False), (FETT, "Segoe UI", 0, True),
              (TITEL, "Segoe UI", 2, True), (MONO, hz.SCHRIFT_ART, -1, False),
              (TABELLE, hz.SCHRIFT_ART, 0, False))

# Treeview-Tags, dunkel statt Pastell. Tabelle haengt "zebra" VOR die
# Tags der Zeile; in Tk 8.6 gewinnt der spaetere Tag.
TAGS = {
    "zebra": {"background": FARBEN["zebra"]},
    "wartet": {"background": FARBEN["dunkelgelb"], "foreground": FARBEN["gelb"]},
    "ueberlebt": {"background": FARBEN["zellgruen"], "foreground": FARBEN["gruen"]},
    "grundlinie": {"foreground": FARBEN["gedaempft"]},
}

ZEILE_FAKTOR = 1.5          # rowheight = Zeilenabstand der Tabellenschrift x Faktor
ABSTAND, ABSTAND_GROSS = 8, 12


def _familie(root, wunsch):
    return wunsch if wunsch in tkfont.families(root) else \
        tkfont.nametofont("TkDefaultFont", root).actual("family")


def schriften(root, groesse):
    """Benannte Schriften anlegen bzw. auf die neue Groesse setzen."""
    # Am Root festhalten: ein eingesammeltes Font-Objekt loescht die Tk-Schrift.
    gehalten = root.__dict__.setdefault("_leit_schriften", {})
    for name, familie, rel, fett in _SCHRIFTEN:
        werte = {"family": _familie(root, familie), "size": groesse + rel,
                 "weight": "bold" if fett else "normal"}
        if name in gehalten:
            gehalten[name].configure(**werte)
        else:
            gehalten[name] = tkfont.Font(root, name=name, exists=False, **werte)


def zeilenhoehe(root):
    return max(18, round(tkfont.nametofont(TABELLE, root).metrics("linespace")
                         * ZEILE_FAKTOR))


def tags(baum):
    for name, werte in TAGS.items():
        baum.tag_configure(name, **werte)


def anwenden(root, groesse):
    schriften(root, groesse)
    f = FARBEN
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except tk.TclError:
        pass
    root.configure(bg=f["bg"])
    # tk-Widgets (Text, Toplevel, Tooltip, Combobox-Liste) ueber die Optionsdatenbank
    for muster, wert in (("*Background", f["bg"]), ("*Foreground", f["text"]),
                         ("*Text.background", f["blatt"]),
                         ("*Text.foreground", f["text"]),
                         ("*Text.insertBackground", f["text"]),
                         ("*Text.selectBackground", f["auswahl"]),
                         ("*Text.font", MONO),
                         ("*TCombobox*Listbox.background", f["blatt"]),
                         ("*TCombobox*Listbox.foreground", f["text"]),
                         ("*TCombobox*Listbox.selectBackground", f["auswahl"]),
                         ("*TCombobox*Listbox.font", TEXT),
                         # Feldschrift ist bei ttk eine Widget-Option, kein Stil
                         ("*TEntry.font", TEXT), ("*TCombobox.font", TEXT),
                         ("*TSpinbox.font", TEXT)):
        root.option_add(muster, wert)

    st.configure(".", background=f["bg"], foreground=f["text"],
                 fieldbackground=f["blatt"], bordercolor=f["rand"],
                 lightcolor=f["bg"], darkcolor=f["bg"], troughcolor=f["blatt"],
                 selectbackground=f["auswahl"], selectforeground=f["text"],
                 insertcolor=f["text"], focuscolor=f["akzent"], font=TEXT)
    st.map(".", foreground=[("disabled", f["gedaempft"])])
    st.configure("TButton", background=f["gitter"], padding=(10, 4))
    st.map("TButton", background=[("disabled", f["bg"]), ("pressed", f["akzent"]),
                                  ("active", f["auswahl"])],
           foreground=[("disabled", f["gedaempft"]), ("pressed", f["bg"])],
           bordercolor=[("focus", f["akzent"])])
    for feld in ("TEntry", "TSpinbox", "TCombobox"):
        st.configure(feld, fieldbackground=f["blatt"], foreground=f["text"],
                     insertcolor=f["text"], arrowcolor=f["matt"],
                     background=f["gitter"], padding=3)
        st.map(feld, bordercolor=[("focus", f["akzent"])],
               lightcolor=[("focus", f["akzent"])],
               fieldbackground=[("readonly", f["blatt"]), ("disabled", f["bg"])],
               foreground=[("disabled", f["gedaempft"]), ("readonly", f["text"])],
               selectbackground=[("readonly", f["blatt"])],
               selectforeground=[("readonly", f["text"])])
    for knopf in ("TCheckbutton", "TRadiobutton"):
        st.configure(knopf, indicatorbackground=f["blatt"],
                     indicatorforeground=f["text"])
        st.map(knopf, background=[("active", f["bg"])],
               indicatorbackground=[("selected", f["akzent"])])
    st.configure("Treeview", background=f["blatt"], fieldbackground=f["blatt"],
                 foreground=f["text"], font=TABELLE, rowheight=zeilenhoehe(root),
                 borderwidth=0)
    st.map("Treeview", background=[("selected", f["auswahl"])],
           foreground=[("selected", f["text"])])
    st.configure("Treeview.Heading", background=f["gitter"],
                 foreground=f["akzent"], font=FETT, padding=(6, 4), relief="flat")
    st.map("Treeview.Heading", background=[("active", f["auswahl"])])
    st.configure("TNotebook", background=f["bg"], borderwidth=0)
    st.configure("TNotebook.Tab", background=f["gitter"], foreground=f["text"],
                 padding=(14, 5), font=TEXT)
    st.map("TNotebook.Tab", background=[("selected", f["auswahl"])],
           foreground=[("selected", f["akzent"])])
    st.configure("TScrollbar", background=f["gitter"], troughcolor=f["blatt"],
                 arrowcolor=f["matt"], bordercolor=f["bg"])
    st.map("TScrollbar", background=[("active", f["auswahl"])])
    st.configure("Sash", sashthickness=6, gripcount=0, background=f["gitter"])
    st.configure("TLabelframe", background=f["bg"], bordercolor=f["rand"])
    st.configure("TLabelframe.Label", foreground=f["akzent"], font=FETT)
    # Benannte Label-Stile: die Reiter sagen, WAS etwas ist, nicht wie es aussieht.
    st.configure("Hinweis.TLabel", foreground=f["hinweis"])
    st.configure("Matt.TLabel", foreground=f["matt"])
    st.configure("Fehler.TLabel", foreground=f["rot"])
    st.configure("Titel.TLabel", foreground=f["akzent"], font=TITEL)
    st.configure("Kopf.TLabel", foreground=f["akzent"], font=FETT)
    st.configure("Warnung.TLabel", background=f["dunkelgelb"],
                 foreground=f["gelb"], padding=(8, 6))
    return st
