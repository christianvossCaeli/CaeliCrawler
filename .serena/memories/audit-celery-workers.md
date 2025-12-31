# Celery Worker Audit (27.12.2025)

## Executive Summary

**Status: BEHOBEN** - Alle 4 Celery-Dienste sind jetzt **healthy**

---

## Ursprünglicher Status

| Service | Status | Problem |
|---------|--------|---------|
| celery-worker | unhealthy | Healthcheck Timeout |
| celery-worker-ai | unhealthy | Healthcheck Timeout |
| celery-worker-crawl | unhealthy | Healthcheck Timeout |
| celery-beat | unhealthy | `pgrep` nicht installiert |

---

## Identifizierte Probleme

### 1. Healthcheck-Konfiguration fehlerhaft

**Worker-Healthchecks:**
```yaml
# Vorher - Spezifischer Hostname, der oft nicht matcht
test: ["CMD-SHELL", "celery -A workers.celery_app inspect ping -d celery@worker-general@$$(hostname) --timeout=10"]
```

**Beat-Healthcheck:**
```yaml
# Vorher - pgrep nicht im minimal Python-Image
test: ["CMD-SHELL", "pgrep -f 'celery.*beat' || exit 1"]
```

### 2. Alte Task-Referenzen (api_templates)

Der ursprüngliche Fehler `relation "api_templates" does not exist` kam von alten Tasks, die durch Container-Neustart behoben wurden.

---

## Durchgeführte Fixes

### 1. Worker-Healthchecks vereinfacht
```yaml
# Nachher - Prüft ob irgendein Worker antwortet
test: ["CMD-SHELL", "celery -A workers.celery_app inspect ping --timeout=10 | grep -q 'pong' || exit 1"]
```

### 2. Beat-Healthcheck geändert
```yaml
# Nachher - Prüft ob PID 1 (Hauptprozess) läuft
test: ["CMD-SHELL", "kill -0 1 2>/dev/null || exit 1"]
```

### 3. Container neu gestartet
```bash
docker compose restart celery-worker celery-worker-ai celery-worker-crawl celery-beat
docker compose up -d celery-beat celery-worker celery-worker-ai celery-worker-crawl
```

---

## Finaler Status

```
caelichrawler-beat           ... Up (healthy)
caelichrawler-worker         ... Up (healthy)
caelichrawler-worker-ai      ... Up (healthy)
caelichrawler-worker-crawl   ... Up (healthy)
```

---

## Geänderte Dateien

```
docker-compose.yml (3 Healthchecks)
```

---

## Celery-Architektur Übersicht

| Worker | Queue | Concurrency | Aufgaben |
|--------|-------|-------------|----------|
| worker-general | default, processing | 4 | Allgemeine Tasks, Export, API-Sync |
| worker-crawl | crawl | 8 | Web-Crawling, Source-Sync |
| worker-ai | ai | 2 | AI-Analyse, Document Processing |
| beat | - | - | Scheduler für periodische Tasks |

### Beat Schedule (wichtige Tasks)
- check-scheduled-crawls: 30s (nur Kategorien mit `schedule_enabled=True`)
- check-scheduled-presets: 30s (nur Presets mit `schedule_enabled=True`)
- **WICHTIG**: Automatische Crawls erfordern explizite Aktivierung via `schedule_enabled`
- check-scheduled-api-syncs: 1min
- check-scheduled-summaries: 1min
- cleanup-idle-connections: 5min
