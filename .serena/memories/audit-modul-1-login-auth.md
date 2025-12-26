# Audit Report: Modul 1 - Login & Auth

## Geprüfte Dateien
- `frontend/src/views/LoginView.vue` (637 Zeilen)
- `frontend/src/stores/auth.ts` (304 Zeilen)
- `backend/app/api/auth.py` (296+ Zeilen - login Funktion)
- `backend/app/core/security.py` (254 Zeilen)
- `backend/app/models/user.py` (205 Zeilen)

## Bewertung nach Kriterien

### UX/UI: ⭐⭐⭐⭐ (4/5)

**Positiv:**
- ✅ Schöne, moderne UI mit Animationen (Particles, Glow Rings)
- ✅ Loading States (Spinner im Button)
- ✅ Error States mit schließbarer Alert
- ✅ Accessibility: aria-labels, aria-invalid, aria-describedby, role="alert"
- ✅ Password Toggle Sichtbarkeit
- ✅ i18n Unterstützung (de/en)
- ✅ Responsive Design (@media max-width 480px)
- ✅ Keyboard Navigation (Enter zum Login)

**Verbesserungspotential:**
- ⚠️ Kein Feedback bei Rate-Limiting (User weiß nicht, warum Login fehlschlägt)
- ⚠️ Keine "Forgot Password" Funktion sichtbar
- ⚠️ Keine Capslock-Warnung

### Best Practice: ⭐⭐⭐⭐⭐ (5/5)

**Security (hervorragend!):**
- ✅ bcrypt mit 12 Rounds für Password Hashing
- ✅ JWT mit kurzer Lebensdauer (15 min Access Token)
- ✅ Separate Refresh Tokens (30 Tage) mit Hash-Storage
- ✅ Rate Limiting für Login-Versuche
- ✅ Session Management (max 5 Sessions pro User)
- ✅ SSE Tickets für sichere EventSource (30 Sek.)
- ✅ Audit Logging für Login-Events
- ✅ Account Deactivation Check
- ✅ Device/User-Agent Tracking

**API Design:**
- ✅ RESTful Endpoints
- ✅ Pydantic Models für Validation
- ✅ Proper HTTP Status Codes (401, 403)

### Modularität: ⭐⭐⭐⭐ (4/5)

**Positiv:**
- ✅ Klare Trennung: View, Store, API, Security, Model
- ✅ Security Functions in separatem Modul
- ✅ Pinia Store mit Composition API

**Verbesserungspotential:**
- ⚠️ LoginView.vue hat 637 Zeilen (inkl. CSS) - könnte aufgeteilt werden
- ⚠️ auth.py hat Request Classes inline definiert - könnten in schemas/ sein

### Code-Qualität: ⭐⭐⭐⭐ (4/5)

**Positiv:**
- ✅ TypeScript mit guter Typisierung
- ✅ Python Type Hints durchgängig
- ✅ Gute Docstrings im Backend
- ✅ Konstanten statt Magic Numbers

**Probleme:**
- ❌ KEINE TESTS vorhanden (weder Frontend noch Backend)
- ⚠️ Hardcoded deutsche Strings in auth.ts (Zeile 120, 235)
- ⚠️ Unused parameter `_index` in LoginView.vue:176

### State of the Art: ⭐⭐⭐⭐ (4/5)

**Positiv:**
- ✅ Vue 3 Composition API
- ✅ Pinia für State Management
- ✅ async/await durchgängig
- ✅ FastAPI Best Practices
- ✅ Modern Python (type hints, enums)

**Verbesserungspotential:**
- ⚠️ localStorage für Token statt HTTP-Only Cookies (XSS-Risiko)
- ⚠️ Keine Zod/Runtime Validation im Frontend
- ⚠️ Kein Passkey/WebAuthn Support

---

## Findings nach Priorität

### Critical (0)
Keine kritischen Probleme gefunden.

### Major (3)

#### M1: Keine Tests
- **Dateien:** auth.ts, auth.py, security.py
- **Problem:** Keine Unit Tests für kritische Auth-Funktionen
- **Risiko:** Regressions bei Änderungen, schwer zu refactoren
- **Lösung:** Unit Tests für Login, Logout, Token Refresh, Password Validation schreiben

#### M2: Token in localStorage (XSS-Anfällig)
- **Datei:** auth.ts:111-113
- **Problem:** Tokens werden in localStorage gespeichert
- **Risiko:** Bei XSS-Vulnerability können Tokens gestohlen werden
- **Lösung:** HTTP-Only Cookies für Refresh Token, Memory für Access Token

#### M3: Keine Email-Validierung
- **Datei:** LoginView.vue:171-173
- **Problem:** `isFormValid` prüft nur `length > 0`, keine Email-Format-Validierung
- **Risiko:** Schlechte UX, unnötige Server-Requests
- **Lösung:** Regex oder Vuelidate für Email-Format

### Minor (4)

#### m1: Hardcoded deutsche Strings
- **Datei:** auth.ts:120, 235
- **Code:** `'Login fehlgeschlagen'`, `'Passwortänderung fehlgeschlagen'`
- **Lösung:** i18n Keys verwenden

#### m2: Unused Parameter
- **Datei:** LoginView.vue:176
- **Code:** `function getParticleStyle(_index: number)`
- **Lösung:** Index nutzen für Variation oder Parameter entfernen

#### m3: Self-initializing Store
- **Datei:** auth.ts:267-271
- **Problem:** Store initialisiert sich selbst bei Creation
- **Risiko:** Probleme bei SSR/Testing
- **Lösung:** Explizite Initialisierung via App Hook

#### m4: Inline Request Classes
- **Datei:** auth.py
- **Problem:** LoginRequest, TokenResponse etc. inline definiert
- **Lösung:** Nach schemas/auth.py verschieben

---

## Refactoring-Tasks

### Phase 1: Quick Fixes
1. [ ] i18n Keys für hardcoded Strings
2. [ ] Email-Validierung im Frontend
3. [ ] Unused parameter fix

### Phase 2: Tests
1. [ ] Unit Tests für auth.ts (login, logout, refresh, hasRole)
2. [ ] Unit Tests für security.py (password hash, JWT)
3. [ ] Integration Tests für auth.py endpoints

### Phase 3: Structural
1. [ ] Request/Response Schemas nach schemas/auth.py verschieben
2. [ ] LoginView.vue aufteilen (CSS auslagern)
3. [ ] Store Initialisierung refactoren

### Phase 4: Advanced (Optional)
1. [ ] HTTP-Only Cookie Implementation
2. [ ] Rate-Limit Feedback im UI
3. [ ] Forgot Password Flow
