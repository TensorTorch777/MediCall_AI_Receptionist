#!/bin/bash
set -e

echo "============================================="
echo " Hospital AI Receptionist — RunPod Setup"
echo " GPU: NVIDIA A40 (48GB)"
echo "============================================="

# ── 1. System dependencies ─────────────────────────────────────────
echo ""
echo "[1/7] Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq libopus-dev curl software-properties-common

# ── 2. Node.js 18 ──────────────────────────────────────────────────
echo ""
echo "[2/7] Installing Node.js 18..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
    apt-get install -y -qq nodejs
fi
echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# ── 3. ngrok ────────────────────────────────────────────────────────
echo ""
echo "[3/7] Installing ngrok..."
if ! command -v ngrok &> /dev/null; then
    curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok-v3-stable-linux-amd64.tgz \
        | tar -xz -C /usr/local/bin
fi
echo "ngrok version: $(ngrok --version)"

# ── 4. Project directory ───────────────────────────────────────────
echo ""
echo "[4/7] Setting up project directory..."
PROJECT_DIR="/workspace/hospital-ai-receptionist"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "ERROR: Project not found at $PROJECT_DIR"
    echo "Please upload the project first using scp or the Jupyter file browser."
    echo ""
    echo "From your local machine run:"
    echo "  scp -P <PORT> -r hospital-ai-receptionist/ root@<RUNPOD_IP>:/workspace/"
    exit 1
fi

# ── 5. Voice Server dependencies ──────────────────────────────────
echo ""
echo "[5/7] Installing Voice Server dependencies..."
cd "$PROJECT_DIR/voice-server"
npm install

# ── 6. API Server dependencies ────────────────────────────────────
echo ""
echo "[6/7] Installing API Server dependencies..."
cd "$PROJECT_DIR/api-server"
pip install -q -r requirements.txt

# ── 7. PersonaPlex / Moshi ─────────────────────────────────────────
echo ""
echo "[7/7] Installing PersonaPlex (Moshi)..."
pip install -q moshi

# Verify GPU is accessible
echo ""
echo "============================================="
echo " Setup Complete!"
echo "============================================="
echo ""
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
echo ""
echo "Next steps:"
echo "  1. Upload your Google credentials JSON to $PROJECT_DIR/api-server/"
echo "  2. Fill in $PROJECT_DIR/voice-server/.env"
echo "  3. Fill in $PROJECT_DIR/api-server/.env"
echo "  4. Run: bash $PROJECT_DIR/start.sh"
echo ""
