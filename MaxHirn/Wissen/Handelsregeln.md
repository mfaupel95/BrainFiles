---
id: 20260902-handelsregeln
title: 'Handelsregeln'
tags: [handel, sicherheit]
created: 2026-09-02
updated: 2026-09-21
related: [20260830-schutzregeln, 20260830-handelsbots, 20260831-marktscanner, 20260901-xperp-handel, 20260929-omnitrade]
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

**Ausnahme seit dem 14.09.2026 auf Max' Anweisung: Spur 3 rechnet mit 0 %.**
`gebuehr_taker` in `kraken/wachen.json` steht auf `0`, weil das Kraken-Pro-Abo
das Handelsvolumen bis 10.000 EUR im Monat gebührenfrei stellt (Freivolumen
zählt auf Kauf **und** Verkauf, also 100 EUR je Runde bei 50 EUR Einsatz —
rund 100 Runden im Monat). Die Spur misst damit das Rohsignal, nicht die
handelbare Wahrheit. Drei Bedingungen hängen daran: (1) fällt das Abo weg, ist
`0.004` zurückzunehmen, **bevor** Runden für Bedingung 1 gezählt werden, sonst
zählt die Spur zu freundlich; (2) das Monatsvolumen gehört in den
wöchentlichen Soll-Ist-Abgleich — oberhalb des Freivolumens gilt wieder
0,40 % je Seite; (3) die drei strengeren Grenzen oben bleiben gültig, ebenso
die Rückrechnung in `kraken/wachen.json` (`_stillgelegt_grund`: −0,57 % je
Runde **ohne** Gebühr) — selbst gebührenfrei gerechnet war der beste gefundene
Wert negativ, die Freigabe bleibt deshalb zu.

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
- **Der Kraken-MCP bleibt lesend — mit genau einem Tor.** Aus einer Sitzung
  heraus gibt es keine Order und keinen Sammelstorno. Die einzige Ausnahme ist
  das Werkzeug `kraken_order_mit_beleg`: es führt nur aus, was eine Handels-Spur
  vorher mit einem **Freigabe-Beleg** versehen hat
  (`Agenten/Handel/freigabebeleg.py`). Einen Beleg stellt allein die Spur aus,
  und nur bei offenem Freigabefenster und `handel_erlaubt=true` — er ist an
  Spur, Seite, Paar, Höchstmenge, Höchstpreis und eine Frist von drei Minuten
  gebunden und nach dem Ausführen verbraucht. So bleibt die Entscheidung dort,
  wo die Wachen sind, und der MCP ist nur die Hand.
  Seit dem 22.09.2026 kann `kraken_order_aufgeben` **nicht mehr echt**
  ausführen (nur noch durchrechnen — der alte Weg ist geschlossen), und
  `kraken_order_stornieren("all")` ist gesperrt, weil ein Sammelstorno den
  Schutz-Stop einer offenen Position mitnehmen und eine nackte Position
  hinterlassen kann. Einzelstornos bleiben erlaubt: sie kürzen nur Risiko.
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
| **1. Freigabe Papier → Live** | mindestens 6 Wochen Papierlauf, ≥ 50 abgeschlossene **Handelsrunden** (seit 15.09.2026: ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung, wird nicht mitgezählt und daneben ausgewiesen — `stoerungen.py`, `teile_runden` in jeder Wachenfassung), größter Rücklauf im Papierlauf < `kill_switch_gesamt_usd`. **Runden aus einem Backtest (`Agenten/Handel/daten/backtest/`) zählen NICHT** — sie sind Messung, keine Live-Erfahrung: dieselbe Signalregel auf denselben Kerzen ist kein Lauf, sie ist dieselbe Rechnung ohne Order. Wer sie mitzaehlt, haelt eine Zahl fuer einen Zeitraum, den die Spur nie gelebt hat. **Seit 19.09.2026 auf Max' Anweisung ohne die Netto-positiv-Bedingung** für die Spuren moondev-* (alle), mosaic, gitter, xperp und spot (scanner): dort zählt nur noch die Rundenzahl und der Rücklauf-Deckel, nicht mehr, ob der Papierlauf netto positiv war. **Seit 20.09.2026 entfällt für xperp auch die Rundenzahl** (Max) — dort zählt nur noch der Rücklauf-Deckel. **Seit 20.09.2026 entfällt für kraken ebenfalls die Netto-positiv-, Wochen- und Rundenzahl-Bedingung** (Max) — dort zählt nur noch der Rücklauf-Deckel. Erst wenn die verbleibenden Kriterien erfüllt sind, darf `handel_erlaubt` von Hand auf `true` — je Spur getrennt. | Block `freigabe` in beiden `wachen.json` |
| **2. Drawdown-Ratsche** | Fällt das Konto 15 % unter seinen Höchststand, halbiert `bot.py`/`handeln.py` jede weitere Positionsgröße. Bei `kill_switch_gesamt_usd` wird flach gestellt **und** `handel_erlaubt` auf `false` geschrieben — der einzige Fall, in dem ein Skript diese Datei schreibt, und nur in diese Richtung. | `bot.py`, `handeln.py` |
| **3. Herzschlag** | Liegt der letzte gesunde Lauf länger zurück als `herzschlag_max_minuten` (**seit 14.09.2026: 180 min für Papier-Spuren, 45 min für Spuren mit Handelserlaubnis**), schließt der nächste Start alle offenen Positionen und schaltet auf Papier. Der Wächter startet einen toten Dauerlauf alle 30 min neu, ein Zyklus dauert 1–2 min — eine Störung heilt nach höchstens ~32 min von selbst; wer darunter geht, stellt bei *jeder* Störung flach und bucht eine Runde, die keine Handelsentscheidung war. Die Regel steht im Feld `_herzschlag_regel` jeder `wachen.json`. Deckt die Kernel-Power-41-Abschaltungen ([[Hardware]]) ab: eine Position, die einen Neustart „überlebt", ist unbewacht. | `handeln.py` prüft `zustand.json` vor dem Start |
| **4. Journal außer Haus** | Das Handelsjournal wird nach jedem Zyklus auf ein zweites Ziel gespiegelt. `G:` genügt nicht — dasselbe Gehäuse. Ein Journal nur auf dem Handelsrechner ist kein Nachweis, sondern eine Wette darauf, dass die Platte hält. | Zeile in `Routinen/`, Ziel offen bis „Kopie außer Haus" steht ([[Hardware]]) |
| **5. Wöchentlicher Soll-Ist-Abgleich** | Einmal pro Woche die vier Pflichtzahlen (Liquidationsabstand, Funding, Gebühren, Trefferquote) gegen das real Erreichte. Liegt der gleitende 30-Runden-Erwartungswert **der Handelsrunden** (seit 15.09.2026 ohne Herzschlag-Zwangsschlüsse) nach Kosten unter null, fällt die Spur automatisch auf Papier zurück, bis ein neuer Papierlauf nach Bedingung 1 trägt. | Skript in `Routinen/`, Befund nach `Werkstatt/`, Entscheidung nach `Wissen/` |

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

**Der Herzschlag hat eine Folge, die man kennen muss:** Läuft `dauerlauf.py`
nicht, stellt der nächste Lauf zuerst alles flach. Bis zum 14.09.2026 standen
hier 30 Minuten — bei einem Wächter, der einen toten Dauerlauf alle 30 Minuten
neu startet, und einem Zyklus von 1–2 Minuten war das enger als die
Selbstheilung. Am 11./12.09.2026 hat die Spur genau deshalb Papierrunden ohne
Anlass geschlossen und die 50 Runden aus Bedingung 1 verdorben, statt sie zu
sammeln. Seit dem 14.09.2026 gelten **180 Minuten in Papier** (Bedingung 3
oben): ein von Hand gestarteter Lauf sammelt jetzt Runden, statt sie
wegzuwerfen. Auf live gehört diese Spur auf 45. Damit ist T-032 erledigt.

**Spur 3 (Kraken), seit 02.09.2026:** Bedingung 1–5 sind umgesetzt und laufen
über dieselbe Rechnung wie Spur 1 — `kraken/wachen_kraken.py` importiert
`scanner/wachen_pruefung.py`, statt sie abzuschreiben; eigen sind dort nur
Währung, Journalspalten und die Datei, in die `sperre_zu` schreibt. Die vier
Freigabewerte sind alle noch offen: Der Papierlauf hat am 02.09.2026 begonnen,
Bedingung 4 (`journal_zweitziel`) ist seit dem 13.09.2026 gesetzt
(`Q:\Handel_Journal\kraken`, Kopie läuft nach jedem Zyklus), und das freie
EUR-Guthaben liegt unter der Schwelle. `handeln.py --wachen` zeigt den Stand,
`--vorschau` nennt jede Sperre, die Live gerade verschließt.

