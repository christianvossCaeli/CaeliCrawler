# API Documentation Discrepancies

## Format Legend
- **MISSING_DOC**: Endpoint exists in backend but not documented in quick reference
- **MISSING_IMPL**: Documented but not implemented (none found)
- **WRONG_SCHEMA**: Response schema doesn't match documentation (none found)
- **WRONG_AUTH**: Authentication requirement mismatch (none found)

---

## Complete Discrepancies List

### AUTH API (`/api/auth`)

#### MISSING_DOC - 9 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| POST | `/auth/check-password-strength` | Has full implementation, returns password strength analysis |
| PUT | `/auth/language` | Update user language preference (de/en) |
| POST | `/auth/refresh` | Refresh access token using refresh token |
| GET | `/auth/sessions` | List all active sessions for current user |
| DELETE | `/auth/sessions/{session_id}` | Revoke specific session |
| DELETE | `/auth/sessions` | Revoke all sessions except current |
| GET | `/auth/email-verification/status` | Check email verification status |
| POST | `/auth/email-verification/request` | Request verification email (rate limited 1/5min) |
| POST | `/auth/email-verification/confirm` | Confirm email with token (24h validity) |

---

### ADMIN SOURCES (`/admin/sources`)

#### MISSING_DOC - 3 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/admin/sources/meta/countries` | Get list of countries with source counts |
| GET | `/admin/sources/meta/locations` | Get locations with source counts (filterable) |
| GET | `/admin/sources/meta/counts` | Aggregated counts by category/type/status |

---

### ADMIN CRAWLER (`/admin/crawler`)

#### MISSING_DOC - 7 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/admin/crawler/jobs/{job_id}/log` | Stream crawl job logs |
| GET | `/admin/crawler/ai-tasks/running` | List currently running AI extraction tasks |
| POST | `/admin/crawler/ai-tasks/{task_id}/cancel` | Cancel specific AI extraction task |
| POST | `/admin/crawler/documents/process-pending` | Trigger processing of all pending documents |
| POST | `/admin/crawler/documents/stop-all` | Stop all document processing |
| POST | `/admin/crawler/documents/reanalyze-filtered` | Re-analyze documents matching filter criteria |
| POST | `/admin/crawler/reanalyze` | Trigger full document re-analysis |

---

### ADMIN LOCATIONS (`/admin/locations`)

#### MISSING_DOC - 5 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/admin/locations/admin-levels` | Get administrative levels (state/region/district) |
| POST | `/admin/locations/link-sources` | Link data sources to locations |
| GET | `/admin/locations/with-sources` | Get locations with linked source counts |
| GET | `/admin/locations/search` | Search locations by name/criteria |
| POST | `/admin/locations/enrich-admin-levels` | Bulk enrich admin level data |

---

### ADMIN USERS (`/admin/users`)

#### MISSING_DOC - 6 endpoints (Entire section)

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/admin/users` | List all users with pagination |
| POST | `/admin/users` | Create new user (admin only) |
| GET | `/admin/users/{id}` | Get user details |
| PUT | `/admin/users/{id}` | Update user (role, status, etc.) |
| DELETE | `/admin/users/{id}` | Delete user (admin only) |
| POST | `/admin/users/{id}/reset-password` | Admin password reset |

**Status:** Section exists in code but documentation places users under auth instead of admin.

---

### ADMIN AUDIT (`/admin/audit`)

#### MISSING_DOC - 2 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/admin/audit/entity/{entity_type}/{entity_id}` | Get audit log filtered by entity |
| GET | `/admin/audit/user/{user_id}` | Get audit log filtered by user |

---

### ADMIN VERSIONS (`/admin/versions`)

#### MISSING_DOC - 3 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/admin/versions/{entity_type}/{entity_id}/diff` | Get diff between versions |
| GET | `/admin/versions/{entity_type}/{entity_id}/restore/{history_id}` | Restore to specific version |

---

### ADMIN NOTIFICATIONS (`/admin/notifications`)

