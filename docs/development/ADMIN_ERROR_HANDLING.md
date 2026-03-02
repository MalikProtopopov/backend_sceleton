# Обработка ошибок 403 / 401 / 429 в админке

> Полный гайд: какие тела ответов возвращает API, как их различать и что показывать пользователю.

---

## 1. Формат ошибок (RFC 7807)

Все ошибки API возвращаются в формате Problem Details:

```json
{
  "type": "https://api.cms.local/errors/{error_code}",
  "title": "Human Readable Title",
  "status": 403,
  "detail": "Описание ошибки для пользователя",
  "instance": "/api/v1/admin/uoms",
  ...дополнительные поля
}
```

Ключевое поле для маршрутизации — **`error_code`** (извлекается из `type`).

---

## 2. Все типы 403-ошибок

### 2.1. `permission_denied` — нет RBAC-разрешения

Пользователь авторизован, но его роль не содержит нужный permission.

```json
{
  "type": "https://api.cms.local/errors/permission_denied",
  "title": "Permission Denied",
  "status": 403,
  "detail": "You do not have sufficient permissions for this action. Contact your organization administrator to update your role.",
  "instance": "/api/v1/admin/uoms",
  "restriction_level": "user",
  "required_permission": "catalog:read"
}
```

| Поле | Значение |
|------|----------|
| `restriction_level` | `"user"` — ограничение на уровне роли пользователя |
| `required_permission` | `"catalog:read"` — какой permission нужен |

**Что показать:** «У вас нет доступа к этому разделу. Обратитесь к администратору для расширения роли.»

---

### 2.2. `insufficient_role` — роль недостаточна

Эндпоинт требует конкретную роль (например `platform_owner`).

```json
{
  "type": "https://api.cms.local/errors/insufficient_role",
  "title": "Insufficient Role",
  "status": 403,
  "detail": "You do not have the required role for this action. Contact your organization administrator.",
  "instance": "/api/v1/admin/platform/plans",
  "restriction_level": "user",
  "required_role": "platform_owner"
}
```

| Поле | Значение |
|------|----------|
| `restriction_level` | `"user"` |
| `required_role` | `"platform_owner"` |

**Что показать:** «Этот раздел доступен только администратору платформы.»

---

### 2.3. `feature_disabled` — модуль не оплачен в тарифе

Тенант не имеет модуль в текущем тарифе. Основная ошибка для feature gating.

```json
{
  "type": "https://api.cms.local/errors/feature_disabled",
  "title": "Feature Disabled",
  "status": 403,
  "detail": "This feature is not enabled for your organization. Contact your platform administrator to enable it.",
  "instance": "/api/v1/admin/products",
  "feature": "catalog_module",
  "contact_admin": true,
  "restriction_level": "organization"
}
```

| Поле | Значение |
|------|----------|
| `restriction_level` | `"organization"` — ограничение на уровне тарифа/тенанта |
| `feature` | `"catalog_module"` — какой модуль нужен |
| `contact_admin` | `true` — можно предложить запрос на апгрейд |

**Что показать:** Модальное окно или страница «Этот раздел доступен в расширенном тарифе» + кнопка «Запросить подключение».

---

### 2.4. `limit_exceeded` — лимит тарифа исчерпан

При попытке создать запись (статью, товар) сверх лимита плана.

```json
{
  "type": "https://api.cms.local/errors/limit_exceeded",
  "title": "Limit Exceeded",
  "status": 403,
  "detail": "Resource limit reached for 'max_products'. Upgrade your plan or purchase additional capacity.",
  "instance": "/api/v1/admin/products",
  "resource": "max_products",
  "current_usage": 50,
  "limit": 50,
  "restriction_level": "organization"
}
```

| Поле | Значение |
|------|----------|
| `restriction_level` | `"organization"` |
| `resource` | `"max_products"` — какой лимит превышен |
| `current_usage` | `50` — текущее использование |
| `limit` | `50` — максимум по тарифу |

