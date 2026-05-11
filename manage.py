import subprocess
import time
import os
import signal
import sys
import requests
from typing import Dict, Optional

# Configuration
SERVICES = {
    "tiphawk": {"port": 8001, "cmd": ["uvicorn", "tiphawk.main:app", "--port", "8001", "--log-level", "debug"]},
    "rails": {"port": 8002, "cmd": ["uvicorn", "rails.main:app", "--port", "8002", "--log-level", "debug"]},
    "copytrader": {"port": 8003, "cmd": ["uvicorn", "copytrader.main:app", "--port", "8003", "--log-level", "debug"]},
    "launchpad": {"port": 8004, "cmd": ["uvicorn", "launchpad.main:app", "--port", "8004", "--log-level", "debug"]},
}

class SovereignManager:
    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}

    def start_all(self):
        print("\n[FORGE] INITIALIZING SOVEREIGN ECOSYSTEM...")
        for name, config in SERVICES.items():
            self.start_service(name)
        
        print("\n[OK] All services dispatched. Entering monitor loop.")
        self.monitor()

    def start_service(self, name: str):
        config = SERVICES[name]
        print(f" [*] Launching {name.upper()} on port {config['port']}...")
        
        # Ensure we are in the right directory (project root)
        process = subprocess.Popen(
            config["cmd"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
        self.processes[name] = process

    def stop_all(self):
        print("\n[FORGE] SHUTTING DOWN ECOSYSTEM...")
        for name, process in self.processes.items():
            print(f" [!] Stopping {name}...")
            process.terminate()
        print("[OK] All systems offline.")

    def monitor(self):
        try:
            while True:
                for name, process in list(self.processes.items()):
                    # 1. Check if process is still running
                    if process.poll() is not None:
                        print(f"\n[CRITICAL] {name.upper()} CRASHED (Exit code: {process.returncode})")
                        print(" [*] Attempting automated recovery...")
                        self.start_service(name)
                    
                    # 2. Check health endpoint
                    try:
                        port = SERVICES[name]["port"]
                        resp = requests.get(f"http://localhost:{port}/health", timeout=1)
                        if resp.status_code != 200:
                            print(f" [?] {name.upper()} health check failed (Status: {resp.status_code})")
                    except Exception:
                        # Service might still be starting
                        pass

                time.sleep(10)
        except KeyboardInterrupt:
            self.stop_all()

if __name__ == "__main__":
    # Check if we are in the project root
    if not os.path.exists("requirements.txt"):
        print("[!] Error: manage.py must be run from the SML-XRPL-FEE-FORGE root directory.")
        sys.exit(1)

    manager = SovereignManager()
    
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    manager.start_all()
