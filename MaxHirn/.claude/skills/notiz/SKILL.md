---
name: notiz
description: Legt dauerhaftes Wissen als Markdown-Notiz im Obsidian-Vault unter Wissen/ ab und verlinkt es. Benutzen, wenn Max sagt "merk dir das", "schreib das auf", "notier", "halt das fest", oder wenn im Gespräch etwas Dauerhaftes über ihn, ein Projekt oder eine Entscheidung herauskommt.
---

# Notiz im Vault anlegen

## Was hier hingehört — und was nicht

**Ja:** Dinge, die in einem Monat noch gelten. Entscheidungen und ihr Grund,
Zugangswege, Vorlieben, Projektstände, „so macht man das hier".

**Nein:** Zwischenstände eines einzelnen Laufs, Ausgaben von Befehlen, Dinge die
das Repository ohnehin dokumentiert, Kurzlebiges. Ein Vault, der mit Protokollen
volläuft, wird unbrauchbar.

Bei Unsicherheit einmal fragen: „Soll das dauerhaft in den Vault?"

## Wohin

Bevorzugt in eine **bestehende** Notiz unter `Wissen/`, statt eine neue anzulegen:

- Etwas über Max selbst → [[Profil]]
- Projektstand → [[Projekte]]
- Neuer Dienst angebunden → [[Verbindungen]]
- Neue Automatisierung → [[Routinen]]

Erst wenn nichts passt, eine neue Datei `Wissen/<Thema>.md` anlegen.

## Form

```markdown
# <Titel>

<Der Kern in ein bis drei Sätzen.>

**Warum:** <Grund — das ist der Teil, der später wirklich fehlt.>

**Stand:** 2026-08-08
```

Regeln:

- **Datum absolut schreiben**, nie „letzte Woche" oder „gestern".
- Mit `[[Dateiname]]` auf verwandte Notizen verlinken, auch wenn die Zielnotiz
  noch nicht existiert — das markiert eine Lücke, die sich lohnt.
- Deutsch, Stichpunkte reichen.
- Dateinamen ohne Umlaute und Leerzeichen (`Portabilitaet.md`), damit sie auch
  nach einem Umzug auf ein anderes Dateisystem stabil bleiben.

## Danach

Prüfen, ob die Notiz vom [[Dashboard]] oder einer Elternnotiz aus erreichbar ist.
Eine Notiz, auf die nichts verlinkt, wird nie wieder gelesen.