**Что показать:** «Достигнут лимит: 50/50 товаров. Перейдите на расширенный тариф.» + кнопка «Перейти к тарифам».

---

### 2.5. `tenant_inactive` — тенант заблокирован

Организация деактивирована платформой.

```json
{
  "type": "https://api.cms.local/errors/tenant_inactive",
  "title": "Tenant Inactive",
  "status": 403,
  "detail": "Organization is currently suspended. Contact platform administrator.",
  "instance": "/api/v1/admin/articles"
}
```

**Что показать:** Полноэкранное сообщение: «Ваша организация приостановлена. Обратитесь к администратору платформы.» Блокировать весь интерфейс.

---

## 3. Ошибки 401 (Unauthorized)

| `error_code` | Когда | Действие |
|-------------|-------|----------|
| `authentication_required` | Нет токена | Редирект на `/login` |
| `token_expired` | Токен истёк | Попробовать refresh, если не получится — `/login` |
| `invalid_token` | Токен невалиден | Очистить хранилище, редирект на `/login` |
| `invalid_credentials` | Неверный пароль | Показать ошибку на форме логина |

---

## 4. Ошибка 429 (Rate Limit)

```json
{
  "type": "https://api.cms.local/errors/rate_limit_exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many upgrade requests. Please wait before submitting another.",
  "retry_after": 3600
}
```

**Что показать:** Toast «Слишком много запросов. Повторите через X минут.»

---

## 5. Реализация: глобальный interceptor

### axios interceptor

```typescript
// lib/api.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useErrorStore } from '@/stores/error'
import { useRouter } from 'vue-router' // или next/navigation для Next.js

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

// Извлечь error_code из RFC 7807 body
function getErrorCode(data: any): string | null {
  if (!data?.type) return null
  // "https://api.cms.local/errors/feature_disabled" → "feature_disabled"
  const parts = data.type.split('/')
  return parts[parts.length - 1] || null
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { status, data } = error.response ?? {}
    const errorCode = getErrorCode(data)
    const errorStore = useErrorStore()

    // ── 401: Authentication ──
    if (status === 401) {
      if (errorCode === 'token_expired') {
        // Попробовать refresh token
        try {
          await useAuthStore().refreshToken()
          return api.request(error.config) // retry
        } catch {
          useAuthStore().logout()
          window.location.href = '/login'
        }
      } else {
        useAuthStore().logout()
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    // ── 403: Authorization / Feature / Limit ──
    if (status === 403) {
      switch (errorCode) {
        case 'feature_disabled':
          errorStore.showFeatureDisabled({
            feature: data.feature,
            message: data.detail,
          })
          break

        case 'limit_exceeded':
          errorStore.showLimitExceeded({
            resource: data.resource,
            current: data.current_usage,
            limit: data.limit,
            message: data.detail,
          })
          break

        case 'permission_denied':
          errorStore.showPermissionDenied({
            permission: data.required_permission,
            message: data.detail,
          })
          break

        case 'insufficient_role':
          errorStore.showPermissionDenied({
            role: data.required_role,
            message: data.detail,
          })
          break

        case 'tenant_inactive':
          errorStore.showTenantInactive()
          break

        default:
          errorStore.showGenericForbidden(data?.detail)
      }
      return Promise.reject(error)
    }

    // ── 429: Rate Limit ──
    if (status === 429) {
      const retryAfter = data?.retry_after
      errorStore.showRateLimit(retryAfter)
      return Promise.reject(error)
    }

    // ── Остальные ошибки ──
    return Promise.reject(error)
  }
)

export default api
```

---

## 6. Стор ошибок

