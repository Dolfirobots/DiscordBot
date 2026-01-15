set -e

# --- Configuration ---
APP_NAME="dolfi-bot"
PYTHON_BIN="python3"
MAIN_FILE="main.py"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$REPO_DIR"

# Process Management (Main Bot)
echo "[4/5] managing $APP_NAME process..."
if pm2 describe "$APP_NAME" > /dev/null 2>&1; then
    echo "Restarting $APP_NAME..."
    pm2 restart "$APP_NAME"
else
    echo "Starting $APP_NAME..."
    pm2 start ./venv/bin/python --name "$APP_NAME" -- "$MAIN_FILE"
fi

echo "[5/5] saving PM2 process list..."
pm2 save --force