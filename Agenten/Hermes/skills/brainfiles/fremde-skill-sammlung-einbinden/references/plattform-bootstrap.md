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
- **Plattform-Konto ist kein Boersenkonto.** Solche Seiten arbeiten mit simuliertem
  Guthaben; die Kennung gehoert trotzdem in die gesperrte Ablage, weil sie die Identitaet
  des Agenten ist.
- **Fremde `install`-Pfade aus der Anleitung nicht ausfuehren** (`~/.claude/skills/...`,
  `~/.openclaw/skills/...`): hier laedt niemand daraus.
