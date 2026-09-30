"""Backtest-Urteile sammeln und in die Freigabe der Spur schreiben.

Warum es dieses Modul gibt: Die drei Spuren mit eigenem Backtest-Motor
(`gitter`, `orbk`, `nautilus`) rechneten ihre Urteile von Hand - das Ergebnis
landete in der Konsole oder in einer JSON-Datei, und `freigabe.backtest_bestanden`
stand in allen `wachen.json` auf `false`, weil es NIEMANDEN gab, der es schreibt.
`orbk/wachen_orb.freigabe_voll_erfuellt()` liest das Feld seit jeher; ohne
Schreiber konnte die Bedingung nie wahr werden. Dieses Modul ist der Schreiber.

WAS ES TUT
  1. faehrt jeden Motor mit den WERTEN DER SPUR (nicht mit den Vorgaben des
     Skripts - sonst bewertet man eine andere Strategie),
  2. bildet daraus ein Urteil (bestanden / nicht bestanden / nicht ermittelbar),
  3. legt alle Urteile in `backtest_urteile.json` ab (Laufzeitdatei, nicht
     versioniert),
  4. schreibt in die `wachen.json` der Spur NUR die drei Felder
     `backtest_bestanden`, `backtest_urteil`, `backtest_geprueft_am` -
     byte-genau, nur an dieser Stelle, mit Sicherung.

WAS ES NICHT TUT
  - Es setzt NIE `handel_erlaubt` und NIE `freigabe.erfuellt`. Ein Backtest-Urteil
    ist EINE Bedingung; scharf schaltet weiterhin Max von Hand.
  - Es aendert nie einen Strategie-Wert (Stufen, Spanne, Jahre). Es liest sie.
  - Bei einem Motor, der nicht laeuft oder nichts Vergleichbares liefert, bleibt
    der alte Wert stehen (ein Netzfehler darf ein bestandenes Urteil nicht
    stillschweigend zuruecknehmen); geschrieben wird nur der Befund in die
    Laufzeitdatei und die Konsole.

DAS MASS JE SPUR (aus den Motoren, nicht erfunden)
  - gitter/nautilus (Gitter): besser als Buy-and-Hold. Der Massstab steht im
    Motor selbst: "Ein Grid, das schlechter ist als schlicht halten, hat seinen
    Zweck verfehlt."
  - orbk (ORB nach SPEC): mindestens ein Instrument mit `URTEIL: Ja` - das
    Urteil des Motors verlangt Trefferquote ueber Break-even, EV > 0, den besten
    Quartalswert > 0 UND mindestens 10 Verlierer. "Nein" mit dem Zusatz
    "unter 10 Verlierer" heisst: zu wenig Daten, nicht schlechte Strategie - das
    steht so im Urteilstext und gehoert so gelesen.

Aufrufe (aus dem Handel-Ordner):
    scanner/.venv/Scripts/python.exe backtest_urteile.py               # alles
    scanner/.venv/Scripts/python.exe backtest_urteile.py --spur gitter
    scanner/.venv/Scripts/python.exe backtest_urteile.py --vorschau    # schreibt nichts
    scanner/.venv/Scripts/python.exe backtest_urteile.py --vorschau --vorschau-datei V.json
    scanner/.venv/Scripts/python.exe backtest_urteile.py --aus-vorschau V.json

VORSCHAU UEBERNEHMEN (der Weg des Leitstands)
  --vorschau-datei legt die Vorschau als Datei ab, mit dem SHA-256 jeder
  gelesenen wachen.json. --aus-vorschau faehrt KEINEN Motor, sondern schreibt
  genau diese Urteile - nur wenn die Vorschau hoechstens 60 min alt ist und
  keine wachen.json sich seitdem geaendert hat. Sonst: nichts geschrieben,
  Exit 2. So landet in der Datei, was Max gesehen und bestaetigt hat, nicht
  das Ergebnis eines neuen Laufs mit neueren Kerzen.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HIER = Path(__file__).resolve().parent
PY_SCANNER = HIER / "scanner" / ".venv" / "Scripts" / "python.exe"
PY_NAUTILUS = HIER / "nautilus" / ".venv" / "Scripts" / "python.exe"
URTEILE = HIER / "backtest_urteile.json"
ZEITLIMIT_S = 900
VORSCHAU_GUELTIG_MIN = 60
VORSCHAU_ZUKUNFT_MIN = 5      # Uhren zweier Laeufe duerfen so weit auseinander liegen


def _jetzt_dt():
    return datetime.now(timezone.utc)


def _jetzt():
    return _jetzt_dt().isoformat(timespec="seconds")


def _sha256(pfad):
    """SHA-256 der Datei als Hex, oder None wenn sie nicht lesbar ist."""
    try:
        return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()
    except OSError:
        return None


def wachen_laden(spur):
    return json.loads((HIER / spur / "wachen.json").read_text(encoding="utf-8"))


def motor_laufen(spur, skript, python, argumente):
    """Den Motor der Spur fahren. Rueckgabe: (text, fehler) - kein Ausstieg."""
    if not Path(python).exists():
        return "", "kein Interpreter: %s" % python
    skript_pfad = HIER / spur / skript
    if not skript_pfad.exists():
        return "", "kein Motor: %s" % skript_pfad
    try:
        p = subprocess.run([str(python), str(skript_pfad)] + list(argumente),
                           cwd=str(HIER / spur), capture_output=True, text=True,
                           timeout=ZEITLIMIT_S)
    except subprocess.TimeoutExpired:
        return "", "Motor lief in %d s nicht zu Ende" % ZEITLIMIT_S
    text = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0:
        return text, "Motor endete mit Code %d" % p.returncode
    return text, None


# --- die drei Motoren ------------------------------------------------------

def _gitter_werte(spur, w):
    """Die Werte des LAUFENDEN Gitters - nicht blind die der wachen.json.

    Der Motor faehrt `gitter/handeln.py` selbst, und das nimmt die im Zustand
    gesetzte Leiter (sie wurde beim Aufsetzen aus den Werten gebaut). Weicht die
    `wachen.json` davon ab, beschreibt ein Backtest mit ihr eine ANDERE
    Strategie. Gemessen 15.09.2026: wachen.json `stufen: 6`, laufende Leiter 12.
    Der Unterschied steht im Urteilstext, damit er nicht untergeht.
    """
    stufen, spanne = w.get("stufen"), w.get("spanne_prozent")
    hinweis = None
    try:
        z = json.loads((HIER / spur / "zustand.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        z = {}
    leiter = z.get("leiter") or {}
    if leiter.get("stufen"):
        if stufen and int(stufen) != int(leiter["stufen"]):
            hinweis = ("Achtung: die laufende Leiter hat %s Stufen, die "
                       "wachen.json %s" % (leiter["stufen"], stufen))
        stufen = leiter["stufen"]
    if leiter.get("schritt_prozent") and not spanne:
        spanne = leiter["schritt_prozent"]
    return stufen, spanne, hinweis


def urteil_gitter(w):
    """Gitter gegen Halten, mit den Werten der lebenden Spur."""
    stufen, spanne, hinweis = _gitter_werte("gitter", w)
    argumente = ["--json"]
    if stufen:
        argumente += ["--stufen", str(stufen)]
    if spanne:
        argumente += ["--spanne-prozent", str(spanne)]
    text, fehler = motor_laufen("gitter", "backtest_gitter.py", PY_SCANNER,
                                argumente)
    if fehler:
        return None, fehler, {}
    zahl = None
    for zeile in reversed(text.splitlines()):
        zeile = zeile.strip()
        if zeile.startswith("{"):
            try:
                zahl = json.loads(zeile)
                break
            except ValueError:
                continue
    if not zahl:
        return None, "kein JSON in der Ausgabe", {}
    rendite = zahl.get("rendite_pct")
    halten = zahl.get("halten_pct")
    if rendite is None or halten is None:
        return None, "Kennzahlen fehlen (rendite_pct/halten_pct)", zahl
    bestanden = rendite > halten
    urteil = ("Gitter %+.2f %% gegen Halten %+.2f %% (%d Zyklen, %d Stufen, "
              "%d Stundenkerzen)" % (rendite, halten, zahl.get("zyklen", 0),
                                     zahl.get("stufen", 0), zahl.get("kerzen", 0)))
    if hinweis:
        urteil += " | " + hinweis
    return bestanden, urteil, zahl


def urteil_nautilus(w):
    """Gitter gegen Halten - Urteil aus der Ergebnisdatei des Motors."""
    argumente = ["--quelle", "1h"]
    if w.get("stufen"):
        argumente += ["--stufen", str(w["stufen"])]
    ergebnis = HIER / "nautilus" / "backtest_grid_ergebnis.json"
    text, fehler = motor_laufen("nautilus", "backtest_grid.py", PY_NAUTILUS,
                                argumente)
    if fehler:
        return None, fehler, {}
    # Die mtime taugt hier nicht als Nachweis: ein schneller Lauf schreibt in
    # dieselbe Sekunde wie der vorherige. Liveness beweist der Rueckgabecode
    # (oben), gelesen wird die Ergebnisdatei des Motors.
    if not ergebnis.exists():
        return None, "Motor hat keine Ergebnisdatei geschrieben", {}
    d = json.loads(ergebnis.read_text(encoding="utf-8"))
    diff = d.get("differenz_zu_hold")
    if diff is None:
        return None, "differenz_zu_hold fehlt", d
    teile = ["Gitter %+.0f USDT gegenueber Halten" % diff]
    if d.get("rendite_pct") is not None:
        teile.append("%+.2f %% im Buch" % d["rendite_pct"])
    elif d.get("buchwert") is not None and d.get("einsatz"):
        teile.append("Buchwert %.2f bei Einsatz %.2f"
                     % (d["buchwert"], d["einsatz"]))
    if d.get("buy_and_hold_prozent") is not None:
        teile.append("Halten %+.2f %%" % d["buy_and_hold_prozent"])
    return diff > 0, " (".join([teile[0], ", ".join(teile[1:]) + ")"]
                               if len(teile) > 1 else teile), d


def urteil_orbk(w):
    """ORB: das Urteil des Motors je Instrument und Einstiegsmodell."""
    text, fehler = motor_laufen("orbk", "backtest.py", PY_SCANNER,
                                ["--jahre", "2"])
    if fehler and not text:
        return None, fehler, {}
    zeilen = []
    for zeile in text.splitlines():
        m = re.match(r"URTEIL:\s*(Ja|Nein)\s*-\s*(.*)", zeile.strip())
        if m:
            zeilen.append((m.group(1), m.group(2).strip()))
    if not zeilen:
        return None, "kein URTEIL in der Ausgabe (Motor ohne Vergleichszahlen)", {}
    ja = [t for v, t in zeilen if v == "Ja"]
    bestanden = bool(ja)
    kennzahlen = {"urteile": ["%s: %s" % (v, t) for v, t in zeilen]}
    if bestanden:
        return True, "mindestens ein Instrument bestanden: %s" % ja[0], kennzahlen
    # Der haeufigste Grund ist zu wenig Material - das gehoert in den Text.
    duenn = [t for _, t in zeilen if "unter 10 Verlierer" in t]
    grund = ("kein Instrument bestanden (%d geprueft%s)"
             % (len(zeilen),
                "; ueberwiegend zu wenig Daten" if duenn else ""))
    return False, grund, kennzahlen


MOTOREN = {"gitter": urteil_gitter, "orbk": urteil_orbk,
           "nautilus": urteil_nautilus}


# --- Schreiben in die wachen.json ------------------------------------------

def _freigabe_spanne(text):
    """Start und Ende des freigabe-Blocks im Rohtext, oder None."""
    i = text.find('"freigabe"')
    if i < 0:
        return None
    j = text.find("{", i)
    tiefe, k = 0, j
    while k < len(text):
        if text[k] == "{":
            tiefe += 1
        elif text[k] == "}":
            tiefe -= 1
            if tiefe == 0:
                return (i, k + 1)
        k += 1
    return None


def _sichern_und_ersetzen(p, text2):
    """Tagessicherung einmal anlegen, dann wachen.json atomar ersetzen.

    Erst .tmp, dann os.replace: ein Abbruch (taskkill aus dem Leitstand,
    voller Datentraeger) laesst die alte Datei ganz, nie eine halbe.
    """
    bak = p.with_name("wachen.json.bak-%s" % datetime.now().strftime("%Y%m%d"))
    if not bak.exists():
        shutil.copy2(p, bak)
    tmp = p.with_name(p.name + ".tmp")
    try:
        tmp.write_bytes(text2.encode("utf-8"))
        os.replace(tmp, p)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _freigabe_anlegen(spur, text, p, bestanden, urteil_kurz, tag, nl, vorschau):
    """Einen freigabe-Block anlegen, wenn die Datei keinen hat (Gitter-Spur).

    Anker ist `journal_zweitziel` - den fuehren alle Spuren mit Kopie ausser
    Haus. Ohne Anker wird nichts geraten.
    """
    anker = text.find('"journal_zweitziel"')
    if anker < 0:
        return ("kein freigabe-Block und kein Anker (journal_zweitziel) in "
                "%s/wachen.json - nicht geraten" % spur)
    start = text.rfind(nl, 0, anker) + len(nl)
    block = ("  \"freigabe\": {" + nl
             + "    \"erfuellt\": false," + nl
             + "    \"backtest_bestanden\": %s," % ("true" if bestanden else "false") + nl
             + "    \"backtest_urteil\": \"%s\"," % urteil_kurz + nl
             + "    \"backtest_geprueft_am\": \"%s\"" % tag + nl
             + "  }," + nl)
    text2 = text[:start] + block + text[start:]
    try:
        json.loads(text2)
    except ValueError as e:
        return "nicht geschrieben - JSON unlesbar nach dem Anlegen: %s" % e
    if vorschau:
        return ("VORSCHAU: %s/wachen.json bekaeme einen freigabe-Block "
                "(backtest_bestanden=%s)" % (spur, bestanden))
    _sichern_und_ersetzen(p, text2)
    return None


def freigabe_schreiben(spur, bestanden, urteil, vorschau=False, tag=None):
    """Die drei Felder in die freigabe der Spur schreiben - byte-genau.

    Nur diese Stelle wird angefasst: erst der Wert `backtest_bestanden`, dann
    die zwei Belegfelder. Die Datei wird VOR dem Schreiben geparst (ein
    eingefuegtes Feld ohne Komma faellt sonst erst danach auf).
    """
    p = HIER / spur / "wachen.json"
    raw = p.read_bytes()
    nl = "\r\n" if b"\r\n" in raw else "\n"
    text = raw.decode("utf-8")
    tag = tag or datetime.now().strftime("%Y-%m-%d")
    urteil_kurz = (urteil or "")[:180].replace('"', "'")
    spanne = _freigabe_spanne(text)
    if spanne is None:
        return _freigabe_anlegen(spur, text, p, bestanden, urteil_kurz, tag, nl,
                                 vorschau)
    a, b = spanne
    block = text[a:b]
    neu = block

    # 1) backtest_bestanden setzen oder einfuegen
    m = re.search(r'"backtest_bestanden"\s*:\s*(true|false)', neu)
    if m:
        neu = neu[:m.start(1)] + ("true" if bestanden else "false") + neu[m.end(1):]
    else:
        einzug = "    "
        neu = neu.replace("{", "{\n%s\"backtest_bestanden\": %s,"
                          % (einzug, "true" if bestanden else "false"), 1)

    # 2) die zwei Belegfelder - vorhandene ersetzen, fehlende vor der letzten Zeile
    for name, wert in (("backtest_urteil", '"%s"' % urteil_kurz),
                       ("backtest_geprueft_am", '"%s"' % tag)):
        m = re.search(r'"%s"\s*:\s*("[^"]*"|null|true|false)' % name, neu)
        if m:
            neu = neu[:m.start(1)] + wert + neu[m.end(1):]
        else:
            i = neu.rfind("}")
            # Ein vorhandenes Komma am Blockende muss weg, sonst entsteht beim
            # zweiten Feld ein doppeltes. Bei leerem Block kein Komma.
            kopf = neu[:i].rstrip().rstrip(",")
            komma = "" if kopf.endswith("{") else ","
            # Das eingefuegte Feld ist das LETZTE im Block: kein Komma danach.
            neu = (kopf + komma + "\n    \"%s\": %s\n  " % (name, wert)
                   + neu[i:])

    text2 = text[:a] + neu + text[b:]
    try:                                  # Gegenprobe VOR dem Schreiben
        json.loads(text2)
    except ValueError as e:
        return "nicht geschrieben - JSON unlesbar nach dem Umbau: %s" % e
    if text2 == text:
        return None                       # war schon so
    if vorschau:
        return "VORSCHAU: %s/wachen.json wuerde backtest_bestanden=%s bekommen" \
               % (spur, bestanden)
    _sichern_und_ersetzen(p, text2)
    return None


# --- Vorschau ablegen und uebernehmen --------------------------------------

def vorschau_ablegen(pfad, eintraege, stand):
    """Die Vorschau als Datei ablegen (erst .tmp, dann umbenennen)."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps({"stand": stand, "art": "urteile-vorschau",
                               "spuren": eintraege}, ensure_ascii=False, indent=2)
                   + "\n", encoding="utf-8")
    os.replace(tmp, pfad)


