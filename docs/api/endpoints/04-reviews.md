# Reviews API

> Customer reviews and testimonials management with moderation workflow

---

## Overview

Reviews represent customer testimonials that require moderation before publication. Features include:
- Moderation workflow (pending → approved/rejected)
- Association with Cases (projects)
- Featured review flag
- Rating support (1-5)

---

## State Machine

```
                    ┌──────────────┐
                    │   PENDING    │
                    └──────┬───────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌──────────────┐          ┌──────────────┐
    │   APPROVED   │          │   REJECTED   │
    └──────────────┘          └──────────────┘
```

| From | To | Action | Endpoint |
|------|-----|--------|----------|
| Pending | Approved | Approve | `POST /reviews/{id}/approve` |
| Pending | Rejected | Reject | `POST /reviews/{id}/reject` |
| Approved | Pending | Reset | `PATCH` with `status: pending` |
| Rejected | Pending | Reset | `PATCH` with `status: pending` |

---

## Data Model

```json
{
  "id": "review-uuid",
  "tenant_id": "tenant-uuid",
  "status": "pending",
  "case_id": "case-uuid",
  "author_name": "Иван Петров",
  "author_position": "CEO, Company Inc",
  "author_avatar_url": "https://cdn.example.com/avatars/ivan.jpg",
  "rating": 5,
  "is_featured": false,
  "sort_order": 0,
  "version": 1,
  "review_date": "2026-01-10",
  "created_at": "2026-01-14T10:00:00Z",
  "updated_at": "2026-01-14T10:00:00Z",
  "locales": [
    {
      "id": "locale-uuid",
      "review_id": "review-uuid",
      "locale": "ru",
      "content": "Отличная работа команды...",
      "company_name": "ООО Компания"
    }
  ]
}
```

---

## Admin Endpoints

### GET /api/v1/admin/reviews

List all reviews with pagination and filters.

**Required Permission:** `reviews:read`

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `pageSize` | integer | 20 | Items per page |
| `status` | string | - | Filter: `pending`, `approved`, `rejected` |
| `caseId` | UUID | - | Filter by associated case |
| `featured` | boolean | - | Filter by featured flag |

**Example Request:**
```bash
GET /api/v1/admin/reviews?status=pending
Authorization: Bearer {token}
```

**Success Response (200):**
```json
{
  "items": [
    {
      "id": "review-uuid",
      "tenant_id": "tenant-uuid",
      "status": "pending",
      "case_id": null,
      "author_name": "Иван Петров",
      "author_position": "CEO, Company Inc",
      "author_avatar_url": null,
      "rating": 5,
      "is_featured": false,
      "sort_order": 0,
      "version": 1,
      "review_date": "2026-01-10",
      "created_at": "2026-01-14T10:00:00Z",
      "updated_at": "2026-01-14T10:00:00Z",
      "locales": [...]
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20
}
```

---

### POST /api/v1/admin/reviews

Create a new review.

**Required Permission:** `reviews:create`

**Request Body:**
```json
{
  "author_name": "Иван Петров",
  "author_position": "CEO, Company Inc",
  "author_avatar_url": "https://cdn.example.com/avatars/ivan.jpg",
  "rating": 5,
  "is_featured": false,
  "sort_order": 0,
  "review_date": "2026-01-10",
  "case_id": "case-uuid-or-null",
  "locales": [
    {
      "locale": "ru",
      "content": "Отличная работа команды! Рекомендую всем.",
      "company_name": "ООО Компания"
    }
  ]
}
```

**Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `author_name` | string | Yes | 1-200 chars |
| `author_position` | string | No | Max 200 chars |
| `author_avatar_url` | string | No | Max 500 chars |
| `rating` | integer | No | 1-5 |
| `is_featured` | boolean | No | Default: false |
| `sort_order` | integer | No | Default: 0 |
| `review_date` | date | No | ISO date format |
| `case_id` | UUID | No | Must exist if provided |
| `locales` | array | Yes | At least 1 locale |

**Locale Field Validation:**
| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `locale` | string | Yes | 2-5 chars |
| `content` | string | Yes | Review text |
| `company_name` | string | No | Max 200 chars |

**Success Response (201):** Created review with `status: pending`.

