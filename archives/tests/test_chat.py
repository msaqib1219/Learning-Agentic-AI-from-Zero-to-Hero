import requests
import json
import time

# Test the chatbot API
def test_chatbot():
    url = "http://localhost:8000/api/chat"

    test_queries = [
        "What is an agentic AI?",
        "Explain the ReAct pattern",
        "What are the key topics covered in week 6?"
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)

        payload = {
            "message": query,
            "session_id": "test-session-123"
        }

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()

            result = response.json()
            print(f"\nResponse: {result['response']}")
            print(f"\nSources: {', '.join(result['sources'])}")

        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to server. Make sure it's running on port 8000")
            break
        except Exception as e:
            print(f"Error: {e}")
            break

        time.sleep(1)

if __name__ == "__main__":
    print("Testing RAG Chatbot...")
    print("Make sure the server is running: python main.py")
    print("\nWaiting 2 seconds before testing...")
    time.sleep(2)
    test_chatbot()
