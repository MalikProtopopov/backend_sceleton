# Tenants & Settings API

> Multi-tenant configuration, feature flags, and system settings

---

## Overview

The Tenants module provides multi-tenancy support with:
- Tenant management (organizations/clients)
- Tenant-specific settings (locale, timezone, notifications)
- Feature flags for enabling/disabling modules per tenant
- Branding customization (logo, colors)

---

## Tenant Entity

### Core Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `name` | string | Organization name (1-255 chars) |
| `slug` | string | URL-friendly identifier (2-100 chars, unique) |
| `domain` | string | Custom domain (optional, unique) |
| `is_active` | boolean | Tenant active status |
| `contact_email` | string | Primary contact email |
| `contact_phone` | string | Primary contact phone |
| `logo_url` | string | Logo image URL (max 500 chars) |
| `primary_color` | string | Brand color in `#RRGGBB` format |
| `extra_data` | object | Custom JSON metadata |
| `version` | integer | Optimistic locking version |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `deleted_at` | datetime | Soft delete timestamp |

### Tenant Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_locale` | string | `ru` | Default content locale |
| `timezone` | string | `Europe/Moscow` | Timezone for dates |
| `date_format` | string | `DD.MM.YYYY` | Date display format |
| `time_format` | string | `HH:mm` | Time display format |
| `notify_on_inquiry` | boolean | `true` | Send notifications on new leads |
| `inquiry_email` | string | - | Email for lead notifications |
| `telegram_chat_id` | string | - | Telegram chat for notifications |
| `default_og_image` | string | - | Default Open Graph image URL |
| `ga_tracking_id` | string | - | Google Analytics ID |
| `ym_counter_id` | string | - | Yandex Metrika counter ID |

---

## Admin Endpoints

### GET /api/v1/tenants

List all tenants with pagination.

**Authentication:** Super admin only (no tenant context)

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page |
| `isActive` | boolean | - | Filter by active status |

