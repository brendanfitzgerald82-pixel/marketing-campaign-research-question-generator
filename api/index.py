"""
FastAPI entrypoint for Vercel. Exposes discovery and research_question_generator as routes.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .discovery import TOOLS
from .tools.research_question_generator import generate_questions

app = FastAPI(
    title="Research Question Generator",
    description="Generate 4C's research questions from a strategic brief.",
    version="1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/discovery")
def discovery():
    """Discovery endpoint: returns metadata for all tools. Served at /api/discovery."""
    return {
        "version": "1.0",
        "name": "Research Question Generator",
        "description": "Generate 4C's research questions from a strategic brief.",
        "tools": TOOLS,
    }


@app.post("/tools/research_question_generator")
def research_question_generator(body: dict):
    """Generate research questions from a strategic brief (POST body: { "brief": "..." })."""
    brief = body.get("brief") or body.get("brief_text") or ""
    if not brief or not isinstance(brief, str):
        raise HTTPException(
            status_code=400,
            detail="Body must include a string 'brief' or 'brief_text'.",
        )
    try:
        return generate_questions(brief)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
