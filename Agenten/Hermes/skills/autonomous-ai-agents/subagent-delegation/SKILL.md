---
name: subagent-delegation
description: "Subagenten losschicken: Kette pruefen, Fehler deuten."
category: autonomous-ai-agents
---

# Mehrere Subagenten losschicken und steuern

## Wann

„Mach das mit mehreren Agenten“, ein Auftrag mit mehreren unabhaengigen Teilen
(mehrere Repos, mehrere Dateien ohne Beruehrung), ein Recherche-/Analyseblock,
dessen Zwischenergebnis den eigenen Kontext fluten wuerde, oder ein
Auswertungsjob, den mehrere Kinder parallel lesen.

## Teuer denkt, billig schreibt

Stehende Vorgabe: **Ausfuehrungsarbeit gehoert auf das billige Modell.** Lesen,
Scannen, Befunde deuten und die eine Empfehlung formulieren macht die Sitzung
selbst; Umsetzen (Code aendern, Tests schreiben, migrieren, committen) geht an
ein Kind. Wer eine mechanische Mehrschritt-Umsetzung im Elternmodell erledigt,
verbrennt Premium-Tokens fuer Arbeit ohne Urteil — und genau das faellt dem
Nutzer auf, nicht die Laufzeit.

Die Aufteilung gilt auch mitten im Auftrag: sobald der Scan fertig ist und die
naechsten Schritte feststehen, wechselt die Rolle. Die Sitzung dispatcht und
prueft danach den Beleg — sie tippt die Umsetzung nicht selbst.

**Die Grenze der Regel: ein Kind liest von Null.** Es erbt den Kontext nicht —
alles, was die Sitzung beim Scan schon gelesen hat, liest das Kind noch einmal,
auf seine Kosten und seine Laufzeit. Hat der eigene Scan die Zieldateien bereits
im Kontext und besteht die Umsetzung aus einer Handvoll chirurgischer
Ersetzungen, ist das Kind das TEURERE Mittel: es verbrennt Minuten und Dutzende
API-Aufrufe fuer Lesearbeit, die schon getan ist. Entscheidungsregel vor dem
Dispatch: **Wie viel muss das Kind lesen, bevor es die erste Zeile schreibt?**
Viel Suche, breiter Baum, unbekannte Stellen → delegieren. Bekannte Datei,
bekannte Zeilen, feststehende Ersetzungen → selbst machen und den gesparten
Dispatch als Ersparnis verbuchen.

Wer trotzdem delegiert, senkt die Lesekosten im `context`: die genauen
Anker ausschreiben (Datei, Funktion, Zeilennummer, der zu ersetzende Text), nicht
nur das Ziel beschreiben. Ein Brief mit Ankern spart dem Kind den halben Lauf.

## Vor dem Dispatch: die Kette pruefen

Zwei Fragen, nicht eine: **was kostet das Ziel, und lebt es?**

**Preis zuerst.** `delegation.provider` / `delegation.model` bestimmen, ueber
welches Modell jedes Kind laeuft. Ein dort stehen gebliebener Premium-Pin (ein
Cloud-Spitzenmodell als `provider`/`model`, aus einer frueheren Sitzung gesetzt)
kostet bei JEDEM Dispatch still das Vielfache, ohne dass irgendetwas scheitert —
der teuerste Fehler dieser Kette ist der, der funktioniert. Also **vor** dem
ersten `delegate_task` einmal `hermes config get delegation` lesen und den Wert
gegen den Auftrag halten: mechanische Umsetzung laeuft auf dem Router-Alias
(`auto/best-coding`), nicht auf dem Elternmodell. Umstellen mit
`hermes config set delegation.provider <x>` / `delegation.model <y>`; wirkt ohne
Neustart.

