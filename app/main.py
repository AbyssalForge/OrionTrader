from fastapi import FastAPI, Body
from utils.env_utils import DummyTradingEnv
from app.model.agent import TradingAgent
from app.model.monitor import DriftMonitor
from app.routes.model_routes import router as model_router

app = FastAPI(title="Trading RL API", version="2.0")

app.include_router(model_router)