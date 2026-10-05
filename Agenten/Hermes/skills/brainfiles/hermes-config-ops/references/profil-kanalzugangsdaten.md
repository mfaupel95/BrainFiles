# Kanalzugangsdaten je Profil (Telegram, Photon, ...)

Ein Telegram-/Photon-Token gehoert genau EINEM Profil. Traegt ein weiteres Profil
dieselbe Verbindungskennung, warnt `hermes profile list` je Profil; ein zweites
Gateway auf demselben Token nimmt dem ersten die Nachrichten weg (beide pollen
`getUpdates`), und `hermes gateway migrate --multiplex` verweigert, solange die
Dopplung steht.

## Wer entscheidet, was eine Kanalzeile ist

`hermes_cli/profile_channels.py`. Es gibt KEIN Unterkommando, das Kanaele aus
einem BESTEHENDEN Profil entfernt — nur `profile create --clone` strippt beim
Anlegen. Die Zuordnung selbst ist Bibliothek:

- `ChannelKeyIndex(source_dir).platform_for(<ENV_NAME>)` liefert die Plattform
  oder `None`. `source_dir` ist der Geltungsbereich (das Startprofil), weil
  Adapter dort entdeckt werden — ohne ihn prueft man den falschen.
- Erkannt werden: die von Adaptern deklarierten Schluessel, `<PLATFORM>_`-Praefixe
  samt historischer Aliase, die Gateway-weite Kanalpolitik
  (`GATEWAY_ALLOW_ALL_USERS`, `GATEWAY_ALLOWED_USERS`) und Praefixe, die sich ein
  Adapter mit einem WERKZEUG teilt (`HASS_`, `TWILIO_`, `EMAIL_`) — letztere nur,
  wenn das Startprofil diesen Adapter wirklich faehrt.
- Deshalb keine eigene Schluesselliste bauen: sie ist entweder zu kurz (geteilte
  Nebenzeilen bleiben stehen) oder zu lang (ein Werkzeugschluessel faellt mit).

## Ablauf

1. **Trockenlauf** je Profil: welche Zeilen fallen weg — und welche Kanalzeilen
   ausdruecklich NICHT angefasst werden.
2. **Sichern:** je Profil `<datei>.bak-JJJJMMTT` (git-ignoriert ueber `*.bak-*`).
3. **Schreiben:** nur die erkannten Zeilen entfernen, alles andere Byte fuer Byte
   behalten. Zeilenenden ZUERST feststellen und erhalten
   (`splitlines(keepends=True)` + `"".join(...)`) — die Bibliotheksfunktion
   `strip_channel_env_file()` schreibt die Datei mit `\n` neu und dreht eine
   CRLF-Datei still auf LF um.
4. **Gegenprobe:** Sicherung zuruecklegen → die Warnungen muessen zurueckkommen,
   erneut strippen → 0 Warnungen. Das belegt Ursache UND Ruecknahme in einem Lauf.
5. **Unveraendert nachweisen:** den Hash der Datei des Startprofils vorher/nachher
   vergleichen — sie traegt die Zugangsdaten und darf sich nicht bewegen.

Werkzeug im Haus: `Agenten/Hermes/scripts/profil-kanaele-bereinigen.py`. Aufruf
aus dem Checkout mit dessen venv, damit Import und Umgebung stimmen:

    cd Agenten/Hermes/hermes-agent
    venv/Scripts/python.exe ../scripts/profil-kanaele-bereinigen.py            # Trockenlauf
    venv/Scripts/python.exe ../scripts/profil-kanaele-bereinigen.py --anwenden
    venv/Scripts/python.exe ../scripts/profil-kanaele-bereinigen.py --zuruecknehmen

## Nachweisen, ohne zu lecken

Ein `diff` gegen die Sicherung gibt die Geheimnisse im Klartext aus. Fuer den
Beleg „genau diese Zeilen" den Diff redigieren (`sed -E 's/=.*/=<wert>/'`) oder
mit Zeilenzahlen und Hashes arbeiten. Die Warnzahl aus `hermes profile list` ist
selbst ein Beleg und braucht keinen Datei-Diff.

## Ein Bot braucht eine EIGENE Modellkennung

