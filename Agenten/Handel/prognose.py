"""Prognose: sucht ueber den ganzen Markt nach guenstigen Einstiegen.

Angelegt am 11.09.2026 auf Max' Anweisung ("bei sehr guenstigen
Einstiegsgelegenheiten ueber alle Maerkte hinweg scannen und melden").

WAS ER IST
Der Marktscanner (scanner/scan.py) sieht eine Watchlist von elf Werten an und
liefert die Rangliste, aus der handeln.py kauft. Prognose sieht den *ganzen*
Markt an und sucht Lagen mit einem klaren Verhaeltnis von Chance zu Risiko -
und nennt die Richtung dazu:

  LONG   - Ruecksetzer in einem Aufwaertstrend (Preis ueber dem SMA, RSI nicht
           ueberhitzt, Abstand zum 60-Tage-Hoch). Das Ziel ist das Hoch.
  SHORT  - das Spiegelbild: Erholung in einem Abwaertstrend (Preis unter dem
           SMA, RSI nicht ueberverkauft, Abstand zum 60-Tage-Tief). Das Ziel
           ist das Tief.

Jede Zeile traegt ihre Richtung als Spalte, die Meldung nennt sie im Text.
Beide Richtungen kommen aus derselben Bewertung (bewertung.bewerten mit
richtung=) und denselben Toren - die Short-Seite ist die gespiegelte Frage,
keine zweite Formel. Was die Tore nicht passiert, wird nicht gemeldet.

WAS ER NICHT IST
Er handelt nicht. Kein Orderaufruf, keine Position, kein Zustand. prognose.py
liest Kurse und schreibt einen Bericht. Die Grenzen aus wachen.json gelten fuer
ihn nicht, weil er keine Order stellt - er ist ein Beobachter, keine Spur.

WOHER DIE ZAHLEN KOMMEN
Dieselben zwei Bausteine wie im Scanner: okx.kerzen() (oeffentlich, kein
Schluessel noetig) und bewertung.bewerten(). Der Rechenweg ist damit derselbe,
der auch die Kaeufe des Scanners auswaehlt - Prognose erfindet keine zweite
Formel und keine zweite Wahrheit.

Die Tore stehen in prognose.json, nicht im Code: dieselbe Trennung wie bei
wachen.json. Ein Tor aendern heisst, die Datei aendern - und das ist Stufe 1
mit Sicherung, echtem Lauf und Commit.

Aufruf:
    python prognose.py                  # ganzer Markt, Bericht + Meldung
    python prognose.py --kurz           # nur die Tabellen, nichts schreiben
    python prognose.py --alle           # alles zeigen, Tore nur als Spalte
    python prognose.py --ohne-meldung   # Bericht schreiben, nichts senden
    python prognose.py --werte 60       # nur die 60 umsatzstaerksten Maerkte
"""

import argparse
import html
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "scanner"))
sys.path.insert(0, str(HIER / os.pardir / "Bus"))

import bewertung                                          # noqa: E402
import okx                                                # noqa: E402

# Fassung (24.09.2026): PROGNOSE_FASSUNG=weit liest prognose_weit.json und
# schreibt neuester_weit.json. Damit laesst sich eine WEICHE Fassung der Tore
# rechnen, ohne die strenge anzufassen - die strenge Quelle bleibt fuer den
# Hauptarm und den Kraken-Papierzweig unveraendert. Ohne die Variable aendert
# sich nichts.
FASSUNG = (os.environ.get("PROGNOSE_FASSUNG") or "").strip()


def _fassung(name):
    """neuester.json -> neuester.weit.json (ohne Fassung: unveraendert).

    Punkt wie bei den Buchdateien (zustand.weit.json, handelsjournal.knapp.csv) -
    damit dieselbe Form ueberall.
    """
    if not FASSUNG:
        return name
    stamm, endung = os.path.splitext(name)
    return "%s.%s%s" % (stamm, FASSUNG, endung)


