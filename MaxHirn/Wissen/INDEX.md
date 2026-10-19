---
id: 20260830-index
title: 'Wissen — Index'
tags: [betrieb]
created: 2026-08-30
updated: 2026-10-13
related: []
summary: 'Einstiegspunkt für Agenten: vollständiges Verzeichnis aller Notizen in Wissen/ mit Zweck und Pfad.'
---

# Wissen — Index

Verbindliches Verzeichnis aller Notizen in `Wissen/`. Diese Datei ist die
Wahrheit darüber, **welche** Notizen es gibt; [[Dashboard]] bleibt die
kuratierte Startseite für Menschen und zeigt bewusst nur einen Teil.

## Für Agenten: so wird gelesen

1. Erst diesen Index lesen, dann anhand der Beschreibungen **1–3 Notizen**
   gezielt öffnen. Nicht den ganzen Ordner einlesen.
2. Was hier steht, wird nicht neu erhoben. Eine Zahl aus einer Notiz wird
   zitiert, nicht nachgemessen.
3. Beim Zitieren die `id` aus dem Frontmatter angeben, nicht den Dateinamen.

## Für Agenten: so wird gepflegt

- Neue dauerhafte Erkenntnis → **neue Notiz** mit vollständigem Frontmatter
  (`id`, `title`, `tags`, `created`, `updated`, `related`, `summary`).
- Bestehendes Thema geändert → Notiz **an Ort und Stelle** ändern und
  `updated` hochsetzen. Keine zweite Notiz zum selben Thema.
- Jedes Anlegen, Umbenennen oder Löschen einer Notiz **muss im selben
  Arbeitsschritt** hier in der Registry nachgezogen werden.
- `id` ist dauerhaft: `JJJJMMTT-slug`, wird nie geändert und nie wiederverwendet.
  Der Dateiname darf sich ändern, die `id` nicht.
- Nur Schlagwörter aus der Liste unten verwenden. Ein neues Schlagwort wird
  **erst hier eingetragen**, dann benutzt.
- Querverweise als `[[Dateiname]]` setzen und die Gegenstelle in `related`
  (dort mit `id`) spiegeln.

## Schlagwörter (kontrolliert)

`archiv`, `betrieb`, `finanzen`, `handel`, `hardware`, `holz`, `ki-agenten`,
`mcp`, `profil`, `sicherheit`, `steuern`, `struktur`, `system`

## Registry

Format: `` `id` — **Titel** — `Pfad` — wofür.``

### Betrieb und Agenten

