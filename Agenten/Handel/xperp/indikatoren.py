"""Indikatoren auf Kerzenreihen - reine Rechnung, keine Netzzugriffe.

Eingabe ist immer eine Liste [ts, offen, hoch, tief, schluss, volumen],
aufsteigend sortiert, wie sie okxf.kerzen() liefert. Jede Funktion gibt eine
Liste gleicher Laenge zurueck; die ersten Werte sind None, solange das Fenster
nicht voll ist. Das ist Absicht - ein mit dem ersten Kurs aufgefuellter
Indikator sieht am Anfang nach einem Signal aus, wo keines ist.

ATR ist hier die tragende Groesse, nicht nur ein Indikator unter vielen: Aus
ihm faellt der Stop-Abstand, und aus dem Stop-Abstand faellt die
Positionsgroesse. Der Hebel ist dann Ergebnis und nicht Eingabe.

saisonalitaet() ist am 01.09.2026 dazugekommen: der Nachbau des Closed-Source-
Indikators "xGhozt Prophecies" von TradingView - Kalenderstatistik nach
Wochentag und Tagesphase (UTC). Der Pine-Code ist nicht einsehbar, also ist
hier nur das Prinzip nachgerechnet, nicht der Indikator kopiert. Auf Anweisung
wird sie in lage() HOCH gewichtet und darf die Richtung setzen und gegen
SuperTrend+EMA kippen - anders als die uebrigen Bausteine, die lage() bewusst
nicht verrechnet. Die Stichprobe ist duenn (rund sieben Kerzen je Wochentag auf
300 x 4h); jede Ausgabe nennt n mit, damit sichtbar bleibt, worauf eine
Drehung steht.

Dritte Ausnahme seit 13.09.2026: cvd_4h() aus cvd.py (CVD-4h-Divergenz,
Nachbau des Buildix-Signals) ist ebenfalls HOCH gewichtet und laeuft als
letzte Komponente - bei Widerspruch gewinnt sie. Sie braucht das gehandelte
Instrument (inst); ohne inst wird sie uebersprungen, damit aeltere Aufrufer
unveraendert weiterlaufen.
"""

from datetime import datetime, timezone

import cvd

# Seam fuer Tests: hier eine Funktion setzen, und lage() nimmt deren Ergebnis
# statt cvd.cvd_4h() (das echt ueber OKX geht). None = echter Abruf.
cvd_quelle = None

WOCHENTAGE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def wahre_spanne(k):
    """True Range je Kerze. Erste Kerze hat keine Vorgaengerin -> None."""
    tr = [None]
    for i in range(1, len(k)):
        tr.append(max(k[i][2] - k[i][3],
                      abs(k[i][2] - k[i - 1][4]),
                      abs(k[i][3] - k[i - 1][4])))
    return tr


def atr(k, n=14):
    """Average True Range, Wilder-Glaettung (wie in den meisten Charts)."""
    tr = wahre_spanne(k)
    out = [None] * len(k)
    if len(k) <= n:
        return out
    schnitt = sum(tr[1:n + 1]) / n
    out[n] = schnitt
    for i in range(n + 1, len(k)):
        schnitt = (schnitt * (n - 1) + tr[i]) / n
        out[i] = schnitt
    return out


def ema(werte, n):
    out = [None] * len(werte)
    if len(werte) < n:
        return out
    start = sum(werte[:n]) / n
    out[n - 1] = start
    f = 2.0 / (n + 1)
    for i in range(n, len(werte)):
        start = werte[i] * f + start * (1 - f)
        out[i] = start
    return out


def rsi(werte, n=14):
    out = [None] * len(werte)
    if len(werte) <= n:
        return out
    gew = [max(0.0, werte[i] - werte[i - 1]) for i in range(1, len(werte))]
    ver = [max(0.0, werte[i - 1] - werte[i]) for i in range(1, len(werte))]
    ag = sum(gew[:n]) / n
    av = sum(ver[:n]) / n
    out[n] = 100.0 if av == 0 else 100 - 100 / (1 + ag / av)
    for i in range(n, len(gew)):
        ag = (ag * (n - 1) + gew[i]) / n
        av = (av * (n - 1) + ver[i]) / n
        out[i + 1] = 100.0 if av == 0 else 100 - 100 / (1 + ag / av)
    return out


