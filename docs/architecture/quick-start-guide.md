# Quick Start: FastAPI + PostgreSQL Corporate CMS Backend

## Быстрый старт разработки

---

## 1. Инициализация проекта

### 1.1 Структура и зависимости

```bash
# Создать проект
mkdir corporate-cms-backend && cd corporate-cms-backend
python -m venv venv
source venv/bin/activate  # или на Windows: venv\Scripts\activate

# Установить зависимости
pip install fastapi uvicorn sqlalchemy psycopg2-binary pydantic pydantic-settings
pip install python-jose cryptography python-multipart  # JWT
pip install alembic  # миграции
pip install pytest pytest-asyncio httpx  # тестирование
pip install redis  # опционально для кеша
pip install python-dateutil pytz  # работа с датами

# Сохранить зависимости
pip freeze > requirements.txt
```

### 1.2 Структура папок

```bash
mkdir -p app/{core,db,modules/{company,content,auth,leads},api/{v1/{public,admin}},middleware,utils,tasks}
mkdir -p alembic/versions tests/{unit,integration,e2e}
```

---

## 2. Базовая конфигурация

### 2.1 app/core/config.py

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/cms_db"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # App
    APP_NAME: str = "Corporate CMS Backend"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # Tenants
    DEFAULT_TENANT_ID: Optional[str] = None
    
    # Localization
    DEFAULT_LOCALE: str = "en"
    SUPPORTED_LOCALES: list[str] = ["en", "ru"]
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

### 2.2 app/core/security.py

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredential

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_jwt_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthCredential = Depends(security)):
    token = credentials.credentials
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
```

### 2.3 app/db/session.py

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 2.4 app/db/base.py

```python
from sqlalchemy.orm import declarative_base

Base = declarative_base()
```

---

## 3. ORM Models (SQLAlchemy)

### 3.1 app/db/models.py (основные модели)

```python
from sqlalchemy import Column, String, UUID, DateTime, Integer, Boolean, ForeignKey, Text, Enum, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.db.base import Base

class Tenant(Base):
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    plan = Column(String(50), default="starter")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

class LocalesConfig(Base):
    __tablename__ = "locales_config"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(5), nullable=False)  # 'en', 'ru', 'de'
    name = Column(String(50), nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'code', name='uq_tenant_locale'),
    )

class Service(Base):
    __tablename__ = "services"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    slug = Column(String(255), nullable=False)
    icon_url = Column(String(500))
    status = Column(String(20), default="published")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    locales = relationship("ServiceLocale", back_populates="service", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'slug', name='uq_tenant_service_slug'),
    )

class ServiceLocale(Base):
    __tablename__ = "service_locales"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_id = Column(UUID(as_uuid=True), ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    locale_id = Column(UUID(as_uuid=True), ForeignKey("locales_config.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    slug = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    service = relationship("Service", back_populates="locales")
    
    __table_args__ = (
        UniqueConstraint('service_id', 'locale_id', name='uq_service_locale'),
        UniqueConstraint('locale_id', 'slug', name='uq_locale_service_slug'),
    )

class AdminUser(Base):
    __tablename__ = "admin_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(500), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"))
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    role = relationship("Role")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_tenant_admin_email'),
    )

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'name', name='uq_tenant_role_name'),
    )
```

---

## 4. Pydantic Schemas

### 4.1 app/modules/company/schemas.py

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID

class ServiceLocaleSchema(BaseModel):
    locale: str = Field(..., min_length=2, max_length=5)
    name: str = Field(..., min_length=3, max_length=500)
    description: str | None = None
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$", min_length=3)

class ServiceCreateSchema(BaseModel):
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$")
    status: str = Field(default="published", pattern=r"^(published|draft|archived)$")
    icon_url: str | None = None
    locales: dict[str, ServiceLocaleSchema] = Field(..., min_items=1)
    
    @field_validator("locales")
    @classmethod
    def validate_locales(cls, v):
        if len(v) == 0:
            raise ValueError("At least one locale is required")
        return v

class ServiceResponseSchema(BaseModel):
    id: UUID
    slug: str
    status: str
    icon_url: str | None
    locales: list[ServiceLocaleSchema]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ServiceListResponseSchema(BaseModel):
    id: UUID
    slug: str
    name: str  # default locale name
    description: str | None
    icon_url: str | None
```

