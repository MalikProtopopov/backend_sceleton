# Руководство по развертыванию Corporate CMS Engine

Это руководство описывает процесс развертывания проекта в разных окружениях:
- **Development (localhost)** - локальная разработка
- **Production (SSL)** - продакшен сервер с HTTPS

---

## Содержание

1. [Архитектура развертывания](#архитектура-развертывания)
2. [Требования](#требования)
3. [Локальная разработка (Development)](#локальная-разработка-development)
4. [Продакшен развертывание](#продакшен-развертывание)
   - [Подготовка сервера](#подготовка-сервера)
   - [Настройка DNS](#настройка-dns)
   - [Настройка переменных окружения](#настройка-переменных-окружения)
   - [Запуск без SSL](#запуск-без-ssl-http)
   - [Настройка SSL](#настройка-ssl-сертификата)
   - [Создание администратора](#создание-первого-админа)
5. [Развертывание админ-панели (Next.js)](#развертывание-админ-панели-nextjs)
6. [Настройка клиентского фронтенда (отдельный сервер)](#настройка-клиентского-фронтенда-отдельный-сервер)
7. [Обновление и деплой](#обновление-проекта)
8. [Резервное копирование](#резервное-копирование)
9. [Мониторинг и логи](#мониторинг-и-логи)
10. [Устранение неполадок](#устранение-неполадок)
11. [Полезные команды](#полезные-команды)

---

## Архитектура развертывания

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        СЕРВЕР 1 (Backend + Admin)                           │
│                                                                             │
│   ┌─────────────┐     ┌──────────────┐     ┌──────────────┐                │
│   │   Nginx     │────▶│   Backend    │────▶│  PostgreSQL  │                │
│   │  (SSL/443)  │     │  (FastAPI)   │     │   :5432      │                │
│   │   :80/:443  │     │   :8000      │     └──────────────┘                │
│   └─────────────┘     └──────────────┘                                     │
│         │                    │              ┌──────────────┐                │
│         │                    └─────────────▶│    Redis     │                │
│         │                                   │   :6379      │                │
│         ▼                                   └──────────────┘                │
│   ┌─────────────┐                                                          │
│   │ Admin Panel │     ┌──────────────┐                                     │
│   │  (Next.js)  │     │   Certbot    │                                     │
│   │   :3000     │     │ (SSL certs)  │                                     │
│   └─────────────┘     └──────────────┘                                     │
│                                                                             │
│   Домены: api.example.com, admin.example.com                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                    СЕРВЕР 2 (Client Frontend)                               │
│                                                                             │
│   ┌─────────────┐     ┌──────────────┐                                     │
│   │   Nginx     │────▶│   Next.js    │                                     │
│   │  (SSL/443)  │     │   Client     │                                     │
│   └─────────────┘     └──────────────┘                                     │
│                                                                             │
│   Домен: www.example.com                                                    │
│   API: https://api.example.com (Сервер 1)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Структура доменов

| Домен | Сервер | Сервис | Описание |
|-------|--------|--------|----------|
| `api.example.com` | Сервер 1 | Backend (FastAPI) | REST API |
| `admin.example.com` | Сервер 1 | Admin Panel (Next.js) | Админ-панель |
| `www.example.com` | Сервер 2 | Client Frontend | Клиентский сайт |

---

## Требования

### Минимальные требования к серверу

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| CPU | 2 ядра | 4 ядра |
| RAM | 4 GB | 8 GB |
| Диск | 50 GB SSD | 100 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

### Необходимое ПО

- Docker 24+
- Docker Compose v2+
- Git
- curl, htop

### Открытые порты

- `22` - SSH
- `80` - HTTP (для Let's Encrypt)
- `443` - HTTPS

---

## Локальная разработка (Development)

### Быстрый старт

```bash
# 1. Перейдите в директорию backend
cd backend

# 2. Скопируйте env.dev в .env (если не существует)
cp env.dev .env

# 3. Запустите все сервисы
make dev-up

# 4. Дождитесь запуска (10-15 секунд) и инициализируйте админа
make init-admin
```

### Доступные сервисы в dev-режиме

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| MinIO Console | http://localhost:9001 | minioadmin/minioadmin |
| PostgreSQL | localhost:5433 | postgres/postgres |
| Redis | localhost:6379 | - |

### Команды разработки

```bash
# Запуск
make dev-up          # Запустить все сервисы
make dev-down        # Остановить все сервисы
make dev-restart     # Перезапустить backend

# Логи
make dev-logs        # Все логи
make dev-logs-backend # Только backend

# Утилиты
make dev-shell       # Shell в контейнере backend
make dev-status      # Статус сервисов
make dev-build       # Пересобрать образы
```

### Настройка CORS для фронтенда

В файле `.env` уже настроены CORS для типичных портов фронтенд-разработки:

```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:5173,http://localhost:5174,http://localhost:8080
```

---

## Продакшен развертывание

### Подготовка сервера

#### 1. Подключитесь к серверу

```bash
ssh root@your-server-ip
```

#### 2. Обновите систему

```bash
apt update && apt upgrade -y
```

#### 3. Установите Docker

```bash
# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Добавьте пользователя в группу docker
usermod -aG docker $USER

# Установите Docker Compose
apt install docker-compose-plugin -y

# Проверьте установку
docker --version
docker compose version
```

#### 4. Установите утилиты

```bash
apt install -y git curl htop
```

#### 5. Настройте файрвол

```bash
# UFW (рекомендуется)
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

#### 6. Клонируйте проект

```bash
cd /opt
git clone https://github.com/your-repo/your-project.git
cd your-project/backend
```

---

### Настройка DNS

Создайте следующие DNS A-записи, указывающие на IP вашего сервера:

| Тип | Имя | Значение | TTL |
|-----|-----|----------|-----|
| A | api | YOUR_SERVER_IP | 300 |
| A | admin | YOUR_SERVER_IP | 300 |

Проверка DNS:

   ```bash
dig +short api.your-domain.com
dig +short admin.your-domain.com
# Оба должны возвращать IP вашего сервера
   ```

---

### Настройка переменных окружения

#### 1. Скопируйте пример файла

```bash
cp env.prod.example .env.prod
```

#### 2. Сгенерируйте безопасные пароли

```bash
# JWT Secret (hex, 32 bytes)
openssl rand -hex 32

# Пароли для БД и Redis
openssl rand -base64 24

# Encryption key (Fernet)
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

#### 3. Отредактируйте `.env.prod`

```bash
nano .env.prod
```

**Обязательные изменения:**

```bash
# Домен
DOMAIN=your-domain.com
PUBLIC_API_URL=https://api.your-domain.com

# База данных
POSTGRES_PASSWORD=<сгенерированный_пароль>
DATABASE_URL=postgresql+asyncpg://cms_user:<сгенерированный_пароль>@postgres:5432/cms_db

# Redis
REDIS_PASSWORD=<сгенерированный_пароль>
REDIS_URL=redis://:<сгенерированный_пароль>@redis:6379/0

# JWT
JWT_SECRET_KEY=<сгенерированный_hex_32>

# CORS (добавьте домены фронтенда)
CORS_ORIGINS=https://admin.your-domain.com,https://www.your-domain.com,https://your-domain.com

# SSL
CERTBOT_EMAIL=admin@your-domain.com

# Encryption
ENCRYPTION_KEY=<сгенерированный_fernet_key>
```

#### 4. S3 Storage

Настройте S3-совместимое хранилище:

```bash
# Selectel
S3_ENDPOINT_URL=https://s3.storage.selcloud.ru

# AWS S3
S3_ENDPOINT_URL=https://s3.amazonaws.com

# Yandex Cloud
S3_ENDPOINT_URL=https://storage.yandexcloud.net

S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_BUCKET_NAME=your-bucket-name
S3_REGION=ru-1
```

---

### Запуск без SSL (HTTP)

Для первоначального тестирования запустите без SSL:

```bash
# 1. Скопируйте начальную конфигурацию nginx
cp nginx/nginx-initial.conf nginx/nginx.conf

# 2. Запустите сервисы
make prod-up

# 3. Проверьте статус
make prod-status

# 4. Проверьте API
curl http://api.your-domain.com/health
```

---

### Настройка SSL сертификата

#### Автоматический способ (рекомендуется)

```bash
make ssl-init DOMAIN=your-domain.com EMAIL=admin@your-domain.com
```

Скрипт автоматически:
1. Проверит DNS записи
2. Получит сертификат Let's Encrypt
3. Настроит nginx с SSL
4. Добавит cron для автообновления

#### Ручной способ

```bash
# 1. Получите сертификат
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@your-domain.com \
    --agree-tos \
    --no-eff-email \
    -d api.your-domain.com \
    -d admin.your-domain.com

# 2. Сгенерируйте nginx config
export DOMAIN=your-domain.com
envsubst '${DOMAIN}' < nginx/nginx.conf.template > nginx/nginx.conf

# 3. Перезапустите nginx
make prod-restart-nginx

# 4. Проверьте HTTPS
curl https://api.your-domain.com/health
```

#### Автообновление сертификата

Добавьте в crontab:

```bash
crontab -e

# Добавьте строку (ежедневная проверка в полночь):
0 0 * * * cd /opt/your-project/backend && make ssl-renew >> /var/log/ssl-renew.log 2>&1
```

---

### Создание первого админа

```bash
make init-admin-prod
```

Будут созданы:
- Tenant по умолчанию
- Все системные роли и разрешения
- Пользователь-администратор

**Учетные данные по умолчанию:**
- Email: `admin@example.com`
- Password: `admin123`

⚠️ **Важно:** Смените пароль сразу после первого входа!

---

## Развертывание админ-панели (Next.js)

### Вариант 1: Статический экспорт (рекомендуется)

```bash
# В директории админ-панели
cd admin

# Создайте .env.production
echo "NEXT_PUBLIC_API_URL=https://api.your-domain.com" > .env.production

# Соберите статические файлы
npm run build
npm run export

# Скопируйте на сервер
scp -r out/* root@your-server:/var/www/admin/
```

### Вариант 2: Docker контейнер

Раскомментируйте сервис `admin` в `docker-compose.prod.yml`:

```yaml
admin:
  build:
    context: ../admin
    dockerfile: Dockerfile
  container_name: cms_admin_prod
  restart: unless-stopped
  environment:
    NEXT_PUBLIC_API_URL: https://api.${DOMAIN}
    NODE_ENV: production
  expose:
    - "3000"
  networks:
    - cms_network
```

И обновите nginx конфиг для проксирования на контейнер.

---

## Настройка клиентского фронтенда (отдельный сервер)

### Переменные окружения

Создайте `.env.production` в проекте клиентского фронтенда:

```bash
# API URL (указывает на Сервер 1)
NEXT_PUBLIC_API_URL=https://api.your-domain.com

# WebSocket URL (если используется)
NEXT_PUBLIC_WS_URL=wss://api.your-domain.com
```

### CORS настройка

На **Сервере 1** в `.env.prod` добавьте домен клиентского фронтенда:

```bash
CORS_ORIGINS=https://admin.your-domain.com,https://www.your-domain.com,https://your-domain.com
```

И перезапустите backend:

```bash
make prod-restart
```

### Пример nginx для клиентского фронтенда (Сервер 2)

```nginx
server {
    listen 80;
    server_name www.your-domain.com your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name www.your-domain.com your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    root /var/www/client;
    index index.html;

    # Static assets
    location /_next/static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Next.js pages
    location / {
        try_files $uri $uri.html $uri/ /index.html;
    }
}
```

---

## Обновление проекта

### Автоматический деплой

```bash
# Обычный деплой
make deploy

# С предварительным бэкапом
make deploy-backup

# Без миграций
make deploy-no-migrate
```

### Ручной деплой

```bash
# 1. Получите последние изменения
git pull origin main

# 2. Пересоберите образы
make prod-build

# 3. Примените миграции
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm migrations

# 4. Перезапустите с минимальным простоем
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --no-deps backend

# 5. Перезагрузите nginx
make prod-restart-nginx
```

---

## Резервное копирование

### Создание бэкапа

```bash
# Только база данных
make db-backup

# База данных + хранилище
make db-backup-full
```

Бэкапы сохраняются в директорию `backups/`.

### Автоматическое резервное копирование

Добавьте в crontab:

```bash
crontab -e

# Ежедневный бэкап в 3:00
0 3 * * * cd /opt/your-project/backend && make db-backup >> /var/log/backup.log 2>&1
```

### Восстановление из бэкапа

```bash
make db-restore FILE=backups/db_backup_20240101_120000.sql.gz
```

---

## Мониторинг и логи

### Просмотр логов

```bash
# Все сервисы
make prod-logs

# Конкретный сервис
make prod-logs-backend
make prod-logs-nginx

# Последние 100 строк
docker compose -f docker-compose.prod.yml --env-file .env.prod logs --tail=100 backend
```

### Статус сервисов

```bash
make prod-status
```

### Использование ресурсов

```bash
docker stats
```

### Health check

```bash
# Локальный
curl http://localhost:8000/health

# Через nginx
curl https://api.your-domain.com/health
```

---

## Устранение неполадок

### Сервис не запускается

```bash
# Проверьте логи
make prod-logs-backend

# Проверьте конфигурацию
docker compose -f docker-compose.prod.yml config

# Перезапустите
make prod-restart
```

### Ошибки SSL

   ```bash
# Проверьте DNS
dig +short api.your-domain.com

# Проверьте доступность порта 80
curl http://api.your-domain.com/.well-known/acme-challenge/test

# Логи certbot
docker compose -f docker-compose.prod.yml --env-file .env.prod logs certbot
   ```

### CORS ошибки

1. Проверьте `CORS_ORIGINS` в `.env.prod`
2. Перезапустите backend: `make prod-restart`
3. Проверьте, что протокол совпадает (https vs http)

### База данных недоступна

```bash
# Проверьте статус
docker compose -f docker-compose.prod.yml --env-file .env.prod exec postgres pg_isready

# Логи PostgreSQL
docker compose -f docker-compose.prod.yml --env-file .env.prod logs postgres
```

### Нет места на диске

```bash
# Проверьте использование
df -h

# Очистите Docker
make docker-clean

# Полная очистка (осторожно!)
make docker-clean-all
```

---

## Полезные команды

### Общие

```bash
# Остановить все сервисы
make prod-down

# Войти в контейнер
make prod-shell

# Проверить конфигурацию
docker compose -f docker-compose.prod.yml config
```

### База данных

```bash
# Подключиться к PostgreSQL
docker compose -f docker-compose.prod.yml --env-file .env.prod exec postgres psql -U cms_user -d cms_db

# Выполнить SQL
docker compose -f docker-compose.prod.yml --env-file .env.prod exec postgres psql -U cms_user -d cms_db -c "SELECT * FROM admin_users;"
```

### Redis

```bash
# Подключиться к Redis
docker compose -f docker-compose.prod.yml --env-file .env.prod exec redis redis-cli -a $REDIS_PASSWORD
```

---

## Контрольный список развертывания

### Подготовка

- [ ] Сервер настроен (Docker, firewall, SSH)
- [ ] DNS записи созданы (api.*, admin.*)
- [ ] `.env.prod` создан и заполнен
- [ ] Все пароли сгенерированы и сохранены

### Развертывание

- [ ] Сервисы запущены (`make prod-up`)
- [ ] SSL сертификат получен (`make ssl-init`)
- [ ] HTTPS работает
- [ ] Администратор создан (`make init-admin-prod`)
- [ ] CORS настроен для всех фронтендов

### Операции

- [ ] Резервное копирование настроено (cron)
- [ ] Автообновление SSL настроено (cron)
- [ ] Мониторинг логов настроен

### Документация

- [ ] Пароли сохранены в безопасном месте
- [ ] IP адреса и домены задокументированы
- [ ] Процедуры восстановления проверены

---

## Рекомендации по безопасности

1. **Используйте сильные пароли** - генерируйте с помощью `openssl rand`
2. **Регулярно обновляйте** - `apt update && apt upgrade`
3. **Настройте fail2ban** - защита от брутфорса SSH
4. **Ограничьте доступ** - используйте firewall, VPN для SSH
5. **Мониторьте логи** - настройте алерты на ошибки
6. **Регулярные бэкапы** - и тестируйте восстановление!

---

**Дата обновления:** Январь 2026  
**Версия:** 2.0
