# mongot Integration Plan: Native $search on Community Edition

> **For Claude:** REQUIRED: Follow this plan task-by-task using TDD.
> **Research:** See `docs/research/2026-02-16-mongot-community-search-research.md` for full reference analysis.

**Goal:** Add native MongoDB `$search` support to the Docker stack by integrating mongot (Community Search), so `detect_search_backend()` finds `nodes_fulltext` and uses the Atlas Search path instead of `$text` fallback.

**Architecture:** Two-container model -- `mongodb/mongodb-community-server:latest` (mongod) + `mongodb/mongodb-community-search:latest` (mongot) communicating via gRPC on port 27028. A setup-generator init container creates keyfile + passwordFile before services start. mongod is configured via `mongod.conf` with `searchIndexManagementHostAndPort` and `mongotHost`. The backend programmatically creates the `nodes_fulltext` search index at startup.

**Tech Stack:** Docker Compose profiles, MongoDB Community Server, mongot, pymongo `createSearchIndex()`, bash init scripts

**Prerequisites:**
- Existing docker-compose.yml with 3 services (mongodb, backend, frontend) -- all healthy
- 453 backend tests + 300 frontend tests passing
- `detect_search_backend()` and `$text` fallback already working
- `build_search_pipeline()` already referencing `index: "nodes_fulltext"`

---

## Dev Journal (User Transparency)

### Planning Process
- Loaded full project memory (activeContext, patterns, progress) -- understood existing Docker setup, search backend detection, and test infrastructure.
- Read research file (`docs/research/2026-02-16-mongot-community-search-research.md`) based on reference repo `JohnGUnderwood/mdb-community-search`.
- Analyzed 4 key source files: `docker-compose.yml`, `src/retrieval/atlas_search.py`, `src/db/indexes.py`, `src/api/server.py`.
- Verified existing `detect_search_backend()` pattern, `build_search_pipeline()` references `nodes_fulltext`, and `init_search_backend()` runs at startup in lifespan.
- Consulted MongoDB skills: schema-design (no schema changes needed), query-and-index-optimize (search index creation via `createSearchIndex()`), ai (confirms `$search` syntax), transactions-consistency (auth/keyfile patterns for replica sets).

### Key Architectural Decisions
- **Docker Compose profiles** (`--profile search`) instead of separate compose file -- backward compatible, single file, existing `docker compose up` still works without mongot.
- **Init container** (setup-generator) creates keyfile + passwordFile on a shared volume -- follows reference repo pattern exactly.
- **mongod.conf mounted as volume** rather than baked into image -- keeps the community-server image stock.
- **Search index creation in Python** (`ensure_search_index()` in `src/db/indexes.py`) rather than init script -- integrates with existing lifespan startup, idempotent, uses existing `nodes_col()`.
- **Switch Docker image** from `mongo:7.0` to `mongodb/mongodb-community-server:8.0.4` only when search profile is active -- the default (no profile) keeps `mongo:7.0` for simplicity. Actually: we need to use a single mongodb service definition. Decision: use profile to select which mongodb variant runs.

### Alternatives Rejected
- **Separate docker-compose.search.yml** -- rejected because Docker Compose `-f` stacking is error-prone and requires users to remember file order. Profiles are cleaner.
- **Bake mongod.conf into custom image** -- rejected because it couples configuration to build, makes iteration slow, and the stock image accepts config via volume mount.
- **Create search index via mongosh init script** -- rejected because it would duplicate the Python detection logic and run outside the application lifecycle.
- **Always use community-server image** -- rejected because `mongo:7.0` is simpler for users who do not need search, and many existing tutorials reference it.

### Assumptions Made
- `mongodb/mongodb-community-server:8.0.4` image supports `searchIndexManagementHostAndPort` and `mongotHost` setParameters.
- `mongodb/mongodb-community-search:latest` mongot image works with gRPC on port 27028 out of the box.
- `pymongo` `collection.create_search_index()` works against Community Edition with mongot (confirmed by reference repo using `mongosh`).
- Keyfile auth with `searchCoordinator` role is sufficient for mongot-to-mongod communication.
- The existing `detect_search_backend()` will detect the search index once mongot syncs and the index is created.

### Your Input Needed
- **Image version pinning**: Plan uses `mongodb/mongodb-community-server:8.0.4` -- confirm this is the version you want, or should it be `:latest`?
- **Default profile**: Should `docker compose up` (no profile) still use `mongo:7.0`, or should it switch to `mongodb/mongodb-community-server:8.0.4` even without mongot?
- **Auth in non-search mode**: The search profile enables keyfile auth. The default profile has no auth. Is this acceptable?

