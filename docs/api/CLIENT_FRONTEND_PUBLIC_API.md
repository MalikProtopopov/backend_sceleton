# Client Frontend Public API Reference

> Полный справочник публичных API-эндпоинтов для клиентского фронтенда

---

## Настройка

### Переменные окружения

```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_TENANT_ID=63d068f7-7a47-46fe-aeb0-c82588e995a4
NEXT_PUBLIC_DEFAULT_LOCALE=ru
```

### API клиент

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID;
const DEFAULT_LOCALE = process.env.NEXT_PUBLIC_DEFAULT_LOCALE || 'ru';

export const apiUrl = (path: string) => `${API_BASE}${API_PREFIX}${path}`;

// Базовый запрос с tenant_id
export async function fetchPublic<T>(
  endpoint: string,
  params: Record<string, string> = {}
): Promise<T> {
  const searchParams = new URLSearchParams({
    tenant_id: TENANT_ID!,
    locale: DEFAULT_LOCALE,
    ...params,
  });
  
  const response = await fetch(`${apiUrl(endpoint)}?${searchParams}`);
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return response.json();
}
```

---

## Эндпоинты

### 1. Информация о сайте (Tenant)

**Получить информацию о сайте (брендинг, лого)**

```typescript
// GET /api/v1/public/tenants/{tenant_id}
interface TenantPublic {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  primary_color: string | null;
}

// Использование
const tenant = await fetch(
  `${API_BASE}/api/v1/public/tenants/${TENANT_ID}`
).then(r => r.json());

// Примеры использования:
// - Лого в шапке: tenant.logo_url
// - Название в footer: tenant.name
// - Цвет бренда в CSS: tenant.primary_color
```

**Пример ответа:**
```json
{
  "id": "63d068f7-7a47-46fe-aeb0-c82588e995a4",
  "name": "Юридическая компания Медианн",
  "slug": "mediann",
  "logo_url": "http://localhost:9000/cms-assets/tenants/63d068f7.png",
  "primary_color": "#1E40AF"
}
```

---

### 2. Услуги (Services)

**Список услуг**

```typescript
// GET /api/v1/public/services?tenant_id={uuid}&locale=ru
interface ServicePublic {
  id: string;
  slug: string;
  name: string;
  short_description: string | null;
  description: string | null;
  icon_url: string | null;
  image_url: string | null;
  price_from: number | null;
  price_to: number | null;
  price_unit: string | null;
  sort_order: number;
}

const services = await fetchPublic<ServicePublic[]>('/public/services');
```

**Услуга по slug**

```typescript
// GET /api/v1/public/services/{slug}?tenant_id={uuid}&locale=ru
const service = await fetchPublic<ServicePublic>(`/public/services/${slug}`);
```

---

### 3. Команда (Employees)

**Список сотрудников**

```typescript
// GET /api/v1/public/employees?tenant_id={uuid}&locale=ru
interface EmployeePublic {
  id: string;
  slug: string;
  first_name: string;
  last_name: string;
  position: string | null;
  bio: string | null;
  photo_url: string | null;
  email: string | null;
  phone: string | null;
  linkedin_url: string | null;
  telegram_url: string | null;
  sort_order: number;
}

