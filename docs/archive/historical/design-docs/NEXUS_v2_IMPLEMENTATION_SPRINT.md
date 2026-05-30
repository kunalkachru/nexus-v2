# NEXUS v2: Implementation Sprint Plan
## Claude Code CLI + Superpowers Automated Build

> Historical hackathon sprint. The live status, gaps, and next priorities are tracked in [docs/NEXUS_v2_DOC_STATUS_MATRIX.md](../../../NEXUS_v2_DOC_STATUS_MATRIX.md) and [docs/NEXUS_v2_PRIORITY_BACKLOG.md](../../../NEXUS_v2_PRIORITY_BACKLOG.md).

**Timeline:** 7 days (Hackathon)  
**Tool:** Claude Code CLI in VS Code + Superpowers plugin  
**Goal:** Ship working RL agent system with Codex integration  
**Approach:** Test-driven, micro-tasked, with structured planning

---

## QUICKSTART (5 minutes to first build)

### Step 1: Install Prerequisites

```bash
# Install Node.js 18+ (if not already installed)
# Check: node --version (should be v18+)

# Install VS Code 1.85+ (from https://code.visualstudio.com/)

# If on Windows: Install WSL2
# https://learn.microsoft.com/en-us/windows/wsl/install
```

### Step 2: Install Claude Code CLI

```bash
# Install globally via npm
npm install -g @anthropic-ai/claude-code@latest

# Authenticate
claude auth

# Verify installation
claude --version
```

### Step 3: Install Claude Code Extension in VS Code

```
Ctrl+Shift+X (or Cmd+Shift+X on Mac) → Search "Claude Code" → Install (by Anthropic)
```

### Step 4: Install Superpowers Plugin

```bash
# In your project directory (after creating it below), run:
claude /plugin install superpowers

# Or manually: add to your CLAUDE.md (see Section 3 below)
```

### Step 5: Create Project Directory & Initialize

```bash
# Clone or create new repo
mkdir nexus-v2
cd nexus-v2

# Initialize git
git init

# Create project structure (see Section 2 below)
```

---

## SECTION 1: HOW TO USE CLAUDE CODE CLI WITH THE MASTER DOCUMENTS

### The Workflow

1. **Claude Code reads the master documents** you created (stored in `/mnt/user-data/outputs/`)
2. **You give it a sprint task** (e.g., "Implement SENTINEL agent using Day 1 spec")
3. **Claude Code generates code** with Superpowers structure (planning → TDD → implementation → review)
4. **Real-time diffs appear in VS Code** — you accept/reject changes
5. **Code lands in your repo** — automatically formatted and tested

### Key Commands

```bash
# Start a Claude Code session in your project
claude

# Reference the master documents (from within a claude session):
claude> /read /mnt/user-data/outputs/NEXUS_v2_Master_Product_Document.md section 5

# Reference the technical spec:
claude> /read /mnt/user-data/outputs/NEXUS_v2_Design_Document.md

# Reference today's sprint task:
claude> /read ./SPRINT_DAY_1.md

# Use Superpowers to plan a complex task:
claude> /plan Build the SENTINEL agent using TDD

# Use Superpowers for test-driven development:
claude> /tdd Implement sentinel.classify() with 95% accuracy target

# Let Claude Code auto-accept safe changes (after you trust it):
claude> /settings auto-accept=true
```

### Superpowers Skills You'll Use

```
/brainstorm    — Design the architecture before coding
/plan          — Break down sprint tasks into 2-5 min subtasks
/tdd           — Write tests first, then implementation
/review        — Get Claude Code to review code before shipping
/parallel      — Run multiple sub-agents on independent tasks
/gsd           — "Get Stuff Done" — skip ceremony for quick tasks
```

---

## SECTION 2: PROJECT STRUCTURE (Set This Up Now)

Create this directory structure in your `nexus-v2/` folder:

