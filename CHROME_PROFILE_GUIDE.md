# Chrome Profile Integration Guide

## Overview

The agent now supports using your existing Chrome profile, giving it access to:
- ✅ Your logged-in sessions (Gmail, GitHub, Netflix, etc.)
- ✅ Cookies and authentication tokens
- ✅ Browser history and bookmarks
- ✅ Installed extensions
- ✅ Saved passwords (Chrome Sync)
- ✅ Autofill data
- ✅ Site preferences

---

## Quick Start

### 1. Find Your Chrome Profile

Run the profile finder:
```powershell
C:/Agent-S-Redfinger/.venv/Scripts/python.exe find_chrome_profile.py
```

**Your profile path** (found on your system):
```
C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default
```

### 2. Close All Chrome Windows

⚠️ **CRITICAL**: Chrome profile must not be in use!
- Close ALL Chrome browser windows
- Check Task Manager to ensure no Chrome processes running
- Otherwise you'll get a "profile in use" error

### 3. Run Agent with Your Profile

```powershell
$env:OPENAI_BASE_URL = $null
C:/Agent-S-Redfinger/.venv/Scripts/python.exe -m src.demos.agent_demo `
  --start "https://gmail.com" `
  --goal "Check inbox" `
  --provider openai `
  --model gpt-5 `
  --profile "C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default" `
  --max-steps 3
```

---

## Example Use Cases

### 1. Check Gmail
```powershell
C:/Agent-S-Redfinger/.venv/Scripts/python.exe -m src.demos.agent_demo `
  --start "https://gmail.com" `
  --goal "Find unread emails" `
  --profile "C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default" `
  --provider openai --model gpt-5 --max-steps 2
```

### 2. GitHub Repository
```powershell
C:/Agent-S-Redfinger/.venv/Scripts/python.exe -m src.demos.agent_demo `
  --start "https://github.com/yourname/yourrepo" `
  --goal "Check latest issues" `
  --profile "C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default" `
  --provider openai --model gpt-5 --max-steps 3
```

### 3. Social Media
```powershell
C:/Agent-S-Redfinger/.venv/Scripts/python.exe -m src.demos.agent_demo `
  --start "https://twitter.com" `
  --goal "Check notifications" `
  --profile "C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default" `
  --provider openai --model gpt-5 --max-steps 2
```

### 4. Cloud Services
```powershell
C:/Agent-S-Redfinger/.venv/Scripts/python.exe -m src.demos.agent_demo `
  --start "https://drive.google.com" `
  --goal "Find recent documents" `
  --profile "C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default" `
  --provider openai --model gpt-5 --max-steps 3
```

---

## Security Recommendations

### ⚠️ Using Your Main Profile (NOT RECOMMENDED for production)

**Risks**:
- Agent has full access to all your accounts
- Could accidentally perform sensitive actions
- Browsing history exposed to logs/screenshots
- Saved passwords accessible

**Only use if**:
- Testing/development only
- You trust the agent code completely
- You're monitoring every action

### ✅ Create a Dedicated "Agent Profile" (RECOMMENDED)

**Steps**:

1. **Open Chrome** (your normal profile)

2. **Click your profile icon** (top-right corner)

3. **Click "Add" to create new profile**
   - Name it: "Agent Profile"
   - Choose an icon (e.g., robot emoji 🤖)
   - Don't sync with Google account (or use separate agent account)

4. **In the new profile, sign in to services you want the agent to access**:
   - Gmail (use agent-specific account or secondary)
   - GitHub (personal access token or read-only account)
   - Other services as needed

5. **Configure extensions** (if any):
   - Ad blockers (optional)
   - Security extensions (optional)
   - Keep it minimal for best performance

6. **Close Chrome**

7. **Find the new profile path**:
   ```powershell
   C:/Agent-S-Redfinger/.venv/Scripts/python.exe find_chrome_profile.py
   ```
   Look for "Profile 1" or similar

8. **Use the new profile**:
   ```powershell
   --profile "C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Profile 1"
   ```

---

## Benefits of Using a Profile

### Without Profile (Current Default)
- ❌ Not logged in to any services
- ❌ Must handle login flows manually
- ❌ No cookies or session persistence
- ❌ Limited access to protected content
- ❌ Fresh browser state every run

### With Your Profile
- ✅ Already logged in to Gmail, GitHub, etc.
- ✅ Agent can access your authenticated content
- ✅ Cookies and tokens persist between runs
- ✅ Can interact with services requiring auth
- ✅ Your preferences and settings apply

