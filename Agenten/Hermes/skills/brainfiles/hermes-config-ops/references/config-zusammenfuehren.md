# Eine Config mit fremden Aenderungen zusammenfuehren

Ausloeser: der Arbeitsbaum zeigt `config.yaml` als geaendert, und der Diff
enthaelt mehr als die eigene Zeile — bei diesem Nutzer der Normalfall (Desktop-,
Telegram- und CLI-Sitzung gleichzeitig). „Zusammenfuehren" heisst: jeden Hunk
einzeln entscheiden, nicht den Stand pauschal uebernehmen oder verwerfen.

**Die Entscheidung faellt am LESER, nicht am Gefuehl.** Fuer jeden fremden Hunk
die Stelle im Code suchen, die den Schluessel liest
(`grep -rln "<schluessel>" hermes-agent/hermes_cli/ hermes-agent/agent/`), und
dort nachsehen, was der Wert bewirkt. Erst danach behalten, korrigieren oder
entfernen. Drei Befunde, die dabei regelmaessig auftauchen:

- **Ein Schluessel ohne Leser ist tote Konfiguration.** Findet die Suche im
  ganzen Baum keine Lesestelle, ist der Block wirkungslos — entfernen, nicht aus
  Hoeflichkeit stehen lassen. Er sieht sonst dauerhaft wie eine Einstellung aus.
  Zweiter Hinweis auf denselben Fund: ein Eintrag, dem ein Pflichtfeld fehlt,
  wuerde vom Normalisierer ohnehin verworfen (siehe `_iter_fallback_entries`).
- **Ein Listen-Schluessel, der als einzelnes Mapping geschrieben wurde, bleibt
  gueltig und verliert trotzdem Eintraege.** Der Normalisierer macht aus einem
  dict eine Ein-Eintrags-Kette — kein Fehler, keine Warnung, aber jede weitere
  Reserve ist weg. Nach dem Zusammenfuehren die ZAHL der Eintraege pruefen
  (`hermes config get <schluessel>`), nicht nur den ersten.
- **Ein geloeschter Kommentarblock ist eine stille Aenderung an der Datei des
  Nutzers** und meist Nebenwirkung eines `hermes config set` (siehe Falle oben),
  keine Absicht. Wiederherstellen.

Harmlose und sinnvolle Fremdaenderungen (ein zusaetzlicher `auxiliary`-Block,
ein Eintrag in einer Allowlist) werden uebernommen und im Commit-Text als
uebernommen benannt — wer sie wegwirft, zwingt die andere Sitzung, sie noch
einmal zu setzen.

Der eigene Anteil geht allein in den Commit, die fremden bleiben liegen. Bei einer
gemischten Datei den Index DETERMINISTISCH bauen statt Hunk-Antworten zu raten:
`git show HEAD:<datei>`, die eigene Aenderung byte-genau im Speicher einsetzen,
`git hash-object -w --path=<datei> --stdin` und
`git update-index --cacheinfo 100644,<sha>,<datei>` (der Arbeitsbaum bleibt unberuehrt,
die fremde Aenderung steht weiter als `M`). Falle dabei: ist die Datei CRLF,
liefert `git show HEAD:` `\r\n` — erst das Zeilenende bestimmen und DARAUF
splitten (`nl = '\r\n' if '\r\n' in text else '\n'`), sonst trifft ein
Zeilenvergleich (`zeile == '  schluessel: wert'`) nie, weil jede Zeile ein `\r`
traegt, und der "gebaute" Index bleibt unbemerkt identisch zum HEAD — der
Gegencheck `git diff --cached --numstat` faengt das (0 Zeilen). `git apply
--cached` mit selbstgebauten Hunks scheitert an CRLF-Configs (`corrupt patch`) —
der Index-Weg ist dort die stabile Route. Danach `git diff --cached --numstat --
<datei>` lesen — dort steht genau der eigene Anteil (Beispiel: `30 0` fuer einen
eingefuegten Abschnitt, `32 2` mit zwei geaenderten Frontmatter-Zeilen) — und die
Restmenge gegenpruefen: `git diff --numstat -- <datei>` muss die fremden Zeilen
unveraendert weiter ausweisen. `git add -p` bleibt der Notweg fuer zwei klar getrennte
kleine Hunks. Die fremden Zeilen werden im Commit-Text als nicht enthalten benannt;
fremd Gestagetes nie mitcommitten (Regeln (immer) 7). Rezept und Regeln:
`arbeitsbaum-git-hygiene`.

**Nach einem Commit aus dem EIGENEN Index den NORMALEN Index fuer dieselben Pfade
nachziehen.** Er zeigt sonst weiter auf die VORHER-Fassungen: `git status` meldet die
Dateien als `MM` (gestaged UND geaendert), und ein fremdes `git commit` ohne
Pfadangabe setzt sie aus seinem Index auf den alten Stand zurueck - der eigene,
gerade committete Teil waere dann in einem fremden Commit wieder weg. Zwei Wege,
nach Absicht: `git add -- <pfade>` fuer Dateien, deren Arbeitsbaumstand mitgehoert;
`git reset -q -- <pfade>` fuer Dateien, die noch fremde uncommittete Zeilen tragen
(der eigene Teil ist committet, der fremde bleibt unstaged liegen). Danach
`git diff --cached --name-only` (muss leer sein) und `git status --porcelain --
<pfade>` lesen - uebrig bleiben darf nur die fremde Zeile.

**Nachweis:** `git diff --stat` muss additiv aussehen (viele Zeilen rein, nur
die eigene Ersetzung raus). Ein Diff, der mehr loescht als hinzufuegt, hat
fremde Arbeit verschluckt. Danach `hermes config get` fuer jeden angefassten
Schluessel, und die Datei einmal als YAML parsen lassen, BEVOR sie geschrieben
wird — bei einer Config gibt es keinen `ast.parse`, aber `yaml.safe_load` auf
dem neuen Text im Speicher leistet dasselbe (dazu die erwarteten Invarianten
als `assert`: Typ der Liste, Zahl der Eintraege, kein toter Schluessel mehr).
