"""Die Handelsgebuehren der Spuren auf den GEMESSENEN Satz ziehen.

Warum es dieses Werkzeug gibt: eine Gebuehr ist der teuerste Fehler eines
Backtests und jeder Kennzahl - sie steht aber in JEDER Spur unter einem anderen
Namen (`gebuehr_taker` als Bruchteil, `gebuehr_pct` als Prozent je Seite), und
zwoelf Spuren trugen sie gar nicht. Ohne Feld rechnet der Replay mit dem
Boersensatz (replay.BOERSENSAETZE), die Auswertung schreibt "BRUTTO und
UNBEKANNT" - und eine Spur mit falschem Satz sieht besser oder schlechter aus
als sie ist. Am 01.10.2026 war beides der Fall: scanner rechnete OKX-SPOT mit
0,05 %/Seite, waehrend das Konto 0,10 % zahlt.

DIE GEMESSENEN SAETZE (01.10.2026, eigenes OKX-Konto, Angabe JE SEITE):

    OKX Spot (USDC/USDT)   taker 0,10 %   Tarif Lv1 UND echte Fuellung
                                          (HYPE-USDC: 0,002772544 auf 2,77254)
    OKX Futures/XPERP      taker 0,05 %   Tarif Lv1 UND echte Fuellungen
                                          (ZEC/ADA-USDC_XPERP)
    Kraken Spot            taker 0,60 %   gemessen 22.09.2026 an der Fuellung
                                          (siehe kraken/wachen.json)
    Kraken Futures         taker 0,04-0,05 %  gemessen 25.09.2026
                                          (nautilus_kraken/wachen.futures.json)

Nachmessen (`--messen`, rein lesend, kein Schluessel wird ausgegeben):

    python gebuehren_setzen.py --messen

Ungefragte Saetze, absichtlich NICHT angefasst (keine Messung moeglich, der
Wert ist eine Modellannahme): kopier/kopier1zu1 1,0 % (Solana-Onchain),
robinhood_radar 1,0 % (Robinhood Chain). Sie brauchen eine Entscheidung, nicht
eine Zahl aus einem anderen Markt.

Aufruf:
    python gebuehren_setzen.py                 # Vorschau (Standard)
    python gebuehren_setzen.py --anwenden      # schreiben, mit .bak-JJJJMMTT
    python gebuehren_setzen.py --messen        # Kontosaetze abfragen
"""

import argparse
import datetime as dt
import json
import os
import shutil
import sys

HIER = os.path.dirname(os.path.abspath(__file__))
HEUTE = dt.date.today().isoformat()
MARKE = dt.date.today().strftime("%Y%m%d")

# --- Die Aenderungen: Datei, Feld, Zielwert, Beleg ---------------------------------
#
# `feld in datei stehen` = nur den Wert richtigstellen; kein Eintrag = anlegen.
# Jede Zeile traegt ihren Beleg - eine Zahl ohne Quelle ist im Haus nichts wert.

QUELLE_OKX_SPOT = ("GEMESSEN 01.10.2026 am eigenen OKX-Konto (EEA): Tarif Lv1 "
                   "taker 0,10 %/Seite und echte Fuellung (HYPE-USDC 0,032 @ "
                   "86,642 = 2,77254 USDC Nettowert, Gebuehr 0,002772544 "
                   "= 0,1000 %). NICHT 0,05 % - das ist der Futures-Satz.")
QUELLE_OKX_SPOT_SPUR = ("OKX-Spot, gemessen 01.10.2026 (Tarif Lv1 taker "
                        "0,10 %/Seite + echte Fuellung HYPE-USDC 0,1000 %). Die "
                        "Spur handelt SPOT: ihre wachen.json bzw. ihr Code nennt "
                        "<SYM>-USDC bzw. BTC-USDT.")
QUELLE_OKX_PERP = ("GEMESSEN 01.10.2026 am eigenen OKX-Konto (EEA): Tarif Lv1 "
                   "FUTURES taker 0,05 %/Seite, gegengeprueft an echten "
                   "Fuellungen (ZEC-USD_UM_XPERP, ADA-USD_UM_XPERP je 0,0500 %).")