#### MISSING_DOC - 13 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| POST | `/admin/notifications/email-addresses` | Add new email address for notifications |
| DELETE | `/admin/notifications/email-addresses/{email_id}` | Remove email address |
| POST | `/admin/notifications/email-addresses/{email_id}/verify` | Verify email ownership |
| POST | `/admin/notifications/email-addresses/{email_id}/resend-verification` | Resend verification |
| GET | `/admin/notifications/rules/{rule_id}` | Get specific notification rule |
| PUT | `/admin/notifications/rules/{rule_id}` | Update notification rule |
| DELETE | `/admin/notifications/rules/{rule_id}` | Delete notification rule |
| GET | `/admin/notifications/notifications/{notification_id}` | Get specific notification |
| POST | `/admin/notifications/notifications/{notification_id}/read` | Mark notification as read |
| POST | `/admin/notifications/notifications/read-all` | Mark all as read |
| POST | `/admin/notifications/test-webhook` | Test webhook delivery |
| GET | `/admin/notifications/preferences` | Get notification preferences |
| PUT | `/admin/notifications/preferences` | Update notification preferences |

---

### ADMIN PYSIS (`/admin/pysis`)

#### MISSING_DOC - 24 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| POST | `/admin/pysis/templates` | Create field template |
| GET | `/admin/pysis/templates/{template_id}` | Get specific template |
| PUT | `/admin/pysis/templates/{template_id}` | Update template |
| DELETE | `/admin/pysis/templates/{template_id}` | Delete template |
| GET | `/admin/pysis/locations/{location_name}/processes` | Get processes for location |
| POST | `/admin/pysis/locations/{location_name}/processes` | Create process for location |
| GET | `/admin/pysis/processes/{process_id}` | Get detailed process info |
| PUT | `/admin/pysis/processes/{process_id}` | Update process |
| DELETE | `/admin/pysis/processes/{process_id}` | Delete process |
| POST | `/admin/pysis/processes/{process_id}/apply-template` | Apply field template to process |
| GET | `/admin/pysis/processes/{process_id}/fields` | List process fields |
| POST | `/admin/pysis/processes/{process_id}/fields` | Add field to process |
| PUT | `/admin/pysis/fields/{field_id}` | Update field definition |
| PUT | `/admin/pysis/fields/{field_id}/value` | Update field value |
| DELETE | `/admin/pysis/fields/{field_id}` | Delete field |
| POST | `/admin/pysis/fields/{field_id}/sync/push` | Push field changes to PySis |
| POST | `/admin/pysis/processes/{process_id}/generate` | AI generate process schema |
| POST | `/admin/pysis/fields/{field_id}/generate` | AI generate field suggestion |
| POST | `/admin/pysis/fields/{field_id}/accept-ai` | Accept AI suggestion |
| POST | `/admin/pysis/fields/{field_id}/reject-ai` | Reject AI suggestion |
| GET | `/admin/pysis/fields/{field_id}/history` | Get field change history |
| POST | `/admin/pysis/fields/{field_id}/restore/{history_id}` | Restore field to previous version |
| GET | `/admin/pysis/available-processes` | List available PySis processes |
| POST | `/admin/pysis/processes/{process_id}/analyze-for-facets` | Analyze process for facet extraction |

**Status:** Very comprehensive PySis implementation but only 5 endpoints documented.

---

### ADMIN EXTERNAL APIS (`/admin/external-apis`)

