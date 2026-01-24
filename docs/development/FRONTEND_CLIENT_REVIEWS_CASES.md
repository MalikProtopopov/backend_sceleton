# Промпт для клиентского сайта: Отображение отзывов с кейсами

## Обзор изменений на бекенде

Бекенд теперь возвращает:
1. **Объект кейса в отзыве** — если отзыв привязан к кейсу, в ответе приходит объект `case`
2. **Фото автора отзыва** — поле `author_photo_url`
3. **Список отзывов в деталке кейса** — на странице кейса теперь приходит массив `reviews`

---

## Задачи для фронтенда

### 1. Отображать фото автора в отзывах

**Где:** Список отзывов, карточка отзыва, слайдер отзывов

**Структура данных отзыва (публичный API):**
```typescript
interface ReviewPublicResponse {
  id: string;
  rating: number;
  author_name: string;
  author_company?: string;
  author_position?: string;
  author_photo_url?: string;   // ✅ Фото автора
  content: string;
  source?: string;
  review_date?: string;
  case?: CaseMinimalResponse;  // ✅ Информация о кейсе
}

interface CaseMinimalResponse {
  id: string;
  slug: string;
  title: string;
  cover_image_url?: string;
  client_name?: string;
}
```

**Компонент карточки отзыва:**
```tsx
interface ReviewCardProps {
  review: ReviewPublicResponse;
}

export function ReviewCard({ review }: ReviewCardProps) {
  return (
    <div className="review-card">
      {/* Автор с фото */}
      <div className="review-author">
        <div className="author-avatar">
          {review.author_photo_url ? (
            <img
              src={review.author_photo_url}
              alt={review.author_name}
              className="author-photo"
            />
          ) : (
            <div className="author-photo-placeholder">
              {review.author_name.charAt(0).toUpperCase()}
            </div>
          )}
        </div>
        
        <div className="author-info">
          <h4 className="author-name">{review.author_name}</h4>
          {review.author_company && (
            <p className="author-company">{review.author_company}</p>
          )}
          {review.author_position && (
            <p className="author-position">{review.author_position}</p>
          )}
        </div>
      </div>

      {/* Рейтинг */}
      <div className="review-rating">
        {Array.from({ length: 5 }).map((_, i) => (
          <span
            key={i}
            className={`star ${i < review.rating ? 'filled' : ''}`}
          >
            ★
          </span>
        ))}
      </div>

      {/* Текст отзыва */}
      <p className="review-content">{review.content}</p>

      {/* ✅ Привязанный кейс */}
      {review.case && (
        <div className="review-case">
          <p className="case-label">Отзыв о проекте:</p>
          <Link href={`/cases/${review.case.slug}`} className="case-link">
            {review.case.cover_image_url && (
              <img
                src={review.case.cover_image_url}
                alt={review.case.title}
                className="case-thumbnail"
              />
            )}
            <div className="case-info">
              <span className="case-title">{review.case.title}</span>
              {review.case.client_name && (
                <span className="case-client">{review.case.client_name}</span>
              )}
            </div>
          </Link>
        </div>
      )}

      {/* Дата отзыва */}
      {review.review_date && (
        <p className="review-date">
          {new Date(review.review_date).toLocaleDateString('ru-RU')}
        </p>
      )}
    </div>
  );
}
```

**Стили:**
```css
.author-photo {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  object-fit: cover;
}

.author-photo-placeholder {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: bold;
  color: white;
}

.review-case {
  margin-top: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.case-link {
  display: flex;
  gap: 1rem;
  text-decoration: none;
  color: inherit;
  align-items: center;
}

.case-thumbnail {
  width: 80px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
}

.star {
  color: #ddd;
  font-size: 1.2rem;
}

.star.filled {
  color: #ffc107;
}
```

---

### 2. Показывать привязанный кейс в карточке отзыва

Если отзыв привязан к кейсу — показать карточку кейса внизу отзыва со ссылкой на страницу кейса.

**Логика:**
1. Проверить `review.case !== null`
2. Отобразить обложку, название, имя клиента
3. Сделать ссылку на `/cases/{slug}`

---