---

## 5. Repository Pattern

### 5.1 app/modules/company/infrastructure/repository.py

```python
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID
from app.db.models import Service, ServiceLocale
from app.core.config import settings

class ServiceRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, service_id: UUID, tenant_id: UUID) -> Service | None:
        return self.db.query(Service).filter(
            and_(
                Service.id == service_id,
                Service.tenant_id == tenant_id,
                Service.status == "published"
            )
        ).first()
    
    def get_by_slug(self, slug: str, tenant_id: UUID, locale: str) -> Service | None:
        return self.db.query(Service).join(
            ServiceLocale,
            ServiceLocale.service_id == Service.id
        ).filter(
            and_(
                Service.tenant_id == tenant_id,
                ServiceLocale.slug == slug,
                Service.status == "published",
                ServiceLocale.locale.has(code=locale)
            )
        ).first()
    
    def list_published(self, tenant_id: UUID, limit: int = 20, offset: int = 0):
        return self.db.query(Service).filter(
            and_(
                Service.tenant_id == tenant_id,
                Service.status == "published"
            )
        ).order_by(Service.sort_order).limit(limit).offset(offset).all()
    
    def create(self, service: Service) -> Service:
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service
    
    def update(self, service: Service) -> Service:
        self.db.commit()
        self.db.refresh(service)
        return service
```

---

## 6. Use Cases (Application Layer)

### 6.1 app/modules/company/application/use_cases.py

```python
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from app.db.models import Service, ServiceLocale, LocalesConfig
from app.modules.company.infrastructure.repository import ServiceRepository
from app.utils.exceptions import ConflictError, NotFoundError
from app.core.config import settings

class CreateServiceUseCase:
    def __init__(self, db: Session, repo: ServiceRepository, tenant_id: UUID):
        self.db = db
        self.repo = repo
        self.tenant_id = tenant_id
    
    def execute(self, slug: str, status: str, icon_url: str | None, locales_data: dict) -> Service:
        # Проверить уникальность slug в каждой локали
        for locale_code in locales_data.keys():
            existing = self.db.query(ServiceLocale).join(
                LocalesConfig, LocalesConfig.id == ServiceLocale.locale_id
            ).filter(
                and_(
                    ServiceLocale.slug == locales_data[locale_code]["slug"],
                    LocalesConfig.code == locale_code,
                    ServiceLocale.service.has(
                        and_(
                            Service.tenant_id == self.tenant_id
                        )
                    )
                )
            ).first()
            
            if existing:
                raise ConflictError(f"Slug '{locales_data[locale_code]['slug']}' already exists for locale {locale_code}")
        
        # Создать service
        service = Service(
            id=uuid4(),
            tenant_id=self.tenant_id,
            slug=slug,
            status=status,
            icon_url=icon_url
        )
        
        # Добавить локали
        for locale_code, data in locales_data.items():
            locale_config = self.db.query(LocalesConfig).filter(
                and_(
                    LocalesConfig.tenant_id == self.tenant_id,
                    LocalesConfig.code == locale_code
                )
            ).first()
            
            if not locale_config:
                raise ValueError(f"Locale {locale_code} not configured for this tenant")
            
            service_locale = ServiceLocale(
                id=uuid4(),
                service_id=service.id,
                locale_id=locale_config.id,
                name=data["name"],
                description=data.get("description"),
                slug=data["slug"]
            )
            service.locales.append(service_locale)
        
        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        
        return service

class GetServiceUseCase:
    def __init__(self, db: Session, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id
    
    def execute(self, service_id: UUID) -> Service:
        service = self.db.query(Service).filter(
            and_(
                Service.id == service_id,
                Service.tenant_id == self.tenant_id
            )
        ).first()
        
        if not service:
            raise NotFoundError("Service not found")
        
        return service
```

