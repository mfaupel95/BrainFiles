---
name: bildflaeche-bearbeiten
category: software-development
description: Use when a photo's floor or wall must show a material.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [bild, textur, material, lokal, diffusion, openmontage]
    related_skills: [fremd-agenten-betrieb, repos-zentrale, telegram-bruecke-diagnose]
---

# Eine Flaeche in einem echten Foto gegen ein Material tauschen

Klassenauftrag: „Leg dieses Muster auf den Boden in diesem Bild", „zeig mir
die Wand in dieser Farbe". Nutzer will **eine VARIANTE seines Raums**, keine
neue Erfindung. Der Raum ist pixelweise das Original; nur die benannte
Flaeche aendert sich. Modelle, Werkzeugpfade und Diffusions-Parameter fuer
den Bildagenten stehen in `references/openmontage-lokal.md`.

## When to Use

- der Nutzer schickt ein Foto eines Raums und ein zweites Bild eines
  Materials („Muster im 2. Bild, Boden im 1. Bild bedecken")
- eine vorhandene Aufnahme soll zeigen, wie ein anderer Bodenbelag, eine
  andere Wandfarbe oder eine andere Oberflaeche wirkt
- ein Bildagent hat Varianten geliefert, die nicht als Raumvariante erkennbar
  sind (verzerrte Perspektive, neue Tuers, Fremdgeometrie)

Nicht fuer allgemeine Bildbearbeitung (Zuschneiden, Format, Farbkorrektur)
und nicht fuer neue Bilder ohne Bezug zu einem Originalfoto.

## Reihenfolge

1. **Bilder zuerst ansehen, dann rechnen.** Vision-Aufruf je Bild: was ist
   Raum, was ist Material, welche Flaeche genau. Ohne das wird aus dem
   Materialbeispiel der falsche Bildbereich.
2. **Materialquelle entrahmen.** Das Mustersample enthaelt Griff, Etikett,
   Holzhintergrund. Einen Ausschnitt nehmen und mit Vision pruefen, dass NUR
   Textur drin ist — 30-70 % des Bildes ist die sichere Ausgangsbasis, das
   Ergebnis aber mit dem Vision-Tool bestaetigen, nicht annehmen.
3. **Bodengrenze bestimmen, nicht raten.** Rasterlinien mit Beschriftung in
   das Original zeichnen und die Kante ablesen. **Wichtig: die Werte dann
   SELBST uebernehmen.** Eine Vision-Analyse mit eingeblendetem Raster
   liefert gern plausibel falsche Koordinaten und rechnet die Skalierung des
   Vorschaubilds noch einmal — sie erwaehnt dann „mal 2" fuer ein bereits
   verkleinertes Bild. Das Bild selbst ansehen oder rechnen, nie die Zahl
   aus der Analyse uebernehmen.
4. **Perspektivisches Textur-Mapping, keine Diffusion als Erstversuch.**
   Der Raum bleibt unangetastet, die Textur wird bilinear abgetastet; die
   Tiefenachse so waehlen, dass die Fugen in die Tiefe laufen, die
   Querachse gegen einen Fluchtpunkt verjengen.
5. **Licht uebernehmen, aber GEGLAETTET.** Die Original-Luminanz als
   Multiplikator traegt die Struktur des alten Belags (Streifen des Teppichs,
   Dielenverlauf) in die neue Textur — das Ergebnis liest sich als Holzoptik
   statt Stein. Die Lichtkarte vor der Anwendung weichzeichnen: Raumlicht
   ist eine Flaeche, kein Muster.
6. **Tonwert als VERSCHIEBUNG, kein Gain.** Ein Gain auf eine Referenzfarbe
   zieht das ganze Bild ins Holz. Mittelwert der Textur messen und auf den
   Zielwert verschieben; Saettigung vorher absenken, weil Fliesentexturen
   kraeftig sind und ein gedeckter Boden das nicht sein darf.
7. **Ausschnitt statt Vollbild pruefen.** Zwei Haelften nebeneinander
   (Original | Ergebnis) aus demselben Crop: so sieht man Kante, Textur und
   Fugen in einem Bild, und die Raumwinkel bleiben beurteilbar.
8. **Ergebnis mit Vision gegenpruefen, mit Zahlen belegen.** Die Frage ist
   „Boden jetzt Material, Waende unveraendert?". Angenommene Werte der
   Bodenflaeche und „geaenderte Pixel in Prozent" ausgeben — der Anteil
   belegt, dass wirklich nur die Flaeche geaendert wurde.

## Fallen

- **Diffusion (Text-to-Image oder img2img mit hoher strength) verliert die
  Raumgeometrie.** Sie ist der zweite Weg, nicht der erste: erst der
  Mapper, und wenn dessen Ergebnis nicht traegt, Diffusion als Alternative
  vorstellen. Ein Diffusionsergebnis mit gerissenen Tueren und verzerrter
  Perspektive wird nicht durch Nachbearbeiten gerettet — dann verwerfen und
  den Mapper nachziehen.
- **Ein Agent, der Bildgenerierung delegiert, liefert oft Dutzende Varianten
  und eine Erfolgsmeldung ohne Sichtpruefung.** Vor dem Bericht selbst mit
  Vision hinsehen. Eine behauptete „pixel-exakte Geometrie, Boden fertig" ist
  erst eine Behauptung; die eigene Messung (geaenderte Pixel, Randlage)
  steht daneben.
- **Eine gerade Bodengrenze malt ueber Wandoberflaeche und Moebel.** Der
  Flur wird von oben fotografiert: links steht ein Schrank tief ins Bild,
  rechts ist die Wand hoeher. Die Kante als Funktion der Bildspalte
  modellieren (zwei bis drei Stuetzpunkte), nicht als eine Zahl.
- **Ein Masken-Generator aus einem Bildagenten ist meist eine Rechteckmaske.**
  Er bestaetigt den Boden als „ab hier nach unten", malt dabei aber
  Schrank und Tuer mit. Die eigene Maske bauen und mit Vision gegen die
  Kante pruefen.
- **Nichts erfinden, was nicht gemessen wurde.** Wenn die Bodenkante
  geschaetzt ist, steht das im Bericht — sie ist eine Zahl, kein Umbau, und
  der Nutzer kann sie in einer Minute korrigieren.