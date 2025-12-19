<template>
  <v-container fluid>
    <!-- Header -->
    <v-row class="mb-4">
      <v-col>
        <h1 class="text-h4 font-weight-bold">
          <v-icon start size="32">mdi-account-group</v-icon>
          Benutzerverwaltung
        </h1>
        <p class="text-body-2 text-medium-emphasis mt-1">
          Benutzer erstellen, bearbeiten und verwalten
        </p>
      </v-col>
      <v-col cols="auto">
        <v-btn color="primary" @click="openCreateDialog">
          <v-icon start>mdi-plus</v-icon>
          Neuer Benutzer
        </v-btn>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-text-field
          v-model="search"
          label="Suche"
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="compact"
          clearable
          @update:model-value="debouncedFetch"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="roleFilter"
          label="Rolle"
          :items="roleOptions"
          variant="outlined"
          density="compact"
          clearable
          @update:model-value="fetchUsers"
        />
      </v-col>
      <v-col cols="12" md="3">
        <v-select
          v-model="activeFilter"
          label="Status"
          :items="activeOptions"
          variant="outlined"
          density="compact"
          clearable
          @update:model-value="fetchUsers"
        />
      </v-col>
    </v-row>

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
          <span v-else class="text-medium-emphasis">Nie</span>
        </template>

        <!-- Actions Column -->
        <template #item.actions="{ item }">
          <v-btn
            icon
            variant="text"
            size="small"
            @click="openEditDialog(item)"
          >
            <v-icon>mdi-pencil</v-icon>
            <v-tooltip activator="parent">Bearbeiten</v-tooltip>
          </v-btn>
          <v-btn
            icon
            variant="text"
            size="small"
            @click="openPasswordDialog(item)"
          >
            <v-icon>mdi-lock-reset</v-icon>
            <v-tooltip activator="parent">Passwort zurücksetzen</v-tooltip>
          </v-btn>
          <v-btn
            icon
            variant="text"
            size="small"
            color="error"
            :disabled="item.id === currentUser?.id"
            @click="confirmDelete(item)"
          >
            <v-icon>mdi-delete</v-icon>
            <v-tooltip activator="parent">Löschen</v-tooltip>
          </v-btn>
        </template>
      </v-data-table-server>
    </v-card>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialogOpen" max-width="500">
      <v-card>
        <v-card-title>
          {{ editingUser ? 'Benutzer bearbeiten' : 'Neuer Benutzer' }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef" @submit.prevent="saveUser">
            <v-text-field
              v-model="formData.email"
              label="E-Mail"
              type="email"
              :rules="[required, emailRule]"
              variant="outlined"
              class="mb-3"
            />
            <v-text-field
              v-model="formData.full_name"
              label="Name"
              :rules="[required]"
              variant="outlined"
              class="mb-3"
            />
            <v-text-field
              v-if="!editingUser"
              v-model="formData.password"
              label="Passwort"
              type="password"
              :rules="[required, minLength(8)]"
              variant="outlined"
              class="mb-3"
            />
            <v-select
              v-model="formData.role"
              label="Rolle"
              :items="roleOptions"
              :rules="[required]"
              variant="outlined"
              class="mb-3"
            />
            <v-switch
              v-model="formData.is_active"
              label="Aktiv"
              color="success"
              :disabled="editingUser?.id === currentUser?.id"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialogOpen = false">Abbrechen</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveUser">
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Password Reset Dialog -->
    <v-dialog v-model="passwordDialogOpen" max-width="400">
      <v-card>
        <v-card-title>Passwort zurücksetzen</v-card-title>
        <v-card-text>
          <p class="mb-4">
            Neues Passwort für <strong>{{ selectedUser?.email }}</strong>:
          </p>
          <v-text-field
            v-model="newPassword"
            label="Neues Passwort"
            type="password"
            :rules="[required, minLength(8)]"
            variant="outlined"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="passwordDialogOpen = false">
            Abbrechen
          </v-btn>
          <v-btn color="primary" :loading="saving" @click="resetPassword">
            Zurücksetzen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialogOpen" max-width="400">
      <v-card>
        <v-card-title class="text-error">Benutzer löschen?</v-card-title>
        <v-card-text>
          Sind Sie sicher, dass Sie den Benutzer
          <strong>{{ selectedUser?.email }}</strong> löschen möchten?
          Diese Aktion kann nicht rückgängig gemacht werden.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialogOpen = false">
            Abbrechen
          </v-btn>
          <v-btn color="error" :loading="saving" @click="deleteUser">
            Löschen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/services/api'
import { useAuthStore, type User } from '@/stores/auth'

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
const formRef = ref<any>(null)

const editingUser = ref<User | null>(null)
const selectedUser = ref<User | null>(null)
const newPassword = ref('')

const formData = reactive({
  email: '',
  full_name: '',
  password: '',
  role: 'VIEWER',
  is_active: true,
})

// Table headers
const headers = [
  { title: 'E-Mail', key: 'email', sortable: false },
  { title: 'Name', key: 'full_name', sortable: false },
  { title: 'Rolle', key: 'role', sortable: false, width: 120 },
  { title: 'Aktiv', key: 'is_active', sortable: false, width: 80 },
  { title: 'Letzter Login', key: 'last_login', sortable: false, width: 180 },
  { title: 'Aktionen', key: 'actions', sortable: false, width: 150 },
]

// Options
const roleOptions = [
  { title: 'Viewer', value: 'VIEWER' },
  { title: 'Editor', value: 'EDITOR' },
  { title: 'Admin', value: 'ADMIN' },
]

const activeOptions = [
  { title: 'Aktiv', value: true },
  { title: 'Inaktiv', value: false },
]

// Validation rules
const required = (v: any) => !!v || 'Pflichtfeld'
const emailRule = (v: string) => /.+@.+\..+/.test(v) || 'Ungültige E-Mail'
const minLength = (min: number) => (v: string) =>
  v.length >= min || `Mindestens ${min} Zeichen`

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
  const labels: Record<string, string> = {
    ADMIN: 'Admin',
    EDITOR: 'Editor',
    VIEWER: 'Viewer',
  }
  return labels[role] || role
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

// Debounce search
let searchTimeout: ReturnType<typeof setTimeout>
function debouncedFetch() {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => fetchUsers(), 300)
}

