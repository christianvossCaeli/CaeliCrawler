# HelpView.vue i18n Translation Keys (Lines 1-800)

## Summary of Translations Done
The following sections have been successfully translated to use i18n keys:
- Main page title
- Introduction section (including main functions table and workflow stepper)
- Quickstart section (all 4 steps with detailed instructions)
- Dashboard section (complete with stats cards, live updates, quick actions, and crawler dialog)
- Smart Query section (title, alert, modes comparison, and setup stepper)

## Remaining Translations Needed (Lines 317-800)

### Smart Query - Expansion Panels

**EntityType Generation Panel:**
```
Schritt 1: EntityType-Generierung → help.smart_query.expansion.entity_type.title
Die KI erstellt einen neuen EntityType mit: → help.smart_query.expansion.entity_type.description
Name & Beschreibung → help.smart_query.expansion.entity_type.items.name.title
Passend zur Anfrage → help.smart_query.expansion.entity_type.items.name.description
Attribute-Schema → help.smart_query.expansion.entity_type.items.schema.title
Relevante Felder fuer die Extraktion → help.smart_query.expansion.entity_type.items.schema.description
Icon & Farbe → help.smart_query.expansion.entity_type.items.icon.title
Fuer die UI-Darstellung → help.smart_query.expansion.entity_type.items.icon.description
Search Focus → help.smart_query.expansion.entity_type.items.search_focus.title
event_attendance, pain_points, contacts, etc. → help.smart_query.expansion.entity_type.items.search_focus.description
```

**Category Generation Panel:**
```
Schritt 2: Category-Generierung → help.smart_query.expansion.category.title
Die KI erstellt eine Category mit: → help.smart_query.expansion.category.description
AI-Extraktions-Prompt → help.smart_query.expansion.category.items.prompt.title
Massgeschneidert fuer die Anfrage → help.smart_query.expansion.category.items.prompt.description
Suchbegriffe → help.smart_query.expansion.category.items.keywords.title
Erweitert (z.B. "Entscheider" → Buergermeister, Landrat, etc.) → help.smart_query.expansion.category.items.keywords.description
Verknuepfung zum EntityType → help.smart_query.expansion.category.items.link.title
Extrahierte Daten werden als Entities gespeichert → help.smart_query.expansion.category.items.link.description
```

**Crawl Config Panel:**
```
Schritt 3: Crawl-Konfiguration → help.smart_query.expansion.crawl_config.title
Die KI generiert URL-Filter: → help.smart_query.expansion.crawl_config.description
Exclude-Patterns (Blacklist) → help.smart_query.expansion.crawl_config.items.exclude.title
Irrelevante Seiten ausschliessen → help.smart_query.expansion.crawl_config.items.exclude.description
Datenquellen-Verknuepfung → help.smart_query.expansion.crawl_config.items.link_sources.title
Basierend auf geografischem Filter (z.B. NRW) → help.smart_query.expansion.crawl_config.items.link_sources.description
Wichtig: → help.smart_query.expansion.crawl_config.note.title
Die KI generiert keine Include-Patterns (Whitelist). Der Crawler besucht alle Seiten und die KI filtert relevante Inhalte. → help.smart_query.expansion.crawl_config.note.description
```

### Smart Query - Workflow Timeline
```
Workflow: Schreib-Modus → help.smart_query.workflow_title
Anfrage eingeben → help.smart_query.workflow.step1.title
Beschreiben Sie in natuerlicher Sprache was Sie suchen/ueberwachen moechten. → help.smart_query.workflow.step1.description
Schreib-Modus aktivieren → help.smart_query.workflow.step2.title
Schalten Sie den Toggle auf "Schreib-Modus" um. → help.smart_query.workflow.step2.description
Vorschau pruefen → help.smart_query.workflow.step3.title
Klicken Sie "Vorschau" um zu sehen was erstellt wird (EntityType, Category, Datenquellen). → help.smart_query.workflow.step3.description
Bestaetigen → help.smart_query.workflow.step4.title
Klicken Sie "Bestaetigen & Erstellen". Die 3-Schritt-KI-Generierung startet. → help.smart_query.workflow.step4.description
Crawl starten → help.smart_query.workflow.step5.title
Nach Erstellung koennen Sie direkt den Crawl fuer die neue Category starten. → help.smart_query.workflow.step5.description
```

