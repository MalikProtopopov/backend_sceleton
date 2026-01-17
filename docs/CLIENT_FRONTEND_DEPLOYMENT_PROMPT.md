# Client Frontend Deployment Prompt (Separate Server)

> **Используй эту документацию как промпт для настройки деплоя Next.js клиентского фронтенда на ОТДЕЛЬНОМ сервере.**

---

## 🎯 Цель

Развернуть Next.js клиентский сайт на отдельном сервере:
- Полностью независимый от бекенд-сервера
- Свой Nginx с SSL (Let's Encrypt)
- Подключение к API бекенда через HTTPS

---

## 📁 Архитектура

```
Сервер 1 (Backend + Admin):
├── api.domain.com    → backend:8000
└── admin.domain.com  → admin panel

Сервер 2 (Client Frontend):  ← ЭТА ДОКУМЕНТАЦИЯ
├── www.domain.com    → client:3000
└── domain.com        → redirect to www
```

---

## 📁 Структура проекта client

```
client/
├── Dockerfile
├── docker-compose.yml          # Development
├── docker-compose.prod.yml     # Production
├── Makefile
├── .env.local                  # Dev environment
├── .env.production             # Prod environment
├── .gitignore
├── .dockerignore
├── next.config.js
├── package.json
├── nginx/
│   ├── nginx-initial.conf      # HTTP only (для SSL)
│   └── nginx.conf.template     # SSL конфигурация
├── scripts/
│   └── init-ssl.sh
└── src/
    └── ...
```

---

## 🔧 Ключевые файлы

### 1. Dockerfile

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Build arguments for environment
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL

# Build
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

### 2. next.config.js

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',  // Для Docker
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'api.domain.com',
      },
      {
        protocol: 'https',
        hostname: '*.storage.selcloud.ru',  // Если используете Selectel S3
      },
    ],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
  },
}

module.exports = nextConfig
```

### 3. docker-compose.prod.yml

```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: client_nginx_prod
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - certbot_webroot:/var/www/certbot:ro
      - certbot_certs:/etc/letsencrypt:ro
    depends_on:
      client:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - client_network
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  certbot:
    image: certbot/certbot:latest
    container_name: client_certbot_prod
    volumes:
      - certbot_webroot:/var/www/certbot
      - certbot_certs:/etc/letsencrypt
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    networks:
      - client_network

  client:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
        NEXT_PUBLIC_SITE_URL: ${NEXT_PUBLIC_SITE_URL}
    container_name: client_frontend_prod
    restart: unless-stopped
    environment:
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL}
      NEXT_PUBLIC_SITE_URL: ${NEXT_PUBLIC_SITE_URL}
      NODE_ENV: production
    expose:
      - "3000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - client_network
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "5"

volumes:
  certbot_webroot:
    name: client_certbot_webroot
  certbot_certs:
    name: client_certbot_certs

networks:
  client_network:
    name: client_network_prod
    driver: bridge
