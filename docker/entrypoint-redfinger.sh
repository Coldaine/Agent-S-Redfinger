#!/bin/bash
set -e

echo "=========================================="
echo "Agent S3 - Redfinger Automation Container"
echo "=========================================="

# Create Xauthority file
touch /root/.Xauthority
export XAUTHORITY=/root/.Xauthority

# Start Xvfb (virtual display)
echo "[1/4] Starting virtual display (1920x1080)..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
export DISPLAY=:99
sleep 3

# Start window manager
echo "[2/4] Starting window manager..."
metacity --replace &
sleep 2

# Start VNC (optional, for debugging)
if [ "$ENABLE_VNC" = "true" ]; then
    echo "[3/4] Starting VNC server on :5900..."
    x11vnc -display :99 -forever -shared -rfbport 5900 -nopw -quiet > /dev/null 2>&1 &
    echo "       Connect via VNC to localhost:5900 to see agent in action"
else
    echo "[3/4] VNC disabled (set ENABLE_VNC=true to enable)"
fi

# Verify display is working
echo "[4/4] Verifying display..."
xdpyinfo -display :99 > /dev/null 2>&1 || {
    echo "ERROR: Display :99 not available"
    exit 1
}

echo "✅ Container ready!"
echo ""

# Execute the command
exec "$@"
