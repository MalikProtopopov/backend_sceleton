# Webmaster Verification: Changelog для Frontend

> **Дата:** 2026-02-16  
> **Версия:** 1.0  
> **Статус:** Готово к внедрению

## Обзор изменений

Добавлена поддержка верификации владения сайтом для **Яндекс.Вебмастера** и **Google Search Console**. Теперь администратор может настроить верификационные коды через админ-панель, и бэкенд будет динамически генерировать верификационные файлы для подтверждения владения сайтом.

**Преимущества:**
- Не нужно вручную загружать файлы на сервер клиентского сайта
- Централизованное управление через админку
- Поддержка нескольких методов верификации для Google (файл и мета-тег)

---

## Изменения для **Админской панели**

### 1. Новые поля в настройках тенанта

В форме редактирования настроек тенанта (`Settings` → `Tenant Settings`) добавить **3 новых поля** в секцию «SEO и аналитика»:

```typescript
interface TenantSettings {
  // ... существующие поля
  ga_tracking_id?: string;
  ym_counter_id?: string;
  
  // НОВЫЕ ПОЛЯ
  yandex_verification_code?: string;
  google_verification_code?: string;
  google_verification_meta?: string;
}
```

### 2. Валидация полей

**Яндекс.Вебмастер:**
- Формат: `yandex_[hex]` (например, `yandex_821edd51f146c052`)
- Regex: `/^yandex_[a-f0-9]+$/`
- Max длина: 255 символов

**Google Search Console (файл):**
- Формат: `google[hex]` (например, `google1234567890abcdef`)
- Regex: `/^google[a-f0-9]+$/`
- Max длина: 255 символов

**Google Search Console (мета-тег):**
- Произвольная строка (hex без префикса)
- Max длина: 500 символов
- Пример: `1234567890abcdef1234567890abcdef`

### 3. UI компоненты (React пример)

```tsx
// Добавить в SettingsForm.tsx после секции Analytics:

<section>
  <h3>Webmaster Verification</h3>
  <p className="text-sm text-gray-600 mb-4">
    Подтвердите владение сайтом для поисковых систем. 
    Коды можно получить в Яндекс.Вебмастере или Google Search Console.
  </p>
  
  <FormField
    label="Яндекс.Вебмастер"
    name="yandex_verification_code"
    value={settings.yandex_verification_code || ''}
    onChange={(value) => updateField('yandex_verification_code', value)}
    placeholder="yandex_821edd51f146c052"
    helpText="Название файла без расширения .html"
  />
  
  <FormField
    label="Google Verification (файл)"
    name="google_verification_code"
    value={settings.google_verification_code || ''}
    onChange={(value) => updateField('google_verification_code', value)}
    placeholder="google1234567890abcdef"
    helpText="Название файла без расширения .html"
  />
  
  <FormField
    label="Google Verification (мета-тег)"
    name="google_verification_meta"
    value={settings.google_verification_meta || ''}
    onChange={(value) => updateField('google_verification_meta', value)}
    placeholder="1234567890abcdef1234567890abcdef"
    helpText="Значение атрибута content из мета-тега (альтернатива файлу)"
  />
</section>
```

### 4. Инструкции для администратора

Добавить **tooltip** или **Help Section** с инструкциями:

```markdown
### Как получить код верификации?

**Яндекс.Вебмастер:**
1. Откройте https://webmaster.yandex.ru/
2. Добавьте ваш сайт
3. Выберите способ подтверждения "HTML-файл"
4. Скопируйте название файла (например, `yandex_821edd51f146c052.html`)
5. Уберите `.html` и вставьте в поле выше

**Google Search Console (файл):**
1. Откройте https://search.google.com/search-console
2. Добавьте ресурс
3. Выберите "HTML-файл"
4. Скачайте файл и посмотрите его название
5. Уберите `.html` и вставьте в поле

**Google Search Console (мета-тег):**
1. Откройте https://search.google.com/search-console
2. Добавьте ресурс
3. Выберите "HTML-тег"
4. Скопируйте значение из `content="..."`
5. Вставьте в поле
```

### 5. API запрос для сохранения

```typescript
// PUT /api/v1/tenants/{tenantId}/settings
const updateTenantSettings = async (tenantId: string, settings: TenantSettings) => {
  const response = await fetch(`/api/v1/tenants/${tenantId}/settings`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
    body: JSON.stringify({
      // ... остальные настройки
      yandex_verification_code: settings.yandex_verification_code || null,
      google_verification_code: settings.google_verification_code || null,
      google_verification_meta: settings.google_verification_meta || null,
    }),
  });
  
  return response.json();
};
```