### 3. Добавить список отзывов на детальной странице кейса

**Где:** `/cases/[slug]` — страница детального просмотра кейса

**API ответ (обновленный):**
```typescript
interface CasePublicResponse {
  id: string;
  slug: string;
  title: string;
  excerpt?: string;
  description?: string;       // HTML контент
  results?: string;           // HTML контент
  cover_image_url?: string;
  client_name?: string;
  project_year?: number;
  project_duration?: string;
  is_featured: boolean;
  published_at?: string;
  meta_title?: string;
  meta_description?: string;
  services: string[];         // Массив UUID сервисов
  reviews: ReviewMinimalResponse[];  // ✅ Список отзывов
}

interface ReviewMinimalResponse {
  id: string;
  rating: number;
  author_name: string;
  author_company?: string;
  author_position?: string;
  author_photo_url?: string;
  content: string;
  review_date?: string;
}
```

**Компонент страницы кейса:**
```tsx
interface CasePageProps {
  params: { slug: string };
}

export default async function CasePage({ params }: CasePageProps) {
  const caseData = await getCaseBySlug(params.slug);

  return (
    <article className="case-page">
      {/* Hero секция */}
      <header className="case-hero">
        {caseData.cover_image_url && (
          <img
            src={caseData.cover_image_url}
            alt={caseData.title}
            className="case-cover"
          />
        )}
        <h1>{caseData.title}</h1>
        {caseData.client_name && (
          <p className="client-name">Клиент: {caseData.client_name}</p>
        )}
        {caseData.project_year && (
          <p className="project-year">Год: {caseData.project_year}</p>
        )}
      </header>

      {/* Описание */}
      {caseData.description && (
        <section className="case-description">
          <div dangerouslySetInnerHTML={{ __html: caseData.description }} />
        </section>
      )}

      {/* Результаты */}
      {caseData.results && (
        <section className="case-results">
          <h2>Результаты</h2>
          <div dangerouslySetInnerHTML={{ __html: caseData.results }} />
        </section>
      )}

      {/* ✅ Секция отзывов */}
      {caseData.reviews && caseData.reviews.length > 0 && (
        <section className="case-reviews">
          <h2>Отзывы о проекте</h2>
          <div className="reviews-grid">
            {caseData.reviews.map((review) => (
              <ReviewMinimalCard key={review.id} review={review} />
            ))}
          </div>
        </section>
      )}
    </article>
  );
}
```

**Компонент отзыва на странице кейса:**
```tsx
function ReviewMinimalCard({ review }: { review: ReviewMinimalResponse }) {
  return (
    <div className="review-minimal-card">
      <div className="review-author">
        {review.author_photo_url ? (
          <img
            src={review.author_photo_url}
            alt={review.author_name}
            className="author-photo"
          />
        ) : (
          <div className="author-photo-placeholder">
            {review.author_name.charAt(0)}
          </div>
        )}
        <div>
          <h4>{review.author_name}</h4>
          {review.author_company && <p>{review.author_company}</p>}
        </div>
      </div>
      
      <div className="review-rating">
        {Array.from({ length: 5 }).map((_, i) => (
          <span key={i} className={i < review.rating ? 'star filled' : 'star'}>
            ★
          </span>
        ))}
      </div>
      
      <p className="review-content">{review.content}</p>
    </div>
  );
}
```

---

### 4. Обновить запросы к API

**Получение списка отзывов (обновленный):**
```typescript
// ✅ Теперь требуется параметр locale
GET /api/v1/public/reviews?tenant_id={uuid}&locale=ru&page=1&page_size=20

// Фильтрация по кейсу
GET /api/v1/public/reviews?tenant_id={uuid}&locale=ru&caseId={uuid}

// Только избранные
GET /api/v1/public/reviews?tenant_id={uuid}&locale=ru&featured=true
```

**Пример API функции:**
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL;
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID;

