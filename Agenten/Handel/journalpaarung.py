#!/usr/bin/env python3
"""Einstieg und Ausstieg einander zuordnen - EINE Umsetzung fuer alle Auswertungen.

WARUM ES DIESES MODUL GIBT (T-095, 30.09.2026)
----------------------------------------------
Die Auswertungen paarten Einstieg und Ausstieg **je Instrument** (`offen[inst]`).
Zwei gleichzeitige Positionen im selben Instrument ueberschreiben einander: der
erste Ausstieg paart dann mit dem falschen Einstieg, der ueberschriebene Einstieg
faellt ganz weg. Gemessen im Backtest ueber 5,7 Jahre (squeeze): 1092 Einstiege,
1088 Ausstiege - und nur **759** ausgewertete Runden. Trefferquote und
`kosten_wendepunkt.f_max` standen damit auf einer nicht zufaelligen Teilmenge
(gleichzeitige Positionen im selben Instrument sind eher gleichgerichtet).

DIE REGEL - vier Stufen, keine davon geraten
--------------------------------------------
1. **Kennung** (`pos_id`): traegt die Ausstiegszeile die Kennung ihres Einstiegs,
   ist die Zuordnung die Zeile selbst. Das ist der Normalfall ab 30.09.2026.
2. Genau EIN offener Einstieg dieses Instruments (Altjournal ohne Kennung):
   eindeutig, unabhaengig von der Zeilenreihenfolge.
3. Mehrere offene, aber genau EINE passt zu der Kopie, die die Ausstiegszeile
   mitfuehrt (Stop, Ziel, Kontraktzahl/Menge - Felder, die sie von ihrem
   Einstieg kopiert, siehe `MERKMAL_FELDER`): eindeutig. Kopierte Felder sind
   ein Beleg, kein Anhaltspunkt - `nominal`/`margin` gehoeren NICHT dazu, sie
   werden beim Ausstieg neu gerechnet.
4. Genau EIN offener Einstieg MIT Kennung und keiner ohne (Code-Wechsel: Einstieg
   neu geschrieben, Ausstieg noch alt): eindeutig.
Sonst: die Zeile zaehlt als **unpaarig** und wird AUSGEWIESEN - eine Zeile ohne
Gegenstueck ist ein Befund, kein zu erratender Partner. Frueher fiel sie still
heraus; genau das machte die Quote zu gut und die Rundenzahl zu klein.

Eine blosse Warteschlange je Instrument ("wer zuerst kauft, verkauft zuerst")
waere eine ANNAHME: bei zwei gleichzeitigen Positionen entscheidet sie den Fall,
ohne ihn zu kennen. Deshalb Stufe 2 statt Warteschlange.

WER DAS MODUL BENUTZT
---------------------
`kosten_wendepunkt.py` (R/C/Trefferquote je Spur) und `auswertung_alle.py`
(Ergebnis, Einsatz, Grund je Runde). Beide brauchen dieselbe Zuordnung - zwei
Fassungen wuerden auseinanderlaufen und zwei verschiedene Rundenzahlen fuer
dieselbe Spur liefern.
"""

from __future__ import annotations

import csv

# Die Aktionsnamen, wie sie in den Journalen stehen. Sie unterscheiden sich je
# Spur (scanner schreibt "kauf"/"verkauf", xperp "eroeffnen"/"schliessen"),
# deshalb sind es zwei Tupel und keine Aufzaehlung.
EINSTIEG = ("kauf", "eroeffnen", "KAUF", "EINSTIEG", "buy")
AUSSTIEG = ("verkauf", "schliessen", "AUSSTIEG", "sell", "exit")

# Die Spaltennamen, unter denen das Instrument stehen kann. `inst` ist der
# Hausname, `paar`/`symbol`/`token` sind die Abweichungen einzelner Spuren.
SCHLUESSEL_FELDER = ("inst", "paar", "symbol", "token")


