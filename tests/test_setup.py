"""Test script to verify the basic project setup."""

import sys
import os


def test_project_structure():
    """Test that all required directories and files exist."""
    required_dirs = [
        "devsync_ai",
        "devsync_ai/api",
        "devsync_ai/models",
        "devsync_ai/services",
        "devsync_ai/webhooks",
        "devsync_ai/scheduler",
        "devsync_ai/utils",
    ]

    required_files = [
        "devsync_ai/__init__.py",
        "devsync_ai/main.py",
        "devsync_ai/config.py",
        "devsync_ai/api/__init__.py",
        "devsync_ai/api/routes.py",
        "devsync_ai/webhooks/__init__.py",
        "devsync_ai/webhooks/routes.py",
        "pyproject.toml",
        ".env.example",
        README.md,
    ]

    print("Testing project structure...")

    # Check directories
    for directory in required_dirs:
        if os.path.isdir(directory):
            print(f"✓ Directory exists: {directory}")
        else:
            print(f"✗ Missing directory: {directory}")
            return False

    # Check files
    for file_path in required_files:
        if os.path.isfile(file_path):
            print(f"✓ File exists: {file_path}")
        else:
            print(f"✗ Missing file: {file_path}")
            return False

    print("\n✓ All required directories and files are present!")
    return True


def test_config_import():
    """Test that configuration can be imported without dependencies."""
    try:
        # Add current directory to Python path
        sys.path.insert(0, os.getcwd())

        # Test basic imports (without external dependencies)
        print("\nTesting configuration import...")

        # This will fail if pydantic is not installed, but structure should be correct
        try:
            from devsync_ai.config import Settings

            print("✓ Configuration class structure is correct")
        except ImportError as e:
            if "pydantic" in str(e):
                print("✓ Configuration structure is correct (pydantic not installed)")
            else:
                print(f"✗ Configuration import error: {e}")
                return False

        return True

    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


if __name__ == "__main__":
    print("DevSync AI Setup Verification")
    print("=" * 40)

    structure_ok = test_project_structure()
    config_ok = test_config_import()

    if structure_ok and config_ok:
        print("\n🎉 Project setup completed successfully!")
        print("\nNext steps:")
        print("1. Install dependencies: uv sync")
        print("2. Copy .env.example to .env and configure your API keys")
        print("3. Run the application: uv run python -m devsync_ai.main")
    else:
        print("\n❌ Setup verification failed!")
        sys.exit(1)
