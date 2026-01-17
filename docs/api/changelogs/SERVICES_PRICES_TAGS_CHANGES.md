# Изменения в Services API: Добавлены цены и теги

> Обновление от 17.01.2026

---

## Краткое описание изменений

Добавлена возможность управления **ценами** и **тегами** для услуг с поддержкой множественных значений и локализации.

### 🔑 Ключевые изменения

1. **Новые поля в ответах API**:
   - `prices` - массив цен в разных валютах
   - `tags` - массив тегов для категоризации

2. **Новые админские endpoints** для управления ценами и тегами

3. **Локализация**: Цены и теги привязаны к конкретной локали (ru, en и т.д.)

---

## 📋 Что изменилось в публичных API

### GET `/api/v1/public/services` и `/api/v1/public/services/{slug}`

**Добавлены два новых поля в ответе:**

```json
{
  "id": "service-uuid",
  "title": "Юридические услуги",
  "slug": "yuridicheskie-uslugi",
  // ... остальные поля ...
  
  // ✨ НОВОЕ: Список цен для текущей локали
  "prices": [
    {"price": 1500.0, "currency": "RUB"},
    {"price": 20.0, "currency": "USD"}
  ],
  
  // ✨ НОВОЕ: Список тегов для текущей локали
  "tags": ["консультация", "юридические услуги", "срочно"]
}
```

**Важно:**
- Если цен/тегов нет для текущей локали, поля будут пустыми массивами: `[]`
- В списке (`/public/services`) также возвращаются `prices` и `tags`

---

## 🛠️ Новые админские endpoints

### Управление ценами

#### 1. Добавить цену
```
POST /api/v1/admin/services/{service_id}/prices
```

**Request Body:**
```json
{
  "locale": "ru",
  "price": 1500.00,
  "currency": "RUB"  // или "USD"
}
```

**Response (201):**
```json
{
  "id": "price-uuid",
  "service_id": "service-uuid",
  "locale": "ru",
  "price": 1500.00,
  "currency": "RUB",
  "created_at": "2026-01-17T10:00:00Z",
  "updated_at": "2026-01-17T10:00:00Z"
}
```

**Особенности:**
- Можно добавить несколько цен для одной услуги
- Уникальность: `service_id + locale + currency`
- Поддерживаемые валюты: `RUB`, `USD`
- Ошибка 400, если цена уже существует для `locale + currency`

---

#### 2. Обновить цену
```
PATCH /api/v1/admin/services/{service_id}/prices/{price_id}
```

**Request Body:**
```json
{
  "price": 1800.00,
  "currency": "RUB"  // опционально
}
```

---

#### 3. Удалить цену
```
DELETE /api/v1/admin/services/{service_id}/prices/{price_id}
```

**Response:** `204 No Content`

---

### Управление тегами

#### 1. Добавить тег
```
POST /api/v1/admin/services/{service_id}/tags
```

**Request Body:**
```json
{
  "locale": "ru",
  "tag": "консультация"
}
```

**Response (201):**
```json
{
  "id": "tag-uuid",
  "service_id": "service-uuid",
  "locale": "ru",
  "tag": "консультация",
  "created_at": "2026-01-17T10:00:00Z",
  "updated_at": "2026-01-17T10:00:00Z"
}
```

**Особенности:**
- Можно добавить несколько тегов для одной услуги
- Уникальность: `service_id + locale + tag`
- Ошибка 400, если тег уже существует для `locale + tag`

---

#### 2. Обновить тег
```
PATCH /api/v1/admin/services/{service_id}/tags/{tag_id}
```

**Request Body:**
```json
{
  "locale": "ru",      // обязательно
  "tag": "новый тег"   // обязательно
}
```

**Примечание:** При изменении `locale` или `tag` проверяется уникальность новой комбинации.

---

#### 3. Удалить тег
```
DELETE /api/v1/admin/services/{service_id}/tags/{tag_id}
```

**Response:** `204 No Content`

---

## 📦 Изменения в админских ответах

### GET `/api/v1/admin/services/{service_id}`

Теперь возвращает полный объект услуги с массивами `prices` и `tags`:

```json
{
  "id": "service-uuid",
  "tenant_id": "tenant-uuid",
  "icon": "⚖️",
  "image_url": "https://...",
  "is_published": true,
  "sort_order": 0,
  "version": 1,
  "locales": [...],
  
  // ✨ НОВОЕ
  "prices": [
    {
      "id": "price-uuid",
      "service_id": "service-uuid",
      "locale": "ru",
      "price": 1500.00,
      "currency": "RUB",
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  
  // ✨ НОВОЕ
  "tags": [
    {
      "id": "tag-uuid",
      "service_id": "service-uuid",
      "locale": "ru",
      "tag": "консультация",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

---

## 💻 Примеры использования для фронтенда

### Отображение цен и тегов (публичный API)

```jsx
const ServiceCard = ({ service }) => {
  return (
    <Card>
      <h2>{service.title}</h2>
      <p>{service.short_description}</p>
      
      {/* Отображение цен */}
      {service.prices && service.prices.length > 0 && (
        <div className="prices">
          <strong>Цены:</strong>
          {service.prices.map((price, index) => (
            <span key={index}>
              {price.price} {price.currency}
            </span>
          ))}
        </div>
      )}
      
      {/* Отображение тегов */}
      {service.tags && service.tags.length > 0 && (
        <div className="tags">
          {service.tags.map((tag, index) => (
            <Badge key={index}>{tag}</Badge>
          ))}
        </div>
      )}
    </Card>
  )
}
```

### Добавление цены (админка)

```javascript
// Добавить цену в RUB
const addPrice = async (serviceId, locale, price, currency) => {
  try {
    const response = await fetch(`/api/v1/admin/services/${serviceId}/prices`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        locale: locale,
        price: parseFloat(price),
        currency: currency.toUpperCase()
      })
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to add price')
    }
    
    return await response.json()
  } catch (error) {
    console.error('Error adding price:', error.message)
    throw error
  }
}

// Использование
await addPrice('service-uuid', 'ru', 1500, 'RUB')
await addPrice('service-uuid', 'ru', 20, 'USD')
```

### Добавление тега (админка)

```javascript
// Добавить тег
const addTag = async (serviceId, locale, tag) => {
  try {
    const response = await fetch(`/api/v1/admin/services/${serviceId}/tags`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        locale: locale,
        tag: tag
      })
    })
    
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Failed to add tag')
    }
    
    return await response.json()
  } catch (error) {
    console.error('Error adding tag:', error.message)
    throw error
  }
}

// Использование
await addTag('service-uuid', 'ru', 'консультация')
await addTag('service-uuid', 'ru', 'юридические услуги')
```

---

## ⚠️ Важные замечания

1. **Обратная совместимость**: Старые поля `price_from` и `price_currency` остаются, но рекомендуется использовать новый массив `prices`

2. **Локализация**: Цены и теги фильтруются по текущей локали в публичных API

3. **Валидация**: 
   - Валюты должны быть в верхнем регистре: `RUB`, `USD`
   - Цены должны быть >= 0 с 2 знаками после запятой
   - Теги: 1-100 символов

4. **Ошибки**: При попытке добавить дубликат (цена или тег) вернется 400 с сообщением об ошибке

---

## 📚 Полная документация

Подробная документация доступна в файле: [`05-services.md`](./05-services.md)

---

## 🚀 Миграция

Для работы с новыми функциями необходимо выполнить миграцию базы данных:
```bash
alembic upgrade head
```

Migration: `013_add_service_prices_and_tags.py`

