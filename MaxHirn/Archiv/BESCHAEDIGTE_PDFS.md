# Beschaedigte PDFs im Archiv

61 Dateien, zusammen 297.4 MB.

Alle bestehen ausschliesslich aus 0xFF-Fuellbytes: Dateiname erhalten, Inhalt weg.
Pruefen laesst sich das an den ersten vier Bytes - intakt beginnt mit `%PDF`,
kaputt mit `0xFFFFFFFF`.

## Ursache (Stand 08.08.2026)

Nicht iCloud, sondern ein **Netzteildefekt**, der mehrere Festplatten gleichzeitig
zerstoert hat; die betroffenen Platten sind ausgebaut. Die Dateinamen wurden noch
geschrieben, die Inhalte gingen mit der Hardware. Siehe [[Hardware]].

## Wiederherstellung 08.08.2026

Aus 123 wurden 83: **40 Dateien wurden aus intakten Fassungen zurueckgespielt**,
gefunden auf G:, H: und O: (vor allem `O:\Documents\Maximilian\PDFs\Handbuecher`
und `G:\Studium`). Jede Kopie wurde nach dem Schreiben auf `%PDF` und gleiche
Groesse geprueft: 40 von 40 in Ordnung.

Wichtig fuer weitere Versuche: **Namensgleichheit genuegt nicht.** Von 261
namensgleichen Kandidaten waren 220 selbst mit 0xFF gefuellt - es sind Kopien
derselben kaputten Dateien, teils mit identischer Groesse. Die Ordner `icloud 26`
auf G: und O: sind durchweg unbrauchbar. Immer die ersten Bytes pruefen.

Nicht angefasst: `Kurzbezeichnungen_Holzarten_und_Holzwerkstoffe.pdf` - intakte
Fassung vorhanden, aber 2906 KB statt 2660 KB, also eine andere Version.

Auf J: (`Extern_BackUp`) wurde nichts gefunden: 0 von 123 bei 1243 PDFs.

**Gegenprobe 08.08.2026 – erster Versuch war fehlerhaft.** Ein Lauf ueber C:, G:,
H:, I: und J: meldete 0 intakte Kopien. Das Ergebnis ist **ungueltig**: Die
Dateiliste lief ueber eine Textdatei, wobei Umlaute in Pfaden zerstoert wurden
(`PRÜFUNGsanmelde` → `PR?FUNGsanmelde`). Die Dateien liessen sich danach nicht
mehr oeffnen, und die Lesefehler wurden faelschlich als "kaputt" gewertet.

**Lehre:** Dateilisten fuer solche Abgleiche nicht ueber `find > datei.txt`
fuehren. Direkt in Python mit `os.walk` arbeiten – dort kommen die Namen als
korrekte Unicode-Strings vom Betriebssystem.

Fuer den Rest bleibt der Weg ueber die Aussteller (Handwerkskammer,
Ausbildungsbetrieb, Rechnungssteller). Bei den zehn Rechnungen in
`Gewerblich/Rechnungen` ist das nicht optional - ein Platzhalter erfuellt keine
Aufbewahrungspflicht.

## Wiederherstellung 08.08.2026 - zweiter Durchgang

Nach Anschluss von **O:** und Behebung des Umlaut-Fehlers (siehe oben):

- **4 Dateien von O: zurueckgespielt**, jede nach dem Kopieren auf `%PDF` und
  gleiche Groesse geprueft: Kontoauszug 28.02.2022, Lebenslauf 2024,
  Lebenslauf Faupel 2020, Laserworld CS-1000-RGB-Handbuch.
- **18 Platzhalter geloescht**, fuer die im Archiv laengst eine intakte Fassung
  unter fast gleichem Namen und mit identischer Groesse lag - darunter beide
  Mietvertraege, der Arztbefund und die Lohnabrechnung. Kein Inhaltsverlust:
  Die Platzhalter enthielten null Bytes, der Zwilling bleibt erhalten.

**Entscheidender Kniff:** Die Platzhalter behalten die Originalgroesse. Ein
Abgleich ueber die exakte Byte-Groesse findet daher auch Fassungen, die anders
heissen - im Archiv `Lebenslauf 2020 (2).pdf`, auf O: `Lebenslauf 2020.pdf`.
Die reine Namenssuche hatte genau diese Faelle uebersehen.

**Stand: 61 Platzhalter, 297 MB.**

## Die geretteten Dateien sind jetzt volltextdurchsuchbar (10.08.2026)

