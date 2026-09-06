"""TP3 Teil 3: aus dem Suchergebnis die Vorschlagsartefakte bauen.

Eingang ist das Ergebnis von ``suche.suche`` (Task 9)::

    {"kandidat", "basis_wf", "kandidat_wf", "auswertungen", "grund",
     "aenderungen"}

``aenderungen`` ist ein *flacher* Diff Kandidat gegen Basis in
wachen.json-Schluesseln (``mindest_score``, ``max_volatilitaet_pa``,
``mindest_chance_risiko``, ``pflicht_stop_prozent_min/max``,
``abklingzeit_tage``, ``watchlist``). Gewichtsaenderungen stehen nicht darin -
sie werden aus ``kandidat["gewichte"]`` als Patch fuer bewertung.py abgeleitet.

``baue`` schreibt in den Vorschlagsordner - nie neben die Quelldateien:

* ``bericht.md``       - Vorher/Nachher, vier Pflichtzahlen, Warnungen, Diff
* ``wachen.neu.json``  - Rohtext der wachen.json mit ersetzten Werten (CRLF
                         und jede Formatierung bleiben unangetastet)
* ``bewertung.patch``  - Unified-Diff der beiden Gewichtskonstanten
* ``commit.txt``       - Commit-Text mit den vier Pflichtzahlen und dem
                         OOS-Delta

Ruling aus dem Task-9-Review: ein Gewinner, dessen einzige Aenderung die
Sizing-Kurve ist (``aenderungen == {}`` und kein Gewichts-Diff), hat in Spur 1
keinen Anwendungspfad. Dann schreibt ``baue`` nur einen Hinweis-Bericht im
Stil von ``kein_vorschlag`` - keine wachen.neu.json, kein commit.txt.

Nur Standardbibliothek.
"""

import difflib
import json
import re
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent

# Diese Schluessel wandern nie in wachen.neu.json - sie sind Gruppen, kein
# einzelner wachen.json-Wert. (suche.suche liefert sie ohnehin nicht in
# ``aenderungen``; hier nur als Gurt.)
_GEWICHTS_SCHLUESSEL = frozenset({"chance", "risiko", "gewichte"})


# --- kleine Formathelfer ----------------------------------------------------

def _heute():
    return date.today().isoformat()


def _als_json(wert):
    """JSON-Form eines Werts fuer die Text-Ersetzung.

    Listen kompakt mit Leerzeichen nach Komma; Zahlen als ``repr`` ohne
    Exponentialschreibweise; Bool als ``true``/``false``.
    """
    if isinstance(wert, bool):
        return "true" if wert else "false"
    if isinstance(wert, list):
        return json.dumps(wert, separators=(", ", ": "), ensure_ascii=False)
    if isinstance(wert, float):
        t = repr(wert)
        if "e" in t or "E" in t:
            t = ("%.12f" % wert).rstrip("0")
            if t.endswith("."):
                t += "0"
        return t
    if isinstance(wert, int):
        return repr(wert)
    return json.dumps(wert, ensure_ascii=False)


def _prozent(x):
    """Anteil (0..1) als Prozent mit einer Nachkommastelle; ``None`` -> n/a."""
    if x is None:
        return "n/a"
    return "%.1f%%" % (x * 100.0)


def _zahl4(x):
    return "n/a" if x is None else "%.4f" % x


# --- wachen.neu.json -------------------------------------------------------

def wachen_neu_text(alt_text, aenderungen):
    """Rohtext der wachen.json mit ersetzten Werten - je Schluessel genau ein
    ``re.sub`` mit ``count=1``. Zeilenenden und jede sonstige Formatierung
    bleiben unberuehrt (kein ``json.loads``/``json.dumps`` der ganzen Datei).
    """
    neu = alt_text
    for key, wert in aenderungen.items():
        if key in _GEWICHTS_SCHLUESSEL:
            continue
        muster = (r'("' + re.escape(key) + r'"\s*:\s*)'
                  r'(\[[^\]]*\]|[^,\n\r}]+)')
        ersatz = _als_json(wert)
        neu = re.sub(muster, lambda m, e=ersatz: m.group(1) + e, neu, count=1)
    return neu