```
nexus-v2/
├── CLAUDE.md                    # Project context for Claude Code
├── .claudeignore                # What Claude Code should ignore
├── requirements.txt             # Python dependencies
├── .gitignore
├── README.md
│
├── server/
│   ├── app.py                   # FastAPI main app
│   ├── models.py                # Pydantic models
│   ├── config.py                # Configuration (LLM provider, etc.)
│   ├── grader.py                # Reward computation
│   ├── curriculum.py            # Difficulty adapter
│   ├── sandbox.py               # Script execution sandbox
│   ├── memory_graph.py          # Incident similarity graph
│   ├── db.py                    # SQLite + aiosqlite
│   │
│   └── agents/
│       ├── __init__.py
│       ├── base.py              # Agent protocol (for LangChain wrapping)
│       ├── sentinel.py          # Classification agent
│       ├── prism.py             # Diagnosis agent
│       ├── forge.py             # Codex integration + runbook gen
│       └── guardian.py          # Safety review agent
│
│   └── orchestrator.py          # Episode runner (non-RL)
│
├── incidents/
│   ├── catalogue.py             # Incident definitions
│   └── INC*.json                # Incident data (INC001–INC008)
│
├── training/
│   ├── grpo_loop.py             # GRPO training
│   ├── policy.py                # Policy networks
│   ├── runner.py                # Episode runner
│   └── __init__.py
│
├── frontend/
│   ├── index.html               # Main dashboard
│   ├── metrics.html             # Reward curves
│   └── static/
│
├── tests/
│   ├── test_agents.py
│   ├── test_grader.py
│   ├── test_training.py
│   └── conftest.py              # Pytest fixtures
│
└── SPRINT_DAY_*.md              # Daily task breakdowns (created as you go)
```

---

## SECTION 3: CREATE CLAUDE.MD (Critical for Claude Code)

Create `nexus-v2/CLAUDE.md`:

```markdown
# NEXUS v2: Project Context for Claude Code

## Project Overview
NEXUS v2 is an RL-trained autonomous incident response system using OpenAI Codex.

- **Hackathon:** OpenAI × Outskill Codex Hackathon (7 days, starting May 25, 2026)
- **Repo docs:** See /mnt/user-data/outputs/NEXUS_v2_Master_Product_Document.md
- **Tech spec:** See /mnt/user-data/outputs/NEXUS_v2_Design_Document.md
- **Build timeline:** /mnt/user-data/outputs/NEXUS_v2_IMPLEMENTATION_SPRINT.md (this file)

## Key Constraints
1. **Solo build** — One developer, 7 days
2. **HF Space deployment** — Zero external dependencies (SQLite only, no Postgres/Redis)
3. **RL-native** — GRPO training is the core differentiator, not a nice-to-have
4. **Codex integration** — Every runbook is Codex-generated, not a template
5. **Daily testing** — Run a 5-episode training test every morning to catch breakage early

## Architecture
- **4 RL-trained agents:** SENTINEL (classify), PRISM (diagnose), FORGE (generate), GUARDIAN (review)
- **1 deterministic orchestrator:** NEXUS CORE (routes between agents, not RL-trained)
- **Reward signal:** 5-dimensional (MTTR 30%, diagnosis 25%, customer 20%, coordination 15%, oversight 5%)
- **Curriculum:** 5 difficulty levels (Easy → Nightmare), auto-advance at 55% reward threshold

## Tech Stack
- **Language:** Python 3.11
- **Web:** FastAPI 0.115+, uvicorn, Pydantic v2
- **RL:** TRL (GRPO), PyTorch
- **LLM:** OpenAI SDK (default: gpt-4o, fallback: Claude)
- **Database:** SQLite + aiosqlite (no external DB for hackathon)
- **Testing:** pytest, pytest-asyncio
- **Deployment:** Docker + HuggingFace Spaces

## Development Workflow
1. **Each sprint day:** One major component gets built
2. **Each component:** TDD — write tests first, then implementation
3. **Daily validation:** Run full training loop (5 episodes) to ensure nothing broke
4. **Superpowers:** Use /plan before each sprint, /tdd for implementation, /review before committing

## File Organization Rules
- **Agents are stateless** — Episode holds all context
- **No global state** — Everything is passed as arguments
- **Config via environment** — LLM provider, model name, etc. all configurable
- **Tests live next to code** — `server/agents/sentinel.py` ↔ `tests/test_agents.py::test_sentinel_classify`

## Important URLs / Docs
- Product: /mnt/user-data/outputs/NEXUS_v2_Master_Product_Document.md
- Technical: /mnt/user-data/outputs/NEXUS_v2_Design_Document.md
- Roadmap: /mnt/user-data/outputs/NEXUS_v2_Product_Roadmap.md
- This sprint: /mnt/user-data/outputs/NEXUS_v2_IMPLEMENTATION_SPRINT.md

## Troubleshooting
- **RL training reward is 0.0:** Check grader.compute_episode_reward() — probably NaN somewhere
- **Agents crash on startup:** Verify Pydantic models match Agent.__init__ signatures
- **Codex calls timeout:** Reduce max_tokens in openai_client.chat.completions.create()
- **HF Space deployment fails:** Check Docker image size (<10GB), verify requirements.txt

---

## Superpowers Configuration
This project uses Superpowers for structured development. Skills are automatically available:

```
/brainstorm    — Before starting a new component
/plan          — Break sprint tasks into subtasks
/tdd           — Test-driven agent implementation
/review        — Code review before committing
/parallel      — Run multiple agents on independent modules
```

When you run `claude /plan`, it will output SPRINT_DAY_X.md with subtasks automatically.

---
```

