#!/usr/bin/env python3
"""
Script to translate the Security and Troubleshooting sections in HelpView.vue to use i18n translation keys.
"""

import re

def translate_security_and_troubleshooting():
    file_path = '/Users/christian.voss/PhpstormProjects/CaeliCrawler/CaeliCrawler/frontend/src/views/HelpView.vue'

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    print("Translating Security section...")
    # Security section title
    content = re.sub(
        r'<v-icon class="mr-2">mdi-shield-lock</v-icon>\s+Sicherheit & Authentifizierung',
        '<v-icon class="mr-2">mdi-shield-lock</v-icon>\n            {{ t(\'help.security.title\') }}',
        content
    )

    # Login section
    content = re.sub(r'<h3 class="text-h6 mb-3">Anmeldung \(Login\)</h3>', '<h3 class="text-h6 mb-3">{{ t(\'help.security.login.heading\') }}</h3>', content)
    content = re.sub(
        r'CaeliCrawler verwendet ein sicheres JWT-basiertes Authentifizierungssystem\.\s+Nach der Anmeldung erhalten Sie einen Token, der bei jeder Anfrage automatisch\s+mitgesendet wird\.',
        "{{ t('help.security.login.description') }}",
        content,
        flags=re.DOTALL
    )
    content = re.sub(r'<strong>Wichtig:</strong>', '<strong>{{ t(\'help.security.login.important\') }}</strong>', content)
    content = re.sub(
        r'Nach 24 Stunden Inaktivität werden Sie automatisch abgemeldet\.\s+Bei einem Logout wird der Token sofort invalidiert\.',
        "{{ t('help.security.login.tokenExpiry') }}",
        content,
        flags=re.DOTALL
    )

    # User roles section
    content = re.sub(r'<h3 class="text-h6 mb-3">Benutzerrollen</h3>', '<h3 class="text-h6 mb-3">{{ t(\'help.security.roles.heading\') }}</h3>', content)
    content = re.sub(r'<tr><th>Rolle</th><th>Berechtigungen</th></tr>', '<tr><th>{{ t(\'help.security.roles.role\') }}</th><th>{{ t(\'help.security.roles.permissions\') }}</th></tr>', content)

    # ADMIN role
    content = re.sub(r'<li>Vollzugriff auf alle Funktionen</li>', '<li>{{ t(\'help.security.roles.admin.fullAccess\') }}</li>', content)
    content = re.sub(r'<li>Benutzerverwaltung \(anlegen, bearbeiten, löschen\)</li>', '<li>{{ t(\'help.security.roles.admin.userManagement\') }}</li>', content)
    content = re.sub(r'<li>Zugriff auf Audit-Log und Versionshistorie</li>', '<li>{{ t(\'help.security.roles.admin.auditLog\') }}</li>', content)
    content = re.sub(r'<li>Systemkonfiguration</li>', '<li>{{ t(\'help.security.roles.admin.systemConfig\') }}</li>', content)

    # EDITOR role
    content = re.sub(r'<li>Kategorien und Datenquellen verwalten</li>', '<li>{{ t(\'help.security.roles.editor.manageCategories\') }}</li>', content)
    content = re.sub(r'<li>Crawler starten und stoppen</li>', '<li>{{ t(\'help.security.roles.editor.controlCrawler\') }}</li>', content)
    content = re.sub(r'<li>Dokumente verarbeiten und analysieren</li>', '<li>{{ t(\'help.security.roles.editor.processDocuments\') }}</li>', content)
    content = re.sub(r'<li>Ergebnisse exportieren</li>', '<li>{{ t(\'help.security.roles.editor.exportResults\') }}</li>', content)

    # VIEWER role
    content = re.sub(r'<li>Alle Daten einsehen</li>', '<li>{{ t(\'help.security.roles.viewer.viewData\') }}</li>', content)
    content = re.sub(r'<li>Keine Bearbeitungsrechte</li>', '<li>{{ t(\'help.security.roles.viewer.noEditRights\') }}</li>', content)

    # Password policies
    content = re.sub(r'<h3 class="text-h6 mb-3">Passwort-Richtlinien</h3>', '<h3 class="text-h6 mb-3">{{ t(\'help.security.password.heading\') }}</h3>', content)
    content = re.sub(r'<strong>Anforderungen:</strong>', '<strong>{{ t(\'help.security.password.requirements\') }}</strong>', content)
    content = re.sub(r'<li>Mindestens 8 Zeichen</li>', '<li>{{ t(\'help.security.password.minLength\') }}</li>', content)
    content = re.sub(r'<li>Mindestens ein Großbuchstabe \(A-Z\)</li>', '<li>{{ t(\'help.security.password.uppercase\') }}</li>', content)
    content = re.sub(r'<li>Mindestens ein Kleinbuchstabe \(a-z\)</li>', '<li>{{ t(\'help.security.password.lowercase\') }}</li>', content)
    content = re.sub(r'<li>Mindestens eine Ziffer \(0-9\)</li>', '<li>{{ t(\'help.security.password.digit\') }}</li>', content)
    content = re.sub(r'<li>Sonderzeichen empfohlen \(erhöht den Sicherheitsscore\)</li>', '<li>{{ t(\'help.security.password.specialChar\') }}</li>', content)

    # Security features
    content = re.sub(r'<h3 class="text-h6 mb-3">Sicherheitsfeatures</h3>', '<h3 class="text-h6 mb-3">{{ t(\'help.security.features.heading\') }}</h3>', content)

    # Rate limiting
    content = re.sub(
        r'Rate Limiting \(Brute-Force-Schutz\)',
        "{{ t('help.security.features.rateLimit.title') }}",
        content
    )
    content = re.sub(
        r'Das System schützt vor automatisierten Anmeldeversachen:',
        "{{ t('help.security.features.rateLimit.description') }}",
        content
    )
    content = re.sub(r'<thead><tr><th>Aktion</th><th>Limit</th><th>Zeitfenster</th></tr></thead>', '<thead><tr><th>{{ t(\'help.security.features.rateLimit.action\') }}</th><th>{{ t(\'help.security.features.rateLimit.limit\') }}</th><th>{{ t(\'help.security.features.rateLimit.timeWindow\') }}</th></tr></thead>', content)
    content = re.sub(r'<tr><td>Login-Versuche</td>', '<tr><td>{{ t(\'help.security.features.rateLimit.loginAttempts\') }}</td>', content)
    content = re.sub(r'<tr><td>Fehlgeschlagene Logins</td>', '<tr><td>{{ t(\'help.security.features.rateLimit.failedLogins\') }}</td>', content)
    content = re.sub(r'<tr><td>Passwort-Änderungen</td>', '<tr><td>{{ t(\'help.security.features.rateLimit.passwordChanges\') }}</td>', content)
    content = re.sub(r'<tr><td>API-Anfragen allgemein</td>', '<tr><td>{{ t(\'help.security.features.rateLimit.apiRequests\') }}</td>', content)
    content = re.sub(r'<td>pro Minute</td>', '<td>{{ t(\'help.security.features.rateLimit.perMinute\') }}</td>', content)
    content = re.sub(r'<td>pro 5 Minuten</td>', '<td>{{ t(\'help.security.features.rateLimit.per5Minutes\') }}</td>', content)
    content = re.sub(r'<td>pro 15 Minuten</td>', '<td>{{ t(\'help.security.features.rateLimit.per15Minutes\') }}</td>', content)
    content = re.sub(
        r'Bei Überschreitung erhalten Sie eine Fehlermeldung mit der verbleibenden Wartezeit\.',
        "{{ t('help.security.features.rateLimit.note') }}",
        content
    )

    # Token blacklist
    content = re.sub(
        r'Token Blacklist \(Sofortiger Logout\)',
        "{{ t('help.security.features.tokenBlacklist.title') }}",
        content
    )
    content = re.sub(
        r'Bei einem Logout wird Ihr Token sofort auf eine Blacklist gesetzt\.\s+Selbst wenn jemand Ihren Token abfängt, kann er nach dem Logout nicht mehr\s+verwendet werden\.',
        "{{ t('help.security.features.tokenBlacklist.description') }}",
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r'Diese Funktion verwendet Redis für Echtzeit-Invalidierung\.',
        "{{ t('help.security.features.tokenBlacklist.note') }}",
        content
    )

    # Encryption
    content = re.sub(
        r'Verschlüsselung & Hashing',
        "{{ t('help.security.features.encryption.title') }}",
        content
    )
    content = re.sub(r'<tr><td><strong>Passwort-Hashing</strong></td>', '<tr><td><strong>{{ t(\'help.security.features.encryption.passwordHashing\') }}</strong></td>', content)
    content = re.sub(r'<td>bcrypt \(sichere Einweg-Verschlüsselung\)</td>', '<td>{{ t(\'help.security.features.encryption.passwordHashingValue\') }}</td>', content)
    content = re.sub(r'<tr><td><strong>Token-Signatur</strong></td>', '<tr><td><strong>{{ t(\'help.security.features.encryption.tokenSignature\') }}</strong></td>', content)
    content = re.sub(r'<td>HS256 mit sicherem Secret Key</td>', '<td>{{ t(\'help.security.features.encryption.tokenSignatureValue\') }}</td>', content)
    content = re.sub(r'<tr><td><strong>Transport</strong></td>', '<tr><td><strong>{{ t(\'help.security.features.encryption.transport\') }}</strong></td>', content)
    content = re.sub(r'<td>HTTPS \(TLS 1\.3\) in Production</td>', '<td>{{ t(\'help.security.features.encryption.transportValue\') }}</td>', content)

    # Audit logging
    content = re.sub(
        r'Audit Logging & Versionierung',
        "{{ t('help.security.features.auditLog.title') }}",
        content
    )
    content = re.sub(r'<p><strong>Audit Log:</strong> Jede Aktion wird protokolliert:</p>', '<p><strong>{{ t(\'help.security.features.auditLog.auditLogHeading\') }}</strong> {{ t(\'help.security.features.auditLog.description\') }}</p>', content)
    content = re.sub(r'<li>Wer hat die Änderung durchgeführt\?</li>', '<li>{{ t(\'help.security.features.auditLog.who\') }}</li>', content)
    content = re.sub(r'<li>Wann wurde die Änderung durchgeführt\?</li>', '<li>{{ t(\'help.security.features.auditLog.when\') }}</li>', content)
    content = re.sub(r'<li>Was wurde geändert \(vorher/nachher\)\?</li>', '<li>{{ t(\'help.security.features.auditLog.what\') }}</li>', content)
    content = re.sub(r'<p><strong>Versionierung:</strong> Diff-basierte Änderungshistorie:</p>', '<p><strong>{{ t(\'help.security.features.auditLog.versioningHeading\') }}</strong> {{ t(\'help.security.features.auditLog.versioningDescription\') }}</p>', content)
    content = re.sub(r'<li>Nur Änderungen werden gespeichert \(effizient\)</li>', '<li>{{ t(\'help.security.features.auditLog.onlyChanges\') }}</li>', content)
    content = re.sub(r'<li>Vollständiger Zustand zu jedem Zeitpunkt rekonstruierbar</li>', '<li>{{ t(\'help.security.features.auditLog.fullState\') }}</li>', content)
    content = re.sub(r'<li>Periodische Snapshots für schnelle Wiederherstellung</li>', '<li>{{ t(\'help.security.features.auditLog.snapshots\') }}</li>', content)

    # Change password
    content = re.sub(r'<h3 class="text-h6 mb-3">Passwort ändern</h3>', '<h3 class="text-h6 mb-3">{{ t(\'help.security.changePassword.heading\') }}</h3>', content)
    content = re.sub(r'<strong>1\.</strong> Klicken Sie auf Ihren Benutzernamen oben rechts', '<strong>1.</strong> {{ t(\'help.security.changePassword.step1\') }}', content)
    content = re.sub(r'<strong>2\.</strong> Wählen Sie "Passwort ändern"', '<strong>2.</strong> {{ t(\'help.security.changePassword.step2\') }}', content)
    content = re.sub(r'<strong>3\.</strong> Geben Sie Ihr aktuelles und neues Passwort ein', '<strong>3.</strong> {{ t(\'help.security.changePassword.step3\') }}', content)
    content = re.sub(r'<strong>4\.</strong> Der Passwort-Stärke-Indikator zeigt die Sicherheit an', '<strong>4.</strong> {{ t(\'help.security.changePassword.step4\') }}', content)

    # Admin functions
    content = re.sub(r'<h3 class="text-h6 mb-3">Admin-Funktionen</h3>', '<h3 class="text-h6 mb-3">{{ t(\'help.security.adminFunctions.heading\') }}</h3>', content)
    content = re.sub(r'<strong>Nur für Administratoren:</strong>', '<strong>{{ t(\'help.security.adminFunctions.adminOnly\') }}</strong>', content)
    content = re.sub(r'Diese Funktionen sind nur mit der ADMIN-Rolle verfügbar\.', '{{ t(\'help.security.adminFunctions.description\') }}', content)

    # User management
    content = re.sub(r'<h4 class="text-subtitle-1 mb-2">\s+<v-icon class="mr-1">mdi-account-multiple</v-icon>\s+Benutzerverwaltung\s+</h4>', '<h4 class="text-subtitle-1 mb-2">\n                    <v-icon class="mr-1">mdi-account-multiple</v-icon>\n                    {{ t(\'help.security.adminFunctions.userManagement.heading\') }}\n                  </h4>', content, flags=re.DOTALL)
    content = re.sub(r'<li>Neue Benutzer anlegen</li>', '<li>{{ t(\'help.security.adminFunctions.userManagement.createUsers\') }}</li>', content)
    content = re.sub(r'<li>Rollen zuweisen</li>', '<li>{{ t(\'help.security.adminFunctions.userManagement.assignRoles\') }}</li>', content)
    content = re.sub(r'<li>Passwörter zurücksetzen</li>', '<li>{{ t(\'help.security.adminFunctions.userManagement.resetPasswords\') }}</li>', content)
    content = re.sub(r'<li>Benutzer deaktivieren</li>', '<li>{{ t(\'help.security.adminFunctions.userManagement.deactivateUsers\') }}</li>', content)

    # Audit log
    content = re.sub(r'<h4 class="text-subtitle-1 mb-2">\s+<v-icon class="mr-1">mdi-clipboard-text-clock</v-icon>\s+Audit Log\s+</h4>', '<h4 class="text-subtitle-1 mb-2">\n                    <v-icon class="mr-1">mdi-clipboard-text-clock</v-icon>\n                    {{ t(\'help.security.adminFunctions.auditLog.heading\') }}\n                  </h4>', content, flags=re.DOTALL)
    content = re.sub(r'<li>Alle Systemaktivitäten einsehen</li>', '<li>{{ t(\'help.security.adminFunctions.auditLog.viewActivities\') }}</li>', content)
    content = re.sub(r'<li>Nach Benutzer/Zeit filtern</li>', '<li>{{ t(\'help.security.adminFunctions.auditLog.filterByUser\') }}</li>', content)
    content = re.sub(r'<li>Änderungen nachvollziehen</li>', '<li>{{ t(\'help.security.adminFunctions.auditLog.trackChanges\') }}</li>', content)
    content = re.sub(r'<li>Sicherheitsprüfungen durchführen</li>', '<li>{{ t(\'help.security.adminFunctions.auditLog.securityChecks\') }}</li>', content)

    print("Translating Troubleshooting section...")
    # Troubleshooting section title
    content = re.sub(
        r'<v-icon class="mr-2">mdi-wrench</v-icon>\s+Fehlerbehebung',
        '<v-icon class="mr-2">mdi-wrench</v-icon>\n            {{ t(\'help.troubleshooting.title\') }}',
        content
    )

    # Crawler finds no documents
    content = re.sub(
        r'Crawler findet keine Dokumente',
        "{{ t('help.troubleshooting.noDocuments.title') }}",
        content
    )
    content = re.sub(r'<strong>Mögliche Ursachen:</strong>', '<strong>{{ t(\'help.troubleshooting.noDocuments.possibleCauses\') }}</strong>', content)
    content = re.sub(r'<li>Exclude-Patterns \(Blacklist\) schliessen zu viel aus</li>', '<li>{{ t(\'help.troubleshooting.noDocuments.causes.excludePatterns\') }}</li>', content)
    content = re.sub(r'<li>Include-Patterns \(Whitelist\) zu restriktiv \(falls gesetzt\)</li>', '<li>{{ t(\'help.troubleshooting.noDocuments.causes.includePatterns\') }}</li>', content)
    content = re.sub(r'<li>Dokumente sind hinter JavaScript versteckt</li>', '<li>{{ t(\'help.troubleshooting.noDocuments.causes.hiddenBehindJs\') }}</li>', content)
    content = re.sub(r'<li>Seite blockiert Crawler \(User-Agent\)</li>', '<li>{{ t(\'help.troubleshooting.noDocuments.causes.blockedCrawler\') }}</li>', content)
    content = re.sub(r'<strong>Lösungen:</strong>', '<strong>{{ t(\'help.troubleshooting.noDocuments.solutions\') }}</strong>', content)
    content = re.sub(r'<li>Blacklist überprüfen und ggf\. Patterns entfernen</li>', '<li>{{ t(\'help.troubleshooting.noDocuments.solutionSteps.checkBlacklist\') }}</li>', content)
    content = re.sub(r'<li>Whitelist leeren \(empfohlen\) - KI filtert relevante Inhalte</li>', '<li>{{ t(\'help.troubleshooting.noDocuments.solutionSteps.emptyWhitelist\') }}</li>', content)
    content = re.sub(r'<li>JavaScript-Rendering aktivieren</li>', '<li>{{ t(\'help.troubleshooting.noDocuments.solutionSteps.enableJs\') }}</li>', content)
    content = re.sub(r'<li>Max-Tiefe erhöhen</li>', '<li>{{ t(\'help.troubleshooting.noDocuments.solutionSteps.increaseDepth\') }}</li>', content)

    # AI analysis returns no results
    content = re.sub(
        r'KI-Analyse liefert keine Ergebnisse',
        "{{ t('help.troubleshooting.noAiResults.title') }}",
        content
    )
    content = re.sub(r'<li>Keyword-Filter zu strikt</li>', '<li>{{ t(\'help.troubleshooting.noAiResults.causes.strictKeywords\') }}</li>', content)
    content = re.sub(r'<li>Dokumente enthalten keine relevanten Inhalte</li>', '<li>{{ t(\'help.troubleshooting.noAiResults.causes.noRelevantContent\') }}</li>', content)
    content = re.sub(r'<li>Prompt nicht passend</li>', '<li>{{ t(\'help.troubleshooting.noAiResults.causes.unsuitablePrompt\') }}</li>', content)
    content = re.sub(r'<li>Keywords erweitern</li>', '<li>{{ t(\'help.troubleshooting.noAiResults.solutionSteps.expandKeywords\') }}</li>', content)
    content = re.sub(r'<li>"Gefilterte analysieren" nutzen</li>', '<li>{{ t(\'help.troubleshooting.noAiResults.solutionSteps.analyzeFiltered\') }}</li>', content)
    content = re.sub(r'<li>Prompt optimieren</li>', '<li>{{ t(\'help.troubleshooting.noAiResults.solutionSteps.optimizePrompt\') }}</li>', content)

    # Documents remain pending
    content = re.sub(
        r'Dokumente bleiben in "Wartend"',
        "{{ t('help.troubleshooting.pendingDocuments.title') }}",
        content
    )
    content = re.sub(r'<li>Worker nicht aktiv</li>', '<li>{{ t(\'help.troubleshooting.pendingDocuments.causes.workerInactive\') }}</li>', content)
    content = re.sub(r'<li>Queue überlastet</li>', '<li>{{ t(\'help.troubleshooting.pendingDocuments.causes.queueOverloaded\') }}</li>', content)
    content = re.sub(r'<li>Worker-Status im Crawler prüfen</li>', '<li>{{ t(\'help.troubleshooting.pendingDocuments.solutionSteps.checkWorker\') }}</li>', content)
    content = re.sub(r'<li>"Pending verarbeiten" manuell klicken</li>', '<li>{{ t(\'help.troubleshooting.pendingDocuments.solutionSteps.manualProcess\') }}</li>', content)

    # Status codes
    content = re.sub(r'<h3 class="text-h6 mt-4 mb-3">Status-Codes</h3>', '<h3 class="text-h6 mt-4 mb-3">{{ t(\'help.troubleshooting.statusCodes.heading\') }}</h3>', content)
    content = re.sub(r'<thead><tr><th>Status</th><th>Bedeutung</th><th>Aktion</th></tr></thead>', '<thead><tr><th>{{ t(\'help.troubleshooting.statusCodes.status\') }}</th><th>{{ t(\'help.troubleshooting.statusCodes.meaning\') }}</th><th>{{ t(\'help.troubleshooting.statusCodes.action\') }}</th></tr></thead>', content)
    content = re.sub(r'<td>Wartet auf Verarbeitung</td>\s+<td>Abwarten oder manuell starten</td>', '<td>{{ t(\'help.troubleshooting.statusCodes.pending.meaning\') }}</td>\n                  <td>{{ t(\'help.troubleshooting.statusCodes.pending.action\') }}</td>', content, flags=re.DOTALL)
    content = re.sub(r'<td>Wird verarbeitet</td>\s+<td>Abwarten</td>', '<td>{{ t(\'help.troubleshooting.statusCodes.processing.meaning\') }}</td>\n                  <td>{{ t(\'help.troubleshooting.statusCodes.processing.action\') }}</td>', content, flags=re.DOTALL)
    content = re.sub(r'<td>KI-Analyse läuft</td>', '<td>{{ t(\'help.troubleshooting.statusCodes.analyzing.meaning\') }}</td>', content)
    content = re.sub(r'<td>Erfolgreich</td>\s+<td>Keine Aktion nötig</td>', '<td>{{ t(\'help.troubleshooting.statusCodes.completed.meaning\') }}</td>\n                  <td>{{ t(\'help.troubleshooting.statusCodes.completed.action\') }}</td>', content, flags=re.DOTALL)
    content = re.sub(r'<td>Durch Keywords gefiltert</td>\s+<td>Ggf\. manuell analysieren</td>', '<td>{{ t(\'help.troubleshooting.statusCodes.filtered.meaning\') }}</td>\n                  <td>{{ t(\'help.troubleshooting.statusCodes.filtered.action\') }}</td>', content, flags=re.DOTALL)
    content = re.sub(r'<td>Fehler aufgetreten</td>\s+<td>Fehler prüfen, neu versuchen</td>', '<td>{{ t(\'help.troubleshooting.statusCodes.failed.meaning\') }}</td>\n                  <td>{{ t(\'help.troubleshooting.statusCodes.failed.action\') }}</td>', content, flags=re.DOTALL)

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    # Calculate changes
    changes_made = len([1 for i, (c1, c2) in enumerate(zip(original_content, content)) if c1 != c2])
    print(f"\n✓ Translation completed!")
    print(f"  - Approximately {changes_made} characters changed")
    print(f"  - File: {file_path}")

if __name__ == '__main__':
    translate_security_and_troubleshooting()
