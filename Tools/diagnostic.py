import socket
import httpx
import asyncio
import os
import subprocess

async def check_ollama():
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("http://localhost:11434/api/tags", timeout=2.0)
            if resp.status_code == 200:
                print("Ollama: CONNECTED")
                models = resp.json().get("models", [])
                print(f"Ollama Models: {[m['name'] for m in models]}")
                return True
            else:
                print(f"Ollama: ERROR (Status {resp.status_code})")
                return False
    except Exception as e:
        print(f"Ollama: FAILED ({e})")
        return False

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def get_pid_on_port(port):
    # Try using netstat via subprocess
    try:
        cmd = f"netstat -ano | findstr :{port}"
        output = subprocess.check_output(cmd, shell=True).decode()
        lines = output.strip().split('\n')
        for line in lines:
            parts = line.split()
            if f":{port}" in parts[1]: # Local Address
                return parts[-1] # PID is last column
    except Exception:
        pass
    return None

async def main():
    print("--- DIAGNOSTIC REPORT ---")
    
    # Check Ollama
    ollama_ok = await check_ollama()
    
    # Check Backend Port
    port_in_use = check_port(8001)
    if port_in_use:
        print("Port 8001: IN USE")
        pid = get_pid_on_port(8001)
        if pid:
            print(f"PID using 8001: {pid}")
    else:
        print("Port 8001: FREE")

    print("-------------------------")

if __name__ == "__main__":
    asyncio.run(main())
