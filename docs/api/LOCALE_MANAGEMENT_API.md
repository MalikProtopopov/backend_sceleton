# API для управления локалями (Locale Management)

## Обзор

Реализована система управления локалями для всех мультиязычных сущностей через отдельные API endpoints. Это позволяет добавлять, редактировать и удалять локали независимо от основной сущности.

## Что было изменено

### Backend изменения:
1. **Создан переиспользуемый helper** (`app/core/locale_helpers.py`):
   - `MinimumLocalesError` - ошибка при попытке удалить последнюю локаль
   - `LocaleAlreadyExistsError` - ошибка при попытке создать дубликат
   - Вспомогательные функции для проверки и работы с локалями

2. **Добавлены схемы обновления** для всех моделей:
   - `ServiceLocaleUpdate`, `EmployeeLocaleUpdate`, `PracticeAreaLocaleUpdate`, `AdvantageLocaleUpdate`, `AddressLocaleUpdate`
   - `TopicLocaleUpdate`, `ArticleLocaleUpdate`, `FAQLocaleUpdate`, `CaseLocaleUpdate`

3. **Добавлены методы в сервисы**:
   - `create_locale()` - создание новой локали
   - `update_locale()` - обновление существующей локали
   - `delete_locale()` - удаление локали (с проверкой минимума)

4. **Добавлены API endpoints** для всех сущностей:
   - `POST /admin/{resource}/{id}/locales` - создать
   - `PATCH /admin/{resource}/{id}/locales/{locale_id}` - обновить
   - `DELETE /admin/{resource}/{id}/locales/{locale_id}` - удалить

### Важные особенности:
- ✅ Все операции транзакционные
- ✅ Проверка минимума локалей (нельзя удалить последнюю)
- ✅ Проверка уникальности slug в пределах locale
- ✅ Проверка на дубликат локали (один язык = одна локаль)
- ✅ Все endpoints требуют permission `{resource}:update`

## Поддерживаемые сущности

### Company Module
- **Service** (`/admin/services/{id}/locales`)
- **Employee** (`/admin/employees/{id}/locales`)
- **PracticeArea** (`/admin/practice-areas/{id}/locales`)
- **Advantage** (`/admin/advantages/{id}/locales`)
- **Address** (`/admin/addresses/{id}/locales`)

### Content Module
- **Topic** (`/admin/topics/{id}/locales`)
- **Article** (`/admin/articles/{id}/locales`)
- **FAQ** (`/admin/faq/{id}/locales`)
- **Case** (`/admin/cases/{id}/locales`)

## Endpoints

Все endpoints требуют аутентификации и permission `{resource}:update`.

### 1. Создание локали

**POST** `/api/v1/admin/{resource}/{resource_id}/locales`

**Пример для Service:**
```http
POST /api/v1/admin/services/1a719413-699e-458e-9e8f-e53d45c7b248/locales
Authorization: Bearer {token}
Content-Type: application/json

{
  "locale": "ru",
  "title": "Веб-разработка",
  "slug": "web-development-ru",
  "short_description": "Профессиональная разработка веб-приложений",
  "description": "Полное описание услуги...",
  "meta_title": "Веб-разработка | Наша компания",
  "meta_description": "SEO описание для поисковых систем"
}
```

**Успешный ответ (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "service_id": "1a719413-699e-458e-9e8f-e53d45c7b248",
  "locale": "ru",
  "title": "Веб-разработка",
  "slug": "web-development-ru",
  "short_description": "Профессиональная разработка веб-приложений",
  "description": "Полное описание услуги...",
  "meta_title": "Веб-разработка | Наша компания",
  "meta_description": "SEO описание для поисковых систем",
  "created_at": "2026-01-17T10:00:00Z",
  "updated_at": "2026-01-17T10:00:00Z"
}
```

**Пример для Article:**
```http
POST /api/v1/admin/articles/b3667d17-0d7f-40cc-ad45-9b409ebfe203/locales
Authorization: Bearer {token}
Content-Type: application/json