---

## Изменения для **Клиентского сайта**

### 1. Обновленный эндпоинт аналитики

**Эндпоинт:** `GET /api/v1/public/tenants/{tenantId}/analytics`

**Было:**
```typescript
interface TenantAnalytics {
  ga_tracking_id: string | null;
  ym_counter_id: string | null;
}
```

**Стало:**
```typescript
interface TenantAnalytics {
  ga_tracking_id: string | null;
  ym_counter_id: string | null;
  google_verification_meta: string | null; // НОВОЕ ПОЛЕ
}
```

### 2. Новый публичный эндпоинт

**Эндпоинт:** `GET /api/v1/public/tenants/{tenantId}/verification/{filename}`

Этот эндпоинт динамически генерирует верификационные файлы для Яндекса и Google.

**Примеры запросов:**
```bash
# Яндекс
GET /api/v1/public/tenants/63d068f7-7a47-46fe-aeb0-c82588e995a4/verification/yandex_821edd51f146c052.html

# Google
GET /api/v1/public/tenants/63d068f7-7a47-46fe-aeb0-c82588e995a4/verification/google1234567890abcdef.html
```

**Ответы:**
```html
<!-- Яндекс -->
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
</head>
<body>Verification: 821edd51f146c052</body>
</html>

<!-- Google -->
google-site-verification: google1234567890abcdef.html
```

### 3. Интеграция в Next.js

#### Вариант A: Rewrites (рекомендуется)

Добавить в `next.config.js`:

```javascript
// next.config.js
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID;

module.exports = {
  async rewrites() {
    return [
      // ... существующие rewrites для sitemap, robots
      
      // Яндекс.Вебмастер верификация
      {
        source: '/yandex_:code.html',
        destination: `${API_BASE}/api/v1/public/tenants/${TENANT_ID}/verification/yandex_:code.html`,
      },
      
      // Google Search Console верификация
      {
        source: '/google:code.html',
        destination: `${API_BASE}/api/v1/public/tenants/${TENANT_ID}/verification/google:code.html`,
      },
    ];
  },
};
```

**Как это работает:**
- Когда Яндекс запрашивает `https://yoursite.com/yandex_821edd51f146c052.html`
- Next.js проксирует запрос на бэкенд
- Бэкенд генерирует файл динамически
- Яндекс получает корректный файл и подтверждает владение ✓

#### Вариант B: API Route (альтернатива)

Если rewrites не работают, создать API route:

```typescript
// pages/api/[...verification].ts (Pages Router)
// ИЛИ
// app/api/[...verification]/route.ts (App Router)

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.API_URL || 'http://localhost:8000';
const TENANT_ID = process.env.TENANT_ID;

export async function GET(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const filename = pathname.split('/').pop();
  
  // Валидация формата файла
  if (!filename?.match(/^(yandex_[a-f0-9]+|google[a-f0-9]+)\.html$/)) {
    return new NextResponse('Not found', { status: 404 });
  }
  
  // Запрос к бэкенду
  const response = await fetch(
    `${API_BASE}/api/v1/public/tenants/${TENANT_ID}/verification/${filename}`
  );
  
  if (!response.ok) {
    return new NextResponse('Not found', { status: 404 });
  }
  
  const html = await response.text();
  
  return new NextResponse(html, {
    headers: {
      'Content-Type': 'text/html; charset=UTF-8',
    },
  });
}
```

### 4. Интеграция Google мета-тега

#### Next.js App Router (app/layout.tsx)

```typescript
// app/layout.tsx
import { fetchAnalytics } from '@/lib/api';

export async function generateMetadata() {
  const analytics = await fetchAnalytics();
  
  return {
    title: 'Your Site Title',
    description: 'Your Site Description',
    
    // Google Search Console верификация через мета-тег
    verification: analytics.google_verification_meta
      ? { google: analytics.google_verification_meta }
      : undefined,
    
    // Остальные метаданные...
  };
}

export default function RootLayout({ children }) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
```

#### Next.js Pages Router (pages/_document.tsx)

