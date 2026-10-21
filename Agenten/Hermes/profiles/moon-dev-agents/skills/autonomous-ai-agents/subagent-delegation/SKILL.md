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
