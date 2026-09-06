"""Walk-Forward-Backtest fuer den Marktscanner.

Teil 1: merkmals_matrix() rechnet die neun ungewichteten Bausteine je (Wert,
Tag) EINMAL vor. Danach kostet das Bewerten eines Kandidaten nur noch
Gewichtung und Tore - die Gewichtssuche wird fast kostenlos.

Teil 2: simuliere() spielt einen Kandidaten ueber ein Fenster durch und bildet
dabei den Ein-/Ausstieg aus scanner/handeln.py exakt nach - Ausstiege vor
Einstiegen, Stop am Tagestief vor Ziel am Tageshoch, Abklingzeit nach Stop,
Deckel fuer offene Positionen und gebundenes Kapital. Gebuehr je Seite aus
kosten.GEBUEHR_PCT, Ausfuehrung konservativ zum Triggerpreis.
"""

import bewertung
import kosten

MINDEST_KERZEN = 120

# Eine Gebuehrenzahl fuer Backtest und Angleichung - identisch mit
# scanner/handeln.py (test_kosten_gleich.py bindet kosten an handeln).
GEBUEHR_PCT = kosten.GEBUEHR_PCT


def merkmals_matrix(kerzen_je_inst):
    aus = {}
    for inst, kerzen in kerzen_je_inst.items():
        reihe = {}
        for t in range(MINDEST_KERZEN, len(kerzen)):
            reihe[t] = bewertung.roh_komponenten(kerzen[: t + 1])
        aus[inst] = reihe
    return aus


# --- Kandidaten-Simulation (TP2 Teil 2) ----------------------------------

def stop_prozent(vola_pa, stop_min, stop_max):
    """Stop-Abstand aus Volatilitaet, hart gedeckelt - wie handeln.stop_prozent:
    3 % ruhig, ~12 % wild, auf eine Stelle gerundet und in [stop_min, stop_max]."""
    roh = 3.0 + 6.0 * min(vola_pa, 1.5)
    return max(stop_min, min(stop_max, round(roh, 1)))


def _score(roh, gewichte):
    """Score und Chance/Risiko-Verhaeltnis aus den Rohbausteinen - derselbe
    Rechenweg wie bewertung.bewerten(), nur ungerundet und ohne Huelle."""
    cg = (gewichte or {}).get("chance") or bewertung.CHANCE_GEWICHTE
    rg = (gewichte or {}).get("risiko") or bewertung.RISIKO_GEWICHTE
    chance = 100.0 * sum(cg[k] * roh["c_" + k] for k in cg)
    risiko = 100.0 * sum(rg[k] * roh["r_" + k] for k in rg)
    score = max(0.0, min(100.0, chance * (1.0 - 0.7 * risiko / 100.0)))
    return score, chance / max(risiko, 1.0)


def _sizing(art, score, vola, max_pro_trade_usd):
    """Positionsgroesse je Sizing-Regel, auf zwei Stellen gerundet."""
    if art == "score-linear":
        f = max(0.4, min(1.0, score / 100.0))
    elif art == "vola-invers":
        f = max(0.4, min(1.0, 0.8 / max(vola, 0.4)))
    else:  # "flach"
        f = 1.0
    return round(max_pro_trade_usd * f, 2)


