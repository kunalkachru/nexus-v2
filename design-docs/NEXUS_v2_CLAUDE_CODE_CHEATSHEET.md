# NEXUS v2: Claude Code CLI — Quick Reference & Commands

> Historical setup reference. Current status and backlog are tracked in [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](../docs/NEXUS_v2_DOC_STATUS_MATRIX.md) and [docs/NEXUS_v2_PRIORITY_BACKLOG.md](../docs/NEXUS_v2_PRIORITY_BACKLOG.md).

**Use this to copy-paste commands into your terminal.**

---

## SETUP (Run Once)

```bash
# Install Node.js 18+ (verify: node --version)
# Install VS Code 1.85+ from https://code.visualstudio.com/

# Install Claude Code globally
npm install -g @anthropic-ai/claude-code@latest

# Authenticate with Anthropic
claude auth

# Verify installation
claude --version

# Create project directory
mkdir ~/nexus-v2 && cd ~/nexus-v2
git init

# Create CLAUDE.md (copy full content from NEXUS_v2_IMPLEMENTATION_SPRINT.md Section 3)
# Create .claudeignore (copy from NEXUS_v2_IMPLEMENTATION_SPRINT.md Section 3)

# Install VS Code extension
# Ctrl+Shift+X (or Cmd+Shift+X) → Search "Claude Code" → Install by Anthropic

# Verify Claude Code works in VS Code
# Click Spark icon (left sidebar) → Should open Claude Code panel
```

---

## DAILY WORKFLOW

### Start of Day

```bash
cd ~/nexus-v2

# 1. Run smoke test (5-10 min)
python training/runner.py --episodes=5 --difficulty=easy

# 2. Read today's sprint plan
cat SPRINT_DAY_X.md  # (Or Claude Code creates this)

# 3. Start Claude Code session in integrated terminal
# In VS Code: Ctrl+` (backtick) to open integrated terminal
claude

# Now you're inside a Claude Code session
# Prompt will show: (claude) >
```

### Inside Claude Code Session (Superpowers Workflow)

```
# Day 1: Scaffold
(claude) > /brainstorm Scaffold FastAPI incident response system
(claude) > /plan Read SPRINT_DAY_1.md and break into subtasks
(claude) > /tdd Implement FastAPI app with /health endpoint
# Accept diffs in VS Code as they appear
(claude) > /review Verify FastAPI structure is correct
(claude) > exit

# Day 2: SENTINEL
(claude) > /brainstorm Design SENTINEL agent architecture
(claude) > /plan
(claude) > /tdd Implement SentinelAgent.classify() with 90% accuracy target
(claude) > /review SENTINEL implementation
(claude) > exit

# Day 3: PRISM
(claude) > /plan Read SPRINT_DAY_3.md
(claude) > /tdd Implement PrismAgent.diagnose() with 75% accuracy target
(claude) > /review PRISM implementation
(claude) > exit

# Day 4: FORGE (Codex day — critical)
(claude) > /brainstorm Codex integration for runbook generation
(claude) > /plan
(claude) > /tdd Implement ForgeAgent.generate_runbook() with syntax validation
# Key: Use claude-3-5-sonnet for testing, not Codex yet
(claude) > export LLM_MODEL=claude-3-5-sonnet  # Save Codex budget
(claude) > /review FORGE implementation
(claude) > exit

# Day 5: GUARDIAN + Reward
(claude) > /plan
(claude) > /tdd Implement GuardianAgent.review() with safety scoring
(claude) > /tdd Implement compute_episode_reward() deterministic grading
(claude) > /review Full episode orchestration
(claude) > exit

# Day 6: GRPO Training (expensive — use Claude Sonnet)
(claude) > export LLM_MODEL=claude-3-5-sonnet
(claude) > /plan
(claude) > /tdd Implement GRPO training loop
(claude) > /tdd Implement curriculum learning
(claude) > /review Training pipeline
(claude) > exit

# Day 7: Dashboard + Ship
(claude) > /gsd Create metrics dashboard
(claude) > /gsd Create demo.py for judges
(claude) > /gsd Deploy to HuggingFace Spaces
(claude) > exit
```

### End of Day (Testing & Commit)

```bash
# After exiting Claude Code session:

# Run unit tests
pytest tests/ -v

# Format code (optional)
python -m black server/ training/
python -m isort server/ training/

# Commit progress
git add -A
git commit -m "Day X: [Component] — [Status]"
git push origin main

# Example commits:
# git commit -m "Day 1: FastAPI scaffold — /health endpoint working"
# git commit -m "Day 2: SENTINEL agent — 90% classification accuracy"
# git commit -m "Day 6: GRPO training — 30-ep training shows 76% improvement"
```

---

## CRITICAL DAILY TESTS (Run These Each Morning)

```bash
# Smoke test: Make sure nothing broke overnight
python training/runner.py --episodes=5 --difficulty=easy
# Should complete without errors, show reward for each episode

# Unit tests: Verify all components still work
pytest tests/ -v --tb=short
# All tests should pass (⚠️ Fix immediately if any fail)

