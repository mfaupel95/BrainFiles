"""Fibonacci-Retracements fuer Stop und Ziel - reine Rechnung.

AUFTRAG (Max, 08.10.2026): Ein- und Ausstiege nach Fibonacci-Retracements
organisieren statt nach festen Prozenten. Stufe A (diese Datei): Fib bestimmt
STOP und ZIELE, die bestehenden Signale bleiben. Stufe B (Einstieg per
Limit-Order in der Pullback-Zone) kommt erst nach dem Backtest von Stufe A.

HYPOTHESE, KEIN FAKT: Die Level 0,382 / 0,5 / 0,618 / 0,786 sind als Marker
dokumentiert, an denen viele Marktteilnehmer Orders platzieren. Eine
belegte Ueberlegenheit gegenueber ATR-Stops gibt es nicht. Ob Fib hier besser
ist als der Ist-Stand, entscheidet allein der Backtest gegen die Grundlinie
(bt_oos.py, Raster ueber Nachbarn, Stichprobe halbieren, Seiten trennen).
Diese Datei schaltet deshalb nichts um: sie rechnet, handelt nicht, liest
keine wachen.json und hat kein Netz.

DER VERSTECKTE PARAMETER ist die Swing-Definition (`links`/`rechts` der
Pivots, `min_hub_pct`). Er gehoert in jedes Raster - wer ihn einmal waehlt
und dann Fib "validiert", hat den Parameter optimiert, nicht Fib gemessen.

PFLICHT-STOP-RAHMEN: Liegt der Fib-Stop ausserhalb von
`stop_min_pct`..`stop_max_pct`, wird der Trade ABGELEHNT, nicht geklemmt. Ein
geklemmter Stop hat die Fib-Geometrie verloren, und der Backtest misst dann
etwas anderes als der Name sagt.

KEIN BLICK NACH VORN: Ein Pivot gilt erst, wenn `rechts` Kerzen danach
vorliegen (wie klassik_regeln.pivot_hoch_tief). Die laufende, nicht
abgeschlossene Kerze gehoert nicht in `k` - das stellt der Aufrufer sicher.

Kerzen: [ts, open, high, low, close, volume]. Seite: "long" | "short".
"""

from __future__ import annotations

RETRACEMENTS = (0.382, 0.5, 0.618, 0.786)
ERWEITERUNGEN = (1.0, 1.272, 1.618)


def pivots(k, links=5, rechts=5):
    """Bestaetigte Pivots, zeitlich geordnet, abwechselnd Hoch/Tief.

    Rueckgabe: Liste (index, preis, "H"|"L"). Gleichstand zaehlt nicht als
    Pivot (streng hoeher/tiefer wie Pine). Eine Kerze, die zugleich
    Pivot-Hoch und -Tief waere (Aussenkerze), ist mehrdeutig und wird
    uebersprungen. Folgen zwei Pivots gleicher Art, bleibt der extremere.
    """
    n = len(k)
    roh = []
    for j in range(links, n - rechts):
        fenster = range(j - links, j + rechts + 1)
        h, l = float(k[j][2]), float(k[j][3])
        ist_h = h > max(float(k[m][2]) for m in fenster if m != j)
        ist_l = l < min(float(k[m][3]) for m in fenster if m != j)
        if ist_h == ist_l:                      # keiner oder beide
            continue
        roh.append((j, h, "H") if ist_h else (j, l, "L"))

    out = []
    for p in roh:
        if out and out[-1][2] == p[2]:
            if (p[2] == "H" and p[1] > out[-1][1]) or (p[2] == "L" and p[1] < out[-1][1]):
                out[-1] = p
            continue
        out.append(p)
    return out


def swing(k, seite, links=5, rechts=5, min_hub_pct=1.0):
    """Das Bein, in dessen Ruecksetzer eingestiegen wird - oder None.

    long : letztes Tief -> darauffolgendes Hoch (Aufwaertsbein), Einstieg im
           Ruecksetzer nach unten.
    short: letztes Hoch -> darauffolgendes Tief, Einstieg im Ruecksetzer nach oben.

    Das Hoch (Tief) des Beins ist der Extremwert SEIT dem Pivot - laeuft der
    Trend weiter, wandert das Ende mit, auch wenn der neue Pivot noch nicht
    bestaetigt ist. Ist der Ursprung des Beins seither unterschritten
    (ueberschritten), gibt es kein Bein mehr.
    """
    if seite not in ("long", "short"):
        raise ValueError("seite muss 'long' oder 'short' sein: %r" % (seite,))
    pv = pivots(k, links, rechts)
    if len(pv) < 2:
        return None
    (i0, p0, t0), (i1, p1, t1) = pv[-2], pv[-1]

    if seite == "long":
        if (t0, t1) != ("L", "H"):
            return None
        tief = p0
        hoch = max(float(z[2]) for z in k[i1:])
        if min(float(z[3]) for z in k[i1:]) < tief:
            return None
        hub = hoch - tief
        ref = tief
    else:
        if (t0, t1) != ("H", "L"):
            return None
        hoch = p0
        tief = min(float(z[3]) for z in k[i1:])
        if max(float(z[2]) for z in k[i1:]) > hoch:
            return None
        hub = hoch - tief
        ref = hoch

    if ref <= 0 or hub <= 0 or hub / ref * 100.0 < min_hub_pct:
        return None
    return {"seite": seite, "tief": tief, "hoch": hoch,
            "ursprung_i": i0, "ende_i": i1}


