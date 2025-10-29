#!/usr/bin/env python3
"""
Setup Git workflow configuration for Agent-S-Redfinger.

This script configures Git to use our commit message template and sets up
helpful aliases for the development workflow.

Usage:
    python scripts/setup_git_workflow.py
"""

import os
import subprocess
import sys

def run_git_command(cmd):
    """Run a git command and return success status."""
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.decode()}")
        return False

def main():
    print("=" * 60)
    print("  Git Workflow Setup for Agent-S-Redfinger")
    print("=" * 60)
    
    # Get the repo root
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_root = result.stdout.strip()
    except subprocess.CalledProcessError:
        print("❌ Not in a Git repository!")
        return 1
    
    os.chdir(repo_root)
    
    print(f"\n📂 Repository root: {repo_root}")
    
    # 1. Set commit message template
    print("\n[1/4] Setting up commit message template...")
    template_path = os.path.join(repo_root, ".gitmessage")
    if os.path.exists(template_path):
        if run_git_command(["git", "config", "commit.template", template_path]):
            print("✅ Commit template configured (.gitmessage)")
        else:
            print("❌ Failed to set commit template")
    else:
        print("⚠️  .gitmessage file not found")
    
    # 2. Set up helpful Git aliases
    print("\n[2/4] Setting up Git aliases...")
    
    aliases = [
        ("co", "checkout", "Shorthand for checkout"),
        ("br", "branch", "Shorthand for branch"),
        ("st", "status", "Shorthand for status"),
        ("cm", "commit", "Shorthand for commit"),
        ("pushf", "push origin HEAD", "Push current branch"),
        ("feature", "checkout -b feature/", "Create feature branch"),
        ("bugfix", "checkout -b bugfix/", "Create bugfix branch"),
        ("changelog", "!git diff CHANGELOG.md", "Show CHANGELOG changes"),
    ]
    
    for alias, command, description in aliases:
        if run_git_command(["git", "config", "--local", f"alias.{alias}", command]):
            print(f"✅ Alias '{alias}' → '{command}'")
        else:
            print(f"❌ Failed to set alias '{alias}'")
    
    # 3. Set up pre-push hook reminder (optional)
    print("\n[3/4] Setting up pre-push hook...")
    hooks_dir = os.path.join(repo_root, ".git", "hooks")
    pre_push_hook = os.path.join(hooks_dir, "pre-push")
    
    hook_content = """#!/bin/sh
# Pre-push hook reminder

echo ""
echo "⚠️  Pre-Push Checklist:"
echo "   ✅ Did you update CHANGELOG.md?"
echo "   ✅ Did you test your changes?"
echo "   ✅ Did you run: python scripts/pre_commit_check.py?"
echo ""
echo "Press Enter to continue push, or Ctrl+C to cancel..."
read -r

exit 0
"""
    
    try:
        with open(pre_push_hook, "w") as f:
            f.write(hook_content)
        
        # Make executable (Unix-like systems)
        if os.name != "nt":
            os.chmod(pre_push_hook, 0o755)
        
        print("✅ Pre-push hook installed")
    except Exception as e:
        print(f"⚠️  Could not install pre-push hook: {e}")
    
    # 4. Configure branch protection (informational)
    print("\n[4/4] Branch protection recommendations...")
    print("ℹ️  Consider these GitHub settings:")
    print("   • Protect 'main' branch")
    print("   • Require pull request reviews")
    print("   • Require status checks")
    print("   • Require branches to be up to date")
    print("   Go to: Settings → Branches → Add rule")
    
    # Summary
    print("\n" + "=" * 60)
    print("  Setup Complete!")
    print("=" * 60)
    
    print("\n✅ Your Git workflow is configured!")
    print("\n📚 Quick Reference:")
    print("   • git feature <name>  → Create feature branch")
    print("   • git bugfix <name>   → Create bugfix branch")
    print("   • git st              → Check status")
    print("   • git changelog       → View CHANGELOG changes")
    print("   • git pushf           → Push current branch")
    
    print("\n🔧 Helpful Commands:")
    print("   python scripts/pre_commit_check.py  → Check before commit")
    print("   git commit                          → Opens template editor")
    
    print("\n📖 Documentation:")
    print("   • CONTRIBUTING.md → Full workflow guide")
    print("   • CHANGELOG.md    → Project changes")
    print("   • README.md       → Project overview")
    
    print("\n🚀 Next Steps:")
    print("   1. Create a feature branch: git feature my-new-feature")
    print("   2. Make your changes")
    print("   3. Update CHANGELOG.md")
    print("   4. Run: python scripts/pre_commit_check.py")
    print("   5. Commit and push")
    print("   6. Open a Pull Request")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
