---
id: 20260902-handelsregeln
title: 'Handelsregeln'
tags: [handel, sicherheit]
created: 2026-09-02
updated: 2026-09-02
related: [20260830-schutzregeln, 20260830-handelsbots, 20260831-marktscanner, 20260901-xperp-handel]
summary: 'Was ein Agent im Handel selbst auslösen darf: die beiden bewachten Spuren, die Prüfpflicht und die fünf Bedingungen für den unbeaufsichtigten Lauf.'
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
Nachprüfbares bezeichnen und keine Haltung. Es sind zwei Dateien, und sie sind
die **einzige** Wahrheit über die Grenzen:

| Spur | Grenzen in | Was dort handelt |
|---|---|---|
| **1 — Spot** | `../Agenten/Handel/scanner/wachen.json` | Marktscanner: Spot, nur Long, kein Hebel |
| **2 — Hebel** | `../Agenten/Handel/xperp/wachen.json` | XPERP-Bot: Long und Short, Hebel bis 5 |

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
   ohne Rückfrage je Order. Das Fenster ist noch nicht gebaut (T-028); bis
   dahin ist der bewusste Aufruf von Hand die einzige Form des Scharfschaltens.

   **Ein Zeitplan legt den Schalter nicht um.** Die eine Ausnahme, von Max am
   01.09.2026 so gewollt, hat zwei Bedingungen, die **beide** erfüllt sein
   müssen: Ein Agent überwacht den Lauf, **und** Max hat das Scharfschalten für
   genau diesen Lauf ausdrücklich angeordnet. „Ein Agent überwacht das" ist
   dabei keine Behauptung, sondern der Herzschlag aus Bedingung 3 weiter unten:
   Schlägt er nicht, überwacht niemand, und die Ausnahme greift nicht.

## Kraken ist keine dritte Spur — dort wird nur gelesen

Angelegt 02.09.2026, weil die Lücke bei der Durchsicht des Regelwerks auffiel.
Die beiden Spuren oben sind abschließend: **auf Kraken löst kein Agent eine
Order aus, weder automatisch noch auf Anweisung im Chat.**

Die Begründung steht in diesem Abschnitt selbst. Drei Eigenschaften tragen die
Handelserlaubnis — Grenzen in einer Datei, nicht abschaltbarer Stop mit
Kill-Switch, Scharfschalten von Hand. Für Kraken gibt es keine davon: keine
`wachen.json`, kein Handelsjournal, keinen Herzschlag, keine Freigabestufen.
Nach dem eigenen Maßstab oben — *fehlt eine, gilt sie nicht* — ist damit nichts
erlaubt.

Das ist keine papierne Lücke. Der MCP-Server `kraken` ist in jeder Sitzung
geladen, und sein Schlüssel trägt laut `Agenten/MCP-Server/kraken/README.md`
das Recht *Create & Modify Orders*. Die beiden schreibenden Werkzeuge würden
also wirklich ausführen.

| Werkzeug | erlaubt |
|---|---|
| `kraken_guthaben`, `kraken_kurs`, `kraken_candles`, `kraken_paare_suchen`, `kraken_ledger`, `kraken_trades`, `kraken_offene_orders`, `kraken_geschlossene_orders`, `kraken_status` | ja — lesen, auswerten, vorbereiten |
| `kraken_order_aufgeben`, `kraken_order_stornieren` | **nein** — auch nicht mit Bestätigung im Chat |

Der Skill `geld` bleibt unberührt: er liest Kraken, stellt fällige Zahlungen
und verfügbare Mittel nebeneinander und hält vor dem Auslösen an. Neu ist nur,
dass das nicht mehr allein in einem Skill steht — eine Skill-Regel gilt nicht,
wenn kein Skill läuft.

**Der Weg zu einer dritten Spur ist offen**, er führt nur nicht am Verfahren
vorbei: erst `../Agenten/Handel/kraken/wachen.json` mit denselben Feldern wie
die beiden anderen, dann ein Skript, das sie liest und ein Journal schreibt,
dann die fünf Bedingungen aus *Damit der Automat unbeaufsichtigt laufen darf*.
Bis dahin wäre „Kraken-Handel" nicht der bewachte Automat, sondern genau die
Wette mit Skriptunterstützung, die dieser Abschnitt ausschließt.

**Kein Auszahlungsrecht, auch hier nicht.** Der Schlüssel hat *Withdraw Funds*
bewusst nicht, und es gibt kein Auszahlungswerkzeug. Das bleibt so.

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
- **Kraken bleibt lesend.** Keine Order, keine Stornierung — siehe *Kraken ist
  keine dritte Spur* oben.
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
`journal_zweitziel` (noch `null` → Live bleibt gesperrt). Bedingung 5 läuft
wöchentlich getrennt über `Routinen/handel-wachen.ps1` (`handeln.py --wachen`),
damit ein einzelner schlechter Tag die Spur nicht sofort abschaltet. Der Lauf
schließt `handel_erlaubt` nur, er öffnet es nie.

**Spur 2 (XPERP):** `bot.py` führt nichts aus, kein Journal, kein Zustand —
Bedingung 2/3/5 haben nichts zu greifen, bis ein Live-Pfad gebaut ist.
`bot.py wachen` zeigt die hinterlegten Grenzen und den Freigabe-Haken.
