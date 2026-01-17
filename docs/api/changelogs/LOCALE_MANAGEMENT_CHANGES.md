# Краткая сводка изменений: Управление локалями

## Что было реализовано

### Новые API Endpoints

Для каждой мультиязычной сущности добавлены 3 endpoints:

1. **POST** `/api/v1/admin/{resource}/{id}/locales` - Создать локаль
2. **PATCH** `/api/v1/admin/{resource}/{id}/locales/{locale_id}` - Обновить локаль
3. **DELETE** `/api/v1/admin/{resource}/{id}/locales/{locale_id}` - Удалить локаль

### Поддерживаемые ресурсы

**Company Module:**
- Services (`/admin/services/{id}/locales`)
- Employees (`/admin/employees/{id}/locales`)
- Practice Areas (`/admin/practice-areas/{id}/locales`)
- Advantages (`/admin/advantages/{id}/locales`)
- Addresses (`/admin/addresses/{id}/locales`)

**Content Module:**
- Topics (`/admin/topics/{id}/locales`)
- Articles (`/admin/articles/{id}/locales`)
- FAQ (`/admin/faq/{id}/locales`)
- Cases (`/admin/cases/{id}/locales`)

## Основные правила

1. **Минимум одна локаль** - нельзя удалить последнюю локаль у сущности
2. **Уникальность языка** - у одной сущности может быть только одна локаль для каждого языка
3. **Уникальность slug** - slug должен быть уникальным в пределах одного языка (locale) и tenant
4. **Права доступа** - все endpoints требуют permission `{resource}:update`

## Ошибки, которые нужно обрабатывать

### 1. Локаль уже существует (409)
```json
{
  "error_code": "locale_already_exists",
  "status": 409,
  "detail": "Service already has a locale for language 'ru'",
  "locale": "ru"
}
```
**Действие:** Показать сообщение и предложить обновить существующую локаль.

### 2. Минимум локалей (400)
```json
{
  "error_code": "minimum_locales_required",
  "status": 400,
  "detail": "Cannot delete the last locale. Service must have at least one locale."
}
```
**Действие:** Заблокировать кнопку удаления для последней локали.

### 3. Slug уже существует (409)
```json
{
  "error_code": "already_exists",
  "status": 409,
  "field": "slug",
  "value": "web-development",
  "locale": "ru"
}
```
**Действие:** Показать ошибку валидации под полем slug.

### 4. Локаль не найдена (404)
```json
{
  "error_code": "not_found",
  "status": 404,
  "detail": "ServiceLocale with id '...' not found"
}
```
**Действие:** Обновить список локалей (возможно, удалена другим пользователем).

## Быстрый старт для фронтенда

### 1. Получить список локалей
```typescript
const response = await fetch(`/api/v1/admin/services/${serviceId}`);
const service = await response.json();
const locales = service.locales; // Массив локалей
```

### 2. Создать локаль
```typescript
const response = await fetch(`/api/v1/admin/services/${serviceId}/locales`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    locale: 'ru',
    title: 'Название',
    slug: 'slug-ru',
    // ... остальные поля
  }),
});
```

### 3. Обновить локаль
```typescript
const response = await fetch(
  `/api/v1/admin/services/${serviceId}/locales/${localeId}`,
  {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      locale: 'ru', // Обязательно
      title: 'Новое название', // Опционально
      // Обновляются только переданные поля
    }),
  }
);
```

### 4. Удалить локаль
```typescript
// Проверить, что это не последняя локаль
if (locales.length <= 1) {
  alert('Нельзя удалить последнюю локаль');
  return;
}

const response = await fetch(
  `/api/v1/admin/services/${serviceId}/locales/${localeId}`,
  {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  }
);
```

## Полная документация

Подробная документация с примерами, схемами данных и рекомендациями находится в:
`docs/api/LOCALE_MANAGEMENT_API.md`

