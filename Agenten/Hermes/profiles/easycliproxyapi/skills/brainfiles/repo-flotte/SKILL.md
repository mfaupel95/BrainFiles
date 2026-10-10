---
name: repo-flotte
description: "Use when Repos wiederherstellen, klonen und Bots je Repo."
category: brainfiles
---

# Repo-Flotte: Fremd-Repos einrichten und je Repo ein Bot

Fuer Arbeiten am Bestand aus Fremd-Repos: geloeschte Repos wieder auf den Account
bringen, lokal als arbeitsfaehige Klone einrichten und je Repo einen Hermes-Bot
(Profil) als Betreuer anlegen. Laeuft auf dem Host ueber `windows-mcp`; `gh` ist
dort angemeldet.

## Ablauf

1. **Soll-Liste gegen die Wirklichkeit halten.** Namen aus einem Screenshot, einer
   Notiz oder dem Gedaechtnis sind eine **Hypothese**. Je Name belegen: das
   Upstream-Repo existiert (`gh api repos/<owner>/<repo>`), oder der lokale Klon
   nennt ihn selbst (`Get-Content <dir>\.git\config` → `url =`). Ein Name, der
   nirgends aufloest, wird berichtet - nicht erfunden und nicht stillschweigend
   weggelassen. *Fertig, wenn* jeder Name eine belegte Quelle hat.
   - Der Bild-Backend holt keinen Dateipfad; liegt ein Screenshot nur als Datei
     vor, den Text lokal auslesen: `tesseract` (bei Bedarf
     `apt-get install -y --no-install-recommends tesseract-ocr`), Bild vorher mit
     ImageMagick auf 300-500 % vergroessern, `--psm 6` und `--psm 11`
     gegeneinander halten. Die so gewonnenen Namen bleiben Hypothese (Schritt 1).
2. **Wiederherstellen als Fork des Originals.** Fuer oeffentliche Upstreams ist
   Re-Fork verlustfrei, solange im geloeschten Repo keine eigene Arbeit lag - das
   prueft man an den lokalen Klonen: zeigen deren `origin`-URLs auf die Upstreams,
   gab es kein Unikat. `gh api -X POST "repos/<upstream>/forks"`. Forks entstehen
   asynchron: in einer Schleife `gh api "repos/<konto>/<name>"` abfragen, bis der
   Name aufloest. Oeffentliche Upstreams ergeben oeffentliche Forks - private
   Forks von oeffentlichen Repos sind ohne Freigabe des Upstreams nicht moeglich.
3. **Bestand zaehlen, nicht Einzeltreffer feiern.** `gh api
   'user/repos?per_page=100&affiliation=owner' --jq '[.[] | select(.fork==true)
   | .full_name] | sort'` zaehlt **alle** Forks des Kontos, also auch die schon
   vorhandenen. Die Zahl gegen Erwartung **plus** Altbestand halten.
4. **Lokal arbeitsfaehig machen.** Ein Verzeichnis je Repo unter
   `Werkstatt/Repos/` (Fremd-Repos sind Durchgangsware, nie im Vault):
   `git clone --quiet --depth 1 https://github.com/<konto>/<name>.git <dir>`,
   danach `git -C <dir> remote add upstream https://github.com/<upstream>.git`.
   Shallow genuegt fuer Bot-Arbeitsplaetze; `git fetch --unshallow` holt die volle
   Historie nach. Liegt am Zielort schon ein Verzeichnis ohne `.git` (eine
   entpackte Kopie), es nach `<name>.vorher` verschieben statt hineinzuklonen.
5. **Ein Bot je Repo.** Bots sind Hermes-Profile:
   `hermes.exe profile create <name> --clone --description "<Rolle, 1-2 Saetze>"`
   und danach `hermes.exe -p <name> config set terminal.cwd <repo-pfad>`. `--clone`
   uebernimmt Modell, Werkzeuge und Skills des Startprofils, `--description`
   landet in `profile.yaml` und wird vom Kanban-Orchestrator zum Sortieren benutzt.
   *Fertig, wenn* `hermes profile list` jeden Bot fuehrt.

## Nachweis

- `gh api "repos/<konto>/<name>" --jq '.full_name + " fork=" + (.fork|tostring)'`
  je Repo.
- `git -C <dir> remote -v` je Klon: `origin` = Fork, `upstream` = Original.
- `hermes profile list` fuehrt jeden Bot, `hermes profile describe <bot>` zeigt
  die gesetzte Rolle.

## Fallen

- **`hermes.exe` aus einer MCP-Brueckensitzung** braucht davor
  `Remove-Item Env:PYTHONHOME, Env:PYTHONPATH` und ein gesetztes
  `$env:HERMES_HOME`, sonst bricht es mit einem falschen „corrupt
  Python"-Fehler ab; Einzelheiten in `hermes-maintenance`.
- **Profilnamen werden klein geschrieben.** `profile create Scrapling` legt
  `scrapling` an; danach nur noch den kleinen Namen verwenden. Ein erneuter
  `create`-Aufruf auf ein vorhandenes Profil meldet einen Fehler, aendert aber
  nichts - Beschreibung und `terminal.cwd` gehoeren in eigene Aufrufe, dann laeuft
  der ganze Satz idempotent.
- **`--clone` kopiert die ganze Skill-Bibliothek ins Profil.** Bei vielen Bots
  kostet das Plattenplatz und, sobald der Bot laeuft, die gleichen Tokens wie das
  Startprofil; ein Bot je Repo braucht nur einen Bruchteil davon.
- **Kein Symlink und kein Import aus Fremd-Repos.** Siehe `skill-library-sync`
  und `fundus-zugriff`.
- **Hilfsskripte gehoeren nicht nach `Agenten/Routinen/`.** Dort gilt jede `.ps1`
  als Routine und muss am Bus haengen, sonst reisst `tests/test_ende_zu_ende.py`
  mit „ohne Bus-Anbindung". Werkzeuge nach `Agenten/Werkzeuge/`.

## Abgrenzung

- Host-Zugriff, PowerShell-Fallen, gezielter Dateiersatz: `windows-host-zugriff`
- Hermes-Installation reparieren (venv, PYTHONHOME, SQLite): `hermes-maintenance`
- Skill-Ablagen abgleichen und Fundus nutzen: `skill-library-sync`, `fundus-zugriff`
