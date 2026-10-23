#!/usr/bin/env bash
# ==============================================================================
# Start Google Chrome in Remote Debugging Mode for Google Flow Automation
# ==============================================================================

PORT=9222
PROFILE_DIR="$HOME/.chrome-flow-automation"
TARGET_URL="https://flow.google.com/project/0ebc25ad-8226-4302-a20a-f0728d85d0a2"

echo "=========================================================="
echo " Starting Google Chrome for Google Flow Automation"
echo " Debugging Port: $PORT"
echo " Profile Dir:    $PROFILE_DIR"
echo " Target URL:     $TARGET_URL"
echo "=========================================================="

mkdir -p "$PROFILE_DIR"

# Check if Chrome is already listening on port 9222
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "[INFO] Chrome is ALREADY running on port $PORT."
    echo "[INFO] You can proceed to run the Python agent."
    exit 0
fi

# Launch Chrome on macOS
if [ -d "/Applications/Google Chrome.app" ]; then
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
        --remote-debugging-port=$PORT \
        --user-data-dir="$PROFILE_DIR" \
        --no-first-run \
        --no-default-browser-check \
        "$TARGET_URL" &
    echo "[SUCCESS] Google Chrome launched on port $PORT."
    echo "[ACTION REQUIRED] If you see a login screen, please log into your Google Account once."
else
    echo "[ERROR] Google Chrome is not installed at /Applications/Google Chrome.app"
    exit 1
fi
