"""
Omniquant-GUI — Live-Ansicht der Papierspur auf dem Prognose-Bericht.

Rein lesend: liest zustand.json, neuester.json und holt Kurse ueber
scanner/okx.letzter_kurs. Schreibt NICHTS — kein zustand, kein Journal,
keine Order. Der Dauerlauf (dauerlauf.py) bleibt der einzige Schreiber.

Start:  python gui.py            (im omniquant-Ordner, venv-Python)
Refresh: alle 15 Sekunden, Kurse aus einem Hintergrund-Thread (Netz darf
         die Oberflaeche nicht blockieren).
"""

import json
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone

# Scanner-Paket fuer Kurse (gleicher Weg wie handeln.py): HIER/../scanner
HIER = os.path.dirname(os.path.abspath(__file__))
for p in (os.path.join(HIER, "..", "scanner"), os.path.join(HIER, "..", "Bus")):
    if p not in sys.path:
        sys.path.insert(0, p)

UTC = timezone.utc
REFRESH_MS = 15_000

# Farben — dunkles Terminal, lesbar auch bei schlechtem Licht
FARBEN = {
    "bg": "#1e1e2e", "blatt": "#181825", "gitter": "#313244",
    "text": "#cdd6f4", "matt": "#a6adc8", "gruen": "#a6e3a1",
    "rot": "#f38ba8", "gelb": "#f9e2af", "akzent": "#89b4fa",
}


def g_uhrzeit(z):
    try:
        t = datetime.fromisoformat(z.replace("Z", "+00:00"))
        return t.astimezone().strftime("%d.%m. %H:%M")
    except Exception:
        return "?"


def zu_kurs(z):
    try:
        return float(z)
    except Exception:
        return None


