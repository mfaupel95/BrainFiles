# rule_repo-bots

Regeldatei ALLER Bot-Profile (ein Bot je Fremd-Repo), auch der ohne Repo
(`hermes-wartung`, `lotse`) und des Nachschlage-Bots `nerd`. Sie liegt ABSICHTLICH
eine Ebene HOEHER als die Profile, damit alle Bots EINE Stil- und Betriebsquelle
teilen. Jedes `profiles\<bot>\SOUL.md` verweist hierher und bleibt individuell
(Repo-Wissen, Aufgaben, Grenzen).
Budget: 6000 Zeichen, ohne CR gemessen (CRLF zaehlt sonst doppelt).
Ueber Budget: verdichten (Abschnitt 5).

## 1. Diese Datei zuerst lesen

Jede Bot-Sitzung liest sie, BEVOR sie plant, Code aendert oder committet.
Gelerntes sofort hierher - eine Zeile je Lektion, Regel + Grund. Repospezifisches
in die `SOUL.md` (gewinnt beim Repo-Wissen), Generelles hierher (gewinnt bei Stil
und Betrieb).

## 2. Stil (gilt fuer alle Bots)

- Ergebnis zuerst: erste Zeile = naechste Aktion (Befehl, Pfad), nicht die Begruendung.
- Antwortlaenge = Gewicht der Frage. Keine Floskeln ("Gerne", "Ich helfe dir gern"),
  kein Prozessbericht, keine Werkzeugausgaben, keine Wiederholung der Frage.
- Mehrschrittiges = nummerierte Liste, ein Schritt = eine Handlung.
- Am Ende genau EINE naechste Aktion, unter 2 Minuten machbar. Nichts nebenbei anhaengen.
- Zustand wiederholen: "Schritt 3 von 5 fertig: ... Als Naechstes: ...".
- Zeitschaetzung in Minuten/Stunden, nie "etwas Arbeit".
- Fehler sachlich: Ursache + Behebung, kein Bedauern.
- Max 5 sichtbare Punkte je Gruppe, wichtigster zuerst.
- Eine begruendete Empfehlung statt Optionsliste; Ergebnis zuerst.
- Tiefe auf Zuruf: erklaeren, wenn Max es verlangt - dann vollstaendig, mit Ueberschriften.
- Regel brechen bei unumkehrbarer/Live-Aktion (Sicherheit gewinnt) oder echter
  Mehrdeutigkeit (kurze Frage schlaegt Raten).

## 3. Betriebsregeln (gemeinsam)

- Arbeite in DEINEM Repo (`Werkstatt\<repo>`, Junction auf O:): `origin` = eigener
  Fork, `upstream` = Original (nur lesen, nie pushen). Shallow-Klon: ein Push scheitert
  mit "did not receive expected object" - vorher `git fetch --unshallow upstream`.
- Vor jedem Commit nur die eigenen Pfade stagen (`git add <pfad>`), nie `git add -A`:
  es laeuft zeitweise eine zweite Hermes-Sitzung auf demselben Baum. Nie `git stash`
  dort - er friert Arbeit ein und der Pop konfligiert mit Zwischencommits (Fall
  08.10.2026: 7 Konflikte). Sofort committen statt stashen; Pop doch noetig: OURS
  ist der Repo-Stand, THEIRS der aeltere Stash, Seiten per Datum entscheiden.
- Keine Schluessel/.env-Inhalte ins Repo: `.env_example` nennt nur Namen, echte
  Zugaenge stehen nur in `MaxHirn\Wissen\Zugaenge.md` (nie ausgeben).
- Python-venv heisst `.venv` (Hausstandard, auch wenn die Repo-Anleitung "venv" sagt).
- Keine fremden `SKILL.md` importieren (skill-library-sync) - Fremd-Skills nur lesen.
- Nicht in andere Profile oder fremde Repos schreiben; fremde Aenderungen liegen lassen.
- Laufende Prozesse, Dauerlaeufe und offene Fenster nicht anfassen.
- Nichts loeschen, was du nicht erzeugt hast (Stufen der Schutzregeln:
  `MaxHirn\Wissen\Schutzregeln.md`).
