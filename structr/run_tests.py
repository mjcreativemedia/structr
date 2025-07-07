#!/usr/bin/env python3
"""
Test runner for Structr

Runs all unit tests and provides detailed reporting.
"""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run all tests with pytest"""
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Run pytest with verbose output and coverage if available
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    # Add coverage if pytest-cov is available
    try:
        import pytest_cov
        cmd.extend([
            "--cov=models",
            "--cov=schemas", 
            "--cov=llm_service",
            "--cov=export",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
        print("Running tests with coverage...")
    except ImportError:
        print("Running tests without coverage (install pytest-cov for coverage reporting)...")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Install it with: pip install pytest")
        return 1


def run_specific_test(test_file):
    """Run a specific test file"""
    
    if not test_file.startswith("tests/"):
        test_file = f"tests/{test_file}"
    
    if not test_file.endswith(".py"):
        test_file = f"{test_file}.py"
    
    cmd = [
        sys.executable, "-m", "pytest",
        test_file,
        "-v",
        "--tb=long",
        "--color=yes"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Install it with: pip install pytest")
        return 1


def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Structr tests")
    parser.add_argument("--file", "-f", help="Run specific test file")
    parser.add_argument("--install-deps", action="store_true", 
                       help="Install test dependencies")
    
    args = parser.parse_args()
    
    if args.install_deps:
        print("Installing test dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "pytest>=7.0.0", 
            "pytest-cov>=4.0.0",
            "beautifulsoup4>=4.12.0"
        ])
        return 0
    
    if args.file:
        print(f"Running specific test: {args.file}")
        return run_specific_test(args.file)
    else:
        print("Running all tests...")
        return run_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)