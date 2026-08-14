# ./backend/main.py
"""
uvicorn main:app --reload
"""
import os
import sys
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path



# Fix for Windows — Playwright requires ProactorEventLoop on Windows

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from apis.leadscores              import router as leadscores_router
from apis.dashboard               import router as dashboard_router
from apis.ICP                     import router as icp_router
from apis.ICP.ScoreConfig         import router as icp_score_router
from apis.Persona.ScoreConfig     import router as persona_router
from apis.Persona.GeneratePersona import router as generate_persona_router
from apis.Authentication          import router as auth_router
from apis.Onboarding              import router as onboarding_router

from apis.context_engine.routes   import router as context_router
from apis.Intellegence.product_context import router as product_context_router


from apis.Context.context import router as contexts_router

from apis.mcp_icp_router import router as mcp_icp_router

from apis.mcp_buyer_group_router import router as mcp_buyer_group_router
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(leadscores_router)
app.include_router(dashboard_router)
app.include_router(icp_router,              prefix="/leadscores/scoring")
app.include_router(icp_score_router,        prefix="/leadscores/icp/scoring")
app.include_router(persona_router,          prefix="/leadscores/persona")
app.include_router(generate_persona_router, prefix="/leadscores/persona")
app.include_router(auth_router)
app.include_router(onboarding_router)


app.include_router(product_context_router)   # add right after mcp_buyer_group_router

app.include_router(contexts_router)
app.include_router(context_router)
app.include_router(mcp_icp_router)
app.include_router(mcp_buyer_group_router)
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "LeadScoring API running"}