QUELLE_PERP_ENTSCHEIDUNG = (
    "Entscheidung Max 01.10.2026: als PERP gefuehrt, Satz 0,05 %/Seite "
    "(GEMESSEN am eigenen OKX-Konto: Tarif Lv1 FUTURES taker -0.0005 und echte "
    "Fuellungen ZEC-/ADA-USD_UM_XPERP je 0,0500 %). Das Instrument der Spur hat "
    "keinen eigenen OKX-Markt in der wachen.json - der Perp-Satz ist die "
    "Buchungsannahme, kein Marktsatz dieser Spur. Zur Abgrenzung: "
    "moondev_topmovers steht auf SPOT (seine wachen.json nennt USDC-Paare).")
QUELLE_KRAKEN_SPOT = ("GEMESSEN 22.09.2026 an der Kraken-Fuellung und "
                      "GET /0/private/TradeVolume: 0,6000 %/Seite "
                      "(das Pro-Abo wirkt auf diesem Konto NICHT). Als "
                      "gebuehr_taker 0.006 je Seite - ein BRUCH, nicht 0.6: "
                      "gebuehr_pct rechnet in PROZENT, und die Auswertung liest "
                      "NUR gebuehr_taker.")

# Die GEMESSENEN Saetze JE BOERSE, in Prozent je Seite. Das `boerse`-Feld einer
# wachen.json ist die Wahl; diese Tabelle ist die Rechnung dazu. Siehe
# `test_geboer_setzen.BoersenfeldTest`.
BOERSENSAETZE_PCT = {
    "okx_spot": 0.10,
    "okx_perp": 0.05,
    "kraken": 0.60,
    "kraken_futures": 0.05,
    "deribit": 0.05,
}

# `boerse: okx` allein sagt nicht, ob SPOT oder FUTURES - das sind zwei
# verschiedene Saetze (0,10 gegen 0,05 %). Bei OKX entscheidet darum NICHT das
# Boersenfeld, sondern was die Spur handelt: Perp-Spuren (XPERP, `moeglich:
# perp`) nehmen BOERSENSAETZE_PCT["okx_perp"], alles andere den Spot-Satz.
# Genau diese Unterscheidung fehlte omniquant (T-308): es handelt ueber
# kraken_futures und lasst den OKX-Satz lesen.
def satz_pct_fuer(w):
    """Der Satz dieser Wachen in PROZENT je Seite, nach den Feldern der Datei.

    Bewusst kein freies Nachschlagen in `boerse`, sondern eine Ableitung aus den
    Angaben, die die Wachen selbst traegt. Reihenfolge = Guelle des Ausgleichs:
    1. `kraken_futures` (der Name nennt Markt UND Produkt),
    2. OKX als Perp (Markttyp in der Wachen),
    3. der Börsenname fuer sich allein.

    `None` heisst: die Wachen traegt keine Angabe, aus der sich ein Satz
    ableiten laesst (Onchain, Paper ohne Boerse). Das ist KEIN Fehler, sondern
    eine Modellannahme - sie wird nur nicht beurteilt.
    """
    boerse = w.get("boerse") or w.get("venue")
    if boerse == "kraken_futures":
        return BOERSENSAETZE_PCT["kraken_futures"], "kraken_futures"
    if boerse == "deribit":
        return BOERSENSAETZE_PCT["deribit"], "deribit"
    if boerse == "okx":
        perp = ("perp" in json.dumps(w).lower()
                or w.get("moeglich") == "perp"
                or any("XPERP" in str(i) or "SWAP" in str(i)
                       for i in (w.get("instrumente") or w.get("instrumente_aktiv") or [])))
        if perp:
            return BOERSENSAETZE_PCT["okx_perp"], "okx_perp"
        return BOERSENSAETZE_PCT["okx_spot"], "okx_spot"
    if boerse == "kraken":
        return BOERSENSAETZE_PCT["kraken"], "kraken"
    return None, None


def gebuehr_pct_der_wachen(w):
    """Was in der Wachen steht, in Prozent - aus BEIDEN Feldern.

    `gebuehr_pct` ist Prozent, `gebuehr_taker` ein Bruch (die Auswertung liest
    nur dieses). Eine Spur darf nur eines davon fuehren (dann ist es eindeutig),
    oder beide (dann muessen sie dasselbe sagen). Ohne jedes Feld: `None` - und
    das ist von 0,0 zu unterscheiden, weil 0,0 eine behauptete Gebuehr waere.
    """
    pct = w.get("gebuehr_pct")
    taker = w.get("gebuehr_taker")
    if pct is None and taker is None:
        return None
    if pct is None:
        return float(taker) * 100.0
    return float(pct)

