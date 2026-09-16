# Hermes-Edge / browser-profile: Dateisperren gegen Sicherungslaeufe

Ausloeser: "Zweitkopie Exit 1", "FEHLER 32 (0x00000020) Zugriff verweigert"
im Kopier-Protokoll, oder ein Sicherungslauf, der ohne Ende-Zeile abbricht.

## Woran man arbeitet

-`browser-profile/`liegt unter`Agenten/Hermes/`und enthaelt das
 **eigene Headless-Edge-Profil** von Hermes (user-data-dir=
 `browser-profile\edge`). Es laeuft rund um die Uhr: der Browser wird von
 `explorer.exe` gestartet und haelt **Cookies, Sessions, localStorage**
 gesperrt.
- Die Sicherungs-Wrapper sind`Agenten/Routinen/sicherung.ps1`(20:00,
 G:) und`Agenten/Routinen/zweitkopie.ps1`(21:00, J:) und rufen die zentralen
 Kopier-Skripte`Agenten/sichern.ps1`und`Agenten/sichern-zweitkopie.ps1`
 auf. Alle vier muessen beim Thema zusammen gelesen werden.

## Befund 16.09.2026 (gemessen, nicht geraten)

-`MaxHirn-Zweitkopie`brach mit Exit 1 nach 62 s ab, Portokoll
 `FEHLER 32 (0x00000020) Der Prozess kann nicht auf die Datei zugreifen`
 auf `browser-profile\edge\Default\Network\Cookies`, `-journal`,
 `Sessions\Session_*` und `Tabs_*`; robocopy mit`/R:1 /W:1`gibt nach
 EINER Wiederholung auf (Exit-Code 20/21, Task-Ergebnis`0x40010004`).
- Die msedge-Prozesse liefen: `--headless=new --user-data-dir=...browser-profile\edge`
 mit Elternprozess `explorer.exe` (nicht irgendein Skript). Diese
 Prozesse sind rund um die Uhr aktiv und waren die Sperre.
- Es war NICHT der normale Edge-Browser von Max (der laeuft unter
 `%LOCALAPPDATA%\Microsoft\Edge\User Data` und war beim Lauf geschlossen).

## Fix (anschaulich)

- `browser-profile`in BEIDEN zentralen Kopier-Skripten als`/XD`aufgefuehrt
 (`Agenten/sichern.ps1`und`Agenten/sichern-zweitkopie.ps1`neben
 `shared_metrics`). Die Browser-Session ist fluessiges Wegwerfmaterial
 (Cookies, Tabs); Zugangsdaten stecken ohnehin in den Profil-`.env`
 (`profiles/<name>/.env`), nicht im Browser-Profil.
- `.bak-JJJJMMTT`-Sicherung der zwei Skripte vor der Aenderung.
- Nachweis des Fixes (23:01, echter Lauf): `browser-profile`stand in der
 robocopy-Ausschlussliste, **0 FEHLER 32**, 112.688 Dateien / 69,9 GB
 kopiert, robocopy-Code 3 („erfolgreich, Extras"), `ENDE nach 46 s`.

## Fallen

1. **Die Sperre ist eine laufende Instanz, kein Einmalereignis.**
   `--headless=new` + Explorer als Eltern = startet bei jedem Rechner-Start
   wieder; der Ausschluss ist Dauerzustand, kein Workaround.
2. **robocopy /R:1 /W:1 meldet Dateisperren als Code 20/21** und der Wrapper
   als „ENDE FEHLER" — eine gesperrte Browserdatei ist KEIN Kopierfehler
   des Skripts.
3. **Nicht dein Edge-Profil fassen.** Der Ausschluss bezieht sich nur auf
   `Agenten\Hermes\browser-profile\`; das normale Edge-Profil
   (`%LOCALAPPDATA%\Edge`) bleibt unberuehrt.
4. **Sicherungslaeufe ohne Ende-Zeile sind Rechner-Neustarts.** `0xC000013A`
   (STATUS_CONTROL_C_EXIT) im Task-Ergebnis = der Prozess wurde von aussen
   beendet — Event 1074 (Neustart) im Systemlog bestaetigen, KEIN Skript-Fix.
