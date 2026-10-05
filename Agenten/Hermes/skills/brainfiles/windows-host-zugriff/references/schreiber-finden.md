# Den Schreiber eines Zustands finden — ohne zu raten

Die Frage lautet selten „was ist kaputt", sondern „**wer** hat das
geschrieben". Eine Datei ist zu einer Sekunde entstanden, ein Ordner ist
verschwunden, ein Junction wurde ersetzt — und im Baum arbeiten mehrere
Sitzungen gleichzeitig. Die Antwort steht in den Zeitstempeln; man muss sie nur
in der richtigen Richtung lesen.

## Die Regel: rueckwaerts von der Tatzeit

1. **Tatzeit festnageln.** Der praeziseste Zeuge ist der Gegenstand selbst:
   `(Get-Item <pfad> -Force).CreationTime` bzw. `.LastWriteTime` — bei einem
   neu entstandenen Ordner ist `CreationTime` die Minute, in der er den Verweis
er
   ersetzt hat. Nicht `stat` aus der Sandbox nehmen, wenn die Uhr der Sandbox
   nachweislich abweicht.
2. **Rueckwaerts-Index ueber die letzten Stunden bauen.** Alle Dateien der
   MOEGLICHEN Schreiber einsammeln und nach mtime sortieren — nicht die
   Ordnerliste ansehen, sondern die Zeitachse:

```powershell
$grenze = (Get-Date).AddHours(-6)
foreach ($w in '<ordner1>','<ordner2>') {
  Get-ChildItem $w -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -gt $grenze } |
    Sort-Object LastWriteTime |
    ForEach-Object { "{0:HH:mm:ss}  {1}" -f $_.LastWriteTime, $_.FullName }
}
```

   Was in der Minute der Tat geschrieben wurde, ist die Kandidatenliste. In
der
   Praxis waren es die Skripte der parallelen Sitzung — genau das, was man
   sucht.
3. **Je Kandidat auf die Tatwaffe pruefen, nicht auf den Namen.** `Remove-Item`,
   `New-Item`, `Move-Item`, `mklink`, `Junction` im Quelltext suchen. Ein
   Dateiname wie `datensortierung.ps1` legt ein Verschieben nahe — der
   Quelltext kann zeigen, dass er nur `Agenten/` und `MaxHirn/` anfasst und den
   betroffenen Ordner **nie** nennt. Damit ist er ausgeschlossen, obwohl die
   Zeit passt.
4. **Was sich ausschliessen laesst, ist so viel wert wie ein Treffer.**
   Ergebnis der Regel: „Tatzeit 22:12:52, in dieser Sekunde wurden genau diese
   drei Skripte geschrieben, keines nennt den Pfad — Ursache unbelegt." Das ist
   eine ehrliche Antwort und keine Niederlage. Sie verhindert den teuren
   Fehler, einen plausiblen Namen als Ursache zu verkaufen.

## Die Gegenprobe, die fast immer fehlt: laeuft der Test im Temp?

Bevor eine Testsuite verdaechtigt wird, ihre Fixture-Wurzel lesen. Ein Test, der
seine Fixtures unter `[IO.Path]::GetTempPath()` mit eigener GUID anlegt, kann
den echten Baum nicht angefasst haben — die Frage ist damit erledigt, ohne
einen Lauf zu opfern.

```powershell
Select-String -Path <test.ps1> -Pattern 'GetTempPath|NewGuid|\$fx\s*=' |
  ForEach-Object { "L$($_.LineNumber): $($_.Line.Trim())" }
```

Umgekehrt gilt: findet sich **kein** Temp-Anker und wird ein absoluter Pfad
zusammengesetzt, ist der Test ein ernster Kandidat — dann die Aufraeumroutine
am Ende lesen (`foreach ($p in $script:Aufraeumen) { Remove-Item -LiteralPath $p -Recurse -Force }`).

## Was ein Zeitgleichlauf NICHT beweist

- **Nicht die Uhr der Sandbox.** Weicht sie von der Host-Uhr ab, liegen alle
  frisch geschriebenen Dateien scheinbar Stunden zurueck und die Kandidatenliste
  ist leer. Vorher `Get-Date` auf dem Host gegen den Zeitstempel der eigenen
  letzten Schreiboperation halten.
- **Nicht die Reihenfolge innerhalb derselben Sekunde.** Zwei Dateien mit
  identischem Zeitstempel koennen Ursache und Folge sein (das Werkzeug und sein
  Bericht) — die Sekunde grenzt die Menge ein, sie ordnet sie nicht.
- **Nicht der Schaden selbst.** Eine zufaellig gleichzeitig geschriebene Datei
  ist noch keine Ursache. Ohne Quelltext-Beleg bleibt es ein Verdacht; so wird
  es auch gemeldet.

## Wenn der Schreiber unbelegt bleibt

Nicht weiter suchen, sondern den Wiederholungsfall absichern: eine Wache auf
den GEGENSTAND (nicht auf den Schreiber) — Existenz, Verweistyp, Ziel. Eine
Wache, die einen Verlust meldet, ist mehr wert als eine gelungene Zuschreibung,
weil der naechste Fall sonst wieder erst beim Symptom auffaellt.
