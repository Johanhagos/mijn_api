"""Simple scheduler to run agent tasks periodically.
This module is a manual runner; do not enable as a daemon without setting up safety and credentials.
"""
import time
from .agent import run_agent


def periodic_check(interval_seconds: int = 600):
    while True:
        result = run_agent("Check site health")
        print("[agent] periodic check:", result)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    periodic_check()
