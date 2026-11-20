"""
verify_setup.py — Run this to confirm Sprint 1 Step 1 is complete.

Usage:
    python verify_setup.py

Expected output: All checks PASSED
If any check FAILS, read the error message and fix it before proceeding.
"""

import sys
import os
from pathlib import Path


def check(name: str, condition: bool, fix: str = "") -> bool:
    """Print pass/fail for a check."""
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {name}")
    if not condition and fix:
        print(f"         FIX: {fix}")
    return condition


def main() -> None:
    print("\n" + "=" * 60)
    print("  Insurance Claims Platform — Setup Verification")
    print("=" * 60 + "\n")

    all_passed = True
    results = []

    # ---- Python Version ----
    print("Python Environment:")
    major, minor = sys.version_info.major, sys.version_info.minor
    r = check(
        f"Python 3.12+ (found: {major}.{minor})",
        major == 3 and minor >= 12,
        "Run: C:\\Python312\\python.exe -m venv venv --clear",
    )
    results.append(r)

    r = check(
        "Running inside venv (not system/base Python)",
        hasattr(sys, "real_prefix") or (
            hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
        ),
        "Activate venv: .\\venv\\Scripts\\Activate.ps1",
    )
    results.append(r)

    r = check(
        "No Anaconda paths in sys.path",
        not any("anaconda3\\Lib" in p and "envs" not in p
                for p in sys.path if p),
        "Use C:\\Python312\\python.exe -m venv venv (not Anaconda Python)",
    )
    results.append(r)

    # ---- Core Packages ----
    print("\nCore Production Packages:")
    packages = [
        ("fastapi", "fastapi"),
        ("sqlalchemy", "sqlalchemy"),
        ("pydantic", "pydantic"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("httpx", "httpx"),
        ("tenacity", "tenacity"),
        ("python-dotenv", "dotenv"),
        ("structlog", "structlog"),
    ]

    for pkg_name, import_name in packages:
        try:
            mod = __import__(import_name)
            version = getattr(mod, "__version__", "installed")
            r = check(f"{pkg_name} ({version})", True)
        except ImportError:
            r = check(
                f"{pkg_name} (MISSING)",
                False,
                f"Run: pip install {pkg_name}",
            )
        results.append(r)

    # ---- Dev Tools ----
    print("\nDev Tools:")
    dev_tools = [
        ("pytest", "pytest"),
        ("ruff", "ruff"),
        ("faker", "faker"),
    ]

    for pkg_name, import_name in dev_tools:
        try:
            mod = __import__(import_name)
            version = getattr(mod, "__version__", "installed")
            r = check(f"{pkg_name} ({version})", True)
        except ImportError:
            r = check(
                f"{pkg_name} (MISSING)",
                False,
                f"Run: pip install {pkg_name}",
            )
        results.append(r)

    # ---- Project Structure ----
    print("\nProject Structure:")
    base = Path(__file__).parent
    required_files = [
        "requirements.txt",
        "requirements-dev.txt",
        ".env.example",
        ".gitignore",
        "Makefile",
        "README.md",
        "TRACKER.md",
        "ruff.toml",
        "pytest.ini",
        "environment.yml",
        ".python-version",
        ".github/workflows/ci.yml",
    ]

    required_dirs = [
        "mock_api/app",
        "etl/pipeline",
        "database/migrations",
        "ml/classification",
        "api/app",
        "infrastructure/terraform",
        "docs/architecture",
    ]

    for f in required_files:
        r = check(f"File exists: {f}", (base / f).exists())
        results.append(r)

    for d in required_dirs:
        r = check(f"Directory exists: {d}/", (base / d).is_dir())
        results.append(r)

    # ---- .env Check ----
    print("\nSecurity Checks:")
    env_file = base / ".env"
    env_example = base / ".env.example"

    r = check(
        ".env.example exists",
        env_example.exists(),
        "This file should be committed to Git as a template",
    )
    results.append(r)

    # Check .gitignore protects .env
    gitignore = base / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text()
        r = check(
            ".env is in .gitignore",
            "\n.env\n" in content or content.startswith(".env\n"),
            "Add .env to .gitignore immediately!",
        )
        results.append(r)

    # ---- Summary ----
    passed = sum(results)
    total = len(results)
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed}/{total} checks passed")
    print("=" * 60)

    if passed == total:
        print("\n  Sprint 1, Step 1 COMPLETE!")
        print("  You are ready for Step 2: Synthetic Data Generation\n")
    else:
        failed = total - passed
        print(f"\n  {failed} check(s) FAILED.")
        print("  Fix the issues above before proceeding.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
