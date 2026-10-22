---
name: skill-maxhirn-videoanalyse
description: Trockenlauf des Skills MaxHirn:videoanalyse — YouTube-Transkript per Skript ziehen, auswerten, Notiz ablegen; Fallen; Hausschema; Trockenlauf.
metadata:
  type: reference
---

**Zweck:** YouTube-Videos transkribieren und nach Hausschema auswerten; Ergebnis in Vault-Notiz ablegen.

**Lauf:** 2026-10-22, trockenlauf.

**Befehl:**
```powershell
python .claude\skills\videoanalyse\transkript.py "<URL>" "..\..\Werkstatt\Projekte\Invest\Quellen"
```
Schreibt `<Datum>_<Kanal>_<VideoID>_transkript.txt`. System-Python 3.13, kein venv. Gemessen: 4,7 s für 17-min-Video.

**Ablage:** Transkript → `Werkstatt/Projekte/Invest/Quellen/`; Erkenntnis → Notiz in `Wissen/` per `notiz`-Skill.

**Fallen:**
- `YouTubeTranscriptApi.get_transcript()` veraltet (ab v1.x): `YouTubeTranscriptApi().fetch(vid)` — Segmente haben `.text`
- `captionTracks[0].baseUrl` seit Mitte 2025 leer → nicht verwenden
- InnerTube `youtubei/v1/player` → HTTP 400 (veralteter Key) → Sackgasse
- Fremd-Transkriptseiten (youtubetotranscript.com etc.) → 403/405 → unbrauchbar
- Titel/Kanal: `youtube.com/oembed?url=...&format=json` ist einzige verlässliche Quelle
- Umlaute in Konsole verstümmelt — nur Anzeige; `.txt` ist sauberes UTF-8

**Auswerteschema:**
| Element | Inhalt |
|---|---|
| Herkunft | Kanal, Datum, Länge, ID, Titel wörtlich |
| Kernthese | Was behauptet der Beitrag? |
| Zahlen/Marken | Tabelle + „nicht gegengeprüft" |
| Einordnung | Falsifizierbares Kriterium? Geschäftsmodell der Quelle? |
| Bezug | Betrifft gehandelten Wert? Sonst: „Marktbeobachtung, kein Handelsauftrag" |

**Grenzen:** Nur YouTube; braucht vorhandene Untertitel; kein Bilderkennen; keine Übersetzung.
