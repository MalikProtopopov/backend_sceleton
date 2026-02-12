# Деплой: tenant domain switcher (ветка feat/tenant-domain-switcher)

## Команды для обновления и деплоя на сервере

### 1. Подключиться к серверу и перейти в каталог проекта

```bash
ssh user@your-server
cd /path/to/mediannback   # путь к проекту на сервере
```

### 2. Забрать обновления и переключиться на новую ветку

```bash
git fetch origin
git checkout feat/tenant-domain-switcher
git pull origin feat/tenant-domain-switcher
```

### 3. Запустить миграции БД

```bash
cd backend
alembic upgrade head
```

### 4. Перезапустить приложение

**Если через systemd:**

```bash
sudo systemctl restart mediannback
# или как называется ваш сервис, например:
# sudo systemctl restart gunicorn
# sudo systemctl restart uvicorn
```

**Если через Docker:**

```bash
docker compose build
docker compose up -d
```

**Если через PM2 / вручную:**

Остановить процесс и запустить заново.

### 5. Проверить работу

```bash
# Проверить, что API отвечает
curl -s https://api.mediann.dev/api/v1/health

# Проверить новый эндпоинт by-domain (если домен уже добавлен в tenant_domains)
curl -s https://api.mediann.dev/api/v1/public/tenants/by-domain/admin.mediann.dev
```

---

## Краткий чек-лист

- [ ] `git fetch && git checkout feat/tenant-domain-switcher && git pull`
- [ ] `cd backend && alembic upgrade head`
- [ ] Перезапустить приложение (systemd / docker / pm2)
- [ ] Проверить health / by-domain

---

## Откат (если что-то пошло не так)

```bash
git checkout refactor/backend-analysis-implementation
git pull origin refactor/backend-analysis-implementation
alembic downgrade -1   # откатить миграцию 024
# Перезапустить приложение
```
