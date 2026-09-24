# Andere Modalitaeten als Chat: Bilder ueber den Router

Der Router ist nicht nur anthropic-kompatibel — er bedient auch
`/v1/images/generations`. Ein Fremdwerkzeug mit dem OpenAI-SDK laesst sich
deshalb per `OPENAI_BASE_URL=http://127.0.0.1:20128/v1` + Inferenz-Schluessel
auf den Router zeigen (gleiche Umstellung fuer jeden OpenAI-kompatiblen Client).

## Katalog ist nicht Verbindung

`/v1/models` und `model_capabilities` tragen die LiteLLM-Liste ALLER Anbieter —
Bildmodelle fuer azure, vercel, poe, fastrouter usw. stehen dort auch ohne Konto.
Wahrheit sind allein die Zeilen in `provider_connections` (`is_active`,
`test_status`). Faehigkeit aus dem Katalog immer gegen die Verbindungsliste
joinen, bevor ein Modell zugesagt wird.

Welche Anbieter eine Modalitaet ueberhaupt koennen:

```sql
select provider, count(*)
from model_capabilities
where lower(modalities_output) like '%image%'
group by provider;
```

Der Haus-Stand ist duenn: aktiv sind meist nur ein Abo-Verteiler (Chat) und
`ollama-local` (Chat) — eine Bildroute kann dort niemand bedienen.

## Eine Verbindung kann eine leere Huelle sein

`auth_type=apikey` mit `length(access_token)=0` ist kein eingerichteter
Anbieter; ein Aktivieren aendert nichts, und Guthaben fehlt genauso. Nur
Laenge/Zustand vergleichen, den Wert nie ausgeben.

## Die Verdrahtung beweisen, ohne etwas zu schreiben

Das Werkzeug seinen EIGENEN Aufruf fahren lassen, mit `OPENAI_BASE_URL` +
`OPENAI_API_KEY` nur in der Prozessumgebung dieses Testlaufs. Kommt die
Fehlermeldung des UPSTREAM zurueck (z. B. die Warteschlangen-Antwort von AI
Horde), ist der Weg belegt — und keine `.env` wurde angefasst. Achtung: ein
Router-Fehler allein beweist nur, dass die Anfrage ankam; der Router antwortet
auf `/v1/images/generations` auch mit 401 statt 404, wenn nichts dahinter steht.

## Umschaltgrenze

Nicht umschalten, solange dahinter nur ein langsamer oder toter Weg liegt. Der
Router bricht einen langsamen Upstream nach seinem eigenen Budget ab
(`504 … budget 597s left`), waehrend eine Gratis-Crowd-Warteschlange 20-25 min
betraegt. Ein Werkzeug, das seinen Anbieter nach ANWESENHEIT eines Schluessels
waehlt, verliert dann seinen funktionierenden lokalen Weg (Skill
`fremd-agenten-betrieb`, `references/lokale-bildkette.md`). Umschalten erst,
wenn ein zahlender Anbieter wirklich hinter der Route steht — vorher als
vorbereitete, in einer Sitzung ausfuehrbare Umstellung dokumentieren.

Routen erzeugt kein Guthaben: ein Verteiler vor einem erschoepften Schluessel
aendert die Absage nicht. Erst Guthaben/Abrechnung beim Anbieter, dann der
Router davor.
