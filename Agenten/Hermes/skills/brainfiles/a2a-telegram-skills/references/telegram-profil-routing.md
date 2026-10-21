# Telegram: Themen, profile_routes und welche Kennung zu welchem Bot gehoert

Tiefe zu den Regeln im SKILL.md. Alles hier ist LESEND ermittelbar - kein
getUpdates, kein Testschuss in den Chat.

## 1. Welcher Bot ist welcher (ohne Token auszugeben)

Der SkillsBot ist NICHT der Hermes-Hauptbot. Er hat eine eigene Kennung; sie
steht als Windows-Benutzervariable (Registry-Rueckfall wie in `_variable()`):

```python
import json, urllib.request, winreg
def var(name):
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, r'Environment') as k:
                v, _ = winreg.QueryValueEx(k, name)
                if v:
                    return v
        except OSError:
            continue
with urllib.request.urlopen('https://api.telegram.org/bot%s/getMe' % tok, timeout=15) as r:
    print(json.load(r)['result']['username'])
```

Ergebnis hier: `@HermesAgentMaksPCbot` (Skills_Bot_Hermes), Token-Name
`SKILLSBOT_TOKEN`, 46 Zeichen. Variablen stehen NICHT in `Agenten/Bus/.env` -
die Datei ist leer, `_variable()` liest die Registry.

Warum nur `getMe` und niemals `getUpdates`: ein zweiter Poller am selben Token
stiehlt dem laufenden Gateway Nachrichten (`terminated by other getUpdates
request`) und damit Order-Freigaben. `getMe` und `sendMessage` sind unkritisch.
Chat- und Themen-IDs liest man aus `gateway.log` / `state.db`, nicht aus der API.

## 2. Echte `thread_id`s finden

```python
import sqlite3
c = sqlite3.connect('file:Agenten/Hermes/state.db?mode=ro', uri=True)
for r in c.execute("select session_key, thread_id, chat_type from sessions "
                   "where chat_id like '%<chatid>%' and thread_id is not null"):
    print(r)
```

- DM- und Gruppensitzungen tragen die Thread-ID als LETZTES Segment des
  `session_key` (`agent:main:telegram:dm:<chat>:<thread>`).
- Zusaetzlich im Log: `topic loaded from config: <chat>:<Name> -> thread_id=<n>`.  
  ACHTUNG: diese Zeile zeigt nur, was in der config STEHT, nicht was Telegram
  vergeben hat.
- Die Spalte `sessions.updated_at` gibt es NICHT - ein `order by updated_at`
  faellt mit `no such column` um. Vorhanden sind u.a. `id`, `source`,
  `session_key`, `chat_id`, `chat_type`, `thread_id`, `model`.

## 3. Anatomie eines Befunds "Themen fehlen"

Drei Zeugen, alle lesbar, keiner raet:

1. `Agenten/Hermes/config.yaml` → `platforms.telegram.extra.dm_topics` nennt
   Name + `thread_id` je DM-Thema.
2. `logs/gateway.log` → `Cannot create DM topic '<Name>' in chat <chat>: Threaded
   Mode is not enabled …` (mit Anleitung: BotFather-Mini-App → My bots → Bot
   Settings → Threads Settings). Tritt der Satz auf, sind die IDs aus (1)
   Platzhalter.
3. `state.db` → keine Sitzung traegt eine dieser IDs.

Alle drei zusammen = die Themen existieren nicht, das Thema-Routing ist
wirkungslos, und der einzige Weg zum Fachbot ist ein Befehlswort.

## 4. YAML-Form einer Route

```yaml
  profile_routes:
    - name: gruppe-handel-1999      # freier Name, nur fuer die Logzeile
      platform: telegram
      chat_id: '-1003980261765'     # IMMER als String, fuehrende -1 bleibt
      thread_id: '1999'             # nur wenn es das Thema wirklich gibt
      profile: jev-trader           # muss in served_profiles stehen
      enabled: true
```

- Es gibt kein CLI-Kommando fuer `profile_routes` (`hermes gateway` kennt nur
  run/ensure/start/stop/restart/status/install/…). Also Textersatz in der
  Datei - und dabei die Zeilenenden der Datei erhalten (die Hermes-config ist
  CRLF, `hermes config set` schreibt LF und schneidet Kommentare ab).
- Nach dem Edit: Gateway neu starten (`schtasks /run /tn "Hermes_Gateway_2ef9d0b7"`
  oder `hermes gateway restart`) und `gateway_state.json` lesen.

## 5. Wer empfaengt was - der haeufigste Denkfehler

Eine Route sagt, WER antwortet, nicht WER sonst noch erreichbar ist. Mehrere
Bots pro Thema gibt es nicht; die uebrigen bleiben ueber die direkte Adresse
(`NAME: Auftrag`) erreichbar. Wer die Doku liest, findet dort oft eine
Wunschzuordnung ("Handel → jev-trader") - die config kann etwas anderes sagen.
Immer beide lesen und den Widerspruch melden, nicht eine Seite glauben.
