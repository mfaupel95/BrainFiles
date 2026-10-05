"""Tests fuer routing_plan_pruefen.

Regel: ein Pruefer, der immer gruen sagt, ist wertlos (Hausregel T-322). Jeder
Test baut deshalb TASKS.md und einen Plan selbst und prueft eine EIGENE
Eigenschaft - keine gespeicherten Zahlen des echten Hauses.
"""

import importlib.util
import pathlib
import sys
import unittest

WERKZEUG = pathlib.Path(__file__).resolve().parents[1] / "routing_plan_pruefen.py"
spez = importlib.util.spec_from_file_location("routing_plan_pruefen", WERKZEUG)
rp = importlib.util.module_from_spec(spez)
sys.modules["routing_plan_pruefen"] = rp
spez.loader.exec_module(rp)

KOPF_A = "\u2014"   # Geviertstrich
KOPF_B = "-"        # ASCII-Bindestrich


def tasks_md(*eintraege):
    teile = ["# TASKS.md", "", "## Eintragsformat", "", "Beispiel.", "", "## Offen"]
    for zeichen, tid, titel in eintraege:
        teile += [f"- [{zeichen}] **{tid} {KOPF_A} {titel}**",
                  "      Kontext: kurz", "      Naechster Schritt: tun"]
    teile += ["", "## Erledigt", "", "- [x] **T-900 \u2014 alt**", "      Erledigt."]
    return "\r\n".join(teile) + "\r\n"


def plan_md(*zeilen):
    kopf = ("| # | Titel | Quelle | Definition of Done | Blocker | Aufwand "
            "| Profil | Begruendung |")
    trenner = "|---|---|---|---|---|---|---|---|"
    return ("# Routing-Plan\n\n## (b) Inventar\n\n" + kopf + "\n" + trenner + "\n"
            + "\n".join(zeilen) + "\n")


def tmpdatei(inhalt):
    import tempfile
    d = tempfile.mkdtemp(prefix="routing_plan_")
    p = pathlib.Path(d) / "dummy"
    p.write_text(inhalt, encoding="utf-8", newline="")
    return d


def planzeile(nr, tid, titel):
    return (f"| {nr} | {titel} ({tid}) | Zeile 10 | {titel} erledigt | keine | M "
            f"| `default` | passt |")


class TestOffeneEintraege(unittest.TestCase):
    def test_drei_zeichenarten_zaehlen_als_offen(self):
        """Nur - [x] ist fertig; [?] (wartet auf Max) und [!] (blockiert) sind offen."""
        mit = pathlib.Path(tmpdatei(tasks_md(
            (" ", "T-001", "a"), ("x", "T-002", "b"),
            ("?", "T-003", "c"), ("!", "T-004", "d")))) / "TASKS.md"
        mit.write_text(tasks_md((" ", "T-001", "a"), ("x", "T-002", "b"),
                                ("?", "T-003", "c"), ("!", "T-004", "d")),
                       encoding="utf-8", newline="")
        erg = rp.offene_eintraege(mit)
        offen = {k for k, v in erg.items() if v["zeichen"] != "x"}
        self.assertEqual(offen, {"T-001", "T-003", "T-004"})
        self.assertEqual(len(erg), 4)

    def test_beide_schreibweisen_werden_gelesen(self):
        pfad = pathlib.Path(tmpdatei("x")) / "TASKS.md"
        inhalt = tasks_md((" ", "T-001", "a")).replace(
            f"T-001 {KOPF_A}", f"T-002 -")
        pfad.write_text(inhalt, encoding="utf-8", newline="")
        erg = rp.offene_eintraege(pfad)
        # BEIDE Formen muessen als getrennte Eintraege erkannt werden, nicht
        # als zwei Schreibweisen DESSELBEN Punktes.
        pfad2 = pathlib.Path(tmpdatei("x")) / "TASKS.md"
        pfad2.write_text(tasks_md((" ", "T-001", "a"), (" ", "T-002", "b")),
                        encoding="utf-8", newline="")
        erg2 = rp.offene_eintraege(pfad2)
        self.assertEqual(set(erg), {"T-002"}, "Typ B wurde nicht erkannt")
        self.assertEqual({v["typ"] for v in erg.values()},
                         {rp.KOPF_B.pattern})
        self.assertEqual(set(erg2), {"T-001", "T-002"})
        self.assertEqual({v["typ"] for v in erg2.values()},
                         {rp.KOPF_A.pattern})

    def test_erledigt_abschnitt_gehoert_nicht_dazu(self):
        pfad = pathlib.Path(tmpdatei("x")) / "TASKS.md"
        pfad.write_text(tasks_md((" ", "T-001", "a")), encoding="utf-8", newline="")
        erg = rp.offene_eintraege(pfad)
        self.assertNotIn("T-900", erg)


