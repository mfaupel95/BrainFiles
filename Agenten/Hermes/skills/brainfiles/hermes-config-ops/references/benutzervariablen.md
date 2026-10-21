# Windows-Benutzervariablen als Ablage fuer Zugangswerte

Wann diese Ablage statt Hermes' `.env`, wie man sie secret-frei liest und setzt,
und wie man belegt, dass der Wert vom Dienst akzeptiert wird.

## Welche Ablage fuer welchen Verbraucher

| Ablage | Wer liest sie | Verweisform |
|---|---|---|
| `Wissen/Zugaenge.md` | nur der Mensch | — (nie lesen, nie ausgeben) |
| `Agenten/Hermes/.env` (+ `profiles/<bot>/.env`) | Hermes fuer `${NAME}` in `config.yaml` | `${NAME}` |
| `HKCU\Environment` | jeder Prozess, der danach startet: MCP-Server, Claude Desktop, Skripte, curl, geplante Aufgaben | `${env:NAME}` in Hermes, sonst direkt |

Merksatz: der Verbraucher entscheidet die Ablage, nicht die Bequemlichkeit. Eine
Variable, die ein MCP-Server braucht, in Hermes' `.env` zu legen, ist wirkungslos —
der MCP-Client reicht Windows-Benutzervariablen nicht an Serverprozesse durch, ein
Server liest sie selbst aus `HKCU\Environment`.

## Ist-Stand lesen, ohne Werte auszugeben

```powershell
# alle Namen mit Laenge — nie die Werte
$k = Get-Item HKCU:\Environment
foreach ($n in ($k.GetValueNames() | Sort-Object)) {
  $v = $k.GetValue($n)
  if ($n -match 'KEY|TOKEN|SECRET|PASS') { "$n = ($($v.ToString().Length) Zeichen)" } else { $n }
}
$k.GetValueKind('NAME')                                    # String vs. ExpandString
$k.GetValue('NAME').Substring(0,[Math]::Min(9,$k.GetValue('NAME').Length))   # Praefix
```

- Das Praefix sagt die **Credential-Familie** (bei OmniRoute: `oma_live_` =
  Management/Access-Token, `sk-` = Inferenz-Key) — das entscheidet, welcher
  Endpunkt den Wert ueberhaupt annimmt.
- Bei zwei Ablagen (`.env` gegen Benutzervariable) ueber `sha8` vergleichen, nie
  ueber Werte: SHA-256 jedes `NAME=WERT` aus der `.env` gegen den Registry-Wert
  hashen; gleicher Anfang = gleicher Wert, sonst sind es zwei Keys.
- Ein negativer Befund aus einer fest verdrahteten Namensliste ist kein Beweis:
  vor der Meldung „fehlt" erneut `HKCU:\Environment` aufzaehlen.

## Setzen und in der Sitzung nachziehen

```powershell
[Environment]::SetEnvironmentVariable('NAME', (Get-Clipboard -Raw).Trim(), 'User')   # Wert aus der Zwischenablage
$env:NAME = (Get-Item HKCU:\Environment).GetValue('NAME')                            # fuer die laufende Sitzung
```

`setx NAME "<wert>"` funktioniert, hinterlaesst den Wert aber im Klartext in
`%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt`.
Ein laufender Prozess erbt die neue Variable nicht — er braucht einen Neustart
oder den Wert direkt aus der Registry.

## Belegen, dass der Wert akzeptiert wird (statt nur „steht drin")

```bash
# Wert in eine Shell-Variable lesen, nie als Literal in den Befehl
K=$(powershell -NoProfile -Command '(Get-Item HKCU:\Environment).GetValue("OMNIROUTE_ADMIN_API_KEY")' | tr -d '\r')
curl -s -o /dev/null -w '%{http_code}\n' --max-time 15 http://127.0.0.1:20128/api/providers
curl -s -o /dev/null -w '%{http_code}\n' --max-time 15 -H "Authorization: Bearer $K" http://127.0.0.1:20128/api/providers
```

401 ohne Token und 200 mit Token ist der Nachweis. Ein 200 ohne Token heisst nur,
dass die Anmeldung am Dienst abgeschaltet ist (`INITIAL_PASSWORD`/Login aus) —
dann beweist der Aufruf nichts ueber den Key.

## OmniRoute: zwei getrennte Zugangswege (Port 20128)

| Pfad | Credential | Form |
|---|---|---|
| `/v1/*` (Inferenz: chat/completions, models) | `OMNIROUTE_API_KEY`, Bearer | `sk-…`, 35 Zeichen |
| `/api/*` (Management: providers, tunnels, Gamification-Verwaltung) | `OMNIROUTE_ADMIN_API_KEY`, Bearer | `oma_live_…` aus der Oberflaeche (Settings -> Access Tokens) oder `omniroute connect` |

Ein `sk-…`-Inferenz-Key darf `/api/*` nur, wenn ihm im Dashboard `manage` oder
`admin` mitgegeben wurde — sonst **403 trotz gueltigem Key**. Anmeldung und Scope
sind zwei verschiedene Fehlerursachen: erst den Statuscode, dann die Scope-Meldung
lesen (`docs/guides/MANAGEMENT-AUTH.md` im OmniRoute-Klon).

Hermes' Provider-Keys liegen **nicht** hier, sondern in `Agenten/Hermes/.env` (und
je Profil in `profiles/<bot>/.env`) als `HERMES_CUSTOM_<host>_<port>_API_KEY`;
mehrere aehnlich benannte Variablen koennen existieren, nur eine traegt den Wert,
auf den die `config.yaml` verweist — deshalb ueber `sha8` identifizieren, nicht
ueber den Namen raten.

## Verbraucher suchen

