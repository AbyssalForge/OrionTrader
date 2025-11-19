import shutil
import os

# --- Paramètres ---
SRC_FILE = "mql5/model_call.mq5"
MT5_PATH = os.path.expandvars(
    r"%APPDATA%\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\model_call.mq5"
)

# --- Copie automatique ---
os.makedirs(os.path.dirname(MT5_PATH), exist_ok=True)
shutil.copy2(SRC_FILE, MT5_PATH)

print(f"✅ Script MQL5 déployé vers MetaTrader : {MT5_PATH}")
