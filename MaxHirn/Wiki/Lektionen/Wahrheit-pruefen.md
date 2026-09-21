---
id: 20260921-wahrheit-pruefen
title: 'Lektionen — Wahrheit pruefen'
tags: [lektion, methode]
created: 2026-09-21
updated: 2026-09-21
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