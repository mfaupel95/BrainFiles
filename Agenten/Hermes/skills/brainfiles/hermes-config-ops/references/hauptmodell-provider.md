# Das Hauptmodell auf einen anderen Provider umstellen

Gilt fuer den `model:`-Block — also fuer den Hauptlauf. **Es gibt keinen
Modell-Schalter je Plattform:** Gateway, A2A-Bruecke und der SkillsBot bedienen
alle das `default`-Profil und lesen genau diesen Block. Ein A2A-`served_agents`-
Eintrag (Adapter `_load_served_agents`, `platforms.a2a.extra.agents`) kann nur ein
anderes PROFIL bedienen, und ein frisches Profil ist eine Insel ohne die
Haus-Skills. Wer „nur den Bot" umstellen will, muss das wissen, bevor er schreibt —
sonst behauptet er eine Trennung, die es nicht gibt.

1. **Den Zielprovider zuerst finden, nicht erfinden.** Ein Block unter `providers:`,
   den nichts referenziert, ist tote Konfiguration — aber oft genau der gemeinte
   (`providers.<name>.models.<modell>.context_length` nennt die erwartete
   Fenstergroesse). Vor dem Setzen die Live-Metadaten des Dienstes holen
   (`curl -s <base_url>/models`, bzw. `/api/tags` bei Ollama) und die Zahl gegen die
   Anforderung halten: was der Dienst meldet, gilt, nicht was in der Config steht.
2. `hermes config set model.provider <neu>` und `model.default <modell>`, dann
   `model.base_url` explizit auf den Endpunkt des neuen Providers. Der Providerwechsel
   **leert `model.base_url` und `model.api_mode` von selbst** und sagt das in der
   Ausgabe („that route belonged to <altersprovider>") — diese Zeile lesen, nicht
   ueberfliegen: ohne neu gesetztes `base_url` zeigt der Aufruf ins Leere.
   Bei einem selbst benannten Provider zusaetzlich `providers.<name>.base_url` und
   `providers.<name>.api_mode` setzen (die `api:`-Zeile allein reicht nicht).
3. **Reserve dahinter, nicht davor.** Den lokalen Eintrag als LETZTES Glied der
   `fallback_providers`-Kette eintragen (siehe `references/fallback-kette.md`) und den Cloud-Eintrag
   davor lassen: der lokale Zweig soll den Ausfall ueberbruecken, nicht den
   Normalbetrieb tragen.
4. **Ein selbst benannter Provider erscheint im Protokoll als `provider=custom`.**
   Das ist kein Widerspruch und kein Beleg gegen die Umstellung — nur die
   `model=`-Angabe zaehlt hier.

**Beweis am lebenden Dienst, ohne Neustart** (gilt fuer jede Oberflaeche, die ueber
den Gateway laeuft): eine Nachricht ueber den A2A-Endpunkt schicken und danach die
Logzeile lesen, die Modell und Provider nennt —

      curl -s http://127.0.0.1:9900/ -H "Authorization: Bearer <A2A-Token>" -H 'Content-Type: application/json' \
        -d '{"jsonrpc":"2.0","id":1,"method":"SendMessage","params":{"message":{"messageId":"m1","role":"ROLE_USER","parts":[{"text":"Antworte nur mit PONG"}]}}}'
      grep -oE "model=[^ ]+ provider=[^ ]+ .*platform=a2a" logs/agent.log | tail -3

Die Zeile muss das neue Modell UND `platform=a2a` tragen; ein Werkzeugaufruf im
selben Auftrag (z. B. `hostname`) belegt zusaetzlich, dass die Route auch
Werkzeugschleifen faehrt, nicht nur Prosa. Danach ist auch der Bot-Weg bewiesen —
kein Prozessneustart, kein „muesste jetzt greifen".
