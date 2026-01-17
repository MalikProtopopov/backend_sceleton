# 🎯 Corporate CMS Engine v1.0 — Рекомендации по улучшению бэкенда

**Дата:** 14 января 2026  
**Статус:** ✅ Готово к реализации  
**Время на реализацию:** 15-20 часов параллельно с разработкой  

---

## 📋 Оглавление

1. [Анализ текущей архитектуры](#анализ-текущей-архитектуры)
2. [🔴 Критичные улучшения (v1)](#-критичные-улучшения-v1)
3. [🟡 Важные оптимизации](#-важные-оптимизации)
4. [🟢 Nice-to-have фичи (v2+)](#-nice-to-have-фичи-v2)
5. [Рекомендуемый MVP](#рекомендуемый-mvp)
6. [Планирование и сроки](#планирование-и-сроки)

---

## Анализ текущей архитектуры

### ✅ Сильные стороны

| Аспект | Оценка | Комментарий |
|--------|--------|-----------|
| **DDD слои** | ⭐⭐⭐⭐⭐ | Правильная разделение ответственности |
| **Модульность** | ⭐⭐⭐⭐⭐ | Четкие границы между доменами |
| **Multi-tenant** | ⭐⭐⭐⭐⭐ | tenant_id везде, готовность к SaaS |
| **Локализация** | ⭐⭐⭐⭐⭐ | Translation tables, а не JSONB (масштабируется) |
| **SEO** | ⭐⭐⭐⭐⭐ | Сразу заложены routes, sitemap, hreflang |
| **RBAC** | ⭐⭐⭐⭐ | Гранулярные права, хороший дизайн |
| **Аудит** | ⭐⭐⭐⭐ | Полная история изменений |
| **API дизайн** | ⭐⭐⭐⭐ | REST, OpenAPI/Swagger, pagination |

### ⚠️ Критические пробелы

| Пробел | Риск | Решение |
|--------|------|---------|
| Нет soft delete | 🔴 Потеря SEO (301 редиректы) | Добавить `deleted_at` везде |
| Нет optimistic locking | 🔴 Race conditions при редактировании | Версионирование через `version` поле |
| Только Pydantic валидация | 🔴 БД может содержать невалидные данные | CheckConstraint'ы в моделях |
| Логирование текстовое | 🔴 Сложно парсить в production | JSON структурированное логирование |
| Нет полноценной транзакции | 🟡 Несогласованность между article и locales | Transactional decorators |
| Отсутствуют индексы | 🟡 Slow queries при масштабировании | Индексы на часто используемые поля |

---

## 🔴 Критичные улучшения (v1)

### 1. Soft Delete (Мягкое удаление)

**Суть:** Вместо физического `DELETE` — добавляем `deleted_at` поле

**Почему это критично:**

```
Сценарий:
1. Админ создал услугу "/services/consulting"
2. Фронт залиндовал на эту страницу → Google проиндексировал
3. Через полгода админ удалил услугу
4. Без Soft Delete: GET /services/consulting → 404
   → Google видит 404 → перестает показывать в выдаче
   → теряемся в поисковой выдаче

С Soft Delete:
1. DELETE /services/consulting → запись остается, deleted_at = now()
2. GET /services/consulting → скрывается из публичного API
3. Admin: DELETE + автоматически создает 301 редирект
   → Google следит редирект → не теряемся в выдаче
```

**Реализация:**

```python
# app/core/base_model.py
from datetime import datetime
from sqlalchemy import Column, DateTime

class SoftDeleteMixin:
    """Миксин для мягкого удаления"""
    deleted_at: datetime | None = Column(DateTime, nullable=True, index=True)

# Применить ко всем основным сущностям:
class Service(Base, SoftDeleteMixin):
    """Услуга"""
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id: UUID = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    name: str = Column(String(255), nullable=False)
    deleted_at: datetime | None = Column(DateTime, nullable=True)

class Article(Base, SoftDeleteMixin):
    """Статья"""
    pass

class Employee(Base, SoftDeleteMixin):
    """Сотрудник"""
    pass

class Case(Base, SoftDeleteMixin):
    """Кейс"""
    pass

# Везде в queries добавить фильтр:
# models/repositories.py
class ServiceRepository:
    async def get_active(self, tenant_id: UUID):
        return await db.query(Service).filter(
            Service.tenant_id == tenant_id,
            Service.deleted_at.is_(None)  # ← Критично!
        ).all()
    
    async def get_deleted(self, tenant_id: UUID):
        """Для восстановления в админке"""
        return await db.query(Service).filter(
            Service.tenant_id == tenant_id,
            Service.deleted_at.isnot(None)
        ).all()

# DELETE эндпоинт: soft delete + auto-redirect
@admin_router.delete("/services/{id}")
async def delete_service(id: UUID, db: AsyncSession):
    service = await db.get(Service, id)
    service.deleted_at = datetime.utcnow()
    await db.commit()
    
    # Создать 301 редирект на главную
    old_slug = service.slug
    redirect = Redirect(
        tenant_id=service.tenant_id,
        from_path=f"/services/{old_slug}",
        to_path="/services",
        status_code=301,
        is_active=True
    )
    db.add(redirect)
    await db.commit()
    
    return {"message": "Service soft deleted, redirect created"}
```

**Миграция:**

```sql
-- alembic/versions/001_add_soft_delete.py
def upgrade():
    op.add_column('services', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('articles', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('employees', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('cases', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('reviews', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('faq', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    
    op.create_index('idx_services_deleted_at', 'services', ['deleted_at'])
    op.create_index('idx_articles_deleted_at', 'articles', ['deleted_at'])

def downgrade():
    op.drop_index('idx_services_deleted_at', 'services')
    op.drop_column('services', 'deleted_at')
    # ... остальное
```

**Усилие:** 2-3 часа  
**Когда:** ДО первого деплоя (очень критично для SEO)

---

### 2. Optimistic Locking (Версионирование)

**Суть:** Предотвращение перезаписи данных при одновременном редактировании

**Сценарий проблемы:**

```
Время  | Юзер 1                    | Юзер 2                   | БД
───────┼───────────────────────────┼──────────────────────────┼──────
t=0    | GET /articles/123          |                          | {title: "Old"}
t=1    |                            | GET /articles/123        | {title: "Old"}
t=2    | Меняет title на "New"      |                          |
       | PATCH /articles/123        |                          |
       | body: {title: "New"}       |                          |
t=3    |                            | Меняет body на "Updated" | {title: "New"}
       |                            | PATCH /articles/123      |
       |                            | body: {title: "Old", body: "Updated"}
t=4    |                            |                          | {title: "Old", body: "Updated"}
       |                            |                          | ❌ Потеря изменений от Юзера 1!
```

**Решение — Optimistic Locking:**

```python
# models.py
class Article(Base, SoftDeleteMixin):
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id: UUID = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    title: str = Column(String(255), nullable=False)
    body: str = Column(Text, nullable=False)
    
    # ← Вот это новое
    version: int = Column(Integer, default=1, nullable=False)
    
    deleted_at: datetime | None = Column(DateTime, nullable=True)

# schemas.py
class ArticleUpdate(BaseModel):
    title: str
    body: str
    version: int  # <- Требуем версию от клиента

# routes.py
@admin_router.patch("/articles/{id}")
async def update_article(
    id: UUID,
    data: ArticleUpdate,
    db: AsyncSession
):
    article = await db.get(Article, id)
    
    # Проверка версии
    if article.version != data.version:
        raise HTTPException(
            status_code=409,  # Conflict
            detail=f"Article was modified. Your version: {data.version}, "
                   f"Current version: {article.version}. "
                   f"Please refresh and try again."
        )
    
    # Обновляем + инкрементируем версию
    article.title = data.title
    article.body = data.body
    article.version += 1  # ← Важно!
    
    await db.commit()
    return article
```

**Ответ при конфликте:**

```json
{
  "type": "https://api.example.com/errors/conflict",
  "title": "Conflict",
  "status": 409,
  "detail": "Article was modified. Your version: 2, Current version: 3. Please refresh and try again."
}
```

**Клиентская сторона (Next.js):**

```typescript
// Когда получаем статью
const [article, setArticle] = useState(null);

useEffect(() => {
  fetch(`/api/v1/admin/articles/${id}`)
    .then(r => r.json())
    .then(data => setArticle(data.data)); // Включает version
}, [id]);

// При сохранении
const handleSave = async (title, body) => {
  try {
    const response = await fetch(`/api/v1/admin/articles/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        body,
        version: article.version  // <- Отправляем текущую версию
      })
    });
    
    if (response.status === 409) {
      const error = await response.json();
      alert(`${error.detail}\n\nПожалуйста, обновите страницу и попробуйте снова.`);
      // Reload
      location.reload();
    } else {
      setArticle(await response.json());
      alert("Сохранено!");
    }
  } catch (err) {
    alert("Ошибка: " + err);
  }
};
```

**Усилие:** 2 часа  
**Когда:** Перед выпуском первому клиенту

---

### 3. DB Constraints (CheckConstraint + UniqueConstraint)

**Суть:** Валидация не только в Pydantic, но и в БД

**Проблема:**

```
Pydantic валидирует:
  ✓ title не пусто
  ✓ status в допустимых значениях

