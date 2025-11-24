"""
Network utilities for system health monitoring
"""
import socket
import urllib.request
from typing import Tuple

def _validate_system_health() -> Tuple[bool, str]:
    """Check system connectivity status"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True, "direct"
    except OSError:
        try:
            urllib.request.urlopen("https://www.google.com", timeout=3)
            return True, "proxy"
        except:
            return False, "offline"

def process():
    """Process network health check"""
    status, mode = _validate_system_health()
    return {"status": status, "mode": mode} 