# Integration test: Full episode from start to finish (Days 5+)
python training/runner.py --episodes=1 --difficulty=easy -v
# Should show: SENTINEL → PRISM → FORGE → GUARDIAN → execute → verify → reward

# Full training test: 30 episodes (Days 6+)
python training/grpo_loop.py --episodes=30 --save-curve=./metrics_day6.json
# Should complete in ~1 hour, show upward reward trend
```

---

## TROUBLESHOOTING QUICK FIXES

```bash
# Claude Code won't start
claude
# If fails: Check if ANTHROPIC_API_KEY is set
echo $ANTHROPIC_API_KEY  # Should show your key
# If empty: export ANTHROPIC_API_KEY=sk-...

# RL reward is 0.0 (broken grader)
# In grader.py, add debug output:
# print(f"DEBUG reward computation: mttr={reward.mttr}, diagnosis={reward.diagnosis}...")
# Run pytest tests/test_grader.py -v -s  # -s shows print statements
# Look for NaN or unexpected 0.0 values

# OpenAI API calls timing out
# Reduce max_tokens in openai_client calls:
# response = await client.chat.completions.create(
#     max_tokens=500,  # Was 1000
#     ...
# )

# HF Space deployment fails
# Check Docker image size:
docker build -t nexus-v2 .
docker images | grep nexus-v2  # Size should be <10GB
# If too large: Remove training data, use python:3.11-slim base image

# Need to revert a day's work
git log --oneline  # See commit history
git reset --hard HEAD~3  # Throw away last 3 commits
# Or revert specific commits:
git revert --no-edit HEAD~2

# Claude Code changes aren't showing in VS Code
# VS Code auto-detects file changes, but if stuck:
# 1. Click the file in VS Code to refresh
# 2. Or: File → Revert File
# 3. Or: In terminal, run: git checkout -- server/agents/sentinel.py
```

---

## ENVIRONMENT VARIABLES TO SET

```bash
# At start of each session:
export ANTHROPIC_API_KEY=sk-...  # Your Anthropic API key
export OPENAI_API_KEY=sk-...     # Your OpenAI API key (for Codex)

# Day 4+ (save money on Codex):
export LLM_PROVIDER=anthropic
export LLM_MODEL=claude-3-5-sonnet  # Cheaper than Codex
# Then Day 6 final demo, switch back:
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o

# HF Space deployment:
export HF_TOKEN=hf_...  # Your HuggingFace token
huggingface-cli login

# Debugging (verbose output):
export DEBUG=true
python training/runner.py --episodes=1 --log-level=debug
```

---

## KEY SLASH COMMANDS IN CLAUDE CODE

```
/brainstorm [task]        → Socratic design phase (Claude asks questions)
/plan [task]              → Break into 2-5 min subtasks, generate SPRINT_DAY_X.md
/tdd [feature]            → Test-driven: write tests first, then code
/review [component]       → Code review before merging
/parallel [task1] [task2] → Run 2 subagents in parallel
/gsd [task]               → "Get Stuff Done" — skip planning, just build
/read [filepath]          → Read a file into context (use for master documents)
/settings                 → Configure Claude Code behavior
/help                     → Show all available commands
```

---

## IMPORTANT FILE LOCATIONS

```
# Master documents (reference these):
/mnt/user-data/outputs/NEXUS_v2_Master_Product_Document.md
/mnt/user-data/outputs/NEXUS_v2_Design_Document.md
/mnt/user-data/outputs/NEXUS_v2_Product_Roadmap.md
/mnt/user-data/outputs/NEXUS_v2_IMPLEMENTATION_SPRINT.md
/mnt/user-data/outputs/NEXUS_v2_IMPLEMENTATION_SPRINT.md (THIS FILE)

# Your project:
~/nexus-v2/
├── server/
│   ├── app.py
│   └── agents/
│       ├── sentinel.py
│       ├── prism.py
│       ├── forge.py
│       └── guardian.py
├── training/
│   ├── grpo_loop.py
│   └── policy.py
├── tests/
│   ├── test_agents.py
│   └── test_training.py
└── CLAUDE.md
```

---

## COPY-PASTE: FULL FIRST-TIME SETUP

```bash
#!/bin/bash
# Save this as setup.sh, then run: bash setup.sh

# Install Claude Code
npm install -g @anthropic-ai/claude-code@latest

# Create project
mkdir ~/nexus-v2 && cd ~/nexus-v2
git init

# Create CLAUDE.md
cat > CLAUDE.md << 'EOF'
# NEXUS v2: Project Context

## Overview
NEXUS v2 is an RL-trained autonomous incident response system.

- **Master docs:** /mnt/user-data/outputs/NEXUS_v2_Master_Product_Document.md
- **Tech spec:** /mnt/user-data/outputs/NEXUS_v2_Design_Document.md

## Architecture
- 4 RL agents: SENTINEL, PRISM, FORGE, GUARDIAN
- OpenAI Codex for runbook generation
- GRPO training loop
- SQLite database (HF Space compatible)

