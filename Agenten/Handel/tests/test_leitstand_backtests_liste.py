"""Die Liste der Einzelskripte haelt ihre Aufnahmebedingung - bei jedem Lauf.

  * jedes Skript existiert, jedes Flag steht in dessen add_argument (AST),
  * kein gesperrtes Flag (--json, --cache, --lokal),
  * optimieren.py und backtest_urteile.py stehen nicht drin,
  * keine Datei aus 'schreibt' wird im Betrieb gelesen: ihre Kennung kommt
    in dauerlauf.py, in keinem handeln.py/bot.py und in keiner Spur vor
    (ausser im gelisteten Skript selbst),
  * kein Skript enthaelt einen Order-Aufruf oder einen Schluessel.

Liest nur Quelltext. Direkt ausfuehrbar:  python tests/test_leitstand_backtests_liste.py
"""

import ast
import json
import re
import sys
import unittest
from pathlib import Path

HANDEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HANDEL))

import dauerlauf                                               # noqa: E402
import leitstand_backtests as lbt                              # noqa: E402

ORDER = re.compile(r"create_order|place_order|order_aufgeben|\.order\(|api_key|"
                   r"secret|private_key|ccxt\.\w+\(\{")


def _eintraege():
    return json.loads(lbt.LISTE.read_text(encoding="utf-8"))["eintraege"]


def _flags(skript):
    baum = ast.parse((HANDEL / skript).read_text(encoding="utf-8"))
    aus = set()
    for k in ast.walk(baum):
        if (isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute)
                and k.func.attr == "add_argument"):
            aus |= {a.value for a in k.args
                    if isinstance(a, ast.Constant) and isinstance(a.value, str)}
    return aus


def _betriebsdateien(ausnahmen):
    dateien = {HANDEL / "dauerlauf.py", HANDEL / "bot.py"}
    dateien |= set(HANDEL.glob("*/handeln.py")) | set(HANDEL.glob("*/bot.py"))
    for info in dauerlauf.SPUREN.values():
        ordner = HANDEL / info.get("ordner", "")
        if ordner != HANDEL and ordner.is_dir():
            dateien |= set(ordner.glob("*.py"))
    return sorted(p for p in dateien
                  if p.is_file() and p.resolve() not in ausnahmen)


class Liste(unittest.TestCase):
    def test_jedes_skript_existiert(self):
        for e in _eintraege():
            self.assertTrue((HANDEL / e["skript"]).is_file(), e["skript"])

    def test_jedes_flag_steht_in_add_argument(self):
        for e in _eintraege():
            vorhanden = _flags(e["skript"])
            for f in e["felder"]:
                self.assertIn(f["flag"], vorhanden, "%s: %s" % (e["skript"], f["flag"]))

    def test_keine_gesperrten_flags(self):
        for e in _eintraege():
            for f in e["felder"]:
                self.assertNotIn(f["flag"], lbt.VERBOTENE_FLAGS, e["name"])

    def test_eigene_bereiche_stehen_nicht_drin(self):
        namen = {Path(e["skript"]).name for e in _eintraege()}
        self.assertFalse(namen & {"optimieren.py", "backtest_urteile.py"})

    def test_schreibt_wird_im_betrieb_nicht_gelesen(self):
        eintraege = _eintraege()
        ausnahmen = {(HANDEL / e["skript"]).resolve() for e in eintraege}
        dateien = _betriebsdateien(ausnahmen)
        self.assertIn(HANDEL / "dauerlauf.py", dateien)
        for e in eintraege:
            for s in e["schreibt"]:
                for p in dateien:
                    text = p.read_text(encoding="utf-8", errors="replace")
                    self.assertNotIn(s["kennung"], text,
                                     "%s liest %s" % (p.relative_to(HANDEL), s["muster"]))

    def test_kein_order_aufruf_und_kein_schluessel(self):
        for e in _eintraege():
            text = (HANDEL / e["skript"]).read_text(encoding="utf-8")
            self.assertIsNone(ORDER.search(text), e["skript"])

    def test_die_liste_laedt_ohne_verworfene_eintraege(self):
        gut, fehler = lbt.lade_liste()
        self.assertEqual(fehler, "")
        self.assertEqual(len(gut), len(_eintraege()))


if __name__ == "__main__":
    unittest.main()
