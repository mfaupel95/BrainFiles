"""Backtest der vierten Spur: Opening Range Breakout ueber DE30/US30/NAS100.

Diese Datei prueft die "81 %"-Behauptung (SPEC.md, Anlass). Sie handelt nichts.
Regeln exakt nach SPEC.md, Abschnitt "Die Strategie, exakt".

Mehrdeutigkeit: M15 loest nicht auf, ob Hoch oder Tief zuerst kam. Beruehrt
eine Kerze Stop UND Ziel, zaehlt sie als Stop (konservativ, "am Tief pruefen,
nicht am Schluss").
"""

import session as sess


def sessions_gruppieren(kerzen, inst_konf):
    aus = {}
    for k in kerzen:
        tag = sess.handelstag(k["zeit"], inst_konf["zone"])
        eroeff, _ = sess.opening_range_fenster(inst_konf, tag)
        schluss = sess.zwangsschluss(inst_konf, tag)
        if eroeff <= k["zeit"] < schluss:
            aus.setdefault(tag, []).append(k)
    return [(t, sorted(aus[t], key=lambda x: x["zeit"])) for t in sorted(aus)]


def opening_range(session_kerzen, inst_konf, tag):
    start, ende = sess.opening_range_fenster(inst_konf, tag)
    im_fenster = [k for k in session_kerzen if start <= k["zeit"] < ende]
    if len(im_fenster) < 2:
        return None
    zwei = im_fenster[:2]
    return max(k["h"] for k in zwei), min(k["l"] for k in zwei)


def _inst_schluessel(inst_konf, w):
    for name, konf in w["instrumente"].items():
        if konf is inst_konf or konf == inst_konf:
            return name
    return next(iter(w["instrumente"]))


def simuliere_session(session_kerzen, inst_konf, tag, w, einstiegsmodell):
    key = _inst_schluessel(inst_konf, w)
    hr = opening_range(session_kerzen, inst_konf, tag)
    if hr is None:
        return None
    hoch, tief = hr
    range_hoehe = hoch - tief
    if range_hoehe < w["mindest_range_punkte"][key] or range_hoehe > w["max_range_punkte"][key]:
        return None

    _, range_ende = sess.opening_range_fenster(inst_konf, tag)
    letzt = sess.letzter_einstieg(inst_konf, tag, w["letzter_einstieg_min_vor_schluss"])
    nach_range = [k for k in session_kerzen if k["zeit"] >= range_ende]

    einstieg_kerze = None
    richtung = None
    for i, k in enumerate(nach_range):
        if k["zeit"] > letzt:
            break
        if k["c"] > hoch:
            einstieg_kerze, richtung, rest = k, "long", nach_range[i + 1:]
            break
        if k["c"] < tief:
            einstieg_kerze, richtung, rest = k, "short", nach_range[i + 1:]
            break
    if einstieg_kerze is None:
        return None

    # Nur Kerzen pruefen, durch die die Position tatsaechlich gehalten wurde:
    #   schluss            -> Einstieg = Schluss der Ausbruchskerze, gehalten ab
    #                         der NAECHSTEN Kerze (H/L der Ausbruchskerze lagen
    #                         vor dem Einstieg) -> pruef_kerzen = rest
    #   naechste_eroeffnung -> Einstieg = Open der Fuellkerze (rest[0]), diese
    #                         Kerze wird voll gehalten -> pruef_kerzen ab rest[0]
    if einstiegsmodell == "schluss":
        einstieg = einstieg_kerze["c"]
        pruef_kerzen = list(rest)
    else:  # naechste_eroeffnung
        if not rest:
            return None
        einstieg = rest[0]["o"]
        pruef_kerzen = list(rest)

    if richtung == "long":
        stop = tief
        ziel = einstieg + (w["ziel_k"] * range_hoehe if w["ziel_modus"] == "r_vielfaches"
                           else w["ziel_punkte"][key])
    else:
        stop = hoch
        ziel = einstieg - (w["ziel_k"] * range_hoehe if w["ziel_modus"] == "r_vielfaches"
                           else w["ziel_punkte"][key])

    ausgang, ausstieg, mehrdeutig = "zwangsschluss", None, False
    for k in pruef_kerzen:
        if richtung == "long":
            stop_beruehrt = k["l"] <= stop
            ziel_beruehrt = k["h"] >= ziel
        else:
            stop_beruehrt = k["h"] >= stop
            ziel_beruehrt = k["l"] <= ziel
        if stop_beruehrt and ziel_beruehrt:
            ausgang, ausstieg, mehrdeutig = "stop", stop, True
            break
        if stop_beruehrt:
            ausgang, ausstieg = "stop", stop
            break
        if ziel_beruehrt:
            ausgang, ausstieg = "ziel", ziel
            break
    if ausstieg is None:
        ausstieg = pruef_kerzen[-1]["c"] if pruef_kerzen else einstieg

    gv = (ausstieg - einstieg) if richtung == "long" else (einstieg - ausstieg)
    return {"tag": tag, "inst": key, "richtung": richtung, "einstieg": einstieg,
            "stop": stop, "ziel": ziel, "ausgang": ausgang, "ausstieg": ausstieg,
            "range_punkte": range_hoehe, "mehrdeutig": mehrdeutig,
            "gv_punkte": gv}