{
  "locale": "ru",
  "title": "Как выбрать правильную CMS",
  "slug": "how-to-choose-cms",
  "excerpt": "Краткое описание статьи",
  "content": "Полный текст статьи...",
  "meta_title": "Как выбрать CMS | Блог",
  "meta_description": "Руководство по выбору CMS"
}
```

### 2. Обновление локали

**PATCH** `/api/v1/admin/{resource}/{resource_id}/locales/{locale_id}`

**Пример:**
```http
PATCH /api/v1/admin/services/1a719413-699e-458e-9e8f-e53d45c7b248/locales/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer {token}
Content-Type: application/json

{
  "locale": "ru",
  "title": "Веб-разработка (обновлено)",
  "slug": "web-development-ru-updated",
  "description": "Обновленное описание"
}
```

**Важно:** Все поля опциональные, кроме `locale`. Обновляются только переданные поля.

**Успешный ответ (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "service_id": "1a719413-699e-458e-9e8f-e53d45c7b248",
  "locale": "ru",
  "title": "Веб-разработка (обновлено)",
  "slug": "web-development-ru-updated",
  "short_description": "Профессиональная разработка веб-приложений",
  "description": "Обновленное описание",
  "meta_title": "Веб-разработка | Наша компания",
  "meta_description": "SEO описание для поисковых систем",
  "created_at": "2026-01-17T10:00:00Z",
  "updated_at": "2026-01-17T10:05:00Z"
}
```

### 3. Удаление локали

**DELETE** `/api/v1/admin/{resource}/{resource_id}/locales/{locale_id}`

**Пример:**
```http
DELETE /api/v1/admin/services/1a719413-699e-458e-9e8f-e53d45c7b248/locales/550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer {token}
```

**Успешный ответ (204 No Content):** Тело ответа пустое.

## Схемы данных

### ServiceLocaleCreate / ServiceLocaleUpdate

```typescript
interface ServiceLocaleCreate {
  locale: string;              // Обязательно, 2-5 символов (ru, en, etc)
  title: string;               // Обязательно, 1-255 символов
  slug: string;                // Обязательно, 2-255 символов, уникален в пределах locale
  short_description?: string;  // Опционально, до 500 символов
  description?: string;        // Опционально
  meta_title?: string;         // Опционально, до 70 символов
  meta_description?: string;   // Опционально, до 160 символов
}

interface ServiceLocaleUpdate {
  locale: string;              // Обязательно
  title?: string;             // Опционально
  slug?: string;              // Опционально
  short_description?: string; // Опционально
  description?: string;       // Опционально
  meta_title?: string;        // Опционально
  meta_description?: string;   // Опционально
}
```

### ArticleLocaleCreate / ArticleLocaleUpdate

```typescript
interface ArticleLocaleCreate {
  locale: string;
  title: string;
  slug: string;
  excerpt?: string;           // До 500 символов
  content?: string;
  meta_title?: string;
  meta_description?: string;
}

interface ArticleLocaleUpdate {
  locale: string;
  title?: string;
  slug?: string;
  excerpt?: string;
  content?: string;
  meta_title?: string;
  meta_description?: string;
}
```

### EmployeeLocaleCreate / EmployeeLocaleUpdate

```typescript
interface EmployeeLocaleCreate {
  locale: string;
  first_name: string;
  last_name: string;
  slug: string;
  position: string;
  bio?: string;
  meta_title?: string;
  meta_description?: string;
}
```

### CaseLocaleCreate / CaseLocaleUpdate

```typescript
interface CaseLocaleCreate {
  locale: string;
  title: string;
  slug: string;
  excerpt?: string;
  description?: string;
  results?: string;
  meta_title?: string;
  meta_description?: string;
}
```

### FAQLocaleCreate / FAQLocaleUpdate

```typescript
interface FAQLocaleCreate {
  locale: string;
  question: string;           // 5-500 символов
  answer: string;             // Минимум 1 символ
}

interface FAQLocaleUpdate {
  locale: string;
  question?: string;
  answer?: string;
}
```

### TopicLocaleCreate / TopicLocaleUpdate

