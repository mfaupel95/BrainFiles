---
id: 20260929-sammelauftrag
title: 'Sammelauftrag Betrieb 29.09.2026'
tags: [betrieb, uebergabe, handel, sicherung]
created: 2026-09-29
updated: 2026-09-29
related: ['Handelsregeln', 'Routinen', 'Schutzregeln']
summary: 'Sechs belegte offene Punkte aus Betrieb, Pruefung und Arbeitsbaum - je mit Fertig-Kriterium und Pruefkommando.'
---

# Sammelauftrag Betrieb 29.09.2026

Stand 2026-09-29. Quellen: `git status`, `sammeln.py`, `systempruefung-2026-09-29.log`,
`Routinen/logs/*.log`, `Get-ScheduledTaskInfo`, Sitzungsspeicher. Basis-Commit der
Aufnahme: `8b3d6a3` (nur zum Wiederfinden, nicht der Stand der Datei).

## Offen

| # | Auftrag | Beleg | Fertig woran zu sehen | Pruefkommando | Weg |
|---|---|---|---|---|---|
| 1 | Push der Routine `fremdarbeit-einziehen` reparieren (403) | `Agenten/Routinen/logs/fremdarbeit-letzter-lauf.log`, Lauf 2026-09-28 20:40: `ENDE ok - 5c80b19 mit 5 uebernommenen Datei(en), Push fehlgeschlagen: remote: Write access to repository not granted ... error: 403` | Der 20:40-Lauf endet ohne `Push fehlgeschlagen`; am Morgen danach ist `git log --oneline origin/master..master` leer | `tail -3 Agenten/Routinen/logs/fremdarbeit-letzter-lauf.log` **und** `git log --oneline origin/master..master \| wc -l` | Auftrag (Ursache: Anmeldedaten im Kontext der geplanten Aufgabe) |
| 2 | Zweitkopie laeuft seit 27.09. mit Exitcode 1 | `logs/zweitkopie-letzter-lauf.log`, 28.09. 21:02: `FEHLER 5 (0x00000005) ... Agenten\Hermes\cache\uv\sdists-v9\editable\...\hermes_agent-0.0.0-0.editable-py3-none-any.whl / Zugriff verweigert`, danach `robocopy-Code 11 - FEHLER. ENDE FEHLER - Exitcode 1 nach 177 s`; Aufgabe `MaxHirn-Zweitkopie` `LastTaskResult 1` | Log endet mit `robocopy-Code 0/1 - erfolgreich.` und enthaelt kein `FEHLER 5` | `powershell -NoProfile -File Agenten/Routinen/zweitkopie.ps1` (Laufzeit ~3 min), danach `grep -c "FEHLER 5" Agenten/Routinen/logs/zweitkopie-letzter-lauf.log` = 0 | Auftrag, Stufe 1 (erst `.bak`, dann echter Lauf) |
| 3 | Fehlalarm der Tagespruefung: „Herzschlag 204 min alt - laeuft die Spur ueberhaupt?" | `logs/systempruefung-2026-09-29.log` Z. 64 und 90; Ursache belegt: `Agenten/Handel/spiegelstand.py:190` liest `zustand.json` (Papier) und `:193 alter = alter_minuten(z.get("letzter_lauf"))`. `moondev_marktlage` laeuft aber live und schreibt `zustand.live.json` (letzter_lauf 15:18, Takt 15 min); der Papierstand fror am 29.09. 03:39 ein | `python Agenten/Handel/spiegelstand.py` zeigt fuer `moondev_marktlage` ein Alter unter einer Zykluslaenge, und Block 11 der Systempruefung meldet keinen Herzschlag-Hinweis mehr | `cd Agenten/Handel && .venv/Scripts/python.exe spiegelstand.py \| grep moondev_marktlage` | Auftrag, Code (Regel: den FRISCHESTEN der beiden Staende nehmen - dasselbe Muster wie `moondev_marktlage._papier_zustand()`) |
| 4 | `okx_bot_waechter`: `herzschlag_max_minuten` fehlt, Tagespruefung meldet es jeden Lauf | `wachen.json` des Ordners hat den Schluessel nicht (nachgemessen: `herzschlag_max_minuten is None`); `systempruefung-2026-09-29.log` Z. 93: `Handel/okx_bot_waechter: Herzschlag 0 min statt 180` | Block 11b meldet `33 von 33` (oder der Ordner wird als Werkzeug ohne Buch gar nicht mehr geprueft) | `powershell -NoProfile -Command "& Agenten/Routinen/systempruefung.ps1" \| Select-String '11b' -Context 0,3` | Auftrag (Regel entscheiden: Werkzeug ohne Handelsbuch ausschliessen ODER 180 setzen - 180 waere hier eine Zahl ohne Bedeutung, weil die Spur nie eine Position haelt) |
| 5 | Docker-Engine antwortet nicht - Container `nautilus-demo` fehlt | `docker ps -a` → `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine ... daemon is running`; `systempruefung-2026-09-29.md`: „Docker-Engine antwortet nicht (Frist 20 s) - Container nautilus-demo ungeprueft" | `docker ps` listet `nautilus-demo` als `Up`; der OKX-Demo-Quoten-Node liefert wieder Quotes | `docker ps --format '{{.Names}} {{.Status}}'` | Auftrag (Docker Desktop starten, dann `docker start nautilus-demo`; ohne Engine fuellt der OKX-Arm des Nautilus nie) |
| 6 | T-129: Fristwaechter fuer die Ausser-Haus-Kopie bauen | Steht bereits als T-129 in `MaxHirn/Archiv/TASKS.md`; Beleg dort: Kopie am 25.09. **13 Tage alt**, 89.421 Dateien fehlten, ohne Meldung | Ein Hermes-Cron meldet nur, wenn `Q:\MaxHirn-AusserHaus` aelter als N Tage ist; leere Ausgabe sonst; er kopiert selbst nichts | `cronjob action='list'` zeigt den Auftrag; ein Lauf gegen ein kuenstlich altes Verzeichnis liefert genau eine Meldung | **Routine 6b** (Hermes-Cron `no_agent`, Muster `Agenten/Hermes/scripts/spiegelfrist-wache.py`) - kein neuer Task, T-129 existiert |