# omniquant (02.10.2026, T-308): der Widerspruch ist GEKLAERT, nicht offen. Am
# 01.10.2026 trug die wachen.json `boerse: kraken_futures` und `gebuehr_pct: 0.05`
# richtig, waehrend diese Tabelle noch 0,1 nannte - der Test schlug darum fehl und
# die Spur rechnete je nach Leser mit zwei verschiedenen Saetzen. Die Gebuehr folgt
# der BOERSE, auf der GEORDERT wird (so steht es inzwischen auch in mehreren
# wachen.json-Vermerken); der Kursweg ist davon unabhaengig - omniquant liest den
# Kurs weiter ueber okx.letzter_kurs, nur der Live-Zweig holt ihn ueber
# kraken_perp.letzter_kurs. Zu gross gesetzt (nicht zu klein) war die alte
# Fassung nicht - aber sie war eben auch FALSCH.
QUELLE_OMNIQUANT = ("GEKLAERT am 01.10.2026 (T-293, Grundlage: `boerse: kraken_futures` "
                    "und die Messung vom 25.09.2026): Kraken FUTURES 0,05 %/Seite. "
                    "Vorher stand hier 0,1 (OKX-Spot) mit dem Vermerk 'Widerspruch, "
                    "offen' - eine Absichtserklaerung fuer einen Widerspruch, den es "
                    "nicht mehr gab. Die Gebuehr folgt der ORDER-BOERSE, nicht dem "
                    "Kursweg: der Preis kommt weiter aus okx.letzter_kurs, nur der "
                    "Live-Zweig holt ihn ueber kraken_perp.")
QUELLE_KRAKEN_FUTURES = ("GEMESSEN 25.09.2026 an der eigenen Kraken-Futures-Rechnung: "
                        "0,04-0,05 % je Seite (Round-Trip 0,0029 USD auf 4,55 USD). "
                        "Vorher stand hier 0.1 - doppelt so hoch wie gemessen. Die Spur "
                        "bucht auf kraken_futures (boerse-Feld ihrer wachen.json).")
QUELLE_ANNAHME_ONCHAIN = ("MODELLANNAHME, NICHT gemessen: 1,0 % je Seite fuer "
                          "Onchain-Handel (DEX-Gebuehr plus Slippage). Der Boersensatz "
                          "waere rund das 20-fache zu niedrig und wurde bewusst nicht "
                          "gesetzt - offen als T-268 (eigene Messung oder Annahme stehen "
                          "lassen, aber dann ausdruecklich als Annahme).")

