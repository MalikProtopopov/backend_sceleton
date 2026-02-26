#!/bin/bash
# Скрипт для проверки параметров в базе данных

echo "====================================="
echo "Проверка параметров в БД"
echo "====================================="
echo ""

# Подключение к БД
CONTAINER_NAME="${1:-cms_postgres_prod}"

echo "1. Проверяем наличие таблиц parameters и parameter_values..."
docker exec -it $CONTAINER_NAME psql -U cms_user -d cms_db -c "\dt parameters*"
echo ""

echo "2. Считаем сколько параметров в БД (по tenant_id)..."
docker exec -it $CONTAINER_NAME psql -U cms_user -d cms_db -c "
SELECT 
    tenant_id, 
    COUNT(*) as parameters_count,
    COUNT(*) FILTER (WHERE is_active = true) as active_count,
    COUNT(*) FILTER (WHERE value_type = 'enum') as enum_count
FROM parameters 
GROUP BY tenant_id
ORDER BY parameters_count DESC;
"
echo ""

echo "3. Показываем все параметры (последние 10)..."
docker exec -it $CONTAINER_NAME psql -U cms_user -d cms_db -c "
SELECT 
    id,
    name,
    slug,
    value_type,
    is_active,
    is_filterable,
    created_at
FROM parameters 
ORDER BY created_at DESC 
LIMIT 10;
"
echo ""

echo "4. Проверяем значения параметров (для enum-типов)..."
docker exec -it $CONTAINER_NAME psql -U cms_user -d cms_db -c "
SELECT 
    pv.id,
    p.name as parameter_name,
    pv.label,
    pv.slug,
    pv.is_active,
    pv.sort_order
FROM parameter_values pv
JOIN parameters p ON p.id = pv.parameter_id
ORDER BY p.name, pv.sort_order
LIMIT 20;
"
echo ""

echo "5. Проверяем связки параметр-категория..."
docker exec -it $CONTAINER_NAME psql -U cms_user -d cms_db -c "
SELECT 
    p.name as parameter_name,
    p.scope,
    COUNT(pc.category_id) as linked_categories_count
FROM parameters p
LEFT JOIN parameter_categories pc ON pc.parameter_id = p.id
GROUP BY p.id, p.name, p.scope
ORDER BY p.name;
"
echo ""

echo "6. Проверяем характеристики продуктов (сколько установлено)..."
docker exec -it $CONTAINER_NAME psql -U cms_user -d cms_db -c "
SELECT 
    p.name as parameter_name,
    COUNT(DISTINCT pc.product_id) as products_count,
    COUNT(*) as total_characteristics
FROM product_characteristics pc
JOIN parameters p ON p.id = pc.parameter_id
GROUP BY p.id, p.name
ORDER BY products_count DESC
LIMIT 10;
"
echo ""

echo "====================================="
echo "Готово!"
echo "====================================="