- `20260830-index` — **Wissen — Index** — `Wissen/INDEX.md` — Diese Datei: verbindliches Verzeichnis aller Notizen. Steht mit drin, damit „alle Notizen“ wörtlich stimmt.
- `20260830-verbindungen` — **Verbindungen** — `Wissen/Verbindungen.md` — Welche Dienste und MCP-Server erreichbar sind und welche davon authentifiziert.
- `20260830-werkzeuge` — **Werkzeuge** — `Wissen/Werkzeuge.md` — Welche Werkzeuge tatsächlich abgerufen werden, gemessen an den bisherigen Sitzungen.
- `20260830-hermes` — **Hermes Agent** — `Wissen/Hermes.md` — Einrichtung, Ablageorte und Fallstricke des Hermes-Agenten neben Claude.
- `20260913-projektatlas` — **ProjectAtlas** — `Wissen/Projektatlas.md` — Rust-Werkzeug, das je Repo eine SQLite-Karte der Struktur anlegt, damit Agenten die richtige Datei finden statt breit zu lesen: Fork, Laufzeit, MCP-Eintrag, Rezept je Repo und die gemessenen Grenzen.
- `20260831-python-versionen` — **Python-Versionen** — `Wissen/Python-Versionen.md` — Installierte Python-Versionen und venv-Konfigurationen nach dem Upgrade auf 3.13.
- `20260830-routinen` — **Routinen** — `Wissen/Routinen.md` — Welche Abläufe ohne Aufforderung laufen, mit Zeitplan und Protokollort.
- `20260902-systempruefung` — **Systemprüfung** — `Wissen/Systempruefung.md` — Tägliche Morgenroutine, die das System nach still gebrochenen Dingen absucht (tote Junctions, doppelte Ollama-Stores, kaputte Pfade) und Eindeutiges selbst aufräumt.
- `20260830-wiederholbare-aufgaben` — **Wiederholbare Aufgaben** — `Wissen/Wiederholbare-Aufgaben.md` — Welche Arbeit sich wiederholt hat und welche Skills daraus entstanden sind.
- `20260830-portabilitaet` — **Portabilität** — `Wissen/Portabilitaet.md` — Was beim Umzug des gesamten Systems auf eine externe SSD zu beachten ist.
- `20260830-ordnerstruktur` — **Ordnerstruktur** — `Wissen/Ordnerstruktur.md` — Die vier Ordner unter `BrainFiles/`, warum sie geteilt sind und welche fünf Fallen beim Verschieben still brechen.
- `20260830-fristen` — **Fristen** — `Wissen/Fristen.md` — Alle laufenden Termine mit Konsequenz, ISO-datiert, gepflegt vom Skill `frist`.
- `20260916-optimierungen-finden` — **Optimierungen finden** — `Wissen/Optimierungen-2026-09-16.md` — Wöchentliche Prüfung der Routinen selbst (montags 09:45, `MaxHirn-Optimierungen-Finden`): Läufe ohne Ende-Zeile, Leichen in der Aufgabenplanung, Prozess-Drift. Warum ein abgebrochener Lauf niemandem auffällt und wie er belegt wird.
- `20260910-optimierungen-umgesetzt` — **Optimierungen — Umgesetzt (2026-09-10)** — `Wissen/Optimierungen-2026-09-10.md` — Drei umgesetzte Verbesserungen für Datensicherheit und Wartbarkeit, allen voran die monatliche Off-Site-Kopie auf USB-SSD.
- `20260911-off-site-backup` — **Off-Site Backup Setup — Monatliche Sicherung auf USB** — `Wissen/Off-Site-Backup.md` — Anleitung für die kalte Monatskopie auf eine externe USB-SSD gegen gleichzeitigen Ausfall von C:, G: und O:.
- `20260910-brainfiles-bus` — **BrainFiles Bus** — `Wissen/BrainFiles-Bus.md` — Zentraler Meldedienst für alle geplanten Aufgaben: Start, Prüfung, Betrieb; ein toter Bus bricht nie einen Lauf ab.
- `20260916-repo-bots` — **Repo-Bots: Flottenstand und Telegram-Zugang** — `Wissen/Repo-Bots.md` — Ein Hermes-Profil je Fremd-Repo in Werkstatt, erreichbar per Telegram über /bots und /bot NAME.
- `20260916-agent-reach` — **Agent Reach: Internet-Zugang für Agenten** — `Wissen/Agent-Reach.md` — Lesender Internet-Zugang (Twitter/X, Reddit, YouTube, GitHub, RSS, Web) ohne API-Schlüssel: Ablageort, Aufruf, Hermes-Profil.
- `20260917-openmontage` — **OpenMontage: Agentisches Videoproduktions-Framework** — `Wissen/OpenMontage.md` — Fork von calesthio/OpenMontage: 12 Produktionspipelines für KI-Videos, 41 von 121 Werkzeugen laufen ohne API-Schlüssel.

### Handel-Agenten (Betrieb)

- `20261013-handel-agenten-befund` — **Handel-Agenten: Befund 13.10.2026** — `Wissen/Handel-Agenten-Befund-20261013.md` — Dauerlauf-Überwachung wieder vollständig (alle vier Wächter-Aufgaben Ready, drei Stufen laufen auf Papier); Backtest-Varianten mit Hausfunktionen verglichen und bewusst stehen gelassen; 5,4 GB redundante state.db-Kopien entfernt.

### System und Hardware

