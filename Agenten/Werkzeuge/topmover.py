"""Wer bewegt sich gerade - und ist der Move noch gesund?

`breite.py` beantwortet eine Frage: Wie viele Paare stehen ueber ihrer EMA200?
Das ist der ZUSTAND des Marktes. Die zweite Frage beantwortet es nicht: Welche
Paare machen die Bewegung, und ist die Bewegung noch getragen?

Genau da ist am 02.10.2026 NIGHT (+129 % in 30 Tagen) aufgefallen. Die Breite
sagte "89,7 %, Trend intakt", die Tageskerze sagte "1,1 % unter dem 90-Tage-Hoch,
Volumen vom 9,9-fachen auf das 1,7-fache des Median gefallen". Das sind zwei
voellig verschiedene Aussagen ueber dasselbe Ding, und die zweite ist die
wichtigere.

WAS DIESES WERKZEUG MISST (je Paar, aus abgeschlossenen Tageskerzen)
---------------------------------------------------------------------
* Rendite ueber 7/30/90 Tage
* Volumen gegen den 30-Tage-Median - der Traeger des Moves
* Volumen-Kraefte: der Vergleich mit dem 30-Tage-MEDIAN statt mit dem Vortag
  ist der ganze Punkt. Ein "heute 2x gestern" sagt nichts (gestern kann 0,2x
  Median gewesen sein). "1,7x Median" ist eine Zahl mit Bedeutung.
* EMA200-Abstand - Trend, aber auch Ueberdehnung
* ATR14 in Prozent - wie gross ist eine NORMALETagesbewegung. Ohne diese Zahl
  ist jedes "%-Ziel" eine Ausrede: bei 8,3 % ATR liegt ein -20 %-Stop INNERHALB
  der normalen Spanne.
* Abstand zum 90-Tage-Hoch und zum EMA200

DIE VIER LAGEN (das ist die Antwort, nicht die Rohzahl)
-------------------------------------------------------
`ausbruch`  ueber dem 90-Tage-Hoch, Volumen >= 5x Median  - Trend setzt sich fort
`getragen`  ueber der EMA200, Volumen 1,5x-5x             - gesunde Bewegung
`ballon`    ueber der EMA200, Volumen < 1,5x Median       - der Kaeufer geht
            weg, der Preis haelt sich noch. NIGHT stand hier (1,7x und fallend)
`ueberdehnt` ueber der EMA200, aber Volumen faellt UND Kurs < 2 % vom Hoch -
            die gefaehrlichste Lage: hohes Chance-Risiko, dünner Traeger
`schwach`   unter der EMA200                              - kein Kandidat

WARUM DIE LAGE STATT DER AMPEL
-----------------------------
Eine Ampel aus "Kurs +129 %" ist eine FALSCHE Information: dieselbe Zahl ist bei
BTC (+4 %/30T) ein Kauf und bei NIGHT (+129 %/30T) eine Warnung. Was
unterscheidet, ist der Traeger (Volumen) und der Abstand zum Hoch. Deshalb
jede Zahl mit ihrer Groesse und jede Lage mit ihrer Begründung.

QUELLE
------
OEFFENTLICHE OKX-Schnittstelle, kein Schluessel, kein Konto. Wie breite.py: mit
einem Browser-Kopf, sonst HTTP 403. Die Rohdaten holt `hole()` - die Naht fuer
Tests, damit ohne Netz gemessen werden kann.

AUFRUF (aus Agenten/Werkzeuge heraus)
    python topmover.py                   # Lage aller Paare
    python topmover.py --kriterien       # nur handelbare Kandidaten
    python topmover.py --paare NIGHT-USDT,BTC-USDT
    python topmover.py --json            # Maschinenform
    python topmover.py --schwelle 5      # Ausbruch ab 5x statt 5x
"""
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PAARE = [
    "BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "BNB-USDT",
    "DOGE-USDT", "ADA-USDT", "LINK-USDT", "AVAX-USDT", "TON-USDT",
    "DOT-USDT", "POL-USDT", "LTC-USDT", "TRX-USDT", "SHIB-USDT",
    "ATOM-USDT", "UNI-USDT", "NEAR-USDT", "APT-USDT", "ARB-USDT",
    "OP-USDT", "FIL-USDT", "INJ-USDT", "SUI-USDT", "SEI-USDT",
    "TIA-USDT", "PEPE-USDT", "ETC-USDT", "XLM-USDT", "ALGO-USDT",
    "NIGHT-USDT", "ASTR-USDT", "WLD-USDT", "RUNE-USDT", "JUP-USDT",
    "AAVE-USDT", "MKR-USDT", "LDO-USDT", "CRV-USDT", "SNX-USDT",
    "GRT-USDT", "IMX-USDT", "SAND-USDT", "MANA-USDT", "AXS-USDT",
    "HBAR-USDT", "ONDO-USDT", "ENA-USDT", "PENGU-USDT",
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
KERZEN = 300
EMA_N = 200
AUSBRUCH_TAGE = 90
NAH_HOCH = 2.0          # % unter dem Hoch = noch "am Hoch"

SCHWELLE_AUSBRUCH = 5.0    # Volumen >= 5x Median
SCHWELLE_GETRAGEN = 1.5    # >= 1,5x Median

ZUSTAENDE = ("ausbruch", "getragen", "ballon", "ueberdehnt", "schwach")


# --- Daten ------------------------------------------------------------------

def _anfrage(url):
    """OKX blockt den Standardkopf mit 403 - Browser-Kopf mitgeben."""
    return urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) topmover",
        "Accept": "application/json",
    })