```

### 4. nginx/nginx-initial.conf (HTTP для SSL)

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript 
               application/xml application/xml+rss text/javascript;

    upstream client {
        server client:3000;
        keepalive 32;
    }

    server {
        listen 80;
        listen [::]:80;
        server_name _;

        # ACME challenge
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
            allow all;
        }

        # Proxy to client
        location / {
            proxy_pass http://client;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 5. nginx/nginx.conf.template (SSL)

```nginx
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    client_max_body_size 10M;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_types text/plain text/css text/xml application/json application/javascript 
               application/xml application/xml+rss text/javascript image/svg+xml;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_stapling on;
    ssl_stapling_verify on;

    upstream client {
        server client:3000;
        keepalive 32;
    }

    # HTTP to HTTPS redirect
    server {
        listen 80;
        listen [::]:80;
        server_name www.${DOMAIN} ${DOMAIN};

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
            allow all;
        }

        location / {
            return 301 https://www.${DOMAIN}$request_uri;
        }
    }

    # Redirect domain.com to www.domain.com
    server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        server_name ${DOMAIN};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

        return 301 https://www.${DOMAIN}$request_uri;
    }

    # Main site (www.domain.com)
    server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;
        server_name www.${DOMAIN};

        ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # Static assets caching
        location /_next/static/ {
            proxy_pass http://client;
            proxy_http_version 1.1;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        location /static/ {
            proxy_pass http://client;
            proxy_http_version 1.1;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Main application
        location / {
            proxy_pass http://client;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
```

### 6. .env.production

```bash
# API URL (бекенд на другом сервере)
NEXT_PUBLIC_API_URL=https://api.domain.com

# URL этого сайта
NEXT_PUBLIC_SITE_URL=https://www.domain.com

# Домен для Nginx/SSL
DOMAIN=domain.com
```

### 7. Makefile

```makefile
.PHONY: help dev build prod-up prod-down prod-logs prod-build ssl-init deploy

help:
	@echo "Client Frontend Commands"
	@echo "========================"
	@echo "  make dev          - Start development server"
	@echo "  make build        - Build for production"
	@echo "  make prod-up      - Start production services"
	@echo "  make prod-down    - Stop production services"
	@echo "  make prod-logs    - View production logs"
	@echo "  make prod-build   - Rebuild production images"
	@echo "  make ssl-init     - Initialize SSL certificates"
	@echo "  make deploy       - Full deployment"

# Development
dev:
	npm run dev

build:
	npm run build

# Production
.env.prod-check:
	@if [ ! -f .env.production ]; then \
		echo "Error: .env.production not found!"; \
		exit 1; \
	fi

prod-up: .env.prod-check
	docker compose -f docker-compose.prod.yml --env-file .env.production up -d
	@echo "Client frontend started!"
	@echo "URL: https://www.$$(grep DOMAIN .env.production | cut -d '=' -f2)"

prod-down:
	docker compose -f docker-compose.prod.yml --env-file .env.production down

prod-logs:
	docker compose -f docker-compose.prod.yml --env-file .env.production logs -f

prod-logs-client:
	docker compose -f docker-compose.prod.yml --env-file .env.production logs -f client

prod-build:
	docker compose -f docker-compose.prod.yml --env-file .env.production build --no-cache

prod-restart:
	docker compose -f docker-compose.prod.yml --env-file .env.production restart client

prod-status:
	docker compose -f docker-compose.prod.yml --env-file .env.production ps

# SSL
ssl-init:
	@if [ -z "$(DOMAIN)" ] || [ -z "$(EMAIL)" ]; then \
		echo "Usage: make ssl-init DOMAIN=example.com EMAIL=admin@example.com"; \
		exit 1; \
	fi
	chmod +x scripts/init-ssl.sh
	./scripts/init-ssl.sh $(DOMAIN) $(EMAIL)

# Deploy
deploy: prod-build
	docker compose -f docker-compose.prod.yml --env-file .env.production up -d
	@echo "Deployment complete!"

# Nginx
nginx-reload:
	docker compose -f docker-compose.prod.yml --env-file .env.production exec nginx nginx -s reload
```

### 8. scripts/init-ssl.sh

```bash
#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <domain> <email>"
    exit 1
fi

DOMAIN=$1
EMAIL=$2
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

log_info "Setting up SSL for $DOMAIN"

# Step 1: Copy initial nginx config
log_info "Setting up initial nginx configuration..."
cp nginx/nginx-initial.conf nginx/nginx.conf

# Step 2: Start services
log_info "Starting services..."
docker compose -f docker-compose.prod.yml --env-file .env.production up -d client nginx
sleep 5

# Step 3: Get SSL certificate
log_info "Obtaining SSL certificate..."
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    --force-renewal \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

# Step 4: Generate SSL nginx config
log_info "Generating SSL nginx configuration..."
export DOMAIN
envsubst '${DOMAIN}' < nginx/nginx.conf.template > nginx/nginx.conf

# Step 5: Reload nginx
log_info "Reloading nginx..."
docker compose -f docker-compose.prod.yml --env-file .env.production exec nginx nginx -t
docker compose -f docker-compose.prod.yml --env-file .env.production exec nginx nginx -s reload

# Step 6: Start certbot renewal
docker compose -f docker-compose.prod.yml --env-file .env.production up -d certbot

log_success "SSL setup complete!"
log_info "Your site is available at:"
log_info "  https://www.$DOMAIN"
log_info "  https://$DOMAIN (redirects to www)"
```

---

## 🚀 Пошаговый деплой на ОТДЕЛЬНЫЙ сервер

### Шаг 1: Подготовка сервера

```bash
# Установка Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Создание директории
sudo mkdir -p /opt/client
sudo chown $USER:$USER /opt/client
cd /opt/client
```

### Шаг 2: Клонирование и настройка

```bash
# Клонирование
git clone https://github.com/user/client-repo.git .

# Настройка окружения
cp .env.example .env.production
nano .env.production
```

**.env.production:**
```bash
NEXT_PUBLIC_API_URL=https://api.domain.com  # API на ДРУГОМ сервере
NEXT_PUBLIC_SITE_URL=https://www.domain.com
DOMAIN=domain.com
```

### Шаг 3: Настройка DNS

Создать A-записи для ЭТОГО сервера:
- `domain.com` → IP клиентского сервера
- `www.domain.com` → IP клиентского сервера

### Шаг 4: Первый запуск

```bash
# Копируем начальную конфигурацию
cp nginx/nginx-initial.conf nginx/nginx.conf

# Собираем и запускаем
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### Шаг 5: SSL сертификат

```bash
# Через скрипт
chmod +x scripts/init-ssl.sh
./scripts/init-ssl.sh domain.com admin@domain.com

# ИЛИ вручную
docker compose -f docker-compose.prod.yml --env-file .env.production stop nginx

docker run --rm -p 80:80 \
  -v client_certbot_certs:/etc/letsencrypt \
  certbot/certbot certonly --standalone \
  -d domain.com -d www.domain.com \
  --email admin@domain.com --agree-tos --no-eff-email

export DOMAIN=domain.com
envsubst '${DOMAIN}' < nginx/nginx.conf.template > nginx/nginx.conf

docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

### Шаг 6: Проверка

```bash
# Статус
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# Логи
docker compose -f docker-compose.prod.yml --env-file .env.production logs -f client

# Тест
curl https://www.domain.com
```

---

## ⚠️ Важные настройки на бекенд-сервере

### CORS

В `.env.prod` на БЕКЕНД-сервере добавить домен клиента:

```bash
CORS_ORIGINS=https://admin.domain.com,https://www.domain.com,https://domain.com
```

### Перезапуск бекенда после изменения CORS

```bash
# На бекенд-сервере
cd /opt/backend_sceleton/backend
docker compose -f docker-compose.prod.yml --env-file .env.prod restart backend
```

---

## 🔄 Обновление клиентского фронтенда

```bash
cd /opt/client

# Получить изменения
git pull origin main

# Пересобрать
docker compose -f docker-compose.prod.yml --env-file .env.production build --no-cache client

# Перезапустить
docker compose -f docker-compose.prod.yml --env-file .env.production up -d client
```

---

## 📦 Чеклист перед деплоем клиента

### На клиентском сервере:
- [ ] DNS A-записи настроены (domain.com, www.domain.com → IP клиентского сервера)
- [ ] `.env.production` заполнен
- [ ] `NEXT_PUBLIC_API_URL` указывает на бекенд (https://api.domain.com)
- [ ] Порты 80 и 443 открыты

### На бекенд-сервере:
- [ ] CORS включает домены клиента (www.domain.com, domain.com)
- [ ] Бекенд перезапущен после изменения CORS
- [ ] API доступен по HTTPS (https://api.domain.com/health)

---

## 🛡️ Безопасность

1. **API ключи и секреты:** Храни только на сервере, не в коде
2. **NEXT_PUBLIC_** переменные видны в браузере - не храни там секреты
3. **CORS:** Ограничь только нужными доменами
4. **SSL:** Убедись что сертификат обновляется автоматически
5. **Firewall:** Открой только 80, 443 и 22 (SSH)

---

## 🔗 Полезные команды

```bash
# Проверка SSL сертификата
openssl s_client -connect www.domain.com:443 -servername www.domain.com

# Проверка CORS
curl -I -X OPTIONS https://api.domain.com/api/v1/public/services \
  -H "Origin: https://www.domain.com" \
  -H "Access-Control-Request-Method: GET"

# Логи nginx
docker compose -f docker-compose.prod.yml --env-file .env.production logs nginx

# Перезапуск всего
docker compose -f docker-compose.prod.yml --env-file .env.production down
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

