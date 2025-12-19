#!/bin/bash
# CaeliCrawler Start Script

set -e

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo "🚀 CaeliCrawler starten..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Beende Prozesse..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo "📡 Starte Backend API..."
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Start Celery Worker
echo "⚙️ Starte Celery Worker..."
celery -A workers.celery_app worker --loglevel=info &
WORKER_PID=$!

# Start Celery Beat (Scheduler)
echo "⏰ Starte Celery Beat..."
celery -A workers.celery_app beat --loglevel=info &
BEAT_PID=$!

cd ..

# Start Frontend
echo "🎨 Starte Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Alle Services gestartet!"
echo ""
echo "🌐 Frontend:  http://localhost:5173"
echo "📡 Backend:   http://localhost:8000"
echo "📚 API Docs:  http://localhost:8000/docs"
echo ""
echo "Drücken Sie Ctrl+C zum Beenden..."

# Wait for all processes
wait
