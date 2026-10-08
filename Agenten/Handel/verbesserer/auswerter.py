"""Geschlossene Handelsrunden aus dem Journal in Segmente schneiden und einen
Befund je Spur schreiben (Teilproblem 1 des Verbesserers).

Ablauf:

  runden_aus_journal (scanner/wachen_pruefung)   -> je Runde gv in USD
  anreichern                                     -> + score/verhaeltnis/vola aus
                                                    dem Tagesbericht, Wochentag,
                                                    Haltedauer und die Baender
  segmente                                       -> je Merkmal je Auspraegung
                                                    n, mittlerer gv, Trefferquote,
                                                    ev_delta gegen das Gesamtmittel
  permutationstest                               -> p-Wert Gruppe vs. Rest
  befund                                         -> <datum>-befund-<spur>.json

Ein Segment wird nur dann Befund, wenn es mindestens `segment_mindest_n` Runden
umfasst UND der Permutationstest gegen den Rest p < 0.05 liefert. Runden mit
Kaufdatum vor dem Gebuehren-Umstellungsdatum werden getrennt gezaehlt, weil ihre
Kostenbasis eine andere ist.

Nur Standardbibliothek. Der Permutationstest ist ein eigener, mit `seed`
festgenagelter Shuffle - kein SciPy.
"""

import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
_SCANNER = HIER.parent / "scanner"
if str(_SCANNER) not in sys.path:
    sys.path.insert(0, str(_SCANNER))
_BUS = HIER.parent.parent / "Bus"
if str(_BUS) not in sys.path:
    sys.path.insert(0, str(_BUS))
import ereignis                                            # noqa: E402

# Merkmale in fester Reihenfolge - so heissen auch die Schluessel im Befund.
MERKMALE = ("score_band", "verhaeltnis_band", "vola_band", "haltedauer_band",
            "wochentag", "inst", "grund")

_WOCHENTAGE = ("Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
               "Samstag", "Sonntag")

P_SCHWELLE = 0.05


# --- kleine Helfer ------------------------------------------------------

def _mittel(werte):
    """Arithmetisches Mittel; leere Folge -> 0.0."""
    werte = list(werte)
    return sum(werte) / len(werte) if werte else 0.0


def _datum(iso):
    """`date` aus einem ISO-Zeitstempel."""
    return datetime.fromisoformat(iso).date()


def _wochentag(iso):
    """Deutscher Wochentagsname aus einem ISO-Zeitstempel; None -> '?'."""
    if not iso:
        return "?"
    try:
        return _WOCHENTAGE[datetime.fromisoformat(iso).weekday()]
    except ValueError:
        return "?"


def _score_band(s):
    if s is None:
        return "?"
    if s < 60:
        return "<60"
    if s < 70:
        return "60-70"
    if s < 80:
        return "70-80"
    return "80+"


def _verhaeltnis_band(v):
    if v is None:
        return "?"
    if v < 1.5:
        return "<1.5"
    if v < 2.0:
        return "1.5-2"
    return "2+"


