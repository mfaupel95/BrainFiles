---
titel: Kraken-Abweisungs-Sonde
tags: [werkzeug, handel, kraken, wache]
aktualisiert: 2026-09-25
---

# Kraken-Abweisungs-Sonde

Ein Zeuge fuer den Fall, dass Kraken unsere signierten Aufrufe abweist - und
zwar bevor jemand nachfragt. Gebaut am 25.09.2026 als Antwort auf T-073.

## Warum es sie gibt

Zwischen etwa **00:29 und 01:33 am 25.09.2026** wies Kraken jeden signierten
Aufruf ab: Spot mit `EGeneral:Permission denied`, Futures mit
`authenticationError`. Und zwar fuer **jede** nonce und mit **zwei
unabhaengigen Umsetzungen** (unser `kraken_futures.py` und die offizielle
`kraken-cli`). Am Haus lag es nachweislich nicht: die Werte in
`HKCU\Environment` waren unveraendert, die Uhr 1,3 s daneben, Kraken online.
Um 01:33 ging es ohne Zutun wieder.

Bemerkenswert war nicht der Ausfall, sondern das **Schweigen**:

* die Spuren liefen im Papier weiter und schrieben `(papier) ok`,
* im Dauerlauf-Log steht zwischen 00:25 und 01:31 keine einzige Kraken-Fehlerzeile,
* `grep` nach `Permission denied`, `authenticationError`, `Temporary lockout`
  und `Invalid key` ueber Journale, Zustaende und Logs aller Kraken-Spuren:
  **kein einziger echter Treffer** (nur Vermerktexte in `wachen.json`).

Deshalb blieb die Ursache offen - nicht weil sie unerklaerbar waere, sondern
weil im Fehlerfall niemand Statuscode, Header und Rohantwort festgehalten hat.
Ein Nachweis ist keine Wache: beim Bus hatte dieselbe Ueberlegung am 15.09. zur
`bus-waechter`-Routine gefuehrt.

## Was sie misst - vier Wege je Lauf

| Weg | Aufruf | Schluessel |
|---|---|---|
| `offen_spot` | `api.kraken.com/0/public/Time` | nein |
| `privat_spot` | `/0/private/Balance` ueber Haus-`kraken.py` | ja |
| `privat_futures` | `futures.kraken.com/.../accounts` ueber `kraken_futures.py` | ja |
| `offen_futures` | `futures.kraken.com/.../tickers` | nein |

Die Unterscheidung ist der ganze Zweck:

* **faellt ein offener Weg**, kann es kein Schluesselproblem sein - ohne
  Schluessel gibt es nichts zu authentifizieren. Das heisst Netz, IP oder
  cloudflare. Kraken liefert in solchen Faellen `5xx`/`1020` statt JSON
  (`content-type` verraet es).
* **fallen nur die signierten Wege**, ist es Schluessel-, Rechte- oder
  Konto-Ebene. Kraken sperrt ein **Konto** zeitweise
  (`EGeneral:Temporary lockout`, ~15 Minuten), wenn zu viele fehlgeschlagene
  Aufrufe kamen - und **jeder weitere Versuch setzt den Timer zurueck**
  (Kraken-Doku). Deshalb klopft die Sonde nach einer Abweisung **60 Minuten
  nicht wieder** (`KUEHLZEIT_MIN`), statt wie ein typischer Waechter alle
  15 Minuten nachzufassen.

Im Fehlerfall macht sie **einen** zusaetzlichen Aufruf (den *Zeugen*) und
schreibt HTTP-Status, `content-type`, cloudflare-Header (`cf-ray`,
`cf-mitigated`), `retry-after`, `ratelimit-*` und den Rohkoerper weg.

## Aufruf

```
cd Agenten/Handel
..\..\..\python kraken_abweisungs_sonde.py            # ein Lauf, Textausgabe
python kraken_abweisungs_sonde.py --wache             # leere Ausgabe, wenn gesund
python kraken_abweisungs_sonde.py --stand             # letzter Stand
```

Cron `kraken-abweisung-wache` (alle 30 Minuten, `no_agent`, Telegram) ruft
`Agenten/Hermes/scripts/kraken-abweisung-wache.py`, das die Sonde als eigenen
Host-Prozess startet. Leere Ausgabe = nichts zu senden. Gemeldet wird nur:
Abweisung (mit allen Details) und Erholung („wieder offen nach X min").

Ablage:

| Datei | Inhalt |
|---|---|
| `Agenten/Handel/cache/kraken-abweisungen.jsonl` | eine Zeile je Lauf, im Fehlerfall voll |
| `Agenten/Handel/cache/kraken-abweisungs-sonde.json` | Zustand: letzter Lauf, laufende Stoerung, Kuehlzeit |
| `Agenten/Handel/tests/test_kraken_abweisungs_sonde.py` | 10 Tests, Kraken-Attrappe im Testprozess |

## Fallen

* **Eine Sonde darf keine eigene Adresse mitbringen.** Die erste Fassung trug
  eigene `SPOT_BASIS`/`FUTURES_BASIS`-Konstanten; die Tests bogen nur diese um,
  waehrend `kraken.guthaben()` weiter an `api.kraken.com` ging - **sechs
  Aufrufe mit Attrappen-Schluessel landeten beim echten Kraken**. Jeder davon
  zaehlt dort als Fehlversuch und kann genau den Konto-Lockout ausloesen, den
  die Sonde untersuchen soll. Jetzt nimmt die Sonde die Basis aus dem
  uebergebenen Hausmodul (`kraken.BASIS`), Tests reichen die Module ueber
  `lauf(module=...)` herein, und ein Test prueft ausdruecklich, dass die Sonde
  **keine** eigene Kraken-Adresse kennt (`test_sonde_kennt_keine_eigene_kraken_adresse`).
* **Ein Test, der nur Konstanten umbiegt, ist kein Test der Adresse.** Er
  beweist nur, dass die umgebogene Konstante benutzt wird.
* **Der echte `cache`-Ordner wird im Test nicht angefasst** - Modulwaechter
  `setUpModule`/`tearDownModule` vergleicht die Dateiliste.

## Offen (T-073)

Die Ursache des Ausfalls ist weiter offen. Neue Lage: sie kann beim naechsten
Auftreten aus dem Protokoll abgelesen werden. Zwei Antworten fehlen dann noch:

1. War Max in dem Fenster im Kraken-Portal (Schluessel bearbeiten/erzeugen)?
   Ein Key-Wechsel dort erklaert einen sofortigen, selbstheilenden Ausfall.
2. Ist die Stoerung `schluessel` oder `netz`? Das sagt der `wege`-Block der
   Protokollzeile - und bei `schluessel` unterscheidet der Zeuge
   (`401`/HTML gegen `200`/JSON) Rechte von Lockout.