```typescript
// stores/error.ts
import { defineStore } from 'pinia'

interface FeatureDisabledPayload {
  feature: string
  message: string
}
interface LimitExceededPayload {
  resource: string
  current: number
  limit: number
  message: string
}
interface PermissionDeniedPayload {
  permission?: string
  role?: string
  message: string
}

type ErrorType =
  | 'feature_disabled'
  | 'limit_exceeded'
  | 'permission_denied'
  | 'tenant_inactive'
  | 'rate_limit'
  | 'generic_forbidden'

export const useErrorStore = defineStore('error', {
  state: () => ({
    visible: false,
    type: null as ErrorType | null,
    payload: null as any,
  }),

  actions: {
    showFeatureDisabled(payload: FeatureDisabledPayload) {
      this.type = 'feature_disabled'
      this.payload = payload
      this.visible = true
    },
    showLimitExceeded(payload: LimitExceededPayload) {
      this.type = 'limit_exceeded'
      this.payload = payload
      this.visible = true
    },
    showPermissionDenied(payload: PermissionDeniedPayload) {
      this.type = 'permission_denied'
      this.payload = payload
      this.visible = true
    },
    showTenantInactive() {
      this.type = 'tenant_inactive'
      this.payload = null
      this.visible = true
    },
    showRateLimit(retryAfter?: number) {
      this.type = 'rate_limit'
      this.payload = { retryAfter }
      this.visible = true
    },
    showGenericForbidden(message?: string) {
      this.type = 'generic_forbidden'
      this.payload = { message: message || 'Доступ запрещён' }
      this.visible = true
    },
    dismiss() {
      this.visible = false
      this.type = null
      this.payload = null
    },
  },
})
```

---

## 7. UI-компоненты

### 7.1. Глобальная модалка ошибок доступа

```vue
<!-- components/ErrorModal.vue -->
<template>
  <Dialog :open="errorStore.visible" @close="errorStore.dismiss()">
    <!-- feature_disabled -->
    <template v-if="errorStore.type === 'feature_disabled'">
      <div class="text-center p-6">
        <LockIcon class="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <h3 class="text-lg font-semibold mb-2">Модуль недоступен</h3>
        <p class="text-gray-600 mb-4">
          Этот раздел не входит в ваш текущий тариф.
        </p>
        <div class="flex gap-3 justify-center">
          <Button variant="outline" @click="errorStore.dismiss()">
            Закрыть
          </Button>
          <Button @click="goToBilling()">
            Посмотреть тарифы
          </Button>
        </div>
      </div>
    </template>

    <!-- limit_exceeded -->
    <template v-else-if="errorStore.type === 'limit_exceeded'">
      <div class="text-center p-6">
        <AlertTriangleIcon class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-semibold mb-2">Лимит исчерпан</h3>
        <p class="text-gray-600 mb-2">
          Достигнут лимит: {{ errorStore.payload.current }}/{{ errorStore.payload.limit }}
        </p>
        <p class="text-gray-500 text-sm mb-4">
          Перейдите на расширенный тариф для увеличения лимитов.
        </p>
        <div class="flex gap-3 justify-center">
          <Button variant="outline" @click="errorStore.dismiss()">
            Закрыть
          </Button>
          <Button @click="goToBilling()">
            Расширить тариф
          </Button>
        </div>
      </div>
    </template>

    <!-- permission_denied -->
    <template v-else-if="errorStore.type === 'permission_denied'">
      <div class="text-center p-6">
        <ShieldXIcon class="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 class="text-lg font-semibold mb-2">Нет доступа</h3>
        <p class="text-gray-600 mb-4">
          У вашей роли нет прав на это действие.
          Обратитесь к администратору.
        </p>
        <Button @click="errorStore.dismiss()">Понятно</Button>
      </div>
    </template>

    <!-- tenant_inactive -->
    <template v-else-if="errorStore.type === 'tenant_inactive'">
      <div class="text-center p-6">
        <BanIcon class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-semibold mb-2">Организация приостановлена</h3>
        <p class="text-gray-600 mb-4">
          Ваша организация временно заблокирована.
          Обратитесь к администратору платформы.
        </p>
      </div>
    </template>

    <!-- rate_limit -->
    <template v-else-if="errorStore.type === 'rate_limit'">
      <div class="text-center p-6">
        <ClockIcon class="w-12 h-12 text-amber-500 mx-auto mb-4" />
        <h3 class="text-lg font-semibold mb-2">Слишком много запросов</h3>
        <p class="text-gray-600 mb-4">
          Повторите попытку позже.
        </p>
        <Button @click="errorStore.dismiss()">Ок</Button>
      </div>
    </template>
  </Dialog>
</template>
```

