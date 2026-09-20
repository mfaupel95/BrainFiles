"""
DCA-Agent: verwaltet mehrere Sparplaene und BEREITET Kaeufe vor.

Was er tut:
  - haelt beliebig viele Plaene (Token, Betrag, Intervall, Kette) in plan.json
  - sagt, welcher Plan faellig ist
  - holt eine echte Quote und rechnet die Gesamtkosten aus
  - prueft den Zieltoken auf Honeypot, Einfrierrechte und aehnliches
  - gleicht die eigene Buchfuehrung gegen den echten Wallet-Bestand ab
  - legt den fertigen Befehl vor

Was er NICHT tut: ausloesen. Kein Swap, keine Order, keine Signatur. Der letzte
Schritt gehoert dem Menschen - der ausgegebene Befehl wird bewusst nur
angezeigt, nicht ausgefuehrt.

Aufruf:
    python agent.py init --name btc --kette solana --betrag 200 --intervall monat
    python agent.py status                       # alle Plaene
    python agent.py vorbereiten --plan btc
    python agent.py vorbereiten --plan btc --limit --abschlag 5
    python agent.py erledigt --plan btc --menge 0.0031
    python agent.py check                        # fuer Routinen, schweigt sonst
    python agent.py abgleich
"""

import argparse
import json
import shutil
import subprocess
import os
import sys
from datetime import date, datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PLAN = Path(__file__).resolve().parent / "plan.json"
FORMAT_VERSION = 2

# Contract-Adressen fest hinterlegt, NICHT ueber Symbole aufloesen. Grund: Zu
# jedem bekannten Symbol existieren Nachbauten mit gleichem Namen und fast
# gleichem Preis, aber ohne Liquiditaet - auf Solana gibt es ein zweites "WBTC"
# mit 55.206 USD statt 664 Mio. Am 10.08.2026 geprueft.
TOKEN = {
    "solana": {
        "USDC": ("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", 1_192_834_698),
        # Zwei BTC-Varianten mit UNTERSCHIEDLICHER Risikoart, beide MEDIUM:
        # WBTC ist "Wrapped BTC (Wormhole)" - Verwahrung liegt bei der Bridge,
        # die 2022 gehackt wurde. cbBTC verwahrt Coinbase; dafuer traegt es
        # zusaetzlich isHasFrozenAuth, das Guthaben kann eingefroren werden.
        # Keine der beiden ist "sicher", sie sind unterschiedlich riskant.
        "WBTC": ("3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh", 664_124_947),
        "cbBTC": ("cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij", 21_659_723),
        # SOL ist auf Solana das NATIVE Asset - kein Bridge-Risiko, im
        # Unterschied zu WBTC und WETH, die beide ueber Wormhole laufen.
        "SOL": ("11111111111111111111111111111111", 5_121_856_736),
        "WETH": ("7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs", 670_219_469),
        # ACHTUNG bei XRP: Von sechs Suchtreffern mit diesem Symbol sind
        # mindestens zwei voellig andere Token - darunter ein Meme-Coin namens
        # "HarryPotterObamaPacman8INU", der schlicht das Symbol XRP fuehrt.
        # Nur diese Adresse ist "Wrapped XRP" mit nennenswerter Liquiditaet,
        # und selbst die ist mit 0,87 Mio USD duenn (cbBTC: 21,7 Mio).
        "wXRP": ("6UpQcMAb5xMzxc7ZfPaVMgx3KqsvKZdT5U718BzD5We2", 865_584),
    },
    "ethereum": {
        "USDC": ("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", 15_218_193_378),
        "WBTC": ("0x2260fac5e5542a773aa44fbcfedf7c193bc2c599", 4_630_330_763),
    },
}

# Welche Kursreihe zu welchem Token gehoert. Der Backtest rechnet auf dem
# Basiswert - ein Wrapper folgt dem Kurs, traegt aber zusaetzlich das Risiko
# seines Verwahrers. Das steckt in keiner Kursreihe und wird separat gemeldet.
TICKER = {
    "WBTC": "BTC-USD", "cbBTC": "BTC-USD",
    "SOL": "SOL-USD", "WETH": "ETH-USD", "wXRP": "XRP-USD",
}

INTERVALL_TAGE = {"woche": 7, "monat": 30, "quartal": 91}

