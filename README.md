# 🛰️ OrionTrader
OrionTrader est un agent de trading intelligent basé sur **l’apprentissage par renforcement (PPO)**, conçu pour interagir directement avec **MetaTrader 5** via une passerelle **FastAPI ↔ MQL5**. 
Son objectif : apprendre à **acheter, vendre ou attendre** sur le marché **EUR/USD** afin de maximiser les profits tout en gérant le risque.

## 🚀 Fonctionnalités principales

- 🤖 **Agent PPO (Proximal Policy Optimization) —** entraînement par renforcement continu sur données de marché.
- 🔗 **Pont MQL5 ↔ FastAPI ↔ Python —** communication bidirectionnelle entre MetaTrader et l’IA.
- 💰 **Trading automatique sur EUR/USD —** l’agent apprend à acheter ou vendre en temps réel.
- 📈 **Simulation et stratégie testing —** intégration possible avec le module Strategy Tester de MetaTrader 5.
- 🧩 **Architecture modulaire —** séparation propre entre environnement RL, API, et modèle.
- 🧠 **Logs et visualisations d’apprentissage —** suivi des performances et des récompenses de l’agent.

## 🏗️ Architecture

```bash
MetaTrader5 (MQL5)
        ⬍
   FastAPI Bridge
        ⬍
   Python RL Agent (PPO)
        ⬍
  Historique & Environnement Forex
```

## ⚙️ Technologies principales

- Python 3.10+
- FastAPI
- MetaTrader5 (MQL5 Bridge)
- Stable-Baselines3 (PPO)
- Pandas / NumPy / Matplotlib
- Docker (optionnel pour le déploiement)

## 🧪 Objectif d’apprentissage

L’agent Orion apprend à :

- Observer l’état du marché (prix, tendances, indicateurs techniques)
- Prendre une action (BUY, SELL, HOLD)
- Recevoir une récompense basée sur le profit net
- S’améliorer via plusieurs itérations d’entraînement

## 💡 Vision

> “Comme Orion guide les navigateurs, OrionTrader guide vos décisions de marché avec la précision d’un modèle d’apprentissage par renforcement.”
