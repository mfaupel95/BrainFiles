"""Kraken-Abweisungs-Sonde: haelt einen ZEUGEN fest, wenn Kraken abweist.

Anlass (T-073, 25.09.2026): Zwischen etwa 00:29 und 01:33 wies Kraken JEDEN
signierten Aufruf ab - Spot mit ``EGeneral:Permission denied``, Futures mit
``authenticationError`` -, fuer jede nonce, mit zwei unabhaengigen Umsetzungen
(unser ``kraken_futures.py`` UND die offizielle kraken-cli). Danach heilte es
ohne Zutun. Die Ursache blieb offen, und zwar aus EINEM Grund: im ganzen Haus
existiert keine Aufzeichnung, die im Fehlerfall Statuscode, Header und
Rohantwort festhaelt. Ohne diese vier Angaben ist "Key kaputt" von
"Konto-Lockout" von "Cloudflare/IP" nicht zu unterscheiden.

Was diese Sonde deshalb tut - fuenf Wege je Lauf:

  1. offen_spot      GET  api.kraken.com/0/public/Time      (kein Schluessel)
  2. privat_spot     POST /0/private/Balance                (Haus-kraken.py)
  3. privat_futures  GET  futures.../api/v3/accounts        (kraken_futures)
  4. offen_futures   GET  futures.../api/v3/tickers         (kein Schluessel)
  5. roh_*           nur IM FEHLERFALL: derselbe Aufruf noch einmal mit
                     vollstaendiger Erfassung (HTTP-Status, Content-Type,
                     cloudflare-Header, Rohkoerper) - das ist der Zeuge.
                     Scheitert ein Zeuge mit ``EAPI:Invalid nonce``,
                     wiederholt die Sonde wie der Haus-Standard (``kraken.py``)
                     mit vorgeschobenem nonce-Pool (bis zu drei Versuche) -
                     ein fremdes Werkzeug auf demselben Schluessel darf den
                     Zeugen nicht faelschen.

Die Unterscheidung, auf die es ankommt:

  * nur die SIGNIERTEN Wege fallen, die oeffentlichen gehen
      -> Schluessel-/Konto-Ebene: Lockout, Rechte, Nonce.
         Kraken sperrt ein KONTO zeitweise ("EGeneral:Temporary lockout",
         ~15 Minuten), wenn zu viele fehlgeschlagene Aufrufe kamen - und
         "jeder Versuch setzt den Timer zurueck" (Kraken-Doku). Deshalb:
         nach einer Abweisung wird NICHT alle 15 Minuten weitergeklopft,
         sondern die Kuehlzeit (KUEHLZEIT_MIN) abgewartet.
  * alle Wege fallen, auch die oeffentlichen
      -> Netz, IP oder cloudflare (Kraken liefert dann 5xx/1020 statt JSON).

Speicherung:

  cache/kraken-abweisungen.jsonl   je Lauf EINE Zeile (kurz); im Fehlerfall
                                   zusaetzlich die vollen Rohdaten
  cache/kraken-abweisungs-sonde.json  Zustand: letzter Lauf, laufende
                                   Stoerung (Beginn), Kuehlzeit

Aufruf:

    python kraken_abweisungs_sonde.py            # ein Lauf, Textausgabe
    python kraken_abweisungs_sonde.py --wache    # leere Ausgabe, wenn gesund
    python kraken_abweisungs_sonde.py --stand    # nur den letzten Stand

Nur Standardbibliothek. Kein Schreibzugriff auf Kraken, keine Order.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import importlib.util
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HIER = os.path.dirname(os.path.abspath(__file__))
KRAKEN_QUELLE = os.path.join(HIER, "kraken", "kraken.py")
NONCE_POOL = os.path.join(HIER, "kraken", "nonce_pool.py")
FUTURES_QUELLE = os.path.join(HIER, "nautilus_kraken", "kraken_futures.py")
CACHE = os.path.join(HIER, "cache")
PROTOKOLL = os.path.join(CACHE, "kraken-abweisungen.jsonl")
STAND_DATEI = os.path.join(CACHE, "kraken-abweisungs-sonde.json")

# Die Basis-URLs stehen NICHT hier, sondern in den Hausmodulen
# (kraken.BASIS / kraken_futures.BASIS). Eine eigene Kopie waere eine zweite
# Wahrheit - und beim Testen gefaehrlich: eine Sonde, die ihre eigene
# (echte) Adresse mitbringt, schickt Test-Anfragen an den echten Host.
# Gemessen 25.09.2026: genau so gingen sechs Aufrufe mit Attrappen-Schluessel
# an api.kraken.com - jeder davon zaehlt bei Kraken als Fehlversuch und kann
# einen Konto-Lockout ausloesen.

# Nach einer Abweisung nicht sofort wieder klopfen: bei einem Konto-Lockout
# setzt JEDER weitere Aufruf den Timer zurueck (Kraken-Doku).
KUEHLZEIT_MIN = 60

UA = "BrainFiles-KrakenSonde/1.0"

# Header, die im Fehlerfall die Ursache verraten.
INTERESSANTE_HEADER = (
    "content-type", "cf-ray", "cf-mitigated", "cf-cache-status", "retry-after",
    "ratelimit-limit", "ratelimit-remaining", "ratelimit-reset",
    "server", "date", "www-authenticate",
)


# --- Laden der Hausmodule ---------------------------------------------------

def _lade(pfad, name):
    """Ein Hausmodul ueber den PFAD laden (Muster kraken_rest._lade).

    Ein sys.path-Eintrag auf kraken/ koennte gleichnamige Spurenmodule
    verdecken - dieselbe Falle wie bei ratschen.py.
    """
    spec = importlib.util.spec_from_file_location(name, pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


# --- kleine Helfer ----------------------------------------------------------

def _jetzt():
    return datetime.now().astimezone().isoformat()


def _header_auswahl(kopf):
    return {k: v for k, v in kopf.items() if k.lower() in INTERESSANTE_HEADER}


def _kurz(text, grenze=600):
    text = (text or "").strip()
    return text[:grenze]


def _lies_stand():
    try:
        with open(STAND_DATEI, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _schreib_stand(stand):
    os.makedirs(CACHE, exist_ok=True)
    with open(STAND_DATEI, "w", encoding="utf-8", newline="") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)
        f.write("\n")


def _protokolliere(zeile):
    os.makedirs(CACHE, exist_ok=True)
    with open(PROTOKOLL, "a", encoding="utf-8", newline="") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")


# --- die fuenf Wege ---------------------------------------------------------

def _oeffentlich(url, timeout=20):
    """Ein oeffentlicher GET: Status, Header, Koerperbeginn."""
    anfang = time.monotonic()
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as antwort:
            koerper = antwort.read().decode(errors="replace")
            return {
                "ok": True,
                "status": antwort.status,
                "dauer_s": round(time.monotonic() - anfang, 2),
                "kopf": _header_auswahl(dict(antwort.headers)),
                "anfang": _kurz(koerper, 200),
            }
    except urllib.error.HTTPError as e:
        return {
            "ok": False,
            "status": e.code,
            "dauer_s": round(time.monotonic() - anfang, 2),
            "kopf": _header_auswahl(dict(e.headers or {})),
            "anfang": _kurz(e.read().decode(errors="replace")),
        }
    except Exception as e:  # noqa: BLE001 - Transportfehler jeder Art
        return {"ok": False, "status": None,
                "dauer_s": round(time.monotonic() - anfang, 2),
                "fehler": "%s: %s" % (type(e).__name__, e)}


def offen_spot(kraken):
    return _oeffentlich(kraken.BASIS + "/0/public/Time")


def offen_futures(futures):
    return _oeffentlich(futures.BASIS + "/tickers")


def _privat(fn, *a, **kw):
    """Ein signierter Hausaufruf ueber die vorhandene Modulfunktion."""
    anfang = time.monotonic()
    try:
        ergebnis = fn(*a, **kw)
        return {"ok": True, "dauer_s": round(time.monotonic() - anfang, 2),
                "wert": ergebnis if isinstance(ergebnis, (int, float, str)) else None}
    except Exception as e:  # noqa: BLE001 - jede Ablehnung ist ein Befund
        return {"ok": False, "dauer_s": round(time.monotonic() - anfang, 2),
                "fehler": "%s: %s" % (type(e).__name__, e)}


def privat_spot(kraken):
    return _privat(kraken.guthaben, "ZEUR")


def privat_futures(futures):
    return _privat(futures.guthaben)


# --- der Zeuge: dieselbe Anfrage noch einmal, diesmal mit allen Details ----

def _nonce_fuer(pool, versuch):
    """Nonce wie der Haus-Standard (kraken.py._roh_privat): Versuch 0 aus dem
    geteilten Pool, ab Versuch 1 mit vorwaerts() vorgeschoben. vorwaerts()
    schreibt den Wert IN die gemeinsame Datei - die Monotonie bleibt erhalten
    und der naechste normale Aufruf ist nicht wieder zu niedrig."""
    if versuch == 0:
        return pool.monotone_nonce()
    return pool.vorwaerts(versuch)


def _ist_nonce_befund(ergebnis):
    """Antwortet Kraken mit einem Nonce-Befund?

    "EAPI:Invalid nonce" heisst NICHT, dass unsere nonce nicht steigt: ein
    fremdes Werkzeug auf demselben Schluessel (die offizielle kraken-cli)
    setzt einen hoeheren Wert, und Kraken vergleicht gegen den HOECHSTEN.
    Der Haus-Standard wiederholt so einen Aufruf bis zu dreimal - ohne das
    Schieben bliebe der Zeuge ein Nonce-Artefakt statt der echten Abweisung.
    """
    anfang = (ergebnis or {}).get("anfang") or ""
    return "nonce" in anfang.lower()


def _roh_spot(kraken, pool):
    """Signierter POST /0/private/Balance mit vollstaendiger Erfassung.

    Bis zu drei Versuche: scheitert der Aufruf mit "EAPI:Invalid nonce"
    (fremdes Werkzeug hat den Schluessel-Nonce hochgesetzt), schiebt der
    naechste Versuch den geteilten Zaehler mit vorwaerts() vor - identisch
    zum Haus-Pfad kraken.py._roh_privat. Ein echter Befund (Permission
    denied, Lockout, HTTP-Fehler) wird NIE wiederholt.
    """
    schluessel = kraken._variable("KRAKEN_SPOT_API_KEY")
    geheim = kraken._variable("KRAKEN_SPOT_API_SECRET")
    if not (schluessel and geheim):
        return {"fehler": "kein SPOT-Schluessel gesetzt"}
    pfad = "/0/private/Balance"
    for versuch in range(3):
        nonce = str(_nonce_fuer(pool, versuch))
        formular = urllib.parse.urlencode({"nonce": nonce})
        roh = (nonce + formular).encode()
        nachricht = pfad.encode() + hashlib.sha256(roh).digest()
        sig = base64.b64encode(
            hmac.new(base64.b64decode(geheim), nachricht, hashlib.sha512).digest()
        ).decode()
        kopf = {"User-Agent": UA, "API-Key": schluessel, "API-Sign": sig,
                "Content-Type": "application/x-www-form-urlencoded"}
        ergebnis = _roh_aufruf(kraken.BASIS + pfad, kopf, formular.encode())
        ergebnis["versuche"] = versuch + 1
        if not _ist_nonce_befund(ergebnis) or versuch == 2:
            return ergebnis
    return ergebnis  # pragma: no cover - der letzte Versuch kehrt immer zurueck


def _roh_futures(futures, pool):
    """Signierter GET /accounts mit vollstaendiger Erfassung.

    Nutzt den gemeinsamen nonce-Pool (Nanosekunden, Haus-Standard seit
    22.09.2026) statt futures._nonce() (Millisekunden). Die Einheit muss
    mindestens so gross sein, die groesste, die ein Werkzeug auf denselben
    Schluessel sendet - sonst ist jeder Wert darunter ungueltig. Wie der
    Spot-Zeuge wiederholt auch dieser Weg einen "Invalid nonce"-Befund mit
    vorgeschobenem Pool (bis zu drei Versuche); ein echter Befund wird nie
    wiederholt.
    """
    if not futures.schluessel_vorhanden():
        return {"fehler": "kein FUTURES-Schluessel gesetzt"}
    pfad = "/accounts"
    for versuch in range(3):
        nonce = str(_nonce_fuer(pool, versuch))
        kopf = {"User-Agent": UA, "APIKey": futures._env(futures.KEY_NAME),
                "Nonce": nonce, "Authent": futures._signatur(pfad, "", nonce)}
        ergebnis = _roh_aufruf(futures.BASIS + pfad, kopf, None)
        ergebnis["versuche"] = versuch + 1
        if not _ist_nonce_befund(ergebnis) or versuch == 2:
            return ergebnis
    return ergebnis  # pragma: no cover - der letzte Versuch kehrt immer zurueck


def _roh_aufruf(url, kopf, daten):
    anfang = time.monotonic()
    req = urllib.request.Request(url, data=daten, headers=kopf,
                                 method="POST" if daten is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=25) as antwort:
            koerper = antwort.read().decode(errors="replace")
            return {"status": antwort.status,
                    "dauer_s": round(time.monotonic() - anfang, 2),
                    "kopf": _header_auswahl(dict(antwort.headers)),
                    "anfang": _kurz(koerper)}
    except urllib.error.HTTPError as e:
        return {"status": e.code,
                "dauer_s": round(time.monotonic() - anfang, 2),
                "kopf": _header_auswahl(dict(e.headers or {})),
                "anfang": _kurz(e.read().decode(errors="replace"))}
    except Exception as e:  # noqa: BLE001
        return {"status": None, "dauer_s": round(time.monotonic() - anfang, 2),
                "fehler": "%s: %s" % (type(e).__name__, e)}


# --- Auswertung -------------------------------------------------------------

def einordnung(wege):
    """Aus den vier Wegen die Ebene ableiten, auf der es klemmt.

    Die tragende Regel: faellt ein OEFFENTLICHER Weg, kann es kein
    Schluesselproblem sein - ohne Schluessel gibt es nichts zu authentifizieren.
    Ein solcher Befund heisst Netz, IP oder cloudflare und wird auch dann so
    genannt, wenn zusaetzlich die signierten Wege fallen.
    """
    rot = [name for name, w in wege.items() if not w.get("ok")]
    if not rot:
        return "ok", "alle Wege offen"
    offen_rot = sorted(n for n in rot if n.startswith("offen_"))
    privat_rot = sorted(n for n in rot if n.startswith("privat_"))
    if offen_rot:
        zusatz = ("; zusaetzlich signiert rot: %s" % ", ".join(privat_rot)
                  if privat_rot else "")
        return "netz", ("ein OEFFENTLICHER Weg faellt ohne Schluessel (%s) - Netz, "
                        "IP oder cloudflare%s" % (", ".join(offen_rot), zusatz))
    # Nur die signierten Wege rot: erst die Herkunft (IP/VPN), dann Rechte.
    # GEMESSEN 25.09.2026: mit laufendem NordLynx-Tunnel (Ausgang 45.150.x.x, ein
    # NordVPN-Knoten) wurde der FUTURES-Weg mit `authenticationError` abgewiesen,
    # waehrend der SPOT-Weg durchlief; OHNE Tunnel (Ausgang 92.208.x.x, eigener
    # Anschluss) ging derselbe Aufruf sofort wieder (guthaben 141,5876 USD).
    # Ein `authenticationError` ist deshalb KEIN Beweis fuer einen falschen
    # Schluessel - die Herkunft gehoert zuerst geprueft.
    return "schluessel", ("nur die SIGNIERTEN Wege fallen (%s), die oeffentlichen "
                          "gehen - erst die HERKUNFT pruefen (VPN/Proxy aktiv? "
                          "IP-Wechsel?), dann Schluessel-, Rechte- oder "
                          "Konto-Ebene (Lockout)" % ", ".join(privat_rot))


def _kuehlzeit_laeuft(stand, jetzt_ts):
    bis = stand.get("kuehlzeit_bis")
    return bool(bis and jetzt_ts < bis)


# --- der Lauf ---------------------------------------------------------------

def _lade_alle():
    """Die drei Hausmodule EINES Laufs. Als Paar, damit ein Test sie ersetzen
    kann (`lauf(module=...)`) - sonst muesste er die echten Adressen patchen."""
    return (_lade(KRAKEN_QUELLE, "sonde_kraken_quelle"),
            _lade(FUTURES_QUELLE, "sonde_kraken_futures"),
            _lade(NONCE_POOL, "sonde_kraken_nonce_pool"))


def lauf(melden=True, module=None):
    """Ein Messlauf. Rueckgabe: der Stand als Dict.

    `module` ist die Testnaht: ein Tupel (kraken, futures, pool) - die Sonde
    benutzt dann DIESE Module samt ihrer BASIS-Adresse und schickt nichts an
    einen echten Host.
    """
    stand = _lies_stand()
    jetzt = time.time()
    if _kuehlzeit_laeuft(stand, jetzt):
        rest = int((stand["kuehlzeit_bis"] - jetzt) / 60)
        if melden:
            print("Kraken-Sonde pausiert noch %d min (Kuehlzeit nach Abweisung "
                  "um %s)." % (rest, stand.get("stoerung_seit", "?")))
        stand["letzter_lauf_uebersprungen"] = _jetzt()
        _schreib_stand(stand)
        return stand

    kraken, futures, pool = module or _lade_alle()

    wege = {
        "offen_spot": offen_spot(kraken),
        "privat_spot": privat_spot(kraken),
        "privat_futures": privat_futures(futures),
        "offen_futures": offen_futures(futures),
    }
    lage, text = einordnung(wege)
    zeile = {"zeit": _jetzt(), "lage": lage,
             "wege": {n: w.get("ok") for n, w in wege.items()}}

    if lage != "ok":
        # Der Zeuge: dieselbe Anfrage noch einmal mit allen Details.
        zeile["zeuge"] = {}
        if not wege["privat_spot"].get("ok"):
            zeile["zeuge"]["roh_spot"] = _roh_spot(kraken, pool)
        if not wege["privat_futures"].get("ok"):
            zeile["zeuge"]["roh_futures"] = _roh_futures(futures, pool)
        zeile["wege_voll"] = wege
        war_stoerung = bool(stand.get("stoerung_seit"))
        stand["stoerung_seit"] = stand.get("stoerung_seit") or zeile["zeit"]
        stand["kuehlzeit_bis"] = jetzt + KUEHLZEIT_MIN * 60
        stand["letzte_abweisung"] = zeile["zeit"]
    else:
        if stand.get("stoerung_seit"):
            # Erholung - das ist der Beleg, den T-073 verlangt hat.
            zeile["erholt_nach_min"] = int((jetzt - stand.get("stoerung_ts", jetzt)) / 60)
            stand["letzte_erholung"] = zeile["zeit"]
        stand.pop("stoerung_seit", None)
        stand["kuehlzeit_bis"] = None

    stand["letzter_lauf"] = zeile["zeit"]
    stand["letzter_lauf_ts"] = jetzt
    stand["letzte_lage"] = lage
    _schreib_stand(stand)
    _protokolliere(zeile)

    if melden:
        if lage == "ok":
            print("Kraken: %s" % text)
            if zeile.get("erholt_nach_min") is not None:
                print("  (vorher abgewiesen, wieder offen nach ~%d min)"
                      % zeile["erholt_nach_min"])
        else:
            print(text)
            for name, w in sorted(wege.items()):
                if not w.get("ok"):
                    print("  %-16s %s" % (name, w.get("fehler") or ("HTTP %s" % w.get("status"))))
            for name, w in (zeile.get("zeuge") or {}).items():
                if w.get("status") or w.get("fehler"):
                    print("  Zeuge %-12s status=%s kopf=%s" % (
                        name, w.get("status") or "-", w.get("kopf") or w.get("fehler")))
                    if w.get("anfang"):
                        print("     roh: %s" % w["anfang"][:300].replace("\n", " "))
    return zeile


def wache(module=None):
    """Fuer den Cron: leere Ausgabe, wenn alles gesund ist."""
    zeile = lauf(melden=False, module=module)
    lage = zeile.get("lage")
    if lage == "ok":
        if zeile.get("erholt_nach_min") is not None:
            print("Kraken wieder offen nach ~%d min Abweisung (%s)."
                  % (zeile["erholt_nach_min"], zeile["zeit"]))
        return 0
    if not lage:
        return 0                       # uebersprungener Lauf (Kuehlzeit)
    _, text = einordnung(zeile.get("wege_voll") or {})
    print("Kraken weist ab (%s) um %s: %s" % (lage, zeile["zeit"], text))
    for name, w in sorted((zeile.get("wege_voll") or {}).items()):
        if not w.get("ok"):
            print("  %-16s %s" % (name, w.get("fehler") or ("HTTP %s" % w.get("status"))))
    for name, w in (zeile.get("zeuge") or {}).items():
        print("  Zeuge %-12s status=%s kopf=%s" % (name, w.get("status") or "-",
                                                   w.get("kopf") or w.get("fehler")))
        if w.get("anfang"):
            print("     roh: %s" % w["anfang"][:300].replace("\n", " "))
    print("  Frage an Max: warst du in dem Fenster im Kraken-Portal "
          "(Schluessel bearbeiten/erzeugen)?")
    return 1


def stand_zeigen():
    stand = _lies_stand()
    if not stand:
        print("kein Stand vorhanden - die Sonde lief noch nie")
        return 0
    print(json.dumps(stand, ensure_ascii=False, indent=1))
    return 0


def main(argv):
    if "--stand" in argv:
        return stand_zeigen()
    if "--wache" in argv:
        return wache()
    lauf(melden=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))