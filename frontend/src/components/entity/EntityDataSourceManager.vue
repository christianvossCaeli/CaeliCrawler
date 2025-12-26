<template>
  <div>
    <!-- Edit Data Source Dialog -->
    <v-dialog v-model="editDialogVisible" max-width="800" persistent scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4 bg-primary">
          <v-avatar color="primary-darken-1" size="40" class="mr-3">
            <v-icon color="on-primary">mdi-database-edit</v-icon>
          </v-avatar>
          <div>
            <div class="text-h6">{{ t('entityDetail.editSourceTitle') }}</div>
            <div v-if="editingSource" class="text-caption opacity-80">{{ editingSource.name }}</div>
          </div>
        </v-card-title>
        <v-card-text class="pa-4">
          <v-form ref="sourceForm" v-model="formValid">
            <v-text-field
              v-model="formData.name"
              :label="t('sources.form.name')"
              :rules="[(v: string) => !!v || t('sources.validation.nameRequired')]"
              variant="outlined"
              prepend-inner-icon="mdi-database"
              class="mb-3"
            ></v-text-field>

            <v-text-field
              v-model="formData.base_url"
              :label="t('sources.form.baseUrl')"
              :rules="[(v: string) => !!v || t('sources.validation.urlRequired')]"
              variant="outlined"
              prepend-inner-icon="mdi-link"
              class="mb-3"
            ></v-text-field>

            <v-row>
              <v-col cols="6">
                <v-number-input
                  v-model="formData.crawl_config.max_depth"
                  :label="t('sources.form.maxDepth')"
                  :min="1"
                  :max="10"
                  variant="outlined"
                  control-variant="stacked"
                ></v-number-input>
              </v-col>
              <v-col cols="6">
                <v-number-input
                  v-model="formData.crawl_config.max_pages"
                  :label="t('sources.form.maxPages')"
                  :min="1"
                  :max="10000"
                  variant="outlined"
                  control-variant="stacked"
                ></v-number-input>
              </v-col>
            </v-row>

            <v-switch
              v-model="formData.crawl_config.render_javascript"
              :label="t('sources.form.renderJs')"
              color="primary"
              class="mt-2"
            ></v-switch>
          </v-form>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-btn variant="tonal" @click="closeEditDialog">{{ t('common.cancel') }}</v-btn>
          <v-spacer></v-spacer>
          <v-btn
            variant="tonal"
            color="primary"
            :disabled="!formValid"
            :loading="saving"
            @click="saveSource"
          >
            <v-icon start>mdi-check</v-icon>
            {{ t('common.save') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Source Confirmation -->
    <v-dialog v-model="deleteDialogVisible" max-width="450">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon color="error" class="mr-2">mdi-alert</v-icon>
          {{ t('entityDetail.deleteSourceTitle') }}
        </v-card-title>
        <v-card-text>
          <p>{{ t('entityDetail.deleteSourceConfirm') }}</p>
          <p v-if="sourceToDelete" class="font-weight-medium mt-2">{{ sourceToDelete.name }}</p>
          <v-alert type="warning" variant="tonal" density="compact" class="mt-3">
            {{ t('entityDetail.deleteSourceWarning') }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="tonal" @click="closeDeleteDialog">{{ t('common.cancel') }}</v-btn>
          <v-btn variant="tonal" color="error" :loading="deleting" @click="deleteSource">
            {{ t('common.delete') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Unlink Source Confirmation -->
    <ConfirmDialog
      v-model="unlinkDialogVisible"
      :title="t('entityDetail.unlinkSourceTitle')"
      :message="t('entityDetail.unlinkSourceConfirm')"
      :subtitle="sourceToUnlink?.name"
      icon="mdi-link-off"
      icon-color="warning"
      confirm-color="warning"
      :confirm-text="t('entityDetail.unlink')"
      :loading="unlinking"
      @confirm="unlinkSource"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/services/api'
import { useSnackbar } from '@/composables/useSnackbar'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { useLogger } from '@/composables/useLogger'

const props = withDefaults(defineProps<Props>(), {
  showEditDialog: false,
  showDeleteDialog: false,
  showUnlinkDialog: false,
  sourceToEdit: null,
  sourceToDelete: null,
  sourceToUnlink: null,
})

const emit = defineEmits<{
  (e: 'update:showEditDialog', value: boolean): void
  (e: 'update:showDeleteDialog', value: boolean): void
  (e: 'update:showUnlinkDialog', value: boolean): void
  (e: 'source-updated'): void
  (e: 'source-deleted'): void
  (e: 'source-unlinked'): void
}>()

const logger = useLogger('EntityDataSourceManager')

interface DataSource {
  id: string
  name: string
  base_url: string
  status: string
  source_type?: string
  is_direct_link?: boolean
  document_count?: number
  last_crawl?: string
  hasRunningJob?: boolean
  crawl_config?: {
    max_depth: number
    max_pages: number
    render_javascript: boolean
  }
  extra_data?: {
    entity_id?: string
    entity_ids?: string[]
  }
}

interface Props {
  entityId: string
  showEditDialog?: boolean
  showDeleteDialog?: boolean
  showUnlinkDialog?: boolean
  sourceToEdit?: DataSource | null
  sourceToDelete?: DataSource | null
  sourceToUnlink?: DataSource | null
}

const { t } = useI18n()
const { showSuccess, showError } = useSnackbar()

// Local state
const editDialogVisible = computed({
  get: () => props.showEditDialog,
  set: (value) => emit('update:showEditDialog', value),
})

const deleteDialogVisible = computed({
  get: () => props.showDeleteDialog,
  set: (value) => emit('update:showDeleteDialog', value),
})

const unlinkDialogVisible = computed({
  get: () => props.showUnlinkDialog,
  set: (value) => emit('update:showUnlinkDialog', value),
})

const editingSource = computed(() => props.sourceToEdit)

const formValid = ref(false)
const saving = ref(false)
const deleting = ref(false)
const unlinking = ref(false)

const formData = ref({
  name: '',
  base_url: '',
  crawl_config: {
    max_depth: 3,
    max_pages: 100,
    render_javascript: false,
  },
})

// Watch for source changes and populate form
watch(() => props.sourceToEdit, (source) => {
  if (source) {
    formData.value = {
      name: source.name || '',
      base_url: source.base_url || '',
      crawl_config: {
        max_depth: source.crawl_config?.max_depth || 3,
        max_pages: source.crawl_config?.max_pages || 100,
        render_javascript: source.crawl_config?.render_javascript || false,
      },
    }
  }
}, { immediate: true })

// Methods
function closeEditDialog() {
  editDialogVisible.value = false
  formData.value = {
    name: '',
    base_url: '',
    crawl_config: {
      max_depth: 3,
      max_pages: 100,
      render_javascript: false,
    },
  }
}

function closeDeleteDialog() {
  deleteDialogVisible.value = false
}

async function saveSource() {
  if (!editingSource.value) return

  saving.value = true
  try {
    await adminApi.updateSource(editingSource.value.id, {
      name: formData.value.name,
      base_url: formData.value.base_url,
      crawl_config: {
        ...editingSource.value.crawl_config,
        ...formData.value.crawl_config,
      },
    })

    showSuccess(t('entityDetail.messages.sourceUpdateSuccess'))
    closeEditDialog()
    emit('source-updated')
  } catch (e) {
    logger.error('Failed to update source:', e)
    showError(t('entityDetail.messages.sourceUpdateError'))
  } finally {
    saving.value = false
  }
}

async function deleteSource() {
  if (!props.sourceToDelete) return

  deleting.value = true
  try {
    await adminApi.deleteSource(props.sourceToDelete.id)

    showSuccess(t('entityDetail.messages.sourceDeleteSuccess'))
    closeDeleteDialog()
    emit('source-deleted')
  } catch (e) {
    logger.error('Failed to delete source:', e)
    showError(t('entityDetail.messages.sourceDeleteError'))
  } finally {
    deleting.value = false
  }
}

async function unlinkSource() {
  if (!props.sourceToUnlink) return

  unlinking.value = true
  try {
    // Remove this entity from entity_ids array (N:M)
    const currentExtraData = props.sourceToUnlink.extra_data || {}

    // Support both legacy entity_id and new entity_ids
    let entityIds = currentExtraData.entity_ids ||
      (currentExtraData.entity_id ? [currentExtraData.entity_id] : [])

    // Remove current entity from the array
    entityIds = entityIds.filter((id: string) => id !== props.entityId)

    // Clean up legacy field and update
    const { entity_id: _entity_id, ...restExtraData } = currentExtraData

    await adminApi.updateSource(props.sourceToUnlink.id, {
      extra_data: {
        ...restExtraData,
        entity_ids: entityIds,
      },
    })

    showSuccess(t('entityDetail.messages.sourceUnlinkSuccess'))
    unlinkDialogVisible.value = false
    emit('source-unlinked')
  } catch (e) {
    logger.error('Failed to unlink source:', e)
    showError(t('entityDetail.messages.sourceUnlinkError'))
  } finally {
    unlinking.value = false
  }
}
</script>