### Smart Query - Geographic Filters
```
Geografische Filter → help.smart_query.geo_filters_title
Smart Query versteht geografische Begriffe und Abkuerzungen: → help.smart_query.geo_filters_description
Eingabe → help.smart_query.geo_filters.table.input
Wird erkannt als → help.smart_query.geo_filters.table.recognized
```

### Smart Query - Example Queries
```
Beispiel-Anfragen → help.smart_query.examples_title
Anfrage → help.smart_query.examples.table.query
Modus → help.smart_query.examples.table.mode
Ergebnis → help.smart_query.examples.table.result
Lesen → help.smart_query.examples.mode.read
Schreiben → help.smart_query.examples.mode.write
```

### Categories Section
```
Kategorien → help.categories.title
Kategorien sind die oberste Organisationsebene und definieren, was gesucht wird und wie die Ergebnisse analysiert werden. → help.categories.description
Grundeinstellungen → help.categories.basic_settings.title
Feld → help.categories.basic_settings.table.field
Beschreibung → help.categories.basic_settings.table.description
Beispiel → help.categories.basic_settings.table.example
Name → help.categories.basic_settings.fields.name.label
Eindeutiger Name → help.categories.basic_settings.fields.name.description
"Windenergie-Beschlüsse" → help.categories.basic_settings.fields.name.example
Beschreibung → help.categories.basic_settings.fields.description.label
Optionale Erläuterung → help.categories.basic_settings.fields.description.description
"Sammelt alle Ratsbeschlüsse" → help.categories.basic_settings.fields.description.example
Zweck → help.categories.basic_settings.fields.purpose.label
Was soll erreicht werden? → help.categories.basic_settings.fields.purpose.description
"Windkraft-Restriktionen analysieren" → help.categories.basic_settings.fields.purpose.example
Status → help.categories.basic_settings.fields.status.label
Aktiv/Inaktiv → help.categories.basic_settings.fields.status.description
Aktiv → help.categories.basic_settings.fields.status.example
Dokumenttypen → help.categories.basic_settings.fields.doc_types.label
Erwartete Typen zur Klassifizierung → help.categories.basic_settings.fields.doc_types.description
Beschluss, Protokoll, Satzung → help.categories.basic_settings.fields.doc_types.example
Zeitplan (Cron) → help.categories.basic_settings.fields.schedule.label
Automatischer Crawl-Zeitplan → help.categories.basic_settings.fields.schedule.description
"0 2 * * *" (täglich 2 Uhr) → help.categories.basic_settings.fields.schedule.example

Suchbegriffe (Keywords) → help.categories.keywords.title
Keywords für die Relevanz-Filterung: → help.categories.keywords.description
Dokumente werden nur zur KI-Analyse weitergeleitet, wenn sie mindestens 2 dieser Keywords enthalten. → help.categories.keywords.note

URL-Filter (Regex) → help.categories.url_filters.title
URL-Filter nutzen Regex-Patterns um zu steuern, welche URLs gecrawlt werden. Die KI-Filterung der Inhalte ersetzt weitgehend die URL-basierte Whitelist. → help.categories.url_filters.description
Exclude-Patterns (Blacklist) - Primär → help.categories.url_filters.exclude.title
URLs die ein Pattern matchen werden nicht gecrawlt: → help.categories.url_filters.exclude.description
Include-Patterns (Whitelist) - Optional → help.categories.url_filters.include.title
Nur URLs die mindestens ein Pattern matchen werden gecrawlt. Nur für manuelle Nutzung - Smart Query generiert keine Include-Patterns. → help.categories.url_filters.include.description
Empfehlung: → help.categories.url_filters.recommendation.title
Include-Patterns (Whitelist) leer lassen und stattdessen auf die KI-basierte Inhaltsfilterung vertrauen. Die Blacklist filtert technische und irrelevante Seiten aus. → help.categories.url_filters.recommendation.description

KI-Extraktions-Prompt → help.categories.ai_prompt.title
Definiert, was die KI extrahieren soll. Beispiel: → help.categories.ai_prompt.description

Aktionen → help.categories.actions.title
Aktion → help.categories.actions.table.action
Symbol → help.categories.actions.table.symbol
Beschreibung → help.categories.actions.table.description
Bearbeiten → help.categories.actions.edit
Einstellungen ändern → help.categories.actions.edit_desc
Crawlen → help.categories.actions.crawl
Crawl für alle Quellen starten → help.categories.actions.crawl_desc
Neu analysieren → help.categories.actions.reanalyze
Dokumente erneut durch KI → help.categories.actions.reanalyze_desc
Löschen → help.categories.actions.delete
Mit allen Daten löschen → help.categories.actions.delete_desc
```