```typescript
// pages/_document.tsx
import Document, { Html, Head, Main, NextScript } from 'next/document';

class MyDocument extends Document {
  static async getInitialProps(ctx) {
    const initialProps = await Document.getInitialProps(ctx);
    
    // Получаем аналитику на сервере
    const analytics = await fetchAnalytics();
    
    return { ...initialProps, analytics };
  }

  render() {
    const { analytics } = this.props as any;
    
    return (
      <Html>
        <Head>
          {/* Google Search Console верификация */}
          {analytics?.google_verification_meta && (
            <meta
              name="google-site-verification"
              content={analytics.google_verification_meta}
            />
          )}
          
          {/* Остальные мета-теги */}
        </Head>
        <body>
          <Main />
          <NextScript />
        </body>
      </Html>
    );
  }
}

export default MyDocument;
```

### 5. API клиент для аналитики

```typescript
// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const TENANT_ID = process.env.NEXT_PUBLIC_TENANT_ID!;

export interface TenantAnalytics {
  ga_tracking_id: string | null;
  ym_counter_id: string | null;
  google_verification_meta: string | null; // НОВОЕ
}

export async function fetchAnalytics(): Promise<TenantAnalytics> {
  const response = await fetch(
    `${API_BASE}/api/v1/public/tenants/${TENANT_ID}/analytics`,
    { next: { revalidate: 3600 } } // кэш на 1 час
  );
  
  if (!response.ok) {
    throw new Error('Failed to fetch analytics');
  }
  
  return response.json();
}
```

---

## Чеклист для внедрения

### Админская панель ✓

- [ ] Добавить 3 новых поля в форму настроек тенанта
- [ ] Добавить валидацию форматов (`yandex_*`, `google*`)
- [ ] Обновить TypeScript интерфейс `TenantSettings`
- [ ] Добавить инструкции/tooltip для администратора
- [ ] Протестировать сохранение и отображение полей

### Клиентский сайт ✓

- [ ] Обновить интерфейс `TenantAnalytics` (добавить `google_verification_meta`)
- [ ] Добавить rewrites в `next.config.js` для `/yandex_*.html` и `/google*.html`
- [ ] Интегрировать `google_verification_meta` в layout/document
- [ ] Протестировать доступность верификационных файлов:
  - `curl https://yoursite.com/yandex_ТЕСТОВЫЙ_КОД.html` → должен вернуть 404 (если код не настроен)
  - После настройки в админке → должен вернуть HTML с кодом
- [ ] Проверить мета-тег в `<head>` (View Page Source)

### Тестирование интеграции ✓

- [ ] Администратор вводит код Яндекса в админке
- [ ] Открыть `https://yoursite.com/yandex_ВАШ_КОД.html` → должен показать HTML
- [ ] Запустить верификацию в Яндекс.Вебмастере → успешно ✓
- [ ] Администратор вводит мета-тег Google в админке
- [ ] Проверить `<meta name="google-site-verification">` в исходном коде страницы
- [ ] Запустить верификацию в Google Search Console → успешно ✓

---

## Частые вопросы (FAQ)

### 1. Нужно ли загружать файлы на сервер вручную?

**Нет.** Файлы генерируются динамически бэкендом на основе кодов из БД. Достаточно настроить rewrites в Next.js.

### 2. Можно ли использовать оба метода Google (файл и мета-тег)?

**Да.** Можно заполнить оба поля — Google примет любой из способов верификации.

### 3. Что если администратор ввёл неправильный код?

Поисковик не сможет подтвердить владение. Администратор должен проверить правильность кода и обновить его в админке.

### 4. Как проверить, что всё работает?

**Для Яндекса:**
```bash
curl https://yoursite.com/yandex_ВАШ_КОД.html
# Должно вернуть HTML с кодом верификации
```

**Для Google (файл):**
```bash
curl https://yoursite.com/googleВАШ_КОД.html
# Должно вернуть: google-site-verification: googleВАШ_КОД.html
```

**Для Google (мета-тег):**
- Открыть главную страницу сайта
- View Page Source (Ctrl+U)
- Найти `<meta name="google-site-verification" content="...">`

### 5. Нужно ли перезапускать Next.js после настройки?

**Rewrites:** Да, нужен перезапуск Next.js после изменения `next.config.js`.

**Мета-тег:** Нет, значение подтягивается динамически из API.

---

## Контакты для вопросов

По вопросам интеграции обращаться к бэкенд-разработчику или в канал #frontend.

**Дата обновления:** 2026-02-16