Но если:
  • Кто-то напрямую в БД вставит некорректные данные
  • Ошибка в другом коде обойдет Pydantic
  • SQL injection атака

→ БД содержит невалидные данные
→ Нарушается целостность
→ Сложно отследить источник проблемы
```

**Решение:**

```python
from sqlalchemy import CheckConstraint, UniqueConstraint

class Service(Base, SoftDeleteMixin):
    __tablename__ = "services"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id: UUID = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    name: str = Column(String(255), nullable=False)
    slug: str = Column(String(255), nullable=False)
    status: str = Column(String(50), nullable=False, default="draft")
    icon_url: str | None = Column(String(2000), nullable=True)
    sort_order: int = Column(Integer, default=0, nullable=False)
    created_at: datetime = Column(DateTime, server_default=func.now())
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # ← Constraints добавляем сюда
    __table_args__ = (
        # CHECK: статус только допустимые значения
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_service_status_valid"
        ),
        
        # UNIQUE: per tenant, нельзя два сервиса с одинаковым slug
        UniqueConstraint(
            "tenant_id", "slug",
            name="uq_tenant_service_slug"
        ),
        
        # CHECK: имя не пусто
        CheckConstraint(
            "LENGTH(name) > 0",
            name="ck_service_name_not_empty"
        ),
        
        # CHECK: sort_order положительное число
        CheckConstraint(
            "sort_order >= 0",
            name="ck_service_sort_order_positive"
        ),
    )

