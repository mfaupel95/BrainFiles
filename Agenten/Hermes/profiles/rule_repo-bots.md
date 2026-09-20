# rule_repo-bots

Regeldatei der Bot-Profile (ein Bot je Fremd-Repo, Hausstandard) - sie gilt
auch fuer `hermes-wartung`, den Bot ohne Repo (Arbeitsbereich `Agenten\Hermes`).
Sie liegt ABSICHTLICH eine Ebene HOEHER als die Profile (`Agenten\Hermes\profiles\`),
damit alle Bots EINE Stil- und Betriebsquelle teilen statt 27 wortgleiche Kopien.
Jedes `profiles\<bot>\SOUL.md` verweist hierher und bleibt selbst individuell
(Repo-Wissen, Aufgaben, Grenzen).
Budget: 6000 Zeichen. Messen:
`(Get-Item 'C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\profiles\rule_repo-bots.md').Length`
Ueber Budget: verdichten (Abschnitt 5), nicht anhaengen.

## 1. Diese Datei zuerst lesen

Jede Sitzung eines Repo-Bots liest `rule_repo-bots.md`, BEVOR sie plant, Code aendert
oder committet. Alles Gelernte kommt sofort hier hinein - eine Zeile je Lektion,
Regel + Grund, kein Erzaehlen des Wegs. Repospezifisches gehoert in die eigene
`SOUL.md`, Generelles hierher. Widerspruch: die eigene SOUL.md gewinnt beim Repo-Wissen,
diese Datei bei Stil und Betriebsregeln.

## 2. Stil (gilt fuer alle Bots)

- Ergebnis zuerst: erste Zeile = naechste Aktion (Befehl, Pfad), nicht die Begruendung.
- Antwortlaenge = Gewicht der Frage. Keine Floskeln ("Gerne", "Ich helfe dir gern"),
  kein Prozessbericht, keine Werkzeugausgaben, keine Wiederholung der Frage.
- Mehrschrittiges = nummerierte Liste, ein Schritt = eine Handlung, keine "und dann".
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

- Arbeite in DEINEM Repo: `Werkstatt\Repos\<repo>` (Junction auf O:). `origin` = eigener
  Fork (mfaupel95), `upstream` = Original. NIE nach upstream pushen, upstream nur lesen.
- Die Klone sind SHALLOW: ein Push scheitert mit "did not receive expected object" -
  vorher `git fetch --unshallow upstream`.
- Vor jedem Commit nur die eigenen Pfade stagen (`git add <pfad>`), nie `git add -A`:
  es laeuft zeitweise eine zweite Hermes-Sitzung auf demselben Baum.
- Keine Schluessel, Tokens oder .env-Inhalte ins Repo. `.env_example` nennt nur Namen;
  echte Zugaenge stehen ausschliesslich in `MaxHirn\Wissen\Zugaenge.md` - nie ausgeben.
- Python-venv heisst `.venv` (Hausstandard, auch wenn die Repo-Anleitung "venv" sagt).
- Keine fremden `SKILL.md` importieren (skill-library-sync) - Fremd-Skills nur lesen.
- Nicht in andere Profile oder fremde Repos schreiben; fremde Aenderungen liegen lassen.
- Laufende Prozesse, Dauerlaeufe und offene Fenster nicht anfassen.
- Nichts loeschen, was du nicht erzeugt hast (Stufen der Schutzregeln:
  `MaxHirn\Wissen\Schutzregeln.md`).
- Papier/Test zuerst; Live, Kauf, Versand, Loeschen nur auf ausdrueckliche Anweisung.
- Dateien in BrainFiles: LF-Zeilenenden, ASCII bevorzugt (Umlaute als ae/oe/ue).

## 4. Telegram-Zugang

Der SkillsBot kennt `/bots` (Name + Beschreibung aus `profile.yaml`) und
`/bot <name> <nachricht>` = frischer Einzelauftrag, Kaltstart 30-60 s; der Name muss
auf der Platte existieren. Doku: `MaxHirn\Wissen\Repo-Bots.md`.

## 5. Verdichten (Pflicht, sobald ueber Budget)

1. Groesse messen (Befehl oben). 2. Doppelte Lektionen zu einer Zeile zusammenlegen.
3. Erledigtes und Veraltetes loeschen - nicht archivieren. 4. Lange Belege in die
passende Skill-Referenz verschieben, hier bleibt der Verweis. 5. Abschlusszeile
`Verdichtet JJJJ-MM-TT: N -> M Zeichen`.
Verdichten ist laufende Arbeit, keine eigene Aufgabe und keine Rueckfrage.

## Gelerntes

- 18.09.2026 angelegt: die 27 Repo-Bots hatten wortgleiche SOUL.md (3030 Zeichen,
  MD5 D5EC74ACD025B18710647B2651F4A085). Umstellung auf EINE hoeher liegende Stilquelle
  (diese Datei) + individuelle, repo-bezogene SOUL.md je Bot. Alte Fassung gesichert
  unter `profiles\.sicherung\SOUL-generisch-20260918.md`, Historie in Git.
- Git-Freigabe dieser Datei: `!Agenten/Hermes/profiles/*.md` in `.gitignore` (die
  allgemeine Sperre `Agenten/Hermes/**` gewinnt sonst). Pruefen: `git check-ignore -v`.- 18.09.2026 Anzahl: 27 Repo-Bots, nicht 26. Ohne `nous` (kein Repo) und ohne
  `awesome-systematic-trading` (eigene Regeldatei `rule_maXtrade.md`).
- 18.09.2026 Werkzeugfalle beim Massenschreiben: das MCP-PowerShell-Werkzeug verschluckt
  bei MEHREREN Here-Strings in EINEM Befehl still den Inhalt - die Datei landet mit
  0 Byte, ohne Fehlermeldung. Eine Datei je Aufruf schreiben (oder das FileSystem-
  Werkzeug mit mode=write) und danach Groesse UND Identitaetszeile pruefen.
- 18.09.2026 `Get-FileHash` fehlt in dieser PowerShell (5.1). Es liefert still nichts,
  und eine Pruefung darauf meldet dann "alle Dateien gleich" - ein falscher Befund.
  Stattdessen `[System.Security.Cryptography.MD5]::Create()` auf die Bytes.
- 18.09.2026 Beleg, dass die Kette wirkt: frische Sitzung eines Bots fragen
  "Welche Regeldatei liest du zuerst?" - die Antwort kommt allein aus `SOUL.md`.