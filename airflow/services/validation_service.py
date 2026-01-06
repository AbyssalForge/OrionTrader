"""
Validation & Notification Service - Business logic pour validation et alertes
"""

from datetime import datetime
import requests


def validate_data_quality(bronze_mt5: dict, bronze_stooq: dict, bronze_eurostat: dict, silver: dict):
    """
    Valide la qualité des données du pipeline

    Args:
        bronze_mt5: Résultat Bronze MT5
        bronze_stooq: Résultat Bronze Stooq
        bronze_eurostat: Résultat Bronze Eurostat
        silver: Résultat Silver

    Returns:
        dict: Résultat validation avec errors/warnings
    """
    print("[VALIDATE] Validation pipeline...")

    errors = []
    warnings = []

    # Vérifier statuts
    if bronze_mt5["status"] != "success":
        errors.append("Bronze MT5 échoué")
    if bronze_stooq["status"] != "success":
        errors.append("Bronze Stooq échoué")
    if bronze_eurostat["status"] != "success":
        errors.append("Bronze Eurostat échoué")
    if silver["status"] != "success":
        errors.append("Silver Features échoué")

    # Vérifier nombre de lignes
    if silver["rows"] < 100:
        errors.append(f"Trop peu de features: {silver['rows']} lignes")

    # Statut final
    if errors:
        status = "failed"
        message = f"❌ Validation échouée: {len(errors)} erreur(s)"
    elif warnings:
        status = "success_with_warnings"
        message = f"⚠ Validation réussie avec {len(warnings)} avertissement(s)"
    else:
        status = "success"
        message = "✅ Pipeline validé"

    print(f"[VALIDATE] {message}")

    return {
        "status": status,
        "message": message,
        "errors": errors,
        "warnings": warnings,
        "bronze_mt5_rows": bronze_mt5["rows"],
        "bronze_stooq_rows": bronze_stooq["rows"],
        "bronze_eurostat_rows": bronze_eurostat["rows"],
        "silver_rows": silver["rows"],
    }


def send_discord_notification(validation_result: dict, webhook_url: str):
    """
    Envoie une notification Discord

    Args:
        validation_result: Résultat de la validation
        webhook_url: URL du webhook Discord

    Returns:
        str: Status de l'envoi
    """
    status_emoji = {
        "success": "✅",
        "success_with_warnings": "⚠",
        "failed": "❌",
        "error": "🔥"
    }

    status = validation_result.get("status", "error")
    emoji = status_emoji.get(status, "❓")

    message = f"{emoji} **Pipeline ETL EURUSD v2 terminé**\n\n"
    message += f"**Statut:** {validation_result.get('message', 'Inconnu')}\n"
    message += f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    message += "**📊 Données chargées:**\n"
    message += f"• Bronze MT5: {validation_result.get('bronze_mt5_rows', 0)} lignes\n"
    message += f"• Bronze Stooq: {validation_result.get('bronze_stooq_rows', 0)} lignes\n"
    message += f"• Bronze Eurostat: {validation_result.get('bronze_eurostat_rows', 0)} lignes\n"
    message += f"• Silver Features: {validation_result.get('silver_rows', 0)} lignes\n"

    if validation_result.get("errors"):
        message += "\n**❌ Erreurs:**\n"
        for error in validation_result["errors"]:
            message += f"• {error}\n"

    try:
        response = requests.post(webhook_url, json={"content": message})
        response.raise_for_status()
        print(f"[NOTIFY] ✓ Notification Discord envoyée")
        return "Notification sent"
    except Exception as e:
        print(f"[NOTIFY] ⚠ Erreur: {e}")
        return f"Notification failed: {e}"
