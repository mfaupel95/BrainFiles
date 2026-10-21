# Arbeitsregel: reparieren statt abschalten

Stand 2026-10-20. Vom Nutzer ausdrücklich festgelegt.

Bei Störungen an Routinen, Wächtern und geplanten Aufgaben zuerst reparieren oder verbessern, nicht abschalten.

**Warum:** Anlass war der Gateway-Wächter `MaxHirn-Gateway-Waechter`. Er hatte zwischen 15. und 19. Oktober 107 Neustarts ausgelöst, weil er ein gesundes Gateway über Port 9900 für tot hielt. Abschalten hätte das Gateway ohne Absicherung gelassen. Die Reparatur (Prüfung auf den eigenen Herzschlag `gateway_state.json`) hat das Problem behoben.

**So anwenden:**
1. Zuerst prüfen, was die Bedingung wirklich misst, und ob die Messung noch zum aktuellen Stand passt.
2. Dann die Prüfung korrigieren und mit einem Lauf von Hand verifizieren.
3. Abschalten nur als Notbremse, wenn eine Reparatur nicht möglich ist, und das ausdrücklich nennen.

**Ausnahme, die bewusst gewählt wurde:** Der Verbesserer wurde abgeschaltet (Weg C), siehe [[Verbesserer-abgeschaltet]]. Das war eine ausdrückliche Entscheidung des Nutzers, keine Notbremse.
