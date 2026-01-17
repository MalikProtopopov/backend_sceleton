# Leads & Inquiries API

> Customer inquiries, contact forms, and lead management

---

## Overview

The Leads module manages customer inquiries submitted through website forms. Features include:
- Inquiry form configuration
- Inquiry status tracking
- User assignment
- UTM parameter tracking
- Analytics and reporting
- Notes/comments per inquiry

---

## Inquiry Status Flow

```
┌─────────┐    ┌─────────────┐    ┌───────────┐    ┌───────────┐
│   NEW   │───▶│ IN_PROGRESS │───▶│ CONTACTED │───▶│ COMPLETED │
└─────────┘    └─────────────┘    └───────────┘    └───────────┘
     │                                                    │
     │                                                    │
     ▼                                                    ▼
┌─────────┐                                         ┌─────────┐
│  SPAM   │                                         │CANCELLED│
└─────────┘                                         └─────────┘
```

| Status | Description |
|--------|-------------|
| `new` | New inquiry, not yet processed |
| `in_progress` | Being handled by staff |
| `contacted` | Customer has been contacted |
| `completed` | Inquiry resolved |
| `spam` | Marked as spam |
| `cancelled` | Cancelled by user or system |

---

## Inquiry Forms

### GET /api/v1/admin/inquiry-forms

List all inquiry forms.

**Required Permission:** `inquiries:read`

**Success Response (200):**
```json
[
  {
    "id": "form-uuid",
    "tenant_id": "tenant-uuid",
    "name": "Contact Form",
    "slug": "contact",
    "description": "Main contact form",
    "is_active": true,
    "notification_email": "sales@company.com",
    "success_message": {
      "ru": "Спасибо! Мы свяжемся с вами в ближайшее время.",
      "en": "Thank you! We will contact you soon."
    },
    "fields_config": {
      "fields": [
        { "name": "name", "type": "text", "required": true },
        { "name": "email", "type": "email", "required": true },
        { "name": "phone", "type": "tel", "required": false },
        { "name": "message", "type": "textarea", "required": true }
      ]
    },
    "sort_order": 0,
    "version": 1,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z"
  }
]
```

---

### POST /api/v1/admin/inquiry-forms

Create a new inquiry form.

**Required Permission:** `settings:update`

**Request Body:**
```json
{
  "name": "Consultation Request",
  "slug": "consultation",
  "description": "Form for requesting a consultation",
  "is_active": true,
  "notification_email": "consultations@company.com",
  "success_message": {
    "ru": "Спасибо за заявку!",
    "en": "Thank you for your request!"
  },
  "fields_config": {
  "fields": [
      { "name": "name", "type": "text", "label": "Full Name", "required": true },
      { "name": "email", "type": "email", "label": "Email", "required": true },
      { "name": "service", "type": "select", "label": "Service", "options": ["Corporate Law", "Tax"] }
    ]
  },
  "sort_order": 0
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | 1-255 chars |
| `slug` | string | Yes | 2-100 chars, unique |
| `description` | string | No | - |
| `is_active` | boolean | No | Default: true |
| `notification_email` | string | No | Max 255 chars |
| `success_message` | object | No | JSON with locale keys |
| `fields_config` | object | No | Form field configuration |
| `sort_order` | integer | No | Default: 0 |

---

### PATCH /api/v1/admin/inquiry-forms/{form_id}

Update inquiry form.

**Required Permission:** `settings:update`

---

### DELETE /api/v1/admin/inquiry-forms/{form_id}

Soft delete inquiry form.

**Required Permission:** `settings:update`

---

## Inquiries

### GET /api/v1/admin/inquiries

List all inquiries with pagination and filters.

**Required Permission:** `inquiries:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page |
| `status` | string | - | Filter by status |
| `formId` | UUID | - | Filter by form |
| `assignedTo` | UUID | - | Filter by assigned user |
| `utmSource` | string | - | Filter by UTM source |

**Example Request:**
```bash
GET /api/v1/admin/inquiries?status=new&page=1
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "inquiry-uuid",
      "tenant_id": "tenant-uuid",
      "form_id": "form-uuid",
      "status": "new",
        "name": "Иван Петров",
        "email": "ivan@example.com",
        "phone": "+7 999 123-45-67",
      "company": "ООО Компания",
      "message": "Хочу узнать о ваших услугах...",
      "service_id": null,
      "utm_source": "google",
      "utm_medium": "cpc",
      "utm_campaign": "brand",
      "utm_term": null,
      "utm_content": null,
      "referrer_url": "https://google.com",
      "source_url": "https://company.com/contact",
      "page_path": "/contact",
      "page_title": "Contact Us",
      "device_type": "desktop",
      "browser": "Chrome",
      "os": "Windows",
      "ip_address": "192.168.1.1",
      "country": "RU",
      "city": "Moscow",
      "session_id": null,
      "session_page_views": null,
      "time_on_page": null,
      "assigned_to": null,
      "notes": null,
      "contacted_at": null,
      "notification_sent": false,
      "custom_fields": null,
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z"
    }
  ],
  "total": 156,
  "page": 1,
  "page_size": 20
}
```

