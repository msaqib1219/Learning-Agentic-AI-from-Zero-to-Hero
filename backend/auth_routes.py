"""
Better-auth compatible endpoints for Phase A.
Maps better-auth client calls to our SQLite backend.
"""

import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from dotenv import load_dotenv
import bcrypt
import httpx
import uuid

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Import SQLite functions from auth_server_simple
from auth_server_simple import (
    get_db, generate_id, hash_password, verify_password,
    get_user_by_email, get_session
)


# --- Request Models ---
class SignUpEmailRequest(BaseModel):
    email: str
    password: str
    name: str


class SignInEmailRequest(BaseModel):
    email: str
    password: str


class GetSessionRequest(BaseModel):
    token: str = None


# --- Better-Auth Compatible Endpoints ---

@router.post("/sign-up/email")
async def sign_up_email(req: SignUpEmailRequest, response: Response):
    """Better-auth compatible sign-up endpoint."""
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

        # Set session cookie
        response.set_cookie(
            "better-auth.session_token",
            session_token,
            max_age=30*24*60*60,
            httponly=True,
            secure=False,
            samesite="lax"
        )

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


@router.post("/sign-in/email")
async def sign_in_email(req: SignInEmailRequest, response: Response):
    """Better-auth compatible sign-in endpoint."""
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
            secure=False,
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


@router.get("/session")
@router.get("/get-session")
async def get_session_endpoint(request: Request):
    """Get current session - better-auth compatible."""
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


@router.post("/sign-out")
async def sign_out(request: Request, response: Response):
    """Sign out - better-auth compatible."""
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


@router.post("/sign-in/social")
async def sign_in_social(request: Request, response: Response):
    """Placeholder for social sign-in."""
    raise HTTPException(status_code=501, detail="Social sign-in not configured yet")
