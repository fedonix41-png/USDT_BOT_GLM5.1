# План: Интеграция Webapp в Docker с Cloudflare Tunnel

## Проблема
Webapp работает только локально через `npm run dev`, но не доступен:
1. В Docker-среде нет сервиса для webapp
2. Telegram требует HTTPS для Mini Apps
3. API `/api/v1/rates` возвращает 500 (Decimal не сериализуется)

---

## Решение

### 1. Исправить Decimal → JSON в API
**Файл:** `app/api/routers/rates.py:33`

Заменить во всех router'ах:
```python
# Было:
return web.json_response(response.model_dump())

# Нужно:
return web.json_response(response.model_dump(mode='json'))
```

Pydantic v2 с `mode='json'` конвертирует `Decimal` → `float` автоматически.

**Файлы для изменения:**
- `app/api/routers/rates.py` (строки 33, 58, 83)
- `app/api/routers/auth.py` (строки 84, 145)
- `app/api/routers/users.py` (строки 43, 59, 94, 126, 155)
- `app/api/routers/statistics.py` (строка 66)
- `app/api/routers/settings.py` (строки 34, 77)
- `app/api/routers/orders.py` (строки 53, 69, 106)

---

### 2. Создать Dockerfile.webapp (multi-stage)
**Новый файл:** `Dockerfile.webapp`

```dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY webapp/package*.json ./
RUN npm ci
COPY webapp/ .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
```

---

### 3. Создать nginx.conf (reverse proxy)
**Новый файл:** `nginx.conf`

```nginx
server {
    listen 3000;
    
    root /usr/share/nginx/html;
    index index.html;
    
    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # API proxy
    location /api/ {
        proxy_pass http://api:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### 4. Обновить docker-compose.yml
Добавить сервис webapp:

```yaml
  webapp:
    build:
      context: .
      dockerfile: Dockerfile.webapp
    ports:
      - "3000:3000"
    depends_on:
      - api
    restart: unless-stopped
```

---

### 5. Настроить Cloudflare Quick Tunnel (для теста)

**Самый быстрый способ получить HTTPS:**

```bash
# Убедиться что webapp запущен на порту 3000
docker compose up -d webapp

# Запустить Quick Tunnel
cloudflared tunnel --url http://localhost:3000
```

Cloudflare выдаст URL вида: `https://random-name-xxxx.trycloudflare.com`

Этот URL можно использовать для тестирования Mini App в Telegram.

**Для продакшена** позже настроить постоянный туннель с собственным доменом.

---

### 6. Обновить документацию

| Файл | Раздел | Изменение |
|------|--------|-----------|
| `architecture.md` | Компоненты системы | Добавить Webapp |
| `architecture.md` | Middleware | — |
| `stack.md` | Основные технологии | Обновить версии React/Vite, добавить nginx |
| `modules.md` | Структура файлов | Добавить webapp/, nginx.conf, Dockerfile.webapp |
| `issues.md` | Активные проблемы | Убрать проблему после исправления |

---

## Порядок выполнения

1. **Decimal fix** — правки в 6 файлах routers/*.py
2. **Dockerfile.webapp** — новый файл
3. **nginx.conf** — новый файл
4. **docker-compose.yml** — добавить сервис webapp
5. **Пересобрать контейнеры:**
   ```bash
   docker compose build webapp
   docker compose up -d webapp
   ```
6. **Проверить API:** `curl http://localhost:3000/api/v1/rates`
7. **Настроить Cloudflare Tunnel**
8. **Обновить документацию**

---

## Результат

```
Telegram Client (HTTPS)
        ↓
Cloudflare Tunnel
        ↓
nginx:3000 → webapp (React static)
        ↓ /api/*
api:8081 → PostgreSQL + Redis
```

Webapp доступен по HTTPS, API проксируется через nginx.
