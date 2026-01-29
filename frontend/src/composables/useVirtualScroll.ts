/**
 * Virtual Scrolling Composable
 *
 * Provides efficient rendering of large lists by only rendering visible items.
 * Use this for lists that could grow beyond ~100 items without server-side pagination.
 *
 * @example
 * ```vue
 * <template>
 *   <div ref="containerRef" style="height: 400px; overflow-y: auto;">
 *     <div :style="{ height: `${totalHeight}px`, position: 'relative' }">
 *       <div
 *         v-for="item in visibleItems"
 *         :key="item.id"
 *         :style="{ position: 'absolute', top: `${item.offsetTop}px`, width: '100%' }"
 *       >
 *         <YourItemComponent :item="item.data" />
 *       </div>
 *     </div>
 *   </div>
 * </template>
 *
 * <script setup>
 * const { containerRef, visibleItems, totalHeight } = useVirtualScroll(items, { itemHeight: 48 })
 * </script>
 * ```
 */

import { ref, computed, watch, onMounted, onUnmounted, type Ref } from 'vue'

export interface VirtualScrollOptions {
  /** Height of each item in pixels (required for fixed-height items) */
  itemHeight: number
  /** Number of items to render above/below the visible area (default: 3) */
  overscan?: number
  /** Debounce scroll events in ms (default: 16 for ~60fps) */
  scrollDebounce?: number
}

export interface VirtualItem<T> {
  /** The original item data */
  data: T
  /** Index in the original array */
  index: number
  /** Absolute top position in pixels */
  offsetTop: number
}

export function useVirtualScroll<T extends { id: string | number }>(
  items: Ref<T[]>,
  options: VirtualScrollOptions
) {
  const { itemHeight, overscan = 3, scrollDebounce = 16 } = options

  const containerRef = ref<HTMLElement | null>(null)
  const scrollTop = ref(0)
  const containerHeight = ref(0)

  // Calculate total scrollable height
  const totalHeight = computed(() => items.value.length * itemHeight)

  // Calculate visible range
  const visibleRange = computed(() => {
    const start = Math.max(0, Math.floor(scrollTop.value / itemHeight) - overscan)
    const visibleCount = Math.ceil(containerHeight.value / itemHeight) + 2 * overscan
    const end = Math.min(items.value.length, start + visibleCount)
    return { start, end }
  })

  // Get visible items with position data
  const visibleItems = computed((): VirtualItem<T>[] => {
    const { start, end } = visibleRange.value
    return items.value.slice(start, end).map((data, i) => ({
      data,
      index: start + i,
      offsetTop: (start + i) * itemHeight,
    }))
  })

  // Scroll event handler with debouncing
  let scrollTimeout: ReturnType<typeof setTimeout> | null = null
  const handleScroll = () => {
    if (scrollTimeout) return

    scrollTimeout = setTimeout(() => {
      if (containerRef.value) {
        scrollTop.value = containerRef.value.scrollTop
      }
      scrollTimeout = null
    }, scrollDebounce)
  }

  // Resize observer for container height changes
  let resizeObserver: ResizeObserver | null = null

  onMounted(() => {
    if (containerRef.value) {
      containerHeight.value = containerRef.value.clientHeight
      containerRef.value.addEventListener('scroll', handleScroll, { passive: true })

      resizeObserver = new ResizeObserver((entries) => {
        for (const entry of entries) {
          containerHeight.value = entry.contentRect.height
        }
      })
      resizeObserver.observe(containerRef.value)
    }
  })

  onUnmounted(() => {
    if (containerRef.value) {
      containerRef.value.removeEventListener('scroll', handleScroll)
    }
    if (resizeObserver) {
      resizeObserver.disconnect()
    }
    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
    }
  })

  // Reset scroll position when items change significantly
  watch(
    () => items.value.length,
    (newLength, oldLength) => {
      if (Math.abs(newLength - oldLength) > 10 && containerRef.value) {
        containerRef.value.scrollTop = 0
        scrollTop.value = 0
      }
    }
  )

  /**
   * Scroll to a specific item index
   */
  const scrollToIndex = (index: number, behavior: ScrollBehavior = 'smooth') => {
    if (containerRef.value && index >= 0 && index < items.value.length) {
      containerRef.value.scrollTo({
        top: index * itemHeight,
        behavior,
      })
    }
  }

  /**
   * Scroll to a specific item by ID
   */
  const scrollToItem = (id: string | number, behavior: ScrollBehavior = 'smooth') => {
    const index = items.value.findIndex((item) => item.id === id)
    if (index !== -1) {
      scrollToIndex(index, behavior)
    }
  }

  return {
    /** Ref to attach to the scroll container element */
    containerRef,
    /** Array of visible items with position data */
    visibleItems,
    /** Total height for the scrollable content */
    totalHeight,
    /** Current visible range { start, end } */
    visibleRange,
    /** Scroll to a specific index */
    scrollToIndex,
    /** Scroll to a specific item by ID */
    scrollToItem,
  }
}

export default useVirtualScroll
