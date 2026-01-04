#!/bin/bash

set -e

# --- Configuration ---
# More in deploy_start.sh
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ensure we are in the correct directory
cd "$REPO_DIR"

echo "----------------------------------------------"
echo "[0/6] starting deployment: $APP_NAME, $TICKET_APP_NAME"
echo "----------------------------------------------"

# Update code and check
echo "[1/6] checking for latest changes from GitHub..."
git fetch origin main

OLD_COMMIT=$(git rev-parse HEAD)

git reset --hard origin/main
chmod +x deploy.sh

NEW_COMMIT=$(git rev-parse HEAD)

# Virtual Environment Setup
if [ ! -d "venv" ]; then
    echo "[2/6] creating virtual environment..."
    $PYTHON_BIN -m venv venv
else
    echo "[2/6] virtual environment already exists."
fi

# Dependencies
echo "[3/6] installing/updating dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Environment Check
if [ ! -f ".env" ]; then
    echo "-------------------------------------------------------"
    echo "ERROR: .env file missing in $REPO_DIR"
    echo "Please create it manually or upload it once."
    echo "-------------------------------------------------------"
    exit 1
fi

if [ "$OLD_COMMIT" != "$NEW_COMMIT" ]; then
    echo "New changes detected! Proceeding with update..."
    /bin/bash deploy_start.sh
else
    echo "----------------------------------------------"
    echo "No changes detected. Skipping restart."
    echo "----------------------------------------------"
fi

echo "----------------------------------------------"
echo "Deployment finished successfully!"
echo "Use 'pm2 status' to check your bots."
echo "----------------------------------------------"
