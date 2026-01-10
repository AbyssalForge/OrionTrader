"""
Validation & Notification Service v3.0
Service de validation et notifications pour architecture 3 tables
"""

from datetime import datetime
import requests


def validate_data_quality(mt5_result: dict, yahoo_result: dict, docs_result: dict) -> dict:
    """
    Valide la qualité des données dans les 3 tables

    Args:
        mt5_result: Résultat load MT5 (table mt5_eurusd_m15)
        yahoo_result: Résultat load Yahoo (table yahoo_finance_daily)
        docs_result: Résultat load Documents (table documents_macro)

    Returns:
        dict: Résultat validation avec errors/warnings
    """
    print("[VALIDATE] Validation des 3 tables...")

    errors = []
    warnings = []
    tables_ok = 0

    # ========================================================================
    # VALIDATION TABLE 1: MT5
    # ========================================================================
    print(f"[VALIDATE] Table 1/3: mt5_eurusd_m15")

    if mt5_result.get("status") != "success":
        errors.append("❌ Table MT5: Échec du chargement")
    else:
        mt5_rows = mt5_result.get("rows", 0)
        print(f"[VALIDATE]   → {mt5_rows} lignes chargées")

        if mt5_rows == 0:
            errors.append("❌ Table MT5: Aucune ligne chargée")
        elif mt5_rows < 1000:
            warnings.append(f"⚠️ Table MT5: Peu de données ({mt5_rows} lignes, attendu >1000)")
        else:
            tables_ok += 1
            print(f"[VALIDATE]   ✓ Table MT5 OK")

    # ========================================================================
    # VALIDATION TABLE 2: YAHOO FINANCE
    # ========================================================================
    print(f"[VALIDATE] Table 2/3: yahoo_finance_daily")

    if yahoo_result.get("status") != "success":
        errors.append("❌ Table Yahoo: Échec du chargement")
    else:
        yahoo_rows = yahoo_result.get("rows", 0)
        print(f"[VALIDATE]   → {yahoo_rows} lignes chargées")

        if yahoo_rows == 0:
            errors.append("❌ Table Yahoo: Aucune ligne chargée")
        elif yahoo_rows < 100:
            warnings.append(f"⚠️ Table Yahoo: Peu de données ({yahoo_rows} lignes, attendu >100)")
        else:
            tables_ok += 1
            print(f"[VALIDATE]   ✓ Table Yahoo OK")

    # ========================================================================
    # VALIDATION TABLE 3: DOCUMENTS
    # ========================================================================
    print(f"[VALIDATE] Table 3/3: documents_macro")

    if docs_result.get("status") != "success":
        errors.append("❌ Table Documents: Échec du chargement")
    else:
        docs_rows = docs_result.get("rows", 0)
        print(f"[VALIDATE]   → {docs_rows} lignes chargées")

        if docs_rows == 0:
            errors.append("❌ Table Documents: Aucune ligne chargée")
        elif docs_rows < 10:
            warnings.append(f"⚠️ Table Documents: Peu de données ({docs_rows} lignes, attendu >10)")
        else:
            tables_ok += 1
            print(f"[VALIDATE]   ✓ Table Documents OK")

    # ========================================================================
    # STATUT FINAL
    # ========================================================================
    if errors:
        status = "failed"
        message = f"❌ Validation échouée: {len(errors)} erreur(s)"
        emoji = "❌"
    elif warnings:
        status = "success_with_warnings"
        message = f"⚠️ Pipeline réussi avec {len(warnings)} avertissement(s)"
        emoji = "⚠️"
    else:
        status = "success"
        message = "✅ Pipeline validé - Toutes les tables OK"
        emoji = "✅"

    print(f"[VALIDATE] {message}")
    print(f"[VALIDATE] Tables OK: {tables_ok}/3")

    return {
        "status": status,
        "message": message,
        "emoji": emoji,
        "errors": errors,
        "warnings": warnings,
        "tables_ok": tables_ok,
        "total_tables": 3,
        "mt5_rows": mt5_result.get("rows", 0),
        "yahoo_rows": yahoo_result.get("rows", 0),
        "docs_rows": docs_result.get("rows", 0),
        "total_rows": mt5_result.get("rows", 0) + yahoo_result.get("rows", 0) + docs_result.get("rows", 0),
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

    # ========================================================================
    # CONSTRUCTION MESSAGE
    # ========================================================================
    emoji = validation_result.get("emoji", "❓")
    status = validation_result.get("status", "unknown")

    # Header
    message = f"{emoji} **Pipeline ETL EURUSD v3.0 terminé**\n\n"
    message += f"**Statut:** {validation_result.get('message', 'Inconnu')}\n"
    message += f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    message += f"**Tables validées:** {validation_result.get('tables_ok', 0)}/3\n\n"

    # Données chargées
    message += "**📊 Données chargées:**\n"
    message += f"• Table MT5 (M15):         {validation_result.get('mt5_rows', 0):,} lignes\n"
    message += f"• Table Yahoo (Daily):     {validation_result.get('yahoo_rows', 0):,} lignes\n"
    message += f"• Table Documents (Var):   {validation_result.get('docs_rows', 0):,} lignes\n"
    message += f"• **Total:**               {validation_result.get('total_rows', 0):,} lignes\n"

    # Erreurs
    if validation_result.get("errors"):
        message += "\n**❌ Erreurs:**\n"
        for error in validation_result["errors"]:
            message += f"• {error}\n"

    # Warnings
    if validation_result.get("warnings"):
        message += "\n**⚠️ Avertissements:**\n"
        for warning in validation_result["warnings"]:
            message += f"• {warning}\n"

    # Footer
    if status == "success":
        message += "\n🎯 **Pipeline prêt pour export CSV**"

    # ========================================================================
    # ENVOI DISCORD
    # ========================================================================
    try:
        response = requests.post(
            webhook_url,
            json={"content": message},
            timeout=10
        )
        response.raise_for_status()

        print(f"[NOTIFY] ✓ Notification Discord envoyée (status: {status})")

        return {
            "status": "success",
            "message": "Notification envoyée",
            "discord_status_code": response.status_code
        }

    except requests.exceptions.Timeout:
        error_msg = "Timeout lors de l'envoi Discord"
        print(f"[NOTIFY] ⚠️ {error_msg}")
        return {
            "status": "failed",
            "message": error_msg,
            "error": "timeout"
        }

    except requests.exceptions.RequestException as e:
        error_msg = f"Erreur HTTP: {str(e)}"
        print(f"[NOTIFY] ⚠️ {error_msg}")
        return {
            "status": "failed",
            "message": error_msg,
            "error": str(e)
        }

    except Exception as e:
        error_msg = f"Erreur inattendue: {str(e)}"
        print(f"[NOTIFY] ⚠️ {error_msg}")
        return {
            "status": "failed",
            "message": error_msg,
            "error": str(e)
        }
