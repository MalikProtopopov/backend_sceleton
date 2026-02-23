# Чек-лист готовности админ-фронтенда к мульти-тенанту

> **Версия**: 1.0  
> **Дата**: 2026-02-23  
> **Назначение**: Пошаговая проверка — всё ли реализовано на фронте, чтобы можно было добавлять новые организации и они сразу работали через общую админку.

---

## Архитектура (для понимания)

```
Один SPA-билд админки → раздаётся Nginx на все admin-домены
  ↓
SPA читает window.location.hostname
  ↓
Резолвит тенант через GET /public/tenants/by-domain/{hostname}
  ↓
Получает tenant_id, name, logo_url, primary_color
  ↓
Показывает брендированную форму логина
```

Это значит: **ничего не нужно пересобирать** при добавлении новой организации. SPA универсальный — тенант определяется динамически из домена.

---

## 1. Bootstrap — резолв тенанта при загрузке

### Что должно быть реализовано

| # | Требование | API | Готово? |
|---|-----------|-----|---------|
| 1.1 | При загрузке SPA — вызвать резолв домена | `GET /api/v1/public/tenants/by-domain/{window.location.hostname}` | ☐ |
| 1.2 | Резолв происходит **до** рендера остального приложения | — | ☐ |
| 1.3 | Результат сохраняется в Zustand-стор (`useTenantStore`) | — | ☐ |
| 1.4 | Если `access_token` уже есть в localStorage — проверить сессию | `GET /api/v1/auth/me` | ☐ |

### API: резолв домена

```
GET /api/v1/public/tenants/by-domain/{hostname}
Авторизация: не нужна
```

**Ответ 200:**

```json
{
  "tenant_id": "uuid",
  "slug": "yastvo",
  "name": "Yastvo",
  "logo_url": "https://cdn.mediann.dev/tenants/yastvo/logo.png",
  "primary_color": "#059669",
  "site_url": "https://yastvo.com"
}
```

**Ответ 404** — домен не найден.

### Поля для стора

```typescript
interface TenantState {
  tenantId: string;       // UUID — для X-Tenant-ID
  slug: string;           // "yastvo"
  name: string;           // "Yastvo" — для отображения
  logoUrl: string | null; // URL лого — для шапки/логина
  primaryColor: string | null; // "#059669" — для CSS-переменных
  siteUrl: string | null; // "https://yastvo.com" — ссылка на клиентский фронт
}
```

### Два режима загрузки

| Ситуация | Домен резолвится (200) | Домен НЕ резолвится (404) |
|----------|----------------------|--------------------------|
| Лого | Лого тенанта | Лого платформы (Mediann) |
| Название | Название организации | Нет / "Mediann Platform" |
| `X-Tenant-ID` при логине | Отправляем | **Не отправляем** |
| Цвет | `primary_color` тенанта | Дефолтный цвет платформы |

---

## 2. Экран ошибки: домен не настроен

| # | Требование | Готово? |
|---|-----------|---------|
| 2.1 | Если резолв вернул 404 — показать полноэкранный блок «Домен не настроен» | ☐ |
| 2.2 | Текст: hostname + «не связан ни с одной организацией» | ☐ |
| 2.3 | Текст: «Обратитесь к администратору платформы» | ☐ |

**Или** (альтернатива): при 404 показать форму логина в режиме «общего домена» — без лого тенанта, без `X-Tenant-ID`.

---

## 3. Брендинг — CSS-переменные

| # | Требование | Готово? |
|---|-----------|---------|
| 3.1 | `primary_color` → CSS-переменная `--color-primary` | ☐ |
| 3.2 | Светлый вариант → `--color-primary-light` (primary + 12% opacity) | ☐ |
| 3.3 | `logo_url` → отображение в шапке / sidebar / форме логина | ☐ |
| 3.4 | Если `logo_url` = null — показать fallback (первая буква названия или иконку) | ☐ |

```typescript
function applyBranding(color: string | null, logoUrl: string | null) {
  const root = document.documentElement;
  if (color) {
    root.style.setProperty("--color-primary", color);
    root.style.setProperty("--color-primary-light", `${color}20`);
  }
}
```

---

## 4. Форма логина — Smart Login

### Запрос

