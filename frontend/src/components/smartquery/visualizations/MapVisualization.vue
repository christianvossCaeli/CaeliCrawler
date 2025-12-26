<template>
  <div
    class="map-visualization"
    :class="{ 'theme-dark': isDark }"
    role="region"
    :aria-label="t('visualization.map.ariaLabel')"
  >
    <!-- Map Container -->
    <div
      ref="mapContainer"
      class="map-container"
      :aria-label="t('visualization.map.interactiveMap')"
    ></div>

    <!-- Caeli tint overlay for dark mode -->
    <div v-if="isDark" class="map-tint-overlay"></div>

    <!-- Map Statistics Overlay -->
    <div class="map-overlay map-overlay--top-left">
      <v-card class="pa-2" density="compact" elevation="2">
        <div class="d-flex align-center ga-2">
          <v-icon size="small" color="primary">mdi-map-marker-multiple</v-icon>
          <div class="text-caption">
            <strong>{{ totalFeatures.toLocaleString() }}</strong>
            {{ t('visualization.map.featuresOnMap') }}
          </div>
        </div>
        <!-- Geometry type breakdown (only show when both types exist) -->
        <div v-if="polygonCount > 0 && pointCount > 0" class="d-flex ga-2 mt-1">
          <v-chip size="x-small" color="primary" variant="flat">
            <v-icon start size="x-small">mdi-map-marker</v-icon>
            {{ pointCount }}
          </v-chip>
          <v-chip size="x-small" color="success" variant="flat">
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
        <div class="text-caption mt-2">{{ t('visualization.map.loading') }}</div>
      </v-card>
    </div>

    <!-- Legend -->
    <div class="map-overlay map-overlay--bottom-left">
      <v-card class="pa-2" density="compact" elevation="2">
        <!-- Cluster Legend (only if points exist) -->
        <div v-if="pointCount > 0">
          <div class="text-caption font-weight-medium mb-1">{{ t('visualization.map.clusterLegend') }}</div>
          <div class="d-flex align-center ga-3">
            <div class="d-flex align-center ga-1">
              <div class="cluster-dot cluster-dot--small"></div>
              <span class="text-caption">&lt; 10</span>
            </div>
            <div class="d-flex align-center ga-1">
              <div class="cluster-dot cluster-dot--medium"></div>
              <span class="text-caption">10-50</span>
            </div>
            <div class="d-flex align-center ga-1">
              <div class="cluster-dot cluster-dot--large"></div>
              <span class="text-caption">&gt; 50</span>
            </div>
          </div>
        </div>
        <!-- Polygon Legend (only if polygons exist) -->
        <div v-if="polygonCount > 0" :class="{ 'mt-2': pointCount > 0 }">
          <div class="text-caption font-weight-medium mb-1">{{ t('visualization.map.regions') }}</div>
          <div class="d-flex align-center ga-1">
            <div class="polygon-sample"></div>
            <span class="text-caption">{{ t('visualization.map.boundaries') }}</span>
          </div>
        </div>
      </v-card>
    </div>

    <!-- Entity Popup -->
    <v-card
      v-if="selectedFeature"
      class="entity-popup"
      :style="popupStyle"
      elevation="8"
      max-width="320"
    >
      <v-card-title class="d-flex align-center py-2">
        <v-icon :icon="selectedFeature.icon || 'mdi-map-marker'" :color="selectedFeature.color || 'primary'" class="mr-2" size="small"></v-icon>
        <span class="text-truncate" style="max-width: 200px;">{{ selectedFeature.name }}</span>
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" size="x-small" variant="text" @click="selectedFeature = null"></v-btn>
      </v-card-title>
      <v-card-text class="py-2 popup-content">
        <div v-if="selectedFeature.entity_type" class="text-caption text-medium-emphasis mb-1">
          {{ selectedFeature.entity_type }}
        </div>
        <div v-for="(value, key) in limitedAttributes" :key="key" class="text-caption">
          <strong>{{ formatAttributeKey(String(key)) }}:</strong> {{ formatAttributeValue(value) }}
        </div>
        <div v-if="hasMoreAttributes" class="text-caption text-medium-emphasis mt-1">
          +{{ Object.keys(selectedFeature.attributes).length - maxAttributesInPopup }} {{ t('common.more') }}
        </div>
      </v-card-text>
      <v-card-actions v-if="selectedFeature.entity_id" class="py-1">
        <v-btn size="small" color="primary" variant="tonal" @click="navigateToEntity(selectedFeature)">
          <v-icon start size="small">mdi-eye</v-icon>
          {{ t('common.details') }}
        </v-btn>
      </v-card-actions>
    </v-card>

    <!-- No Data Message -->
    <div v-if="!loading && totalFeatures === 0" class="map-overlay map-overlay--center">
      <v-card class="pa-4 text-center" elevation="4">
        <v-icon size="48" color="grey">mdi-map-marker-off</v-icon>
        <div class="text-body-2 mt-2">{{ t('visualization.map.noGeoData') }}</div>
      </v-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from 'vuetify'
