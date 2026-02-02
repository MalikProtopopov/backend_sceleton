# Контакты для кейсов и отзывов — Изменения в Public API

Этот документ описывает изменения в публичных API эндпоинтах для отображения контактов клиентов кейсов и авторов отзывов на клиентском фронтенде.

## Обзор изменений

Во все публичные эндпоинты, где выводятся кейсы и отзывы, добавлены новые поля:
- **contacts** — для кейсов (контакты клиента/компании)
- **author_contacts** — для отзывов (контакты автора отзыва)

## Типы контактов

Возможные значения `contact_type`:
```
website, instagram, telegram, linkedin, facebook, twitter, youtube, tiktok, email, phone, whatsapp, viber, other
```

Используйте этот список для отображения соответствующих иконок на фронтенде.

---

## Затронутые публичные эндпоинты

### 1. GET `/api/v1/public/cases`

Список опубликованных кейсов.

**Добавлено поле `contacts` в каждый кейс:**
```json
{
  "items": [
    {
      "id": "uuid",
      "slug": "project-name",
      "title": "Название проекта",
      "excerpt": "Описание...",
      "cover_image_url": "/media/...",
      "client_name": "Компания",
      "contacts": [
        {
          "id": "uuid",
          "contact_type": "website",
          "value": "https://example.com",
          "sort_order": 0
        },
        {
          "id": "uuid",
          "contact_type": "instagram",
          "value": "https://instagram.com/company",
          "sort_order": 1
        }
      ],
      "reviews": []
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

### 2. GET `/api/v1/public/cases/{slug}`

Детальная страница кейса.

**Добавлено поле `contacts`:**
```json
{
  "id": "uuid",
  "slug": "project-name",
  "title": "Название проекта",
  "description": "Полное описание...",
  "client_name": "Компания",
  "contacts": [
    {
      "id": "uuid",
      "contact_type": "website",
      "value": "https://example.com",
      "sort_order": 0
    }
  ],
  "reviews": [
    {
      "id": "uuid",
      "rating": 5,
      "author_name": "Иван Иванов",
      "author_company": "Компания",
      "content": "Отличная работа!",
      "author_contacts": [
        {
          "id": "uuid",
          "contact_type": "linkedin",
          "value": "https://linkedin.com/in/author",
          "sort_order": 0
        }
      ]
    }
  ]
}
```

### 3. GET `/api/v1/public/reviews`

Список одобренных отзывов.

**Добавлено поле `author_contacts` в каждый отзыв:**
```json
{
  "items": [
    {
      "id": "uuid",
      "rating": 5,
      "author_name": "Иван Иванов",
      "author_company": "Компания",
      "author_position": "CEO",
      "author_photo_url": "/media/...",
      "content": "Отличная работа!",
      "review_date": "2026-01-15T10:00:00Z",
      "author_contacts": [
        {
          "id": "uuid",
          "contact_type": "linkedin",
          "value": "https://linkedin.com/in/ceo",
          "sort_order": 0
        },
        {
          "id": "uuid",
          "contact_type": "telegram",
          "value": "https://t.me/ceo",
          "sort_order": 1
        }
      ],
      "case": {
        "id": "uuid",
        "slug": "project-name",
        "title": "Название проекта",
        "contacts": [...]
      }
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

### 4. GET `/api/v1/public/services/{slug}`

Детальная страница услуги (содержит кейсы и отзывы).

**Добавлено поле `contacts` в кейсы и `author_contacts` в отзывы:**
```json
{
  "id": "uuid",
  "slug": "web-development",
  "title": "Веб-разработка",
  "cases": [
    {
      "id": "uuid",
      "slug": "project-name",
      "title": "Название проекта",
      "contacts": [
        {
          "id": "uuid",
          "contact_type": "website",
          "value": "https://example.com",
          "sort_order": 0
        }
      ]
    }
  ],
  "reviews": [
    {
      "id": "uuid",
      "rating": 5,
      "author_name": "Иван Иванов",
      "content": "Отличная работа!",
      "author_contacts": [
        {
          "id": "uuid",
          "contact_type": "linkedin",
          "value": "https://linkedin.com/in/author",
          "sort_order": 0
        }
      ]
    }
  ]
}
```

---

## Структура объектов контактов

### CaseContact (контакты кейса)

```typescript
interface CaseContact {
  id: string;           // UUID контакта
  contact_type: string; // Тип: website, instagram, telegram, etc.
  value: string;        // URL, телефон, email и т.д.
  sort_order: number;   // Порядок отображения
}
```

### ReviewAuthorContact (контакты автора отзыва)

```typescript
interface ReviewAuthorContact {
  id: string;           // UUID контакта
  contact_type: string; // Тип: website, instagram, telegram, etc.
  value: string;        // URL, телефон, email и т.д.
  sort_order: number;   // Порядок отображения
}
```

---

## Пример использования на фронтенде

### Отображение контактов кейса

```tsx
function CaseContacts({ contacts }: { contacts: CaseContact[] }) {
  const sortedContacts = [...contacts].sort((a, b) => a.sort_order - b.sort_order);
  
  const getIcon = (type: string) => {
    const icons: Record<string, string> = {
      website: '🌐',
      instagram: '📸',
      telegram: '✈️',
      linkedin: '💼',
      facebook: 'fb',
      twitter: '𝕏',
      youtube: '▶️',
      email: '✉️',
      phone: '📞',
      whatsapp: '💬',
    };
    return icons[type] || '🔗';
  };
  
  return (
    <div className="contacts">
      {sortedContacts.map(contact => (
        <a 
          key={contact.id} 
          href={contact.value} 
          target="_blank" 
          rel="noopener noreferrer"
        >
          {getIcon(contact.contact_type)}
        </a>
      ))}
    </div>
  );
}
```

### Отображение контактов автора отзыва

```tsx
function ReviewAuthor({ review }: { review: Review }) {
  return (
    <div className="review-author">
      <img src={review.author_photo_url} alt={review.author_name} />
      <div>
        <strong>{review.author_name}</strong>
        <span>{review.author_position}</span>
        {review.author_company && <span>{review.author_company}</span>}
      </div>
      
      {review.author_contacts?.length > 0 && (
        <div className="author-socials">
          {review.author_contacts
            .sort((a, b) => a.sort_order - b.sort_order)
            .map(contact => (
              <a 
                key={contact.id}
                href={contact.value}
                target="_blank"
                rel="noopener noreferrer"
                title={contact.contact_type}
              >
                <SocialIcon type={contact.contact_type} />
              </a>
            ))}
        </div>
      )}
    </div>
  );
}
```

---

## Важные замечания

1. **Контакты всегда возвращаются как массив** — если контактов нет, будет пустой массив `[]`

2. **Сортировка** — контакты возвращаются в порядке `sort_order`, но рекомендуется дополнительно сортировать на фронте

3. **Валидация value** — значение `value` может содержать:
   - URL (для website, соцсетей)
   - Email адрес
   - Телефон в любом формате
   - Username (например, для telegram)

4. **Обратная совместимость** — если приложение не обрабатывает новые поля `contacts`/`author_contacts`, это не вызовет ошибок (поля просто игнорируются)

---

## TypeScript типы

```typescript
// Типы для публичного API
interface CaseContact {
  id: string;
  contact_type: ContactType;
  value: string;
  sort_order: number;
}

interface ReviewAuthorContact {
  id: string;
  contact_type: ContactType;
  value: string;
  sort_order: number;
}

type ContactType = 
  | 'website' 
  | 'instagram' 
  | 'telegram' 
  | 'linkedin' 
  | 'facebook' 
  | 'twitter' 
  | 'youtube' 
  | 'tiktok' 
  | 'email' 
  | 'phone' 
  | 'whatsapp' 
  | 'viber' 
  | 'other';

// Обновленные типы для кейса
interface CasePublic {
  id: string;
  slug: string;
  title: string;
  // ... другие поля
  contacts: CaseContact[];  // НОВОЕ
  reviews: ReviewMinimal[];
}

// Обновленные типы для отзыва
interface ReviewPublic {
  id: string;
  rating: number;
  author_name: string;
  // ... другие поля
  author_contacts: ReviewAuthorContact[];  // НОВОЕ
  case: CaseMinimal | null;
}
```
