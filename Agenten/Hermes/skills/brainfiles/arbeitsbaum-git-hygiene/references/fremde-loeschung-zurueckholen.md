# Eine fremde Loeschung im eigenen Commit zurueckholen

Die geteilter-Index-Falle, ihre Erkennung und die Ruecknahme. Gehoert zu
`arbeitsbaum-git-hygiene`, SKILL.md.

## Das Muster

`git add <eigene Pfade>` merkt nur VOR. Der anschliessende `git commit` OHNE
Pfadangabe committet den GANZEN Index — auch alles, was eine parallele Sitzung
oder eine Routine Sekunden vorher vorgemerkt hat. Bei einer Textdatei faellt das
auf; bei einer **Loeschung** faellt es nicht auf, weil die Commit-Meldung nur
Zahlen zeigt.

## Die zwei Blicke

```bash
git diff --cached --numstat    # VOR dem Commit — LESEN, nicht nur ausfuehren
git commit -m "..."
git show HEAD --stat           # NACH dem Commit — steht hier ein fremder Pfad?
```

**Die Deletions sind das Warnsignal.** Mehr Loeschungen als der eigene Block
Zeilen hat, heisst immer: hier ist Fremdtext mitgegangen. Eine Meldung wie
`2 files changed, 15 insertions(+), 382 deletions(-)` liest sich wie eine reine
Textaenderung und ist eine Dateiloeschung.

## Die Ruecknahme — zwei Zeilen, ein FOLGE-Commit

```bash
git show HEAD --stat                 # welcher Pfad gehoert nicht ins Thema
git add <fremder pfad>               # Arbeitsbaum-Inhalt ist unberuehrt -> holt ihn zurueck
git commit -m "<pfad> wiederhergestellt (fremde Loeschung im eigenen Commit mitgenommen)"
```

**Nie `--amend`, nie force-push.** Der Baum hat einen geteilten Index und fremde
Arbeit; ein Umschreiben der Historie trifft beides.

Die Datei liegt meist noch auf der PLATTE — nur der Commit hat sie entfernt.
Erst wenn sie auch dort fehlt, ist es ein echter Verlust und `git show
<vorgaenger>:<pfad>` der Weg.

## Warum das teuer ist

Die geloeschte Datei war oft schon einmal weg. Belegt: eine Aufraeum-PR hatte
eine Datei entfernt, die Routine `fremdarbeit-einziehen` hatte sie Minuten
vorher gerade WIEDERHERGESTELLT — der eigene Commit loeschte sie ein ZWEITES
Mal. Ohne `git show HEAD --stat` faellt das erst auf, wenn jemand die Datei
vermisst.

## Warum der eigene Index trotzdem noetig ist

Ist der Index schon von fremden Pfaden belegt, mit EIGENEM Index committen:

```bash
GIT_INDEX_FILE=<scratch>/idx_<thema> git read-tree HEAD
GIT_INDEX_FILE=<scratch>/idx_<thema> git add <eigene pfade>
GIT_INDEX_FILE=<scratch>/idx_<thema> git commit -m "..."
unset GIT_INDEX_FILE
git add <eigene pfade>        # PFLICHT: den ECHTEN Index nachziehen
```

Der Nachtrag ist Pflicht, sonst vergleicht der echte Index gegen den neuen HEAD
und meldet die frisch committeten Dateien als geloescht (`D `) plus
untracked (`??`) — die Fremdarbeit-Routine committet sie dann erneut als fremd.
Ausnahme: hat eine parallele Sitzung die Datei NACH dem eigenen Commit
weiterbearbeitet, NICHT nachziehen (`git reset -q HEAD -- <pfad>`), sonst liegt
ihre laufende Arbeit im Index.
