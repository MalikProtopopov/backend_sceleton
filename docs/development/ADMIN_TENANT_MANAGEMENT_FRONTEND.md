# Управление организациями — фронтенд-документация для админки

> **Версия**: 1.0  
> **Дата**: 2026-02-23  
> **Доступ**: platform_owner / superuser  
> **Базовый URL API**: `https://api.mediann.dev/api/v1`

---

## Содержание

1. [Общая структура данных тенанта](#1-структура-данных-тенанта)
2. [Список организаций](#2-список-организаций)
3. [Создание организации](#3-создание-организации)
4. [Просмотр / редактирование организации](#4-просмотр-и-редактирование-организации)
5. [Управление лого](#5-управление-лого)
6. [Управление доменами (admin_domain)](#6-управление-доменами)
7. [Настройки организации (settings)](#7-настройки-организации)
8. [Feature Flags](#8-feature-flags)
9. [Удаление организации](#9-удаление-организации)
10. [Карта экранов → API](#10-карта-экранов--api)

---

## 1. Структура данных тенанта

Организация хранится в **трёх связанных сущностях**:

```
Tenant (основная таблица)
  ├── TenantSettings (1:1) — site_url, аналитика, email, SEO
  ├── TenantDomain[] (1:N) — админ-домены (admin.yastvo.com)
  └── FeatureFlag[] (1:N) — модули (блог, кейсы, FAQ...)
```

### Что где хранится — шпаргалка

| Что нужно изменить | Эндпоинт | Поле |
|---|---|---|
| Название, цвет, контакты | `PATCH /tenants/{id}` | `name`, `primary_color`, `contact_email`, `contact_phone` |
| Лого | `POST /tenants/{id}/logo` | multipart file |
| Админ-домен (admin.yastvo.com) | `POST/PATCH/DELETE /tenants/{id}/domains/{domain_id}` | `domain`, `is_primary` |
| Ссылка на клиентский сайт (site_url) | `PUT /tenants/{id}/settings` | `site_url` |
| Аналитика (GA, Метрика) | `PUT /tenants/{id}/settings` | `ga_tracking_id`, `ym_counter_id` |
| Email-настройки (SMTP) | `PUT /tenants/{id}/settings` | `email_provider`, `smtp_host`, ... |
| Включить/выключить модуль | `PATCH /feature-flags/{name}?tenant_id={id}` | `enabled` |

> **Важно**: поле `domain` в `PATCH /tenants/{id}` — это **legacy-поле**, оно **НЕ влияет** на резолв доменов и `admin_domain`. Для управления доменами используй только API `/tenants/{id}/domains/`.

---

## 2. Список организаций

### Экран

Таблица/список всех организаций с поиском, фильтрацией и пагинацией.

### API

```
GET /api/v1/tenants?page=1&page_size=20&search=yastvo&is_active=true&sort_by=name&sort_order=asc
Authorization: Bearer {token}
```

### Query-параметры

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|----------|
| `page` | int | 1 | Номер страницы |
| `page_size` | int | 20 (макс. 100) | Записей на странице |
| `search` | string | — | Поиск по названию (ilike) |
| `is_active` | bool | — | Фильтр по статусу |
| `sort_by` | string | `created_at` | Поле сортировки: `name` или `created_at` |
| `sort_order` | string | `desc` | `asc` или `desc` |

### Ответ

```json
{
  "items": [
    {
      "id": "22c020ec-0a8a-486e-8699-6dfe1f10f54f",
      "name": "Yastvo",
      "slug": "yastvo",
      "domain": "yastvo.com",
      "is_active": true,
      "contact_email": "admin@yastvo.com",
      "contact_phone": "+79001234567",
      "primary_color": "#059669",
      "logo_url": "https://cdn.mediann.dev/tenants/yastvo/logo.png",
      "version": 3,
      "users_count": 5,
      "created_at": "2026-02-20T10:00:00Z",
      "updated_at": "2026-02-23T15:30:00Z",
      "settings": { "..." }
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

### Колонки таблицы (рекомендация)

| Колонка | Поле | Заметки |
|---------|------|---------|
| Лого | `logo_url` | Миниатюра или fallback (первая буква `name`) |
| Название | `name` | Ссылка на страницу редактирования |
| Slug | `slug` | — |
| Статус | `is_active` | Badge: зелёный/серый |
| Пользователи | `users_count` | Число |
| Создан | `created_at` | Дата |

---

## 3. Создание организации

### API

```
POST /api/v1/tenants
Authorization: Bearer {token}
Content-Type: application/json
```

### Тело запроса

```json
{
  "name": "Yastvo",
  "slug": "yastvo",
  "domain": null,
  "is_active": true,
  "contact_email": "admin@yastvo.com",
  "contact_phone": "+79001234567",
  "primary_color": "#059669"
}
```

### Поля формы создания

| Поле | Обязательное | Тип | Валидация | Описание |
|------|-------------|-----|-----------|----------|
| `name` | Да | text | 1–255 символов | Название организации |
| `slug` | Да | text | 2–100 символов, только `[a-z0-9-]`, уникальный | URL-идентификатор |
| `is_active` | Нет | toggle | — | Активна ли организация (default: true) |
| `contact_email` | Нет | email | макс. 255 | Контактный email |
| `contact_phone` | Нет | tel | макс. 50 | Контактный телефон |
| `primary_color` | Нет | color picker | `#RRGGBB` | Брендовый цвет |

> **Не показывать** поле `domain` в форме создания — это legacy-поле. Домены добавляются отдельно через раздел «Домены» после создания.

### Что создаётся автоматически

При `POST /tenants` бэкенд автоматически:
1. Создаёт `TenantSettings` с дефолтами (locale=ru, timezone=Europe/Moscow)
2. Включает **все** feature flags

### Ответ (201 Created)

Возвращает полный `TenantResponse` (см. раздел 4).

### Ошибки

| Код | Ситуация | Что показать |
|-----|---------|-------------|
| 409 `already_exists` | Slug уже занят | «Организация с таким slug уже существует» |
| 422 | Невалидные данные | Показать ошибки валидации у полей |

---

## 4. Просмотр и редактирование организации

### Экран

Страница деталей организации с вкладками:
- **Основное** — название, slug, контакты, цвет, статус
- **Домены** — список admin-доменов (см. раздел 6)
- **Настройки** — site_url, аналитика, email (см. раздел 7)
- **Модули** — feature flags (см. раздел 8)
- **Пользователи** — список юзеров тенанта (отдельная документация)

### API — получить тенант

```
GET /api/v1/tenants/{tenant_id}
Authorization: Bearer {token}
```

### Ответ — TenantResponse

```json
{
  "id": "22c020ec-0a8a-486e-8699-6dfe1f10f54f",
  "name": "Yastvo",
  "slug": "yastvo",
  "domain": null,
  "is_active": true,
  "contact_email": "admin@yastvo.com",
  "contact_phone": "+79001234567",
  "primary_color": "#059669",
  "logo_url": "https://cdn.mediann.dev/tenants/yastvo/logo.png",
  "version": 3,
  "users_count": 5,
  "created_at": "2026-02-20T10:00:00Z",
  "updated_at": "2026-02-23T15:30:00Z",
  "settings": {
    "id": "uuid",
    "tenant_id": "uuid",
    "default_locale": "ru",
    "timezone": "Europe/Moscow",
    "date_format": "DD.MM.YYYY",
    "time_format": "HH:mm",
    "site_url": "https://yastvo.com",
    "notify_on_inquiry": true,
    "inquiry_email": null,
    "ga_tracking_id": null,
    "ym_counter_id": null,
    "email_provider": null,
    "smtp_host": null,
    "smtp_port": null,
    "smtp_user": null,
    "smtp_use_tls": true,
    "smtp_password_configured": false,
    "email_api_key_configured": false,
    "created_at": "...",
    "updated_at": "..."
  }
}
```

### API — обновить тенант

```
PATCH /api/v1/tenants/{tenant_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "Yastvo Updated",
  "primary_color": "#10b981",
  "version": 3
}
```

### Поля формы редактирования

| Поле | Тип | Валидация | Можно менять? |
|------|-----|-----------|--------------|
| `name` | text | 1–255 | Да |
| `slug` | text | — | **Только просмотр** (менять slug опасно) |
| `is_active` | toggle | — | Да (деактивация блокирует всех юзеров) |
| `contact_email` | email | макс. 255 | Да |
| `contact_phone` | tel | макс. 50 | Да |
| `primary_color` | color picker | `#RRGGBB` | Да |
| `version` | hidden | — | **Обязательно** передавать текущую версию |

### Optimistic Locking

Поле `version` **обязательно** при каждом PATCH. Если кто-то другой обновил тенант между моментом загрузки и отправкой формы — бэкенд вернёт:

| Код | Ситуация | Что делать |
|-----|---------|-----------|
| 409 `version_conflict` | Данные устарели | Показать «Данные были изменены другим пользователем. Обновите страницу.» + кнопка перезагрузки |

### Деактивация организации

При `is_active: false`:
- Все пользователи немедленно теряют доступ (следующий API-запрос → 403 `tenant_inactive`)
- Публичный API перестаёт отдавать контент
- **Суперюзеры и platform_owner не затрагиваются**

Рекомендуется показать confirm-диалог: «Все пользователи организации потеряют доступ. Продолжить?»

---

## 5. Управление лого

### Загрузить лого

```
POST /api/v1/tenants/{tenant_id}/logo
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: <binary>
```

| Параметр | Значение |
|----------|---------|
| Форматы | JPEG, PNG, WebP, GIF |
| Макс. размер | 10 MB |
| Ответ | `TenantResponse` с обновлённым `logo_url` |

### Удалить лого

```
DELETE /api/v1/tenants/{tenant_id}/logo
Authorization: Bearer {token}
```

Ответ: 204 No Content.

### UI

- Аватарка/превью текущего лого (или fallback — первая буква названия)
- Кнопка «Загрузить» → file input
- Кнопка «Удалить» (видна только если `logo_url !== null`)

---

## 6. Управление доменами

**Это ключевой раздел.** Домены из таблицы `tenant_domains` определяют:
- По какому адресу админка резолвит тенант (`GET /public/tenants/by-domain/...`)
- Какой `admin_domain` показывается в tenant switcher и модалке редиректа при логине
- CORS origins (автоматически)

### 6.1 Список доменов

```
GET /api/v1/tenants/{tenant_id}/domains
Authorization: Bearer {token}
```

**Ответ:**

```json
{
  "items": [
    {
      "id": "aaa-bbb-ccc",
      "tenant_id": "22c020ec-...",
      "domain": "admin.yastvo.com",
      "is_primary": true,
      "ssl_status": "active",
      "dns_verified_at": "2026-02-20T10:05:00Z",
      "ssl_provisioned_at": "2026-02-20T10:05:30Z",
      "created_at": "2026-02-20T10:00:00Z",
      "updated_at": "2026-02-23T15:30:00Z"
    },
    {
      "id": "ddd-eee-fff",
      "tenant_id": "22c020ec-...",
      "domain": "admin-yastvo.mediann.dev",
      "is_primary": false,
      "ssl_status": "pending",
      "dns_verified_at": null,
      "ssl_provisioned_at": null,
      "created_at": "2026-02-21T12:00:00Z",
      "updated_at": "2026-02-21T12:00:00Z"
    }
  ],
  "total": 2
}
```

### 6.2 Поля домена

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | ID записи домена |
| `tenant_id` | UUID | К какому тенанту привязан |
| `domain` | string | FQDN, например `admin.yastvo.com` |
| `is_primary` | bool | **Основной домен** — используется как `admin_domain` в ответах API (switcher, redirect) |
| `ssl_status` | string | `"pending"` / `"verifying"` / `"active"` / `"error"` |
| `dns_verified_at` | datetime / null | Когда DNS CNAME последний раз прошёл проверку |
| `ssl_provisioned_at` | datetime / null | Когда SSL-сертификат был успешно выпущен |
| `created_at` | datetime | — |
| `updated_at` | datetime | — |

#### Статусы SSL (`ssl_status`)

| Статус | Значение | UI |
|--------|----------|-----|
| `pending` | Ожидание настройки DNS | Жёлтый badge + инструкция CNAME + кнопка «Проверить DNS» |
| `verifying` | DNS подтверждён, выпускается сертификат | Спиннер + «Получаем SSL-сертификат...» |
| `active` | Сертификат выпущен и работает | Зелёный badge + ссылка `https://{domain}` |
| `error` | Ошибка при выпуске сертификата | Красный badge + текст ошибки + кнопка «Повторить» |

### 6.3 Добавить домен

```
POST /api/v1/tenants/{tenant_id}/domains
Authorization: Bearer {token}
Content-Type: application/json

{
  "domain": "admin.yastvo.com",
  "is_primary": true
}
```

| Поле | Обязательное | Валидация | Описание |
|------|-------------|-----------|----------|
| `domain` | Да | FQDN, 4–255 символов, уникальный | Например `admin.yastvo.com` |
| `is_primary` | Нет | bool, default: false | Если `true` — предыдущий primary автоматически сбрасывается |

**Ответ:** 201 + `TenantDomainResponse`

**Ошибки:**

| Код | Ситуация | Что показать |
|-----|---------|-------------|
| 409 | Домен уже привязан к другому тенанту | «Домен уже используется другой организацией» |
| 422 | Невалидный формат домена | «Введите корректный домен (например admin.client.com)» |

### 6.4 Обновить домен

```
PATCH /api/v1/tenants/{tenant_id}/domains/{domain_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "is_primary": true,
  "ssl_status": "active"
}
```

| Поле | Описание |
|------|----------|
| `is_primary` | Сделать основным (сбрасывает primary у других) |
| `ssl_status` | Обновить статус SSL: `"pending"`, `"verifying"`, `"active"`, `"error"` |

> **Менять `domain` нельзя** — нужно удалить и создать новый.

### 6.5 Удалить домен

```
DELETE /api/v1/tenants/{tenant_id}/domains/{domain_id}
Authorization: Bearer {token}
```

Ответ: 204 No Content.

### 6.6 Проверить DNS (Verify)

```
POST /api/v1/tenants/{tenant_id}/domains/{domain_id}/verify
Authorization: Bearer {token}
```

Проверяет CNAME-запись домена. Если DNS настроен правильно — автоматически запускает выпуск SSL-сертификата в фоне.

**Ответ:** `DNSVerifyResponse`

```json
{
  "ok": true,
  "cname_target": "tenants.mediann.dev",
  "expected_target": "tenants.mediann.dev",
  "message": "CNAME record configured correctly"
}
```

```json
{
  "ok": false,
  "cname_target": null,
  "expected_target": "tenants.mediann.dev",
  "message": "No CNAME or A record found for admin.yastvo.com. Add a CNAME record pointing to tenants.mediann.dev"
}
```

### 6.7 Проверить статус SSL (Polling)

```
GET /api/v1/tenants/{tenant_id}/domains/{domain_id}/ssl-status
Authorization: Bearer {token}
```

Легковесный эндпоинт для polling статуса SSL. Фронтенд вызывает каждые 10 секунд пока `ssl_status` не станет `active` или `error`.

**Ответ:** `TenantDomainSSLStatusResponse`

```json
{
  "domain_id": "aaa-bbb-ccc",
  "domain": "admin.yastvo.com",
  "ssl_status": "verifying",
  "dns_verified_at": "2026-02-24T10:00:00Z",
  "ssl_provisioned_at": null,
  "message": "DNS verified, obtaining SSL certificate..."
}
```

### 6.8 UI — таблица доменов

| Колонка | Поле | Описание |
|---------|------|----------|
| Домен | `domain` | Текст, ссылка `https://{domain}` (только если `ssl_status === "active"`) |
| Тип | — | Badge: «Платформа» (если `.mediann.dev`) или «Кастомный» |
| Основной | `is_primary` | Badge «Primary» или переключатель |
| SSL | `ssl_status` | Badge по статусу (см. таблицу статусов выше) |
| Действия | — | Кнопки: «Проверить DNS» (при `pending`/`error`), «Сделать основным», «Удалить» |

Кнопка «Добавить домен» → модальное окно:

#### Модалка добавления домена

1. **Тип домена** (radio):
   - «Поддомен Mediann» — автозаполняет `.mediann.dev` (поле ввода: только часть до `.mediann.dev`)
   - «Кастомный домен» — свободный ввод FQDN

2. **Поле ввода домена** (`domain`)

3. **Если выбран «Кастомный домен»** — показать инструкцию:
   > Добавьте у вашего DNS-провайдера CNAME-запись:
   > `{введённый_домен}` → `tenants.mediann.dev`

4. **Checkbox `is_primary`** — «Сделать основным»

5. **Кнопка «Добавить»** → `POST /tenants/{id}/domains`

#### Polling после добавления

После добавления кастомного домена (когда `ssl_status === "pending"` или `"verifying"`):

1. Показать блок с инструкцией по CNAME (для `pending`)
2. Показать кнопку «Проверить DNS» (для `pending` и `error`)
3. После нажатия «Проверить DNS» → `POST .../verify`
4. Если `ok: true` → начать polling `GET .../ssl-status` каждые 10 секунд
5. Если `ok: false` → показать сообщение из `message`
6. Polling: при `ssl_status === "active"` — остановить, показать зелёный badge
7. Polling: при `ssl_status === "error"` — остановить, показать красный badge + кнопку «Повторить»

#### UX-детали

- При `pending`: disabled кнопка «Сделать основным» (домен ещё не работает)
- При `verifying`: disabled все кнопки, спиннер
- При `error`: показать текст ошибки + кнопка «Повторить» (вызывает `/verify`)
- Для поддоменов `*.mediann.dev` — SSL статус всегда `active` (wildcard), кнопка «Проверить DNS» не нужна

### 6.9 TypeScript типы

```typescript
type SSLStatus = "pending" | "verifying" | "active" | "error";

interface TenantDomain {
  id: string;
  tenant_id: string;
  domain: string;
  is_primary: boolean;
  ssl_status: SSLStatus;
  dns_verified_at: string | null;
  ssl_provisioned_at: string | null;
  created_at: string;
  updated_at: string;
}

interface TenantDomainCreate {
  domain: string;        // FQDN, 4-255
  is_primary?: boolean;
}

interface TenantDomainUpdate {
  is_primary?: boolean;
  ssl_status?: SSLStatus;
}

interface TenantDomainListResponse {
  items: TenantDomain[];
  total: number;
}

interface TenantDomainSSLStatusResponse {
  domain_id: string;
  domain: string;
  ssl_status: SSLStatus;
  dns_verified_at: string | null;
  ssl_provisioned_at: string | null;
  message?: string;
}

interface DNSVerifyResponse {
  ok: boolean;
  cname_target: string | null;
  expected_target: string;
  message: string;
}
```

### 6.10 Zustand Store для доменов

```typescript
import { create } from "zustand";
import { api } from "@/lib/api";

interface DomainStore {
  domains: TenantDomain[];
  loading: boolean;
  pollingIntervals: Map<string, ReturnType<typeof setInterval>>;

  fetchDomains: (tenantId: string) => Promise<void>;
  addDomain: (tenantId: string, data: TenantDomainCreate) => Promise<TenantDomain>;
  updateDomain: (tenantId: string, domainId: string, data: TenantDomainUpdate) => Promise<void>;
  deleteDomain: (tenantId: string, domainId: string) => Promise<void>;
  verifyDomain: (tenantId: string, domainId: string) => Promise<DNSVerifyResponse>;
  startPolling: (tenantId: string, domainId: string) => void;
  stopPolling: (domainId: string) => void;
  stopAllPolling: () => void;
}

export const useDomainStore = create<DomainStore>((set, get) => ({
  domains: [],
  loading: false,
  pollingIntervals: new Map(),

  fetchDomains: async (tenantId) => {
    set({ loading: true });
    const { data } = await api.get<TenantDomainListResponse>(
      `/tenants/${tenantId}/domains`
    );
    set({ domains: data.items, loading: false });

    // Auto-start polling for domains in transitional states
    data.items
      .filter((d) => d.ssl_status === "pending" || d.ssl_status === "verifying")
      .forEach((d) => get().startPolling(tenantId, d.id));
  },

  addDomain: async (tenantId, payload) => {
    const { data } = await api.post<TenantDomain>(
      `/tenants/${tenantId}/domains`,
      payload
    );
    set((s) => ({ domains: [...s.domains, data] }));
    if (data.ssl_status !== "active") {
      get().startPolling(tenantId, data.id);
    }
    return data;
  },

  updateDomain: async (tenantId, domainId, payload) => {
    const { data } = await api.patch<TenantDomain>(
      `/tenants/${tenantId}/domains/${domainId}`,
      payload
    );
    set((s) => ({
      domains: s.domains.map((d) => (d.id === domainId ? data : d)),
    }));
  },

  deleteDomain: async (tenantId, domainId) => {
    await api.delete(`/tenants/${tenantId}/domains/${domainId}`);
    get().stopPolling(domainId);
    set((s) => ({
      domains: s.domains.filter((d) => d.id !== domainId),
    }));
  },

  verifyDomain: async (tenantId, domainId) => {
    const { data } = await api.post<DNSVerifyResponse>(
      `/tenants/${tenantId}/domains/${domainId}/verify`
    );
    if (data.ok) {
      get().startPolling(tenantId, domainId);
    }
    return data;
  },

  startPolling: (tenantId, domainId) => {
    const { pollingIntervals } = get();
    if (pollingIntervals.has(domainId)) return; // already polling

    const interval = setInterval(async () => {
      try {
        const { data } = await api.get<TenantDomainSSLStatusResponse>(
          `/tenants/${tenantId}/domains/${domainId}/ssl-status`
        );
        set((s) => ({
          domains: s.domains.map((d) =>
            d.id === domainId
              ? { ...d, ssl_status: data.ssl_status,
                  dns_verified_at: data.dns_verified_at,
                  ssl_provisioned_at: data.ssl_provisioned_at }
              : d
          ),
        }));
        if (data.ssl_status === "active" || data.ssl_status === "error") {
          get().stopPolling(domainId);
        }
      } catch {
        // Ignore polling errors
      }
    }, 10_000);

    set((s) => {
      const next = new Map(s.pollingIntervals);
      next.set(domainId, interval);
      return { pollingIntervals: next };
    });
  },

  stopPolling: (domainId) => {
    const { pollingIntervals } = get();
    const interval = pollingIntervals.get(domainId);
    if (interval) {
      clearInterval(interval);
      set((s) => {
        const next = new Map(s.pollingIntervals);
        next.delete(domainId);
        return { pollingIntervals: next };
      });
    }
  },

  stopAllPolling: () => {
    const { pollingIntervals } = get();
    pollingIntervals.forEach((interval) => clearInterval(interval));
    set({ pollingIntervals: new Map() });
  },
}));
```

### 6.11 Как `admin_domain` попадает в ответы API

`admin_domain` **нигде не хранится отдельно** — бэкенд вычисляет его динамически:

```sql
SELECT domain FROM tenant_domains 
WHERE tenant_id = ? AND is_primary = true
LIMIT 1
```

Это значение подставляется в:
- Ответ `POST /auth/login` → `tenant.admin_domain` (при `tenant_redirect_required` и `tenant_selection_required`)
- Ответ `GET /auth/me/tenants` → `tenants[].admin_domain` (для tenant switcher)

**Поэтому**: чтобы `admin_domain` появился — **необходимо** добавить домен через `POST /tenants/{id}/domains` с `is_primary: true`.

---

## 7. Настройки организации

### API

```
PUT /api/v1/tenants/{tenant_id}/settings
Authorization: Bearer {token}
Content-Type: application/json
```

> Метод **PUT** — передавайте все поля. Не переданные поля будут обновлены дефолтными значениями.

### Все поля settings

#### Основные

| Поле | Тип | По умолчанию | Описание |
|------|-----|-------------|----------|
| `site_url` | string / null | null | URL клиентского фронта (например `https://yastvo.com`). Используется для SEO, CORS. |
| `default_locale` | string | `"ru"` | Язык по умолчанию |
| `timezone` | string | `"Europe/Moscow"` | Часовой пояс |
| `date_format` | string | `"DD.MM.YYYY"` | Формат даты |
| `time_format` | string | `"HH:mm"` | Формат времени |

#### Уведомления

| Поле | Тип | По умолчанию | Описание |
|------|-----|-------------|----------|
| `notify_on_inquiry` | bool | true | Уведомлять о новых заявках |
| `inquiry_email` | string / null | null | Email для уведомлений о заявках |
| `telegram_chat_id` | string / null | null | Telegram chat ID для уведомлений |

#### Аналитика

| Поле | Тип | Описание |
|------|-----|----------|
| `ga_tracking_id` | string / null | Google Analytics ID (например `G-XXXXXXXXXX`) |
| `ym_counter_id` | string / null | Yandex.Metrika counter ID или полный HTML-код (макс. 5000 символов) |

#### SEO

| Поле | Тип | Описание |
|------|-----|----------|
| `allowed_domains` | string[] / null | Разрешённые домены для sitemap |
| `sitemap_static_pages` | object[] / null | Статические страницы для sitemap (каждая: `path`, `priority`, `changefreq`) |
| `robots_txt_custom_rules` | string / null | Кастомные правила для robots.txt |
| `indexnow_key` | string / null | IndexNow API key |
| `indexnow_enabled` | bool | false | Включить IndexNow |
| `llms_txt_enabled` | bool | false | Включить llms.txt |
| `llms_txt_custom_content` | string / null | Контент для llms.txt |

#### Верификация вебмастера

| Поле | Тип | Описание |
|------|-----|----------|
| `yandex_verification_code` | string / null | Код верификации Яндекс (формат: `yandex_821edd51f146c052`) |
| `google_verification_code` | string / null | Код верификации Google (формат: `google1234567890abcdef`) |
| `google_verification_meta` | string / null | Meta-тег Google для верификации |

#### Email / SMTP

| Поле | Тип | Описание |
|------|-----|----------|
| `email_provider` | string / null | `"smtp"`, `"sendgrid"`, `"mailgun"`, `"console"` или `null` (глобальный дефолт) |
| `email_from_address` | string / null | Адрес отправителя |
| `email_from_name` | string / null | Имя отправителя |
| `smtp_host` | string / null | SMTP-сервер |
| `smtp_port` | int / null | Порт (587=STARTTLS, 465=SSL) |
| `smtp_user` | string / null | SMTP-логин |
| `smtp_use_tls` | bool | true | STARTTLS |
| `smtp_password` | string / null | **Write-only!** Пароль SMTP. Не возвращается в ответах. |
| `email_api_key` | string / null | **Write-only!** API-ключ SendGrid/Mailgun. Не возвращается в ответах. |

### Ответ — TenantSettingsResponse

Такой же как в `settings` внутри `TenantResponse`, плюс два boolean-поля:

| Поле | Описание |
|------|----------|
| `smtp_password_configured` | `true` если SMTP-пароль задан |
| `email_api_key_configured` | `true` если API-ключ задан |

> Сами секреты (`smtp_password`, `email_api_key`) **никогда** не возвращаются. Фронт показывает только индикатор «настроено / не настроено».

### Тестирование email

```
POST /api/v1/tenants/{tenant_id}/settings/email-test
Authorization: Bearer {token}
Content-Type: application/json

{
  "to_email": "test@example.com"
}
```

Ответ:

```json
{
  "success": true,
  "provider": "smtp",
  "error": null
}
```

### UI — вкладка «Настройки»

Рекомендуется разбить на секции:
1. **Основное** — `site_url`, `default_locale`, `timezone`, `date_format`, `time_format`
2. **Уведомления** — `notify_on_inquiry`, `inquiry_email`, `telegram_chat_id`
3. **Аналитика** — `ga_tracking_id`, `ym_counter_id`
4. **SEO** — `sitemap_static_pages`, `robots_txt_custom_rules`, верификация
5. **Email** — провайдер, SMTP-настройки, кнопка «Отправить тестовое письмо»

---

## 8. Feature Flags

### Список флагов

```
GET /api/v1/feature-flags?tenant_id={tenant_id}
Authorization: Bearer {token}
```

**Ответ:**

```json
{
  "items": [
    {
      "id": "uuid",
      "tenant_id": "uuid",
      "feature_name": "blog_module",
      "enabled": true,
      "description": "Блог / Статьи",
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "available_features": {
    "blog_module": { "name": "Блог / Статьи", "description": "..." },
    "cases_module": { "name": "Кейсы / Портфолио", "description": "..." },
    "reviews_module": { "name": "Отзывы", "description": "..." },
    "faq_module": { "name": "Вопросы и ответы", "description": "..." },
    "team_module": { "name": "Команда / Сотрудники", "description": "..." },
    "services_module": { "name": "Услуги", "description": "..." },
    "seo_advanced": { "name": "Расширенное SEO", "description": "..." },
    "multilang": { "name": "Мультиязычность", "description": "..." },
    "analytics_advanced": { "name": "Расширенная аналитика", "description": "..." }
  }
}
```

### Переключить флаг

```
PATCH /api/v1/feature-flags/{feature_name}?tenant_id={tenant_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "enabled": false
}
```

### UI — вкладка «Модули»

Список карточек/строк с toggle-переключателем для каждого модуля:

| Модуль | Название | Toggle |
|--------|---------|--------|
| `blog_module` | Блог / Статьи | ✅ |
| `cases_module` | Кейсы / Портфолио | ✅ |
| `reviews_module` | Отзывы | ☐ |
| `faq_module` | FAQ | ✅ |
| ... | ... | ... |

При отключении модуля — confirm-диалог: «Все пользователи потеряют доступ к этому разделу. Продолжить?»

---

## 9. Удаление организации

```
DELETE /api/v1/tenants/{tenant_id}
Authorization: Bearer {token}
```

Ответ: 204 No Content.

Это **soft delete** — данные сохраняются, но помечаются удалёнными.

Обязательно confirm-диалог: «Организация будет удалена. Все пользователи потеряют доступ. Это действие необратимо.»

---

## 10. Карта экранов → API

### Экран: Список организаций

| Действие | Метод | URL |
|----------|-------|-----|
| Загрузка списка | GET | `/tenants?page=1&page_size=20` |
| Поиск | GET | `/tenants?search=...` |
| Фильтр по статусу | GET | `/tenants?is_active=true` |

### Экран: Создание организации

| Действие | Метод | URL |
|----------|-------|-----|
| Создать | POST | `/tenants` |

### Экран: Редактирование организации

| Действие | Метод | URL | Тело |
|----------|-------|-----|------|
| Загрузка данных | GET | `/tenants/{id}` | — |
| Сохранить основное | PATCH | `/tenants/{id}` | `{ name, primary_color, ..., version }` |
| Загрузить лого | POST | `/tenants/{id}/logo` | multipart file |
| Удалить лого | DELETE | `/tenants/{id}/logo` | — |

### Вкладка: Домены

| Действие | Метод | URL | Тело |
|----------|-------|-----|------|
| Список доменов | GET | `/tenants/{id}/domains` | — |
| Добавить домен | POST | `/tenants/{id}/domains` | `{ domain, is_primary }` |
| Обновить домен | PATCH | `/tenants/{id}/domains/{domain_id}` | `{ is_primary?, ssl_status? }` |
| Удалить домен | DELETE | `/tenants/{id}/domains/{domain_id}` | — |

### Вкладка: Настройки

| Действие | Метод | URL | Тело |
|----------|-------|-----|------|
| Сохранить настройки | PUT | `/tenants/{id}/settings` | все поля settings |
| Тест email | POST | `/tenants/{id}/settings/email-test` | `{ to_email }` |
| Логи email | GET | `/tenants/{id}/email-logs?page=1&status=failed` | — |

### Вкладка: Модули (Feature Flags)

| Действие | Метод | URL | Тело |
|----------|-------|-----|------|
| Список флагов | GET | `/feature-flags?tenant_id={id}` | — |
| Переключить | PATCH | `/feature-flags/{name}?tenant_id={id}` | `{ enabled }` |

### Удаление

| Действие | Метод | URL |
|----------|-------|-----|
| Удалить организацию | DELETE | `/tenants/{id}` |

---

## TypeScript-типы

```typescript
// ─── Tenant ───
interface Tenant {
  id: string;
  name: string;
  slug: string;
  domain: string | null;        // legacy, не использовать
  is_active: boolean;
  contact_email: string | null;
  contact_phone: string | null;
  primary_color: string | null;
  logo_url: string | null;
  version: number;
  users_count: number;
  created_at: string;
  updated_at: string;
  settings: TenantSettings | null;
}

interface TenantCreate {
  name: string;                  // 1-255
  slug: string;                  // 2-100, [a-z0-9-]
  is_active?: boolean;
  contact_email?: string | null;
  contact_phone?: string | null;
  primary_color?: string | null; // #RRGGBB
}

interface TenantUpdate {
  name?: string;
  is_active?: boolean;
  contact_email?: string | null;
  contact_phone?: string | null;
  primary_color?: string | null;
  version: number;               // обязательно!
}

interface TenantListResponse {
  items: Tenant[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Domains ───
interface TenantDomain {
  id: string;
  tenant_id: string;
  domain: string;
  is_primary: boolean;
  ssl_status: "pending" | "active" | "error";
  created_at: string;
  updated_at: string;
}

interface TenantDomainCreate {
  domain: string;                // FQDN, 4-255
  is_primary?: boolean;
}

interface TenantDomainUpdate {
  is_primary?: boolean;
  ssl_status?: "pending" | "active" | "error";
}

interface TenantDomainListResponse {
  items: TenantDomain[];
  total: number;
}

// ─── Settings ───
interface TenantSettings {
  id: string;
  tenant_id: string;
  site_url: string | null;
  default_locale: string;
  timezone: string;
  date_format: string;
  time_format: string;
  notify_on_inquiry: boolean;
  inquiry_email: string | null;
  telegram_chat_id: string | null;
  default_og_image: string | null;
  ga_tracking_id: string | null;
  ym_counter_id: string | null;
  allowed_domains: string[] | null;
  sitemap_static_pages: SitemapStaticPage[] | null;
  robots_txt_custom_rules: string | null;
  indexnow_key: string | null;
  indexnow_enabled: boolean;
  llms_txt_enabled: boolean;
  llms_txt_custom_content: string | null;
  yandex_verification_code: string | null;
  google_verification_code: string | null;
  google_verification_meta: string | null;
  email_provider: "smtp" | "sendgrid" | "mailgun" | "console" | null;
  email_from_address: string | null;
  email_from_name: string | null;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  smtp_use_tls: boolean;
  smtp_password_configured: boolean;   // read-only
  email_api_key_configured: boolean;   // read-only
  created_at: string;
  updated_at: string;
}

interface TenantSettingsUpdate {
  site_url?: string | null;
  default_locale?: string;
  timezone?: string;
  // ... все поля из TenantSettings кроме id, tenant_id, *_configured, created_at, updated_at
  smtp_password?: string | null;       // write-only
  email_api_key?: string | null;       // write-only
}

interface SitemapStaticPage {
  path: string;
  priority: number;    // 0.0–1.0
  changefreq: string;
}

// ─── Feature Flags ───
interface FeatureFlag {
  id: string;
  tenant_id: string;
  feature_name: string;
  enabled: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
}

interface FeatureFlagsListResponse {
  items: FeatureFlag[];
  available_features: Record<string, { name: string; description: string }>;
}
```
