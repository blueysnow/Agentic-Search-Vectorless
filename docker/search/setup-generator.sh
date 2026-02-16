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
