# Bildschirm-Standby: wenn der Monitor nicht ausgeht

Anlass: Max meldete am 04.10.2026 „Monitor schaltet sich nicht auf Standby".
Gemessen, nicht geraten — und am Ende war **kein Fehler in der Einstellung**
und **kein Dauerstörer** zu finden. Die Ursache lag davor.

## Was gemessen wurde

| Frage | Antwort | Beleg |
|---|---|---|
| Ist die Auszeit gesetzt? | Ja, 180 s (Netz) / 120 s (Akku) | `powercfg -q SCHEME_CURRENT SUB_VIDEO VIDEOIDLE` = `0xb4` |
| Steht ein Plan auf „Nie"? | Nein, keiner der vier | Ultimative Leistung 600 s, Ausbalanciert/Höchstleistung 300 s, Energiesparmodus 180 s |
| Hält ein Programm den Bildschirm fest? | Nein | 5,5 min Dauerbeobachtung: Leerlauf lief 181 s → 512 s **ohne einen Rücksprung** |
| Erzeugt ein Gerät Eingaben? | Nein | Zweite Messung: 746 s → 1076 s, **0 Rohdaten-Ereignisse** |

Bei 3 Minuten Auszeit war der Rechner anschließend 18 Minuten ohne jede Eingabe
— der Bildschirm ging aus und blieb aus.

## Die eigentliche Ursache

Aus dem Ereignisprotokoll, im selben Zeitraum wie das gemeldete Verhalten:

- **Ressourcenerschöpfung (Ereignis 2004):** 27.09. 27×, 29.09. 18×, 30.09. 17×,
  01.10. 7×, 03.10. 2×
- **Abstürze von `dwm.exe`** (Desktop Window Manager, zeichnet die Anzeige):
  27.09., 30.09. (2×), 01.10. (3×)
- **Kernel-Power 41** am 04.10. 19:10 → Neustart

Unter Speicherdruck fällt zuerst die Desktop-Schicht aus — und der
Bildschirm-Standby ist genau ihre Aufgabe. Nach dem Neustart (Commit frei
20,2 GB, Auslagerung O: auf 32 GB) läuft er wieder.

## Werkzeug

`Agenten/Werkzeuge/eingabe-quelle.py` beantwortet die Frage hart belegbar:

```
python Agenten\Werkzeuge\eingabe-quelle.py            # 5 Minuten messen
python Agenten\Werkzeuge\eingabe-quelle.py --dauer 120
```

Es lauscht auf die Rohdaten (Raw Input) und schreibt zu jeder Eingabe den
**Gerätenamen (VID/PID)**. Am Ende steht ein Urteil: höchster erreichter
Leerlaufwert gegen die eingestellte Auszeit.

Die Unterscheidung, auf die es ankommt:

- Eingabe **mit** Gerätenamen → **Hardware** (Maus, Tastatur, Adapter)
- Rücksprung des Leerlauf-Timers **ohne** Rohdaten-Ereignis → **Software** hat
  die Eingabe erzeugt (`SendInput`), z. B. ein Agenten-Overlay

Während der Messung nichts anfassen — jede eigene Bewegung ist ein Messfehler.

## Fallen, die Zeit gekostet haben

- **`powercfg -change -monitor-timeout-ac` rechnet in MINUTEN.** `180` setzt
  drei **Stunden**, nicht drei Minuten. Der korrekte Aufruf für 3 Minuten ist
  `powercfg -change -monitor-timeout-ac 3`. Gegenprobe immer über
  `powercfg -q SCHEME_CURRENT SUB_VIDEO VIDEOIDLE` (`0xb4` = 180 s).
- **`powercfg -requests` braucht Admin.** Ohne Erhöhung kommt nur „Dieser Befehl
  erfordert Administratorrechte". Es nennt den Prozess beim Namen, der einen
  Anzeige-Request hält — die einzige Quelle für Ursache (b).
- **Elevation nicht blind wiederholen.** Ein `Start-Process -Verb RunAs` blockiert
  auch ohne `-Wait`, bis der Dialog beantwortet ist. Drei Versuche hintereinander
  hinterließen drei `consent.exe`-Dialoge, die sich als normaler Nutzer **nicht
  beenden** lassen (Zugriff verweigert) — der Desktop bleibt verdunkelt, bis Max
  sie wegklickt. Also: erst ansagen, dann **einmal** starten.
- **Rücksprünge in der ersten Messung waren Mausbewegungen.** Der Beleg dafür ist
  die zweite Messung ohne einen einzigen Rücksprung — zwei Messungen, sonst
  hält man eine Bewegung für einen Prozess.
- **ctypes-Signaturen festnageln.** Ohne `argtypes`/`restype` wirft
  `DefWindowProcW` bei langen Werten `OverflowError: int too long to convert`;
  der Fehler kommt **nach** der Auswertung und macht das Ergebnis nicht falsch,
  verrauscht aber das Log.

## Merksätze

1. Eine richtige Einstellung ist kein Beweis, dass sie greift — **messen**:
   Leerlauf-Timer gegen Auszeit.
2. Beim Bildschirm-Standby zuerst den **Leerlauf-Timer** prüfen, nicht den Plan.
   Steigt der Wert nie auf die Auszeit, erzeugt etwas Eingaben.
3. Zwei Messungen statt einer: die erste zeigt das Muster, die zweite beweist es.
4. Unter Speicherdruck ist die Anzeige das erste Opfer — bei unerklärlichem
   Anzeigeverhalten zuerst `dwm.exe`-Abstürze und Ereignis 2004 ansehen.

Verwandt: [[Systemleistung-2026-09-29]], [[Wachen-und-Aufgaben]]