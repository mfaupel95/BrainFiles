"""Alt-Breite: Anteil der Top-Paare ueber ihrer EMA200 (Tageskerzen).

WOFUER
------
Ein einzelner Messpunkt sagt nichts ueber die Richtung. Dieses Werkzeug misst,
fuehrt eine REIHE (`--merken`) und kann die Reihe RUECKWAERTS nachrechnen
(`--fuellen`) - damit "die Breite schrumpft" eine Zahl mit Stichprobe ist
statt einer Behauptung mit einem Punkt.

Die Reihe fuehrt EINE ZEILE JE KERZENTAG (siehe `merken`) - mehrere Messungen
desselben Tages ersetzen einander. `--reihe` zeigt den VERLAUF mit der
Veraenderung in Punkten je Tag, `--statistik` die Verteilung und die Frage,
was auf eine hohe Breite folgte.

LUECKEN: fehlt ein Kalendertag zwischen der aeltesten und der neuesten Zeile,
war der Rechner aus - die Reihe hat dann ein Loch, das nur auffaellt, wenn
jemand sie liest. `--reihe` nennt die Luecken deshalb ausdruecklich
(`fehlende_tage`/`luecken_text`), und `breite-wache.py` heilt sie taeglich
nach: die Heiltiefe richtet sich nach der Ausfalllaenge, nicht nach einer
festen Zahl von Tagen.

FENSTER (geaendert 30.09.2026)
------------------------------
Gerechnet wird auf den letzten FENSTER **abgeschlossenen** Kerzen bis
einschliesslich des Kerzentags. Vorher war das Fenster "was OKX in EINEM Aufruf
zurueckgibt" (300 Zeilen minus die laufende Kerze = 299) - eine Zahl, die davon
abhing, ob gerade eine Kerze offen ist. Der Startwert der EMA (SMA der ersten
200) hat im laufenden Mittelwert ein Gewicht von (1-k)^Schritte; bei 299 Kerzen
sind das noch ~37 %, bei 600 nur ~2 %. Das Fenster ist seither FEST und fuer
Live-Lauf und Nachrechnung DASSELBE.

WOHER
-----
Oeffentliche OKX-Tageskerzen (`/api/v5/market/candles`, geblaettert mit
`after`), nur Standardbibliothek, kein Schluessel, keine Kosten. Der EEA-Host
ist der Haushost; faellt er aus, wird www.okx.com probiert.

Zeitbezug: gerechnet wird auf der letzten GESCHLOSSENEN Tageskerze, nicht auf
dem laufenden Kurs. Die Kerze steht in der Ausgabe. OKX-Tageskerzen beginnen
16:00 UTC (00:00 UTC+8) - die Kerze wechselt also um 16:00 UTC.

FALLE (gemessen 25.09.2026)
---------------------------
OKX beantwortet `urllib` ohne User-Agent mit HTTP 403. Ohne den Kopf liefern
ALLE Paare einen Fehler und die Breite waere "0 von 0" - eine glatte
Falschaussage. Darum nennt die Ausgabe immer die Deckung: wie viele Paare
gemessen wurden und welche nicht.

AUFRUF (aus Agenten/Handel heraus: ..\\Werkzeuge\\breite.py)
    python breite.py                    # messen und zeigen (schreibt nichts)
    python breite.py --merken           # messen und in die Reihe schreiben
    python breite.py --reihe            # Verlauf je Kerzentag
    python breite.py --fuellen          # die letzten 250 Kerzentage nachrechnen
    python breite.py --statistik        # Verteilung + was auf hohe Breite folgte
    python breite.py --json             # Maschinenform fuer die Wache
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

REIHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "breite-reihe.jsonl")

# TON-USDT am 21.10.2026 ENTFERNT: auf dem EEA-Host delistet (51001 fuer
# TON-USDT UND TON-USDC, Lebendprobe SEI-USDT = code 0). Ersatz bewusst
# NICHT aufgenommen - die Reihe ist seit 2026-01-22 durchgehend ein
# 29-Paar-Korb (n_gesamt 28/29, TON war nie mitgezaehlt); ein 30. Paar
# waere eine Zusammensetzungsaenderung MITTEN in der Reihe. Geprueft mit
# voller Historie (>=871 Tageskerzen): HBAR, ICP, AAVE, CRV, WLD - zu kurz:
# ONDO (814), ENA (399), TAO (113).

PAARE = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "BNB-USDT",
    "DOGE-USDT", "ADA-USDT", "LINK-USDT", "AVAX-USDT",
    "DOT-USDT", "POL-USDT", "LTC-USDT", "TRX-USDT", "SHIB-USDT",
    "ATOM-USDT", "UNI-USDT", "NEAR-USDT", "APT-USDT", "ARB-USDT",
    "OP-USDT", "FIL-USDT", "INJ-USDT", "SUI-USDT", "SEI-USDT",
    "TIA-USDT", "PEPE-USDT", "ETC-USDT", "XLM-USDT", "ALGO-USDT",
]

import os as _os
import sys as _sys
_HANDEL = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "Handel")
if _HANDEL not in _sys.path:
    _sys.path.append(_HANDEL)
import okx_takt  # noqa: E402
# Haus-Bremse gegen OKX-Drosselung (Agenten/Handel/okx_takt.py): sie ist
# prozessuebergreifend, damit Wache, Zentrale und Dauerlauf-Stufen sich nicht
# gegenseitig die IP-Zuteilung leeren (gemessen 05.10.2026: 6 Threads ->
# 93x 50011, nacheinander 120 Abrufe -> 0 Fehler).

BASEN = ("https://eea.okx.com", "https://www.okx.com")
LAENGE = 200                                  # EMA-Laenge
FENSTER = 600                                 # Kerzen je Messung (fest, s. Kopf)
SEITE = 300                                   # OKX gibt je Aufruf hoechstens 300
NACHRECHNEN_TAGE = 250                        # Vorgabe fuer --fuellen
VERLAUF_MIT = 10                              # Zusatzkerzen fuer `mit_verlauf`


def _anfrage(url):
    """OKX blockt den urllib-Standardkopf mit HTTP 403 - Kopf mitgeben."""
    return urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) marktdaten",
        "Accept": "application/json",
    })


def _seite(inst, basis, after=None):
    """Eine Rohseite Tageskerzen, neueste zuerst."""
    url = ("%s/api/v5/market/candles?instId=%s&bar=1D&limit=%d"
           % (basis, inst, SEITE))
    if after:
        url += "&after=%s" % after            # aelter als dieser Zeitstempel
    okx_takt.reserviere()
    with urllib.request.urlopen(_anfrage(url), timeout=20) as a:
        daten = json.loads(a.read().decode("utf-8"))
    if daten.get("code") != "0":
        raise RuntimeError("OKX %s: %s" % (daten.get("code"), daten.get("msg")))
    return daten.get("data") or []


def kerzen_verlauf(inst, basis, anzahl, bestaetigt=True):
    """Abgeschlossene Tageskerzen, aelteste zuerst: [(ts_ms, schluss), ...].

    Blaettert mit `after` nach, bis `anzahl` Kerzen da sind (OKX liefert je
    Aufruf hoechstens 300). Mehr als noetig wird abgeschnitten.
    """
    roh = {}
    after = None
    for _ in range(12):                        # Deckel: 12 x 300 Kerzen
        seite = _seite(inst, basis, after)
        if not seite:
            break
        for r in seite:
            if bestaetigt and r[8] != "1":
                continue                       # laufende Kerze nie mitrechnen
            roh[int(r[0])] = float(r[4])
        if len(roh) >= anzahl:
            break
        after = min(roh)
        time.sleep(0.05)
    if not roh:
        raise RuntimeError("keine abgeschlossene Kerze")
    raus = sorted(roh.items())
    return raus[-anzahl:] if anzahl else raus


def kerzen(inst, basis, limit=300):
    """Wie frueher: Schluesse der abgeschlossenen Tageskerzen + letzter ts."""
    verlauf = kerzen_verlauf(inst, basis, limit)
    return [s for _, s in verlauf], verlauf[-1][0]


def ema(werte, n=LAENGE):
    """Exponentieller Mittelwert, Start = einfacher Mittel der ersten n."""
    if len(werte) < n:
        return None
    k = 2.0 / (n + 1)
    e = sum(werte[:n]) / n
    for x in werte[n:]:
        e = x * k + e * (1 - k)
    return e


def kerzentag(ts_ms):
    """Kerzentag als YYYY-MM-DD (UTC) - der Schluessel der Reihe."""
    return datetime.fromtimestamp(ts_ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def fenster_von(reihe, i, fenster=FENSTER):
    """Die letzten `fenster` Schluesse bis einschliesslich Index i.

    Ist die Geschichte kuerzer, wird genommen was da ist (mindestens LAENGE).
    Rueckgabe: Liste oder None, wenn selbst das nicht reicht.
    """
    if i is None or i < 0 or i >= len(reihe):
        return None
    anfang = max(0, i + 1 - fenster)
    schluesse = [s for _, s in reihe[anfang:i + 1]]
    return schluesse if len(schluesse) >= LAENGE else None


def _messe_fenster(schluesse):
    """(kurs, ema, abstand) aus den Schluessen EINES Fensters."""
    e = ema(schluesse)
    if e is None:
        return None
    kurs = schluesse[-1]
    return kurs, e, (kurs / e - 1.0) * 100.0


def hole(inst, anzahl=None):
    """Kerzenverlauf eines Paares, erster erreichbarer Host gewinnt."""
    fehler = []
    for basis in BASEN:
        try:
            return kerzen_verlauf(inst, basis, anzahl or FENSTER)
        except Exception as f:                 # noqa: BLE001
            fehler.append("%s@%s" % (f, basis.split("//")[1]))
        time.sleep(0.1)
    raise RuntimeError("; ".join(fehler))


def messen(paare=None, still=False, mit_verlauf=False):
    """Misst die Breite. Rueckgabe: dict (Maschinenform).

    Mit `mit_verlauf=True` kommen die geholten Kerzenverlaeufe unter dem
    Schluessel `_verlauf` mit (je Paar ein Verlauf, etwas mehr Kerzen als das
    Fenster). Dann kann `fuellen` DIESELBEN Kerzen benutzen, statt sie ein
    zweites Mal zu holen - und beide Wege rechnen beweisbar auf denselben
    Zahlen. `merken` und `--json` lesen den Schluessel nicht.
    """
    ueber, unter, offen = [], [], []
    kerzen_zeit, kurz = None, []
    brauchen = FENSTER + (VERLAUF_MIT if mit_verlauf else 0)
    verlaeufe = {}
    for inst in (paare or PAARE):
        try:
            verlauf = hole(inst, brauchen)
        except Exception as f:                 # noqa: BLE001
            offen.append({"inst": inst, "grund": str(f)[:70]})
            continue
        verlaeufe[inst] = verlauf
        kerzen_zeit = kerzen_zeit or verlauf[-1][0]
        if len(verlauf) < FENSTER:
            kurz.append(inst)
        schluesse = fenster_von(verlauf, len(verlauf) - 1)
        satz = _messe_fenster(schluesse) if schluesse else None
        if satz is None:
            offen.append({"inst": inst, "grund": "nur %d Tageskerzen"
                          % len(verlauf)})
            continue
        kurs, e, abstand = satz
        zeile = {"inst": inst, "kurs": kurs, "ema": e, "abstand": abstand}
        (ueber if kurs > e else unter).append(zeile)
        if not still:
            time.sleep(0.05)
    gesamt = len(ueber) + len(unter)
    raus = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kerze": kerzentag(kerzen_zeit) if kerzen_zeit else None,
        "ueber": sorted(ueber, key=lambda z: -z["abstand"]),
        "unter": sorted(unter, key=lambda z: z["abstand"]),
        "offen": offen,
        "kurzes_fenster": kurz,
        "n_ueber": len(ueber),
        "n_gesamt": gesamt,
        "breite": (100.0 * len(ueber) / gesamt) if gesamt else None,
    }
    if mit_verlauf:
        raus["_verlauf"] = verlaeufe
    return raus


def zeige(m):
    print("== UEBER der EMA200 (%d) ==" % LAENGE)
    for s in m["ueber"]:
        print("  %-10s %14.6f   EMA200 %14.6f   %+7.2f %%"
              % (s["inst"], s["kurs"], s["ema"], s["abstand"]))
    print("== UNTER der EMA200 ==")
    for s in m["unter"]:
        print("  %-10s %14.6f   EMA200 %14.6f   %+7.2f %%"
              % (s["inst"], s["kurs"], s["ema"], s["abstand"]))
    if m["offen"]:
        print("== NICHT GEMESSEN ==")
        for o in m["offen"]:
            print("  %-10s %s" % (o["inst"], o["grund"]))
    if m.get("kurzes_fenster"):
        print("== KUERZERE GESCHICHTE ALS %d KERZEN ==" % FENSTER)
        print("  " + ", ".join(m["kurzes_fenster"]))
    print("")
    if m["n_gesamt"]:
        print("BREITE: %d von %d ueber der EMA200 = %.1f %%"
              % (m["n_ueber"], m["n_gesamt"], m["breite"]))
    print("(Deckung %d von %d, Kerze %s, gemessen %s)"
          % (m["n_gesamt"], len(PAARE), m["kerze"], m["ts"]))


def _satz_aus(ueber, unter, abstand, kerze, ts, art, offen, zusatz=None):
    """Eine Zeile der Reihe aus gerechneten Werten."""
    gesamt = len(ueber) + len(unter)
    satz = {
        "ts": ts, "kerze": kerze,
        "n_ueber": len(ueber), "n_gesamt": gesamt,
        "breite": round(100.0 * len(ueber) / gesamt, 2) if gesamt else None,
        "unter": sorted(unter), "offen": sorted(offen),
        "abstand": {i: round(a, 2) for i, a in abstand.items()},
    }
    if art and art != "live":
        satz["art"] = art
    if zusatz:
        satz.update(zusatz)
    return satz


def _schreibe(saetze):
    with open(REIHE, "w", encoding="utf-8", newline="\n") as f:
        for z in saetze:
            f.write(json.dumps(z, ensure_ascii=False) + "\n")


def merken(m):
    """Eine Zeile je KERZENTAG. Abstaende mit, sonst ist der Verlauf blind.

    FALLE (gemessen 25.09.2026): zuerst wurde bei JEDER Messung angebaut. Sechs
    Laeufe am selben Tag ergaben sechs Zeilen mit DEMSELBEN Wert (Kerze
    2026-09-23) - "die letzten 30 Messungen" waren damit EIN Tag, und "die
    Breite schrumpft" blieb unbelegbar. Eine Messung derselben Kerze ERSETZT
    daher ihre Zeile; die letzte Messung des Tages gewinnt. Die Tageskerze
    wechselt um 16:00 UTC.
    """
    unter = [s["inst"] for s in m["unter"]]
    abstand = {s["inst"]: round(s["abstand"], 2)
               for s in m["ueber"] + m["unter"]}
    satz = {
        "ts": m["ts"], "kerze": m["kerze"],
        "n_ueber": m["n_ueber"], "n_gesamt": m["n_gesamt"],
        "breite": round(m["breite"], 2) if m["breite"] is not None else None,
        "unter": unter,
        "offen": [o["inst"] for o in m["offen"]],
        "abstand": abstand,
    }
    # Wurde der Tag vorher NACHGERECHNET, bleibt das Ergebnis als Beleg in der
    # Zeile stehen: die Messung gilt, aber der Vergleich der zwei Wege ist
    # spaeter noch nachlesbar (die Wache prueft ihn jeden Tag neu).
    vorher = {z.get("kerze"): z for z in reihe(None)}.get(satz["kerze"])
    if vorher is not None and vorher.get("art") == "nachgerechnet":
        satz["nachgerechnet_alt"] = {"breite": vorher.get("breite"),
                                     "unter": list(vorher.get("unter") or [])}
        if vorher.get("nachgerechnet_am"):
            satz["nachgerechnet_am"] = vorher["nachgerechnet_am"]
    # Reihenfolge bleibt zeitlich: eine aeltere Kerze wird dort ersetzt, wo sie
    # steht (kommt bei einem Nachlauf vor), nicht angehaengt.
    alt = [z for z in reihe(None)
           if not (satz["kerze"] and z.get("kerze") == satz["kerze"])]
    alt.append(satz)
    alt.sort(key=lambda z: (z.get("kerze") or ""))
    _schreibe(alt)
    return satz


def reihe(n=30):
    """Zeilen der Reihe, aelteste zuerst. n=None oder 0 = alle."""
    if not os.path.exists(REIHE):
        return []
    saetze = []
    with open(REIHE, encoding="utf-8") as f:
        for zeile in f:
            zeile = zeile.strip()
            if not zeile:
                continue
            try:
                saetze.append(json.loads(zeile))
            except ValueError:
                continue                      # eine kaputte Zeile killt nicht alles
    return saetze if not n else saetze[-n:]


def verlauf(n=None):
    """Die Reihe als VERLAUF: eine Zeile je Kerzentag, mit Veraenderung.

    Reine Rechnung auf den Zeilen der Reihe - kein Netz, damit pruefbar.
    Rueckgabe (aeltester Kerzentag zuerst), je dict:
        kerze, breite, n_ueber, n_gesamt, delta, unter, messungen, art
    `delta` = Veraenderung gegenueber dem Kerzentag DAVOR, in Punkten (None beim
    ersten Tag). `messungen` zaehlt die Zeilen, die zu diesem Tag in der Reihe
    standen - mehr als 1 heisst: es wurde mehrfach gemessen und ersetzt.
    `art` = 'live', wenn eine echte Messung den Tag gestellt hat, sonst
    'nachgerechnet'.
    """
    tage = {}
    for s in reihe(None):
        k = s.get("kerze")
        if not k:
            continue                          # ohne Kerze kein Tagesbezug
        if k not in tage:
            tage[k] = {"kerze": k, "breite": s.get("breite"),
                       "n_ueber": s.get("n_ueber"),
                       "n_gesamt": s.get("n_gesamt"),
                       "unter": list(s.get("unter") or []), "messungen": 0,
                       "art": s.get("art") or "live"}
        tage[k]["messungen"] += 1
    raus, vorher = [], None
    for k in sorted(tage):
        z = tage[k]
        if vorher is not None and z["breite"] is not None:
            z["delta"] = round(z["breite"] - vorher, 2)
        else:
            z["delta"] = None
        if z["breite"] is not None:
            vorher = z["breite"]
        raus.append(z)
    return raus[-n:] if n else raus


# ---------------------------------------------------------------- Luecken

def fehlende_tage(tage, bis=None):
    """Kerzentage, die zwischen erster und letzter Zeile FEHLEN - reine Rechnung.

    Der Kerzentag ist ein Kalendertag (UTC), die Reihe fuehrt EINE Zeile je Tag.
    Ein Kalendertag zwischen der aeltesten und der neuesten Zeile ohne Zeile ist
    deshalb eine Luecke - der Rechner war aus oder der Lauf ist ausgefallen
    (`--merken` schreibt nur, wenn wirklich gemessen wurde).

    `bis` verschiebt das Ende: der Waechter kennt die gerade gemessene Kerze,
    auch wenn `merken` noch nicht geschrieben hat. `bis` wird nie gekuerzt -
    liegt es VOR dem ersten Tag, gibt es keine Luecke.

    Rueckgabe: (luecken, erster, letzter). `luecken` = Liste von YYYY-MM-DD,
    aelteste zuerst. Eine leere Reihe gibt ([], None, None).
    """
    tage_geordnet = sorted({z["kerze"] for z in tage if z.get("kerze")})
    if not tage_geordnet:
        return [], None, None
    erster = tage_geordnet[0]
    letzter = tage_geordnet[-1]
    if bis and bis > letzter:
        letzter = bis
    if letzter < erster:
        return [], erster, letzter
    vorhanden = set(tage_geordnet)
    luecken, d = [], datetime.strptime(erster, "%Y-%m-%d").date()
    ende = datetime.strptime(letzter, "%Y-%m-%d").date()
    while d <= ende:
        k = d.isoformat()
        if k not in vorhanden:
            luecken.append(k)
        d += timedelta(days=1)
    return luecken, erster, letzter


def luecken_bereiche(luecken):
    """Zusammenhaengende Luecken als Bereiche: [('2026-07-02','2026-07-03'), ...].

    Eine Liste einzelner Tage ist bei einem langen Ausfall unlesbar; gemeldet
    wird ein Bereich. Reine Rechnung auf den Tagen aus `fehlende_tage`.
    """
    raus, lauf = [], []
    for k in sorted(luecken):
        if lauf and (datetime.strptime(k, "%Y-%m-%d").date()
                     - datetime.strptime(lauf[-1], "%Y-%m-%d").date()) \
                != timedelta(days=1):
            raus.append((lauf[0], lauf[-1]))
            lauf = []
        lauf.append(k)
    if lauf:
        raus.append((lauf[0], lauf[-1]))
    return raus


def luecken_text(luecken):
    """Ein Satz je Luecke: '2026-07-02 .. 2026-07-03 (2 Kerzentage)'."""
    raus = []
    for von, bis in luecken_bereiche(luecken):
        if von == bis:
            raus.append("%s (1 Kerzentag)" % von)
        else:
            raus.append("%s .. %s (%d Kerzentage)"
                        % (von, bis, (datetime.strptime(bis, "%Y-%m-%d").date()
                                      - datetime.strptime(von, "%Y-%m-%d").date()
                                      ).days + 1))
    return raus


# ---------------------------------------------------------------- Nachrechnen

def reihe_rechnen(verlauf_je_inst, tage, fenster=FENSTER):
    """Breite je Kerzentag rueckwaerts rechnen - REINE Funktion, kein Netz.

    `verlauf_je_inst` = {inst: [(ts_ms, schluss), ...]} aelteste zuerst, je Paar
    mindestens `fenster` Kerzen VOR dem aeltesten Zieltrag.
    Rueckgabe: {kerzentag: {n_ueber, n_gesamt, breite, unter, offen, abstand}}.
    """
    zeitachse = sorted({ts for r in verlauf_je_inst.values() for ts, _ in r})
    ziel = zeitachse[-int(tage):] if tage else zeitachse
    index = {i: {ts: n for n, (ts, _) in enumerate(r)}
             for i, r in verlauf_je_inst.items()}
    raus = {}
    for ts in ziel:
        ueber, unter, offen, abstand = [], [], [], {}
        for inst in sorted(verlauf_je_inst):
            schluesse = fenster_von(verlauf_je_inst[inst],
                                    index[inst].get(ts), fenster)
            satz = _messe_fenster(schluesse) if schluesse else None
            if satz is None:
                offen.append(inst)
                continue
            kurs, _e, a = satz
            abstand[inst] = a
            (ueber if kurs > _e else unter).append(inst)
        if not (ueber or unter):
            continue
        raus[kerzentag(ts)] = _satz_aus(ueber, unter, abstand, kerzentag(ts),
                                        None, "nachgerechnet", offen)
    return raus


def fuellen(tage=NACHRECHNEN_TAGE, ueberschreiben=False, still=False,
            verlauf_je_inst=None):
    """Die Reihe rueckwaerts nachrechnen und fehlende Kerzentage ergaenzen.

    Vorhandene LIVE-Zeilen bleiben stehen (sie sind der Beleg, dass der Tag
    wirklich gemessen wurde); nur fehlende Tage kommen dazu. Mit
    `ueberschreiben=True` stellt die Nachrechnung jeden Tag - der alte Live-Wert
    bleibt dann als `live_alt` in der Zeile stehen.

    `verlauf_je_inst` kann fertige Kerzenverlaeufe mitgeben (aus
    `messen(mit_verlauf=True)`); dann entfaellt der zweite Abruf, und die
    Nachrechnung rechnet auf DENSELBEN Kerzen wie die Live-Messung.

    Rueckgabe: gefuellt, abgleich (Abweichung gegen vorhandene Tage), ohne
    (Paare ohne Daten), kerzen_je_paar, tage.
    """
    brauchen = FENSTER + int(tage) + 5
    ohne = []
    if verlauf_je_inst is None:
        verlauf_je_inst = {}
        for inst in PAARE:
            try:
                verlauf_je_inst[inst] = hole(inst, brauchen)
            except Exception as f:             # noqa: BLE001
                ohne.append({"inst": inst, "grund": str(f)[:70]})
            if not still:
                time.sleep(0.05)
    else:
        verlauf_je_inst = {i: r for i, r in verlauf_je_inst.items() if r}
    gerechnet = reihe_rechnen(verlauf_je_inst, tage)
    alt = {z.get("kerze"): z for z in reihe(None) if z.get("kerze")}
    abgleich = []
    for k, z in sorted(gerechnet.items()):
        if k in alt and alt[k].get("breite") is not None:
            abgleich.append({"kerze": k, "live": alt[k]["breite"],
                             "nachgerechnet": z["breite"],
                             "diff": round(z["breite"] - alt[k]["breite"], 2),
                             "unter_live": list(alt[k].get("unter") or []),
                             "unter_jetzt": list(z["unter"] or [])})

    neu = 0
    jetzt = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for k, z in gerechnet.items():
        vorher = alt.get(k)
        if vorher is not None and not ueberschreiben:
            continue
        if vorher is not None and vorher.get("art") != "nachgerechnet":
            # Der Tag wurde LIVE gemessen - mit dem alten, kuerzeren Fenster.
            # Der alte Wert bleibt als BELEG in der Zeile stehen (er ist die
            # Messung von damals), aber die Reihe selbst rechnet einheitlich.
            z["live_alt"] = vorher.get("breite")
            z["live_alt_unter"] = list(vorher.get("unter") or [])
        z["nachgerechnet_am"] = jetzt
        alt[k] = z
        neu += 1
    _schreibe([alt[k] for k in sorted(alt)])
    return {"gefuellt": neu, "abgleich": abgleich, "ohne": ohne,
            "kerzen_je_paar": {i: len(r) for i, r in verlauf_je_inst.items()},
            "tage": len(alt)}


# ---------------------------------------------------------------- Kennzahlen

def _median(werte):
    if not werte:
        return None
    w = sorted(werte)
    m = len(w) // 2
    return w[m] if len(w) % 2 else (w[m - 1] + w[m]) / 2.0


def _perzentil(werte, p):
    if not werte:
        return None
    w = sorted(werte)
    k = (len(w) - 1) * p / 100.0
    lo = int(k)
    hi = min(lo + 1, len(w) - 1)
    return w[lo] + (w[hi] - w[lo]) * (k - lo)


def kennzahlen(tage):
    """Verteilung der Reihe (aus verlauf()) - reine Rechnung.

    Beantwortet unter anderem, ob ein Melde-Schwellwert wie 10 Punkte ueber
    oder unter dem Tagesrauschen liegt: `delta_p*` und `anteil_ueber_10`.
    """
    werte = [(z["kerze"], z["breite"]) for z in tage
             if z.get("breite") is not None]
    if not werte:
        return {"n_tage": 0}
    zahlen = [b for _, b in werte]
    deltas = [z["delta"] for z in tage if z.get("delta") is not None]
    betraege = [abs(d) for d in deltas]
    return {
        "n_tage": len(werte),
        "erster": werte[0][0], "letzter": werte[-1][0],
        "mittel": round(sum(zahlen) / len(zahlen), 2),
        "median": round(_median(zahlen), 2),
        "min": min(zahlen), "min_tag": min(werte, key=lambda z: z[1])[0],
        "max": max(zahlen), "max_tag": max(werte, key=lambda z: z[1])[0],
        "n_ueber_90": sum(1 for b in zahlen if b >= 90.0),
        "n_ueber_80": sum(1 for b in zahlen if b >= 80.0),
        # Hochphasen-Tage (>= 60, die "achtung"-Stufe der Wache): die
        # Stichprobe fuer die Rueckgang-Schwelle (RUCKGANGS_PP). Entscheidet
        # wird erst mit 30 solchen Tagen - bis dahin zaehlt die Statistik.
        "n_ueber_60": sum(1 for b in zahlen if b >= 60.0),
        "n_unter_60": sum(1 for b in zahlen if b < 60.0),
        "n_delta": len(deltas),
        "delta_median_abs": round(_median(betraege), 2) if betraege else None,
        "delta_p75_abs": round(_perzentil(betraege, 75), 2) if betraege else None,
        "delta_p90_abs": round(_perzentil(betraege, 90), 2) if betraege else None,
        "delta_max_abs": max(betraege) if betraege else None,
        "n_ueber_10": sum(1 for b in betraege if b >= 10.0),
        "anteil_ueber_10": (round(100.0 * sum(1 for b in betraege if b >= 10.0)
                                  / len(betraege), 1) if betraege else None),
        "n_gefallen": sum(1 for d in deltas if d < 0),
        "n_gestiegen": sum(1 for d in deltas if d > 0),
        "laengste_serie_90": serie_ueber(tage, 90.0),
    }


def serie_ueber(tage, schwelle=90.0):
    """Laengste zusammenhaengende Folge von Kerzentagen >= schwelle."""
    beste, lauf = None, []
    for z in tage:
        if z.get("breite") is not None and z["breite"] >= schwelle:
            lauf.append(z["kerze"])
            if beste is None or len(lauf) > len(beste):
                beste = list(lauf)
        else:
            lauf = []
    return {"n": len(beste) if beste else 0,
            "von": beste[0] if beste else None,
            "bis": beste[-1] if beste else None}


def vorwaerts(tage, kurse, horizont=7, schwelle=90.0):
    """Was folgte auf eine hohe Breite? - reine Rechnung.

    `kurse` = {kerzentag: schluss} EINES Instruments (Vergleichsmass, im Haus
    BTC-USDT). Verglichen wird die Vorwaertsrendite ueber `horizont`
    HANDELSTAGE der Kursreihe: alle Tage gegen die Tage mit Breite >=
    `schwelle` und die darunter. Ohne die Gruppe "alle" ist eine Zahl nicht
    deutbar.
    """
    tage_geordnet = sorted(kurse)
    pos = {k: i for i, k in enumerate(tage_geordnet)}
    gruppen = {"alle": [], "hoch": [], "niedrig": []}
    for z in tage:
        k, b = z.get("kerze"), z.get("breite")
        if k is None or b is None or k not in pos:
            continue
        i = pos[k]
        if i + horizont >= len(tage_geordnet):
            continue                           # Zukunft fehlt noch
        r = (kurse[tage_geordnet[i + horizont]] / kurse[k] - 1.0) * 100.0
        gruppen["alle"].append(r)
        gruppen["hoch" if b >= schwelle else "niedrig"].append(r)
    raus = {}
    for name, werte in gruppen.items():
        raus[name] = {
            "n": len(werte),
            "median": round(_median(werte), 2) if werte else None,
            "mittel": round(sum(werte) / len(werte), 2) if werte else None,
            "anteil_positiv": (round(100.0 * sum(1 for w in werte if w > 0)
                                     / len(werte), 1) if werte else None),
        }
    raus["horizont"] = horizont
    raus["schwelle"] = schwelle
    return raus


def kurse_je_tag(inst="BTC-USDT", anzahl=400):
    """{kerzentag: schluss} eines Instruments, nur abgeschlossene Kerzen."""
    return {kerzentag(ts): s for ts, s in hole(inst, anzahl)}


def _zahl_aus(argv, name, vorgabe):
    for a in argv:
        if a.startswith(name + "="):
            try:
                return float(a.split("=", 1)[1])
            except ValueError:
                return vorgabe
    return vorgabe


def _zahlen_aus(argv, name, vorgaben):
    roh = _zahl_aus(argv, name, None)
    return [int(roh)] if roh is not None else [int(v) for v in vorgaben]


def main(argv):
    if "--reihe" in argv:
        tage = verlauf()
        if not tage:
            print("Keine Reihe vorhanden - noch nichts gemessen.")
            return 0
        print("== Breite-Reihe: %d Kerzentag(e) ==" % len(tage))
        for z in tage:
            print("  %s  %6s %%  (%d/%d)  %s%s%s"
                  % (z["kerze"],
                     ("%.1f" % z["breite"]) if z["breite"] is not None else "-",
                     z["n_ueber"] if z["n_ueber"] is not None else 0,
                     z["n_gesamt"] if z["n_gesamt"] is not None else 0,
                     ("%+.1f pp" % z["delta"]) if z["delta"] is not None
                     else "   -",
                     "  unter: " + ",".join(z["unter"]) if z["unter"] else "",
                     "  [nachgerechnet]" if z.get("art") == "nachgerechnet"
                     else ""))
        luecken, erster, letzter = fehlende_tage(tage)
        if luecken:
            print("  LUECKEN: %d Kerzentag(e) fehlen zwischen %s und %s:"
                  % (len(luecken), erster, letzter))
            for z in luecken_text(luecken):
                print("    " + z)
        elif erster:
            print("  Keine Luecke zwischen %s und %s (%d Kerzentage)."
                  % (erster, letzter, len(tage)))
        if len(tage) < 2:
            print("  Ein Kerzentag ist ein Messpunkt, keine Richtung - "
                  "fuer die Richtung braucht es mindestens zwei.")
        return 0

    if "--fuellen" in argv:
        tage = int(_zahl_aus(argv, "--tage", NACHRECHNEN_TAGE))
        r = fuellen(tage, ueberschreiben="--ueberschreiben" in argv)
        print("== Nachgerechnet: %d Paar(e) ==" % len(r["kerzen_je_paar"]))
        if r["kerzen_je_paar"]:
            print("  Kerzen je Paar: %d bis %d (noetig %d)"
                  % (min(r["kerzen_je_paar"].values()),
                     max(r["kerzen_je_paar"].values()), FENSTER + tage))
            kurz = sorted(i for i, n in r["kerzen_je_paar"].items()
                          if n < FENSTER + tage)
            if kurz:
                print("  kuerzer: " + ", ".join(kurz))
        if r["ohne"]:
            print("  nicht messbar: " + ", ".join(o["inst"] for o in r["ohne"]))
        print("  neu eingetragen: %d, Reihe jetzt %d Kerzentage"
              % (r["gefuellt"], r["tage"]))
        if r["abgleich"]:
            print("== Abgleich gegen die LIVE gemessenen Tage ==")
            for a in r["abgleich"]:
                print("  %s  live %6.2f %%  nachgerechnet %6.2f %%  %+6.2f pp%s"
                      % (a["kerze"], a["live"], a["nachgerechnet"], a["diff"],
                         "" if a["unter_live"] == a["unter_jetzt"]
                         else "   UNTER verschieden: %s -> %s"
                              % (",".join(a["unter_live"]) or "-",
                                 ",".join(a["unter_jetzt"]) or "-")))
        return 0

    if "--statistik" in argv:
        tage = verlauf()
        if not tage:
            print("Keine Reihe vorhanden - erst messen (--merken).")
            return 1
        k = kennzahlen(tage)
        print("== Breite-Reihe: %d Kerzentage (%s .. %s) =="
              % (k["n_tage"], k["erster"], k["letzter"]))
        print("  Breite: Mittel %.1f %%, Median %.1f %%, min %.1f %% (%s), "
              "max %.1f %% (%s)"
              % (k["mittel"], k["median"], k["min"], k["min_tag"], k["max"],
                 k["max_tag"]))
        print("  Tage >= 90 %%: %d    >= 80 %%: %d    >= 60 %%: %d    < 60 %%: %d"
              % (k["n_ueber_90"], k["n_ueber_80"], k["n_ueber_60"],
                 k["n_unter_60"]))
        s = k["laengste_serie_90"]
        print("  laengste Serie >= 90 %%: %d Kerzentag(e) (%s .. %s)"
              % (s["n"], s["von"], s["bis"]))
        print("== Tagesschwankung (|Aenderung| zum Vortag, %d Tage) =="
              % k["n_delta"])
        print("  Median %.1f pp   p75 %.1f pp   p90 %.1f pp   groesste %.1f pp"
              % (k["delta_median_abs"], k["delta_p75_abs"],
                 k["delta_p90_abs"], k["delta_max_abs"]))
        print("  Tage mit >= 10 pp: %d (%.1f %%)   gefallen %d / gestiegen %d"
              % (k["n_ueber_10"], k["anteil_ueber_10"], k["n_gefallen"],
                 k["n_gestiegen"]))
        schwelle = _zahl_aus(argv, "--schwelle", 90.0)
        for h in _zahlen_aus(argv, "--horizont", (7, 30)):
            try:
                kurse = kurse_je_tag(anzahl=FENSTER)
            except Exception as f:             # noqa: BLE001
                print("  (Vergleichskurs nicht abrufbar: %s)" % str(f)[:60])
                break
            v = vorwaerts(tage, kurse, horizont=h, schwelle=schwelle)
            print("== Was auf eine Breite >= %.0f %% folgte (BTC-USDT, "
                  "%d Handelstage spaeter) ==" % (schwelle, h))
            for name, text in (("alle", "alle Tage"), ("hoch", ">= Schwelle"),
                               ("niedrig", "< Schwelle")):
                g = v[name]
                if not g["n"]:
                    print("  %-12s keine Messung" % text)
                    continue
                print("  %-12s n=%3d   Median %+6.2f %%   Mittel %+6.2f %%   "
                      "positiv %s %%"
                      % (text, g["n"], g["median"], g["mittel"],
                         ("%.0f" % g["anteil_positiv"])))
        return 0

    m = messen()
    if "--json" in argv:
        print(json.dumps(m, ensure_ascii=False))
    else:
        zeige(m)
    if "--merken" in argv:
        s = merken(m)
        print("In der Reihe vermerkt: Kerze %s (%.1f %%)"
              % (s["kerze"], s["breite"]))
    return 0 if m["n_gesamt"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))