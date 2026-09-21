---
id: 20260921-gates-und-freigabe
title: 'Handel — Gates und Freigabe'
tags: [handel, sicherheit]
created: 2026-09-21
updated: 2026-09-21
related: ['[[Handel/Spuren-Uebersicht]]', '[[Wissen/Handelsregeln]]']
summary: 'Die Sperrenkette vor jeder Live-Order, das Freigabefenster und die Armingschritte — in der Reihenfolge, in der sie geprueft werden.'
---

# Gates und Freigabe

## Die Sperrenkette (jede Spur prueft selbst)

Eine Live-Order entsteht nur, wenn **alle** Punkte offen sind:

1. `handel_erlaubt: true` in der `wachen.json`
2. `freigabe.erfuellt: true` — der von Hand gesetzte Haken (siehe unten)
3. Offenes **Freigabefenster** (`freigabe_fenster.json`, `freigabefenster.py`)
4. `handel_erlaubt` gilt fuer **diesen** Modus: kein Demo-/Papierzwang im Code-Pfad
5. Guthaben in der Kontowaehrung ≥ `mindest_guthaben*`
6. Boersen-Schluessel vorhanden und **orderfaehig** (nicht read-only, richtige Umgebung)
7. Risikogrenzen/Deckel (Ratsche, `max_pro_trade`, Plaetze)

**Der Live-Modus wird nicht aus Chat oder A2A gesetzt.** Kein Befehl schaltet live; nur die
Freigabekette (Bildschirmfenster `freigabe.py` oder `/ja_<spur>` **im Dauerlauf**, auf eine
**wartende Anfrage**) plus `handel_erlaubt=true`.

**Wichtig und oft falsch erinnert:** `freigabe.erfuellt` ist **nur der von Hand gesetzte
Haken** — Wochen, Runden und „netto positiv" rechnet der Code NICHT. Diese Kriterien sind
Eingabe fuer die Entscheidung des Menschen, nicht Maschinenlogik.

## Arming-Sequenz (wenn eine Spur live soll)

1. `herzschlag_max_minuten` auf 180 (Live-Spuren muessen die PC-Ausfall-Luecke ueberleben).
2. `handel_erlaubt: true`.
3. `freigabe.erfuellt: true` (Haken).
4. `/ja_<spur>` **im Dauerlauf** (Fenster max. 24 h, nur auf Anfrage des Dauerlaufs;
   `/ja` ohne wartende Anfrage tut nichts).
5. Vorher: Schluessel-Test mit einem signierten LESEaufruf gegen den **Registry-Host**.

## AUTO_FREIGABE

`dauerlauf.pruefe_anfragen()` oeffnet die Fenster der Spuren aus `AUTO_FREIGABE` sofort selbst
(`freigegeben_von: auto`, 12 h), statt auf `/ja` zu warten. Sie greift **nur**, wenn
`nur_fenster_fehlt()` GENAU EINEN Sperrgrund nennt und darin das Wort **„Freigabefenster"**
vorkommt — also nur, wenn sonst nichts sperrt.

**Merksatz.** Wer eine Spur per AUTO_FREIGABE scharf haben will, muss dafuer sorgen, dass die
`--vorschau`-Zeile „Live waere gesperrt durch:" genau einen Grund nennt. Nennt sie zwei
(z. B. fehlendes Guthaben UND Fenster), greift die Auto-Freigabe nicht — richtig so.

**Beleg.** 21.09.2026: `xperp` 00:02 live, `scanner` 01:52 live, `mosaic` 06:58:40
Auto-Freigabe, Zyklus 07:11:27 „ok". `kraken` und frueher `mosaic` waren nicht durch das
Fenster gesperrt, sondern durch das **Guthaben in der richtigen Waehrung** („nur 33.15 EUR
frei, noetig 60.00", „nur 0.00 USDT frei, noetig 30.00").

## Punkt 3 hat ZWEI Formen — und eine kann still fehlen

