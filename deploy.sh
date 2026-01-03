#!/bin/bash

set -e

# --- Configuration ---
APP_NAME="dolfi-bot"
TICKET_APP_NAME="dolfi-ticket-bot"
PYTHON_BIN="python3"
MAIN_FILE="main.py"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Ensure we are in the correct directory
cd "$REPO_DIR"

echo "----------------------------------------------"
echo "[0/6] starting deployment: $APP_NAME, $TICKET_APP_NAME"
echo "----------------------------------------------"

# 1. Update code and check
echo "[1/6] checking for latest changes from GitHub..."
git fetch origin main

OLD_COMMIT=$(git rev-parse HEAD)

git reset --hard origin/main
chmod +x deploy.sh

NEW_COMMIT=$(git rev-parse HEAD)

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    echo "----------------------------------------------"
    echo "No changes detected. Skipping restart."
    echo "----------------------------------------------"
    exit 0
fi

echo "New changes detected! Proceeding with update..."

# 2. Virtual Environment Setup
if [ ! -d "venv" ]; then
    echo "[2/6] creating virtual environment..."
    $PYTHON_BIN -m venv venv
else
    echo "[2/6] virtual environment already exists."
fi

# 3. Dependencies
echo "[3/6] installing/updating dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 4. Environment Check
if [ ! -f ".env" ]; then
    echo "-------------------------------------------------------"
    echo "ERROR: .env file missing in $REPO_DIR"
    echo "Please create it manually or upload it once."
    echo "-------------------------------------------------------"
    exit 1
fi

# 5. Process Management (Main Bot)
echo "[4/6] managing $APP_NAME process..."
if pm2 describe "$APP_NAME" > /dev/null 2>&1; then
    echo "Restarting $APP_NAME..."
    pm2 restart "$APP_NAME"
else
    echo "Starting $APP_NAME..."
    pm2 start ./venv/bin/python --name "$APP_NAME" -- "$MAIN_FILE"
fi

# 6. Process Management (Ticket Bot)
echo "[5/6] managing $TICKET_APP_NAME process..."
if pm2 describe "$TICKET_APP_NAME" > /dev/null 2>&1; then
    echo "Restarting $TICKET_APP_NAME..."
    pm2 restart "$TICKET_APP_NAME"
else
    echo "Starting $TICKET_APP_NAME..."
    pm2 start ./venv/bin/python --name "$TICKET_APP_NAME" -- "$MAIN_FILE" --ticket
fi

# Finalizing
echo "[6/6] saving PM2 process list..."
pm2 save --force

echo "----------------------------------------------"
echo "Deployment finished successfully!"
echo "Use 'pm2 status' to check your bots."
echo "----------------------------------------------"
