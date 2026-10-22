---
name: skill-maxhirn-auftrag
description: Trockenlauf des Skills MaxHirn:auftrag - deutet knappe Eingaben wie "mach weiter" aus dem Verlauf und wählt den Weg; hier auf die Frage angewendet, was "mach weiter" im Lern-Ablauf bedeutet.
metadata:
  type: reference
---

**Zweck:** Liest aus einer knappen Eingabe das Ziel heraus und wählt den Weg. Das erkannte Ziel bestimmt das Werkzeug und die Reihenfolge, nicht den Umfang der Arbeit. Bei unklarem Verweis wird aufgelöst, nicht nachgefragt, solange der Verlauf eine Liste hat.

**Wann nutzen:** Bei kurzen Eingaben wie "3", "weiter", "ja" oder "mach mal", deren Zweck klarer ist als ihr Wortlaut.

**Lauf:** 2026-10-22, trockenlauf, Aufgabe: bewerten, wie "mach weiter" im Lern-Ablauf zu lesen ist. Nichts geändert.

**Ergebnis:**

Die Eingabe "mach weiter" hat im Verlauf drei mögliche Bedeutungen:
1. **Nächster Skill** derselben Gruppe.
2. **Nächste Gruppe**, wenn die laufende Gruppe fertig ist.
3. **Abschluss**, wenn der Auftrag ausdrücklich erledigt war.

Lesart, die ich wählen würde: **nächster Skill derselben Gruppe**. Das stimmt mit der letzten Ansage überein, dass der nächste offene Kandidat laufen soll. Eine Gruppe wechselt erst, wenn die Gruppe leer ist, und dann nur mit einer Zeile, nicht stillschweigend.

Die Regel "Ein Skill pro Aufruf" in `skill-lernen` steht dagegen: "mach weiter" bedeutet also genau einen Skill, außer der Auftrag verlangt ausdrücklich mehrere.

Nicht zu tun: Gruppe wechseln oder mehrere Skills auf einmal, ohne dass das gesagt wurde. Das wäre Umfangserweiterung, nicht Zielerkennung.

**Gelernt:** Eine knappe Eingabe braucht den Verlauf, um eindeutig zu sein. Der Verlauf dieses Laufs enthält genügend Hinweise, um die Lesart festzulegen. Ein Skill, der bei jeder Eingabe fragt, bremst den Lauf unnötig.

**Grenzen:** Der Verlauf ist hier nicht vollständig im Kontext. Die Lesart ist eine Vermutung, die beim nächsten Aufruf zu überprüfen ist.
