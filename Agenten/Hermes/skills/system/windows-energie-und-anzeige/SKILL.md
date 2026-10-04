---
name: windows-energie-und-anzeige
category: system
description: "Use when Bildschirm-Standby oder Schlafmodus nicht greifen."
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [Windows, Energie, Standby, Bildschirm, powercfg, RawInput, Beleg]
    related_skills: [systemdiagnose, trugschluesse, erhoehte-windows-aktion]
---

# Energie und Anzeige: messen statt den Plan lesen

Beantwortet „der Bildschirm geht nicht aus", „der Rechner schlaeft nicht", „er wacht
staendig auf". Der tragende Satz: **eine richtig gesetzte Auszeit ist kein Beweis, dass
sie greift.** Gemessen wird der Leerlauf-Timer gegen die Auszeit; bei einem Ruecksprung
wird der VERURSACHER benannt — Geraet oder Software. Nicht enthalten: der volle
Systemcheck (`systemdiagnose`), Aenderungen mit Adminrechten (`erhoehte-windows-aktion`).

## Wann

- „Monitor schaltet sich nicht auf Standby", „Bildschirm bleibt an", „geht nicht schlafen"
- der Bildschirm geht aus und SOFORT wieder an
- eine Auszeit ist gesetzt und wirkt trotzdem nicht
- der Rechner wacht ohne Zutun auf

## Werkzeug

`Agenten/Werkzeuge/eingabe-quelle.py` (versioniert) macht die Messung in einem Aufruf:

```
python Agenten\Werkzeuge\eingabe-quelle.py            # 5 Minuten, Vorgabe
python Agenten\Werkzeuge\eingabe-quelle.py --dauer 120
```

Es lauscht auf die Rohdaten (Raw Input), nennt zu jeder Eingabe den Geraetenamen
(VID/PID), stellt den hoechsten erreichten Leerlaufwert gegen die eingestellte Auszeit
und schreibt Log + Urteil. Waehrend der Messung nichts anfassen — jede eigene Bewegung
ist ein Messfehler.

## Vorgehen

1. **Ist-Stand: den AKTIVEN Plan und ALLE anderen lesen.** Nur den aktiven Plan zu
   pruefen uebersieht den Fall, dass Hersteller-Software (MSI Dragon Center, Hersteller-
   Tools) den Plan umschaltet — dann greift ploetzlich eine Auszeit von „Nie".
   ```
   powercfg -getactivescheme
   powercfg -list
   powercfg -q <plan-guid> SUB_VIDEO VIDEOIDLE      # je Plan, Netz UND Akku
   powercfg -q SCHEME_CURRENT SUB_SLEEP STANDBYIDLE # 0 = Rechner schlaeft nie
   powercfg -availablesleepstates
   ```
   Der Wert steht als Hex: `0xb4` = 180 s, `0x12c` = 300 s, `0x258` = 600 s, `0x0` = Nie.
2. **Leerlauf-Timer messen.** `GetLastInputInfo` (im Werkzeug) gegen die Auszeit halten:
   erreicht der Wert die Auszeit nicht, kann der Bildschirm nicht ausgehen — dann gibt es
   einen Verursacher, und der ist ab Schritt 3 zu benennen.
3. **Bei einem Ruecksprung den Verursacher trennen.** Ein Rohdaten-Ereignis MIT
   Geraetenamen = Hardware (Maus, Tastatur, Funkempfaenger, Adapter). Ein Ruecksprung
   OHNE Rohdaten-Ereignis = SOFTWARE hat die Eingabe erzeugt (`SendInput`): Agenten-
   Overlays, Makro-Software, Geraetetreiber-Suiten, PowerToys-Module. Das ist die
   Unterscheidung, die den ganzen weiteren Weg bestimmt.
4. **Wenn der Wert die Auszeit ERREICHT und der Bildschirm trotzdem an bleibt:** ein
   Prozess haelt einen Anzeige-Request. `powercfg -requests` nennt ihn beim Namen —
   **das braucht Admin** (siehe `erhoehte-windows-aktion`, dort auch die Falle mit dem
   Dialog). Ohne Erhoehung bleibt der Weg ueber das Ereignisprotokoll (Schritt 6).
5. **Wenn er ausgeht und sofort wieder an:** Aufweck-Geraete lesen und einzeln
   eingrenzen — `powercfg -devicequery wake_armed`, dann je Geraet „Energieverwaltung >
   Geraet kann den Computer aktivieren" abwaehlen, dazwischen messen. Immer nur EINES
   aendern, sonst ist der Beweis weg.
6. **Das Ereignisprotokoll mitlesen, wenn die Einstellung stimmt.** Gehaeufte Ereignisse
   2004 (Ressourcenerschoepfung) und Abstuerze von `dwm.exe` (Application-Log) gehen
   unerklaerlichem Anzeigeverhalten voraus: unter Speicherdruck faellt zuerst die
   Anzeige-Schicht aus, und der Bildschirm-Standby ist genau ihre Aufgabe. Ein Neustart
   mit freier Commit-Luft behebt das Symptom, ohne dass eine Einstellung sich aendert.
