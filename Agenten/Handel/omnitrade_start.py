"""Startet omnitrade-Testnet-Laeufe - je Lauf eine Statusdatei, Doppelstart-Schutz.

Aufruf (ueber omnitrade-laeufe.cmd in der Wurzel oder direkt):
  python omnitrade_start.py liste                       Tabelle: Lauf, Strategie, Zustand
  python omnitrade_start.py start <name>|alle           fehlende Laeufe starten
  python omnitrade_start.py start <name> --trocken      nur anzeigen, nichts starten
  python omnitrade_start.py start <name> --symbol ETHUSDC
  python omnitrade_start.py start <name> --intervall 1d

`<name>` ist ENTWEDER ein benannter Lauf aus LAEUFE (mit festem Symbol) ODER
der Name einer Datei in `Werkstatt/omnitrade/strategien/` ohne `.omni`. Damit ist
jede der 41 Strategien startbar, ohne dass hier eine zweite Liste gepflegt wird
(die Datei auf der Platte ist die Wahrheit). Benanntes Symbol und Vorgabe
BTCUSDC - der Lauf schreibt dann `status/live_<strategie>_<symbol>.json`.

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
    "ema_cross_btc": ("ema_cross_20_50", "BTCUSDC"),
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
    "rsi_noema_btc": ("rsi_noema", "BTCUSDC"),
}
INTERVALL = "1h"
# Abweichendes Intervall je benanntem Lauf (sonst INTERVALL).
INTERVALL_JE_LAUF = {
    "rsi_noema_btc": "15m",
    "ema_cross_btc": "1d",
    "adx_macd_btc": "1d",
    "adx_macd_eth": "1d",
    "pine_sma_cross_btc": "1d",
    "pine_ema_cross_btc": "1d",
    "pine_macd_cross_btc": "1d",
    "pine_donchian_btc": "1d",
}
STANDARD_SYMBOL = "BTCUSDC"

# Programme in der Reihenfolge der Vorliebe: eigener Build zuerst (laufende
# Laeufe sperren target/release, ein Neubau dort scheitert mit "Zugriff verweigert").
EXE_KANDIDATEN = ("target-live/release", "target/release", "target/debug")


def strategien():
    """Namen aller Strategiedateien in `strategien/` (ohne Endung), sortiert."""
    ordner = os.path.join(OMNI, "strategien")
    try:
        return sorted(n[:-5] for n in os.listdir(ordner) if n.endswith(".omni"))
    except OSError:
        return []


def aufloesen(name, symbol=None):
    """(Strategie, Symbol) zu einem Namen - benannter Lauf zuerst, sonst jede
    Strategiedatei auf der Platte. None, wenn beides nicht passt."""
    if name in LAEUFE:
        strategie, sym = LAEUFE[name]
        return strategie, (symbol or sym)
    if name in strategien():
        return name, (symbol or STANDARD_SYMBOL)
    return None


def statusdatei(name, symbol=None):
    paar = aufloesen(name, symbol)
    if paar is None:
        return None
    strategie, sym = paar
    # Der ema_cross-Lauf ist der ETABLIERTE Hauptlauf des Hauses: er schreibt
    # `status/live.json` (Standard der Bruecke, des omnitrade.cmd-Status und der
    # Handelszentrale-Kopfzeile), nicht `live_<strategie>_<symbol>.json`. Sonst
    # bliebe die alte live.json als Leiche stehen und die Wache meldete ewig
    # "kein Lebenszeichen", obwohl der Lauf laeuft (Befund 07.10.2026).
    if strategie == "ema_cross_20_50" and sym == "BTCUSDC":
        return os.path.join(OMNI, "status", "live.json")
    return os.path.join(OMNI, "status", "live_%s_%s.json" % (strategie, sym))


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
            capture_output=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    except Exception:
        return None
    return (aus.stdout or b"").decode("utf-8", "replace").splitlines()


def zustand(name, symbol=None):
    """(laeuft, Grund) - an zwei Zeugen entschieden, nie werfen. Das Alter der
    Statusdatei zaehlt hier NICHT: bei 1h-Kerzen ist sie bis zu einer Stunde alt,
    und ein lebender Prozess darf nie ein zweites Mal gestartet werden
    (30.09.2026: Testlauf startete so ein Duplikat, sofort beendet)."""
    datei = statusdatei(name, symbol)
    if datei is None:
        return False, "unbekannter Name: %s" % name
    zeilen = kommandozeilen()
    if zeilen is None:
        return True, "Prozessliste nicht lesbar - sicherheitshalber nicht starten"
    marke = "status/" + os.path.basename(datei)
    if any(" live " in z and marke in z.replace("\\", "/") for z in zeilen):
        return True, "Prozess mit --status-file %s laeuft" % marke
    try:
        # KEIN `veraltet_s=inf` mehr (30.09.2026): mit unendlicher Altersgrenze
        # galt eine 4,5 Stunden alte Statusdatei als lebender Lauf, und weil
        # Windows die PID inzwischen neu vergeben hatte (sie gehoerte csrss.exe),
        # meldete die Pruefung "laeuft schon" - der tote Lauf wurde nie neu
        # gestartet. Jetzt gilt die Altersgrenze aus dem Kerzenabstand UND die
        # PID muss zum Programm gehoeren.
        u = lauf.beurteile(bruecke.lage(datei),
                           lebt=lambda p: lauf.pid_lebt(p, "omnitrade-cli.exe"))
        return u["laeuft"], u["grund"]
    except Exception as e:  # pragma: no cover
        return False, "Pruefung fehlgeschlagen: %s" % e


def befehl(name, exe, symbol=None, intervall=None):
    strategie, sym = aufloesen(name, symbol)
    # Der Statusdatei-Pfad kommt aus `statusdatei()` - nur dort steht die
    # Ausnahme, dass ema_cross_20_50/BTCUSDC die Standard-Datei `live.json`
    # schreibt (Handelszentrale-Kopf, omnitrade.cmd-Status und Lauf-Wache
    # lesen diesen Standard). Inline gebaut, wuerde der Lauf eine zweite
    # Datei `live_ema_cross_20_50_BTCUSDC.json` schreiben und die alte
    # live.json bliebe als Leiche liegen (Befund 07.10.2026).
    status = statusdatei(name, symbol)
    return [
        exe, "live", "--exchange", "okx", "--network", "testnet",
        "--symbol", sym, "--script", "strategien/%s.omni" % strategie,
        "--interval", intervall or INTERVALL_JE_LAUF.get(name, INTERVALL),
        "--initial-capital", str(KAPITAL_USD),
        "--status-file", status,
    ]


def starte(name, trocken=False, symbol=None, intervall=None):
    paar = aufloesen(name, symbol)
    if paar is None:
        return "unbekannt: %s (benannte Laeufe: %s; sonst jede Datei in strategien/)" % (
            name, ", ".join(LAEUFE))
    strategie, sym = paar
    laeuft, grund = zustand(name, sym)
    if laeuft:
        return "%s: laeuft schon - %s" % (name, grund)
    if not os.path.isfile(os.path.join(OMNI, "strategien", strategie + ".omni")):
        return "%s: Strategiedatei fehlt" % name
    exe = programm()
    if not exe:
        return "%s: kein omnitrade-cli.exe gefunden (cargo build --release -p omnitrade-cli)" % name
    for v in ("OKX_DEMO_API_KEY", "OKX_DEMO_API_SECRET", "OKX_DEMO_API_PASSPHRASE"):
        if not os.environ.get(v):
            return "%s: Umgebungsvariable %s fehlt" % (name, v)
    cmd = befehl(name, exe, sym, intervall)
    if trocken:
        return "%s: wuerde starten: %s" % (name, " ".join(cmd))
    os.makedirs(os.path.join(OMNI, "logs"), exist_ok=True)
    log = os.path.join(OMNI, "logs", "live-%s-%s-%s.log" % (
        strategie, sym, time.strftime("%Y%m%d-%H%M")))
    with open(log, "ab") as f:
        proc = subprocess.Popen(
            cmd, cwd=OMNI, stdout=f, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            creationflags=0x00000008 | 0x00000200,  # DETACHED_PROCESS | NEW_PROCESS_GROUP
        )
    return "%s: gestartet, PID %d, Log %s" % (name, proc.pid, log)


def liste():
    for n, (s, sym) in LAEUFE.items():
        laeuft, grund = zustand(n)
        print("%-22s %-24s %-8s %s %s" % (n, s, sym, "LAEUFT" if laeuft else "steht  ",
                                          "" if laeuft else "- " + grund))
    print("Weitere startbar (jede Datei in strategien/): %d Strategien" % len(strategien()))
    print("Programm: %s" % (programm() or "KEINS"))


def main(argv):
    if not argv or argv[0] == "liste":
        liste()
        return 0
    if argv[0] == "start" and len(argv) >= 2:
        trocken = "--trocken" in argv
        symbol = _wert(argv, "--symbol")
        intervall = _wert(argv, "--intervall")
        namen = list(LAEUFE) if argv[1] == "alle" else [argv[1]]
        for n in namen:
            print(starte(n, trocken, symbol, intervall))
        return 0
    print(__doc__)
    return 2


def _wert(argv, schalter):
    if schalter in argv:
        i = argv.index(schalter)
        if i + 1 < len(argv):
            return argv[i + 1]
    return None


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))