KONFIG = HIER / _fassung("prognose.json")
BERICHTE = HIER / "prognose_berichte"


def konfig():
    return json.loads(KONFIG.read_text("utf-8"))


# --- Kennzahlen, die bewertung.py nicht liefert -------------------------------

def _sma(werte, n):
    if len(werte) < n:
        return None
    return sum(werte[-n:]) / n


def stopp_und_ziel(kerzen, tore, richtung="long"):
    """Stop, Ziel und Chance-Risiko-Verhaeltnis einer Lage.

    Long: Der Stop liegt unter dem Tief der letzten 20 Tage, aber nie weiter
    als stop_max_pct unter dem Preis - ein Stop, der 40 % weg liegt, ist kein
    Stop, sondern eine Hoffnung. Das Ziel ist das Hoch der letzten 60 Tage.
    Short ist das Spiegelbild: Stop ueber dem Hoch der letzten 20 Tage, Ziel
    das Tief der letzten 60 Tage. Beide Zahlen sind gerechnet, nicht
    geschaetzt; wird das Ziel nicht erreicht, sagt das der C/R-Wert, statt
    dass das Ziel hochgezogen wird - ein Ziel, das immer das geforderte
    Verhaeltnis herstellt, macht das Verhaeltnis als Tor wertlos.
    """
    schluss = [k[4] for k in kerzen]
    hoch = [k[2] for k in kerzen]
    tief = [k[3] for k in kerzen]
    preis = schluss[-1]

    tief20 = min(tief[-20:]) if len(tief) >= 20 else min(tief)
    hoch20 = max(hoch[-20:]) if len(hoch) >= 20 else max(hoch)
    hoch60 = max(hoch[-60:]) if len(hoch) >= 60 else max(hoch)
    tief60 = min(tief[-60:]) if len(tief) >= 60 else min(tief)

    if richtung == "short":
        stop = max(hoch20, preis * (1.0 + tore["stop_min_pct"] / 100.0))
        stop = min(stop, preis * (1.0 + tore["stop_max_pct"] / 100.0))
        if stop <= preis:                  # entartet, wenn das Hoch am Preis klebt
            stop = preis * (1.0 + tore["stop_min_pct"] / 100.0)
        ziel = tief60
        risiko_pct = (stop - preis) / preis * 100.0
        abstand = stop - preis
        cr = (preis - ziel) / abstand if abstand > 0 else 0.0
    else:
        stop = min(tief20, preis * (1.0 - tore["stop_min_pct"] / 100.0))
        stop = max(stop, preis * (1.0 - tore["stop_max_pct"] / 100.0))
        if stop >= preis:                  # entartet, wenn das Tief am Preis klebt
            stop = preis * (1.0 - tore["stop_min_pct"] / 100.0)
        ziel = hoch60
        risiko_pct = (preis - stop) / preis * 100.0
        abstand = preis - stop
        cr = (ziel - preis) / abstand if abstand > 0 else 0.0

    return {"stop": stop, "ziel": ziel, "risiko_pct": risiko_pct,
            "cr": cr, "tief20": tief20, "hoch20": hoch20,
            "hoch60": hoch60, "tief60": tief60}


