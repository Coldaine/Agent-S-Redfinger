# Detailed Validation & Testing Plan for Agent-S-Redfinger
**Version**: 1.0
**Date**: October 29, 2025
**Purpose**: Step-by-step guide for validating the Docker-based Agent S3 Redfinger implementation
**Time Required**: 2-4 hours
**Skill Level**: Basic command-line knowledge

---

## Current validation status (auto-generated)
See: [VALIDATION_STATUS.md](./VALIDATION_STATUS.md)

## Mapping: validation steps -> scripts and code

### Generate results / run experiments

- S2 orchestration: [osworld_setup/s2/run.py](../osworld_setup/s2/run.py)
- S2.5 local runs: [osworld_setup/s2_5/run_local.py](../osworld_setup/s2_5/run_local.py)
- S3 local runs: [osworld_setup/s3/run_local.py](../osworld_setup/s3/run_local.py)

### Fact captions / judge (Behavior Best-of-N)

- Generate facts: [osworld_setup/s3/bbon/generate_facts.py](../osworld_setup/s3/bbon/generate_facts.py)
- Comparative judge: [osworld_setup/s3/bbon/run_judge.py](../osworld_setup/s3/bbon/run_judge.py)

### Behavior narrator / post-processing

- [gui_agents/s3/bbon/behavior_narrator.py](../gui_agents/s3/bbon/behavior_narrator.py)

### Redfinger runner (manual/integration)

- [redfinger/run_redfinger.py](../redfinger/run_redfinger.py)

To regenerate the status file:

```powershell
python scripts/generate_validation_report.py
```

## Important Resources

📚 **BEFORE STARTING**: Familiarize yourself with these documents:
- **Troubleshooting Guide**: `docs/TROUBLESHOOTING_GUIDE.md` - Comprehensive diagnostic procedures with deep-think markers
- **Project Context**: `.claude/CLAUDE.md` - Architecture, known issues, common misconceptions
- **Handoff Document**: `docs/handoffs/11AM.md` - Current implementation status

🧠 **WHEN YOU HIT AN ISSUE**: Look for "🧠 DEEP THINK" markers in this guide. These indicate complex problems requiring careful analysis before proceeding.

---

## Pre-Flight Checklist

### STOP! Check These First:

1. **Docker Desktop Status**
   ```powershell
   # Run this EXACT command:
   docker --version
   ```
   **Expected Output**: `Docker version XX.X.X, build XXXXX`
   **If Error**: Install Docker Desktop from https://www.docker.com/products/docker-desktop/

2. **Navigate to Project Directory**
   ```powershell
   # Run this EXACT command:
   cd C:\Agent-S-Redfinger
   pwd
   ```
   **Expected Output**: `C:\Agent-S-Redfinger`
   **If Error**: Directory doesn't exist, check location

3. **Verify Critical Files Exist**
   ```powershell
   # Run these commands one by one:
   Test-Path ".env"
   Test-Path "docker\Dockerfile.redfinger"
   Test-Path "docker\entrypoint-redfinger.sh"
   Test-Path "redfinger\run_redfinger.py"
   Test-Path "docker-compose.yml"
   ```
   **Expected**: All return `True`
   **If Any False**: Missing critical file, check handoff document

---

## Phase 1: Docker Image Build (30 minutes)

### Step 1.1: Build the Docker Image

**What This Does**: Creates the Ubuntu container with all dependencies

```bash
# Run this EXACT command:
docker-compose build --no-cache
```

**What You'll See**:
- Multiple "Step X/Y" messages
- Package downloads (this takes 5-10 minutes)
- "Successfully built" message at the end

**Success Criteria**:
- ✅ See "Successfully tagged agent-s3-redfinger"
- ✅ No red error messages

**If Build Fails**:
- Check Docker Desktop is running (green icon in system tray)
- Check internet connection
- Try: `docker system prune -a` then rebuild

### Step 1.2: Verify Image Created

```bash
# Run this command:
docker images | findstr redfinger
```

**Expected Output**: Shows image with name containing "redfinger"

---

## Phase 2: Container Validation Tests (45 minutes)

### Test 2.1: Basic Container Launch

**Purpose**: Verify container starts with display system

```bash
# Run this EXACT command (copy-paste it):
docker-compose run --rm agent-redfinger bash -c "echo 'Container started successfully'"
```

