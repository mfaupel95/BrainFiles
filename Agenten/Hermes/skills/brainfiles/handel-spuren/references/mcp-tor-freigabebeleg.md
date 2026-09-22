# Ein MCP-Werkzeug, das handeln darf — ohne die Sperrenkette zu umgehen

Ein MCP-Server wird aus JEDER Sitzung aufgerufen: Chat, Bot, A2A-Nachricht.
Seine Werkzeuge sind damit aus dem Nichts scharf. Die Haus-Sperrenkette
(Freigabefenster, Herzschlag, Deckel, Stop, Kill-Switch, Journal) haengt aber am
**Skript der Spur**. Deshalb gilt: der Boersen-MCP bleibt lesend — und wenn er
doch ausfuehren soll, bekommt er genau EIN Tor.

## Aufbau: die Entscheidung bleibt bei der Spur, der MCP ist nur die Hand

```
Spur (unter ihren Wachen)  --stellt aus-->  Freigabe-Beleg  --liest-->  MCP-Werkzeug fuehrt aus
```

Der Beleg darf NUR von der Spur ausgestellt werden, und nur solange
`freigabefenster.offen(spur)` gilt UND `handel_erlaubt` true ist. Beides zu
pruefen ist kein Beiwerk, sondern der Kern: ein Chat kann kein Fenster oeffnen
(`freigabefenster.oeffnen()` verweigert ohne wartende Anfrage, und die stellt
nur der laufende Dauerlauf), also kann er sich auch keine Erlaubnis ausstellen.

Felder des Belegs und warum jedes da ist:

| Feld | Zweck |
|---|---|
| `kennung` | einmalig, wird beim Ausfuehren verbraucht |
| `spur` / `seite` | ein Beleg fuer LONG ist kein Beleg fuer den Ausstieg |
| `paar` | schuetzt vor der Order im falschen Markt |
| `menge` (Hoechstmenge) | verhindert eine groessere Order als beschlossen |
| `preis_max` / `preis_min` | Kauf nicht ueber, Verkauf nicht unter der Rechnung |
| `gueltig_bis` | kurz (Minuten) — eine Hand, kein Dauer-Schluessel |
| `verbraucht` | Einmaligkeit, auch wenn das Protokoll nicht geschrieben wurde |

Fail-closed in jede Richtung: fehlend, unlesbar, abgelaufen, verbraucht, falsche
Spur/Seite/Paar, zu gross, zu teuer = **Absage mit Grund**. Nie ein Ersatzwert,
nie eine stille Ausnahme.

## Die Gegenrichtung muss AUCH zu sein

Ein neues Tor nuetzt nichts, solange die alten Wege offen bleiben:

- **Der alte Orderweg des MCP wird abgeschaltet**, nicht nur dokumentiert:
  das bestehende Werkzeug lehnt `echt_ausfuehren=True` ab und verweist auf das
  Beleg-Werkzeug (sonst existiert ein zweiter, ungegateter Weg auf denselben
  Schluessel).
- **Der Sammelstorno wird gesperrt** ("all"), Einzelstorno bleibt erlaubt: ein
  Sammelstorno nimmt den Schutz-Stop einer offenen Position mit und
  hinterlaesst eine nackte Position. Risiko kuerzen ist erlaubt, Risiko
  entfernen nicht.
- **Ausstiege haengen NIE am Beleg.** Stop, Ziel und Notaus laufen ueber den
  eigenen Orderweg der Spur. Wer sie hinter das Tor stellt, verriegelt den
  Notausstieg.

## Beim Laden zweier Tor-Module: Cache-Schluessel nach PFAD

Ein Nachbarmodul ueber `importlib` zu laden ist Hausmuster (siehe pitfall 34).
Der Eintrag in `sys.modules` muss aber den **Pfad** enthalten:

```python
schluessel = "%s@%s" % (name, os.path.abspath(pfad))
if schluessel in sys.modules:
    return sys.modules[schluessel]
```

Mit dem blanken Namen teilen sich zwei Ordner einen Eintrag: wer zuerst laedt,
bestimmt fuer den GANZEN Prozess, aus welchem Ordner das Modul kommt. Symptom im
Test: das zweite Testmodul bekommt die Instanz aus dem im `tearDown` geloeschten
Temp-Ordner und meldet `No such file or directory` aus einem Pfad, den der Test
nie angelegt hat. Im Betrieb waere es die falsche Fenster-/Regeldatei.

## Nachweis, der zaehlt

1. **Werkzeugliste am laufenden Server abfragen** (stdio, JSON-RPC
   `initialize` + `tools/list`) — nicht der Datei glauben: die neuen Werkzeuge
   muessen in der Liste stehen. Laufende Serverprozesse halten alten Code im
   Speicher; sie zu beenden genuegt, der Client startet sie beim naechsten
   Aufruf mit dem neuen Code.
2. **Ohne Beleg wird der Netzaufruf GAR NICHT gemacht**: im Test die private
   Transportfunktion durch einen Recorder ersetzen und `assertEqual(aufrufe, [])`
   pruefen. Ein abgelehnter Auftrag, der trotzdem sendet, ist der teure Fehler.
3. **Mit Beleg: `validate` fehlt im echten Fall** (der Pruefmodus ist nur ein
   Schalter im Rumpf), der Beleg ist danach verbraucht und eine Protokollzeile
   existiert. Trockenlauf laesst den Beleg stehen.
4. **Regelwerk nachziehen** (`Wissen/Handelsregeln.md`) und den Werkzeug-README:
   die Regel "der MCP bleibt lesend" wird zu "lesend mit genau einem Tor", sonst
   liest die naechste Sitzung die alte Fassung als Wahrheit.

## Bericht an Max

Das Tor ist eine Faehigkeit, kein Schalter: nach dem Bau ist NICHTS scharf.
Sagen, was noch fehlt (ein Aussteller in einer Spur — Beleg-Aussteller sind der
naechste Schritt), und dass Ausstiege weiter frei bleiben. Keine Option-Liste;
eine Entscheidung mit einer Zeile Konsequenz.
