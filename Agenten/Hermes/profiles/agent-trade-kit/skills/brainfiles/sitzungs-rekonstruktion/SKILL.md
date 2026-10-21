---
name: sitzungs-rekonstruktion
description: "Sitzung rekonstruieren: fehlenden Stand nachliefern."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [hermes, sessions, state-db, statusbericht, brainfiles]
    related_skills: [hermes-config-ops, absturz-recovery]
---

# Abgebrochene Sitzung rekonstruieren

Eine Sitzung endet mitten im Turn — die letzte Assistenten-Zeile ist ein halber Satz
(„…, dann der Stand:") — und Stunden später kommt in einer **neuen** Sitzung nur ein
Wort: „stand", „wie siehts aus", eine nackte Ziffer („9"), „ja". Der Auftrag steht
nirgends im aktuellen Kontext. Ziel: den versprochenen Stand nachliefern, mit Belegen,
statt zu raten oder zurückzufragen.

## Wann

- eine Nachricht ohne Bezug im Kontext (Einzelwort, Ziffer, „mach weiter")
- eine Sitzung, die sichtbar mitten im Satz abgebrochen ist
- „wie siehts aus", „stand", „wo waren wir" in einer Sitzung, die den Faden nicht hat

**Don't use for:** Absturz am Rechner mit beschädigtem Arbeitsbaum (`absturz-recovery`),
gezielte Änderung an der Hermes-Konfiguration (`hermes-config-ops`).

## Prozedur

1. **Sitzungen nach letzter Aktivität auflisten** — `session_search` ohne Argument.
   Kandidat ist die jüngste Sitzung, die **nicht** die laufende ist. Mit `query` das
   Thema finden, dann die Nutzer-Nachrichten dieser Sitzung lesen: die letzte offene
   Frage ist der Auftrag.
   - **Eine nackte Ziffer ist ein Verweis, kein Auftrag.** Sie zeigt auf eine
   nummerierte Liste, die in einer anderen Sitzung stand. Also die letzten
   Assistenten-Nachrichten der zwei juengsten fremden Sitzungen lesen
   (`session_search` mit `session_id` - das Fenster liegt von selbst am Ende) und
   pruefen, ob eine davon mit einer Liste endet. Endet KEINE damit (typisch: beide
   Sitzungen starben mitten in einem Werkzeugaufruf), hat die Ziffer keinen Bezug -
   dann EINE Rueckfrage ueber `clarify` stellen: die 2-4 offenen Straenge als
   klickbare Optionen, der wahrscheinlichste zuerst, plus eine Versehen-Option. Die
   Straenge mit Datei/Testname benennen, nicht als Thema - die Antwort soll sofort
   weiterfuehren. In Prosa angebotene Optionen sind hier der Fehler: sie sind nicht
   klickbar und der Nutzer tippt, was er sonst nur anwaehlt.
2. **Nur wenn Schritt 1 den Faden nicht hergibt, in die DB sehen** (lesend):
   `sqlite3.connect("file:<HERMES_HOME>/state.db?mode=ro", uri=True)`, Tabelle
   `messages` mit `id, session_id, role, content, tool_name, tool_calls, timestamp,
   `active`. `active=1` ist der lebende Verlauf, `active=0` komprimierte Altstände.
   - **Lebt die Sitzung noch?** `SELECT session_id, MAX(timestamp) FROM messages WHERE
     active=1 GROUP BY session_id ORDER BY 2 DESC LIMIT 10` — die Zahl in Ortszeit
     umrechnen (`time.localtime`) und mit „jetzt" vergleichen: Minuten = sie arbeitet
     gerade, Stunden = abgebrochen.
   - **`id` ist global über alle Sitzungen.** `WHERE session_id=… AND id>N` schneidet
     willkürlich ab und versteckt genau die Zeilen, die man sucht — pro `session_id`
     nach `timestamp` ordnen.
   - Assistenten-Zeilen mit leerem `content` sind reine Werkzeugaufruf-Turns; die Zeile
     `role='tool'` mit `tool_name` und Ergebnis darunter zeigt, woran gearbeitet wurde
     und wie weit es kam.
   - Die letzte Zeile einer abgebrochenen Sitzung ist oft ein Werkzeugergebnis ohne
     Nachsatz — der Assistent starb **vor** dem Bericht, nicht weil die Arbeit fehlte.
     Das ist die gute Nachricht: die Fakten sind schon da.
3. **Nichts aus der toten Sitzung ungeprüft übernehmen.** Jeder Satz, der in den Bericht
   soll, wird am lebenden System nachgeprüft (Zustand, Kommando, Datei). Behauptungen
   aus einem abgebrochenen Lauf sind der häufigste Grund für einen falschen Stand.
4. **Bericht in der Hausform:** Ergebnis zuerst, Belege (Kommando + Ausgabe), genau eine
   begründete Empfehlung, dann die nächste Aktion. Keine Optionsliste.
5. **Immer eine Liste „nicht angefasst"** anschließen: laufende Prozesse, fremde
   Arbeitsstände, Dateien, generierte Artefakte. Ohne sie ist der wiederhergestellte
   Stand unvollständig.

## Regeln (Standing)

- **Zuerst suchen, dann fragen.** Eine Nachricht ohne Bezug ist in dieser Umgebung fast
  immer eine Antwort auf eine parallele Sitzung. Wer sofort nachfragt, kostet einen
  Umlauf; wer sucht, liefert beim ersten Mal.
- **Widersprüchliche Belege offen benennen**, nicht glätten: wenn zwei Quellen
  (Git, Backup, Kommandoausgabe) Verschiedenes sagen, steht beides im Bericht — mit der
  Angabe, welche Quelle mehr wiegt. Eine geglättete Version ist ein Fehler, der später
  auffällt.
- **Fremde Arbeit im Arbeitsbaum nicht anfassen** (anderer Autor, gestagte Dateien,
  fremde Notizen). Benennen, nicht wegräumen; Commits nur auf benannten Pfaden.
- **Unmittelbar vor dem Handeln noch einmal messen, ob die „tote" Sitzung wirklich tot
  ist.** Diese Sitzungen wachen auf, sobald der Nutzer dort etwas tippt — und können in
  der Zwischenzeit genau den Auftrag erledigt haben, den man selbst gerade ausführen
  soll. Also vor jedem Schreiben die letzte Aktivität erneut abfragen (Schritt 2) **und**
  `git status --porcelain <pfad>` plus `git diff --cached <pfad>` lesen. Ist sie wieder
  aktiv, nicht doppelt schreiben: ihr Ergebnis unabhängig nachprüfen und den Bericht
  darauf umstellen — „was sie getan hat, was ich nachgeprüft habe, was offen blieb".
  Zwei Schreiber auf derselben Datei sind der Schaden, nicht die verlorene Zeit.
- **Der fertige Bericht einer parallelen Sitzung ist eine Behauptung, kein Beleg** — auch
  wenn er plausibel klingt und eine Kommandoausgabe mitbringt. Meist fehlt genau der
  entscheidende Schritt: belegt ist der Transport oder die Datei, nicht die Wirkung — dazu
  die Restliste. Diesen fehlenden Schritt selbst nachziehen und als eigenes Ergebnis
  ausweisen, statt ihn der anderen Sitzung zuzuschreiben.

## Verweise

- `hermes-config-ops` — wenn der Stand eine Hermes-Einstellung betrifft: dort steht, wie
  man „was gilt" belegt (Kommando statt YAML-Lesen) und wo Vorher-Kopien liegen.
- `absturz-recovery` — wenn zusätzlich der Arbeitsbaum nach einem Absturz zu prüfen ist.
- Hinweis: `absturz-recovery` ist nutzereigen und für die automatische Pflege gesperrt
  (`hermes curator adopt absturz-recovery`, wenn sie mitgepflegt werden soll).