def supertrend(k, n=10, faktor=3.0):
    """SuperTrend. Gibt (linie, richtung) zurueck, richtung ist +1 oder -1.

    Die Baender liegen faktor x ATR um den Kerzenmittelpunkt. Entscheidend ist
    die Nachzieh-Logik: Ein Band darf sich nur in Richtung des Trends bewegen,
    nie zurueck. Ohne diese Sperre zappelt der Indikator mit jedem Ausreisser
    und liefert doppelt so viele Signale wie er soll.
    """
    a = atr(k, n)
    ob = [None] * len(k)
    ub = [None] * len(k)
    richtung = [None] * len(k)
    linie = [None] * len(k)

    for i in range(len(k)):
        if a[i] is None:
            continue
        mitte = (k[i][2] + k[i][3]) / 2
        o = mitte + faktor * a[i]
        u = mitte - faktor * a[i]

        if ob[i - 1] is None:
            ob[i], ub[i], richtung[i] = o, u, 1
        else:
            # Nachziehen nur in Trendrichtung
            ob[i] = o if (o < ob[i - 1] or k[i - 1][4] > ob[i - 1]) else ob[i - 1]
            ub[i] = u if (u > ub[i - 1] or k[i - 1][4] < ub[i - 1]) else ub[i - 1]
            if richtung[i - 1] == 1 and k[i][4] < ub[i - 1]:
                richtung[i] = -1
            elif richtung[i - 1] == -1 and k[i][4] > ob[i - 1]:
                richtung[i] = 1
            else:
                richtung[i] = richtung[i - 1]
        linie[i] = ub[i] if richtung[i] == 1 else ob[i]
    return linie, richtung


def effizienz(werte, n=42):
    """Kaufman Efficiency Ratio: Nettobewegung / zurueckgelegter Weg.

    Nahe 1 = sauberer Trend (Trendstrategie sinnvoll).
    Nahe 0 = Gezappel (Grid sinnvoll, Trendstrategie wird zerrieben).
    """
    f = werte[-min(n, len(werte)):]
    if len(f) < 2:
        return None
    weg = sum(abs(f[i] - f[i - 1]) for i in range(1, len(f)))
    return abs(f[-1] - f[0]) / weg if weg > 0 else 0.0


def _gleichzeitig(k, k_stat, kerzen=2):
    """Enden beide Reihen (fast) auf derselben Kerze?

    saisonalitaet() bestimmt Wochentag und Tagesphase der naechsten Kerze aus
    dem Ende der uebergebenen Reihe. Eine verschobene oder alte Reihe wuerde das
    Raster still verschieben - dann bleibt es bei der eigenen Reihe.
    """
    if not k or not k_stat:
        return False
    schritt = (k[-1][0] - k[-2][0]) if len(k) >= 2 else 0
    if schritt <= 0 and len(k_stat) >= 2:
        schritt = k_stat[-1][0] - k_stat[-2][0]
    return abs(k[-1][0] - k_stat[-1][0]) <= kerzen * max(schritt, 1)


