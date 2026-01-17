# Troubleshooting Login 401 Error

## Проблема
Фронтенд получает 401 Unauthorized при попытке логина на `/auth/login`.

## Решение

### 1. Проверьте заголовок X-Tenant-ID

**Обязательно** передавайте заголовок `X-Tenant-ID` при логине:

```bash
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: f8f8a58e-6e2b-4779-a5fc-75a104cc10e7" \
  -d '{
    "email": "admin@test.example.com",
    "password": "admin123"
  }'
```

### 2. Правильный Tenant ID для тестовых данных

Для заполненных тестовых данных используйте:
- **Tenant ID**: `f8f8a58e-6e2b-4779-a5fc-75a104cc10e7`
- **Email**: `admin@test.example.com`
- **Password**: `admin123`

### 3. Возможные причины 401

#### A. Неправильный пароль
**Ответ**: `{"status": 401, "detail": "Invalid email or password"}`

**Решение**: Проверьте пароль. Для тестового пользователя: `admin123`

#### B. Пользователь не найден в tenant
**Ответ**: `{"status": 401, "detail": "Invalid email or password"}`

**Решение**: Убедитесь, что:
- Email правильный: `admin@test.example.com`
- Tenant ID правильный: `f8f8a58e-6e2b-4779-a5fc-75a104cc10e7`
- Пользователь существует в этом tenant

#### C. Пользователь неактивен
**Ответ**: `{"status": 401, "detail": "Account is disabled"}`

**Решение**: Проверьте, что `is_active = true` в базе данных

### 4. Проверка в базе данных

```sql
-- Проверить пользователя
SELECT 
    u.id,
    u.email,
    u.tenant_id,
    t.slug as tenant_slug,
    u.is_active,
    u.password_hash IS NOT NULL as has_password
FROM admin_users u
JOIN tenants t ON t.id = u.tenant_id
WHERE u.email = 'admin@test.example.com';

-- Проверить tenant
SELECT 
    id,
    slug,
    is_active,
    name
FROM tenants
WHERE id = 'f8f8a58e-6e2b-4779-a5fc-75a104cc10e7';
```

### 5. CORS настройки

Убедитесь, что фронтенд отправляет заголовок `X-Tenant-ID`. CORS настроен на разрешение всех заголовков (`allow_headers=["*"]`), но проверьте:

1. Заголовок отправляется в запросе
2. Браузер не блокирует заголовок (проверьте в DevTools → Network)
3. CORS preflight проходит успешно

### 6. Исключение login из refresh token interceptor

Как вы правильно заметили, **login endpoint НЕ должен обрабатываться refresh token interceptor**, так как 401 на логине - это нормальная ошибка (неверные credentials), а не повод обновлять токен.

**Рекомендация для фронтенда:**
```typescript
// В вашем HTTP interceptor
if (error.status === 401 && request.url.includes('/auth/login')) {
  // Не пытаться обновить токен для login endpoint
  // Просто показать ошибку пользователю
  return Promise.reject(error);
}
```

### 7. Тестирование

```bash
# ✅ Правильный запрос (должен вернуть 200)
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: f8f8a58e-6e2b-4779-a5fc-75a104cc10e7" \
  -d '{"email":"admin@test.example.com","password":"admin123"}'

# ❌ Без заголовка (вернет 400)
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@test.example.com","password":"admin123"}'

# ❌ Неправильный пароль (вернет 401)
curl -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: f8f8a58e-6e2b-4779-a5fc-75a104cc10e7" \
  -d '{"email":"admin@test.example.com","password":"wrong"}'
```

## Итоговые данные для входа

- **URL**: `http://localhost:3000/auth/login` (или `/api/v1/auth/login`)
- **Method**: `POST`
- **Headers**:
  - `Content-Type: application/json`
  - `X-Tenant-ID: f8f8a58e-6e2b-4779-a5fc-75a104cc10e7`
- **Body**:
  ```json
  {
    "email": "admin@test.example.com",
    "password": "admin123"
  }
  ```

## После успешного логина

После успешного логина вы получите:
- `access_token` - используйте в заголовке `Authorization: Bearer <token>`
- `refresh_token` - для обновления access token
- `user` - информация о пользователе, включая `tenant_id`

Все последующие запросы будут автоматически использовать `tenant_id` из токена, заголовок `X-Tenant-ID` больше не нужен.

