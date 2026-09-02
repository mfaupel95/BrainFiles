"""Bestaetigungsfenster zum Scharfschalten eines Handelsauftrags.

Verlangt von Wissen/Schutzregeln.md, Abschnitt "Handel: was ein Agent selbst
ausloesen darf", Punkt 3: scharf geschaltet wird von Hand, in einem Fenster,
das die Werte anzeigt, sie anpassbar macht und Felder zum Bestaetigen oder
Ablehnen hat. Was danach laeuft, laeuft ohne Rueckfrage.

Die Grenze, auf der das Ganze steht:

    Dieses Fenster fuehrt nichts aus. Es gibt frei.

Es setzt keine Order, ruft weder OKX noch Kraken. Es nimmt Auftraege entgegen,
laesst sie im Rahmen der Wachen veraendern und gibt die bestaetigten zurueck.
Ausgefuehrt werden sie vom aufrufenden Automaten (handeln.py, bot.py), der
wachen.json liest. Damit bleibt die Ausfuehrung dort, wo die Grenzen sind.

Zwei weitere Regeln, die im Code verankert sind und nicht in einem Kommentar:

  * wachen.json wird nur gelesen, nie geschrieben. Kein Schieberegler kann
    ueber eine Grenze hinaus - die Obergrenze jedes Reglers IST der
    Wachen-Wert. Passt ein Auftrag nicht, ist der Auftrag falsch.
  * Der Hebeldeckel laesst sich senken, nie heben. Der Hebel selbst ist
    Ergebnis der Stopweite, keine Eingabe (Wissen/XPERP-Handel.md).

Aufruf als Bibliothek:

    import freigabe
    bestaetigt = freigabe.bestaetige(vorschlaege, spur="spot")
    if not bestaetigt:
        print("abgelehnt")

Aufruf von der Kommandozeile:

    python freigabe.py --spur spot  --auftrag auftrag.json [--aus frei.json]
    python freigabe.py --spur hebel --auftrag -            # JSON von stdin
    python freigabe.py --spur hebel --beispiel             # Fenster ansehen

Exit-Code 0 = mindestens ein Auftrag bestaetigt, 1 = alles abgelehnt.
"""

import argparse
import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

HIER = Path(__file__).resolve().parent
WACHEN = {"spot": HIER / "scanner" / "wachen.json",
          "hebel": HIER / "xperp" / "wachen.json"}


# --- Wachen ----------------------------------------------------------------

def lade_wachen(spur):
    """Die Grenzen. Einzige Wahrheit, nur gelesen."""
    p = WACHEN.get(spur)
    if p is None:
        raise ValueError("Unbekannte Spur %r, erlaubt: spot, hebel" % spur)
    if not p.exists():
        raise FileNotFoundError("Wachen fehlen: %s" % p)
    return json.loads(p.read_text("utf-8"))


def _z(w, name, ersatz=None):
    """Zahl aus den Wachen, mit Ersatz falls der Schluessel fehlt."""
    v = w.get(name, ersatz)
    return ersatz if v is None else v


# --- Rechnung --------------------------------------------------------------
# Beide Spuren liefern dasselbe Ergebnis-Schema, damit das Fenster nur eine
# Tabelle kennen muss.

def rechne_spot(a, w):
    """Spot, nur Long, kein Hebel. Der Einsatz ist der Kapitaleinsatz."""
    einstieg = float(a["einstieg"])
    stop_pct = float(a["stop_pct"])
    cr = float(a.get("cr", 2.0))
    usd = float(a["usd"])

    stop = einstieg * (1 - stop_pct / 100.0)
    ziel = einstieg + cr * (einstieg - stop)
    risiko = usd * stop_pct / 100.0
    return {"einstieg": einstieg, "stop": stop, "ziel": ziel,
            "stop_pct": stop_pct, "cr": cr,
            "positionswert": usd, "gebunden": usd, "hebel": 1.0,
            "risiko_usd": risiko}


