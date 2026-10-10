"""Kanal-Zustell-Test: gibt eine Zeile aus, die als Cron-Delivery im
Telegram-Kanal MaxHirn_Hermes (-1004430752246) ankommen muss.

Wiederverwendbar nach jeder Umkonfiguration: `hermes cron run kanal-test`
bzw. das gleiche ueber das cronjob-Tool. no_agent-Job, keine Seiteneffekte.
"""
import sys


def main() -> int:
    print("Cron-Kanal-Test: Zustellung an Kanal MaxHirn_Hermes funktioniert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
