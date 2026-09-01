# Dashboard

Startseite des KI-Betriebssystems. In Obsidian als Standardnotiz setzen:
*Einstellungen → Allgemein → Beim Start diese Notiz öffnen*.

## Struktur

Seit dem **30.08.2026** liegt die Wurzel eine Ebene höher, in `BrainFiles/`,
und ist in vier Ordner geteilt. Vorher war `MaxHirn/` alles zugleich.

| Ordner | Aufgabe |
|---|---|
| `MaxHirn/` | **dieser Vault** — Wissen und Archiv. Hier liegt nichts, was startet. |
| `Modelle/` | Modellgewichte und Laufzeiten, 51 GB. Nicht in der Sicherung. |
| `Agenten/` | MCP-Server, Hermes, Handelsagent, Routinen, Sicherungsskripte. |
| `Werkstatt/` | gemeinsamer Arbeitsplatz der Modelle. Durchgangsware. |

Was dabei zu beachten ist — und welche fünf Fallen es gibt —, steht in
[[Ordnerstruktur]]. Der Ordner `Archiv/` hieß bis dahin „Claude“.

## Wissen

Diese Liste ist eine Auswahl. **Vollständig** — mit einem Satz Zweck je Notiz —
steht alles in [[INDEX|Wissen/INDEX]]; dort steigen auch die Agenten ein.

- [[Fristen]] — laufende Termine mit Konsequenz; **4 offen, davon 1 überfällig**
  (Nachzahlung 3.259,19 € war am 21.08.2026 fällig, AdV beantragt und noch nicht
  entschieden; nächster künftiger Termin 10.09.2026)
- [[Profil]] — wer ich bin, wie ich arbeite
- [[Projekte]] — was gerade läuft
- [[Verbindungen]] — welche Dienste angebunden sind
- [[Werkzeuge]] — welche davon tatsächlich abgerufen werden (gemessen)
- [[Zugaenge]] — API-Schlüssel und Tokens, **einzige** Ablage
- [[Passwoerter-Quarantaene]] — Checkliste: welche Passwörter zu ändern sind
- [[Routinen]] — was automatisch passiert
- [[Portabilitaet]] — Umzug auf externe SSD
- [[PDF-Scans-lesen]] — gescannte Dokumente auswerten statt nur durchsuchen
- [[Hardware]] — Laufwerke, Plattendiagnose; **offen: Stromausfälle ohne Bluescreen, WD My Book (J:) baut ab**
- [[Steuerunterlagen]] — Steuernummern, veranlagte Jahre; **Einspruch läuft seit 19.08.2026, AdV beantragt**
- [[Marktlage-August-2026]] — geprüfter Marktstand, Quellenbewertung STA Solutions
- [[Handelsbots]] — OKX-DCA-Bots: was gemessen wurde, womit nachgerechnet wird

## Archiv

Dateiarchiv liegt in `Archiv/` (Bilder, Videos, Musik, Dokumente).
Neue Dateien einfach nach `Archiv/Posteingang/` ziehen — der Skill
`posteingang` sortiert sie ein.

Suchen: Skill `archiv`, oder direkt
`Archiv/ArchivSuche/Suche_starten.bat` für die Weboberfläche.

**Neu seit 19.08.2026: semantische Suche.** Findet nach Bedeutung statt nach
Stichwort, läuft vollständig lokal (Ollama + bge-m3), deckt 1.076 Dateien mit
echtem Text in 11.965 Abschnitten ab.

```
Archiv\ArchivSuche\.venv\Scripts\python.exe Archiv\ArchivSuche\vektor_suche.py "frage in eigenen worten"
```

Anleitung und Grenzen: `Archiv/ArchivSuche/VEKTORSUCHE.md`.

## Sicherung

`sichern.ps1` liegt seit dem 30.08.2026 in `../Agenten/` — prüft erst auf
Klartext-Zugangsdaten, kopiert dann nach `G:\MaxHirn-Sicherung`. Gemessener Lauf
am 23.08.2026: **48 Sekunden**. Details in [[Hardware]].

