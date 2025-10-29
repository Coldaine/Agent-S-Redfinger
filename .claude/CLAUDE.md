# Agent-S-Redfinger Project Context

## Project Overview

**Purpose**: Automate Android interactions in Redfinger cloud emulator using Agent S3 (AI agent for GUI automation)

**Architecture**: Docker-based Ubuntu container running Agent S3 with virtual display, controlling web browser that interfaces with Redfinger's cloud Android emulator

**Status**: Implementation complete, ready for validation testing

**Repository**: C:\Agent-S-Redfinger (forked from simular-ai/Agent-S)

---

## Critical Architecture Understanding

### The Stack (4 Layers)

```
Layer 1: Windows Host (Your PC)
    ↓
Layer 2: Docker Container (Ubuntu 22.04)
    ↓ Xvfb virtual display (:99 at 1920x1080)
    ↓ Chromium browser (full-screen at 0,0)
    ↓ Agent S3 Python process
    ↓
Layer 3: Redfinger Web UI (in browser)
    ↓ WebSocket/Canvas connection
    ↓
Layer 4: Android VM (in Redfinger cloud)
```

### Why This Architecture?

**Previous Failed Approach** (C:\AgentS3SecondTry):
- Tried to use Agent-S as a library on Windows
- Browser window at unknown screen position
- Required complex coordinate translation
- Window focus issues

**Current Correct Approach**:
- Agent S3 runs INSIDE Docker container with virtual display
- Browser runs full-screen at (0,0) in container
- PyAutoGUI coordinates match browser coordinates perfectly
- NO coordinate translation needed
- This is how Agent S3 was designed for OSWorld benchmark

**Key Insight**: Agent S3 assumes it controls the entire screen. Running in a Docker container with virtual display makes this assumption true.

---

## Critical Technical Details

### 1. BOTH Models MUST Be Vision-Capable

**Source Code Evidence**:
```python
# gui_agents/s3/agents/worker.py:345
self.generator_agent.add_message(
    generator_message,
    image_content=obs["screenshot"],  # ← Reasoner gets RAW images!
    role="user"
)
```

**Architecture**:
```
Screenshot → Reasoner (vision) → Strategic Plan
Screenshot + Plan → Grounding (vision) → Pixel Coordinates
Coordinates → PyAutoGUI → Click Execution
```

**Valid Vision Models**:
- ✅ glm-4.5v (ZAI, proven working)
- ✅ gpt-5-2025-08-07 (OpenAI, untested here)
- ✅ gpt-5-mini-2025-08-07 (OpenAI, untested here)
- ❌ glm-4.6 (text-only, will fail with error 1210)
- ❌ gpt-4-turbo (text-only)

### 2. Coordinate System

**Container Setup**:
- Virtual display: 1920x1080 at :99
- Browser: Full-screen starts at (0,0)
- PyAutoGUI: Screen-absolute coordinates

**Critical**: No manual coordinate translation! Browser top-left IS screen origin (0,0).

### 3. Current API Configuration

Located in `.env`:

```env
# Working configuration (last verified 2025-10-26)
REASONER_PROVIDER=zai
REASONER_MODEL=glm-4.5v      # Vision-capable
VISION_PROVIDER=zai
VISION_MODEL=glm-4.5v        # Vision-capable

ZAI_API_KEY=2c21c2eed1fa44e7834a6113aeb832a5.i0i3LQY4p00w19xe
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4

# Fallback (untested in this setup)
OPENAI_API_KEY=sk-proj-[...]
```

**Credential Status**:
- ZAI: Last working 2025-10-26 (preferred)
- OpenAI: Needs verification

---

## File Structure

### Essential Files

**Docker Infrastructure**:
- `docker/Dockerfile.redfinger` - Ubuntu 22.04 with GUI stack
- `docker/entrypoint-redfinger.sh` - Startup (Xvfb, VNC, display verify)
- `docker-compose.yml` - Orchestration config

