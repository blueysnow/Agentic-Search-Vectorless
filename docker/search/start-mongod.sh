#!/bin/bash
set -e

# Custom entrypoint for mongodb-search container.
#
# Phase 1: Start mongod WITHOUT setParameter (no mongotHost) to create basic users.
#           The searchCoordinator role only exists when mongotHost is set, so
#           mongotUser is created in Phase 2.
# Phase 2: Start mongod with full config (setParameter for mongot). Once healthy,
#           create mongotUser with searchCoordinator role.

INIT_CONF="/etc/mongod-init.conf"
FULL_CONF="/etc/mongod.conf"
INIT_MARKER="/data/db/.initialized"
MONGOT_MARKER="/data/db/.mongot_user_created"

ADMIN_PASSWORD="adminPass123"
MONGOT_PASSWORD="mongotSearchPass123"
BACKEND_PASSWORD="backendPass123"

# Fix keyfile permissions (setup-generator creates it as root)
if [ -f /auth/keyfile ]; then
    cp /auth/keyfile /tmp/keyfile
    chmod 400 /tmp/keyfile
fi

create_mongot_user() {
    # Wait for mongod to be ready with auth
    local retries=0
    until mongosh --host 127.0.0.1 -u admin -p "$ADMIN_PASSWORD" \
          --authenticationDatabase admin --quiet \
          --eval "db.adminCommand('ping')" 2>/dev/null; do
        retries=$((retries + 1))
        if [ "$retries" -ge 30 ]; then
            echo "ERROR: mongod not ready for mongotUser creation after 30 retries"
            return 1
        fi
        sleep 2
    done

    mongosh --host 127.0.0.1 -u admin -p "$ADMIN_PASSWORD" \
        --authenticationDatabase admin --quiet --eval "
      try {
        db.getSiblingDB('admin').createUser({
          user: 'mongotUser',
          pwd: '${MONGOT_PASSWORD}',
          roles: [{ role: 'root', db: 'admin' }]
        });
        print('Created mongotUser');
      } catch (e) {
        if (e.codeName === 'DuplicateKey' || e.code === 51003) {
          print('mongotUser already exists');
        } else {
          print('Error creating mongotUser: ' + e.message);
        }
      }
    "
    touch "$MONGOT_MARKER"
}

# ── Phase 1: First-time initialization (no setParameter) ──
if [ ! -f "$INIT_MARKER" ]; then
    echo "=== Phase 1: Initializing MongoDB ==="

    mongod --config "$INIT_CONF" --fork --logpath /proc/1/fd/1

    RETRIES=0
    until mongosh --quiet --eval "db.adminCommand('ping')" 2>/dev/null; do
        RETRIES=$((RETRIES + 1))
        if [ "$RETRIES" -ge 30 ]; then
            echo "ERROR: mongod not ready after 30 retries"
            exit 1
        fi
        echo "Waiting for mongod... ($RETRIES/30)"
        sleep 2
    done
    echo "mongod is ready."

    # Initiate replica set
    mongosh --quiet --eval "
      try { rs.status().ok; print('Replica set already initiated');
      } catch(e) {
        rs.initiate({_id: 'rs0', members: [{_id: 0, host: 'mongodb-search:27017'}]});
        print('Replica set initiated');
      }
    "

    # Wait for primary
    RETRIES=0
    until mongosh --quiet --eval "rs.isMaster().ismaster" 2>/dev/null | grep -q true; do
        RETRIES=$((RETRIES + 1))
        if [ "$RETRIES" -ge 15 ]; then echo "ERROR: not elected primary"; exit 1; fi
        sleep 2
    done
    echo "Primary elected."

    # Create admin user
    mongosh --quiet --eval "
      try {
        db.getSiblingDB('admin').createUser({
          user: 'admin', pwd: '${ADMIN_PASSWORD}', roles: ['root']
        }); print('Created admin user');
      } catch (e) {
        if (e.codeName === 'DuplicateKey' || e.code === 51003) { print('admin already exists'); }
        else { throw e; }
      }
    "

    # Create backendUser
    mongosh --quiet --eval "
      try {
        db.getSiblingDB('admin').createUser({
          user: 'backendUser', pwd: '${BACKEND_PASSWORD}',
          roles: [
            { role: 'readWrite', db: 'agentic_search' },
            { role: 'clusterMonitor', db: 'admin' }
          ]
        }); print('Created backendUser');
      } catch (e) {
        if (e.codeName === 'DuplicateKey' || e.code === 51003) { print('backendUser already exists'); }
        else { throw e; }
      }
    "

    touch "$INIT_MARKER"
    echo "=== Phase 1 complete ==="

    mongod --shutdown --dbpath /data/db
    sleep 2
fi

# ── Phase 2: Start with full config + create mongotUser ──
echo "=== Phase 2: Starting mongod with full config ==="

# Start mongod in background first to create mongotUser
# (searchCoordinator role only exists when mongotHost setParameter is active)
if [ ! -f "$MONGOT_MARKER" ]; then
    mongod --config "$FULL_CONF" --fork --logpath /proc/1/fd/1
    create_mongot_user
    # Stop forked mongod, then start in foreground via exec
    mongod --shutdown --dbpath /data/db
    sleep 2
fi

exec mongod --config "$FULL_CONF"