def simuliere(matrix, kerzen_je_inst, kandidat, start_tag, end_tag):
    """Geschlossene Runden im Fenster [start_tag, end_tag).

    Bildet handeln.py nach: je Tag zuerst pruefe_ausstiege (Stop am Tagestief
    schlaegt Ziel am Tageshoch), dann pruefe_einstiege (Abklingzeit nach Stop,
    Deckel fuer offene Positionen und gebundenes Kapital). Ausfuehrung zum
    Triggerpreis - konservativ und eindeutig. gv ist netto nach GEBUEHR_PCT je
    Seite. Am end_tag noch offene Positionen zaehlen nicht.
    """
    g = kandidat["gates"]
    gewichte = kandidat.get("gewichte")
    sizing = kandidat.get("sizing", "flach")
    watchlist = kandidat["watchlist"]

    frei_ab = {}          # inst -> erster Tag, an dem wieder eingestiegen werden darf
    offen = []            # {inst, einstieg_kurs, stop, ziel, einsatz, einstieg_tag,
                          #  score, vola_pa, verhaeltnis}
    runden = []

    for t in range(start_tag, end_tag):
        # 1) Ausstiege zuerst - genau wie handeln.pruefe_ausstiege.
        behalten = []
        for p in offen:
            kerze = kerzen_je_inst[p["inst"]][t]
            hoch, tief = kerze[2], kerze[3]
            if tief <= p["stop"]:
                grund, trigger = "stop", p["stop"]
                frei_ab[p["inst"]] = t + g["abklingzeit_tage"]
            elif hoch >= p["ziel"]:
                grund, trigger = "ziel", p["ziel"]
            else:
                behalten.append(p)
                continue
            erloes = p["einsatz"] * trigger / p["einstieg_kurs"] * (1.0 - GEBUEHR_PCT)
            einsatz_mit_gebuehr = p["einsatz"] * (1.0 + GEBUEHR_PCT)
            runden.append({
                "inst": p["inst"],
                "einstieg_tag": p["einstieg_tag"],
                "ausstieg_tag": t,
                "einstieg_kurs": p["einstieg_kurs"],
                "ausstieg_kurs": trigger,
                "einsatz": p["einsatz"],
                "erloes": erloes,
                "gv": erloes - einsatz_mit_gebuehr,
                "grund": grund,
                "score": p["score"],
                "vola_pa": p["vola_pa"],
                "verhaeltnis": p["verhaeltnis"],
            })
        offen = behalten

        # 2) Einstiege nach den Ausstiegen - wie handeln.pruefe_einstiege.
        # Erst alle Anwaerter sammeln, die durch alle Tore kommen, dann nach
        # Score absteigend abarbeiten - wie der Livepfad: scan.py sortiert den
        # Bericht key=score, reverse=True, vorschlaege() haelt die Reihenfolge,
        # pruefe_einstiege() fuellt in dieser Reihenfolge. So oeffnet auch der
        # Backtest die hoechstbewerteten Kandidaten zuerst, wenn ein Deckel
        # bindet - nicht nach Watchlist-Reihenfolge.
        gehalten = {p["inst"] for p in offen}
        eingesetzt = sum(p["einsatz"] for p in offen)
        anwaerter = []
        for inst in watchlist:
            reihe = matrix.get(inst)
            if not reihe or t not in reihe:
                continue
            if inst in gehalten or t < frei_ab.get(inst, start_tag):
                continue
            roh = reihe[t]
            score, verh = _score(roh, gewichte)
            vola = roh["vola_pa"]
            if not (score >= g["mindest_score"]
                    and vola <= g["max_volatilitaet_pa"]
                    and verh >= g["mindest_chance_risiko"]):
                continue
            anwaerter.append((score, verh, vola, inst))
        # Stabiler Sort: gleiche Scores behalten die Watchlist-Reihenfolge -
        # deckt sich mit CPythons stabilem Sort in scan.py.
        anwaerter.sort(key=lambda a: a[0], reverse=True)
        for score, verh, vola, inst in anwaerter:
            if len(offen) >= g["max_offene_positionen"]:
                break
            einsatz = _sizing(sizing, score, vola, g["max_pro_trade_usd"])
            if eingesetzt + einsatz > g["max_gesamt_usd"]:
                continue
            sp = stop_prozent(vola, g["stop_min"], g["stop_max"])
            einstieg_kurs = kerzen_je_inst[inst][t][4]
            stop = round(einstieg_kurs * (1.0 - sp / 100.0), 6)
            ziel = round(einstieg_kurs + 2.0 * (einstieg_kurs - stop), 6)
            offen.append({
                "inst": inst,
                "einstieg_kurs": einstieg_kurs,
                "stop": stop,
                "ziel": ziel,
                "einsatz": einsatz,
                "einstieg_tag": t,
                "score": score,
                "vola_pa": vola,
                "verhaeltnis": verh,
            })
            eingesetzt += einsatz

    return runden


