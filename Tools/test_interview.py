import requests
import json
import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"

def print_separator():
    print("\n" + "="*60 + "\n")

def test_full_interview():
    """Run a complete interview simulation"""
    print(">>> AI INTERVIEW SIMULATOR - FULL TEST\n")
    
    # Step 1: Health check
    print("[1] Checking system health...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        health = response.json()
        print(f"   [OK] Status: {health['status']}")
        print(f"   [OK] Ollama: {health['ollama']}")
        print(f"   [OK] Models: {', '.join(health['available_models']) if health['available_models'] else 'None'}")
        
        if not health['available_models']:
            print("\n   [WARNING] No models available! Run: ollama pull llama3.1")
            return
            
    except Exception as e:
        print(f"   [ERROR] Backend not available: {e}")
        print("\n   [TIP] Start backend: cd backend && python main.py")
        return
    
    print_separator()
    
    # Step 2: Start interview
    print("[2] Starting Software Engineer interview...")
    try:
        start_data = {
            "role": "software_engineer",
            "difficulty": "medium"
        }
        response = requests.post(f"{BASE_URL}/interview/start", json=start_data, timeout=90)
        
        if response.status_code != 200:
            print(f"   [ERROR] Error: {response.text}")
            return
            
        result = response.json()
        print(f"\n   [AI] {result['message']}")
        
        # Store conversation history
        messages = [
            {"role": "user", "content": "Hello, I'm ready for the interview."},
            {"role": "assistant", "content": result['message']}
        ]
        
    except Exception as e:
        print(f"   [ERROR] Error starting interview: {e}")
        return
    
    print_separator()
    
    # Step 3: Simulate conversation
    test_responses = [
        "I'm a software engineer with 3 years of experience in full-stack development, primarily working with Python and React.",
        "I recently built a real-time chat application using WebSockets and Redis for pub/sub messaging. The biggest challenge was handling connection drops and ensuring message delivery.",
        "I would use a hash table to store characters and their frequencies. Time complexity would be O(n) and space O(k) where k is the number of unique characters.",
        "I'm interested in your company's focus on AI-driven products and the collaborative engineering culture I've read about."
    ]
    
    for i, user_response in enumerate(test_responses):
        print(f"[3.{i+1}] Continuing conversation...")
        
        # User response
        print(f"\n   [YOU] {user_response}")
        messages.append({"role": "user", "content": user_response})
        
        # Get AI response
        try:
            chat_data = {
                "messages": messages,
                "role": "software_engineer"
            }
            
            response = requests.post(
                f"{BASE_URL}/interview/chat",
                json=chat_data,
                stream=True,
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"   [ERROR] Error: {response.text}")
                break
            
            print("\n   [AI] ", end="", flush=True)
            
            # Collect streaming response
            ai_message = ""
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        try:
                            data = json.loads(decoded[6:])
                            if 'content' in data:
                                content = data['content']
                                print(content, end='', flush=True)
                                ai_message += content
                            elif data.get('done'):
                                break
                        except json.JSONDecodeError:
                            pass
            
            print()  # New line after response
            
            # Add to conversation history
            if ai_message:
                messages.append({"role": "assistant", "content": ai_message})
            
            print_separator()
            
        except Exception as e:
            print(f"\n   [ERROR] Error: {e}")
            break
    
    # Summary
    print("\n[OK] INTERVIEW TEST COMPLETE!\n")
    print(f"[STATS] Total exchanges: {len(messages) // 2}")
    print(f"[STATS] Conversation length: {len(messages)} messages")
    
    print("\n[EVALUATION CRITERIA]")
    print("  * Did the AI ask relevant questions?")
    print("  * Was the tone professional?")
    print("  * Did responses stay concise (2-3 sentences)?")
    print("  * Did follow-ups relate to previous answers?")
    print("  * Did it feel like a real interview?")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        test_full_interview()
    except KeyboardInterrupt:
        print("\n\n[PAUSED] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
