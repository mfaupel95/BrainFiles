"""Walk-Forward fuer klassik-donchian-trend (HausSpurDonchianTrendOpt).

Je Falte: Hyperopt auf dem Lernzeitraum, dann Backtests der Sieger-Parameter
und der Haus-Vorgabe auf dem spaeteren, nie gesehenen Pruefzeitraum. Ein
Parametersatz traegt nur, wenn er die Vorgabe AUSSERHALB der Lernzeit schlaegt.

  python walkforward.py [--epochen 300] [--jobs 4]

Ergebnis: Tabelle auf stdout und user_data/walkforward.json (nicht versioniert).
Die Parameterdatei der Strategie existiert nur waehrend des Sieger-Backtests -
sonst zoege jeder spaetere Backtest sie still mit (Falle im Skill
freqtrade-strategie).

Befund 11.10.2026 (3 Falten x 300 Epochen, SharpeHyperOptLossDaily):
Lernzeit Sieger +44,8/+42,9/+8,6 % gegen Vorgabe +28,2/+25,7/-7,0 % - in der
Pruefzeit Summe -2,15 % (63 Runden) gegen Vorgabe +1,36 % (58). Die Sieger
springen (trend_n 168/273/139, kanal_aus_n 16/5/29): Ueberanpassung. Die
Haus-Wachen bleiben. Einzig stabil: kanal_ein_n 29-35 und Stop 2,8-3,5 %.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import bots

BOT = "klassik-donchian-trend"
STRATEGIE = "HausSpurDonchianTrendOpt"
VERLUST = "SharpeHyperOptLossDaily"
# Daten 30.09.2024-10.10.2026; startup 600 x 4h = 100 Tage -> nutzbar ab ~08.01.2025.
# Rollend: 8 Monate lernen, die folgenden 4 bis 5 Monate pruefen.
FALTEN = [
    ("20250108-20250901", "20250901-20260101"),
    ("20250501-20260101", "20260101-20260501"),
    ("20250901-20260501", "20260501-20261010"),
]
PARAMDATEI = bots.USER_DATA / "strategies" / f"{STRATEGIE}.json"


def daten_ordner() -> Path:
    """user_data/data des Hauptbaums - Arbeitsbaeume haben keine Kerzen."""
    gemein = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=bots.HIER,
                            capture_output=True, text=True).stdout.strip()
    haupt = (bots.HIER / gemein).resolve().parent
    return haupt / bots.HIER.relative_to(bots.HIER.parents[2]) / "user_data" / "data"


def lauf(bot, befehl, timerange, *extra, ausgabe=False):
    args = ["run", "--rm", *bots.mounts(bot),
            "-v", f"{daten_ordner().as_posix()}:{bots.IM_CONTAINER}/data:ro",
            bots.IMAGE, befehl, "--userdir", bots.IM_CONTAINER,
            "--config", f"{bots.IM_CONTAINER}/config.{BOT}.json",
            *extra]
    # hyperopt-show MIT --strategy liest keine Epochen und schreibt still
    # nichts (gemessen 11.10.2026) - es nimmt ohnehin das letzte Ergebnis.
    if befehl != "hyperopt-show":
        args += ["--strategy", STRATEGIE]
    if timerange:
        args += ["--timerange", timerange]
    r = subprocess.run(["docker", *args], capture_output=ausgabe, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(f"{befehl} {timerange}: rc {r.returncode}\n{(r.stderr or '')[-2000:]}")
    return r.stdout


def backtest(bot, timerange):
    vorher = bots._letzter_zeiger()
    lauf(bot, "backtesting", timerange, "--cache", "none", "--export", "trades")
    if bots._letzter_zeiger() in (None, vorher):
        raise RuntimeError(f"backtest {timerange}: kein neues Ergebnis")
    return bots.urteil_aus_ergebnis(bots.letztes_ergebnis(), STRATEGIE)


def falte(bot, lernen, pruefen, epochen, jobs):
    PARAMDATEI.unlink(missing_ok=True)
    lauf(bot, "hyperopt", lernen, "--hyperopt-loss", VERLUST, "--spaces", "buy", "sell",
         "-e", str(epochen), "-j", str(jobs), "--min-trades", "10",
         "--random-state", "42", "--disable-param-export")
    erg = {"lernen": lernen, "pruefen": pruefen,
           "vorgabe_lernen": backtest(bot, lernen), "vorgabe_pruefen": backtest(bot, pruefen)}
    # hyperopt-show --best schreibt die Parameterdatei selbst (im Format, das
    # der Backtest liest) - sie lebt nur fuer die beiden Sieger-Backtests.
    try:
        lauf(bot, "hyperopt-show", None, "--best", "--no-header", ausgabe=True)
        erg["params"] = json.loads(PARAMDATEI.read_text(encoding="utf-8"))["params"]
        erg["sieger_lernen"] = backtest(bot, lernen)
        erg["sieger_pruefen"] = backtest(bot, pruefen)
    finally:
        PARAMDATEI.unlink(missing_ok=True)
    return erg


def zeile(name, u):
    return (f"    {name:16} {u['runden']:4d} Runden  {u['netto_prozent']:+8.2f} %  "
            f"Ruecklauf {u['max_ruecklauf_prozent']:6.2f} %")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochen", type=int, default=300)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--falten", type=int, default=len(FALTEN))
    a = ap.parse_args(argv)
    bot = next(b for b in bots.bots() if b["name"] == BOT)
    (bots.USER_DATA / f"config.{BOT}.json").write_text(
        json.dumps(bots.config_fuer(bot), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ergebnisse = []
    for lernen, pruefen in FALTEN[:a.falten]:
        print(f"\n== Falte lernen {lernen} / pruefen {pruefen} ==", flush=True)
        e = falte(bot, lernen, pruefen, a.epochen, a.jobs)
        ergebnisse.append(e)
        (bots.USER_DATA / "walkforward.json").write_text(
            json.dumps(ergebnisse, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("\n== Ergebnis ==")
    for e in ergebnisse:
        print(f"  {e['lernen']} -> {e['pruefen']}  {json.dumps({**e['params']['buy'], **e['params']['sell']})}")
        for k in ("vorgabe_lernen", "sieger_lernen", "vorgabe_pruefen", "sieger_pruefen"):
            print(zeile(k, e[k]))
    # Der eigentliche Walk-Forward-Befund: alle Pruefzeitraeume zusammen.
    for k in ("vorgabe_pruefen", "sieger_pruefen"):
        runden = sum(e[k]["runden"] for e in ergebnisse)
        netto = sum(e[k]["netto_prozent"] for e in ergebnisse)
        print(f"  Summe {k:16} {runden:4d} Runden  {netto:+8.2f} %")
    return 0


if __name__ == "__main__":
    sys.exit(main())
