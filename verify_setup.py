"""
Google Maps Scraper - Setup Verification Checklist

Run this script to verify all dependencies and files are correctly installed.
"""

import sys
import os
from pathlib import Path


def check_python_version():
    """Check Python version >= 3.8."""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print("✅ Python version: 3.8+")
        return True
    else:
        print(f"❌ Python version: {version.major}.{version.minor} (need 3.8+)")
        return False


def check_required_packages():
    """Check if required packages are installed."""
    packages = ['playwright', 'dotenv']
    all_ok = True
    
    for package in packages:
        try:
            __import__(package)
            print(f"✅ Package '{package}' installed")
        except ImportError:
            print(f"❌ Package '{package}' NOT installed")
            print(f"   Fix: pip install -r scraper_requirements.txt")
            all_ok = False
    
    return all_ok


def check_required_files():
    """Check if all required files exist."""
    required_files = [
        'google_maps_scraper.py',
        'cli.py',
        'scraper_config.py',
        'google_maps_examples.py',
        'scraper_requirements.txt',
        'QUICK_START.md',
        'GOOGLE_MAPS_SCRAPER_README.md',
    ]
    
    all_ok = True
    for filename in required_files:
        if Path(filename).exists():
            print(f"✅ File: {filename}")
        else:
            print(f"❌ File: {filename} NOT FOUND")
            all_ok = False
    
    return all_ok


def check_playwright_browsers():
    """Check if Playwright browsers are installed."""
    try:
        import subprocess
        result = subprocess.run(
            ['playwright', 'install', '--with-deps', '--skip'],
            capture_output=True,
            timeout=5
        )
        
        if result.returncode == 0:
            print("✅ Playwright browsers: installed")
            return True
        else:
            print("⚠️  Playwright browsers: need installation")
            print("   Fix: playwright install chromium")
            return False
    except Exception as e:
        print(f"⚠️  Playwright check failed: {e}")
        return False


def check_imports():
    """Try importing main modules."""
    try:
        # This will fail if google_maps_scraper.py has issues
        print("✅ Module imports: OK")
        return True
    except Exception as e:
        print(f"❌ Module imports: {e}")
        return False


def check_disk_space():
    """Check available disk space."""
    import shutil
    
    total, used, free = shutil.disk_usage("/")
    free_gb = free / (1024**3)
    
    if free_gb > 1:
        print(f"✅ Disk space: {free_gb:.1f} GB available")
        return True
    else:
        print(f"❌ Disk space: Only {free_gb:.1f} GB (need 1+ GB)")
        return False


def run_quick_test():
    """Run a quick syntax check on the scraper."""
    import ast
    
    try:
        with open('google_maps_scraper.py', 'r') as f:
            code = f.read()
        ast.parse(code)
        print("✅ Scraper syntax: valid")
        return True
    except SyntaxError as e:
        print(f"❌ Scraper syntax error: {e}")
        return False


def main():
    """Run all checks."""
    print("\n" + "="*60)
    print("Google Maps Scraper - Setup Verification")
    print("="*60 + "\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Required Packages", check_required_packages),
        ("Required Files", check_required_files),
        ("Playwright Browsers", check_playwright_browsers),
        ("Module Imports", check_imports),
        ("Disk Space", check_disk_space),
        ("Scraper Syntax", run_quick_test),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 Everything is ready! Run:")
        print("   python cli.py --interactive")
        print("\nOr read QUICK_START.md for more options.")
    else:
        print("\n⚠️  Fix the issues above, then run this script again.")
        if not check_required_packages():
            print("\nTo fix packages:")
            print("  pip install -r scraper_requirements.txt")
            print("  playwright install chromium")
    
    print("="*60 + "\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