def zahl(zeile, *namen):
    """Der erste lesbare Zahlenwert dieser Zeile - None, wenn keiner da ist."""
    for n in namen:
        v = zeile.get(n)
        if v not in (None, ""):
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def gv_aus_zeile(zeile):
    """Der G/V einer Ausstiegszeile, wenn sie ihn direkt traegt - sonst None.

    Seit 22.10.2026 schreibt spur_buch die Verkaufszeile mit `gv_usd` (dem
    Gewinn/Verlust der Runde). Traegt eine Zeile das Feld, ist es die
    Wahrheit der Runde und die Auswertung soll es verwenden statt den G/V
    aus der Paarung von kauf/verkauf zu schaetzen. Fehlt das Feld (Altjournal
    oder eine Spur, die es nicht schreibt), liefert diese Funktion None und
    der Aufrufer rechnet wie bisher - rueckwaertskompatibel.
    """
    return zahl(zeile, "gv_usd")


def kennung(zeile):
    """Die Positionskennung einer Journalzeile ('' bei Altjournalen)."""
    return (zeile.get("pos_id") or "").strip()


def schluessel(zeile):
    """Das Instrument einer Journalzeile - erster gefuellter Name gewinnt."""
    for n in SCHLUESSEL_FELDER:
        w = (zeile.get(n) or "").strip()
        if w:
            return w
    return ""


def gleich(a, b):
    """Zwei Preise aus dem Journal - Zahl gegen Zahl, nicht Text gegen Text."""
    if a is None or b is None:
        return False
    return abs(a - b) <= max(abs(a), abs(b)) * 1e-9


# Die Felder, in denen eine Ausstiegszeile die Position ihrer Einstiegszeile
# KOPIERT. Nicht der Kurs (der bewegt sich) und nicht `nominal`/`margin` (die
# werden neu gerechnet), sondern das, was die Position ausmacht: ihre Grenzen
# und ihre Groesse. Fehlt ein Feld auf einer Seite, wird es nicht verglichen.
MERKMAL_FELDER = ("stop", "ziel", "stop_pct", "ziel_pct", "kontrakte", "menge",
                  "stueck", "hebel", "seite")


def _wert(gleich_text):
    """Ein Merkmalswert - Zahl, wenn er eine ist, sonst Text.

    `25` und `25.0` sind derselbe Kontraktstand; als Text waeren sie
    verschieden.
    """
    try:
        return ("z", float(gleich_text))
    except (TypeError, ValueError):
        return ("t", gleich_text)


def merkmale_standard(zeile):
    """Die Positionsmerkmale einer Zeile, wie sie im Journal stehen."""
    return {f: _wert((zeile.get(f) or "").strip())
            for f in MERKMAL_FELDER if (zeile.get(f) or "").strip()}


def passt(a, b):
    """True, wenn zwei Zeilen sich in JEDEM gemeinsamen Merkmal gleichen.

    Ohne gemeinsames Merkmal gibt es keinen Beleg - dann passt es nicht.
    """
    gemeinsam = [f for f in a if f in b]
    if not gemeinsam:
        return False
    return all(a[f] == b[f] for f in gemeinsam)


