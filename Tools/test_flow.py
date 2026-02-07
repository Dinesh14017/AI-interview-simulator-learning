import requests
import json
import time
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def print_separator():
    print("\n" + "="*80 + "\n")

def test_session_flow():
    """Run a complete interview simulation with session state"""
    print(">>> AI INTERVIEW SIMULATOR - SESSION FLOW TEST\n")
    
    # Step 1: Start interview
    print("[1] Starting Software Engineer interview...")
    start_data = {
        "role": "software_engineer",
        "difficulty": "medium"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/interview/start", json=start_data, timeout=30)
        if response.status_code != 200:
            print(f"[ERROR] Start failed: {response.text}")
            return
            
        data = response.json()
        session_id = data["session_id"]
        print(f"   [OK] Session started: {session_id}")
        print(f"   [STAGE] {data['stage']}")
        print(f"   [AI] {data['message']}")
        
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return

    print_separator()
    
    # Step 2: Simulate conversation with various response types
    # We consciously create responses that trigger stage 1 -> stage 2 transition
    # And include one short response to test difficulty adaptation
    test_responses = [
        # Intro Stage (needs 2 questions to advance)
        "I'm a backend developer with 5 years experience in Python and cloud architecture.", 
        
        # Should be Intro -> Technical transition now
        "I built a distributed task queue using Redis and FastAPI that handled 1M jobs/day.", 
        
        # Technical Stage - Give a SHORT answer to trigger adaptation
        "Hash maps use keys.", 
        
        # Technical Stage - Good answer
        "To scale the database, I would implement read replicas and sharding based on user ID.",
        
        # Should be ending soon
        "I don't have any specific questions right now."
    ]
    
    messages = [] # Client-side history (optional now, but good for tracking)
    
    for i, user_response in enumerate(test_responses):
        print(f"[2.{i+1}] Sending response...")
        print(f"   [YOU] {user_response}")
        
        # Start streaming request
        chat_data = {
            "session_id": session_id,
            "messages": [{"role": "user", "content": user_response}],
            "role": "software_engineer"
        }
        
        try:
            response = requests.post(
                f"{BASE_URL}/interview/chat",
                json=chat_data,
                stream=True,
                timeout=60
            )
            
            print("   [AI] ", end="", flush=True)
            
            ai_full_text = ""
            meta_stage = "unknown"
            
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        try:
                            chunk = json.loads(decoded[6:])
                            if 'content' in chunk:
                                content = chunk['content']
                                print(content, end='', flush=True)
                                ai_full_text += content
                            elif chunk.get('done'):
                                meta_stage = chunk.get('stage', 'unknown')
                        except:
                            pass
            
            print(f"\n\n   [META] Current Stage: {meta_stage}")
            print_separator()
            
        except Exception as e:
            print(f"\n[ERROR] Chat failed: {e}")
            break
            
    print("[TEST COMPLETE]")

if __name__ == "__main__":
    test_session_flow()
