# API: Связка продукта с параметрами и значениями

> **Назначение**: Документация для фронтенда по тому, как на бэкенде задаётся связь «продукт — параметр — значение» (например: продукт X, параметр «Цвет», значение «Жёлтый»).  
> **Контекст**: Параметры и их значения хранятся в справочниках; у продукта хранятся только привязки к ним (характеристики).  
> **Версия бэкенда**: 2026-02-26

---

## Содержание

1. [Модель данных](#1-модель-данных)
2. [Эндпоинты — сводка](#2-эндпоинты--сводка)
3. [Получить текущие характеристики продукта](#3-получить-текущие-характеристики-продукта)
4. [Добавить или изменить одно значение (например, только «Жёлтый»)](#4-добавить-или-изменить-одно-значение)
5. [Задать ровно нужный набор значений (только жёлтый, без красного)](#5-задать-ровно-нужный-набор-значений)
6. [Удалить все значения параметра у продукта](#6-удалить-все-значения-параметра)
7. [Типы параметров и поля запроса](#7-типы-параметров-и-поля-запроса)
8. [Типы и примеры (TypeScript)](#8-типы-и-примеры-typescript)
9. [Типичные сценарии UI](#9-типичные-сценарии-ui)

---

## 1. Модель данных

- **Parameter** — справочник параметров (Цвет, Вес, Материал и т.д.). Имеет `value_type`: `enum`, `number`, `string`, `bool`, `range`.
- **ParameterValue** — справочник значений только для параметров типа `enum` (Красный, Жёлтый, Синий для параметра «Цвет»).
- **ProductCharacteristic** — связка «продукт + параметр + значение»:
  - для **enum**: одна запись = один выбранный вариант (например, «Цвет = Жёлтый»); у одного продукта по одному параметру может быть **несколько записей** (продукт «красный и жёлтый»).
  - для **number/string/bool/range**: одна запись на параметр (одно число, одна строка, один флаг).

Чтобы «у продукта цвет = только жёлтый» (без красного), у продукта по параметру «Цвет» должны быть ровно те характеристики, которые ссылаются на значение «Жёлтый». Красный нужно «убрать», задав нужный набор заново (см. разделы 5 и 6).

---

## 2. Эндпоинты — сводка

| Метод | Путь | Назначение |
|-------|------|------------|
| **GET** | `/api/v1/admin/products/{product_id}/characteristics` | Список всех характеристик продукта |
| **POST** | `/api/v1/admin/products/{product_id}/characteristics` | Добавить/обновить **одно** значение по параметру (для enum — добавить один вариант, не снимая другие) |
| **PUT** | `/api/v1/admin/products/{product_id}/characteristics/bulk` | **Задать заново** набор характеристик: по каждому параметру старые значения заменяются на переданные |
| **DELETE** | `/api/v1/admin/products/{product_id}/characteristics/{parameter_id}` | Удалить **все** значения данного параметра у продукта |

Во всех запросах нужны заголовки: `Authorization: Bearer <token>`, `X-Tenant-ID: <tenant_id>`, `Content-Type: application/json` (кроме GET).

---

## 3. Получить текущие характеристики продукта

**Запрос:**

```http
GET /api/v1/admin/products/{product_id}/characteristics
```

**Ответ:** массив характеристик с встроенной информацией о параметре и значении (имена, slug, тип, UOM). Фронту не нужно отдельно запрашивать справочник параметров для отображения — всё приходит в одном запросе.

```json
[
  {
    "id": "uuid-1",
    "product_id": "product-uuid",
    "parameter_id": "color-param-uuid",
    "parameter_value_id": "yellow-value-uuid",
    "value_text": null,
    "value_number": null,
    "value_bool": null,
    "uom_id": null,
    "source_type": "manual",
    "is_locked": false,
    "created_at": "2026-02-26T12:00:00Z",
    "updated_at": "2026-02-26T12:00:00Z",
    "parameter": {
      "id": "color-param-uuid",
      "name": "Цвет",
      "slug": "tsvet",
      "value_type": "enum",
      "is_filterable": true,
      "uom": null
    },
    "parameter_value": {
      "id": "yellow-value-uuid",
      "label": "Жёлтый",
      "slug": "zhjoltyj"
    }
  },
  {
    "id": "uuid-2",
    "product_id": "product-uuid",
    "parameter_id": "color-param-uuid",
    "parameter_value_id": "red-value-uuid",
    "value_text": null,
    "value_number": null,
    "value_bool": null,
    "uom_id": null,
    "source_type": "manual",
    "is_locked": false,
    "created_at": "2026-02-26T12:00:00Z",
    "updated_at": "2026-02-26T12:00:00Z",
    "parameter": {
      "id": "color-param-uuid",
      "name": "Цвет",
      "slug": "tsvet",
      "value_type": "enum",
      "is_filterable": true,
      "uom": null
    },
    "parameter_value": {
      "id": "red-value-uuid",
      "label": "Красный",
      "slug": "krasnyj"
    }
  },
  {
    "id": "uuid-3",
    "product_id": "product-uuid",
    "parameter_id": "weight-param-uuid",
    "parameter_value_id": null,
    "value_text": null,
    "value_number": "2.5",
    "value_bool": null,
    "uom_id": "kg-uom-uuid",
    "source_type": "manual",
    "is_locked": false,
    "created_at": "2026-02-26T12:00:00Z",
    "updated_at": "2026-02-26T12:00:00Z",
    "parameter": {
      "id": "weight-param-uuid",
      "name": "Вес",
      "slug": "ves",
      "value_type": "number",
      "is_filterable": true,
      "uom": { "id": "kg-uom-uuid", "code": "kg", "symbol": "кг" }
    },
    "parameter_value": null
  }
]
```

**Ключевые поля в ответе:**
- `parameter.name` — человекочитаемое название параметра
- `parameter.value_type` — тип (`enum` / `number` / `string` / `bool` / `range`) — определяет виджет ввода
- `parameter.uom` — единица измерения (code + symbol)
- `parameter_value.label` — человекочитаемая метка выбранного значения (для enum)

Для **enum**-параметров по одному `parameter_id` может быть несколько элементов с разными `parameter_value_id` (например, два цвета). Для **number/string/bool/range** — один элемент на `parameter_id` с заполненным `value_number` / `value_text` / `value_bool`.

Чтобы добавить **новый параметр** (показать доступные для выбора), нужен справочник: `GET /api/v1/admin/parameters?page=1&page_size=100` — список всех параметров с их `values[]` (для enum-типов).

---

## 4. Добавить или изменить одно значение

**Когда использовать:** нужно **добавить** один вариант (например, «Жёлтый») или обновить одно скалярное значение, **не трогая** остальные значения этого параметра.

**Запрос:**

```http
POST /api/v1/admin/products/{product_id}/characteristics
Content-Type: application/json
```

**Тело (enum — одно значение):**

```json
{
  "parameter_id": "color-param-uuid",
  "parameter_value_id": "yellow-value-uuid"
}
```

**Тело (число):**

```json
{
  "parameter_id": "weight-param-uuid",
  "value_number": 2.5,
  "uom_id": "kg-uom-uuid"
}
```

**Поведение:**

- Для **enum**: ищется запись по `(product_id, parameter_id, parameter_value_id)`. Если есть — обновляется, если нет — создаётся. Остальные значения этого параметра (например, красный) **не удаляются**. То есть POST только добавляет/обновляет одно выбранное значение.
- Для **number/string/bool/range**: ищется единственная запись по `(product_id, parameter_id)` (без значения). Если есть — обновляется, если нет — создаётся.

**Ответ:** `201 Created` или `200` — один объект характеристики (как в списке выше).

Если нужно «оставить только жёлтый, убрать красный» — этот эндпоинт для этого не подходит: он не удаляет другие значения. Используйте bulk (раздел 5) или удаление (раздел 6) + POST.

---

## 5. Задать ровно нужный набор значений (только жёлтый, без красного)

**Когда использовать:** нужно задать у продукта **ровно** такие значения параметра, какие указаны в запросе. Все предыдущие значения этого параметра у продукта заменяются.

**Запрос:**

```http
PUT /api/v1/admin/products/{product_id}/characteristics/bulk
Content-Type: application/json
```

**Тело:**

```json
{
  "characteristics": [
    {
      "parameter_id": "color-param-uuid",
      "parameter_value_ids": ["yellow-value-uuid"]
    },
    {
      "parameter_id": "weight-param-uuid",
      "value_number": 2.5,
      "uom_id": "kg-uom-uuid"
    }
  ]
}
```

**Правила:**

- В массиве `characteristics` каждый объект отвечает за **один** параметр.
- Для параметра типа **enum** задаётся массив `parameter_value_ids` — список UUID значений из справочника `ParameterValue`. У продукта по этому параметру будут ровно эти значения (все старые удаляются).
- Для **number/string/bool/range** задаётся одно значение через `value_number`, `value_text`, `value_bool`, при необходимости `uom_id`. Старая характеристика по этому параметру заменяется одной новой.

**Пример «только жёлтый цвет»:** в запросе по параметру «Цвет» передать только жёлтый:

```json
{
  "characteristics": [
    {
      "parameter_id": "color-param-uuid",
      "parameter_value_ids": ["yellow-value-uuid"]
    }
  ]
}
```

Если передать `"parameter_value_ids": ["yellow-value-uuid", "red-value-uuid"]` — у продукта будут оба цвета. Если передать `[]` или не передать `parameter_value_ids` для enum — по этому параметру у продукта не останется выбранных значений (все будут удалены для этого параметра).

**Ответ:**

```json
{
  "created": 2,
  "updated": 0,
  "deleted": 1
}
```

Заблокированные характеристики (`is_locked: true`) не удаляются и не перезаписываются.

---

## 6. Удалить все значения параметра у продукта

**Когда использовать:** нужно убрать у продукта все значения данного параметра (например, все цвета).

**Запрос:**

```http
DELETE /api/v1/admin/products/{product_id}/characteristics/{parameter_id}
```

**Поведение:** удаляются все записи `ProductCharacteristic` для данной пары `(product_id, parameter_id)`. Если есть записи с `is_locked: true`, запрос вернёт ошибку и ничего не удалит.

**Ответ:** `204 No Content`.

Чтобы после этого оставить «только жёлтый», после DELETE можно вызвать POST с `parameter_id` и `parameter_value_id: yellow-value-uuid`, или один раз вызвать PUT bulk с `parameter_value_ids: ["yellow-value-uuid"]` (раздел 5) — так делается одной операцией.

---

## 7. Типы параметров и поля запроса

| value_type | В запросе (POST / bulk) | Комментарий |
|------------|-------------------------|-------------|
| **enum** | `parameter_value_id` (POST) или `parameter_value_ids` (bulk) | Ссылки на `ParameterValue`. В bulk можно несколько. |
| **number** | `value_number`, опционально `uom_id` | Одно число. |
| **string** | `value_text` | Произвольная строка. |
| **bool** | `value_bool` | `true` / `false`. |
| **range** | `value_number` (и при необходимости второй параметр/логика на фронте) | На бэкенде хранится как число; при необходимости два числа — двумя характеристиками или своей схемой. |

В bulk для enum не передавайте `value_text`/`value_number`/`value_bool` — используются только `parameter_value_ids`. Для не-enum не передавайте `parameter_value_ids`.

---

## 8. Типы и примеры (TypeScript)

```typescript
// Встроенная информация о параметре
interface UOMBrief {
  id: string;
  code: string;
  symbol: string | null;
}

interface ParameterBrief {
  id: string;
  name: string;
  slug: string;
  value_type: 'enum' | 'number' | 'string' | 'bool' | 'range';
  is_filterable: boolean;
  uom: UOMBrief | null;
}

interface ParameterValueBrief {
  id: string;
  label: string;
  slug: string;
}

// Одна характеристика в ответе GET (обогащённая)
interface ProductCharacteristicDetailResponse {
  id: string;
  product_id: string;
  parameter_id: string;
  parameter_value_id: string | null;
  value_text: string | null;
  value_number: string | null;  // decimal приходит как строка
  value_bool: boolean | null;
  uom_id: string | null;
  source_type: string;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
  parameter: ParameterBrief;                // всегда есть — имя, тип, UOM
  parameter_value: ParameterValueBrief | null;  // для enum — выбранное значение
}

// POST — добавить/обновить одно значение
interface ProductCharacteristicCreate {
  parameter_id: string;
  parameter_value_id?: string;   // для enum
  value_text?: string;
  value_number?: number;
  value_bool?: boolean;
  uom_id?: string;
  source_type?: 'manual' | 'import' | 'system';
}

// PUT bulk — элемент массива
interface ProductCharacteristicBulkItem {
  parameter_id: string;
  parameter_value_ids?: string[];  // для enum — список UUID значений
  value_text?: string;
  value_number?: number;
  value_bool?: boolean;
  uom_id?: string;
}

interface ProductCharacteristicBulkCreate {
  characteristics: ProductCharacteristicBulkItem[];
}

interface ProductCharacteristicBulkResponse {
  created: number;
  updated: number;
  deleted: number;
}
```

**Пример: выставить продукту только цвет «Жёлтый» (убрать красный и остальные):**

```typescript
const colorParamId = '...';   // UUID параметра "Цвет"
const yellowValueId = '...';  // UUID значения "Жёлтый" из GET /admin/parameters/{colorParamId}

await fetch(`/api/v1/admin/products/${productId}/characteristics/bulk`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'X-Tenant-ID': tenantId,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    characteristics: [
      { parameter_id: colorParamId, parameter_value_ids: [yellowValueId] },
    ],
  }),
});
```

**Пример: добавить жёлтый, не снимая красный:**

```typescript
await fetch(`/api/v1/admin/products/${productId}/characteristics`, {
  method: 'POST',
  headers: { ... },
  body: JSON.stringify({
    parameter_id: colorParamId,
    parameter_value_id: yellowValueId,
  }),
});
```

---

## 9. Типичные сценарии UI

| Задача | Эндпоинт | Действие |
|--------|----------|----------|
| Показать все характеристики продукта | GET `/characteristics` | Список + подставить названия параметров/значений из справочника. |
| Добавить продукту один цвет «Жёлтый», не трогая остальные | POST `/characteristics` | `parameter_id` + `parameter_value_id` = жёлтый. |
| Сделать у продукта ровно один цвет «Жёлтый» (убрать красный и др.) | PUT `/characteristics/bulk` | Один элемент: `parameter_id` + `parameter_value_ids: [yellowId]`. |
| Снять у продукта все цвета | DELETE `/characteristics/{parameter_id}` | `parameter_id` = UUID параметра «Цвет». |
| Заполнить несколько параметров разом (цвет только жёлтый, вес 2.5) | PUT `/characteristics/bulk` | Два элемента: цвет с `[yellowId]`, вес с `value_number: 2.5`, `uom_id`. |

Итог: «указать, что у продукта параметр Цвет = только Жёлтый» делается через **PUT bulk** с `parameter_value_ids: [yellow-value-uuid]`. Остальные значения этого параметра при этом с бэкенда снимаются.
