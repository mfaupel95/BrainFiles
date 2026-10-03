"""jevgrep an OpenCode Zen anmelden - ohne dass der Schluessel durch den Chat geht.

Hintergrund: OpenCode Zen fuehrt Jev unter `https://opencode.ai/zen/v1/systemone`
und hat neben dem bezahlten `jev-1.13` ein **kostenloses** `jev-1.13-free`. Der
Anbieter `opencode` in jevgrep zeigt auf das bezahlte Modell; deshalb meldet dieses
Werkzeug den EIGENEN Endpunkt (`--provider custom`) mit dem freien Modell an.

Der Schluessel wird aus der OpenCode-Anmeldung gelesen
(`~/.local/share/opencode/auth.json`, entsteht durch `opencode auth login`), per
stdin an `jg auth` gereicht und **nie ausgegeben** - auch nicht bei Fehlern.

Aufruf (aus der BrainFiles-Wurzel oder mit absolutem Pfad):
    python Agenten/Werkzeuge/jevgrep/von_opencode_anmelden.py            # Trockenlauf
    python Agenten/Werkzeuge/jevgrep/von_opencode_anmelden.py --anwenden
    python Agenten/Werkzeuge/jevgrep/von_opencode_anmelden.py --anwenden --modell jev-1.13
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
JG = HIER / "jg.cmd"
BASIS = "https://opencode.ai/zen/v1"
MODELL = "jev-1.13-free"
ANMELDUNG = Path(os.path.expanduser("~/.local/share/opencode/auth.json"))
# Namen, unter denen OpenCode Zen in der Anmeldedatei stehen kann.
ZEN_NAMEN = ("opencode", "opencode-zen", "zen")
# Windows-Variablen, aus denen der Schluessel kommen darf (in dieser Reihenfolge).
UMGEBUNG_NAMEN = ("OPENCODE_API_KEY", "OPENCODE_ZEN_API_KEY", "ZEN_API_KEY")


def _aus_registry(name: str) -> str | None:
    """Eine Benutzervariable lesen, OHNE den Wert je in eine Kommandozeile zu geben.

    Direkt aus der Registry, nicht ueber `reg query` und nicht aus der
    Prozessumgebung: ein frisch gesetztes `setx` sieht ein laufender Prozess nicht,
    und `reg query` gibt den Wert im Klartext aus.
    """
    try:
        import winreg
    except ImportError:
        return None
    for wurzel in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(wurzel, "Environment") as k:
                wert, _ = winreg.QueryValueEx(k, name)
        except OSError:
            continue
        if isinstance(wert, str) and wert.strip():
            return wert.strip()
    return None


def aus_umgebung() -> tuple[str | None, str]:
    """Den Schluessel aus der Umgebung holen. Rueckgabe: (Wert, Quelle)."""
    for name in UMGEBUNG_NAMEN:
        wert = os.environ.get(name)
        if isinstance(wert, str) and wert.strip():
            return wert.strip(), f"Prozessumgebung {name}"
    for name in UMGEBUNG_NAMEN:
        wert = _aus_registry(name)
        if wert:
            return wert, f"Windows-Benutzervariable {name}"
    return None, ""


def schluessel_lesen(datei: Path | None = None, quelle: str = "auto") -> tuple[str | None, str]:
    """Den Zen-Schluessel holen: erst Umgebung, dann OpenCode-Anmeldung."""
    if quelle in ("auto", "umgebung"):
        wert, herkunft = aus_umgebung()
        if wert:
            return wert, herkunft
        if quelle == "umgebung":
            return None, ""
    pfad = Path(datei) if datei else ANMELDUNG
    if not pfad.is_file():
        return None, ""
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, ""
    for name, eintrag in (daten or {}).items():
        if not isinstance(eintrag, dict):
            continue
        if name.lower() in ZEN_NAMEN or "zen" in name.lower() or "opencode" in name.lower():
            for feld in ("key", "apiKey", "api_key", "access", "token"):
                wert = eintrag.get(feld)
                if isinstance(wert, str) and wert.strip():
                    return wert.strip(), name
    return None, ""


def anmelden(schluessel: str, modell: str, basis: str = BASIS) -> int:
    r = subprocess.run(
        [str(JG), "auth", "--provider", "custom", "--base-url", basis,
         "--model", modell, "--stdin"],
        input=schluessel + "\n", capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    # Die Ausgabe von jg auth nennt nur den Host, nie den Schluessel.
    print((r.stdout or "").strip())
    if r.stderr:
        print((r.stderr or "").strip()[:400])
    return r.returncode


def main() -> int:
    p = argparse.ArgumentParser(description="jevgrep an OpenCode Zen anmelden")
    p.add_argument("--anwenden", action="store_true", help="wirklich anmelden")
    p.add_argument("--modell", default=MODELL, help=f"Modell-ID (Vorgabe {MODELL})")
    p.add_argument("--doctor", action="store_true", help="nach dem Anmelden jg doctor fahren")
    p.add_argument("--datei", help="abweichende Anmeldedatei (nur fuer Tests)")
    p.add_argument("--quelle", choices=("auto", "umgebung", "datei"), default="auto",
                   help="woher der Schluessel kommt (Vorgabe auto: Umgebung, dann Datei)")
    p.add_argument("--basis", default=BASIS, help=f"abweichender Endpunkt (Vorgabe {BASIS})")
    a = p.parse_args()

    if not JG.is_file():
        print(f"jg.cmd fehlt: {JG}")
        return 2
    schluessel, name = schluessel_lesen(a.datei, a.quelle)
    if not schluessel:
        print("Kein Zen-Schluessel gefunden.")
        print("  Quelle 1: Windows-Benutzervariable OPENCODE_API_KEY"
              "  ->  setx OPENCODE_API_KEY \"<wert>\"   (danach neu anmelden oder dieses Werkzeug nutzen)")
        print(f"  Quelle 2: OpenCode-Anmeldung {a.datei or ANMELDUNG}"
              "  ->  opencode auth login (Anbieter 'OpenCode Zen')")
        print("  Quelle 3: Schluessel auf opencode.ai/auth holen und in eine Datei legen, dann")
        print("            .\\jevgrep.cmd auth --provider custom "
              f"--base-url {a.basis} --model {a.modell} --stdin < <datei>")
        return 3

    print(f"Schluessel gefunden: {name}, {len(schluessel)} Zeichen (Wert nicht angezeigt).")
    print(f"Ziel: {a.basis} | Modell {a.modell}")
    if not a.anwenden:
        print("Trockenlauf - nichts geschrieben. Mit --anwenden ausfuehren.")
        return 0

    rc = anmelden(schluessel, a.modell, a.basis)
    print("Anmeldung:", "ok" if rc == 0 else f"fehlgeschlagen (Exit {rc})")
    if rc == 0 and a.doctor:
        d = subprocess.run([str(JG), "doctor"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print((d.stdout or "").strip())
    return rc


if __name__ == "__main__":
    sys.exit(main())