**Example Request:**
```bash
GET /api/v1/tenants?page=1&pageSize=20&isActive=true
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "tenant-uuid-1",
      "name": "Mediann Law Firm",
      "slug": "mediann",
      "domain": "mediann.ru",
      "is_active": true,
      "contact_email": "admin@mediann.ru",
      "contact_phone": "+7 (495) 123-45-67",
      "logo_url": "https://cdn.example.com/logos/mediann.png",
      "primary_color": "#1E40AF",
      "extra_data": { "plan": "enterprise" },
      "version": 3,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2026-01-10T15:30:00Z",
      "settings": {
        "id": "settings-uuid",
        "tenant_id": "tenant-uuid-1",
        "default_locale": "ru",
        "timezone": "Europe/Moscow",
        "date_format": "DD.MM.YYYY",
        "time_format": "HH:mm",
        "notify_on_inquiry": true,
        "inquiry_email": "leads@mediann.ru",
        "telegram_chat_id": "-1001234567890",
        "default_og_image": "https://cdn.example.com/og/default.jpg",
        "ga_tracking_id": "G-XXXXXXXXXX",
        "ym_counter_id": "12345678",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2026-01-10T15:30:00Z"
      }
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/v1/tenants

Create a new tenant.

**Authentication:** Super admin only

**Request Body:**
```json
{
  "name": "New Company",
  "slug": "new-company",
  "domain": "newcompany.com",
  "is_active": true,
  "contact_email": "admin@newcompany.com",
  "contact_phone": "+7 (495) 987-65-43",
  "logo_url": "https://cdn.example.com/logos/new-company.png",
  "primary_color": "#059669"
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | 1-255 chars |
| `slug` | string | Yes | 2-100 chars, lowercase, alphanumeric with hyphens, unique |
| `domain` | string | No | Max 255 chars, unique |
| `is_active` | boolean | No | Default: true |
| `contact_email` | string | No | Max 255 chars |
| `contact_phone` | string | No | Max 50 chars |
| `logo_url` | string | No | Max 500 chars |
| `primary_color` | string | No | Format: `#RRGGBB` |

**Success Response (201):**
```json
{
  "id": "new-tenant-uuid",
  "name": "New Company",
  "slug": "new-company",
  "domain": "newcompany.com",
  "is_active": true,
  "version": 1,
  "created_at": "2026-01-14T14:00:00Z",
  "updated_at": "2026-01-14T14:00:00Z",
  "settings": null
}
```

**Error Response (409):**
```json
{
  "type": "https://api.cms.local/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Tenant with slug 'new-company' already exists"
}
```

**Error Response (422):**
```json
{
  "type": "https://api.cms.local/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed",
  "errors": [
    {
      "loc": ["body", "slug"],
      "msg": "Slug must contain only lowercase letters, numbers, and hyphens",
      "type": "value_error"
    }
  ]
}
```

---

### GET /api/v1/tenants/{tenant_id}

Get tenant by ID.

**Authentication:** Super admin or tenant admin

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `tenant_id` | UUID | Tenant ID |

**Success Response (200):** Same structure as list item.

**Error Response (404):**
```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Tenant not found"
}
```

---

### PATCH /api/v1/tenants/{tenant_id}

Update tenant.

**Authentication:** Super admin or tenant admin

**Request Body:**
```json
{
  "name": "Updated Company Name",
  "is_active": true,
  "contact_email": "new-email@company.com",
  "primary_color": "#DC2626",
  "version": 3
}
```

**Note:** 
- `version` field is required for optimistic locking
- `slug` cannot be changed after creation

**Success Response (200):** Updated tenant object.

**Error Response (409):**
```json
{
  "type": "https://api.cms.local/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Version mismatch: expected 4, got 3"
}
```

---

### DELETE /api/v1/tenants/{tenant_id}

Soft delete a tenant.

**Authentication:** Super admin only

**Response:** `204 No Content`

**Behavior:**
- Sets `deleted_at` timestamp
- All tenant data remains but is excluded from queries
- Associated users are deactivated

---

## Tenant Settings

### PUT /api/v1/tenants/{tenant_id}/settings

Update tenant settings.

**Authentication:** Tenant admin with `settings:update` permission

**Request Body:**
```json
{
  "default_locale": "ru",
  "timezone": "Europe/Moscow",
  "date_format": "DD.MM.YYYY",
  "time_format": "HH:mm",
  "notify_on_inquiry": true,
  "inquiry_email": "leads@company.com",
  "telegram_chat_id": "-1001234567890",
  "default_og_image": "https://cdn.example.com/og/default.jpg",
  "ga_tracking_id": "G-XXXXXXXXXX",
  "ym_counter_id": "12345678"
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `default_locale` | string | No | 2-5 chars, format: `xx` or `xx-XX` |
| `timezone` | string | No | Max 50 chars, valid IANA timezone |
| `date_format` | string | No | Max 20 chars |
| `time_format` | string | No | Max 10 chars |
| `notify_on_inquiry` | boolean | No | - |
| `inquiry_email` | string | No | Valid email, max 255 chars |
| `telegram_chat_id` | string | No | Max 50 chars |
| `default_og_image` | string | No | Max 500 chars |
| `ga_tracking_id` | string | No | Max 50 chars |
| `ym_counter_id` | string | No | Max 20 chars |

**Success Response (200):**
```json
{
  "id": "settings-uuid",
  "tenant_id": "tenant-uuid",
  "default_locale": "ru",
  "timezone": "Europe/Moscow",
  "date_format": "DD.MM.YYYY",
  "time_format": "HH:mm",
  "notify_on_inquiry": true,
  "inquiry_email": "leads@company.com",
  "telegram_chat_id": "-1001234567890",
  "default_og_image": "https://cdn.example.com/og/default.jpg",
  "ga_tracking_id": "G-XXXXXXXXXX",
  "ym_counter_id": "12345678",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2026-01-14T14:30:00Z"
}
```

---

## Feature Flags

Feature flags allow enabling/disabling modules per tenant.

### Available Features

| Feature Name | Description |
|--------------|-------------|
| `cases_module` | Case studies / portfolio module |
| `reviews_module` | Client testimonials module |
| `seo_advanced` | Advanced SEO features (custom meta, redirects) |
| `multilang` | Multi-language content support |
| `analytics_advanced` | Detailed lead analytics (UTM, device, geo) |
| `blog_module` | Blog / articles module |
| `faq_module` | FAQ module |
| `team_module` | Team / employees module |

### GET /api/v1/feature-flags

List all feature flags for a tenant.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |

**Example Request:**
```bash
GET /api/v1/feature-flags?tenant_id={uuid}
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "flag-uuid-1",
      "tenant_id": "tenant-uuid",
      "feature_name": "cases_module",
      "enabled": true,
      "description": "Case studies / portfolio module",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2026-01-10T12:00:00Z"
    },
    {
      "id": "flag-uuid-2",
      "tenant_id": "tenant-uuid",
      "feature_name": "multilang",
      "enabled": false,
      "description": null,
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-01T00:00:00Z"
    }
  ],
  "available_features": {
    "cases_module": "Case studies / portfolio module",
    "reviews_module": "Client testimonials module",
    "seo_advanced": "Advanced SEO features (custom meta per page, redirects)",
    "multilang": "Multi-language content support",
    "analytics_advanced": "Detailed lead analytics (UTM, device, geo)",
    "blog_module": "Blog / articles module",
    "faq_module": "FAQ module",
    "team_module": "Team / employees module"
  }
}
```

---

### PATCH /api/v1/feature-flags/{feature_name}

Enable or disable a feature flag.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `feature_name` | string | Feature name (e.g., `cases_module`) |

**Request Body:**
```json
{
  "enabled": true
}
```

**Success Response (200):**
```json
{
  "id": "flag-uuid",
  "tenant_id": "tenant-uuid",
  "feature_name": "cases_module",
  "enabled": true,
  "description": "Case studies / portfolio module",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2026-01-14T14:45:00Z"
}
```

**Error Response (404):**
```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Feature flag 'unknown_feature' not found"
}
```

---

## Business Logic

### Tenant Lifecycle

```
┌────────────┐     ┌────────────┐     ┌────────────┐
│   ACTIVE   │────▶│  INACTIVE  │────▶│  DELETED   │
└────────────┘     └────────────┘     └────────────┘
      │                  │                  │
      │                  │                  │
      ▼                  ▼                  ▼
  Full access        Read-only          Hidden
