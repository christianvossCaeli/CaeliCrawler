# CaeliCrawler - Benutzerhandbuch

**Version 1.0** | Stand: Dezember 2024

---

## Inhaltsverzeichnis

1. [Einführung](#1-einführung)
2. [Schnellstart](#2-schnellstart)
3. [Dashboard](#3-dashboard)
4. [Kategorien](#4-kategorien)
5. [Datenquellen](#5-datenquellen)
6. [Crawler](#6-crawler)
7. [Dokumente](#7-dokumente)
8. [Gemeinden/Locations](#8-gemeindenlocation)
9. [Ergebnisse](#9-ergebnisse)
10. [Export](#10-export)
11. [Tipps & Best Practices](#11-tipps--best-practices)
12. [Fehlerbehebung](#12-fehlerbehebung)

---

## 1. Einführung

### Was ist CaeliCrawler?

CaeliCrawler ist ein intelligentes Web-Crawling-System zur automatisierten Erfassung und Analyse von kommunalen Dokumenten und Webseiten. Das System wurde speziell entwickelt, um relevante Informationen aus öffentlichen Quellen zu extrahieren und mittels KI-Analyse strukturiert aufzubereiten.

### Hauptfunktionen

| Funktion | Beschreibung |
|----------|--------------|
| **Web-Crawling** | Automatisches Durchsuchen von Websites nach relevanten Dokumenten |
| **Dokumentenverarbeitung** | Extraktion von Text aus PDFs, HTML, Word-Dokumenten |
| **KI-Analyse** | Intelligente Auswertung der Inhalte mittels Azure OpenAI |
| **Relevanz-Filterung** | Automatische Vorsortierung nach konfigurierbaren Keywords |
| **Strukturierte Ergebnisse** | Export der Erkenntnisse als JSON oder CSV |

### Typischer Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Kategorie  │───▶│ Datenquelle │───▶│   Crawler   │───▶│  Dokumente  │
│  erstellen  │    │  hinzufügen │    │   starten   │    │  gefunden   │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
│   Export    │◀───│  Ergebnisse │◀───│  KI-Analyse │◀──────────┘
│  (JSON/CSV) │    │   ansehen   │    │   läuft     │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## 2. Schnellstart

### In 5 Minuten zum ersten Ergebnis

**Schritt 1: Kategorie anlegen**
1. Navigieren Sie zu **Kategorien**
2. Klicken Sie auf **"Neue Kategorie"**
3. Geben Sie einen Namen ein (z.B. "Windenergie-Beschlüsse")
4. Definieren Sie den Zweck und Suchbegriffe
5. Speichern Sie die Kategorie

**Schritt 2: Datenquelle hinzufügen**
1. Wechseln Sie zu **Datenquellen**
2. Klicken Sie auf **"Neue Quelle"**
3. Wählen Sie die erstellte Kategorie
4. Geben Sie die Basis-URL der Website ein
5. Wählen Sie Land und Gemeinde
6. Speichern Sie die Quelle

**Schritt 3: Crawl starten**
1. Gehen Sie zum **Dashboard**
2. Klicken Sie auf **"Crawler starten"**
3. Wählen Sie die gewünschten Filter oder starten Sie für alle Quellen
4. Der Crawler beginnt mit der Arbeit

**Schritt 4: Ergebnisse ansehen**
1. Überwachen Sie den Fortschritt unter **Crawler**
2. Prüfen Sie verarbeitete **Dokumente**
3. Sehen Sie die KI-Erkenntnisse unter **Ergebnisse**

---

## 3. Dashboard

Das Dashboard ist die zentrale Übersichtsseite und zeigt den aktuellen Systemstatus.

### Statistik-Karten

| Karte | Beschreibung |
|-------|--------------|
| **Kategorien** | Anzahl der konfigurierten Kategorien |
| **Datenquellen** | Anzahl der registrierten Websites/APIs |
| **Dokumente** | Gesamtzahl der gefundenen Dokumente |
| **Aktive Crawler** | Aktuell laufende Crawl-Jobs |

### Aktive Crawler (Live-Ansicht)

Wenn Crawler laufen, erscheint eine Live-Ansicht mit:
- Name der Datenquelle
- Anzahl gefundener Dokumente
- Anzahl neuer Dokumente
- Fehlerzähler
- Laufzeit

### Crawler Status

- **Aktive Workers**: Anzahl der verfügbaren Verarbeitungseinheiten
- **Laufende Jobs**: Aktuell aktive Crawl-Prozesse
- **Wartende Jobs**: In der Queue wartende Jobs

### Schnellaktionen

| Button | Funktion |
|--------|----------|
| **Neue Kategorie** | Öffnet das Kategorie-Formular |
| **Neue Datenquelle** | Öffnet das Quellen-Formular |
| **Crawler starten** | Öffnet den Crawl-Dialog mit Filteroptionen |
| **Daten exportieren** | Navigiert zur Export-Seite |

### Crawler starten - Dialog

Der Crawler-Dialog ermöglicht gezieltes Crawlen:

| Filter | Beschreibung |
|--------|--------------|
| **Kategorie** | Nur Quellen einer bestimmten Kategorie |
| **Land** | Nur Quellen aus einem bestimmten Land |
| **Suche** | Textsuche in Name oder URL |
| **Maximale Anzahl** | Limit für die Anzahl zu crawlender Quellen |
| **Status** | Nur aktive, ausstehende oder fehlerhafte Quellen |
| **Quellentyp** | Website, OParl API oder RSS Feed |

> **Hinweis**: Die Anzeige zeigt immer, wie viele Quellen mit den aktuellen Filtern gecrawlt werden.

---

## 4. Kategorien

Kategorien sind die oberste Organisationsebene und definieren, **was** gesucht wird und **wie** die Ergebnisse analysiert werden.

### Kategorie erstellen

#### Grundeinstellungen

| Feld | Beschreibung | Beispiel |
|------|--------------|----------|
| **Name** | Eindeutiger Name der Kategorie | "Windenergie-Beschlüsse" |
| **Beschreibung** | Optionale Erläuterung | "Sammelt alle Ratsbeschlüsse zu Windenergie" |
| **Zweck** | Was soll erreicht werden? | "Windkraft-Restriktionen analysieren" |
| **Status** | Aktiv/Inaktiv | Aktiv |

#### Suchbegriffe (Keywords)

Definieren Sie hier die Keywords für die **Relevanz-Filterung**:

```
windkraft, windenergie, windpark, windrad, repowering,
flächennutzungsplan, bebauungsplan, bauleitplanung
```

> **Wichtig**: Dokumente werden nur zur KI-Analyse weitergeleitet, wenn sie mindestens 2 dieser Keywords enthalten.

#### Dokumenttypen

Definieren Sie, welche Dokumentarten erfasst werden sollen:

```
Beschluss, Protokoll, Satzung, Pressemitteilung, Bekanntmachung
```

#### URL-Filter (Regex)

Optimieren Sie das Crawling durch URL-Muster:

**Include-Patterns (Whitelist)**
```
/ratsinformation/
/beschluesse/
/dokumente/
/sitzungen/
```
> URLs müssen mindestens ein Pattern matchen, um gecrawlt zu werden.

**Exclude-Patterns (Blacklist)**
```
/archiv/
/login/
/suche/
/\?page=
```
> URLs mit diesen Mustern werden übersprungen.

⚠️ **Warnung**: Ohne URL-Filter wird die komplette Website durchsucht - das kann sehr lange dauern!

#### Zeitplan (Cron)

Automatisches Crawling nach Zeitplan:

| Cron-Ausdruck | Bedeutung |
|---------------|-----------|
| `0 2 * * *` | Täglich um 02:00 Uhr |
| `0 2 * * 1` | Jeden Montag um 02:00 Uhr |
| `0 2 1 * *` | Am 1. jeden Monats um 02:00 Uhr |

#### KI-Extraktions-Prompt

Der wichtigste Teil: Hier definieren Sie, **was die KI extrahieren soll**.

Beispiel-Prompt:
```
Analysiere das Dokument und extrahiere folgende Informationen als JSON:

{
  "topic": "Hauptthema des Dokuments",
  "summary": "Zusammenfassung in 2-3 Sätzen",
  "is_relevant": true/false,
  "municipality": "Name der Gemeinde",
  "pain_points": ["Liste kritischer Punkte bezüglich Windenergie"],
  "opportunities": ["Liste von Chancen für Windenergie-Projekte"],
  "sentiment": "positiv/neutral/negativ",
  "key_dates": ["Relevante Termine"],
  "contact_persons": ["Ansprechpartner"]
}
```

### Kategorie-Aktionen

| Aktion | Symbol | Beschreibung |
|--------|--------|--------------|
| **Bearbeiten** | ✏️ | Kategorie-Einstellungen ändern |
| **Crawlen** | ▶️ | Crawl für alle Quellen dieser Kategorie starten |
| **Neu analysieren** | 🔄 | Alle Dokumente erneut durch die KI schicken |
| **Löschen** | 🗑️ | Kategorie mit allen Daten löschen |

---

## 5. Datenquellen

Datenquellen sind die konkreten Websites oder APIs, die gecrawlt werden.

### Quellentypen

| Typ | Beschreibung | Verwendung |
|-----|--------------|------------|
| **WEBSITE** | Standard-Website-Crawling | Kommunale Websites, Nachrichtenseiten |
| **OPARL_API** | OParl-Schnittstelle | Ratsinformationssysteme |
| **RSS** | RSS-Feed | News-Aggregation |

### Quelle erstellen

#### Grunddaten

| Feld | Beschreibung | Pflicht |
|------|--------------|---------|
| **Name** | Anzeigename der Quelle | Ja |
| **Kategorie** | Zuordnung zur Kategorie | Ja |
| **Quellentyp** | WEBSITE, OPARL_API oder RSS | Ja |
| **Basis-URL** | Startpunkt für den Crawler | Ja |

#### Standort

| Feld | Beschreibung |
|------|--------------|
| **Land** | Ländercode (z.B. DE, GB) |
| **Bundesland** | Admin Level 1 |
| **Gemeinde** | Name der Kommune |

> **Tipp**: Die Standort-Zuordnung ermöglicht später das Filtern nach Regionen.

### Crawl-Konfiguration

#### Allgemeine Einstellungen

| Einstellung | Beschreibung | Standard |
|-------------|--------------|----------|
| **Max. Tiefe** | Wie viele Link-Ebenen verfolgen | 3 |
| **Max. Seiten** | Maximale Anzahl zu crawlender Seiten | 200 |
| **Externe Links** | Links zu anderen Domains verfolgen | Nein |
| **JavaScript rendern** | Playwright für dynamische Seiten nutzen | Nein |

#### Dokumententypen zum Download

```
pdf, doc, docx
```

#### URL-Filter (Quelle-spezifisch)

Überschreiben die Kategorie-Filter für diese eine Quelle:

- **Include-Patterns**: Whitelist für URLs
- **Exclude-Patterns**: Blacklist für URLs

### Filter & Suche

Die Datenquellen-Übersicht bietet umfangreiche Filtermöglichkeiten:

| Filter | Beschreibung |
|--------|--------------|
| **Land** | Nach Ländercode filtern |
| **Gemeinde** | Autocomplete-Suche nach Ort |
| **Kategorie** | Nach Kategorie filtern |
| **Status** | ACTIVE, PENDING, ERROR |
| **Suche** | Volltextsuche in Name und URL |

### Quellen-Aktionen

| Aktion | Symbol | Beschreibung |
|--------|--------|--------------|
| **Bearbeiten** | ✏️ | Konfiguration ändern |
| **Crawlen** | ▶️ | Einzelnen Crawl starten |
| **Zurücksetzen** | 🔄 | Alle Dokumente löschen und neu crawlen |
| **Löschen** | 🗑️ | Quelle entfernen |

### Bulk-Import

Für das Hinzufügen vieler Quellen gleichzeitig:

1. Klicken Sie auf **"Bulk Import"**
2. Fügen Sie JSON-Daten im Format ein:

```json
[
  {
    "name": "Gummersbach",
    "base_url": "https://www.gummersbach.de/",
    "country": "DE",
    "location_name": "Gummersbach"
  },
  {
    "name": "Köln",
    "base_url": "https://www.stadt-koeln.de/",
    "country": "DE",
    "location_name": "Köln"
  }
]
```

---

## 6. Crawler

Die Crawler-Seite zeigt den Live-Status aller Crawling-Aktivitäten.

### Übersicht

| Karte | Beschreibung |
|-------|--------------|
| **Aktive Worker** | Verfügbare Verarbeitungs-Prozesse |
| **Laufende Jobs** | Aktuell aktive Crawls |
| **Wartende Jobs** | Jobs in der Queue |
| **Dokumente gesamt** | Alle gefundenen Dokumente |

### KI-Aufgaben (Live)

Zeigt laufende KI-Analysen mit:
- Name der Aufgabe
- Aktuelles Dokument
- Fortschrittsbalken (X/Y)
- Abbrechen-Button

### Aktive Crawler (Live)

Expandierbare Panels für jeden laufenden Crawl:

- **Quelle**: Name der Datenquelle
- **Aktuelle URL**: Was gerade gecrawlt wird
- **Statistiken**: Seiten, Dokumente, Fehler
- **Log**: Letzte Aktivitäten mit Zeitstempel

### Job-Tabelle

Liste aller Crawl-Jobs mit Filterung:

| Spalte | Beschreibung |
|--------|--------------|
| **Quelle** | Name der gecrawlten Datenquelle |
| **Status** | RUNNING, COMPLETED, FAILED, CANCELLED |
| **Gestartet** | Startzeitpunkt |
| **Dauer** | Laufzeit |
| **Fortschritt** | Verarbeitete/Gefundene Dokumente |

#### Status-Filter

- **Alle**: Alle Jobs anzeigen
- **Laufend**: Nur aktive Jobs
- **Abgeschlossen**: Erfolgreich beendete Jobs
- **Fehlgeschlagen**: Jobs mit Fehlern

### Job-Details

Klicken Sie auf das Info-Symbol für Details:

- Quelle und Kategorie
- Status und Dauer
- Seiten gecrawlt
- Dokumente gefunden/neu
- Fehler-Log (falls vorhanden)

---

## 7. Dokumente

Die Dokumenten-Ansicht zeigt alle gefundenen und verarbeiteten Dateien.

### Status-Leiste

Klickbare Statistiken zum schnellen Filtern:

| Status | Farbe | Beschreibung |
|--------|-------|--------------|
| **Wartend** | Gelb | Noch nicht verarbeitet |
| **In Bearbeitung** | Blau | Wird gerade heruntergeladen/extrahiert |
| **Fertig** | Grün | Text erfolgreich extrahiert |
| **Gefiltert** | Grau | Durch Keyword-Filter aussortiert |
| **Fehler** | Rot | Verarbeitung fehlgeschlagen |

### Aktions-Buttons

| Button | Beschreibung |
|--------|--------------|
| **X Pending verarbeiten** | Alle wartenden Dokumente starten |
| **X Gefilterte analysieren** | Gefilterte Dokumente erneut mit KI prüfen |
| **Verarbeitung stoppen** | Laufende Verarbeitung abbrechen |
| **Aktualisieren** | Liste neu laden |

### Filter

| Filter | Beschreibung |
|--------|--------------|
| **Volltextsuche** | Suche in Dokumentinhalt |
| **Gemeinde/Ort** | Nach Standort filtern |
| **Kategorie** | Nach Kategorie filtern |
| **Status** | Nach Verarbeitungsstatus |
| **Typ** | PDF, HTML, DOC, DOCX |

### Dokument-Tabelle

| Spalte | Beschreibung |
|--------|--------------|
| **Titel** | Dokumenttitel oder Dateiname |
| **Typ** | Dateiformat |
| **Status** | Verarbeitungsstatus |
| **Quelle** | Herkunfts-Datenquelle |
| **Entdeckt** | Wann gefunden |
| **Größe** | Dateigröße |
| **Aktionen** | Detail, Original öffnen, Verarbeiten |

### Dokument-Details

Klicken Sie auf ein Dokument für Details:

#### Tab: Info
- Original-URL
- Quelle und Kategorie
- Zeitstempel (entdeckt, geladen, verarbeitet)
- Dateigröße und Seitenanzahl

#### Tab: Text
- Extrahierter Rohtext des Dokuments

#### Tab: Extrahierte Daten
- KI-Analyse-Ergebnisse
- Konfidenz-Score
- Verifizierungs-Status

### Einzelne Dokument-Aktionen

| Aktion | Wann verfügbar | Beschreibung |
|--------|----------------|--------------|
| **Verarbeiten** | Status: PENDING/FILTERED/FAILED | Download & Textextraktion starten |
| **KI-Analyse** | Status: COMPLETED, ohne Extraktion | KI-Analyse manuell anstoßen |
| **Trotzdem analysieren** | Status: FILTERED | Keyword-Filter ignorieren |

---

## 8. Gemeinden/Locations

Übersicht aller Standorte mit aggregierten Daten.

### Statistiken

| Karte | Beschreibung |
|-------|--------------|
| **Gemeinden** | Anzahl unterschiedlicher Standorte |
| **Dokumente** | Gesamtzahl aller Dokumente |
| **Extraktionen** | Anzahl KI-Analysen |
| **Avg. Konfidenz** | Durchschnittliche KI-Sicherheit |

### Filter

| Filter | Beschreibung |
|--------|--------------|
| **Land** | Nach Ländercode (DE, GB, ...) |
| **Bundesland** | Nach Admin Level 1 |
| **Landkreis** | Nach Admin Level 2 |
| **Kategorie** | Nach Kategorie filtern |
| **Min. Konfidenz** | Nur Standorte mit hoher Sicherheit |
| **Suche** | Nach Name suchen |

### Gemeinde-Tabelle

| Spalte | Beschreibung |
|--------|--------------|
| **Name** | Gemeindename |
| **Bundesland** | Admin Level 1 |
| **Quellen** | Anzahl Datenquellen |
| **Dokumente** | Anzahl Dokumente |
| **Extraktionen** | KI-Analysen |
| **Konfidenz** | Durchschnittliche Sicherheit |
| **Datum** | Letzte Aktualisierung |

### Gemeinde-Report

Klicken Sie auf eine Zeile für den Detail-Report:

#### Übersicht
- Name und Region
- Dokumenten-Statistik
- Durchschnittliche Konfidenz

#### Zusammenfassung
- Automatisch generierte Zusammenfassung aller Erkenntnisse

#### Dokumente-Tab
- Liste aller Dokumente dieser Gemeinde
- Direkt-Links zu Originalen

#### Extraktionen-Tab
- Alle KI-Analysen mit Details
- Pain Points und Opportunities
- Sentiment-Analyse

---

## 9. Ergebnisse

Zentrale Ansicht aller KI-extrahierten Daten.

### Statistik-Karten

| Karte | Beschreibung |
|-------|--------------|
| **Gesamt** | Anzahl aller Extraktionen |
| **Verifiziert** | Manuell bestätigte Einträge |
| **Avg. Konfidenz** | Durchschnittliche KI-Sicherheit |

### Filter

| Filter | Beschreibung |
|--------|--------------|
| **Land** | Nach Ländercode filtern |
| **Gemeinde** | Nach Standort filtern |
| **Kategorie** | Nach Kategorie filtern |
| **Min. Konfidenz** | Slider 0-100% |

### Ergebnis-Tabelle

| Spalte | Beschreibung |
|--------|--------------|
| **Typ** | Art der Extraktion |
| **Dokument** | Quell-Dokument |
| **Konfidenz** | KI-Sicherheit in % |
| **Verifiziert** | Manuell geprüft? |
| **Erstellt** | Zeitstempel |

### Ergebnis-Details

Klicken Sie auf eine Zeile für Details:

- **Typ**: Art der extrahierten Information
- **Dokument**: Link zum Quelldokument
- **Konfidenz**: Sicherheit der KI
- **Extrahierter Inhalt**: JSON mit allen Feldern
- **Verifizierung**: Status und Buttons zum Bestätigen/Ablehnen

---

## 10. Export

Daten exportieren und API-Informationen.

### Export-Optionen

| Option | Beschreibung |
|--------|--------------|
| **Land** | Export auf Land beschränken |
| **Gemeinde** | Export auf Standort beschränken |
| **Kategorie** | Nach Kategorie filtern |
| **Min. Konfidenz** | Nur sichere Ergebnisse |
| **Nur verifizierte** | Nur manuell geprüfte Daten |

### Export-Formate

| Format | Button | Beschreibung |
|--------|--------|--------------|
| **JSON** | Blau | Strukturiertes JSON mit allen Details |
| **CSV** | Grün | Tabellenformat für Excel |

### API-Endpunkte

Für programmatischen Zugriff:

| Endpunkt | Beschreibung |
|----------|--------------|
| `GET /api/v1/data` | Extrahierte Daten abrufen |
| `GET /api/v1/data/documents` | Dokumente abrufen |
| `GET /api/v1/data/search?q=...` | Volltextsuche |
| `GET /api/v1/export/changes` | Änderungs-Feed |

### Webhook-Test

Testen Sie Ihren Webhook-Endpunkt:

1. Geben Sie Ihre Webhook-URL ein
2. Klicken Sie auf **"Webhook testen"**
3. Prüfen Sie Status-Code und Antwort

### Änderungs-Feed

Tabelle der letzten Änderungen:

| Typ | Bedeutung |
|-----|-----------|
| **NEW_DOCUMENT** | Neues Dokument gefunden |
| **CONTENT_CHANGED** | Inhalt hat sich geändert |
| **REMOVED** | Dokument nicht mehr verfügbar |
| **METADATA_CHANGED** | Metadaten aktualisiert |

---

## 11. Tipps & Best Practices

### Effizientes Crawling

1. **URL-Filter nutzen**
   - Definieren Sie Include-Patterns für relevante Bereiche
   - Schließen Sie Archive, Login-Seiten und Suchergebnisse aus

2. **Max. Tiefe begrenzen**
   - Starten Sie mit Tiefe 2-3
   - Erhöhen Sie nur bei Bedarf

3. **Dokumenttypen einschränken**
   - Crawlen Sie nur die benötigten Formate
   - PDFs sind meist ergiebiger als HTML

### Bessere KI-Ergebnisse

1. **Präzise Prompts**
   - Definieren Sie klare JSON-Strukturen
   - Geben Sie konkrete Beispiele
   - Beschreiben Sie den Kontext (Windenergie, Kommune, etc.)

2. **Keyword-Optimierung**
   - Nutzen Sie domänenspezifische Begriffe
   - Inkludieren Sie Varianten und Synonyme
   - Testen Sie mit wenigen Quellen zuerst

3. **Konfidenz-Schwellen**
   - Ergebnisse < 50%: Kritisch prüfen
   - Ergebnisse 50-70%: Stichproben prüfen
   - Ergebnisse > 70%: Meist zuverlässig

### Organisation

1. **Kategorien sinnvoll trennen**
   - Eine Kategorie pro Themengebiet
   - Unterschiedliche Prompts für unterschiedliche Analysen

2. **Standorte pflegen**
   - Weisen Sie jeder Quelle einen Standort zu
   - Ermöglicht regionale Auswertungen

3. **Regelmäßige Pflege**
   - Prüfen Sie fehlerhafte Quellen
   - Aktualisieren Sie URLs bei Änderungen

---

## 12. Fehlerbehebung

### Häufige Probleme

#### Crawler findet keine Dokumente

**Mögliche Ursachen:**
- URL-Include-Patterns zu restriktiv
- Dokumente sind hinter JavaScript versteckt
- Seite blockiert Crawler (User-Agent)

**Lösungen:**
- Include-Patterns lockern oder entfernen
- JavaScript-Rendering aktivieren
- Max-Tiefe erhöhen

#### KI-Analyse liefert keine Ergebnisse

**Mögliche Ursachen:**
- Keyword-Filter zu strikt
- Dokumente enthalten keine relevanten Inhalte
- Prompt nicht passend

**Lösungen:**
- Keywords erweitern
- "Gefilterte analysieren" nutzen
- Prompt optimieren

#### Dokumente bleiben in "Wartend"

**Mögliche Ursachen:**
- Worker nicht aktiv
- Queue überlastet

**Lösungen:**
- Worker-Status im Crawler prüfen
- "Pending verarbeiten" manuell klicken

#### Fehlerhafte Textextraktion

**Mögliche Ursachen:**
- PDF ist gescannt (Bild-PDF)
- Encoding-Probleme
- Korrupte Dateien

**Lösungen:**
- OCR-basierte PDFs werden nicht unterstützt
- Dokument einzeln neu verarbeiten

### Status-Codes

| Status | Bedeutung | Aktion |
|--------|-----------|--------|
| **PENDING** | Wartet auf Verarbeitung | Abwarten oder manuell starten |
| **PROCESSING** | Wird verarbeitet | Abwarten |
| **ANALYZING** | KI-Analyse läuft | Abwarten |
| **COMPLETED** | Erfolgreich | Keine Aktion nötig |
| **FILTERED** | Durch Keywords gefiltert | Ggf. manuell analysieren |
| **FAILED** | Fehler aufgetreten | Fehler prüfen, ggf. neu versuchen |

### Support

Bei weiteren Fragen:
- Prüfen Sie die Log-Ausgaben im Crawler-Bereich
- Kontaktieren Sie das Entwicklungsteam

---

**CaeliCrawler** - Intelligente Dokumentenanalyse für kommunale Daten

*Entwickelt von Caeli Wind*
