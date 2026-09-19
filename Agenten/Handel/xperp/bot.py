"""XPERP-Bot: Lage lesen, Positionen rechnen, Orders vorlegen.

Der Bot rechnet und legt vor; abgesendet wird die scharfe Order von Max oder
von einem dafuer gebauten Skript. Seit dem 01.09.2026 ist Hebel nicht mehr
grundsaetzlich verboten (Wissen/Handelsregeln.md, Spur 2) - verboten bleibt,
ihn von selbst zu nehmen. Daraus folgen zwei Dinge fuer dieses Modul:

  - Eine Rangliste aus auswahl.py ist ein VORSCHLAG, keine Anweisung. Der Bot
    eroeffnet nichts aus einer Rangliste heraus und leitet keine Richtung aus
    dem Trend ab. Eine gueltige Anweisung nennt Kontrakt, Richtung, Hebel,
    Einsatz und Stop - fehlt eine Angabe, wird danach gefragt statt geraten.
  - Vor jeder gehebelten Order legt pruefpflicht() ungefragt vier Zahlen vor:
    Liquidationsabstand gegen groessten 7-Tage-Ruecklauf, Funding ueber die
    Haltedauer, Gebuehren je Runde, noetige gegen beobachtete Trefferquote.

Widerspruchspflicht, kein Vetorecht: Sagen die Zahlen, dass eine Anweisung
falsch gedacht ist, steht das einmal in der Ausgabe - mit Gegenvorschlag.
Bestaetigt Max, wird wie angewiesen gerechnet, nicht stillschweigend kleiner.

Die tragende Rechnung steht in groesse(): Der Stop-Abstand kommt aus dem ATR,
die Positionsgroesse aus dem Stop-Abstand, und der Hebel faellt hinten heraus.
Er ist Ergebnis, nicht Eingabe. "5x" ist damit ein Deckel, kein Ziel - genau
die Regel, die in Handel/README.md schon aus dem Titelvergleich gezogen wurde:
Die Hebelhoehe gehoert an die gemessene Volatilitaet gekoppelt, nicht an eine
Kurserwartung.

Aufrufe:
    python bot.py lage   --wert SOL
    python bot.py trend  --wert SOL
    python bot.py grid   --wert SOL

--historie zieht Hebel-Deckel und Trefferquote aus einer tieferen Reihe, wenn
der Kontrakt zu jung ist (CHIP-XPERP war am 01.09.2026 14 Tage alt). Das
Signal - SuperTrend, EMA, RSI, ATR jetzt - kommt weiter vom gehandelten
Kontrakt; nur die Rueckrechnung wechselt die Quelle. Siehe historie.py.

Seit dem 13.09.2026 rechnet der Hebel-Deckel auf TAGESKERZEN
(auswahl.mae_tage): 300 4H-Kerzen sind nur 50 Tage, und der groesste
Ruecklauf darf nicht vom Fensterrand abhaengen (SOL, Einbruch vom
31.05.2026 lag ausserhalb des 4H-Fensters).

    python bot.py trend --wert CHIP --historie auto            # <Basis>-USDT-SWAP
    python bot.py trend --wert CHIP --historie CHIP-USDT-SWAP  # ausdruecklich

--hebel N setzt den Hebel als Zahl (Spur 2: eine gueltige Anweisung nennt ihn).
Ohne --hebel faellt er wie bisher aus dem Deckel. Mit --hebel gilt die Zahl;
ueberschreitet sie den Deckel, rechnet der Bot wie angewiesen und meldet es in
der Pruefpflicht - nicht stillschweigend kleiner.

    python bot.py trend --wert CHIP --historie auto --hebel 2
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, os.pardir, "Bus"))
import ereignis                                            # noqa: E402

import auswahl
import historie
import indikatoren
import okxf

HIER = os.path.dirname(os.path.abspath(__file__))
BAR = "4H"


# Risikostufe (HANDEL_RISIKO): Faktor auf die Betraege, Suffix auf Zustand
# und Journal. OHNE die Variable aendert sich nichts (Faktor 1.0, kein
# Suffix) - das ist die Bedingung, unter der diese Umstellung in laufenden
# Handelscode darf. Ueber den PFAD geladen wie ratschen.py: die Spur hat ihren
# eigenen Ordner als sys.path[0], ein 'import risikostufe' haenge an der
# Reihenfolge der Eintraege.
from importlib.util import module_from_spec as _rs_mod, \
    spec_from_file_location as _rs_spec
_rs_datei = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         os.pardir, "risikostufe.py")
_rs_spec_obj = _rs_spec("risikostufe", _rs_datei)
risikostufe = _rs_mod(_rs_spec_obj)
_rs_spec_obj.loader.exec_module(risikostufe)

def wachen():
    with open(os.path.join(HIER, "wachen.json"), encoding="utf-8") as f:
        # Risikostufe: die Betraege tragen den Faktor dieser Stufe.
        return risikostufe.skaliere(json.load(f))


def familie(w, instr):
    """Die Tore, die fuer genau dieses Instrument gelten.

    Seit 03.09.2026 handelt die Spur drei instCategory-Familien (Krypto,
    Aktien, Rohstoffe) mit getrennten Toren - der Block 'familien' in
    wachen.json. Ein Wert, der an Krypto gemessen wurde, misst bei einer
    Aktie das Falsche: MSTR faellt mit 1,8 Mio Umsatz durch das 3-Mio-Tor,
    obwohl sein Spread ein Zehntel des Krypto-Werts betraegt.

    Faellt der Block weg oder kennt er die Kategorie nicht, gelten die alten
    Werte aus der obersten Ebene - dann verhaelt sich der Bot wie vorher.
    """
    grund = {"vola_tor_pa": w.get("vola_tor_pa", 1.20),
             "umsatz_bezug_usd": w.get("min_umsatz_24h_usd", 3_000_000),
             "max_anteil_gesamt": 1.0,
             "name": "krypto"}
    kat = (instr or {}).get("instCategory")
    for name, f in (w.get("familien") or {}).items():
        if f.get("instCategory") == kat:
            if not f.get("aktiv", True):
                return dict(grund, name=name, aktiv=False)
            return {"vola_tor_pa": f.get("vola_tor_pa", grund["vola_tor_pa"]),
                    "umsatz_bezug_usd": f.get("umsatz_bezug_usd",
                                              grund["umsatz_bezug_usd"]),
                    "max_anteil_gesamt": f.get("max_anteil_gesamt", 1.0),
                    "name": name, "aktiv": True}
    return dict(grund, aktiv=True)


# --- Rechnungen -------------------------------------------------------------

def trefferquote(k, stop_atr, ziel_atr, seite, max_kerzen=42):
    """Wie oft wurde das Ziel vor dem Stop erreicht - auf der eigenen Historie.

    Von jeder Kerze aus wird ein Anlauf simuliert und vorwaerts gelaufen, bis
    Ziel oder Stop faellt. Zwei bewusste Entscheidungen:

      - Faellt beides in dieselbe Kerze, gilt der STOP. 4h-Kerzen loesen nicht
        auf, was zuerst kam; das Gegenteil anzunehmen rechnet die Strategie
        systematisch schoen.
      - Anlaeufe aus benachbarten Kerzen ueberlappen sich stark. Das sind
        KEINE unabhaengigen Beobachtungen - dieselbe Einschraenkung, die in
        Handel/README.md schon fuer die rollierenden Fenster steht.
    """
    a = indikatoren.atr(k, 14)
    vz = 1 if seite == "long" else -1
    ziel_n = stop_n = offen = 0

    for i in range(len(k) - 1):
        if a[i] is None:
            continue
        ein = k[i][4]
        ziel = ein + vz * ziel_atr * a[i]
        stop = ein - vz * stop_atr * a[i]
        erg = None
        for j in range(i + 1, min(i + 1 + max_kerzen, len(k))):
            hoch, tief = k[j][2], k[j][3]
            if seite == "long":
                traf_stop, traf_ziel = tief <= stop, hoch >= ziel
            else:
                traf_stop, traf_ziel = hoch >= stop, tief <= ziel
            if traf_stop:                     # Stop hat Vorrang - vorsichtig
                erg = "stop"
                break
            if traf_ziel:
                erg = "ziel"
                break
        if erg == "ziel":
            ziel_n += 1
        elif erg == "stop":
            stop_n += 1
        else:
            offen += 1

    n = ziel_n + stop_n
    return {"ziel": ziel_n, "stop": stop_n, "offen": offen, "n": n,
            "quote": (ziel_n / n) if n else None}


def noetige_quote(gewinn_pct, verlust_pct, kosten_pct):
    """Trefferquote, ab der die Runde ueberhaupt bei null herauskommt.

    p * Gewinn = (1-p) * Verlust + Kosten
    """
    nenner = gewinn_pct + verlust_pct
    return (verlust_pct + kosten_pct) / nenner if nenner > 0 else None


def pruefpflicht(w, instr, k, seite, einstieg, stop, ziel, hebel, stunden=48,
                 stop_atr_f=None, ziel_atr_f=None, was="Order", still=False,
                 stat_id=None):
    """Die vier Zahlen, die Wissen/Handelsregeln.md vor jeder gehebelten
    Order verlangt (Spur 2, Pruefpflicht, angeordnet 01.09.2026).

    Sie werden ungefragt vorgelegt, kurz und als Tabelle. Die Grundlinie aus
    Wissen/Handelsbots.md ist unbequem: noetige und erreichte Trefferquote
    lagen dort immer ein bis zwei Prozentpunkte auseinander, uebrig blieben
    die Gebuehren. Hebel vergroessert diesen Abstand mit.

    Gibt die vier Werte immer zurueck, auch beim Drucken. Das ist seit dem
    03.09.2026 noetig, weil handeln.py sie ins Journal schreibt: Auf dem
    automatischen Weg liest niemand mit, und die Handelsregeln sagen dazu
    unmissverstaendlich - "eine Zahl, die der Automat nicht ablegt, ist nicht
    gerechnet worden; eine Position ohne diese vier Werte im Journal ist ein
    Befund, kein Trade." Mit still=True bleibt die Ausgabe weg.

    stat_id: instId der Reihe, aus der der Hebel-Deckel kommt (Tageskerzen).
    None -> der Kontrakt selbst (instr["instId"]). zeige_trend/zeige_grid
    reichen hier die Statistik-Reihe durch (--historie).
    """
    dl, ds = hebel_deckel(stat_id or instr["instId"],
                         wartung=w["wartungsmarge"])
    deckel = dl if seite == "long" else ds
    liq = liquidationspreis(einstieg, hebel, w["wartungsmarge"], seite)
    liq_abstand = abs(einstieg - liq) / einstieg

    f = okxf.funding(instr["instId"])
    perioden = stunden / 8.0                      # OKX rechnet alle 8 Stunden
    # Long zahlt bei positivem Satz, Short bekommt. Auf die Margin bezogen
    # wirkt der Satz mit dem Hebel multipliziert.
    funding_pct = (f * perioden * (1 if seite == "long" else -1)) if f is not None else None

    gewinn = abs(ziel - einstieg) / einstieg
    verlust = abs(einstieg - stop) / einstieg
    gebuehren = 2 * w["gebuehr_taker"]
    kosten = gebuehren + (funding_pct or 0.0)
    noetig = noetige_quote(gewinn, verlust, kosten)

    # Beim Grid kommt die Geometrie nicht aus wachen.json, sondern aus dem
    # Raster: Ziel ist eine Stufe hoeher, Stop der gemeinsame Rasterboden.
    a_jetzt = indikatoren.atr(k, 14)[-1]
    if stop_atr_f is None:
        stop_atr_f = (verlust * einstieg / a_jetzt) if a_jetzt else w["stop_atr_faktor"]
    if ziel_atr_f is None:
        ziel_atr_f = (gewinn * einstieg / a_jetzt) if a_jetzt else w["ziel_atr_faktor"]
    tq = trefferquote(k, stop_atr_f, ziel_atr_f, seite)

    werte = {
        "liq_abstand": liq_abstand,
        "liq_preis": liq,
        "hebel": hebel,
        "hebel_deckel": deckel,
        "hebel_traegt": hebel <= deckel,
        "funding_pct": funding_pct,
        "funding_satz": f,
        "gebuehren_pct": gebuehren,
        "gewinn_pct": gewinn,
        "verlust_pct": verlust,
        "kosten_pct": kosten,
        "quote_noetig": noetig,
        "quote_beobachtet": tq["quote"],
        "quote_ziel": tq["ziel"],
        "quote_stop": tq["stop"],
        "quote_selten": min(tq["ziel"], tq["stop"]),
        "traegt": (noetig is not None and tq["quote"] is not None
                   and (tq["quote"] - noetig) > 0.02),
    }
    if still:
        return werte

    print()
    print("-" * 66)
    print("PRUEFPFLICHT  (Handelsregeln, Spur 2 - vier Zahlen vor der %s)" % was)
    print("-" * 66)

    print("  1  Liquidationsabstand gegen groessten 7-Tage-Ruecklauf (Tageskerzen)")
    print("       Liquidation %.2f%% entfernt, Hebel-Deckel %.1fx, gewaehlt %.1fx" % (
        liq_abstand * 100, deckel, hebel))
    print("       %s" % ("passt - der Hebel liegt unter dem Deckel"
                         if hebel <= deckel else
                         "ZU HOCH - der groesste Ruecklauf haette liquidiert"))

    print("  2  Funding ueber %.0f Stunden Haltedauer" % stunden)
    if f is None:
        print("       nicht abrufbar")
    else:
        print("       %+.4f%% je 8h x %.1f Perioden = %+.3f%% auf das Nominal" % (
            f * 100, perioden, (funding_pct or 0) * 100))
        print("       = %+.3f%% auf die Margin bei %.1fx   (%s)" % (
            (funding_pct or 0) * 100 * hebel, hebel,
            "laufende Miete" if (funding_pct or 0) > 0 else "Zuschuss"))

    print("  3  Gebuehren je Runde gegen erwarteten Gewinn")
    print("       %.3f%% Gebuehr (2 x Taker) gegen %.2f%% Ziel = %.0f%% des Gewinns" % (
        gebuehren * 100, gewinn * 100, gebuehren / gewinn * 100 if gewinn else 0))

    print("  4  Noetige gegen beobachtete Trefferquote")
    if noetig is None:
        print("       nicht rechenbar")
    else:
        print("       noetig     %.1f%%   (Ziel %.2f%%, Stop %.2f%%, Kosten %.3f%%)" % (
            noetig * 100, gewinn * 100, verlust * 100, kosten * 100))
        if tq["quote"] is None:
            print("       beobachtet n/a - kein Anlauf lief in der Historie aus")
        else:
            print("       beobachtet %.1f%%   (%d Ziel / %d Stop, %d offen, %.0f Tage)" % (
                tq["quote"] * 100, tq["ziel"], tq["stop"], tq["offen"], len(k) / 6))
            abstand = (tq["quote"] - noetig) * 100
            print("       Abstand    %+.1f Prozentpunkte  -> %s" % (
                abstand,
                "traegt" if abstand > 2 else
                "zu knapp, das ist die Nulllinie aus [[Handelsbots]]"
                if abstand > -2 else "traegt NICHT"))

            # Die seltenere der beiden Seiten bestimmt, wie genau die Quote
            # ueberhaupt ist. Bei einem einzigen Stop in 50 Tagen ist das
            # Verlustereignis nicht gemessen, sondern nicht vorgekommen - und
            # eine Quote von 99 % aus einem Gegenbeispiel ist keine Schaetzung.
            selten = min(tq["ziel"], tq["stop"])
            if selten < 10:
                grosse = "Stop" if tq["stop"] < tq["ziel"] else "Ziel"
                print()
                print("       ACHTUNG: nur %d x %s in der ganzen Historie." % (selten, grosse))
                print("       Die Quote steht auf einem einzigen Ereignistyp und ist")
                print("       nicht belastbar. Genau dieses Muster beschreibt")
                print("       Wissen/Handelsbots.md: enges Ziel, weiter Stop, hohe")
                print("       Trefferquote - und der eine Stop kostet mehr, als die")
                print("       vielen Treffer eingebracht haben. Bei %.2f%% Ziel gegen" % (gewinn * 100))
                print("       %.2f%% Stop braucht es %d Treffer, um einen Stop zu" % (
                    verlust * 100, int(verlust / gewinn) + 1 if gewinn else 0))
                print("       bezahlen.")
    print()
    print("  Die Anlaeufe ueberlappen sich (jede Kerze ein Einstieg) und stammen")
    print("  aus %.0f Tagen. Das sind keine unabhaengigen Beobachtungen, und" % (len(k) / 6))
    print("  Wissen/Handelsbots.md verlangt ein Jahr - das gibt es bei XPERP")
    print("  nirgends, die aeltesten Kontrakte laufen seit Mai 2026.")
    return werte


def liquidationspreis(einstieg, hebel, wartung, seite="long"):
    """Wo die Boerse zwangsschliesst. Isolierte Margin, ohne Nachschuss.

    Naeherung: Der Einschuss ist 1/hebel des Positionswerts; liquidiert wird,
    wenn davon nur noch die Wartungsmarge uebrig ist. Die echte Formel von OKX
    kennt zusaetzlich Gebuehren und Stufen der Wartungsmarge - sie liegt etwas
    frueher. Deshalb wird hier nie bis an die Liquidation herangeplant, sondern
    der Stop klar darueber gesetzt.
    """
    strecke = 1.0 / hebel - wartung
    return einstieg * (1 - strecke) if seite == "long" else einstieg * (1 + strecke)


# Test-Seam: None -> echte OKX-Tageskerzen (okxf.kerzen(inst_id, "1D", n)).
# Tests setzen eine Lambda mit synthetischen Kerzen, tearDown setzt None.
tages_kerzen_quelle = None


def _tages_kerzen(inst_id, n=300):
    if tages_kerzen_quelle is not None:
        return tages_kerzen_quelle(inst_id, n)
    return okxf.kerzen(inst_id, "1D", n)


def hebel_deckel(inst_id, tage=7, wartung=0.005, obergrenze=20.0):
    """Groesster Hebel, der den groessten Ruecklauf der letzten Tage ueberlebt.

    Rueckblick, keine Zusage. Aber ein Hebel, der schon die letzte Woche nicht
    ueberstanden haette, braucht ueber die naechste nicht diskutiert zu werden.

    Seit dem 13.09.2026 auf TAGESKERZEN (auswahl.mae_tage): das 4H-Fenster
    des gehandelten Kontrakts (300 Kerzen = 50 Tage) unterschlaegt aeltere
    Ruecklaeufe. Gemessen an SOL: ueber 50 Tage 9,5 % (Deckel 10x), ueber
    200 Tage 27,9 % (Deckel 3,5x) - der Einbruch vom 31.05.2026 lag
    ausserhalb des kurzen Fensters. Der Deckel ist eine feste Grenze nach
    Handelsregeln, Spur 2 und darf nicht vom Fensterrand abhaengen.
    """
    kt = _tages_kerzen(inst_id)
    if len(kt) < tage + 1:
        return 1.0, 1.0
    mae_l, mae_s = auswahl.mae_tage(kt, tage)
    return (max(1.0, min(obergrenze, 1.0 / (mae_l + wartung))),
            max(1.0, min(obergrenze, 1.0 / (mae_s + wartung))))


def groesse(w, instr, einstieg, stop, seite, deckel, hebel_wunsch=None, einsatz=None):
    """Kontrakte, Hebel und tatsaechliches Risiko einer Position.

    Reihenfolge: Risikobetrag geteilt durch Stop-Abstand ergibt den
    Positionswert. Erst danach wird geprueft, ob die Margin in den Rahmen
    passt - und wenn nicht, wird die Position kleiner, nicht der Stop weiter.

    Ohne hebel_wunsch faellt der Hebel aus dem Deckel (Ergebnis, nicht
    Eingabe). Mit hebel_wunsch - einer Anweisung nach Spur 2 - gilt die Zahl;
    der Deckel wird dann in pruefpflicht() gemeldet, nicht hier angewandt.
    """
    abstand = abs(einstieg - stop) / einstieg
    if abstand <= 0:
        return None

    hebel = min(w["max_hebel"], deckel) if hebel_wunsch is None else float(hebel_wunsch)
    if hebel < 1:
        return None

    max_margin = w["max_margin_je_anlauf_usd"] if einsatz is None else float(einsatz)
    nominal_risiko = w["risiko_je_anlauf_usd"] / abstand
    nominal_margin = max_margin * hebel
    nominal = min(nominal_risiko, nominal_margin)

    kontrakte, echt = okxf.kontrakte_aus_nominal(instr, nominal, einstieg)
    if kontrakte <= 0:
        return None

    return {
        "kontrakte": kontrakte,
        "nominal": echt,
        "hebel": hebel,
        "margin": echt / hebel,
        "risiko": echt * abstand,
        "abstand": abstand,
        "gedeckelt": nominal_margin < nominal_risiko,
        "liq": liquidationspreis(einstieg, hebel, w["wartungsmarge"], seite),
    }


# --- Ausgaben ---------------------------------------------------------------

def hole(wert):
    instr = okxf.instrument(wert)
    k = okxf.kerzen(instr["instId"], BAR, 300)
    return instr, k


def zeige_lage(w, wert, historie_quelle=None):
    instr, k = hole(wert)

    # Das KURS-Signal steht auf k (dem gehandelten Kontrakt). Die Statistik -
    # Hebel-Deckel, in pruefpflicht() die Trefferquote und seit 16.09.2026 auch
    # die Saisonalitaet (T-018) - darf aus einer tieferen Reihe kommen, wenn der
    # Kontrakt zu jung ist. Ohne --historie ist k_hist einfach k.
    k_hist, hist_id, hist_ersatz = k, instr["instId"], False
    if historie_quelle is not None:
        k_hist, hist_id, hist_ersatz = historie.tiefe_reihe(
            instr["instId"], historie_quelle)

    # k_stat: die Saisonalitaet rechnet auf der tiefen Reihe, wenn sie laenger
    # ist und gleichzeitig endet (indikatoren._gleichzeitig) - Wochentagsquoten
    # auf ~7 Beobachtungen je Wochentag sind keine Statistik. signal_bauen()
    # laeuft danach mit dieser Saisonalitaet.
    z = indikatoren.lage(k, inst=instr["instId"], k_stat=k_hist)

    dl, ds = hebel_deckel(hist_id, wartung=w["wartungsmarge"])
    ist_swap = instr["instId"].upper().endswith("-SWAP")
    tick = okxf.tickers("SWAP" if ist_swap else "FUTURES").get(instr["instId"], {})
    umsatz = float(tick.get("volCcy24h") or 0) * z["kurs"]
    tage = len(k) / 6.0

    print()
    print("=" * 66)
    print("%s   %s" % (wert.upper(), instr["instId"]))
    print("=" * 66)
    print("  Kurs           %.6f" % z["kurs"])
    print("  ATR(14)        %.6f  = %.2f%% vom Kurs" % (z["atr"], z["atr_pct"] * 100))
    print("  SuperTrend     %s seit %d Kerzen, Linie %.6f" % (
        "AUF" if z["st_richtung"] == 1 else "AB", z["st_dauer"], z["st_linie"]))
    print("  EMA20 / EMA50  %.6f / %.6f  -> %s" % (
        z["ema20"], z["ema50"], "auf" if z["ema20"] > z["ema50"] else "ab"))
    print("  RSI(14)        %.0f" % z["rsi"])
    print("  Effizienz      %.2f  (%s)" % (
        z["er"], "Gezappel - Grid-Futter" if z["er"] < 0.3
        else "gemischt" if z["er"] < 0.6 else "Trend - Grid wird zerrieben"))

    s = z["sais"]
    if s["quote"] is None:
        print("  Saisonalitaet  %s: zu wenig Historie fuer eine Aussage (n=%d)" % (
            s["wochentag"] or "?", s["n"]))
    else:
        pfeil = {1: "-> LONG", -1: "-> SHORT", 0: "neutral"}[s["richtung"]]
        print("  Saisonalitaet  %s %02d:00 UTC  %s" % (
            s["wochentag"], s["phase_h"], pfeil))
        print("                 Wochentag: Auf-Quote %.0f%% (n=%d), Kerze im Mittel %+.2f%%" % (
            s["quote"] * 100, s["n"], s["mittel"] * 100))
        if s["quote_phase"] is not None and s["n_phase"] >= 3:
            print("                 + Phase:   Auf-Quote %.0f%% (n=%d), Mittel %+.2f%%" % (
                s["quote_phase"] * 100, s["n_phase"], s["mittel_phase"] * 100))
        if s["richtung"] != 0:
            print("                 HOCH gewichtet - kann das SIGNAL setzen/kippen")
            print("                 (Anweisung 01.09.2026; n=%d ist duenn, kein Backtest)" % s["n"])

    if z.get("sais_tief"):
        print("                 Basis: tiefe Reihe, %d Kerzen - Statistik, nicht "
              "der Kontrakt" % z["sais_kerzen"])

    vd = z["vol_drift"]
    if vd["score"] is None:
        print("  Volumen-Drift  zu wenig Historie fuer eine Aussage (n=%d)" % vd["n"])
    else:
        pfeil = {1: "-> LONG", -1: "-> SHORT", 0: "neutral"}[vd["richtung"]]
        print("  Volumen-Drift  Score %+.2f, Volumen %.2fx vs. davor  %s" % (
            vd["score"], vd["volumen_verhaeltnis"], pfeil))
        if vd["richtung"] != 0:
            print("                 Zeitebenen bestaetigt (2x %+.2f / 4x %+.2f)%s" % (
                vd["score_2x"], vd["score_4x"], " - STARK" if vd["stark"] else ""))
            print("                 HOCH gewichtet - kann das SIGNAL setzen/kippen,")
            print("                 hat bei Widerspruch Vorrang vor Saisonalitaet (Anweisung 08.09.2026)")

    cv = z["cvd"]
    if cv["n"] == 0:
        print("  CVD-4h         keine Aussage: %s" % cv["grund"])
    else:
        pfeil = {1: "-> LONG", -1: "-> SHORT", 0: "neutral"}[cv["richtung"]]
        print("  CVD-4h         %d Eimer: Preis %+.2f%%, CVD %+.0f%% der Bewegung  %s" % (
            cv["eimer"], (cv["preis_pct"] or 0.0) * 100,
            (cv["cvd_anteil"] or 0.0) * 100, pfeil))
        if cv["richtung"] != 0:
            print("                 Divergenz am %s%s" % (
                "Hoch (Verteilung)" if cv["richtung"] == -1
                else "Tief (Akkumulation)", " - STARK" if cv["stark"] else ""))
            print("                 HOCH gewichtet - laeuft als letzte Komponente und")
            print("                 hat bei Widerspruch Vorrang (Anweisung 13.09.2026)")
    print()
    print("  SIGNAL: %s   (%s)" % (z["signal"].upper(), z["grund"]))
    print()
    print("  Hebel-Deckel   long %.1fx   short %.1fx   (groesster 7-Tage-Ruecklauf, Tageskerzen)" % (dl, ds))
    print("  Umsatz 24h     %.1f Mio USD" % (umsatz / 1e6))
    print("  Historie       %.0f Tage" % tage)
    tage_hist = len(k_hist) / 6.0
    if hist_ersatz:
        print("  Statistik aus  %s  -  %.0f Tage" % (hist_id, tage_hist))
        print("                 Hebel-Deckel, Trefferquote und Saisonalitaet stammen")
        print("                 aus dieser Reihe (gleicher Basiswert), das Kurs-Signal oben nicht.")
    elif historie_quelle is not None and tage_hist > tage + 1:
        print("  Statistik aus  %.0f Tage - tiefe Reihe desselben Kontrakts" % tage_hist)
        print("                 (mehr Kerzen als die 300 fuer das Signal oben).")
    elif historie_quelle is not None:
        print("  Statistik aus  keine laengere Reihe gefunden - es bleibt bei %.0f Tagen" % tage)

    print()
    fam = familie(w, instr)
    if fam["name"] != "krypto":
        print("  Familie        %s  (eigene Tore aus wachen.json)" % fam["name"])
    tore = [
        ("Historie >= %d Tage" % w["min_historie_tage"], tage >= w["min_historie_tage"]),
        ("Umsatz >= %.1f Mio (%s)" % (fam["umsatz_bezug_usd"] / 1e6, fam["name"]),
         umsatz >= fam["umsatz_bezug_usd"]),
        ("Hebel-Deckel >= %g" % w["max_hebel"], max(dl, ds) >= w["max_hebel"]),
    ]
    if not fam.get("aktiv", True):
        tore.append(("Familie %s ist aktiv" % fam["name"], False))
    for name, ok in tore:
        print("  [%s] %s" % ("x" if ok else " ", name))
    if not all(ok for _, ok in tore):
        print("\n  -> Mindestens ein Tor ist zu. Vorschlaege werden trotzdem")
        print("     gerechnet, aber mit gesenktem Hebel und mit Warnung.")
    return instr, k, k_hist, z, (dl, ds), hist_id


def zeige_trend(w, wert, historie_quelle=None, hebel_wunsch=None, einsatz=None,
                sammle=None):
    instr, k, k_hist, z, (dl, ds), hist_id = zeige_lage(w, wert, historie_quelle)
    if z["signal"] == "kein":
        print()
        print("Kein Einstieg: %s" % z["grund"])
        print("Der Bot erfindet kein Signal, wenn die Indikatoren sich widersprechen.")
        return 0

    seite = z["signal"]
    deckel = dl if seite == "long" else ds
    atr = z["atr"]
    vz = 1 if seite == "long" else -1

    # Limit unter den Kurs legen (bei Short darueber) - der Einstieg soll
    # Maker sein, nicht Taker. Er kann dadurch liegenbleiben; das ist der
    # bewusste Unterschied zum Marktkauf.
    einstieg = okxf.auf_tick(instr, z["kurs"] - vz * w["einstieg_atr_abschlag"] * atr)
    stop = okxf.auf_tick(instr, einstieg - vz * w["stop_atr_faktor"] * atr)
    ziel = okxf.auf_tick(instr, einstieg + vz * w["ziel_atr_faktor"] * atr)

    g = groesse(w, instr, einstieg, stop, seite, deckel, hebel_wunsch, einsatz)
    if not g:
        print("\nPosition waere kleiner als ein Kontrakt - kein Vorschlag.")
        return 1

    print()
    print("-" * 66)
    print("TREND-ANLAUF  %s" % seite.upper())
    print("-" * 66)
    print("  Einstieg (Limit)  %.6f   %.2f ATR vom Kurs" % (
        einstieg, w["einstieg_atr_abschlag"]))
    print("  Stop              %.6f   %.2f ATR = %.2f%%" % (
        stop, w["stop_atr_faktor"], g["abstand"] * 100))
    print("  Ziel              %.6f   %.2f ATR = %.2f%%   (%.1f:1)" % (
        ziel, w["ziel_atr_faktor"], abs(ziel - einstieg) / einstieg * 100,
        w["ziel_atr_faktor"] / w["stop_atr_faktor"]))
    print()
    print("  Kontrakte         %g  a %s %s" % (
        g["kontrakte"], instr["ctVal"], instr["ctValCcy"]))
    print("  Positionswert     %.2f USD" % g["nominal"])
    print("  Hebel             %.1fx   (Deckel %.1fx aus dem Ruecklauf, %g aus wachen.json)" % (
        g["hebel"], deckel, w["max_hebel"]))
    if hebel_wunsch is not None:
        print("                    per Anweisung gesetzt (--hebel %g)%s" % (
            hebel_wunsch,
            " - UEBER dem Deckel, siehe Pruefpflicht" if g["hebel"] > deckel else ""))
    print("  Margin            %.2f USD  von %g erlaubt%s" % (
        g["margin"],
        einsatz if einsatz is not None else w["max_margin_je_anlauf_usd"],
        "  (--einsatz)" if einsatz is not None else ""))
    print("  Risiko bei Stop   %.2f USD  von %g Budget%s" % (
        g["risiko"], w["risiko_je_anlauf_usd"],
        "  (durch Margin gedeckelt)" if g["gedeckelt"] else ""))
    print()
    print("  Liquidation bei   %.6f" % g["liq"])
    sicher = (stop > g["liq"]) if seite == "long" else (stop < g["liq"])
    if sicher:
        luft = abs(stop - g["liq"]) / einstieg * 100
        print("  -> Der Stop liegt %.2f%% vor der Liquidation. Die Position wird" % luft)
        print("     ausgestoppt, nicht zwangsgeschlossen. So soll es sein.")
    else:
        print("  -> WARNUNG: Der Stop liegt HINTER der Liquidation. Die Boerse")
        print("     schliesst vor dem Stop - der Verlust ist dann die ganze Margin,")
        print("     nicht der gerechnete Risikobetrag. Hebel senken.")

    pruefpflicht(w, instr, k_hist, seite, einstieg, stop, ziel, g["hebel"],
                 stop_atr_f=w["stop_atr_faktor"], ziel_atr_f=w["ziel_atr_faktor"],
                 stat_id=hist_id)
    befehle(instr, seite, g["kontrakte"], einstieg, ziel, stop, g["hebel"])
    if sammle is not None:
        sammle.append({"instr": instr, "hebel": g["hebel"], "orders": [
            ("buy" if seite == "long" else "sell",
             g["kontrakte"], einstieg, ziel, stop)]})
    return 0


def zeige_grid(w, wert, historie_quelle=None, hebel_wunsch=None, einsatz=None,
               sammle=None):
    instr, k, k_hist, z, (dl, _), hist_id = zeige_lage(w, wert, historie_quelle)
    atr, kurs = z["atr"], z["kurs"]
    gesamt_margin_erlaubt = w["max_margin_gesamt_usd"] if einsatz is None else float(einsatz)

    spanne_abs = w["grid_spanne_atr"] * atr
    unten = kurs - spanne_abs
    if unten <= 0:
        print("\nSpanne reicht unter null - grid_spanne_atr senken.")
        return 1
    spanne_rel = spanne_abs / kurs

    # Der strukturelle Test. Die oberste Stufe hat den weitesten Weg bis zum
    # Boden des Rasters; ueberlebt sie ihn nicht, sterben die oberen Stufen,
    # bevor die unteren kaufen. Das ist der Befund aus Handel/README.md,
    # Abschnitt "Grid mit Hebel - die Konstruktion traegt nicht".
    hebel_max = 1.0 / (spanne_rel + w["wartungsmarge"] + w["grid_puffer"])
    hebel = (min(w["max_hebel"], hebel_max, dl) if hebel_wunsch is None
             else float(hebel_wunsch))

    stufen = int(w["grid_stufen"])
    schritt = (kurs / unten) ** (1.0 / stufen)      # geometrisch
    stufe_pct = schritt - 1
    zyklus = 2 * w["gebuehr_maker"]

    print()
    print("-" * 66)
    print("GRID  (nur Long-Stufen, jede mit eigenem Ziel und Stop)")
    print("-" * 66)
    print("  Spanne            %.6f bis %.6f  = %.1f%% tief (%.1f ATR)" % (
        unten, kurs, spanne_rel * 100, w["grid_spanne_atr"]))
    print("  Stufen            %d, geometrisch, Abstand %.2f%%" % (stufen, stufe_pct * 100))
    print()
    print("  Hebel aus der Spanne: hoechstens %.1fx" % hebel_max)
    print("  Hebel aus dem Ruecklauf: hoechstens %.1fx" % dl)
    print("  -> gewaehlt %.1fx%s" % (
        hebel, "  (per Anweisung, --hebel %g)" % hebel_wunsch
        if hebel_wunsch is not None else ""))
    if hebel_wunsch is not None and hebel > min(hebel_max, dl) + 1e-9:
        print("     UEBER dem Deckel (%.1fx Spanne / %.1fx Ruecklauf). Wird wie" % (
            hebel_max, dl))
        print("     angewiesen gerechnet; die Pruefpflicht unten zeigt, was der")
        print("     groesste 7-Tage-Ruecklauf mit diesem Hebel gemacht haette.")
    if hebel_max < w["max_hebel"]:
        print("     (unter den %g aus wachen.json - die Spanne ist zu tief fuer mehr;" % w["max_hebel"])
        print("      mehr Hebel wuerde die oberen Stufen liquidieren, bevor die")
        print("      unteren kaufen)")

    if stufe_pct < zyklus * w["min_stufe_gebuehr"]:
        print()
        print("  ABBRUCH: Ein Stufengewinn von %.3f%% traegt den Zyklus von %.3f%%" % (
            stufe_pct * 100, zyklus * 100))
        print("  nicht (%.0ffach gefordert). Weniger Stufen oder groessere Spanne." % (
            w["min_stufe_gebuehr"]))
        return 1

    # Ein Long-Raster in einen laufenden Abwaertstrend zu legen heisst, auf
    # dem ganzen Weg nach unten zuzukaufen. Das ist der zweite Befund aus
    # Handel/README.md: "Ein Grid ist keine Absicherung; es erhoeht das
    # Engagement, waehrend der Kurs faellt."
    if z["st_richtung"] == -1:
        print()
        print("  WARNUNG: SuperTrend steht seit %d Kerzen auf AB." % z["st_dauer"])
        print("  Ein Long-Grid kauft dann auf dem ganzen Weg nach unten zu. Die")
        print("  Stufen fuellen sich der Reihe nach, ohne dass eine ihr Ziel")
        print("  erreicht. Erst wenn der SuperTrend dreht, arbeitet das Raster.")

    boden = okxf.auf_tick(instr, unten * (1 - w["grid_puffer"]))
    margin_je = gesamt_margin_erlaubt / stufen
    print()
    print("  Stufengewinn %.2f%% gegen Zyklus %.3f%% = %.0ffach gedeckt" % (
        stufe_pct * 100, zyklus * 100, stufe_pct / zyklus))
    print("  Gemeinsamer Stop aller Stufen: %.6f" % boden)
    print()
    print("  %-3s %-11s %-11s %-11s %8s %8s" % (
        "Nr", "Kauf", "Ziel", "Stop", "Kontr.", "Margin"))

    zeilen = []
    for i in range(1, stufen + 1):
        kauf = okxf.auf_tick(instr, kurs / (schritt ** i))
        ziel = okxf.auf_tick(instr, kurs / (schritt ** (i - 1)))
        nominal = margin_je * hebel
        kontrakte, echt = okxf.kontrakte_aus_nominal(instr, nominal, kauf)
        if kontrakte <= 0:
            print("  %-3d %-11.6f  -- zu klein fuer einen Kontrakt" % (i, kauf))
            continue
        liq = liquidationspreis(kauf, hebel, w["wartungsmarge"], "long")
        warn = "" if boden > liq else "  !! Stop hinter Liquidation"
        print("  %-3d %-11.6f %-11.6f %-11.6f %8g %7.2f$%s" % (
            i, kauf, ziel, boden, kontrakte, echt / hebel, warn))
        zeilen.append((i, kauf, ziel, kontrakte))

    print()
    print("  Gesamte Margin    %.2f USD von %g erlaubt%s" % (
        sum(z[3] * float(instr["ctVal"]) * z[1] for z in zeilen) / hebel,
        gesamt_margin_erlaubt, "  (--einsatz)" if einsatz is not None else ""))
    print("  Verlust, wenn alle Stufen kaufen und der Boden faellt:")
    verlust = sum(z[3] * float(instr["ctVal"]) * (z[1] - boden) for z in zeilen)
    print("    rund %.2f USD  (Kill-Switch steht bei %g)" % (
        verlust, w["kill_switch_gesamt_usd"]))
    margin_gesamt = sum(z[3] * float(instr["ctVal"]) * z[1] for z in zeilen) / hebel
    if verlust > w["kill_switch_gesamt_usd"] and verlust > 0:
        passt = margin_gesamt * w["kill_switch_gesamt_usd"] / verlust
        print("    -> UEBER dem Kill-Switch. Der Verlust waechst linear mit der")
        print("       Margin, also passt das Raster bei hoechstens %.0f USD" % passt)
        print("       Gesamtmargin (statt %.0f). Alternativ: engere Spanne" % margin_gesamt)
        print("       (grid_spanne_atr senken) - sie verkuerzt den Weg zum Boden.")

    print()
    print("  Was das Grid nicht kann: Faellt der Kurs unter %.6f, sind alle" % boden)
    print("  Stufen gestoppt und das Raster ist leer. Steigt er ueber %.6f," % kurs)
    print("  ohne vorher zu fallen, passiert gar nichts. Ein Grid gewinnt in")
    print("  der Seitwaertsbewegung und verliert im Trend - Effizienz steht")
    print("  bei %.2f." % z["er"])

    # Pruefpflicht auf der obersten Stufe: Sie hat den weitesten Weg zum
    # Boden, traegt also den groessten Einzelverlust des Rasters.
    if zeilen:
        i, kauf, zielk, _ = zeilen[0]
        print()
        print("  (Die Pruefpflicht wird auf Stufe 1 gerechnet - sie hat den")
        print("   weitesten Weg zum Boden und damit den groessten Einzelverlust.)")
        pruefpflicht(w, instr, k_hist, "long", kauf, boden, zielk, hebel,
                     was="Grid-Stufe", stat_id=hist_id)

    for i, kauf, ziel, kontrakte in zeilen:
        befehle(instr, "long", kontrakte, kauf, ziel, boden, hebel, nr=i)
    if sammle is not None:
        sammle.append({"instr": instr, "hebel": hebel, "orders": [
            ("buy", kontrakte, kauf, ziel, boden)
            for (_i, kauf, ziel, kontrakte) in zeilen]})
    return 0


def befehle(instr, seite, kontrakte, einstieg, ziel, stop, hebel, nr=None):
    """Die fertigen Aufrufe. Sie werden ausgegeben, nicht ausgefuehrt."""
    kopf = "Befehl" if nr is None else "Befehl Stufe %d" % nr
    print()
    print("  --- %s (von Hand auszufuehren) ---" % kopf)
    print("  Hebel setzen:")
    print("    okxf.hebel_setzen(%r, %g, 'isolated')" % (instr["instId"], hebel))
    print("  Order mit Ziel und Stop in einem:")
    print("    okxf.order_limit(%r, %r, %g, %.6f, tp=%.6f, sl=%.6f)" % (
        instr["instId"], "buy" if seite == "long" else "sell",
        kontrakte, einstieg, ziel, stop))


def zeige_wachen(w):
    """bot.py wachen: der Freigabe-Block und die Bedingungen 2-5 aus
    Wissen/Handelsregeln.md, wie sie fuer Spur 2 stehen.

    Zeigt die hinterlegten GRENZEN. Was davon gerade greift - Ruecklauf,
    Herzschlag-Alter, rollierender Erwartungswert -, rechnet seit dem
    03.09.2026 handeln.py --wachen aus dem Journal. Bis dahin gab es hier
    nichts durchzurechnen, weil bot.py nur vorlegte; diese Ausgabe hat den
    Satz "es gibt keinen Live-Pfad" entsprechend lange getragen.
    """
    fr = w.get("freigabe") or {}
    print("=== XPERP Wachen-Status ===")
    print("  handel_erlaubt          %s" % w.get("handel_erlaubt"))
    print("  freigabe.erfuellt       %s" % fr.get("erfuellt"))
    print("    Papierlauf min        %s Wochen / %s Runden"
          % (fr.get("papierlauf_min_wochen"), fr.get("papierlauf_min_runden")))
    if fr.get("_netto_positiv_entfaellt"):
        print("    netto positiv         entfaellt (Max 19.09.2026)")
    else:
        print("    netto positiv         %s" % fr.get("netto_positiv_nach_gebuehren_und_funding"))
    print("    groesster Ruecklauf   %s USD" % fr.get("groesster_ruecklauf_papierlauf_usd"))
    print("    geprueft am           %s" % fr.get("geprueft_am"))
    print("  2 drawdown_halbierung   %s %%" % w.get("drawdown_halbierung_prozent"))
    print("    kill_switch_gesamt    %s USD" % w.get("kill_switch_gesamt_usd"))
    print("  3 herzschlag_max        %s min" % w.get("herzschlag_max_minuten"))
    print("  4 journal_zweitziel     %s" % (w.get("journal_zweitziel") or "-- nicht gesetzt"))
    print()
    print("  Das sind die Grenzen, nicht der Stand. Was davon gerade greift,")
    print("  rechnet handeln.py --wachen aus dem Journal - seit 03.09.2026")
    print("  hat diese Spur einen Live-Pfad. bot.py selbst legt weiterhin nur")
    print("  vor: es ist der Weg fuer eine Anweisung von Max, handeln.py der")
    print("  fuer den Automaten.")


def main():
    with ereignis.lauf("handel/xperp"):
        return _main()


def _main():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("befehl", choices=("lage", "trend", "grid", "wachen"))
    p.add_argument("--wert", help="Basiswert, z.B. SOL oder RE "
                                  "(nicht noetig bei 'wachen')")
    p.add_argument("--historie", default=None, metavar="QUELLE",
                   help="Reihe fuer Hebel-Deckel und Trefferquote, wenn der "
                        "Kontrakt zu jung ist: 'auto' (=<Basis>-USDT-SWAP), "
                        "'selbst' oder ein instId wie CHIP-USDT-SWAP. Ohne "
                        "Angabe: der Kontrakt selbst.")
    p.add_argument("--hebel", type=float, default=None, metavar="N",
                   help="Hebel als Zahl (Spur 2). Ohne Angabe faellt er aus "
                        "dem Deckel. Mit Angabe gilt die Zahl; ueberschreitet "
                        "sie den Deckel, wird das in der Pruefpflicht gemeldet.")
    p.add_argument("--einsatz", type=float, default=None, metavar="USD",
                   help="Margin in USD (Spur 2: 'Einsatz'). trend: je Anlauf "
                        "statt max_margin_je_anlauf_usd. grid: Gesamtmargin "
                        "statt max_margin_gesamt_usd.")
    a = p.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    w = wachen()

    if a.befehl == "wachen":
        zeige_wachen(w)
        return 0
    if not a.wert:
        p.error("--wert ist noetig fuer '%s'" % a.befehl)

    try:
        if a.befehl == "lage":
            zeige_lage(w, a.wert, a.historie)
            return 0
        if a.befehl == "trend":
            return zeige_trend(w, a.wert, a.historie, a.hebel, a.einsatz)
        return zeige_grid(w, a.wert, a.historie, a.hebel, a.einsatz)
    except okxf.OKXFehler as e:
        print("OKX: %s" % e, file=sys.stderr)
        return 1
    finally:
        if a.befehl in ("trend", "grid"):
            print()
            print("=" * 66)
            print("Vorgelegt, nicht ausgeloest - keine Order, keine Signatur.")
            print("Gehebelt gehandelt wird nur auf ausdrueckliche Anweisung mit")
            print("Kontrakt, Richtung, Hebel, Einsatz und Stop (Handelsregeln,")
            print("Spur 2). Diese Ausgabe ist ein Vorschlag, keine Anweisung.")
            print("=" * 66)


if __name__ == "__main__":
    raise SystemExit(main())
