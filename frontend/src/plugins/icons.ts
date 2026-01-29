/**
 * Vuetify SVG Icon Configuration
 *
 * This module provides tree-shakeable SVG icons using @mdi/js instead of the
 * full @mdi/font (~200KB). Only icons that are actually imported are included
 * in the final bundle.
 *
 * Usage: Icons are referenced by their Vuetify alias (e.g., icon="$check")
 * or by their full mdi path for dynamic icons.
 */

import { h } from 'vue'
import type { IconSet, IconProps } from 'vuetify'
import { iconPaths } from './icon-paths'

/**
 * Convert kebab-case (mdi-account-circle) to PascalCase (mdiAccountCircle)
 */
function kebabToPascal(str: string): string {
  return str
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join('')
}

/**
 * Custom SVG icon component that renders MDI icons from @mdi/js
 */
const mdiSvgIcon: IconSet['component'] = (props: IconProps) => {
  // Handle both formats: "mdi-account" and just "account"
  let iconName = props.icon as string

  // If it starts with "mdi-", convert to the @mdi/js format
  if (typeof iconName === 'string') {
    if (iconName.startsWith('mdi-')) {
      iconName = 'mdi' + kebabToPascal(iconName.slice(4))
    } else if (!iconName.startsWith('mdi')) {
      iconName = 'mdi' + kebabToPascal(iconName)
    }
  }

  // Get the SVG path from the generated subset (448 icons vs 7000+)
  const svgPath = iconPaths[iconName]

  if (!svgPath) {
    console.warn(`Icon not found: ${props.icon} (looked for ${iconName})`)
    // Return a placeholder icon
    return h('svg', {
      viewBox: '0 0 24 24',
      style: { width: '1em', height: '1em' },
    })
  }

  return h(
    'svg',
    {
      viewBox: '0 0 24 24',
      style: {
        width: '1em',
        height: '1em',
        fill: 'currentColor',
      },
      role: 'img',
      'aria-hidden': 'true',
    },
    [h('path', { d: svgPath })]
  )
}

/**
 * Vuetify icon set configuration for MDI SVG icons
 */
export const mdiSvgIconSet: IconSet = {
  component: mdiSvgIcon,
}

/**
 * Commonly used icon aliases for better tree-shaking
 * These are pre-resolved to their SVG paths
 */
export const iconAliases = {
  // Navigation & Actions
  menu: 'mdi-menu',
  close: 'mdi-close',
  check: 'mdi-check',
  plus: 'mdi-plus',
  minus: 'mdi-minus',
  edit: 'mdi-pencil',
  delete: 'mdi-delete',
  save: 'mdi-content-save',
  refresh: 'mdi-refresh',
  search: 'mdi-magnify',
  filter: 'mdi-filter',
  sort: 'mdi-sort',

  // Vuetify component defaults
  complete: 'mdi-check',
  cancel: 'mdi-close-circle',
  error: 'mdi-close-circle',
  warning: 'mdi-alert',
  info: 'mdi-information',
  success: 'mdi-check-circle',
  clear: 'mdi-close',
  prev: 'mdi-chevron-left',
  next: 'mdi-chevron-right',
  checkboxOn: 'mdi-checkbox-marked',
  checkboxOff: 'mdi-checkbox-blank-outline',
  checkboxIndeterminate: 'mdi-minus-box',
  delimiter: 'mdi-circle',
  sortAsc: 'mdi-arrow-up',
  sortDesc: 'mdi-arrow-down',
  expand: 'mdi-chevron-down',
  collapse: 'mdi-chevron-up',
  dropdown: 'mdi-menu-down',
  radioOn: 'mdi-radiobox-marked',
  radioOff: 'mdi-radiobox-blank',
  ratingEmpty: 'mdi-star-outline',
  ratingFull: 'mdi-star',
  ratingHalf: 'mdi-star-half-full',
  loading: 'mdi-cached',
  first: 'mdi-page-first',
  last: 'mdi-page-last',
  unfold: 'mdi-unfold-more-horizontal',
  file: 'mdi-paperclip',
  subgroup: 'mdi-menu-down',
  calendar: 'mdi-calendar',
  treeviewCollapse: 'mdi-chevron-down',
  treeviewExpand: 'mdi-chevron-right',

  // Status & Feedback
  alert: 'mdi-alert',
  'alert-circle': 'mdi-alert-circle',
  'check-circle': 'mdi-check-circle',
  'close-circle': 'mdi-close-circle',
  'help-circle': 'mdi-help-circle',
  'information-outline': 'mdi-information-outline',

  // Common UI elements
  eye: 'mdi-eye',
  'eye-off': 'mdi-eye-off',
  download: 'mdi-download',
  upload: 'mdi-upload',
  copy: 'mdi-content-copy',
  link: 'mdi-link',
  'open-in-new': 'mdi-open-in-new',
  settings: 'mdi-cog',
  account: 'mdi-account',
  home: 'mdi-home',
  star: 'mdi-star',
  heart: 'mdi-heart',
  bookmark: 'mdi-bookmark',
}