### What's Next
Once you approve this plan, BUILD workflow starts. Component-builder follows phases defined here. You can adjust plan before we start building.

---

## Relevant Codebase Files

### Patterns to Follow
- `docker-compose.yml` (lines 1-73) -- existing 3-service Docker Compose with healthcheck, depends_on, volumes, networks
- `src/retrieval/atlas_search.py` (lines 134-159) -- `detect_search_backend()` and `init_search_backend()` pattern
- `src/db/indexes.py` (lines 130-158) -- `ensure_text_index()` idempotent index creation pattern
- `src/api/server.py` (lines 39-65) -- lifespan startup: ensure_indexes, ensure_text_index, init_search_backend
- `src/db/collections.py` (lines 1-35) -- `nodes_col()` accessor pattern
- `src/config.py` (lines 1-51) -- Settings via pydantic-settings, environment variables

### Configuration Files
- `docker-compose.yml` -- will be modified (add profile-gated services)
- `Dockerfile` -- backend Dockerfile, no changes needed
- `.env` (optional) -- may need SEARCH_PROFILE or similar env var

### Related Documentation
- `docs/research/2026-02-16-mongot-community-search-research.md` -- full reference repo analysis
- `README.md` -- may need section on running with search

### Test Files
- `tests/test_text_search_fallback.py` (lines 1-189) -- existing search detection and fallback tests

---

## Phase 1: Docker Infrastructure (Setup Files + Compose Profile)

> **Exit Criteria:** `docker compose --profile search up` starts 5 containers (setup-generator, mongodb-search, mongot, backend, frontend) with mongodb-search healthy and mongot connected via gRPC. `docker compose up` (no profile) still starts the original 3 containers unchanged.

### Task 1: Create setup-generator init script

**Files:**
- Create: `docker/search/setup-generator.sh`

**Step 1: Create the docker/search directory**

```bash
mkdir -p docker/search
```

**Step 2: Write the setup-generator script**

This script generates a keyfile for replica set auth and a passwordFile for mongot authentication.

```bash
#!/bin/bash
set -e

KEYFILE_PATH="/auth/keyfile"
PASSWORD_FILE_PATH="/auth/passwordFile"
MONGOT_PASSWORD="mongotSearchPass123"

echo "=== Setup Generator: Creating auth files ==="

# Generate keyfile for replica set authentication (base64, 756 bytes)
if [ ! -f "$KEYFILE_PATH" ]; then
    openssl rand -base64 756 > "$KEYFILE_PATH"
    chmod 400 "$KEYFILE_PATH"
    echo "Created keyfile at $KEYFILE_PATH"
else
    echo "Keyfile already exists at $KEYFILE_PATH"
fi

# Generate passwordFile for mongot authentication
if [ ! -f "$PASSWORD_FILE_PATH" ]; then
    echo -n "$MONGOT_PASSWORD" > "$PASSWORD_FILE_PATH"
    chmod 400 "$PASSWORD_FILE_PATH"
    echo "Created passwordFile at $PASSWORD_FILE_PATH"
else
    echo "passwordFile already exists at $PASSWORD_FILE_PATH"
fi

echo "=== Setup Generator: Complete ==="
```

**Step 3: Verify the script is executable**

Run: `chmod +x docker/search/setup-generator.sh && file docker/search/setup-generator.sh`
Expected: "Bourne-Again shell script" or similar

---

### Task 2: Create mongod.conf for search-enabled mode

**Files:**
- Create: `docker/search/mongod.conf`

**Step 1: Write mongod.conf**

This configuration enables mongot integration via gRPC. The `mongot` hostname resolves within the Docker network.

```yaml
# mongod.conf for Community Search (mongot integration)
# Mounted when running with --profile search

replication:
  replSetName: "rs0"

net:
  bindIpAll: true
  port: 27017

security:
  authorization: enabled
  keyFile: /auth/keyfile

setParameter:
  searchIndexManagementHostAndPort: "mongot:27028"
  mongotHost: "mongot:27028"
  skipAuthenticationToSearchIndexManagementServer: false
  useGrpcForSearch: true
```

---

### Task 3: Create mongot.conf

**Files:**
- Create: `docker/search/mongot.conf`

**Step 1: Write mongot.conf**

