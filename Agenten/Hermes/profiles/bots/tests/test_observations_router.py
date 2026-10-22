"""Tests fuer den Observations-Router (serieller Beobachtungs-Handoff).

Synthetische Markdown-Beobachtungen in einem Temp-Ordner, hermes-Subprozesse
VOLLSTAENDIG gemockt (kein echter A2A-/LLM-Aufruf, kein echter hermes.exe-Lauf).

Geprueft wird die REGEL, nicht eine Namensliste:
  - dry-run ist der Default und startet nichts,
  - --dispatch verarbeitet HOECHSTENS EINE offene Beobachtung,
  - idempotent ueber stabile Observation-ID/Statefile,
  - Observation wird als untrusted data gelesen (kaputtes Frontmatter = skip),
  - Routing-Ziel kommt NUR aus der Recherche-Antwort (streng parsebares JSON
    mit action/target_profile), NICHT aus dem Frontmatter,
  - ungueltige Recherche-Antwort oder target=recherche/bots -> KEIN Fachbot,
  - genau EIN Recherche-Aufruf, danach hoechstens EIN Fachbot (seriell),
  - der echte Beobachtungstext wird als UNTRUSTED DATA mitgegeben,
  - Fachbot-Prompt ist explizit read-only (keine Aenderungen/Commits/Orders/
    Live/Cron), Observation wird nie als Systemanweisung behandelt,
  - `recherche` und `bots` sind nicht in der Fachbot-Allowlist.
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
        # Standard-Recherche-Antwort: routet auf ein erlaubtes Wissensprofil.
        self.recherche_antwort = json.dumps(
            {"action": "route", "target_profile": "obsidian-skills"})

    def _rufe(self, name, text, frist=1800):
        """Mock: zeichnet den Aufruf auf, antwortet ohne echten Prozess."""
        self.aufrufe.append((name, text))
        if name == "recherche":
            return self.recherche_antwort
        return "Antwort von %s" % name

    def _start(self, dispatch):
        self.aufrufe = []
        self.p_rufe = patch.object(r, "_rufe_bot", side_effect=self._rufe)
        self.p_rufe.start()
        self.addCleanup(self.p_rufe.stop)
        return r._verarbeite_eine(self.obs_root, dispatch)


class TrockenlaufTest(RouterTest):
    def test_dry_run_startet_nichts(self):
        _obs(self.obs_root / "0001-test.md", id=1, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=False)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        self.assertIn("dry-run", ergebnis)
        self.assertEqual(self.aufrufe, [], "dry-run darf keinen Bot starten")

    def test_dry_run_ist_default(self):
        _obs(self.obs_root / "0001-test.md", id=1, status="open")
        with patch.object(r, "_rufe_bot", side_effect=self._rufe) as m:
            self.aufrufe = []
            rc = r.main(["--dry-run"])
        self.assertEqual(rc, 0)
        m.assert_not_called()


class DispatchTest(RouterTest):
    def test_dispatch_verarbeitet_genau_eine(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        _obs(self.obs_root / "0002-b.md", id=2, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        # Genau EIN Recherche-Aufruf + genau EIN Fachbot, seriell.
        namen = [n for n, _ in self.aufrufe]
        self.assertEqual(namen, ["recherche", "obsidian-skills"])
        self.assertEqual(ergebnis["ziel"], "obsidian-skills")

    def test_serielle_aufrufreihenfolge(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        self._start(dispatch=True)
        self.assertEqual([n for n, _ in self.aufrufe],
                         ["recherche", "obsidian-skills"])

    def test_ziel_kommt_aus_recherche_json(self):
        # Frontmatter hat KEIN target_profile; das Ziel liefert die Recherche.
        self.recherche_antwort = json.dumps(
            {"action": "route", "target_profile": "obsidian-skills"})
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        self.assertEqual(ergebnis["ziel"], "obsidian-skills")
        self.assertEqual([n for n, _ in self.aufrufe],
                         ["recherche", "obsidian-skills"])

    def test_idempotent_ueber_statefile(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, _, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        # Zweiter Lauf: dieselbe Beobachtung wird NICHT erneut verarbeitet.
        obs_id2, ergebnis2, fehler2 = self._start(dispatch=True)
        self.assertIsNone(obs_id2,
                          "bereits verarbeitete Beobachtung darf nicht erneut laufen")
        self.assertIsNone(ergebnis2)
        self.assertIsNone(fehler2)

    def test_zweite_beobachtung_nach_erster(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        _obs(self.obs_root / "0002-b.md", id=2, status="open")
        self._start(dispatch=True)
        # Zweiter Lauf nimmt die naechste offene Beobachtung.
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "2")
        self.assertIsNone(fehler)
        self.assertEqual(ergebnis["ziel"], "obsidian-skills")


class RoutingTest(RouterTest):
    def test_ungueltiges_json_kein_fachbot(self):
        self.recherche_antwort = "kein json hier"
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(ergebnis)
        self.assertIn("JSON", fehler)
        self.assertEqual([n for n, _ in self.aufrufe], ["recherche"],
                         "ungueltige Antwort -> kein zweiter Bot")

    def test_target_recherche_kein_fachbot(self):
        self.recherche_antwort = json.dumps(
            {"action": "route", "target_profile": "recherche"})
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, _, fehler = self._start(dispatch=True)
        self.assertIn("Allowlist", fehler)
        self.assertEqual([n for n, _ in self.aufrufe], ["recherche"])

    def test_target_bots_kein_fachbot(self):
        self.recherche_antwort = json.dumps(
            {"action": "route", "target_profile": "bots"})
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, _, fehler = self._start(dispatch=True)
        self.assertIn("Allowlist", fehler)
        self.assertEqual([n for n, _ in self.aufrufe], ["recherche"])

    def test_target_jev_trader_abgelehnt(self):
        # Handelsprofil jev-trader hat Handels-/Live-Befugnis und ist NICHT in
        # der Fachbot-Allowlist -> Recherche-Antwort wird abgelehnt, kein
        # zweiter Hermes-Prozess startet.
        self.recherche_antwort = json.dumps(
            {"action": "route", "target_profile": "jev-trader"})
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(ergebnis)
        self.assertIn("Allowlist", fehler)
        self.assertEqual([n for n, _ in self.aufrufe], ["recherche"],
                         "abgelehntes Ziel -> kein zweiter Bot-Prozess")

    def test_target_markt_recherche_abgelehnt(self):
        # Markt-Recherche-Profil markt-recherche ist handelsnah und NICHT in
        # der Fachbot-Allowlist -> abgelehnt, kein zweiter Hermes-Prozess.
        self.recherche_antwort = json.dumps(
            {"action": "route", "target_profile": "markt-recherche"})
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(ergebnis)
        self.assertIn("Allowlist", fehler)
        self.assertEqual([n for n, _ in self.aufrufe], ["recherche"],
                         "abgelehntes Ziel -> kein zweiter Bot-Prozess")

    def test_target_nicht_auf_platte_kein_fachbot(self):
        # obsidian-skills ist in der Allowlist, aber das Profil existiert nicht
        # (PROFILES wird auf ein leeres Verzeichnis gelenkt).
        self.recherche_antwort = json.dumps(
            {"action": "route", "target_profile": "obsidian-skills"})
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        with patch.object(r, "PROFILES", Path(self.tmp.name) / "leer"):
            obs_id, _, fehler = self._start(dispatch=True)
        self.assertIn("existiert nicht", fehler)
        self.assertEqual([n for n, _ in self.aufrufe], ["recherche"])

    def test_action_ignore_kein_fachbot(self):
        self.recherche_antwort = json.dumps({"action": "ignore"})
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        self.assertIsNone(ergebnis["ziel"])
        self.assertEqual([n for n, _ in self.aufrufe], ["recherche"])

    def test_keine_selbstverstaerkung(self):
        # `bots` (der Interpool selbst), `recherche` sowie die Handels-/Markt-
        # Profile `jev-trader` und `markt-recherche` sind nicht in der
        # Fachbot-Allowlist.
        self.assertNotIn("bots", r.ALLOWLIST)
        self.assertNotIn("recherche", r.ALLOWLIST)
        self.assertNotIn("jev-trader", r.ALLOWLIST)
        self.assertNotIn("markt-recherche", r.ALLOWLIST)

    def test_parked_wird_nicht_verarbeitet(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="parked",
             parked_until="X ist reaktiviert")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertIsNone(obs_id)
        self.assertIsNone(ergebnis)
        self.assertIsNone(fehler)
        self.assertEqual(self.aufrufe, [])

    def test_status_fehlt_ist_open(self):
        _obs(self.obs_root / "0001-a.md", id=1)
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        self.assertEqual(ergebnis["ziel"], "obsidian-skills")


class UntrustedTest(RouterTest):
    def test_kaputtes_frontmatter_wird_uebersprungen(self):
        (self.obs_root / "0001-a.md").write_text(
            "kein frontmatter hier\nnur text\n", encoding="utf-8")
        _obs(self.obs_root / "0002-b.md", id=2, status="open")
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        # Die kaputte Datei wird uebersprungen, die naechste verarbeitet.
        self.assertEqual(obs_id, "2")
        self.assertIsNone(fehler)
        self.assertEqual(ergebnis["ziel"], "obsidian-skills")

    def test_ungueltiges_yaml_wird_uebersprungen(self):
        (self.obs_root / "0001-a.md").write_text(
            "---\nstatus: [unterminiert\n---\n", encoding="utf-8")
        _obs(self.obs_root / "0002-b.md", id=2, status="open")
        obs_id, _, fehler = self._start(dispatch=True)
        self.assertEqual(obs_id, "2")
        self.assertIsNone(fehler)

    def test_kein_verzeichnis_kein_crash(self):
        obs_id, ergebnis, fehler = self._start(dispatch=True)
        self.assertIsNone(obs_id)
        self.assertIsNone(ergebnis)
        self.assertIsNone(fehler)

    def test_recherche_bekommt_body_als_untrusted(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        self._start(dispatch=True)
        recherche_text = self.aufrufe[0][1]
        self.assertIn("UNTRUSTED", recherche_text)
        self.assertIn("Beobachtungstext.", recherche_text)

    def test_fachbot_prompt_read_only_und_untrusted(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        self._start(dispatch=True)
        fachbot_text = self.aufrufe[1][1]
        self.assertIn("UNTRUSTED", fachbot_text)
        self.assertIn("read-only", fachbot_text.lower())
        self.assertIn("Beobachtungstext.", fachbot_text)
        for verbot in ["keine aenderungen", "keine commits", "keine orders",
                       "kein live", "kein cron"]:
            self.assertIn(verbot, fachbot_text.lower())


class StateTest(RouterTest):
    def test_statefile_wird_geschrieben(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        self._start(dispatch=True)
        self.assertTrue(self.state.exists())
        data = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertIn("verarbeitet", data)
        self.assertIn("1", data["verarbeitet"])


class _FakeLauf:
    """Ersatz fuer den Popen-Rueckgabewert: antwortet ohne echten Prozess."""

    def __init__(self, antwort):
        self._antwort = antwort
        self.returncode = 0

    def communicate(self, timeout=None):
        return self._antwort, ""

    def kill(self):
        pass


class SubprocessTest(RouterTest):
    """Mockt den echten subprocess.Popen-Aufruf und prueft die Kommandoargumente.

    Beide Hermes-Aufrufe (Recherche und Fachbot) muessen `--toolsets search`
    enthalten (read-only technisch erzwungen), die Serienreihenfolge bleibt
    Recherche -> genau EIN Fachbot.
    """

    def setUp(self):
        super().setUp()
        # hermes.exe existiert im Worktree nicht; auf eine echte Datei lenken,
        # damit die isfile-Pruefung in _rufe_bot durchlaeuft.
        self.exe = Path(self.tmp.name) / "hermes.exe"
        self.exe.write_text("", encoding="utf-8")
        self.p_exe = patch.object(r, "HERMES_EXE", self.exe)
        self.p_exe.start()
        self.addCleanup(self.p_exe.stop)

    def _popen(self, cmd, **kwargs):
        self.kommandos.append(cmd)
        name = cmd[cmd.index("-p") + 1]
        if name == "recherche":
            return _FakeLauf(self.recherche_antwort)
        return _FakeLauf("Antwort von %s" % name)

    def _start_popen(self, dispatch):
        self.kommandos = []
        self.p_popen = patch.object(r.subprocess, "Popen", side_effect=self._popen)
        self.p_popen.start()
        self.addCleanup(self.p_popen.stop)
        return r._verarbeite_eine(self.obs_root, dispatch)

    def test_beide_aufrufe_mit_toolsets_search(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        obs_id, ergebnis, fehler = self._start_popen(dispatch=True)
        self.assertEqual(obs_id, "1")
        self.assertIsNone(fehler)
        self.assertEqual(ergebnis["ziel"], "obsidian-skills")
        # Genau zwei Hermes-Prozesse: Recherche + genau EIN Fachbot.
        self.assertEqual(len(self.kommandos), 2)
        for cmd in self.kommandos:
            self.assertIn("--toolsets", cmd)
            # Kein Toolset-Default, keine Vererbung: search ist der einzige
            # Toolset-Wert im Kommando.
            idx = cmd.index("--toolsets")
            self.assertEqual(cmd[idx + 1], "search")

    def test_serienreihenfolge_und_toolsets(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        self._start_popen(dispatch=True)
        namen = []
        for cmd in self.kommandos:
            namen.append(cmd[cmd.index("-p") + 1])
            self.assertIn("--toolsets", cmd)
            self.assertIn("search", cmd)
        self.assertEqual(namen, ["recherche", "obsidian-skills"])

    def test_dry_run_startet_keinen_prozess(self):
        _obs(self.obs_root / "0001-a.md", id=1, status="open")
        self._start_popen(dispatch=False)
        self.assertEqual(self.kommandos, [])


if __name__ == "__main__":
    unittest.main()
