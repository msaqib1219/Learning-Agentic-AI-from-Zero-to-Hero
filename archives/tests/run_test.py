import subprocess
import time
import requests
import sys

print("Starting FastAPI server...")
# Start the server
server_process = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
    cwd=r"E:\PIAIC\Hackathon I\backend",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# Wait for server to start
print("Waiting for server to start...")
time.sleep(8)

try:
    # Test query
    url = "http://localhost:8000/api/chat"
    query = "What is an agentic AI?"

    print(f"\nSending query: '{query}'")
    print("="*60)

    payload = {
        "message": query,
        "session_id": "test-session-123"
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()

    result = response.json()
    print(f"\nResponse:\n{result['response']}")
    print(f"\nSources: {', '.join(result['sources'])}")
    print("="*60)
    print("\n[SUCCESS] Chatbot is working correctly!")

except Exception as e:
    print(f"\n[ERROR] {e}")

    # Print server output
    print("\n--- Server stdout ---")
    try:
        stdout, stderr = server_process.communicate(timeout=1)
        print(stdout.decode())
        if stderr:
            print("\n--- Server stderr ---")
            print(stderr.decode())
    except:
        pass

finally:
    # Stop the server
    print("\nStopping server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except:
        server_process.kill()
    print("Server stopped.")