- `20260830-hardware` — **Hardware** — `Wissen/Hardware.md` — Laufwerke des Arbeitsrechners, Plattendiagnose und der ungeklärte Stromausfall.
- `20260830-hardware-checkliste-d5` — **Hardware-Checkliste D5** — `Wissen/Hardware-Checkliste-D5.md` — Schrittfolge zur Eingrenzung des D5-RAM-Fehlers und der Kernel-Power-41-Abschaltungen.
- `20260930-systembild` — **Systembild** — `Wissen/Systembild.md` — Gemessener Stand von C: und O: (Belegung, Schwergewichte, Programme) und die daraus abgeleiteten Aufraeum-Kandidaten.
- `20260830-benutzerprofil` — **Benutzerprofil** — `Wissen/Benutzerprofil.md` — Was im Windows-Benutzerprofil liegt, was davon zum Betrieb gehört und was Altlast ist.
- `20260830-ki-ablagen-benutzerordner` — **KI-Ablagen im Benutzerordner** — `Wissen/KI-Ablagen-im-Benutzerordner.md` — Welche KI-Daten außerhalb von `BrainFiles/` liegen, warum sie dort bleiben und was bei einem Neuaufsetzen verlorenginge.
- `20260830-miniaturansichten` — **Miniaturansichten** — `Wissen/Miniaturansichten.md` — Warum der Explorer keine Vorschaubilder mehr zeigte und was dagegen geholfen hat.
- `20260901-globale-npm-tools-path` — **Globale npm-Tools und PATH** — `Wissen/Globale-npm-Tools-PATH.md` — Warum global installierte npm-CLIs (omniroute, opencode) nicht erkannt wurden (Volta + fehlender `Roaming\\npm`-Eintrag) und der gesetzte PATH-Fix.
- `20260907-omniroute-produktion` — **OmniRoute-Produktion** — `Wissen/OmniRoute-Produktion.md` — OmniRoute-Quell-Klon als Produktions-Router installiert und verifiziert; Umstieg gegen die globale Instanz vorbereitet (Entscheidung offen).

### Sicherheit

- `20260830-schutzregeln` — **Schutzregeln** — `Wissen/Schutzregeln.md` — Welche Dateien in `MaxHirn/` ein Agent nicht anfassen darf und warum.
- `20260830-zugaenge` — **Zugänge** — `Wissen/Zugaenge.md` — Zentrale und einzige Ablage aller API-Schlüssel und Tokens. **Geschützt: nur auf ausdrückliche Anweisung ändern, kein Frontmatter.**
- `20260830-passwoerter-quarantaene` — **Passwörter-Quarantäne** — `Wissen/Passwoerter-Quarantaene.md` — Arbeitsliste der Dienste aus dem Firefox-Export, deren Passwörter noch zu ändern sind.
- `20260908-onchainos-backup` — **OnChainOS Backup** — `Wissen/OnChainOS_Backup.md` — Archivierte OnChainOS-Konfiguration (Identität, Wallet-Konfiguration, Session) vom 08.09.2026: Herkunft, Inhalt, Aufbewahrungsort.

### Steuern und Geld

