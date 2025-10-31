# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Purpose**: Automate Android interactions in Redfinger cloud emulator using Agent S3 (AI agent for GUI automation)

**Architecture**: Docker-based Ubuntu container running Agent S3 with virtual display, controlling web browser that interfaces with Redfinger's cloud Android emulator

**Status**: Validation testing in progress (see docs/VALIDATION_STATUS.md)

**Repository**: Forked from simular-ai/Agent-S

---

## Critical Architecture Understanding

### The Stack (4 Layers)

```
Layer 1: Windows Host
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

**Key Insight**: Agent S3 assumes it controls the entire screen. Running in a Docker container with virtual display makes this assumption true. The browser runs full-screen at (0,0), so PyAutoGUI coordinates match browser coordinates perfectly with NO coordinate translation needed.

**Previous Failed Approach**: Tried to use Agent-S as a library on Windows with browser window at unknown screen position, requiring complex coordinate translation. Current approach uses Docker container as originally designed for OSWorld benchmark.

---

## Critical Technical Details

### 1. BOTH Models MUST Be Vision-Capable

**Source**: `gui_agents/s3/agents/worker.py:345` - Both reasoner and grounding agents receive raw images

**Architecture Flow**:
```
Screenshot → Reasoner (vision) → Strategic Plan
Screenshot + Plan → Grounding (vision) → Pixel Coordinates
Coordinates → PyAutoGUI → Click Execution
```

**Valid Vision Models**:
- ✅ glm-4.5v (ZAI, proven working)
- ✅ gpt-5-2025-08-07 (OpenAI)
- ✅ gpt-5-mini-2025-08-07 (OpenAI)
- ❌ glm-4.6 (text-only, will fail with error 1210)
- ❌ gpt-4-turbo (text-only)

### 2. Coordinate System

**Container Setup**:
- Virtual display: 1920x1080 at :99
- Browser: Full-screen starts at (0,0)
- PyAutoGUI: Screen-absolute coordinates

**Critical**: No manual coordinate translation! Browser top-left IS screen origin (0,0).

### 3. API Configuration

Located in `.env` (copy from `.env.example`):

**Current Working Configuration** (last verified 2025-10-26):
```env
REASONER_PROVIDER=zai
REASONER_MODEL=glm-4.5v      # Vision-capable
VISION_PROVIDER=zai
VISION_MODEL=glm-4.5v        # Vision-capable

ZAI_API_KEY=<your_key>
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

**Alternative (OpenAI GPT-5)**:
```env
REASONER_PROVIDER=openai
REASONER_MODEL=gpt-5-2025-08-07
VISION_PROVIDER=openai
VISION_MODEL=gpt-5-2025-08-07
OPENAI_API_KEY=<your_key>
```

---

## Essential Commands

### Docker Operations

```bash
# Build Docker image (first time, 5-10 min)
docker-compose build

# Rebuild without cache (if dependencies changed)
docker-compose build --no-cache

# Run task automation (uses .env configuration)
docker-compose up agent-redfinger

# Run with specific task override
docker-compose run --rm agent-redfinger python3 /workspace/redfinger/run_redfinger.py \
  --url "https://www.cloudemulator.net/app/phone?channelCode=web" \
  --task "Click on the Google search box" \
  --max-steps 10

# Interactive debugging (enter container)
docker-compose run --rm agent-redfinger bash

# View logs
docker-compose logs -f agent-redfinger

# Stop and clean up
docker-compose down
```

### Validation Testing (Phase 5 Harness)

The Phase 5 harness provides robust testing with timeout protection, real-time logging, and automatic validation report generation.

```powershell
# Pre-flight check (validates Docker, API keys, etc.)
python scripts/run_phase5_harness.py --dry-run

# Run Phase 5 test with GPT-5
python scripts/run_phase5_harness.py \
  --provider openai \
  --model gpt-5-2025-08-07 \
  --model-temperature 1.0 \
  --url "https://www.google.com" \
  --task "Click on the search box and type weather" \
  --max-steps 5 \
  --overall-timeout 900 \
  --stall-timeout 120

# Run Phase 5 test with ZAI GLM-4.5V
python scripts/run_phase5_harness.py \
  --provider zai \
  --model glm-4.5v \
  --model-temperature 1.0 \
  --url "https://www.google.com" \
  --task "Click on the search box" \
  --max-steps 5

# Hygiene options
python scripts/run_phase5_harness.py \
  --auto-start-docker \           # Start Docker Desktop if not running
  --compose-down-before \          # Clean containers before test
  --compose-down-after \           # Clean containers after test
  --compose-build \                # Rebuild image before test
  --provider openai \
  --model gpt-5-2025-08-07 \
  --url "https://www.google.com" \
  --task "Click search box"

# Generate validation report
python scripts/generate_validation_report.py
```