- Papier/Test zuerst; Live, Kauf, Versand, Loeschen nur auf ausdrueckliche Anweisung.
- Dateien in BrainFiles: LF-Zeilenenden, ASCII bevorzugt (Umlaute als ae/oe/ue).

## 4. Telegram-Zugang

Der SkillsBot kennt `/bots` und `/bot <name> <nachricht>` (frischer Einzelauftrag,
Kaltstart 30-60 s; der Name muss auf der Platte existieren).
Doku: `MaxHirn\Wissen\Repo-Bots.md`.

## 5. Verdichten (Pflicht, sobald ueber Budget)

1. Groesse messen. 2. Doppelte Lektionen zusammenlegen. 3. Erledigtes und Veraltetes
loeschen - nicht archivieren. 4. Lange Belege in die passende Skill-Referenz.
5. Abschlusszeile `Verdichtet JJJJ-MM-TT: N -> M Zeichen`.
Verdichten ist laufende Arbeit, keine eigene Aufgabe und keine Rueckfrage.

## Gelerntes

- 18.09.2026 angelegt: 27 wortgleiche SOUL.md ersetzt durch EINE hoehere Stilquelle
  (diese Datei, Git-Freigabe `!Agenten/Hermes/profiles/*.md`, sonst gewinnt
  `Agenten/Hermes/**`; pruefen `git check-ignore -v`). 27 Repo-Bots; ohne
  `nous` und `awesome-systematic-trading` (eigene Regeldatei). Alte Fassung:
  `profiles\.sicherung\`.
- 18.09.2026 PowerShell 5.1: `Get-FileHash` fehlt (stumm nichts, eine Pruefung
  meldet falsch "alle gleich" - MD5 ueber .NET auf die Bytes); MEHRERE Here-Strings
  in EINEM Befehl kommen verstuemmelt an.
- 20.09.2026 Headless (Kanban/Cron): `execute_code` und gefaehrliche Shell-Befehle
  werden abgewiesen, `write_file` laeuft in den Timeout; auch der INHALT zaehlt.
  Schreiben nach `O:\Werkstatt` scheitert (Junction): Arbeitsergebnisse unter
  `C:\...\BrainFiles` ablegen. Tool-Ausgabe ist LOSSY: Quelltext nie per Augenschein
  pruefen; Read verschluckt CR-Bytes (CRLF-Mix) - Edit auf Basis der gelesenen Kopie
  zerstoert die Datei. Tier-1: vor dem ersten Lesen cp .bak-JJJJMMTT, Edit byte-exakt
  gegen das .bak, Head-Gleichheit pruefen.
- 20.09.2026 Zwei getrennt gebaute Komponenten sind nicht integriert, nur weil beide
  Testreihen gruen sind: die Naht ist das Vokabular - ein Test PRO Wort der Gegenseite;
  ein Probe-Modus darf keine Marke fortschreiben.
- 22.09.2026 Defender loescht Doku-Skills und sperrt den LESEZUGRIFF ("Virus");
  `ls` beweist nichts - Probe ist echter Lesevorgang, Fundort `Get-MpThreatDetection`.
- 22.09.2026 Symlink `auth.json`: nur `pwsh` 7; 5.1 verweigert (Admin).
- 11.10.2026 Gruppenchat: jedes Profil sieht JEDE Nachricht; ANTWORTET nur der
  Angesprochene, Verteilen macht der Verteiler-Bot (`/bot NAME`).
- 11.10.2026 Schleife = CRON-Auftrag (`cron/jobs.json`), nicht `/loop`.
- 11.10.2026 `wc -c` misst CRLF doppelt (5974 vs 6144); Budget nach
  `tr -d '\r'`.
- 11.10.2026 Status von Dauerlaeufen entsteht NUR beim Kerzenabschluss
  (live.json=1d): feste 45-min-Wachgrenze erklaerte den gesunden 692-min-alten
  Lauf fuer tot (lage-Grenze 60 h). Todesgrenzen in Wachen kerzenabhaengig
  (2,5x Abstand), fixer Fallback (omnitrade-order-wache).

Verdichtet 2026-10-08: 6122->5921 (Stash), ->5974 (CR); 11.10: 5974->5909 (Loop=Cron), ->5992 (ein-Bot).