Die Quelle ist seit dem Umbau `BrainFiles/` statt `MaxHirn/`, damit auch
`Agenten/` mitgesichert wird; `Modelle/` steht dafür in der Ausschlussliste.
Das nimmt 51 GB aus jedem Lauf — sie sind neu herunterladbar.

**Läuft seit 23.08.2026 täglich um 20:00 von selbst** (Aufgabe
`MaxHirn-Sicherung`, Protokoll unter `../Agenten/Routinen/logs/`). Vorher lief sie nur,
wenn jemand daran dachte — zuletzt fehlten deshalb der ganze `Hermes/`-Ordner
und `AGENTS.md` in der Sicherung.

Dazu seit 23.08.2026 eine **Zweitkopie um 21:00 nach `O:\MaxHirn-Zweitkopie`**
(`sichern-zweitkopie.ps1`): der unersetzliche Teil ohne Videos, Musik, Software
und Posteingang — 7,1 GB, gemessen **8 Sekunden**. Sie liegt bewusst auf O:,
weil `G:`, `H:` und `I:` dieselbe physische Platte sind. Übersicht: [[Routinen]].

**Dritte Kopie außer Haus:** `sichern-ausser-haus.ps1` → `E:\MaxHirn-AusserHaus`
(externe SSD, 46,2 GB komplett). **Läuft bewusst nicht automatisch** — eine
Platte, die dauerhaft angesteckt ist, wäre keine Kopie außer Haus. Anstecken,
Skript aufrufen, sicher entfernen, weglegen. Erstmals angelegt am 25.08.2026.

⚠️ Gegen den Fall, der 2026 eingetreten ist — ein Netzteilschaden tötet mehrere
Platten **gleichzeitig** —, hilft nur diese dritte Kopie, und nur solange sie
nicht am Rechner hängt. Sie enthält Klartext-Zugangsdaten; ohne BitLocker To Go
liest sie jeder, der sie findet.

## Skills

| Skill | Wofür |
|---|---|
| `archiv` | Im eigenen Dateiarchiv suchen |
| `frist` | Post mit Termindruck erfassen, Frist eintragen |
| `schaden` | Zerstörte Dateien finden und zurückspielen |
| `dokument` | Ein einzelnes Schreiben verstehen, benennen, ablegen |
| `belege` | Nachweise für einen Termin sammeln und mitzählen |
| `geld` | Anstehende Zahlungen und Guthaben nebeneinander |
| `auftrag` | Aus knapper Eingabe das Ziel lesen und loslegen |
| `posteingang` | Posteingang einsortieren und neu indexieren |
| `notiz` | Dauerhaftes Wissen als Vault-Notiz ablegen |
| `tagesbriefing` | Morgendlicher Überblick |
| `wochenrueckblick` | Wochenabschluss und Aufräumen |

Dazu seit 28.08.2026 sechs Skills für den Betrieb des Systems selbst:

| Skill | Wofür |
|---|---|
| `system` | Windows-Probleme gezielt eingrenzen statt rundum scannen |
| `verbindungen` | MCP-Server und Dienste prüfen, eintragen, reparieren |
| `vergleich` | Ordner über Laufwerke vergleichen, Duplikate, Zusammenführen |
| `sichern` | Committen, ohne fremde Arbeit zu vermischen oder zu verlieren |
| `skill` | Aus einem Anwendungsfall eine wiederholbare Aufgabe machen |
| `rueckschau` | Sitzungen auswerten, um wiederkehrende Arbeit zu finden |
| `umzug` | Ordner verschieben oder umbenennen, ohne dass Pfade still brechen |

Aufruf in Claude Code mit `/archiv`, `/posteingang` usw.

