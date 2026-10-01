# Einem Profil eine Modell-Anmeldung geben (Symlink, nicht Kopie)

Ausloeser: "/bot NAME antwortet nicht", `hermes -p NAME chat -q ...` endet mit
"Hermes is not logged into Nous Portal". Ein Profil ohne eigene `auth.json`
liest NIE die des Root-Homes (`profile_credential_audit.py`); `NOUS_API_KEY` in
der Benutzerumgebung genuegt NICHT - der Gate verlangt den Provider-State in der
`auth.json` des Profils.

Richtig ist ein **Symlink** auf den Root-Store, nicht eine Kopie:
`Agenten/Hermes/scripts/auth-verknuepfen.ps1` (Trockenlauf ohne Argument,
`-Anwenden`, `-Zuruecknehmen`). Der Grund gegen die Kopie: eine device_code-
OAuth-Sitzung enthaelt einen Refresh-Token; als Kopie in vielen Profilen
entwertet die erste Rotation alle anderen ("Refresh session has been revoked").
Ein Symlink haelt EINEN Store, und genau dafuer hat Hermes die Sperre und die
"Peer hat rotiert, uebernimm seinen Token"-Logik
(`hermes_cli/auth.py::_nous_shared_store_lock`); `auth_oauth_grants.py` behandelt
einen Symlink auf den Root-Store ausdruecklich als "kein Klon" und laesst ihn
stehen. **Symlinks: erst den direkten Versuch, dann die Leiter.** Ein Symlink braucht nicht
per se Erhoehung: ein schlichtes
`New-Item -ItemType SymbolicLink -Path <ziel> -Target <root>` ist hier mehrfach OHNE
Admin durchgelaufen (Developer-Mode AN, `AllowDevelopmentWithoutDevLicense=1`),
waehrend derselbe Aufruf in einer anderen Sitzung mit
`NewItemSymbolicLinkElevationRequired` („Fuer diesen Vorgang sind
Administratorrechte erforderlich") abbrach — die Anforderung haengt also am Kontext,
nicht am Befehl. Reihenfolge, die keinen UAC-Klick kostet: (1) `New-Item
-ItemType SymbolicLink` direkt; (2) falls es verweigert, `pwsh` 7
(`C:\Program Files\PowerShell\7\pwsh.exe`)
`-NoProfile -Command "New-Item -ItemType SymbolicLink -Path <ziel> -Target <root>"`;
(3) erst dann das Hausskript erhoeht (UAC, `auth-verknuepfen.ps1` braucht `-Anwenden`,
ein Aufruf ohne den Schalter ist ein TROCKENLAUF und legt nichts an). Danach mit
`os.path.islink()` gegenpruefen, nicht mit `os.path.exists()`.
**Die Leiter NICHT ueberspringen — und den UAC-Weg nie aus einer Nachtsitzung.**
Das Hausskript direkt nicht-erhoeht aufzurufen liefert nur
`Administratorrechte erforderlich` (erwartet, kein Befund), und der naechste Griff
nach `Start-Process -Verb RunAs ... -Wait` ist der teure Fehler: ohne Nutzer am
Geraet bleibt der Prompt unbeantwortet, das `-Wait` laeuft ins Zeitlimit und der
Schritt bleibt offen, obwohl Stufe (1) oder (2) ihn in Sekunden erledigt haette.
Erhoehte Schritte gehoeren in den Bericht als offener Punkt fuer den Nutzer, nicht
in einen Warteversuch. **Ein Symlink ist keine
Kopie** — die Begruendung oben gilt unveraendert; wo schon eine eigene `auth.json`
liegt, nicht ueberschreiben. Fuer EIN
Profil ist das der kuerzere Weg als das Skript samt UAC-Prompt. **`-PassThru` und
`-RedirectStandardOutput` vertragen sich in PowerShell 5.1 NICHT mit `-Verb
RunAs`** (AmbiguousParameterSet); das innere Skript schreibt sein Ergebnis
selbst per `Start-Transcript` in eine Logdatei.

**`hermes auth` ist NICHT profilbewusst — es zeigt immer den Wurzel-Pool.**
`hermes auth` (ohne Unterkommando) ist ein interaktives Menue und laeuft ohne
Terminal in den Pool-Status; `hermes auth list` und `auth status <provider>`
liefern fuer `default` und fuer jedes `-p <profil>` die IDENTISCHE Ausgabe (am
30.09.2026 Zeile fuer Zeile verglichen). Wer daraus schliesst, ein Profil sei
angemeldet, prueft in Wahrheit den Root-Store: die eigene `profiles/<p>/auth.json`
(z. B. 713 B, nur `openrouter`) sieht man dort nicht. Was ein Profil WIRKLICH
nutzt, belegt nur ein echter Aufruf plus `session_model_usage` in
`profiles/<p>/state.db` (Spalten `model`, `billing_provider`, `billing_base_url`)
— nicht die Pool-Anzeige.

Fallen: Ein Profil mit eigener `auth.json` bleibt unberuehrt (die Datei NICHT
ueberschreiben). Enthaelt sie nur einen Pool-Eintrag ohne `providers.nous`,
nutzt sie nichts - vorher sichern und dann ebenfalls verknuepfen. Ein
`api_key`-Provider (llamacpp, docker) braucht keine Sitzung.

Beleg: `hermes -p NAME chat -q "Antworte nur mit dem einen Wort: fertig" -Q -t
memory` je Muster (verknuepft, eigene Sitzung, Sonderfall) - und danach das
Hauptprofil einmal aufrufen: bleibt SEINE Sitzung intakt, ist die gemeinsame
Nutzung bewiesen.