**What You'll See**:
```
[1/4] Starting virtual display (1920x1080)...
[2/4] Starting window manager...
[3/4] Starting VNC server on :5900...
[4/4] Verifying display...
✅ Container ready!
Container started successfully
```

**Success Criteria**:
- ✅ See all 4 startup steps
- ✅ See "Container ready!"
- ✅ See "Container started successfully"

**If Fails**:
- Check Docker is running
- Run `docker-compose down` then retry

### Test 2.2: Virtual Display Check

**Purpose**: Verify Xvfb display is working at correct resolution

```bash
# Run this command:
docker-compose run --rm agent-redfinger bash -c "xdpyinfo -display :99 | grep dimensions"
```

**Expected Output**:
```
  dimensions:    1920x1080 pixels
```

**Success Criteria**:
- ✅ Shows 1920x1080 resolution
- ✅ No error messages

### Test 2.3: PyAutoGUI Screen Size

**Purpose**: Verify Python can see correct screen dimensions

```bash
# Run this command:
docker-compose run --rm agent-redfinger python3 -c "import pyautogui; s = pyautogui.size(); print(f'Screen width: {s.width}, height: {s.height}'); assert s == (1920, 1080), 'Wrong size!'"
```

**Expected Output**:
```
Screen width: 1920, height: 1080
```

**Success Criteria**:
- ✅ Shows 1920 x 1080
- ✅ No assertion error

### Test 2.4: Agent S3 Import Test

**Purpose**: Verify Agent S3 library loads correctly

```bash
# Run this command:
docker-compose run --rm agent-redfinger python3 -c "from gui_agents.s3.agents.agent_s import AgentS3; from gui_agents.s3.agents.grounding import OSWorldACI; print('SUCCESS: All Agent S3 modules imported')"
```

**Expected Output**:
```
SUCCESS: All Agent S3 modules imported
```

**Success Criteria**:
- ✅ See "SUCCESS" message
- ✅ No import errors

### Test 2.5: Browser Launch Test

**Purpose**: Verify Chromium browser can launch

```bash
# Run this command:
docker-compose run --rm agent-redfinger bash -c "chromium-browser --version"
```

**Expected Output**:
```
Chromium XX.X.XXXX.XX Built on Ubuntu
```

**Success Criteria**:
- ✅ Shows Chromium version
- ✅ No error messages

---

## Phase 3: API Key Validation (15 minutes)

🧠 **DEEP THINK CHECKPOINT**: You are entering the API validation phase. This is one of the most common failure points. If tests fail here:
1. Read the error message CAREFULLY - note the exact status code
2. Verify which provider is configured (ZAI vs OpenAI)
3. Check model names are EXACT (case-sensitive, include 'v' for vision models)
4. Refer to `docs/TROUBLESHOOTING_GUIDE.md` section "API Authentication Fails" for detailed diagnostics
5. Do NOT guess - systematically verify each configuration point

### Step 3.1: Check Current Configuration

```powershell
# In PowerShell, run:
Get-Content .env | Select-String "PROVIDER|MODEL|API_KEY" | Select-String -NotMatch "^#"
```

**Current Default Settings**:
- REASONER_PROVIDER=zai
- REASONER_MODEL=glm-4.5v
- VISION_PROVIDER=zai
- VISION_MODEL=glm-4.5v

### Step 3.2: Test API Connection (ZAI)

```bash
# Test ZAI API key:
docker-compose run --rm agent-redfinger python3 -c "
import os
import requests
api_key = os.getenv('ZAI_API_KEY')
base_url = os.getenv('ZAI_BASE_URL', 'https://api.z.ai/api/coding/paas/v4')
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
test_payload = {'model': 'glm-4.5v', 'messages': [{'role': 'user', 'content': 'Hi'}], 'max_tokens': 10}
response = requests.post(f'{base_url}/chat/completions', json=test_payload, headers=headers)
print(f'ZAI API Status: {response.status_code}')
if response.status_code == 200:
    print('✅ ZAI API key is valid')
else:
    print('❌ ZAI API key failed:', response.text[:200])
"
```

**Success Criteria**:
- ✅ Status code 200
- ✅ "ZAI API key is valid"

### Step 3.3: Test API Connection (OpenAI - Optional Fallback)

