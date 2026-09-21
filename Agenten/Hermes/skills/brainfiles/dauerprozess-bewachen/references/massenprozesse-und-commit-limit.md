# Massenprozesse und Speicherdruck (Commit-Limit)

Gehoert zu jedem Lauf, der **viele Prozesse** anfasst: Repos aktualisieren, Profil-/Modell-Massenwechsel,
Prozessbaeume zaehlen, ganze Ordnertrees durchsuchen. Was dabei schiefgeht, sieht nicht nach Speicher aus.

## 1. Das Commit-Limit ist die Engstelle, nicht der RAM

Windows reserviert fuer jeden Prozess virtuellen Speicher (Commit) und deckelt die Summe auf
`RAM + Auslagerungsdateien`. Ist diese Grenze erreicht, scheitert **jede** neue Reservation —
unabhaengig davon, wie viel RAM frei ist.

    $os = Get-CimInstance Win32_OperatingSystem
    'Commit frei MB: {0:N0} von {1:N0}' -f ($os.FreeVirtualMemory/1KB), ($os.TotalVirtualMemorySize/1KB)
    Get-CimInstance Win32_PageFileUsage | ForEach-Object { 'Seite {0}: {1} MB' -f $_.Name, $_.AllocatedBaseSize }

Gemessenes Bild: **27,8 GB RAM frei**, aber nur **1,94 GB von 89,8 GB Commit frei** — also 98 %
reserviert bei reichlich freiem RAM.

Symptome, die alle NICHT nach Speicher aussehen:

- ein Modelllader bricht beim Laden ab: `ggml_backend_cpu_buffer_type_alloc_buffer: failed to allocate
  buffer of size 1.16 GB` / `cudaMalloc failed: out of memory` (bei nur 1,1 GB belegter GPU!)
- `git` im Sandbox-Terminal stirbt mitten im Lauf: `WinError 1455` ("Die Auslagerungsdatei ist zu klein")
- MSYS/bash: `fork: Resource temporarily unavailable`, `child_copy: cygheap read copy failed`
- ein natives Programm endet mit `0xC0000409` (STATUS_STACK_BUFFER_OVERRUN) statt mit einem Fehlertext

Wer eine dieser Meldungen sieht, misst ZUERST das Commit, statt das Modell, das Skript oder das
Programm zu verdaechtigen.

## 2. Den Verursacher nach Prozessgruppen finden, nicht nach Namen

    Get-Process | Group-Object ProcessName | ForEach-Object {
      [pscustomobject]@{ Name=$_.Name; Anzahl=$_.Count;
        GB=[math]::Round((($_.Group | Measure-Object PrivateMemorySize64 -Sum).Sum)/1GB,1) } } |
      Sort-Object GB -Descending | Select-Object -First 12

Gruppen mit vielen GLEICHEN Prozessen sind der Hinweis (hier: 88 `pythonw`, davon 84 Agenten eines
Treiber-Leaks). Danach die Gruppe nach **Kommandozeilen-MUSTER** des Kindes auflisten und die
`CreationDate`-Generationen zaehlen: erwartet ist EINE Generation je laufendem Zyklus.

## 3. Der Lauf gehoert auf den HOST, wenn das Sandbox-Terminal unter Druck steht

Bricht der Lauf im Werkzeug-Terminal mit `WinError 1455`/`fork`-Fehlern ab, ist das kein Grund,
ihn in kleinen Stuecken zu wiederholen — dieselben Stuecke scheitern an derselben Grenze. Stattdessen
**denselben Befehl ueber die Host-Shell** fahren (windows-mcp `PowerShell`), die kein
gedrosseltes Container-Commit hat:

    cd C:\Users\<user>\Documents\BrainFiles; python Agenten\Werkzeuge\<werkzeug>.py

Nachweis, dass es dieselbe Arbeit war: Anzahl der verarbeiteten Objekte und Exit-Code ausgeben lassen.
Der Sandbox-Zweig ist fuer Diagnose weiter brauchbar (Prozesslisten, Dateien), nur der Massenlauf
gehoert auf den Host.

## 4. Aufraeumen: Waisen beenden, dann Commit frei nachmessen

Sind die Verursacher Waisen (Kinder aus gestorbenen Vorgaengen), per PID-Beenden und **danach**
das Commit erneut messen — die Zahl ist der Beleg, nicht die Anzahl der Beendeten.

Gemessen nach dem Aufraeumen von 80 Waisen: 1,94 GB -> **22,0 GB** freies Commit, und das lokale
Modell lud danach (vorher jede Puffer-Anforderung gescheitert).

## 5. Was man NICHT schliesst

- Nicht "das Modell ist zu gross": erst das Commit messen (die abgelehnte Pufferanforderung war
  1,1 GB bei 27,8 GB freiem RAM).
- Nicht "das Werkzeug ist kaputt": dieselbe Datei lief nach dem Aufraeumen ohne Aenderung.
- Nicht "mehr RAM kaufen": mehr Auslagerungsdatei (Commit-Limit) oder weniger Prozessgruppen
  loesen dasselbe Problem sofort.
