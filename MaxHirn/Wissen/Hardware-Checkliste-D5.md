---
id: 20260830-hardware-checkliste-d5
title: 'Hardware-Checkliste: Behebung D5-Fehler & Startprobleme'
tags: [hardware]
created: 2026-08-29
updated: 2026-09-06
related: [20260830-hardware]
summary: 'Schrittfolge zur Eingrenzung des D5-RAM-Fehlers und der Kernel-Power-41-Abschaltungen.'
---

# Hardware-Checkliste: Behebung D5-Fehler & Startprobleme

**ZIEL:** System stabilisieren und Ursache für D5 (RAM) / Kernel-Power 41 (Strom) finden.
**GEFAHR:** Instabiles Netzteil + Misch-RAM können Hardware beschädigen. **Keine Experimente mit BIOS-Spannungen!**

**Hintergrund, Messstände und bereits ausgeschlossene Ursachen:** [[Hardware]].

---

## ⚠️ VORBEREITUNG (Sicherheit zuerst)
- [ ] Rechner komplett ausschalten.
- [ ] Netzstecker aus der Dose ziehen.
- [ ] Startknopf 5-10 Sekunden gedrückt halten (Reststrom entleeren).
- [ ] Erdung: Kurze Zeit ein unlackiertes Metallteil (z.B. Heizung) berühren, um statische Aufladung zu vermeiden.

## SCHRITT 1: Peripherie-Minimalismus
*Ziel: Stromlast beim Start reduzieren und USB-Konflikte ausschließen.*
- [ ] **Alle externen Festplatten abziehen** (G:, O:, J:, E:).
- [ ] Nur Tastatur und Maus angeschlossen lassen.

## SCHRITT 2: RAM-Vereinfachung (Die "D5-Kur")
*Ziel: Mischbestückung eliminieren, da diese oft instabil ist.*
- [ ] **Alle alten 8GB-Riegel (2133 MHz) ausbauen.**
- [ ] **Nur die zwei neuen 16GB-Riegel (3100 MHz) einbauen.**
- [ ] Sicherstellen, dass sie in den korrekten Slots für Dual-Channel stecken (siehe Handbuch, meist Slot 2 und 4).

## SCHRITT 3: Der Test-Start
- [ ] Strom anschließen $\rightarrow$ Start drücken.
- [ ] **Beobachtung des Debug-Displays:**
    - [ ] **Bootet normal durch?** $\rightarrow$ Ursache war die Mischbestückung. (Sicherstellen, dass Windows stabil läuft).
    - [ ] **Hängt immer noch auf D5?** $\rightarrow$ Gehe zu Schritt 4.
    - [ ] **Hängt auf einem anderen Code?** $\rightarrow$ Code notieren und Hermes melden.

## SCHRITT 4: RAM-Kreuztest (Nur falls Schritt 3 scheiterte)
*Ziel: Defekten Riegel identifizieren.*
- [ ] Nur **einen** der 16GB-Riegel einbauen $\rightarrow$ Startversuch.
- [ ] Wenn Fehler $\rightarrow$ Riegel tauschen (den anderen 16GB-Riegel testen).
- [ ] Wenn beide einzeln funktionieren, aber zusammen nicht $\rightarrow$ Problem liegt am Controller oder Netzteil.

---

## 📝 ERGEBNISSE (Für Hermes notieren)
- Datum/Uhrzeit: _____________________
- Ergebnis Schritt 3: [ ] Bootet [ ] D5 [ ] Anderer Code: ______
- Ergebnis Schritt 4: [ ] Riegel A ok [ ] Riegel B ok [ ] Beide defekt
- Beobachtungen: _____________________________________________________
