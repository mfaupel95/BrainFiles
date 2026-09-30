"""Startet omnitrade-Testnet-Laeufe - je Lauf eine Statusdatei, Doppelstart-Schutz.

Aufruf (ueber omnitrade-laeufe.cmd in der Wurzel oder direkt):
  python omnitrade_start.py liste                  Tabelle: Lauf, Strategie, Zustand
  python omnitrade_start.py start <name>|alle      fehlende Laeufe starten
  python omnitrade_start.py start <name> --trocken nur anzeigen, nichts starten

Ein Lauf gilt als laufend, wenn Statusdatei UND PID es bestaetigen
(omnitrade_lauf.beurteile). Nur dann wird NICHT gestartet - ein toter oder
`stopped`-Lauf wird neu gestartet.

Grenzen: nur Testnet (OKX-Demo, Schluessel OKX_DEMO_API_* aus der Umgebung).
Mainnet startet dieses Skript nie - Checkliste in MaxHirn/Wissen/Omnitrade.md.
Pfade relativ zur Wurzel (BrainFiles), keine absoluten.
"""

import os
import subprocess
import sys
import time

HIER = os.path.dirname(os.path.abspath(__file__))
if HIER not in sys.path:
    sys.path.insert(0, HIER)

import omnitrade_bridge as bruecke  # noqa: E402
import omnitrade_lauf as lauf  # noqa: E402

WURZEL = os.path.abspath(os.path.join(HIER, "..", ".."))
OMNI = os.environ.get("OMNITRADE_DIR") or os.path.join(WURZEL, "Werkstatt", "omnitrade")
KAPITAL_USD = 500

# name -> (Strategie ohne .omni, Symbol). Intervall je Lauf 1h (Standard).
LAEUFE = {
    "adx_macd_btc": ("adx_macd", "BTCUSDC"),
    "adx_macd_eth": ("adx_macd", "ETHUSDC"),
    "rsi30_stop5_btc": ("rsi30_stop5", "BTCUSDC"),
    "rsi30_stop5_eth": ("rsi30_stop5", "ETHUSDC"),
    "pine_sma_cross_btc": ("pine_sma_cross_20_50", "BTCUSDC"),
    "pine_ema_cross_btc": ("pine_ema_cross_12_26", "BTCUSDC"),
    "pine_macd_cross_btc": ("pine_macd_cross", "BTCUSDC"),
    "pine_rsi_meanrev_btc": ("pine_rsi_meanrev", "BTCUSDC"),
    "pine_bollinger_btc": ("pine_bollinger_breakout", "BTCUSDC"),
    "pine_donchian_btc": ("pine_donchian_20_10", "BTCUSDC"),
}
INTERVALL = "1h"

# Programme in der Reihenfolge der Vorliebe: eigener Build zuerst (laufende
# Laeufe sperren target/release, ein Neubau dort scheitert mit "Zugriff verweigert").
EXE_KANDIDATEN = ("target-live/release", "target/release", "target/debug")


def statusdatei(name):
    strategie, symbol = LAEUFE[name]
    return os.path.join(OMNI, "status", "live_%s_%s.json" % (strategie, symbol))


def programm():
    for k in EXE_KANDIDATEN:
        p = os.path.join(OMNI, k, "omnitrade-cli.exe")
        if os.path.isfile(p):
            return p
    return None


def kommandozeilen():
    """Kommandozeilen aller omnitrade-cli-Prozesse (Beweis, wer WIRKLICH laeuft -
    die Statusdatei kann von einem Duplikat ueberschrieben sein). None bei Fehler."""
    ps = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32",
                      "WindowsPowerShell", "v1.0", "powershell.exe")
    try:
        aus = subprocess.run(
            [ps, "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='omnitrade-cli.exe'\" "
             "| ForEach-Object { $_.CommandLine }"],
            capture_output=True, timeout=60)
    except Exception:
        return None
    return (aus.stdout or b"").decode("utf-8", "replace").splitlines()


def zustand(name):
    """(laeuft, Grund) - an zwei Zeugen entschieden, nie werfen. Das Alter der
    Statusdatei zaehlt hier NICHT: bei 1h-Kerzen ist sie bis zu einer Stunde alt,
    und ein lebender Prozess darf nie ein zweites Mal gestartet werden
    (30.09.2026: Testlauf startete so ein Duplikat, sofort beendet)."""
    zeilen = kommandozeilen()
    if zeilen is None:
        return True, "Prozessliste nicht lesbar - sicherheitshalber nicht starten"
    marke = "status/" + os.path.basename(statusdatei(name))
    if any(" live " in z and marke in z.replace("\\", "/") for z in zeilen):
        return True, "Prozess mit --status-file %s laeuft" % marke
    try:
        u = lauf.beurteile(bruecke.lage(statusdatei(name), veraltet_s=float("inf")),
                         alt_grenze_s=float("inf"))
        return u["laeuft"], u["grund"]
    except Exception as e:  # pragma: no cover
        return False, "Pruefung fehlgeschlagen: %s" % e


def befehl(name, exe):
    strategie, symbol = LAEUFE[name]
    return [
        exe, "live", "--exchange", "okx", "--network", "testnet",
        "--symbol", symbol, "--script", "strategien/%s.omni" % strategie,
        "--interval", INTERVALL, "--initial-capital", str(KAPITAL_USD),
        "--status-file", "status/live_%s_%s.json" % (strategie, symbol),
    ]


def starte(name, trocken=False):
    if name not in LAEUFE:
        return "unbekannt: %s (verfuegbar: %s)" % (name, ", ".join(LAEUFE))
    laeuft, grund = zustand(name)
    if laeuft:
        return "%s: laeuft schon - %s" % (name, grund)
    strategie, _ = LAEUFE[name]
    if not os.path.isfile(os.path.join(OMNI, "strategien", strategie + ".omni")):
        return "%s: Strategiedatei fehlt" % name
    exe = programm()
    if not exe:
        return "%s: kein omnitrade-cli.exe gefunden (cargo build --release -p omnitrade-cli)" % name
    for v in ("OKX_DEMO_API_KEY", "OKX_DEMO_API_SECRET", "OKX_DEMO_API_PASSPHRASE"):
        if not os.environ.get(v):
            return "%s: Umgebungsvariable %s fehlt" % (name, v)
    cmd = befehl(name, exe)
    if trocken:
        return "%s: wuerde starten: %s" % (name, " ".join(cmd))
    os.makedirs(os.path.join(OMNI, "logs"), exist_ok=True)
    log = os.path.join(OMNI, "logs", "live-%s-%s-%s.log" % (
        LAEUFE[name][0], LAEUFE[name][1], time.strftime("%Y%m%d-%H%M")))
    with open(log, "ab") as f:
        proc = subprocess.Popen(
            cmd, cwd=OMNI, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            creationflags=0x00000008 | 0x00000200,  # DETACHED_PROCESS | NEW_PROCESS_GROUP
        )
    return "%s: gestartet, PID %d, Log %s" % (name, proc.pid, log)


def liste():
    for n, (s, sym) in LAEUFE.items():
        laeuft, grund = zustand(n)
        print("%-22s %-24s %-8s %s %s" % (n, s, sym, "LAEUFT" if laeuft else "steht  ", "" if laeuft else "- " + grund))
    print("Programm: %s" % (programm() or "KEINS"))


def main(argv):
    if not argv or argv[0] == "liste":
        liste()
        return 0
    if argv[0] == "start" and len(argv) >= 2:
        trocken = "--trocken" in argv
        namen = list(LAEUFE) if argv[1] == "alle" else [argv[1]]
        for n in namen:
            print(starte(n, trocken))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
