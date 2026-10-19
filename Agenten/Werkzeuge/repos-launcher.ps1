# Oeffnet Git-Repositories aus Werkstatt in Windows Terminal oder GUI.
#
# UMGEZOGEN am 18.09.2026: lag vorher unter Agenten\Routinen\ - dort gilt jede
# .ps1 als Bus-Routine, und dieses Skript ist keine (es ist ein Werkzeug).
# Ausserdem war es nie versioniert, also nach einem Verlust nicht
# wiederherstellbar. Jetzt unter Agenten\Werkzeuge\ und in der .gitignore
# freigegeben.
#
# WARUM ES WEICH IST (18.09.2026): vorher brach der Aufruf hart ab
# ("lazygit.exe wurde nicht gefunden"), sobald ein Werkzeug fehlte - und
# lazygit.exe fehlt auf diesem Rechner. Der Modus Tui war damit kaputt. Jetzt
# wird ein fehlendes Werkzeug GENANNT und der Modus uebersprungen; nur wt.exe
# ist Pflicht. (Modus Gui funktioniert: VSCode ist installiert - der erste
# Befund "code.exe fehlt" kam aus einer Pruefung ueber die bash-PATH, die den
# Windows-PATH nicht sieht. Lehre: Werkzeuge mit Get-Command in PowerShell
# pruefen, nicht mit which.)
#
# Fuer EIN einzelnes Repo ist die Repos-Zentrale der bequemere Weg
# (Agenten\Werkzeuge\repos-zentrale): Fenster mit Start, Bot-Chat und Doku.
# Dieses Skript bleibt der Massenweg (alle Repos auf einmal).
#
# Beispiele:
#   .\repos-launcher.ps1 -Mode Terminal
#   .\repos-launcher.ps1 -Mode Terminal -Repos codex,odysseus -SeparateWindows
#   .\repos-launcher.ps1 -Mode Gui -Repos one-skill-to-rule-them-all
[CmdletBinding()]
param(
    [ValidateSet('Terminal', 'Tui', 'Gui')]
    [string]$Mode = 'Terminal',

    [string[]]$Repos,

    [switch]$IncludeNonGit,

    [switch]$SeparateWindows
)

$ErrorActionPreference = 'Stop'

$agenten = Split-Path -Parent $PSScriptRoot
$brainFiles = Split-Path -Parent $agenten
$reposRoot = Join-Path $brainFiles 'Werkstatt'

$uebersprungen = New-Object System.Collections.Generic.List[string]

function Get-RepositoryDirectories {
    if (-not (Test-Path -LiteralPath $reposRoot -PathType Container)) {
        throw "Repos-Verzeichnis fehlt: $reposRoot"
    }

    $directories = Get-ChildItem -LiteralPath $reposRoot -Directory |
        Where-Object { $_.Name -ne 'copilot-worktrees' -and $_.Name -ne '.vscode' }

    if (-not $IncludeNonGit) {
        $directories = $directories |
            Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName '.git') }
    }

    if ($Repos) {
        $wanted = [System.Collections.Generic.HashSet[string]]::new(
            [StringComparer]::OrdinalIgnoreCase
        )
        foreach ($repo in $Repos) {
            [void]$wanted.Add($repo)
        }
        $directories = $directories | Where-Object { $wanted.Contains($_.Name) }

        $missing = $Repos | Where-Object {
            -not ($directories.Name -contains $_)
        }
        if ($missing) {
            throw "Nicht gefunden oder kein Git-Repository: $($missing -join ', ')"
        }
    }

    # Ein gesuchter Name darf auch ohne .git gefunden werden (z. B. eine
    # Worktree-Sammlung) - dann lieber oeffnen als schweigen.
    $directories | Sort-Object Name
}

function Get-ExecutablePath {
    # -Pflicht: ohne dieses Werkzeug ist der Aufruf sinnlos (wt.exe).
    # Sonst: fehlt es, wird der Modus uebersprungen und der Name genannt -
    # KEIN Abbruch, damit ein fehlendes Werkzeug nicht alles blockiert.
    param([string[]]$names, [switch]$Pflicht)

    foreach ($name in $names) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($command) {
            return $command.Source
        }
    }

    if ($Pflicht) {
        throw "$($names -join ' / ') wurde nicht gefunden. Bitte installieren oder PATH pruefen."
    }
    $script:uebersprungen.Add(($names -join ' / '))
    Write-Warning "$($names -join ' / ') fehlt - '$Mode' wird uebersprungen."
    return $null
}

function ConvertTo-PowerShellLiteral([string]$value) {
    "'" + $value.Replace("'", "''") + "'"
}

$repositories = @(Get-RepositoryDirectories)
if (-not $repositories) {
    throw "Keine passenden Repositories unter $reposRoot gefunden."
}

$windowArguments = @()
if ($SeparateWindows) {
    $windowArguments = @('-w', 'new')
}

$gestartet = 0

switch ($Mode) {
    'Terminal' {
        $terminal = Get-ExecutablePath 'wt.exe' -Pflicht
        foreach ($repository in $repositories) {
            Start-Process -FilePath $terminal -ArgumentList @(
                $windowArguments
                'new-tab'
                '--title'
                $repository.Name
                '--startingDirectory'
                $repository.FullName
                'powershell.exe'
                '-NoExit'
                '-NoProfile'
            ) | Out-Null
            $gestartet++
        }
    }

    'Tui' {
        $terminal = Get-ExecutablePath 'wt.exe' -Pflicht
        $lazygit = Get-ExecutablePath 'lazygit.exe'
        if (-not $lazygit) {
            Write-Host "Modus 'Tui' braucht lazygit (winget install JesseDuffield.lazygit)."
            Write-Host "Nichts gestartet."
            exit 0
        }
        foreach ($repository in $repositories) {
            $command = "& $((ConvertTo-PowerShellLiteral $lazygit))"
            Start-Process -FilePath $terminal -ArgumentList @(
                $windowArguments
                'new-tab'
                '--title'
                "Git - $($repository.Name)"
                '--startingDirectory'
                $repository.FullName
                'powershell.exe'
                '-NoExit'
                '-NoProfile'
                '-Command'
                $command
            ) | Out-Null
            $gestartet++
        }
    }

    'Gui' {
        $code = Get-ExecutablePath @('code.cmd', 'code.exe')
        if (-not $code) {
            Write-Host "Modus 'Gui' braucht VSCode (code). Nicht installiert."
            Write-Host "Alternativen: -Mode Terminal, oder die Repos-Zentrale nutzen."
            Write-Host "Nichts gestartet."
            exit 0
        }
        foreach ($repository in $repositories) {
            Start-Process -FilePath $code -ArgumentList @(
                '--new-window'
                $repository.FullName
            ) | Out-Null
            $gestartet++
        }
    }
}

"$gestartet von $($repositories.Count) Repository(s) im Modus '$Mode' gestartet."
if ($uebersprungen.Count -gt 0) {
    "Fehlende Werkzeuge: $($uebersprungen -join ', ')"
}
