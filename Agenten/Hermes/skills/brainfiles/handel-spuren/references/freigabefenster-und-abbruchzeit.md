# Freigabefenster im Dauerlauf: zwei Regeln, die zusammenpassen muessen

Fall vom 21.09.2026 (scanner, live). Die Ursache sah nach einem Zahlendreher
aus, war aber ein Vertrag zwischen zwei Stellen, den niemand aufgeschrieben
hatte.

## Was passierte

* 19:15 wurde `FREIGABE_ZEITLIMIT_S` von 120 auf 600 s gestellt (Auftrag Max:
  10 Minuten Zeit zum Bedienen).
* Der Dauerlauf bricht jeden Spur-Zyklus nach `TIMEOUT_S` ab - damals 300 s,
  hart im Aufruf verdrahtet.
* Ein Live-Zyklus aus dem Dauerlauf hielt sich fuer eine Sitzung am
  Bildschirm (`sitzung_da()` prueft `sys.stdin.isatty()`, ein Dienstprozess
  erbt ein Terminal), zog das Freigabefenster auf, wartete auf einen Klick,
  den niemand geben kann - und wurde nach 300 s abgebrochen.
* Ab 19:22 lief **jeder** scanner-Zyklus so. Mit dem Abbruch starb die
  Spiegelung nach Q: (sie stand nur am Zyklusende), das Ablehnungsprotokoll
  wuchs lokal weiter, die Live-Position wurde 2,5 h nicht auf Stop/Ziel
  geprueft. Sichtbar wurde es nur beim Nachsehen von Hand.

## Die zwei Regeln (beide sind Pflicht)

1. **Ein Dienstprozess darf das Freigabefenster nie erreichen.** Der
   Dauerlauf setzt `MAXHIRN_ROUTINE=1` in BEIDEN Modi (`zyklus_umgebung()` in
   `dauerlauf.py`); jede Spur mit Fenster fragt das vor `isatty()` ab. Eine
   Variable nur fuer `--papier` zu setzen ist der Fehler - die Begruendung
   "bei --live ist die Freigabe schon erteilt" klingt richtig und ist falsch.
2. **Fenster-Zeitlimit < Abbruchzeit des Aufrufers.** `TIMEOUT_S` (700) muss
   ueber `FREIGABE_ZEITLIMIT_S` (600) liegen, mit Reserve fuer die Rechnung
   danach. Sonst toetet der Abbruch einen Lauf, der korrekt wartet, statt
   dass das Fenster selbst ablehnt.

Festgehalten in `Agenten/Handel/tests/test_zyklus_zeitgrenze.py`: beide Modi
setzen die Variable (in einem echten Kindprozess je Spur geprueft), jedes
Zeitlimit liegt unter dem Abbruch, und kein Aufruf traegt eine nackte Zahl
statt der Konstante. Wer ein Zeitlimit anfasst, laesst diese Datei laufen.

## Bedingung 4 hat eine Frist, nicht nur einen Nachweis

`spiegelstand.py` vergleicht byte-genau - aber nur, wenn jemand es aufruft.
Der Tagesbericht zeigt die Zeile einmal am Abend. Deshalb:
`Agenten/Hermes/scripts/spiegelfrist-wache.py` als Hermes-Cron (15 min,
`no_agent`, leere Ausgabe = nichts senden). Er meldet nur, was die Frist
reisst (Standard 20 min; darunter heilt Test- und Laufrauschen von selbst),
und dieselbe Feststellung hoechstens alle 6 Stunden - sonst wird ein
abgezogenes Q: ein Alarm je Viertelstunde, und solche Meldungen liest
niemand mehr. Er kopiert NICHTS: nachkopieren verdeckt die Ursache.

## Pruefen, ob ein Lauf wirklich wartet

