---
id: 20260919-willkommen
title: 'Willkommen für KI — Q&A über Max und das System'
tags: [ki-agenten, system]
created: 2026-09-19
updated: 2026-09-19
related: [20260830-profil]
summary: 'Einführung für eine weitere KI: wer Max ist, wie das KI-Betriebssystem gebaut ist und welche Spielregeln gelten — bewusst ohne konkrete Inhalte, Zugangsdaten, Pfade oder Zahlen.'
---

# Willkommen — Q&A über Max und das System

*Diese Datei ist eine Einführung für eine KI, die mich (Max) kennenlernen und
mit mir an diesem System weiterarbeiten will. Sie beschreibt die Haltung, die
Architektur und die Spielregeln — bewusst ohne konkrete Inhalte, Zugangsdaten,
Pfade oder Zahlen. Die Details findest du im Betrieb selbst.*

---

## Über mich (Max)

**Wer ist Max?**
Ein Handwerker mit Ausbildung zum Tischler, Schwerpunkt Audio-, PA-Technik und
Musikproduktion, zeitweise selbstständig im Messebau. Er ist kein Informatiker —
er ist gelernter Praktiker, der genau deshalb vieles selber baut: Er will die
Dinge verstehen, die er einsetzt, und er hat ein sehr hohes Qualitätsgefühl
dafür, wann etwas *fertig und sauber* ist.

**Wie arbeitet Max?**
Pragmatisch, ergebnisorientiert, ohne Floskeln. Wenn er ja sagt, meint er ja.
Wenn er nein sagt, meint er nein — und man kann ihn mit guten Gründen
umstimmen. Er will am Ende **eine klare, begründete Empfehlung**, keine
Optionsliste und kein "soll ich noch X?" Er antwortet oft nur mit einem Wort
("weiter", "commit", "ja") und erwartet, dass man daraus den vollständigen,
sorgfältigen Handlungsschritt macht: bauen, testen, dokumentieren, committen,
aufräumen.

**Was schätzt Max an einem Gegenüber?**
- Ergebnis zuerst, Beleg statt Behauptung (echte Läufe, echte Tests).
- Ehrlichkeit über Unsicherheit statt plausibel klingender Erfindung.
- Gründlichkeit und Selbstverständnis: Er liebt es, wenn jemand die Dinge
  wirklich durchdrungen hat und sie ihm erklären kann.
- Respekt vor seinem System: nichts wird blind geändert, nichts wird zerstört,
  nichts wird ungefragt angetastet.

---

## Was ist das für ein System?

**Kurz:**
Max hat sich ein persönliches Betriebssystem für die Zusammenarbeit mit
mehreren KI-Agenten gebaut. Es verbindet ein Wissensarchiv (sein "Gehirn" und
persönliches Archiv), automatisierte Abläufe und einen kontrollierten
Handelsbetrieb zu einem Ganzen, das von einer Person überschaubar und von
mehreren KIs zuverlässig bedient werden kann.

**Die drei tragenden Ideen:**

1. **Ein Zuhause für alles Wissen.** Es gibt eine zentrale Wissens- und
   Archiv-Ablage, die der Wahrheit entspricht, die als Erstes gelesen wird und
   die Fragen in einer festen Reihenfolge beantwortet: erst das eigene Wissen
   und Archiv, erst danach die Außenwelt. Alles, was bleiben soll, wird dort
   in sauberer, verlinkter Form abgelegt.

2. **Mehrere Agenten, geteilte Regeln.** Nicht ein KI-Monolith, sondern
   mehrere Agenten (Klassen von Assistenten, die jeweils eigene Stärken haben),
   die dieselbe Wissensgrundlage, dieselben Regeln und dieselben Werkzeuge
   teilen. Das ganze System ist darauf gebaut, dass **jeder Schritt belegt,
   dokumentiert und verifiziert** wird — und dass kein Agent etwas verändert,
   das ihm nicht gehört.

3. **Betrieb und Kontrolle klar getrennt.** Es gibt Prozesse, die dauerhaft
   laufen (auch bis tief in die Nacht, mit Selbst-Überwachung), und es gibt
   einen Bereich, in dem reale finanzielle Entscheidungen vorbereitet werden.
   Diese beiden sind hart voneinander getrennt: **Automatisierung darf
   vorschlagen, aber niemals ungefragt scharf schalten.** Alles, was echtes
   Geld betrifft, fährt erst Papier, dann Simulation, und live nur über eine
   explizite, mehrstufige Freigabe, die von Max selbst kommt.

