# Git Workflow Quick Reference

## 🔄 Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FEATURE DEVELOPMENT                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  1. Create Feature Branch                     │
    │     git checkout -b feature/my-feature        │
    └───────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  2. Make Changes                              │
    │     • Write code                              │
    │     • Add comments                            │
    │     • Test locally                            │
    └───────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  3. Update CHANGELOG.md (REQUIRED!)           │
    │     • Add entry under [Unreleased]            │
    │     • Describe what changed                   │
    │     • Include PR number placeholder           │
    └───────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  4. Run Pre-Commit Checks                     │
    │     python scripts/pre_commit_check.py        │
    │     • Verifies not on main branch             │
    │     • Checks CHANGELOG updated                │
    │     • Validates Python syntax                 │
    └───────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  5. Commit Changes                            │
    │     git add .                                 │
    │     git commit                                │
    │     • Use template for message                │
    │     • Follow format: type: description        │
    └───────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  6. Push Feature Branch                       │
    │     git push origin feature/my-feature        │
    └───────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  7. Open Pull Request                         │
    │     • Use PR template                         │
    │     • Request reviewers                       │
    │     • Link related issues                     │
    └───────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  8. Code Review                               │
    │     • Address feedback                        │
    │     • Make requested changes                  │
    │     • Push updates to same branch             │
    └───────────────────────────────────────────────┘
                            ↓
    ┌───────────────────────────────────────────────┐
    │  9. Merge to Main                             │
    │     • Squash and merge                        │
    │     • Delete feature branch                   │
    │     • Pull latest main                        │
    └───────────────────────────────────────────────┘
```

## 📝 Common Commands

### Initial Setup (One Time)
```bash
# Configure Git workflow
python scripts/setup_git_workflow.py
```

### Starting New Work
```bash
# Always start from latest main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-feature-name

# Or use alias (if setup script ran)
git feature my-feature-name
```

### During Development
```bash
# Check status
git status

# Check CHANGELOG
git diff CHANGELOG.md

# Run pre-commit checks
python scripts/pre_commit_check.py
```

### Committing Changes
```bash
# Stage changes
git add .

# Commit (opens template editor)
git commit

# Or commit with inline message
git commit -m "feat: add pre-flight checks for API validation"
```

### Pushing and PR
```bash
# Push your branch
git push origin feature/my-feature-name

# Or use alias (if setup script ran)
git pushf

# Then open PR on GitHub
```

## ✅ Pre-Commit Checklist

Before every commit, verify:

- [ ] 🌿 On a feature branch (not main)
- [ ] 📝 CHANGELOG.md updated
- [ ] 🧪 Changes tested locally
- [ ] 💬 Code comments added
- [ ] ✅ Pre-commit check passed
- [ ] 📏 Follows code style

**Quick check**: `python scripts/pre_commit_check.py`

## 🚫 What NOT to Do

```bash
# ❌ NEVER commit directly to main
git checkout main
git commit -m "changes"
git push

# ❌ NEVER force push to main
git push -f origin main

# ❌ NEVER skip CHANGELOG update
# Every PR needs a CHANGELOG entry!

# ❌ NEVER push without testing
# Always run pre-commit checks first
```

## 📊 Commit Message Format

```
<type>: <short description>

<optional detailed explanation>

Closes #<issue-number>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Tests
- `chore`: Maintenance

### Examples

**Good:**
```
feat: add pre-flight API key validation

Validates OpenAI and ZAI API keys before Docker spin-up.
Saves 2-3 minutes per failed run by catching errors early.

Closes #42
```

**Good:**
```
fix: resolve GPT-5 temperature compatibility issue

GPT-5 models don't accept explicit temperature parameter.
Updated code to use default temperature for GPT-5.
```

**Bad:**
```
fix stuff
```

## 🔧 Helpful Aliases (After Setup)

If you ran `python scripts/setup_git_workflow.py`, these aliases are available:

```bash
git co <branch>        # Checkout
git br                 # List branches
git st                 # Status
git cm                 # Commit
git pushf              # Push current branch
git feature <name>     # Create feature branch
git bugfix <name>      # Create bugfix branch
git changelog          # View CHANGELOG diff
```

## 🆘 Common Issues

### "I committed to main by accident!"

```bash
# Don't panic! Fix it:
git reset HEAD~1            # Undo last commit (keep changes)
git checkout -b feature/my-feature  # Create branch
git add .
git commit -m "feat: my changes"
git push origin feature/my-feature
```

### "I forgot to update CHANGELOG!"

```bash
# Add to your existing commit
# (Before pushing)
git add CHANGELOG.md
git commit --amend --no-edit
```

### "I need to sync with main"

```bash
# While on feature branch
git checkout main
git pull origin main
git checkout feature/my-feature
git rebase main

# Or use merge
git merge main
```

## 📚 Learn More

- [CONTRIBUTING.md](../CONTRIBUTING.md) - Full guidelines
- [CHANGELOG.md](../CHANGELOG.md) - Project history
- [README.md](../README.md) - Project overview
- [Pull Request Template](../.github/pull_request_template.md)

## 💡 Pro Tips

1. **Commit often**: Small, focused commits are easier to review
2. **Descriptive messages**: Future you will thank you
3. **Test before push**: Catch issues early
4. **Update CHANGELOG**: Keep it current
5. **Request reviews**: Fresh eyes catch bugs
6. **Be patient**: Good reviews take time
7. **Ask questions**: No question is too small

---

**Remember**: Quality over speed. Taking time to follow the workflow saves everyone time in the long run! 🚀
