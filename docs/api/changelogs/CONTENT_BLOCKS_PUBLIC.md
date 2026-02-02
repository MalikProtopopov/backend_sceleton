# Content Blocks Public API Documentation

Данная документация описывает изменения в публичных API эндпоинтах, связанные с новой системой контент-блоков.

## Обзор

Публичные эндпоинты для статей, кейсов и услуг теперь возвращают дополнительное поле `content_blocks` — массив гибких блоков контента.

Это позволяет фронтенду отображать:
- Видео (YouTube, RuTube и др.)
- Изображения (с адаптацией под mobile/desktop)
- Галереи/слайдеры
- Ссылки (сайты, Telegram боты)
- Блоки результатов (для кейсов)
- HTML-текст с произвольным форматированием

---

## Обновленные эндпоинты

### GET /api/v1/public/cases/{slug}

**Новое поле в ответе:**

```json
{
  "id": "uuid",
  "slug": "case-slug",
  "title": "Название кейса",
  "description": "<p>Старое описание (для обратной совместимости)</p>",
  "results": "<p>Старые результаты (для обратной совместимости)</p>",
  "content_blocks": [
    {
      "id": "uuid-блока",
      "locale": "ru",
      "block_type": "text",
      "sort_order": 0,
      "title": "Заголовок",
      "content": "<p>HTML контент</p>",
      "media_url": null,
      "thumbnail_url": null,
      "link_url": null,
      "link_label": null,
      "device_type": "both",
      "block_metadata": null
    },
    {
      "id": "uuid-блока-2",
      "locale": "ru",
      "block_type": "video",
      "sort_order": 1,
      "title": null,
      "content": null,
      "media_url": "https://www.youtube.com/watch?v=xxx",
      "thumbnail_url": "https://img.youtube.com/vi/xxx/maxresdefault.jpg",
      "link_url": null,
      "link_label": null,
      "device_type": "both",
      "block_metadata": {"provider": "youtube"}
    }
  ]
}
```

---

### GET /api/v1/public/articles/{slug}

**Новое поле в ответе:**

```json
{
  "id": "uuid",
  "slug": "article-slug",
  "title": "Название статьи",
  "content": "<p>Старый контент (для обратной совместимости)</p>",
  "content_blocks": [
    {
      "id": "uuid-блока",
      "locale": "ru",
      "block_type": "text",
      "sort_order": 0,
      "content": "<p>HTML контент</p>",
      ...
    }
  ]
}
```

---

### GET /api/v1/public/services/{slug}

**Новое поле в ответе:**

```json
{
  "id": "uuid",
  "slug": "service-slug",
  "title": "Название услуги",
  "description": "<p>Старое описание (для обратной совместимости)</p>",
  "content_blocks": [
    {
      "id": "uuid-блока",
      "locale": "ru",
      "block_type": "text",
      "sort_order": 0,
      "content": "<p>HTML контент</p>",
      ...
    }
  ]
}
```

---

## Структура ContentBlock

```typescript
interface ContentBlockResponse {
  id: string;                    // UUID блока
  locale: string;                // Локаль ("ru", "en")
  block_type: ContentBlockType;  // Тип блока
  sort_order: number;            // Порядок сортировки
  title: string | null;          // Заголовок блока
  content: string | null;        // HTML контент (для type="text")
  media_url: string | null;      // URL медиа (изображение/видео)
  thumbnail_url: string | null;  // URL превью (для видео)
  link_url: string | null;       // URL ссылки
  link_label: string | null;     // Текст ссылки/кнопки
  device_type: DeviceType;       // Тип устройства
  block_metadata: object | null; // Дополнительные данные
}

type ContentBlockType = "text" | "image" | "video" | "gallery" | "link" | "result";
type DeviceType = "mobile" | "desktop" | "both";
```

---

## Типы блоков и их поля

### text — Текстовый блок