def rechne_hebel(a, w):
    """Hebel. Der Hebel faellt aus dem Stop heraus und wird nur gedeckelt:

        Stop-Abstand  = atr_faktor x ATR
        Positionswert = Risikobetrag / Stop-Abstand
        Margin        = Positionswert / Hebel

    Ein fester Prozent-Stop ist verboten - bei 2,9 % ATR liegt -2 % innerhalb
    des normalen Zappelns (Wissen/XPERP-Handel.md).
    """
    einstieg = float(a["einstieg"])
    atr_pct = float(a["atr_pct"])
    atr_faktor = float(a.get("stop_atr_faktor", _z(w, "stop_atr_faktor", 1.5)))
    ziel_faktor = float(a.get("ziel_atr_faktor", _z(w, "ziel_atr_faktor", 3.0)))
    risiko = float(a["risiko_usd"])
    deckel = float(a.get("hebel", _z(w, "max_hebel", 5)))
    kurz = str(a.get("richtung", "long")).lower().startswith("s")

    stop_pct = atr_faktor * atr_pct
    ziel_pct = ziel_faktor * atr_pct
    if kurz:
        stop = einstieg * (1 + stop_pct / 100.0)
        ziel = einstieg * (1 - ziel_pct / 100.0)
    else:
        stop = einstieg * (1 - stop_pct / 100.0)
        ziel = einstieg * (1 + ziel_pct / 100.0)

    positionswert = risiko / (stop_pct / 100.0) if stop_pct > 0 else 0.0
    margin = positionswert / deckel if deckel > 0 else 0.0
    return {"einstieg": einstieg, "stop": stop, "ziel": ziel,
            "stop_pct": stop_pct,
            "cr": ziel_faktor / atr_faktor if atr_faktor else 0.0,
            "positionswert": positionswert, "gebunden": margin,
            "hebel": deckel, "risiko_usd": risiko, "atr_pct": atr_pct,
            "richtung": "short" if kurz else "long"}


RECHNER = {"spot": rechne_spot, "hebel": rechne_hebel}


# --- Pruefung gegen die Wachen ---------------------------------------------