```bash
# Test OpenAI API key if ZAI fails:
docker-compose run --rm agent-redfinger python3 -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
try:
    response = client.models.list()
    print('✅ OpenAI API key is valid')
    print(f'Available models: {len(list(response))} found')
except Exception as e:
    print(f'❌ OpenAI API key failed: {e}')
"
```

**If BOTH APIs Fail**:
1. Check `.env` file has valid keys
2. Check internet connection
3. Keys may be expired - need new ones

🧠 **DEEP THINK REQUIRED**: If BOTH API providers fail, this is NOT a configuration issue. Stop and analyze:
- Is Docker able to reach external networks? Test with `curl google.com`
- Are API keys actually loaded? Check environment variables inside container
- Are keys in correct format? ZAI should start with hex chars, OpenAI should start with "sk-"
- See `docs/TROUBLESHOOTING_GUIDE.md` section "API Authentication Fails" → "DEEP THINK: Both APIs fail?"

---

## Phase 4: Simple Functionality Test (30 minutes)

### Test 4.1: Screenshot Capability

**Purpose**: Verify agent can capture screenshots

```bash
# Run this command:
docker-compose run --rm agent-redfinger python3 -c "
import pyautogui
import os
screenshot = pyautogui.screenshot()
screenshot.save('/workspace/test_screenshot.png')
if os.path.exists('/workspace/test_screenshot.png'):
    size = os.path.getsize('/workspace/test_screenshot.png')
    print(f'✅ Screenshot saved: {size} bytes')
else:
    print('❌ Screenshot failed')
"
```

**Success Criteria**:
- ✅ "Screenshot saved" message
- ✅ File size > 0 bytes

### Test 4.2: Browser Navigation Test

**Purpose**: Test browser can open and navigate

```bash
# Run this command:
docker-compose run --rm agent-redfinger python3 -c "
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, args=['--start-maximized'])
    page = browser.new_page(viewport={'width': 1920, 'height': 1080})
    page.goto('https://www.google.com')
    time.sleep(2)
    title = page.title()
    browser.close()
    print(f'✅ Browser test successful. Page title: {title}')
"
```

**Success Criteria**:
- ✅ "Browser test successful"
- ✅ Shows "Google" in page title

---

## Phase 5: Full Integration Test (45 minutes)

🧠 **DEEP THINK CHECKPOINT**: You are entering full integration testing. This is where multiple systems interact and issues can be complex. Before proceeding:
1. Ensure all Phase 2 tests passed (especially display resolution)
2. Ensure Phase 3 API validation passed
3. If this test fails, systematically check EACH layer:
   - Docker/Display → Phase 2 tests
   - API → Phase 3 tests
   - Agent code → Check logs for Python errors
   - Coordinates → See `docs/TROUBLESHOOTING_GUIDE.md` section "Clicks Miss Targets"

### Test 5.1: Run Simple Google Search Task (Recommended: Harness)

**Purpose**: Test complete agent pipeline with simple task

Option A — Preferred (Harness with timeouts, logs, and result files):

```powershell
# Preflight
python scripts/run_phase5_harness.py --dry-run

# GPT‑5 with temperature 1.0
python scripts/run_phase5_harness.py `
   --provider openai `
   --model gpt-5-2025-08-07 `
   --model-temperature 1.0 `
   --url "https://www.google.com" `
   --task "Click on the search box and type weather" `
   --max-steps 5 `
   --overall-timeout 900 `
   --stall-timeout 120

# ZAI GLM‑4.5V with temperature 1.0
python scripts/run_phase5_harness.py `
   --provider zai `
   --model glm-4.5v `
   --model-temperature 1.0 `
   --url "https://www.google.com" `
   --task "Click on the search box and type weather" `
   --max-steps 5 `
   --overall-timeout 900 `
   --stall-timeout 120
```

Artifacts: `logs/phase5/<timestamp>/stdout.log`, `stderr.log`, `meta.json`, `result.json` (and the status page updates automatically).

Option B — Direct docker-compose (legacy; less robust):

```powershell
docker-compose run --rm agent-redfinger python3 /workspace/redfinger/run_redfinger.py --url "https://www.google.com" --task "Click on the search box and type weather" --max-steps 5
```

**What You'll See**:
```
Opening browser: https://www.google.com
Initializing Agent S3...
Starting task: Click on the search box and type weather

--- Step 1/5 ---
[Agent output with actions]
```

