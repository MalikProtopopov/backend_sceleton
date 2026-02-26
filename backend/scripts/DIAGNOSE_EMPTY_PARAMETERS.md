# БЫСТРАЯ ДИАГНОСТИКА ПОЧЕМУ НЕ ВИДНЫ ПАРАМЕТРЫ

## В базе данных всё ОК:
- ✅ Параметр "Цвет" (enum) создан
- ✅ 3 значения: Красный, Желтый, Оранжевый
- ✅ is_active = true
- ✅ tenant_id = 6dc384ef-c364-49df-aaa7-22941c7f3422
- ✅ Миграция 035 применена

## ПРОБЛЕМА: API возвращает пустой список

### Шаг 1: Проверь логи бэкенда при запросе

Открой логи в реальном времени:
```bash
docker logs -f cms_backend_prod --tail=100
```

Затем в браузере сделай запрос на список параметров и посмотри что выводится в логах.

Ищи строки с:
- `GET /api/v1/admin/parameters` — сам запрос
- `tenant_id` — какой тенант передан
- Ошибки или WARNING

### Шаг 2: Проверь через curl (с сервера)

```bash
# Получи токен (замени EMAIL и PASSWORD):
TOKEN=$(curl -s -X POST https://api.mediann.dev/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpass"}' \
  | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo "Token: ${TOKEN:0:30}..."

# Запроси параметры:
curl -v https://api.mediann.dev/api/v1/admin/parameters?page=1&page_size=10 \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: 6dc384ef-c364-49df-aaa7-22941c7f3422"
```

Смотри на:
- HTTP статус (должен быть 200, не 401/403)
- Поле `total` в ответе
- Массив `items`

### Шаг 3: Проверь tenant_id в JWT токене

```bash
# Декодируй payload JWT (вторая часть токена):
echo "$TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | python3 -m json.tool

# Или онлайн: https://jwt.io
```

Найди поле `tenant_id` в payload. Должно быть `6dc384ef-c364-49df-aaa7-22941c7f3422`.

**Если там другой tenant_id** — значит ты залогинен под другим тенантом и параметры не видны (они привязаны к tenant_id).

### Шаг 4: Проверь права пользователя

```bash
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT 
    u.email, 
    r.name as role,
    u.is_active,
    u.tenant_id
FROM admin_users u 
LEFT JOIN roles r ON r.id = u.role_id 
WHERE u.email = 'your@email.com';
"
```

Проверь:
- `is_active = t`
- `tenant_id` совпадает с `6dc384ef-c364-49df-aaa7-22941c7f3422`
- `role` не NULL (должна быть роль типа `site_owner` или `content_manager`)

### Шаг 5: Проверь права роли

```bash
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT 
    r.name as role,
    string_agg(p.name, ', ') as permissions
FROM roles r
LEFT JOIN role_permissions rp ON rp.role_id = r.id
LEFT JOIN permissions p ON p.id = rp.permission_id
WHERE r.tenant_id = '6dc384ef-c364-49df-aaa7-22941c7f3422'
GROUP BY r.id, r.name;
"
```

Должно быть право `catalog:read` (или просто `catalog` со всеми правами).

### Шаг 6: Проверь feature flag catalog_module

```bash
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT 
    t.name as tenant,
    ff.name as feature,
    ff.is_enabled
FROM feature_flags ff
JOIN tenants t ON t.id = ff.tenant_id
WHERE t.id = '6dc384ef-c364-49df-aaa7-22941c7f3422'
  AND ff.name = 'catalog_module';
"
```

Должно быть `is_enabled = t`. Если флаг выключен — все catalog API вернут 403.

---

## ТИПИЧНЫЕ ПРИЧИНЫ:

| Проблема | Как проверить | Решение |
|----------|---------------|---------|
| **Неправильный tenant_id в токене** | Декодировать JWT | Залогиниться под нужным тенантом |
| **Нет прав catalog:read** | Проверить роль и permissions | Добавить права роли |
| **Feature flag catalog_module выключен** | Проверить feature_flags таблицу | `UPDATE feature_flags SET is_enabled = true WHERE name = 'catalog_module'` |
| **Фронт не передаёт X-Tenant-ID** | Логи бэкенда | Исправить на фронте |
| **Параметр создан для другого тенанта** | Сравнить tenant_id параметра и пользователя | Пересоздать параметр для нужного тенанта |

---

## БЫСТРАЯ ПРОВЕРКА ЧЕРЕЗ CURL (на сервере):

```bash
# Всё в одной команде:
curl -s https://api.mediann.dev/api/v1/admin/parameters?page=1&page_size=10 \
  -H "Authorization: Bearer $(curl -s -X POST https://api.mediann.dev/api/v1/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"your@email.com","password":"yourpass"}' \
    | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)" \
  -H "X-Tenant-ID: 6dc384ef-c364-49df-aaa7-22941c7f3422" | jq '.'
```

Если вернётся `"total": 1` и в `items[]` будет параметр «Цвет» — значит API работает, проблема на фронте.
Если вернётся `"total": 0` — значит проблема с tenant_id или правами.
