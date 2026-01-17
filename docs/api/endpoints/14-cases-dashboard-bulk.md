# Cases, Dashboard & Bulk Operations API

Документация по API для работы с кейсами (портфолио), дашбордом и массовыми операциями.

## Содержание

1. [Cases API](#cases-api)
2. [Dashboard API](#dashboard-api)
3. [Bulk Operations API](#bulk-operations-api)

---

## Cases API

Cases (кейсы/портфолио) — это записи о выполненных проектах компании. Поддерживают мультиязычность, связь с услугами, статусы публикации.

### Модель данных

```typescript
interface Case {
  id: string;                    // UUID
  tenant_id: string;             // UUID
  status: 'draft' | 'published' | 'archived';
  cover_image_url: string | null;
  client_name: string | null;    // Название клиента
  project_year: number | null;   // Год проекта
  project_duration: string | null; // Длительность (например "3 месяца")
  is_featured: boolean;          // Выделенный кейс
  sort_order: number;
  version: number;               // Для optimistic locking
  published_at: string | null;   // ISO datetime
  created_at: string;
  updated_at: string;
  locales: CaseLocale[];
  services: CaseServiceLink[];
}

interface CaseLocale {
  id: string;
  case_id: string;
  locale: string;                // "en", "ru", "uk"
  title: string;
  slug: string;
  excerpt: string | null;
  description: string | null;
  results: string | null;        // Результаты проекта
  meta_title: string | null;
  meta_description: string | null;
}

interface CaseServiceLink {
  service_id: string;            // UUID связанной услуги
}
```

### State Machine

```
                    publish
        ┌─────────────────────────────────┐
        │                                 ▼
    ┌───────┐                        ┌───────────┐
    │ DRAFT │◄───────────────────────│ PUBLISHED │
    └───────┘      unpublish         └───────────┘
        │                                 │
        │              archive            │
        └────────────────┬────────────────┘
                         ▼
                    ┌──────────┐
                    │ ARCHIVED │
                    └──────────┘
```

### Admin Endpoints

#### GET /api/v1/admin/cases

Список кейсов с фильтрацией и пагинацией.

| Параметр | Тип | Описание |
|----------|-----|----------|
| page | integer | Номер страницы (default: 1) |
| page_size | integer | Размер страницы (default: 20, max: 100) |
| status | string | Фильтр по статусу: draft, published, archived |
| featured | boolean | Фильтр по выделенным |
| search | string | Поиск по названию и клиенту |

**Пример запроса:**
```bash
curl -X GET "https://api.example.com/api/v1/admin/cases?status=published&featured=true" \
  -H "Authorization: Bearer <token>"
```

**Пример ответа:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "published",
      "cover_image_url": "https://cdn.example.com/cases/cover.jpg",
      "client_name": "Acme Corp",
      "project_year": 2024,
      "project_duration": "3 месяца",
      "is_featured": true,
      "sort_order": 0,
      "version": 1,
      "published_at": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-10T08:00:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "locales": [
        {
          "locale": "ru",
          "title": "Редизайн корпоративного сайта",
          "slug": "redesign-korporativnogo-sajta",
          "excerpt": "Полный редизайн сайта для Acme Corp"
        }
      ],
      "services": [
        { "service_id": "123e4567-e89b-12d3-a456-426614174000" }
      ]
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

#### POST /api/v1/admin/cases

Создание нового кейса.

**Тело запроса:**
```json
{
  "status": "draft",
  "cover_image_url": "https://cdn.example.com/cases/new-cover.jpg",
  "client_name": "New Client",
  "project_year": 2024,
  "project_duration": "2 месяца",
  "is_featured": false,
  "sort_order": 0,
  "locales": [
    {
      "locale": "ru",
      "title": "Новый проект",
      "slug": "novyj-proekt",
      "excerpt": "Краткое описание",
      "description": "Полное описание проекта...",
      "results": "Достигнутые результаты...",
      "meta_title": "Новый проект | Компания",
      "meta_description": "SEO описание кейса"
    }
  ],
  "service_ids": ["123e4567-e89b-12d3-a456-426614174000"]
}
```

**Требования к полям:**
- `locales` — минимум 1 локаль
- `locales[].locale` — 2-5 символов
- `locales[].title` — 1-255 символов
- `locales[].slug` — 2-255 символов, уникальный для tenant+locale

#### GET /api/v1/admin/cases/{id}

Получение кейса по ID.

#### PATCH /api/v1/admin/cases/{id}

Обновление кейса. Требует `version` для optimistic locking.

**Тело запроса:**
```json
{
  "client_name": "Updated Client Name",
  "is_featured": true,
  "service_ids": ["new-service-id"],
  "version": 1
}
```

**Ошибки:**
- `409 Conflict` — версия не совпадает (кейс был изменен другим пользователем)

#### POST /api/v1/admin/cases/{id}/publish

Публикация кейса. Устанавливает `status: published` и `published_at`.

#### POST /api/v1/admin/cases/{id}/unpublish

Снятие с публикации. Устанавливает `status: draft`.

#### DELETE /api/v1/admin/cases/{id}

Мягкое удаление кейса (soft delete).

### Public Endpoints

#### GET /api/v1/public/cases

Список опубликованных кейсов.

| Параметр | Тип | Описание |
|----------|-----|----------|
| locale | string | Язык контента (required, header или query) |
| tenant_id | string | ID тенанта (required) |
| page | integer | Номер страницы |
| page_size | integer | Размер страницы |
| featured | boolean | Только выделенные |

#### GET /api/v1/public/cases/{slug}

Получение кейса по slug.

---

## Dashboard API

Dashboard предоставляет агрегированную статистику для главной страницы админ-панели.

### GET /api/v1/admin/dashboard

Получение статистики для дашборда.

**Требуемые права:** `dashboard:read`

**Пример ответа:**
```json
{
  "summary": {
    "total_articles": 45,
    "total_cases": 12,
    "total_team_members": 8,
    "total_services": 15,
    "total_faqs": 30,
    "total_reviews": 25
  },
  "inquiries": {
    "total": 150,
    "pending": 12,
    "in_progress": 5,
    "done": 130,
    "this_month": 15
  },
  "content_by_status": {
    "articles": {
      "published": 30,
      "draft": 10,
      "archived": 5
    },
    "cases": {
      "published": 8,
      "draft": 3,
      "archived": 1
    }
  },
  "recent_activity": []
}
```

### Структура ответа

| Поле | Описание |
|------|----------|
| summary | Общее количество контента по типам |
| inquiries | Статистика заявок: всего, по статусам, за месяц |
| content_by_status | Разбивка контента по статусам публикации |
| recent_activity | Последние действия (требует audit log) |

### Frontend интеграция

```typescript
// Рекомендуемый интервал обновления: 5 минут
const DASHBOARD_REFRESH_INTERVAL = 5 * 60 * 1000;

async function fetchDashboard() {
  const response = await api.get('/admin/dashboard');
  return response.data;
}

// React Query пример
const { data: dashboard } = useQuery({
  queryKey: ['dashboard'],
  queryFn: fetchDashboard,
  staleTime: DASHBOARD_REFRESH_INTERVAL,
});
```

---

## Bulk Operations API

Массовые операции позволяют выполнять действия над несколькими записями одновременно.

### POST /api/v1/admin/bulk

Выполнение массовой операции.

**Требуемые права:** `content:bulk`

**Поддерживаемые типы ресурсов:**
- `articles` — статьи
- `cases` — кейсы
- `faq` — FAQ
- `reviews` — отзывы

**Поддерживаемые действия:**
| Действие | Описание | Применимо к |
|----------|----------|-------------|
| publish | Публикация | articles, cases, reviews (approve), faq |
| unpublish | Снятие с публикации | articles, cases, reviews (reject), faq |
| archive | Архивирование | articles, cases |
| delete | Мягкое удаление | все |

**Тело запроса:**
```json
{
  "resource_type": "articles",
  "action": "publish",
  "ids": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002",
    "550e8400-e29b-41d4-a716-446655440003"
  ]
}
```

**Ограничения:**
- Максимум 500 записей за один запрос
- При количестве < 100 — синхронное выполнение
- При количестве >= 100 — рекомендуется async (Celery)

**Пример ответа:**
```json
{
  "job_id": null,
  "status": "completed",
  "summary": {
    "total": 3,
    "succeeded": 2,
    "failed": 1,
    "details": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "status": "success",
        "message": "publish completed"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "status": "success",
        "message": "publish completed"
      },
      {
        "id": "550e8400-e29b-41d4-a716-446655440003",
        "status": "error",
        "message": "Article not found"
      }
    ]
  }
}
```

### Frontend интеграция

```typescript
interface BulkOperationRequest {
  resource_type: 'articles' | 'cases' | 'faq' | 'reviews';
  action: 'publish' | 'unpublish' | 'archive' | 'delete';
  ids: string[];
}

interface BulkOperationResponse {
  job_id: string | null;
  status: 'completed' | 'processing';
  summary: {
    total: number;
    succeeded: number;
    failed: number;
    details: Array<{
      id: string;
      status: 'success' | 'error';
      message: string | null;
    }>;
  };
}

async function executeBulkOperation(
  request: BulkOperationRequest
): Promise<BulkOperationResponse> {
  const response = await api.post('/admin/bulk', request);
  return response.data;
}

// Пример использования с выбранными элементами
async function publishSelected(selectedIds: string[]) {
  if (selectedIds.length === 0) return;
  
  try {
    const result = await executeBulkOperation({
      resource_type: 'articles',
      action: 'publish',
      ids: selectedIds,
    });
    
    if (result.summary.failed > 0) {
      // Показать частичный успех
      toast.warning(`Опубликовано ${result.summary.succeeded} из ${result.summary.total}`);
    } else {
      toast.success(`Опубликовано ${result.summary.succeeded} записей`);
    }
    
    // Обновить список
    queryClient.invalidateQueries(['articles']);
  } catch (error) {
    toast.error('Ошибка при выполнении операции');
  }
}
```

### Обработка ошибок

При частичном успехе:
1. Показать пользователю сводку (сколько успешно, сколько с ошибками)
2. Предоставить возможность просмотреть детали ошибок
3. Обновить UI для отображения актуального состояния

---

## Примечания для фронтенда

### Optimistic Locking (Cases)

При обновлении кейса всегда передавайте текущую версию:

```typescript
const updateCase = async (id: string, data: Partial<Case>, version: number) => {
  try {
    await api.patch(`/admin/cases/${id}`, { ...data, version });
  } catch (error) {
    if (error.response?.status === 409) {
      // Версия устарела — предложить перезагрузить данные
      const shouldReload = confirm('Данные были изменены другим пользователем. Перезагрузить?');
      if (shouldReload) {
        queryClient.invalidateQueries(['case', id]);
      }
    }
  }
};
```

### Связь кейсов с услугами

При создании/редактировании кейса можно привязать услуги:

```typescript
// Получить список услуг для селектора
const { data: services } = useQuery({
  queryKey: ['services'],
  queryFn: () => api.get('/admin/services'),
});

// При сохранении передать service_ids
await api.patch(`/admin/cases/${id}`, {
  service_ids: selectedServiceIds,
  version: currentVersion,
});
```