---

## Troubleshooting

### Error: "Profile in use"
**Cause**: Chrome is already running with this profile  
**Fix**: Close ALL Chrome windows and try again

### Error: "Profile not found"
**Cause**: Invalid path or profile doesn't exist  
**Fix**: Run `find_chrome_profile.py` to get correct path

### Browser opens but doesn't use profile
**Cause**: Path might have spaces or special characters  
**Fix**: Make sure path is in quotes in the command

### Extensions not loading
**Cause**: Some extensions may be disabled in automation mode  
**Fix**: Extensions will load, but some may detect automation and behave differently

### Profile gets corrupted
**Cause**: Rare, but can happen if browser crashes during automation  
**Fix**: 
1. Use a dedicated agent profile (not your main one)
2. Chrome will usually auto-recover
3. Worst case: delete the profile folder and recreate

---

## Environment Variable Method

You can also set a default profile in your `.env`:

```bash
# Add to .env
CHROME_PROFILE_DIR=C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default
```

Then modify `agent_demo.py` to read it:
```python
profile = args.profile or os.getenv("CHROME_PROFILE_DIR")
```

---

## Advanced: Multiple Profiles for Different Tasks

Create specialized profiles:

### Profile 1: "Work Agent"
- Signed into work Gmail
- Work GitHub account
- Work Slack
- Corporate SSO

### Profile 2: "Personal Agent"
- Personal email
- Personal GitHub
- Social media
- Shopping sites

### Profile 3: "Testing Agent"
- Test accounts only
- Minimal data
- Disposable

Use different profiles with `--profile` flag:
```powershell
# Work tasks
--profile "C:\...\User Data\Profile 1"

# Personal tasks
--profile "C:\...\User Data\Profile 2"

# Testing
--profile "C:\...\User Data\Profile 3"
```

---

## Technical Details

### What Changed in the Code

**`browser_selenium.py`**:
- Added `profile_dir` parameter to `__init__`
- Added `--user-data-dir` Chrome option when profile specified
- Logs profile path when used

**`web_agent.py`**:
- Added `profile_dir` to `AgentConfig`
- Constructor accepts `profile_dir` parameter
- Passes profile to driver initialization
- Logs profile in run output

**`agent_demo.py`**:
- Added `--profile` command-line argument
- Passes profile to agent config

### Chrome User Data Directory Structure
```
C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\
├── Default/                  ← Your default profile
│   ├── Cookies              ← Session cookies
│   ├── History              ← Browsing history
│   ├── Preferences          ← Settings
│   ├── Extensions/          ← Installed extensions
│   └── ...
├── Profile 1/               ← Additional profile
├── Profile 2/               ← Another profile
└── ...
```

---

## Example Session with Profile

```powershell
# Make sure Chrome is closed!

$env:OPENAI_BASE_URL = $null
C:/Agent-S-Redfinger/.venv/Scripts/python.exe -m src.demos.agent_demo `
  --start "https://github.com" `
  --goal "Check notifications" `
  --provider openai `
  --model gpt-5 `
  --profile "C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default" `
  --max-steps 2
```

**Expected Output**:
```
================================================================================
🔍 AGENT RUN: 2025-10-31 12:00:00
================================================================================
📍 START URL: https://github.com
🎯 GOAL: Check notifications
📂 LOGS: C:\Agent-S-Redfinger\logs\run_20251031_120000
🔐 CHROME PROFILE: C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default
================================================================================

🔐 Using Chrome profile: C:\Users\pmacl\AppData\Local\Google\Chrome\User Data\Default
📸 Saved initial page screenshot: step_0_initial_page.png
   Current URL: https://github.com

⚡ STEP 1/2
...
```

**You'll notice**:
- Already logged in to GitHub (your profile icon visible)
- Agent can see your notifications bell
- Agent can access your repos and settings
- No login flow required!

---

## Summary

✅ **Feature Added**: Chrome profile support  
✅ **How to Use**: Add `--profile "path"` to any command  
✅ **Recommendation**: Create dedicated "Agent Profile"  
✅ **Benefits**: Access logged-in services automatically  
⚠️ **Caution**: Profile must not be in use (close Chrome first)

**Next Steps**:
1. Run `find_chrome_profile.py` to get your profile path
2. Close all Chrome windows
3. Try a test run with `--profile` flag
4. Consider creating a dedicated agent profile for safety