def _alt_wert(alt_text, key):
    """Bisheriger Rohwert eines Schluessels aus dem wachen.json-Text."""
    if not alt_text:
        return "?"
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*(\[[^\]]*\]|[^,\n\r}]+)',
                  alt_text)
    return m.group(1).strip() if m else "?"


# --- bewertung.patch -----------------------------------------------------

def _dict_literal(d):
    return "{" + ", ".join('"%s": %s' % (k, _als_json(v))
                           for k, v in d.items()) + "}"


def _ersetze_konstante(text, name, gruppe):
    """``<name> = {...}`` im Quelltext auf ``gruppe`` setzen. Leere ``gruppe``
    oder kein Treffer -> Text unveraendert."""
    if not gruppe:
        return text
    muster = re.compile(re.escape(name) + r"\s*=\s*\{[^}]*\}")
    if not muster.search(text):
        return text
    ersatz = name + " = " + _dict_literal(gruppe)
    return muster.sub(lambda _m, e=ersatz: e, text, count=1)


def bewertung_patch(alt_datei, chance_g, risiko_g):
    """Unified-Diff, der ``CHANCE_GEWICHTE`` und ``RISIKO_GEWICHTE`` im
    Quelltext auf die neuen Dicts setzt. Leerer String, wenn nichts sich
    aendert (auch bei leeren Gewicht-Dicts)."""
    pfad = Path(alt_datei)
    alt = pfad.read_text(encoding="utf-8")
    neu = _ersetze_konstante(alt, "CHANCE_GEWICHTE", chance_g or {})
    neu = _ersetze_konstante(neu, "RISIKO_GEWICHTE", risiko_g or {})
    if neu == alt:
        return ""
    diff = difflib.unified_diff(
        alt.splitlines(keepends=True), neu.splitlines(keepends=True),
        fromfile="a/" + pfad.name, tofile="b/" + pfad.name)
    return "".join(diff)


# --- commit.txt --------------------------------------------------------

def commit_text(spur_name, basis_wf, kandidat_wf, aenderungen):
    """Mehrzeiliger Commit-Text: Titel, vier Pflichtzahlen, OOS-Delta, Liste
    der geaenderten Schluessel, Co-Authored-By-Trailer."""
    b = basis_wf["gesamt"]
    k = kandidat_wf["gesamt"]
    if aenderungen:
        schluessel = "Geaenderte Schluessel: " + ", ".join(aenderungen.keys())
    else:
        schluessel = "Geaenderte Schluessel: (nur Gewichte)"
    zeilen = [
        "verbesserer: %s Parameter angepasst" % spur_name,
        "",
        "Vier Pflichtzahlen (OOS-Aggregat des Kandidaten):",
        "  Gebuehr je Runde:    %s" % _prozent(k.get("gebuehr_runde_pct")),
        "  Trefferquote:        noetig %s, beobachtet %s" % (
            _prozent(k.get("noetige_trefferquote")),
            _prozent(k.get("beobachtete_trefferquote"))),
        "  Liquidationsabstand: n/a (Spot)",
        "  Funding:             n/a (Spot)",
        "",
        "OOS netto_gv_je_runde: %.4f -> %.4f" % (
            b["netto_gv_je_runde"], k["netto_gv_je_runde"]),
        "",
        schluessel,
        "",
        "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>",
    ]
    return "\n".join(zeilen) + "\n"


# --- bericht.md --------------------------------------------------------

def _fenster_besser(kandidat_wf, basis_wf):
    kf = kandidat_wf.get("fenster", [])
    bf = basis_wf.get("fenster", [])
    return sum(1 for i in range(min(len(kf), len(bf)))
               if kf[i]["kennzahlen"]["netto_gv_je_runde"]
               > bf[i]["kennzahlen"]["netto_gv_je_runde"])


def _tabelle_vorher_nachher(basis_wf, kandidat_wf):
    z = ["| Fenster | netto_gv_je_runde vorher | nachher | n vorher | n nachher |",
         "|---|---|---|---|---|"]
    bf, kf = basis_wf.get("fenster", []), kandidat_wf.get("fenster", [])
    for i in range(min(len(bf), len(kf))):
        bk, kk = bf[i]["kennzahlen"], kf[i]["kennzahlen"]
        z.append("| %s-%s | %s | %s | %s | %s |" % (
            bf[i]["von_tag"], bf[i]["bis_tag"],
            _zahl4(bk.get("netto_gv_je_runde")),
            _zahl4(kk.get("netto_gv_je_runde")),
            bk.get("n", "?"), kk.get("n", "?")))
    bg, kg = basis_wf["gesamt"], kandidat_wf["gesamt"]
    z.append("| Aggregat | %s | %s | %s | %s |" % (
        _zahl4(bg.get("netto_gv_je_runde")), _zahl4(kg.get("netto_gv_je_runde")),
        bg.get("n", "?"), kg.get("n", "?")))
    return z


