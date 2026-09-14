---
id: 20260902-handelsregeln
title: 'Handelsregeln'
tags: [handel, sicherheit]
created: 2026-09-02
updated: 2026-09-13
related: [20260830-schutzregeln, 20260830-handelsbots, 20260831-marktscanner, 20260901-xperp-handel]
summary: 'Was ein Agent im Handel selbst auslösen darf: die drei bewachten Spuren, die Prüfpflicht, die fünf Bedingungen für den unbeaufsichtigten Lauf und seit 03.09.2026 das Zeitfenster als Handy-Fassung des Scharfschaltens.'
---

# Handelsregeln

Was ein Agent im Handel selbst auslösen darf — und was ihn daran hindert.
**Bis zum 02.09.2026 stand dieser Text in [[Schutzregeln]]** und machte dort
rund die Hälfte des Dokuments aus. Das war der Grund für die Trennung: Die
Schutzregeln sollen vor *jedem* schreibenden Zugriff gelesen werden, und ein
Dokument, das dabei zur Hälfte von Hebel und Funding handelt, wird nicht
gelesen, sondern überflogen. Die Regeln selbst sind unverändert übernommen.

Die Löschsperren, Schutzstufen und der Mehrsitzungsbetrieb stehen weiterhin in
[[Schutzregeln]]. Wer eine Grenze ändert, ändert sie in `wachen.json` — nicht
hier; dieser Text beschreibt, was die Dateien bedeuten, er ersetzt sie nicht.