# --- Kennzahlen und Walk-Forward-Aggregation (TP2 Teil 3) ---------------

def kennzahlen(runden):
    """Kennzahlen einer Menge geschlossener Runden.

    n == 0 -> jede Zahl 0, jede Quote/None-Feld None, kein ZeroDivision.
    max_drawdown auf der kumulierten gv-Kurve, sortiert nach einstieg_tag:
    groesster Abstand vom bisherigen Hoch zum aktuellen Stand.
    noetige_trefferquote = mittlerer Verlustbetrag / (mittlerer Gewinn +
    mittlerer Verlustbetrag) - der Break-even bei diesem Chance/Risiko.
    Fehlt eine Seite (nur Gewinne oder nur Verluste), ist sie None.
    Spur 1 ist Spot: liquidationsabstand und funding_pct sind None.
    """
    n = len(runden)
    gebuehr_runde_pct = 2 * GEBUEHR_PCT
    if n == 0:
        return {
            "n": 0,
            "netto_gv_je_runde": 0,
            "trefferquote": None,
            "summe_gv": 0,
            "max_drawdown": 0.0,
            "gebuehr_runde_pct": gebuehr_runde_pct,
            "noetige_trefferquote": None,
            "beobachtete_trefferquote": None,
            "liquidationsabstand": None,
            "funding_pct": None,
        }

    gvs = [r["gv"] for r in runden]
    summe_gv = sum(gvs)
    treffer = sum(1 for x in gvs if x > 0)
    trefferquote = treffer / n

    gewinne = [x for x in gvs if x > 0]
    verluste = [abs(x) for x in gvs if x < 0]
    if gewinne and verluste:
        mittl_gewinn = sum(gewinne) / len(gewinne)
        mittl_verlust = sum(verluste) / len(verluste)
        noetige_trefferquote = mittl_verlust / (mittl_gewinn + mittl_verlust)
    else:
        noetige_trefferquote = None

    # Kumulierte gv-Kurve in zeitlicher Reihenfolge - groesster Ruecksetzer.
    stand = 0.0
    hoch = 0.0
    max_drawdown = 0.0
    for r in sorted(runden, key=lambda x: x["einstieg_tag"]):
        stand += r["gv"]
        hoch = max(hoch, stand)
        max_drawdown = max(max_drawdown, hoch - stand)

    return {
        "n": n,
        "netto_gv_je_runde": summe_gv / n,
        "trefferquote": trefferquote,
        "summe_gv": summe_gv,
        "max_drawdown": max_drawdown,
        "gebuehr_runde_pct": gebuehr_runde_pct,
        "noetige_trefferquote": noetige_trefferquote,
        "beobachtete_trefferquote": trefferquote,
        "liquidationsabstand": None,
        "funding_pct": None,
    }


def walk_forward(kerzen_je_inst, kandidat, konfig):
    """Rollende OOS-Fenster: je Fenster nur den Testabschnitt simulieren,
    danach alle OOS-Runden zusammen auswerten.

    Fenster: Start bei oos_training_tage, Testlaenge oos_test_tage, Vorruecken
    um oos_schritt_tage, solange das Testfenster noch in die Historie passt.
    Die Merkmals-Matrix wird einmal berechnet und in jedem Fenster genutzt.
    """
    laenge = min(len(k) for k in kerzen_je_inst.values())
    matrix = merkmals_matrix(kerzen_je_inst)

    fenster = []
    alle_runden = []
    start = konfig["oos_training_tage"]
    while start + konfig["oos_test_tage"] <= laenge:
        bis = start + konfig["oos_test_tage"]
        runden = simuliere(matrix, kerzen_je_inst, kandidat, start, bis)
        fenster.append({
            "von_tag": start,
            "bis_tag": bis,
            "kennzahlen": kennzahlen(runden),
        })
        alle_runden.extend(runden)
        start += konfig["oos_schritt_tage"]

    return {
        "fenster": fenster,
        "gesamt": kennzahlen(alle_runden),
        "fenster_anzahl": len(fenster),
    }
