"""Gueteproben der IV-Wand-Spur auf echten Deribit-Daten.

Zwei Fragen, getrennt beantwortet:

  A) HAELT DIE SPANNE? - Deckt die aus der Vortages-IV gerechnete Spanne den
     Tag wirklich ab? (Die Behauptung aus dem Video.)
  B) ZAHLT DER FADE?  - Wenn der Kurs die Spannengrenze beruehrt und man dagegen
     handelt (Stop dahinter, Ziel zurueck zur Mitte), bleibt dann etwas uebrig?

Kein Blick nach vorn: die Spanne fuer Tag D wird aus dem DVOL-Schluss von Tag
D-1 und dem Tageroeffnungskurs gebaut.

Was hier NICHT gemessen werden kann: der Wand-Filter. Das offene Interesse je
Strike gibt es bei Deribit nur als Momentaufnahme, keine Historie - die Waende
gehen in diese Gueteproben nicht ein, nur Spanne und Fade.
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))

import daten  # noqa: E402
import iv_waelle as k  # noqa: E402

GEBUEHR_JE_SEITE = 0.0005  # Deribit-Taker, konservativ


def tage_aus_kerzen(kerzen: dict) -> dict:
    """Stundenkerzen nach UTC-Tag buendeln."""
    tage: dict = {}
    for i, tick in enumerate(kerzen["ticks"]):
        tag = datetime.fromtimestamp(tick / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        tage.setdefault(tag, []).append({
            "ts": tick,
            "open": kerzen["open"][i],
            "high": kerzen["high"][i],
            "low": kerzen["low"][i],
            "close": kerzen["close"][i],
        })
    return tage


def dvol_je_tag(reihe: list) -> dict:
    """Tages-DVOL: Schluessel = Tag, Wert = Schlusskurs des Tages."""
    aus: dict = {}
    for eintrag in reihe:
        tag = k.tag_in_utc(eintrag[0])
        aus[tag] = eintrag[4]
    return aus


def pruefe_spanne(tage: dict, dvol: dict, jahres_iv_je_tag: dict,
                  ks=(k.K_68, 1.282, k.K_90), fenster_hv: int = 20) -> list:
    """Anteil der Tage, die vollstaendig (und per Schlusskurs) in der Spanne lagen."""
    tagnamen = sorted(tage)
    schlussreihe: list = []
    zeilen = []
    for tag in tagnamen:
        kerzen = tage[tag]
        if not kerzen:
            continue
        offen = kerzen[0]["open"]
        hoch = max(b["high"] for b in kerzen)
        tief = min(b["low"] for b in kerzen)
        schluss = kerzen[-1]["close"]
        schlussreihe.append(schluss)
        if jahres_iv_je_tag is None:
            continue
        iv = jahres_iv_je_tag.get(tag)
        if iv is None:
            continue
        hv = k.hist_vol_prozent(schlussreihe[:-1], fenster_hv)
        zeile = {"tag": tag, "offen": offen, "hoch": hoch, "tief": tief,
                 "schluss": schluss, "iv_wert": iv, "hv_wert": hv}
        for name, wert in (("iv", iv), ("hv", hv), ("misch", k.mische_iv_hv(iv, hv))):
            if wert is None:
                continue
            zeile[name] = {}
            sp = k.spanne(offen, wert, ks[-1])
            sigma = sp["sigma"]
            for kk in ks:
                drin = (tief >= offen - kk * sigma) and (hoch <= offen + kk * sigma)
                schluss_drin = abs(schluss - offen) <= kk * sigma
                zeile[name][f"drin_{kk}"] = drin
                zeile[name][f"schluss_drin_{kk}"] = schluss_drin
        zeilen.append(zeile)
    return zeilen


def pruefe_fade(tage: dict, jahres_iv_je_tag: dict, kk: float,
                stop_sigma: float = 0.5, ziel: str = "mitte") -> dict:
    """Fade an der Spannengrenze, stundenweise, konservative Reihenfolge
    (Stop vor Ziel, wenn beides in derselben Stunde liegt)."""
    tagnamen = sorted(tage)
    rundungen = []
    for tag in tagnamen:
        iv = jahres_iv_je_tag.get(tag)
        kerzen = tage[tag]
        if iv is None or len(kerzen) < 4:
            continue
        offen = kerzen[0]["open"]
        sigma = k.tages_sigma(offen, iv)
        oben = offen + kk * sigma
        unten = offen - kk * sigma
        mitte = offen

        for seite, grenze in (("short", oben), ("long", unten)):
            for i, balken in enumerate(kerzen):
                beruehrt = (balken["high"] >= grenze) if seite == "short" \
                    else (balken["low"] <= grenze)
                if not beruehrt:
                    continue
                einstieg = grenze
                stop = einstieg + stop_sigma * sigma if seite == "short" \
                    else einstieg - stop_sigma * sigma
                ziel_kurs = mitte
                ergebnis = None
                # die Einstiegskerze selbst zuerst pruefen (konservativ)
                for j in range(i, len(kerzen)):
                    b = kerzen[j]
                    if seite == "short":
                        if b["high"] >= stop:
                            ergebnis = stop
                            break
                        if b["low"] <= ziel_kurs:
                            ergebnis = ziel_kurs
                            break
                    else:
                        if b["low"] <= stop:
                            ergebnis = stop
                            break
                        if b["high"] >= ziel_kurs:
                            ergebnis = ziel_kurs
                            break
                if ergebnis is None:
                    ergebnis = kerzen[-1]["close"]
                if seite == "short":
                    brutto = (einstieg - ergebnis) / einstieg
                else:
                    brutto = (ergebnis - einstieg) / einstieg
                netto = brutto - 2 * GEBUEHR_JE_SEITE
                rundungen.append({
                    "tag": tag, "seite": seite,
                    "einstieg": einstieg, "ausstieg": ergebnis,
                    "brutto_prozent": brutto * 100.0, "netto_prozent": netto * 100.0,
                    "abstand_grenze_prozent": abs(grenze - offen) / offen * 100.0,
                })
                break  # je Seite und Tag hoechstens eine Runde
    return {"rundungen": rundungen, "kennzahlen": kennzahlen(rundungen)}


def kennzahlen(rundungen: list) -> dict:
    if not rundungen:
        return {"n": 0}
    netto = [r["netto_prozent"] for r in rundungen]
    brutto = [r["brutto_prozent"] for r in rundungen]
    gewinne = [x for x in netto if x > 0]
    return {
        "n": len(rundungen),
        "trefferquote": len(gewinne) / len(netto) * 100.0,
        "summe_netto_prozent": sum(netto),
        "mittel_netto_prozent": statistics.mean(netto),
        "mittel_brutto_prozent": statistics.mean(brutto),
        "bester": max(netto), "schlechtester": min(netto),
        "median": statistics.median(netto),
    }


def haupt():
    print("Backtest IV-Wand-Spur (Deribit, oeffentlich)")
    kette = daten.optionskette("BTC", frisch=True)
    spot = daten.indexpreis("btc_usd")
    dvol_reihe = daten.dvol_tagesreihe("BTC", tage=400)
    kerzen = daten.minutenkerzen("BTC-PERPETUAL", "60", tage=400)
    dvol = dvol_je_tag(dvol_reihe)
    tage = tage_aus_kerzen(kerzen)
    print(f"Kurs {spot:.0f} | DVOL-Tage {len(dvol)} | Handelstage {len(tage)} "
          f"| Optionsinstrumente {len(kette)}")

    # Waende (Momentaufnahme, geht nicht in den Backtest ein)
    waende = k.waende(kette, spot)
    print("\n--- Waende jetzt ---")
    for name in ("call_wand", "put_wand"):
        w = waende[name]
        print(f"{name:10s}: " + (f"Strike {w['strike']:.0f} OI {w['oi']:.0f} "
                                 f"IV {w['iv']:.1f} % Abstand {w['abstand_prozent']:+.2f} %"
                                 if w else "keine"))

    # A) Deckt die Spanne den Tag ab?  Vortages-IV, kein Blick nach vorn.
    tagnamen = sorted(tage)
    iv_je_tag = {}
    for i in range(1, len(tagnamen)):
        vorher = dvol.get(tagnamen[i - 1])
        if vorher is not None:
            iv_je_tag[tagnamen[i]] = vorher
    zeilen = pruefe_spanne(tage, dvol, iv_je_tag)
    print(f"\n--- A) Spanne: {len(zeilen)} Tage geprueft ---")
    for quelle in ("iv", "hv", "misch"):
        for kk in (k.K_68, 1.282, k.K_90):
            werte = [z[quelle][f"drin_{kk}"] for z in zeilen if quelle in z]
            schluss = [z[quelle][f"schluss_drin_{kk}"] for z in zeilen if quelle in z]
            if not werte:
                continue
            print(f"{quelle:5s} k={kk:5.3f}: vollstaendig drin "
                  f"{100.0 * sum(werte) / len(werte):5.1f} %  "
                  f"(Schlusskurs drin {100.0 * sum(schluss) / len(schluss):5.1f} %)  "
                  f"n={len(werte)}")

    # B) Zahlt der Fade?
    print("\n--- B) Fade an der Spannengrenze ---")
    gesamt = {}
    for quelle_name, quellen_iv in (("Vortages-IV", iv_je_tag),):
        for kk in (k.K_68, 1.282, k.K_90):
            for stop_sigma in (0.5, 1.0):
                ergebnis = pruefe_fade(tage, quellen_iv, kk, stop_sigma)
                kz = ergebnis["kennzahlen"]
                if kz["n"] == 0:
                    continue
                print(f"{quelle_name} k={kk:5.3f} stop={stop_sigma:.1f} Sigma: "
                      f"n={kz['n']:3d} Treffer {kz['trefferquote']:5.1f} % "
                      f"Netto-Summe {kz['summe_netto_prozent']:+7.2f} % "
                      f"je Runde {kz['mittel_netto_prozent']:+6.3f} % "
                      f"Median {kz['median']:+6.3f} %")
                gesamt[f"k{kk}_stop{stop_sigma}"] = {"kennzahlen": kz,
                                                     "rundungen": ergebnis["rundungen"]}

    # Aufteilen: obere und untere Grenze einzeln
    print("\n--- B2) Fade getrennt nach Seite (k=%.3f, stop=0.5) ---" % k.K_68)
    for kk in (k.K_68, k.K_90):
        ergebnis = pruefe_fade(tage, iv_je_tag, kk, 0.5)
        for seite in ("short", "long"):
            teil = [r for r in ergebnis["rundungen"] if r["seite"] == seite]
            kz = kennzahlen(teil)
            if kz["n"]:
                print(f"k={kk:5.3f} {seite:5s}: n={kz['n']:3d} "
                      f"Treffer {kz['trefferquote']:5.1f} % "
                      f"Summe {kz['summe_netto_prozent']:+7.2f} % "
                      f"je Runde {kz['mittel_netto_prozent']:+6.3f} %")

    (HIER / "backtest_ergebnis.json").write_text(
        json.dumps({"spot": spot, "waende": waende, "fade": gesamt},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nErgebnis geschrieben: backtest_ergebnis.json")


if __name__ == "__main__":
    haupt()
