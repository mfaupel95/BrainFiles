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