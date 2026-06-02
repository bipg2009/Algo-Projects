from fastapi import FastAPI, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import scanner_engine

app = FastAPI(title="STOCK FINDER API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/{scanner_type}/{category}")
def run_scan(scanner_type: str, category: str, timeframe: str = "daily"):
    if scanner_type == "breakout":
        results = scanner_engine.get_breakout_stocks(category.replace("_", " "), timeframe)
        return {"status": "success", "data": results}
    elif scanner_type == "value":
        results = scanner_engine.get_value_stocks(category.replace("_", " "), timeframe)
        return {"status": "success", "data": results}

# Mount static files for the frontend
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
