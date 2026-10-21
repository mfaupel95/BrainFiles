# Signature Plot: Volatilität gegen Abtastintervall

Der Signature Plot trägt die Volatilität über dem Abtastintervall auf. Fällt die Kurve zu kurzen Intervallen hin stark ab, steckt Mikrostruktur-Rauschen im Datensatz. Bleibt sie flach, ist das Rauschen vernachlässigbar. Gemessen auf XBTEUR-Kerzen (Kraken, öffentliche API, siehe [[Verbindungen]]).

**Ergebnis 21.10.2026:** Mit 720 Fünf-Minuten-Kerzen (knapp 60 Stunden) liegt der Wert bei 5 Minuten bei 35,5 %, zwischen 5 und 60 Minuten bei 33 bis 35 %. Ein Rauschaufschlag ist nicht sichtbar.

**Warum:** Eine kürzere Stichprobe (120 Minutenkerzen) zeigte bei 1 Minute 63 %, weil ein Kursrutsch und ein Spike darin lagen. Die längere Reihe glättet das. Für Aussagen unter 1 Minute fehlen Sekundendaten; dafür ist noch keine Quelle festgelegt.

**Stand:** 2026-10-21
