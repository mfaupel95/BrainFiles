# Token-effizienter Claude-Kontext – Design

**Stand:** 2026-08-30
**Status:** Umgesetzt am 30.08.2026 (Punkte 1–2 und 4 der Umsetzungsliste).
Punkt 3 (Empfehlungs-Präferenz) war bereits in `Wissen/Profil.md` vorhanden
und wird über `Wissen/INDEX.md` erreicht — kein direkter Link in den
Kernregeln, um die Index-first-Regel nicht zu unterlaufen.

## Problem

Lange zentrale Anweisungen, vollständige Dateilesevorgänge und Rohprotokolle
lassen den Kontext mit der Dauer einer Sitzung wachsen. Das betrifft die
Antwortqualität und den Tokenverbrauch, ohne bei den meisten Aufgaben
zusätzlichen Nutzen zu bringen.

## Entscheidung

Wir optimieren die vorhandene Claude-Umgebung direkt. Es entsteht keine eigene
RAG-Runtime und kein Ersatz für Claude Codes interne Tool-Definitionen: Beides
wäre zusätzlicher Betriebsaufwand und kann den vom Produkt gesendeten
Systemkontext nicht zuverlässig verkleinern.

## Architektur

1. **Kernregeln klein halten.** `CLAUDE.md` enthält nur universelle Reihenfolge,
   Sicherheitsgrenzen, knappe Ausgabevorgaben und Verweise. Detailverfahren
   bleiben in Skills, den jeweiligen Tool-README-Dateien oder Fachnotizen.
2. **Search-first statt Volltext.** Vor jedem Datei-Read zuerst gezielt suchen
   (`rg` für Projektdateien, Archivsuche für persönliche Unterlagen) und nur
   die erforderlichen Trefferbereiche lesen. Ganze Dateien sind nur erlaubt,
   wenn ihre vollständige Struktur für die Aufgabe nötig ist.
3. **Gezielte Wissensauswahl.** `Wissen/INDEX.md` ist der Einstieg; anschließend
   werden höchstens die für die Anfrage relevanten Notizen geöffnet.
4. **Sitzungen abschließen, nicht mitschleppen.** Nach einer abgeschlossenen
   Arbeit steht nur der dauerhafte Befund in `Wissen/` oder der konkrete offene
   Punkt in `Archiv/TASKS.md`. Roh-Ausgaben und Zwischenergebnisse werden nicht
   als dauerhafter Kontext wiederholt.
5. **Entscheidungen empfehlen.** Wenn mehrere realistische Wege bestehen,
   nennt Claude zuerst den für Max vorteilhaftesten Weg, begründet ihn knapp
   und benennt eine Alternative nur bei einem echten Zielkonflikt.

## Nicht im Umfang

- Die von Claude Code intern übermittelten Tool-Schemas dynamisch ersetzen.
- Eine neue Embedding-Datenbank oder einen separaten Session-Manager betreiben.
- Bestehende Archivsuche oder MCP-Server umschreiben.

## Umsetzung und Prüfung

1. Die globalen Kontextregeln auf den Index- und Search-first-Ablauf ergänzen,
   ohne gleichzeitig geänderte Fremdabschnitte zu überschreiben.
2. `Archiv/CLAUDE.md` auf Regeln für das Archiv reduzieren und lange
   Hintergrundinformationen in bestehende, bei Bedarf lesbare Dokumente
   verweisen.
3. Max' Präferenz zur klaren Empfehlung in `Wissen/Profil.md` festhalten und
   in den Kernregeln verlinken.
4. Prüfen, dass jede geänderte Steuerdatei auf einen konkreten Detailort zeigt,
   keine sensiblen Daten enthält und dass Git nur eigene Dateien im Commit hat.

## Erfolgskriterien

- Eine Standardanfrage erfordert keinen vollständigen Wissensordner und keine
  vollständige Archiv-Anleitung im Kontext.
- Detailregeln bleiben auffindbar, werden aber nur bei passender Aufgabe
  geladen.
- Bei Auswahlentscheidungen erhält Max eine klare, begründete Empfehlung.

## Umgesetzte Änderungen (30.08.2026)

- `CLAUDE.md`: Regel „gezielt lesen statt vollständig" ergänzt (rg /
  `archiv`-Skill vor jedem Datei-Read).
- `Archiv/CLAUDE.md`: Abschnitt „Was nicht im Index ist" von ~59 auf ~16
  Zeilen gekürzt — die Details standen bereits vollständig in
  `BESCHAEDIGTE_DATEIEN.md` und `BESCHAEDIGTE_PDFS.md`, nur als Verweis
  behalten.
- **Nebenfund beim Kürzen:** `ArchivSuche/README.md` beschrieb beim
  Duplikat-Umgang noch das alte, änderungsdatum-basierte Löschverhalten.
  Tatsächlich entscheidet seit der Umstellung auf SHA1-Vergleich (siehe
  `sort_inbox.py`, `move()`) der Inhalt — nichts wird gelöscht, wenn er
  abweicht. Doku korrigiert, damit der Verweis aus `Archiv/CLAUDE.md` nicht
  auf eine veraltete Beschreibung zeigt.
- `Archiv/CLAUDE.md`: Abschnitt „Was das Skript von sich aus absichert" von
  ~19 auf ~9 Zeilen gekürzt. Die Zahlen (1151/1152, 2927, 64 KB, 512 px,
  Endungslisten) waren wortgleiche Kopien der Code-Kommentare in
  `sort_inbox.py` — dasselbe Rott-Muster wie beim Duplikat-Nebenfund. Die
  vollständige Fassung ist nach `ArchivSuche/README.md` (neuer Abschnitt
  „Eingebaute Sicherungen") gezogen, `CLAUDE.md` verweist nur noch. Das
  Sicherheitssignal (welche Sicherungen es gibt) bleibt im Kernkontext.