import { useI18n } from 'vue-i18n'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { VisualizationConfig } from './types'
import { useLogger } from '@/composables/useLogger'

// =============================================================================
// Types
// =============================================================================

interface MapDataItem {
  entity_id?: string
  entity_name?: string
  name?: string
  entity_type?: string
  latitude?: number
  longitude?: number
  geometry?: unknown
  coordinates?: {
    lat?: number
    lon?: number
  }
  facets?: Record<string, unknown>
  icon?: string
  color?: string
  [key: string]: unknown
}

interface SelectedFeatureInfo {
  name: string
  entity_id?: string
  entity_type?: string
  icon?: string
  color?: string
  attributes: Record<string, unknown>
}

interface PopupPosition {
  x: number
  y: number
}

const props = defineProps<{
  data: MapDataItem[]
  config?: VisualizationConfig
}>()

const logger = useLogger('MapVisualization')

// =============================================================================
// Composables & Props
// =============================================================================

const { t } = useI18n()
const router = useRouter()
const theme = useTheme()

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_CENTER: [number, number] = [10.4515, 51.1657] // Germany center
const DEFAULT_ZOOM = 5
const FIT_BOUNDS_PADDING = 50
const MAX_FIT_ZOOM = 12
const MAX_ATTRIBUTES_IN_POPUP = 6 // Limit attributes to prevent overflow

// =============================================================================
// Reactive State
// =============================================================================

// Dark mode detection
const isDark = computed(() => theme.global.current.value.dark)

// Map refs
const mapContainer = ref<HTMLElement | null>(null)
const map = ref<maplibregl.Map | null>(null)
const resizeObserver = ref<ResizeObserver | null>(null)

// Loading and stats
const loading = ref(true)
const totalFeatures = ref(0)
const pointCount = ref(0)
const polygonCount = ref(0)

// Feature selection (properly typed)
const selectedFeature = ref<SelectedFeatureInfo | null>(null)
const popupPosition = ref<PopupPosition>({ x: 0, y: 0 })

// Map Styles - CartoDB free styles
const MAP_STYLES = {
  light: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
}

const mapStyle = computed(() => isDark.value ? MAP_STYLES.dark : MAP_STYLES.light)

// Popup computed properties
const maxAttributesInPopup = MAX_ATTRIBUTES_IN_POPUP

const limitedAttributes = computed(() => {
  if (!selectedFeature.value?.attributes) return {}
  const entries = Object.entries(selectedFeature.value.attributes)
  return Object.fromEntries(entries.slice(0, MAX_ATTRIBUTES_IN_POPUP))
})

const hasMoreAttributes = computed(() => {
  if (!selectedFeature.value?.attributes) return false
  return Object.keys(selectedFeature.value.attributes).length > MAX_ATTRIBUTES_IN_POPUP
})

const popupStyle = computed(() => {
  const containerWidth = mapContainer.value?.clientWidth || 500
  const containerHeight = mapContainer.value?.clientHeight || 400
  const popupWidth = 320
  const popupMaxHeight = 250

  let x = popupPosition.value.x + 10
  let y = popupPosition.value.y - 10

  // Prevent overflow on right
  if (x + popupWidth > containerWidth) {
    x = popupPosition.value.x - popupWidth - 10
  }
  // Prevent overflow on left
  if (x < 0) {
    x = 10
  }
  // Prevent overflow on bottom
  if (y + popupMaxHeight > containerHeight) {
    y = containerHeight - popupMaxHeight - 10
  }
  // Prevent overflow on top
  if (y < 10) {
    y = 10
  }

  return {
    left: x + 'px',
    top: y + 'px',
    maxHeight: popupMaxHeight + 'px',
  }
})

// Caeli-themed cluster colors
const CLUSTER_COLORS = {
  light: {
    small: '#2E7D32',
    medium: '#113634',
    large: '#5c6bc0',
    text: '#ffffff',
    stroke: '#ffffff',
  },
  dark: {
    small: '#81C784',
    medium: '#deeec6',
    large: '#B39DDB',
    text: '#113634',
    stroke: '#ffffff',
  },
}

