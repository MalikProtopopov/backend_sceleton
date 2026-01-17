# 🧪 FastAPI Backend Testing Strategy & Implementation Guide

**Дата:** 14 января 2026  
**Для:** Corporate CMS Engine v1.0  
**Статус:** ✅ Готово к реализации  
**Область:** Unit + Integration + E2E тестирование FastAPI/PostgreSQL/AsyncIO  

---

## 📋 Оглавление

1. [Test Strategy (Пирамида тестов)](#test-strategy-пирамида-тестов)
2. [Рекомендуемый стек инструментов](#рекомендуемый-стек-инструментов)
3. [Структура репозитория для тестов](#структура-репозитория-для-тестов)
4. [База данных в тестах (2 варианта)](#база-данных-в-тестах-2-варианта)
5. [FastAPI Testing Patterns](#fastapi-testing-patterns)
6. [Data Factories и генерация тестовых данных](#data-factories-и-генерация-тестовых-данных)
7. [Примеры кода (реальные шаблоны)](#примеры-кода-реальные-шаблоны)
8. [CI/CD рекомендации](#cicd-рекомендации)
9. [Definition of Done (DoD)](#definition-of-done-dod)
10. [Чек-лист внедрения по этапам](#чек-лист-внедрения-по-этапам)

---

## Test Strategy (Пирамида тестов)

### 📊 Рекомендуемое распределение

```
                   /\
                  /  \
                 / E2E \        5-10% (2-5 тестов на фичу)
                /______\       
               /        \
              / Integration\  30-40% (основное покрытие БД)
             /            \  
            /______/\______\
           /        /  \    \
          / Unit   /    \    \  50-60% (бизнес-логика, валидация)
         /________/______\____\
         
TOTAL: ~100 тестов на небольшой проект (100K LOC)
       ~500+ на enterprise (500K+ LOC)
```

### 🎯 Что тестировать где

| Тип | % | Что | Инструменты | Скорость |
|-----|---|-----|------------|----------|
| **Unit** | 50-60% | Сервисы, репозитории, валидация, бизнес-логика | pytest + unittest.mock | <100ms |
| **Integration** | 30-40% | API endpoints, БД transactions, миграции | pytest + TestClient + Postgres | 100ms-1s |
| **E2E** | 5-10% | Полные юзкейсы, flow's (create→read→update) | pytest + TestClient + Postgres | 1-5s |
| **Contract** | 5% | Внешние интеграции (если есть) | requests-mock + pact | <500ms |

---

## Рекомендуемый стек инструментов

### 📦 Core Testing Stack

```yaml
pytest: "^7.4.0"                    # Фреймворк для тестов (заменяет unittest)
pytest-asyncio: "^0.21.0"           # Async/await support
pytest-cov: "^4.1.0"                # Coverage reporting
pytest-xdist: "^3.3.0"              # Параллельное выполнение тестов
httpx: "^0.24.0"                    # Async HTTP client для API тестов

# ДЛЯ МОКОВ И ФАБРИК
unittest.mock: "builtin"            # Встроенный mocking
pytest-mock: "^3.11.0"              # Удобный wrapper
factory-boy: "^3.3.0"               # Фабрики для тестовых данных
faker: "^19.0.0"                    # Генерация фейковых данных

# ДЛЯ БД
pytest-postgresql: "^5.0.0"         # Фикстуры для Postgres
sqlalchemy: "^2.0.0"                # ORM + async support
alembic: "^1.12.0"                  # Миграции БД

# ОПЦИОНАЛЬНО (но рекомендуется)
testcontainers: "^3.7.0"            # Docker контейнеры для тестов (PostgreSQL, Redis, MinIO)
pytest-env: "^1.0.0"                # Переменные окружения в тестах
pytest-benchmark: "^4.0.0"          # Бенчмарки для slow тестов
pydantic: "^2.0.0"                  # Валидация (уже есть)
python-jose[cryptography]: "^3.3"   # JWT для auth тестов

# COVERAGE И LINTING
coverage: "^7.2.0"                  # Анализ покрытия
pytest-cov: "^4.1.0"                # Плагин для pytest
black: "^23.0.0"                    # Code formatting
flake8: "^6.0.0"                    # Linting (опционально, если не используется ruff)
ruff: "^0.0.280"                    # Faster linter + formatter

# ДЛЯ CI/CD
pytest-timeout: "^2.1.0"            # Таймауты для долгих тестов
pytest-repeat: "^0.9.0"             # Повторное выполнение flaky тестов
```

### Версионирование по Python

```toml
# pyproject.toml
[project]
name = "corporate-cms-backend"
version = "1.0.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
# Детали в следующих разделах
```

---

## Структура репозитория для тестов

### 📁 Папки проекта

```
corporate-cms-backend/
├── app/                          # ← Исходный код
│   ├── main.py
│   ├── config.py
│   ├── core/
│   │   ├── database.py
│   │   ├── security.py
│   │   └── ...
│   ├── modules/
│   │   ├── auth/
│   │   ├── content/
│   │   └── ...
│   └── api/
│       └── v1/
│
├── tests/                        # ← ТЕСТЫ (это то, что нам нужно создать)
│   ├── __init__.py
│   ├── conftest.py               # ← ГЛАВНЫЙ файл для фикстур
│   ├── pytest.ini                # ← Конфигурация pytest
│   │
│   ├── unit/                     # Unit tests (без БД, только бизнес-логика)
│   │   ├── __init__.py
│   │   ├── test_auth_service.py         # Тесты сервисов
│   │   ├── test_content_service.py
│   │   ├── test_validators.py           # Валидация
│   │   ├── test_utils.py                # Утилиты
│   │   └── mocks/                       # Моки для unit тестов
│   │       └── __init__.py
│   │
│   ├── integration/              # Integration tests (с БД, с реальными сервисами)
│   │   ├── __init__.py
│   │   ├── test_article_repository.py   # Тесты репозиториев (БД)
│   │   ├── test_service_repository.py
│   │   ├── test_migrations.py           # Миграции
│   │   └── fixtures/                    # Фабрики и фикстуры для БД
│   │       ├── __init__.py
│   │       ├── factories.py             # Factory Boy factories
│   │       └── seeders.py               # Инициализация тестовых данных
│   │
│   ├── api/                      # API tests (тестирование эндпоинтов)
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── test_articles_api.py     # GET /articles, POST /articles, etc
│   │   │   ├── test_services_api.py
│   │   │   ├── test_auth_api.py         # POST /login, /refresh
│   │   │   ├── test_inquiries_api.py
│   │   │   ├── test_seo_api.py
│   │   │   └── common/
│   │   │       ├── __init__.py
│   │   │       └── test_error_handling.py  # 400/422/404/409/429 тесты
│   │   └── fixtures/
│   │       └── api_fixtures.py          # Переопределение зависимостей
│   │
│   ├── e2e/                      # E2E tests (полные сценарии)
│   │   ├── __init__.py
│   │   ├── test_article_workflow.py     # create → read → update → delete
│   │   ├── test_leads_workflow.py       # submit inquiry → get analytics
│   │   └── test_seo_workflow.py         # publish article → check sitemap
│   │
│   ├── performance/              # Бенчмарки и load-тесты (если нужны)
│   │   └── test_query_performance.py
│   │
│   └── data/                     # Фикстурные данные (JSON/CSV для сложных тестов)
│       ├── articles.json
│       └── inquiries.json
│
├── .env.test                     # Конфиг для тестов (раздельная БД)
├── .env.test.ci                  # Конфиг для CI (Docker Postgres)
├── pytest.ini                    # Конфигурация pytest
├── pyproject.toml                # Зависимости
└── docker-compose.test.yml       # Docker для тестовой БД (опционально)
```

### 📝 Конвенции именования

```python
# Unit tests
test_<function_name>.py           # test_validate_email.py
test_<class_name>.py              # test_ArticleService.py

class Test<Class>:
    def test_<method>_<scenario>(self):  # test_create_article_with_valid_data

# Integration tests
test_<repository>_repository.py   # test_article_repository.py
test_<migrations>.py              # test_migrations_001_add_articles.py

# API tests
test_<resource>_api.py            # test_articles_api.py

class Test<Resource>:
    def test_get_<resource>_<scenario>(self):  # test_get_articles_published_only
    def test_create_<resource>_<scenario>(self):
    def test_update_<resource>_<scenario>(self):

# E2E tests
test_<workflow>_workflow.py       # test_article_workflow.py
```

---

## 📁 Конфиг файлы

### pytest.ini

```ini
[pytest]
# Основное
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Маркеры
markers =
    unit: unit tests (no external dependencies)
    integration: integration tests (with database)
    api: API endpoint tests
    e2e: end-to-end tests
    slow: slow tests (>1s)
    db: tests that touch database
    auth: authentication tests
    skip_ci: skip in CI (only local)
    smoke: smoke tests (quick sanity checks)

# Асинк
asyncio_mode = auto
asyncio_default_fixture_scope = function

# Timeout
timeout = 30
timeout_method = thread

# Output
addopts =
    -v
    --strict-markers
    --tb=short
    --color=yes
    --code-highlight=yes
    -ra
    --durations=10

# Coverage
[coverage:run]
source = app
omit =
    */migrations/*
    */tests/*
    */__pycache__/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    @abstractmethod
```

### .env.test

```bash
# БД для тестов
DATABASE_URL=postgresql+asyncpg://test_user:test_password@localhost:5432/test_cms_db
DATABASE_URL_SYNC=postgresql://test_user:test_password@localhost:5432/test_cms_db

# Redis (если используется)
REDIS_URL=redis://localhost:6379/1

# Auth
SECRET_KEY=test-secret-key-do-not-use-in-production
ALGORITHM=HS256

# S3 (MinIO для тестов)
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=test-bucket
S3_REGION=us-east-1

# Email (mock)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=test
SMTP_PASSWORD=test

# Telegram (mock)
TELEGRAM_BOT_TOKEN=test-token
TELEGRAM_CHAT_ID=test-chat

# Environment
ENVIRONMENT=test
LOG_LEVEL=WARNING
```

### docker-compose.test.yml (опционально, для Testcontainers)

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
      POSTGRES_DB: test_cms_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_test_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio:latest
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    command: server /data --console-address ":9001"

volumes:
  postgres_test_data:
```

---

## База данных в тестах (2 варианта)

### ✅ Вариант 1: Транзакции + Rollback (быстро, для локальной разработки)

**Как работает:**

```
Каждый тест:
1. BEGIN TRANSACTION (или SAVEPOINT)
2. Вставляем данные
3. Тестируем
4. ROLLBACK (откатываем все изменения)
5. БД остается чистой

Плюсы:
✓ Очень быстро (100-200ms на тест)
✓ Гарантированно чистая БД между тестами
✓ Простая реализация
✓ Тесты работают параллельно с разными DB connections

Минусы:
✗ Не ловит баги с commit/flush на лету
✗ Не совпадает с поведением production (где нет rollback)
✗ Сложнее тестировать транзакции в самом коде
```

**Реализация:**

```python
# tests/conftest.py
import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Event loop для всей сессии тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def async_engine():
    """Создание engine для БД"""
    engine = create_async_engine(
        "postgresql+asyncpg://test_user:test_password@localhost/test_cms_db",
        echo=False,
        future=True,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(async_engine):
    """
    Фикстура для БД сессии с автоматическим rollback'ом.
    Для каждого теста создаём новую сессию в транзакции.
    """
    async with async_engine.begin() as connection:
        transaction = await connection.begin_nested()  # SAVEPOINT
        
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
        )
        
        try:
            yield session
        finally:
            await transaction.rollback()  # Откатываем все изменения
            await session.close()

@pytest.fixture
def override_get_db(db_session):
    """Переопределение зависимости get_db"""
    def _override():
        return db_session
    return _override
```

**Использование в тесте:**

```python
@pytest.mark.asyncio
async def test_create_article(db_session):
    """Тест создания статьи"""
    
    # 1. Вставляем тестовые данные (будет откачено при rollback)
    article = Article(
        tenant_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        title="Test Article",
        slug="test-article",
        status="published"
    )
    db_session.add(article)
    await db_session.flush()
    
    # 2. Тестируем
    retrieved = await db_session.get(Article, article.id)
    assert retrieved.title == "Test Article"
    
    # 3. ROLLBACK автоматический (БД чистая)
```

---

### ✅ Вариант 2: Testcontainers (максимально близко к prod, медленнее)

**Как работает:**

```
Перед запуском тестов:
1. Docker запускает PostgreSQL контейнер
2. Прогоняются миграции (alembic upgrade head)
3. Тесты создают данные (без rollback)
4. После тестов контейнер удаляется

Плюсы:
✓ 100% совпадает с production окружением
✓ Ловит реальные баги с транзакциями/concurrency
✓ Можно тестировать миграции
✓ Легче отладить в случае падения

Минусы:
✗ Медленно (контейнер запускается 10-20s)
✗ Нужен Docker
✗ Параллелизм сложнее (нужны разные БД для разных workers)
✗ На CI медленнее
```

**Реализация с Testcontainers:**

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio

@pytest.fixture(scope="session")
def postgres_container():
    """
    Поднимаем Docker контейнер PostgreSQL перед всеми тестами.
    После тестов удаляем контейнер.
    """
    container = PostgresContainer(
        image="postgres:15",
        user="test_user",
        password="test_password",
        dbname="test_cms_db",
        port=5432,
    )
    container.start()
    
    # Ждем пока БД будет доступна
    import time
    time.sleep(2)
    
    yield container
    
    container.stop()

@pytest.fixture(scope="session")
async def async_engine(postgres_container):
    """Engine для PostgreSQL контейнера"""
    database_url = postgres_container.get_connection_url()
    
    engine = create_async_engine(
        database_url.replace("postgresql://", "postgresql+asyncpg://"),
        echo=False,
    )
    
    # Прогоняем миграции
    await run_migrations(engine)
    
    yield engine
    await engine.dispose()

async def run_migrations(engine):
    """Прогон миграций Alembic"""
    from alembic import command
    from alembic.config import Config
    
    alembic_cfg = Config("alembic.ini")
    
    # Обновляем database URL в alembic.ini временно
    command.upgrade(alembic_cfg, "head")

@pytest.fixture(scope="function")
async def db_session(async_engine):
    """
    Для каждого теста создаём новую транзакцию,
    но БД данные остаются (не откатываем).
    После теста — удаляем все данные.
    """
    async with AsyncSession(async_engine) as session:
        async with session.begin():
            yield session
            
            # Cleanup после теста (удаляем все данные)
            # ТОЛЬКО если нужно, иначе оставляем как есть
            # await session.query(Article).delete()
            # await session.query(Service).delete()
```

---

### 🤔 Какой выбрать?

| Критерий | Вариант 1 (Rollback) | Вариант 2 (Testcontainers) |
|----------|---------------------|---------------------------|
| **Скорость** | ⚡⚡⚡ 100ms/тест | ⚡ 1-2s/тест |
| **Простота** | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Близость к prod** | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Параллелизм** | ✓ Легко | ✗ Сложно |
| **CI/CD** | ✓ Быстро | ✗ Долго |
| **Локальная разработка** | ✓ Можно без Docker | ✗ Нужен Docker |
| **Тестирование миграций** | ✗ Сложно | ✓ Легко |

**РЕКОМЕНДАЦИЯ:**
- **Локальная разработка:** Вариант 1 (Rollback) — быстро, удобно
- **CI/CD:** Вариант 1 (Rollback) + smoke-тесты Вариант 2
- **Миграции:** Отдельные интеграционные тесты (Вариант 2)

---

## FastAPI Testing Patterns

### 1️⃣ Поднятие приложения для тестов

```python
# tests/conftest.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def app() -> FastAPI:
    """Создание FastAPI приложения для тестов"""
    from app.main import create_app
    return create_app()

@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """TestClient для синхронных тестов"""
    return TestClient(app)

# Для асинк тестов:
@pytest.fixture
async def async_client(app: FastAPI):
    """Async client для асинк тестов"""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
```

### 2️⃣ Переопределение зависимостей (Dependency Injection)

**Главная идея:** FastAPI позволяет переопределять зависимости в тестах.

```python
# tests/conftest.py
from fastapi import Depends
from app.core.database import get_db
from app.core.security import get_current_user

@pytest.fixture
def override_get_db(db_session):
    """Переопределение зависимости get_db"""
    async def _override():
        return db_session
    return _override

@pytest.fixture
def override_get_current_user():
    """Переопределение зависимости get_current_user"""
    async def _override(token: str = Depends(...)):
        # Возвращаем фейкового пользователя
        return AdminUser(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            tenant_id=UUID("660e8400-e29b-41d4-a716-446655440001"),
            email="test@example.com",
            role="admin"
        )
    return _override

@pytest.fixture
def app_with_overrides(app, override_get_db, override_get_current_user):
    """Приложение с переопределенными зависимостями"""
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    yield app
    
    # Очищаем переопределения после теста
    app.dependency_overrides.clear()

@pytest.fixture
def client(app_with_overrides: FastAPI):
    """TestClient с переопределениями"""
    return TestClient(app_with_overrides)
```

### 3️⃣ Тестирование ошибок и валидации

```python
# tests/api/v1/test_articles_api.py
def test_create_article_validation_error(client: TestClient):
    """Тест ошибки валидации (422)"""
    
    response = client.post(
        "/api/v1/admin/articles",
        json={
            # Missing 'title' — обязательное поле
            "slug": "test-article",
            "body": "Test"
        },
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("title" in str(error) for error in data["detail"])

def test_create_article_conflict(client: TestClient, db_session):
    """Тест конфликта (409) — статья уже существует"""
    
    # Создаем первую статью
    client.post(
        "/api/v1/admin/articles",
        json={
            "title": "Test",
            "slug": "test-article",
            "body": "Test"
        }
    )
    
    # Пытаемся создать вторую с тем же slug
    response = client.post(
        "/api/v1/admin/articles",
        json={
            "title": "Test 2",
            "slug": "test-article",  # ← Дублирование slug
            "body": "Test"
        }
    )
    
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

def test_not_found(client: TestClient):
    """Тест Not Found (404)"""
    
    fake_id = UUID("00000000-0000-0000-0000-000000000000")
    response = client.get(f"/api/v1/admin/articles/{fake_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

### 4️⃣ Тестирование авторизации и прав доступа

```python
# tests/api/v1/test_auth_api.py
def test_public_endpoint_without_auth(client: TestClient):
    """Public endpoint должен работать без auth"""
    response = client.get("/api/v1/public/articles")
    assert response.status_code == 200

def test_admin_endpoint_without_auth(client: TestClient):
    """Admin endpoint без auth должен возвращать 401"""
    response = client.post(
        "/api/v1/admin/articles",
        json={"title": "Test", "slug": "test", "body": "Test"}
    )
    assert response.status_code == 401

def test_forbidden_for_low_role(client: TestClient):
    """Пользователь с низкой ролью не может делать админские действия"""
    
    # Переопределяем текущего пользователя (content_manager, не admin)
    def override_current_user_low_role():
        return AdminUser(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            tenant_id=UUID("660e8400-e29b-41d4-a716-446655440001"),
            email="manager@example.com",
            role="content_manager"  # ← Low privilege
        )
    
    client.app.dependency_overrides[get_current_user] = override_current_user_low_role
    
    # Пытаемся удалить статью (требует 'admin')
    response = client.delete("/api/v1/admin/articles/some-id")
    
    assert response.status_code == 403
    assert "Permission denied" in response.json()["detail"]
```

### 5️⃣ Тестирование параметров запроса (pagination, filtering, sorting)

```python
# tests/api/v1/test_articles_api.py
@pytest.mark.asyncio
async def test_get_articles_with_pagination(
    async_client: AsyncClient,
    db_session
):
    """Тестирование пагинации"""
    
    # Создаём 25 статей
    for i in range(25):
        article = Article(
            tenant_id=TENANT_ID,
            title=f"Article {i}",
            slug=f"article-{i}",
            status="published"
        )
        db_session.add(article)
    await db_session.commit()
    
    # Тест: первая страница, 20 на странице
    response = await async_client.get(
        "/api/v1/public/articles",
        params={"page": 1, "limit": 20, "locale": "en"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["page"] == 1
    assert data["meta"]["limit"] == 20
    assert data["meta"]["total"] == 25
    assert data["meta"]["pages"] == 2
    assert data["meta"]["has_next"] == True
    assert len(data["data"]) == 20

def test_get_articles_with_filter(client: TestClient, db_session):
    """Тестирование фильтра"""
    
    # Создаём статьи с разными статусами
    article1 = Article(..., status="published")
    article2 = Article(..., status="draft")
    db_session.add_all([article1, article2])
    db_session.commit()
    
    # Тест: только published
    response = client.get(
        "/api/v1/public/articles",
        params={"status": "published", "locale": "en"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert all(item["status"] == "published" for item in data["data"])

def test_get_articles_with_sorting(client: TestClient):
    """Тестирование сортировки"""
    
    response = client.get(
        "/api/v1/public/articles",
        params={"sort": "-created_at", "locale": "en"}  # DESC by created_at
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что отсортировано в убывающем порядке
    dates = [article["created_at"] for article in data["data"]]
    assert dates == sorted(dates, reverse=True)
```

---

## Data Factories и генерация тестовых данных

### 🏭 Factory Boy + Faker

```python
# tests/integration/fixtures/factories.py
import factory
from faker import Faker
from uuid import uuid4
from datetime import datetime

fake = Faker('ru_RU')

# TENANT фабрика
class TenantFactory(factory.Factory):
    class Meta:
        model = Tenant
    
    id = factory.LazyFunction(uuid4)
    slug = factory.LazyFunction(lambda: fake.slug())
    name = factory.LazyFunction(lambda: fake.company())
    plan = factory.Faker('random_element', elements=['starter', 'pro', 'enterprise'])
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)

# ADMIN USER фабрика
class AdminUserFactory(factory.Factory):
    class Meta:
        model = AdminUser
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.SubFactory(TenantFactory)
    email = factory.Faker('email')
    password_hash = "hashed_password"
    role = factory.Faker('random_element', elements=['admin', 'content_manager', 'marketer'])
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)

# ARTICLE фабрика
class ArticleFactory(factory.Factory):
    class Meta:
        model = Article
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.SubFactory(TenantFactory)
    title = factory.Faker('sentence', nb_words=6)
    slug = factory.LazyAttribute(lambda o: fake.slug())
    body = factory.Faker('text', max_nb_chars=500)
    status = factory.Faker('random_element', elements=['draft', 'published', 'archived'])
    featured = False
    created_at = factory.LazyFunction(datetime.utcnow)
    published_at = factory.LazyFunction(lambda: datetime.utcnow() if factory.Faker('boolean') else None)
    deleted_at = None

# SERVICE фабрика
class ServiceFactory(factory.Factory):
    class Meta:
        model = Service
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.SubFactory(TenantFactory)
    name = factory.Faker('word')
    slug = factory.LazyAttribute(lambda o: fake.slug())
    status = 'published'
    icon_url = factory.Faker('image_url')
    sort_order = factory.Sequence(lambda n: n)

# INQUIRY фабрика (с аналитикой)
class InquiryFactory(factory.Factory):
    class Meta:
        model = Inquiry
    
    id = factory.LazyFunction(uuid4)
    tenant_id = factory.SubFactory(TenantFactory)
    form_id = factory.SubFactory(InquiryFormFactory)
    
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    message = factory.Faker('text', max_nb_chars=200)
    status = 'new'
    
    # Аналитика
    source_url = factory.Faker('url')
    referrer = factory.Faker('url')
    utm_source = factory.Faker('word')
    utm_medium = factory.Faker('word')
    utm_campaign = factory.Faker('word')
    ip_address = factory.Faker('ipv4')
    device_type = factory.Faker('random_element', elements=['desktop', 'mobile', 'tablet'])
    created_at = factory.LazyFunction(datetime.utcnow)
```

**Использование в тестах:**

```python
# tests/integration/test_article_repository.py
@pytest.mark.asyncio
async def test_get_articles_by_tenant(db_session):
    """Тест получения статей по тенанту"""
    
    # Создаём тестовые данные с фабриками
    tenant1 = TenantFactory.build()
    tenant2 = TenantFactory.build()
    
    articles_t1 = [ArticleFactory.build(tenant_id=tenant1.id) for _ in range(3)]
    articles_t2 = [ArticleFactory.build(tenant_id=tenant2.id) for _ in range(2)]
    
    # Сохраняем в БД
    db_session.add_all([tenant1, tenant2] + articles_t1 + articles_t2)
    await db_session.flush()
    
    # Тестируем
    repository = ArticleRepository(db_session)
    result = await repository.get_by_tenant(tenant1.id)
    
    assert len(result) == 3
    assert all(a.tenant_id == tenant1.id for a in result)
```

### 🧹 Как избежать Flaky тестов

```python
# ❌ ПЛОХО (Flaky):
def test_article_created_at(db_session):
    article = ArticleFactory.build()
    db_session.add(article)
    db_session.commit()
    
    # Проблема: time.sleep нужен для того чтобы дата точно совпала
    import time
    time.sleep(0.1)
    
    # Может упасть если выполнится в разные миллисекунды
    assert article.created_at == datetime.utcnow()

# ✅ ХОРОШО (Deterministic):
def test_article_created_at(db_session):
    article = ArticleFactory.build()
    db_session.add(article)
    db_session.commit()
    
    # Проверяем только что дата в правильном диапазоне
    now = datetime.utcnow()
    assert (now - article.created_at).total_seconds() < 1

# ❌ ПЛОХО (Flaky — случайность):
def test_random_user():
    # Генерируем случайный email каждый раз
    user = UserFactory.build(email=fake.email())
    assert user.email  # Может быть None!

# ✅ ХОРОШО:
def test_user_has_email():
    # Используем фабрику (гарантирует корректные данные)
    user = UserFactory.build()
    assert user.email
    assert "@" in user.email

# ❌ ПЛОХО (Порядок зависит от других тестов):
def test_articles_count(db_session):
    count = db_session.query(Article).count()
    assert count == 5  # Может быть 3 если другие тесты не откатились

# ✅ ХОРОШО (Независимо от других):
def test_articles_count(db_session):
    # Создаём свои данные
    for _ in range(5):
        ArticleFactory.create(session=db_session)
    
    count = db_session.query(Article).count()
    assert count == 5
```

---

## Примеры кода (реальные шаблоны)

### 1️⃣ Unit Test сервиса (без БД)

```python
# app/modules/content/service.py (исходный код)
class ArticleService:
    def __init__(self, repository: ArticleRepository):
        self.repository = repository
    
    async def publish_article(self, article_id: UUID) -> Article:
        """Публикация статьи"""
        article = await self.repository.get_by_id(article_id)
        
        if article is None:
            raise NotFoundError(f"Article {article_id} not found")
        
        if article.status == "published":
            raise ValidationError("Article is already published")
        
        article.status = "published"
        article.published_at = datetime.utcnow()
        
        return await self.repository.save(article)

# tests/unit/test_content_service.py
from unittest.mock import Mock, AsyncMock
import pytest

class TestArticleService:
    
    @pytest.fixture
    def mock_repository(self):
        """Mock репозитория"""
        return Mock(spec=ArticleRepository)
    
    @pytest.fixture
    def service(self, mock_repository):
        """Service с mocked репозиторием"""
        return ArticleService(repository=mock_repository)
    
    @pytest.mark.asyncio
    async def test_publish_article_success(self, service, mock_repository):
        """Тест успешной публикации"""
        
        # Arrange
        article = Article(
            id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            title="Test",
            slug="test",
            status="draft"
        )
        mock_repository.get_by_id = AsyncMock(return_value=article)
        mock_repository.save = AsyncMock(return_value=article)
        
        # Act
        result = await service.publish_article(article.id)
        
        # Assert
        assert result.status == "published"
        assert result.published_at is not None
        mock_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_article_not_found(self, service, mock_repository):
        """Тест публикации несуществующей статьи"""
        
        # Arrange
        fake_id = UUID("00000000-0000-0000-0000-000000000000")
        mock_repository.get_by_id = AsyncMock(return_value=None)
        
        # Act & Assert
        with pytest.raises(NotFoundError):
            await service.publish_article(fake_id)
    
    @pytest.mark.asyncio
    async def test_publish_already_published(self, service, mock_repository):
        """Тест публикации уже опубликованной статьи"""
        
        # Arrange
        article = Article(status="published")
        mock_repository.get_by_id = AsyncMock(return_value=article)
        
        # Act & Assert
        with pytest.raises(ValidationError, match="already published"):
            await service.publish_article(article.id)
```

### 2️⃣ Integration Test репозитория с Postgres

```python
# tests/integration/test_article_repository.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

class TestArticleRepository:
    
    @pytest.fixture
    async def article(self, db_session: AsyncSession):
        """Создаём тестовую статью"""
        article = Article(
            tenant_id=TENANT_ID,
            title="Test Article",
            slug="test-article",
            status="draft"
        )
        db_session.add(article)
        await db_session.flush()
        return article
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session: AsyncSession, article: Article):
        """Тест получения статьи по ID"""
        
        repository = ArticleRepository(db_session)
        result = await repository.get_by_id(article.id)
        
        assert result is not None
        assert result.id == article.id
        assert result.title == "Test Article"
    
    @pytest.mark.asyncio
    async def test_get_by_slug(self, db_session: AsyncSession, article: Article):
        """Тест получения статьи по slug"""
        
        repository = ArticleRepository(db_session)
        result = await repository.get_by_slug(TENANT_ID, "test-article")
        
        assert result is not None
        assert result.slug == "test-article"
    
    @pytest.mark.asyncio
    async def test_list_by_tenant(self, db_session: AsyncSession):
        """Тест получения списка статей по тенанту"""
        
        # Создаём несколько статей
        articles = [
            Article(tenant_id=TENANT_ID, title=f"Article {i}", slug=f"article-{i}")
            for i in range(3)
        ]
        db_session.add_all(articles)
        await db_session.flush()
        
        repository = ArticleRepository(db_session)
        result = await repository.list_by_tenant(TENANT_ID)
        
        assert len(result) == 3
        assert all(a.tenant_id == TENANT_ID for a in result)
    
    @pytest.mark.asyncio
    async def test_update(self, db_session: AsyncSession, article: Article):
        """Тест обновления статьи"""
        
        repository = ArticleRepository(db_session)
        
        article.title = "Updated Title"
        updated = await repository.save(article)
        
        # Проверяем, что изменения сохранены
        await db_session.refresh(article)
        assert article.title == "Updated Title"
    
    @pytest.mark.asyncio
    async def test_soft_delete(self, db_session: AsyncSession, article: Article):
        """Тест мягкого удаления"""
        
        repository = ArticleRepository(db_session)
        await repository.soft_delete(article.id)
        
        # Проверяем, что deleted_at установлен
        await db_session.refresh(article)
        assert article.deleted_at is not None
        
        # Проверяем, что при запросе не возвращается
        result = await repository.get_by_id(article.id)
        assert result is None
```

### 3️⃣ API Test эндпоинта (create + read) с dependency override

```python
# tests/api/v1/test_articles_api.py
from fastapi.testclient import TestClient

class TestArticlesAPI:
    
    @pytest.fixture
    def client(self, app, db_session, override_get_db):
        """TestClient с переопределённой БД"""
        app.dependency_overrides[get_db] = override_get_db
        yield TestClient(app)
        app.dependency_overrides.clear()
    
    def test_create_article(self, client: TestClient):
        """Тест создания статьи через API"""
        
        response = client.post(
            "/api/v1/admin/articles",
            json={
                "title": "Test Article",
                "slug": "test-article",
                "body": "Test body",
                "status": "draft",
                "locales": {
                    "en": {
                        "title": "English Title",
                        "body": "English body"
                    }
                }
            },
            headers={
                "Authorization": "Bearer test-token",
                "X-Tenant-ID": str(TENANT_ID)
            }
        )
        
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == "Test Article"
        assert data["slug"] == "test-article"
        assert "id" in data
    
    def test_get_article(self, client: TestClient):
        """Тест получения статьи по ID"""
        
        # Сначала создаём статью
        create_response = client.post(
            "/api/v1/admin/articles",
            json={...}
        )
        article_id = create_response.json()["data"]["id"]
        
        # Затем получаем её
        response = client.get(f"/api/v1/admin/articles/{article_id}")
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == article_id
        assert data["title"] == "Test Article"
    
    def test_list_articles_pagination(self, client: TestClient):
        """Тест листинга статей с пагинацией"""
        
        # Создаём 25 статей
        for i in range(25):
            client.post(
                "/api/v1/admin/articles",
                json={"title": f"Article {i}", "slug": f"article-{i}"}
            )
        
        # Получаем первую страницу (20 по умолчанию)
        response = client.get("/api/v1/admin/articles?page=1&limit=20")
        
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 25
        assert data["meta"]["page"] == 1
        assert len(data["data"]) == 20
    
    def test_update_article(self, client: TestClient):
        """Тест обновления статьи"""
        
        # Создаём статью
        create_response = client.post(
            "/api/v1/admin/articles",
            json={"title": "Original", "slug": "original"}
        )
        article_id = create_response.json()["data"]["id"]
        
        # Обновляем её
        response = client.patch(
            f"/api/v1/admin/articles/{article_id}",
            json={"title": "Updated Title", "version": 1}
        )
        
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["title"] == "Updated Title"
        assert data["version"] == 2  # Версия инкрементирована
```

### 4️⃣ Тест авторизации (admin vs public)

```python
# tests/api/v1/test_auth_api.py
class TestAuthorization:
    
    def test_public_endpoint_no_auth_required(self, client: TestClient):
        """Public endpoint работает без авторизации"""
        
        response = client.get("/api/v1/public/articles?locale=en")
        
        # Может быть 200 (есть статьи) или 404 (нет), но НЕ 401
        assert response.status_code in [200, 404]
    
    def test_admin_endpoint_requires_auth(self, client: TestClient):
        """Admin endpoint требует авторизации"""
        
        response = client.post(
            "/api/v1/admin/articles",
            json={"title": "Test"}
            # Без Authorization header
        )
        
        assert response.status_code == 401
    
    def test_forbidden_for_content_manager(self, app, db_session):
        """Content manager не может удалять статьи"""
        
        # Переопределяем current_user (content_manager)
        def override_current_user():
            return AdminUser(
                id=UUID("550e8400-e29b-41d4-a716-446655440000"),
                tenant_id=TENANT_ID,
                role="content_manager"  # Не admin
            )
        
        app.dependency_overrides[get_current_user] = override_current_user
        client = TestClient(app)
        
        # Пытаемся удалить (требует admin)
        response = client.delete("/api/v1/admin/articles/some-id")
        
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()
        
        app.dependency_overrides.clear()
    
    def test_jwt_token_validation(self, app):
        """JWT токен должен быть валидным"""
        
        client = TestClient(app)
        
        # Неправильный токен
        response = client.get(
            "/api/v1/admin/articles",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
```

### 5️⃣ Тест валидации (422) и типовой ошибки

```python
# tests/api/v1/test_error_handling.py
class TestErrorHandling:
    
    def test_validation_error_missing_field(self, client: TestClient):
        """Тест 422 ошибки валидации (обязательное поле)"""
        
        response = client.post(
            "/api/v1/admin/articles",
            json={
                "slug": "test",
                # Missing 'title'
                "body": "Test"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "title" in str(data)
    
    def test_validation_error_invalid_format(self, client: TestClient):
        """Тест 422 ошибки (неправильный формат)"""
        
        response = client.post(
            "/api/v1/admin/articles",
            json={
                "title": "Test",
                "rating": "not-a-number"  # Должно быть число
            }
        )
        
        assert response.status_code == 422
    
    def test_not_found_error(self, client: TestClient):
        """Тест 404 ошибки"""
        
        fake_id = UUID("00000000-0000-0000-0000-000000000000")
        response = client.get(f"/api/v1/admin/articles/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_conflict_error(self, client: TestClient):
        """Тест 409 ошибки (конфликт)"""
        
        # Создаём первую статью
        client.post(
            "/api/v1/admin/articles",
            json={"title": "Test", "slug": "test-article"}
        )
        
        # Пытаемся создать вторую с тем же slug
        response = client.post(
            "/api/v1/admin/articles",
            json={"title": "Test 2", "slug": "test-article"}
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    def test_rate_limit_error(self, client: TestClient):
        """Тест 429 ошибки (rate limit)"""
        
        # Создаём много заявок подряд
        for _ in range(10):
            response = client.post("/api/v1/public/inquiries", json={...})
            
            if response.status_code == 429:
                break
        
        # Последний должен быть 429
        assert response.status_code == 429
        assert response.headers["Retry-After"]
    
    def test_response_error_format(self, client: TestClient):
        """Тест формата ошибки (RFC 7807)"""
        
        response = client.get("/api/v1/admin/articles/invalid-id")
        
        assert response.status_code in [422, 400]
        data = response.json()
        
        # Проверяем структуру ошибки
        assert "type" in data or "detail" in data
        assert "status" in data or response.status_code
```

### 6️⃣ Тест миграций (Alembic)

```python
# tests/integration/test_migrations.py
import pytest
from alembic.script import ScriptDirectory
from alembic.config import Config as AlembicConfig

class TestMigrations:
    
    @pytest.fixture(scope="module")
    def alembic_config(self):
        """Конфиг Alembic"""
        cfg = AlembicConfig("alembic.ini")
        return cfg
    
    def test_migrations_can_upgrade(self, alembic_config):
        """Тест что миграции апгрейдятся без ошибок"""
        
        from alembic.command import upgrade
        
        # Это запустит все миграции (в тестовой БД)
        upgrade(alembic_config, "head")
        
        # Если не было исключения, тест прошел
    
    def test_migrations_can_downgrade(self, alembic_config):
        """Тест что миграции даунгрейдятся без ошибок"""
        
        from alembic.command import downgrade, upgrade
        
        # Апгрейдим до последней
        upgrade(alembic_config, "head")
        
        # Даунгрейдим на одну версию назад
        downgrade(alembic_config, "-1")
        
        # Опять апгрейдим (проверяем идемпотентность)
        upgrade(alembic_config, "head")
    
    def test_migration_001_creates_articles_table(self, db_session):
        """Тест что миграция #001 создала таблицу articles"""
        
        from sqlalchemy import inspect
        
        inspector = inspect(db_session.connection())
        tables = inspector.get_table_names()
        
        assert "articles" in tables
        
        # Проверяем колонки
        columns = {col['name'] for col in inspector.get_columns('articles')}
        assert "id" in columns
        assert "title" in columns
        assert "slug" in columns
        assert "status" in columns
    
    def test_migration_soft_delete_adds_column(self, db_session):
        """Тест что миграция soft delete добавила deleted_at"""
        
        from sqlalchemy import inspect
        
        inspector = inspect(db_session.connection())
        columns = {col['name'] for col in inspector.get_columns('articles')}
        
        assert "deleted_at" in columns
```

---

## CI/CD рекомендации

### 🔧 Команды для CI

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
          POSTGRES_DB: test_cms_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -e .[dev]
    
    - name: Run linting
      run: |
        ruff check app tests
        black --check app tests
    
    - name: Run unit tests
      run: |
        pytest tests/unit -v --cov=app/modules --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest tests/integration -v --cov=app --cov-report=xml --cov-append
      env:
        DATABASE_URL: postgresql+asyncpg://test_user:test_password@localhost:5432/test_cms_db
    
    - name: Run API tests
      run: |
        pytest tests/api -v --cov=app --cov-report=xml --cov-append
    
    - name: Run E2E tests (if needed)
      run: |
        pytest tests/e2e -v --cov=app --cov-report=xml --cov-append
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage.xml
        fail_ci_if_error: true
        flags: unittests
```

### ⚡ Параллелизм с pytest-xdist

```bash
# Локально (на 4 ядрах)
pytest tests/ -n 4

# В CI (опасно для БД — нужна синхронизация)
pytest tests/unit -n 4      # Unit безопасно параллелить
pytest tests/integration -n 1  # Integration — только 1 процесс (БД)

# Или с разными БД per worker
pytest tests/integration -n 4 --dist=loadscope
```

**Минусы параллелизма для integration тестов:**
- Конфликты в БД (разные workers пишут одновременно)
- Сложнее отлаживать
- Нужна синхронизация блокировок

**Рекомендация:** Параллелить только unit тесты, integration последовательно.

### 📊 Coverage политика

```ini
# .coveragerc
[coverage:report]
# Общий минимум покрытия
fail_under = 80

# Per-file минимум
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if TYPE_CHECKING:

[coverage:html]
directory = htmlcov
```

**CI команда:**

```bash
# Fail если покрытие ниже 80%
pytest --cov=app --cov-report=html --cov-fail-under=80

# Сгенерировать отчет
coverage report --fail-under=80
coverage html  # htmlcov/index.html
```

---

## Definition of Done (DoD)

### ✅ Checklist для каждой фичи

**Перед тем как выпустить фичу, должны быть:**

```
[ ] Unit тесты для сервисов/валидаторов
    - Положительные сценарии (happy path)
    - Граничные случаи (boundary conditions)
    - Ошибки (exceptions)
    
[ ] Integration тесты для БД
    - CRUD операции
    - Валидация constraints
    - Миграции (если БД-related)
    
[ ] API тесты для эндпоинтов
    - GET (success, 404, permissions)
    - POST (201, 400, 409, 422)
    - PATCH (200, 409, 403)
    - DELETE (204, 403)
    - Пагинация/фильтрация (если есть)
    
[ ] E2E тесты для workflows
    - Полный сценарий create→read→update→delete
    - Интеграция между модулями (если есть)
    
[ ] Error handling тесты
    - Валидация (422)
    - Not found (404)
    - Конфликты (409)
    - Forbidden (403)
    - Rate limit (429)
    - Internal errors (500)
    
[ ] Auth & permissions тесты
    - Public vs Admin endpoints
    - Role-based access control
    - Token validation
    
[ ] Coverage: минимум 80%
    - app/modules/: 85%+
    - app/api/: 80%+
    - app/core/: 85%+
    
[ ] Все тесты проходят локально
    pytest tests/ -v --cov=app --cov-fail-under=80
    
[ ] Нет flaky тестов
    pytest tests/ --count=10 (повторяем 10 раз)
    
[ ] CI/CD проходит
    GitHub Actions, GitLab CI, или другое
    
[ ] Code review approved
    - Логика tests правильная
    - Нет дубликатов
    - Best practices соблюдены
```

### 📋 Template для доп. проверок

```python
# Для критичного кода (payment, auth, admin actions):
# - Минимум 2 разработчика reviewed tests
# - Integration tests обязательны
# - E2E тесты обязательны

# Для non-critical (UI, cosmetic):
# - Unit tests достаточно
# - Coverage может быть 70%
```

---

## Чек-лист внедрения по этапам

### 📅 Этап 1: Foundation (Неделя 1-2)

**Цель:** Поднять инфраструктуру для тестирования

```
[ ] Установить зависимости (pytest, fixtures, factories)
    pip install pytest pytest-asyncio pytest-cov httpx factory-boy faker

[ ] Создать структуру папок
    mkdir -p tests/{unit,integration,api,e2e,fixtures}

[ ] Создать conftest.py с базовыми фикстурами
    - event_loop
    - async_engine
    - db_session
    - override_get_db
    - app
    - client

[ ] Создать factories.py для TenantFactory, UserFactory

[ ] Создать .env.test конфиг

[ ] Настроить pytest.ini

[ ] Добавить простейшие тесты (smoke tests)
    - test_app_startup (может ли приложение запуститься)
    - test_health_check (GET /health работает)

Результат: pytest tests/ проходит 5-10 тестов за <10s
```

### 📅 Этап 2: Core API + Unit (Неделя 2-3)

**Цель:** Покрыть основные эндпоинты и бизнес-логику

```
[ ] Unit тесты для каждого сервиса
    tests/unit/test_*_service.py
    - Минимум 10 unit тестов на сервис
    - Покрытие: 80%+ per service

[ ] Unit тесты для валидаторов/утилит
    tests/unit/test_validators.py
    tests/unit/test_utils.py

[ ] API тесты для CRUD эндпоинтов
    tests/api/v1/test_articles_api.py
    tests/api/v1/test_services_api.py
    - GET (list + detail)
    - POST (create + validation)
    - PATCH (update)
    - DELETE

[ ] Auth тесты
    tests/api/v1/test_auth_api.py
    - POST /login
    - POST /refresh
    - Forbidden/Unauthorized checks

[ ] Error handling тесты
    tests/api/v1/common/test_error_handling.py
    - 400, 422, 404, 409, 429, 500

[ ] Coverage check
    pytest tests/ --cov=app --cov-fail-under=75

Результат: ~80 тестов, coverage 75%+, время выполнения <30s
```

### 📅 Этап 3: Integration + Data (Неделя 3-4)

**Цель:** Покрыть БД и миграции

```
[ ] Integration тесты для репозиториев
    tests/integration/test_*_repository.py
    - CRUD operations
    - Filtering/Sorting
    - Soft delete
    - Constraints

[ ] Миграции тесты
    tests/integration/test_migrations.py
    - Upgrade/Downgrade
    - Specific migration checks

[ ] Data factories улучшения
    tests/integration/fixtures/factories.py
    - Все основные модели
    - Related objects (fixtures)
    - Relationships

[ ] Локализация тесты (если есть)
    tests/integration/test_localization.py

[ ] SEO модуль тесты (если есть)
    tests/integration/test_seo.py

Результат: ~120 тестов, coverage 80%+, интеграция время <60s
```

### 📅 Этап 4: E2E + Polish (Неделя 4-5)

**Цель:** Полные сценарии + CI/CD

```
[ ] E2E тесты для workflows
    tests/e2e/test_article_workflow.py
    tests/e2e/test_leads_workflow.py
    - create → read → update → delete

[ ] Параллельность
    pytest -n 4 tests/unit

[ ] CI/CD конфигурация
    .github/workflows/test.yml
    - Lint (ruff, black)
    - Unit tests
    - Integration tests
    - Coverage report
    - Codecov

[ ] Performance тесты (опционально)
    tests/performance/test_query_performance.py
    - pytest-benchmark

[ ] Cleanup + Documentation
    README.md в tests/
    Инструкция как запустить тесты

Результат: ~150 тестов, coverage 85%+, CI/CD работает
```

### 📅 Этап 5: Maintenance (Ongoing)

**Цель:** Поддержание и улучшение

```
[ ] Ежемесячно: review flaky tests
[ ] Ежемесячно: optimize slow tests
[ ] Quarterly: refactor/consolidate duplicate tests
[ ] После каждого сложного buгfix: добавить регрессионный тест
```

---

## 🚀 Быстрый старт (copy-paste ready)

### Установка

```bash
# 1. Зависимости
pip install pytest pytest-asyncio pytest-cov pytest-xdist \
            httpx factory-boy faker pytest-mock \
            testcontainers[postgres]

# 2. Структура
mkdir -p tests/{unit,integration,api,e2e}

# 3. Базовые файлы (см. выше: conftest.py, pytest.ini)

# 4. Запуск
pytest tests/ -v --cov=app --cov-fail-under=80
```

### Первый тест (копипейт)

```python
# tests/unit/test_validators.py
import pytest
from app.core.validators import validate_email

def test_validate_email_valid():
    assert validate_email("user@example.com") is True

def test_validate_email_invalid():
    assert validate_email("invalid-email") is False
```

```bash
pytest tests/unit/test_validators.py -v
```

---

## 📚 Ресурсы

- [pytest docs](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
- [SQLAlchemy async testing](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#async-io-concurrency)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [Testcontainers Python](https://testcontainers-python.readthedocs.io/)

---

**Версия:** v1.0  
**Дата:** 14 января 2026  
**Статус:** ✅ Готово к реализации
