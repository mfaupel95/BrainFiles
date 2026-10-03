"""Der Handelsstand der Zentrale: lesen, pruefen, testen, scharf schalten.

Die Zentrale zeigt `Agenten/Handel` als eigenen Bereich. Damit ist sie die
naechste Stelle, an der jemand eine Spur **scharf schalten** will - und genau
dafuer gibt es Regeln (Wissen/Handelsregeln.md, Punkt 3, und
Wiki/Handel/Gates-und-Freigabe.md):

  * scharf geschaltet wird **von Hand, in einem Fenster**, das die Werte zeigt,
    sie aendern laesst und ein Feld zum Bestaetigen hat,
  * `handel_erlaubt` ist nur EINER von sieben Punkten - ohne
    `freigabe.erfuellt`, ein offenes Zeitfenster und ein orderfaehiges Konto
    passiert nichts,
  * `herzschlag_max_minuten` steht auf 180, BEVOR `handel_erlaubt` auf true geht,
  * und wer eine Spur live nimmt, prueft ihre Sperrkette an der Vorschau.

Dieses Modul setzt das um, soweit es ohne Boersenkontakt geht:

| Aufgabe | Funktion |
|---|---|
| Stand je Spur (erlaubt, Haken, Orderweg, Fenster, Buch) | `zustand` (liest `spuren_stand.py` - EINE Erkennung des Live-Pfads, keine zweite Liste) |
| welches Skript welche Spur faehrt | `laufplan` (liest `dauerlauf.SPUREN` per `ast`, nicht per Regex) |
| Vorschau-Befehl (`--vorschau`, der einzige Beleg fuer den Modus) | `vorschau_argv` |
| Checkliste vor dem Scharfschalten | `pruefpunkte` |
| Schreiben in `wachen.json` | `wachen_setzen` (gezielter Textersatz, Sicherung, `json.loads`-Gegenprobe) |

Was dieses Modul NICHT tut: es ordert nicht, es ruft keine Boerse, und es setzt
keinen Wert, den der Aufrufer nicht ausdruecklich genannt hat.
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Hausregel seit 19.09.2026: eine Live-Spur muss die PC-Ausfall-Luecke
# ueberleben, darum 180 Minuten. Wer darunter scharf schaltet, stellt bei jeder
# Stoerung echte Positionen flach.
HERZSCHLAG_LIVE = 180

SPUREN_STAND = "spuren_stand.py"
DAUERLAUF = "dauerlauf.py"

# Interpreter, den der Dauerlauf als Vorgabe benutzt (dauerlauf.PYTHON).
VENV_VORGABE = ("scanner", ".venv", "Scripts", "python.exe")


# ------------------------------------------------------------------ Pfade
def handel_ordner(brainfiles: Path | str) -> Path:
    # Aufgeloest, weil `dauerlauf.SPUREN` seinen eigenen Ordner absolut nennt
    # (`os.path.join(HIER, ...)`) - ein relativer Pfad hier gaebe einen
    # relativen Interpreterpfad zurueck, der beim Start ins Leere zeigt.
    return (Path(brainfiles) / "Agenten" / "Handel").resolve()


def spur_ordner(brainfiles: Path | str, ordner: str) -> Path:
    return handel_ordner(brainfiles) / ordner


def wachen_pfad(brainfiles: Path | str, ordner: str) -> Path:
    return spur_ordner(brainfiles, ordner) / "wachen.json"


# ------------------------------------------------------------------ Laden
_STAND_MODUL = {}


def stand_modul(handel: Path) -> object | None:
    """`spuren_stand.py` ueber den PFAD laden (nicht ueber sys.path).

    Warum per Pfad: `Agenten/Handel` auf `sys.path` koennte gleichnamige Module
    verdecken, und `spuren_stand` soll genau die Erkennung des Live-Pfads
    benutzen, die auch das Werkzeug selbst benutzt - eine zweite Liste waere
    eine zweite Wahrheit.
    """
    handel = Path(handel)
    if handel in _STAND_MODUL:
        return _STAND_MODUL[handel]
    pfad = handel / SPUREN_STAND
    if not pfad.is_file():
        _STAND_MODUL[handel] = None
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location("zentrale_spurenstand", pfad)
    modul = importlib.util.module_from_spec(spec)
    sys.modules["zentrale_spurenstand"] = modul      # sonst scheitert @dataclass
    spec.loader.exec_module(modul)
    _STAND_MODUL[handel] = modul
    return modul


def zustand(brainfiles: Path | str) -> dict[str, dict]:
    """Stand aller Spuren aus `spuren_stand.sammle()` - {spur: eintrag}.

    Fehlt das Werkzeug oder scheitert es, kommt ein leeres Dict zurueck; die
    Zentrale zeigt dann keine Handels-Spalten, statt abzustuerzen.
    """
    modul = stand_modul(handel_ordner(brainfiles))
    if modul is None:
        return {}
    try:
        return {e["spur"]: e for e in modul.sammle()}
    except Exception:                                        # noqa: BLE001
        return {}


def spurnamen(brainfiles: Path | str) -> list[str]:
    """Die Namen der Spuren, die der Dauerlauf faehrt."""
    modul = stand_modul(handel_ordner(brainfiles))
    if modul is None:
        return []
    try:
        return list(modul.spurenliste()[0])
    except Exception:                                        # noqa: BLE001
        return []


# ------------------------------------------------------------------ Laufplan
def _wert(knoten, handel: Path):
    """Einen ast-Knoten als Zeichenkette lesen (Constant oder os.path.join)."""
    if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
        return knoten.value
    if isinstance(knoten, ast.Call):
        teile = []
        for arg in knoten.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                teile.append(arg.value)
            elif isinstance(arg, ast.Name) and arg.id == "HIER":
                teile.append(str(handel))
            else:
                return None
        return str(Path(*teile)) if teile else None
    return None


def laufplan(brainfiles: Path | str) -> dict[str, dict]:
    """Welche Spur welches Skript mit welchem Interpreter faehrt.

    Gelesen aus `dauerlauf.SPUREN` mit `ast` - **nicht** mit einem Muster. Ein
    Muster greift ueber auskommentierte Bloecke hinweg und zieht deren Werte in
    den vorigen Eintrag (dieser Fehler stand schon einmal in einem README).
    `ast` liest nur, was wirklich Code ist.

    Rueckgabe je Spur: `{"ordner", "skript", "python"}`; `python` ist None, wenn
    die Spur das gemeinsame venv benutzt.
    """
    handel = handel_ordner(brainfiles)
    quelle = handel / DAUERLAUF
    if not quelle.is_file():
        return {}
    try:
        baum = ast.parse(quelle.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return {}
    knoten = None
    for n in baum.body:
        if isinstance(n, ast.Assign) and any(
            getattr(z, "id", "") == "SPUREN" for z in n.targets
        ):
            knoten = n.value
            break
    if not isinstance(knoten, ast.Dict):
        return {}
    plan: dict[str, dict] = {}
    for schluessel, wert in zip(knoten.keys, knoten.values):
        if not (isinstance(schluessel, ast.Constant) and isinstance(schluessel.value, str)):
            continue
        if not isinstance(wert, ast.Dict):
            continue
        felder = {}
        for k, v in zip(wert.keys, wert.values):
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                felder[k.value] = v
        plan[schluessel.value] = {
            "ordner": _wert(felder.get("ordner"), handel) or schluessel.value,
            "skript": _wert(felder.get("skript"), handel) or "handeln.py",
            "python": _wert(felder.get("python"), handel),
            "waehrung": _wert(felder.get("waehrung"), handel) or "",
        }
    return plan


def interpreter(brainfiles: Path | str, spur: str) -> Path:
    """Der Interpreter, mit dem der Dauerlauf diese Spur faehrt.

    Reihenfolge: der `python`-Eintrag der Spur, sonst das scanner-venv (so
    startet der Dauerlauf seine Spuren), sonst der laufende Interpreter. Die
    Wahl wird NICHT geraten - sie steht in `dauerlauf.SPUREN`.
    """
    handel = handel_ordner(brainfiles)
    eintrag = laufplan(brainfiles).get(spur) or {}
    if eintrag.get("python"):
        return Path(eintrag["python"])
    vorgabe = handel.joinpath(*VENV_VORGABE)
    if vorgabe.is_file():
        return vorgabe
    return Path(sys.executable)


def vorschau_argv(brainfiles: Path | str, spur: str) -> list[str]:
    """Der Vorschau-Aufruf einer Spur: `<python> <ordner>/<skript> --vorschau`.

    Das ist die Messprobe aus Wiki/Handel/Gates-und-Freigabe.md - **mit**
    `MAXHIRN_ROUTINE=1` im Umfeld (die Umgebungsvariablen setzt der Aufrufer,
    `vorschau_umgebung`).
    """
    handel = handel_ordner(brainfiles)
    eintrag = laufplan(brainfiles).get(spur) or {}
    ordner = eintrag.get("ordner") or spur
    skript = eintrag.get("skript") or "handeln.py"
    return [str(interpreter(brainfiles, spur)), str(handel / ordner / skript), "--vorschau"]


def vorschau_umgebung(basis=None) -> dict:
    """Die Umgebung fuer einen Vorschau-Lauf.

    Drei Hausregeln in einem Aufruf: `MAXHIRN_ROUTINE=1` (sonst haelt sich die
    Spur fuer eine Sitzung am Bildschirm und wartet auf eine Freigabe, die
    niemand geben kann), `PYTHONHOME`/`PYTHONPATH` entfernt (eine geerbte
    Vergiftung laesst jeden Python-Start scheitern) und UTF-8 fuer die Ausgabe.
    """
    import os

    umgebung = dict(basis if basis is not None else os.environ)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        umgebung.pop(name, None)
    umgebung["MAXHIRN_ROUTINE"] = "1"
    umgebung["PYTHONIOENCODING"] = "utf-8"
    return umgebung


# ------------------------------------------------------------------ Checkliste
@dataclass
class Punkt:
    """Ein Punkt der Arming-Checkliste: was gilt, und was daraus folgt."""

    name: str
    stand: str          # "ok", "fehlt", "warnung", "unbekannt"
    text: str


def _zahl(w: dict, name: str):
    wert = w.get(name)
    return wert if isinstance(wert, (int, float)) and not isinstance(wert, bool) else None


def zahl(w: dict, name: str):
    """Eine Zahl aus einer Wachen-Datei (None, wenn sie fehlt oder keine Zahl ist).

    Oeffentlich, weil `schalter.py` denselben Blick auf die Wachen braucht -
    eine zweite Lesart waere eine zweite Wahrheit.
    """
    return _zahl(w, name)


def deckel_text(w: dict) -> str:
    """Die Risikozahlen einer Wachen-Datei in einer Zeile (nur was da ist)."""
    teile = []
    for name, titel in (
        ("max_pro_trade_usd", "je Trade USD"), ("max_pro_trade_eur", "je Trade EUR"),
        ("live_max_pro_trade_usd", "live je Trade USD"),
        ("live_max_pro_trade_eur", "live je Trade EUR"),
        ("live_max_gesamt_usd", "live gesamt USD"),
        ("live_max_gesamt_eur", "live gesamt EUR"),
        ("max_gesamt_usd", "gesamt USD"), ("max_offene_positionen", "Plaetze"),
        ("risiko_je_position_usd", "Risiko je Position USD"),
        ("drawdown_halbierung_usd", "Ratsche USD"),
        ("kill_switch_gesamt_usd", "Kill USD"),
    ):
        z = _zahl(w, name)
        if z is not None:
            teile.append(f"{titel} {z:g}")
    return ", ".join(teile[:6]) or "keine Zahlen in der Wachen-Datei"


def pruefpunkte(w: dict, eintrag: dict | None, *, buch: dict | None = None,
                alter: int | None = None) -> list[Punkt]:
    """Die Checkliste aus Wiki/Handel/Gates-und-Freigabe.md als Punkte.

    Sie bewertet nur, was ohne Boersenkontakt messbar ist. Guthaben und
    Schluesselrechte stehen ausdruecklich als `unbekannt` darin - eine geratene
    Aussage waere schlimmer als eine fehlende (die Spur prueft beides selbst in
    ihrem Zyklus).
    """
    punkte: list[Punkt] = []
    eintrag = eintrag or {}

    hs = _zahl(w, "herzschlag_max_minuten")
    if hs is None:
        punkte.append(Punkt("Herzschlag", "fehlt",
                            "kein herzschlag_max_minuten in der Wachen-Datei"))
    elif hs < HERZSCHLAG_LIVE:
        punkte.append(Punkt("Herzschlag", "fehlt",
                            f"{hs:g} min - fuer live sind {HERZSCHLAG_LIVE} noetig "
                            f"(ein PC-Ausfall wuerde sonst echte Positionen flachstellen)"))
    else:
        punkte.append(Punkt("Herzschlag", "ok", f"{hs:g} min"))

    order = list(eintrag.get("order") or [])
    art = eintrag.get("art")
    if not order:
        punkte.append(Punkt("Orderweg", "warnung",
                            "kein Orderaufruf im Spurordner - der Schalter ist wirkungslos"))
    else:
        punkte.append(Punkt("Orderweg", "ok",
                            f"{art or 'haus'} ({', '.join(order[:3])})"))

    erlaubt = eintrag.get("erlaubt")
    punkte.append(Punkt(
        "handel_erlaubt", "ok" if erlaubt else "warnung",
        "true" if erlaubt else "false (der Schalter der Spur)",
    ))

    frei = eintrag.get("frei")
    punkte.append(Punkt(
        "freigabe.erfuellt", "ok" if frei else "unbekannt",
        "true - der Haken ist gesetzt" if frei else
        "false - ohne den Haken handelt die Spur auch mit handel_erlaubt=true nicht live",
    ))

    fenster = eintrag.get("fenster")
    if fenster and fenster != "-":
        punkte.append(Punkt("Zeitfenster", "ok", str(fenster)))
    else:
        punkte.append(Punkt("Zeitfenster", "unbekannt",
                            "keins - der Dauerlauf oeffnet es nur auf Anfrage"
                            + (" (Spur steht in AUTO_FREIGABE)" if eintrag.get("auto") else "")))

    punkte.append(Punkt("Deckel", "ok", deckel_text(w)))

    if buch:
        punkte.append(Punkt("Buch", "ok",
                            ", ".join(f"{k}: {v}" for k, v in buch.items())))
    if alter is not None:
        punkte.append(Punkt(
            "Zyklus", "ok" if alter <= HERZSCHLAG_LIVE else "warnung",
            f"letzter Zyklus vor {alter} min",
        ))
    punkte.append(Punkt("Guthaben/Schluessel", "unbekannt",
                        "prueft die Spur selbst im Zyklus (Guthaben-Tor, Rechte)"))
    return punkte


def wirkung(eintrag: dict | None, *, erlaubt: bool, freigabe: bool | None = None) -> str:
    """In Worten, was das Scharfschalten zur Folge hat - ohne Beschwichtigung."""
    eintrag = eintrag or {}
    if not erlaubt:
        return ("Die Spur handelt nicht mehr. Offene Positionen bleiben und werden "
                "weiter ueber Stop/Ziel verwaltet - ein Ausstieg haengt NICHT an "
                "handel_erlaubt.")
    order = list(eintrag.get("order") or [])
    if not order:
        return ("Ohne Orderaufruf im Spurordner aendert der Schalter nichts - die Spur "
                "kann gar nicht ordern.")
    teile = ["handel_erlaubt=true"]
    frei = eintrag.get("frei") if freigabe is None else freigabe
    if frei:
        teile.append("freigabe.erfuellt ist true")
    else:
        teile.append("freigabe.erfuellt ist false (ohne den Haken kein Live-Handel)")
    fenster = eintrag.get("fenster")
    if fenster and fenster != "-":
        teile.append(f"Zeitfenster {fenster}")
    elif eintrag.get("auto"):
        teile.append("der Dauerlauf oeffnet das Zeitfenster selbst (AUTO_FREIGABE)")
    else:
        teile.append("kein Zeitfenster offen")
    if frei and (fenster and fenster != "-"):
        teile.append("=> der naechste Zyklus KANN live ordern")
    elif frei and eintrag.get("auto"):
        teile.append("=> der Dauerlauf oeffnet das Zeitfenster selbst, danach KANN "
                     "der Zyklus live ordern")
    elif frei:
        teile.append("=> live erst, wenn zusaetzlich ein Zeitfenster offen ist")
    else:
        teile.append("=> es kann nichts geordert werden")
    return ", ".join(teile)


# ------------------------------------------------------------------ Schreiben
# Zulaessige Schluessel: Anzeigename -> (Name in der Datei, Pfad im JSON).
# Der Name in der Datei ist der letzte Teil ("freigabe.erfuellt" -> "erfuellt"),
# der Pfad ist der Weg durch die verschachtelten Objekte. Beides gehoert
# zusammen: die Gegenprobe nach dem Schreiben sucht ueber den PFAD, der
# Textersatz ueber den NAMEN.
KEYS = {
    "handel_erlaubt": ("handel_erlaubt", ("handel_erlaubt",)),
    "herzschlag_max_minuten": ("herzschlag_max_minuten", ("herzschlag_max_minuten",)),
    "freigabe.erfuellt": ("erfuellt", ("freigabe", "erfuellt")),
}


def _dateiname(schluessel: str) -> str:
    return KEYS.get(schluessel, (schluessel, (schluessel,)))[0]


def _suchpfad(schluessel: str) -> tuple[str, ...]:
    return KEYS.get(schluessel, (schluessel, (schluessel,)))[1]


@dataclass
class Ergebnis:
    """Was ein Schreibversuch ergeben hat."""

    ok: bool
    pfad: Path
    sicherung: Path | None = None
    geaendert: list[str] = field(default_factory=list)
    fehler: str = ""
    vermerk: str = ""


def _muster(schluessel: str) -> re.Pattern:
    """Ein Schluessel, verankert am ZEILENANFANG.

    Die Verankerung ist der Schutz: die Wachen-Dateien tragen lange
    `_`-Notiztexte, in denen ein Schluesselname vorkommen darf ("_zweck": "wird
    von handeln.py gelesen"). Ein Treffer mitten im Text wuerde die Notiz
    zerschneiden - ein Treffer am Zeilenanfang ist immer ein echter Schluessel
    (ein JSON-String kann keinen unescapten Zeilenumbruch enthalten).
    """
    return re.compile(
        r'(?m)^([ \t]*)"%s"([ \t]*):([ \t]*)(true|false|[0-9.]+)' % re.escape(schluessel)
    )


def ersetze_wert(text: str, schluessel: str, wert) -> tuple[str, str]:
    """Einen Wert in einer Wachen-Datei ersetzen. Gibt (neuer Text, Meldung).

    Genau EIN Treffer, sonst wird nichts geaendert - ein zweiter Fund waere ein
    Zeichen dafuer, dass die Datei anders aussieht als erwartet (dann ist
    Nachsehen richtig, nicht Raten).
    """
    if isinstance(wert, bool):
        neu = "true" if wert else "false"
    else:
        neu = f"{wert:g}" if isinstance(wert, float) else str(wert)
    treffer = list(_muster(schluessel).finditer(text))
    if not treffer:
        return text, f"{schluessel}: nicht gefunden"
    if len(treffer) > 1:
        return text, f"{schluessel}: {len(treffer)} Fundstellen - nicht angefasst"
    m = treffer[0]
    alt = m.group(4)
    if alt == neu:
        return text, f"{schluessel}: war schon {neu}"
    neuer_text = text[:m.start(4)] + neu + text[m.end(4):]
    return neuer_text, f"{schluessel}: {alt} -> {neu}"


def _notiz_setzen(text: str, schluessel: str, wert: str, nach: str = "handel_erlaubt") -> str:
    """Eine datierte Notizzeile setzen bzw. auffrischen (idempotent).

    Sie steht direkt unter `handel_erlaubt` - dort, wo der Leser den Schalter
    sucht. Eine vorhandene Zeile desselben Namens wird ersetzt, nicht doppelt
    angelegt.
    """
    zeilen = text.splitlines(keepends=True)
    neu = f'  "{schluessel}": {json.dumps(wert, ensure_ascii=False)},\n'
    raus = [z for z in zeilen if not re.match(r'[ \t]*"%s"[ \t]*:' % re.escape(schluessel), z)]
    if len(raus) != len(zeilen):
        text = "".join(raus)
        zeilen = text.splitlines(keepends=True)
    for i, z in enumerate(zeilen):
        if re.match(r'[ \t]*"%s"[ \t]*:' % re.escape(nach), z):
            # Komma sicherstellen, dann die Notiz direkt darunter
            if not z.rstrip().endswith(","):
                zeilen[i] = z.rstrip("\r\n") + ",\n" if z.endswith("\n") else z + ","
            zeilen.insert(i + 1, neu)
            return "".join(zeilen)
    return text + ("\n" if not text.endswith("\n") else "") + neu


def wachen_setzen(
    pfad: Path | str,
    aenderungen: dict,
    *,
    vermerk: str = "",
    notiz_schluessel: str = "",
    jetzt: dt.datetime | None = None,
) -> Ergebnis:
    """Werte in eine Wachen-Datei schreiben - gezielter Textersatz, nie ein Dump.

    Warum kein `json.dump`: die Wachen-Dateien sind handformatiert (lange
    Notiztexte, CRLF, eigene Reihenfolge). Ein Dump wuerde jede Zeile umbrechen -
    der Diff waere die ganze Datei, und die Notizen waeren nicht mehr lesbar
    angeordnet.

    Ablauf: Sicherung `.bak-JJJJMMTT` (nur wenn es heute noch keine gibt - der
    Stand VOR der ersten Aenderung ist der wertvolle), Textersatz je Schluessel,
    dann die Gegenprobe `json.loads` UND der Vergleich jedes Wertes. Stimmt
    etwas nicht, wird NICHTS geschrieben.
    """
    pfad = Path(pfad)
    jetzt = jetzt or dt.datetime.now()
    if not pfad.is_file():
        return Ergebnis(False, pfad, fehler="Wachen-Datei fehlt")
    roh = pfad.read_bytes()
    text = roh.decode("utf-8")
    crlf = b"\r\n" in roh

    geaendert, fehler = [], []
    for schluessel, wert in aenderungen.items():
        text, meldung = ersetze_wert(text, _dateiname(schluessel), wert)
        if "nicht gefunden" in meldung or "Fundstellen" in meldung:
            fehler.append(meldung)
        else:
            geaendert.append(meldung)

    if fehler:
        return Ergebnis(False, pfad, geaendert=geaendert, fehler="; ".join(fehler))

    if notiz_schluessel and vermerk:
        text = _notiz_setzen(
            text, notiz_schluessel, f"{jetzt:%Y-%m-%d %H:%M} Zentrale: {vermerk}"
        )

    try:
        daten = json.loads(text)
    except ValueError as e:
        return Ergebnis(False, pfad, geaendert=geaendert,
                        fehler=f"json.loads nach dem Ersetzen: {e}")

    for schluessel, wert in aenderungen.items():
        gefunden = daten
        for teil in _suchpfad(schluessel):
            gefunden = gefunden.get(teil) if isinstance(gefunden, dict) else None
        if gefunden != wert:
            return Ergebnis(False, pfad, geaendert=geaendert,
                            fehler=f"Gegenprobe: {schluessel} ist {gefunden!r}, erwartet {wert!r}")

    sicherung = pfad.with_name(f"{pfad.name}.bak-{jetzt:%Y%m%d}")
    if not sicherung.exists():
        try:
            sicherung.write_bytes(roh)
        except OSError as e:
            return Ergebnis(False, pfad, geaendert=geaendert, fehler=f"Sicherung: {e}")
    ausgabe = text.replace("\n", "\r\n").encode("utf-8") if crlf else text.encode("utf-8")
    try:
        pfad.write_bytes(ausgabe)
    except OSError as e:
        return Ergebnis(False, pfad, geaendert=geaendert, fehler=f"Schreiben: {e}")
    return Ergebnis(True, pfad, sicherung, geaendert, "", vermerk)


def scharf_schalten(
    pfad: Path | str,
    *,
    w: dict,
    freigabe: bool | None = None,
    herzschlag: bool = False,
    vermerk: str = "",
    jetzt: dt.datetime | None = None,
) -> Ergebnis:
    """Eine Spur scharf schalten: Herzschlag, Schalter, Haken.

    `herzschlag=True` setzt `herzschlag_max_minuten` auf 180 mit - das ist die
    Hausregel ("wer eine Spur live nimmt, setzt 180, BEVOR handel_erlaubt auf
    true geht"). Ohne den Schalter und mit einem Wert unter 180 wird NICHTS
    geschrieben: dann fehlt die Voraussetzung, und ein halb scharfer Zustand
    waere schlimmer als der alte.
    """
    aenderungen: dict = {}
    hs = _zahl(w, "herzschlag_max_minuten")
    if herzschlag or (hs is not None and hs < HERZSCHLAG_LIVE):
        aenderungen["herzschlag_max_minuten"] = HERZSCHLAG_LIVE
    if hs is None and not herzschlag:
        return Ergebnis(False, Path(pfad), fehler=(
            f"herzschlag_max_minuten fehlt in der Wachen-Datei - erst {HERZSCHLAG_LIVE} setzen"))
    aenderungen["handel_erlaubt"] = True
    if freigabe is not None:
        aenderungen["freigabe.erfuellt"] = bool(freigabe)
    return wachen_setzen(
        pfad, aenderungen, vermerk=vermerk or "scharf geschaltet",
        notiz_schluessel="_scharfgeschaltet", jetzt=jetzt,
    )


def entschaerfen(
    pfad: Path | str, *, vermerk: str = "", jetzt: dt.datetime | None = None
) -> Ergebnis:
    """Eine Spur entschaerfen: nur `handel_erlaubt` auf false.

    Der Haken `freigabe.erfuellt` bleibt stehen - er ist die Entscheidung des
    Menschen und wird nicht als Nebenwirkung zurueckgenommen.
    """
    return wachen_setzen(
        pfad, {"handel_erlaubt": False},
        vermerk=vermerk or "entschaerft", notiz_schluessel="_entschaerft",
        jetzt=jetzt,
    )


def beleg(log_ordner: Path | str, text: str, jetzt: dt.datetime | None = None) -> Path:
    """Eine Zeile ins Belegprotokoll der Zentrale schreiben (Anhaengen)."""
    jetzt = jetzt or dt.datetime.now()
    ordner = Path(log_ordner)
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / f"handel-schalter-{jetzt:%Y%m%d}.log"
    try:
        with open(ziel, "a", encoding="utf-8", newline="\n") as f:
            f.write(f"{jetzt:%Y-%m-%d %H:%M:%S} {text}\n")
    except OSError:
        pass
    return ziel