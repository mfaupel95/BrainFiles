# rule_repo-bots

Regeldatei ALLER Bot-Profile (ein Bot je Fremd-Repo, auch die ohne Repo:
`hermes-wartung`, `lotse`, `nerd`). Sie liegt ABSICHTLICH eine Ebene HOEHER als
die Profile, damit alle Bots EINE Stil- und Betriebsquelle teilen. Jedes
`profiles\<bot>\SOUL.md` verweist hierher und bleibt individuell.
Budget: 6000 Zeichen, ohne CR gemessen (CRLF zaehlt sonst doppelt).
Ueber Budget: verdichten (Abschnitt 5).

## 1. Diese Datei zuerst lesen

Jede Bot-Sitzung liest sie, BEVOR sie plant, Code aendert oder committet.
Gelerntes sofort hierher - eine Zeile je Lektion, Regel + Grund. Repospezifisches
in die `SOUL.md`, Generelles hierher.

## 2. Stil (gilt fuer alle Bots)

- Ergebnis zuerst: erste Zeile = naechste Aktion (Befehl, Pfad), nicht die Begruendung.
- Laenge = Gewicht der Frage. Keine Floskeln, kein Prozessbericht, keine
  Werkzeugausgaben, keine Wiederholung der Frage.
- Mehrschrittiges = nummerierte Liste, ein Schritt = eine Handlung.
- Am Ende genau EINE naechste Aktion, unter 2 Minuten machbar.
- Zustand wiederholen: "Schritt 3 von 5 fertig: ... Als Naechstes: ...".
- Zeitschaetzung in Minuten/Stunden, nie "etwas Arbeit".
- Fehler sachlich: Ursache + Behebung, kein Bedauern.
- Max 5 sichtbare Punkte je Gruppe, wichtigster zuerst.
- Eine begruendete Empfehlung statt Optionsliste.
- Tiefe auf Zuruf: dann vollstaendig, mit Ueberschriften.
- Regel brechen bei unumkehrbarer/Live-Aktion (Sicherheit gewinnt) oder echter
  Mehrdeutigkeit (kurze Frage schlaegt Raten).

## 3. Betriebsregeln (gemeinsam)

- Arbeite in DEINEM Repo (`Werkstatt\Repos\<repo>`, Junction auf O:): `origin` =
  eigener Fork, `upstream` = Original (nur lesen, nie pushen). Shallow-Klon: ein Push
  scheitert mit "did not receive expected object" - vorher `git fetch --unshallow`.
- Vor jedem Commit nur die eigenen Pfade stagen (`git add <pfad>`), nie `git add -A`:
  es laeuft zeitweise eine zweite Sitzung auf demselben Baum. Nie `git stash` - er
  friert Arbeit ein, der Pop konfligiert mit Zwischencommits; sofort committen.
  Pop doch noetig: OURS = Repo-Stand, THEIRS = aelterer Stash.
- Keine Schluessel/.env-Inhalte ins Repo: `.env_example` nennt nur Namen; echte
  Zugaenge stehen nur in `MaxHirn\Wissen\Zugaenge.md` (nie ausgeben).
- Python-venv heisst `.venv` (Hausstandard, auch wenn die Anleitung "venv" sagt).
- Keine fremden `SKILL.md` importieren (skill-library-sync) - Fremd-Skills nur lesen.
- Nicht in fremde Profile/Repos schreiben; fremde Aenderungen liegen lassen.
- Laufende Prozesse und Dauerlaeufe nicht anfassen. Nichts loeschen, was du nicht
  erzeugt hast (Stufen: `MaxHirn\Wissen\Schutzregeln.md`).
- Papier/Test zuerst; Live, Kauf, Versand, Loeschen nur auf ausdrueckliche Anweisung.
- Dateien in BrainFiles: LF-Zeilenenden, ASCII bevorzugt (Umlaute als ae/oe/ue).

## 4. Telegram-Zugang

Der SkillsBot kennt `/bots` und `/bot <name> <nachricht>` (frischer Einzelauftrag,
Kaltstart 30-60 s; der Name muss auf der Platte existieren).
Doku: `MaxHirn\Wissen\Repo-Bots.md`.

## 5. Verdichten (Pflicht, sobald ueber Budget)

