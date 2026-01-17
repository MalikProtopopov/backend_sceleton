# Employees API

> Team members and staff management

---

## Overview

Employees represent team members displayed on the company's "About" or "Team" pages. Features include:
- Multi-language support via `locales`
- Publish/unpublish control
- Association with practice areas
- Photo and contact information
- Sort order for display sequence
- SEO metadata per locale

---

## Data Model

```json
{
  "id": "employee-uuid",
  "tenant_id": "tenant-uuid",
  "photo_url": "https://cdn.example.com/team/john.jpg",
  "email": "john@company.com",
  "phone": "+7 999 123-45-67",
  "is_published": true,
  "sort_order": 0,
  "version": 1,
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z",
  "locales": [
    {
      "id": "locale-uuid",
      "employee_id": "employee-uuid",
      "locale": "ru",
      "first_name": "Иван",
      "last_name": "Петров",
      "position": "Старший юрист",
      "slug": "ivan-petrov",
      "bio": "<p>Иван специализируется на...</p>",
      "meta_title": "Иван Петров - Старший юрист",
      "meta_description": "Профиль Ивана Петрова..."
    }
  ],
  "practice_areas": [
    { "practice_area_id": "pa-uuid-1" }
  ]
}
```

---

## Admin Endpoints

### GET /api/v1/admin/employees

List all employees with pagination and filters.

**Required Permission:** `employees:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page |
| `isPublished` | boolean | - | Filter by published status |

**Example Request:**
```bash
GET /api/v1/admin/employees?page=1&isPublished=true
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "employee-uuid",
      "tenant_id": "tenant-uuid",
      "photo_url": "https://cdn.example.com/team/john.jpg",
      "email": "john@company.com",
      "phone": "+7 999 123-45-67",
      "is_published": true,
      "sort_order": 0,
      "version": 1,
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z",
      "locales": [...],
      "practice_areas": [...]
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/v1/admin/employees

Create a new employee.

**Required Permission:** `employees:create`

