"""
Utilitaires de calendrier de trading
Gestion des jours de marché (éviter les week-ends)
"""
from datetime import datetime, timedelta


def is_trading_day(date: datetime) -> bool:
    """
    Vérifie si une date est un jour de trading (lundi-vendredi)

    Args:
        date: Date à vérifier

    Returns:
        bool: True si c'est un jour de trading (lundi-vendredi)
    """
    # 0 = lundi, 6 = dimanche
    weekday = date.weekday()
    return weekday < 5  # Lundi (0) à vendredi (4)


def get_last_trading_day(date: datetime = None) -> datetime:
    """
    Retourne le dernier jour de trading avant ou égal à la date donnée

    Args:
        date: Date de référence (par défaut: aujourd'hui)

    Returns:
        datetime: Dernier jour de trading

    Examples:
        - Dimanche → Vendredi précédent
        - Samedi → Vendredi précédent
        - Lundi → Lundi (inchangé)
    """
    if date is None:
        date = datetime.now()

    while not is_trading_day(date):
        date = date - timedelta(days=1)

    return date


def adjust_date_range_for_trading(start: datetime, end: datetime) -> tuple:
    """
    Ajuste une plage de dates pour exclure les week-ends

    Args:
        start: Date de début
        end: Date de fin

    Returns:
        tuple: (start_adjusted, end_adjusted) où les deux sont des jours de trading

    Examples:
        - start=Samedi, end=Dimanche → start=Vendredi, end=Vendredi
        - start=Lundi, end=Vendredi → inchangé
    """
    start_adjusted = get_last_trading_day(start)
    end_adjusted = get_last_trading_day(end)

    # Vérifier que start <= end après ajustement
    if start_adjusted > end_adjusted:
        end_adjusted = start_adjusted

    return start_adjusted, end_adjusted


def get_trading_days_info(start: datetime, end: datetime) -> dict:
    """
    Retourne des informations sur les jours de trading dans une plage

    Args:
        start: Date de début
        end: Date de fin

    Returns:
        dict: Informations sur les jours de trading
    """
    start_adj, end_adj = adjust_date_range_for_trading(start, end)

    # Compter les jours de trading dans la plage
    current = start_adj
    trading_days = 0
    while current <= end_adj:
        if is_trading_day(current):
            trading_days += 1
        current += timedelta(days=1)

    return {
        'original_start': start,
        'original_end': end,
        'adjusted_start': start_adj,
        'adjusted_end': end_adj,
        'start_was_weekend': not is_trading_day(start),
        'end_was_weekend': not is_trading_day(end),
        'trading_days_count': trading_days,
        'date_range_days': (end_adj - start_adj).days + 1
    }
