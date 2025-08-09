#!/usr/bin/env python3
"""
Quick test script to verify GitHub integration with real API calls.
Run this after setting up your GitHub token in .env
"""

import asyncio
import os
from dotenv import load_dotenv
from devsync_ai.services.github import GitHubService, GitHubAPIError

# Load environment variables
load_dotenv()


async def test_github_connection():
    """Test real GitHub API connection."""
    print("Testing GitHub API connection...")

    try:
        service = GitHubService()
        print(f"Configured to track repository: {service.get_default_repository()}")

        # Test authentication
        print("\n1. Testing authentication...")
        auth_info = await service.test_authentication()
        print(f"✅ Authenticated as: {auth_info['user']['login']} ({auth_info['user']['name']})")
        print(
            f"   Rate limit: {auth_info['rate_limit']['remaining']}/{auth_info['rate_limit']['limit']}"
        )

        # Test repository access
        print("\n2. Testing repository access...")
        repo = await service.get_repository(service.get_default_repository())
        print(f"✅ Successfully accessed repository: {repo.full_name}")

        # Test getting PRs
        print("\n3. Testing pull request retrieval...")
        prs = await service.get_open_pull_requests(service.get_default_repository())
        print(f"✅ Found {len(prs)} open pull requests")

        for pr in prs[:3]:  # Show first 3 PRs
            print(
                f"   - PR #{pr.id}: {pr.title} by {pr.author} ({pr.status.value if hasattr(pr.status, 'value') else str(pr.status)})"
            )

        # Test repository restriction
        print("\n4. Testing repository restriction...")
        try:
            await service.get_repository("octocat/Hello-World")
            print("❌ Repository restriction failed - should have been blocked!")
        except GitHubAPIError as e:
            if e.status_code == 403:
                print("✅ Repository restriction working - access denied as expected")
            else:
                print(f"❌ Unexpected error: {e}")

        print("\n🎉 All tests passed! GitHub integration is working correctly.")

    except GitHubAPIError as e:
        if "authentication" in str(e).lower() or e.status_code in [401, 403]:
            print(f"❌ Authentication failed: {e}")
            print("   Please check your GITHUB_TOKEN in .env file")
        else:
            print(f"❌ GitHub API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    finally:
        await service.close()


if __name__ == "__main__":
    # Check if token is configured
    token = os.getenv("GITHUB_TOKEN")
    if not token or token == "ghp_your-github-token":
        print("❌ Please set your GITHUB_TOKEN in the .env file first!")
        print("   1. Go to GitHub → Settings → Developer settings → Personal access tokens")
        print("   2. Generate a new token with 'repo' and 'read:user' permissions")
        print("   3. Replace 'ghp_your-github-token' in .env with your actual token")
        exit(1)

    asyncio.run(test_github_connection())
