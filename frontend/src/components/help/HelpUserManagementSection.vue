<template>
  <HelpCard section-id="user-management" :title="t('help.userManagement.title')" icon="mdi-account-group" color="blue">
    <p class="mb-4">
      {{ t('help.userManagement.description') }}
    </p>

    <v-alert type="info" variant="tonal" class="mb-4">
      <v-icon class="mr-2">mdi-shield-account</v-icon>
      {{ t('help.userManagement.accessInfo') }}
    </v-alert>

    <h3 class="text-h6 mb-3">{{ t('help.userManagement.overview.title') }}</h3>
    <p class="mb-4">
      {{ t('help.userManagement.overview.description') }}
    </p>

    <v-list density="compact" class="mb-4">
      <v-list-item prepend-icon="mdi-format-list-bulleted">
        <v-list-item-subtitle>{{ t('help.userManagement.overview.features.list') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-account-plus">
        <v-list-item-subtitle>{{ t('help.userManagement.overview.features.create') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-account-edit">
        <v-list-item-subtitle>{{ t('help.userManagement.overview.features.edit') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-lock-reset">
        <v-list-item-subtitle>{{ t('help.userManagement.overview.features.resetPassword') }}</v-list-item-subtitle>
      </v-list-item>
      <v-list-item prepend-icon="mdi-account-off">
        <v-list-item-subtitle>{{ t('help.userManagement.overview.features.deactivate') }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.userManagement.roles.title') }}</h3>
    <v-row>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon color="error" class="mr-2">mdi-shield-crown</v-icon>
            {{ t('help.userManagement.roles.admin.name') }}
          </v-card-title>
          <v-card-text>
            <p class="mb-2">{{ t('help.userManagement.roles.admin.description') }}</p>
            <v-list density="compact">
              <v-list-item
                v-for="(permission, idx) in (t('help.userManagement.roles.admin.permissions', { returnObjects: true }) as unknown as string[])"
                :key="idx"
                prepend-icon="mdi-check"
              >
                <v-list-item-subtitle>{{ permission }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon color="warning" class="mr-2">mdi-pencil</v-icon>
            {{ t('help.userManagement.roles.editor.name') }}
          </v-card-title>
          <v-card-text>
            <p class="mb-2">{{ t('help.userManagement.roles.editor.description') }}</p>
            <v-list density="compact">
              <v-list-item
                v-for="(permission, idx) in (t('help.userManagement.roles.editor.permissions', { returnObjects: true }) as unknown as string[])"
                :key="idx"
                prepend-icon="mdi-check"
              >
                <v-list-item-subtitle>{{ permission }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="h-100">
          <v-card-title class="text-subtitle-1">
            <v-icon color="info" class="mr-2">mdi-eye</v-icon>
            {{ t('help.userManagement.roles.viewer.name') }}
          </v-card-title>
          <v-card-text>
            <p class="mb-2">{{ t('help.userManagement.roles.viewer.description') }}</p>
            <v-list density="compact">
              <v-list-item
                v-for="(permission, idx) in (t('help.userManagement.roles.viewer.permissions', { returnObjects: true }) as unknown as string[])"
                :key="idx"
                prepend-icon="mdi-check"
              >
                <v-list-item-subtitle>{{ permission }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.userManagement.createUser.title') }}</h3>
    <v-timeline density="compact" side="end" class="mb-4">
      <v-timeline-item
        v-for="(step, key) in createUserSteps"
        :key="key"
        dot-color="primary"
        size="small"
      >
        {{ step }}
      </v-timeline-item>
    </v-timeline>

    <v-alert type="info" variant="tonal" class="mb-4">
      {{ t('help.userManagement.createUser.passwordRequirements') }}
    </v-alert>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.userManagement.editUser.title') }}</h3>
    <v-table density="compact" class="mb-4">
      <thead>
        <tr>
          <th>{{ t('common.field') }}</th>
          <th>{{ t('common.description') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><code>{{ t('help.userManagement.editUser.editableFields.email') }}</code></td>
          <td>E-Mail-Adresse des Benutzers</td>
        </tr>
        <tr>
          <td><code>{{ t('help.userManagement.editUser.editableFields.fullName') }}</code></td>
          <td>Anzeigename des Benutzers</td>
        </tr>
        <tr>
          <td><code>{{ t('help.userManagement.editUser.editableFields.role') }}</code></td>
          <td>Admin, Editor oder Viewer</td>
        </tr>
        <tr>
          <td><code>{{ t('help.userManagement.editUser.editableFields.isActive') }}</code></td>
          <td>Aktiviert oder deaktiviert</td>
        </tr>
      </tbody>
    </v-table>

    <v-alert type="warning" variant="tonal" class="mb-4">
      <strong>{{ t('help.userManagement.editUser.restrictions.title') }}:</strong>
      <v-list density="compact" class="bg-transparent">
        <v-list-item prepend-icon="mdi-alert">
          <v-list-item-subtitle>{{ t('help.userManagement.editUser.restrictions.ownRole') }}</v-list-item-subtitle>
        </v-list-item>
        <v-list-item prepend-icon="mdi-alert">
          <v-list-item-subtitle>{{ t('help.userManagement.editUser.restrictions.ownAccount') }}</v-list-item-subtitle>
        </v-list-item>
        <v-list-item prepend-icon="mdi-alert">
          <v-list-item-subtitle>{{ t('help.userManagement.editUser.restrictions.deleteOwnAccount') }}</v-list-item-subtitle>
        </v-list-item>
      </v-list>
    </v-alert>

    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 mb-3">{{ t('help.userManagement.resetPassword.title') }}</h3>
    <p class="mb-4">{{ t('help.userManagement.resetPassword.description') }}</p>

    <v-list density="compact" class="mb-4">
      <v-list-item
        v-for="(step, idx) in (t('help.userManagement.resetPassword.steps', { returnObjects: true }) as unknown as string[])"
        :key="idx"
        :prepend-icon="`mdi-numeric-${idx + 1}-circle`"
      >
        <v-list-item-subtitle>{{ step }}</v-list-item-subtitle>
      </v-list-item>
    </v-list>
  </HelpCard>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import HelpCard from './HelpCard.vue'

const { t } = useI18n()

const createUserSteps = computed(() => {
  const steps = t('help.userManagement.createUser.steps', { returnObjects: true })
  if (typeof steps === 'object' && steps !== null) {
    return Object.values(steps) as string[]
  }
  return []
})
</script>
