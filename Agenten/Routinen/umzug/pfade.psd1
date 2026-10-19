#
# Die eine Tabelle alt -> neu. Jedes Umzugsskript liest sie, keins raet.
# Alle Pfade sind relativ zur Wurzel 'BrainFiles'.
#
@{
    # Phase 2 -- Modelle heraus und geradeziehen.
    # Reihenfolge zaehlt: erst der grosse Move, dann das Sortieren darin.
    Modelle = @(
        @{ Von = 'MaxHirn\Modelle'          ; Nach = 'Modelle' }
        @{ Von = 'MaxHirn\Daten'            ; Nach = 'Modelle\Daten' }
        @{ Von = 'Modelle\blobs'            ; Nach = 'Modelle\Ollama\Store\blobs' }
        @{ Von = 'Modelle\manifests'        ; Nach = 'Modelle\Ollama\Store\manifests' }
        @{ Von = 'Modelle\Ollama\app.ico'   ; Nach = 'Modelle\Programme\Ollama\app.ico' }
        @{ Von = 'Modelle\Ollama\lib'       ; Nach = 'Modelle\Programme\Ollama\lib' }
        @{ Von = 'Modelle\Ollama\ollama.exe'; Nach = 'Modelle\Programme\Ollama\ollama.exe' }
        @{ Von = 'Modelle\Ollama\ollama app.exe' ; Nach = 'Modelle\Programme\Ollama\ollama app.exe' }
        @{ Von = 'Modelle\Ollama\unins000.dat'   ; Nach = 'Modelle\Programme\Ollama\unins000.dat' }
        @{ Von = 'Modelle\Ollama\unins000.exe'   ; Nach = 'Modelle\Programme\Ollama\unins000.exe' }
        @{ Von = 'Modelle\Ollama\unins000.msg'   ; Nach = 'Modelle\Programme\Ollama\unins000.msg' }
    )

    # Leere Altlasten in Modelle/. 'Manifeste' war die deutsche Dublette von
    # 'manifests' und hat nie etwas enthalten.
    ModelleLeer = @('Modelle\Manifeste')

    # Die Ordner, die nach dem Umbau die neuen Heimaten sind.
    ModelleNeu = @('Modelle\HuggingFace', 'Modelle\GGUF', 'Modelle\Checkpoints')

    # Ollama erwartet in OLLAMA_MODELS einen Ordner, der 'blobs' und 'manifests'
    # nebeneinander enthaelt -- nicht deren Elternordner, nicht 'models'.
    OllamaStore = 'Modelle\Ollama\Store'

    # Phase 3 -- Agenten. Routinen steht bewusst am Ende: darin laeuft das
    # Skript, das gerade verschiebt.
    Agenten = @(
        @{ Von = 'MaxHirn\MCP-Server'              ; Nach = 'Agenten\MCP-Server' }
        @{ Von = 'MaxHirn\Hermes'                  ; Nach = 'Agenten\Hermes' }
        @{ Von = 'MaxHirn\Handel'                  ; Nach = 'Agenten\Handel' }
        @{ Von = 'MaxHirn\sichern.ps1'             ; Nach = 'Agenten\sichern.ps1' }
        @{ Von = 'MaxHirn\sichern-zweitkopie.ps1'  ; Nach = 'Agenten\sichern-zweitkopie.ps1' }
        @{ Von = 'MaxHirn\sichern-ausser-haus.ps1' ; Nach = 'Agenten\sichern-ausser-haus.ps1' }
        @{ Von = 'MaxHirn\Routinen'                ; Nach = 'Agenten\Routinen' }
    )

    # Phase 4 -- Werkstatt.
    Werkstatt = @(
        @{ Von = 'MaxHirn\GitHub'          ; Nach = 'Werkstatt' }
        @{ Von = 'MaxHirn\Coworking-Space' ; Nach = 'Werkstatt\Sitzungen' }
        @{ Von = 'MaxHirn\Codex'           ; Nach = 'Werkstatt\Protokolle\Codex' }
        @{ Von = 'MaxHirn\Claude\Worktrees'; Nach = 'Werkstatt\Worktrees' }
        @{ Von = 'MaxHirn\phase1-git-stabilization.ps1' ; Nach = 'Werkstatt\Protokolle\phase1-git-stabilization.ps1' }
    )
    WerkstattNeu = @('Werkstatt\Austausch', 'Werkstatt\Projekte', 'Werkstatt\Ausgabe')

    # Phase 5 -- Umbenennung des Archivs.
    ArchivVon  = 'MaxHirn\Claude'
    ArchivNach = 'MaxHirn\Archiv'

    # Konfigurationsdateien mit absoluten Pfaden. Beide muessen gemeinsam
    # geaendert werden, sonst laufen Claude und Hermes auseinander.
    Konfigurationen = @(
        '%APPDATA%\Claude\claude_desktop_config.json'
        'Agenten\Hermes\config.yaml'
    )

    # Prozesse, die vor dem Umzug beendet sein muessen.
    Prozesse = @('Claude', 'claude', 'ollama', 'ollama app', 'codex', 'hermes', 'Obsidian')
}
