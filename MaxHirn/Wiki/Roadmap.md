---
id: 20260922-roadmap
title: 'Roadmap — smartes, personalisiertes System'
tags: [betrieb]
created: 2026-09-22
updated: 2026-09-22
related: ['[[INDEX]]', '[[Offen/Entscheidungen]]', '[[Wissen/Routinen]]', '[[Wissen/Profil]]']
summary: 'Zielkarte des KI-Betriebssystems: was gemessen fehlt, was automatisiert, was personalisiert wird — priorisiert nach Wirkung.'
---

# Roadmap

Ziel von Max: ein **vollständig smart agierendes KI-System, auf ihn personalisiert**.
Diese Seite ist die Zielkarte dazu — keine Wunschliste, sondern die gemessenen
Lücken, sortiert nach Wirkung. Erstellt 22.09.2026 aus einem Vollscan; die Zahlen
stammen aus den unten genannten Dateien.

## Grundbefund: das System funktioniert schon

Der Vollscan zeigt **kein rohes System, sondern eines, das läuft**:

- ~30 geplante Abläufe ([[Wissen/Routinen]]), alle verdrahtet — Windows-Aufgabenplanung,
  Hermes-Cron, Bus. 27 Cron-Jobs, alle `no_agent`, still bei Erfolg.
- 31+ Handelsspuren im Dauerlauf, Papier und ein paar live, alle mit `wachen.json`
  (einzige Wahrheit) und Spiegelung nach `Q:`.
- 18+ Repo-Bots als Hermes-Profile, auf `nous`/`deepseek-v4-flash`, per `/bot` erreichbar.
- Wiki (17 Seiten) und `Wissen/` (vollständiger Index) trennen sauber „Arbeiten" von „Max".

**Deshalb ist „smarter machen" hier nicht neu bauen, sondern die gemessenen Lücken
schließen.** Ein System, das funktioniert, wird nicht durch mehr Teile besser, sondern
durch weniger unbemerkte Fehler (Zuverlässigkeit), weniger Token-Last (Schlankheit)
und mehr genutzten Kontext (Personalisierung).

## Die vier Hebel, nach Wirkung

### 1. Zuverlässigkeit — unbemerkte Fehler schließen (höchste Wirkung)

Das sind die Punkte, bei denen das System *leise* falsch läuft. Details und Stand in
[[Offen/Entscheidungen]].

| # | Lücke | Wirkung, wenn behoben |
|---|---|---|
| 1.1 | **Bedingung 4 hinkt hinterher** — ein Zykluspfad steigt zwischen Schreiben und Spiegeln früh aus; `Q:` lief 24 min nach. | Außer-Haus-Kopie stimmt wieder immer; kein stiller Datenverlust. |
| 1.2 | **xperp-Key liefert 50101** — kein Orderweg, kein Dateischalter löst das. | Nur echte Spur, die live *handeln* kann statt nur vorlegen. |
| 1.3 | **Außer-Haus-Kopie unverschlüsselt** — Klartext-Zugangsdaten auf einer SSD, die das Haus verlässt. | Der einzige Schutz gegen den Netzteilschaden 2026 (alle Platten gleichzeitig) wird tragbar. |
| 1.4 | **T-004 Abschaltungen** — Kernel-Power 41, Ursache offen (Kabel/Steckdose/Lastspitzen). | Jeder Langlauf bleibt davon bedroht; erst hier gelöst, ist echter Dauerbetrieb sicher. |

Merksatz: **1.1 und 1.2 blockieren „smart" nicht, aber sie sind die Stellen, an denen
das System ohne Alarm falsch liegt.** 1.3 und 1.4 sind die Stellen, an denen alles andere
hinfällig wird, wenn sie zuschlagen.

### 2. Schlankheit — Token- und Plattenlast senken

Gemessen: `Agenten/Hermes/skills/` ist 2,4 GB, davon ~1,8 GB unversionierte Fremd-Klone
ohne SKILL.md (jeder neu klonbar). Die **geladene** Bibliothek ist schon getrimmt
(331 → 90 Skills, ~3.050 Token je Anfrage). Weiterer Hebel nur beim Fremd-Ballast:
löschen oder bewusst behalten — reine Plattenfrage, keine Token-Frage. C: ist bei 61 GB
frei (Stand 22.09.2026), nicht mehr kritisch; `uv cache clean` bleibt ein reproduzierbarer
Knopf, wenn es knapp wird.

### 3. Personalisierung — der Kontext ist da, er muss nur genutzt werden

`Wissen/Profil` und das User-Profil tragen bereits, wie Max arbeitet: Ergebnis zuerst,
keine Optionslisten, eine begründete Empfehlung, kurze Steuerbefehle, „Ja" = vollständig
ausführen. Der Scan zeigt **keine Lücke** in der Personalisierung selbst — sie hängt an
Disziplin, nicht an Daten. Der einzige echte Ausbau ist Pflege: das Wiki bei jeder Lehre
füllen (`wiki-pflege`), statt Wissen nur im Sitzungsverlauf zu lassen.

### 4. Autonomie — Loops und Routinen

Der Betrieb hat schon die volle Meldekette (Bus) plus 27 stille Wachen. Neue Loops sind
**nur sinnvoll, wo die 5-Fragen-Schwelle** (Skill `skill-schleifen`) **besteht**: Wiederkehr
belegt, Prüfkriterium in einer Zeile, stiller Erfolg, entscheidungsarm, rein lesend.
Nach dem Scan besteht sie für **keine** neue Schleife — jede denkbare (Spiegel-Frist,
stille Spuren, Automatik-Wache, junge Spuren) existiert bereits. Konsolidieren statt
vermehren ist hier der richtige Schritt.

## Priorisierte Reihenfolge

1. **1.1** Bedingung 4: Spiegelung an jeden Zyklus-Ausgang hängen — behebbar ohne Max,
   mit Nachweis über `spiegelstand.py`.
2. **1.3** Außer-Haus-Kopie verschlüsseln (BitLocker To Go) — braucht Max am Gerät.
3. **1.2** xperp-Key: Konto-seitig klären (Host EEA, IP-Whitelist, Trade-Recht) — braucht Max.
4. **1.4** T-004: Kaltgerätekabel/Steckdose prüfen — braucht Max, einen Handgriff nach dem anderen.
5. **2** Fremd-Klone in `skills/` löschen, wenn Platz gebraucht wird — sonst liegen lassen.

Die Reihenfolge ist nicht zufällig: zuerst, was ohne Max und ohne Risiko behebbar ist,
dann, was seine Hand braucht, zuletzt, was reine Kosmetik ist.
