---
name: skill-maxhirn-dokument
description: Trockenlauf des Skills MaxHirn:dokument - erschließt ein einzelnes Dokument (vollständig lesen, sechs Fragen, Benennung, Ablage, Verankerung); hier auf eine Lernnotiz angewendet, nichts abgelegt.
metadata:
  type: reference
---

**Zweck:** Erschließt ein einzelnes wichtiges Dokument so, dass Max es in zwei Jahren wiederfindet und weiß, was darin steht, ohne es zu öffnen. Das Original wird nie verändert.

**Wann nutzen:** Bei einem einzelnen Schreiben oder Dokument, das zählt. Für Stapel `posteingang`, für Suchen `archiv`.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: beschreiben, wie eine Lernnotiz aus `MaxHirn/Wissen/Skill-Lernen/` erschlossen würde. Nichts abgelegt, nichts verschoben, nichts indexiert.

**Ergebnis:**

Der Skill ist für Papierdokumente gebaut: Scans, Bescheide, Verträge. Eine Lernnotiz ist ein Markdown-Text im Vault, kein Archivstück. Daher ändert sich der Ablauf:

1. **Vollständig lesen:** Die Notiz ist kurz und liegt als Text vor. Keine OCR nötig.
2. **Sechs Fragen:**
   - Wer schreibt? Die Sitzung, die den Trockenlauf gemacht hat, nicht ein Mensch. Die Rolle `Claude` oder `Hermes` ist angebbar, ein Name nicht.
   - Wann? Das Datum des Laufs steht in der Notiz (`**Lauf:**`).
   - Worum? Ein Satz aus dem Feld `description` im Frontmatter.
   - Beträge? Keine.
   - Zustandsänderung? Nein, eine Lernnotiz ändert keinen Zustand außer dem Fortschritt.
   - Frist? Keine.
3. **Benennung:** Das Schema `<Datum>_<Was>_<Wer>.pdf` passt nicht. Die Notiz trägt bereits den Namen `skill-<name>.md` nach der Regel aus `skill-lernen`. Eine zweite Benennung wäre eine Dublette.
4. **Ablage:** Nicht im Archiv. Lernnotizen liegen bereits im Vault unter `Wissen/Skill-Lernen/`.
5. **Verankerung:** Die Notiz selbst ist die Verankerung. Eine zusätzliche Notiz wäre überflüssig.

Der Skill sagt „im Zweifel in eine bestehende Notiz ergänzen“. Für Lernnotizen trifft das zu: Jede hat genau einen Skill.

**Gelernt:** Der Skill setzt ein Papierdokument voraus. Für Vault-Dokumente sind die Schritte 3 und 4 überflüssig. Ein Lauf auf einer Lernnotiz zeigt, dass der Skill nicht für jede Art Dokument passt.

**Grenzen:** Trockenlauf an einer Notiz, nicht an einem echten Schreiben. Die Regel „Beträge wörtlich“ ist hier nicht geprüft, weil keine Beträge vorkommen.
