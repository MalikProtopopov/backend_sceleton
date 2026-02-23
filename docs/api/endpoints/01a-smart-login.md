# Smart Login & Tenant Selection API

> Обновление: 2026-02-23
> Заменяет старый флоу с обязательным X-Tenant-ID

## Обзор

Новый флоу логина позволяет пользователю авторизоваться **без указания конкретной организации**. Бэкенд автоматически определяет тенант, или предлагает выбор если пользователь состоит в нескольких организациях.

```
                           POST /auth/login
                          (X-Tenant-ID опционален)
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼              ▼
              X-Tenant-ID     1 тенант       2+ тенантов
              передан         найден         найдено
                    │             │              │
                    ▼             ▼              ▼
              LoginResponse  LoginResponse  TenantSelectionRequired
              (status:       (status:       (status:
               "success")     "success")     "tenant_selection_required")
                                                │
                                                ▼
                                       POST /auth/select-tenant
                                                │
                                                ▼
                                          LoginResponse
                                          (status: "success")
```

---

## `POST /auth/login`

### Описание

Авторизация пользователя. Заголовок `X-Tenant-ID` теперь **опциональный**.

### Headers

| Header | Обязательный | Описание |
|--------|:---:|----------|
| `Content-Type` | Да | `application/json` |
| `X-Tenant-ID` | Нет | UUID тенанта. Если передан — логин в конкретный тенант (старое поведение). Если не передан — автоопределение. |

### Request Body

```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

### Response: Success (один тенант или X-Tenant-ID передан)

**HTTP 200**

```json
{
  "status": "success",
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 1800
  },
  "user": {
    "id": "a1b2c3d4-...",
    "tenant_id": "550e8400-...",
    "email": "user@example.com",
    "first_name": "Иван",
    "last_name": "Петров",
    "is_active": true,
    "is_superuser": false,
    "force_password_change": false,
    "avatar_url": null,
    "last_login_at": "2026-02-23T12:00:00Z",
    "role": {
      "id": "...",
      "name": "site_owner",
      "is_system": true,
      "permissions": [...]
    },
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-02-23T12:00:00Z"
  }
}
```

### Response: Tenant Selection Required (несколько тенантов)

**HTTP 200**

```json
{
  "status": "tenant_selection_required",
  "tenants": [
    {
      "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Компания Альфа",
      "slug": "alpha",
      "logo_url": "https://cdn.example.com/logos/alpha.png",
      "primary_color": "#1a5276",
      "admin_domain": "admin.alpha.com",
      "role": "site_owner"
    },
    {
      "tenant_id": "660f9500-f39c-52e5-b827-557766551111",
      "name": "Компания Бета",
      "slug": "beta",
      "logo_url": null,
      "primary_color": "#27ae60",
      "admin_domain": "admin.beta.com",
      "role": "content_manager"
    }
  ],
  "selection_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Errors

| HTTP | Error Code | Описание |
|------|------------|----------|
| 401 | `invalid_credentials` | Неверный email или пароль |
| 403 | `tenant_inactive` | Организация приостановлена |
| 429 | `rate_limit_exceeded` | Слишком много попыток (10/мин на IP) |

---

## `POST /auth/select-tenant`

### Описание

Завершает логин после выбора организации. Вызывается когда `/auth/login` вернул `status: "tenant_selection_required"`.

**Авторизация не требуется** — `selection_token` подтверждает, что пароль уже проверен.

### Request Body

```json
{
  "selection_token": "eyJhbGciOiJIUzI1NiIs...",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Response

**HTTP 200** — такой же `LoginResponse` как при обычном логине:

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

### Errors

| HTTP | Error Code | Описание |
|------|------------|----------|
| 401 | `invalid_credentials` | Нет доступа к этой организации |
| 401 | `token_expired` | selection_token истёк (15 мин TTL) |
| 401 | `invalid_token` | Невалидный selection_token |
| 403 | `tenant_inactive` | Организация приостановлена |
| 429 | `rate_limit_exceeded` | Слишком много попыток |

---

## `POST /auth/switch-tenant`

### Описание

Переключает авторизованного пользователя на другую организацию. Выдаёт новую пару JWT-токенов. Старый access_token автоматически отзывается (blacklist).

**Требует авторизации:** `Authorization: Bearer <access_token>`

**Rate-limit:** 5 переключений в минуту на пользователя.

### Request Body

```json
{
  "tenant_id": "660f9500-..."
}
```

### Response

**HTTP 200**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Errors

| HTTP | Error Code | Описание |
|------|------------|----------|
| 401 | `invalid_credentials` | Нет доступа к этой организации |
| 403 | `tenant_inactive` | Организация приостановлена |
| 429 | `rate_limit_exceeded` | Слишком много переключений |

---

## `GET /auth/me/tenants`

### Описание

Возвращает список всех организаций, к которым пользователь имеет доступ (по email). Используется для отображения тенант-свитчера.

**Требует авторизации:** `Authorization: Bearer <access_token>`

### Response

**HTTP 200**

```json
{
  "current_tenant_id": "550e8400-...",
  "tenants": [
    {
      "tenant_id": "550e8400-...",
      "name": "Компания Альфа",
      "slug": "alpha",
      "logo_url": "https://cdn.example.com/logos/alpha.png",
      "primary_color": "#1a5276",
      "admin_domain": "admin.alpha.com"
    },
    {
      "tenant_id": "660f9500-...",
      "name": "Компания Бета",
      "slug": "beta",
      "logo_url": null,
      "primary_color": "#27ae60",
      "admin_domain": "admin.beta.com"
    }
  ]
}
```

---

## Selection Token

`selection_token` — это короткоживущий JWT (TTL 15 минут) со следующей структурой:

```json
{
  "email": "user@example.com",
  "tenant_ids": ["550e8400-...", "660f9500-..."],
  "type": "tenant_selection",
  "exp": 1708700000,
  "iat": 1708699100,
  "jti": "unique-token-id"
}
```

- Не даёт доступа к API (только к `POST /auth/select-tenant`)
- Ограничивает выбор тенантов списком `tenant_ids` из payload
- **Не сохранять в localStorage** — хранить только в state компонента

---

## Синхронизация паролей

При смене пароля (`POST /auth/me/password`) или сбросе через email (`POST /auth/reset-password`) новый пароль автоматически обновляется во **всех** записях `AdminUser` с тем же email. Пользователь всегда входит с одним и тем же паролем, независимо от тенанта.

---

## TypeScript Types

```typescript
// Discriminated union для ответа /auth/login
type LoginResult = LoginSuccess | TenantSelectionRequired;

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

interface SelectTenantRequest {
  selection_token: string;
  tenant_id: string;
}

interface SwitchTenantRequest {
  tenant_id: string;
}

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
```
