#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wache auf die jungen Papierspuren trendwende_btc, liq_wand, supertrend, iv_waelle.

WARUM: Die Spuren warten auf ein SELTENES Tor. trendwende_btc braucht einen
SuperTrend-Wechsel +1 -> -1 unter der EMA200 (3x in den letzten 200 Kerzen),
liq_wand einen Liquidations-Cluster mit 30 % der Menge in einem Band, hoechstens
2 % entfernt, supertrend einen Wechsel auf der letzten Kerze, iv_waelle eine
handelbare Optionswand mit dem Kurs in Reichweite. Nachsehen waere Warten auf
ein Ereignis, das tagelang ausbleibt.

DAZU SEIT 22.09.2026: supertrend und iv_waelle (Auftrag Max). Bei beiden ist
Stille der Normalfall — supertrend stand nach einem stillen ImportError fuenf
Tage still, ohne dass es auffiel, und iv_waelle hat seit dem 19.09. keine Zeile
geschrieben. Ohne Wache ist "wartet korrekt" nicht von "kaputt" zu
unterscheiden.

Gemeldet wird je Spur NUR, was neu ist:
  1. jeder neue EINSTIEG (der erste ist die Antwort auf "greift die Regel?"),
  2. jede geschlossene RUNDE mit G/V und Grund (Stop, Ziel, Frist, Rueckdreh),
  3. ein ZURUECKGEHALTENES Signal - das ist kein Fehler, sondern die Regel bei
     der Arbeit. Bei trendwende_btc: Wende da, aber Schluss ueber der EMA200.
     Bei liq_wand: Cluster da, aber zu weit weg oder zu duenn. Einmal je
     Ereignis, nicht oefter,
  4. ein STILLSTAND: der Zyklus schreibt alle ~6,5 min, gemeldet wird erst ab
     45 min ohne Lauf (dann laeuft der Dauerlauf nicht oder die Spur bricht ab).

LEERE AUSGABE = nichts senden (Watchdog-Muster). Zustand je Spur in
Agenten/Hermes/cache/spur-wache-<spur>.json.

Aufruf (Hermes-Cron, no_agent, alle 30 Minuten):
    python spur-wache.py                 # beide Spuren
    python spur-wache.py --nur liq_wand  # eine davon
    python spur-wache.py --jetzt         # zeigen, nichts schreiben
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

HERMES = Path(__file__).resolve().parents[1]
HANDEL = HERMES.parents[0] / "Handel"
CACHE = HERMES / "cache"

EINSTIEG = ("kauf", "eroeffnen", "EINSTIEG")
AUSSTIEG = ("verkauf", "schliessen", "AUSSTIEG")
STILL_MIN = 45          # ~sieben verpasste Laeufe bei ~6,5 min Takt


# --- Lesen ----------------------------------------------------------------