def lage(inst, kerzen, tore, richtung="long"):
    """Eine Zeile des Berichts: Bewertung, gerechnete Grenzen, offene Tore.

    Die Richtung entscheidet, welche Tore gelten. Long prueft den Ruecksetzer
    im Aufwaertstrend (Abstand zum 60-Tage-Hoch), Short die Erholung im
    Abwaertstrend (Abstand zum 60-Tage-Tief); RSI- und Trend-Tor sind
    spiegelbildlich.
    """
    b = bewertung.bewerten(kerzen, richtung=richtung)
    k = b["kennzahlen"]
    schluss = [x[4] for x in kerzen]
    preis = schluss[-1]

    s = stopp_und_ziel(kerzen, tore, richtung)
    sma_n = tore.get("trend_ueber_sma", 100)
    sma = _sma(schluss, sma_n)

    # Volumen der letzten 5 Tage gegen den 30-Tage-Schnitt. Unter 0,5 ist der
    # Markt eingeschlafen - dann fehlt die Gegenwehr, die einen Ruecksetzer
    # von einem Abschwung unterscheidet.
    vol = [x[5] for x in kerzen]
    v30 = _sma(vol, 30)
    v5 = (sum(vol[-5:]) / 5.0) if len(vol) >= 5 else None
    volumen_verhaeltnis = (v5 / v30) if (v5 is not None and v30) else None

    z = {
        "inst": inst,
        "richtung": richtung,
        "preis": preis,
        "score": b["score"],
        "chance": b["chance"],
        "risiko": b["risiko"],
        "verhaeltnis": b["verhaeltnis"],
        "stop": round(s["stop"], 6),
        "ziel": round(s["ziel"], 6),
        "risiko_prozent": round(s["risiko_pct"], 2),
        "cr": round(s["cr"], 2),
        "volumen_verhaeltnis": (round(volumen_verhaeltnis, 2)
                                if volumen_verhaeltnis is not None else None),
        "hoch60": round(s["hoch60"], 6),
        "tief20": round(s["tief20"], 6),
        "sma": round(sma, 6) if sma else None,
        "kennzahlen": k,
    }

    # --- die Tore -------------------------------------------------------
    offen = []
    # Short hat eine eigene Score-Schwelle: die Skala ist long-kalibriert
    # (siehe _mindest_score_short in prognose.json).
    mindest_score = (tore.get("mindest_score_short", tore["mindest_score"])
                     if richtung == "short" else tore["mindest_score"])
    if z["score"] < mindest_score:
        offen.append("Score %.1f < %g" % (z["score"], mindest_score))
    if richtung == "short":
        if k["rsi14"] < tore["mindest_rsi"]:
            offen.append("RSI %.1f < %g" % (k["rsi14"], tore["mindest_rsi"]))
        a = k["abstand_60t_tief_pct"]
        if not (tore["erholung_von_pct"] <= a <= tore["erholung_bis_pct"]):
            offen.append("Abstand zum Tief %.1f %% nicht zwischen %g und %g"
                         % (a, tore["erholung_von_pct"], tore["erholung_bis_pct"]))
    else:
        if k["rsi14"] > tore["hoechst_rsi"]:
            offen.append("RSI %.1f > %g" % (k["rsi14"], tore["hoechst_rsi"]))
        a = k["abstand_60t_hoch_pct"]
        if not (tore["ruecksetzer_von_pct"] <= a <= tore["ruecksetzer_bis_pct"]):
            offen.append("Abstand zum Hoch %.1f %% nicht zwischen %g und %g"
                         % (a, tore["ruecksetzer_von_pct"],
                            tore["ruecksetzer_bis_pct"]))
    if k["volatilitaet_pa"] > tore["max_volatilitaet_pa"]:
        offen.append("Vola %.2f > %g" % (k["volatilitaet_pa"],
                                         tore["max_volatilitaet_pa"]))
    if sma is None:
        offen.append("zu wenig Historie fuer SMA%d" % sma_n)
    elif richtung == "short" and preis >= sma:
        offen.append("Trend: Preis >= SMA%d" % sma_n)
    elif richtung == "long" and preis <= sma:
        offen.append("Trend: Preis <= SMA%d" % sma_n)
    if volumen_verhaeltnis is None:
        offen.append("zu wenig Historie fuers Volumen")
    elif volumen_verhaeltnis < tore["mindest_volumen_verhaeltnis"]:
        offen.append("Volumen %.2f < %g" % (volumen_verhaeltnis,
                                            tore["mindest_volumen_verhaeltnis"]))
    if z["cr"] < tore["mindest_cr"]:
        offen.append("Chance/Risiko %.2f < %g" % (z["cr"], tore["mindest_cr"]))

    z["offene_tore"] = offen
    z["guenstig"] = not offen
    return z


# --- Ausgabe ----------------------------------------------------------------