### Also Create `.claudeignore`:

```
# Don't read these (large, irrelevant files)
.git/
.gitignore
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.coverage/
*.egg-info/
dist/
build/
venv/
env/
node_modules/
.env
.env.local
*.log
.DS_Store

# Lock files (not needed, they're heavy)
requirements.lock
package-lock.json
poetry.lock

# Build artifacts
*.whl
*.tar.gz

# IDE
.vscode/
.idea/
*.swp
*.swo

# Data files (too large)
*.csv
*.parquet
/data/
```

---

## SECTION 4: DAILY SPRINT SCHEDULE

### Day 1: Scaffold + Incident Catalogue (6-8 hours)

**Goal:** `/health` endpoint returns 200. No agents yet.

**What you'll do:**
1. Create FastAPI app skeleton (`server/app.py`)
2. Define Pydantic models (`server/models.py`)
3. Load all 8 incidents (`incidents/catalogue.py`)
4. Create empty agent stubs
5. Set up pytest + conftest
6. Deploy to HF Spaces (verify Docker builds)

**Claude Code task:**

```bash
cd nexus-v2
claude

# Inside claude session:
> /brainstorm Scaffold a FastAPI incident response system with 8 incident types

# Claude will ask clarifying questions, then:
> /plan Break this into 2-5 minute tasks

# You'll get SPRINT_DAY_1.md. Then:
> /tdd Implement FastAPI app with /health endpoint

# Accept diffs as they appear in VS Code
# Once done:
> /review Verify app structure and Pydantic models
```

**Success criteria:**
- `curl localhost:8000/health` returns `{"status": "ok"}`
- All 8 incidents load from `incidents/catalogue.py`
- `pytest tests/` runs with no failures (8/8 tests pass)

**Checkpoint (EOD):**
```bash
git add -A
git commit -m "Day 1: FastAPI scaffold + incident catalogue"
git push
```

---

### Day 2: SENTINEL Agent (6-8 hours)

**Goal:** SENTINEL classifies incidents. Tests pass. No RL yet.

**What you'll do:**
1. Define `Agent` protocol (for future LangChain wrapping)
2. Implement `SentinelAgent.classify()`
3. Test with all 8 incident types
4. Wire into orchestrator
5. Manual validation in `/guided` mode

