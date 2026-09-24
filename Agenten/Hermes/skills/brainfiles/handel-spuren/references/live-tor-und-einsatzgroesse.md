# Live-Tor und Einsatzgroesse

Zwei Regeln, die jede Spur mit echtem Orderweg braucht. Beide sind in
`moondev_marktlage` (`live_kraken.py`) und `mosaic` (`handeln.py`) umgesetzt —
Namensmuster: `einsatz_gedeckelt(eur, w)` bzw. `betrag_gedeckelt(betrag, w)`.

## 1. Ein Tor liest den Zustand des Zweigs, der SCHREIBT

Der Herzschlag ist das Alter des letzten ZYKLUS, nicht des Papierbuchs. Eine
Sperre, die nur `zustand.json` liest, waehrend die Spur live laeuft (und der
Papierzweig deshalb seit dem Umschalten nichts mehr schreibt), friert ein: nach
`herzschlag_max_minuten` sperrt sich die Spur SELBST — „Live waere gesperrt
durch: Herzschlag alt".

Doppelt schlimm mit Auto-Freigabe: `nur_fenster_fehlt` verlangt GENAU EINEN Grund,
und „Herzschlag alt" ist genau einer. Der Dauerlauf oeffnet also im 30-Min-Takt
Fenster fuer einen Lauf, der gar nicht handeln kann — der Ausfall sieht aus wie
Betrieb, es entstehen keine Fehlerzeilen, nur Stille.

Regel: den FRISCHESTEN der beiden Staende lesen (`zustand.json` UND
`zustand.live.json`). Nur Papier zaehlt weiter, damit eine Spur, die noch nie live
lief, sich scharf machen kann; nur Live waere ein Kreislauf (Papierzweig
aktualisiert nicht mehr, das Tor bliebe zu).

Gegenprobe nach dem Fix: `<spur>/handeln.py --vorschau` mit `MAXHIRN_ROUTINE=1`
muss „Live waere gesperrt durch: nichts" melden (bzw. nur echte Gruende nennen).

Merksatz: **Bei jeder neuen Sperre fragen — welcher Zweig schreibt die Datei, die
ich hier lese?** Ein Tor, das aus dem Zustand des falschen Zweigs liest, ist ein
Selbstsperrer.

## 2. Erst den Einsatz DECKELN, dann das Freigabefenster zeigen

Ein Einsatz ueber dem freien Guthaben ist eine von der Boerse ABGELEHNTE Order:
kein Handel, aber eine Journalzeile „kauf fehlgeschlagen", die wie ein Defekt
aussieht. Der Deckel gehoert deshalb VOR `hole_freigabe`/`freigabe_protokoll`,
damit das Fenster den Betrag zeigt, der wirklich ausgefuehrt wird.

Form: `gedeckelt = frei * (1 - gebuehr_taker - 0.002)`, danach runden.
Rueckfall-Regeln, die in den Tests festgehalten sind:

| Fall | Verhalten |
|---|---|
| Betrag passt ins freie Guthaben | unveraendert, kein Hinweis |
| Betrag zu gross | auf den Deckel zurueck, Hinweiszeile ins Log |
| Guthaben nicht lesbar (Ausnahme) | Betrag UNVERAENDERT lassen — die Sperrenkette hat denselben Abruf schon gemeldet, hier nichts erfinden oder still abschalten |
| kein Guthaben (0) | melden, nicht handeln |
| gedeckelter Betrag unter der Mindestmenge des Paares | die Mengenpruefung lehnt ab — ein eigener Mindestbetrag ist nicht noetig |

Der Gebuehrensatz steht als Zahl in der `wachen.json` (`gebuehr_taker`), nicht im
Code. **Jede Spur mit Live-Pfad braucht diese Deckelung** — sonst waechst nur die
Fehlerzeile mit dem Limit.

Testmuster: die Deckelfunktion direkt pruefen (Seam `op_guthaben` der Spur
patchen, danach `addCleanup` zurueck) UND eine Quelltext-Pruefung, dass der
Deckel-Aufruf VOR dem Kaufaufruf steht (`quelle.index(...)` Vergleiche) — sonst
kann der Deckel an einer Stelle stehen, die nie erreicht wird.

## 3. Nach jeder Grenz-Erhoehung nachrechnen, WELCHES Limit danach bindet

Die Kette von der engsten zur weitesten Grenze: **je Trade (oder Risiko je
Position) → Anzahl Plaetze → Gesamtdeckel → freies Guthaben.**

- Ein hoeheres Je-Trade-Limit kann wirkungslos bleiben (Plaetze x Betrag liegt
  weiter unter dem Gesamtdeckel) oder den Gesamtdeckel ploetzlich binden.
- Umgekehrt bindet darunter oft allein das Guthaben — dann ist die Zahl am Papier
  richtig und live trotzdem nicht erreichbar.
- Im Bericht die Kette mit den ECHTEN Zahlen nennen, sonst ist die Aenderung nur
  eine Zahl. Und dazu genau eine Empfehlung: „die Grenzen sind nicht der Engpass,
  mehr Einsatz verlangt Guthaben" — nichts stillschweigend umschichten (Max
  schichtet kein Kapital um, wenn der Bestand passt).
- **Ein Guthaben-Tor ist die UNTERGRENZE, kein Puffer.** `mindest_guthaben*` wird
  mit dem KLEINSTEN Einsatz begruendet (Mindest-Einsatz + kleiner Puffer), nie mit
  einem alten Beispielbetrag: eine veraltete Zahl („3x Max-Einsatz") sperrt den
  Live-Zweig dauerhaft, obwohl ein gueltiger Einsatz hineinpasst. Symptom: viele
  Zyklen ohne Einstieg, das Tor nennt nur „nur X frei, noetig Y".

Verwandt: `references/tor-kalibrierung.md` (Schwellen und Kosten),
`references/freigabefenster-und-abbruchzeit.md` (Fenster gegen Abbruchzeit),
`references/live-schalten.md` (der erste echte Geldpfad).
