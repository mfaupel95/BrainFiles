# jevgrep (`jg`) — Quelltext finden durch Fragen

Haus-Installation von [jevgrep](https://github.com/dzhng/jevgrep) (MIT), gepinnt auf
**0.7.0**. Der Klon liegt daneben in `Werkstatt/Repos/jevgrep` (origin =
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

```
jg.cmd auth            # Anbieter waehlen, Schluessel eingeben (interaktiv)
jg.cmd auth --provider vercel --stdin < schluessel.txt
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

## Nachweis

`Werkzeuge/jevgrep/test_jevgrep.py` faehrt eine Attrappe eines
TypeSafe-kompatiblen Endpunkts (127.0.0.1) und prueft den ganzen Weg: `auth` gegen die
Attrappe, `doctor`, eine echte Suche, und dass die Anfragen wirklich die Attrappe
treffen. Danach wird die Attrappen-Anmeldung wieder entfernt.