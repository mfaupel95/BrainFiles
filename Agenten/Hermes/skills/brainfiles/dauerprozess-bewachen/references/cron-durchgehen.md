# Cron-Bestand durchgehen: Triagerunde und die Fehler, die `last_status` nicht zeigt

Der Auftrag „geh die Cronjobs durch und repariere sie" hat zwei Sorten Befund:
rote (`last_status: error`) und die viel gefaehrlicheren **still gruenen**. Das
Dokument ist die Runde; die Reihenfolge ist so, dass kein Befund ungeprueft in
den Bericht wandert.

## Die Runde

1. `Agenten/Hermes/cron/jobs.json` laden. **Zwei Ebenen unterscheiden:** der Job
   liegt unter `jobs`, und `schedule` ist ein **DICT**, kein Cron-String. Die
   Mehrzahl der Jobs traegt `{"kind": "interval", "minutes": 15}` — nur
   wenige ein `{"kind": "cron", "expr": "..."}`. Wer den Takt aus `expr` liest,
   findet bei 71 Jobs genau EINE und schliesst daraus „alles haengt".
2. **Nach `last_status` gruppieren**, nicht nach Ausgabe: `ok` / `error` /
   kein `last_run_at`. Letzteres heisst bei einem `no_agent=False`-Job mit
   fester Uhrzeit **nichts**, sondern „erstes Lauf steht noch aus" — erst
   `next_run_at` und `schedule.kind` lesen, dann urteilen.
3. **Skript-Zuordnung je Job pruefen**: `os.path.basename(jobs[...]["script"])`
   muss in `Agenten/Hermes/scripts/` existieren. Das Feld nimmt NUR den
   Dateinamen — ein Pfad oder ein Argument darin wird nie uebergeben, und der
   Job laeuft dann mit der Vorgabe des Nachbarn oder gar nicht. Ein Job kann
   so laden und trotzdem „ok“ melden.
4. **Der eigentliche Befund ist der Takt.** `last_status: ok` bedeutet nur:
   der LETZTE Lauf ging. Gemessen wird das Alter von `last_run_at` gegen den
   EIGENEN Takt (`interval.minutes`, bei `cron` die groebste Periode aus
   `expr`) — Flag bei mehr als dem 2,5-fachen. Zusaetzlich `next_run_at`: liegt
   es weit in der Vergangenheit und ist der Job `enabled`, haengt der Ticker.
   Zwei Marken `cron/ticker_heartbeat` und `cron/ticker_last_success`
   unterscheiden „Ticker arbeitet“ von „Ticker laeuft, Jobplanung haengt“.
5. **Rot = Fehlerzeile lesen, dann den Exitcode deuten.** Ein Exitcode im Cron,
   den der Handaufruf nicht zeigt, ist zuerst eine **Unterschiedsfrage der
   Umgebung**, kein Fehler im Skript: beide Wege fahren, beide Ausgaben
   vergleichen. Erst danach wird repariert.
6. Je Fehler: `sqlite3 cron/executions.db` — Tabelle `executions`
   (`job_id`, `started_at`, `finished_at`, `status`, `error`) und
   `cron_incidents` (Vorfallsfolge bis `resolved`). Die **Laufdauer** je Job
   ist das Beste an dieser Diagnose; danach suchen (unten).

## Muster, die man nicht am Fehlertext erkennt

### Eine wachsende Laufzeit ist Akkumulation, nicht Stoerung

Wenn die Dauer je Lauf **monoton steigt** statt zu schwanken (41 s, 70 s,
234 s, 325 s, 349 s), ist das kein Rauschen und keine Last — es zaehlt etwas
auf. Der Aufrufer legt am Anfang einen Lauf in einer Tabelle an und beendet
ihn am Ende; wird er vorher gekillt, bleibt die Zeile offen, und der naechste
Lauf stoesst darauf.

```sql
SELECT id, kind, started_at FROM runs WHERE finished_at IS NULL ORDER BY started_at;
```

Gemessen: 95 offene Zeilen, der aelteste 99,9 Stunden alt, aus jedem
abgebrochenen Lauf — jeder erzeugte den naechsten (etwa vier pro Stunde). Die
Einzelschritte des Skripts liefen zusammen 39 s, der Cron meldete 349 s. **Zwei
Fixes, nicht einer:** die offenen Zeilen schliessen (sonst wartet der erste Lauf
nach dem Timeout-Fix wieder) und die Frist anheben. Die Frist allein laesst die
Akkumulation weiterlaufen.