**Application Code**:
- `redfinger/run_redfinger.py` - Main task runner (119 lines)
- `gui_agents/s3/` - Agent S3 implementation (from upstream)

**Configuration**:
- `.env` - Active config with credentials
- `.env.example` - Template for new setups
- `requirements.txt` - Python dependencies (includes playwright)

**Documentation**:
- `docs/GO_FORWARD_PLAN.md` - Architecture rationale (16.9 KB)
- `docs/handoffs/11AM.md` - Implementation status handoff (12 KB)
- `docs/VALIDATION_PLAN_DETAILED.md` - Step-by-step testing guide
- `.claude/CLAUDE.md` - This file

### Key Directories

- `gui_agents/s3/` - Agent S3 core implementation
- `logs/` - Application logs (currently empty)
- `evaluation_sets/` - OSWorld test datasets
- `docker/` - Docker configuration files
- `redfinger/` - Redfinger-specific code

---

## Current State

### Completed ✅
1. Docker infrastructure (Dockerfile, entrypoint, compose)
2. Agent S3 integration (run_redfinger.py)
3. Configuration files (.env, .env.example)
4. Dependencies installed (requirements.txt)
5. Documentation complete

### Not Yet Done ⏳
1. Docker image build
2. Validation testing (6 test phases)
3. Redfinger login automation verification
4. Full task execution test

### Git Status
- Branch: main
- Modified: requirements.txt (added playwright)
- Untracked: .env.example, docker-compose.yml, docker/, docs/, redfinger/

---

## Common Pitfalls & Solutions

### Pitfall 1: Using Text-Only Models
**Symptom**: Error 1210 or "model does not support images"
**Cause**: glm-4.6 or other text-only model
**Solution**: Use glm-4.5v or gpt-5 models

### Pitfall 2: Coordinate Misalignment
**Symptom**: Clicks miss targets
**Cause**: Display not 1920x1080 or browser not full-screen
**Solution**: Verify with `xdpyinfo` and `pyautogui.size()`

### Pitfall 3: API Authentication Failures
**Symptom**: 401 Unauthorized
**Cause**: Invalid or expired API keys
**Solution**: Test with curl/requests, rotate keys if needed

### Pitfall 4: Container Won't Start
**Symptom**: Immediate exit
**Cause**: Display initialization failure
**Solution**: Check entrypoint logs, rebuild with --no-cache

### Pitfall 5: Agent Does Nothing
**Symptom**: Takes screenshot but no actions
**Cause**: Model not generating valid Python code
**Solution**: Check model output in logs, verify task description clarity

---

## Quick Start Commands

```bash
# Navigate to project
cd C:\Agent-S-Redfinger

# Build Docker image (first time, takes 5-10 min)
docker-compose build

# Test container launch
docker-compose run --rm agent-redfinger bash

# Test PyAutoGUI screen size
docker-compose run --rm agent-redfinger python3 -c "import pyautogui; print(pyautogui.size())"

# Test Agent S3 imports
docker-compose run --rm agent-redfinger python3 -c "from gui_agents.s3.agents.agent_s import AgentS3; print('OK')"

# Run full automation
docker-compose up agent-redfinger

# View logs
docker-compose logs -f agent-redfinger

# Stop container
docker-compose down

# Connect VNC (watch agent live)
# VNC Viewer → localhost:5900 (no password)
```

---

## Validation Testing Procedure

**Follow this order** (see `docs/VALIDATION_PLAN_DETAILED.md` for full details):

1. **Phase 1**: Build Docker image (30 min)
2. **Phase 2**: Container validation tests (45 min)
   - Container launch
   - Virtual display check
   - PyAutoGUI screen size
   - Agent S3 imports
   - Browser launch
3. **Phase 3**: API key validation (15 min)
4. **Phase 4**: Simple functionality tests (30 min)
5. **Phase 5**: Full integration test (45 min)
6. **Phase 6**: Redfinger-specific testing (30 min)

