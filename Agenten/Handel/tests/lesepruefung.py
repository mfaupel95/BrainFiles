"""AST-Pruefung "schreibt nichts" fuer die Module des Leitstands.

Hilfsmodul fuer Tests, selbst kein Test (der Name beginnt nicht mit test_).
Dieselben Regeln wie tests/test_handelszentrale_rein_lesend.py, dazu die
Schreibmethoden von pathlib (write_text, write_bytes, unlink, touch, open im
Schreibmodus). Geprueft wird der Quelltext, nicht ein Stichwort: ein
Kommentar mit "schreiben" ist kein Schreibzugriff.
"""

import ast
from pathlib import Path

SCHREIBMODI = ("w", "a", "x", "w+", "a+", "r+", "wb", "ab", "xb")
VERBOTEN = {("json", "dump"), ("json", "dumps"), ("csv", "writer"),
            ("os", "remove"), ("os", "rename"), ("os", "replace"),
            ("os", "mkdir"), ("os", "makedirs"), ("os", "rmdir"),
            ("shutil", "rmtree"), ("shutil", "copy")}
PFAD_METHODEN = ("write_text", "write_bytes", "unlink", "touch")


def _baum(pfad):
    return ast.parse(Path(pfad).read_text(encoding="utf-8"))


def _modus(knoten, stelle):
    """Modus eines open-Aufrufs: Argument an `stelle` oder mode=, sonst None."""
    if len(knoten.args) > stelle and isinstance(knoten.args[stelle], ast.Constant):
        return knoten.args[stelle].value
    for kw in knoten.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            return kw.value.value
    return None


def schreibstellen(pfad):
    """Alle Schreibstellen als "Z. <zeile>: <was>"; leer = schreibt nichts."""
    aus = []
    for k in ast.walk(_baum(pfad)):
        if not isinstance(k, ast.Call):
            continue
        f = k.func
        if isinstance(f, ast.Name) and f.id == "open":
            m = _modus(k, 1)
            if m is not None and str(m) in SCHREIBMODI:
                aus.append("Z. %d: open(..., %r)" % (k.lineno, m))
        elif isinstance(f, ast.Attribute):
            if isinstance(f.value, ast.Name) and (f.value.id, f.attr) in VERBOTEN:
                aus.append("Z. %d: %s.%s" % (k.lineno, f.value.id, f.attr))
            elif f.attr in PFAD_METHODEN:
                aus.append("Z. %d: .%s" % (k.lineno, f.attr))
            elif f.attr == "open":
                m = _modus(k, 0)
                if m is not None and str(m) in SCHREIBMODI:
                    aus.append("Z. %d: .open(%r)" % (k.lineno, m))
    return aus


def importiert(pfad, modul):
    """Importiert die Datei `modul` (auch als `from modul import ...`)?"""
    for k in ast.walk(_baum(pfad)):
        if isinstance(k, ast.Import):
            if any(a.name.split(".")[0] == modul for a in k.names):
                return True
        elif isinstance(k, ast.ImportFrom):
            if (k.module or "").split(".")[0] == modul:
                return True
    return False