```typescript
interface TopicLocaleCreate {
  locale: string;
  title: string;
  slug: string;
  description?: string;
  meta_title?: string;
  meta_description?: string;
}
```

## Обработка ошибок

### 1. Локаль уже существует (409 Conflict)

**Когда:** Попытка создать локаль с языком, который уже есть у сущности.

**Ответ:**
```json
{
  "type": "https://api.cms.local/errors/locale_already_exists",
  "title": "Locale Already Exists",
  "status": 409,
  "detail": "Service already has a locale for language 'ru'",
  "resource": "Service",
  "locale": "ru"
}
```

**Обработка на фронтенде:**
```typescript
if (error.status === 409 && error.error_code === 'locale_already_exists') {
  // Показать сообщение: "Локаль для языка 'ru' уже существует"
  // Предложить обновить существующую локаль вместо создания новой
}
```

### 2. Минимум локалей (400 Bad Request)

**Когда:** Попытка удалить последнюю локаль у сущности.

**Ответ:**
```json
{
  "type": "https://api.cms.local/errors/minimum_locales_required",
  "title": "Minimum Locales Required",
  "status": 400,
  "detail": "Cannot delete the last locale. Service must have at least one locale.",
  "resource": "Service"
}
```

**Обработка на фронтенде:**
```typescript
if (error.status === 400 && error.error_code === 'minimum_locales_required') {
  // Показать сообщение: "Нельзя удалить последнюю локаль. Должна остаться хотя бы одна."
  // Скрыть/заблокировать кнопку удаления для последней локали
}
```

### 3. Slug уже существует (409 Conflict)

**Когда:** Попытка создать/обновить локаль с slug, который уже используется в этом языке.

**Ответ:**
```json
{
  "type": "https://api.cms.local/errors/already_exists",
  "title": "Already Exists",
  "status": 409,
  "detail": "Slug 'web-development' already exists for locale 'ru'",
  "resource": "Content",
  "field": "slug",
  "value": "web-development",
  "slug": "web-development",
  "locale": "ru"
}
```

**Обработка на фронтенде:**
```typescript
if (error.status === 409 && error.field === 'slug') {
  // Показать ошибку валидации под полем slug
  // Предложить другой slug
}
```

### 4. Локаль не найдена (404 Not Found)

**Когда:** Попытка обновить/удалить несуществующую локаль.

**Ответ:**
```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "ServiceLocale with id '550e8400-e29b-41d4-a716-446655440000' not found",
  "resource": "ServiceLocale"
}
```

**Обработка на фронтенде:**
```typescript
if (error.status === 404) {
  // Обновить список локалей (возможно, локаль была удалена другим пользователем)
  // Показать сообщение: "Локаль не найдена"
}
```

### 5. Сущность не найдена (404 Not Found)

**Когда:** Попытка создать локаль для несуществующей сущности.

**Ответ:**
```json
{
  "type": "https://api.cms.local/errors/not_found",
  "title": "Not Found",
  "status": 404,
  "detail": "Service with id '1a719413-699e-458e-9e8f-e53d45c7b248' not found",
  "resource": "Service"
}
```

### 6. Недостаточно прав (403 Forbidden)

**Когда:** У пользователя нет permission `{resource}:update`.

**Ответ:**
```json
{
  "type": "https://api.cms.local/errors/permission_denied",
  "title": "Permission Denied",
  "status": 403,
  "detail": "Permission denied",
  "required_permission": "services:update"
}
```

### 7. Валидация данных (422 Unprocessable Entity)

**Когда:** Невалидные данные в запросе (например, слишком короткий slug).

**Ответ:**
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "slug"],
      "msg": "String should have at least 2 characters",
      "input": "a"
    }
  ]
}
```

## TypeScript типы для фронтенда

```typescript
// Базовые типы
interface Locale {
  id: string;
  locale: string;
  created_at: string;
  updated_at: string;
}

interface ServiceLocale extends Locale {
  service_id: string;
  title: string;
  slug: string;
  short_description?: string;
  description?: string;
  meta_title?: string;
  meta_description?: string;
}