## Nicht aufgenommen (kein Fertig-Kriterium)

- **`repo-updates-check`: Cron-Status `error`, „Script exited with code 15" (28.09. 09:15).**
  Heute von Hand nachgemessen: `python Agenten/Hermes/scripts/repo-updates-check.py`
  endet mit **EXIT 0** und listet 21 gepruefte Klone. Kein reproduzierbarer Fehler,
  also kein Auftrag. Auffaellig bleibt: `laya` haengt 658 Commits zurueck, und geprueft
  werden 21 Klone, waehrend `Agenten/Werkzeuge/repos-updaten.py` von 29 spricht.
- **Sieben absolute Benutzerpfade in Codezeilen** (Portabilitaets-Block der
  Systempruefung). Fuenf davon liegen unter `profiles/*/cache/scratch/` und sind
  Wegwerfskripte; echt sind `Agenten/Handel/ai4trade/neu_anlegen.py:25` und
  `Agenten/Hermes/scripts/bonsai-provider-einbauen.py:15`. Zu klein fuer einen
  eigenen Punkt - beim naechsten Anfassen mitziehen.
- **9 uncommittete Dateien aelter als 1 h.** Sie sind die Aufgabe der Routine
  `fremdarbeit-einziehen` (taeglich 20:40) und warten nur darauf, dass Punkt 1
  repariert ist. Kein eigener Handgriff.
- **Vier unpushed Commits (`f571251`, `5dcbe84`, `350f17b`, `fc3e9cb`).** In dieser
  Sitzung gepusht, `master == origin/master` (27a4466). Nur als Beleg notiert, kein
  offener Punkt - die Ursache ist Punkt 1.

## Nicht angefasst

- **Fremde, laufende Sitzung im Handel-Baum.** Frisch geschrieben und in Arbeit:
  `Agenten/Handel/moondev_historie.py`, `Agenten/Handel/tests/test_replay.py`,
  `Agenten/Hermes/scripts/gateway-identitaet-wache.py` (11 min),
  `Agenten/Handel/tests/test_gateway_identitaet_wache.py` (14 min) sowie die Commits
  `8b3d6a3`, `350f17b`, `fc3e9cb` (Backtest-Fundament, Aufgaben 1-3). Nicht committet,
  nicht bewegt.
- **`Agenten/Routinen/handel-tests.ps1`** (neu, 79 min, unversioniert) samt
  `Agenten/Handel/testlauf.py`. Der Wrapper hat Bus-Anbindung (`routine/handel-tests`)
  und ist damit automatisch eine Routine - aber **ohne geplante Aufgabe und ohne Zeile
  in `Wissen/Routinen.md`**. Nach dem Hausgrundsatz „angebunden ist nicht gestartet"
  meldet sie nie. Bewusst nicht angefasst: die Datei gehoert einer laufenden Sitzung,
  die die Basislinie (`testlauf_basis.json`) noch setzt. Entscheidung dort, nicht hier.