class TestPlanGegenTasks(unittest.TestCase):
    def _lege(self, eintraege, zeilen):
        t = pathlib.Path(tmpdatei(tasks_md(*eintraege))) / "TASKS.md"
        t.write_text(tasks_md(*eintraege), encoding="utf-8", newline="")
        p = pathlib.Path(tmpdatei(plan_md(*zeilen))) / "PLAN.md"
        p.write_text(plan_md(*zeilen), encoding="utf-8", newline="")
        return t, p

    def test_vollstaendiger_plan_ist_gruen(self):
        t, p = self._lege([(" ", "T-001", "a"), (" ", "T-002", "b")],
                          [planzeile(1, "T-001", "a"), planzeile(2, "T-002", "b")])
        e = rp.pruefe(t, p)
        self.assertTrue(e["ok"], e["befunde"])
        self.assertEqual(e["fehlend"], [])

    def test_fehlender_punkt_wird_gemeldet(self):
        t, p = self._lege([(" ", "T-001", "a"), (" ", "T-002", "b")],
                          [planzeile(1, "T-001", "a")])
        e = rp.pruefe(t, p)
        self.assertFalse(e["ok"])
        self.assertEqual(e["fehlend"], ["T-002"])

    def test_gegenprobe_abschneiden_zeigt_mehr_fehlende(self):
        eintraege = [(" ", "T-001", "a"), (" ", "T-002", "b"), (" ", "T-003", "c")]
        zeilen = [planzeile(i, t, x) for i, (t, x) in
                  enumerate([("T-001", "a"), ("T-002", "b"), ("T-003", "c")], 1)]
        t, p = self._lege(eintraege, zeilen)
        voll = rp.pruefe(t, p)
        kaputt = rp.pruefe(t, p, abschneiden=2)
        self.assertEqual(len(kaputt["fehlend"]), len(voll["fehlend"]) + 2)

    def test_doppelte_tid_wird_gemeldet(self):
        t, p = self._lege([(" ", "T-001", "a"), (" ", "T-002", "b")],
                          [planzeile(1, "T-001", "a"), planzeile(2, "T-001", "a")])
        e = rp.pruefe(t, p)
        self.assertEqual(e["doppelt"], ["T-001"])
        self.assertFalse(e["ok"])

    def test_planzeile_ohne_offenen_punkt_wird_gemeldet(self):
        t, p = self._lege([(" ", "T-001", "a")],
                          [planzeile(1, "T-001", "a"), planzeile(2, "T-777", "tot")])
        e = rp.pruefe(t, p)
        self.assertEqual(e["ueberzaehlig"], ["T-777"])
        self.assertFalse(e["ok"])

    def test_leeres_feld_wird_gemeldet(self):
        zeile = ("| 1 | a (T-001) | Zeile 10 | erledigt | keine | M |  | passt |")
        t, p = self._lege([(" ", "T-001", "a")], [zeile])
        e = rp.pruefe(t, p)
        self.assertEqual(list(e["leere_felder"]), ["profil"])
        self.assertFalse(e["ok"])

    def test_keine_eintraege_ist_kein_fehler(self):
        t, p = self._lege([], [])
        e = rp.pruefe(t, p)
        self.assertTrue(e["ok"], "leerer Plan bei leerem Backlog ist gueltig")
        self.assertEqual(e["offen"], 0)
        self.assertEqual(e["planzeilen"], 0)

    def _tmp(self, inhalt):
        import tempfile
        d = tempfile.mkdtemp(prefix="routing_plan_")
        p = pathlib.Path(d) / "dummy"
        p.write_text(inhalt, encoding="utf-8", newline="")
        return d


if __name__ == "__main__":
    unittest.main()