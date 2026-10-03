# pragma pylint: disable=missing-docstring, invalid-name
"""Frequenzbremse fuer die Freqtrade-Bots (T-197, 01.10.2026).

WARUM ES DIESE DATEI GIBT
-------------------------
Der erste echte Backtest der drei Moon-Dev-Bots (30.09.2026) war in JEDEM
Fenster negativ, und der Grund war nicht die Richtung, sondern die ZAHL der
Trades: `MoonDevTradingAgent` machte 3,23 Runden pro Tag, bei 0,2 % je Runde
also ueber 240 % Kosten im Jahr. Im Backtest standen 8.399 USDT Gebuehren
gegen ein Ergebnis von -8.335 USDT - **der Verlust IST die Gebuehr**.

Im Haus gibt es zwei Bremsen, die in der Uebertragung fehlten:

* `Agenten/Handel/risikovorfilter.py` - die Regeln des Moon-Dev `risk_agent`
  ohne Sprachmodell: Verlust- und Gewinngrenze in einem 12-h-Fenster, danach
  kein neuer Einstieg.
* `scanner/handeln.in_zielsperre` / `in_abklingzeit` - Sperrfrist nach einem
  Ziel-Ausstieg (2 h) und Abklingzeit nach einem Stop (4 Tage).

Diese Datei traegt dieselben Regeln in Freqtrade-Sprache. Sie ist eine REINE
RECHNUNG (keine Freqtrade-Importe), damit sie ohne Boerse und ohne Container
geprueft werden kann - die Anbindung an Freqtrade steht in `moondev_basis.py`.

WELCHE ZAHLEN HAUS-ZAHLEN SIND UND WELCHE NICHT
-----------------------------------------------
Haus-Zahlen (aus `scanner/wachen.json`, nicht geraten):

* `sperrfrist_ziel_stunden 2.0` - Auftrag Max 23.09.2026 ("Sperrfrist 2h"):
  ZEC wurde live im Ziel verkauft und acht Sekunden spaeter fast zum selben
  Kurs neu gekauft; dieselbe Bewegung, 1,2 % Gebuehren.
* `sperrfrist_stop_stunden 96.0` - `abklingzeit_tage 4` aus derselben Wache.
  Nach einem GESCHEITERTEN Versuch gilt die laengere Frist, nicht die kurze.
* `fenster_stunden 12.0`, `verlust_max_pct 5.0`, `gewinn_ziel_pct 5.0` - die
  Zahlen des `risk_agent` (12 h, MAX_LOSS/GAIN_PERCENT 5).

NICHT aus dem Haus, sondern gemessen:

* `mindestabstand_einstieg_stunden` - Vorgabe 0.0 (AUS). Es gibt im Haus keine
  Zahl fuer "Abstand zwischen zwei Einstiegen desselben Paares"; sie wird am
  Backtest gesucht, nicht gesetzt.
* Die USD-Grenzen des risk_agent (25/25) sind hier ABSICHTLICH aus: sie sind
  an ein kleines Konto gebunden, waehrend der Backtest mit 10.000 USDT und
  ~3.300 USDT je Platz rechnet. Eine absolute 25-USD-Grenze waere dort 0,76 %
  des Einsatzes und wuerde jeden Handel sofort ersticken - das waere keine
  Uebertragung, sondern ein Rechenfehler. Die uebertragbare Fassung ist die
  PROZENTUALE (`verlust_max_pct`/`gewinn_ziel_pct`), weil sie skalenfrei ist.
  Wer die USD-Fassung will, setzt `verlust_max_usd`/`gewinn_ziel_usd`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Die Regeln. Fehlt ein Schluessel in der Konfiguration, gilt der Standard -
# eine fehlende Zeile darf keine Regel still umstellen.
#
# `bremse` ist ABSICHTLICH aus: dieselbe Haltung wie beim Haus-Vorfilter
# (`risikovorfilter.STANDARD["risikovorfilter"] = False`) - eine stillschweigend
# drosselnde Neuerung waere schlimmer als keine. Die Messung vom 01.10.2026
# stuetzt das: die Bremse senkt die Zahl der Runden, aber NICHT den Verlust je
# Runde (-0,16 % bis -0,21 % in JEDER Einstellung) - sie ist damit kein
# Heilmittel, sondern eine Option. Wer sie will, setzt sie in seiner Bot-
# Konfiguration (`moondev.bremse`).
STANDARD = {
    "bremse": False,
    "sperrfrist_ziel_stunden": 2.0,
    "sperrfrist_stop_stunden": 96.0,
    "mindestabstand_einstieg_stunden": 0.0,
    "fenster_stunden": 12.0,
    "verlust_max_pct": 5.0,
    "gewinn_ziel_pct": 5.0,
    "verlust_max_usd": None,
    "gewinn_ziel_usd": None,
    "max_einstiege_je_paar_im_fenster": 0,
}

# Freqtrade nennt den Ausstieg im Feld `exit_reason`. Was als "Ziel" und was
# als "Stop" zaehlt, steht hier - eine neue Schreibweise soll auffallen und
# nicht still durchfallen.
ZIEL_GRUENDE = ("roi",)
STOP_GRUENDE = ("stop_loss", "trailing_stop_loss")


def grenzen(cfg):
    """Die wirksamen Grenzen als dict - Standard, wo die Konfiguration schweigt."""
    aus = dict(STANDARD)
    for k in STANDARD:
        if cfg.get(k) is not None:
            aus[k] = cfg[k]
    return aus


def _zeit(wert):
    """datetime aus allem, was Freqtrade liefert (datetime oder ISO-Text)."""
    if isinstance(wert, datetime):
        t = wert
    elif wert:
        try:
            t = datetime.fromisoformat(str(wert).replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None


def urteil(runden, jetzt, paar, g):
    """(erlaubt, grund, regel) fuer EINEN geplanten Einstieg.

    `regel` ist der STABILE Schluessel der Regel ("mindestabstand",
    "sperrfrist_ziel", ...), `grund` der lesbare Satz. Gezaehlt wird ueber
    `regel` - ein Text mit der gemessenen Stundenzahl darin zerfaellt sonst in
    hunderte Zaehler und die Statistik ist wertlos.

    `runden` ist die abgeschlossene Handelsgeschichte: eine Liste von dicts

        {"paar": "BTC/USDT", "auf_zeit": datetime, "zu_zeit": datetime,
         "grund": "roi" | "stop_loss" | "exit_signal" | ...,
         "ergebnis_usd": float, "einsatz_usd": float}

    `jetzt` ist der Kerzenzeitpunkt, `paar` das Paar, das einsteigen will.
    Die Reihenfolge der Pruefungen ist Absicht: erst die Sperrfristen des
    PAARES (sie sind der harte Grund), dann die Grenzen des GANZEN BUCHS.
    """
    jetzt = _zeit(jetzt)
    if jetzt is None:
        return True, "kein Zeitpunkt - Bremse nicht anwendbar", "kein_zeitpunkt"
    if not g.get("bremse", True):
        return True, "Frequenzbremse aus", "bremse_aus"

    eigene = [r for r in runden if r.get("paar") == paar]
    eigene.sort(key=lambda r: _zeit(r.get("zu_zeit")) or jetzt)

    # 1. Sperrfrist nach einem ZIEL-Ausstieg (Haus: 2 h, scanner).
    frist = _zahl(g.get("sperrfrist_ziel_stunden")) or 0.0
    if frist > 0:
        for r in reversed(eigene):
            if (r.get("grund") or "").lower() not in ZIEL_GRUENDE:
                continue
            zu = _zeit(r.get("zu_zeit"))
            if zu and jetzt - zu < timedelta(hours=frist):
                return (False, ("Ziel-Ausstieg vor %.1f h (< %.1f h Sperrfrist)"
                               % ((jetzt - zu).total_seconds() / 3600.0, frist)),
                        "sperrfrist_ziel")
            break

    # 2. Abklingzeit nach einem STOP (Haus: 4 Tage, scanner).
    frist = _zahl(g.get("sperrfrist_stop_stunden")) or 0.0
    if frist > 0:
        for r in reversed(eigene):
            if (r.get("grund") or "").lower() not in STOP_GRUENDE:
                continue
            zu = _zeit(r.get("zu_zeit"))
            if zu and jetzt - zu < timedelta(hours=frist):
                return (False, ("Stop vor %.1f h (< %.1f h Abklingzeit)"
                               % ((jetzt - zu).total_seconds() / 3600.0, frist)),
                        "sperrfrist_stop")
            break

    # 3. Mindestabstand zwischen zwei Einstiegen desselben Paares.
    frist = _zahl(g.get("mindestabstand_einstieg_stunden")) or 0.0
    if frist > 0 and eigene:
        zu = _zeit(eigene[-1].get("zu_zeit"))
        if zu and jetzt - zu < timedelta(hours=frist):
            return (False, ("letzte Runde vor %.1f h (< %.1f h Mindestabstand)"
                           % ((jetzt - zu).total_seconds() / 3600.0, frist)),
                    "mindestabstand")

    # 4. Grenzen des GANZEN Buchs im Fenster (risk_agent, ohne Sprachmodell).
    fenster = _zahl(g.get("fenster_stunden")) or 0.0
    if fenster > 0:
        grenze = jetzt - timedelta(hours=fenster)
        drin = [r for r in runden
                if (_zeit(r.get("zu_zeit")) or jetzt) >= grenze]
        ergebnis = sum(_zahl(r.get("ergebnis_usd")) or 0.0 for r in drin)
        einsatz = sum(_zahl(r.get("einsatz_usd")) or 0.0 for r in drin)
        verlust_usd = _zahl(g.get("verlust_max_usd"))
        gewinn_usd = _zahl(g.get("gewinn_ziel_usd"))
        verlust_pct = _zahl(g.get("verlust_max_pct"))
        gewinn_pct = _zahl(g.get("gewinn_ziel_pct"))
        if verlust_usd and ergebnis <= -abs(verlust_usd):
            return (False, ("Verlust %.2f USD im %.0f-h-Fenster (Grenze -%.2f)"
                            % (ergebnis, fenster, abs(verlust_usd))),
                    "verlust_usd")
        if gewinn_usd and ergebnis >= abs(gewinn_usd):
            return (False, ("Gewinnziel %.2f USD im %.0f-h-Fenster erreicht"
                            % (ergebnis, fenster)), "gewinn_usd")
        if einsatz > 0 and verlust_pct and ergebnis / einsatz * 100.0 <= -abs(verlust_pct):
            return (False, ("Verlust %.2f %% des Einsatzes im %.0f-h-Fenster "
                            "(Grenze -%.2f %%)"
                            % (ergebnis / einsatz * 100.0, fenster, abs(verlust_pct))),
                    "verlust_pct")
        if einsatz > 0 and gewinn_pct and ergebnis / einsatz * 100.0 >= abs(gewinn_pct):
            return (False, ("Gewinn %.2f %% des Einsatzes im %.0f-h-Fenster "
                            "(Ziel %.2f %%)"
                            % (ergebnis / einsatz * 100.0, fenster, abs(gewinn_pct))),
                    "gewinn_pct")

    # 5. Hoechstzahl Einstiege desselben Paares im Fenster.
    deckel = int(_zahl(g.get("max_einstiege_je_paar_im_fenster")) or 0)
    if deckel > 0:
        fenster = _zahl(g.get("fenster_stunden")) or 0.0
        grenze = jetzt - timedelta(hours=fenster)
        n = sum(1 for r in eigene
                if (_zeit(r.get("auf_zeit")) or jetzt) >= grenze)
        if n >= deckel:
            return (False, ("%d Einstiege im %.0f-h-Fenster (Deckel %d)"
                            % (n, fenster, deckel)), "max_einstiege")
    return True, "Bremse frei", "frei"


def lage(runden, jetzt, paar, g):
    """Kurzbild fuer Berichte - rechnet, urteilt nicht."""
    erlaubt, grund, regel = urteil(runden, jetzt, paar, g)
    return {"bremse": bool(g.get("bremse", True)), "erlaubt": erlaubt,
            "grund": grund, "regel": regel, "runden_gesamt": len(runden),
            "runden_paar": sum(1 for r in runden if r.get("paar") == paar)}