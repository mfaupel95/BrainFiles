"""
Omniquant-GUI — Live-Ansicht der Papierspur auf dem Prognose-Bericht.

Rein lesend: liest zustand.json, neuester.json, handelsjournal.csv und holt
Kurse/Kerzen ueber scanner/okx. Schreibt NICHTS — kein zustand, kein Journal,
keine Order. Der Dauerlauf (dauerlauf.py) bleibt der einzige Schreiber.

Start:  python gui.py            (im omniquant-Ordner, venv-Python)
Refresh: alle 15 Sekunden; Kurse/Kerzen aus Hintergrund-Threads (Netz darf
         die Oberflaeche nicht blockieren).
```

Layout: Kopf (Modus/Bericht/Lauf) · Positionstabelle · Zeile "letzte
Schließungen" · Kerzenchart (Klick auf eine Zeile waehlt das Instrument) ·
Fuss (Einsatz/Verluste/Kill-Switch).
"""

import csv
import importlib.util
import json
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone

# Scanner-Paket fuer Kurse/Kerzen (gleicher Weg wie handeln.py): HIER/../scanner.
# HIER selbst steht mit drin: auswertung.py liegt neben dieser Datei, und der
# Import soll auch dann greifen, wenn die GUI aus einem anderen Ordner startet.
HIER = os.path.dirname(os.path.abspath(__file__))
for p in (HIER, os.path.join(HIER, "..", "scanner"),
          os.path.join(HIER, "..", "Bus")):
    if p not in sys.path:
        sys.path.insert(0, p)

import auswertung                                            # noqa: E402

UTC = timezone.utc
REFRESH_MS = 15_000
BERICHTS_GRENZE_H = 26.0
CHART_KERZEN = 90

# Farben, Schrift, Abstaende und ttk-Stile kommen aus EINER Quelle:
# `Werkzeuge/fenster_design.py`. Bis 04.10.2026 stand hier eine vollstaendige
# Kopie der Palette (12 Schluessel) - heute wertgleich, aber ungebunden: eine
# Aenderung in der Quelle erreicht dieses Fenster nicht mehr, und `auswahl`
# fehlte bereits. Genau das ist der Wartungsfehler, den die Quelle in ihrem
# eigenen Kopf als Grund fuer ihre Existenz nennt.
#
# Geladen per Dateipfad, nicht ueber sys.path: ein Eintrag auf `Werkzeuge/`
# wuerde dort liegende Module einblenden und gleichnamige in `Handel/`
# verdecken (dort liegt `marktdaten.py`).
_spec = importlib.util.spec_from_file_location(
    "fenster_design",
    os.path.join(os.path.dirname(HIER), "..", "Werkzeuge",
                 "fenster_design.py"))
design = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(design)

FARBEN = design.FARBEN
SCHRIFT_ART = design.SCHRIFT_ART
SCHRIFT_GROESSE = design.SCHRIFT_GROESSE
KLEIN = design.KLEIN       # Fusszeile, Nebeninfo
TINY = design.TINY         # Chart-Beschriftung


def schrift(rel=0, fett=False):
    """Schriftart dieser Ansicht: (veraenderliche) Basis + relative Groesse."""
    return design.schrift(SCHRIFT_GROESSE, rel, fett)


def g_uhrzeit(z):
    try:
        t = datetime.fromisoformat(z.replace("Z", "+00:00"))
        return t.astimezone().strftime("%d.%m. %H:%M")
    except Exception:
        return "?"


def g_zeit_kurz(z):
    try:
        t = datetime.fromisoformat(z.replace("Z", "+00:00"))
        return t.astimezone().strftime("%d.%m. %H:%M")
    except Exception:
        return "?"


