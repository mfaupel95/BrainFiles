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
| Klon | `Werkstatt/jevgrep` (origin `mfaupel95/jevgrep`, upstream `dzhng/jevgrep`) |
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
den Schluessel aus der Prozessumgebung, sonst direkt aus der Registry
(`OPENCODE_API_KEY`, `OPENCODE_ZEN_API_KEY`, `ZEN_API_KEY` — ein frisch gesetztes
`setx` sieht ein laufender Prozess nicht), sonst aus der OpenCode-Anmeldung
(`opencode auth login`, Anbieter „OpenCode Zen"), reicht ihn per stdin an `jg auth`
und **gibt ihn nie aus** (auch nicht in Fehlermeldungen). Trockenlauf ohne
`--anwenden`. Nicht per `reg query` lesen — das gibt den Wert im Klartext aus.

**Stand 01.10.2026: `OPENCODE_API_KEY` ist als Windows-Benutzervariable gesetzt
(51 Zeichen), `jg` ist angemeldet und `jg doctor` antwortet „Jev connection verified
through Custom endpoint (opencode.ai)".** Kosten: 0 (freies Modell).

**Im Vordergrund aufrufen.** Ein Hintergrundprozess bricht sofort mit
`stdin is not a tty` und Exit 1 ab (gemessen 01.10.2026); in eine Datei umleiten geht
trotzdem. Erste echte Suchen: `Agenten/Handel/scanner` (66 Dateien) **6,2 s** und
22 relevante Dateien (handeln.py, tests/test_zielsperre.py, boersenstops.py — genau die
Stellen, die die Frage meint); `Agenten/Bus` (40 Dateien) 9 Treffer. Zweiter Lauf
ueber dieselbe Wurzel 8,7 s, weil die Antworten im Cache liegen (`~/.cache/jevgrep`).

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

## Ein anderes Modell: die eigene Bruecke (auch lokal)

Der Anbieter ist austauschbar. `Agenten/Werkzeuge/jevgrep/jev_bruecke.py` nimmt die
jevgrep-Anfragen an (`POST <basis>/systemone`) und beantwortet sie ueber ein
**OpenAI-kompatibles** Modell der Wahl — Ollama lokal, Inception Mercury 2.5, Nous,
OmniRoute. Gefordert sind nur: JSON rein/raus, je Kennung ein `noul` zwischen 0 und 1,
**32k Kontext** (Zustaende sind 20.000-54.000 Zeichen), sauberes JSON, und Durchsatz
fuer 60-400 Anfragen je Suche. Ein Chat-Modell mit Werkzeugen braucht es nicht.

```powershell
python Agenten\Werkzeuge\jevgrep\jev_bruecke.py      # laeuft lokal, Ollama-Standard
'lokal' | .\jevgrep.cmd auth --provider custom --base-url http://127.0.0.1:8742/v1 --model bruecke --stdin
.\jevgrep.cmd doctor
```

**Gemessen und ernuechternd** (01.10.2026, lokales Ollama):

| Befund | Messung |
|---|---|
| erster Anlauf | `HTTP 404 model 'qwen35-8k:latest' not found` bei **jeder** Frage -> alle Dateien galten als „nicht relevant" |
| zweiter Anlauf, `gemma-e4b-8k-64k` | `HTTP 500 out-of-memory` (llama-server wollte 3,7 GB) — die bekannte Speichernot des Rechners |
| direkter Modellaufruf, 20.000 Zeichen `handeln.py`, „zeigt das, wann eine Position geschlossen wird?" | **51 s**, Antwort **0.0** — also FALSCH fuer eine Datei, die genau das tut |

Die Bruecke ist damit **mechanisch fertig, aber ein lokales Modell ist als Richter
nicht belastbar**: zu langsam, speicherfragil, und bei 20.000+ Zeichen Zustand
unzuverlaessig (eine Einzelmessung mit anderer Fragestellung hatte noch 0,95/0,85/0,75
geliefert — genau diese Streuung ist das Problem). Die Bruecke meldet solche Ausfaelle
jetzt im Protokoll und auf der Konsole (`leere Modellantwort`, `HTTP 404/500`), statt
sie in `0.0` verschwinden zu lassen.

**Folge:** fuer echte Suchen bleibt der Jev-Weg (OpenCode Zen bezahlt ~4 US-Cent je
Suche, oder Vercel). Mercury 2.5 hinter derselben Bruecke ist der naechste Kandidat
(260k Kontext, 1.107 tok/s, Schema-JSON, 100 Mio. Gratis-Token) — dafuer fehlt ein
Inception-Schluessel und ein Qualitaetsvergleich gegen Jev.

Nachweis ohne jeden Schluessel: `python Agenten/Werkzeuge/jevgrep/test_jev_bruecke.py`
(8 Tests, inklusive echtem Durchlauf jevgrep -> Bruecke -> Modell -> Trefferliste).
Eine laufende Bruecke pruefen: `python Agenten/Werkzeuge/jevgrep/pruefe_bruecke.py`.

## So nutzt du es (Bedienung)

1. **Wurzel klein waehlen** — `.\jevgrep.cmd files <ordner>` sagt kostenlos, was eine
   Suche lesen wuerde. `Agenten\Handel\scanner` (66 Dateien) ist gut, `Agenten\Handel`
   (5.247 Dateien) ist zu gross.
2. **Nach Verhalten fragen**, ein Satz, keine Aufzaehlung:
   `.\jevgrep.cmd 'Wie wird entschieden, ob eine offene Position geschlossen wird?' Agenten\Handel\scanner`
3. **Treffer nachlesen** — `jg` liefert Lesespuren und Quelltextausschnitte, keine
   Antwort. Eine Trefferliste ohne nachgelesene Stelle ist kein Befund.
4. **Im Vordergrund** aufrufen; ein Lauf dauert bei Mercury 1-2 Minuten fuer 66 Dateien.
5. **Kosten im Blick**: ~1,8 US-Cent je Suche (Mercury, Aktion), 10 Mio. Gratis-Token je
   Schluessel ≈ 22 Suchen. Antworten liegen in `~/.cache/jevgrep`, ein zweiter Lauf
   derselben Frage ueber derselben Wurzel kostet nichts.
6. **Nicht vergessen:** jede Suche schickt Quelltext an den Anbieter. Vault,
   Schluesselordner und Personenbezogenes gehoeren nicht in die Wurzel.

**Der Vorschalter prueft vor jeder Suche** (`jg_sicher.py` + `vorpruefung.py`):
Anbieter erreichbar (sonst startet er die Bruecke und bricht bei 429/402/403 mit dem
Grund ab), Wurzelgroesse (ueber **300 Dateien oder 60 MiB** wird abgelehnt, `--trotzdem`
erzwingt) und die Kostenschaetzung samt heutiger Ausgabe:

```
Anbieter bruecke ueber http://127.0.0.1:8742/v1 antwortet (0.6 s) | Wurzel Agenten/Handel/scanner: 66 Dateien, 1.7 MiB | grob 0.4 Mio. Token, 0.02 US-Dollar
  heute schon 211 Anfragen ueber die Bruecke, grob 0.04 US-Dollar
```

`--leise` schweigt bei Erfolg. Subkommandos (`files`, `auth`, `doctor`) laufen ungeprueft
durch — `.\jevgrep.cmd files <ordner>` bleibt also der kostenlose erste Blick.

**Die Bruecke laeuft automatisch.** Der Hermes-Cron `jev-bruecke-wache`
(Job `7a2d058e063e`, alle 15 Minuten, `no_agent`) prueft Port 8742 und startet die
Bruecke, wenn sie aus ist — leere Ausgabe heisst: alles laeuft. Von Hand:
`Agenten\Werkzeuge\jevgrep\bruecke-mercury.cmd`. Ohne laufende Bruecke kann `jg`
nicht suchen, weil die Anmeldung auf `127.0.0.1:8742` zeigt.

## Mercury 2.5 laeuft — Kopf an Kopf mit Jev

Seit 01.10.2026 ist die Bruecke mit **Inception Mercury 2.5** verdrahtet
(`INCEPTION_API_KEY` als Windows-Benutzervariable, wird aus der Registry gelesen).
Starten: `Agenten\Werkzeuge\jevgrep\bruecke-mercury.cmd` — Fenster offen lassen,
solange gesucht wird.

| | Jev (OpenCode Zen) | Mercury 2.5 (ueber die Bruecke) |
|---|---|---|
| Suche `Agenten/Handel/scanner` (66 Dateien) | 6,2 s | **56,7 s** |
| Treffer | 22 | 13 |
| Anfragen / Token | — | 70 / ~447.000 |
| Kosten je Suche | 0 im Gratis-Kontingent, sonst ~4 US-Cent | **1,8 US-Cent** (Promo 0,04 USD/1M), 8,9 Cent Listenpreis |
| Kontingent | Gratis-Limit war nach ~10 Suchen weg | 10 Mio. Gratis-Token je Schluessel ≈ **22 Suchen**, Free-Plan 100 Mio. ≈ 220 |
| Antwortzeit je Anfrage | — | Median 1,40 s (0,42-7,38 s) |

Beide liefern dieselben Kernstellen (`handeln.py`, `boersenstops.py`,
`wachen_pruefung.py`). Mercury ist langsamer (jevgrep wartet auf mehr Runden), dafuer
unabhaengig vom Gratis-Limit. **Das lokale Modell bleibt draussen** — es war 51 s
langsam und urteilte falsch.

**Zurueck zu Zen** (ersetzt die gespeicherte Anmeldung, die Bruecke braucht dann
nicht zu laufen):

```powershell
python Agenten\Werkzeuge\jevgrep\von_opencode_anmelden.py --anwenden
```

## Wenn nichts geht: zwei Antworten, gemessen

`Agenten/Werkzeuge/jevgrep/sonde_zen.py` fragt den Endpunkt direkt (ohne jevgrep) und
nennt HTTP-Status und Dauer; der Schluessel kommt aus der Benutzervariable und wird nie
ausgegeben. Damit sind die zwei Faelle auseinanderzuhalten:

| Antwort | Bedeutung | Was hilft |
|---|---|---|
| `429 FreeUsageLimitError` | das **freie** Kontingent ist aufgebraucht (01.10.2026 nach rund zehn Suchen an einem Abend) | spaeter erneut versuchen; das Limit ist ein Zeitfenster, kein Verbrauch fuer immer |
| `402 Insufficient account funds` | das **bezahlte** `jev-1.13` und das Konto hat kein Guthaben | Guthaben bei OpenCode Zen aufladen (0,042 USD/1M Eingabe ≈ 4 US-Cent je Suche) |
| `403 error code 1010` | Cloudflare weist die Anfrage ab — **nicht** der Schluessel (die Sonde mit Browser-Kennung antwortet dann normal) | nichts am Schluessel aendern |
| Exit 1 ohne jede Ausgabe | der Anbieter hat die Anfrage abgewiesen; jevgrep nennt den Grund nicht | Sonde laufen lassen, dann erst handeln |

Der Schluessel selbst war nie das Problem: `jg doctor` antwortet „Jev connection
verified", solange das Kontingent traegt.

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
`Werkstatt/jevgrep/apps` — und dass die Anfragen wirklich `/systemone` mit
Bearer-Kopf und mitgeschicktem Zustand treffen.