# Product Inquiry Support — Changelog

> **Date**: 2026-02-24  
> **Migration**: `033_add_product_id_to_inquiries`

---

## Что изменилось

Добавлена привязка заявки (inquiry) к конкретному **продукту** из каталога.

---

## 1. Новое поле `product_id` в заявке

Таблица `inquiries` получила FK-поле `product_id → products.id (SET NULL)`.

---

## 2. Публичный API — отправка заявки на продукт

### POST /api/v1/public/inquiries?tenant_id={uuid}

Добавлено новое опциональное поле `product_id`.

**Пример запроса с карточки товара:**
```json
{
  "form_slug": "quick",
  "name": "Иван Петров",
  "email": "ivan@example.com",
  "phone": "+7 999 123-45-67",
  "message": "Хочу уточнить наличие и стоимость доставки",
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "consent": true,
  "analytics": {
    "source_url": "https://example.com/catalog/widget-pro-2000",
    "page_path": "/catalog/widget-pro-2000",
    "page_title": "Widget Pro 2000"
  }
}
```

**Правило валидации:** `product_id` должен принадлежать тому же тенанту (по `tenant_id` из query). Если передан UUID несуществующего или чужого продукта — поле игнорируется (сохраняется `null`).

---

## 3. Ответ — новые поля `product_id` и `product`

Все эндпоинты заявок (публичный и административные) теперь возвращают `product_id` и вложенный объект `product`.

```json
{
  "id": "inquiry-uuid",
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "product": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "slug": "widget-pro-2000",
    "sku": "WP-2000",
    "name": "Widget Pro 2000"
  },
  ...
}
```

Если продукт не привязан — оба поля `null`.

---

## 4. Административный API — фильтр по продукту

### GET /api/v1/admin/inquiries

Добавлен query-параметр `productId`.

```bash
GET /api/v1/admin/inquiries?productId=3fa85f64-5717-4562-b3fc-2c963f66afa6
Authorization: Bearer {token}
```

Возвращает только заявки, привязанные к указанному продукту.

---

## 5. Сценарии использования на фронтенде

### Клиентский фронт — кнопка «Оставить заявку» на карточке товара

```javascript
// Кнопка на карточке товара: POST /api/v1/public/inquiries
async function submitProductInquiry(product, formData) {
  const response = await fetch(
    `/api/v1/public/inquiries?tenant_id=${TENANT_ID}`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        form_slug: 'quick',
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        message: formData.message || `Заявка на товар: ${product.title}`,
        product_id: product.id,          // <-- ключевое поле
        consent: true,
        analytics: {
          source_url: window.location.href,
          page_path: window.location.pathname,
          page_title: document.title,
        },
      }),
    }
  );
  return response.json();
}
```

### Административная панель — список заявок по продукту

```javascript
// Страница продукта в админке: показать заявки на него
async function fetchProductInquiries(productId, page = 1) {
  const params = new URLSearchParams({
    productId,
    page,
    pageSize: 20,
    status: 'new',           // опционально
  });
  const response = await fetch(
    `/api/v1/admin/inquiries?${params}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return response.json(); // { items: [...], total, page, page_size }
}
```

### Административная панель — отображение продукта в заявке

```javascript
// В карточке заявки
function InquiryCard({ inquiry }) {
  return (
    <div>
      <p>Клиент: {inquiry.name}</p>
      <p>Email: {inquiry.email}</p>
      {inquiry.product && (
        <div>
          <strong>Продукт:</strong>
          <a href={`/admin/catalog/products/${inquiry.product.slug}`}>
            {inquiry.product.name} ({inquiry.product.sku})
          </a>
        </div>
      )}
    </div>
  );
}
```

---

## 6. Объект `product` в ответе (тип)

```typescript
interface InquiryProductBrief {
  id: string;        // UUID
  slug: string;      // URL-friendly slug
  sku: string;       // артикул
  name: string | null; // product.title (заголовок продукта)
}

interface InquiryResponse {
  // ... existing fields ...
  product_id: string | null;       // UUID продукта
  product: InquiryProductBrief | null; // null если продукт не привязан
}
```

---

## 7. Миграция на сервере

```bash
alembic upgrade head
```

Применится миграция `033` — добавит колонку `product_id` и FK в таблицу `inquiries`.
