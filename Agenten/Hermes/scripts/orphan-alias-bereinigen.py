#!/usr/bin/env python3
"""Bereinigt verwaiste Hermes-Profil-Aliase (~/.local/bin/*.bat) nach einem Update.

T-190: Der Hermes-'doctor' MELDET Orphan-Aliase
    ``Orphan alias: <x>.bat -> profile 'y' no longer exists``,
    entfernt sie aber nicht selbst, und die Hermes-Installation raeumt
    verwaiste Wrapper beim Update nicht auf. Die 14 Leichen vom 29.09.2026
    (agent-reach, coder, nous, projectatlas, superpowers, ...) mussten von
    Hand nach ~/.local/bin/.orphan-20260929/ verschoben werden.

Dieses Hauswerkzeug loest das dauerhaft: Es scannt den Wrapper-Ordner, findet
Wrapper, deren Zieldatei KEIN lebendes Profil ist, und verschiebt sie nach
~/.local/bin/.orphan-<JJJJMMTT>/ - derselbe Quarantaene-Pfad wie der Handgriff
vom 29.09. Ein Wrapper gilt als Hermes-Wrapper, wenn sein Text ``hermes -p``
enthaelt (dieselbe Erkennung wie ``profiles.py::_is_our_wrapper``); ein Profil
ist 'lebend', wenn sein Ordner ein Identitaetsmerkmal traegt
(config.yaml/.env/SOUL.md/profile.yaml/auth.json/state.db - derselbe Satz wie
``hermes_constants.named_profile_has_identity``). Ein Wrapper, der auf
``default`` oder einen reservierten Namen zeigt, wird nie angefasst.

Aufruf:
    python orphan-alias-bereinigen.py            # Trockenlauf: nur auflisten
    python orphan-alias-bereinigen.py --anwenden # verschiebt nach .orphan-<datum>/
    python orphan-alias-bereinigen.py --test     # Selbsttest (siehe unten)

Idempotent: laeuft erneut, nachdem alles veraumt wurde, findet er nichts mehr.
Nichts wird geloescht - nur in einen Quarantaene-Ordner verschoben.

Herkunft der Identitaetssetze bewusst NICHT ueber den hermes-agent-Import
bezogen: der Checkout wird von der Hermes-Installation bei jedem Update
zurueckgesetzt, ein Import daraus waere die Abhaengigkeit von genau dem Code,
den das Werkzeug ergaenzen soll. Die zwei Mengen sind als Konstanten
dokumentiert und deckungsgleich mit den Upstream-Lesern.

Selbsttest (kein Netz, kein Schreiben ausserhalb eines Temp-Ordners):
    python orphan-alias-bereinigen.py --test
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Wrapper-Ordner (dieselbe Kante wie hermes_cli.profiles._get_wrapper_dir).
WRAPPER_DIR = Path.home() / ".local" / "bin" if os.name == "nt" else Path.home() / ".local" / "bin"

# Profil-Wurzel (dieselbe Kante wie hermes_cli.profiles._get_profiles_root).
PROFILES_ROOT = Path(__file__).resolve().parents[2] / "Hermes" / "profiles"
# Fallback: wenn das Werkzeug woanders liegt als Agenten/Hermes/scripts/.
if not PROFILES_ROOT.is_dir():
    PROFILES_ROOT = Path(os.environ.get("HERMES_HOME", "")) / "profiles"

_WRAPPER_NEEDLE = "hermes -p "          # genau wie _is_our_wrapper / build_alias_map
_PROFILE_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")

# Identitaetsmarker eines lebenden Profils (deckungsgleich mit
# hermes_constants.named_profile_has_identity).
_IDENTITY_MARKERS = ("config.yaml", ".env", "SOUL.md", "profile.yaml", "auth.json", "state.db")


def _wrapper_ziel(pfad: Path) -> str | None:
    """Profilname, den ein Wrapper aktiviert; None wenn kein Hermes-Wrapper."""
    if not pfad.is_file() or pfad.suffix != ".bat":
        return None
    try:
        text = pfad.read_text(encoding="utf-8-sig", errors="strict")
    except (OSError, UnicodeDecodeError):
        return None
    idx = text.find(_WRAPPER_NEEDLE)
    if idx == -1:
        return None
    rest = text[idx + len(_WRAPPER_NEEDLE):].strip()
    first = rest.split(None, 1)[0].strip() if rest else ""
    if not first or not _PROFILE_RE.fullmatch(first):
        return None
    return first


def _profil_lebt(name: str) -> bool:
    """'default' lebt immer; ein benanntes Profil nur mit Identitaetsmerkmal."""
    if name == "default":
        return True
    pdir = PROFILES_ROOT / name
    if not pdir.is_dir():
        return False
    return any((pdir / m).exists() for m in _IDENTITY_MARKERS)


def _quarantaene_name() -> Path:
    return WRAPPER_DIR / (".orphan-" + dt.datetime.now().strftime("%Y%m%d"))


def finde_verwaiste() -> list[tuple[Path, str]]:
    """[(wrapper_pfad, profilname)] aller Orphan-Aliase, sortiert nach Name."""
    if not WRAPPER_DIR.is_dir():
        return []
    funde = []
    for e in sorted(WRAPPER_DIR.iterdir()):
        if not e.is_file():
            continue
        ziel = _wrapper_ziel(e)
        if ziel is None:
            continue
        if not _profil_lebt(ziel):
            funde.append((e, ziel))
    return funde


def bereinigen(anwenden: bool = False) -> list[tuple[Path, Path]]:
    """Verschiebt verwaiste Wrapper nach .orphan-<datum>/. Gibt [(alt, neu)] zurueck.

    Im Trockenlauf (anwenden=False) werden die Ziele nur berechnet, es wird
    nichts verschoben. Idempotent: ein zweiter Lauf findet nichts mehr.
    """
    verwaist = finde_verwaiste()
    if not verwaist:
        return []
    quarantaene = _quarantaene_name()
    ergebnis = []
    for pfad, _ in verwaist:
        ziel = quarantaene / pfad.name
        ergebnis.append((pfad, ziel))
        if anwenden:
            quarantaene.mkdir(parents=True, exist_ok=True)
            shutil.move(str(pfad), str(ziel))
    return ergebnis


def main() -> int:
    ap = argparse.ArgumentParser(description="Orphan-Aliase nach einem Hermes-Update bereinigen")
    ap.add_argument("--anwenden", action="store_true", help="wirklich nach .orphan-<datum>/ verschieben")
    ap.add_argument("--test", action="store_true", help="Selbsttest in einem Temp-Ordner fahren")
    args = ap.parse_args()
    if args.test:
        suite = unittest.TestLoader().loadTestsFromTestCase(SelbstTest)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if result.wasSuccessful() else 1

    ergebnis = bereinigen(anwenden=args.anwenden)
    if not ergebnis:
        print("keine verwaisten Aliase")
        return 0
    for alt, neu in ergebnis:
        marke = "->" if args.anwenden else "~>"
        print(f"{marke} {alt.name} ({alt.parent / '.orphan-*'})  profil: {_wrapper_ziel(alt)}")
    aktion = "verschoben" if args.anwenden else "wuerde verschoben (--anwenden fuer echt)"
    print(f"{len(ergebnis)} verwaiste Alias(e) {aktion} nach {_quarantaene_name()}")
    return 0


class SelbstTest(unittest.TestCase):
    """Prueft die Regeln in einem Wegwerf-Ordner, ohne die echte Umgebung anzufassen."""

    def _probe(self):
        tmp = Path(tempfile.mkdtemp(prefix="orphan-alias-"))
        wrapper = tmp / "bin"
        wrapper.mkdir()
        profile = tmp / "profiles"
        profile.mkdir()
        return tmp, wrapper, profile

    def _heile_probe(self):
        global WRAPPER_DIR, PROFILES_ROOT
        tmp, wrapper, profile = self._probe()
        self.alt_w, self.alt_r = WRAPPER_DIR, PROFILES_ROOT
        WRAPPER_DIR, PROFILES_ROOT = wrapper, profile
        # lebender Plus ein toter Name, dazu ein Nicht-Wrapper und eine Reserve-POSIX-Datei
        (profile / "lebt").mkdir()
        (profile / "lebt" / "config.yaml").write_text("x", encoding="utf-8")
        (profile / "leer").mkdir()                      # ohne Identitaetsmerkmal => tot
        (wrapper / "lebt.bat").write_text("@echo off\r\nhermes -p lebt %*\r\n", encoding="utf-8")
        (wrapper / "tot.bat").write_text("@echo off\r\nhermes -p tot %*\r\n", encoding="utf-8")
        (wrapper / "leer.bat").write_text("@echo off\r\nhermes -p leer %*\r\n", encoding="utf-8")
        (wrapper / "kein-wrapper.bat").write_text("@echo off\r\necho hi\r\n", encoding="utf-8")
        (wrapper / "echt.bin").write_bytes(b"\x00\x01binary")   # kein .bat => kein Wrapper
        return tmp

    def tearDown(self):                                     # noqa: N802
        if hasattr(self, "alt_w"):
            WRAPPER_DIR, PROFILES_ROOT = self.alt_w, self.alt_r
        if hasattr(self, "_tmp"):
            shutil.rmtree(self._tmp, ignore_errors=True)

    def test_lebt_bleibt_tot_wird_gefunden(self):
        self._tmp = self._heile_probe()
        funde = finde_verwaiste()
        namen = {p.name for p, _ in funde}
        self.assertEqual(namen, {"tot.bat", "leer.bat"}, namen)   # verwaist: tot + leer
        self.assertNotIn("lebt.bat", namen)
        self.assertNotIn("kein-wrapper.bat", namen)

    def test_trockenlauf_verschiebt_nichts(self):
        self._tmp = self._heile_probe()
        ergebnis = bereinigen(anwenden=False)
        self.assertEqual(len(ergebnis), 2)
        self.assertTrue((WRAPPER_DIR / "tot.bat").exists(), "Trockenlauf darf nicht verschieben")

    def test_anwenden_verschiebt_und_ist_idempotent(self):
        self._tmp = self._heile_probe()
        ergebnis = bereinigen(anwenden=True)
        self.assertEqual(len(ergebnis), 2)
        self.assertFalse((WRAPPER_DIR / "tot.bat").exists())
        self.assertTrue((WRAPPER_DIR / "lebt.bat").exists())
        # zweiter Lauf: nichts mehr zu tun
        self.assertEqual(bereinigen(anwenden=True), [])
        # Quarantaene-Ordner traegt beide
        datname = (dt.datetime.now().strftime("%Y%m%d"))
        for name in ("tot.bat", "leer.bat"):
            self.assertTrue((WRAPPER_DIR / f".orphan-{datname}" / name).exists(), name)

    def test_default_und_reserviert_werden_nie_angefasst(self):
        self._tmp = self._heile_probe()
        (WRAPPER_DIR / "default.bat").write_text("@echo off\r\nhermes -p default %*\r\n", encoding="utf-8")
        ergebnis = bereinigen(anwenden=True)
        namen = {alt.name for alt, _ in ergebnis}
        self.assertNotIn("default.bat", namen)
        self.assertTrue((WRAPPER_DIR / "default.bat").exists())


if __name__ == "__main__":
    sys.exit(main())
