#!/usr/bin/env python3
"""Standalone health check script for debugging deployment issues."""

import sys
import os


def check_environment():
    """Check that all required environment variables are set."""
    required_vars = [
        "API_KEY_SECRET",
        "LANGEXTRACT_API_KEY",
        "ENV",
    ]
    
    missing = []
    present = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            present.append(f"{var}={value[:10]}..." if len(value) > 10 else f"{var}={value}")
        else:
            missing.append(var)
    
    print("Environment Variables Check:")
    print("-" * 50)
    for var in present:
        print(f"✓ {var}")
    
    if missing:
        print("\nMissing variables:")
        for var in missing:
            print(f"✗ {var}")
        return False
    
    print("\n✓ All required environment variables are set")
    return True


def check_imports():
    """Check that all required modules can be imported."""
    modules_to_check = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "pydantic",
        "httpx",
        "langextract",
        "dotenv",
    ]
    
    print("\n\nModule Import Check:")
    print("-" * 50)
    
    failed = []
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            failed.append(module)
    
    if failed:
        print(f"\n✗ Failed to import: {', '.join(failed)}")
        return False
    
    print("\n✓ All required modules can be imported")
    return True


def check_claim_validation():
    """Check if claim validation module is available."""
    print("\n\nClaim Validation Check:")
    print("-" * 50)
    
    try:
        from claim_validation import claim_validator, ClaimType
        print("✓ Claim validation module loaded successfully")
        print(f"  - Validation patterns initialized")
        return True
    except Exception as e:
        print(f"✗ Failed to load claim validation: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_config():
    """Check if config module loads without errors."""
    print("\n\nConfiguration Check:")
    print("-" * 50)
    
    try:
        from config import config
        print(f"✓ Config loaded successfully")
        print(f"  - Environment: {config.env}")
        print(f"  - API Key Secret: {'SET' if config.api_key_secret else 'NOT SET'}")
        print(f"  - LangExtract API Key: {'SET' if config.langextract_api_key else 'NOT SET'}")
        print(f"  - Database URL: {config.database_url}")
        print(f"  - Log Level: {config.log_level}")
        return True
    except Exception as e:
        print(f"✗ Failed to load config: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database():
    """Check if database can be initialized."""
    print("\n\nDatabase Check:")
    print("-" * 50)
    
    try:
        import asyncio
        from database import init_db
        
        asyncio.run(init_db())
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_app_creation():
    """Check if FastAPI app can be created."""
    print("\n\nApp Creation Check:")
    print("-" * 50)
    
    try:
        from api import app
        print(f"✓ FastAPI app created successfully")
        print(f"  - Title: {app.title}")
        print(f"  - Version: {app.version}")
        print(f"  - Routes: {len(app.routes)}")
        return True
    except Exception as e:
        print(f"✗ Failed to create app: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all health checks."""
    print("=" * 50)
    print("DEPLOYMENT HEALTH CHECK")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", check_environment),
        ("Module Imports", check_imports),
        ("Claim Validation", check_claim_validation),
        ("Configuration", check_config),
        ("Database", check_database),
        ("App Creation", check_app_creation),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n✗ Unexpected error in {name}: {e}")
            import traceback
            traceback.print_exc()
            results[name] = False
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ All checks passed! App should start successfully.")
        sys.exit(0)
    else:
        print("\n✗ Some checks failed. Review errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
