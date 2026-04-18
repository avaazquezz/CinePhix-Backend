"""
AI Concierge router — Semantic Search, AI Chat, Smart Collections, Review Assistant.
All powered by Groq LLaMA 3.3 70B.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, OptionalUser, DBSession
from app.services import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)
    language: str = Field(default="en", pattern="^(en|es)$")


class ChatResponse(BaseModel):
    reply: str


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    movies: list[dict]  # [{tmdb_id, title, overview, genres, vote_average, release_year}, ...]
    top_k: int = Field(default=10, ge=1, le=30)


class SmartCollectionRequest(BaseModel):
    theme: str = Field(..., min_length=1, max_length=200)
    movies: list[dict] = Field(default_factory=list)
    limit: int = Field(default=15, ge=1, le=30)


class ReviewAssistantRequest(BaseModel):
    review_text: str = Field(..., min_length=10, max_length=5000)
    media_title: str = Field(...)


# ─── AI Concierge ──────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    body: ChatRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Natural language chat about movies/TV.
    Personalized with the user's watchlist and favorites.
    """
    try:
        reply = await ai_service.ai_concierge_chat(
            user_message=body.message,
            user_history=[h.model_dump() for h in body.history],
            watchlist_titles=None,
            favorites_titles=None,
            language=body.language,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ChatResponse(reply=reply)


# ─── Semantic Search ────────────────────────────────────────────────────────────

@router.post("/search")
async def semantic_search(
    body: SemanticSearchRequest,
    current_user: OptionalUser,
    db: DBSession,
):
    """
    Natural language search over a set of movies.
    Useful for filtering/searching within a user's list, trending page, etc.
    No auth required (but personalized if logged in).
    """
    try:
        results = await ai_service.semantic_search(
            query=body.query,
            tmdb_movies=body.movies,
            top_k=body.top_k,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"results": results, "query": body.query}


# ─── Smart Collections ───────────────────────────────────────────────────────────

SMART_THEMES = {
    "hidden_gems": "Underrated movies (rating 7-8.2) that didn't get much attention",
    "critics_favorites": "Highest rated movies (rating > 8.3) by critics",
    "moody": "Dark, atmospheric thriller and drama movies",
    "feel_good": "Uplifting, fun, feel-good comedies and adventures",
    "marathon": "Movies with runtime under 2 hours for a quick watch",
    "epic": "Movies over 2.5 hours for a long movie night",
    "rewatchables": "Classics with rating > 7.5 worth watching again",
    "trending_now": "Popular movies from the last 12 months",
    "similar_to": "Movies similar to a given title",
    "winter_2024": "Best movies released in winter 2024 season",
    "summer_2025": "Best movies released in summer 2025 season",
}


@router.get("/collections/themes")
async def list_collection_themes():
    """List available Smart Collection themes."""
    return {"themes": list(SMART_THEMES.keys())}


@router.post("/collections/generate")
async def generate_collection(
    body: SmartCollectionRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Generate a Smart Collection of TMDB movie IDs based on a theme.
    """
    try:
        movie_ids = await ai_service.generate_smart_collection(
            theme=body.theme,
            user_favorites_titles=None,
            tmdb_movies=body.movies,
            limit=body.limit,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"theme": body.theme, "movie_ids": movie_ids}


# ─── Review Assistant ───────────────────────────────────────────────────────────

@router.post("/review/feedback")
async def review_feedback(
    body: ReviewAssistantRequest,
    current_user: CurrentUser,
    db: DBSession,
):
    """
    Get AI feedback on a draft review before publishing.
    """
    try:
        feedback = await ai_service.review_assistant_feedback(
            review_text=body.review_text,
            media_title=body.media_title,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return feedback
