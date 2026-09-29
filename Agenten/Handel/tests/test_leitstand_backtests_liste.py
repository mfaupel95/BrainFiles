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
import tempfile
import unittest
from pathlib import Path

HANDEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HANDEL))

import dauerlauf                                               # noqa: E402
import leitstand_backtests as lbt                              # noqa: E402

# Order-Funktionen der hauseigenen Clients (kraken, okx ...) und ihre Signatur
ORDER_NAMEN = ("order_limit", "markt_kauf", "markt_verkauf", "_add_order",
               "stop_setzen", "markt_schliessen", "hebel_setzen", "_roh_privat")
ORDER = re.compile(r"create_order|place_order|order_aufgeben|\.order\(|api_key|"
                   r"secret|private_key|ccxt\.\w+\(\{|signiert\s*=\s*True|"
                   + "|".join(ORDER_NAMEN))
_IMPORT = re.compile(r"^[ \t]*import[ \t]+([\w., \t]+)$", re.M)
_VON = re.compile(r"^[ \t]*from[ \t]+(\w+)[ \t]+import[ \t]+([\w, \t()]+)", re.M)


def import_funde(text, suchordner):
    """Order-Funktionen, die das Skript aus eigenen Modulen (Handel-Ordner oder
    Skriptordner) aufruft oder importiert: 'modul.markt_kauf(' bzw.
    'from modul import markt_kauf'. Dass das Modul sie definiert, ist kein Fund."""
    def eigen(modul):
        return any((Path(o) / (modul + ".py")).is_file() for o in suchordner)

    funde = []
    namen = "|".join(ORDER_NAMEN)
    for zeile in _IMPORT.findall(text):
        for teil in zeile.split(","):
            wort = teil.split()
            if not wort or not eigen(wort[0]):
                continue
            alias = wort[2] if len(wort) == 3 and wort[1] == "as" else wort[0]
            for m in re.finditer(r"\b%s\.(%s)\(" % (re.escape(alias), namen), text):
                funde.append("%s.%s(" % (alias, m.group(1)))
    for modul, liste in _VON.findall(text):
        if eigen(modul):
            for n in re.findall(r"\w+", liste):
                if n in ORDER_NAMEN:
                    funde.append("from %s import %s" % (modul, n))
    return funde


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

    def test_skripte_rufen_keine_order_funktion_aus_eigenen_modulen(self):
        for e in _eintraege():
            skript = HANDEL / e["skript"]
            text = skript.read_text(encoding="utf-8")
            self.assertEqual(import_funde(text, [HANDEL, skript.parent]), [],
                             e["skript"])

    def test_die_liste_laedt_ohne_verworfene_eintraege(self):
        gut, fehler = lbt.lade_liste()
        self.assertEqual(fehler, "")
        self.assertEqual(len(gut), len(_eintraege()))


class Schutz(unittest.TestCase):
    """Der Schutz selbst schlaegt an, wenn ein Skript kaufen wuerde."""

    def test_order_muster_kennt_die_hauseigenen_namen(self):
        for text in ("kraken.markt_kauf(x)", "order_limit(a)", "x._add_order(",
                     "stop_setzen(", "markt_verkauf(", "markt_schliessen(",
                     "hebel_setzen(", "_roh_privat(", "f(signiert=True)",
                     "f(signiert = True)"):
            self.assertIsNotNone(ORDER.search(text), text)
        self.assertIsNone(ORDER.search("kraken.kurs(x)\nsigniert=False"))

    def test_import_funde_in_temp_kopie(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "kraken.py").write_text("def markt_kauf(): pass\n",
                                                 encoding="utf-8")
            wo = [tmp]
            self.assertEqual(import_funde("import kraken\nkraken.markt_kauf(1)", wo),
                             ["kraken.markt_kauf("])
            self.assertEqual(import_funde("import kraken as k\nk.markt_kauf(1)", wo),
                             ["k.markt_kauf("])
            self.assertEqual(import_funde("from kraken import markt_kauf", wo),
                             ["from kraken import markt_kauf"])
            self.assertEqual(import_funde("import kraken\nkraken.kurs()", wo), [])
            self.assertEqual(import_funde("import fremd\nfremd.markt_kauf(1)", wo), [])


if __name__ == "__main__":
    unittest.main()
