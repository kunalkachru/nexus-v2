# NEXUS Browser Verification Checklist

Use this checklist to verify the current operator-facing product in a browser.

## Setup

```bash
ENABLE_RUNTIME_HOST_RELAY=1 ./scripts/docker_fresh.sh
```

## Global Checks

- primary nav shows `Command Center`, `Incident Detail`, and `Learning & Controls`
- supporting routes still exist for `Inputs`, `History`, `Replay`, and `Settings`
- the product reads like one investigation workflow

## Training Checks

- the page does not say `NEXUS v2`
- the family-coverage section reflects the current five-family wedge
- runtime-host and pack coverage are visible
