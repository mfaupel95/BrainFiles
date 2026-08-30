"""
Kursdaten holen und lokal zwischenspeichern.

Der Cache ist Absicht: yfinance ist eine inoffizielle Schnittstelle, die ohne
Vorwarnung ausfallen kann. Liegen die Daten lokal, laeuft die Simulation auch
dann weiter - sie sagt dann nur dazu, wie alt der Stand ist.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DATEN_DIR = Path(__file__).resolve().parent / "daten"
CACHE_MAX_STUNDEN = 12


def cache_pfad(ticker):
    return DATEN_DIR / f"{ticker.upper()}.csv"


def cache_alter_stunden(pfad):
    if not pfad.exists():
        return None
    alter = datetime.now(timezone.utc).timestamp() - pfad.stat().st_mtime
    return alter / 3600


def _laden_vom_netz(ticker):
    import yfinance as yf

    df = yf.Ticker(ticker).history(period="max", auto_adjust=True)
    if df.empty:
        raise RuntimeError(f"keine Daten fuer {ticker}")
    df = df[["Open", "High", "Low", "Close"]].copy()
    df.index = df.index.tz_localize(None).normalize()
    df.index.name = "Datum"
    return df


def laden(ticker, erzwinge_aktualisierung=False, still=False):
    """Gibt (DataFrame, quelle) zurueck. quelle ist 'netz' oder 'cache (N h alt)'."""
    import pandas as pd

    ticker = ticker.upper()
    pfad = cache_pfad(ticker)
    alter = cache_alter_stunden(pfad)

    frisch_genug = alter is not None and alter < CACHE_MAX_STUNDEN
    if frisch_genug and not erzwinge_aktualisierung:
        df = pd.read_csv(pfad, index_col="Datum", parse_dates=True)
        return df, f"Cache ({alter:.0f} h alt)"

    try:
        df = _laden_vom_netz(ticker)
        DATEN_DIR.mkdir(parents=True, exist_ok=True)
        df.to_csv(pfad)
        return df, "abgerufen"
    except Exception as e:
        if pfad.exists():
            if not still:
                print(f"  Hinweis: Abruf fehlgeschlagen ({type(e).__name__}), nutze Cache.")
            df = pd.read_csv(pfad, index_col="Datum", parse_dates=True)
            return df, f"Cache ({alter:.0f} h alt, Abruf fehlgeschlagen)"
        raise


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else "PLTR"
    df, quelle = laden(t, erzwinge_aktualisierung="--neu" in sys.argv)
    print(f"{t}: {len(df)} Handelstage, {df.index[0].date()} bis {df.index[-1].date()} | {quelle}")
    print(f"Letzter Schluss: {df['Close'].iloc[-1]:.2f}")
