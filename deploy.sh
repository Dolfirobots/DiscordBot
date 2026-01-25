#!/bin/bash
set -e

# Config
APP_NAME="dolfi-bot"
PYTHON_BIN="python3"
MAIN_FILE="main.py"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
FORCE=false

export PATH="/usr/local/bin:/usr/bin:/bin"

if [[ "$1" == "--force" ]]; then
    FORCE=true
fi

cd "$REPO_DIR"

start_bot() {
    echo "[4/5] managing $APP_NAME process..."

    PM2="$(command -v pm2)"
    if [ -z "$PM2" ]; then
        echo "ERROR: pm2 not found in PATH"
        exit 1
    fi

    if $PM2 describe "$APP_NAME" > /dev/null 2>&1; then
        echo "Restarting $APP_NAME..."
        $PM2 restart "$APP_NAME"
    else
        echo "Starting $APP_NAME..."
        $PM2 start ./venv/bin/python --name "$APP_NAME" -- "$MAIN_FILE"
    fi

    echo "[5/5] saving PM2 process list..."
    $PM2 save --force
}

# Deploy
echo "----------------------------------------------"
echo "[0/5] starting deployment: $APP_NAME"
echo "----------------------------------------------"

echo "[1/5] checking for latest changes from GitHub..."
git fetch origin main

OLD_COMMIT=$(git rev-parse HEAD)
git reset --hard origin/main
chmod +x deploy.sh
NEW_COMMIT=$(git rev-parse HEAD)

# Virtual python env
if [ ! -d "venv" ]; then
    echo "[2/5] creating virtual environment..."
    $PYTHON_BIN -m venv venv
else
    echo "[2/5] virtual environment already exists."
fi

# Dependencies
echo "[3/5] installing/updating dependencies..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Env check
if [ ! -f ".env" ]; then
    echo "ERROR: .env file missing in $REPO_DIR"
    exit 1
fi

# Github check
if $FORCE; then
    echo "----------------------------------------------"
    echo "FORCE mode enabled – restarting bot"
    echo "----------------------------------------------"
    start_bot
elif [ "$OLD_COMMIT" != "$NEW_COMMIT" ]; then
    echo "New changes detected! Proceeding with update..."
    start_bot
else
    echo "----------------------------------------------"
    echo "No changes detected. Skipping restart."
    echo "----------------------------------------------"
fi

echo "----------------------------------------------"
echo "Deployment finished successfully!"
echo "Use 'pm2 status' to check your bot."
echo "----------------------------------------------"