7. **ZWEIMAL messen.** Die erste Messung zeigt das Muster, die zweite beweist es: die
   Rueckspruenge der ersten koennen die eigenen Mausbewegungen sein. Erst eine Messung
   OHNE einen einzigen Ruecksprung entlastet die Einstellung und die Geraete.

## Fallen

- **`powercfg -change` rechnet in MINUTEN, nicht in Sekunden.**
  `powercfg -change -monitor-timeout-ac 180` setzt drei STUNDEN. Fuer drei Minuten ist
  `3` richtig. Nach jedem Setzen gegenlesen: `powercfg -q SCHEME_CURRENT SUB_VIDEO
  VIDEOIDLE` muss den erwarteten Hex-Wert zeigen (`0xb4` = 180 s).
- **Die Ausgabe von `powercfg` ist OEM-kodiert (cp850), nicht UTF-8.** Ein
  `subprocess.run(..., text=True)` bricht beim Auswerten mit `UnicodeDecodeError` ab,
  und die Folge ist ein `NoneType`-Fehler eine Zeile spaeter. Bytes holen und selbst
  dekodieren: `.stdout.decode("cp850", errors="replace")` — die gesuchten Woerter
  (`Wechselstromeinstellung`) sind ASCII und ueberleben das.
- **Eine Auszeit-Aenderung gehoert zurueckgesetzt.** Ein Diagnosewert (1 Minute) bleibt
  sonst stehen. Am Ende den Originalwert setzen und BEIDE Werte nennen (Netz/Akku) —
  der Ausgangswert auf diesem Rechner war 180/120 s.
- **Ein Ruecksprung ist nicht automatisch ein Programm.** Bevor ein Prozess verdaechtigt
  wird, die Messung ohne eigene Bewegung wiederholen; sonst entsteht aus einer
  Mausbewegung ein Befund gegen ein unschuldiges Programm.
- **Monitor-Standby und System-Standby sind zwei Dinge.** Der Bildschirm kann sauber
  abschalten, waehrend der Rechner nie schlaeft (`STANDBYIDLE` Netzbetrieb = 0). Beides
  getrennt benennen — und den PC-Schlaf NICHT ohne Auftrag setzen: er haelt
  Handels-Dauerlauf, Telegram-Bots und Gateway an.
- **Ruhezustand „nicht verfuegbar" ist bei aktivem Hypervisor normal.**
  `powercfg -availablesleepstates` meldet ihn dann als „durch eine interne
  Systemkomponente deaktiviert" (ueberwachter Host) — das ist kein Defekt und kein
  Grund fuer eine Reparatur. S3-Standby bleibt nutzbar.
- **Ein ctypes-Listener ohne festgenagelte Signaturen rauscht.** Ohne
  `argtypes`/`restype` wirft `DefWindowProcW` bei langen Werten
  `OverflowError: int too long to convert` — der Fehler kommt NACH der Auswertung, macht
  das Ergebnis also nicht falsch, verrauscht aber das Log bis zur Unlesbarkeit.
- **Ein selbstgebauter Listener braucht ein eigenes Fenster und `RIDEV_INPUTSINK`.**
  Message-only-Fenster plus `RegisterRawInputDevices` fuer Maus, Tastatur,
  Systemsteuerung und Consumer; ohne `INPUTSINK` kommen keine Ereignisse, solange der
  Fokus woanders liegt.

## Pruefen

Belegt ist der Befund, wenn die Zahlen zusammenpassen:

```
python Agenten\Werkzeuge\eingabe-quelle.py --dauer 300
```

Erwartet: eine Messung ohne Ruecksprung, in der der hoechste Leerlaufwert die Auszeit
erreicht — dann geht der Bildschirm aus, und die Frage ist eine andere (Aufweck-Geraet
oder Anzeige-Request). Oder eine Messung MIT Rueckspruengen, dann nennt das Log je
Ruecksprung die beteiligten Geraete bzw. meldet ausdruecklich „ohne Rohdaten-Ereignis"
(= Software). Beide Faelle mit dem Ist-Stand aus Schritt 1 im Bericht nennen.

## Bericht

- Ergebnis zuerst: greift die Auszeit, und wenn nicht — wer oder was verhindert sie.
- Was jetzt konkret funktioniert (mit der Zahl, die es belegt).
- Was absichtlich NICHT angefasst wurde: Aufweck-Rechte der Geraete, Hersteller-Software,
  Autostart-Gaeste, System-Standby.
- Genau eine Empfehlung, und die offene Entscheidung als Frage.
- Die Lehre ins Wiki (`MaxHirn/Wiki/Betrieb/`), nicht nur in die Antwort.
