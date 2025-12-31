from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List
import shutil
import os
import datetime

router = APIRouter(prefix="/upload", tags=["Uploads"])

UPLOAD_DIR = "uploads"

# Ensure subdirectories exist
os.makedirs(f"{UPLOAD_DIR}/chatgpt", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/tradingview", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/finviz", exist_ok=True)

async def _save_file(file: UploadFile, source: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = f"{UPLOAD_DIR}/{source}/{safe_filename}"
    
    # Async Read/Write prevents blocking
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
        
    return file_path

@router.post("/chatgpt")
async def upload_chatgpt_csv(file: UploadFile = File(...)):
    """
    Endpoint for ChatGPT to drop analysis CSVs or watchlists.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")
        
    path = await _save_file(file, "chatgpt")
    return {"status": "success", "file_path": path, "message": "ChatGPT watchlist received"}

@router.post("/tradingview")
async def upload_tradingview_csv(file: UploadFile = File(...)):
    """
    Endpoint to upload exported TradingView watchlists.
    """
    if not file.filename.endswith('.csv'):
         raise HTTPException(status_code=400, detail="Only CSV files allowed")
         
    path = await _save_file(file, "tradingview")
    return {"status": "success", "file_path": path, "message": "TradingView export received"}

@router.post("/finviz")
async def upload_finviz_csv(file: UploadFile = File(...)):
    """
    Endpoint to upload exported Finviz screener results.
    """
    if not file.filename.endswith('.csv'):
         raise HTTPException(status_code=400, detail="Only CSV files allowed")
         
    path = await _save_file(file, "finviz")
    return {"status": "success", "file_path": path, "message": "Finviz screener data received"}

@router.get("/list")
async def list_uploads():
    """
    List all uploaded files organized by source.
    """
    results = {}
    for source in ["chatgpt", "tradingview", "finviz", "chatgpt_automation"]:
        dir_path = f"{UPLOAD_DIR}/{source}"
        if os.path.exists(dir_path):
            files = os.listdir(dir_path)
            # Filter for .csv or .json
            results[source] = [f for f in files if f.endswith('.csv') or f.endswith('.json')]
        else:
            results[source] = []
    return results
