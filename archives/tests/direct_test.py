import asyncio
import sys
sys.path.insert(0, r"E:\PIAIC\Hackathon I\backend")

from main import chat, ChatRequest

async def test():
    request = ChatRequest(
        message="What is an agentic AI?",
        session_id="test-123"
    )

    try:
        response = await chat(request)
        print("="*60)
        print(f"Response: {response.response}")
        print(f"\nSources: {', '.join(response.sources)}")
        print("="*60)
        print("\n[SUCCESS] Chatbot working!")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