def pruefe(r, w, spur, bestand):
    """Jede Grenze einzeln, mit Namen, Ist und Soll.

    Liste von (Bezeichnung, Ist, Soll, haelt?)."""
    p = []
    gebunden_vorher = float(bestand.get("gebunden_usd", 0.0))
    offen_vorher = int(bestand.get("offene_positionen", 0))

    if spur == "spot":
        je = _z(w, "max_pro_trade_usd", 50)
        ges = _z(w, "max_gesamt_usd", 200)
        maxoffen = _z(w, "max_offene_positionen", 4)
        smin = _z(w, "pflicht_stop_prozent_min", 4.0)
        smax = _z(w, "pflicht_stop_prozent_max", 12.0)
        mcr = _z(w, "mindest_chance_risiko", 1.5)
        p.append(("Einsatz je Trade", "%.2f USD" % r["gebunden"],
                  "hoechstens %.2f" % je, r["gebunden"] <= je + 1e-9))
        p.append(("Gebunden gesamt", "%.2f USD" % (gebunden_vorher + r["gebunden"]),
                  "hoechstens %.2f" % ges,
                  gebunden_vorher + r["gebunden"] <= ges + 1e-9))
        p.append(("Offene Positionen", "%d" % (offen_vorher + 1),
                  "hoechstens %d" % maxoffen, offen_vorher + 1 <= maxoffen))
        p.append(("Stopweite", "%.2f %%" % r["stop_pct"],
                  "%.1f bis %.1f %%" % (smin, smax),
                  smin - 1e-9 <= r["stop_pct"] <= smax + 1e-9))
        p.append(("Chance zu Risiko", "%.2f zu 1" % r["cr"],
                  "mindestens %.2f" % mcr, r["cr"] >= mcr - 1e-9))
    else:
        je = _z(w, "max_margin_je_anlauf_usd", 50)
        ges = _z(w, "max_margin_gesamt_usd", 200)
        maxoffen = _z(w, "max_offene_anlaeufe", 4)
        maxhebel = _z(w, "max_hebel", 5)
        maxrisiko = _z(w, "risiko_je_anlauf_usd", 7.5)
        minatr = _z(w, "stop_atr_faktor", 1.5)
        p.append(("Margin je Anlauf", "%.2f USD" % r["gebunden"],
                  "hoechstens %.2f" % je, r["gebunden"] <= je + 1e-9))
        p.append(("Margin gesamt", "%.2f USD" % (gebunden_vorher + r["gebunden"]),
                  "hoechstens %.2f" % ges,
                  gebunden_vorher + r["gebunden"] <= ges + 1e-9))
        p.append(("Offene Anlaeufe", "%d" % (offen_vorher + 1),
                  "hoechstens %d" % maxoffen, offen_vorher + 1 <= maxoffen))
        p.append(("Hebel", "%.1fx" % r["hebel"],
                  "hoechstens %.1fx" % maxhebel, r["hebel"] <= maxhebel + 1e-9))
        p.append(("Risiko je Anlauf", "%.2f USD" % r["risiko_usd"],
                  "hoechstens %.2f" % maxrisiko,
                  r["risiko_usd"] <= maxrisiko + 1e-9))
        gewaehlt = r["stop_pct"] / r["atr_pct"] if r.get("atr_pct") else 0.0
        p.append(("Stop in ATR", "%.2f ATR" % gewaehlt,
                  "mindestens %.2f" % minatr, gewaehlt >= minatr - 1e-9))

    # Kill-Switch und Freigabe sind keine Felder, sondern Zustand. Sie stehen
    # in derselben Tabelle, damit niemand bestaetigt, ohne sie gesehen zu haben.
    ks = _z(w, "kill_switch_gesamt_usd", None)
    if ks is not None:
        verlust = float(bestand.get("verlust_gesamt_usd", 0.0))
        p.append(("Kill-Switch Gesamtverlust", "%.2f USD" % verlust,
                  "unter %.2f" % ks, verlust < ks))
    frei = bool((w.get("freigabe") or {}).get("erfuellt"))
    p.append(("Freigabe Papier zu Live", "erfuellt" if frei else "nicht erfuellt",
              "Bedingung 1", frei))
    erlaubt = bool(w.get("handel_erlaubt"))
    p.append(("handel_erlaubt", "true" if erlaubt else "false",
              "true fuer Live", erlaubt))
    return p


# Diese beiden Zeilen sind Zustand, keine Auftragswerte: reissen nur sie, ist
# der Auftrag nicht falsch, sondern der Live-Pfad zu. Dann Papier.
ZUSTANDSZEILEN = ("Freigabe Papier zu Live", "handel_erlaubt")


def haelt_alles(pruefungen):
    """Live nur, wenn jede Zeile haelt. Sonst Papier - nie stillschweigend."""
    return all(ok for _n, _i, _s, ok in pruefungen)


def gerissene_grenzen(pruefungen):
    """Die harten Reisser: Auftragswerte, die eine Grenze verletzen."""
    return [n for n, _i, _s, ok in pruefungen
            if not ok and n not in ZUSTANDSZEILEN]


# --- Das Fenster -----------------------------------------------------------