- **`Agenten/Handel/xperp/wachen.json`** (60 min, uncommittet) - fremde Aenderung,
  nicht mitgenommen.
- Laufende Prozesse: Handels-Dauerlauf (drei Stufen), MoonDev-Treiber mit 8 Agenten,
  Bus, SkillsBot, Gateway. Nicht beendet, nicht neu gestartet.

## Entscheidung von Max noetig

- **Punkt 4:** Werkzeug `okx_bot_waechter` aus der Herzschlag-Pruefung ausschliessen
  (Empfehlung: ja - es haelt nie eine Position) oder `180` eintragen, damit die Zeile
  verschwindet, ohne etwas zu bedeuten?
- **Punkt 3:** Der Fehlalarm betrifft nur die Anzeige, nicht den Handel. Reparieren
  (Empfehlung: ja, eine Zeile, sonst lernt man, die Tageswarnungen zu ignorieren) oder
  als bekannt stehen lassen?
## Nachtrag 29.09.2026, 23:30 — Empfehlungen umgesetzt

Vier Punkte sind erledigt, jeder mit echtem Lauf belegt (committet und gepusht
auf `master`: `0158fba`, `0f1a6ad`, `ac89d01`, der Block-11b-Teil kam ueber den
Fremdarbeit-Commit `45ad2b5` auf master).

| Punkt | Aenderung | Beleg |
|---|---|---|
| 1 (Push 403) | `fremdarbeit-einziehen.ps1` raeumt `GITHUB_TOKEN`/`GH_TOKEN` vor dem Push | Ursache gemessen: mit dem Registry-Token = exit 128/403, ohne ihn = exit 0. Die Variable bleibt stehen |
| 2 (Zweitkopie) | `Agenten\Hermes\cache` in der Ausschlussliste | Lauf 23:09 mit Fix: **0 FEHLER**, Code 3, exit 0, `Agenten\Hermes\cache` steht in `Ausgeschl. Verzeichnisse` |
| 3 (Fehlalarm Herzschlag) | `spiegelstand.frisches_alter()` nimmt den frischsten von `zustand.json`/`zustand.live.json` | `moondev_marktlage` meldet 14 min statt 204; 6 neue Tests in `Handel/tests/test_spiegelstand_alter.py`; `spiegelstand` danach 29/29 byte-gleich |
| 4 (okx_bot_waechter) | Block 11b trennt Spuren von Werkzeugen | Lauf 23:2x: „32 von 32 Handels-Spuren folgen der Herzschlag-Regel — ausgenommen als Werkzeug ohne Handelsbuch: okx_bot_waechter" |
| T-138 | `nautilus-demo` laeuft (Max gestartet) | `docker ps`: `nautilus-demo | Up 3 minutes` |

### Neuer Befund: die Task-IDs kollidieren wieder

`MaxHirn/Archiv/TASKS.md` traegt doppelte IDs — `T-139`, `T-142`, `T-145`,
`T-153`, `T-156` je zweimal, hoechste ID `T-171`. Ursache: parallele Sitzungen
vergeben `max+1` unabhaengig voneinander; am 29.09.2026 kam meine Reihe
T-134…T-138 dazu, waehrend eine andere Sitzung bei T-160 weiterschrieb. Die
Datei war beim Schreiben dieses Nachtrags 0,6 min alt, also nicht angefasst.

Naechster Schritt (eine Entscheidung): IDs aus EINER Quelle vergeben — Vorschlag
`T-<JJJJMMTT>-<nn>` (datumseindeutig, kollisionsfrei) — ODER die bestehenden
Doppelten einmalig umnummerieren und die Vergabe in die
Fremdarbeit-Routine legen. Ohne das waechst der Fehler mit jeder parallelen
Sitzung.

### Nicht angefasst

`MaxHirn/Archiv/TASKS.md` (0,6 min), `Agenten/Handel/replay.py`,
26 × `Agenten/Hermes/profiles/*/config.yaml`, `Agenten/Hermes/config.yaml`,
`MaxHirn/Wiki/*` — alles aktive Fremdarbeit der laufenden Sitzung. Ebenso
unangetastet: `GITHUB_TOKEN` als Benutzervariable (Entscheidung Max), die
Arbeitsbaum-Sitzung `C:\Users\faupe\Documents\Handel-leitstand` (Zweig
`arbeit/leitstand`), alle Dauerprozesse.
