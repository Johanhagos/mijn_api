"""Simple file-based memory for the agent.
This is not intended for production; replace with a secure store if needed.
"""
import json
import os

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_memory(data):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
