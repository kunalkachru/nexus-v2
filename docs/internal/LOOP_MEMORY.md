# NEXUS Loop Memory Contract

This file exists to improve loop discipline, not to let the agent invent product strategy.

Current verified rules:

1. any packaged-app runtime claim must be verified through the Docker app on `:7860`
2. scaffold-only evidence must stay labeled as scaffold-only
3. seeded and live incident paths must stay semantically aligned
4. do not mark a backlog item done until its listed test gates pass
5. update control docs when a backlog is fully closed
