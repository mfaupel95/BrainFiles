---
name: videoanalyse
description: Holt Transkript und Metadaten eines YouTube-Videos und wertet es nach Hausschema zu einer Wissensnotiz aus. Benutzen bei "entnimm dem Video", "wertet das Video aus", "fass das YouTube-Video zusammen", "was sagt das Video", "Transkript ziehen", oder wenn ein YouTube-Link zu Analyse/Markt/Anleitung kommt.
---

# Videoanalyse

Ein Video ist erst ausgewertet, wenn das Transkript in `Werkstatt/Projekte/Invest/Quellen/`
(bzw. dem thematisch passenden `Quellen/`-Ordner) liegt **und** die Erkenntnis
in einer Notiz unter `Wissen/` steht. Der Chat-Verlauf zählt nicht.

## 1. Der Befehl, der wirklich läuft

```powershell
python .claude\skills\videoanalyse\transkript.py "<URL-oder-VideoID>" "..\..\Werkstatt\Projekte\Invest\Quellen"
```

Schreibt `<Datum>_<Kanal>_<VideoID>_transkript.txt` mit Kopf (Titel, Kanal,
Datum, Länge, Aufrufe, ID, URL) und dem Fließtext dahinter. Läuft mit dem
System-Python (3.13), kein venv. Gemessen 02.09.2026: **4,7 s, 21 459 Zeichen**
für ein 17-min-Video.

Danach: Transkript lesen, nach Abschnitt 3 auswerten, Notiz mit Skill `notiz`
anlegen, `Wissen/INDEX.md` im selben Schritt nachziehen, mit Skill `sichern`
committen.

## 2. Die Fallen, die Zeit gekostet haben

- **`YouTubeTranscriptApi.get_transcript()` gibt es nicht mehr.** Ab v1.x ist es
  eine Instanzmethode: `YouTubeTranscriptApi().fetch(vid, languages=["de","en"])`,
  die Segmente haben `.text` (kein Dict mehr). Das Skript kapselt das.
- **Paket fehlte.** `pip install youtube-transcript-api` — das Skript macht das
  bei `ImportError` selbst.
- **timedtext direkt aus der watch-Seite ziehen → leere Antwort.** Der
  `captionTracks[0].baseUrl` aus dem HTML liefert seit Mitte 2025 `len 0`, auch
  mit `&fmt=json3`/`&fmt=srv3`. Nicht nochmal versuchen. Die watch-Seite wird nur
  noch für `publishDate` / `lengthSeconds` / `viewCount` per Regex angezapft.
- **InnerTube-Player-API (`youtubei/v1/player`, ANDROID-Client)** → `HTTP 400`,
  der öffentliche Key ist veraltet. Sackgasse.
- **Fremd-Transkriptseiten** (youtubetotranscript.com, kome.ai,
  youtube-transcript.io) über web_extract → 403 / 405 / nur Marketingtext. Alle
  unbrauchbar.
- **Titel + Kanal:** `https://www.youtube.com/oembed?url=...&format=json` ist die
  einzige verlässliche Quelle ohne Scraping.
- **Umlaute im Terminal verstümmelt** (`stärker` → `st?rker`) — nur die Anzeige.
  Die geschriebene `.txt` ist sauberes UTF-8. Datei lesen, nicht der Konsole
  glauben.
- **STA-Solutions-Videos:** Der Titel ist ein A/B-getesteter Klickköder und
  taugt nie als Zusammenfassung — steht in [[Marktlage-August-2026]]. Der
  Sprechername wird im Auto-Transkript oft falsch geschrieben ("SCR Solutions",
  "Alexer Schulz").

## 3. Auswerten nach Hausschema

Für Analyse-/Markt-Videos die Struktur aus [[Marktlage-August-2026]] und
[[XRP-Analyse-STA-September-2026]] übernehmen:

- **Herkunft** — Kanal, Datum, Länge, ID, Titel wörtlich.
- **Was der Beitrag behauptet** — Kernthese knapp.
- **Zahlen/Marken** als Tabelle, mit dem Zusatz „nicht gegengeprüft", solange
  nicht extern verifiziert.
- **Kritische Einordnung** — gibt es ein falsifizierbares Kriterium (Kursziel,
  Zeithorizont, Invalidierungsmarke)? Geschäftsmodell der Quelle? Deckt sich der
  Titel mit dem Inhalt?
- **Bezug zum eigenen System** — betrifft es einen gehandelten Wert
  ([[Marktscanner]], [[XPERP-Handel]])? Wenn nein: ausdrücklich „Marktbeobachtung,
  kein Handelsauftrag".

Bei bekanntem Kanal die Quellenbewertung **nicht wiederholen**, sondern per
`[[…]]` auf die bestehende Notiz verweisen und dort `related` spiegeln.

## 4. Grenzen

- Nur YouTube. Keine anderen Plattformen.
- Braucht vorhandene Untertitel (auch automatische). Videos ganz ohne Captions
  gibt das Skript mit Fehler zurück — dann kein Transkript, kein Notbehelf.
- Wertet **Text** aus. Charts, eingeblendete Zahlen und Zeichnungen im Bild
  sind im Transkript nicht enthalten; solche Marken bleiben „laut Sprecher".
- Übersetzt nicht. Fremdsprachige Videos werden in Originalsprache abgelegt.
