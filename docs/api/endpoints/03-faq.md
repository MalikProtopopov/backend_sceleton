# FAQ API

> Frequently Asked Questions management

---

## Overview

FAQ entries provide common questions and answers organized by category. Features include:
- Multi-language support via `locales`
- Category grouping
- Publish/unpublish control
- Sort order for display sequence

---

## Data Model

```json
{
  "id": "faq-uuid",
  "tenant_id": "tenant-uuid",
  "category": "general",
  "is_published": true,
  "sort_order": 0,
  "version": 1,
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z",
  "locales": [
    {
      "id": "locale-uuid",
      "faq_id": "faq-uuid",
      "locale": "ru",
      "question": "Как заказать услугу?",
      "answer": "<p>Чтобы заказать услугу...</p>"
    }
  ]
}
```

---

## Admin Endpoints

### GET /api/v1/admin/faq

List all FAQ entries with pagination and filters.

**Required Permission:** `faq:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page |
| `category` | string | - | Filter by category |
| `isPublished` | boolean | - | Filter by published status |

**Example Request:**
```bash
GET /api/v1/admin/faq?page=1&category=general&isPublished=true
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "faq-uuid-1",
      "tenant_id": "tenant-uuid",
      "category": "general",
      "is_published": true,
      "sort_order": 0,
      "version": 1,
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z",
      "locales": [
        {
          "id": "locale-uuid",
          "faq_id": "faq-uuid-1",
          "locale": "ru",
          "question": "Как заказать услугу?",
          "answer": "<p>Чтобы заказать услугу...</p>"
        }
      ]
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/v1/admin/faq

Create a new FAQ entry.

**Required Permission:** `faq:create`

**Request Body:**
```json
{
  "category": "general",
  "is_published": false,
  "sort_order": 0,
  "locales": [
    {
      "locale": "ru",
      "question": "Как заказать услугу?",
      "answer": "<p>Чтобы заказать услугу, заполните форму...</p>"
    },
    {
      "locale": "en",
      "question": "How to order a service?",
      "answer": "<p>To order a service, fill out the form...</p>"
    }
  ]
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `category` | string | No | Max 100 chars |
| `is_published` | boolean | No | Default: false |
| `sort_order` | integer | No | Default: 0 |
| `locales` | array | Yes | At least 1 locale |

**Locale Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars |
| `question` | string | Yes | 1-500 chars |
| `answer` | string | Yes | HTML content |

**Success Response (201):** Created FAQ object.

---

### GET /api/v1/admin/faq/{faq_id}

Get FAQ by ID.

**Required Permission:** `faq:read`

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `faq_id` | UUID | FAQ entry ID |

**Success Response (200):** FAQ object with all locales.

---

### PATCH /api/v1/admin/faq/{faq_id}

Update FAQ entry.

**Required Permission:** `faq:update`

**Request Body:**
```json
{
  "category": "services",
  "is_published": true,
  "sort_order": 1,
  "version": 1
}
```

**Note:** Include `version` for optimistic locking.

**Success Response (200):** Updated FAQ object.

---

### DELETE /api/v1/admin/faq/{faq_id}

Soft delete FAQ entry.

**Required Permission:** `faq:delete`

**Response:** `204 No Content`

---

## Public Endpoints

### GET /api/v1/public/faq

List published FAQ for public display.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |
| `category` | string | No | Filter by category |

**Example Request:**
```bash
GET /api/v1/public/faq?tenant_id={uuid}&locale=ru&category=general
```

**Success Response (200):**
```json
[
  {
    "id": "faq-uuid",
    "question": "Как заказать услугу?",
    "answer": "<p>Чтобы заказать услугу...</p>",
    "category": "general",
    "sort_order": 0
  }
]
```

---

## Frontend Integration

### FAQ List Component

```javascript
// Fetch FAQ grouped by category
const fetchFAQ = async () => {
  const { data } = await api.get('/admin/faq')
  
  // Group by category
  const grouped = data.items.reduce((acc, faq) => {
    const cat = faq.category || 'uncategorized'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(faq)
    return acc
  }, {})
  
  return grouped
}
```

### FAQ Editor

```jsx
const FAQEditor = ({ faq, onSave }) => {
  const [activeLocale, setActiveLocale] = useState('ru')
  
  const handleSave = async () => {
    await api.patch(`/admin/faq/${faq.id}`, {
      ...formData,
      version: faq.version
    })
    onSave()
  }
  
  return (
    <Form>
      <Input name="category" label="Category" />
      <Switch name="is_published" label="Published" />
      
      <LocaleTabs 
        value={activeLocale} 
        onChange={setActiveLocale}
      />
      
      <Input name="question" label="Question" />
      <RichEditor name="answer" label="Answer" />
      
      <Button onClick={handleSave}>Save</Button>
    </Form>
  )
}
```

### Categories

Common FAQ categories:
- `general` - General questions
- `services` - Service-related
- `pricing` - Pricing and payment
- `delivery` - Delivery and timing
- `legal` - Legal questions

