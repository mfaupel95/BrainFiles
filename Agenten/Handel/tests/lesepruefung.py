"""AST-Pruefung "schreibt nichts" fuer die Module des Leitstands.

Hilfsmodul fuer Tests, selbst kein Test (der Name beginnt nicht mit test_).
Grundsatz: lieber ein falscher Fund als ein uebersehener Schreibzugriff.
Geprueft wird der Quelltext, nicht ein Stichwort: ein Kommentar mit
"schreiben" ist kein Schreibzugriff. Aliase aus `import x as y` und
`from x import f as g` werden aufgeloest. json.dumps (baut nur einen String)
ist kein Fund; .write/.writelines auf beliebigen Objekten schon.
"""

import ast
from pathlib import Path

MODUS_ZEICHEN = "wax+"
MODULE = {"json", "os", "shutil", "pathlib", "tempfile", "csv", "io", "codecs"}
VERBOTEN = {
    "json": {"dump"},
    "os": {"remove", "unlink", "rename", "replace", "makedirs", "mkdir", "rmdir"},
    "shutil": {"move", "copy", "copy2", "copyfile", "copytree", "rmtree"},
    "csv": {"writer", "DictWriter"},
    "tempfile": {"NamedTemporaryFile", "mkstemp", "mkdtemp"},
}
OPEN_MODULE = {"io", "codecs"}
PFAD_IMMER = {"write_text", "write_bytes", "mkdir", "unlink", "touch", "rmdir"}
PFAD_EIN_ARGUMENT = {"rename", "replace"}       # str/datetime.replace: kein Fund
OBJEKT_SCHREIBEN = {"write", "writelines"}


def _baum(pfad):
    return ast.parse(Path(pfad).read_text(encoding="utf-8"))


def _aliase(baum):
    """(Modul-Aliase, Funktions-Aliase): name -> modul bzw. name -> (modul, orig)."""
    module, funktionen = {}, {}
    for k in ast.walk(baum):
        if isinstance(k, ast.Import):
            for a in k.names:
                wurzel = a.name.split(".")[0]
                if wurzel in MODULE:
                    module[a.asname or wurzel] = wurzel
        elif isinstance(k, ast.ImportFrom):
            if (k.module or "").split(".")[0] in MODULE and not k.level:
                for a in k.names:
                    funktionen[a.asname or a.name] = (k.module.split(".")[0], a.name)
    return module, funktionen


def _modus_schreibt(knoten, stelle):
    """True, wenn der open-Modus schreibt oder nicht als Konstante erkennbar ist.
    Kein Modus angegeben = "r". Ein Dateiname wird nie als Modus gelesen."""
    wert = None
    if len(knoten.args) > stelle:
        wert = knoten.args[stelle]
    for kw in knoten.keywords:
        if kw.arg == "mode":
            wert = kw.value
        elif kw.arg is None:                     # **kwargs: nicht erkennbar
            return True
    if wert is None:
        return False
    if isinstance(wert, ast.Constant) and isinstance(wert.value, str):
        return any(z in wert.value for z in MODUS_ZEICHEN)
    return True


def _aufloesen(f, module, funktionen):
    """(modul, name) fuer bekannte Modulaufrufe, ("", name) fuer freie Namen,
    (None, attr) fuer Methodenaufrufe auf Objekten."""
    if isinstance(f, ast.Name):
        if f.id in funktionen:
            return funktionen[f.id]
        return "", f.id
    if isinstance(f, ast.Attribute):
        if isinstance(f.value, ast.Name) and f.value.id in module:
            return module[f.value.id], f.attr
        return None, f.attr
    return None, ""


def schreibstellen(pfad):
    """Alle Schreibstellen als "Z. <zeile>: <was>"; leer = schreibt nichts."""
    baum = _baum(pfad)
    module, funktionen = _aliase(baum)
    aus = []
    for k in ast.walk(baum):
        if not isinstance(k, ast.Call):
            continue
        mod, name = _aufloesen(k.func, module, funktionen)
        was = None
        if mod == "" and name == "open":
            if _modus_schreibt(k, 1):
                was = "open(...)"
        elif mod in OPEN_MODULE and name == "open":
            if _modus_schreibt(k, 1):
                was = "%s.open(...)" % mod
        elif mod == "os" and name == "open":
            was = "os.open"                      # Flags nicht lesbar: im Zweifel Fund
        elif mod in VERBOTEN and name in VERBOTEN[mod]:
            was = "%s.%s" % (mod, name)
        elif mod is None:
            if name in PFAD_IMMER:
                was = ".%s" % name
            elif name in PFAD_EIN_ARGUMENT and len(k.args) + len(k.keywords) == 1 and (
                    k.args or k.keywords[0].arg == "target"):
                was = ".%s" % name
            elif name == "open" and _modus_schreibt(k, 0):
                was = ".open(...)"
            elif name in OBJEKT_SCHREIBEN:
                was = ".%s" % name
        if was:
            aus.append("Z. %d: %s" % (k.lineno, was))
    return sorted(aus, key=lambda z: int(z.split(":")[0][3:]))


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