**Request Body:**
```json
{
  "photo_url": "https://cdn.example.com/team/john.jpg",
  "email": "john@company.com",
  "phone": "+7 999 123-45-67",
  "is_published": false,
  "sort_order": 0,
  "practice_area_ids": ["pa-uuid-1", "pa-uuid-2"],
  "locales": [
    {
      "locale": "ru",
      "first_name": "Иван",
      "last_name": "Петров",
      "position": "Старший юрист",
      "slug": "ivan-petrov",
      "bio": "<p>Иван специализируется на корпоративном праве...</p>",
      "meta_title": "Иван Петров - Старший юрист | Компания",
      "meta_description": "Профиль Ивана Петрова - старшего юриста компании"
    },
    {
      "locale": "en",
      "first_name": "Ivan",
      "last_name": "Petrov",
      "position": "Senior Lawyer",
      "slug": "ivan-petrov",
      "bio": "<p>Ivan specializes in corporate law...</p>",
      "meta_title": "Ivan Petrov - Senior Lawyer | Company",
      "meta_description": "Profile of Ivan Petrov - senior lawyer"
    }
  ]
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `photo_url` | string | No | Max 500 chars |
| `email` | string | No | Valid email, max 255 chars |
| `phone` | string | No | Max 50 chars |
| `is_published` | boolean | No | Default: false |
| `sort_order` | integer | No | Default: 0 |
| `practice_area_ids` | UUID[] | No | Must exist |
| `locales` | array | Yes | At least 1 locale |

**Locale Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars |
| `first_name` | string | Yes | 1-100 chars |
| `last_name` | string | Yes | 1-100 chars |
| `position` | string | No | Max 200 chars |
| `slug` | string | Yes | 2-255 chars, URL-safe |
| `bio` | string | No | HTML content |
| `meta_title` | string | No | Max 70 chars |
| `meta_description` | string | No | Max 160 chars |

**Success Response (201):** Created employee object.

---

### GET /api/v1/admin/employees/{employee_id}

Get employee by ID.

**Required Permission:** `employees:read`

**Success Response (200):** Full employee object.

---

### PATCH /api/v1/admin/employees/{employee_id}

Update employee.

**Required Permission:** `employees:update`

**Request Body:**
```json
{
  "photo_url": "https://cdn.example.com/team/john-new.jpg",
  "is_published": true,
  "sort_order": 1,
  "practice_area_ids": ["pa-uuid-1"],
  "version": 1
}
```

**Success Response (200):** Updated employee object.

---

### DELETE /api/v1/admin/employees/{employee_id}

Soft delete employee.

**Required Permission:** `employees:delete`

**Response:** `204 No Content`

---

## Public Endpoints

### GET /api/v1/public/employees

List published employees.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |
| `practice_area` | string | No | Filter by practice area slug |

**Example Request:**
```bash
GET /api/v1/public/employees?tenant_id={uuid}&locale=ru
```

**Success Response (200):**
```json
[
  {
    "id": "employee-uuid",
    "photo_url": "https://cdn.example.com/team/john.jpg",
    "email": "john@company.com",
    "first_name": "Иван",
    "last_name": "Петров",
    "position": "Старший юрист",
    "slug": "ivan-petrov",
    "bio": null,
    "sort_order": 0,
    "practice_areas": [
      {
        "id": "pa-uuid",
        "title": "Корпоративное право",
        "slug": "corporate-law"
      }
    ]
  }
]
```

**Note:** `bio` is `null` in list view for performance.

---

### GET /api/v1/public/employees/{slug}

Get published employee by slug.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |

**Success Response (200):**
```json
{
  "id": "employee-uuid",
  "photo_url": "https://cdn.example.com/team/john.jpg",
  "email": "john@company.com",
  "phone": "+7 999 123-45-67",
  "first_name": "Иван",
  "last_name": "Петров",
  "position": "Старший юрист",
  "slug": "ivan-petrov",
  "bio": "<p>Иван специализируется на корпоративном праве...</p>",
  "meta_title": "Иван Петров - Старший юрист",
  "meta_description": "Профиль Ивана Петрова...",
  "practice_areas": [...]
}
```

---

## Practice Areas

Practice areas are specializations or departments that employees can be associated with.

### Data Model

```json
{
  "id": "pa-uuid",
  "tenant_id": "tenant-uuid",
  "icon": "⚖️",
  "is_published": true,
  "sort_order": 0,
  "version": 1,
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z",
  "locales": [
    {
      "id": "locale-uuid",
      "practice_area_id": "pa-uuid",
      "locale": "ru",
      "title": "Корпоративное право",
      "slug": "korporativnoe-pravo",
      "description": "Специализация на корпоративных вопросах",
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z"
    }
  ]
}
```

### POST /api/v1/admin/practice-areas

Create a practice area.

**Required Permission:** `services:create`

**Request Body:**
```json
{
  "icon": "⚖️",
  "is_published": true,
  "sort_order": 0,
  "locales": [
    {
      "locale": "ru",
      "title": "Корпоративное право",
      "slug": "korporativnoe-pravo",
      "description": "Специализация на корпоративных вопросах"
    },
    {
      "locale": "en",
      "title": "Corporate Law",
      "slug": "corporate-law",
      "description": "Specialization in corporate matters"
    }
  ]
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `icon` | string | No | Max 100 chars |
| `is_published` | boolean | No | Default: false |
| `sort_order` | integer | No | Default: 0 |
| `locales` | array | Yes | At least 1 locale |

**Locale Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars |
| `title` | string | Yes | 1-255 chars |
| `slug` | string | Yes | 2-255 chars, URL-safe |
| `description` | string | No | - |

**Success Response (201):** Created practice area object.

> **Implementation Gap:** GET (list), GET (by ID), PATCH (update), DELETE are not yet implemented. See [gap-analysis.md](./gap-analysis.md).

### GET /api/v1/public/practice-areas

List published practice areas.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |

**Success Response (200):**
```json
[
  {
    "id": "pa-uuid",
    "slug": "korporativnoe-pravo",
    "title": "Корпоративное право",
    "description": "Специализация на корпоративных вопросах",
    "icon": "⚖️"
  }
]
```

---

## Advantages

Company advantages/benefits displayed on the website.

### Data Model

```json
{
  "id": "adv-uuid",
  "tenant_id": "tenant-uuid",
  "icon": "🏆",
  "is_published": true,
  "sort_order": 0,
  "version": 1,
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z",
  "locales": [
    {
      "id": "locale-uuid",
      "advantage_id": "adv-uuid",
      "locale": "ru",
      "title": "15 лет опыта",
      "description": "Более 15 лет работы в юридической сфере",
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z"
    }
  ]
}
```

### POST /api/v1/admin/advantages

Create an advantage.

**Required Permission:** `services:create`

**Request Body:**
```json
{
  "icon": "🏆",
  "is_published": true,
  "sort_order": 0,
  "locales": [
    {
      "locale": "ru",
      "title": "15 лет опыта",
      "description": "Более 15 лет успешной работы в юридической сфере"
    },
    {
      "locale": "en",
      "title": "15 Years Experience",
      "description": "More than 15 years of successful work in the legal field"
    }
  ]
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `icon` | string | No | Max 100 chars |
| `is_published` | boolean | No | Default: false |
| `sort_order` | integer | No | Default: 0 |
| `locales` | array | Yes | At least 1 locale |

**Locale Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars |
| `title` | string | Yes | 1-255 chars |
| `description` | string | No | - |

**Success Response (201):** Created advantage object.

> **Implementation Gap:** GET (list), GET (by ID), PATCH (update), DELETE are not yet implemented. See [gap-analysis.md](./gap-analysis.md).

### GET /api/v1/public/advantages

List published advantages.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |

**Success Response (200):**
```json
[
  {
    "id": "adv-uuid",
    "title": "15 лет опыта",
    "description": "Более 15 лет работы в юридической сфере",
    "icon": "🏆"
  }
]
```

---

## Contacts & Addresses

Company contact information and office locations.

### Address Data Model

```json
{
  "id": "address-uuid",
  "tenant_id": "tenant-uuid",
  "address_type": "office",
  "latitude": 55.7558,
  "longitude": 37.6173,
  "working_hours": "Пн-Пт: 9:00-18:00",
  "phone": "+7 (495) 123-45-67",
  "email": "office@company.com",
  "is_primary": true,
  "sort_order": 0,
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z",
  "locales": [
    {
      "id": "locale-uuid",
      "address_id": "address-uuid",
      "locale": "ru",
      "name": "Главный офис",
      "country": "Россия",
      "city": "Москва",
      "street": "ул. Пушкина",
      "building": "д. 10, оф. 501",
      "postal_code": "123456",
      "full_address": "Москва, ул. Пушкина, д. 10, оф. 501, 123456",
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z"
    }
  ]
}
```

### POST /api/v1/admin/addresses

Create an address.

**Required Permission:** `settings:update`

**Request Body:**
```json
{
  "address_type": "office",
  "latitude": 55.7558,
  "longitude": 37.6173,
  "working_hours": "Пн-Пт: 9:00-18:00",
  "phone": "+7 (495) 123-45-67",
  "email": "office@company.com",
  "is_primary": true,
  "sort_order": 0,
  "locales": [
    {
      "locale": "ru",
      "name": "Главный офис",
      "country": "Россия",
      "city": "Москва",
      "street": "ул. Пушкина",
      "building": "д. 10, оф. 501",
      "postal_code": "123456"
    }
  ]
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `address_type` | string | No | `office`, `warehouse`, `showroom`, `other` |
| `latitude` | float | No | - |
| `longitude` | float | No | - |
| `working_hours` | string | No | Max 255 chars |
| `phone` | string | No | Max 50 chars |
| `email` | string | No | Max 255 chars |
| `is_primary` | boolean | No | Default: false |
| `sort_order` | integer | No | Default: 0 |
| `locales` | array | Yes | At least 1 locale |

**Locale Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars |
| `name` | string | No | Max 255 chars |
| `country` | string | No | Max 100 chars |
| `city` | string | No | Max 100 chars |
| `street` | string | Yes | Max 255 chars |
| `building` | string | No | Max 50 chars |
| `postal_code` | string | No | Max 20 chars |

**Success Response (201):** Created address object.

### Contact Data Model

```json
{
  "id": "contact-uuid",
  "tenant_id": "tenant-uuid",
  "contact_type": "phone",
  "value": "+7 (495) 123-45-67",
  "label": "Отдел продаж",
  "icon": "📞",
  "is_primary": true,
  "sort_order": 0,
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z"
}
```

### POST /api/v1/admin/contacts

Create a contact.

**Required Permission:** `settings:update`

**Request Body:**
```json
{
  "contact_type": "phone",
  "value": "+7 (495) 123-45-67",
  "label": "Отдел продаж",
  "icon": "📞",
  "is_primary": true,
  "sort_order": 0
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `contact_type` | string | Yes | See types below |
| `value` | string | Yes | Max 255 chars |
| `label` | string | No | Max 100 chars |
| `icon` | string | No | Max 100 chars |
| `is_primary` | boolean | No | Default: false |
| `sort_order` | integer | No | Default: 0 |

**Contact Types:**
- `phone` - Phone number
- `email` - Email address
- `whatsapp` - WhatsApp
- `telegram` - Telegram
- `viber` - Viber
- `facebook` - Facebook
- `instagram` - Instagram
- `linkedin` - LinkedIn
- `youtube` - YouTube
- `other` - Other

**Success Response (201):** Created contact object.

### GET /api/v1/public/contacts

Get all contact information.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |

**Success Response (200):**
```json
{
  "addresses": [
    {
      "id": "address-uuid",
      "tenant_id": "tenant-uuid",
      "address_type": "office",
      "latitude": 55.7558,
      "longitude": 37.6173,
      "working_hours": "Пн-Пт: 9:00-18:00",
      "phone": "+7 (495) 123-45-67",
      "email": "office@company.com",
      "is_primary": true,
      "sort_order": 0,
      "locales": [...]
    }
  ],
  "contacts": [
    {
      "id": "contact-uuid",
      "tenant_id": "tenant-uuid",
      "contact_type": "phone",
      "value": "+7 (495) 123-45-67",
      "label": "Отдел продаж",
      "icon": "📞",
      "is_primary": true,
      "sort_order": 0
    }
  ]
}
```

---

## Frontend Integration

### Team Page

```jsx
const TeamPage = () => {
  const [employees, setEmployees] = useState([])
  const [filter, setFilter] = useState(null)
  
  useEffect(() => {
    const params = filter ? `?practice_area=${filter}` : ''
    api.get(`/public/employees${params}&tenant_id=${tenantId}`)
      .then(({ data }) => setEmployees(data))
  }, [filter])
  
  return (
    <div>
      <PracticeAreaFilter value={filter} onChange={setFilter} />
      <TeamGrid employees={employees} />
    </div>
  )
}

const TeamGrid = ({ employees }) => (
  <Grid columns={{ sm: 2, md: 3, lg: 4 }}>
    {employees.map(emp => (
      <EmployeeCard key={emp.id} employee={emp} />
    ))}
  </Grid>
)

const EmployeeCard = ({ employee }) => (
  <Card>
    <Avatar 
      src={employee.photo_url} 
      alt={`${employee.first_name} ${employee.last_name}`}
    />
    <Name>{employee.first_name} {employee.last_name}</Name>
    <Position>{employee.position}</Position>
    <PracticeAreas>
      {employee.practice_areas.map(pa => (
        <Tag key={pa.id}>{pa.title}</Tag>
      ))}
    </PracticeAreas>
    <Link href={`/team/${employee.slug}`}>View Profile</Link>
  </Card>
)
```

### Admin Employee Form

```jsx
const EmployeeForm = ({ employee, onSave }) => {
  const [practiceAreas, setPracticeAreas] = useState([])
  
  useEffect(() => {
    api.get('/public/practice-areas')
      .then(({ data }) => setPracticeAreas(data))
  }, [])
  
  const handleSubmit = async (formData) => {
    if (employee) {
      await api.patch(`/admin/employees/${employee.id}`, {
        ...formData,
        version: employee.version
      })
    } else {
      await api.post('/admin/employees', formData)
    }
    onSave()
  }
  
  return (
    <Form onSubmit={handleSubmit}>
      <ImageUpload name="photo_url" label="Photo" />
      <Input name="email" type="email" label="Email" />
      <Input name="phone" label="Phone" />
      
      <MultiSelect 
        name="practice_area_ids" 
        label="Practice Areas"
        options={practiceAreas.map(pa => ({
          value: pa.id,
          label: pa.locales[0]?.title
        }))}
      />
      
      <Switch name="is_published" label="Published" />
      <NumberInput name="sort_order" label="Sort Order" />
      
      <LocaleTabs>
        <Input name="first_name" label="First Name" required />
        <Input name="last_name" label="Last Name" required />
        <Input name="position" label="Position" />
        <Input name="slug" label="URL Slug" required />
        <RichEditor name="bio" label="Biography" />
        <Input name="meta_title" label="SEO Title" />
        <Textarea name="meta_description" label="SEO Description" />
      </LocaleTabs>
      
      <Button type="submit">Save</Button>
    </Form>
  )
}
```

