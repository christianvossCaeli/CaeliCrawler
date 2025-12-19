<template>
  <v-expansion-panels variant="accordion">
    <v-expansion-panel v-for="group in apiGroups" :key="group.title">
      <v-expansion-panel-title>
        <v-icon :color="group.color" class="mr-2">{{ group.icon }}</v-icon>
        {{ group.title }}
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <v-alert v-if="group.note" type="info" variant="tonal" class="mb-3">
          {{ group.note }}
        </v-alert>
        <v-table density="compact">
          <thead>
            <tr>
              <th>Methode</th>
              <th>Endpunkt</th>
              <th>Beschreibung</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="endpoint in group.endpoints" :key="endpoint.path">
              <td>
                <v-chip size="x-small" :color="methodColors[endpoint.method]">
                  {{ endpoint.method }}
                </v-chip>
              </td>
              <td><code>{{ endpoint.path }}</code></td>
              <td>{{ endpoint.description }}</td>
            </tr>
          </tbody>
        </v-table>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { apiGroups, methodColors } from './helpSections'
</script>
