# Feature Flags API — руководство для фронтенда

Краткое руководство по работе с API feature flags в админ-панели.

---

## 1. Общее

### Base URL

```
Production: https://api.yoursite.com/api/v1
Development: http://localhost:8000/api/v1
```

### Кто может управлять feature flags

| Роль | Доступ |
|------|--------|
| **platform_owner** / **superuser** | Полный доступ: просмотр и изменение флагов любого тенанта |
| **Все остальные** (content_manager, editor, site_owner и т.д.) | **Нет доступа** → `403 Permission Denied` |

Управление feature flags — только для супер-админа платформы. Обычные пользователи (клиенты/организации) не могут менять свои флаги.

---

## 2. Эндпоинты

### GET /api/v1/feature-flags

Список всех feature flags для тенанта.

**Headers:**

```
Authorization: Bearer {access_token}
```

**Query-параметры:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `tenant_id` | UUID | Нет | ID тенанта. Если не передан — берётся тенант из JWT (текущий пользователь). Для platform_owner можно указать любой тенант. |

**Примеры запросов:**

```bash
# Флаги своего тенанта (из JWT)
GET /api/v1/feature-flags
Authorization: Bearer {token}

# Флаги конкретного тенанта (только platform_owner)
GET /api/v1/feature-flags?tenant_id=6dc384ef-c364-49df-aaa7-22941c7f3422
Authorization: Bearer {token}
```

**Успешный ответ (200):**

```json
{
  "items": [
    {
      "id": "c2db0c7d-9ff6-40f1-9c18-6003f764e972",
      "tenant_id": "e2e981fc-6c28-4641-beb2-291394efdcfe",
      "feature_name": "cases_module",
      "enabled": true,
      "description": "Case studies / portfolio module",
      "created_at": "2026-01-25T09:23:45.909131Z",
      "updated_at": "2026-01-25T09:24:12.653497Z"
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

Включить или выключить feature flag.

**Headers:**

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Path:**

| Параметр | Описание |
|----------|----------|
| `feature_name` | Имя фичи, например `cases_module`, `reviews_module`. |

**Query-параметры:**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `tenant_id` | UUID | Нет | Как в GET. Если не передан — используется тенант из JWT. |

**Body:**

```json
{
  "enabled": true
}
```

**Пример запроса:**

```bash
PATCH /api/v1/feature-flags/cases_module?tenant_id=6dc384ef-c364-49df-aaa7-22941c7f3422
Authorization: Bearer {token}
Content-Type: application/json

{"enabled": true}
```

**Успешный ответ (200):**

```json
{
  "id": "c2db0c7d-9ff6-40f1-9c18-6003f764e972",
  "tenant_id": "e2e981fc-6c28-4641-beb2-291394efdcfe",
  "feature_name": "cases_module",
  "enabled": true,
  "description": "Case studies / portfolio module",
  "created_at": "2026-01-25T09:23:45.909131Z",
  "updated_at": "2026-01-25T09:24:12.653497Z"
}
```

---

## 3. Доступные фичи

| `feature_name` | Описание |
|----------------|----------|
| `cases_module` | Кейсы / портфолио |
| `reviews_module` | Отзывы клиентов |
| `seo_advanced` | Расширённый SEO (мета, редиректы) |
| `multilang` | Многоязычность |
| `analytics_advanced` | Расширенная аналитика лидов (UTM, устройство, гео) |
| `blog_module` | Блог / статьи |
| `faq_module` | FAQ |
| `team_module` | Команда / сотрудники |

---

## 4. Ошибки

| Код | Причина |
|-----|---------|
| **401** | Нет или невалидный токен |
| **403** | Пользователь не platform_owner/superuser. Обычные юзеры всегда получают 403. |
| **404** | Тенант или feature flag не найден |

**Пример 403:**

```json
{
  "type": "https://api.cms.local/errors/permission_denied",
  "title": "Permission Denied",
  "status": 403,
  "detail": "Permission denied",
  "instance": "/api/v1/feature-flags",
  "required_permission": "platform:*"
}
```

**Пример 404 (флаг не найден):**

```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "FeatureFlag 'unknown_feature' not found",
  "instance": "/api/v1/feature-flags/unknown_feature"
}
```

---

## 5. Типы (TypeScript)

```ts
export interface FeatureFlag {
  id: string
  tenant_id: string
  feature_name: string
  enabled: boolean
  description: string | null
  created_at: string
  updated_at: string
}

