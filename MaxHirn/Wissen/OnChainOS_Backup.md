---
id: 20260908-onchainos-backup
title: 'OnChainOS Backup'
tags: [sicherheit, archiv]
created: 2026-09-08
updated: 2026-09-08
related: [20260830-schutzregeln]
summary: 'Archivierte OnChainOS-Konfiguration (Identität, Wallet-Konfiguration, Session) vom 08.09.2026: Herkunft, Inhalt und Aufbewahrungsort.'
---

# OnChainOS Backup

## Status
- **Archiviert:** 08.09.2026
- **Herkunft:** `../Modelle/.onchainos/` (OnChainOS-Konfiguration)
- **Zweck:** Identität, Wallet-Konfiguration, Session-Schlüssel
- **Aufbewahrung:** Archiv/OnChainOS_Backup_20260908/

## Inhalt
- `wallets.json` - Projekt-ID, Account-ID, Wallet-Adressen auf 30+ Chains (ETH, Solana, etc.)
- `machine-identity` - Maschinen-Identität (SHA-256 Hash)
- `session.json` - Session-Zertifikat, verschlüsselter Session-Key, Ablaufdatum (2027-01-18)
- `keyring.enc` - Verschlüsseltes Keyring
- `audit.jsonl`, `chain_cache.json`, `balance_cache.json` - Caches
- `workflows/` - Workflow-Definitionen
- `bin/` - Binärdateien

## Wichtige Daten
- **Projekt-ID:** agentic-wallet-project01
- **Account-ID:** 05c0d7a8-4f81-47b9-8d0d-c563e7d61738
- **Wallet:** 0x353535416cd196881d3bb36cbe37e37e0a674dbc (Ethereum und 30+ Chains)
- **Solana-Adresse:** 3x6YiDY2CQkQDJxHzeQqYfFPCXw1Qu9zT2RMo5j1Qbjv
- **Login-Typ:** Apple
- **Session-Expires:** 2027-01-18 (Unix-Zeitstempel 1795010549)

## Hinweise
- `session.json` enthält verschlüsselte Session-Schlüssel - bei Bedarf neu generieren
- `keyring.enc` ist verschlüsselt und erfordert Zugriff auf das Original-Keyring
- Nach Wiederherstellung: Session neu authentifizieren
