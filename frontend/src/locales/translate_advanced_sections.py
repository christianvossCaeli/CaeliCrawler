#!/usr/bin/env python3
"""
Script to translate the advanced sections (API, Tips, Security, Troubleshooting)
in HelpView.vue to use i18n translation keys.
"""

import re

def translate_helpview():
    file_path = '/Users/christian.voss/PhpstormProjects/CaeliCrawler/CaeliCrawler/frontend/src/views/HelpView.vue'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Store original content for comparison
    original_content = content

    # API Section replacements
    print("Translating API section...")
    content = re.sub(
        r"{{ t\('help\.apiReference\.title'\) }}",
        "{{ t('help.api.title') }}",
        content
    )
    content = re.sub(
        r'Vollständige Liste aller API-Endpunkte\. Die interaktive API-Dokumentation \(Swagger/OpenAPI\)\s+ist unter <code>/docs</code> verfügbar\.',
        "{{ t('help.api.description') }}",
        content
    )

    # API Groups - Categories
    content = re.sub(
        r'<v-icon color="primary" class="mr-2">mdi-folder-multiple</v-icon>\s+Kategorien',
        '<v-icon color="primary" class="mr-2">mdi-folder-multiple</v-icon>\n                  {{ t(\'help.apiGroups.categories.title\') }}',
        content
    )
    content = re.sub(r'<td>Liste aller Kategorien</td>', '<td>{{ t(\'help.apiGroups.categories.endpoints.list\') }}</td>', content)
    content = re.sub(r'<td>Neue Kategorie erstellen</td>', '<td>{{ t(\'help.apiGroups.categories.endpoints.create\') }}</td>', content)
    content = re.sub(r'<td>Kategorie abrufen</td>', '<td>{{ t(\'help.apiGroups.categories.endpoints.get\') }}</td>', content)
    content = re.sub(r'<td>Kategorie aktualisieren</td>', '<td>{{ t(\'help.apiGroups.categories.endpoints.update\') }}</td>', content)
    content = re.sub(r'<td>Kategorie löschen</td>', '<td>{{ t(\'help.apiGroups.categories.endpoints.delete\') }}</td>', content)
    content = re.sub(r'<td>Kategorie-Statistiken</td>', '<td>{{ t(\'help.apiGroups.categories.endpoints.stats\') }}</td>', content)

    # API Groups - Sources
    content = re.sub(
        r'<v-icon color="teal" class="mr-2">mdi-web</v-icon>\s+Datenquellen',
        '<v-icon color="teal" class="mr-2">mdi-web</v-icon>\n                  {{ t(\'help.apiGroups.sources.title\') }}',
        content
    )
    content = re.sub(r'<td>Liste aller Quellen \(mit Filtern\)</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.list\') }}</td>', content)
    content = re.sub(r'<td>Neue Quelle erstellen</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.create\') }}</td>', content)
    content = re.sub(r'<td>Mehrere Quellen importieren</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.bulkImport\') }}</td>', content)
    content = re.sub(r'<td>Verfügbare Länder</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.countries\') }}</td>', content)
    content = re.sub(r'<td>Verfügbare Standorte</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.locations\') }}</td>', content)
    content = re.sub(r'<td>Quelle abrufen</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.get\') }}</td>', content)
    content = re.sub(r'<td>Quelle aktualisieren</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.update\') }}</td>', content)
    content = re.sub(r'<td>Quelle löschen</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.delete\') }}</td>', content)
    content = re.sub(r'<td>Quelle zurücksetzen</td>', '<td>{{ t(\'help.apiGroups.sources.endpoints.reset\') }}</td>', content)

    # API Groups - Crawler
    content = re.sub(
        r'<v-icon color="cyan" class="mr-2">mdi-robot</v-icon>\s+Crawler',
        '<v-icon color="cyan" class="mr-2">mdi-robot</v-icon>\n                  {{ t(\'help.apiGroups.crawler.title\') }}',
        content
    )
    content = re.sub(r'<td>Crawl starten</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.start\') }}</td>', content)
    content = re.sub(r'<td>Crawler-Status \(Worker, Queue\)</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.status\') }}</td>', content)
    content = re.sub(r'<td>Crawler-Statistiken</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.stats\') }}</td>', content)
    content = re.sub(r'<td>Laufende Jobs</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.running\') }}</td>', content)
    content = re.sub(r'<td>Alle Jobs \(mit Filtern\)</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.jobs\') }}</td>', content)
    content = re.sub(r'<td>Job-Details</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.jobDetails\') }}</td>', content)
    content = re.sub(r'<td>Job-Log</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.jobLog\') }}</td>', content)
    content = re.sub(r'<td>Job abbrechen</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.cancelJob\') }}</td>', content)
    content = re.sub(r'<td>Dokumente neu analysieren</td>', '<td>{{ t(\'help.apiGroups.crawler.endpoints.reanalyze\') }}</td>', content)

    # API Groups - AI Tasks
    content = re.sub(
        r'<v-icon color="purple" class="mr-2">mdi-brain</v-icon>\s+KI-Tasks & Dokumente',
        '<v-icon color="purple" class="mr-2">mdi-brain</v-icon>\n                  {{ t(\'help.apiGroups.aiTasks.title\') }}',
        content
    )
    content = re.sub(r'<td>Alle KI-Tasks</td>', '<td>{{ t(\'help.apiGroups.aiTasks.endpoints.list\') }}</td>', content)
    content = re.sub(r'<td>Laufende KI-Tasks</td>', '<td>{{ t(\'help.apiGroups.aiTasks.endpoints.running\') }}</td>', content)
    content = re.sub(r'<td>KI-Task abbrechen</td>', '<td>{{ t(\'help.apiGroups.aiTasks.endpoints.cancel\') }}</td>', content)
    content = re.sub(r'<td>Dokument verarbeiten</td>', '<td>{{ t(\'help.apiGroups.aiTasks.endpoints.processDocument\') }}</td>', content)
    content = re.sub(r'<td>Dokument analysieren</td>', '<td>{{ t(\'help.apiGroups.aiTasks.endpoints.analyzeDocument\') }}</td>', content)
    content = re.sub(r'<td>Alle Pending verarbeiten</td>', '<td>{{ t(\'help.apiGroups.aiTasks.endpoints.processPending\') }}</td>', content)
    content = re.sub(r'<td>Verarbeitung stoppen</td>', '<td>{{ t(\'help.apiGroups.aiTasks.endpoints.stopAll\') }}</td>', content)
    content = re.sub(r'<td>Gefilterte neu analysieren</td>', '<td>{{ t(\'help.apiGroups.aiTasks.endpoints.reanalyzeFiltered\') }}</td>', content)

    # API Groups - Locations
    content = re.sub(
        r'<v-icon color="indigo" class="mr-2">mdi-map-marker</v-icon>\s+Locations',
        '<v-icon color="indigo" class="mr-2">mdi-map-marker</v-icon>\n                  {{ t(\'help.apiGroups.locations.title\') }}',
        content
    )
    content = re.sub(r'<td>Alle Locations</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.list\') }}</td>', content)
    content = re.sub(r'<td>Einzelne Location abrufen</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.get\') }}</td>', content)
    content = re.sub(r'<td>Locations suchen</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.search\') }}</td>', content)
    content = re.sub(r'<td>Locations mit Quellen</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.withSources\') }}</td>', content)
    content = re.sub(r'<td>Bundesländer/States</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.states\') }}</td>', content)
    content = re.sub(r'<td>Admin-Levels \(Level 1/2\)</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.adminLevels\') }}</td>', content)
    content = re.sub(r'<td>Location erstellen</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.create\') }}</td>', content)
    content = re.sub(r'<td>Location aktualisieren</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.update\') }}</td>', content)
    content = re.sub(r'<td>Location löschen</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.delete\') }}</td>', content)
    content = re.sub(r'<td>Quellen verknüpfen</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.linkSources\') }}</td>', content)
    content = re.sub(r'<td>Admin-Levels anreichern</td>', '<td>{{ t(\'help.apiGroups.locations.endpoints.enrichAdminLevels\') }}</td>', content)

    # API Groups - Public API
    content = re.sub(
        r'<v-icon color="info" class="mr-2">mdi-database-search</v-icon>\s+Public API \(v1/data\)',
        '<v-icon color="info" class="mr-2">mdi-database-search</v-icon>\n                  {{ t(\'help.apiGroups.publicApi.title\') }}',
        content
    )
    content = re.sub(r'<td>Extrahierte Daten \(mit Filtern\)</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.data\') }}</td>', content)
    content = re.sub(r'<td>Extraktions-Statistiken</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.stats\') }}</td>', content)
    content = re.sub(r'<td>Locations mit Extraktionen</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.locations\') }}</td>', content)
    content = re.sub(r'<td>Länder mit Extraktionen</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.countries\') }}</td>', content)
    content = re.sub(r'<td>Alle Dokumente</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.documents\') }}</td>', content)
    content = re.sub(r'<td>Dokument-Details</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.documentDetails\') }}</td>', content)
    content = re.sub(r'<td>Dokument-Locations</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.documentLocations\') }}</td>', content)
    content = re.sub(r'<td>Volltextsuche</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.search\') }}</td>', content)
    content = re.sub(r'<td>Extraktion verifizieren</td>', '<td>{{ t(\'help.apiGroups.publicApi.endpoints.verify\') }}</td>', content)

    # API Groups - Entities
    content = re.sub(
        r'<v-icon color="deep-purple" class="mr-2">mdi-cube-outline</v-icon>\s+Entities',
        '<v-icon color="deep-purple" class="mr-2">mdi-cube-outline</v-icon>\n                  {{ t(\'help.apiGroups.entities.title\') }}',
        content
    )
    content = re.sub(r'<td>Alle Entities \(mit Filtern\)</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.list\') }}</td>', content)
    content = re.sub(r'<td>Entity erstellen</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.create\') }}</td>', content)
    content = re.sub(r'<td>Entity abrufen</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.get\') }}</td>', content)
    content = re.sub(r'<td>Entity aktualisieren</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.update\') }}</td>', content)
    content = re.sub(r'<td>Entity loeschen</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.delete\') }}</td>', content)
    content = re.sub(r'<td>Kurzuebersicht</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.brief\') }}</td>', content)
    content = re.sub(r'<td>Kind-Entities</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.children\') }}</td>', content)
    content = re.sub(r'<td>Hierarchie nach Typ</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.hierarchy\') }}</td>', content)
    content = re.sub(r'<td>Location-Filteroptionen</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.filterLocation\') }}</td>', content)
    content = re.sub(r'<td>Attribut-Filteroptionen</td>', '<td>{{ t(\'help.apiGroups.entities.endpoints.filterAttributes\') }}</td>', content)

    # API Groups - Smart Query
    content = re.sub(
        r'<v-icon color="pink" class="mr-2">mdi-brain</v-icon>\s+Smart Query & Analysis',
        '<v-icon color="pink" class="mr-2">mdi-brain</v-icon>\n                  {{ t(\'help.apiGroups.smartQuery.title\') }}',
        content
    )
    content = re.sub(
        r'Smart Query ermoeglicht KI-gestuetzte natuerlichsprachige Abfragen und automatische Erstellung von Kategorien\.',
        "{{ t('help.apiGroups.smartQuery.note') }}",
        content
    )
    content = re.sub(r'<td>Smart Query ausfuehren \(Read-Mode\)</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.query\') }}</td>', content)
    content = re.sub(r'<td>Smart Write ausfuehren \(Write-Mode\)</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.write\') }}</td>', content)
    content = re.sub(r'<td>Beispiel-Queries</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.examples\') }}</td>', content)
    content = re.sub(r'<td>Analyse-Templates</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.templates\') }}</td>', content)
    content = re.sub(r'<td>Template erstellen</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.createTemplate\') }}</td>', content)
    content = re.sub(r'<td>Template abrufen</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.getTemplate\') }}</td>', content)
    content = re.sub(r'<td>Template aktualisieren</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.updateTemplate\') }}</td>', content)
    content = re.sub(r'<td>Template loeschen</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.deleteTemplate\') }}</td>', content)
    content = re.sub(r'<td>Analyse-Uebersicht</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.overview\') }}</td>', content)
    content = re.sub(r'<td>Entity-Report</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.report\') }}</td>', content)
    content = re.sub(r'<td>Analyse-Statistiken</td>', '<td>{{ t(\'help.apiGroups.smartQuery.endpoints.stats\') }}</td>', content)

    # API Groups - Municipalities
    content = re.sub(
        r'<v-icon color="orange" class="mr-2">mdi-city</v-icon>\s+Gemeinden & Reports',
        '<v-icon color="orange" class="mr-2">mdi-city</v-icon>\n                  {{ t(\'help.apiGroups.municipalities.title\') }}',
        content
    )
    content = re.sub(r'<td>Alle Gemeinden</td>', '<td>{{ t(\'help.apiGroups.municipalities.endpoints.list\') }}</td>', content)
    content = re.sub(r'<td>Gemeinde-Report</td>', '<td>{{ t(\'help.apiGroups.municipalities.endpoints.report\') }}</td>', content)
    content = re.sub(r'<td>Gemeinde-Dokumente</td>', '<td>{{ t(\'help.apiGroups.municipalities.endpoints.documents\') }}</td>', content)
    content = re.sub(r'<td>Übersichts-Report</td>', '<td>{{ t(\'help.apiGroups.municipalities.endpoints.overview\') }}</td>', content)
    content = re.sub(r'<td>Gemeinde-Historie</td>', '<td>{{ t(\'help.apiGroups.municipalities.endpoints.history\') }}</td>', content)
    content = re.sub(r'<td>Crawl-Historie</td>', '<td>{{ t(\'help.apiGroups.municipalities.endpoints.crawlHistory\') }}</td>', content)

    # API Groups - Export (add missing translations)
    content = re.sub(r'<td>JSON-Export</td>', '<td>{{ t(\'help.apiGroups.export.endpoints.json\') }}</td>', content)
    content = re.sub(r'<td>CSV-Export</td>', '<td>{{ t(\'help.apiGroups.export.endpoints.csv\') }}</td>', content)
    content = re.sub(r'<td>Änderungs-Feed</td>', '<td>{{ t(\'help.apiGroups.export.endpoints.changes\') }}</td>', content)
    content = re.sub(r'<td>Webhook testen</td>', '<td>{{ t(\'help.apiGroups.export.endpoints.webhookTest\') }}</td>', content)

    # API Groups - System & Health
    content = re.sub(
        r'<v-icon color="green" class="mr-2">mdi-heart-pulse</v-icon>\s+System & Health',
        '<v-icon color="green" class="mr-2">mdi-heart-pulse</v-icon>\n                  {{ t(\'help.apiGroups.system.title\') }}',
        content
    )
    content = re.sub(r'<td>Root-Endpoint \(API-Info\)</td>', '<td>{{ t(\'help.apiGroups.system.endpoints.root\') }}</td>', content)
    content = re.sub(r'<td>Health-Check</td>', '<td>{{ t(\'help.apiGroups.system.endpoints.health\') }}</td>', content)
    content = re.sub(r'<td>Swagger UI \(interaktive Doku\)</td>', '<td>{{ t(\'help.apiGroups.system.endpoints.swagger\') }}</td>', content)
    content = re.sub(r'<td>ReDoc \(alternative Doku\)</td>', '<td>{{ t(\'help.apiGroups.system.endpoints.redoc\') }}</td>', content)
    content = re.sub(r'<td>OpenAPI Schema</td>', '<td>{{ t(\'help.apiGroups.system.endpoints.openapi\') }}</td>', content)

    # API Footer text
    content = re.sub(
        r'Die vollständige interaktive API-Dokumentation mit allen Parametern und Beispielen finden Sie unter\s+<a href="/docs" target="_blank" class="text-primary">/docs</a> \(Swagger UI\) oder\s+<a href="/redoc" target="_blank" class="text-primary">/redoc</a> \(ReDoc\)\.',
        '{{ t(\'help.api.fullDocumentation\') }}\n              <a href="/docs" target="_blank" class="text-primary">/docs</a> (Swagger UI) {{ t(\'help.api.or\') }}\n              <a href="/redoc" target="_blank" class="text-primary">/redoc</a> (ReDoc).',
        content,
        flags=re.DOTALL
    )

    print("Translating Tips section...")
    # Tips section
    content = re.sub(
        r'<v-icon class="mr-2">mdi-lightbulb</v-icon>\s+Tipps & Best Practices',
        '<v-icon class="mr-2">mdi-lightbulb</v-icon>\n            {{ t(\'help.tips.title\') }}',
        content
    )
    content = re.sub(r'<v-expansion-panel title="Effizientes Crawling">', '<v-expansion-panel :title="t(\'help.tips.efficientCrawling.title\')">', content)
    content = re.sub(r'<v-list-item-title>Blacklist-Filter nutzen</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.efficientCrawling.useBlacklist\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>Exclude-Patterns filtern irrelevante Seiten \(Impressum, Login, etc\.\)</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.efficientCrawling.useBlacklistDesc\') }}</v-list-item-subtitle>', content)
    content = re.sub(r'<v-list-item-title>Max\. Tiefe begrenzen</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.efficientCrawling.limitDepth\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>Starten Sie mit Tiefe 2-3, erhöhen Sie nur bei Bedarf</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.efficientCrawling.limitDepthDesc\') }}</v-list-item-subtitle>', content)
    content = re.sub(r'<v-list-item-title>Dokumenttypen einschränken</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.efficientCrawling.restrictDocTypes\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>PDFs sind meist ergiebiger als HTML</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.efficientCrawling.restrictDocTypesDesc\') }}</v-list-item-subtitle>', content)

    content = re.sub(r'<v-expansion-panel title="Bessere KI-Ergebnisse">', '<v-expansion-panel :title="t(\'help.tips.betterAiResults.title\')">', content)
    content = re.sub(r'<v-list-item-title>Präzise Prompts</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.betterAiResults.precisePrompts\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>Definieren Sie klare JSON-Strukturen und geben Sie Beispiele</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.betterAiResults.precisePromptsDesc\') }}</v-list-item-subtitle>', content)
    content = re.sub(r'<v-list-item-title>Keyword-Optimierung</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.betterAiResults.optimizeKeywords\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>Nutzen Sie domänenspezifische Begriffe inkl\. Varianten</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.betterAiResults.optimizeKeywordsDesc\') }}</v-list-item-subtitle>', content)
    content = re.sub(r'<v-list-item-title>Testen Sie zuerst</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.betterAiResults.testFirst\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>Starten Sie mit wenigen Quellen, optimieren Sie dann</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.betterAiResults.testFirstDesc\') }}</v-list-item-subtitle>', content)

    content = re.sub(r'<v-expansion-panel title="Organisation">', '<v-expansion-panel :title="t(\'help.tips.organization.title\')">', content)
    content = re.sub(r'<v-list-item-title>Kategorien sinnvoll trennen</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.organization.separateCategories\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>Eine Kategorie pro Themengebiet mit eigenem Prompt</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.organization.separateCategoriesDesc\') }}</v-list-item-subtitle>', content)
    content = re.sub(r'<v-list-item-title>Standorte pflegen</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.organization.maintainLocations\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>Weisen Sie jeder Quelle einen Standort zu</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.organization.maintainLocationsDesc\') }}</v-list-item-subtitle>', content)
    content = re.sub(r'<v-list-item-title>Regelmäßige Pflege</v-list-item-title>', '<v-list-item-title>{{ t(\'help.tips.organization.regularMaintenance\') }}</v-list-item-title>', content)
    content = re.sub(r'<v-list-item-subtitle>Prüfen Sie fehlerhafte Quellen und URLs</v-list-item-subtitle>', '<v-list-item-subtitle>{{ t(\'help.tips.organization.regularMaintenanceDesc\') }}</v-list-item-subtitle>', content)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Calculate changes
    changes_made = len([1 for i, (c1, c2) in enumerate(zip(original_content, content)) if c1 != c2])
    print("\n✓ Translation completed!")
    print(f"  - Approximately {changes_made} characters changed")
    print(f"  - File: {file_path}")

if __name__ == '__main__':
    translate_helpview()