def _terzil_grenzen(werte):
    """Zwei Schnittpunkte fuer die Terzile einer sortierten Werteliste.
    Weniger als drei Werte -> (None, None), dann faellt alles auf '?'."""
    werte = sorted(werte)
    if len(werte) < 3:
        return None, None
    n = len(werte)
    return werte[n // 3], werte[(2 * n) // 3]


def _vola_band(v, c1, c2):
    if v is None or c1 is None:
        return "?"
    if v <= c1:
        return "unteres"
    if v < c2:
        return "mittleres"
    return "oberes"


def _haltedauer_band(tage):
    if tage is None:
        return "?"
    if tage <= 2:
        return "<=2T"
    if tage <= 5:
        return "3-5T"
    return ">5T"


def _merkmal_wert(runde, merkmal):
    return runde.get(merkmal)


# --- eigener FIFO-Lauf fuer Kauf- und Verkaufszeit ---------------------

def _kauf_verkauf_zeiten(journal_pfad):
    """Je abgeschlossener Runde (Kaufzeit, Verkaufzeit) - in derselben
    Reihenfolge, in der `wachen_pruefung.runden_aus_journal` die Runden liefert
    (gleiche FIFO-Logik, gleiche Zeilen-Filter). `runden_aus_journal` selbst
    haelt nur die Verkaufszeit als `zeit`; fuer die Haltedauer brauchen wir die
    Kaufzeit, also laufen wir das Journal hier ein zweites Mal ab."""
    p = Path(journal_pfad)
    if not p.exists():
        return []
    offen = {}
    paare = []
    with p.open("r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            inst = r.get("inst")
            try:
                float(r["usd"])
            except (TypeError, ValueError, KeyError):
                continue
            if r["aktion"] == "kauf":
                offen.setdefault(inst, []).append(r["zeit"])
            elif r["aktion"] == "verkauf" and offen.get(inst):
                kauf = offen[inst].pop(0)
                paare.append((kauf, r["zeit"]))
    return paare


def _zeit(iso):
    """ISO-Zeit als UTC-datetime, oder None wenn nicht lesbar."""
    try:
        d = datetime.fromisoformat(str(iso).strip())
    except ValueError:
        return None
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None         else d.astimezone(timezone.utc)


def vor_stichtag(runde, gueltig_ab):
    """Gehoert die Runde in die Zeit VOR `gueltig_ab` (nach Kaufzeit)?

    Ohne lesbare Kaufzeit: ja - ihre Unschuld ist nicht belegbar. Derselbe
    Stichtag und dieselbe Linie wie auswertung_alle.GUELTIG_AB (Scanner-Preisfix
    vom 03.10.2026): die Runden davor messen den Rechenfehler beim Einstieg, und
    ein Segment- oder Permutationstest darauf misst ihn mit.
    """
    d = _zeit(runde.get("kaufzeit"))
    return d is None or d < _zeit(gueltig_ab)


# --- Anreichern -------------------------------------------------------

def anreichern(runden, berichte_dir, journal_pfad=None):
    """Je Runde zusaetzlich:

      score, verhaeltnis, vola_pa  aus dem Tagesbericht `<datum>.json` im Ordner
                                   `berichte_dir` (datum = Tag der `zeit` der
                                   Runde), `None`, wenn kein Bericht oder kein
                                   Eintrag fuer das Instrument passt
      wochentag                    deutscher Name (Einstiegstag, wenn das
                                   Journal vorliegt, sonst Tag der `zeit`)
      haltedauer_tage              Verkaufsdatum - Kaufdatum in Tagen
                                   (`None`, wenn kein Journal uebergeben)
      score_band, verhaeltnis_band, vola_band, haltedauer_band

    `journal_pfad` ist optional: nur damit lassen sich Kaufzeit und Haltedauer
    bestimmen. `runden_aus_journal` fuellt `zeit` mit der Verkaufszeile.
    """
    bdir = Path(berichte_dir)
    _cache = {}

    def bericht(tag):
        if tag not in _cache:
            p = bdir / ("%s.json" % tag)
            try:
                _cache[tag] = json.loads(p.read_text("utf-8")) if p.exists() else None
            except (ValueError, OSError):
                _cache[tag] = None
        return _cache[tag]

    paare = _kauf_verkauf_zeiten(journal_pfad) if journal_pfad else []
    mit_paaren = len(paare) == len(runden)

    ergebnis = []
    for i, r in enumerate(runden):
        rr = dict(r)
        verkaufzeit = r.get("zeit", "")
        kaufzeit = paare[i][0] if mit_paaren else None

        # Merkmale sollen die Lage beim Einstieg beschreiben. Liegt das Journal
        # vor, ist die Kaufzeit aus dem zweiten FIFO-Lauf bekannt und der
        # Einstiegstag-Bericht wird gesucht. Nur ohne Journal faellt die Suche
        # auf den Verkaufstag zurueck, den `runden_aus_journal` in `zeit` legt.
        tag = (kaufzeit or verkaufzeit)[:10]
        b = bericht(tag)
        score = verhaeltnis = vola = None
        if b:
            for w in b.get("werte", []):
                if w.get("inst") == r.get("inst"):
                    score = w.get("score")
                    verhaeltnis = w.get("verhaeltnis")
                    vola = (w.get("kennzahlen") or {}).get("volatilitaet_pa")
                    break
        rr["score"] = score
        rr["verhaeltnis"] = verhaeltnis
        rr["vola_pa"] = vola
        rr["kaufzeit"] = kaufzeit
        rr["wochentag"] = _wochentag(kaufzeit or verkaufzeit)
        if mit_paaren and kaufzeit:
            rr["haltedauer_tage"] = (_datum(paare[i][1]) - _datum(kaufzeit)).days
        else:
            rr["haltedauer_tage"] = None
        ergebnis.append(rr)

    c1, c2 = _terzil_grenzen(x["vola_pa"] for x in ergebnis
                             if x["vola_pa"] is not None)
    for rr in ergebnis:
        rr["score_band"] = _score_band(rr["score"])
        rr["verhaeltnis_band"] = _verhaeltnis_band(rr["verhaeltnis"])
        rr["vola_band"] = _vola_band(rr["vola_pa"], c1, c2)
        rr["haltedauer_band"] = _haltedauer_band(rr["haltedauer_tage"])
    return ergebnis


# --- Segmente -------------------------------------------------------

def segmente(runden_angereichert, mindest_n):
    """`{merkmal: {auspraegung: {n, mittel_gv, trefferquote, ev_delta}}}`.

    Nur Auspraegungen mit `n >= mindest_n` erscheinen. `ev_delta` ist das
    Mittel der Auspraegung minus dem Gesamtmittel ueber alle Runden.
    """
    runden = list(runden_angereichert)
    gesamtmittel = _mittel(r["gv"] for r in runden)
    ergebnis = {}
    for merkmal in MERKMALE:
        auspraegungen = {}
        for wert in sorted({_merkmal_wert(r, merkmal) for r in runden}, key=str):
            gruppe = [r for r in runden if _merkmal_wert(r, merkmal) == wert]
            n = len(gruppe)
            if n < mindest_n:
                continue
            gv = [r["gv"] for r in gruppe]
            mittel = _mittel(gv)
            auspraegungen[wert] = {
                "n": n,
                "mittel_gv": mittel,
                "trefferquote": sum(1 for x in gv if x > 0) / n,
                "ev_delta": mittel - gesamtmittel,
            }
        ergebnis[merkmal] = auspraegungen
    return ergebnis


# --- Permutationstest -------------------------------------------------

def permutationstest(gruppe, rest, seed=1, runden=2000):
    """p-Wert fuer 'der mittlere gv der Gruppe unterscheidet sich vom Rest'.

    Teststatistik ist `abs(mean(gruppe) - mean(rest))`. `runden`-mal werden die
    Labels ueber den zusammengelegten Topf gemischt; p ist der Anteil der
    gemischten Statistiken, die die beobachtete erreichen oder uebertreffen.
    Mit festem `seed` deterministisch. Leere Gruppe oder leerer Rest -> 1.0.
    """
    g = [r["gv"] for r in gruppe]
    h = [r["gv"] for r in rest]
    if not g or not h:
        return 1.0
    beobachtet = abs(_mittel(g) - _mittel(h))
    topf = g + h
    n_g = len(g)
    wuerfel = random.Random(seed)
    treffer = 0
    for _ in range(runden):
        wuerfel.shuffle(topf)
        if abs(_mittel(topf[:n_g]) - _mittel(topf[n_g:])) >= beobachtet - 1e-9:
            treffer += 1
    return treffer / runden


# --- Befund -------------------------------------------------------

def befund(spur_konf, konfig, ausgabe_dir):
    """Schreibt `ausgabe_dir/<heute>-befund-<name>.json` und gibt denselben
    Inhalt zurueck:

      segmente               volle Segment-Tabelle (mindest_n aus der Konfig)
      befunde                Liste der Auspraegungen mit n >= mindest_n und
                             Permutationstest p < 0.05 gegen den Rest
      runden_gesamt          Anzahl geschlossener Runden (nach Stichtag)
      runden_vor_stichtag    davon ausgeschlossen: Kaufzeit < spur_konf
                             ["gueltig_ab"] (leer: 0, kein Stichtag)
      runden_vor_umstellung  davon mit Kaufdatum < gebuehr_umstellung_datum
      erzeugt                Zeitstempel

    `name` kommt aus `spur_konf["name"]`, Vorgabe 'spur1'.

    Meldet Start/Ende an den Bus (Aufgabe 7) - der Bus haengt sich nur
    aussen an, die Rechnung selbst bleibt unveraendert.
    """
    with ereignis.lauf("handel/verbesserer"):
        return _befund(spur_konf, konfig, ausgabe_dir)


def _befund(spur_konf, konfig, ausgabe_dir):
    import wachen_pruefung as wp

    journal = spur_konf["journal"]
    name = spur_konf.get("name", "spur1")
    mindest_n = int(konfig["segment_mindest_n"])
    umstellung = konfig["gebuehr_umstellung_datum"]

    roh = wp.runden_aus_journal(journal)
    angereichert = anreichern(roh, spur_konf["berichte"], journal)
    # Stichtag aus spuren.json: Runden mit Kaufzeit davor zaehlen nicht, werden
    # aber AUSGEWIESEN (runden_vor_stichtag) - sonst sieht ein kleiner Befund
    # aus wie eine kleine Stichprobe statt wie ein abgeschnittenes Journal.
    gueltig_ab = spur_konf.get("gueltig_ab")
    runden_alle = len(angereichert)
    if gueltig_ab:
        angereichert = [r for r in angereichert
                        if not vor_stichtag(r, gueltig_ab)]
    seg = segmente(angereichert, mindest_n)

    befunde = []
    for merkmal, auspraegungen in seg.items():
        for wert, kennzahlen in auspraegungen.items():
            gruppe = [r for r in angereichert
                      if _merkmal_wert(r, merkmal) == wert]
            uebrig = [r for r in angereichert
                      if _merkmal_wert(r, merkmal) != wert]
            if len(gruppe) < mindest_n or not uebrig:
                continue
            p = permutationstest(gruppe, uebrig)
            if p < P_SCHWELLE:
                befunde.append({
                    "merkmal": merkmal,
                    "auspraegung": wert,
                    "n": kennzahlen["n"],
                    "mittel_gv": kennzahlen["mittel_gv"],
                    "trefferquote": kennzahlen["trefferquote"],
                    "ev_delta": kennzahlen["ev_delta"],
                    "p": p,
                })

    vor = sum(1 for kauf, _ in _kauf_verkauf_zeiten(journal)
              if kauf[:10] < umstellung)

    ergebnis = {
        "segmente": seg,
        "befunde": befunde,
        "runden_gesamt": len(angereichert),
        "runden_vor_umstellung": vor,
        "runden_vor_stichtag": runden_alle - len(angereichert),
        "gueltig_ab": gueltig_ab,
        "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    ziel = Path(ausgabe_dir)
    ziel.mkdir(parents=True, exist_ok=True)
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (ziel / ("%s-befund-%s.json" % (heute, name))).write_text(
        json.dumps(ergebnis, ensure_ascii=False, indent=2), "utf-8")
    return ergebnis