**Claude Code task:**

```bash
claude

> /brainstorm Design the SENTINEL agent architecture for incident classification

> /plan Break SENTINEL implementation into TDD subtasks

> /tdd Implement SentinelAgent.classify() with 90% accuracy target

# Claude will write tests first:
# - test_sentinel_classify_payment_timeout()
# - test_sentinel_classify_db_pool()
# ... etc for all 8 types

# Then implementation in sentinel.py

# Then:
> /review SENTINEL agent code before merging
```

**Success criteria:**
- `tests/test_agents.py::test_sentinel_*` all pass (8/8)
- SENTINEL classification matches ground truth 90%+ of the time
- Each agent has clear `.classify()` signature
- Agent protocol supports future LangChain wrapping

**Daily training smoke test:**
```bash
python training/runner.py --episodes=5 --difficulty=easy
# Should run without crashing, show 5 episodes
```

**Checkpoint (EOD):**
```bash
git add -A
git commit -m "Day 2: SENTINEL agent with 90% accuracy"
git push
```

---

### Day 3: PRISM Agent (6-8 hours)

**Goal:** PRISM diagnoses root causes. Tests pass.

**What you'll do:**
1. Implement `PrismAgent.diagnose()`
2. TDD: write tests for each incident's root cause
3. Multi-step diagnosis (query logs → query metrics → form hypothesis)
4. Test with all 8 incidents
5. Wire into orchestrator

**Claude Code task:**

```bash
claude

> /tdd Implement PrismAgent.diagnose() with root cause accuracy target 75%

# Tests will include:
# - test_prism_diagnose_payment_timeout() → expects "Stripe API degradation"
# - test_prism_diagnose_db_pool() → expects "connection pool exhaustion"
# ... etc

> /review PRISM implementation before merging
```

**Success criteria:**
- `tests/test_agents.py::test_prism_*` all pass (8/8)
- Root cause diagnosis matches ground truth 75%+ of the time
- Multi-step diagnosis is testable (not one giant LLM call)

**Daily smoke test:**
```bash
python training/runner.py --episodes=5 --difficulty=easy
# SENTINEL + PRISM should both run, no crashes
```

**Checkpoint (EOD):**
```bash
git add -A
git commit -m "Day 3: PRISM agent with 75% diagnostic accuracy"
git push
```

---

### Day 4: FORGE Agent + OpenAI Codex (8-10 hours)

**Goal:** FORGE generates live executable runbooks using Codex. Critical day.

**What you'll do:**
1. Set up OpenAI SDK client (configurable via env vars)
2. Implement `ForgeAgent.generate_runbook()`
3. Codex prompt engineering (reference past incidents, system context)
4. Output parsing (extract bash/python/kubectl script)
5. Syntax validation
6. Test with all 8 incident types

**Claude Code task:**

```bash
claude

> /brainstorm Design the Codex integration for runbook generation

> /plan Break FORGE + Codex into TDD subtasks

> /tdd Implement ForgeAgent.generate_runbook() generating syntactically valid scripts

# Tests will include:
# - test_forge_generate_runbook_payment_timeout() → check bash syntax
# - test_forge_generate_runbook_db_pool() → check python syntax
# ... etc

# Key test: generated scripts must pass `bash -n` syntax check

> /review FORGE implementation and Codex prompts before merging
```

**Budget:**
- You have ~2000 OpenAI API calls available (at $5 per incident resolution)
- FORGE generates 1 runbook per episode
- Do NOT spend budget on this day — test with claude-3-sonnet (cheaper) first

**Success criteria:**
- `tests/test_agents.py::test_forge_*` all pass (8/8)
- Generated scripts pass syntax validation 95%+ of the time
- OpenAI API cost logged per call
- Fallback to Claude works (set `LLM_MODEL=claude-3-5-sonnet`)