Profile sind Inseln: sie lesen nur ihr eigenes `auth.json` und `.env`, nie die
des Startprofils. Kanalzugangsdaten braucht der `/bot`-Weg des SkillsBot NICHT
(er startet `hermes -p NAME chat -q`, ohne Gateway) — eine Modellanmeldung schon.
Reihenfolge der Diagnose, bevor der Kanal verdaechtigt wird:

1. `auth.json` des Profils: existiert sie, und steht der Provider unter
   `providers`? Fehlt der Eintrag, meldet der Lauf „not logged into Nous Portal";
   ein gefuellter `credential_pool` ersetzt ihn nicht.
2. Modell gegen die Mindestgroesse: ein kleines lokales Modell scheitert mit
   „context window ... below the minimum" — der Lauf kommt dann gar nicht zum
   Provider.
3. Erst danach den Kanal pruefen.
4. **Echter Test des Weges, den der SkillsBot geht:** aus `Agenten/Bus`
   `skillsbot._bot_fragen('<profil>', 'Antworte mit genau: OK')` — derselbe
   Aufruf wie bei `/bot`, nur ohne Telegram.

## Modellkennung: auf den lokalen Router zeigen statt die Konto-Anmeldung kopieren

Ein Bot-Profil, das „not logged into Nous Portal" meldet, hat keinen `providers`-Eintrag
im eigenen `auth.json`. Zwei Wege — einer davon ist eine Falle:

- **Kopieren (nicht nehmen):** die Portal-Anmeldung des Startprofils in 25 Profile
  schreiben. Das ist dieselbe Kennung in vielen Dateien (die Fehlerklasse, die bei
  Telegram/Photon gerade aufgeraeumt wurde), und eine geteilte Refresh-Sitzung kann allen
  Profilen gleichzeitig ablaufen.
- **Auf den Router zeigen (nehmen):** `model.provider=omniroute`,
  `model.default=auto/best-coding`. Den Schluessel traegt jede Profil-`.env` schon, den
  Provider-Block jede `config.yaml`; der Router ist ein lokaler Dienst und muss laufen.
  Kein `providers`-Eintrag im `auth.json` noetig, kein Duplikat. Ein veraltetes
  `model.base_url` auf den Anbieter dabei entfernen (`hermes config unset model.base_url`),
  sonst steht dort eine zweite Wahrheit.

Werkzeug im Haus: `Agenten/Hermes/scripts/bot-modell-auf-router.py` (Trockenlauf ohne
Argument, `--anwenden`, `--zuruecknehmen`). Es laesst unberuehrt, was eine eigene
Portal-Anmeldung hat, und meldet je Profil den Grund.

## Eine Einstellung ueber alle Profile ziehen

1. **Je Profil `config.yaml.bak-JJJJMMTT`** (git-ignoriert ueber `*.bak-*`).
2. **Schreiben per `hermes config set` mit `-p <name>`**, ein Aufruf je Wert,
   `HERMES_HOME` gesetzt, `PYTHONHOME`/`PYTHONPATH` entfernt. Rund 15 s je Profil: 25
   Profile sind ein Hintergrundlauf mit Logdatei, kein einzelner Foreground-Aufruf.
   Der Lauf ist idempotent — schon umgestellte Profile werden uebersprungen, ein
   abgebrochener Lauf ist wiederholbar.
3. **Der Kommentar-Schluss der Profil-Config geht dabei verloren** (references/fallen.md, Fallen).
   Danach die Ziel-Fassung byte-genau aus `git show HEAD:<pfad>` bauen und nur den
   geaenderten Block ersetzen — das raeumt auch gemischte Zeilenenden aus einem frueheren
   Schreibvorgang weg.
4. **Je Datei pruefen, nicht in der Summe:** `git diff --numstat <datei>` muss die Zeilen
   der gewollten Ersetzung zeigen (Beispiel: 2/3), jede Datei mit `yaml.safe_load` parsen
   und die Zielwerte asserten.
5. **Stichprobenartig live belegen** statt alle Profile zu rufen: je ein Profil, das vorher
   kaputt war, plus eines, dessen Datei am staerksten umgebaut wurde —
   `hermes -p <name> chat -q "Antworte nur mit dem einen Wort: fertig" -Q`.
6. **Im Bericht trennen:** was umgestellt wurde, was ausdruecklich unberuehrt blieb (Profile
   mit eigener Anmeldung, lokale Provider) und wie die Ruecknahme lautet (`--zuruecknehmen`).