**Success Criteria**:
- ✅ Browser opens
- ✅ Agent initializes
- ✅ Takes at least one action (or prints `HARNESS:STATUS=passed`)
- ✅ No Python errors

**Common Issues**:
- "Model not found" → Check model name in .env
- "API key invalid" → Verify keys in .env
- "Import error" → Requirements not installed properly

🧠 **DEEP THINK: Agent runs but clicks miss targets?**
This is a coordinate alignment issue. Systematically verify:
1. Display resolution: `xdpyinfo -display :99 | grep dimensions` → Must be 1920x1080
2. PyAutoGUI sees same: `python3 -c "import pyautogui; print(pyautogui.size())"` → Must be (1920, 1080)
3. Browser is full-screen: Check run_redfinger.py has '--start-fullscreen' argument
4. All three MUST match. If any differ, coordinate math will be wrong.
5. See `docs/TROUBLESHOOTING_GUIDE.md` section "Clicks Miss Targets" for comprehensive diagnosis

### Test 5.2: VNC Connection Test (Optional)

**Purpose**: Watch agent work in real-time

1. **Download VNC Viewer**: https://www.realvnc.com/en/connect/download/viewer/

2. **Start container with VNC**:
```bash
# Make sure ENABLE_VNC=true in .env, then:
docker-compose up -d agent-redfinger
```

3. **Connect VNC Viewer**:
- Server: `localhost:5900`
- Password: (leave empty, press Enter)

4. **What You'll See**:
- Ubuntu desktop in viewer
- Browser window when agent runs
- Mouse movements as agent works

---

## Phase 6: Redfinger-Specific Testing (30 minutes)

🧠 **DEEP THINK CHECKPOINT**: You are now testing the actual Redfinger automation. This adds a 4th layer of complexity (Android in cloud). If tests fail:
1. First verify Phase 5 (simple Google test) worked → If not, fix that first
2. Redfinger issues are SEPARATE from Agent S3 issues → Don't confuse them
3. Canvas detection may fail if Redfinger changed their web structure → Use VNC to inspect
4. Login may fail due to CAPTCHA or session requirements
5. See `docs/TROUBLESHOOTING_GUIDE.md` section "Redfinger-Specific Issues" and "Canvas Not Found"

### Test 6.1: Verify Redfinger Credentials

```powershell
# Check credentials are set:
Get-Content .env | Select-String "REDFINGER"
```

**Should Show**:
- REDFINGER_URL=https://www.cloudemulator.net/app/phone?channelCode=web
- REDFINGER_EMAIL=pmaclyman@gmail.com
- REDFINGER_PASSWORD=Rockstar01!

### Test 6.2: Test Redfinger Page Load

```bash
# Test if Redfinger URL is accessible:
docker-compose run --rm agent-redfinger python3 -c "
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://www.cloudemulator.net/app/phone?channelCode=web')
    time.sleep(5)

    # Check for login form
    email_input = page.query_selector('input[type=\"email\"], input[type=\"text\"]')
    if email_input:
        print('✅ Redfinger login page loaded')
    else:
        print('⚠️ Login form not found - page may have changed')

    browser.close()
"
```

### Test 6.3: Full Redfinger Task (Final Test)

**Purpose**: Run the actual Redfinger automation task

```bash
# Run the configured task from .env:
docker-compose up agent-redfinger
```

**What Should Happen**:
1. Container starts (4 startup messages)
2. Browser opens to Redfinger URL
3. Agent S3 initializes
4. Agent attempts to log in
5. Agent tries to open settings app

**Monitor Progress**:
```bash
# In another terminal:
docker-compose logs -f agent-redfinger
```

---

## Troubleshooting Guide

⚠️ **NOTE**: This section contains QUICK fixes only. For complex issues with multiple possible causes, see:
- **Full Troubleshooting Guide**: `docs/TROUBLESHOOTING_GUIDE.md` (comprehensive diagnostics with deep-think markers)
- **Project Context**: `.claude/CLAUDE.md` (architecture details, common misconceptions)

### Problem: "Docker daemon not running"
**Solution**:
1. Start Docker Desktop
2. Wait for green icon in system tray
3. Retry command

### Problem: "Container exits immediately"
**Check Logs**:
```bash
docker-compose logs agent-redfinger
```
**Common Fixes**:
- Missing display: Rebuild with `docker-compose build --no-cache`
- Python error: Check .env configuration