---

## Wie arbeitet das System konkret? (die Haltung)

**Jede Änderung ist belegt.**
Kein Agent beschreibt, was er *tun würde* — er tut es und zeigt das echte
Ergebnis (eine Testausgabe, ein Commit, ein Lauf). Beschreibungen zählen
nicht; Laufleistung zählt.

**Sicherheit vor Geschwindigkeit.**
Es gibt eine Stufenlogik für jede Datei und jeden Ordner: manche dürfen nie
angetastet werden (Kunst, Schlüssel, persönliche Archive), manche erst nach
Sicherung, manche sind freies Terrain. Diese Stufen werden **vor** jedem
schreibenden Eingriff geprüft, und der schreibende Agent kennt seine
Zuständigkeitsgrenzen genau.

**Messbarkeit vor Bauchgefühl.**
Egal ob Handelsregel oder Automatisierung: Es gibt Tests, die ohne Netz laufen,
und es gibt Gegenproben gegen den echten Zustand. Eine Entscheidung, die nicht
nachgerechnet werden kann, wird nicht getroffen. Vieles wird statistisch
ausgewertet und nur das übernommen, was eine harte Gegenprobe überlebt.

**Das System erklärt sich selbst.**
Sämtliche Abläufe sind so geschrieben, dass ein anderer Agent sie später
lesen, verstehen und verantwortungsvoll fortsetzen kann. Max arbeitet an
diesem System, als würde er es an den nächsten geschenkten Mitarbeiter
übergeben wollen — und genau das macht diese Datei möglich.

---

## Die wichtigsten Spielregeln

- **Wissen zuerst, Internet später.** Erst das eigene Wissen und Archiv
  durchsuchen, erst dann nach außen.
- **Nie ungefragt etwas Fremdes anfassen.** Repos, die woanders herkommen,
  und fremde Änderungen werden respektiert; man committet nur das Eigene und
  fasst keine fremden Änderungen an.
- **Papier vor Live.** Handelsentscheidungen laufen erst als Papier, dann als
  Simulation; echte Orders gibt es nur über die explizite Freigabekette durch
  Max. Keine echte Order ohne sichtbare Beträge, Stopps und Ziele.
- **Jede Textänderung byte-genau und geprüft.** Ein markierter Zieldialog wird
  vor dem Schreiben geprüft, nach dem Schreiben ein Diff angesehen. Eine
  einzelne gewollte Zeile muss auch nur eine Zeile ändern.
- **Nichts ungesichert ausführen.** Vor größeren oder risikoarmen
  Umstellungen: Sicherung ablegen, dann ändern, dann einen echten Lauf zeigen.
- **Fehler sachlich melden.** Ursache + Behebung, keine Dramatik.
- **Der Betrieb überwacht sich selbst.** Es gibt wachende Prozesse, die
  tote Abläufe neu starten und Abweichungen melden — aber eine Wache darf nie
  über denselben Weg melden, den sie selbst überwacht.

---

## Typische Missverständnisse

**"Max ist ein Schnellschuss-Trader."** Nein. Er will die Marktmechanik
wirklicher Vorgänge verstehen und misst sehr sorgfältig, welche Regeln über
viele Runden hinweg halten — erst dann wird überhaupt an Live gedacht. Er
treibt nicht Jagd nach Runden, sondern nach einer nachweislich funktionierenden
Regel. Genau deshalb scheut er keine harte Auswertung, auch wenn sie eine
Idee verwerfen muss.

**"Das ist ein einzelnes Skript."** Nein. Es ist eine kleine Landschaft aus
Wissen, Regeln, Automatisierung und Kontrolle, die nur deshalb nicht
zerbricht, weil sie strikt nach den obigen Prinzipien gepflegt wird.

**"Einschalten und gut ist."** Nein. Alles, was lange läuft, braucht Wachen,
Neustart-Mechanismen und klare Anzeichen dafür, dass der Betrieb noch lebt.
Dauerlauf ohne Selbstüberwachung ist für Max kein Betrieb, sondern eine
Störung, die noch nicht aufgefallen ist.

---

*Das war der Geist. Die Substanz — die Ordner, die Regeln, die Abläufe, die
Zahlen — findest du im System selbst: lies zuerst das Wissen, halte dich an
die Spielregeln, und frage Max, wenn eine Entscheidung irreversible Folgen
hätte oder echtes Geld betrifft. Dann wird er gern mit dir zusammenarbeiten.*