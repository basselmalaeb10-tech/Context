#!/bin/bash
# Start the Context app — builds frontend and runs the backend on port 8000
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Building frontend..."
cd "$SCRIPT_DIR/frontend"
npm install --silent
npm run build

echo ""
echo "Starting Context on http://localhost:8000"
echo ""
cd "$SCRIPT_DIR/backend"
pip install -q -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
