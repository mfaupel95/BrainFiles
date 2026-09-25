"""Das Fenster der Repos-Zentrale: Gruppen, Filter, fuenf Aktionen je Zeile.

Die Anzeigelogik (Filter, Gruppen, Hinweistext) steht bewusst als reine
Funktionen oben - sie ist ohne Fenster pruefbar. Die Klasse `Fenster` baut nur
zusammen, was scan/manifest/aktionen liefern, und rechnet nichts selbst.
"""

from __future__ import annotations

import subprocess
import threading
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk

import aktionen
import befehle
import manifest
import scan

GRUPPEN_TITEL = {
    "startbar": "STARTBAR",
    "einrichten": "EINRICHTEN",
    "neu": "NEU",
    "doku": "NUR DOKU",
    "fehlt": "FEHLT",
}
ERKLAERUNG = {
    "startbar": "Befehl belegt, Abhaengigkeiten da",
    "einrichten": "Einstieg da, es fehlt noch etwas",
    "neu": "Ordner ohne Eintrag im Manifest",
    "doku": "kein Programm, nur Text",
    "fehlt": "Manifest-Eintrag ohne Ordner",
}


# ------------------------------------------------------------------ Anzeigelogik
def gruppen_titel(gruppe: str, anzahl: int) -> str:
    """Ueberschrift einer Gruppe, mit dem Hinweis in Klammern: STARTBAR (4)."""
    return f"{GRUPPEN_TITEL.get(gruppe, gruppe.upper())} ({anzahl})"


def sichtbare_zeilen(zeilen: list[manifest.Zeile], suchtext: str) -> list[manifest.Zeile]:
    """Filtern ueber Ordnername, Bot und Notiz - Gross-/Kleinschreibung egal."""
    text = (suchtext or "").strip().lower()
    if not text:
        return list(zeilen)
    return [
        z
        for z in zeilen
        if text in z.ordner.lower()
        or text in (z.bot or "").lower()
        or text in (z.notiz or "").lower()
        or text in z.art.lower()
    ]


def nach_gruppen(zeilen: list[manifest.Zeile]) -> dict[str, list[manifest.Zeile]]:
    """Zeilen in die feste Gruppenreihenfolge legen; leere Gruppen fallen weg."""
    gruppen: dict[str, list[manifest.Zeile]] = {}
    for name in manifest.GRUPPEN_REIHENFOLGE:
        passende = [z for z in zeilen if z.gruppe == name]
        if passende:
            gruppen[name] = sorted(passende, key=lambda z: z.ordner.lower())
    return gruppen


def hinweis(zeile: manifest.Zeile) -> str:
    """Was in der Hinweisspalte steht: erst der Grund, sonst die Notiz."""
    if zeile.gruende:
        return "; ".join(zeile.gruende)
    if zeile.gruppe in ("doku", "neu", "fehlt"):
        return zeile.notiz
    return ""


