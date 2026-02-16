#!/bin/bash
set -e

# This script runs inside the mongodb-search container via /docker-entrypoint-initdb.d/
# At this point, mongod is running on localhost WITHOUT auth (init mode).
# The localhost exception allows user creation without credentials.

MONGOT_PASSWORD="mongotSearchPass123"
BACKEND_PASSWORD="backendPass123"
MAX_RETRIES=30
RETRY_COUNT=0

echo "=== Init MongoDB: Configuring search users ==="

# Wait for mongod to be ready on localhost (with retry limit)
until mongosh --host 127.0.0.1 --quiet --eval "db.adminCommand('ping')" 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
        echo "ERROR: mongod not ready after $MAX_RETRIES retries. Exiting."
        exit 1
    fi
    echo "Waiting for mongod on localhost... (attempt $RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

echo "mongod is ready on localhost."

# Create mongotUser with searchCoordinator role (idempotent)
mongosh --host 127.0.0.1 --quiet --eval "
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

# Create backendUser with readWrite on agentic_search database (idempotent)
mongosh --host 127.0.0.1 --quiet --eval "
  try {
    db.getSiblingDB('admin').createUser({
      user: 'backendUser',
      pwd: '${BACKEND_PASSWORD}',
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

echo "=== Init MongoDB: Complete ==="