**Harness Features**:
- Timeout protection (overall + stall detection)
- Real-time log streaming to files
- Structured results in JSON
- Automatic validation report refresh
- Exit codes: 0 (passed), 1 (failed)

**Test Artifacts** (saved to `logs/phase5/<timestamp>/`):
- `stdout.log` - Container output
- `stderr.log` - Error messages
- `meta.json` - Test configuration
- `result.json` - Test results and status

### Development Workflow

```bash
# ALWAYS work on feature branches (NEVER commit directly to main)
git checkout -b feature/your-feature-name

# Make changes, update CHANGELOG.md

# Run pre-commit checks
python scripts/pre_commit_check.py

# Commit with descriptive message
git commit -m "feat: add new feature"

# Push and open PR
git push origin feature/your-feature-name
```

**Required for ALL PRs**:
1. Feature branch (never commit to main)
2. Update CHANGELOG.md
3. Pass pre-flight checks
4. Get review approval

See [CONTRIBUTING.md](CONTRIBUTING.md) for full workflow details.

### Container Diagnostics

```bash
# Inside container (after: docker-compose run --rm agent-redfinger bash)

# Check display
xdpyinfo -display :99 | grep dimensions  # Should show 1920x1080

# Check PyAutoGUI screen size
python3 -c "import pyautogui; print(pyautogui.size())"  # Should show Size(width=1920, height=1080)

# Check Agent S3 imports
python3 -c "from gui_agents.s3.agents.agent_s import AgentS3; print('OK')"

# Check browser
chromium-browser --version

# Test API keys
python3 -c "import os; print(os.getenv('OPENAI_API_KEY')[:10])"
```

### VNC Debugging

Connect via VNC Viewer to `localhost:5900` (no password) to watch the agent live. Enable in `.env`:
```env
ENABLE_VNC=true
```

---

## File Structure

### Core Implementation Files

**Docker Infrastructure**:
- `docker/Dockerfile.redfinger` - Ubuntu 22.04 with GUI stack
- `docker/entrypoint-redfinger.sh` - Startup (Xvfb, VNC, display verify)
- `docker-compose.yml` - Orchestration config

**Application Code**:
- `redfinger/run_redfinger.py` - Main task runner (159 lines)
  - Uses Playwright to launch browser
  - Integrates Agent S3
  - Executes agent actions via PyAutoGUI
  - Emits `HARNESS:STATUS=passed/failed` for test harness

**Agent S3 Implementation** (from upstream):
- `gui_agents/s3/agents/agent_s.py` - Main agent loop
- `gui_agents/s3/agents/worker.py` - Reasoner (strategic planning)
- `gui_agents/s3/agents/grounding.py` - Grounding (pixel coordinates)
- `gui_agents/s3/cli_app.py` - CLI reference implementation

**Testing Infrastructure**:
- `scripts/run_phase5_harness.py` - Robust test harness with timeouts
- `scripts/generate_validation_report.py` - Generate validation status report
- `scripts/pre_commit_check.py` - Pre-commit validation checks
- `scripts/setup_git_workflow.py` - Git workflow setup

**Configuration**:
- `.env` - Active config with credentials (NOT in git)
- `.env.example` - Template for new setups
- `requirements.txt` - Python dependencies

**Documentation**:
- `README.md` - Project overview and quickstart
- `CONTRIBUTING.md` - Git workflow and contribution guidelines
- `CHANGELOG.md` - Version history and changes
- `docs/VALIDATION_STATUS.md` - Auto-generated test results
- `docs/VALIDATION_PLAN_DETAILED.md` - Step-by-step testing procedures
- `docs/TROUBLESHOOTING_GUIDE.md` - Common issues and solutions
- `docs/GIT_WORKFLOW_QUICK_REFERENCE.md` - Git workflow cheatsheet

---

## Common Pitfalls & Solutions

### Pitfall 1: Using Text-Only Models
**Symptom**: Error 1210 or "model does not support images"
**Cause**: glm-4.6 or other text-only model
**Solution**: Use glm-4.5v, gpt-5-2025-08-07, or gpt-5-mini-2025-08-07