---

### GET /api/v1/admin/inquiries/{inquiry_id}

Get inquiry by ID.

**Required Permission:** `inquiries:read`

**Success Response (200):** Full inquiry object.

---

### PATCH /api/v1/admin/inquiries/{inquiry_id}

Update inquiry (status, assignment, notes).

**Required Permission:** `inquiries:update`

**Request Body:**
```json
{
  "status": "in_progress",
  "assigned_to": "user-uuid",
  "notes": "Called customer on 14.01.2026. Scheduled follow-up for 16.01."
}
```

**Field Validation:**
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | New status value |
| `assigned_to` | UUID | User to assign (or null to unassign) |
| `notes` | string | Internal notes |

**Success Response (200):** Updated inquiry object.

---

### DELETE /api/v1/admin/inquiries/{inquiry_id}

Soft delete inquiry.

**Required Permission:** `inquiries:delete`

**Response:** `204 No Content`

---

### GET /api/v1/admin/inquiries/analytics

Get inquiry analytics summary.

**Required Permission:** `inquiries:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Number of days to analyze |

**Example Request:**
```bash
GET /api/v1/admin/inquiries/analytics?days=30
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
    "total": 156,
  "by_status": {
    "new": 23,
    "in_progress": 12,
    "contacted": 8,
    "completed": 98,
    "spam": 15
  },
  "by_utm_source": {
    "google": 78,
    "direct": 45,
    "facebook": 33
  },
  "by_device_type": {
    "desktop": 89,
    "mobile": 52,
    "tablet": 15
  },
  "by_day": [
    { "date": "2026-01-14", "count": 8 },
    { "date": "2026-01-13", "count": 5 },
    { "date": "2026-01-12", "count": 12 }
  ]
}
```

---

## Public Endpoint

### POST /api/v1/public/inquiries

Submit an inquiry (public form submission).

**Rate Limit:** 3 requests per 60 seconds per IP (planned, not yet implemented)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |

**Request Body:**
```json
{
  "form_slug": "contact",
    "name": "Иван Петров",
    "email": "ivan@example.com",
    "phone": "+7 999 123-45-67",
  "company": "ООО Компания",
  "message": "Хочу узнать о ваших услугах...",
  "service_id": "service-uuid",
  "analytics": {
  "utm_source": "google",
  "utm_medium": "cpc",
    "utm_campaign": "brand",
    "referrer_url": "https://google.com",
    "source_url": "https://company.com/services",
    "page_path": "/services",
    "page_title": "Services",
    "user_agent": "Mozilla/5.0...",
    "device_type": "desktop",
    "browser": "Chrome",
    "os": "Windows"
  },
  "custom_fields": {
    "preferred_time": "morning",
    "budget": "100000"
  }
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `form_slug` | string | No | Max 100 chars |
| `name` | string | Yes | 1-255 chars |
| `email` | string | No | Valid email format |
| `phone` | string | No | Max 50 chars |
| `company` | string | No | Max 255 chars |
| `message` | string | No | - |
| `service_id` | UUID | No | Link to service |
| `analytics` | object | No | Analytics data |
| `custom_fields` | object | No | Custom form fields |

**Success Response (201):**
```json
{
  "id": "inquiry-uuid",
  "tenant_id": "tenant-uuid",
  "form_id": null,
  "status": "new",
  "name": "Иван Петров",
  "email": "ivan@example.com",
  "phone": "+7 999 123-45-67",
  "company": "ООО Компания",
  "message": "Хочу узнать о ваших услугах...",
  "service_id": "service-uuid",
  "utm_source": "google",
  "utm_medium": "cpc",
  "utm_campaign": "brand",
  "utm_term": null,
  "utm_content": null,
  "referrer_url": "https://google.com",
  "source_url": "https://company.com/services",
  "page_path": "/services",
  "page_title": "Services",
  "device_type": "desktop",
  "browser": "Chrome",
  "os": "Windows",
  "ip_address": "192.168.1.1",
  "country": null,
  "city": null,
  "session_id": null,
  "session_page_views": null,
  "time_on_page": null,
  "assigned_to": null,
  "notes": null,
  "contacted_at": null,
  "notification_sent": false,
  "custom_fields": {
    "preferred_time": "morning",
    "budget": "100000"
  },
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z"
}
```

**Error Response (422):**
```json
{
  "type": "https://api.cms.local/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed",
  "errors": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

**Error Response (429):** (planned)
```json
{
  "type": "https://api.cms.local/errors/rate_limit_exceeded",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many submissions. Please try again later.",
  "retry_after": 60
}
```

---

## Frontend Integration

### Inquiries List with Filters

```jsx
const InquiriesList = () => {
  const [inquiries, setInquiries] = useState([])
  const [filters, setFilters] = useState({
    status: '',
    formId: '',
    page: 1
  })
  
  useEffect(() => {
    const params = new URLSearchParams()
    if (filters.status) params.set('status', filters.status)
    if (filters.formId) params.set('formId', filters.formId)
    params.set('page', filters.page)
    
    api.get(`/admin/inquiries?${params}`)
      .then(({ data }) => setInquiries(data))
  }, [filters])
  
  return (
    <div>
      <Filters>
        <Select 
          value={filters.status} 
          onChange={(v) => setFilters({ ...filters, status: v })}
          options={[
            { value: '', label: 'All Statuses' },
            { value: 'new', label: 'New' },
            { value: 'in_progress', label: 'In Progress' },
            { value: 'completed', label: 'Completed' }
          ]}
        />
      </Filters>
      
      <Table>
        {inquiries.items?.map(inq => (
          <InquiryRow key={inq.id} inquiry={inq} />
        ))}
      </Table>
      
      <Pagination 
        total={inquiries.total}
        page={filters.page}
        pageSize={20}
        onChange={(p) => setFilters({ ...filters, page: p })}
      />
    </div>
  )
}
```

### Kanban Board View

```jsx
const InquiriesKanban = () => {
  const [inquiries, setInquiries] = useState([])
  
  useEffect(() => {
    api.get('/admin/inquiries?pageSize=100')
      .then(({ data }) => setInquiries(data.items))
  }, [])
  
  const columns = ['new', 'in_progress', 'contacted', 'completed']
  
  const groupedByStatus = columns.reduce((acc, status) => {
    acc[status] = inquiries.filter(i => i.status === status)
    return acc
  }, {})
  
  const handleDrop = async (inquiryId, newStatus) => {
    await api.patch(`/admin/inquiries/${inquiryId}`, { status: newStatus })
    // Refresh list
  }
  
  return (
    <Board>
      {columns.map(status => (
        <Column key={status} status={status} onDrop={handleDrop}>
          {groupedByStatus[status].map(inq => (
            <InquiryCard key={inq.id} inquiry={inq} />
          ))}
        </Column>
      ))}
    </Board>
  )
}
```

### Analytics Dashboard

```jsx
const InquiriesAnalytics = () => {
  const [analytics, setAnalytics] = useState(null)
  const [days, setDays] = useState(30)
  
  useEffect(() => {
    api.get(`/admin/inquiries/analytics?days=${days}`)
      .then(({ data }) => setAnalytics(data))
  }, [days])
  
  if (!analytics) return <Loading />
  
  return (
    <Dashboard>
      <StatCards>
        <StatCard title="Total" value={analytics.summary.total} />
        <StatCard title="New" value={analytics.summary.new} color="blue" />
        <StatCard title="Completed" value={analytics.summary.completed} color="green" />
      </StatCards>
      
      <Chart 
        type="line" 
        data={analytics.by_day} 
        xKey="date" 
        yKey="count" 
      />
      
      <PieChart 
        data={analytics.by_source}
        dataKey="count"
        nameKey="source"
      />
    </Dashboard>
  )
}
```

### Public Form Submission

```jsx
const ContactForm = ({ formSlug }) => {
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  
  const handleSubmit = async (formData) => {
    setSubmitting(true)
    try {
      // Get UTM params from URL
      const urlParams = new URLSearchParams(window.location.search)
      
      await api.post(`/public/inquiries?tenant_id=${TENANT_ID}`, {
        form_slug: formSlug,
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        message: formData.message,
        analytics: {
          utm_source: urlParams.get('utm_source'),
          utm_medium: urlParams.get('utm_medium'),
          utm_campaign: urlParams.get('utm_campaign'),
          referrer_url: document.referrer,
          source_url: window.location.href,
          page_path: window.location.pathname,
          page_title: document.title,
          user_agent: navigator.userAgent
        }
      })
      
      setSuccess(true)
    } catch (error) {
      if (error.response?.status === 429) {
        showError('Please wait before submitting again')
      } else {
        showError('Something went wrong. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }
  
  if (success) {
    return <SuccessMessage>Thank you! We'll be in touch soon.</SuccessMessage>
  }
  
  return (
    <Form onSubmit={handleSubmit}>
      <Input name="name" label="Name" required />
      <Input name="email" type="email" label="Email" />
      <Input name="phone" type="tel" label="Phone" />
      <Textarea name="message" label="Message" />
      <Button type="submit" loading={submitting}>Send</Button>
    </Form>
  )
}
```

