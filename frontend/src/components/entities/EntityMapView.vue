<template>
  <div class="entity-map-container" :class="{ 'theme-dark': isDark }">
    <!-- Map Container -->
    <div ref="mapContainer" class="map-container"></div>

    <!-- Caeli tint overlay for dark mode (subtle green tint) -->
    <div v-if="isDark" class="map-tint-overlay"></div>

    <!-- Map Controls Overlay -->
    <div class="map-overlay map-overlay--top-left">
      <v-card class="pa-2" density="compact" elevation="2">
        <div class="d-flex align-center ga-2">
          <v-icon size="small" color="primary">mdi-map-marker-multiple</v-icon>
          <div class="text-caption">
            <strong>{{ totalWithCoords.toLocaleString() }}</strong>
            <span class="text-medium-emphasis">
              / {{ (totalWithCoords + totalWithoutCoords).toLocaleString() }}
            </span>
            {{ $t('entities.mapView.onMap') }}
          </div>
        </div>
        <!-- Geometry type breakdown -->
        <div v-if="polygonCount > 0 || pointCount > 0" class="d-flex ga-2 mt-1">
          <v-chip v-if="pointCount > 0" size="x-small" color="primary" variant="flat">
            <v-icon start size="x-small">mdi-map-marker</v-icon>
            {{ pointCount }}
          </v-chip>
          <v-chip v-if="polygonCount > 0" size="x-small" color="success" variant="flat">
            <v-icon start size="x-small">mdi-vector-polygon</v-icon>
            {{ polygonCount }}
          </v-chip>
        </div>
      </v-card>
    </div>

    <!-- Loading Overlay -->
    <div v-if="loading" class="map-overlay map-overlay--center">
      <v-card class="pa-4 text-center" elevation="4">
        <v-progress-circular indeterminate color="primary" size="40"></v-progress-circular>
        <div class="text-caption mt-2">{{ $t('entities.mapView.loading') }}</div>
      </v-card>
    </div>

    <!-- Legend -->
    <div class="map-overlay map-overlay--bottom-left">
      <v-card class="pa-2" density="compact" elevation="2">
        <!-- Cluster Legend (only if points exist) -->
        <div v-if="pointCount > 0">
          <div class="text-caption font-weight-medium mb-1">{{ $t('entities.mapView.clusterLegend') }}</div>
          <div class="d-flex align-center ga-3">
            <div class="d-flex align-center ga-1">
              <div class="cluster-dot cluster-dot--small"></div>
              <span class="text-caption">&lt; 100</span>
            </div>
            <div class="d-flex align-center ga-1">
              <div class="cluster-dot cluster-dot--medium"></div>
              <span class="text-caption">100-1000</span>
            </div>
            <div class="d-flex align-center ga-1">
              <div class="cluster-dot cluster-dot--large"></div>
              <span class="text-caption">&gt; 1000</span>
            </div>
          </div>
        </div>
        <!-- Polygon Legend (only if polygons exist) -->
        <div v-if="polygonCount > 0" :class="{ 'mt-2': pointCount > 0 }">
          <div class="text-caption font-weight-medium mb-1">{{ $t('entities.mapView.regions') }}</div>
          <div class="d-flex align-center ga-1">
            <div class="polygon-sample"></div>
            <span class="text-caption">{{ $t('entities.mapView.boundaries') }}</span>
          </div>
        </div>
      </v-card>
    </div>

    <!-- Entity Popup -->
    <v-card
      v-if="selectedEntity"
      class="entity-popup"
      :style="{ left: popupPosition.x + 'px', top: popupPosition.y + 'px' }"
      elevation="8"
      max-width="320"
    >
      <v-card-title class="d-flex align-center py-2">
        <v-icon :icon="selectedEntity.icon" :color="selectedEntity.color" class="mr-2" size="small"></v-icon>
        {{ selectedEntity.name }}
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" size="x-small" variant="text" @click="selectedEntity = null"></v-btn>
      </v-card-title>
      <v-card-text class="py-2">
        <div v-if="selectedEntity.entity_type_name" class="text-caption text-medium-emphasis mb-1">
          {{ selectedEntity.entity_type_name }}
        </div>
        <div v-if="selectedEntity.external_id" class="text-caption">
          <strong>ID:</strong> {{ selectedEntity.external_id }}
        </div>
        <div v-if="selectedEntity.admin_level_1 || selectedEntity.admin_level_2" class="text-caption">
          <strong>{{ $t('entities.location') }}:</strong>
          {{ [selectedEntity.admin_level_2, selectedEntity.admin_level_1, selectedEntity.country].filter(Boolean).join(', ') }}
        </div>
      </v-card-text>
      <v-card-actions class="py-1">
        <v-btn size="small" color="primary" variant="tonal" @click="navigateToEntity(selectedEntity)">
          <v-icon start size="small">mdi-eye</v-icon>
          {{ $t('common.details') }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { entityApi } from '@/services/api'

interface Props {
  entityTypeSlug?: string
  country?: string
  adminLevel1?: string
  adminLevel2?: string
  search?: string
}

const props = defineProps<Props>()

const router = useRouter()
const theme = useTheme()

// Dark mode detection
const isDark = computed(() => theme.global.current.value.dark)

// State
const mapContainer = ref<HTMLElement | null>(null)
const map = ref<maplibregl.Map | null>(null)
const loading = ref(true)
const totalWithCoords = ref(0)
const totalWithoutCoords = ref(0)
const pointCount = ref(0)
const polygonCount = ref(0)
const selectedEntity = ref<any>(null)
const popupPosition = ref({ x: 0, y: 0 })

// Map Styles - CartoDB free styles (MapLibre-compatible)
const MAP_STYLES = {
  light: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
}

const mapStyle = computed(() => isDark.value ? MAP_STYLES.dark : MAP_STYLES.light)

// Caeli-themed cluster colors
const CLUSTER_COLORS = {
  light: {
    small: '#2E7D32',    // success green
    medium: '#113634',   // primary dark green
    large: '#5c6bc0',    // tertiary purple
    text: '#ffffff',
    stroke: '#ffffff',
  },
  dark: {
    // Bright, vibrant colors that pop on dark background
    small: '#81C784',    // bright green (success-light)
    medium: '#deeec6',   // Caeli primary light green
    large: '#B39DDB',    // light purple
    text: '#113634',     // dark text on light bubbles
    stroke: '#ffffff',
  },
}

const clusterColors = computed(() => isDark.value ? CLUSTER_COLORS.dark : CLUSTER_COLORS.light)

// Initialize map
async function initMap() {
  if (!mapContainer.value) return

  map.value = new maplibregl.Map({
    container: mapContainer.value,
    style: mapStyle.value,
    center: [10.4515, 51.1657], // Germany center
    zoom: 5,
    attributionControl: true,
  })

  // Add navigation controls
  map.value.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.value.addControl(new maplibregl.ScaleControl(), 'bottom-right')

  // Wait for map to load
  map.value.on('load', async () => {
    await loadGeoData()
    setupMapInteractions()
  })
}

// Helper to get centroid of polygon for popup positioning
function getPolygonCentroid(geometry: any): [number, number] {
  if (geometry.type === 'Polygon') {
    const coords = geometry.coordinates[0]
    let x = 0, y = 0
    for (const [lng, lat] of coords) {
      x += lng
      y += lat
    }
    return [x / coords.length, y / coords.length]
  } else if (geometry.type === 'MultiPolygon') {
    // Use first polygon's centroid
    const coords = geometry.coordinates[0][0]
    let x = 0, y = 0
    for (const [lng, lat] of coords) {
      x += lng
      y += lat
    }
    return [x / coords.length, y / coords.length]
  }
  return [0, 0]
}

// Helper to extend bounds with any geometry type
function extendBoundsWithGeometry(bounds: maplibregl.LngLatBounds, geometry: any) {
  if (geometry.type === 'Point') {
    bounds.extend(geometry.coordinates as [number, number])
  } else if (geometry.type === 'Polygon') {
    for (const ring of geometry.coordinates) {
      for (const coord of ring) {
        bounds.extend(coord as [number, number])
      }
    }
  } else if (geometry.type === 'MultiPolygon') {
    for (const polygon of geometry.coordinates) {
      for (const ring of polygon) {
        for (const coord of ring) {
          bounds.extend(coord as [number, number])
        }
      }
    }
  } else if (geometry.type === 'LineString') {
    for (const coord of geometry.coordinates) {
      bounds.extend(coord as [number, number])
    }
  }
}

// Load GeoJSON data from API
async function loadGeoData() {
  if (!map.value) return

  loading.value = true
  try {
    const response = await entityApi.getEntitiesGeoJSON({
      entity_type_slug: props.entityTypeSlug,
      country: props.country,
      admin_level_1: props.adminLevel1,
      admin_level_2: props.adminLevel2,
      search: props.search,
    })

    const geojson = response.data
    totalWithCoords.value = geojson.total_with_coords
    totalWithoutCoords.value = geojson.total_without_coords

    // Separate points from polygons
    const points: any[] = []
    const polygons: any[] = []

    for (const feature of geojson.features) {
      const geomType = feature.geometry?.type
      if (geomType === 'Point') {
        points.push(feature)
      } else if (['Polygon', 'MultiPolygon', 'LineString', 'MultiLineString'].includes(geomType)) {
        polygons.push(feature)
      }
    }

    pointCount.value = points.length
    polygonCount.value = polygons.length

    // Remove existing sources and layers
    const layersToRemove = ['clusters', 'cluster-count', 'unclustered-point', 'polygon-fill', 'polygon-line', 'polygon-highlight']
    const sourcesToRemove = ['entities-points', 'entities-polygons']

    for (const layer of layersToRemove) {
      if (map.value.getLayer(layer)) {
        map.value.removeLayer(layer)
      }
    }
    for (const source of sourcesToRemove) {
      if (map.value.getSource(source)) {
        map.value.removeSource(source)
      }
    }

    // Add Points source with clustering (if we have points)
    if (points.length > 0) {
      map.value.addSource('entities-points', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: points },
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 50,
      })

      // Cluster circles layer - using Caeli theme colors
      const colors = clusterColors.value
      map.value.addLayer({
        id: 'clusters',
        type: 'circle',
        source: 'entities-points',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': [
            'step',
            ['get', 'point_count'],
            colors.small,   // < 100
            100,
            colors.medium,  // 100-1000
            1000,
            colors.large,   // > 1000
          ],
          'circle-radius': [
            'step',
            ['get', 'point_count'],
            18,   // Small clusters
            100,
            26,   // Medium clusters
            1000,
            34,   // Large clusters
          ],
          'circle-stroke-width': 3,
          'circle-stroke-color': colors.stroke,
          'circle-opacity': 0.9,
        },
      })

      // Cluster count labels
      map.value.addLayer({
        id: 'cluster-count',
        type: 'symbol',
        source: 'entities-points',
        filter: ['has', 'point_count'],
        layout: {
          'text-field': ['get', 'point_count_abbreviated'],
          'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
          'text-size': 13,
        },
        paint: {
          'text-color': colors.text,
        },
      })

      // Individual points layer - styled to match
      map.value.addLayer({
        id: 'unclustered-point',
        type: 'circle',
        source: 'entities-points',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-color': colors.small,
          'circle-radius': 7,
          'circle-stroke-width': 2,
          'circle-stroke-color': colors.stroke,
          'circle-opacity': 0.9,
        },
      })
    }

    // Add Polygons source (no clustering)
    if (polygons.length > 0) {
      map.value.addSource('entities-polygons', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: polygons },
      })

      // Polygon colors based on theme
      const polygonColor = isDark.value ? '#81C784' : '#2E7D32'
      const highlightColor = isDark.value ? '#deeec6' : '#113634'

      // Polygon fill layer
      map.value.addLayer({
        id: 'polygon-fill',
        type: 'fill',
        source: 'entities-polygons',
        paint: {
          'fill-color': ['coalesce', ['get', 'color'], polygonColor],
          'fill-opacity': isDark.value ? 0.25 : 0.2,
        },
      })

      // Polygon border layer
      map.value.addLayer({
        id: 'polygon-line',
        type: 'line',
        source: 'entities-polygons',
        paint: {
          'line-color': ['coalesce', ['get', 'color'], polygonColor],
          'line-width': 2,
        },
      })

      // Polygon highlight layer (for hover)
      map.value.addLayer({
        id: 'polygon-highlight',
        type: 'line',
        source: 'entities-polygons',
        paint: {
          'line-color': highlightColor,
          'line-width': 3,
        },
        filter: ['==', ['get', 'id'], ''],
      })
    }

    // Fit bounds to all data
    if (geojson.features.length > 0) {
      const bounds = new maplibregl.LngLatBounds()
      geojson.features.forEach((feature: any) => {
        extendBoundsWithGeometry(bounds, feature.geometry)
      })
      map.value.fitBounds(bounds, { padding: 50, maxZoom: 10 })
    }
  } catch (error) {
    console.error('Failed to load GeoJSON data:', error)
  } finally {
    loading.value = false
  }
}

