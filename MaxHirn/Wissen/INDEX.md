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

- `20261022-claude-code-auto-mode-abrechnung` - **Claude Code: Auto-Mode-Abrechnung** - `Wissen/Claude-Code-Auto-Mode-Abrechnung.md` - Bestandsaufnahme 22.10.2026: Version 2.1.307, claude.ai Pro direkt, `defaultMode: auto`; keine Gateway-Anpassung oder Konfigurationsänderung nötig.

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
- `20261021-handelsuniversum` — **Handelsuniversum** — `Wissen/Handelsuniversum.md` — Welche Instrumente eine Spur handeln darf, wo die Liste steht (eine Quelle je Spur), und dass Backtest und Betrieb dasselbe Universum nennen.
- `20261021-quant-konzepte` — **Quant-Konzepte aus den fidetolabs-Reels** — `Wissen/Quant-Konzepte-fidetolabs.md` — Sechs Methoden (Marchenko-Pastur, Fractional Differencing, Triple Barrier, Signature Plot, CUSUM, Breeden-Litzenberger), was sie tun und was die Captions weglassen.
- `20261021-signature-plot` — **Signature Plot auf XBTEUR** — `Wissen/Signature-Plot-XBTEUR.md` — Realized Volatility über Abtastintervalle (720 Fünf-Minuten-Kerzen): flach zwischen 5 und 60 Minuten, kein Rauschaufschlag, Methode und Fallen.
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
- `20261021-kelly-positionsgroesse` — **Kelly-Kriterium: Positionsgröße aus gemessenem Vorteil** — `Wissen/Kelly-Positionsgroesse.md` — Kelly-Formel und Bruchteil-Kelly aus drei Papers (Dang & Woods, Markopoulos, CryptoPredictions) gegen Einsatzregeln und Ratsche; Kelly-Check der gemessenen Spuren: nur der Scanner hat Vorteil an der Konfidenzgrenze, Größenerhöhung nicht freigegeben.
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

