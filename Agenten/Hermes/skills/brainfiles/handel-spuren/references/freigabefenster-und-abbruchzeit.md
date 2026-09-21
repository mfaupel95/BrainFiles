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
