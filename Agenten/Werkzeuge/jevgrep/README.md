# jevgrep (`jg`) — Quelltext finden durch Fragen

Haus-Installation von [jevgrep](https://github.com/dzhng/jevgrep) (MIT), gepinnt auf
**0.7.0**. Der Klon liegt daneben in `Werkstatt/jevgrep` (origin =
`mfaupel95/jevgrep`, upstream = `dzhng/jevgrep`).

## Aufruf

```
Agenten\Werkzeuge\jevgrep\jg.cmd --version
Agenten\Werkzeuge\jevgrep\jg.cmd files <projektordner>
Agenten\Werkzeuge\jevgrep\jg.cmd "Wie wird ein Projekt gestartet?" <projektordner>
```

Voraussetzung: **Node 22+** auf dem PATH (hier: Node 26.7.0). Der Aufrufer setzt kein
npm ein; die Abhaengigkeiten (`typescript`, `web-tree-sitter`) liegen in
`node_modules/`.

## Erst einrichten (braucht einen Schluessel)

**Gratis zuerst: OpenCode Zen mit `jev-1.13-free`.** Zen bedient Jev unter genau dem
Pfad, den jevgrep benutzt (`https://opencode.ai/zen/v1/systemone`), und fuehrt neben
`jev-1.13` (0,042 USD/1M) ein zeitweise kostenloses `jev-1.13-free`.

1. Schluessel als Windows-Benutzervariable ablegen:
   `setx OPENCODE_API_KEY "<wert>"` (oder `opencode auth login`, Anbieter „OpenCode
   Zen" — dann steht er in `~/.local/share/opencode/auth.json`).
2. In jevgrep eintragen, ohne dass der Wert im Klartext erscheint:

```
python von_opencode_anmelden.py              # Trockenlauf: zeigt nur die Quelle und die Laenge
python von_opencode_anmelden.py --anwenden --doctor
```

Das Werkzeug liest den Schluessel aus der Prozessumgebung, sonst direkt aus der
Registry (`OPENCODE_API_KEY`, `OPENCODE_ZEN_API_KEY`, `ZEN_API_KEY` — ein frisch
gesetztes `setx` sieht ein laufender Prozess nicht), sonst aus der OpenCode-Anmeldung.
**Nicht** per `reg query` lesen: das gibt den Wert im Klartext aus.

**Bricht ein Lauf sofort mit Exit 1 und ohne Ausgabe ab, ist der Anbieter schuld, nicht
der Schluessel** — meist ist das freie Kontingent aufgebraucht. Pruefen mit der Sonde
(ohne jevgrep, ohne den Schluessel auszugeben):

```
python Agenten\Werkzeuge\jevgrep\sonde_zen.py
```

`429 FreeUsageLimitError` = freies Kontingent weg (spaeter erneut), `402 Insufficient
account funds` = bezahltes Modell ohne Guthaben, `403 error code 1010` = Cloudflare
(nicht der Schluessel). Die Zeile `stdin is not a tty` ist MSYS-Rauschen und erscheint
auch bei gelungenen Laeufen. Erste echte Suchen (01.10.2026): `Agenten/Handel/scanner`
(66 Dateien) **6,2 s**, 22 relevante Dateien; `Agenten/Bus` (40 Dateien) 9 Treffer.
Zweiter Lauf ueber dieselbe Wurzel 8,7 s, weil die Antworten im Cache liegen.

Alternativ der bezahlte Vercel-Weg (0,04 USD/1M Eingabe, Neukunden-Guthaben):
`vercel.com → AI Gateway → API Keys → Create key`, dann

```
jg.cmd auth --provider vercel --stdin < datei-mit-schluessel
```

```
jg.cmd auth            # Anbieter waehlen, Schluessel eingeben (interaktiv)
jg.cmd doctor          # prueft den Zugang mit einer Testfrage
```

Anbieter laut `packages/core/src/providers.ts`:

| Name | Basis | Modell |
|---|---|---|
| `vercel` | `https://ai-gateway.vercel.sh/typesafe/v1` | `typesafe-ai/jev` |
| `typesafe` | `https://api.typesafe.ai/v1` | `jev-1.13.0` |
| `openrouter` | `https://openrouter.ai/api/v1` | `typesafe/jev-1.13` |
| `opencode` | `https://opencode.ai/zen/v1` | `jev-1.13` |
| `custom` | eigener TypeSafe-kompatibler Endpunkt | frei |

Der Schluessel liegt danach in `~/.config/jevgrep/credentials.json` (nur der Eigentuemer
darf lesen). Umgebungsvariablen werden **nicht** ausgewertet.

Gemessener Preis (Vercel AI Gateway, 30.09.2026): **0,04 USD je 1M Eingabetoken**,
Kontext 32K. Eine Suche ueber `Agenten/Werkzeuge/repos-zentrale` (171 Dateien) machte
396 Anfragen mit zusammen 3,24 Mio. Zeichen Zustand — grob **4 US-Cent je Suche**.

**`openrouter` ist vermutlich tot**: der Anbieter kennt nur `typesafe/jev-router`,
nicht `typesafe/jev-1.13`. Vor dem Kauf pruefen.

## Vor dem ersten Lauf: Umfang ansehen (kostenlos, kein Netz)

```
jg.cmd files <ordner>            # zaehlt die Dateien, die eine Suche lesen darf
```

Jede Suche **schickt den Quelltext** berechtigter Dateien an den gewaehlten Dienst.
Die Filter (ignore-Dateien, versteckte, Abhaengigkeits-, Binaer- und offensichtliche
Zugangsdateien) sind ausdruecklich **keine Garantie**. Deshalb: Wurzel bewusst waehlen
und mit `--exclude 'muster'` verengen. Fuer den Vault und alles mit Schluesseln ist das
Werkzeug nicht gedacht.

## Windows-Besonderheiten (gemessen 30.09.2026)

- Das npm-Paket traegt `"os": ["darwin","linux"]` — `npm install -g` bricht mit
  `EBADPLATFORM` ab. **`--force` umgeht die Pruefung**, der Code laeuft unter Windows
  fehlerfrei (Node 26.7.0: `--version`, `--help`, `files`, `auth`, `doctor` und eine
  echte Suche gegen eine Attrappe geprueft).
- Die veroeffentlichte `package.json` traegt `devDependencies` mit `workspace:*`.
  Als Projektwurzel laesst sie sich deshalb nicht installieren (`EUNSUPPORTEDPROTOCOL`);
  als Abhaengigkeit installiert npm sie problemlos.
- `jg skill` wurde **nicht** ausgefuehrt: der Haus-Regel folgend werden fremde
  SKILL.md nicht in die Hermes-Bibliothek importiert. Der Skill-Text liegt im Paket
  unter `node_modules/@dzhng/jevgrep/dist/skills/jevgrep/SKILL.md`.

## Ein anderes Modell: die eigene Bruecke (lokaler Betrieb moeglich)

jevgrep fragt kein Chat-Modell, sondern einen **Richter**: es schickt einen Zustand
(Quelltext) und mehrere typisierte Fragen und erwartet je Frage eine Zahl 0..1. Genau
das uebersetzt `jev_bruecke.py` auf ein **OpenAI-kompatibles** Modell der Wahl.

**Gefordert sind nur sechs Dinge** (gemessen an jevgrep 0.7.0):

| Anforderung | Wert |
|---|---|
| Endpunkt | `POST <basis>/systemone`, JSON rein, JSON raus |
| Antwortform | `{"answers":{"<kennung>":{"type":"noul","noul":0.0..1.0}}}` fuer **jede** Kennung |
| Kontext | Zustaende 20.000-54.000 Zeichen (~6.000-15.000 Token) -> **32k Kontext noetig** |
| Buendelung | 1-8 Fragen je Anfrage (Antworten in einem Durchgang) |
| Ausgabe | sauberes JSON (Schema-Ausgabe hilft, sonst Nachfassen) |
| Durchsatz | 60 Anfragen (66 Dateien) bis 396 (171 Dateien) je Suche |

Ein Chat-Modell mit Werkzeugen oder Agent-Faehigkeiten braucht es **nicht** — nur
Urteil und JSON.

```
python jev_bruecke.py                 # lokal: Ollama 127.0.0.1:11434, Modell umstellbar
set JEVCREP_BRUECKE_BASIS=https://api.inceptionlabs.ai/v1
set JEVCREP_BRUECKE_MODELL=mercury-2.5
set JEVCREP_BRUECKE_SCHLUESSEL=<key>
python jev_bruecke.py
```

Einmalig bei jevgrep anmelden — der Wert darf beliebig sein, der Dienst laeuft lokal
(`--stdin` verlangt nur einen nicht-leeren Wert):

```powershell
'lokal' | .\jevgrep.cmd auth --provider custom --base-url http://127.0.0.1:8742/v1 --model bruecke --stdin
.\jevgrep.cmd doctor
```

**Gemessen und ernuechternd** (01.10.2026, lokales Ollama):

| Befund | Messung |
|---|---|
| erster Anlauf | `HTTP 404 model 'qwen35-8k:latest' not found` bei **jeder** Frage -> alle Dateien galten als „nicht relevant" |
| zweiter Anlauf, `gemma-e4b-8k-64k` | `HTTP 500 out-of-memory` (llama-server wollte 3,7 GB) |
| direkter Modellaufruf, 20.000 Zeichen `handeln.py`, „zeigt das, wann eine Position geschlossen wird?" | **51 s**, Antwort **0.0** — FALSCH fuer eine Datei, die genau das tut |

Die Bruecke ist mechanisch fertig, aber ein lokales Modell ist als Richter **nicht
belastbar** (langsam, speicherfragil, bei 20.000+ Zeichen unzuverlaessig). Ausfaelle
stehen jetzt im Protokoll und auf der Konsole, statt in `0.0` zu verschwinden.

Fuer echte Suchen bleibt der Jev-Weg (Zen bezahlt ~4 US-Cent je Suche). Mercury 2.5
hinter derselben Bruecke ist der naechste Kandidat (260k Kontext, 1.107 tok/s,
100 Mio. Gratis-Token). Nachmessen: `python messung_lokal.py <modell> [zeichen]`,
laufende Bruecke pruefen: `python pruefe_bruecke.py`.

## Mercury 2.5 (Inception) — verdrahtet und gemessen

`INCEPTION_API_KEY` als Windows-Benutzervariable, Start ueber
`bruecke-mercury.cmd` (Fenster offen lassen). Gemessener Kopf-an-Kopf-Vergleich,
Suche ueber `Agenten/Handel/scanner` (66 Dateien):

| | Jev (Zen) | Mercury 2.5 |
|---|---|---|
| Dauer | 6,2 s | **56,7 s** |
| Treffer | 22 | 13 |
| Anfragen / Token | — | 70 / ~447.000 |
| Kosten je Suche | 0 im Gratis-Limit, sonst ~4 US-Cent | **1,8 US-Cent** (Promo), 8,9 Cent Liste |
| Gratis-Kontingent | Limit war nach ~10 Suchen weg | 10 Mio. Token je Schluessel ≈ 22 Suchen |

Beide finden dieselben Kernstellen (`handeln.py`, `boersenstops.py`,
`wachen_pruefung.py`). Zurueck zu Zen:
`python von_opencode_anmelden.py --anwenden`.

## Vorschalter: erst pruefen, dann Geld ausgeben

`jevgrep.cmd` ruft nicht mehr jevgrep direkt, sondern `jg_sicher.py` — Subkommandos
(`files`, `auth`, `doctor`, `skill`, `--help`, `--version`) laufen ungeprueft durch,
eine **Suche** bekommt vorher die Vorpruefung:

1. **Anbieter** — laeuft die Bruecke? Wenn nein, wird sie ueber die Wache gestartet.
   Danach ein Testaufruf mit einer winzigen Frage an denselben Endpunkt (fast kostenlos).
   Bei 429/402/403/500 wird die Suche **nicht** gestartet, mit dem Grund im Klartext.
2. **Wurzelgroesse** — `jg files` (kostenlos) nennt Dateien und MiB. Ueber **300 Dateien
   oder 60 MiB** wird abgelehnt; `--trotzdem` erzwingt den Lauf.
3. **Kostenschaetzung** — aus der gemessenen Beziehung (1,7 MiB ≈ 447.000 Token ≈
   1,8 US-Cent) plus die heutige Ausgabe aus dem Bruecken-Protokoll.

```
Anbieter bruecke ueber http://127.0.0.1:8742/v1 antwortet (0.6 s) | Wurzel Agenten/Handel/scanner: 66 Dateien, 1.7 MiB | grob 0.4 Mio. Token, 0.02 US-Dollar
  heute schon 211 Anfragen ueber die Bruecke, grob 0.04 US-Dollar
```

`--leise` schweigt bei Erfolg (fuer Skripte). Nachweis ohne Netz:
`python test_vorpruefung.py` (8 Tests: Subkommando, fehlende Anmeldung, toter Anbieter,
gute Suche mit Kosten, zu grosse Wurzel, `--trotzdem`, `--leise`, und dass jevgrep die
eigenen Schalter nie zu sehen bekommt).

## Nachweis

`Werkzeuge/jevgrep/test_jevgrep.py` faehrt eine Attrappe eines
TypeSafe-kompatiblen Endpunkts (127.0.0.1) und prueft den ganzen Weg: `auth` gegen die
Attrappe, `doctor`, eine echte Suche, und dass die Anfragen wirklich die Attrappe
treffen. Danach wird die Attrappen-Anmeldung wieder entfernt.