**Daily smoke test:**
```bash
python training/runner.py --episodes=5 --difficulty=easy --lm-model=claude-3-5-sonnet
# All 4 agents (SENTINEL + PRISM + FORGE + GUARDIAN) should run
```

**Checkpoint (EOD):**
```bash
git add -A
git commit -m "Day 4: FORGE agent with Codex integration, syntax validation"
git push
```

---

### Day 5: GUARDIAN Agent + Reward Computation (8-10 hours)

**Goal:** GUARDIAN reviews runbooks. Episode reward computed deterministically.

**What you'll do:**
1. Implement `GuardianAgent.review()` (approve/reject/request modification)
2. Safety scoring (syntax check, no destructive patterns, no hardcoded secrets)
3. Implement `compute_episode_reward()` (5-dim reward)
4. Asymmetric grading (under-severity penalized 2x harder)
5. Full episode orchestration (SENTINEL → PRISM → FORGE → GUARDIAN → execute → verify → reward)

**Claude Code task:**

```bash
claude

> /tdd Implement GuardianAgent.review() with safety scoring

> /tdd Implement compute_episode_reward() with asymmetric grading

# Key tests:
# - test_guardian_approves_safe_runbook()
# - test_guardian_rejects_dangerous_runbook()
# - test_reward_is_deterministic() — same input always → same reward
# - test_reward_is_asymmetric() — false negative -1.0 > false positive -0.5

> /review Complete episode orchestration before merging
```

**Success criteria:**
- `tests/test_agents.py::test_guardian_*` all pass
- `tests/test_grader.py::test_reward_*` all pass
- Episode orchestration is tested end-to-end
- Same input always produces same reward (deterministic grader)

**Daily smoke test:**
```bash
python training/runner.py --episodes=5 --difficulty=easy
# Should complete 5 episodes, show reward for each
# Reward should be non-zero (not all 0.0 or NaN)
```

**Checkpoint (EOD):**
```bash
git add -A
git commit -m "Day 5: GUARDIAN agent + episode reward computation (deterministic)"
git push
```

---

### Day 6: GRPO Training Loop + Curriculum (8-10 hours)

**Goal:** RL training loop works. Agents improve over 30 episodes.

**What you'll do:**
1. Implement GRPO training loop (`training/grpo_loop.py`)
2. Policy networks for each agent (small MLPs)
3. Advantage computation (GAE)
4. Curriculum adapter (difficulty increases at 55% reward threshold)
5. Training loop: sample incident → run episode → compute advantage → update policies
6. Reward curve dashboard

**Claude Code task:**

```bash
claude

> /tdd Implement GRPO training loop with policy updates

> /tdd Implement curriculum learning (Easy → Hard, auto-advance)

# Tests will include:
# - test_grpo_update_increases_policy_likelihood_of_good_actions()
# - test_curriculum_advances_after_55_percent_threshold()
# - test_30_episode_training_shows_reward_improvement()

> /review Training loop before running full 30-episode train
```

**Budget:**
- This is the expensive day — 30 episodes × $5 per runbook = $150 in OpenAI costs
- Use claude-3-5-sonnet for Days 6-7 to save money (much cheaper, still competent)
- Monitor API spend: `echo "Cost so far: $(grep -c "openai_call" logs/training.log) calls"`

**Success criteria:**
- `pytest tests/test_training.py` all pass
- 30-episode training completes without crashing
- Reward curve shows upward trend (0.28 → 0.65+)
- Difficulty advances at least 1 level (Easy → Medium)
- Agents measurably improve (can show side-by-side comparisons)

**Daily training:**
```bash
python training/grpo_loop.py --episodes=30 --save-curve=./metrics.json
# Takes ~1 hour, outputs reward curve
```

**Checkpoint (EOD):**
```bash
git add -A
git commit -m "Day 6: GRPO training + curriculum, 30-ep train shows 76% improvement"
git push
```