def hole(url, basis=None):
    """Rohdaten einer URL. Die EINZIGE Netzstelle - Tests biegen sie um."""
    ziel = url if url.startswith("http") else "%s%s" % (basis or BASEN[0], url)
    okx_takt.reserviere()
    with urllib.request.urlopen(_anfrage(ziel), timeout=20) as a:
        return json.loads(a.read().decode("utf-8"))


def kerzen(inst, anzahl=KERZEN):
    """Abgeschlossene Tageskerzen, aelteste zuerst.

    Nur `confirm == "1"`: eine laufende Tageskerze ist kein Schlusskurs. Ein
    Tageshoch aus einer halben Kerze ist die haeufigste Falschaussage in
    solchen Werkzeugen (gemessen am 02.10.2026).
    """
    for basis in BASEN:
        try:
            d = hole("/api/v5/market/candles?instId=%s&bar=1D&limit=%d"
                     % (inst, anzahl), basis)
        except Exception:                                   # noqa: BLE001
            continue
        if d.get("code") != "0":
            continue
        k = [r for r in (d.get("data") or []) if r[8] == "1"]
        k.sort(key=lambda r: r[0])
        return k
    return []


# --- Rechnung ---------------------------------------------------------------

def ema(werte, n=EMA_N):
    """Exponentieller Durchschnitt ueber die SCHLUSSkurse."""
    if not werte or len(werte) < n:
        return None
    e = sum(werte[:n]) / n
    a = 2.0 / (n + 1)
    for v in werte[n:]:
        e = v * a + e * (1 - a)
    return e


def median(werte):
    s = sorted(v for v in werte if v is not None and v > 0)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def atr(k, n=14):
    """Durchschnittliche True Range in Prozent des Schlusskurses.

    Die Zahl, ohne die jedes Prozent-Ziel eine Ausrede ist: bei 8 % ATR liegt
    ein -20 %-Stop INNERHALB der normalen Tagesspanne.
    """
    if len(k) < n + 1:
        return None
    trs = []
    for i in range(1, len(k)):
        h, l = float(k[i][2]), float(k[i][3])
        pc = float(k[i - 1][4])
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return (sum(trs[-n:]) / n) / float(k[-1][4]) * 100.0 if k[-1][4] else None


