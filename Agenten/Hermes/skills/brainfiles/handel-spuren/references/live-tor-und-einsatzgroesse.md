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
| gedeckelter Betrag unter der Mindestmenge des Paares | die Mengenpruefung lehnt ab — ein eigener Mindestbetrag ist nicht noetig. Auf einem Markt mit GANZEN KONTRAKTEN rundet der Sendeweg dagegen still nach oben (min. 1 Kontrakt): dann sperrt die Kette ausdruecklich, siehe 5 |

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
  einem alten Beispielbetrag. Die Schwelle sagt nur: „darf ich ueberhaupt starten?" —
  nicht, ob der GEPLANTE Einsatz (Definition nach Risikorechnung, dann live_max_*)
  auf das freie Guthaben passt. Solange die geplante Order groesser ist als das
  freie Guthaben *minus* Gebuehr/Puffer, ist ein niedriges `mindest_guthaben` trotzdem
  keine Kaufkraft — und ein hohes waere unnoetig. Symptom: viele Zyklen ohne Einstieg,
  das Tor nennt nur „nur X frei, noetig Y", aber eine Order des geplanten Betrags waere
  an der Boerse gescheitert (**insufficient balance**), erst NACH dem Kaufversuch.
  Gegenprobe: den gedeckelten Betrag (nach `liberal * (1 - geb - 0,002)`) mit dem
  Mindestbetrag des Instruments vergleichen, nicht den risikonormale.

## 4. Fehlendes Geld gehoert in die Sperrliste — mit Boerse und Waehrung

Ein Guthaben-Tor, das nur den Betrag nennt, ist zweideutig, sobald eine Spur
mehrere Boersen kennt: „nur 0.71 EUR frei, noetig 60.00" liest sich wie die
Boerse, die in der ANDEREN Waehrung notiert — und die Fehlersuche beginnt beim
falschen Konto.

- **Boerse UND Waehrung nennen** (`kraken: nur 0.71 EUR frei, noetig 60.00`) und
  bei mehreren Boersen die uebrigen Gruende daneben stellen
  (`- dazu okx: nur 0.15 USDC frei, noetig 60.00`). Sonst sieht eine geprueft-leere
  Boerse wie eine uebersprungene aus.
- **Fehlende freie Margin gehoert in dieselbe Sperrliste wie die Bedingungen**
  (Muster `swap`: `nur 0.15 USDC frei, noetig 50.00 (max_margin_je_anlauf_usd)`).
  Steht die Pruefung nur unmittelbar vor der Order, oeffnet AUTO_FREIGABE weiter
  Fenster fuer einen Lauf, der nicht handeln kann, und der Versuch endet als
  Orderfehler (`51008`) statt als lesbarer Grund. Heute bindet das Guthaben fast
  immer zuerst: die Konten sind bis auf Cent in laufenden Positionen besichert.
- **Eine gescheiterte Guthaben-Abfrage sperrt NICHT.** `None` zurueckgeben und den
  Grund weglassen — ein Netzfehler darf eine scharfe Spur nicht stilllegen.
- **Der Geldgrund darf das Wort „Freigabefenster" nicht tragen.**
  `nur_fenster_fehlt` liest GENAU EINEN Grund mit diesem Wort als Fenster-Bitte;
  ein Geldgrund daneben ist richtig (zwei Gruende = keine Bitte), ein Geldgrund
  MIT dem Wort waere eine falsche Bitte.

**Testfalle beim Einbau:** eine neue signierte Guthaben-Abfrage in der
Sperrfunktion trifft JEDEN bestehenden Test, der diese Funktion aufruft — ohne
Attrappe laeuft dort eine echte Kontoabfrage. Die Naht (`okxf.guthaben_usdc`,
`handeln._guthaben_roh`) im `setUp` der betroffenen Testklassen ergaenzen und im
`tearDown` zuruecknehmen, dazu ein Testfall je Zweig: Geld fehlt / Geld reicht /
Abfrage scheitert.

## 5. Ein Einsatz-Limit traegt den Waehrungsnamen der SPUR

Die Live-Grenzen heissen `live_einsatz_<waehrung>` und
`live_max_risiko_gesamt_<waehrung>` (EUR fuer die Spot-Spuren, USD fuer die
Futures-Spur). Liest die Ableitung nur EINEN Namen, ist das kein Fehler, sondern
ein stiller Rueckfall: die Spur rechnet mit dem PAPIER-Einsatz weiter, waehrend
`--wachen` den Live-Einsatz anzeigt - die Anzeige zeigt eine Grenze, die nicht
wirkt.

Belegt: `live_wachen()` las nur `live_einsatz_eur`. Bei einem Papier-Einsatz von
50 und einem Kontrakt zu 117 USD rundete der Sendeweg auf EIN Kontrakt = 118 USD,
also das 2,4-fache des gedachten Einsatzes - und nichts meldete es.

Regel: den Namen aus dem Waehrungsfeld der Spur bauen
(`betrag_feld(w, "live_einsatz")`) und, solange beide Schreibweisen im Bestand
sind, beide lesen - je Spur gewinnt genau einer. Und der Einsatz gehoert zuerst
gegen die MINDESTMENGE des Instruments geprueft: liegt er darunter, ist die
Sperre die richtige Antwort, nicht das Aufrunden.

Testmuster: je einen Fall fuer die EUR-Spur und die USD-Spur, dazu die
Zusicherung, dass die Papierwerte unberuehrt bleiben (die Funktion gibt eine KOPIE
zurueck, der Aufrufer schreibt `w` nicht in die Datei).

Verwandt: `references/tor-kalibrierung.md` (Schwellen und Kosten),
`references/freigabefenster-und-abbruchzeit.md` (Fenster gegen Abbruchzeit),
`references/live-schalten.md` (der erste echte Geldpfad).