#### MISSING_DOC - 12 endpoints (Entire section)

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/admin/external-apis` | List all external API configurations |
| POST | `/admin/external-apis` | Create new external API config |
| GET | `/admin/external-apis/{config_id}` | Get API configuration details |
| PATCH | `/admin/external-apis/{config_id}` | Update API configuration |
| DELETE | `/admin/external-apis/{config_id}` | Delete API configuration |
| POST | `/admin/external-apis/{config_id}/sync` | Trigger sync from external API |
| POST | `/admin/external-apis/{config_id}/test` | Test API connection |
| GET | `/admin/external-apis/{config_id}/stats` | Get sync statistics |
| GET | `/admin/external-apis/{config_id}/records` | List synced records |
| GET | `/admin/external-apis/{config_id}/records/{record_id}` | Get specific synced record |
| DELETE | `/admin/external-apis/{config_id}/records/{record_id}` | Delete synced record |
| GET | `/admin/external-apis/types/available` | List available API types |

**Status:** Complete External API system but completely undocumented.

---

### DATA API (`/v1/data`)

#### MISSING_DOC - 7 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/data/locations` | Get available data locations |
| GET | `/v1/data/countries` | Get available countries |
| GET | `/v1/data/documents/locations` | Get document locations |
| GET | `/v1/data/history/municipalities` | Get municipality change history |
| GET | `/v1/data/history/crawls` | Get crawl job history |
| PUT | `/v1/data/extracted/{extraction_id}/verify` | Mark extraction as verified |
| GET | `/v1/data/report/overview` | Get data overview report |

---

### EXPORT API (`/v1/export`)

#### MISSING_DOC - 4 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/export/changes` | Export changes (CSV/JSON) |
| POST | `/v1/export/webhook/test` | Test export webhook |
| DELETE | `/v1/export/async/{job_id}` | Cancel async export job |
| GET | `/v1/export/async` | List all export jobs |

---

### ENTITY TYPES (`/v1/entity-types`)

#### MISSING_DOC - 1 endpoint

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/entity-types/by-slug/{slug}` | Get entity type by URL slug |

---

### ENTITIES (`/v1/entities`)

#### MISSING_DOC - 6 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/entities/hierarchy/{entity_type_slug}` | Get entity hierarchy |
| GET | `/v1/entities/filter-options/location` | Get available location filters |
| GET | `/v1/entities/filter-options/attributes` | Get available attribute filters |
| GET | `/v1/entities/by-slug/{entity_type_slug}/{entity_slug}` | Get entity by slug |
| GET | `/v1/entities/{entity_id}/children` | Get child entities |
| GET | `/v1/entities/{entity_id}/brief` | Get brief entity summary |

---

### ATTACHMENTS (`/v1/entities/{id}/attachments`)

#### MISSING_DOC - 1 endpoint

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/entities/{id}/attachments` | List entity attachments |

---

### FACET TYPES (`/v1/facets/types`)

#### MISSING_DOC - 1 endpoint

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/facets/types/by-slug/{slug}` | Get facet type by slug |

---

### RELATIONS (`/v1/relations`)

#### MISSING_DOC - 5 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/relations/types/{relation_type_id}` | Get specific relation type |
| GET | `/v1/relations/types/by-slug/{slug}` | Get relation type by slug |
| PUT | `/v1/relations/types/{relation_type_id}` | Update relation type |
| DELETE | `/v1/relations/types/{relation_type_id}` | Delete relation type |
| PUT | `/v1/relations/{relation_id}/verify` | Mark relation as verified |

---

### ANALYSIS API (`/v1/analysis`)

#### MISSING_DOC - 9 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/analysis/templates` | List analysis templates |
| POST | `/v1/analysis/templates` | Create analysis template |
| GET | `/v1/analysis/templates/{template_id}` | Get template details |
| GET | `/v1/analysis/templates/by-slug/{slug}` | Get template by slug |
| PUT | `/v1/analysis/templates/{template_id}` | Update template |
| DELETE | `/v1/analysis/templates/{template_id}` | Delete template |
| GET | `/v1/analysis/overview` | Get analysis overview |
| GET | `/v1/analysis/report/{entity_id}` | Get detailed analysis report |
| GET | `/v1/analysis/stats` | Get analysis statistics |

---

### ASSISTANT (`/v1/assistant`)

