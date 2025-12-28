from fastapi import APIRouter, HTTPException, BackgroundTasks
from executor_service.chatgpt_models import ChatGPTDropPayload
from configs.settings import settings
import json
import os
import datetime

router = APIRouter(prefix="/automation", tags=["Automation"])

AUTOMATION_DIR = "uploads/chatgpt_automation"
os.makedirs(AUTOMATION_DIR, exist_ok=True)

@router.post("/chatgpt-drop")
async def receive_chatgpt_drop(payload: ChatGPTDropPayload):
    """
    Dedicated endpoint for automated ChatGPT stock pick drops (JSON).
    """
    # 1. Security Check
    if payload.auth_token != settings.WEBHOOK_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid automation token")

    # 2. Save Drop to Disk (JSON)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{payload.batch_id}.json"
    filepath = f"{AUTOMATION_DIR}/{filename}"

    with open(filepath, "w") as f:
        json.dump(payload.dict(), f, indent=2)

    # 3. Log receipt
    print(f"Received ChatGPT Drop: {len(payload.picks)} symbols. Saved to {filepath}")

    return {
        "status": "success",
        "message": f"Received {len(payload.picks)} picks.",
        "batch_id": payload.batch_id,
        "saved_path": filepath
    }
