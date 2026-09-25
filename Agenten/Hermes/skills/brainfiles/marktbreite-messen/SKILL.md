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
`Agenten/Werkzeuge/breite.py` (`--merken` schreibt, `--reihe` zeigt den Verlauf in
Punkten je Kerzentag), Ablage `Agenten/Werkzeuge/breite-reihe.jsonl` (Laufzeitstand,
**nicht versioniert**), Wache `Agenten/Hermes/scripts/breite-wache.py` als Hermes-Cron
(taeglich, `no_agent`, leere Ausgabe = nichts senden; meldet Stufenwechsel, neu
unter die EMA200 gefallene Paare, Rueckgang gegenueber der letzten Meldung,
unvollstaendige Deckung). `scripts/alt_breite.py` in diesem Skill bleibt der
Ad-hoc-Messwert fuer einen einzelnen Tag.

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
4. **Ein Messpunkt ist keine Richtung.** „Die Breite schrumpft" braucht eine Reihe
(taeglich festhalten, siehe „Die Reihe" oben). Aus einem Wert folgt der Zustand,
nicht der Trend — und eine Reihe, die mehrere Zeilen fuer DENSELBEN Tag enthaelt,
ist weiterhin ein Messpunkt.
5. **Breite messen, BEVOR gedeutet wird.** „BTC steht, die Alts steigen" ist kein
Beweis fuer eine Rotation — eine Rotation hat einen Verlierer. Erst wenn ein Teil
des Markts unter seinem langfristigen Durchschnitt liegt, gibt es Nachzuegler, in
die rotiert werden koennte.

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

## Abgrenzung

- Quellen, Belege, Aktien/Indizes/News: `markt-recherche`
- Eigene Handels-Spuren auswerten (Runden, Trefferquote, Kosten): `handel-spuren`,
  `handelsspur-studie` — die Breite ist der MARKT, nicht das eigene Buch
- Keine Order auf diesem Weg. Werkzeug und Skill sind rein lesend.