**Dann die Erreichbarkeit.** Zeigt `provider` auf einen lokalen Router, stirbt
bei totem Dienst **jedes** Kind nach 3 Wiederholungen mit `API call failed after
3 retries: Connection error`, in rund 45 s, noch **vor** dem ersten
Werkzeugeinsatz. Messen nicht per Portscan, sondern am HTTP-Endpunkt — ein
offener Port beweist nicht, dass der Router antwortet:
`curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://127.0.0.1:<p>/v1/models`.
**`401` ohne Schluessel heisst: lebt.** `000` heisst: tot.

Muss der Router erst starten, den Start-Wrapper **nicht** in einem knappen
Vordergrund-Aufruf abwarten: er braucht Minuten, der Werkzeug-Timeout reisst,
waehrend der Dienst im Hintergrund trotzdem hochkommt — ein zweiter Startversuch
waere dann ein zweiter Prozess auf demselben Port. Nach dem Anstossen in einer
kurzen Schleife pollen (`for` ueber ~10 Versuche mit Pause, Abbruch beim ersten
Antwortcode != `000`) und erst bei Antwort dispatchen. Ein Batch, der ins Leere
laeuft, kostet einen ganzen Durchgang.

**Einen Dauerdienst NIE aus der eigenen Sitzung heraus starten.** Ein Start ueber
das Terminal-Werkzeug mit `background=true` erzeugt ein KIND der Sitzung: endet
der Wrapper, stirbt der Dienst mit ihm — und jeder „Neustart“ toetet zugleich den
vorher gestarteten. Das Fehlerbild ist heimtueckisch, weil es wie ein instabiler
Dienst aussieht: er kommt hoch, nimmt Arbeit an, und Kinder sterben Minuten
spaeter reihenweise an `Connection error`. Richtig ist ein **abgekoppelter**
Start ueber den Dienst-/Aufgabenmechanismus des Systems — unter Windows die
Aufgabenplanung (`schtasks /run /tn <Aufgabe>`), die den Prozess ausserhalb der
Sitzung fuehrt. Gibt es fuer den Dienst eine Aufgabe, ist sie der einzige
Startweg; existiert keine, ist das Anlegen einer der Fix, nicht ein weiterer
Handstart.

**Bevor ein Dienst fuer instabil erklaert wird: pruefen, wer seinen Prozess
besitzt.** Zwei Gegenproben, beide billig. (1) Faellt jeder Ausfall in ein
Fenster, in dem die Sitzung selbst gestartet, gestoppt oder einen Wrapper hat
enden lassen? Dann ist die Sitzung die Ursache, nicht die Last. (2) Laeuft ein
Geschwister-Kind durch DENSELBEN Zeitraum weiter, in dem ein anderes stirbt, ist
der Dienst gesund — ein echter Dienstausfall trifft alle Kinder gleichzeitig.
Eine Fehldiagnose kostet hier doppelt: sie erzeugt eine erfundene Empfehlung
(„der Dienst braucht einen Waechter“), die der Nutzer umsetzen soll. Ist sie
rausgegangen, gehoert sie ausdruecklich zurueckgenommen.

Zwei Fehlerbilder, zwei verschiedene Fixes — nicht verwechseln:

- `Connection error` nach 3 Retries: das Ziel ist nicht erreichbar (Prozess aus,
falscher Port). Fix am Dienst, nicht an der Aufgabe.
- `HTTP 401: No active credentials for provider: <X>`: die Route steht, aber
`<X>` ist fuer sie nicht bedienbar — und das hat **zwei** Ursachen mit
identischem Wortlaut: (1) der Zugang fehlt (Schluessel, Berechtigung,
Entschluesselung), (2) **`<X>` existiert im Ziel ueberhaupt nicht**, weil die
Config einen Provider-/Modellnamen nennt, den der Router nicht kennt (dort
stand `Ollama/gemma4`, der Router kennt nur `ollama-local`). Immer erst den
Namen gegen die Modellliste des Ziels halten — `GET /v1/models` mit dem
Zugang des Ziels, bei Ollama direkt `/api/tags` —, sonst repariert man
Schluessel, die nie das Problem waren. Fix am Zugang nur, wenn der Name
aufloest; und wenn der Nutzer etwas tun muss, klar sagen: welche Zeile,
welches Ziel, welche Handlung.