AENDERUNGEN = [
    # OKX SPOT - der falsche Satz war der teuerste Fund: scanner handelt live.
    ("scanner/wachen.json", "gebuehr_taker", 0.001, QUELLE_OKX_SPOT),
    ("squeeze/wachen.json", "gebuehr_taker", 0.001, QUELLE_OKX_SPOT),
    ("wavetrend/wachen.json", "gebuehr_taker", 0.001, QUELLE_OKX_SPOT),
    ("macd_mtf/wachen.json", "gebuehr_taker", 0.001, QUELLE_OKX_SPOT),
    ("supertrend/wachen.json", "gebuehr_taker", 0.001, QUELLE_OKX_SPOT),
    ("gitter/wachen.json", "gebuehr_taker", 0.001, QUELLE_OKX_SPOT_SPUR),
    ("iv_wand/wachen.json", "gebuehr_taker", 0.001, QUELLE_OKX_SPOT_SPUR),
    ("moondev_topmovers/wachen.json", "gebuehr_taker", 0.001,
     QUELLE_OKX_SPOT_SPUR),
    ("moondev_listingarb/wachen.json", "gebuehr_taker", 0.001,
     QUELLE_OKX_SPOT_SPUR),
    # OKX Futures/XPERP - bisher ohne Feld, der Satz ist jetzt belegt.
    ("moondev_funding/wachen.json", "gebuehr_taker", 0.0005, QUELLE_OKX_PERP),
    ("moondev_whale/wachen.json", "gebuehr_taker", 0.0005, QUELLE_OKX_PERP),
    ("moondev_liquidation/wachen.json", "gebuehr_taker", 0.0005, QUELLE_OKX_PERP),
    ("moondev_sentiment/wachen.json", "gebuehr_taker", 0.0005, QUELLE_OKX_PERP),
    # Markt nicht aus der Datei belegbar - Max hat am 01.10.2026 PERP entschieden.
    ("moondev_sniper/wachen.json", "gebuehr_taker", 0.0005,
     QUELLE_PERP_ENTSCHEIDUNG),
    ("moondev_signalwelle/wachen.json", "gebuehr_taker", 0.0005,
     QUELLE_PERP_ENTSCHEIDUNG),
    # Kraken-Spot-Arm: stand auf 0 (Abo-Annahme), die ist widerlegt.
    ("nautilus_kraken/wachen.json", "gebuehr_pct", 0.6, QUELLE_KRAKEN_SPOT),
    # Kraken SPOT, dieselbe Zahl in der Einheit, die die Auswertung liest:
    ("nautilus_kraken/wachen.json", "gebuehr_taker", 0.006, QUELLE_KRAKEN_SPOT),
    # Diese zwei fuehren den Satz NUR als `gebuehr_pct` (ihr eigener Code) -
    # die AUSWERTUNG liest aber `gebuehr_taker` und meldete deshalb "BRUTTO und
    # UNBEKANNT", obwohl die Zahl bekannt war. Dieselbe Zahl, beide Felder.
    ("nautilus/wachen.json", "gebuehr_taker", 0.0005, QUELLE_OKX_PERP),
    ("nautilus_kraken/wachen.futures.json", "gebuehr_taker", 0.0005,
     "GEMESSEN 25.09.2026 an der Kraken-Futures-Rechnung: 0,04-0,05 %/Seite "
     "(Round-Trip 0,0029 USD auf 4,55 USD). Derselbe Satz steht dort schon als "
     "`gebuehr_pct` 0.05 - die Auswertung liest `gebuehr_taker`."),
    # --- Spuren, deren Satz schon stand, aber OHNE Quelle. Befund 01.10.2026
    # beim Festziehen: "Wert ohne Quelle ist nicht nachpruefbar".
    ("liq_wand/wachen.json", "gebuehr_taker", 0.0005, QUELLE_OKX_PERP),
    ("trendwende_btc/wachen.json", "gebuehr_taker", 0.0005, QUELLE_OKX_PERP),
    ("omnitrade/wachen.json", "gebuehr_taker", 0.006, QUELLE_KRAKEN_SPOT),
    # omniquant + Schattenarm: rechnen auf Kraken FUTURES (`boerse` ihrer
    # wachen.json), gemessen 0,05 %/Seite. Vorher stand hier 0,1 als
    # OKX-Spot-Satz mit offengehaltenem Widerspruch - T-308.
    # `gebuehr_taker` kommt dazu, weil die generische Auswertung
    # (`auswertung_alle.gebuehr_fuer`) NUR dieses Feld liest; ohne es meldete
    # jede allgemeine Auswertung 0,0 und damit eine Runde ohne Kosten.
    ("omniquant/wachen.json", "gebuehr_pct", 0.05, QUELLE_OMNIQUANT),
    ("omniquant/wachen.json", "gebuehr_taker", 0.0005, QUELLE_OMNIQUANT),
    ("omniquant/wachen.weit.json", "gebuehr_pct", 0.05, QUELLE_OMNIQUANT),
    ("omniquant/wachen.weit.json", "gebuehr_taker", 0.0005, QUELLE_OMNIQUANT),
    ("kopier/wachen.json", "gebuehr_pct", 1.0, QUELLE_ANNAHME_ONCHAIN),
    ("kopier1zu1/wachen.json", "gebuehr_pct", 1.0, QUELLE_ANNAHME_ONCHAIN),
    ("robinhood_radar/wachen.json", "gebuehr_taker", 0.01, QUELLE_ANNAHME_ONCHAIN),
    ("spiegel/wachen.json", "gebuehr_pct", 1.0, QUELLE_ANNAHME_ONCHAIN),
    ("spiegel/wachen.knapp.json", "gebuehr_pct", 1.0, QUELLE_ANNAHME_ONCHAIN),
    ("spiegel/wachen.weit.json", "gebuehr_pct", 1.0, QUELLE_ANNAHME_ONCHAIN),
]


def _eol(text):
    return "\r\n" if "\r\n" in text else "\n"


def _lesen(pfad):
    with open(pfad, "rb") as f:
        roh = f.read().decode("utf-8")
    return roh, json.loads(roh)


