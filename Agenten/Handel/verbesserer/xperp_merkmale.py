"""Merkmals-Cache fuer die Spur-2-Schleife.

Die Rangliste je 4H-Schritt (Kennzahlen, Lage, Hebel-Deckel-Merkmale) haengt
nicht von der Wache ab, nur von den Kerzen. Sie ist die teure Stelle eines
Rücktests (20-35 min) und wird deshalb einmal je Datenstand gerechnet und mit
einem Hash ueber die Eingangsdaten abgelegt. Aendern sich Kerzen, Universum
oder Raster, passt der Hash nicht mehr und der Cache wird neu gebaut - nie
stillschweigend mit altem Stand weitergearbeitet.

Nur Standardbibliothek.
"""

import hashlib
import json
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent
for _p in (WURZEL, WURZEL.parent / "xperp"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import xperp_ruecktest as rt  # noqa: E402


def staende(von_ms, bis_ms):
    """Alle Entscheidungsstaende (t - 4H) fuer jeden 4H-Schritt t in
    [von_ms, bis_ms]. simuliere() entscheidet bei t nur mit Kerzen bis t - 4H.
    """
    return list(range(von_ms - rt.SCHRITT_MS, bis_ms - rt.SCHRITT_MS + 1,
                      rt.SCHRITT_MS))


def ctval_je_inst(universum, instr_je_basis):
    """Kontraktwert je Instrument - dieselbe Zeile wie in simuliere()."""
    return {x["instId"]: float(instr_je_basis[x["basis"]]["ctVal"])
            for x in universum if x["basis"] in instr_je_basis}


def _reihe(kerzen):
    """Fingerabdruck der GANZEN Reihe (Zeit und Schluss je Kerze): OKX
    korrigiert gelegentlich Kerzen mitten in der Reihe, ohne dass Anzahl oder
    Raender sich aendern."""
    if not kerzen:
        return [0]
    h = hashlib.sha256(
        json.dumps([[k[0], k[4]] for k in kerzen]).encode("utf-8"))
    return [len(kerzen), h.hexdigest()]


def _code_stempel():
    """Hash der Quelltexte, die die Rangliste bestimmen (Punkteformel,
    Kennzahlen, Kategorien, Engine). Eine Aenderung dort macht jeden Cache
    ungueltig - sonst liefe die Suche gegen eine Logik, die live nicht mehr
    gilt."""
    h = hashlib.sha256()
    for modul in (rt, rt.auswahl):
        h.update(Path(modul.__file__).read_bytes())
    return h.hexdigest()


def daten_hash(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste):
    """Hash ueber alles, wovon die Matrix abhaengt: Universum, je Instrument
    Anzahl/erste/letzte Zeit/letzter Schlusskurs der 4H- und 1D-Reihe,
    Kontraktwerte und das Stand-Raster."""
    kopf = {
        "code": _code_stempel(),
        "universum": [[x["instId"], x["basis"], x["kategorie"]]
                      for x in universum],
        "k4": {i: _reihe(k4_je_inst[i]) for i in sorted(k4_je_inst)},
        "k1d": {i: _reihe(k1d_je_inst[i]) for i in sorted(k1d_je_inst)},
        "ctval": {i: ctval[i] for i in sorted(ctval)},
        "staende": ([stand_liste[0], stand_liste[-1], len(stand_liste)]
                    if stand_liste else []),
    }
    return hashlib.sha256(
        json.dumps(kopf, sort_keys=True).encode("utf-8")).hexdigest()


def baue(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste):
    """{stand_ms: Rangliste} - genau das, was simuliere(werte_cache=...)
    erwartet."""
    return {s: rt.rangliste_schritt(universum, k4_je_inst, k1d_je_inst, {}, s,
                                    ctval_je_inst=ctval)
            for s in stand_liste}


def speichern(pfad, hash_, matrix):
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_name(pfad.name + ".tmp")
    tmp.write_text(json.dumps(
        {"hash": hash_, "werte": {str(s): w for s, w in matrix.items()}}),
        "utf-8")
    tmp.replace(pfad)


def laden(pfad, hash_):
    """Die Matrix, wenn Datei und Hash passen - sonst None."""
    pfad = Path(pfad)
    if not pfad.is_file():
        return None
    try:
        d = json.loads(pfad.read_text("utf-8"))
        if d.get("hash") != hash_:
            return None
        return {int(s): w for s, w in d["werte"].items()}
    except (OSError, ValueError, KeyError, AttributeError):
        return None


def hole_oder_baue(pfad, universum, k4_je_inst, k1d_je_inst, ctval,
                   stand_liste):
    """(matrix, aus_cache). Aus dem Cache nur, wenn der Hash passt UND alle
    gebrauchten Staende enthalten sind."""
    h = daten_hash(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste)
    matrix = laden(pfad, h)
    if matrix is not None and set(stand_liste) <= set(matrix):
        return matrix, True
    matrix = baue(universum, k4_je_inst, k1d_je_inst, ctval, stand_liste)
    speichern(pfad, h, matrix)
    return matrix, False
