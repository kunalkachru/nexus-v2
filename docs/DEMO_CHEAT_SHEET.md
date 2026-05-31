# NEXUS v2 Demo Cheat Sheet

Current as of 2026-05-31.

This is the short live-demo reference.
For the full operating picture, use [docs/FINAL_SUBMISSION_GUIDE.md](FINAL_SUBMISSION_GUIDE.md).

## One-Line Pitch

NEXUS v2 is an autonomous incident response product where `SENTINEL`, `PRISM`, `FORGE`, and `GUARDIAN` work a live incident together, show their reasoning, and learn from training episodes over time.

## Public URL

- [https://kunalkachru23-nexus.hf.space](https://kunalkachru23-nexus.hf.space)

## Safest Demo Mode

- Default mode is deterministic
- No project OpenAI key is exposed
- Live reasoning is optional through a user-supplied key in `Incident Detail`

## Fastest Demo Flow

1. Open `/inputs`
2. Click `Load example logs`
3. Click `Submit raw logs`
4. Show the created incident page
5. Explain the 4-agent handoff
6. Click `Approve runbook`
7. Open `/training`
8. Show the reward curve and learning summary

## What To Say On Each Screen

### Inputs

- “This is the fastest path into the system.”
- “Raw logs become a structured incident.”

### Incident Detail

- “This is the core product surface.”
- “You can see `SENTINEL -> PRISM -> FORGE -> GUARDIAN` as a visible handoff.”
- “Guardian is the explicit safety gate.”
- “The app is deterministic by default, and a user can bring their own OpenAI key if they want live reasoning.”

### Training

- “The system tracks 30 episodes of learning.”
- “Reward moves from roughly `0.28` baseline to `0.65+` trained.”
- “This makes the product story more than just a static UI.”

## Expected Good Outcomes

- Queue incidents open populated incident detail pages
- Raw-log submission redirects into a populated `nxs_...` incident
- Guardian approval changes the execution state visibly
- Training shows the reward progression clearly

## If Something Looks Off

1. Refresh once
2. Re-open the page from `/queue` or `/inputs`
3. If local, run `./scripts/docker_fresh.sh`

## Local Commands

```bash
./scripts/docker_fresh.sh
python demo.py
pytest tests/ -v
npm run browser:verify
```
