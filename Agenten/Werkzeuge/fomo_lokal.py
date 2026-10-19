"""FOMO-Robinhood-Radar: Wallets auf dem LOKALEN Modell bewerten (Ollama).

WARUM DIESE DATEI EXISTIERT
---------------------------
Das Fremd-Repo `Werkstatt/fomo-robinhood-radar` bewertet Trader-Wallets mit
Claude. Der Weg ueber `ANTHROPIC_API_KEY` ist auf diesem Rechner tot (Console-
Schluessel ohne Guthaben) - und der Haus-Regel nach faellt das Urteil lokal.
Das Repo verlangt ausdruecklich, dass die Bewertung AUCH OHNE Schluessel
funktioniert, ueber seine eigene Naht:

    score --export pending_scores.json  ->  Urteil faellen  ->  score --import

Genau diese Naht bedient dieses Werkzeug. Es wird NICHTS am Fremd-Repo geaendert:
der Prompt (`pipeline/score.py: SYSTEM`) und das Ergebnis-Schema
(`models.ScoreResult`) werden aus dem Repo GELESEN, damit das lokale Urteil
dasselbe Format und dieselben Regeln hat wie das Urteil der API.

ABLAUF
  1. `fomo-radar score --export <datei> [--limit N]` (Repo-venv, PYTHONIOENCODING)
  2. je Wallet EIN Ollama-Aufruf, strikt auf das Schema von ScoreResult
  3. `fomo-radar score --import <ergebnisdatei> --model-label ollama-<modell>`

REGELN, DIE AUS FEHLERN STAMMEN
-------------------------------
1. `think: false` ist Pflicht (ein Denk-Modell liefert sonst leeren `content`).
2. Temperatur 0 und fester Seed: dasselbe Wallet ergibt dasselbe Urteil.
3. Drei Stufen, wenn die Antwort unlesbar ist: Schema -> `format=json` ->
   freier Text. Bleibt es unlesbar, faellt der Wallet AUS (kein Urteil ist
   besser als ein geratenes) - er zaehlt in `unlesbar`, nicht in `bewertet`.
4. Das Modell darf sich nicht selbst adeln: `status` wird wie im Repo
   nachgerechnet (eine verteilende Wallet bleibt hoechstens `watch`), und
   `--trocken` importiert nichts.

Aufruf (aus dem Repo-Ordner ODER von ueberall, Pfade werden aus __file__ gebaut):

    Frontend/Agenten/Werkzeuge> ..\\..\\Werkstatt\\fomo-robinhood-radar\\.venv\\Scripts\\python.exe fomo_lokal.py --anzahl 3
    ... fomo_lokal.py --trocken            # nur rechnen, nichts importieren
    ... fomo_lokal.py --adresse 0xabc...   # genau eine Wallet
    ... fomo_lokal.py --modell qwen36-35b-a3b:8k

Tests: Agenten/Werkzeuge/tests/test_fomo_lokal.py (ohne Netz).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parent.parent                      # BrainFiles
REPO = WURZEL / "Werkstatt" / "fomo-robinhood-radar"
PY = REPO / ".venv" / "Scripts" / "python.exe"

OLLAMA = "http://127.0.0.1:11434/api/chat"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"

# Gemessen im Haus (Handel/llm_lokal.py): qwen35-8k haelt einen Vertrag 6/6 und
# antwortet warm in ~1,5 s; qwen36-35b-a3b braucht ~7,5 s warm. Fuer 16 Wallets
# ist beides vertretbar - das kleine Modell ist die Vorgabe.
MODELL_STANDARD = "qwen35-8k:latest"
SEED = 42
NUM_PREDICT = 700
ZEITGRENZE = 300.0

EXPORT_DATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "fomo-lokal" / "pending_scores.json"
ERGEBNIS_DATEI = WURZEL / "Agenten" / "Hermes" / "cache" / "fomo-lokal" / "local_scores.json"

# Test-Naht: None -> echter HTTP-Aufruf. Tests setzen eine Funktion
# (prompt, modell, schema, format) -> Text. Kein Test braucht Ollama.
ANFRAGE = None
LAUF = None                     # Test-Naht fuer den CLI-Aufruf des Repos


# ---------------------------------------------------------------- Repo-Zugang

def _repo_pfad_sichern() -> None:
    p = str(REPO)
    if p not in sys.path:
        sys.path.insert(0, p)


def system_prompt() -> str:
    """Die Regeltexte des Repos - EINE Quelle, keine Kopie."""
    _repo_pfad_sichern()
    from fomo_agent.pipeline.score import SYSTEM
    return SYSTEM


def schema() -> dict:
    _repo_pfad_sichern()
    from fomo_agent.models import ScoreResult
    return ScoreResult.model_json_schema()


def pruefe(objekt: dict):
    """Urteil gegen das Repo-Schema pruefen. Rueckgabe: ScoreResult oder None."""
    _repo_pfad_sichern()
    from fomo_agent.models import ScoreResult
    try:
        return ScoreResult.model_validate(objekt)
    except Exception:                                          # noqa: BLE001
        return None


def repo_lauf(args: list[str], *, trocken: bool = False) -> dict:
    """Das Repo-CLI aufrufen. Rueckgabe: {rc, ausgabe}."""
    if LAUF is not None:                                       # Test-Naht
        return LAUF(args, trocken=trocken)
    umgebung = dict(os.environ)
    umgebung["PYTHONIOENCODING"] = "utf-8"
    umgebung["SCORER"] = "manual"           # nie den toten API-Weg nehmen
    befehl = [str(PY), "-m", "fomo_agent.cli", *args]
    if trocken:
        return {"rc": 0, "ausgabe": "(trocken) " + " ".join(args)}
    p = subprocess.run(befehl, cwd=str(REPO), env=umgebung,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"rc": p.returncode, "ausgabe": (p.stdout or "") + (p.stderr or "")}


# ---------------------------------------------------------------- Ollama

def modelle() -> list[str] | None:
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=10) as antwort:
            daten = json.loads(antwort.read().decode("utf-8", "replace"))
    except Exception:                                          # noqa: BLE001
        return None
    return [m.get("name") for m in daten.get("models", []) if m.get("name")]


def modell_da(name: str) -> bool:
    namen = modelle() or []
    return any(n == name or n.split(":")[0] == name.split(":")[0] for n in namen)


def _echte_anfrage(prompt: str, modell: str, form: object, zeitgrenze: float) -> str:
    koerper = {
        "model": modell,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,                     # Regel 1: sonst leerer content
        "options": {"temperature": 0, "seed": SEED, "num_predict": NUM_PREDICT},
    }
    if form is not None:
        koerper["format"] = form
    daten = json.dumps(koerper).encode("utf-8")
    anfrage = urllib.request.Request(
        OLLAMA, data=daten, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as antwort:
        roh = json.loads(antwort.read().decode("utf-8", "replace"))
    return ((roh.get("message") or {}).get("content") or "").strip()


def frage(prompt: str, modell: str, form: object = None,
          zeitgrenze: float = ZEITGRENZE) -> str | None:
    """Rohtext des Modells. Wirft nie - ein Fehler ist kein Urteil."""
    try:
        text = (ANFRAGE(prompt, modell, form, zeitgrenze) if ANFRAGE
                else _echte_anfrage(prompt, modell, form, zeitgrenze))
    except Exception as e:                                     # noqa: BLE001
        print("  Ollama nicht erreichbar (%s): %s" % (modell, str(e)[:150]))
        return None
    return text or None


def _json_aus_text(text: str) -> dict | None:
    if not text:
        return None
    roh = text.strip()
    if roh.startswith("```"):
        roh = roh.strip("`")
        roh = roh.split("\n", 1)[-1] if "\n" in roh else roh
        roh = roh.rsplit("```", 1)[0]
    start, ende = roh.find("{"), roh.rfind("}")
    if start < 0 or ende <= start:
        return None
    try:
        geladen = json.loads(roh[start:ende + 1])
    except (TypeError, ValueError):
        return None
    return geladen if isinstance(geladen, dict) else None


# ---------------------------------------------------------------- Bewerten

def wallet_prompt(wallet: dict, regeln: str) -> str:
    """Das Marktbild einer Wallet unter die Regeln des Repos."""
    return (regeln
            + "\n\nScore exactly ONE trader. Answer with the JSON object only.\n"
            + "Trader context (JSON):\n"
            + json.dumps(wallet, separators=(",", ":"), ensure_ascii=False)[:4096])


def bewerte(wallet: dict, modell: str, regeln: str, form: dict) -> tuple[dict | None, str]:
    """Eine Wallet bewerten. Rueckgabe: (Ergebnis ohne address, Zustand).

    Zustand: 'bewertet' | 'unlesbar' | 'ollama_tot'. Drei Stufen, weil ein
    lokales Modell das Schema nicht immer haelt - geraten wird nie.
    """
    prompt = wallet_prompt(wallet, regeln)
    stufen: list[tuple[str, object]] = [("schema", form), ("json", "json"), ("text", None)]
    letzter = ""
    for name, f in stufen:
        text = frage(prompt, modell, f)
        if text is None and f is None:
            return None, "ollama_tot"
        objekt = _json_aus_text(text or "")
        if objekt is None:
            letzter = "kein JSON (%s)" % name
            continue
        objekt.pop("address", None)
        ergebnis = pruefe(objekt)
        if ergebnis is None:
            letzter = "Schema verletzt (%s): %s" % (name, json.dumps(objekt)[:120])
            continue
        return ergebnis.model_dump(), "bewertet"
    print("  unlesbar: %s" % letzter)
    return None, "unlesbar"


# ---------------------------------------------------------------- Ablauf

def exportieren(datei: Path, *, anzahl: int | None, adresse: str | None,
                alle: bool = False) -> dict:
    datei.parent.mkdir(parents=True, exist_ok=True)
    vorher = time.time()
    antwort = repo_lauf(["score", "--export", str(datei)]
                        + (["--force"] if alle else ["--unscored"])
                        + (["--limit", str(anzahl)] if anzahl else []))
    if antwort["rc"] != 0:
        raise SystemExit("Export fehlgeschlagen (rc=%s):\n%s" % (antwort["rc"], antwort["ausgabe"][:800]))
    print(antwort["ausgabe"].strip()[:300])
    nutzlast = json.loads(datei.read_text(encoding="utf-8"))
    if adresse:
        treffer = [w for w in nutzlast["wallets"] if w["address"].lower() == adresse.lower()]
        if not treffer:
            raise SystemExit("Adresse %s ist nicht in der Warteschlange (%d Wallets)."
                             % (adresse, len(nutzlast["wallets"])))
        nutzlast["wallets"] = treffer
    _ = vorher
    return nutzlast


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="FOMO-Radar-Wallets lokal mit Ollama bewerten")
    p.add_argument("--anzahl", type=int, help="hoechstens so viele Wallets exportieren")
    p.add_argument("--adresse", help="genau diese Wallet bewerten")
    p.add_argument("--modell", default=os.getenv("FOMO_LLM_MODELL", MODELL_STANDARD),
                   help="Ollama-Modell (Vorgabe %s)" % MODELL_STANDARD)
    p.add_argument("--trocken", action="store_true", help="rechnen, aber NICHTS importieren")
    p.add_argument("--alle", action="store_true",
                   help="auch Wallets mit frischem Urteil erneut bewerten (Export mit --force)")
    p.add_argument("--export-datei", default=str(EXPORT_DATEI))
    p.add_argument("--ergebnis-datei", default=str(ERGEBNIS_DATEI))
    a = p.parse_args(argv)

    if not PY.exists():
        raise SystemExit("Repo-venv fehlt: %s (Klon unter Werkstatt/fomo-robinhood-radar?)" % PY)
    if not modell_da(a.modell):
        raise SystemExit("Modell %s liegt nicht in Ollama. Vorhanden: %s"
                         % (a.modell, ", ".join(modelle() or []) or "keins erreichbar"))

    nutzlast = exportieren(Path(a.export_datei), anzahl=a.anzahl, adresse=a.adresse, alle=a.alle)
    wallets = nutzlast.get("wallets") or []
    if not wallets:
        print("Keine Wallet zu bewerten - die Warteschlange ist leer.")
        return 0
    regeln, form = system_prompt(), schema()
    print("Modell %s, %d Wallet(s), Schema %d Felder"
          % (a.modell, len(wallets), len(form.get("properties") or {})))

    ergebnisse: list[dict] = []
    zaehler = {"bewertet": 0, "unlesbar": 0}
    start = time.time()
    for i, w in enumerate(wallets, 1):
        name = ((w.get("fomo") or {}).get("fomo_handle") or w["address"][:10])
        t0 = time.time()
        urteil, zustand = bewerte(w, a.modell, regeln, form)
        if urteil is None:
            zaehler["unlesbar"] += 1
            print("%2d/%d %-20s UNLESBAR (%.1fs)" % (i, len(wallets), name, time.time() - t0))
            continue
        zaehler["bewertet"] += 1
        urteil["address"] = w["address"]
        ergebnisse.append(urteil)
        print("%2d/%d %-20s %3d %-7s conf %.2f (%.1fs) %s"
              % (i, len(wallets), name, urteil["score"], urteil["status"],
                 urteil["confidence"], time.time() - t0, urteil["summary"][:110]))

    dauer = time.time() - start
    ziel = Path(a.ergebnis_datei)
    ziel.write_text(json.dumps({"results": ergebnisse, "modell": a.modell,
                                "erzeugt": int(time.time())}, indent=1, ensure_ascii=False),
                    encoding="utf-8")
    print("\n%d bewertet, %d unlesbar, %.1f s (%.1f s je Wallet) -> %s"
          % (zaehler["bewertet"], zaehler["unlesbar"], dauer,
             dauer / max(1, len(wallets)), ziel))
    if a.trocken:
        print("--trocken: NICHT importiert.")
        return 0
    if not ergebnisse:
        print("Nichts zu importieren.")
        return 1
    antwort = repo_lauf(["score", "--import", str(ziel),
                         "--model-label", "ollama-%s" % a.modell.split(":")[0]])
    print(antwort["ausgabe"].strip()[:500])
    return 0 if antwort["rc"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())