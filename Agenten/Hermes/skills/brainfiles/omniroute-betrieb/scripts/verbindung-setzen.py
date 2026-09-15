"""Provider-Verbindung im OmniRoute per Management-API setzen und pruefen.

Liest alle Zugangswerte direkt aus HKCU\\Environment (winreg), nie aus der
Kommandozeile, und gibt nur Status, Modellnamen und Fehlerklassen aus - keine
Schluessel, keine Kopien. Damit steht kein Secret in argv oder im Verlauf.

Aufrufe:
  python verbindung-setzen.py --liste
  python verbindung-setzen.py --sichern
  python verbindung-setzen.py --verbindung <id> --setzen --key-var ANTHROPIC_API_KEY \\
         --name "Anthropic (API-Key)" --base-url https://api.anthropic.com/v1
  python verbindung-setzen.py --pruefen
  python verbindung-setzen.py --anfrage anthropic/claude-opus-5
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
import winreg
from pathlib import Path

HOME = Path(os.path.expanduser("~")) / ".omniroute"
DB = HOME / "storage.sqlite"
BASIS = "http://127.0.0.1:20128"


def user_env(name: str) -> str:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as schluessel:
        wert, _ = winreg.QueryValueEx(schluessel, name)
    return wert


def call(methode: str, pfad: str, rumpf: dict | None = None, token: str | None = None,
         timeout: int = 180) -> tuple[int, str]:
    daten = json.dumps(rumpf).encode() if rumpf is not None else None
    kopf = {"Content-Type": "application/json"}
    if token:
        kopf["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASIS + pfad, data=daten, headers=kopf, method=methode)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as antwort:
            return antwort.status, antwort.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as fehler:
        return fehler.code, fehler.read().decode("utf-8", "replace")
    except Exception as fehler:  # noqa: BLE001
        return -1, f"{type(fehler).__name__}: {fehler}"


def liste() -> None:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    for zeile in con.execute(
        "SELECT id, provider, name, is_active, test_status, error_code, default_model"
        " FROM provider_connections ORDER BY provider, priority"
    ):
        print(f"{zeile['provider']:<16} {str(zeile['name'])[:28]:<28} aktiv={zeile['is_active']} "
              f"test={zeile['test_status']} fehler={zeile['error_code']} id={zeile['id']}")
    con.close()


def sichern(grund: str = "verbindung") -> None:
    ziel_dir = HOME / "db_backups"
    ziel_dir.mkdir(exist_ok=True)
    ziel = ziel_dir / f"db_{time.strftime('%Y%m%d-%H%M%S')}_{grund}.sqlite"
    src = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(str(ziel))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    print(f"SICHERUNG {ziel}  {ziel.stat().st_size} B")


def setzen(verbindung: str, key_var: str, name: str | None, base_url: str | None) -> None:
    key = user_env(key_var)
    admin = user_env("OMNIROUTE_ADMIN_API_KEY")
    print(f"{key_var}: len={len(key)}")
    rumpf: dict = {"apiKey": key}
    if name:
        rumpf["name"] = name
    if base_url:
        # providerSpecificData wird gemerged: nur ueberschreiben, was falsch ist.
        # Leerstring wird von der Validierung abgelehnt ("must be a valid http(s) URL").
        rumpf["providerSpecificData"] = {"baseUrl": base_url}
    status, text = call("PUT", f"/api/providers/{verbindung}", rumpf, admin)
    print(f"PUT  status={status}")
    if status >= 300:
        print("  antwort:", text[:400])
        return
    status, text = call("POST", f"/api/providers/{verbindung}/test", {}, admin)
    print(f"TEST status={status}")
    try:
        nutzlast = json.loads(text)
    except Exception:  # noqa: BLE001
        print("  antwort:", text[:400])
        return
    for feld in ("valid", "success", "status", "error", "message", "testStatus"):
        if feld in nutzlast:
            print(f"  {feld}: {nutzlast[feld]}")
    print("  Hinweis: 'valid: true' prueft die ANMELDUNG, nicht ein Modell -"
          " danach immer --pruefen und --anfrage.")


def pruefen(vorwahl: str = "") -> None:
    router_key = user_env("OMNIROUTE_API_KEY")
    status, text = call("GET", "/v1/models", None, router_key, timeout=90)
    print(f"/v1/models status={status}")
    if status != 200:
        print("  ", text[:300])
        return
    ids = [m["id"] for m in json.loads(text).get("data", [])]
    passend = sorted(i for i in ids if vorwahl and i.startswith(vorwahl)) if vorwahl else []
    print(f"   modelle={len(ids)} mit vorwahl '{vorwahl}'={len(passend)}")
    for i in passend[:15]:
        print("   -", i)


def anfrage(modell: str) -> None:
    router_key = user_env("OMNIROUTE_API_KEY")
    status, text = call(
        "POST", "/v1/chat/completions",
        {"model": modell, "max_tokens": 16,
         "messages": [{"role": "user", "content": "Antworte mit genau: OK"}]},
        router_key,
    )
    print(f"CHAT {modell} status={status}")
    if status == 200:
        nutzlast = json.loads(text)
        print(f"   modell={nutzlast.get('model')} "
              f"inhalt={nutzlast['choices'][0]['message'].get('content','')[:60]!r} "
              f"tokens={nutzlast.get('usage')}")
    else:
        print("  ", text[:300])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--liste", action="store_true")
    parser.add_argument("--sichern", action="store_true")
    parser.add_argument("--setzen", action="store_true")
    parser.add_argument("--pruefen", action="store_true")
    parser.add_argument("--anfrage")
    parser.add_argument("--verbindung")
    parser.add_argument("--key-var", default="")
    parser.add_argument("--name")
    parser.add_argument("--base-url")
    args = parser.parse_args()
    if args.liste:
        liste()
    if args.sichern:
        sichern()
    if args.setzen:
        if not args.verbindung or not args.key_var:
            parser.error("--setzen braucht --verbindung und --key-var")
        setzen(args.verbindung, args.key_var, args.name, args.base_url)
    if args.pruefen:
        pruefen("anthropic/" if not args.verbindung else args.verbindung)
    if args.anfrage:
        anfrage(args.anfrage)
