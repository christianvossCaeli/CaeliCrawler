#!/bin/bash
# CaeliCrawler Docker Start Script

set -e

echo "🐳 CaeliCrawler Docker Setup"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker ist nicht gestartet. Bitte starten Sie Docker Desktop."
    exit 1
fi

# Function to show usage
usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       - Start alle Container (default)"
    echo "  stop        - Stop alle Container"
    echo "  restart     - Restart alle Container"
    echo "  logs        - Zeige Container Logs"
    echo "  build       - Build alle Images neu"
    echo "  migrate     - Fuehre Datenbank-Migration aus"
    echo "  shell       - Oeffne Shell im Backend Container"
    echo "  clean       - Entferne alle Container und Volumes"
    echo "  status      - Zeige Container Status"
    echo ""
}

# Start containers
start() {
    echo "🚀 Starte Container..."
    docker-compose up -d

    echo ""
    echo "⏳ Warte auf Services..."
    sleep 5

    # Run migrations
    echo "📦 Fuehre Datenbank-Migration aus..."
    docker-compose exec -T backend alembic upgrade head 2>/dev/null || \
        docker-compose exec -T backend alembic revision --autogenerate -m "Initial" && \
        docker-compose exec -T backend alembic upgrade head

    echo ""
    echo "✅ Alle Services gestartet!"
    echo ""
    echo "🌐 Frontend:  http://localhost:5173"
    echo "📡 Backend:   http://localhost:8000"
    echo "📚 API Docs:  http://localhost:8000/docs"
    echo ""
}

# Stop containers
stop() {
    echo "🛑 Stoppe Container..."
    docker-compose down
    echo "✅ Alle Container gestoppt."
}

# Restart containers
restart() {
    stop
    start
}

# Show logs
logs() {
    docker-compose logs -f
}

# Build images
build() {
    echo "🔨 Build Images..."
    docker-compose build --no-cache
    echo "✅ Build abgeschlossen."
}

# Run migrations
migrate() {
    echo "📦 Fuehre Datenbank-Migration aus..."
    docker-compose exec backend alembic upgrade head
}

# Open shell
shell() {
    docker-compose exec backend bash
}

# Clean up
clean() {
    echo "🧹 Entferne Container und Volumes..."
    docker-compose down -v --remove-orphans
    echo "✅ Cleanup abgeschlossen."
}

# Show status
status() {
    docker-compose ps
}

# Main
case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    build)
        build
        ;;
    migrate)
        migrate
        ;;
    shell)
        shell
        ;;
    clean)
        clean
        ;;
    status)
        status
        ;;
    *)
        usage
        exit 1
        ;;
esac
