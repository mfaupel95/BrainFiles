---
titel: Boersen und Schluessel
tags: [lektion, handel, kraken, schluessel]
aktualisiert: 2026-09-25
---

# Boersen und Schluessel

Zwei Lektionen vom 22.09.2026, beide aus einem einzigen Satz von Max
(„Grade wird auch kraken-cli integriert"). Beide haben dieselbe Wurzel: auf
der Boerse gilt FUER EINEN SCHLUESSEL, was das ZULETZT gesehene Werkzeug
getan hat - nicht, was das eigene Werkzeug tut.

## 1. Zwei Werkzeuge, ein Schluessel: die Nonce-Einheit muss die groesste sein

Kraken verlangt zu jeder signierten Abfrage einen **nonce** (eine Zahl, die
streng steigen muss) und merkt sich je Schluessel den **hoechsten** Wert. Die
Hausseite rechnete in **Mikrosekunden** (~1,77e12); die offizielle
`kraken-cli` signiert in **Nanosekunden** (~1,78e18) - rund eine Million Mal
groesser. Nach EINEM Aufruf der CLI war jede Hausabfrage kleiner als der
gemerkte Wert und endete mit `EAPI:Invalid nonce`.

**Wie es aufgefallen ist:** nicht am kraken-Skript, sondern an der
LIVE-SPERRE von mosaic - `--vorschau` meldete nicht mehr „Freigabefenster
nicht offen", sondern „Guthaben nicht abrufbar (EAPI:Invalid nonce)". Ein
Nebeneffekt auf einem anderen Weg ist oft das einzige Symptom.

**Regel:** benutzen zwei Werkzeuge denselben API-Schluessel, muss die
Nonce-Einheit die GROESSTE der beiden sein (hier: Nanosekunden, belegt durch
den Betrieb der offiziellen CLI). Wer eine zweite Anbindung einrichtet, misst
zuerst, womit sie signiert (`Agenten/Hermes/cache/kraken_nonce_sonde.py`).

**Gegenprobe, wenn es wieder passiert:** `kraken.guthaben('ZEUR')` ueber das
Hausmodul; kommt `EAPI:Invalid nonce`, hat ein anderes Werkzeug den Zaehler
hochgestellt. Heilen kann nur ein groesserer Wert, nicht ein Neustart.

## 2. Ein Programmpaar mit zwei Namen: der gueltige steht selten im Handbuch

In der Benutzerumgebung liegen **zwei** Kraken-Paare:

| Name | Zustand (gemessen 22.09.2026) |
|---|---|
| `KRAKEN_SPOT_API_KEY` / `KRAKEN_SPOT_API_SECRET` | **gueltig** - liest Haus-`kraken.py` und der Kraken-MCP |
| `KRAKEN_API_KEY` / `KRAKEN_API_SECRET` | existiert, Kraken antwortet `EAPI:Invalid key` |

Ein Programm, das „Invalid key" meldet, waehrend ein anderes mit demselben
Konto arbeitet, liest den ANDEREN Variablennamen - nicht einen falschen
Schluessel. `Agenten/Werkzeuge/kraken.ps1` setzt fuer die CLI die generischen
Namen aus den SPOT-Werten; danach meldet die CLI dasselbe Guthaben wie die
Hausseite.

**Regel:** vor jeder „Schluessel kaputt"-Aussage pruefen, welchen NAMEN das
Programm liest (Quelltext oder Doku), und beide Namen gegen die API halten.
Kein Wert wird je ausgegeben oder committet - nur Ja/Nein und Laenge.

## 3. Eine Abweisung ohne Zeugen ist keine Messung

Am 25.09.2026 wies Kraken von etwa 00:29 bis 01:33 **jeden** signierten Aufruf
ab - Spot `EGeneral:Permission denied`, Futures `authenticationError`, fuer jede
nonce, mit zwei unabhaengigen Umsetzungen (Hausmodul UND offizielle
`kraken-cli`). Am Haus lag es nicht: Schluesselwerte unveraendert, Uhr 1,3 s
daneben, Kraken online. Danach heilte es ohne Zutun. Die Ursache blieb offen,
und der teure Teil war nicht der Ausfall, sondern das **Schweigen**: keine
Kraken-Fehlerzeile in irgendeinem Log, die Spuren schrieben weiter
`(papier) ok`. Ohne Statuscode, `content-type`, Header und Rohantwort ist
„Key kaputt" von „Konto-Lockout" von „cloudflare" nicht zu unterscheiden -
geraten wird trotzdem.

**Regel 1 - Ebene trennen, nicht Symptom lesen.** Ein OEFFENTLICHER Aufruf
braucht keinen Schluessel, also kann ein Schluesselproblem ihn nicht treffen.
Faellt er mit, ist die Ebene Netz/IP/cloudflare; fallen nur die signierten
Wege, ist es Schluessel-, Rechte- oder Konto-Ebene. Deshalb misst das Werkzeug
alle vier Wege (`[[kraken-abweisungs-sonde]]`), nicht nur den, der weh tut.

**Regel 2 - nach einer Abweisung NICHT weiterklopfen.** Kraken sperrt ein
Konto zeitweise (`EGeneral:Temporary lockout`, etwa 15 Minuten), wenn zu viele
fehlgeschlagene Aufrufe kamen, und **jeder weitere Versuch setzt den Timer
zurueck**. Ein Waechter mit 15-Minuten-Takt, der einfach weiterfragt, haelt die
Sperre selbst am Leben - die Sonde wartet deshalb 60 Minuten.

**Regel 3 - Fehlversuche zaehlen beim Gegenueber.** Sechs Aufrufe mit einem
Attrappen-Schluessel, die aus einem Testlauf an `api.kraken.com` gingen, sind
kein Testfehler ohne Folgen: sie zaehlen bei Kraken als Fehlversuch und koennen
genau den Lockout ausloesen, den der Test untersuchen wollte. Eine Sonde oder
ein Test darf **nie** eine eigene Adresse mitbringen; die Adresse kommt aus dem
Hausmodul und wird im Test durch ein Attrappen-Ziel ersetzt.

**Gegenprobe, wenn es wieder passiert:** Protokollzeile aus
`Agenten/Handel/cache/kraken-abweisungen.jsonl` nehmen - `wege` zeigt die
Ebene, `zeuge.roh_*` zeigt Status, `content-type` und Rohkoerper. Kraken liefert
im cloudflare-Fall `5xx`/`1020` **ohne** JSON; ein JSON-`error`-Feld heisst
dagegen Auth-Ebene.

## Lektion: der Auth-Kopf steht in der Doku, die Wahrheit an der API (28.09.2026)

Ein Skill oder eine Anleitung nennt einen Header — das ist eine Behauptung, kein
Beweis. Beim ai4trade-Heartbeat stand `X-Claw-Token` in der Skill-Datei und
lieferte **401 Invalid token**, waehrend `Authorization: Bearer <token>` mit
demselben Token 200 lieferte. Vorgehen bei jedem neuen Zugang: **denselben
Aufruf mit mehreren Kopf-Varianten messen** (`Authorization: Bearer`,
`<X-Spezifisch>`, Query-Token) und die Messung dokumentieren. Ein Programm, das
nur den dokumentierten Weg kennt, faellt bei der ersten Umstellung still aus —
und Stille sieht aus wie Ruhe. Deshalb probieren die Haus-Werkzeuge den zweiten
Weg mit und melden den benutzten.

**Zweiter Teil derselben Lektion:** Fehlerantworten sind ein Leck. Die
ai4trade-API echot bei 422 das Feld `input` zurueck — also die ganze Anfrage
samt Passwort im Klartext. Regel: von einer fremden API niemals die rohe Antwort
protokollieren; erwartete Felder auswaehlen (`success`, `agent_id`, `detail.loc`)
und Geheimnis-Felder verwerfen. Gemessen heisst das: ein einziger Tippfehler im
Login-Aufruf kann ein Passwort in ein Protokoll schreiben.