// Setup map click interactions
function setupMapInteractions() {
  if (!map.value) return

  // Click on cluster to zoom in
  map.value.on('click', 'clusters', async (e) => {
    const features = map.value!.queryRenderedFeatures(e.point, { layers: ['clusters'] })
    if (!features.length) return

    const clusterId = features[0].properties?.cluster_id
    const source = map.value!.getSource('entities-points') as maplibregl.GeoJSONSource

    const zoom = await source.getClusterExpansionZoom(clusterId)
    map.value!.easeTo({
      center: (features[0].geometry as any).coordinates,
      zoom: zoom,
    })
  })

  // Click on individual point to show popup
  map.value.on('click', 'unclustered-point', (e) => {
    if (!e.features?.length) return
    showEntityPopup(e.features[0], e.point)
  })

  // Click on polygon to show popup
  map.value.on('click', 'polygon-fill', (e) => {
    if (!e.features?.length) return
    showEntityPopup(e.features[0], e.point)
  })

  // Hover effects for clusters
  map.value.on('mouseenter', 'clusters', () => {
    if (map.value) map.value.getCanvas().style.cursor = 'pointer'
  })
  map.value.on('mouseleave', 'clusters', () => {
    if (map.value) map.value.getCanvas().style.cursor = ''
  })

  // Hover effects for points
  map.value.on('mouseenter', 'unclustered-point', () => {
    if (map.value) map.value.getCanvas().style.cursor = 'pointer'
  })
  map.value.on('mouseleave', 'unclustered-point', () => {
    if (map.value) map.value.getCanvas().style.cursor = ''
  })

  // Hover effects for polygons
  map.value.on('mouseenter', 'polygon-fill', (e) => {
    if (map.value) {
      map.value.getCanvas().style.cursor = 'pointer'
      // Highlight the polygon
      if (e.features?.length) {
        map.value.setFilter('polygon-highlight', ['==', ['get', 'id'], e.features[0].properties?.id || ''])
      }
    }
  })
  map.value.on('mouseleave', 'polygon-fill', () => {
    if (map.value) {
      map.value.getCanvas().style.cursor = ''
      map.value.setFilter('polygon-highlight', ['==', ['get', 'id'], ''])
    }
  })

  // Close popup when clicking elsewhere
  map.value.on('click', (e) => {
    const layers = ['unclustered-point', 'clusters', 'polygon-fill'].filter(l => map.value?.getLayer(l))
    const features = map.value!.queryRenderedFeatures(e.point, { layers })
    if (!features.length) {
      selectedEntity.value = null
    }
  })
}