- `search_files` (ripgrep) mit engem Pfad und `file_glob`; ein breites `grep -rIn`
  ueber die BrainFiles-Wurzel laeuft ins Zeitlimit (45 GB Archiv, Junctions).
- Variablennamen ankern: `OMNIROUTE_API_KEY` trifft als Teilstring in
  `HERMES_CUSTOM_OMNIROUTE_API_KEY`. Ein ungeankerter Treffer beweist keinen Leser.
- Die Warnzeile „N matches in hidden or gitignored files" ernst nehmen: die
  Konvention stand oft nur in einer ignorierten Notiz oder Sitzungsablage.
- Ergebnis ehrlich benennen: findet sich kein Leser, ist die Variable bisher nur
  eine Vereinbarung — das sagen, statt einen Verbraucher zu erfinden.

---

## Vollstaendiger Abschnitt aus dem SKILL.md-Rumpf

# Dritte Ablage: Windows-Benutzervariablen (`HKCU\Environment`)


Ist der Verbraucher **nicht** Hermes, gehoert der Wert in die Benutzervariable und
nicht in Hermes' `.env`: nur die Benutzervariable wird an jeden danach gestarteten
Prozess vererbt. Hermes selbst loest `${NAME}` aus seiner `.env` auf und
`${env:NAME}` aus der Prozessumgebung — beides greift erst in einem **neu
gestarteten** Hermes-Prozess, ein laufender sieht die Aenderung nie.

Setzen, ohne den Wert in die Kommandozeile zu schreiben:

```powershell
## Wert vorher in der Quelle kopieren
[Environment]::SetEnvironmentVariable('NAME', (Get-Clipboard -Raw).Trim(), 'User')
```

```powershell
## oder maskiert eintippen
$s = Read-Host -AsSecureString 'Wert'
$b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
[Environment]::SetEnvironmentVariable('NAME', [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b), 'User')
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b)
```

- **`setx NAME "<wert>"` nicht verwenden.** `setx` kennt keinen maskierten Weg, und
  PowerShell legt die Zeile im Klartext in
  `%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt` ab —
  dort stehen dann Zugangswerte, die niemand mehr rotiert.
- **Ist-Stand am Registry-Schluessel ablesen, nicht an einer Kandidatenliste.**
  Namen aufzaehlen und je Name nur Laenge und Praefix zeigen. Ein „FEHLT" aus einer
  fest verdrahteten Namensliste ist **kein Beweis fuer Abwesenheit** — die Variable
  kann zwischen zwei Aufrufen gesetzt worden sein, oft von einer zweiten Sitzung
  des Nutzers. Vor jeder Abwesenheitsmeldung neu aus `HKCU:\Environment` lesen.
- **In einer MCP-/Dienst-PowerShell kann `HKCU:\` einen ANDEREN Nutzer meinen als den
  interaktiven.** `Get-ItemProperty HKCU:\Environment` meldete hier faelschlich
  „keine OKX-Variable", waehrend `[Environment]::GetEnvironmentVariable('OKX_API_KEY','User')`
  denselben Namen als gesetzt zeigte. Die autoritative Existenz-/Wert-Pruefung fuer die
  persistente Benutzerumgebung ist deshalb immer dieser .NET-Aufruf — nie die
  Registry-Lese als einzige Quelle. Wer `setx /M` genutzt haben koennte, prueft zusaetzlich
  den `'System'`-Scope (`[Environment]::GetEnvironmentVariable('<NAME>','System')`);
  `setx` (ohne `/M`) schreibt nach `HKCU\Environment` und wird von Anwendern gern
  gesetzt — eine fehlende Umgebungsvariable heisst also nicht automatisch „nicht
  vorhanden", wenn ein Nutzer dazwischengekommen ist. Dynamischer Zugriff auf einen
  Variablennamen aus einer String-Variablen braucht in PowerShell 5.1 ausserdem die
  `${env:<NAME>}`-Schreibweise; `$env:<NAME>` ist ein Parse-Fehler.
- **Laufende Prozesse erben neu gesetzte Variablen nicht.** In der Sitzung nachziehen:
  `$env:NAME = (Get-Item HKCU:\Environment).GetValue('NAME')`. Das gilt auch fuer einen
  Dienst, den man per `Start-Process` startet: das Kind erbt die SHELL-Umgebung, nicht
  die Registry — die Variable VOR dem Start in der Shell setzen, sonst startet der
  Dienst mit dem alten Wert (gemessen: OLLAMA_MODELS korrigiert, Server per
  Start-Process neu gestartet, `/api/tags` zeigte weiter 0 Modelle, bis `$env:OLLAMA_MODELS`
  in der startenden Shell gesetzt war).
- **Belegt wird nicht „steht drin", sondern „wird akzeptiert":** den Wert in eine
  Shell-Variable lesen (nie als Literal in den Befehl) und den echten Endpunkt damit
  abfragen — ohne Token 401, mit Token 200 ist der Nachweis. Rezepte, Hash-Vergleich
  und die OmniRoute-Zugangstrennung: `siehe oben in dieser Datei`.
- **Wer liest einen Variablennamen? Namen ankern.** `OMNIROUTE_API_KEY` trifft als
  Teilstring in `HERMES_CUSTOM_OMNIROUTE_API_KEY` — ein ungeankerter Treffer beweist
  keinen Leser. Und `search_files` meldet Treffer in versteckten/ignorierten Dateien
  nur als Warnzeile („N matches in hidden or gitignored files"): dieser Zeile
  nachgehen, dort stand die einzige Notiz zur Variable. Breites `grep -rIn` ueber die
  Wurzel laeuft ins Zeitlimit (45 GB Archiv, Junctions) — `search_files` mit engem
  Pfad und `file_glob` nehmen.
