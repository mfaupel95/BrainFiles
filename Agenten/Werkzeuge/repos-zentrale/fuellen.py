"""Das Manifest fuellen: jeden Ordner und jedes Werkzeug der Wurzeln aufnehmen.

Warum ein Werkzeug und keine Handarbeit: die Wurzeln wachsen (46 Repos, 45
Ordner in Handel, 21 in der Werkstatt) und ein neuer Klon soll nicht unbemerkt
bleiben. Zwei Regeln gelten dabei unveraendert:

1. **Kein geratener Befehl.** Ein `start` kommt nur aus `START` unten - und was
   dort steht, ist vorher wirklich gelaufen (Beleg in `logs/`).
2. **Die eigene Quelle schlaegt die Erfindung.** Eine Notiz wird aus README oder
   Modul-Docstring des Projekts gelesen; `KURATIERT` ueberschreibt sie nur, wo
   die Quelle nichts Brauchbares hergibt.

    .venv\\Scripts\\python.exe fuellen.py             # Trockenlauf
    .venv\\Scripts\\python.exe fuellen.py --anwenden  # schreiben (mit .bak)
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import quellen  # noqa: E402
import scan  # noqa: E402

# ------------------------------------------------------------------ Kuratiert
# Rolle je Eintrag. Kurz, ein Wort, in der Spalte "Rolle" sichtbar.
# `gruppe: doku` heisst: kein Programm, nur Text oder Daten - es soll nicht als
# "EINRICHTEN" erscheinen, nur weil kein Startbefehl daran haengt.
ABLAGE = {"rolle": "Ablage", "gruppe": "doku"}

KURATIERT: dict[tuple[str, str], dict] = {
    # ------------------------------------------------------------- REPOS
    # Rolle der 46 Klone: die Spalte war ohne Eintrag durchgehend "-".
    **{
        ("repos", name): {"rolle": rolle}
        for name, rolle in (
            ("Agent-Reach", "Werkzeug"), ("agent-trade-kit", "MCP-Server"),
            ("awesome-deepseek-harness-plugins", "Liste"), ("awesome-dsh-plugin", "Liste"),
            ("awesome-systematic-trading", "Liste"), ("basic-memory", "Werkzeug"),
            ("caveman", "Installer"), ("claude-code", "Doku"),
            ("claude-plugins-official", "Doku"), ("claude-red", "Skills"),
            ("claudian", "Plugin"), ("codex", "Werkzeug"),
            ("deepseek-harness", "Werkzeug"), ("EasyCLIProxyAPI", "App"),
            ("everything-claude-code", "Doku"), ("fast-jev-compaction", "Plugin"),
            ("fomo-robinhood-radar", "Werkzeug"), ("foreman", "Werkzeug"),
            ("gbrain", "Werkzeug"), ("graphify", "Werkzeug"),
            ("Harvard-Algorithmic-Trading-with-AI", "Doku"),
            ("intelligent-trading-bot", "Pruefstand"), ("jev-chat-jarvis", "App (Android)"),
            ("jev-trader", "Bot"), ("kraken-cli", "Werkzeug"), ("Kronos", "Modell"),
            ("laya", "Modell"), ("moon-dev-ai-agents", "Werkzeug"),
            ("Moon-Dev-Code", "Doku"), ("obsidian-skills", "Skills"),
            ("odysseus", "Werkzeug"), ("one-skill-to-rule-them-all", "Skills"),
            ("openmontage", "Werkzeug"), ("OpenTerminal", "Werkzeug"),
            ("OpenTerminalUI", "Terminal"), ("osiris", "Dashboard"),
            ("ProjectAtlas", "Werkzeug"), ("robinhood-fomo-kronos-arena", "Rahmen"),
            ("santiment", "Doku"), ("Scrapling", "Bibliothek"), ("skills", "Doku"),
            ("superpowers", "Skills"), ("tradememory-protocol", "MCP-Server"),
            ("Trading-View-MCP-for-AI-by-Moon-Dev", "MCP-Server"),
            ("winget-cli", "Doku"), ("ziplime", "Backtest"),
        )
    },
    # ------------------------------------------------------------- WERKSTATT
    # ("werkstatt", "omnitrade") steht weiter unten bei den gemessenen Starts.
    ("werkstatt", "OmniRoute"): {
        "rolle": "Projekt",
        "notiz": "Lokaler Modell-Router (Next.js) auf Port 20128 - traegt Subagenten und "
                 "die Bot-Profile; faellt er aus, scheitern alle delegate_task",
    },
    ("werkstatt", "freqtrade"): {
        "rolle": "Projekt",
        "notiz": "Freqtrade-Bot-Suite in Docker, dry_run: Basiscontainer 8080, "
                 "trading-agent 8081, topmovers 8082, marktlage-regime 8083",
    },
    ("werkstatt", "handel-stack"): {
        "rolle": "Spiegel (18.09.)",
        "notiz": "Privater GitHub-Spiegel von Agenten/Handel, Stand 18.09.2026: 33 damals 48 Spuren "
                 "samt Journalen und Zustand - ein eingefrorener Altstand, NICHT der lebende Baum",
        "warnungen": ["Altstand 18.09.2026 - nichts liest ihn; der lebende Baum liegt in "
                      "Agenten/Handel (spuren_stand.py zeigt ihn)"],
    },
    ("werkstatt", "intelligent-trading-bot"): {
        "rolle": "Projekt",
        # KEIN Duplikat: die Wurzel `repos` erreicht DIESEN Ordner ueber eine
        # Junction (`Werkstatt\intelligent-trading-bot` -> hierher). Eine
        # physische Ablage, zwei Zeilen im Fenster. Die alte Notiz ("Zweite
        # Ablage") war falsch und hat am 30.09.2026 fast dazu gefuehrt, den
        # Ordner als Duplikat wegzuraeumen - ein Doppel-Scan ueber Junctions
        # findet sonst denselben Inhalt zweimal.
        "notiz": "ML-Backtest-Pruefstand (dieselbe Ablage wie Werkstatt/intelligent-trading-bot: "
                 "die Wurzel Repos erreicht diesen Ordner ueber eine Junction)",
        "warnungen": ["Junction-Ziel von Werkstatt/intelligent-trading-bot - eine physische "
                      "Ablage, kein zweites Exemplar"],
    },
    ("repos", "intelligent-trading-bot"): {
        # Die zweite Zeile DESSELBEN Ordners (siehe oben) - der Start steht
        # hier, die Herkunft dort.
        "warnungen": ["Junction auf Werkstatt/intelligent-trading-bot - eine physische "
                      "Ablage, kein zweites Exemplar (nicht als Duplikat wegraeumen)"],
    },
    # Repos mit einer GEMESSEN laufenden Binary auf der Platte (05.10.2026).
    # `start` traegt hier die Gebrauchsanweisung, nicht das Angebot zu laufen:
    # `--help` beendet sich, legt nichts an und braucht keinen Schluessel. Erst
    # mit dem Beleg in logs/ darf so ein Befehl im Manifest stehen (T-085).
    ("repos", "kraken-cli"): {
        "start": ["target\\release\\kraken.exe", "--help"],
        "pfad_pflicht": "target\\release\\kraken.exe",
    },
    ("repos", "fomo-robinhood-radar"): {
        "start": [".venv\\Scripts\\fomo-radar.exe", "--help"],
    },
    ("repos", "laya"): {
        "start": [".venv\\Scripts\\python.exe", "verify\\laya_smoke_test.py", "--help"],
    },
    ("werkstatt", "omnitrade"): {
        "rolle": "Projekt",
        "notiz": "Rust-Workspace (Klon jackby03/omnitrade, AGPL-3.0): backtest, validate, "
                 "live, kill - privat gesichert als mfaupel95/omnitrade",
        # 05.10.2026 gemessen: `target\\release\\omnitrade-cli.exe --help` laeuft
        # und endet mit Exit 0. `pfad_pflicht` macht die Zeile zum EINRICHTEN,
        # sobald der Ordner ohne Bau dasteht - dann fehlt genau diese Datei.
        "start": ["target\\release\\omnitrade-cli.exe", "--help"],
        "pfad_pflicht": "target\\release\\omnitrade-cli.exe",
    },
    ("werkstatt", "CryptoPredictions"): {
        "rolle": "Projekt",
        "notiz": "Fremd-Klon: Krypto-Vorhersagemodelle (Anhaengsel einer Handelsreihe)",
    },
    ("werkstatt", "CryptoTrade"): {
        "rolle": "Projekt",
        "notiz": "Fremd-Klon: LLM-Agent fuer Zero-Shot-Krypto-Handel",
    },
    ("werkstatt", "FinRL"): {
        "rolle": "Projekt",
        "notiz": "Fremd-Klon: FinRL - Reinforcement Learning fuer Finanzhandel",
    },
    ("werkstatt", "RLTrader"): {
        "rolle": "Projekt",
        "notiz": "Fremd-Klon: RLTrader, der Vorgaenger von TensorTrade",
    },
    ("werkstatt", "skillspector"): {
        "rolle": "Werkzeug",
        "notiz": "SkillSpector - prueft Skill-Sammlungen (Node + Python + Makefile)",
    },
    ("werkstatt", "scrapling-wissen"): {
        "rolle": "Ablage",
        "gruppe": "doku",
        "notiz": "Handelswissen-Ernte mit Scrapling - Ablage der Ernte, kein Programm",
    },
    ("werkstatt", "security-skills-claude-code"): {
        "rolle": "Skills",
        "gruppe": "doku",
        "notiz": "Security-Skills fuer Claude Code - Nachschlagewerk, kein Programm",
    },
    ("werkstatt", "trailofbits-skills"): {
        "rolle": "Skills",
        "gruppe": "doku",
        "notiz": "Trail-of-Bits-Skill-Marktplatz - Nachschlagewerk, kein Programm",
    },
    ("werkstatt", "Ausgabe"): dict(ABLAGE, notiz="Ausgaben und Berichte"),
    ("werkstatt", "Ausgemustert"): dict(ABLAGE, notiz="Ausgemusterte Staende"),
    ("werkstatt", "Austausch"): dict(
        ABLAGE, notiz="Durchgangsordner fuer Uebergaben, zuletzt der Systempruefungslauf"
    ),
    ("werkstatt", "Protokolle"): dict(ABLAGE, notiz="Protokolle abgeschlossener Laeufe"),
    ("werkstatt", "Sitzungen"): dict(ABLAGE, notiz="Aufzeichnungen einzelner Arbeitssitzungen"),
    ("werkstatt", "Worktrees"): dict(ABLAGE, notiz="Arbeitsbaeume fuer parallele Sitzungen"),
    ("werkstatt", "repos-verschoben-aus-skills"): dict(
        ABLAGE,
        notiz="Fremd-Klone, die aus Agenten/Hermes/skills herausgezogen wurden "
              "(unsloth, nautilus_trader, public-apis ...) - nichts geloescht",
    ),
    ("werkstatt", "zustand-sicherung-20260916-015331"): dict(
        ABLAGE, notiz="Zustandssicherung vom 16.09.2026 01:53 vor dem Hermes-Umbau"
    ),
    # ---------------------------------------------------- WERKSTATT/PROJEKTE
    ("projekte", "Daten"): dict(ABLAGE, notiz="Datenfeld der Projekte"),
    ("projekte", "GGUF"): dict(ABLAGE, notiz="Quantisierte Modellgewichte (GGUF)"),
    ("projekte", "HuggingFace"): dict(ABLAGE, notiz="HuggingFace-Ablage der Projekte"),
    ("projekte", "Checkpoints"): dict(ABLAGE, notiz="Trainings-Checkpoints"),
    ("projekte", "Invest"): dict(
        ABLAGE, notiz="Anlage-Unterlagen; eigene LIESMICH.md im Ordner"
    ),
    ("projekte", "NautilusTrader"): dict(
        ABLAGE, notiz="NautilusTrader-Daten und -Laeufe der Handels-Spuren"
    ),
    ("projekte", "OmniRoute"): dict(
        ABLAGE, notiz="OmniRoute-Projektstand; die laufende Installation liegt unter "
                      "Werkstatt/OmniRoute"
    ),
    ("projekte", "skill-automatik"): dict(ABLAGE, notiz="Skill-Automatik: Zuarbeit und Skripte"),
    ("projekte", "workflow"): dict(ABLAGE, notiz="Arbeitsablaeufe der Projekte"),
    # ------------------------------------------------------------- HANDEL
    ("handel", "OpenAlice"): {
        # Die ROLLE kommt aus Agenten/FREMD-Liste.json (eine Quelle) - hier steht
        # nur, was die Liste nicht weiss: dass es als Ablage in der Doku-Gruppe
        # steht und was es in einem Satz ist.
        "gruppe": "doku",
        "notiz": "Fremdes Quant-Framework mit eigenem Baum (545 MB, 482 .py, 513.266 "
                 "Zeilen = 81 % der Zeilen in Agenten/Handel) - nur oeffnen, wenn die "
                 "Aufgabe ausdruecklich OpenAlice betrifft",
    },
    ("handel", "ai4trade"): {
        "rolle": "Werkzeug",
        "notiz": "Anbindung an ai4trade.ai (Papier-Signalplattform): Agent HermesMax2, "
                 "Heartbeat-Poller und Anlage-Werkzeug",
    },
    ("handel", "bt_opt"): {
        "rolle": "Werkzeug",
        "notiz": "Gegenprobe der Empfehlungen aus backtest-optimierung-2026-09-21.md",
    },
    ("handel", "freqtrade"): {
        "rolle": "Werkzeug",
        "notiz": "Die Moon-Dev-Bots in Freqtrade einsetzen, fahren und messen "
                 "(Strategien, Aufsaetze, Startskript)",
        # Der einzige Bot-Betrieb des Hauses mit einer WEB-OBERFLAECHE. Der
        # Startknopf zeigt die Zuordnung (welche Strategie auf welchem Port),
        # die Web-UIs sind eigene Befehle - sie setzen die laufenden Container
        # voraus und oeffnen nur den Browser.
        "start": ["..\\.venv\\Scripts\\python.exe", "bots.py", "liste"],
        "befehle": [
            {"was": "Web-UI trading-agent (Port 8081)", "cmd": ["cmd", "/c",
             "start \"\" http://127.0.0.1:8081"], "hinweis": "Zugang in user_data/config.json"},
            {"was": "Web-UI topmovers (Port 8082)", "cmd": ["cmd", "/c",
             "start \"\" http://127.0.0.1:8082"], "hinweis": "24 Paare, 1 h"},
            {"was": "Web-UI marktlage-regime (Port 8083)", "cmd": ["cmd", "/c",
             "start \"\" http://127.0.0.1:8083"], "hinweis": "1 Paar, 1 h"},
            {"was": "Bots starten (Docker, drei Container)", "cmd": ["bash",
             "bots_starten.sh"], "hinweis": "dry_run=true - kein Geld"},
            {"was": "Zustand der Container", "cmd": ["docker", "ps",
             "--filter", "name=freqtrade", "--format",
             "{{.Names}} {{.Status}} {{.Ports}}"], "hinweis": "leer = keiner laeuft"},
        ],
    },
    ("handel", "nautilus-rust"): {
        "rolle": "Werkzeug",
        "notiz": "Rust-Arm der Nautilus-Reihe (Cargo-Workspace)",
    },
    ("handel", "nautilus_rc5"): {
        "rolle": "Werkzeug",
        "notiz": "Rauchproben fuer nautilus_trader 2.0.0rc5 gegen das Kraken-Spotkonto",
    },
    ("handel", "okx_bot_waechter"): {
        "rolle": "Werkzeug",
        "notiz": "Waechter der OKX-Future-Bots: Leiter, Munition, Liquidation, Vorschlag "
                 "'letzte kaufbare Grenze' mit Stop (Eingriff nur mit --anwenden)",
        # Der Bericht ist der Sinn des Ordners. Ohne --anwenden stoppt er nichts
        # (zwei Tore davor: stop_erlaubt in wachen.json und der Schalter selbst).
        "start": ["..\\.venv\\Scripts\\python.exe", "waechter.py"],
    },
    ("handel", "verbesserer"): {
        "rolle": "Werkzeug",
        "notiz": "Selbstverbesserung: Anfragen sammeln und anwenden (der Dauerlauf ruft es)",
        # Die Werkzeuge dieses Ordners stehen EINZELN darueber (lauf.py). Der
        # Ordner selbst ist kein Programm - deshalb KEIN EIGENER START statt
        # EINRICHTEN.
        "gruppe": "kein_start",
        "warnungen": ["kein eigenes Programm: die Werkzeuge (lauf.py) stehen einzeln darueber"],
    },
    ("handel", "ai4trade"): {
        "rolle": "Werkzeug",
        "notiz": "ai4trade.ai: Papierhandel auf einer Signalplattform (Agent HermesMax2)",
        "gruppe": "kein_start",
        "warnungen": ["kein eigenes Programm: heartbeat.py und neu_anlegen.py stehen einzeln darueber"],
    },
    ("handel", "bt_opt"): {
        "rolle": "Werkzeug",
        "notiz": "Gegenproben zu den Backtest-Optimierungen (4h_gegenprobe.py, verify_equivalence.py)",
        "gruppe": "kein_start",
        "warnungen": ["kein eigenes Programm: die beiden Gegenproben stehen einzeln darueber"],
    },
    ("handel", "nautilus-rust"): {
        "rolle": "Werkzeug",
        "notiz": "Rust-Arm der Nautilus-Reihe (Cargo-Workspace: omnitrade-risk, quant-alpha, "
                 "quant-planes, quant-signal, quant-strategy)",
        "gruppe": "kein_start",
        "warnungen": ["Cargo-Workspace ohne Startbefehl (cargo build/test)"],
    },
    ("handel", "nautilus_rc5"): {
        "rolle": "Werkzeug",
        "notiz": "Rauchproben fuer nautilus_trader 2.0.0rc5 gegen das Kraken-Spotkonto",
        "gruppe": "kein_start",
        "warnungen": ["Rauchproben gegen das ECHTE Kraken-Konto - kein Klick-Start"],
    },
    ("handel", "backtest_laeufe"): dict(
        ABLAGE, notiz="Ergebnisse der Backtest-Laeufe aus dem Leitstand (je Lauf eine JSON)"
    ),
    ("handel", "prognose_berichte"): dict(
        ABLAGE, notiz="Taegliche Prognose-Berichte (neuester.json) - Eingang der Spur omniquant"
    ),
    ("handel", "stand"): dict(ABLAGE, notiz="Tagesstaende des Handels"),
    # Spuren: Rolle setzen, Notiz kommt aus dem eigenen README
    **{
        ("handel", name): {"rolle": "Spur"}
        for name in (
            "gitter", "iv_waelle", "iv_wand", "kopier", "kopier1zu1", "kraken", "liq_wand",
            "macd_mtf", "moondev_funding", "moondev_liquidation", "moondev_listingarb",
            "moondev_marktlage", "moondev_sentiment", "moondev_signalwelle", "moondev_sniper",
            "moondev_topmovers", "moondev_whale", "mosaic", "nautilus", "nautilus_kraken",
            "omniquant", "orb", "orbk", "robinhood_radar", "scanner", "spiegel", "squeeze",
            "supertrend", "swap", "trendwende_btc", "wavetrend", "xperp",
        )
    },
    # Klassik-Spuren (30.09.2026): Pine-Regeln als Papierbuch, Kern klassik_regeln.py
    **{
        ("handel", name): {"rolle": "Spur", "notiz": notiz + " (Papier, 4H, BTC/ETH/SOL)"}
        for name, notiz in (
            ("klassik_sma", "SMA-Kreuz 20/50"),
            ("klassik_ema", "EMA-Kreuz"),
            ("klassik_macd", "MACD-Signalkreuz"),
            ("klassik_bollinger", "Bollinger-Ausbruch"),
            ("klassik_donchian", "Donchian-Ausbruch, Kanal vor der Kerze"),
            ("klassik_rsi", "RSI-Mean-Reversion"),
            ("klassik_rsi2", "Connors RSI(2) mit SMA200-Filter, Ausstieg SMA5"),
            ("klassik_donchian_trend", "Donchian nur in Richtung der EMA200"),
        )
    },
}

# Der Bereich HANDEL hat eine Besonderheit: die wichtigsten Werkzeuge liegen als
# EINZELDATEIEN in der Wurzel. Sie bekommen einen Startbefehl, der nichts tut
# ausser die Gebrauchsanweisung zu zeigen - und der vorher wirklich gelaufen ist.
# Der Pfad wird mit Backslash eingesetzt (Hausschreibweise im Manifest); Python
# versteht auf Windows beide Trenner.
HILFE_START = [".venv\\Scripts\\python.exe", "{pfad}", "--help"]

# NUR diese Dateien bekommen den Hilfe-Start. Der Grund ist die Hausregel
# "kein geratener Befehl": verifiziert ist, was einmal gelaufen ist. Eine neue
# Datei in der Wurzel erscheint dadurch als Zeile OHNE Startbefehl - das ist der
# ehrliche Zustand, und ein Aufruf kommt erst nach einem echten Lauf dazu
# (`fuellen.py --belege` fuehrt jeden hinterlegten, noch unbelegten Start aus).
#
# Schluessel sind die Pfade innerhalb der Wurzel (mit "/"), nicht die Dateinamen:
# `auswertung.py` gibt es in fuenf Spuren, `backtest.py` in zweien.
HILFE_VERIFIZIERT = (
    "agent.py", "auswertung_alle.py", "auswertung_trading.py", "backtest_prognose.py",
    "backtest_urteile.py", "beleg_hand.py", "bt_varianten_fast.py", "dca.py",
    "dca_auswertung.py", "filter_studie.py", "freigabe.py", "freigabefenster.py",
    "gesamtbilanz.py", "grid.py", "handelszentrale.py", "historie_binance.py",
    "journal_pos_id_nachziehen.py", "kerzenschluss_bias.py", "kosten_wendepunkt.py", "llm_probe.py",
    "moondev_historie.py", "okx_waisen.py", "optimieren.py", "papierbuch_schliessen.py",
    "prognose.py", "reinvest.py", "replay.py", "santiment_daten.py",
    "sperrgruende.py", "spiegelstand.py", "spuren_stand.py", "stille_spuren.py",
    "stoerungen.py", "tagesbericht.py", "testlauf.py", "vergleich.py",
    "wochenbericht.py", "zeitversatz_messen.py",
    # Werkzeuge neben den Spuren (30.09.2026) - alle mit __main__ + argparse,
    # jede Zeile hier hat einen echten Lauf in logs/.
    "okx_bot_waechter/analyse.py", "okx_bot_waechter/vorschlag.py",
    "okx_bot_waechter/bauen.py", "scanner/stops_bereinigen.py",
    "scanner/boersenstops.py", "xperp/geister_nachziehen.py",
    "xperp/fremde_positionen_uebernehmen.py", "kraken/abgleich.py",
    "kraken/einsatz_nachziehen.py", "mosaic/geist_zurueckbuchen.py",
    "mosaic/boersenabgleich.py", "ai4trade/heartbeat.py", "verbesserer/lauf.py",
    "nautilus/daten_auffrischen.py", "nautilus/backtest_grid.py",
    "kerzenschluss_bias.py",
    "orb/backtest.py", "orbk/backtest.py",
    "gitter/backtest_gitter.py", "xperp/historie.py",
    "gitter/auswertung.py", "kopier/auswertung.py", "kopier1zu1/auswertung.py",
    "omniquant/auswertung.py", "spiegel/auswertung.py",
    # Werkzeuge der Wurzel, 05.10.2026 - jeder Eintrag unten ist am 05.10.2026
    # mit `.venv\\Scripts\\python.exe <datei> --help` ECHT gelaufen (Exit 0),
    # die Belegdatei steht in logs/. `melder.py` und `kraken_abweisungs_sonde.py`
    # fehlen hier ABSICHTLICH: sie stehen in OHNE_START (Telegram-Seiteneffekt
    # bzw. echter Kraken-Aufruf) und duerfen nicht ueber den Startknopf laufen.
    "5m_historie_holen.py", "dpi_fall.py", "gebuehr_boerse_abgleich.py",
    "gebuehren_setzen.py", "leitstand_messprobe.py", "messprobe.py",
    "modus_nachtragen.py", "okx_positionen_live.py", "okx_tp_stufen.py",
    "spur_audit.py", "stapel_raeumen.py", "universum_messen.py",
)

# Zweite Runde der Kuratierung: die Spuren, deren README mit einem Halbsatz
# anfaengt, und die Werkzeugdateien. Was hier steht, ist Hauswissen - es wird
# nicht aus der Datei gelesen, weil die Datei es nicht hergibt.
KURATIERT.update({
    ("handel", "gitter"): {
        "rolle": "Spur",
        "notiz": "Gitter-Spur: kauft auf fallenden Stufen. Befund 15.09.2026 - das Gitter "
                 "folgt der Marktrichtung (Korrelation +0,78), gewinnt in fallenden Fenstern "
                 "und verliert in steigenden; die 52-Wochen-Mittel bleibt negativ",
    },
    ("handel", "iv_wand"): {
        "rolle": "Spur",
        "notiz": "Strike mit dem groessten Open Interest als Wand (OKX-Optionen, Verfall "
                 "7-45 Tage); long/short nur, wenn der Spot hoechstens 5 % daneben liegt",
    },
    ("handel", "iv_waelle"): {
        "rolle": "Spur",
        "notiz": "Wie iv_wand, aber Ausstieg an der Spannengrenze: Stop hinter die Wand, "
                 "Ziel der halbe Rueckweg (Deribit-IV)",
    },
    ("handel", "kraken"): {
        "rolle": "Spur",
        "notiz": "Spur 3 - Kraken-Spot, nur long, Waehrung je Paar (EUR, USDC, EURC); ordert "
                 "seit 22.09.2026 nicht selbst, sondern stellt einen Freigabe-Beleg aus",
    },
    ("handel", "kopier"): {
        "rolle": "Spur",
        "notiz": "Copy-Trading der Pump.fun-Rangliste (Papierbuch); am 24.09.2026 stillgelegt, "
                 "das Buch bleibt als Vergleichsgrundlage stehen",
    },
    ("handel", "kopier1zu1"): {
        "rolle": "Spur",
        "notiz": "1:1-Copy-Trade auf Trade-Ereignissen statt auf einem Portfolio-Diff "
                 "(Papierbuch); am 24.09.2026 stillgelegt",
    },
    ("handel", "liq_wand"): {
        "rolle": "Spur",
        "notiz": "Wand aus Zwangsschluessen (OKX-Liquidationen, groesstes Preisband der letzten "
                 "~78 min) - die Spur geht MIT dem Cluster, weil geschlossene Shorts Kaufdruck sind",
    },
    ("handel", "macd_mtf"): {
        "rolle": "Spur",
        "notiz": "MACD auf zwei Zeitrahmen - Trendfolge nur bei Einigkeit; braucht 600 "
                 "Basiskerzen, seit der Nachblaetterung am 15.09.2026 vorhanden",
    },
    ("handel", "moondev_signalwelle"): {
        "rolle": "Spur",
        "notiz": "Bot-Spur signalwelle (Papier): Einbrueche im Marktquerschnitt als Signal",
    },
    ("handel", "moondev_sniper"): {
        "rolle": "Spur",
        "notiz": "Bot-Spur sniper (Papier): Einzelkandidaten des MoonDev-Agenten",
    },
    ("handel", "mosaic"): {
        "rolle": "Spur",
        "notiz": "4H-Bias, 30M-Pullback zur Nachfragezone, 5M-Structure-Shift - die einzige "
                 "Spur mit zwei Boersen (Kraken EUR und OKX USDC), Ausstieg bindet die "
                 "Boerse der Position",
    },
    ("handel", "nautilus"): {
        "rolle": "Spur",
        "notiz": "NautilusTrader-Arm (OKX-Demo): Stop -19,8 %, Trailing ab +10 % mit 6 % "
                 "Abstand, Frist 48 h; bucht Kopier-Kaeufe als BTC-Proxy",
    },
    ("handel", "nautilus_kraken"): {
        "rolle": "Spur",
        "notiz": "Kraken-Arm der Nautilus-Reihe (EUR); Schwesterarme sind nautilus (OKX) und "
                 "nautilus_kraken_futures (USD, PF_XBTUSD)",
    },
    ("handel", "omniquant"): {
        "rolle": "Spur",
        "notiz": "Handelt die Treffer des Prognose-Berichts als Papierbuch; Hauptarm liest seit "
                 "24.09.2026 die weiche Fassung (prognose_fassung=weit)",
    },
    ("handel", "orb"): {
        "rolle": "Spur",
        "notiz": "Opening Range Breakout auf BTC-/ETH-USDT-SWAP, 00:00-UTC-Grenze - der eigene "
                 "Backtest ist fuer beide Instrumente negativ, die Spur laeuft nur zur Beobachtung",
    },
    ("handel", "orbk"): {
        "rolle": "Spur",
        "notiz": "Opening Range Breakout auf Kraken (dieselbe Strategie wie orb, andere Boerse); "
                 "seit 21.09.2026 sind die Schwellen so gesetzt, dass die ETH-Range greift",
    },
    ("handel", "robinhood_radar"): {
        "rolle": "Spur",
        "notiz": "Papierbuch auf bewerteten Wallets der Robinhood Chain - liest NUR die "
                 "fomo-radar-Datenbank, nie die Rangliste; kein Orderweg",
    },
    ("handel", "scanner"): {
        "rolle": "Spur",
        "notiz": "Marktscanner - die einzige Spur mit belegtem Vorteil (t=15,3 bei 125 echten "
                 "Runden). Handelt live ueber OKX mit Boersen-Stop, Papier und Live im selben Buch",
    },
    ("handel", "spiegel"): {
        "rolle": "Spur",
        "notiz": "Papierbuch fuer Copy-Trading (Pump.fun-Rangliste); am 21.09.2026 abgeschaltet, "
                 "das Buch bleibt als Vergleichsgrundlage. Wieder einschalten nur mit frischem "
                 "letzter_lauf, sonst wird alles flachgestellt",
    },
    ("handel", "squeeze"): {
        "rolle": "Spur",
        "notiz": "Volatilitaetskompression, die sich loest (Squeeze-Momentum)",
    },
    ("handel", "supertrend"): {
        "rolle": "Spur",
        "notiz": "SuperTrend-Richtungswechsel, die Linie dient als Stop",
    },
    ("handel", "swap"): {
        "rolle": "Spur",
        "notiz": "SWAP-Spur mit Live-Pfad; am 27.09.2026 auf Papier zurueckgesetzt (4 echte "
                 "Runden, 0 % Treffer, -8,2 %) - der Schalter war wirkungslos, es gibt keinen "
                 "Orderaufruf im Code",
    },
    ("handel", "trendwende_btc"): {
        "rolle": "Spur",
        "notiz": "BTC short, sobald der SuperTrend auf 1H dreht - nur unter der EMA200; ein "
                 "Rueckdreh beendet die Position (erste Spur mit Rueckdreh-Ausstieg)",
    },
    ("handel", "wavetrend"): {
        "rolle": "Spur",
        "notiz": "Wavetrend-Umkehr im ueberzogenen Bereich",
    },
    ("handel", "xperp"): {
        "rolle": "Spur",
        "notiz": "XPERP-Bot: OKX-Perpetuals mit Zonenrechnung und wartenden Limit-Auftraegen "
                 "(ein Limit hinter dem Markt ist kein Fehler); Live-Grenzen 80 USD je Anlauf, "
                 "600 USD gesamt, Hoechststrafe 30 USD Buchrisiko",
    },
    # ------------------------------------------------- Werkzeugdateien
    ("handel", "handelszentrale.py"): {
        "rolle": "Werkzeug",
        # Die beiden Fenster des Hauses bekommen einen KLICK-Start: sie sind
        # UIs, und eine UI ohne Startknopf ist in einer Startzentrale fehl am
        # Platz. Gestartet wird mit pythonw.exe - sonst steht neben dem Fenster
        # noch eine schwarze Konsole.
        "start": [".venv\\Scripts\\pythonw.exe", "handelszentrale.py"],
        "anleitung": "Das lesende Fenster ueber alle Spuren (Positionen, Kursweg, Konsole, "
                     "Kopfzeile mit Dauerlauf-PID). Es schreibt NICHTS - dauerlauf.py bleibt "
                     "der einzige Schreiber.\n\n"
                     "Von Hand: .venv\\Scripts\\pythonw.exe handelszentrale.py (Fenster) oder "
                     "handelszentrale.py --pruefen (ohne Fenster). --risiko mittel|hoch zeigt "
                     "eine Risikostufe, --schrift N stellt die Schriftgroesse ein.",
    },
    ("handel", "dauerlauf.py"): {
        "rolle": "Betrieb",
        "anleitung": "Der 24/7-Betrieb: fuehrt alle Spuren, spiegelt nach Q: und meldet an "
                     "Telegram. Die Wahrheit, welche Spur laeuft, steht im Dict SPUREN "
                     "(ab Zeile 140).\n\n"
                     "Start NUR ueber die geplanten Aufgaben (MaxHirn-Handel-Dauerlauf, "
                     "-Waechter, -Mittel-, -Hoch-Waechter) oder den Wrapper "
                     "Routinen/handel-dauerlauf.ps1. Ein Handstart nimmt die echte Sperre und "
                     "schreibt ins echte Protokoll.",
    },
    ("handel", "tagesbericht.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Ein Bild aller Spuren fuer das Handy. --risiko mittel|hoch|alle liest eine "
                     "Risikostufe (Vorgabe: Basis), --senden schickt je Stufe eine eigene "
                     "Telegram-Nachricht. Ohne --senden passiert nichts nach draussen.",
    },
    ("handel", "spuren_stand.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Tafel aller Spuren: erlaubt, Freigabefenster, Live-Pfad, Buch, Runden. "
                     "Rein lesend - der schnellste Weg zu 'was laeuft und was ist gesperrt'.",
    },
    ("handel", "spiegelstand.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Bedingung 4: vergleicht jede Handelsspur BYTE-GENAU mit der Kopie unter "
                     "Q:\\Handel_Journal\\<spur>. Rein lesend. --risiko prueft eine Stufe mit.",
    },
    ("handel", "auswertung_alle.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Wertet die Spuren aus, die keine eigene auswertung.py haben. Rechnet auf "
                     "ECHTEN Handelsrunden; Zwangsschluesse (Herzschlag, Notaus) stehen getrennt "
                     "daneben. --risiko waehlt die Stufe.",
    },
    ("handel", "sperrgruende.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Sperrgruende aller Spuren aus ihrer EIGENEN Vorschau - markiert, wo nur "
                     "das Freigabefenster fehlt (das ist die Bedingung, unter der die "
                     "Auto-Freigabe greift).",
    },
    ("handel", "pruefe_ratschen.py"): {
        "rolle": "Werkzeug",
        "start": [".venv\\Scripts\\python.exe", "pruefe_ratschen.py"],
        "anleitung": "Tafel der Drawdown-Ratsche je Spur. Fragt jede Spur ueber ihr EIGENES "
                     "lage() - eine nachgebaute Formel wuerde die Formel pruefen, nicht die "
                     "Spur. Die Spalte '1.0x?' prueft, dass der Betrag nicht davongelaufen ist.",
    },
    ("handel", "strategie_kennzahlen.py"): {
        "rolle": "Werkzeug",
        "start": [".venv\\Scripts\\python.exe", "strategie_kennzahlen.py"],
        "anleitung": "t-Statistik der Expectancy und Stop-Vorschlag aus der MAE der Gewinner - "
                     "je Spur. Laeuft im Handel-venv (.venv), weil numpy/pandas gebraucht werden; "
                     "das scanner-venv hat sie nicht.",
    },
    ("handel", "freigabe.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Das Bildschirm-Freigabefenster: bestaetigt ein Scharfschalten, das eine "
                     "Spur anfragt. Live wird NIE aus Chat oder Telegram scharf geschaltet - "
                     "nur hier oder per /ja_<spur> im Dauerlauf.",
    },
    ("handel", "beleg_hand.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Die HAND: fuehrt einen Freigabe-Beleg aus (Kraken-Order ueber das MCP-Tor). "
                     "Vorschau ist Standard, --anwenden fuehrt wirklich aus. Ein Beleg ist "
                     "einmalig und laeuft nach 180 s ab.",
    },
    ("handel", "leitstand.py"): {
        "rolle": "Werkzeug",
        "start": [".venv\\Scripts\\pythonw.exe", "leitstand.py"],
        "anleitung": "Das grosse Fenster: Ueberwachen, Freigaben, Backtests, Markt und Urteile in "
                     "einem. Handelt nie live.\n\n"
                     ".venv\\Scripts\\pythonw.exe leitstand.py",
    },
    ("handel", "testlauf.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Faehrt jede Testsuite des Handel-Baums und meldet die Abweichungen. Der "
                     "Hausweg, wenn nach einer Aenderung die Wirkung belegt werden soll.",
    },
    ("handel", "replay.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Backtest-Kern: die Spur entscheidet, der Replay liefert nur Kerzen und "
                     "stellt die Uhr. Zwei Familien (A: Buch im Modul, B: spur_buch.zyklus) und "
                     "der Feed-Querschnitt (lauf_feed, lauf_c).",
    },
    ("handel", "optimieren.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Walk-Forward-Suche je Spur auf dem Backtest-Fundament; die Suchtabelle "
                     "steht in spur_opt.json. Ein Optimierlauf ohne Walk-Forward ist keine Messung.",
    },
    ("handel", "okx_waisen.py"): {
        "rolle": "Werkzeug",
        "anleitung": "OKX-Wartung: findet Schutz-Orders, deren Position bzw. Bestand es nicht "
                     "mehr gibt. Vorschau ist Standard.",
    },
    ("handel", "papierbuch_schliessen.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Bucht Papier-Altlasten aus den Kraken-Buechern aus (Positionen ohne "
                     "Boersensatz). Vorschau ist Standard, --anwenden schreibt.",
    },
    ("handel", "journal_pos_id_nachziehen.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Zieht die Spalte pos_id in vorhandene Journale nach - bis alle 94 "
                     "Journal-Schreiber sie tragen (offener Punkt T-226).",
    },
    ("handel", "beobachte_live.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Beobachtet die offenen Scanner-Positionen (USDC-Spot) und meldet "
                     "Bewegungen. Rein lesend, laeuft bis zum Abbruch.",
    },
    ("handel", "kraken_abweisungs_sonde.py"): {
        "rolle": "Werkzeug",
        "anleitung": "Sonde: misst vier Wege (offen/signiert x Spot/Futures) und unterscheidet "
                     "damit 'Netz' von 'Schluessel'. Nach einer Abweisung 60 min Kuehlzeit - "
                     "jeder weitere Versuch setzt den Kraken-Lockout-Timer zurueck.",
    },
    ("handel", "agent.py"): {
        "rolle": "Werkzeug",
        "anleitung": "DCA-Agent: verwaltet mehrere Sparplaene und bereitet Kaeufe VOR - der "
                     "Vorbereitungsschritt ist die Grenze zur Order.",
    },
})

# Dritte Runde (30.09.2026 abends): die Werkzeuge NEBEN den Spuren und die
# Freqtrade-Strategien. Schluessel ist hier der PFAD innerhalb der Wurzel, weil
# `auswertung.py` in fuenf Spuren liegt und `backtest.py` in zweien.
KURATIERT.update({
    # ------------------------------------------- Wartung und Betrieb
    ("handel", "okx_bot_waechter/analyse.py"): {
        "rolle": "Werkzeug",
        "notiz": "Misst je OKX-Bot die Leiter (Tiefe = Stufen x Abstand) gegen das Instrument "
                 "und empfiehlt neue Zahlen; --woche nimmt den uebergeordneten Trend dazu",
    },
    ("handel", "okx_bot_waechter/vorschlag.py"): {
        "rolle": "Werkzeug",
        "notiz": "Rechnet einen neuen DCA-Bot durch (Tiefe aus ATR, Stop am Planboden) - "
                 "--tiefe auto; ein neuer Bot bringt seinen Stop mit",
    },
    ("handel", "okx_bot_waechter/bauen.py"): {
        "rolle": "Werkzeug",
        "warnungen": ["legt einen echten OKX-Bot an - nur mit bauen_erlaubt=true UND --anwenden"],
        "notiz": "Legt einen Bot an, wahlweise aus vorschlag.py; ohne --anwenden passiert nichts",
    },
    ("handel", "scanner/stops_bereinigen.py"): {
        "rolle": "Werkzeug",
        "notiz": "Raeumt die Stop-Merker der scanner-Zustandsdatei auf (Vorschau Standard, "
                 "--anwenden schreibt, --stornieren nimmt Waisenstops von der Boerse)",
    },
    ("handel", "scanner/boersenstops.py"): {
        "rolle": "Werkzeug",
        "notiz": "Buch gegen BOERSE: hat jede Live-Position ihren Stop, steht sie ueberhaupt "
                 "noch, gibt es Waisen-Stops - laeuft im Live-Zyklus mit",
    },
    ("handel", "xperp/geister_nachziehen.py"): {
        "rolle": "Werkzeug",
        "notiz": "Zieht Geister-Zeilen (grund buchbereinigung_geist, Erloes genau 0.00) auf den "
                 "Einsatz zurueck, den die FIFO-Paarung verrechnet - Vorschau Standard",
    },
    ("handel", "xperp/fremde_positionen_uebernehmen.py"): {
        "rolle": "Werkzeug",
        "notiz": "Nimmt Positionen ins Buch, die an der Boerse stehen, aber (noch) nicht im Buch",
    },
    ("handel", "kraken/abgleich.py"): {
        "rolle": "Werkzeug",
        "notiz": "Kraken-Buch gegen die Boerse (Arten GEIST/TEILS/WAISE); bucht nur mit BELEGTEM "
                 "Boersenerloes aus, ohne Zeugen bleibt die Position und heisst 'unklar'",
    },
    ("handel", "kraken/einsatz_nachziehen.py"): {
        "rolle": "Werkzeug",
        "notiz": "Stellt den Einsatz in Belegzeilen richtig (Menge x Preis statt Stueckpreis) - "
                 "vier ueber die Hand ausgefuehrte Belege standen um Faktor 30 zu klein im Buch",
    },
    ("handel", "mosaic/geist_zurueckbuchen.py"): {
        "rolle": "Werkzeug",
        "notiz": "Holt eine falsch gebuchte Live-Position zurueck ins Buch (Vorschau Standard); "
                 "die Falschbuchung wandert nach handelsjournal.verworfen-<datum>.csv",
    },
    ("handel", "mosaic/boersenabgleich.py"): {
        "rolle": "Werkzeug",
        "notiz": "Buch gegen Boerse fuer mosaic (Kraken-Spot und OKX-Spot)",
    },
    ("handel", "ai4trade/heartbeat.py"): {
        "rolle": "Werkzeug",
        "notiz": "Pollt den Heartbeat von ai4trade.ai und meldet nur Neues (leere Ausgabe = "
                 "nichts zu senden); laeuft als Cron ueber Agenten/Hermes/scripts/",
    },
    ("handel", "verbesserer/lauf.py"): {
        "rolle": "Werkzeug",
        "notiz": "Faehrt die gesammelten Verbesserungs-Anfragen ab - der Dauerlauf ruft es bei "
                 "Bedarf selbst auf",
    },
    ("handel", "nautilus/daten_auffrischen.py"): {
        "rolle": "Werkzeug",
        "notiz": "Zieht die Kursdaten der Nautilus-Arme nach (die Arme buchen Kopier-Kaeufe als "
                 "BTC-Proxy)",
    },
    # ------------------------------------------- Backtests
    ("handel", "orb/backtest.py"): {
        "rolle": "Backtest",
        "notiz": "Backtest der ORB-Spur auf OKX-Perps - der eigene Befund ist fuer beide "
                 "Instrumente NEGATIV (EV -45.1 Pkt je Runde bei BTC)",
    },
    ("handel", "orbk/backtest.py"): {
        "rolle": "Backtest",
        "notiz": "Backtest der ORB-Spur auf Kraken (dieselbe Strategie wie orb)",
    },
    ("handel", "gitter/backtest_gitter.py"): {
        "rolle": "Backtest",
        "notiz": "Faehrt gitter/handeln.py SELBST (keine Nachbildung) - sonst optimiert man die "
                 "Nachbildung; die Leiter entsteht nur beim Erstlauf",
    },
    ("handel", "nautilus/backtest_grid.py"): {
        "rolle": "Backtest",
        "notiz": "Grid-Backtest auf den eigenen Kursdaten (nautilus/daten/)",
        "warnungen": ["braucht nautilus_trader aus nautilus/.venv, nicht das Handel-venv "
                      "(der Import scheitert sonst schon bei --help)"],
    },
    ("handel", "xperp/historie.py"): {
        "rolle": "Werkzeug",
        "notiz": "Kurshistorie fuer den xperp-Backtest - spur-eigen, NICHT die gemeinsame "
                 "historie_binance.py",
    },
    # ------------------------------------------- Auswertungen je Spur
    ("handel", "gitter/auswertung.py"): {
        "rolle": "Werkzeug",
        "notiz": "Wertet das Gitter-Papierbuch aus (eigenes Journal der Spur)",
    },
    ("handel", "kopier/auswertung.py"): {
        "rolle": "Werkzeug",
        "notiz": "Wertet das kopier-Papierbuch aus",
    },
    ("handel", "kopier1zu1/auswertung.py"): {
        "rolle": "Werkzeug",
        "notiz": "Wertet das kopier1zu1-Papierbuch aus",
    },
    ("handel", "omniquant/auswertung.py"): {
        "rolle": "Werkzeug",
        "notiz": "Wertet das Omniquant-Papierbuch aus (Haupt- und Schattenarm getrennt)",
    },
    ("handel", "spiegel/auswertung.py"): {
        "rolle": "Werkzeug",
        "notiz": "Wertet das Spiegel-Papierbuch aus",
    },
    # ------------------------------------------- Stufen und Stand
    # Die drei Risikostufen (Basis / mittel / hoch) sind KEIN eigener Eintrag:
    # es sind dieselben Spuren mit groesseren Betraegen in eigenen Dateien. Die
    # Befehle hier machen sie sichtbar, ohne eine zweite Wahrheit anzulegen.
    ("handel", "spuren_stand.py"): {
        "befehle": [
            {"was": "Stand aller Spuren (zeigt haupt/.mittel/.hoch je Spur)",
             "cmd": [".venv\\Scripts\\python.exe", "spuren_stand.py"],
             "hinweis": "rein lesend"},
            {"was": "Nur die scharfen Spuren",
             "cmd": [".venv\\Scripts\\python.exe", "spuren_stand.py", "--nur", "scharf"],
             "hinweis": "gemessen 30.09.: scanner, mosaic, moondev_listingarb"},
            {"was": "Stand als JSON",
             "cmd": [".venv\\Scripts\\python.exe", "spuren_stand.py", "--json"],
             "hinweis": "fuer Werkzeuge"},
        ],
    },
    ("handel", "auswertung_alle.py"): {
        "befehle": [
            {"was": "Auswertung Stufe Basis",
             "cmd": [".venv\\Scripts\\python.exe", "auswertung_alle.py"],
             "hinweis": "eigene Journale (handelsjournal.csv)"},
            {"was": "Auswertung Stufe mittel",
             "cmd": [".venv\\Scripts\\python.exe", "auswertung_alle.py", "--risiko", "mittel"],
             "hinweis": "handelsjournal.mittel.csv"},
            {"was": "Auswertung Stufe hoch",
             "cmd": [".venv\\Scripts\\python.exe", "auswertung_alle.py", "--risiko", "hoch"],
             "hinweis": "handelsjournal.hoch.csv"},
        ],
    },
    ("handel", "spiegelstand.py"): {
        "befehle": [
            {"was": "Spiegelstand Basis (Bedingung 4)",
             "cmd": [".venv\\Scripts\\python.exe", "spiegelstand.py"],
             "hinweis": "byte-genau gegen Q:"},
            {"was": "Spiegelstand Stufe mittel",
             "cmd": [".venv\\Scripts\\python.exe", "spiegelstand.py", "--risiko", "mittel"],
             "hinweis": "gemessen 30.09.: 29 von 29 byte-gleich"},
            {"was": "Spiegelstand Stufe hoch",
             "cmd": [".venv\\Scripts\\python.exe", "spiegelstand.py", "--risiko", "hoch"],
             "hinweis": "byte-genau gegen Q:"},
        ],
    },
    # ------------------------------------------- Freqtrade-Strategien
    **{
        ("handel", f"freqtrade/user_data/strategies/{name}.py"): {
            "rolle": "Strategie",
            "notiz": notiz,
            # KEIN EIGENER START: freqtrade laedt die Klasse, sie ist kein
            # Programm. Ohne diese Gruppe stuende sie in EINRICHTEN - als
            # fehlte etwas, dabei ist sie fertig.
            "gruppe": "kein_start",
            "warnungen": ["freqtrade laedt diese Klasse; der Bot-Aufsatz steht in "
                          "freqtrade/user_data/bots/"],
        }
        for name, notiz in (
            ("MoonDevTradingAgent", "Freqtrade-Strategie des Trading-Agenten (MA20/MA40, RSI 45-70, "
                                    "Volumen) - LONG-ONLY: can_short laedt im Spot-Modus nicht"),
            ("MoonDevTopMovers", "Freqtrade-Strategie TopMovers (+8..40 % in 24 h)"),
            ("MoonDevMarketRegime", "Freqtrade-Strategie Marktregime (BTC-Trend und Marktbreite)"),
            ("ema_cross", "Freqtrade-Strategie EMA-Kreuz - walk-forward geprueft; im ungesehenen "
                          "H2 halten die Hyperopt-Parameter NICHT"),
            ("ema_cross_h1", "Freqtrade-Strategie EMA-Kreuz auf 1 h (eigener Aufsatz)"),
            ("moondev_basis", "Freqtrade-Strategie: gemeinsame Basis der drei MoonDev-Strategien"),
        )
    },
})

# ---------------------------------------------------------------------------
# JEDE SPUR ALS ANKLICKBARE ZEILE (30.09.2026)
#
# Eine Spur ist ein ORDNER, kein Programm: sie hat kein eigenes venv (ausser
# den Nautilus-Armen) und ihre Datei heisst nicht immer `handeln.py`. Damit die
# Zeile im Fenster startbar wird, braucht sie den Interpreter, mit dem auch der
# Dauerlauf sie fahrt (`dauerlauf.PYTHON` = scanner-venv) und den Namen ihrer
# eigenen Datei. Beides steht hier EINMAL; die Paare sind dieselben wie in
# `dauerlauf.SPUREN` - eine zweite Spurliste gibt es nicht.
#
# Gestartet wird IMMER `--vorschau`: das ist der lesende Blick einer Spur
# (ihre Zeile "Live waere gesperrt durch: ..."), sie schreibt dabei nichts.
# Ohne den Zusatz liefe ein voller Handelszyklus los - und das ist Sache des
# Dauerlaufs, nicht eines Klicks im Fenster.
#
# Der Interpreter steht RELATIV zur Spur (`..\scanner\...`), weil das
# Arbeitsverzeichnis einer Zeile ihr eigener Ordner ist; das Fenster loest den
# Programmnamen gegen genau dieses Verzeichnis auf
# (`aktionen.start_ausfuehren`). Ein absoluter Pfad waere hier ein zweiter
# Standort und wuerde einen Umzug auf ein anderes Laufwerk nicht ueberleben.
HANDEL_PYTHON = "..\\scanner\\.venv\\Scripts\\python.exe"
NAUTILUS_PYTHON = "..\\nautilus\\.venv\\Scripts\\python.exe"

SPUREN_START = {
    name: ("handeln.py", HANDEL_PYTHON)
    for name in (
        "xperp", "swap", "orbk", "orb", "omniquant", "gitter", "macd_mtf",
        "squeeze", "supertrend", "wavetrend", "mosaic", "kraken",
        "moondev_funding", "moondev_listingarb", "moondev_topmovers",
        "moondev_marktlage", "moondev_signalwelle", "moondev_sniper",
        "moondev_whale", "moondev_liquidation", "moondev_sentiment",
        "trendwende_btc", "liq_wand", "robinhood_radar", "kopier1zu1",
        "iv_wand", "iv_waelle",
        # omnitrade (30.09.2026): die Haus-Spur, die den Rust-Lauf spiegelt.
        "omnitrade",
        "klassik_sma", "klassik_ema", "klassik_macd", "klassik_bollinger",
        "klassik_donchian", "klassik_rsi", "klassik_rsi2",
        "klassik_donchian_trend",
    )
}
SPUREN_START.update({
    # Der scanner fuehrt das gemeinsame venv selbst - von innen ist es sein
    # eigenes `.venv`, von aussen `..\scanner\.venv`.
    "scanner": ("handeln.py", ".venv\\Scripts\\python.exe"),
    # Die Nautilus-Arme brauchen nautilus_trader; das liegt nur im
    # nautilus-venv. nautilus_kraken hat keines und teilt sich den Ordner mit
    # dem Futures-Arm (der fahrt handeln_futures.py) - hier steht der
    # Hauptarm.
    "nautilus": ("handeln.py", NAUTILUS_PYTHON),
    "nautilus_kraken": ("handeln.py", NAUTILUS_PYTHON),
    # Stillgelegte Spuren (spiegel, kopier): sie handeln nicht mehr, ihr Buch
    # bleibt aber als Vergleichsgrundlage stehen - die Vorschau zeigt genau
    # diesen Stand.
    "spiegel": ("spiegel.py", HANDEL_PYTHON),
    "kopier": ("kopier.py", HANDEL_PYTHON),
})

# In KURATIERT eintragen, statt 37 Bloecke von Hand zu schreiben. `setdefault`
# laesst einen vorhandenen Eintrag stehen (Rolle, Notiz, Gruppe) und ergaenzt
# nur den Start.
for _spur, (_spur_skript, _spur_python) in SPUREN_START.items():
    KURATIERT.setdefault(("handel", _spur), {})["start"] = [
        _spur_python, _spur_skript, "--vorschau",
    ]

# Die zehn omnitrade-LAEUFE (Rust-CLI, OKX-Testnet) sind keine Spuren und haben
# keinen eigenen Ordner. Eine Zeile je Lauf entstuende deshalb gar nicht - die
# Zentrale listet nur Pfade, die es auf der Platte gibt (fuellen.fuellen()).
# Sie haengen darum als ANKLICKBARE BEFEHLE an der Zeile der Haus-Spur: das
# Fenster zeigt sie in der Karte "Was dieses Projekt kann" und fuehrt sie mit
# Logbeleg aus (fenster.py, befehle.manifestkommandos).
#
# Der Start ist absichtlich der ECHTE Start und nicht `--vorschau`: die drei
# laufenden Spuren-Zeilen sind lesende Blicke, ein Lauf laesst sich so nicht
# hochfahren. `omnitrade_start.py start <name>` ist idempotent - laeuft der Lauf
# schon, meldet es "laeuft schon" und startet nichts doppelt. Die Handelsregeln
# sind davon nicht beruehrt: die Laeufe fahren OKX-Testnet, kein echtes Geld.
OMNI_LAEUFE = (
    ("adx_macd_btc", "BTCUSDC"), ("adx_macd_eth", "ETHUSDC"),
    ("rsi30_stop5_btc", "BTCUSDC"), ("rsi30_stop5_eth", "ETHUSDC"),
    ("pine_sma_cross_btc", "BTCUSDC"), ("pine_ema_cross_btc", "BTCUSDC"),
    ("pine_macd_cross_btc", "BTCUSDC"), ("pine_rsi_meanrev_btc", "BTCUSDC"),
    ("pine_bollinger_btc", "BTCUSDC"), ("pine_donchian_btc", "BTCUSDC"),
)
KURATIERT.setdefault(("handel", "omnitrade"), {})["befehle"] = [
    {
        "was": "Lauf %s starten (%s)" % (name, symbol),
        "cmd": [HANDEL_PYTHON, "..\\omnitrade_start.py", "start", name],
        "hinweis": "OKX-Testnet, kein echtes Geld; laeuft schon = es passiert nichts",
        "start": True,
    }
    for name, symbol in OMNI_LAEUFE
] + [
    {
        "was": "Alle Laeufe mit Zustand auflisten (rein lesend)",
        "cmd": [HANDEL_PYTHON, "..\\omnitrade_start.py", "liste"],
        "hinweis": "je Lauf: laeuft oder steht, PID, Alter der Statusdatei",
    },
]

# Nicht von Hand starten: der Dauerlauf nimmt die echte Sperre, melder.py
# verschickt Telegram-Nachrichten. Beide bekommen KEINEN Startbefehl.
OHNE_START = {
    "dauerlauf.py": "NIE von Hand starten - ein Handstart nimmt die echte Sperre und schreibt "
                    "ins echte Protokoll (dafuer gibt es die geplanten Aufgaben und den "
                    "Dauerlauf-Waechter)",
    "melder.py": "verschickt Telegram-Nachrichten - nicht zum Ausprobieren aufrufen",
    "kraken_abweisungs_sonde.py": "jeder Aufruf misst ECHT gegen Kraken und setzt den "
                                  "Lockout-Timer zurueck",
}


def _erste_zeile(pfad: Path) -> str:
    """Die erste brauchbare Textzeile einer README - die eigene Beschreibung."""
    for name in ("README.md", "readme.md", "README.MD", "README.rst", "README.txt"):
        f = pfad / name
        if not f.is_file():
            continue
        for zeile in f.read_text(encoding="utf-8", errors="replace").splitlines():
            t = zeile.strip().lstrip("#*-> ").strip()
            if not t or t.startswith(("!", "[", "<", "|", "=", "```")):
                continue
            return t[:200]
    return ""


def _docstring(pfad: Path) -> str:
    """Der erste Satz der Modul-Docstring einer .py-Datei."""
    f = pfad if pfad.is_file() else None
    if f is None:
        kandidaten = sorted(pfad.glob("*.py"))
        if not kandidaten:
            return ""
        f = kandidaten[0]
    text = f.read_text(encoding="utf-8", errors="replace")
    treffer = re.search(r'^\s*"""(.*?)(?:"""|\Z)', text, re.S | re.M)
    if not treffer:
        return ""
    return treffer.group(1).strip().splitlines()[0][:200] if treffer.group(1).strip() else ""


def notiz_aus_platte(repo: scan.Repo) -> str:
    """Notiz aus dem Projekt SELBST: README zuerst, dann Docstring."""
    if repo.datei is not None:
        text = _docstring(repo.datei)
        if text:
            return text
        return f"Werkzeug in {repo.pfad.name}/"
    text = _erste_zeile(repo.pfad)
    if text:
        return text
    return _docstring(repo.pfad)


def _kuratiert(wurzel: str, pfad: str, ordner: str = "") -> dict:
    """Der kuratierte Eintrag zu einem Projekt - Pfad schlaegt Dateiname.

    `auswertung.py` gibt es in fuenf Spuren, `backtest.py` in zweien: ueber den
    Dateinamen allein liessen sie sich nicht unterscheiden. Deshalb wird zuerst
    der Pfad innerhalb der Wurzel gesucht (mit "/"), dann der Anzeigename -
    damit die aelteren Eintraege (nur Name) weiter greifen.
    """
    return KURATIERT.get((wurzel, pfad)) or KURATIERT.get((wurzel, ordner), {})


def eintrag_bauen(repo: scan.Repo) -> dict:
    """Aus einem Plattenfund einen Manifest-Eintrag machen - ohne Erfindung."""
    kuratiert = _kuratiert(repo.wurzel, repo.pfad_rel, repo.ordner)
    eintrag: dict = {"ordner": repo.ordner}
    if repo.wurzel != "repos":
        eintrag["wurzel"] = repo.wurzel
    if repo.pfad_rel != repo.ordner:
        eintrag["pfad"] = repo.pfad_rel
    rolle = kuratiert.get("rolle") or {
        "spur": "Spur", "werkzeug": "Werkzeug", "daten": "Datenfeld", "ablage": "Ablage",
        "doku": "Doku", "container": "Projekt",
    }.get(repo.art, "")
    if rolle:
        eintrag["rolle"] = rolle
    eintrag["art"] = repo.art
    eintrag["notiz"] = kuratiert.get("notiz") or notiz_aus_platte(repo) or repo.art

    start = kuratiert.get("start")
    schluessel = repo.pfad_rel
    if start is None and repo.datei is not None and schluessel in HILFE_VERIFIZIERT:
        start = [t.format(pfad=schluessel.replace("/", "\\")) for t in HILFE_START]
    if start:
        eintrag["start"] = start
        eintrag["venv_pflicht"] = bool(repo.venv)
    elif schluessel in OHNE_START and repo.datei is not None:
        eintrag["warnungen"] = [OHNE_START[schluessel]]
        # Ein bewusst startloses Werkzeug ist nicht "einzurichten" - der Grund
        # steht daneben (siehe manifest._zeile, Gruppe KEIN EIGENER START).
        eintrag["gruppe"] = "kein_start"

    gruppe = kuratiert.get("gruppe")
    if gruppe:
        eintrag["gruppe"] = gruppe
    if kuratiert.get("anleitung"):
        eintrag["anleitung"] = kuratiert["anleitung"]
    if kuratiert.get("bot"):
        eintrag["bot"] = kuratiert["bot"]
    return eintrag


def _sortierschluessel(eintrag: dict, reihenfolge: list[str]) -> tuple:
    wurzel = eintrag.get("wurzel", "repos")
    platz = reihenfolge.index(wurzel) if wurzel in reihenfolge else len(reihenfolge)
    return (platz, str(eintrag.get("ordner", "")).lower())


# Feste Feldreihenfolge je Eintrag: so liest sich die Datei wie eine Tabelle und
# ein Feld, das nachtraeglich hinzukommt, landet nicht achtlos am Ende.
FELD_REIHENFOLGE = (
    "ordner", "wurzel", "pfad", "rolle", "art", "bot", "gruppe", "notiz",
    "start", "einrichten", "einrichten_kette", "bauen", "bauen_kette",
    "venv_pflicht", "node_modules_pflicht",
    "pfad_pflicht", "port", "anleitung", "befehle", "warnungen",
    "beleg_frist_s",
)


def felder_ordnen(eintrag: dict) -> dict:
    """Einzelnen Eintrag in die feste Feldreihenfolge bringen."""
    geordnet = {k: eintrag[k] for k in FELD_REIHENFOLGE if k in eintrag}
    for k, v in eintrag.items():
        if k not in geordnet:
            geordnet[k] = v
    return geordnet


def fuellen(manifest_pfad: Path, brainfiles: Path, *, anwenden: bool = False) -> int:
    """Fehlende Eintraege ergaenzen, bestehende unveraendert lassen."""
    daten = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    vorhanden = daten.get("repos") or []
    schluessel = {(e.get("wurzel", "repos"), e.get("pfad") or e.get("ordner")) for e in vorhanden}

    plaetze = [(w, scan.tief_scannen(w, pfad)) for w, pfad in quellen.alle(brainfiles)]
    neu: list[dict] = []
    for wurzel_obj, repos in plaetze:
        for repo in repos:
            if (repo.wurzel, repo.pfad_rel) in schluessel:
                continue
            neu.append(eintrag_bauen(repo))

    print(f"Manifest : {manifest_pfad}")
    print(f"vorhanden: {len(vorhanden)} Eintraege")
    for wurzel_obj, repos in plaetze:
        anzahl = len([r for r in neu if r.get("wurzel", "repos") == wurzel_obj.kennung])
        print(f"  {wurzel_obj.titel:<22} {len(repos):>4} Zeilen auf der Platte, "
              f"{anzahl:>3} neu")
    print(f"neu      : {len(neu)} Eintraege")

    if not anwenden:
        for e in neu:
            print(f"  + [{e.get('wurzel', 'repos')}] {e['ordner']:<40} {e.get('rolle', ''):<12} "
                  f"{'START' if e.get('start') else '     '} {e['notiz'][:60]}")
        print("\nTrockenlauf - nichts geschrieben. Mit --anwenden schreiben.")
        return 0

    daten["repos"] = [
        felder_ordnen(e)
        for e in sorted(
            vorhanden + neu, key=lambda e: _sortierschluessel(e, list(quellen.REIHENFOLGE))
        )
    ]
    daten["stand"] = datetime.now().strftime("%Y-%m-%d")
    sicherung = manifest_pfad.with_name(
        f"{manifest_pfad.stem}.bak-{datetime.now():%Y%m%d}{manifest_pfad.suffix}"
    )
    shutil.copy2(manifest_pfad, sicherung)
    text = json.dumps(daten, indent=2, ensure_ascii=False) + "\n"
    vorher = manifest_pfad.read_bytes()
    manifest_pfad.write_bytes(text.encode("utf-8"))
    print(f"\n{len(neu)} Eintraege ergaenzt -> {len(daten['repos'])} gesamt.")
    print(f"Sicherung: {sicherung}")
    print(f"Datei    : {len(vorher)} -> {len(manifest_pfad.read_bytes())} Byte")
    return 0


def belege_erzeugen(manifest_pfad: Path, brainfiles: Path, log_ordner: Path) -> int:
    """Jeden Startbefehl EINMAL wirklich ausfuehren - das ist der Beleg.

    Es laeuft derselbe Weg wie im Fenster (`aktionen.start_ausfuehren`), also
    entsteht genau die Logdatei, auf die sich das Fenster und
    `tests/test_manifest_gegenprobe.py` berufen. Ein Befehl, der laenger als
    `FRIST_S` laeuft, wird beendet - ein Startbeleg darf keinen Prozess
    hinterlassen.
    """
    import aktionen
    import manifest as _manifest

    log_ordner.mkdir(parents=True, exist_ok=True)
    plaetze = [(w, scan.tief_scannen(w, pfad)) for w, pfad in quellen.alle(brainfiles)]
    eintraege = _manifest.manifest_laden(manifest_pfad)
    zeilen = _manifest.zeilen_bauen(plaetze, eintraege, None)

    offen = [
        z for z in zeilen
        if z.start_da and z.repo is not None
        and not any(log_ordner.glob(f"{z.ordner}-*.log"))
    ]
    print(f"Belege: {len(offen)} Startbefehle ohne Log")
    gut, schlecht = [], []
    for z in offen:
        ergebnis = aktionen.start_ausfuehren(z, log_ordner, jetzt=datetime.now())
        if ergebnis.fehler or ergebnis.prozess is None:
            schlecht.append((z.ordner, ergebnis.fehler))
            continue
        try:
            frist = z.beleg_frist_s or FRIST_S
            code = ergebnis.prozess.wait(timeout=frist)
        except Exception:                                     # noqa: BLE001
            ergebnis.prozess.kill()
            ergebnis.prozess.wait(timeout=10)
            code = "abgebrochen (Frist)"
        aktionen.ereignis_anhaengen(ergebnis.log, f"beendet (Code {code})")
        (gut if code == 0 else schlecht).append((z.ordner, code))
    print(f"belegt: {len(gut)}   auffaellig: {len(schlecht)}")
    for ordner, grund in schlecht:
        print(f"   ! {ordner}: {grund}")
    return 0 if not schlecht else 1


FRIST_S = 90


def _projekt_ordner(brainfiles: Path, eintrag: dict) -> Path | None:
    """Der Ordner eines Manifest-Eintrags auf der Platte (None, wenn unbekannt).

    Der Schluessel ist das PAAR (wurzel, pfad) - ein Eintrag ohne `wurzel` liegt
    in `Werkstatt`, einer ohne `pfad` in seinem Ordner.
    """
    for w, basis in quellen.alle(brainfiles):
        if w.kennung == eintrag.get("wurzel", "repos"):
            return Path(basis) / (eintrag.get("pfad") or eintrag["ordner"])
    return None


def auffrischen(
    manifest_pfad: Path, *, anwenden: bool = False, brainfiles: Path | None = None
) -> int:
    """Fehlende Felder BESTEHENDER Eintraege aus KURATIERT nachtragen.

    Nur was fehlt wird ergaenzt (Rolle, Notiz, Gruppe, Anleitung, `start`) -
    alles handschriftlich Gepflegte bleibt unangetastet, denn geschrieben wird
    nur, wo das Feld LEER ist. Gedacht fuer den Fall, dass eine Kuratierung
    nachgezogen wurde (z. B. ein Startbefehl fuer die Handelsspuren am
    30.09.2026): `fuellen` laesst vorhandene Eintraege bewusst unveraendert,
    sonst wuerde es Handarbeit ueberschreiben.

    Kommt ein `start` dazu, wird auch `venv_pflicht` gesetzt, wenn das Projekt
    ein EIGENES venv hat - ein Start ohne Abhaengigkeitspruefung waere eine
    halbe Aussage.
    """
    daten = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    geaendert = []
    for e in daten.get("repos") or []:
        kuratiert = _kuratiert(
            e.get("wurzel", "repos"), e.get("pfad") or e["ordner"], e["ordner"]
        )
        if not kuratiert:
            # Auch ohne kuratierten Eintrag kann ein Start nachzuziehen sein:
            # die Hilfe-Startbefehle (HILFE_VERIFIZIERT) gelten fuer Dateien,
            # die kein KURATIERT brauchen.
            if not e.get("start"):
                schluessel = e.get("pfad") or e["ordner"]
                if schluessel in HILFE_VERIFIZIERT:
                    e["start"] = [
                        t.format(pfad=schluessel.replace("/", "\\")) for t in HILFE_START
                    ]
                    geaendert.append(f"{e['ordner']}.start")
            continue
        for feld in ("rolle", "notiz", "gruppe", "anleitung", "befehle", "start",
                     "warnungen"):
            if kuratiert.get(feld) and not e.get(feld):
                e[feld] = kuratiert[feld]
                geaendert.append(f"{e['ordner']}.{feld}")
                if feld == "start" and brainfiles is not None:
                    ordner = _projekt_ordner(brainfiles, e)
                    if ordner is not None and scan._venv(ordner)[0] is not None:
                        e["venv_pflicht"] = True
        # Bewusst startlose Werkzeuge (OHNE_START): der Grund gehoert in den
        # Eintrag, sonst stuende die Zeile als "EINRICHTEN" im Fenster - als
        # fehlte etwas, dabei ist das Fehlen die Absicht.
        pfad = e.get("pfad") or e["ordner"]
        if pfad in OHNE_START and not e.get("warnungen"):
            e["warnungen"] = [OHNE_START[pfad]]
            e.setdefault("gruppe", "kein_start")
            geaendert.append(f"{e['ordner']}.warnungen")
    print(f"nachzutragen: {len(geaendert)} Felder")
    if not anwenden:
        for name in geaendert:
            print(f"   + {name}")
        print("\nTrockenlauf - nichts geschrieben. Mit --anwenden schreiben.")
        return 0
    if geaendert:
        sicherung = manifest_pfad.with_name(
            f"{manifest_pfad.stem}.bak-{datetime.now():%Y%m%d}{manifest_pfad.suffix}"
        )
        shutil.copy2(manifest_pfad, sicherung)
        daten["repos"] = [felder_ordnen(e) for e in daten["repos"]]
        manifest_pfad.write_bytes(
            (json.dumps(daten, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        )
        print(f"\n{len(geaendert)} Felder ergaenzt. Sicherung: {sicherung}")
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description="Manifest der Zentrale fuellen")
    zerleger.add_argument("--anwenden", action="store_true", help="wirklich schreiben")
    zerleger.add_argument(
        "--belege", action="store_true",
        help="jeden Startbefehl ohne Log einmal ausfuehren (erzeugt den Beleg in logs/)",
    )
    zerleger.add_argument(
        "--auffrischen", action="store_true",
        help="fehlende Felder vorhandener Eintraege aus der Kuratierung nachtragen",
    )
    args = zerleger.parse_args(argv)
    brainfiles = HIER.parents[2]
    if args.belege:
        return belege_erzeugen(HIER / "repos-zentrale.json", brainfiles, HIER / "logs")
    if args.auffrischen:
        return auffrischen(HIER / "repos-zentrale.json", anwenden=args.anwenden,
                           brainfiles=brainfiles)
    return fuellen(HIER / "repos-zentrale.json", brainfiles, anwenden=args.anwenden)


if __name__ == "__main__":
    raise SystemExit(main())
