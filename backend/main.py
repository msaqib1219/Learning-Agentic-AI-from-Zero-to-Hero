import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types
import json
import re
from qdrant_client import QdrantClient
from contextlib import asynccontextmanager

from database import init_db, add_message, get_history
from auth import verify_api_key, verify_auth, check_rate_limit, rate_limiter, get_client_identifier
from auth_server import router as auth_router, init_auth_db

# Load environment variables FIRST (override=True to override system env vars)
load_dotenv(override=True)

# Configure Gemini AFTER loading .env
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not set — chat endpoints will fail")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

# Initialize clients
QDRANT_URL = os.getenv("QDRANT_URL")
if QDRANT_URL:
    qdrant_client = QdrantClient(
        url=QDRANT_URL,
        api_key=os.getenv("QDRANT_API_KEY"),
    )
else:
    print("WARNING: QDRANT_URL not set — chat endpoints will fail")
    qdrant_client = None

COLLECTION_NAME = "agentic_ai_book"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await init_auth_db()
        await init_db()
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)

# CORS configuration
ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")]
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
if FRONTEND_URL not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(FRONTEND_URL)
print(f"CORS allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

# Include auth routes
app.include_router(auth_router)

class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    sources: List[str]

class ProfileUpdate(BaseModel):
    experienceLevel: Optional[str] = None
    programmingLanguages: Optional[str] = None
    aiMlFamiliarity: Optional[str] = None
    hardwareExperience: Optional[str] = None
    learningGoals: Optional[str] = None
    questionnaireCompleted: Optional[bool] = None

def get_embedding(text: str) -> List[float]:
    """Generate embedding using Gemini"""
    result = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text
    )
    return result.embeddings[0].values


def extract_json_from_response(text: str) -> str:
    """Extract JSON from text response if present"""
    text = re.sub(r'```json\n?', '', text)
    text = re.sub(r'```\n?', '', text)
    return text.strip()

@app.get("/api/health")
async def health_check():
    """Health check endpoint - no auth required."""
    return {"status": "healthy", "service": "rag-chatbot"}


@app.get("/api/rate-limit-status")
async def rate_limit_status(request: Request, api_key: str = Depends(verify_api_key)):
    """Check current rate limit status for the client."""
    identifier = get_client_identifier(request)
    remaining = rate_limiter.get_remaining(identifier)
    return {
        "identifier": identifier,
        "limits": {
            "per_minute": rate_limiter.requests_per_minute,
            "per_hour": rate_limiter.requests_per_hour,
        },
        "remaining": remaining,
    }


@app.get("/api/user/profile")
async def get_profile(auth_payload: dict = Depends(verify_auth)):
    """Get current user's profile including questionnaire data."""
    return {
        "id": auth_payload.get("sub"),
        "email": auth_payload.get("email"),
        "name": auth_payload.get("name"),
        "experienceLevel": auth_payload.get("experienceLevel", ""),
        "programmingLanguages": auth_payload.get("programmingLanguages", ""),
        "aiMlFamiliarity": auth_payload.get("aiMlFamiliarity", ""),
        "hardwareExperience": auth_payload.get("hardwareExperience", ""),
        "learningGoals": auth_payload.get("learningGoals", ""),
        "questionnaireCompleted": auth_payload.get("questionnaireCompleted", False),
    }


@app.post("/api/user/profile")
async def update_profile(
    profile: ProfileUpdate,
    auth_payload: dict = Depends(verify_auth),
):
    """Update user questionnaire fields in better-auth user table."""
    import asyncpg

    user_id = auth_payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    updates = {}
    if profile.experienceLevel is not None:
        updates['"experienceLevel"'] = profile.experienceLevel
    if profile.programmingLanguages is not None:
        updates['"programmingLanguages"'] = profile.programmingLanguages
    if profile.aiMlFamiliarity is not None:
        updates['"aiMlFamiliarity"'] = profile.aiMlFamiliarity
    if profile.hardwareExperience is not None:
        updates['"hardwareExperience"'] = profile.hardwareExperience
    if profile.learningGoals is not None:
        updates['"learningGoals"'] = profile.learningGoals
    if profile.questionnaireCompleted is not None:
        updates['"questionnaireCompleted"'] = profile.questionnaireCompleted

    if not updates:
        return {"message": "No fields to update"}

    database_url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(database_url)
    try:
        set_clauses = []
        values = []
        for i, (col, val) in enumerate(updates.items(), 1):
            set_clauses.append(f"{col} = ${i}")
            values.append(val)
        values.append(user_id)
        query = f'UPDATE "user" SET {", ".join(set_clauses)} WHERE id = ${len(values)}'
        await conn.execute(query, *values)
    finally:
        await conn.close()

    return {"message": "Profile updated"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: Request,
    chat_request: ChatRequest,
    auth_payload: dict = Depends(verify_auth),
):
    # Apply rate limiting using session_id
    await check_rate_limit(request, chat_request.session_id)

    try:
        # 1. Retrieve relevant context
        embedding = get_embedding(chat_request.message)
        search_result = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=embedding,
            limit=3
        ).points

        context_text = "\n\n".join([hit.payload["text"] for hit in search_result])
        sources = list(set([hit.payload["source"] for hit in search_result]))

        # 2. Build personalized system prompt
        system_prompt = f"""You are a helpful assistant for the Agentic AI Book.
        Use the following context to answer the user's question.
        If the answer is not in the context, say you don't know.

        Context:
        {context_text}
        """

        # Personalize based on user questionnaire
        exp_level = auth_payload.get("experienceLevel", "")
        prog_langs = auth_payload.get("programmingLanguages", "")
        ai_familiarity = auth_payload.get("aiMlFamiliarity", "")
        if exp_level or prog_langs or ai_familiarity:
            personalization = "\n        User background:"
            if exp_level:
                personalization += f"\n        - Experience level: {exp_level}"
            if prog_langs:
                personalization += f"\n        - Programming languages: {prog_langs}"
            if ai_familiarity:
                personalization += f"\n        - AI/ML familiarity: {ai_familiarity}"
            personalization += "\n        Adjust your explanations accordingly."
            system_prompt += personalization

        user_message = chat_request.message

        # 3. Call LLM
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{system_prompt}\n\nUser: {user_message}\n\nAssistant:",
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=2048,
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_ONLY_HIGH"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH",
                            threshold="BLOCK_ONLY_HIGH"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT",
                            threshold="BLOCK_ONLY_HIGH"
                        ),
                        types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                            threshold="BLOCK_ONLY_HIGH"
                        ),
                    ]
                )
            )

            response_text = response.text

        except Exception as e:
            print(f"Gemini API error: {e}")
            raise HTTPException(status_code=500, detail="An error occurred processing your request")

        # 4. Save to history
        try:
            user_id = auth_payload.get("sub")
            await add_message(chat_request.session_id, user_message, response_text, user_id=user_id)
        except Exception as e:
            print(f"Warning: Failed to save to history: {e}")

        return ChatResponse(response=response_text, sources=sources)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