---

### GET /api/v1/admin/reviews/{review_id}

Get review by ID.

**Required Permission:** `reviews:read`

**Success Response (200):** Full review object.

---

### PATCH /api/v1/admin/reviews/{review_id}

Update review.

**Required Permission:** `reviews:update`

**Request Body:**
```json
{
  "author_name": "Иван С. Петров",
  "rating": 4,
  "is_featured": true,
  "version": 1
}
```

**Success Response (200):** Updated review object.

---

### POST /api/v1/admin/reviews/{review_id}/approve

Approve a pending review for publication.

**Required Permission:** `reviews:update`

**Request Body:** None

**Success Response (200):**
```json
{
  "id": "review-uuid",
  "status": "approved",
  "version": 2,
  ...
}
```

**Error Response (422):**
```json
{
  "type": "https://api.cms.local/errors/validation_error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Review is already approved"
}
```

---

### POST /api/v1/admin/reviews/{review_id}/reject

Reject a pending review.

**Required Permission:** `reviews:update`

**Request Body:** None (or optional rejection reason)

**Success Response (200):**
```json
{
  "id": "review-uuid",
  "status": "rejected",
  "version": 2,
  ...
}
```

---

### DELETE /api/v1/admin/reviews/{review_id}

Soft delete review.

**Required Permission:** `reviews:delete`

**Response:** `204 No Content`

---

## Public Endpoints

### GET /api/v1/public/reviews

List approved reviews for public display.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tenant_id` | UUID | Yes | Tenant ID |
| `locale` | string | No | Locale code (default: `ru`) |
| `featured` | boolean | No | Only featured reviews |
| `limit` | integer | No | Max items (default: 10) |

**Example Request:**
```bash
GET /api/v1/public/reviews?tenant_id={uuid}&locale=ru&featured=true
```

**Success Response (200):**
```json
[
  {
    "id": "review-uuid",
    "author_name": "Иван Петров",
    "author_position": "CEO, Company Inc",
    "author_avatar_url": "https://cdn.example.com/avatars/ivan.jpg",
    "content": "Отличная работа команды! Рекомендую всем.",
    "company_name": "ООО Компания",
    "rating": 5,
    "review_date": "2026-01-10"
  }
]
```

---

## Frontend Integration

### Reviews Moderation Queue

```javascript
// Fetch pending reviews
const fetchPendingReviews = async () => {
  const { data } = await api.get('/admin/reviews?status=pending')
  return data.items
}

// Approve review
const approveReview = async (id) => {
  await api.post(`/admin/reviews/${id}/approve`)
  showNotification({ type: 'success', message: 'Review approved' })
}

// Reject review
const rejectReview = async (id) => {
  await api.post(`/admin/reviews/${id}/reject`)
  showNotification({ type: 'warning', message: 'Review rejected' })
}
```

### Review Card Component

```jsx
const ReviewCard = ({ review, onApprove, onReject }) => {
  const statusBadge = {
    pending: { color: 'yellow', label: 'Pending' },
    approved: { color: 'green', label: 'Approved' },
    rejected: { color: 'red', label: 'Rejected' }
  }
  
  return (
    <Card>
      <Header>
        <Avatar src={review.author_avatar_url} />
        <div>
          <Name>{review.author_name}</Name>
          <Position>{review.author_position}</Position>
        </div>
        <Badge {...statusBadge[review.status]} />
      </Header>
      
      <Rating value={review.rating} />
      <Content>{review.locales[0]?.content}</Content>
      
      {review.status === 'pending' && (
        <Actions>
          <Button onClick={() => onApprove(review.id)}>Approve</Button>
          <Button danger onClick={() => onReject(review.id)}>Reject</Button>
        </Actions>
      )}
    </Card>
  )
}
```

### Featured Reviews Carousel

```jsx
const FeaturedReviews = () => {
  const [reviews, setReviews] = useState([])
  
  useEffect(() => {
    api.get('/public/reviews?featured=true&limit=5')
      .then(({ data }) => setReviews(data))
  }, [])
  
  return (
    <Carousel>
      {reviews.map(review => (
        <ReviewSlide key={review.id} review={review} />
      ))}
    </Carousel>
  )
}
```

