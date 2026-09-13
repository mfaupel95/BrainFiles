"""CVD-4h-Divergenz aus dem OKX-Taker-Volumen - Nachbau des Buildix-Signals.

Was gerechnet wird
------------------
CVD (Cumulative Volume Delta) ist die laufende Summe aus aggressivem
Kaufvolumen minus aggressivem Verkaufsvolumen, hier in 4h-Eimern. Eine
Divergenz liegt vor, wenn der Preis ein neues Extrem macht und das Delta es
nicht bestaetigt (Rally ohne CVD = weak, Reversal wahrscheinlich). Das ist
dieselbe Logik, die buildix.trade als Signal-Label fuehrt: STRONG BUY
(accumulation near lows) / STRONG SELL (distribution near highs) / NEUTRAL.

Woher die Zahlen kommen
-----------------------
`okxf.taker_volumen(inst, "4H")` - OKX fuehrt das Taker-Volumen je Kontrakt
unter /api/v5/rubik/stat/taker-volume-contract. Das ist die von der Boerse
aggregierte Fassung desselben Trade-Tapes, aus dem Buildix rechnet.

Das ROHE Tape traegt 4 Stunden nicht: /api/v5/market/history-trades liefert 100
Trades je Anfrage, und 100 Trades sind bei BTC-USDT-SWAP 28 Sekunden
(gemessen am 13.09.2026, dasselbe bei CHIP und WLFI). 4 Stunden waeren rund
4000 Anfragen je Reihe - bei 40 Anfragen je 2 s ueber eine Stunde fuer EINEN
Wert. Der Taker-Volumen-Endpunkt liefert dieselbe Aussage in einer Anfrage,
100 Eimer tief (4h-Eimer = rund 16 Tage).

Einheit: Kontrakte, so wie das Volumen in den OKX-Kerzen steht - die Summe
der beiden Seiten eines 4h-Eimers deckt sich mit dem Volumen der
entsprechenden 4h-Kerze. Fuer die Divergenz zaehlt das Vorzeichen und die
Form, nicht die Einheit; die Ausgabe nennt deshalb den Anteil an der
Bewegung, nicht die Kontraktzahl.

Host-Falle: dieser Abruf muss auf den globalen API-Host. Auf my.okx.com (der
OKX_BASE dieser Maschine) und auf eea.okx.com antwortet der Endpunkt mit
code 0 und LEERER Liste - kein Fehler, nur nichts, und damit ein stilles
"kein Signal". okxf.rubik_basis() kapselt das; der Grund einer leeren Antwort
nennt den benutzten Host.

Nur lesend. Kein Import aus einem Order-Pfad, keine Order-Funktion.
"""

BAR = "4H"
BAR_MS = 4 * 3_600_000

# 12 Eimer = 48 h. Kuerzer kippt bei jedem Rauschen, laenger verpasst den
# Anlass; die Wahl ist aus dem Buildix-Signal uebernommen (dort "CVD 4h").
EIMER = 12

# Ein Divergenz-Paar aus zwei Haelften braucht eine Mindestbewegung, sonst ist
# es Rauschen: die juengere Haelfte muss sich um mindestens diesen Anteil der
# gesamten Fensterspanne vom Mittel der aelteren abheben.
MIN_BEWEGUNG = 0.15
STARK_BEWEGUNG = 0.30

# "near highs" / "near lows" aus dem Buildix-Signal: eine baerische Divergenz
# zaehlt nur in der oberen, eine bullische nur in der unteren Fensterhaelfte.
# In der Mitte des Bereichs ist ein Aufwaertspreis mit fallendem CVD kein
# Signal, sondern ein Zufall des Ausschnitts.
NAEHE_HOCH = 0.60
NAEHE_TIEF = 0.40

# Untergrenze fuer die CVD-Seite: die Steigung der juengsten Haelfte muss
# mindestens diesen Anteil der mittleren absoluten Eimer-Bewegung betragen,
# und zwar gegen die Preisrichtung. Ohne diese Untergrenze zaehlt auch eine
# Steigung von +0.2 % als "Akkumulation" - das Tor geht dann auf, aber es
# steht nichts dahinter.
#
# Kalibriert am 13.09.2026 an der eigenen Verteilung: 15 USDT-Perpetuals,
# 1287 Fenster ueber je 12 4h-Eimer, davon 142 mit Divergenz. Die Verteilung
# von |CVD-Anteil| in diesen 142: min 0.002, p10 0.037, p25 0.142,
# Median 0.333, p75 0.623, max 1.202. Das untere Fuenftel (27 Fenster unter
# 0.10) ist das Rauschband; die Schwelle 0.10 schneidet es weg und laesst
# 8.9 % aller Fenster als Signal stehen (vorher 11.0 %).
MIN_CVD_ANTEIL = 0.10