```json
{
  "block_type": "text",
  "content": "<p>HTML содержимое</p>",
  "title": "Опциональный заголовок"
}
```

**Рендеринг:** отображать `content` как HTML.

---

### image — Изображение

```json
{
  "block_type": "image",
  "media_url": "/media/cases/image.jpg",
  "device_type": "both",
  "block_metadata": {
    "alt": "Описание изображения",
    "caption": "Подпись под изображением"
  }
}
```

**Рендеринг:**
- `device_type`: показывать только на указанных устройствах
- `block_metadata.alt`: атрибут alt для `<img>`
- `block_metadata.caption`: подпись под изображением

---

### video — Видео

```json
{
  "block_type": "video",
  "media_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
  "block_metadata": {
    "provider": "youtube"
  }
}
```

**Рендеринг:**
- `block_metadata.provider`: определяет способ встраивания (youtube, rutube, vimeo, other)
- `thumbnail_url`: превью до начала воспроизведения
- Для YouTube: конвертировать URL в embed URL

**Пример обработки YouTube:**
```typescript
function getYouTubeEmbedUrl(url: string): string {
  const videoId = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&]+)/)?.[1];
  return `https://www.youtube.com/embed/${videoId}`;
}
```

---

### gallery — Галерея/Слайдер

```json
{
  "block_type": "gallery",
  "block_metadata": {
    "images": [
      {
        "url": "/media/cases/slide1.jpg",
        "alt": "Слайд 1",
        "device_type": "both"
      },
      {
        "url": "/media/cases/slide2.jpg",
        "alt": "Слайд 2",
        "device_type": "both"
      },
      {
        "url": "/media/cases/slide3-mobile.jpg",
        "alt": "Слайд 3 (мобильная версия)",
        "device_type": "mobile"
      }
    ]
  }
}
```

**Рендеринг:**
- Использовать библиотеку слайдера (Swiper, Embla, и др.)
- Фильтровать `block_metadata.images` по `device_type`

---

### link — Ссылка

```json
{
  "block_type": "link",
  "link_url": "https://t.me/mybot",
  "link_label": "Открыть в Telegram",
  "block_metadata": {
    "icon": "telegram"
  }
}
```

**Рендеринг:**
- Отображать как кнопку или ссылку
- `block_metadata.icon`: иконка (telegram, website, play_store, app_store, и др.)

---

### result — Блок результата

```json
{
  "block_type": "result",
  "title": "Результат работы",
  "content": "<ul><li>Увеличение конверсии на 30%</li></ul>",
  "media_url": "https://www.youtube.com/watch?v=demo",
  "link_url": "https://example.com",
  "link_label": "Перейти на сайт"
}
```

**Рендеринг:** комбинированный блок с заголовком, текстом, видео и ссылкой.

---

## Стратегия рендеринга

### Логика отображения контента

```typescript
function renderContent(entity: CasePublicResponse | ArticlePublicResponse | ServicePublicResponse) {
  // Если есть контент-блоки — рендерим их
  if (entity.content_blocks && entity.content_blocks.length > 0) {
    return renderContentBlocks(entity.content_blocks);
  }
  
  // Иначе используем старые поля для обратной совместимости
  if ('description' in entity && entity.description) {
    return renderHtml(entity.description);
  }
  if ('content' in entity && entity.content) {
    return renderHtml(entity.content);
  }
  
  return null;
}
```

### Рендеринг блоков

```typescript
function renderContentBlocks(blocks: ContentBlockResponse[]) {
  // Сортировка по sort_order
  const sortedBlocks = [...blocks].sort((a, b) => a.sort_order - b.sort_order);
  
  return sortedBlocks.map(block => {
    // Проверка device_type
    if (!shouldShowOnDevice(block.device_type)) {
      return null;
    }
    
    switch (block.block_type) {
      case 'text':
        return <TextBlock content={block.content} title={block.title} />;
      case 'image':
        return <ImageBlock url={block.media_url} blockMetadata={block.block_metadata} />;
      case 'video':
        return <VideoBlock url={block.media_url} thumbnail={block.thumbnail_url} blockMetadata={block.block_metadata} />;
      case 'gallery':
        return <GalleryBlock images={block.block_metadata?.images} />;
      case 'link':
        return <LinkBlock url={block.link_url} label={block.link_label} icon={block.block_metadata?.icon} />;
      case 'result':
        return <ResultBlock {...block} />;
      default:
        return null;
    }
  });
}
```

### Определение device_type

```typescript
function shouldShowOnDevice(deviceType: string | null): boolean {
  if (!deviceType || deviceType === 'both') return true;
  
  const isMobile = window.innerWidth < 768; // или использовать медиа-запросы
  
  if (deviceType === 'mobile') return isMobile;
  if (deviceType === 'desktop') return !isMobile;
  
  return true;
}
```

---

## Примеры React-компонентов

### TextBlock

```tsx
function TextBlock({ content, title }: { content: string | null; title: string | null }) {
  return (
    <div className="content-block content-block--text">
      {title && <h3>{title}</h3>}
      {content && <div dangerouslySetInnerHTML={{ __html: content }} />}
    </div>
  );
}
```

### VideoBlock

```tsx
function VideoBlock({ url, thumbnail, blockMetadata }: { 
  url: string | null; 
  thumbnail: string | null; 
  blockMetadata: any 
}) {
  const [isPlaying, setIsPlaying] = useState(false);
  
  const embedUrl = blockMetadata?.provider === 'youtube' 
    ? getYouTubeEmbedUrl(url!)
    : url;
  
  return (
    <div className="content-block content-block--video">
      {!isPlaying && thumbnail ? (
        <div className="video-thumbnail" onClick={() => setIsPlaying(true)}>
          <img src={thumbnail} alt="Video thumbnail" />
          <button className="play-button">▶</button>
        </div>
      ) : (
        <iframe src={embedUrl} allowFullScreen />
      )}
    </div>
  );
}
```

### GalleryBlock

```tsx
import { Swiper, SwiperSlide } from 'swiper/react';

