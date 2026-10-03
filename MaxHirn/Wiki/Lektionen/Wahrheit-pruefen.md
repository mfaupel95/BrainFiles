---
id: 20260921-wahrheit-pruefen
title: 'Lektionen — Wahrheit pruefen'
tags: [lektion, methode]
created: 2026-09-21
updated: 2026-10-01
related: ['[[Handel/Lektionen]]', '[[Lektionen/Tests]]']
summary: 'Siebzehn Merksaetze, wie eine Aussage belegt wird, bevor sie rausgeht: zwei Zeugen, Konto statt Buch, Ursache statt Zaehler, Gegenprobe, kein Haenger im Pruefer, deklariert gegen real, Einstellung gegen Leser.'
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

## 12. Deklariert ist nicht real (29.09.2026)

**Regel.** Jede Referenz in einer Config — Pfad, Adresse, Modellname — ist eine **Behauptung**.
Vor dem Bericht wird sie EINMAL gegen die Wirklichkeit gehalten: laufender Dienst, Store,
Dateisystem. Nicht gegen die Erinnerung und nicht gegen die Nachbardatei.

**Warum.** Am 29.09.2026 trugen Hauptconfig und 17 Profile in der `models:`-Liste des lokalen
Providers vier Namen, die im Ollama-Store nicht lagen; `providers.bonsai` zeigte auf Port 8080,
wo die FreqTrade-Oberflaeche antwortete (der Startbaustein hat 8081 als Vorgabe). Der
Vorgabewert `model:` war am selben Abend schon gerichtet — **dieselbe Behauptung stand an zwei
Stellen, eine blieb falsch.** Kein Werkzeug meldet das: der Name wird erst gelesen, wenn der
lokale Rueckfall gebraucht wird, und dann ist er der letzte Ausweg.

**Prueffrage.** Steht der Name in der Datei — oder auch in der Sache, die die Datei
beschreibt? Die Wahrheit liefert `/api/tags`, der offene Port, `Test-Path`, nicht die Config.

**Zweiter Teil: der Pruefer braucht eine Gegenprobe.** Der erste Lauf der Config-Gegenprobe
meldete `auto/coding:free` als „nicht im Store" — ein **Fehlalarm**: ein Block in Spalte 0 erbte
die Einstufung „lokaler Provider" vom vorigen `providers:`-Block. Ein Pruefer ohne Gegenprobe
erzeugt Reparaturen an Stellen, die in Ordnung sind. Gegenprobe heisst hier: einen Fall bauen,
der rot werden MUSS, und einen, der gruen bleiben muss.

**Werkzeug.** `Agenten/Hermes/scripts/config-gegenprobe.py` (rein lesend) und die Wache
`config-gegenprobe-wache.py` (Cron montags 07:40, leere Ausgabe = nichts senden). Ohne Wache
waere die Gegenprobe ein Nachweis, den niemand von selbst aufruft. Siehe
[[Werkzeuge/config-gegenprobe]].

## 13. Ein laufender Prozess ist kein antwortender Dienst — und Arbeit ist kein Haenger (30.09.2026)

**Regel.** Ein Dienst gilt als gesund, wenn er **antwortet** (echte Anfrage, echte Antwort) —
nicht wenn ein Prozess laeuft und ein Port offen ist. Und bevor ein Dienst neu gestartet wird,
wird gemessen, ob er gerade **arbeitet**: zwei Abstandsmessungen der CPU-Zeit, Kinder
mitgezaehlt. Steigt sie, laeuft ein Bau/Start und ein Neustart macht alles schlimmer.

**Warum.** Am 30.09.2026 lief der Dashboard-Prozess und Port 9119 war offen
(`Get-NetTCPConnection` nannte PID 27864), aber es kam 60 s **keine Antwort** — OmniRoute
(20128) und der Gateway-Webhook (8644) antworteten im selben Moment in Millisekunden. Dieselbe
Instanz stand in 5 Minuten mit **1 s CPU** still: ein echter Haenger, den die Aufgabe
`Hermes_Dashboard` nicht heilt (`RestartCount 999` greift nur bei einem **Absturz**).
Umgekehrt schrieb die von Hand gestartete Instanz
`hermes: finishing an interrupted source update ...` und baute ueber **6 Minuten** Node/TUI/
Web-UI/Desktop-App, bevor Port 9119 aufging — wer das als Haenger deutet und neu startet,
reisst den Bau ab und hinterlaesst ein halb gebautes `dist`.

**Prueffrage.** „Antwortet er?" statt „laeuft er?" — und bei einem Nein: „arbeitet er gerade,
oder steht er still?" (die Zahl steht in der CPU-Zeit, nicht im Gefuehl).

