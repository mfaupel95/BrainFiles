---
name: skill-maxhirn-umzug
description: Trockenlauf des Skills MaxHirn:umzug - Verfahren für Ordnerumzüge ohne stille Brüche; hier auf den Lernordner angewendet: Verweise in Index und Fortschritt gezählt, Suche in Skills und Notizen läuft noch.
metadata:
  type: reference
---

**Zweck:** Ein Ordner wird verschoben, ohne dass Pfade still brechen. Zuerst alle Stellen finden, die den alten Pfad tragen. Dann verschieben und alles in einem Zug nachziehen. Zuletzt eine Gegenprobe.

**Wann nutzen:** Bei Umzügen, bei Umbenennungen und wenn ein Programm nach einer Umstellung nichts mehr findet.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: Verweise auf `MaxHirn/Wissen/Skill-Lernen/` finden, die ein Umzug brechen würde. Keine Verweise geändert, nichts verschoben.

**Ergebnis:**

Gezählt (lesend, schnell):
- **Index `MaxHirn/Wissen/INDEX.md`:** 144 Zeilen verweisen auf `Skill-Lernen/`. Ein Umzug bricht diese Pfade vollständig.
- **Fortschritt `Werkstatt/Projekte/skill-lernen/fortschritt.md`:** 146 Zeilen nennen den Ordner. Der Fortschritt verweist mit Notiz-Pfad auf den Ordner.
- **Lernnotizen selbst:** Die Dateien tragen den Ordnernamen nicht im Frontmatter. Kein Eintrag in den Notizen bricht daher.

Noch nicht gezählt: Verweise in Skills (`.claude`, `Agenten`) und in anderen Notizen. Die Suche über den gesamten Vault lief zu lange und wurde in den Hintergrund gestellt. Das Ergebnis fehlt in diesem Lauf. Ob der Umzug die Routinen oder Skills bricht, ist daher nicht beantwortet.

Die Fallen aus dem Skill, auf den Lernordner übertragen:
- **Ein Programm rechnet seinen Ort aus:** Der Lern-Ablauf tut das nicht. Kein Quelltext berechnet den Pfad.
- **Die Fortschrittsdatei liegt außerhalb des Vault-Ordners:** Sie zeigt auf den Vault, aber ein Umzug des Vault-Ordners verschiebt sie nicht. Der Verweis wird dann ungültig, die Datei bleibt.
- **Git:** Der Ordner ist ungetrackt, ein Umzug erzeugt im Verlauf keine Umbenennung.

**Gelernt:** Die Verweise auf den Lernordner sind an drei Stellen gebunden: Index, Fortschritt und die Notizen selbst. Ein Umzug würde den Index und den Fortschritt brechen, nicht die Notizen. Die Reihenfolge ist deshalb: erst Index und Fortschritt anpassen, dann verschieben.

**Grenzen:** Die Suche in Skills und in den übrigen Notizen ist offen. Die Zahlen beziehen sich nur auf Index und Fortschritt.