def _feld_setzen(roh, feld, wert, quelle):
    """Feld setzen, ohne die Datei neu zu formatieren: Textersatz je Zeile.

    Ein `json.dump` waere kuerzer, wuerde aber die Reihenfolge und die
    Kommentar-Schluessel (`_zweck`, `_risiko_erklaerung`) neu schreiben - bei
    Handelswachen ist ein diff mit einer Zeile das, was ein Mensch pruefen kann.

    Die QUELLE wird mitgesetzt, nicht danebengelassen: eine alte
    `_gebuehr_quelle` ueber einem neuen Wert waere ein Widerspruch in der Datei
    selbst (genau der Fehler, den dieses Werkzeug behebt).
    """
    eol = _eol(roh)
    zeilen = roh.split(eol)
    wert_text = ("%g" % wert) if isinstance(wert, float) else json.dumps(wert)
    feld_zeile = notiz_zeile = None
    for i, z in enumerate(zeilen):
        s = z.lstrip()
        if s.startswith('"_gebuehr_quelle"'):
            notiz_zeile = i
        if s.startswith('"%s"' % feld):
            feld_zeile = i
    alt = None
    if feld_zeile is not None:
        alt = zeilen[feld_zeile].split(":", 1)[1].strip().rstrip(",")
        zeilen[feld_zeile] = (zeilen[feld_zeile].split(":", 1)[0] + ": "
                              + wert_text
                              + ("," if zeilen[feld_zeile].rstrip().endswith(",")
                                 else ""))
    if notiz_zeile is not None:
        # ACHTUNG: die Notiz kann OHNE den Wert dastehen (am 01.10.2026 so
        # gefunden: nautilus_kraken trug eine _gebuehr_quelle aus einem
        # frueheren Lauf, aber kein gebuehr_taker). Dann wird der WERT hier
        # eingesetzt - vorher fiel er still unter den Tisch und `anwenden()`
        # stuerzte danach mit einem irrefuehrenden TypeError ab.
        hat_komma = zeilen[notiz_zeile].rstrip().endswith(",")
        zeilen[notiz_zeile] = ('  "_gebuehr_quelle": %s%s'
                               % (json.dumps(quelle), "," if hat_komma else ""))
        if feld_zeile is None:
            if hat_komma:
                zeilen.insert(notiz_zeile, '  "%s": %s,' % (feld, wert_text))
            else:
                zeilen[notiz_zeile] += ","
                zeilen.insert(notiz_zeile + 1, '  "%s": %s' % (feld, wert_text))
    elif feld_zeile is not None:
        if not zeilen[feld_zeile].rstrip().endswith(","):
            zeilen[feld_zeile] = zeilen[feld_zeile].rstrip() + ","
        zeilen.insert(feld_zeile + 1,
                      '  "_gebuehr_quelle": %s,' % json.dumps(quelle))
    else:
        # Feld fehlt: Notiz und Feld als LETZTE Schluessel vor die schliessende
        # Klammer des Objekts setzen (ohne Komma am Ende).
        for i in range(len(zeilen) - 1, -1, -1):
            if zeilen[i].strip() == "}":
                vor = i - 1
                while vor > 0 and not zeilen[vor].strip():
                    vor -= 1
                if not zeilen[vor].rstrip().endswith(","):
                    zeilen[vor] = zeilen[vor].rstrip() + ","
                zeilen[i:i] = ['  "_gebuehr_quelle": %s,' % json.dumps(quelle),
                               '  "%s": %s' % (feld, wert_text)]
                break
        else:
            raise ValueError("keine schliessende Klammer gefunden")
    _komma_am_ende_weg(zeilen)
    return eol.join(zeilen), alt


def _komma_am_ende_weg(zeilen):
    """Der LETZTE Schluessel vor der schliessenden Klammer traegt kein Komma.

    Ohne diesen Durchgang entsteht ungueltiges JSON, sobald der neue Schluessel
    hinter dem bisher letzten landet - gefunden am 01.10.2026 durch den Test
    `test_erfolgsfall_schreibt_und_meldet`: `json.decoder.JSONDecodeError:
    Illegal trailing comma before end of object`. In den echten Wachen fiel es
    nicht auf, weil dort nach dem Wert immer noch ein Schluessel stand.
    """
    for i in range(len(zeilen) - 1, -1, -1):
        if zeilen[i].strip() == "}":
            vor = i - 1
            while vor > 0 and not zeilen[vor].strip():
                vor -= 1
            if zeilen[vor].rstrip().endswith(","):
                zeilen[vor] = zeilen[vor].rstrip()[:-1]
            break
    return zeilen