### Pitfall 2: Coordinate Misalignment
**Symptom**: Clicks miss targets
**Cause**: Display not 1920x1080 or browser not full-screen
**Solution**: Verify with `xdpyinfo` and `pyautogui.size()` inside container

### Pitfall 3: API Authentication Failures
**Symptom**: 401 Unauthorized
**Cause**: Invalid or expired API keys
**Solution**: Verify keys in `.env`, test with harness `--dry-run`

### Pitfall 4: Container Won't Start
**Symptom**: Immediate exit
**Cause**: Display initialization failure
**Solution**: Check logs with `docker-compose logs`, rebuild with `--no-cache`

### Pitfall 5: Agent Does Nothing
**Symptom**: Takes screenshot but no actions
**Cause**: Model not generating valid Python code
**Solution**: Check logs, verify task description clarity, ensure vision-capable model

### Pitfall 6: Test Hangs Forever
**Symptom**: Harness never completes
**Cause**: Agent stuck in loop or waiting indefinitely
**Solution**: Use harness timeouts: `--overall-timeout 900 --stall-timeout 120`

### Pitfall 7: Committing to Main Branch
**Symptom**: Direct commits to main
**Cause**: Bypassing feature branch workflow
**Solution**: ALWAYS create feature branch first, open PR for review

---

## Model Configuration Examples

### Current Setup (ZAI)
```env
REASONER_PROVIDER=zai
REASONER_MODEL=glm-4.5v
VISION_PROVIDER=zai
VISION_MODEL=glm-4.5v
ZAI_API_KEY=<your_key>
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

### Alternative (OpenAI GPT-5)
```env
REASONER_PROVIDER=openai
REASONER_MODEL=gpt-5-2025-08-07
VISION_PROVIDER=openai
VISION_MODEL=gpt-5-2025-08-07
OPENAI_API_KEY=<your_key>
```

### Alternative (OpenAI GPT-5 Mini)
```env
REASONER_PROVIDER=openai
REASONER_MODEL=gpt-5-mini-2025-08-07
VISION_PROVIDER=openai
VISION_MODEL=gpt-5-mini-2025-08-07
OPENAI_API_KEY=<your_key>
```

**Note**: Always keep REASONER and VISION models the same for consistency.

---

## Task Configuration

Configure tasks in `.env`:
```env
REDFINGER_URL=https://www.cloudemulator.net/app/phone?channelCode=web
REDFINGER_EMAIL=your_email@example.com
REDFINGER_PASSWORD=your_password
TASK=Log in to Redfinger and open the settings app
MAX_STEPS=50
```

**Task Format**: Natural language description
**MAX_STEPS**: Safety limit (agent stops after N iterations)

---

## Debugging Tools

### 1. VNC Server (Real-Time Viewing)
- Connect: `localhost:5900` (no password)
- Enable: Set `ENABLE_VNC=true` in `.env`
- See exactly what agent sees and does

### 2. Log Files
- Container logs: `docker-compose logs agent-redfinger`
- Application logs: `logs/` directory
- Test artifacts: `logs/phase5/<timestamp>/`

### 3. Interactive Shell
```bash
docker-compose run --rm agent-redfinger bash
# Then run diagnostic commands inside container
```

### 4. Validation Status
```powershell
# View current validation status
cat docs/VALIDATION_STATUS.md

# Regenerate validation report
python scripts/generate_validation_report.py
```

---

## Git Workflow (IMPORTANT!)

**🚨 All changes must follow this workflow**:

1. **Never commit directly to main** - Always use feature branches
2. **Update CHANGELOG.md** - Required for every PR
3. **Run pre-flight checks** - Before pushing
4. **Open Pull Request** - All changes require review
5. **Get approval** - Merge only after review

See [CONTRIBUTING.md](CONTRIBUTING.md) for complete workflow details.

**Quick Reference**:
```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Make changes and update CHANGELOG.md

# 3. Run pre-flight checks
python scripts/pre_commit_check.py

# 4. Commit
git commit -m "feat: descriptive message"