Die Zyklusdauer ist das Messinstrument: 300 s exakt = Abbruch, 600 s = das
Fenster hat selbst abgelehnt, Sekunden = kein Fenster im Spiel. Daneben
`Agenten/Handel/freigabe_journal.jsonl` (Eintraege "abgelehnt, Grund
Zeitlimit" = das Fenster ging auf) und das Dauerlauf-Log
(`<spur> TIMEOUT (exceeded <n>s limit)`).

## Aenderungen wirken ohne Neustart - der Neustart hat Nebenwirkungen

- Der Dauerlauf startet jede Spur JEDEN Zyklus als Kindprozess (Eintrag in
  `dauerlauf.SPUREN`: Ordner + Skript). Aenderungen an `<spur>/handeln.py`,
  `wachen.json`, Adaptermodulen und Tests wirken damit im NAECHSTEN Zyklus - ein
  Neustart des Dauerlaufs ist dafuer nicht noetig und nicht zu rechtfertigen.
- Nur `dauerlauf.py` selbst braucht einen Neustart: Spurenliste, `NUR_BASIS`,
  `AUTO_FREIGABE`, `TIMEOUT_S`.
- **Ein Neustart ist nicht harmlos.** Eine neu gestartete Spur bewertet den
  Herzschlag gegen den frischen Prozess; steht eine Live-Position, kann der erste
  Zyklus sie flachstellen. Vorher offene Live-Positionen und
  `freigabe_fenster.json` pruefen, Instanzen per PID beenden (nicht per
  Prozessname), danach die Prozesszahl NACHZAEHLEN - ein fehlgeschlagenes
  Beenden laesst zwei Treiber parallel laufen (Doppelorder-Risiko).
- **Beleg, dass eine Aenderung greift:** `--vorschau` MIT `MAXHIRN_ROUTINE=1`
  aufrufen (genau so ruft der Dauerlauf die Spur). Ohne die Variable beantwortet
  der Lauf eine andere Frage; `(live) ok` im Log ist der Modus des AUFRUFS und
  kein Beleg, dass eine Order moeglich waere.

## Das Tor muss aus dem Zweig lesen, der SCHREIBT

Der Herzschlag ist das Alter des letzten **Zyklus** - die Quelle muss der
Zustand sein, den der **laufende** Zweig fortschreibt. Wird er aus dem
Papierzustand gelesen, waehrend die Spur live faehrt, friert er ein: nach
`herzschlag_max_minuten` sperrt sich die Spur SELBST, `--vorschau` meldet
`Live waere gesperrt durch: Herzschlag alt`, waehrend das Dauerlauf-Log weiter
`(live) ok` schreibt. Und weil die Auto-Freigabe GENAU EINEN Grund verlangt,
(„nur das Fenster fehlt"), oeffnet sie weiter Fenster fuer einen Lauf, der
nicht handeln kann.

Richtig ist der **frischste** der beiden Staende (Papier UND Live, verglichen
ueber `letzter_lauf`): nur Papier sperrt eine Spur, die nie live lief - das war
der Grund, aus dem der Papierzustand ueberhaupt gelesen wurde -, nur Live ist
ein Kreislauf.

Merksatz: **Wenn ein Tor aus einem Zustand liest, muss es der Zustand des
Zweigs sein, der schreibt.** Und `--vorschau` mit `MAXHIRN_ROUTINE=1` ist der
einzige Beleg fuer den MODUS eines Laufs; `(live) ok` im Dauerlauf-Log ist der
Modus des Aufrufs, kein Orderbeleg.

## Guthaben-Tor: ERST deckeln, DANN das Fenster zeigen

- `mindest_guthaben_*` ist die Untergrenze des freien Guthabens, damit der
  **kleinste** Einsatz hineinpasst (`live_einsatz_min_*`). Ein Wert aus einer
  frueheren Einsatz-Rechnung sperrt sonst den ganzen Zweig, sobald das Guthaben
  darunter faellt - und der Sperrtext nennt nur das Guthaben, nicht die
  veraltete Annahme dahinter.
- Der Einsatz wird **zusaetzlich auf das freie Guthaben gedeckelt**
  (`frei * (1 - gebuehr_taker - 0,2 %)`); unter der Untergrenze wird NICHT
  gehandelt, mit Begruendung im Log. Ein Signal von 150 EUR bei 88 EUR frei
  waere sonst eine abgelehnte Order - kein Handel, aber im Log nicht von einem
  Signalfehler zu unterscheiden.
- **Die Reihenfolge ist Teil der Regel:** erst deckeln, dann das Freigabefenster
  oeffnen. Das Fenster (und die Freigabe am Bildschirm) muss den Betrag zeigen,
  der wirklich ausgefuehrt wird.