// Show entity popup
function showEntityPopup(feature: any, point: maplibregl.Point) {
  selectedEntity.value = {
    id: feature.properties?.id,
    name: feature.properties?.name,
    slug: feature.properties?.slug,
    external_id: feature.properties?.external_id,
    entity_type_slug: feature.properties?.entity_type_slug,
    entity_type_name: feature.properties?.entity_type_name,
    icon: feature.properties?.icon || 'mdi-map-marker',
    color: feature.properties?.color || '#1976D2',
    country: feature.properties?.country,
    admin_level_1: feature.properties?.admin_level_1,
    admin_level_2: feature.properties?.admin_level_2,
  }

  // Position popup
  popupPosition.value = {
    x: Math.min(point.x + 10, window.innerWidth - 340),
    y: Math.max(point.y - 100, 10),
  }
}

// Navigate to entity detail
function navigateToEntity(entity: any) {
  if (entity.entity_type_slug && entity.slug) {
    router.push({
      name: 'entity-detail',
      params: {
        typeSlug: entity.entity_type_slug,
        entitySlug: entity.slug,
      },
    })
  }
}

// Watch for filter changes
watch(
  () => [props.entityTypeSlug, props.country, props.adminLevel1, props.adminLevel2, props.search],
  async () => {
    if (map.value && map.value.loaded()) {
      await loadGeoData()
    }
  }
)

