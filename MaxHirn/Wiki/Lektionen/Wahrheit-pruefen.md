---
id: 20260921-wahrheit-pruefen
title: 'Lektionen — Wahrheit pruefen'
tags: [lektion, methode]
created: 2026-09-21
updated: 2026-09-22
related: ['[[Handel/Lektionen]]', '[[Lektionen/Tests]]']
summary: 'Vier Merksaetze, wie eine Aussage belegt wird, bevor sie rausgeht: zwei Zeugen, Konto statt Buch, Ursache statt Zaehler, Gegenprobe.'
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