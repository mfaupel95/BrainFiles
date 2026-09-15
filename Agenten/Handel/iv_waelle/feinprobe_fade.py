"""Feinprobe: Zahlt der Fade an der Spannengrenze in irgendeiner Einstellung?

Gerastert werden Grenzweite (k), Stopabstand (in Sigma) und Zielanteil
(1.0 = zurueck zur Tagesmitte, 0.5 = halber Weg). Ausgabe ist eine Matrix,
damit ein einzelner Treffer nicht mit einem Befund verwechselt wird - erst ein
Zusammenhang ueber benachbarte Felder ist ein Hinweis.
"""
from __future__ import annotations

import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import backtest_iv_waelle as b  # noqa: E402
import daten  # noqa: E402
import iv_waelle as k  # noqa: E402


def runde(tage: dict, iv_je_tag: dict, kk: float, stop_sigma: float,
          ziel_anteil: float) -> list:
    rundungen = []
    for tag in sorted(tage):
        iv = iv_je_tag.get(tag)
        kerzen = tage[tag]
        if iv is None or len(kerzen) < 4:
            continue
        offen = kerzen[0]["open"]
        sigma = k.tages_sigma(offen, iv)
        oben, unten = offen + kk * sigma, offen - kk * sigma
        for seite, grenze in (("short", oben), ("long", unten)):
            for i, balken in enumerate(kerzen):
                beruehrt = balken["high"] >= grenze if seite == "short" \
                    else balken["low"] <= grenze
                if not beruehrt:
                    continue
                einstieg = grenze
                ziel = einstieg - ziel_anteil * (einstieg - offen) if seite == "short" \
                    else einstieg + ziel_anteil * (offen - einstieg)
                stop = einstieg + stop_sigma * sigma if seite == "short" \
                    else einstieg - stop_sigma * sigma
                ergebnis = None
                for j in range(i, len(kerzen)):
                    balken_j = kerzen[j]
                    if seite == "short":
                        if balken_j["high"] >= stop:
                            ergebnis = stop
                            break
                        if balken_j["low"] <= ziel:
                            ergebnis = ziel
                            break
                    else:
                        if balken_j["low"] <= stop:
                            ergebnis = stop
                            break
                        if balken_j["high"] >= ziel:
                            ergebnis = ziel
                            break
                if ergebnis is None:
                    ergebnis = kerzen[-1]["close"]
                brutto = (einstieg - ergebnis) / einstieg if seite == "short" \
                    else (ergebnis - einstieg) / einstieg
                rundungen.append({"tag": tag, "seite": seite,
                                  "brutto_prozent": brutto * 100.0,
                                  "netto_prozent": (brutto - 2 * b.GEBUEHR_JE_SEITE) * 100.0,
                                  "stop_getroffen": abs(ergebnis - stop) < 1e-9})
                break
    return rundungen


def haupt():
    spot = daten.indexpreis("btc_usd")
    dvol_reihe = daten.dvol_tagesreihe("BTC", tage=400)
    kerzen = daten.minutenkerzen("BTC-PERPETUAL", "60", tage=400)
    dvol = b.dvol_je_tag(dvol_reihe)
    tage = b.tage_aus_kerzen(kerzen)
    tagnamen = sorted(tage)
    iv_je_tag = {tagnamen[i]: dvol[tagnamen[i - 1]]
                 for i in range(1, len(tagnamen)) if tagnamen[i - 1] in dvol}
    print(f"Kurs {spot:.0f}, {len(iv_je_tag)} Tage mit Vortages-IV\n")

    for kk in (k.K_68, k.K_90):
        for ziel_anteil in (1.0, 0.5):
            print(f"--- Grenze k={kk:.3f}, Zielanteil {ziel_anteil:.1f} ---")
            kopf = "  Stop(Sigma) |" + "".join(f"{s:>7.2f}" for s in (0.2, 0.35, 0.5, 1.0))
            print(kopf)
            for was in ("je_Runde", "n", "Treffer"):
                zeile = f"  {was:<11s} |"
                for stop_sigma in (0.2, 0.35, 0.5, 1.0):
                    r = runde(tage, iv_je_tag, kk, stop_sigma, ziel_anteil)
                    kz = b.kennzahlen(r)
                    if was == "je_Runde":
                        zeile += f"{kz['mittel_netto_prozent']:>7.3f}"
                    elif was == "n":
                        zeile += f"{kz['n']:>7d}"
                    else:
                        zeile += f"{kz['trefferquote']:>7.1f}"
                print(zeile)
            print()


if __name__ == "__main__":
    haupt()