Ausführliche Beschreibung aller Skills, der Werkzeuge darunter und der Grenzen:
[Handbuch.html](Handbuch.html) — im Browser öffnen, mit Strg+P druckfertig (A4, 11 Kapitel).

## Offen

**Die verbindliche Liste ist [Archiv/TASKS.md](Archiv/TASKS.md)** (seit 28.08.2026).
Der folgende Abschnitt ist der Stand vom 23.08.2026 und wird nicht mehr gepflegt.

### Stand 23.08.2026 (überholt)

- [ ] **Netzteil / Stromzufuhr klären** — blockiert alles Langlaufende
      (siehe [[Hardware]]). Zuerst das Billige: Kaltgerätekabel,
      Steckdosenleiste, Wandsteckdose.
- [ ] **Passwörter aus dem Firefox-Export von 2020/2023 ändern**, soweit sie
      noch gelten. **Arbeitsliste steht jetzt in [[Passwoerter-Quarantaene]]** —
      68 Dienste nach Dringlichkeit sortiert, Postfächer zuerst, ohne
      Zugangsdaten. Die vier Kopien in `C:\Users\faupe\Zugangsdaten-Quarantaene\`
      sind **inhaltlich identisch** (ein Export, viermal kopiert) und bleiben
      liegen, bis die Liste abgearbeitet ist — danach löschen.
- [ ] **OKX-Schlüssel widerrufen** — `Werkstatt/Worktrees/investment/OKX_API.env`
      liegt im Klartext, wird aber von keinem Skript gelesen (geprüft
      23.08.2026). Erst im Portal widerrufen, dann die Datei löschen. Anleitung
      in [[Zugaenge]].
- [ ] **Unraid-Reste entscheiden** — SSH-Hostschlüssel, `passwd`, `shadow`,
      `smbpasswd`, `secrets.tdb`, `unbalanced.env` unter
      `Archiv/Software/Linux/Unraid/`. `sichern.ps1` listet sie bei jedem Lauf
      unter „noch nicht bewertet" auf.
- [x] ~~**Kopie außer Haus anlegen**~~ — 25.08.2026 auf `E:` angelegt
      (46,2 GB). Offen bleibt: **die SSD auch wirklich aus dem Haus bringen**
      und regelmäßig nachziehen — das Skript läuft von Hand, nicht als Aufgabe.
- [ ] **`E:` verschlüsseln (BitLocker To Go)** — auf der Kopie außer Haus liegen
      Klartext-Zugangsdaten. Eine Platte außerhalb kann verloren gehen; im
      Rechner war das Risiko geringer.
- [ ] **Zeitsynchronisation läuft nicht** — der Dienst `w32time` ist gestoppt
      (`w32tm /query /source` meldet 0x80070426, geprüft 25.08.2026). Bei einem
      Rechner mit unerklärten Abschaltungen driftet die Uhr dadurch ungebremst,
      und Zeitstempel in Sicherungen und Protokollen werden unzuverlässig.
- [ ] **Toten Ordner aus `localAgentModeTrustedFolders` nehmen** — der Eintrag
      steht auf `Documents\BrainFiles\KI Futter`, und dieser Ordner existiert
      nicht mehr (geprüft 23.08.2026). Wirkungslos, aber irreführend. Die frühere
      Formulierung („zeigt auf `Referenz\`") war falsch: `Referenz\` steht dort
      gar nicht, `MaxHirn` dagegen schon. Ändern nur bei geschlossener App.
- [x] ~~[[Profil]] ausfüllen~~ — 19.08.2026 aus Vault und Archiv befüllt;
      offene Punkte dort mit `⬚ offen` markiert
- [ ] MCP-Verbindungen authentifizieren (siehe [[Verbindungen]])
- [ ] Routinen einplanen (siehe [[Routinen]])
- [ ] `Maximilianbackup0924` (48,8 GB) — existiert nur noch auf G:. Wird es noch
      gebraucht? Wenn ja: zweiter Ort. Wenn nein: weg, Sicherung halbiert sich.
