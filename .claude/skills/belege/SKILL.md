---
name: belege
description: Sammelt Nachweise für einen Vorgang mit Abgabetermin — Kaufbelege, Fahrten, Einsatztage — ordnet sie der richtigen Position zu und hält den Stand fest. Benutzen bei "Beleg", "Quittung", "Nachweis", "Rechnung aufheben", "Arbeitsmittel", "Verpflegungsmehraufwand", "Einsatztage", "was fehlt noch für", "Aufstellung machen", oder wenn etwas für Finanzamt, Versicherung oder Gericht zusammengetragen werden muss.
---

# Belege für einen Vorgang sammeln

Der Unterschied zu `dokument`: Dort geht es um **ein** Schreiben, hier um einen
**Stapel, der bis zu einem Termin vollständig sein muss**. Der Skill zählt mit,
was fehlt.

## 1. Den Vorgang aufsetzen

Eine Sammeldatei `Wissen/Belege-<Vorgang>.md` mit drei Dingen im Kopf:

- **Wofür** — welche Position, welche Rechtsgrundlage, an wen es geht
- **Bis wann** — und dieser Termin gehört zusätzlich nach [[Fristen]]
- **Was verlangt wird** — wörtlich aus dem Schreiben, nicht sinngemäß

Danach je Position eine Tabelle. Eine Zeile pro Beleg, **Summe darunter**.

## 2. Zwei Arten, sie zu unterscheiden

**Kaufbelege** brauchen: Datum · Händler · Gegenstand · Betrag · Zahlungsweg ·
Ablageort der Datei. Ohne Datei ist es kein Beleg, sondern eine Behauptung —
das gehört als „Beleg fehlt" markiert, nicht weggelassen.

**Aufstellungen** (Einsatztage, Fahrten, Abwesenheitszeiten) brauchen keine
Quittung, sondern **Nachvollziehbarkeit**: Datum · Ziel · Abfahrt · Rückkehr ·
Dauer. Eine Aufstellung, die nur eine Zahl nennt, wird nicht anerkannt.

## 3. Woher die Angaben kommen dürfen

In dieser Reihenfolge, und die Quelle wird **je Zeile vermerkt**:

1. **Belegdatei** im Archiv (Skill `archiv` zum Finden)
2. **Kalender** — bei Einsatztagen oft die einzige Spur. Termine des Zeitraums
   holen und als Rohmaterial nehmen (siehe [[Verbindungen]])
3. **Kontoauszug** — belegt die Zahlung, nicht den Gegenstand
4. **Erinnerung von Max** — zulässig, aber als solche gekennzeichnet

**Nie geschätzt.** Weder Beträge noch Tage. Wo nichts belegbar ist, steht
„nicht rekonstruierbar" — eine erfundene Aufstellung ist gegenüber einer Behörde
kein Formfehler, sondern ein eigenes Problem.

## 4. Stand ausgeben

Immer in dieser Form, damit auf einen Blick klar ist, was noch fehlt:

```
Position                     erfasst   Summe        Stand
Arbeitsmittel                   7      412,80 €     3 ohne Belegdatei
Verpflegungsmehraufwand        61 Tage  ---         Zeitraum Mai–Aug offen
```

Was fehlt, steht **vor** dem, was da ist. Eine Sammlung, die zu 80 % fertig
aussieht, aber am Stichtag unvollständig ist, hat nichts genützt.

## 5. Vor dem Abgeben

- Summen neu rechnen, nicht aus dem letzten Lauf übernehmen
- Jede Zeile ohne Quelle entfernen oder klären
- Die Aufstellung als **eigene Datei** ablegen und benennen wie in `dokument`
- **Abgeschickt wird nichts** — der Versand bleibt bei Max

## Regeln

- Beträge wörtlich vom Beleg, mit Datum des Belegs, nicht des Kaufs im Kopf.
- Doppelte Belege fallen auf, wenn Datum **und** Betrag **und** Händler gleich
  sind — nur dann zusammenfassen, sonst stehen lassen.
- Privates und Berufliches nicht vermischen; bei gemischter Nutzung den Anteil
  benennen statt den vollen Betrag anzusetzen.
- Bei Gesundheits- oder Behandlungsdaten nur aufnehmen, was Max ausdrücklich
  freigibt — auch wenn es die Position stützen würde.
