"""Tests fuer den Omniquant-Block im Tagesbericht - ohne Netz.

Der Block liest omniquant/wachen.json, zustand.json und das Journal; hier
laufen alle drei in einem temp-Ordner. Belegt wird:

  1. Die Bilanzzeile steht im Bericht und kommt aus derselben Quelle wie die
     GUI (auswertung.kernzeile) - nicht aus einer zweiten Formel.
  2. Ohne Ausstiege nennt sie die Datenlage, nicht eine Null-Bilanz: "0,00 USD"
     liest sich wie ein Ergebnis, obwohl noch nichts gemessen ist.
  3. Der Bericht schreibt nichts.

Nachsehen statt glauben:
    python tests/test_tagesbericht_omniquant.py --zeigen
"""

import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

HIER = os.path.dirname(os.path.abspath(__file__))
HANDEL = os.path.dirname(HIER)
OMNI = os.path.join(HANDEL, "omniquant")
for p in (HANDEL, OMNI):
    if p not in sys.path:
        sys.path.insert(0, p)

import tagesbericht                                        # noqa: E402

WACHEN_DATEI = os.path.join(OMNI, "wachen.json")

SPALTEN = ["zeit", "modus", "aktion", "inst", "seite", "preis",
           "einsatz_usd", "wert_usd", "stop", "ziel", "grund",
           "score", "cr", "mfe_pct", "mae_pct", "haltetage"]


def _ausstieg(inst, einsatz, wert, grund="ziel"):
    return {"zeit": "2026-09-13T10:00:00+00:00", "modus": "papier",
            "aktion": "AUSSTIEG", "inst": inst, "seite": "long",
            "preis": "100", "einsatz_usd": str(einsatz), "wert_usd": str(wert),
            "stop": "95", "ziel": "110", "grund": grund, "score": "67.0",
            "cr": "2.0", "mfe_pct": "1.0", "mae_pct": "-2.0", "haltetage": "3"}


def _schreibe(pfad, inhalt):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with io.open(pfad, "w", encoding="utf-8", newline="") as f:
        if isinstance(inhalt, str):
            f.write(inhalt)
        else:
            json.dump(inhalt, f, ensure_ascii=False)


def datenordner(ausstiege=()):
    """Ein Ordner, wie ihn der Bericht erwartet - nur der Omniquant-Teil.

    wachen.json wird aus der echten Spur kopiert: ein erfundener Rest liesse
    den Bericht etwas anderes zeigen als das, was Max aufs Handy bekommt.
    """
    t = tempfile.mkdtemp(prefix="bericht-omni-")
    with io.open(WACHEN_DATEI, encoding="utf-8", newline="") as f:
        _schreibe(os.path.join(t, "omniquant", "wachen.json"), f.read())
    _schreibe(os.path.join(t, "omniquant", "zustand.json"),
              {"modus": "papier", "letzter_lauf": "2026-09-13T10:00:00+00:00",
               "positionen": [], "erledigt": [], "verluste_usd": 0.0})
    p = os.path.join(t, "omniquant", "handelsjournal.csv")
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN)
        w.writeheader()
        for a in ausstiege:
            w.writerow(a)
    # Der Bericht laedt <spur>/auswertung.py ueber den Dateipfad (die Spuren
    # haben gleichnamige Module). Ohne die Datei im temp-Ordner stuende dort
    # "Auswertung nicht lesbar" - der Test wuerde die Verdrahtung also nicht
    # mehr pruefen.
    shutil.copy(os.path.join(OMNI, "auswertung.py"),
                os.path.join(t, "omniquant", "auswertung.py"))
    return t


def bericht(ausstiege=()):
    t = datenordner(ausstiege)
    with patch.object(tagesbericht, "HIER", t):
        text = tagesbericht.baue(mit_xperp=False)
    return t, text


def omniquant_block(ausstiege=()):
    """Der Omniquant-Block, unabhaengig vom Rang gebaut.

    Seit der Vorrangregel (Aufgabe 4) landet eine Spur ohne offene Position
    und ohne Unterschied zu gestern in der Sammelzeile, nicht mehr als
    voller Block im Bericht - das ist hier so gewollt (Omniquant faehrt
    papier, keine Position offen). Die Bilanzzeile selbst kommt weiterhin
    aus _block(), das die Vorrangregel absichtlich als eigene, unabhaengig
    testbare Funktion ausweist. Der Weg zur Erhebung spiegelt baue()s
    eigene HIER-Bindung (tagesbericht.HIER -> lage.HIER).
    """
    t = datenordner(ausstiege)
    with patch.object(tagesbericht, "HIER", t), \
            patch.object(tagesbericht.lage, "HIER", t):
        erhebung = tagesbericht.lage.erhebe(mit_xperp=False)
        for e in erhebung:
            if e["name"].startswith("Omniquant"):
                return tagesbericht._block(e, {})
    raise AssertionError("omniquant nicht in der Erhebung gefunden")


def bestand(ordner):
    aus = {}
    for wurzel, _, dateien in os.walk(ordner):
        for name in sorted(dateien):
            p = os.path.join(wurzel, name)
            s = os.stat(p)
            aus[os.path.relpath(p, ordner)] = (s.st_size, s.st_mtime_ns)
    return aus


class BilanzImBericht(unittest.TestCase):

    def test_ohne_ausstiege_steht_die_datenlage_da(self):
        block = omniquant_block([])
        self.assertIn("Auswertung: noch kein Ausstieg", block)
        # Nicht als Ergebnis verkleiden: keine Bilanz in USD.
        self.assertNotIn("Auswertung: 0 Ausstiege", block)

    def test_mit_ausstiegen_steht_die_bilanz_da(self):
        block = omniquant_block([_ausstieg("BTC-USDC", 50, 55),
                                 _ausstieg("ETH-USDC", 50, 45, grund="stop")])
        self.assertIn("2 Ausstiege", block)
        self.assertIn("nach Kosten", block)
        self.assertIn("Treffer 1/2", block)

    def test_bericht_schreibt_nichts(self):
        t = datenordner([_ausstieg("BTC-USDC", 50, 55)])
        vorher = bestand(t)
        with patch.object(tagesbericht, "HIER", t):
            tagesbericht.baue(mit_xperp=False)
        self.assertEqual(vorher, bestand(t),
                         "Der Bericht darf keine Datei anfassen")

    def test_fehlendes_journal_kippt_den_block_nicht(self):
        t = datenordner([])
        os.remove(os.path.join(t, "omniquant", "handelsjournal.csv"))
        with patch.object(tagesbericht, "HIER", t), \
                patch.object(tagesbericht.lage, "HIER", t):
            erhebung = tagesbericht.lage.erhebe(mit_xperp=False)
        e = next(e for e in erhebung if e["name"].startswith("Omniquant"))
        block = tagesbericht._block(e, {})
        self.assertIn("Omniquant", block)
        self.assertIn("Auswertung", block)


def zeige():
    t, text = bericht([_ausstieg("BTC-USDC", 50, 55),
                       _ausstieg("SOL-USDC", 50, 46, grund="stop")])
    print(text.replace("<b>", "").replace("</b>", ""))


if __name__ == "__main__":
    if "--zeigen" in sys.argv:
        zeige()
    else:
        unittest.main()