interface ArticleLocale extends Locale {
  article_id: string;
  title: string;
  slug: string;
  excerpt?: string;
  content?: string;
  meta_title?: string;
  meta_description?: string;
}

interface EmployeeLocale extends Locale {
  employee_id: string;
  first_name: string;
  last_name: string;
  slug: string;
  position: string;
  bio?: string;
  meta_title?: string;
  meta_description?: string;
}

interface CaseLocale extends Locale {
  case_id: string;
  title: string;
  slug: string;
  excerpt?: string;
  description?: string;
  results?: string;
  meta_title?: string;
  meta_description?: string;
}

interface FAQLocale extends Locale {
  faq_id: string;
  question: string;
  answer: string;
}

interface TopicLocale extends Locale {
  topic_id: string;
  title: string;
  slug: string;
  description?: string;
  meta_title?: string;
  meta_description?: string;
}

// Типы для создания/обновления
type LocaleCreate<T> = Omit<T, 'id' | 'created_at' | 'updated_at' | `${string}_id`>;
type LocaleUpdate<T> = Partial<LocaleCreate<T>> & { locale: string };

// Типы ошибок
interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  error_code?: string;
  resource?: string;
  locale?: string;
  field?: string;
  value?: string;
}

interface LocaleAlreadyExistsError extends ApiError {
  error_code: 'locale_already_exists';
  resource: string;
  locale: string;
}

interface MinimumLocalesError extends ApiError {
  error_code: 'minimum_locales_required';
  resource: string;
}

interface SlugExistsError extends ApiError {
  error_code: 'already_exists';
  field: 'slug';
  value: string;
  locale: string;
}
```

## Рекомендации по реализации на фронтенде

### 1. UI для управления локалями

```typescript
// Пример компонента для управления локалями
interface LocaleManagerProps {
  resourceType: 'service' | 'article' | 'case' | 'faq' | 'topic';
  resourceId: string;
  existingLocales: Locale[];
  availableLocales: string[]; // ['ru', 'en', 'de']
}

// Логика:
// 1. Показать список существующих локалей
// 2. Показать кнопку "Добавить локаль" для доступных языков
// 3. Для каждой локали:
//    - Кнопка "Редактировать"
//    - Кнопка "Удалить" (заблокирована, если это последняя локаль)
// 4. Модальное окно для создания/редактирования локали
```

### 2. Валидация перед отправкой

```typescript
// Проверка перед созданием локали
const validateBeforeCreate = (locale: string, existingLocales: Locale[]) => {
  // Проверить, что локаль еще не существует
  if (existingLocales.some(l => l.locale === locale)) {
    throw new Error(`Локаль для языка '${locale}' уже существует`);
  }
};