- `20261020-sitzungs-konsolidierung` — **Sitzungs-Konsolidierung 20.10.2026** — `Wissen/Sitzungs-Konsolidierung-2026-10-20.md` — Dauerhaft gueltige Fakten aus der Konsolidierung (Verbesserer aus, WSL 16 GB, Pinecone, Mediathek abgeschrieben, Kill-Switch), offene Entscheidungen und Verweis auf den Plan.
- `20261021-skill-lernen-profil` — **Skill-Lernen: Trockenlauf build-user-profile** — `Wissen/Skill-Lernen/skill-adaptive-agent-build-user-profile.md` — Warum der Profil-Skill neben `Wissen/Profil.md` eine Dublette wäre; Trockenlauf ohne Schreibzugriff.
- `20261021-skill-lernen-skill-review` — **Skill-Lernen: Trockenlauf skill-review** — `Wissen/Skill-Lernen/skill-adaptive-agent-skill-review.md` — Pflege-Skill passt schlecht zu einem Trockenlauf; Plugin-Skills liegen ohne Git-Repo im Cache.
- `20261021-skill-lernen-api-schnittstelle` — **Skill-Lernen: Schnittstellenprüfung skill-lernen** — `Wissen/Skill-Lernen/skill-agent-protocols-api-and-interface-design.md` — Acht Mehrdeutigkeiten im Skill (Dateiname der Notiz, Statuswerte, Spalten, Indexzeile).
- `20261021-skill-lernen-memory-search` — **Skill-Lernen: memory-search nicht ausführbar** — `Wissen/Skill-Lernen/skill-agent-memory-memory-search.md` — Gedächtnis-Werkzeug nicht geladen, weil der zugehörige MCP-Server nicht verbunden ist.
- `20261021-skill-lernen-browser-devtools` — **Skill-Lernen: browser-testing-with-devtools** — `Wissen/Skill-Lernen/skill-agent-protocols-browser-testing-with-devtools.md` — Chrome DevTools MCP für Live-Browser-Debugging; Trockenlauf, da kein Browser-Kontext vorhanden.
- `20261022-skill-lernen-build` — **Skill-Lernen: build (Trockenlauf)** — `Wissen/Skill-Lernen/skill-agent-protocols-build.md` — Build-Ablauf für Textregeln: Tests und Build entfallen, Ersatz ist eine Konsistenzprüfung gegen die Wertliste.
- `20261022-skill-lernen-ci-cd` — **Skill-Lernen: ci-cd-and-automation** — `Wissen/Skill-Lernen/skill-agent-protocols-ci-cd-and-automation.md` — GitHub-Actions-CI/CD-Muster: Quality Gates, Deployment-Strategien, Rollback; Trockenlauf.
- `20261022-skill-lernen-code-review` — **Skill-Lernen: code-review-and-quality** — `Wissen/Skill-Lernen/skill-agent-protocols-code-review-and-quality.md` — Fünf-Achsen-Review mit Schwere-Labeln; Trockenlauf.
- `20261022-skill-lernen-code-simplification` — **Skill-Lernen: code-simplification** — `Wissen/Skill-Lernen/skill-agent-protocols-code-simplification.md` — Fünf Prinzipien zum Vereinfachen ohne Verhaltensänderung; Trockenlauf.
- `20261022-skill-lernen-context-engineering` — **Skill-Lernen: context-engineering** — `Wissen/Skill-Lernen/skill-agent-protocols-context-engineering.md` — Fünfstufige Kontexthierarchie, <2000-Zeilen-Regel, Verwirrungsmanagement; Trockenlauf.
- `20261022-skill-lernen-debugging` — **Skill-Lernen: debugging-and-error-recovery** — `Wissen/Skill-Lernen/skill-agent-protocols-debugging-and-error-recovery.md` — Sechsstufige Triage, git-bisect-Automatisierung, Fehlerausgabe als unvertrauenswürdige Daten; Trockenlauf.
- `20261022-skill-lernen-deprecation` — **Skill-Lernen: deprecation-and-migration** — `Wissen/Skill-Lernen/skill-agent-protocols-deprecation-and-migration.md` — Code als Verbindlichkeit, Churn-Regel, Strangler/Adapter/Feature-Flag-Muster; Trockenlauf.
- `20261022-skill-lernen-documentation-adrs` — **Skill-Lernen: documentation-and-adrs** — `Wissen/Skill-Lernen/skill-agent-protocols-documentation-and-adrs.md` — ADR-Vorlage mit Status-Lifecycle, Inline-Kommentare nur für das Warum; Trockenlauf.
- `20261022-skill-lernen-frontend-ui` — **Skill-Lernen: frontend-ui-engineering** — `Wissen/Skill-Lernen/skill-agent-protocols-frontend-ui-engineering.md` — KI-Ästhetik vermeiden, WCAG AA, State-Management-Hierarchie; Trockenlauf.
- `20261022-skill-lernen-git-workflow` — **Skill-Lernen: git-workflow-and-versioning** — `Wissen/Skill-Lernen/skill-agent-protocols-git-workflow-and-versioning.md` — Trunk-Based Dev, atomare Commits, DIDN'T-TOUCH-Muster, Worktrees; Trockenlauf.
- `20261022-skill-lernen-idea-refine` — **Skill-Lernen: idea-refine** — `Wissen/Skill-Lernen/skill-agent-protocols-idea-refine.md` — Drei-Phasen-Ideation mit Not-Doing-Liste als Kernoutput; Trockenlauf.
- `20261022-skill-lernen-incident-response` — **Skill-Lernen: incident-response-and-postmortems** — `Wissen/Skill-Lernen/skill-agent-protocols-incident-response-and-postmortems.md` — Fünf-Phasen-Incident-Response, Blameless-Postmortem, Beweissicherung; Trockenlauf.
- `20261022-skill-lernen-incremental-impl` — **Skill-Lernen: incremental-implementation** — `Wissen/Skill-Lernen/skill-agent-protocols-incremental-implementation.md` — Vertikale Scheiben, NOTICED-BUT-NOT-TOUCHING-Muster, Risk-First-Slicing; Trockenlauf.
- `20261022-skill-lernen-i18n` — **Skill-Lernen: internationalization-and-localization** — `Wissen/Skill-Lernen/skill-agent-protocols-internationalization-and-localization.md` — ICU-Pluralisierung, Pseudo-Lokalisierung als CI-Gate, RTL mit logischen CSS-Eigenschaften; Trockenlauf.
- `20261022-skill-lernen-karpathy` — **Skill-Lernen: karpathy-guidelines** — `Wissen/Skill-Lernen/skill-agent-protocols-karpathy-guidelines.md` — Vier Verhaltensregeln gegen LLM-Coding-Fallen: Annahmen explizit, Minimalcode, chirurgische Änderungen, verifizierbare Ziele; Trockenlauf.
- `20261022-skill-lernen-perf-opt` — **Skill-Lernen: performance-optimization** — `Wissen/Skill-Lernen/skill-agent-protocols-performance-optimization.md` — Messen-zuerst-Workflow, Core Web Vitals, N+1/Bundle/Re-render-Gegenmuster, fetchpriority, CI-Budget; Trockenlauf.
- `20261022-skill-lernen-plan` — **Skill-Lernen: plan (Trockenlauf)** — `Wissen/Skill-Lernen/skill-agent-protocols-plan.md` — Plan für eine Statuswert-Prüfung des Fortschritts; Testlauf zeigt eine Zeile mit fünf statt vier Spalten.
- `20261022-skill-lernen-research-spike` — **Skill-Lernen: research-spike-and-poc** — `Wissen/Skill-Lernen/skill-agent-protocols-research-spike-and-poc.md` — Charter vor PoC, Zeitbox und Proceed/Pivot/Stop; Trockenlaufregel kollidiert nicht mit Fortschritt, Empfehlung Fortsetzen; Spike-Code nicht nach master.
- `20261022-skill-lernen-planning-breakdown` — **Skill-Lernen: planning-and-task-breakdown** — `Wissen/Skill-Lernen/skill-agent-protocols-planning-and-task-breakdown.md` — Abhängigkeitsgraph, vertikales Slicing, Aufgabenformat mit Akzeptanzkriterien, XS–XL-Größentabelle, Checkpoints; Trockenlauf.
- `20261022-skill-lernen-security` — **Skill-Lernen: security-and-hardening** — `Wissen/Skill-Lernen/skill-agent-protocols-security-and-hardening.md` — Drei-Tier-Grenzsystem, OWASP-Top-10-Snippets, Zod-Validierung, npm-audit-Triage, Secrets-Management; Trockenlauf.
- `20261022-skill-lernen-shipping` — **Skill-Lernen: shipping-and-launch** — `Wissen/Skill-Lernen/skill-agent-protocols-shipping-and-launch.md` — Pre-Launch-Checkliste, Feature-Flag-Lifecycle mit 2-Wochen-Aufräum-Deadline, Rollout-Schwellenwerte, Rollback-Plan-Vorlage; Trockenlauf.
- `20261022-skill-lernen-source-driven` — **Skill-Lernen: source-driven-development** — `Wissen/Skill-Lernen/skill-agent-protocols-source-driven-development.md` — Detect→Fetch→Implement→Cite, Deep-Link-Pflicht, UNVERIFIED-Flag, kein Stack Overflow als Primärquelle; Trockenlauf.
- `20261022-skill-lernen-spec-driven` — **Skill-Lernen: spec-driven-development** — `Wissen/Skill-Lernen/skill-agent-protocols-spec-driven-development.md` — Vier-Phasen-Gate, sechs Spec-Pflichtbereiche, Annahmen-Block zuerst, Anforderungen als messbare Akzeptanzkriterien; Trockenlauf.
- `20261022-skill-lernen-tdd` — **Skill-Lernen: test-driven-development** — `Wissen/Skill-Lernen/skill-agent-protocols-test-driven-development.md` — Red-Green-Refactor, Prove-It-Pattern, DAMP über DRY, Real>Fake>Stub>Mock, Zustand testen nicht Interaktion; Trockenlauf.
- `20261022-skill-lernen-using-skills` — **Skill-Lernen: using-agent-skills** — `Wissen/Skill-Lernen/skill-agent-protocols-using-agent-skills.md` — Meta-Skill: Entdeckungsbaum, sechs Kernverhaltensregeln, zehn Failure-Modes, vollständige Lifecycle-Sequenz; Trockenlauf.
- `20261022-skill-lernen-sdk-new-app` — **Skill-Lernen: agent-sdk-dev:new-sdk-app** — `Wissen/Skill-Lernen/skill-agent-sdk-dev-new-sdk-app.md` — Setup-Wizard für neue Agent SDK Apps (TS/Py), Versions-Check npm/PyPI, tsc-Verifikation, Verifier-Agent; Trockenlauf.
- `20261022-skill-lernen-algo-art` — **Skill-Lernen: algorithmic-art** — `Wissen/Skill-Lernen/skill-anthropic-algorithmic-art.md` — Zwei-Phasen-Workflow: Kunstphilosophie (.md) + p5.js-Implementierung (.html), Seed-Navigation, Anthropic-Branding; Trockenlauf.
- `20261022-skill-lernen-brand-guide` — **Skill-Lernen: brand-guidelines** — `Wissen/Skill-Lernen/skill-anthropic-brand-guidelines.md` — Anthropic-Farbpalette und Typografie-Referenz (Poppins/Lora, 7 Farben); Trockenlauf.
- `20261022-skill-lernen-canvas-design` — **Skill-Lernen: canvas-design** — `Wissen/Skill-Lernen/skill-anthropic-canvas-design.md` — Visuelle Designphilosophie + PDF/PNG-Ausgabe, Museumsqualität, minimaler Text; Trockenlauf.
- `20261022-skill-lernen-docs` — **Skill-Lernen: docs** — `Wissen/Skill-Lernen/skill-anthropic-docs.md` — Weiterleitungs-Skill zum Docs-Connector; ohne MCP nicht ausführbar.
- `20261022-skill-lernen-docx` — **Skill-Lernen: docx** — `Wissen/Skill-Lernen/skill-anthropic-docx.md` — Word-Dateien erstellen/bearbeiten/lesen, Tracked Changes, Kommentare, Gotchas-Referenz; Trockenlauf.
- `20261022-skill-lernen-import-memory` — **Skill-Lernen: import-memory** — `Wissen/Skill-Lernen/skill-anthropic-import-memory.md` — Memory-Import aus ChatGPT/Gemini, 6-Stufen-Workflow, Datenschutz-Filter, Injektionsschutz; Trockenlauf.
- `20261022-skill-lernen-internal-comms` — **Skill-Lernen: internal-comms** — `Wissen/Skill-Lernen/skill-anthropic-internal-comms.md` — Dispatcher für interne Unternehmenskommunikation (3P, Newsletter, FAQ); Trockenlauf.
- `20261022-skill-lernen-learn` — **Skill-Lernen: learn** — `Wissen/Skill-Lernen/skill-anthropic-learn.md` — Tutoring-Skill: Diagnose vor Erklärung, 6 Moves, Zeitdruck-Erkennung, akademische Integrität; Trockenlauf.
- `20261022-skill-lernen-local-ai-config-doctor` — **Skill-Lernen: local-ai-config-doctor** — `Wissen/Skill-Lernen/skill-anthropic-local-ai-config-doctor.md` — 8-Schritte KI-Config-Diagnose: effektive Config zuerst, empirisch prüfen, Diagnosemeldungen hinterfragen; Trockenlauf.
- `20261022-skill-lernen-mcp-builder` — **Skill-Lernen: mcp-builder** — `Wissen/Skill-Lernen/skill-anthropic-mcp-builder.md` — 4-Phasen MCP-Server-Entwicklung: TypeScript-first, SDK v1 vs. v2, Coverage-first, Evaluations-Framework; Trockenlauf.
- `20261022-skill-lernen-morning` — **Skill-Lernen: morning** — `Wissen/Skill-Lernen/skill-anthropic-morning.md` — Tägliche Morgenübersicht als HTML (SVG-Terrain + Needs attention + Resolved); Base64-Font, Playwright-Render-Check, strenge Button-Regeln; Trockenlauf.
- `20261022-skill-lernen-pdf` — **Skill-Lernen: pdf** — `Wissen/Skill-Lernen/skill-anthropic-pdf.md` — Python-PDF-Toolkit (pypdf/pdfplumber/reportlab) + CLI; Fallstrick ReportLab-Unicode-Subskript; Trockenlauf.
- `20261022-skill-lernen-pptx` — **Skill-Lernen: pptx** — `Wissen/Skill-Lernen/skill-anthropic-pptx.md` — pptxgenjs PowerPoint-Guide: Structured Decks, ~15 kritische Fallstricke, QA-Pipeline; Trockenlauf.
- `20261022-skill-lernen-skill-creator` — **Skill-Lernen: skill-creator** — `Wissen/Skill-Lernen/skill-anthropic-skill-creator.md` — Vollständiger Skill-Lifecycle: Capture Intent→Evals→Iteration→Description Optimization; Viewer immer vor eigener Bewertung; Trockenlauf.
- `20261022-skill-lernen-theme-factory` — **Skill-Lernen: theme-factory** — `Wissen/Skill-Lernen/skill-anthropic-theme-factory.md` — 10 Deck-Themes (PDF-Showcase→Auswahl→Anwenden), Custom-Theme möglich; Trockenlauf.
- `20261022-skill-lernen-web-artifacts-builder` — **Skill-Lernen: web-artifacts-builder** — `Wissen/Skill-Lernen/skill-anthropic-web-artifacts-builder.md` — React+TS+Vite+Parcel+shadcn/ui→bundle.html für Artifacts; Trockenlauf.
- `20261022-skill-lernen-xlsx` — **Skill-Lernen: xlsx** — `Wissen/Skill-Lernen/skill-anthropic-xlsx.md` — openpyxl/pandas Excel-Guide: recalc.py Pflicht, verbotene Funktionen, Finanzmodell-Konventionen; Trockenlauf.
- `20261022-skill-lernen-rust-performance` — **Skill-Lernen: rust-performance** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-performance.md` — Audit, Messung und Optimierung getrennt; hyperfine, kein cargo run. Keine Profil-Einstellungen oder Messwerte vorhanden; Arbeitslast und Basis messen und vorher/nachher vergleichen.
- `20261022-skill-lernen-rust-processes` — **Skill-Lernen: rust-processes** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-processes.md` — Command, Streams, Exit-Status, Timeout beendet keinen Prozess, Process Groups; im Rust-Teil kein Kindprozess gefunden, Risiko beim Aufrufer: Exit-Code, Pipes und Zeitgrenze in pruefen.ps1.
- `20261022-skill-lernen-rust-testing` — **Skill-Lernen: rust-testing** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-testing.md` — Behavior-first mit Fixtures, Regression-Loop, I/O-Injection und Property-Tests; Stand: 21 Unit-Tests in sechs Dateien, keine Integrationstests; Lücken bei Exit-Codes, Eingabedatei und Cargo.lock-Fehlerpfad.
- `20261022-skill-lernen-code-metrics-tracker` — **Skill-Lernen: code-metrics-tracker** — `Wissen/Skill-Lernen/skill-code-metrics-tracker.md` — metrics.py: Komplexität/Größe/Duplikation messen, Churn×Komplexität Priorisierung; Trockenlauf.
- `20261022-skill-lernen-skills-daily` — **Skill-Lernen: skills:daily** — `Wissen/Skill-Lernen/skill-skills-daily.md` — Session-Orientierung: Backlog+Patch+Git→Karte+Top3; tägliche Routine, nur lesend; Trockenlauf.
- `20261022-skill-lernen-skills-date-sim` — **Skill-Lernen: skills:date-sim** — `Wissen/Skill-Lernen/skill-skills-date-sim.md` — Sokotan-Simulator: Gesprächstraining, ehrliches Scoring, Autopsie-Bericht mit verborgenem Bedürfnis; Trockenlauf.
- `20261022-skill-lernen-skills-feature-flow` — **Skill-Lernen: skills:feature-flow** — `Wissen/Skill-Lernen/skill-skills-feature-flow.md` — 9-Schritt Feature-Zyklus: Scope→Plan→Execute→Review→Commit→Doku; Checkpoints je Schritt; Trockenlauf.
- `20261022-skill-lernen-skills-feature-flow-superpowers` — **Skill-Lernen: skills:feature-flow-superpowers** — `Wissen/Skill-Lernen/skill-skills-feature-flow-superpowers.md` — feature-flow + superpowers-Skills je Schritt; TDD-first, verification-before-completion; Trockenlauf.
- `20261022-skill-lernen-skills-handoff` — **Skill-Lernen: skills:handoff** — `Wissen/Skill-Lernen/skill-skills-handoff.md` — Kontext-Übergabe via handoff.md; auto bei 80–95% + manuell /handoff; SessionStart-Hook liest es ein; Trockenlauf.
- `20261022-skill-lernen-skills-prompt-mbti` — **Skill-Lernen: skills:prompt-mbti** — `Wissen/Skill-Lernen/skill-skills-prompt-mbti.md` — Prompt-Gewohnheiten aus Logs zählen, MBTI-Typkarte, datenbasiertes Coaching; Trockenlauf.
- `20261022-skill-lernen-skills-shimmy-tone` — **Skill-Lernen: skills:shimmy-tone** — `Wissen/Skill-Lernen/skill-skills-shimmy-tone.md` — seungboshim Dev-Blog-Stil (Velog); baut auf korean-tone auf; Memes/Emojis erlaubt; Trockenlauf.
- `20261022-skill-lernen-skills-tailwind-design-system` — **Skill-Lernen: skills:tailwind-design-system** — `Wissen/Skill-Lernen/skill-skills-tailwind-design-system.md` — Tailwind+Next.js Design-System; Phase 0–6; semantische Token, Komponenten, Audit; Trockenlauf.
- `20261022-skill-lernen-skills-truman` — **Skill-Lernen: skills:truman** — `Wissen/Skill-Lernen/skill-skills-truman.md` — Arbeitstag als TV-Sendungsmanuskript; 3-Personen-Erzählung aus Git+Sessions; Cliffhanger-Mechanismus; Trockenlauf.
- `20261022-skill-lernen-skills-worklog` — **Skill-Lernen: skills:worklog** — `Wissen/Skill-Lernen/skill-skills-worklog.md` — Sitzungs-Abschluss-Dokumentation: Patchnote+Spec+Backlog in einem Schritt; Ausgang-Pendant zu daily; Trockenlauf.
- `20261022-skill-lernen-superpowers-brainstorming` — **Skill-Lernen: superpowers:brainstorming** — `Wissen/Skill-Lernen/skill-superpowers-brainstorming.md` — Anforderungs-Gespräch vor dem Bauen; Anti-Ziele, Designer-Check, Hard-Gate; Trockenlauf.
- `20261022-skill-lernen-superpowers-diagnosing` — **Skill-Lernen: superpowers:diagnosing-superpowers** — `Wissen/Skill-Lernen/skill-superpowers-diagnosing.md` — Sitzungsfehler diagnostizieren; 7 Analyse-Dimensionen parallel; path:line-Zitierpflicht; Trockenlauf.
- `20261022-skill-lernen-superpowers-parallel-agents` — **Skill-Lernen: superpowers:dispatching-parallel-agents** — `Wissen/Skill-Lernen/skill-superpowers-parallel-agents.md` — Unabhängige Probleme parallel an Subagenten delegieren; ein Agent pro Domäne; Trockenlauf.
- `20261022-skill-lernen-superpowers-executing-plans` — **Skill-Lernen: superpowers:executing-plans** — `Wissen/Skill-Lernen/skill-superpowers-executing-plans.md` — Plan inline ausführen; TDD je Schritt; Ledger für Rulings; finale Review; Trockenlauf.
- `20261022-skill-lernen-superpowers-finishing-branch` — **Skill-Lernen: superpowers:finishing-a-development-branch** — `Wissen/Skill-Lernen/skill-superpowers-finishing-a-development-branch.md` — Branch abschließen; Tests, Umgebung, Menü, Cleanup; Trockenlauf.
- `20261022-skill-lernen-superpowers-receiving-review` — **Skill-Lernen: superpowers:receiving-code-review** — `Wissen/Skill-Lernen/skill-superpowers-receiving-code-review.md` — Review-Feedback verifizieren; kein performatives Bestätigen; YAGNI-Check; Trockenlauf.
- `20261022-skill-lernen-superpowers-requesting-review` — **Skill-Lernen: superpowers:requesting-code-review** — `Wissen/Skill-Lernen/skill-superpowers-requesting-code-review.md` — Review-Subagent dispatchen; präziser Kontext; Critical/Important vor Weiterarbeit; Trockenlauf.
- `20261022-skill-lernen-superpowers-sdd` — **Skill-Lernen: superpowers:subagent-driven-development** — `Wissen/Skill-Lernen/skill-superpowers-subagent-driven-development.md` — Plan per Subagent je Task; Task-Review-Gate; Fix-Loop 5 Runden; Ledger; Trockenlauf.
- `20261022-skill-lernen-superpowers-systematic-debugging` — **Skill-Lernen: superpowers:systematic-debugging** — `Wissen/Skill-Lernen/skill-superpowers-systematic-debugging.md` — 4 Phasen; kein Fix ohne Ursache; ≥3 Fixes = Architekturproblem; Trockenlauf.
- `20261022-skill-lernen-superpowers-tdd` — **Skill-Lernen: superpowers:test-driven-development** — `Wissen/Skill-Lernen/skill-superpowers-test-driven-development.md` — Red-Green-Refactor; kein Code ohne fehlschlagenden Test; Code vor Test = Neustart; Trockenlauf.
- `20261022-skill-lernen-superpowers-git-worktrees` — **Skill-Lernen: superpowers:using-git-worktrees** — `Wissen/Skill-Lernen/skill-superpowers-using-git-worktrees.md` — Isolation erkennen; natives Tool bevorzugt; Submodul-Guard; Trockenlauf.
- `20261022-skill-lernen-superpowers-using-superpowers` — **Skill-Lernen: superpowers:using-superpowers** — `Wissen/Skill-Lernen/skill-superpowers-using-superpowers.md` — Meta-Skill; Skills VOR jeder Aktion; Prozess vor Implementierung; Trockenlauf.
- `20261022-skill-lernen-superpowers-verification` — **Skill-Lernen: superpowers:verification-before-completion** — `Wissen/Skill-Lernen/skill-superpowers-verification-before-completion.md` — 5-Schritt-Gate; kein Claim ohne Beleg; Agent-Berichte separat prüfen; Trockenlauf.
- `20261022-skill-lernen-superpowers-writing-plans` — **Skill-Lernen: superpowers:writing-plans** — `Wissen/Skill-Lernen/skill-superpowers-writing-plans.md` — File-Struktur zuerst; Step-Granularität; Self-Review; Übergabe SDD/executing-plans; Trockenlauf.
- `20261022-skill-lernen-superpowers-writing-skills` — **Skill-Lernen: superpowers:writing-skills** — `Wissen/Skill-Lernen/skill-superpowers-writing-skills.md` — TDD auf Prozessdoku; Baseline-Test zuerst; Form nach Fehlertyp; SDO; Trockenlauf.
- `20261022-skill-lernen-project-memory-recall` — **Skill-Lernen: project-memory:recall** — `Wissen/Skill-Lernen/skill-project-memory-recall.md` — Projekt-Memories abrufen; externe API; übersprungen.
- `20261022-skill-lernen-project-memory-remember` — **Skill-Lernen: project-memory:remember** — `Wissen/Skill-Lernen/skill-project-memory-remember.md` — Projekt-Memories speichern; externe API; übersprungen.
- `20261022-skill-lernen-project-memory` — **Skill-Lernen: project-memory:project-memory** — `Wissen/Skill-Lernen/skill-project-memory-project-memory.md` — lokale SQLite-DB für Projektfakten; kein API; Trockenlauf.
- `20261022-skill-lernen-api-drift-check-drift` — **Skill-Lernen: api-drift-detector:check-drift** — `Wissen/Skill-Lernen/skill-api-drift-detector-check-drift.md` — API-Drift in Codebase finden; lokales Scan-Tool; Trockenlauf.
- `20261022-skill-lernen-api-drift-detector` — **Skill-Lernen: api-drift-detector:api-drift-detector** — `Wissen/Skill-Lernen/skill-api-drift-detector-api-drift-detector.md` — vollständiges 4-Stufen-Rezept: Quellen→Vergleich→Compiler→Befund; TypeScript; Trockenlauf.
- `20261022-skill-lernen-rust-build` — **Skill-Lernen: rust-cli-skills:rust-build** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-build.md` — Prüfplan für den Rust-Teil des Handelsstacks (Workspace, Cargo.lock, Features, Windows-Linker); Trockenlauf ohne cargo.
- `20261022-skill-lernen-rust-cli-interface` — **Skill-Lernen: rust-cli-skills:rust-cli-interface** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-cli-interface.md` — Schnittstellenvertrag der Rust-CLIs: Vorrang Argumente/Umgebung/Konfiguration, stdout/stderr, JSON-Schema für Skripte; Trockenlauf.
- `20261022-skill-lernen-rust-cli-testing` — **Skill-Lernen: rust-cli-skills:rust-cli-testing** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-cli-testing.md` — Dreistufige Prüfgrenze (Parser, Prozess mit assert_cmd, Terminal); im Bestand fehlen Prozesstests; Trockenlauf.
- `20261022-skill-lernen-rust-concurrency` — **Skill-Lernen: rust-cli-skills:rust-concurrency** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-concurrency.md` — Im Rust-Teil des Handelsstacks keine Nebenläufigkeit gefunden (kein Thread, tokio oder rayon); Befund auf Schlüsselwörter beschränkt; Trockenlauf.
- `20261022-skill-lernen-rust-debugging` — **Skill-Lernen: rust-cli-skills:rust-debugging** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-debugging.md` — Eingrenzung in Schichten (Kompilierung, Start, Fachfehler, Absturz), Reproduktion mit kleinster Eingabe, Widerlegungsbeobachtung; Trockenlauf.
- `20261022-skill-lernen-rust-design` — **Skill-Lernen: rust-cli-skills:rust-design** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-design.md` — Prüffragen zu Crate-Grenzen (Risiko, Strategie, Signal, Plattform); nur Manifeste gelesen, Vorprüfung; Trockenlauf.
- `20261022-skill-lernen-rust-distribution` — **Skill-Lernen: rust-cli-skills:rust-distribution** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-distribution.md` — Auslieferung lokal auf dem Handelsrechner: Release-Build aus gesperrtem Lock, pruefen.ps1 als Gatter, Laufzeitbibliotheken als offene Annahme; Trockenlauf, ohne Build und ohne Veröffentlichung.
- `20261022-skill-lernen-rust-errors` — **Skill-Lernen: rust-cli-skills:rust-errors** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-errors.md` — Fehlerpfad im Rust-Teil: anyhow in quant-strategy, process::exit in quant-planes (überspringt Puffer-Leerung); Erfolg nur nach vollständiger Ausgabe; Trockenlauf.
- `20261022-skill-lernen-rust-filesystem` — **Skill-Lernen: rust-cli-skills:rust-filesystem** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-filesystem.md` — Vier Dateizugriffe im Rust-Teil: direkte Schreibvorgänge ohne Temp-Datei, relativer Pfad zu ranked_book.json, expect bei Cargo.lock; Trockenlauf.
- `20261022-skill-lernen-rust-idiomatic` — **Skill-Lernen: rust-cli-skills:rust-idiomatic** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-idiomatic.md` — Von vier Textfunden nur die expect-Stellen in quant-planes als Vertragsproblem; Clones bleiben; Trockenlauf.
- `20261022-skill-lernen-rust-implement` — **Skill-Lernen: rust-cli-skills:rust-implement** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-implement.md` — Schrittfolge für die expect-Änderung in quant-planes: erst reproduzieren, dann Result, dann Prüfung mit --locked; Trockenlauf.
- `20261022-skill-lernen-rust-io` — **Skill-Lernen: rust-cli-skills:rust-io** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-io.md` — Ausgabe über println!/eprintln! in drei Programmen; offen ist, ob ein früh geschlossener Pipe-Partner (| head) einen Panic auslöst; Trockenlauf.
- `20261022-skill-lernen-rust-memory` — **Skill-Lernen: rust-cli-skills:rust-memory** — `Wissen/Skill-Lernen/skill-rust-cli-skills-rust-memory.md` — Wachstumsstellen: Matrizen in cross_panel.rs, Datenliste in quant-strategy; Vorschlag einer Obergrenze aus dem Universum statt Umbau ohne Messung; Trockenlauf.
- `20261022-skill-lernen-maxhirn-absturz` — **Skill-Lernen: MaxHirn:absturz-recovery** — `Wissen/Skill-Lernen/skill-maxhirn-absturz-recovery.md` — Routine passt nur teilweise: Werkstatt ist nicht versioniert, der Zwischenstand-Zweig ist die einzige Sicherung; Trockenlauf.
- `20261022-skill-lernen-maxhirn-archiv` — **Skill-Lernen: MaxHirn:archiv** — `Wissen/Skill-Lernen/skill-maxhirn-archiv.md` — Suche nach skill-lernen liefert keine Treffer: das Archiv-Index deckt Wissen/ nicht ab; Lernnotizen sind nur über INDEX.md oder Textsuche auffindbar; Trockenlauf.
- `20261022-skill-lernen-maxhirn-auftrag` — **Skill-Lernen: MaxHirn:auftrag** — `Wissen/Skill-Lernen/skill-maxhirn-auftrag.md` — "mach weiter" im Lern-Ablauf heißt: nächster Skill derselben Gruppe, Gruppenwechsel nur mit Zeile; Trockenlauf.
- `20261022-skill-lernen-maxhirn-belege` — **Skill-Lernen: MaxHirn:belege** — `Wissen/Skill-Lernen/skill-maxhirn-belege.md` — Fortschrittsdatei ist kein Beleg (Protokoll, nicht versioniert, ohne Aussteller); Chronik ja, Nachweis nein; Trockenlauf.
- `20261022-skill-lernen-maxhirn-docker` — **Skill-Lernen: MaxHirn:docker-cascade-repair** — `Wissen/Skill-Lernen/skill-maxhirn-docker-cascade-repair.md` — Erkennung eines Docker-Hangs im Lern-Ablauf: Verbindungsfehler, fehlende Notizen, Prozesszahl über 100 vor jedem Lauf messen; Trockenlauf.
- `20261022-skill-lernen-context-compactor-compact-plan` — **Skill-Lernen: context-compactor:compact-plan** — `Wissen/Skill-Lernen/skill-context-compactor-compact-plan.md` — Shortcut für /compact-Befehl; Skill-Output enthielt Prompt-Injection (ignoriert); Trockenlauf.
- `20261022-skill-lernen-context-compactor` — **Skill-Lernen: context-compactor:context-compactor** — `Wissen/Skill-Lernen/skill-context-compactor-context-compactor.md` — Rezept: weniger lesen, Zustandszusammenfassung schreiben, /compact-Hinweis, Handoff nach NOTES.md; Trockenlauf.
- `20261022-skill-lernen-crypto-bonuses` — **Skill-Lernen: crypto-research-market-insights:bonuses** — `Wissen/Skill-Lernen/skill-crypto-research-bonuses.md` — Übersprungen: externe Krypto-API.
- `20261022-skill-lernen-crypto-chart` — **Skill-Lernen: crypto-research-market-insights:chart** — `Wissen/Skill-Lernen/skill-crypto-research-chart.md` — Übersprungen: externe Krypto-API.
- `20261022-skill-lernen-crypto-coin` — **Skill-Lernen: crypto-research-market-insights:coin** — `Wissen/Skill-Lernen/skill-crypto-research-coin.md` — Übersprungen: externe Krypto-API.
- `20261022-skill-lernen-crypto-compare` — **Skill-Lernen: crypto-research-market-insights:compare** — `Wissen/Skill-Lernen/skill-crypto-research-compare.md` — Übersprungen: externe Krypto-API.
- `20261022-skill-lernen-crypto-exchange` — **Skill-Lernen: crypto-research-market-insights:exchange** — `Wissen/Skill-Lernen/skill-crypto-research-exchange.md` — Übersprungen: externe Krypto-API.
- `20261022-skill-lernen-crypto-learn` — **Skill-Lernen: crypto-research-market-insights:learn** — `Wissen/Skill-Lernen/skill-crypto-research-learn.md` — Übersprungen: externe Krypto-API.
- `20261022-skill-lernen-crypto-market` — **Skill-Lernen: crypto-research-market-insights:market** — `Wissen/Skill-Lernen/skill-crypto-research-market.md` — Übersprungen: externe Krypto-API.
- `20261022-skill-lernen-crypto-news` — **Skill-Lernen: crypto-research-market-insights:news** — `Wissen/Skill-Lernen/skill-crypto-research-news.md` — Übersprungen: externe Krypto-API.
- `20261022-skill-lernen-crypto-research-meta` — **Skill-Lernen: crypto-research-market-insights:crypto-research** — `Wissen/Skill-Lernen/skill-crypto-research-meta.md` — Meta-Skill: 9 Workflows (Projekt, Markt, Chart, News, Vergleich, Bildung, Börse, Bonus); externe Daten nötig für Echtzeitmarkt; Trockenlauf.
- `20261022-skill-lernen-crypto-spot-futures` — **Skill-Lernen: crypto-spot-futures-analyzer:crypto-spot-futures-analysis** — `Wissen/Skill-Lernen/skill-crypto-spot-futures-analyzer.md` — 5-Modus-Analyseassistent (Screenshot/Trade/Coin/Futures/Rechner); Datenhierarchie; kein Kaufbefehl; Trockenlauf.
- `20261022-skill-lernen-daloopa-gruppe` — **Skill-Lernen: daloopa:* (21 Skills)** — `Wissen/Skill-Lernen/skill-daloopa-gruppe.md` — Übersprungen: Daloopa-Finanzanalyse-SaaS (externe API).
- `20261022-skill-lernen-datarobot-gruppe` — **Skill-Lernen: datarobot-agent-skills:* (14 Skills)** — `Wissen/Skill-Lernen/skill-datarobot-gruppe.md` — Übersprungen: DataRobot-ML-Plattform (externe API).
- `20261022-skill-lernen-data-analyze` — **Skill-Lernen: data:analyze** — `Wissen/Skill-Lernen/skill-data-analyze.md` — 3 Komplexitätsstufen (Quick/Full/Formal); 6-Schritt-Workflow mit Validierung; MCP-Warehouse oder User-Daten; Trockenlauf.
- `20261022-skill-lernen-data-build-dashboard` — **Skill-Lernen: data:build-dashboard** — `Wissen/Skill-Lernen/skill-data-build-dashboard.md` — selbständige HTML-Dashboards mit Chart.js; KPI+Charts+Tabelle; Performance-Grenzen 1k/10k/100k; Trockenlauf.
- `20261022-skill-lernen-data-create-viz` — **Skill-Lernen: data:create-viz** — `Wissen/Skill-Lernen/skill-data-create-viz.md` — Python-Charts (matplotlib/seaborn/plotly); Charttyp-Empfehlung; Insight-Titel-Regel; Trockenlauf.
- `20261022-skill-lernen-data-data-context-extractor` — **Skill-Lernen: data:data-context-extractor** — `Wissen/Skill-Lernen/skill-data-data-context-extractor.md` — Meta-Skill: firmenspezifischen Datenwissen destillieren; Bootstrap- und Iterations-Modus; 5 Kernfragen; Trockenlauf.
- `20261022-skill-lernen-data-data-visualization` — **Skill-Lernen: data:data-visualization** — `Wissen/Skill-Lernen/skill-data-data-visualization.md` — Chartauswahl-Referenz; Python-Muster (matplotlib/seaborn/plotly); 3 Kernregeln; Accessibility-Checkliste; Trockenlauf.
- `20261022-skill-lernen-data-explore-data` — **Skill-Lernen: data:explore-data** — `Wissen/Skill-Lernen/skill-data-explore-data.md` — 7-Schritt-Datenprofil; Qualitäts-Ampel; Red-Flag-Liste; Muster-Erkennung; Trockenlauf.
- `20261022-skill-lernen-data-sql-queries` — **Skill-Lernen: data:sql-queries** — `Wissen/Skill-Lernen/skill-data-sql-queries.md` — SQL-Dialekte (PG/Snowflake/BQ/Redshift/Databricks); Dedup/Funnel/Cohort-Muster; CTE-Regel; Trockenlauf.
- `20261022-skill-lernen-data-statistical-analysis` — **Skill-Lernen: data:statistical-analysis** — `Wissen/Skill-Lernen/skill-data-statistical-analysis.md` — Deskriptiv (Mean+Median immer zusammen); Ausreißer IQR/Z; Hypothesentests; 5 Fallstricke; Trockenlauf.
- `20261022-skill-lernen-data-validate-data` — **Skill-Lernen: data:validate-data** — `Wissen/Skill-Lernen/skill-data-validate-data.md` — Analyse-QA vor Stakeholder-Weitergabe; 7 Fallstricke (Join-Explosion, Survivorship, Avg-of-Avg…); Konfidenz-Stufen; Trockenlauf.
- `20261022-skill-lernen-data-write-query` — **Skill-Lernen: data:write-query** — `Wissen/Skill-Lernen/skill-data-write-query.md` — SQL aus Freitext; dialektspezifisch; CTE-First; Performance-Regeln; Trockenlauf.
- `20261022-skill-lernen-dataviz` — **Skill-Lernen: dataviz** — `Wissen/Skill-Lernen/skill-dataviz.md` — Design-agnostische Viz-Methodik; Farbvalidierung per Skript (CVD Delta E ≥ 8); 7 Schritte; Anti-Pattern-Katalog; Trockenlauf.
- `20261022-skill-lernen-artifact-design` — **Skill-Lernen: artifact-design** — `Wissen/Skill-Lernen/skill-artifact-design.md` — Seitenvertrag, Designprozess, Fundamentals; Pflichtlektüre vor jedem Artifact-Publish; Trockenlauf.
- `20261022-skill-lernen-artifact-diagramming` — **Skill-Lernen: artifact-diagramming** — `Wissen/Skill-Lernen/skill-artifact-diagramming.md` — Wann Diagramm nötig; Mechanismus zeigen nicht benennen; Inline-SVG-Mechanik; Trockenlauf.
- `20261022-skill-lernen-artifact-capabilities` — **Skill-Lernen: artifact-capabilities** — `Wissen/Skill-Lernen/skill-artifact-capabilities.md` — Runtime-Capabilities (db/room/sample/user/artifact/assets/mcp); Deklaration; Zustandsfragen; Trockenlauf.
- `20261022-skill-lernen-update-config` — **Skill-Lernen: update-config** — `Wissen/Skill-Lernen/skill-update-config.md` — settings.json bearbeiten, Hooks anlegen/debuggen, Berechtigungen, Env-Vars; Trockenlauf.
- `20261022-skill-lernen-videoanalyse` — **Skill-Lernen: MaxHirn:videoanalyse** — `Wissen/Skill-Lernen/skill-maxhirn-videoanalyse.md` — YouTube-Transkript ziehen, Fallen, Auswerteschema; Trockenlauf.
- `20261022-skill-lernen-wochenrueckblick` — **Skill-Lernen: MaxHirn:wochenrueckblick** — `Wissen/Skill-Lernen/skill-maxhirn-wochenrueckblick.md` — wöchentliche Vault-Pflege, 5 Schritte; Trockenlauf.
- `20261022-skill-lernen-skill` — **Skill-Lernen: MaxHirn:skill** — `Wissen/Skill-Lernen/skill-maxhirn-skill.md` — wann Skill anlegen, Hausformat, drei Ablageorte; Trockenlauf.
- `20261022-skill-lernen-scanner-papier` — **Skill-Lernen: scanner-papier** — `Wissen/Skill-Lernen/skill-scanner-papier.md` — Scanner-Varianten im Papiermodus und ihre Fallen prüfen; Handelsbereich ohne Bezug zum Lern-Ablauf, keine Testdaten ausgewertet.
- `20261022-skill-lernen-wissen-beitragen` — **Skill-Lernen: wissen-beitragen** — `Wissen/Skill-Lernen/skill-wissen-beitragen.md` — Ablage zwischen gbrain/Wissen/Wiki, gbrain-Aufruf und CRLF-Pflichten; Lernnotizen nach Wissen/Skill-Lernen, Fallen ins Wiki, offene Punkte nach TASKS.md; Hauptzweig maks_master, Trockenlauf ohne Schreibvorgang.
- `20261022-skill-lernen-simplify` — **Skill-Lernen: simplify** — `Wissen/Skill-Lernen/skill-simplify.md` — Code-Qualität per 4 parallele Agents (Reuse/Simplification/Efficiency/Altitude); Trockenlauf.
- `20261022-skill-lernen-fewer-permission-prompts` — **Skill-Lernen: fewer-permission-prompts** — `Wissen/Skill-Lernen/skill-fewer-permission-prompts.md` — Transkripte scannen, Read-only-Allowlist aufbauen; Trockenlauf.
- `20261022-skill-lernen-loop` — **Skill-Lernen: loop** — `Wissen/Skill-Lernen/skill-loop.md` — wiederkehrende Prompts mit Cron oder dynamisch (ScheduleWakeup+Monitor); Trockenlauf.
- `20261022-skill-lernen-run` — **Skill-Lernen: run** — `Wissen/Skill-Lernen/skill-run.md` — App starten und interagieren, Projekt-Skill zuerst prüfen; Trockenlauf.
- `20261022-skill-lernen-plugin-authoring` — **Skill-Lernen: plugin-authoring** — `Wissen/Skill-Lernen/skill-plugin-authoring.md` — Claude Code Mods erstellen (Pane, Band, Hook, Status-Line); Trockenlauf.
- `20261022-skill-lernen-init` — **Skill-Lernen: init** — `Wissen/Skill-Lernen/skill-init.md` — CLAUDE.md für neues Repo erstellen (Befehle, Architektur, Quellen); Trockenlauf.
- `20261022-skill-lernen-maxhirn-dokument` — **Skill-Lernen: MaxHirn:dokument** — `Wissen/Skill-Lernen/skill-maxhirn-dokument.md` — Erschließungs-Skill setzt Papierdokumente voraus; für Lernnotizen entfallen Benennung und Ablage; Trockenlauf.
- `20261022-skill-lernen-maxhirn-frist` — **Skill-Lernen: MaxHirn:frist** — `Wissen/Skill-Lernen/skill-maxhirn-frist.md` — Keine echte Frist in den Lernnotizen (Treffer nur Vorlagenfelder); Eintrag würde in Wissen/Fristen.md als offenes Kästchen landen; Trockenlauf.
- `20261022-skill-lernen-maxhirn-geld` — **Skill-Lernen: MaxHirn:geld** — `Wissen/Skill-Lernen/skill-maxhirn-geld.md` — Anstehende Zahlungen aus Fristen.md (21.08. 3.259,19 € noch offen, 10.09. und 10.12. je 877 €); Girokonto fehlt, Mittel nicht abgefragt; Trockenlauf.
- `20261022-skill-lernen-maxhirn-grill-me` — **Skill-Lernen: MaxHirn:grill-me** — `Wissen/Skill-Lernen/skill-maxhirn-grill-me.md` — Schwächste Entscheidung im Lern-Ablauf: die Kandidatenliste aus der Sitzung, nicht reproduzierbar; keine Interviewfragen gestellt; Trockenlauf.
- `20261022-skill-lernen-maxhirn-marktbriefing` — **Skill-Lernen: MaxHirn:marktbriefing** — `Wissen/Skill-Lernen/skill-maxhirn-marktbriefing.md` — Quellen: traderhub-Boards macro, movers, rotation; Pflichtprüfung meta/stale; Lern-Ablauf hat keinen Marktbezug; Trockenlauf.
- `20261022-skill-lernen-maxhirn-notiz` — **Skill-Lernen: MaxHirn:notiz** — `Wissen/Skill-Lernen/skill-maxhirn-notiz.md` — 126 Lernnotizen haben ein eigenes Frontmatter-Schema (name/description/metadata) statt id/title/tags; ohne Elternnotiz nicht verlinkt; Trockenlauf.
- `20261022-skill-lernen-maxhirn-posteingang` — **Skill-Lernen: MaxHirn:posteingang** — `Wissen/Skill-Lernen/skill-maxhirn-posteingang.md` — 288 Dateien im Posteingang (O:\Archiv); Testlauf vorgesehen, Programmpakete nicht blind zerlegen; Trockenlauf.
- `20261022-skill-lernen-maxhirn-rueckschau` — **Skill-Lernen: MaxHirn:rueckschau** — `Wissen/Skill-Lernen/skill-maxhirn-rueckschau.md` — Auswertung über Sitzungen zählt parallele Läufe mehrfach; Themenliste enthält skill-lernen vermutlich nicht; Trockenlauf.
- `20261022-skill-lernen-maxhirn-schaden` — **Skill-Lernen: MaxHirn:schaden** — `Wissen/Skill-Lernen/skill-maxhirn-schaden.md` — Füllbyte-Prüfung über die Lernnotizen: keine leeren, keine 0xFF-, keine fehlerhaften Dateien; Trockenlauf.
- `20261022-skill-lernen-maxhirn-sichern` — **Skill-Lernen: MaxHirn:sichern** — `Wissen/Skill-Lernen/skill-maxhirn-sichern.md` — 69 Lernnotizen ungetrackt; Fortschritt in Werkstatt/ durch .gitignore nicht gesichert; Trockenlauf, kein Commit.
- `20261022-skill-lernen-maxhirn-system` — **Skill-Lernen: MaxHirn:system** — `Wissen/Skill-Lernen/skill-maxhirn-system.md` — Befunde, die den Lauf treffen könnten (Stromverlust, Plattenfehler, Dienstabstürze); gezielte Ereignis-Abfragen beschrieben, nicht ausgeführt; Trockenlauf.
- `20261022-skill-lernen-maxhirn-tagesbriefing` — **Skill-Lernen: MaxHirn:tagesbriefing** — `Wissen/Skill-Lernen/skill-maxhirn-tagesbriefing.md` — Briefing für den Lern-Ablauf: nächste offene Gruppe, offene Fristenzahlung, ungesicherte Fortschrittsdatei; Kalender nicht abgefragt; Trockenlauf.
- `20261022-skill-lernen-maxhirn-umzug` — **Skill-Lernen: MaxHirn:umzug** — `Wissen/Skill-Lernen/skill-maxhirn-umzug.md` — 144 Index-Zeilen und 146 Fortschrittszeilen verweisen auf den Ordner; Suche in Skills und Notizen läuft noch im Hintergrund; Trockenlauf.
- `20261022-skill-lernen-maxhirn-verbindungen` — **Skill-Lernen: MaxHirn:verbindungen** — `Wissen/Skill-Lernen/skill-maxhirn-verbindungen.md` — Der Lern-Ablauf braucht keinen MCP-Server; Ausfälle träfen nur aufgerufene Skills mit Außenbezug; Trockenlauf.
- `20261022-skill-lernen-maxhirn-vergleich` — **Skill-Lernen: MaxHirn:vergleich** — `Wissen/Skill-Lernen/skill-maxhirn-vergleich.md` — Im Fortschritt 6 doppelte Skill-Namen, im Index 4 doppelte IDs; Protokoll-Doppelungen sind kein Dateivergleich-Fall; Trockenlauf, nichts gelöscht.
- `20261022-skill-lernen-maxhirn-videoanalyse` — **Skill-Lernen: MaxHirn:videoanalyse** — `Wissen/Skill-Lernen/skill-maxhirn-videoanalyse.md` — Für Skill-Dokumentation gibt es keine Video-Quelle; Auswertungsschema passt nur für Markt-Videos; Trockenlauf, kein Link aufgerufen.
- `20261022-skill-lernen-maxhirn-wochenrueckblick` — **Skill-Lernen: MaxHirn:wochenrueckblick** — `Wissen/Skill-Lernen/skill-maxhirn-wochenrueckblick.md` — 145 Lernnotizen in dieser Woche geändert, 177 Fortschrittszeilen; Entscheidungen: Kandidatenliste, ungesicherte Fortschrittsdatei, Index-Doppelungen; Trockenlauf.
- `20261022-skill-lernen-security-review` — **Skill-Lernen: security-review** — `Wissen/Skill-Lernen/skill-security-review.md` — Branch-Review auf Sicherheitslücken (Injection, Auth, Crypto, RCE); 3-Phasen, Subagent-Filter, Konfidenz ≥80%; Skill lief als echtes Review; Trockenlauf.
- `20261022-skill-lernen-claude-api` — **Skill-Lernen: claude-api** — `Wissen/Skill-Lernen/skill-claude-api.md` — Anthropic SDK; Modell-IDs, Thinking-Konfiguration, Tool Use, Streaming, Caching; API-Drift-Warntabelle; Trockenlauf.
- `20261022-skill-lernen-workflow-authoring` — **Skill-Lernen: workflow-authoring** — `Wissen/Skill-Lernen/skill-workflow-authoring.md` — Workflow-Skript-API (pipeline/parallel/agent/phase/log); Qualitätsmuster (adversarial-verify, judge-panel, loop-until-dry); Resume; Trockenlauf.
- `20261022-skill-lernen-schedule` — **Skill-Lernen: schedule** — `Wissen/Skill-Lernen/skill-schedule.md` — Cloud-Routinen (CCR) per RemoteTrigger; Cron, Environments, MCP-Konnektoren; min. 1h Intervall; Trockenlauf.
- `20261022-skill-lernen-keybindings-help` — **Skill-Lernen: keybindings-help** — `Wissen/Skill-Lernen/skill-keybindings-help.md` — ~/.claude/keybindings.json; Kontexte, Aktionen, Chords, Unbind mit null; Trockenlauf.
- `20261022-skill-lernen-github-cli-health-check` — **Skill-Lernen: github-cli-health-check** — `Wissen/Skill-Lernen/skill-github-cli-health-check.md` — GitHub-CLI-Status (auth, repos, rate-limit); drei Ausführungspfade; Cowork-VM-Proxy blockiert api.github.com; Trockenlauf.
