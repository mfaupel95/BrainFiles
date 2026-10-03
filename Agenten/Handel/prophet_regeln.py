"""Prophet-Signal: Saisonale Trend-Zerlegung nach dem CryptoPredictions-Modell.

Das Paper zeigt Prophet als bestes Modell für Crypto-Prognosen. Der Kern:
1. Additive Zerlegung: y = Trend + Saisonalität + Rauschen
2. Trend: exponentielle Glättung (Holt-Winters)
3. Saisonalität: repetitives Muster in den Schlusspreisen

Diese Umsetzung ist eine vereinfachte Nachbildung ohne externe Abhängigkeiten
(Prophet selbst hat NumPy-Probleme im Scanner-venv):
- Trend: EMA mit 24H-Kerzen (täglicher Durchschnitt)
- Saisonalität: SMA5 über die Wochentagsmuster (7 Tage)
- Forecast: Trend + Saisonalität der nächsten Periode

Regel: Long wenn Trend steigt UND Saisonalität aufweist,
       Short wenn Trend fällt UND Saisonalität aufweist.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

HANDEL = Path(__file__).resolve().parent


# --- Indikator: Vereinfachte Prophet-Nachbildung -----

def ema(w, n):
    """Exponential Moving Average wie Klassik."""
    out = [None] * len(w)
    if len(w) < n:
        return out
    v = sum(w[:n]) / n
    out[n - 1] = v
    f = 2.0 / (n + 1)
    for i in range(n, len(w)):
        v = w[i] * f + v * (1 - f)
        out[i] = v
    return out


def sma(w, n):
    """Simple Moving Average."""
    out = [None] * len(w)
    if n <= 0 or len(w) < n:
        return out
    s = sum(w[:n])
    out[n - 1] = s / n
    for i in range(n, len(w)):
        s += w[i] - w[i - n]
        out[i] = s / n
    return out


def prophet_trend_saisonalitaet(kerzen, trend_n=30, saisonalitaet_n=7):
    """Trend (EMA30) + Saisonalität (5-Tages-Muster) nach Prophet-Idee.
    
    Args:
        kerzen: Liste [ts, o, h, l, c, v]
        trend_n: EMA-Periode für Trend (Tage; bei 4H-Kerzen ~6 Kerzen)
        saisonalitaet_n: Periodenlaenge (7 = Wochenzyklus)
    
    Returns:
        (trend, saison): Listen mit None wo noch nicht definiert
    """
    # Schluesse extrahieren
    c = [float(z[4]) for z in kerzen]
    
    # Trend: EMA der Schluesse
    trend = ema(c, trend_n)
    
    # Saisonalität: Abweichung vom Trend mit Wochentagszyklus
    saison = [None] * len(c)
    if len(c) >= saisonalitaet_n + trend_n:
        # Ab Trend-Start: (Schluss - Trend) / Trend als prozentuale Abweichung
        for i in range(trend_n, len(c)):
            if trend[i] is not None:
                saison[i] = (c[i] - trend[i]) / trend[i] if trend[i] != 0 else 0
    
    return trend, saison


def trend_richtung(kerzen, trend_n=30, min_kerzen=60):
    """Trend-Richtung: steigend (1), fallend (-1), flach (0), oder None (keine Daten).
    
    Vergleicht EMA gegen die vorherige Position: ist es um >0,1% gestiegen = long,
    ist es um >0,1% gefallen = short, sonst flach.
    """
    if len(kerzen) < min_kerzen:
        return None
    
    c = [float(z[4]) for z in kerzen]
    trend = ema(c, trend_n)
    
    if trend[-1] is None or trend[-2] is None:
        return None
    
    diff_pct = (trend[-1] - trend[-2]) / trend[-2] if trend[-2] != 0 else 0
    
    if diff_pct > 0.001:  # >0,1% Anstieg
        return 1  # Aufwärtstrend
    elif diff_pct < -0.001:  # <-0,1% Abstieg
        return -1  # Abwärtstrend
    else:
        return 0  # Flach


def saisonalitaet_staerke(kerzen, trend_n=30, min_kerzen=60):
    """Stärke der Saisonalität als Indikator für Zuverlässigkeit (0..1).
    
    Höhere Saisonalität = repetitives Muster erkannt = Signal zuverlässiger.
    Berechnet als: Standardabweichung der Abweichungen / Volatilität.
    """
    if len(kerzen) < min_kerzen:
        return None
    
    c = [float(z[4]) for z in kerzen]
    trend, saison = prophet_trend_saisonalitaet(kerzen, trend_n)
    
    # Saisonalitäten sammeln (letzte 30 Kerzen)
    s_recent = [s for s in saison[-30:] if s is not None]
    if not s_recent:
        return 0
    
    # Standardabweichung der Abweichungen
    mean_saison = sum(s_recent) / len(s_recent)
    var = sum((s - mean_saison) ** 2 for s in s_recent) / len(s_recent)
    sd_saison = var ** 0.5
    
    # Normalisieren auf 0..1 (>3% Saisonalität = sehr stark)
    return min(1.0, sd_saison / 0.03)


# --- Einstiegs-/Ausstiegsregeln ---

def einstieg(k, w):
    """Prophet-Signal: Long bei Aufwärtstrend, Short bei Abwärtstrend.
    
    Mit Mindeststärke der Saisonalität (w['saison_min'] Default 0.2).
    """
    trend_richtung_val = trend_richtung(k, int(w.get('trend_n', 30)), int(w.get('mindest_kerzen', 60)))
    if trend_richtung_val is None:
        return None
    
    saison_staerke = saisonalitaet_staerke(k, int(w.get('trend_n', 30)), int(w.get('mindest_kerzen', 60)))
    min_saison = float(w.get('saison_min', 0.2))
    
    if saison_staerke is None or saison_staerke < min_saison:
        return None  # Keine zuverlässige Saisonalität
    
    if trend_richtung_val > 0:
        return "long"
    elif trend_richtung_val < 0:
        return "short"
    else:
        return None  # Flache Seitwärtsbewegung


def ausstieg(k, seite, w):
    """Ausstieg bei Gegensignal (Trend-Umkehr)."""
    trend_richtung_val = trend_richtung(k, int(w.get('trend_n', 30)), int(w.get('mindest_kerzen', 60)))
    if trend_richtung_val is None:
        return None
    
    # Long: Ausstieg bei Abwärtstrend oder Flach
    if seite == "long" and trend_richtung_val <= 0:
        return "trend_umkehr"
    
    # Short: Ausstieg bei Aufwärtstrend oder Flach
    if seite == "short" and trend_richtung_val >= 0:
        return "trend_umkehr"
    
    return None


# --- Anschluss an spur_buch ---

def _lade(pfad, name):
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_okx = None
_cache = {}


def _kerzen(inst, bar, anzahl):
    """OKX-Kerzen mit 60s Cache."""
    global _okx
    schluessel = (inst, bar, anzahl)
    jetzt = time.time()
    alt = _cache.get(schluessel)
    if alt and jetzt - alt[0] < 60:
        return alt[1]
    if _okx is None:
        sc = str(HANDEL / "scanner")
        if sc not in sys.path:
            sys.path.insert(0, sc)
        _okx = _lade(HANDEL / "scanner" / "okx.py", "okx_prophet")
    roh = _okx.kerzen(inst, bar=bar, anzahl=anzahl)
    k = roh[:-1] if roh else []
    _cache[schluessel] = (jetzt, k)
    return k


def bauen(name):
    """(quelle, signal, ausstieg) für die Spur."""
    def quelle(w):
        bar = w.get("kerzen_zeitrahmen", "4H")
        anzahl = int(w.get("kerzen_anzahl", 400))
        daten, kurse, fehler = {}, {}, []
        for inst in w.get("instrumente", ["BTC-USDT-SWAP"]):
            try:
                k = _kerzen(inst, bar, anzahl)
            except Exception as e:
                fehler.append("%s: Kerzen nicht abrufbar (%s)" % (inst, str(e)[:100]))
                continue
            if not k:
                fehler.append("%s: keine Kerzen" % inst)
                continue
            daten[inst] = {"kerzen": k, "bar": bar}
            kurse[inst] = float(k[-1][4])
        return daten, kurse, fehler

    def signal(d, w):
        k = d.get("kerzen") or []
        if len(k) < int(w.get("mindest_kerzen", 60)):
            return None
        try:
            return einstieg(k, w)
        except Exception as e:
            print("  prophet_signal: Regel nicht rechenbar (%s)" % e, file=sys.stderr)
            return None

    def signal_ausstieg(p, w):
        if not w.get("ausstieg_bei_regel", True):
            return None
        inst = p.get("inst") or p.get("instrument")
        bar = w.get("kerzen_zeitrahmen", "4H")
        try:
            k = _kerzen(inst, bar, int(w.get("kerzen_anzahl", 400)))
        except Exception:
            return None
        if len(k) < int(w.get("mindest_kerzen", 60)):
            return None
        seite = (p.get("seite") or "").lower()
        if seite not in ("long", "short"):
            return None
        return ausstieg(k, seite, w)

    return quelle, signal, signal_ausstieg


def spur_main(name, ordner, bus_name=None):
    """Gemeinsamer Startpunkt wie klassik_regeln."""
    import argparse
    quelle, signal, signal_ausstieg = bauen(name)
    sp = _lade(HANDEL / "spur_buch.py", "spur_buch_" + name)
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = p.add_mutually_exclusive_group()
    for opt, c, h in (("--vorschau", "vorschau", "nur rechnen, nichts schreiben"),
                      ("--papier", "papier", "Papierbuch (Standard)"),
                      ("--live", "live", "verweigert: kein Live-Zweig"),
                      ("--wachen", "wachen", "nur den Wachenstand zeigen")):
        g.add_argument(opt, action="store_const", dest="modus", const=c, help=h)
    modus = p.parse_args().modus or "papier"
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if modus == "live":
        print("Live waere gesperrt durch: kein Live-Zweig in dieser Spur "
              "(Papier, Prognosemodell ohne Orderweg).")
        return 0
    return sp.zyklus(str(ordner), quelle, signal, modus,
                     ereignis_name=bus_name or ("handel/" + name),
                     zusatz_ausstieg=signal_ausstieg)