---

### Day 7: Dashboard + Demo + Ship (10-12 hours)

**Goal:** Ship to HF Space with live demo. Judges impressed.

**What you'll do:**
1. Create metrics dashboard (reward curve, MTTR before/after, agent accuracy)
2. Pre-record a 90-second demo runthrough
3. Deploy to HF Spaces
4. Test live URL stability
5. Prepare pitch deck (1 slide)

**Claude Code task:**

```bash
claude

> /gsd Create metrics dashboard showing reward curve and before/after MTTR

> /gsd Create demo.py that runs a single live incident end-to-end

> /gsd Deploy to HF Spaces and verify live URL
```

**Demo script:**
```bash
# Load a pre-trained model (from Day 6)
python demo.py --incident=INC001 --model-checkpoint=./checkpoints/day6_30ep.pt

# Output:
# Incident: Payment service timeout
# SENTINEL: Classified as PaymentTimeout (P2)
# PRISM: Diagnosed as Stripe API degradation (confidence 0.92)
# FORGE: Generated bash script (syntax: OK)
# GUARDIAN: Approved (safety_score: 0.95)
# Execution: Success (exit_code: 0)
# Time: 3.2 seconds
# Reward: 0.68 (baseline was 0.28 at start of week)
```

**Success criteria:**
- Live URL loads in <3 seconds
- Dashboard shows reward curve (0.28 → 0.65)
- Demo incident resolves in <5 seconds
- No errors in console logs
- All 8 incidents can be demo'd (pick INC001, INC003, INC007 for variety)

**HF Space deployment:**
```bash
# Push to HF
huggingface-cli login
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/nexus-v2
git push hf main

# Verify live at: https://huggingface.co/spaces/YOUR_USERNAME/nexus-v2
```

**Final checkpoint:**
```bash
git add -A
git commit -m "Day 7: Live demo dashboard + HF Space deployment"
git push
git tag -a v1.0.0-hackathon -m "Hackathon submission"
git push --tags
```

**Pitch to judges (30 seconds):**
> "NEXUS is the first RL-trained incident response system. Watch: incident detected → 4 agents collaborate → Codex generates a bash script → it executes safely. Baseline MTTR is 74 minutes industry-wide. Our agents trained on 30 incidents now solve issues in 3 minutes. And they get faster every week. This is genuinely learning to solve production problems."

---

## SECTION 5: HOW TO RUN CLAUDE CODE FOR EACH DAY

### General Pattern

```bash
cd nexus-v2

# Each morning, create the day's sprint doc:
# (Claude Code will do this via /plan, or you can create manually)

# Start Claude Code session:
claude

# Inside Claude Code:
(claude) > /plan Read /mnt/user-data/outputs/NEXUS_v2_IMPLEMENTATION_SPRINT.md Day 4

# Claude generates SPRINT_DAY_4.md with detailed subtasks

# Then run Superpowers workflow:
(claude) > /tdd [component] implementation

# Accept diffs as they appear in VS Code
# Once component is done:
(claude) > /review [component] before merge

# Commit:
(claude) > exit
git add -A
git commit -m "Day 4: [component description]"

# Run daily smoke test:
python training/runner.py --episodes=5 --difficulty=easy
```

### Superpowers Slash Commands You'll Use

```
/plan NEXUS_v2 Day 3: PRISM agent implementation
→ Outputs SPRINT_DAY_3.md with 4-5 subtasks

/tdd Implement SentinelAgent.classify()
→ Claude writes tests first, then code

/review SENTINEL agent implementation
→ Claude Code reviews the code you just wrote

/parallel Run SENTINEL and PRISM in parallel
→ Spawns 2 subagents, one per task

/gsd Create metrics dashboard
→ "Get Stuff Done" mode — skip planning, just build it
```

---

## SECTION 6: CRITICAL DECISION POINTS

### Day 2 (End): Verify Agent Architecture Works

