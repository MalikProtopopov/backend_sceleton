# Документация для фронтенда админки: мульти-тенантный режим

> **Версия**: 2.0  
> **Дата**: 2026-02-23  
> **Backend branch**: `feat/tenant-domain-switcher`  
> **Ключевое изменение v2**: Smart Login -- `X-Tenant-ID` при логине теперь опционален; добавлен `POST /auth/select-tenant`; пароль синхронизируется между тенантами.

---

## Содержание

1. [Общая схема работы](#1-общая-схема-работы)
2. [Резолв тенанта из домена](#2-резолв-тенанта-из-домена)
3. [HTTP interceptor (Axios)](#3-http-interceptor)
4. [Сторы (Zustand)](#4-сторы)
5. [Применение брендинга](#5-применение-брендинга)
6. [Умный логин (Smart Login)](#6-умный-логин-smart-login)
7. [Tenant Switcher — компонент для мульти-орг пользователей](#7-tenant-switcher)
8. [Экраны ошибок](#8-экраны-ошибок)
9. [Локальная разработка (/etc/hosts)](#9-локальная-разработка)
10. [Полный список API эндпоинтов](#10-api-эндпоинты)

---

## 1. Общая схема работы

```
admin.client1.com  ──┐
admin.client2.com  ──┼──► Caddy (auto SSL) ──► Единый SPA-билд ──► API (api.mediann.dev)
admin-acme.mediann.dev─┘
```

**Двухуровневая система доменов:**

| Уровень | Пример | SSL | Что нужно |
|---------|--------|-----|-----------|
| Поддомены платформы | `yastvo.mediann.dev` | Wildcard cert `*.mediann.dev` | Ничего — автоматически |
| Кастомные домены | `admin.yastvo.com` | On-demand TLS (Let's Encrypt) | Клиент добавляет CNAME → `tenants.mediann.dev` |

1. Все админ-домены ведут на один и тот же SPA-деплой (Caddy reverse proxy).
2. SPA при загрузке читает `window.location.hostname` и резолвит его в `tenant_id` через `GET /public/tenants/by-domain/{hostname}`.
3. **Логин** (`POST /auth/login`) — заголовок `X-Tenant-ID` **опционален**:
   - Если домен резолвится — отправляется `X-Tenant-ID`, бэкенд входит сразу.
   - Если домен не резолвится (общий домен) или хедер не передан — бэкенд определяет список доступных тенантов и может вернуть `selection_required`, после чего пользователь выбирает тенант → `POST /auth/select-tenant`.
4. **После входа** (получены `access_token` + `tenant_id`) — все дальнейшие API-запросы **обязательно** содержат `X-Tenant-ID`.

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

const API_BASE = process.env.NEXT_PUBLIC_API_URL; // "https://api.mediann.dev/api/v1"

export async function resolveTenant(): Promise<TenantInfo> {
  const hostname = window.location.hostname;
  const resp = await fetch(`${API_BASE}/public/tenants/by-domain/${hostname}`);

  if (!resp.ok) {
    throw new Error(`Domain not found: ${hostname}`);
  }

  return resp.json();
}
```

**Важно:** резолв тенанта должен произойти **до** рендера остального приложения, чтобы `tenant_id` был доступен до первого API-вызова.

```tsx
// src/app/providers/TenantProvider.tsx
"use client";
import { useEffect, useState, type ReactNode } from "react";
import { resolveTenant } from "@/shared/lib/tenant-resolver";
import { useTenantStore } from "@/shared/stores/tenant";

export function TenantProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const setTenant = useTenantStore((s) => s.setTenant);

  useEffect(() => {
    resolveTenant()
      .then((info) => {
        setTenant({
          tenantId: info.tenant_id,
          slug: info.slug,
          name: info.name,
          logoUrl: info.logo_url,
          primaryColor: info.primary_color,
          siteUrl: info.site_url,
        });
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [setTenant]);

  if (status === "loading") return <div>Загрузка...</div>;
  if (status === "error") return <div className="error">Домен не настроен. Обратитесь к администратору.</div>;
  return <>{children}</>;
}
```

> **Примечание:** если SPA работает на общем домене (например `admin.mediann.dev`), резолв вернёт 404. В этом случае `TenantProvider` может перейти в режим «общего логина» — не показывать лого тенанта и не передавать `X-Tenant-ID` при логине.

---

## 3. HTTP interceptor

### Правила отправки `X-Tenant-ID`

| Ситуация | `X-Tenant-ID` | Комментарий |
|---|---|---|
| `POST /auth/login` — домен резолвился | ✅ отправляем | Мгновенный вход |
| `POST /auth/login` — общий домен / без резолва | ❌ не отправляем | Бэкенд вернёт `selection_required` или войдёт автоматически, если тенант один |
| `POST /auth/select-tenant` | ❌ не нужен | `tenant_id` передаётся в теле запроса |
| Все остальные запросы после входа | ✅ **обязательно** | Из стора / `localStorage` |

### Axios (рекомендуемый пример)

```typescript
// src/shared/api/instance.ts
import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

api.interceptors.request.use((config) => {
  // JWT
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Tenant — добавляем только если уже известен
  const tenantId = localStorage.getItem("tenant_id");
  if (tenantId) {
    config.headers["X-Tenant-ID"] = tenantId;
  }

  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      // попытка refresh, или редирект на /login
    }
    return Promise.reject(error);
  },
);

export default api;
```

> **Важно**: при логине через общий домен `tenant_id` ещё не известен — interceptor
> просто не добавит заголовок, и это корректное поведение.

---

## 4. Сторы

### Auth store (Zustand)

```typescript
// src/shared/stores/auth.ts
import { create } from "zustand";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  selectionToken: string | null;         // временный токен для выбора тенанта

  setTokens: (access: string, refresh: string) => void;
  setSelectionToken: (token: string) => void;
  clearSelectionToken: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem("access_token"),
  refreshToken: localStorage.getItem("refresh_token"),
  selectionToken: null,

  setTokens: (access, refresh) => {
    localStorage.setItem("access_token", access);
    localStorage.setItem("refresh_token", refresh);
    set({ accessToken: access, refreshToken: refresh, selectionToken: null });
  },

  setSelectionToken: (token) => set({ selectionToken: token }),
  clearSelectionToken: () => set({ selectionToken: null }),

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("tenant_id");
    set({ accessToken: null, refreshToken: null, selectionToken: null });
  },
}));
```

### Tenant store (Zustand)

```typescript
// src/shared/stores/tenant.ts
import { create } from "zustand";

interface TenantInfo {
  tenantId: string;
  slug: string;
  name: string;
  logoUrl: string | null;
  primaryColor: string | null;
  siteUrl: string | null;
}

interface TenantState extends TenantInfo {
  setTenant: (info: TenantInfo) => void;
  clear: () => void;
}

const initial: TenantInfo = {
  tenantId: localStorage.getItem("tenant_id") ?? "",
  slug: "",
  name: "",
  logoUrl: null,
  primaryColor: null,
  siteUrl: null,
};

export const useTenantStore = create<TenantState>((set) => ({
  ...initial,

  setTenant: (info) => {
    localStorage.setItem("tenant_id", info.tenantId);
    set(info);
  },

  clear: () => {
    localStorage.removeItem("tenant_id");
    set({ ...initial, tenantId: "" });
  },
}));
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

## 6. Умный логин (Smart Login)

Заголовок `X-Tenant-ID` при логине теперь **опциональный**. Бэкенд сам определяет, к какому тенанту относится пользователь.

### 6.1 Два сценария формы логина

**Сценарий A — кастомный домен (тенант известен из домена):**

SPA загружается на `admin.client1.com`, резолвит тенант, показывает лого и название компании. При отправке `POST /auth/login` передаётся `X-Tenant-ID`.

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

**Сценарий B — общий домен (тенант неизвестен):**

SPA загружается на `admin.mediann.dev`, домен не резолвится в конкретный тенант. Показывается лого платформы. `X-Tenant-ID` **не передаётся**.

```
┌─────────────────────────────┐
│      [logo платформы]       │
│                             │
│   Email: [____________]     │
│   Пароль: [___________]     │
│                             │
│      [ Войти ]              │
└─────────────────────────────┘
```

### 6.2 Запрос

```http
POST /api/v1/auth/login
X-Tenant-ID: 550e8400-...  (ОПЦИОНАЛЬНО — передавайте если тенант известен из домена)
Content-Type: application/json

{
  "email": "admin@client1.com",
  "password": "..."
}
```

### 6.3 Ответ — вариант 1: один тенант (или `X-Tenant-ID` передан)

Если у пользователя один тенант, или `X-Tenant-ID` был указан — обычный логин:

```json
{
  "status": "success",
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
    "force_password_change": false
  }
}
```

### 6.4 Ответ — вариант 2: несколько тенантов

Если `X-Tenant-ID` НЕ передан и у пользователя доступ к 2+ организациям:

```json
{
  "status": "tenant_selection_required",
  "tenants": [
    {
      "tenant_id": "550e8400-...",
      "name": "Компания 1",
      "slug": "company1",
      "logo_url": "https://cdn.mediann.dev/...",
      "primary_color": "#1a5276",
      "admin_domain": "admin.company1.com",
      "role": "site_owner"
    },
    {
      "tenant_id": "660f9500-...",
      "name": "Компания 2",
      "slug": "company2",
      "logo_url": null,
      "primary_color": "#27ae60",
      "admin_domain": "admin.company2.com",
      "role": "content_manager"
    }
  ],
  "selection_token": "eyJ..."
}
```

### 6.5 Ответ — вариант 3: аккаунт в другой организации (redirect)

Если `X-Tenant-ID` передан (из домена), но пользователь зарегистрирован только в **другом** тенанте и **не является** суперюзером / platform_owner:

```json
{
  "status": "tenant_redirect_required",
  "tenant": {
    "tenant_id": "22c020ec-...",
    "name": "Другая Компания",
    "slug": "other-company",
    "logo_url": "https://cdn.mediann.dev/...",
    "primary_color": "#e74c3c",
    "admin_domain": "admin.other-company.com",
    "role": "editor"
  },
  "message": "Your account belongs to a different organization"
}
```

> **Примечание:** суперюзеры и platform_owner получат `status: "success"` с токенами (cross-tenant авто-логин).

### 6.5.1 Экран редиректа на другую организацию

Показывается если бэкенд вернул `status: "tenant_redirect_required"`:

```
┌─────────────────────────────────────────┐
│                                         │
│   Ваш аккаунт принадлежит              │
│   организации «Другая Компания»         │
│                                         │
│   [logo]                                │
│                                         │
│   ┌─────────────────────────────────┐   │
│   │  Перейти в admin.other-co.com   │   │
│   └─────────────────────────────────┘   │
│                                         │
│   Или обратитесь к администратору       │
│   вашей организации                     │
│                                         │
└─────────────────────────────────────────┘
```

Логика кнопки:
- Если `tenant.admin_domain` **не null** — кнопка ведёт на `https://{admin_domain}`
- Если `tenant.admin_domain` **null** — кнопка скрыта, показать текст «Обратитесь к администратору вашей организации для получения ссылки на админ-панель»

### 6.6 Экран выбора тенанта

Показывается **только** если бэкенд вернул `status: "tenant_selection_required"`:

```
┌─────────────────────────────────┐
│   Выберите организацию           │
│                                  │
│   ┌─────────────────────────┐    │
│   │ [logo] Компания 1       │    │
│   │        site_owner        │    │
│   └─────────────────────────┘    │
│   ┌─────────────────────────┐    │
│   │ [logo] Компания 2       │    │
│   │        content_manager   │    │
│   └─────────────────────────┘    │
│                                  │
└─────────────────────────────────┘
```

### 6.6 Завершение логина — `POST /auth/select-tenant`

После выбора организации фронтенд вызывает:

```http
POST /api/v1/auth/select-tenant
Content-Type: application/json

{
  "selection_token": "eyJ...",
  "tenant_id": "550e8400-..."
}
```

**Авторизация не требуется** — `selection_token` подтверждает, что пароль уже проверен.

**Ответ** — такой же `LoginResponse` как при обычном логине:

```json
{
  "status": "success",
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "user": { ... }
}
```

### 6.7 Как фронтенд определяет тип ответа

```typescript
type LoginResult = LoginSuccess | TenantSelectionRequired | TenantRedirectRequired;

interface LoginSuccess {
  status: "success";
  tokens: TokenPair;
  user: UserResponse;
}

interface TenantSelectionRequired {
  status: "tenant_selection_required";
  tenants: TenantOption[];
  selection_token: string;
}

interface TenantRedirectRequired {
  status: "tenant_redirect_required";
  tenant: TenantOption;
  message: string;
}

async function handleLogin(email: string, password: string) {
  const result: LoginResult = await api.post("/auth/login", { email, password });

  switch (result.status) {
    case "success":
      localStorage.setItem("access_token", result.tokens.access_token);
      localStorage.setItem("refresh_token", result.tokens.refresh_token);
      router.push("/dashboard");
      break;

    case "tenant_selection_required":
      showTenantPicker(result.tenants, result.selection_token);
      break;

    case "tenant_redirect_required":
      // Показать экран редиректа с информацией о тенанте пользователя
      showTenantRedirect(result.tenant, result.message);
      break;
  }
}
```

**Важно:** `selection_token` хранится ТОЛЬКО в state компонента (НЕ в localStorage). Он действует 15 минут.

### 6.8 Смена пароля синхронизируется

При смене пароля через `POST /auth/me/password` или через сброс пароля — новый пароль автоматически обновляется во **всех** тенантах, где есть учётная запись с этим email. Пользователь всегда входит с одним и тем же паролем.

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

**Важно:** при switch-tenant бэкенд автоматически добавляет старый access_token в blacklist (Redis). Поэтому после переключения старый токен больше не работает.

Эндпоинт имеет rate-limit: **5 переключений в минуту** на пользователя.

### 7.3 Компонент свитчера (React пример)

```tsx
"use client";
import { useState } from "react";
import { useTenantStore } from "@/shared/stores/tenant";

interface TenantAccessInfo {
  tenant_id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  admin_domain: string | null;
}

export function TenantSwitcher({
  tenants,
  currentTenantId,
  onSwitch,
}: {
  tenants: TenantAccessInfo[];
  currentTenantId: string;
  onSwitch: (tenant: TenantAccessInfo) => void;
}) {
  const [open, setOpen] = useState(false);
  if (tenants.length <= 1) return null;

  const current = tenants.find((t) => t.tenant_id === currentTenantId);

  return (
    <div className="relative">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-2">
        {current?.logo_url && <img src={current.logo_url} className="h-6 w-6 rounded" />}
        <span>{current?.name}</span>
      </button>

      {open && (
        <ul className="absolute mt-1 w-60 rounded-lg border bg-white shadow-lg">
          {tenants.map((t) => (
            <li
              key={t.tenant_id}
              className={`flex cursor-pointer items-center gap-3 px-4 py-2 hover:bg-gray-50 ${
                t.tenant_id === currentTenantId ? "bg-gray-100" : ""
              }`}
              onClick={() => { onSwitch(t); setOpen(false); }}
            >
              {t.logo_url && <img src={t.logo_url} className="h-8 w-8 rounded" />}
              <div>
                <div className="font-medium">{t.name}</div>
                {t.admin_domain && <div className="text-xs text-gray-500">{t.admin_domain}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

### 7.4 Когда показывать свитчер

Если `tenants.length === 1`, свитчер не нужен. Показывайте только лого и название. Компонент `TenantSwitcher` выше уже содержит эту проверку (`if (tenants.length <= 1) return null`).

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
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
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
| POST | `/auth/login` | Умный логин (`X-Tenant-ID` опционален). Возвращает `LoginResponse`, `TenantSelectionRequired` или `TenantRedirectRequired` |
| POST | `/auth/select-tenant` | **Завершение логина** после выбора тенанта (без авторизации, использует `selection_token`) |
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
| GET | `/tenants/{id}/domains` | Список доменов тенанта (с `ssl_status`, `dns_verified_at`, `ssl_provisioned_at`) |
| POST | `/tenants/{id}/domains` | Добавить домен (автоматически запускает SSL provisioning) |
| PATCH | `/tenants/{id}/domains/{domain_id}` | Обновить (is_primary, ssl_status) |
| DELETE | `/tenants/{id}/domains/{domain_id}` | Удалить домен |
| GET | `/tenants/{id}/domains/{domain_id}/ssl-status` | Polling статуса SSL (для фронтенд-поллинга) |
| POST | `/tenants/{id}/domains/{domain_id}/verify` | Проверить DNS + запустить SSL provisioning |

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

#### LoginResponse (Smart Login)

```typescript
// Discriminated union: проверяйте поле status
type LoginResult = LoginSuccess | TenantSelectionRequired | TenantRedirectRequired;

interface LoginSuccess {
  status: "success";
  tokens: TokenPair;
  user: UserResponse;
}

interface TenantSelectionRequired {
  status: "tenant_selection_required";
  tenants: TenantOption[];
  selection_token: string;  // JWT, 15 min TTL, хранить ТОЛЬКО в state
}

interface TenantRedirectRequired {
  status: "tenant_redirect_required";
  tenant: TenantOption;     // единственный тенант, в котором зарегистрирован юзер
  message: string;          // "Your account belongs to a different organization"
}

interface TenantOption {
  tenant_id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  primary_color: string | null;
  admin_domain: string | null;
  role: string | null;  // роль пользователя в этом тенанте
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}
```

#### SelectTenantRequest / Response

```typescript
// POST /auth/select-tenant — Request body
interface SelectTenantRequest {
  selection_token: string;
  tenant_id: string;
}

// Response — LoginSuccess (status: "success")
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
// POST /auth/switch-tenant — Request body
interface SwitchTenantRequest {
  tenant_id: string;
}

// Response — TokenPair
```

#### TenantDomainResponse

```typescript
type SSLStatus = "pending" | "verifying" | "active" | "error";

interface TenantDomainResponse {
  id: string;
  tenant_id: string;
  domain: string;                    // "admin.client1.com"
  is_primary: boolean;
  ssl_status: SSLStatus;
  dns_verified_at: string | null;    // ISO 8601
  ssl_provisioned_at: string | null; // ISO 8601
  created_at: string;                // ISO 8601
  updated_at: string;
}
```

#### TenantDomainSSLStatusResponse

```typescript
interface TenantDomainSSLStatusResponse {
  domain_id: string;
  domain: string;
  ssl_status: SSLStatus;
  dns_verified_at: string | null;
  ssl_provisioned_at: string | null;
  message?: string;
}
```

#### DNSVerifyResponse

```typescript
interface DNSVerifyResponse {
  ok: boolean;
  cname_target: string | null;
  expected_target: string;    // "tenants.mediann.dev"
  message: string;
}
```

---

## Чек-лист интеграции

### Bootstrap

- [ ] Резолв тенанта из `window.location.hostname` при загрузке SPA
- [ ] Стор тенанта (Zustand) заполняется до монтирования приложения
- [ ] Если домен не резолвится — показать форму логина без лого (общий домен)
- [ ] При наличии `access_token` в localStorage — проверить `GET /auth/me`

### Логин

- [ ] `X-Tenant-ID` header **только** в запросе `/auth/login` и **только** если тенант известен из домена
- [ ] Обработка ответа `status: "success"` — сохранить токены, перейти на dashboard
- [ ] Обработка ответа `status: "tenant_selection_required"` — показать экран выбора тенанта
- [ ] Обработка ответа `status: "tenant_redirect_required"` — показать экран редиректа на организацию пользователя
- [ ] Экран редиректа: если `tenant.admin_domain` есть — кнопка «Перейти», иначе — «Обратитесь к администратору»
- [ ] Экран выбора тенанта: список с логотипом, названием и ролью
- [ ] При выборе тенанта — `POST /auth/select-tenant` с `selection_token` + `tenant_id`
- [ ] `selection_token` хранить ТОЛЬКО в state компонента (не в localStorage)
- [ ] Проверка `force_password_change` — если `true`, редирект на смену пароля

### После логина

- [ ] `GET /auth/me/tenants` — определить нужен ли свитчер
- [ ] `GET /auth/me/features` — каталог фич для sidebar
- [ ] Брендинг: CSS-переменные из `primary_color` + `logo_url`

### Tenant Switcher

- [ ] Свитчер отображается если `tenants.length > 1`
- [ ] Переключение через `POST /switch-tenant` → сохранить новые токены
- [ ] После переключения — `window.location.reload()` для сброса всех кэшей
- [ ] Loading overlay при переключении

### Interceptors

- [ ] `Authorization: Bearer {token}` на всех авторизованных запросах
- [ ] `X-Tenant-ID` **обязательно** на всех запросах после логина (берётся из `localStorage` / стора)
- [ ] При логине (`POST /auth/login`) — `X-Tenant-ID` добавляется **только** если тенант известен из домена
- [ ] `POST /auth/select-tenant` — `X-Tenant-ID` **не** нужен (tenant_id в теле запроса)
- [ ] 401 interceptor: попытка refresh → при ошибке → на логин
- [ ] 403 `tenant_inactive` → полноэкранный блок «Организация приостановлена»
- [ ] 403 `feature_disabled` → информация «Раздел недоступен»

### Ошибки

- [ ] Экран ошибки: домен не найден (404)
- [ ] Экран ошибки: организация приостановлена (403)
- [ ] Экран ошибки: нет доступа к организации (401 от switch-tenant)

### Управление доменами

- [ ] Таблица доменов с колонками: Домен, Тип, SSL статус, Основной, Действия
- [ ] Модалка добавления домена: выбор типа (поддомен/кастомный), ввод домена, checkbox is_primary
- [ ] Для кастомных доменов — показать инструкцию CNAME в модалке
- [ ] Кнопка «Проверить DNS» для доменов с `ssl_status === "pending"` или `"error"`
- [ ] Polling `GET .../ssl-status` каждые 10 сек для доменов с `ssl_status === "pending"` или `"verifying"`
- [ ] Остановка polling при `ssl_status === "active"` или `"error"`
- [ ] Disabled состояния кнопок во время `verifying`
- [ ] Зелёный badge + ссылка для `active`, красный badge + retry для `error`

### Разработка

- [ ] Локальная разработка через `/etc/hosts`
