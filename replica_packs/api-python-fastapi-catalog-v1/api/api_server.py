#!/usr/bin/env python3
"""
Minimal FastAPI server for catalog query regression replay.
Simulates a deploy regression where query optimization introduces a null-pointer bug.
"""
import os
import uvicorn
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(title="Catalog API")

# Feature flag to simulate the regression
ENABLE_QUERY_OPTIMIZATION = os.getenv("ENABLE_QUERY_OPTIMIZATION", "true").lower() == "true"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/products/search")
async def search_products(q: str = Query(..., min_length=1)):
    """
    Search for products by query.
    Simulates the regression: with optimization enabled, returns None instead of empty list.
    """
    if ENABLE_QUERY_OPTIMIZATION:
        # Simulated regression: query optimization has a null-pointer bug in filter logic
        try:
            # Simulate the null-pointer error by attempting to filter None
            result = _apply_optimized_filter(q)
            if result is None:
                # Return 500 to simulate the regression
                raise HTTPException(status_code=500, detail="Query filter returned invalid state")
            return {"products": result}
        except Exception as e:
            return {"error": str(e), "status": 500}
    else:
        # Without optimization: returns properly formed response
        return {"products": [{"id": 1, "name": "Test Product"}]}


def _apply_optimized_filter(query: str):
    """
    Simulated optimized filter that has a null-pointer bug.
    Returns None instead of an empty list in certain conditions.
    """
    # The regression: filter returns None instead of []
    if query and len(query) > 0:
        # This would normally filter products, but it has a bug
        return None  # BUG: should return [] or [matching products]
    return []


@app.post("/api/mitigation/disable-query-optimization")
async def disable_optimization():
    """Endpoint to disable the query optimization (simulates rollback effect)."""
    global ENABLE_QUERY_OPTIMIZATION
    ENABLE_QUERY_OPTIMIZATION = False
    return {"status": "disabled", "optimization_enabled": ENABLE_QUERY_OPTIMIZATION}


@app.post("/api/mitigation/apply-null-check-hotfix")
async def apply_hotfix():
    """Endpoint to apply the null-check hotfix."""
    # In a real scenario, this would apply a code fix
    # For simulation purposes, we just return success
    return {"status": "hotfix_applied", "safe": True}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
