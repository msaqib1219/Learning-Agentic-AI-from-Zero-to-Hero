import asyncio
import sys
sys.path.insert(0, r"E:\PIAIC\Hackathon I\backend")

from main import chat, ChatRequest

async def test_multiple_queries():
    queries = [
        "What is an agentic AI?",
        "Explain the ReAct pattern",
        "What topics are covered in week 6?",
        "What is RAG?"
    ]

    print("="*70)
    print("COMPREHENSIVE CHATBOT TEST")
    print("="*70)

    for i, query in enumerate(queries, 1):
        print(f"\n[Query {i}] {query}")
        print("-"*70)

        request = ChatRequest(
            message=query,
            session_id=f"test-session-{i}"
        )

        try:
            response = await chat(request)
            print(f"Response: {response.response[:300]}...")
            print(f"Sources: {', '.join(response.sources)}")
            print("Status: ✓ SUCCESS")
        except Exception as e:
            print(f"Status: ✗ FAILED - {type(e).__name__}: {str(e)[:100]}")

    print("\n" + "="*70)
    print("TEST COMPLETE")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_multiple_queries())