Die zurueckgespielten Fassungen waren **Scans ohne Textebene**. Der Indexer
extrahierte bis dahin nur ueber `pypdf`, was bei bildbasierten PDFs 0 bis 30
Zeichen liefert - die Dokumente lagen zwar wieder im Archiv, waren im Index aber
leer und nur ueber den Dateinamen auffindbar.

`index.py` hat seither einen OCR-Rueckfall (Details in
[ArchivSuche/README.md](ArchivSuche/README.md)). Alle 13 wiederhergestellten
Dokumente haben jetzt Text, darunter Ausbildungsvertrag (2.406 Zeichen), beide
Mietvertraege (6.902 und 32.590), Lohnabrechnung (14.287) und der Kontoauszug
12/2022 (11.209).

**Zum Wiederfinden:** Der Dateiname der Kuendigung ist
`20231130_tm_kündigung_mf.pdf` - mit **ü**, nicht `kuendigung`. Eine Suche nach
`*kuendigung*` findet sie nicht. Dasselbe Umlaut-Problem wie beim ersten
Rettungsversuch, nur an anderer Stelle.

## Unterscheiden: kaputt oder nur bildbasiert?

Seit dem OCR-Rueckfall laesst sich das am Index ablesen, ohne die Dateien
anzufassen:

| `extract_status` | Bedeutung |
|---|---|
| `ok` | Textebene vorhanden, direkt extrahiert |
| `ok_ocr` | Scan, per Texterkennung erfasst |
| `ok_ocr_skipped_too_large` | Scan ueber 30 MB, Texterkennung uebersprungen |
| `skipped_too_large` | ueber 60 MB, gar nicht gelesen |
| `error: …` | beschaedigt oder unlesbar |

Von 926 PDFs im Index tragen 66 einen Fehlerstatus. Davon sind **59 die
0xFF-Platzhalter** aus dem Netzteildefekt; die restlichen **7 haben eine andere
Ursache** - sie beginnen korrekt mit `%PDF`, brechen aber mittendrin ab
(abgebrochene Downloads, kein Hardwareschaden):

- `Dokumente\Privat\Bedienungsanleitungen\DDJ-SX_TRAKTOR2_Import_Guide_E.pdf`
- `Dokumente\Gewerblich\Maks Sound\Handbücher\DDJ-SX_TRAKTOR2_Import_Guide_E.pdf`
- `Dokumente\Gewerblich\Maks Sound\avr3311.pdf`
- `Dokumente\Privat\Bewerbung\Lebenslauf Faupel 2020 (2).pdf`
- `Dokumente\Privat\Eingang\Geheimwissen-Maennlicher-Multi-Orgasmus--Ebook.pdf`
- `Dokumente\Privat\Finanzen und Versicherungen\30089707_2022_Nr.002_Kontoauszug_vom_28.02.2022_20220315144831(1).pdf`
- `Dokumente\Privat\Gesundheit\Das_Wichtigste_zur_KSV_in_Kuerze.pdf`

Beim Kontoauszug und beim Lebenslauf ist das unkritisch: die Fassungen ohne `(1)`
bzw. ` (2)` im Namen sind intakt.

## Verbleibende Dateien

### Gewerblich/Angebote  (3)

- `Angebot CampusSession 05_23 2.pdf`  (272 KB)
- `Angebot CampusSession 05_23.pdf`  (272 KB)
- `Angebot_Vorlage.pdf`  (740 KB)

### Gewerblich/Rechnungen  (10)

- `2020-08-21_Rechnung_KieferChirurgMF.pdf`  (3728 KB)
- `2023090435_Rechnung.pdf`  (459 KB)
- `Rechnung 20231101.pdf`  (531 KB)
- `Rechnung ANUGA Maximillian Faupel(1).pdf`  (1042 KB)
- `Rechnung ANUGA Maximillian Faupel(2).pdf`  (1042 KB)
- `Rechnung ANUGA Maximillian Faupel.pdf`  (1042 KB)
- `Rechnung_ART23_MaximilianFaupel.pdf`  (106 KB)
- `Rechnung_MaximilianFaupel(1).pdf`  (71 KB)
- `Rechnung_MaximilianFaupel(2).pdf`  (71 KB)
- `Rechnung_MaximilianFaupel.pdf`  (71 KB)

### Privat/Ausbildung Tischler  (11)