class Freigabefenster:
    """Zeigt einen Auftrag, laesst ihn im Rahmen der Wachen aendern und gibt
    ihn frei oder nicht. Kennt weder Boerse noch Order."""

    def __init__(self, auftraege, spur, w, bestand):
        self.spur, self.w, self.bestand = spur, w, bestand
        self.auftraege = [dict(a) for a in auftraege]
        self.i = 0
        self.ergebnis = []
        self.regler = {}
        self.rechnung, self.pruefungen = None, []

        self.root = tk.Tk()
        self.root.title("Scharfschalten - Spur %s"
                        % ("1 Spot" if spur == "spot" else "2 Hebel"))
        self.root.minsize(600, 0)
        self.root.protocol("WM_DELETE_WINDOW", self._ablehnen)   # Fenster zu = Nein
        self.root.bind("<Escape>", lambda _e: self._ablehnen())

        aussen = ttk.Frame(self.root, padding=14)
        aussen.pack(fill="both", expand=True)

        self.kopf = ttk.Label(aussen, font=("Segoe UI", 13, "bold"))
        self.kopf.pack(anchor="w")
        self.unterkopf = ttk.Label(aussen, foreground="#555")
        self.unterkopf.pack(anchor="w", pady=(0, 10))

        self.reglerbox = ttk.LabelFrame(aussen, text=" Anpassen ", padding=10)
        self.reglerbox.pack(fill="x")

        wertebox = ttk.LabelFrame(aussen, text=" Ergebnis ", padding=10)
        wertebox.pack(fill="x", pady=(10, 0))
        self.werte = ttk.Label(wertebox, font=("Consolas", 10), justify="left")
        self.werte.pack(anchor="w")

        pruefbox = ttk.LabelFrame(aussen, text=" Wachen ", padding=10)
        pruefbox.pack(fill="both", expand=True, pady=(10, 0))
        self.pruefung = ttk.Label(pruefbox, font=("Consolas", 10), justify="left")
        self.pruefung.pack(anchor="w")

        self.hinweis = ttk.Label(aussen, font=("Segoe UI", 10, "bold"),
                                 wraplength=560, justify="left")
        self.hinweis.pack(anchor="w", pady=(10, 0))

        knoepfe = ttk.Frame(aussen)
        knoepfe.pack(fill="x", pady=(12, 0))
        self.ja = ttk.Button(knoepfe, text="Bestaetigen", command=self._bestaetigen)
        self.ja.pack(side="right")
        ttk.Button(knoepfe, text="Ablehnen",
                   command=self._ablehnen).pack(side="right", padx=(0, 8))
        ttk.Button(knoepfe, text="Ueberspringen",
                   command=self._weiter).pack(side="left")

        self._zeige()

    # -- Aufbau je Auftrag --

    def _felder(self, _a):
        """Welche Regler dieser Auftrag bekommt:
        (Schluessel, Text, min, max, Schritt, Einheit).

        Die Obergrenzen kommen aus den Wachen - deshalb kann kein Regler ueber
        eine Grenze hinaus."""
        w = self.w
        if self.spur == "spot":
            return [
                ("usd", "Einsatz", 1.0,
                 float(_z(w, "max_pro_trade_usd", 50)), 1.0, "USD"),
                ("stop_pct", "Stopweite",
                 float(_z(w, "pflicht_stop_prozent_min", 4.0)),
                 float(_z(w, "pflicht_stop_prozent_max", 12.0)), 0.1, "%"),
                ("cr", "Chance zu Risiko",
                 float(_z(w, "mindest_chance_risiko", 1.5)), 5.0, 0.1, "zu 1"),
            ]
        return [
            ("risiko_usd", "Risiko je Anlauf", 0.5,
             float(_z(w, "risiko_je_anlauf_usd", 7.5)), 0.25, "USD"),
            ("stop_atr_faktor", "Stopweite",
             float(_z(w, "stop_atr_faktor", 1.5)), 4.0, 0.1, "ATR"),
            # Deckel senkbar, nie hebbar: das Maximum ist der Wachen-Wert.
            ("hebel", "Hebeldeckel", 1.0,
             float(_z(w, "max_hebel", 5)), 0.5, "x"),
        ]

    def _zeige(self):
        for kind in self.reglerbox.winfo_children():
            kind.destroy()
        self.regler.clear()

        a = self.auftraege[self.i]
        self.kopf.config(text="%s   %s" % (a.get("inst", "?"),
                                           str(a.get("richtung", "long")).upper()))
        self.unterkopf.config(text="Auftrag %d von %d"
                                   % (self.i + 1, len(self.auftraege)))

        for zeile, (schl, text, lo, hi, schritt, einheit) in enumerate(self._felder(a)):
            start = min(max(float(a.get(schl, hi)), lo), hi)
            var = tk.DoubleVar(value=start)
            self.regler[schl] = var
            ttk.Label(self.reglerbox, text=text).grid(row=zeile, column=0,
                                                      sticky="w", pady=3)
            ttk.Scale(self.reglerbox, from_=lo, to=hi, variable=var, length=260,
                      command=lambda _e, k=schl, st=schritt: self._raste(k, st)
                      ).grid(row=zeile, column=1, padx=10)
            marke = ttk.Label(self.reglerbox, width=14, font=("Consolas", 10))
            marke.grid(row=zeile, column=2, sticky="w")
            marke.config(text="%.2f %s" % (start, einheit))
            var.trace_add("write",
                          lambda *_x, m=marke, v=var, e=einheit:
                          m.config(text="%.2f %s" % (v.get(), e)))

        # Einstiegspreis als Textfeld - er kommt vom Markt, nicht vom Regler.
        zeile = len(self.regler)
        ttk.Label(self.reglerbox, text="Einstieg").grid(row=zeile, column=0,
                                                        sticky="w", pady=3)
        self.einstieg = tk.StringVar(value="%.6g" % float(a["einstieg"]))
        ttk.Entry(self.reglerbox, textvariable=self.einstieg, width=18
                  ).grid(row=zeile, column=1, sticky="w", padx=10)
        self.einstieg.trace_add("write", lambda *_x: self._neu())
        self._neu()

    def _raste(self, schluessel, schritt):
        """Regler auf den Schritt runden, damit keine krummen Werte entstehen."""
        var = self.regler[schluessel]
        gerundet = round(var.get() / schritt) * schritt
        if abs(gerundet - var.get()) > 1e-9:
            var.set(gerundet)        # loest _neu ueber die Marken-Spur aus
        self._neu()

    # -- Neuberechnung bei jeder Aenderung --

    def _aktueller(self):
        a = dict(self.auftraege[self.i])
        for schl, var in self.regler.items():
            a[schl] = var.get()
        try:
            a["einstieg"] = float(str(self.einstieg.get()).replace(",", "."))
        except ValueError:
            return None
        return a

    def _neu(self, *_x):
        a = self._aktueller()
        if a is None or a["einstieg"] <= 0:
            self.werte.config(text="Einstieg ist keine Zahl groesser null.")
            self.pruefung.config(text="")
            self.hinweis.config(text="", foreground="black")
            self.ja.state(["disabled"])
            return

        r = RECHNER[self.spur](a, self.w)
        p = pruefe(r, self.w, self.spur, self.bestand)
        self.rechnung, self.pruefungen = r, p

        self.werte.config(text="\n".join([
            "Einstieg        %12.6g" % r["einstieg"],
            "Stop            %12.6g   (%.2f %%)" % (r["stop"], r["stop_pct"]),
            "Ziel            %12.6g   (%.2f zu 1)" % (r["ziel"], r["cr"]),
            "Positionswert   %12.2f USD" % r["positionswert"],
            "Gebunden        %12.2f USD   bei %.1fx" % (r["gebunden"], r["hebel"]),
            "Verlust im Stop %12.2f USD" % r["risiko_usd"],
        ]))
        self.pruefung.config(text="\n".join(
            "%-26s %-16s %-22s %s" % (n, ist, soll, "haelt" if ok else "REISST")
            for n, ist, soll, ok in p))

        harte = gerissene_grenzen(p)
        if harte:
            self.hinweis.config(text="Gesperrt: " + ", ".join(harte)
                                     + ". Werte anpassen oder ablehnen.",
                                foreground="#a00")
            self.ja.state(["disabled"])
        elif haelt_alles(p):
            self.hinweis.config(text="Alle Wachen halten. Bestaetigen schaltet "
                                     "diesen Auftrag scharf - danach laeuft er "
                                     "ohne Rueckfrage.", foreground="#070")
            self.ja.state(["!disabled"])
            self.ja.config(text="Scharf schalten")
        else:
            self.hinweis.config(text="Die Grenzen halten, aber die Freigabe steht "
                                     "noch aus (freigabe.erfuellt / "
                                     "handel_erlaubt). Bestaetigen gibt den "
                                     "Auftrag als PAPIER frei, nicht als "
                                     "Live-Order.", foreground="#a60")
            self.ja.state(["!disabled"])
            self.ja.config(text="Als Papier bestaetigen")

    # -- Knoepfe --

    def _bestaetigen(self):
        a = self._aktueller()
        if a is None or self.rechnung is None:
            return
        a.update({k: self.rechnung[k] for k in ("stop", "ziel", "stop_pct",
                                                "positionswert", "risiko_usd")})
        a["gebunden_usd"] = self.rechnung["gebunden"]
        a["hebel"] = self.rechnung["hebel"]
        a["modus"] = "live" if haelt_alles(self.pruefungen) else "papier"
        self.ergebnis.append(a)
        # Der bestaetigte Auftrag bindet Kapital - der naechste sieht das.
        self.bestand["gebunden_usd"] = (float(self.bestand.get("gebunden_usd", 0.0))
                                        + a["gebunden_usd"])
        self.bestand["offene_positionen"] = int(
            self.bestand.get("offene_positionen", 0)) + 1
        self._weiter()

    def _weiter(self):
        self.i += 1
        if self.i >= len(self.auftraege):
            self.root.destroy()
        else:
            self._zeige()

    def _ablehnen(self):
        self.ergebnis = []          # Ablehnen verwirft auch schon Bestaetigtes
        self.root.destroy()

    def lauf(self):
        self.root.mainloop()
        return self.ergebnis


