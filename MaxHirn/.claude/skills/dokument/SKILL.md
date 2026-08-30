---
name: dokument
description: Erschließt ein einzelnes wichtiges Dokument — liest es vollständig, zieht Beteiligte, Beträge und Daten heraus, benennt es nach Schema, legt es im Archiv ab und verankert es im Vault. Benutzen bei "was steht da drin", "lies das mal", "was bedeutet dieses Schreiben", "leg das ab", "hab da einen Brief bekommen", oder wenn ein einzelnes PDF verstanden werden soll statt nur gefunden.
---

# Dokument erschließen

Für **ein** Dokument, das zählt. Nicht für Stapel — dafür ist `posteingang` da,
und nicht zum Suchen — dafür ist `archiv` da.

Ziel ist nicht „abgelegt", sondern: In zwei Jahren findet Max das Dokument
wieder **und weiß, was drinsteht, ohne es zu öffnen.**

## 1. Vollständig lesen

**Alle Seiten.** Bei Scans ohne Textebene nicht auf OCR verlassen — Beträge,
Aktenzeichen und Daten werden am Bild selbst abgelesen. Wie das geht, steht in
[[PDF-Scans-lesen]]; Leerseiten dürfen gemessen statt betrachtet werden.

Ein Auszug führt in die Irre: Der Steuerbescheid vom 17.07.2026 hatte die
Nachzahlung auf Seite 1, die Rechenfehler auf Seite 2, die Rechtsbehelfs-
belehrung auf Seite 6 — und die dauerhaften Vorauszahlungen versteckt unter
einer Tabelle auf Seite 1.

## 2. Sechs Fragen beantworten

- **Wer** schreibt, **an wen**, unter welchem Aktenzeichen?
- **Wann** — Datum des Schreibens, nicht des Scans?
- **Worum** geht es in einem Satz?
- **Welche Beträge** stehen drin, und wofür genau?
- **Was ändert sich dadurch** für Max?
- **Muss er etwas tun** — und bis wann?

Steht bei der letzten Frage ein Datum: **Skill `frist` anschließen.** Nicht hier
nebenbei erledigen, sonst landet die Frist nirgends.

Was im Dokument nicht steht, wird nicht ergänzt. „Aktenzeichen nicht angegeben"
ist eine gültige Antwort, eine plausibel geratene Nummer nicht.

## 3. Benennen

Schema im Archiv, mit Unterstrich als Trenner und Bindestrich innerhalb von
Namen:

```
<Bezugsjahr>_<Was>_<Wer>_<Datum>.pdf
2024_Einkommensteuerbescheid_geaendert_FA-Limburg-Weilburg_2026-07-17.pdf

<Datum>_<Was>_<Wer>.pdf              (wenn es kein Bezugsjahr gibt)
2016-11-28_Steuernummer_Umsatzsteuer_FA-Bad-Kreuznach.pdf
```

Umlaute vermeiden — sie brechen Suchen. Im Archiv liegt eine Kündigung als
`…_kündigung_…pdf`; `*kuendigung*` findet sie bis heute nicht.

## 4. Ablegen

Nach `Dokumente/Privat/…` oder `Dokumente/Gewerblich/…` in den **bestehenden**
Unterordner. Passt keiner, nachfragen statt einen neuen anlegen — eine Struktur
mit dreißig Einzelordnern ist keine Struktur.

Danach neu indexieren, sonst bleibt das Dokument unauffindbar:

```
cd ArchivSuche
.venv\Scripts\python.exe index.py
```

## 5. Im Vault verankern — aber nur, wenn es trägt

Eine Notiz lohnt sich, wenn das Dokument **einen Zustand ändert**: neue
Steuernummer, neuer Vertrag, geänderte Zuständigkeit, ein Betrag, der später
wieder gebraucht wird.

Sie lohnt sich **nicht** bei Belegen, Tickets, Kontoauszügen, Bedienungs-
anleitungen. Die sind über `archiv` auffindbar, und der Vault verstopft.

Im Zweifel: in eine **bestehende** Notiz ergänzen (Skill `notiz`), nicht eine
neue anlegen. Immer mit Datum und Fundort der Datei.

## Regeln

- **Das Original wird nie verändert** — nicht umgeschrieben, nicht komprimiert,
  nicht „aufgeräumt". Umbenennen und verschieben ist erlaubt, der Inhalt bleibt.
- **Beträge und Daten wörtlich**, nichts runden, nichts zusammenfassen. Wo im
  Dokument 2.646,00 € steht, steht in der Notiz nicht „rund 2.600 €".
- **Zertifikate, Schlüssel und Passwortdateien nicht bewegen** (`.pfx`, `.p12`,
  `.kdbx`, `.pem`). Melden und liegen lassen.
- Bei mehr als einer Handvoll Dateien abbrechen und `posteingang` benutzen.
- Findet sich beim Lesen ein Widerspruch zu einer Notiz im Vault, wird die
  Notiz korrigiert — auch wenn das nicht die Aufgabe war.
