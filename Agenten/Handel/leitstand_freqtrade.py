"""FreqTrade-Reiter des Leitstands: alle Bots aus freqtrade/bots.json auf einen Blick.

Auftrag Max 10.10.2026 (Spec Werkstatt/spec-freqtrade-hausspuren-2026-10-10.md):
die Haus-Spur-Bots sollen im Leitstand sichtbar sein - mit ihrem Backtest-Urteil
daneben, damit Breite nicht mit Kante verwechselt wird.

Nur lesend: alles geht ueber freqtrade_bridge (nur GET). Die Abfrage laeuft in
einem Hintergrund-Thread; 20 Bots x 4 s Zeitgrenze duerfen den Rahmen nicht
einfrieren. Tk wird nur im Hauptthread angefasst (after-Schleife).
"""

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import freqtrade_bridge as fb
import handelszentrale as hz
import leitstand_stil as stil

URTEILE = Path(__file__).resolve().parent / "freqtrade" / "urteile.json"
SPALTEN = (("bot", "Bot", 170), ("spur", "Spur", 150), ("zustand", "Zustand", 190),
           ("offen", "offen", 50), ("runden", "Runden", 60),
           ("gv", "G/V geschl.", 90), ("bt", "Backtest 2 J.", 170))
OFFEN_SPALTEN = ("Paar", "Seite", "seit", "Einstieg", "aktuell", "Einsatz", "G/V %")
ZU_SPALTEN = ("Paar", "auf", "zu", "G/V %", "G/V", "Grund")
ABHOLEN_MS = 150
DETAIL_ZEITGRENZE = 4        # wie die Uebersicht; Bruecken-Vorgabe 10 s ist fuer Tk zu lang


def lade_urteile(pfad: Path = URTEILE) -> dict:
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def _backtest_text(u):
    if not u:
        return "—"
    if not isinstance(u, dict):               # urteile.json ist Fremdtext (Review M10d)
        return "?"
    stand = str(u.get("stand", ""))
    datum = "%s.%s." % (stand[8:10], stand[5:7]) if len(stand) >= 10 else "?"
    try:
        return "%+.2f %% / %d R (%s)" % (float(u.get("netto_prozent", 0.0)),
                                         int(u.get("runden", 0)), datum)
    except (TypeError, ValueError):
        return "?"


def detail_abfrage(bot):
    """Offene und geschlossene Trades eines Bots, mit kurzer Zeitgrenze (Review M10c)."""
    zugang = fb.zugang_fuer(bot["port"])
    return (fb.hole("status", zugang, zeitgrenze=DETAIL_ZEITGRENZE),
            fb.hole("trades", zugang, zeitgrenze=DETAIL_ZEITGRENZE, limit=50))


def zeilen(uebersicht, bot_liste, urteile):
    """Eine Tabellenzeile je Bot: (Bot, Spur, Zustand, offen, Runden, G/V, Backtest)."""
    spur_je_bot = {b["name"]: (b.get("hausspur") or "MoonDev") for b in bot_liste}
    aus = []
    for z in uebersicht:
        if z.get("erreichbar"):
            zustand = "läuft" if z.get("zustand") == "running" else str(z.get("zustand"))
            if z.get("dry_run") is False:
                zustand = "LIVE! " + zustand       # nie der Normalfall
        else:
            zustand = "taub: %s" % (z.get("fehler") or "?")
        gv = z.get("gewinn")
        aus.append((z["name"], spur_je_bot.get(z["name"], "?"), zustand,
                    "" if z.get("offen") is None else str(z["offen"]),
                    "" if z.get("trades") is None else str(z["trades"]),
                    "" if gv is None else "%+.2f" % float(gv),
                    _backtest_text(urteile.get(z["name"]))))
    return aus


def titel(uebersicht):
    if not uebersicht:
        return ""
    return " (%d/%d)" % (sum(1 for z in uebersicht if z.get("erreichbar")), len(uebersicht))


def status_text(uebersicht):
    taub = [z["name"] for z in uebersicht if not z.get("erreichbar")]
    if not taub:
        return ""
    return "FreqTrade: %d taub (%s)" % (len(taub), ", ".join(taub))


