# MCP-Server-Venv-Rebuild: PYTHONHOME-Leak dauerhaft beseitigen

DETAIL-Anleitung zur PYTHONHOME-Sektion der SKILL.md — der komplette Ablauf vom 18.09.2026.

## Wann

Jedes Python-MCP-Server-venv auf uv-Python (AppData\Roaming\uv\python\cpython-3.13...) setzt bei uv-venvs das `python.exe` PYTHONHOME in seine EIGENE Prozessumgebung. Jede gespawnte PowerShell (windows-mcp) erbt sie; `hermes.exe` (3.11-venv) stirbt mit Fake-Corrupt-Python.

## Pruefung je Server-venv

    <server>/.venv/Scripts/python.exe -c "import os; print(os.environ.get('PYTHONHOME'))"

uv-venv → Pfad auf AppData\Roaming\uv\python... ; python.org-venv → `None`.

Betroffene Server (Agenten/MCP-Server/): archiv, kraken, mail, ant.dir.cursortouch.windows-mcp, ant.dir.gh.tooluniverse.tooluniverse-mcp, ant.dir.gh.blender.blender-mcp.

## Rebuild je Server

1. `mv .venv .venv.bak-JJJJMMTT`  (klein da Symlinks; als Rollback stehen lassen)
2. `C:/Users/faupe/AppData/Local/Programs/Python/Python313/python.exe -m venv .venv`
3. Deps installieren (Tabelle unten)
4. Pruefen: PYTHONHOME None + Import + Kind-Prozess-Test

## Deps je Server (Installationsart laut MCP-Manifest + pyproject)

| Server | Install | Hinweis |
|---|---|---|
| windows-mcp | `pip install -e .` | fastmcp + windows_mcp, Importtest `from windows_mcp.__main__ import main` |
| archiv | `pip install "mcp>=1.2"` | erscheint bei `pip list` nicht als editable |
| kraken | `pip install "mcp>=1.2" httpx` | |
| mail | `pip install mcp keyring` | |
| blender | `pip install -e .` | ~44 Pakete |
| tooluniverse | siehe FALLE unten | ~184 Pakete, 240 Tools |

## FALLE: `pip install -e .` zieht Deps still nicht

- `echo "EXIT=$?"` NACH einer Pipe (`... | tail -5`) misst den Exit von TAIL, nicht von pip — ohne Pipe pruefen.
- tooluniverse: `fitz>=0.0.1.dev2` existiert auf PyPI nicht (nur 0.0.0) → pip bricht den ganzen Install ab (kein fastmcp, keine Deps). Der Server importiert fitz nur in `src/tooluniverse/remote/uspto_downloader/uspto_downloader_tool.py` (lazy). Workaround:
  1. `pip install -e . --no-deps`
  2. `pip install PyMuPDF`  (liefert das fitz-MODUL; die fitz-Distribution bleibt „fehlend“ → benign)
  3. `pip install requests numpy sympy graphql-core fastapi uvicorn pydantic networkx openai pyyaml google-genai google-generativeai "mcp[cli]" fastmcp xmltodict lxml huggingface_hub jsonpath_ng rcsb-api pandas pdfplumber flask aiohttp beautifulsoup4 python-dotenv psutil ddgs`
  4. Danach: `pip install epam.indigo faiss-cpu==1.12.0 "setuptools>=70,<81" "markitdown[all]" playwright` (gehen alle auf 3.13).

## Verifikation

- windows-mcp Kind-PowerShell OHNE PYTHONHOME: `./.venv/Scripts/python.exe -c "import subprocess; r=subprocess.run(['powershell.exe','-NoProfile','-Command','Write-Output (\"PYTHONHOME=[\" + $env:PYTHONHOME + \"]\")'],capture_output=True,text=True); print(r.stdout)"` → `PYTHONHOME=[]`.
- Danach aus derselben PowerShell `hermes.exe --version` (mit HERMES_HOME gesetzt): rc 0, kein Fake-Corrupt-Python.
- WICHTIG: Der Fix wirkt erst in NEUEN Sessions — die laufende Session hat die alten venvs bereits gespawnt.
- Alle 6 Server pruefen (PYTHONHOME None + Import), auch wenn nur einer das Symptom zeigte: sie leaken dieselbe Klasse.