```yaml
# mongot configuration for Community Search
# Sync from mongod via gRPC, expose health + metrics

syncSource:
  replicaSet:
    hostAndPort: "mongodb-search:27017"
    username: "mongotUser"
    passwordFile: "/auth/passwordFile"
    authSource: "admin"
    tls: false

storage:
  dataPath: "/data/mongot"

server:
  grpc:
    address: "mongot:27028"

metrics:
  enabled: true
  address: "mongot:9946"

healthCheck:
  address: "mongot:8080"

logging:
  verbosity: INFO
```

---

### Task 4: Create mongod init script (create mongotUser)

**Files:**
- Create: `docker/search/init-mongod.sh`

**Step 1: Write the init script**

This script runs after mongod is healthy. It initializes the replica set and creates the `mongotUser` with `searchCoordinator` role.

```bash
#!/bin/bash
set -e

MONGOT_PASSWORD="mongotSearchPass123"

echo "=== Init MongoDB: Configuring search user ==="

# Wait for mongod to be ready (primary)
until mongosh --quiet --eval "rs.status().ok" 2>/dev/null; do
    echo "Waiting for mongod primary..."
    sleep 2
done

# Create mongotUser with searchCoordinator role (idempotent)
mongosh --quiet --eval "
  try {
    db.getSiblingDB('admin').createUser({
      user: 'mongotUser',
      pwd: '${MONGOT_PASSWORD}',
      roles: [{ role: 'searchCoordinator', db: 'admin' }]
    });
    print('Created mongotUser');
  } catch (e) {
    if (e.codeName === 'DuplicateKey' || e.code === 51003) {
      print('mongotUser already exists');
    } else {
      throw e;
    }
  }
"

echo "=== Init MongoDB: Complete ==="
```

**Step 2: Make executable**

Run: `chmod +x docker/search/init-mongod.sh`

---

### Task 5: Update docker-compose.yml with search profile

**Files:**
- Modify: `docker-compose.yml`

**Step 1: Add profile-gated services**

[CHECKPOINT] The existing `mongodb` service (using `mongo:7.0`) stays as-is for non-search use. A new `mongodb-search` service is added under `profiles: [search]`. The `backend` and `frontend` services need conditional `depends_on` -- this is the tricky part.

**Approach:** Add the search-profile services alongside existing ones. When `--profile search` is used, users should set `MONGODB_URI` to point to `mongodb-search` instead of `mongodb`. The `backend` service environment variable `MONGODB_URI` must be overridden.

**Updated docker-compose.yml structure:**

```yaml
services:
  # === DEFAULT MODE (no profile) ===
  # MongoDB 7.0+ with replica set (simple, no auth, no search)
  mongodb:
    image: mongo:7.0
    container_name: agentic-search-mongodb
    command: ["--replSet", "rs0", "--bind_ip_all"]
    ports:
      - "127.0.0.1:27017:27017"
    volumes:
      - mongodb_data:/data/db
    healthcheck:
      test: >
        mongosh --eval "
          try {
            rs.status().ok
          } catch(e) {
            rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'mongodb:27017'}]});
            1;
          }
        "
      interval: 10s
      timeout: 10s
      retries: 5
      start_period: 10s
    networks:
      - app-network

  # === SEARCH PROFILE ===
  # Phase 1: Generate keyfile + passwordFile
  setup-generator:
    image: alpine:3.19
    profiles: [search]
    container_name: agentic-search-setup
    command: ["/bin/sh", "/scripts/setup-generator.sh"]
    volumes:
      - search_auth:/auth
      - ./docker/search/setup-generator.sh:/scripts/setup-generator.sh:ro
    networks:
      - app-network

  # Phase 2: MongoDB Community Server with mongot support
  mongodb-search:
    image: mongodb/mongodb-community-server:8.0.4-ubi9
    profiles: [search]
    container_name: agentic-search-mongodb-search
    command: ["--config", "/etc/mongod.conf"]
    ports:
      - "127.0.0.1:27018:27017"   # Port 27018 to avoid conflict with default mongodb
    volumes:
      - mongodb_search_data:/data/db
      - search_auth:/auth:ro
      - ./docker/search/mongod.conf:/etc/mongod.conf:ro
    healthcheck:
      test: >
        mongosh --eval "
          try {
            rs.status().ok
          } catch(e) {
            rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'mongodb-search:27017'}]});
            1;
          }
        "
      interval: 10s
      timeout: 10s
      retries: 10
      start_period: 15s
    depends_on:
      setup-generator:
        condition: service_completed_successfully
    networks:
      - app-network

  # Phase 2: mongot (Lucene search engine)
  mongot:
    image: mongodb/mongodb-community-search:latest
    profiles: [search]
    container_name: agentic-search-mongot
    command: ["--config", "/etc/mongot.conf"]
    volumes:
      - mongot_data:/data/mongot
      - search_auth:/auth:ro
      - ./docker/search/mongot.conf:/etc/mongot.conf:ro
    ports:
      - "127.0.0.1:8080:8080"    # Health check
      - "127.0.0.1:9946:9946"    # Metrics
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
    depends_on:
      mongodb-search:
        condition: service_healthy
    networks:
      - app-network

  # Phase 3: Init container -- create mongotUser
  mongodb-search-init:
    image: mongodb/mongodb-community-server:8.0.4-ubi9
    profiles: [search]
    container_name: agentic-search-init
    entrypoint: ["/bin/bash", "/scripts/init-mongod.sh"]
    volumes:
      - search_auth:/auth:ro
      - ./docker/search/init-mongod.sh:/scripts/init-mongod.sh:ro
    depends_on:
      mongodb-search:
        condition: service_healthy
    networks:
      - app-network

  # FastAPI backend (port 8000)
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: agentic-search-backend
    ports:
      - "8000:8000"
    env_file:
      - path: .env
        required: false
    environment:
      - MONGODB_URI=mongodb://mongodb:27017/?replicaSet=rs0
      - MONGODB_DATABASE=agentic_search
      - PORT=8000
      - CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
    depends_on:
      mongodb:
        condition: service_healthy
    networks:
      - app-network

  # Next.js frontend (port 3000)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_URL: http://localhost:8000
    container_name: agentic-search-frontend
    ports:
      - "3000:3000"
    environment:
      - HOSTNAME=0.0.0.0
    depends_on:
      - backend
    networks:
      - app-network

volumes:
  mongodb_data:
  mongodb_search_data:
  mongot_data:
  search_auth:

networks:
  app-network:
    driver: bridge
```