```

### Tenant Deactivation Effects

When `is_active` is set to `false`:
- Users cannot log in
- API requests return 401/403
- Public content remains accessible (if cached)
- Admin panel access blocked

### Feature Flag Behavior

Feature flags control module visibility and functionality:

```javascript
// Frontend feature check
const isFeatureEnabled = (tenant, featureName) => {
  const flag = tenant.feature_flags.find(f => f.feature_name === featureName)
  return flag?.enabled ?? false
}

// Show/hide navigation based on features
const getNavItems = (tenant) => {
  const items = [
    { name: 'Dashboard', path: '/dashboard', always: true },
    { name: 'Articles', path: '/articles', feature: 'blog_module' },
    { name: 'Cases', path: '/cases', feature: 'cases_module' },
    { name: 'Reviews', path: '/reviews', feature: 'reviews_module' },
    { name: 'Team', path: '/team', feature: 'team_module' },
    { name: 'FAQ', path: '/faq', feature: 'faq_module' },
  ]
  
  return items.filter(item => 
    item.always || isFeatureEnabled(tenant, item.feature)
  )
}
```

---

## Frontend Integration

### Settings Page

```javascript
// Fetch tenant settings
const fetchTenantSettings = async (tenantId) => {
  const { data } = await api.get(`/tenants/${tenantId}`)
  return data
}

// Update settings
const updateSettings = async (tenantId, settings) => {
  const { data } = await api.put(`/tenants/${tenantId}/settings`, settings)
  return data
}

