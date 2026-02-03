# Заявки: короткая и полная форма (quick / mvp-brief)

> Изменения API заявок: типы форм, поля брифа, multipart, фильтр по типу формы.

---

## Обзор

Поддержаны два типа форм заявок:

| form_slug   | Описание           | Обязательные поля              |
|-------------|--------------------|--------------------------------|
| `quick`     | Короткая заявка    | name, email, message, consent  |
| `mvp-brief` | Полный бриф (MVP)  | name, email, idea, consent      |

Поля брифа (idea, market, audience, budget и т.д.) сохраняются в `custom_fields`. Для `mvp-brief` поле `idea` также записывается в `message` для отображения в списке.

---

## Изменения в API

### POST /api/v1/public/inquiries (application/json)

**Новые/уточнённые поля в теле запроса:**

| Поле        | Тип        | Обязательно       | Описание |
|-------------|------------|-------------------|----------|
| `form_slug` | string     | для typed forms   | `quick` или `mvp-brief` |
| `telegram`  | string     | нет               | @username или t.me |
| `consent`   | boolean    | рекомендуется     | Согласие на обработку ПД |
| `idea`      | string     | при form_slug=mvp-brief | Основная идея (10–2000 символов) |
| `market`    | string     | нет               | b2b_saas, b2c_mobile, ai_service, marketplace, internal, other |
| `audience`  | string     | нет               | До 1000 символов |
| `audienceSize` | string  | нет               | small, medium, large, unknown |
| `aiRequired`| string     | нет               | no, nlp, llm, cv, unknown |
| `appTypes`  | string[]   | нет               | website, webapp, mobile, desktop, telegram, api |
| `integrations` | string  | нет               | До 500 символов |
| `budget`    | string     | нет               | 5-15k, 15-40k, 40-100k, 100k+, undefined |
| `urgency`   | string     | нет               | 30days, fast, flexible |
| `source`    | string     | нет               | friend, google, linkedin, investor, portfolio, other |

Валидация:
- При `form_slug=quick` обязательно поле `message`.
- При `form_slug=mvp-brief` обязательно поле `idea`.

---

### POST /api/v1/public/inquiries/upload (multipart/form-data)

**Новый endpoint** для отправки заявки через FormData (поддержка файлов в перспективе).

- **Content-Type:** `multipart/form-data`
- **Query:** `tenant_id` (UUID)
- **Form fields:** те же поля, что и в JSON; все значения — строки.
  - `appTypes`: несколько полей с одним именем (`appTypes=website`, `appTypes=webapp`) или одно поле со списком.
  - `analytics`: JSON-строка с объектом analytics.
  - `consent`: `"true"` / `"false"`.
- **Files:** опционально поле `files` (обработка файлов — в разработке).

Ответ: 201, тело как у POST /public/inquiries.

---

### GET /api/v1/admin/inquiries

**Новый query-параметр:**

| Параметр   | Тип    | Описание |
|------------|--------|----------|
| `formSlug` | string | Фильтр по slug формы: `quick`, `mvp-brief` |

---

### Ответы admin (GET /admin/inquiries, GET /admin/inquiries/{id})

**В объекте заявки добавлено поле:**

| Поле       | Тип    | Описание |
|------------|--------|----------|
| `form_slug` | string \| null | Slug привязанной формы (`quick`, `mvp-brief` или другой). |

---

## Хранение на бэкенде

- Таблица `inquiries`: без новых колонок; используется существующее поле `custom_fields` (JSONB).
- Таблица `inquiry_forms`: в сиде создаются формы с `slug = "quick"` и `slug = "mvp-brief"`.
- При создании заявки по `form_slug` ищется форма по slug, в заявку записывается `form_id`; поля брифа и доп. поля (telegram, consent и т.д.) попадают в `custom_fields`.

---

## Чек-лист для фронта

- [ ] Короткая форма: отправлять `form_slug=quick`, name, email, message, consent; опционально phone, telegram.
- [ ] Полный бриф: отправлять `form_slug=mvp-brief`, name, email, idea, consent и остальные поля брифа.
- [ ] Для отправки с файлами использовать POST /public/inquiries/upload (multipart/form-data).
- [ ] В админке: фильтр по типу формы (formSlug); в карточке заявки показывать `form_slug` и секции по данным из `custom_fields` для mvp-brief.
