"""
Fulfillment Hub Launcher
Starts the Uvicorn web server and opens the browser automatically.
Run with: python run.py
"""

import sys
import os
import time
import webbrowser
import threading
import uvicorn
from database import init_db, get_db
from sample_data import seed_database

def check_and_seed():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders")
    count = cursor.fetchone()[0]
    conn.close()
    if count == 0:
        print("[*] No existing orders found. Seeding initial 250 realistic demo orders...")
        seed_database()
    else:
        print(f"[*] Found {count} orders in database.")

def open_browser():
    time.sleep(1.2)
    url = "http://127.0.0.1:8000"
    print(f"\n=======================================================")
    print(f"  XYZ E-Commerce Fulfillment Hub is LIVE!")
    print(f"  Access Dashboard at: {url}")
    print(f"  Press Ctrl+C in this terminal to stop the server.")
    print(f"=======================================================\n")
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")

if __name__ == "__main__":
    check_and_seed()
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False, log_level="info")
