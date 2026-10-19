#!/usr/bin/env python3
"""MCP-Bloecke der Hermes-Profile aus EINER Quelle erzeugen.

WARUM: Jedes Profil unter Agenten/Hermes/profiles/<name>/config.yaml trug eine
handgepflegte Kopie des mcp_servers-Blocks der Haupt-Config. Die Kopien liefen
auseinander (07.10.2026-Befund): in den Profilen fehlte `enabled: false` bei
affinity/blender/revolut-x - dort liefen sie, in der Haupt-Config nicht - und
`cwd` fehlte. Quelle ist jetzt der Block `mcp_servers` in
Agenten/Hermes/config.yaml. Was ein Profil bewusst anders braucht, steht in
Agenten/Hermes/profiles/mcp-abweichungen.yaml - nur dort.

WIE: Kein YAML-Roundtrip (zerstoert Anfuehrungszeichen und Reihenfolge, und die
Dateien sind CRLF). Die Server-Abschnitte der Haupt-Config werden Textzeile fuer
Textzeile uebernommen; Abweichungen sind Textersetzungen auf diesem Abschnitt.
Geschrieben wird nur der mcp_servers-Block, der Rest des Profils bleibt
byte-gleich, das Zeilenende bleibt wie in der Datei.

  python Agenten/Werkzeuge/mcp-profile-sync.py            # pruefen (Exit 1 bei Drift)
  python Agenten/Werkzeuge/mcp-profile-sync.py --anwenden # Profile schreiben
  python Agenten/Werkzeuge/mcp-profile-sync.py --profil claude-code

Profile ohne eigenen mcp_servers-Block (bots, lotse, nerd, ...) werden nicht
angefasst - sie haben bewusst keine Server.
Braucht PyYAML (nur zum Lesen der Abweichungen und fuer den Drift-Bericht).
"""
from __future__ import annotations

import argparse
import copy
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML fehlt: im Hermes-venv ausfuehren oder 'pip install pyyaml'")

HIER = os.path.dirname(os.path.abspath(__file__))
WURZEL = os.path.normpath(os.path.join(HIER, "..", ".."))
HAUPT = os.path.join(WURZEL, "Agenten", "Hermes", "config.yaml")
PROFILE = os.path.join(WURZEL, "Agenten", "Hermes", "profiles")
ABWEICHUNGEN = os.path.join(PROFILE, "mcp-abweichungen.yaml")

_SERVER = re.compile(r"^  ([^\s#:][^:]*):\s*$")


def lies(pfad):
    with open(pfad, "rb") as f:
        return f.read().decode("utf-8")


def eol(text):
    return "\r\n" if "\r\n" in text else "\n"


def block_grenzen(zeilen):
    """(start, ende) des mcp_servers-Blocks; ende exklusiv. None wenn keiner."""
    start = None
    for i, z in enumerate(zeilen):
        if z.rstrip() == "mcp_servers:":
            start = i
            break
    if start is None:
        return None
    ende = len(zeilen)
    for i in range(start + 1, len(zeilen)):
        z = zeilen[i]
        if z and not z[0].isspace() and not z.startswith("#"):
            ende = i
            break
    return start, ende


def server_abschnitte(zeilen):
    """Geordnete Liste (name, [zeilen]) der Server innerhalb eines Blocks."""
    out = []
    for z in zeilen:
        m = _SERVER.match(z)
        if m:
            out.append((m.group(1).strip("'\""), [z]))
        elif out:
            out[-1][1].append(z)
    return out


def haupt_abschnitte():
    text = lies(HAUPT)
    zeilen = text.splitlines()
    g = block_grenzen(zeilen)
    if not g:
        sys.exit("Kein mcp_servers-Block in " + HAUPT)
    return server_abschnitte(zeilen[g[0] + 1:g[1]])


