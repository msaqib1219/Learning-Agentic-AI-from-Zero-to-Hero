import os
from typing import Optional
from dotenv import load_dotenv
import asyncpg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def init_db():
    """Initialize database - only chat_history table.
    better-auth manages its own tables (user, session, account, verification).
    Gracefully fails if PostgreSQL is not available (e.g., in local dev).
    """
    try:
        conn = await asyncpg.connect(DATABASE_URL, timeout=2)
        try:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT
                )
            ''')
            print("✅ PostgreSQL chat_history table initialized")
        finally:
            await conn.close()
    except Exception as e:
        print(f"⚠️  PostgreSQL not available (using SQLite for auth): {type(e).__name__}")
        # Chat history will be unavailable, but auth will work with SQLite


# --- Chat history functions ---

async def add_message(session_id: str, user_message: str, bot_response: str, user_id: Optional[str] = None):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute('''
            INSERT INTO chat_history (session_id, user_message, bot_response, user_id)
            VALUES ($1, $2, $3, $4)
        ''', session_id, user_message, bot_response, user_id)
    finally:
        await conn.close()


async def get_history(session_id: str):
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch('''
            SELECT user_message, bot_response FROM chat_history
            WHERE session_id = $1
            ORDER BY created_at ASC
        ''', session_id)
    finally:
        await conn.close()
    result = []
    for row in rows:
        result.append({"role": "user", "content": row["user_message"]})
        result.append({"role": "assistant", "content": row["bot_response"]})
    return result