# Аналогично для всех моделей:

class Article(Base, SoftDeleteMixin):
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_article_status_valid"
        ),
        UniqueConstraint(
            "tenant_id", "slug",
            name="uq_tenant_article_slug"
        ),
        CheckConstraint(
            "LENGTH(title) > 0",
            name="ck_article_title_not_empty"
        ),
    )

class AdminUser(Base):
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "email",
            name="uq_tenant_user_email"
        ),
        CheckConstraint(
            "LENGTH(email) > 0 AND email LIKE '%@%'",
            name="ck_user_email_valid"
        ),
    )

class Inquiry(Base):
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'read', 'contacted', 'converted', 'spam')",
            name="ck_inquiry_status_valid"
        ),
        CheckConstraint(
            "LENGTH(email) > 0 AND email LIKE '%@%'",
            name="ck_inquiry_email_valid"
        ),
    )

class Review(Base, SoftDeleteMixin):
    __table_args__ = (
        CheckConstraint(
            "rating >= 1 AND rating <= 5",
            name="ck_review_rating_range"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_review_status_valid"
        ),
    )
```

**Обработка ошибок при нарушении constraint'а:**

```python
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

@admin_router.post("/services")
async def create_service(data: ServiceCreate, db: AsyncSession):
    try:
        service = Service(**data.dict())
        db.add(service)
        await db.commit()
        return service
    
    except IntegrityError as e:
        await db.rollback()
        
        # Определяем какой constraint нарушен
        if "uq_tenant_service_slug" in str(e.orig):
            raise HTTPException(
                status_code=409,
                detail=f"Service with slug '{data.slug}' already exists in this tenant"
            )
        elif "ck_service_status_valid" in str(e.orig):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status '{data.status}'. "
                       f"Allowed: draft, published, archived"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Database constraint violation"
            )
```

**Миграция:**

```python
# alembic/versions/002_add_table_constraints.py
def upgrade():
    op.create_check_constraint(
        'ck_service_status_valid',
        'services',
        "status IN ('draft', 'published', 'archived')"
    )
    op.create_unique_constraint(
        'uq_tenant_service_slug',
        'services',
        ['tenant_id', 'slug']
    )
    # ... остальное

def downgrade():
    op.drop_constraint('ck_service_status_valid', 'services')
    op.drop_constraint('uq_tenant_service_slug', 'services')
    # ... остальное
```

**Усилие:** 2 часа (для всех моделей)  
**Когда:** При создании моделей, перед первой миграцией

---

### 4. Structured Logging (JSON)

**Суть:** Логирование в JSON вместо текста

**Проблема текстовых логов:**

```
# Текстовый лог (сложно парсить):
[2026-01-14 17:45:23] INFO: Article created by user_id=abc123 in 145ms
[2026-01-14 17:45:24] ERROR: Failed to save article, reason=database_timeout

# Парсить очень сложно:
- Сделать regex для каждого типа лога
- Отправить в ELK/Datadog → он тоже парсит regex
- Потерялась половина информации
```

**Решение — JSON логирование:**

```python
# app/core/logging.py
import json
import logging
from pythonjsonlogger import jsonlogger