### 7.2. Маппинг `error_code` → русское название лимита

```typescript
const RESOURCE_NAMES: Record<string, string> = {
  max_users: 'пользователей',
  max_storage_mb: 'хранилища (МБ)',
  max_leads_per_month: 'заявок в месяц',
  max_products: 'товаров',
  max_variants: 'вариаций',
  max_domains: 'доменов',
  max_articles: 'статей',
  max_rbac_roles: 'ролей',
}

const FEATURE_NAMES: Record<string, string> = {
  blog_module: 'Блог / Статьи',
  cases_module: 'Кейсы',
  reviews_module: 'Отзывы',
  faq_module: 'FAQ',
  team_module: 'Команда',
  services_module: 'Услуги',
  catalog_module: 'Каталог товаров',
  variants_module: 'Вариации товаров',
  seo_advanced: 'Расширенное SEO',
  multilang: 'Мультиязычность',
  analytics_advanced: 'Расширенная аналитика',
  documents: 'Документы',
}
```

---

## 8. Полная таблица: `error_code` → действие фронта

| `error_code` | HTTP | `restriction_level` | Действие фронта |
|--------------|------|---------------------|-----------------|
| `authentication_required` | 401 | — | Redirect `/login` |
| `token_expired` | 401 | — | Refresh token → retry / redirect `/login` |
| `invalid_token` | 401 | — | Clear storage → redirect `/login` |
| `permission_denied` | 403 | `user` | Модалка «Нет прав, обратитесь к админу» |
| `insufficient_role` | 403 | `user` | Модалка «Нужна роль X» |
| `feature_disabled` | 403 | `organization` | Модалка «Модуль не в тарифе» + кнопка «Тарифы» |
| `limit_exceeded` | 403 | `organization` | Модалка «Лимит N/M» + кнопка «Расширить тариф» |
| `tenant_inactive` | 403 | — | Полноэкранная блокировка |
| `rate_limit_exceeded` | 429 | — | Toast «Подождите X сек» |

---

## 9. Как отличать «нет прав роли» от «нет модуля в тарифе»

Ключевое поле — **`restriction_level`**:

- `"user"` → проблема в **роли пользователя** (`permission_denied`, `insufficient_role`)
- `"organization"` → проблема в **тарифе тенанта** (`feature_disabled`, `limit_exceeded`)

```typescript
function is403FromBilling(data: any): boolean {
  return data?.restriction_level === 'organization'
}
```

Если `restriction_level === "organization"` → показываем «Расширить тариф».
Если `restriction_level === "user"` → показываем «Обратитесь к администратору».

---

## 10. Рекомендация: проактивная защита

Вместо того чтобы пользователь кликал → получал 403 → видел модалку, лучше **скрывать/блокировать** элементы заранее:

1. **Сайдбар**: использовать `GET /auth/me/features` для скрытия разделов (см. ADMIN_BILLING_FRONTEND_REQUIREMENTS.md)
2. **Кнопки создания**: проверять лимиты через `GET /admin/my-limits` и дизейблить кнопку «Добавить» если лимит исчерпан
3. **RBAC**: из `GET /auth/me` → `permissions[]` скрывать кнопки, для которых нет permission

Но interceptor с модалкой **всё равно нужен** как safety net — на случай race condition или прямого перехода по URL.
