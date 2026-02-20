"""frontend/test_integration.py — Smoke test for API connectivity.

Run with: python test_integration.py
Requires: FastAPI server running on port 8001
"""

import httpx
import sys

API_BASE = "http://localhost:8001/api"


def test_endpoints():
    """Test that all key endpoints respond."""
    client = httpx.Client(base_url=API_BASE, timeout=10.0)
    results = []

    endpoints = [
        ("GET", "/health", None),
        ("GET", "/health/growth", {"days": 7}),
        ("GET", "/health/milestones", None),
        ("GET", "/health/setup", None),
        ("GET", "/patterns", None),
        ("GET", "/experiences", None),
        ("GET", "/examples", None),
        ("GET", "/knowledge", None),
        ("GET", "/projects", None),
        ("GET", "/content-types", None),
        ("GET", "/graph/health", None),
        ("GET", "/settings/config", None),
        ("GET", "/settings/providers", None),
    ]

    for method, path, params in endpoints:
        try:
            if method == "GET":
                resp = client.get(path, params=params)
            else:
                resp = client.post(path, json=params or {})
            status = "OK" if resp.status_code < 500 else "FAIL"
            results.append((path, resp.status_code, status))
        except Exception as e:
            results.append((path, 0, f"ERROR: {e}"))

    print("\n=== API Connectivity Test ===\n")
    for path, code, status in results:
        icon = "+" if status == "OK" else "-"
        print(f"  [{icon}] {path}: {code} ({status})")

    failures = [r for r in results if r[2] != "OK"]
    print(f"\n{len(results) - len(failures)}/{len(results)} endpoints OK")

    if failures:
        print(f"\n{len(failures)} failures:")
        for path, code, status in failures:
            print(f"  - {path}: {status}")
        sys.exit(1)


if __name__ == "__main__":
    test_endpoints()