**Werkzeug.** `Agenten/Hermes/scripts/dashboard-wache.py` (Cron `dashboard-wache`,
`bf375a2ac65f`, alle 15 min), Tests `test_dashboard_wache.py` (18, mit Attrappen — kein Netz,
kein Prozesskill). Verwandt: die Gateway-Wache unter
[[Betrieb/Wachen-und-Aufgaben]] (Adresse statt Bedingung, 128 Neustarts an einem Tag).

## 14. Eine Einstellung gilt nur fuer den Weg, der sie liest (01.10.2026)

**Regel.** Eine Konfigurationsangabe ist kein Zustand des Systems, sondern eine Zusage an
**einen** Leser. Vor „X ist gesetzt" also fragen: *welcher Code liest X — und laeuft mein Fall
durch diesen Code?* Wo zwei Wege denselben Anker setzen sollen, muss **jeder** Weg seinen
eigenen Mechanismus haben.

**Warum.** `terminal.cwd` in `Agenten/Hermes/config.yaml` (gesetzt am 30.09.2026, T-233) galt
fuer Gateway, Cron und entfernte Backends — **nicht** fuer die interaktive CLI und TUI: die
uebernehmen das Startverzeichnis der Shell (`os.getcwd()`). Von der Wurzel gestartet, liefen
beide dort, waehrend die Desktop-App in `Agenten\Hermes` startete. Zwei Anker, und jede
Anweisung `cd "$HERMES_HOME/../.."` landete eine Ebene **ueber** der Wurzel. Zeuge war nicht
die Konfiguration, sondern `state.db`: alle TUI-/CLI-Sitzungen trugen `cwd = BrainFiles`.
Der Merksatz stand schon zweimal im Wiki ([[Betrieb/Arbeitsverzeichnis]], Lektion 12) — die
Konfigurationsdatei war nur nie der Beleg.

**Prueffrage.** „Wer liest das?" statt „ist das gesetzt?" — und beim Nachweis die **Spur** des
Lesers nehmen (`state.db`, Journal, Log), nicht die Einstellung selbst.

**Werkzeug.** `Agenten/Werkzeuge/anker-pruefen.ps1` (Exit 0 = die echte Profilfunktion startet
die Sitzung in `Agenten\Hermes`); die Mechanik steht in [[Betrieb/Arbeitsverzeichnis]].

## 15. Eine Randmeldung ist kein Ausfall (01.10.2026)

`OKX-Transportfehler 1/6: <urlopen error [WinError 10054] ...>` liest sich wie ein
Ausfall und ist eine **Warnung**: der Wiederholer versucht es bis zu sechsmal (Pause
1,5 s x Nummer), "1/6" heisst erster Fehlversuch, der naechste gelingt. Bevor daraus
eine Stoerung wird, wird GEZAEHLT und GEMESSEN:

    Transportfehler in dauerlauf.log                      -> 0
    Rand-Logs: dauerlauf-kind.err.log 1x (13:44), handelszentrale-fehler.log 6x (00:15)
    signierter Leseaufruf /api/v5/account/config          -> 0,2 s, perm read_only,trade
    Zyklus 13:40-13:44                                    -> alle Spuren "ok", 0 Timeouts

Drei Zeugen (Hauptlog, Live-Abruf, Zyklus), alle gruen - die Meldung war folgenlos.
Dass OKX UND Kraken im selben Moment betroffen waren, zeigt auf den eigenen Anschluss,
nicht auf die Boerse.

**Regel: eine Meldung, die wie ein Ausfall klingt und nachweislich folgenlos ist, wird
UMGESCHRIEBEN.** Jetzt enden alle vier Wiederholer auf "- wird wiederholt, kein Ausfall"
(`tests/test_transport_wiederholung.py` nagelt Meldung UND Wiederholregel fest: zwei
Fehlversuche dann Erfolg, sechs dann Ausnahme, fachliche Fehler nur einmal). Eine Warnung,
die den Menschen erschreckt, kostet Vertrauen in jede weitere Warnung.

## 16. Was eine Ansicht zeigt, ist eine Behauptung — sie wird gemessen (01.10.2026)

In einem Durchgang durch `Agenten/Handel/handelszentrale.py` fielen fünf Sätze auf, die
das Fenster sagte, ohne sie belegt zu haben. Keiner war ein Rechenfehler; jeder war eine
Beschriftung, die wie ein Messwert aussah:

* **Ein Reiter zeigte einen Bot, während drei liefen.** Die Brücke kannte nur die feste
  Adresse `127.0.0.1:8080`; gemessen am 30.09. antwortete die nicht, die Container auf
  8081/8082/8083 dagegen auf jedem Endpunkt. Die einzige Antwort des Reiters war
  "nicht erreichbar" — über alle drei Bots. Liste jetzt: `freqtrade/bots.json`
  (dieselbe, die `bots.py` zum Starten benutzt), eine Zeile je Bot, ein Grund je toten Bot.
