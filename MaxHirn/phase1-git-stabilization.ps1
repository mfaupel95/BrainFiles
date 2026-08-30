# phase1-git-stabilization.ps1

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " PHASE 1 - GIT STABILIZATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Git-Verfügbarkeit prüfen

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
throw "Git wurde nicht gefunden. Bitte Git installieren oder PATH pruefen."
}

# Git-Repository prüfen

$IsGitRepo = git rev-parse --is-inside-work-tree 2>$null

if ($IsGitRepo -ne "true") {
throw "Der aktuelle Ordner ist kein Git-Repository."
}

# Repository-Root bestimmen

$RepoRoot = git rev-parse --show-toplevel
Set-Location $RepoRoot

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$AuditDir = Join-Path $RepoRoot "docs\audit"

if (-not (Test-Path $AuditDir)) {
New-Item -ItemType Directory -Path $AuditDir -Force | Out-Null
}

$AuditFile = Join-Path $AuditDir "git-baseline-$Timestamp.txt"

$CurrentBranch = git branch --show-current

Write-Host "Repository: $RepoRoot" -ForegroundColor Yellow
Write-Host "Branch: $CurrentBranch" -ForegroundColor Yellow
Write-Host ""

# ========================================

# PHASE 1A - AUDIT

# ========================================

Write-Host "Starte Git-Audit..." -ForegroundColor Cyan

"========================================" | Out-File $AuditFile -Encoding utf8
"GIT BASELINE AUDIT" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8
"" | Out-File $AuditFile -Append -Encoding utf8
"Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $AuditFile -Append -Encoding utf8
"Repository: $RepoRoot" | Out-File $AuditFile -Append -Encoding utf8
"Branch: $CurrentBranch" | Out-File $AuditFile -Append -Encoding utf8
"" | Out-File $AuditFile -Append -Encoding utf8

"========================================" | Out-File $AuditFile -Append -Encoding utf8
"GIT STATUS" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8

git status 2>&1 | Tee-Object -FilePath $AuditFile -Append

"" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8
"UNSTAGED DIFF STATISTICS" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8

git diff --stat 2>&1 | Tee-Object -FilePath $AuditFile -Append

"" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8
"STAGED DIFF STATISTICS" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8

git diff --cached --stat 2>&1 | Tee-Object -FilePath $AuditFile -Append

"" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8
"RECENT COMMITS" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8

git log --oneline -10 2>&1 | Tee-Object -FilePath $AuditFile -Append

"" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8
"REMOTE CONFIGURATION" | Out-File $AuditFile -Append -Encoding utf8
"========================================" | Out-File $AuditFile -Append -Encoding utf8

git remote -v 2>&1 | Tee-Object -FilePath $AuditFile -Append

Write-Host ""
Write-Host "Audit abgeschlossen." -ForegroundColor Green
Write-Host "Audit-Datei: $AuditFile" -ForegroundColor Yellow
Write-Host ""

# ========================================

# PHASE 1B - STATUS PRUEFEN

# ========================================

Write-Host "Pruefe auf Aenderungen..." -ForegroundColor Cyan

$Status = git status --porcelain

if ([string]::IsNullOrWhiteSpace($Status)) {

```
Write-Host ""
Write-Host "Working Tree ist bereits sauber." -ForegroundColor Green
Write-Host "Kein Feature-Commit erforderlich." -ForegroundColor Yellow
```

}
else {

```
Write-Host ""
Write-Host "Aenderungen erkannt:" -ForegroundColor Yellow
Write-Host $Status
Write-Host ""

# ========================================
# PHASE 1C - STAGE
# ========================================

Write-Host "Stage alle Aenderungen..." -ForegroundColor Cyan

git add -A

Write-Host ""
Write-Host "Staged Changes:" -ForegroundColor Yellow

git diff --cached --stat

# ========================================
# PHASE 1D - COMMIT
# ========================================

$CommitMessage = "feat: implement token-efficient context handling"

Write-Host ""
Write-Host "Erstelle Feature-Commit..." -ForegroundColor Cyan
Write-Host $CommitMessage -ForegroundColor Yellow

git commit -m $CommitMessage

Write-Host ""
Write-Host "Feature-Commit erfolgreich erstellt." -ForegroundColor Green
```

}

# ========================================

# PHASE 1E - BASELINE TAG

# ========================================

$TagName = "v0-context-baseline"

Write-Host ""
Write-Host "Pruefe Baseline-Tag..." -ForegroundColor Cyan

$ExistingTag = git tag -l $TagName

if ([string]::IsNullOrWhiteSpace($ExistingTag)) {

```
Write-Host "Erstelle Baseline-Tag: $TagName" -ForegroundColor Cyan

git tag -a $TagName -m "Baseline before modular RAG context architecture"

Write-Host "Baseline-Tag erfolgreich erstellt." -ForegroundColor Green
```

}
else {

```
Write-Host "Tag '$TagName' existiert bereits." -ForegroundColor Yellow
Write-Host "Kein bestehender Tag wird ueberschrieben." -ForegroundColor Yellow
```

}

# ========================================

# PHASE 1F - FINAL VERIFICATION

# ========================================

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " FINAL VERIFICATION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Git Status:" -ForegroundColor Yellow
git status

Write-Host ""
Write-Host "Letzte Commits:" -ForegroundColor Yellow
git log --oneline -5

Write-Host ""
Write-Host "Tags:" -ForegroundColor Yellow
git tag --sort=-creatordate | Select-Object -First 10

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " PHASE 1 SUCCESSFULLY COMPLETED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Baseline Commit:" -ForegroundColor Yellow
git rev-parse HEAD

Write-Host ""
Write-Host "Baseline Tag:" -ForegroundColor Yellow
git rev-list -n 1 $TagName

Write-Host ""
Write-Host "Audit Report:" -ForegroundColor Yellow
Write-Host $AuditFile -ForegroundColor Cyan
