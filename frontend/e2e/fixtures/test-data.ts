/**
 * Test Data Fixtures for E2E Tests
 *
 * Contains test users, entities, and other test data
 */

export interface TestUser {
  email: string
  password: string
  role: 'admin' | 'editor' | 'viewer'
}

export interface TestEntity {
  name: string
  type: string
  description?: string
}

// Test Users
export const TEST_USERS: Record<string, TestUser> = {
  admin: {
    email: process.env.ADMIN_EMAIL || 'admin@test.com',
    password: process.env.ADMIN_PASSWORD || 'testpassword123',
    role: 'admin'
  },
  editor: {
    email: process.env.EDITOR_EMAIL || 'editor@test.com',
    password: process.env.EDITOR_PASSWORD || 'editor123',
    role: 'editor'
  },
  viewer: {
    email: process.env.VIEWER_EMAIL || 'viewer@test.com',
    password: process.env.VIEWER_PASSWORD || 'viewer123',
    role: 'viewer'
  }
}

// Invalid credentials for negative tests
export const INVALID_CREDENTIALS = {
  email: 'invalid@test.com',
  password: 'wrongpassword'
}

// Test Entities
export const TEST_ENTITIES: TestEntity[] = [
  {
    name: 'Test Organization',
    type: 'organization',
    description: 'A test organization for E2E testing'
  },
  {
    name: 'Test Person',
    type: 'person',
    description: 'A test person for E2E testing'
  },
  {
    name: 'Test Location',
    type: 'location',
    description: 'A test location for E2E testing'
  }
]

// Test Smart Queries
export const TEST_QUERIES = {
  simple: 'Zeige alle Dokumente der letzten Woche',
  withVisualization: 'Erstelle eine Übersicht aller Organisationen als Diagramm',
  complex: 'Analysiere die Beziehungen zwischen Personen und Organisationen'
}

// Test filters
export const TEST_FILTERS = {
  category: 'Politik',
  dateRange: {
    from: '2024-01-01',
    to: '2024-12-31'
  }
}

// API endpoints
export const API_ENDPOINTS = {
  login: '/api/v1/auth/login',
  logout: '/api/v1/auth/logout',
  currentUser: '/api/v1/auth/me',
  entities: '/api/v1/entities',
  smartQuery: '/api/v1/analysis/smart-query'
}

// Timeouts
export const TIMEOUTS = {
  short: 3000,
  medium: 10000,
  long: 30000
}
