import os
from dotenv import load_dotenv

# Load environment variables (override=True to override system env vars)
load_dotenv(override=True)

# Get the API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY not found in .env file")
    print("Please check your .env file and ensure it contains:")
    print("GEMINI_API_KEY=your_api_key_here")
else:
    print(f"Found API key: {GEMINI_API_KEY[:10]}...")

# Try to use the key
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    # Try a simple embedding request
    result = genai.embed_content(
        model="models/text-embedding-004",
        content="Test message to verify API key",
        task_type="retrieval_document"
    )

    print("[SUCCESS] API key is VALID! Successfully connected to Gemini API")
    print(f"[SUCCESS] Embedding generated successfully with dimension: {len(result['embedding'])}")

except Exception as e:
    print(f"[ERROR] API key is INVALID or there was an error: {e}")
    print("\nPossible issues:")
    print("1. API key is incorrect or expired")
    print("2. API key doesn't have the right permissions")
    print("3. Billing is not enabled on the project")