RISIKO_FLAGS = {
    "isHoneypot": "Honeypot - Verkauf blockiert",
    "isCounterfeit": "Fälschung eines bekannten Tokens",
    "isFakeLiquidity": "vorgetäuschte Liquidität",
    "isLowLiquidity": "geringe Liquidität",
    "isMintable": "nachprägbar (Menge kann erhöht werden)",
    "isNotRenounced": "Rechte des Erstellers nicht abgegeben",
    "isHasFrozenAuth": "Guthaben kann eingefroren werden",
    "isLiquidityRemoval": "Liquidität wurde abgezogen",
    "isNotOpenSource": "Quellcode nicht offen",
    "isDumping": "Erstellerbestand wird abverkauft",
}


# --- CLI-Anbindung ------------------------------------------------------

def onchainos(*args):
    """Ruft die CLI auf. Hartes Zeitlimit, damit ein haengender Aufruf nicht
    den Agenten blockiert."""
    try:
        if os.name == "nt":
            proc = subprocess.run(
                ["onchainos", *args], capture_output=True, timeout=120,
                creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            proc = subprocess.run(["onchainos", *args], capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Zeitlimit überschritten"}
    except FileNotFoundError:
        return {"ok": False, "error": "onchainos nicht gefunden"}
    text = proc.stdout.decode("utf-8", errors="replace").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        fehler = proc.stderr.decode("utf-8", errors="replace").strip()
        return {"ok": False, "error": fehler or text[:200] or "keine Antwort"}


def token_pruefen(kette, adresse):
    """Sicherheitsscan. Gibt (riskLevel, [Klartext-Befunde]) zurueck."""
    chain_id = {"solana": "501", "ethereum": "1"}.get(kette, kette)
    r = onchainos("security", "token-scan", "--tokens", f"{chain_id}:{adresse}")
    if not r.get("ok") or not r.get("data"):
        return None, [f"Scan fehlgeschlagen: {r.get('error', 'keine Daten')}"]
    d = r["data"][0]
    befunde = [text for flag, text in RISIKO_FLAGS.items() if d.get(flag)]
    for seite in ("buyTaxes", "sellTaxes"):
        try:
            if float(d.get(seite) or 0) > 0:
                befunde.append(f"{seite} = {d[seite]}")
        except (TypeError, ValueError):
            pass
    return d.get("riskLevel"), befunde


# --- Datei laden, speichern, migrieren ----------------------------------

def datei_laden():
    if not PLAN.exists():
        print("Kein Plan vorhanden. Erst anlegen:")
        print("  python agent.py init --name btc --kette solana --betrag 200")
        sys.exit(1)
    d = json.loads(PLAN.read_text(encoding="utf-8"))

    # Migration von Version 1 (genau ein Plan als flaches Objekt). Die alte
    # Datei wird vorher gesichert - ein Plan enthaelt die Kaufhistorie und
    # laesst sich nicht rekonstruieren.
    if "plaene" not in d:
        sicherung = PLAN.with_suffix(".json.v1")
        shutil.copy2(PLAN, sicherung)
        name = d.get("nach", {}).get("symbol", "plan").lower()
        d = {"version": FORMAT_VERSION, "plaene": [{**d, "name": name}]}
        PLAN.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Plan auf das neue Format umgestellt (Name: {name}).")
        print(f"  Alte Fassung gesichert: {sicherung.name}\n")
    return d


def datei_speichern(d):
    d["version"] = FORMAT_VERSION
    PLAN.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def plan_waehlen(d, name, pflicht=True):
    """Loest --plan auf. Ohne Angabe und bei genau einem Plan wird dieser
    genommen; bei mehreren muss der Name genannt werden, damit nicht
    versehentlich der falsche Sparplan angefasst wird."""
    plaene = d["plaene"]
    if not plaene:
        print("Keine Pläne vorhanden.")
        sys.exit(1)
    if name is None:
        if len(plaene) == 1:
            return plaene[0]
        if pflicht:
            print("Mehrere Pläne vorhanden - bitte --plan angeben:")
            for p in plaene:
                print(f"  {p['name']}")
            sys.exit(1)
        return None
    treffer = [p for p in plaene if p["name"] == name]
    if not treffer:
        treffer = [p for p in plaene if p["name"].startswith(name)]
    if len(treffer) == 1:
        return treffer[0]
    if not treffer:
        print(f"Kein Plan namens '{name}'. Vorhanden: "
              f"{', '.join(p['name'] for p in plaene)}")
    else:
        print(f"'{name}' ist mehrdeutig: {', '.join(p['name'] for p in treffer)}")
    sys.exit(1)


def faellig_seit(p):
    """Tage seit Faelligkeit. Negativ heisst: noch nicht dran."""
    hist = p.get("historie", [])
    if not hist:
        return 0, None
    letzte = datetime.fromisoformat(hist[-1]["datum"]).date()
    vergangen = (date.today() - letzte).days
    return vergangen - INTERVALL_TAGE[p["intervall"]], letzte


# --- Befehle ------------------------------------------------------------

def cmd_init(args):
    d = json.loads(PLAN.read_text(encoding="utf-8")) if PLAN.exists() else {}
    if "plaene" not in d:
        d = datei_laden() if PLAN.exists() else {"version": FORMAT_VERSION, "plaene": []}

    if args.kette not in TOKEN or args.token not in TOKEN[args.kette]:
        print(f"{args.token} auf {args.kette} nicht hinterlegt. Verfügbar: "
              f"{', '.join(TOKEN.get(args.kette, {}))}")
        sys.exit(1)

    name = args.name or args.token.lower()
    if any(p["name"] == name for p in d["plaene"]):
        if not args.ueberschreiben:
            print(f"Plan '{name}' existiert bereits. Mit --ueberschreiben ersetzen "
                  f"(die Kaufhistorie geht dabei verloren).")
            sys.exit(1)
        d["plaene"] = [p for p in d["plaene"] if p["name"] != name]

    von, von_liq = TOKEN[args.kette]["USDC"]
    nach, nach_liq = TOKEN[args.kette][args.token]
    d["plaene"].append({
        "name": name,
        "kette": args.kette,
        "von": {"symbol": "USDC", "adresse": von, "liquiditaet_bei_anlage": von_liq},
        "nach": {"symbol": args.token, "adresse": nach, "liquiditaet_bei_anlage": nach_liq},
        "betrag_usd": args.betrag,
        "intervall": args.intervall,
        "max_kosten_prozent": args.max_kosten,
        # Der CLI-Standard fuer Limit-Orders liegt bei 15 % - fuer einen
        # Sparplan viel zu weit. 0,5 % passt zu den gemessenen Impact-Werten
        # (0,04-0,06 % auf Solana) und laesst Luft bis zur Ausfuehrung.
        "slippage_prozent": args.slippage,
        "angelegt": date.today().isoformat(),
        "historie": [],
    })
    datei_speichern(d)
    print(f"Plan '{name}' angelegt: {args.betrag} USDC → {args.token} "
          f"je {args.intervall} auf {args.kette}")
    print(f"  Kostengrenze {args.max_kosten} %, Slippage {args.slippage} %")

    stufe, befunde = token_pruefen(args.kette, nach)
    print(f"\n  Sicherheitsscan {args.token}: Risikostufe {stufe}")
    for b in befunde:
        print(f"    - {b}")
    if stufe and stufe.upper() not in ("LOW", "SAFE", "NONE"):
        print(f"\n  Vor der ersten Tranche ansehen: agent.py pruefen --plan {name}")


def cmd_entfernen(args):
    d = datei_laden()
    p = plan_waehlen(d, args.plan)
    if p["historie"] and not args.trotzdem:
        print(f"Plan '{p['name']}' hat {len(p['historie'])} eingetragene Tranchen. "
              f"Mit --trotzdem wirklich entfernen.")
        sys.exit(1)
    d["plaene"] = [x for x in d["plaene"] if x["name"] != p["name"]]
    datei_speichern(d)
    print(f"Plan '{p['name']}' entfernt.")


def _plan_zeile(p):
    name = p["name"] if len(p["name"]) <= 11 else p["name"][:10] + "…"
    if p.get("typ") == "grid":
        # Grid-Plaene haben kein Intervall und keine Faelligkeit - sie laufen
        # ueber platzierte Orders, nicht ueber einen Kalender.
        spanne = f"{p['unten']:,.0f}-{p['oben']:,.0f}"
        return (f"  {name:<12}{p['nach']['symbol']:<7}{p['kette']:<10}"
                f"{p['kapital_usd']:>7.0f}/{p['stufen']} Stufen"
                f"{len(p['historie']):>4}{spanne:>22}{'Grid':>13}")
    hist = p["historie"]
    ueber, letzte = faellig_seit(p)
    if not hist:
        faellig = "ja (erste)"
    elif ueber >= 0:
        faellig = f"ja (+{ueber} T)"
    else:
        faellig = f"in {-ueber} T"
    gesamt = sum(h["betrag_usd"] for h in hist)
    menge = sum(h.get("menge", 0) for h in hist)
    basis = f"{gesamt / menge:,.0f}" if menge else "-"
    return (f"  {name:<12}{p['nach']['symbol']:<7}{p['kette']:<10}"
            f"{p['betrag_usd']:>7.0f}/{p['intervall']:<9}{len(hist):>4}"
            f"{gesamt:>10,.0f}{basis:>12}{faellig:>13}")


def cmd_status(args):
    d = datei_laden()
    p = plan_waehlen(d, args.plan, pflicht=False)
    plaene = [p] if p else d["plaene"]

    print(f"\n  {'Plan':<12}{'Token':<7}{'Kette':<10}{'Rate':>7} {'Intervall':<9}"
          f"{'Tr.':>4}{'Gesamt':>10}{'Basis':>12}{'Fällig':>13}")
    print("  " + "-" * 84)
    for x in plaene:
        print(_plan_zeile(x))

    o = onchainos("strategy", "list")
    if o.get("ok"):
        offen = o["data"].get("list", [])
        print(f"\n  Offene Limit-Orders: {len(offen)}")
        for eintrag in offen[:5]:
            print(f"    {eintrag}")
    else:
        print(f"\n  Offene Orders nicht abrufbar ({o.get('error')})")
    print()


def cmd_check(args):
    """Fuer Routinen gedacht: schweigt, wenn nichts ansteht. Eine Routine, die
    jeden Tag meldet 'nichts zu tun', wird nach einer Woche ignoriert."""
    d = datei_laden()
    faellige = []
    # Grid-Plaene haben keine Faelligkeit - sie laufen ueber platzierte Orders.
    for p in [x for x in d["plaene"] if x.get("typ") != "grid"]:
        ueber, _ = faellig_seit(p)
        if not p["historie"] or ueber >= 0:
            faellige.append((p, ueber))
    if not faellige:
        if args.laut:
            offen = [-faellig_seit(p)[0] for p in d["plaene"] if p.get("typ") != "grid"]
            naechste = min(offen, default=0)
            print(f"Nichts fällig. Nächste Tranche in {naechste} Tagen.")
        return
    for p, ueber in faellige:
        wieviel = "erste Tranche" if not p["historie"] else f"fällig seit {ueber} Tagen"
        print(f"DCA '{p['name']}' ({p['nach']['symbol']}): {wieviel} — "
              f"{p['betrag_usd']} {p['von']['symbol']} auf {p['kette']}.")
    print(f"Vorbereiten:  python agent.py vorbereiten --plan <name>")


def cmd_pruefen(args):
    d = datei_laden()
    p = plan_waehlen(d, args.plan, pflicht=False)
    for x in ([p] if p else d["plaene"]):
        stufe, befunde = token_pruefen(x["kette"], x["nach"]["adresse"])
        print(f"\n{x['name']} — {x['nach']['symbol']} auf {x['kette']}: {stufe}")
        for b in befunde or ["keine Auffälligkeiten"]:
            print(f"    - {b}")
    print()


def cmd_abgleich(args):
    """Vergleicht die Buchfuehrung mit dem echten Wallet-Bestand. Der Plan weiss
    nur, was eingetragen wurde - wer eine Order platziert und `erledigt`
    vergisst, laesst beide auseinanderlaufen."""
    d = datei_laden()
    p = plan_waehlen(d, args.plan, pflicht=False)
    for x in ([p] if p else d["plaene"]):
        gebucht = sum(h.get("menge", 0) for h in x["historie"])
        r = onchainos("wallet", "balance", "--chain", x["kette"],
                      "--token-address", x["nach"]["adresse"])
        print(f"\n{x['name']} — {x['nach']['symbol']} auf {x['kette']}")
        if not r.get("ok"):
            print(f"  Bestand nicht abrufbar: {r.get('error')}")
            continue
        echt = preis = 0.0
        for detail in r["data"].get("details", []):
            for a in detail.get("tokenAssets", []):
                if a["tokenAddress"].lower() == x["nach"]["adresse"].lower():
                    echt = float(a["balance"])
                    preis = float(a.get("tokenPrice") or 0)
        print(f"  Laut Plan       {gebucht:.8f}   ({len(x['historie'])} Tranchen)")
        print(f"  Im Wallet       {echt:.8f}")
        diff = echt - gebucht
        if abs(diff) < 1e-9:
            print("  Stimmt überein.")
        elif diff > 0:
            print(f"  Abweichung      {diff:+.8f}")
            print("    Mehr im Wallet als gebucht — vermutlich eine ausgeführte")
            print(f"    Tranche nicht eingetragen: agent.py erledigt --plan {x['name']} --menge <X>")
        else:
            print(f"  Abweichung      {diff:+.8f}")
            print("    Weniger im Wallet als gebucht — verkauft, übertragen,")
            print("    oder eine Order wurde doch nicht ausgeführt.")
        if preis and echt:
            wert = echt * preis
            eingesetzt = sum(h["betrag_usd"] for h in x["historie"])
            print(f"  Wert            {wert:,.2f} USD")
            if eingesetzt:
                print(f"  Eingesetzt      {eingesetzt:,.2f} USD   ({wert / eingesetzt - 1:+.1%})")
    print()


def cmd_grid_init(args):
    """Legt einen Grid-Plan an. Anderer Typ als ein DCA-Plan: kein Intervall,
    dafuer Preisspanne, Stufen und Gesamtkapital."""
    import grid as grid_modul

    d = datei_laden() if PLAN.exists() else {"version": FORMAT_VERSION, "plaene": []}
    if args.kette not in TOKEN or args.token not in TOKEN[args.kette]:
        print(f"{args.token} auf {args.kette} nicht hinterlegt.")
        sys.exit(1)
    if args.unten >= args.oben:
        print("Untere Grenze muss kleiner als obere sein.")
        sys.exit(1)

    name = args.name or f"grid-{args.token.lower()}"
    if any(p["name"] == name for p in d["plaene"]):
        if not args.ueberschreiben:
            print(f"Plan '{name}' existiert bereits. Mit --ueberschreiben ersetzen.")
            sys.exit(1)
        d["plaene"] = [p for p in d["plaene"] if p["name"] != name]

    von, von_liq = TOKEN[args.kette]["USDC"]
    nach, nach_liq = TOKEN[args.kette][args.token]
    preise = grid_modul.stufen_bauen(args.unten, args.oben, args.stufen)
    d["plaene"].append({
        "name": name,
        "typ": "grid",
        "kette": args.kette,
        "von": {"symbol": "USDC", "adresse": von, "liquiditaet_bei_anlage": von_liq},
        "nach": {"symbol": args.token, "adresse": nach, "liquiditaet_bei_anlage": nach_liq},
        "unten": args.unten,
        "oben": args.oben,
        "stufen": args.stufen,
        "kapital_usd": args.kapital,
        "slippage_prozent": args.slippage,
        "angelegt": date.today().isoformat(),
        "historie": [],
    })
    datei_speichern(d)
    je_stufe = args.kapital / (args.stufen - 1)
    print(f"Grid '{name}' angelegt: {args.kapital:g} USDC auf {args.stufen} Stufen "
          f"zwischen {args.unten:,.2f} und {args.oben:,.2f}")
    print(f"  {je_stufe:,.2f} USDC je Kaufstufe, Abstand "
          f"{(preise[1] / preise[0] - 1) * 100:.2f} %")

    # Der Stufenabstand muss die Kosten eines vollstaendigen Zyklus (Kauf UND
    # Verkauf) klar uebersteigen, sonst verliert das Grid unabhaengig vom Kurs.
    anteil, fix = dca_kosten(args.kette)
    zyklus_kosten = 2 * (je_stufe * anteil + fix)
    gewinn = je_stufe * (preise[1] / preise[0] - 1)
    print(f"  Gewinn je Zyklus {gewinn:,.2f} USD, Kosten {zyklus_kosten:,.2f} USD")
    if gewinn <= zyklus_kosten * 2:
        print("\n  WARNUNG: Der Stufengewinn liegt nicht klar über den Kosten.")
        print("  Weniger Stufen oder eine breitere Spanne wählen.")


def dca_kosten(kette):
    import dca
    return dca.KOSTEN.get(kette, dca.KOSTEN["keine"])


def cmd_grid_orders(args):
    """Legt die Kauf-Orders des Grids vor: alle Stufen unterhalb des aktuellen
    Kurses. Verkaufs-Orders kommen erst, wenn eine Stufe tatsaechlich gekauft
    wurde - vorher gibt es nichts zu verkaufen."""
    import grid as grid_modul

    d = datei_laden()
    p = plan_waehlen(d, args.plan)
    if p.get("typ") != "grid":
        print(f"'{p['name']}' ist kein Grid-Plan.")
        return

    q = onchainos("swap", "quote", "--chain", p["kette"],
                  "--from", p["von"]["adresse"], "--to", p["nach"]["adresse"],
                  "--readable-amount", "100")
    if not q.get("ok"):
        print(f"Kurs nicht abrufbar: {q.get('error')}")
        return
    kurs = float(q["data"][0]["toToken"]["tokenUnitPrice"])

    preise = grid_modul.stufen_bauen(p["unten"], p["oben"], p["stufen"])
    kauf_stufen = [x for x in preise[:-1] if x < kurs]
    je_stufe = p["kapital_usd"] / (p["stufen"] - 1)
    slippage = p.get("slippage_prozent", 0.5)

    print(f"\n[{p['name']}]  {p['nach']['symbol']} steht bei {kurs:,.2f}")
    print(f"  Gitter {p['unten']:,.2f} – {p['oben']:,.2f}, {p['stufen']} Stufen, "
          f"{je_stufe:,.2f} USDC je Stufe")

    if not kauf_stufen:
        print("\n  Keine Kaufstufe unter dem aktuellen Kurs — der Kurs steht unter")
        print("  der Gitterspanne oder darüber. Nichts zu platzieren.")
        return
    print(f"  {len(kauf_stufen)} Kaufstufen unter dem Kurs, Bedarf "
          f"{len(kauf_stufen) * je_stufe:,.2f} USDC\n")

    for i, preis in enumerate(reversed(kauf_stufen), 1):
        ziel = next(x for x in preise if x > preis)
        print(f"  {i}. Kauf bei {preis:,.2f}  → Verkaufsziel {ziel:,.2f} "
              f"({(ziel / preis - 1) * 100:.2f} %)")

    print("\n  Nichts wurde ausgelöst. Zum Platzieren jede Order einzeln aufrufen:\n")
    for preis in reversed(kauf_stufen):
        print(f"    onchainos strategy create-limit --chain-id {p['kette']} "
              f"--from-token {p['von']['adresse']} --to-token {p['nach']['adresse']} "
              f"--amount {je_stufe:.2f} --trigger-price {preis:.2f} "
              f"--direction buy --slippage {slippage} --mev-protection on")
    print("\n  Danach: onchainos strategy list")
    print("  Wird eine Kauf-Order ausgeführt, gehört die zugehörige Verkaufs-Order")
    print(f"  auf die nächsthöhere Stufe gelegt (--direction sell).\n")


def cmd_backtest(args):
    """Rechnet GENAU DIESEN Plan auf historischen Kursen durch - mit dem
    eingestellten Betrag, Intervall und den gemessenen Swap-Kosten seiner
    Kette. Verbindet die Buchfuehrung mit dem Simulator."""
    import dca
    import kursdaten

    d = datei_laden()
    p = plan_waehlen(d, args.plan)
    sym = p["nach"]["symbol"]
    ticker = TICKER.get(sym)
    if not ticker:
        print(f"Für {sym} ist keine Kursreihe hinterlegt.")
        return

    df, quelle = kursdaten.laden(ticker, still=True)
    kette = p["kette"] if p["kette"] in dca.KOSTEN else "keine"
    print(f"\n[{p['name']}]  {p['betrag_usd']:g} USDC je {p['intervall']} "
          f"→ {sym}, Kurse aus {ticker} ({quelle})")
    print(f"  Swap-Kosten der Kette {kette} sind eingerechnet.\n")

    erg = dca.rollierend(df, p["betrag_usd"], p["intervall"], 1,
                         args.dauer, "isoliert", dca.FINANZIERUNG_PA, kette)
    if not erg:
        print(f"  Zu wenig Historie für {args.dauer} Monate Haltedauer.")
        return
    renditen = sorted(r for _, r, _, _ in erg)
    n = len(renditen)
    print(f"  Haltedauer      {args.dauer} Monate, {n} mögliche Startzeitpunkte")
    print(f"  Median          {renditen[n // 2]:+.0%}")
    print(f"  Schlechtestes   {renditen[0]:+.0%}")
    print(f"  Bestes          {renditen[-1]:+.0%}")
    verlust = sum(1 for r in renditen if r < 0)
    print(f"  Im Minus        {verlust} von {n}  ({verlust / n:.0%})")

    # Ein Durchlauf ueber die volle Historie, damit die Kostenwirkung sichtbar wird.
    voll = dca.simuliere(df, p["betrag_usd"], p["intervall"], 1,
                         df.index[0], df.index[-1], kette=kette)
    if voll["swap_kosten"]:
        anteil = voll["swap_kosten"] / voll["eingezahlt"]
        print(f"\n  Über die volle Historie ({voll['tranchen']} Tranchen):")
        print(f"  Swap-Kosten     {dca.euro(voll['swap_kosten'])} USD "
              f"({anteil:.1%} des Eingezahlten)")
    print(f"\n  Historie, nicht Prognose. {sym} folgt dem {ticker}-Kurs, trägt")
    print("  aber zusätzlich das Risiko seines Verwahrers — das steckt in")
    print("  keiner Kursreihe. Siehe: agent.py pruefen\n")


def cmd_vorbereiten(args):
    d = datei_laden()
    p = plan_waehlen(d, args.plan)
    if p.get("typ") == "grid":
        print(f"'{p['name']}' ist ein Grid-Plan. Orders vorlegen mit:")
        print(f"  python agent.py grid-orders --plan {p['name']}")
        return
    ueber, _ = faellig_seit(p)
    if p["historie"] and ueber < 0 and not args.trotzdem:
        print(f"'{p['name']}' noch nicht fällig (in {-ueber} Tagen). "
              f"Mit --trotzdem erzwingen.")
        return

    betrag = args.betrag or p["betrag_usd"]
    print(f"\n[{p['name']}]  Quote: {betrag} {p['von']['symbol']} → "
          f"{p['nach']['symbol']} auf {p['kette']} ...")

    q = onchainos("swap", "quote", "--chain", p["kette"],
                  "--from", p["von"]["adresse"], "--to", p["nach"]["adresse"],
                  "--readable-amount", str(betrag))
    if not q.get("ok"):
        print(f"  Quote fehlgeschlagen: {q.get('error')}")
        return

    dat = q["data"][0]
    dez = int(dat["toToken"]["decimal"])
    menge = int(dat["toTokenAmount"]) / 10 ** dez
    preis = float(dat["toToken"]["tokenUnitPrice"])
    fee = float(dat.get("tradeFee") or 0)
    impact = float(dat.get("priceImpactPercent") or 0)
    gas = dat.get("estimateGasFee", "?")

    # Negativer Impact (guenstiger als Referenzkurs) wird NICHT gutgeschrieben.
    # Sonst koennte eine momentane Kursdelle die Kostengrenze aushebeln, obwohl
    # die Gebuehren unveraendert anfallen.
    kosten_pct = (fee / betrag * 100) + max(0.0, impact)
    grenze = p["max_kosten_prozent"]
    slippage = p.get("slippage_prozent", 0.5)

    print(f"\n  Kaufen          {menge:.8f} {p['nach']['symbol']}")
    print(f"  Kurs            {preis:,.2f} USD")
    print(f"  Router-Gebühr   {fee:,.2f} USD")
    print(f"  Preis-Impact    {impact:.3f} %")
    print(f"  Gas (Einheiten) {gas}")
    print(f"  Kosten gesamt   {kosten_pct:.3f} %  (Grenze {grenze} %)")

    if dat["toToken"].get("isHoneyPot"):
        print("\n  ABBRUCH: Zieltoken ist als Honeypot markiert.")
        return
    if kosten_pct > grenze:
        print("\n  WARNUNG: Kosten über der Grenze. Größere Tranche oder "
              "längeres Intervall senkt den Anteil.")

    if args.limit:
        # Limit-Order statt Marktkauf: Trigger liegt um --abschlag unter dem
        # aktuellen Kurs. Ausgefuehrt wird erst, wenn der Kurs dorthin faellt -
        # die Tranche kann also auch liegenbleiben.
        trigger = preis * (1 - args.abschlag / 100)
        print(f"\n  Limit-Order bei {trigger:,.2f} USD "
              f"({args.abschlag:g} % unter {preis:,.2f})")
        print(f"  Slippage        {slippage:g} %   (CLI-Standard wäre 15 %)")
        print("\n  Nichts wurde ausgelöst. Zum Platzieren selbst aufrufen:\n")
        print(f"    onchainos strategy create-limit --chain-id {p['kette']} \\")
        print(f"      --from-token {p['von']['adresse']} \\")
        print(f"      --to-token {p['nach']['adresse']} \\")
        print(f"      --amount {betrag} \\")
        print(f"      --trigger-price {trigger:.2f} \\")
        print("      --direction buy \\")
        print(f"      --slippage {slippage} \\")
        print("      --mev-protection on")
        print("\n  Offene Orders ansehen:  onchainos strategy list\n")
        return

    print(f"  Slippage        {slippage:g} %   (CLI-Standard wäre 15 %)")
    print("\n  Nichts wurde ausgelöst. Zum Ausführen selbst aufrufen:\n")
    print(f"    onchainos swap execute --chain {p['kette']} \\")
    print(f"      --from {p['von']['adresse']} \\")
    print(f"      --to {p['nach']['adresse']} \\")
    print(f"      --readable-amount {betrag}")
    print(f"\n  Danach eintragen:  python agent.py erledigt "
          f"--plan {p['name']} --menge {menge:.8f}\n")


def cmd_erledigt(args):
    d = datei_laden()
    p = plan_waehlen(d, args.plan)
    betrag = args.betrag or p["betrag_usd"]
    p["historie"].append({
        "datum": args.datum or date.today().isoformat(),
        "betrag_usd": betrag,
        "menge": args.menge,
        "kurs": betrag / args.menge if args.menge else None,
    })
    datei_speichern(d)
    print(f"'{p['name']}': {args.menge} {p['nach']['symbol']} eingetragen. "
          f"Jetzt {len(p['historie'])} Tranchen.")


def main():
    ap = argparse.ArgumentParser(description="DCA-Agent (bereitet vor, löst nicht aus)")
    sub = ap.add_subparsers(dest="befehl", required=True)

    i = sub.add_parser("init", help="Plan anlegen")
    i.add_argument("--name", default=None, help="Kurzname (Standard: Tokensymbol)")
    i.add_argument("--kette", default="solana", choices=list(TOKEN))
    i.add_argument("--token", default="WBTC")
    i.add_argument("--betrag", type=float, default=200)
    i.add_argument("--intervall", default="monat", choices=list(INTERVALL_TAGE))
    i.add_argument("--max-kosten", type=float, default=1.0,
                   help="Kostengrenze in Prozent der Tranche (Standard 1.0)")
    i.add_argument("--slippage", type=float, default=0.5,
                   help="Slippage für Limit-Orders (Standard 0.5, CLI-Standard wäre 15)")
    i.add_argument("--ueberschreiben", action="store_true")
    i.set_defaults(func=cmd_init)

    s = sub.add_parser("status", help="Stand aller Pläne")
    s.add_argument("--plan", default=None)
    s.set_defaults(func=cmd_status)

    v = sub.add_parser("vorbereiten", help="Quote holen und Kauf vorlegen")
    v.add_argument("--plan", default=None)
    v.add_argument("--betrag", type=float, default=None)
    v.add_argument("--trotzdem", action="store_true", help="auch wenn nicht fällig")
    v.add_argument("--limit", action="store_true", help="Limit-Order statt Marktkauf")
    v.add_argument("--abschlag", type=float, default=5.0,
                   help="Trigger in Prozent unter dem aktuellen Kurs (Standard 5)")
    v.set_defaults(func=cmd_vorbereiten)

    e = sub.add_parser("erledigt", help="ausgeführte Tranche eintragen")
    e.add_argument("--plan", default=None)
    e.add_argument("--menge", type=float, required=True)
    e.add_argument("--betrag", type=float, default=None)
    e.add_argument("--datum", default=None)
    e.set_defaults(func=cmd_erledigt)

    c = sub.add_parser("check", help="still prüfen, ob etwas fällig ist (für Routinen)")
    c.add_argument("--laut", action="store_true", help="auch melden, wenn nichts ansteht")
    c.set_defaults(func=cmd_check)

    a = sub.add_parser("abgleich", help="Pläne gegen echten Wallet-Bestand prüfen")
    a.add_argument("--plan", default=None)
    a.set_defaults(func=cmd_abgleich)

    pr = sub.add_parser("pruefen", help="Sicherheitsscan der Zieltoken")
    pr.add_argument("--plan", default=None)
    pr.set_defaults(func=cmd_pruefen)

    gi = sub.add_parser("grid-init", help="Grid-Plan anlegen")
    gi.add_argument("--name", default=None)
    gi.add_argument("--kette", default="solana", choices=list(TOKEN))
    gi.add_argument("--token", default="cbBTC")
    gi.add_argument("--unten", type=float, required=True)
    gi.add_argument("--oben", type=float, required=True)
    gi.add_argument("--stufen", type=int, default=8)
    gi.add_argument("--kapital", type=float, default=2000)
    gi.add_argument("--slippage", type=float, default=0.5)
    gi.add_argument("--ueberschreiben", action="store_true")
    gi.set_defaults(func=cmd_grid_init)

    go = sub.add_parser("grid-orders", help="Kauf-Orders des Grids vorlegen")
    go.add_argument("--plan", default=None)
    go.set_defaults(func=cmd_grid_orders)

    b = sub.add_parser("backtest", help="diesen Plan auf historischen Kursen rechnen")
    b.add_argument("--plan", default=None)
    b.add_argument("--dauer", type=int, default=18, help="Haltedauer in Monaten")
    b.set_defaults(func=cmd_backtest)

    rm = sub.add_parser("entfernen", help="Plan löschen")
    rm.add_argument("--plan", default=None)
    rm.add_argument("--trotzdem", action="store_true", help="auch mit Historie")
    rm.set_defaults(func=cmd_entfernen)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