def saisonalitaet(k, min_n=6):
    """Kalenderstatistik nach dem Prinzip von "xGhozt Prophecies" (TradingView,
    Closed-Source - hier nachgerechnet, nicht kopiert).

    Nimmt die naechste, noch nicht existierende Kerze, bestimmt ihren Wochentag
    und ihre Tagesphase (UTC) und misst an allen frueheren Kerzen desselben
    Rasters, wie oft sie ueber ihrem Eroeffnungskurs schlossen und wie gross
    die mittlere Kerzenrendite war.

    Zwei Aggregationen, weil die feine (Wochentag + Phase) auf 300 Kerzen nur
    eine Handvoll Treffer hat:
      - Wochentag:        alle Kerzen desselben Wochentags     (~len/7)
      - Wochentag+Phase:  zusaetzlich dieselbe 4h-Phase         (~len/42)

    richtung ist +1/-1/0 und wird nur gesetzt, wenn die groebere Aggregation
    mindestens min_n Beobachtungen hat UND Auf-Quote und mittlere Rendite
    dasselbe Vorzeichen zeigen. Sonst 0 - die Statistik sagt dann nichts.
    Das ist Rueckblick auf einem duennen Fenster, keine Zusage.
    """
    leer = {"richtung": 0, "n": 0, "n_phase": 0, "quote": None,
            "quote_phase": None, "mittel": None, "mittel_phase": None,
            "wochentag": None, "phase_h": None, "stark": False}
    if len(k) < min_n + 1:
        return leer

    bar_h = 4.0
    if len(k) >= 2:
        bar_h = max(1.0, round((k[-1][0] - k[-2][0]) / 3_600_000.0))
    ziel = datetime.fromtimestamp((k[-1][0] + int(bar_h * 3_600_000)) / 1000,
                                  timezone.utc)
    ziel_wt = ziel.weekday()
    ziel_phase = int(ziel.hour // bar_h)

    def sammle(nur_phase):
        auf = n = 0
        summe = 0.0
        for row in k:
            d = datetime.fromtimestamp(row[0] / 1000, timezone.utc)
            if d.weekday() != ziel_wt:
                continue
            if nur_phase and int(d.hour // bar_h) != ziel_phase:
                continue
            o, c = row[1], row[4]
            if o <= 0:
                continue
            n += 1
            auf += 1 if c > o else 0
            summe += (c - o) / o
        return (n, auf / n, summe / n) if n else (0, None, None)

    n, quote, mittel = sammle(False)
    n_ph, quote_ph, mittel_ph = sammle(True)

    richtung, stark = 0, False
    if n >= min_n and quote is not None:
        if quote >= 0.58 and mittel > 0:
            richtung, stark = 1, (quote >= 0.65 or mittel > 0.004)
        elif quote <= 0.42 and mittel < 0:
            richtung, stark = -1, (quote <= 0.35 or mittel < -0.004)

    return {"richtung": richtung, "n": n, "n_phase": n_ph,
            "quote": quote, "quote_phase": quote_ph,
            "mittel": mittel, "mittel_phase": mittel_ph,
            "wochentag": WOCHENTAGE[ziel_wt], "phase_h": int(ziel_phase * bar_h),
            "stark": stark}


def _serie_verschmelzen(k, faktor):
    """Fasst je `faktor` aufeinanderfolgende Kerzen zu einer zusammen - eine
    naeherungsweise hoehere Zeitebene aus derselben Reihe, ohne Zusatzabruf.
    Ueberzaehlige aelteste Kerzen (die keine volle Gruppe mehr fuellen) fallen
    vorn weg, damit die juengste Kerze immer eine volle Gruppe abschliesst.
    """
    if faktor <= 1:
        return k
    rest = len(k) % faktor
    out = []
    for i in range(rest, len(k), faktor):
        gruppe = k[i:i + faktor]
        out.append([
            gruppe[-1][0],
            gruppe[0][1],
            max(r[2] for r in gruppe),
            min(r[3] for r in gruppe),
            gruppe[-1][4],
            sum(r[5] for r in gruppe),
        ])
    return out


def _drift_score(k, n):
    """Volumengewichtete Preisdrift der letzten n Kerzen, ATR-normiert, plus
    Volumen-Verhaeltnis (Fenster gegen das gleich lange Fenster davor).
    (None, None) bei zu wenig Historie oder wenn ATR/Volumen nicht tragen.
    """
    if len(k) < 2 * n + 1:
        return None, None
    a = atr(k, 14)
    if a[-1] is None or a[-1] == 0:
        return None, None
    zaehler = sum((k[i][4] - k[i - 1][4]) * k[i][5] for i in range(len(k) - n, len(k)))
    vol_fenster = sum(k[i][5] for i in range(len(k) - n, len(k)))
    if vol_fenster == 0:
        return None, None
    vol_vorher = sum(r[5] for r in k[len(k) - 2 * n:len(k) - n])
    if vol_vorher == 0:
        return None, None
    score = (zaehler / vol_fenster) / a[-1]
    verhaeltnis = (vol_fenster / n) / (vol_vorher / n)
    return score, verhaeltnis


def volumen_drift(k, n=20, min_score=0.15, min_verhaeltnis=1.15):
    """Volumen-Drift-Momentum mit Mehrfach-Zeitebenen-Bestaetigung.

    volumen_drift() ist am 08.09.2026 dazugekommen: eigener Nachbau des
    Funktionsprinzips von "Swift Algo X" (TradingView, Invite-Only/Closed-
    Source, Autor swiftalgo) - eine Volumen-Drift-Momentum-Engine kombiniert
    mit einer Mehrfach-Zeitebenen-Bestaetigung. Der Pine-Code ist nirgends
    einsehbar (kein oeffentlicher Quellcode), hier ist nur die auf der
    TradingView-Seite beschriebene Methodik nachgebaut, nicht der Indikator
    kopiert - dasselbe Vorgehen wie bei saisonalitaet().

    Kern: Ueber n Kerzen wird Summe(Schlusskursaenderung * Volumen) durch
    Summe(Volumen) geteilt - eine volumengewichtete mittlere Kursaenderung
    (Grundprinzip wie OBV/Klinger: eine Bewegung zaehlt mehr, wenn viel
    Volumen dahintersteht) - und durch ATR(14) geteilt, damit die Kennzahl
    unabhaengig von Instrument/Volatilitaet vergleichbar bleibt, wie ueberall
    sonst in diesem Modul. Eine Richtung zaehlt nur, wenn zusaetzlich das
    Fenster-Volumen um min_verhaeltnis ueber dem Volumen davor liegt - reine
    Drift ohne Volumen wird herausgefiltert.

    Dieselbe Rechnung laeuft zusaetzlich auf zwei synthetisch verschmolzenen
    Reihen (_serie_verschmelzen, Faktor 2 und 4 = angenaeherte hoehere
    Zeitebenen aus derselben Reihe, ohne weiteren Datenabruf). Stimmen beide
    hoeheren Ebenen nicht im Vorzeichen mit der Basisebene ueberein, bleibt
    richtung 0 - Widerspruch zwischen den Zeitebenen zaehlt als kein Signal,
    nicht als schwaches. stark markiert zusaetzlich einen ungewoehnlich
    kraeftigen Basis-Score (>= 2x min_score).

    Auf Anweisung vom 08.09.2026 wird sie in lage() wie saisonalitaet() HOCH
    gewichtet und darf die Richtung setzen/ueberstimmen - bei Widerspruch der
    beiden hat volumen_drift() Vorrang, weil sie zuletzt geprueft wird.
    """
    leer = {"richtung": 0, "stark": False, "n": len(k),
            "score": None, "score_2x": None, "score_4x": None,
            "volumen_verhaeltnis": None}

    basis_score, basis_verh = _drift_score(k, n)
    if basis_score is None or basis_verh is None:
        return leer

    richtung = 0
    if basis_verh >= min_verhaeltnis:
        if basis_score >= min_score:
            richtung = 1
        elif basis_score <= -min_score:
            richtung = -1

    score_2x = score_4x = None
    if richtung != 0:
        einig = True
        for faktor, feld in ((2, "score_2x"), (4, "score_4x")):
            reihe = _serie_verschmelzen(k, faktor)
            s, _ = _drift_score(reihe, n)
            if faktor == 2:
                score_2x = s
            else:
                score_4x = s
            if s is None or (s > 0) != (richtung == 1):
                einig = False
        if not einig:
            richtung = 0

    return {
        "richtung": richtung,
        "stark": richtung != 0 and abs(basis_score) >= 2 * min_score,
        "n": len(k),
        "score": basis_score,
        "score_2x": score_2x,
        "score_4x": score_4x,
        "volumen_verhaeltnis": basis_verh,
    }


def _cvd_lage(inst, fertig=None):
    """Die CVD-4h-Lage zu diesem Instrument.

    fertig ist der Testweg (ein fertiges Ergebnis wird durchgereicht), inst der
    Produktivweg. Ohne beides wird die Komponente uebersprungen - sie steht
    dann als "kein Instrument im Aufruf" in der Ausgabe, nicht als Richtung.
    """
    if fertig is not None:
        return fertig
    if inst is None:
        return cvd.leer("kein Instrument im Aufruf")
    quelle = cvd_quelle or cvd.cvd_4h
    try:
        return quelle(inst)
    except Exception as e:                                    # noqa: BLE001
        # Ein Ausfall der Quelle darf das Signal nicht umbringen - die
        # Komponente faellt aus, der Rest von lage() bleibt gueltig.
        return cvd.leer("CVD-Lage nicht lesbar: %s" % e)


def signal_bauen(st_richtung, e_auf, e_ab, rsi_jetzt, sais, vol_drift, cv):
    """Das SIGNAL aus den Komponenten - die Rangfolge als eigene Funktion.

    Herausgezogen am 16.09.2026 (T-018), damit derselbe Merge ein zweites Mal
    laufen kann, wenn sich die DATENBASIS einer Komponente aendert: die
    Saisonalitaet darf auf der tiefen Reihe gerechnet werden (lage(k_stat=...)),
    ohne dass die Rangfolge der uebrigen Komponenten im Quelltext doppelt steht.
    Die PruefREIHENFOLGE ist die Rangfolge: Saisonalitaet -> Volumen-Drift ->
    CVD-4h; RSI blockt am Ende nur das Nachlaufen und dreht nichts um.
    """
    if st_richtung == 1 and e_auf:
        signal, grund = "long", "SuperTrend auf, EMA20 ueber EMA50"
    elif st_richtung == -1 and e_ab:
        signal, grund = "short", "SuperTrend ab, EMA20 unter EMA50"
    else:
        signal, grund = "kein", "SuperTrend und EMA widersprechen sich"

    # Saisonalitaet, auf Anweisung vom 01.09.2026 HOCH gewichtet: sie darf die
    # Richtung setzen und auch gegen SuperTrend+EMA kippen. Das weicht bewusst
    # von der sonstigen Trennung der Bausteine ab - deshalb traegt der Grund
    # die Stichprobe (n), und zeige_lage() in bot.py druckt sie mit. Grundlage
    # aus Wissen/Handelsbots.md: kurze Fenster taeuschen; ~7 Kerzen je
    # Wochentag sind kein Backtest, sondern ein Hinweis mit Vorzeichen.
    sr = sais["richtung"]
    if sr != 0:
        srichtung = "long" if sr == 1 else "short"
        marke = "Saisonalitaet %s (Auf-Quote %.0f%%, Mittel %+.2f%%, n=%d)" % (
            sais["wochentag"], sais["quote"] * 100, sais["mittel"] * 100,
            sais["n"])
        if signal == srichtung:
            grund = "%s + %s bestaetigt" % (grund, marke)
        elif signal == "kein":
            signal, grund = srichtung, "%s - SuperTrend/EMA neutral" % marke
        else:
            signal, grund = srichtung, "%s ueberstimmt SuperTrend+EMA" % marke

    # Volumen-Drift-Momentum, auf Anweisung vom 08.09.2026 HOCH gewichtet und
    # zuletzt geprueft: bei Widerspruch zum bisherigen Signal (egal ob Basis
    # oder schon durch Saisonalitaet gesetzt) gewinnt sie. stark markiert
    # einen Score deutlich ueber der Mindestschwelle, siehe volumen_drift().
    vr = vol_drift["richtung"]
    if vr != 0:
        vrichtung = "long" if vr == 1 else "short"
        vmarke = "Volumen-Drift %s (Verhaeltnis %.2fx, Score %+.2f, n=%d)" % (
            "long" if vr == 1 else "short", vol_drift["volumen_verhaeltnis"],
            vol_drift["score"], vol_drift["n"])
        if signal == vrichtung:
            grund = "%s + %s bestaetigt" % (grund, vmarke)
        elif signal == "kein":
            signal, grund = vrichtung, "%s - bisher neutral" % vmarke
        else:
            signal, grund = vrichtung, "%s ueberstimmt (%s)" % (vmarke, grund)

    # CVD-4h-Divergenz, auf Anweisung vom 13.09.2026 HOCH gewichtet und als
    # letzte Komponente geprueft - bei Widerspruch gewinnt sie. Buildix fuehrt
    # genau diese Groesse als Signal-Label (STRONG BUY = Akkumulation am Tief,
    # STRONG SELL = Verteilung am Hoch). Der Grund nennt Richtung, Preis- und
    # CVD-Bewegung und die Zahl der Eimer, damit die Drehung nachpruefbar ist.
    cr = cv["richtung"]
    if cr != 0:
        crichtung = "long" if cr == 1 else "short"
        cmarke = cvd.marke(cv)
        if cv["stark"]:
            cmarke = "STARK " + cmarke
        if signal == crichtung:
            grund = "%s + %s bestaetigt" % (grund, cmarke)
        elif signal == "kein":
            signal, grund = crichtung, "%s - bisher neutral" % cmarke
        else:
            signal, grund = crichtung, "%s ueberstimmt (%s)" % (cmarke, grund)

    # RSI blockt nur das Nachlaufen, er dreht kein Signal um.
    if signal == "long" and rsi_jetzt is not None and rsi_jetzt > 78:
        signal, grund = "kein", "Long-Signal, aber RSI %.0f - ueberkauft" % rsi_jetzt
    if signal == "short" and rsi_jetzt is not None and rsi_jetzt < 22:
        signal, grund = "kein", "Short-Signal, aber RSI %.0f - ueberverkauft" % rsi_jetzt

    return signal, grund


def lage(k, st_n=10, st_faktor=3.0, inst=None, cvd_lage=None,
         k_stat=None):
    """Alle Signalgroessen der letzten Kerze in einem Wortschatz.

    SuperTrend sagt die Richtung, EMA bestaetigt sie, RSI warnt vor dem
    Nachlaufen - diese drei bleiben getrennt, eine Summe wuerde verdecken,
    welcher widerspricht. Ausnahme seit 01.09.2026 auf Anweisung: die
    Saisonalitaet (saisonalitaet(), xGhozt-Prinzip) wird HOCH gewichtet und
    kann das Signal setzen oder gegen SuperTrend+EMA kippen. Der Grund-Text
    nennt dann die Stichprobe, damit sichtbar bleibt, worauf die Drehung steht.

    Zweite Ausnahme seit 08.09.2026 auf Anweisung: volumen_drift() (Swift-
    Algo-X-Prinzip) ist ebenfalls HOCH gewichtet und wird NACH der
    Saisonalitaet geprueft - bei Widerspruch zwischen beiden gewinnt
    volumen_drift(), einfach weil sie als letzte laeuft. Das ist bewusst so
    einfach gehalten statt mit einer Prioritaets-Fallunterscheidung: die
    Pruefreihenfolge IST die Rangfolge.

    Dritte Ausnahme seit 13.09.2026: die CVD-4h-Divergenz (cvd.cvd_4h(),
    Buildix-Prinzip) laeuft als letzte der drei und hat damit den letzten
    Widerspruch. Sie braucht den gehandelten Kontrakt: inst ist der volle
    instId, cvd_lage ein fertiges Ergebnis (Testweg). Fehlt beides, faellt nur
    diese Komponente aus.
    """
    c = [r[4] for r in k]
    a = atr(k, 14)
    linie, richtung = supertrend(k, st_n, st_faktor)
    e20, e50 = ema(c, 20), ema(c, 50)
    r = rsi(c, 14)
    er = effizienz(c, 42)
    # T-018: Die Saisonalitaet ist STATISTIK, nicht Kursstruktur - sie darf auf
    # der tiefen Reihe desselben Basiswerts gerechnet werden (wie Hebel-Deckel
    # und Trefferquote, siehe historie.py). Sonst stehen auf den 300 4h-Kerzen
    # des Kontrakts (~50 Tage) nur ~7 Beobachtungen je Wochentag. Uebernommen
    # wird sie nur, wenn beide Reihen gleichzeitig enden - saisonalitaet() liest
    # Wochentag und Tagesphase der NAECHSTEN Kerze aus dem Ende der Reihe.
    sais_basis = k
    if k_stat is not None and len(k_stat) > len(k) and _gleichzeitig(k, k_stat):
        sais_basis = k_stat
    sais = saisonalitaet(sais_basis)
    vol_drift = volumen_drift(k)
    cv = _cvd_lage(inst, cvd_lage)

    kurs = c[-1]
    st_richtung = richtung[-1]
    e_auf = (e20[-1] is not None and e50[-1] is not None and e20[-1] > e50[-1])
    e_ab = (e20[-1] is not None and e50[-1] is not None and e20[-1] < e50[-1])
    rsi_jetzt = r[-1]

    # Wieviele Kerzen laeuft die aktuelle Richtung schon?
    dauer = 0
    for i in range(len(richtung) - 1, 0, -1):
        if richtung[i] is None or richtung[i] != st_richtung:
            break
        dauer += 1

    signal, grund = signal_bauen(st_richtung, e_auf, e_ab, rsi_jetzt, sais,
                                  vol_drift, cv)

    return {
        "kurs": kurs,
        "atr": a[-1],
        "atr_pct": (a[-1] / kurs) if a[-1] else None,
        "st_linie": linie[-1],
        "st_richtung": st_richtung,
        "st_dauer": dauer,
        "ema20": e20[-1], "ema50": e50[-1],
        "rsi": rsi_jetzt,
        "er": er,
        "sais": sais,
        "sais_tief": sais_basis is not k,
        "sais_kerzen": len(sais_basis),
        "vol_drift": vol_drift,
        "cvd": cv,
        "signal": signal,
        "grund": grund,
    }