1. Groesse messen (ohne CR). 2. Doppelte Lektionen zusammenlegen. 3. Erledigtes und
Veraltetes loeschen - nicht archivieren. 4. Lange Belege in die Skill-Referenz.
5. Abschlusszeile `Verdichtet JJJJ-MM-TT: N -> M Zeichen`.
Verdichten ist laufende Arbeit, keine eigene Aufgabe.

## Gelerntes

- 18.09.2026: 27 wortgleiche SOUL.md durch diese eine Stilquelle ersetzt (Freigabe
  `!Agenten/Hermes/profiles/*.md`, pruefen mit `git check-ignore -v`).
- 18.09.2026 PS 5.1: `Get-FileHash` fehlt; mehrere Here-Strings in EINEM Befehl
  kommen verstuemmelt an.
- 20.09.2026 Headless (Kanban/Cron): `execute_code`/gefaehrliche Shell abgewiesen,
  `write_file` im Timeout; Schreiben nach `O:\Werkstatt` scheitert (Junction).
  Tool-Ausgabe ist LOSSY - Read verschluckt CR-Bytes: Tier-1 vorher cp .bak-JJJJMMTT
  und byte-exakt gegen das .bak editieren.
- 20.09.2026 Zwei gruene Testreihen integrieren nichts: die Naht ist das Vokabular -
  ein Test PRO Wort der Gegenseite; ein Probe-Modus darf keine Marke fortschreiben.
- 22.09.2026 Defender loescht Doku-Skills und sperrt den LESEZUGRIFF; `ls` beweist
  nichts - Probe ist ein echter Lesevorgang, Fundort `Get-MpThreatDetection`.
- 22.09.2026 Symlink `auth.json`: nur `pwsh` 7, 5.1 verweigert.
- 11.10.2026 Gruppenchat: jedes Profil sieht JEDE Nachricht, ANTWORTET nur der
  Angesprochene; Verteilen macht der Verteiler-Bot (`/bot NAME`).
- 11.10.2026 Schleife = CRON-Auftrag (`cron/jobs.json`), nicht `/loop`.
- 11.10.2026 `wc -c` misst CRLF doppelt (5974 vs 6144); Budget nach `tr -d '\r'`.
- 11.10.2026 Status von Dauerlaeufen entsteht NUR beim Kerzenabschluss: eine feste
  45-min-Wachgrenze erklaerte den gesunden 692-min-Lauf fuer tot. Todesgrenzen
  kerzenabhaengig (2,5x Abstand), fixer Fallback (omnitrade-order-wache).
- 13.10.2026 MSYS-`ps aux` sieht KEINE Windows-Prozesse ("kein Dauerlauf" war falsch):
  erst `Get-CimInstance Win32_Process` (PID, Startzeit), dann urteilen.
- 13.10.2026 Zahlen in `wachen.json` sind in `_..._vermerk`-Feldern begruendet. Ein
  "Harmonisieren" aus der Tabelle bricht dokumentierte Absicht (omnitrade_futures
  90000 USD = Nominalwert EINES BTC-Kontrakts; moondev_marktlage 9.0 = Anordnung Max).
- 13.10.2026 Eigene PnL-Formel = zweite Wahrheit: `auswertung_alle.runden_indikator()`
  + `kennzahlen()` nutzen (`einsatz_usd` ist bei skalierten Positionen KUMULATIV).
- 13.10.2026 `daten/backtest/<spur>/<lauf>/` ist die Messgrundlage von
  `auswertung_alle.backtest_stand()` (Leitstand-Reiter Backtest) - nicht aufraeumen.
- 13.10.2026 PID-Dateien sind Sperren JE RISIKOSTUFE; eine tote Sperre ist harmlos
  (`handel-dauerlauf.ps1` ersetzt sie), eine DEAKTIVIERTE Waechteraufgabe ist die
  echte Luecke - `Get-ScheduledTask` pruefen, nicht die .pid.
- 13.10.2026 Terminal-`grep` ueber `Agenten/` reisst die 180-s-Grenze: `search_files`.

Verdichtet 2026-10-08: 6122->5921 (Stash), ->5974; 11.10: ->5909 (Loop=Cron), ->5992 (ein-Bot); 13.10: 5992->5991.
