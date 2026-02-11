# Platform Owner Dashboard — Frontend Integration Guide

> **Audience:** Admin-panel frontend (React / Next.js).
> These endpoints are visible **only** to users with `is_superuser=true` or `role.name = "platform_owner"`.

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Base URL & Headers](#2-base-url--headers)
3. [Endpoints Reference](#3-endpoints-reference)
   - 3.1 [Platform Overview](#31-get-apiv1adminplatformoverview)
   - 3.2 [Tenants Table](#32-get-apiv1adminplatformtenants)
   - 3.3 [Tenant Details](#33-get-apiv1adminplatformtenantstenant_iddetails)
   - 3.4 [Trends](#34-get-apiv1adminplatformtrends)
   - 3.5 [Health Alerts](#35-get-apiv1adminplatformalerts)
4. [Recommended Page Layout](#4-recommended-page-layout)
5. [Data Loading Strategy](#5-data-loading-strategy)
6. [Charts & Graphs](#6-charts--graphs)
7. [Tenants Table Configuration](#7-tenants-table-configuration)
8. [Tenant Drill-Down Page](#8-tenant-drill-down-page)
9. [Health Alerts UI](#9-health-alerts-ui)
10. [TypeScript Types](#10-typescript-types)
11. [Error Handling](#11-error-handling)

---

## 1. Authentication

All platform dashboard endpoints require a valid JWT token and platform-level privileges.

```
Authorization: Bearer <access_token>
```

If the current user is **not** a superuser or platform_owner, the API returns:

```json
{
  "type": "https://api.cms.local/errors/permission_denied",
  "title": "Permission Denied",
  "status": 403,
  "detail": "Required permission: platform:*"
}
```

**Frontend logic:** Show the "Platform Dashboard" menu item only when:
```typescript
const canSeePlatformDashboard =
  currentUser.is_superuser || currentUser.role?.name === 'platform_owner';
```

---

## 2. Base URL & Headers

```
Base URL:  https://<api-domain>/api/v1/admin
Headers:
  Authorization: Bearer <token>
  Content-Type: application/json
```

---

## 3. Endpoints Reference

### 3.1 `GET /api/v1/admin/platform/overview`

**Purpose:** Top-level summary cards for the platform dashboard main screen.

**Query parameters:** none

**Response** `200 OK`:

```json
{
  "total_tenants": 12,
  "active_tenants": 10,
  "inactive_tenants": 2,
  "total_users": 47,
  "active_users": 38,
  "total_inquiries": 1253,
  "inquiries_this_month": 89,
  "inquiries_prev_month": 102,
  "inactive_tenants_30d": 3
}
```

| Field                  | Type  | Description                                   |
|------------------------|-------|-----------------------------------------------|
| `total_tenants`        | int   | All non-deleted tenants                       |
| `active_tenants`       | int   | `is_active = true`                            |
| `inactive_tenants`     | int   | `is_active = false`                           |
| `total_users`          | int   | All non-deleted admin users across tenants    |
| `active_users`         | int   | `is_active = true` users                      |
| `total_inquiries`      | int   | All non-deleted inquiries across all tenants  |
| `inquiries_this_month` | int   | Created in current calendar month             |
| `inquiries_prev_month` | int   | Created in previous calendar month            |
| `inactive_tenants_30d` | int   | Active tenants with no user login for >30 days|

---

### 3.2 `GET /api/v1/admin/platform/tenants`

**Purpose:** Paginated table of all tenants with aggregated metrics.

**Query parameters:**

| Param      | Type   | Default      | Description                                                                 |
|------------|--------|--------------|-----------------------------------------------------------------------------|
| `page`     | int    | `1`          | Page number (>= 1)                                                         |
| `per_page` | int    | `25`         | Items per page (1–100)                                                     |
| `sort_by`  | string | `created_at` | One of: `name`, `slug`, `created_at`, `is_active`, `users_count`, `content_count`, `inquiries_total`, `inquiries_this_month`, `last_login_at`, `enabled_features_count` |
| `sort_dir` | string | `desc`       | `asc` or `desc`                                                            |
| `search`   | string | `null`       | Case-insensitive search in `name`, `slug`, `domain` (max 200 chars)        |

**Response** `200 OK`:

```json
{
  "items": [
    {
      "id": "uuid",
      "name": "Acme Corp",
      "slug": "acme-corp",
      "domain": "acme.example.com",
      "is_active": true,
      "created_at": "2025-06-15T10:30:00Z",
      "users_count": 5,
      "active_users_count": 4,
      "content_count": 23,
      "articles_count": 12,
      "cases_count": 5,
      "services_count": 6,
      "inquiries_total": 156,
      "inquiries_this_month": 12,
      "inquiries_new": 3,
      "last_login_at": "2026-02-10T14:22:00Z",
      "enabled_features_count": 7,
      "enabled_features": ["blog_module", "cases_module", "reviews_module", "faq_module", "team_module", "services_module", "multilang"]
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 25,
  "pages": 1
}
```

| Field (per item)         | Type        | Description                                          |
|--------------------------|-------------|------------------------------------------------------|
| `id`                     | UUID        | Tenant ID                                            |
| `name`                   | string      | Tenant display name                                  |
| `slug`                   | string      | URL-safe identifier                                  |
| `domain`                 | string?     | Custom domain (can be null)                          |
| `is_active`              | bool        | Tenant active status                                 |
| `created_at`             | datetime    | Registration date                                    |
| `users_count`            | int         | Total admin users in tenant                          |
| `active_users_count`     | int         | Active admin users                                   |
| `content_count`          | int         | Total published (articles + cases + services)        |
| `articles_count`         | int         | Published articles                                   |
| `cases_count`            | int         | Published cases                                      |
| `services_count`         | int         | Published services                                   |
| `inquiries_total`        | int         | All inquiries ever                                   |
| `inquiries_this_month`   | int         | Inquiries created this month                         |
| `inquiries_new`          | int         | Unprocessed inquiries (status = "new")               |
| `last_login_at`          | datetime?   | Most recent login among all tenant users             |
| `enabled_features_count` | int         | Number of enabled feature flags                      |
| `enabled_features`       | string[]    | List of enabled feature flag names                   |

---

### 3.3 `GET /api/v1/admin/platform/tenants/{tenant_id}/details`

**Purpose:** Full drill-down statistics for a single tenant.

**Path parameters:** `tenant_id` (UUID)

**Response** `200 OK`:

```json
{
  "tenant_id": "uuid",
  "tenant_name": "Acme Corp",
  "tenant_slug": "acme-corp",
  "is_active": true,
  "content": {
    "articles": { "published": 12, "draft": 3, "archived": 1 },
    "cases": { "published": 5, "draft": 2, "archived": 0 },
    "documents": { "published": 8, "draft": 1, "archived": 0 },
    "services": 6,
    "services_total": 8,
    "employees": 10,
    "employees_total": 12,
    "faqs": 15,
    "faqs_total": 18,
    "reviews": { "pending": 2, "approved": 20, "rejected": 1 }
  },
  "inquiries": {
    "total": 156,
    "by_status": { "new": 3, "in_progress": 5, "contacted": 12, "completed": 130, "spam": 6 },
    "by_utm_source": { "google": 80, "facebook": 30, "direct": 46 },
    "by_device_type": { "desktop": 90, "mobile": 55, "tablet": 11 },
    "by_country_top10": [
      { "country": "Russia", "count": 95 },
      { "country": "Kazakhstan", "count": 30 }
    ],
    "top_pages": [
      { "page": "/services/consulting", "count": 45 },
      { "page": "/contacts", "count": 38 }
    ],
    "avg_processing_hours": 4.2
  },
  "feature_flags": [
    { "feature_name": "blog_module", "enabled": true },
    { "feature_name": "cases_module", "enabled": true },
    { "feature_name": "seo_advanced", "enabled": false }
  ],
  "users": [
    {
      "id": "uuid",
      "email": "admin@acme.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_active": true,
      "role_name": "admin",
      "last_login_at": "2026-02-10T14:22:00Z"
    }
  ],
  "recent_activity": [
    {
      "id": "uuid",
      "action": "update",
      "resource_type": "Article",
      "resource_id": "uuid",
      "user_email": "admin@acme.com",
      "created_at": "2026-02-10T14:20:00Z"
    }
  ]
}
```

**Error** `404 Not Found` — if `tenant_id` does not exist.

---

### 3.4 `GET /api/v1/admin/platform/trends`

**Purpose:** Time-series data for platform graphs.

**Query parameters:**

| Param  | Type | Default | Description                  |
|--------|------|---------|------------------------------|
| `days` | int  | `90`    | Look-back period (7–365)     |

**Response** `200 OK`:

```json
{
  "new_tenants_by_month": [
    { "date": "2025-12", "value": 2 },
    { "date": "2026-01", "value": 3 },
    { "date": "2026-02", "value": 1 }
  ],
  "new_users_by_month": [
    { "date": "2025-12", "value": 5 },
    { "date": "2026-01", "value": 8 }
  ],
  "inquiries_by_day": [
    { "date": "2026-02-01", "value": 12 },
    { "date": "2026-02-02", "value": 8 }
  ],
  "logins_by_day": [
    { "date": "2026-02-01", "value": 15 },
    { "date": "2026-02-02", "value": 11 }
  ],
  "inquiries_by_tenant": [
    {
      "tenant_id": "uuid",
      "tenant_name": "Acme Corp",
      "data": [
        { "date": "2026-02-01", "value": 5 },
        { "date": "2026-02-02", "value": 3 }
      ]
    }
  ]
}
```

| Field                   | Type            | Description                                      |
|-------------------------|-----------------|--------------------------------------------------|
| `new_tenants_by_month`  | TrendPoint[]    | Tenants created, grouped by month (YYYY-MM)      |
| `new_users_by_month`    | TrendPoint[]    | Users created, grouped by month                  |
| `inquiries_by_day`      | TrendPoint[]    | Inquiries created, grouped by day (YYYY-MM-DD)   |
| `logins_by_day`         | TrendPoint[]    | Login events from audit log, grouped by day      |
| `inquiries_by_tenant`   | TenantSeries[]  | Top 10 tenants by volume, daily breakdown        |

---

### 3.5 `GET /api/v1/admin/platform/alerts`

**Purpose:** Health alerts for proactive management.

**Query parameters:** none

**Response** `200 OK`:

```json
{
  "alerts": [
    {
      "type": "stale_inquiries",
      "severity": "critical",
      "tenant_id": "uuid",
      "tenant_name": "Acme Corp",
      "message": "5 unprocessed inquiries older than 3 days",
      "details": { "count": 5 }
    },
    {
      "type": "inactive_tenant",
      "severity": "warning",
      "tenant_id": "uuid",
      "tenant_name": "Beta Inc",
      "message": "No user login for >14 days",
      "details": { "last_login": "2026-01-15T10:00:00Z" }
    },
    {
      "type": "empty_tenant",
      "severity": "info",
      "tenant_id": "uuid",
      "tenant_name": "New Co",
      "message": "No published content (articles, cases, or services)",
      "details": null
    }
  ],
  "summary": {
    "critical": 1,
    "warning": 1,
    "info": 1
  }
}
```

**Alert types:**

| `type`                 | `severity` | Trigger                                             |
|------------------------|------------|-----------------------------------------------------|
| `stale_inquiries`      | critical   | Tenant has `status=new` inquiries older than 3 days |
| `inactive_tenant`      | warning    | No user logged in for >14 days                      |
| `high_spam_ratio`      | warning    | >50% of inquiries are spam (minimum 5 total)        |
| `declining_inquiries`  | warning    | This month's inquiries dropped >50% vs previous     |
| `empty_tenant`         | info       | Zero published articles, cases, or services          |
| `low_feature_adoption` | info       | Fewer than 3 features enabled                        |

---

## 4. Recommended Page Layout

### Main Dashboard Screen

```
+------------------------------------------------------------------+
|  PLATFORM DASHBOARD                                              |
+------------------------------------------------------------------+
|                                                                  |
|  [Card]          [Card]          [Card]          [Card]          |
|  Tenants: 12     Users: 47       Inquiries:      Inactive:      |
|  Active: 10      Active: 38      This month: 89  30d: 3         |
|  Inactive: 2                     Prev: 102                      |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  [ALERTS BAR]  3 critical  |  1 warning  |  1 info              |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  [Chart: Inquiries by Day — last 90 days]                       |
|  ──────────────────────────────────────                          |
|                                                                  |
+------------------------------------------------------------------+
|                                                                  |
|  [Table: Tenants]                                                |
|  Search: [________________]  Sort: [created_at v] [desc v]      |
|                                                                  |
|  Name   | Status | Users | Content | Inquiries | Last Login | >  |
|  -----  | ------ | ----- | ------- | --------- | ---------- | -  |
|  Acme   | Active |   5   |   23    |   156/12  | 2h ago     | >  |
|  Beta   | Active |   3   |    8    |    42/3   | 15d ago    | >  |
|                                                                  |
+------------------------------------------------------------------+
```

### Tenant Detail Screen (drill-down on row click)

```
+------------------------------------------------------------------+
|  < Back to Dashboard     ACME CORP    [Active]                   |
+------------------------------------------------------------------+
|                                                                  |
|  [Tab: Content]  [Tab: Inquiries]  [Tab: Users]  [Tab: Activity]|
|                                                                  |
|  ---- Content Tab ----                                           |
|  Articles: 12 published / 3 draft / 1 archived                  |
|  Cases:     5 published / 2 draft                                |
|  Documents: 8 published / 1 draft                                |
|  Services:  6 / 8 total                                          |
|  Employees: 10 / 12 total                                        |
|  FAQs:      15 / 18 total                                        |
|  Reviews:   20 approved / 2 pending / 1 rejected                 |
|                                                                  |
|  Feature Flags: blog [on] cases [on] seo_adv [off] ...          |
|                                                                  |
|  ---- Inquiries Tab ----                                         |
|  [Pie: By Status] [Pie: By Device] [Bar: Top UTM Sources]       |
|  [Bar: Top Countries]  [Bar: Top Pages]                          |
|  Avg Processing Time: 4.2 hours                                  |
|                                                                  |
|  ---- Users Tab ----                                             |
|  Email | Name | Role | Active | Last Login                      |
|                                                                  |
|  ---- Activity Tab ----                                          |
|  Timeline of last 20 audit events                                |
+------------------------------------------------------------------+
```

---

## 5. Data Loading Strategy

### Initial Page Load

Load overview and alerts in parallel, then load the table:

```typescript
// Load on mount — parallel requests
const [overview, alerts] = await Promise.all([
  api.get('/admin/platform/overview'),
  api.get('/admin/platform/alerts'),
]);

// Then load table (may depend on default sorting)
const tenantsTable = await api.get('/admin/platform/tenants', {
  params: { page: 1, per_page: 25, sort_by: 'created_at', sort_dir: 'desc' },
});

// Trends can load slightly deferred (below the fold)
const trends = await api.get('/admin/platform/trends', {
  params: { days: 90 },
});
```

### Drill-Down

```typescript
const details = await api.get(`/admin/platform/tenants/${tenantId}/details`);
```

### Refresh Strategy

- **Overview + Alerts:** Refresh every 5 minutes or on tab focus
- **Table:** Refresh when user changes sort/search/page
- **Trends:** Cache for the session, re-fetch only on `days` change
- **Details:** Fetch on navigation, no polling needed

---

## 6. Charts & Graphs

### Recommended Libraries

- **Recharts** (React) or **Chart.js** via `react-chartjs-2`

### Inquiries by Day (Line Chart)

```typescript
// Using Recharts
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

<ResponsiveContainer width="100%" height={300}>
  <LineChart data={trends.inquiries_by_day}>
    <XAxis
      dataKey="date"
      tickFormatter={(d) => new Date(d).toLocaleDateString('ru', { day: '2-digit', month: 'short' })}
    />
    <YAxis />
    <Tooltip />
    <Line type="monotone" dataKey="value" stroke="#4F46E5" strokeWidth={2} dot={false} />
  </LineChart>
</ResponsiveContainer>
```

### New Tenants / Users by Month (Bar Chart)

```typescript
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

// Merge the two series by date
const merged = trends.new_tenants_by_month.map((t) => ({
  date: t.date,
  tenants: t.value,
  users: trends.new_users_by_month.find((u) => u.date === t.date)?.value ?? 0,
}));

<ResponsiveContainer width="100%" height={300}>
  <BarChart data={merged}>
    <XAxis dataKey="date" />
    <YAxis />
    <Tooltip />
    <Legend />
    <Bar dataKey="tenants" fill="#4F46E5" name="New Tenants" />
    <Bar dataKey="users" fill="#10B981" name="New Users" />
  </BarChart>
</ResponsiveContainer>
```

### Inquiries by Status (Donut/Pie)

```typescript
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';

const statusColors: Record<string, string> = {
  new: '#3B82F6',
  in_progress: '#F59E0B',
  contacted: '#8B5CF6',
  completed: '#10B981',
  spam: '#EF4444',
  cancelled: '#6B7280',
};

const statusData = Object.entries(details.inquiries.by_status).map(([status, count]) => ({
  name: status,
  value: count,
}));

<ResponsiveContainer width="100%" height={250}>
  <PieChart>
    <Pie data={statusData} dataKey="value" nameKey="name" innerRadius={60} outerRadius={100}>
      {statusData.map((entry) => (
        <Cell key={entry.name} fill={statusColors[entry.name] || '#6B7280'} />
      ))}
    </Pie>
    <Tooltip />
  </PieChart>
</ResponsiveContainer>
```

### Inquiries by Tenant (Multi-Line)

```typescript
const COLORS = ['#4F46E5', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
                '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'];

<ResponsiveContainer width="100%" height={400}>
  <LineChart>
    <XAxis
      dataKey="date"
      type="category"
      allowDuplicatedCategory={false}
    />
    <YAxis />
    <Tooltip />
    <Legend />
    {trends.inquiries_by_tenant.map((tenant, i) => (
      <Line
        key={tenant.tenant_id}
        data={tenant.data}
        dataKey="value"
        name={tenant.tenant_name}
        stroke={COLORS[i % COLORS.length]}
        dot={false}
      />
    ))}
  </LineChart>
</ResponsiveContainer>
```

---

## 7. Tenants Table Configuration

### Columns

| Column             | Width  | Sort Key                | Render                                |
|--------------------|--------|-------------------------|---------------------------------------|
| Name               | 200px  | `name`                  | Bold text + slug in gray below        |
| Status             | 80px   | `is_active`             | Green/Red badge                       |
| Users              | 80px   | `users_count`           | `{active}/{total}` format             |
| Content            | 100px  | `content_count`         | Total published count                 |
| Inquiries          | 120px  | `inquiries_total`       | `{total} / {this_month} this mo`      |
| New (unprocessed)  | 80px   | —                       | Red badge if > 0                      |
| Last Login         | 120px  | `last_login_at`         | Relative time (e.g. "2h ago")         |
| Features           | 80px   | `enabled_features_count`| `{count}/9` with progress bar         |
| Actions            | 60px   | —                       | "Details" button / row click          |

### Row Click

Navigate to detail page: `/platform/tenants/{id}`

### Conditional Formatting

```typescript
// Highlight rows with issues
const getRowClassName = (row: TenantRow) => {
  if (!row.is_active) return 'bg-gray-50 opacity-60';
  if (row.inquiries_new > 0) return 'border-l-4 border-red-400';
  if (row.last_login_at && daysSince(row.last_login_at) > 14) return 'border-l-4 border-yellow-400';
  return '';
};
```

---

## 8. Tenant Drill-Down Page

### URL Pattern

```
/admin/platform/tenants/:tenantId
```

### Tabs

| Tab        | Data Source                       | Widgets                                                                     |
|------------|----------------------------------|-----------------------------------------------------------------------------|
| Content    | `details.content`                | Status cards per type, feature flag toggle display                          |
| Inquiries  | `details.inquiries`              | Donut (status), Bars (UTM, device, country, pages), KPI card (avg time)    |
| Users      | `details.users`                  | Simple table: email, name, role, active, last login                         |
| Activity   | `details.recent_activity`        | Timeline list: icon by action, resource link, timestamp, user email         |

### Content Tab — Feature Flags Display

```typescript
<div className="flex flex-wrap gap-2">
  {details.feature_flags.map((flag) => (
    <span
      key={flag.feature_name}
      className={`px-2 py-1 rounded text-sm ${
        flag.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
      }`}
    >
      {flag.feature_name.replace(/_/g, ' ')}
    </span>
  ))}
</div>
```

### Inquiries Tab — Avg Processing Time KPI

```typescript
<div className="bg-blue-50 rounded-lg p-4 text-center">
  <div className="text-3xl font-bold text-blue-700">
    {details.inquiries.avg_processing_hours
      ? `${details.inquiries.avg_processing_hours}h`
      : '—'}
  </div>
  <div className="text-sm text-blue-500 mt-1">Avg Response Time</div>
</div>
```

---

## 9. Health Alerts UI

### Alert Bar (main dashboard)

Display a clickable summary bar at the top of the dashboard:

```typescript
const severityConfig = {
  critical: { bg: 'bg-red-100', text: 'text-red-800', icon: 'ExclamationCircle' },
  warning:  { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: 'ExclamationTriangle' },
  info:     { bg: 'bg-blue-100', text: 'text-blue-800', icon: 'InformationCircle' },
};

<div className="flex gap-4 p-3 rounded-lg bg-white border">
  {(['critical', 'warning', 'info'] as const).map((sev) => (
    alerts.summary[sev] > 0 && (
      <span key={sev} className={`px-3 py-1 rounded-full text-sm font-medium ${severityConfig[sev].bg} ${severityConfig[sev].text}`}>
        {alerts.summary[sev]} {sev}
      </span>
    )
  ))}
</div>
```

### Alert List (expandable)

```typescript
{alerts.alerts.map((alert) => (
  <div
    key={`${alert.type}-${alert.tenant_id}`}
    className={`p-4 rounded-lg border-l-4 mb-2 ${
      alert.severity === 'critical' ? 'border-red-500 bg-red-50' :
      alert.severity === 'warning'  ? 'border-yellow-500 bg-yellow-50' :
                                      'border-blue-500 bg-blue-50'
    }`}
  >
    <div className="font-medium">{alert.message}</div>
    {alert.tenant_name && (
      <Link
        to={`/admin/platform/tenants/${alert.tenant_id}`}
        className="text-sm text-blue-600 hover:underline"
      >
        {alert.tenant_name} →
      </Link>
    )}
  </div>
))}
```

### Recommended Actions (tooltip/popover)

| Alert Type              | Suggested Action Button                          |
|-------------------------|--------------------------------------------------|
| `stale_inquiries`       | "View Inquiries" → link to tenant admin panel    |
| `inactive_tenant`       | "Contact Tenant" → show contact email            |
| `empty_tenant`          | "Send Onboarding Guide"                          |
| `low_feature_adoption`  | "Suggest Features" → link to feature flags page  |
| `high_spam_ratio`       | "Review Spam Settings"                           |
| `declining_inquiries`   | "View Inquiry Trends" → link to tenant details   |

---

## 10. TypeScript Types

```typescript
// === Overview ===
interface PlatformOverview {
  total_tenants: number;
  active_tenants: number;
  inactive_tenants: number;
  total_users: number;
  active_users: number;
  total_inquiries: number;
  inquiries_this_month: number;
  inquiries_prev_month: number;
  inactive_tenants_30d: number;
}

// === Tenants Table ===
interface TenantRow {
  id: string;
  name: string;
  slug: string;
  domain: string | null;
  is_active: boolean;
  created_at: string;
  users_count: number;
  active_users_count: number;
  content_count: number;
  articles_count: number;
  cases_count: number;
  services_count: number;
  inquiries_total: number;
  inquiries_this_month: number;
  inquiries_new: number;
  last_login_at: string | null;
  enabled_features_count: number;
  enabled_features: string[];
}

interface TenantTableResponse {
  items: TenantRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

// === Tenant Detail ===
interface ContentByStatus {
  published: number;
  draft: number;
  archived: number;
}

interface ReviewByStatus {
  pending: number;
  approved: number;
  rejected: number;
}

interface ContentBreakdown {
  articles: ContentByStatus;
  cases: ContentByStatus;
  documents: ContentByStatus;
  services: number;
  services_total: number;
  employees: number;
  employees_total: number;
  faqs: number;
  faqs_total: number;
  reviews: ReviewByStatus;
}

interface InquiryBreakdown {
  total: number;
  by_status: Record<string, number>;
  by_utm_source: Record<string, number>;
  by_device_type: Record<string, number>;
  by_country_top10: Array<{ country: string; count: number }>;
  top_pages: Array<{ page: string; count: number }>;
  avg_processing_hours: number | null;
}

interface FeatureFlagInfo {
  feature_name: string;
  enabled: boolean;
}

interface TenantUserInfo {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role_name: string | null;
  last_login_at: string | null;
}

interface AuditEntry {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  user_email: string | null;
  created_at: string;
}

interface TenantDetailStats {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  is_active: boolean;
  content: ContentBreakdown;
  inquiries: InquiryBreakdown;
  feature_flags: FeatureFlagInfo[];
  users: TenantUserInfo[];
  recent_activity: AuditEntry[];
}

// === Trends ===
interface TrendPoint {
  date: string;
  value: number;
}

interface TenantTrendSeries {
  tenant_id: string;
  tenant_name: string;
  data: TrendPoint[];
}

interface PlatformTrends {
  new_tenants_by_month: TrendPoint[];
  new_users_by_month: TrendPoint[];
  inquiries_by_day: TrendPoint[];
  logins_by_day: TrendPoint[];
  inquiries_by_tenant: TenantTrendSeries[];
}

// === Alerts ===
interface HealthAlert {
  type: string;
  severity: 'critical' | 'warning' | 'info';
  tenant_id: string | null;
  tenant_name: string | null;
  message: string;
  details: Record<string, unknown> | null;
}

interface AlertSummary {
  critical: number;
  warning: number;
  info: number;
}

interface PlatformAlerts {
  alerts: HealthAlert[];
  summary: AlertSummary;
}
```

---

## 11. Error Handling

All endpoints follow the RFC 7807 error format:

```json
{
  "type": "https://api.cms.local/errors/<error_code>",
  "title": "Error Title",
  "status": 403,
  "detail": "Human-readable message",
  "instance": "/api/v1/admin/platform/overview"
}
```

| Status | When                                           |
|--------|------------------------------------------------|
| `401`  | Missing or expired JWT token                   |
| `403`  | User is not superuser / platform_owner         |
| `404`  | Tenant not found (details endpoint)            |
| `422`  | Invalid query parameters                       |

**Frontend handling:**

```typescript
try {
  const data = await api.get('/admin/platform/overview');
} catch (error) {
  if (error.response?.status === 403) {
    // Redirect to main dashboard — user doesn't have platform access
    router.push('/admin/dashboard');
  } else if (error.response?.status === 401) {
    // Token expired — redirect to login
    router.push('/login');
  } else {
    // Show generic error toast
    toast.error('Failed to load platform dashboard');
  }
}
```