def _lies(pfad: Path):
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _zeilen(pfad: Path):
    try:
        with pfad.open(encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception:
        return []


def _zahl(wert):
    try:
        return float(wert)
    except (TypeError, ValueError):
        return None


def _spur_laden(spur: str):
    """Das handeln.py DER SPUR laden - nicht irgendein gleichnamiges Modul.

    REIHENFOLGE ZAEHLT: jedes insert(0, ...) draengt sich vor. Stuende die
    eigene Spur zuerst, laege am Ende scanner/ vorn und 'import handeln' holte
    scanner/handeln.py - genau das ist beim Bau der ersten Wache passiert.
    Deshalb die eigene Spur ZULETZT und danach gegen __file__ pruefen.
    """
    ordner = HANDEL / spur
    for p in (HANDEL / "scanner", HANDEL / "xperp", ordner):
        if str(p) in sys.path:
            sys.path.remove(str(p))
        sys.path.insert(0, str(p))
    for name in ("handeln", "indikatoren"):
        sys.modules.pop(name, None)
    import handeln as mod                                       # noqa: E402
    if not str(Path(mod.__file__).resolve()).startswith(str(ordner)):
        raise ImportError("falsches Modul geladen (%s)" % mod.__file__)
    return mod


# --- Zurueckgehaltene Signale ---------------------------------------------

def _zurueck_trendwende(w):
    """(kennung, text), wenn der SuperTrend dreht, die EMA200 aber blockt."""
    try:
        spur = _spur_laden("trendwende_btc")
        import indikatoren as xi                                # noqa: E402
    except Exception as e:
        return None, "Indikatoren nicht ladbar: %s" % e

    # Die Kerzen holt die SPUR selbst (quelle()) - damit rechnet die Wache auf
    # denselben Daten wie der Zyklus. quelle() gibt (daten, kurse, fehler).
    try:
        daten, _kurse, fehler = spur.quelle(w)
    except Exception as e:
        return None, "Kerzen nicht abrufbar: %s" % e
    if fehler:
        return None, "Kerzen nicht abrufbar: %s" % "; ".join(fehler)

    inst = w.get("instrument", "BTC-USDT-SWAP")
    k = (daten.get(inst) or {}).get("kerzen") or []
    if len(k) < 220:
        return None, None
    k = k[:-1]                                  # letzte Kerze laeuft noch
    _, richtung = xi.supertrend(
        k, n=int(w.get("supertrend_n", 10)),
        faktor=float(w.get("supertrend_faktor", 3.0)))
    if not (len(richtung) >= 2 and richtung[-2] == 1 and richtung[-1] == -1):
        return None, None

    schluss = [float(z[4]) for z in k]
    ema = xi.ema(schluss, int(w.get("ema_filter_n", 200)))
    if ema[-1] is None or schluss[-1] < float(ema[-1]):
        return None, None                       # Signal - die Spur handelt
    return (str(k[-1][0]),
            "trendwende_btc: Trend gedreht (+1 -> -1), aber Schluss %.0f liegt "
            "UEBER der EMA200 %.0f - der Filter haelt zurueck (Ruecksetzer im "
            "Aufwaertstrend, kein Short)."
            % (schluss[-1], float(ema[-1])))


def _zurueck_liqwand(w):
    """(kennung, text), wenn ein Cluster da ist, aber ein Tor zu bleibt.

    Rechnet mit spur.wand() - derselben Funktion wie signal(). Eine nachgebaute
    Bandrechnung wuerde die Nachbildung pruefen, nicht die Spur.
    """
    try:
        spur = _spur_laden("liq_wand")
    except Exception as e:
        return None, "liq_wand nicht ladbar: %s" % e
    try:
        daten, _kurse, fehler = spur.quelle(w)
    except Exception as e:
        return None, "Liquidationen nicht abrufbar: %s" % e
    if fehler:
        return None, "Liquidationen nicht abrufbar: %s" % "; ".join(fehler)

    inst = w.get("instrument", "BTC-USDT-SWAP")
    d = daten.get(inst) or {}
    if spur.signal(d, w):
        return None, None                       # Tor offen - die Spur handelt

    spot = float(d.get("spot") or 0)
    liqs = d.get("liqs") or []
    mind_n = int(w.get("mindest_liquidationen", 20))
    if spot <= 0:
        return None, None
    if len(liqs) < mind_n:
        # Kein Befund, sondern Datenlage - taeglich melden waere Rauschen.
        return None, None

    treffer = spur.wand(liqs, spot, float(w.get("bandbreite_prozent", 0.25)))
    if not treffer:
        return None, None
    preis, menge, seite = treffer

    gesamt = 0.0
    for x in liqs:
        try:
            gesamt += float(x.get("kontrakte") or 0)
        except (TypeError, ValueError):
            pass
    anteil = (menge / gesamt) if gesamt > 0 else 0.0
    abstand = abs(preis / spot - 1) * 100
    mind_anteil = float(w.get("mindest_anteil", 0.30))
    max_ab = float(w.get("max_abstand_prozent", 2.0))

    gruende = []
    if anteil < mind_anteil:
        gruende.append("Cluster zu duenn (%.0f %% der Menge, noetig %.0f %%)"
                       % (anteil * 100, mind_anteil * 100))
    if abstand > max_ab:
        gruende.append("Wand zu weit weg (%.2f %%, erlaubt %.2f %%)"
                       % (abstand, max_ab))
    if not gruende:
        # Beide Tore offen, trotzdem kein Signal: die Wand liegt auf der
        # falschen Seite (Kaufdruck unter dem Spot laeuft ins Leere).
        gruende.append("Wand auf der falschen Seite (%s-Liquidationen %s dem "
                       "Spot)" % (seite, "unter" if preis < spot else "ueber"))
    kennung = "%s|%.0f" % (dt.datetime.now(dt.timezone.utc)
                           .strftime("%Y-%m-%d %H"), preis)
    return kennung, ("liq_wand: Wand bei %.0f (Spot %.0f), aber %s."
                     % (preis, spot, "; ".join(gruende)))


def _zurueck_supertrend(w):
    """(kennung, text), wenn der SuperTrend dreht, aber kein Einstieg entstand.

    supertrend handelt NUR beim Wechsel auf der letzten Kerze (+1 -> -1 oder
    -1 -> +1, siehe `signal()`). Bleibt der Einstieg aus, obwohl die Wende da
    ist, liegt es an einer Kapazitaetsgrenze: Buch voll oder ATR nicht
    rechenbar. Genau dieser Fall ist die Antwort auf "wartet die Spur richtig
    oder ist sie kaputt?" - fuenf Tage signalfrei sah vor dem ImportFix
    genauso aus wie ein seltener Wechsel.
    """
    try:
        spur = _spur_laden("supertrend")
    except Exception as e:
        return None, "supertrend nicht ladbar: %s" % e
    inst = w.get("instrument", "BTC-USDT-SWAP")
    try:
        k = spur.lade_kerzen(inst, w.get("kerzen_takt", "1H"),
                             int(w.get("mindest_kerzen", 300)) + 60)
    except Exception as e:
        return None, "Kerzen nicht abrufbar: %s" % e
    if not k or len(k) < int(w.get("mindest_kerzen", 300)):
        return None, None
    idx = len(k) - 1                      # dieselbe Kerze wie der Zyklus
    sig = spur.signal(k, idx)
    if not sig:
        return None, None                 # keine Wende - Ruhe, kein Befund
    seite, _linie = sig
    kurs = float(k[idx][4])

    z = _lies(HANDEL / "supertrend" / "zustand.json")
    offen = len(z.get("positionen") or [])
    grenze = int(w.get("max_offene_positionen", 4))
    if offen >= grenze:
        warum = "Buch voll (%d von %d)" % (offen, grenze)
    else:
        atr = spur.atr_abs(k, idx, 14)
        warum = ("ATR nicht rechenbar" if not atr or atr <= 0
                 else "Kapazitaet frei, aber kein Einstieg gebucht")
    kennung = "%s|%s" % (str(k[idx][0]), seite)
    return (kennung,
            "supertrend: Wende %s bei %.2f auf der letzten Kerze, aber kein "
            "Einstieg - %s. Der Papierlauf greift also nur, wenn Platz ist."
            % (seite.upper(), kurs, warum))


def _zurueck_ivwaelle(w):
    """(kennung, text), wenn eine HANDELBARE Wand da ist, der Kurs aber fehlt.

    Die Regel (siehe `iv_waelle.signal`): Einstieg nur, wenn der laufende Kurs
    hoechstens `naehe_prozent` von der Wand entfernt steht UND die Wand
    handelbar ist (zwischen Grenze und 3 Sigma, siehe `wandelage`). Steht eine
    handelbare Wand da und der Kurs ist noch weit weg, ist das der Fall, auf
    den die Spur wartet - einmal je Tag und Wand gemeldet, nicht je Zyklus.
    """
    try:
        spur = _spur_laden("iv_waelle")
    except Exception as e:
        return None, "iv_waelle nicht ladbar: %s" % e
    try:
        daten, _kurse, fehler = spur._hole_markt(w)
    except Exception as e:
        return None, "Markt nicht abrufbar: %s" % e
    if fehler:
        # Datenlage, kein Signal - nicht taeglich melden (wie bei liq_wand).
        return None, None
    inst = w.get("instrument", "BTC-PERPETUAL")
    d = daten.get(inst) or {}
    if not d.get("spot"):
        return None, None
    try:
        sig = spur.spanne_und_signal(d, w)
    except Exception as e:
        return None, "Signal nicht rechenbar: %s" % e
    if sig.get("richtung") and sig["richtung"] != "kein_signal":
        return None, None                 # die Spur handelt
    spot = float(sig.get("spot") or d["spot"])
    naehe = float(w.get("naehe_prozent", 0.5))
    for name, lage in sorted((sig.get("lagen") or {}).items()):
        if not isinstance(lage, dict) or lage.get("lage") != "handelbar":
            continue                      # keine Wand / Rauschen / unerreichbar
        strike = float(lage.get("strike") or 0)
        if strike <= 0:
            continue
        abstand = abs(strike - spot) / spot * 100.0
        if abstand <= naehe:
            continue                      # Nah genug - dann haette sie gehandelt
        kennung = "%s|%s|%.0f" % (dt.datetime.now(dt.timezone.utc)
                                  .strftime("%Y-%m-%d"), name, strike)
        return (kennung,
                "iv_waelle: handelbare Wand %s bei %.0f (%.1f Sigma), der Kurs "
                "steht %.2f %% entfernt - noetig sind hoechstens %.2f %%. "
                "Warten auf die Naehe ist die Regel, kein Fehler."
                % (name, strike, float(lage.get("abstand_sigma") or 0),
                   abstand, naehe))
    return None, None


def _zurueck_nautilus_emacross(w):
    """(kennung, text) fuer den EMA-Wechsel - die SIGNALEITE dieser Spur.

    Der Rueckgabewert ist die EMA-Richtung als Kennung, damit die Wache
    einmal je Wechsel meldet und nicht bei jedem Zyklus. Gemeldet wird,
    was man sonst nicht sieht:

    * die Seite, in der die schnelle EMA gerade liegt (long/short) - die
      Spur schweigt bei stabiler Lage, und Stille ist von einem kaputten
      Kerzenabruf nicht zu unterscheiden,
    * ein fehlender oder leerer Queue-Eintrag - der Dauerlauf meldet einen
      Wechsel nur in die Queue, und eine fehlende Datei heisst, es gab
      noch keinen.

    Die Kennung traegt Zeit UND Seite: sonst wuerde ein Wechsel long->short
    ->long innerhalb einer Nacht als derselbe Zustand gelten.
    """
    z = _lies(HANDEL / "nautilus_emacross" / "zustand.json")
    seite = (z.get("vor_signal") or {})
    jetzige = list(seite.values())[0] if seite else None
    if not jetzige:
        return None, ("nautilus_emacross: noch keine EMA-Richtung im Zustand "
                      "- die Spur hat seit dem Neustart nicht gerechnet oder "
                      "hat noch keine 40 abgeschlossenen 1H-Kerzen")
    wartend = []
    for name in ("signal_queue.json", "signal_queue.mittel.json",
                 "signal_queue.hoch.json"):
        pfad = HANDEL / "nautilus_emacross" / name
        if pfad.is_file():
            try:
                wartend.extend(json.loads(pfad.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
    zusatz = ""
    if wartend:
        letzte = wartend[-1]
        zusatz = (" | %d Auftrag/Auftraege in der Queue, letzter %s %s %s"
                  % (len(wartend), letzte[0], letzte[1],
                     (letzte[3] or "")[11:16] if len(letzte) > 3 else ""))
    return "%s@%s" % (jetzige, (z.get("letzter_lauf") or "")[:16]), (
        "nautilus_emacross: EMA(10/20) zeigt %s%s"
        % (jetzige.upper(), zusatz))


def _zurueck_queue(spur):
    """(kennung, text) fuer jede Spur, die ueber die Queue Einstiege erzeugt.

    Diese Form braucht keine eigene Regel je Spur: sie liest das, was die
    Spur selbst geschrieben hat. Gemeldet wird der Wechsel - also die Seite
    gegenueber dem letzten gemeldeten Stand - und der Zaehler der wartenden
    Auftraege. Eine Spur ohne Warteschlange meldet nichts; eine Spur mit
    Warteschlange und WITHOUT Freigabe meldet genau das, denn das ist der
    Zustand, den man sonst woertlich nicht sieht: die Spur arbeitet, der
    Auftrag wartet, und niemand hat es gemerkt.

    Angewendet auf moondev_signalwelle und moondev_topmovers - beide legen
    ueber spur_buch eine Queue an, beide hatten keine Wache. Das fiel am
    03.10.2026 nicht durch einen Fehler auf, sondern durch einen Test, der
    eine feste Zahl Spuren eingefroren hatte und deshalb bei der neuen
    EMA-Spur kippte.
    """
    ordner = HANDEL / spur
    z = _lies(ordner / "zustand.json")
    wartend, aktueller = [], None
    for name in ("signal_queue.json", "signal_queue.mittel.json",
                 "signal_queue.hoch.json"):
        pfad = ordner / name
        if not pfad.is_file():
            continue
        try:
            q = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        wartend.extend(q if isinstance(q, list) else [])
    vor = z.get("vor_signal") or {}
    if vor:
        aktueller = "%s %s" % (list(vor)[0], list(vor.values())[0])
    if not aktueller and not wartend:
        return None, ("%s: noch keine EMA-/Signalrichtung und keine Warteschlange "
                      "- die Spur hat seit dem Neustart nicht gerechnet" % spur)
    teile = []
    if aktueller:
        teile.append("Signal %s" % aktueller)
    if wartend:
        teile.append("%d Auftrag/Auftraege warten (Ausfuehrung nur mit Freigabe)"
                     % len(wartend))
    else:
        teile.append("keine wartenden Auftraege")
    kennung = "%s|%d|%s" % (aktueller or "-", len(wartend),
                            (z.get("letzter_lauf") or "")[:16])
    return kennung, "%s: %s" % (spur, " | ".join(teile))


SPUREN = {
    "trendwende_btc": _zurueck_trendwende,
    "liq_wand": _zurueck_liqwand,
    "supertrend": _zurueck_supertrend,
    "iv_waelle": _zurueck_ivwaelle,
    "nautilus_emacross": _zurueck_nautilus_emacross,
    "moondev_signalwelle": lambda w: _zurueck_queue("moondev_signalwelle"),
    "moondev_topmovers": lambda w: _zurueck_queue("moondev_topmovers"),
    "moondev_listingarb": lambda w: _zurueck_queue("moondev_listingarb"),
    "moondev_marktlage": lambda w: _zurueck_queue("moondev_marktlage"),
    "omnitrade": lambda w: _zurueck_queue("omnitrade"),
    "omnitrade_futures": lambda w: _zurueck_queue("omnitrade_futures"),
}


# --- Eine Spur pruefen ----------------------------------------------------

def pruefe(spur: str, schreiben: bool = True):
    ordner = HANDEL / spur
    stand_datei = CACHE / ("spur-wache-%s.json" % spur)
    stand = _lies(stand_datei)
    neu = dict(stand)
    meldungen = []

    w = _lies(ordner / "wachen.json")
    rows = _zeilen(ordner / "handelsjournal.csv")
    ein = [r for r in rows if (r.get("aktion") or "").strip() in EINSTIEG]
    aus = [r for r in rows if (r.get("aktion") or "").strip() in AUSSTIEG]

    n_ein = int(stand.get("einstiege", 0))
    n_aus = int(stand.get("ausstiege", 0))
    neu["einstiege"], neu["ausstiege"] = len(ein), len(aus)

    # 1. Einstiege
    for r in ein[n_ein:]:
        preis = _zahl(r.get("preis"))
        kopf = "%s: ERSTER EINSTIEG" if n_ein == 0 else "%s: EINSTIEG"
        meldungen.append(
            (kopf % spur) + " %s %s zu %s (Einsatz %s USD, Stop %s, Ziel %s) %s"
            % (r.get("richtung") or r.get("seite") or "",
               r.get("inst") or "?",
               ("%.4f" % preis) if preis is not None else "?",
               r.get("einsatz_usd") or "?", r.get("stop") or "?",
               r.get("ziel") or "?", (r.get("zeit") or "")[:16]))

    # 2. Geschlossene Runden
    for r in aus[n_aus:]:
        gv = _zahl(r.get("gv_usd")) or _zahl(r.get("gv")) or 0.0
        meldungen.append(
            "%s: RUNDE ZU %s - G/V %+.2f USD, Grund %s %s"
            % (spur, r.get("inst") or "?", gv, r.get("grund") or "?",
               (r.get("zeit") or "")[:16]))

    # 3. Zurueckgehaltenes Signal - einmal je Ereignis
    kennung, text = SPUREN[spur](w)
    if text and kennung is None:
        meldungen.append("%s: %s" % (spur, text))          # echter Fehler
    elif kennung and kennung != stand.get("zurueck"):
        meldungen.append(text)
        neu["zurueck"] = kennung

    # 4. Stillstand
    z = _lies(ordner / "zustand.json")
    letzter = z.get("letzter_lauf")
    if letzter:
        try:
            t = dt.datetime.fromisoformat(str(letzter).replace("Z", "+00:00"))
            if t.tzinfo is None:
                t = t.replace(tzinfo=dt.timezone.utc)
            alt = (dt.datetime.now(dt.timezone.utc) - t).total_seconds() / 60
            if alt > STILL_MIN:
                if not stand.get("still"):
                    meldungen.append(
                        "%s: STILLSTAND - letzter Zyklus vor %d min "
                        "(erwartet alle ~6,5 min). Laeuft der Dauerlauf?"
                        % (spur, int(alt)))
                neu["still"] = True
            else:
                if stand.get("still"):
                    meldungen.append("%s: laeuft wieder (Zyklus vor %d min)."
                                     % (spur, int(alt)))
                neu["still"] = False
        except Exception:
            pass

    if schreiben and neu != stand:
        CACHE.mkdir(parents=True, exist_ok=True)
        stand_datei.write_text(json.dumps(neu, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    return meldungen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nur", choices=sorted(SPUREN))
    ap.add_argument("--jetzt", action="store_true",
                    help="zeigen, nichts schreiben")
    a = ap.parse_args()

    alle = []
    for spur in ([a.nur] if a.nur else sorted(SPUREN)):
        try:
            alle += pruefe(spur, schreiben=not a.jetzt)
        except Exception as e:
            alle.append("%s: Wache selbst gescheitert - %s" % (spur, e))
    if alle:
        print("\n".join(alle))


if __name__ == "__main__":
    main()