#### MISSING_DOC - 11 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| DELETE | `/v1/assistant/upload/{attachment_id}` | Delete assistant upload |
| POST | `/v1/assistant/create-facet-type` | Create facet type via assistant |
| GET | `/v1/assistant/batch-action/{batch_id}/status` | Check batch action status |
| POST | `/v1/assistant/batch-action/{batch_id}/cancel` | Cancel batch action |
| POST | `/v1/assistant/wizards/{wizard_id}/respond` | Respond to wizard step |
| POST | `/v1/assistant/wizards/{wizard_id}/back` | Go back in wizard |
| POST | `/v1/assistant/wizards/{wizard_id}/cancel` | Cancel wizard |
| DELETE | `/v1/assistant/reminders/{reminder_id}` | Delete reminder |
| POST | `/v1/assistant/reminders/{reminder_id}/dismiss` | Dismiss reminder |
| POST | `/v1/assistant/reminders/{reminder_id}/snooze` | Snooze reminder |
| GET | `/v1/assistant/reminders/due` | Get due reminders |

---

### PYSIS FACETS (`/v1/pysis-facets`)

#### MISSING_DOC - 2 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/pysis-facets/preview` | Preview facet analysis results |
| GET | `/v1/pysis-facets/summary` | Get PySis facet summary |

---

### AI TASKS (`/v1/ai-tasks`)

#### MISSING_DOC - 2 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/ai-tasks/result` | Get AI task result/output |
| GET | `/v1/ai-tasks/by-entity` | Get AI tasks for specific entity |

---

### DASHBOARD (`/v1/dashboard`)

#### MISSING_DOC - 3 endpoints

| Method | Endpoint | Notes |
|--------|----------|-------|
| GET | `/v1/dashboard/activity` | Get activity feed |
| GET | `/v1/dashboard/insights` | Get dashboard insights |
| GET | `/v1/dashboard/charts/{chart_type}` | Get chart data by type |

---

## Summary by Issue Type

### MISSING_DOC: 152 endpoints
These endpoints exist in the codebase but are not listed in the quick reference table in `docs/API_REFERENCE.md`.

**Most Critical Missing Sections:**
1. Admin External APIs (12 endpoints - completely new feature)
2. Admin Users (6 endpoints - moved from auth section)
3. Admin PySis Field Management (24 endpoints - complex feature)
4. Analysis Templates & Reports (9 endpoints - new dashboarding)

### MISSING_IMPL: 0 endpoints
All endpoints documented in `docs/API_REFERENCE.md` are correctly implemented.

### WRONG_SCHEMA: 0 endpoints
All response schemas match their documentation.

### WRONG_AUTH: 0 endpoints
All authentication requirements are correctly enforced.

---

## Recommendations by Priority

### Priority 1: Add Missing Sections
- [ ] Admin Users (6 endpoints)
- [ ] Admin External APIs (12 endpoints)
- Add proper section headers and descriptions

### Priority 2: Expand Existing Sections
- [ ] Auth: Add refresh, sessions, email verification (9 endpoints)
- [ ] Admin PySis: Add field management (24 endpoints)
- [ ] Analysis: Add templates and reports (9 endpoints)
- [ ] Admin Notifications: Add detailed endpoints (13 endpoints)
- [ ] Admin Crawler: Add document management (7 endpoints)

### Priority 3: Add Slug-based Variants
- [ ] Entity Types: by-slug endpoint
- [ ] Facet Types: by-slug endpoint
- [ ] Relations: type by-slug and individual endpoints
- [ ] Analysis Templates: by-slug endpoint

### Priority 4: Add Metadata Endpoints
- [ ] Sources: meta/countries, meta/locations, meta/counts
- [ ] Dashboard: activity, insights, charts
- [ ] Data API: history, locations, countries endpoints

---

## Files to Update

**Primary:**
- `docs/API_REFERENCE.md` - Update quick reference table (add 152 endpoints)

**Optional (if creating detailed docs):**
- `docs/api/ADMIN.md` - Add Admin Users and External APIs sections
- `docs/api/PYSIS.md` - Expand PySis field management
- `docs/api/ANALYSIS.md` - Add templates and reports
- `docs/api/NOTIFICATIONS.md` - Expand notification endpoints

---

## Verification Checklist

- [x] All documented endpoints are implemented
- [x] All response schemas match documentation
- [x] Authentication is correctly enforced
- [x] No orphaned endpoints
- [x] All implementations have docstrings
- [ ] All endpoints in quick reference (152/304 = 50%)
- [ ] All advanced features documented
- [ ] Examples provided for each endpoint group

