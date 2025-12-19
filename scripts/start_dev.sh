#!/bin/bash
# CaeliCrawler Development Start Script - einzelne Komponenten

usage() {
    echo "Usage: $0 [component]"
    echo ""
    echo "Components:"
    echo "  backend   - Start FastAPI Backend"
    echo "  worker    - Start Celery Worker"
    echo "  beat      - Start Celery Beat Scheduler"
    echo "  frontend  - Start Vue.js Frontend"
    echo "  all       - Start all components (default)"
    echo ""
}

start_backend() {
    echo "📡 Starte Backend..."
    cd backend
    source venv/bin/activate
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

start_worker() {
    echo "⚙️ Starte Celery Worker..."
    cd backend
    source venv/bin/activate
    celery -A workers.celery_app worker --loglevel=info -Q default,crawl,processing,ai
}

start_beat() {
    echo "⏰ Starte Celery Beat..."
    cd backend
    source venv/bin/activate
    celery -A workers.celery_app beat --loglevel=info
}

start_frontend() {
    echo "🎨 Starte Frontend..."
    cd frontend
    npm run dev
}

# Load environment
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

case "${1:-all}" in
    backend)
        start_backend
        ;;
    worker)
        start_worker
        ;;
    beat)
        start_beat
        ;;
    frontend)
        start_frontend
        ;;
    all)
        echo "Bitte nutzen Sie ./scripts/start.sh für alle Komponenten"
        echo "oder starten Sie einzelne Komponenten in separaten Terminals:"
        echo ""
        echo "  Terminal 1: ./scripts/start_dev.sh backend"
        echo "  Terminal 2: ./scripts/start_dev.sh worker"
        echo "  Terminal 3: ./scripts/start_dev.sh beat"
        echo "  Terminal 4: ./scripts/start_dev.sh frontend"
        ;;
    *)
        usage
        exit 1
        ;;
esac