### Problem: "API authentication failed"
**Solutions**:
1. Verify API keys in .env
2. Try switching providers:
   ```
   # Edit .env and uncomment OpenAI section:
   REASONER_PROVIDER=openai
   REASONER_MODEL=gpt-5-2025-08-07
   VISION_PROVIDER=openai
   VISION_MODEL=gpt-5-2025-08-07
   ```

### Problem: "Import error: No module named..."
**Solution**:
```bash
# Rebuild with fresh dependencies:
docker-compose build --no-cache
```

### Problem: "Coordinate error" or "Click missed target"
**Checks**:
1. Verify display is 1920x1080: Test 2.2
2. Verify PyAutoGUI sees correct size: Test 2.3
3. Ensure browser is full-screen

### Problem: "Model not found" error
**Info**: Model must be vision-capable!
- ✅ Good: glm-4.5v, gpt-5-2025-08-07, gpt-5-mini-2025-08-07
- ❌ Bad: glm-4.6 (text-only), gpt-4-turbo (text-only)

---

## Success Metrics

### Minimum Success (Required)
- [ ] Docker image builds
- [ ] Container starts with display
- [ ] PyAutoGUI reports 1920x1080
- [ ] Agent S3 imports work
- [ ] At least one API key works

### Good Success (Expected)
- [ ] Browser launches in container
- [ ] Agent can take screenshot
- [ ] Simple Google task works
- [ ] Agent executes at least 3 actions

### Full Success (Ideal)
- [ ] VNC connection works
- [ ] Redfinger page loads
- [ ] Agent attempts login
- [ ] Full task runs to completion
- [ ] Logs show reasonable behavior

---

## Quick Reference Card

### Essential Commands
```bash
# Navigate to project
cd C:\Agent-S-Redfinger

# Build Docker image
docker-compose build

# Run any test
docker-compose run --rm agent-redfinger [command]

# Start with VNC
docker-compose up agent-redfinger

# View logs
docker-compose logs -f agent-redfinger

# Stop everything
docker-compose down

# Clean up Docker
docker system prune -a
```

### File Locations
- Configuration: `C:\Agent-S-Redfinger\.env`
- Main script: `C:\Agent-S-Redfinger\redfinger\run_redfinger.py`
- Docker setup: `C:\Agent-S-Redfinger\docker\`
- Logs: `C:\Agent-S-Redfinger\logs\`

### VNC Access
- Server: `localhost:5900`
- Password: (none, just press Enter)
- Resolution: 1920x1080

---

## Final Checklist

Before declaring complete:

1. **Container Tests** (Phase 2)
   - [ ] Container starts: Test 2.1
   - [ ] Display verified: Test 2.2
   - [ ] PyAutoGUI works: Test 2.3
   - [ ] Agent imports: Test 2.4
   - [ ] Browser exists: Test 2.5

2. **API Tests** (Phase 3)
   - [ ] ZAI or OpenAI key validated
   - [ ] Model is vision-capable

3. **Integration Tests** (Phase 5)
   - [ ] Simple task attempted
   - [ ] Agent takes actions
   - [ ] No critical errors

4. **Documentation**
   - [ ] This plan followed step-by-step
   - [ ] Results documented
   - [ ] Issues noted for next person

---

## Time Estimates

- **Phase 1**: Docker Build - 30 minutes
- **Phase 2**: Container Tests - 45 minutes
- **Phase 3**: API Validation - 15 minutes
- **Phase 4**: Functionality - 30 minutes
- **Phase 5**: Integration - 45 minutes
- **Phase 6**: Redfinger - 30 minutes

**Total**: 3-4 hours (including wait times)

---

## Next Steps After Validation

Once all tests pass:

1. **Document Results**: Create `VALIDATION_RESULTS.md` with:
   - Which tests passed/failed
   - Any error messages
   - Performance observations

2. **Production Readiness**:
   - Rotate API keys if needed
   - Set up proper logging
   - Create backup of working .env

3. **Advanced Testing**:
   - Try more complex tasks
   - Test error recovery
   - Benchmark performance

---

**Document Version**: 1.0
**Created**: October 29, 2025
**For**: Agent-S-Redfinger Validation Team
**Estimated Time**: 3-4 hours for complete validation