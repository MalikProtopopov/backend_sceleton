# Промпт для админки: Привязка отзывов к кейсам

## Обзор изменений на бекенде

Бекенд теперь поддерживает:
1. **Привязка отзыва к кейсу** — при создании/редактировании отзыва можно указать `case_id`
2. **Объект кейса в ответе** — в `ReviewResponse` теперь возвращается объект `case` с информацией о кейсе
3. **Фильтрация по slug кейса** — в списке отзывов можно фильтровать по `caseSlug`

---

## Задачи для фронтенда

### 1. Добавить поле выбора кейса при создании/редактировании отзыва

**Где:** Форма создания/редактирования отзыва (`/admin/reviews/new`, `/admin/reviews/{id}`)

**Что добавить:**
- Выпадающий список (Select/Combobox) с поиском для выбора кейса
- Поле опциональное — отзыв можно создать без привязки к кейсу
- Показывать название кейса и его обложку в списке

**API для получения списка кейсов:**
```typescript
GET /api/v1/admin/cases?page=1&page_size=100
```

**Структура запроса на создание/обновление отзыва:**
```typescript
interface ReviewCreateRequest {
  rating: number;              // 1-5
  author_name: string;         // min 2 символа
  author_company?: string;
  author_position?: string;
  content: string;             // min 10 символов
  case_id?: string;            // ✅ UUID кейса или null
  is_featured?: boolean;
  source?: string;
  source_url?: string;
  review_date?: string;        // ISO datetime
  sort_order?: number;
}

interface ReviewUpdateRequest {
  rating?: number;
  author_name?: string;
  author_company?: string;
  author_position?: string;
  content?: string;
  case_id?: string | null;     // ✅ UUID кейса, null для отвязки
  is_featured?: boolean;
  source?: string;
  source_url?: string;
  review_date?: string;
  sort_order?: number;
  status?: 'pending' | 'approved' | 'rejected';
  version: number;             // Обязательно для оптимистичной блокировки
}
```

**Пример компонента выбора кейса:**
```tsx
interface CaseOption {
  id: string;
  title: string;
  coverImageUrl?: string;
  slug: string;
}

function CaseSelector({ 
  value, 
  onChange 
}: { 
  value?: string; 
  onChange: (caseId: string | null) => void;
}) {
  const { data: cases } = useQuery({
    queryKey: ['admin', 'cases', 'list'],
    queryFn: async () => {
      const res = await api.get('/admin/cases', { 
        params: { page: 1, page_size: 100 } 
      });
      return res.data.items;
    },
  });

  return (
    <div className="form-field">
      <label>Привязать к кейсу (опционально)</label>
      <Select
        value={value || ''}
        onChange={(e) => onChange(e.target.value || null)}
        placeholder="Выберите кейс..."
      >
        <option value="">Не привязан</option>
        {cases?.map((c: CaseOption) => (
          <option key={c.id} value={c.id}>
            {c.title}
          </option>
        ))}
      </Select>
    </div>
  );
}
```

---

### 2. Отображать информацию о кейсе в списке отзывов

**Где:** Таблица отзывов (`/admin/reviews`)

**Что добавить:**
- Новая колонка "Кейс" в таблице
- Ссылка на редактирование кейса
- Если кейс не привязан — показать "—" или "Не привязан"

**Структура ответа (обновленная):**
```typescript
interface ReviewResponse {
  id: string;
  rating: number;
  author_name: string;
  author_company?: string;
  author_position?: string;
  author_photo_url?: string;
  content: string;
  status: 'pending' | 'approved' | 'rejected';
  case_id?: string;
  case?: {                     // ✅ Новый объект кейса
    id: string;
    slug: string;
    title: string;
    cover_image_url?: string;
    client_name?: string;
  };
  is_featured: boolean;
  source?: string;
  source_url?: string;
  review_date?: string;
  sort_order: number;
  version: number;
  created_at: string;
  updated_at: string;
  tenant_id: string;
}
```