## Listen-Schluessel im Profil: Block schneiden statt `config set`

`hermes config set` kann keinen EINZELNEN Listeneintrag aendern — bei
`fallback_providers` bleibt nur die ganze Liste oder ein Blockschnitt. Ein ungueltig
gewordener Eintrag (lokales Modell unter der Mindest-Kontextgroesse) wird deshalb
byte-genau entfernt: die Zeile in Spalte 0 plus die eingerueckten Folgezeilen, dabei die
Datei VORHER und NACHHER mit `yaml.safe_load` parsen und asserten, dass alles ausserhalb
des Schluessels gleich geblieben ist. Eine EINGERUECKTE Kette (z. B. unter `delegation:`)
bleibt dabei stehen, und `fallback_providers: []` ist schon sauber — die beiden Formen
nicht verwechseln, `grep '^fallback_providers:'` findet beide. Werkzeug im Haus:
`Agenten/Hermes/scripts/bot-rueckfallkette-bereinigen.py` (Trockenlauf, `--anwenden`,
`--zuruecknehmen`). Regeln und Fallen: references/fallback-kette.md, Abschnitt „Fallback-Kette und lokale
Provider".

## Ein NEUES Kanal-Profil: drei Tore, alle drei messen

Ein angelegtes Profil mit `.env` und `SOUL.md` ist noch kein laufender Bot.
`hermes profile list` fuehrt es bereits als `running`, obwohl kein Prozess davon
existiert - die Liste liest die Served-Liste des Gateways, nicht die Wirklichkeit.
Vor der Meldung "fertig" diese drei Dinge getrennt pruefen:

1. **Der Kanal ist ueberhaupt eingeschaltet.** Ein Adapter startet nur mit
   `platforms.<plattform>: {enabled: true}` in der Profil-Config. Fehlt der Block
   ganz (nicht `enabled: false`), startet nichts - unabhaengig davon, ob die
   `.env` vollstaendig gefuellt ist.
2. **Die Zugangsdaten stehen drin - und es ist ein EIGENER Bot.** Ein Token kann
   nicht an zwei Profilen haengen (`acquire_scoped_lock` verhindert das aktiv);
   der Hauptbot der `.env` ist fuer ein zweites Profil unbrauchbar. Ein
   `.env`-Geruest mit Werten im Format `NAME = <wert>` und einem Kommentar
   darueber ist eine VORLAGE, kein Eintrag - vor jeder Aussage ueber Kanalbereit-
   schaft Namen und Laengen zeigen, nie den Wert.
3. **Die Hilfsmodelle sind gesetzt.** `auxiliary.compression` fehlt in einem
   frischen Profil; der Lauf bricht dann mit "context window below the minimum
   64.000" ab (references/auxiliary-kompression.md).

Fehlt eine dieser drei Voraussetzungen, ist das ein Befund und keine
Nachlassigkeit: jede der drei pruefen, jeden einzeln mit seinem Werkzeug
belegen, und die offene Frage stellen, **bevor** gebaut wird - ein Bot-Token
haengt am BotFather des Nutzers und ist nicht selbst erstellbar.

### `gateway.multiplex_profiles: false` ist KEIN viertes Tor

Diese Zeile wird leicht zum vermeintlichen Kanal-Blocker, weil ein
Multiplex-Gateway, das 20+ Profile in `served_profiles` fuehrt, im Profil-Check
wie ein Widerspruch aussieht. Er ist keiner:
`hermes_cli/gateway_multiplex_mode.py::resolve_multiplex_mode` loest ein
explizites `false` **wie ein unset** auf - gewarnt wird, multiplexed wird
trotzdem. Der Rueckfall ist nicht optimistisch: haelt ein echter Blocker (ein
s6-Container, ein sekundaeres Profil mit eigenem Gateway, eine doppelte
Bot-Kennung), startet der Host solo und **sagt im Log warum**. `false`
aufzusetzen ist damit eine zweite Wahrheit ohne Wirkung.

Der echte Kanal-Blocker ist die **fehlende Credential im Profilscope**.
`_platform_has_bot_credential` (`gateway/run.py`) liest nur `token`/`api_key`
aus der Profil-Config bzw. `extra` - **nie `os.environ`**. Ohne Token meldet der
Gateway `[MULTIPLEX] Profile 'X': skipping <plattform> - no bot credential in
this profile's secrets` und ueberspringt den Kanal. Diese Logzeile ist das
zuverlaessigste Signal fuer "Kanal aus, Token fehlt"; sie steht im Gateway-Log
und nicht in der Profil-Config.