**Total Time**: 3-4 hours

---

## Debugging Tools

### 1. VNC Server (Real-Time Viewing)
- Enabled by default (`ENABLE_VNC=true` in .env)
- Connect: `localhost:5900` (no password)
- See exactly what agent sees and does

### 2. Log Files
- Container logs: `docker-compose logs agent-redfinger`
- Application logs: `logs/` directory
- Docker Desktop logs if container won't start

### 3. Interactive Shell
```bash
# Enter container for debugging
docker-compose run --rm agent-redfinger bash

# Inside container:
xdpyinfo -display :99          # Check display
python3 -c "import pyautogui; print(pyautogui.size())"  # Check PyAutoGUI
chromium-browser --version     # Check browser
```

---

## Model Configuration Reference

### Current Setup (ZAI)
```env
REASONER_PROVIDER=zai
REASONER_MODEL=glm-4.5v
VISION_PROVIDER=zai
VISION_MODEL=glm-4.5v
ZAI_API_KEY=2c21c2eed1fa44e7834a6113aeb832a5.i0i3LQY4p00w19xe
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

### Alternative Setup (OpenAI GPT-5)
```env
REASONER_PROVIDER=openai
REASONER_MODEL=gpt-5-2025-08-07
VISION_PROVIDER=openai
VISION_MODEL=gpt-5-2025-08-07
OPENAI_API_KEY=sk-proj-[...]
```

### Alternative Setup (OpenAI GPT-5 Mini)
```env
REASONER_PROVIDER=openai
REASONER_MODEL=gpt-5-mini-2025-08-07
VISION_PROVIDER=openai
VISION_MODEL=gpt-5-mini-2025-08-07
OPENAI_API_KEY=sk-proj-[...]
```

**Note**: Always keep REASONER and VISION models the same for consistency.

---

## Task Configuration

Current task (in `.env`):
```env
REDFINGER_URL=https://www.cloudemulator.net/app/phone?channelCode=web
REDFINGER_EMAIL=pmaclyman@gmail.com
REDFINGER_PASSWORD=Rockstar01!
TASK=Log in to Redfinger and open the settings app
MAX_STEPS=50
```

**Task Format**: Natural language description of what to do
**MAX_STEPS**: Safety limit (agent stops after N iterations)

---

## When Things Go Wrong

### If Docker Build Fails
1. Check Docker Desktop is running
2. Check internet connection (downloads packages)
3. Try: `docker system prune -a` then rebuild

### If Container Exits Immediately
1. Check logs: `docker-compose logs agent-redfinger`
2. Look for display initialization errors
3. Rebuild: `docker-compose build --no-cache`

### If API Calls Fail
1. Test ZAI API key with curl
2. Switch to OpenAI as fallback
3. Check model name is exactly correct
4. Verify model is vision-capable

### If Clicks Miss Targets
1. Verify display: `xdpyinfo -display :99 | grep dimensions`
2. Verify PyAutoGUI: `python3 -c "import pyautogui; print(pyautogui.size())"`
3. Should both show 1920x1080
4. If wrong, rebuild container

### If Agent Generates No Actions
1. Check task description is clear
2. Check model is receiving screenshots
3. Review logs for model output
4. Try simpler task first (e.g., "Click on Google search box")

---

## Security Notes

**IMPORTANT**: The `.env` file contains:
- Valid OpenAI API key
- Valid ZAI API key
- Redfinger account credentials (email/password)

**Actions**:
- ✅ `.env` is in `.gitignore`
- ✅ `.env.example` has placeholders
- ⚠️ Rotate credentials if committed to public repo

---

## Next Steps (After Validation)

1. **Document Validation Results**
   - Which tests passed/failed
   - Performance observations
   - Error messages

2. **Production Hardening**
   - Rotate API keys
   - Set up proper logging
   - Error recovery mechanisms
   - Task completion detection

3. **Advanced Features**
   - Multiple task execution
   - Session persistence
   - Performance optimization
   - Cost tracking

---

## Resources

**Original Working Setup**: `C:\AgentS3` (gui-agents library, working with glm-4.5v as of 2025-10-26)

**Failed Previous Attempt**: `C:\AgentS3SecondTry` (wrong architecture, library approach)

**Agent-S Repository**: https://github.com/simular-ai/Agent-S

**OSWorld Benchmark**: https://github.com/xlang-ai/OSWorld (Agent S3's original use case)

**Docker Desktop**: https://www.docker.com/products/docker-desktop/

**VNC Viewer**: https://www.realvnc.com/en/connect/download/viewer/

**Redfinger**: https://www.cloudemulator.net/

---

## Questions for Investigation

1. **GPT-5 Mini Reasoning Budget**: How to increase reasoning depth for complex tasks?
2. **Canvas Element Detection**: Does Redfinger use `<canvas>` for Android screen? (Need to verify)
3. **Login Flow**: Does current task description handle Redfinger login properly?
4. **Performance**: How many steps does a typical task require?
5. **Cost**: What's the API cost per task with different models?

---

## Technical Debt (42 TODOs in codebase)

**Notable Items**:
- `gui_agents/s3/agents/grounding.py` - Duration specification for wait actions
- `gui_agents/s3/agents/worker.py` - RAG subask level, planner history reuse
- `gui_agents/linux_os_aci.py` - "Terrible coordinate handling" (author's words)

**Impact**: These are optimization opportunities, not blockers.

---

## Success Criteria

### Minimum Success (Ready for Production)
- [ ] Docker image builds
- [ ] Container starts with display
- [ ] PyAutoGUI reports 1920x1080
- [ ] Agent S3 imports work
- [ ] API authentication succeeds
- [ ] Browser launches in container
- [ ] Agent executes at least one action

### Full Success (Production Ready + Validated)
- [ ] Redfinger page loads
- [ ] Agent attempts login
- [ ] Agent interacts with Android UI
- [ ] Task completes successfully
- [ ] Logs show reasonable behavior
- [ ] VNC debugging works

---

## Context for Future Claude Instances

### What Makes This Project Unique

1. **Four-layer virtualization**: Windows → Docker → Browser → Cloud Android
2. **Coordinate alignment requirement**: Must maintain 1:1 screen-to-browser mapping
3. **Vision model requirement**: Both reasoner and grounding need image input
4. **OSWorld architecture adaptation**: Using GUI agent framework for web-based Android control

### Common Misconceptions to Avoid

1. ❌ "Agent-S can be used as a library on Windows" → NO, needs Linux container
2. ❌ "Just one model needs vision" → NO, both reasoner and grounding need it
3. ❌ "Coordinate translation is needed" → NO, full-screen eliminates this
4. ❌ "Any GPT-4/5 model works" → NO, must be vision-capable variant

### When to Re-Read Documentation

- If coordinate issues occur → Review architecture section above
- If model errors occur → Review "BOTH Models MUST Be Vision-Capable"
- If Docker issues occur → Review `docs/VALIDATION_PLAN_DETAILED.md`
- If API errors occur → Check `.env` configuration

---

## Project History Summary

1. **Original Working Setup** (C:\AgentS3): GUI-agents library approach, worked for desktop apps
2. **Failed Redfinger Attempt** (C:\AgentS3SecondTry): Tried library approach for Redfinger, coordinate issues
3. **GO_FORWARD_PLAN.md Created**: Identified need for Docker-based approach
4. **Current Implementation** (C:\Agent-S-Redfinger): Rebuilt with correct architecture, ready for validation

**Key Lesson**: Use Agent S3 as intended (in container with virtual display), don't fight the framework.

---

**Document Version**: 1.0
**Last Updated**: October 29, 2025
**Status**: Implementation complete, validation pending
**Next Action**: Follow validation plan in `docs/VALIDATION_PLAN_DETAILED.md`