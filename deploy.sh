#!/bin/bash
set -e

# Config
# Crontab config:
# */5 * * * * echo "--- $(date) ---" >> .../logs/deploy.log && /usr/bin/flock -n .../deploy.lock /bin/bash .../DiscordBot/deploy.sh >> .../logs/deploy.log 2>&1
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

send_discord_embed() {
    local STATUS="$1"
    local COLOR="$2"

    local HOSTNAME="$(hostname)"
    local USERNAME="$(whoami)"
    local DATE="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"
    local SHORT_OLD="${OLD_COMMIT:0:7}"
    local SHORT_NEW="${NEW_COMMIT:0:7}"

    curl -s -X POST "$DISCORD_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"Deploy Bot\",
            \"avatar_url\": \"https://i.imgur.com/4M34hi2.png\",
            \"embeds\": [{
                \"title\": \"🚀 $APP_NAME Deployment\",
                \"description\": \"$STATUS\",
                \"color\": $COLOR,
                \"fields\": [
                    {\"name\": \"📦 App\", \"value\": \"$APP_NAME\", \"inline\": true},
                    {\"name\": \"🔀 Old Commit\", \"value\": \"\`$SHORT_OLD\`\", \"inline\": true},
                    {\"name\": \"✨ New Commit\", \"value\": \"\`$SHORT_NEW\`\", \"inline\": true},
                    {\"name\": \"⚡ Force Mode\", \"value\": \"$FORCE\", \"inline\": true}
                ],
                \"footer\": {
                    \"text\": \"Deployed at $DATE\"
                }
            }]
        }"
}

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
        ACTION="Bot updated and restarted"
    else
        echo "Starting $APP_NAME..."
        $PM2 start ./venv/bin/python --name "$APP_NAME" -- "$MAIN_FILE"
        ACTION="Bot started"
    fi


    echo "[5/5] saving PM2 process list..."
    $PM2 save --force

    send_discord_embed "$ACTION – dependencies updated & bot is online" 5814783
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

# .env check
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "ERROR: .env file missing"
    exit 1
fi

if [ -z "$DISCORD_WEBHOOK_URL" ]; then
    echo "ERROR: DISCORD_WEBHOOK_URL not set"
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