const employees = await fetchPublic<EmployeePublic[]>('/public/employees');
```

**Сотрудник по slug**

```typescript
// GET /api/v1/public/employees/{slug}?tenant_id={uuid}&locale=ru
const employee = await fetchPublic<EmployeePublic>(`/public/employees/${slug}`);
```

---

### 4. Статьи (Articles)

**Список статей**

```typescript
// GET /api/v1/public/articles?tenant_id={uuid}&locale=ru&page=1&page_size=20
interface ArticlePublic {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  content: string | null;
  cover_image_url: string | null;
  author_name: string | null;
  published_at: string | null;
  topics: { id: string; slug: string; name: string }[];
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

const articles = await fetchPublic<PaginatedResponse<ArticlePublic>>(
  '/public/articles',
  { page: '1', page_size: '10' }
);

// Фильтрация по теме
const articlesByTopic = await fetchPublic<PaginatedResponse<ArticlePublic>>(
  '/public/articles',
  { topic: 'novosti' }
);
```

**Статья по slug**

```typescript
// GET /api/v1/public/articles/{slug}?tenant_id={uuid}&locale=ru
const article = await fetchPublic<ArticlePublic>(`/public/articles/${slug}`);
```

---

### 5. Темы статей (Topics)

**Список тем**

```typescript
// GET /api/v1/public/topics?tenant_id={uuid}&locale=ru
interface TopicPublic {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  sort_order: number;
}

const topics = await fetchPublic<TopicPublic[]>('/public/topics');
```

**Тема по slug**

```typescript
// GET /api/v1/public/topics/{slug}?tenant_id={uuid}&locale=ru
const topic = await fetchPublic<TopicPublic>(`/public/topics/${slug}`);
```

---

### 6. FAQ

**Список FAQ**

```typescript
// GET /api/v1/public/faq?tenant_id={uuid}&locale=ru
interface FAQPublic {
  id: string;
  question: string;
  answer: string;
  category: string | null;
  sort_order: number;
}

const faqs = await fetchPublic<FAQPublic[]>('/public/faq');

// Фильтрация по категории
const faqsByCategory = await fetchPublic<FAQPublic[]>(
  '/public/faq',
  { category: 'general' }
);
```

---

### 7. Кейсы (Cases / Portfolio)

**Список кейсов**

```typescript
// GET /api/v1/public/cases?tenant_id={uuid}&locale=ru&page=1&page_size=20
interface CasePublic {
  id: string;
  slug: string;
  title: string;
  short_description: string | null;
  description: string | null;
  client_name: string | null;
  client_logo_url: string | null;
  cover_image_url: string | null;
  result_summary: string | null;
  is_featured: boolean;
  published_at: string | null;
  services: { id: string; slug: string; name: string }[];
}

const cases = await fetchPublic<PaginatedResponse<CasePublic>>(
  '/public/cases',
  { page: '1', page_size: '10' }
);

// Только featured кейсы
const featuredCases = await fetchPublic<PaginatedResponse<CasePublic>>(
  '/public/cases',
  { featured: 'true' }
);
```

**Кейс по slug**

```typescript
// GET /api/v1/public/cases/{slug}?tenant_id={uuid}&locale=ru
const caseItem = await fetchPublic<CasePublic>(`/public/cases/${slug}`);
```

---

### 8. Отзывы (Reviews)

**Список отзывов**

```typescript
// GET /api/v1/public/reviews?tenant_id={uuid}&locale=ru&page=1&page_size=20
interface ReviewPublic {
  id: string;
  author_name: string;
  author_position: string | null;
  author_company: string | null;
  author_photo_url: string | null;
  content: string;
  rating: number | null;
  is_featured: boolean;
  published_at: string | null;
  case_id: string | null;
}

const reviews = await fetchPublic<PaginatedResponse<ReviewPublic>>(
  '/public/reviews',
  { page: '1', page_size: '10' }
);

// Только featured отзывы
const featuredReviews = await fetchPublic<PaginatedResponse<ReviewPublic>>(
  '/public/reviews',
  { featured: 'true' }
);

// Отзывы по конкретному кейсу
const caseReviews = await fetchPublic<PaginatedResponse<ReviewPublic>>(
  '/public/reviews',
  { case_id: 'uuid-here' }
);
```

---

### 9. Документы (Documents)

**Список документов**

```typescript
// GET /api/v1/public/documents?tenant_id={uuid}&locale=ru&page=1&page_size=20
interface DocumentPublic {
  id: string;
  slug: string;
  title: string;
  description: string | null;
  file_url: string;
  file_type: string;
  file_size: number;
  document_date: string | null;
}

const documents = await fetchPublic<PaginatedResponse<DocumentPublic>>(
  '/public/documents',
  { page: '1', page_size: '10' }
);
```

**Документ по slug**

```typescript
// GET /api/v1/public/documents/{slug}?tenant_id={uuid}&locale=ru
const document = await fetchPublic<DocumentPublic>(`/public/documents/${slug}`);
```

---

### 10. Контакты

**Получить контакты**

```typescript
// GET /api/v1/public/contacts?tenant_id={uuid}
interface Address {
  id: string;
  name: string | null;
  address: string;
  city: string | null;
  postal_code: string | null;
  latitude: number | null;
  longitude: number | null;
  is_primary: boolean;
}

interface Contact {
  id: string;
  type: string; // 'phone', 'email', 'whatsapp', etc.
  value: string;
  label: string | null;
  is_primary: boolean;
}

interface ContactsResponse {
  addresses: Address[];
  contacts: Contact[];
}

const contacts = await fetch(
  `${apiUrl('/public/contacts')}?tenant_id=${TENANT_ID}`
).then(r => r.json()) as ContactsResponse;
```

---

### 11. Преимущества (Advantages)

**Список преимуществ**

```typescript
// GET /api/v1/public/advantages?tenant_id={uuid}&locale=ru
interface AdvantagePublic {
  id: string;
  title: string;
  description: string | null;
  icon_url: string | null;
  sort_order: number;
}

const advantages = await fetchPublic<AdvantagePublic[]>('/public/advantages');
```

---

### 12. Заявки (Inquiries)

**Отправить заявку**

```typescript
// POST /api/v1/public/inquiries?tenant_id={uuid}
interface InquiryCreate {
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  message?: string;
  service_id?: string;
  // UTM параметры
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  // Информация о странице
  source_url?: string;
  page_path?: string;
  page_title?: string;
  referrer_url?: string;
  // Устройство
  device_type?: 'desktop' | 'mobile' | 'tablet';
  user_agent?: string;
}

const submitInquiry = async (data: InquiryCreate) => {
  const response = await fetch(
    `${apiUrl('/public/inquiries')}?tenant_id=${TENANT_ID}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    }
  );
  
  if (!response.ok) {
    throw new Error('Failed to submit inquiry');
  }
  
  return response.json();
};

// Пример использования с UTM
submitInquiry({
  name: 'Иван Иванов',
  phone: '+7 (999) 123-45-67',
  message: 'Хочу консультацию',
  utm_source: new URLSearchParams(window.location.search).get('utm_source') || undefined,
  utm_medium: new URLSearchParams(window.location.search).get('utm_medium') || undefined,
  utm_campaign: new URLSearchParams(window.location.search).get('utm_campaign') || undefined,
  source_url: window.location.href,
  page_path: window.location.pathname,
  page_title: document.title,
  referrer_url: document.referrer || undefined,
  device_type: /Mobi/i.test(navigator.userAgent) ? 'mobile' : 'desktop',
  user_agent: navigator.userAgent,
});
```

**Rate Limit:** 3 запроса в 60 секунд с одного IP

---

### 13. SEO

**Мета-теги для страницы**

```typescript
// GET /api/v1/public/seo/meta?tenant_id={uuid}&path=/about&locale=ru
interface SEOMeta {
  path: string;
  locale: string;
  title: string | null;
  meta_title: string | null;
  meta_description: string | null;
  meta_keywords: string | null;
  og_image: string | null;
  canonical_url: string | null;
  robots_index: boolean;
  robots_follow: boolean;
}

const getSEOMeta = async (path: string, locale: string = 'ru') => {
  const params = new URLSearchParams({
    tenant_id: TENANT_ID!,
    path,
    locale,
  });
  
  const response = await fetch(`${apiUrl('/public/seo/meta')}?${params}`);
  if (!response.ok) return null;
  return response.json() as Promise<SEOMeta>;
};

// Использование в Next.js
export async function generateMetadata({ params }) {
  const seo = await getSEOMeta(`/services/${params.slug}`);
  
  return {
    title: seo?.meta_title || seo?.title || 'Default Title',
    description: seo?.meta_description,
    keywords: seo?.meta_keywords,
    openGraph: {
      images: seo?.og_image ? [seo.og_image] : [],
    },
    robots: {
      index: seo?.robots_index ?? true,
      follow: seo?.robots_follow ?? true,
    },
  };
}
```

**Sitemap**

```typescript
// GET /api/v1/public/sitemap.xml?tenant_id={uuid}
// Возвращает XML sitemap

// В next.config.js для редиректа:
async rewrites() {
  return [
    {
      source: '/sitemap.xml',
      destination: `${API_BASE}/api/v1/public/sitemap.xml?tenant_id=${TENANT_ID}`,
    },
  ];
}
```

**Robots.txt**

```typescript
// GET /api/v1/public/robots.txt?tenant_id={uuid}
// Возвращает plain text robots.txt
```

---

## Маппинг страниц на API

| Страница | Эндпоинты |
|----------|-----------|
| **Главная** | `/public/tenants/{id}`, `/public/services`, `/public/cases?featured=true`, `/public/reviews?featured=true`, `/public/advantages` |
| **Услуги (список)** | `/public/services` |
| **Услуга (детальная)** | `/public/services/{slug}`, `/public/cases?service_id={id}`, `/public/reviews` |
| **О компании** | `/public/tenants/{id}`, `/public/employees`, `/public/advantages` |
| **Команда** | `/public/employees` |
| **Сотрудник** | `/public/employees/{slug}` |
| **Блог (список)** | `/public/articles`, `/public/topics` |
| **Статья** | `/public/articles/{slug}` |
| **Кейсы (список)** | `/public/cases` |
| **Кейс** | `/public/cases/{slug}`, `/public/reviews?case_id={id}` |
| **Отзывы** | `/public/reviews` |
| **FAQ** | `/public/faq` |
| **Документы** | `/public/documents` |
| **Контакты** | `/public/contacts`, `/public/tenants/{id}` |

---

## Работа с медиа-файлами

Все URL изображений возвращаются как полные URL (с хостом) или относительные пути.

```typescript
// Получение полного URL изображения
const getImageUrl = (url: string | null): string | null => {
  if (!url) return null;
  if (url.startsWith('http')) return url;
  return `${API_BASE}${url}`;
};

// Использование
<img src={getImageUrl(tenant.logo_url)} alt={tenant.name} />
<img src={getImageUrl(employee.photo_url)} alt={employee.first_name} />
```

---

## Обработка ошибок

```typescript
// Типичные HTTP статусы
// 200 - OK
// 400 - Bad Request (невалидные параметры)
// 404 - Not Found (ресурс не найден)
// 429 - Too Many Requests (rate limit, для inquiries)
// 500 - Internal Server Error

// Пример обработки
try {
  const data = await fetchPublic('/public/articles');
} catch (error) {
  if (error.message.includes('404')) {
    // Показать 404 страницу
  } else if (error.message.includes('429')) {
    // Показать сообщение "Подождите..."
  } else {
    // Общая ошибка
  }
}
```

---

## Кэширование (Next.js)

```typescript
// Рекомендуемые настройки кэширования

// Статичные данные (редко меняются)
const tenant = await fetch(url, { 
  next: { revalidate: 3600 } // 1 час
});

// Контент (статьи, кейсы)
const articles = await fetch(url, { 
  next: { revalidate: 300 } // 5 минут
});

// Динамичные данные (отзывы, заявки)
const reviews = await fetch(url, { 
  next: { revalidate: 60 } // 1 минута
});
```

---

## Примеры компонентов

### Шапка сайта

```tsx
// components/Header.tsx
async function Header() {
  const tenant = await fetch(
    `${API_BASE}/api/v1/public/tenants/${TENANT_ID}`
  ).then(r => r.json());

  return (
    <header style={{ '--primary-color': tenant.primary_color }}>
      {tenant.logo_url && (
        <img src={tenant.logo_url} alt={tenant.name} className="logo" />
      )}
      <nav>...</nav>
    </header>
  );
}
```

### Список услуг

```tsx
// app/services/page.tsx
async function ServicesPage() {
  const services = await fetchPublic<ServicePublic[]>('/public/services');

  return (
    <div className="services-grid">
      {services.map(service => (
        <Link key={service.id} href={`/services/${service.slug}`}>
          <div className="service-card">
            {service.icon_url && <img src={service.icon_url} alt="" />}
            <h3>{service.name}</h3>
            <p>{service.short_description}</p>
          </div>
        </Link>
      ))}
    </div>
  );
}
```

### Форма заявки

```tsx
// components/InquiryForm.tsx
'use client';

function InquiryForm({ serviceId }: { serviceId?: string }) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);

    const formData = new FormData(e.currentTarget);
    
    try {
      await fetch(`${API_BASE}/api/v1/public/inquiries?tenant_id=${TENANT_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: formData.get('name'),
          phone: formData.get('phone'),
          email: formData.get('email'),
          message: formData.get('message'),
          service_id: serviceId,
          source_url: window.location.href,
          utm_source: new URLSearchParams(window.location.search).get('utm_source'),
        }),
      });
      setSuccess(true);
    } catch (error) {
      alert('Ошибка отправки. Попробуйте позже.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return <div>Спасибо! Мы свяжемся с вами.</div>;
  }

  return (
    <form onSubmit={handleSubmit}>
      <input name="name" placeholder="Имя" required />
      <input name="phone" placeholder="Телефон" required />
      <input name="email" type="email" placeholder="Email" />
      <textarea name="message" placeholder="Сообщение" />
      <button type="submit" disabled={loading}>
        {loading ? 'Отправка...' : 'Отправить'}
      </button>
    </form>
  );
}
```

---

## Чеклист интеграции

- [ ] Настроить переменные окружения (`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_TENANT_ID`)
- [ ] Создать API клиент (`lib/api.ts`)
- [ ] Подключить tenant info в шапку/футер
- [ ] Реализовать страницы: услуги, команда, статьи, кейсы, отзывы, FAQ, контакты
- [ ] Добавить форму заявки с UTM трекингом
- [ ] Настроить SEO мета-теги для всех страниц
- [ ] Подключить sitemap.xml и robots.txt
- [ ] Настроить кэширование
- [ ] Обработать 404 и ошибки
