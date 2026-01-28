# Инструкция по деплою изменений на удаленный сервер

## Ветка: `refactor/backend-analysis-implementation`

### Что было изменено:
- ✅ Миграция DocumentService на BaseService
- ✅ Исправление datetime.utcnow() → datetime.now(UTC)
- ✅ Разделение больших router файлов на под-роутеры
- ✅ Добавление BaseService и pagination helpers

---

## Команды для деплоя на сервере

### 1. Подключиться к серверу
```bash
ssh root@81.31.244.142
```

### 2. Перейти в директорию проекта
```bash
cd /opt/backend_sceleton/backend
```

### 3. Переключиться на новую ветку
```bash
git fetch origin
git checkout refactor/backend-analysis-implementation
```

### 4. Получить последние изменения
```bash
git pull origin refactor/backend-analysis-implementation
```

### 5. Пересобрать и перезапустить backend контейнер
```bash
# Остановить текущий контейнер
docker compose -f docker-compose.prod.yml --env-file .env.prod stop backend

# Пересобрать образ (если нужно)
docker compose -f docker-compose.prod.yml --env-file .env.prod build backend

# Запустить контейнер
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d backend

# Проверить логи
docker logs cms_backend_prod --tail 50 -f
```

### 6. Проверить статус контейнера
```bash
docker ps | grep backend
```

### 7. Проверить, что приложение запустилось
```bash
# Проверить логи на наличие ошибок
docker logs cms_backend_prod --tail 100 | grep -i error

# Проверить health check
docker exec cms_backend_prod curl -f http://localhost:8000/health || echo "Health check failed"
```

---

## Быстрая команда (все в одном)

```bash
ssh root@81.31.244.142 "cd /opt/backend_sceleton/backend && \
  git fetch origin && \
  git checkout refactor/backend-analysis-implementation && \
  git pull origin refactor/backend-analysis-implementation && \
  docker compose -f docker-compose.prod.yml --env-file .env.prod restart backend && \
  sleep 5 && \
  docker logs cms_backend_prod --tail 30"
```

---

## Откат изменений (если что-то пошло не так)

```bash
cd /opt/backend_sceleton/backend
git checkout main
git pull origin main
docker compose -f docker-compose.prod.yml --env-file .env.prod restart backend
```

---

## Проверка после деплоя

1. **Проверить логи:**
   ```bash
   docker logs cms_backend_prod --tail 100
   ```

2. **Проверить импорты:**
   ```bash
   docker exec cms_backend_prod python -c "from app.main import app; print('OK')"
   ```

3. **Проверить API:**
   ```bash
   curl -I http://localhost:8000/api/v1/health
   ```

---

## Примечания

- Все изменения протестированы локально ✅
- Импорты проверены ✅
- Синтаксис проверен ✅
- Приложение инициализируется без ошибок ✅

Если возникнут проблемы, проверьте логи контейнера и убедитесь, что все зависимости установлены.