function GalleryBlock({ images }: { images: Array<{ url: string; alt: string; device_type: string }> }) {
  const filteredImages = images?.filter(img => shouldShowOnDevice(img.device_type)) || [];
  
  return (
    <div className="content-block content-block--gallery">
      <Swiper spaceBetween={20} slidesPerView={1}>
        {filteredImages.map((img, idx) => (
          <SwiperSlide key={idx}>
            <img src={img.url} alt={img.alt} />
          </SwiperSlide>
        ))}
      </Swiper>
    </div>
  );
}
```

### LinkBlock

```tsx
function LinkBlock({ url, label, icon }: { url: string | null; label: string | null; icon: string }) {
  const iconMap: Record<string, string> = {
    telegram: '📱',
    website: '🌐',
    play_store: '▶️',
    app_store: '🍎',
  };
  
  return (
    <a href={url!} target="_blank" rel="noopener noreferrer" className="content-block content-block--link">
      {icon && <span className="link-icon">{iconMap[icon] || '🔗'}</span>}
      <span className="link-label">{label || 'Перейти'}</span>
    </a>
  );
}
```

---

## Обратная совместимость

Система Content Blocks **не ломает** существующую функциональность:

1. Старые поля (`description`, `results`, `content`) **остаются** в ответах API
2. Если `content_blocks` пустой — используйте старые поля
3. Если `content_blocks` заполнен — рекомендуется рендерить блоки

**Рекомендация:** Постепенно мигрировать контент на Content Blocks для более гибкого отображения.

---

## Кэширование

Публичные эндпоинты кэшируются браузером (`Cache-Control: max-age=300`).

При обновлении контент-блоков через админку:
- Кэш автоматически инвалидируется через 5 минут
- Для немедленного обновления — очистить кэш браузера или добавить query-параметр