class FreqtradeReiter(ttk.Frame):
    def __init__(self, eltern, leitstand, quelle=None, bot_quelle=None, urteile_pfad=None,
                 detail_quelle=None):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.ls = leitstand
        self.quelle = quelle or fb.uebersicht
        self.bot_quelle = bot_quelle or fb.bots
        self.urteile_pfad = urteile_pfad or URTEILE
        self.detail_quelle = detail_quelle or detail_abfrage
        self._uebersicht = []
        self._bots = []
        self._ergebnisse = []          # (fertig, wert, fehler) aus den Threads
        self._detail_laeuft = False
        self._detail_nachholen = False  # Auswahl kam waehrend einer Abfrage (Review M10a)
        self._laeuft = False

        self.kopf = ttk.Label(self, text="FreqTrade: wird abgefragt …", anchor="w")
        self.kopf.pack(fill="x")
        self.tabelle = ttk.Treeview(self, columns=[s[0] for s in SPALTEN],
                                    show="headings", height=12, selectmode="browse")
        for schluessel, text, breite in SPALTEN:
            self.tabelle.heading(schluessel, text=text)
            self.tabelle.column(schluessel, width=breite, anchor="w")
        self.tabelle.pack(fill="both", expand=True, pady=(6, 6))
        self.tabelle.bind("<<TreeviewSelect>>", self._gewaehlt)
        self.offen = self._liste(OFFEN_SPALTEN, 5)
        self.zu = self._liste(ZU_SPALTEN, 8)

    def _liste(self, spalten, hoehe):
        t = ttk.Treeview(self, columns=list(range(len(spalten))), show="headings",
                         height=hoehe)
        for i, text in enumerate(spalten):
            t.heading(i, text=text)
            t.column(i, width=95, anchor="w")
        t.pack(fill="both", expand=True, pady=(0, 6))
        return t

    # --- Hintergrund ----------------------------------------------------
    def _im_hintergrund(self, arbeit, fertig):
        def lauf():
            try:
                self._ergebnisse.append((fertig, arbeit(), None))
            except Exception as e:                             # noqa: BLE001
                self._ergebnisse.append((fertig, None, e))
        threading.Thread(target=lauf, daemon=True).start()
        self.after(ABHOLEN_MS, self._abholen)

    def _abholen(self):
        # Review M10e: nach destroy() trifft ein spaetes Ergebnis kein Widget mehr.
        try:
            if not self.winfo_exists():
                return
            if not self._ergebnisse:
                self.after(ABHOLEN_MS, self._abholen)
                return
            fertig, wert, fehler = self._ergebnisse.pop(0)
            fertig(wert, fehler)
        except tk.TclError:
            return

    # --- Reiter-Schnittstelle --------------------------------------------
    def refresh(self):
        if self._laeuft:
            return
        self._laeuft = True

        def arbeit():
            bots = self.bot_quelle()
            return bots, self.quelle(zeitgrenze=4, bot_liste=bots)
        self._im_hintergrund(arbeit, self._uebersicht_da)

    def _uebersicht_da(self, wert, fehler):
        self._laeuft = False
        if fehler is not None:
            self.kopf.configure(text="⚠ FreqTrade-Abfrage gescheitert: %s" % fehler)
            return
        self._bots, self._uebersicht = wert
        gewaehlt = self.tabelle.selection()
        self.tabelle.delete(*self.tabelle.get_children())
        for z in zeilen(self._uebersicht, self._bots, lade_urteile(self.urteile_pfad)):
            self.tabelle.insert("", "end", iid=z[0], values=z)
        if gewaehlt and self.tabelle.exists(gewaehlt[0]):
            self.tabelle.selection_set(gewaehlt[0])
        self.kopf.configure(text="FreqTrade: %d Bots%s  %s" % (
            len(self._uebersicht), titel(self._uebersicht), status_text(self._uebersicht)))

    def _gewaehlt(self, _ereignis=None):
        sel = self.tabelle.selection()
        bot = next((b for b in self._bots if sel and b["name"] == sel[0]), None)
        if bot is None:
            return
        if self._detail_laeuft:
            self._detail_nachholen = True
            return
        self._detail_laeuft = True
        self._im_hintergrund(lambda: self.detail_quelle(bot), self._detail_da)

    def _detail_da(self, wert, fehler):
        self._detail_laeuft = False
        if self._detail_nachholen:            # Ergebnis gehoert zur alten Auswahl
            self._detail_nachholen = False
            self._gewaehlt()
            return
        self.offen.delete(*self.offen.get_children())
        self.zu.delete(*self.zu.get_children())
        if fehler is not None or wert is None:
            self.offen.insert("", "end", values=(
                "⚠ Abfrage gescheitert", str(fehler or "keine Antwort")))
            return
        offen, zu = wert
        for t in (offen if isinstance(offen, list) else []):
            self.offen.insert("", "end", values=hz.freqtrade_offen_zeile(t))
        for z in hz.freqtrade_zu_zeilen(zu, 20):
            self.zu.insert("", "end", values=z)

    def titel_zusatz(self):
        return titel(self._uebersicht)

    def status(self):
        return status_text(self._uebersicht)