class JSONFormatter(jsonlogger.JsonFormatter):
    """Кастомный форматер для JSON логов"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = self.formatTime(record)
        log_record['level'] = record.levelname
        log_record['logger'] = record.name

def setup_logging():
    """Инициализация структурированного логирования"""
    
    # Для файла — JSON
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/app.json',
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(JSONFormatter())
    
    # Для консоли — читаемый формат во время разработки
    console_handler = logging.StreamHandler()
    if os.getenv('ENVIRONMENT') == 'production':
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter('[%(levelname)s] %(message)s')
        )
    
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

# app/main.py
from app.core.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup():
    logger.info("Application started", extra={
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT")
    })
```

**Использование в коде:**

```python
from app.core.logging import logger

# Перед операцией
logger.info("Creating article", extra={
    "user_id": str(user_id),
    "tenant_id": str(tenant_id),
    "action": "create_article"
})

# Во время операции
import time
start = time.time()

try:
    article = Article(**data.dict())
    db.add(article)
    await db.commit()
    
    duration_ms = (time.time() - start) * 1000
    logger.info("Article created successfully", extra={
        "user_id": str(user_id),
        "article_id": str(article.id),
        "duration_ms": int(duration_ms),
        "action": "create_article",
        "result": "success"
    })

except Exception as e:
    duration_ms = (time.time() - start) * 1000
    logger.error("Failed to create article", extra={
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "error": str(e),
        "duration_ms": int(duration_ms),
        "action": "create_article",
        "result": "error"
    }, exc_info=True)
    raise
```

**Результат в логе:**

```json
{
  "timestamp": "2026-01-14T17:45:23.123Z",
  "level": "INFO",
  "logger": "app.modules.content.service",
  "message": "Creating article",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440001",
  "action": "create_article"
}

{
  "timestamp": "2026-01-14T17:45:23.267Z",
  "level": "INFO",
  "logger": "app.modules.content.service",
  "message": "Article created successfully",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "article_id": "770e8400-e29b-41d4-a716-446655440002",
  "duration_ms": 144,
  "action": "create_article",
  "result": "success"
}
```

**Отправка в ELK/Datadog:**

```yaml
# docker-compose.yml — добавить Filebeat
filebeat:
  image: docker.elastic.co/beats/filebeat:8.0.0
  volumes:
    - ./logs:/logs:ro
  environment:
    - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
  command: filebeat -e -strict.perms=false
```

Потом в Kibana/Datadog:
```
# Поиск всех ошибок за последний час
level: "ERROR" AND timestamp > now-1h

# Поиск медленных операций
action: "create_article" AND duration_ms > 1000

# Группировка по ошибкам
aggregation by error
```

**Усилие:** 3 часа  
**Когда:** Перед деплоем в production

---

### 5. Transactional Decorators

**Суть:** Обертка для обеспечения атомарности операций

**Проблема:**

```python
# Без транзакции:
async def create_article(data: ArticleCreate):
    # Шаг 1: создаём article
    article = Article(
        tenant_id=tenant_id,
        title=data.title,
        slug=data.slug
    )
    db.add(article)
    await db.commit()  # ← Коммит!
    
    # Шаг 2: создаём article_locales
    for locale_code, title in data.locales.items():
        locale = ArticleLocale(
            article_id=article.id,
            locale_code=locale_code,
            title=title
        )
        db.add(locale)
        await db.commit()  # ← Коммит!
    
    # Если здесь упадет исключение?
    # → Article создана, но locales не создана
    # → БД в несогласованном состоянии
```

**Решение — Transactional Decorator:**

```python
# app/core/database.py
from functools import wraps
from sqlalchemy.ext.asyncio import AsyncSession

def transactional(func):
    """
    Декоратор для оборачивания функции в транзакцию.
    
    Если функция выбросит исключение → автоматический rollback
    Если успешно → автоматический commit
    """
    @wraps(func)
    async def wrapper(*args, db: AsyncSession = None, **kwargs):
        if db is None:
            raise ValueError("transactional requires 'db' parameter")
        
        try:
            async with db.begin():  # Начало транзакции
                return await func(*args, db=db, **kwargs)
        except Exception as e:
            # Автоматический rollback при ошибке
            await db.rollback()
            raise

    return wrapper

# Использование:

class ArticleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @transactional
    async def create_article(self, data: ArticleCreate, db: AsyncSession):
        """
        Создание статьи со всеми локализациями за раз.
        Либо все создается, либо ничего (atomic operation).
        """
        
        # Шаг 1: создаём article
        article = Article(
            tenant_id=data.tenant_id,
            title=data.title,
            slug=data.slug
        )
        db.add(article)
        
        # Шаг 2: создаём article_locales
        for locale_code, title in data.locales.items():
            locale = ArticleLocale(
                article_id=article.id,
                locale_code=locale_code,
                title=title
            )
            db.add(locale)
        
        # Если здесь упадет исключение → rollback всё (и article, и locales)
        # Если успех → commit всё за раз
        
        return article

# В роутере:
@admin_router.post("/articles")
async def create_article(
    data: ArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user)
):
    service = ArticleService(db)
    
    try:
        article = await service.create_article(data, db=db)
        
        logger.info("Article created", extra={
            "article_id": str(article.id),
            "user_id": str(current_user.id)
        })
        
        return {"data": article}
    
    except IntegrityError as e:
        logger.error("Failed to create article", extra={
            "error": str(e),
            "user_id": str(current_user.id)
        })
        raise HTTPException(
            status_code=422,
            detail="Failed to create article"
        )
```

**Более сложный пример с несколькими операциями:**

```python
class ArticleService:
    @transactional
    async def publish_article(self, article_id: UUID, db: AsyncSession):
        """
        Публикация статьи:
        1. Изменить статус
        2. Обновить SEO routes
        3. Добавить в очередь для индексации в поиск
        
        Если любой шаг упадет → откатываем всё
        """
        
        # Шаг 1: обновляем статью
        article = await db.get(Article, article_id)
        article.status = "published"
        article.published_at = datetime.utcnow()
        db.add(article)
        
        # Шаг 2: создаём SEO routes для каждой локали
        for locale in article.locales:
            seo_route = SEORoute(
                tenant_id=article.tenant_id,
                locale_id=locale.locale_id,
                path=f"/articles/{locale.slug}",
                title=locale.title,
                description=locale.description
            )
            db.add(seo_route)
        
        # Шаг 3: добавляем в очередь для индексации
        # (это может быть Message Queue внутри транзакции)
        search_task = SearchIndexTask(
            entity_type="article",
            entity_id=article.id,
            action="index"
        )
        db.add(search_task)
        
        # Если любой из шагов упадет → откатываем ALL
        # Либо все создается, либо ничего
        
        return article
```

**Альтернатива с context manager'ом:**

```python
# Если не хочешь использовать декоратор:

async def create_article(data: ArticleCreate, db: AsyncSession):
    async with db.begin():  # Начало транзакции
        # Все операции здесь
        article = Article(...)
        db.add(article)
        
        locale = ArticleLocale(...)
        db.add(locale)
        
        # Если ошибка → rollback
        # Если успех → commit
        
    return article
```

**Усилие:** 2 часа  
**Когда:** При создании use cases и сложных операций

---

## 🟡 Важные оптимизации

### 6. Индексы на публичные queries

**Суть:** Добавить индексы на часто используемые поля

**Проблема:**

```sql
-- Без индекса: FULL TABLE SCAN
SELECT * FROM articles 
WHERE tenant_id = '123' AND status = 'published'
ORDER BY created_at DESC

-- План:
Seq Scan on articles  (cost=0.00..500000.00 rows=1000000)
  Filter: (tenant_id = '123' AND status = 'published')

-- При 1М записей = 500ms!
```

**С индексом:**

```sql
-- С индексом: INDEX SCAN
SELECT * FROM articles 
WHERE tenant_id = '123' AND status = 'published'
ORDER BY created_at DESC

-- План:
Index Scan using idx_article_tenant_status_created on articles (cost=0.42..15.00 rows=50)
  Index Cond: (tenant_id = '123' AND status = 'published')

-- = 15ms! (33x ускорение)
```

**Добавляем индексы в модели:**

```python
from sqlalchemy import Index

class Article(Base, SoftDeleteMixin):
    __tablename__ = "articles"
    
    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    tenant_id: UUID = Column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    topic_id: UUID | None = Column(UUID(as_uuid=True), ForeignKey("topics.id"))
    title: str = Column(String(255), nullable=False)
    slug: str = Column(String(255), nullable=False)
    status: str = Column(String(50), nullable=False, default="draft")
    featured: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, server_default=func.now())
    published_at: datetime | None = Column(DateTime, nullable=True)
    deleted_at: datetime | None = Column(DateTime, nullable=True)
    
    __table_args__ = (
        # ← Индексы сюда
        
        # 1. Главный индекс для листингов
        Index(
            "idx_article_tenant_status_created",
            "tenant_id", "status", "created_at",
            name="idx_article_tenant_status_created"
        ),
        
        # 2. Для фильтра по topic_id
        Index(
            "idx_article_tenant_topic",
            "tenant_id", "topic_id", "status",
            name="idx_article_tenant_topic"
        ),
        
        # 3. Для поиска по slug
        Index(
            "idx_article_tenant_slug",
            "tenant_id", "slug",
            name="idx_article_tenant_slug"
        ),
        
        # 4. Для featured статей
        Index(
            "idx_article_featured",
            "tenant_id", "featured", "created_at",
            name="idx_article_featured"
        ),
        
        # 5. Для soft delete запросов
        Index(
            "idx_article_deleted_at",
            "deleted_at",
            name="idx_article_deleted_at"
        ),
    )

class Service(Base, SoftDeleteMixin):
    __table_args__ = (
        Index("idx_service_tenant_status", "tenant_id", "status"),
        Index("idx_service_tenant_slug", "tenant_id", "slug"),
        Index("idx_service_tenant_sort", "tenant_id", "sort_order"),
    )

class Employee(Base, SoftDeleteMixin):
    __table_args__ = (
        Index("idx_employee_tenant_status", "tenant_id", "is_active"),
        Index("idx_employee_tenant_slug", "tenant_id", "slug"),
    )

class Inquiry(Base):
    __table_args__ = (
        Index("idx_inquiry_tenant_status", "tenant_id", "status"),
        Index("idx_inquiry_tenant_created", "tenant_id", "created_at"),
        Index("idx_inquiry_tenant_form", "tenant_id", "form_id"),
        Index("idx_inquiry_email", "email"),  # Для поиска по почте
    )

class Review(Base, SoftDeleteMixin):
    __table_args__ = (
        Index("idx_review_tenant_status", "tenant_id", "status"),
        Index("idx_review_case_approved", "case_id", "status"),
    )
```

**Миграция:**

```python
# alembic/versions/003_add_indices.py
def upgrade():
    op.create_index(
        'idx_article_tenant_status_created',
        'articles',
        ['tenant_id', 'status', 'created_at']
    )
    op.create_index(
        'idx_article_tenant_topic',
        'articles',
        ['tenant_id', 'topic_id', 'status']
    )
    op.create_index(
        'idx_service_tenant_status',
        'services',
        ['tenant_id', 'status']
    )
    # ... остальное

def downgrade():
    op.drop_index('idx_article_tenant_status_created', 'articles')
    # ... остальное
```

**Усилие:** 2 часа  
**Когда:** При создании моделей, перед миграциями

---

### 7. Health Checks (детальные)

**Суть:** Endpoint который проверяет статус всех зависимостей

**Зачем:**

```
Kubernetes проверяет liveness/readiness probes:
  GET /health → 200 OK → Pod живой ✓
  
Мониторинг может отследить:
  GET /health → 200 OK с "database": "error"
  → Отправить alert: БД упала!
  
При рестарте контейнера:
  GET /health/ready → 503 (DB не доступна)
  → Kubernetes ждет 
  GET /health/ready → 200 OK
  → Начинает маршрутить трафик
```

**Реализация:**

```python
# app/modules/health/service.py
from datetime import datetime
import asyncio

class HealthCheckService:
    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis = redis_client
        self.start_time = datetime.utcnow()
    
    async def check_database(self) -> dict:
        """Проверка БД"""
        try:
            # Простой запрос для проверки соединения
            await self.db.execute(select(1))
            return {"status": "ok", "latency_ms": 5}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def check_redis(self) -> dict:
        """Проверка Redis"""
        try:
            await self.redis.ping()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def check_s3(self) -> dict:
        """Проверка S3"""
        try:
            # Список bucket'а
            s3_client = boto3.client('s3')
            s3_client.head_bucket(Bucket=os.getenv('S3_BUCKET'))
            return {"status": "ok"}
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "note": "S3 not critical for readiness"
            }
    
    def get_uptime(self) -> dict:
        """Время работы приложения"""
        uptime = datetime.utcnow() - self.start_time
        return {
            "uptime_seconds": int(uptime.total_seconds()),
            "started_at": self.start_time.isoformat()
        }
    
    async def get_full_status(self) -> dict:
        """Полный статус"""
        db_status = await self.check_database()
        redis_status = await self.check_redis()
        s3_status = await self.check_s3()
        uptime = self.get_uptime()
        
        # Общий статус: OK если все критичные компоненты OK
        overall = "ok"
        if db_status["status"] != "ok" or redis_status["status"] != "ok":
            overall = "degraded"
        
        return {
            "status": overall,
            "database": db_status,
            "redis": redis_status,
            "s3": s3_status,
            **uptime
        }

# app/api/v1/public/health.py
from fastapi import APIRouter, Depends, HTTPException
from app.core.database import get_db

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    GET /health
    → Основная проверка здоровья
    """
    service = HealthCheckService(db, redis_client)
    status = await service.get_full_status()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        **status
    }