def leer(grund=""):
    """Neutrale Lage - kein Signal, mitlesbarer Grund. Nie None zurueckgeben:
    lage() darf an einer fehlenden Quelle nicht scheitern."""
    return {"richtung": 0, "stark": False, "n": 0, "d_preis": None,
            "d_cvd": None, "cvd_anteil": None, "preis_pct": None,
            "spanne": None, "lage_im_bereich": None, "eimer": 0,
            "grund": grund}


def _erste_reihe(tape):
    """OKX liefert taker-volume-contract neueste-zuerst als
    [ts, verkaufsvolumen, kaufvolumen]. Rueckgabe: {ts: (verkauf, kauf)}."""
    eimer = {}
    for r in tape or []:
        try:
            eimer[int(r[0])] = (float(r[1]), float(r[2]))
        except (TypeError, ValueError, IndexError):
            continue
    return eimer


def reihen(kerzen, tape, eimer=EIMER):
    """Preis- und CVD-Reihe auf dem 4h-Raster, nur lueckenlose Eimer.

    Rueckgabe (kerzen, cvd_werte) oder (None, None), wenn die juengsten `eimer`
    Eimer nicht lueckenlos zusammenhaengen - ein Fenster mit Loch darin ist
    keine Divergenz, sondern eine andere Frage.
    """
    tabelle = _erste_reihe(tape)
    if not tabelle:
        return None, None
    paare = [k for k in kerzen if int(k[0]) in tabelle]
    if len(paare) < eimer:
        return None, None
    paare = paare[-eimer:]
    for a, b in zip(paare, paare[1:]):
        if int(b[0]) - int(a[0]) != BAR_MS:
            return None, None
    cvd, summe = [], 0.0
    for k in paare:
        verkauf, kauf = tabelle[int(k[0])]
        summe += kauf - verkauf
        cvd.append(summe)
    return paare, cvd


def divergenz(kerzen, cvd_werte,
              min_bewegung=MIN_BEWEGUNG, stark_bewegung=STARK_BEWEGUNG,
              min_cvd_anteil=MIN_CVD_ANTEIL):
    """Divergenz zwischen Preis und CVD in einem fertig ausgerichteten Fenster.

    Halbiert das Fenster und stellt die Mittel der beiden Haelften einander
    gegenueber:
      - juengere Haelfte teurer, aber CVD gefallen  -> -1 (Verteilung oben)
      - juengere Haelfte billiger, aber CVD gestiegen -> +1 (Akkumulation unten)
    Der CVD zaehlt dabei als mittlere Steigung der juengsten Haelfte, nicht als
    Mittelwert des Standes - der Stand traegt die Vorgeschichte mit. Und er
    muss sich deutlich genug gegen die Preisrichtung stellen: unter
    min_cvd_anteil der mittleren Eimer-Bewegung ist es Rauschen (Begruendung
    und Messung bei MIN_CVD_ANTEIL).
    Sonst 0. `stark` markiert eine klarere Preisbewegung im Fenster - dieselbe
    Rolle wie in volumen_drift(), kein zweites Signal.
    """
    z = leer("Fenster zu klein")
    n = len(kerzen)
    if cvd_werte is None or n < 4 or len(cvd_werte) != n:
        return z
    halb = n // 2
    preis = [k[4] for k in kerzen]
    oben = max(k[2] for k in kerzen)
    unten = min(k[3] for k in kerzen)
    spanne = oben - unten
    if spanne <= 0 or preis[-1] <= 0:
        return z

    d_preis = sum(preis[halb:]) / (n - halb) - sum(preis[:halb]) / halb
    # Der CVD wird als STEHUNG der juengsten Haelfte gemessen, nicht als
    # Mittelwert des Standes: der Stand traegt die ganze Vorgeschichte mit, ein
    # steil gestiegener und dann leicht gefallener CVD haette sonst immer noch
    # einen hoeheren Mittelwert als die aeltere Haelfte - und eine Verteilung
    # saehe wie Bestaetigung aus. Gemessen wird die mittlere Differenz je Eimer.
    d_cvd = (cvd_werte[-1] - cvd_werte[halb - 1]) / (n - halb)
    summe_abs = sum(abs(cvd_werte[i] - cvd_werte[i - 1])
                    for i in range(1, n))
    mittlere_bewegung = summe_abs / (n - 1)
    lage_im_bereich = (preis[-1] - unten) / spanne

    richtung = 0
    if d_preis > 0 and d_cvd < 0 and lage_im_bereich >= NAEHE_HOCH:
        richtung = -1
    elif d_preis < 0 and d_cvd > 0 and lage_im_bereich <= NAEHE_TIEF:
        richtung = 1
    if richtung != 0 and abs(d_preis) < min_bewegung * spanne:
        richtung = 0
    if (richtung != 0 and mittlere_bewegung > 0
            and abs(d_cvd) < min_cvd_anteil * mittlere_bewegung):
        richtung = 0

    return {
        "richtung": richtung,
        "stark": richtung != 0 and abs(d_preis) >= stark_bewegung * spanne,
        "n": n,
        "d_preis": d_preis,
        "d_cvd": d_cvd,
        "cvd_anteil": (d_cvd / mittlere_bewegung) if mittlere_bewegung > 0 else None,
        "preis_pct": d_preis / preis[-1],
        "spanne": spanne,
        "lage_im_bereich": lage_im_bereich,
        "eimer": n,
        "grund": "" if richtung else "keine Divergenz",
    }