class OmniquantGui:
    """Tk-Ansicht der Papierspur. Kein Schreibzugriff auf Spurdateien."""

    def __init__(self, root):
        self.root = root
        self.q_kurse = queue.Queue()
        self.kurse = {}          # inst -> kurs (Stand des letzten Worker-Laufs)
        self.bericht = {}        # neuester.json
        self.bericht_alter = None
        self.zustand = {}
        root.title("Omniquant (Papier) — Prognose-Treffer als Papierbuch")
        root.configure(bg=FARBEN["bg"])
        root.geometry("980x560")
        root.minsize(820, 420)
        self._baue()
        self.refresh_daten()
        root.after(REFRESH_MS, self._planer)

    # ---------- Aufbau ----------
    def _baue(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure(".", background=FARBEN["bg"], foreground=FARBEN["text"],
                     fieldbackground=FARBEN["blatt"], font=("Consolas", 10))
        st.configure("Treeview", background=FARBEN["blatt"],
                     fieldbackground=FARBEN["blatt"], foreground=FARBEN["text"],
                     rowheight=22, borderwidth=0)
        st.configure("Treeview.Heading", background="#313244",
                     foreground=FARBEN["akzent"], font=("Consolas", 10, "bold"))
        st.map("Treeview", background=[("selected", "#45475a")])

        # Kopf: drei Infozeilen
        kopf = tk.Frame(self.root, bg=FARBEN["bg"])
        kopf.pack(fill="x", padx=10, pady=(8, 4))
        self.l_modus = tk.Label(kopf, bg=FARBEN["bg"], font=("Consolas", 12, "bold"))
        self.l_modus.pack(side="left")
        self.l_bericht = tk.Label(kopf, bg=FARBEN["bg"], font=("Consolas", 10))
        self.l_bericht.pack(side="right")
        z2 = tk.Frame(self.root, bg=FARBEN["bg"])
        z2.pack(fill="x", padx=10, pady=(0, 6))
        self.l_lauf = tk.Label(z2, bg=FARBEN["bg"], font=("Consolas", 10))
        self.l_lauf.pack(side="left")
        self.l_takt = tk.Label(z2, bg=FARBEN["bg"], font=("Consolas", 10),
                               fg=FARBEN["matt"])
        self.l_takt.pack(side="right")

        # Tabelle der Positionen
        rahmen = tk.Frame(self.root, bg=FARBEN["blatt"])
        rahmen.pack(fill="both", expand=True, padx=10)
        spalten = ("inst", "seite", "einstieg", "kurs", "stop", "ziel",
                   "abstand", "wert", "gv")
        self.tree = ttk.Treeview(rahmen, columns=spalten, show="headings",
                                 selectmode="browse")
        kopf_t = {"inst": "Instrument", "seite": "Seite", "einstieg": "Einstieg",
                  "kurs": "Kurs", "stop": "Stop", "ziel": "Ziel",
                  "abstand": "Abstand", "wert": "Wert USD", "gv": "G/V %"}
        breite = {"inst": 130, "seite": 60, "einstieg": 90, "kurs": 90,
                  "stop": 90, "ziel": 90, "abstand": 80, "wert": 90, "gv": 80}
        for s in spalten:
            self.tree.heading(s, text=kopf_t[s])
            self.tree.column(s, width=breite[s], anchor="e" if s not in
                             ("inst", "seite") else "w", stretch=s == "inst")
        sb = ttk.Scrollbar(rahmen, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # Fuss: Kapital/Grenzen
        fuss = tk.Frame(self.root, bg=FARBEN["bg"])
        fuss.pack(fill="x", padx=10, pady=(6, 8))
        self.l_einsatz = tk.Label(fuss, bg=FARBEN["bg"], font=("Consolas", 10, "bold"))
        self.l_einsatz.pack(side="left")
        self.l_verluste = tk.Label(fuss, bg=FARBEN["bg"], font=("Consolas", 10, "bold"))
        self.l_verluste.pack(side="left", padx=(18, 0))
        self.l_kill = tk.Label(fuss, bg=FARBEN["bg"], font=("Consolas", 10, "bold"))
        self.l_kill.pack(side="left", padx=(18, 0))
        self.l_status = tk.Label(fuss, bg=FARBEN["bg"], font=("Consolas", 10),
                                 fg=FARBEN["matt"])
        self.l_status.pack(side="right")

    # ---------- Daten ----------
    def refresh_daten(self):
        """Liest Spur + Bericht und startet den Kurs-Worker (Netz)."""
        self._lies_zustand()
        self._lies_bericht()
        self._starte_kurs_worker()
        self._zeige()

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
        """Naechster Refresh; wertet daneben abgelieferte Kurse aus."""
        try:
            while True:
                neu = self.q_kurse.get_nowait()
                self.kurse.update(neu)
        except queue.Empty:
            pass
        self.refresh_daten()
        self.root.after(REFRESH_MS, self._planer)

    # ---------- Anzeige ----------
    def _zeige(self):
        z = self.zustand
        modus = z.get("modus") or "papier"
        self.l_modus.config(text="MODUS: %s" % modus.upper(),
                            fg=(FARBEN["gruen"] if modus == "papier"
                                else FARBEN["gelb"]))
        self.l_bericht.config(text=self._bericht_text(),
                              fg=(FARBEN["gruen"]
                                  if (self.bericht_alter is not None
                                      and self.bericht_alter <= 26)
                                  else FARBEN["rot"]))
        self.l_lauf.config(text="letzter Lauf: %s   |   %d Position(en), Takt 15 min"
                            % (g_uhrzeit(z.get("letzter_lauf")) if z else "?-??-??",
                               len(z.get("positionen", []))))
        self.l_takt.config(text="Refresh alle %ds" % (REFRESH_MS // 1000))

        # Tabelle füllen
        for i in self.tree.get_children():
            self.tree.delete(i)
        pos = z.get("positionen", [])
        for p in sorted(pos, key=lambda x: (x.get("inst", ""),
                                            x.get("seite", ""))):
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
            self.tree.insert("", "end", values=(
                inst, seite,
                "%.4f" % einstieg if einstieg else "-",
                "%.4f" % kurs if kurs else "-",
                "%.4f" % stop if stop else "-",
                "%.4f" % ziel if ziel else "-",
                abstand, p.get("nominal", "-"),
                gv,
            ))

        # Fuss
        einsatz = z.get("einsatz_pro_position")
        self.l_einsatz.config(text="Einsatz: %s USD/Position"
                              % ("%.0f" % einsatz if einsatz else "?"))
        verluste = z.get("kumulierte_verluste", 0)
        farbe = FARBEN["text"]
        if verluste:
            farbe = FARBEN["rot"] if verluste > 0 else FARBEN["gruen"]
        self.l_verluste.config(text="kum. Verluste: %.0f USD" % -verluste,
                               fg=farbe)
        if z.get("kill_switch", False):
            self.l_kill.config(text="KILL-SWITCH AKTIV (keine neuen Einstiege)",
                               fg=FARBEN["rot"])
        else:
            self.l_kill.config(text="Kill-Switch: frei", fg=FARBEN["gruen"])
        self.l_status.config(text=g_uhrzeit(
            datetime.now(UTC).isoformat()) + " Uhr — nur lesend, schreibt nichts")

    def _bericht_text(self):
        b = self.bericht
        treffer = b.get("treffer") or b.get("ergebnisse") or []
        n = len(treffer) if isinstance(treffer, list) else "?"
        if self.bericht_alter is None:
            return "Bericht: -"
        alt = self.bericht_alter
        grenze = 26
        marke = "frisch" if alt <= grenze else "ZU ALT — Spur pausiert"
        return "Bericht: %.1f h alt (%s), %s Treffer" % (alt, marke, n)


def main():
    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.1)
    except Exception:
        pass
    OmniquantGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()