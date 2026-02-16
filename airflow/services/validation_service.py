"""
Validation & Notification Service v3.0
Service de validation et notifications pour architecture 3 tables
"""

from datetime import datetime
import requests


def validate_data_quality(mt5_result: dict, yahoo_result: dict, docs_result: dict, snapshot_result: dict) -> dict:
    """
    Valide la qualité des données dans les 4 tables

    Args:
        mt5_result: Résultat load MT5 (table mt5_eurusd_m15)
        yahoo_result: Résultat load Yahoo (table yahoo_finance_daily)
        docs_result: Résultat load Documents (table documents_macro)
        snapshot_result: Résultat load Market Snapshot (table market_snapshot_m15)

    Returns:
        dict: Résultat validation (success/failed uniquement)

    Note:
        Validation simplifiée:
        - Vérifie que le chargement a réussi (status = success)
        - Vérifie qu'au moins 1 ligne a été chargée par table
        - Pas de seuils de lignes (adapté au mode quotidien J-2→J-1)
    """
    print("[VALIDATE] Validation des 4 tables...")

    errors = []
    tables_ok = 0

    print(f"[VALIDATE] Table 1/3: mt5_eurusd_m15")

    if mt5_result.get("status") != "success":
        errors.append(" Table MT5: Échec du chargement")
    else:
        mt5_rows = mt5_result.get("rows", 0)
        print(f"[VALIDATE]   → {mt5_rows} lignes chargées")

        if mt5_rows == 0:
            errors.append(" Table MT5: Aucune ligne chargée")
        else:
            tables_ok += 1
            print(f"[VALIDATE] Table MT5 OK")

    print(f"[VALIDATE] Table 2/3: yahoo_finance_daily")

    if yahoo_result.get("status") != "success":
        errors.append(" Table Yahoo: Échec du chargement")
    else:
        yahoo_rows = yahoo_result.get("rows", 0)
        print(f"[VALIDATE]   → {yahoo_rows} lignes chargées")

        if yahoo_rows == 0:
            errors.append(" Table Yahoo: Aucune ligne chargée")
        else:
            tables_ok += 1
            print(f"[VALIDATE] Table Yahoo OK")

    print(f"[VALIDATE] Table 3/4: documents_macro")

    if docs_result.get("status") != "success":
        errors.append(" Table Documents: Échec du chargement")
    else:
        docs_rows = docs_result.get("rows", 0)
        print(f"[VALIDATE]   → {docs_rows} lignes chargées")

        if docs_rows == 0:
            errors.append(" Table Documents: Aucune ligne chargée")
        else:
            tables_ok += 1
            print(f"[VALIDATE] Table Documents OK")

    print(f"[VALIDATE] Table 4/4: market_snapshot_m15")

    if snapshot_result.get("status") != "success":
        errors.append(" Table Snapshot: Échec du chargement")
    else:
        snapshot_rows = snapshot_result.get("rows", 0)
        print(f"[VALIDATE]   → {snapshot_rows} lignes chargées")

        if snapshot_rows == 0:
            errors.append(" Table Snapshot: Aucune ligne chargée")
        else:
            tables_ok += 1
            print(f"[VALIDATE] Table Snapshot OK")

    if errors:
        status = "failed"
        message = f" Pipeline échoué: {len(errors)} erreur(s)"
        emoji = ""
    else:
        status = "success"
        message = " Pipeline réussi"
        emoji = ""

    print(f"[VALIDATE] {message}")
    print(f"[VALIDATE] Tables OK: {tables_ok}/4")

    return {
        "status": status,
        "message": message,
        "emoji": emoji,
        "errors": errors,
        "tables_ok": tables_ok,
        "total_tables": 4,
        "mt5_rows": mt5_result.get("rows", 0),
        "yahoo_rows": yahoo_result.get("rows", 0),
        "docs_rows": docs_result.get("rows", 0),
        "snapshot_rows": snapshot_result.get("rows", 0),
        "total_rows": mt5_result.get("rows", 0) + yahoo_result.get("rows", 0) + docs_result.get("rows", 0) + snapshot_result.get("rows", 0),
    }