**Der Rueckfall muss eine ANDERE Ausfalldomaene haben.** `delegation` und
`delegation.fallback_providers` duerfen nicht auf dasselbe Ziel zeigen: ein
Rueckfall, der beim Ausfall des Routers denselben Router ruft, ist keiner — er
sieht in der Config nach Absicherung aus und faengt genau den haeufigsten Fall
nicht. Steht `delegation.provider` auf dem lokalen Router, gehoert in den
Rueckfall ein Weg, der ohne ihn auskommt (Cloud-Provider mit eigenem Zugang,
oder ein lokales Modell direkt an seinem eigenen Port). Dieselbe Frage fuer die
globale Kette: **`fallback_providers` ist eine LISTE.** Wird sie auf ein
einzelnes Mapping umgeschrieben, bleibt sie gueltig (ein dict wird zu einer
Ein-Eintrags-Kette normalisiert) — und wirft still jede weitere Reserve raus.
Wer dort etwas aendert, prueft danach `hermes config get fallback_providers`
auf die Zahl der Eintraege, nicht nur auf den ersten.

## Jeder Eintrag in `tasks` startet einen Agenten

Es gibt keinen Platzhalter: ein Eintrag mehr als echte Aufgaben kostet einen
Parallel-Slot und laeuft sinnlos. Das Array genau so lang wie die Zahl der Jobs,
die man wirklich delegiert — vor dem Absenden einmal durchzaehlen.

Auftraege so schneiden, dass sie sich nicht beruehren: **getrennte Ordner,
Crates oder Dateimengen.** Zwei Kinder im selben Baum serialisieren sich ueber
gemeinsame `target/`- oder Lock-Dateien und kollidieren bei derselben Datei.