export async function getReviews(
  locale: string = 'ru',
  options: {
    page?: number;
    pageSize?: number;
    caseId?: string;
    featured?: boolean;
  } = {}
): Promise<ReviewPublicListResponse> {
  const params = new URLSearchParams({
    tenant_id: TENANT_ID,
    locale,
    page: (options.page || 1).toString(),
    page_size: (options.pageSize || 20).toString(),
  });

  if (options.caseId) {
    params.append('caseId', options.caseId);
  }
  if (options.featured !== undefined) {
    params.append('featured', options.featured.toString());
  }

  const response = await fetch(`${API_URL}/public/reviews?${params}`);
  
  if (!response.ok) {
    throw new Error('Failed to fetch reviews');
  }
  
  return response.json();
}
```

**Получение кейса (теперь с отзывами):**
```typescript
export async function getCaseBySlug(
  slug: string,
  locale: string = 'ru'
): Promise<CasePublicResponse> {
  const params = new URLSearchParams({
    tenant_id: TENANT_ID,
    locale,
  });

  const response = await fetch(
    `${API_URL}/public/cases/${slug}?${params}`
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Case not found');
    }
    throw new Error('Failed to fetch case');
  }

  return response.json();
}
```

---

## Чек-лист

- [ ] В карточках отзывов отображается фото автора
- [ ] Если фото нет — показывается placeholder с первой буквой имени
- [ ] Если отзыв привязан к кейсу — показывается информация о кейсе со ссылкой
- [ ] На странице кейса отображается секция "Отзывы о проекте"
- [ ] Отзывы в секции показывают фото, имя, рейтинг, текст
- [ ] API запросы обновлены с параметром `locale`
- [ ] Обработаны случаи отсутствия фото/кейса/отзывов
- [ ] Стили адаптивны для мобильных устройств

---

## Типы данных

```typescript
// Минимальная информация о кейсе (в ответе отзыва)
interface CaseMinimalResponse {
  id: string;
  slug: string;
  title: string;
  cover_image_url?: string;
  client_name?: string;
}

// Публичный отзыв
interface ReviewPublicResponse {
  id: string;
  rating: number;
  author_name: string;
  author_company?: string;
  author_position?: string;
  author_photo_url?: string;
  content: string;
  source?: string;
  review_date?: string;
  case?: CaseMinimalResponse;
}

// Минимальный отзыв (в ответе кейса)
interface ReviewMinimalResponse {
  id: string;
  rating: number;
  author_name: string;
  author_company?: string;
  author_position?: string;
  author_photo_url?: string;
  content: string;
  review_date?: string;
}

// Публичный кейс (с отзывами)
interface CasePublicResponse {
  id: string;
  slug: string;
  title: string;
  excerpt?: string;
  description?: string;
  results?: string;
  cover_image_url?: string;
  client_name?: string;
  project_year?: number;
  project_duration?: string;
  is_featured: boolean;
  published_at?: string;
  meta_title?: string;
  meta_description?: string;
  services: string[];
  reviews: ReviewMinimalResponse[];  // ✅ Список отзывов
}

// Список отзывов
interface ReviewPublicListResponse {
  items: ReviewPublicResponse[];
  total: number;
  page: number;
  page_size: number;
}
```

---

## Примеры использования

### Страница со всеми отзывами

```tsx
// app/reviews/page.tsx
export default async function ReviewsPage() {
  const { items: reviews } = await getReviews('ru', { pageSize: 50 });

  return (
    <div className="reviews-page">
      <h1>Отзывы наших клиентов</h1>
      <div className="reviews-grid">
        {reviews.map((review) => (
          <ReviewCard key={review.id} review={review} />
        ))}
      </div>
    </div>
  );
}
```

### Секция отзывов на главной странице

```tsx
// Только избранные отзывы
const { items: featuredReviews } = await getReviews('ru', { 
  featured: true,
  pageSize: 6 
});

<section className="home-reviews">
  <h2>Что говорят клиенты</h2>
  <div className="reviews-slider">
    {featuredReviews.map((review) => (
      <ReviewCard key={review.id} review={review} />
    ))}
  </div>
</section>
```

### Отзывы конкретного кейса

```tsx
// Если нужно загрузить отзывы отдельно (не из деталки кейса)
const { items: caseReviews } = await getReviews('ru', { 
  caseId: 'uuid-of-case'
});
```
