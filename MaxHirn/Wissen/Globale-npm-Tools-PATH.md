---
id: 20260901-globale-npm-tools-path
title: 'Globale npm-Tools und PATH'
tags: [system]
created: 2026-09-01
updated: 2026-09-06
related:
  - id: 20260831-python-versionen
  - id: 20260830-benutzerprofil
summary: 'Warum global installierte npm-CLIs (omniroute, opencode) auf diesem Rechner nicht erkannt werden und wie der PATH-Eintrag das behebt.'
---

# Globale npm-Tools und PATH

## Befund

`npm install -g <tool>` legt die Startdateien nach
`C:\Users\faupe\AppData\Roaming\npm\` (bestätigt: `npm prefix -g`). Dieser
Ordner stand **weder in der User- noch in der Machine-PATH**. Folge: jedes
`npm install -g` läuft durch, aber die Shell findet den Befehl nicht —
`CommandNotFoundException`. Mehrfaches Neuinstallieren ändert daran nichts,
weil die Startdatei immer in denselben ungesuchten Ordner geschrieben wird.

Ursache: **Volta** ist installiert (`C:\Program Files\Volta\` und
`%LOCALAPPDATA%\Volta\bin` stehen vorn auf PATH). Volta übernimmt `node`/`npm`,
aber globale npm-Pakete landen weiter im Standardordner `Roaming\npm`, und der
npm-Installer trägt diesen Ordner bei aktivem Volta nicht in die PATH ein.
Volta shimt nur Pakete, die man ausdrücklich mit `volta install <tool>` holt.

Betroffen sind alle so installierten CLIs, aktuell im globalen Store:
`omniroute` (v3.8.51) und `opencode-ai`.

## Behebung (einmalig, am 01.09.2026 gesetzt)

`C:\Users\faupe\AppData\Roaming\npm` wurde der **User-PATH** angehängt:

```powershell
[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path','User').TrimEnd(';') + ";$env:APPDATA\npm", 'User')
```

Danach greift der Eintrag in **neu geöffneten** Shells. Seither werden global
installierte npm-Tools direkt als Befehl erkannt.

## Für die nächste globale npm-CLI

Nichts weiter nötig — der PATH-Eintrag deckt alle künftigen `npm install -g`
ab. Wenn ein frisch installiertes Tool trotzdem nicht erkannt wird: prüfen, ob
es in einen anderen Prefix geschrieben wurde (`npm prefix -g`), oder es
alternativ über `volta install <tool>` verwalten lassen.

Für die aktuelle Sitzung ohne Neustart:

```powershell
$env:Path += ";$env:APPDATA\npm"
```

## Verwandt

[[Python-Versionen]] — dieselbe Klasse Problem für die Python-Laufzeiten.