def retracement_preis(sw, quote):
    """Preis, an dem das Bein zu `quote` (0..1) zurueckgelaufen ist."""
    hub = sw["hoch"] - sw["tief"]
    if sw["seite"] == "long":
        return sw["hoch"] - quote * hub
    return sw["tief"] + quote * hub


def tiefe(sw, kurs):
    """Wie weit der Kurs schon zurueckgelaufen ist (0 = am Extrem, 1 = am Ursprung)."""
    hub = sw["hoch"] - sw["tief"]
    if sw["seite"] == "long":
        return (sw["hoch"] - kurs) / hub
    return (kurs - sw["tief"]) / hub


def ziel_preis(sw, erweiterung):
    """Erweiterung des Beins, gemessen vom Ursprung (1,0 = altes Extrem)."""
    hub = sw["hoch"] - sw["tief"]
    if sw["seite"] == "long":
        return sw["tief"] + erweiterung * hub
    return sw["hoch"] - erweiterung * hub


def plan(k, seite, kurs, links=5, rechts=5, min_hub_pct=1.0,
         zone=(0.5, 0.618), zone_pflicht=False,
         stop_art="ursprung", stop_puffer_pct=0.1,
         ziel_erweiterungen=ERWEITERUNGEN,
         stop_min_pct=None, stop_max_pct=None, min_r=1.0):
    """Stop und Ziele fuer einen Einstieg zu `kurs`.

    Rueckgabe immer ein dict mit `ok`. Bei `ok=False` steht der Grund in
    `grund`, kein Wert wird geklemmt oder ersetzt.

    stop_art "ursprung": hinter dem Ursprung des Beins (100 %).
    stop_art "786"     : hinter dem 78,6-%-Level (enger, mehr Fehlausloesungen).
    stop_puffer_pct    : zusaetzlicher Abstand hinter dem Level, in % des Preises.
    zone_pflicht       : True -> nur im Ruecksetzer-Fenster `zone` (Stufe-B-Vorstufe);
                         False (Stufe A) -> die Zonenlage wird nur gemeldet.
    min_r              : erstes Ziel muss mindestens so viele Stop-Abstaende weit sein.
    """
    if stop_art not in ("ursprung", "786"):
        raise ValueError("stop_art: 'ursprung' oder '786', nicht %r" % (stop_art,))
    sw = swing(k, seite, links, rechts, min_hub_pct)
    if sw is None:
        return {"ok": False, "grund": "kein Bein"}

    tf = tiefe(sw, kurs)
    in_zone = zone[0] <= tf <= zone[1]
    if tf < 0 or tf >= 1:
        return {"ok": False, "grund": "Kurs ausserhalb des Beins (Tiefe %.2f)" % tf,
                "swing": sw, "tiefe": tf}
    if zone_pflicht and not in_zone:
        return {"ok": False, "grund": "ausserhalb der Zone (Tiefe %.2f)" % tf,
                "swing": sw, "tiefe": tf, "in_zone": False}

    if stop_art == "ursprung":
        basis = sw["tief"] if seite == "long" else sw["hoch"]
    else:
        basis = retracement_preis(sw, 0.786)
    puffer = basis * stop_puffer_pct / 100.0
    stop = basis - puffer if seite == "long" else basis + puffer

    abstand = abs(kurs - stop)
    if abstand <= 0 or (seite == "long" and stop >= kurs) or (seite == "short" and stop <= kurs):
        return {"ok": False, "grund": "Stop liegt nicht hinter dem Kurs",
                "swing": sw, "tiefe": tf}
    stop_pct = abstand / kurs * 100.0
    if stop_min_pct is not None and stop_pct < stop_min_pct:
        return {"ok": False, "grund": "Stop %.2f %% unter Rahmen %.2f %%" % (stop_pct, stop_min_pct),
                "swing": sw, "tiefe": tf, "stop": stop, "stop_pct": stop_pct}
    if stop_max_pct is not None and stop_pct > stop_max_pct:
        return {"ok": False, "grund": "Stop %.2f %% ueber Rahmen %.2f %%" % (stop_pct, stop_max_pct),
                "swing": sw, "tiefe": tf, "stop": stop, "stop_pct": stop_pct}

    ziele = []
    for e in ziel_erweiterungen:
        z = ziel_preis(sw, e)
        if (z > kurs) if seite == "long" else (z < kurs):
            ziele.append({"erweiterung": e, "preis": z,
                          "r": abs(z - kurs) / abstand})
    if not ziele:
        return {"ok": False, "grund": "kein Ziel jenseits des Kurses",
                "swing": sw, "tiefe": tf, "stop": stop, "stop_pct": stop_pct}
    if ziele[0]["r"] < min_r:
        return {"ok": False, "grund": "erstes Ziel nur %.2f R (min %.2f)" % (ziele[0]["r"], min_r),
                "swing": sw, "tiefe": tf, "stop": stop, "stop_pct": stop_pct,
                "ziele": ziele}

    return {"ok": True, "grund": "", "swing": sw, "tiefe": tf, "in_zone": in_zone,
            "stop": stop, "stop_pct": stop_pct, "ziele": ziele}
