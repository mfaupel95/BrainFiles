"""Freigabe-Beleg: die EINE Erlaubnis, mit der ein MCP-Werkzeug eine Order ausfuehren darf.

Das Problem, das dieses Modul loest
-----------------------------------
Der Kraken-MCP-Server hat ein Order-Werkzeug, und ein Werkzeug ist aus JEDER
Sitzung aufrufbar - aus einem Chat, aus einem Bot, aus einer A2A-Nachricht. Die
Sperrenkette der Spuren (Freigabefenster, Herzschlag, Stop, Kill-Switch,
Deckel, Journal) haengt aber am Skript, nicht am Werkzeug. Deshalb steht im
Handelsregelwerk: der MCP bleibt lesend.

Dieses Modul ist der Ausweg, ohne die Regel zu brechen: der MCP darf ausfuehren,
aber NUR, was eine Spur vorher beschlossen und belegt hat.

    Spur (Entscheidung, unter allen Wachen)  ->  Beleg  ->  MCP (Hand)

Der Beleg ist an eine Spur, eine Seite, ein Paar, eine Hoechstmenge, einen
Hoechstpreis und eine kurze Frist gebunden und ist EINMALIG (nach dem
Ausfuehren verbraucht). Er kann nur entstehen, solange das Freigabefenster
dieser Spur offen ist - und ein Fenster oeffnet nur der laufende Dauerlauf,
wenn das Fenster der EINZIGE fehlende Grund ist. Ein Chat kann sich damit
KEINE Erlaubnis ausstellen: `schreibe()` verweigert ohne offenes Fenster.

Fail-closed: fehlende, kaputte, abgelaufene, verbrauchte oder nicht passende
Belege sind eine ABSAGE - nie eine stille Ausnahme, nie ein Ersatzwert.

Ausstiege sind NICHT belegt-pflichtig: Stop, Ziel und Notaus laufen weiter
ueber den eigenen Orderweg der Spur (kraken/kraken.py). Wer diesen Weg
verriegelt, verriegelt den Notausstieg.
"""
from __future__ import annotations

import importlib.util
import json
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

HIER = os.path.dirname(os.path.abspath(__file__))          # .../Agenten/Handel
CACHE = os.path.join(HIER, "cache", "freigabebelege")

# Frist eines Belegs: kurz. Er ist eine Hand, die einen beschlossenen Auftrag
# ausfuehrt - kein Dauer-Schluessel.
GUELTIG_SEKUNDEN = 600  # > Cron-Takt (5 min), sonst verfallen Belege vor dem naechsten Handler

# Mengen- und Preistoleranz: die Boerse rundet, die Rechnung der Spur nicht.
# 0,1 % ist Rundung, nicht Ermessen - eine groessere Order ist eine andere
# Order und braucht einen neuen Beleg.
TOLERANZ = 0.001