## Ein von Hand eingetragener Token: drei Tore, und keines davon ist der Kanal

Sobald der Nutzer den Token selbst eingetragen hat, ist "es passiert nichts" die
wahrscheinlichste Meldung - und sie hat drei getrennte Ursachen. In dieser
Reihenfolge messen, weil jede spaetere Messung eine fruehere als gegeben
voraussetzt.

**Tor 1: Ist es ueberhaupt der richtige Bot?** Beide Token (Startprofil und
neues Profil) mit `getMe` befragen und die `username` vergleichen. Der
Nutzer schreibt dem vertrauten Bot; ein zweiter Bot, der nur durch seinen
Anzeigenamen aehnelt, sieht nichts, weil er nie eine Nachricht bekommen hat.
Ein `getMe`-Vergleich beantwortet das in zwei Sekunden und ohne Geheimnis
auszugeben.

**Tor 2: Hat der Bot ueberhaupt je etwas empfangen?** `getUpdates` aufrufen.
Null Eintraege heisst: der Bot hat vom Nutzer noch nichts bekommen - das ist
kein Defekt, sondern der Normalfall fuer einen frisch angelegten Bot, und es
bleibt es, bis der Nutzer ihm zum ersten Mal schreibt. Ein neuer Bot sieht
ausserdem nichts, was **vor** seiner Erstellung geschrieben wurde.

**Tor 3: Passt die Nutzerkennung?** `getChat` ist als Probe **unbrauchbar**:
Telegram beantwortet es fuer einen privaten Chat mit `400 chat not found`,
solange keine Nachricht existiert - auch bei einer vollstaendig richtigen ID.
Nicht als Fehlerbericht verwenden.

Der Wert wird von Hand eingetragen, also ist die Frage nach seiner Form vor
dem Wertvergleich zu stellen. Ohne ihn auszugeben pruefen:

- **Zeichenart je Position**, nicht den Wert: ist jeder Zeichen ein `-` oder eine
  Ziffer? Ein haengender Punkt am Ende einer zehnstelligen Nummer ist die
  haeufigste Kopierpaste-Marke und sieht in jeder Laengen- und Hash-Ausgabe
  vollstaendig gesund aus.
- **Laenge gegen eine bekannte Referenz** aus einer anderen Datei desselben
  Nutzers (`strlen` vergleichen, nie den Inhalt). Zwei Ziffernfolgen desselben
  Nutzers muessen gleich lang sein.
- **Vergleich ueber Normalisierung** (`rstrip('.')`): stimmt die bereinigte
  Fassung mit dem Referenzwert ueberein, ist der Fund die Ursache.

Die Kombination ist das Belegbare: Formfehler gefunden, Referenzwert stimmt
nach Normalisierung, `getUpdates` leer. Der Nutzer entscheidet dann ueber das
Korrektieren - ein `.env`-Wert wird nicht ueberschrieben, auch wenn er mit
hoher Wahrscheinlichkeit falsch ist.

## Was in eine leere Kanalzeile gehoert

Bevor der Nutzer eine leere `.env`-Zeile fuellt, die Bedeutung in einem Satz
und die **Form des Werts** nennen - die Frage kommt, und sie kommt vor dem
Warten. Fuer Telegram heisst das:

- `TELEGRAM_BOT_TOKEN` - der einzige Wert, der sich pro Profil unterscheidet.
- `TELEGRAM_ALLOWED_USERS` - wer dem Bot schreiben darf; im privaten DM die
  Nutzerkennung.
- `TELEGRAM_HOME_CHANNEL` - Ziel-Chat fuer **Cron-Zustellung**
  (`cron/scheduler_delivery.py`, registriert vom Adapter als
  `cron_deliver_env_var`). Ohne Wert findet ein geplanter Job keinen
  Empfaenger. Im privaten DM mit dem Nutzer ist das dieselbe Zahl wie oben; eine
  Gruppe hat eine negative ID und braucht zusaetzlich eine Gruppen-Politik,
  sonst ignoriert der Adapter die Gruppe.

Den Leser im Code zu benennen ist hier Pflicht: "steht in der Doku" ist keine
Belegkette, ein Dateipfad mit Funktion ist eine.