### Sources Section
```
Datenquellen → help.sources.title
Datenquellen sind die konkreten Websites oder APIs, die gecrawlt werden. → help.sources.description

Kategorie-Zuordnung (N:M) → help.sources.category_mapping.title
Eine Datenquelle kann mehreren Kategorien zugeordnet werden (N:M-Beziehung). Beim Crawlen wird die Kategorie des Jobs verwendet, nicht die der Quelle. → help.sources.category_mapping.description
Mehrfachzuordnung → help.sources.category_mapping.items.multiple.title
Eine Quelle kann z.B. sowohl für "Windkraft" als auch "Solarenergie" relevant sein → help.sources.category_mapping.items.multiple.description
Crawl-Kontext → help.sources.category_mapping.items.context.title
Beim Crawlen wird der AI-Prompt und die Filter der gewählten Kategorie verwendet → help.sources.category_mapping.items.context.description
Smart Query Integration → help.sources.category_mapping.items.smart_query.title
Smart Query kann automatisch passende Quellen zu neuen Kategorien verknüpfen → help.sources.category_mapping.items.smart_query.description

Quellentypen → help.sources.source_types.title
WEBSITE → help.sources.source_types.website.label
Standard-Website-Crawling für kommunale Websites, Nachrichtenseiten → help.sources.source_types.website.description
OPARL_API → help.sources.source_types.oparl.label
OParl-Schnittstelle für Ratsinformationssysteme → help.sources.source_types.oparl.description
RSS → help.sources.source_types.rss.label
RSS-Feed für News-Aggregation → help.sources.source_types.rss.description

Verfügbare Filter → help.sources.filters_title
Land (mit Anzahl) → help.sources.filters.country
Gemeinde (Autocomplete) → help.sources.filters.municipality
Kategorie → help.sources.filters.category
Status → help.sources.filters.status
Suche (Name/URL) → help.sources.filters.search

Aktionen → help.sources.actions.title
Button → help.sources.actions.table.button
Beschreibung → help.sources.actions.table.description
Bulk Import → help.sources.actions.bulk_import
Mehrere Quellen per JSON importieren → help.sources.actions.bulk_import_desc
Neue Quelle → help.sources.actions.new_source
Einzelne Quelle manuell anlegen → help.sources.actions.new_source_desc
Bearbeiten → help.sources.actions.edit
Quelle bearbeiten → help.sources.actions.edit_desc
Crawlen → help.sources.actions.crawl
Crawl für diese Quelle starten → help.sources.actions.crawl_desc
Zurücksetzen → help.sources.actions.reset
Nur bei ERROR-Status: Quelle zurücksetzen → help.sources.actions.reset_desc
Löschen → help.sources.actions.delete
Quelle mit allen Dokumenten löschen → help.sources.actions.delete_desc

Formular-Felder (Neue/Bearbeiten) → help.sources.form_fields.title
Feld → help.sources.form_fields.table.field
Beschreibung → help.sources.form_fields.table.description
Pflicht → help.sources.form_fields.table.required
Kategorie → help.sources.form_fields.category.label
Zugehörige Kategorie (bei Edit nicht änderbar) → help.sources.form_fields.category.description
Ja → help.sources.form_fields.required.yes
Nein → help.sources.form_fields.required.no
Name → help.sources.form_fields.name.label
Anzeigename der Quelle → help.sources.form_fields.name.description
Quellentyp → help.sources.form_fields.source_type.label
WEBSITE, OPARL_API, RSS, CUSTOM_API → help.sources.form_fields.source_type.description
Basis-URL → help.sources.form_fields.base_url.label
Start-URL für den Crawler → help.sources.form_fields.base_url.description
API-Endpunkt → help.sources.form_fields.api_endpoint.label
Nur für OPARL_API/CUSTOM_API → help.sources.form_fields.api_endpoint.description
Land → help.sources.form_fields.country.label
Dropdown: DE, AT, CH, etc. → help.sources.form_fields.country.description
Ort → help.sources.form_fields.location.label
Autocomplete-Suche mit Location-Verknüpfung → help.sources.form_fields.location.description

Bulk Import → help.sources.bulk_import.title
Mehrere Quellen auf einmal importieren: → help.sources.bulk_import.description

Crawl-Konfiguration → help.sources.crawl_config.title
Einstellung → help.sources.crawl_config.table.setting
Beschreibung → help.sources.crawl_config.table.description
Standard → help.sources.crawl_config.table.default
Max. Tiefe → help.sources.crawl_config.max_depth.label
Wie viele Link-Ebenen verfolgen → help.sources.crawl_config.max_depth.description
3 → help.sources.crawl_config.max_depth.default
Max. Seiten → help.sources.crawl_config.max_pages.label
Maximale Anzahl zu crawlender Seiten → help.sources.crawl_config.max_pages.description
200 → help.sources.crawl_config.max_pages.default
Externe Links → help.sources.crawl_config.external_links.label
Links zu anderen Domains verfolgen → help.sources.crawl_config.external_links.description
Nein → help.sources.crawl_config.external_links.default
JavaScript rendern → help.sources.crawl_config.javascript.label
Playwright für dynamische Seiten → help.sources.crawl_config.javascript.description
Nein → help.sources.crawl_config.javascript.default
HTML-Capture → help.sources.crawl_config.html_capture.label
Relevante HTML-Seiten als Dokumente speichern → help.sources.crawl_config.html_capture.description
Ja → help.sources.crawl_config.html_capture.default

URL-Filter (Erweiterte Einstellungen) → help.sources.url_filters.title
URL-Filter sind Regex-Patterns. Die KI-Filterung der Inhalte macht eine strikte URL-Whitelist meist überflüssig. Stattdessen wird primär die Blacklist verwendet. → help.sources.url_filters.description
Exclude-Patterns (Blacklist) - Primär → help.sources.url_filters.exclude.title
URLs die ein Pattern matchen werden nicht gecrawlt: → help.sources.url_filters.exclude.description
Include-Patterns (Whitelist) - Optional → help.sources.url_filters.include.title
Nur für manuelle Nutzung. Smart Query generiert keine Include-Patterns. → help.sources.url_filters.include.description

Status-Bedeutung → help.sources.status_meaning.title
Status → help.sources.status_meaning.table.status
Bedeutung → help.sources.status_meaning.table.meaning
PENDING → help.sources.status_meaning.pending.label
Noch nie gecrawlt → help.sources.status_meaning.pending.description
CRAWLING → help.sources.status_meaning.crawling.label
Crawl läuft gerade → help.sources.status_meaning.crawling.description
ACTIVE → help.sources.status_meaning.active.label
Erfolgreich gecrawlt → help.sources.status_meaning.active.description
ERROR → help.sources.status_meaning.error.label
Letzter Crawl fehlgeschlagen → help.sources.status_meaning.error.description
```

