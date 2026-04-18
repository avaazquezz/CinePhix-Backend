"""
Groq AI service — LLaMA 3.3 70B for all AI features.
- AI Concierge (chat)
- Semantic Search (query + TMDB data → ranked results)
- Smart Collections (criteria → movie list)
- Review Assistant (review text → feedback)
"""

import os
from typing import Optional

from groq import Groq, APIError

from app.config import settings

# Groq client (singleton)
_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


# ─── System prompts ───────────────────────────────────────────────────────────

SYSTEM_CONCIERGE = """You are CinePhix AI, the personal movie and TV show concierge.
You help users discover movies and series they'll love based on their taste, mood, and history.
You have access to TMDB data: overviews, ratings, genres, cast, and crew.
You also know the user's watchlist and favorites.
Be concise, specific, and enthusiastic about cinema.
If you recommend a movie, mention why it fits what they asked for.
Never spoiler beyond what is already public on TMDB."""

SYSTEM_REVIEW_ASSISTANT = """You are a movie review assistant helping users improve their reviews.
Given their draft, you provide 2-3 concise, actionable suggestions.
Focus on: clarity, specificity, avoiding early spoilers, and constructive critique.
Do NOT rewrite the review. Do NOT be generic. Be specific to their content."""

SYSTEM_SMART_COLLECTION = """You are a movie curation assistant.
Given a user's collection (watchlist, favorites, ratings) and a theme/criteria,
suggest the best movies from TMDB that fit the theme.
You must respond ONLY with a valid JSON array of TMDB movie IDs (integers).
Example: [550, 238, 680]
No markdown, no explanation, just the JSON array."""


# ─── AI Concierge ────────────────────────────────────────────────────────────

async def ai_concierge_chat(
    user_message: str,
    user_history: list[dict] | None = None,
    watchlist_titles: list[str] | None = None,
    favorites_titles: list[str] | None = None,
    language: str = "en",
) -> str:
    """
    Natural language chat about movies/TV.
    Uses Groq LLaMA 3.3 70B with context from user's watchlist and favorites.
    """
    client = get_groq_client()

    # Build context from user data
    context_parts = []
    if watchlist_titles:
        context_parts.append(f"User's watchlist: {', '.join(watchlist_titles[:20])}")
    if favorites_titles:
        context_parts.append(f"User's favorites: {', '.join(favorites_titles[:20])}")

    context = (
        f"User context: {' | '.join(context_parts)}\n\n"
        if context_parts
        else ""
    )

    # Build message history for context window
    messages = [{"role": "system", "content": SYSTEM_CONCIERGE}]
    if context:
        messages.append({"role": "system", "content": context})

    if user_history:
        for h in user_history[-6:]:  # last 6 turns
            messages.append({"role": h.get("role", "user"), "content": h["content"]})

    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.8,
            max_tokens=1024,
        )
        return response.choices[0].message.content.strip()
    except APIError as e:
        raise RuntimeError(f"Groq API error: {e}")


# ─── Semantic Search ──────────────────────────────────────────────────────────

async def semantic_search(
    query: str,
    tmdb_movies: list[dict],
    top_k: int = 10,
) -> list[dict]:
    """
    Given a natural language query and a list of TMDB movie dicts,
    return the movies that best match, ranked by relevance.
    tmdb_movies: [{tmdb_id, title, overview, genres, vote_average, ...}, ...]
    """
    if not tmdb_movies:
        return []

    client = get_groq_client()

    # Serialize movie list for the prompt
    movies_text = "\n".join(
        f"{m['tmdb_id']}. {m['title']} ({m.get('release_year','?')}) — "
        f"rating={m.get('vote_average',0):.1f}, genres={m.get('genres','')}, "
        f"overview={m.get('overview','N/A')[:200]}"
        for m in tmdb_movies[:50]  # cap at 50 for cost control
    )

    prompt = f"""Given this search query: "{query}"

And these movies:
{movies_text}

Select the {top_k} that best match the query. Consider title, genres, rating, and overview.
Respond ONLY with a JSON array of the selected movie IDs (integers), ordered by relevance.
Example: [238, 550, 680]
No markdown, no explanation, just the JSON array."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a movie search relevance assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()

        # Parse JSON array
        import json
        import re

        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            return tmdb_movies[:top_k]  # fallback

        ids = json.loads(match.group(0))
        id_to_movie = {m["tmdb_id"]: m for m in tmdb_movies}

        # Preserve order from Groq response
        ranked = [id_to_movie[mid] for mid in ids if mid in id_to_movie]
        return ranked[:top_k]

    except Exception as e:
        raise RuntimeError(f"Semantic search failed: {e}")


# ─── Smart Collections ────────────────────────────────────────────────────────

SMART_COLLECTION_TEMPLATES = {
    "hidden_gems": "Underrated movies (vote_average 7-8.2) that didn't get much attention",
    "critics_favorites": "Highest rated movies (vote_average > 8.3) by critics",
    "moody": "Dark, atmospheric thriller and drama movies",
    "feel_good": "Uplifting, fun, feel-good comedies and adventures",
    "marathon": "Movies with runtime under 2 hours for a quick watch session",
    "epic": "Movies with runtime over 2.5 hours for a long movie night",
    "rewatchables": "Movies with vote_average > 7.5 that are considered classics",
    "trending_now": "Popular movies from the last 12 months",
    "similar_to": "Movies similar to a given title (user provides title name)",
}


async def generate_smart_collection(
    theme: str,
    user_favorites_titles: list[str] | None = None,
    tmdb_movies: list[dict] | None = None,
    limit: int = 15,
) -> list[int]:
    """
    Generate a "Smart Collection" — a list of TMDB movie IDs matching a theme.
    tmdb_movies: full TMDB discover results to pick from
    Returns: list of TMDB movie IDs
    """
    client = get_groq_client()

    context = ""
    if user_favorites_titles:
        context = f"\nUser's favorite movies: {', '.join(user_favorites_titles[:10])}"

    prompt = f"""Theme: "{theme}"
{context}

From the following TMDB movies, select the {limit} best matches for this theme.
Respond ONLY with a JSON array of TMDB movie IDs (integers).
Movies:
{chr(10).join(f"- {m.get('title','?')} ({m.get('release_year','?')}) rating={m.get('vote_average',0):.1f}" for m in (tmdb_movies or [])[:50])}

Respond with JSON array only."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_SMART_COLLECTION},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=256,
        )
        raw = response.choices[0].message.content.strip()

        import json, re
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            return []
        return json.loads(match.group(0))

    except Exception as e:
        raise RuntimeError(f"Smart collection generation failed: {e}")


# ─── Review Assistant ──────────────────────────────────────────────────────────

async def review_assistant_feedback(review_text: str, media_title: str) -> dict:
    """
    Analyze a draft review and return constructive feedback.
    Returns: { suggestions: [string], spoiler_flag: bool, rating_alignment: str }
    """
    client = get_groq_client()

    prompt = f"""You are a movie review assistant. 
A user just wrote this review for "{media_title}":
---
{review_text}
---

Provide feedback in JSON format:
{{
  "suggestions": ["suggestion 1", "suggestion 2"],
  "spoiler_flag": true/false,
  "rating_alignment": "match" | "high" | "low" (does the text match the implied rating?)
}}

Be specific. If the review is already strong, say so briefly."""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_REVIEW_ASSISTANT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()

        import json, re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            return {"suggestions": [], "spoiler_flag": False, "rating_alignment": "match"}
        return json.loads(match.group(0))

    except Exception as e:
        raise RuntimeError(f"Review assistant failed: {e}")