* **"Wert USD" stand über einem EUR-Betrag.** Das Kraken-Buch führt `eur`; die Regel für
  die Einheit liegt in `auswertung_alle.einheit_fuer()` und wird dort im Tagesbericht
  längst benutzt — die Zentrale hatte sie nicht abgerufen, sondern eine Spalte benannt.
  Fusszeile und Zelle nennen jetzt die Waehrung, gruppiert: eine Summe aus EUR und USD
  ist kein Betrag, den jemand ausgeben könnte.
* **Ein Einstieg von 3,14e-06 stand als "0.00000" da.** Die Preisskala endete bei
  "%.5f"; Einstieg, Stop und Ziel derselben Token-Position waren drei Nullen — eine
  Grenze, die keine mehr ist. Unter 1e-4 gilt jetzt die exponentielle Form.
* **"Quelle okx" über einer Contract-Adresse.** `moondev_sniper` führt seine Mints als
  `inst`, `robinhood_radar` notiert auf der Robinhood-Kette (4663). Beides ist kein
  OKX-Paar. Der erste ist über den Onchain-Feed preisierbar (gemessen 3,104e-06 am
  01.10.), die zweite Kette kennt kein Haus-Leser. Ein Kursweg, der nie antwortet, ist
  eine Beschriftung, kein Weg — jetzt heisst er "keine".
* **Jede Logzeile ohne " ok" war rot.** Damit standen Betriebsmeldungen wie
  `01.10. 11:56:06  Auto-Freigabe scanner (720 min)` in Alarmfarbe. Rot gibt es nur noch
  für ein Fehlermerkmal (`log_marke`), neutrale Zeilen bleiben ohne Farbe.

Merksatz: Wer ein Fenster beschriftet, trifft eine Aussage über die Daten. Die Aussage
ist erst gemacht, wenn die Quelle (Datei, Endpunkt, Feld) an derselben Stelle
nachgelesen wird — eine Spaltenüberschrift ist kein Nachweis.

Nachprüfen: `cd Agenten/Handel && python handelszentrale.py --pruefen` (nennt die Bots
samt Port und Grund), `python freqtrade_bridge.py` (Bot-Liste und Übersicht, Exit 0 wenn
einer antwortet), Tests `tests/test_handelszentrale_anzeigefehler.py` und
`tests/test_handelszentrale_struktur.py`.

## 17. Eine Strukturregel gehört in den Prüfer, nicht ins Gefühl (01.10.2026)

Zwei Funde aus demselben Durchgang durch `Agenten/Handel/handelszentrale.py`, beide durch
nichts sichtbar — kein Absturz, keine falsche Zahl, nur tote Stelle:

* **Zwei wortgleiche `spur_zeile`-Funktionen in einer Datei.** Python lässt die LETZTE
  Definition gewinnen, die erste ist tot. Die Tabelle bauden richtig, also fiel nichts
  auf — aber eine Änderung nur an der ersten Fassung hätte gewirkt wie keine, und die
  nächste Sitzung hätte sie erneut versucht.
* **Tabellen ohne Leiste, eine Seite ohne Scrollfläche.** Die Spurtabelle forderte
  `height=len(SPUREN)` an (42 Zeilen), ihr Rahmen wurde mit `fill="x"` gepackt — die Seite
  war damit höher als jedes Fenster und der untere Teil (Chart, Konsole) nicht erreichbar.

Behoben ist beides nicht durch Hinschauen, sondern durch zwei Prüfer in
`tests/test_handelszentrale_struktur.py`:

* kein Funktions-/Klassename darf in derselben Datei (Modul oder Klasse) zweimal definiert
  sein — per AST über alle Scopes, nicht als Suche nach einem bestimmten Namen;
* `ttk.Treeview` darf nur in `tabelle_mit_leiste` gebaut werden (Zeilenbereich des Helfers
  per AST), und jede Tabelle im gebauten Fenster muss `yscrollcommand`/`xscrollcommand`
  und eine Mausrad-Bindung tragen.

Merksatz: Eine Regel, die nur im Kopf der Autorin lebt, gilt bis zum nächsten Umbau.
Was im Prüfer steht, gilt auch für den Abschnitt, den morgen niemand liest.

Zusatzregel beim Prüfen von Tk-Geometrie: ein verstecktes Testfenster (`withdraw()`) hat
keine Größe — `yview()` bleibt dort `(0.0, 1.0)`, auch mit 40 Zeilen in einer
Fünf-Zeilen-Tabelle. Geprüft wird die Verdrahtung, nicht Tks Scrollrechnung; sonst
beweist der Test etwas über die Maschine.
