"""
Java Performance Analysis & Diagnostics - MCP Server Package

LLM-powered Java application performance monitoring and system diagnostics toolkit.
Provides real-time performance analysis, memory profiling, thread analysis, and method tracing.
Diagnose business issues, including inspecting method call inputs and outputs, exceptions, monitoring method execution time, and class loading information.
"""

__version__ = "0.1.0"
__author__ = "Arthas MCP Team"
__description__ = "Java Performance Analysis & Diagnostics - LLM-powered performance monitoring and system optimization toolkit"

from .models import ArthasConnection, JVMInfo, ThreadInfo
from .client import ArthasClient
from .server import ArthasMCPServer

__all__ = [
    "ArthasConnection", 
    "JVMInfo",
    "ThreadInfo",
    "ArthasClient",
    "ArthasMCPServer"
]