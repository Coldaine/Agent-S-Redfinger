# Contributing to Agent-S-Redfinger

Thank you for your interest in contributing! This document outlines our workflow and standards.

## ⚡ Quick Setup

First time contributing? Run this to configure your Git workflow:

```bash
python scripts/setup_git_workflow.py
```

This sets up:
- Commit message template with reminders
- Helpful Git aliases
- Pre-push hook checklist

---

## 🚨 IMPORTANT: Development Workflow

**ALL CHANGES MUST:**
1. ✅ Be developed on a **feature branch** (never commit directly to `main`)
2. ✅ Go through a **Pull Request** review process
3. ✅ Be documented in `CHANGELOG.md`
4. ✅ Pass all pre-flight checks before PR submission

## 📋 Quick Start Checklist

Before making ANY changes:

- [ ] Create a feature branch: `git checkout -b feature/your-feature-name`
- [ ] Make your changes
- [ ] Update `CHANGELOG.md` under "Unreleased" section
- [ ] Run pre-flight checks (see below)
- [ ] Commit with descriptive message
- [ ] Push branch and open PR
- [ ] Request review
- [ ] Merge only after approval

## 🌿 Branch Naming Convention

Use descriptive branch names with prefixes:

- **Feature**: `feature/add-preflight-checks`
- **Bug Fix**: `bugfix/fix-temperature-validation`
- **Documentation**: `docs/update-readme-workflow`
- **Refactor**: `refactor/simplify-monitoring-logic`
- **Hotfix**: `hotfix/critical-api-error`

Examples:
```bash
git checkout -b feature/real-time-log-monitoring
git checkout -b bugfix/docker-image-cache
git checkout -b docs/git-workflow-guide
```

## 🔄 Development Workflow

### 1. Create Feature Branch

```bash
# Always start from latest main
git checkout main
git pull origin main

# Create your feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write clean, documented code
- Follow existing code style
- Add comments for complex logic
- Keep commits atomic and focused

### 3. Update CHANGELOG.md

**REQUIRED**: Add entry under `## [Unreleased]` section:

```markdown
## [Unreleased]

### Added
- Pre-flight checks for API key validation (#PR_NUMBER)
- Real-time log monitoring with 2-second intervals (#PR_NUMBER)

### Changed
- Refactored harness to use active polling instead of blocking (#PR_NUMBER)

### Fixed
- Temperature parameter compatibility check for GPT-5 (#PR_NUMBER)
```

Categories:
- **Added**: New features
- **Changed**: Changes to existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security fixes

### 4. Run Pre-flight Checks

**BEFORE PUSHING**, run these checks:

```powershell
# 0. Run the automated pre-commit check (recommended!)
python scripts/pre_commit_check.py

# 1. Check for Python syntax errors
python -m py_compile scripts/run_phase5_harness.py

# 2. Run the harness pre-flight check
python scripts/run_phase5_harness.py --dry-run

# 3. Verify Docker image exists (or build if needed)
docker images | Select-String "redfinger"

# 4. Check for linting issues (if you have linters installed)
# pylint gui_agents/s3/
# black --check .
```

### 5. Commit Changes

Write clear, descriptive commit messages:

```bash
# Good commit messages
git commit -m "feat: add pre-flight API key validation"
git commit -m "fix: resolve GPT-5 temperature compatibility issue"
git commit -m "refactor: improve log monitoring with real-time polling"
git commit -m "docs: add Git workflow guidelines to CONTRIBUTING.md"

# Bad commit messages (avoid these!)
git commit -m "fix stuff"
git commit -m "updates"
git commit -m "wip"
```

**Commit Message Format**:
```
<type>: <short description>

<optional detailed explanation>

Closes #<issue-number>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

### 6. Push Branch

```bash
git push origin feature/your-feature-name
```

### 7. Open Pull Request

1. Go to GitHub repository
2. Click "New Pull Request"
3. Select your feature branch
4. Fill out PR template (see below)
5. Request reviewers
6. Link related issues

### 8. PR Review Process

- Address all review comments
- Make requested changes
- Push additional commits to same branch
- Mark conversations as resolved
- Wait for approval

### 9. Merge

- **Squash and merge** (preferred for feature branches)
- **Delete branch** after merge
- Update local main:
  ```bash
  git checkout main
  git pull origin main
  ```

## 📝 Pull Request Template

When opening a PR, include:

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to not work as expected)
- [ ] Documentation update

## Changes Made
- Bullet point list of changes
- Another change
- And another

## Testing
Describe tests you've run:
- [ ] Pre-flight checks pass
- [ ] Docker image builds successfully
- [ ] Harness runs without errors
- [ ] Manual testing completed

## Checklist
- [ ] I have created a feature branch (not committing to main)
- [ ] I have updated CHANGELOG.md
- [ ] I have tested my changes
- [ ] I have added comments to complex code
- [ ] My code follows the existing style
- [ ] I have requested a review

## Related Issues
Closes #<issue-number>
```

## 🚫 What NOT to Do

### ❌ Never Commit Directly to Main

```bash
# WRONG - Don't do this!
git checkout main
git add .
git commit -m "changes"
git push origin main
```

This bypasses review and breaks the workflow.

### ❌ Never Force Push to Main

```bash
# WRONG - Don't do this!
git push -f origin main
```

This can destroy other people's work.

### ❌ Never Skip CHANGELOG Updates

Every PR should update `CHANGELOG.md`. No exceptions.

### ❌ Never Push Without Testing

Always run pre-flight checks before pushing.

## 🔍 Code Review Guidelines

### For Authors

- Keep PRs focused and small (easier to review)
- Respond to feedback promptly
- Don't take criticism personally
- Explain your reasoning when disagreeing

### For Reviewers

- Be constructive and respectful
- Focus on the code, not the person
- Ask questions instead of demanding changes
- Approve when ready, request changes when needed

## 📊 CHANGELOG.md Best Practices

### Good Changelog Entry

```markdown
### Added
- Pre-flight checks for API key validation before Docker spin-up (#123)
  - Validates OpenAI/ZAI API keys
  - Checks temperature compatibility with GPT-5
  - Verifies Docker image exists
  - Saves 2-3 minutes per failed run
```

### Bad Changelog Entry

```markdown
### Added
- Stuff (#123)
```

Be specific! Future you (and others) will thank you.

## 🆘 Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open an Issue with reproduction steps
- **Feature Requests**: Open an Issue with use case
- **Urgent**: Tag maintainers in PR/Issue

## 📚 Additional Resources

- [README.md](README.md) - Project overview and usage
- [VALIDATION_PLAN_DETAILED.md](docs/VALIDATION_PLAN_DETAILED.md) - Testing procedures
- [TROUBLESHOOTING_GUIDE.md](docs/TROUBLESHOOTING_GUIDE.md) - Common issues

## 🎯 Summary

**Remember the golden rule**: 
> Every change flows through: **Feature Branch → PR → Review → Merge → CHANGELOG**

No shortcuts. No exceptions. This keeps our codebase stable and our team aligned.

Thank you for contributing! 🙏
