# Telegram-Bus — Entwurf (Teilprojekt 1: Bus und Anbindung)

Stand: 2026-09-09
Pfad-Ziel des Moduls: `Agenten/Bus/`
Erste Ausbaustufe: Ereignisse einsammeln und den Puls melden. Abruf, Steuerung
und Deutung sind ausdrücklich **nicht** Teil dieser Stufe.

## Zweck

Jeder Agent und jeder Bot meldet, dass er gelaufen ist und was dabei herauskam.
Ein einziger Dienst sammelt diese Meldungen, schreibt sie fort und schickt über
Telegram nur das, was auffällig ist — plus einmal täglich eine Sammelmeldung.

Heute ist der Stand: `Agenten/Handel/melder.py` ist ein vollständiger
Telegram-Kanal (senden, empfangen, Chat-ID-Allowlist, Token aus HKCU), aber nur
vier Stellen nutzen ihn — `dauerlauf.py`, `beobachte_live.py`,
`tagesbericht.py`, `verbesserer/auswerter.py`. Alles andere arbeitet stumm.

## Umfang

**Drin:**

- Handelsspuren unter `Agenten/Handel/`: xperp, orb, scanner, dca, grid,
  verbesserer, dauerlauf.
- Die Routinen in `Agenten/Routinen/` (~25 PowerShell-Skripte).
- Die drei Sicherungsskripte `sichern.ps1`, `sichern-zweitkopie.ps1`,
  `sichern-ausser-haus.ps1`.

**Draußen:** Hermes und die MCP-Server. Fremdcode bzw. Dauerprozesse; dort ginge
nur „läuft / läuft nicht", das trägt den Aufwand nicht.

## Zerlegung

Das Gesamtvorhaben zerfällt in drei Teilprojekte mit je eigener Spec, eigenem
Plan, eigener Umsetzung:

1. **Bus und Anbindung** (diese Spec) — Dienst, Journal, alle Erzeuger, Puls.
2. **Abruf und Steuerung** — `/lage`, `/log`, `/bericht`, `/hinweise`,
   `/pause`, `/lauf`, Freigabefenster, Datei statt Text bei langen Ausgaben.
3. **Deutung** — der Bus leitet aus den Journaldaten eigene Empfehlungen ab.
   Sachlich das, was `verbesserer/` für Spur 1 schon tut; braucht einen eigenen
   Durchgang, damit es nicht beiläufig entsteht.

## Rahmen (unverhandelbar)

- `melder.py` bleibt **unverändert**. Er ist der Fahrweg zu Telegram; diese
  Stufe ändert nur, wer ihn aufruft.
- Die Grenze aus `melder.py` gilt weiter: über Telegram kommt höchstens eine
  Freigabe herein, nie ein Betrag, nie ein Hebel, nie ein Instrument. Diese
  Stufe nimmt überhaupt nichts entgegen — sie meldet nur.
- Der Bus führt nichts aus. Ein Ereignis annehmen ist Schreiben, kein Auslösen.
- **Ein toter Bus darf niemals einen Lauf abbrechen.** Diese Regel steht über
  jeder Meldegenauigkeit.
- Keine absoluten Pfade in Code oder Konfiguration (`CLAUDE.md`,
  `Wissen/Portabilitaet.md`). Absolute Pfade existieren allein in den
  Registrierungen der Aufgabenplanung.

## Aufbau

Drei Teile unter `Agenten/Bus/`:

### `bus.py` — der Dienst

HTTP auf `127.0.0.1:8787`, nur an localhost gebunden, kein Weg nach außen. Der
Port steht in `Agenten/Bus/bus.json`, damit Erzeuger und Dienst dieselbe Zahl
lesen. Nimmt `POST /ereignis` entgegen.

Die Reihenfolge ist bindend:

1. Zeile an `Agenten/Bus/journal/JJJJ-MM-TT.jsonl` anhängen und flushen.
2. Erst danach an die Sprecher-Warteschlange geben.

Fällt der Dienst zwischen Annahme und Telegram aus, steht das Ereignis trotzdem
auf Platte, und der nächste Start holt es nach. Das ist die Gegenmaßnahme zum
einzigen echten Nachteil eines Dienst-Busses.

### `ereignis.py` / `Ereignis.ps1` — die Erzeugerseite

Je ein Dreizeiler pro Sprache.

- Python: Kontextmanager `with ereignis.lauf("handel/xperp"): ...` — meldet
  Start, Ende, Dauer und eine durchgereichte Ausnahme von selbst.
- PowerShell: `Melde-Start` / `Melde-Ende` aus `Ereignis.ps1`, dot-sourced.

Beide feuern gegen `localhost` mit 1 s Zeitlimit und **stiller Aufgabe bei
Misserfolg**. Kommt der Bus nicht ans Telefon, schreibt der Erzeuger die Zeile
ersatzweise selbst ins Journal; der Sprecher findet sie beim nächsten Durchgang.

### `sprecher.py` — die einzige Stelle, die meldet

Liest die Warteschlange und das Journal, entscheidet was auffällig ist, fasst
zusammen, drosselt, ruft `melder.py`. Erzeugt außerdem einmal täglich die
Sammelmeldung „wer lief, wie lange, was kam raus".

