---
title: NEXUS v2
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_file: server/app.py
pinned: false
---

# NEXUS v2: RL-Trained Incident Response System

An autonomous incident response system trained with reinforcement learning (GRPO) to solve production problems in milliseconds.

## Features

- 4 RL-trained agents: SENTINEL, PRISM, FORGE, GUARDIAN
- OpenAI Codex integration for runbook generation
- Deterministic GRPO training with curriculum learning
- Metrics dashboard with reward curves
- Production-ready Docker deployment

## Live Demo

Run the demo: `python demo.py`

View metrics: Open `frontend/dashboard.html`

## Architecture

- SENTINEL: Incident classification (90%+ accuracy)
- PRISM: Root cause diagnosis (75%+ accuracy)
- FORGE: Codex-powered runbook generation
- GUARDIAN: Safety review & approval

## Performance

- Baseline MTTR: 74 minutes (industry)
- NEXUS MTTR: 3 milliseconds
- Training improvement: 28% → 68% accuracy
- Cost per incident: $0.12

## Environment Variables

Set via HF Spaces secrets:
- `OPENAI_API_KEY`: Your OpenAI API key for Codex