// API calls
async function fetchUsers() {
  loading.value = true
  try {
    const params: Record<string, any> = {
      page: page.value,
      per_page: perPage.value,
    }
    if (search.value) params.search = search.value
    if (roleFilter.value) params.role = roleFilter.value
    if (activeFilter.value !== null) params.is_active = activeFilter.value

    const response = await api.get('/api/admin/users', { params })
    users.value = response.data.items
    totalUsers.value = response.data.total
  } catch (error) {
    console.error('Failed to fetch users:', error)
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
      await api.put(`/api/admin/users/${editingUser.value.id}`, {
        email: formData.email,
        full_name: formData.full_name,
        role: formData.role,
        is_active: formData.is_active,
      })
    } else {
      await api.post('/api/admin/users', formData)
    }
    dialogOpen.value = false
    await fetchUsers()
  } catch (error: any) {
    console.error('Failed to save user:', error)
    alert(error.response?.data?.detail || 'Fehler beim Speichern')
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
    await api.post(`/api/admin/users/${selectedUser.value.id}/reset-password`, {
      new_password: newPassword.value,
    })
    passwordDialogOpen.value = false
  } catch (error: any) {
    console.error('Failed to reset password:', error)
    alert(error.response?.data?.detail || 'Fehler beim Zurücksetzen')
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
    await api.delete(`/api/admin/users/${selectedUser.value.id}`)
    deleteDialogOpen.value = false
    await fetchUsers()
  } catch (error: any) {
    console.error('Failed to delete user:', error)
    alert(error.response?.data?.detail || 'Fehler beim Löschen')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchUsers()
})
</script>
