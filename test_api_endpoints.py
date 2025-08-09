#!/usr/bin/env python3
"""
Test the FastAPI endpoints directly without starting a server.
"""

import asyncio
from fastapi.testclient import TestClient
from devsync_ai.main import app


def test_api_endpoints():
    """Test the API endpoints."""
    print("Testing FastAPI endpoints...")

    # Create test client
    client = TestClient(app)

    # Test health endpoint
    print("\n1. Testing health endpoint...")
    response = client.get("/api/v1/health")
    print(f"Status: {response.status_code}")
    try:
        print(f"Response: {response.json()}")
    except:
        print(f"Response text: {response.text}")
        print(f"Response headers: {dict(response.headers)}")

    # Test root endpoint
    print("\n2. Testing root endpoint...")
    response = client.get("/api/v1/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test GitHub auth endpoint
    print("\n3. Testing GitHub auth endpoint...")
    response = client.get("/api/v1/github/test")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ GitHub auth successful!")
        print(f"   User: {data.get('user', {}).get('login')} ({data.get('user', {}).get('name')})")
        print(
            f"   Rate limit: {data.get('rate_limit', {}).get('remaining')}/{data.get('rate_limit', {}).get('limit')}"
        )
    else:
        print(f"❌ GitHub auth failed: {response.text}")

    # Test GitHub PRs endpoint
    print("\n4. Testing GitHub PRs endpoint...")
    response = client.get("/api/v1/github/prs")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ GitHub PRs retrieved successfully!")
        print(f"   Repository: {data.get('repository')}")
        print(f"   Total PRs: {data.get('total_prs', 0)}")
        print(f"   Conflict updates: {data.get('conflict_updates', 0)}")
    else:
        print(f"❌ GitHub PRs failed: {response.text}")

    print("\n🎉 API endpoint testing complete!")


if __name__ == "__main__":
    test_api_endpoints()