```
POST /api/v1/auth/login
Content-Type: application/json
X-Tenant-ID: {tenant_id}          ← ТОЛЬКО если тенант известен из домена!

{
  "email": "user@example.com",
  "password": "..."
}
```

### Три варианта ответа (discriminated union по полю `status`)

| # | `status` | Что делать | Готово? |
|---|---------|-----------|---------|
| 4.1 | `"success"` | Сохранить токены → dashboard | ☐ |
| 4.2 | `"tenant_selection_required"` | Показать экран выбора тенанта | ☐ |
| 4.3 | `"tenant_redirect_required"` | Показать модалку/экран редиректа | ☐ |

---

### 4.1 Ответ `status: "success"`

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
    "id": "uuid",
    "tenant_id": "uuid",
    "email": "user@example.com",
    "first_name": "Иван",
    "last_name": "Петров",
    "force_password_change": false
  }
}
```

**Действия фронта:**

| # | Действие | Готово? |
|---|---------|---------|
| 4.1.1 | `localStorage.setItem("access_token", tokens.access_token)` | ☐ |
| 4.1.2 | `localStorage.setItem("refresh_token", tokens.refresh_token)` | ☐ |
| 4.1.3 | Если `user.force_password_change === true` → редирект на `/change-password` | ☐ |
| 4.1.4 | Иначе → редирект на `/dashboard` | ☐ |

---

### 4.2 Ответ `status: "tenant_selection_required"`

```json
{
  "status": "tenant_selection_required",
  "tenants": [
    {
      "tenant_id": "uuid-1",
      "name": "Компания 1",
      "slug": "company1",
      "logo_url": "https://...",
      "primary_color": "#1a5276",
      "admin_domain": "admin.company1.com",
      "role": "site_owner"
    },
    {
      "tenant_id": "uuid-2",
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

**Экран выбора тенанта:**

| # | Требование | Готово? |
|---|-----------|---------|
| 4.2.1 | Показать список организаций (карточками) | ☐ |
| 4.2.2 | Каждая карточка: `logo_url` (или fallback), `name`, `role` | ☐ |
| 4.2.3 | `selection_token` хранить ТОЛЬКО в state (НЕ в localStorage) | ☐ |
| 4.2.4 | По клику на карточку → вызвать `POST /auth/select-tenant` | ☐ |

**Завершение логина после выбора:**

```
POST /api/v1/auth/select-tenant
Content-Type: application/json
Авторизация: НЕ нужна

{
  "selection_token": "eyJ...",
  "tenant_id": "uuid-выбранного-тенанта"
}
```

Ответ — такой же как `status: "success"` (токены + user). Далее обработка как в п.4.1.

---

### 4.3 Ответ `status: "tenant_redirect_required"`

Возникает когда пользователь вводит верные креды на домене **чужого** тенанта.

```json
{
  "status": "tenant_redirect_required",
  "tenant": {
    "tenant_id": "uuid",
    "name": "Yastvo",
    "slug": "yastvo",
    "logo_url": null,
    "primary_color": "#059669",
    "admin_domain": "admin.yastvo.com",
    "role": "marketer"
  },
  "message": "Your account belongs to a different organization"
}
```

**Модалка/экран редиректа:**

| # | Требование | Готово? |
|---|-----------|---------|
| 4.3.1 | Показать название организации из `tenant.name` | ☐ |
| 4.3.2 | Показать лого из `tenant.logo_url` (или fallback) | ☐ |
| 4.3.3 | Показать роль из `tenant.role` | ☐ |
| 4.3.4 | **Если `tenant.admin_domain` есть** → кнопка «Перейти в {admin_domain}» → `window.location.href = "https://{admin_domain}"` | ☐ |
| 4.3.5 | **Если `tenant.admin_domain` = null** → текст «Обратитесь к администратору организации для получения ссылки» | ☐ |
| 4.3.6 | Кнопка «Назад» / «Вернуться к форме входа» — сброс state | ☐ |

---

## 5. HTTP Interceptor (Axios)

| # | Требование | Готово? |
|---|-----------|---------|
| 5.1 | `Authorization: Bearer {token}` — на всех авторизованных запросах | ☐ |
| 5.2 | `X-Tenant-ID` — на `POST /auth/login` ТОЛЬКО если тенант известен из домена | ☐ |
| 5.3 | `X-Tenant-ID` — **НЕ нужен** на `POST /auth/select-tenant` | ☐ |
| 5.4 | 401 → попытка refresh (`POST /auth/refresh`) → если ошибка → на `/login` | ☐ |
| 5.5 | 403 `tenant_inactive` → полноэкранный блок «Организация приостановлена» | ☐ |
| 5.6 | 403 `feature_disabled` → «Раздел недоступен» (restriction_level: organization) | ☐ |
| 5.7 | 403 `permission_denied` → «Нет доступа» (restriction_level: user) | ☐ |

### Refresh-токен

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

Ответ:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

---

## 6. После логина — Tenant Switcher

### Получить список организаций

```
GET /api/v1/auth/me/tenants
Authorization: Bearer {token}
```

**Ответ:**

```json
{
  "current_tenant_id": "uuid",
  "tenants": [
    {
      "tenant_id": "uuid-1",
      "name": "Yastvo",
      "slug": "yastvo",
      "logo_url": null,
      "primary_color": "#059669",
      "admin_domain": "admin.yastvo.com"
    },
    {
      "tenant_id": "uuid-2",
      "name": "Mediann",
      "slug": "mediann",
      "logo_url": "https://...",
      "primary_color": "#6366f1",
      "admin_domain": "admin.mediann.com"
    }
  ]
}
```

| # | Требование | Готово? |
|---|-----------|---------|
| 6.1 | Вызвать `GET /auth/me/tenants` после логина | ☐ |
| 6.2 | Если `tenants.length > 1` — показать компонент свитчера (sidebar / header) | ☐ |
| 6.3 | Если `tenants.length === 1` — свитчер скрыт, показать только лого/название | ☐ |
| 6.4 | Каждый элемент свитчера: `logo_url`, `name`, `admin_domain` | ☐ |
| 6.5 | Текущий тенант подсвечен (по `current_tenant_id`) | ☐ |

### Переключение тенанта

**Вариант A — редирект (рекомендуется):**

Если у целевого тенанта есть `admin_domain` → `window.location.href = "https://{admin_domain}"`.
Юзер перейдёт на другой домен и заново залогинится (или будет авто-вход если сессия жива).

**Вариант B — in-place через API:**

```
POST /api/v1/auth/switch-tenant
Authorization: Bearer {token}
Content-Type: application/json

{
  "tenant_id": "uuid-целевого-тенанта"
}
```

Ответ — новые токены:

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

| # | Требование | Готово? |
|---|-----------|---------|
| 6.6 | При переключении — показать loading overlay | ☐ |
| 6.7 | Сохранить новые токены в localStorage | ☐ |
| 6.8 | После сохранения — `window.location.reload()` для сброса кэшей | ☐ |

Rate limit: 5 переключений в минуту.

---

## 7. Каталог фич (sidebar)

```
GET /api/v1/auth/me/features
Authorization: Bearer {token}
```

**Ответ:**

```json
{
  "features": {
    "blog_module": true,
    "cases_module": true,
    "reviews_module": false,
    "faq_module": true,
    "team_module": true,
    "services_module": true,
    "seo_advanced": false,
    "multilang": false,
    "analytics_advanced": false
  }
}
```

| # | Требование | Готово? |
|---|-----------|---------|
| 7.1 | Вызвать `GET /auth/me/features` после логина | ☐ |
| 7.2 | Скрывать пункты sidebar для фич с `false` | ☐ |
| 7.3 | Если юзер вручную перейдёт по URL отключённой фичи — показать «Раздел недоступен» | ☐ |

---

## 8. Экраны ошибок

| # | Ситуация | Как определить | Что показать | Готово? |
|---|---------|---------------|-------------|---------|
| 8.1 | Домен не найден | Резолв вернул 404 | «Домен {hostname} не настроен. Обратитесь к администратору платформы» | ☐ |
| 8.2 | Организация приостановлена | 403 + `error_code: "tenant_inactive"` | Полноэкранный блок «Организация приостановлена» | ☐ |
| 8.3 | Раздел недоступен (фича отключена) | 403 + `error_code: "feature_disabled"` + `restriction_level: "organization"` | «Раздел недоступен. Обратитесь к администратору **платформы**» | ☐ |
| 8.4 | Нет прав (роль) | 403 + `error_code: "permission_denied"` + `restriction_level: "user"` | «Нет доступа. Обратитесь к администратору **организации**» | ☐ |
| 8.5 | Сессия истекла | 401 + refresh не удался | Редирект на `/login` | ☐ |

---

## 9. Полная карта API-вызовов (только те, что затрагивает мульти-тенант)

| Когда | Метод | URL | Авторизация | X-Tenant-ID | Тело запроса |
|-------|-------|-----|-------------|-------------|-------------|
| Загрузка SPA | GET | `/public/tenants/by-domain/{hostname}` | Нет | Нет | — |
| Логин | POST | `/auth/login` | Нет | Опционально (если домен резолвился) | `{ email, password }` |
| Выбор тенанта | POST | `/auth/select-tenant` | Нет | Нет | `{ selection_token, tenant_id }` |
| Refresh | POST | `/auth/refresh` | Нет | Нет | `{ refresh_token }` |
| Текущий юзер | GET | `/auth/me` | Bearer | Нет (tenant в JWT) | — |
| Список организаций юзера | GET | `/auth/me/tenants` | Bearer | Нет | — |
| Каталог фич | GET | `/auth/me/features` | Bearer | Нет | — |
| Переключение тенанта | POST | `/auth/switch-tenant` | Bearer | Нет | `{ tenant_id }` |
| Смена пароля | POST | `/auth/me/password` | Bearer | Нет | `{ current_password, new_password }` |
| Выход | POST | `/auth/logout` | Bearer | Нет | — |

> **Важно**: после логина `X-Tenant-ID` отдельным хедером **не нужен** — он зашит в JWT-токен. Interceptor должен слать только `Authorization: Bearer {token}`.

---

## 10. TypeScript-типы (скопировать в проект)

```typescript
// ─── Резолв домена ───
interface TenantByDomainResponse {
  tenant_id: string;
  slug: string;
  name: string;
  logo_url: string | null;
  primary_color: string | null;
  site_url: string | null;
}

// ─── Логин (discriminated union) ───
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

interface TenantOption {
  tenant_id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  primary_color: string | null;
  admin_domain: string | null;
  role: string | null;
}

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

interface UserResponse {
  id: string;
  tenant_id: string;
  email: string;
  first_name: string;
  last_name: string;
  force_password_change: boolean;
}

// ─── Список организаций юзера ───
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
  admin_domain: string | null;
}

// ─── Каталог фич ───
interface FeaturesResponse {
  features: Record<string, boolean>;
}
```

---

## 11. Быстрый smoke-тест после реализации

Проверить сценарии вручную:

| # | Сценарий | Ожидаемый результат | ✓ |
|---|---------|-------------------|---|
| T1 | Открыть `https://admin.yastvo.com` | SPA загрузится, покажет лого/цвет Yastvo | ☐ |
| T2 | Залогиниться юзером этого тенанта | `status: "success"` → dashboard | ☐ |
| T3 | Залогиниться юзером **другого** тенанта | `status: "tenant_redirect_required"` → модалка с кнопкой перехода | ☐ |
| T4 | Открыть `https://admin.unknown.com` (без записи) | Экран «Домен не настроен» | ☐ |
| T5 | Залогиниться юзером с 2+ тенантами на общем домене | `status: "tenant_selection_required"` → пикер | ☐ |
| T6 | Выбрать тенант в пикере | `POST /select-tenant` → dashboard | ☐ |
| T7 | Переключить тенант через свитчер | Редирект на другой домен или reload | ☐ |
| T8 | `force_password_change = true` | После логина → `/change-password` | ☐ |
| T9 | Организация деактивирована (`is_active=false`) | 403 → «Организация приостановлена» | ☐ |

---

## Минимальный набор для запуска (MVP)

Если нужно запуститься быстро, вот **минимум** без которого ничего не заработает:

1. **Bootstrap**: резолв тенанта из домена (п.1)
2. **Логин**: обработка трёх статусов (п.4.1, 4.2, 4.3)
3. **Interceptor**: `Authorization: Bearer` на все запросы, refresh при 401 (п.5)
4. **Брендинг**: хотя бы `primary_color` → CSS (п.3)

Всё остальное (свитчер, фичи, экраны ошибок) — можно добавлять итеративно.
