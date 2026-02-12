# DataStream SDK Reference Guide

## Overview

The DataStream SDK provides client libraries for interacting with the DataStream
Platform API. Libraries are available for Python, JavaScript/TypeScript, Go, and
Java.

All SDK clients follow a consistent design pattern:
1. Initialize with connection parameters
2. Authenticate (API key or OAuth)
3. Perform operations (create pipelines, push data, query results)
4. Handle errors with typed exceptions

## Installation

### Python

```bash
pip install datastream-sdk
```

Requires Python 3.10 or later.

### JavaScript / TypeScript

```bash
npm install @datastream/sdk
```

Requires Node.js 18 LTS or later. TypeScript definitions are included.

### Go

```bash
go get github.com/datastream/sdk-go@v3
```

Requires Go 1.21 or later.

### Java

```xml
<dependency>
  <groupId>io.datastream</groupId>
  <artifactId>datastream-sdk</artifactId>
  <version>3.2.0</version>
</dependency>
```

Requires Java 17 or later.

## Authentication

All API calls require authentication. The SDK supports two authentication methods:

### API Key Authentication

```python
from datastream import Client

client = Client(
    base_url="https://datastream.example.com",
    api_key="ds_key_abc123..."
)
```

### OAuth 2.0 Authentication

```python
from datastream import Client, OAuthConfig

oauth = OAuthConfig(
    client_id="my-app",
    client_secret="secret",
    token_url="https://auth.example.com/oauth/token"
)

client = Client(
    base_url="https://datastream.example.com",
    oauth=oauth
)
```

## Pipeline Management

### Creating a Pipeline

```python
pipeline = client.pipelines.create(
    name="user-events",
    source={
        "type": "kafka",
        "config": {
            "brokers": ["kafka-1:9092", "kafka-2:9092"],
            "topic": "raw-events",
            "group_id": "datastream-ingest"
        }
    },
    transforms=[
        {"type": "filter", "config": {"field": "event_type", "equals": "click"}},
        {"type": "enrich", "config": {"lookup_table": "user_profiles"}},
    ],
    sink={
        "type": "postgresql",
        "config": {
            "connection_string": "postgresql://...",
            "table": "processed_events"
        }
    }
)

print(f"Created pipeline: {pipeline.id}")
```

### Listing Pipelines

```python
pipelines = client.pipelines.list(status="running")
for p in pipelines:
    print(f"{p.name}: {p.status} (events: {p.metrics.total_events})")
```

### Starting and Stopping

```python
client.pipelines.start(pipeline_id="pipe-123")
client.pipelines.stop(pipeline_id="pipe-123")
```

## Data Operations

### Pushing Events

```python
# Single event
client.data.push(
    pipeline="user-events",
    event={"user_id": "u-456", "action": "click", "timestamp": "2024-01-15T10:30:00Z"}
)

# Batch push
events = [
    {"user_id": "u-456", "action": "click"},
    {"user_id": "u-789", "action": "purchase"},
    {"user_id": "u-123", "action": "view"},
]
result = client.data.batch_push(pipeline="user-events", events=events)
print(f"Pushed {result.accepted} events, {result.rejected} rejected")
```

### Querying Data

```python
results = client.data.query(
    pipeline="user-events",
    filter={"event_type": "purchase", "timestamp": {"$gte": "2024-01-01"}},
    limit=100,
    sort=[("timestamp", "desc")]
)

for row in results:
    print(f"{row['user_id']}: {row['action']} at {row['timestamp']}")
```

## Error Handling

The SDK raises typed exceptions for different error categories:

```python
from datastream import (
    Client,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    ServerError,
)

try:
    pipeline = client.pipelines.get("nonexistent")
except NotFoundError as e:
    print(f"Pipeline not found: {e.detail}")
except AuthenticationError:
    print("Invalid API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after} seconds")
except ValidationError as e:
    print(f"Invalid request: {e.errors}")
except ServerError:
    print("Server error, please retry")
```

## WebSocket Streaming

```python
import asyncio
from datastream import AsyncClient

async def stream_events():
    client = AsyncClient(
        base_url="https://datastream.example.com",
        api_key="ds_key_abc123..."
    )

    async with client.stream("user-events") as stream:
        async for event in stream:
            print(f"Received: {event}")
            if event.get("action") == "purchase":
                await process_purchase(event)

asyncio.run(stream_events())
```

## Configuration Reference

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| base_url | str | required | DataStream API base URL |
| api_key | str | None | API key for authentication |
| oauth | OAuthConfig | None | OAuth configuration |
| timeout | float | 30.0 | Request timeout in seconds |
| max_retries | int | 3 | Maximum retry attempts |
| retry_backoff | float | 1.0 | Base retry delay in seconds |
| verify_ssl | bool | True | Verify TLS certificates |
| connection_pool_size | int | 10 | HTTP connection pool size |

## Changelog

### v3.2.0 (2024-12-01)
- Added WebSocket streaming support
- Added batch push with partial failure reporting
- Improved retry logic with jitter
- Fixed connection leak in long-running clients

### v3.1.0 (2024-06-15)
- Added OAuth 2.0 support
- Added pipeline templates
- Performance improvements for large batch operations

### v3.0.0 (2024-01-10)
- Complete rewrite for DataStream Platform v3
- New API design with typed models
- Added async client support
- Breaking: Removed v2 API compatibility layer
