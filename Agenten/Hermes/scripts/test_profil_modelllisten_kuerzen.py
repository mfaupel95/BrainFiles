"""Pruefungen fuer scripts/profil-modelllisten-kuerzen.py - auf KOPIEN, nie auf den echten Profilen."""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

import yaml

HIER = Path(__file__).resolve()
HERMES = HIER.parents[2]
SPEC = importlib.util.spec_from_file_location("kuerzen", HERMES / "scripts" / "profil-modelllisten-kuerzen.py")
mod = importlib.util.module_from_spec(SPEC)
sys.modules["kuerzen"] = mod
SPEC.loader.exec_module(mod)

fehler = 0


def pruefe(name: str, bedingung: bool, zusatz: str = "") -> None:
    global fehler
    print(("OK   " if bedingung else "ROT  ") + name + (" | " + zusatz if zusatz else ""))
    if not bedingung:
        fehler += 1


VORLAGE = """model:
  default: deepseek/deepseek-v4.1-flash
  provider: nous
providers:
  ollama-launch:
    base_url: http://127.0.0.1:11434/v1
    default_model: gemma-e4b-8k:cpu
    discover_models: true
    model: gemma-e4b-8k:cpu
    models:
    - gemma-e4b-8k:latest
    - gemma-e4b-8k:cpu
    - glm4:9b
    - qwen3.5:9b
  omniroute:
    base_url: http://localhost:20128/v1
    default_model: auto
    discover_models: true
    model: auto
    models:
      auto: {}
      auto/best-coding: {}
      auto/coding:free: {}
      "sonder/fall: x": {}
      auto/vision: {}
fallback_providers:
  - provider: ollama-launch
    model: gemma-e4b-8k:cpu
  - provider: omniroute
    model: auto/coding:free
terminal:
  cwd: C:\\irgendwo
"""


def kopie(tmp: str, text: str = VORLAGE) -> Path:
    p = Path(tmp) / "config.yaml"
    p.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    return p


with tempfile.TemporaryDirectory() as tmp:
    # 1) Kuerzen in beiden Formen
    p = kopie(tmp)
    vorher = p.read_bytes()
    e = mod._kuerzen(p, True)
    neu = p.read_bytes()
    pruefe("Kuerzen meldet Erfolg", e["stand"] == "gekuerzt", e["stand"])
    pruefe("Zahlen kleiner", e["nachher"] < e["vorher"], "%d -> %d" % (e["vorher"], e["nachher"]))
    d = yaml.safe_load(neu.decode("utf-8"))
    pruefe("YAML liest die Datei", d["model"]["default"] == "deepseek/deepseek-v4.1-flash")
    pruefe("referenzierte Modelle bleiben (Liste)",
           d["providers"]["ollama-launch"]["models"] == ["gemma-e4b-8k:cpu"],
           str(d["providers"]["ollama-launch"]["models"]))
    pruefe("referenzierte Modelle bleiben (Dict)",
           set(d["providers"]["omniroute"]["models"]) == {"auto", "auto/coding:free"},
           str(sorted(d["providers"]["omniroute"]["models"])))
    pruefe("nicht referenzierte fallen", "auto/vision" not in d["providers"]["omniroute"]["models"])
    pruefe("Schluessel mit Doppelpunkt ueberlebt", "sonder/fall: x" not in d["providers"]["omniroute"]["models"])
    pruefe("Zeilenenden CRLF", neu.count(b"\r\n") == neu.count(b"\n") and neu.count(b"\r\r") == 0)
    pruefe("andere Bloecke unberuehrt", d["terminal"]["cwd"] == "C:\\irgendwo" and d["providers"]["omniroute"]["discover_models"] is True)
    pruefe("Sicherung angelegt", (Path(tmp) / ("config.yaml.bak-" + e["sicherung"].split("bak-")[1])).exists() if "sicherung" in e else False, e.get("sicherung", "-"))

    # 2) Zweiter Lauf ist still
    e2 = mod._kuerzen(p, True)
    pruefe("zweiter Lauf still", e2["stand"] == "nichts zu kuerzen", e2["stand"])
    pruefe("zweiter Lauf schreibt nicht", p.read_bytes() == neu)

    # 3) Leere Schnittmenge: der ganze models:-Block verschwindet
    ohne_ref = (VORLAGE.replace("    default_model: auto\n", "    default_model: fremd/x\n")
                    .replace("    model: auto\n", "    model: fremd/x\n")
                    .replace("    model: auto/coding:free\n", "    model: fremd/y\n"))
    p2 = kopie(tmp, ohne_ref)
    e3 = mod._kuerzen(p2, True)
    d3 = yaml.safe_load(p2.read_bytes().decode("utf-8"))
    pruefe("leere Liste entfernt den Block", "models" not in d3["providers"]["omniroute"], e3["stand"])
    pruefe("Anbieter bleibt erhalten", d3["providers"]["omniroute"]["base_url"] == "http://localhost:20128/v1")

    # 4) Trockenlauf schreibt nicht
    p3 = kopie(tmp, VORLAGE)
    roh3 = p3.read_bytes()
    e4 = mod._kuerzen(p3, False)
    pruefe("Trockenlauf schreibt nicht", p3.read_bytes() == roh3 and e4["stand"] == "Trockenlauf")
    pruefe("Trockenlauf meldet Zahlen", e4["vorher"] == 9 and e4["nachher"] == 3, "%d -> %d" % (e4["vorher"], e4["nachher"]))

    # 5) Gegenprobe greift: ein referenziertes Modell, das fehlt, wird nicht erfunden
    p4 = kopie(tmp, VORLAGE.replace("    - glm4:9b", "    - gemma-e4b-8k:latest"))
    e5 = mod._kuerzen(p4, True)
    d5 = yaml.safe_load(p4.read_bytes().decode("utf-8"))
    pruefe("fehlende Referenz wird nicht erfunden",
           d5["providers"]["ollama-launch"]["models"] == ["gemma-e4b-8k:cpu"], e5["stand"])

print("\nFehler:", fehler)
sys.exit(1 if fehler else 0)