# 5. Push and open PR
git push origin feature/your-feature
```

---

## Security Notes

**IMPORTANT**: The `.env` file contains:
- OpenAI API key
- ZAI API key
- Redfinger account credentials

**Actions**:
- ✅ `.env` is in `.gitignore`
- ✅ `.env.example` has placeholders
- ⚠️ Rotate credentials if exposed

---

## Common Development Tasks

### Adding a New Feature

1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes to code
3. Update CHANGELOG.md under "Unreleased"
4. Run pre-flight checks: `python scripts/pre_commit_check.py`
5. Test with harness: `python scripts/run_phase5_harness.py --dry-run`
6. Commit: `git commit -m "feat: add new feature"`
7. Push and open PR: `git push origin feature/new-feature`

### Debugging a Failed Test

1. Check validation status: `cat docs/VALIDATION_STATUS.md`
2. View test artifacts: `logs/phase5/<timestamp>/stdout.log`
3. Check result: `logs/phase5/<timestamp>/result.json`
4. Enable VNC for live debugging: Set `ENABLE_VNC=true`
5. Connect VNC to `localhost:5900` and re-run test
6. Check logs for model errors or action failures

### Modifying Agent Behavior

**Agent S3 Code** (upstream, modify carefully):
- `gui_agents/s3/agents/worker.py` - Reasoner logic
- `gui_agents/s3/agents/grounding.py` - Grounding logic
- `gui_agents/s3/agents/agent_s.py` - Main agent loop

**Redfinger-Specific Code**:
- `redfinger/run_redfinger.py` - Task runner and browser setup

After modifying:
1. Rebuild Docker image: `docker-compose build`
2. Test with simple task first
3. Verify with harness: `python scripts/run_phase5_harness.py ...`

### Changing Model Configuration

1. Update `.env` with new model
2. Verify model is vision-capable (check models.md)
3. Test API key: `python scripts/run_phase5_harness.py --dry-run`
4. Run simple test: Use Google search task with `--max-steps 5`
5. Check results in `logs/phase5/`

---

## Context for Future Claude Instances

### What Makes This Project Unique

1. **Four-layer virtualization**: Windows → Docker → Browser → Cloud Android
2. **Coordinate alignment requirement**: Must maintain 1:1 screen-to-browser mapping
3. **Vision model requirement**: Both reasoner and grounding need image input
4. **OSWorld architecture adaptation**: Using GUI agent framework for web-based Android control
5. **Robust testing infrastructure**: Harness with timeout protection and structured logging

### Common Misconceptions to Avoid

1. ❌ "Agent-S can be used as a library on Windows" → NO, needs Linux container
2. ❌ "Just one model needs vision" → NO, both reasoner and grounding need it
3. ❌ "Coordinate translation is needed" → NO, full-screen eliminates this
4. ❌ "Any GPT-4/5 model works" → NO, must be vision-capable variant
5. ❌ "Can commit directly to main" → NO, must use feature branch + PR

### When to Re-Read Documentation

- Coordinate issues → Review "Critical Architecture Understanding"
- Model errors → Review "BOTH Models MUST Be Vision-Capable"
- Docker issues → Review [docs/TROUBLESHOOTING_GUIDE.md](docs/TROUBLESHOOTING_GUIDE.md)
- API errors → Check `.env` configuration
- Git workflow questions → Review [CONTRIBUTING.md](CONTRIBUTING.md)
- Test failures → Check [docs/VALIDATION_STATUS.md](docs/VALIDATION_STATUS.md)

---

## Project History

1. **Original Working Setup** (C:\AgentS3): GUI-agents library, worked for desktop apps
2. **Failed Redfinger Attempt** (C:\AgentS3SecondTry): Library approach, coordinate issues
3. **GO_FORWARD_PLAN.md Created**: Identified need for Docker-based approach
4. **Current Implementation**: Rebuilt with correct architecture, validation in progress
5. **Testing Infrastructure Added**: Robust harness with timeout protection
6. **Git Workflow Established**: Feature branches, PR reviews, CHANGELOG.md

**Key Lesson**: Use Agent S3 as intended (in container with virtual display), don't fight the framework.

---

## Technical Debt

**Notable TODOs** (42 in codebase):
- `gui_agents/s3/agents/grounding.py` - Duration specification for wait actions
- `gui_agents/s3/agents/worker.py` - RAG subask level, planner history reuse
- `gui_agents/linux_os_aci.py` - "Terrible coordinate handling" (author's words)

**Impact**: These are optimization opportunities, not blockers.

---

## Resources

- **Upstream Repository**: https://github.com/simular-ai/Agent-S
- **OSWorld Benchmark**: https://github.com/xlang-ai/OSWorld
- **Agent S3 Paper**: https://arxiv.org/abs/2510.02250
- **Redfinger**: https://www.cloudemulator.net/

---

**Document Version**: 2.0
**Last Updated**: October 30, 2025
**Status**: Validation testing in progress
**Next Action**: Continue Phase 5 validation tests, document results
