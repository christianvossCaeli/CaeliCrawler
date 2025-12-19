<template>
  <div>
    <h1 class="text-h4 mb-6">
      <v-icon class="mr-2">mdi-help-circle</v-icon>
      Benutzerhandbuch
    </h1>

    <!-- Quick Navigation -->
    <v-card class="mb-6">
      <v-card-text>
        <div class="d-flex flex-wrap ga-2">
          <v-chip
            v-for="section in sections"
            :key="section.id"
            :color="activeSection === section.id ? 'primary' : 'default'"
            variant="outlined"
            @click="scrollTo(section.id)"
          >
            <v-icon start size="small">{{ section.icon }}</v-icon>
            {{ section.title }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Content -->
    <v-row>
      <v-col cols="12" lg="9">
        <!-- Einführung -->
        <v-card id="intro" class="mb-4">
          <v-card-title class="text-h5 bg-primary">
            <v-icon class="mr-2">mdi-information</v-icon>
            Einführung
          </v-card-title>
          <v-card-text class="pt-4">
            <h3 class="text-h6 mb-3">Was ist CaeliCrawler?</h3>
            <p class="mb-4">
              CaeliCrawler ist ein intelligentes Web-Crawling-System zur automatisierten Erfassung und
              Analyse von kommunalen Dokumenten und Webseiten. Das System wurde speziell entwickelt, um
              relevante Informationen aus öffentlichen Quellen zu extrahieren und mittels KI-Analyse
              strukturiert aufzubereiten.
            </p>

            <h3 class="text-h6 mb-3">Hauptfunktionen</h3>
            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>Funktion</th><th>Beschreibung</th></tr>
              </thead>
              <tbody>
                <tr><td><strong>Web-Crawling</strong></td><td>Automatisches Durchsuchen von Websites nach relevanten Dokumenten</td></tr>
                <tr><td><strong>Dokumentenverarbeitung</strong></td><td>Extraktion von Text aus PDFs, HTML, Word-Dokumenten</td></tr>
                <tr><td><strong>KI-Analyse</strong></td><td>Intelligente Auswertung der Inhalte mittels Azure OpenAI</td></tr>
                <tr><td><strong>Relevanz-Filterung</strong></td><td>Automatische Vorsortierung nach konfigurierbaren Keywords</td></tr>
                <tr><td><strong>Strukturierte Ergebnisse</strong></td><td>Export der Erkenntnisse als JSON oder CSV</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">Typischer Workflow</h3>
            <v-stepper :model-value="1" alt-labels class="elevation-0 bg-transparent">
              <v-stepper-header>
                <v-stepper-item title="Kategorie" subtitle="erstellen" value="1" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item title="Datenquelle" subtitle="hinzufügen" value="2" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item title="Crawler" subtitle="starten" value="3" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item title="Dokumente" subtitle="verarbeiten" value="4" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item title="KI-Analyse" subtitle="läuft" value="5" complete></v-stepper-item>
                <v-divider></v-divider>
                <v-stepper-item title="Ergebnisse" subtitle="exportieren" value="6" complete></v-stepper-item>
              </v-stepper-header>
            </v-stepper>
          </v-card-text>
        </v-card>

        <!-- Schnellstart -->
        <v-card id="quickstart" class="mb-4">
          <v-card-title class="text-h5 bg-success">
            <v-icon class="mr-2">mdi-rocket-launch</v-icon>
            Schnellstart
          </v-card-title>
          <v-card-text class="pt-4">
            <h3 class="text-h6 mb-3">In 5 Minuten zum ersten Ergebnis</h3>

            <v-timeline density="compact" side="end">
              <v-timeline-item dot-color="primary" size="small">
                <template v-slot:opposite><strong>Schritt 1</strong></template>
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">Kategorie anlegen</v-card-title>
                  <v-card-text>
                    <ol class="pl-4">
                      <li>Navigieren Sie zu <strong>Kategorien</strong></li>
                      <li>Klicken Sie auf <v-chip size="small" color="primary">Neue Kategorie</v-chip></li>
                      <li>Geben Sie einen Namen ein (z.B. "Windenergie-Beschlüsse")</li>
                      <li>Definieren Sie Zweck und Suchbegriffe</li>
                      <li>Speichern</li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-timeline-item>

              <v-timeline-item dot-color="success" size="small">
                <template v-slot:opposite><strong>Schritt 2</strong></template>
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">Datenquelle hinzufügen</v-card-title>
                  <v-card-text>
                    <ol class="pl-4">
                      <li>Wechseln Sie zu <strong>Datenquellen</strong></li>
                      <li>Klicken Sie auf <v-chip size="small" color="success">Neue Quelle</v-chip></li>
                      <li>Wählen Sie die erstellte Kategorie</li>
                      <li>Geben Sie die Basis-URL der Website ein</li>
                      <li>Wählen Sie Land und Gemeinde</li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-timeline-item>

              <v-timeline-item dot-color="warning" size="small">
                <template v-slot:opposite><strong>Schritt 3</strong></template>
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">Crawl starten</v-card-title>
                  <v-card-text>
                    <ol class="pl-4">
                      <li>Gehen Sie zum <strong>Dashboard</strong></li>
                      <li>Klicken Sie auf <v-chip size="small" color="warning">Crawler starten</v-chip></li>
                      <li>Wählen Sie Filter oder starten Sie für alle Quellen</li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-timeline-item>

              <v-timeline-item dot-color="info" size="small">
                <template v-slot:opposite><strong>Schritt 4</strong></template>
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">Ergebnisse ansehen</v-card-title>
                  <v-card-text>
                    <ol class="pl-4">
                      <li>Überwachen Sie den Fortschritt unter <strong>Crawler</strong></li>
                      <li>Prüfen Sie verarbeitete <strong>Dokumente</strong></li>
                      <li>Sehen Sie KI-Erkenntnisse unter <strong>Ergebnisse</strong></li>
                    </ol>
                  </v-card-text>
                </v-card>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
        </v-card>

        <!-- Dashboard -->
        <v-card id="dashboard" class="mb-4">
          <v-card-title class="text-h5 bg-info">
            <v-icon class="mr-2">mdi-view-dashboard</v-icon>
            Dashboard
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">Das Dashboard ist die zentrale Übersichtsseite und zeigt den aktuellen Systemstatus.</p>

            <h3 class="text-h6 mb-3">Statistik-Karten</h3>
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="primary" size="32">mdi-folder-multiple</v-icon>
                  <div class="text-h6">Kategorien</div>
                  <div class="text-caption">Anzahl konfigurierter Kategorien</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="success" size="32">mdi-web</v-icon>
                  <div class="text-h6">Datenquellen</div>
                  <div class="text-caption">Registrierte Websites/APIs</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="info" size="32">mdi-file-document-multiple</v-icon>
                  <div class="text-h6">Dokumente</div>
                  <div class="text-caption">Gefundene Dateien</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="warning" size="32">mdi-robot</v-icon>
                  <div class="text-h6">Aktive Crawler</div>
                  <div class="text-caption">Laufende Jobs</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">Live-Updates für aktive Crawler</h3>
            <v-alert type="info" variant="tonal" class="mb-4">
              Wenn Crawler laufen, erscheint eine Live-Ansicht mit:
              <v-list density="compact" class="bg-transparent">
                <v-list-item prepend-icon="mdi-file-document">Gefundene Dokumente (mit Anzahl neuer)</v-list-item>
                <v-list-item prepend-icon="mdi-clock">Laufzeit seit Start</v-list-item>
                <v-list-item prepend-icon="mdi-alert">Fehleranzahl (falls vorhanden)</v-list-item>
              </v-list>
            </v-alert>

            <h3 class="text-h6 mb-3">Crawler Status & Letzte Jobs</h3>
            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3">
                  <div class="text-subtitle-1 mb-2"><v-icon class="mr-1">mdi-robot</v-icon> Status</div>
                  <v-list density="compact">
                    <v-list-item><v-icon color="success" class="mr-2">mdi-circle</v-icon> Aktive Workers</v-list-item>
                    <v-list-item><v-icon color="info" class="mr-2">mdi-run</v-icon> Laufende Jobs</v-list-item>
                    <v-list-item><v-icon color="warning" class="mr-2">mdi-clock-outline</v-icon> Wartende Jobs</v-list-item>
                  </v-list>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3">
                  <div class="text-subtitle-1 mb-2"><v-icon class="mr-1">mdi-history</v-icon> Letzte Crawl-Jobs</div>
                  <div class="text-body-2">Zeigt die letzten 5 abgeschlossenen Jobs mit Status und Dokumentenanzahl</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">Schnellaktionen</h3>
            <v-chip-group class="mb-4">
              <v-chip color="primary" variant="elevated"><v-icon start>mdi-plus</v-icon> Neue Kategorie</v-chip>
              <v-chip color="success" variant="elevated"><v-icon start>mdi-web-plus</v-icon> Neue Datenquelle</v-chip>
              <v-chip color="warning" variant="elevated"><v-icon start>mdi-play</v-icon> Crawler starten</v-chip>
              <v-chip color="info" variant="elevated"><v-icon start>mdi-export</v-icon> Daten exportieren</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">Crawler starten - Dialog</h3>
            <v-table density="compact">
              <thead><tr><th>Filter</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><strong>Kategorie</strong></td><td>Nur Quellen einer bestimmten Kategorie</td></tr>
                <tr><td><strong>Land</strong></td><td>Nur Quellen aus einem bestimmten Land</td></tr>
                <tr><td><strong>Suche</strong></td><td>Textsuche in Name oder URL</td></tr>
                <tr><td><strong>Max. Anzahl</strong></td><td>Limit für zu crawlende Quellen</td></tr>
                <tr><td><strong>Status</strong></td><td>Nur aktive, ausstehende oder fehlerhafte Quellen</td></tr>
                <tr><td><strong>Quellentyp</strong></td><td>Website, OParl API oder RSS Feed</td></tr>
              </tbody>
            </v-table>
            <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
              <v-icon>mdi-alert</v-icon> Bei mehr als 500 Quellen wird ein Filter oder Limit empfohlen!
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- Kategorien -->
        <v-card id="categories" class="mb-4">
          <v-card-title class="text-h5 bg-purple">
            <v-icon class="mr-2">mdi-folder-multiple</v-icon>
            Kategorien
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">
              Kategorien sind die oberste Organisationsebene und definieren, <strong>was</strong> gesucht wird
              und <strong>wie</strong> die Ergebnisse analysiert werden.
            </p>

            <v-expansion-panels variant="accordion">
              <v-expansion-panel title="Grundeinstellungen">
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Feld</th><th>Beschreibung</th><th>Beispiel</th></tr></thead>
                    <tbody>
                      <tr><td><strong>Name</strong></td><td>Eindeutiger Name</td><td>"Windenergie-Beschlüsse"</td></tr>
                      <tr><td><strong>Beschreibung</strong></td><td>Optionale Erläuterung</td><td>"Sammelt alle Ratsbeschlüsse"</td></tr>
                      <tr><td><strong>Zweck</strong></td><td>Was soll erreicht werden?</td><td>"Windkraft-Restriktionen analysieren"</td></tr>
                      <tr><td><strong>Status</strong></td><td>Aktiv/Inaktiv</td><td>Aktiv</td></tr>
                      <tr><td><strong>Dokumenttypen</strong></td><td>Erwartete Typen zur Klassifizierung</td><td>Beschluss, Protokoll, Satzung</td></tr>
                      <tr><td><strong>Zeitplan (Cron)</strong></td><td>Automatischer Crawl-Zeitplan</td><td>"0 2 * * *" (täglich 2 Uhr)</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel title="Suchbegriffe (Keywords)">
                <v-expansion-panel-text>
                  <p class="mb-2">Keywords für die Relevanz-Filterung:</p>
                  <v-chip-group>
                    <v-chip size="small">windkraft</v-chip>
                    <v-chip size="small">windenergie</v-chip>
                    <v-chip size="small">windpark</v-chip>
                    <v-chip size="small">repowering</v-chip>
                    <v-chip size="small">flächennutzungsplan</v-chip>
                    <v-chip size="small">bebauungsplan</v-chip>
                  </v-chip-group>
                  <v-alert type="info" variant="tonal" density="compact" class="mt-3">
                    Dokumente werden nur zur KI-Analyse weitergeleitet, wenn sie mindestens 2 dieser Keywords enthalten.
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel title="URL-Filter (Regex)">
                <v-expansion-panel-text>
                  <h4 class="mb-2">Include-Patterns (Whitelist)</h4>
                  <v-chip-group class="mb-3">
                    <v-chip size="small" color="success" variant="outlined">/ratsinformation/</v-chip>
                    <v-chip size="small" color="success" variant="outlined">/beschluesse/</v-chip>
                    <v-chip size="small" color="success" variant="outlined">/dokumente/</v-chip>
                  </v-chip-group>

                  <h4 class="mb-2">Exclude-Patterns (Blacklist)</h4>
                  <v-chip-group>
                    <v-chip size="small" color="error" variant="outlined">/archiv/</v-chip>
                    <v-chip size="small" color="error" variant="outlined">/login/</v-chip>
                    <v-chip size="small" color="error" variant="outlined">/suche/</v-chip>
                  </v-chip-group>

                  <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
                    Ohne URL-Filter wird die komplette Website durchsucht - das kann sehr lange dauern!
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel title="KI-Extraktions-Prompt">
                <v-expansion-panel-text>
                  <p class="mb-2">Definiert, was die KI extrahieren soll. Beispiel:</p>
                  <v-code class="pa-3 d-block text-caption" style="white-space: pre-wrap;">Analysiere das Dokument und extrahiere:
{
  "topic": "Hauptthema",
  "summary": "Zusammenfassung",
  "is_relevant": true/false,
  "municipality": "Gemeinde",
  "pain_points": ["Kritische Punkte"],
  "positive_signals": ["Positive Signale/Chancen"],
  "decision_makers": [{"person": "Name", "role": "Position"}],
  "sentiment": "positiv/neutral/negativ"
}</v-code>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mt-4 mb-3">Aktionen</h3>
            <v-table density="compact">
              <thead><tr><th>Aktion</th><th>Symbol</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td>Bearbeiten</td><td><v-icon size="small">mdi-pencil</v-icon></td><td>Einstellungen ändern</td></tr>
                <tr><td>Crawlen</td><td><v-icon size="small" color="success">mdi-play</v-icon></td><td>Crawl für alle Quellen starten</td></tr>
                <tr><td>Neu analysieren</td><td><v-icon size="small" color="warning">mdi-refresh</v-icon></td><td>Dokumente erneut durch KI</td></tr>
                <tr><td>Löschen</td><td><v-icon size="small" color="error">mdi-delete</v-icon></td><td>Mit allen Daten löschen</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Datenquellen -->
        <v-card id="sources" class="mb-4">
          <v-card-title class="text-h5 bg-teal">
            <v-icon class="mr-2">mdi-web</v-icon>
            Datenquellen
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">Datenquellen sind die konkreten Websites oder APIs, die gecrawlt werden.</p>

            <h3 class="text-h6 mb-3">Quellentypen</h3>
            <v-row class="mb-4">
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <v-chip color="primary" class="mb-2">WEBSITE</v-chip>
                  <div class="text-body-2">Standard-Website-Crawling für kommunale Websites, Nachrichtenseiten</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <v-chip color="success" class="mb-2">OPARL_API</v-chip>
                  <div class="text-body-2">OParl-Schnittstelle für Ratsinformationssysteme</div>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <v-chip color="warning" class="mb-2">RSS</v-chip>
                  <div class="text-body-2">RSS-Feed für News-Aggregation</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">Verfügbare Filter</h3>
            <v-chip-group class="mb-4">
              <v-chip size="small" variant="outlined">Land (mit Anzahl)</v-chip>
              <v-chip size="small" variant="outlined">Gemeinde (Autocomplete)</v-chip>
              <v-chip size="small" variant="outlined">Kategorie</v-chip>
              <v-chip size="small" variant="outlined">Status</v-chip>
              <v-chip size="small" variant="outlined">Suche (Name/URL)</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">Aktionen</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>Button</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="secondary">Bulk Import</v-chip></td><td>Mehrere Quellen per JSON importieren</td></tr>
                <tr><td><v-chip size="small" color="primary">Neue Quelle</v-chip></td><td>Einzelne Quelle manuell anlegen</td></tr>
                <tr><td><v-icon size="small">mdi-pencil</v-icon> Bearbeiten</td><td>Quelle bearbeiten</td></tr>
                <tr><td><v-icon size="small" color="success">mdi-play</v-icon> Crawlen</td><td>Crawl für diese Quelle starten</td></tr>
                <tr><td><v-icon size="small" color="warning">mdi-refresh</v-icon> Zurücksetzen</td><td>Nur bei ERROR-Status: Quelle zurücksetzen</td></tr>
                <tr><td><v-icon size="small" color="error">mdi-delete</v-icon> Löschen</td><td>Quelle mit allen Dokumenten löschen</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">Formular-Felder (Neue/Bearbeiten)</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>Feld</th><th>Beschreibung</th><th>Pflicht</th></tr></thead>
              <tbody>
                <tr><td><strong>Kategorie</strong></td><td>Zugehörige Kategorie (bei Edit nicht änderbar)</td><td>Ja</td></tr>
                <tr><td><strong>Name</strong></td><td>Anzeigename der Quelle</td><td>Ja</td></tr>
                <tr><td><strong>Quellentyp</strong></td><td>WEBSITE, OPARL_API, RSS, CUSTOM_API</td><td>Ja</td></tr>
                <tr><td><strong>Basis-URL</strong></td><td>Start-URL für den Crawler</td><td>Ja</td></tr>
                <tr><td><strong>API-Endpunkt</strong></td><td>Nur für OPARL_API/CUSTOM_API</td><td>Nein</td></tr>
                <tr><td><strong>Land</strong></td><td>Dropdown: DE, AT, CH, etc.</td><td>Nein</td></tr>
                <tr><td><strong>Ort</strong></td><td>Autocomplete-Suche mit Location-Verknüpfung</td><td>Nein</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">Bulk Import</h3>
            <v-alert type="info" variant="tonal" class="mb-4">
              Mehrere Quellen auf einmal importieren:
              <ol class="mt-2 pl-4">
                <li>Kategorie auswählen</li>
                <li>JSON-Array mit Quellen eingeben:</li>
              </ol>
              <v-code class="mt-2 pa-2 d-block text-caption">[
  {"name": "Stadt X", "base_url": "https://...", "location_name": "Stadt X"},
  {"name": "Stadt Y", "base_url": "https://...", "location_name": "Stadt Y"}
]</v-code>
            </v-alert>

            <h3 class="text-h6 mb-3">Crawl-Konfiguration</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>Einstellung</th><th>Beschreibung</th><th>Standard</th></tr></thead>
              <tbody>
                <tr><td><strong>Max. Tiefe</strong></td><td>Wie viele Link-Ebenen verfolgen</td><td>3</td></tr>
                <tr><td><strong>Max. Seiten</strong></td><td>Maximale Anzahl zu crawlender Seiten</td><td>200</td></tr>
                <tr><td><strong>Externe Links</strong></td><td>Links zu anderen Domains verfolgen</td><td>Nein</td></tr>
                <tr><td><strong>JavaScript rendern</strong></td><td>Playwright für dynamische Seiten</td><td>Nein</td></tr>
                <tr><td><strong>HTML-Capture</strong></td><td>Relevante HTML-Seiten als Dokumente speichern</td><td>Ja</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">URL-Filter (Erweiterte Einstellungen)</h3>
            <v-alert type="info" variant="tonal" class="mb-3">
              URL-Filter sind Regex-Patterns um URLs einzugrenzen oder auszuschließen.
            </v-alert>
            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3" color="success">
                  <div class="text-subtitle-2 mb-2"><v-icon color="success">mdi-check</v-icon> Include-Patterns (Whitelist)</div>
                  <div class="text-body-2">URLs müssen mindestens ein Pattern matchen:</div>
                  <v-chip-group class="mt-2">
                    <v-chip size="small">/dokumente/</v-chip>
                    <v-chip size="small">/beschluesse/</v-chip>
                    <v-chip size="small">/ratsinformation/</v-chip>
                  </v-chip-group>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3" color="error">
                  <div class="text-subtitle-2 mb-2"><v-icon color="error">mdi-close</v-icon> Exclude-Patterns (Blacklist)</div>
                  <div class="text-body-2">URLs die ein Pattern matchen werden übersprungen:</div>
                  <v-chip-group class="mt-2">
                    <v-chip size="small">/archiv/</v-chip>
                    <v-chip size="small">/login/</v-chip>
                    <v-chip size="small">/suche/</v-chip>
                  </v-chip-group>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">Status-Bedeutung</h3>
            <v-table density="compact">
              <thead><tr><th>Status</th><th>Bedeutung</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="grey">PENDING</v-chip></td><td>Noch nie gecrawlt</td></tr>
                <tr><td><v-chip size="small" color="info">CRAWLING</v-chip></td><td>Crawl läuft gerade</td></tr>
                <tr><td><v-chip size="small" color="success">ACTIVE</v-chip></td><td>Erfolgreich gecrawlt</td></tr>
                <tr><td><v-chip size="small" color="error">ERROR</v-chip></td><td>Letzter Crawl fehlgeschlagen</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Crawler -->
        <v-card id="crawler" class="mb-4">
          <v-card-title class="text-h5 bg-cyan">
            <v-icon class="mr-2">mdi-robot</v-icon>
            Crawler Status
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">Die Crawler-Seite zeigt den Live-Status aller Crawling- und KI-Aktivitäten.</p>

            <h3 class="text-h6 mb-3">Status-Karten</h3>
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="success" size="32">mdi-account-hard-hat</v-icon>
                  <div class="text-subtitle-1">Aktive Worker</div>
                  <div class="text-caption">Verfügbare Prozesse</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="info" size="32">mdi-run</v-icon>
                  <div class="text-subtitle-1">Laufende Jobs</div>
                  <div class="text-caption">Aktive Crawls</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="warning" size="32">mdi-clock-outline</v-icon>
                  <div class="text-subtitle-1">Wartende Jobs</div>
                  <div class="text-caption">In der Queue</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-3">
                  <v-icon color="primary" size="32">mdi-file-document-multiple</v-icon>
                  <div class="text-subtitle-1">Dokumente</div>
                  <div class="text-caption">Gesamt gefunden</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">KI-Aufgaben (Live)</h3>
            <v-alert type="info" variant="tonal" class="mb-3">
              Zeigt laufende KI-Analysen mit:
              <v-list density="compact" class="bg-transparent">
                <v-list-item prepend-icon="mdi-brain">Task-Name und aktuelles Dokument</v-list-item>
                <v-list-item prepend-icon="mdi-progress-check">Fortschrittsbalken (X/Y Dokumente)</v-list-item>
                <v-list-item prepend-icon="mdi-stop"><v-chip size="x-small" color="error">Stopp</v-chip> Button zum Abbrechen</v-list-item>
              </v-list>
            </v-alert>

            <h3 class="text-h6 mb-3">Aktive Crawler (Live)</h3>
            <p class="mb-2">Expandierbare Panels für jeden laufenden Crawl:</p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-web">
                <v-list-item-title>Quelle & aktuelle URL</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-file-document">
                <v-list-item-title>Seiten gecrawlt / Dokumente gefunden / Neue</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-alert">
                <v-list-item-title>Fehlerzähler (falls vorhanden)</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-stop">
                <v-list-item-title><v-chip size="x-small" color="error">Stopp</v-chip> Button zum sofortigen Abbruch</v-list-item-title>
              </v-list-item>
            </v-list>

            <h4 class="text-subtitle-1 mb-2">Live-Log (expandierbar)</h4>
            <v-alert type="info" variant="tonal" density="compact" class="mb-4">
              Virtueller Scroll mit letzten Aktivitäten: URL besucht, Dokument gefunden, Fehler. Farbcodiert mit Timestamps.
            </v-alert>

            <h3 class="text-h6 mb-3">Job-Tabelle</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>Spalte</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><strong>Quelle</strong></td><td>Name der gecrawlten Datenquelle</td></tr>
                <tr><td><strong>Status</strong></td><td>RUNNING, COMPLETED, FAILED, CANCELLED</td></tr>
                <tr><td><strong>Gestartet</strong></td><td>Startzeitpunkt des Jobs</td></tr>
                <tr><td><strong>Dauer</strong></td><td>Laufzeit in Minuten/Stunden</td></tr>
                <tr><td><strong>Fortschritt</strong></td><td>Verarbeitete/Gefundene Dokumente mit Balken</td></tr>
                <tr><td><strong>Aktionen</strong></td><td><v-icon size="small" color="error">mdi-stop</v-icon> Stopp (bei RUNNING), <v-icon size="small">mdi-information</v-icon> Details</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">Job-Details-Dialog</h3>
            <p class="mb-2">Klicken Sie auf das Info-Symbol für den vollständigen Job-Report:</p>
            <v-row class="mb-3">
              <v-col cols="12" md="6">
                <v-list density="compact">
                  <v-list-item prepend-icon="mdi-web"><v-list-item-title>Quelle & Kategorie</v-list-item-title></v-list-item>
                  <v-list-item prepend-icon="mdi-check-circle"><v-list-item-title>Status mit Farb-Chip</v-list-item-title></v-list-item>
                  <v-list-item prepend-icon="mdi-clock"><v-list-item-title>Dauer (formatiert)</v-list-item-title></v-list-item>
                </v-list>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-2">
                  <div class="text-subtitle-2 mb-2">Statistiken:</div>
                  <v-chip size="small" class="mr-1">Seiten gecrawlt</v-chip>
                  <v-chip size="small" class="mr-1" color="success">Dokumente gefunden</v-chip>
                  <v-chip size="small" color="info">Neue Dokumente</v-chip>
                </v-card>
              </v-col>
            </v-row>
            <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
              Bei fehlgeschlagenen Jobs wird zusätzlich ein <strong>Error-Log</strong> mit Details angezeigt.
            </v-alert>

            <h3 class="text-h6 mt-4 mb-3">Status-Filter</h3>
            <v-btn-toggle class="mb-2" density="compact" variant="outlined">
              <v-btn size="small">Alle</v-btn>
              <v-btn size="small" color="info">Laufend</v-btn>
              <v-btn size="small" color="success">Abgeschlossen</v-btn>
              <v-btn size="small" color="error">Fehlgeschlagen</v-btn>
            </v-btn-toggle>
          </v-card-text>
        </v-card>

        <!-- Dokumente -->
        <v-card id="documents" class="mb-4">
          <v-card-title class="text-h5 bg-blue-grey">
            <v-icon class="mr-2">mdi-file-document-multiple</v-icon>
            Dokumente
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">Die Dokumenten-Ansicht zeigt alle gefundenen und verarbeiteten Dateien.</p>

            <h3 class="text-h6 mb-3">Status-Übersicht</h3>
            <div class="d-flex flex-wrap ga-2 mb-4">
              <v-chip color="warning" variant="tonal">
                <v-icon start size="small">mdi-clock-outline</v-icon>
                Wartend
              </v-chip>
              <v-chip color="info" variant="tonal">
                <v-icon start size="small">mdi-cog-sync</v-icon>
                In Bearbeitung
              </v-chip>
              <v-chip color="success" variant="tonal">
                <v-icon start size="small">mdi-check-circle</v-icon>
                Fertig
              </v-chip>
              <v-chip color="grey" variant="tonal">
                <v-icon start size="small">mdi-filter-remove</v-icon>
                Gefiltert
              </v-chip>
              <v-chip color="error" variant="tonal">
                <v-icon start size="small">mdi-alert-circle</v-icon>
                Fehler
              </v-chip>
            </div>

            <h3 class="text-h6 mb-3">Aktions-Buttons</h3>
            <v-table density="compact">
              <thead><tr><th>Button</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="primary">Pending verarbeiten</v-chip></td><td>Alle wartenden Dokumente starten</td></tr>
                <tr><td><v-chip size="small" color="warning">Gefilterte analysieren</v-chip></td><td>Gefilterte Dokumente erneut mit KI prüfen</td></tr>
                <tr><td><v-chip size="small" color="error">Verarbeitung stoppen</v-chip></td><td>Laufende Verarbeitung abbrechen</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mt-4 mb-3">Verfügbare Filter</h3>
            <v-chip-group>
              <v-chip size="small" variant="outlined">Volltextsuche</v-chip>
              <v-chip size="small" variant="outlined">Gemeinde/Ort</v-chip>
              <v-chip size="small" variant="outlined">Kategorie</v-chip>
              <v-chip size="small" variant="outlined">Status</v-chip>
              <v-chip size="small" variant="outlined">Typ (PDF, HTML, ...)</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mt-4 mb-3">Dokument-Details</h3>
            <v-expansion-panels variant="accordion">
              <v-expansion-panel title="Tab: Info">
                <v-expansion-panel-text>
                  <ul class="pl-4">
                    <li>Original-URL mit Link</li>
                    <li>Quelle und Kategorie</li>
                    <li>Zeitstempel (entdeckt, geladen, verarbeitet)</li>
                    <li>Dateigröße und Seitenanzahl</li>
                    <li>Anzahl KI-Extraktionen</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel title="Tab: Text">
                <v-expansion-panel-text>
                  Zeigt den extrahierten Rohtext des Dokuments in einem Textfeld.
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel title="Tab: Extrahierte Daten">
                <v-expansion-panel-text>
                  <ul class="pl-4">
                    <li>KI-Analyse-Ergebnisse als JSON</li>
                    <li>Konfidenz-Score pro Extraktion</li>
                    <li>Verifizierungs-Status</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>

        <!-- Gemeinden -->
        <v-card id="municipalities" class="mb-4">
          <v-card-title class="text-h5 bg-indigo">
            <v-icon class="mr-2">mdi-city</v-icon>
            Gemeinden / Locations
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">Übersicht aller Standorte mit aggregierten Daten und Detail-Reports.</p>

            <h3 class="text-h6 mb-3">Statistik-Karten</h3>
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-subtitle-1">Gemeinden</div>
                  <div class="text-caption">Anzahl Standorte</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="primary">
                  <div class="text-subtitle-1">Dokumente</div>
                  <div class="text-caption">Gesamtzahl</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="success">
                  <div class="text-subtitle-1">Relevante</div>
                  <div class="text-caption">Mit Ergebnissen</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="warning">
                  <div class="text-subtitle-1">High Priority</div>
                  <div class="text-caption">Prioritäre Gemeinden</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">Tabellen-Spalten</h3>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>Spalte</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><v-icon size="small">mdi-city</v-icon> <strong>Name</strong></td><td>Gemeindename (klickbar für Report)</td></tr>
                <tr><td><strong>Admin Level 1/2</strong></td><td>Bundesland / Landkreis</td></tr>
                <tr><td><v-chip size="x-small" color="info">Quellen</v-chip></td><td>Anzahl verknüpfter Datenquellen</td></tr>
                <tr><td><strong>Dokumente</strong></td><td>Chips: Gesamt / Relevant / High Priority / Opportunity Score</td></tr>
                <tr><td><strong>Konfidenz</strong></td><td>Durchschnittliche KI-Konfidenz als Fortschrittsbalken</td></tr>
                <tr><td><v-chip size="x-small" color="info">Entscheider</v-chip></td><td>Anzahl gefundener Entscheidungsträger</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">Filter</h3>
            <v-chip-group class="mb-4">
              <v-chip size="small" variant="outlined">Land</v-chip>
              <v-chip size="small" variant="outlined">Bundesland (Admin Level 1)</v-chip>
              <v-chip size="small" variant="outlined">Landkreis (Admin Level 2)</v-chip>
              <v-chip size="small" variant="outlined">Kategorie</v-chip>
              <v-chip size="small" variant="outlined">Min. Konfidenz</v-chip>
              <v-chip size="small" variant="outlined">Suche</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">Gemeinde-Report (Detail-Dialog)</h3>
            <p class="mb-2">Klicken Sie auf eine Zeile oder das Auge-Symbol für den vollständigen Report:</p>

            <v-alert type="info" variant="tonal" class="mb-3">
              <strong>Report-Header:</strong> Gemeindename, Opportunity Score, Kategorie-Zweck
            </v-alert>

            <h4 class="text-subtitle-1 mb-2">Übersichts-Karten</h4>
            <v-row class="mb-3">
              <v-col cols="3"><v-chip size="small" variant="outlined">Dokumente</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined" color="success">Relevant</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined">Konfidenz %</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined" color="warning">Priorität</v-chip></v-col>
            </v-row>

            <h4 class="text-subtitle-1 mb-2">Report-Tabs</h4>
            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-account-group</v-icon> Entscheider
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Liste aller identifizierten Entscheidungsträger mit Name, Rolle, Kontakt und zugehörigen Dokumenten
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="error">mdi-alert</v-icon> Pain Points
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Kritische Punkte und Hindernisse, die aus Dokumenten extrahiert wurden. Mit Typ, Schwere und Quell-Dokument.
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="success">mdi-thumb-up</v-icon> Positive Signale
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Chancen und positive Entwicklungen. Mit Typ, Priorität und Quell-Dokument.
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-text</v-icon> Zusammenfassungen
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  KI-generierte Zusammenfassungen pro Dokument (expandierbar)
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-web</v-icon> Datenquellen
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Alle verknüpften Quellen dieser Gemeinde mit Status und letztem Crawl-Datum
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-database-sync</v-icon> PySis (Optional)
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Integration mit externem Prozess-Management-System (falls konfiguriert)
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mt-4 mb-3">Location-Verwaltung (Admin)</h3>
            <v-table density="compact">
              <thead><tr><th>Funktion</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="primary">Neue Location</v-chip></td><td>Standort manuell anlegen</td></tr>
                <tr><td><v-icon size="small">mdi-pencil</v-icon> Bearbeiten</td><td>Name, Land, Admin-Levels ändern</td></tr>
                <tr><td><v-icon size="small">mdi-eye</v-icon> Report anzeigen</td><td>Detail-Report öffnen</td></tr>
                <tr><td><v-icon size="small">mdi-file-document-multiple</v-icon> Dokumente</td><td>Alle Dokumente dieser Location</td></tr>
                <tr><td><strong>Quellen verknüpfen</strong></td><td>Automatische Verknüpfung anhand Location-Name</td></tr>
                <tr><td><strong>Admin-Levels anreichern</strong></td><td>Bundesland/Landkreis via Geocoding ermitteln</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Entity-Facet System -->
        <v-card id="entity-facet" class="mb-4">
          <v-card-title class="text-h5 bg-deep-purple">
            <v-icon class="mr-2">mdi-database</v-icon>
            Entity-Facet System
          </v-card-title>
          <v-card-text class="pt-4">
            <v-alert type="info" variant="tonal" class="mb-4">
              <strong>NEU:</strong> Das Entity-Facet System ermoeglicht eine flexible, generische Datenstruktur
              fuer verschiedene Analyse-Szenarien - von Pain-Point-Analysen ueber Event-Tracking bis hin zu
              Entscheider-Profilen.
            </v-alert>

            <h3 class="text-h6 mb-3">Konzept: Was sind Entities und Facets?</h3>
            <p class="mb-4">
              Das System basiert auf zwei Hauptkonzepten:
            </p>

            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="h-100">
                  <v-card-title class="text-subtitle-1">
                    <v-icon class="mr-2" color="primary">mdi-cube</v-icon>
                    Entities (Objekte)
                  </v-card-title>
                  <v-card-text>
                    <p class="mb-2">Grundlegende Objekte, die analysiert werden:</p>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-city">
                        <v-list-item-title><strong>Municipality</strong> - Gemeinden, Staedte</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-account">
                        <v-list-item-title><strong>Person</strong> - Entscheider, Kontakte</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-domain">
                        <v-list-item-title><strong>Organization</strong> - Behoerden, Unternehmen</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-calendar">
                        <v-list-item-title><strong>Event</strong> - Veranstaltungen, Sitzungen</v-list-item-title>
                      </v-list-item>
                    </v-list>
                    <p class="text-caption mt-2">Entity-Typen sind konfigurierbar und erweiterbar.</p>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="h-100">
                  <v-card-title class="text-subtitle-1">
                    <v-icon class="mr-2" color="success">mdi-tag-multiple</v-icon>
                    Facets (Eigenschaften)
                  </v-card-title>
                  <v-card-text>
                    <p class="mb-2">Dynamische Eigenschaften, die Entities zugeordnet werden:</p>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-alert-circle" color="error">
                        <v-list-item-title><strong>Pain Point</strong> - Probleme, Herausforderungen</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-thumb-up" color="success">
                        <v-list-item-title><strong>Positive Signal</strong> - Positive Signale</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-card-account-details">
                        <v-list-item-title><strong>Contact</strong> - Kontaktdaten</v-list-item-title>
                      </v-list-item>
                      <v-list-item prepend-icon="mdi-calendar-check">
                        <v-list-item-title><strong>Event Attendance</strong> - Veranstaltungsteilnahme</v-list-item-title>
                      </v-list-item>
                    </v-list>
                    <p class="text-caption mt-2">Facet-Typen koennen individuell definiert werden.</p>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">Verknuepfungen (Relations)</h3>
            <p class="mb-3">Entities koennen miteinander verknuepft werden:</p>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>Beziehungstyp</th><th>Beschreibung</th><th>Beispiel</th></tr></thead>
              <tbody>
                <tr>
                  <td><strong>works_for</strong></td>
                  <td>Person arbeitet fuer Organisation/Gemeinde</td>
                  <td>Max Mustermann → Buergermeister → Gemeinde Musterstadt</td>
                </tr>
                <tr>
                  <td><strong>member_of</strong></td>
                  <td>Person ist Mitglied einer Organisation</td>
                  <td>Person → Mitglied → Gemeinderat</td>
                </tr>
                <tr>
                  <td><strong>attends</strong></td>
                  <td>Person nimmt an Event teil</td>
                  <td>Person → Teilnehmer → Windenergie-Konferenz</td>
                </tr>
                <tr>
                  <td><strong>organizes</strong></td>
                  <td>Organisation organisiert Event</td>
                  <td>Landratsamt → Veranstalter → Buergerversammlung</td>
                </tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">Zeitbasierte Facets</h3>
            <v-alert type="warning" variant="tonal" class="mb-4">
              Einige Facet-Typen unterstuetzen <strong>zeitbasierte Filterung</strong>:
              <v-list density="compact" class="bg-transparent">
                <v-list-item prepend-icon="mdi-calendar-arrow-right">
                  <v-list-item-title><strong>future_only</strong> - Nur zukuenftige Events (z.B. anstehende Veranstaltungen)</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-calendar-arrow-left">
                  <v-list-item-title><strong>past_only</strong> - Nur vergangene Events (z.B. historische Daten)</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-calendar-range">
                  <v-list-item-title><strong>all</strong> - Alle Zeitraeume (Standard)</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-alert>

            <h3 class="text-h6 mb-3">Analyse-Templates</h3>
            <p class="mb-3">
              Templates definieren, welche Facets fuer welche Entity-Typen relevant sind und wie sie
              aggregiert und dargestellt werden:
            </p>
            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-chart-timeline-variant</v-icon>
                  Pain-Point-Analyse (Standard)
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>Aggregiert Pain Points und Positive Signale pro Gemeinde:</p>
                  <v-list density="compact">
                    <v-list-item>Primary Entity Type: <strong>Municipality</strong></v-list-item>
                    <v-list-item>Aktive Facets: Pain Point, Positive Signal</v-list-item>
                    <v-list-item>Gruppierung: Nach Gemeinde</v-list-item>
                    <v-list-item>Sortierung: Nach Opportunity Score</v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-calendar-multiple</v-icon>
                  Event-Tracking
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>Verfolgt Veranstaltungen und Teilnehmer:</p>
                  <v-list density="compact">
                    <v-list-item>Primary Entity Type: <strong>Event</strong></v-list-item>
                    <v-list-item>Aktive Facets: Event Attendance</v-list-item>
                    <v-list-item>Zeitfilter: future_only (nur anstehende Events)</v-list-item>
                    <v-list-item>Verknuepfungen: Person attends Event</v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-account-network</v-icon>
                  Entscheider-Profil
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>Erstellt Profile von Entscheidungstraegern:</p>
                  <v-list density="compact">
                    <v-list-item>Primary Entity Type: <strong>Person</strong></v-list-item>
                    <v-list-item>Aktive Facets: Contact, Event Attendance</v-list-item>
                    <v-list-item>Verknuepfungen: works_for Municipality, member_of Organization</v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mb-3">Entities-Ansicht</h3>
            <p class="mb-3">Ueber <strong>Entities</strong> im Hauptmenue erreichen Sie die neue generische Ansicht:</p>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>Funktion</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><strong>Entity-Typ Tabs</strong></td><td>Wechseln zwischen verschiedenen Entity-Typen (Gemeinden, Personen, etc.)</td></tr>
                <tr><td><strong>Tabellen- / Kartenansicht</strong></td><td>Umschalten zwischen Tabellenansicht und Kartenansicht</td></tr>
                <tr><td><strong>Filter</strong></td><td>Nach Kategorie, uebergeordnetem Element, Facet-Typen filtern</td></tr>
                <tr><td><strong>Facet-Uebersicht</strong></td><td>Zeigt aggregierte Facet-Zaehler pro Entity</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">Entity-Detail-Ansicht</h3>
            <p class="mb-3">Klicken Sie auf eine Entity fuer die Detailansicht:</p>
            <v-row class="mb-4">
              <v-col cols="12" md="6">
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">Tabs</v-card-title>
                  <v-card-text>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-tag-multiple"><strong>Facets</strong> - Alle Facet-Werte gruppiert nach Typ</v-list-item>
                      <v-list-item prepend-icon="mdi-link"><strong>Verknuepfungen</strong> - Relations zu anderen Entities</v-list-item>
                      <v-list-item prepend-icon="mdi-web"><strong>Datenquellen</strong> - Verknuepfte Crawl-Quellen</v-list-item>
                      <v-list-item prepend-icon="mdi-file-document-multiple"><strong>Dokumente</strong> - Gefundene Dokumente</v-list-item>
                      <v-list-item prepend-icon="mdi-database-sync"><strong>PySis</strong> - Integration (fuer Gemeinden)</v-list-item>
                    </v-list>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined">
                  <v-card-title class="text-subtitle-1">Aktionen</v-card-title>
                  <v-card-text>
                    <v-list density="compact">
                      <v-list-item prepend-icon="mdi-plus"><strong>Facet hinzufuegen</strong> - Manuell neue Werte erfassen</v-list-item>
                      <v-list-item prepend-icon="mdi-check"><strong>Verifizieren</strong> - KI-Ergebnisse bestaetigen</v-list-item>
                      <v-list-item prepend-icon="mdi-pencil"><strong>Bearbeiten</strong> - Entity-Daten anpassen</v-list-item>
                      <v-list-item prepend-icon="mdi-play"><strong>Crawl starten</strong> - Datenquellen aktualisieren</v-list-item>
                    </v-list>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">KI-Integration</h3>
            <p class="mb-3">
              Das Entity-Facet System ist eng mit der KI-Analyse integriert:
            </p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-robot">
                <v-list-item-title><strong>Automatische Extraktion</strong></v-list-item-title>
                <v-list-item-subtitle>Die KI extrahiert Facet-Werte aus Dokumenten basierend auf dem Facet-Typ</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-text-box-search">
                <v-list-item-title><strong>Facet-spezifische Prompts</strong></v-list-item-title>
                <v-list-item-subtitle>Jeder Facet-Typ hat einen eigenen Extraktions-Prompt</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-percent">
                <v-list-item-title><strong>Konfidenz-Bewertung</strong></v-list-item-title>
                <v-list-item-subtitle>Die KI bewertet die Zuverlaessigkeit jedes extrahierten Wertes</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-check-decagram">
                <v-list-item-title><strong>Human-in-the-Loop</strong></v-list-item-title>
                <v-list-item-subtitle>Manuelle Verifizierung zur Qualitaetssicherung</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <h3 class="text-h6 mb-3">Best Practices</h3>
            <v-alert type="success" variant="tonal">
              <v-list density="compact" class="bg-transparent">
                <v-list-item prepend-icon="mdi-lightbulb">
                  <v-list-item-title>Starten Sie mit vordefinierten Entity-Typen</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-lightbulb">
                  <v-list-item-title>Nutzen Sie Analyse-Templates fuer konsistente Auswertungen</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-lightbulb">
                  <v-list-item-title>Verifizieren Sie KI-Ergebnisse regelmaessig</v-list-item-title>
                </v-list-item>
                <v-list-item prepend-icon="mdi-lightbulb">
                  <v-list-item-title>Nutzen Sie zeitbasierte Filter fuer Event-Tracking</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- Ergebnisse -->
        <v-card id="results" class="mb-4">
          <v-card-title class="text-h5 bg-orange">
            <v-icon class="mr-2">mdi-chart-bar</v-icon>
            Ergebnisse
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">Zentrale Ansicht aller KI-extrahierten Daten.</p>

            <h3 class="text-h6 mb-3">Statistik-Karten</h3>
            <v-row class="mb-4">
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-subtitle-1">Gesamt</div>
                  <div class="text-caption">Alle Extraktionen</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="success">
                  <div class="text-subtitle-1">Verifiziert</div>
                  <div class="text-caption">Manuell bestätigt</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2" color="info">
                  <div class="text-subtitle-1">Hohe Konfidenz</div>
                  <div class="text-caption">≥80% Sicherheit</div>
                </v-card>
              </v-col>
              <v-col cols="6" md="3">
                <v-card variant="outlined" class="text-center pa-2">
                  <div class="text-subtitle-1">Durchschnitt</div>
                  <div class="text-caption">Ø Konfidenz</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">Verfügbare Filter</h3>
            <v-chip-group class="mb-4">
              <v-chip size="small" variant="outlined">Land</v-chip>
              <v-chip size="small" variant="outlined">Gemeinde/Ort (Autocomplete)</v-chip>
              <v-chip size="small" variant="outlined">Kategorie</v-chip>
              <v-chip size="small" variant="outlined">Min. Konfidenz (Slider)</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">Was wird extrahiert?</h3>
            <v-list density="compact">
              <v-list-item prepend-icon="mdi-tag">
                <v-list-item-title>Thema & Zusammenfassung</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-emoticon-sad">
                <v-list-item-title>Pain Points</v-list-item-title>
                <v-list-item-subtitle>Kritische Punkte, Hindernisse, Probleme</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-emoticon-happy">
                <v-list-item-title>Opportunities</v-list-item-title>
                <v-list-item-subtitle>Chancen, positive Entwicklungen</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-emoticon-neutral">
                <v-list-item-title>Sentiment</v-list-item-title>
                <v-list-item-subtitle>Positiv / Neutral / Negativ</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-percent">
                <v-list-item-title>Konfidenz-Score</v-list-item-title>
                <v-list-item-subtitle>Wie sicher ist die KI (0-100%)</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <h3 class="text-h6 mt-4 mb-3">Detail-Dialog</h3>
            <p class="mb-2">Klicken Sie auf das Auge-Symbol, um Details zu sehen:</p>

            <h4 class="text-subtitle-1 mb-2">Header</h4>
            <v-list density="compact" class="mb-3">
              <v-list-item prepend-icon="mdi-text">Thema der Extraktion</v-list-item>
              <v-list-item prepend-icon="mdi-percent">Konfidenz mit Farb-Chip</v-list-item>
              <v-list-item prepend-icon="mdi-link">Dokument-Link + Quelle</v-list-item>
            </v-list>

            <h4 class="text-subtitle-1 mb-2">Info-Karten</h4>
            <v-row class="mb-3">
              <v-col cols="3"><v-chip size="small" variant="outlined" color="success">Relevant?</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined">Relevanz</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined">Gemeinde</v-chip></v-col>
              <v-col cols="3"><v-chip size="small" variant="outlined" color="warning">Priorität</v-chip></v-col>
            </v-row>

            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel title="Zusammenfassung">
                <v-expansion-panel-text>
                  KI-generierte Zusammenfassung des Inhalts
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="error">mdi-alert</v-icon> Pain Points
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Expandierbare Liste mit kritischen Punkten aus dem Dokument
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="success">mdi-thumb-up</v-icon> Positive Signale
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Expandierbare Liste mit Chancen und positiven Entwicklungen
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2" color="primary">mdi-account-group</v-icon> Entscheider
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Identifizierte Entscheidungsträger mit Name und Rolle
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon class="mr-2">mdi-code-json</v-icon> Raw JSON
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  Vollständige KI-Antwort im JSON-Format zur Analyse
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <v-alert type="success" variant="tonal" density="compact" class="mb-4">
              <strong>Tipp:</strong> Nutzen Sie "Dokument öffnen" um das Original anzuzeigen.
            </v-alert>

            <h3 class="text-h6 mt-4 mb-3">Konfidenz verstehen</h3>
            <v-table density="compact">
              <thead><tr><th>Bereich</th><th>Bedeutung</th><th>Empfehlung</th></tr></thead>
              <tbody>
                <tr>
                  <td><v-chip size="small" color="error">0-50%</v-chip></td>
                  <td>Geringe Sicherheit</td>
                  <td>Kritisch prüfen</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="warning">50-70%</v-chip></td>
                  <td>Mittlere Sicherheit</td>
                  <td>Stichproben prüfen</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="success">70-100%</v-chip></td>
                  <td>Hohe Sicherheit</td>
                  <td>Meist zuverlässig</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Export -->
        <v-card id="export" class="mb-4">
          <v-card-title class="text-h5 bg-deep-purple">
            <v-icon class="mr-2">mdi-export</v-icon>
            Export
          </v-card-title>
          <v-card-text class="pt-4">
            <h3 class="text-h6 mb-3">Export-Formate</h3>
            <v-row class="mb-4">
              <v-col cols="6">
                <v-card variant="outlined" class="pa-3 text-center">
                  <v-icon size="48" color="primary">mdi-code-json</v-icon>
                  <div class="text-h6">JSON</div>
                  <div class="text-caption">Strukturiert mit allen Details</div>
                </v-card>
              </v-col>
              <v-col cols="6">
                <v-card variant="outlined" class="pa-3 text-center">
                  <v-icon size="48" color="success">mdi-file-delimited</v-icon>
                  <div class="text-h6">CSV</div>
                  <div class="text-caption">Tabellenformat für Excel</div>
                </v-card>
              </v-col>
            </v-row>

            <h3 class="text-h6 mb-3">Export-Filter</h3>
            <v-chip-group class="mb-4">
              <v-chip size="small" variant="outlined">Land</v-chip>
              <v-chip size="small" variant="outlined">Gemeinde/Ort</v-chip>
              <v-chip size="small" variant="outlined">Kategorie</v-chip>
              <v-chip size="small" variant="outlined">Mindest-Konfidenz (Slider)</v-chip>
              <v-chip size="small" variant="outlined">Nur verifizierte Daten</v-chip>
            </v-chip-group>

            <h3 class="text-h6 mb-3">Webhook Test</h3>
            <p class="mb-2">Testen Sie Webhook-Integrationen mit externen Systemen:</p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-link">
                <v-list-item-title>Webhook-URL eingeben</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-send">
                <v-list-item-title>Test-Request senden</v-list-item-title>
              </v-list-item>
              <v-list-item prepend-icon="mdi-check">
                <v-list-item-title>Ergebnis mit Status-Code anzeigen</v-list-item-title>
              </v-list-item>
            </v-list>

            <h3 class="text-h6 mb-3">Änderungs-Feed</h3>
            <p class="mb-2">Zeigt die letzten Änderungen im System:</p>
            <v-table density="compact" class="mb-4">
              <thead><tr><th>Änderungstyp</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><v-chip size="small" color="success">NEW</v-chip></td><td>Neue Extraktion hinzugefügt</td></tr>
                <tr><td><v-chip size="small" color="info">UPDATED</v-chip></td><td>Bestehende Extraktion aktualisiert</td></tr>
                <tr><td><v-chip size="small" color="warning">VERIFIED</v-chip></td><td>Manuell verifiziert</td></tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">API-Endpunkte</h3>
            <v-table density="compact">
              <thead><tr><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
              <tbody>
                <tr><td><code>GET /api/v1/data</code></td><td>Extrahierte Daten abrufen</td></tr>
                <tr><td><code>GET /api/v1/data/documents</code></td><td>Dokumente abrufen</td></tr>
                <tr><td><code>GET /api/v1/data/search?q=...</code></td><td>Volltextsuche</td></tr>
                <tr><td><code>GET /api/v1/export/json</code></td><td>JSON-Export (mit Filtern)</td></tr>
                <tr><td><code>GET /api/v1/export/csv</code></td><td>CSV-Export (mit Filtern)</td></tr>
                <tr><td><code>GET /api/v1/export/changes</code></td><td>Änderungs-Feed</td></tr>
                <tr><td><code>POST /api/v1/export/webhook/test</code></td><td>Webhook testen</td></tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

        <!-- Benachrichtigungen -->
        <v-card id="notifications" class="mb-4">
          <v-card-title class="text-h5 bg-orange-darken-2">
            <v-icon class="mr-2">mdi-bell</v-icon>
            Benachrichtigungen
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">
              Das Benachrichtigungssystem ermoeglicht es Ihnen, automatisch ueber wichtige Ereignisse
              informiert zu werden - per E-Mail, Webhook oder In-App-Benachrichtigung.
            </p>

            <h3 class="text-h6 mb-3">Uebersicht</h3>
            <p class="mb-4">
              Unter <strong>Benachrichtigungen</strong> (erreichbar ueber das Glocken-Symbol in der
              App-Leiste) finden Sie drei Bereiche:
            </p>

            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-inbox">
                <v-list-item-title><strong>Posteingang</strong></v-list-item-title>
                <v-list-item-subtitle>Alle Ihre Benachrichtigungen mit Filterfunktionen</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-filter-cog">
                <v-list-item-title><strong>Regeln</strong></v-list-item-title>
                <v-list-item-subtitle>Erstellen und verwalten Sie Benachrichtigungsregeln</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-cog">
                <v-list-item-title><strong>Einstellungen</strong></v-list-item-title>
                <v-list-item-subtitle>Allgemeine Einstellungen und E-Mail-Adressen verwalten</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">Event-Typen</h3>
            <p class="mb-4">Folgende Ereignisse koennen Benachrichtigungen ausloesen:</p>

            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>Event</th><th>Beschreibung</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><v-chip size="small" color="success">Neues Dokument</v-chip></td>
                  <td>Ein neues Dokument wurde beim Crawling gefunden</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="info">Dokument geaendert</v-chip></td>
                  <td>Ein bestehendes Dokument wurde aktualisiert</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="error">Dokument entfernt</v-chip></td>
                  <td>Ein Dokument ist nicht mehr verfuegbar</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="purple">Crawl gestartet</v-chip></td>
                  <td>Ein Crawl-Job wurde gestartet</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="success">Crawl abgeschlossen</v-chip></td>
                  <td>Ein Crawl-Job wurde erfolgreich beendet</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="error">Crawl fehlgeschlagen</v-chip></td>
                  <td>Ein Crawl-Job ist mit Fehlern beendet</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="cyan">KI-Analyse abgeschlossen</v-chip></td>
                  <td>Die KI-Analyse eines Dokuments ist fertig</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="orange">Hohe Konfidenz</v-chip></td>
                  <td>Ein KI-Ergebnis mit hoher Konfidenz wurde gefunden</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="grey">Quellenstatus geaendert</v-chip></td>
                  <td>Der Status einer Datenquelle hat sich geaendert</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="error">Quellenfehler</v-chip></td>
                  <td>Es gab einen Fehler bei einer Datenquelle</td>
                </tr>
              </tbody>
            </v-table>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">Benachrichtigungskanaele</h3>

            <v-row class="mb-4">
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <div class="d-flex align-center mb-2">
                    <v-icon color="blue" class="mr-2">mdi-email</v-icon>
                    <strong>E-Mail</strong>
                  </div>
                  <p class="text-body-2">
                    Erhalten Sie Benachrichtigungen per E-Mail. Sie koennen mehrere E-Mail-Adressen
                    hinterlegen und pro Regel auswaehlen, welche Adressen benachrichtigt werden sollen.
                  </p>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <div class="d-flex align-center mb-2">
                    <v-icon color="purple" class="mr-2">mdi-webhook</v-icon>
                    <strong>Webhook</strong>
                  </div>
                  <p class="text-body-2">
                    Senden Sie Benachrichtigungen an einen HTTP-Endpunkt. Unterstuetzt werden
                    Bearer-Token, API-Key und Basic-Authentifizierung.
                  </p>
                </v-card>
              </v-col>
              <v-col cols="12" md="4">
                <v-card variant="outlined" class="pa-3">
                  <div class="d-flex align-center mb-2">
                    <v-icon color="green" class="mr-2">mdi-bell-ring</v-icon>
                    <strong>In-App</strong>
                  </div>
                  <p class="text-body-2">
                    Benachrichtigungen werden im Posteingang angezeigt. Das Glocken-Symbol zeigt
                    die Anzahl ungelesener Nachrichten an.
                  </p>
                </v-card>
              </v-col>
            </v-row>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">Regeln erstellen</h3>
            <p class="mb-4">So erstellen Sie eine neue Benachrichtigungsregel:</p>

            <v-timeline density="compact" side="end" class="mb-4">
              <v-timeline-item dot-color="primary" size="small">
                <template v-slot:opposite><strong>1</strong></template>
                <div>
                  <strong>Grundeinstellungen</strong><br>
                  Vergeben Sie einen Namen und waehlen Sie den Event-Typ aus.
                </div>
              </v-timeline-item>
              <v-timeline-item dot-color="success" size="small">
                <template v-slot:opposite><strong>2</strong></template>
                <div>
                  <strong>Kanal waehlen</strong><br>
                  Waehlen Sie E-Mail, Webhook oder In-App als Benachrichtigungskanal.
                </div>
              </v-timeline-item>
              <v-timeline-item dot-color="warning" size="small">
                <template v-slot:opposite><strong>3</strong></template>
                <div>
                  <strong>Filter konfigurieren (optional)</strong><br>
                  Schraenken Sie ein, fuer welche Kategorien, Quellen oder Konfidenzwerte
                  die Regel gelten soll.
                </div>
              </v-timeline-item>
              <v-timeline-item dot-color="info" size="small">
                <template v-slot:opposite><strong>4</strong></template>
                <div>
                  <strong>Kanal-spezifische Einstellungen</strong><br>
                  Bei E-Mail: Waehlen Sie Empfaenger. Bei Webhook: Geben Sie URL und
                  Authentifizierung an.
                </div>
              </v-timeline-item>
            </v-timeline>

            <h3 class="text-h6 mb-3">Filteroptionen</h3>
            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>Filter</th><th>Beschreibung</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Kategorien</strong></td>
                  <td>Nur bei Ereignissen in bestimmten Kategorien benachrichtigen</td>
                </tr>
                <tr>
                  <td><strong>Datenquellen</strong></td>
                  <td>Nur bei Ereignissen von bestimmten Quellen benachrichtigen</td>
                </tr>
                <tr>
                  <td><strong>Min. Konfidenz</strong></td>
                  <td>Nur bei KI-Ergebnissen ueber einem Schwellenwert (0.0 - 1.0)</td>
                </tr>
                <tr>
                  <td><strong>Schluesselwoerter</strong></td>
                  <td>Nur wenn bestimmte Begriffe im Dokument vorkommen</td>
                </tr>
              </tbody>
            </v-table>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">Digest-Modus</h3>
            <p class="mb-4">
              Statt jeder einzelnen Benachrichtigung koennen Sie einen Digest aktivieren:
            </p>
            <v-alert type="info" variant="tonal" class="mb-4">
              <strong>Digest-Funktion:</strong> Sammelt mehrere Benachrichtigungen und sendet
              sie gebuendelt (stuendlich, taeglich oder woechentlich). Die Digest-Zeit koennen
              Sie in den Einstellungen festlegen.
            </v-alert>

            <h3 class="text-h6 mb-3">E-Mail-Adressen verwalten</h3>
            <p class="mb-4">
              Unter <strong>Einstellungen</strong> koennen Sie zusaetzliche E-Mail-Adressen
              hinterlegen:
            </p>
            <v-list density="compact" class="mb-4">
              <v-list-item prepend-icon="mdi-plus">
                <v-list-item-title>Adresse hinzufuegen</v-list-item-title>
                <v-list-item-subtitle>Geben Sie eine E-Mail und optional eine Bezeichnung ein</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-email-check">
                <v-list-item-title>Verifizierung</v-list-item-title>
                <v-list-item-subtitle>Neue Adressen muessen per Bestaetigunslink verifiziert werden</v-list-item-subtitle>
              </v-list-item>
              <v-list-item prepend-icon="mdi-delete">
                <v-list-item-title>Loeschen</v-list-item-title>
                <v-list-item-subtitle>Nicht mehr benoetigte Adressen koennen entfernt werden</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-h6 mb-3">Webhook-Konfiguration</h3>
            <p class="mb-4">
              Fuer Webhook-Benachrichtigungen werden folgende Authentifizierungsmethoden unterstuetzt:
            </p>
            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>Methode</th><th>Beschreibung</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Keine</strong></td>
                  <td>Keine Authentifizierung (nur fuer interne Endpunkte empfohlen)</td>
                </tr>
                <tr>
                  <td><strong>Bearer Token</strong></td>
                  <td>Authorization: Bearer &lt;token&gt;</td>
                </tr>
                <tr>
                  <td><strong>API Key</strong></td>
                  <td>Custom Header mit API-Schluessel</td>
                </tr>
                <tr>
                  <td><strong>Basic Auth</strong></td>
                  <td>HTTP Basic Authentication (Benutzername/Passwort)</td>
                </tr>
              </tbody>
            </v-table>

            <v-alert type="warning" variant="tonal" class="mb-4">
              <strong>Webhook testen:</strong> Nutzen Sie die Test-Funktion, um zu pruefen, ob Ihr
              Endpunkt erreichbar ist und korrekt antwortet, bevor Sie die Regel aktivieren.
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- API Referenz -->
        <v-card id="api" class="mb-4">
          <v-card-title class="text-h5 bg-grey-darken-3">
            <v-icon class="mr-2">mdi-api</v-icon>
            API-Referenz
          </v-card-title>
          <v-card-text class="pt-4">
            <p class="mb-4">
              Vollständige Liste aller API-Endpunkte. Die interaktive API-Dokumentation (Swagger/OpenAPI)
              ist unter <code>/docs</code> verfügbar.
            </p>

            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="primary" class="mr-2">mdi-folder-multiple</v-icon>
                  Kategorien
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/categories</code></td><td>Liste aller Kategorien</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/categories</code></td><td>Neue Kategorie erstellen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/categories/{id}</code></td><td>Kategorie abrufen</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/categories/{id}</code></td><td>Kategorie aktualisieren</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/categories/{id}</code></td><td>Kategorie löschen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/categories/{id}/stats</code></td><td>Kategorie-Statistiken</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="teal" class="mr-2">mdi-web</v-icon>
                  Datenquellen
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/sources</code></td><td>Liste aller Quellen (mit Filtern)</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/sources</code></td><td>Neue Quelle erstellen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/sources/bulk-import</code></td><td>Mehrere Quellen importieren</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/sources/meta/countries</code></td><td>Verfügbare Länder</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/sources/meta/locations</code></td><td>Verfügbare Standorte</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/sources/{id}</code></td><td>Quelle abrufen</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/sources/{id}</code></td><td>Quelle aktualisieren</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/sources/{id}</code></td><td>Quelle löschen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/sources/{id}/reset</code></td><td>Quelle zurücksetzen</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="cyan" class="mr-2">mdi-robot</v-icon>
                  Crawler
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/start</code></td><td>Crawl starten</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/status</code></td><td>Crawler-Status (Worker, Queue)</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/stats</code></td><td>Crawler-Statistiken</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/running</code></td><td>Laufende Jobs</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/jobs</code></td><td>Alle Jobs (mit Filtern)</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/jobs/{id}</code></td><td>Job-Details</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/jobs/{id}/log</code></td><td>Job-Log</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/jobs/{id}/cancel</code></td><td>Job abbrechen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/reanalyze</code></td><td>Dokumente neu analysieren</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="purple" class="mr-2">mdi-brain</v-icon>
                  KI-Tasks & Dokumente
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/ai-tasks</code></td><td>Alle KI-Tasks</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/crawler/ai-tasks/running</code></td><td>Laufende KI-Tasks</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/ai-tasks/{id}/cancel</code></td><td>KI-Task abbrechen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/{id}/process</code></td><td>Dokument verarbeiten</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/{id}/analyze</code></td><td>Dokument analysieren</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/process-pending</code></td><td>Alle Pending verarbeiten</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/stop-all</code></td><td>Verarbeitung stoppen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/crawler/documents/reanalyze-filtered</code></td><td>Gefilterte neu analysieren</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="indigo" class="mr-2">mdi-map-marker</v-icon>
                  Locations
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations</code></td><td>Alle Locations</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/{id}</code></td><td>Einzelne Location abrufen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/search</code></td><td>Locations suchen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/with-sources</code></td><td>Locations mit Quellen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/countries</code></td><td>Verfügbare Länder</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/states</code></td><td>Bundesländer/States</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/locations/admin-levels</code></td><td>Admin-Levels (Level 1/2)</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/locations</code></td><td>Location erstellen</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/locations/{id}</code></td><td>Location aktualisieren</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/locations/{id}</code></td><td>Location löschen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/locations/link-sources</code></td><td>Quellen verknüpfen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/locations/enrich-admin-levels</code></td><td>Admin-Levels anreichern</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="info" class="mr-2">mdi-database-search</v-icon>
                  Public API (v1/data)
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data</code></td><td>Extrahierte Daten (mit Filtern)</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/stats</code></td><td>Extraktions-Statistiken</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/locations</code></td><td>Locations mit Extraktionen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/countries</code></td><td>Länder mit Extraktionen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/documents</code></td><td>Alle Dokumente</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/documents/{id}</code></td><td>Dokument-Details</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/documents/locations</code></td><td>Dokument-Locations</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/search</code></td><td>Volltextsuche</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/v1/data/extracted/{id}/verify</code></td><td>Extraktion verifizieren</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="orange" class="mr-2">mdi-city</v-icon>
                  Gemeinden & Reports
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/municipalities</code></td><td>Alle Gemeinden</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/municipalities/{name}/report</code></td><td>Gemeinde-Report</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/municipalities/{name}/documents</code></td><td>Gemeinde-Dokumente</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/report/overview</code></td><td>Übersichts-Report</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/history/municipalities</code></td><td>Gemeinde-Historie</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/data/history/crawls</code></td><td>Crawl-Historie</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="deep-purple" class="mr-2">mdi-export</v-icon>
                  Export
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/export/json</code></td><td>JSON-Export</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/export/csv</code></td><td>CSV-Export</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/v1/export/changes</code></td><td>Änderungs-Feed</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/v1/export/webhook/test</code></td><td>Webhook testen</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="pink" class="mr-2">mdi-sync</v-icon>
                  PySis Integration (Optional)
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-alert type="info" variant="tonal" class="mb-3">
                    PySis ist eine optionale Integration zur Synchronisation mit externen Prozess-Management-Systemen.
                    Erfordert Azure AD Konfiguration.
                  </v-alert>

                  <h4 class="text-subtitle-2 mb-2">Templates</h4>
                  <v-table density="compact" class="mb-4">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/templates</code></td><td>Alle Templates auflisten</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/templates</code></td><td>Template erstellen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/templates/{id}</code></td><td>Template abrufen</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/pysis/templates/{id}</code></td><td>Template aktualisieren</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/pysis/templates/{id}</code></td><td>Template löschen</td></tr>
                    </tbody>
                  </v-table>

                  <h4 class="text-subtitle-2 mb-2">Prozesse</h4>
                  <v-table density="compact" class="mb-4">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/available-processes</code></td><td>Verfügbare Prozesse</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/locations/{name}/processes</code></td><td>Prozesse einer Location</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/locations/{name}/processes</code></td><td>Prozess für Location erstellen</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/processes/{id}</code></td><td>Prozess-Details</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/pysis/processes/{id}</code></td><td>Prozess aktualisieren</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/pysis/processes/{id}</code></td><td>Prozess löschen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/apply-template</code></td><td>Template anwenden</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/generate</code></td><td>Felder KI-generieren</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/sync/pull</code></td><td>Von PySis laden</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/sync/push</code></td><td>Zu PySis senden</td></tr>
                    </tbody>
                  </v-table>

                  <h4 class="text-subtitle-2 mb-2">Felder</h4>
                  <v-table density="compact" class="mb-4">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/processes/{id}/fields</code></td><td>Felder eines Prozesses</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/processes/{id}/fields</code></td><td>Feld hinzufügen</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/pysis/fields/{id}</code></td><td>Feld aktualisieren</td></tr>
                      <tr><td><v-chip size="x-small" color="warning">PUT</v-chip></td><td><code>/api/admin/pysis/fields/{id}/value</code></td><td>Feld-Wert setzen</td></tr>
                      <tr><td><v-chip size="x-small" color="error">DELETE</v-chip></td><td><code>/api/admin/pysis/fields/{id}</code></td><td>Feld löschen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/generate</code></td><td>KI-Vorschlag generieren</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/accept-ai</code></td><td>KI-Vorschlag akzeptieren</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/reject-ai</code></td><td>KI-Vorschlag ablehnen</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/sync/push</code></td><td>Feld zu PySis senden</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/fields/{id}/history</code></td><td>Feld-Änderungshistorie</td></tr>
                      <tr><td><v-chip size="x-small" color="primary">POST</v-chip></td><td><code>/api/admin/pysis/fields/{id}/restore/{history_id}</code></td><td>Version wiederherstellen</td></tr>
                    </tbody>
                  </v-table>

                  <h4 class="text-subtitle-2 mb-2">Verbindung</h4>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/api/admin/pysis/test-connection</code></td><td>Verbindung testen</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="green" class="mr-2">mdi-heart-pulse</v-icon>
                  System & Health
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <thead><tr><th>Methode</th><th>Endpunkt</th><th>Beschreibung</th></tr></thead>
                    <tbody>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/</code></td><td>Root-Endpoint (API-Info)</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/health</code></td><td>Health-Check</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/docs</code></td><td>Swagger UI (interaktive Doku)</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/redoc</code></td><td>ReDoc (alternative Doku)</td></tr>
                      <tr><td><v-chip size="x-small" color="success">GET</v-chip></td><td><code>/openapi.json</code></td><td>OpenAPI Schema</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <v-alert type="info" variant="tonal" class="mt-4">
              <v-icon>mdi-information</v-icon>
              Die vollständige interaktive API-Dokumentation mit allen Parametern und Beispielen finden Sie unter
              <a href="/docs" target="_blank" class="text-primary">/docs</a> (Swagger UI) oder
              <a href="/redoc" target="_blank" class="text-primary">/redoc</a> (ReDoc).
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- Tipps -->
        <v-card id="tips" class="mb-4">
          <v-card-title class="text-h5 bg-amber">
            <v-icon class="mr-2">mdi-lightbulb</v-icon>
            Tipps & Best Practices
          </v-card-title>
          <v-card-text class="pt-4">
            <v-expansion-panels variant="accordion">
              <v-expansion-panel title="Effizientes Crawling">
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item prepend-icon="mdi-filter">
                      <v-list-item-title>URL-Filter nutzen</v-list-item-title>
                      <v-list-item-subtitle>Definieren Sie Include-Patterns für relevante Bereiche</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-stairs">
                      <v-list-item-title>Max. Tiefe begrenzen</v-list-item-title>
                      <v-list-item-subtitle>Starten Sie mit Tiefe 2-3, erhöhen Sie nur bei Bedarf</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-file-document">
                      <v-list-item-title>Dokumenttypen einschränken</v-list-item-title>
                      <v-list-item-subtitle>PDFs sind meist ergiebiger als HTML</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel title="Bessere KI-Ergebnisse">
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item prepend-icon="mdi-text-box">
                      <v-list-item-title>Präzise Prompts</v-list-item-title>
                      <v-list-item-subtitle>Definieren Sie klare JSON-Strukturen und geben Sie Beispiele</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-tag-multiple">
                      <v-list-item-title>Keyword-Optimierung</v-list-item-title>
                      <v-list-item-subtitle>Nutzen Sie domänenspezifische Begriffe inkl. Varianten</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-test-tube">
                      <v-list-item-title>Testen Sie zuerst</v-list-item-title>
                      <v-list-item-subtitle>Starten Sie mit wenigen Quellen, optimieren Sie dann</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel title="Organisation">
                <v-expansion-panel-text>
                  <v-list density="compact">
                    <v-list-item prepend-icon="mdi-folder-multiple">
                      <v-list-item-title>Kategorien sinnvoll trennen</v-list-item-title>
                      <v-list-item-subtitle>Eine Kategorie pro Themengebiet mit eigenem Prompt</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-map-marker">
                      <v-list-item-title>Standorte pflegen</v-list-item-title>
                      <v-list-item-subtitle>Weisen Sie jeder Quelle einen Standort zu</v-list-item-subtitle>
                    </v-list-item>
                    <v-list-item prepend-icon="mdi-update">
                      <v-list-item-title>Regelmäßige Pflege</v-list-item-title>
                      <v-list-item-subtitle>Prüfen Sie fehlerhafte Quellen und URLs</v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>

        <!-- Sicherheit & Authentifizierung -->
        <v-card id="security" class="mb-4">
          <v-card-title class="text-h5 bg-purple">
            <v-icon class="mr-2">mdi-shield-lock</v-icon>
            Sicherheit & Authentifizierung
          </v-card-title>
          <v-card-text class="pt-4">
            <h3 class="text-h6 mb-3">Anmeldung (Login)</h3>
            <p class="mb-4">
              CaeliCrawler verwendet ein sicheres JWT-basiertes Authentifizierungssystem.
              Nach der Anmeldung erhalten Sie einen Token, der bei jeder Anfrage automatisch
              mitgesendet wird.
            </p>

            <v-alert type="info" variant="tonal" class="mb-4">
              <strong>Wichtig:</strong> Nach 24 Stunden Inaktivität werden Sie automatisch abgemeldet.
              Bei einem Logout wird der Token sofort invalidiert.
            </v-alert>

            <h3 class="text-h6 mb-3">Benutzerrollen</h3>
            <v-table density="compact" class="mb-4">
              <thead>
                <tr><th>Rolle</th><th>Berechtigungen</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td><v-chip size="small" color="error">ADMIN</v-chip></td>
                  <td>
                    <ul class="pl-4">
                      <li>Vollzugriff auf alle Funktionen</li>
                      <li>Benutzerverwaltung (anlegen, bearbeiten, löschen)</li>
                      <li>Zugriff auf Audit-Log und Versionshistorie</li>
                      <li>Systemkonfiguration</li>
                    </ul>
                  </td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="warning">EDITOR</v-chip></td>
                  <td>
                    <ul class="pl-4">
                      <li>Kategorien und Datenquellen verwalten</li>
                      <li>Crawler starten und stoppen</li>
                      <li>Dokumente verarbeiten und analysieren</li>
                      <li>Ergebnisse exportieren</li>
                    </ul>
                  </td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="info">VIEWER</v-chip></td>
                  <td>
                    <ul class="pl-4">
                      <li>Alle Daten einsehen</li>
                      <li>Ergebnisse exportieren</li>
                      <li>Keine Bearbeitungsrechte</li>
                    </ul>
                  </td>
                </tr>
              </tbody>
            </v-table>

            <h3 class="text-h6 mb-3">Passwort-Richtlinien</h3>
            <v-alert type="warning" variant="tonal" class="mb-4">
              <strong>Anforderungen:</strong>
              <ul class="pl-4 mt-2">
                <li>Mindestens 8 Zeichen</li>
                <li>Mindestens ein Großbuchstabe (A-Z)</li>
                <li>Mindestens ein Kleinbuchstabe (a-z)</li>
                <li>Mindestens eine Ziffer (0-9)</li>
                <li>Sonderzeichen empfohlen (erhöht den Sicherheitsscore)</li>
              </ul>
            </v-alert>

            <h3 class="text-h6 mb-3">Sicherheitsfeatures</h3>
            <v-expansion-panels variant="accordion" class="mb-4">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="success" class="mr-2">mdi-shield-check</v-icon>
                  Rate Limiting (Brute-Force-Schutz)
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>Das System schützt vor automatisierten Anmeldeversachen:</p>
                  <v-table density="compact" class="mt-2">
                    <thead><tr><th>Aktion</th><th>Limit</th><th>Zeitfenster</th></tr></thead>
                    <tbody>
                      <tr><td>Login-Versuche</td><td>5</td><td>pro Minute</td></tr>
                      <tr><td>Fehlgeschlagene Logins</td><td>10</td><td>pro 15 Minuten</td></tr>
                      <tr><td>Passwort-Änderungen</td><td>3</td><td>pro 5 Minuten</td></tr>
                      <tr><td>API-Anfragen allgemein</td><td>100</td><td>pro Minute</td></tr>
                    </tbody>
                  </v-table>
                  <v-alert type="info" variant="tonal" class="mt-2" density="compact">
                    Bei Überschreitung erhalten Sie eine Fehlermeldung mit der verbleibenden Wartezeit.
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="success" class="mr-2">mdi-logout</v-icon>
                  Token Blacklist (Sofortiger Logout)
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p>
                    Bei einem Logout wird Ihr Token sofort auf eine Blacklist gesetzt.
                    Selbst wenn jemand Ihren Token abfängt, kann er nach dem Logout nicht mehr
                    verwendet werden.
                  </p>
                  <v-alert type="success" variant="tonal" class="mt-2" density="compact">
                    Diese Funktion verwendet Redis für Echtzeit-Invalidierung.
                  </v-alert>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="success" class="mr-2">mdi-lock</v-icon>
                  Verschlüsselung & Hashing
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-table density="compact">
                    <tbody>
                      <tr><td><strong>Passwort-Hashing</strong></td><td>bcrypt (sichere Einweg-Verschlüsselung)</td></tr>
                      <tr><td><strong>Token-Signatur</strong></td><td>HS256 mit sicherem Secret Key</td></tr>
                      <tr><td><strong>Transport</strong></td><td>HTTPS (TLS 1.3) in Production</td></tr>
                    </tbody>
                  </v-table>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="success" class="mr-2">mdi-history</v-icon>
                  Audit Logging & Versionierung
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <p><strong>Audit Log:</strong> Jede Aktion wird protokolliert:</p>
                  <ul class="pl-4 mb-3">
                    <li>Wer hat die Änderung durchgeführt?</li>
                    <li>Wann wurde die Änderung durchgeführt?</li>
                    <li>Was wurde geändert (vorher/nachher)?</li>
                  </ul>
                  <p><strong>Versionierung:</strong> Diff-basierte Änderungshistorie:</p>
                  <ul class="pl-4">
                    <li>Nur Änderungen werden gespeichert (effizient)</li>
                    <li>Vollständiger Zustand zu jedem Zeitpunkt rekonstruierbar</li>
                    <li>Periodische Snapshots für schnelle Wiederherstellung</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mb-3">Passwort ändern</h3>
            <v-timeline density="compact" side="end" class="mb-4">
              <v-timeline-item dot-color="primary" size="small">
                <v-card variant="outlined" class="pa-3">
                  <strong>1.</strong> Klicken Sie auf Ihren Benutzernamen oben rechts
                </v-card>
              </v-timeline-item>
              <v-timeline-item dot-color="primary" size="small">
                <v-card variant="outlined" class="pa-3">
                  <strong>2.</strong> Wählen Sie "Passwort ändern"
                </v-card>
              </v-timeline-item>
              <v-timeline-item dot-color="primary" size="small">
                <v-card variant="outlined" class="pa-3">
                  <strong>3.</strong> Geben Sie Ihr aktuelles und neues Passwort ein
                </v-card>
              </v-timeline-item>
              <v-timeline-item dot-color="success" size="small">
                <v-card variant="outlined" class="pa-3">
                  <strong>4.</strong> Der Passwort-Stärke-Indikator zeigt die Sicherheit an
                </v-card>
              </v-timeline-item>
            </v-timeline>

            <h3 class="text-h6 mb-3">Admin-Funktionen</h3>
            <v-alert type="error" variant="tonal" class="mb-4">
              <strong>Nur für Administratoren:</strong>
              Diese Funktionen sind nur mit der ADMIN-Rolle verfügbar.
            </v-alert>

            <v-row>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3 h-100">
                  <h4 class="text-subtitle-1 mb-2">
                    <v-icon class="mr-1">mdi-account-multiple</v-icon>
                    Benutzerverwaltung
                  </h4>
                  <ul class="pl-4 text-body-2">
                    <li>Neue Benutzer anlegen</li>
                    <li>Rollen zuweisen</li>
                    <li>Passwörter zurücksetzen</li>
                    <li>Benutzer deaktivieren</li>
                  </ul>
                </v-card>
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3 h-100">
                  <h4 class="text-subtitle-1 mb-2">
                    <v-icon class="mr-1">mdi-clipboard-text-clock</v-icon>
                    Audit Log
                  </h4>
                  <ul class="pl-4 text-body-2">
                    <li>Alle Systemaktivitäten einsehen</li>
                    <li>Nach Benutzer/Zeit filtern</li>
                    <li>Änderungen nachvollziehen</li>
                    <li>Sicherheitsprüfungen durchführen</li>
                  </ul>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Fehlerbehebung -->
        <v-card id="troubleshooting" class="mb-4">
          <v-card-title class="text-h5 bg-red">
            <v-icon class="mr-2">mdi-wrench</v-icon>
            Fehlerbehebung
          </v-card-title>
          <v-card-text class="pt-4">
            <v-expansion-panels variant="accordion">
              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="error" class="mr-2">mdi-alert</v-icon>
                  Crawler findet keine Dokumente
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <strong>Mögliche Ursachen:</strong>
                  <ul class="pl-4 mb-3">
                    <li>URL-Include-Patterns zu restriktiv</li>
                    <li>Dokumente sind hinter JavaScript versteckt</li>
                    <li>Seite blockiert Crawler (User-Agent)</li>
                  </ul>
                  <strong>Lösungen:</strong>
                  <ul class="pl-4">
                    <li>Include-Patterns lockern oder entfernen</li>
                    <li>JavaScript-Rendering aktivieren</li>
                    <li>Max-Tiefe erhöhen</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="error" class="mr-2">mdi-alert</v-icon>
                  KI-Analyse liefert keine Ergebnisse
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <strong>Mögliche Ursachen:</strong>
                  <ul class="pl-4 mb-3">
                    <li>Keyword-Filter zu strikt</li>
                    <li>Dokumente enthalten keine relevanten Inhalte</li>
                    <li>Prompt nicht passend</li>
                  </ul>
                  <strong>Lösungen:</strong>
                  <ul class="pl-4">
                    <li>Keywords erweitern</li>
                    <li>"Gefilterte analysieren" nutzen</li>
                    <li>Prompt optimieren</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>

              <v-expansion-panel>
                <v-expansion-panel-title>
                  <v-icon color="warning" class="mr-2">mdi-clock-alert</v-icon>
                  Dokumente bleiben in "Wartend"
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <strong>Mögliche Ursachen:</strong>
                  <ul class="pl-4 mb-3">
                    <li>Worker nicht aktiv</li>
                    <li>Queue überlastet</li>
                  </ul>
                  <strong>Lösungen:</strong>
                  <ul class="pl-4">
                    <li>Worker-Status im Crawler prüfen</li>
                    <li>"Pending verarbeiten" manuell klicken</li>
                  </ul>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>

            <h3 class="text-h6 mt-4 mb-3">Status-Codes</h3>
            <v-table density="compact">
              <thead><tr><th>Status</th><th>Bedeutung</th><th>Aktion</th></tr></thead>
              <tbody>
                <tr>
                  <td><v-chip size="small" color="warning">PENDING</v-chip></td>
                  <td>Wartet auf Verarbeitung</td>
                  <td>Abwarten oder manuell starten</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="info">PROCESSING</v-chip></td>
                  <td>Wird verarbeitet</td>
                  <td>Abwarten</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="secondary">ANALYZING</v-chip></td>
                  <td>KI-Analyse läuft</td>
                  <td>Abwarten</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="success">COMPLETED</v-chip></td>
                  <td>Erfolgreich</td>
                  <td>Keine Aktion nötig</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="grey">FILTERED</v-chip></td>
                  <td>Durch Keywords gefiltert</td>
                  <td>Ggf. manuell analysieren</td>
                </tr>
                <tr>
                  <td><v-chip size="small" color="error">FAILED</v-chip></td>
                  <td>Fehler aufgetreten</td>
                  <td>Fehler prüfen, neu versuchen</td>
                </tr>
              </tbody>
            </v-table>
          </v-card-text>
        </v-card>

      </v-col>

      <!-- Sidebar TOC (Desktop) -->
      <v-col cols="3" class="d-none d-lg-block">
        <v-card class="position-sticky" style="top: 80px;">
          <v-card-title class="text-subtitle-1">Inhalt</v-card-title>
          <v-list density="compact" nav>
            <v-list-item
              v-for="section in sections"
              :key="section.id"
              :class="{ 'v-list-item--active': activeSection === section.id }"
              @click="scrollTo(section.id)"
            >
              <template v-slot:prepend>
                <v-icon size="small">{{ section.icon }}</v-icon>
              </template>
              <v-list-item-title class="text-body-2">{{ section.title }}</v-list-item-title>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const activeSection = ref('intro')

const sections = [
  { id: 'intro', title: 'Einführung', icon: 'mdi-information' },
  { id: 'quickstart', title: 'Schnellstart', icon: 'mdi-rocket-launch' },
  { id: 'dashboard', title: 'Dashboard', icon: 'mdi-view-dashboard' },
  { id: 'categories', title: 'Kategorien', icon: 'mdi-folder-multiple' },
  { id: 'sources', title: 'Datenquellen', icon: 'mdi-web' },
  { id: 'crawler', title: 'Crawler Status', icon: 'mdi-robot' },
  { id: 'documents', title: 'Dokumente', icon: 'mdi-file-document-multiple' },
  { id: 'municipalities', title: 'Gemeinden', icon: 'mdi-city' },
  { id: 'entity-facet', title: 'Entity-Facet System', icon: 'mdi-database' },
  { id: 'results', title: 'Ergebnisse', icon: 'mdi-chart-bar' },
  { id: 'export', title: 'Export', icon: 'mdi-export' },
  { id: 'notifications', title: 'Benachrichtigungen', icon: 'mdi-bell' },
  { id: 'api', title: 'API-Referenz', icon: 'mdi-api' },
  { id: 'tips', title: 'Tipps', icon: 'mdi-lightbulb' },
  { id: 'security', title: 'Sicherheit', icon: 'mdi-shield-lock' },
  { id: 'troubleshooting', title: 'Fehlerbehebung', icon: 'mdi-wrench' },
]

const scrollTo = (id: string) => {
  const element = document.getElementById(id)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    activeSection.value = id
  }
}

// Track active section on scroll
let observer: IntersectionObserver | null = null

onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          activeSection.value = entry.target.id
        }
      })
    },
    { threshold: 0.3, rootMargin: '-100px 0px -50% 0px' }
  )

  sections.forEach((section) => {
    const element = document.getElementById(section.id)
    if (element) observer?.observe(element)
  })
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<style scoped>
.v-code {
  background-color: rgba(var(--v-theme-surface-variant), 0.5);
  border-radius: 4px;
  font-family: monospace;
}
</style>
