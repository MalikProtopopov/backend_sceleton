# Audit Log, Export, Search & Company Info API

Документация по API для аудит-лога, экспорта данных, поиска и расширенного управления компанией.

## Содержание

1. [Audit Log API](#audit-log-api)
2. [Export API](#export-api)
3. [Search Functionality](#search-functionality)
4. [Role Management CRUD](#role-management-crud)
5. [Company Info CRUD](#company-info-crud)

---

## Audit Log API

Аудит-лог предоставляет неизменяемую историю всех действий в системе для отслеживания изменений и compliance.

### Модель данных

```typescript
interface AuditLog {
  id: string;                     // UUID
  timestamp: string;              // ISO datetime
  action: string;                 // create, update, delete, publish, etc.
  resource_type: string;          // article, case, employee, etc.
  resource_id: string | null;     // UUID ресурса
  resource_name: string | null;   // Название для отображения
  user: AuditUser | null;
  changes: Record<string, any> | null;  // Что изменилось
  ip_address: string | null;
  status: string;                 // success, error
}

interface AuditUser {
  id: string | null;
  email: string | null;
  name: string | null;
}
```

### GET /api/v1/admin/audit-logs

Получение списка записей аудит-лога с фильтрацией.

**Требуемые права:** `audit:read`

| Параметр | Тип | Описание |
|----------|-----|----------|
| page | integer | Номер страницы (default: 1) |
| page_size | integer | Размер страницы (default: 25) |
| userId | string | Фильтр по ID пользователя |
| resourceType | string | Фильтр по типу ресурса |
| resourceId | string | Фильтр по ID ресурса |
| action | string | Фильтр по действию |
| dateFrom | string | Начало периода (YYYY-MM-DD) |
| dateTo | string | Конец периода (YYYY-MM-DD) |

**Пример запроса:**
```bash
curl -X GET "https://api.example.com/api/v1/admin/audit-logs?resourceType=article&dateFrom=2024-01-01&dateTo=2024-01-31" \
  -H "Authorization: Bearer <token>"
```

**Пример ответа:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "timestamp": "2024-01-15T10:30:00Z",
      "action": "update",
      "resource_type": "article",
      "resource_id": "123e4567-e89b-12d3-a456-426614174000",
      "resource_name": "Статья о маркетинге",
      "user": {
        "id": "789e0123-e89b-12d3-a456-426614174000",
        "email": "admin@example.com",
        "name": "Иван Петров"
      },
      "changes": {
        "status": { "old": "draft", "new": "published" }
      },
      "ip_address": "192.168.1.100",
      "status": "success"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 25
}
```

### Frontend интеграция

```typescript
interface AuditFilters {
  userId?: string;
  resourceType?: string;
  resourceId?: string;
  action?: string;
  dateFrom?: string;
  dateTo?: string;
}

async function fetchAuditLogs(
  page: number,
  pageSize: number,
  filters: AuditFilters
) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    ...filters,
  });
  
  const response = await api.get(`/admin/audit-logs?${params}`);
  return response.data;
}

// Компонент фильтрации
function AuditLogFilters({ onFilter }) {
  const [filters, setFilters] = useState<AuditFilters>({});
  
  // Типы ресурсов для выпадающего списка
  const resourceTypes = [
    { value: 'article', label: 'Статьи' },
    { value: 'case', label: 'Кейсы' },
    { value: 'employee', label: 'Сотрудники' },
    { value: 'inquiry', label: 'Заявки' },
    { value: 'seo_route', label: 'SEO' },
  ];
  
  // Действия для фильтрации
  const actions = [
    { value: 'create', label: 'Создание' },
    { value: 'update', label: 'Обновление' },
    { value: 'delete', label: 'Удаление' },
    { value: 'publish', label: 'Публикация' },
  ];
}
```

---

## Export API

Export API позволяет выгружать данные в CSV или JSON формате.

### GET /api/v1/admin/export

Экспорт данных в файл.

**Требуемые права:** `export:read`

| Параметр | Тип | Описание |
|----------|-----|----------|
| resourceType | string | Тип данных: inquiries, team, seo_routes, audit_logs |
| format | string | Формат: csv (default), json |
| status | string | Фильтр по статусу (для inquiries) |
| dateFrom | string | Начало периода (ISO datetime) |
| dateTo | string | Конец периода (ISO datetime) |
| columns | string | Список колонок через запятую |

### Поддерживаемые типы ресурсов

#### inquiries (Заявки)

Колонки по умолчанию: `name, email, phone, company, status, utm_source, created_at`

Все доступные колонки:
- name, email, phone, company, message
- status, utm_source, utm_medium, utm_campaign
- device_type, source_url, created_at

#### team (Сотрудники)

Колонки по умолчанию: `name, position, email, phone, is_published`

Все доступные колонки:
- name, position, email, phone
- is_published, linkedin_url, telegram_url

#### seo_routes (SEO маршруты)

Колонки по умолчанию: `path, locale, meta_title, meta_description, created_at`

Все доступные колонки:
- path, locale, meta_title, meta_description
- canonical_url, robots_index, robots_follow, created_at

#### audit_logs (Аудит-лог)

Колонки по умолчанию: `timestamp, user_email, action, resource_type, resource_name`

Все доступные колонки:
- timestamp, user_email, user_name
- action, resource_type, resource_id, resource_name
- ip_address, status

**Пример запроса:**
```bash
# Экспорт заявок за январь в CSV
curl -X GET "https://api.example.com/api/v1/admin/export?resourceType=inquiries&format=csv&dateFrom=2024-01-01&dateTo=2024-01-31" \
  -H "Authorization: Bearer <token>" \
  -o inquiries_january.csv

# Экспорт команды в JSON с выбранными колонками
curl -X GET "https://api.example.com/api/v1/admin/export?resourceType=team&format=json&columns=name,position,email" \
  -H "Authorization: Bearer <token>"
```

### Frontend интеграция

```typescript
async function downloadExport(
  resourceType: 'inquiries' | 'team' | 'seo_routes' | 'audit_logs',
  format: 'csv' | 'json' = 'csv',
  filters?: Record<string, string>
) {
  const params = new URLSearchParams({
    resourceType,
    format,
    ...filters,
  });
  
  const response = await api.get(`/admin/export?${params}`, {
    responseType: 'blob',
  });
  
  // Получить имя файла из заголовка
  const contentDisposition = response.headers['content-disposition'];
  const filename = contentDisposition?.match(/filename="(.+)"/)?.[1] 
    || `export_${resourceType}.${format}`;
  
  // Скачать файл
  const blob = new Blob([response.data]);
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}

// Пример кнопки экспорта
function ExportButton({ resourceType }) {
  const [isExporting, setIsExporting] = useState(false);
  
  const handleExport = async () => {
    setIsExporting(true);
    try {
      await downloadExport(resourceType, 'csv');
      toast.success('Файл скачан');
    } catch (error) {
      toast.error('Ошибка при экспорте');
    } finally {
      setIsExporting(false);
    }
  };
  
  return (
    <Button onClick={handleExport} disabled={isExporting}>
      {isExporting ? 'Экспорт...' : 'Экспорт CSV'}
    </Button>
  );
}
```

---

## Search Functionality

В список эндпоинтов добавлен параметр `search` для полнотекстового поиска.

### Модифицированные эндпоинты

| Эндпоинт | Поля поиска |
|----------|-------------|
| GET /api/v1/admin/articles | title, content, slug (в locales) |
| GET /api/v1/admin/cases | title (в locales), client_name |
| GET /api/v1/admin/employees | name, position (в locales), email |
| GET /api/v1/admin/inquiries | name, email, company, phone |
| GET /api/v1/auth/users | email, full_name |

**Пример запроса:**
```bash
curl -X GET "https://api.example.com/api/v1/admin/articles?search=маркетинг&status=published" \
  -H "Authorization: Bearer <token>"
```

### Frontend интеграция

```typescript
// Хук для debounced поиска
function useSearchDebounce(delay = 300) {
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedTerm, setDebouncedTerm] = useState('');
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedTerm(searchTerm);
    }, delay);
    
    return () => clearTimeout(timer);
  }, [searchTerm, delay]);
  
  return { searchTerm, debouncedTerm, setSearchTerm };
}

