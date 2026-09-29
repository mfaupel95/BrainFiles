# Einzelne Plattform mit eigener SKILL.md anbinden

Rezept fuer den Auftrag "lies <URL> und melde dich dort an", wenn die Plattform ihre
Anleitung selbst als `SKILL.md` ausliefert (Bootstrap-Datei + Kind-Skills je
Faehigkeit). Die Haus-Skill-Bibliothek bleibt unberuehrt.

## 1. Lesen und einordnen

- Hauptdatei holen, dann die Kind-Skills fuer die Faehigkeiten, die gebraucht werden.
- Ein Kompatibilitaets-Alias derselben Datei (z. B. `/SKILL.md` neben `/skill/<name>`)
  ist dieselbe Anleitung — einmal lesen, Byte-Gleichheit pruefen, nicht zweimal deuten.
- Die Datei nennt meist: Basis-URL, Registrierung/Login, Aktivitaets-Endpunkt
  (Heartbeat), Nachrichten-/Aufgabenweg, dazu optionale Module (Marktdaten, Wettbewerbe).
  Nur was dort steht, wird aufgerufen.

## 2. Ablage

```
Agenten/Handel/<plattform>/
  .env                     AI4TRADE_EMAIL / _PASSWORD / _TOKEN  (gesperrt via **/.env)
  skill/SKILL.md           Hauptdatei
  skill/<modul>/SKILL.md   Kind-Skills
```

- Die Kennung liegt als Datei NEBEN den Skill-Dateien, nie darin, nie in einer Notiz.
- `git check-ignore -v <pfad>` gegenpruefen: `.env` muss ignoriert sein, die
  `.md`-Kopien duerfen liegen bleiben (Fremdtext, kein Eigenanteil).
- `Wissen/Zugaenge.md` ist die Ablage von Max; sie zu lesen ist gesperrt. Das
  Nachtragen der Werte dort als offenen Punkt eintragen, nicht selbst tun.

## 3. Registrieren und verifizieren

Registrierung mit dem dokumentierten Endpunkt (Beispielform, Plattformnamen ersetzen):

```python
import json, secrets, string, urllib.request, pathlib
pw = ''.join(secrets.choice(string.ascii_letters + string.digits + '-_') for _ in range(32))
body = json.dumps({'name': NAME, 'email': MAIL, 'password': pw}).encode()
req = urllib.request.Request(BASIS + '/api/claw/agents/selfRegister', data=body,
                             headers={'Content-Type': 'application/json'})
d = json.loads(urllib.request.urlopen(req, timeout=45).read().decode())
tok = d.get('token') or (d.get('data') or {}).get('token')
pathlib.Path('.env').write_text(
    f'<PLATTFORM>_EMAIL={MAIL}\n<PLATTFORM>_PASSWORD={pw}\n<PLATTFORM>_TOKEN={tok}\n',
    encoding='utf-8')
print('OK name=', d.get('name'), 'id=', d.get('agent_id'), 'token_laenge=', len(tok))
```

- **Ausgegeben werden nur Adresse, Name, ID, Laenge** — nie der Antwortkoerper im
  Ganzen und nie das Token. Bei Fehler `HTTPError` fangen und nur `e.code` plus die
  ersten Zeichen der Fehlermeldung zeigen.
- Danach ZWEI Aufrufe: `GET .../me` (liest Name/Konto/Rechte) und der
  Aktivitaets-Endpunkt. Beide mit `Authorization: Bearer <token>` aus der `.env`.
- Beim zweiten Aufruf dieselbe Regel: nur die gebrauchten Felder drucken
  (`d['name']`, `d['cash']`, `d['message_count']`), nie `json.dumps(d)`.

## 4. Bericht und offene Punkte

- Wiki-Seite unter `Wiki/Werkzeuge/<plattform>.md`: Endpunkte, Ablage der Kennung,
  gemessener Stand (IDs, Kontostand, Antwortzeiten), **was nicht angeschlossen ist**
  (fehlendes Polling, keine Signale veroeffentlicht).
- `Wiki/INDEX.md` und `Archiv/TASKS.md` im selben Arbeitsschritt nachziehen.
- Fuer die Registrierung selbst gibt es keinen Waechter: das ist ein einmaliger
  Schritt. Der Wachbedarf entsteht erst beim Polling (Cron mit leerer Ausgabe =
  nichts senden, Muster siehe `dauerprozess-bewachen`).

## Fallen

- **Antwort eines Auth-Endpunkts nicht roh ausgeben.** Genau der Verifikationsaufruf
  ist die Falle: er bestaetigt die Kennung, indem er sie zurueckgibt.
- **Die FEHLERantwort ist die gefaehrlichere Haelfte davon.** Eine Validierungsantwort
  (422) echot die ganze Anfrage unter `input` zurueck - E-Mail UND Passwort im
  Klartext. Im Fehlerpfad nur `e.code` und das Feld `detail` lesen, nie den ganzen
  Koerper; ist es doch passiert, gehoert das Passwort auf der Plattform geaendert
  (Aufgabe fuer Max eintragen) - das Sitzungsprotokoll ist derselbe Leak wie ein Commit.
- **Der Auth-Kopf der Anleitung ist ein Vorschlag.** Gemessen: der Plattform-Skill
  nennt `X-Claw-Token`, die API antwortet damit 401 `Invalid token`; tragfaehig ist
  `Authorization: Bearer <token>`. Zuerst den dokumentierten Kopf probieren, bei 401
  den Standardkopf gegentesten und den Befund in die Wiki-Seite schreiben - NICHT die
  Kennung neu ausstellen, solange nicht beide Formen 401 liefern.
- **Den Poller als duenne Bruecke in `Agenten/Hermes/scripts/` legen.** Der Scheduler
  fuehrt nur Skripte aus diesem Ordner aus; ein Cron auf
  `Agenten/Handel/<plattform>/heartbeat.py` wird beim Anlegen abgewiesen. Die Logik
  bleibt beim Werkzeug (dort liegt auch die `.env`), die Bruecke laedt `main()` ueber
  den Pfad und wird selbst wieder still, wenn nichts Neues anliegt.
- **Plattform-Konto ist kein Boersenkonto.** Solche Seiten arbeiten mit simuliertem
  Guthaben; die Kennung gehoert trotzdem in die gesperrte Ablage, weil sie die Identitaet
  des Agenten ist.
- **Poller testen, ohne ins Netz zu gehen - der Patch muss zurueckgestellt werden.**
  Die Aufruffunktionen im Test auf Modulebene ersetzen UND in `tearDown`/`addCleanup`
  wiederherstellen: ein Patch, der stehen bleibt, laesst die NAECHSTE Testklasse die
  echten Endpunkte aufrufen - der Test bleibt dabei gruen, und Kennung samt
  Fehlermeldung wandern ins Protokoll. Zwei kleinere Fallen derselben Art: ein
  Parameter `env` nur mit `if env is None` auswerten (ein absichtlich leerer Wert
  faellt bei `env or _env()` still auf die ECHTE Umgebung zurueck), und den Merkordner
  des Pollers im Test auf ein tmp-Verzeichnis zeigen lassen - ein Test, der in den
  echten `cache/`-Ordner schreibt, legt dort eine Datei ab, die niemand mehr aufraeumt.
- **Fremde `install`-Pfade aus der Anleitung nicht ausfuehren** (`~/.claude/skills/...`,
  `~/.openclaw/skills/...`): hier laedt niemand daraus.