## Wenn der Zieltext nur in uncommitteter Fremdarbeit steht

Die Skill-Bibliothek unter `Agenten/Hermes/skills/` kann uncommittete Aenderungen
anderer Sitzungen tragen. Wer dort ergaenzt, committet nur die eigene Aenderung
(`git add -p`). Existiert der Zieltext in `HEAD` gar nicht — weil der ganze Absatz
selbst uncommittete Fremdarbeit ist —, ist ein Teil-Commit nicht moeglich: die
Ergaenzung bleibt im Arbeitsbaum (sie wirkt sofort, Skills werden von der Platte
geladen) und wird im Bericht als unversioniert benannt, statt fremde Arbeit
mitzucommitten.

---

## Vollstaendiger Abschnitt aus dem SKILL.md-Rumpf

# Kanal-Zugangsdaten gehoeren genau einem Profil (Telegram, Photon, ...)


1. **Ein Bot-Token, ein Profil.** Traegt ein Profil dieselbe Verbindungskennung
   wie `default`, warnt `hermes profile list` je Profil
   (`hermes_cli/profile_channels.shared_channel_credentials`: Byte-Vergleich der
   Kennungszeilen aus `.env` und von `platforms.<p>.token|api_key` aus
   `config.yaml`). Ein zweites Gateway auf demselben Token nimmt dem ersten die
   Nachrichten weg — beide pollen `getUpdates` —, und
   `hermes gateway migrate --multiplex` verweigert, solange die Dopplung steht.
   Die Dopplung ist also nicht kosmetisch: sie kostet Nachrichten.
2. **Ein Bot-PROFIL braucht keine Kanalzugangsdaten — es braucht eine eigene
   Modellkennung.** Der `/bot`-Weg des SkillsBot startet
   `hermes -p NAME chat -q` ohne Gateway. Also die geteilten Kanalzeilen
   entfernen statt jedem Bot einen eigenen Bot zu geben. Profile sind Inseln:
   sie lesen nur ihr eigenes `auth.json`/`.env`.
   Die Modellkennung holt man NICHT, indem man die Konto-Anmeldung des
   Startprofils in jedes Profil kopiert: das ist dieselbe Kennung in vielen
   Dateien (dieselbe Fehlerklasse wie beim Kanal) und eine geteilte
   Refresh-Sitzung kann allen Profilen gleichzeitig ablaufen — im Startprofil
   stand `Refresh session has been revoked`, waehrend ein anderes Profil
   dieselbe Kennung benutzte. Die Sitzung holt ein Profil stattdessen ueber
   einen SYMLINK auf den Root-Store oder eine eigene Anmeldung (Abschnitt
   „Einem Profil eine Modell-Anmeldung geben"); der lokale Router war nur
   Zwischenloesung und traegt die Flotte nicht mehr, weil ein toter Kandidat in
   seiner Combo alle Bots gleichzeitig stilllegt. Rezept und der Weg ueber alle
   Profile: `siehe oben in dieser Datei`.
3. **Kein Unterkommando entfernt Kanaele aus einem bestehenden Profil** (nur
   `--clone` strippt beim Anlegen). Nicht selbst eine Schluesselliste bauen:
   `ChannelKeyIndex(<startprofil>).platform_for(<ENV_NAME>)` ist dieselbe
   Zuordnung, mit der `--clone` strippt. Ablauf, Werkzeug und Belege:
   `siehe oben in dieser Datei`.
4. **Geheimnisse nicht in den Diff.** Ein `diff` gegen die Sicherung gibt die
   Werte im Klartext aus — redigieren (`sed -E 's/=.*/=<wert>/'`) oder ueber
   Hashes und Zeilenzahlen nachweisen.
5. **Nachweis:** `hermes profile list` ohne eine einzige Warnzeile UND die
   Gegenprobe (Sicherung zuruecklegen → Warnungen wieder da → erneut strippen →
   0). Die `.env` des Startprofils bleibt unveraendert (Hash vorher/nachher):
   dort gehoeren die Zugangsdaten hin.
6. **Geteilte Zeilen, die keine Warnung ausloesen, nicht mitstrichen** (z. B.
   `A2A_*`, `SMS_*`): melden und als eigene Entscheidung stellen — ein
   stillschweigend mitgestrichener Nebeneintrag ist spaeter nicht mehr zuordenbar.