def bestaetige(auftraege, spur, bestand=None):
    """Zeigt das Fenster und gibt die bestaetigten Auftraege zurueck.

    Leere Liste heisst abgelehnt - und abgelehnt ist auch, wer das Fenster
    schliesst oder Escape drueckt. Es gibt keinen Weg, der ohne Klick
    freigibt."""
    if not auftraege:
        return []
    w = lade_wachen(spur)
    return Freigabefenster(auftraege, spur, w, dict(bestand or {})).lauf()


# --- Kommandozeile ---------------------------------------------------------

BEISPIEL = {
    "spot": [{"inst": "SOL-USDT", "einstieg": 168.42, "stop_pct": 6.0,
              "cr": 2.0, "usd": 50}],
    "hebel": [{"inst": "RE-USD_UM_XPERP-310620", "richtung": "long",
               "einstieg": 1.2345, "atr_pct": 2.9, "risiko_usd": 7.5,
               "hebel": 5}],
}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(
        description="Bestaetigungsfenster zum Scharfschalten. Fuehrt nichts aus.")
    p.add_argument("--spur", choices=("spot", "hebel"), required=True)
    p.add_argument("--auftrag",
                   help="JSON-Datei mit einem Auftrag oder einer Liste; - fuer stdin")
    p.add_argument("--aus", help="bestaetigte Auftraege hierhin schreiben (sonst stdout)")
    p.add_argument("--bestand",
                   help="JSON mit gebunden_usd, offene_positionen, verlust_gesamt_usd")
    p.add_argument("--beispiel", action="store_true",
                   help="mit einem Beispielauftrag oeffnen")
    a = p.parse_args()

    if a.beispiel:
        auftraege = BEISPIEL[a.spur]
    elif a.auftrag == "-":
        auftraege = json.loads(sys.stdin.read())
    elif a.auftrag:
        auftraege = json.loads(Path(a.auftrag).read_text("utf-8"))
    else:
        p.error("--auftrag oder --beispiel angeben")
    if isinstance(auftraege, dict):
        auftraege = [auftraege]

    bestand = json.loads(Path(a.bestand).read_text("utf-8")) if a.bestand else {}
    frei = bestaetige(auftraege, a.spur, bestand)

    text = json.dumps(frei, indent=2, ensure_ascii=False)
    if a.aus:
        Path(a.aus).write_text(text, encoding="utf-8")
        print("%d von %d bestaetigt -> %s" % (len(frei), len(auftraege), a.aus))
    else:
        print(text)
    return 0 if frei else 1


if __name__ == "__main__":
    sys.exit(main())
