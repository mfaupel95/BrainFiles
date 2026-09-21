# Bericht und Meldungen nach Telegram ausliefern

Ausloeser: "der Tagesbericht/Wochenbericht kommt nicht an", "Telegram-Fehler 400",
`can't parse entities`, eine Nachricht erscheint abgeschnitten, oder eine Meldung soll
neu an Telegram gehen. Im Haus laeuft alles ueber EINE Sendestelle
(`Agenten/Handel/melder.py`), die auch die Wachen und der Handelsbot benutzen.

## Regel 1: mit `parse_mode=HTML` wird an der SENDESTELLE entschaerft, nicht im Bericht

Telegram liest ein rohes `<...>` als Marke. Steht im Text etwas wie
`n=<Zahl> heisst: zu wenige Runden` oder ein Traceback (`<module>`, `<lambda>`, `<stdin>`),
weist die API die GANZE Nachricht ab:

    400 Bad Request: can't parse entities: Unsupported start tag "zahl"

Der Bericht kommt dann nie an — und es sieht aus, als haette die Spur oder das Konto ein
Problem. Deshalb gehoert die Rettung in die Sendefunktion (eine Stelle fuer
Tagesbericht, Wochenbericht, Handelsmeldungen und Wachen), nicht in jeden Text:

1. Erlaubte Marken stehen lassen: `</?(b|i|u|s|code|pre|a)(\s[^<>]*)?>`.
2. Alles andere `<` / `>` per `&lt;` / `&gt;` entschaerfen.
3. Nur NACKTE `&` zu `&amp;` machen (`&(?!(amp|lt|gt|quot|#\d+|#x[0-9a-fA-F]+);)`). Wer
   `&` blind ersetzt und vorhandene Entitaeten nicht ausnimmt, schreibt `&amp;amp;` in
   die Nachricht.
4. Die Funktion muss **idempotent** sein: derselbe Text zweimal entschaerft darf sich
   nicht weiter veraendern (sonst waechst bei jedem Rerun die Zahl der `&amp;`).

Erst NACH dem Entschaerfen an Zeilengrenzen teilen (Telegram bricht hart bei 4096 ab;
im Haus sind es 4000 Zeichen) — anders zerreisst eine Marke mitten im Stueck.

## Regel 2: die Auslieferung wird bewiesen, nicht angenommen

- Die Sendefunktion WIRFT bei einer abgewiesenen Nachricht (HTTP-Fehler mit
  `description`). Ein Lauf ohne Ausnahme ist damit der Beleg "akzeptiert" — kein
  zweiter Kanal, kein Blick in die App noetig.
- **Den ECHTEN Berichtstext durch die Sendefunktion schicken**, nicht einen
  handgebauten Beispielsatz: der fehlerhafte Baustein sitzt in einer Vorlage.
- Ein Test deckt die echten Vorlagen ab: Bericht bauen, entschaerfen, dann pruefen, dass
  AUSSERHALB der erlaubten Marken kein `<`/`>` und kein nacktes `&` mehr steht — und
  dass die Stuecke unter der Laengengrenze bleiben. Fuer den Vorfall, an dem es
  auffiel, gehoert ein Test ueber genau diese Vorlage dazu.
- Klartext-Ausgaben (die Bots ohne `parse_mode`) brauchen das nicht — dort waeren
  `&lt;` und `&amp;` sichtbarer Muell. Die beiden Sendewege nicht vermischen.

## Fallen

- **Ein fehlender Bericht ist kein Beweis fuer einen kaputten Bot.** Zuerst pruefen, ob
  die Vorlage spitze Klammern enthaelt (Platzhalter wie `<Name>`, `<Zahl>`,
  Fehlertexte, Tracebacks) — erst danach Token, Chat-ID oder Kontingent verdaechtigen.
- **Ein langer Bericht wird geteilt, nicht gekuerzt.** Wer die Laengengrenze mit einem
  Zeichenlimit beantwortet, verliert den Schluss der Meldung ohne Fehlermeldung.
- **Der Split darf keine Entitaet zerreissen.** Nach dem Entschaerfen teilen, und zwar an
  `\n`; ein Stueck, das mitten in `&amp;` endet, wird von Telegram abgewiesen.
- **Auch Fehlermeldungen aus fremden Programmen tragen Klammern.** Weil entschaerft wird,
  bevor geteilt wird, sind sie harmlos — wer die Entschaerfung nur auf die eigenen
  Textbausteine anwendet, faellt beim naechsten Traceback wieder um.
