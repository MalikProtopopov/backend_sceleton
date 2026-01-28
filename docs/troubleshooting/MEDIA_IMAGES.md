# Диагностика проблем с изображениями/медиа

## Как проверить, проблема на бекенде или фронтенде

### 1. Проверка на бекенде

#### Шаг 1: Проверьте логи бекенда

```bash
# На сервере
docker logs cms_backend_prod | grep -i "media_serve_error"
```

Если видите ошибки типа:
```
"error": "Could not connect to the endpoint URL: \"http://minio:9000/...\""
```

Это означает проблему с подключением к S3/MinIO на бекенде.

#### Шаг 2: Запустите скрипт диагностики

```bash
cd /opt/backend_sceleton/backend
python scripts/check_media.py
```

Скрипт проверит:
- ✅ Настройки S3 в `.env.prod`
- ✅ Подключение к S3/MinIO
- ✅ Существование bucket
- ✅ Доступность объектов

#### Шаг 3: Проверьте эндпоинт напрямую

```bash
# Замените {tenant_id} и путь на реальные значения
curl -v http://localhost:8000/media/{tenant_id}/cases/test.png

# Или через внешний URL
curl -v https://your-api-domain.com/media/{tenant_id}/cases/test.png
```

**Ожидаемый результат:**
- ✅ `200 OK` с содержимым файла - бекенд работает
- ❌ `404 Not Found` - файл не найден в S3
- ❌ `500 Internal Server Error` - проблема с подключением к S3

### 2. Проверка на фронтенде

#### Шаг 1: Откройте DevTools в браузере

1. Откройте страницу с изображениями
2. Откройте DevTools (F12)
3. Перейдите на вкладку **Network**
4. Обновите страницу
5. Найдите запросы к `/media/...`

#### Шаг 2: Проверьте запросы

**Если запрос возвращает 404:**
- Проверьте URL изображения в ответе API
- Убедитесь, что путь правильный: `/media/{tenant_id}/{folder}/{filename}`
- Проверьте, что файл существует в S3

**Если запрос возвращает 500:**
- Проблема на бекенде (см. раздел выше)
- Проверьте логи бекенда

**Если запрос блокируется CORS:**
- Проверьте настройки CORS в бекенде
- Убедитесь, что домен фронтенда добавлен в `CORS_ORIGINS`

**Если запрос не отправляется:**
- Проверьте консоль браузера на ошибки JavaScript
- Проверьте, правильно ли формируется URL на фронтенде

### 3. Частые проблемы и решения

#### Проблема: "Could not connect to the endpoint URL"

**Причина:** Бекенд не может подключиться к MinIO/S3

**Решение:**
1. Проверьте, запущен ли MinIO:
   ```bash
   docker ps | grep minio
   ```

2. Проверьте настройки в `.env.prod`:
   ```bash
   # Для MinIO в Docker
   S3_ENDPOINT_URL=http://minio:9000
   S3_ACCESS_KEY=minioadmin
   S3_SECRET_KEY=minioadmin
   S3_BUCKET_NAME=cms-assets
   ```

3. Убедитесь, что контейнеры в одной сети:
   ```bash
   docker network inspect cms_network_prod
   ```

4. Перезапустите бекенд:
   ```bash
   docker compose -f docker-compose.prod.yml restart backend
   ```

#### Проблема: "NoSuchBucket"

**Причина:** Bucket не существует в S3

**Решение:**
1. Создайте bucket в MinIO:
   ```bash
   docker exec -it cms_minio_prod mc mb myminio/cms-assets
   docker exec -it cms_minio_prod mc anonymous set public myminio/cms-assets
   ```

2. Или обновите `S3_BUCKET_NAME` в `.env.prod` на существующий bucket

#### Проблема: "InvalidAccessKeyId" или "SignatureDoesNotMatch"

**Причина:** Неправильные credentials

**Решение:**
1. Проверьте `S3_ACCESS_KEY` и `S3_SECRET_KEY` в `.env.prod`
2. Для MinIO используйте `minioadmin/minioadmin` (по умолчанию)
3. Перезапустите бекенд после изменения

#### Проблема: Изображения не отображаются, но запросы успешные

**Причина:** Проблема на фронтенде

**Решение:**
1. Проверьте, правильно ли формируется URL:
   - Должен быть: `https://api.example.com/media/{tenant_id}/cases/image.png`
   - Не должен быть: `http://minio:9000/...` (внутренний адрес)

2. Проверьте CORS:
   - Убедитесь, что домен фронтенда в `CORS_ORIGINS`
   - Проверьте заголовки ответа: `Access-Control-Allow-Origin`

3. Проверьте Content-Type:
   - Должен быть правильный MIME-type (например, `image/png`)
   - Проверьте заголовок `Content-Type` в ответе

### 4. Проверка конфигурации

#### Проверьте `.env.prod`:

```bash
# S3 Storage
S3_ENDPOINT_URL=http://minio:9000  # Для MinIO в Docker
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=cms-assets
S3_REGION=us-east-1
```

#### Проверьте docker-compose.prod.yml:

Убедитесь, что MinIO запущен и в той же сети, что и бекенд:

```yaml
services:
  backend:
    networks:
      - cms_network_prod
    environment:
      - S3_ENDPOINT_URL=http://minio:9000
  
  minio:
    networks:
      - cms_network_prod
```

### 5. Тестирование эндпоинта

#### Тест 1: Проверка доступности эндпоинта

```bash
curl -I http://localhost:8000/media/test/test.png
```

Должен вернуть `404` (файл не найден) или `200` (файл найден), но НЕ `500`.

#### Тест 2: Проверка существующего файла

Если знаете путь к существующему файлу:

```bash
curl -v http://localhost:8000/media/{tenant_id}/cases/{filename}.png
```

Должен вернуть:
- `200 OK` с содержимым файла
- Правильный `Content-Type: image/png`
- Заголовок `Cache-Control`

### 6. Логи для отладки

#### Включите подробное логирование:

В `.env.prod`:
```bash
LOG_LEVEL=DEBUG
```

Перезапустите бекенд и проверьте логи:
```bash
docker logs -f cms_backend_prod | grep -i "s3\|media\|minio"
```

### 7. Быстрая проверка

Выполните все проверки одной командой:

```bash
cd /opt/backend_sceleton/backend && \
python scripts/check_media.py && \
echo "---" && \
docker ps | grep -E "minio|backend" && \
echo "---" && \
docker logs cms_backend_prod --tail 50 | grep -i "media_serve_error"
```

---

## Резюме

**Если ошибка в логах бекенда** → Проблема на бекенде (S3/MinIO)
**Если запросы к `/media/...` возвращают 500** → Проблема на бекенде
**Если запросы успешные, но изображения не показываются** → Проблема на фронтенде
**Если запросы блокируются CORS** → Проблема конфигурации CORS на бекенде
