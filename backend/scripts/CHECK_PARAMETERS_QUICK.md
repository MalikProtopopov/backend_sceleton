# БЫСТРАЯ ПРОВЕРКА ПАРАМЕТРОВ В БД
# Скопируй и выполни на сервере

# ====================================
# Вариант 1: Проверка через docker exec
# ====================================

# Проверить есть ли параметры вообще:
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "SELECT COUNT(*) FROM parameters;"

# Показать все параметры с деталями:
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT 
    id,
    name,
    slug,
    value_type,
    is_active,
    is_filterable,
    scope,
    created_at
FROM parameters 
ORDER BY created_at DESC;
"

# Показать значения параметров (для enum-типов):
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT 
    pv.id,
    p.name as parameter_name,
    pv.label as value_label,
    pv.slug as value_slug,
    pv.is_active,
    pv.sort_order
FROM parameter_values pv
JOIN parameters p ON p.id = pv.parameter_id
ORDER BY p.name, pv.sort_order;
"

# Проверить tenant_id параметров (если у тебя несколько тенантов):
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT tenant_id, COUNT(*) as count 
FROM parameters 
GROUP BY tenant_id;
"

# ====================================
# Вариант 2: Интерактивная psql-сессия
# ====================================

# Зайти в psql:
docker exec -it cms_postgres_prod psql -U cms_user -d cms_db

# Затем внутри psql выполнить:
# SELECT * FROM parameters;
# SELECT * FROM parameter_values;
# \q  -- выйти


# ====================================
# Вариант 3: Через API (если уже есть токен)
# ====================================

# Получить токен (замени EMAIL и PASSWORD):
curl -X POST https://api.mediann.dev/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"your@email.com","password":"yourpassword"}'

# Затем запросить параметры (замени TOKEN и TENANT_ID):
curl https://api.mediann.dev/api/v1/admin/parameters?page=1&page_size=100 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "X-Tenant-ID: YOUR_TENANT_ID"


# ====================================
# ТИПИЧНЫЕ ПРОБЛЕМЫ:
# ====================================

# 1. Параметры есть, но неактивные:
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT name, is_active FROM parameters;
"
# Решение: UPDATE parameters SET is_active = true WHERE id = '...';

# 2. Не тот tenant_id:
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT id, slug FROM tenants;
"
# Сравни tenant_id в токене с tenant_id параметров

# 3. Миграция не применилась:
docker exec cms_backend_prod alembic current
docker exec cms_backend_prod alembic upgrade head

# 4. Права доступа (проверь роль пользователя):
docker exec cms_postgres_prod psql -U cms_user -d cms_db -c "
SELECT u.email, r.name as role 
FROM admin_users u 
LEFT JOIN roles r ON r.id = u.role_id 
WHERE u.email = 'your@email.com';
"