// Проверка перед удалением
const validateBeforeDelete = (localeId: string, existingLocales: Locale[]) => {
  if (existingLocales.length <= 1) {
    throw new Error('Нельзя удалить последнюю локаль');
  }
};
```

### 3. Обработка ошибок

```typescript
async function createLocale(resourceType: string, resourceId: string, data: LocaleCreate) {
  try {
    const response = await fetch(
      `/api/v1/admin/${resourceType}s/${resourceId}/locales`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      
      if (error.error_code === 'locale_already_exists') {
        // Показать сообщение и предложить обновить
        showError(`Локаль для языка '${error.locale}' уже существует`);
        return;
      }
      
      if (error.error_code === 'already_exists' && error.field === 'slug') {
        // Показать ошибку валидации под полем slug
        setFieldError('slug', `Slug '${error.value}' уже используется`);
        return;
      }
      
      throw new Error(error.detail || 'Ошибка при создании локали');
    }

    return await response.json();
  } catch (error) {
    console.error('Error creating locale:', error);
    throw error;
  }
}
```

### 4. Обновление списка локалей

```typescript
// После успешного создания/обновления/удаления
async function refreshLocales(resourceType: string, resourceId: string) {
  // Получить обновленную сущность с локалями
  const response = await fetch(
    `/api/v1/admin/${resourceType}s/${resourceId}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );
  
  const resource = await response.json();
  setLocales(resource.locales);
}
```

### 5. Полный пример React компонента

```typescript
import React, { useState, useEffect } from 'react';

interface LocaleManagerProps {
  resourceType: 'service' | 'article' | 'case' | 'faq' | 'topic';
  resourceId: string;
  availableLocales: string[]; // ['ru', 'en', 'de']
}

export const LocaleManager: React.FC<LocaleManagerProps> = ({
  resourceType,
  resourceId,
  availableLocales,
}) => {
  const [locales, setLocales] = useState<Locale[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingLocale, setEditingLocale] = useState<Locale | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Загрузить локали
  useEffect(() => {
    loadLocales();
  }, [resourceId]);

  const loadLocales = async () => {
    try {
      const response = await fetch(
        `/api/v1/admin/${resourceType}s/${resourceId}`,
        {
          headers: {
            'Authorization': `Bearer ${getToken()}`,
          },
        }
      );
      const resource = await response.json();
      setLocales(resource.locales);
    } catch (err) {
      setError('Ошибка загрузки локалей');
    }
  };

  const handleCreate = async (data: LocaleCreate) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `/api/v1/admin/${resourceType}s/${resourceId}/locales`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        handleError(error);
        return;
      }

      await loadLocales();
      setShowCreateModal(false);
    } catch (err) {
      setError('Ошибка создания локали');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (localeId: string, data: LocaleUpdate) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `/api/v1/admin/${resourceType}s/${resourceId}/locales/${localeId}`,
        {
          method: 'PATCH',
          headers: {
            'Authorization': `Bearer ${getToken()}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        handleError(error);
        return;
      }

      await loadLocales();
      setEditingLocale(null);
    } catch (err) {
      setError('Ошибка обновления локали');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (localeId: string) => {
    if (locales.length <= 1) {
      alert('Нельзя удалить последнюю локаль');
      return;
    }

    if (!confirm('Вы уверены, что хотите удалить эту локаль?')) {
      return;
    }

    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `/api/v1/admin/${resourceType}s/${resourceId}/locales/${localeId}`,
        {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${getToken()}`,
          },
        }
      );

      if (!response.ok) {
        const error = await response.json();
        handleError(error);
        return;
      }

      await loadLocales();
    } catch (err) {
      setError('Ошибка удаления локали');
    } finally {
      setLoading(false);
    }
  };

  const handleError = (error: ApiError) => {
    if (error.error_code === 'locale_already_exists') {
      setError(`Локаль для языка '${error.locale}' уже существует`);
    } else if (error.error_code === 'minimum_locales_required') {
      setError('Нельзя удалить последнюю локаль');
    } else if (error.error_code === 'already_exists' && error.field === 'slug') {
      setError(`Slug '${error.value}' уже используется для языка '${error.locale}'`);
    } else {
      setError(error.detail || 'Произошла ошибка');
    }
  };

  const canAddLocales = availableLocales.filter(
    loc => !locales.some(l => l.locale === loc)
  );

  return (
    <div className="locale-manager">
      <h3>Управление локалями</h3>
      
      {error && <div className="error">{error}</div>}
      
      <div className="locales-list">
        {locales.map(locale => (
          <div key={locale.id} className="locale-item">
            <div>
              <strong>{locale.locale.toUpperCase()}</strong>
              {resourceType === 'service' && (
                <span> - {(locale as ServiceLocale).title}</span>
              )}
            </div>
            <div className="actions">
              <button onClick={() => setEditingLocale(locale)}>
                Редактировать
              </button>
              <button
                onClick={() => handleDelete(locale.id)}
                disabled={locales.length <= 1}
                title={locales.length <= 1 ? 'Нельзя удалить последнюю локаль' : ''}
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>

      {canAddLocales.length > 0 && (
        <button onClick={() => setShowCreateModal(true)}>
          Добавить локаль ({canAddLocales.join(', ')})
        </button>
      )}

      {showCreateModal && (
        <LocaleForm
          availableLocales={canAddLocales}
          onSubmit={handleCreate}
          onCancel={() => setShowCreateModal(false)}
        />
      )}

      {editingLocale && (
        <LocaleForm
          locale={editingLocale}
          onSubmit={(data) => handleUpdate(editingLocale.id, data)}
          onCancel={() => setEditingLocale(null)}
        />
      )}
    </div>
  );
};
```

```typescript
// После успешного создания/обновления/удаления
async function refreshLocales(resourceType: string, resourceId: string) {
  // Получить обновленную сущность с локалями
  const response = await fetch(
    `/api/v1/admin/${resourceType}s/${resourceId}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    }
  );
  
  const resource = await response.json();
  setLocales(resource.locales);
}
```

## Примеры использования

### Добавление локали к услуге

```typescript
// 1. Получить список существующих локалей
const service = await getService(serviceId);
const existingLocales = service.locales.map(l => l.locale); // ['en']

