<template>
  <div class="page-header mb-6">
    <div class="header-content d-flex align-center">
      <v-avatar
        :color="avatarColor"
        :size="avatarSize"
        class="mr-4 header-avatar"
      >
        <v-icon :size="iconSize">{{ icon }}</v-icon>
      </v-avatar>
      <div class="header-text">
        <h1 class="text-h4 font-weight-bold">
          {{ title }}
          <span v-if="count !== undefined" class="text-medium-emphasis font-weight-regular">
            ({{ typeof count === 'number' ? count.toLocaleString() : count }})
          </span>
        </h1>
        <p v-if="subtitle" class="text-body-2 text-medium-emphasis mb-0">
          {{ subtitle }}
        </p>
      </div>
    </div>
    <div v-if="$slots.actions" class="header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  subtitle?: string
  icon: string
  count?: number | string
  avatarColor?: string
  avatarSize?: number | string
  iconSize?: number | string
}>(), {
  avatarColor: 'primary',
  avatarSize: 56,
  iconSize: 32
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px;
  background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.06) 0%, rgba(var(--v-theme-primary), 0.02) 100%);
  border-radius: 16px;
  border: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.header-avatar {
  box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.2);
}

/* Icon color that works in both light and dark mode */
.header-avatar :deep(.v-icon) {
  color: rgb(var(--v-theme-on-primary)) !important;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-text {
  min-width: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .header-content {
    flex-direction: column;
  }

  .header-avatar {
    margin-right: 0 !important;
    margin-bottom: 12px;
  }

  .header-actions {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }
}
</style>
