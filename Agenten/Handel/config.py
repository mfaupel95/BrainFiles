"""Konfigurationskonstanten fuer dauerlauf.py und verwandte Module.

Zentrale Stelle fuer Tuning-Parameter, Limits und Schwellwerte.
"""

from dataclasses import dataclass
from typing import Dict
import logging

log = logging.getLogger(__name__)


# ===== TIMING-PARAMETER =====

# Zyklus-Takt in Sekunden (wird von Herzschlag ueberschrieben, wenn dieser engmaschiger ist)
DEFAULT_TAKT_MINUTEN = 5

# Maximum Sekunden pro Zyklus (MUSS groesser sein als Freigabefenster-Limit!)
# Siehe: scanner/wachen.json FREIGABE_ZEITLIMIT_S = 600s -> hier 700s
TIMEOUT_S = 700

# Hintergrund-Abruf-Timeouts
KURSE_TIMEOUT_S = 30
KERZEN_TIMEOUT_S = 45
FREQTRADE_TIMEOUT_S = 20

# Refresh-Rate fuer GUI (ms)
REFRESH_MS = 5000

# Cache-Alter-Schwellwerte (Minuten)
SCAN_ALTER_MINUTEN = 120  # Scanner-Rangliste gueltig
KURS_CACHE_MIN = 1        # Kurse min aktualisieren

# Herzschlag-Schwellen (Minuten, von wachen.json ueberschreibbar)
HERZSCHLAG_WARNUNG_MIN = 30
HERZSCHLAG_KRITISCH_MIN = 45


# ===== RISIKO-MANAGEMENT =====

@dataclass
class RisikoStufe:
    """Parameter je Risikostufe."""
    name: str
    faktor: float
    live_mode: bool  # ob diese Stufe im Live-Modus handeln darf
    telegram_aktiv: bool  # ob Befehle abgerufen werden
    papier_force: bool  # erzwinge Papier-Modus unabhaengig von Fenster
    
    def beschreibung(self) -> str:
        mode = "LIVE" if self.live_mode else "PAPIER"
        return f"{self.name} x{self.faktor} ({mode})"


RISIKO_STUFEN: Dict[str, RisikoStufe] = {
    "niedrig": RisikoStufe("Niedrig", 1.0, True, True, False),
    "mittel": RisikoStufe("Mittel", 2.0, False, False, True),
    "hoch": RisikoStufe("Hoch", 4.0, False, False, True),
}

STANDARD_STUFE = "niedrig"


# ===== SPUR-KONFIGURATION =====

@dataclass
class SpurConfig:
    """Konfiguration je Handelsspur."""
    ordner: str
    waehrung: str = "USD"
    python_path: str = None  # optional, fuer venvs wie nautilus
    beschreibung: str = ""
    
    def __str__(self) -> str:
        desc = f" ({self.beschreibung})" if self.beschreibung else ""
        return f"{self.ordner} [{self.waehrung}]{desc}"


SPUREN: Dict[str, SpurConfig] = {
    "xperp": SpurConfig("xperp", "USD", beschreibung="OKX Perpetuals - Hauptweg"),
    "scanner": SpurConfig("scanner", "USD", beschreibung="Scan + Entry"),
    "swap": SpurConfig("swap", "USD", beschreibung="SWAP-Spur"),
    "kraken": SpurConfig("kraken", "EUR", beschreibung="Kraken Spot (Papier seit 03.09)"),
    "omniquant": SpurConfig("omniquant", "USD", beschreibung="Prognose-Treffer"),
}

# Spuren die Live-Pfade haben (werden bei Freigabefenster ggf. aktiv)
LIVE_SPUREN = {"xperp", "scanner", "swap"}

# Spuren die einen eigenen venv haben (nicht Basis-Python)
CUSTOM_VENV_SPUREN = {"nautilus"}


# ===== LOGGING-KONFIGURATION =====

LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_MAX_BYTES = 10_000_000  # 10 MB pro Logfile
LOG_BACKUP_COUNT = 5

# Kritische Log-Level: sende sofort Alarm
CRITICAL_LOG_LEVEL = logging.ERROR


# ===== FREIGABE-FENSTER-REGELN =====

FREIGABE_MIN_DAUER = 1

# Maximale Dauer eines offenen Freigabefensters (Stunden)
FREIGABE_MAX_DAUER = 2

# Standard-Dauer bei /ja ohne Angabe (Minuten)
FREIGABE_DEFAULT_DAUER = 30

# Anfrage-Cooldown: max. eine Anfrage je X Minuten pro Spur
ANFRAGE_COOLDOWN_MIN = 10


# ===== TELEGRAM-INTEGRATION =====

TELEGRAM_POLL_TIMEOUT_S = 30
TELEGRAM_MSG_RETRY_MAX = 3
TELEGRAM_MSG_RETRY_DELAY_S = 2

# Nachrichtentypen: log-level im Telegram
TELEGRAM_LOG_LEVEL = logging.WARNING  # nur WARNING und ERROR


# ===== DATEN-INTEGRATION =====

# Maximale Anzahl Datensaetze im Journal (rotiert nach dieser Groesse)
JOURNAL_MAX_ROWS = 10000

# Maximale Anzahl Positionen in Status-Output
STATUS_MAX_POSITIONEN = 50

# Maximale Anzahl Trades im Bericht
BERICHT_MAX_TRADES = 100


# ===== UEBERWACHUNGS-SCHWELLEN =====

class ThresholdConfig:
    """Automatische Ueberwachungs-Schwellen."""
    
    # Equity-Drawdown: stoppe alle Spuren wenn >= diesen Anteil
    STOP_ON_DD_RATIO = 0.30  # 30%
    
    # Tagesgewinn/Verlust: Warnung bei diese Groesse
    DAILY_LOSS_THRESHOLD = -1000.0  # USD
    
    # Offene Positionen: Warnung wenn mehr als
    MAX_OPEN_POSITIONS = 20
    
    # Position-Groesse: Warnung wenn eine Position groesser ist als
    MAX_POSITION_SIZE = 10000.0  # USD
    
    # Margin-Nutzung (Futures): Warnung ab X%
    MARGIN_WARNING_PCT = 50.0
    MARGIN_CRITICAL_PCT = 80.0


def validate_config() -> bool:
    """Validiere Konfigurationskonsistenz.
    
    Returns:
        True wenn OK, False wenn Fehler
    """
    errors = []
    
    # Pruefen Sie Spur-Definitionen
    for spur_name, spur_config in SPUREN.items():
        if not spur_config.ordner:
            errors.append(f"Spur {spur_name}: ordner nicht gesetzt")
        if not spur_config.waehrung:
            errors.append(f"Spur {spur_name}: waehrung nicht gesetzt")
    
    # Pruefen Sie Risiko-Stufen
    if STANDARD_STUFE not in RISIKO_STUFEN:
        errors.append(f"STANDARD_STUFE '{STANDARD_STUFE}' nicht in RISIKO_STUFEN")
    
    # Pruefen Sie Timer
    if TIMEOUT_S <= 600:  # < Freigabefenster-Limit
        errors.append(f"TIMEOUT_S ({TIMEOUT_S}s) muss > 600s sein")
    
    if errors:
        for error in errors:
            log.error(f"Konfigurationsfehler: {error}")
        return False
    
    log.info(f"Konfiguration validiert: {len(SPUREN)} Spuren, {len(RISIKO_STUFEN)} Risikostufen")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
    validate_config()
    
    print("\n=== Spuren ===")
    for name, config in SPUREN.items():
        print(f"  {name}: {config}")
    
    print("\n=== Risiko-Stufen ===")
    for name, stufe in RISIKO_STUFEN.items():
        print(f"  {name}: {stufe.beschreibung()}")
