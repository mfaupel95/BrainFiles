---
id: 20260921-wahrheit-pruefen
title: 'Lektionen — Wahrheit pruefen'
tags: [lektion, methode]
created: 2026-09-21
updated: 2026-09-24
related: ['[[Handel/Lektionen]]', '[[Lektionen/Tests]]']
summary: 'Neun Merksaetze, wie eine Aussage belegt wird, bevor sie rausgeht: zwei Zeugen, Konto statt Buch, Ursache statt Zaehler, Gegenprobe, kein Haenger im Pruefer.'
---

# Wahrheit pruefen

## 1. Zwei Zeugen oder keine Aussage

**Regel.** Bevor „Spur X ist live mit N Positionen" rausgeht: **Buch UND Journal UND
Boerse** ansehen. Fuer Kraken: Balance + Open Orders.

**Warum.** Am 21.09.2026 fuehrte `xperp` vier Positionen (ZEC, XAG, LINK, ETC) — an der
Boerse existierten sie NICHT (`/account/positions` kannte nur die manuelle FIL-Position
und einen XRP-Rest). Zweiter Zeuge: von 14 Live-Zeilen im Journal waren **alle 14
`funding`** — kein Live-Kauf, kein Live-Verkauf. Die vier Positionen stammten aus dem
Papierlauf bei Buchmodus live.

## 2. Fehlender Hash ist keine Messung — er ist eine falsche Aussage

**Belegter Fall.** `fundus-suche.ps1` benutzte `Get-FileHash`, das es in PowerShell 5.1
nicht gibt. Folge war keine Fehlermeldung, sondern: leerer Hash → alle Skills in EINER
Gruppe → „0 Treffer von 0 eindeutigen Skills" bei 182 Skills.
Dasselbe Muster hatte `systempruefung.ps1` Block 10 (Regelwerk war seit Einfuehrung tot).

**Regel.** Version-gebundene PowerShell-Befehle durch
`System.Security.Cryptography`-Aufrufe ersetzen, die in 5.1 und 7.x gleich laufen, und
nach dem Fix **beide** Wirte gegeneinander messen.

## 3. Zaehler sind keine Ursache

**Regel.** Bei „laeuft nicht rund" die **Zeilen mit Grund** lesen, nicht die Summen.

**Belegte Faelle.** (a) Der MoonDev-Treiber sah wie ein Crash-Loop aus — vier Abstuerze
mit Code `4294967295` im selben Moment waren eigene Abschuesse; die echte Ursache war
CoinGecko HTTP 429 (Rate Limit der Gratis-Grenze) und Kraken public. (b) Der Telegram-Bus
war vier Tage aus; es gab kein Systemereignis, der Prozess wurde von aussen beendet und
der Task hat **keinen** Wiederholungs-Trigger. Nicht-0 Exitcodes bei Dauerprozessen sind
normal (267014/1073807364 = von aussen beendet, 2147946720 = laeuft schon).

## 4. Gegenprobe statt Vermutung

**Regel.** Jede Annahme mit einem zweiten Weg pruefen, der auch scheitern koennte.

