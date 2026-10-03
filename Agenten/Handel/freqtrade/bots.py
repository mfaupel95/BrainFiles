"""Die Moon-Dev-Bots in Freqtrade einsetzen, fahren und messen.

EIN BOT = EIN CONTAINER
-----------------------
Freqtrade faehrt EINEN Bot mit EINER Strategie je Prozess. Drei Agenten
bedeuten deshalb drei Container, jeder mit eigener Konfiguration, eigener
Datenbank und eigenem Port. `bots.json` ist die Liste; dieses Werkzeug
erzeugt daraus die Konfigurationen und startet sie.

    python bots.py liste                  # Zuordnung und Zustand
    python bots.py configs                # config.<name>.json je Bot schreiben
    python bots.py daten [name ...]       # Kerzen laden, die der Backtest braucht
    python bots.py backtest [name ...]    # Backtest, Ergebniszeile
    python bots.py start  [name ...]      # Container starten (Probelauf)
    python bots.py stop   [name ...]      # Container beenden
    python bots.py status                 # was laeuft

WARUM PYTHON UND KEIN SHELL-SKRIPT
----------------------------------
Der Haus-Standard fuer Routinen ist PowerShell, aber hier werden Pfade an ein
Windows-Programm (docker) uebergeben, und in bash/MSYS sind genau dafuer schon
Fehler passiert (Backtick-Sequenzen, Pfaduebersetzung, `-o` als Parameter).
Python gibt den Pfad in EINER Form aus und ist mit unittest pruefbar
(tests/test_bots.py).

WAS DIESES WERKZEUG NICHT TUT
-----------------------------
Es handelt nicht und es fasst den laufenden Container `freqtrade` nicht an.
Der laeuft weiter mit SampleStrategy (Fremdprozess, nicht meiner). Backtests
und Downloads laufen in EINWEG-Containern (`--rm`) und stoeren deshalb keinen
laufenden Bot.

Zugangsdaten: die erzeugten Konfigurationen tragen eigene Zufallswerte je Bot
(lokal, an 127.0.0.1 gebunden) und stehen NUR in der Datei - dieses Werkzeug
gibt sie nie aus.
"""

from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent
USER_DATA = HIER / "user_data"
STRATEGIEN = USER_DATA / "strategies"
MANIFEST = HIER / "bots.json"

IMAGE = "freqtradeorg/freqtrade:stable"

# Im Container heisst das Benutzerverzeichnis immer gleich (Mountpunkt).
IM_CONTAINER = "/freqtrade/user_data"


# --- Manifest ---------------------------------------------------------------

def manifest() -> dict:
    """Das Manifest lesen. Fehlt es, ist das ein Fehler - keine leere Liste."""
    if not MANIFEST.exists():
        raise SystemExit(f"Manifest fehlt: {MANIFEST}")
    with MANIFEST.open(encoding="utf-8") as f:
        return json.load(f)


def bots() -> list[dict]:
    return manifest().get("bots", [])


def bot_mit_name(name: str) -> dict:
    for b in bots():
        if b["name"] == name:
            return b
    bekannt = ", ".join(b["name"] for b in bots())
    raise SystemExit(f"Kein Bot '{name}'. Bekannt: {bekannt}")


def ausgewaehlt(argumente: list[str]) -> list[dict]:
    """Die genannten Bots, oder alle wenn nichts genannt ist."""
    if not argumente:
        return bots()
    return [bot_mit_name(n) for n in argumente]


# --- Pfade ------------------------------------------------------------------

def mount_pfad() -> str:
    """Das Benutzerverzeichnis als Pfad fuer docker.

    `as_posix()` liefert `C:/Users/...` - genau die Form, mit der der
    vorhandene start.sh arbeitet. Ein Backslash-Pfad ist auf Windows je nach
    Shell-Aufrufer schon an der Uebersetzung gescheitert.
    """
    return USER_DATA.resolve().as_posix()


# --- Docker -----------------------------------------------------------------