// Watch for theme changes and update map style
watch(isDark, async () => {
  if (map.value) {
    // Store current view state
    const center = map.value.getCenter()
    const zoom = map.value.getZoom()
    const bearing = map.value.getBearing()
    const pitch = map.value.getPitch()

    // Set new style (this removes all layers/sources)
    map.value.setStyle(mapStyle.value)

    // Wait for new style to load, then restore data and view
    map.value.once('style.load', async () => {
      // Restore view state
      map.value!.setCenter(center)
      map.value!.setZoom(zoom)
      map.value!.setBearing(bearing)
      map.value!.setPitch(pitch)

      // Reload geo data (re-adds sources and layers)
      await loadGeoData()
    })
  }
})

// Lifecycle
onMounted(async () => {
  await nextTick()
  await initMap()
})

onUnmounted(() => {
  if (map.value) {
    map.value.remove()
    map.value = null
  }
})
</script>

<style scoped>
.entity-map-container {
  position: relative;
  width: 100%;
  height: 600px;
  border-radius: 8px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
}

/* Caeli green tint overlay for dark mode */
.map-tint-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    135deg,
    rgba(17, 54, 52, 0.15) 0%,
    rgba(13, 31, 30, 0.1) 100%
  );
  pointer-events: none;
  z-index: 0;
}

