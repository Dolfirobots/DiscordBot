set -e

# --- Configuration ---
APP_NAME="dolfi-bot"
TICKET_APP_NAME="dolfi-ticket-bot"
PYTHON_BIN="python3"
MAIN_FILE="main.py"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

cd "$REPO_DIR"

# Process Management (Main Bot)
echo "[4/6] managing $APP_NAME process..."
if pm2 describe "$APP_NAME" > /dev/null 2>&1; then
    echo "Restarting $APP_NAME..."
    pm2 restart "$APP_NAME"
else
    echo "Starting $APP_NAME..."
    pm2 start ./venv/bin/python --name "$APP_NAME" -- "$MAIN_FILE"
fi

# Process Management (Ticket Bot)
echo "[5/6] managing $TICKET_APP_NAME process..."
if pm2 describe "$TICKET_APP_NAME" > /dev/null 2>&1; then
    echo "Restarting $TICKET_APP_NAME..."
    pm2 restart "$TICKET_APP_NAME"
else
    echo "Starting $TICKET_APP_NAME..."
    pm2 start ./venv/bin/python --name "$TICKET_APP_NAME" -- "$MAIN_FILE" --ticket
fi

echo "[6/6] saving PM2 process list..."
pm2 save --force