def _abschnitt_pflichtzahlen(gesamt):
    return [
        "## Vier Pflichtzahlen",
        "",
        "- Gebuehr je Runde: %s" % _prozent(gesamt.get("gebuehr_runde_pct")),
        "- Trefferquote: noetig %s, beobachtet %s" % (
            _prozent(gesamt.get("noetige_trefferquote")),
            _prozent(gesamt.get("beobachtete_trefferquote"))),
        "- Liquidationsabstand: n/a (Spot)",
        "- Funding: n/a (Spot)",
    ]


def _abschnitt_warnungen(ergebnis):
    kg = ergebnis["kandidat_wf"]["gesamt"]
    kbes = _fenster_besser(ergebnis["kandidat_wf"], ergebnis["basis_wf"])
    return [
        "## Warnungen",
        "",
        "- Das Kostenmodell des Backtests ist strenger als das Alt-Journal: er "
        "rechnet %s Gebuehr je Runde; die alten Journalrunden entstanden unter "
        "einer anderen Kostenbasis." % _prozent(kg.get("gebuehr_runde_pct")),
        "- Die Historie umfasst nur etwa ein bis zwei Jahre Tageskerzen - "
        "wenige echte Regimewechsel im Fenster.",
        "- Kein Survivorship-Schutz: es sind nur heute noch gelistete "
        "Instrumente auf der Watchlist, ausgefallene fehlen.",
        "- Overfitting-Sperre bestanden: %s (%d Fenster besser, n = %s "
        "OOS-Runden)." % (ergebnis.get("grund", ""), kbes, kg.get("n", "?")),
    ]


def _abschnitt_schluessel(aenderungen, alt_text):
    z = ["## Geaenderte Schluessel", ""]
    if aenderungen:
        for key, wert in aenderungen.items():
            z.append("- %s: %s -> %s" % (
                key, _alt_wert(alt_text, key), _als_json(wert)))
    else:
        z.append("- (nur Gewichte, siehe bewertung.patch)")
    return z


def _bericht_voll(ordner, ergebnis, spur_name, aenderungen, alt_text):
    z = ["# Verbesserungsvorschlag - %s" % spur_name, "",
         "Datum: %s" % _heute(), "",
         "Grund: %s" % ergebnis.get("grund", ""), "",
         "## Vorher / Nachher", ""]
    z += _tabelle_vorher_nachher(ergebnis["basis_wf"], ergebnis["kandidat_wf"])
    z += ["", "OOS netto_gv_je_runde: %.4f -> %.4f" % (
        ergebnis["basis_wf"]["gesamt"]["netto_gv_je_runde"],
        ergebnis["kandidat_wf"]["gesamt"]["netto_gv_je_runde"]), ""]
    z += _abschnitt_pflichtzahlen(ergebnis["kandidat_wf"]["gesamt"])
    z += [""]
    z += _abschnitt_warnungen(ergebnis)
    z += [""]
    z += _abschnitt_schluessel(aenderungen, alt_text)
    z += [""]
    (ordner / "bericht.md").write_text("\n".join(z), encoding="utf-8",
                                       newline="\n")


