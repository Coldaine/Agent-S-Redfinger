#!/usr/bin/env python3
"""
Pre-commit reminder script - Run this before committing to ensure workflow compliance.

Usage:
    python scripts/pre_commit_check.py
"""

import os
import sys
import subprocess

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_check(passed, message):
    icon = "✅" if passed else "❌"
    print(f"{icon} {message}")

def check_branch():
    """Ensure we're not on main branch."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        branch = result.stdout.strip()
        
        if branch == "main":
            print_check(False, "You are on 'main' branch!")
            print("\n⚠️  WARNING: Direct commits to 'main' are not allowed!")
            print("   Create a feature branch instead:")
            print("   git checkout -b feature/your-feature-name")
            return False
        else:
            print_check(True, f"On feature branch: {branch}")
            return True
    except subprocess.CalledProcessError:
        print_check(False, "Could not determine current branch")
        return False

def check_changelog_updated():
    """Check if CHANGELOG.md has been modified."""
    try:
        # Check if CHANGELOG.md is staged
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True,
            text=True,
            check=True
        )
        
        staged_files = result.stdout.strip().split("\n")
        
        if "CHANGELOG.md" in staged_files:
            print_check(True, "CHANGELOG.md has been updated")
            return True
        else:
            # Check if CHANGELOG.md has unstaged changes
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True
            )
            
            unstaged_files = result.stdout.strip().split("\n")
            
            if "CHANGELOG.md" in unstaged_files:
                print_check(False, "CHANGELOG.md modified but not staged")
                print("   Run: git add CHANGELOG.md")
                return False
            else:
                print_check(False, "CHANGELOG.md not updated")
                print("\n⚠️  REMINDER: Update CHANGELOG.md before committing!")
                print("   Add your changes under the [Unreleased] section")
                return False
    except subprocess.CalledProcessError:
        print_check(False, "Could not check CHANGELOG.md status")
        return False

def check_python_syntax():
    """Run basic Python syntax checks on changed .py files."""
    try:
        # Get changed Python files
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            check=True
        )
        
        py_files = [f for f in result.stdout.strip().split("\n") if f.endswith(".py")]
        
        if not py_files:
            print_check(True, "No Python files to check")
            return True
        
        all_valid = True
        for py_file in py_files:
            if os.path.exists(py_file):
                try:
                    subprocess.run(
                        ["python", "-m", "py_compile", py_file],
                        capture_output=True,
                        check=True
                    )
                    print_check(True, f"Syntax valid: {py_file}")
                except subprocess.CalledProcessError as e:
                    print_check(False, f"Syntax error: {py_file}")
                    print(f"   Error: {e.stderr.decode()}")
                    all_valid = False
        
        return all_valid
    except subprocess.CalledProcessError:
        print_check(False, "Could not check Python files")
        return False

def main():
    print_header("Pre-Commit Workflow Check")
    
    checks = []
    
    # 1. Check we're not on main
    print("\n[1/3] Checking branch...")
    checks.append(check_branch())
    
    # 2. Check CHANGELOG.md updated
    print("\n[2/3] Checking CHANGELOG.md...")
    checks.append(check_changelog_updated())
    
    # 3. Check Python syntax
    print("\n[3/3] Checking Python syntax...")
    checks.append(check_python_syntax())
    
    # Summary
    print_header("Summary")
    
    if all(checks):
        print("\n✅ All checks passed! Safe to commit.")
        print("\nNext steps:")
        print("  1. git commit -m 'feat: your descriptive message'")
        print("  2. git push origin <your-branch-name>")
        print("  3. Open a Pull Request on GitHub")
        return 0
    else:
        print("\n❌ Some checks failed. Please fix issues above.")
        print("\nReminders:")
        print("  • Never commit directly to main")
        print("  • Always update CHANGELOG.md")
        print("  • Fix syntax errors before committing")
        print("\nSee CONTRIBUTING.md for full workflow guide")
        return 1

if __name__ == "__main__":
    sys.exit(main())