## Tech Stack
Python 3.11, FastAPI, PyTorch, TRL (GRPO), OpenAI SDK

## Daily Workflow
1. Morning: Run smoke test (5 episodes)
2. Read SPRINT_DAY_X.md
3. Use Superpowers: /plan, /tdd, /review
4. Evening: Test and commit

See /mnt/user-data/outputs/NEXUS_v2_IMPLEMENTATION_SPRINT.md for full details
EOF

# Create .claudeignore
cat > .claudeignore << 'EOF'
.git/
__pycache__/
*.pyc
.pytest_cache/
venv/
env/
.DS_Store
*.log
EOF

# Create requirements.txt (Claude Code will expand this)
cat > requirements.txt << 'EOF'
fastapi==0.115.0
uvicorn==0.30.0
pydantic==2.5.0
httpx==0.25.0
aiosqlite==0.19.0
networkx==3.2
torch==2.1.0
trl==0.8.0
openai==1.5.0
pytest==7.4.0
pytest-asyncio==0.21.0
EOF

# Create basic directory structure
mkdir -p server/agents training incidents frontend tests

# Create __init__.py files
touch server/__init__.py server/agents/__init__.py training/__init__.py

# Initialize git
git add -A
git commit -m "Initial commit: project scaffold"

echo "✅ Setup complete! Run: cd ~/nexus-v2 && claude"
```

---

## COPY-PASTE: SUPERPOWERS INSTALLATION (If Needed)

```bash
# Inside a Claude Code session:
(claude) > /plugin install superpowers

# Or manually add to CLAUDE.md:
# ## Superpowers Configuration
# This project uses the Superpowers plugin for TDD and structured development.
# Install with: /plugin install superpowers
# Then use: /plan, /tdd, /review slash commands
```

---

## DEMO DAY CHECKLIST (Day 7)

```bash
# 1 hour before judges arrive:

# Verify live URL works
curl https://huggingface.co/spaces/YOUR_USERNAME/nexus-v2
# Should return 200, not 404

# Test demo script (run locally first)
python demo.py --incident=INC001 --verify-deterministic=true
# Should show: classification → diagnosis → runbook → execution → reward

# Check metrics dashboard
curl http://localhost:8000/metrics-dashboard.html
# Should show reward curve trending upward

# Prepare pitch (30 seconds)
cat > PITCH.txt << 'EOF'
"NEXUS is the first RL-trained incident response system. 

Watch: incident fires → 4 agents collaborate → Codex generates a bash script → executes safely. 

Industry MTTR is 74 minutes. Our agents trained on 30 incidents solve issues in 3 minutes. 

And they get faster every incident. This is real learning, not templates."
EOF

# Prepare backup (if live URL dies):
# 1. Local deployment: python -m uvicorn server.app:app --reload
# 2. Record screen of demo.py running
# 3. Have reward curve image saved (generated Day 6)

echo "✅ Demo ready!"
```

---

## GIT COMMANDS YOU'LL USE

```bash
# Check status
git status

# See what changed
git diff

# Stage all changes
git add -A

# Commit with message
git commit -m "Day 4: FORGE + Codex integration, syntax validation works"

# Push to GitHub
git push origin main

# Tag a milestone
git tag -a v0.2.0-day-4 -m "FORGE agent complete"
git push --tags

# See history
git log --oneline

# Revert last commit (if mistake)
git reset --soft HEAD~1  # Keeps changes, unstages

# Undo all changes to file
git checkout -- server/agents/sentinel.py

# Go back to specific commit
git reset --hard abc123def  # Throws away everything after commit abc123
```

---

## PERFORMANCE EXPECTATIONS BY DAY

| Day | Component | Expected time | Expected tests passing |
|-----|-----------|----------------|------------------------|
| 1 | Scaffold | 6-8 hr | 1/1 (/health) |
| 2 | SENTINEL | 6-8 hr | 8/8 (classify accuracy 90%+) |
| 3 | PRISM | 6-8 hr | 8/8 (diagnose accuracy 75%+) |
| 4 | FORGE | 8-10 hr | 8/8 (syntax validation 95%+) |
| 5 | GUARDIAN + reward | 8-10 hr | 8/8 (safety) + reward deterministic |
| 6 | GRPO training | 8-10 hr | 30-ep train, reward 0.28→0.68 |
| 7 | Dashboard + ship | 10-12 hr | Live URL + demo works |

---

## YOU'RE READY

Copy this into your VS Code terminal:

```bash
mkdir ~/nexus-v2 && cd ~/nexus-v2
npm install -g @anthropic-ai/claude-code@latest
claude auth
claude
```

Then inside the Claude Code session:

```
(claude) > /read /mnt/user-data/outputs/NEXUS_v2_IMPLEMENTATION_SPRINT.md
(claude) > /plan Day 1: Scaffold FastAPI incident response system
(claude) > /tdd Implement FastAPI app with /health endpoint
```

**Go build the future of incident response. 🚀**