Gegenprobe: jeden Unterbefehl **einzeln** mitlaufen und die Dauer messen, statt
die Summe des Skripts zu behaupten. Wer die Einzelschritte nicht misst, weiss
nicht, ob die Frist zu knapp oder der Zustand zu gross war — beides fuehrt zur
falschen Reparatur. Nach dem Schliessen der offenen Zeilen fiel derselbe
Unterbefehl von 349 s auf 5 s; das ist der Beweis, dass die Zeit **im Zustand**
saß, nicht in der Arbeit.

### Die Frist steht meist im Skript, nicht im Cron-Job

Ein Timeout-Feld am Job zu setzen ist wirkungslos, wenn die Zahl im Skript
steht: `subprocess.run(..., timeout=frist)` mit einem Modulstandard oder einem
Parameter beim Aufruf liest die Job-Konfiguration nie. **Vor der Reparatur
greppen, WO die Frist steht** (`grep -n "timeout" <skript>`), und dort aendern.
Andernfalls steht nach dem Fix ein Vermerk in `jobs.json`, den niemand liest —
das sieht wie eine Konfiguration aus und aendert nichts.

### Ein Exitcode, den nur der Cron zeigt, ist eine Umgebungsfrage

Exit 15 im Job, Exit 0 von Hand, gleiches Skript, gleicher Tag. Bevor am
Skript gedreht wird: beide Wege fahren und die Ausgaben vergleichen. Oft
schlaegt der Watchdog-Prozess in der Scheduler-Umgebung in ein Working-Dir,
ein fehlendes Netz oder eine Prozessgrenze, die es von Hand nicht gibt. Ohne
den Vergleich repariert man ein Skript, das nie das Problem war.

**Exit 15 heisst SIGTERM, nicht Skriptfehler.** Unter MSYS/Git-Bash liefern
`timeout N` und der Bash-Job-Abbau 15 (bzw. 143); die Windows-Kommandos
(`taskkill`, `Stop-Process`, `os.kill`) erzeugen 15 **nie**. Steht dort 15,
ist der Lauf von aussen beendet worden — die richtige Antwort lautet „Abbruch",
nicht „Skript kaputt". Wer die Zahl sieht, faengt an, im Skript zu suchen, was
gar nicht dort steht.

### Zwei Datenquellen dieselbe Frage gestellt: der Zaehler stimmt, die Erzaehlung luegt

Ein Repo-Aktualitaetsbericht nennt pro Klon den Rueckstand **und** „lokal /
upstream“. Wenn beide Zeitstempel **identisch** sind, liest die zweite Zeile den
lokalen Zweig:

```python
git log -1 --format=%ci <zweig>                       # FALSCH: lokaler Zweig
git log -1 --format=%ci refs/remotes/upstream/<zweig>  # richtig
```

Der Rueckstandszaehler bleibt dabei korrekt — nur die Erzaehlung daneben ist
die lokalen Daten. **Identische Zeitstempel in einer Gegenueberstellung sind
die Signatur, dass beide Seiten dieselbe Quelle lesen.** Derselbe Fehler in
angepasster Form: ein Nachkommastellen- oder Einheitenformat ist ein echter
Datenfehler, wenn es sich systematisch um eine feste Groesse handelt.

## Reihenfolge der Reparatur

**Die Runde endet mit Fixes, nicht mit einer Frage.** „geh die Cronjobs durch
und repariere sie“ heisst reparieren. Wenn eine Ursache nicht auffindbar ist,
wird sie benannt — und **der Rest wird trotzdem behoben**, statt alles liegen
zu lassen. Eine Triagerunde, die mit drei Befunden und „soll ich fixen?“ endet,
hat die Haelfte geliefert, die man bestellt und fuer die man bezahlt.

- Offene Zustandszeilen schliessen **vor** der Frist-Erhöhung.
- Frist anheben **nach** der Einzelmessung, nicht nach dem Cron-Symptom.
- Eine inhaltlich falsche Ausgabe (Zeitstempel, Beschriftung) wird behoben,
  auch wenn der Job „ok“ meldet — der Job lief, er log nur das Falsche.
- Jeden Fix mit **zwei** Läufen belegen: der erste zeigt den Befund, der
  zweite die Ruhe. Danach `last_status` und `next_run_at` frisch lesen, statt
  den Erfolg aus dem Job-Objekt von vorher zu zitieren.

## Merksatz

> Ein gruener Cron-Job ist eine Aussage ueber den letzten Lauf, nicht ueber den
> naechsten. Die Rechnung, die etwas sagt, ist **Alter gegen eigenen Takt** —
> und eine Dauer, die von Lauf zu Lauf waechst, zaehlt Zustand auf, den
> jemand liegen gelassen hat.