**Seit dem 14.09.2026 läuft sie wieder als Papier — im Dauerlauf.** Sie war
vom 03.09.2026 bis dahin stillgelegt: `stillgelegt: true` verweigerte jeden
Papier- und Live-Lauf (Grund und Rückrechnung in `kraken/wachen.json`,
`_stillgelegt_grund` — ohne Gebühr gerechnet stand der beste Wert bei
−0,57 % je Runde). Drei Dinge sind mit dem Wiederanlauf neu und gehören zur
Spur: sie steht wieder in `dauerlauf.SPUREN` und wird alle 15 Minuten geprüft
(Stop und Ziel greifen damit durchgehend statt einmal am Tag), ihr Herzschlag
steht auf **180 Minuten** — seit dem 14.09.2026 der Wert für alle Papier-Spuren,
weil der Wächter einen toten Dauerlauf nach höchstens rund 32 Minuten selbst neu
startet (Bedingung 3 oben), und den Einstandskurs nimmt sie vom **lebenden
Kurs**, nicht mehr aus der Tagesrangliste; die wählt nur noch aus (Score,
Volatilität, Chance/Risiko) und darf höchstens drei Tage alt sein. Gehandelt
wird ausschließlich auf Papier (`handel_erlaubt: false`,
`freigabe.erfuellt: false`).

**Kraken-Paper-Node (Papierbuch, Stand 13.10.2026):** `Handel/nautilus_kraken`
läuft quote-only gegen Kraken (Spot und Futures). Die Fills simuliert
`papierbuch.py`: Kauf zum Ask, Verkauf zum Bid, 0,26 % Taker-Gebühr je Seite,
nur Long, 1000 Kapital. Gekauft und verkauft wird nach SMA 4/16 auf 15-Minuten-Mids
mit 0,4 %-Band; die Gewinnanzeige steht im Leitstand.
**Warum:** Die alte Strategie (SMA 10/30 auf 1-Minuten-Mids) verlor im Spot-Lauf
46,02 € in 8 Trades, fast nur durch Gebühren. Im Backtest über 7,5 Tage
(15-Minuten-Kerzen) kam die neue Strategie ohne Band auf 35 Trades und −209 €,
mit Band auf 1 Trade und +10 €; Buy&Hold lag bei −35 €. Die alten Bücher liegen
archiviert als `*.v1-20261012.*`.

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

## Backtest-Urteile und die Freigabefelder (15.09.2026)

Drei Spuren haben einen eigenen Backtest-Motor: **gitter**
(`backtest_gitter.py`), **orbk** (`backtest.py`), **nautilus**
(`backtest_grid.py`). Ihre Urteile landeten bisher nirgends — auf der Konsole
(gitter, orbk) oder in einer Datei im eigenen Repo (nautilus) —, und
`freigabe.backtest_bestanden` stand in allen `wachen.json` auf `false`: **es gab
keinen Schreiber.** `orbk/wachen_orb.freigabe_voll_erfuellt()` liest das Feld seit
jeher; ohne Schreiber konnte die Bedingung nie wahr werden.

Neu: `Agenten/Handel/backtest_urteile.py`, wöchentlich aufgerufen aus
`Routinen/handel-wachen.ps1` (die Ausgabe steht danach im Log).

- Es fährt jeden Motor mit den **Werten der Spur**, nicht mit den Vorgaben des
  Skripts. Beim Gitter nimmt es die im Zustand gesetzte Leiter — die ist die
  laufende Strategie (so kam der Widerspruch unten heraus).