def fuss_texte(z, w):
    """Die Fusszeilen-Texte aus Zustand und Wachen. Reine Funktion.

    Damit ist die Bindung pruefbar, ohne ein Fenster zu oeffnen - und genau
    die war falsch: Die Fusszeile las einsatz_pro_position,
    kumulierte_verluste und kill_switch, drei Felder, die es im Zustand
    nicht gibt. Sie zeigte "?" und "0 USD" unabhaengig vom echten Zustand,
    und der Kill-Switch stand auch bei gerissenem Deckel auf "frei".
    Gelesen werden die Namen, die handeln.py schreibt (verluste_usd) und die
    Grenzen aus wachen.json; der Kill-Switch ist die Rechnung, kein Feld.

    Rueckgabe: (einsatz, verluste, kill, kill_aktiv)
    """
    einsatz = w.get("max_einsatz_je_position_usd")
    verluste = float(z.get("verluste_usd") or 0.0)
    deckel = float(w.get("max_gesamt_risiko_usd") or 0.0)
    kill_aktiv = bool(deckel) and verluste >= deckel
    return (
        "Einsatz: %s USD/Position" % ("%.0f" % einsatz if einsatz else "?"),
        "kum. Verluste: %.2f USD" % verluste,
        ("KILL-SWITCH AKTIV (keine neuen Einstiege)" if kill_aktiv
         else "Kill-Switch: frei%s"
              % (" (Deckel %.0f USD)" % deckel if deckel else "")),
        kill_aktiv,
    )


def kurs_fmt(wert):
    """Genauigkeit passend zur Preisgroesse: 0.05697 -> 5, 2471 -> 1."""
    try:
        w = float(wert)
    except Exception:
        return "-"
    if w >= 1000:
        return "%.1f" % w
    if w >= 10:
        return "%.2f" % w
    if w >= 1:
        return "%.3f" % w
    return "%.5f" % w


