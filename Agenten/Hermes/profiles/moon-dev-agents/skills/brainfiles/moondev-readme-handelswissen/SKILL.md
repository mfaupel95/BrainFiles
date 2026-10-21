---
name: moondev-readme-handelswissen
description: Moon-Dev GUI READMEs into Handelswissen überführen.
version: 1.0.0
author: moon-dev-agents
license: MIT
metadata:
  hermes:
    tags: [brainfiles, moondev, readme, handelswissen]
    related_skills: []
---

# Moon-Dev README → Handelswissen

## When to Use

Wenn die moon-dev-GUI (moongui.py) verknüpfte README-Dateien ins Handelswissen
unter Wissen/Handelsregeln.md überführt werden sollen.

## Ablauf

1. GUI-Dateien lesen: `moongui.py`, `START_GUI.bat`
   - GUI sucht READMEs via `os.walk(REPO)` mit Pruning (.venv, .git, etc.)
   - Filter: Dateiname beginnt mit "README"
2. README-Dateien im Repo finden:
   - `find . -name "README*" -not -path "./.venv/*" -not -path "./.git/*"`
3. Inhalt extrahieren und strukturieren
4. Ziel: `Wissen/Handelsregeln.md` im BrainFiles-Repo (ergänzen, nicht ersetzen)
5. `.gitignore` Whitelist: `!Wissen/Handelsregeln.md` (Grundsatzregel `*` blockiert alles)
6. Commit in BrainFiles

## Kernaussagen der READMEs

- 47 Agenten: Trading, Strategy, Risk, Copy, Whale, Sentiment, Listingarb,
  Liquidation, Chart, Funding, Fundingarb, RBI, Twitter, Video, New/Top,
  Chat, Clips, Phone, Sniper, TX, Solana, Million, TikTok, Compliance, Research
- Model Factory: OpenAI, Claude, Gemini, Groq, DeepSeek, Ollama (lokal)
- Strategie-System: BaseStrategy, generate_signals(), Signal-Format
- RBI-Swarm: 54 Sub-Agenten, SPARC-Methodologie
- Börsen: OKX, Kraken, Binance + Solana Wallet
- Sicherheit: Order-Limits, private Keys nie gespeichert

## Commit

BrainFiles, Commit e470ddff (13.10.2026).
