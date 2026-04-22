"""
Simple SQLite-based authentication for Phase A testing.
Replaces the PostgreSQL-based auth_server.py for local development.
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import bcrypt
import httpx

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# SQLite database file
DB_PATH = "auth.db"

router = APIRouter(prefix="/auth", tags=["auth"])


# --- Database Setup ---
def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db_sqlite():
    """Initialize SQLite database tables."""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # User table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "user" (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                password_hash TEXT,
                emailVerified INTEGER DEFAULT 1,
                image TEXT,
                createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                experienceLevel TEXT,
                programmingLanguages TEXT,
                aiMlFamiliarity TEXT,
                hardwareExperience TEXT,
                learningGoals TEXT,
                questionnaireCompleted INTEGER DEFAULT 0
            )
        ''')

        # Session table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session (
                id TEXT PRIMARY KEY,
                userId TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expiresAt TIMESTAMP NOT NULL,
                createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(userId) REFERENCES "user"(id) ON DELETE CASCADE
            )
        ''')

        # Account table (for OAuth)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS account (
                id TEXT PRIMARY KEY,
                userId TEXT NOT NULL,
                type TEXT NOT NULL,
                provider TEXT NOT NULL,
                providerAccountId TEXT NOT NULL,
                refreshToken TEXT,
                accessToken TEXT,
                expiresAt INTEGER,
                createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(provider, providerAccountId),
                FOREIGN KEY(userId) REFERENCES "user"(id) ON DELETE CASCADE
            )
        ''')

        conn.commit()
        print("✅ SQLite auth tables initialized")
    except Exception as e:
        print(f"Database init error: {e}")
    finally:
        conn.close()


# --- Models ---
class SignUpRequest(BaseModel):
    email: str
    password: str
    name: str


class SignInRequest(BaseModel):
    email: str
    password: str


# --- Helpers ---
def generate_id() -> str:
    """Generate unique ID."""
    import uuid
    return str(uuid.uuid4())


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hash: str) -> bool:
    """Verify password."""
    try:
        return bcrypt.checkpw(password.encode(), hash.encode())
    except:
        return False


def get_user_by_email(email: str):
    """Get user by email."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM "user" WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_session(token: str):
    """Get session and user from token."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, u.* FROM session s
        JOIN "user" u ON s.userId = u.id
        WHERE s.token = ? AND s.expiresAt > datetime('now')
    ''', (token,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# --- Endpoints ---
@router.post("/sign-up")
async def sign_up(req: SignUpRequest):
    """Register a new user."""
    try:
        # Check if user exists
        user = get_user_by_email(req.email)
        if user:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_id = generate_id()
        password_hash = hash_password(req.password)

        conn = get_db()
        cursor = conn.cursor()

        # Insert user
        cursor.execute('''
            INSERT INTO "user" (id, email, name, password_hash, emailVerified)
            VALUES (?, ?, ?, ?, 1)
        ''', (user_id, req.email, req.name, password_hash))

        # Create session
        session_token = generate_id()
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        session_id = generate_id()

        cursor.execute('''
            INSERT INTO session (id, userId, token, expiresAt)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, session_token, expires_at.isoformat()))

        conn.commit()
        conn.close()

        return {
            "user": {
                "id": user_id,
                "email": req.email,
                "name": req.name,
            },
            "session": {
                "token": session_token,
                "expiresAt": expires_at.isoformat(),
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Sign-up error: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/sign-in")
async def sign_in(req: SignInRequest, response: Response):
    """Sign in user with email and password."""
    try:
        user = get_user_by_email(req.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Verify password
        password_hash = user.get("password_hash")
        if not password_hash or not verify_password(req.password, password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Create session
        session_token = generate_id()
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        session_id = generate_id()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO session (id, userId, token, expiresAt)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user["id"], session_token, expires_at.isoformat()))
        conn.commit()
        conn.close()

        # Set session cookie
        response.set_cookie(
            "better-auth.session_token",
            session_token,
            max_age=30*24*60*60,
            httponly=True,
            secure=False,  # Allow non-HTTPS for localhost
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Sign-in error: {e}")
        raise HTTPException(status_code=500, detail=f"Sign-in failed: {str(e)}")


@router.post("/sign-out")
async def sign_out(request: Request, response: Response):
    """Sign out user."""
    try:
        token = request.cookies.get("better-auth.session_token")
        if token:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM session WHERE token = ?', (token,))
            conn.commit()
            conn.close()

        response.delete_cookie("better-auth.session_token")
        return {"success": True}
    except Exception as e:
        print(f"Sign-out error: {e}")
        raise HTTPException(status_code=500, detail="Sign-out failed")


@router.get("/session")
async def get_session_endpoint(request: Request):
    """Get current session and user data."""
    try:
        token = request.cookies.get("better-auth.session_token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")

        session = get_session(token)
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
                "questionnaireCompleted": bool(session.get("questionnaireCompleted")),
            },
            "session": {
                "token": token,
                "expiresAt": session["expiresAt"],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Session error: {e}")
        raise HTTPException(status_code=401, detail="Session error")


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
    """Google OAuth callback."""
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
        user = get_user_by_email(email)

        conn = get_db()
        cursor = conn.cursor()

        if not user:
            user_id = generate_id()
            cursor.execute('''
                INSERT INTO "user" (id, email, name, emailVerified)
                VALUES (?, ?, ?, 1)
            ''', (user_id, email, google_user.get("name", "")))
        else:
            user_id = user["id"]

        # Create session
        session_token = generate_id()
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        session_id = generate_id()

        cursor.execute('''
            INSERT INTO session (id, userId, token, expiresAt)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, session_token, expires_at.isoformat()))

        conn.commit()
        conn.close()

        # Set cookie and redirect
        response = RedirectResponse(url=FRONTEND_URL)
        response.set_cookie(
            "better-auth.session_token",
            session_token,
            max_age=30*24*60*60,
            httponly=True,
            secure=False,
            samesite="lax"
        )
        return response

    except Exception as e:
        print(f"Google OAuth error: {e}")
        raise HTTPException(status_code=400, detail="OAuth failed")
