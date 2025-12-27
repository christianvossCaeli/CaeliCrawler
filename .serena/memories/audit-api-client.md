# API-Client Audit (27.12.2025)

## Executive Summary

**Gesamtbewertung: ⭐⭐⭐⭐ (4.0/5)** - Solide Architektur mit guten Verbesserungen

---

## Analysierte Dateien

| Datei | LOC | Bewertung |
|-------|-----|-----------|
| `services/api/client.ts` | 145 | ⭐⭐⭐⭐ |
| `services/api/index.ts` | 505 | ⭐⭐⭐⭐⭐ |
| `services/api/admin.ts` | 376 | ⭐⭐⭐⭐ |

---

## Positive Findings

### client.ts
✅ **Token-Refresh-Queue** - Parallele Requests werden gequeued während Refresh läuft
✅ **Auth-Endpoint-Check** - Verhindert Refresh-Loops bei /auth/* Endpoints
✅ **Redirect mit Original-URL** - Nach Login wird zur ursprünglichen Seite navigiert

### index.ts
✅ **Exzellente Strukturierung** - 20+ API-Namespaces klar organisiert
✅ **Konsistentes Naming** - `entityApi`, `facetApi`, `adminApi`, etc.
✅ **Legacy-Aliase** - Backwards-Compatibility für alte API-Aufrufe

### admin.ts
✅ **TypeScript Types** - Alle Parameter typisiert
✅ **AbortSignal Support** - Requests können abgebrochen werden
✅ **Response Types** - Generics für typisierte Responses

---

## Durchgeführte Verbesserungen

### 1. Timeout hinzugefügt
```typescript
// Vorher: Kein Timeout (kann zu hängenden Requests führen)
// Nachher:
const DEFAULT_TIMEOUT = 30000

export const api = axios.create({
  baseURL: '/api',
  timeout: DEFAULT_TIMEOUT,
  ...
})
```

### 2. Code-Duplikation eliminiert
```typescript
// Vorher: 2x identischer Logout-Code (je 14 Zeilen)
// Nachher: Shared Helper-Funktion
async function clearAuthAndRedirect(router: Router) {
  const { useAuthStore } = await import('@/stores/auth')
  const auth = useAuthStore()
  // ... clear auth state
}
```
**Einsparung:** ~20 Zeilen doppelter Code

### 3. Request-Interceptor für Auth-Header
```typescript
// Vorher: Header manuell im Store gesetzt
// Nachher: Automatisch via Interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('caeli_auth_token')
  if (token && !config.headers['Authorization']) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})
```
**Vorteil:** Zuverlässiger, auch bei Race-Conditions während Initialization

---

## Verbleibende Empfehlungen

### Optional: Retry-Logic für Netzwerkfehler
Aktuell werden nur 401-Fehler speziell behandelt. Für robustere Netzwerk-Handhabung könnte man `axios-retry` integrieren:

```typescript
// Optional - nicht implementiert
import axiosRetry from 'axios-retry'

axiosRetry(api, {
  retries: 3,
  retryDelay: axiosRetry.exponentialDelay,
  retryCondition: (error) =>
    axiosRetry.isNetworkOrIdempotentRequestError(error) ||
    error.response?.status === 503
})
```

### Response-Type-Safety
Einige API-Funktionen haben keine expliziten Response-Types. Beispiel:
```typescript
// Aktuell
export const getUsers = (params?) => api.get('/admin/users', { params })

// Besser
export const getUsers = (params?): Promise<AxiosResponse<UserListResponse>> =>
  api.get('/admin/users', { params })
```

---

## Architektur-Übersicht

```
services/api/
├── client.ts      # Axios-Instance + Interceptors
├── index.ts       # API-Namespaces Export (20+)
├── admin.ts       # Admin-Endpoints (Crawler, Users, etc.)
├── entities.ts    # Entity CRUD + Filtering
├── facets.ts      # Facet Types/Values
├── relations.ts   # Entity Relations
├── sources.ts     # Data Sources + Categories
├── ai.ts          # AI/Assistant Endpoints
└── auth.ts        # Authentication
```

---

## Geänderte Dateien

```
frontend/src/services/api/client.ts
```

## Fixes Zusammenfassung

| # | Fix | Impact |
|---|-----|--------|
| 1 | Timeout (30s) | Verhindert hängende Requests |
| 2 | clearAuthAndRedirect Helper | -20 Zeilen Duplikation |
| 3 | Request-Interceptor | Zuverlässigere Auth-Header |
