#!/bin/bash
# Start the full stack with native $search support via mongot
# Usage: ./docker/search/start-search.sh

set -e

echo "=== Starting Agentic Search with native \$search support ==="
echo ""
echo "This starts 4 containers (+ 1 init that exits):"
echo "  1. setup-generator (creates auth files, then exits)"
echo "  2. mongodb-search (MongoDB Community Server 8.0.4 with mongot config + user init)"
echo "  3. mongot (Lucene search engine)"
echo "  4. backend (FastAPI)"
echo "  5. frontend (Next.js)"
echo ""
echo "Note: User creation (mongotUser + backendUser) runs inside mongodb-search"
echo "on first startup via /docker-entrypoint-initdb.d/init-mongod.sh"
echo ""

# Ensure docker/search scripts are executable
chmod +x docker/search/setup-generator.sh docker/search/init-mongod.sh

# Run with search profile + override
docker compose \
  -f docker-compose.yml \
  -f docker-compose.search.override.yml \
  --profile search \
  up --build

echo ""
echo "=== Stack is running ==="
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  MongoDB:  localhost:27018 (search-enabled)"
echo "  mongot health: http://localhost:8080/health"
echo "  mongot metrics: http://localhost:9946"
