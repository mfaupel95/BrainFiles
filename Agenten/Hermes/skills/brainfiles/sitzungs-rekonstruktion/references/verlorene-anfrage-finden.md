# Die verlorene Anfrage finden (Wiederholbefehl aufloesen)

Fuer Nachrichten, die keinen eigenen Inhalt tragen — „retry", „nochmal", „Continue",
„mach weiter" — und fuer die Frage „was war der letzte Auftrag, der nicht lief?".
Ergebnis ist IMMER: der Wortlaut des Auftrags, der Beleg, dass er nie ausgefuehrt wurde,
und die Angabe, welche Sitzung ihn inzwischen fuehrt.

## 1. Ueberblick: welche Sitzungen gibt es gerade

```python
import sqlite3, datetime
c = sqlite3.connect("file:Agenten/Hermes/state.db?mode=ro", uri=True)
for sid, titel, quelle, t in c.execute(
        "SELECT id,title,source,started_at FROM sessions ORDER BY started_at DESC LIMIT 20"):
    print(datetime.datetime.fromtimestamp(t).strftime('%d.%m %H:%M'), quelle, sid, titel)
```

- `title` = erste Nutzer-Nachricht der Sitzung; sie benennt den Strang sofort.
- `source` trennt die Wege: `telegram`, `cli`, `tui`, `kanban`, `a2a`, `oneshot`.
- `bg_<HHMMSS>_<hash>` ist eine **Hintergrundsitzung** des Gateways. Sie entsteht, wenn
eine Nachricht eintrifft, waehrend die Hauptsitzung des Kanals beschaeftigt ist. Mehrere
koennen gleichzeitig laufen — dieselbe Person, derselbe Auftrag, getrennte Verlaeufe.

## 2. Den verlorenen Auftrag finden

```python
for sid, i, inhalt, t in c.execute(
        "SELECT session_id,id,content,timestamp FROM messages "
        "WHERE role='assistant' AND content LIKE 'Your request was not processed%' "
        "ORDER BY id DESC LIMIT 10"):
    print(datetime.datetime.fromtimestamp(t).strftime('%d.%m %H:%M'), sid, i)
```

Die `role='user'`-Zeile mit der naechstkleineren `id` **in derselben Sitzung** ist der
Auftrag. Nicht die letzte Zeile der Sitzung nehmen: nach der Fehlzeile kann der Nutzer
laengst etwas anderes getippt haben.

Faustregeln zur Zeile:

- Sie ist die Standardantwort auf einen **fehlgeschlagenen Modellaufruf** (Provider weg,
Zeitlimit, Kontingent) — der Auftrag wurde also nie ausgefuehrt, nicht halb ausgefuehrt.
- Die Nutzer-Nachricht bleibt in der DB stehen. Ein Wiederholbefehl, der sie nicht nennt,
ist trotzdem eindeutig: es ist die letzte unverarbeitete.
- Laeuft die Sitzung danach weiter (spaetere Zeilen, API-Aufrufe), hat sie den Auftrag
womoeglich selbst wieder aufgenommen — dann nachsehen statt selbst neu anfangen.

## 3. Zweiter Zeuge: die Protokolle

`logs/gateway.log` (Zustellung, Routing, Kanal):

    inbound message: platform=telegram user=... msg='<text>' reply_to_id=None
    Transient agent failure in session <id> — persisting user message so conversation
      context is preserved on retry
    response ready: platform=... session=... time=<s> api_calls=<n> response=<n> chars
    Agent cache idle-TTL evict: session=agent:main:telegram:dm:<chat> (idle=<s>s)

`logs/agent.log` (Turns und Modellaufrufe):

    [<session>] agent.turn_context: conversation turn: session=... model=...
      provider=... platform=... history=<n> msg='<text>'
    [<session>] agent.conversation_loop: API call #<n>: ... latency=...s

- **Damit ist die Lebendigkeit messbar**, auch wenn die DB nichts Frisches zeigt: eine
`API call`-Zeile mit Zeitstempel der letzten Sekunden heisst, die Sitzung arbeitet
gerade. `history=0` plus frischer Turn heisst: neue Sitzung, aber der Faden liegt in
einer anderen.
- `Transient agent failure ... persisting user message` ist der Beleg, dass eine
Nachricht zum Wiederholen vorgemerkt wurde.
- Vor dem Suchen im Checkout: `rg` statt `grep -r` (ein `grep -r` ueber den
Hermes-Checkout laeuft in den Werkzeug-Timeout).

## 4. Haengende Schleife von offener Aufgabe trennen

Symptom: dieselbe Sitzung endet im festen Takt (Minuten) wieder mit „Your request was
not processed", ohne dass ein Mensch etwas getippt hat. Dann ist der Nutzer-Text eine
**Maschinen-Aufforderung** („[Continuing toward this kanban task — judge says it is not
done yet]" o.ae.) und die Ursache steht im Protokoll:

    Provider has been unresponsive (no response received) for 5 consecutive stale
      attempts — aborting this call to avoid an indefinite stall.
    goal judge: API call failed (Request timed out.) — falling through to continue

- Das ist **kein Auftrag, den man wiederholen kann** — wiederholen verbraucht nur weitere
Takte. Gehoert als Befund in den Bericht (welche Karte/welcher Worker, welches Modell,
seit wann) und wird beendet, nicht neu gestartet.
- Ein `kanban dispatcher: reaped N zombie worker(s)` im `gateway.log` zeigt, dass die
Aufraeumung selbst schon greift — den Worker also nicht von Hand nachstarten.

## 5. Bevor gehandelt wird

1. Fuehrt eine andere Sitzung den Auftrag schon? (`MAX(timestamp)` je Sitzung, plus
   frische `API call`-Zeilen im Protokoll.)
2. Hat sie das Ergebnis schon geliefert? Dann **unabhaengig nachpruefen** und ihren
   Bericht als Behauptung behandeln, nicht als Beleg.
3. Beruehrt der Auftrag Schalter mit echter Wirkung — Live-Handel, Freigaben,
   Loeschungen, Massenlaeufe — **nicht** selbst ausfuehren. Messen, berichten, den einen
   Schritt benennen, den nur der Nutzer tun kann. Zwei Sitzungen an denselben Schaltern
   erzeugen doppelte Orders bzw. doppelte Loeschungen.
