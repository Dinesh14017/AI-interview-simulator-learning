import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("🔍 Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")

def test_start_interview():
    """Test starting an interview"""
    print("🎯 Testing /interview/start endpoint...")
    data = {
        "role": "software_engineer",
        "difficulty": "medium"
    }
    response = requests.post(f"{BASE_URL}/interview/start", json=data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"First question: {result['message']}\n")
    else:
        print(f"Error: {response.text}\n")

def test_chat():
    """Test chat endpoint"""
    print("💬 Testing /interview/chat endpoint...")
    data = {
        "messages": [
            {"role": "user", "content": "Hello, I'm ready for the interview."},
            {"role": "assistant", "content": "Great! Tell me about yourself."},
            {"role": "user", "content": "I'm a software engineer with 3 years of experience."}
        ],
        "role": "software_engineer"
    }
    response = requests.post(f"{BASE_URL}/interview/chat", json=data, stream=True)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Streaming response:")
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith('data: '):
                    try:
                        data = json.loads(decoded[6:])
                        if 'content' in data:
                            print(data['content'], end='', flush=True)
                    except:
                        pass
        print("\n")
    else:
        print(f"Error: {response.text}\n")

if __name__ == "__main__":
    print("=== AI Interview Simulator - API Tests ===\n")
    
    try:
        # Test 1: Health check
        test_health()
        
        print("=" * 50)
        print("\nℹ️  To test interview endpoints, make sure you have:")
        print("   1. Ollama running: ollama serve")
        print("   2. A model pulled: ollama pull llama3.1")
        print("\nThen run these tests:")
        print("   - test_start_interview()")
        print("   - test_chat()")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure the backend is running:")
        print("   cd backend")
        print("   python main.py")