export interface FeatureFlagsResponse {
  items: FeatureFlag[]
  available_features: Record<string, string>
}

export type FeatureName =
  | 'cases_module'
  | 'reviews_module'
  | 'seo_advanced'
  | 'multilang'
  | 'analytics_advanced'
  | 'blog_module'
  | 'faq_module'
  | 'team_module'
```

---

## 6. Примеры для фронтенда

### Fetch — получить флаги

```ts
const getFeatureFlags = async (tenantId?: string): Promise<FeatureFlagsResponse> => {
  const url = tenantId
    ? `/api/v1/feature-flags?tenant_id=${tenantId}`
    : '/api/v1/feature-flags'
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  if (res.status === 403) throw new Error('No access to feature flags')
  if (!res.ok) throw new Error('Failed to fetch feature flags')
  return res.json()
}
```

### Fetch — переключить флаг

```ts
const updateFeatureFlag = async (
  featureName: FeatureName,
  enabled: boolean,
  tenantId?: string
): Promise<FeatureFlag> => {
  const params = tenantId ? `?tenant_id=${tenantId}` : ''
  const res = await fetch(
    `/api/v1/feature-flags/${featureName}${params}`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ enabled }),
    }
  )
  if (res.status === 403) throw new Error('No access to feature flags')
  if (res.status === 404) throw new Error('Feature or tenant not found')
  if (!res.ok) throw new Error('Failed to update feature flag')
  return res.json()
}
```

### Axios

```ts
const api = axios.create({
  baseURL: 'https://api.yoursite.com/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Список флагов
const { data } = await api.get<FeatureFlagsResponse>('/feature-flags', {
  params: tenantId ? { tenant_id: tenantId } : {},
})

// Переключить флаг
const { data } = await api.patch<FeatureFlag>(
  `/feature-flags/${featureName}`,
  { enabled: true },
  { params: tenantId ? { tenant_id: tenantId } : {} }
)
```

### React + React Query

```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

function useFeatureFlags(tenantId?: string) {
  return useQuery({
    queryKey: ['feature-flags', tenantId ?? 'current'],
    queryFn: () => getFeatureFlags(tenantId),
    enabled: !!isPlatformOwner, // запрос только для platform_owner
  })
}

function useToggleFeature(tenantId?: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ name, enabled }: { name: FeatureName; enabled: boolean }) =>
      updateFeatureFlag(name, enabled, tenantId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feature-flags', tenantId ?? 'current'] })
    },
  })
}

// В компоненте — показывать UI только platform_owner
function FeatureFlagsPage() {
  const { user } = useAuth()
  const tenantId = selectedTenantId ?? undefined

  if (!user?.is_superuser && user?.role?.name !== 'platform_owner') {
    return <div>No access</div>
  }

  const { data, isLoading } = useFeatureFlags(tenantId)
  const toggle = useToggleFeature(tenantId)

  const handleToggle = (name: FeatureName, enabled: boolean) => {
    toggle.mutate({ name, enabled })
  }

  // ...
}
```

---

## 7. Рекомендации

1. **Показывать UI управления флагами только** пользователям с `role.name === 'platform_owner'` или `is_superuser === true`. Иначе они всё равно получат 403.
2. **При выборе тенанта** в админке (например, в селекторе «Организация») передавать его `id` в `tenant_id` для GET и PATCH. Для «своего» тенанта можно не передавать `tenant_id`.
3. **Обрабатывать 403**: скрыть блок с флагами или показать сообщение «Нет доступа».
4. **Кэшировать** ответ GET (например, через React Query) и инвалидировать после успешного PATCH.

---

## 8. Связанные документы

- [13-tenants-settings.md](./endpoints/13-tenants-settings.md) — полное описание Tenants & Feature Flags API
- [01-authentication.md](./endpoints/01-authentication.md) — логин, JWT, роли
