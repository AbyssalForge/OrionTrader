#!/usr/bin/env python3
"""
Test du calendrier de trading (gestion des week-ends)
"""
from datetime import datetime
import sys
from pathlib import Path

# Ajouter le répertoire airflow au path
airflow_dir = Path(__file__).parent / "airflow"
sys.path.insert(0, str(airflow_dir))

from utils.trading_calendar import (
    is_trading_day,
    get_last_trading_day,
    adjust_date_range_for_trading,
    get_trading_days_info
)


def test_trading_calendar():
    print("=" * 70)
    print("TEST CALENDRIER DE TRADING")
    print("=" * 70)

    # Test 1: Jours de la semaine
    print("\n1. Test jours de la semaine:")
    test_dates = [
        ("2026-01-26", "Lundi"),
        ("2026-01-27", "Mardi"),
        ("2026-01-30", "Vendredi"),
        ("2026-01-31", "Samedi"),
        ("2026-02-01", "Dimanche"),
    ]

    for date_str, jour in test_dates:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        is_trading = is_trading_day(date)
        status = "Trading" if is_trading else "Week-end"
        print(f"   {date_str} ({jour}): {status}")

    # Test 2: Dernier jour de trading
    print("\n2. Test dernier jour de trading:")
    print(f"   Aujourd'hui: {datetime.now().date()}")
    last_trading = get_last_trading_day()
    print(f"   Dernier jour de trading: {last_trading.date()}")

    # Test 3: Ajustement de plage (cas problématique: vendredi -> dimanche)
    print("\n3. Test ajustement plage (30 janvier - 1er février 2026):")
    start = datetime(2026, 1, 30)  # Vendredi
    end = datetime(2026, 2, 1)     # Dimanche
    start_adj, end_adj = adjust_date_range_for_trading(start, end)
    print(f"   Original: {start.date()} -> {end.date()}")
    print(f"   Ajusté:   {start_adj.date()} -> {end_adj.date()}")

    # Test 4: Plage sur plusieurs semaines
    print("\n4. Test plage 2020-2022:")
    start = datetime(2020, 1, 1)
    end = datetime(2022, 1, 1)
    info = get_trading_days_info(start, end)
    print(f"   Original: {info['original_start'].date()} -> {info['original_end'].date()}")
    print(f"   Ajusté:   {info['adjusted_start'].date()} -> {info['adjusted_end'].date()}")
    print(f"   Jours de trading: {info['trading_days_count']}")
    print(f"   Plage totale: {info['date_range_days']} jours")

    print("\n" + "=" * 70)
    print("TEST TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    test_trading_calendar()
