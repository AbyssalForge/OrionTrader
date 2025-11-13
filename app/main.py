from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, List
import pandas as pd
from app.utils.inference import load_model, run_inference

app = FastAPI()
model = load_model("models/orion_model.zip")

class PredictRequest(BaseModel):
    data: Dict[str, List[float]]  # chaque colonne -> liste de valeurs

@app.post("/predict")
def predict(request: PredictRequest):
    df = pd.DataFrame(request.data)
    result = run_inference(model, df)
    last_action = result["actions"][-1] if result["actions"] else 0
    action_label = {1.0: "BUY", -1.0: "SELL", 0.0: "HOLD"}.get(last_action, "HOLD")
    return {
        "status": "success",
        "action": action_label,
        "action_code": last_action,
        "total_reward": result["total_reward"],
        "steps": result["n_steps"]
    }