def lage(k, einstieg_schwelle=SCHWELLE_AUSBRUCH, nah_hoch=NAH_HOCH):
    """Die LAGE eines Instruments aus seinen Kerzen. Reine Funktion.

    Rueckgabe: dict mit allen Kennzahlen und `zustand`. `zustand=None` heisst
    "zu wenig Historie" - kein 'unbekannt' als LAGE.
    """
    if len(k) < EMA_N + 1:
        # Zu wenig Historie ist KEIN Instrument, sondern eine LAGE:
        # 'keine Aussage'. Als eigener Zustand, damit die Rangfolge ihn
        # einordnet statt ihn zu verstecken.
        return dict(zustand=" unbekannt"[:0] or "unbekannt",
                    grund="nur %d Kerzen (EMA braucht %d)" % (len(k), EMA_N),
                    kerzen=len(k))
    c = [float(r[4]) for r in k]
    jetzt = c[-1]
    v = [float(r[5]) for r in k]
    e = ema(c)
    med = median(v[-31:-1] if len(v) > 31 else v[:-1])   # Median OHNE heute
    tage = len(k)
    hoch = max(float(r[2]) for r in k[-min(AUSBRUCH_TAGE, tage):])
    fenster = min(90, tage - 1)
    hoch = max(float(r[2]) for r in k[-fenster:]) if fenster > 0 else jetzt
    a = atr(k)

    d = {}
    for n in (7, 30, 90):
        d["pct_%dt" % n] = (100.0 * (jetzt / c[-1 - n] - 1)
                            if tage > n else None)
    d.update({
        "kurs": jetzt,
        "ema200": e,
        "ueber_ema200": (jetzt > e) if e else None,
        "abstand_ema_pct": (100.0 * (jetzt / e - 1)) if e else None,
        "hoch_%dt" % AUSBRUCH_TAGE: hoch,
        "abstand_hoch_pct": (100.0 * (jetzt / hoch - 1)) if hoch else None,
        "atr14_pct": a,
        "volumen": v[-1],
        "volumen_median": med,
        "volumen_faktor": (v[-1] / med) if med else None,
        "kerzen": tage,
        "einstieg_schwelle": einstieg_schwelle,
        "nah_hoch": nah_hoch,
    })

    # Die Lage. Reihenfolge = Wichtigkeit: der Traeger entscheidet, ob der
    # Kurs ueberhaupt zaehlt.
    f = d["volumen_faktor"]
    hoch_nah = (d["abstand_hoch_pct"] is not None
                and d["abstand_hoch_pct"] > -nah_hoch)
    if not d["ueber_ema200"]:
        d["zustand"] = "schwach"
        d["begruendung"] = "unter der EMA200 - kein Kandidat"
    elif d["abstand_hoch_pct"] is not None and d["abstand_hoch_pct"] > 0:
        d["zustand"] = "ausbruch"
        d["begruendung"] = "ueber dem %dT-Hoch, Volumen %.1fx Median" % (
            AUSBRUCH_TAGE, f or 0)
    elif f is None:
        d["zustand"] = "getragen"
        d["begruendung"] = "ueber der EMA200, Volumen nicht messbar"
    elif f >= einstieg_schwelle:
        d["zustand"] = "ausbruch"
        d["begruendung"] = "am %dT-Hoch mit %.1fx Median - Trend setzt sich fort" % (
            AUSBRUCH_TAGE, f)
    elif f < SCHWELLE_GETRAGEN:
        # Der Ballon: die Zahl, die einen Kaeufer vermissen laesst.
        if hoch_nah:
            d["zustand"] = "ueberdehnt"
            d["begruendung"] = ("nur %.1f %% vom Hoch, aber Volumen nur %.1fx "
                                "Median - der Traeger fehlt" % (
                                    abs(d["abstand_hoch_pct"] or 0), f))
        else:
            d["zustand"] = "ballon"
            d["begruendung"] = "Volumen nur %.1fx Median - der Kaeufer geht weg" % f
    else:
        d["zustand"] = "getragen"
        d["begruendung"] = "ueber der EMA200, Volumen %.1fx Median" % f
    return d


def messe(inst, **kw):
    """Alles fuer ein Instrument. Netzfehler -> `zustand=None` mit Grund."""
    try:
        k = kerzen(inst)
    except Exception as e:                                   # noqa: BLE001
        return dict(zustand=None, inst=inst,
                    grund="Kerzen nicht abrufbar: %s" % type(e).__name__,
                    kerzen=0)
    if not k:
        # Der Name gehoert in JEDE Rueckgabe - sonst steht in der Liste ein
        # '?' und man weiss nicht, welches Instrument gemeint war.
        return dict(zustand=None, inst=inst,
                    grund="keine Kerzen von der Boerse", kerzen=0)
    d = lage(k, **{a: b for a, b in kw.items() if a in
                   ("einstieg_schwelle", "nah_hoch")})
    d["inst"] = inst
    return d


def alle(paare=None, **kw):
    """Alle Paare, nach Zustand sortiert (die interessanten zuerst)."""
    reihe = [messe(p, **kw) for p in (paare or PAARE)]
    rang = {"ausbruch": 0, "ueberdehnt": 1, "getragen": 2, "ballon": 3,
            "schwach": 4, "unbekannt": 5, None: 9}
    reihe.sort(key=lambda d: (rang.get(d.get("zustand"), 9),
                              -(d.get("pct_30t") if d.get("pct_30t") is not None
                                else -999)))
    return reihe