def send_discord_notification(validation_result: dict, webhook_url: str) -> dict:
    """
    Envoie une notification Discord avec résumé du pipeline

    Args:
        validation_result: Résultat de la validation
        webhook_url: URL du webhook Discord

    Returns:
        dict: Résultat de l'envoi
    """
    print("[NOTIFY] Envoi notification Discord...")

    emoji = validation_result.get("emoji", "")
    status = validation_result.get("status", "unknown")

    message = f"{emoji} **Pipeline ETL EURUSD terminé**\n\n"
    message += f"**Statut:** {validation_result.get('message', 'Inconnu')}\n"
    message += f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += f"**Tables validées:** {validation_result.get('tables_ok', 0)}/4\n\n"

    message += "** Données chargées:**\n"
    message += f"• Table MT5 (M15):         {validation_result.get('mt5_rows', 0):,} lignes\n"
    message += f"• Table Yahoo (Daily):     {validation_result.get('yahoo_rows', 0):,} lignes\n"
    message += f"• Table Documents (Var):   {validation_result.get('docs_rows', 0):,} lignes\n"
    message += f"• Table Snapshot (M15):    {validation_result.get('snapshot_rows', 0):,} lignes\n"
    message += f"• **Total:**               {validation_result.get('total_rows', 0):,} lignes\n"

    if validation_result.get("errors"):
        message += "\n** Erreurs:**\n"
        for error in validation_result["errors"]:
            message += f"• {error}\n"

    try:
        response = requests.post(
            webhook_url,
            json={"content": message},
            timeout=10
        )
        response.raise_for_status()

        print(f"[NOTIFY] Notification Discord envoyée (status: {status})")

        return {
            "status": "success",
            "message": "Notification envoyée",
            "discord_status_code": response.status_code
        }

    except requests.exceptions.Timeout:
        error_msg = "Timeout lors de l'envoi Discord"
        print(f"[NOTIFY] ️ {error_msg}")
        return {
            "status": "failed",
            "message": error_msg,
            "error": "timeout"
        }

    except requests.exceptions.RequestException as e:
        error_msg = f"Erreur HTTP: {str(e)}"
        print(f"[NOTIFY] ️ {error_msg}")
        return {
            "status": "failed",
            "message": error_msg,
            "error": str(e)
        }

    except Exception as e:
        error_msg = f"Erreur inattendue: {str(e)}"
        print(f"[NOTIFY] ️ {error_msg}")
        return {
            "status": "failed",
            "message": error_msg,
            "error": str(e)
        }

def send_wikipedia_notification(validation_result: dict, webhook_url: str) -> dict:
    """
    Envoie une notification Discord pour le scraping Wikipedia

    Args:
        validation_result: Résultat de la validation Wikipedia
        webhook_url: URL du webhook Discord

    Returns:
        dict: Résultat de l'envoi
    """
    print("[NOTIFY] Envoi notification Discord (Wikipedia)...")

    status = validation_result.get("status", "unknown")
    emoji = "" if status == "success" else ""

    message = f"{emoji} **Pipeline Scraping Wikipedia - Terminé**\n\n"
    message += f"**Statut:** {'Réussi' if status == 'success' else 'Échoué'}\n"
    message += f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"

    if validation_result.get('wikipedia_ok'):
        rows = validation_result.get('wikipedia_rows', 0)
        message += "** Données scrapées:**\n"
        message += f"• Indices: CAC 40, S&P 500, NASDAQ 100, DJIA\n"
        message += f"• Tickers uniques: {rows:,}\n"
        message += f"• Attendu: ~670 tickers\n\n"

        if validation_result.get('quality') == 'excellent':
            message += "** Qualité:** Excellente\n"
        elif validation_result.get('warning'):
            message += f"**️ Attention:** {validation_result.get('warning')}\n"

    if validation_result.get("error"):
        message += f"\n** Erreur:**\n• {validation_result['error']}\n"

    message += "\n** Source:** Wikipedia (scraping)\n"

    try:
        response = requests.post(webhook_url, json={"content": message}, timeout=10)
        response.raise_for_status()
        print(f"[NOTIFY] Notification Discord envoyée (Wikipedia)")
        return {"status": "success", "message": "Notification envoyée"}
    except Exception as e:
        print(f"[NOTIFY] ️ Erreur: {str(e)}")
        return {"status": "failed", "error": str(e)}