### Crawler Section
```
Crawler Status → help.crawler.title
Die Crawler-Seite zeigt den Live-Status aller Crawling- und KI-Aktivitäten. → help.crawler.description

Status-Karten → help.crawler.status_cards.title
Aktive Worker → help.crawler.cards.workers.title
Verfügbare Prozesse → help.crawler.cards.workers.description
Laufende Jobs → help.crawler.cards.running.title
Aktive Crawls → help.crawler.cards.running.description
Wartende Jobs → help.crawler.cards.waiting.title
In der Queue → help.crawler.cards.waiting.description
Dokumente → help.crawler.cards.documents.title
Gesamt gefunden → help.crawler.cards.documents.description

KI-Aufgaben (Live) → help.crawler.ai_tasks_title
Zeigt laufende KI-Analysen mit: → help.crawler.ai_tasks_description
Task-Name und aktuelles Dokument → help.crawler.ai_tasks.task_name
Fortschrittsbalken (X/Y Dokumente) → help.crawler.ai_tasks.progress
Stopp Button zum Abbrechen → help.crawler.ai_tasks.stop

Aktive Crawler (Live) → help.crawler.active_crawlers_title
Expandierbare Panels für jeden laufenden Crawl: → help.crawler.active_crawlers_description
Quelle & aktuelle URL → help.crawler.active_crawlers.source_url
Seiten gecrawlt / Dokumente gefunden / Neue → help.crawler.active_crawlers.progress
Fehlerzähler (falls vorhanden) → help.crawler.active_crawlers.errors
Stopp Button zum sofortigen Abbruch → help.crawler.active_crawlers.stop

Live-Log (expandierbar) → help.crawler.live_log.title
Virtueller Scroll mit letzten Aktivitäten: URL besucht, Dokument gefunden, Fehler. Farbcodiert mit Timestamps. → help.crawler.live_log.description

Job-Tabelle → help.crawler.job_table.title
Spalte → help.crawler.job_table.table.column
Beschreibung → help.crawler.job_table.table.description
Quelle → help.crawler.job_table.columns.source
Name der gecrawlten Datenquelle → help.crawler.job_table.columns.source_desc
Status → help.crawler.job_table.columns.status
RUNNING, COMPLETED, FAILED, CANCELLED → help.crawler.job_table.columns.status_desc
Gestartet → help.crawler.job_table.columns.started
Startzeitpunkt des Jobs → help.crawler.job_table.columns.started_desc
Dauer → help.crawler.job_table.columns.duration
Laufzeit in Minuten/Stunden → help.crawler.job_table.columns.duration_desc
Fortschritt → help.crawler.job_table.columns.progress
Verarbeitete/Gefundene Dokumente mit Balken → help.crawler.job_table.columns.progress_desc
Aktionen → help.crawler.job_table.columns.actions
Stopp (bei RUNNING), Details → help.crawler.job_table.columns.actions_desc

Job-Details-Dialog → help.crawler.job_details.title
Klicken Sie auf das Info-Symbol für den vollständigen Job-Report: → help.crawler.job_details.description
Quelle & Kategorie → help.crawler.job_details.items.source
Status mit Farb-Chip → help.crawler.job_details.items.status
Dauer (formatiert) → help.crawler.job_details.items.duration
```

## Implementation Notes

1. All keys follow the pattern: `help.section.subsection.item`
2. Use nested keys for better organization
3. Keys with `.title` are headers/titles
4. Keys with `.description` are explanatory text
5. Keys with `.table.*` are table headers/columns
6. Keys with `.items.*` are list items
7. Use v-html for strings containing HTML elements (like `<strong>`, `<v-chip>`)

## File Status
- Lines 1-300: ✅ Completed
- Lines 300-800: ⏳ Keys documented, implementation in progress
