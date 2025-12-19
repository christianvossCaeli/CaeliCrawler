# HelpView.vue - i18n Übersetzungsstatus

## Zusammenfassung
Die HelpView.vue Datei ist eine sehr umfangreiche Datei (2619 Zeilen) mit vielen hardcoded deutschen Texten. Eine vollständige manuelle Übersetzung wurde begonnen.

## Erledigte Arbeiten

### 1. Common.json Erweiterungen
Folgende Keys wurden zu `de/common.json` und `en/common.json` hinzugefügt:
- `field` (Feld / Field)
- `example` (Beispiel / Example)
- `icon` (Symbol / Icon)

### 2. Übersetzte Sektionen in HelpView.vue

#### Kategorien-Sektion (Zeilen 445-544)
- ✅ Titel: `{{ t('help.categories.title') }}`
- ✅ Beschreibung: `{{ t('help.categories.description') }}`
- ✅ Grundeinstellungen Panel komplett übersetzt
- ✅ Suchbegriffe Panel komplett übersetzt
- ✅ URL-Filter Panel komplett übersetzt
- ✅ KI-Extraktions-Prompt Panel übersetzt
- ✅ Aktionen-Tabelle komplett übersetzt

#### Datenquellen-Sektion (Zeilen 546-571)
- ✅ Titel: `{{ t('help.sources.title') }}`
- ✅ Beschreibung: `{{ t('help.sources.description') }}`
- ✅ Kategorie-Zuordnung komplett übersetzt
- ⚠️ Quellentypen: Noch hardcoded (Zeile 573+)
- ⚠️ Filter: Noch hardcoded
- ⚠️ Aktionen: Noch hardcoded
- ⚠️ Formular-Felder: Noch hardcoded
- ⚠️ Bulk Import: Noch hardcoded
- ⚠️ Crawl-Konfiguration: Noch hardcoded

## Verbleibende Arbeit

### Sektionen mit hardcoded deutschen Texten:

1. **Datenquellen (sources)** - ca. Zeilen 573-700
   - Quellentypen
   - Verfügbare Filter
   - Aktionen
   - Formular-Felder
   - Bulk Import
   - Crawl-Konfiguration
   - URL-Filter (Erweitert)
   - Status-Bedeutung

2. **Crawler** - ca. Zeilen 707-825
   - Status-Karten
   - KI-Aufgaben
   - Aktive Crawler
   - Job-Tabelle
   - Job-Details-Dialog

3. **Dokumente** - ca. Zeilen 826-906
   - Status-Übersicht
   - Aktions-Buttons
   - Verfügbare Filter
   - Dokument-Details

4. **Gemeinden** - ca. Zeilen 909-1030
   - Statistik-Karten
   - Tabellen-Spalten
   - Filter
   - Gemeinde-Report

5. **Entity-Facet System** - ca. Zeilen 1031-1420
   - Konzept
   - Verknüpfungen
   - Zeitbasierte Facets
   - Analyse-Templates
   - Entities-Ansicht
   - Entity-Detail-Ansicht
   - KI-Integration
   - Best Practices

6. **Ergebnisse** - ca. Zeilen 1421-1550
   - Statistik-Karten
   - Filter
   - Detail-Dialog
   - Konfidenz-Verständnis

7. **Export** - ca. Zeilen 1551-1650
   - Export-Formate
   - Export-Filter
   - Webhook-Test
   - Änderungs-Feed
   - API-Endpunkte

8. **Benachrichtigungen** - ca. Zeilen 1651-1900
   - Übersicht
   - Event-Typen
   - Kanäle
   - Regeln erstellen
   - Filteroptionen
   - Digest-Modus
   - E-Mail-Adressen
   - Webhook-Konfiguration

9. **API-Referenz** - ca. Zeilen 1901-2100
   - API-Gruppen
   - Endpunkte

10. **Tipps & Best Practices** - ca. Zeilen 2101-2200
    - Effizientes Crawling
    - Bessere KI-Ergebnisse
    - Organisation

11. **Sicherheit** - ca. Zeilen 2201-2400
    - Login
    - Benutzerrollen
    - Passwort-Richtlinien
    - Sicherheitsfeatures
    - Admin-Funktionen

12. **Fehlerbehebung** - ca. Zeilen 2401-2550
    - Crawler findet keine Dokumente
    - KI-Analyse ohne Ergebnisse
    - Dokumente bleiben wartend
    - Status-Codes

## Empfohlenes Vorgehen

### Option 1: Schrittweise manuelle Übersetzung
Für jede Sektion:
1. Übersetzungskeys in `de/help/*.json` erstellen
2. Englische Übersetzungen in `en/help/*.json` hinzufügen
3. Hardcoded Texte in HelpView.vue durch `{{ t('...') }}` ersetzen
4. Bei HTML-Inhalt: `<i18n-t>` Komponente mit Slots verwenden (NICHT v-html wegen XSS)

### Option 2: Automatisiertes Script
Ein Python/Node.js Script könnte erstellt werden, das:
1. Alle hardcoded deutschen Texte extrahiert
2. Automatisch Keys generiert
3. Deutsche und englische Übersetzungsdateien aktualisiert
4. Vue-Datei mit i18n-Calls aktualisiert

## Hinweise

### i18n-Verwendung in HelpView.vue
- ✅ `useI18n` ist bereits importiert
- ✅ `const { t } = useI18n()` ist vorhanden
- ✅ Im Template: `{{ t('key') }}` oder für HTML: `<i18n-t>` mit Slots
- ✅ Für Attribute: `:title="t('key')"`

### Übersetzungsstruktur
Die Übersetzungen sind bereits gut strukturiert in:
- `/locales/de/help/intro.json` - Einführung & Schnellstart
- `/locales/de/help/views.json` - Dashboard, Categories, Sources, Crawler, Documents, Municipalities
- `/locales/de/help/features.json` - Entity-Facet, Results, Export, Notifications
- `/locales/de/help/advanced.json` - API, Tips, Security, Troubleshooting
- `/locales/de/help/ui.json` - Navigation & Sections

## Status: 15% abgeschlossen
- Kategorien: ✅ 100%
- Datenquellen: ⚠️ 30%
- Crawler: ❌ 0%
- Dokumente: ❌ 0%
- Gemeinden: ❌ 0%
- Entity-Facet: ❌ 0%
- Ergebnisse: ❌ 0%
- Export: ❌ 0%
- Benachrichtigungen: ❌ 0%
- API: ❌ 0%
- Tipps: ❌ 0%
- Sicherheit: ❌ 0%
- Fehlerbehebung: ❌ 0%

## Nächste Schritte
1. Datenquellen-Sektion vollständig übersetzen
2. Crawler-Sektion übersetzen
3. Dokumente-Sektion übersetzen
4. Fortsetzung der restlichen Sektionen

Die vorhandenen Übersetzungskeys in den JSON-Dateien sind bereits sehr gut strukturiert und können direkt verwendet werden.
