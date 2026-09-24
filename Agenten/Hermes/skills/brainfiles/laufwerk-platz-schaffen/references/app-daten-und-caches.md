# App-Daten und Caches bewerten (C:)

Fertige Skripte statt abtippen: `scripts/groessen-messen.ps1` (reparse-sichere
Messung der Posten) und `scripts/caches-leeren.sh` (Caches leeren, je Ordner
vorher/nachher). Beide als Hintergrundauftrag starten und die Ausgabedatei mit
`read_file` lesen.

Reihenfolge: erst die Verbraucher BENENNEN (eine Zeile je Ordner, mit Zahl), dann
in *reproduzierbar* und *Software* trennen, dann nur die reproduzierbaren
anfassen. Der Vault ist nie die Ursache — er liegt bei ~6 GB, waehrend
App-Daten dreistellig sind.

## Messen (Windows, Reparse-Punkte aussortiert)

```powershell
$ErrorActionPreference = 'Continue'
foreach ($d in (Get-ChildItem $env:LOCALAPPDATA -Force -Directory -ErrorAction SilentlyContinue)) {
  if ($d.Attributes -band [IO.FileAttributes]::ReparsePoint) { "$($d.Name)`tVERWEIS" }
  else {
    $s = (Get-ChildItem $d.FullName -Recurse -Force -File -ErrorAction SilentlyContinue |
          Measure-Object -Property Length -Sum).Sum
    "{0,8} MB  {1}" -f [int][math]::Round($s / 1MB), $d.Name
  }
}
```

Als `.ps1`-Datei schreiben und mit `-File` starten, Ausgabe in eine Datei
umleiten (bash frisst Backtick-Formatstrings, s. Skill `windows-host-zugriff`).
Ein voller Lauf ueber `Local` **und** `Roaming` braucht mehrere Minuten — als
Hintergrundprozess mit Benachrichtigung starten, nicht blockierend messen.

## Gemessene Posten (Beispielrechner, ~86 GB Local / ~30 GB Roaming)

| Ordner | Groesse | Einordnung |
|---|---|---|
| `Local\Packages` | 24,5 GB | **Software** (App-Container: Teams/WhatsApp/Claude) — nie blind loeschen |
| `Local\Programs` | 8,7 GB | installierte Programme |
| `Local\NVIDIA` / `Local\Microsoft` | 5,9 / 5,7 GB | Treiber- bzw. App-Daten |
| `Local\pip` | 5,4 GB | reproduzierbar (`pip cache purge`) |
| `Local\hermes`, `Local\Google` | 4,2 / 4,0 GB | App-Daten |
| `Local\pnpm` | 3,4 GB | reproduzierbar (`pnpm store prune`) |
| `Local\ms-playwright` | 2,6 GB | **Software** — Browser-Binaries fuer Automatisierung |
| `Local\npm-cache` / `Local\uv` | 2,4 / 2,2 GB | reproduzierbar (`npm cache clean --force`, `uv cache clean`) |
| `Local\wsl` | 1,9 GB | Distro-Abbild (vorsichtig: enthaelt Zustand) |
| `Local\CrashDumps` / `Local\Temp` | 1,7 / 1,6 GB | Muell |
| `Roaming\Pioneer`, `Cemu`, `Mozilla` | 11,9 / 4,5 / 4,1 GB | Software-Zustand (DJ-Archiv, Emulator, Browserprofil) |
| `Roaming\npm` | 4,8 GB | **global installierte CLIs** — loeschen bricht Werkzeuge |
| `Roaming\uv` | 1,4 GB | reproduzierbar |

## Was der Nutzer hoeren will

- Eine Tabelle mit den Posten, nicht die Summe allein — sonst wird als Naechstes
  wieder der Dokumentenordner verdaechtigt.
- **Genau eine Empfehlung** mit der Zahl: „reproduzierbare Caches und Dumps
  loeschen, ~18 GB, kein Datenverlust", und die Befehle dahinter nennen.
- Die Nicht-Anfassen-Liste ausdruecklich nennen (Software, globale CLIs,
  Browser-Binaries, App-Container) — sie ist der Grund, warum nicht mehr weg
  kann, und sie verhindert Rueckfragen.

## Was die Reinigungsbefehle wirklich freigeben (gemessen)

Fahrplan: alle Befehle UND die Nachmessung in EINEM Hintergrundauftrag, Ausgabe
in eine Datei, danach die Datei lesen. Die Reinigung selbst (`npm`, `pnpm`) und
ein `du` ueber `pnpm`/`Temp` laufen einzeln schon in das Terminal-Zeitlimit
(~420 s); blockierend aufgerufen verliert man die Ausgabe UND weiss nicht, was
fertig wurde.

```bash
OUT="<scratch>/cache-leeren.txt"; : > "$OUT"
echo "df vorher: $(df -m /c | tail -1)" >> "$OUT"
pip cache purge            >> "$OUT" 2>&1; echo "exit $?" >> "$OUT"
npm cache clean --force    >> "$OUT" 2>&1; echo "exit $?" >> "$OUT"
pnpm store prune           >> "$OUT" 2>&1; echo "exit $?" >> "$OUT"
uv cache clean             >> "$OUT" 2>&1; echo "exit $?" >> "$OUT"
powershell -NoProfile -ExecutionPolicy Bypass -File "<scratch>/muell-leeren.ps1" >> "$OUT" 2>&1
echo "df nachher: $(df -m /c | tail -1)" >> "$OUT"
```

`muell-leeren.ps1` leert nur die Inhalte von `Local\CrashDumps` und `Local\Temp`
(`Remove-Item <ordner>\* -Recurse -Force -ErrorAction SilentlyContinue`) und
misst beide Ordner vorher/nachher.

| Ordner | vorher | nachher | Werkzeug |
|---|---|---|---|
| `Local\pip` | 5.428 MB | 1 MB | `pip cache purge` |
| `Local\uv` | 2.164 MB | 1 MB | `uv cache clean` — meldet trotzdem „No cache found" |
| `Local\npm-cache` | 2.381 MB | 951 MB | `npm cache clean --force` |
| `Local\pnpm` | 3.398 MB | 2.970 MB | `pnpm store prune` |
| `Local\CrashDumps` | 1.663 MB | 0 MB | Inhalt geloescht |
| `Local\Temp` | 1.596 MB | 255 MB | Inhalt geloescht (Rest in Benutzung) |

Summe der Einzelposten ~12,4 GB, an `df` gemessen **+11,2 GB** (frei 50,5 →
61,7 GB). Die Differenz sind Schreibvorgaenge waehrend des Laufs — **beide
Zahlen nennen**, nicht eine auswaehlen.

Regeln aus dem Lauf:

- **Die Meldung des Werkzeugs ist keine Quittung, die Groesse ist es.**
  `uv cache clean` schrieb „No cache found at <pfad>" und raeumte den Ordner
  trotzdem von 2,2 GB auf 1 MB. `uv cache dir` nennt den Pfad, nicht das
  Ergebnis — vorher/nachher messen.
- **Die Ausbeute je Werkzeug vorher ansagen.** `pnpm store prune` gibt nur
  wenige hundert MB zurueck (inhaltsadressiertes Store, der Inhalt ist von
  lebenden Projekten referenziert), `npm cache clean --force` etwa die Haelfte.
  Wer hier Gigabyte verspricht, laesst einen korrekten Lauf wie einen
  Fehlschlag aussehen.
- **`pip cache purge` wirkt benutzerweit**, unabhaengig davon, welches venv
  gerade aktiv ist (der Cache liegt unter `Local\pip`, nicht im Projekt).
- **Ein Rest in `Temp`/`CrashDumps` ist kein Fehler** — Dateien in Benutzung
  lassen sich nicht loeschen. Mit `-ErrorAction SilentlyContinue` arbeiten und
  danach die Groesse messen, statt Fehlerzeilen zu sammeln.
- **Die Nicht-Anfassen-Liste gilt auch hier:** `Packages`, `Programs`,
  `Roaming\npm`, `ms-playwright`, Browser-/Emulator-/DJ-Profile bleiben.

## Weitere Fundstellen fuer ploetzlichen Schwund

- **Update-Rueckstaende eines Programms:** Kopien seiner Zustandsdateien vor dem
  Update (`_Backups/`, `state-snapshots/`) — je Kopie mehrere hundert MB bis GB.
  Immer mitnennen, wenn das Programm ein eigenes Backup-Verzeichnis fuehrt.
- **Auslagerungsdatei** (`pagefile.sys`, auch mit eingestelltem BEREICH bis zum
  Maximum hochlaufend): Rezept in `references/auslagerung-ruhezustand.md`.
- **Logs von Dauerprozessen:** wachsen ohne Obergrenze, sichtbar nur am
  Plattenplatz; Drehung im Spawn-Pfad, s. Skill `dauerprozess-bewachen`.
