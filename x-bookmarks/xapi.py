"""Minimal X API v2 client that reuses an X login stored in ~/.config/x-mcp.

The Authorization header comes from a login helper that isn't included here
(headers.ps1, which decrypts the DPAPI-protected user token and renews it
when it can). Never print, log or save the header or anything derived from it.
"""
import json
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

HEADERS_HELPER = [
    "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
    "-File", r"C:\Users\you\.config\x-mcp\headers.ps1",
]
API = "https://api.x.com"


class XApiError(RuntimeError):
    def __init__(self, message, status=None, body=None):
        super().__init__(message)
        self.status = status
        self.body = body


def auth_header(refresh_now=False):
    command = HEADERS_HELPER + (["-RefreshNow"] if refresh_now else [])
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        # The helper's own errors never contain credentials; keep only the last line.
        lines = [line.strip() for line in (result.stderr or "").splitlines() if line.strip()]
        reason = next((line for line in lines if "X " in line or "renewal" in line), lines[-1] if lines else "unknown error")
        raise XApiError(f"X login helper failed: {reason[:200]}")
    headers = json.loads(result.stdout)
    if not headers.get("Authorization", "").startswith("Bearer "):
        raise XApiError("X login helper returned no bearer token")
    return headers


class Client:
    def __init__(self):
        self.headers = auth_header()
        self.calls = 0
        self.rate = {}

    def get(self, path, params=None, retries=4):
        query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
        url = f"{API}{path}" + (f"?{query}" if query else "")
        attempt = 0
        renewed = False
        while True:
            attempt += 1
            request = urllib.request.Request(url, headers={**self.headers, "User-Agent": "x-bookmarks/1"})
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    self.calls += 1
                    self.rate = {k: response.headers.get(k) for k in ("x-rate-limit-limit", "x-rate-limit-remaining", "x-rate-limit-reset")}
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                self.calls += 1
                body = error.read().decode("utf-8", "replace")[:2000]
                if error.code == 401 and not renewed:
                    # Expired user token: ask the helper to renew once.
                    renewed = True
                    try:
                        self.headers = auth_header(refresh_now=True)
                    except XApiError as renewal:
                        raise XApiError(f"X rejected the stored login (401) and renewal failed: {renewal}", 401, body)
                    continue
                if error.code == 429 and attempt <= retries:
                    reset = error.headers.get("x-rate-limit-reset")
                    wait = max(5, min(900, int(reset) - int(time.time()) + 2)) if reset and reset.isdigit() else 60
                    if wait > 300:
                        raise XApiError(f"X rate limit: reset in {wait} s", 429, body)
                    time.sleep(wait)
                    continue
                if error.code >= 500 and attempt <= retries:
                    time.sleep(5 * attempt)
                    continue
                raise XApiError(f"X API HTTP {error.code} for {path}", error.code, body)
            except (urllib.error.URLError, TimeoutError) as error:
                if attempt <= retries:
                    time.sleep(5 * attempt)
                    continue
                raise XApiError(f"X API network error for {path}: {error}")
