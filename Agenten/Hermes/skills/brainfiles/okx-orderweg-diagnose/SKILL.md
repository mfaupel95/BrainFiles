---
name: okx-orderweg-diagnose
description: "Use when eine Live-Order scheitert (OKX-Code deuten)."
version: 0.1.0
author: Hermes
license: MIT
category: brainfiles
platforms: [windows]
metadata:
  hermes:
    tags: [OKX, Handel, Live, Fehlersuche, Belegpflicht]
    related_skills: [handel-spuren, okx-live-anbinden, betriebsrunde]
---

# Orderweg einer Live-Spur: deuten, belegen, sicher beheben

Eine Handelsspur meldet einen Orderfehler vom Handelsplatz (Verkauf/Kauf/Stop
fehlgeschlagen, OKX-Code). Dieses Skill ist die Reihenfolge, in der so ein Fall
abgeraeumt wird: Ursache an der AUFRUFSTELLE festmachen, mit einem LESENDEN
Aufruf belegen, dann die kleinste sichere Aenderung — und Tests, die den Fall
festhalten. Es gilt fuer jede Live-Spur (scanner, xperp, mosaic, kraken), nicht
fuer die Auswertung der Buecher (`handel-spuren`).

## When to Use

- „scanner: Verkauf X fehlgeschlagen: OKX 51000 …" / „Kauf X fehlgeschlagen" / „Stop … fehlgeschlagen"
- ein OKX-Code muss gedeutet werden (51000, 51603, 51008, 50101)
- eine echte Position scheint zu fehlen, oder das Buch und das Konto passen nicht zusammen
- eine Order soll gesetzt/verkauft werden und der Live-Pfad ist unklar

## Pruefregel (die tragende Regel)

