# Документация для фронтенда админки: мульти-доменный режим + свитчер тенантов

> **Версия**: 1.0  
> **Дата**: 2026-02-13  
> **Backend**: `refactor/backend-analysis-implementation`

---

## Содержание

1. [Общая схема работы](#1-общая-схема-работы)
2. [Резолв тенанта из домена](#2-резолв-тенанта-из-домена)
3. [HTTP interceptor для X-Tenant-ID](#3-http-interceptor-для-x-tenant-id)
4. [Стор тенанта (Pinia / Zustand / Redux)](#4-стор-тенанта)
5. [Применение брендинга](#5-применение-брендинга)
6. [Логин без выбора организации](#6-логин-без-выбора-организации)
7. [Tenant Switcher — компонент для мульти-орг пользователей](#7-tenant-switcher)
8. [Экраны ошибок](#8-экраны-ошибок)
9. [Локальная разработка (/etc/hosts)](#9-локальная-разработка)
10. [Полный список API эндпоинтов](#10-api-эндпоинты)

---

## 1. Общая схема работы

```
admin.client1.com  ──┐
admin.client2.com  ──┼──► Nginx (wildcard SSL) ──► Единый SPA-билд ──► API (api.mediann.dev)
admin-acme.mediann.dev─┘
```

1. Все админ-домены ведут на один и тот же SPA-деплой (Nginx `root` на один каталог).
2. SPA при загрузке читает `window.location.hostname` и резолвит его в `tenant_id` через API.
3. Все последующие API-запросы содержат заголовок `X-Tenant-ID`.

---

## 2. Резолв тенанта из домена

### Endpoint

```
GET /api/v1/public/tenants/by-domain/{hostname}
```

**Авторизация:** не требуется (публичный).

### Пример запроса

```bash
curl https://api.mediann.dev/api/v1/public/tenants/by-domain/admin.client1.com
```

### Ответ (200 OK)

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "client1",
  "name": "Клиент 1",
  "logo_url": "https://cdn.mediann.dev/tenants/logo.png",
  "primary_color": "#1a5276",
  "site_url": "https://client1.com"
}
```

### Ответ (404)

Домен не найден — показывайте экран «Домен не настроен».

### Как интегрировать

```typescript
// src/lib/tenant-resolver.ts

interface TenantInfo {
  tenant_id: string;
  slug: string;
  name: string;
  logo_url: string | null;
  primary_color: string | null;
  site_url: string | null;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL; // "https://api.mediann.dev/api/v1"

export async function resolveTenant(): Promise<TenantInfo> {
  const hostname = window.location.hostname;
  const resp = await fetch(`${API_BASE}/public/tenants/by-domain/${hostname}`);

  if (!resp.ok) {
    throw new Error(`Domain not found: ${hostname}`);
  }

  return resp.json();
}
```

**Важно:** вызывайте `resolveTenant()` **до** создания Vue/React app (в `main.ts`), чтобы `tenant_id` был доступен до первого API-вызова.

```typescript
// main.ts — пример для Vue 3 + Pinia
import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { resolveTenant } from "./lib/tenant-resolver";
import { useTenantStore } from "./stores/tenant";

async function bootstrap() {
  try {
    const tenantInfo = await resolveTenant();

    const app = createApp(App);
    const pinia = createPinia();
    app.use(pinia);

    const tenantStore = useTenantStore(pinia);
    tenantStore.setTenant(tenantInfo);

    app.mount("#app");
  } catch (err) {
    // Показываем страницу "Домен не найден"
    document.getElementById("app")!.innerHTML =
      '<div class="error">Домен не настроен. Обратитесь к администратору.</div>';
  }
}

bootstrap();
```

---

## 3. HTTP interceptor для X-Tenant-ID

Каждый запрос к API **должен** содержать заголовок `X-Tenant-ID`.

### Axios

```typescript
// src/lib/api.ts
import axios from "axios";
import { useTenantStore } from "@/stores/tenant";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const tenantStore = useTenantStore();
  if (tenantStore.tenantId) {
    config.headers["X-Tenant-ID"] = tenantStore.tenantId;
  }

  // JWT token
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export default api;
```

### Fetch (нативный)

```typescript
function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const tenantStore = useTenantStore();
  const headers = new Headers(options.headers);
  headers.set("X-Tenant-ID", tenantStore.tenantId);

  const token = localStorage.getItem("access_token");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  return fetch(`${API_BASE}${url}`, { ...options, headers });
}
```

---

## 4. Стор тенанта

### Pinia (Vue 3)

```typescript
// src/stores/tenant.ts
import { defineStore } from "pinia";

interface TenantState {
  tenantId: string;
  slug: string;
  name: string;
  logoUrl: string | null;
  primaryColor: string | null;
  siteUrl: string | null;
}

export const useTenantStore = defineStore("tenant", {
  state: (): TenantState => ({
    tenantId: "",
    slug: "",
    name: "",
    logoUrl: null,
    primaryColor: null,
    siteUrl: null,
  }),

  actions: {
    setTenant(info: {
      tenant_id: string;
      slug: string;
      name: string;
      logo_url: string | null;
      primary_color: string | null;
      site_url: string | null;
    }) {
      this.tenantId = info.tenant_id;
      this.slug = info.slug;
      this.name = info.name;
      this.logoUrl = info.logo_url;
      this.primaryColor = info.primary_color;
      this.siteUrl = info.site_url;
    },
  },
});
```

---

## 5. Применение брендинга

При получении `primary_color` и `logo_url` от API, применяйте их через CSS-переменные:

```typescript
function applyBranding(color: string | null, logoUrl: string | null) {
  const root = document.documentElement;

  if (color) {
    root.style.setProperty("--color-primary", color);
    // Можно вычислить светлый/тёмный вариант:
    root.style.setProperty("--color-primary-light", `${color}20`); // 12% opacity
    root.style.setProperty("--color-primary-dark", darken(color, 0.15));
  }

  if (logoUrl) {
    root.style.setProperty("--tenant-logo-url", `url(${logoUrl})`);
  }
}
```

### CSS

```css
:root {
  --color-primary: #1a5276;
  --color-primary-light: #1a527620;
}

.btn-primary {
  background-color: var(--color-primary);
}

.sidebar-logo {
  background-image: var(--tenant-logo-url);
  background-size: contain;
  background-repeat: no-repeat;
}
```

---

## 6. Логин без выбора организации

Поскольку тенант уже определён из домена, форма логина НЕ содержит выбора организации.

```
┌─────────────────────────────┐
│      [logo тенанта]         │
│    «Название компании»      │
│                             │
│   Email: [____________]     │
│   Пароль: [___________]     │
│                             │
│      [ Войти ]              │
└─────────────────────────────┘
```

### Запрос

```http
POST /api/v1/auth/login
X-Tenant-ID: 550e8400-e29b-41d4-a716-446655440000
Content-Type: application/json

{
  "email": "admin@client1.com",
  "password": "..."
}
```

### Ответ

```json
{
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "user": {
    "id": "...",
    "tenant_id": "...",
    "email": "admin@client1.com",
    "first_name": "Иван",
    "last_name": "Петров",
    ...
  }
}
```

---

## 7. Tenant Switcher

Если пользователь состоит в нескольких организациях (один email — несколько тенантов), в интерфейсе показывается свитчер.

### 7.1 Получить список организаций

```http
GET /api/v1/auth/me/tenants
Authorization: Bearer <access_token>
X-Tenant-ID: <current>
```

**Ответ:**

```json
{
  "current_tenant_id": "550e8400-...",
  "tenants": [
    {
      "tenant_id": "550e8400-...",
      "name": "Клиент 1",
      "slug": "client1",
      "logo_url": "https://cdn.mediann.dev/...",
      "primary_color": "#1a5276",
      "admin_domain": "admin.client1.com"
    },
    {
      "tenant_id": "660f9500-...",
      "name": "Клиент 2",
      "slug": "client2",
      "logo_url": null,
      "primary_color": "#27ae60",
      "admin_domain": "admin.client2.com"
    }
  ]
}
```

### 7.2 Логика переключения

**Вариант A — редирект на домен (рекомендуется):**

Если у целевого тенанта есть `admin_domain`, перенаправляйте пользователя на этот домен. Он снова пройдёт логин на новом домене.

```typescript
function switchTenant(tenant: TenantAccessInfo) {
  if (tenant.admin_domain) {
    window.location.href = `https://${tenant.admin_domain}`;
  }
}
```

**Вариант B — switch-tenant API (без смены домена):**

Если редирект не подходит (например, все тенанты на одном домене), используйте API:

```http
POST /api/v1/auth/switch-tenant
Authorization: Bearer <access_token>
X-Tenant-ID: <current>
Content-Type: application/json

{
  "tenant_id": "660f9500-..."
}
```

**Ответ (200):**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

После получения новых токенов:

```typescript
async function switchTenantInPlace(targetTenantId: string) {
  const resp = await api.post("/auth/switch-tenant", {
    tenant_id: targetTenantId,
  });

  // 1. Сохранить новые токены
  localStorage.setItem("access_token", resp.data.access_token);
  localStorage.setItem("refresh_token", resp.data.refresh_token);

  // 2. Перезагрузить приложение (самый надёжный способ сбросить все кэши)
  window.location.reload();
}
```

### 7.3 Компонент свитчера (Vue 3 пример)

```vue
<template>
  <div v-if="tenants.length > 1" class="tenant-switcher">
    <button @click="open = !open" class="switcher-toggle">
      <img v-if="currentTenant?.logo_url" :src="currentTenant.logo_url" />
      <span>{{ currentTenant?.name }}</span>
      <ChevronIcon />
    </button>

    <ul v-if="open" class="switcher-dropdown">
      <li
        v-for="t in tenants"
        :key="t.tenant_id"
        :class="{ active: t.tenant_id === currentTenantId }"
        @click="switchTo(t)"
      >
        <img v-if="t.logo_url" :src="t.logo_url" class="tenant-logo" />
        <div>
          <div class="tenant-name">{{ t.name }}</div>
          <div class="tenant-domain">{{ t.admin_domain }}</div>
        </div>
      </li>
    </ul>
  </div>
</template>
```

### 7.4 Когда показывать свитчер

```typescript
const showSwitcher = computed(() => tenants.value.length > 1);
```

Если `tenants.length === 1`, свитчер не нужен. Показывайте только лого и название.

---

## 8. Экраны ошибок

### 8.1 Домен не найден (404 от by-domain)

```
┌──────────────────────────────────┐
│                                  │
│   ⚠ Домен не настроен           │
│                                  │
│   Адрес admin.unknown.com        │
│   не связан с организацией.      │
│                                  │
│   Обратитесь к администратору    │
│   платформы.                     │
│                                  │
└──────────────────────────────────┘
```

### 8.2 Нет доступа к организации (switch-tenant → 401)

```
┌──────────────────────────────────┐
│                                  │
│   🔒 Нет доступа                 │
│                                  │
│   У вас нет прав для доступа     │
│   к этой организации.            │
│                                  │
│   [ Вернуться ]                  │
│                                  │
└──────────────────────────────────┘
```

### 8.3 Организация отключена (tenant is_active=false)

Бэкенд вернёт `403 Tenant is suspended`. Показывайте:

```
┌──────────────────────────────────┐
│                                  │
│   ⏸ Организация приостановлена   │
│                                  │
│   Обратитесь к администратору    │
│   платформы для восстановления   │
│   доступа.                       │
│                                  │
└──────────────────────────────────┘
```

---

## 9. Локальная разработка

Для тестирования мульти-доменного режима локально, добавьте записи в `/etc/hosts`:

```
# /etc/hosts
127.0.0.1   admin.client1.local
127.0.0.1   admin.client2.local
```

В базе данных (через API или seed) создайте записи в `tenant_domains`:

```bash
# Добавить домен для тенанта (platform owner token)
curl -X POST https://api.mediann.dev/api/v1/tenants/{tenant_id}/domains \
  -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: <your_tenant_id>" \
  -H "Content-Type: application/json" \
  -d '{"domain": "admin.client1.local", "is_primary": true}'
```

Запустите dev-сервер:

```bash
npm run dev -- --host 0.0.0.0 --port 3000
```

Открывайте `http://admin.client1.local:3000` — SPA резолвит тенант из hostname.

**Env-переменные для разработки:**

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 10. API эндпоинты

### Публичные (без авторизации)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/public/tenants/by-domain/{domain}` | Резолв домена → tenant info |
| GET | `/public/tenants/{tenant_id}` | Публичная информация о тенанте |
| GET | `/public/tenants/{tenant_id}/analytics` | GA / Метрика коды |

### Авторизация

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/auth/login` | Логин (требует `X-Tenant-ID`) |
| POST | `/auth/refresh` | Обновить токены |
| POST | `/auth/logout` | Выход (отзыв токена) |
| POST | `/auth/forgot-password` | Запрос сброса пароля |
| POST | `/auth/reset-password` | Сброс пароля по токену |

### Текущий пользователь

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/auth/me` | Информация о текущем пользователе |
| GET | `/auth/me/tenants` | **Список организаций пользователя** (для свитчера) |
| GET | `/auth/me/features` | Каталог фич тенанта |
| POST | `/auth/switch-tenant` | **Смена организации → новые токены** |
| POST | `/auth/me/password` | Смена пароля |
| POST | `/auth/me/avatar` | Загрузка аватара |
| DELETE | `/auth/me/avatar` | Удаление аватара |

### Управление доменами (platform owner)

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/tenants/{id}/domains` | Список доменов тенанта |
| POST | `/tenants/{id}/domains` | Добавить домен |
| PATCH | `/tenants/{id}/domains/{domain_id}` | Обновить (is_primary, ssl_status) |
| DELETE | `/tenants/{id}/domains/{domain_id}` | Удалить домен |

### Структуры данных

#### TenantByDomainResponse

```typescript
interface TenantByDomainResponse {
  tenant_id: string;   // UUID
  slug: string;
  name: string;
  logo_url: string | null;
  primary_color: string | null;  // "#RRGGBB"
  site_url: string | null;
}
```

#### MyTenantsResponse

```typescript
interface MyTenantsResponse {
  current_tenant_id: string;
  tenants: TenantAccessInfo[];
}

interface TenantAccessInfo {
  tenant_id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  primary_color: string | null;
  admin_domain: string | null;  // primary domain, e.g. "admin.client1.com"
}
```

#### SwitchTenantRequest / Response

```typescript
// Request body
interface SwitchTenantRequest {
  tenant_id: string;
}

// Response — same as login tokens
interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}
```

#### TenantDomainResponse

```typescript
interface TenantDomainResponse {
  id: string;
  tenant_id: string;
  domain: string;         // "admin.client1.com"
  is_primary: boolean;
  ssl_status: "pending" | "active" | "error";
  created_at: string;     // ISO 8601
  updated_at: string;
}
```

---

## Чек-лист интеграции

- [ ] Резолв тенанта из `window.location.hostname` при загрузке SPA
- [ ] Стор тенанта (Pinia/Zustand) заполняется до монтирования приложения
- [ ] `X-Tenant-ID` header в каждом API-запросе (interceptor)
- [ ] Брендинг: CSS-переменные из `primary_color` + `logo_url`
- [ ] Форма логина без выбора организации (тенант из домена)
- [ ] `GET /auth/me/tenants` после логина → определить нужен ли свитчер
- [ ] Свитчер отображается если `tenants.length > 1`
- [ ] Переключение через редирект на `admin_domain` или `POST /switch-tenant`
- [ ] Экран ошибки: домен не найден (404)
- [ ] Экран ошибки: организация приостановлена (403)
- [ ] Локальная разработка через `/etc/hosts`