.map-overlay {
  position: absolute;
  z-index: 1;
}

.map-overlay--top-left {
  top: 10px;
  left: 10px;
}

.map-overlay--bottom-left {
  bottom: 30px;
  left: 10px;
}

.map-overlay--center {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.entity-popup {
  position: absolute;
  z-index: 2;
  pointer-events: auto;
}

.cluster-dot {
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.cluster-dot--small {
  width: 14px;
  height: 14px;
  background-color: #2E7D32; /* success green */
}

.cluster-dot--medium {
  width: 18px;
  height: 18px;
  background-color: #113634; /* primary dark green */
}

.cluster-dot--large {
  width: 22px;
  height: 22px;
  background-color: #5c6bc0; /* tertiary purple */
}

.polygon-sample {
  width: 20px;
  height: 14px;
  background-color: rgba(46, 125, 50, 0.2);
  border: 2px solid #2E7D32;
  border-radius: 2px;
}

/* MapLibre GL overrides - Light mode */
:deep(.maplibregl-ctrl-attrib) {
  font-size: 10px;
  background: rgba(255, 255, 255, 0.8);
}

:deep(.maplibregl-ctrl-group) {
  border-radius: 4px;
  overflow: hidden;
}

:deep(.maplibregl-ctrl-group button) {
  width: 32px;
  height: 32px;
}

/* Dark mode adjustments - Caeli theme colors */
.entity-map-container.theme-dark {
  /* Legend dots with dark mode Caeli colors */
  .cluster-dot {
    border-color: rgba(17, 54, 52, 0.6);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  }

  .cluster-dot--small {
    background-color: #a8d5a2; /* light success */
  }

  .cluster-dot--medium {
    background-color: #deeec6; /* primary light green */
  }

  .cluster-dot--large {
    background-color: #92a0ff; /* light tertiary */
  }

  .polygon-sample {
    background-color: rgba(168, 213, 162, 0.25);
    border-color: #a8d5a2;
  }

  /* MapLibre controls - matching Caeli dark surface */
  :deep(.maplibregl-ctrl-attrib) {
    background: rgba(20, 41, 40, 0.9);
    color: rgba(222, 238, 198, 0.8);
  }

  :deep(.maplibregl-ctrl-attrib a) {
    color: rgba(222, 238, 198, 0.9);
  }

  :deep(.maplibregl-ctrl-group) {
    background: #142928;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  :deep(.maplibregl-ctrl-group button) {
    background-color: #142928;
    border-color: rgba(222, 238, 198, 0.1);
  }

  :deep(.maplibregl-ctrl-group button:hover) {
    background-color: #1d3a38;
  }

  :deep(.maplibregl-ctrl-group button + button) {
    border-top-color: rgba(222, 238, 198, 0.1);
  }

  :deep(.maplibregl-ctrl-icon) {
    filter: invert(0.85) sepia(0.2) hue-rotate(90deg);
  }
}
</style>
