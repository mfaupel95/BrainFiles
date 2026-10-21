---
name: skill-adaptive-agent-build-user-profile
description: Trockenlauf des Skills adaptive-agent:build-user-profile - baut aus bestehenden Vault-Notizen ein Nutzerprofil, speichert nichts.
metadata:
  type: reference
---

**Zweck:** Leitet aus Vault-Notizen ein Nutzerprofil für das Agenten-Gedächtnis ab (Rolle, Stärken, Arbeitsstil, Kommunikation, aktuelle Interessen).

**Wann nutzen:** Erster Start in einem leeren Arbeitsbereich ohne Profil, oder wenn das Profil veraltet ist. Im Vault selbst eher nicht: `Wissen/Profil.md` ist das Fundament und deckt diesen Zweck ab.

**Lauf:** 2026-10-21, trockenlauf, Aufgabe: aus `Wissen/Profil.md` und `Wissen/Benutzerprofil.md` ein kurzes Profil ableiten. Nichts geschrieben, nichts gespeichert, keine Git-Abfragen.

**Ergebnis:**
- Der Skill schreibt in das Agenten-Gedächtnis (Memory-Datei und Index), nicht in den Vault. Ein Trockenlauf kann deshalb nur lesen und vorschlagen.
- `Wissen/Profil.md` liefert bereits alle Abschnitte, die der Skill verlangt. Das Ergebnis wäre eine Dublette, die beim nächsten Update auseinanderläuft.
- `Benutzerprofil.md` gehört nicht zum Profil. Es beschreibt das Windows-Profil `C:\Users\faupe`. Ein Skill, der beide Dateien zusammenliest, mischt Nutzerdaten mit Systemdaten.
- Im Profil.md sind mehrere Angaben als `erschlossen` markiert, zum Beispiel Tischlerausbildung, Audio und Messebau. Der Skill würde sie als Fakten übernehmen. Die Quelle nennt aber selbst „bitte bestätigen oder streichen".

**Gelernt:**
- Der Skill ist für leere Arbeitsbereiche gebaut. Vor dem Lauf prüfen, ob es schon eine Profil-Quelle gibt. Im Vault ist das `Wissen/Profil.md`, und die gehört bevorzugt aktualisiert statt dupliziert.
- Die Obergrenze von 2 KB im Skill ist für diese Profil-Datei zu knapp. Die aktuelle Profil.md liegt darüber.
- Ein Trockenlauf eignet sich gut für Skills mit Schreibziel außerhalb von Werkstatt und Wissen. Er zeigt den Inhalt, ohne das Gedächtnis zu verändern.

**Grenzen:** Der Git-Schritt (Schritt 1a des Skills) wurde nicht ausgeführt. Die Git-Identität `mfaupel95` steht nur im Sitzungskontext, nicht als geprüfter Befund.
