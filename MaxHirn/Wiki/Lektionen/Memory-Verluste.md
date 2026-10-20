# Memory-Verluste: belegbar finden und zurueckholen

Stand 30.09.2026. Gilt fuer das Hauptgedaechtnis `Agenten/Hermes/memories/MEMORY.md`.

## Der Fund

Am 30.09.2026 fehlte im Gedaechtnis der Eintrag `HERMES-CONFIG 30.09.2026` (1117 Zeichen),
obwohl das Werkzeug ihn um 16:14 mit `"success": true` bestaetigt hatte.

Ursache, belegt: Um 16:43 schrieb dieselbe Sitzung einen NEUEN Eintrag
(`terminal.backend: local` = Standard ...) mit dem Anker

```
old_text: "`terminal.backend: local` = Standard. OFFEN T-231/232/233"
```

Dieser Anker war die SCHLUSSZEILE des HERMES-CONFIG-Eintrags. Das `replace` traf also den
falschen Eintrag und ersetzte ihn vollstaendig. Das Ergebnis nennt den Getroffenen selbst:

```
"replaced_entries": {"1": "HERMES-CONFIG 30.09.2026 (Stand): config.yaml ist jetzt KOMMENTARLOS, ..."}
```

Regel: **old_text ist der eigene, unverwechselbare ANFANG des Eintrags, nie eine Schlusszeile
und nie ein Satz, der auch in einem anderen Eintrag stehen koennte.** Nach jedem `replace`
und `remove` das Feld `replaced_entries`/`removed_entries` lesen - es ist die einzige
Kontrolle, WELCHER Eintrag getroffen wurde.

## Warum nichts verloren ist

Das Ergebnis-JSON jedes `replace`/`remove` traegt den VOLLEN Text des getroffenen Eintrags.
state.db (Tabelle `messages`, `tool_name='memory'`) ist damit ein Archiv aller je ersetzten
oder entfernten Eintraege - unabhaengig von Sicherungen, Backups und Git.

## Werkzeug

```
python Agenten/Hermes/scripts/memory-verlust.py                  # Liste der belegten Verluste
python Agenten/Hermes/scripts/memory-verlust.py --alles          # Volltexte
python Agenten/Hermes/scripts/memory-verlust.py --retten DATEI   # Volltexte als Markdown
python Agenten/Hermes/scripts/memory-verlust.py --json DATEI     # maschinenlesbar
```

Als Verlust gilt: der Text steht heute nicht mehr in MEMORY.md UND sein Anfang (erste
70 Zeichen) auch nicht - sonst wurde der Eintrag nur umgeschrieben (das ist der Normalfall
und kein Verlust). Absichtliche `remove`-Aufrufe werden getrennt ausgewiesen.

Stand 30.09.2026: 13 belegte Ersetzungen/Entfernungen, 6 davon nicht mehr im Gedaechtnis,
davon 1 absichtlich entfernt (STARTREGEL FUER SITZUNGSLOESCHUNG, 19 Sekunden nach dem
Schreiben vom selben Verfasser geloescht). Echter Verlust: genau der HERMES-CONFIG-Eintrag
- wiederhergestellt und gegen die Wirklichkeit geprueft (config.yaml: kommentarlos,
`fallback_providers: []`, threshold 0.5, `local_runtime.enabled: true`).

Tests: `Agenten/Hermes/scripts/test_memory_verlust.py` (7).

## Wache

`Agenten/Hermes/scripts/memory-verlust-wache.py` meldet nur, was seit dem letzten Lauf NEU
verloren ist; Merkdatei `cache/memory-verlust-wache.json`, erster Lauf setzt die Baseline und
schweigt, ein Messfehler wird gemeldet statt verschwiegen. Hermes-Cron
`memory-verlust-wache` (Job f6f34ed95e0b, taeglich 20:45, no_agent, Telegram, leere Ausgabe
= nichts senden). Tests: `scripts/test_memory_verlust_wache.py` (7).

## Zweiter Befund derselben Sitzung: die Pending-Queue