**Пример колонки в таблице:**
```tsx
{
  header: 'Кейс',
  accessorKey: 'case',
  cell: ({ row }) => {
    const caseData = row.original.case;
    if (!caseData) {
      return <span className="text-muted">—</span>;
    }
    return (
      <Link to={`/admin/cases/${caseData.id}`} className="case-link">
        {caseData.cover_image_url && (
          <img 
            src={caseData.cover_image_url} 
            alt={caseData.title}
            className="case-thumbnail"
          />
        )}
        <span>{caseData.title}</span>
      </Link>
    );
  },
}
```

---

### 3. Добавить фильтрацию отзывов по slug кейса

**Где:** Фильтры в списке отзывов (`/admin/reviews`)

**Что добавить:**
- Поле для ввода slug кейса или выпадающий список кейсов

**API запрос с фильтрацией:**
```typescript
// По UUID кейса
GET /api/v1/admin/reviews?caseId={uuid}

// ✅ Новое: по slug кейса
GET /api/v1/admin/reviews?caseSlug={slug}
```

**Пример использования:**
```typescript
const { data } = useQuery({
  queryKey: ['admin', 'reviews', { caseSlug, status, page }],
  queryFn: async () => {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: '20',
    });
    
    if (caseSlug) params.append('caseSlug', caseSlug);
    if (status) params.append('status', status);
    
    const res = await api.get(`/admin/reviews?${params}`);
    return res.data;
  },
});
```

---

### 4. Показывать фото автора отзыва

**Где:** Список отзывов и форма редактирования

**Загрузка фото:**
```typescript
// Загрузить фото автора
POST /api/v1/admin/reviews/{review_id}/author-photo
Content-Type: multipart/form-data
file: <image file>

// Удалить фото автора
DELETE /api/v1/admin/reviews/{review_id}/author-photo
```

**Пример компонента:**
```tsx
function AuthorPhotoUpload({ 
  reviewId, 
  currentPhotoUrl,
  onUploaded
}: { 
  reviewId: string;
  currentPhotoUrl?: string;
  onUploaded: (url: string) => void;
}) {
  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post(
        `/admin/reviews/${reviewId}/author-photo`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      return res.data;
    },
    onSuccess: (data) => {
      onUploaded(data.author_photo_url);
    },
  });

  return (
    <div className="author-photo-upload">
      {currentPhotoUrl && (
        <img src={currentPhotoUrl} alt="Author" className="preview" />
      )}
      <input
        type="file"
        accept="image/*"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) uploadMutation.mutate(file);
        }}
      />
    </div>
  );
}
```

---

## Чек-лист

- [ ] В форме отзыва добавлено поле выбора кейса (Select с поиском)
- [ ] При создании/обновлении отзыва отправляется `case_id`
- [ ] В таблице отзывов отображается колонка "Кейс" с ссылкой
- [ ] Добавлена фильтрация отзывов по `caseSlug`
- [ ] Отображается фото автора в списке и форме
- [ ] Реализована загрузка/удаление фото автора
- [ ] Обрабатывается случай, когда кейс не привязан (null)

---

## Типы данных

```typescript
// Минимальная информация о кейсе (приходит с отзывом)
interface CaseMinimalResponse {
  id: string;
  slug: string;
  title: string;
  cover_image_url?: string;
  client_name?: string;
}

// Полный ответ отзыва
interface ReviewResponse {
  id: string;
  tenant_id: string;
  rating: number;
  author_name: string;
  author_company?: string;
  author_position?: string;
  author_photo_url?: string;
  content: string;
  case_id?: string;
  case?: CaseMinimalResponse;  // ✅ Объект кейса
  is_featured: boolean;
  source?: string;
  source_url?: string;
  review_date?: string;
  sort_order: number;
  status: 'pending' | 'approved' | 'rejected';
  version: number;
  created_at: string;
  updated_at: string;
  deleted_at?: string;
}

// Список отзывов
interface ReviewListResponse {
  items: ReviewResponse[];
  total: number;
  page: number;
  page_size: number;
}
```
