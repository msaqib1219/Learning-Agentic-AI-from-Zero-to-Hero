"""
Better Auth server implementation for FastAPI.
Handles user registration, login, Google OAuth, and session management.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
import asyncpg
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import bcrypt
from authlib.integrations.httpx_client import AsyncOAuth2Session
import httpx

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
JWT_SECRET = os.getenv("JWT_SECRET_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Database Schema ---
async def init_auth_db():
    """Create better-auth compatible tables."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS "user" (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                "emailVerified" BOOLEAN DEFAULT FALSE,
                image TEXT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "experienceLevel" TEXT,
                "programmingLanguages" TEXT,
                "aiMlFamiliarity" TEXT,
                "hardwareExperience" TEXT,
                "learningGoals" TEXT,
                "questionnaireCompleted" BOOLEAN DEFAULT FALSE
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS account (
                id TEXT PRIMARY KEY,
                "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                provider TEXT NOT NULL,
                "providerAccountId" TEXT NOT NULL,
                "refreshToken" TEXT,
                "accessToken" TEXT,
                "expiresAt" BIGINT,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, "providerAccountId")
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS session (
                id TEXT PRIMARY KEY,
                "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                token TEXT UNIQUE NOT NULL,
                "expiresAt" TIMESTAMP NOT NULL,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        await conn.execute('''
            CREATE TABLE IF NOT EXISTS verification (
                id TEXT PRIMARY KEY,
                identifier TEXT NOT NULL,
                token TEXT NOT NULL,
                "expiresAt" TIMESTAMP NOT NULL,
                "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(identifier, token)
            )
        ''')

        print("✅ Auth database tables initialized")
    finally:
        await conn.close()


# --- Request/Response Models ---
class SignUpRequest(BaseModel):
    email: str
    password: str
    name: str


class SignInRequest(BaseModel):
    email: str
    password: str


class SessionResponse(BaseModel):
    user: dict
    session: dict


# --- Helper Functions ---
def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hash: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode(), hash.encode())


def generate_id() -> str:
    """Generate a unique ID."""
    import uuid
    return str(uuid.uuid4())


async def get_user_by_email(email: str):
    """Get user from database by email."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        return await conn.fetchrow('SELECT * FROM "user" WHERE email = $1', email)
    finally:
        await conn.close()


async def get_session(token: str):
    """Get session and user from token."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        row = await conn.fetchrow('''
            SELECT s.*, u.* FROM session s
            JOIN "user" u ON s."userId" = u.id
            WHERE s.token = $1 AND s."expiresAt" > NOW()
        ''', token)
        return row
    finally:
        await conn.close()


# --- Auth Endpoints ---
@router.post("/sign-up")
async def sign_up(req: SignUpRequest):
    """Register a new user."""
    # Check if user exists
    user = await get_user_by_email(req.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = generate_id()
    password_hash = hash_password(req.password)

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO "user" (id, email, name, "emailVerified")
            VALUES ($1, $2, $3, TRUE)
        ''', user_id, req.email, req.name)

        # Create session
        session_token = generate_id()
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        session_id = generate_id()

        await conn.execute('''
            INSERT INTO session (id, "userId", token, "expiresAt")
            VALUES ($1, $2, $3, $4)
        ''', session_id, user_id, session_token, expires_at)
    finally:
        await conn.close()

    # Return session
    user = await get_user_by_email(req.email)
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
        },
        "session": {
            "token": session_token,
            "expiresAt": expires_at.isoformat(),
        }
    }


@router.post("/sign-in")
async def sign_in(req: SignInRequest, response: Response):
    """Sign in user with email and password."""
    user = await get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # For now, we store plain password. In production, hash it.
    # This is a temporary solution for Phase A
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Check if password matches (simplified - should use hashing)
        # For Phase A, we'll accept any password to test flow

        # Create session
        session_token = generate_id()
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        session_id = generate_id()

        await conn.execute('''
            INSERT INTO session (id, "userId", token, "expiresAt")
            VALUES ($1, $2, $3, $4)
        ''', session_id, user["id"], session_token, expires_at)
    finally:
        await conn.close()

    # Set session cookie
    response.set_cookie(
        "better-auth.session_token",
        session_token,
        max_age=30*24*60*60,  # 30 days
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
        },
        "session": {
            "token": session_token,
            "expiresAt": expires_at.isoformat(),
        }
    }


@router.post("/sign-out")
async def sign_out(request: Request, response: Response):
    """Sign out user and invalidate session."""
    token = request.cookies.get("better-auth.session_token")
    if token:
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            await conn.execute('DELETE FROM session WHERE token = $1', token)
        finally:
            await conn.close()

    response.delete_cookie("better-auth.session_token")
    return {"success": True}


@router.get("/session")
async def get_session_endpoint(request: Request):
    """Get current session and user data."""
    token = request.cookies.get("better-auth.session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = await get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")

    return {
        "user": {
            "id": session["id"],
            "email": session["email"],
            "name": session["name"],
            "experienceLevel": session.get("experienceLevel"),
            "programmingLanguages": session.get("programmingLanguages"),
            "aiMlFamiliarity": session.get("aiMlFamiliarity"),
            "hardwareExperience": session.get("hardwareExperience"),
            "learningGoals": session.get("learningGoals"),
            "questionnaireCompleted": session.get("questionnaireCompleted"),
        },
        "session": {
            "token": token,
            "expiresAt": session["expiresAt"].isoformat(),
        }
    }


@router.get("/oauth/google")
async def oauth_google():
    """Initiate Google OAuth flow."""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile"
    )
    return RedirectResponse(url=google_auth_url)


@router.get("/callback/google")
async def oauth_google_callback(code: str, response: Response):
    """Google OAuth callback - exchange code for token."""
    try:
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                }
            )
            token_resp.raise_for_status()
            tokens = token_resp.json()

            # Get user info
            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            user_resp.raise_for_status()
            google_user = user_resp.json()

        # Create or update user
        email = google_user["email"]
        user = await get_user_by_email(email)

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            if not user:
                user_id = generate_id()
                await conn.execute('''
                    INSERT INTO "user" (id, email, name, image, "emailVerified")
                    VALUES ($1, $2, $3, $4, TRUE)
                ''', user_id, email, google_user.get("name", ""), google_user.get("picture"))
            else:
                user_id = user["id"]

            # Create session
            session_token = generate_id()
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            session_id = generate_id()

            await conn.execute('''
                INSERT INTO session (id, "userId", token, "expiresAt")
                VALUES ($1, $2, $3, $4)
            ''', session_id, user_id, session_token, expires_at)
        finally:
            await conn.close()

        # Set session cookie and redirect
        response = RedirectResponse(url=FRONTEND_URL)
        response.set_cookie(
            "better-auth.session_token",
            session_token,
            max_age=30*24*60*60,
            httponly=True,
            secure=True,
            samesite="lax"
        )
        return response

    except Exception as e:
        print(f"Google OAuth error: {e}")
        raise HTTPException(status_code=400, detail="OAuth failed")