- Zeitreihenlaenge: OKX `/market/candles` gibt oeffentlich nur **1440 Stundenkerzen**,
  egal was man anfordert — `kerzen_holen()` bricht jetzt laut ab statt still ein kuerzeres
  Fenster zu liefern (96 Kerzen wurden einmal fuer „8 Wochen" gehalten).
- Suchfenster aus lokalen Kerzen, Prueffenster live — sonst prueft man dieselben Daten,
  aus denen optimiert wurde.
- Read-only-Check vor jeder Freigabe: `npm`-Hash, Signatur, `git status`.

## 5. „Repariert" heisst: der echte Lauf ist gezeigt

**Regel.** Ein Fix ist erst fertig, wenn der bestandene LAUF zitiert wird (Kommando +
Ausgabe), nicht die Aenderung am Code. Bei Textdateien zusaetzlich `git diff --numstat`;
bei Massenaenderungen pruefen, ob die Dateien in einem EIGENEN Repo liegen
(`nautilus/`) oder per Whitelist ausgeklammert sind.

## 6. Ein stiller `except` darf keinen Sachverhalt behaupten

**Regel.** Wer eine Ausnahme verschluckt und daraus einen Befund formt, behauptet etwas
ueber die Welt, das er gar nicht geprueft hat. Im `except`-Zweig gilt: **fail-safe
handeln, laut melden** — nach `stderr` schreiben und den Text der Meldung vom Befund
trennen („Zeitfenster nicht lesbar" ist etwas anderes als „Zeitfenster ist zu").

**Belegter Fall (22.09.2026, scanner).** `zeitfenster_offen()` las das Freigabefenster per
blankem `import freigabefenster`, der im Spurlauf nicht aufloesbar war
(`ModuleNotFoundError`), und gab im `except` `False` zurueck. Die Sperre meldete daraufhin
`Freigabefenster nicht offen - keine Sitzung am Bildschirm und kein Zeitfenster`, obwohl
das Fenster offen war. Die Folge war doppelt schlecht: die Spur handelte Papier, **und**
der Dauerlauf glaubte der Meldung — `nur_fenster_fehlt()` sah genau einen Grund mit dem
Wort „Freigabefenster" und oeffnete im 30-Minuten-Takt neue Fenster. Der Fehler verdeckte
sich selbst, bis jemand die Meldung im Chat hinterfragte.

**Merksatz.** Ein Sperrgrund ist eine Aussage. Wenn die Ursache des Sperrens ein Fehler
beim *Pruefen* sein kann, muss die Meldung das sagen. Sonst ist die Wache kaputt, nicht
die Lage.

## 7. Gemeldet wird, was WIRKT — nicht, was angefordert wurde

**Regel.** Eine Zustandszeile beschreibt das ERGEBNIS. Wo eine Absicht und eine Wirkung
auseinanderfallen koennen, muss die Meldung die Wirkung nennen — sonst liest der Nutzer
„aus" statt „ruhig".

**Zwei belegte Faelle am 22.09.2026, beide von Max hinterfragt.**

(a) **Tagesbericht:** `N Spuren still: kraken, omniquant, …` — gelesen als „die sind
abgeschaltet". „Still" war aber `tagesbericht.rang() == 3`: kein Fehler, keine neue Runde,
keine neue oder weggefallene Position **seit dem letzten Bericht**. Die betroffenen Spuren
liefen in Papier weiter. Die Sammelzeile nennt die Bedeutung jetzt selbst.

(b) **Dauerlauf-Log:** `kraken (live) ok`, waehrend kraken Papier handelte. Der Modus kam
allein aus dem Freigabefenster (`modus = "--live" if f.offen() …`); ob die Spur live geht,
entscheidet ihr eigener Riegel (`wachen.json handel_erlaubt`). Die Spur schrieb selbst
`--live angefordert, aber gesperrt: wachen.json handel_erlaubt=false`. Fix:
`_meldungsmodus(modus, ordner)` meldet `(papier)`, wenn `handel_erlaubt=false` ist — der
AUFRUF bleibt der angeforderte Modus, sonst aendert sich das Verhalten der Spur still
(die Buchbereinigung laeuft nur im Live-Zweig).

**Prueffrage fuer jede neue Zeile.** Ist das ein Zustand (Modus, Position, Sperre) oder eine
Aenderung (neu, weg, anders)? Wer beides in ein Wort legt, erzeugt genau diese Rueckfrage.

**Zusatzregel fuer die Wirkung:** Nicht aus der Konfiguration schliessen, sondern die Spur
selbst fragen. `handeln.py --vorschau` mit `MAXHIRN_ROUTINE=1` (so ruft der Dauerlauf sie)
ist die einzige Wahrheit — `<spur> (live) ok` im Log ist der Modus des DAUERLAUFS, kein
Orderbeleg.

## 8. Ein Pruefer, der haengen kann, liefert still GAR KEINEN Befund

**Regel.** Jeder Aufruf an ein fremdes System (Docker, Netz, ein Dienst) braucht eine
Zeitgrenze. Ein Haenger ist nicht „keine Meldung" — er ist der **Verlust aller Meldungen
danach**, denn der Bericht wird am Ende geschrieben.

**Belegter Fall (19.–22.09.2026).** `Docker Desktop` war aus (WSL-Distro `docker-desktop`
gestoppt), der Docker-Client wartete unbegrenzt auf die Pipe. `systempruefung.ps1` Block 14
war deshalb **dreimal** die letzte Zeile im Protokoll, der Lauf wurde von aussen gekillt
(Code `267014`), und der Bericht `systempruefung-letzter-lauf.md` blieb auf dem 19.09.
stehen. Sichtbar war das an nichts: Der Aufgabenzustand sagte „Ready", die Tageslogs
existierten, nur der Bericht war alt.

**Behebung.** `DockerMitFrist` in Block 14 (Aufruf ueber
`System.Diagnostics.Process` mit `WaitForExit(ms)` und asynchronem Lesen, damit die
Ausgabe nicht den Puffer verstopft). Ohne Antwort in 20/25 s kommt `$null` zurueck und
der Block meldet ausdruecklich „Docker-Engine antwortet nicht". Gemessen: 8,2 s statt
unbegrenzt, Lauf danach 97–160 s mit Ende-Zeile.

**Prueffrage fuer jede Wache.** Kann der Aufruf, mit dem sie prueft, haengen? Wenn ja:
Zeitgrenze setzen **und** den Zeitueberschreitungs-Fall als eigenen Befund melden — nicht
als „alles in Ordnung".

**Nebenbefund, der zum Merksatz gehoert.** Derselbe Ausfall hatte eine zweite unsichtbare
Folge: der Nautilus-Quoten-Container war weg (samt Image), weil Docker beim toten Daemon
nichts hochzieht. Ein Dienst, der „nur noch im Log" existiert, ist kein laufender Dienst —
der Container wurde am 22.09. neu gebaut und liefert wieder Quotes.

## 9. Eine erzeugte Fehlermeldung ist kein Befund

**Regel.** Bevor eine Fehlermeldung (Code, Text) zur Diagnose wird, die Zeile in der
QUELLE suchen: Journal, Log, Zustandsdatei. Steht sie dort nicht, ist sie ein Modelltext
- ein Messwert sieht anders aus.

**Belegter Fall (24.09.2026).** Die Meldung "nautilus-kraken Spuren haben Fehler OKX
51001" war erzeugt. Die Suche nach `51001` im Handelsbaum findet Treffer NUR in
`xperp/` (abgelaufener XPERP-Kontrakt `CL-USD_UM_XPERP-310509`) und in der Skill-Doku;
in `nautilus/`, `nautilus_kraken/`, `nautilus_rc5/` und den drei dauerlauf-Protokollen:
kein Treffer. 51001 heisst "Instrument ID does not exist" und gehoert zu OKX-Kontrakten,
die die Kraken-Arme nie anfassen - sie importieren kein OKX-Modul, geteilt ist nur das
venv.

**Was der gemessene Fehler war.** `RuntimeError(Authentication error: Failed to get
WebSocket token: API error: EGeneral:Permission denied)` im Exec-Client des
Nautilus-Kraken-Adapters (24.09. 18:49 UTC, `nautilus_kraken/logs/kraken-orders-
20260924T184919894096Z.jsonl` -> `success: false`). Dem Kraken-Schluessel fehlt die
Berechtigung "Access WebSockets API"; ueber REST arbeitet derselbe Schluessel
(Kontostand und 14 offene Orders lesbar).

**Merksatz.** Ein Fehlercode ohne Fundstelle ist keine Spur. Die erfundene Diagnose hat
einen echten, aber ganz anderen Fehler verdeckt - erst die falsche Faehrte erledigen,
dann den gemessenen Fehler nennen.

## 10. Eine Prozessabfrage traegt ihren Suchtext selbst (29.09.2026)

**Regel.** Wer per Kommandozeilen-Filter nach einem Prozess sucht, muss den Suchtext
ZUSAMMENSETZEN und den eigenen Prozess ausschliessen - sonst findet die Abfrage sich selbst.

**Belegter Fall.** `update_laeuft()` in `Agenten/Hermes/scripts/gateway-identitaet-wache.py`
fragte `Where-Object { $_.CommandLine -match 'hermes_cli.main update' }` ab. Die
PowerShell-Kommandozeile der Abfrage enthaelt diesen Text woertlich - also war das Ergebnis
**immer** "es laeuft ein Update", und die Wache griff im Blindfall nie ein. Sichtbar wurde es
erst an einer zweiten Stelle: derselbe Ausdruck in einer Handmessung zeigte genau EINEN
Treffer, naemlich die Messung selbst.

**Richtig.** Muster aus Teilen bauen (`'hermes_cli.main' + ' ' + 'update'`), `$_.ProcessId -ne $PID`
setzen, und das Ergebnis einer Prozessabfrage IMMER gegen eine zweite Quelle halten
(PID-Datei, Port, Log). Verwandt: ein Kommandozeilen-Filter fuer einen DAUERPROZESS darf
keinen zu breiten Namensteil nennen - `*moondev*` traf die eigene Shell und beendete sie
(Skill `dauerprozess-bewachen`).

**Merksatz.** Ein Messgeraet, das sich selbst mitmisst, meldet konstant. Vor jeder
"es laeuft/ist tot"-Aussage die Messung gegen die eigene PID absichern.

## 11. Eine Wache prueft die Sache, nicht eine Startform (29.09.2026)

Der Gateway-Waechter erkannte den Dienst an einer Zeichenfolge in der Kommandozeile
(`hermes_cli\.main gateway`). Das traf nur die Launcher-Form. Der Update-Weg startet den
Gateway ueber `runpy.run_module('hermes_cli.main', …)`, wo zwischen Modul und Unterbefehl noch
`, run_name=` steht - **0 Treffer bei laufendem Gateway**. Der Waechter startete ihn 148-mal an
einem Tag neu und schrieb dabei jedes Mal "kein Gateway-Prozess".

**Warum das so lange unentdeckt blieb.** Die Zeile las sich richtig ("kein Prozess"), die Wache
tat ihre Arbeit ("Neustart ausgeloest"), und danach war der Dienst tatsaechlich kurz weg - es
gab kein Widerspruchssignal. Nur die ZAHL verraet es: 148 Neustarts an einem Tag.

**Richtig.** Den Dienst nach der **Identitaet** fragen, die er selbst schreibt
(`gateway_state.json`: pid + Zustand), und die Prozessliste nur als Rueckfall benutzen - breit
genug fuer **alle** bekannten Startformen. Ein Suchmuster, das an einem Starter haengt, ist
eine Adresse, kein Befund.

**Prueffrage fuer jede Wache.** Erkennt sie den Dienst - oder die Startzeile, die er einmal
benutzt hat? Und was tut sie im Zweifel: meldet sie Gesundheit oder startet sie neu? Wer im
Zweifel neu startet, zerlegt den Dienst im Takt seiner eigenen Laufzeit.
