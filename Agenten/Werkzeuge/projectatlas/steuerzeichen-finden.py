# Findet Steuerzeichen in Dateien, die ProjectAtlas als Quelle liest.
# Ursache: Steuerzeichen landen in der Graph-Identitaet (Signatur, Ueberschrift)
# und lassen die Graph-Projektion mit "identity text contains control characters"
# scheitern - der Atlas bleibt dann leer (scan.status: failed).
# Aufruf: python steuerzeichen-finden.py <repo> [<repo> ...]
# Abhilfe je Fund: projectatlas ignore add --kind path-prefix <repo-relativer-pfad>
import os, sys
from pathlib import Path

EXT = set('.py .pyw .js .jsx .ts .tsx .mjs .cjs .java .c .cpp .h .hpp .cs .go .rb .php .swift .kt .rs .sh .ps1 .bat .cmd .lua .dart .html .css .scss .md .mdx .json .jsonc .xml .yml .yaml .toml .toon .txt .ini .cfg .conf .vue .svelte .astro .sql'.split())
SKIP = set(['.git', '.projectatlas', '.venv', '__pycache__', 'node_modules', 'dist', 'build', 'target', '.next', '.turbo', '.build'])
ERLAUBT = set([9, 10, 13])  # Tabulator, LF, CR sind normal

for root in sys.argv[1:]:
    print('=== ' + root)
    anzahl = 0
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for f in files:
            if os.path.splitext(f)[1].lower() not in EXT:
                continue
            p = os.path.join(r, f)
            try:
                b = Path(p).read_bytes()
            except Exception:
                continue
            fund = None
            for i, by in enumerate(b):
                if by < 32 and by not in ERLAUBT:
                    fund = (i, by)
                    break
            if fund:
                anzahl += 1
                zeile = b[:fund[0]].count(10) + 1
                print('   byte=' + str(fund[1]) + ' zeile=' + str(zeile) + '  ' + os.path.relpath(p, root).replace(chr(92), chr(47)))
    print('Dateien mit Steuerzeichen: ' + str(anzahl))