const clusterColors = computed(() => isDark.value ? CLUSTER_COLORS.dark : CLUSTER_COLORS.light)

// Convert Smart Query data to GeoJSON
function convertToGeoJSON(data: Record<string, unknown>[]): GeoJSON.FeatureCollection {
  const features: GeoJSON.Feature[] = []

  for (const item of data) {
    let geometry: GeoJSON.Geometry | null = null

    // Type guards for item properties
    const lat = typeof item.latitude === 'number' ? item.latitude : null
    const lon = typeof item.longitude === 'number' ? item.longitude : null
    const coords = item.coordinates as { lat?: number; lon?: number } | undefined

    // Check for geometry field (complex shapes)
    if (item.geometry && typeof item.geometry === 'object') {
      geometry = item.geometry as GeoJSON.Geometry
    }
    // Check for lat/lon (simple points)
    else if (lat != null && lon != null) {
      geometry = {
        type: 'Point',
        coordinates: [lon, lat],
      }
    }
    // Check for nested coordinates
    else if (coords?.lat != null && coords?.lon != null) {
      geometry = {
        type: 'Point',
        coordinates: [coords.lon, coords.lat],
      }
    }
    // Check for facets with geo data
    else if (item.facets) {
      const geoFacet = Object.values(item.facets).find(
        (f: unknown) => (f as { latitude?: number; longitude?: number })?.latitude != null && (f as { latitude?: number; longitude?: number })?.longitude != null
      ) as { latitude: number; longitude: number } | undefined
      if (geoFacet) {
        geometry = {
          type: 'Point',
          coordinates: [geoFacet.longitude, geoFacet.latitude],
        }
      }
    }

    if (geometry) {
      // Build properties for popup
      const attributes: Record<string, unknown> = {}

      // Extract relevant display attributes
      const skipKeys = ['geometry', 'latitude', 'longitude', 'coordinates', 'entity_id', 'entity_name', 'name', 'facets']
      for (const [key, value] of Object.entries(item)) {
        if (!skipKeys.includes(key) && value != null && typeof value !== 'object') {
          attributes[key] = value
        }
      }

      // Add some facet values if available
      if (item.facets) {
        for (const [key, facetValue] of Object.entries(item.facets)) {
          if (facetValue && typeof facetValue === 'object' && 'value' in (facetValue as Record<string, unknown>)) {
            attributes[key] = (facetValue as { value: unknown }).value
          } else if (facetValue != null && typeof facetValue !== 'object') {
            attributes[key] = facetValue
          }
        }
      }

      features.push({
        type: 'Feature',
        geometry,
        properties: {
          id: item.entity_id || item.id || `feature-${features.length}`,
          name: item.entity_name || item.name || t('visualization.map.unknownEntity'),
          entity_id: item.entity_id,
          entity_type: item.entity_type || item.entity_type_name,
          icon: item.icon || 'mdi-map-marker',
          color: item.color || 'primary',
          attributes,
        },
      })
    }
  }

  return {
    type: 'FeatureCollection',
    features,
  }
}

// Initialize map
async function initMap() {
  if (!mapContainer.value) return

  map.value = new maplibregl.Map({
    container: mapContainer.value,
    style: mapStyle.value,
    center: DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
    // Use empty object to enable attribution with default options (fixes MapLibre type issue)
    attributionControl: {},
  })

  // Add navigation controls
  // @ts-expect-error - MapLibre types cause deep instantiation error
  map.value.addControl(new maplibregl.NavigationControl(), 'top-right')
  map.value.addControl(new maplibregl.ScaleControl(), 'bottom-right')

  // Setup ResizeObserver for responsive resizing
  if (mapContainer.value) {
    resizeObserver.value = new ResizeObserver(() => {
      if (map.value) {
        map.value.resize()
      }
    })
    resizeObserver.value.observe(mapContainer.value)
  }

  // Wait for map to load
  map.value.on('load', () => {
    loadGeoData()
    setupMapInteractions()
  })
}