**Key design notes:**
- `setup-generator` runs first (Alpine image, just creates files), completes and exits.
- `mongodb-search` depends on setup-generator completing.
- `mongot` depends on mongodb-search being healthy.
- `mongodb-search-init` depends on mongodb-search being healthy (creates mongotUser).
- Default `backend` still depends on `mongodb` (non-search mode).
- For search mode, user overrides `MONGODB_URI` via `.env` or command line.

**Step 2: Verify default mode still works**

Run: `docker compose config --quiet`
Expected: exit 0

**Step 3: Verify search profile parses**

Run: `docker compose --profile search config --quiet`
Expected: exit 0

**Step 4: Commit**

```bash
git add docker/search/ docker-compose.yml
git commit -m "feat: add mongot Docker infrastructure with search profile"
```

---

### Task 6: Create docker-compose.search.override.yml for backend overrides

**Files:**
- Create: `docker-compose.search.override.yml`

[CHECKPOINT] The backend service in the main compose file depends on `mongodb` (non-search). When using the search profile, the backend needs to connect to `mongodb-search` instead. Docker Compose does not support conditional `depends_on` per profile. The cleanest solution is a separate override file.

**Step 1: Write the override file**

```yaml
# Override for search profile: backend connects to mongodb-search instead of mongodb
# Usage: docker compose -f docker-compose.yml -f docker-compose.search.override.yml --profile search up

services:
  backend:
    environment:
      - MONGODB_URI=mongodb://mongodb-search:27017/?replicaSet=rs0
    depends_on:
      mongodb-search:
        condition: service_healthy
      mongot:
        condition: service_healthy
      mongodb-search-init:
        condition: service_completed_successfully
```

**Step 2: Verify combined config parses**

Run: `docker compose -f docker-compose.yml -f docker-compose.search.override.yml --profile search config --quiet`
Expected: exit 0

**Step 3: Commit**

```bash
git add docker-compose.search.override.yml
git commit -m "feat: add search override for backend to connect to mongodb-search"
```

---

## Phase 2: Search Index Creation (Python Code)

> **Exit Criteria:** `ensure_search_index()` function exists, creates `nodes_fulltext` search index programmatically, is idempotent, and is called during lifespan startup when `_search_backend` could be atlas. All existing tests still pass plus new tests for the function.

### Task 7: Write failing tests for ensure_search_index()

**Files:**
- Create or modify: `tests/test_search_index_creation.py`

**Step 1: Write the test file**

