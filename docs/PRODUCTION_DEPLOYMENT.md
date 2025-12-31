# CaeliCrawler - Production & Staging Deployment Guide

Dieses Dokument beschreibt alle notwendigen Schritte und Sicherheitsmaßnahmen für das Deployment in Production- und Staging-Umgebungen.

---

## Inhaltsverzeichnis

1. [Übersicht der Umgebungen](#1-übersicht-der-umgebungen)
2. [Server-Infrastruktur](#2-server-infrastruktur)
3. [Datenbank-Setup](#3-datenbank-setup)
4. [Redis-Setup](#4-redis-setup)
5. [Docker-Konfiguration](#5-docker-konfiguration)
6. [Reverse Proxy & SSL](#6-reverse-proxy--ssl)
7. [Environment-Variablen](#7-environment-variablen)
8. [Sicherheitsmaßnahmen](#8-sicherheitsmaßnahmen)
9. [Monitoring & Logging](#9-monitoring--logging)
10. [Backup-Strategie](#10-backup-strategie)
11. [CI/CD Pipeline](#11-cicd-pipeline)
12. [Checklisten](#12-checklisten)

---

## 1. Übersicht der Umgebungen

### Umgebungen

| Umgebung | Zweck | Domain |
|----------|-------|--------|
| **Development** | Lokale Entwicklung | localhost:5173 |
| **Staging** | Testing vor Production | staging.caeli-wind.de |
| **Production** | Live-System | app.caeli-wind.de |

### Architektur-Übersicht

```
                    ┌─────────────────┐
                    │   Cloudflare    │
                    │   (DNS + CDN)   │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     Nginx       │
                    │ (Reverse Proxy) │
                    │   + SSL/TLS     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│   Frontend    │   │    Backend    │   │  API Docs     │
│  (Vue.js)     │   │  (FastAPI)    │   │  (Optional)   │
│   :5173       │   │    :8000      │   │    :8001      │
└───────────────┘   └───────┬───────┘   └───────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼───────┐   ┌───────▼───────┐   ┌──────▼──────┐
│  PostgreSQL   │   │     Redis     │   │   Celery    │
│    :5432      │   │    :6379      │   │   Workers   │
└───────────────┘   └───────────────┘   └─────────────┘
```

---

## 2. Server-Infrastruktur

### Minimale Hardware-Anforderungen

| Komponente | Staging | Production |
|------------|---------|------------|
| **CPU** | 2 vCPUs | 4+ vCPUs |
| **RAM** | 4 GB | 8+ GB |
| **Storage** | 50 GB SSD | 100+ GB SSD |
| **Netzwerk** | 100 Mbit/s | 1 Gbit/s |

### Empfohlene Cloud-Provider

- **Hetzner Cloud** (EU, DSGVO-konform, günstig)
- **DigitalOcean** (einfach)
- **AWS/Azure** (Enterprise)

### Server-Setup (Ubuntu 22.04 LTS)

```bash
# System aktualisieren
sudo apt update && sudo apt upgrade -y

# Grundlegende Pakete
sudo apt install -y \
    curl \
    git \
    htop \
    ufw \
    fail2ban \
    unattended-upgrades

# Docker installieren
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Docker Compose installieren
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Firewall konfigurieren
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# Fail2ban aktivieren
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### SSH-Härtung

```bash
# /etc/ssh/sshd_config anpassen:
sudo nano /etc/ssh/sshd_config
```

```
# Empfohlene Einstellungen
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
```

```bash
sudo systemctl restart sshd
```

---

## 3. Datenbank-Setup

### PostgreSQL mit getrennten Usern

**WICHTIG:** In Production niemals den App-User als Superuser verwenden!

```sql
-- Als postgres Admin-User ausführen:

-- 1. Datenbank erstellen
CREATE DATABASE caelichrawler_prod;

-- 2. Admin-User für Migrationen (mit erweiterten Rechten)
CREATE USER caelichrawler_admin WITH PASSWORD 'SICHERES_ADMIN_PASSWORT';
GRANT ALL PRIVILEGES ON DATABASE caelichrawler_prod TO caelichrawler_admin;
ALTER USER caelichrawler_admin CREATEDB;

-- 3. App-User für die Anwendung (eingeschränkte Rechte)
CREATE USER caelichrawler_app WITH PASSWORD 'SICHERES_APP_PASSWORT';
GRANT CONNECT ON DATABASE caelichrawler_prod TO caelichrawler_app;

-- 4. Nach Migrationen: Rechte für App-User setzen
\c caelichrawler_prod
GRANT USAGE ON SCHEMA public TO caelichrawler_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO caelichrawler_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO caelichrawler_app;

-- Für zukünftige Tabellen
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO caelichrawler_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO caelichrawler_app;

-- 5. Extensions (als Admin)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### PostgreSQL Konfiguration (postgresql.conf)

```ini
# Performance
shared_buffers = 2GB                    # 25% des RAM
effective_cache_size = 6GB              # 75% des RAM
work_mem = 64MB
maintenance_work_mem = 512MB

# Connections
max_connections = 200
superuser_reserved_connections = 3

# Write-Ahead Log
wal_level = replica
max_wal_senders = 3
wal_keep_size = 1GB

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000       # Queries > 1s loggen
log_connections = on
log_disconnections = on

# Security
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'
password_encryption = scram-sha-256
```

### pg_hba.conf (Zugriffskontrolle)

```
# TYPE  DATABASE        USER                ADDRESS         METHOD
local   all             postgres                            peer
local   all             all                                 scram-sha-256
host    all             all                 127.0.0.1/32    scram-sha-256
host    all             all                 ::1/128         scram-sha-256

# Docker-Netzwerk (anpassen!)
host    caelichrawler_prod  caelichrawler_app   172.18.0.0/16   scram-sha-256

# Keine externen Verbindungen!
# host  all             all                 0.0.0.0/0       reject
```

---

## 4. Redis-Setup

### Redis Konfiguration (redis.conf)

```ini
# Netzwerk - nur lokal/Docker
bind 127.0.0.1
protected-mode yes
port 6379

# Passwort setzen!
requirepass SICHERES_REDIS_PASSWORT

# Persistenz
appendonly yes
appendfsync everysec
save 900 1
save 300 10
save 60 10000

# Memory
maxmemory 1gb
maxmemory-policy allkeys-lru

# Security
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
rename-command CONFIG ""
```

---

## 5. Docker-Konfiguration

### Production docker-compose.yml

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    image: postgres:17-alpine
    container_name: caeli-postgres
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_ADMIN_USER}
      POSTGRES_PASSWORD: ${POSTGRES_ADMIN_PASSWORD}
      POSTGRES_DB: caelichrawler_prod
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    networks:
      - caeli-internal
    # NICHT nach außen exposen!
    # ports:
    #   - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_ADMIN_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 2G

  redis:
    image: redis:7-alpine
    container_name: caeli-redis
    restart: always
    command: redis-server /usr/local/etc/redis/redis.conf
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/usr/local/etc/redis/redis.conf:ro
    networks:
      - caeli-internal
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1G

  backend:
    image: ghcr.io/caeli-wind/caelichrawler-backend:${VERSION:-latest}
    container_name: caeli-backend
    restart: always
    environment:
      - APP_ENV=production
      - DEBUG=false
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_APP_USER}:${POSTGRES_APP_PASSWORD}@postgres:5432/caelichrawler_prod
      - DATABASE_SYNC_URL=postgresql+psycopg://${POSTGRES_APP_USER}:${POSTGRES_APP_PASSWORD}@postgres:5432/caelichrawler_prod
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/2
      - CORS_ORIGINS=["https://app.caeli-wind.de"]
      - FRONTEND_URL=https://app.caeli-wind.de
      # Azure OpenAI
      - AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}
      - AZURE_OPENAI_API_KEY=${AZURE_OPENAI_API_KEY}
      # ... weitere Secrets
    volumes:
      - document_storage:/app/storage/documents
      - attachment_storage:/app/storage/attachments
    networks:
      - caeli-internal
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 2G
    # Security: Non-root user
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true

  celery-worker:
    image: ghcr.io/caeli-wind/caelichrawler-backend:${VERSION:-latest}
    container_name: caeli-worker
    restart: always
    command: celery -A workers.celery_app worker --loglevel=info -Q default,processing --concurrency=4
    environment:
      # Gleiche wie backend
      - APP_ENV=production
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_APP_USER}:${POSTGRES_APP_PASSWORD}@postgres:5432/caelichrawler_prod
      # ...
    volumes:
      - document_storage:/app/storage/documents
      - attachment_storage:/app/storage/attachments
    networks:
      - caeli-internal
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        limits:
          memory: 2G
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true

  celery-worker-crawl:
    image: ghcr.io/caeli-wind/caelichrawler-backend:${VERSION:-latest}
    container_name: caeli-worker-crawl
    restart: always
    command: celery -A workers.celery_app worker --loglevel=info -Q crawl --concurrency=8
    # ... (analog zu celery-worker)

  celery-worker-ai:
    image: ghcr.io/caeli-wind/caelichrawler-backend:${VERSION:-latest}
    container_name: caeli-worker-ai
    restart: always
    command: celery -A workers.celery_app worker --loglevel=info -Q ai --concurrency=2
    # ... (analog zu celery-worker)

  celery-beat:
    image: ghcr.io/caeli-wind/caelichrawler-backend:${VERSION:-latest}
    container_name: caeli-beat
    restart: always
    command: celery -A workers.celery_app beat --loglevel=info
    # ...

  frontend:
    image: ghcr.io/caeli-wind/caelichrawler-frontend:${VERSION:-latest}
    container_name: caeli-frontend
    restart: always
    networks:
      - caeli-internal
    # Nur intern, Nginx macht die Exposition
    deploy:
      resources:
        limits:
          memory: 512M
    read_only: true
    security_opt:
      - no-new-privileges:true

networks:
  caeli-internal:
    driver: bridge
    internal: false  # Für ausgehende Requests (Crawling)

volumes:
  postgres_data:
  redis_data:
  document_storage:
  attachment_storage:
```

### Dockerfile Optimierungen für Production

```dockerfile
# backend/Dockerfile.prod
FROM python:3.12-slim AS builder

WORKDIR /app

# Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim

# Non-root user erstellen
RUN groupadd -r caeli && useradd -r -g caeli caeli

WORKDIR /app

# Dependencies vom Builder kopieren
COPY --from=builder /root/.local /home/caeli/.local
ENV PATH=/home/caeli/.local/bin:$PATH

# App-Code kopieren
COPY --chown=caeli:caeli . .

# Security: Keine Shell, kein root
USER caeli

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 6. Reverse Proxy & SSL

### Nginx Konfiguration

```nginx
# /etc/nginx/sites-available/caelichrawler

# Rate Limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=1r/s;

# Upstream definitions
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream frontend {
    server 127.0.0.1:5173;
    keepalive 16;
}

# HTTP -> HTTPS Redirect
server {
    listen 80;
    listen [::]:80;
    server_name app.caeli-wind.de;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name app.caeli-wind.de;

    # SSL Zertifikate (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/app.caeli-wind.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.caeli-wind.de/privkey.pem;

    # SSL Konfiguration (modern)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 1.1.1.1 8.8.8.8 valid=300s;
    resolver_timeout 5s;

    # Security Headers (zusätzlich zu Backend-Headers)
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    # Logging
    access_log /var/log/nginx/caelichrawler_access.log;
    error_log /var/log/nginx/caelichrawler_error.log;

    # Request Limits
    client_max_body_size 25M;
    client_body_timeout 60s;
    client_header_timeout 60s;

    # API Endpoints
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffer settings
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Login Endpoint (strengeres Rate Limiting)
    location /api/auth/login {
        limit_req zone=login_limit burst=5 nodelay;

        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health Check (kein Rate Limiting)
    location /health {
        proxy_pass http://backend;
        access_log off;
    }

    # Frontend (Static Files)
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Cache für Static Assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            proxy_pass http://frontend;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
    }
}
```

### SSL-Zertifikat mit Certbot

```bash
# Certbot installieren
sudo apt install certbot python3-certbot-nginx

# Zertifikat anfordern
sudo certbot --nginx -d app.caeli-wind.de

# Auto-Renewal testen
sudo certbot renew --dry-run

# Cron für Auto-Renewal (wird automatisch erstellt)
# 0 0,12 * * * root certbot renew --quiet
```

---

## 7. Environment-Variablen

### .env.production Template

```bash
# ===========================================
# CaeliCrawler Production Environment
# ===========================================
# WARNUNG: Diese Datei niemals committen!
# Kopieren nach .env und Werte anpassen

# =====================
# Application
# =====================
APP_NAME=CaeliCrawler
APP_ENV=production
DEBUG=false
FRONTEND_URL=https://app.caeli-wind.de

# WICHTIG: Sicheren Key generieren mit:
# python -c "import secrets; print(secrets.token_urlsafe(64))"
SECRET_KEY=<GENERIERTER_KEY_MIN_64_ZEICHEN>

# =====================
# Database (getrennte User!)
# =====================
POSTGRES_ADMIN_USER=caelichrawler_admin
POSTGRES_ADMIN_PASSWORD=<SICHERES_ADMIN_PASSWORT>
POSTGRES_APP_USER=caelichrawler_app
POSTGRES_APP_PASSWORD=<SICHERES_APP_PASSWORT>

# =====================
# Redis
# =====================
REDIS_PASSWORD=<SICHERES_REDIS_PASSWORT>

# =====================
# CORS (nur Production-Domain!)
# =====================
CORS_ORIGINS=["https://app.caeli-wind.de"]

# =====================
# SMTP / Email
# =====================
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=<SMTP_USER>
SMTP_PASSWORD=<SMTP_PASSWORD>
SMTP_FROM_EMAIL=noreply@caeli-wind.de
SMTP_FROM_NAME=CaeliCrawler
SMTP_USE_TLS=true
SMTP_USE_SSL=false

# =====================
# Azure OpenAI (GPT für Analyse)
# =====================
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_KEY=<API_KEY>
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1-mini
AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT=text-embedding-3-large

# =====================
# Azure Document Intelligence (PDF-Verarbeitung)
# =====================
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=<API_KEY>

# =====================
# Anthropic/Claude (AI Source Discovery)
# =====================
ANTHROPIC_API_ENDPOINT=https://your-azure-anthropic-endpoint.ai.azure.com/anthropic/v1/messages
ANTHROPIC_API_KEY=<API_KEY>
ANTHROPIC_MODEL=claude-opus-4-5
AI_DISCOVERY_USE_CLAUDE=true

# =====================
# Web Search APIs (für AI Source Discovery)
# =====================
# SerpAPI (Google Search)
SERPAPI_API_KEY=<SERPAPI_KEY>
# Serper.dev (Alternative)
SERPER_API_KEY=<SERPER_KEY>

# =====================
# PySis Integration
# =====================
PYSIS_API_BASE_URL=https://pisys.caeli-wind.de/api/pisys/v1
PYSIS_TENANT_ID=<TENANT_ID>
PYSIS_CLIENT_ID=<CLIENT_ID>
PYSIS_CLIENT_SECRET=<CLIENT_SECRET>
PYSIS_SCOPE=api://xxxxx/.default

# =====================
# Caeli Auction API (Marketplace)
# =====================
CAELI_AUCTION_MARKETPLACE_API_URL=https://auction.caeli-wind.de/api/auction-platform/v4/public-marketplace
CAELI_AUCTION_MARKETPLACE_API_AUTH=<BASE64_AUTH>

# =====================
# Crawler Settings
# =====================
CRAWLER_USER_AGENT=CaeliCrawler/1.0 (Production; kontakt@caeli-wind.de)
CRAWLER_DEFAULT_DELAY=2.0
CRAWLER_MAX_CONCURRENT_REQUESTS=5
CRAWLER_RESPECT_ROBOTS_TXT=true

# =====================
# Storage
# =====================
DOCUMENT_STORAGE_PATH=/app/storage/documents
ATTACHMENT_STORAGE_PATH=/app/storage/attachments
ATTACHMENT_MAX_SIZE_MB=20
ATTACHMENT_ALLOWED_TYPES=image/png,image/jpeg,image/gif,image/webp,application/pdf

# =====================
# Logging
# =====================
LOG_LEVEL=INFO
LOG_FORMAT=json

# =====================
# Rate Limiting
# =====================
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10

# =====================
# Docker Image Version
# =====================
VERSION=1.0.0
```

### Secrets Management

**Empfohlen für Production:**

1. **Docker Secrets** (für Swarm):
```yaml
secrets:
  db_password:
    external: true

services:
  backend:
    secrets:
      - db_password
    environment:
      - DATABASE_PASSWORD_FILE=/run/secrets/db_password
```

2. **HashiCorp Vault** (Enterprise)

3. **AWS Secrets Manager / Azure Key Vault** (Cloud)

---

## 8. Sicherheitsmaßnahmen

### Checkliste Sicherheit

- [ ] **Netzwerk**
  - [ ] Firewall aktiv (UFW)
  - [ ] Nur Port 80/443 offen
  - [ ] SSH nur mit Key-Auth
  - [ ] Fail2ban konfiguriert

- [ ] **Datenbank**
  - [ ] App-User ohne SUPERUSER
  - [ ] Starke Passwörter
  - [ ] Keine externe Exposition
  - [ ] SSL für Verbindungen

- [ ] **Anwendung**
  - [ ] DEBUG=false
  - [ ] SECRET_KEY sicher (64+ Zeichen)
  - [ ] CORS auf Production-Domain beschränkt
  - [ ] Rate Limiting aktiv
  - [ ] Security Headers konfiguriert

- [ ] **Docker**
  - [ ] Keine privilegierten Container
  - [ ] Non-root User
  - [ ] Read-only Filesystem wo möglich
  - [ ] Resource Limits gesetzt

- [ ] **SSL/TLS**
  - [ ] TLS 1.2+ only
  - [ ] HSTS aktiviert
  - [ ] Zertifikat Auto-Renewal

- [ ] **Monitoring**
  - [ ] Log-Aggregation
  - [ ] Alerting für Fehler
  - [ ] Security-Event-Monitoring

### Automatische Security Updates

```bash
# unattended-upgrades konfigurieren
sudo dpkg-reconfigure -plow unattended-upgrades

# /etc/apt/apt.conf.d/50unattended-upgrades
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}";
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::AutoFixInterruptedDpkg "true";
Unattended-Upgrade::MinimalSteps "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
Unattended-Upgrade::Automatic-Reboot "false";
```

---

## 9. Monitoring & Logging

### Log-Aggregation mit Loki + Grafana

```yaml
# docker-compose.monitoring.yml
services:
  loki:
    image: grafana/loki:latest
    container_name: loki
    volumes:
      - loki_data:/loki
    networks:
      - monitoring

  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    volumes:
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./config/promtail.yml:/etc/promtail/config.yml:ro
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    networks:
      - monitoring

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./config/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    networks:
      - monitoring
```

### Health Check Endpoint

Das Backend stellt `/health` bereit:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2025-12-21T12:00:00Z"
}
```

### Alerting

```yaml
# alertmanager.yml
route:
  receiver: 'slack'
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/xxx'
        channel: '#alerts'
        send_resolved: true
```

---

## 10. Backup-Strategie

### Automatische Datenbank-Backups

```bash
#!/bin/bash
# /opt/scripts/backup-postgres.sh

BACKUP_DIR="/opt/backups/postgres"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/caelichrawler_${TIMESTAMP}.sql.gz"

# Backup erstellen
docker exec caeli-postgres pg_dump -U caelichrawler_admin caelichrawler_prod | gzip > "${BACKUP_FILE}"

# Alte Backups löschen
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +${RETENTION_DAYS} -delete

# Optional: Upload zu S3/B2
# aws s3 cp "${BACKUP_FILE}" s3://caeli-backups/postgres/
```

```bash
# Crontab
0 2 * * * /opt/scripts/backup-postgres.sh >> /var/log/backup.log 2>&1
```

### Volume Backups

```bash
#!/bin/bash
# /opt/scripts/backup-volumes.sh

BACKUP_DIR="/opt/backups/volumes"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Document Storage
docker run --rm -v caelichrawler_document_storage:/data -v ${BACKUP_DIR}:/backup \
    alpine tar czf /backup/documents_${TIMESTAMP}.tar.gz -C /data .

# Attachment Storage
docker run --rm -v caelichrawler_attachment_storage:/data -v ${BACKUP_DIR}:/backup \
    alpine tar czf /backup/attachments_${TIMESTAMP}.tar.gz -C /data .
```

### Restore-Prozedur

```bash
# Datenbank wiederherstellen
gunzip -c backup.sql.gz | docker exec -i caeli-postgres psql -U caelichrawler_admin caelichrawler_prod

# Volume wiederherstellen
docker run --rm -v caelichrawler_document_storage:/data -v /opt/backups:/backup \
    alpine tar xzf /backup/documents_20251221.tar.gz -C /data
```

---

## 11. CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Run Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest --cov=app tests/

  build:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push Backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          file: ./backend/Dockerfile.prod
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.ref_name }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:latest

      - name: Build and Push Frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          file: ./frontend/Dockerfile.prod
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.ref_name }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Deploy to Server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.PRODUCTION_HOST }}
          username: ${{ secrets.PRODUCTION_USER }}
          key: ${{ secrets.PRODUCTION_SSH_KEY }}
          script: |
            cd /opt/caelichrawler
            docker-compose -f docker-compose.prod.yml pull
            docker-compose -f docker-compose.prod.yml up -d
            docker system prune -f
```

### Deployment Script

```bash
#!/bin/bash
# /opt/caelichrawler/deploy.sh

set -e

VERSION=${1:-latest}
COMPOSE_FILE="docker-compose.prod.yml"

echo "Deploying CaeliCrawler version: ${VERSION}"

# Pull new images
docker-compose -f ${COMPOSE_FILE} pull

# Run migrations (mit Admin-User)
docker-compose -f ${COMPOSE_FILE} run --rm \
    -e DATABASE_URL="postgresql+psycopg://${POSTGRES_ADMIN_USER}:${POSTGRES_ADMIN_PASSWORD}@postgres:5432/caelichrawler_prod" \
    backend alembic upgrade head

# Restart services (zero-downtime)
docker-compose -f ${COMPOSE_FILE} up -d --no-deps --scale backend=2 backend
sleep 10
docker-compose -f ${COMPOSE_FILE} up -d --no-deps --scale backend=1 backend

# Cleanup
docker system prune -f

echo "Deployment complete!"
```

---

## 12. Checklisten

### Pre-Deployment Checklist

- [ ] Alle Tests bestanden
- [ ] Security-Scan durchgeführt (Trivy, Snyk)
- [ ] Datenbank-Migration getestet
- [ ] Backup vor Deployment erstellt
- [ ] Rollback-Plan dokumentiert
- [ ] Monitoring-Alerts konfiguriert

### Post-Deployment Checklist

- [ ] Health-Check erfolgreich
- [ ] Smoke Tests bestanden
- [ ] Logs auf Fehler geprüft
- [ ] Performance-Metriken normal
- [ ] SSL-Zertifikat gültig
- [ ] Alle Services laufen

### Rollback-Prozedur

```bash
#!/bin/bash
# /opt/caelichrawler/rollback.sh

PREVIOUS_VERSION=${1}

if [ -z "$PREVIOUS_VERSION" ]; then
    echo "Usage: ./rollback.sh <version>"
    exit 1
fi

echo "Rolling back to version: ${PREVIOUS_VERSION}"

# Set version
export VERSION=${PREVIOUS_VERSION}

# Pull and restart
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Optional: Datenbank-Rollback (wenn nötig)
# alembic downgrade -1

echo "Rollback complete!"
```

---

## Anhang: Schnellstart-Befehle

### Server Initial Setup
```bash
# Als root auf neuem Server
curl -sSL https://raw.githubusercontent.com/caeli-wind/caelichrawler/main/scripts/setup-server.sh | bash
```

### Deployment
```bash
cd /opt/caelichrawler
./deploy.sh v1.2.3
```

### Logs anzeigen
```bash
docker-compose -f docker-compose.prod.yml logs -f --tail=100 backend
```

### DB-Shell
```bash
docker exec -it caeli-postgres psql -U caelichrawler_app caelichrawler_prod
```

### Backup manuell
```bash
/opt/scripts/backup-postgres.sh
```

---

## 13. iOS App Deployment

Die iOS App befindet sich in einem separaten Repository und kommuniziert ausschließlich über die REST API.

### API-Konfiguration in der iOS App

Die App unterstützt Environment-Switching:

```swift
// Environment.swift
enum AppEnvironment {
    case development  // http://localhost:8000/api
    case production   // https://api.caeli-wind.de/api
}
```

### Push Notifications (APNs)

Für Push Notifications werden Device Tokens im Backend gespeichert:

```bash
# Backend Environment für APNs
APNS_KEY_ID=<KEY_ID>
APNS_TEAM_ID=<TEAM_ID>
APNS_BUNDLE_ID=de.caeli-wind.crawler
APNS_USE_SANDBOX=false  # true für Development
```

### App Store Deployment

1. **Certificates & Provisioning:**
   - Apple Developer Account
   - Distribution Certificate
   - App Store Provisioning Profile

2. **Build Settings:**
   ```
   PRODUCT_BUNDLE_IDENTIFIER = de.caeli-wind.crawler
   MARKETING_VERSION = 1.0.0
   CURRENT_PROJECT_VERSION = 1
   ```

3. **App Store Connect:**
   - App erstellen
   - Screenshots & Metadata
   - TestFlight für Beta-Testing
   - Review einreichen

### iOS-spezifische API-Endpoints

Die iOS App nutzt primär:
- `POST /api/auth/login` - Authentifizierung
- `POST /api/auth/device-token` - Push Token registrieren
- `GET /api/v1/entities` - Entity-Liste
- `GET /api/v1/dashboard/*` - Dashboard-Daten
- `GET /api/v1/favorites` - Favoriten
- `GET /api/admin/notifications/*` - Benachrichtigungen

---

## 14. Celery Worker Konfiguration

### Worker-Queues Übersicht

| Queue | Worker | Concurrency | Aufgaben |
|-------|--------|-------------|----------|
| `default` | celery-worker | 4 | Allgemeine Tasks, Notifications |
| `processing` | celery-worker | 4 | Dokument-Verarbeitung |
| `crawl` | celery-worker-crawl | 8 | Web-Crawling |
| `ai` | celery-worker-ai | 2 | AI-Analyse (Rate Limited) |

### Task-Routing

```python
# celery_app.py
task_routes = {
    'workers.crawl_tasks.*': {'queue': 'crawl'},
    'workers.ai_tasks.*': {'queue': 'ai'},
    'workers.processing_tasks.*': {'queue': 'processing'},
    'workers.notification_tasks.*': {'queue': 'default'},
}
```

### Scaling-Empfehlungen

```yaml
# Production Scaling
celery-worker:
  replicas: 2
  concurrency: 4
  # = 8 parallele Default/Processing Tasks

celery-worker-crawl:
  replicas: 2
  concurrency: 8
  # = 16 parallele Crawl Tasks

celery-worker-ai:
  replicas: 1
  concurrency: 2
  # = 2 parallele AI Tasks (API Rate Limits!)
```

### Celery Beat Schedule

```python
# Automatische Tasks
# HINWEIS: Automatische Crawls nur für Kategorien mit schedule_enabled=True
beat_schedule = {
    'check-scheduled-crawls': {
        'task': 'workers.crawl_tasks.check_scheduled_crawls',
        'schedule': timedelta(seconds=30),  # Nur Kategorien mit schedule_enabled=True
    },
    'process-pending-documents': {
        'task': 'workers.processing_tasks.process_pending_documents',
        'schedule': crontab(minute='*/5'),  # Alle 5 Min
    },
    'cleanup-old-jobs': {
        'task': 'workers.crawl_tasks.cleanup_old_jobs',
        'schedule': crontab(hour=3, minute=0),  # Täglich 3:00
    },
    'send-pending-notifications': {
        'task': 'workers.notification_tasks.send_pending',
        'schedule': crontab(minute='*/2'),  # Alle 2 Min
    },
    'process-notification-digests': {
        'task': 'workers.notification_tasks.process_digests',
        'schedule': crontab(hour='*/1', minute=0),  # Stündlich
    },
}
```

---

## 15. Externe API-Integrationen

### Übersicht aller APIs

| API | Zweck | Rate Limits |
|-----|-------|-------------|
| **Azure OpenAI** | Text-Analyse, Extraktion | ~60 RPM |
| **Azure Doc Intelligence** | PDF-OCR | ~15 RPM |
| **Anthropic/Claude** | AI Source Discovery | ~50 RPM |
| **SerpAPI** | Google-Suche | 100/Monat (Free) |
| **Serper** | Google-Suche Alternative | 2500/Monat |
| **PySis** | Windprojekt-Daten | - |
| **Caeli Auction** | Marketplace-Daten | - |

### API Health Monitoring

```python
# Health-Check für externe APIs
async def check_external_apis():
    results = {
        'azure_openai': await check_azure_openai(),
        'pysis': await check_pysis_api(),
        'serpapi': await check_serpapi(),
    }
    return results
```

### Fallback-Strategien

- **SerpAPI → Serper**: Automatischer Fallback bei Quota-Überschreitung
- **Azure OpenAI**: Retry mit Exponential Backoff
- **PySis**: Cache für 1 Stunde

---

## 16. Wartung & Troubleshooting

### Häufige Probleme

#### 1. Celery Worker hängt
```bash
# Worker neu starten
docker-compose restart celery-worker celery-worker-crawl celery-worker-ai

# Queue leeren (Vorsicht!)
docker exec caeli-redis redis-cli -a $REDIS_PASSWORD FLUSHDB
```

#### 2. Datenbank-Verbindungen erschöpft
```sql
-- Aktive Verbindungen prüfen
SELECT count(*) FROM pg_stat_activity WHERE datname = 'caelichrawler_prod';

-- Idle Verbindungen beenden
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'caelichrawler_prod'
  AND state = 'idle'
  AND state_change < now() - interval '10 minutes';
```

#### 3. Redis Memory voll
```bash
# Memory-Info
docker exec caeli-redis redis-cli -a $REDIS_PASSWORD INFO memory

# Alte Keys löschen
docker exec caeli-redis redis-cli -a $REDIS_PASSWORD --scan --pattern "rate_limit:*" | xargs -I{} docker exec caeli-redis redis-cli -a $REDIS_PASSWORD DEL {}
```

#### 4. Crawl-Jobs bleiben stecken
```sql
-- Stuck Jobs finden
SELECT id, source_id, status, started_at
FROM crawl_jobs
WHERE status = 'RUNNING'
  AND started_at < now() - interval '2 hours';

-- Manuell auf FAILED setzen
UPDATE crawl_jobs SET status = 'FAILED', error_log = 'Timeout - manuell beendet'
WHERE id = '<job_id>';
```

### Log-Analyse

```bash
# Backend-Fehler der letzten Stunde
docker logs caeli-backend --since 1h 2>&1 | grep -i error

# Crawl-Statistiken
docker logs caeli-worker-crawl --since 24h 2>&1 | grep -c "Task completed"

# AI-Task Errors
docker logs caeli-worker-ai --since 24h 2>&1 | grep -i "rate limit\|quota"
```

### Performance-Optimierung

```sql
-- Langsame Queries finden
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Index-Nutzung prüfen
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Tabellen-Bloat prüfen
SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::regclass)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;
```

---

**Letzte Aktualisierung:** 2025-12-21
**Version:** 1.1
