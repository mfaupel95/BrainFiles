# Auslagerungsdatei und Ruhezustand: Fix-Heft

Diagnose (vor jeder Aktion):
- `Get-CimInstance Win32_PageFileUsage`: `AllocatedBaseSize` vs. `CurrentUsage`.
  Eine systemverwaltete pagefile waechst bei einer Commit-Spitze auf ~RAM-
  Groesse (40 GB bei 63,7 GB RAM) und schrumpft NICHT von selbst — wenig
  benutzt + riesig zugeteilt = verschenkter Platz, kein Speicherengpass.
- Volsnap-Ereignis 36 im Systemprotokoll (Schattenkopien sterben wegen
  Platzmangel) = harter Dringlichkeitsgrund fuer die Platte.
- Schwund nicht einem "aktiven Schreiber" zuschreiben, bevor zweimal im
  Abstand von ~45 s der freie Platz gemessen wurde und `Win32_PageFileUsage`
  gelesen ist.

Fix (nur nach ausdruecklicher Freigabe des Nutzers — z.B. "weiter"):

1. Unter ~2 GB frei ZUERST Stufe-2-Caches leeren, bevor irgendetwas
   diagnostiziert wird: `uv cache clean`, `npm cache clean --force`, Temp-
   Inhalt. Frei vorher/nachher im SELBEN Durchgang messen.
2. Admin-Skript nach `Agenten/Routinen/` schreiben (dort liegen die
   versionierten Betriebswrapper; anlegen ist ok, Stufe 1 schuetzt nur
   Bestehendes):
   - PagingFiles lesen: `HKLM:\SYSTEM\CurrentControlSet\Control\Session
     Manager\Memory Management` (MultiString). Ausgangslage kann
     `c:\pagefile.sys 0 0 | o:\pagefile.sys 4096 16384` sein.
   - NUR die C:-Zeile auf feste Groesse (z.B. `C:\pagefile.sys 8192 8192`)
     ersetzen, ALLE uebrigen Zeilen (zweite Pagefile auf O:!) unveraendert
     behalten — ein blindes Setzen wuerde den O:-Eintrag loeschen.
   - `powercfg /h off` gegen `hiberfil.sys` (loescht normalerweise sofort;
     die laufende Sitzung kann die Datei bis zum Neustart halten — nicht
     von Hand loeschen, per `powercfg /a` verifizieren: "Ruhezustand ...
     deaktiviert").
   - Alles ins Log schreiben (Alt/Neu-PagingFiles, frei vorher/nachher,
     Admin: ja/nein) nach `Agenten/Routinen/logs/`.
3. Start: `powershell -NoProfile -Command "Start-Process powershell.exe
   -Verb RunAs -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy',
   'Bypass','-File','<skript>'"` — der UAC-Dialog erscheint auf dem Desktop
   und der Nutzer klickt. Bei Handy-Fernsteuerung des Rechners NICHT blind
   lostreten: der Dialog wartet dann ungesehen (kein Schaden, aber kein
   Ergebnis). Ablehnung erkennt man am Fehler des Start-Process.
   Verneinung nicht von Erfolg unterscheiden: das Log nach ~60-75 s lesen.
4. Verifizieren: Log (Admin: True, PagingFiles gesetzt), Registry zurueck-
   lesen, `powercfg /a`-Ausgabe. Die Differenz des freien Platzes kommt erst
   NACH dem Neustart (40 GB pagefile -> 8 GB, plus hiberfil beim Boot) — dem
   Nutzer die erwartete Rechnung nennen, nicht den sofortigen Gewinn.
5. Einmaliges Skript danach committen (nur eigene Datei stagen, fremden
   Arbeitsbaum liegen lassen) und im Commit das Skript als "einmalig"
   kennzeichnen.