@router.get("/live")
async def liveness_probe():
    """
    GET /health/live
    → Kubernetes liveness probe
    → Проверяет просто живой ли процесс
    """
    return {"status": "alive"}

@router.get("/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    GET /health/ready
    → Kubernetes readiness probe
    → Проверяет готовность принимать трафик
    """
    service = HealthCheckService(db, redis_client)
    
    db_status = await service.check_database()
    redis_status = await service.check_redis()
    
    # Если БД или Redis не доступны → не готовы
    if db_status["status"] != "ok" or redis_status["status"] != "ok":
        raise HTTPException(
            status_code=503,
            detail="Service unavailable - dependencies not ready"
        )
    
    return {"status": "ready"}
```

**Ответ:**

```json
// GET /health
{
  "status": "ok",
  "database": {"status": "ok", "latency_ms": 5},
  "redis": {"status": "ok"},
  "s3": {"status": "ok"},
  "uptime_seconds": 3600,
  "started_at": "2026-01-14T16:00:00",
  "timestamp": "2026-01-14T17:00:00"
}

// GET /health (если БД упала)
{
  "status": "degraded",
  "database": {"status": "error", "error": "Connection timeout"},
  "redis": {"status": "ok"},
  "s3": {"status": "ok"},
  "uptime_seconds": 3600,
  "started_at": "2026-01-14T16:00:00",
  "timestamp": "2026-01-14T17:00:00"
}

// GET /health/ready (если БД упала)
HTTP 503 Service Unavailable
{
  "detail": "Service unavailable - dependencies not ready"
}
```

**Kubernetes конфигурация:**

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cms-backend
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: cms-backend:latest
        
        # Liveness probe (перестартует если приложение зависло)
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        # Readiness probe (не маршрутит трафик если не готово)
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
```

**Усилие:** 2 часа  
**Когда:** Перед деплоем в production / Kubernetes

---

### 8. Request Logging Middleware

**Суть:** Логировать все входящие запросы (метод, путь, время, статус)

**Зачем:**

```
Production проблема:
  "API медленный! Какой endpoint упал?"
  
Без логирования:
  ¯\_(ツ)_/¯

С логированием:
  GET /api/v1/public/articles?status=published took 2500ms → 🚨 Slow!
  GET /api/v1/admin/services took 1200ms from user_123 → Тоже медленный
  POST /api/v1/public/inquiries got 500 error → БД упала
```

**Реализация:**

```python
# app/middleware/request_logging.py
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Генерируем уникальный request_id для отслеживания
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Начало замера времени
        start_time = time.time()
        
        # Логируем входящий запрос
        logger.info(
            f"Incoming {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_string": str(request.url.query),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", ""),
            }
        )
        
        try:
            # Обработка запроса
            response = await call_next(request)
            
            # Расчет времени
            duration_ms = (time.time() - start_time) * 1000
            
            # Логируем ответ
            log_level = "info"
            if response.status_code >= 500:
                log_level = "error"
            elif response.status_code >= 400:
                log_level = "warning"
            elif duration_ms > 1000:  # Медленный запрос
                log_level = "warning"
            
            getattr(logger, log_level)(
                f"Completed {request.method} {request.url.path} "
                f"with {response.status_code} in {duration_ms:.0f}ms",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": int(duration_ms),
                    "client_ip": request.client.host if request.client else "unknown",
                }
            )
            
            # Добавляем request_id в header ответа для отслеживания
            response.headers["X-Request-ID"] = request_id
            
            return response
        
        except Exception as e:
            # Логируем ошибки
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Exception in {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": int(duration_ms),
                    "error": str(e),
                    "client_ip": request.client.host if request.client else "unknown",
                },
                exc_info=True
            )
            raise

# app/main.py
from app.middleware.request_logging import RequestLoggingMiddleware

app = FastAPI()

# Добавляем middleware в начало (чтобы ловил все запросы)
app.add_middleware(RequestLoggingMiddleware)
```

**Результаты логирования:**

```json
{
  "timestamp": "2026-01-14T17:45:23.123Z",
  "level": "INFO",
  "message": "Incoming GET /api/v1/public/articles",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "path": "/api/v1/public/articles",
  "query_string": "status=published&locale=en",
  "client_ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

{
  "timestamp": "2026-01-14T17:45:23.267Z",
  "level": "INFO",
  "message": "Completed GET /api/v1/public/articles with 200 in 144ms",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "GET",
  "path": "/api/v1/public/articles",
  "status": 200,
  "duration_ms": 144,
  "client_ip": "192.168.1.100"
}
```

**Использование request_id в коде:**

```python
@admin_router.patch("/articles/{id}")
async def update_article(
    id: UUID,
    data: ArticleUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    request_id = request.state.request_id
    
    logger.info(
        f"Updating article {id}",
        extra={
            "request_id": request_id,
            "article_id": str(id)
        }
    )
    
    # ... логика обновления ...
    
    logger.info(
        f"Article {id} updated successfully",
        extra={
            "request_id": request_id,
            "article_id": str(id),
            "changes": ["title", "body"]
        }
    )
```

**Поиск в логах по request_id:**

```bash
# Найти все логи для одного запроса
grep "request_id: 550e8400-e29b-41d4-a716-446655440000" logs/app.json | jq .

# Результат покажет всю цепочку операций для этого запроса
```

**Усилие:** 2 часа  
**Когда:** Перед деплоем в production

---

### 9. Rate Limiting Pro (пользовательский)

**Суть:** Расширить текущий rate limit per IP на rate limit per user

**Текущее решение:**

```python
# Простой rate limit per IP
5 req/min per IP для /login
100 req/min per IP для публичных эндпоинтов

# Но проблемы:
- Админ из одного офиса (общий IP) → все 5 человек делят лимит
- Бот может менять IP → обходит лимит
```

**Улучшенное решение:**

```python
# app/core/rate_limit.py
import redis.asyncio as redis
from fastapi import HTTPException, Request, Depends

class RateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def check_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> bool:
        """
        Проверка лимита. Возвращает True если OK, False если превышен.
        """
        current = await self.redis.incr(key)
        
        if current == 1:
            # Первый запрос в этом окне
            await self.redis.expire(key, window_seconds)
        
        return current <= max_requests
    
    async def get_remaining(
        self,
        key: str,
        max_requests: int
    ) -> int:
        """Количество оставшихся запросов"""
        current = await self.redis.get(key)
        current = int(current) if current else 0
        return max(0, max_requests - current)

# Dependency'я для rate limit'а
async def rate_limit_public(
    request: Request,
    redis_client = Depends(get_redis)
):
    """Rate limit для публичного API (per IP)"""
    limiter = RateLimiter(redis_client)
    
    client_ip = request.client.host
    key = f"rl:public:{client_ip}"
    
    is_ok = await limiter.check_limit(
        key=key,
        max_requests=100,
        window_seconds=60  # 100 req/min
    )
    
    if not is_ok:
        remaining = await limiter.get_remaining(key, 100)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. "
                   f"Remaining requests: {remaining}",
            headers={
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": str(remaining),
                "Retry-After": "60",
            }
        )
    
    return True

async def rate_limit_login(
    request: Request,
    redis_client = Depends(get_redis)
):
    """Rate limit для login (per IP, строже)"""
    limiter = RateLimiter(redis_client)
    
    client_ip = request.client.host
    key = f"rl:login:{client_ip}"
    
    is_ok = await limiter.check_limit(
        key=key,
        max_requests=5,
        window_seconds=60  # 5 req/min (bruteforce protection)
    )
    
    if not is_ok:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": "60"}
        )
    
    return True

async def rate_limit_admin(
    request: Request,
    current_user: AdminUser = Depends(get_current_user),
    redis_client = Depends(get_redis)
):
    """Rate limit для админского API (per user)"""
    limiter = RateLimiter(redis_client)
    
    # Rate limit per user, не per IP
    key = f"rl:admin:{current_user.id}"
    
    is_ok = await limiter.check_limit(
        key=key,
        max_requests=1000,
        window_seconds=3600  # 1000 req/hour
    )
    
    if not is_ok:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded for your account. "
                   "Try again later.",
            headers={"Retry-After": "3600"}
        )
    
    return True

async def rate_limit_inquiry_form(
    request: Request,
    redis_client = Depends(get_redis)
):
    """Rate limit для формы заявки (очень строгий)"""
    limiter = RateLimiter(redis_client)
    
    # Rate limit + session tracking для spam protection
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    key = f"rl:inquiry:{client_ip}:{hash(user_agent)}"
    
    is_ok = await limiter.check_limit(
        key=key,
        max_requests=5,
        window_seconds=3600  # 5 заявок в час per IP
    )
    
    if not is_ok:
        raise HTTPException(
            status_code=429,
            detail="Too many submissions. Please try again later.",
            headers={"Retry-After": "3600"}
        )
    
    return True

# Использование в роутах:

# Public API
@public_router.get("/articles", dependencies=[Depends(rate_limit_public)])
async def get_articles():
    pass

# Login
@auth_router.post("/login", dependencies=[Depends(rate_limit_login)])
async def login(credentials: LoginRequest):
    pass

# Admin API
@admin_router.patch(
    "/articles/{id}",
    dependencies=[Depends(rate_limit_admin)]
)
async def update_article(id: UUID, data: ArticleUpdate):
    pass

# Form submission
@public_router.post(
    "/inquiries",
    dependencies=[Depends(rate_limit_inquiry_form)]
)
async def submit_inquiry(data: InquiryCreate):
    pass
```

**Усилие:** 3 часа  
**Когда:** После основного функционала

---

## 🟢 Nice-to-have фичи (v2+)

### 10. Full-Text Search (PostgreSQL)

```python
# Поиск по статьям, услугам, кейсам
GET /api/v1/public/search?q=consulting&locale=en

# Результат:
{
  "results": [
    {"type": "article", "title": "...", "slug": "..."},
    {"type": "service", "title": "...", "slug": "..."},
    {"type": "case", "title": "...", "slug": "..."}
  ]
}
```

**Усилие:** 4 часа  
**Когда:** После v1.0, если нужен поиск

---

### Дополнительные оптимизации:

**11. Database Partitioning** — партиционирование по tenant_id для больших таблиц

**12. Caching Layer** — Redis кэш для публичных эндпоинтов (GET /articles, /services)

**13. Webhooks** — события при создании/изменении сущностей

**14. Scheduled Publishing** — публикация статей по расписанию

**15. Email Templates** — управление шаблонами писем из админки

---

## Рекомендуемый MVP

### Неделя 1-2: Foundation + Укрепление
- [x] DB schema + Tenants
- [x] Auth (JWT) + RBAC
- [x] **Soft Delete на всех моделях** ← критичное
- [x] **DB Constraints + CheckConstraint'ы** ← критичное
- [x] **Индексы на публичные queries** ← критичное
- [x] **Transactional decorators** ← критичное
- [x] Audit Log

**Усилие:** 16-20 часов (1-2 недели)

### Неделя 3: Company Module
- [ ] Services + Employees
- [ ] Practice Areas
- [ ] Advantages
- [ ] Locales + Localization

### Неделя 4: Content Module
- [ ] Articles + Topics
- [ ] FAQ

### Неделя 5: Leads Module
- [ ] Inquiry Forms + Inquiries
- [ ] Базовая аналитика (source_url, utm, device)

### Неделя 6: SEO Module
- [ ] SEO Routes (мета, og, canonical)
- [ ] Sitemap + robots.txt
- [ ] Redirects

### Неделя 7-8: Polish + DevOps
- [x] **Structured Logging (JSON)** ← важное
- [x] **Request Logging Middleware** ← важное
- [x] **Health Checks (детальные)** ← важное
- [ ] Rate Limiting
- [ ] Cache Headers
- [ ] Docker Deployment
- [ ] Documentation

**На v1.1 отложить:**
- Cases + Reviews (feature flag)
- Webhooks
- Scheduled Publishing
- Email Templates Management
- Full-Text Search

---

## Планирование и сроки

### Время на реализацию критичных улучшений:

| # | Улучшение | Часов | Неделя |
|---|-----------|-------|--------|
| 1 | Soft Delete | 2-3 | 1 |
| 2 | Optimistic Locking | 2 | 1 |
| 3 | DB Constraints | 2 | 1 |
| 4 | Индексы | 2 | 1 |
| 5 | Transactional Decorators | 2 | 1 |
| 6 | Structured Logging | 3 | 2 |
| 7 | Request Logging | 2 | 2 |
| 8 | Health Checks | 2 | 2 |
| **TOTAL** | | **17-18** | **2 нед** |

### Параллельная разработка:

**Неделя 1:** Foundation + Soft Delete, Constraints, Индексы  
**Неделя 2:** Company Module + Logging, Health Checks  
**Неделя 3:** Content Module  
**Неделя 4:** Leads Module  
**Неделя 5:** SEO Module  
**Неделя 6-7:** Polish + Deploy  
**Неделя 8:** Buffer + Фиксы + Документация  

---

## Checklist перед production

- [ ] Soft Delete на всех основных моделях
- [ ] DB Constraints + CheckConstraint'ы
- [ ] Индексы на все часто используемые поля
- [ ] Optimistic Locking на Article и Case
- [ ] Transactional Decorators на все use cases
- [ ] Structured JSON Logging
- [ ] Request Logging Middleware
- [ ] Health Checks (/health, /health/live, /health/ready)
- [ ] Rate Limiting (публичный API + login + inquiries)
- [ ] Cache Headers на публичный API
- [ ] Логирование исключений с traceback'ом
- [ ] Мониторинг slow queries (>1s)
- [ ] Docker image оптимизирован
- [ ] .env.example заполнен
- [ ] README с инструкциями деплоя
- [ ] API документация (OpenAPI/Swagger)
- [ ] Тесты интеграции основных flow'ов

---

## Ссылки и ресурсы

### PostgreSQL оптимизация:
- [PostgreSQL Indexes Best Practices](https://www.postgresql.org/docs/current/sql-createindex.html)
- [Check Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-CHECK-CONSTRAINTS)

### Логирование:
- [python-json-logger](https://github.com/madzak/python-json-logger)
- [Structured Logging Best Practices](https://www.kartar.net/2015/12/structured-logging/)

### Performance:
- [SQLAlchemy Query Optimization](https://docs.sqlalchemy.org/en/20/orm/query.html)
- [PostgreSQL Query Planning](https://www.postgresql.org/docs/current/sql-explain.html)

### Testing:
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-websockets/)

---

**Версия документа:** v1.0  
**Дата создания:** 14 января 2026  
**Статус:** ✅ Готово к реализации  
**Время на реализацию:** 8-9 недель (включая укрепления v1)
