"""Die Wurzeln der Zentrale: welche Orte sie zeigt und was daraus eine Zeile wird.

Die Zentrale war bis 30.09.2026 auf `Werkstatt` festgelegt. Sie zeigt
jetzt drei **Bereiche** - jede mit eigenem Wurzelordner, eigener Sperrliste und
eigener Regel, was ueberhaupt eine Zeile bekommt:

| Kennung | Bereich | Wurzel | Regel |
|---|---|---|---|
| `repos` | REPOS | `Werkstatt` | nur Klone mit `.git` (wie bisher) |
| `werkstatt` | WERKSTATT | `Werkstatt` | Projekt- und Ablageordner; Klone und `Projekte` sind eigene Bereiche |
| `handel` | HANDEL | `Agenten/Handel` | Spuren, Werkzeuge, Ausgabefelder |

Diese Datei kennt weder tkinter noch das Manifest - sie ist ohne Fenster
pruefbar (`tests/test_quellen.py`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Ordner, die in JEDER Wurzel keine Zeile bekommen: Interpreter, Caches und
# Editor-/Werkzeugzustand. Bewusst als Namen (nicht als Muster), damit eine
# Sperre nicht versehentlich ein echtes Projekt trifft.
UEBERALL_OHNE = frozenset(
    {
        ".git", ".venv", "venv", "__pycache__", "node_modules", ".vscode",
        ".pytest_cache", ".claude", ".devcontainer", ".docker", ".onchainos",
        ".mypy_cache", ".ruff_cache", "cache",
    }
)

# Dateiendungen, die als eigene Zeile erscheinen duerfen (nur in Wurzeln mit
# `dateien=True`). Ein .py ohne eigenen Einstieg wird NICHT gezeigt - sonst
# stuenden in Handel/ 91 Moduldateien neben 45 Ordnern.
DATEI_ENDUNGEN = (".py",)

# Kennzeichen eines Werkzeugs, das man wirklich aufrufen kann: es deklariert
# einen Einstieg UND nimmt Argumente entgegen. Wer eine CLI ohne argparse baut,
# kann sie mit 'datei hinzufuegen' im Manifest trotzdem sichtbar machen.
WERKZEUG_MERKMALE = ("__main__", "argparse")

# Ausnahmen von der Regel oben: Dateien, die einen eigenen Einstieg haben, aber
# keine Argumente auswerten - und die man trotzdem im Fenster sehen will (ein
# Fenster, eine Sonde, eine Kennzahlen-Tafel). Bewusst eine kurze, ausdrueckliche
# Liste: eine .py-Datei ohne Einstieg wird hier NICHT aufgenommen.
#
# Seit 30.09.2026 duerfen hier auch PFADE mit Unterordner stehen
# ("okx_bot_waechter/analyse.py"). Nur so sind die Haus-Werkzeuge erreichbar, die
# neben einer Spur liegen; die Wurzel selbst wird weiter nur nach Einstieg UND
# Argumentliste durchsucht, damit die 130 Dateien des Fremdprojekts OpenAlice
# nicht als Zeilen auftauchen.
#
# Pfad-Schreibweise: mit "/", relativ zur Wurzel, ohne "..".
WERKZEUG_ZUSATZ = (
    "leitstand.py",                 # das grosse Fenster (Ueberwachen/Freigaben/Backtests)
    "pruefe_ratschen.py",           # Tafel: Herkunft der Drawdown-Ratsche je Spur
    "strategie_kennzahlen.py",      # t-Statistik und Stop-Vorschlag je Spur
    "kraken_abweisungs_sonde.py",   # Sonde: haelt eine Kraken-Abweisung als Zeugen fest
    # --- Wartung, Betrieb und Auswertung neben den Spuren -------------------
    "okx_bot_waechter/analyse.py",       # Leiter/Munition je OKX-Bot gegen das Instrument
    "okx_bot_waechter/vorschlag.py",     # neuen DCA-Bot rechnen (mit Stop)
    "okx_bot_waechter/bauen.py",         # Bot anlegen (nur mit bauen_erlaubt + --anwenden)
    "scanner/stops_bereinigen.py",       # Stop-Merker aufraeumen (Vorschau Standard)
    "scanner/boersenstops.py",           # Buch gegen Boerse: hat jede Position ihren Stop?
    "xperp/geister_nachziehen.py",       # Geister-Zeilen im xperp-Journal begradigen
    "xperp/fremde_positionen_uebernehmen.py",
    "kraken/abgleich.py",                # Kraken-Buch gegen die Boerse
    "kraken/einsatz_nachziehen.py",      # Einsatz in Kraken-Belegzeilen richtigstellen
    "mosaic/geist_zurueckbuchen.py",     # falsch gebuchte Live-Position zurueckholen
    "mosaic/boersenabgleich.py",
    "ai4trade/heartbeat.py",             # ai4trade.ai: Heartbeat pollen
    "verbesserer/lauf.py",               # Selbstverbesserung: Anfragen anwenden
    "nautilus/daten_auffrischen.py",     # Kursdaten der Nautilus-Arme nachziehen
    # --- Backtests ----------------------------------------------------------
    "orb/backtest.py",
    "orbk/backtest.py",
    "gitter/backtest_gitter.py",
    "nautilus/backtest_grid.py",
    "xperp/historie.py",                 # Kurshistorie fuer den xperp-Backtest
    # --- Auswertungen, die je Spur liegen -----------------------------------
    "gitter/auswertung.py",
    "kopier/auswertung.py",
    "kopier1zu1/auswertung.py",
    "omniquant/auswertung.py",
    "spiegel/auswertung.py",
    # --- Freqtrade-Strategien (kein eigenes Programm: eine Klasse, die
    #     freqtrade laedt - darum KEIN Startbefehl) --------------------------
    "freqtrade/user_data/strategies/MoonDevTradingAgent.py",
    "freqtrade/user_data/strategies/MoonDevTopMovers.py",
    "freqtrade/user_data/strategies/MoonDevMarketRegime.py",
    "freqtrade/user_data/strategies/ema_cross.py",
    "freqtrade/user_data/strategies/ema_cross_h1.py",
    "freqtrade/user_data/strategies/moondev_basis.py",
)


@dataclass(frozen=True)
class Wurzel:
    """Ein Ort, den die Zentrale zeigt."""

    kennung: str                 # "repos" - Schluessel im Manifest
    titel: str                   # Ueberschrift im Fenster (Versalien)
    erklaerung: str              # eine Zeile unter der Ueberschrift
    pfad_rel: str                # relativ zur BrainFiles-Wurzel
    nur_git: bool = False        # nur Ordner mit eigenem .git
    ohne_git: bool = False       # Ordner mit eigenem .git ueberspringen (Klone gehoeren zu REPOS)
    ohne: tuple[str, ...] = ()   # Namen, die hier keine Zeile bekommen (zusaetzlich zu UEBERALL_OHNE)
    tiefe: int = 1               # 1 = direkte Kinder, 2 = auch eine Ebene tiefer
    dateien: bool = False        # auch Werkzeug-Dateien in der Wurzel zeigen

    def pfad(self, brainfiles: Path) -> Path:
        return Path(brainfiles) / self.pfad_rel


# Die feste Reihenfolge im Fenster. REPOS zuerst: das ist der gewachsene Teil.
WURZELN: tuple[Wurzel, ...] = (
    Wurzel(
        kennung="repos",
        titel="REPOS",
        erklaerung="geklonte Fremd-Repos unter Werkstatt, je Repo ein Bot",
        pfad_rel="Werkstatt",
        nur_git=True,
        ohne=("copilot-worktrees",),
    ),
    Wurzel(
        kennung="werkstatt",
        titel="WERKSTATT",
        erklaerung="eigene Projekte, Datenfelder und Ablagen unter Werkstatt/",
        pfad_rel="Werkstatt",
        ohne=("Projekte",),
        ohne_git=True,
    ),
    Wurzel(
        kennung="handel",
        titel="HANDEL",
        erklaerung="Spuren, Werkzeuge und Ausgaben unter Agenten/Handel",
        pfad_rel="Agenten/Handel",
        ohne=("docs", "tests", "daten", "daten.bak-20260919"),
        dateien=True,
    ),
)

# Die Projekte-Unterordner gehoeren in den Bereich WERKSTATT, stehen aber eine
# Ebene tiefer. Eigene Wurzel mit demselben Bereich - so bleiben Wurzel und
# Bereich getrennt und die Anzeige trotzdem flach.
PROJEKTE = Wurzel(
    kennung="projekte",
    titel="WERKSTATT · PROJEKTE",
    erklaerung="Datenfelder und Projektstaende unter Werkstatt/Projekte",
    pfad_rel="Werkstatt/Projekte",
)

# Anzeige-Reihenfolge der Wurzeln (die Kennung `projekte` haengt an WERKSTATT).
REIHENFOLGE: tuple[str, ...] = ("repos", "werkstatt", "projekte", "handel")

# Zuordnung Wurzel -> Bereich (Ueberschrift). Zwei Wurzeln koennen sich einen
# Bereich teilen: Werkstatt und Werkstatt/Projekte.
BEREICHE: dict[str, str] = {
    "repos": "REPOS",
    "werkstatt": "WERKSTATT",
    "projekte": "WERKSTATT",
    "handel": "HANDEL",
}

BEREICH_ERKLAERUNG: dict[str, str] = {
    "REPOS": "Fremd-Klone, je Repo ein Bot",
    "WERKSTATT": "eigene Projekte und Ablagen",
    "HANDEL": "Spuren, Werkzeuge, Ausgaben",
}


_NACH_KENNUNG = {w.kennung: w for w in (*WURZELN, PROJEKTE)}


def alle(brainfiles: Path) -> list[tuple[Wurzel, Path]]:
    """Alle Wurzeln mit aufgeloestem Pfad, in Anzeige-Reihenfolge."""
    return [(_NACH_KENNUNG[k], _NACH_KENNUNG[k].pfad(brainfiles)) for k in REIHENFOLGE]


def wurzel_von(kennung: str) -> Wurzel | None:
    """Die Wurzel zu einer Kennung - None, wenn das Manifest etwas Fremdes nennt."""
    return _NACH_KENNUNG.get(kennung)


def bereich(kennung: str) -> str:
    """Die Bereichs-Ueberschrift einer Wurzel-Kennung (unbekannt -> REPOS)."""
    return BEREICHE.get(kennung, "REPOS")


# --------------------------------------------------------------------------
# Die Grenze zu Fremd-Material (Agenten/FREMD-Liste.json)
#
# Die Zentrale soll zeigen, WAS fremd ist, ohne es mitzuzaehlen. Die Liste liegt
# in `Agenten/Werkzeuge/fremd.py` - geladen ueber den PFAD, nicht ueber sys.path
# (dasselbe Muster wie fenster_design.py): ein Eintrag auf `Agenten/Werkzeuge`
# koennte gleichnamige Spurenmodule verdecken.
# --------------------------------------------------------------------------

_FREMD = None


def fremd_modul():
    """Das Modul `Agenten/Werkzeuge/fremd.py` laden (None, wenn es fehlt)."""
    global _FREMD
    if _FREMD is None:
        import importlib.util
        import sys as _sys

        pfad = Path(__file__).resolve().parent.parent / "fremd.py"
        if not pfad.is_file():
            _FREMD = False
        else:
            spec = importlib.util.spec_from_file_location("haus_fremd", pfad)
            modul = importlib.util.module_from_spec(spec)
            # WICHTIG: vor exec_module in sys.modules eintragen. Sonst findet
            # `@dataclass` beim Verarbeiten von Fremd das eigene Modul nicht
            # (`sys.modules[cls.__module__]` ist None) und der Import bricht mit
            # AttributeError ab - ein Fehler, der erst beim Laden auftritt.
            _sys.modules["haus_fremd"] = modul
            spec.loader.exec_module(modul)
            _FREMD = modul
    return _FREMD or None


def fremde() -> list:
    """Die Fremd-Eintraege (leer, wenn die Liste fehlt - nie ein Absturz)."""
    modul = fremd_modul()
    return modul.laden() if modul else []


def pfad_in_wurzel(kennung: str, pfad_im_projekt: str) -> str:
    """Den vollen Pfad relativ zur BrainFiles-Wurzel bauen.

    Das Manifest nennt den Pfad INNERHALB seiner Wurzel (`kraken/abgleich.py`),
    die Fremd-Liste den Pfad AB der Wurzel - hier wird beides zusammengefuehrt.
    """
    w = wurzel_von(kennung) or PROJEKTE
    return f"{w.pfad_rel}/{pfad_im_projekt}".strip("/")
