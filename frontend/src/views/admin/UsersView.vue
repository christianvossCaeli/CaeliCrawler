<template>
  <v-container fluid>
    <!-- Header -->
    <PageHeader
      :title="t('admin.users.title')"
      :subtitle="t('admin.users.subtitle')"
      icon="mdi-account-group"
    >
      <template #actions>
        <v-btn variant="tonal" color="primary" @click="openCreateDialog">
          <v-icon start>mdi-plus</v-icon>
          {{ t('admin.users.actions.create') }}
        </v-btn>
      </template>
    </PageHeader>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text>
        <v-row align="center">
          <v-col cols="12" md="4">
            <v-text-field
              v-model="search"
              :label="t('admin.users.filters.search')"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
              @update:model-value="debouncedFetch"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="roleFilter"
              :label="t('admin.users.filters.role')"
              :items="roleOptions"
              clearable
              hide-details
              @update:model-value="fetchUsers"
            />
          </v-col>
          <v-col cols="12" md="3">
            <v-select
              v-model="activeFilter"
              :label="t('admin.users.filters.status')"
              :items="activeOptions"
              clearable
              hide-details
              @update:model-value="fetchUsers"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Users Table -->
    <v-card>
      <v-data-table-server
        v-model:page="page"
        v-model:items-per-page="perPage"
        :headers="headers"
        :items="users"
        :items-length="totalUsers"
        :loading="loading"
        @update:page="fetchUsers"
        @update:items-per-page="fetchUsers"
      >
        <!-- Role Column -->
        <template #item.role="{ item }">
          <v-chip
            :color="getRoleColor(item.role)"
            size="small"
            label
          >
            {{ getRoleLabel(item.role) }}
          </v-chip>
        </template>

        <!-- Active Column -->
        <template #item.is_active="{ item }">
          <v-icon :color="item.is_active ? 'success' : 'error'">
            {{ item.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
          </v-icon>
        </template>

        <!-- Last Login Column -->
        <template #item.last_login="{ item }">
          <span v-if="item.last_login">
            {{ formatDate(item.last_login) }}
          </span>
          <span v-else class="text-medium-emphasis">{{ t('admin.users.never') }}</span>
        </template>

        <!-- Actions Column -->
        <template #item.actions="{ item }">
          <div class="d-flex justify-end ga-1">
            <v-btn icon="mdi-pencil" size="small" variant="tonal" :title="t('common.edit')" :aria-label="t('common.edit')" @click="openEditDialog(item)"></v-btn>
            <v-btn icon="mdi-lock-reset" size="small" variant="tonal" :title="t('admin.users.actions.resetPassword')" :aria-label="t('admin.users.actions.resetPassword')" @click="openPasswordDialog(item)"></v-btn>
            <v-btn icon="mdi-delete" size="small" variant="tonal" color="error" :title="t('common.delete')" :aria-label="t('common.delete')" :disabled="item.id === currentUser?.id" @click="confirmDelete(item)"></v-btn>
          </div>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialogOpen" max-width="550">
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-avatar :color="editingUser ? 'surface' : 'primary-darken-1'" size="40" class="mr-3">
            <v-icon :color="editingUser ? 'primary' : 'on-primary'">{{ editingUser ? 'mdi-account-edit' : 'mdi-account-plus' }}</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ editingUser ? t('admin.users.dialog.editTitle') : t('admin.users.dialog.createTitle') }}</div>
            <div v-if="editingUser" class="text-caption opacity-80">{{ editingUser.email }}</div>
          </div>
        </v-card-title>
        <v-card-text class="pa-6">
          <v-form ref="formRef" @submit.prevent="saveUser">
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.email"
                  :label="t('admin.users.form.email')"
                  type="email"
                  :rules="[required, emailRule]"
                  variant="outlined"
                  prepend-inner-icon="mdi-email"
                />
              </v-col>
              <v-col cols="12">
                <v-text-field
                  v-model="formData.full_name"
                  :label="t('admin.users.form.name')"
                  :rules="[required]"
                  variant="outlined"
                  prepend-inner-icon="mdi-account"
                />
              </v-col>
              <v-col v-if="!editingUser" cols="12">
                <v-text-field
                  v-model="formData.password"
                  :label="t('admin.users.form.password')"
                  type="password"
                  :rules="[required, passwordValidRule]"
                  variant="outlined"
                  prepend-inner-icon="mdi-lock"
                />
                <PasswordStrengthIndicator
                  v-if="formData.password"
                  :password="formData.password"
                  show-requirements
                  class="mt-2"
                  @update:is-valid="passwordValid = $event"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-select
                  v-model="formData.role"
                  :label="t('admin.users.form.role')"
                  :items="roleOptions"
                  :rules="[required]"
                  variant="outlined"
                  prepend-inner-icon="mdi-shield-account"
                />
              </v-col>
              <v-col cols="12" md="6">
                <v-card variant="outlined" class="pa-3 h-100 d-flex align-center">
                  <v-switch
                    v-model="formData.is_active"
                    :label="t('admin.users.form.active')"
                    color="success"
                    hide-details
                    :disabled="editingUser?.id === currentUser?.id"
                  />
                </v-card>
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="dialogOpen = false">{{ t('common.cancel') }}</v-btn>
          <v-spacer />
          <v-btn variant="tonal" color="primary" :loading="saving" @click="saveUser">
            <v-icon start>mdi-check</v-icon>
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Password Reset Dialog -->
    <v-dialog v-model="passwordDialogOpen" max-width="450">
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-warning">
          <v-avatar color="warning-darken-1" size="40" class="mr-3">
            <v-icon color="on-warning">mdi-lock-reset</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ t('admin.users.dialog.resetPasswordTitle') }}</div>
            <div class="text-caption opacity-80">{{ selectedUser?.email }}</div>
          </div>
        </v-card-title>
        <v-card-text class="pa-6">
          <v-alert type="info" variant="tonal" class="mb-4">
            {{ t('admin.users.resetPasswordFor') }} <strong>{{ selectedUser?.full_name || selectedUser?.email }}</strong>
          </v-alert>
          <v-text-field
            v-model="newPassword"
            :label="t('admin.users.newPassword')"
            type="password"
            :rules="[required, newPasswordValidRule]"
            variant="outlined"
            prepend-inner-icon="mdi-lock"
          />
          <PasswordStrengthIndicator
            v-if="newPassword"
            :password="newPassword"
            show-requirements
            class="mt-2"
            @update:is-valid="newPasswordValid = $event"
          />
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="passwordDialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-spacer />
          <v-btn
            variant="tonal"
            color="warning"
            :loading="saving"
            :disabled="!newPasswordValid"
            @click="resetPassword"
          >
            <v-icon start>mdi-lock-reset</v-icon>
            {{ t('admin.users.resetButton') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialogOpen" max-width="450">
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-error">
          <v-avatar color="error-darken-1" size="40" class="mr-3">
            <v-icon color="on-error">mdi-account-remove</v-icon>
          </v-avatar>
          <div class="text-h6">{{ t('admin.users.dialog.deleteTitle') }}</div>
        </v-card-title>
        <v-card-text class="pa-6">
          <v-alert type="error" variant="tonal">
            {{ t('admin.users.deleteConfirm', { email: selectedUser?.email }) }}
          </v-alert>
        </v-card-text>
        <v-divider />
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="deleteDialogOpen = false">
            {{ t('common.cancel') }}
          </v-btn>
          <v-spacer />
          <v-btn variant="tonal" color="error" :loading="saving" @click="deleteUser">
            <v-icon start>mdi-delete</v-icon>
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/services/api'
import { useAuthStore, type User } from '@/stores/auth'
import { useDebounce, DEBOUNCE_DELAYS } from '@/composables/useDebounce'
import PasswordStrengthIndicator from '@/components/PasswordStrengthIndicator.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { useLogger } from '@/composables/useLogger'
import { getErrorMessage } from '@/composables/useApiErrorHandler'

const logger = useLogger('UsersView')

const { t } = useI18n()
const auth = useAuthStore()
const currentUser = computed(() => auth.user)

// State
const users = ref<User[]>([])
const totalUsers = ref(0)
const loading = ref(false)
const saving = ref(false)

// Pagination & Filters
const page = ref(1)
const perPage = ref(20)
const search = ref('')
const roleFilter = ref<string | null>(null)
const activeFilter = ref<boolean | null>(null)

// Dialogs
const dialogOpen = ref(false)
const passwordDialogOpen = ref(false)
const deleteDialogOpen = ref(false)
const formRef = ref<{ validate: () => Promise<{ valid: boolean }>; reset: () => void } | null>(null)

const editingUser = ref<User | null>(null)
const selectedUser = ref<User | null>(null)
const newPassword = ref('')
const passwordValid = ref(false)
const newPasswordValid = ref(false)

const formData = reactive({
  email: '',
  full_name: '',
  password: '',
  role: 'VIEWER',
  is_active: true,
})

// Table headers
const headers = computed(() => [
  { title: t('admin.users.columns.email'), key: 'email', sortable: false },
  { title: t('admin.users.columns.name'), key: 'full_name', sortable: false },
  { title: t('admin.users.columns.role'), key: 'role', sortable: false, width: 120 },
  { title: t('admin.users.columns.active'), key: 'is_active', sortable: false, width: 80 },
  { title: t('admin.users.columns.lastLogin'), key: 'last_login', sortable: false, width: 180 },
  { title: t('common.actions'), key: 'actions', sortable: false, align: 'end' as const },
])

// Options
const roleOptions = computed(() => [
  { title: t('roles.VIEWER'), value: 'VIEWER' },
  { title: t('roles.EDITOR'), value: 'EDITOR' },
  { title: t('roles.ADMIN'), value: 'ADMIN' },
])

const activeOptions = computed(() => [
  { title: t('admin.users.activeLabel'), value: true },
  { title: t('admin.users.inactiveLabel'), value: false },
])

// Validation rules
const required = (v: unknown) => !!v || t('validation.required')
const emailRule = (v: string) => /.+@.+\..+/.test(v) || t('validation.email')
const passwordValidRule = () => passwordValid.value || t('admin.users.passwordNotValid')
const newPasswordValidRule = () => newPasswordValid.value || t('admin.users.passwordNotValid')

// Helpers
function getRoleColor(role: string): string {
  const colors: Record<string, string> = {
    ADMIN: 'error',
    EDITOR: 'primary',
    VIEWER: 'grey',
  }
  return colors[role] || 'grey'
}

function getRoleLabel(role: string): string {
  return t(`roles.${role}`) || role
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// Debounce search - uses composable with automatic cleanup
const { debouncedFn: debouncedFetch } = useDebounce(
  () => fetchUsers(),
  { delay: DEBOUNCE_DELAYS.SEARCH }
)

// API calls
async function fetchUsers() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: page.value,
      per_page: perPage.value,
    }
    if (search.value) params.search = search.value
    if (roleFilter.value) params.role = roleFilter.value
    if (activeFilter.value !== null) params.is_active = activeFilter.value

    const response = await api.get('/admin/users', { params })
    users.value = response.data.items
    totalUsers.value = response.data.total
  } catch (error) {
    logger.error('Failed to fetch users:', error)
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  editingUser.value = null
  Object.assign(formData, {
    email: '',
    full_name: '',
    password: '',
    role: 'VIEWER',
    is_active: true,
  })
  dialogOpen.value = true
}

function openEditDialog(user: User) {
  editingUser.value = user
  Object.assign(formData, {
    email: user.email,
    full_name: user.full_name,
    password: '',
    role: user.role,
    is_active: user.is_active,
  })
  dialogOpen.value = true
}

async function saveUser() {
  const valid = await formRef.value?.validate()
  if (!valid?.valid) return

  saving.value = true
  try {
    if (editingUser.value) {
      await api.put(`/admin/users/${editingUser.value.id}`, {
        email: formData.email,
        full_name: formData.full_name,
        role: formData.role,
        is_active: formData.is_active,
      })
    } else {
      await api.post('/admin/users', formData)
    }
    dialogOpen.value = false
    await fetchUsers()
  } catch (error) {
    logger.error('Failed to save user:', error)
    alert(getErrorMessage(error) || t('admin.users.saveError'))
  } finally {
    saving.value = false
  }
}

function openPasswordDialog(user: User) {
  selectedUser.value = user
  newPassword.value = ''
  passwordDialogOpen.value = true
}

async function resetPassword() {
  if (!selectedUser.value || newPassword.value.length < 8) return

  saving.value = true
  try {
    await api.post(`/admin/users/${selectedUser.value.id}/reset-password`, {
      new_password: newPassword.value,
    })
    passwordDialogOpen.value = false
  } catch (error) {
    logger.error('Failed to reset password:', error)
    alert(getErrorMessage(error) || t('admin.users.resetError'))
  } finally {
    saving.value = false
  }
}

function confirmDelete(user: User) {
  selectedUser.value = user
  deleteDialogOpen.value = true
}

async function deleteUser() {
  if (!selectedUser.value) return

  saving.value = true
  try {
    await api.delete(`/admin/users/${selectedUser.value.id}`)
    deleteDialogOpen.value = false
    await fetchUsers()
  } catch (error) {
    logger.error('Failed to delete user:', error)
    alert(getErrorMessage(error) || t('admin.users.deleteError'))
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
