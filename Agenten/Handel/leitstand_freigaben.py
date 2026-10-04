"""Freigaben-Reiter des Leitstands.

Schreibt NUR ueber freigabefenster.* - dieselben Funktionen, die Telegram
benutzt; die Wirkung ist dieselbe wie /ja und /nein. Freigeben geht nur,
wenn der Dauerlauf eine Anfrage gestellt hat. Freigeben und Notaus haben kein
Tastenkuerzel; der Dialog schliesst sich nach 120 s ohne Bedienung und
schreibt dann nichts.
"""

import json
import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import dauerlauf
import freigabefenster as ff
import leitstand_stil as stil
from leitstand_bedienung import Tabelle, Tooltip, ZeitDialog, blinken, setze_knopf

HIER = Path(__file__).resolve().parent
SPALTEN = ("Spur", "Stand", "Anfrage verfällt in", "Freigegeben von",
           "Freigegeben am", "Geschlossen am", "Grund", "Auto")
SPERRE_BELEGT = "Sperre belegt — bitte erneut"


def _kurz(iso):
    t = ff._zeit(iso)
    return t.strftime("%d.%m. %H:%M") if t else ""


def _gueltig(fenster):
    return {s: f for s, f in fenster.items() if isinstance(f.d, dict)}


def zeilen(fenster, jetzt=None):
    """Eine Zeile je Spur; Spuren aus dauerlauf.SPUREN ohne Eintrag als Papier."""
    jetzt = jetzt or ff._jetzt()
    fenster = _gueltig(fenster)
    for spur in dauerlauf.SPUREN:
        fenster.setdefault(spur, ff.Fenster(spur, {}))
    aus = []
    for spur in sorted(fenster):
        f = fenster[spur]
        d = f.d
        verfaellt = ""
        if f.anfrage_offen():
            rest = ff._zeit(d.get("anfrage_bis")) - jetzt
            verfaellt = "%d min" % max(0, int(rest.total_seconds() // 60))
        aus.append((spur, f.text(), verfaellt, d.get("freigegeben_von") or "",
                    _kurz(d.get("freigegeben_am")),
                    _kurz(d.get("zuletzt_geschlossen")),
                    d.get("schliess_grund") or "",
                    "ja" if spur in dauerlauf.AUTO_FREIGABE else ""))
    return aus


def knopf_zustand(f):
    if f is None:
        kein = (False, "keine Spur gewählt")
        return {"freigeben": kein, "ablehnen": kein, "schliessen": kein}
    anfrage = f.anfrage_offen()
    grund_a = "" if anfrage else "keine wartende Anfrage"
    scharf = f.offen()
    return {"freigeben": (anfrage, grund_a), "ablehnen": (anfrage, grund_a),
            "schliessen": (scharf, "" if scharf else "Spur ist nicht scharf")}


def _fehler(was, e):
    return "%s NICHT ausgeführt: %s: %s — bitte freigabefenster.py prüfen" % (
        was, type(e).__name__, e)


def freigeben(spur, stunden):
    try:
        minuten = ff.oeffnen(spur, stunden, wer="leitstand")
    except TimeoutError:
        return SPERRE_BELEGT
    except Exception as e:
        return _fehler("Freigabe", e)
    if minuten is None:
        return "Anfrage war verfallen — nichts geändert"
    return "%s scharf für %d:%02d h" % (spur, minuten // 60, minuten % 60)


def ablehnen(spur):
    try:
        wartet = ff.lade(spur).anfrage_offen()
    except Exception as e:
        return _fehler("Ablehnen", e)
    if not wartet:
        return "%s: keine wartende Anfrage — nichts geändert" % spur
    try:
        ff.schliessen(spur, "abgelehnt (Leitstand)")
    except TimeoutError:
        return SPERRE_BELEGT
    except Exception as e:
        return _fehler("Ablehnen", e)
    return "%s abgelehnt — Wiedervorlage in %d h" % (
        spur, ff.WIEDERVORLAGE_NACH_ABLEHNUNG_STUNDEN)


def schliessen(spur):
    try:
        war = ff.schliessen(spur, "von Hand (Leitstand)")
    except TimeoutError:
        return SPERRE_BELEGT
    except Exception as e:
        return _fehler("Schließen", e)
    return ("%s zurück auf Papier" % spur if war
            else "%s war nicht scharf — Grund vermerkt" % spur)


def notaus():
    try:
        spuren = ff.alles_schliessen("Notaus (Leitstand)")
    except TimeoutError:
        return SPERRE_BELEGT
    except Exception as e:
        return _fehler("Notaus", e)
    if spuren:
        return "Notaus: %s zurück auf Papier" % ", ".join(sorted(spuren))
    return "Notaus: keine Spur war scharf — Anfragen verworfen"


def freigeben_mehrfach(spuren, stunden):
    """Mehrere Spuren nacheinander freigeben - eine Meldung je Ergebnis.

    Bewusst NICHT in einer Sperre fuer alle: `freigabefenster.oeffnen()`
    nimmt die Sperre je Spur. Ein Buendel nacher wuerde beim ersten Erfolg
    alle anderen verpassen, und der Dauerlauf koennte in der Luecke dazwischen
    eine Anfrage stellen. Jede Spur einzeln behandeln heisst: jede bekommt
    ihren eigenen Eintrag, jede kann scheitern, und der Bericht sagt es.
    """
    if not spuren:
        return []
    ergebnis = []
    for spur in spuren:
        ergebnis.append((spur, freigeben(spur, stunden)))
    return ergebnis


def mehrfach_meldung(ergebnis):
    """Aus [(spur, text)] eine Meldung: erst die Zahl, dann die Misserfolge.

    Wer drei Spuren freigibt und eine scheitert, will beides sehen: die Zahl
    der Erfolge UND den Grund der einen, die nicht ging.
    """
    if not ergebnis:
        return ""
    ok = [s for s, t in ergebnis if "scharf für" in t]
    schlecht = [(s, t) for s, t in ergebnis if "scharf für" not in t]
    teile = []
    if ok:
        teile.append("%d freigegeben" % len(ok))
    for s, t in schlecht:
        teile.append("%s: %s" % (s, t))
    return " | ".join(teile)


def _stunden_aus(text):
    """'xperp scharf für 1:30 h' -> 90 Minuten."""
    treffer = re.search(r"(\d+):(\d\d) h", text or "")
    return (int(treffer.group(1)) * 60 + int(treffer.group(2))) if treffer else 0


def vorbelegte_stunden(f):
    minuten = f.d.get("anfrage_dauer_minuten") or 60
    return max(1, min(24, round(minuten / 60)))


def grenz_zeilen(spur):
    info = dauerlauf.SPUREN.get(spur, {})
    pfad = HIER / info.get("ordner", spur) / "wachen.json"
    try:
        w = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [("wachen.json", "nicht lesbar")]
    if not isinstance(w, dict):
        return [("wachen.json", "nicht lesbar")]
    paare = [(n, v.strip()) for n, v in ff.grenzwerte(w, info.get("waehrung", "USD"))]
    return paare or [("Grenzen", "keine in wachen.json")]


def neue_anfragen(gesehen, fenster):
    """(neu, aktuell): eine Anfrage ist neu, bis sie einmal gesehen wurde."""
    aktuell = {(s, f.d.get("anfrage_gestellt"))
               for s, f in _gueltig(fenster).items() if f.anfrage_offen()}
    return aktuell - set(gesehen), aktuell


class FreigabeDialog(ZeitDialog):
    """Ergebnis: ("ja", stunden) | "nein" | "abgebrochen" | "zeitablauf"."""

    def __init__(self, eltern, spur, grenzen, stunden, spuren=None, **kw):
        # spuren=None -> Einzel spur (alte Form). Sonst Mehrfachauswahl mit
        # einer gemeinsamen Dauer: 05.10.2026 Auftrag Max "im Freigabemenue
        # die Funktion Spuren auch freizugeben" (mehrere auf einmal).
        self.spuren = tuple(spuren) if spuren else (spur,)
        titel = ("Freigabe %d Spuren" % len(self.spuren) if len(self.spuren) > 1
                 else "Freigabe %s" % spur)
        super().__init__(eltern, titel, **kw)
        i = self.inhalt
        ttk.Label(i, text=("Freigabe %d Spuren?" % len(self.spuren)
                           if len(self.spuren) > 1 else "Freigabe %s?" % spur),
                  style="Titel.TLabel").grid(row=0, column=0,
                                             columnspan=2, sticky="w")
        if len(self.spuren) > 1:
            ttk.Label(i, text=", ".join(self.spuren[:6])
                      + (" …" if len(self.spuren) > 6 else ""),
                      foreground=stil.FARBEN["hinweis"]).grid(
                          row=1, column=0, columnspan=2, sticky="w")
        r_start = 2
        ttk.Label(i, text="Es gelten die Grenzen aus wachen.json:").grid(
            row=r_start, column=0, columnspan=2, sticky="w", pady=(6, 2))
        for n, (name, wert) in enumerate(grenzen, start=r_start + 1):
            ttk.Label(i, text=name).grid(row=n, column=0, sticky="w",
                                         padx=(10, 20))
            ttk.Label(i, text=wert).grid(row=n, column=1, sticky="w")
        r = r_start + len(grenzen) + 1
        ttk.Label(i, text="Dauer (Stunden):").grid(row=r, column=0, sticky="w",
                                                   pady=(8, 0))
        self.w_stunden = tk.IntVar(value=stunden)
        ttk.Spinbox(i, from_=1, to=24, textvariable=self.w_stunden, width=5,
                    state="readonly").grid(row=r, column=1, sticky="w", pady=(8, 0))
        knoepfe = ttk.Frame(i)
        knoepfe.grid(row=r + 1, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(knoepfe, text="Ja, freigeben", command=self.ja).pack(side="left",
                                                                       padx=4)
        ttk.Button(knoepfe, text="Nein, ablehnen",
                   command=lambda: self.fertig("nein")).pack(side="left", padx=4)
        ttk.Button(knoepfe, text="Abbrechen",
                   command=lambda: self.fertig("abgebrochen")).pack(side="left",
                                                                    padx=4)

    def ja(self):
        self.fertig(("ja", max(1, min(24, int(self.w_stunden.get())))))


class FreigabenReiter(ttk.Frame):
    def __init__(self, eltern, leitstand, dialog=FreigabeDialog,
                 frage=messagebox.askyesno):
        super().__init__(eltern, padding=stil.ABSTAND_GROSS)
        self.ls, self.dialog, self.frage = leitstand, dialog, frage
        self._fenster, self._gesehen = {}, set()
        self.tabelle = Tabelle(self, SPALTEN, leitstand.zustand, "freigaben",
                               hoehe=14, auswahl="extended")
        self.tabelle.pack(fill="both", expand=True)
        self.tabelle.baum.bind("<<TreeviewSelect>>", lambda _e: self._knoepfe())
        leiste = ttk.Frame(self)
        leiste.pack(fill="x", pady=(6, 0))
        self.k = {
            "freigeben": ttk.Button(leiste, text="Freigeben …",
                                    command=self.freigeben_klick),
            "ablehnen": ttk.Button(leiste, text="Ablehnen",
                                   command=self.ablehnen_klick),
            "schliessen": ttk.Button(leiste, text="Schließen",
                                     command=self.schliessen_klick),
        }
        self.tips = {}
        for name, knopf in self.k.items():
            knopf.pack(side="left", padx=4)
            self.tips[name] = Tooltip(knopf)
        self.k_notaus = tk.Button(leiste, text="NOTAUS", command=self.notaus_klick,
                                  bg=stil.FARBEN["notaus"], fg="white",
                                  activebackground=stil.FARBEN["notaus_aktiv"],
                                  activeforeground="white", font=stil.FETT,
                                  padx=12, pady=2)
        self.k_notaus.pack(side="right", padx=4)
        self.refresh()

    # Reiter-Schnittstelle
    def refresh(self):
        try:
            self._fenster = _gueltig(ff.alle())
        except (AttributeError, TypeError):          # Datei ist kein Objekt
            self._fenster = {}
        z = zeilen(self._fenster)
        self.tabelle.setze(z, [("wartet",) if r[2] else () for r in z])
        neu, self._gesehen = neue_anfragen(self._gesehen, self._fenster)
        if neu:
            blinken(self.ls.root)
        self._knoepfe()

    def titel_zusatz(self):
        return " (%d)" % len(self._gesehen) if self._gesehen else ""

    def status(self):
        return ""

    # Bedienung
    def gewaehlt(self):
        a = self.tabelle.auswahl()
        return a[0][0] if a else None

    def gewaehlt_viele(self):
        """Alle angeklickten Spuren. Mit Strg/Klick im Baum Mehrfachauswahl."""
        return [z[0] for z in self.tabelle.auswahl()]

    def _wartende(self, spuren):
        """Nur Spuren mit wartender Anfrage - ohne Anfrage gibt es nichts zu
        bestaetigen. So ein Dialog, der eine Spur ohne Anfrage nennt, waere
        eine Frage, die keiner beantworten kann."""
        wartend = []
        for spur in spuren:
            try:
                f = ff.lade(spur)
                if f.anfrage_offen():
                    wartend.append(spur)
            except Exception:
                continue
        return wartend

    def _knoepfe(self):
        spur = self.gewaehlt()
        f = (self._fenster.get(spur) or ff.Fenster(spur, {})) if spur else None
        for name, (erlaubt, grund) in knopf_zustand(f).items():
            setze_knopf(self.k[name], self.tips[name], erlaubt, grund)

    def freigeben_klick(self):
        # Mehrfachauswahl: mit Strg oder Shift im Baum anklicken (05.10.2026,
        # Auftrag Max: "im Freigabemenue die Funktion Spuren auch freizugeben").
        viele = self.gewaehlt_viele()
        spur = viele[0] if viele else None
        try:
            f = ff.lade(spur) if spur else None
            wartet = bool(f and f.anfrage_offen())
        except Exception as e:
            self.ls.melde(_fehler("Freigabe", e))
            return
        if len(viele) > 1:
            self._freigeben_viele(viele)
            return
        if not wartet:
            self.ls.melde("%s: keine wartende Anfrage — nichts geändert" % spur)
            self.refresh()
            return
        erg = self.dialog(self.ls.root, spur, grenz_zeilen(spur),
                          vorbelegte_stunden(f)).zeige_modal()
        if isinstance(erg, tuple) and erg[0] == "ja":
            self.ls.melde(freigeben(spur, erg[1]))
        elif erg == "nein":
            self.ls.melde(ablehnen(spur))
        elif erg == "zeitablauf":
            self.ls.melde("Freigabe-Dialog ohne Bedienung geschlossen — nichts geändert")
        else:
            self.ls.melde("Freigabe abgebrochen — nichts geändert")
        self.refresh()

    def _freigeben_viele(self, viele):
        """Mehrere Spuren in einem Dialog - eine Dauer fuer alle."""
        wartend = self._wartende(viele)
        if not wartend:
            self.ls.melde("Keine der gewählten Spuren hat eine wartende "
                          "Anfrage — nichts geändert")
            self.refresh()
            return
        # Die Dauer ist die kuerzeste der Anfragen: eine Spur mit 30 Minuten
        # Anfrage wuerde sonst eine Stunde bekommen, die niemand bestellt hat.
        try:
            stunden = min(vorbelegte_stunden(ff.lade(s)) for s in wartend)
        except Exception:
            stunden = 1
        grenzen = []
        for name, wert in grenz_zeilen(wartend[0]):
            grenzen.append((name if len(wartend) == 1
                            else "%s" % name, wert))
        erg = self.dialog(self.ls.root, wartend[0], grenzen, stunden,
                          spuren=wartend).zeige_modal()
        if isinstance(erg, tuple) and erg[0] == "ja":
            self.ls.melde(mehrfach_meldung(freigeben_mehrfach(wartend, erg[1])))
        elif erg == "zeitablauf":
            self.ls.melde("Freigabe-Dialog ohne Bedienung geschlossen — "
                          "nichts geändert")
        else:
            self.ls.melde("Freigabe abgebrochen — nichts geändert")
        self.refresh()

    def ablehnen_klick(self):
        spur = self.gewaehlt()
        if spur and self.frage("Ablehnen", "Anfrage von %s ablehnen?" % spur,
                               parent=self):
            self.ls.melde(ablehnen(spur))
            self.refresh()

    def schliessen_klick(self):
        spur = self.gewaehlt()
        if spur and self.frage("Schließen", "%s sofort zurück auf Papier?" % spur,
                               parent=self):
            self.ls.melde(schliessen(spur))
            self.refresh()

    def notaus_klick(self):
        if self.frage("NOTAUS", "Alle Spuren sofort zurück auf Papier?\n"
                      "Wartende Anfragen werden verworfen.", icon="warning",
                      default="no", parent=self):
            self.ls.melde(notaus())
            self.refresh()
