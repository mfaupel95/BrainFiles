---
name: frist
description: Erfasst Post mit Termindruck — Bescheid, Mahnung, Kündigung, Vertrag, Rechnung mit Zahlungsziel. Liest das Schreiben vollständig, trägt die Frist nach Wissen/Fristen.md ein und bereitet die Antwort als Entwurf vor. Benutzen bei "Frist", "Bescheid", "Mahnung", "Einspruch", "bis wann muss ich", "Widerspruch", "was ist die Frist", oder sobald in einem Dokument ein Datum mit Konsequenz auftaucht.
---

# Frist erfassen

Eine Frist, die nur im Gespräch genannt wurde, ist keine erfasste Frist.
Der Skill endet erst, wenn sie in [[Fristen]] steht.

## 1. Vollständig lesen — auch wenn es ein Scan ist

**Alle Seiten.** Die Rechtsfolge steht regelmäßig hinten, der Betrag vorn, und
die wichtigste Nebenfrist im Kleingedruckten dazwischen.

Der Volltextindex (Skill `archiv`) ist zum **Finden** da. Zum **Auswerten**
nicht: bei Beträgen, Aktenzeichen und Datumsangaben wird das Bild selbst
angesehen, nicht die OCR-Fassung. Wie das bei textlosen Scans geht, steht in
[[PDF-Scans-lesen]] — Leerseiten dürfen dabei gemessen statt betrachtet werden.

## 2. Herausziehen — und nach der ersten Frist weitersuchen

Absender · Aktenzeichen · Datum des Schreibens · **Frist** · Betrag ·
was zu tun ist · **was passiert, wenn nichts passiert**.

Ein Schreiben enthält oft mehrere Fristen, und die auffälligste ist selten die
einzige. Erst weiterblättern, wenn alle vier Fragen beantwortet sind:

- Was ist **jetzt** zu zahlen oder zu tun?
- Bis wann kann ich **widersprechen**?
- Werden **künftige, wiederkehrende** Zahlungen festgesetzt?
- Hängt daran eine **Antragsfrist**, die sonst verfällt?

> Im ESt-Bescheid vom 17.07.2026 standen auf Seite 1 unten Vorauszahlungen ab
> 10.09.2026 — 877 € je Termin, dauerhaft. Zwischen den Steuertabellen wären sie
> untergegangen; in keiner Notiz standen sie.

Fehlt einer der Punkte im Schreiben, steht das später so im Eintrag —
nicht ergänzen, nicht plausibel machen.

## 3. Das Datum belegen, nicht rechnen

Steht ein Enddatum im Schreiben, wird **dieses** übernommen, mit Fundstelle.

Muss gerechnet werden („einen Monat nach Bekanntgabe"), gilt: **die Rechenregel
steht im Schreiben selbst** — in der Rechtsbehelfsbelehrung, in der
Zahlungsbelehrung, im Kleingedruckten. Diese Stelle wird gesucht und wörtlich
zitiert. Aus dem Gedächtnis gerechnet wird nicht.

> **Realer Fehler, 20.08.2026.** Ich habe die Bekanntgabefiktion mit **drei**
> Tagen angesetzt, wie es bis 2024 galt. Im Bescheid stand „mit dem **vierten**
> Tag nach Aufgabe zur Post". Frist einen Tag zu früh notiert — diesmal harmlos,
> andersherum wäre sie verfallen.

Den Rechtsweg benennen, aber **keine Rechtsberatung erfinden**. „Einspruch ist
binnen Monatsfrist möglich" ist eine Angabe aus dem Schreiben; „das lohnt sich"
ist es nicht.

## 4. Zahlungsfristen sind Gutschriftfristen

„Zahlen Sie bis zum …" heißt fast immer: bis dahin muss das Geld **da sein**,
nicht abgeschickt. Steht das im Schreiben, kommt es in den Eintrag, mit Vorlauf.

Und: **ein Rechtsbehelf stundet nichts.** Wer Einspruch einlegt, zahlt trotzdem
pünktlich, solange keine Aussetzung der Vollziehung oder Stundung gewährt ist.
Zahlung und Rechtsbehelf sind **zwei** Fristen, nie eine.

## 5. Eintragen

In `Wissen/Fristen.md`, nach Datum sortiert, ISO-Datum vorn, als offenes
Kästchen. Der Aufbau steht dort; die vorhandenen Einträge sind die Vorlage.

Das `- [ ]` ist keine Kosmetik: das Tagesbriefing (Skill `tagesbriefing`) sammelt genau diese
Kästchen aus `Wissen/*.md` ein. Wer das Format ändert, macht Fristen im
Morgenüberblick unsichtbar.

**Wiederkehrende Zahlungen bekommen nur ihren nächsten Termin.** Vier Quartale
im Voraus einzutragen, macht die Liste zur Tapete und das Briefing unlesbar.
Nach dem Abhaken wird der folgende Termin angelegt — Rhythmus und Betrag stehen
im Eintrag, damit das ohne erneutes Lesen des Bescheids geht.

Danach in der Themennotiz einen **Rückverweis** setzen. Die Frist steht an
**einer** Stelle vollständig, überall sonst nur der Verweis. Zwei Fassungen
driften auseinander.

## 6. Wenn die Frist schon abgelaufen ist

Nicht beschwichtigen und nicht stillschweigend eintragen. Zuerst sagen, dass sie
weg ist und was das kostet.

Dann: es gibt die **Wiedereinsetzung in den vorigen Stand** (§ 110 AO, § 32
VwVfG). Ihre Voraussetzungen sind eng — unverschuldete Verhinderung, Antrag
binnen eines Monats nach Wegfall des Hindernisses, und die versäumte Handlung
muss **gleichzeitig nachgeholt** werden. Ob ein Grund trägt, entscheide ich
nicht; dass der Weg existiert und **eilt**, gehört sofort gesagt.

Krankheitszeiten und Nachweise dazu nie ungefragt in einen Entwurf schreiben —
das ist Max' Entscheidung, nicht meine.

## 7. Antwort vorbereiten, Termin vorschlagen — beides nicht ausführen

Ist eine Antwort nötig (Einspruch, Widerspruch, Raten- oder Stundungsantrag),
einen Entwurf ablegen: Aktenzeichen, Bezug auf das Schreiben, konkreter Antrag.
**Versendet wird nichts**, auch nicht auf Zuruf — Absenden bleibt bei Max.

Genauso beim Kalender ([[Verbindungen]]): Termin mit Datum, Uhrzeit und Titel
**vorschlagen**, Bestätigung abwarten. Nicht ungefragt anlegen, keine Gäste.

## Regeln

- **Weniger als sieben Tage Rest → sofort ansagen**, unabhängig davon, wonach
  gefragt wurde.
- **Erledigtes wird abgehakt, nicht gelöscht** (`- [x]` mit Datum). Die Historie
  beantwortet später „habe ich das damals gemacht?".
- Beträge und Daten wörtlich aus dem Schreiben, nichts runden.
- Ein selbst gerechnetes Datum wird **als solches gekennzeichnet**, samt der
  Regel, aus der es folgt.
