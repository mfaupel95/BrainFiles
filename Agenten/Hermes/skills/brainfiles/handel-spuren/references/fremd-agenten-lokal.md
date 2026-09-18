# Fremd-Repo-Agenten schluessellos lokal betreiben

Eine Haus-Klasse: ein Drittanbieter-Repo (geklonter KI-/Trading-Agent, z.B.
`moon-dev-ai-agents`) soll auf dieser Maschine laufen — ohne bezahlte
Schluessel, mit dem lokalen Ollama, in einem sichtbaren Fenster oder als
Routine. Das Repo ist Fremd-Code: minimal in den eigenen Fork patchen, jede
Abweichung von der Vorlage im Commit benennen.

## Starten (Reihenfolge)

1. **Aus dem Repo-Root starten: `python -m <paket>.<…>` statt
   `python <pfad>.py`.** Ein Skript-Aufruf setzt `sys.path[0]` auf sein
   Skript-Verzeichnis; ein `import src.…` im Skript scheitert dann mit
   `ModuleNotFoundError: No module named 'src'`.
2. **Die .env des Repos nicht dem Skript ueberlassen.** Viele Repo-Agenten
   rufen `load_dotenv()` nie auf; der Wrapper/Shell erbt die Werte nicht und
   der Agent meckert ueber fehlende Schluessel, die in der .env stehen.
   Beim Start exportieren (Bash, CRLF-sicher):
   `export VAR=$(grep '^VAR=' .env | cut -d= -f2 | tr -d '\r')`
3. **Ersten Zyklus im Hintergrund mit Log fahren, DANN das Log lesen.** Der
   Start ist erst belegt, wenn ein Zyklus komplett durchlief: Prozess lebt
   (`Get-CimInstance Win32_Process`, CommandLine-Muster), Log zeigt Daten
   und Urteil, Ergebnisdateien sind frisch.

## Schluessellose Umstellung (Papier-Betrieb)

- **Hart verlangter Schluessel statt Modellwahl:** `ValueError: … not found
  in environment variables` im Konstruktor, obwohl das Modell lokal laufen
  soll — einen Ollama-Zweig einbauen, der nur dann greift, wenn
  `OLLAMA_MODEL` gesetzt ist. Ohne den Zweig crasht der Agent vor jedem
  Zyklus.
- **Base-URL-Falle:** Ollamas OpenAI-kompatibler Weg ist `/v1`, die native
  API `/api`; die .env zeigt oft auf `/api`. Beim SDK-Aufruf auf `/v1`
  normieren, bei der nativen API auf `/api/chat`.
- **LLM-Urteil:** IMMER die native `/api/chat` mit `think: false` nehmen —
  der `/v1/chat/completions`-Weg liefert leeren `content` (Antwort im
  `reasoning`-Feld). Eine lange Folge identischer DO-NOTHING-Urteile ohne
  Fehlermeldung ist das Symptom einer stummen Modellstrecke, kein Marktbild.
  Details: `references/sprachmodell-spur.md`.
- **Pro-only-Endpunkte** (`error_code` 10005 bei CoinGecko o.ae.): auf die
  oeffentliche Alternative umstellen (`/coins/markets` statt
  `top_gainers_losers`), 429er mit Abstand (DELAY ~12 s) + einmaligem Retry
  beantworten und die Analyseanzahl je Zyklus begrenzen. Ehrlich benennen,
  wenn sich dabei die Semantik verschoben hat („neue Coins" → kleinste
  Marketcaps).
- **Versionierte Ergebnis-CSVs im Klon tragen altes Schema:** die
  Zusammenfassung crasht dann (`Error tokenizing data`) und beendet die
  while-Schleife — ein Zyklusfehler darf einen Dauerlaeufer nie beenden.
  Ergebnisdateien aus dem Index nehmen (`git rm`) und die Zusammenfassung
  fehlerfest machen (try/except).
- **Sichtbar ausfuehren („im GUI"):** `Start-Process python -m … -
  WindowStyle Normal -PassThru` mit den exportierten Variablen; die
  sichtbare Konsole ist der Nachweis fuer den Nutzer, der Prozess-Check
  fuer den Agenten.

## Dateien im Repo aendern

`Werkstatt/Repos/*` sind Junctions auf `O:` und liegen ausserhalb von
HERMES_WRITE_SAFE_ROOT — `write_file`/`patch` verweigern. Entweder nach
`Agenten/Hermes/cache/` schreiben und per `cp` ins Repo legen, oder
byte-sauber auf der Datei patchen: Zeilen-Ersetzung mit Trefferzahl-Assertion
(genau 1), Newline aus der Rohdatei ableiten, Umlaute im Anker als Escape
statt Emoji — ein `python -c` mit Nicht-ASCII im Bytes-Literal ist ein
SyntaxError; Emoji-Anker in Patch-Skripten als normalen String schreiben und
`.encode('utf-8')`.

## Regeln

- Ein Fremd-Agent wird NIE als Order-Weg angebunden: keine Orders aus
  Fremd-Code ohne Haus-Gate (Urteil lokal, Daten oeffentlich,
  Einstieg/Ausstieg im Haus-Code — `references/sprachmodell-spur.md`).
- Dauerbetrieb ueber Wrapper + geplante Aufgabe statt Terminalprozess:
  Wrapper-Anforderungen siehe `windows-host-zugriff` (Elevation,
  ExecutionTimeLimit, IgnoreNew, PYTHONIOENCODING).