Punkt 3 der Handelsregeln ("scharf geschaltet wird von Hand") ist zweimal umgesetzt,
und die Spur muss BEIDE kennen:

| Form | Modul | Wo sie greift |
|---|---|---|
| Freigabefenster am Bildschirm | `freigabe.py` (Tk) | jemand sitzt davor, bestaetigt je Einstieg |
| **Zeitfenster** | `freigabefenster.py` (`freigabe_fenster.json`) | Dauerbetrieb: `AUTO_FREIGABE` oder `/ja` am Handy |

**Unter `MAXHIRN_ROUTINE=1` ist `sitzung_da()` immer `False`** — und der Dauerlauf setzt
die Variable seit dem 21.09.2026 in BEIDEN Modi. Eine Spur, deren Sperrtext nur
`sitzung_da()` prueft, kann damit **im Dauerlauf nie live gehen**, egal wie oft ein Fenster
offen ist. Der Dauerlauf protokolliert trotzdem `<spur> (live) ok` — das ist SEIN Modus,
kein Beleg fuer eine Order.

**Beleg 21.09.2026 (mosaic):** Sperrtext `keine Sitzung am Bildschirm - Freigabefenster
nicht moeglich` → `nur_fenster_fehlt` sah "genau ein Grund, Wort Freigabefenster" →
oeffnete im 30-Minuten-Takt Fenster, die nichts bewirkten; das Journal hatte keine einzige
Live-Zeile. Zusaetzlich stand in `hole_freigabe()` `str(HIER.parent)`, obwohl `HIER` in
mosaic/handeln.py ein **String** ist (`os.path.dirname`) — `AttributeError` schon VOR dem
`try`, also "Freigabefenster nicht verfuegbar" und kein Einstieg, auch am Bildschirm.

**Messprobe (die einzige Wahrheit):** `<spurinterpreter> handeln.py --vorschau` **mit**
`MAXHIRN_ROUTINE=1` — genau so ruft der Dauerlauf sie. Steht dort "nicht offen - keine
Sitzung am Bildschirm und kein Zeitfenster", fehlt die zweite Form. Ohne die Variable
sieht dieselbe Spur frei aus.

## Wiedervorlage-Fristen

`freigabefenster.neue_anfrage_erlaubt()` verhindert, dass dieselbe Frage alle 30 Minuten
gestellt wird. Ohne diese Frist stand am 12.09.2026 um 19:06 eine Ablehnung und um 19:20
schon die naechste Frage. Eine unbeantwortete Anfrage **verfaellt**; ein `/ja` von gestern
Nacht ist keine Freigabe fuer heute frueh (`melder.leeren()` beim Start).

## Notaus

`/stop` schliesst alle Fenster; beendet sich der Dauerlauf (Strg+C), schliesst der
**Basislauf** alle Fenster (nie eine Stufe — sie wuerde dem Basislauf mitten im Handel die
Freigabe nehmen). Positionsschliessungen laufen ueber Stop-/Risikologik, **nicht** ueber den
Herzschlag (siehe [[Handel/Lektionen]]).

## Herzschlag

`herzschlag_max_minuten: 180` fuer alle Spuren (19.09.2026 von 45 angehoben). Grund: die
ungeklaerten Abschaltungen des Rechners (T-004) liessen die Luecke ueber 45 min wachsen, und
ein Fehlschluss der Live-Position waere Verlust in echtem Geld. Der Waechter startet einen
toten Lauf nach spaetestens 30 min neu, ein Zyklus dauert 1-2 min — eine Stoerung heilt nach
rund 32 min von selbst. **Jede Grenze darunter stellt bei JEDER Stoerung flach** (am
11./12.09.2026 mit 30 min in xperp/swap passiert). Wer eine Spur live nimmt, setzt 180
BEVOR `handel_erlaubt` auf `true` geht. Der Wert ist die Zahl in der `wachen.json`
(`_herzschlag_regel` ist nur Doku) und wirkt ohne Neustart.