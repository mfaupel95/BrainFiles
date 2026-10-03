---
name: marktbreite-messen
description: "Use when Marktbreite/Regime gemessen wird (viele Paare)."
category: brainfiles
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [markt, breite, regime, krypto, messung, belege]
    related_skills: [markt-recherche, handel-spuren, handelsspur-studie]
---

# Marktbreite und Regime messen

Eine Aussage ueber „den Markt" ist erst belegt, wenn sie ueber **viele
Instrumente** gerechnet ist. Einzelne Kurse zeigen, was ein Wert tut; die Breite
zeigt, was der Markt tut. Die Quellen- und Belegregeln (Quelle + Zeitstempel an
jeder Zahl, Gegenprobe bei zwei Boersen) stehen in `markt-recherche`.

## When to Use (Wann)

- „ist das eine Rotation oder ein Ausreisser bei vier Coins"
- „wie breit ist die Bewegung", „steht der Markt insgesamt im Aufwaertstrend"
- Regime-Entscheidung: long/short nur, wenn der GESAMTmarkt mitgeht
- eine Behauptung aus einem Bericht gegenpruefen („die Alts rotieren")

## Werkzeug

`scripts/alt_breite.py` — nur Standardbibliothek, oeffentliche OKX-Kerzen, kein
Schluessel, rein lesend:

    python <skill>/scripts/alt_breite.py              # 30 Paare, EMA200, Tageskerzen
    python <skill>/scripts/alt_breite.py --laenge 100 # kuerzerer Durchschnitt

Ausgabe: je Paar eine Zeile (Schluss, EMA, Abstand in Prozent), sortiert; dann
die **BREITE**, die **DECKUNG** und der **ZEITBEZUG** der letzten geschlossenen
Kerze. Ein nicht aufloesendes Paar wird namentlich genannt.

Zwei Zahlen heissen hier „Breite" — nicht verwechseln:

| Groesse | Frage | Quelle |
|---|---|---|
| Momentum-Breite | wie viele Werte stehen HEUTE im Plus | Anteil mit positivem 24-h-Vorzeichen |
| Trend-Breite | wie viele stehen ueberhaupt im Aufwaertstrend | Schluss ueber EMA200 (dieser Skill) |

## Die Reihe (Verlauf statt Einzelwert)

Im Haus gibt es die fortgeschriebene Reihe bereits — nicht neu bauen:
`Agenten/Werkzeuge/breite.py` (Reihe `breite-reihe.jsonl` daneben, Laufzeitstand,
**nicht versioniert**, geht in die Sicherung), Wache
`Agenten/Hermes/scripts/breite-wache.py` als Hermes-Cron (`breite-wache`, taeglich
19:00 = nach dem Kerzenwechsel 16:00 UTC, `no_agent`, leere Ausgabe = nichts
senden). Stand, Zahlen und Befunde: [[Marktbreite-Reihe]].

    python Agenten/Werkzeuge/breite.py --merken                # messen + fortschreiben
    python Agenten/Werkzeuge/breite.py --fuellen --tage 250    # rueckwaerts nachrechnen
    python Agenten/Werkzeuge/breite.py --reihe                 # Verlauf je Kerzentag
    python Agenten/Werkzeuge/breite.py --statistik              # Verteilung, Folgeverhalten

`scripts/alt_breite.py` in diesem Skill bleibt der Ad-hoc-Messwert fuer einen
einzelnen Tag.

**Dieselbe Rechenregel fuer jeden Tag.** Das Fenster ist fest (`FENSTER` = 600
abgeschlossene Kerzen, in Live-Lauf und Nachrechnung derselbe Wert). Ein Fenster,
das sich nur nach dem richtigen Abstand richtet, misst bei kurzen Reihen den
EMA-Startwert mit: bei 299 Kerzen traegt der Startwert noch ~37 % Gewicht und
dreht bei einzelnen Paaren das VORZEICHEN (gemessen: BTC -1,24 % gegen +4,52 %).
Eine Reihe aus zwei Fenstern ist keine Reihe.

**Ein Nachlauf darf Live-Werte nicht ersetzen.** Vorgabe ist, nur fehlende Tage
zu ergaenzen; mit `--ueberschreiben` bleibt der alte Messwert als `live_alt` in
der Zeile stehen statt zu verschwinden. Genauso behaelt eine Live-Messung, die
eine nachgerechnete Zeile desselben Tages ersetzt, das nachgerechnete Ergebnis als
`nachgerechnet_alt`.

**Eine Wache darf heilen, ohne zu melden.** `breite-wache.py` rechnet fehlende
Tage nach und meldet nur, wenn wirklich Tage fehlten, eine Luecke bleibt oder
Live-Weg und Nachrechnung um mehr als 0,5 Punkte auseinanderlaufen. Die
Heiltiefe ist die AUSFALLLAENGE (`_heil_tage`: fehlende Kerzentage zwischen
letzter Zeile und gemessener Kerze, mindestens 5, hoechstens `HEIL_MAX` 120,
plus eine Randkerze) — passt die Luecke in den mitgemessenen Verlauf
(`messen(mit_verlauf=True)`, kein zweiter Abruf), heilt er daraus, sonst holt
`fuellen` die Kerzen selbst. Feste 5 Tage liessen einen dreiwochen-Ausfall als
Loch stehen. Leere Ausgabe heisst nichts zu sagen, nicht nichts getan —
geschrieben wird auch dann.

**Luecken gehoeren genannt, nicht nur gezaehlt.** `breite.py --reihe` sagt
ausdruecklich, ob zwischen aeltester und neuester Zeile Kalendertage fehlen
(`fehlende_tage` / `luecken_text`, Bereiche statt Einzeltage); ohne Luecke sagt
es das ebenfalls. Sonst faellt ein Loch nur dem auf, der die Datei liest.

**Eine Absturz-Meldung wird begrenzt.** Fallen bei einem breiten Einbruch 23
Paare auf einmal unter die EMA200, nennt die Wache nur die `NEU_UNTER_MAX` (5)
NAECHSTEN an der EMA200 (ein Paar, das gerade eben darunter faellt, ist das
Fruehwarnzeichen) und den Rest als Zahl. Gemessen: 27 Zeilen wurden so zu 10.
Die Zahl in der Ueberschrift und der gemerkte Stand bleiben vollstaendig.

**Die Reihe fuehrt EINE ZEILE JE KERZENTAG, nicht je Messung.** Eine Messung
derselben Kerze ERSETZT ihre Zeile (letzte des Tages gewinnt); die Tageskerze
wechselt 16:00 UTC, der Meldezeitpunkt muss also NACH diesem Wechsel liegen. Ein
Werkzeug, das bei jedem Lauf anhaengt, macht aus einem Handelstag "30 Messungen":
die Reihe sieht lang aus und enthaelt doch nur EINEN Punkt — genau die
Richtungsaussage, fuer die sie gebaut wurde, bleibt unbelegbar, und niemand sieht
es der Datei an. Gegenprobe: `--reihe` muss die Zahl der KERZENTAGE nennen, nicht
die Zahl der Zeilen, und bei nur einem Tag ausdruecklich sagen, dass ein Messpunkt
keine Richtung ist. Fuer die Auswertung zaehlen Kerzentage.

## Regeln, die die Zahl tragen

1. **Nur GESCHLOSSENE Kerzen rechnen.** Die laufende Tageskerze wandert und macht
die Breite bei jedem Abruf anders; in der OKX-Antwort ist das `confirm == "1"`.
2. **Den Zeitbezug mitliefern.** OKX-Tageskerzen beginnen 16:00 UTC (00:00 UTC+8),
die letzte geschlossene Kerze ist der Handelstag, der um 16:00 UTC endete. Ohne
diesen Satz passt die Messung nicht zur Live-Kurszeile, und der Nutzer haelt zwei
richtige Zahlen fuer einen Widerspruch.
3. **Deckung nennen, nicht nur die Quote.** „29 von 29 = 100 %" ist eine Messung,
„0 von 0 = 0 %" ein Fehler. Die Zeile „X von Y gemessen, Z nicht messbar" ist
das, was einen stillen Ausfall von einem Ergebnis unterscheidet.
4. **Ein Fenster ist keine Messung.** Wer die Laenge des Durchschnittsfensters
   aendert, aendert bei einzelnen Paaren das Vorzeichen — die Fensterlaenge gehoert
   zur Rechnung wie die Quelle, und ein Nachlauf muss DASSELBE Fenster benutzen
   (siehe „Die Reihe"). **Ein Fenster wird nicht geschaetzt, sondern gegengeprobt:**
   die Reihe ZWEIMAL rechnen (z. B. 600 gegen 1200 Kerzen ueber dieselben Tage) und
   beide Ausgaben vergleichen — Mittel, Median, kleinster und groesster Wert UND
   eine Stichprobe einzelner Tage. Gleiche Summenwerte allein beweisen nichts: im
   Haus waren sie fuer beide Fenster identisch, waehrend an einem Tag ein einzelnes
   Paar an der EMA kippte (6,9 % gegen 10,3 % = 1 von 29). Beides in die Doku — die
   Gleichheit der Summenwerte UND die Restempfindlichkeit mit Tag und Zahl. Die
   Zahlen aus der EIGENEN Ausgabe lesen (eine gekuerzte Ausgabe ist keine Messung)
   und das Fenster nur dann kuerzen, wenn die Paar-Vorzeichen stabil bleiben; ein
   laengeres Fenster kostet Geschichte (Paare x Kerzen je Nachlauf).
5. **Ein Messpunkt ist keine Richtung.** „Die Breite schrumpft" braucht eine Reihe
(taeglich festhalten, siehe „Die Reihe" oben). Aus einem Wert folgt der Zustand,
nicht der Trend — und eine Reihe, die mehrere Zeilen fuer DENSELBEN Tag enthaelt,
ist weiterhin ein Messpunkt.
6. **Breite messen, BEVOR gedeutet wird.** „BTC steht, die Alts steigen" ist kein
Beweis fuer eine Rotation — eine Rotation hat einen Verlierer. Erst wenn ein Teil
des Markts unter seinem langfristigen Durchschnitt liegt, gibt es Nachzuegler, in
die rotiert werden koennte.

## Nicht die Breite: wer bewegt sich (Topmover)

Die Breite zaehlt, WER ueber der EMA200 steht. Sie sieht nicht, dass die Kaeufer
weggehen - an einem Tag mit 89,7 % Breite kann die Mehrheit der Paare ueber der
Linie liegen und unter dem Medianvolumen handeln. Die zweite Frage - **was
bewegt sich, und traegt das Volumen die Bewegung** - beantwortet
`references/mover-und-lagen.md` mit dem Werkzeug
`Agenten/Werkzeuge/topmover.py` (oeffentliche OKX-Kerzen, kein Schluessel,
fuenf Lagen, ATR je Zeile). Merksatz dort: der **Traeger kommt vor dem Kurs**,
und `1,0x Median` heisst "wie immer", nicht "Traeger da".

## Die Zahl lesen

- **Sehr hohe Breite (alle oder fast alle ueber dem Durchschnitt):** kein Laggard
  — also auch kein billiger Aufhol-Trade. Die Werte mit dem **kleinsten Abstand**
  zum Durchschnitt sind die ersten, an denen ein Dreh sichtbar wird; sie sind der
  Maßstab fuer „die Breite kippt", nicht der Index selbst.
- **Mittlere Breite:** eine echte Rotation ist moeglich — es gibt Verlierer und
  Gewinner.
- **Der Index allein sagt nichts ueber die Breite.** Ein stehender BTC mit
  steigenden Alts und ein steigender BTC mit fallenden Alts sind zwei verschiedene
  Lagen mit derselben Kurszeile.

Der Abstand zum Durchschnitt ist ein Mass fuer **Weite, nicht fuer Richtung**: ein
Wert weit ueber seinem Durchschnitt ist weit gelaufen, nicht automatisch ein Kauf.

## Fallen

- **OKX oeffentliche Schnittstellen beantworten `urllib` ohne User-Agent mit HTTP
  403.** Der Standardkopf wird geblockt; `Request(url, headers={"User-Agent": ...})`
  mitgeben. Sonst sieht jeder Abruf wie ein Rechteproblem aus, obwohl die
  Schnittstelle offen ist.
- **Ein Symbol, das auf dem Host nicht existiert, meldet `51001`** — nicht als
  Nullkurs verbuchen, sondern namentlich als Luecke nennen. Faellt so ein Paar
  still aus der Liste, sieht die Quote vollstaendiger aus als sie ist.
- **Die Zahl nie aus `zustand.json`, Journalen oder einer Notiz ableiten** — immer
  neu messen. Kurse sind Momentaufnahmen; die Messung traegt Zeitpunkt und Quelle.
- **CoinGecko als Breitenquelle nur als Notnagel** (HTTP 429 im Haus regelmaessig).
  Wer 429 sieht, hat keine Breite gemessen, sondern eine Grenze erreicht.
- **Der Nenner wandert.** `n_gesamt` steht in jeder Zeile der Reihe und gehoert
  mitgelesen: „25 von 29" und „25 von 28" sind verschiedene Prozente. Paare
  kommen (SEI-USDT erst ab Juni) und gehen (Ausfall).
- **Ein Rueckgang wird gegen die letzte MELDUNG gerechnet, nicht gegen den
  Vortag.** Sonst summieren sich „vorgestern −9, gestern −9" nie zu einer
  Nachricht; innerhalb einer Stufe waere die Wache sonst blind (100 % auf 81 %
  ohne eine einzige Zeile).

## Abgrenzung

- Quellen, Belege, Aktien/Indizes/News: `markt-recherche`
- Eigene Handels-Spuren auswerten (Runden, Trefferquote, Kosten): `handel-spuren`,
  `handelsspur-studie` — die Breite ist der MARKT, nicht das eigene Buch
- Keine Order auf diesem Weg. Werkzeug und Skill sind rein lesend.
