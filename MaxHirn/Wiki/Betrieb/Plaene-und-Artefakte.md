---
id: 20261014-plaene-und-artefakte
title: 'Plaene und Artefakte einsammeln'
tags: [betrieb, kanban, plaene]
created: 2026-10-14
updated: 2026-10-14
related: ['[[INDEX]]', '[[Wissen/INDEX]]']
summary: 'Wo Plaene des Hauses liegen, wie Kanban-Artefakte zu durchgehen sind (drei Klassen), und die Regel, dass ein Plan nie nur als Karten-Artefakt existieren darf.'
---

# Plaene und Artefakte einsammeln

Kanban-Worker geben Abschlussberichte als Karten-Artefakte ab
(`Agenten/Hermes/kanban/attachments/<id>/`). Diese laufen unbegrenzt auf und
verrauschen, bis jemand sie durchgeht. Bestand am 14.10.2026: 16 Karten mit
Artefakten, 3 Klassen.

## Die drei Klassen

| Klasse | Merkmal | Weg |
|---|---|---|
| **Plaene/Konzepte** | Einzigartig im Baum - nirgends sonst versioniert | Nach `Werkstatt/Projekte/` kopieren (AGENTS.md-Regel: Plaene gehoeren dort hin) |
| **Code** | Duplikat eines Moduls, das schon im Baum lebt | Nichts tun - Verweis reicht; Artefakt-Fassungen sind oft AELTER als der Live-Code |
| **Berichte/Rohdaten** | Situations-Snapshot eines Laufs (groessen.txt, block-review.md, requeue-report) | Wegwerf - bleibt als Karten-Beleg stehen, NICHT nach Werkstatt |

## Bestand 14.10.2026 (ausgefuehrt)

Eingesammelt nach `Werkstatt/Projekte/zielstruktur-c-o-20260930/`
(vier Vorarbeiten zu t_e52230de, konsolidiert in t_0f03a945):
- `umsetzungsplan-zielstruktur.md` - der EINE konsolidierte Umsetzungsplan fuer die Zielstruktur C:/O:
- `konzept-datei-verzeichnisstruktur-c-o.md` - strukturiertes Konzept C:/O:
- `zielstruktur-multi-ki.md` - Zielstruktur fuer den Multi-KI-Workflow mit konstantem Speicher
- `konzept-repo-einbindung.md` - schlanke Repo-Einbindung ohne Modell-Ueberlast
- `layout-handels-spuren-bots.md` - Layout der Handels-Spuren und Bots (Endfassung `_1`, 279 Zeilen; die 46-Zeilen-`.md` ist ein abgeschnittener Entwurf)

Redundant (nicht kopiert): `ROUTING_PLAN_2026-10-04_v173.md` liegt bereits
vierfach in `MaxHirn/Archiv/`; das Skill-Automatik-Paket (`reaktion.py`,
`kanaele.py`, `reaktionen.yaml`, `SPEZIFIKATION.md`, Registry) lebt in
`Agenten/Hermes/automatik/` - zwei Artefakt-Fassungen (`reaktion.py`,
`test_reaktion.py`) sind ALT gegen den Live-Code, vor einem Kopieren hashen.

## Regel

Ein Plan oder Konzept darf nie NUR als Karten-Artefakt existieren - die
Laufzeitordnung `kanban/attachments/` ist Durchgangsware und geht bei einem
Aufraeumen mit verloren. Nach jedem Planungs-Kartendurchgang: einzigartige
Dokumente nach `Werkstatt/Projekte/`, Code im Baum verifizieren (Hash gegen
den Live-Stand, nie blind kopieren), Berichte liegen lassen.