```python
"""Tests for search index creation via createSearchIndex().

Covers:
1. ensure_search_index() creates nodes_fulltext search index
2. ensure_search_index() is idempotent (index already exists)
3. ensure_search_index() handles errors gracefully (mongot not available)
4. ensure_search_index() defines correct field mappings
5. ensure_search_index() is called during init_search_backend()
"""

from unittest.mock import MagicMock, patch, call

import pytest
from pymongo.errors import OperationFailure


class TestEnsureSearchIndex:
    """Test search index creation for mongot integration."""

    def test_creates_nodes_fulltext_index(self):
        """ensure_search_index() calls createSearchIndex with correct name and definition."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            mock_col.return_value.create_search_index.return_value = "nodes_fulltext"
            result = ensure_search_index()
            assert "nodes_fulltext" in result

            # Verify createSearchIndex was called
            mock_col.return_value.create_search_index.assert_called_once()
            call_args = mock_col.return_value.create_search_index.call_args

            # Verify index model has correct name
            index_model = call_args[0][0]
            assert index_model.name == "nodes_fulltext"

    def test_search_index_field_mappings(self):
        """ensure_search_index() defines mappings for title, summary, keywords, documentId, contentType."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            mock_col.return_value.create_search_index.return_value = "nodes_fulltext"
            ensure_search_index()

            call_args = mock_col.return_value.create_search_index.call_args
            index_model = call_args[0][0]
            definition = index_model.definition

            # Must have mappings
            assert "mappings" in definition
            mappings = definition["mappings"]

            # dynamic: false for explicit field control
            assert mappings.get("dynamic") is False

            # Must define fields for title, summary, keywords
            fields = mappings["fields"]
            assert "title" in fields
            assert "summary" in fields
            assert "keywords" in fields
            assert "documentId" in fields
            assert "contentType" in fields

    def test_idempotent_index_exists(self):
        """ensure_search_index() handles 'index already exists' gracefully."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            # Simulate duplicate index error
            mock_col.return_value.create_search_index.side_effect = OperationFailure(
                "Duplicate Index", code=68
            )
            # Should not raise
            result = ensure_search_index()
            assert isinstance(result, list)

    def test_handles_mongot_not_available(self):
        """ensure_search_index() returns empty list when mongot is not running."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            mock_col.return_value.create_search_index.side_effect = Exception(
                "mongot not available"
            )
            result = ensure_search_index()
            assert result == []

    def test_list_search_indexes_check(self):
        """ensure_search_index() checks if index exists before creating."""
        from src.db.indexes import ensure_search_index

        with patch("src.db.indexes.nodes_col") as mock_col:
            # Index already exists
            mock_col.return_value.list_search_indexes.return_value = [
                {"name": "nodes_fulltext"}
            ]
            result = ensure_search_index()
            # Should NOT call create_search_index
            mock_col.return_value.create_search_index.assert_not_called()
            assert "nodes_fulltext" in result
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo && python -m pytest tests/test_search_index_creation.py -v`
Expected: FAIL (ensure_search_index does not exist yet)

---

### Task 8: Implement ensure_search_index()

**Files:**
- Modify: `src/db/indexes.py` (add function after `ensure_text_index`)

**Step 1: Add imports at top of file**

Add `from pymongo.operations import SearchIndexModel` to the imports.

**Step 2: Implement the function**

Add after `ensure_text_index()`:

```python
def ensure_search_index() -> list[str]:
    """Create the nodes_fulltext search index for Atlas Search / mongot.

    Uses pymongo's create_search_index() to programmatically create a search
    index with explicit field mappings for title, summary, keywords, documentId,
    and contentType. This enables $search aggregation queries.

    The function is idempotent:
    - Checks if index already exists via list_search_indexes()
    - Handles 'duplicate index' errors gracefully
    - Returns empty list if mongot is not available (non-fatal)

    Returns:
        List of created/existing search index names.
    """
    created: list[str] = []
    n = nodes_col()
    index_name = "nodes_fulltext"

    try:
        # Check if index already exists
        existing = {idx["name"] for idx in n.list_search_indexes()}
        if index_name in existing:
            logger.info("search_index_already_exists", index_name=index_name)
            return [index_name]
    except Exception:
        # list_search_indexes not supported (no mongot) -- try creating anyway
        logger.debug("list_search_indexes_unavailable", exc_info=True)

    try:
        model = SearchIndexModel(
            name=index_name,
            definition={
                "mappings": {
                    "dynamic": False,
                    "fields": {
                        "title": [
                            {"type": "string", "analyzer": "lucene.standard"}
                        ],
                        "summary": [
                            {"type": "string", "analyzer": "lucene.standard"}
                        ],
                        "keywords": [
                            {"type": "string", "analyzer": "lucene.standard"}
                        ],
                        "documentId": [
                            {"type": "string", "analyzer": "lucene.keyword"}
                        ],
                        "contentType": [
                            {"type": "string", "analyzer": "lucene.keyword"}
                        ],
                    },
                }
            },
        )
        result = n.create_search_index(model)
        created.append(result)
        logger.info("search_index_created", index_name=result)
    except OperationFailure as exc:
        if exc.code == 68 or "Duplicate" in str(exc):
            logger.info("search_index_duplicate", index_name=index_name, error=str(exc))
            created.append(index_name)
        else:
            logger.warning("search_index_creation_failed", error=str(exc), exc_info=True)
    except Exception:
        # mongot not available or search indexes not supported -- non-fatal
        logger.info("search_index_creation_skipped", exc_info=True)

    return created
```

