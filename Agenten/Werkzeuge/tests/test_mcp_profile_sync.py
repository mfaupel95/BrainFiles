"""Tests fuer Agenten/Werkzeuge/mcp-profile-sync.py.

Gegenproben, ohne die das Werkzeug nichts verhindert:
1. Ein Profil mit abweichendem Block wird als DRIFT gemeldet (nicht still OK).
2. --anwenden aendert NUR den mcp_servers-Block; der Rest bleibt byte-gleich,
   das Zeilenende (CRLF) bleibt erhalten.
3. Zweiter Lauf nach dem Anwenden ist idempotent (kein Drift).
4. Alle echten Profile im Repo stimmen mit der Quelle ueberein.
"""
import importlib.util
import os
import shutil
import tempfile
import unittest

_HIER = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "mcp_profile_sync", os.path.join(_HIER, "..", "mcp-profile-sync.py"))
ms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ms)


class SyncTest(unittest.TestCase):
    def test_echte_profile_ohne_drift(self):
        self.assertEqual(ms.lauf(ms.profil_namen(), False, ausgabe=lambda s: None), 0)

    def test_drift_anwenden_idempotent_und_crlf(self):
        tmp = tempfile.mkdtemp()
        alt = ms.PROFILE
        try:
            shutil.copytree(alt, os.path.join(tmp, "p"))
            ms.PROFILE = os.path.join(tmp, "p")
            ms.ABWEICHUNGEN = os.path.join(ms.PROFILE, "mcp-abweichungen.yaml")
            pfad = os.path.join(ms.PROFILE, "claude-code", "config.yaml")
            with open(pfad, "rb") as f:
                ist = f.read().decode("utf-8")
            i = ist.index("mcp_servers:")
            kaputt = ist[:i] + ist[i:].replace("    enabled: false\r\n", "", 1)
            self.assertNotEqual(ist, kaputt)
            with open(pfad, "wb") as f:
                f.write(kaputt.encode("utf-8"))
            self.assertEqual(ms.lauf(["claude-code"], False, ausgabe=lambda s: None), 1)
            self.assertEqual(ms.lauf(["claude-code"], True, ausgabe=lambda s: None), 1)
            with open(pfad, "rb") as f:
                neu = f.read().decode("utf-8")
            self.assertEqual(neu, ist)  # Rest und Zeilenende byte-gleich
            self.assertEqual(ms.lauf(["claude-code"], False, ausgabe=lambda s: None), 0)
        finally:
            ms.PROFILE = alt
            ms.ABWEICHUNGEN = os.path.join(alt, "mcp-abweichungen.yaml")
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