// Helper to extend bounds with any geometry type
function extendBoundsWithGeometry(bounds: maplibregl.LngLatBounds, geometry: GeoJSON.Geometry) {
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

// Load GeoJSON data from props
function loadGeoData() {
  if (!map.value) return

  loading.value = true
  try {
    const geojson = convertToGeoJSON(props.data)

    // Separate points from polygons
    const points: GeoJSON.Feature[] = []
    const polygons: GeoJSON.Feature[] = []

    for (const feature of geojson.features) {
      const geomType = feature.geometry?.type
      if (geomType === 'Point') {
        points.push(feature)
      } else if (['Polygon', 'MultiPolygon', 'LineString', 'MultiLineString'].includes(geomType || '')) {
        polygons.push(feature)
      }
    }

    totalFeatures.value = geojson.features.length
    pointCount.value = points.length
    polygonCount.value = polygons.length

    // Remove existing sources and layers
    const layersToRemove = ['clusters', 'cluster-count', 'unclustered-point', 'polygon-fill', 'polygon-line', 'polygon-highlight']
    const sourcesToRemove = ['smart-query-points', 'smart-query-polygons']

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

    // Add Points source with clustering
    if (points.length > 0) {
      map.value.addSource('smart-query-points', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: points },
        cluster: points.length > 20, // Only cluster if many points
        clusterMaxZoom: 14,
        clusterRadius: 50,
      })

      const colors = clusterColors.value

      // Cluster circles layer
      if (points.length > 20) {
        map.value.addLayer({
          id: 'clusters',
          type: 'circle',
          source: 'smart-query-points',
          filter: ['has', 'point_count'],
          paint: {
            'circle-color': [
              'step',
              ['get', 'point_count'],
              colors.small,
              10,
              colors.medium,
              50,
              colors.large,
            ],
            'circle-radius': [
              'step',
              ['get', 'point_count'],
              18,
              10,
              26,
              50,
              34,
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
          source: 'smart-query-points',
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
      }

      // Individual points layer
      map.value.addLayer({
        id: 'unclustered-point',
        type: 'circle',
        source: 'smart-query-points',
        filter: points.length > 20 ? ['!', ['has', 'point_count']] : true,
        paint: {
          'circle-color': colors.small,
          'circle-radius': 8,
          'circle-stroke-width': 2,
          'circle-stroke-color': colors.stroke,
          'circle-opacity': 0.9,
        },
      })
    }

    // Add Polygons source
    if (polygons.length > 0) {
      map.value.addSource('smart-query-polygons', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: polygons },
      })

      const polygonColor = isDark.value ? '#81C784' : '#2E7D32'
      const highlightColor = isDark.value ? '#deeec6' : '#113634'

      map.value.addLayer({
        id: 'polygon-fill',
        type: 'fill',
        source: 'smart-query-polygons',
        paint: {
          'fill-color': ['coalesce', ['get', 'color'], polygonColor],
          'fill-opacity': isDark.value ? 0.25 : 0.2,
        },
      })

      map.value.addLayer({
        id: 'polygon-line',
        type: 'line',
        source: 'smart-query-polygons',
        paint: {
          'line-color': ['coalesce', ['get', 'color'], polygonColor],
          'line-width': 2,
        },
      })

      map.value.addLayer({
        id: 'polygon-highlight',
        type: 'line',
        source: 'smart-query-polygons',
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
      geojson.features.forEach((feature) => {
        if (feature.geometry) {
          extendBoundsWithGeometry(bounds, feature.geometry)
        }
      })
      map.value.fitBounds(bounds, {
        padding: FIT_BOUNDS_PADDING,
        maxZoom: MAX_FIT_ZOOM,
      })
    }
  } catch (error) {
    logger.error('Failed to load map data:', error)
  } finally {
    loading.value = false
  }
}

// Setup map interactions
function setupMapInteractions() {
  if (!map.value) return

  // Click on cluster to zoom in
  map.value.on('click', 'clusters', async (e) => {
    if (!map.value) return
    const features = map.value.queryRenderedFeatures(e.point, { layers: ['clusters'] })
    if (!features.length) return

    const clusterId = features[0].properties?.cluster_id
    const source = map.value.getSource('smart-query-points') as maplibregl.GeoJSONSource

    const zoom = await source.getClusterExpansionZoom(clusterId)
    map.value.easeTo({
      center: (features[0].geometry as GeoJSON.Point).coordinates as [number, number],
      zoom: zoom,
    })
  })

  // Click on individual point
  map.value.on('click', 'unclustered-point', (e) => {
    if (!e.features?.length) return
    showFeaturePopup(e.features[0], e.point)
  })

  // Click on polygon
  map.value.on('click', 'polygon-fill', (e) => {
    if (!e.features?.length) return
    showFeaturePopup(e.features[0], e.point)
  })

  // Hover effects
  const setCursor = (cursor: string) => {
    if (map.value) map.value.getCanvas().style.cursor = cursor
  }

  map.value.on('mouseenter', 'clusters', () => setCursor('pointer'))
  map.value.on('mouseleave', 'clusters', () => setCursor(''))
  map.value.on('mouseenter', 'unclustered-point', () => setCursor('pointer'))
  map.value.on('mouseleave', 'unclustered-point', () => setCursor(''))

  map.value.on('mouseenter', 'polygon-fill', (e) => {
    setCursor('pointer')
    if (e.features?.length && map.value) {
      map.value.setFilter('polygon-highlight', ['==', ['get', 'id'], e.features[0].properties?.id || ''])
    }
  })
  map.value.on('mouseleave', 'polygon-fill', () => {
    setCursor('')
    if (map.value) {
      map.value.setFilter('polygon-highlight', ['==', ['get', 'id'], ''])
    }
  })

  // Close popup when clicking elsewhere
  map.value.on('click', (e) => {
    if (!map.value) return
    const layers = ['unclustered-point', 'clusters', 'polygon-fill'].filter(l => map.value?.getLayer(l))
    const features = map.value.queryRenderedFeatures(e.point, { layers })
    if (!features.length) {
      selectedFeature.value = null
    }
  })
}

function showFeaturePopup(feature: maplibregl.MapGeoJSONFeature, point: maplibregl.Point) {
  const props = feature.properties || {}

  selectedFeature.value = {
    name: props.name,
    entity_id: props.entity_id,
    entity_type: props.entity_type,
    icon: props.icon,
    color: props.color,
    attributes: typeof props.attributes === 'string' ? JSON.parse(props.attributes) : props.attributes,
  }

  popupPosition.value = {
    x: Math.min(point.x + 10, (mapContainer.value?.clientWidth || 500) - 330),
    y: Math.min(point.y - 10, (mapContainer.value?.clientHeight || 400) - 200),
  }
}

function formatAttributeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase())
}

function formatAttributeValue(value: unknown): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') return value.toLocaleString()
  if (typeof value === 'boolean') return value ? t('common.yes') : t('common.no')
  if (value instanceof Date) return value.toLocaleDateString()
  return String(value)
}