def lade_abweichungen():
    with open(ABWEICHUNGEN, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def soll_block(profil, abw, haupt):
    """Zeilen (ohne Zeilenende) des erwarteten Blocks inkl. 'mcp_servers:'."""
    alle = abw.get("alle") or {}
    mein = (abw.get("profile") or {}).get(profil) or {}
    ausschluss = set(alle.get("ausschluss") or []) - set(mein.get("einschluss") or [])
    # ohne: je Server die Profile, in denen er entfaellt (z. B. windows-mcp nur
    # in den Desktop-Profilen). Liegt in einem eigenen Schluessel, weil
    # 'ausschluss' global gilt.
    ausschluss |= {n for n, profile_ in (abw.get("ohne") or {}).items()
                   if profil in (profile_ or [])}
    ersetze = copy.deepcopy(mein.get("ersetze") or {})
    repo = mein.get("projectatlas_repo")
    if repo:
        ersetze.setdefault("projectatlas", []).append(
            ["Werkstatt\\omnitrade\\", "Werkstatt\\%s\\" % repo])
    namen = {n for n, _ in haupt}
    unbekannt = (set(ersetze) | set(mein.get("einschluss") or [])) - namen
    if unbekannt:
        raise SystemExit("%s: Abweichung nennt Server, den die Haupt-Config nicht hat: %s"
                         % (profil, ", ".join(sorted(unbekannt))))
    zeilen = ["mcp_servers:"]
    for name, abschnitt in haupt:
        if name in ausschluss:
            continue
        text = "\n".join(abschnitt)
        for alt, neu in ersetze.get(name, []):
            if alt not in text:
                raise SystemExit("%s/%s: '%s' kommt im Abschnitt nicht vor" % (profil, name, alt))
            text = text.replace(alt, neu)
        zeilen.extend(text.split("\n"))
    zusatz = (abw.get("zusatzbloecke") or {})
    for name in mein.get("zusatz") or []:
        if name not in zusatz:
            raise SystemExit("%s: zusatzblock '%s' nicht definiert" % (profil, name))
        zeilen.extend(zusatz[name].rstrip("\n").split("\n"))
    return zeilen


def ist_block(zeilen):
    try:
        return yaml.safe_load("\n".join(zeilen))["mcp_servers"] or {}
    except Exception:
        return {}


def unterschied(ist, soll):
    a, b = ist_block(ist), ist_block(soll)
    out = []
    for k in sorted(set(a) | set(b)):
        if k not in b:
            out.append("%s: zu viel im Profil" % k)
        elif k not in a:
            out.append("%s: fehlt im Profil" % k)
        elif a[k] != b[k]:
            felder = sorted(f for f in set(a[k]) | set(b[k]) if a[k].get(f) != b[k].get(f))
            out.append("%s: %s" % (k, ", ".join(felder)))
    return out or ["nur Reihenfolge/Format"]


def lauf(profile, anwenden, ausgabe=print):
    abw = lade_abweichungen()
    haupt = haupt_abschnitte()
    drift = 0
    for p in profile:
        pfad = os.path.join(PROFILE, p, "config.yaml")
        text = lies(pfad)
        zeilen = text.splitlines()
        g = block_grenzen(zeilen)
        if not g:
            continue
        soll = soll_block(p, abw, haupt)
        ist = zeilen[g[0]:g[1]]
        if ist == soll:
            ausgabe("  OK    " + p)
            continue
        drift += 1
        ausgabe("  DRIFT %s: %s" % (p, "; ".join(unterschied(ist, soll))))
        if anwenden:
            # Zeilen ausserhalb des Blocks behalten ihr eigenes Zeilenende
            # (Profile koennen gemischte Enden haben); der neue Block nimmt das
            # Ende der Zeile 'mcp_servers:'.
            roh = text.splitlines(True)
            e = "\r\n" if roh[g[0]].endswith("\r\n") else "\n"
            neu = "".join(roh[:g[0]]) + "".join(z + e for z in soll) + "".join(roh[g[1]:])
            with open(pfad, "wb") as f:
                f.write(neu.encode("utf-8"))
    return drift


def profil_namen():
    return sorted(d for d in os.listdir(PROFILE)
                  if os.path.isfile(os.path.join(PROFILE, d, "config.yaml")))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--anwenden", action="store_true", help="Profile schreiben")
    ap.add_argument("--profil", action="append", help="nur dieses Profil (mehrfach)")
    a = ap.parse_args(argv)
    drift = lauf(a.profil or profil_namen(), a.anwenden)
    if drift and not a.anwenden:
        print("%d Profil(e) weichen von der Haupt-Config ab - mit --anwenden angleichen." % drift)
        return 1
    print("Profile stimmen mit der Haupt-Config ueberein." if not drift
          else "%d Profil(e) angeglichen." % drift)
    return 0


if __name__ == "__main__":
    sys.exit(main())