class Paarung:
    """Ordnet die Ausstiegszeilen eines Journals ihren Einstiegszeilen zu.

    Aufruf:
        p = Paarung()
        for ein, aus in p.zuordnen(zeilen):
            ...
        p.unpaarig, p.offen, p.ohne_kennung      # die Zahlen zum Ausweisen

    `einstieg`/`ausstieg` sind die Aktionsnamen, `merkmale` liefert die
    Positionsmerkmale einer Zeile (fuer Stufe 3), `einstieg_ok` entscheidet, ob
    eine Einstiegszeile ueberhaupt als offene Position gefuehrt wird
    (kosten_wendepunkt braucht Stop und Ziel, auswertung_alle nicht).
    """

    def __init__(self, einstieg=EINSTIEG, ausstieg=AUSSTIEG,
                 merkmale=merkmale_standard, einstieg_ok=None):
        self.einstieg = einstieg
        self.ausstieg = ausstieg
        self.merkmale = merkmale
        self.einstieg_ok = einstieg_ok
        # offene Positionen, nach Kennung bzw. nach Instrument
        self._mit_kennung = {}
        self._ohne_kennung = {}
        self.unpaarig = 0        # Ausstiegszeilen ohne Partner
        self.ohne_kennung = 0    # Einstiege aus Altjournalen
        self.ohne_partner_alt = 0  # davon zweideutig geblieben (nicht geraten)
        self.ausstiege_ohne_inst = 0

    # -- die offene Position finden (Stufen 1-4) ---------------------------
    def _altbestand(self, inst, aus):
        """Der Einstieg zu einer Ausstiegszeile OHNE Kennung (Altjournal)."""
        kette = self._ohne_kennung.get(inst) or []
        if len(kette) == 1:
            return kette.pop(0)                      # Stufe 2
        if len(kette) > 1:
            m_aus = self.merkmale(aus)
            treffer = [i for i, e in enumerate(kette)
                       if passt(self.merkmale(e), m_aus)]
            if len(treffer) == 1:
                return kette.pop(treffer[0])         # Stufe 3
            # mehrere gleichartige Positionen: NICHT raten
            self.ohne_partner_alt += 1
            return None
        # Stufe 4: der Code-Wechsel (Einstieg neu, Ausstieg noch alt). Nur wenn
        # GENAU EIN Kandidat mit Kennung offen ist - sonst waere es geraten.
        kandidaten = [k for k, e in self._mit_kennung.items()
                      if self._inst_von(e) == inst]
        if len(kandidaten) == 1:
            # `_mit_kennung` traegt (inst, zeile) - der Aufrufer braucht die
            # ZEILE. Ohne das [1] kam hier ein Tupel heraus und `schluessel()`
            # in `_paare` rief `.get()` darauf auf: AttributeError 'tuple' has
            # no attribute 'get' (gemessen 02.10.2026 an einer scanner-Zeile
            # mit `pos_id: None` - ein leerer Kennungswert aus dem CSV-Rest).
            return self._mit_kennung.pop(kandidaten[0])[1]
        return None

    @staticmethod
    def _inst_von(eintrag):
        return eintrag[0]

    def _ablegen(self, zeile):
        """Eine Einstiegszeile als offene Position fuehren."""
        k = kennung(zeile)
        inst = schluessel(zeile)
        if k:
            self._mit_kennung[k] = (inst, zeile)
        else:
            self.ohne_kennung += 1
            self._ohne_kennung.setdefault(inst, []).append(zeile)

    def zuordnen(self, zeilen):
        """[(einstieg, ausstieg)] in der Reihenfolge des Journals."""
        paare = []
        for r in zeilen:
            art = (r.get("aktion") or "").strip()
            if art in self.einstieg:
                inst = schluessel(r)
                if not inst:
                    continue
                if self.einstieg_ok is not None and not self.einstieg_ok(r):
                    continue
                self._ablegen(r)
                continue
            if art not in self.ausstieg:
                continue
            inst = schluessel(r)
            if not inst:
                self.ausstiege_ohne_inst += 1
                continue
            k = kennung(r)
            if k:
                eintrag = self._mit_kennung.pop(k, None)
                ein = eintrag[1] if eintrag else None
            else:
                ein = self._altbestand(inst, r)
            if ein is None:
                self.unpaarig += 1
                continue
            paare.append((ein, r))
        return paare

    @property
    def offen(self):
        """Einstiege ohne Ausstieg - offene Positionen am Journalende."""
        return sum(len(v) for v in self._ohne_kennung.values()) \
            + len(self._mit_kennung)

    def stand(self):
        """Die Zahlen, die jede Auswertung ausweisen soll."""
        return {"unpaarig": self.unpaarig, "offen": self.offen,
                "ohne_kennung": self.ohne_kennung,
                "zweideutig": self.ohne_partner_alt,
                "ohne_instrument": self.ausstiege_ohne_inst}


def zeilen(pfad):
    """Ein Journal als Liste von dicts - leer, wenn es keine Datei gibt."""
    try:
        with open(pfad, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except OSError:
        return []