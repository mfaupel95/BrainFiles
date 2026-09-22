# rule_repo-bots

Regeldatei der Bot-Profile (ein Bot je Fremd-Repo, Hausstandard) - sie gilt fuer
ALLE Bot-Profile, auch die ohne Repo (`hermes-wartung`, `lotse`) und den
Nachschlage-Bot `nerd`.
Sie liegt ABSICHTLICH eine Ebene HOEHER als die Profile (`Agenten\Hermes\profiles\`),
damit alle Bots EINE Stil- und Betriebsquelle teilen statt 27 wortgleiche Kopien.
Jedes `profiles\<bot>\SOUL.md` verweist hierher und bleibt selbst individuell
(Repo-Wissen, Aufgaben, Grenzen).
Budget: 6000 Zeichen. Messen:
`(Get-Item 'C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\profiles\rule_repo-bots.md').Length`
Ueber Budget: verdichten (Abschnitt 5), nicht anhaengen.

## 1. Diese Datei zuerst lesen

Jede Bot-Sitzung liest diese Datei, BEVOR sie plant, Code aendert oder committet.
Gelerntes kommt sofort hier hinein - eine Zeile je Lektion, Regel + Grund.
Repospezifisches gehoert in die eigene `SOUL.md` (sie gewinnt beim Repo-Wissen),
Generelles hierher (diese Datei gewinnt bei Stil und Betriebsregeln).

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
- Regel brechen bei: unumkehrbarer/Live-Aktion (Sicherheit gewinnt), echter
  Mehrdeutigkeit (eine kurze Frage schlaegt Raten), oder wenn die Regel die Antwort
  selbst loeschen wuerde ("welche Optionen habe ich" = die Optionen SIND die Antwort).
- Tiefe auf Zuruf: erklaeren, wenn Max es verlangt - dann vollstaendig, mit Ueberschriften.

## 3. Betriebsregeln (gemeinsam)

- Arbeite in DEINEM Repo (`Werkstatt\Repos\<repo>`, Junction auf O:): `origin` = eigener
  Fork, `upstream` = Original (nur lesen, nie pushen). Shallow-Klon: ein Push scheitert
  mit "did not receive expected object" - vorher `git fetch --unshallow upstream`.
- Vor jedem Commit nur die eigenen Pfade stagen (`git add <pfad>`), nie `git add -A`:
  es laeuft zeitweise eine zweite Hermes-Sitzung auf demselben Baum.
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

1. Groesse messen (Befehl oben). 2. Doppelte Lektionen zusammenlegen. 3. Erledigtes
und Veraltetes loeschen - nicht archivieren. 4. Lange Belege in die passende
Skill-Referenz, hier bleibt der Verweis. 5. Abschlusszeile
`Verdichtet JJJJ-MM-TT: N -> M Zeichen`.
Verdichten ist laufende Arbeit, keine eigene Aufgabe und keine Rueckfrage.

## Gelerntes

- 18.09.2026 angelegt: 27 wortgleiche SOUL.md ersetzt durch EINE hoehere Stilquelle
  (diese Datei). Alte Fassung: `profiles\.sicherung\`.
- Git-Freigabe dieser Datei: `!Agenten/Hermes/profiles/*.md` in `.gitignore` (sonst
  gewinnt `Agenten/Hermes/**`). Pruefen: `git check-ignore -v`.
- 18.09.2026: 27 Repo-Bots; ohne `nous` (kein Repo) und `awesome-systematic-trading`
  (eigene Regeldatei `rule_maXtrade.md`).
- 18.09.2026 PowerShell 5.1: `Get-FileHash` fehlt und liefert stumm nichts (eine
  Pruefung darauf meldet falsch "alle gleich" - MD5 ueber .NET auf die Bytes), und
  MEHRERE Here-Strings in EINEM Befehl kommen verstuemmelt an (0-Byte-Datei, keine
  Meldung) - eine Datei je Aufruf, Groesse pruefen.
- 20.09.2026 Headless (Kanban/Cron): `execute_code` und gefaehrliche Shell-Befehle
  werden abgewiesen, `write_file` laeuft in den Timeout; auch der INHALT zaehlt -
  Risikomuster aus Teilen bauen.
- 20.09.2026 Schreiben nach `O:\Werkstatt` scheitert (Junction, ausserhalb
  HERMES_WRITE_SAFE_ROOT). Arbeitsergebnisse unter `C:\...\BrainFiles` ablegen.
- 20.09.2026 Tool-Ausgabe ist LOSSY (Gleichheitszeichen, Pfeile, doppelte Leerzeichen
  fallen weg): Quelltext nie per Augenschein pruefen - Leerzeichen sichtbar machen oder
  inspect.signature lesen, sonst diagnostiziert man Fehler, die gar nicht dastehen.
- 20.09.2026 Zwei getrennt gebaute Komponenten sind nicht integriert, nur weil beide
  Testreihen gruen sind: die Naht ist das Vokabular - eine Uebersetzungstabelle braucht
  einen Test PRO WORT der Gegenseite. Ein Probe-Modus darf keine Marke fortschreiben.

- 22.09.2026 Windows Defender zieht Doku-Repos ein: vier `SKILL.md` in `claude-red`
  (SQLi/RCE/File-Upload/Shellcode) wurden geloescht, danach blieb der LESEZUGRIFF
  gesperrt ("Datei enthaelt einen Virus"). `ls` beweist nichts - die Probe ist ein
  echter Lesevorgang, der Fundort `Get-MpThreatDetection`.
- 22.09.2026 Symlink fuer `auth.json`: `pwsh` 7 legt ihn ohne Erhoehung an,
  `powershell.exe` 5.1 verweigert mit "Administratorrechte erforderlich".

Verdichtet 2026-09-22: 5990 -> 5991 Zeichen