def zeige(titel, zeilen, grenze=None):
    print()
    print(titel)
    print("%-5s %-12s | %5s | %4s | %6s | %5s | %4s | %5s | %5s | %s"
          % ("Richt", "Markt", "Score", "RSI", "Hoch%", "Vola", "Vol", "Stop%", "C/R",
             "offene Tore"))
    print("-" * 112)
    for z in (zeilen if grenze is None else zeilen[:grenze]):
        k = z["kennzahlen"]
        abstand = (k["abstand_60t_tief_pct"] if z["richtung"] == "short"
                   else k["abstand_60t_hoch_pct"])
        print("%-5s %-12s | %5.1f | %4.1f | %6.1f | %5.2f | %4.2f | %4.1f%% | %5.2f | %s"
              % (z["richtung"].upper(), z["inst"], z["score"], k["rsi14"], abstand,
                 k["volatilitaet_pa"], z["volumen_verhaeltnis"] or 0.0,
                 z["risiko_prozent"], z["cr"],
                 "keine" if z["guenstig"] else "; ".join(z["offene_tore"])))


def meldung(treffer, geprueft, grenze):
    """Der Telegram-Text. Leer heisst: nichts gefunden, und das wird gesagt."""
    if not treffer:
        return ("<b>Prognose</b>: %d Maerkte geprueft, kein guenstiger Einstieg.\n"
                "Die Tore hat heute nichts passiert - dann wird auch nichts "
                "gemeldet." % geprueft)
    n_long = sum(1 for t in treffer if t["richtung"] == "long")
    z = ["<b>Prognose: %d guenstige Einstiege</b> (von %d Maerkten: %d LONG, %d SHORT)"
         % (len(treffer), geprueft, n_long, len(treffer) - n_long), ""]
    for t in treffer[:grenze]:
        lang = t["richtung"] == "long"
        z.append("<b>%s</b>  %s  Score %.1f  C/R %.2f"
                 % (html.escape(t["inst"]), t["richtung"].upper(),
                    t["score"], t["cr"]))
        z.append("  Einstieg %.6g  Stop %.6g (%s%.1f%%)  Ziel %.6g"
                 % (t["preis"], t["stop"], "-" if lang else "+",
                    t["risiko_prozent"], t["ziel"]))
        z.append("  RSI %.1f  %s %.1f%%  Vola %.2f"
                 % (t["kennzahlen"]["rsi14"],
                    "Ruecksetzer" if lang else "Erholung",
                    t["kennzahlen"]["abstand_60t_hoch_pct"] if lang
                    else t["kennzahlen"]["abstand_60t_tief_pct"],
                    t["kennzahlen"]["volatilitaet_pa"]))
    if len(treffer) > grenze:
        z.append("")
        z.append("... und %d weitere im Bericht." % (len(treffer) - grenze))
    z.append("")
    z.append("Kein Kauf: prognose.py stellt keine Order. Wer kaufen will, "
             "schaltet die Spur ueber das Freigabefenster scharf.")
    return "\n".join(z)


