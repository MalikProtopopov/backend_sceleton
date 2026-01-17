# Admin Frontend Deployment Prompt (Same Server as Backend)

> **Используй эту документацию как промпт для настройки деплоя Next.js админ-панели на том же сервере, что и бекенд.**

---

## 🎯 Цель

Развернуть Next.js админ-панель на том же сервере, что и бекенд:
- Использовать тот же Nginx для проксирования
- SSL уже настроен для `admin.domain.com`
- Два варианта деплоя: статический экспорт или Docker контейнер

---

## 📁 Архитектура

```
Сервер (один для backend + admin):
├── api.domain.com    → backend:8000 (FastAPI)
└── admin.domain.com  → admin:3000 (Next.js) или статика в /var/www/admin
```

---

## 🔧 Вариант 1: Static Export (Рекомендуется для простоты)

### Преимущества:
- Меньше ресурсов сервера
- Проще деплой
- Быстрее загрузка

### Шаг 1: Настройка Next.js для static export

**next.config.js:**
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',  // Static HTML export
  trailingSlash: true,
  images: {
    unoptimized: true  // Для static export
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://api.domain.com',
  }
}

module.exports = nextConfig
```

### Шаг 2: Структура проекта admin

```
admin/
├── package.json
├── next.config.js
├── .env.production         # Переменные для production
├── .env.local              # Локальная разработка
├── Dockerfile              # Для Docker варианта (опционально)
├── src/
│   ├── app/
│   └── ...
└── scripts/
    └── deploy.sh           # Скрипт деплоя
```

### Шаг 3: .env.production

```bash
NEXT_PUBLIC_API_URL=https://api.domain.com
NEXT_PUBLIC_ADMIN_URL=https://admin.domain.com
```

### Шаг 4: Скрипт деплоя (admin/scripts/deploy.sh)

```bash
#!/bin/bash
# =============================================================================
# Admin Panel Deployment Script (Static Export)
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Настройки
REMOTE_USER="root"
REMOTE_HOST="your-server-ip"
REMOTE_PATH="/var/www/admin"
BACKEND_PATH="/opt/backend_sceleton/backend"

log_info "Building admin panel..."
npm run build

log_info "Uploading to server..."
rsync -avz --delete out/ ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/

log_info "Setting permissions..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "chmod -R 755 ${REMOTE_PATH}"

log_success "Admin panel deployed!"
log_info "URL: https://admin.domain.com"
```

### Шаг 5: Nginx конфигурация (уже в nginx.conf.template)

```nginx
# Admin Panel Server (admin.domain.com)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name admin.${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Root for static files
    root /var/www/admin;
    index index.html;

    # Static assets with caching
    location /_next/static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri.html $uri/ /index.html;
    }
}
```

### Шаг 6: Деплой на сервер

```bash
# На локальной машине (в папке admin)
npm install
npm run build  # Создаст папку out/

# Загрузить на сервер
rsync -avz --delete out/ root@server:/var/www/admin/

# На сервере - проверить права
ssh root@server "chmod -R 755 /var/www/admin"

# Перезагрузить nginx (если нужно)
ssh root@server "cd /opt/backend_sceleton/backend && docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -s reload"
```

---

## 🐳 Вариант 2: Docker Container

### Преимущества:
- SSR (Server Side Rendering)
- API Routes в Next.js
- Более сложная логика

### Шаг 1: Dockerfile для admin

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

### Шаг 2: next.config.js для Docker

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',  // Для Docker
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  }
}

module.exports = nextConfig
```

### Шаг 3: Добавить в docker-compose.prod.yml (backend)

```yaml
services:
  # ... другие сервисы ...

  admin:
    build:
      context: ../admin  # Путь к папке admin
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_URL: https://api.${DOMAIN}
    container_name: ${PROJECT_NAME}_admin_prod
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: https://api.${DOMAIN}
      NODE_ENV: production
    expose:
      - "3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - app_network
```

### Шаг 4: Обновить nginx.conf.template для proxy

```nginx
# Upstream для admin
upstream admin {
    server admin:3000;
    keepalive 16;
}

# Admin Panel Server
server {
    listen 443 ssl http2;
    server_name admin.${DOMAIN};

    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    location / {
        proxy_pass http://admin;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static assets caching
    location /_next/static/ {
        proxy_pass http://admin;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

---

## 📋 Makefile команды для admin

Добавить в backend/Makefile:

```makefile
# =============================================================================
# Admin Panel Commands
# =============================================================================

admin-build:
	cd ../admin && npm run build

admin-deploy: admin-build
	rsync -avz --delete ../admin/out/ root@server:/var/www/admin/
	@echo "Admin panel deployed!"

# Для Docker варианта
admin-docker-build:
	docker compose -f docker-compose.prod.yml --env-file .env.prod build admin

admin-docker-up:
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d admin

admin-docker-logs:
	docker compose -f docker-compose.prod.yml --env-file .env.prod logs -f admin
```

---

## 🚀 Пошаговый деплой

### Для Static Export:

```bash
# 1. На локальной машине
cd admin
npm install
npm run build

# 2. Загрузить на сервер
rsync -avz --delete out/ root@server:/var/www/admin/

# 3. На сервере - проверить
curl https://admin.domain.com
```

### Для Docker:

```bash
# 1. На сервере
cd /opt/backend_sceleton/backend

# 2. Собрать admin образ
docker compose -f docker-compose.prod.yml --env-file .env.prod build admin

# 3. Запустить
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d admin

# 4. Перезагрузить nginx
docker compose -f docker-compose.prod.yml --env-file .env.prod exec nginx nginx -s reload
```

---

## ⚠️ Важные моменты

### CORS на бекенде

В `.env.prod` бекенда добавить admin домен:
```
CORS_ORIGINS=https://admin.domain.com,https://www.domain.com
```

### Переменные окружения

```bash
# .env.production (admin)
NEXT_PUBLIC_API_URL=https://api.domain.com

# ВАЖНО: Переменные с NEXT_PUBLIC_ доступны в браузере!
# Не храни секреты в NEXT_PUBLIC_ переменных!
```

### Cookie и авторизация

Если используете httpOnly cookies для JWT:
```javascript
// В API запросах
fetch('https://api.domain.com/auth/login', {
  credentials: 'include',  // Для отправки cookies
  // ...
})
```

---

## 🔄 Обновление admin панели

### Static Export:
```bash
# Локально
cd admin
npm run build
rsync -avz --delete out/ root@server:/var/www/admin/
```

### Docker:
```bash
# На сервере
cd /opt/backend_sceleton
git pull origin main

cd backend
docker compose -f docker-compose.prod.yml --env-file .env.prod build admin
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d admin
```

---

## 📦 Чеклист

- [ ] `NEXT_PUBLIC_API_URL` указывает на правильный API
- [ ] CORS на бекенде включает `https://admin.domain.com`
- [ ] SSL сертификат покрывает `admin.domain.com`
- [ ] Nginx настроен для обслуживания admin
- [ ] Папка `/var/www/admin` существует и имеет правильные права (755)