def _bericht_baseline(ordner, ergebnis, spur_name, grund, mit_delta):
    b = ergebnis["basis_wf"]
    z = ["# Kein Vorschlag - %s" % spur_name, "",
         "Datum: %s" % _heute(), "",
         "Grund: %s" % grund, ""]
    if mit_delta and ergebnis.get("kandidat_wf"):
        z += ["OOS netto_gv_je_runde: %.4f -> %.4f" % (
            b["gesamt"]["netto_gv_je_runde"],
            ergebnis["kandidat_wf"]["gesamt"]["netto_gv_je_runde"]), ""]
    z += ["## Baseline-Kennzahlen", "",
          "| Fenster | netto_gv_je_runde | n | max_drawdown |",
          "|---|---|---|---|"]
    for fen in b.get("fenster", []):
        kk = fen["kennzahlen"]
        z.append("| %s-%s | %s | %s | %s |" % (
            fen["von_tag"], fen["bis_tag"], _zahl4(kk.get("netto_gv_je_runde")),
            kk.get("n", "?"), _zahl4(kk.get("max_drawdown"))))
    g = b["gesamt"]
    z.append("| Aggregat | %s | %s | %s |" % (
        _zahl4(g.get("netto_gv_je_runde")), g.get("n", "?"),
        _zahl4(g.get("max_drawdown"))))
    z.append("")
    (ordner / "bericht.md").write_text("\n".join(z), encoding="utf-8",
                                       newline="\n")


# --- Orchestrierung -----------------------------------------------------

def _aufloesen(pfad):
    """Pfad aus ``spuren.json`` - absolut lassen, relativ zum verbesserer/-Ordner
    aufloesen."""
    p = Path(pfad)
    return p if p.is_absolute() else (HIER / p).resolve()


def kein_vorschlag(ordner, ergebnis, spur_name):
    """Nur ``ordner/bericht.md`` mit dem Grund und der Baseline-Kennzahltabelle -
    sonst nichts."""
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    _bericht_baseline(ordner, ergebnis, spur_name, ergebnis.get("grund", ""),
                      mit_delta=False)


def baue(ordner, ergebnis, spur, konfig):
    """Vorschlagsartefakte in ``ordner`` schreiben.

    * ``kandidat is None`` -> wie ``kein_vorschlag``.
    * ``aenderungen == {}`` und kein Gewichts-Diff -> nur ein Hinweis-Bericht:
      der beste Kandidat aendert nur die Sizing-Kurve, wofuer Spur 1 keinen
      Anwendungspfad hat (Ruling Task 9). Inkl. OOS-Delta.
    * ``aenderungen == {}`` mit Gewichts-Diff -> bericht.md, bewertung.patch,
      commit.txt (Schluesselzeile ``(nur Gewichte)``); keine wachen.neu.json.
    * ``aenderungen`` gefuellt -> alle vier Dateien.
    """
    _ = konfig  # derzeit ungenutzt; Kennzahlen kommen aus ``ergebnis``.
    ordner = Path(ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    spur_name = spur.get("name", "spur1")

    kandidat = ergebnis.get("kandidat")
    if kandidat is None:
        _bericht_baseline(ordner, ergebnis, spur_name,
                          ergebnis.get("grund", ""), mit_delta=False)
        return

    aenderungen = {k: v for k, v in (ergebnis.get("aenderungen") or {}).items()
                   if k not in _GEWICHTS_SCHLUESSEL}

    gewichte = kandidat.get("gewichte") or {}
    patch = bewertung_patch(_aufloesen(spur["bewertung_datei"]),
                            gewichte.get("chance") or {},
                            gewichte.get("risiko") or {})

    # Sizing-only: kein anwendbarer Parameter-Diff -> nur Hinweis-Bericht.
    if not aenderungen and not patch:
        neu_sizing = kandidat.get("sizing", "flach")
        grund = ("bester Kandidat aendert nur die Sizing-Kurve "
                 "(flach -> %s); dafuer gibt es in Spur 1 noch keinen "
                 "Anwendungspfad - nur als Hinweis vermerkt." % neu_sizing)
        _bericht_baseline(ordner, ergebnis, spur_name, grund, mit_delta=True)
        return

    alt_text = None
    if aenderungen:
        with open(_aufloesen(spur["wachen"]), "r", encoding="utf-8",
                  newline="") as f:
            alt_text = f.read()

    _bericht_voll(ordner, ergebnis, spur_name, aenderungen, alt_text)
    (ordner / "bewertung.patch").write_text(patch, encoding="utf-8",
                                            newline="\n")
    (ordner / "commit.txt").write_text(
        commit_text(spur_name, ergebnis["basis_wf"], ergebnis["kandidat_wf"],
                    aenderungen),
        encoding="utf-8", newline="\n")

    if aenderungen:
        neu_text = wachen_neu_text(alt_text, aenderungen)
        with open(ordner / "wachen.neu.json", "w", encoding="utf-8",
                  newline="") as f:
            f.write(neu_text)