**Step 3: Run tests to verify they pass**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo && python -m pytest tests/test_search_index_creation.py -v`
Expected: PASS (5/5)

**Step 4: Run all existing tests to verify no regressions**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo && python -m pytest tests/ -x -q`
Expected: 453+ passed, 11 skipped

**Step 5: Commit**

```bash
git add src/db/indexes.py tests/test_search_index_creation.py
git commit -m "feat: add ensure_search_index() for programmatic nodes_fulltext creation"
```

---

### Task 9: Wire ensure_search_index() into lifespan startup

**Files:**
- Modify: `src/api/server.py` (lines 29, 52-58)

**Step 1: Add import**

Update line 29:
```python
from src.db.indexes import ensure_indexes, ensure_text_index, ensure_search_index
```

**Step 2: Call ensure_search_index() in lifespan**

After the `ensure_text_index()` call (around line 56-57), add:

```python
        search_idx = ensure_search_index()
        logger.info("search_index_ensured", count=len(search_idx))
```

The updated lifespan block (lines 52-61) should look like:

```python
    # Create indexes (idempotent) and detect search backend
    try:
        idx_names = ensure_indexes()
        logger.info("indexes_ensured", count=len(idx_names))
        text_idx = ensure_text_index()
        logger.info("text_index_ensured", count=len(text_idx))
        search_idx = ensure_search_index()
        logger.info("search_index_ensured", count=len(search_idx))
    except Exception:
        logger.warning("index_creation_warning", exc_info=True)

    init_search_backend()
```

**Step 3: Run existing tests**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo && python -m pytest tests/ -x -q`
Expected: All tests still pass

**Step 4: Commit**

```bash
git add src/api/server.py
git commit -m "feat: call ensure_search_index() at startup before detect_search_backend()"
```

---

## Phase 3: Auth Integration + Connection String Update

> **Exit Criteria:** When running with search profile, the backend can authenticate to mongodb-search and mongot correctly. The `MONGODB_URI` in search mode includes replica set name. Authentication files are properly secured.

### Task 10: Update connection string handling for auth mode

**Files:**
- Modify: `src/config.py` (no changes needed -- MONGODB_URI is already configurable via env)
- Verify: `docker-compose.search.override.yml` sets correct MONGODB_URI

**Step 1: Verify MONGODB_URI in override**

The `docker-compose.search.override.yml` (from Task 6) sets:
```
MONGODB_URI=mongodb://mongodb-search:27017/?replicaSet=rs0
```

This connects without auth credentials because the backend itself does not need mongotUser credentials -- only mongot needs them. The backend connects as an unauthenticated client to the replica set (auth is between mongot and mongod only for the search coordinator role).

**However**, if `security.authorization: enabled` is set in `mongod.conf`, ALL connections need auth. This is a critical issue.

[CHECKPOINT] Two options:
1. **Remove `security.authorization: enabled`** from mongod.conf -- only use keyFile for internal replica set auth, not client auth. This means mongot authenticates via keyFile but the backend connects without auth. This works because `keyFile` implies `authorization: enabled` in MongoDB.
2. **Add a backend user** to mongod with readWrite role, and include credentials in MONGODB_URI.

**Decision: Option 2 (add backend user)** -- more secure, follows best practice. The init script creates both mongotUser and a backendUser.

**Step 2: Update init-mongod.sh to create backendUser**

Add to `docker/search/init-mongod.sh`:

```bash
# Create backendUser with readWrite on agentic_search database (idempotent)
mongosh --quiet --eval "
  try {
    db.getSiblingDB('admin').createUser({
      user: 'backendUser',
      pwd: 'backendPass123',
      roles: [
        { role: 'readWrite', db: 'agentic_search' },
        { role: 'clusterMonitor', db: 'admin' }
      ]
    });
    print('Created backendUser');
  } catch (e) {
    if (e.codeName === 'DuplicateKey' || e.code === 51003) {
      print('backendUser already exists');
    } else {
      throw e;
    }
  }