`Agenten/Hermes/pending/memory/` traegt 25 nicht angewandte Konsolidierungsvorschlaege aus
`background_review` (aeltester 09.09.2026, neuester 24.09.2026, zusammen ~60 KB). Am
30.09.2026 um 18:32 hat Max `/memory approve all` ausgefuehrt: MEMORY.md wurde neu
geschrieben, aber KEIN Inhalt aus der Queue steht heute im Gedaechtnis (Stichproben:
"OKX-Schluessel 19.09.2026 erneuert", "841 Zeilen" - beide nicht vorhanden). Die Anker der
Vorschlaege sind tagealt und treffen nicht mehr. Lehre: **ein Konsolidierungsvorschlag
verfaellt mit seinem Anker.** Wer ihn spaeter freigibt, gibt nichts frei; die Vorschlaege
muessen inhaltlich nachgezogen oder geloescht werden, nicht "freigegeben".

## Abgearbeitet am 30.09.2026 (T-245)

Alle 25 Vorschlaege (46 Einzeloperationen) wurden einzeln gegen das heutige Gedaechtnis
geprueft. Ergebnis: **4 Inhalte fehlten wirklich und stimmen noch** - sie wurden von Hand
nachgezogen, alles Uebrige verworfen (Anker tagealt, wiederholt Vorhandenes oder ein
Arbeitsprotokoll, das kein Gedaechtnisinhalt ist):

| Vorschlag | Befund | Pruefung |
|---|---|---|
| Stoerungen / Bedingung 5 | fehlte und war FALSCH: das Gedaechtnis nannte die Umstellung noch "OFFEN (Entscheidung Max)" | `scanner/wachen_pruefung.py`: `rollierender_ev` rechnet auf `teile_runden` (Handelsrunden), `rollierender_ev_alle` nur Diagnose - umgesetzt |
| FOMO/Copy-Trading | fehlte | `Werkstatt/fomo-copy-trading-plan.md` liegt (8307 B), nichts gebaut |
| Plan-Modus | fehlte | `Agenten/Hermes/skills/.archive/plan/SKILL.md` vorhanden |
| scanner MFE/MAE | fehlte | Kopfzeile `handelsjournal.csv`: `mfe_pct,mae_pct,haltetage` |

MEMORY.md 245.477 -> 247.972 Zeichen, USER.md 5.565 -> 6.266 (Antwortform bei
"fuehre Skill X aus", Git-Zweige/EIN Arbeitszweig).

Verworfen wurden die 25 Dateien aus `pending/memory/`; ihr Volltext liegt als Digest in
`Agenten/Hermes/.sicherung/memory-queue-verworfen-20260930.md`. Zwei Vorschlaege waren
beim Pruefen WIDERLEGT statt nur veraltet: der "Ollama-Store-Pfad"-Fehlalarm steht nicht
mehr in `systempruefung.ps1`, und die HARDWARE-Vorschlaege nannten `E:`/`J:` als
Kopieziele (heute `O:` und `Q:`).

**Der Anker ist die Ursache, nicht der Inhalt** - aber die Wache dagegen ist schon gebaut.
28 der 46 Operationen waren `replace`, und eine `replace`-Operation traegt `old_text`.

KORREKTUR 30.09.2026 (gemessen, nicht gelesen): die erste Fassung dieses Abschnitts behauptete,
`/memory approve` melde nichts. Falsch. Beim EINLAGERN pinnt `tools/memory_tool.py:64` die volle
getroffene Eintragung als `matched_entry`, und `apply_memory_pending` (Zeile 306-308) **verweigert**
jede destructive Operation ohne Pin:

```
This destructive pending write predates entry pinning and cannot be verified;
nothing was applied. Reject it and recreate the change.
```

`/memory pending` nennt dazu je Eintrag `unpinned legacy target - reject and recreate before
approving`, und `approve` druckt `Failed:`-Zeilen samt ueberschriebenen Eintraegen. Sonde:
`Agenten/Hermes/scripts/probe-memory-pinning.py` (baut denselben Store wie `/memory approve`);
beide alten Formen werden verweigert, MEMORY.md bleibt byte-gleich.