// 2. Определить доступные языки для добавления
const availableLocales = ['ru', 'en', 'de'];
const canAdd = availableLocales.filter(l => !existingLocales.includes(l)); // ['ru', 'de']

// 3. Создать новую локаль
const newLocale = await createLocale('service', serviceId, {
  locale: 'ru',
  title: 'Веб-разработка',
  slug: 'web-development-ru',
  short_description: 'Описание на русском',
  description: 'Полное описание...',
  meta_title: 'Веб-разработка | Компания',
  meta_description: 'SEO описание',
});

// 4. Обновить список локалей
await refreshLocales('service', serviceId);
```

### Редактирование локали

```typescript
// Обновить только title и slug
const updated = await updateLocale('service', serviceId, localeId, {
  locale: 'ru', // Обязательно указать
  title: 'Новое название',
  slug: 'new-slug',
  // Остальные поля не изменятся
});
```

### Удаление локали

```typescript
// Проверить, что это не последняя локаль
if (locales.length <= 1) {
  alert('Нельзя удалить последнюю локаль');
  return;
}

// Удалить
await deleteLocale('service', serviceId, localeId);

// Обновить список
await refreshLocales('service', serviceId);
```

## Важные замечания

1. **Минимум одна локаль:** Каждая сущность должна иметь хотя бы одну локаль. Нельзя удалить последнюю.

2. **Уникальность slug:** Slug должен быть уникальным в пределах одного языка (locale) и tenant.

3. **Обязательное поле locale:** В запросах на создание и обновление поле `locale` всегда обязательно.

4. **Частичное обновление:** При обновлении (PATCH) обновляются только переданные поля. Остальные остаются без изменений.

5. **Права доступа:** Все endpoints требуют permission `{resource}:update`:
   - `services:update` для услуг
   - `articles:update` для статей
   - `cases:update` для кейсов
   - `faq:update` для FAQ
   - `articles:update` для тем (topics)
   - `employees:update` для сотрудников
   - `settings:update` для адресов

6. **Транзакционность:** Все операции выполняются в транзакциях, поэтому либо все изменения применяются, либо ничего.

## Результаты тестирования

✅ **Протестировано:**
- Создание новой локали - работает корректно
- Проверка на дубликат локали - возвращает правильную ошибку `LocaleAlreadyExistsError`
- Обновление локали - работает корректно
- Проверка минимума локалей - возвращает правильную ошибку `MinimumLocalesError`
- Валидация slug - проверяется уникальность в пределах locale

## Тестирование

Для тестирования можно использовать следующие curl команды:

```bash
# Создать локаль
curl -X POST "http://localhost:8000/api/v1/admin/services/{service_id}/locales" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "locale": "ru",
    "title": "Тестовая услуга",
    "slug": "test-service-ru"
  }'

# Обновить локаль
curl -X PATCH "http://localhost:8000/api/v1/admin/services/{service_id}/locales/{locale_id}" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "locale": "ru",
    "title": "Обновленное название"
  }'

# Удалить локаль
curl -X DELETE "http://localhost:8000/api/v1/admin/services/{service_id}/locales/{locale_id}" \
  -H "Authorization: Bearer {token}"
```

