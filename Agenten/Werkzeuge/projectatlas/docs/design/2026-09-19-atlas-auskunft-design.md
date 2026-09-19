# Design: Atlas-Auskunft fuer Haus-Spuren (Teilprojekt B)

- Datum: 2026-09-19
- Status: zur Freigabe
- Basis: Brainstorming 19.09.2026, genehmigt A1 → B1 → C1
- Abhaengt von: Teilprojekt A (Atlas fuer moon-dev-ai-agents u. a.)
- Abgrenzung: B (Auskunft). A (Atlas anlegen) und C (Atlas-Tab) sind
  eigene Zyklen.

## Zweck

Die acht `moondev_*`-Spuren lesen ihre Signale aus dem geklonten
`Werkstatt/Repos/moon-dev-ai-agents` (je Agent eine Datei unter
`src/agents/`, Datenfunktionen in `src/nice_funcs_hl.py`). Die Zuordnung
„welche Datei ist fuer Signal X zustaendig“ steht heute nur verstreut in
den `wachen.json`-Kommentaren und den `handeln.py`-Kopfkommentaren. B
macht diese Frage beantwortbar: ein Modul, das ueber die ProjectAtlas-Karte
des Repos die zustaendige Datei/Funktion liefert — fuer Diagnose, Doku und
Bot-Antworten. **Es ersetzt keinen Datenweg** der Spuren (die sind
verdrahtet und getestet), es beantwortet nur die Zustaendigkeitsfrage.

## Ist-Zustand (gemessen 19.09.2026)

- Alle acht Spuren lesen aus `moon-dev-ai-agents`:
  funding → `src/nice_funcs_hl.get_funding_rates` (Regel
  `src/agents/fundingarb_agent.py`); liquidation → `liquidation_agent`;
  listingarb → `listingarb_agent`; marktlage → `coingecko_agent`;
  sentiment → `sentiment_agent`; topmovers → `new_or_top_agent`;
  whale → `whale_agent`; iv_wand → OKX-Optionsdaten (kein Repo).
- Die Zuordnung steht in `moondev_*/wachen.json` (`_zweck`, `_quelle`)
  und in den `handeln.py`-Kopfkommentaren — nicht maschinenlesbar.
- ProjectAtlas-CLI kann die Frage beantworten:
  `projectatlas --format json files "<begriff>"` (Volltextsuche in der
  Karte) und `slice <datei>` (exakte Quellstelle).
- Die Spuren laufen als eigene Prozesse ohne MCP; ein CLI-Aufruf je
  Anfrage ist moeglich, aber teuer (Prozessstart ~1 s).

## Entscheidungen

1. **Ein Modul `Agenten/Handel/atlas_auskunft.py`**, das die Frage
   „welche Datei ist fuer Signal X zustaendig“ beantwortet. Es kennt die
   Spur→Repo-Zuordnung als Konstante (die acht Spuren → `moon-dev-ai-agents`,
   iv_wand → kein Repo) und fragt die Karte ueber die CLI.
2. **Cache statt heissem Zyklus:** Die Antwort wird je Spur 24 h gecacht
   (JSON neben dem Modul). Der erste Aufruf fragt die CLI, danach liest
   der Cache. Niemals im heissen Zyklus einer Spur — nur auf Anforderung
   (Diagnose, Tagesbericht, Bot-Antwort).
3. **CLI als Schnittstelle, nicht SQLite direkt** — die CLI ist die
   stabile Schnittstelle; das SQLite-Schema von ProjectAtlas ist intern
   und darf sich aendern.
4. **Antwortformat:** `{spur, repo, datei, funktion, quelle}` — die
   Funktion wird aus dem `wachen.json`-Kommentar uebernommen, die Datei
   aus der Atlas-Suche bestaetigt. Fehlt die Karte (Repo nicht kartiert),
   liefert das Modul die Datei aus der bekannten Zuordnung und vermerkt
   `atlas: fehlt`.
5. **Nutzung:** (a) Tagesbericht/Diagnose zeigt je Spur die zustaendige
   Datei, (b) ein Bot/eine Sitzung kann „welche Datei fuer funding?“
   beantworten, (c) nach einem Repo-Update erkennt man Pfad-Abweichungen
   (Atlas nennt die neue Datei, die Konstante die alte).

## Umfang B

**In** (Abnahmekriterien):

1. `atlas_auskunft.py` mit `zustandig(spur) -> dict` fuer die acht
   moondev-Spuren und iv_wand; Cache 24 h; CLI-Fallback.
2. `--pruefen`-Modus: alle Spuren durchlaufen, Ausgabe je Spur
   (Datei, Funktion, Atlas-Status), Exit 0 wenn alle beantwortbar.
3. Tagesbericht-Zeile oder Diagnose-Aufruf, der die Zustaendigkeit
   anzeigt (wo der Tagesbericht schon Spur-Infos ausgibt).
4. Tests: `tests/test_atlas_auskunft.py` — Cache-Treffer, CLI-Fallback,
   fehlende Karte, iv_wand (kein Repo), unbekannte Spur.
5. Doku: `Wissen/Projektatlas.md` oder `Wissen/Handel.md` um die
   Zustaendigkeitsfrage ergaenzen.

**Nicht in B** (bewusst):

- Kein Umbau der Datenwege der Spuren (die bleiben wie sie sind).
- Kein Laufzeit-Aufruf im heissen Zyklus.
- Kein neues Bot-Profil, keine MCP-Anbindung (CLI reicht).
- Keine Zweck-Kuration (gehoert zu A).

## Massnahmen gegen gemessene Fallen

| Falle | Massnahme |
|---|---|
| CLI-Aufruf teuer (~1 s) | Cache 24 h; nur auf Anforderung, nie im Zyklus. |
| Karte fehlt (Repo nicht kartiert) | Modul faellt auf die bekannte Zuordnung zurueck, `atlas: fehlt`. |
| Repo-Update verschiebt Datei | Atlas nennt die neue Datei; Konstante bleibt alt — Abweichung sichtbar. |
| Umlaute/Steuerzeichen in Pfaden | Ausgabe der CLI als UTF-8 lesen; Pfade nicht selbst bauen. |

## Nachweis (am Ende von B)

```
python atlas_auskunft.py --pruefen        # je Spur Datei/Funktion/Atlas-Status, Exit 0
python -m unittest tests/test_atlas_auskunft.py   # gruen
```

## Betroffene Dateien (Aenderung)

- Neu: `Agenten/Handel/atlas_auskunft.py`, `Agenten/Handel/tests/test_atlas_auskunft.py`.
- Aenderung: Tagesbericht/Diagnose (eine Zeile je Spur).
- Doku: `Wissen/Projektatlas.md` oder `Wissen/Handel.md`.
- Neu: diese Datei unter `docs/design/2026-09-19-atlas-auskunft-design.md`.