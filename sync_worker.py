import time
import requests
import os

# Internal URL for syncing
SYNC_URL = "http://localhost:5001/api/sync/all"

def run_sync():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting background sync...")
    try:
        # Trigger full sync
        response = requests.get(SYNC_URL, params={"force": "1"}, timeout=300)
        if response.status_code == 200:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sync successful: {response.json()}")
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sync failed with status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error during sync: {e}")

if __name__ == "__main__":
    print("Background Sync Worker Started.")
    # Wait for the main app to start
    time.sleep(10)
    
    while True:
        run_sync()
        # Sleep for 1 hour
        print("Waiting for 1 hour...")
        time.sleep(3600)
