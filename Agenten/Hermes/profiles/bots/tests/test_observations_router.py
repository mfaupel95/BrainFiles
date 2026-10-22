"""Tests fuer den Observations-Router (serieller Beobachtungs-Handoff).

Synthetische Markdown-Beobachtungen in einem Temp-Ordner, hermes-Subprozesse
VOLLSTAENDIG gemockt (kein echter A2A-/LLM-Aufruf, kein echter hermes.exe-Lauf).

Geprueft wird die REGEL, nicht eine Namensliste:
  - dry-run ist der Default und startet nichts,
  - --dispatch verarbeitet HOECHSTENS EINE offene Beobachtung,
  - idempotent ueber stabile Observation-ID/Statefile,
  - Observation wird als untrusted data gelesen (kaputtes Frontmatter = skip),
  - target_profile muss eindeutig, allowlist-valide und auf der Platte sein,
  - genau EIN Recherche-Aufruf, danach hoechstens EIN Fachbot,
  - keine Selbstverstaerkung: `bots` selbst ist nicht in der Allowlist.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BOTS = Path(__file__).resolve().parent
sys.path.insert(0, str(BOTS))
import observations_router as r                                   # noqa: E402


def _obs(datei, **fm):
    """Eine synthetische Beobachtung schreiben (YAML-Frontmatter + Body)."""
    zeilen = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            zeilen.append("%s: [%s]" % (k, ", ".join(v)))
        else:
            zeilen.append("%s: %s" % (k, v))
    zeilen.append("---")
    zeilen.append("")
    zeilen.append("Beobachtungstext.")
    datei.write_text("\n".join(zeilen), encoding="utf-8")


class RouterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.obs_root = Path(self.tmp.name) / "observation-log"
        self.obs_root.mkdir()
        self.state = Path(self.tmp.name) / "state.json"
        # Pfade auf die Temp-Fixture lenken.
        self.p_obs = patch.object(r, "OBS_ROOT", self.obs_root)
        self.p_state = patch.object(r, "STATE_PFAD", self.state)
        self.p_obs.start()
        self.p_state.start()
        self.addCleanup(self.p_obs.stop)
        self.addCleanup(self.p_state.stop)
        self.addCleanup(self.tmp.cleanup)

    def _rufe(self, name, text, frist=1800):
        """Mock: zeichnet den Aufruf auf, antwortet ohne echten Prozess."""
        self.aufrufe.append((name, text))
        return "Antwort von %s" % name

    def _start(self, dispatch):
        self.aufrufe = []
        self.p_rufe = patch.object(r, "_rufe_bot", side_effect=self._rufe)
        self.p_rufe.start()
        self.addCleanup(self.p_rufe.stop)
        return r._verarbeite_eine(self.obs_root, dispatch)


class TrockenlaufTest(RouterTest):
    def test_dry_run_startet_nichts(self):
        _obs(self.obs_root / "0001-test.md", id=1, status="open",
             target_profile="jev-trader")
        obs_id, ergebnis, fehler = self._start(dispatch=False)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        self.assertIn("dry-run", ergebnis)
        self.assertEqual(self.aufrufe, [], "dry-run darf keinen Bot starten")

    def test_dry_run_ist_default(self):
        _obs(self.obs_root / "0001-test.md", id=1, status="open",
             target_profile="jev-trader")
        with patch.object(r, "_rufe_bot", side_effect=self._rufe) as m:
            self.aufrufe = []
            rc = r.main(["--dry-run"])
        self.assertEqual(rc, 0)
        m.assert_not_called()


class DispatchTest(RouterTest):
    def test_dispatch_verarbeitet_genau_eine(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open",
             target_profile="jev-trader")
        _obs(self.obs_root / "0002-b.md", id=2, status="open",
             target_profile="obsidian-skills")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        # Genau EIN Recherche-Aufruf + genau EIN Fachbot.
        namen = [n for n, _ in self.aufrufe]
        self.assertEqual(namen, ["recherche", "jev-trader"])
        self.assertEqual(ergebnis["ziel"], "jev-trader")

    def test_idempotent_ueber_statefile(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open",
             target_profile="jev-trader")
        obs_id, _, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        # Zweiter Lauf: dieselbe Beobachtung wird NICHT erneut verarbeitet.
        obs_id2, ergebnis2, fehler2 = self._start(dispatch=True)
        self.assertIsNone(obs_id2, "bereits verarbeitete Beobachtung darf nicht erneut laufen")
        self.assertIsNone(ergebnis2)
        self.assertIsNone(fehler2)

    def test_zweite_beobachtung_nach_erster(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open",
             target_profile="jev-trader")
        _obs(self.obs_root / "0002-b.md", id=2, status="open",
             target_profile="obsidian-skills")
        self._start(dispatch=True)
        # Zweiter Lauf nimmt die naechste offene Beobachtung.
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "2")
        self.assertIsNone(fehler)
        self.assertEqual(ergebnis["ziel"], "obsidian-skills")


class RoutingTest(RouterTest):
    def test_kein_target_profile_kein_bot(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(ergebnis)
        self.assertIn("kein target_profile", fehler)
        self.assertEqual(self.aufrufe, [], "ohne Ziel darf kein Bot starten")

    def test_target_profile_nicht_in_allowlist(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open",
             target_profile="nicht-existenter-bot")
        obs_id, _, fehler = self._start(dispatch=True)
        self.assertIn("nicht in der Allowlist", fehler)
        self.assertEqual(self.aufrufe, [])

    def test_keine_selbstverstaerkung(self):
        # `bots` (der Interpool selbst) ist nicht in der Allowlist.
        self.assertNotIn("bots", r.ALLOWLIST)
        _obs(self.obs_root / "0001-a.md", id=1, status="open",
             target_profile="bots")
        obs_id, _, fehler = self._start(dispatch=True)
        self.assertIn("nicht in der Allowlist", fehler)
        self.assertEqual(self.aufrufe, [])

    def test_parked_wird_nicht_verarbeitet(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="parked",
             parked_until="X ist reaktiviert", target_profile="jev-trader")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertIsNone(obs_id)
        self.assertIsNone(ergebnis)
        self.assertIsNone(fehler)
        self.assertEqual(self.aufrufe, [])

    def test_status_fehlt_ist_open(self):
        _obs(self.obs_root / "0001-a.md", id=1, target_profile="jev-trader")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        self.assertEqual(ergebnis["ziel"], "jev-trader")


class UntrustedTest(RouterTest):
    def test_kaputtes_frontmatter_wird_uebersprungen(self):
        (self.obs_root / "0001-a.md").write_text(
            "kein frontmatter hier\nnur text\n", encoding="utf-8")
        _obs(self.obs_root / "0002-b.md", id=2, status="open",
             target_profile="jev-trader")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        # Die kaputte Datei wird uebersprungen, die naechste verarbeitet.
        self.assertEqual(obs_id, "2")
        self.assertIsNone(fehler)
        self.assertEqual(ergebnis["ziel"], "jev-trader")

    def test_ungueltiges_yaml_wird_uebersprungen(self):
        (self.obs_root / "0001-a.md").write_text(
            "---\nstatus: [unterminiert\n---\n", encoding="utf-8")
        _obs(self.obs_root / "0002-b.md", id=2, status="open",
             target_profile="jev-trader")
        obs_id, _, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "2")
        self.assertIsNone(fehler)

    def test_kein_verzeichnis_kein_crash(self):
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertIsNone(obs_id)
        self.assertIsNone(ergebnis)
        self.assertIsNone(fehler)


class StateTest(RouterTest):
    def test_statefile_wird_geschrieben(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open",
             target_profile="jev-trader")
        self._start(dispatch=True)
        self.assertTrue(self.state.exists())
        data = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertIn("verarbeitet", data)
        self.assertIn("1", data["verarbeitet"])


if __name__ == "__main__":
    unittest.main()
