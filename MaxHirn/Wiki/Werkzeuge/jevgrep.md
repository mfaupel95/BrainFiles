---
id: 20260930-jevgrep
title: 'jevgrep (jg) — Quelltext finden durch Fragen'
tags: [werkzeuge, fremd, code, agenten]
created: 2026-09-30
updated: 2026-09-30
related: ['[[repos-zentrale]]', '[[Betrieb/Fremd-Material]]', '[[Werkzeuge/Ollama-Bruecke]]']
summary: 'Haus-Installation des Fremd-CLI jevgrep unter Windows: laeuft, kostet rund 4 US-Cent je Suche, braucht aber einen Anbieterschluessel. Der openrouter-Weg ist vermutlich tot.'
---

# jevgrep (`jg`) — Quelltext finden durch Fragen

[jevgrep](https://github.com/dzhng/jevgrep) (MIT, dzhng) beantwortet eine Frage zum
Repository mit **Dateiliste, Lesespuren und Quelltextausschnitten**. Es urteilt nicht
selbst, sondern befragt das Modell **Jev** (TypeSafe) ueber den Quelltext — pro Suche
Hunderte Einzelfragen, gebuendelt. Der Nutzen liegt bei **unbekannten, grossen
Codebestaenden**; wo der Name eines Symbols bekannt ist, ist `search_files`/ripgrep
besser und kostenlos.

Stand 30.09.2026: **installiert und nachgewiesen, aber ohne Schluessel nicht
benutzbar.**

## Was laeuft

| | |
|---|---|
| Installation | `Agenten/Werkzeuge/jevgrep/` (npm-Paket `@dzhng/jevgrep` **0.7.0** in `node_modules`) |
| Aufruf | `Agenten\Werkzeuge\jevgrep\jg.cmd` oder Wurzel-Aufrufer `.\jevgrep.cmd` (aus jedem Verzeichnis) |
| Voraussetzung | Node 22+ auf dem PATH (hier Node 26.7.0); kein npm, kein Bun, kein ripgrep noetig |
| Klon | `Werkstatt/Repos/jevgrep` (origin `mfaupel95/jevgrep`, upstream `dzhng/jevgrep`) |
| Nachweis | `python Agenten/Werkzeuge/jevgrep/test_jevgrep.py` — 6 Tests, 6,7 s, ohne Netz und ohne Schluessel |

## Was fehlt: der Schluessel

`jg auth` verlangt einen Anbieter **und** dessen Schluessel; Umgebungsvariablen werden
ausdruecklich **nicht** ausgewertet. Im Haus ist kein solcher Schluessel vorhanden
(weder in `HKCU\Environment` noch in OmniRoute: dort gibt es nur ein OpenRouter-Konto,
und das ist selbst-deaktiviert).

### Der gratis Weg: OpenCode Zen mit `jev-1.13-free`

Am 01.10.2026 in der Zen-Dokumentation nachgelesen: Zen fuehrt Jev unter **genau dem
Pfad, den jevgrep benutzt** (`https://opencode.ai/zen/v1/systemone`) und hat neben dem
bezahlten `jev-1.13` (0,042 USD/1M Eingabe) ein **zeitweise kostenloses
`jev-1.13-free`** — beide gratis in der Ausgabe. Der Anbieter `opencode` in jevgrep
zeigt auf das *bezahlte* Modell; deshalb meldet man den EIGENEN Endpunkt an:

```
.\jevgrep.cmd auth --provider custom --base-url https://opencode.ai/zen/v1 --model jev-1.13-free --stdin
```

Das Werkzeug dafuer ist `Agenten/Werkzeuge/jevgrep/von_opencode_anmelden.py`: es liest
den Schluessel aus der OpenCode-Anmeldung (`opencode auth login`, Anbieter „OpenCode
Zen"), reicht ihn per stdin an `jg auth` und **gibt ihn nie aus** (auch nicht in
Fehlermeldungen). Trockenlauf ohne `--anwenden`.

| Anbieter | Modell | Bemerkung |
|---|---|---|
| `custom` + Zen | `jev-1.13-free` | **gratis**, derselbe Endpunkt wie der Preset; der empfohlene Weg |
| `vercel` (Vercel AI Gateway) | `typesafe-ai/jev` | gemessen: **0,04 USD je 1M Eingabetoken**, 32K Kontext, Neukunden bekommen ein Gateway-Guthaben |
| `typesafe` | `jev-1.13.0` | Direktanbieter |
| `opencode` (OpenCode Zen) | `jev-1.13` | Pfad und Modell bestaetigt; dieser Preset nimmt die **bezahlte** Variante — fuer gratis `custom` mit `jev-1.13-free` (siehe oben) |
| `openrouter` | `typesafe/jev-1.13` | **vermutlich tot**: OpenRouter kennt nur `typesafe/jev-router`, nicht `jev-1.13` |
| `custom` | frei | jeder TypeSafe-kompatible Endpunkt (Protokoll unten) |

**Kosten gemessen** (Suche ueber `Agenten/Werkzeuge/repos-zentrale`, 171 Dateien,
Attrappe auf 127.0.0.1): 396 Anfragen, 3,24 Mio. Zeichen Zustand ≈ 0,93 Mio. Token
≈ **4 US-Cent**. Grosse Wurzeln kosten entsprechend mehr; die Wurzel ist die
Stellschraube, nicht die Frage.

## Der eigene Endpunkt (Protokoll)

jevgrep haengt an die Basis-URL `/systemone` an und schickt:

```json
{"model":"<id>","state":"<Quelltext-Kontext>","questions":{"q":{"type":"noul","instructions":"Relevant?"}}}
```

erwartet werden **Antworten fuer jede Frage-ID** mit `noul` zwischen 0 und 1:

```json
{"answers":{"q":{"type":"noul","noul":0.9}}}
```

`auth --provider custom --base-url https://…/v1 --model ID --stdin` (nur `https://`,
`http://localhost`/`127.0.0.1` fuer einen lokalen Proxy). Genau dieses Protokoll
beherrscht auch **Laya** lokal — der Gedanke „eigenes Urteil statt bezahltes" ist
trotzdem verworfen, siehe unten.

## Fallen und gemessene Grenzen

- **npm verweigert Windows**: das Paket traegt `"os": ["darwin","linux"]` →
  `EBADPLATFORM`. `npm install … --force` umgeht die Pruefung; der Code laeuft unter
  Node 26.7.0 fehlerfrei (`--version`, `--help`, `files`, `auth`, `doctor`, echte Suche).
- **Nicht als Projektwurzel installierbar**: die veroeffentlichte `package.json` traegt
  `devDependencies` mit `workspace:*` → `EUNSUPPORTEDPROTOCOL`. Als *Abhaengigkeit*
  installiert npm sie problemlos — also `npm install @dzhng/jevgrep@0.7.0 --force`.
- **Jede Suche schickt Quelltext hinaus.** Der Zustand je Anfrage war 20.000–54.000
  Zeichen; die Filter (ignore-Dateien, versteckte, Abhaengigkeiten, Binaer-,
  offensichtliche Zugangsdateien) sind laut Hersteller **keine Garantie**. Vor jeder
  Suche `jg files <ordner>` (kostenlos, kein Netz) und mit `--exclude 'muster'`
  verengen. Vault und Schluesselordner gehoeren nicht in die Wurzel.
- **Ein lokales Urteil ist nicht praktikabel** (gerechnet, nicht geraten): 396 Anfragen
  × ~7.000 Token = 2,4 Mio. Prompt-Token; bonsai-27b schafft 85 t/s Prompt → rund
  **8 Stunden je Suche**. Laya (1.024 Token Kontext) passt schon von der Laenge nicht.
  Damit ist der Gratis-Weg ueber ein lokales Modell keine Option.
- **`jg skill` wurde nicht ausgefuehrt**: fremde SKILL.md werden nicht in die
  Hermes-Bibliothek importiert. Der Text liegt im Paket unter
  `node_modules/@dzhng/jevgrep/dist/skills/jevgrep/SKILL.md`.
- **Keine zweite Installation**: die globale Kopie im Hermes-`tools`-Node wurde
  entfernt (ein `hermes update` ersetzt `tools/` — dort haette `jg` still verschwunden).
  Es gilt die Haus-Installation unter `Agenten/Werkzeuge/jevgrep`.
- Eine Attrappen-Anmeldung in `~/.config/jevgrep/credentials.json` wurde nach dem
  Nachweis **entfernt** — `jg` ist derzeit absichtlich nicht angemeldet.

## Die Anfrage verfeinern

Vier Regeln, die ueber Nutzen und Kosten entscheiden:

1. **Nach Verhalten fragen, nicht nach Namen.** `jg` ist fuer Fragen gebaut, deren
   Antwort in unbekannten Dateien liegt: „Wie wird entschieden, ob …?", „Wo wird
   geprueft, bevor …?", „Welche Sperren greifen, wenn …?". Einen bekannten
   Symbolnamen findet `search_files` schneller und kostenlos.
2. **Eine Frage, ein Satz.** Keine Aufzaehlung, kein „und ausserdem" — jede
   Teilfrage kostet eigene Anfragen.
3. **Die Wurzel ist der Kostenhebel**, nicht die Frage. Gemessen mit
   `jg files <ordner>` (kostenlos, kein Netz, kein Schluessel):

   | Wurzel | berechtigte Dateien | Groesse |
   |---|---|---|
   | `Agenten/Handel/scanner` | 66 | 1,7 MiB |
   | `Agenten/Hermes/skills/brainfiles` | 213 | 2,2 MiB |
   | `Agenten/Bus` | 40 | 11,2 MiB |
   | `Agenten/Handel` | 5.247 | 390,8 MiB |

   Grobe Regel aus der einen Messung: 171 Dateien ≈ 0,93 Mio. Token ≈ 4 US-Cent.
   `Agenten/Handel` als Wurzel ist damit ein Vielfaches einer Scanner-Suche — und
   schickt Daten aus dem Handelshaus hinaus.
4. **Vor jeder Suche verengen**, wenn die Wurzel vertraulich ist:
   `--exclude '**/zustand*.json' --exclude '**/*.csv' --exclude 'daten/'`.

Beispielanfragen, die zu diesem Haus passen:

```
jg "Wie wird entschieden, ob eine offene Position geschlossen wird?" Agenten/Handel/scanner
jg "Wie wird eine Nachricht in Stuecke geteilt und an Telegram zugestellt?" Agenten/Bus
jg "Wo ist beschrieben, wie eine neue Handelsspur angeschlossen wird?" Agenten/Hermes/skills/brainfiles
jg "Wie wird ein Freigabebeleg geprueft, bevor eine Order ausgefuehrt wird?" Agenten/Handel
```

## Nachweis im Detail

`Agenten/Werkzeuge/jevgrep/test_jevgrep.py` startet eine Attrappe eines
TypeSafe-kompatiblen Endpunkts auf einem freien Port, biegt `XDG_CONFIG_HOME` auf einen
Tempordner (die echte Anmeldung bleibt unberuehrt) und prueft: Version, `files` ohne
Netzanfrage, `auth` gegen die Attrappe, `doctor`, eine echte Suche ueber
`Werkstatt/Repos/jevgrep/apps` — und dass die Anfragen wirklich `/systemone` mit
Bearer-Kopf und mitgeschicktem Zustand treffen.