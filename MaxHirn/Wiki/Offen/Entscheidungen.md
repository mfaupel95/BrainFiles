---
id: 20260921-offene-entscheidungen
title: 'Offen — was auf eine Entscheidung wartet'
tags: [offen]
created: 2026-09-21
updated: 2026-09-22
related: ['[[INDEX]]', '[[Betrieb/Sicherung-und-Laufwerke]]', '[[Handel/Spuren-Uebersicht]]']
summary: 'Die offenen Punkte mit dem Stand vom 22.09.2026 — je Punkt: was gemessen ist, was fehlt, was der naechste Schritt ist.'
---

# Offen — was auf eine Entscheidung wartet

**Diese Seite ist eine Wiedervorlage, kein Auftrag.** Jeder Punkt nennt nur Messung und
naechsten Schritt. Erledigtes wird geloescht, nicht durchgestrichen (Historie liegt in Git).

## 1. xperp: Schluessel liefert 50101

Der OKX-EEA-Satz von `xperp` antwortete mit `APIKey does not match current environment`,
obwohl `handel_erlaubt` und `freigabe.erfuellt` true sind und das Fenster offen war.
**Offen:** Konto-seitig klaeren (Host EEA vs. global, IP-Whitelist, read-only-Recht).
Kein Dateischalter loest das. Kandidaten zum Gegenpruefen: signierter Leseaufruf gegen den
Registry-Host, Rechte des Schluessels im OKX-Portal.

## 2. `kraken` bleibt im Papier (aktualisiert 22.09.2026)

**Seit 22.09.2026 laeuft trotzdem eine Kraken-Spur live: `moondev_marktlage`.**
Sie ist die einzige Spur mit fertigem Kraken-Orderweg, deren eigene Messung die gemessene
Gebuehr schlaegt (`kosten_wendepunkt.py`: f_max **+9,00 %** je Runde gegen 1,2 % Kraken-Runde).
Paar **XXBTZEUR** (die Waehrung, in der das Geld liegt — XBTUSD waere an 12,27 USD gescheitert),
Einsatz 60–150 EUR nach Signalstaerke, **ein** Platz (das Signal ist eine Marktlage-Wette),
Ratsche 9,00 = 1,0x Buchrisiko, Kill 27,00. Der Kraken-Blker bleibt nur fuer die Haus-Spur
`kraken` selbst (eigene Rueckrechnung negativ).

**Das Guthaben ist kein Blocker mehr.** Das Konto ist seit dem 22.09.2026 wieder frei
(`EGeneral:Temporary lockout` vorbei): **189,15 EUR** verfuegbar, `mindest_guthaben_eur` 60.

**Der Blocker ist die Gebuehr — und die ist gemessen, nicht angenommen.** Kraken hat an den
Fuellungen vom 22.09.2026 je Seite **0,60 %** berechnet (SOLEUR: Kauf 50,01954 EUR mit
0,30012 EUR, Verkauf 50,01466 EUR mit 0,30009 EUR), und `TradeVolume` meldet taker 0,6000 %
(EUR 3.479 Monatsvolumen, naechste Stufe 0,38 % ab EUR 10.000). Das Kraken-**Pro-Abo wirkt auf
diesem Konto damit nicht** — eine Runde kostet **1,2 %** statt 0. `gebuehr_taker` steht
deshalb auf dem gemessenen `0.006`.