# ------------------------------------------------------------------ Fenster
class Fenster:
    """Die Oberflaeche. `lauf` und `jetzt` sind fuer Tests ersetzbar."""

    def __init__(
        self,
        repos_basis: Path | str,
        manifest_pfad: Path | str,
        profile_dir: Path | str,
        log_ordner: Path | str,
        *,
        lauf=None,
        jetzt=None,
    ):
        self.repos_basis = Path(repos_basis)
        self.manifest_pfad = Path(manifest_pfad)
        self.profile_dir = Path(profile_dir)
        self.log_ordner = Path(log_ordner)
        self.lauf = lauf or self._popen
        self.jetzt = jetzt or datetime.now
        self.zeilen: list[manifest.Zeile] = []
        self.kinder: dict[str, manifest.Zeile] = {}   # Item-Id -> Zeile

        self.root = tk.Tk()
        self.root.title("Repos-Zentrale - Werkstatt/Repos")
        self.root.geometry("1280x880")
        self._bauen()
        self.aktualisieren()

    # ------------------------------------------------------------- Aufbau
    def _bauen(self) -> None:
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass

        oben = ttk.Frame(self.root)
        oben.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(oben, text="Filtern:").pack(side="left")
        self.suchtext = tk.StringVar()
        self.suchtext.trace_add("write", lambda *_: self.anzeigen())
        ttk.Entry(oben, textvariable=self.suchtext, width=40).pack(side="left", padx=6)
        ttk.Button(oben, text="Aktualisieren (Platte + Manifest)", command=self.aktualisieren).pack(
            side="left", padx=6
        )
        self.zusammenfassung = ttk.Label(oben, text="")
        self.zusammenfassung.pack(side="right")

        tabelle = ttk.Frame(self.root)
        tabelle.pack(fill="both", expand=True, padx=8)
        self.baum = ttk.Treeview(
            tabelle,
            columns=("art", "venv", "bot", "lauf", "hinweis"),
            show="tree headings",
            selectmode="browse",
        )
        self.baum.heading("#0", text="Projekt")
        self.baum.column("#0", width=260, anchor="w")
        for spalte, titel, breite in (
            ("art", "Art", 110),
            ("venv", "venv", 60),
            ("bot", "Bot", 160),
            ("lauf", "letzter Start", 130),
            ("hinweis", "Hinweis", 380),
        ):
            self.baum.heading(spalte, text=titel)
            self.baum.column(spalte, width=breite, anchor="w")
        self.baum.pack(side="left", fill="both", expand=True)
        rollbalken = ttk.Scrollbar(tabelle, orient="vertical", command=self.baum.yview)
        rollbalken.pack(side="right", fill="y")
        self.baum.configure(yscrollcommand=rollbalken.set)
        self.baum.bind("<<TreeviewSelect>>", lambda _: self._auswahl_geaendert())
        self.baum.bind("<Double-Button-1>", lambda _: self._log_oeffnen())

        self._bauen_details()

        unten = ttk.Frame(self.root)
        unten.pack(fill="x", padx=8, pady=8)
        self.knoepfe = {}
        for name, text, befehl in (
            ("ordner", "Ordner", self.ordner),
            ("terminal", "Terminal", self.terminal),
            ("start", "Starten", self.starten),
            ("bot", "Bot", self.bot_chat),
            ("doku", "Doku", self.doku),
        ):
            b = ttk.Button(unten, text=text, command=befehl, state="disabled")
            b.pack(side="left", padx=3)
            self.knoepfe[name] = b
        ttk.Button(unten, text="Log oeffnen", command=self._log_oeffnen).pack(side="left", padx=3)

        self.status = ttk.Label(self.root, text="", anchor="w", foreground="#3b5c86")
        self.status.pack(fill="x", padx=8, pady=(0, 8))

    # ------------------------------------------------------------- Daten
    def aktualisieren(self) -> None:
        """Platte und Manifest neu lesen (Knopf 'Aktualisieren')."""
        repos = scan.repos_scannen(self.repos_basis)
        eintraege = manifest.manifest_laden(self.manifest_pfad)
        self.zeilen = manifest.zeilen_bauen(
            repos, eintraege, self.profile_dir, self.repos_basis
        )
        self.anzeigen()
        self.status.configure(
            text=f"{len(repos)} Repos auf der Platte, {len(self.zeilen)} Zeilen, "
                 f"Manifest: {self.manifest_pfad}"
        )

    def anzeigen(self) -> None:
        """Die gefilterten Zeilen in den Baum schreiben."""
        self.baum.delete(*self.baum.get_children())
        self.kinder.clear()
        sichtbar = sichtbare_zeilen(self.zeilen, self.suchtext.get())
        gruppen = nach_gruppen(sichtbar)
        for name, zeilen in gruppen.items():
            kopf = self.baum.insert(
                "", "end", text=gruppen_titel(name, len(zeilen)), open=True,
                values=("", "", "", "", ERKLAERUNG.get(name, "")),
            )
            for z in zeilen:
                item = self.baum.insert(
                    kopf, "end", text=z.ordner,
                    values=(
                        z.art,
                        (z.repo.venv if z.repo and z.repo.venv else "-"),
                        (f"{z.bot}{'' if z.bot_da else ' (fehlt)'}" if z.bot else "-"),
                        self._letzter_start(z.ordner),
                        hinweis(z),
                    ),
                )
                self.kinder[item] = z
        self.zusammenfassung.configure(
            text=f"{len(sichtbar)} von {len(self.zeilen)} Zeilen"
        )
        self._details_fuellen(None)

    def _letzter_start(self, ordner: str) -> str:
        """Der letzte Startbeleg: neueste Logdatei dieses Repos, sonst leer."""
        treffer = sorted(
            self.log_ordner.glob(f"{ordner}-*.log"),
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
        rahmen.pack(fill="both", expand=False, padx=8, pady=(6, 0))

        links = ttk.Frame(rahmen)
        links.pack(side="left", fill="both", expand=True, padx=(6, 3), pady=6)
        self.anleitung_text = tk.Text(
            links, height=9, width=58, wrap="word", relief="flat", background="#f4f6f9"
        )
        self.anleitung_text.pack(side="left", fill="both", expand=True)
        self.anleitung_text.configure(state="disabled")
        leiste = ttk.Scrollbar(links, orient="vertical", command=self.anleitung_text.yview)
        leiste.pack(side="right", fill="y")
        self.anleitung_text.configure(yscrollcommand=leiste.set)

        rechts = ttk.Frame(rahmen)
        rechts.pack(side="left", fill="both", expand=True, padx=(3, 6), pady=6)
        self.befehlsbaum = ttk.Treeview(
            rechts, columns=("was", "befehl", "hinweis"), show="headings", selectmode="browse"
        )
        for spalte, titel, breite in (
            ("was", "Was", 190),
            ("befehl", "Befehl", 300),
            ("hinweis", "Hinweis", 190),
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
        leiste2.pack(side="left", fill="y", padx=(0, 6), pady=6)
        self.befehl_knoepfe = {}
        for name, text, befehl in (
            ("ausfuehren", "Befehl ausfuehren", self.befehl_ausfuehren),
            ("kopieren", "Befehl kopieren", self.befehl_kopieren),
            ("bot", "Bot damit beauftragen", self.befehl_an_bot),
        ):
            b = ttk.Button(leiste2, text=text, command=befehl, state="disabled")
            b.pack(side="top", fill="x", pady=2)
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
            self.status.configure(text=f"{k.was}: {k.hinweis}")

    def befehl_ausfuehren(self) -> None:
        """Den gewaehlten Befehl in einem sichtbaren Terminal im Repo starten."""
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
        self._ruf(
            aktionen.argv_befehl_im_terminal(z.repo.pfad, k.cmd),
            f"{k.was}: {befehle.befehl_text(k.cmd)}",
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
        self.status.configure(text=f"Kopiert: {text}")

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
        teile = [z.ordner, z.art]
        if z.notiz:
            teile.append(z.notiz)
        if z.gruende:
            teile.append("Hinweis: " + "; ".join(z.gruende))
        if z.start:
            teile.append("Start: " + " ".join(z.start))
        self.status.configure(text=" | ".join(teile))

    def _popen(self, argv: list[str]) -> subprocess.Popen:
        return subprocess.Popen(argv)

    def ordner(self) -> None:
        z = self._gewaehlt()
        if z and z.repo:
            self._ruf(aktionen.argv_ordner(z.repo.pfad), f"Ordner: {z.repo.pfad}")

    def terminal(self) -> None:
        z = self._gewaehlt()
        if z and z.repo:
            self._ruf(aktionen.argv_terminal(z.repo.pfad), "Terminal im Repo-Ordner")

    def bot_chat(self) -> None:
        z = self._gewaehlt()
        if z and z.repo and z.bot_da and z.bot:
            argv, cwd = aktionen.argv_bot(z.bot, z.repo.pfad)
            self._ruf(
                ["wt.exe", "-d", str(cwd)] + argv,
                f"Bot-Chat '{z.bot}' im Repo-Ordner",
            )

    def doku(self) -> None:
        z = self._gewaehlt()
        if z and z.repo and z.repo.readme:
            fehler = aktionen.doku_oeffnen(z.repo.pfad / z.repo.readme)
            self.status.configure(
                text=fehler or f"Doku geoeffnet: {z.repo.readme}"
            )

    def _log_oeffnen(self) -> None:
        z = self._gewaehlt()
        if not z:
            return
        treffer = sorted(
            self.log_ordner.glob(f"{z.ordner}-*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not treffer:
            self.status.configure(text=f"Kein Startbeleg fuer {z.ordner} - noch nie gestartet")
            return
        aktionen.doku_oeffnen(treffer[0])
        self.status.configure(text=f"Log: {treffer[0]}")

    def starten(self) -> None:
        z = self._gewaehlt()
        if z is None or not z.start_da:
            self.status.configure(text="Kein Startbefehl belegt - nichts gestartet")
            return
        self.status.configure(text=f"Starte {z.ordner}: {' '.join(z.start or [])} ...")
        threading.Thread(target=self._starten_im_hintergrund, args=(z,), daemon=True).start()

    def _starten_im_hintergrund(self, z: manifest.Zeile) -> None:
        ergebnis = aktionen.start_ausfuehren(z, self.log_ordner, jetzt=self.jetzt())
        if ergebnis.fehler:
            self.root.after(0, lambda: self._start_fertig(z, ergebnis))
            return
        self.root.after(
            0,
            lambda: self.status.configure(
                text=f"{z.ordner} gestartet (PID {ergebnis.pid}) - Ausgabe in {ergebnis.log}"
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
                    text=f"{z.ordner} beendet (Code {code}). Log: {ergebnis.log}"
                ),
            ),
        )

    def _ruf(self, argv: list[str], was: str) -> None:
        """Ein Fenster/Programm starten - Fehler landen in der Statuszeile."""
        try:
            self.lauf(argv)
        except OSError as e:
            self.status.configure(text=f"{was}: {type(e).__name__}: {e}")
            return
        self.status.configure(text=f"{was} gestartet")

    def _start_fertig(self, z: manifest.Zeile, ergebnis) -> None:
        self.status.configure(text=f"Startfehler bei {z.ordner}: {ergebnis.fehler}")