// Использование в списке статей
function ArticlesList() {
  const { searchTerm, debouncedTerm, setSearchTerm } = useSearchDebounce();
  const [filters, setFilters] = useState({ status: null });
  
  const { data, isLoading } = useQuery({
    queryKey: ['articles', debouncedTerm, filters],
    queryFn: () => fetchArticles({
      search: debouncedTerm || undefined,
      ...filters,
    }),
  });
  
  return (
    <div>
      <Input
        placeholder="Поиск статей..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
      />
      {/* Остальной UI */}
    </div>
  );
}
```

### Рекомендации

1. **Debouncing** — используйте задержку 300-500ms перед отправкой запроса
2. **Минимальная длина** — рекомендуется искать от 2+ символов
3. **Очистка** — предоставьте кнопку очистки поиска
4. **Комбинирование** — поиск работает вместе с другими фильтрами

---

## Role Management CRUD

API для управления пользовательскими ролями и разрешениями.

### Существующие эндпоинты (только чтение)

- **GET /api/v1/auth/roles** — список ролей
- **GET /api/v1/auth/permissions** — список всех разрешений

### Новые эндпоинты

#### POST /api/v1/auth/roles

Создание новой роли.

**Требуемые права:** `users:manage`

**Тело запроса:**
```json
{
  "name": "content_editor",
  "description": "Редактор контента без прав на публикацию",
  "permission_ids": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ]
}
```

**Валидация:**
- `name` — 2-50 символов, уникальное в рамках tenant
- `permission_ids` — массив UUID существующих разрешений

#### PATCH /api/v1/auth/roles/{role_id}

Обновление роли.

**Тело запроса:**
```json
{
  "name": "content_editor_v2",
  "description": "Обновленное описание",
  "permission_ids": ["..."]
}
```

**Ограничения:**
- Системные роли (`is_system: true`) нельзя изменять

#### DELETE /api/v1/auth/roles/{role_id}

Удаление роли.

**Ограничения:**
- Системные роли нельзя удалять
- Роли, назначенные пользователям, нельзя удалять

### Предустановленные роли

| Роль | Код | Описание |
|------|-----|----------|
| Администратор | admin | Полный доступ ко всем функциям |
| Контент-менеджер | content_manager | Управление статьями, FAQ, услугами |
| Маркетолог | marketer | Кейсы, отзывы, SEO, просмотр заявок |

### Frontend интеграция

```typescript
interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  permissions: Permission[];
}

