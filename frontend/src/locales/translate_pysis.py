#!/usr/bin/env python3
"""
Script to translate the PySis Integration section in HelpView.vue to use i18n translation keys.
"""

import re

def translate_pysis():
    file_path = '/Users/christian.voss/PhpstormProjects/CaeliCrawler/CaeliCrawler/frontend/src/views/HelpView.vue'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    print("Translating PySis section...")

    # PySis section title
    content = re.sub(
        r'<v-icon color="pink" class="mr-2">mdi-sync</v-icon>\s+PySis Integration \(Optional\)',
        '<v-icon color="pink" class="mr-2">mdi-sync</v-icon>\n                  {{ t(\'help.apiGroups.pysis.title\') }}',
        content
    )

    # PySis note
    content = re.sub(
        r'PySis ist eine optionale Integration zur Synchronisation mit externen Prozess-Management-Systemen\.\s+Erfordert Azure AD Konfiguration\.',
        "{{ t('help.apiGroups.pysis.note') }}",
        content,
        flags=re.DOTALL
    )

    # Templates heading
    content = re.sub(
        r'<h4 class="text-subtitle-2 mb-2">Templates</h4>',
        '<h4 class="text-subtitle-2 mb-2">{{ t(\'help.apiGroups.pysis.templates.heading\') }}</h4>',
        content
    )

    # Template endpoints
    content = re.sub(r'<td>Alle Templates auflisten</td>', '<td>{{ t(\'help.apiGroups.pysis.templates.endpoints.list\') }}</td>', content)
    # These were already translated earlier with generic names, but we need specific ones for PySis
    # Let me be more specific with the context

    # Find and replace template endpoints within PySis section
    pysis_section_pattern = r'(<v-icon color="pink" class="mr-2">mdi-sync</v-icon>.*?</v-expansion-panel>)'

    def replace_in_pysis(match):
        pysis_content = match.group(1)
        # Template endpoints
        pysis_content = re.sub(r'<td>Alle Templates auflisten</td>', '<td>{{ t(\'help.apiGroups.pysis.templates.endpoints.list\') }}</td>', pysis_content)
        pysis_content = re.sub(r'(<code>/api/admin/pysis/templates</code></td><td>)Template erstellen(</td>)', r'\1{{ t(\'help.apiGroups.pysis.templates.endpoints.create\') }}\2', pysis_content)
        pysis_content = re.sub(r'(<code>/api/admin/pysis/templates/{id}</code></td><td>)Template abrufen(</td>)', r'\1{{ t(\'help.apiGroups.pysis.templates.endpoints.get\') }}\2', pysis_content)
        pysis_content = re.sub(r'(<code>/api/admin/pysis/templates/{id}</code></td><td>)Template aktualisieren(</td>)', r'\1{{ t(\'help.apiGroups.pysis.templates.endpoints.update\') }}\2', pysis_content)
        pysis_content = re.sub(r'(<code>/api/admin/pysis/templates/{id}</code></td><td>)Template löschen(</td>)', r'\1{{ t(\'help.apiGroups.pysis.templates.endpoints.delete\') }}\2', pysis_content)

        # Processes heading
        pysis_content = re.sub(r'<h4 class="text-subtitle-2 mb-2">Prozesse</h4>', '<h4 class="text-subtitle-2 mb-2">{{ t(\'help.apiGroups.pysis.processes.heading\') }}</h4>', pysis_content)

        # Process endpoints
        pysis_content = re.sub(r'<td>Verfügbare Prozesse</td>', '<td>{{ t(\'help.apiGroups.pysis.processes.endpoints.available\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Prozesse einer Location</td>', '<td>{{ t(\'help.apiGroups.pysis.processes.endpoints.locationProcesses\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Prozess für Location erstellen</td>', '<td>{{ t(\'help.apiGroups.pysis.processes.endpoints.createForLocation\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Prozess-Details</td>', '<td>{{ t(\'help.apiGroups.pysis.processes.endpoints.details\') }}</td>', pysis_content)
        pysis_content = re.sub(r'(<code>/api/admin/pysis/processes/{id}</code></td><td>)Prozess aktualisieren(</td>)', r'\1{{ t(\'help.apiGroups.pysis.processes.endpoints.update\') }}\2', pysis_content)
        pysis_content = re.sub(r'(<code>/api/admin/pysis/processes/{id}</code></td><td>)Prozess löschen(</td>)', r'\1{{ t(\'help.apiGroups.pysis.processes.endpoints.delete\') }}\2', pysis_content)
        pysis_content = re.sub(r'<td>Template anwenden</td>', '<td>{{ t(\'help.apiGroups.pysis.processes.endpoints.applyTemplate\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Felder KI-generieren</td>', '<td>{{ t(\'help.apiGroups.pysis.processes.endpoints.generate\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Von PySis laden</td>', '<td>{{ t(\'help.apiGroups.pysis.processes.endpoints.syncPull\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Zu PySis senden</td>', '<td>{{ t(\'help.apiGroups.pysis.processes.endpoints.syncPush\') }}</td>', pysis_content)

        # Fields heading
        pysis_content = re.sub(r'<h4 class="text-subtitle-2 mb-2">Felder</h4>', '<h4 class="text-subtitle-2 mb-2">{{ t(\'help.apiGroups.pysis.fields.heading\') }}</h4>', pysis_content)

        # Field endpoints
        pysis_content = re.sub(r'<td>Felder eines Prozesses</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.list\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Feld hinzufügen</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.add\') }}</td>', pysis_content)
        pysis_content = re.sub(r'(<code>/api/admin/pysis/fields/{id}</code></td><td>)Feld aktualisieren(</td>)', r'\1{{ t(\'help.apiGroups.pysis.fields.endpoints.update\') }}\2', pysis_content)
        pysis_content = re.sub(r'<td>Feld-Wert setzen</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.setValue\') }}</td>', pysis_content)
        pysis_content = re.sub(r'(<code>/api/admin/pysis/fields/{id}</code></td><td>)Feld löschen(</td>)', r'\1{{ t(\'help.apiGroups.pysis.fields.endpoints.delete\') }}\2', pysis_content)
        pysis_content = re.sub(r'<td>KI-Vorschlag generieren</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.generate\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>KI-Vorschlag akzeptieren</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.acceptAi\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>KI-Vorschlag ablehnen</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.rejectAi\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Feld zu PySis senden</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.syncPush\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Feld-Änderungshistorie</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.history\') }}</td>', pysis_content)
        pysis_content = re.sub(r'<td>Version wiederherstellen</td>', '<td>{{ t(\'help.apiGroups.pysis.fields.endpoints.restore\') }}</td>', pysis_content)

        # Connection heading
        pysis_content = re.sub(r'<h4 class="text-subtitle-2 mb-2">Verbindung</h4>', '<h4 class="text-subtitle-2 mb-2">{{ t(\'help.apiGroups.pysis.connection.heading\') }}</h4>', pysis_content)

        # Connection endpoint
        pysis_content = re.sub(r'<td>Verbindung testen</td>', '<td>{{ t(\'help.apiGroups.pysis.connection.endpoints.test\') }}</td>', pysis_content)

        return pysis_content

    content = re.sub(pysis_section_pattern, replace_in_pysis, content, flags=re.DOTALL)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Calculate changes
    changes_made = len([1 for i, (c1, c2) in enumerate(zip(original_content, content)) if c1 != c2])
    print(f"\n✓ Translation completed!")
    print(f"  - Approximately {changes_made} characters changed")
    print(f"  - File: {file_path}")

if __name__ == '__main__':
    translate_pysis()