def vorschau():
    print("%-38s %-15s %-10s %s" % ("Datei", "Feld", "alt -> neu", "Beleg"))
    offen = 0
    for datei, feld, wert, quelle in AENDERUNGEN:
        pfad = os.path.join(HIER, datei)
        try:
            _roh, d = _lesen(pfad)
        except (OSError, ValueError) as e:
            print("%-38s FEHLER %s" % (datei, e))
            continue
        alt = d.get(feld)
        if (alt is not None and float(alt) == float(wert)
                and d.get("_gebuehr_quelle") == quelle):
            print("%-38s %-15s %s" % (datei, feld, "schon richtig"))
            continue
        offen += 1
        print("%-38s %-15s %-10s %s"
              % (datei, feld, "%s -> %g" % ("-" if alt is None else alt, wert),
                 quelle.split(".")[0][:60]))
    print("\n%d von %d Aenderung(en) offen." % (offen, len(AENDERUNGEN)))
    return offen


def anwenden():
    getan = 0
    for datei, feld, wert, quelle in AENDERUNGEN:
        pfad = os.path.join(HIER, datei)
        roh, d = _lesen(pfad)
        alt = d.get(feld)
        if (alt is not None and float(alt) == float(wert)
                and d.get("_gebuehr_quelle") == quelle):
            continue
        neu_text, _ = _feld_setzen(roh, feld, wert, quelle)
        json.loads(neu_text)                       # erst pruefen, DANN schreiben
        shutil.copy2(pfad, pfad + ".bak-" + MARKE)
        with open(pfad, "wb") as f:
            f.write(neu_text.encode("utf-8"))
        _roh, neu = _lesen(pfad)
        neu_wert = neu.get(feld)
        if neu_wert is None or float(neu_wert) != float(wert):
            raise RuntimeError(
                "%s: %s steht auf %r (erwartet %g) - das Feld liess sich nicht "
                "setzen. Datei pruefen, Sicherung <datei>.bak-%s liegt daneben."
                % (datei, feld, neu_wert, wert, MARKE))
        print("%-38s %s: %s -> %g" % (datei, feld,
                                      "-" if alt is None else alt, wert))
        getan += 1
    print("\n%d Datei(en) geaendert (Sicherung: <datei>.bak-%s)." % (getan, MARKE))
    return getan


# --- Nachmessen -------------------------------------------------------------

def _okx():
    sys.path.insert(0, os.path.join(HIER, "scanner"))
    import okx
    return okx


def messen():
    okx = _okx()
    print("Basis:", okx._live_basis())
    if not okx.schluessel_vorhanden():
        print("OKX_LIVE_* fehlen - nicht messbar.")
        return
    for typ, inst in (("SPOT", "HYPE-USDC"), ("FUTURES", None)):
        pfad = "/api/v5/account/trade-fee?instType=%s" % typ
        try:
            daten = okx._roh(pfad, signiert=True) or []
        except Exception as e:                                   # noqa: BLE001
            print("  %s: FEHLER %s" % (typ, str(e)[:120]))
            continue
        for z in daten[:1]:
            print("  Tarif %-8s level=%s maker=%s taker=%s (Bruchteil je Seite)"
                  % (typ, z.get("level"), z.get("maker"), z.get("taker")))
    # Eine ECHTE Fuellung je Instrumentenart - der Tarif allein ist eine Seite.
    for typ in ("SPOT", "FUTURES"):
        fills = okx._roh("/api/v5/trade/fills?instType=%s&limit=5" % typ,
                         signiert=True) or []
        for f in fills[:2]:
            print("  Fuellung %-8s %s %s @ %s -> Gebuehr %s %s"
                  % (typ, f.get("side"), f.get("fillSz"), f.get("fillPx"),
                     f.get("fee"), f.get("feeCcy")))
    print("\nKraken Spot/Futures: siehe kraken/wachen.json (_gebuehren) und "
          "nautilus_kraken/wachen.futures.json - dort sind die Messungen "
          "vom 22./25.09.2026 abgelegt.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anwenden", action="store_true")
    ap.add_argument("--messen", action="store_true")
    a = ap.parse_args()
    if a.messen:
        messen()
        return
    if a.anwenden:
        anwenden()
        return
    vorschau()


if __name__ == "__main__":
    main()