- `20260830-steuerunterlagen` — **Steuerunterlagen** — `Wissen/Steuerunterlagen.md` — Steuernummern, veranlagte Jahre, Bescheide und laufende Verfahren.
- `20260830-belege-einspruch-2024` — **Belege zum Einspruch ESt 2024** — `Wissen/Belege-Einspruch-2024.md` — Welche Nachweise gesammelt sind und was bis 30.09.2026 noch fehlt.
- `20260902-handelsregeln` — **Handelsregeln** — `Wissen/Handelsregeln.md` — Was ein Agent im Handel selbst auslösen darf: die drei bewachten Spuren (OKX-Spot, XPERP-Hebel, Kraken-EUR), der weiterhin lesende Kraken-MCP, Prüfpflicht und die fünf Freigabebedingungen. Bis 02.09.2026 Teil der Schutzregeln.
- `20260830-handelsbots` — **Handelsbots auf OKX** — `Wissen/Handelsbots.md` — Gemessene Ergebnisse der DCA-Bots und welche Stellschraube tatsächlich wirkt.
- `20260831-marktscanner` — **Marktscanner OKX** — `Wissen/Marktscanner.md` — Täglicher Krypto-Scanner mit begrenztem Selbsthandel: Entscheidung, Grenzen, Scharfschalt-Weg, Stand.
- `20260929-omnitrade` — **omnitrade — Live-Lauf auf OKX-Demo mit Anzeige** — `Wissen/Omnitrade.md` — Anleitung: omnitrade (Rust) im OKX-Demo starten (EEA-Region, BTCUSDC, 500 USD je Position, long-only) und im Reiter „omnitrade“ der Handelszentrale verfolgen; Schlüsselnamen und Fallen.
- `20260906-verbesserer` — **Verbesserer — Spur 1** — `Wissen/Verbesserer.md` — Wöchentliche Schleife mit OOS-geprüften Vorschlägen für bessere Scanner-Parameter: Entscheidung, Whitelist/Denylist, schwache Overfitting-Sperre, Anwende-Weg, Stand.
- `20260907-marktbriefing` — **Marktbriefing — Routine und Verfahren** — `Wissen/Marktbriefing.md` — Lesende Routine, die aus den fertigen traderhub-Boards (Makro, Sektorrotation, Einzelwerte) einen geprüften Marktüberblick zusammenträgt und als Monatsnotiz fortschreibt. Kein Handel.
- `20260830-marktlage-august-2026` — **Marktlage August 2026** — `Wissen/Marktlage-August-2026.md` — Geprüfter Marktstand samt Bewertung der zugrunde liegenden Quelle.
- `20260907-marktlage-september-2026` — **Marktlage September 2026** — `Wissen/Marktlage-September-2026.md` — Laufende Monatsnotiz mit den Tagesständen aus dem Marktbriefing (traderhub-Boards, geprüft, als Einordnung).
- `20260902-xrp-analyse-sta` — **XRP-Analyse STA Solutions — September 2026** — `Wissen/XRP-Analyse-STA-September-2026.md` — Charttechnik- und Indikatoren-Analyse zu XRP aus einem YouTube-Beitrag desselben Kanals: Preismarken (v. a. 3,30 USD), ITW-Methodik, Positionierungsvorschlag, kritische Einordnung.
- `20260905-btc-analyse-sta` — **BTC-Analyse STA Solutions — September 2026** — `Wissen/BTC-Analyse-STA-September-2026.md` — Charttechnik- und Volumen-Analyse zu Bitcoin (OBV/CVD-Squeeze-Diagnostik, RSI/MACD-Divergenzen, strukturelle Marken, Primärszenario) aus einem YouTube-Beitrag desselben Kanals.
- `20260902-analyse-quellen` — **Analyse-Quellen** — `Wissen/Analyse-Quellen.md` — Wiederkehrende externe Analyse-Quellen (STA Solutions, xGhozt Prophecies) mit fester Einstufung, damit die Quellenbewertung nicht je Einzelnotiz neu geschrieben wird.
- `20260901-chip-xperp` — **CHIP XPERP auf OKX** — `Wissen/CHIP-XPERP.md` — Analyse für einen gehebelten Anlauf auf CHIP: 14-Tage-Fenster täuscht, reale 133-Tage-Historie negativ, alle drei Tore zu.
- `20260901-xperp-handel` — **XPERP-Handel auf OKX** — `Wissen/XPERP-Handel.md` — Wo die gehebelten Perpetuals liegen, welche Werte 5x tragen und warum der Hebel aus dem Stop fällt statt umgekehrt.
- `20260901-saisonalitaet-signal` — **Saisonalität im XPERP-Signal** — `Wissen/Saisonalitaet-Signal.md` — Warum der Closed-Source-Indikator „xGhozt Prophecies" als Kalenderstatistik nachgebaut ist, hoch gewichtet ins Signal greift und trotzdem laut seine dünne Stichprobe nennt.
- `20260908-volumen-drift-signal` — **Volumen-Drift-Momentum im XPERP-Signal** — `Wissen/Volumen-Drift-Signal.md` — Eigener Nachbau des Prinzips von Swift Algo X (TradingView, Invite-Only) — volumengewichtete Preisdrift mit Mehrfach-Zeitebenen-Bestätigung, hoch gewichtet ins Signal, mit Vorrang vor der Saisonalität.
- `20260913-buildix-santiment` — **Orderflow- und Verhaltensdaten: Buildix & Santiment** — `Wissen/Buildix-Santiment-Handelswissen.md` — Zwei neue externe Handelswissen-Quellen: Buildix (Hyperliquid-Orderflow, CVD/VPIN/OBI/OFI-Logik, Learn-Academy) und Santiment (1100+ On-Chain-/Social-/Dev-Metriken, MVRV/DAA/Age-Consumed-Methodik); Ernte mit Scrapling am 13.09.2026.
- `20260913-cvd-divergenz-signal` — **CVD-4h-Divergenz im XPERP/SWAP-Signal** — `Wissen/CVD-4h-Divergenz-Signal.md` — Dritter hoch gewichteter Baustein im Signal: CVD (kumulierte Differenz aggressiver Käufe und Verkäufe) aus dem OKX-Taker-Volumen je Kontrakt in 4h-Eimern, als Divergenz gegen den Preis (Buildix-Prinzip) — mit Herkunft der Zahlen, Rangfolge der drei hoch gewichteten Bausteine, Schwellen-Kalibrierung an 1287 Fenstern und der Host-Falle unter `/rubik/`.
- `20260919-moon-dev-code-studien` — **Moon-Dev-Code: die drei Strategie-PDFs** — `Wissen/Moon-Dev-Code-Studien.md` — Gelesene Zusammenfassung der drei Paper in `Werkstatt/Moon-Dev-Code/strategy_pdfs/`: Psychologie des Krypto-Handels (Delfabbro 2021, Risikofaktoren FOMO/Kontroll-Illusion), Deep Reinforcement Learning für Handelspunkte (Appl. Sci. 2020, Backtest-Renditen ohne Kostenmodell), EMH-Survey über 38 Studien (JRFM 2019, Langzeit-Gedächtnis verblasst mit Marktreife). Kein Code/Parameter übernommen.
- `20260921-archiv-trading-skills` — **Archiv-Trading-Skills und Fremdstrategien im Lauf** — `Wissen/Archiv-Trading-Skills.md` — Was von den ausgemusterten Handels-Skills lauffähig ist (nur `geld`; `marktbriefing` hängt am fehlenden `traderhub`, `financial-services` bleibt bewusst im Archiv) und was eine gefahrene Fremdstrategie messbar liefert: TTM-Squeeze+ADX auf neun Jahren BTC-Stundenkerzen ergibt einen Kosten-Wendepunkt von ≈ 0,10 % je Runde — rund 100-mal schlechter als der Haus-Scanner. Dazu der eigentliche Fund: neun Jahre lokale Kursdaten und vier Backtest-Umgebungen mit venv unter `Werkstatt/`.
- `20260921-prognose-backtest` — **Prognose-Spuren-Backtest** — `Wissen/Prognose-Spuren-Backtest.md` — Erster langer Backtest der vier Prognose-Spuren (7000 Stundenkerzen, 0,10 % Gebuehr je Seite): tragen tut nur die LONG-Seite von macd_mtf (+2,28 % je Runde, 48 % Treffer) und squeeze (+1,57 %); short ist bei allen vier negativ, wavetrend und supertrend sind auf beiden Seiten negativ. Das Kurzfenster war ein Aufwaertsmarkt und ist die freundlichere Zahl — der Langlauf ist der Massstab. Werkzeug: `Agenten/Handel/backtest_prognose.py` + `bt_lang.py`.
- `20260918-handel-stack-repo` — **Handel-Stack als eigenes Repo** — `Wissen/Handel-Stack-Repo.md` — Agenten/Handel als privates GitHub-Repo mfaupel95/handel-stack gespiegelt: Umfang, Ausschlüsse, fehlende CI-Workflows, Schnappschuss-Charakter.
- `20260916-moon-dev-agenten` — **Moon-Dev-Agenten** — `Wissen/Moon-Dev-Agenten.md` — Stand der installierten Moon-Dev-Repos (46 Agenten, TradingView-MCP), die vier Haus-Spuren daraus und was vorgemerkt ist.
- `20260917-awesome-systematic-trading` — **awesome-systematic-trading** — `Wissen/Awesome-Systematic-Trading.md` — Fork einer reinen Markdown-Referenzliste: 136 Backtesting-/Live-Trading-Bibliotheken, Kennzahlen aus 4.843 replizierten Papers; nichts zu installieren.
- `20260919-nautilus-candle-rust` — **NautilusTrader + candle: Rust-KI-Stack** — `Wissen/Nautilus-Candle-Rust-Stack.md` — Zwei-Ebenen-Architektur in einem Cargo-Workspace: Research-Ebene fittet das Modell, Execution-Ebene entscheidet, der Linker erzwingt die Trennung.

