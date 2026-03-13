"""
Misinfo Shield - API Server + Panel
=====================================
Serves the fact-checking panel at http://localhost:8899
and exposes API endpoints for the ML pipeline.

Usage:
    cd hack
    python api_server.py

Then open http://localhost:8899 in a small browser window and pin it.
"""

import sys
import os
import asyncio
import json
import hashlib
import logging
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ml-agent"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "ml-agent", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-28s | %(message)s",
    datefmt="%H:%M:%S",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

from agent.graph import graph

app = FastAPI(title="Misinfo Shield API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    claim_text: str
    source_platform: Optional[str] = "panel"
    source_url: Optional[str] = ""
    source_account: Optional[str] = "panel_user"


# ---- Serve the panel ----
PANEL_PATH = Path(__file__).parent / "extension" / "panel.html"


@app.get("/", response_class=HTMLResponse)
async def serve_panel():
    return PANEL_PATH.read_text(encoding="utf-8")


@app.get("/health")
async def health():
    from nodes.verdict import LLM_PROVIDER
    return {
        "status": "ok",
        "pipeline_nodes": len(graph.nodes),
        "llm_provider": LLM_PROVIDER,
    }


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    claim_id = "panel_" + hashlib.md5(req.claim_text[:100].encode()).hexdigest()[:10]

    claim_state = {
        "claim_id": claim_id,
        "original_text": req.claim_text,
        "source_platform": req.source_platform,
        "source_account_id": req.source_account,
        "source_post_url": req.source_url,
        "source_followers": 500,
        "media_urls": [],
        "engagement": {"likes": 0, "shares": 0, "comments": 0},
        "posted_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await graph.ainvoke(claim_state)
    verdict = result.get("verdict", {})

    return verdict


if __name__ == "__main__":
    import uvicorn

    print()
    print("  ============================================================")
    print("  MISINFO SHIELD - API Server + Panel")
    print("  ============================================================")
    print("  Panel: http://localhost:8899")
    print("  API  : http://localhost:8899/analyze")
    print("  ============================================================")
    print()

    # Auto-open removed for desktop app backend
    uvicorn.run(app, host="0.0.0.0", port=8899, log_level="info")
