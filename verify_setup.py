#!/usr/bin/env python3
"""Verification script to check if the setup is correct."""

import sys
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    path = Path(filepath)
    if path.exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ {description} NOT FOUND: {filepath}")
        return False


def check_directory_exists(dirpath: str, description: str) -> bool:
    """Check if a directory exists."""
    path = Path(dirpath)
    if path.is_dir():
        print(f"✓ {description}: {dirpath}")
        return True
    else:
        print(f"✗ {description} NOT FOUND: {dirpath}")
        return False


def check_imports():
    """Check if core modules can be imported."""
    print("\n=== Checking Python Imports ===")
    errors = []

    modules = [
        "src.config",
        "src.domain.models",
        "src.domain.interfaces",
        "src.domain.use_cases",
        "src.infrastructure.logging_config",
        "src.infrastructure.browser_manager",
        "src.infrastructure.twitter_repository",
        "src.api.schemas",
        "src.api.routes",
        "src.api.app",
        "src.mcp.server",
    ]

    for module in modules:
        try:
            __import__(module)
            print(f"✓ Import successful: {module}")
        except ImportError as e:
            print(f"✗ Import failed: {module} - {e}")
            errors.append((module, str(e)))

    return len(errors) == 0, errors


def main():
    """Main verification function."""
    print("=" * 60)
    print("Twitter MCP Agent - Setup Verification")
    print("=" * 60)

    all_checks_passed = True

    # Check directory structure
    print("\n=== Checking Directory Structure ===")
    all_checks_passed &= check_directory_exists("src", "Main source directory")
    all_checks_passed &= check_directory_exists("src/domain", "Domain layer")
    all_checks_passed &= check_directory_exists("src/infrastructure", "Infrastructure layer")
    all_checks_passed &= check_directory_exists("src/api", "API layer")
    all_checks_passed &= check_directory_exists("src/mcp", "MCP layer")

    # Check essential files
    print("\n=== Checking Essential Files ===")
    all_checks_passed &= check_file_exists("src/config.py", "Configuration")
    all_checks_passed &= check_file_exists("src/domain/models.py", "Domain models")
    all_checks_passed &= check_file_exists("src/domain/interfaces.py", "Domain interfaces")
    all_checks_passed &= check_file_exists("src/domain/use_cases.py", "Use cases")
    all_checks_passed &= check_file_exists("src/infrastructure/browser_manager.py", "Browser manager")
    all_checks_passed &= check_file_exists("src/infrastructure/twitter_repository.py", "Twitter repository")
    all_checks_passed &= check_file_exists("src/api/app.py", "FastAPI app")
    all_checks_passed &= check_file_exists("src/api/routes.py", "API routes")
    all_checks_passed &= check_file_exists("src/mcp/server.py", "MCP server")

    # Check entry points
    print("\n=== Checking Entry Points ===")
    all_checks_passed &= check_file_exists("run_rest_api.py", "REST API entry point")
    all_checks_passed &= check_file_exists("run_mcp_server.py", "MCP server entry point")
    all_checks_passed &= check_file_exists("login_and_save_auth.py", "Auth script")

    # Check documentation
    print("\n=== Checking Documentation ===")
    all_checks_passed &= check_file_exists("README.md", "README")
    all_checks_passed &= check_file_exists("ARCHITECTURE.md", "Architecture docs")
    all_checks_passed &= check_file_exists("requirements.txt", "Requirements")

    # Check configuration
    print("\n=== Checking Configuration ===")
    all_checks_passed &= check_file_exists(".env", "Environment config")
    all_checks_passed &= check_file_exists(".gitignore", "Git ignore file")

    # Check auth file (warning if missing)
    print("\n=== Checking Authentication ===")
    if not check_file_exists("auth.json", "Authentication file"):
        print("  ⚠ Warning: auth.json not found. Run 'python login_and_save_auth.py' first.")
        print("  ⚠ This is expected on first setup.")

    # Check Python imports
    imports_ok, import_errors = check_imports()
    all_checks_passed &= imports_ok

    # Final summary
    print("\n" + "=" * 60)
    if all_checks_passed:
        print("✓ ALL CHECKS PASSED!")
        print("\nNext steps:")
        print("1. Ensure auth.json exists: python login_and_save_auth.py")
        print("2. Install dependencies: pip install -r requirements.txt")
        print("3. Start REST API: python run_rest_api.py")
        print("4. Or start MCP server: python run_mcp_server.py")
        print("\nSee README.md for detailed usage instructions.")
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        print("\nPlease review the errors above.")
        if import_errors:
            print("\nImport errors detected. You may need to:")
            print("1. Install dependencies: pip install -r requirements.txt")
            print("2. Ensure you're in the project root directory")
        return 1


if __name__ == "__main__":
    sys.exit(main())