def lauf(kurz=False, alle=False, melden=True, werte=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    k = konfig()
    tore = k["tore"]
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Der Markt: alle Paare der konfigurierten Quote-Waehrungen ueber einem
    # Mindestumsatz, absteigend nach Umsatz. Zuerst der Umsatz, dann die
    # Kerzen - sonst zieht der Lauf an den toten Paaren die meiste Zeit.
    #
    # `maerkte` fehlt seit dem 05.10.2026 ABSICHTLICHT in beiden
    # Konfigurationen (Auftrag Max: "maerkte und werte erhoehen"). Der
    # ZUGRIFF hier ist deshalb mit .get() und nicht mit k["maerkte"]: ein
    # fehlender Schluessel ist "kein Quotefilter", und ein KeyError waere
    # ein Abbruch des Laufs. Gemessen am 05.10.: der Filter USDT+USDC
    # schloss 12 echte Kandidaten aus, ohne einen tauglichen zu retten
    # (BTC-EUR, BTC-BRL, CT-TRY, PI-TRY sind Fiat-Paare, die OKX-Spot
    # fuehrt und Kraken Futures nicht). `okx.alle_paare(quote=None)` heisst
    # "alle Quotes" - das ist die gewollte Breite, kein Versehen.
    paare = okx.alle_paare(quote=k.get("maerkte"),
                           min_volumen_usd=k["min_volumen_24h_usd"])
    if werte:
        paare = paare[:werte]
    print("=== Prognose %s | %d Maerkte ueber %s (Umsatz >= %g USD, 24 h) ==="
          % (heute, len(paare), ", ".join(k.get("maerkte") or ["alle Quotes"]),
             k["min_volumen_24h_usd"]))

    zeilen = []
    geprueft = 0
    for i, (inst, umsatz) in enumerate(paare, 1):
        try:
            kerzen = okx.kerzen(inst, "1D", 300)
            if len(kerzen) < 120:
                continue
            geprueft += 1
            for richtung in ("long", "short"):
                z = lage(inst, kerzen, tore, richtung)
                z["umsatz_24h_usd"] = round(umsatz)
                zeilen.append(z)
        except Exception as e:                            # noqa: BLE001
            print("  %-12s Fehler: %s" % (inst, e), file=sys.stderr)
        if i % 25 == 0:
            print("  ... %d/%d geprueft" % (i, len(paare)))
        time.sleep(k.get("pause_s", 0.12))

    if not zeilen:
        print("Kein Markt lieferte genug Historie.")
        return 1

    treffer = [z for z in zeilen if z["guenstig"]]
    treffer.sort(key=lambda z: z["cr"] * z["score"], reverse=True)
    rest = [z for z in zeilen if not z["guenstig"]]
    rest.sort(key=lambda z: z["score"], reverse=True)

    n_long = sum(1 for z in treffer if z["richtung"] == "long")
    print("\n%d Maerkte mit genug Historie, %d guenstig (%d LONG, %d SHORT)."
          % (geprueft, len(treffer), n_long, len(treffer) - n_long))
    zeige("--- Guenstige Einstiege (alle Tore offen) ---", treffer)
    if alle:
        zeige("--- Alle geprueften Maerkte ---", rest)

    bericht = {
        "datum": heute,
        "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tore": tore,
        "maerkte_geprueft": geprueft,
        "treffer": treffer,
        "werte": rest if alle else treffer,
    }
    if not kurz:
        BERICHTE.mkdir(exist_ok=True)
        name_heute = _fassung("%s.json" % heute)
        name_neu = _fassung("neuester.json")
        (BERICHTE / name_heute).write_text(
            json.dumps(bericht, ensure_ascii=False, indent=2), "utf-8")
        (BERICHTE / name_neu).write_text(
            json.dumps(bericht, ensure_ascii=False, indent=2), "utf-8")
        print("\nBericht: prognose_berichte/%s" % name_heute)

    if melden and not kurz:
        text = meldung(treffer, geprueft, k["melden"]["hoechstens"])
        try:
            import melder
            ok = melder.sende(text)
            print("Meldung gesendet:", ok)
        except Exception as e:                            # noqa: BLE001
            print("Meldung fehlgeschlagen: %s" % e, file=sys.stderr)

    return 0 if treffer else 1


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kurz", action="store_true",
                   help="nur die Tabellen, nichts schreiben, nichts senden")
    p.add_argument("--alle", action="store_true",
                   help="auch zeigen, was die Tore nicht passiert hat")
    p.add_argument("--ohne-meldung", action="store_true",
                   help="Bericht schreiben, aber nichts senden")
    p.add_argument("--werte", type=int, default=None,
                   help="nur die N umsatzstaerksten Maerkte")
    a = p.parse_args()
    return lauf(kurz=a.kurz, alle=a.alle, melden=not a.ohne_meldung,
                werte=a.werte)


if __name__ == "__main__":
    raise SystemExit(main())