"
```

**Step 3: Update docker-compose.search.override.yml MONGODB_URI**

```yaml
services:
  backend:
    environment:
      - MONGODB_URI=mongodb://backendUser:backendPass123@mongodb-search:27017/agentic_search?replicaSet=rs0&authSource=admin
    depends_on:
      mongodb-search:
        condition: service_healthy
      mongot:
        condition: service_healthy
      mongodb-search-init:
        condition: service_completed_successfully
```

**Step 4: Run compose config validation**

Run: `docker compose -f docker-compose.yml -f docker-compose.search.override.yml --profile search config --quiet`
Expected: exit 0

**Step 5: Commit**

```bash
git add docker/search/init-mongod.sh docker-compose.search.override.yml
git commit -m "feat: add backendUser auth for search profile MongoDB connection"
```

---

### Task 11: Update mongod.conf -- remove explicit security.authorization

**Files:**
- Modify: `docker/search/mongod.conf`

**Step 1: Clarify auth behavior**

MongoDB documentation states: "If you enable `security.keyFile`, authentication is automatically enabled." So we do NOT need `security.authorization: enabled` separately. The `keyFile` setting enables both internal (replica set) and external (client) authentication.

The mongod.conf from Task 2 already has:
```yaml
security:
  authorization: enabled
  keyFile: /auth/keyfile
```

This is correct as-is. The `keyFile` enables internal auth, and `authorization: enabled` enables client auth. Both are needed.

**No changes needed to mongod.conf.** The init script (Task 10) creates backendUser with credentials that go in MONGODB_URI.

---

## Phase 4: Integration Testing + Documentation

> **Exit Criteria:** A documented procedure for running with search profile. Manual verification that `detect_search_backend()` returns "atlas" when mongot is running and search index is created.

### Task 12: Create helper script for search mode

**Files:**
- Create: `docker/search/start-search.sh`

**Step 1: Write the helper script**

```bash
#!/bin/bash
# Start the full stack with native $search support via mongot
# Usage: ./docker/search/start-search.sh

set -e

echo "=== Starting Agentic Search with native \$search support ==="
echo ""
echo "This starts 5 containers:"
echo "  1. setup-generator (creates auth files, then exits)"
echo "  2. mongodb-search (MongoDB Community Server 8.0.4 with mongot config)"
echo "  3. mongot (Lucene search engine)"
echo "  4. backend (FastAPI)"
echo "  5. frontend (Next.js)"
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
```

**Step 2: Make executable**

Run: `chmod +x docker/search/start-search.sh`

**Step 3: Commit**

```bash
git add docker/search/start-search.sh
git commit -m "feat: add start-search.sh helper script for mongot stack"
```

---

### Task 13: Add verification commands to validate search integration

**Files:**
- Create: `docker/search/verify-search.sh`

**Step 1: Write the verification script**

```bash
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
```

**Step 2: Make executable and commit**

```bash
chmod +x docker/search/verify-search.sh
git add docker/search/verify-search.sh
git commit -m "feat: add verify-search.sh for search stack validation"
```

---

### Task 14: Update .gitignore for auth files

**Files:**
- Modify: `.gitignore` (if it exists)

**Step 1: Ensure auth files are never committed**

Add to `.gitignore`:
```
# Search auth files (generated by setup-generator)
docker/search/keyfile
docker/search/passwordFile
```

Note: These files are only ever on Docker volumes (`search_auth`), not on disk. But add to `.gitignore` as a safety measure.

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore search auth files"
```

---

### Task 15: Run full test suite -- verify no regressions

**Files:** None (verification only)

**Step 1: Run backend tests**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo && python -m pytest tests/ -x -q`
Expected: 453+ passed (plus new search index tests), 11 skipped

**Step 2: Run frontend tests**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo/frontend && npx vitest run`
Expected: 300/300 passed

**Step 3: TypeScript check**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo/frontend && npx tsc --noEmit`
Expected: exit 0

**Step 4: Docker Compose config validation (default mode)**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo && docker compose config --quiet`
Expected: exit 0