**Lesen vor Deuten, Beleg vor Aussage.** Jede Aussage ueber echtes Geld wird mit
einem signierten LESEaufruf bewiesen (Kontostand je Waehrung, Orderhistorie) —
aus der Fehlermeldung allein wird nichts geschlossen, und zum Diagnostizieren
wird NIE eine Order gesetzt (auch keine kleine, auch nicht „zum Testen").

## Procedure

1. **Fehlerzeile woertlich nehmen, Aufrufstelle suchen.** `grep -n "fehlgeschlagen"
   <spur>/handeln.py`. Achtung: eine Meldezeile umfasst oft MEHRERE Aufrufe — ein
   „Verkauf fehlgeschlagen" kann aus der Mengen-/Detailabfrage davor stammen, nicht
   aus dem Verkaufsaufruf selbst. Die Zeile lesen, die den Text druckt, und sehen,
   welche Aufrufe in ihrem `try` stehen.
2. **Code der Aufrufstelle zuordnen** (Tabelle: `references/okx-fehler-und-nachweis.md`).
   `51000` = Parameter leer/ungueltig, nicht „Order unbekannt" (`51603`).
3. **Belegen statt vermuten** — aus dem Spur-Ordner, mit dem Haus-`okx`-Modul:
   Basis und Schluessel ausgeben (`okx._live_basis()`, `okx.schluessel_vorhanden()`),
   dann `okx._roh(pfad, signiert=True)` fuer Kontostand je Waehrung und Orderhistorie.
   Rezept + fertige Endpunkte: `references/okx-fehler-und-nachweis.md`.
   Buch gegen Boerse stellen (Fuellung, Geister, Wiederherstellung):
   `references/buch-gegen-boerse.md`.
4. **Folgen benennen**: was war echt (Konto), was nur Buch (Journal), was der Nutzer
   wissen muss. Leere Kontodetails + leere Orderhistorie = die Position hat es am
   Handelsplatz nie gegeben — dann ist der abgebrochene Verkauf RICHTIG gewesen.
5. **Kleinste sichere Aenderung bauen.** Bei einem Verkauf ohne Order-Kennung: vor
   jeder Abfrage abbrechen und es im Klartext drucken — siehe Pitfalls. Bestehende
   Aufraeumfunktionen der Spur nutzen statt eine zweite Wahrheit zu bauen.
6. **Test, der den Fall festhaelt** — im Attrappen-Stil der Spur
   (`scanner/tests/test_handeln_boersenstop.py`): Attrappe statt `okx`, Journal in
   eine Temp-Datei, und pruefen, dass KEINE Order an die Boerse geht.
7. **Belegen und sichern**: Tests der Spur,
   `Agenten/Handel/spiegelstand.py` (Bedingung 4, muss byte-gleich melden),
   Commit nur eigener Pfade (`brainfiles-auftrag`).
8. **Kein Dauerlauf-Neustart noetig**: der Dauerlauf startet `handeln.py` je
   Zyklus als eigenen Prozess — die Aenderung wirkt im naechsten Zyklus.

## Pitfalls

- **`51000 Parameter ordId error` ist ein Parameterproblem, kein Bestandsproblem.**
  Python-`urlencode` schreibt `None` als den Text „None"; eine Position ohne
  Order-Kennung schickt also genau das. Ein formal gueltiger, aber unbekannter
  `ordId` ergibt `51603`. Immer die Aufrufstelle lesen, nie den Code allein deuten.
- **Eine ANGENOMMENE Order ist keine Position.** `order_limit()` gibt die ordId
  zurueck, sobald der Handelsplatz sie annimmt — nicht wenn sie fuellt. Wer sofort
  bucht, hat bei einem Limit, das nie fuellt, eine Position im Buch und an der
  Boerse nur eine offene Order (`accFillSz 0`, `state live`): ein Platz ist belegt,
  der Ausstieg verkauft ins Leere, Funding und Bilanz rechnen fuer etwas, das
  niemand haelt. Vor dem Buchen die Fuellung pruefen (`accFillSz`), bei 0 die Order
  stornieren und nichts buchen, bei Teilfuellung den Rest stornieren und nur das
  Gehandelte buchen. Unbekannte Antwort (Abfragefehler) zaehlt als nicht gefuellt.
- **Das Buch gegen die BOERSE pruefen, nicht gegen sich selbst.** `/account/positions`
  ist die Wahrheit eines Live-Buchs; fehlender Bestand oder Groesse 0 (OKX behaelt
  geschlossene Positionen als Zeile) ist ein Geist. Beim Ausbuchen die offene Order
  dazu stornieren, sonst fuellt sie spaeter und erzeugt eine Position ohne Buch.
  Reihenfolge beachten: **erst den Orderzustand fragen, dann ausbuchen** — ein
  Limit, das genau jetzt fuellt, sieht wie ein Geist aus, ist aber eine echte
  Position (gefuellte Order = Position, auch wenn die Positionsliste nachhinkt).
  Faellt die Abfrage aus, bleibt das Buch unberuehrt: ein Netzfehler darf nie
  Positionen loeschen.
- **Ein PAPIERLAUF schliesst keine Position mit `modus=live`.** Loest der
  Kill-Switch aus, waehrend die Spur ohne Fenster (oder mit `handel_erlaubt=false`)
  im Papier laeuft, schliesst die Flachstellung sonst auch echte Positionen — aber
  nur im Buch, an der Boerse bleibt die Position offen. Ergebnis: eine gehebelte
  Position ohne Buch, kein Ausstieg, kein Funding. Solche Positionen im Papierlauf
  stehen lassen und im Klartext melden; geschlossen werden sie nur vom Live-Lauf.
- **Sperre und Kill-Switch sind zwei Dinge — vor dem Entsperren beide rechnen.**
  `handel_erlaubt=true` allein genuegt nicht: liegt der Ruecklauf ueber
  `kill_switch_gesamt_usd`, stellt der naechste Zyklus sofort wieder flach und
  verkauft dabei die gerade wieder eingebuchte Position. Vor dem Entsperren die
  eigene `lage()` fragen (Ruecklauf, Hoechststand, Groessenfaktor) und den Deckel
  datiert anheben oder die Sperre bleibt sinnlos. Danach einen Zyklus abwarten und
  Buch, Journal und Boerse gegeneinander belegen.
- **Eine ausgebuchte, aber echt vorhandene Position gehoert ins Buch zurueck** — mit
  den Werten der Eroeffnungszeile aus dem JOURNAL, nie geschaetzt; zusaetzlich
  pruefen, ob der boersenseitige Stop noch steht (Anhaenge einer Order greifen
  nicht immer), und ihn sonst nachsetzen. Eine gehebelte Position ohne Stop laeuft
  bis zur Liquidation, wenn der Rechner ausfaellt.
- **Kein Market-Verkauf ohne Order-Kennung.** Eine Position ohne `kauf_ord_id` hat am
  Handelsplatz nichts, was verkauft werden koennte: der Verkauf muss VOR der ersten
  Abfrage abbrechen. Ein Market-Verkauf ohne Kennung verkauft nicht „nichts", sondern
  den GESAMTEN Bestand dieses Werts auf dem Konto — auch Coins, die die Spur nie
  gekauft hat.
- **Die Quote-Waehrung entscheidet, was kaufbar ist.** `ccy=USDT` gegen `ccy=USDC`
  pruefen: bei 0 USDT scheitert JEDE `-USDT`-Vorschau, waehrend die `-USDC` desselben
  Laufs durchgeht. Solche Fehlkaeufe fallen nicht auf — sie stehen nur nicht im Buch.
- **Ein Buch fuer Papier und Live.** Faellt ein Live-Kauf aus, fuellt der naechste
  Papierlauf dasselbe Buch; im Live-Lauf stehen dann Positionen ohne jede Order,
  belegen Plaetze und laufen bei jedem Ausstieg in denselben Fehler. Ein Live-Lauf
  muss Papier-Altlasten VOR dem Handeln ausbuchen (idempotent, im Live-Pfad gated).
- **Ein fehlgeschlagener LESEaufruf darf keinen Ausstieg blockieren.** Eine
  Mengenabfrage, die die ganze Verkaufslogik umwirft, macht aus einem
  Verbindungsfehler eine offene Position. Abfrage und Verkauf getrennt behandeln
  (Menge notfalls aus dem Buch rechnen) — aber nur, wenn die Order-Kennung wirklich
  vorhanden ist.
- **Kein Schalter fuer eine Diagnose.** Ein Fehlercode ist kein Grund, `--live` zu
  fahren, eine Testorder zu setzen oder Guthaben zu verschieben. Beweis ist der
  LESEaufruf.
- **Diagnose-Skripte nicht in den Spur-Ordner legen.** Nach
  `Agenten/Hermes/cache/` schreiben und danach loeschen; der Spur-Ordner ist
  versioniert und wird gespiegelt.
- **Antwortform an Max.** Zuerst die Ursache in einem Satz, dann die Belege
  (Zahlen, nicht Adjektive), dann was jetzt anders ist und was absichtlich NICHT
  angefasst wurde (Fremdarbeit im Arbeitsbaum, laufende Prozesse), am Ende genau
  eine naechste Aktion. Keine Optionsliste, keine Rueckfrage nach Erlaubnis fuer
  additive Arbeit.

## Verification

```bash
cd Agenten/Handel/<spur>/tests && ../.venv/Scripts/python.exe -m unittest discover -s . -t .
cd Agenten/Handel && scanner/.venv/Scripts/python.exe spiegelstand.py   # byte-gleich (Q:)
```

Ein Fall ist fertig, wenn der Code an der Aufrufstelle erklaert ist, ein LESEaufruf
die Aussage belegt (Konto/Historie), ein Test den Fall festhaelt und der Spiegel
byte-gleich meldet.
