"""Ende-zu-Ende-Beleg: die Bilanzzeile einer Spur im FERTIGEN Bericht.

tests/test_tagesbericht_omniquant.py wurde auf tagesbericht._block(e, {})
umgestellt (Vorrangregel, Aufgabe 4: eine Spur ohne offene Position und ohne
Unterschied zu gestern faellt in die Sammelzeile, nicht mehr als voller Block
in den Bericht). Seitdem beweist dort kein Test mehr, dass die Bilanzzeile
tatsaechlich bis in tagesbericht.baue() durchkommt - _block() wird isoliert
aufgerufen, rang() und die Sammelzeile bleiben aussen vor. Dieser Test schliesst
genau diese Luecke: er ruft baue() auf, mit einer offenen Position (damit die
Spur sicher Rang 1 oder 2 hat und nicht in der Sammelzeile verschwindet), und
prueft am Volltext, dass die Bilanzzeile DIESER Spur - nicht irgendeine
Ausstiegszahl, die auch aus einer fremden Spur stammen koennte - im Bericht
steht.
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


def datenordner_mit_position(ausstiege):
    """Wie datenordner() in test_tagesbericht_omniquant.py, plus eine offene
    Position - damit rang() garantiert nicht 3 liefert (Rang 3 = Sammelzeile,
    dort geht die Bilanzzeile im Bericht wieder verloren).
    """
    t = tempfile.mkdtemp(prefix="bericht-ezb-")
    with io.open(WACHEN_DATEI, encoding="utf-8", newline="") as f:
        _schreibe(os.path.join(t, "omniquant", "wachen.json"), f.read())
    _schreibe(os.path.join(t, "omniquant", "zustand.json"),
              {"modus": "papier", "letzter_lauf": "2026-09-13T10:00:00+00:00",
               "positionen": [{"inst": "BTC-USDC", "seite": "long",
                               "einstieg": 100.0, "nominal": 50.0,
                               "stop": 95.0, "eroeffnet":
                               "2026-09-13T10:00:00+00:00"}],
               "erledigt": [], "verluste_usd": 0.0})
    p = os.path.join(t, "omniquant", "handelsjournal.csv")
    with io.open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SPALTEN)
        w.writeheader()
        for a in ausstiege:
            w.writerow(a)
    shutil.copy(os.path.join(OMNI, "auswertung.py"),
                os.path.join(t, "omniquant", "auswertung.py"))
    return t


class BilanzImFertigenBericht(unittest.TestCase):

    def test_baue_traegt_die_bilanzzeile_der_spur_im_volltext(self):
        t = datenordner_mit_position([_ausstieg("BTC-USDC", 50, 55),
                                      _ausstieg("ETH-USDC", 50, 45,
                                                grund="stop")])
        try:
            with patch.object(tagesbericht, "HIER", t), \
                    patch.object(tagesbericht.lage, "HIER", t):
                erwartete_bilanz = tagesbericht.lage.bilanz("omniquant")
                text = tagesbericht.baue(mit_xperp=False)
        finally:
            shutil.rmtree(t, ignore_errors=True)

        # rang() muss die Spur ins Bild geholt haben, nicht in die
        # Sammelzeile verbannt - sonst waere die Bilanzzeile unten geprueft,
        # obwohl sie im Bericht gar nicht mehr steht. Andere Spuren duerfen
        # in der Sammelzeile landen, Omniquant nicht.
        sammelzeile = next((z for z in text.splitlines()
                            if z.strip().endswith("still:")
                            or "Spuren still:" in z), "")
        # Die Still-Zeile darf den STRENGEN Arm nicht verschlucken - der
        # Schattenarm "omniquant weit" gehoert dort aber hin (er hat seit dem
        # letzten Bericht nichts Neues). Deshalb wird der Eintrag genau
        # verglichen und nicht als Teilwort: "omniquant weit (papier)" ist ein
        # anderer Eintrag als "omniquant (papier)". Ein fester Namensvergleich
        # haette hier gemeldet, dass sich etwas geaendert hat - nicht, dass
        # etwas falsch ist.
        eintraege = [e.strip().lower()
                     for e in sammelzeile.split(":", 1)[-1].split(",")]
        verschluckt = [e for e in eintraege
                       if e.startswith("omniquant (") or e == "omniquant"]
        self.assertFalse(verschluckt,
                         "der strenge Arm liegt in der Sammelzeile: %s" % eintraege)
        self.assertIn("<b>Omniquant (papier)</b>", text)

        # Spurgebunden statt Allerweltsfragment: dieselbe Bilanzzeile, wie sie
        # auch die GUI ueber lage.bilanz() bekaeme, muss WORTGLEICH im
        # zusammenhaengenden Omniquant-Block des fertigen Berichtstexts
        # stehen - nicht nur irgendwo im Text (dort koennte sie auch aus
        # einer anderen Spur mit zufaellig gleichen Zahlen stammen).
        self.assertIn("2 Ausstiege", erwartete_bilanz)
        block_anfang = text.index("<b>Omniquant (papier)</b>")
        block_ende = text.find("\n<b>", block_anfang + 1)
        if block_ende == -1:
            block_ende = len(text)
        omniquant_block = text[block_anfang:block_ende]
        self.assertIn(erwartete_bilanz, omniquant_block)


if __name__ == "__main__":
    unittest.main()