class OmniquantGui:
    """Tk-Ansicht der Papierspur. Kein Schreibzugriff auf Spurdateien."""

    def __init__(self, root, eigener_timer=True):
        self.root = root
        self.eigener_timer = eigener_timer
        self.q_kurse = queue.Queue()
        self.q_chart = queue.Queue()
        self.kurse = {}          # inst -> kurs (Stand des letzten Worker-Laufs)
        self.bericht = {}
        self.bericht_alter = None
        self.zustand = {}
        self.wachen = {}         # Grenzen (Einsatz, Risikodeckel) aus wachen.json
        self.auswertung = []     # Bilanzzeilen aus auswertung.kernzeilen()
        self.journal = []        # letzte Schliessungen (AUSSTIEG/ZWANGSSCHLUSS)
        self.aktiv_inst = None   # fuer den Chart gewaehltes Instrument
        self.chart_wunsch = None
        root.title("Omniquant (Papier) — Prognose-Treffer als Papierbuch")
        root.configure(bg=FARBEN["bg"])
        root.geometry("1020x760")
        root.minsize(840, 560)
        self._baue()
        self.refresh_daten()
        if eigener_timer:
            root.after(REFRESH_MS, self._planer)

    # ---------- Aufbau ----------
    def _baue(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure(".", background=FARBEN["bg"], foreground=FARBEN["text"],
                     fieldbackground=FARBEN["blatt"], font=schrift(KLEIN))
        st.configure("Treeview", background=FARBEN["blatt"],
                     fieldbackground=FARBEN["blatt"], foreground=FARBEN["text"],
                     rowheight=design.zeilenhoehe(SCHRIFT_GROESSE),
                     borderwidth=0)
        # Die beiden Literale `#313244` und `#45475a` waren wertgleich zu
        # FARBEN["gitter"] und FARBEN["auswahl"] - in derselben Datei, drei
        # Zeilen unter der eigenen Palette. Sie jetzt aus der Quelle zu
        # holen ist der ganze Sinn der Quelle.
        st.configure("Treeview.Heading", background=FARBEN["gitter"],
                     foreground=FARBEN["akzent"], font=schrift(KLEIN, fett=True))
        st.map("Treeview", background=[("selected", FARBEN["auswahl"])])

        # Kopf: Modus + Bericht
        kopf = tk.Frame(self.root, bg=FARBEN["bg"])
        kopf.pack(fill="x", padx=10, pady=(8, 2))
        self.l_modus = tk.Label(kopf, bg=FARBEN["bg"],
                                font=schrift(1, fett=True))
        self.l_modus.pack(side="left")
        self.l_bericht = tk.Label(kopf, bg=FARBEN["bg"],
                                  font=schrift(KLEIN))
        self.l_bericht.pack(side="right")
        z2 = tk.Frame(self.root, bg=FARBEN["bg"])
        z2.pack(fill="x", padx=10, pady=(0, 4))
        self.l_lauf = tk.Label(z2, bg=FARBEN["bg"], font=schrift(KLEIN))
        self.l_lauf.pack(side="left")
        self.l_takt = tk.Label(z2, bg=FARBEN["bg"], font=schrift(KLEIN),
                               fg=FARBEN["matt"])
        self.l_takt.pack(side="right")

        # Positionstabelle
        rahmen = tk.Frame(self.root, bg=FARBEN["blatt"])
        rahmen.pack(fill="x", padx=10)
        spalten = ("inst", "seite", "einstieg", "kurs", "stop", "ziel",
                   "abstand", "wert", "gv")
        self.tree = ttk.Treeview(rahmen, columns=spalten, show="headings",
                                 selectmode="browse", height=6)
        kopf_t = {"inst": "Instrument", "seite": "Seite", "einstieg": "Einstieg",
                  "kurs": "Kurs", "stop": "Stop", "ziel": "Ziel",
                  "abstand": "Abstand", "wert": "Wert USD", "gv": "G/V %"}
        breite = {"inst": 150, "seite": 60, "einstieg": 90, "kurs": 90,
                  "stop": 90, "ziel": 90, "abstand": 80, "wert": 90, "gv": 80}
        for s in spalten:
            self.tree.heading(s, text=kopf_t[s])
            self.tree.column(s, width=breite[s],
                             anchor="e" if s not in ("inst", "seite") else "w",
                             stretch=s == "inst")
        sb = ttk.Scrollbar(rahmen, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._gewaehlt)

        # Zeile: letzte Schliessungen
        self.l_schluesse = tk.Label(self.root, bg=FARBEN["bg"],
                                    font=schrift(TINY), fg=FARBEN["matt"],
                                    anchor="w", justify="left", wraplength=980)
        self.l_schluesse.pack(fill="x", padx=10, pady=(4, 2))

        # Auswertung: die Bilanz aus dem Journal, aus derselben Quelle wie
        # der Tagesbericht (auswertung.kernzeilen). Rein lesend.
        self.l_ausw_titel = tk.Label(self.root, bg=FARBEN["bg"],
                                     font=schrift(KLEIN, fett=True),
                                     fg=FARBEN["akzent"], anchor="w",
                                     text="Auswertung (Journal)")
        self.l_ausw_titel.pack(fill="x", padx=10, pady=(2, 0))
        self.l_auswertung = tk.Label(self.root, bg=FARBEN["bg"],
                                     font=schrift(TINY), fg=FARBEN["matt"],
                                     anchor="w", justify="left", wraplength=980)
        self.l_auswertung.pack(fill="x", padx=10, pady=(0, 2))

        # Chart
        self.l_chart_titel = tk.Label(self.root, bg=FARBEN["bg"],
                                      font=schrift(KLEIN, fett=True),
                                      fg=FARBEN["akzent"], anchor="w")
        self.l_chart_titel.pack(fill="x", padx=10, pady=(0, 0))
        self.canvas = tk.Canvas(self.root, bg=FARBEN["blatt"], height=200,
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10)

        # Fuss
        fuss = tk.Frame(self.root, bg=FARBEN["bg"])
        fuss.pack(fill="x", padx=10, pady=(4, 6))
        self.l_einsatz = tk.Label(fuss, bg=FARBEN["bg"],
                                  font=schrift(KLEIN, fett=True))
        self.l_einsatz.pack(side="left")
        self.l_verluste = tk.Label(fuss, bg=FARBEN["bg"],
                                   font=schrift(KLEIN, fett=True))
        self.l_verluste.pack(side="left", padx=(18, 0))
        self.l_kill = tk.Label(fuss, bg=FARBEN["bg"],
                               font=schrift(KLEIN, fett=True))
        self.l_kill.pack(side="left", padx=(18, 0))
        self.l_status = tk.Label(fuss, bg=FARBEN["bg"],
                                 font=schrift(KLEIN), fg=FARBEN["matt"])
        self.l_status.pack(side="right")

    # ---------- Daten ----------
    def refresh_daten(self):
        """Liest Spur + Bericht und startet den Kurs-Worker (Netz)."""
        self._lies_wachen()
        self._lies_zustand()
        self._lies_bericht()
        self._lies_journal()
        self._lies_auswertung()
        self._starte_kurs_worker()
        self._zeige()
        self._chart_impuls()

    def _lies_wachen(self):
        try:
            with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
                self.wachen = json.load(f)
        except Exception:
            self.wachen = {}

    def _lies_auswertung(self):
        """Die Bilanz aus dem Journal - dieselbe Quelle wie der Tagesbericht."""
        try:
            self.auswertung = auswertung.kernzeilen(
                os.path.join(HIER, "handelsjournal.csv"))
        except Exception as e:                               # noqa: BLE001
            self.auswertung = ["Auswertung nicht lesbar: %s" % str(e)[:80]]

    def _lies_zustand(self):
        try:
            with open(os.path.join(HIER, "zustand.json"), encoding="utf-8") as f:
                self.zustand = json.load(f)
        except Exception:
            self.zustand = {}

    def _lies_bericht(self):
        try:
            with open(os.path.join(HIER, "..", "prognose_berichte",
                                   "neuester.json"), encoding="utf-8") as f:
                self.bericht = json.load(f)
        except Exception:
            self.bericht = {}
        try:
            pfad = os.path.join(HIER, "..", "prognose_berichte", "neuester.json")
            alter_s = (datetime.now(UTC) - datetime.fromtimestamp(
                os.path.getmtime(pfad), UTC)).total_seconds()
            self.bericht_alter = alter_s / 3600
        except Exception:
            self.bericht_alter = None

    def _lies_journal(self):
        """Letzte 6 Schliess-Eintraege (AUSSTIEG/ZWANGSSCHLUSS), zeitlich neu."""
        try:
            pfad = os.path.join(HIER, "handelsjournal.csv")
            with open(pfad, encoding="utf-8", newline="") as f:
                zeilen = list(csv.DictReader(f))
            zu = [z for z in zeilen
                  if z.get("aktion") in ("AUSSTIEG", "ZWANGSSCHLUSS")]
            zu.sort(key=lambda z: z.get("zeit", ""), reverse=True)
            self.journal = zu[:6]
        except Exception:
            self.journal = []

    def _starte_kurs_worker(self):
        insts = sorted({p.get("inst") for p in
                        self.zustand.get("positionen", []) if p.get("inst")})
        t = threading.Thread(target=self._kurs_worker, args=(insts,),
                             daemon=True)
        t.start()

    def _kurs_worker(self, insts):
        import okx
        neu = {}
        for inst in insts:
            try:
                k = okx.letzter_kurs(inst)
                if k is not None:
                    neu[inst] = float(k)
            except Exception:
                pass  # Kurs gerade nicht erreichbar -> alte Anzeige behalten
        self.q_kurse.put(neu)

    def _planer(self):
        """Naechster Refresh; wertet abgelieferte Kurse/Charts aus.

        Im Leitstand (eigener_timer=False) plant er den naechsten Timer NICHT
        selbst - der Leitstand-Takt (5 s) ruft ihn ueber refresh() auf. Sonst
        liefen zwei Timer auf dieselbe Datei (T-345).
        """
        try:
            while True:
                neu = self.q_kurse.get_nowait()
                self.kurse.update(neu)
        except queue.Empty:
            pass
        self._chart_ergebnis()
        self.refresh_daten()
        if self.eigener_timer:
            self.root.after(REFRESH_MS, self._planer)

    # ---------- Chart ----------
    def _gewaehlt(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        werte = self.tree.item(sel[0], "values")
        if not werte:
            return
        inst = werte[0]
        self.chart_wunsch = inst
        self._chart_impuls()

    def _chart_impuls(self):
        """Laedt Kerzen fuer das gewuenschte Instrument im Hintergrund."""
        inst = self.chart_wunsch
        if not inst:
            # Ohne Auswahl: erstes Instrument der Tabelle vorbelegen
            pos = self.zustand.get("positionen", [])
            if pos:
                inst = pos[0].get("inst")
                self.chart_wunsch = inst
        if not inst:
            self._zeichne_chart(None, None, None)
            return
        if self.aktiv_inst == inst and self.q_chart.empty():
            return  # schon geladen
        self.l_chart_titel.config(text="%s  —  lade Tageskerzen …" % inst)
        t = threading.Thread(target=self._chart_worker, args=(inst,),
                             daemon=True)
        t.start()

    def _chart_worker(self, inst):
        import okx
        try:
            k = okx.kerzen(inst, bar="1D", anzahl=CHART_KERZEN)
            self.q_chart.put((inst, [list(map(float, kz)) for kz in k]))
        except Exception as e:
            self.q_chart.put((inst, None, str(e)))

    def _chart_ergebnis(self):
        try:
            while True:
                daten = self.q_chart.get_nowait()
                inst = daten[0]
                self.aktiv_inst = inst
                k = daten[1]
                fehler = daten[2] if len(daten) > 2 else None
                self._zeichne_chart(inst, k, fehler)
        except queue.Empty:
            pass

    def _zeichne_chart(self, inst, kerzen, fehler):
        c = self.canvas
        c.delete("all")
        breite = max(c.winfo_width(), 400)
        hoehe = max(c.winfo_height(), 180)
        rand_l, rand_r, rand_o, rand_u = 52, 12, 8, 18
        if fehler or not kerzen:
            c.create_text(breite // 2, hoehe // 2,
                          text="Keine Kerzen verfuegbar%s"
                          % (": " + fehler if fehler else ""),
                          fill=FARBEN["matt"], font=schrift(KLEIN))
            return

        pos = {p.get("inst"): p for p in self.zustand.get("positionen", [])}
        p = pos.get(inst)
        if not p:
            # Instrument aus Tabelle, aber nicht mehr offen -> Position weg
            c.create_text(breite // 2, hoehe // 2,
                          text="%s: Position nicht mehr offen" % inst,
                          fill=FARBEN["matt"], font=schrift(KLEIN))
            return

        einstieg = float(p.get("einstieg") or 0)
        stop = float(p.get("stop") or 0)
        ziel = float(p.get("ziel") or 0)
        seite = p.get("seite") or "long"

        # Wertebereich: Kerzen + Linien, mit Puffer
        tief, hoch = min(k[3] for k in kerzen), max(k[2] for k in kerzen)
        tief = min(tief, einstieg, stop if stop else tief, ziel if ziel else tief)
        hoch = max(hoch, einstieg, stop if stop else hoch, ziel if ziel else hoch)
        spanne = (hoch - tief) or 1
        tief -= spanne * 0.06
        hoch += spanne * 0.06

        def x(i):
            n = len(kerzen)
            abstand = (breite - rand_l - rand_r) / n
            return rand_l + abstand * (i + 0.5)

        def y(w):
            return rand_o + (hoehe - rand_o - rand_u) * (1 - (w - tief) / (hoch - tief))

        # Gitter + Preisachse
        for s in range(5):
            ys = rand_o + (hoehe - rand_o - rand_u) * s / 4
            c.create_line(rand_l, ys, breite - rand_r, ys,
                          fill=FARBEN["gitter"], width=1)
            preis = hoch - (hoch - tief) * s / 4
            c.create_text(rand_l - 4, ys, text=kurs_fmt(preis),
                          anchor="e", fill=FARBEN["matt"], font=schrift(-3))

        # Kerzen
        n = len(kerzen)
        kbreite = max(2.0, (breite - rand_l - rand_r) / n * 0.62)
        for i, k in enumerate(kerzen):
            o, h, l, cl = k[1], k[2], k[3], k[4]
            farbe = FARBEN["zellgruen"] if cl >= o else FARBEN["zellrot"]
            c.create_line(x(i), y(l), x(i), y(h), fill=farbe, width=1)
            yo, yc = y(o), y(cl)
            if abs(yo - yc) < 1:
                yo = yc - 1
            c.create_rectangle(x(i) - kbreite, yo, x(i) + kbreite, yc,
                               fill=farbe, outline=farbe)

        # Linien: Einstieg/Stop/Ziel mit Beschriftung am rechten Rand
        linien = []
        if einstieg:
            linien.append(("Einstieg", einstieg, FARBEN["blau"]))
        if stop:
            linien.append(("Stop", stop, FARBEN["rot"]))
        if ziel:
            linien.append(("Ziel", ziel, FARBEN["gruen"]))
        for name, wert, farbe in linien:
            if wert <= 0 or not (tief <= wert <= hoch):
                continue
            ys = y(wert)
            c.create_line(rand_l, ys, breite - rand_r, ys, fill=farbe,
                          width=1, dash=(4, 3))
            c.create_text(breite - rand_r + 1, ys,
                          text=name, anchor="w", fill=farbe,
                          font=schrift(-3, fett=True))

        # Datumsachse (Anfang/Ende)
        if n:
            c.create_text(rand_l, hoehe - 4, text="%s" % kerzen[0][0],
                          anchor="w", fill=FARBEN["matt"], font=schrift(-3))
            c.create_text(breite - rand_r, hoehe - 4, text="%s" % kerzen[-1][0],
                          anchor="e", fill=FARBEN["matt"], font=schrift(-3))

        self.l_chart_titel.config(
            text="%s  %s   —  %d Tageskerzen, Einstieg %s (Stop %s, Ziel %s)"
            % (inst, seite, n, kurs_fmt(einstieg),
               kurs_fmt(stop) if stop else "-",
               kurs_fmt(ziel) if ziel else "-"))

    # ---------- Anzeige ----------
    def _zeige(self):
        z = self.zustand
        modus = z.get("modus") or "papier"
        self.l_modus.config(text="MODUS: %s" % modus.upper(),
                            fg=(FARBEN["gruen"] if modus == "papier"
                                else FARBEN["gelb"]))
        bericht_text = self._bericht_text()
        alter_ok = (self.bericht_alter is not None
                    and self.bericht_alter <= BERICHTS_GRENZE_H)
        self.l_bericht.config(text=bericht_text,
                              fg=(FARBEN["gruen"] if alter_ok else FARBEN["rot"]))
        self.l_lauf.config(
            text="letzter Lauf: %s   |   %d Position(en), Takt 15 min"
            % (g_uhrzeit(z.get("letzter_lauf")) if z else "?-??-??",
               len(z.get("positionen", []))))
        self.l_takt.config(text="Refresh alle %ds" % (REFRESH_MS // 1000))

        # Tabelle indizieren: inst -> Zeilen-ID zum Anklicken merken
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._zeilen_id = {}
        for p in sorted(self.zustand.get("positionen", []),
                        key=lambda x: (x.get("inst", ""), x.get("seite", ""))):
            inst = p.get("inst", "")
            seite = p.get("seite", "")
            einstieg = p.get("einstieg")
            kurs = self.kurse.get(inst) or p.get("kurs")
            stop = p.get("stop")
            ziel = p.get("ziel")
            abstand = ""
            if kurs and stop:
                vz = 1 if seite == "long" else -1
                ab = vz * (kurs / stop - 1) * 100
                abstand = "%+.1f%%" % ab
            gv = ""
            if kurs and einstieg:
                vz = 1 if seite == "long" else -1
                gv = "%+.1f%%" % (vz * (kurs / einstieg - 1) * 100)
            iid = self.tree.insert("", "end", values=(
                inst, seite, kurs_fmt(einstieg), kurs_fmt(kurs),
                kurs_fmt(stop), kurs_fmt(ziel), abstand,
                p.get("nominal", "-"), gv,
            ))
            self._zeilen_id[inst] = iid

        # Schliessungen
        if self.journal:
            teile = []
            for zr in self.journal:
                gv = ""
                try:
                    e = float(zr.get("einsatz_usd") or 0)
                    w = float(zr.get("wert_usd") or 0)
                    if e:
                        gv = "%+.1f %%" % ((w / e - 1) * 100)
                except Exception:
                    pass
                teile.append("%s %-9s %s %s → %s%s%s" % (
                    g_zeit_kurz(zr.get("zeit")), zr.get("inst", ""),
                    zr.get("seite", ""), zr.get("grund", ""),
                    kurs_fmt(zr.get("preis")),
                    "  " + gv if gv else "",
                    ""))
            self.l_schluesse.config(
                text="letzte Schließungen:   " + "   |   ".join(teile))
        else:
            self.l_schluesse.config(text="letzte Schließungen:  (noch keine)")

        # Auswertung
        self.l_auswertung.config(
            text="\n".join(self.auswertung) if self.auswertung
            else "keine Daten")

        # Fuss - Feldnamen so, wie handeln.py sie schreibt (verluste_usd),
        # und die Grenzen aus wachen.json (siehe fuss_texte).
        t_einsatz, t_verluste, t_kill, kill_aktiv = fuss_texte(z, self.wachen)
        self.l_einsatz.config(text=t_einsatz)
        self.l_verluste.config(text=t_verluste,
                               fg=(FARBEN["rot"]
                                   if float(z.get("verluste_usd") or 0.0) > 0
                                   else FARBEN["gruen"]))
        self.l_kill.config(text=t_kill,
                           fg=(FARBEN["rot"] if kill_aktiv
                               else FARBEN["gruen"]))
        self.l_status.config(text=g_uhrzeit(datetime.now(UTC).isoformat())
                             + " Uhr — nur lesend, schreibt nichts")

    def _bericht_text(self):
        b = self.bericht
        treffer = b.get("treffer") or b.get("ergebnisse") or []
        n = len(treffer) if isinstance(treffer, list) else "?"
        if self.bericht_alter is None:
            return "Bericht: -"
        alt = self.bericht_alter
        grenze = BERICHTS_GRENZE_H
        marke = "frisch" if alt <= grenze else "ZU ALT — Spur pausiert"
        return "Bericht: %.1f h alt (%s), %s Treffer" % (alt, marke, n)


class OmniquantReiter(ttk.Frame):
    """Leitstand-Wrapper: bettet OmniquantGui als Notebook-Reiter ein."""

    def __init__(self, eltern, leitstand):
        super().__init__(eltern)
        self.ls = leitstand
        # eigener_timer=False: der Leitstand-Takt (5 s) ruft _planer() ueber
        # refresh() auf - sonst liefen zwei Timer auf dieselbe Datei (T-345).
        self._gui = OmniquantGui(self, eigener_timer=False)

    # Stubs fuer Fenster-Aufrufe aus OmniquantGui.__init__
    def title(self, s=None):
        return ""

    def geometry(self, s=None):
        pass

    def minsize(self, w=None, h=None):
        pass

    def configure(self, **kwargs):
        kwargs.pop("bg", None)
        kwargs.pop("background", None)
        if kwargs:
            super().configure(**kwargs)

    # Leitstand-Interface (OmniquantGui hat eigenen 15-s-Timer)
    # Leitstand-Interface (der 15-s-Timer ist im Leitstand abgeschaltet)
    def refresh(self):
        # Der Leitstand-Takt (5 s) ruft _planer() - das wertet die
        # Kurs-/Chart-Queues aus UND liest die Daten neu. refresh_daten()
        # allein wuerde den Chart nie zeichnen (T-345).
        try:
            self._gui._planer()
        except Exception:                       # noqa: BLE001
            # Ein Fehler darf den Leitstand nicht mitnehmen - der Timer
            # des Reiters laeuft weiter und der Naechste ist wieder da.
            pass

    def titel_zusatz(self):
        """Ein Punkt, wenn die Spur live laeuft. Sonst nichts."""
        z = getattr(self._gui, "zustand", None) or {}
        # Das Feld heisst `modus` (zustand.json der Spur), nicht `live` -
        # ein geratenes Feld faellt hier still aus und der Punkt bleibt aus.
        if isinstance(z, dict) and z.get("modus") == "live":
            return " ●"
        return ""

    def status(self):
        """Was in der Statusleiste steht - aus dem Gelesenen, nicht geraten."""
        g = self._gui
        teile = ["Omniquant"]
        bericht = getattr(g, "bericht", None)
        if isinstance(bericht, dict) and bericht:
            treffer = bericht.get("treffer") or bericht.get("ergebnisse") or []
            n = len(treffer) if isinstance(treffer, list) else "?"
            teile.append("%d Treffer" % n)
        alt = getattr(g, "bericht_alter", None)
        if isinstance(alt, (int, float)):
            teile.append("Bericht %.1f h alt" % alt)
        if self.titel_zusatz():
            teile.append("live")
        return " — ".join(teile)

    def abbrechbar(self):
        """Omniquant haelt keinen Hintergrundprozess - immer schliessbar."""
        return True


def main():
    # `dpi_bewusst()` statt `tk scaling 1.1` (Auftrag Max, 05.10.2026).
    # Gemessen: der Monitor ist 120 dpi, ein dpi-unawares Fenster sieht
    # 3072x1728 statt 3840x2160 - 36 % weniger Bildschirm, und Windows
    # stretcht das fertige Bitmap, wodurch jede Schrift weich wird.
    #
    # Der Aufruf muss VOR dem ersten `Tk()` laufen. `tk scaling` entfaellt:
    # es war ein Ersatz fuer genau das, was der Windows-Aufruf macht, und
    # beides zusammen ergibt 1.666 statt 1.25 (gemessen).
    #
    # Als Reiter im Leitstand kommt `main()` nicht vorbei - dort hat der
    # Leitstand den Aufruf schon gemacht (leitstand.py, Zeile 319), und
    # DPI-Awareness gilt prozessweit.
    design.dpi_bewusst()
    root = tk.Tk()
    OmniquantGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