def vorschau_pruefen(daten, jetzt):
    """"" wenn die Vorschau uebernommen werden darf, sonst der Grund."""
    if (not isinstance(daten, dict) or daten.get("art") != "urteile-vorschau"
            or not isinstance(daten.get("spuren"), dict)):
        return "Vorschau unlesbar"
    try:
        stand = datetime.fromisoformat(str(daten.get("stand")))
    except ValueError:
        return "Vorschau ohne Stand"
    if stand.tzinfo is None:
        return "Vorschau ohne Stand"
    alter_min = (jetzt - stand).total_seconds() / 60
    if alter_min < -VORSCHAU_ZUKUNFT_MIN:
        return "Stand liegt in der Zukunft"
    if alter_min > VORSCHAU_GUELTIG_MIN:
        return "Vorschau aelter als %d min" % VORSCHAU_GUELTIG_MIN
    return ""


def _urteile_laden():
    if URTEILE.exists():
        try:
            d = json.loads(URTEILE.read_text(encoding="utf-8"))
            if isinstance(d, dict):
                return d
        except (OSError, ValueError):
            pass
    return {}


def aus_vorschau(pfad):
    """Genau die Urteile der Vorschau schreiben - ohne Motor. Exit-Code."""
    try:
        daten = json.loads(Path(pfad).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        daten = None
    grund = vorschau_pruefen(daten, _jetzt_dt())
    if not grund and not daten["spuren"]:
        grund = "Vorschau ohne Spuren"
    tag = None
    if not grund:
        tag = datetime.fromisoformat(daten["stand"]).astimezone().strftime("%Y-%m-%d")
        # Erst ALLES pruefen, dann schreiben: keine halbe Uebernahme.
        for spur, e in sorted(daten["spuren"].items()):
            if spur not in MOTOREN or not isinstance(e, dict):
                grund = "unbekannte Spur in der Vorschau: %s" % spur
                break
            b = e.get("bestanden")
            if (not (b is None or isinstance(b, bool))
                    or not (e.get("urteil") is None or isinstance(e["urteil"], str))
                    or not isinstance(e.get("kennzahlen", {}), dict)
                    or not isinstance(e.get("sha256"), str)):
                grund = "Vorschau unlesbar"
                break
            sha = _sha256(HIER / spur / "wachen.json")
            if sha is None or sha != e["sha256"]:
                grund = "%s/wachen.json hat sich seit der Vorschau geaendert" % spur
                break
            if b is None:
                continue
            # Trockenlauf: scheitert das Schreiben spaeter, dann schon jetzt.
            try:
                h = freigabe_schreiben(spur, b, e.get("urteil"), vorschau=True,
                                       tag=tag)
            except Exception as fehler:       # noqa: BLE001
                h = str(fehler)
            if h and not h.startswith("VORSCHAU:"):
                grund = "%s: %s" % (spur, h)
                break
    if grund:
        print("nichts geschrieben - %s" % grund)
        return 2

    alt = _urteile_laden()
    aus = {"stand": _jetzt(), "spuren": dict(alt.get("spuren") or {}),
           "ohne_motor": alt.get("ohne_motor") or []}
    rc = 0
    for spur, e in sorted(daten["spuren"].items()):
        if e.get("bestanden") is None:
            print("nicht ermittelbar: %s - nichts zu schreiben" % spur)
            continue
        vorher = _sha256(HIER / spur / "wachen.json")
        try:
            hinweis = freigabe_schreiben(spur, e["bestanden"], e.get("urteil"),
                                         tag=tag)
        except Exception as fehler:           # noqa: BLE001
            hinweis = str(fehler)
        if hinweis:
            print("nicht geschrieben: %s - %s" % (spur, hinweis))
            rc = 1
        elif _sha256(HIER / spur / "wachen.json") == vorher:
            print("unveraendert: %s/wachen.json" % spur)
        else:
            print("geschrieben: %s/wachen.json" % spur)
        aus["spuren"][spur] = {
            "stand": e.get("stand"), "bestanden": e["bestanden"],
            "urteil": e.get("urteil"), "kennzahlen": e.get("kennzahlen") or {},
            "geschrieben": not hinweis, "hinweis": hinweis, "aus_vorschau": True,
        }
    tmp = URTEILE.with_name(URTEILE.name + ".tmp")
    try:
        tmp.write_text(json.dumps(aus, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        os.replace(tmp, URTEILE)
    except OSError as fehler:
        print("Urteile-Datei nicht geschrieben - %s" % fehler)
        rc = 1
        try:
            tmp.unlink()
        except OSError:
            pass
    return rc


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Backtest-Urteile sammeln")
    ap.add_argument("--spur", action="append", choices=sorted(MOTOREN))
    ap.add_argument("--vorschau", action="store_true", help="nichts schreiben")
    ap.add_argument("--vorschau-datei", help="Vorschau zusaetzlich als Datei ablegen")
    ap.add_argument("--aus-vorschau", help="genau diese Vorschau uebernehmen")
    a = ap.parse_args()
    if a.vorschau_datei and not a.vorschau:
        ap.error("--vorschau-datei nur zusammen mit --vorschau")
    if a.aus_vorschau and (a.vorschau or a.spur):
        ap.error("--aus-vorschau steht allein (die Spuren kommen aus der Datei)")
    if a.aus_vorschau:
        return aus_vorschau(a.aus_vorschau)

    beginn = _jetzt()
    vorschau = {}
    spuren = a.spur or sorted(MOTOREN)
    alt = {}
    if URTEILE.exists():
        try:
            alt = json.loads(URTEILE.read_text(encoding="utf-8"))
        except ValueError:
            alt = {}
    aus = {"stand": _jetzt(), "spuren": dict(alt.get("spuren") or {})}

    # Spuren, die es gibt, aber keinen Motor: sie gehoeren in dieselbe Datei,
    # sonst sieht die Luecke aus wie "alles geprueft".
    ohne = []
    for d in sorted(HIER.iterdir()):
        if (d / "wachen.json").exists() and d.name not in MOTOREN:
            ohne.append(d.name)
    aus["ohne_motor"] = ohne

    for spur in spuren:
        sha = _sha256(HIER / spur / "wachen.json")   # VOR dem Motor: was Max sieht
        w = wachen_laden(spur)
        try:
            bestanden, urteil, kennzahlen = MOTOREN[spur](w)
        except Exception as e:            # noqa: BLE001 - ein Motor darf nie reissen
            bestanden, urteil, kennzahlen = None, "Motor abgebrochen: %s" % e, {}
        alt_wert = ((w.get("freigabe") or {}).get("backtest_bestanden"))
        hinweis = None
        if bestanden is None:
            hinweis = ("nicht ermittelbar - %s (alter Wert bleibt: %s)"
                       % (urteil, alt_wert))
        else:
            hinweis = freigabe_schreiben(spur, bestanden, urteil, a.vorschau)
        aus["spuren"][spur] = {
            "stand": _jetzt(), "bestanden": bestanden, "urteil": urteil,
            "kennzahlen": kennzahlen, "geschrieben": not a.vorschau
            and bestanden is not None, "hinweis": hinweis,
        }
        vorschau[spur] = {"stand": aus["spuren"][spur]["stand"],
                          "bestanden": bestanden, "urteil": urteil,
                          "kennzahlen": kennzahlen, "alt": alt_wert,
                          "sha256": sha}
        print("%-9s %-18s %s"
              % (spur, {True: "bestanden", False: "nicht bestanden",
                        None: "nicht ermittelbar"}[bestanden], urteil))
        if hinweis and bestanden is not None:
            print("          %s" % hinweis)

    if not a.vorschau:
        URTEILE.write_text(json.dumps(aus, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
        print("\nUrteile: %s" % URTEILE.name)
    else:
        print("\n(Vorschau - nichts geschrieben)")
        if a.vorschau_datei:
            vorschau_ablegen(a.vorschau_datei, vorschau, beginn)
            print("Vorschau-Datei: %s" % a.vorschau_datei)
    return 0


if __name__ == "__main__":
    sys.exit(main())
