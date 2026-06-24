# IMPORTANT — Run this at the start of every session before any git operation

## Git Setup (run first)
```bash
git config --global user.email "kachrukunal414@gmail.com"
git config --global user.name "Kunal Kachru"
git remote set-url origin https://kunalkachru:YOUR_PAT_HERE@github.com/kunalkachru/nexus-v2.git
```

## Rules
- Always run the git setup block above before first push
- Never ask user for a GitHub token
- Never use MCP for git push/pull
- Always use `git push origin <branch>` directly