---

## 7. API Routes

### 7.1 app/modules/company/api/dependencies.py

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from uuid import UUID
from app.db.session import get_db
from app.modules.company.infrastructure.repository import ServiceRepository
from app.modules.company.application.use_cases import CreateServiceUseCase, GetServiceUseCase

def get_service_repo(db: Session = Depends(get_db)) -> ServiceRepository:
    return ServiceRepository(db)

def get_create_service_use_case(
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant)
) -> CreateServiceUseCase:
    return CreateServiceUseCase(db, ServiceRepository(db), tenant_id)

def get_get_service_use_case(
    db: Session = Depends(get_db),
    tenant_id: UUID = Depends(get_current_tenant)
) -> GetServiceUseCase:
    return GetServiceUseCase(db, tenant_id)

def get_current_tenant() -> UUID:
    # Извлечь tenant_id из контекста (обычно из middleware или заголовка)
    # Это упрощенный пример
    return UUID("00000000-0000-0000-0000-000000000001")
```

### 7.2 app/modules/company/api/public_routes.py

```python
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.modules.company.schemas import ServiceListResponseSchema
from app.core.config import settings

router = APIRouter(prefix="/services", tags=["services"])

@router.get("")
async def list_services(
    db: Session = Depends(get_db),
    locale: str = Query(default=settings.DEFAULT_LOCALE),
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    search: str | None = None
) -> dict:
    """List all published services"""
    
    offset = (page - 1) * limit
    
    # Query services (filtered, paginated)
    query = db.query(Service).filter(Service.status == "published")
    
    if search:
        query = query.join(ServiceLocale).filter(
            ServiceLocale.name.ilike(f"%{search}%")
        )
    
    total = query.count()
    services = query.order_by(Service.sort_order).limit(limit).offset(offset).all()
    
    return {
        "data": [ServiceListResponseSchema.from_orm(s) for s in services],
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
    }

@router.get("/{slug}")
async def get_service(
    slug: str,
    db: Session = Depends(get_db),
    locale: str = Query(default=settings.DEFAULT_LOCALE)
) -> ServiceResponseSchema:
    """Get single service by slug"""
    
    service = db.query(Service).join(ServiceLocale).filter(
        and_(
            ServiceLocale.slug == slug,
            Service.status == "published"
        )
    ).first()
    
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    return ServiceResponseSchema.from_orm(service)
```

### 7.3 app/modules/company/api/admin_routes.py

```python
from fastapi import APIRouter, Depends, HTTPException, status
from app.modules.company.schemas import ServiceCreateSchema, ServiceResponseSchema
from app.modules.company.application.use_cases import CreateServiceUseCase, GetServiceUseCase
from app.core.security import check_permission
from app.utils.exceptions import ConflictError, NotFoundError

router = APIRouter(prefix="/services", tags=["admin:services"])

@router.post("", status_code=201)
async def create_service(
    body: ServiceCreateSchema,
    use_case: CreateServiceUseCase = Depends(get_create_service_use_case),
    user = Depends(check_permission("create_services"))
) -> dict:
    """Create new service"""
    
    try:
        service = use_case.execute(
            slug=body.slug,
            status=body.status,
            icon_url=body.icon_url,
            locales_data=body.locales
        )
        return {
            "data": ServiceResponseSchema.from_orm(service)
        }
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("/{service_id}")
async def get_service(
    service_id: UUID,
    use_case: GetServiceUseCase = Depends(get_get_service_use_case),
    user = Depends(check_permission("view_services"))
) -> dict:
    """Get service by ID"""
    
    try:
        service = use_case.execute(service_id)
        return {"data": ServiceResponseSchema.from_orm(service)}
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

---

## 8. Main Application

