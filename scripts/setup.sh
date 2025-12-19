#!/bin/bash
# CaeliCrawler Setup Script

set -e

echo "🚀 CaeliCrawler Setup"
echo "===================="

# Check for required tools
command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3 ist erforderlich"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js ist erforderlich"; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "❌ npm ist erforderlich"; exit 1; }

# Backend Setup
echo ""
echo "📦 Backend Setup..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "  → Erstelle Python Virtual Environment..."
    python3 -m venv venv
fi

# Activate and install dependencies
echo "  → Installiere Python Dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "  → Installiere Playwright Browser..."
playwright install chromium

cd ..

# Frontend Setup
echo ""
echo "📦 Frontend Setup..."
cd frontend

echo "  → Installiere Node.js Dependencies..."
npm install

cd ..

# Copy environment file
echo ""
echo "⚙️ Konfiguration..."
if [ ! -f ".env" ]; then
    cp config/.env.example .env
    echo "  → .env Datei erstellt (bitte anpassen!)"
else
    echo "  → .env existiert bereits"
fi

echo ""
echo "✅ Setup abgeschlossen!"
echo ""
echo "Nächste Schritte:"
echo "1. Passen Sie die .env Datei an (Datenbank, Redis, Azure OpenAI)"
echo "2. Erstellen Sie die PostgreSQL Datenbank: createdb caelichrawler"
echo "3. Starten Sie Redis: redis-server"
echo "4. Führen Sie die Migrationen aus: cd backend && source venv/bin/activate && alembic upgrade head"
echo "5. Starten Sie die Anwendung: ./scripts/start.sh"
