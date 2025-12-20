# Prometheus/Grafana Monitoring

Dieses Modul stellt Prometheus-Metriken für das CaeliCrawler-System bereit.

## Übersicht

Das Monitoring-System erfasst Metriken für:
- **Crawler Jobs**: Anzahl, Dauer, Status, Fehler
- **Document Processing**: Verarbeitung, Dauer, Queue-Länge
- **AI Analysis**: Analyse-Tasks, Dauer, Token-Verbrauch

## Installation

### Abhängigkeiten

```bash
pip install prometheus-client
```

### FastAPI Integration

Die Metriken werden automatisch beim Start der Anwendung registriert.
Der `/metrics` Endpoint ist unter `http://localhost:8000/metrics` verfügbar.

## Verfügbare Metriken

### Crawler Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `crawler_jobs_total` | Counter | source_type, status | Gesamtzahl der Crawler-Jobs |
| `crawler_jobs_running` | Gauge | source_type | Aktuell laufende Jobs |
| `crawler_pages_crawled_total` | Counter | source_type | Gecrawlte Seiten |
| `crawler_documents_found_total` | Counter | source_type, document_type | Gefundene Dokumente |
| `crawler_errors_total` | Counter | source_type, error_type | Crawler-Fehler |
| `crawler_job_duration_seconds` | Histogram | source_type | Job-Dauer in Sekunden |

### Document Processing Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `documents_processed_total` | Counter | document_type, status | Verarbeitete Dokumente |
| `documents_processing_duration_seconds` | Histogram | document_type | Verarbeitungsdauer |
| `documents_pending_count` | Gauge | status | Wartende Dokumente |

### AI Analysis Metriken

| Metrik | Typ | Labels | Beschreibung |
|--------|-----|--------|--------------|
| `ai_analysis_total` | Counter | status | AI-Analyse-Tasks |
| `ai_analysis_duration_seconds` | Histogram | - | Analyse-Dauer |
| `ai_analysis_errors_total` | Counter | error_type | Analyse-Fehler |
| `ai_tokens_used_total` | Counter | model, token_type | Verbrauchte Tokens |

## Verwendung im Code

### Context Manager für Crawler Jobs

```python
from app.monitoring import track_crawler_job

with track_crawler_job("WEBSITE") as tracker:
    # Crawl durchführen...
    tracker.set_pages(10)
    tracker.set_documents(5)
```

### Context Manager für Document Processing

```python
from app.monitoring import track_document_processing

with track_document_processing("PDF"):
    # Dokument verarbeiten...
```

### Context Manager für AI Analysis

```python
from app.monitoring import track_ai_analysis

with track_ai_analysis():
    # AI-Analyse durchführen...
```

### Direkte Metrik-Nutzung

```python
from app.monitoring import (
    crawler_jobs_total,
    crawler_errors_total,
    documents_pending_count,
)

# Counter inkrementieren
crawler_jobs_total.labels(source_type="WEBSITE", status="completed").inc()

# Fehler zählen
crawler_errors_total.labels(source_type="OPARL_API", error_type="timeout").inc()

# Gauge setzen
documents_pending_count.labels(status="pending").set(42)
```

## Prometheus Konfiguration

Fügen Sie folgende Konfiguration zu `prometheus.yml` hinzu:

```yaml
scrape_configs:
  - job_name: 'caeli-crawler'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

## Grafana Dashboard

Ein vorkonfiguriertes Dashboard ist verfügbar unter:
`backend/app/monitoring/grafana_dashboard.json`

### Dashboard importieren

1. Öffnen Sie Grafana
2. Gehen Sie zu **Dashboards** → **Import**
3. Laden Sie die `grafana_dashboard.json` Datei hoch
4. Wählen Sie Ihre Prometheus-Datenquelle

### Dashboard-Panels

1. **Crawler Overview**
   - Running Jobs (aktuell)
   - Jobs (24h)
   - Documents Found (24h)
   - Errors (24h)

2. **Jobs per Source Type**
   - Rate der Jobs nach Quelltyp (WEBSITE, OPARL_API, RSS, etc.)

3. **Job Duration**
   - 95. Perzentil der Job-Dauer pro Quelltyp

4. **Document Processing**
   - Pending Documents by Status
   - Documents Processed Rate

5. **AI Analysis**
   - Analysis Rate (erfolg/fehlgeschlagen)
   - Analysis Duration (p50, p95, p99)

## Alerting

Beispiel-Alert-Regeln für Prometheus:

```yaml
groups:
  - name: crawler_alerts
    rules:
      - alert: HighCrawlerErrorRate
        expr: rate(crawler_errors_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High crawler error rate"
          description: "Crawler error rate is {{ $value }} errors/second"

      - alert: CrawlerJobTimeout
        expr: histogram_quantile(0.95, rate(crawler_job_duration_seconds_bucket[5m])) > 3600
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Crawler jobs taking too long"
          description: "95th percentile job duration is {{ $value }} seconds"

      - alert: HighPendingDocuments
        expr: documents_pending_count{status="pending"} > 1000
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "High number of pending documents"
          description: "{{ $value }} documents pending processing"
```

## Troubleshooting

### Metriken nicht verfügbar

1. Prüfen Sie, ob `prometheus-client` installiert ist
2. Prüfen Sie, ob der `/metrics` Endpoint erreichbar ist
3. Prüfen Sie die Logs auf Import-Fehler

### Keine Daten in Grafana

1. Prüfen Sie die Prometheus-Datenquelle in Grafana
2. Prüfen Sie, ob Prometheus die Metriken scraped (`http://prometheus:9090/targets`)
3. Prüfen Sie den Zeitbereich im Dashboard

## Entwicklung

### Neue Metrik hinzufügen

1. Definieren Sie die Metrik in `metrics.py`:

```python
my_new_counter = Counter(
    "my_new_counter_total",
    "Description of the metric",
    ["label1", "label2"],
)
```

2. Exportieren Sie in `__init__.py`:

```python
from .metrics import my_new_counter
```

3. Verwenden Sie die Metrik im Code:

```python
from app.monitoring import my_new_counter
my_new_counter.labels(label1="value1", label2="value2").inc()
```