Damit ist der Fall vollstaendig erklaert: alle 25 Dateien stammten aus der Zeit VOR dem Pin
(09.-24.09.), 14 davon waren Batches - und ein Batch wird als GANZES verweigert, auch seine
reinen `add`s. `approve all` hat nichts angewandt und das auch gesagt. Was wirklich fehlt, ist
eine WACHE gegen das Verrotten der Queue (offen als T-247), nicht Code am `approve`.

## Dritter Durchgang am 20.10.2026 (10 Vorschlaege)

Alle 10 Dateien in `pending/memory/` (Vorschlaege vom 05.-20.10.2026) wurden einzeln gegen
Code/Dateien/Cron und das heutige Gedaechtnis geprueft. Verifizierte Inhalte wurden von Hand
nachgezogen, der Rest verworfen; Volltext aller Vorschlaege im Digest
`.sicherung/memory-queue-verworfen-20261020.md`.

Nachgezogen (jeweils gegen die Realitaet belegt):
- TELEGRAM-GRUPPE: require_mention=true (in .env gemessen) + Erweiterung auf 8 Bots (11.10.)
  bzw. 24 Bot-Profile mit eigenem Token (20.10., profiles/*/.env gezaehlt).
- JUNCTION: Korrektur - junction-wache.py existiert (T-390, Cron b65d0a979ce8, 10 min) und
  meldet Verlust; die alte Notiz "es gibt KEINE Wache" war falsch (Merkdatei + Cron geprueft).
- MCP-ZOMBIE-WACHE: 05.10.-Erweiterung (NODE-Knoten + Ollama-:cpu-Idle-Fresser) - die Wache
  filtert bis 20.10. nur python/pythonw (im Skript geprueft).
- FREQTRADE-STACK: 20 Container 8081-8100 (bots.json gezaehlt) + Futures-Short-Messung.
- AUTO-FREIGABE: "der Hebel ist die zwei Haken, nicht die Auto-Freigabe" + 9-Orderpfad-Liste.
- OMNIQUANT: markte_laden-Falle; KRAKEN-FAKTEN: /fills-Notaus-Falle; DOCKER-TERMINAL:
  docker_volumes-/brainfiles-Eintrag (in config.yaml gesetzt); HERMES-TOOL-BACKEND: write_file.
- SANDBOX-FALLE: schtasks LogonTrigger braucht Admin, TimeTrigger-only-XML ohne.
- Neu: ZEILENENDEN BEI GEMISCHTEN DATEIEN, DOCKER-DESKTOP MANUELL PAUSIERT.

Verworfen (nicht uebernommen, Gruende):
- ADX_MACD-"gemessene Kante" (02.10.) - widerlegt durch die Pin-Nachrechnung mit festem
  Fensterende (OMNITRADE-PIN-BEWEIS 04.10.): das Vorzeichen kippt mit dem Fenster.
- MAX' KONTEN (01./02.10.) - redundant zu OKX-STAKING/OKX-KONTO WAERUNGEN (03.10. gemessen).
- JEV-TRADER-add - stand schon woertlich im JEV-TRADER-LIVE-Eintrag.
- Sweep-/rsi_noema-/erledigen.py-Details - schon in OMNITRADE-PIN-BEWEIS, BITLOCKER-
  ENTSCHEIDUNG und BACKTEST-FENSTER.
- SKILL_MANAGE-Praezisierung ("am 05.10. kein CRLF") - die Regel (nach jedem Patch numstat)
  steht schon; die Umwandlung ist nachweislich nicht vorhersagbar, die Vorsicht gilt trotzdem.

MEMORY.md 394.018 -> 397.405 Zeichen (72 % des Budgets): 2 neue Eintraege, 10 geaendert,
1 Korrektur. Queue ist leer, probe-memory-pinning.py belegt weiterhin beide alten Formen als
verweigert (MEMORY.md bleibt byte-gleich). Offen als TASKS T-424: mcp-zombie-wache filtert nur
python/pythonw, nicht node.