### 8.1 app/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import router as v1_router
from app.middleware.tenant_context import TenantMiddleware
from app.middleware.error_handler import setup_exception_handlers

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Corporate CMS Backend API"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # или конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Custom middleware
app.add_middleware(TenantMiddleware)

# Exception handlers
setup_exception_handlers(app)

# Routes
app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 8.2 app/api/v1/__init__.py

```python
from fastapi import APIRouter

router = APIRouter()

# Public routes
from app.modules.company.api.public_routes import router as company_public
from app.modules.content.api.public_routes import router as content_public

# Admin routes
from app.modules.company.api.admin_routes import router as company_admin
from app.modules.content.api.admin_routes import router as content_admin

# Auth
from app.modules.auth.api.routes import router as auth_router

# Include routers
router.include_router(company_public, prefix="/public", tags=["public"])
router.include_router(content_public, prefix="/public", tags=["public"])
router.include_router(company_admin, prefix="/admin", tags=["admin"])
router.include_router(content_admin, prefix="/admin", tags=["admin"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
```

---

## 9. Тестирование

### 9.1 tests/conftest.py

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Create test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def admin_token(db):
    # Create test user and token
    token = create_access_token(data={"sub": "test_user_id", "tenant_id": "test_tenant"})
    return token
```

### 9.2 tests/integration/test_service_api.py

```python
def test_create_service_success(client, admin_token):
    response = client.post(
        "/api/v1/admin/services",
        json={
            "slug": "consulting",
            "status": "published",
            "icon_url": "https://example.com/icon.png",
            "locales": {
                "en": {
                    "name": "Consulting",
                    "description": "Our consulting services",
                    "slug": "consulting"
                }
            }
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 201
    assert response.json()["data"]["slug"] == "consulting"

def test_list_services_public(client):
    response = client.get("/api/v1/public/services?limit=10&page=1")
    
    assert response.status_code == 200
    assert "data" in response.json()
    assert "meta" in response.json()
```

---

## 10. Docker

### 10.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app ./app
COPY alembic ./alembic

# Run migrations and app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
```

### 10.2 docker-compose.yml

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: cms_user
      POSTGRES_PASSWORD: cms_password
      POSTGRES_DB: cms_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  app:
    build: .
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://cms_user:cms_password@postgres/cms_db
      DEBUG: "false"
    ports:
      - "8000:8000"
    volumes:
      - .:/app

volumes:
  postgres_data:
```

### 10.3 .env.example

```env
DATABASE_URL=postgresql://cms_user:cms_password@localhost/cms_db
SECRET_KEY=your_super_secret_key_change_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_NAME=Corporate CMS Backend
DEBUG=true
API_V1_PREFIX=/api/v1
DEFAULT_LOCALE=en
SUPPORTED_LOCALES=en,ru,de
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## 11. Запуск

```bash
# 1. Создать .env
cp .env.example .env

# 2. Запустить с Docker
docker-compose up --build

# 3. Или локально
python -m uvicorn app.main:app --reload

# 4. OpenAPI docs
# http://localhost:8000/docs
# http://localhost:8000/redoc

# 5. Запустить тесты
pytest -v

# 6. Миграции (если не в docker)
alembic upgrade head
```

---

## Дальнейшие шаги

1. **Реализовать остальные сущности** (articles, cases, faq, etc) по той же схеме
2. **Добавить SEO API** (routes, hreflang, sitemap)
3. **Реализовать file upload** и S3 integration
4. **Добавить кеширование** (Redis + ETag)
5. **Настроить мониторинг** (Sentry, DataDog)
6. **Покрыть тестами** все use cases
7. **Подготовить к production** (security headers, rate limiting, logging)

---

## Полезные ссылки

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/)
- [Pydantic v2](https://docs.pydantic.dev/latest/)
- [PostgreSQL Full-Text Search](https://www.postgresql.org/docs/current/textsearch.html)
- [JWT with FastAPI](https://fastapi.tiangolo.com/advanced/security/oauth2-jwt/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)
