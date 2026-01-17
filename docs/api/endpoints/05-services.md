# Services API

> Company services and offerings management

---

## Overview

Services represent the main offerings of the company displayed on the website. Features include:
- Multi-language support via `locales`
- Publish/unpublish control
- Icon and cover image
- Sort order for display sequence
- SEO metadata per locale

---

## Data Model

```json
{
  "id": "service-uuid",
  "tenant_id": "tenant-uuid",
  "icon": "⚖️",
  "image_url": "https://cdn.example.com/services/legal.jpg",
  "price_from": 1500,
  "price_currency": "RUB",
  "is_published": true,
  "sort_order": 0,
  "version": 1,
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z",
  "locales": [
    {
      "id": "locale-uuid",
      "service_id": "service-uuid",
      "locale": "ru",
      "title": "Юридические услуги",
      "slug": "yuridicheskie-uslugi",
      "short_description": "Полный спектр юридической поддержки",
      "description": "<p>Мы предоставляем...</p>",
      "meta_title": "Юридические услуги | Компания",
      "meta_description": "Профессиональные юридические услуги...",
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z"
    }
  ],
  "prices": [
    {
      "id": "price-uuid",
      "service_id": "service-uuid",
      "locale": "ru",
      "price": 1500.00,
      "currency": "RUB",
      "created_at": "2026-01-17T10:00:00Z",
      "updated_at": "2026-01-17T10:00:00Z"
    },
    {
      "id": "price-uuid-2",
      "service_id": "service-uuid",
      "locale": "ru",
      "price": 20.00,
      "currency": "USD",
      "created_at": "2026-01-17T10:00:00Z",
      "updated_at": "2026-01-17T10:00:00Z"
    }
  ],
  "tags": [
    {
      "id": "tag-uuid",
      "service_id": "service-uuid",
      "locale": "ru",
      "tag": "консультация",
      "created_at": "2026-01-17T10:00:00Z",
      "updated_at": "2026-01-17T10:00:00Z"
    },
    {
      "id": "tag-uuid-2",
      "service_id": "service-uuid",
      "locale": "ru",
      "tag": "юридические услуги",
      "created_at": "2026-01-17T10:00:00Z",
      "updated_at": "2026-01-17T10:00:00Z"
    }
  ]
}
```

### Key Features

- **Multiple Prices per Service**: Services can have multiple prices in different currencies (RUB, USD) per locale
- **Multiple Tags per Service**: Services can have multiple tags for categorization per locale
- **Locale-based**: Both prices and tags are tied to specific locales, allowing different pricing and tags for different languages

---

## Admin Endpoints

### GET /api/v1/admin/services

List all services with pagination and filters.

**Required Permission:** `services:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page |
| `isPublished` | boolean | - | Filter by published status |

**Example Request:**
```bash
GET /api/v1/admin/services?isPublished=true
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "service-uuid",
      "tenant_id": "tenant-uuid",
      "icon": "⚖️",
      "cover_image_url": "https://cdn.example.com/services/legal.jpg",
      "is_published": true,
      "sort_order": 0,
      "version": 1,
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z",
      "locales": [...]
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/v1/admin/services

Create a new service.

**Required Permission:** `services:create`