**Before moving to Day 3:**

```bash
# Test that agents are stateless and testable
pytest tests/test_agents.py -v

# If all pass: green light for Days 3-7
# If any fail: debug now (don't accumulate debt)
```

### Day 4 (Mid): Verify Codex Integration

**Critical decision:**
- **If OpenAI Codex API is unavailable:** Switch to Claude Sonnet immediately
  ```bash
  export LLM_MODEL=claude-3-5-sonnet
  export LLM_PROVIDER=anthropic
  # Run test
  python -m pytest tests/test_agents.py::test_forge_generate_runbook -v
  # If passes: continue with Claude, narrative shifts slightly but product works
  ```

- **If Codex works but is expensive:** Use Claude for Days 6-7, reserve budget for final demo

### Day 5 (End): Verify Reward is Deterministic

**Before moving to training:**

```bash
# Run same episode twice, expect identical reward
python training/runner.py --episodes=1 --difficulty=easy --seed=42 > run1.txt
python training/runner.py --episodes=1 --difficulty=easy --seed=42 > run2.txt
diff run1.txt run2.txt
# Should be identical. If not: debug grader.compute_episode_reward()
```

### Day 6 (End): Verify RL Training Actually Improves Agents

**Before Day 7:**

```bash
# Check that reward trend is upward
python training/grpo_loop.py --episodes=30 --plot=true
# Visually inspect: curve should go up, not flat or down
# If flat: RL loop has a bug, debug before Day 7 demo
```

---

## SECTION 7: FAILURE MODES & RECOVERY

### "RL training reward is always 0.0"

**Diagnosis:**
```python
# In grader.py, check this:
reward = compute_episode_reward(episode)
if reward.composite == 0.0:
    print(f"DEBUG: mttr={reward.mttr}, diagnosis={reward.diagnosis}, ...")
    print(f"DEBUG: episode.steps = {len(episode.steps)}")
    # Is episode empty? Are steps not being recorded?
```

**Fix:**
- Ensure every agent call records a step (see `episode.steps.append(...)`)
- Ensure grader doesn't have NaN in intermediate calculations
- Add assertions: `assert 0 <= reward.composite <= 1.0`

### "HF Space deployment fails with 'image too large'"

**Diagnosis:**
```bash
docker build -t nexus-v2 .
docker images | grep nexus-v2
# Check size — should be <10GB
```

**Fix:**
- Remove unnecessary dependencies from requirements.txt
- Use lighter image base: `python:3.11-slim` not `python:3.11`
- Don't include training data in Docker image

### "Demo works locally but fails on HF Space"

**Diagnosis:**
- HF Spaces have limited CPU/memory
- Pre-trained model checkpoint might be too large
- OpenAI API calls might timeout (HF has network restrictions)