**Stand des Schalters:** `handel_erlaubt = false` (Auftrag Max „Kraken papier", 22.09.2026);
`freigabe.erfuellt` bleibt true; `stillgelegt` ist false. Die Spur laeuft Papier und nennt
den Sperrgrund selbst (`Live waere gesperrt durch: wachen.json handel_erlaubt=false`).
**Offen:** ob die Spur live gehen soll — die eigene Rueckrechnung war schon ohne Gebuehr
**-0,57 % je Runde**, mit 1,2 % ist sie es deutlicher. Reihenfolge, falls doch: erst messen
(Monatsvolumen, Signal ohne Gebuehr), dann `handel_erlaubt`, dann das Fenster.

## 2a. `moondev_signalwelle` — neue Papierspur (22.09.2026)

Angelegt als ehrliches Gegenstueck zu einem VIP-Signal-Kanal (Max' Screenshot: NVDAUSDT
10x, +27 % ROI, ohne Verlusthistorie). 1h-Momentum 3-15 % plus Tagesvolumen >= 20 Mio USD,
Long, deterministisch, **kein Hebel, kein Live-Zweig**. Grenzen: 3 Plaetze, 5 USD Risiko,
Stop 7 %, Ratsche 15 USD. Erster Zyklus am 22.09. buchte 3 Papierpositionen.
**Offen:** nach ein paar Tagen die Auswertung ansehen (`auswertung_alle.py`, `BOT_SPUREN`) —
ob eine 1h-Regel dieser Art ueberhaupt traegt, entscheidet die Stichprobe, nicht der Kanal.

## 2b. `iv_waelle` und `supertrend` sind jetzt bewacht (22.09.2026)

Beide sind still, und bei beiden ist Stille der Normalfall (supertrend stand nach einem
stillen ImportError fuenf Tage ohne Signal; iv_waelle schreibt seit dem 19.09. nichts).
Der Cron `spur-wache` fuehrt jetzt vier junge Spuren und meldet nur, was NEU ist —
zurueckgehaltene Signale, Einstiege, Runden, Stillstand.
**Offen:** nichts zu entscheiden; zu beobachten ist, ob die Meldungen kommen, bevor Max
selbst nachfragt.

## 3. Ausser-Haus-Kopie

`Q:\MaxHirn-AusserHaus` ist vollstaendig und geprueft (150.732 Dateien / 63,74 GB), aber
**nicht verschluesselt** und enthaelt Klartext-Zugangsdaten (`Wissen/Zugaenge.md`,
`Wissen/OKX_API.env`). Ohne angesteckte `Q:`-Platte stecken alle Kopien im selben Rechner.
**Offen:** Verschluesselung oder ein zweiter Ort ausser Haus.

## 4. Abschaltungen des Rechners (T-004)

Kernel-Power 41 mit BugcheckCode 0, kein Minidump, kein WHEA; Netzteiltausch erfolglos.
**Offen:** naechste Verdaechtige sind Kaltgeraetekabel/Steckdose und Lastspitzen. Bis dahin
keine langen Schreiblaeufe ohne Sicherung, keine Windows-Reparaturinstallation.

## 5. Fremd-Klone: Plugins-Ordner und Skill-Baum (22.09.2026 aufgeraeumt)

Die Sammelstelle `Agenten/Hermes/plugins/` war **2,1 GB** gross (21 Eintraege) und ist jetzt
**11 MB**: Wahrheit ist allein `plugins/.install-metadata.json` (drei installierte Plugins:
`memory-wiki` aus dem Katalog, `everything-claude-code`, `one-skill-to-rule-them-all`) plus
`hermes plugins list --json` (60 Plugins, 59x `source: bundled`, 1x `catalog:`). Die lebenden
Claude-Marketplaces liegen unter `~/.claude/plugins/marketplaces/`, nie in diesem Ordner.
Entfernt (alle re-clonbar): nautilus_trader 401M, unsloth 428M, OmniRoute 828M, notebooklm-py 189M,
context7 61M, claude-code 45M, onchainos-skills 31M, claude-plugins-official 18M, cli, financial-services,
chromaprint, public-apis, acoustid-index, EasyCLIProxyAPI, one-skill-to-rule-them-all-main, mfaupel95, productivity.

Im Skill-Baum `Agenten/Hermes/skills/` tragen fuenf Klone **geladene** Skills (OmniRoute 3,
onchainos-skills 4, claude-code 1, one-skill-to-rule-them-all je 1) — die Rumpf-Ordner bleiben, denn die
Skills verweisen hinein (`docs/openapi.yaml`, `src/lib/agentSkills/generator.ts`). Geschnitten wurde nur
das `.git` der drei grossen (570M + 32M + 23M = **625 MB**, je 0 eigene Commits; Arbeitsbaum unveraendert,
`hermes skills list` meldet weiter **113 enabled**).
**Offen:** `Werkstatt/repos-verschoben-aus-skills/` traegt noch 451 MB reine Parkware
(unsloth 426M, chromaprint 9M, public-apis 8,8M, acoustid-index 6,7M, mfaupel95 61K) — verifiziert:
0 eigene Commits, kein SKILL.md, kein Zwilling, keine Routine liest sie. `EasyCLIProxyAPI` ist dort
geloescht (der lebende Klon steht in `Werkstatt/Repos`, 136M, Stand 21.09.).
Verfahren: `laufwerk-platz-schaffen/references/fremd-klon-ballast.md`.

## 6. Profile in `.deleted/`

17 am 19.09.2026 weggelegte Profile (`projectatlas`, `skills`, `superpowers`, `tradingview-mcp`,
`agent-reach`, `nous`, `codex`, `scrapling`, `santiment`, …) sind per `/bot` nicht erreichbar.
**Offen:** zurueckholen, was wieder gebraucht wird — oder liegen lassen.

## 7. Speicher: C: und O: (nachgemessen 23.09.2026)

`C:` ist bei **52,3 GB frei von 475 GB** (89 % belegt) — der Plattendruck ist entschaerft,
kein Umzug von `MaxHirn` noetig. `uv/cache` ist auf 0,8 GB geschrumpft, `uv cache clean`
bleibt ein reproduzierbarer Knopf.

**Wohin der Platz geht, wenn er scheinbar grundlos schwindet** (gemessen waehrend einer
Aufraeumsitzung, in der 3,1 GB freigeraeumt und trotzdem 5–11 GB weniger frei wurden):

| Fund | Groesse | Erklaerung |
|---|---|---|
| `O:\pagefile.sys` | **15,96 GB** | Windows-Auslagerungsdatei, eingestellt 4096–16384 MB, stand am Maximum; letzte Aenderung 22.09. 23:16. Ein Ausbau um 12 GB sieht wie Datenzuwachs aus, ist aber Systemverhalten. |
| `Agenten/_Backups/` | 1,17 GB | Hermes-Notfallkopien vom Update 22.09. 15:20 und 15:37: `state.db` 2 × 408 MB |
| `Agenten/Hermes/state-snapshots/20260922-155224-pre-update/` | 410 MB | dasselbe Update, dritte Kopie |
| `Agenten/Hermes/state.db` | 427 MB | Sitzungsdatenbank selbst |
| `Agenten/Handel/moondev_sniper.log` | **160 MB und wachsend** | Kindprozess des Moon-Dev-Treibers schreibt bis ~50 MB/Tag; keine Drehung |

**Behoben (23.09.2026):** `moondev_dauerlauf.py` dreht eine Agenten-Logdatei beim Start, sobald
sie 50 MB ueberschreitet (`_log_drehen`, Ziel `<name>.log.1`). Gedreht wird **beim Start**, nicht im
Betrieb — ein laufender Agent haelt die Datei offen und Windows verweigert das Umbenennen
(nachgemessen: `mv` schlaegt fehl, solange der Prozess lebt). Der bereits gewachsene
`moondev_sniper.log` faellt beim naechsten Start des Agenten der Drehung anheim; die Aenderung
greift mit dem naechsten Neustart des Treibers (Aufgabe `MaxHirn-MoonDev-Dauerlauf`).
Merkregel: **Wachstum von Dauerprozessen faellt nicht an RAM oder Prozesszahl auf, sondern nur am
Plattenplatz** — wer Platz sucht, sieht zuerst Prozesstabellen an und findet dort nichts.
**Offen:** die beiden 408-MB-Notfallkopien in `_Backups` (Rollmaterial des Updates) sind noch da.

## 8. Marktscanner-Bericht friert ein — der scanner kauft zu Tagespreisen

**Gemessen 22.09.2026:** `scanner/berichte/neuester.json` traegt `erzeugt 2026-09-21T00:08:25Z`;
der scanner kauft seine Vorschlaege aus genau dieser Datei
(`vorschlaege()`: `einstieg = z["preis"]`, daraus Stop und Ziel). Der Tageslauf
`MaxHirn-Marktscanner` (07:30) schreibt **nichts**, weil `marktscanner.ps1` bei laufendem
Dauerlauf mit „ENDE uebersprungen: der Dauerlauf fuehrt die Spur" aussteigt — der
Dauerlauf laeuft aber dauerhaft. Die Sperre war fuer den `handeln.py`-Teil gedacht, der
seit 14.09.2026 gar nicht mehr in der Routine steht; `scan.py` schreibt nur
`berichte/*.json` und kollidiert mit keinem Dauerlauf-Zustand.

**Wirkung in echtem Geld (erste zwei Live-Kaeufe nach dem Import-Fix):**

| Position | gebucht (Berichtspreis) | echter Fill | Stop real | Ziel real | C/R |
|---|---|---|---|---|---|
| `ETH-USDC` | 2655,28 | 2773,36 | −9,8 % | +6,8 % | 0,69:1 |
| `SOL-USDC` | 111,71 | 118,63 | −11,8 % | +6,0 % | 0,51:1 |

Geplant war **2:1**. Beide Positionen stehen damit mit umgekehrtem Chance/Risiko im Buch.

**Offen:** Entscheidung, ob der Marktscanner wieder taeglich rechnen darf (Skip-Wache auf
den `handeln.py`-Teil verkuerzen, `scan.py` durchlassen) — oder ob der scanner einen
**frischen Kurs** beim Einstieg nehmen soll (`okx.letzter_kurs`) statt des Berichtspreises.