def _lade(name: str, pfad: str):
    """Ein Nachbarmodul ueber den PFAD laden (Hausmuster, kein sys.path-Eintrag).

    Der Schluessel im Modul-Cache enthaelt den PFAD. Ohne ihn teilten zwei
    verschiedene Ordner denselben Eintrag: wer zuerst `freigabefenster` laedt,
    bestimmt fuer den ganzen Prozess, aus welchem Ordner es kommt - im Betrieb
    (MCP + Spur im selben Prozessbaum) waere das die falsche Fensterdatei.
    """
    schluessel = "%s@%s" % (name, os.path.abspath(pfad))
    if schluessel in sys.modules:
        return sys.modules[schluessel]
    spec = importlib.util.spec_from_file_location(schluessel, pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[schluessel] = modul
    spec.loader.exec_module(modul)
    return modul


def _fenster():
    return _lade("freigabefenster", os.path.join(HIER, "freigabefenster.py"))


def _jetzt() -> datetime:
    return datetime.now(timezone.utc)


def _ordner(spur: str | None = None) -> str:
    return CACHE if spur is None else os.path.join(CACHE, spur if spur else "_ohne_spur")


def datei(spur: str) -> str:
    return os.path.join(CACHE, "%s.json" % spur)


def _wachen_handel_erlaubt(spur: str):
    """handel_erlaubt aus der wachen.json der Spur - None, wenn nicht lesbar.

    Absichtlich ueber den Dateipfad und nicht ueber die Spur-Module: die MCP-
    Seite importiert keine Spur, sie liest nur die Regeldatei.
    """
    kandidaten = [os.path.join(HIER, spur, "wachen.json"),
                  os.path.join(HIER, spur, "wachen.live.json")]
    for k in kandidaten:
        try:
            with open(k, encoding="utf-8") as f:
                return bool(json.load(f).get("handel_erlaubt"))
        except (OSError, ValueError):
            continue
    return None


def offener(spur: str) -> dict | None:
    """Der noch GUELTIGE, unverbrauchte Beleg einer Spur - sonst None.

    Warum es diese Funktion gibt (Befund T-283, 01.10.2026): Eine Spur hat
    genau EINE Belegdatei. `schreibe()` hat den alten Beleg bisher STILL
    ueberschrieben. Im Zyklus vom 01.10.2026 11:25:51 stellte die kraken-Spur
    deshalb NEUN Belege in einem Lauf aus (ALGO/AVAX/LINK/TRX/DOT/SUI/LTC/ADA/
    SOL, je 50 EUR = 450 EUR Absicht bei max_gesamt_eur 200) und schrieb neun
    `kauf_beleg`-Zeilen ins Journal - ausgefuehrt werden konnte aber nur der
    LETZTE (SOLEUR), weil die vorherigen acht mit dem naechsten `schreibe()`
    verschwanden. Journal und Belegdatei erzaehlten also zwei Geschichten.
    """
    d = lies(spur)
    if not d or d.get("verbraucht"):
        return None
    try:
        if _jetzt() <= datetime.fromisoformat(str(d.get("gueltig_bis"))):
            return d
    except ValueError:
        return None
    return None


def verfallene() -> list[dict]:
    """Abgelaufene, NICHT verbrauchte Belege - die verpassten Auftraege.

    Sie sind kein Schaden (ein verfallener Beleg kauft nicht), aber sie sind
    unsichtbar: `offene()` laesst sie weg, und niemand sonst sieht nach. Der
    Handler meldet sie einmal (Feld `verfallen_gemeldet`).
    """
    ergebnis = []
    if not os.path.isdir(CACHE):
        return ergebnis
    for name in sorted(os.listdir(CACHE)):
        if not name.endswith(".json"):
            continue
        spur = name[:-len(".json")]
        d = lies(spur)
        if not d or d.get("verbraucht") or d.get("verfallen_gemeldet"):
            continue
        try:
            if _jetzt() > datetime.fromisoformat(str(d.get("gueltig_bis"))):
                ergebnis.append(d)
        except ValueError:
            continue
    return ergebnis


def merke_verfallen(spur: str, grund: str = "") -> bool:
    """Einen verfallenen Beleg als gemeldet kennzeichnen (kein zweites Mal)."""
    d = lies(spur)
    if not d:
        return False
    d["verfallen_gemeldet"] = _jetzt().isoformat(timespec="seconds")
    if grund:
        d["verfallen_grund"] = grund
    try:
        with open(datei(spur), "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return True
    except OSError:
        return False


def schreibe(spur: str, seite: str, paar: str, menge: float, preis_max: float,
             grund: str, gueltig_sekunden: int = GUELTIG_SEKUNDEN,
             preis_min: float | None = None, zusatz: dict | None = None) -> dict:
    """Einen Beleg ausstellen. Verweigert, wenn die Spur nicht freigegeben ist.

    Rueckgabe: der Beleg als dict. Bei Verweigerung: {"ok": False, "grund": ...}.
    Es wird nie ein Beleg ausgestellt, der nicht durch die Sperrenkette der
    Spur gedeckt ist - das ist der ganze Zweck dieses Moduls.
    """
    if not spur or seite not in ("buy", "sell") or not paar or menge <= 0:
        return {"ok": False, "grund": "unvollstaendige Angabe - kein Beleg"}

    fenster = _fenster()
    try:
        # _fenster() liefert das MODUL, nicht ein Fenster. Die Frage "ist fuer
        # DIESE Spur ein Fenster offen?" beantwortet lade(spur).offen().
        # Mit fenster.offen(spur) schlug JEDER Beleg fehl ("Freigabefenster
        # nicht lesbar") - und damit war der einzige sanktionierte Orderweg
        # (MCP kraken_order_mit_beleg) tot, ohne dass es auffiel: die Spur
        # verbuchte es als normalen Sperrgrund. Gefunden am 24.09.2026.
        offen = bool(fenster.lade(spur).offen())
    except Exception as e:                                        # noqa: BLE001
        return {"ok": False, "grund": "Freigabefenster nicht lesbar (%s)" % e}
    if not offen:
        # DER KERN: ohne offenes Fenster gibt es keinen Beleg. Ein Chat kann
        # kein Fenster oeffnen - `freigabefenster.oeffnen` verweigert ohne
        # wartende Anfrage, und die stellt nur der laufende Dauerlauf.
        return {"ok": False, "grund": "kein offenes Freigabefenster fuer %s" % spur}

    erlaubt = _wachen_handel_erlaubt(spur)
    if not erlaubt:
        return {"ok": False,
                "grund": "handel_erlaubt=%s in %s/wachen.json - kein Beleg"
                         % ("false" if erlaubt is False else "nicht lesbar", spur)}

    # Eine Spur hat hoechstens EINEN offenen Beleg. Der neue ERSETZT den alten
    # nicht mehr, er wird abgelehnt: ein gueltiger Beleg ist eine offene
    # Entscheidung, die noch ausgefuehrt werden kann - ihn zu ueberschreiben
    # hiesse, sie wegzuwerfen, und genau das hat am 01.10.2026 acht von neun
    # Belegen eines Zyklus verschluckt (T-283). Ein abgelaufener Beleg
    # blockiert nicht: `offener()` laesst ihn durchfallen.
    vorher = offener(spur)
    if vorher:
        return {"ok": False,
                "grund": "es liegt schon ein offener Beleg fuer %s (%s %s, "
                         "gueltig bis %s) - erst ausfuehren oder ablaufen lassen"
                         % (spur, vorher.get("seite"), vorher.get("paar"),
                            vorher.get("gueltig_bis"))}

    jetzt = _jetzt()
    beleg = {
        "kennung": secrets.token_hex(16),
        "spur": spur,
        "seite": seite,
        "paar": paar.upper(),
        "menge": round(float(menge), 12),
        "preis_max": float(preis_max) if (seite == "buy" and preis_max is not None) else None,
        "preis_min": float(preis_min) if (seite == "sell" and preis_min is not None) else None,
        "grund": grund,
        "zusatz": zusatz or {},
        "erstellt": jetzt.isoformat(timespec="seconds"),
        "gueltig_bis": (jetzt + timedelta(seconds=int(gueltig_sekunden))).isoformat(timespec="seconds"),
        "verbraucht": None,
    }
    os.makedirs(CACHE, exist_ok=True)
    # Hier steht genau EIN Beleg je Spur (die Datei <spur>.json). Ein noch
    # gueltiger Beleg wird oben abgelehnt - hier landet nur ein neuer, wenn
    # keiner offen ist.
    with open(datei(spur), "w", encoding="utf-8", newline="\n") as f:
        json.dump(beleg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return beleg


def lies(spur: str) -> dict | None:
    """Den Beleg einer Spur lesen. None, wenn keiner da ist oder er kaputt ist."""
    try:
        with open(datei(spur), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def pruefe(beleg_kennung: str, spur: str, seite: str, paar: str,
           menge: float, preis: float | None = None) -> tuple[bool, str]:
    """Passt dieser Beleg zu GENAU dieser Order? (ok, grund).

    Reihenfolge ist Absicht: erst Existenz, dann Verbrauch, dann Frist, dann
    Inhalt. Alles, was nicht eindeutig passt, ist eine Absage.
    """
    d = lies(spur)
    if not d:
        return False, "kein Beleg fuer die Spur %s - der MCP darf hier nicht ausfuehren" % spur
    if not beleg_kennung or str(d.get("kennung")) != str(beleg_kennung):
        return False, "Beleg-Kennung passt nicht"
    if d.get("verbraucht"):
        return False, "Beleg schon verbraucht (%s)" % d.get("verbraucht")
    try:
        bis = datetime.fromisoformat(str(d.get("gueltig_bis")))
    except ValueError:
        return False, "Beleg ohne lesbare Frist - Absage"
    if _jetzt() > bis:
        return False, "Beleg abgelaufen (%s)" % d.get("gueltig_bis")
    if d.get("seite") != seite:
        return False, "Beleg gilt fuer %s, angefragt ist %s" % (d.get("seite"), seite)
    if str(d.get("paar", "")).upper() != str(paar).upper():
        return False, "Beleg gilt fuer %s, angefragt ist %s" % (d.get("paar"), paar)
    soll = float(d.get("menge") or 0.0)
    if menge > soll * (1.0 + TOLERANZ):
        return False, "Menge %.12g ueber dem Beleg (%.12g) - neue Entscheidung noetig" % (menge, soll)
    if seite == "buy" and d.get("preis_max") is not None and preis is not None:
        if preis > float(d["preis_max"]) * (1.0 + TOLERANZ):
            return False, "Preis %s ueber dem Beleg-Hoechstpreis %s" % (preis, d["preis_max"])
    if seite == "sell" and d.get("preis_min") is not None and preis is not None:
        if preis < float(d["preis_min"]) * (1.0 - TOLERANZ):
            return False, "Preis %s unter dem Beleg-Mindestpreis %s" % (preis, d["preis_min"])
    return True, "ok"


def verbrauche(spur: str, kennung: str, ergebnis: str = "") -> bool:
    """Den Beleg als verbraucht eintragen (einmalig). True, wenn es geklappt hat."""
    d = lies(spur)
    if not d or str(d.get("kennung")) != str(kennung):
        return False
    d["verbraucht"] = _jetzt().isoformat(timespec="seconds")
    if ergebnis:
        d["verbraucht_mit"] = ergebnis
    try:
        with open(datei(spur), "w", encoding="utf-8", newline="\n") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return True
    except OSError:
        return False


def protokolliere(spur: str, satz: dict) -> None:
    """Jede Ausfuehrung ueber den MCP wird protokolliert (Nachweis, kein Journal).

    Eigene Datei neben dem Beleg: das Handelsjournal der Spur fuehrt die
    Boerse, hier steht, WER ausgefuehrt hat (MCP statt Spur-Skript).
    """
    try:
        os.makedirs(CACHE, exist_ok=True)
        satz = dict(satz)
        satz.setdefault("zeit", _jetzt().isoformat(timespec="seconds"))
        with open(os.path.join(CACHE, "%s.ausgefuehrt.jsonl" % spur), "a",
                  encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(satz, ensure_ascii=False) + "\n")
    except OSError:
        pass


def offene() -> list[dict]:
    """Alle Belege, die noch gelten (lesend, fuer die Uebersicht im MCP)."""
    ergebnis = []
    if not os.path.isdir(CACHE):
        return ergebnis
    for name in sorted(os.listdir(CACHE)):
        if not name.endswith(".json"):
            continue
        d = lies(name[:-len(".json")])
        if not d or d.get("verbraucht"):
            continue
        try:
            if _jetzt() <= datetime.fromisoformat(str(d.get("gueltig_bis"))):
                ergebnis.append(d)
        except ValueError:
            continue
    return ergebnis