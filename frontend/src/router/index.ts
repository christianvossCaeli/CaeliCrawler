import { createRouter, createWebHistory } from 'vue-router'
import type { RouteLocationNormalized, NavigationGuardNext } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// Route meta types
declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    requiresAdmin?: boolean
    requiresEditor?: boolean
    public?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // Public routes
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true }
    },

    // Protected routes
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    // Entity-Facet System Routes
    {
      path: '/entities',
      name: 'entities',
      component: () => import('@/views/EntitiesView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/entities/:typeSlug',
      name: 'entities-by-type',
      component: () => import('@/views/EntitiesView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/entities/:typeSlug/:entitySlug',
      name: 'entity-detail',
      component: () => import('@/views/EntityDetailView.vue'),
      meta: { requiresAuth: true }
    },
    // Direct entity access by ID (used by maps, summaries, etc.)
    {
      path: '/entity/:id',
      name: 'entity-by-id',
      component: () => import('@/views/EntityDetailView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('@/views/CategoriesView.vue'),
      meta: { requiresAuth: true, requiresEditor: true }
    },
    {
      path: '/sources',
      name: 'sources',
      component: () => import('@/views/SourcesView.vue'),
      meta: { requiresAuth: true, requiresEditor: true }
    },
    {
      path: '/crawler',
      name: 'crawler',
      component: () => import('@/views/CrawlerView.vue'),
      meta: { requiresAuth: true, requiresEditor: true }
    },
    {
      path: '/documents',
      name: 'documents',
      component: () => import('@/views/DocumentsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/results',
      name: 'results',
      component: () => import('@/views/ResultsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/smart-query',
      name: 'smart-query',
      component: () => import('@/views/SmartQueryView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/export',
      name: 'export',
      component: () => import('@/views/ExportView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/help',
      name: 'help',
      component: () => import('@/views/HelpView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/notifications',
      name: 'notifications',
      component: () => import('@/views/NotificationsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: () => import('@/views/FavoritesView.vue'),
      meta: { requiresAuth: true }
    },

    // Entity Types (accessible to all authenticated users)
    {
      path: '/admin/entity-types',
      name: 'admin-entity-types',
      component: () => import('@/views/admin/EntityTypesView.vue'),
      meta: { requiresAuth: true }
    },

    // Facet Types (accessible to all authenticated users)
    {
      path: '/admin/facet-types',
      name: 'admin-facet-types',
      component: () => import('@/views/admin/FacetTypesView.vue'),
      meta: { requiresAuth: true }
    },

    // Admin routes
    {
      path: '/admin/users',
      name: 'admin-users',
      component: () => import('@/views/admin/UsersView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/audit-log',
      name: 'admin-audit-log',
      component: () => import('@/views/admin/AuditLogView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },
    {
      path: '/admin/llm-usage',
      name: 'admin-llm-usage',
      component: () => import('@/views/admin/LLMUsageView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true }
    },

    // Custom Summaries routes
    {
      path: '/summaries',
      name: 'summaries',
      component: () => import('@/views/CustomSummariesView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/summaries/:id',
      name: 'summary-dashboard',
      component: () => import('@/views/SummaryDashboardView.vue'),
      meta: { requiresAuth: true }
    },

    // Shared Summary (public access)
    {
      path: '/shared/summary/:token',
      name: 'shared-summary',
      component: () => import('@/views/SharedSummaryView.vue'),
      meta: { public: true }
    },

    // 403 Forbidden page
    {
      path: '/forbidden',
      name: 'forbidden',
      component: () => import('@/views/ForbiddenView.vue'),
      meta: { requiresAuth: true }
    },

    // Catch-all redirect
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

// Navigation guard
router.beforeEach(async (
  to: RouteLocationNormalized,
  _from: RouteLocationNormalized,
  next: NavigationGuardNext
) => {
  const auth = useAuthStore()

  // Wait for auth to initialize
  if (!auth.initialized) {
    await auth.fetchCurrentUser()
  }

  // Public routes (like login)
  if (to.meta.public) {
    // If already authenticated, redirect to dashboard
    if (auth.isAuthenticated) {
      return next({ name: 'dashboard' })
    }
    return next()
  }

  // Protected routes - check authentication
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({
      name: 'login',
      query: { redirect: to.fullPath }
    })
  }

  // Admin routes - check admin role
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return next({ name: 'forbidden', query: { from: to.fullPath } })
  }

  // Editor routes - check editor role
  if (to.meta.requiresEditor && !auth.isEditor) {
    return next({ name: 'forbidden', query: { from: to.fullPath } })
  }

  next()
})

export default router