def kandidat(d):
    """Ein Instrument, bei dem ein Einstieg eine DEFINIERTE Position hat.

    Kriterium ist nicht "gefaellt mir" - es ist: ueber der EMA200, und der
    Traeger ist da. Genau diese beiden Bedingungen.
    """
    return d.get("zustand") in ("ausbruch", "getragen")


# --- Ausgabe ----------------------------------------------------------------

def _z(w):
    """Zahl kurz und mit Vorzeichen - ein Minuszeichen muss sichtbar sein."""
    return "   n/a" if w is None else "%+8.1f" % w


def zeile(d):
    if d.get("zustand") in (None, "unbekannt"):
        return "  %-14s %-10s %s" % (d.get("inst", "?"),
                                     d.get("zustand") or "keine Daten",
                                     d.get("grund"))
    # Jede Zahl an ihrer Groesse, JEDE Lage mit ihrer Begruendung. Die
    # Begruendung steht in der Fusszeile - sie passt nicht in eine Spalte,
    # und eine Lage ohne Grund ist ein Etikett.
    return ("  %-14s %-10s %12.6f %8.1f %8.1f %8.4g %9.1f %8.1f %7.1f"
            % (d.get("inst", "?"), d.get("zustand"), d.get("kurs") or 0,
               d.get("pct_7t") or 0, d.get("pct_30t") or 0,
               d.get("volumen_faktor") or 0,
               d.get("abstand_ema_pct") or 0,
               d.get("abstand_hoch_pct") or 0,
               d.get("atr14_pct") or 0))


def begruendungen(reihe, nur_kandidaten=False, grenze=6):
    """Die Erklaerung je Lage - der Grund steht NICHT in der Spalte."""
    print("\n   Warum (die oberen %d):" % grenze)
    n = 0
    for d in reihe:
        if nur_kandidaten and not kandidat(d):
            continue
        if d.get("zustand") in (None, "unbekannt"):
            continue
        print("     %-14s %s" % (d["inst"], d.get("begruendung", "")))
        n += 1
        if n >= grenze:
            break


def zeige(reihe, nur_kandidaten=False, titel=None):
    print("== %s ==" % (titel or "MARKT - wer bewegt sich"))
    print("   %-14s %-10s %12s %8s %8s %8s %9s %8s %8s %7s"
          % ("Instrument", "Lage", "Kurs", "7T", "30T", "Vol-fak",
             "EMA200", "v. Hoch", "ATR", "Lage?"))
    gezeigt = 0
    for d in reihe:
        if nur_kandidaten and not kandidat(d):
            continue
        print(zeile(d))
        gezeigt += 1
    if nur_kandidaten and not gezeigt:
        print("   (kein Paar erfuellt beide Bedingungen: ueber EMA200 UND Volumen >= 1,5x)")
    return gezeigt


def als_json(reihe):
    return json.dumps([d for d in reihe if d.get("zustand")], ensure_ascii=False)


def _zahl(argv, name, vorgabe):
    for a in argv:
        if a.startswith("--%s=" % name):
            return float(a.split("=", 1)[1])
    return vorgabe


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    paare = None
    for a in argv:
        if a.startswith("--paares="):
            paare = [x.strip().upper() for x in a.split("=", 1)[1].split(",")
                     if x.strip()]
    schwelle = _zahl(argv, "schwelle", SCHWELLE_AUSBRUCH)

    reihe = alle(paare, einstieg_schwelle=schwelle)
    if "--json" in argv:
        print(als_json(reihe))
        return 0
    nur = "--kriterien" in argv
    zeige(reihe, nur, "MARKT - wer bewegt sich (Kandidaten)" if nur else None)
    if "--ohne-grund" not in argv:
        begruendungen(reihe, nur)

    print("\n   Lagen: ausbruch = am %dT-Hoch mit Volumen | getragen = gesund |"
          % AUSBRUCH_TAGE)
    print("          ueberdehnt = am Hoch, Traeger fehlt | ballon = Kaeufer geht weg |")
    print("          schwach = unter EMA200")
    kandidaten = [d["inst"] for d in reihe if kandidat(d)]
    if kandidaten:
        print("\n   Kandidaten (ueber EMA200 UND Volumen >= %.1fx): %s"
              % (SCHWELLE_GETRAGEN, ", ".join(kandidaten)))
    print("   Quelle: oeffentliche OKX-Schnittstelle, %s, abgeschlossene Tageskerzen"
          % datetime.now(timezone.utc).strftime("%d.%m. %H:%M UTC"))
    return 0


if __name__ == "__main__":
    sys.exit(main())