function navigateToEntity(feature: { entity_id?: string }) {
  if (feature.entity_id) {
    // Use /entity/:id route for direct access by ID
    router.push(`/entity/${feature.entity_id}`)
  }
}

// Watch for data changes
watch(() => props.data, () => {
  if (map.value) {
    loadGeoData()
  }
}, { deep: true })

// Watch for theme changes
watch(isDark, () => {
  if (map.value) {
    map.value.setStyle(mapStyle.value)
    map.value.once('style.load', () => {
      loadGeoData()
      setupMapInteractions()
    })
  }
})

onMounted(() => {
  nextTick(() => {
    initMap()
  })
})

onUnmounted(() => {
  // Clean up ResizeObserver
  if (resizeObserver.value) {
    resizeObserver.value.disconnect()
    resizeObserver.value = null
  }
  // Clean up map
  if (map.value) {
    map.value.remove()
    map.value = null
  }
})
</script>

<style scoped>
.map-visualization {
  position: relative;
  height: 450px;
  border-radius: 8px;
  overflow: hidden;
}

.map-container {
  width: 100%;
  height: 100%;
}

.map-tint-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(135deg, rgba(17, 54, 52, 0.08) 0%, transparent 50%);
}

.map-overlay {
  position: absolute;
  z-index: 1;
}

.map-overlay--top-left {
  top: 12px;
  left: 12px;
}

.map-overlay--bottom-left {
  bottom: 32px;
  left: 12px;
}

.map-overlay--center {
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.entity-popup {
  position: absolute;
  z-index: 10;
  pointer-events: auto;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.popup-content {
  overflow-y: auto;
  max-height: 150px;
}

.cluster-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid white;
}

.cluster-dot--small {
  background-color: #2E7D32;
}

.cluster-dot--medium {
  background-color: #113634;
}

.cluster-dot--large {
  background-color: #5c6bc0;
}

.polygon-sample {
  width: 20px;
  height: 12px;
  background-color: rgba(46, 125, 50, 0.2);
  border: 2px solid #2E7D32;
  border-radius: 2px;
}

.theme-dark .cluster-dot--small {
  background-color: #81C784;
}

.theme-dark .cluster-dot--medium {
  background-color: #deeec6;
}

.theme-dark .cluster-dot--large {
  background-color: #B39DDB;
}

.theme-dark .polygon-sample {
  background-color: rgba(129, 199, 132, 0.25);
  border-color: #81C784;
}
</style>
