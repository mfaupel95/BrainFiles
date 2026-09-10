"""Prognose: sucht ueber den ganzen Markt nach guenstigen Einstiegen.

Angelegt am 11.09.2026 auf Max' Anweisung ("bei sehr guenstigen
Einstiegsgelegenheiten ueber alle Maerkte hinweg scannen und melden").

WAS ER IST
Der Marktscanner (scanner/scan.py) sieht eine Watchlist von elf Werten an und
liefert die Rangliste, aus der handeln.py kauft. Prognose sieht den *ganzen*
Markt an und sucht nur das eine: Lagen, in denen ein Wert deutlich unter seinem
letzten Hoch liegt, der laengere Trend aber steht - ein Ruecksetzer in einem
Aufwaertstrend, kein Absturz. Was die Tore nicht passiert, wird nicht gemeldet.

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

KONFIG = HIER / "prognose.json"
BERICHTE = HIER / "prognose_berichte"


def konfig():
    return json.loads(KONFIG.read_text("utf-8"))


# --- Kennzahlen, die bewertung.py nicht liefert -------------------------------

def _sma(werte, n):
    if len(werte) < n:
        return None
    return sum(werte[-n:]) / n


def stopp_und_ziel(kerzen, tore):
    """Stop, Ziel und Chance-Risiko-Verhaeltnis einer Lage.

    Der Stop liegt unter dem Tief der letzten 20 Tage, aber nie weiter als
    stop_max_pct unter dem Preis - ein Stop, der 40 % weg liegt, ist kein Stop,
    sondern eine Hoffnung. Das Ziel ist das Hoch der letzten 60 Tage; liegt es
    naeher als das geforderte Verhaeltnis hergibt, wird es auf das Verhaeltnis
    hochgezogen. Beide Zahlen sind gerechnet, nicht geschaetzt.
    """
    schluss = [k[4] for k in kerzen]
    hoch = [k[2] for k in kerzen]
    tief = [k[3] for k in kerzen]
    preis = schluss[-1]

    tief20 = min(tief[-20:]) if len(tief) >= 20 else min(tief)
    stop = min(tief20, preis * (1.0 - tore["stop_min_pct"] / 100.0))
    stop = max(stop, preis * (1.0 - tore["stop_max_pct"] / 100.0))
    if stop >= preis:                      # entartet, wenn das Tief am Preis klebt
        stop = preis * (1.0 - tore["stop_min_pct"] / 100.0)

    # Das Ziel ist das Hoch der letzten 60 Tage - ein beobachteter Kurs, keine
    # Wunschzahl. Wird es nicht erreicht, sagt das der C/R-Wert, statt dass das
    # Ziel hochgezogen wird: ein Ziel, das immer das geforderte Verhaeltnis
    # herstellt, macht das Verhaeltnis als Tor wertlos.
    hoch60 = max(hoch[-60:]) if len(hoch) >= 60 else max(hoch)
    abstand = preis - stop
    ziel = hoch60

    risiko_pct = (preis - stop) / preis * 100.0
    cr = (ziel - preis) / abstand if abstand > 0 else 0.0
    return {"stop": stop, "ziel": ziel, "risiko_pct": risiko_pct,
            "cr": cr, "tief20": tief20, "hoch60": hoch60}


def lage(inst, kerzen, tore):
    """Eine Zeile des Berichts: Bewertung, gerechnete Grenzen, offene Tore."""
    b = bewertung.bewerten(kerzen)
    k = b["kennzahlen"]
    schluss = [x[4] for x in kerzen]
    preis = schluss[-1]

    s = stopp_und_ziel(kerzen, tore)
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
    if z["score"] < tore["mindest_score"]:
        offen.append("Score %.1f < %g" % (z["score"], tore["mindest_score"]))
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
    elif preis <= sma:
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
    print("%-12s | %5s | %4s | %6s | %5s | %4s | %5s | %5s | %s"
          % ("Markt", "Score", "RSI", "Hoch%", "Vola", "Vol", "Stop%", "C/R",
             "offene Tore"))
    print("-" * 104)
    for z in (zeilen if grenze is None else zeilen[:grenze]):
        k = z["kennzahlen"]
        print("%-12s | %5.1f | %4.1f | %6.1f | %5.2f | %4.2f | %4.1f%% | %5.2f | %s"
              % (z["inst"], z["score"], k["rsi14"], k["abstand_60t_hoch_pct"],
                 k["volatilitaet_pa"], z["volumen_verhaeltnis"] or 0.0,
                 z["risiko_prozent"], z["cr"],
                 "keine" if z["guenstig"] else "; ".join(z["offene_tore"])))


def meldung(treffer, geprueft, grenze):
    """Der Telegram-Text. Leer heisst: nichts gefunden, und das wird gesagt."""
    if not treffer:
        return ("<b>Prognose</b>: %d Maerkte geprueft, kein guenstiger Einstieg.\n"
                "Die Tore hat heute nichts passiert - dann wird auch nichts "
                "gemeldet." % geprueft)
    z = ["<b>Prognose: %d guenstige Einstiege</b> (von %d Maerkten)"
         % (len(treffer), geprueft), ""]
    for t in treffer[:grenze]:
        z.append("<b>%s</b>  Score %.1f  C/R %.2f"
                 % (html.escape(t["inst"]), t["score"], t["cr"]))
        z.append("  Einstieg %.6g  Stop %.6g (-%.1f%%)  Ziel %.6g"
                 % (t["preis"], t["stop"], t["risiko_prozent"], t["ziel"]))
        z.append("  RSI %.1f  Ruecksetzer %.1f%%  Vola %.2f"
                 % (t["kennzahlen"]["rsi14"],
                    t["kennzahlen"]["abstand_60t_hoch_pct"],
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
    paare = okx.alle_paare(quote=k["maerkte"],
                           min_volumen_usd=k["min_volumen_24h_usd"])
    if werte:
        paare = paare[:werte]
    print("=== Prognose %s | %d Maerkte ueber %s (Umsatz >= %g USD, 24 h) ==="
          % (heute, len(paare), ", ".join(k["maerkte"]),
             k["min_volumen_24h_usd"]))

    zeilen = []
    for i, (inst, umsatz) in enumerate(paare, 1):
        try:
            kerzen = okx.kerzen(inst, "1D", 300)
            if len(kerzen) < 120:
                continue
            z = lage(inst, kerzen, tore)
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

    print("\n%d Maerkte mit genug Historie, %d guenstig."
          % (len(zeilen), len(treffer)))
    zeige("--- Guenstige Einstiege (alle Tore offen) ---", treffer)
    if alle:
        zeige("--- Alle geprueften Maerkte ---", rest)

    bericht = {
        "datum": heute,
        "erzeugt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tore": tore,
        "maerkte_geprueft": len(zeilen),
        "treffer": treffer,
        "werte": rest if alle else treffer,
    }
    if not kurz:
        BERICHTE.mkdir(exist_ok=True)
        (BERICHTE / ("%s.json" % heute)).write_text(
            json.dumps(bericht, ensure_ascii=False, indent=2), "utf-8")
        (BERICHTE / "neuester.json").write_text(
            json.dumps(bericht, ensure_ascii=False, indent=2), "utf-8")
        print("\nBericht: prognose_berichte/%s.json" % heute)

    if melden and not kurz:
        text = meldung(treffer, len(zeilen), k["melden"]["hoechstens"])
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
