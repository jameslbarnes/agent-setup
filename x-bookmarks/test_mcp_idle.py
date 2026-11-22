"""Measure mcp_server.py memory after the handshake only (what an idle session costs)."""
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes

PYTHON = r"C:\Users\you\AppData\Local\Programs\Python\Python312\python.exe"


class PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]


def private_mb(pid):
    handle = ctypes.windll.kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
    counters = PMC()
    counters.cb = ctypes.sizeof(PMC)
    ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    return counters.PrivateUsage / 2**20


server = subprocess.Popen([PYTHON, "-I", r"C:\Users\you\src\x-bookmarks\mcp_server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for message in ({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}):
    server.stdin.write((json.dumps(message) + "\n").encode())
    server.stdin.flush()
    server.stdout.readline()
time.sleep(0.5)
print(f"idle after handshake: private {private_mb(server.pid):.1f} MB")
server.stdin.close()
server.wait(timeout=10)
