# Research: MongoDB Community Search with mongot

**Date:** 2026-02-16
**Source:** https://github.com/JohnGUnderwood/mdb-community-search
**Purpose:** Understand how to properly deploy `$search` on MongoDB Community Edition using mongot

## Key Findings

### Architecture: Two-Container Model

mongot runs as a **separate process/container** alongside mongod:
- `mongodb/mongodb-community-server:latest` -- mongod (database)
- `mongodb/mongodb-community-search:latest` -- mongot (Lucene search engine)
- Communication via gRPC on port 27028
- mongot also exposes: health check (8080), metrics (9946)

### mongod Configuration for Search

mongod.conf requires these setParameter entries:
```yaml
setParameter:
  searchIndexManagementHostAndPort: "mongot-host:27028"
  mongotHost: "mongot-host:27028"
  skipAuthenticationToSearchIndexManagementServer: false
  useGrpcForSearch: true
```

Without these, `$search` stages fail even if mongot is running.

### Authentication Requirements

1. **Keyfile** for replica set authentication (required when security.authorization=enabled)
2. **mongotUser** with `searchCoordinator` role in admin database
3. **passwordFile** passed to mongot for authentication to mongod

```js
adminDb.createUser({
  user: 'mongotUser',
  pwd: '...',
  roles: [{ role: 'searchCoordinator', db: 'admin' }]
});
```

### mongot Configuration (mongot.conf / config.default.yml)

```yaml
syncSource:
  replicaSet:
    hostAndPort: "mongod-host:27017"
    username: "mongotUser"
    passwordFile: "/auth/passwordFile"
    authSource: "admin"
    tls: false
storage:
  dataPath: "/data/mongot"
server:
  grpc:
    address: "mongot-host:27028"
metrics:
  enabled: true
  address: "mongot-host:9946"
healthCheck:
  address: "mongot-host:8080"
logging:
  verbosity: INFO
```

### Search Index Creation

Search indexes are created programmatically via `createSearchIndex()`:
```js
db.collection.createSearchIndex('index_name', {
  mappings: {
    dynamic: true,  // or false with explicit field definitions
    fields: {
      title: [
        { type: 'string', analyzer: 'lucene.standard' },
        { type: 'autocomplete', tokenization: 'edgeGram', minGrams: 3, maxGrams: 15 }
      ]
    }
  }
});
```

### $search Pipeline Syntax (Confirmed Same as Atlas)

```js
db.collection.aggregate([
  {
    $search: {
      index: 'text_index',
      compound: {
        must: [{ text: { query: '...', path: ['title', 'plot'] } }],
        should: [
          { text: { query: '...', path: ['genres'] } },
          { range: { path: 'year', gte: 2000, lte: 2020 } }
        ]
      }
    }
  },
  { $limit: 10 },
  { $project: { title: 1, score: { $meta: 'searchScore' } } }
]);
```

Score metadata: `{ $meta: 'searchScore' }` -- same as Atlas.

### Docker Compose Setup Pattern

1. **Phase 1 (setup):** Generate keyfile + passwordFile via `setup-generator` container
2. **Phase 2 (run):** Start mongod → healthcheck → start mongot
3. **Init script:** Create mongotUser, load sample data
4. **External network:** `docker network create search-community`

### $vectorSearch Also Works on Community

```js
db.collection.aggregate([
  {
    $vectorSearch: {
      index: 'vector_index',
      path: 'embedding_field',
      queryVector: [...],
      numCandidates: 100,
      limit: 10
    }
  },
  { $project: { title: 1, score: { $meta: 'vectorSearchScore' } } }
]);
```

## Gaps in Our Implementation

1. **No mongot container** in docker-compose.yml
2. **No createSearchIndex()** code -- we reference `nodes_fulltext` but never create it
3. **No mongod.conf** with search parameters (searchIndexManagementHostAndPort, mongotHost)
4. **No authentication** for mongot (searchCoordinator role, keyfile, passwordFile)
5. **Docker image:** We use `mongo:7.0` not `mongodb/mongodb-community-server:latest`

## Our Correct Patterns

1. `$search` pipeline syntax is correct (compound, must, should, text, equals, boost)
2. Score metadata correct (`searchScore` for $search, `textScore` for $text)
3. `detect_search_backend()` fallback pattern is sound
4. `$text` fallback with weighted fields works everywhere
