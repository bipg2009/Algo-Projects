"""
run_dashboard.py

Convenience entrypoint to run the local dashboard server (FastAPI + WebSocket)
without starting the full system controller.
"""

from api_server import start_server


def main() -> None:
    start_server()


if __name__ == "__main__":
    main()

