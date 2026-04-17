"""
Wanis Lightning Module - Remote Execution.

This module contains components for remote voice processing:
- remote_client: Thin client for capturing audio from laptop microphone
- remote_server: Full pipeline server running on Lightning AI

Usage:
    # On Lightning AI (server):
    python -m wanis.lightning.remote_server --port 8000

    # On Laptop (client):
    python -m wanis.lightning.remote_client --server ws://LIGHTNING_IP:8000/ws
"""

__all__ = ["RemoteClient", "RemoteServer"]
