"""Die beiden Fenster zum Scharfschalten und Entschaerfen einer Handels-Spur.

Verlangt von Wissen/Handelsregeln.md, Punkt 3 ("scharf geschaltet wird von
Hand, in einem Fenster, das die Werte anzeigt, sie aendern laesst und ein Feld
zum Bestaetigen hat") - dieselbe Regel, die `freigabe.py` fuer den einzelnen
Auftrag umsetzt.

Die Grenze, auf der das Ganze steht:

    Dieses Fenster ordert nicht. Es schaltet einen Schalter.

Es ruft keine Boerse und schreibt keine Order. Es aendert genau die Werte, die
der Mensch im Fenster ankreuzt, in der `wachen.json` der Spur - mit Sicherung,
`json.loads`-Gegenprobe und einer datierten Notiz. Was danach laeuft, laeuft
ueber die Sperrenkette der Spur (handel_erlaubt + freigabe.erfuellt +
Zeitfenster + Guthaben + Schluessel + Deckel).

Zwei Regeln sind im Code verankert, nicht in einem Kommentar:

  * **`herzschlag_max_minuten` steht auf 180, bevor `handel_erlaubt` auf true
    geht** (Hausregel seit 19.09.2026). Ist der Wert kleiner, setzt dieses
    Fenster ihn mit - die Checkbox ist dann vorbelegt und nicht abwaehlbar.
  * **Wer wirklich handeln kann, muss es tippen.** Kann die Spur nach dem
    Scharfschalten live ordern (Orderweg vorhanden UND `freigabe.erfuellt`
    true), verlangt das Fenster den Namen der Spur als Bestaetigung. Sonst
    genuegt ein Haken "Ich habe die Werte gelesen".

`plan_bauen` ist eine reine Funktion und ohne Fenster pruefbar
(`tests/test_schalter.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import tkinter as tk
from tkinter import ttk

import handelstand
import rund

TIPPEN = "tippen"
HAKEN = "haken"
NICHTS = "nichts"


@dataclass
class Plan:
    """Was ein Klick im Fenster aendern wuerde - und wie es bestaetigt wird."""

    aenderungen: dict = field(default_factory=dict)
    bestaetigung: str = HAKEN
    wirkung: str = ""
    titel: str = ""

    @property
    def etwas_zu_tun(self) -> bool:
        return bool(self.aenderungen)


def plan_bauen(
    spur: str,
    wachen: dict,
    stand: dict,
    *,
    herzschlag: bool,
    freigabe: bool | None,
    entschaerfen: bool = False,
) -> Plan:
    """Den Plan aus den angekreuzten Werten bauen.

    `freigabe=None` heisst: den Haken `freigabe.erfuellt` NICHT anfassen (er ist
    die Entscheidung des Menschen und wird nur auf ausdrueckliches Ankreuzen
    geaendert).
    """
    if entschaerfen:
        return Plan(
            aenderungen={"handel_erlaubt": False},
            bestaetigung=HAKEN,
            wirkung=handelstand.wirkung(stand, erlaubt=False),
            titel=f"Entschaerfen · {spur}",
        )

    hs = handelstand.zahl(wachen, "herzschlag_max_minuten")
    aenderungen: dict = {}
    # Fehlt der Wert ganz, wird er gesetzt: ohne ihn kann niemand pruefen, ob
    # die Spur einen PC-Ausfall ueberlebt - und eine Live-Spur ohne Herzschlag
    # waere genau der Fall, den die Hausregel verbietet.
    if herzschlag or hs is None or hs < handelstand.HERZSCHLAG_LIVE:
        aenderungen["herzschlag_max_minuten"] = handelstand.HERZSCHLAG_LIVE
    if not stand.get("erlaubt"):
        aenderungen["handel_erlaubt"] = True
    if freigabe is not None and bool(freigabe) != bool(stand.get("frei")):
        aenderungen["freigabe.erfuellt"] = bool(freigabe)

    # Kann die Spur danach live ordern? Nur dann muss der Name getippt werden.
    order_da = bool(stand.get("order"))
    frei_danach = bool(freigabe) if freigabe is not None else bool(stand.get("frei"))
    scharf_danach = bool(aenderungen.get("handel_erlaubt", stand.get("erlaubt")))
    bestaetigung = TIPPEN if (order_da and frei_danach and scharf_danach) else HAKEN
    if not aenderungen:
        bestaetigung = NICHTS

    return Plan(
        aenderungen=aenderungen,
        bestaetigung=bestaetigung,
        wirkung=handelstand.wirkung(stand, erlaubt=scharf_danach, freigabe=frei_danach),
        titel=f"Scharf schalten · {spur}",
    )


class _BasisFenster(tk.Toplevel):
    """Gemeinsamer Aufbau: Kopf, Text, Fuss mit zwei Knoepfen."""

    def __init__(self, master, *, titel: str, farben: dict, schrift_tupel,
                 radius: int, s: float, ausfuehren, jetzt):
        super().__init__(master)
        self.farben = farben
        self.ausfuehren = ausfuehren
        self.jetzt = jetzt
        self.radius = radius
        self.s = s
        self.schrift_tupel = schrift_tupel
        self.title(titel)
        self.configure(background=farben["bg"])
        self.transient(master)
        self.resizable(True, True)
        self.bind("<Escape>", lambda _e: self.destroy())

        self.kopf = ttk.Label(self, text=titel, foreground=farben["akzent"],
                              font=(schrift_tupel[0], schrift_tupel[1] + 1, "bold"))
        self.kopf.pack(anchor="w", padx=12, pady=(12, 4))

        self.text = tk.Text(
            self, height=9, width=72, wrap="word", relief="flat",
            background=farben["blatt"], foreground=farben["text"],
            font=(schrift_tupel[0], schrift_tupel[1] - 1), borderwidth=0,
            highlightthickness=0, insertbackground=farben["text"],
        )
        self.text.pack(fill="both", expand=True, padx=12)
        self.text.configure(state="disabled")

        self.fuss = tk.Frame(self, background=farben["bg"])
        self.fuss.pack(fill="x", padx=12, pady=12)

    def text_setzen(self, inhalt: str) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", inhalt)
        self.text.configure(state="disabled")

    def knopf(self, eltern, text, befehl, *, variante="normal") -> rund.RunderKnopf:
        return rund.RunderKnopf(
            eltern, text, befehl, variante=variante, farben=self.farben,
            schrift_tupel=self.schrift_tupel, radius=self.radius,
            padx=int(10 * self.s), pady=int(4 * self.s),
        )

    def abschluss(self, ergebnis) -> None:
        """Das Ergebnis eines Schreibversuchs anzeigen."""
        if ergebnis.ok:
            self.text_setzen(
                "Geschrieben.\n\n"
                + "\n".join(ergebnis.geaendert or ["(keine Aenderung)"])
                + (f"\n\nSicherung: {ergebnis.sicherung.name}" if ergebnis.sicherung else "")
            )
            self.kopf.configure(text="Erledigt", foreground=self.farben["gruen"])
        else:
            self.text_setzen(
                "NICHT geschrieben.\n\n" + (ergebnis.fehler or "unbekannter Grund")
                + "\n\nEs wurde nichts geaendert - die Wachen-Datei ist unberuehrt."
            )
            self.kopf.configure(text="Fehlgeschlagen", foreground=self.farben["rot"])


class ScharfFenster(_BasisFenster):
    """Checkliste, Wirkung, Bestaetigung - dann erst wird geschrieben."""

    def __init__(self, master, *, spur: str, wachen: dict, stand: dict, farben: dict,
                 schrift_tupel, radius: int, s: float, ausfuehren, jetzt):
        super().__init__(master, titel=f"Scharf schalten · {spur}", farben=farben,
                         schrift_tupel=schrift_tupel, radius=radius, s=s,
                         ausfuehren=ausfuehren, jetzt=jetzt)
        self.spur = spur
        self.wachen = wachen
        self.stand = stand

        hs = handelstand.zahl(wachen, "herzschlag_max_minuten")
        self.herzschlag = tk.BooleanVar(value=(hs is None or hs < handelstand.HERZSCHLAG_LIVE))
        self.freigabe = tk.BooleanVar(value=bool(stand.get("frei")))
        self.gelesen = tk.BooleanVar(value=False)
        self.tipptext = tk.StringVar(value="")

        self._bauen_checkliste()
        self._bauen_schalter(hs)
        self._bauen_bestaetigung()
        self._bauen_fuss()
        self._neu_rechnen()
        self.update_idletasks()
        self._mittig(master)

    # ------------------------------------------------------------ Aufbau
    def _bauen_checkliste(self) -> None:
        self.text_setzen(self._checkliste())
        self.text.configure(height=10)

    def _checkliste(self) -> str:
        punkte = handelstand.pruefpunkte(
            self.wachen, self.stand, buch=self.stand.get("buch"),
            alter=self.stand.get("alter"),
        )
        zeilen = [f"{_zeichen(p.stand)} {p.name}: {p.text}" for p in punkte]
        zeilen.append("")
        zeilen.append("Der Stand kommt aus der Wachen-Datei und spuren_stand.py - "
                      "rein lesend. Was die Spur selbst noch prueft (Guthaben, "
                      "Schluesselrechte), steht als '?' darin.")
        return "\n".join(zeilen)

    def _bauen_schalter(self, hs) -> None:
        rahmen = tk.Frame(self, background=self.farben["bg"])
        rahmen.pack(fill="x", padx=12, pady=(8, 0))
        haken = ttk.Checkbutton(
            rahmen, text=f"herzschlag_max_minuten auf {handelstand.HERZSCHLAG_LIVE} setzen",
            variable=self.herzschlag, command=self._neu_rechnen,
        )
        haken.pack(anchor="w")
        if hs is not None and hs < handelstand.HERZSCHLAG_LIVE:
            ttk.Label(rahmen, text=f"   Pflicht: der Wert steht auf {hs:g} - eine Live-Spur "
                                   f"braucht {handelstand.HERZSCHLAG_LIVE} (PC-Ausfall).",
                      foreground=self.farben["gelb"]).pack(anchor="w")
        ttk.Checkbutton(
            rahmen, text="freigabe.erfuellt setzen (der von Hand gesetzte Endhaken)",
            variable=self.freigabe, command=self._neu_rechnen,
        ).pack(anchor="w")
        ttk.Label(
            rahmen,
            text="   Ohne diesen Haken handelt die Spur auch mit handel_erlaubt=true nicht live.",
            foreground=self.farben["matt"],
        ).pack(anchor="w")

    def _bauen_bestaetigung(self) -> None:
        self.best_rahmen = tk.Frame(self, background=self.farben["bg"])
        self.best_rahmen.pack(fill="x", padx=12, pady=(8, 0))
        self.best_haken = ttk.Checkbutton(
            self.best_rahmen, text="Ich habe die Werte gelesen",
            variable=self.gelesen, command=self._neu_rechnen,
        )
        self.best_tipp = ttk.Entry(self.best_rahmen, textvariable=self.tipptext, width=30)
        self.tipptext.trace_add("write", lambda *_: self._neu_rechnen())
        self.best_hinweis = ttk.Label(self.best_rahmen, text="", foreground=self.farben["gelb"])

    def _bauen_fuss(self) -> None:
        self.wirkung = ttk.Label(self, text="", foreground=self.farben["text"],
                                 wraplength=int(700 * self.s), justify="left")
        self.wirkung.pack(fill="x", padx=12, pady=(8, 0))
        self.knopf_ab = self.knopf(self.fuss, "Abbrechen", self.destroy, variante="flach")
        self.knopf_ab.pack(side="left")
        self.knopf_an = self.knopf(self.fuss, "Scharf schalten", self._anwenden,
                                   variante="gefahr")
        self.knopf_an.pack(side="right")

    def _mittig(self, master) -> None:
        try:
            x = master.winfo_rootx() + max(0, (master.winfo_width() - self.winfo_width()) // 2)
            y = master.winfo_rooty() + 80
            self.geometry(f"+{x}+{y}")
        except Exception:                                    # noqa: BLE001
            pass

    # ------------------------------------------------------------ Rechnen
    def _plan(self) -> Plan:
        return plan_bauen(
            self.spur, self.wachen, self.stand,
            herzschlag=bool(self.herzschlag.get()),
            freigabe=bool(self.freigabe.get()),
        )

    def _neu_rechnen(self) -> None:
        plan = self._plan()
        self.wirkung.configure(
            text=("Was passiert: " + plan.wirkung) if plan.etwas_zu_tun
            else "Es ist nichts zu aendern - der Schalter steht schon so."
        )
        # Bestaetigungsfeld zeigen, je nach Plan
        for w in (self.best_haken, self.best_tipp, self.best_hinweis):
            w.pack_forget()
        if plan.bestaetigung == TIPPEN:
            self.best_hinweis.configure(
                text=f"Zum Bestaetigen den Spurnamen tippen: {self.spur}")
            self.best_hinweis.pack(anchor="w")
            self.best_tipp.pack(anchor="w")
        elif plan.bestaetigung == HAKEN:
            self.best_haken.pack(anchor="w")
        self.knopf_an.setze_aktiv(plan.etwas_zu_tun and self._bestaetigt(plan))

    def _bestaetigt(self, plan: Plan) -> bool:
        if plan.bestaetigung == TIPPEN:
            return self.tipptext.get().strip().lower() == self.spur.strip().lower()
        if plan.bestaetigung == HAKEN:
            return bool(self.gelesen.get())
        return False

    def _anwenden(self) -> None:
        plan = self._plan()
        if not (plan.etwas_zu_tun and self._bestaetigt(plan)):
            return
        vermerk = "scharf geschaltet" + (f" ({self.tipptext.get().strip()})"
                                         if plan.bestaetigung == TIPPEN else "")
        ergebnis = self.ausfuehren(self.spur, plan.aenderungen, vermerk)
        self.abschluss(ergebnis)
        self.knopf_an.setze_aktiv(False)


class EntschaerfenFenster(_BasisFenster):
    """Eine Rueckfrage vor dem Ausschalten - mit den Folgen in Worten."""

    def __init__(self, master, *, spur: str, farben: dict, schrift_tupel, radius: int,
                 s: float, ausfuehren, jetzt):
        super().__init__(master, titel=f"Entschaerfen · {spur}", farben=farben,
                         schrift_tupel=schrift_tupel, radius=radius, s=s,
                         ausfuehren=ausfuehren, jetzt=jetzt)
        self.spur = spur
        self.gelesen = tk.BooleanVar(value=False)
        self.text_setzen(
            f"{handelstand.wirkung({}, erlaubt=False)}\n\n"
            "Geaendert wird NUR handel_erlaubt (auf false). Der Haken "
            "freigabe.erfuellt bleibt stehen - er ist eine Entscheidung von Hand "
            "und wird nicht als Nebenwirkung zurueckgenommen.\n\n"
            "Offene Positionen bleiben offen; sie werden weiter ueber Stop, Ziel "
            "und Frist verwaltet."
        )
        ttk.Checkbutton(self.fuss, text="Ich habe die Werte gelesen",
                        variable=self.gelesen,
                        command=lambda: self.knopf_an.setze_aktiv(bool(self.gelesen.get()))
                        ).pack(side="left")
        self.knopf_ab = self.knopf(self.fuss, "Abbrechen", self.destroy, variante="flach")
        self.knopf_ab.pack(side="left", padx=12)
        self.knopf_an = self.knopf(self.fuss, "Entschaerfen", self._anwenden, variante="gefahr")
        self.knopf_an.pack(side="right")
        self.knopf_an.setze_aktiv(False)
        self.update_idletasks()
        try:
            x = master.winfo_rootx() + max(0, (master.winfo_width() - self.winfo_width()) // 2)
            self.geometry(f"+{x}+{master.winfo_rooty() + 80}")
        except Exception:                                    # noqa: BLE001
            pass

    def _anwenden(self) -> None:
        if not self.gelesen.get():
            return
        ergebnis = self.ausfuehren(self.spur, {"handel_erlaubt": False}, "entschaerft")
        self.abschluss(ergebnis)
        self.knopf_an.setze_aktiv(False)


def _zeichen(stand: str) -> str:
    return {"ok": "ok  ", "fehlt": "FEHLT", "warnung": "WARN ", "unbekannt": "?   "}.get(
        stand, "?   ")