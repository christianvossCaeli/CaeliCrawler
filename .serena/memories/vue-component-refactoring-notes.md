# Vue Component Refactoring Notes (2024-12-31)

## ChatAssistant.vue (1024 Zeilen)
**Status:** Partiell analysiert, Refactoring ausstehend

**Befund:**
- Im Verzeichnis `frontend/src/components/assistant/` existieren bereits Sub-Komponenten:
  - ChatMessage.vue
  - ChatBubble.vue
  - QuickActionsPanel.vue
  - InputHints.vue
  - BatchActionProgress.vue
  - ChatWindow.vue
  - ActionPreview.vue
  - etc.
- **PROBLEM:** ChatAssistant.vue verwendet diese Sub-Komponenten NICHT, sondern hat alles inline

**Empfohlene Änderungen:**
1. Quick Actions Panel (Zeilen ~84-112) → QuickActionsPanel.vue nutzen oder konsolidieren
2. Messages Area (Zeilen ~113-229) → ChatMessage.vue nutzen
3. Input Area (Zeilen ~230+) → Eigene Komponente extrahieren

**Aufwand:** ~3-4 Stunden für vollständige Integration

## PySisTab.vue (1014 Zeilen)
**Status:** Nicht analysiert

**Geplante Struktur laut Audit:**
```
frontend/src/components/pysis/
  PySisTab.vue                   # Container
  PySisProcessList.vue           # Prozessliste
  PySisFieldEditor.vue           # Feld-Editor
  PySisTemplateDialog.vue        # Template-Dialog
  PySisFacetEnrichmentPanel.vue  # Facet Enrichment
```

**Aufwand:** ~3-4 Stunden