### Handel — Sonderregeln

- `20260908-ausnahme-usdg-live` — **Ausnahme — 100 USDG als Live-Start (Spur 1)** — `Wissen/Ausnahme-USDG-Live.md` — Von Max angeordnete, gedeckelte Ausnahme: bis 100 USDG real in Spur 1 (OKX Spot), bevor die Rundensperre erfüllt ist. Voraussetzungen (Live-Key mit Trade-Recht, USDG→Börsenkonto) und zeitliche Begrenzung.

### Person und Fachliches

- `20260830-profil` — **Profil** — `Wissen/Profil.md` — Wer Max ist und wie er arbeitet; Fundament für Antworten ohne Werkzeugaufruf.
- `20260919-willkommen` — **Willkommen für KI — Q&A über Max und das System** — `Wissen/Willkommen-fuer-KI.md` — Einführung für eine weitere KI: wer Max ist, wie das KI-Betriebssystem gebaut ist (Wissensarchiv, mehrere Agenten auf geteilter Basis, harte Trennung Betrieb/Finanzen) und welche Spielregeln gelten; bewusst ohne konkrete Inhalte, Zugangsdaten, Pfade oder Zahlen.
- `20260830-projekte` — **Projekte** — `Wissen/Projekte.md` — Was gerade läuft, ein Abschnitt je Projekt.
- `20260830-fachkunde-holztechnik` — **Fachkunde Holztechnik** — `Wissen/Fachkunde-Holztechnik.md` — Inhalt und Ablage des Lehrwerks im Archiv.
- `20260908-studium` — **Studium — Unterlagen im Archiv** — `Wissen/Studium.md` — Studienunterlagen (TH Bingen, Uni KL: Botanik, Physik, Wirtschaftslehre u. a.) im Archiv, für Archivsuche erschlossen.
- `20260908-sound-studio` — **Maks Sound — Ton-/Licht-/Lasertechnik** — `Wissen/Maks-Sound.md` — Gewerblicher Sound-/Technikbestand (DJ-Handbücher, Laserworld, Verleih-Rechnungen) im Archiv, durchsuchbar.

