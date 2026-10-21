# Wenn die Wache den Lauf selbst neu starten muss

Eine Wache, die nur MELDET, ist bei einem Ausfall so lange wirkungslos, wie
niemand die Meldung liest. Gemessen: ein Live-Loop stand 5,5 h still, waehrend
die Wache ihn korrekt als "HAENGT" gemeldet hatte — die Meldung war da, die
Handlung fehlte. Der Ausfall wird nicht am Erkennen sichtbar, sondern an der
fehlenden Reaktion.

## Die Entscheidung ist eine reine Funktion

```
neustart_grund(steht, deckung, jetzt_s, merk) -> str | None
```

Ohne Prozess, ohne Netz, ohne Seiteneffekt — nur so ist sie testbar. Drei
Bedingungen, alle drei muessen halten:

1. **Nur wenn der Lauf steht.** Status aelter als die Frischeschwelle ODER
   `state != running`. Ein gesunder Lauf wird nie angefasst.
2. **Offene Position nur bei VOLLSTAENDIGER Deckung an der Boerse.** Deckung ist
   die Summe der Schutz-Order-MENGEN auf der Gegenrichtung (nicht die Anzahl der
   Orders). Ungedeckt, teilgedeckt oder nicht lesbar = nur melden. Der Grund:
   ein Prozesswechsel kann eine Position nicht mitnehmen — der Schutz muss
   ausserhalb des Prozesses liegen (conditional Order an der Boerse).
3. **Hoechstens ein Neustart je Abstand** (15 min). Ohne diese Sperre startet
   die Wache im Cron-Takt gegen einen Fehler an, der beim Starten entsteht.

Nach dem Start **beweisen, dass er lebt**: bis N Sekunden auf einen frischen
Status warten. Kommt keiner, ist das eine WARNUNG — und es wird KEINE Sperre
gesetzt, damit der naechste Tick es erneut versuchen darf.

## Aktion: die vorhandenen Funktionen benutzen

Keinen zweiten Starter bauen: dieselben Funktionen nehmen, die der
Nachzieher/Starter der Spur schon hat (`loop_pid`, `pid_lebt` MIT Programmnamen,
`loop_beenden`, `lauf_starten`). `taskkill /F` tat im Haus schon nichts;
`Stop-Process -Id <pid> -Force` ueber PowerShell ist der belegte Weg, danach die
Prozesszahl nachzaehlen.

## Testen ohne echten Prozess

- Attrappe des Moduls, das die Prozessfunktionen haelt; jeder Aufruf wird
  mitgeschrieben (`rufe.append(...)`).
- Faelle: gesund -> kein Neustart · steht + ungedeckt -> kein Neustart · steht +
gedeckt -> Neustart · Sperrfrist laeuft -> kein Neustart · Beenden scheitert ->
KEIN Start · Start ohne frischen Status -> Warnung ohne Sperre.
- Zusaetzlich die `haupt()`-Funktion gegen die Attrappe laufen lassen: das
  beweist die VERDRAHTUNG (Meldung + Neustart + Merkdatei), nicht nur die Regel.
- Gegenprobe: die Regel ueberspringen (immer `steht` zurueckgeben) und sehen,
  dass mindestens drei Tests rot werden. Ohne diese Gegenprobe ist unklar, ob
  die Tests die Regel pruefen oder nur die Attrappe.

Zeit nicht verbrauchen: die Wartezeit auf den frischen Status als Modulkonstante
fuehren und im Test auf 1 s setzen.

## Meldung

Eine AKTION wird immer berichtet, auch wenn das Tageslimit fuer
Beobachtungsmeldungen erschoepft ist — sonst startet die Wache still. Grund,
alter und neuer PID und das Ergebnis ("neuer Status frisch, N Kerzen") gehoeren in
EINE Meldung.
