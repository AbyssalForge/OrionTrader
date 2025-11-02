from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain.tools import tool
from typing import TypedDict

from app.model.agent import TradingAgent
from app.utils.env_utils import DummyTradingEnv

# Ton agent RL
env = DummyTradingEnv()
agent = TradingAgent(env)

# === Étape 1 : Observation du marché ===
def get_market_observation(state):
    # Exemple : retourne un vecteur [variation, volume]
    print(state)
    obs = [state["price_change"], state["volume_change"]]
    return {"observation": obs}

# === Étape 2 : Décision du modèle RL ===
def decide_action(state):
    obs = state["observation"]
    action = agent.predict(obs)
    print(f"🧠 Action prédite : {action}")
    return {"action": action}

# === Étape 3 : Exécution via API de trading ===
@tool
def execute_trade(action: int):
    """Exécute un trade via MetaTrader 5 ou autre API"""
    if action == 1:
        print("💹 Achat exécuté")
        # mt5.order_send(...)
    elif action == 2:
        print("📉 Vente exécutée")
        # mt5.order_send(...)
    else:
        print("⏸️ Attente")
    return {"action": action}

# === Construction du graphe ===

class TradingState(TypedDict):
    price_change: float # prix EUR/USD
    volume_change: float # variation depuis la dernière observation
    observation: list[float]
    action: int | None

graph = StateGraph(state_schema=TradingState)

graph.add_node("observe", get_market_observation)
graph.add_node("decide", decide_action)
graph.add_node("execute", execute_trade)

graph.add_edge("observe", "decide")
graph.add_edge("decide", "execute")
graph.add_edge("execute", END)

graph.set_entry_point("observe")

# === Exemple d'exécution ===
app_trading_graph  = graph.compile()