def docker(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def container_laeuft(name: str) -> bool:
    r = docker(["inspect", "-f", "{{.State.Running}}", name])
    return r.returncode == 0 and r.stdout.strip() == "true"


def einweglauf(fenster: list[str], beschriftung: str) -> int:
    """Ein Docker-Lauf in einem Wegwerf-Container. Gibt den Exitcode zurueck."""
    print(f"  docker {' '.join(fenster[:4])} …  ({beschriftung})")
    r = subprocess.run(["docker", *fenster], text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


# --- Konfiguration je Bot ---------------------------------------------------

def _basis_exchange() -> dict:
    """Die exchange-Schluessel der Basis-config.json (Schluessel, kein Geheimnis).

    Die Aufsaetze tragen bewusst KEINE eigenen Boersen-Schluessel - die
    gehoeren der Basis, und ein Aufsatz, der sie leer setzt, wuerde sie beim
    tiefen Merge der Container zunichte machen (gemessen 01.10.2026: die
    Container laden config.json + config.<name>.json, ein leeres key/secret
    im Aufsatz hebelt das echte aus der Basis aus).
    """
    pfad = USER_DATA / "config.json"
    if not pfad.exists():
        return {}
    try:
        with pfad.open(encoding="utf-8") as f:
            return json.load(f).get("exchange", {}) or {}
    except (OSError, ValueError):
        return {}


def config_fuer(bot: dict) -> dict:
    """Die Konfiguration EINES Bots.

    Bewusst NICHT die vorhandene config.json kopiert: die traegt Zugangsdaten
    einer anderen Sitzung und einen anderen Port. Jeder Bot bekommt eigene
    Zufallswerte, damit zwei Bots nie denselben Zugang teilen (dieselbe Lehre
    wie bei den Telegram-Kanaelen der Bot-Profile).

    Die Boersen-Schluessel kommen aus der Basis-config.json (siehe
    `_basis_exchange`), damit ein Aufsatz beim tiefen Merge nichts aushebelt.
    """
    port = int(bot["port"])
    name = bot["name"]
    basis_exchange = _basis_exchange()
    return {
        "max_open_trades": int(bot.get("max_open_trades", 3)),
        "stake_currency": "USDT",
        "stake_amount": "unlimited",
        "tradable_balance_ratio": 0.99,
        "dry_run": True,
        "initial_state": "running",
        "dry_run_wallet": 10000,
        "trading_mode": "spot",
        "timeframe": bot.get("zeitrahmen", "1h"),
        "strategy": bot["strategie"],
        "exchange": {
            "name": "binance",
            "key": basis_exchange.get("key", ""),
            "secret": basis_exchange.get("secret", ""),
            "pair_whitelist": list(bot["whitelist"]),
            "pair_blacklist": [],
        },
        "entry_pricing": {"price_side": "same", "use_order_book": True,
                          "order_book_top": 1},
        "exit_pricing": {"price_side": "same", "use_order_book": True,
                         "order_book_top": 1},
        "pairlists": [{"method": "StaticPairList"}],
        "unfilledtimeout": {"entry": 10, "exit": 10, "unit": "minutes"},
        "api_server": {
            "enabled": True,
            "listen_ip_address": "0.0.0.0",
            "listen_port": port,
            "jwt_secret_key": secrets.token_hex(32),
            "ws_token": secrets.token_urlsafe(24),
            "CORS_origins": [],
            "username": "max",
            "password": secrets.token_urlsafe(18),
        },
        "telegram": {"enabled": False, "token": "", "chat_id": ""},
        "bot_name": f"freqtrade-{name}",
        "db_url": f"sqlite:///{IM_CONTAINER}/tradesv3.{name}.sqlite",
        "logfile": f"{IM_CONTAINER}/logs/{name}.log",
        "internals": {"process_throttle_secs": 5},
        # Schalter der Moon-Dev-Strategien (moondev_basis.MoonDevBasis).
        # `signal_ausstieg` aus = nur Stop, Ziel und Schutzschicht entscheiden.
        # Vorgabe ist die Strategie selbst; hier steht sie ausdruecklich, damit
        # ein Backtest-Lauf sie ueberschreiben kann, ohne die Datei zu aendern.
        "moondev": {"signal_ausstieg": bool(bot.get("signal_ausstieg", True))},
    }


def schreibe_configs(ziele: list[dict]) -> int:
    USER_DATA.mkdir(parents=True, exist_ok=True)
    (USER_DATA / "logs").mkdir(exist_ok=True)
    for b in ziele:
        pfad = USER_DATA / f"config.{b['name']}.json"
        pfad.write_text(json.dumps(config_fuer(b), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        # Nie die Werte ausgeben - nur, dass die Datei steht.
        print(f"  ✓ config.{b['name']}.json  (Strategie {b['strategie']}, "
              f"Port {b['port']}, {len(b['whitelist'])} Paare)")
    return 0


# --- Unterbefehle -----------------------------------------------------------

def cmd_liste() -> int:
    m = manifest()
    print("BOTS (startbar)")
    print(f"  {'Name':<18} {'Strategie':<22} {'Port':<6} {'Rahmen':<7} Paare")
    for b in m["bots"]:
        print(f"  {b['name']:<18} {b['strategie']:<22} {b['port']:<6} "
              f"{b.get('zeitrahmen', '1h'):<7} {len(b['whitelist'])}")
    print()
    print("ALS SCHUTZSCHICHT PORTIERT (kein eigener Bot)")
    for s in m.get("als_schutzschicht_portiert", []):
        print(f"  {s['agent']}  ->  {s['wo']}")
    print()
    print(f"NICHT PORTIERBAR ({len(m.get('nicht_portierbar', []))} Eintraege)")
    for n in m.get("nicht_portierbar", []):
        print(f"  {n['agent']}")
        print(f"      {n['hindernis']}")
    return 0


def cmd_configs(argumente: list[str]) -> int:
    print("Konfigurationen schreiben:")
    return schreibe_configs(ausgewaehlt(argumente))


def _daten_fenster(paare: list[str], zeitrahmen: str) -> list[str]:
    return [
        "run", "--rm",
        "-v", f"{mount_pfad()}:{IM_CONTAINER}",
        IMAGE,
        "download-data", "--userdir", IM_CONTAINER,
        "-p", *paare,
        "-t", zeitrahmen,
        "--days", "400",
    ]


def cmd_daten(argumente: list[str]) -> int:
    """Kerzen laden, die der Backtest der Bots braucht.

    Alle Pairlisten zusammen, damit kein Bot ohne Daten dasteht.
    """
    paare: list[str] = []
    zeitrahmen: set[str] = set()
    for b in ausgewaehlt(argumente):
        for p in b["whitelist"]:
            if p not in paare:
                paare.append(p)
        zeitrahmen.add(b.get("zeitrahmen", "1h"))
        for p in b.get("breite_paare", []):
            if p not in paare:
                paare.append(p)
    print(f"{len(paare)} Paare, Zeitrahmen {sorted(zeitrahmen)}, 400 Tage")
    rc = 0
    for tf in sorted(zeitrahmen):
        rc |= einweglauf(_daten_fenster(paare, tf), f"download-data {tf}")
    return rc


def cmd_backtest(argumente: list[str], timerange: str | None = None,
                 signal: str | None = None) -> int:
    """Je Bot ein Backtest, mit der Ergebniszeile am Ende.

    `--cache none` und keine Hyperopt-Datei: sonst zieht ein Lauf still eine
    alte Optimierung (Falle im Skill freqtrade-strategie).

    `--signal-ausstieg an|aus` schreibt eine ZWEITE Konfiguration und faehrt
    damit - so ist die Frage "traegt der Signal-Ausstieg?" messbar, ohne den
    Code zu aendern und ohne die Konfiguration des Bots anzufassen.
    """
    rc = 0
    for b in ausgewaehlt(argumente):
        cfg_pfad = USER_DATA / f"config.{b['name']}.json"
        hinweis = ""
        if signal is not None:
            cfg_pfad = USER_DATA / f"config.{b['name']}.signal-{signal}.json"
            variante = config_fuer(b)
            variante["moondev"] = {"signal_ausstieg": (signal == "an")}
            cfg_pfad.write_text(
                json.dumps(variante, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
            hinweis = f"  [Signal-Ausstieg {signal}]"
        print(f"\n══ Backtest {b['name']} ({b['strategie']}){hinweis} ══")
        fenster = [
            "run", "--rm",
            "-v", f"{mount_pfad()}:{IM_CONTAINER}",
            IMAGE,
            "backtesting", "--userdir", IM_CONTAINER,
            "--config", f"{IM_CONTAINER}/{cfg_pfad.name}",
            "--strategy", b["strategie"],
            "--cache", "none",
            "--export", "trades",
        ]
        if timerange:
            fenster += ["--timerange", timerange]
        rc |= einweglauf(fenster, f"backtesting {b['name']}")
    return rc


def cmd_start(argumente: list[str]) -> int:
    rc = 0
    for b in ausgewaehlt(argumente):
        name = b["container"]
        cfg = USER_DATA / f"config.{b['name']}.json"
        if not cfg.exists():
            print(f"  ✗ {b['name']}: config fehlt - erst 'python bots.py configs'")
            rc |= 1
            continue
        if container_laeuft(name):
            print(f"  · {b['name']}: laeuft schon ({name})")
            continue
        # Alten, beendeten Container desselben Namens wegnehmen.
        docker(["rm", "-f", name])
        fenster = [
            "run", "-d", "--name", name, "--restart", "unless-stopped",
            "-v", f"{mount_pfad()}:{IM_CONTAINER}",
            "-p", f"127.0.0.1:{b['port']}:{b['port']}",
            IMAGE,
            "trade",
            "--config", f"{IM_CONTAINER}/config.{b['name']}.json",
        ]
        r = docker(fenster)
        if r.returncode != 0:
            print(f"  ✗ {b['name']}: {r.stderr.strip()[:200]}")
            rc |= 1
        else:
            print(f"  ✓ {b['name']}: gestartet ({name}, Port {b['port']})")
    return rc


def cmd_stop(argumente: list[str]) -> int:
    rc = 0
    for b in ausgewaehlt(argumente):
        r = docker(["rm", "-f", b["container"]])
        if r.returncode == 0:
            print(f"  ✓ {b['name']}: beendet")
        else:
            print(f"  · {b['name']}: war nicht da")
    return rc


def _api_stand(bot: dict) -> str:
    """Kurzlage eines Bots ueber seine eigene API. Lesend, nur aus der eigenen
    Konfiguration. Ist der Bot nicht erreichbar, ist das eine Zeile, kein Abbruch.
    """
    pfad = USER_DATA / f"config.{bot['name']}.json"
    if not pfad.exists():
        return "keine config"
    with pfad.open(encoding="utf-8") as f:
        cfg = json.load(f)
    # Der Zugang kommt aus dem AUFSATZ (config.<name>.json): der traegt die
    # EIGENEN Zugangsdaten des Bots, und der Starter laedt genau diese Datei
    # in den Container. Die Container akzeptieren sie (gemessen 02.10.2026:
    # show_config 200 mit dem Aufsatz-Passwort, 401 mit dem Basis-Passwort auf
    # 8081-8083) - die Basis-config.json ist hier NICHT mehr die Anmeldung.
    api = cfg.get("api_server", {})
    zugang = api
    import base64
    roh = f"{zugang.get('username', '')}:{zugang.get('password', '')}".encode()
    kopf = {"Authorization": "Basic " + base64.b64encode(roh).decode()}
    url = f"http://127.0.0.1:{api.get('listen_port')}/api/v1/"
    teile = []
    for endpunkt in ("ping", "count", "profit"):
        try:
            req = urllib.request.Request(url + endpunkt, headers=kopf)
            with urllib.request.urlopen(req, timeout=5) as a:
                daten = json.loads(a.read().decode())
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            teile.append(f"{endpunkt}={type(e).__name__}")
            continue
        if endpunkt == "ping":
            teile.append("erreichbar" if daten.get("status") else "keine Antwort")
        elif endpunkt == "count":
            teile.append(f"{daten.get('current', '?')} offen")
        else:
            g = daten.get("profit_closed_coin")
            teile.append(f"Gewinn {g:+.4f}" if isinstance(g, (int, float)) else "Gewinn ?")
    return ", ".join(teile)


def cmd_status() -> int:
    for b in bots():
        laeuft = container_laeuft(b["container"])
        zustand = "laeuft" if laeuft else "aus"
        api = _api_stand(b) if laeuft else "—"
        print(f"  {b['name']:<18} {zustand:<7} {api}")
    return 0


# --- Einstieg ---------------------------------------------------------------

def haupt(argv: list[str]) -> int:
    if not argv or argv[0] in ("-h", "--help", "hilfe"):
        print(__doc__)
        return 0
    befehl, rest = argv[0], argv[1:]
    timerange = None
    if "--timerange" in rest:
        i = rest.index("--timerange")
        timerange = rest[i + 1] if i + 1 < len(rest) else None
        rest = rest[:i] + rest[i + 2:]
    signal = None
    if "--signal-ausstieg" in rest:
        i = rest.index("--signal-ausstieg")
        wert = rest[i + 1] if i + 1 < len(rest) else ""
        if wert not in ("an", "aus"):
            print("--signal-ausstieg braucht 'an' oder 'aus'.")
            return 2
        signal = wert
        rest = rest[:i] + rest[i + 2:]

    if befehl == "liste":
        return cmd_liste()
    if befehl == "configs":
        return cmd_configs(rest)
    if befehl == "daten":
        return cmd_daten(rest)
    if befehl == "backtest":
        return cmd_backtest(rest, timerange, signal)
    if befehl == "start":
        return cmd_start(rest)
    if befehl == "stop":
        return cmd_stop(rest)
    if befehl == "status":
        return cmd_status()
    print(f"Unbekannter Befehl '{befehl}'. Siehe --help.")
    return 2


if __name__ == "__main__":
    raise SystemExit(haupt(sys.argv[1:]))