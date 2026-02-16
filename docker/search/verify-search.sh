#!/bin/bash
# Verify the search stack is working correctly
# Run after docker/search/start-search.sh

set -e
PASS=0
FAIL=0

check() {
    local desc="$1"
    local cmd="$2"
    if eval "$cmd" > /dev/null 2>&1; then
        echo "  PASS: $desc"
        ((PASS++))
    else
        echo "  FAIL: $desc"
        ((FAIL++))
    fi
}

echo "=== Verifying Search Stack ==="

# Container health
check "mongodb-search container healthy" \
  "docker inspect --format='{{.State.Health.Status}}' agentic-search-mongodb-search | grep -q healthy"

check "mongot container healthy" \
  "docker inspect --format='{{.State.Health.Status}}' agentic-search-mongot | grep -q healthy"

check "backend container healthy" \
  "docker inspect --format='{{.State.Health.Status}}' agentic-search-backend | grep -q healthy"

# mongot health endpoint
check "mongot health endpoint responds" \
  "curl -sf http://localhost:8080/health"

# Backend health
check "backend health endpoint responds" \
  "curl -sf http://localhost:8000/health"

# Search backend detection
check "backend detected atlas search" \
  "docker logs agentic-search-backend 2>&1 | grep -q 'search_backend_initialized.*backend.*atlas'"

# Search index creation
check "nodes_fulltext search index created" \
  "docker logs agentic-search-backend 2>&1 | grep -q 'search_index'"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
