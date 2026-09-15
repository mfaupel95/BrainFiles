# Fremdarbeit im Baum: erkennen, liegen lassen, spaeter mitnehmen

## Wann
Mehrere Sitzungen arbeiten im selben Baum. Ausloeser: „wenn die andere Session
fertig ist, mitnehmen", `git status` zeigt eine geaenderte Datei, die man selbst
nicht angefasst hat, oder ein `git add -A <ordner>` hat sie schon eingesammelt.

## Schritt 1 - erkennen, bevor committet wird
- `git status --short <ordner>` VOR dem Commit, `git show --stat HEAD` danach
  gegen die Absicht halten.
- Fremdarbeit erkennt man an: mtime, die zu keinem eigenen Aufruf passt;
  Wachstum zwischen zwei Blicken (spiegel.py am 14.09.2026: 19:02 = 188
  geaenderte Zeilen, 19:04 = 376); Symbolen, die man nicht kennt.
- `python -m py_compile <datei>` sagt, ob der Stand uebersetzbar ist. Ein
  Zwischenstand ist oft syntaktisch fein und trotzdem unfertig - py_compile
  beweist Fertigsein NICHT.

## Schritt 2 - ist sie im eigenen Commit gelandet?
```
git reset --soft HEAD~1
git restore --staged <fremddatei>
git commit -q -F - <<'EOF'      # nur die eigenen Dateien, eigene Nachricht
EOF
git status --short <ordner>     # Fremddatei muss wieder als " M" stehen
```
So wurde eine 188-Zeilen-Fremdaenderung aus einem eigenen Commit geholt. Die
Fremdaenderung danach UNANGETASTET liegen lassen und im Abschlussbericht nennen
- sie braucht eine Entscheidung von Max, nicht eine stille Mitnahme.

## Schritt 3 - fertig oder nicht?
Fertig heisst: (a) die Quelldateien der Spur sind seit `RUHE_MIN` (20) Minuten
unberuehrt, (b) `py_compile` gruen, (c) die Testsuite der Spur gruen.
Sonst warten - nicht raten und nicht „sieht fertig aus". Die mtime ist das
Messinstrument; ein Stand, der zwischen zwei eigenen Nachfragen waechst, ist in
Arbeit.

## Schritt 4 - der Waechter (Hermes-Cron, kein LLM)
```
cronjob(action="create", name="<Spur>-Fremdcommit", schedule="every 20m",
        no_agent=True, script="fremdarbeit_waechter.py",
        deliver="origin", repeat=72)
```
- `no_agent: true`: das Skript IST der Job; **leere Ausgabe schickt nichts**
  (Watchdog-Muster) - kein Spam alle 20 Minuten.
- `repeat` laesst den Job von allein auslaufen (72 x 20 min = 24 h).
- Verdrahtung einmal probefahren: `cronjob(action="run", job_id=...)`; der
  Status muss `silent (empty output)` melden.
- Merkerdatei: eine rote Meldung nur EINMAL je Inhalt, sonst kommt alle 20
  Minuten dieselbe Nachricht.
- Der Waechter committet NUR Quelldateien (.py) der Spur. Laufzeitdaten
  (`zustand.json`, `handelsjournal.csv`, `ablehnungen.csv`, `verfolgte.json`)
  sind per Whitelist ignoriert und werden nie angefasst.
- Die Commit-Nachricht sagt, wessen Arbeit es ist: „nicht von Hermes, nur
  geprueft (`py_compile` + Testsuite) und mitgenommen, inhaltlich nicht
  bewertet".
Skript dieses Skills: `scripts/fremdarbeit_waechter.py` (Spur, Repo,
Interpreter, Ruhezeit sind Parameter; `--probe` zeigt ohne zu schreiben).

## Schritt 5 - ungefragt wird nichts verdrahtet
Aendert die Fremdarbeit Regeln (Deckel, `handel_erlaubt`, Kosten, Freigabe),
gehoert sie Max vorgelegt. Mitnehmen heisst: pruefen, committen, melden - nicht
bewerten.

## Pitfalls
- `git add -A <ordner>` in einem Baum mit mehreren Sitzungen ist die Ursache,
  nicht der Zufall. Immer eine explizite Pfadliste.
- Die andere Sitzung darf selbst committen: dann findet der Waechter beim
  naechsten Lauf nichts und bleibt still. Das ist der Normalfall, kein Fehler.
- Ein eigener Testlauf kann dabei dieselbe Kopie ausser Haus treffen, die schon
  einmal ueberschrieben wurde (Bedingung 4): nach jeder Testrunde
  `spiegelstand.py` - siehe die Regel zu `journal_zweitziel` im Test-Setup.
- Ein Waechter committet NICHT, wenn die Tests rot sind; er meldet. Eine
  halbfertige Sitzung wird nicht durch einen roten Commit markiert.
- Das Skript selbst liegt unter `Agenten/Hermes/scripts/` (nicht versioniert,
  wie die uebrigen Hermes-Interna) - es wird nicht mitcommittet.

## Verification
```
python scripts/fremdarbeit_waechter.py --probe --spur <pfad> --repo <pfad> \
       --python <venv-python>
git status --short <ordner>    # danach: leer
git log --oneline -1
git -C <spur> status --short   # Spuren mit eigenem Repo: dort getrennt committen
```