// Update feature flag
const toggleFeature = async (tenantId, featureName, enabled) => {
  const { data } = await api.patch(
    `/feature-flags/${featureName}?tenant_id=${tenantId}`,
    { enabled }
  )
  return data
}
```

### Settings Form Component

```jsx
const SettingsForm = ({ tenant }) => {
  const [settings, setSettings] = useState(tenant.settings)
  const [saving, setSaving] = useState(false)
  
  const handleSave = async () => {
    setSaving(true)
    try {
      await updateSettings(tenant.id, settings)
      toast.success('Settings saved successfully')
    } catch (error) {
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }
  
  return (
    <form onSubmit={handleSave}>
      {/* Localization */}
      <section>
        <h3>Localization</h3>
        <Select
          label="Default Language"
          value={settings.default_locale}
          onChange={(v) => setSettings({ ...settings, default_locale: v })}
          options={[
            { value: 'ru', label: 'Russian' },
            { value: 'en', label: 'English' },
          ]}
        />
        <Select
          label="Timezone"
          value={settings.timezone}
          onChange={(v) => setSettings({ ...settings, timezone: v })}
          options={timezoneOptions}
        />
      </section>
      
      {/* Notifications */}
      <section>
        <h3>Notifications</h3>
        <Toggle
          label="Notify on new inquiry"
          checked={settings.notify_on_inquiry}
          onChange={(v) => setSettings({ ...settings, notify_on_inquiry: v })}
        />
        <Input
          label="Notification Email"
          type="email"
          value={settings.inquiry_email || ''}
          onChange={(v) => setSettings({ ...settings, inquiry_email: v })}
        />
        <Input
          label="Telegram Chat ID"
          value={settings.telegram_chat_id || ''}
          onChange={(v) => setSettings({ ...settings, telegram_chat_id: v })}
        />
      </section>
      
      {/* Analytics */}
      <section>
        <h3>Analytics</h3>
        <Input
          label="Google Analytics ID"
          placeholder="G-XXXXXXXXXX"
          value={settings.ga_tracking_id || ''}
          onChange={(v) => setSettings({ ...settings, ga_tracking_id: v })}
        />
        <Input
          label="Yandex Metrika ID"
          placeholder="12345678"
          value={settings.ym_counter_id || ''}
          onChange={(v) => setSettings({ ...settings, ym_counter_id: v })}
        />
      </section>
      
      <Button type="submit" loading={saving}>
        Save Settings
      </Button>
    </form>
  )
}
```

### Feature Flags Management

```jsx
const FeatureFlagsManager = ({ tenant }) => {
  const [flags, setFlags] = useState([])
  const [availableFeatures, setAvailableFeatures] = useState({})
  
  useEffect(() => {
    fetchFeatureFlags(tenant.id).then(({ items, available_features }) => {
      setFlags(items)
      setAvailableFeatures(available_features)
    })
  }, [tenant.id])
  
  const handleToggle = async (featureName, currentEnabled) => {
    try {
      const updated = await toggleFeature(tenant.id, featureName, !currentEnabled)
      setFlags(flags.map(f => 
        f.feature_name === featureName ? updated : f
      ))
    } catch (error) {
      toast.error('Failed to update feature')
    }
  }
  
  return (
    <div>
      <h2>Feature Flags</h2>
      <p>Enable or disable modules for this tenant.</p>
      
      <div className="feature-list">
        {Object.entries(availableFeatures).map(([name, description]) => {
          const flag = flags.find(f => f.feature_name === name)
          const isEnabled = flag?.enabled ?? false
          
          return (
            <div key={name} className="feature-item">
              <div>
                <strong>{name}</strong>
                <p>{description}</p>
              </div>
              <Toggle
                checked={isEnabled}
                onChange={() => handleToggle(name, isEnabled)}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

---

## Security Considerations

### Tenant Isolation

- All data queries include `tenant_id` filter
- Users can only access data within their tenant
- Super admins can access all tenants

### Permission Requirements

| Action | Required Permission |
|--------|---------------------|
| List tenants | Super admin |
| Create tenant | Super admin |
| View own tenant | Any authenticated user |
| Update tenant | `settings:update` or super admin |
| Delete tenant | Super admin |
| Update settings | `settings:update` |
| Manage feature flags | `settings:update` |

### Rate Limiting

Tenant management endpoints are rate-limited:
- List: 60 requests/minute
- Create/Update: 30 requests/minute
- Feature flags: 60 requests/minute

