from fastapi import FastAPI, Body
from app.utils.env_utils import DummyTradingEnv
from app.model.agent import TradingAgent
from app.model.monitor import DriftMonitor
from app.routes.model_routes import router as model_router
import uvicorn

app = FastAPI(
    title="OrionTrader API",
    description="API de trading avec surveillance de drift et ré-entraînement",
    version="1.0.0"
)

# Ajout des routes du modèle
app.include_router(model_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)