interface Permission {
  id: string;
  code: string;
  name: string;
  resource: string;
  action: string;
}

// Форма создания/редактирования роли
function RoleForm({ role, onSave }) {
  const { data: allPermissions } = useQuery({
    queryKey: ['permissions'],
    queryFn: () => api.get('/auth/permissions'),
  });
  
  // Группировка разрешений по ресурсу
  const groupedPermissions = useMemo(() => {
    if (!allPermissions) return {};
    return allPermissions.items.reduce((acc, perm) => {
      if (!acc[perm.resource]) acc[perm.resource] = [];
      acc[perm.resource].push(perm);
      return acc;
    }, {});
  }, [allPermissions]);
  
  // UI с чекбоксами для каждого ресурса
}
```

---

## Company Info CRUD

Расширенное управление данными компании: практики, преимущества, адреса, контакты.

### Practice Areas (Направления практики)

#### GET /api/v1/admin/practice-areas

Список всех направлений практики.

**Пример ответа:**
```json
{
  "items": [
    {
      "id": "...",
      "icon": "briefcase",
      "is_published": true,
      "sort_order": 0,
      "version": 1,
      "locales": [
        {
          "locale": "ru",
          "title": "Корпоративное право",
          "slug": "korporativnoe-pravo",
          "description": "Полный спектр услуг..."
        }
      ]
    }
  ],
  "total": 5
}
```

#### POST /api/v1/admin/practice-areas

Создание направления практики.

#### GET /api/v1/admin/practice-areas/{id}

Получение по ID.

#### PATCH /api/v1/admin/practice-areas/{id}

Обновление (требует `version`).

#### DELETE /api/v1/admin/practice-areas/{id}

Мягкое удаление.

### Advantages (Преимущества)

#### GET /api/v1/admin/advantages

Список преимуществ.

#### POST /api/v1/admin/advantages

Создание преимущества.

#### GET /api/v1/admin/advantages/{id}

Получение по ID.

#### PATCH /api/v1/admin/advantages/{id}

Обновление (требует `version`).

#### DELETE /api/v1/admin/advantages/{id}

Мягкое удаление.

### Addresses (Адреса офисов)

#### GET /api/v1/admin/addresses

Список всех адресов.

**Пример ответа:**
```json
{
  "items": [
    {
      "id": "...",
      "address_type": "office",
      "latitude": 55.7558,
      "longitude": 37.6173,
      "working_hours": "Пн-Пт: 9:00-18:00",
      "phone": "+7 495 123-45-67",
      "email": "office@example.com",
      "is_primary": true,
      "sort_order": 0,
      "locales": [
        {
          "locale": "ru",
          "name": "Головной офис",
          "country": "Россия",
          "city": "Москва",
          "street": "Тверская",
          "building": "1",
          "postal_code": "125009",
          "full_address": "Россия, Москва, Тверская, 1"
        }
      ]
    }
  ],
  "total": 2
}
```

#### POST /api/v1/admin/addresses

Создание адреса.

#### GET /api/v1/admin/addresses/{id}

Получение по ID.

#### PATCH /api/v1/admin/addresses/{id}

Обновление адреса.

#### DELETE /api/v1/admin/addresses/{id}

Мягкое удаление.

### Contacts (Контакты)

#### GET /api/v1/admin/contacts

Список всех контактов.

**Пример ответа:**
```json
{
  "items": [
    {
      "id": "...",
      "contact_type": "phone",
      "value": "+7 495 123-45-67",
      "label": "Основной",
      "icon": "phone",
      "is_primary": true,
      "sort_order": 0
    },
    {
      "id": "...",
      "contact_type": "email",
      "value": "info@example.com",
      "label": "Общие вопросы",
      "icon": "mail",
      "is_primary": false,
      "sort_order": 1
    }
  ],
  "total": 5
}
```

#### POST /api/v1/admin/contacts

Создание контакта.

**Тело запроса:**
```json
{
  "contact_type": "social",
  "value": "https://t.me/company",
  "label": "Telegram",
  "icon": "telegram",
  "is_primary": false,
  "sort_order": 10
}
```

#### GET /api/v1/admin/contacts/{id}

Получение по ID.

#### PATCH /api/v1/admin/contacts/{id}

Обновление контакта.

#### DELETE /api/v1/admin/contacts/{id}

Мягкое удаление.

### Типы контактов

| Тип | Описание |
|-----|----------|
| phone | Телефон |
| email | Email |
| social | Социальная сеть |
| messenger | Мессенджер |

---

## Коды ошибок

| Код | Описание |
|-----|----------|
| 400 | Неверный формат запроса |
| 401 | Требуется авторизация |
| 403 | Недостаточно прав |
| 404 | Ресурс не найден |
| 409 | Конфликт версий (optimistic locking) |
| 422 | Ошибка валидации |
| 429 | Превышен лимит запросов |

### Формат ошибки (RFC 7807)

```json
{
  "type": "https://api.example.com/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Поле 'name' обязательно для заполнения",
  "instance": "/api/v1/admin/roles",
  "errors": [
    {
      "field": "name",
      "message": "Field required"
    }
  ]
}
```

