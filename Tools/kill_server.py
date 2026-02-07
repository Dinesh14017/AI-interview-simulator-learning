import subprocess
import os

def kill_port(port):
    print(f"Attempting to kill process on port {port}...")
    try:
        # Try absolute path for netstat
        cmd = r'C:\Windows\System32\netstat.exe -ano'
        # Check if file exists to be sure, otherwise try simple netstat
        if not os.path.exists(r'C:\Windows\System32\netstat.exe'):
            cmd = 'netstat -ano'
            
        print(f"Running: {cmd}")
        output = subprocess.check_output(cmd, shell=True).decode()
        
        target_pid = None
        for line in output.splitlines():
            if f':{port}' in line and 'LISTENING' in line:
                parts = line.strip().split()
                if parts[-1].isdigit():
                    target_pid = parts[-1]
                    break
        
        if target_pid:
            print(f"Found PID {target_pid}. Killing...")
            kill_cmd = f'C:\\Windows\\System32\\taskkill.exe /F /PID {target_pid}'
            subprocess.call(kill_cmd, shell=True)
            print("Process killed.")
            return

        print(f"No process listening on port {port} found by netstat.")

    except Exception as e:
        print(f"Error executing netstat: {e}")
    
    # Fallback: Blindly kill python.exe processes that are likely the old server
    # We do this because we KNOW port 8000 is in use but netstat failed or didn't find it
    print("Fallback: Attempting to kill python.exe processes (excluding self)...")
    try:
        current_pid = os.getpid()
        # Get list of python pids
        # We can't use psutil, so we use tasklist
        cmd = r'C:\Windows\System32\tasklist.exe /FI "IMAGENAME eq python.exe" /FO CSV /NH'
        output = subprocess.check_output(cmd, shell=True).decode()
        
        for line in output.splitlines():
            if "python.exe" in line:
                # Parse CSV: "python.exe","1234","Console",...
                parts = line.split(',')
                pid_str = parts[1].replace('"', '')
                if pid_str.isdigit():
                    pid = int(pid_str)
                    if pid != current_pid:
                        print(f"Killing python.exe PID {pid}")
                        subprocess.call(f'C:\\Windows\\System32\\taskkill.exe /F /PID {pid}', shell=True)
    except Exception as e:
        print(f"Fallback error: {e}")
        # Ultimate fallback
        subprocess.call(r'C:\Windows\System32\taskkill.exe /F /IM python.exe', shell=True)

if __name__ == "__main__":
    kill_port(8000)
