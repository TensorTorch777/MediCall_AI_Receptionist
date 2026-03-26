#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

echo "============================================="
echo " Starting Hospital AI Receptionist"
echo "============================================="

# ── 1. Start PersonaPlex / Moshi Server on GPU ─────────────────────
echo ""
echo "[1/3] Starting PersonaPlex (Moshi) on GPU..."
SSL_DIR=$(mktemp -d)
nohup python -m moshi_server --ssl "$SSL_DIR" \
    > "$LOG_DIR/personaplex.log" 2>&1 &
MOSHI_PID=$!
echo "  PID: $MOSHI_PID → log: $LOG_DIR/personaplex.log"
sleep 5

# ── 2. Start API Server (FastAPI) ─────────────────────────────────
echo ""
echo "[2/3] Starting API Server on port 8000..."
cd "$PROJECT_DIR/api-server"
nohup python main.py \
    > "$LOG_DIR/api-server.log" 2>&1 &
API_PID=$!
echo "  PID: $API_PID → log: $LOG_DIR/api-server.log"
sleep 2

# ── 3. Start Voice Server (Node.js) ───────────────────────────────
echo ""
echo "[3/3] Starting Voice Server on port 50061..."
cd "$PROJECT_DIR/voice-server"
nohup node index.js \
    > "$LOG_DIR/voice-server.log" 2>&1 &
VOICE_PID=$!
echo "  PID: $VOICE_PID → log: $LOG_DIR/voice-server.log"
sleep 2

# ── Summary ────────────────────────────────────────────────────────
echo ""
echo "============================================="
echo " All Services Running"
echo "============================================="
echo ""
echo " PersonaPlex (Moshi) : PID $MOSHI_PID  → https://localhost:8998"
echo " API Server (FastAPI) : PID $API_PID   → http://localhost:8000"
echo " Voice Server (Node)  : PID $VOICE_PID → localhost:50061"
echo ""
echo " Logs: $LOG_DIR/"
echo ""
echo " To expose VoiceServer for Fonoster, run:"
echo "   ngrok tcp 50061"
echo ""
echo " To check health:"
echo "   curl http://localhost:8000/health"
echo ""
echo " To stop all:"
echo "   kill $MOSHI_PID $API_PID $VOICE_PID"
echo ""

# Save PIDs for easy cleanup
echo "$MOSHI_PID $API_PID $VOICE_PID" > "$LOG_DIR/pids.txt"
