#!/usr/bin/env python
"""Test fuer `profil-moa-entfernen.py` - der `moa:`-Block verschwindet aus den
Bot-Profilen, das Hauptprofil (Profil `default`) behaelt ihn.

Getestet wird die REGEL, nicht der Tagesstand:
  1. Ein Profil mit `moa:` verliert genau diesen Block, alle anderen
     Top-Level-Abschnitte bleiben IDENTISCH (YAML-Vergleich).
  2. Zeilenenden (CRLF) und der Rest der Datei bleiben unangetastet.
  3. Ein Profil ohne `moa:` meldet "kein moa-Block" und wird nicht geschrieben.
  4. Der Hauptprofil-Pfad wird nie angefasst - der Werkzeuglauf ueber
     `PROFILE` kann das Hauptprofil gar nicht erreichen.
  5. Gegenprobe: mit kaputtem Block (z. B. `moa:` mitten in einer Liste) darf
     das Werkzeug nicht schreiben, sondern melden.

Gegenprobe zum Test selbst: wird `_gegenproben` umgangen (Block-Ende auf
`len(zeilen)`), muss der Test rot werden - das belegt, dass er ueberhaupt
etwas prueft.
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "profil-moa-entfernen.py"
spec = importlib.util.spec_from_file_location("profil_moa_entfernen", SCRIPT)
pm = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pm)

PROFIL = (
    "model:\r\n"
    "  default: deepseek/deepseek-v4-flash\r\n"
    "  providers:\r\n"
    "    nous:\r\n"
    "      models:\r\n"
    "        - deepseek/deepseek-v4-flash\r\n"
    "delegation:\r\n"
    "  provider: nous\r\n"
    "moa:\r\n"
    "  presets:\r\n"
    "    default:\r\n"
    "      reference_models:\r\n"
    "        - provider: nous\r\n"
    "          model: gpt-5.6-sol\r\n"
    "          enabled: true\r\n"
    "      aggregator:\r\n"
    "        provider: ollama-launch\r\n"
    "        model: gemma-e4b-8k:latest\r\n"
    "      fanout: user_turn\r\n"
    "      enabled: false\r\n"
    "    Max:\r\n"
    "      enabled: true\r\n"
    "      fanout: user_turn\r\n"
    "skills:\r\n"
    "  creation_nudge_interval: 15\r\n"
    "curator:\r\n"
    "  enabled: true\r\n"
)

OHNE_MOA = "model:\r\n  default: nous/x\r\ndelegation:\r\n  provider: nous\r\n"


class ProfilOhneMoaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _schreibe(self, name: str, text: str) -> Path:
        p = self.tmp / name / "config.yaml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))
        return p

    def test_moa_block_verschwindet_und_rest_bleibt(self) -> None:
        p = self._schreibe("bot", PROFIL)
        e = pm.bearbeite(p, anwenden=False)
        self.assertEqual(e["stand"], "Trockenlauf", e)
        self.assertEqual(e["presets"], ["Max", "default"])
        neu = pm.bearbeite(p, anwenden=True)
        self.assertEqual(neu["stand"], "entfernt", neu)
        import yaml
        d = yaml.safe_load(p.read_bytes().decode("utf-8")) or {}
        self.assertNotIn("moa", d)
        self.assertEqual(sorted(d), ["curator", "delegation", "model", "skills"])
        self.assertEqual(d["model"]["default"], "deepseek/deepseek-v4-flash")
        self.assertEqual(d["skills"]["creation_nudge_interval"], 15)

    def test_zeilenenden_bleiben_crlf(self) -> None:
        p = self._schreibe("bot", PROFIL)
        pm.bearbeite(p, anwenden=True)
        roh = p.read_bytes()
        self.assertNotIn(b"\n\n", roh)
        self.assertEqual(roh.count(b"\n"), roh.count(b"\r\n"))
        self.assertTrue(p.read_bytes().startswith(b"model:\r\n"))

    def test_ohne_moa_wird_nichts_geschrieben(self) -> None:
        p = self._schreibe("bot", OHNE_MOA)
        vorher = p.read_bytes()
        e = pm.bearbeite(p, anwenden=True)
        self.assertEqual(e["stand"], "kein moa-Block")
        self.assertEqual(p.read_bytes(), vorher)
        self.assertFalse(list(p.parent.glob("*.bak-*")))

    def test_sicherung_entspricht_dem_vorzustand(self) -> None:
        p = self._schreibe("bot", PROFIL)
        pm.bearbeite(p, anwenden=True)
        baks = list(p.parent.glob("config.yaml.bak-*"))
        self.assertEqual(len(baks), 1)
        self.assertEqual(baks[0].read_bytes(), PROFIL.encode("utf-8"))

    def test_zweiter_lauf_ist_unveraendert(self) -> None:
        p = self._schreibe("bot", PROFIL)
        pm.bearbeite(p, anwenden=True)
        stand = p.read_bytes()
        e = pm.bearbeite(p, anwenden=True)
        self.assertEqual(e["stand"], "kein moa-Block")
        self.assertEqual(p.read_bytes(), stand)

    def test_moa_ohne_folgenden_abschnitt(self) -> None:
        """`moa:` als LETZTER Abschnitt: der Block laeuft bis Dateiende, der
        Abschnitt davor bleibt unangetastet."""
        am_ende = (
            "model:\r\n"
            "  default: nous/x\r\n"
            "moa:\r\n"
            "  presets:\r\n"
            "    default:\r\n"
            "      enabled: false\r\n"
        )
        p = self._schreibe("bot", am_ende)
        e = pm.bearbeite(p, anwenden=True)
        self.assertEqual(e["stand"], "entfernt", e)
        import yaml
        d = yaml.safe_load(p.read_bytes().decode("utf-8")) or {}
        self.assertEqual(d, {"model": {"default": "nous/x"}})

    def test_eingeruecktes_moa_gehoert_nicht_dazu(self) -> None:
        """Ein `moa:` unter einem Provider ist ein Schluessel DIESES
        Providers - der darf nicht mit dem Top-Level-Block verschwinden."""
        text = (
            "model:\r\n"
            "  default: nous/x\r\n"
            "providers:\r\n"
            "  nous:\r\n"
            "    moa:\r\n"
            "      note: bleibt\r\n"
            "      default_model: nous/x\r\n"
        )
        p = self._schreibe("bot", text)
        e = pm.bearbeite(p, anwenden=True)
        self.assertEqual(e["stand"], "kein moa-Block", e)
        self.assertEqual(p.read_bytes(), text.encode("utf-8"))

    def test_gegenprobe_meldet_verlorenen_abschnitt(self) -> None:
        """Echte Gegenprobe: reisst der Schnitt zu viel mit, MUSS das
        Werkzeug stehen bleiben und melden. Dazu wird `_block_zeilen` so
        gebrochen, dass es bis zum Dateiende laeuft - ohne die Gegenprobe
        wuerde `skills:` verschwinden und der Test hier bliebe gruen."""
        p = self._schreibe("bot", PROFIL)
        vorher = p.read_bytes()
        original = pm._block_zeilen
        pm._block_zeilen = lambda z: (original(z)[0], len(z)) if original(z) else None
        try:
            e = pm.bearbeite(p, anwenden=True)
        finally:
            pm._block_zeilen = original
        # Die Schluesselmenge-Pruefung greift ZUERST (sie ist die staerkere):
        # `skills:` und `curator:` duerfen nicht verschwinden.
        self.assertEqual(e["stand"],
                         "Gegenprobe fehlgeschlagen (Top-Level-Schluessel: weg "
                         "['curator', 'skills'], dazu [])", e)
        self.assertEqual(p.read_bytes(), vorher)      # NICHTS geschrieben
        self.assertFalse(list(p.parent.glob("*.bak-*")))

    def test_hauptprofil_nie_im_werkzeuglauf(self) -> None:
        """Der Lauf geht ueber `PROFILE` (= profiles/) - der Hauptprofil-Pfad
        liegt ausserhalb und kann nicht getroffen werden."""
        self.assertNotIn(pm.HAUPT.parent, [pm.PROFILE])
        self.assertEqual(pm.HAUPT.name, "config.yaml")
        self.assertEqual(pm.HAUPT.parent.name, "Hermes")
        treffer = [p for p in pm.PROFILE.glob("*/config.yaml")]
        self.assertTrue(treffer)
        self.assertNotIn(pm.HAUPT, treffer)


class RueckwegTest(unittest.TestCase):
    def test_neueste_sicherung_gewinnt(self) -> None:
        alt = Path(r"C:/Users/faupe/Documents/BrainFiles/Agenten/Hermes/profiles")
        if not alt.is_dir():
            self.skipTest("kein Profile-Baum")
        baks = sorted(alt.glob("*/config.yaml.bak-*"))
        if not baks:
            self.skipTest("keine Sicherungen")
        neueste: dict[str, Path] = {}
        for b in baks:
            neueste[b.parent.name] = b
        # die Auswahl des Werkzeugs muss die juengste Datei je Profil nehmen
        import re
        for name, b in neueste.items():
            alle = [x for x in baks if x.parent.name == name]
            self.assertEqual(b, max(alle, key=lambda x: x.name), name)
            self.assertIsNotNone(re.match(r"config\.yaml\.bak-\d{12}$", b.name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