**Request Body:**
```json
{
  "icon": "⚖️",
  "cover_image_url": "https://cdn.example.com/services/legal.jpg",
  "is_published": false,
  "sort_order": 0,
  "locales": [
    {
      "locale": "ru",
      "title": "Юридические услуги",
      "slug": "yuridicheskie-uslugi",
      "short_description": "Полный спектр юридической поддержки",
      "description": "<p>Мы предоставляем полный спектр...</p>",
      "meta_title": "Юридические услуги | Компания",
      "meta_description": "Профессиональные юридические услуги для бизнеса"
    }
  ]
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `icon` | string | No | Max 10 chars (emoji) |
| `cover_image_url` | string | No | Max 500 chars |
| `is_published` | boolean | No | Default: false |
| `sort_order` | integer | No | Default: 0 |
| `locales` | array | Yes | At least 1 locale |

**Locale Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars |
| `title` | string | Yes | 1-255 chars |
| `slug` | string | Yes | 2-255 chars, URL-safe |
| `short_description` | string | No | Max 500 chars |
| `description` | string | No | HTML content |
| `meta_title` | string | No | Max 70 chars |
| `meta_description` | string | No | Max 160 chars |
| `meta_keywords` | string | No | Max 255 chars |

**Success Response (201):** Created service object.

---

### GET /api/v1/admin/services/{service_id}

Get service by ID.

**Required Permission:** `services:read`

**Success Response (200):** Full service object with `prices` and `tags` arrays.

---

### PATCH /api/v1/admin/services/{service_id}

Update service.

**Required Permission:** `services:update`

**Request Body:**
```json
{
  "icon": "🏛️",
  "is_published": true,
  "sort_order": 1,
  "version": 1
}
```

**Success Response (200):** Updated service object.

---

### DELETE /api/v1/admin/services/{service_id}

Soft delete service.

**Required Permission:** `services:delete`

**Response:** `204 No Content`

---

## Managing Prices

Services can have multiple prices in different currencies per locale. Each price is unique per `service_id + locale + currency` combination.

### POST /api/v1/admin/services/{service_id}/prices

Add a price to a service.

**Required Permission:** `services:update`

**Request Body:**
```json
{
  "locale": "ru",
  "price": 1500.00,
  "currency": "RUB"
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars (e.g., "ru", "en") |
| `price` | number | Yes | >= 0, 2 decimal places |
| `currency` | string | Yes | "RUB" or "USD" (uppercase) |

**Example Requests:**
```bash
# Add price in RUB
POST /api/v1/admin/services/{service_id}/prices
{
  "locale": "ru",
  "price": 1500.00,
  "currency": "RUB"
}

# Add price in USD
POST /api/v1/admin/services/{service_id}/prices
{
  "locale": "ru",
  "price": 20.00,
  "currency": "USD"
}
```

**Success Response (201):**
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

**Error Response (400):** If price already exists for `locale + currency` combination:
```json
{
  "detail": "Price for locale 'ru' and currency 'RUB' already exists"
}
```

---

### PATCH /api/v1/admin/services/{service_id}/prices/{price_id}

Update a service price.

**Required Permission:** `services:update`

**Request Body:**
```json
{
  "price": 1800.00,
  "currency": "RUB"
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `price` | number | No | >= 0, 2 decimal places |
| `currency` | string | No | "RUB" or "USD" |

**Success Response (200):** Updated price object.

---

### DELETE /api/v1/admin/services/{service_id}/prices/{price_id}

Delete a price from a service.

**Required Permission:** `services:update`

**Response:** `204 No Content`

---

## Managing Tags

Services can have multiple tags per locale for categorization. Each tag is unique per `service_id + locale + tag` combination.

### POST /api/v1/admin/services/{service_id}/tags

Add a tag to a service.

**Required Permission:** `services:update`

**Request Body:**
```json
{
  "locale": "ru",
  "tag": "консультация"
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars (e.g., "ru", "en") |
| `tag` | string | Yes | 1-100 chars |

**Example Requests:**
```bash
# Add first tag
POST /api/v1/admin/services/{service_id}/tags
{
  "locale": "ru",
  "tag": "консультация"
}

# Add second tag
POST /api/v1/admin/services/{service_id}/tags
{
  "locale": "ru",
  "tag": "юридические услуги"
}
```

**Success Response (201):**
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

**Error Response (400):** If tag already exists for `locale + tag` combination:
```json
{
  "detail": "Tag 'консультация' for locale 'ru' already exists"
}
```

---

### PATCH /api/v1/admin/services/{service_id}/tags/{tag_id}

Update a service tag.

**Required Permission:** `services:update`

**Request Body:**
```json
{
  "locale": "ru",
  "tag": "юридическая консультация"
}
```

**Note:** Both `locale` and `tag` must be provided. If changing either, the system will check for uniqueness.

**Success Response (200):** Updated tag object.

---

### DELETE /api/v1/admin/services/{service_id}/tags/{tag_id}

Delete a tag from a service.

**Required Permission:** `services:update`

**Response:** `204 No Content`

---

## Public Endpoints

### GET /api/v1/public/services

List published services.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |

**Success Response (200):**
```json
[
  {
    "id": "service-uuid",
    "icon": "⚖️",
    "image_url": "https://cdn.example.com/services/legal.jpg",
    "title": "Юридические услуги",
    "slug": "yuridicheskie-uslugi",
    "short_description": "Полный спектр юридической поддержки",
    "description": null,
    "price_from": 1500,
    "price_currency": "RUB",
    "prices": [
      {"price": 1500.0, "currency": "RUB"},
      {"price": 20.0, "currency": "USD"}
    ],
    "tags": ["консультация", "юридические услуги"],
    "meta_title": "Юридические услуги | Компания",
    "meta_description": "Профессиональные юридические услуги..."
  }
]
```

**Note:** 
- `description` is `null` in list view. Fetch single service for full content.
- `prices` contains only prices for the requested locale. If no prices exist, returns empty array `[]`.
- `tags` contains only tags for the requested locale. If no tags exist, returns empty array `[]`.

---

### GET /api/v1/public/services/{slug}

Get published service by slug.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |

**Success Response (200):**
```json
{
  "id": "service-uuid",
  "icon": "⚖️",
  "image_url": "https://cdn.example.com/services/legal.jpg",
  "title": "Юридические услуги",
  "slug": "yuridicheskie-uslugi",
  "short_description": "Полный спектр юридической поддержки",
  "description": "<p>Мы предоставляем полный спектр...</p>",
  "price_from": 1500,
  "price_currency": "RUB",
  "prices": [
    {"price": 1500.0, "currency": "RUB"},
    {"price": 20.0, "currency": "USD"}
  ],
  "tags": ["консультация", "юридические услуги", "срочно"],
  "meta_title": "Юридические услуги | Компания",
  "meta_description": "Профессиональные юридические услуги..."
}
```

**Note:** 
- `prices` array contains objects with `price` (float) and `currency` (string) for the requested locale
- `tags` array contains strings for the requested locale
- If no prices/tags exist for the locale, arrays will be empty `[]`

---

## Frontend Integration

### Services Grid

```jsx
const ServicesGrid = () => {
  const [services, setServices] = useState([])
  
  useEffect(() => {
    api.get('/admin/services?isPublished=true')
      .then(({ data }) => setServices(data.items))
  }, [])
  
  return (
    <Grid columns={3}>
      {services.map(service => (
        <ServiceCard key={service.id} service={service} />
      ))}
    </Grid>
  )
}

const ServiceCard = ({ service }) => {
  const locale = service.locales[0]
  
  return (
    <Card>
      {service.image_url && (
        <Image src={service.image_url} />
      )}
      <Icon>{service.icon}</Icon>
      <Title>{locale?.title}</Title>
      <Description>{locale?.short_description}</Description>
      <Link href={`/services/${locale?.slug}`}>Learn More</Link>
    </Card>
  )
}
```

### Displaying Prices and Tags (Public API)

```jsx
const ServiceDetail = ({ slug }) => {
  const [service, setService] = useState(null)
  const locale = 'ru' // Get from context/state
  const tenantId = 'your-tenant-id'
  
  useEffect(() => {
    api.get(`/public/services/${slug}`, {
      params: { tenant_id: tenantId, locale }
    })
      .then(({ data }) => setService(data))
  }, [slug, locale])
  
  if (!service) return <Loading />
  
  return (
    <div>
      <h1>{service.title}</h1>
      <p>{service.description}</p>
      
      {/* Display prices */}
      {service.prices && service.prices.length > 0 && (
        <div>
          <h3>Цены:</h3>
          {service.prices.map((price, index) => (
            <div key={index}>
              {price.price} {price.currency}
            </div>
          ))}
        </div>
      )}
      
      {/* Display tags */}
      {service.tags && service.tags.length > 0 && (
        <div>
          <h3>Теги:</h3>
          {service.tags.map((tag, index) => (
            <Tag key={index}>{tag}</Tag>
          ))}
        </div>
      )}
    </div>
  )
}
```

### Managing Prices (Admin)

```jsx
const ServicePricesManager = ({ serviceId }) => {
  const [prices, setPrices] = useState([])
  const [newPrice, setNewPrice] = useState({ locale: 'ru', price: '', currency: 'RUB' })
  
  // Fetch prices
  useEffect(() => {
    api.get(`/admin/services/${serviceId}`)
      .then(({ data }) => setPrices(data.prices || []))
  }, [serviceId])
  
  // Add price
  const handleAddPrice = async () => {
    try {
      const { data } = await api.post(`/admin/services/${serviceId}/prices`, {
        locale: newPrice.locale,
        price: parseFloat(newPrice.price),
        currency: newPrice.currency
      })
      setPrices([...prices, data])
      setNewPrice({ locale: 'ru', price: '', currency: 'RUB' })
    } catch (error) {
      console.error('Failed to add price:', error.response?.data)
    }
  }
  
  // Update price
  const handleUpdatePrice = async (priceId, updatedPrice) => {
    try {
      const { data } = await api.patch(
        `/admin/services/${serviceId}/prices/${priceId}`,
        updatedPrice
      )
      setPrices(prices.map(p => p.id === priceId ? data : p))
    } catch (error) {
      console.error('Failed to update price:', error.response?.data)
    }
  }
  
  // Delete price
  const handleDeletePrice = async (priceId) => {
    try {
      await api.delete(`/admin/services/${serviceId}/prices/${priceId}`)
      setPrices(prices.filter(p => p.id !== priceId))
    } catch (error) {
      console.error('Failed to delete price:', error.response?.data)
    }
  }
  
  return (
    <div>
      <h3>Цены услуги</h3>
      
      {/* Add new price form */}
      <div>
        <select value={newPrice.locale} onChange={e => setNewPrice({...newPrice, locale: e.target.value})}>
          <option value="ru">RU</option>
          <option value="en">EN</option>
        </select>
        <input 
          type="number" 
          value={newPrice.price}
          onChange={e => setNewPrice({...newPrice, price: e.target.value})}
          placeholder="Цена"
          step="0.01"
        />
        <select value={newPrice.currency} onChange={e => setNewPrice({...newPrice, currency: e.target.value})}>
          <option value="RUB">RUB</option>
          <option value="USD">USD</option>
        </select>
        <button onClick={handleAddPrice}>Добавить цену</button>
      </div>
      
      {/* Prices list */}
      {prices.map(price => (
        <div key={price.id}>
          {price.price} {price.currency} ({price.locale})
          <button onClick={() => handleDeletePrice(price.id)}>Удалить</button>
        </div>
      ))}
    </div>
  )
}
```

### Managing Tags (Admin)

```jsx
const ServiceTagsManager = ({ serviceId }) => {
  const [tags, setTags] = useState([])
  const [newTag, setNewTag] = useState({ locale: 'ru', tag: '' })
  
  // Fetch tags
  useEffect(() => {
    api.get(`/admin/services/${serviceId}`)
      .then(({ data }) => setTags(data.tags || []))
  }, [serviceId])
  
  // Add tag
  const handleAddTag = async () => {
    try {
      const { data } = await api.post(`/admin/services/${serviceId}/tags`, newTag)
      setTags([...tags, data])
      setNewTag({ locale: 'ru', tag: '' })
    } catch (error) {
      console.error('Failed to add tag:', error.response?.data)
    }
  }
  
  // Update tag
  const handleUpdateTag = async (tagId, updatedTag) => {
    try {
      const { data } = await api.patch(
        `/admin/services/${serviceId}/tags/${tagId}`,
        updatedTag
      )
      setTags(tags.map(t => t.id === tagId ? data : t))
    } catch (error) {
      console.error('Failed to update tag:', error.response?.data)
    }
  }
  
  // Delete tag
  const handleDeleteTag = async (tagId) => {
    try {
      await api.delete(`/admin/services/${serviceId}/tags/${tagId}`)
      setTags(tags.filter(t => t.id !== tagId))
    } catch (error) {
      console.error('Failed to delete tag:', error.response?.data)
    }
  }
  
  return (
    <div>
      <h3>Теги услуги</h3>
      
      {/* Add new tag form */}
      <div>
        <select value={newTag.locale} onChange={e => setNewTag({...newTag, locale: e.target.value})}>
          <option value="ru">RU</option>
          <option value="en">EN</option>
        </select>
        <input 
          type="text" 
          value={newTag.tag}
          onChange={e => setNewTag({...newTag, tag: e.target.value})}
          placeholder="Название тега"
        />
        <button onClick={handleAddTag}>Добавить тег</button>
      </div>
      
      {/* Tags list */}
      {tags.map(tag => (
        <div key={tag.id}>
          <Tag>{tag.tag} ({tag.locale})</Tag>
          <button onClick={() => handleDeleteTag(tag.id)}>Удалить</button>
        </div>
      ))}
    </div>
  )
}
```

### Drag-and-Drop Reorder

```javascript
// Update sort order after drag-and-drop
const handleReorder = async (reorderedServices) => {
  const updates = reorderedServices.map((service, index) => ({
    id: service.id,
    sort_order: index,
    version: service.version
  }))
  
  // Batch update (would need bulk endpoint)
  // For now, update one by one
  for (const update of updates) {
    await api.patch(`/admin/services/${update.id}`, {
      sort_order: update.sort_order,
      version: update.version
    })
  }
}
```