def cvd_4h(inst, eimer=EIMER):
    """Die CVD-4h-Lage eines Instruments - ein Abruf Taker-Volumen, ein Abruf
    Kerzen.

    Faellt die Quelle aus (Netz, 429, unbekanntes Instrument), kommt eine
    neutrale Lage mit Grund zurueck. Ein neuer Datenabruf im Signalpfad darf
    das Signal nicht umbringen: lage() laeuft in jedem Zyklus jeder Spur.
    """
    import okxf

    tape = None
    fehler = ""
    for versuch in (1, 2):
        try:
            tape = okxf.taker_volumen(inst, BAR)
            break
        except Exception as e:                                # noqa: BLE001
            fehler = str(e)
            # 429 (50011 Too Many Requests) ist der einzige Grund, der sich
            # durch kurzes Warten heilt - alles andere ist fachlich.
            if "Too Many Requests" not in fehler and "50011" not in fehler:
                break
            if versuch == 1:
                import time
                time.sleep(1.2)
    if not tape:
        # Der Host gehoert in den Grund: auf my.okx.com/eea.okx.com kommt
        # hier code 0 mit leerer Liste, und "leer" ohne Hostangabe laesst
        # sich nicht deuten. okxf.rubik_basis() weiss den benutzten Host.
        return leer("Taker-Volumen %s (Host %s)"
                    % (fehler or "ohne Zeilen", okxf.rubik_basis()))

    try:
        kerzen = okxf.kerzen(inst, BAR, 300)
    except Exception as e:                                    # noqa: BLE001
        return leer("Kerzen nicht lesbar: %s" % e)
    if not kerzen:
        return leer("keine 4h-Kerzen zu %s" % inst)

    paare, cvd_werte = reihen(kerzen, tape, eimer)
    if not paare:
        return leer("kein lueckenloses %d-Eimer-Fenster (Tape %d Eimer, "
                    "Kerzen %d)" % (eimer, len(_erste_reihe(tape)), len(kerzen)))

    z = divergenz(paare, cvd_werte)
    z["grund"] = z["grund"] if z["richtung"] else "keine Divergenz in %d Eimern" % eimer
    return z


def marke(z):
    """Eine Zeile fuer den Signal-Grund - nennt Richtung UND Zahlen, damit die
    Drehung nachpruefbar bleibt."""
    if z["richtung"] == 0:
        return ""
    return "CVD-4h-Divergenz %s (Preis %+.2f%%, CVD %+.0f%% der Bewegung, n=%d)" % (
        "bearish" if z["richtung"] == -1 else "bullish",
        (z["preis_pct"] or 0.0) * 100,
        (z["cvd_anteil"] or 0.0) * 100,
        z["eimer"])