- Maßstab je Motor: **Gitter** = besser als Buy-and-Hold (so steht es im Motor
  selbst: „Ein Grid, das schlechter ist als schlicht halten, hat seinen Zweck
  verfehlt"), **ORB** = mindestens ein Instrument mit dem eigenen `URTEIL: Ja`.
- Geschrieben werden in die `wachen.json` der Spur **nur** `backtest_bestanden`,
  `backtest_urteil` und `backtest_geprueft_am` — byte-genau, mit Sicherung und
  JSON-Gegenprobe vor dem Schreiben. `handel_erlaubt` und `freigabe.erfuellt`
  bleiben unberührt; scharf schaltet weiterhin nur ein Schritt von Hand.
- Kann ein Motor nicht laufen, bleibt der **alte Wert stehen** — ein Netzfehler
  darf ein bestandenes Urteil nicht stillschweigend zurücknehmen.

Erster echter Lauf, 15.09.2026:

| Spur | Urteil | Zahl |
|---|---|---|
| gitter | nicht bestanden | +2,19 % gegen Halten +15,79 % (7 Zyklen, 12 Stufen) |
| nautilus | **bestanden** | +1.425 USDT gegenüber Halten (Halten −31,95 %) |
| orbk | nicht bestanden | kein Instrument bestanden (6 geprüft, überwiegend zu wenig Daten) |

Zwei Befunde aus dem Lauf:

- **`gitter/wachen.json` sagt `stufen: 6`, die laufende Leiter hat 12.** Der
  Motor fährt `gitter/handeln.py` selbst, also gilt die Leiter aus
  `zustand.json`; das Urteil rechnet damit und nennt den Widerspruch im Text.
  Ein Zurücksetzen der Leiter würde die Strategie still ändern — die Zahl in der
  `wachen.json` gehört auf den laufenden Stand (Entscheidung von Max).
- **orbk braucht Material, kein neues Signal:** ETH_USD 7 Sessions, Trefferquote
  42,9 %, Break-even nötig 24,1 %, EV +6,05 Punkte je Runde. Das „Nein" heißt
  „unter 10 Verlierer", nicht „Strategie trägt nicht".

Spuren ohne Motor (kein Urteil möglich): xperp, swap, kraken, spiegel,
omniquant, kopier, kopier1zu1, orb sowie die vier am 15.09.2026 angelegten
Indikator-Spuren macd_mtf, squeeze, supertrend, wavetrend (gebaut, getestet,
noch nicht im Dauerlauf). Für **scanner** gibt es den Verbesserer — sein Weg ist
ein Vorschlag per Telegram, kein Urteil in der `wachen.json`.

## Was die Bücher am 14.09.2026 hergeben — und was daraus geändert wurde

Erstmals liegen die Zahlen **aller** Spuren nebeneinander. Das Werkzeug dafür ist
`Agenten/Handel/auswertung_alle.py` (aus dem Handel-Ordner:
`scanner/.venv/Scripts/python.exe auswertung_alle.py`). Es liest die Journale der
Spuren, die keine eigene Auswertung haben (xperp, swap, scanner, kraken, orbk,
gitter, nautilus), paart Einstieg und Ausstieg je Instrument und rechnet mit der
Kostenrechnung, die **in der Zeile steht** — nicht mit einer Schätzung. spiegel,
omniquant und gitter behalten ihre eigene `auswertung.py`.

Geschlossene Runden, Stand 14.09.2026:

| Spur | Runden | Treffer | Ergebnis | Ausstiegsgründe |
|---|---|---|---|---|
| xperp | 20 | 55 % | +45,53 USD (+5,05 %) | herzschlag_alt 12, ziel 4, stop 4 |
| swap | 3 | 33 % | −6,59 USD | stop 2, herzschlag_alt 1 |
| scanner | 14 | 64 % | +111,81 USD (+8,95 %) | ziel 9, stop 5 |
| kraken | 9 | 56 % | +4,00 USD | **5 davon sind Testläufe** (12./14.09.) |
| orbk | 15 | 53 % | +7,20 USD | ziel 8, stop 7 |
| spiegel | 107 | 39 % | +10,98 % | ziel 36, stop 58, frist 13 |

Ohne geschlossene Runden: **omniquant** (erste Ausstiege erst nach der
Haltegrenze von 14 Tagen), **gitter** (frisch aufgelegt), **nautilus** —
bauartbedingt: die Spur fährt den OKX-DEMO-Node ohne Live-Strategiezweig und
sammelt Quotes, sie kann keine Runden liefern.

### Störungen stehen daneben, nicht darin

Zählte man die Journalzeilen, käme man auf mehr Runden als gehandelt wurden:
**ein Herzschlag-Zwangsschluss ist keine Handelsentscheidung**, er entsteht,
weil der Dauerlauf stand, und landet trotzdem als Runde im Journal. Stand
15.09.2026 (`python stoerungen.py` aus `Agenten/Handel`):

| Spur | Buchungen | Handelsrunden | Störungen |
|---|---|---|---|
| xperp | 23 | 11 | 12 (alle `herzschlag_alt`) |
| kraken | 10 | 2 | 8 (vier am 12.09., vier am 14.09.) |
| swap | 5 | 4 | 1 |
| scanner | 14 | 14 | 0 |
| orbk | 3 | 3 | 0 |
| alle Spuren zusammen (mit spiegel 257, kopier 3, kopier1zu1 2) | 317 | 296 | 21 |

Die Richtung der Verzerrung ist **nicht vorhersagbar**, deshalb wird beides
gezeigt. Gemessen am 15.09.2026 über die Runden selbst
(`sum(r["gv"])` je Gruppe):

* **kraken**: die 8 Zwangsschlüsse trugen **+4,59 EUR**, die zwei echten Runden
  **−4,50 EUR** — das Buch sah geschminkt aus, und die Störungen waren die
  einzige gute Zahl darin.
* **xperp**: umgekehrt, aber schwächer. Die 11 Handelsrunden trugen
  **+39,50 USD**, die 12 Störungen **+4,73 USD** — je Runde sank der Wert von
  **+3,59** auf **+1,92 USD**. Die Störungen waren nicht das Vorzeichen,
  aber die Höhe.

Eine Bilanz, die nur eine der beiden Zahlen nennt, hängt damit von der
Vorfallshistorie ab.

Die drei Orte, an denen die Trennung wirkt:

1. `Agenten/Handel/stoerungen.py` — die **eine** Fassung des Merkmals
   (`ist_stoerung`, `teile_runden`) plus die Übersicht mit der Häufung nach
   Tag. Die Häufung **ist** die Fehlersuche: alle 21 Störungen liegen in einem
   Vorfallsfenster, keine außerhalb.
2. Die Wachenfassungen (`scanner/wachen_pruefung.py`, `xperp/wachen_xperp.py`,
   `kraken/wachen_kraken.py`, `orbk/wachen_orb.py`) liefern `runden_echt`,
   `runden_stoerung`, `runden_papier_echt` und `rollierender_ev_echt`;
   `handeln.py --wachen` und der Tagesbericht zeigen Handelsrunden **und** die
   Störungen dazu.
3. `auswertung_alle.py` zählt die Störungen unter der Rundenzahl aus.

**Was ausdrücklich NICHT gefiltert wird: die Kapitalkurve.** Drawdown-Ratsche,
Höchststand und Kill-Switch rechnen weiter auf **allen** Buchungen — eine
Störung ist gebucht und hat Geld bewegt; wer sie aus der Kurve nimmt, schönt
genau das Risiko, gegen das die Sicherung gebaut ist. **Bedingung 5** dagegen
(rollierender Erwartungswert < 0 → Sperre zu) rechnet seit dem 15.09.2026 auf
den **Handelsrunden**: ein Herzschlag-Zwangsschluss ist keine
Handelsentscheidung und darf die Sperre nicht auslösen (Entscheidung von Max am
15.09.2026, umgesetzt in allen vier Wachenfassungen — scanner, xperp, kraken,
orbk). Die Zahl über alle Buchungen steht daneben als `rollierender_ev_alle`;
die Sperrzahl heißt weiter `rollierender_ev` („n/a" unter fünf Handelsrunden).

### Die Geometrie jeder Spur trägt

Vor jeder Parameteränderung die Gegenprobe: welche Trefferquote braucht die
Geometrie, um die Kosten zu tragen — und was ist gemessen?

- xperp/swap: Stop 1,5 ATR, Ziel 3,0 ATR → **Break-even 33 %**, gemessen 55 %.
- scanner: Stop 5–12 %, Ziel ≥ 1,5 R → **Break-even ≤ 40 %**, gemessen 64 %.
- orbk: Ziel 1,5 R → **Break-even 40 %**, gemessen 53 %.
- spiegel: Stop 25 %, Ziel 60 % → **Break-even 29 %**, gemessen 39 %.

Keine Spur hat nach ihren eigenen Zahlen eine negativ erwartete Geometrie. Der
Grund, warum xperp trotzdem mager aussieht (Median +0,10 % gegen Mittel +5,05 %),
sind die **12 Herzschlag-Ausstiege von 20** — der Wert war mit 30 Minuten enger
als die Selbstheilung (Bedingung 3). Das ist seit dem 14.09.2026 behoben; die
Zahlen davor messen die Störung, nicht die Strategie.

### Geändert

**spiegel: Marktkapitalisierung nur noch bis 1 Mio USD.** Das Band stand auf
`[50000, 20000000]` und ist ein echtes Tor (`spiegel.py`). 107 Runden, gepaart
mit dem Einstiegspreis: unter 1 Mio **88 Runden, 63 Token, Ø +16,5 %** (unter
250k Ø +14,72 %, 250k–1M Ø +20,41 %); 1M–5M **15 Runden, 11 Token, Ø −12,32 %**;
ab 5M 4 Runden, 2 Token, Ø −22,29 %. Es liegt nicht an den Kosten — Slippage und
Gebühr sind feste Sätze und treffen jedes Band gleich —, sondern am Ziel: über
1 Mio wurde das Ziel von +60 % in 17 Runden **zweimal** erreicht, unter 1 Mio in
88 Runden 34 mal; dort läuft stattdessen der Stop. Offene Positionen über 1 Mio
bleiben stehen und laufen in Stop, Ziel oder Frist aus. Herleitung als
`_marktkap_band` im Wachen-File.

**spiegel: Papier sammelt mit mehr Plätzen, live behält das Muster.** Das
Ablehnungsprotokoll der ersten echten Zyklen zeigte den Engpass an einer Stelle,
die im Journal unsichtbar war: von 706 Signalen je Zyklus waren 5 bis 58
„kaufbar", das Buch stand dauerhaft auf 20/20, und der Zyklus brach beim ersten
Platzmangel ab — alles danach fiel als „kaufbar, aber nicht mehr erreicht" aus.
Der Durchsatz hängt an den Plätzen (Runden/Tag = Plätze × Umschläge je Platz,
beobachtet rund 2), nicht am Tor. Das Papierbuch sammelt deshalb mit **60
Plätzen** (rund dreifacher Ertrag: 30–55 → 90–165 geschlossene Runden je Tag);
die Notbremse zieht im selben Anteil mit (300 USD bei 3.000 USD Nominal) — sonst
hätte sie die Messung nach acht Stops selbst beendet. **Geändert wird nur die
Kapazität**: Tore, Stop, Ziel, Frist, Kosten und Einsatz bleiben unverändert,
sonst wäre die Messung eine andere Strategie und nicht mehr übertragbar. **Das
Muster (20 Plätze, 100 USD) gilt automatisch wieder, sobald `handel_erlaubt:
true` wird oder `--live` läuft** — die Rücknahme ist also der Schalter, der die
Spur auf Geld stellt, kein zweiter Wert zum Nachziehen. Herleitung als `_umfang`
in `wachen.json` (Schlüssel `max_offen_papier`,
`kill_switch_gesamt_usd_papier`).

**spiegel: die Verfolgungsliste wird im Zyklus selbst erneuert.** Sie ist ein
*Fenster* auf den Feed, kein Stammbuch: die Fassung vom 12.09.2026 hatte 305
Wallets, im Feed handelten am 14.09.2026 206 Wallets, davon 154 nicht in der
Liste — **472 von 706 Signalen je Zyklus** fielen als „Wallet nicht verfolgt"
aus, zwei Drittel des Feeds. Der Zyklus baut die Liste jetzt neu, sobald sie
älter ist als `verfolgte_max_alter_stunden` (1 h, rund zehn Abrufe je Neubau,
~240 Abrufe je Tag); die Vorschau baut nichts. Offene Kopien bleiben unberührt
— sie tragen Stop, Ziel und Frist selbst. **Rücknahme:** die Grenze sehr groß
setzen lässt die Liste stehen, bis jemand `--waehlen` ruft.

**scanner und kraken: der Börsen-Stop wird aufgeräumt.** Beide setzten den
Notausstieg schon mit der Order an den Handelsplatz — aber scanner warf die
`algoId` weg (kein Storno möglich, der Stop blieb nach jedem Ausstieg im Buch),
kein Ausstieg stornierte ihn, und loeste er zwischen zwei Zyklen aus, blieb die
Position als Karteileiche im Buch, weil der eigene Verkauf scheiterte. Kraken
hatte Stornieren und Verkaufen in einem `try`: ein nicht stornierbarer Stop
brach den Verkauf ab. Jetzt in beiden Spuren: Stop stornieren → verkaufen → bei
Fehlschlag nachsehen, ob der Börsen-Stop gefüllt hat (dann Ausstieg
„stop (boerse)"). Ein Kauf ohne Stop wird zurückverkauft; geht auch das schief,
steht die Position als `boersen_stop_fehlt` im Buch — eine Position am Markt, die
im Buch fehlt, ist der schlimmere Zustand. Tests:
`scanner/tests/test_handeln_boersenstop.py`, `kraken/tests/test_handeln_boersenstop.py`.

**Testläufe dürfen die Kopie außer Haus nicht anfassen.** Beim Auswerten
aufgefallen: die Testsuiten von **spiegel und omniquant** riefen `lauf("papier")`
mit einer Wachen-Kopie, die das **echte** `journal_zweitziel`
(`Q:\Handel_Journal\<spur>`) behielt. Jeder `discover`-Lauf überschrieb damit die
Außer-Haus-Kopie mit Tempdaten — bei omniquant Zustand **und** Journal, bei
spiegel der Zustand (gemessen: 13.816 → 222 Byte). Das trifft direkt Bedingung 4,
und es fällt nicht auf: die Tests waren grün, die Spur im Dauerlauf auch. Die
echten Dateien sind zurückgespielt (byte-gleich), die Test-Wachen zeigt jetzt auf
einen Temp-Ordner — der Spiegelpfad bleibt damit getestet. Nachweis: alle Suiten
laufen lassen und danach `spiegelstand.py` aufrufen; es muss byte-gleich melden.
Nachgestellt am 14.09.2026: ohne den Fix schreibt der spiegel-Testlauf Q: wieder
kaputt, mit Fix nicht.

**omniquant: alte Zustandsdateien.** `lade_zustand()` ergänzt fehlende Felder
(`verluste_usd`, `positionen`, `modus`, `letzter_lauf`) wie `gitter/handeln.py`.
Dazu eine Testfalle geschlossen: `gui.py` legt beim Import den scanner-Ordner auf
den Suchpfad, deshalb lud `tests/test_gui_bindung.py` einzeln aufgerufen
**scanner/handeln.py** und prüfte still die falsche Spur. Der Test prüft jetzt
die Herkunft des Moduls.

### Bewusst nicht geändert

- **Keine Parametersuche auf dünnen Stichproben.** swap (3), kraken (9, davon 5
  Testläufe), scanner (14), orbk (15) — unter der Hausregel von 8 Runden ist das
  kein Maß, und darüber ist die Streuung größer als der Effekt. Die wöchentliche
  Suche des Verbesserers (`Agenten/Handel/verbesserer`, derzeit nur Spur 1) ist
  der Ort dafür, nicht die Hand.
- **`mindest_score` 60 im scanner bleibt.** Das Tor hat nie gegriffen: der
  niedrigste eingegangene Score im Journal ist 68,4.
- **Wallet-Auswahl im spiegel bleibt.** Der Schnitt über 107 Runden zeigt zwei
  starke Wallets (+15,06 % / +28,20 %) und mehrere schwache mit 2–5 Runden — bei
  19 Gruppen wäre das Aussortieren nach Sicht ein Kurvenfit, kein Befund.
- **Die Slippage-Annahme (3 %) bleibt.** Sie ist ein fester Satz je Runde und
  kann die Bandrangfolge nicht drehen; sie niedriger zu setzen, um Zahlen zu
  verbessern, wäre das Gegenteil von Messen.
## Risikostufen: derselbe Handel, andere Buchgroesse (15.09.2026)

**Auftrag Max:** denselben Dauerlauf mehrfach fahren, mit unterschiedlicher
Risikobewertung und groesseren Positionen je Spur - **ausser Spiegel** - um
schneller Daten zu sammeln.

**Der Gedanke:** nicht mehr Gewinn, sondern mehr Beobachtungen je Zeiteinheit.
Bei 20-EUR-Einsaetzen dauert jede Statistik Monate; bei 80 EUR sieht man
denselben Fehler viermal schneller. Die Strategien bleiben unangetastet -
dieselben Wachen, dieselben Regeln, nur ein Faktor auf die Betraege.

**Wie:** `Agenten/Handel/risikostufe.py`. Der Dauerlauf setzt je Stufe
`HANDEL_RISIKO=niedrig|mittel|hoch` (Faktor 1 / 2 / 4); jede Spur skaliert beim
Laden ihre Wachen und schreibt Zustand und Journal mit Suffix
(`zustand.mittel.json`, `handelsjournal.mittel.csv`). Ohne die Variable aendert
sich **nichts** - der laufende Betrieb wird von der Umstellung nicht angefasst.
Der Dateiname muss getrennt sein: zwei Laeufe auf derselben `zustand.json`
wuerden sich die Positionen gegenseitig ueberschreiben.

**Was NICHT skaliert wird** (an den echten Wachen nachgemessen, nicht geraten):
`marketcap_band_usd` (Marktgroesse des Tokens, kein Einsatz),
`groesster_ruecklauf_papierlauf_*` (eine Messung, kein Limit - skaliert waere
sie eine Behauptung ueber die Vergangenheit), `mindest_guthaben_*` /
`mindest_marge_frei_*` (Kontoschwellen der Boerse), `umsatz_bezug_usd`,
`punkt_wert_usd`. Felder mit fuehrendem Unterstrich (`_risiko_je_position_usd`)
sind der dokumentierte Vorwert und bleiben ebenfalls.

**Was MIT muss:** `drawdown_halbierung_usd` und `kill_switch_gesamt_usd`. Sie
sind in Buchrisiko ausgedrueckt (1,0x, siehe `Handel/ratschen.py`). Blieben sie
stehen, wuerde die doppelte Position die Halbierung sofort ausloesen - die
Stufe waere nach dem ersten Verlust gesperrt und lieferte keine Daten mehr.

**Stand:** Angeschlossen (15.09.2026). `risikostufe.py` ist die eine Umsetzung,
`Agenten/Handel/tests/test_risikostufe.py` faehrt ueber JEDE Spur (23 Tests:
Dateinamen und Wachen-Funktion, in beiden Richtungen). Jede Spur laedt
`risikostufe` ueber den PFAD (wie `ratschen.py`), schickt ihre Wachen durch
`skaliere(...)` und bildet ihre Dateinamen ueber `datei(...)`:

| wer | was |
|---|---|
| `dauerlauf.py --risiko mittel` | setzt `HANDEL_RISIKO` fuer sich und die Kindprozesse; eigene PID-, Log- und Zustandsdateien |
| `Routinen/handel-dauerlauf.ps1 -Risiko mittel` | eigener Waechter-Aufruf, Sperre `dauerlauf.mittel.pid` |
| `spiegelstand.py --risiko mittel` | prueft die Q:-Kopien der Stufe (Bedingung 4) |
| `auswertung_alle.py --risiko mittel` | rechnet die Stufenjournale, gleiche Rechnung |
| `auswertung.py` in kopier/kopier1zu1/omniquant/gitter | dito, ueber die Umgebungsvariable |

**Eine Stufe geht NIE live** (`risikostufe.live_erlaubt()`): der Dauerlauf
uebergibt auch bei offenem Freigabefenster `--papier`. Der Grund ist nicht
Vorsicht allein — das Buch der Stufe ist getrennt, live gehandeltes Geld
stuende in keiner Auswertung.

**Kein Telegram in der Stufe:** kein Senden, kein Abholen von Befehlen, keine
Freigabe-Anfrage, und beim Beenden werden die Freigabefenster NICHT
geschlossen (sie gehoeren dem Basislauf). Zwei Laeufe an einem Bot nehmen sich
sonst die Nachrichten weg (Telegram antwortet dem zweiten Abrufer mit 409).

**Spiegel:** bleibt bei Faktor 1,0 (Max' Vorgabe) und lief **nur im
Basislauf** (`dauerlauf.NUR_BASIS`). Liefe er in allen Stufen mit, entstuenden
drei identische Buecher — dieselbe Beobachtung dreimal, dazu zwei Schreiber
auf denselben Dateien. `spiegel.py` bricht in einer Stufe mit Klartext ab.

**Seit 21.09.2026 laufen die drei Spiegel-Arme nicht mehr** (`spiegel`,
`spiegel_knapp`, `spiegel_weit` stehen nicht mehr in `dauerlauf.SPUREN`,
`NUR_BASIS` ist leer). Max: „spiegel Spuren erstmal deaktivieren". Die Buecher
bleiben als Vergleichsgrundlage liegen und wachsen nicht weiter; Bedingung 4
fuehrt das Hauptbuch weiter als „ausserhalb des Dauerlaufs mitgeprueft"
(`spiegelstand.py`: 27 von 27 byte-gleich, `spiegel` und `orb` daneben).

**Ergebnis der Schattenbuecher (ausgewertet 21.09.2026, Ausstiegsgeometrie V1).**
Gefahren mit `Agenten/Handel/spiegel/auswertung.py --pfad handelsjournal[.knapp|.weit].csv`
(die Arme spiegeln dieselbe Signalquelle, nur Stop/Trailing unterscheiden sich;
Hauptbuch 15/30/25, knapp 8/15/15, weit 25/40/30):

| Buch | Ausstiege | nach Kosten | vor Kosten | Treffer |
|---|---|---|---|---|
| Hauptbuch | 1153 | **-9,22 %** | -1,66 % | 26 % |
| knapp 8/15/15 | 358 | **-8,95 %** | -1,37 % | 22 % |
| weit 25/40/30 | 98 | **-10,46 %** | -3,00 % | 35 % |

Befund: **kein Arm traegt.** Die Kosten allein machen rund 7,5 Prozentpunkte aus
(Hauptbuch: 4.359,78 USD auf 57.650 USD Einsatz). Die Ausstiegsgeometrie bewegt
nur etwa 1,5 Punkte - knapp ist der beste Arm, liegt aber im Rauschen des
Hauptbuchs, weit ist deutlich schlechter. Der Hebel liegt NICHT in der
Geometrie, sondern beim Einstieg und bei den Kosten:

- **Stop-Ausstiege sind der groesste Verlustposten** (Hauptbuch 637 Stueck zu
  Ø -44,59 %; knapp Ø -30,73 %; weit Ø -58,06 %). Wer einen Stop bei -8 % setzt
  und dann im Mittel -31 % bis -58 % bucht, hat kein Stop-Problem, sondern ein
  Ausfuehrungs-/Slippage-Problem - die Annahme in `wachen.json` ist zu freundlich.
- **Tiefe unter 250k Marktkapitalisierung ist das Verlustbecken**: 610 Kopien,
  Ø -20,50 % (vor Kosten -13,88 %). Das Band wurde am 16.09.2026 bereits auf
  250k-1M eingeengt; die Schattenbuecher liefen genau dort (Ø -8,95 % knapp,
  -10,46 % weit) und bleiben trotzdem negativ.
- **Zwangsschluesse (`herzschlag_alt`) sind harmloser als Stops** (+6,22 %,
  180 Stueck) - die Notausstiege haben das Bild nicht verdorben.

Folge: die Arme bleiben aus. Wer sie wieder einschaltet, soll zuerst die
Slippage MESSEN, nicht die Parameter drehen - dieselbe Reihenfolge wie beim
Gitter (dort war der Parameter ebenfalls nicht der Hebel).

**Gemessen (21.09.2026, `spiegel/slippage_messen.py`, Pool-Tiefe live von
DexScreener, Round-Trip-Naeherung 2 x Order / Quote-Tiefe):**

- Stichprobe: die 80 juengsten Einstiege des Spiegel-Buchs. Pool-Tiefe Median
  **62.900 USD** (p25 34.500, p10 9.800, min 5 USD).
- Preiseinfluss 50 USD: **Median 0,33 %** (p25 0,27 %, p75 0,94 %). Bei 100 USD
  0,67 %, bei 500 USD 3,34 %.
- Die Annahme im Wachenbuch (3 % je Seite, also 6 % Round Trip) ist fuer den
  Median-Handel **rund fuenf Prozentpunkte zu streng**. Sie beschreibt nicht
  den Normalfall, sondern den Rand.
- Der Rand ist aber kein "3 % teurer", sondern **kein Fill**: 7 von 77 Pools
  lagen unter 5.000 USD Tiefe (9 %), 4 davon unter 2.000 USD. Bei 50 USD Order
  ist das nicht teuer, sondern nicht ausfuehrbar.

Folge fuer die Bewertung: mit gemessenen Kosten (2 x 0,33 % Impact + 2 x 1 %
Gebuehr ~ 2,7 % Round Trip) bleibt das Buch negativ, aber bei etwa -4,4 %
statt -9,22 %. Das Urteil "Arme bleiben aus" haelt; die Zahl "wie schlimm"
war jedoch vom Modell gepraegt, nicht vom Markt. Wer den Kostensatz im
Wachenbuch korrigiert, gehoert dazu: Groesse gegen Tiefe rechnen und Kopien
ohne Tiefe (< 5 x Order) als NICHT ausfuehrbar zaehlen, statt sie mit 3 % zu
bepreisen.

**Zeitversatz (21.09.2026).** Gemessen wird er seit dem mit
`Agenten/Handel/zeitversatz_messen.py` (Cron `zeitversatz-sammeln`, alle 10
Minuten, sammelt leise nach `Agenten/Handel/zeitversatz.csv`). Er holt fuer die
juengsten Einstiege der Kopier-Spuren den aktuellen Marktpreis und schreibt je
Einstieg und Altersstufe (0-5, 5-15, 15-30, 30-60, 60-180, 180-720 min) eine
Zeile; `--bericht` rechnet daraus den Median der Kursaenderung gegen den
Signalpreis.

Bereits gemessen (ohne dieses Werkzeug, aus `kopier1zu1/handelsjournal.csv`):
der Verzug zwischen dem Kauf des Vorbilds (`trade_zeit`) und unserer Buchung
(`zeit`) ist **Median 566 s, p75 777 s** - die Kopier-Spuren entdecken einen
Kauf erst beim naechsten Abruf, und der Dauerlauf laeuft im 15-Minuten-Takt.

Und der eigentliche Befund: `kopier1zu1` bucht den Einstieg nicht mit dem
Marktpreis, sondern mit `preis_vorbild * 1,05`. Die 5 % stehen in JEDER Zeile
identisch - das ist eine gesetzte Zahl, keine gemessene. Erst der Sammler sagt,
ob sie reicht. Erste Stichproben (Alter 1-12 h, also nicht der eigentliche
Verzug): Median -2,97 % im Band 60-180 min und -15,61 % im Band 180-720 min -
der Kurs laeuft in der Wartezeit eher weg als hoch. Die Baender unter 15
Minuten fuellen sich mit den naechsten frischen Signalen.
Dafuer fehlt eine Vorwaerts-Messung, die den Preis bei Signal und nach 1/5/15
Minuten nebeneinander schreibt.

Wieder einschalten: die drei Zeilen in `SPUREN` und `NUR_BASIS` einkommentieren
(der Weg steht als Kommentar an beiden Stellen in `dauerlauf.py`) — UND vorher
`letzter_lauf` in `spiegel/zustand.json`, `zustand.knapp.json` und
`zustand.weit.json` auf jetzt setzen. Ohne diesen Schritt gilt der Herzschlag
nach mehr als 180 Minuten als alt und der erste Zyklus stellt alle offenen
Papierpositionen flach (`spiegel.py`, `flach_stellen "herzschlag_alt"`) — die
Vergleichsbuecher waeren dann weg. Danach `dauerlauf.py` neu starten (nur der
Treiber liest `SPUREN`).

**Betrieb (Stand 15.09.2026, 23:59):** Der zweite Lauf ist **gestartet** und
hat eine eigene Waechter-Aufgabe, `MaxHirn-Handel-Dauerlauf-Mittel-Waechter`
(Anmeldung + alle 30 Minuten, ruft `Routinen\handel-dauerlauf.ps1 -Risiko
mittel`; erkennt am `dauerlauf.mittel.pid`, wenn schon einer laeuft). Der
Basislauf bleibt unveraendert daneben. Zu beachten:

- Er kostet Rechenzeit und Netz auf derselben Maschine (Kernel-Power-41-Risiko,
  siehe `Wissen/Hardware.md`) - er ist kein Ersatz fuer den Basislauf.
- Wird er nicht gebraucht: Aufgabe deaktivieren (`Disable-ScheduledTask
  -TaskName MaxHirn-Handel-Dauerlauf-Mittel-Waechter`) und den Prozess aus
  `Handel/dauerlauf.mittel.pid` beenden. Die Basis laeuft weiter.
- Seine Buecher stehen NEBEN den Basisbuechern: `zustand.mittel.json`,
  `handelsjournal.mittel.csv`, gespiegelt nach `Q:\Handel_Journal\<spur>`.
- Die Stufenbuecher der ersten Minuten (bis 23:58) wurden verworfen: dort
  schrieb parallel noch ein Trocken-Testlauf in dieselben Dateien. Eine
  Messreihe, die zwei Schreiber hatte, ist keine.
- Die **Handelszentrale** zeigt beide Buecher: ein Umschalter in der Kopfzeile
  (Basis/mittel/hoch) wechselt die Ansicht, `--risiko mittel` ist der Startwert.
  Der **Tagesbericht** traegt eine eigene Zeile je Stufe (Spuren mit Buch,
  Alter des juengsten Zyklus, geschlossene Runden mit Summe); ohne Stufe bleibt
  sie weg. Die Zahlen kommen aus `auswertung_alle.kennzahlen_fuer`, nicht aus
  einer zweiten Formel.

## Bot-Spuren: geklonte Fremd-Agenten als Papierbuch (16.09.2026)

Max hat die Moon-Dev-Repos installiert und wollte die Bots in den Handelsspuren
sehen. Die Fremd-Agenten sind Sprachmodell-Agenten mit echtem Orderpfad
(Hyperliquid/Solana, echte Schluessel) - beides gehoert nicht in den
Hausbetrieb. Der Weg ist deshalb ein anderer: **die Funktion des Bots rufen,
die Regel im Haus entscheiden lassen, ein Haus-Buch fuehren.**

**Erste Spur: `moondev_funding`** (`Agenten/Handel/moondev_funding/`) - ein
Papierbuch auf den Funding-Extremen von Hyperliquid. Die Zahlen liefert
`src/nice_funcs_hl.get_funding_rates()` aus `Werkstatt/moon-dev-ai-agents`,
gerufen in DESSEN venv (dort liegen pandas und requests); die Regel stammt aus
`fundingarb_agent.py` (ab +-100 %/Jahr) und ist hier deterministisch. Kein
Sprachmodell, kein Orderpfad, ein `--live` verweigert. Sie laeuft als
`moondev_funding` in `dauerlauf.SPUREN` und spiegelt nach
`Q:\Handel_Journal\moondev_funding`.

**Die vier Repos** liegen als Klone unter `Werkstatt/` (origin = Fork
unter `mfaupel95`, upstream = Original):

| Repo | Inhalt | venv / Zustand |
|---|---|---|
| `moon-dev-ai-agents` | 46 Agenten (Quelle der Bots) | `.venv` mit requirements (numpy, pandas, ta-lib, torch/whisper, anthropic, openai ...) |
| `Trading-View-MCP-for-AI-by-Moon-Dev` | MCP-Server fuer TradingView | `.venv` mit requirements (mcp, websocket-client, pydantic) |
| `Harvard-Algorithmic-Trading-with-AI` | Research-/Backtest-Material | keine requirements.txt - nichts zu installieren |
| `Moon-Dev-Code` | Sammlung (PDFs/Strategien), kein Code | keine requirements.txt - nichts zu installieren |

`moon-dev-ai-agents` ist unter seinem alten Namen nicht mehr oeffentlich; die
Quelle ist der Nachbau `yolojewjitsu/moon-dev-ai-agents` (zuletzt 20.10.2025).
Die Datei `.env_example` nennt die Schluessel, die der Bot kennt
(`MOONDEV_API_KEY`, `SOLANA_PRIVATE_KEY`, LLM-Keys) - **keiner davon ist
eingetragen**; Zugaenge stehen ausschliesslich in `Wissen/Zugaenge.md`.

**Grenzen:** Ohne `MOONDEV_API_KEY` fehlen die Daten der
MoonDevAPI-Agenten (liquidation, whale, funding, rbi), ohne LLM-Schluessel das
Urteil der uebrigen. Das ist kein Grund, fremde Schluessel einzutragen: Die
Spur zeigt die Bauform - Bot-Funktion, Haus-Regel, Haus-Buch -, und jede
weitere Spur folgt derselben Vorlage. Moegliche naechste Kandidaten ohne
Fremdschluessel: `coingecko_agent`, `new_or_top_agent` (CoinGecko),
`listingarb_agent` (Binance + CoinGecko).

### Die vier Bot-Spuren (Stand 16.09.2026, nachts)

| Spur | Quelle | Regel |
|---|---|---|
| `moondev_funding` | **echte Bot-Funktion** (`nice_funcs_hl.get_funding_rates`), gerufen im Bot-venv | ab +-100 % Funding im Jahr; positive Rate -> short |
| `moondev_listingarb` | CoinGecko + Binance (oeffentlich) | gross (>= 1 Mrd USD Marktkapital, >= 30 Mio Volumen) und bei Binance nicht handelbar -> long |
| `moondev_topmovers` | CoinGecko (oeffentlich) | +8 % bis +40 % in 24 h bei >= 20 Mio Volumen -> long |
| `moondev_marktlage` | CoinGecko (oeffentlich) | BTC +2 % und Marktbreite >= 60 % -> long; spiegelbildlich short |

Alle vier: Papier, kein Sprachmodell, kein Orderpfad, `--live` verweigert,
eigene Buecher mit Spiegelung nach `Q:\Handel_Journal\<spur>`. Die drei
CoinGecko-Spuren teilen sich `Handel/moondev_daten.py` (Abruf, nur
Standardbibliothek) und `Handel/moondev_buch.py` (Buch, Ratsche, Stop/Ziel) -
eine Buchhaltung fuer alle.

**Vorgemerkt, nicht gebaut:** die uebrigen 42 Agenten des Repos. Sie sind in
`Wissen/Moon-Dev-Agenten.md` nach dem gruppiert, was fehlt (Moon-Dev-API-Schluessel,
LLM-Schluessel, Solana-RPC/Wallet, kein Handelsbezug) - samt dem, was ein
Weiterbau je Gruppe braeuchte. Kein Sprachmodell-Buch und kein Wallet ohne
ausdrueckliche Entscheidung.

## IV-Wand: der Strike mit dem groessten Open Interest (17.09.2026)

**Auftrag Max:** "IV-Wand anschliessen."

**Was sie ist.** Im Optionsmarkt liegt bei einzelnen Strikes sehr viel offenes
Interesse (Open Interest). Dort sitzen die Absicherungen der Marktmacher, und
der Kurs wird von diesen Zonen angezogen oder abgestossen - die "Wand". Die
implizite Volatilitaet (IV) gehoert dazu: Wo viel OI liegt UND die IV hoch ist,
ist die Erwartung des Marktes konzentriert.

**Wie sie gerechnet wird** (`Agenten/Handel/iv_wand/handeln.py`, oeffentliche
OKX-Daten, kein Schluessel):

1. `/public/open-interest?instType=OPTION&uly=BTC-USD` - Open Interest je
   Option (`oiUsd`).
2. `/public/opt-summary?uly=BTC-USD` - implizite Volatilitaet je Option
   (`markVol`).
3. Nur Verfaelle in **7 bis 45 Tagen** (nahe Verfaelle, wo gehandelt wird).
4. Open Interest je **Strike** summieren (Call + Put gehoeren zusammen) - der
   groesste Strike ist die Wand, seine mittlere IV steht als Notiz im Zustand.

**Regel:** Spot unter der Wand mit Abstand <= 5 % -> long, Ziel ist die Wand.
Spot ueber der Wand im selben Abstand -> short, Ziel ist die Wand. Weiter weg
oder genau darauf: kein Geschaeft. Stop 4 % (fester Satz), eine Position.

**Zwei Besonderheiten:** Das Ziel ist ein **Marktpunkt**, kein Vielfaches des
Stops - dafuer hat das gemeinsame Buch (`Handel/spur_buch.py`) den Parameter
`ziel_preis`; ein Ziel hinter dem Einstieg wird abgelehnt statt gebucht. Und
die Spur gehoert zur Familie **Options-Zone**, nicht zu den Bot-Signalen: hier
rechnet kein fremder Bot, sondern der Optionsmarkt.

**Nachweis (16.09.2026 nachts):** Spot 75.678 USD, **Wand 70.000 USD**
(OI 136,5 Mio USD, IV 41,2 %, faellig in 9,3 Tagen, 78 Strikes im Fenster);
Abstand -7,5 % -> korrekt kein Signal. 14 Tests, Bedingung 4: 21 von 21 Spuren
byte-gleich, `pruefe_ratschen` fuehrt sie (5,00 = 1,0x Buchrisiko).

**Grenze:** gehandelt wird der Spot-Papierpreis, nicht die Option. Kein
Live-Zweig.

## Risiko-Vorfilter: die Regeln des Moon-Dev `risk_agent` (17.09.2026)

**Auftrag Max:** "Risk_agent als Vorfilter einbauen."

**Was der Fremd-Agent tut.** `Werkstatt/moon-dev-ai-agents/src/agents/
risk_agent.py` ueberwacht dort jede offene Position und stoppt den Handel, wenn
ueber die letzten **12 Stunden** ein Limit gerissen wird: `MAX_LOSS_USD = 25`,
`MAX_GAIN_USD = 25`, `MAX_LOSS_PERCENT = 5`, `MAX_GAIN_PERCENT = 5`. Ob das
Limit ueberstimmen werden darf, fragt er alle 15 Minuten ein Sprachmodell
(`OVERRIDE` oder `RESPECT_LIMIT`).

**Was hier daraus wurde** (`Agenten/Handel/risikovorfilter.py`): dieselben
Zahlen, dieselbe Frist - **ohne Sprachmodell**. Das Limit gilt; wer es anders
will, setzt einen anderen Betrag in seine `wachen.json`. Geraten wird nichts.

**Warum Vorfilter und nicht Notaus.** Die Spuren begrenzten bisher die
Buchgroesse (Risiko je Position, Plaetze, Gesamtdeckel, Ratsche) - die **Zeit**
fehlte: ein Tag, an dem schon dreimal der Stop traf, handelte munter weiter.
Der Vorfilter greift **vor** dem Einstieg:

1. **Verlustgrenze** im Fenster erreicht -> kein neuer Einstieg.
2. **Gewinnziel** im Fenster erreicht -> kein neuer Einstieg (Gewinn sichern;
   der Bot stoppt hier ebenfalls).
3. **Buchrisiko**: offenes Risiko + neues Risiko > Deckel -> kein Einstieg.

Er schliesst **keine** Position und aendert **keine** Wache. Das ist die Grenze
zwischen Vorfilter und Notaus: Positionen schliessen gehoert dem Kill-Schalter
und der Ratsche.

**Eingeschaltet ist er bei den fuenf Feed-Spuren** (`moondev_funding`,
`moondev_listingarb`, `moondev_topmovers`, `moondev_marktlage`, `iv_wand`) -
jeweils `risikovorfilter: true`, 12-h-Fenster, +/-25 USD und +/-5 %.
**Bei den uebrigen Spuren ist er aus**, und zwar absichtlich: ein Filter, der
stillschweigend drosselt, waere schlimmer als keiner. Einschalten ist ein Feld
(`risikovorfilter`, `risiko_verlust_max_usd`, `risiko_gewinn_ziel_usd`,
`risiko_fenster_stunden`) - danach greift er im naechsten Zyklus.

**Nachweis:** 12 Tests fuer den Vorfilter allein (`tests/test_risikovorfilter.py`
- Paarung Kauf/Verkauf, Zeitfenster, alle vier Grenzen, Buchdeckel, Schalter
aus) plus der Einbau im Buch; die fuenf Spuren 48 Tests, Handel-Suite 83 Tests,
alle gruen.

## Moon-Dev-Sniper: neue Solana-Launches als Papierbuch (19.09.2026)

**Spur `moondev_sniper`** (`Agenten/Handel/moondev_sniper/`) - die Gruppe-C-Spur
aus `Moon-Dev-Agenten.md`: der Fremd-Agent `sniper_agent` scannt neue
Solana-Token-Launches und zeigt sie an (kein eigenes Kaufurteil). Die
Haus-Regel ist deterministisch und nachrechenbar, kein Sprachmodell, kein
Live-Zweig.

**Quelle** (oeffentlich, kein Schluessel):
- `frontend-api-v3.pump.fun/coins?sort=created_timestamp&order=DESC` - die
  neuesten Launches mit Alter, Marktwert und Liquiditaet.
- `swap-api.pump.fun/v2/coins/<mint>/trades?limit=1` - der letzte gehandelte
  Preis (`priceUsd`).

**Regel:** Ein neuer Launch wird **long** gekauft, wenn er jung ist
(`max_alter_minuten`, Vorgabe 60), nicht gebannt/nsfw, Marktwert im Band
(`marktkap_band_usd`, Vorgabe 200-100k USD) und einen Preis hat. Stop/Ziel
ueber `spur_buch` (Vorgabe 8 % Stop, 1.5R Ziel), Buch ueber `spur_buch.py`.

**Verdrahtet:** `dauerlauf.SPUREN`, `auswertung_alle.BOT_SPUREN`,
`pruefe_ratschen` (Ratsche 1.0x Buchrisiko), `befehle.FAMILIE`
(Bot-Signal), `lage.HOLER` (28.), Bus-Anbindung, Spiegelung nach
`Q:\Handel_Journal\moondev_sniper`. Tests 13, Handel-Suite 402, Bus-Suite
gruen, spiegelstand 28/28 byte-gleich.

**Zwei ehrliche Befunde (19.09.2026):**
- **Slippage ist real.** Der Preis kommt vom letzten Swap-Trade. Bei frischen
  Launches mit duenner Liquiditaet rutscht der Kurs zwischen zwei Zyklen
  durch den Stop - der 8-%-Stop wird mit deutlich groesserem Verlust
  ausgefuehrt (gemessen: -37.59 USD bei 62.50 Nominal). Kein Bug, sondern die
  Memecoin-Realitaet.
- **Rate-Limit.** swap-api.pump.fun deckelt hart (HTTP 429). Nur die
  `max_offene_positionen` juengsten Kandidaten bekommen einen Preis, nicht
  alle 40 - sonst reisst der Deckel und die Spur liefert nichts.

**Journal-Praezision:** `spur_buch.pformat()` formatiert Preise mit genug
Nachkommastellen, dass Einstieg und Stop unterscheidbar bleiben. `%.6f`
reichte fuer BTC (60000.000000), nicht aber fuer die Mini-Preise der
Sniper-Spur (~1e-6): dort stuerzten Einstieg und Stop beim Runden auf
denselben String zusammen und die Auswertung haette G/V = 0 gelesen. Grosse
Kurse bleiben 6 Stellen (bestehende Spuren unveraendert), kleine bekommen
mehr.
## Positionen von Hand im Konto (21.09.2026)

Nicht jede offene Position kommt von einer Spur. Wer in der OKX-Kontouebersicht
etwas findet, das im Buch keiner Spur steht, sucht zuerst hier - sonst wird eine
selbst gesetzte Position beim naechsten Audit als Fehler gemeldet.

- **FIL-USD_UM_XPERP** (OKX, XPERP-Kontrakt, `mgnMode=isolated`, Margin-Waehrung
  **USDC**): von Max selbst eroeffnet, am 21.09.2026 bestaetigt. Margin rund
  386,05 USDC, P&L zum Zeitpunkt der Pruefung -107,17 USD. **Keine Spur
  verwaltet sie** - xperp fuehrt vier andere Kontrakte (LINK, ZEC, ETC, XAG) und
  fasst diese nicht an.

Folge fuer die Tore der Spuren: die gebundene Margin sitzt im **USDC**-Topf. Die
Oberflaeche meldet `isoEq 279,83` (laufende Margin) und `availEq 255,01` (frei) -
eine Spur mit Guthaben-Tor sieht also nur die freien 255,01.

Merksatz: **Margin-Waehrung einer Position pruefen, nicht die Waehrung im Kopf
des Kontos.** Die XPERP-Kontrakte dieses Kontos sind in USDC besichert; es gibt
dort gar kein USDT. `xperp/okxf.guthaben_usdt()` lieferte deshalb 0,0, bis die
Funktion am 21.09.2026 auf USDC als Rueckfall umgestellt wurde.
## Nautilus-Arme: Stand und Befund (21.09.2026)

Drei Papier-Arme haengen am NautilusTrader-Baum (`Agenten/Handel/nautilus*`). Sie
nehmen die **Kaeufe der kopier-Spur** (Solana, Pump.fun) als Signal und buchen
darauf einen **Proxy** auf einen BTC-Instrument: nautilus -> `BTC-USDT-SWAP`
(OKX, Demo-Node), nautilus_kraken -> `BTC/EUR` (Kraken Spot, Gebuehr 0 ueber das
Pro-Abo), nautilus_kraken_futures -> `PF_XBTUSD` (Kraken Futures, 0,05 %).
Ausstiegsgeometrie in allen drei: Stop -19,8 %, Trailing ab **+30 %** mit 25 %
Abstand, **Frist 168 h**; Quelle der Zahlen ist `trailing_stop_strategie.ausstiegsgrund`
(reine Funktion, eine Stelle fuer die Entscheidung).

**Stand 21.09.2026, 10:50** (jeder Arm 4 offene Positionen, 200 Einheiten Einsatz):

| Arm | offen G/V | Stop-Abstand | Peak seit Einstieg | erste Frist |
|---|---|---|---|---|
| nautilus (BTC-USDT-SWAP) | +14,64 USD (+7,32 %) | +33 % | +8,5 % | 15 h |
| nautilus_kraken (BTC/EUR) | +5,58 EUR (+2,79 %) | +28 % | +3,3 % | 132 h |
| nautilus_kraken_futures (PF_XBTUSD) | +5,83 USD (+2,91 %) | +28 % | +3,2 % | 131 h |

**Befund 1: kein einziger Ausstieg.** In 4 bis 6 Tagen Laufzeit hat kein Arm eine
Runde geschlossen (nur `zyklus`-Zeilen im Journal, je 4 `eroeffnen`). Damit ist
bisher **keine Aussage ueber die Strategie moeglich** - nur ueber den offenen
Bestand. Die ersten echten Ausstiege stehen morgen frueh an (Frist, ~00:05 UTC).

**Befund 2: das Trailing kann hier nicht greifen.** Es aktiviert bei +30 %; der
hoechste Stand nach sechs Tagen sind +8,5 % - Faktor 3,5 zu weit. Wirklicher
Ausstieg ist damit allein die **Frist** (168 h): die Arme messen "sieben Tage
halten", nicht "Trailing". Wer das Trailing messen will, muss die Aktivierung auf
eine Spanne setzen, die BTC in einer Woche erreichen kann, und den Abstand der
BTC-Volatilitaet anpassen (25 % Abstand ist fuer einen Token richtig, fuer BTC
sehr weit).

**Befund 3: die vier Positionen sind EINE Wette.** Alle Einstiege liegen Minuten
auseinander (15.09. 00:05-00:36), alle auf demselben Instrument - der Arm
diversifiziert nicht, er vervierfacht. Und der Proxy misst den **BTC-Weg** nach
einem Solana-Signal, nicht den Weg des Tokens: die kopier-Spur selbst bleibt die
einzige Quelle fuer die Token-Frage.

**Befund 4: die Fehlschlaege waren Speicherdruck, kein Logikfehler.** 11 von ~170
Zyklen je Arm scheiterten heute zwischen 08:41 und 10:16: `Rueckgabe 1` (die Spur
sagt selbst "keine Quote angekommen und Kopier-Spur tot"), zweimal ein nativer
Absturz (`3221226505` = STATUS_STACK_BUFFER_OVERRUN) und einmal der 300-s-Timeout
der Futures. Genau in diesem Fenster war das Windows-Commit zu 99 % belegt (siehe
MoonDev-Leak). Seit dem Aufraeumen um 10:25 laufen alle Zyklen wieder "ok" - der
Befund ist damit erklart und nicht offen.
## Kosten-Wendepunkt je Spur (21.09.2026)

Nicht jede Spur traegt dieselbe Gebuehr. Die Rechnung steht als Werkzeug
`Agenten/Handel/kosten_wendepunkt.py` (rein lesend) und ist eine Zeile:

    EV je Runde = p*(C - f) - (1-p)*(R + f)
    => f_max = p*C - (1-p)*R

R = mittlerer Risikoabstand (Einstieg -> Stop) in Prozent, C = mittlerer
Chancenabstand (Einstieg -> Ziel), p = gemessene Trefferquote, f = Gebuehr JE
RUNDE (Kauf + Verkauf). **f_max ist die Gebuehr, ab der die Spur bei der
eigenen gemessenen Trefferquote nur noch die Nullinie trifft.**

Stand 21.09.2026 (nur Buecher mit mindestens 4 Runden):

| Spur | Runden | R | C | Treffer | f_max je Runde |
|---|---|---|---|---|---|
| orbk | 8 | 0,48 % | 0,62 % | 50 % | **+0,07 %** |
| orbk (mittel) | 6 | 0,50 % | 0,55 % | 50 % | +0,03 % |
| omniquant | 0 | - | - | - | **keine Messung** |
| moondev_topmovers | 7 | 8,00 % | 12,00 % | 71 % | +6,29 % |
| swap | 7 | 1,33 % | 2,65 % | 71 % | +1,52 % |
| xperp | 30 | 3,16 % | 6,32 % | 67 % | +3,16 % |
| scanner | 150 | 6,42 % | 12,83 % | 80 % | +8,98 % |

Zwei Aussagen, die daraus folgen:

- **orbk haengt an der Gebuehrfreiheit.** Seine Runden sind knapp 0,5 % breit;
  f_max liegt bei +0,07 %. Ohne das Kraken-Pro-Abo kostet eine Runde 0,4 %
  (Taker 0,2 % je Seite) - das ist fuenfmal so viel wie der ganze Vorteil.
  Der Merksatz "Faellt das Abo weg, 0,004 zuruecknehmen" ist damit beziffert:
  **bevor orbk-Runden gezaehlt werden, muss die Gebuehr im Wachen stehen** -
  sonst zaehlt die Spur zu freundlich (dieselbe Regel wie am 14.09.2026).
- **omniquant hat gar keine Messung** (Korrektur vom selben Tag). Eine erste
  Fassung dieses Abschnitts nannte 8 Runden mit 25 % Treffern und f_max -1,70 %.
  Falsch: **alle acht Ausstiege tragen `herzschlag` als Grund** - es waren
  Zwangsschluesse der Ausfaelle vom 16./17.09.2026, keine Handelsentscheidungen
  (7 Einstiege, alle zwangsweise geschlossen). Das Werkzeug zaehlt sie seit der
  Korrektur nicht mehr mit (`stoerungen.ist_stoerung`, dieselbe Fassung wie
  `auswertung_alle.py`); omniquant steht damit auf "keine messbare Runde".
  Lehre: **die Störungs-Trennung gehoert in JEDES Werkzeug, das Runden zaehlt** -
  ein Zwangsschluss sitzt meist im Verlust und macht die Trefferquote
  kuenstlich schlecht.

Methodische Grenze: f_max benutzt die eigenen Runden der Spur, also auch deren
Stichprobengroesse. Bei weniger als 8 Runden ist die Zahl ein Befund, keine
Messung (dieselbe Schwelle wie in `auswertung_alle.py`).

## Kraken: nur noch omnitrade (30.09.2026, Auftrag Max)

Max hat am 30.09.2026 angeordnet: *"nur noch omnitrade auf kraken handel
erlaubt"*. Umgesetzt wurde das fuer die Spuren mit vorhandenem Kraken-Orderweg:

| Spur | Kraken vorher | jetzt |
|---|---|---|
| `kraken` | live (Spot EUR, Beleg ueber die Hand) | `handel_erlaubt=false`, `freigabe.erfuellt=false` |
| `moondev_marktlage` | live (`live_kraken.py`) | `handel_erlaubt=false`, `freigabe.erfuellt=false` |
| `mosaic` | live (Kraken zuerst, OKX als zweite Boerse) | `boersen: ["okx"]` - Kraken entfernt, OKX bleibt |
| `nautilus_kraken`, `nautilus_kraken_futures` | waren schon aus | aus der Auto-Freigabe entfernt |

`dauerlauf.AUTO_FREIGABE` fuehrt die vier nicht mehr.

**Erledigt (Entscheidung Max 30.09.2026, Weg B):** `omnitrade` selbst bekommt
keinen Rust-Kraken-Adapter (sein Exchange-Modul kennt weiterhin nur `binance`
und `okx`, `omnitrade-cli/src/commands/live.rs` weist jedes andere
`--exchange` ab - das bleibt so, kein zweiter Kraken-Schluessel neben dem
Haus-Pool). Stattdessen spiegelt die Haus-Spur `Agenten/Handel/omnitrade`
(`omnitrade_bridge.py`, `omnitrade_lauf.py`, `wachen.json`) die POSITION der
Rust-Testnet-Laeufe (net_quantity aus `Werkstatt/omnitrade/status/*.json`,
zwei Zeugen: Statusdatei + lebende PID) und fuehrt im Live-Zweig ueber den
bewaehrten Haus-Kraken-Weg (`kraken_quote=USDC`, `boerse=kraken`). Der
Rust-Lauf bleibt der Entscheider (Strategie im `.omni`-Skript), die Spur nur
der Ausfuehrer. Stand 08.10.2026 (T-256): `handel_erlaubt=false`,
`freigabe.erfuellt=false` - Papierbetrieb laeuft (mehrere Testnet-Laeufe
liefern frische Statusdateien), Live bleibt gesperrt bis Bedingung 1 (Runden,
netto positiv, Ruecklauf) belegt ist UND das Kraken-USDC-Guthaben ueber 60
liegt (T-115, zuletzt ~25 USDC).

**Werkzeuge, die weiter auf Kraken ordern koennen** (bewusst nicht gesperrt,
sie sind Handwerkzeug und kein Automat): `kraken/spot_stops.py`,
`kraken/waisen_stops.py`, `kraken/margin_stops.py`, `mosaic/stops_nachziehen.py`
sowie das MCP-Werkzeug `kraken_order_mit_beleg` (verlangt einen Beleg, den nur
eine Spur ausstellt).

## Moon-Dev-Repo: Bauform und Einbindung (aus den READMEs, 13.10.2026)

**Anlass:** Die GUI `moongui.py` zeigt alle README-Dateien des Repos im
README-Tab (`_find_readmes()`, os.walk mit Pruning von `.venv`, `.git`,
`moongui_logs`, `node_modules`, `__pycache__`, `temp_data`, `responses`; alles,
was mit `README` beginnt). Ihre Inhalte sind die Bauform des Fremd-Repos — sie
gehoeren ins Handelswissen, weil sie beschreiben, wie die Agenten, Strategien
und Modelle strukturiert sind.

**Neun README-Dateien** gefunden:

| Datei | Inhalt |
|---|---|
| `README.md` | Uebersicht der 47 Agenten, Vision, Disclaimers, Quick Start |
| `README_FIXES.md` | GUI-Fixes: BirdEye API Key, `startup.py`, `validate_env.py`, `unicode_fix.py` |
| `docs/README.md` | Alpha-Status, Verweis auf Video-Doku |
| `src/agents/README.md` | Build-Liste der Agenten (copy trading, sentiment, rbi, sniper, liquidation, OI, funding, coingecko, listing arb) |
| `src/models/README.md` | Model Factory: API Keys, Modelle (OpenAI, Claude, Gemini, Groq, DeepSeek, lokales Ollama) |
| `src/strategies/README.md` | Strategie-Struktur: `BaseStrategy`, `generate_signals()`, Signal-Format |
| `src/strategies/custom/README.md` | Custom Strategien: `private_`/`secret_`/`dev_` Prefixe fuer gitignore |
| `src/data/rbi/memory/sessions/README.md` | Session Memory Storage (Claude-Flow/SPARC) |
| `src/data/rbi/memory/agents/README.md` | Agent Memory Storage (Claude-Flow/SPARC) |

### Agenten-Uebersicht (47 Agenten)

Das Repo stellt 47 Agenten bereit, gruppiert nach Zweck:

- **Handels-Agenten:** `trading_agent`, `strategy_agent`, `risk_agent`,
  `copy_agent`, `whale_agent`, `sentiment_agent`, `listingarb_agent`,
  `funding_agent`, `liquidation_agent`, `chartanalysis_agent`,
  `fundingarb_agent`, `rbi_agent`, `new_or_top_agent`
- **Solana-Agenten:** `sniper_agent`, `tx_agent`, `solana_agent`,
  `million_agent`
- **Content-Agenten:** `tweet_agent`, `video_agent`, `clips_agent`,
  `tiktok_agent`, `compliance_agent`, `chat_agent`
- **Sonstige:** `focus_agent`, `phone_agent`, `research_agent`

**Haus-Einbindung:** Vier davon laufen als Papier-Spuren (`moondev_funding`,
`moondev_listingarb`, `moondev_topmovers`, `moondev_marktlage`), siehe
[[Moon-Dev-Agenten]]. Die anderen sind nach Blockern gruppiert
(MoonDev-API-Schluessel, LLM-Schluessel, Solana-RPC/Wallet, kein
Handelsbezug).

### Strategie-Struktur

Alle Strategien erben von `BaseStrategy` und implementieren
`generate_signals()` mit dem Format:

```python
{
    'token': str,          # Token-Adresse
    'signal': float,       # Signalstaerke (0-1)
    'direction': str,      # 'BUY', 'SELL', oder 'NEUTRAL'
    'metadata': dict       # optionale strategie-spezifische Daten
}
```

Signale werden vom LLM bewertet, bevor sie ausgefuehrt werden. Die
Positionsgroesse haengt von der Signalstaerke ab.

**Private Strategien:** Dateinamen mit `private_`, `secret_` oder `dev_`
Prefix werden von git ignoriert (`.gitignore`).

### Model Factory

`src/models/model_factory.py` stellt eine einheitliche Schnittstelle fuer
mehrere Provider bereit:

- **Cloud:** OpenAI (`gpt-5`, `gpt-4o`, `o1`, `o3-mini`), Anthropic
  (`claude-3-opus/sonnet/haiku`), Gemini (`gemini-2.0-flash`,
  `gemini-1.5-flash/pro`), Groq (`mixtral-8x7b`, `llama-3.3-70b`,
  `gemma2-9b`), DeepSeek (`deepseek-chat`, `deepseek-reasoner`,
  `deepseek-r1`)
- **Lokal (Ollama):** `deepseek-r1` (7B, Reasoning), `gemma:2b` (schnell),
  `llama3.2` (ausgewogen) — kostenlos, privat, keine API-Kosten

**Haus-Standard:** Lokales Ollama (`qwen35-8k:latest`), siehe
[[Moon-Dev-Agenten]].

### Disclaimers

Das Repo ist ein **experimentelles Forschungsprojekt**, kein Handelssystem:

- Keine Garantie fuer Profitabilitaet
- Keine Plug-and-play-Loesungen
- Keine Handelsstrategien im Repo
- Erfolg haengt von der eigenen Strategie, dem Risikomanagement und der
  Validierung ab
- Kein KI-Agent kann profitables Handeln garantieren
- Vergangene Ergebnisse sind keine Garantie fuer zukuenftige

### GUI-Betrieb

Die GUI (`moongui.py`) wird ueber `startup.py` gestartet, der Pre-flight-Checks
macht:

1. Python-Version (3.10+)
2. Umgebungsvariablen (`validate_env.py`)
3. Ollama-Verbindung
4. Ordner-Struktur (`src/data`, `src/strategies`, `logs`, `temp_data`)
5. Module (`dotenv`, `termcolor`, `requests`, `pandas`, `anthropic`, `openai`,
   `solders`)

**Fixes (README_FIXES.md):** `BIRDEYE_API_KEY` fuer `copybot_agent`,
`unicode_fix.py` fuer Windows-Emoji-Crash, `ollama_health.py` fuer
Ollama-Recovery, `validate_env.py` fuer Status-Anzeige.