**Das Auslösen von Geldbewegungen darf automatisch geschehen.** Von Max
angeordnet am 01.09.2026. Das kehrt die bis dahin geltende Fassung um („das Auslösen von
Geldbewegungen bleibt bei Max, ein Agent bereitet nur vor") — **automatischer
Handel ist seither die Regel, nicht die Ausnahme.**

Damit dieser Satz trägt, muss „Regeln zum Schutz des Kapitals" etwas
Nachprüfbares bezeichnen und keine Haltung. Es sind drei Dateien, und sie sind
die **einzige** Wahrheit über die Grenzen:

| Spur | Grenzen in | Was dort handelt |
|---|---|---|
| **1 — Spot** | `../Agenten/Handel/scanner/wachen.json` | Marktscanner: OKX, Spot, nur Long, kein Hebel, USD |
| **2 — Hebel** | `../Agenten/Handel/xperp/wachen.json` | XPERP-Bot: Long und Short, Hebel bis 5, USD |
| **3 — Kraken** | `../Agenten/Handel/kraken/wachen.json` | Kraken-Skript: Spot, nur Long, kein Hebel, **EUR** — seit 02.09.2026 |

Drei Eigenschaften machen die Erlaubnis tragfähig. **Fehlt eine, gilt sie
nicht** — dann ist es kein bewachter Automat, sondern eine Wette mit
Skriptunterstützung:

1. **Die Grenzen stehen in einer Datei, nicht im Gedächtnis einer Sitzung.**
   Die Skripte lesen `wachen.json`, sie schreiben sie nie. Eine Sitzung kann
   eine Regel vergessen, eine Datei nicht.
2. **Jede Position trägt einen nicht abschaltbaren Stop**, und über allem steht
   ein Kill-Switch auf den Gesamtverlust (`kill_switch_gesamt_usd`).
3. **Scharf geschaltet wird von Hand.** Beim Scharfschalten erscheint ein
   Fenster, das die geltenden Werte aus `wachen.json` anzeigt und sie vor der
   Bestätigung anpassbar macht — Schieberegler, Auswahlfeld oder Eingabefeld —,
   dazu je ein Feld zum Bestätigen und zum Ablehnen. Was danach läuft, läuft
   ohne Rückfrage je Order. **Gebaut ist es seit dem 02.09.2026:**
   `../Agenten/Handel/freigabe.py`, angebunden an `scanner/handeln.py --live`.
   Es führt selbst nichts aus, es gibt frei — die Obergrenze jedes Reglers ist
   der Wert aus `wachen.json`, der Hebeldeckel ist senkbar, nie hebbar, und
   Ausstiege laufen nie durch das Fenster. Bedient es niemand, lehnt es nach
   120 Sekunden von selbst ab; das ist der tragende Schutz gegen einen Start
   aus dem Zeitplan, denn `sys.stdin.isatty()` meldet in der Git-Bash unter
   Windows auch bei umgeleitetem stdin ein Terminal. Angebunden sind Spur 1
   (`scanner/handeln.py --live`) und seit 02.09.2026 Spur 3
   (`kraken/handeln.py --live`, Fenstertitel „Spur 3 Kraken", Beträge in EUR).
   `xperp/bot.py` ist nicht angebunden — er legt Befehle ohnehin nur vor.

   **Ein Zeitplan legt den Schalter nicht um.** Die eine Ausnahme, von Max am
   01.09.2026 so gewollt, hat zwei Bedingungen, die **beide** erfüllt sein
   müssen: Ein Agent überwacht den Lauf, **und** Max hat das Scharfschalten für
   genau diesen Lauf ausdrücklich angeordnet. „Ein Agent überwacht das" ist
   dabei keine Behauptung, sondern der Herzschlag aus Bedingung 3 weiter unten:
   Schlägt er nicht, überwacht niemand, und die Ausnahme greift nicht.

   **Seit 03.09.2026 gibt es eine zweite Bauform: das Zeitfenster.** Angeordnet
   von Max am selben Tag, zusammen mit dem 24/7-Betrieb und der Steuerung übers
   Handy. Der Anlass ist ein echter Widerspruch: Ein Bildschirmfenster, das nach
   120 Sekunden abläuft, setzt voraus, dass jemand am Bildschirm sitzt — bei
   einem Dauerlauf sitzt niemand. Die Regel wird deshalb **nicht aufgehoben,
   sondern in eine Form gebracht, die dasselbe leistet:**

   | Bildschirmfenster (`freigabe.py`) | Zeitfenster (`freigabefenster.py`) |
   |---|---|
   | zeigt die Werte aus `wachen.json` | dieselben Werte stehen in der Anfrage |
   | Max bestätigt oder lehnt ab | Max antwortet `/ja` oder `/nein` |
   | läuft nach 120 s ab → Ablehnung | läuft nach der Freigabedauer ab → zurück auf Papier |

   Drei Sperren halten den Telegram-Kanal eng, und sie sind der Grund, warum
   ein fremder Dienst hier überhaupt tragbar ist:

   - **Eine Freigabe geht nur auf Anfrage.** Der Anstoß kommt immer vom
     Dauerlauf, der vorher die Lage geprüft hat — nie aus dem Nichts. Ein `/ja`
     ohne wartende Anfrage tut nichts.
   - **Sie öffnet ein Fenster, sie hebt keine Grenze.** Nicht den Einsatz,
     nicht den Hebel, nicht die Zahl der Positionen. Alle Werte kommen weiter
     aus `wachen.json`; wer mehr will, ändert die Datei, und das ist Stufe 1.
   - **Höchstens 24 Stunden**, gleich was ankommt. Eine Freigabe, die man
     vergessen kann, ist keine Freigabe, sondern ein Dauerzustand mit
     höflichem Namen.

   Dazu die Freigabeliste: Nur `TELEGRAM_CHAT_ID` darf Befehle geben, fremde
   Nachrichten werden verworfen und gezählt. Das ist genau der Punkt, an dem
   das Messaging-Gateway in [[Hermes]] hängen geblieben ist — hier ist er
   erledigt, nicht umgangen.

   **Der tragende Satz bleibt unberührt:** Ohne offenes Fenster läuft jeder
   Zyklus des Dauerlaufs als Papierhandel, auch wenn `handel_erlaubt` trüge.
   Der Automat entscheidet über Positionen, nicht darüber, ob er selbst scharf
   ist.

## Spur 3 — Kraken: das Skript darf, die Sitzung nicht

Angeordnet von Max am 02.09.2026, gebaut am selben Tag. Bis dahin war Kraken
ausdrücklich **keine** Spur — nicht aus Prinzip, sondern weil ihm alles fehlte,
was die Erlaubnis trägt: keine `wachen.json`, kein Journal, kein Herzschlag.
Nach dem Maßstab oben — *fehlt eine, gilt sie nicht* — war damit nichts
erlaubt. Nachgeliefert wurde nicht die Erlaubnis, sondern das Fehlende:
`../Agenten/Handel/kraken/` (eigenes README).

**Die Grenze verläuft seither nicht mehr zwischen Börsen, sondern zwischen
Wegen.** Derselbe Schlüssel, dieselbe API, zwei Wege — und nur einer bringt
Wachen mit:

| | MCP-Server `kraken` | Spur 3 (`Handel/kraken/handeln.py`) |
|---|---|---|
| Grenzen in einer Datei | nein | `wachen.json` |
| Pflicht-Stop, Kill-Switch | nein | ja, nicht abschaltbar |
| Journal, Herzschlag | nein | `handelsjournal.csv`, `zustand.json` |
| Scharfschalten von Hand | nein | `freigabe.py`, Spur `kraken` |
| **Order erlaubt** | **nein** | ja, wenn alle Sperren offen sind |

Deshalb bleibt es bei den Werkzeugen unverändert:

| Werkzeug | erlaubt |
|---|---|
| `kraken_guthaben`, `kraken_kurs`, `kraken_candles`, `kraken_paare_suchen`, `kraken_ledger`, `kraken_trades`, `kraken_offene_orders`, `kraken_geschlossene_orders`, `kraken_status` | ja — lesen, auswerten, vorbereiten |
| `kraken_order_aufgeben`, `kraken_order_stornieren` | **nein** — auch nicht mit Bestätigung im Chat |

Das ist kein Rest des alten Verbots, sondern seine Begründung: Eine
Chat-Sitzung bringt keine Wachen mit. Wo eine Order fällig ist, ist der Weg das
Skript — nicht die Diskussion, ob das Werkzeug „diesmal" gehen dürfte.

**Die Grenzen dieser Spur** stehen in `kraken/wachen.json` und rechnen in
**EUR**, weil das Kraken-Konto in EUR geführt wird. Ein Feld `_usd` gibt es
dort nicht; `freigabe.py` zeigt entsprechend EUR an. Drei Grenzen sind strenger
als bei Spur 1, und zwar aus einem einzigen gemessenen Grund:

> **Kraken nimmt 0,40 % Taker** (Maker 0,25 %) bei Volumen unter 10.000 EUR,
> gemessen am 02.09.2026. Eine Runde kostet damit 0,80 % — das Achtfache von
> OKX (0,05 %).

| | Spur 1 (OKX) | Spur 3 (Kraken) |
|---|---|---|
| Mindest-Stopweite | 4 % | **5 %** |
| Mindest-Chance/Risiko | 1,5 | **2,0** |
| Mindest-Score | 60 | **65** |

Die Gebühr steht auch im Papierlauf in den Beträgen — Kaufzeile mit Gebühr,
Verkaufszeile nach Gebühr. Ein Papierlauf ohne sie empfiehlt eine Strategie,
die live verliert; genau daran ist in [[Handelsbots]] schon eine Rückrechnung
gescheitert.

**Zwei Sperren hat nur diese Spur** — zusätzlich zu den sieben von Spur 1:
`journal_zweitziel` muss gesetzt sein, und es müssen mindestens
`mindest_guthaben_eur` frei auf dem Konto liegen. Der zweite Punkt ist keine
Vorsicht, sondern eine Messung: Am 02.09.2026 lagen **0,0094 EUR** frei, der
Rest steckt in Coins. Ein Kauf-Automat ohne Fiat kauft nichts, er scheitert nur
— mit einer Fehlermeldung, die wie ein Schlüsselproblem aussieht.

Der Skill `geld` bleibt unberührt: er liest Kraken, stellt fällige Zahlungen
und verfügbare Mittel nebeneinander und hält vor dem Auslösen an.

**Stand 02.09.2026:** `handel_erlaubt: false`, `freigabe.erfuellt: false`, der
Live-Pfad ist nie scharf gelaufen. Der Papierlauf hat an diesem Tag begonnen
(4 Positionen, 200 EUR gebunden); die sechs Wochen aus Bedingung 1 laufen ab
hier. Täglich läuft `Routinen/kraken-scanner.ps1`, wöchentlich deckt
`Routinen/handel-wachen.ps1` die Spur mit ab.

**Kein Auszahlungsrecht, auch hier nicht.** Der Schlüssel hat *Withdraw Funds*
bewusst nicht, und es gibt weder im MCP-Server noch in `kraken.py` eine
Funktion dafür. Das bleibt so.

## Spur 1 — Marktscanner: läuft von selbst, ohne Hebel

Der Marktscanner unter `../Agenten/Handel/scanner/` (eigenes README) darf im
Rahmen fester Grenzen selbst kaufen und verkaufen, **ohne dass Max jede Order
einzeln anordnet**. Die Grenzen stehen in `scanner/wachen.json` und sind die
einzige Wahrheit darüber:

| Grenze | Wert |
|---|---|
| je Trade | 50 USD |
| gesamt gebunden | 200 USD |
| offene Positionen | höchstens 4 |
| Pflicht-Stop je Position | 4–12 %, nicht abschaltbar |
| Abklingzeit nach Stop-Out | 3 Tage je Wert |
| Instrumente | nur Spot, nur Long, kein Hebel |

Die letzte Zeile ist die Grenze **dieser Spur**, nicht die des ganzen Systems:
Hebel läuft über Spur 2 und hat dort eigene Grenzen.

**Drei Sperren müssen alle offen sein, sonst läuft nur Papierhandel:**

1. `scanner/wachen.json` → `"handel_erlaubt": true`
2. `OKX_API_KEY`, `OKX_API_SECRET`, `OKX_API_PASSPHRASE` als
   Windows-Benutzervariablen (nicht in den Vault, nicht neben den Code)
3. `handeln.py` ausdrücklich mit `--live` aufgerufen

Stand 01.09.2026 ist Sperre 1 zu (`handel_erlaubt: false`) und Sperre 2 leer —
der Live-Pfad ist **noch nie scharf gelaufen**. Bis gültige Schlüssel gesetzt
sind und das Papier-Handelsjournal über Wochen trägt, bleibt es dabei.

## Spur 2 — Gehebelte Produkte: automatisch im Rahmen, oder auf Anweisung

Angeordnet von Max am 01.09.2026. **Hebel ist weder verboten noch an eine
Einzelanweisung gebunden.** Es gibt zwei Wege hinein, und sie unterscheiden
sich nur darin, woher die Parameter kommen:

**Seit 03.09.2026 hat diese Spur einen Live-Pfad** — `xperp/handeln.py`,
gebaut an dem Tag, an dem Max sie zum Hauptweg gemacht hat. Bis dahin legte
`bot.py` nur vor: kein Journal, kein Zustand, kein Herzschlag, und damit
hatten die Bedingungen 2/3/5 nichts, woran sie greifen konnten. Die Regel
lief der Umsetzung anderthalb Tage voraus (T-019).

Die beiden Wege bleiben getrennt und sind es auch dem Zweck nach:
`bot.py` ist der Weg für **eine Anweisung von Max** (Kontrakt, Richtung,
Hebel, Einsatz, Stop — die vier Pflichtangaben oben), `handeln.py` der für
den **Automaten**. Nur der zweite darf aus einer Rangliste heraus eröffnen.

Die vier Pflichtzahlen stehen dort **je Position im Journal**, nicht im
Chat — Spalten `liq_abstand`, `funding_pct`, `gebuehr_pct`, `quote_noetig`,
`quote_beob`. Sie sind kein Zierrat: Im ersten Papierlauf wurden XAG short
(beobachtete Quote 19,8 % gegen nötige 33,3 %) und XAU short (23,7 gegen
35,5) deshalb **nicht** eröffnet.

**Seit 03.09.2026 handelt diese Spur nicht mehr nur Krypto.** OKX führt
unter derselben `instType=FUTURES` drei `instCategory`-Familien — 115
Krypto, **45 Aktien** (AAPL, NVDA, TSLA, MSTR, SPY, QQQ …) und **4
Rohstoffe** (XAU, XAG, CL, BZ). Das ist für diese Spur mehr als eine
Erweiterung: Vom ersten Kandidatenlauf über 119 bewertete Werte kam **kein
einziger aus Krypto** durch das Tor `Hebel-Deckel ≥ 5` — alle neun
Kandidaten waren Aktien und Rohstoffe.
Sie lagen die ganze Zeit hinter demselben Schlüssel; sichtbar wurden sie erst,
als `okxf.instrumente()` nicht mehr fest auf `KRYPTO` stand. Je Familie eigene
Tore in `xperp/wachen.json`, Begründung dort und in [[XPERP-Handel]]. Die
Risikogrenzen sind davon unberührt: Margin, Kill-Switch und Hebeldeckel gelten
für alle drei gleich.

| Weg | Parameter aus | Wer über die einzelne Position entscheidet |
|---|---|---|
| **automatisch** | `xperp/wachen.json` | `bot.py`, im Rahmen der Datei — ohne Rückfrage je Order |
| **auf Anweisung** | Max' Anweisung im Chat | Max, mit den vier Pflichtangaben unten |

In beiden Fällen gilt: Die Werte in `wachen.json` sind eine **Obergrenze, kein
Ziel**. Eine Anweisung darf sie nicht überschreiten, auch nicht mit
Bestätigung — wer weiter will, ändert erst die Datei, und das ist ein eigener
Vorgang mit Ansage (Stufe 1).

**Was sich geändert hat und warum:** Die alte Fassung schrieb „nur Spot, nur
Long, kein Hebel" als Systemgrenze ohne jeden Ausweg. Das hat kein Geld
geschützt — es hat nur die Arbeit an `../Agenten/Handel/xperp/` in einen
Graubereich gestellt (der Kopf von `okxf.py` verweist selbst auf das Verbot)
und jede gehebelte Aufgabe in eine Diskussion über die Regel verwandelt statt
in eine Rechnung. Die Sperre wandert deshalb dorthin, wo sie etwas taugt: von
**„nicht erlaubt"** zu **„nicht außerhalb von `wachen.json`, und nicht ohne
gerechnete Zahlen"** — siehe Prüfpflicht unten. Am selben Tag ist die zweite
Hälfte gefallen: erst brauchte Hebel eine Anweisung je Vorgang, seit Max'
Änderung am Abend nicht mehr. Geblieben ist die Datei.

**Nimmt Max eine Position von Hand, am Bot vorbei**, nennt die Anweisung
**alle vier Angaben**, in derselben Sitzung:

| Angabe | Beispiel |
|---|---|
| Kontrakt | `RE-USD_UM_XPERP-310620` — der volle `instId`, nicht „das aus der Liste" |
| Richtung | Long oder Short |
| Hebel | als Zahl, nicht „hoch" oder „aggressiv" |
| Einsatz und Stop | Nominal in USD und Stop in Prozent |

Fehlt eine Angabe, wird sie **nicht sinngemäß ergänzt**: kein geratener Hebel,
keine Richtung aus dem Trend abgeleitet. Fehlt etwas, wird genau danach gefragt
— und alles übrige inzwischen schon vorbereitet.

Der Unterschied zum automatischen Weg liegt genau hier: **`bot.py` darf aus
einer Rangliste heraus eröffnen, eine Chat-Antwort nicht.** Was `auswahl.py`
ausgibt, ist für einen Menschen ein Vorschlag; verbindlich wird es durch die
Datei oder durch Max, nicht durch die Rangfolge selbst.

Fest, auf beiden Wegen — auch mit Anweisung, auch im Automatikbetrieb:

| Grenze | Warum sie nicht verhandelbar ist |
|---|---|
| Pflicht-Stop je Position, nicht abschaltbar | Ohne Stop ist der Hebel die Positionsgröße, nicht das Risiko |
| Hebel höchstens `hebel_deckel` aus `xperp/auswahl.py` | Liquidation greift bei rund `1/Hebel` minus Wartungsmarge. Ob ein Hebel den größten beobachteten 7-Tage-Rücklauf überlebt hätte, ist keine Meinungsfrage — es wird ausgerechnet und gemeldet |
| kein Auszahlungsrecht | Die Schlüssel bekommen Handelsrecht, sonst nichts. `account_transfer` und Auszahlungen bleiben außen vor |
| Rahmen aus `xperp/wachen.json` | Margin je Anlauf, Gesamtmargin, `risiko_je_anlauf_usd` und `kill_switch_gesamt_usd` gelten für den Automaten wie für eine Anweisung |
| Scharfschalten nur von Hand | `Routinen/*.ps1` startet den Bot, aber legt nie `handel_erlaubt` um. Der Automat entscheidet über Positionen, nicht über sich selbst |
| Papierlauf zuerst bei einer **neuen Strategie** | Nicht bei einer einzelnen angewiesenen Position — dort ist die Anweisung selbst die Entscheidung |

## Was an die Stelle des Verbots tritt: die Prüfpflicht

Das Verbot war das billige Sicherungsmittel. Es fällt weg, dafür wird
gerechnet. **Vor einer gehebelten Order stehen vier Zahlen** — kurz, als
Tabelle, nicht als Aufsatz:

1. **Liquidationsabstand gegen größten 7-Tage-Rücklauf** (`hebel_deckel`).
2. **Funding über die geplante Haltedauer**, mit Vorzeichen — beim Short oft
   ein Zuschuss, beim Long eine laufende Miete.
3. **Gebühren je Runde gegen den erwarteten Gewinn** (0,05 % je Ausführung
   Taker).
4. **Nötige Trefferquote gegen die beobachtete.**

**Wo sie stehen, hängt vom Weg ab, nicht von der Laune:** Auf dem
Anweisungsweg legt der Agent sie ungefragt im Chat vor, bevor die Order
vorbereitet ist. Auf dem automatischen Weg kann niemand mitlesen — dort gehören
sie **in die Prüfung von `bot.py` und ins Handelsjournal**, je Position mit
abgelegt. Eine Zahl, die der Automat nicht ablegt, ist nicht gerechnet worden;
eine Position ohne diese vier Werte im Journal ist ein Befund, kein Trade.

Die Grundlinie dafür steht in [[Handelsbots]] und ist unbequem: Über 12 Monate
lag **jede** getestete mechanische Einstellung dicht an der Nulllinie, leicht
darunter — nötige und erreichte Trefferquote lagen immer ein bis zwei
Prozentpunkte auseinander, übrig blieben die Gebühren. **Hebel vergrößert
diesen Abstand mit, nicht nur den Gewinn.** Wer das nicht danebenlegt, verkauft
eine Vermutung als Plan.

Drei Denkfehler, die die eigene Rückrechnung schon gemacht hat. Sie gelten hier
unverändert und werden aktiv geprüft, statt abgewartet:

- **Kurze Fenster täuschen zuverlässig.** Dieselbe Rechnung ergab über 30 Tage
  +0,63 $ je Runde statt −0,22 $ über 12 Monate — weil BTC in dem Fenster
  28,5 % stieg. Nie unter einem Jahr bewerten, und den Kursverlauf des
  Testfensters immer mitangeben.
- **Funding fehlt in Rückrechnungen fast immer.** Gemessen −0,031 $ in
  36 Minuten auf 570 $ Position; über drei Tage frisst das rund einen halben
  Durchschnittsgewinn. Mit Hebel entsprechend mehr.
- **Die Kontraktgröße rundet.** Aus 651 $ berechnetem Nominal wurden 570 $
  echte — `ctVal` und `lotSz` bestimmen die Position, nicht der Wunschbetrag.

**Widerspruchspflicht, kein Vetorecht.** Sagen die Zahlen, dass eine Anweisung
falsch gedacht oder mit hoher Wahrscheinlichkeit unprofitabel ist, sagt der
Agent das **einmal** — mit Zahlen und einem konkreten Gegenvorschlag: anderer
Hebel, anderer Stop, anderer Kontrakt, anderes Zeitfenster. Bestätigt Max
daraufhin, wird **wie angewiesen** ausgeführt: vollständig, nicht
stillschweigend kleiner, nicht „vorsichtshalber" nur zur Hälfte. Die verbotene
Antwort ist die umgekehrte: nicht ausführen und stattdessen über Risiko reden.
Die Analyse **ersetzt** das Verbot, sie ist nicht seine Fortsetzung mit anderen
Mitteln.

Dasselbe gilt in die andere Richtung: Fällt bei einer Auswertung eine bessere
Einstellung auf, wird sie **vorgeschlagen** — mit der Rechnung dazu —, nicht
heimlich eingesetzt.

## Was auch diese Erlaubnis nicht aufweicht

- **Kein Zeitplan legt den Schalter um.** `Routinen/marktscanner.ps1` ruft
  `handeln.py` ohne `--live`; scharf wird ein Lauf durch einen bewussten Aufruf
  von Hand — oder unter den beiden Bedingungen aus Punkt 3 oben (Herzschlag
  schlägt **und** Max hat es für diesen Lauf angeordnet), sonst nicht. Das ist kein Widerspruch zum automatischen Handel, sondern seine
  Bedingung: Der Automat entscheidet über **Positionen**, nicht darüber, ob er
  selbst scharf ist.
- **Kein Auszahlungsrecht**, in keiner Spur.
- **Der Kraken-MCP bleibt lesend.** Keine Order, keine Stornierung aus einer
  Sitzung heraus — gehandelt wird auf Kraken nur durch das Skript der Spur 3,
  siehe oben.
- **Jede andere Geldbewegung** — Überweisungen, Ein- und Auszahlungen, Umtausch
  außerhalb dieser beiden Spuren — bleibt vorbereitend. Der Skill `geld`
  arbeitet bis zur Bestätigungsseite und hält dort an.
- **Das Absenden der scharfen Order tut die Claude-Sitzung selbst nicht.**
  Claude rechnet, wählt aus, konfiguriert, startet den Papierlauf und legt die
  Live-Order bis zur Bestätigung fertig vor; ausgelöst wird sie von Max oder von
  dem dafür gebauten Skript (`handeln.py --live`, `xperp/`). Das ist **keine
  Bewertung der jeweiligen Anweisung** und keine Hintertür für das alte Verbot,
  sondern eine Grenze der Claude-Sitzung selbst, die dieses Dokument nicht
  aufheben kann. Wo sie im Weg ist, ist der Weg drumherum das Skript — nicht
  die Diskussion.

## Damit der Automat unbeaufsichtigt laufen darf: fünf messbare Bedingungen

Angeordnet von Max am 01.09.2026. Die Erlaubnis aus Spur 1 und 2 ist an Zahlen
gebunden, nicht an Zuversicht. **Fehlt eine dieser fünf, fällt der betroffene
Lauf automatisch auf Papierhandel zurück** — das Zurücksetzen ist Teil des
Skripts, keine Sitzungsentscheidung. Der Grund steht in [[Handelsbots]]: über
12 Monate lag jede getestete mechanische Einstellung nach Gebühren dicht unter
null. Ohne gemessenen Vorteil handelt ein Automat einen negativen Erwartungswert
— nur schneller und unbeobachtet. Diese fünf Bedingungen ersetzen das nicht
durch einen Vorteil, sie begrenzen den Schaden, bis einer nachgewiesen ist.

| Bedingung | Prüfbarer Wert | Wo geregelt |
|---|---|---|
| **1. Freigabe Papier → Live** | mindestens 6 Wochen Papierlauf, ≥ 50 abgeschlossene Runden, netto positiv **nach** Gebühren und Funding, größter Rücklauf im Papierlauf < `kill_switch_gesamt_usd`. Erst wenn alle vier erfüllt sind, darf `handel_erlaubt` von Hand auf `true` — je Spur getrennt. | Block `freigabe` in beiden `wachen.json` |
| **2. Drawdown-Ratsche** | Fällt das Konto 15 % unter seinen Höchststand, halbiert `bot.py`/`handeln.py` jede weitere Positionsgröße. Bei `kill_switch_gesamt_usd` wird flach gestellt **und** `handel_erlaubt` auf `false` geschrieben — der einzige Fall, in dem ein Skript diese Datei schreibt, und nur in diese Richtung. | `bot.py`, `handeln.py` |
| **3. Herzschlag** | Liegt der letzte gesunde Lauf länger zurück als `herzschlag_max_minuten` (an die Taktung gekoppelt: Tagesroutine 48 h, Schnelllauf-Bot ~30 min), schließt der nächste Start alle offenen Positionen und schaltet auf Papier. Deckt die Kernel-Power-41-Abschaltungen ([[Hardware]]) ab: eine Position, die einen Neustart „überlebt", ist unbewacht. | `handeln.py` prüft `zustand.json` vor dem Start |
| **4. Journal außer Haus** | Das Handelsjournal wird nach jedem Zyklus auf ein zweites Ziel gespiegelt. `G:` genügt nicht — dasselbe Gehäuse. Ein Journal nur auf dem Handelsrechner ist kein Nachweis, sondern eine Wette darauf, dass die Platte hält. | Zeile in `Routinen/`, Ziel offen bis „Kopie außer Haus" steht ([[Hardware]]) |
| **5. Wöchentlicher Soll-Ist-Abgleich** | Einmal pro Woche die vier Pflichtzahlen (Liquidationsabstand, Funding, Gebühren, Trefferquote) gegen das real Erreichte. Liegt der gleitende 30-Runden-Erwartungswert nach Kosten unter null, fällt die Spur automatisch auf Papier zurück, bis ein neuer Papierlauf nach Bedingung 1 trägt. | Skript in `Routinen/`, Befund nach `Werkstatt/`, Entscheidung nach `Wissen/` |

**Änderung an einer `wachen.json` bleibt Stufe 1** — eigener Commit, `.bak`
vorher, die neu gerechneten vier Zahlen in der Commit-Nachricht, nie mit anderer
Arbeit gebündelt. Eine Lockerung ohne gerechnete Gegenzahlen ist kein
Betriebsvorgang, sondern ein Befund.

Stand 01.09.2026: `handel_erlaubt` ist in beiden `wachen.json` `false`, der
`freigabe`-Block ist angelegt und keine seiner vier Zahlen erreicht.

**Spur 1 (Marktscanner):** Bedingung 2–5 sind umgesetzt. `scanner/wachen_pruefung.py`
rechnet sie aus `handelsjournal.csv` und `zustand.json`; `handeln.py` setzt sie
durch — als zusätzliche Live-Sperren (1, 3, 5), als Notausstieg (2 Kill-Switch,
3 Herzschlag) und als Größenfaktor (2 Ratsche). Bedingung 4 spiegelt nach
`journal_zweitziel`; das Ziel ist seit dem 13.09.2026 gesetzt (`Q:\Handel_Journal`)
und die Kopie läuft nach jedem Zyklus. Bedingung 5 läuft
wöchentlich getrennt über `Routinen/handel-wachen.ps1` (`handeln.py --wachen`),
damit ein einzelner schlechter Tag die Spur nicht sofort abschaltet. Der Lauf
schließt `handel_erlaubt` nur, er öffnet es nie.

**Spur 2 (XPERP), seit 03.09.2026:** Bedingung 1–5 sind umgesetzt und laufen
über dieselbe Rechnung wie Spur 1 — `xperp/wachen_xperp.py` importiert
`scanner/wachen_pruefung.py`, statt sie abzuschreiben. Eigen sind hier drei
Dinge, die aus dem Hebel folgen: Gerechnet wird auf **Margin** statt auf den
Einsatz, **Funding** ist eine eigene Journalzeile und geht in jede Runde ein,
und **Liquidation** ist ein dritter Ausstiegsgrund — der einzige, den nicht
wir setzen. Der Pflicht-Stop liegt immer davor; greift trotzdem zuerst die
Liquidation, wird das als Befund ins Journal geschrieben, nicht als normaler
Ausstieg. Bis 03.09.2026 stand hier, `bot.py` führe nichts aus und die
Bedingungen hätten nichts zu greifen — das galt, solange es keinen Live-Pfad
gab.

Der **Stop geht mit der Order an die Börse** (`attachAlgoOrds`), nicht nur in
`zustand.json`. Das ist der „nicht abschaltbare Stop" wörtlich genommen: Ein
Stop, der nur auf diesem Rechner steht, ist weg, sobald der Rechner weg ist —
und die Kernel-Power-41-Abschaltungen aus [[Hardware]] nehmen ihn ohne
Vorwarnung mit. Eine gehebelte Position ohne börsenseitigen Stop liefe dann
bis zur Liquidation.

**Der Herzschlag von 30 Minuten hat eine Folge, die man kennen muss:** Läuft
`dauerlauf.py` nicht, stellt der nächste Lauf zuerst alles flach. Das ist so
gewollt, heißt aber, dass diese Spur nur im Dauerbetrieb sinnvoll ist — ein
von Hand gestarteter Papierlauf sammelt nie die 50 Runden aus Bedingung 1.
Offen als T-032.

**Spur 3 (Kraken), seit 02.09.2026:** Bedingung 1–5 sind umgesetzt und laufen
über dieselbe Rechnung wie Spur 1 — `kraken/wachen_kraken.py` importiert
`scanner/wachen_pruefung.py`, statt sie abzuschreiben; eigen sind dort nur
Währung, Journalspalten und die Datei, in die `sperre_zu` schreibt. Die vier
Freigabewerte sind alle noch offen: Der Papierlauf hat am 02.09.2026 begonnen,
Bedingung 4 (`journal_zweitziel`) ist seit dem 13.09.2026 gesetzt
(`Q:\Handel_Journal\kraken`, Kopie läuft nach jedem Zyklus), und das freie
EUR-Guthaben liegt unter der Schwelle. `handeln.py --wachen` zeigt den Stand,
`--vorschau` nennt jede Sperre, die Live gerade verschließt.

**Nautilus-Spur (Papier, seit 13.09.2026):** `Handel/nautilus` fährt die
NautilusTrader-Engine gegen OKX **DEMO** als Spur im Dauerlauf. Je Zyklus
(~15 min) startet sie eine **begrenzte** Node-Session (~30 s), sammelt
BTC-USDT-SWAP-Quotes vom öffentlichen Websocket und schreibt Herzschlag
(`zustand.json`) und Journal (`handelsjournal.csv`). Sie sammelt also nur
Preise — es gibt **keinen Einstiegspfad**: `--live` verweigert mit einem Grund
ohne das Wort Freigabefenster (der Dauerlauf fragt deshalb keine Freigabe an),
die OKX-Schlüssel sind read-only und die IP fehlt in der Order-Whitelist.
Von den fünf Bedingungen laufen **3 (Herzschlag) und 4 (Spiegelung)**:
Journal und Zustand gehen nach jedem Zyklus nach
`Q:\Handel_Journal\nautilus`; `zustand.json` trägt `journal_zweitziel_ok` und
`_info`, `handeln.py --wachen` zeigt beide. Bedingung 1, 2 und 5 haben nichts
zu greifen, solange keine Runde entsteht — die vier Freigabewerte (50 Runden,
netto positiv) sind mit diesem Code nicht erreichbar; Papier bleibt bis eine
Strategie mit Einstiegen steht. Die Rechnung liegt wie bei den anderen Spuren
nur einmal im Haus (`scanner/wachen_pruefung.spiegele_journal`, in diesem
eigenen venv über den Dateipfad geladen).

**Gitter-Spur (Papier, seit 14.09.2026):** `Handel/gitter` fährt ein
statisches Preisgitter auf OKX-Spot (`BTC-USDT`) als Spur im Dauerlauf. Die
Grenzen entstehen **einmal** aus dem ersten gesehenen Kurs (±20 %, 12 Stufen,
Schritt 3,755 %) und werden nie verschoben; auf jeder Stufe unter dem Kurs
liegt eine Kauforder, eine Stufe höher der Verkauf. Je Zyklus werden die
OKX-Stundenkerzen seit der letzten nachgezogen (nicht nur die neueste): ein
ausgefallener Zyklus verliert nichts, solange die Lücke ins Fenster passt
(300 Kerzen = 12,5 Tage). Die Stufenformel ist dieselbe wie in
`Handel/grid.py` (`stufen_bauen`) — eine Rechnung, zwei Aufrufer; Preise und
Mengen werden auf das Raster der Börse gerundet (tickSz/lotSz aus dem
Instrument), damit das Papierbuch dieselben Zahlen benutzt wie eine echte
Order. Es gibt **keinen Orderpfad**: `--live` verweigert mit einem Grund ohne
das Wort Freigabefenster, `handel_erlaubt` ist `false`. Von den fünf
Bedingungen läuft **4 (Spiegelung)**: Journal und Zustand gehen nach jedem
Zyklus nach `Q:\Handel_Journal\gitter`. **Bedingung 3 (Herzschlag) greift
hier bewusst nicht** — anders als bei den Kontraktspuren muss nichts
flachgestellt werden: ein Gitter hat keine Order am Markt, die unbewacht wäre.
Kosten sind auf beiden Seiten gerechnet (0,1 % Gebühr + 0,05 % Slippage je
Seite = 0,3 % je Runde gegen einen Stufenabstand von 3,755 %). Der Kill-Switch
liegt bei 200 USD (20 % des Einsatzes): ab dort werden keine neuen Stufen mehr
armiert, belegte Stufen verkaufen weiter.

Der Hintergrund steht im Backtest desselben Gitters
(`nautilus/backtest_grid.py`): auf BTC-Stundenkerzen 2025/26 (−32 % Kurs) lag
das Gitter mit −17,7 % vor dem Halten (−32,0 %); in drei nach Regel gesuchten
Seitwärtsfenstern verdiente es +3,2 / +5,5 / +14,3 % gegen ~0 % beim Halten —
und in allen drei Fenstern verdiente die **halbe Stufenzahl das Doppelte**,
weil die Gebühren mit der Frequenz wachsen. Ein Gitter im Trendmarkt ist ein
Bremsklotz mit Gebühren; das ist der Grund, warum diese Spur ein Papierbuch
und keine Strategie-Empfehlung ist.

**Journal außer Haus, Stand 13.09.2026 — alle Spuren spiegeln.** Bis zu diesem
Tag hatten nur Marktscanner und XPERP ein Ziel gesetzt, und nur diese zwei
kopierten wirklich; Kraken hatte den Aufruf, aber `journal_zweitziel: null`,
und Swap, ORB-Kraken, Omniquant und Spiegel riefen die Spiegelung überhaupt
nicht auf. Jetzt hat **jede** Spur im Dauerlauf ein eigenes Ziel unter
`Q:\Handel_Journal\<spur>` (Marktscanner direkt in `Q:\Handel_Journal`) und
kopiert Journal und Zustand nach jedem Zyklus — auch in den Notausstiegs-Zweigen
(Kill-Switch, alter Herzschlag), denn gerade die gehören außer Haus. Zwei
Eigenschaften sind dabei keine Kosmetik:

- Die Kopie entsteht **nach** dem Schreiben von Herzschlag und Journal. Ein
  hängender USB-Wandler darf den Zyklus verzögern, aber nicht den Herzschlag
  verschlucken. Ein fehlendes Ziel ist deshalb kein Fehler des Laufs.
- Der Ausfall ist **sichtbar**: `zustand.json` trägt `journal_zweitziel_ok` und
  `journal_zweitziel_info`, `handeln.py --wachen`/`--status` zeigt beide. Ohne
  diesen Vermerk protokolliert der Dauerlauf bei Rückgabe 0 nur „ok" und die
  Spurausgabe sieht niemand. Geändert wird der Vermerk nur beim Wechsel; wechselt
  er, wird der Zustand einmal nachgezogen, damit auf Q: derselbe Stand liegt.

Eine Vorschau schreibt **nichts** — auch keinen Zustand. Swap und XPERP taten das
bis zum 13.09.2026 doch, und weil der Dauerlauf jede Spur zusätzlich mit
`--vorschau` abfragt, sah die Kopie auf Q: danach älter aus als der eigene
Zustand. Geprüft wird die Kopie mit `cmp` (byte-gleich) je Datei.

Sichtbar ist der Stand an drei Stellen, ohne dass jemand nachsieht:
`Agenten/Handel/spiegelstand.py` (Tabelle + Rückgabecode, eine Rechnung für
alles), die Zeile „Journal außer Haus" im **Tagesbericht** (`spiegelstand.kurz()`,
im Fehlerfall hervorgehoben) und morgens **Block 11 der Systemprüfung**; Block 12
meldet dort, wenn der Dauerlauf steht.