**Fix:**
- Keep model checkpoint <100MB (use model quantization if needed)
- Cache Codex responses in demo.py (don't re-generate runbooks)
- Reduce max_tokens in OpenAI calls

### "Judges don't understand RL learning"

**Prevention:**
- Show 2 reward curves side-by-side: "untrained" vs "trained after 30 episodes"
- Explicitly say: "This is not ChatGPT answering questions. This is agents learning to solve problems."
- Have 1-min explainer video ready (recorded Day 6, narrated Day 7)

---

## SECTION 8: RESOURCE TRACKING

### Time Budget (56 hours total)

| Day | Component | Estimated time | Actual |
|-----|-----------|----------------|--------|
| 1 | Scaffold | 6-8 hrs | __ |
| 2 | SENTINEL | 6-8 hrs | __ |
| 3 | PRISM | 6-8 hrs | __ |
| 4 | FORGE | 8-10 hrs | __ |
| 5 | GUARDIAN + reward | 8-10 hrs | __ |
| 6 | GRPO + curriculum | 8-10 hrs | __ |
| 7 | Dashboard + ship | 10-12 hrs | __ |
| **Total** | | **56 hours** | __ |

**Goal:** Finish with 8-12 hours of buffer (for debugging, unexpected issues)

### Money Budget

| Item | Estimate | Actual |
|------|----------|--------|
| OpenAI Codex (Days 4-7) | $200 | __ |
| OpenAI GPT-4o (training, Day 6) | $150 | __ |
| Claude Sonnet fallback (Days 6-7) | $50 | __ |
| **Total** | **$400** | __ |

**Goal:** Stay under budget. Use cheaper models (Claude Sonnet) for Days 6-7 if needed.

---

## SECTION 9: VALIDATION CHECKLIST

Use this before each daily commit:

```bash
# Daily smoke test (run every morning)
python training/runner.py --episodes=5 --difficulty=easy

# Unit tests (run before commit)
pytest tests/ -v --tb=short

# Code style (run before commit)
python -m black server/ training/ --check
python -m isort server/ training/ --check

# Integration test (run every few days)
python training/grpo_loop.py --episodes=10  # Takes ~30 min

# Pre-demo validation (Day 7 only)
python demo.py --incident=INC001 --verify-deterministic=true
python demo.py --incident=INC007  # hardest incident
```

---

## SECTION 10: GIT WORKFLOW

### Daily commit pattern

```bash
# At end of each day:
git add -A
git commit -m "Day X: [Component] — [What works now]"
git push origin main

# At end of each phase (Days 3, 5, 7):
git tag -a vX.Y.Z -m "[Phase description]"
git push origin --tags
```

### Rewind feature (if you need to backtrack)

```bash
# If a day goes wrong and you want to revert:
git revert HEAD~3  # Revert last 3 commits
# OR
git reset --hard HEAD~3  # Throw away last 3 commits
```

---

## SECTION 11: COMMUNICATION DURING HACKATHON

### Daily standup (if with mentors)

```
"Good morning! Here's where we are:

✅ Yesterday: [Component] working, [X] tests passing
🔄 Today: Building [Component], goal is [Y] tests passing
🚨 Blockers: [If any]
📊 Metrics: Reward curve [status], MTTR [status]
"
```

### If you get stuck

```
1. Check the docs: /mnt/user-data/outputs/NEXUS_v2_Design_Document.md Section 5
2. Run Claude Code with /gsd to debug quickly
3. Check git history: git log --oneline (see what changed when)
4. Revert to last good state if needed: git reset --hard [commit-hash]
```

---

## FINAL: THE COMMANDS YOU'LL RUN (Copy-Paste Ready)

### First time setup (one-time, 5 minutes)

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code@latest
claude auth

# Create project
mkdir nexus-v2 && cd nexus-v2
git init

# Create CLAUDE.md (copy from Section 3 above)
cat > CLAUDE.md << 'EOF'
[...paste CLAUDE.md content...]
EOF

# Create .claudeignore (copy from above)
cat > .claudeignore << 'EOF'
[...paste .claudeignore content...]
EOF

# Create requirements.txt (you'll manage this with Claude Code)
touch requirements.txt

# Start first Claude Code session
claude
```

### Each day (Daily pattern)

```bash
cd nexus-v2

# Morning: Run smoke test
python training/runner.py --episodes=5 --difficulty=easy

# Read today's sprint doc
cat SPRINT_DAY_X.md  # (Claude Code creates this)

# Start Claude Code session
claude

# (Inside claude)
> /brainstorm [Today's component]
> /plan Break into subtasks
> /tdd Implement [component]
> /review [component] before merge
> exit

# Evening: Test and commit
pytest tests/ -v
git add -A && git commit -m "Day X: [What's done]"
git push

# Weekly: Tag progress
git tag -a v0.1.0-day-3 -m "SENTINEL agent complete"
git push --tags
```

---

**You're ready. Open VS Code, run `claude`, and start building.**

**See you on the other side with a working RL incident response system. 🚀**