### Verfahren

- `20260830-pdf-scans-lesen` — **Gescannte PDFs lesen** — `Wissen/PDF-Scans-lesen.md` — Wie PDFs ohne Textebene per OCR auswertbar gemacht werden.
- `20260902-skill-bibliothek` — **Skill-Bibliothek** — `Wissen/Skill-Bibliothek.md` — Eigene Skills liegen serverseitig im Konto; der Ordner unter AppData ist nur ein Sync-Cache ohne Git und ohne Sicherung.
- `20260917-task-observer-metaskill` — **Task-Observer — Meta-Skill zur Skill-Selbstverbesserung** — `Wissen/Task-Observer-Metaskill.md` — Bewertung des fremden Claude-Meta-Skills „One Skill to Rule Them All" (rebelytics, CC BY 4.0): Funktionsweise, Claude-spezifische Abhängigkeiten, Token-Kosten gegen die Skill-Ausmist-Linie, Entscheidung offen.
- `20260917-externe-api-referenz` — **Externe API-Referenz (public-apis-Liste)** — `Wissen/Externe-API-Referenz-2026-09-17.md` — Angehängte public-apis-README als Nachschlagewerk erfasst; Standouts mit Bezug zu laufenden Handelsspuren (DefiLlama, Hyperliquid Market Data, PumpFunData, Messari, FRED).
- `20260917-beobachtungslog` — **Beobachtungslog** — `Wissen/Beobachtungen/README.md` — Verzeichnis mit einer Markdown-Datei je beobachtetem Skill-Verbesserungsbedarf, gepflegt vom Skill `beobachtungslog` (schlanker Eigenbau statt des fremden Task-Observer-Meta-Skills).
- `20261006-sitzungsanalyse` — **Sitzungsanalyse — Themen, Fehler, offene Punkte, Erfolge** — `Wissen/Sitzungsanalyse-2026-10-06.md` — Auswertung von 1.479 User-Nachrichten (05.08.–06.10.2026) und TASKS.md (T-001 bis T-371): Themencluster, sieben Fehler-Klassen, priorisierte offene Punkte, belegte Erfolge.
- `20261008-stash-geteilter-arbeitsbaum` — **git stash im geteilten Arbeitsbaum** — `Wissen/Stash-Geteilter-Arbeitsbaum.md` — Warum `git stash` im Mehrsitzungsbetrieb Arbeit einfriert und beim Pop gegen Zwischencommits konfligiert; Auflösungsmuster per Datum, Ablösung durch sofortiges Committen.
