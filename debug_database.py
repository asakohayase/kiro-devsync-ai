#!/usr/bin/env python3
"""Debug script to check database state for PR-JIRA integration."""

import asyncio
import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

sys.path.append(".")

from devsync_ai.database.connection import get_database


async def debug_database():
    """Check the current state of PR-JIRA mappings."""
    try:
        db = await get_database()

        print("🔍 Checking pr_ticket_mappings table...")

        # Get all PR-ticket mappings
        result = await db.select(table="pr_ticket_mappings", filters=None, select_fields="*")

        print(f"Debug - result type: {type(result)}")
        print(f"Debug - result: {result}")

        if isinstance(result, dict) and result.get("success"):
            mappings = result["data"]
            print(f"📊 Found {len(mappings)} PR-ticket mappings:")

            for mapping in mappings:
                print(
                    f"  PR #{mapping['pr_number']} → {mapping['ticket_key']} ({mapping['created_at']})"
                )

            # Check for recent mappings (last 5)
            if mappings:
                print(f"\n🔍 Most recent mappings:")
                recent = sorted(mappings, key=lambda x: x["created_at"], reverse=True)[:5]
                for mapping in recent:
                    print(f"  PR #{mapping['pr_number']} → {mapping['ticket_key']}")
                    print(f"    URL: {mapping.get('pr_url', 'N/A')}")
                    print(f"    Created: {mapping['created_at']}")
                    print()
        else:
            print(f"❌ Error querying mappings: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_database())