**Step 5: Docker Compose config validation (search mode)**

Run: `cd /Users/rom.iluz/Dev/agentic-search-mongo && docker compose -f docker-compose.yml -f docker-compose.search.override.yml --profile search config --quiet`
Expected: exit 0

---

## Risks

| Risk | P | I | Score | Mitigation |
|------|---|---|-------|------------|
| mongot image incompatible with our MongoDB version | 2 | 5 | 10 | Pin `mongodb-community-server:8.0.4-ubi9` + `mongodb-community-search:latest`. Test in CI. |
| `createSearchIndex()` pymongo API differs from mongosh | 3 | 4 | 12 | Use `SearchIndexModel` from pymongo 4.7+. Test with mocked and live MongoDB. |
| Auth keyfile permissions wrong on Linux vs macOS | 3 | 3 | 9 | `chmod 400` in setup-generator. Volume mounts handle permissions. |
| mongot sync takes too long, search index not ready at startup | 3 | 3 | 9 | `detect_search_backend()` already handles missing index (falls back to $text). Retry on next startup. |
| Docker profile breaks existing `docker compose up` | 2 | 5 | 10 | Profile-gated services only start with `--profile search`. Default mode is unchanged. Verified via `docker compose config --quiet`. |
| `security.authorization: enabled` blocks unauthenticated connections | 4 | 4 | 16 | Init script creates backendUser. Override MONGODB_URI includes credentials. |
| Port conflicts (27017 default vs 27018 search) | 2 | 2 | 4 | Search mode uses port 27018 on host. Documented in start-search.sh. |

---

## Success Criteria

- [ ] `docker compose up` (default, no profile) still starts 3 containers, all healthy -- NO REGRESSIONS
- [ ] `docker compose --profile search up` starts 5 containers (setup-generator exits, mongodb-search, mongot, backend, frontend)
- [ ] `mongodb-search` has healthy replica set with keyfile auth
- [ ] `mongot` healthcheck passes on port 8080
- [ ] `mongotUser` has `searchCoordinator` role
- [ ] `backendUser` has `readWrite` on `agentic_search` + `clusterMonitor`
- [ ] `ensure_search_index()` creates `nodes_fulltext` search index
- [ ] `detect_search_backend()` returns `"atlas"` when mongot is running
- [ ] `atlas_search()` uses `$search` pipeline (not `$text` fallback) when mongot is running
- [ ] All 453+ backend tests pass
- [ ] All 300 frontend tests pass
- [ ] New search index tests pass (5+ tests)
- [ ] TypeScript clean (tsc --noEmit exit 0)

---

## Implementation Notes

### pymongo SearchIndexModel

pymongo 4.7+ supports `create_search_index()` with `SearchIndexModel`:

```python
from pymongo.operations import SearchIndexModel

model = SearchIndexModel(
    name="nodes_fulltext",
    definition={
        "mappings": {
            "dynamic": False,
            "fields": {
                "title": [{"type": "string", "analyzer": "lucene.standard"}],
                # ...
            }
        }
    }
)
collection.create_search_index(model)
```

Verify pymongo version in `pyproject.toml` supports this.

### Docker Compose Profile Behavior

- `docker compose up` -- starts services WITHOUT profiles only (mongodb, backend, frontend)
- `docker compose --profile search up` -- starts services with `search` profile AND services without profiles
- Profile-gated services: setup-generator, mongodb-search, mongot, mongodb-search-init
- Non-profile services: mongodb, backend, frontend

**Conflict:** Both `mongodb` (no profile) and `mongodb-search` (search profile) will start when using `--profile search`. This is by design -- they use different ports (27017 vs 27018). The backend override points to `mongodb-search`.

### Search Index Readiness

mongot takes time to sync and build indexes. The first startup may have a window where `detect_search_backend()` runs before the search index is ready. This is acceptable because:
1. The `$text` fallback works immediately
2. On subsequent startups (container restart, not rebuild), the index is already built
3. The index state is persisted in the `mongot_data` volume

### Field Mapping Rationale

| Field | Type | Analyzer | Why |
|-------|------|----------|-----|
| title | string | lucene.standard | Full-text search with tokenization, matches existing `$search` pipeline |
| summary | string | lucene.standard | Full-text search with tokenization |
| keywords | string | lucene.standard | Keyword search (standard tokenizes multi-word keywords) |
| documentId | string | lucene.keyword | Exact match filter (equals clause in compound query) |
| contentType | string | lucene.keyword | Exact match filter (optional content type filter) |