- `Ausbildungsordnung_Tischler.pdf`  (448 KB)
- `Bestimmung der Holzarten.pdf`  (1611 KB)
- `Einladungsschreiben_Meisterprüfung_Teil IV_Praktischer_Teil.pdf`  (104 KB)
- `Hoischen Technisches Zeichnen_ Grundlagen, Normen, Beispiele, Darstellende Geometrie.pdf`  (99407 KB)
- `Holzfachkunde für Tischler, Schreiner und Holzmechaniker; 4. Auflage   ( PDFDrive ).pdf`  (19009 KB)
- `Kurzbezeichnungen_Holzarten_und_Holzwerkstoffe.pdf`  (2660 KB)
- `Lernfelder Tischler.pdf`  (13006 KB)
- `Schwalbenschwanz_und_Zapfen_MF.pdf`  (566 KB)
- `Tischler-Teil-I-II_Beispielrechnung-BAfoeG.pdf`  (499 KB)
- `Unterlagen Handlungsfeld 2(1).pdf`  (1769 KB)
- `Unterlagen Handlungsfeld 2.pdf`  (1769 KB)

### Privat/Bedienungsanleitungen  (5)

- `DE_Anleitung_macroHOLZdata_Installation.pdf`  (714 KB)
- `Das Bondage Handbuch ( PDFDrive.com ).pdf`  (84280 KB)
- `Manual American Audio V-01 Plus Series - ManualsBase.com.pdf`  (3185 KB)
- `Manual American Audio V-01 Plus Series.pdf`  (3185 KB)
- `Manual_KSCX3625.pdf`  (6411 KB)

### Privat/Behoerden und Ausweise  (1)

- `Meldebescheinigung Wiesbaden.pdf`  (292 KB)

### Privat/Bewerbung  (4)

- `Bewerbung 1(1).pdf`  (106 KB)
- `Bewerbung 2(1).pdf`  (107 KB)
- `Bewerbung 3(1).pdf`  (107 KB)
- `Lebenslauf Faupel 2020(1).pdf`  (3194 KB)

### Privat/Fahrzeug-KFZ  (1)

- `Fahrzeugschein_WI_MA_721.pdf`  (1646 KB)

### Privat/Finanzen und Versicherungen  (3)

- `Bescheiddaten_fuer_2024_zu_Ihrer_Einkommensteuer.pdf`  (2 KB)
- `Gehaltsabrechnung Apr März Feb_Faupel.pdf`  (589 KB)
- `Teil-III-IV_Beispielrechnung-BAfoeG.pdf`  (453 KB)

### Privat/Gesundheit  (1)

- `116117.de - Arzt- und Psychotherapeutensuche.pdf`  (670 KB)

### Privat/Studium  (19)

- `(SoSe 19) PRÜFUNGsanmelde-INFO.pdf`  (249 KB)
- `Biochemie-1-Einführung-Druck.pdf`  (2060 KB)
- `Biochemie-3-Lipide-Druck.pdf`  (3706 KB)
- `Biochemie-4-Protein-Druck.pdf`  (5924 KB)
- `Biochemie-6-Enzyme-Druck.pdf`  (4898 KB)
- `Studienbescheinigung.pdf`  (61 KB)
- `campus_fingerzinkung_a4.pdf`  (2645 KB)
- `campus_gratung_a4.pdf`  (2661 KB)
- `campus_halbverdeckte_zinkung_a4.pdf`  (1659 KB)
- `campus_nutzapfen_a4.pdf`  (2003 KB)
- `campus_offene_zinkung_a4.pdf`  (1814 KB)
- `campus_projekt_tischlampe_a4.pdf`  (2376 KB)
- `campus_projekt_toolbox_a4.pdf`  (3569 KB)
- `campus_radien_boegen_anreissen_a4.pdf`  (1208 KB)
- `campus_schlitz_und_zapfen_a4.pdf`  (1706 KB)
- `campus_schraeger_zapfen_a4.pdf`  (1759 KB)
- `campus_schubkastenkonstruktionen_a4.pdf`  (5456 KB)
- `campus_stegverbindung_mit_keil_a4.pdf`  (1542 KB)
- `campus_ueberblattung_a4.pdf`  (2407 KB)

### Privat/Vertraege  (2)

- `20231130_tm_kündigung_mf(1).pdf`  (190 KB)
- `Kundenstamm-Vertrag Einzelkonten und Einzeldepots (Kombivertrag).pdf`  (208 KB)

### Privat/Wichtige Unterlagen  (1)

- `3_Wichtige + Gängige Plattenwerkstoffe.pdf`  (1225 KB)
