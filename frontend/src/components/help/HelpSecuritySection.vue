<template>
  <HelpCard section-id="security" :title="t('help.security.title')" icon="mdi-shield-lock" color="primary">
    <h3 class="text-h6 mb-3">{{ t('help.security.login.heading') }}</h3>
    <p class="mb-4">
      {{ t('help.security.login.description') }}
    </p>

    <v-alert type="info" variant="tonal" class="mb-4">
      <strong>{{ t('help.security.login.important') }}</strong> {{ t('help.security.login.tokenExpiry') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.security.roles.heading') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr><th>{{ t('help.security.roles.role') }}</th><th>{{ t('help.security.roles.permissions') }}</th></tr>
      </thead>
      <tbody>
        <tr>
          <td><v-chip size="small" color="error">ADMIN</v-chip></td>
          <td>
            <ul class="pl-4">
              <li>{{ t('help.security.roles.admin.fullAccess') }}</li>
              <li>{{ t('help.security.roles.admin.userManagement') }}</li>
              <li>{{ t('help.security.roles.admin.auditLog') }}</li>
              <li>{{ t('help.security.roles.admin.systemConfig') }}</li>
            </ul>
          </td>
        </tr>
        <tr>
          <td><v-chip size="small" color="warning">EDITOR</v-chip></td>
          <td>
            <ul class="pl-4">
              <li>{{ t('help.security.roles.editor.manageCategories') }}</li>
              <li>{{ t('help.security.roles.editor.controlCrawler') }}</li>
              <li>{{ t('help.security.roles.editor.processDocuments') }}</li>
              <li>{{ t('help.security.roles.editor.exportResults') }}</li>
            </ul>
          </td>
        </tr>
        <tr>
          <td><v-chip size="small" color="info">VIEWER</v-chip></td>
          <td>
            <ul class="pl-4">
              <li>{{ t('help.security.roles.viewer.viewData') }}</li>
              <li>{{ t('help.security.roles.viewer.exportResults') }}</li>
              <li>{{ t('help.security.roles.viewer.noEditRights') }}</li>
            </ul>
          </td>
        </tr>
      </tbody>
    </v-table>

    <h3 class="text-h6 mb-3">{{ t('help.security.password.heading') }}</h3>
    <v-alert type="warning" variant="tonal" class="mb-4">
      <strong>{{ t('help.security.password.requirements') }}</strong>
      <ul class="pl-4 mt-2">
        <li>{{ t('help.security.password.minLength') }}</li>
        <li>{{ t('help.security.password.uppercase') }}</li>
        <li>{{ t('help.security.password.lowercase') }}</li>
        <li>{{ t('help.security.password.digit') }}</li>
        <li>{{ t('help.security.password.specialChar') }}</li>
      </ul>
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.security.features.heading') }}</h3>
    <v-expansion-panels variant="accordion" class="mb-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon color="success" class="mr-2">mdi-shield-check</v-icon>
          {{ t('help.security.features.rateLimit.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p>{{ t('help.security.features.rateLimit.description') }}</p>
          <v-table density="compact" class="mt-2">
            <thead><tr><th>{{ t('help.security.features.rateLimit.action') }}</th><th>{{ t('help.security.features.rateLimit.limit') }}</th><th>{{ t('help.security.features.rateLimit.timeWindow') }}</th></tr></thead>
            <tbody>
              <tr><td>{{ t('help.security.features.rateLimit.loginAttempts') }}</td><td>5</td><td>{{ t('help.security.features.rateLimit.perMinute') }}</td></tr>
              <tr><td>{{ t('help.security.features.rateLimit.failedLogins') }}</td><td>10</td><td>{{ t('help.security.features.rateLimit.per15Minutes') }}</td></tr>
              <tr><td>{{ t('help.security.features.rateLimit.passwordChanges') }}</td><td>3</td><td>{{ t('help.security.features.rateLimit.per5Minutes') }}</td></tr>
              <tr><td>{{ t('help.security.features.rateLimit.apiRequests') }}</td><td>100</td><td>{{ t('help.security.features.rateLimit.perMinute') }}</td></tr>
            </tbody>
          </v-table>
          <v-alert type="info" variant="tonal" class="mt-2" density="compact">
            {{ t('help.security.features.rateLimit.note') }}
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon color="success" class="mr-2">mdi-logout</v-icon>
          {{ t('help.security.features.tokenBlacklist.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p>
            {{ t('help.security.features.tokenBlacklist.description') }}
          </p>
          <v-alert type="success" variant="tonal" class="mt-2" density="compact">
            {{ t('help.security.features.tokenBlacklist.note') }}
          </v-alert>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon color="success" class="mr-2">mdi-lock</v-icon>
          {{ t('help.security.features.encryption.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-table density="compact">
            <tbody>
              <tr><td><strong>{{ t('help.security.features.encryption.passwordHashing') }}</strong></td><td>{{ t('help.security.features.encryption.passwordHashingValue') }}</td></tr>
              <tr><td><strong>{{ t('help.security.features.encryption.tokenSignature') }}</strong></td><td>{{ t('help.security.features.encryption.tokenSignatureValue') }}</td></tr>
              <tr><td><strong>{{ t('help.security.features.encryption.transport') }}</strong></td><td>{{ t('help.security.features.encryption.transportValue') }}</td></tr>
            </tbody>
          </v-table>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <v-expansion-panel>
        <v-expansion-panel-title>
          <v-icon color="success" class="mr-2">mdi-history</v-icon>
          {{ t('help.security.features.auditLog.title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <p><strong>{{ t('help.security.features.auditLog.auditLogHeading') }}</strong> {{ t('help.security.features.auditLog.description') }}</p>
          <ul class="pl-4 mb-3">
            <li>{{ t('help.security.features.auditLog.who') }}</li>
            <li>{{ t('help.security.features.auditLog.when') }}</li>
            <li>{{ t('help.security.features.auditLog.what') }}</li>
          </ul>
          <p><strong>{{ t('help.security.features.auditLog.versioningHeading') }}</strong> {{ t('help.security.features.auditLog.versioningDescription') }}</p>
          <ul class="pl-4">
            <li>{{ t('help.security.features.auditLog.onlyChanges') }}</li>
            <li>{{ t('help.security.features.auditLog.fullState') }}</li>
            <li>{{ t('help.security.features.auditLog.snapshots') }}</li>
          </ul>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <h3 class="text-h6 mb-3">{{ t('help.security.changePassword.heading') }}</h3>
    <v-timeline density="compact" side="end" class="mb-4">
      <v-timeline-item dot-color="primary" size="small">
        <v-card variant="outlined" class="pa-3">
          <strong>1.</strong> {{ t('help.security.changePassword.step1') }}
        </v-card>
      </v-timeline-item>
      <v-timeline-item dot-color="primary" size="small">
        <v-card variant="outlined" class="pa-3">
          <strong>2.</strong> {{ t('help.security.changePassword.step2') }}
        </v-card>
      </v-timeline-item>
      <v-timeline-item dot-color="primary" size="small">
        <v-card variant="outlined" class="pa-3">
          <strong>3.</strong> {{ t('help.security.changePassword.step3') }}
        </v-card>
      </v-timeline-item>
      <v-timeline-item dot-color="success" size="small">
        <v-card variant="outlined" class="pa-3">
          <strong>4.</strong> {{ t('help.security.changePassword.step4') }}
        </v-card>
      </v-timeline-item>
    </v-timeline>

    <h3 class="text-h6 mb-3">{{ t('help.security.adminFunctions.heading') }}</h3>
    <v-alert type="error" variant="tonal" class="mb-4">
      <strong>{{ t('help.security.adminFunctions.adminOnly') }}</strong>
      {{ t('help.security.adminFunctions.description') }}
    </v-alert>

    <v-row>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3 h-100">
          <h4 class="text-subtitle-1 mb-2">
            <v-icon class="mr-1">mdi-account-multiple</v-icon>
            {{ t('help.security.adminFunctions.userManagement.heading') }}
          </h4>
          <ul class="pl-4 text-body-2">
            <li>{{ t('help.security.adminFunctions.userManagement.createUsers') }}</li>
            <li>{{ t('help.security.adminFunctions.userManagement.assignRoles') }}</li>
            <li>{{ t('help.security.adminFunctions.userManagement.resetPasswords') }}</li>
            <li>{{ t('help.security.adminFunctions.userManagement.deactivateUsers') }}</li>
          </ul>
        </v-card>
      </v-col>
      <v-col cols="12" md="6">
        <v-card variant="outlined" class="pa-3 h-100">
          <h4 class="text-subtitle-1 mb-2">
            <v-icon class="mr-1">mdi-clipboard-text-clock</v-icon>
            {{ t('help.security.adminFunctions.auditLog.heading') }}
          </h4>
          <ul class="pl-4 text-body-2">
            <li>{{ t('help.security.adminFunctions.auditLog.viewActivities') }}</li>
            <li>{{ t('help.security.adminFunctions.auditLog.filterByUser') }}</li>
            <li>{{ t('help.security.adminFunctions.auditLog.trackChanges') }}</li>
            <li>{{ t('help.security.adminFunctions.auditLog.securityChecks') }}</li>
          </ul>
        </v-card>
      </v-col>
    </v-row>
  </HelpCard>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()
</script>
