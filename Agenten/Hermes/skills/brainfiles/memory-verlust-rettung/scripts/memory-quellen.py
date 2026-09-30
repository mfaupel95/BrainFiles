#!/usr/bin/env python3
"""Sammelt Memory-Schnappschuesse und vergleicht Profil-Inseln gegen das Hauptgedaechtnis.

Zwei Unterbefehle:

  schnappschuesse   Zieht MEMORY.md aus Agenten/Hermes/backups/*.zip und den Memory-Block
                    aus Agenten/Hermes/sessions/request_dump_*.json (er steht in
                    request.body.system; der USER-PROFILE-Block wird abgeschnitten).
                    Ablage: Agenten/Hermes/cache/scratch/memsnap/

  inseln            Vergleicht jede profiles/<bot>/memories/MEMORY.md gegen das
                    Hauptgedaechtnis und zeigt Eintraege, die dort fehlen, mit Urteil
                    'abgeloest' (>=45 % Wortdeckung durch einen heutigen Eintrag) oder
                    'verwaist' (Inhalt wirklich weg).

Aufruf aus der BrainFiles-Wurzel (terminal-Werkzeug), nur stdlib, alles lesend.
"""
import argparse
import glob
import json
import os
import re
import sys
import zipfile

HIER = os.path.dirname(os.path.abspath(__file__))
# scripts -> memory-verlust-rettung -> brainfiles -> skills -> Hermes -> Agenten -> BrainFiles
WURZEL = os.path.abspath(os.path.join(HIER, "..", "..", "..", "..", "..", ".."))
HERMES = os.path.join(WURZEL, "Agenten", "Hermes")
ZIEL = os.path.join(HERMES, "cache", "scratch", "memsnap")
STOP = set("""der die das ein eine einen einem eines und oder aber auch mit ohne fuer von zu im in am an auf aus bei
ist sind war waren wird werden hat haben hatte hatten nicht nur noch schon sehr mehr als wie dass dieser diese dieses
the a an of to in on for and or with is are was were be been it its this that as at by from not only also
chars your personal notes memory""".split())


def woerter(t):
    return set(w for w in re.findall(r"[A-Za-zÄÖÜäöüß0-9_.\-/]{3,}", t.lower()) if w not in STOP)


def norm(t):
    return re.sub(r"\s+", " ", t or "").strip()


def eintraege(text):
    teile = [x.strip() for x in re.split(r"\n?\s*§\s*\n?", text)]
    out = []
    for t in teile:
        t = re.sub(r"^[═\s]+", "", t)
        t = re.sub(r"^MEMORY \(your personal notes\)[^\n]*\n?", "", t)
        t = t.strip()
        if len(t) > 40:
            out.append(norm(t))
    return out


def nur_memory_block(text):
    """Aus einem Anfrage-Dump nur den MEMORY-Block (nicht USER PROFILE / SKILLS)."""
    i = text.find("MEMORY (your personal notes)")
    if i < 0:
        return text
    rest = text[i:]
    for marke in ("USER PROFILE", "SKILLS"):
        j = rest.find(marke)
        if j > 0:
            rest = rest[:j]
    return rest


def schnappschuesse(ziel=ZIEL):
    os.makedirs(ziel, exist_ok=True)
    n_zip = n_dump = 0
    for z in sorted(glob.glob(os.path.join(HERMES, "backups", "*.zip"))):
        try:
            zf = zipfile.ZipFile(z)
        except Exception as e:                                  # noqa: BLE001
            print("uebersprungen %s: %s" % (z, e))
            continue
        basis = os.path.basename(z).replace(".zip", "")
        for n in zf.namelist():
            p = n.replace(chr(92), "/")
            if not p.endswith("memories/MEMORY.md"):
                continue
            teile = p.split("/")
            vor = "_".join(teile[:teile.index("memories")]) or "root"
            out = os.path.join(ziel, "zip_%s__%s.md" % (basis, vor))
            with open(out, "wb") as f:
                f.write(zf.read(n))
            n_zip += 1
    start = re.compile(r"MEMORY \(your personal notes\)")
    for f in sorted(glob.glob(os.path.join(HERMES, "sessions", "request_dump_*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:                                        # noqa: BLE001
            continue
        bloecke = ((d.get("request") or {}).get("body") or {}).get("system")
        if isinstance(bloecke, str):
            bloecke = [bloecke]
        if not isinstance(bloecke, list):
            continue
        text = "\n".join(x if isinstance(x, str) else json.dumps(x) for x in bloecke)
        if not start.search(text):
            continue
        ts = re.sub(r"[^0-9]", "", d.get("timestamp") or "")[:14]
        out = os.path.join(ziel, "dump_%s_%s.md" % (ts, d.get("session_id")))
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(nur_memory_block(text))
        n_dump += 1
    print("Schnappschuesse: %d aus Backups, %d aus Anfrage-Dumps -> %s" % (n_zip, n_dump, ziel))
    return 0


def inseln(ziel=ZIEL, ausgabe=None):
    with open(os.path.join(HERMES, "memories", "MEMORY.md"), encoding="utf-8") as f:
        haupt = f.read()
    liste = eintraege(haupt)
    wort = [woerter(e) for e in liste]

    def bewerte(text):
        w = woerter(text)
        if not w:
            return 0.0, ""
        bester, deckung = "", 0.0
        for i, aw in enumerate(wort):
            if not aw:
                continue
            d = len(w & aw) / len(w)
            if d > deckung:
                deckung, bester = d, liste[i]
        return round(deckung, 2), bester[:150]

    ergebnis = {"haupt_zeichen": len(haupt), "haupt_eintraege": len(liste), "inseln": {}}
    for p in sorted(glob.glob(os.path.join(HERMES, "profiles", "*", "memories", "MEMORY.md"))):
        profil = p.replace(chr(92), "/").split("/")[-3]
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        fehlend = []
        for e in eintraege(txt):
            if e in liste:
                continue
            d, naechster = bewerte(e)
            fehlend.append({"text": e, "zeichen": len(e), "deckung": d,
                            "urteil": "abgeloest" if d >= 0.45 else "verwaist",
                            "naechster_heute": naechster})
        ergebnis["inseln"][profil] = {"zeichen": len(txt), "eintraege": len(eintraege(txt)),
                                      "fehlend": len(fehlend), "liste": fehlend}
    print("Hauptgedaechtnis: %d Zeichen, %d Eintraege" % (len(haupt), len(liste)))
    for profil, d in ergebnis["inseln"].items():
        verwaist = [x for x in d["liste"] if x["urteil"] == "verwaist"]
        if d["fehlend"]:
            print("  %-28s %3d von %3d Eintraegen fehlen, davon %d verwaist"
                  % (profil, d["fehlend"], d["eintraege"], len(verwaist)))
            for x in verwaist:
                print("      [%d Zeichen] %s" % (x["zeichen"], x["text"][:140]))
    if ausgabe:
        with open(ausgabe, "w", encoding="utf-8", newline="") as f:
            json.dump(ergebnis, f, ensure_ascii=False, indent=1)
        print("geschrieben: %s" % ausgabe)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("befehl", choices=["schnappschuesse", "inseln"])
    ap.add_argument("--ziel", default=ZIEL, help="Zielordner der Schnappschuesse")
    ap.add_argument("--json", help="Ergebnis von 'inseln' zusaetzlich als JSON sichern")
    a = ap.parse_args(argv)
    if a.befehl == "schnappschuesse":
        return schnappschuesse(a.ziel)
    return inseln(a.ziel, a.json)


if __name__ == "__main__":
    sys.exit(main())