**Der `tasks`-JSON-Parser ist waehlerisch beim Goal- UND Context-Text.**
Ein Goal oder Context, der Shell-Sonderzeichen oder escaped Anfuehrungszeichen
in eingebetteten Zitaten traegt (z. B. ein Aufruf mit `&&`, `2>&1`, `"$r"`
als zitiertem Argument, oder `\"`-Sequenzen in einem langen Context), scheitert
im Dispatcher mit `Expecting ',' delimiter`, obwohl das JSON valide ist. Ein
Prosa-Text ohne solche Zeichen laeuft durch. Bevor ein Goal/Context mit
Shell-Text oder verschachtelten Zitaten abgeschickt wird: den Befehl in den
`context` legen und im Goal nur beschreiben ("das Skript X ausfuehren und
verifizieren"), nicht zitieren — oder dem Kind erlauben, die Fachbegriffe aus
dem Context zu nehmen. Scheitert der erste Versuch trotzdem, den Text
vereinfachen (Zitate entfernen, Prosa statt Befehl) — nicht denselben Aufruf
unveraendert wiederholen (naechste Regel).

Zwei weitere Ausloeser desselben `Expecting ',' delimiter`-Fehlers, beide
beobachtet: **Literal-Zeilenumbrueche in einem mehrzeiligen `context`** (ein
String mit echten `\n`-Zeilen bricht den Parser, obwohl er als JSON valide
ist) und ein **verschachteltes `output_schema`-Objekt im Task** (ein
mehrstufiges Schema mit `properties`/`required` kippt den Parser, waehrend
derselbe Task ohne Schema durchlaeuft). Beide sind nicht am Text zu erkennen —
die robuste Vorlage ist: `context` und `goal` als EINZEILIGE Prosa-Strings
ohne eingebettete Zeilenumbrueche und ohne `output_schema`; die erwartete
Ausgabe stattdessen als Prosa-Satz im `goal` beschreiben ("Antworte mit:
Dateien, Testzahl, Commit-Hash"). Ein minimaler Test-Dispatch (kurzer
`context`, kein Schema) vor dem echten Auftrag trennt Tool-Fehler von
Text-Fehler: laeuft der minimale durch, liegt es am Inhalt, nicht am Tool.


**Fehlversuche gleichen Arguments kosten den Dispatch-Budget und enden im
Hard-Limit.** Wiederholt man denselben `tasks`-Aufruf unveraendert (auch nach
`Expecting ',' delimiter`), zaehlt JEDER Versuch gegen das
Subagent-Limit pro Sitzung; nach 50 Versuchen blockiert der Dispatcher dauerhaft
mit `already spawned 50 subagents`. Also: kein zweiter identischer Versuch —
nach dem ersten Fehler den Goal vereinfachen oder die Ausfuehrung inline
weiterfuehren (siehe "Wenn die Kette fehlt").

## Nach dem Dispatch

- **Ein Blick in den Live-Transcript belegt, dass das Kind arbeitet** (nicht
pollen, aber einmal nachsehen). Zeigt er nur `kickoff` und `start`, hat das Kind
kein Werkzeug angefasst: das ist kein Fortschritt, und sehen alle Kinder so aus,
ist die Ursache oben zu suchen, nicht in der Aufgabe.
- **`steer` landet nur an einer Werkzeug-Ergebnis-Grenze.** Ein Kind, das
zwischen Kickoff und dem ersten Werkzeugeinsatz stirbt, sieht den Steer nie
(„steer did not land“). Dann `stop` + neu dispatchen statt auf den Steer zu
vertrauen. Vor dem Neu-Dispatch pruefen, ob das tote Kind schon Dateien angefasst
hat (`git status`, Zieldateien, Zustandsdateien) — **nur** bei „vor dem ersten
Werkzeugeinsatz gescheitert“ ist ein Neustart ohne Aufraeumen sicher. Fertige
Fertige Teilarbeit eines toten Kindes wird **geborgen, nicht weggeworfen**: eine Datei,
die es vollstaendig geschrieben hat, erst pruefen (Syntax, Aufruf, Abgleich mit
dem Vorbild im Baum) und dann uebernehmen — ein Neu-Dispatch, der sie noch einmal
schreiben laesst, bezahlt dieselbe Arbeit zweimal.
- **Ein Kind stirbt gern MITTEN in einer zweiseitigen Verdrahtung — und die halbe
Haelfte meldet keinen Fehler.** Landet nur der LESER (ein Pruefer, der eine neue
Datei erwartet; ein Bericht, der ein neues Feld liest) und nicht der Schreiber,
laeuft alles gruen weiter: eine beidseitig fehlende Datei zaehlt als „gleich",
ein nirgends geschriebenes Feld als „leer". Nach dem Tod eines Kindes deshalb
nicht nur `git status` lesen, sondern jede angefasste Datei auf ihr GEGENSTUECK
pruefen — wer erwartet jetzt etwas, das niemand erzeugt? Das ist der teuerste
Rest, weil er wie Erfolg aussieht.
- **Neu dispatchen ist nach einem Tod nicht die Vorgabe.** Erst den Transcript
lesen, WORAN das Kind gestorben ist: hat es seine ganze Lebenszeit mit Lesen
verbracht und keine Zeile geschrieben, wiederholt ein zweiter Dispatch exakt
diesen Lauf — mit demselben Ausgang, wenn die Ursache am Ziel liegt. Dann gilt
die Grenzregel oben: die Sitzung haelt den Kontext laengst, also macht sie es
selbst und sagt dem Nutzer, warum. Erneut dispatchen lohnt nur, wenn das Kind an
einem Punkt starb, den ein besserer `context` verschiebt (fehlender Anker,
fehlende Umgebungsregel) — dann mit genau dieser Ergaenzung, nicht mit demselben
Brief.
- **Ergebnisse kommen zwischen den Zuegen.** Nach dem Dispatch die eigene,
unabhaengige Arbeit weitermachen und den Zug beenden; nicht auf Transkripte oder
Artefakte warten und nicht nachfassen.
- **Ein Kind erbt die Unterhaltung nicht.** Umgebungsregeln (Sandkasten vs.
Host, Einzelaufrufe statt gemischter Batches, Verbote), absolute Pfade,
Interpreter und die genaue Zielzeile gehoeren in `context` — wiederholt, wenn
mehrere Kinder sie brauchen. Ein Kind, das die Umgebungsfalle nicht kennt,
schreibt in eine Kopie, die verschwindet, und meldet trotzdem Erfolg.
- **Ein Kind erbt auch die Skills nicht, die den Auftrag regieren.** Wer eine
Aufgabe delegiert, fuer die es einen Skill gibt, muss dessen Pitfalls in den
`context` **ausschreiben** — das Kind laedt ihn nicht und kennt keine einzige
der Fallen, an denen die Sitzung gerade vorbeigekommen ist. In die Vorlage
gehoeren: das vorhandene Vorbild im Baum („bau keine dritte Variante, uebernimm
das Muster in <Datei>:<Funktion>"), die Zeilenenden der Zieldatei, die Pfade,
die ein Test **nicht** beruehren darf, die Commit-Disziplin (explizite
Pfadliste, nie `add -A`, fremde Aenderungen liegen lassen und nennen) und die
Nachweise, die das Kind vorlegen muss. Ein Brief, der nur das Ziel nennt,
produziert eine zweite Fassung derselben Regel an der falschen Stelle.
- **Migrationen mitdenken und ausschreiben.** Erweitert das Kind ein
Datenformat (Spalte, Feld, Signatur), gehoert der Umgang mit dem Altbestand in
den Auftrag: bestehende Datei migrieren, alte Eintraege ohne das neue Feld per
Rueckfall (`get` mit Vorgabe) weiterfuehren, nichts rueckwirkend schaetzen.
Sonst liefert das Kind sauberen neuen Code, der am gewachsenen Bestand bricht
oder ihn still falsch liest.
- **Kind-Berichte sind Selbstauskunft.** Bei externen Wirkungen (Commit, Upload,
Versand, Schreiben in einen fremden Baum) den Beleg selbst nachziehen — Log,
Datei, ID —, bevor „erledigt“ an den Nutzer geht.
- **Ein Kind, das mit eigenem Git-Index committet, laesst den geteilten Index
  zurueck — das ist Nacharbeit der Eltern, nicht des Kindes.** Der Weg
  `GIT_INDEX_FILE=<eigen> git read-tree HEAD && git add <pfad> && git commit`
  ist die einzige sichere Art, fremde Vormerkungen nicht mitzunehmen, und er
  hat eine Kehrseite: `.git/index` kennt den neuen Commit nicht. `git status
  --porcelain` zeigt die Kind-Pfade danach als `MM`, und wer als Naechstes aus
  dem geteilten Index committet, zieht die **Rueckabenderung** mit. Nach jedem
  Kinder-Commit daher selbst nachziehen:

  ```bash
  git reset -q HEAD -- <die pfade des kindes>
  ```

  danach `git diff --cached --numstat` — das muss leer sein (bzw. nur fremde
  Pfade zeigen). Das ist ein reiner Index-Schritt, er aendert keine Datei.
  **Ein Kind kann den geteilten Index auch zerstoeren, ohne es zu melden:**
  ein `git read-tree HEAD` OHNE `GIT_INDEX_FILE` setzt ihn auf HEAD zurueck und
  nimmt damit die Vormerkungen anderer Sitzungen weg. Deshalb im Brief nicht
  nur „nutze einen eigenen Index“ sondern „jeder git-Befehl, der den Index
  schreibt, laeuft mit gesetztem `GIT_INDEX_FILE`; im Bericht die Pfade nennen“,
  und nach dem Lauf `git status --porcelain` lesen — ein Kind, das fremde
  `M `-Eintraege verschwinden lassen hat, hat sie nicht aufgeraeumt.
- **Ein Kind, das sein Iterationslimit erreicht, hat Pflichten offen, die
  ausdruecklich im Bericht stehen muessen.** Der Status lautet dann nicht
  „fertig“, sondern „Teilfertig, Rest nicht geschafft“ — und der Rest ist meist
  eine Zustandsreparierung (Index, `git reset`, `TASKS.md`-Eintraege), die das
  Kind als letzte Zeile „Nacharbeit zwingend“ nennt. Diese Liste abarbeiten,
  BEVOR der Abschluss an den Nutzer geht: ein stehengebliebener `MM`-Zustand
  faellt der naechsten Sitzung als fremde Aenderung auf und wird dann als
  solche committet.
- **Auch BEFUNDE sind Selbstauskunft, nicht nur Wirkungen.** Ein Kind, das Code
liest und meldet "dieser Schluessel wird nirgends gelesen / dieser Wert bindet
nichts", sagt das mit Datei:Zeile-Anmutung und kann trotzdem falsch liegen. Die
Gegenprobe kostet einen Griff: das vom Kind GENANNTE Symbol ueber den ganzen
Baum suchen — ohne `head`, denn eine abgeschnittene Trefferliste ist genau das,
was ein falsches "nichts gefunden" erzeugt. Bei einem auf Fundstellen gestuetzten
Urteil zusaetzlich pruefen, ob das Kind nur den eigenen Ordner durchsucht hat
oder die tragende Stelle ganz woanders liegt. Ein ungeprueft weitergegebener
Befund wird zu deinem eigenen — und die Ruecknahme kostet mehr als der Griff.
- **Ein Kind liest einen SCHNAPPSCHUSS.** Aendert die Sitzung waehrend des Laufs
Dateien, die das Kind liest, beschreibt sein Bericht den Stand von vorher: er
zitiert dann Werte als aktuell, die laengst ersetzt sind. Vor dem
Weiterverwenden die zitierten Werte gegen die DATEI halten, nicht gegen die
Erinnerung — Aenderungen der Sitzung sind der zweite Grund, die Gegenprobe zu
fahren, neben der Fehlbarkeit des Kindes selbst.

## Externe Coding-CLIs als Ausfuehrungsagenten (opencode & Co.)

Ein externer CLI-Agent (`opencode run --model <provider/modell> "<Prompt>"`)
ist ein eigener Delegationsweg mit derselben Disziplin und eigenen Fallen:

- **Gesundheitstest VOR dem echten Auftrag, mit einem Ein-Wort-Prompt.**
  Liefert der Testmodell-Weg einen Fehler (z. B. `502` am Router-Zweig) oder
  `No active credentials for provider: <X>`, kostet der echte Lauf sonst
  erst Minuten spaeter dieselbe Meldung. Modelle durchprobieren mit kurzen
  Sonden, nicht mit dem echten Brief — und nach einem Ausfall die NAECHSTE
  Stufe derselben Familie testen, bevor man den Auftrag abbricht: der Tod
  eines Modellzweigs sagt nichts ueber die anderen.
- **Der Brief gehoert in eine DATEI, nicht in die Kommandozeile.** Der Agent
  bekommt nur den Hinweis „lies <Pfad>, das ist der VOLLSTAENDIGE Auftrag“.
  Das umgeht Aufrufgrenzen und Zitat-Eskapaden und macht den Brief
  wiederholbar fuer die Steuerungsrunde.
- **Hintergrundlauf mit Fruh-Check:** Start mit Benachrichtigung, nach 1-2
  Minuten die ersten Artefakte ansehen (Logdatei des Agents, `git status`
  im Zielordner). Erscheint nichts und das Agent-Log zeigt Stream-Fehler,
  den hängenden Lauf per Kommandozeilen-Muster beenden und das Ersatzmodell
  starten — nicht minutenlang auf einen toten Lauf warten.
- **Der Abschlussbericht ist nach zwei Beweisen NICHT Glaubenssache, sondern
  ein Pruefplan.** Gemessen lief ein Agent „Tests 10/10 gruen“ (real: ein
  Importfehler, weil ein Paket fehlte), „Datei X angepasst“ (real: `git diff`
  leer) und rief eine Funktion auf, die es nicht gibt — sein eigener Log
  zeigte es. Nach jedem Agent-Lauf: die Suite SELBST fahren, die behaupteten
  Dateiaenderungen per `git status`/`git diff` halten, jede behauptete
  Integration gegen den Quelltext greppen, und `git log` pruefen (der Agent
  committet entgegen der Anweisung und nimmt fremde uncommittete Arbeit im
  Index mit). Erst der eigene Lauf ist der Beleg.
- **Regeln, die der Agent brechen soll, gehoeren als PRUEFBARER Vertrag in
  den Brief** („kein Commit“, „keine Netzaufrufe in Tests“, „Sperrenkette
  unangetastet“) — und als Nachweis in der Review-Liste: `git log` seit dem
  Start, `git diff --numstat` der behaupteten Dateien, die Suite selbst.
  Ein Brief allein haelt keinen Agenten an die Regel.

## Ein fertiges Kind, das nur die Antwortform verfehlt

Ein Kind mit `output_schema` kann die ARBEIT abgeschlossen haben (Datei geschrieben,
Zahlen ermittelt) und trotzdem am Antwortvertrag scheitern: der Validator weist die
Prosa ab, das Kind bekommt die Aufforderung, NUR JSON zu senden — und statt
umzuformatieren faengt es von vorn an, bis die aeussere Frist es erschlaegt. Von
aassen sieht das wie ein Fehlschlag aus; auf der Platte liegt der Befund laengst.

- **Fuer Datei-Lieferungen kein `output_schema` verlangen.** Wer einen Bericht, eine
  Tabelle oder eine Messreihe als Artefakt will, beschreibt die erwartete Ausgabe in
  Prosa ("Antworte mit: Pfad, Kennzahlen, Urteil"). Ein Schema auf einem Auftrag mit
  Prosa-Werkzeugen erzeugt genau diese Schleife.
- **Vor jedem Neu-Dispatch den Baum lesen.** Nach dem Abbruch zuerst Zieldateien und
  Transkript (`cache/delegation/live/<id>/task-N.log`) pruefen: existieren Bericht
  und Zahlen schon, werden sie geborgen, gegen die Artefakte geprueft und nur der
  Rest ergaenzt. Neu dispatchen bezahlt dieselbe Arbeit ein zweites Mal.
- **Ein Kind kann versionierte Dateien geloescht haben.** Beim Aufraeumen nach einem
  Abbruch `git status` nach `D`-Eintraegen ansehen: ein Kind, das seine Hilfsdatei
  "wieder entfernt", trifft manchmal eine gleichnamige Datei aus dem Repo. Diese
  eine Datei zurueckholen, den Rest der Scratch-Spur loeschen.
- **Die Frist gehoert zum Auftrag.** Ein Auftrag mit echten Backtests oder
  Serienlaeufen dauert schnell 20-30 Minuten. Steckt der Absender in einer harten
  Grenze (Bot-Bruecken wie der SkillsBot kappen nach 30 Minuten, `-q`-Aufrufe,
  Werkzeug-Timeouts), stirbt der ganze Kinderbaum mit — also vorher in Teilstuecke
  schneiden, die je unter der Grenze bleiben, und das Ergebnis als DATEI abliefern
  lassen statt als Antwort.

## Ein Kind, das sein Ausgabebudget im Nachdenken verbrennt

Fehlerbild: `status=failed`, `Response remained truncated after 4 continuation
attempts`, als Teilausgabe nur „No visible answer was produced — the model hit
its output-token limit on every continuation attempt; its reasoning consumed the
entire budget each time“. Das Kind hat gelesen, gearbeitet, aber nichts
geschrieben — auf der Platte ist nichts passiert.

**Das ist ein AUFTRAGSfehler, kein Kettenfehler.** Gegenprobe, die das trennt:
lief im selben Lauf ein anderer Batch ueber DIESELBE Kette sauber durch, liegt es
an der Aufgabe, nicht am Ziel. Also nicht die Kette reparieren, sondern den
Brief.

- **Der Ausloeser ist eine offene ENTSCHEIDUNG im Auftrag.** Ein Goal der Form
  „baue X so, dass es zu Y passt“ laesst das Kind die Konstruktionsfrage selbst
  waegen — und ein Modell, das im `think`-Kanal denkt, verbraucht dort sein
  ganzes Ausgabebudget, bevor eine Zeile Code entsteht. Beleg: zwei Kinder
  starben so, waehrend ein drittes mit mechanischem Auftrag („messen, auflisten“)
  durchlief.
- **Die Entscheidung gehoert in den `context`, nicht ins Kind.** Wer die
  Konstruktion schon kennt (oder sie in zwei Minuten selbst entscheidet),
  schreibt sie als Anweisung hin („haenge die Eintraege an die BESTEHENDE Zeile,
  das Feld heisst `befehle`, Form `{was, cmd, hinweis, start}`“) und laesst das
  Kind nur noch ausfuehren. Ein Auftrag mit „entscheide, wie“ ist teurer als
  einer mit „setze um“.
- **Kein zweiter identischer Dispatch.** Der Lauf wiederholt sich (dasselbe
  Lesen, dieselbe Entscheidung, dasselbe Ende) und kostet nur Budget. Entweder
  den Brief um die Entscheidung ergaenzen oder inline selbst machen — die
  Grenzregel „ein Kind liest von Null“ greift hier fast immer.
- **Ein so gestorbenes Kind hat nichts angefasst.** Vor dem Urteil trotzdem
  `git status` lesen: es belegt, dass nur gelesen wurde, und macht den
  Inline-Weg risikofrei.

## Ein aufloesender Modellname ist noch kein taugliches Modell

Die Kette kann technisch stehen und trotzdem unbrauchbar sein: ein kleines
lokales Modell (8B, 8k Kontext) endet mit `status=completed`, ruft aber **kein
einziges Werkzeug** auf und liefert erfundenen Text. Ursache: System-Prompt plus
Werkzeugbeschreibung fuellen das Kontextfenster bereits, fuer die Aufgabe bleibt
nichts. Ein groesseres Kontextfenster allein loest das nicht — wer eine
mehrstufige Werkzeugkette braucht, nimmt ein Modell mit genug Kapazitaet dafuer;
beim Router ist das der Coding-Alias (`auto/best-coding`), der auf ein
Cloud-Modell zeigt, waehrend das lokale Modell fuer Einzelschritte ohne
Werkzeugkette bleibt.

- **`delegation.model` aendern wirkt ohne Neustart** — der Gateway liest die
Config zur Laufzeit. Kein Grund, den laufenden Dienst anzufassen; das gehoert
in `hermes-config-ops` (dort auch die Falle, dass `hermes config set` ohne
`HERMES_HOME` eine **andere** `config.yaml` trifft als die, die der Gateway
liest).
- **Nachweis mit vorher selbst ermittelten Referenzwerten.** Vor dem Dispatch
die erwarteten Werte unabhaengig bestimmen (Zeilenzahl, Feldwert, Dateiname)
und den Kinderbericht dagegen stellen. `status=completed`, eine Laufzeit und
eine API-Call-Zahl sagen **nichts** ueber Erfolg: der genannte Fall sah mit
`completed`/90 s/3 Calls wie ein Erfolg aus und hatte die Aufgabe komplett
verfehlt. Erst wenn die genannten Werte mit den eigenen uebereinstimmen, ist
die Kette als benutzbar belegt.

## Wenn die Kette fehlt

Ohne erreichbares Ziel ist Delegation blockiert — das ist kein Grund, die Arbeit
liegen zu lassen. Den Blockierenden klar benennen (Zeile, Ziel, Fix, und was der
Nutzer tun muss, wenn es ein Zugang ist) und die Aufgabe selbst erledigen. „Mit
mehreren Agenten“ ist Mittel, nicht Zweck; ein selbst gebauter Beleg schlaegt
einen wartenden Batch.

## Abgrenzung

- Hermes' eigene Konfiguration (Provider-Kette, `delegation`-Block): `hermes-config-ops`
- A2A-Peers und SkillsBot: `a2a-telegram-skills`
