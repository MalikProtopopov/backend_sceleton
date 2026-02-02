# Контакты для кейсов и отзывов — Изменения в Admin API

Этот документ описывает изменения в Admin API для управления контактами клиентов кейсов и авторов отзывов.

## Обзор изменений

Добавлена возможность прикреплять контакты (сайт, соцсети, email, телефон и т.д.) к:
- **Кейсам** — контакты клиента/компании из кейса
- **Отзывам** — контакты автора отзыва

## Типы контактов

Поддерживаемые значения `contact_type`:
```
website, instagram, telegram, linkedin, facebook, twitter, youtube, tiktok, email, phone, whatsapp, viber, other
```

Фронтенд может использовать этот список для отображения соответствующих иконок.

---

## Новые эндпоинты для кейсов

### POST `/api/v1/admin/cases/{case_id}/contacts`

Добавить контакт к кейсу.

**Request Body:**
```json
{
  "contact_type": "website",
  "value": "https://example.com",
  "sort_order": 0
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "contact_type": "website",
  "value": "https://example.com",
  "sort_order": 0
}
```

### PATCH `/api/v1/admin/cases/{case_id}/contacts/{contact_id}`

Обновить контакт кейса.

**Request Body:**
```json
{
  "contact_type": "instagram",
  "value": "https://instagram.com/company",
  "sort_order": 1
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "contact_type": "instagram",
  "value": "https://instagram.com/company",
  "sort_order": 1
}
```

### DELETE `/api/v1/admin/cases/{case_id}/contacts/{contact_id}`

Удалить контакт из кейса.

**Response:** `204 No Content`

---

## Новые эндпоинты для отзывов

### POST `/api/v1/admin/reviews/{review_id}/author-contacts`

Добавить контакт автора отзыва.

**Request Body:**
```json
{
  "contact_type": "linkedin",
  "value": "https://linkedin.com/in/author",
  "sort_order": 0
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "contact_type": "linkedin",
  "value": "https://linkedin.com/in/author",
  "sort_order": 0
}
```

### PATCH `/api/v1/admin/reviews/{review_id}/author-contacts/{contact_id}`

Обновить контакт автора отзыва.

**Request Body:**
```json
{
  "contact_type": "telegram",
  "value": "https://t.me/author",
  "sort_order": 1
}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "contact_type": "telegram",
  "value": "https://t.me/author",
  "sort_order": 1
}
```

### DELETE `/api/v1/admin/reviews/{review_id}/author-contacts/{contact_id}`

Удалить контакт автора отзыва.

**Response:** `204 No Content`

---

## Изменения в существующих response схемах

### CaseResponse (админ)

Добавлено поле:
```json
{
  "contacts": [
    {
      "id": "uuid",
      "contact_type": "website",
      "value": "https://example.com",
      "sort_order": 0
    }
  ]
}
```

### ReviewResponse (админ)

Добавлено поле:
```json
{
  "author_contacts": [
    {
      "id": "uuid",
      "contact_type": "linkedin",
      "value": "https://linkedin.com/in/author",
      "sort_order": 0
    }
  ]
}
```

---

## Затронутые эндпоинты (изменения в response)

| Эндпоинт | Изменение |
|----------|-----------|
| `GET /admin/cases` | Добавлено поле `contacts` в каждый кейс |
| `GET /admin/cases/{id}` | Добавлено поле `contacts` |
| `POST /admin/cases` | В response добавлено поле `contacts` |
| `PATCH /admin/cases/{id}` | В response добавлено поле `contacts` |
| `GET /admin/reviews` | Добавлено поле `author_contacts` в каждый отзыв |
| `GET /admin/reviews/{id}` | Добавлено поле `author_contacts` |
| `POST /admin/reviews` | В response добавлено поле `author_contacts` |
| `PATCH /admin/reviews/{id}` | В response добавлено поле `author_contacts` |

---

## Пример использования

### Добавление контактов при работе с кейсом

1. Создать/обновить кейс через `POST/PATCH /admin/cases/{id}`
2. Добавить контакты клиента через `POST /admin/cases/{id}/contacts`

```bash
# Добавить сайт компании
curl -X POST "/api/v1/admin/cases/123/contacts" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"contact_type": "website", "value": "https://company.com"}'

# Добавить Instagram
curl -X POST "/api/v1/admin/cases/123/contacts" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"contact_type": "instagram", "value": "https://instagram.com/company", "sort_order": 1}'
```

### Добавление контактов автора отзыва

1. Создать/обновить отзыв через `POST/PATCH /admin/reviews/{id}`
2. Добавить контакты автора через `POST /admin/reviews/{id}/author-contacts`

```bash
# Добавить LinkedIn автора
curl -X POST "/api/v1/admin/reviews/456/author-contacts" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"contact_type": "linkedin", "value": "https://linkedin.com/in/ceo"}'
```

---

## Права доступа

- Для управления контактами кейсов требуется permission: `cases:update`
- Для управления контактами отзывов требуется permission: `reviews:update`