Wie weit er gekommen ist, merkt er sich in `Agenten/Bus/stand.json` (zuletzt
gemeldete `id` je Tag). Nach einem Neustart liest er das Journal ab dieser
Marke weiter — so wird nichts doppelt gemeldet und nichts übersprungen.

## Datenmodell

Ein Ereignis ist immer dieselbe Zeile:

| Feld | Bedeutung |
|---|---|
| `id` | eindeutig je Ereignis; trägt die Entdopplung |
| `zeit` | ISO-8601, lokale Zeit mit Zeitzone |
| `wer` | `handel/xperp`, `routine/sicherung`, `sicherung/ausser-haus` … |
| `was` | `start`, `ende`, `hinweis` |
| `code` | Ergebniscode; `null` bei `start` und `hinweis` |
| `dauer_s` | Sekunden; `null` bei `start` |
| `text` | ein Satz Klartext |
| `log` | Pfad zum Rohprotokoll, relativ zur Wurzel; darf `null` sein |

`log` ist bewusst dabei, damit `/log` in Teilprojekt 2 nichts suchen muss.

## Datenfluss

```
Erzeuger --POST--> Bus --schreibt+flusht--> journal/*.jsonl
                    |
                    +--Warteschlange--> Sprecher --> melder.py --> Telegram

Bus tot:  Erzeuger --schreibt selbst--> journal/*.jsonl
                                              |
                                    Sprecher findet beim nächsten Durchgang
```

Es gibt genau **einen** Ort der Wahrheit — das Journal. Der Bus ist nur der
schnelle Weg dorthin.

## Anbindung der Erzeuger

Pro Komponente zwei Zeilen und ein `finally`. Bewusst **kein** zentraler
Wrapper, der die Skripte aufruft: der würde die Registrierungen in der
Aufgabenplanung umschreiben, und genau die enthalten die absoluten Pfade, die
nach einem Umzug ohnehin die empfindlichste Stelle sind
(`Wissen/Portabilitaet.md`). Rund 35 mechanische Kleinänderungen sind billiger als
ebenso viele neu registrierte Aufgaben.

## Auffälligkeit

Die Regeln stehen in einer Datei (`Agenten/Bus/auffaellig.json`), nicht im Code:

- Ergebniscode ≠ 0.
- Dauer über dem Zweifachen des Median der letzten zehn Läufe derselben
  Komponente.
- Ein Lauf, der zur erwarteten Zeit ausbleibt.
- Jedes `hinweis`-Ereignis.

Alles andere sammelt sich still und erscheint erst in der Tagesmeldung.

## Fehlerfälle

| Fall | Verhalten |
|---|---|
| Bus tot | Erzeuger schreibt selbst, Lauf geht weiter. Nie ein Abbruch. |
| Telegram tot | Journal ist geschrieben, Sprecher versucht später erneut. Kein Verlust. |
| Zwei Busse | PID-Datei wie bei `dauerlauf.py`; der zweite beendet sich. Zwei Sprecher am selben Token nähmen sich gegenseitig die Nachrichten weg — davor warnt `handel-dauerlauf.ps1` bereits. |
| Doppelte Zeile | Bus nahm an *und* Erzeuger schrieb; der Sprecher entdoppelt über `id`. |
| Flut | Sprecher fasst zusammen und deckelt auf 20 Nachrichten je Stunde (Wert in `auffaellig.json`), statt in ein Telegram-Limit zu laufen. |
| Journal nicht schreibbar | Bus antwortet mit Fehler und meldet einmalig; Erzeuger geht trotzdem weiter. |

## Sicherheit

Der Bus lauscht nur auf `127.0.0.1` und hat keinen Schlüssel — jeder lokale
Prozess kann melden. Das ist hingenommen: das Schlimmste ist eine erfundene
Journalzeile. Der Telegram-Token bleibt allein im Sprecher; der Bus kennt ihn
nicht. Der Bus führt nichts aus.

## Betrieb

Der Dienst läuft als Aufgabe „bei Systemstart" in der Windows-Aufgabenplanung
mit Neustart bei Fehler — dieselbe Schiene wie die übrigen Routinen
(`Wissen/Routinen.md`), kein neuer Mechanismus. Registrierung mit
`Register-ScheduledTask`, weil `schtasks` kein „Starten, sobald möglich" setzt.

## Prüfung

Testgetrieben, mit temporärem Journalpfad statt echtem Telegram:

- Bus schreibt vor dem Verteilen: Abbruch unmittelbar nach dem Schreiben → die
  Zeile ist da.
- Erzeuger fällt bei totem Bus sauber auf Direktschreiben zurück und wirft
  nicht.
- Entdopplung über `id` greift.
- Die Auffälligkeitsregeln als Tabelle von Fällen.
- `Ereignis.ps1` meldet `ende` auch, wenn das Skript in der Mitte scheitert.
- Ende-zu-Ende gegen einen Melder-Doppelgänger, der statt zu senden
  protokolliert.

## Fertig, wenn

- Alle Komponenten aus „Umfang" melden Start und Ende.
- Ein erzwungener Fehler in einer Routine erscheint innerhalb einer Minute auf
  dem Handy.
- Ein gestoppter Bus lässt einen Sicherungslauf unbeschädigt durchlaufen, und
  die Zeile steht danach trotzdem im Journal.
- Die Tagesmeldung listet alle Läufe des Tages.
