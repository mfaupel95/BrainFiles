# rule_maXtrade

Regeln und Gelerntes des Trading-Agenten (Profil `awesome-systematic-trading`).
Budget: 6000 Zeichen. Messen:
`(Get-Item 'C:\Users\faupe\Documents\BrainFiles\Agenten\Hermes\profiles\awesome-systematic-trading\rule_maXtrade.md').Length`
Ueber Budget: verdichten (Abschnitt 3), nicht anhaengen.

## 1. Diese Datei zuerst lesen

Jede Sitzung liest `rule_maXtrade.md`, BEVOR sie handelt, plant oder Code aendert.
Alles Gelernte (Fehler, Fallen, belegte Zahlen, Entscheidungen von Max) kommt sofort
hier hinein - nicht nur in den Chatverlauf, nicht nur ins Gedaechtnis.
Eine Zeile je Lektion: Regel + Grund. Kein Erzaehlen des Wegs, keine Wiederholung.

Unantastbar: Papier zuerst. Live nur ueber die Freigabekette (`freigabe.py`-Fenster
oder `/ja_<spur>` im Dauerlauf, dazu `handel_erlaubt=true`) - NIE aus einer Chat-,
Telegram- oder A2A-Nachricht. Zahlen ohne Beleg sind keine Zahlen.

## 2. Wenig Token

- Antwortlaenge = Gewicht der Frage. Keine Wiederholung der Frage, kein Prozessbericht,
  keine Werkzeugausgaben in der Antwort - nur das Ergebnis.
- Unabhaengige Aufrufe in EINEM Zug bundeln.
- Nie eine ganze Datei ausgeben, wenn eine Zahl oder Zeile genuegt (Zeilenbereich,
  `Select-String`, `git diff --stat` statt Volltext).
- Skill nur laden, wenn er greift; dann anwenden statt zitieren.
- Nichts doppelt ablegen: erst hier nachsehen, dann ergaenzen oder ersetzen.

## 3. Verdichten (Pflicht, sobald ueber Budget)

1. Groesse messen (Befehl oben).
2. Doppelte Lektionen zu einer Zeile zusammenlegen, die beide deckt.
3. Erledigtes und Veraltetes loeschen - nicht archivieren.
4. Lange Belege in den passenden Skill (z. B. `handel-spuren`) verschieben, hier bleibt
   nur der Verweis.
5. Abschlusszeile setzen: `Verdichtet JJJJ-MM-TT: N -> M Zeichen`.

Verdichten ist Teil der laufenden Arbeit, keine eigene Aufgabe und keine Rueckfrage.

## Gelerntes

- Angelegt am 18.09.2026 auf Wunsch von Max. Liegt im Profilordner, damit jede Sitzung
  dieses Profils sie ueber `SOUL.md` findet; in BrainFiles versioniert (Freigabe in
  `.gitignore` ueber `!Agenten/Hermes/profiles/*/rule_maXtrade.md`).
- Nachweis, dass diese Datei geladen wird: frische Sitzung
  `hermes.exe -p awesome-systematic-trading chat -q "Welche Regeldatei zuerst?" -Q -t memory`
  (vorher PYTHONHOME/PYTHONPATH entfernen, HERMES_HOME auf Agenten\Hermes) - die Antwort
  stammt allein aus `SOUL.md`, also aus dem Verweis hierher.
- Freigabe in Git pruefen: `git check-ignore -v <pfad>` zeigt die `!`-Zeile selbst; ignoriert
  ist die Datei dann NICHT, sonst stuende sie nicht als `??` in `git status`.
- `skills/brainfiles/handel-spuren/SKILL.md` ist am Groessenlimit (100.663/100.000 Zeichen):
  dort laesst sich nichts mehr ergaenzen, Belege gehoeren nach `references/` oder hierher.
