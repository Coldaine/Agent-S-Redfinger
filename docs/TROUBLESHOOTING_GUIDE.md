# Agent-S-Redfinger Troubleshooting Guide
**Version**: 1.0
**Date**: October 29, 2025
**Purpose**: Comprehensive diagnostic and resolution guide for common issues

---

## How to Use This Guide

1. **Find your symptom** in the table of contents
2. **Follow the diagnostic steps** exactly as written
3. **Watch for 🧠 DEEP THINK markers** - these indicate complex issues requiring careful analysis
4. **Document your findings** as you go
5. **Escalate** if you hit an "ESCALATION POINT"

---

## Table of Contents

**[Quick Diagnostics](#quick-diagnostics)** - Start here for fast checks

**Docker Issues**:
- [Docker Won't Start](#docker-wont-start)
- [Image Build Fails](#image-build-fails)
- [Container Exits Immediately](#container-exits-immediately)
- [Display Initialization Fails](#display-initialization-fails)

**API & Model Issues**:
- [API Authentication Fails](#api-authentication-fails) 🧠
- [Model Not Found Error](#model-not-found-error) 🧠
- [Vision Model Errors](#vision-model-errors) 🧠

**Agent Behavior Issues**:
- [Agent Does Nothing](#agent-does-nothing)
- [Agent Generates Invalid Actions](#agent-generates-invalid-actions)
- [Clicks Miss Targets](#clicks-miss-targets) 🧠
- [Agent Loops Without Progress](#agent-loops-without-progress)

**Redfinger-Specific Issues**:
- [Redfinger Page Won't Load](#redfinger-page-wont-load)
- [Login Fails](#login-fails)
- [Canvas Not Found](#canvas-not-found) 🧠

**Performance Issues**:
- [Slow Response Times](#slow-response-times)
- [High API Costs](#high-api-costs)

---

## Quick Diagnostics

### 5-Minute Health Check

Run these commands in order. Stop at first failure.

```bash
cd C:\Agent-S-Redfinger

# 1. Docker running?
docker --version

# 2. Image exists?
docker images | findstr redfinger

# 3. Container starts?
docker-compose run --rm agent-redfinger bash -c "echo OK"

# 4. Display works?
docker-compose run --rm agent-redfinger bash -c "xdpyinfo -display :99 | grep dimensions"

# 5. PyAutoGUI works?
docker-compose run --rm agent-redfinger python3 -c "import pyautogui; print(pyautogui.size())"

# 6. Agent imports?
docker-compose run --rm agent-redfinger python3 -c "from gui_agents.s3.agents.agent_s import AgentS3; print('OK')"
```

**All pass?** → System is healthy, issue is likely in configuration or task definition

**Any fail?** → Jump to specific section below

---

## Docker Issues

### Docker Won't Start

**Symptom**: `docker: command not found` or `error during connect`

**Diagnostic Steps**:

1. **Check Docker Desktop is installed**:
   ```powershell
   Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
   ```
   - If empty → Docker Desktop not running

2. **Check system tray**:
   - Look for Docker whale icon
   - Should be green/white (not red)

3. **Start Docker Desktop**:
   - Windows: Start menu → Docker Desktop
   - Wait 30-60 seconds for full startup

4. **Verify**:
   ```bash
   docker ps
   ```
   - Should show table (even if empty)

**If Still Fails**:
- Restart Docker Desktop
- Restart Windows
- Reinstall Docker Desktop from https://www.docker.com/products/docker-desktop/

---

### Image Build Fails

**Symptom**: `docker-compose build` fails with error

**Diagnostic Steps**:

1. **Capture the exact error**:
   ```bash
   docker-compose build --no-cache 2>&1 | tee build_log.txt
   ```

2. **Common Error: "failed to fetch metadata"**:
   - **Cause**: Internet connection or Docker Hub issue
   - **Solution**:
     ```bash
     # Check internet
     ping 8.8.8.8

     # Retry build
     docker-compose build --no-cache
     ```

3. **Common Error: "COPY failed"**:
   - **Cause**: Missing file in build context
   - **Check**:
     ```bash
     Test-Path docker\Dockerfile.redfinger
     Test-Path docker\entrypoint-redfinger.sh
     Test-Path requirements.txt
     ```
   - **Solution**: Verify all files exist, check paths in Dockerfile

4. **Common Error: "pip install failed"**:
   - **Cause**: Package dependency conflict
   - **Solution**:
     ```bash
     # Check requirements.txt for obvious errors
     Get-Content requirements.txt

     # Try building with verbose output
     docker-compose build --no-cache --progress=plain
     ```

5. **Common Error: "insufficient space"**:
   - **Cause**: Docker running out of disk space
   - **Solution**:
     ```bash
     # Clean up Docker
     docker system prune -a --volumes

     # Check available space
     docker system df
     ```

**If Still Fails**:
- Post error to GitHub Issues with full build log
- Try building on different network
- Check Docker Desktop settings (RAM, disk allocation)

---

### Container Exits Immediately

**Symptom**: `docker-compose up` exits within seconds, no output

**Diagnostic Steps**:

1. **Check logs**:
   ```bash
   docker-compose logs agent-redfinger
   ```

2. **Common Error: "Display :99 not available"**:
   - **Cause**: Xvfb failed to start
   - **Solution**:
     ```bash
     # Test entrypoint manually
     docker-compose run --rm agent-redfinger bash -c "Xvfb :99 -screen 0 1920x1080x24 &; sleep 3; xdpyinfo -display :99"
     ```
   - If fails → Rebuild image

3. **Common Error: "python3: command not found"**:
   - **Cause**: Build didn't complete properly
   - **Solution**: Rebuild with --no-cache

4. **Common Error: "No such file: run_redfinger.py"**:
   - **Cause**: Volume mount issue or file missing
   - **Check**:
     ```bash
     Test-Path redfinger\run_redfinger.py
     ```
   - **Solution**: Verify file exists, check docker-compose.yml mounts

**If Still Fails**:
- Run interactively: `docker-compose run --rm agent-redfinger bash`
- Manually test each step from entrypoint script

---

### Display Initialization Fails

**Symptom**: "Display :99 not available" or "xdpyinfo: unable to open display"

**Diagnostic Steps**:

1. **Check Xvfb is running**:
   ```bash
   docker-compose run --rm agent-redfinger bash -c "ps aux | grep Xvfb"
   ```

2. **Check DISPLAY variable**:
   ```bash
   docker-compose run --rm agent-redfinger bash -c "echo \$DISPLAY"
   ```
   - Should show `:99`

3. **Check resolution**:
   ```bash
   docker-compose run --rm agent-redfinger bash -c "xdpyinfo -display :99 | grep dimensions"
   ```
   - Should show `1920x1080 pixels`

4. **Manual Xvfb start**:
   ```bash
   docker-compose run --rm agent-redfinger bash
   # Inside container:
   Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
   sleep 3
   export DISPLAY=:99
   xdpyinfo -display :99
   ```

**If Fails**:
- Check entrypoint-redfinger.sh has correct Xvfb command
- Verify X11 libraries installed in Dockerfile
- Rebuild with `--no-cache`

---

## API & Model Issues

### API Authentication Fails

**Symptom**: 401 Unauthorized, "Invalid API key", or authentication errors

🧠 **DEEP THINK REQUIRED**: API authentication involves multiple configuration points. Slow down and methodically check each one.

**Diagnostic Steps**:

1. **Identify which provider is failing**:
   ```bash
   # Check current config
   Get-Content .env | Select-String "PROVIDER|MODEL" | Select-String -NotMatch "^#"
   ```

2. **If using ZAI**:

   **Step 2a: Verify API key format**:
   ```bash
   Get-Content .env | Select-String "ZAI_API_KEY"
   ```
   - Should be: `2c21c2eed1fa44e7834a6113aeb832a5.XXXXXXXXXXXX`
   - Format: `<32-char-hex>.<alphanumeric>`

   **Step 2b: Test ZAI API directly**:
   ```bash
   docker-compose run --rm agent-redfinger python3 -c "
   import os
   import requests

   api_key = os.getenv('ZAI_API_KEY')
   base_url = os.getenv('ZAI_BASE_URL', 'https://api.z.ai/api/coding/paas/v4')

   print(f'Testing ZAI API...')
   print(f'Base URL: {base_url}')
   print(f'API Key: {api_key[:20]}...')

   headers = {
       'Authorization': f'Bearer {api_key}',
       'Content-Type': 'application/json'
   }

   payload = {
       'model': 'glm-4.5v',
       'messages': [{'role': 'user', 'content': 'Say hello'}],
       'max_tokens': 10
   }

   response = requests.post(
       f'{base_url}/chat/completions',
       json=payload,
       headers=headers,
       timeout=30
   )

   print(f'Status: {response.status_code}')
   print(f'Response: {response.text[:500]}')
   "
   ```

   **Expected**: Status 200, response with content

   **If 401**:
   - API key is invalid or expired
   - Need to obtain new key from z.ai
   - Check for typos in .env

   **If 404**:
   - Base URL is wrong
   - Verify: `ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4`

3. **If using OpenAI**:

   **Step 3a: Test OpenAI API**:
   ```bash
   docker-compose run --rm agent-redfinger python3 -c "
   import os
   from openai import OpenAI

   api_key = os.getenv('OPENAI_API_KEY')
   print(f'Testing OpenAI API...')
   print(f'API Key: {api_key[:20]}...')

   client = OpenAI(api_key=api_key)

   try:
       # Test with models list
       models = client.models.list()
       print(f'✅ API Key Valid')
       print(f'Available models: {len(list(models))}')

       # Test actual call
       response = client.chat.completions.create(
           model='gpt-5-mini-2025-08-07',
           messages=[{'role': 'user', 'content': 'Hi'}],
           max_tokens=10
       )
       print(f'✅ Chat completion works')

   except Exception as e:
       print(f'❌ Error: {e}')
   "
   ```

   **If fails**:
   - Check API key format: `sk-proj-XXXX...`
   - Verify key hasn't expired
   - Check OpenAI account has credits

4. **🧠 DEEP THINK: Both APIs fail?**

   **Possible causes**:
   - Network issue (firewall, proxy)
   - Both keys expired (unlikely)
   - .env not being loaded properly

   **Test .env loading**:
   ```bash
   docker-compose run --rm agent-redfinger bash -c "echo ZAI_API_KEY=\$ZAI_API_KEY | head -c 50"
   ```
   - Should show key starting with `2c21c2e...`
   - If empty → .env not mounted or not loaded

   **Check docker-compose.yml**:
   ```yaml
   volumes:
     - ./.env:/workspace/.env
   ```

   **Test network**:
   ```bash
   docker-compose run --rm agent-redfinger bash -c "curl -I https://api.openai.com"
   ```
   - Should return 200-level response

**Solution Paths**:

- **Path A: Switch providers**
  ```bash
  # Edit .env, comment out ZAI, uncomment OpenAI
  # Or vice versa
  notepad .env
  ```

- **Path B: Get new API keys**
  - ZAI: Contact z.ai support
  - OpenAI: https://platform.openai.com/api-keys

- **Path C: Use different model**
  ```env
  # Try older proven models
  REASONER_MODEL=gpt-4-vision-preview
  VISION_MODEL=gpt-4-vision-preview
  ```

**ESCALATION POINT**: If both providers fail with valid keys and network is working, escalate to senior engineer.

---

### Model Not Found Error

**Symptom**: "Model not found", "model does not exist", or 404 errors

🧠 **DEEP THINK REQUIRED**: Model names are provider-specific and case-sensitive. Requires careful verification.

**Diagnostic Steps**:

1. **Capture exact error message**:
   ```bash
   docker-compose up agent-redfinger 2>&1 | tee model_error.log
   ```

2. **Check current model configuration**:
   ```bash
   Get-Content .env | Select-String "MODEL"
   ```

3. **🧠 DEEP THINK: Verify model name is correct**

   **For ZAI**:
   - Valid: `glm-4.5v` (with 'v' for vision)
   - Invalid: `glm-4.6` (text-only, no vision)
   - Invalid: `glm-4-5v` (wrong format)

   **For OpenAI**:
   - Valid: `gpt-5-2025-08-07` (exact date format)
   - Valid: `gpt-5-mini-2025-08-07`
   - Invalid: `gpt-5` (needs date)
   - Invalid: `gpt-5-latest` (not a valid name)

4. **List available models**:

   **For ZAI**:
   ```bash
   docker-compose run --rm agent-redfinger python3 -c "
   import os
   import requests

   api_key = os.getenv('ZAI_API_KEY')
   base_url = os.getenv('ZAI_BASE_URL')

   headers = {'Authorization': f'Bearer {api_key}'}

   # Try to get models list
   response = requests.get(f'{base_url}/models', headers=headers)
   print(response.text)
   "
   ```

   **For OpenAI**:
   ```bash
   docker-compose run --rm agent-redfinger python3 -c "
   import os
   from openai import OpenAI

   client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
   models = client.models.list()

   vision_models = [m.id for m in models if 'vision' in m.id or 'gpt-5' in m.id or 'gpt-4' in m.id]

   print('Vision-capable models:')
   for model in sorted(vision_models):
       print(f'  - {model}')
   "
   ```

5. **Check model availability**:

   Some models may require:
   - Specific API tier (e.g., GPT-5 may need Pro tier)
   - Waitlist approval
   - Regional availability

**Solutions**:

- **Solution A: Fix model name**
  ```env
  # Change from this:
  REASONER_MODEL=glm-4.6

  # To this:
  REASONER_MODEL=glm-4.5v
  ```

- **Solution B: Use proven fallback**
  ```env
  # OpenAI fallback:
  REASONER_PROVIDER=openai
  REASONER_MODEL=gpt-4-vision-preview
  VISION_PROVIDER=openai
  VISION_MODEL=gpt-4-vision-preview
  ```

**CRITICAL**: Verify BOTH reasoner and vision models exist!

---

### Vision Model Errors

**Symptom**: "model does not support images", error 1210, or "invalid request"

🧠 **DEEP THINK REQUIRED**: This is the most common configuration error. Vision capability is REQUIRED for both models.

**Understanding the Problem**:

```
Agent S3 Architecture:
┌─────────────────────────────────────┐
│ Screenshot (PNG image)              │
└────────────┬────────────────────────┘
             │
             ├──→ Reasoner Model (NEEDS VISION)
             │    Input: Raw screenshot
             │    Output: Strategic plan
             │
             ├──→ Grounding Model (NEEDS VISION)
             │    Input: Screenshot + plan
             │    Output: Pixel coordinates
             │
             └──→ PyAutoGUI
                  Executes clicks
```

**Diagnostic Steps**:

1. **Verify BOTH models are vision-capable**:

   ```bash
   Get-Content .env | Select-String "MODEL"
   ```

   **Vision-Capable Models**:
   - ✅ `glm-4.5v` (note the 'v')
   - ✅ `gpt-5-2025-08-07`
   - ✅ `gpt-5-mini-2025-08-07`
   - ✅ `gpt-4-vision-preview`
   - ✅ `gpt-4-turbo-2024-04-09` (if vision-enabled)

   **Text-Only Models (WILL FAIL)**:
   - ❌ `glm-4.6` (no 'v')
   - ❌ `gpt-4-turbo` (without date)
   - ❌ `gpt-4` (base model)
   - ❌ Any model without "vision" or 'v' indicator

2. **🧠 DEEP THINK: Check error message carefully**

   **Error 1210 (ZAI)**:
   - Definitive: Model doesn't support vision
   - Solution: Change to glm-4.5v

   **"invalid request" with image**:
   - Model exists but doesn't accept images
   - Solution: Switch to vision-capable variant

3. **Test vision capability**:

   ```bash
   docker-compose run --rm agent-redfinger python3 -c "
   import os
   import base64
   import requests
   from PIL import Image
   import io

   # Create test image
   img = Image.new('RGB', (100, 100), color='red')
   buf = io.BytesIO()
   img.save(buf, format='PNG')
   img_b64 = base64.b64encode(buf.getvalue()).decode()

   # Test with current config
   provider = os.getenv('REASONER_PROVIDER')
   model = os.getenv('REASONER_MODEL')

   print(f'Testing vision capability: {provider}/{model}')

   if provider == 'zai':
       api_key = os.getenv('ZAI_API_KEY')
       base_url = os.getenv('ZAI_BASE_URL')

       payload = {
           'model': model,
           'messages': [{
               'role': 'user',
               'content': [
                   {'type': 'text', 'text': 'What color is this image?'},
                   {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
               ]
           }],
           'max_tokens': 50
       }

       response = requests.post(
           f'{base_url}/chat/completions',
           json=payload,
           headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
       )

       print(f'Status: {response.status_code}')
       print(f'Response: {response.text[:500]}')

       if response.status_code == 200:
           print('✅ Model supports vision')
       else:
           print('❌ Model does NOT support vision')

   elif provider == 'openai':
       from openai import OpenAI
       client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

       try:
           response = client.chat.completions.create(
               model=model,
               messages=[{
                   'role': 'user',
                   'content': [
                       {'type': 'text', 'text': 'What color?'},
                       {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
                   ]
               }],
               max_tokens=50
           )
           print('✅ Model supports vision')
           print(f'Response: {response.choices[0].message.content}')
       except Exception as e:
           print(f'❌ Model does NOT support vision: {e}')
   "
   ```

4. **Fix configuration**:

   ```env
   # CORRECT: Both are vision-capable
   REASONER_PROVIDER=zai
   REASONER_MODEL=glm-4.5v          # ← Note the 'v'
   VISION_PROVIDER=zai
   VISION_MODEL=glm-4.5v            # ← Same vision model

   # WRONG: Text-only model
   REASONER_PROVIDER=zai
   REASONER_MODEL=glm-4.6           # ← No 'v', text-only!
   VISION_PROVIDER=zai
   VISION_MODEL=glm-4.5v
   ```

**CRITICAL RULE**: `REASONER_MODEL` and `VISION_MODEL` MUST BOTH be vision-capable!

**ESCALATION POINT**: If using correct vision models and still getting vision errors, escalate with full error logs.

---

## Agent Behavior Issues

### Agent Does Nothing

**Symptom**: Agent starts, takes screenshot, but doesn't generate any actions

**Diagnostic Steps**:

1. **Check logs for model output**:
   ```bash
   docker-compose logs agent-redfinger | findstr "action"
   ```

2. **Verify task description**:
   ```bash
   Get-Content .env | Select-String "TASK"
   ```

   **Good task descriptions**:
   - "Click on the Google search box"
   - "Type 'weather' in the search field"
   - "Open the settings app"

   **Bad task descriptions**:
   - "Do stuff" (too vague)
   - "Make it work" (no specific action)
   - "" (empty)

3. **Test with simple task**:
   ```bash
   docker-compose run --rm agent-redfinger python3 /workspace/redfinger/run_redfinger.py --url "https://www.google.com" --task "Move the mouse" --max-steps 3
   ```

4. **Check model is generating output**:
   - Look for "Executing:" in logs
   - If present → Model working, actions may be invalid
   - If absent → Model not responding

**Solutions**:

- **Solution A: Simplify task**
  - Use very specific, simple instruction
  - One action at a time

- **Solution B: Check model parameters**
  - May need higher `max_tokens`
  - May need different temperature

- **Solution C: Try different model**
  - GPT-5 Mini may need more reasoning budget
  - Switch to GPT-5 full model

---

### Agent Generates Invalid Actions

**Symptom**: Actions generated but cause errors when executed

**Diagnostic Steps**:

1. **Capture error**:
   ```bash
   docker-compose logs agent-redfinger | findstr "Error\|Traceback" -A 5
   ```

2. **Check action format**:
   - Agent should generate Python code
   - Code should use `pyautogui` functions

3. **Common invalid actions**:
   - Syntax errors in generated Python
   - Undefined variables
   - Invalid pyautogui calls

**Solutions**:

- Review generated code in logs
- May need different model or prompt tuning
- Check Agent S3 configuration

---

### Clicks Miss Targets

**Symptom**: Agent clicks but at wrong coordinates

🧠 **DEEP THINK REQUIRED**: Coordinate issues involve the entire stack. Requires systematic verification.

**Understanding the Coordinate System**:

```
Container Display: 1920x1080 at :99
    ↓
Browser: Full-screen starting at (0,0)
    ↓
PyAutoGUI: Screen-absolute coordinates
    ↓
Redfinger Canvas: At some position (x, y) in browser
    ↓
Android Screen: At canvas position + offset
```

**Diagnostic Steps**:

1. **🧠 DEEP THINK: Verify display resolution**

   ```bash
   # Step 1: Check virtual display
   docker-compose run --rm agent-redfinger bash -c "xdpyinfo -display :99 | grep dimensions"
   ```
   **Must show**: `1920x1080 pixels`

   ```bash
   # Step 2: Check PyAutoGUI sees same resolution
   docker-compose run --rm agent-redfinger python3 -c "import pyautogui; s = pyautogui.size(); print(f'{s.width}x{s.height}'); assert s == (1920, 1080)"
   ```
   **Must show**: `1920x1080`

   ```bash
   # Step 3: Check browser viewport
   docker-compose run --rm agent-redfinger python3 -c "
   from playwright.sync_api import sync_playwright
   with sync_playwright() as p:
       browser = p.chromium.launch(headless=False)
       page = browser.new_page(viewport={'width': 1920, 'height': 1080})
       print(f'Viewport: {page.viewport_size}')
       browser.close()
   "
   ```
   **Must show**: `{'width': 1920, 'height': 1080}`

2. **🧠 DEEP THINK: All three must match!**

   **If ANY don't match**:
   - Display and PyAutoGUI mismatch → Xvfb configuration issue
   - PyAutoGUI and browser mismatch → Browser not full-screen
   - Rebuild container with correct settings

3. **Verify browser is full-screen**:

   ```bash
   # Check browser launch arguments
   Get-Content redfinger\run_redfinger.py | Select-String "chromium.launch"
   ```

   **Must include**: `'--start-fullscreen'` or `'--start-maximized'`

4. **Test coordinate accuracy with VNC**:

   - Enable VNC: `ENABLE_VNC=true` in .env
   - Connect: VNC Viewer → `localhost:5900`
   - Run task and WATCH where clicks happen
   - Compare to where they SHOULD happen

5. **🧠 DEEP THINK: Is it consistently off by same amount?**

   **If offset is consistent** (e.g., always +10px right):
   - Browser window may not be at (0,0)
   - Window decorations may be present
   - Check window manager (metacity) settings

   **If offset varies**:
   - Model grounding is inaccurate
   - May need better vision model
   - May need explicit coordinate calibration

**Solutions**:

- **Solution A: Rebuild with correct resolution**
  ```bash
  # Verify Dockerfile has:
  # Xvfb :99 -screen 0 1920x1080x24
  docker-compose build --no-cache
  ```

- **Solution B: Fix browser launch**
  ```python
  # In run_redfinger.py:
  browser = p.chromium.launch(
      headless=False,
      args=['--start-fullscreen', '--no-default-browser-check']
  )
  ```

- **Solution C: Use better vision model**
  ```env
  # GPT-5 has better spatial reasoning
  VISION_MODEL=gpt-5-2025-08-07
  ```

**ESCALATION POINT**: If all resolutions match and clicks still consistently miss by same offset, escalate with VNC recording.

---

### Agent Loops Without Progress

**Symptom**: Agent repeats same action over and over, doesn't make progress

**Diagnostic Steps**:

1. **Check logs for repeated actions**:
   ```bash
   docker-compose logs agent-redfinger | findstr "Step" | Select-Object -Last 20
   ```

2. **Identify loop pattern**:
   - Same action every step?
   - Alternating between two actions?
   - Gradually drifting?

3. **Common causes**:
   - Action not having desired effect (clicks miss)
   - Model not recognizing task completion
   - Task description too vague
   - No progress feedback to model

**Solutions**:

- Reduce MAX_STEPS to prevent waste
- Add explicit success criteria to task
- Check clicks are landing correctly (see above)
- Review model memory/context handling

---

## Redfinger-Specific Issues

### Redfinger Page Won't Load

**Symptom**: Browser opens but Redfinger page doesn't load or times out

**Diagnostic Steps**:

1. **Test URL directly**:
   ```bash
   curl -I "https://www.cloudemulator.net/app/phone?channelCode=web"
   ```

2. **Check if login required**:
   - Redfinger may require authentication
   - Session may have expired

3. **Test with Playwright**:
   ```bash
   docker-compose run --rm agent-redfinger python3 -c "
   from playwright.sync_api import sync_playwright
   import time

   with sync_playwright() as p:
       browser = p.chromium.launch(headless=False)
       page = browser.new_page()

       print('Navigating to Redfinger...')
       response = page.goto('https://www.cloudemulator.net/app/phone?channelCode=web', wait_until='domcontentloaded', timeout=30000)

       print(f'Status: {response.status}')
       print(f'URL: {page.url}')
       print(f'Title: {page.title()}')

       time.sleep(5)

       # Check for login form
       email_field = page.query_selector('input[type=\"email\"]')
       if email_field:
           print('✅ Login form found')
       else:
           print('⚠️ No login form - may already be logged in or page structure changed')

       browser.close()
   "
   ```

**Solutions**:

- Check internet connection
- Verify Redfinger URL is correct
- May need to handle login first (see below)

---

### Login Fails

**Symptom**: Agent doesn't successfully log in to Redfinger

**Diagnostic Steps**:

1. **Verify credentials**:
   ```bash
   Get-Content .env | Select-String "REDFINGER"
   ```

2. **Test manual login with Playwright**:
   ```bash
   docker-compose run --rm agent-redfinger python3 -c "
   from playwright.sync_api import sync_playwright
   import time
   import os

   email = os.getenv('REDFINGER_EMAIL')
   password = os.getenv('REDFINGER_PASSWORD')

   with sync_playwright() as p:
       browser = p.chromium.launch(headless=False)
       page = browser.new_page()
       page.goto('https://www.cloudemulator.net/app/phone?channelCode=web')

       time.sleep(3)

       # Try to find and fill login form
       try:
           page.wait_for_selector('input[type=\"email\"]', timeout=5000)
           page.fill('input[type=\"email\"]', email)
           page.fill('input[type=\"password\"]', password)
           page.click('button[type=\"submit\"]')

           print('✅ Login form submitted')
           time.sleep(5)

           # Check if login succeeded
           if 'login' not in page.url.lower():
               print('✅ Login successful')
           else:
               print('❌ Still on login page')
       except Exception as e:
           print(f'❌ Login failed: {e}')

       browser.close()
   "
   ```

3. **Check for CAPTCHA**:
   - Redfinger may have CAPTCHA
   - May need manual first login

**Solutions**:

- Verify credentials are correct
- May need to handle CAPTCHA separately
- Consider using session cookies

---

### Canvas Not Found

**Symptom**: Can't locate Android screen canvas element

🧠 **DEEP THINK REQUIRED**: Canvas detection requires understanding of Redfinger's web architecture.

**Diagnostic Steps**:

1. **🧠 DEEP THINK: Inspect page structure**

   ```bash
   docker-compose run --rm agent-redfinger python3 -c "
   from playwright.sync_api import sync_playwright
   import time

   with sync_playwright() as p:
       browser = p.chromium.launch(headless=False)
       page = browser.new_page()
       page.goto('https://www.cloudemulator.net/app/phone?channelCode=web')

       time.sleep(10)  # Wait for full load

       # Search for canvas elements
       canvases = page.query_selector_all('canvas')
       print(f'Found {len(canvases)} canvas elements')

       for i, canvas in enumerate(canvases):
           box = canvas.bounding_box()
           if box:
               print(f'Canvas {i}: {box}')

       # Search for iframes (Android may be in iframe)
       iframes = page.query_selector_all('iframe')
       print(f'Found {len(iframes)} iframe elements')

       browser.close()
   "
   ```

2. **Check if Android screen loads**:
   - Use VNC to visually verify
   - Android screen should be visible in browser
   - If not visible → Redfinger session issue

3. **🧠 DEEP THINK: Multiple possible structures**

   **Possibility A: Single canvas**
   - Android screen rendered to one `<canvas>` element
   - Solution: Use largest canvas

   **Possibility B: Canvas in iframe**
   - Android screen in separate iframe
   - Solution: Switch to iframe context first

   **Possibility C: WebGL canvas**
   - 3D-rendered canvas (for GPU apps)
   - Solution: Filter for WebGL context

   **Possibility D: No canvas (WebRTC)**
   - Video stream instead of canvas
   - Solution: Different capture approach

**Solutions**:

- **Solution A: Use page inspection**
  - Connect VNC and inspect with Chrome DevTools
  - Right-click → Inspect to see actual structure

- **Solution B: Update detection code**
  ```python
  # Try all possible methods
  canvas = page.query_selector('canvas')
  if not canvas:
      # Try in iframe
      iframes = page.frames
      for frame in iframes:
          canvas = frame.query_selector('canvas')
          if canvas:
              break
  ```

**ESCALATION POINT**: If Redfinger has changed their web architecture significantly, may need to document new structure.

---

## Performance Issues

### Slow Response Times

**Symptom**: Agent takes a long time between actions

**Causes**:
- API latency (model inference time)
- Network latency
- Large screenshot processing

**Solutions**:
- Use faster model (GPT-5 Mini instead of GPT-5)
- Reduce screenshot resolution (if possible)
- Use local model (advanced)

---

### High API Costs

**Symptom**: API usage is expensive

**Diagnostic Steps**:

1. **Track API calls**:
   - Each step = 1 reasoner call + 1 grounding call
   - 50 steps = 100 API calls

2. **Calculate cost**:
   - GPT-5: $X per 1M tokens
   - GPT-5 Mini: $Y per 1M tokens (cheaper)
   - glm-4.5v: $Z per 1M tokens

**Solutions**:

- Reduce MAX_STEPS
- Use GPT-5 Mini instead of GPT-5
- Use ZAI (generally cheaper)
- Optimize task descriptions for fewer steps

---

## Emergency Procedures

### Complete Reset

If everything is broken:

```bash
cd C:\Agent-S-Redfinger

# Stop all containers
docker-compose down

# Remove all Docker data
docker system prune -a --volumes

# Rebuild from scratch
docker-compose build --no-cache

# Test basic functionality
docker-compose run --rm agent-redfinger bash -c "echo 'OK'"
```

### Revert to Known Good Config

```bash
# Copy example config
copy .env.example .env

# Edit with valid API keys
notepad .env

# Use proven model
# Set: REASONER_MODEL=glm-4.5v
#      VISION_MODEL=glm-4.5v
```

---

## Logging and Documentation

When troubleshooting, ALWAYS:

1. **Capture full error output**:
   ```bash
   docker-compose up agent-redfinger 2>&1 | tee error_log.txt
   ```

2. **Document what you tried**:
   - Commands run
   - Error messages
   - Solutions attempted

3. **Note your environment**:
   - Docker version: `docker --version`
   - OS: `ver`
   - .env configuration (without secrets)

---

## Escalation Checklist

Before escalating to senior engineer, verify you've:

- [ ] Read this entire troubleshooting guide
- [ ] Captured full error logs
- [ ] Verified API keys are valid
- [ ] Verified Docker is running
- [ ] Tried rebuild with --no-cache
- [ ] Checked all resolutions match (1920x1080)
- [ ] Verified both models are vision-capable
- [ ] Documented all steps taken

Include in escalation:
- Error logs (sanitized of API keys)
- .env configuration (sanitized)
- Docker version and OS version
- Steps to reproduce
- What you've tried

---

**Document Version**: 1.0
**Last Updated**: October 29, 2025
**Maintainer**: Agent-S-Redfinger Team