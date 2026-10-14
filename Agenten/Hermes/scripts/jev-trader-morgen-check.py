# jev-trader Status-Wache (Hermes-Cron "jev-trader-morgen-check", taeglich ~08:30).
# Prueft: laeuft der Bot, ist events.jsonl frisch, wie viel MON ist in der Wallet.
# Watchdog-Muster: leere Ausgabe = nichts senden. Bei Problemen wird der Befund gemeldet.
# Anker: Agenten/Hermes/scripts -> BrainFiles.
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
WURZEL = HIER.parents[2]
BOT_ORDNER = WURZEL / "Werkstatt" / "jev-trader"
CACHE = HIER.parent / "cache"
MERK = CACHE / "jev-trader-morgen-check.json"

def bot_laeuft():
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'bun' -and $_.CommandLine -match 'index.ts' } | Select-Object -ExpandProperty ProcessId"],
            capture_output=True, text=True, timeout=60,
        ).stdout
        pids = [int(x) for x in out.split() if x.strip().isdigit()]
        return pids
    except Exception:
        return []

def events_frisch():
    try:
        from datetime import datetime as dt
        lines = (BOT_ORDNER / "data" / "events.jsonl").read_text(encoding="utf-8", errors="ignore").strip().splitlines()
        if not lines:
            return False, None
        letzter = json.loads(lines[-1])
        alter_min = (datetime.now(timezone.utc).timestamp() * 1000 - letzter["ts"]) / 60000
        return True, round(alter_min, 1)
    except Exception:
        return False, None

def mon_stand():
    try:
        skript = (
            "import { ethers } from 'ethers';\n"
            "import { config } from './src/config.ts';\n"
            "const rpc = new ethers.providers.JsonRpcProvider(config.rpcUrl);\n"
            "const w = new ethers.Wallet(config.privateKey, rpc);\n"
            "console.log(ethers.utils.formatEther(await w.getBalance()));\n"
        )
        tmp = BOT_ORDNER / "jev-bal.mjs"  # im Bot-Ordner, damit ./src/config.ts aufloest
        tmp.write_text(skript, encoding="utf-8")
        out = subprocess.run(
            [str(WURZEL / "Agenten" / "Hermes" / "tools" / "bun" / "bun.exe"), str(tmp)],
            capture_output=True, text=True, timeout=60, cwd=str(BOT_ORDNER),
        ).stdout.strip()
        tmp.unlink(missing_ok=True)
        return round(float(out), 1) if out else None
    except Exception:
        return None

def main():
    pids = bot_laeuft()
    frische_events, alter_min = events_frisch()
    mon = mon_stand()

    meldungen = []
    if not pids:
        meldungen.append("Bot laeuft NICHT (kein bun-Prozess mit src/index.ts)")
    if frische_events and alter_min is not None and alter_min > 60:
        meldungen.append(f"events.jsonl ist {alter_min} min alt -> Bot haengt oder ist tot")
    if not frische_events:
        meldungen.append("events.jsonl fehlt oder ist leer")
    if mon is None:
        meldungen.append("MON-Stand nicht lesbar")
    elif mon < 100:
        meldungen.append(f"MON fast aufgebraucht: {mon} (Nachladen noetig)")

    # Merkdatei: nur bei Aenderung neu melden
    vorher = {}
    if MERK.exists():
        try:
            vorher = json.loads(MERK.read_text(encoding="utf-8"))
        except Exception:
            vorher = {}

    jetzt = {"pid_vorhanden": bool(pids), "alter_min": alter_min, "mon": mon}
    if meldungen and json.dumps(vorher.get("meldungen")) != json.dumps(meldungen):
        print("Jev-Trader Status:\n" + "\n".join("- " + m for m in meldungen))
        MERK.write_text(json.dumps({"meldungen": meldungen, "jetzt": jetzt}, ensure_ascii=False), encoding="utf-8")
    elif mon is not None and vorher.get("mon") and mon - vorher["mon"] > 200:
        # MON wurde nachgeladen -> kurze Bestaetigung einmalig
        print(f"Jev-Trader: MON nachgeladen ({vorher['mon']} -> {mon}), Bot {'laeuft' if pids else 'LÄUFT NICHT'}")
        MERK.write_text(json.dumps({"meldungen": meldungen, "jetzt": jetzt}, ensure_ascii=False), encoding="utf-8")
    else:
        MERK.write_text(json.dumps({"meldungen": meldungen, "jetzt": jetzt}, ensure_ascii=False), encoding="utf-8")

if __name__ == "__main__":
    main()
