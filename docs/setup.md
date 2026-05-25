# Установка и запуск

## Предварительные требования

| Инструмент | Версия | Назначение |
|-----------|--------|------------|
| Python | 3.11+ | Локальная разработка, выполнение Alembic миграций |
| Docker | 20.10+ | Контейнеризация сервисов |
| Docker Compose | 2.0+ | Оркестрация контейнеров |
| uv | latest | Менеджер пакетов Python (устанавливается автоматически в Docker) |

## Пошаговая установка

### Шаг 1. Клонирование репозитория

```bash
git clone <url-репозитория>
cd USDT_BOT_GLM5.1
```

### Шаг 2. Настройка переменных окружения

```bash
cp .env.example .env
```

Отредактируйте `.env` и заполните обязательные значения:

```env
# Telegram — получите токен у @BotFather
BOT_TOKEN=ваш_токен_бота

# Database — пароль должен совпадать с POSTGRES_PASSWORD
DATABASE_URL=postgresql+asyncpg://usdt_bot:ваш_пароль@postgres:5432/usdt_bot
POSTGRES_PASSWORD=ваш_пароль

# Redis — оставьте по умолчанию, если Redis в Docker
REDIS_URL=redis://redis:6379/0

# Encryption — сгенерируйте 32-байтный ключ в hex (64 символа)
# Пример генерации: python -c "import secrets; print(secrets.token_hex(32))"
ENCRYPTION_KEY=сгенерированный_64_символьный_hex

# SuperAdmin — ваш Telegram ID (узнать: @userinfobot)
SUPER_ADMIN_TELEGRAM_ID=ваш_telegram_id
```

**Важно:**

- `ENCRYPTION_KEY` — 64-символьная hex-строка (32 байта = AES-256). Сохраните резервную копию: при потере ключа зашифрованные реквизиты невозможно восстановить.
- `SUPER_ADMIN_TELEGRAM_ID` — Telegram ID пользователя, который при первом `/start` получит роль `super_admin`.
- `POSTGRES_PASSWORD` — пароль для PostgreSQL в Docker. Должен совпадать с паролем в `DATABASE_URL`.

### Шаг 3. Установка зависимостей (локально)

Для выполнения миграций локально установите зависимости:

```bash
pip install uv
uv sync
```

Или, если Docker используется для всего:

```bash
docker compose run --rm bot uv sync
```

### Шаг 4. Запуск инфраструктуры (PostgreSQL + Redis)

```bash
docker-compose up -d postgres redis
```

Дождитесь готовности (healthcheck):

```bash
docker-compose ps
# Убедитесь, что postgres и redis имеют статус "healthy"
```

### Шаг 5. Выполнение миграций базы данных

```bash
uv run alembic upgrade head
```

Или через Docker:

```bash
docker-compose run --rm bot uv run alembic upgrade head
```

Эта команда создаст все 6 таблиц (`users`, `orders`, `rates`, `global_settings`, `notification_chats`, `audit_logs`), enum-типы и индексы.

### Шаг 6. Запуск всех сервисов

```bash
docker-compose up -d
```

Проверьте статус контейнеров:

```bash
docker-compose ps
```

Все 4 сервиса должны быть запущены: `postgres`, `redis`, `bot`, `arq-worker`.

### Шаг 7. Проверка логов

```bash
docker-compose logs -f bot
```

Убедитесь, что бот успешно подключился и начал Long Polling.

## Первый запуск: настройка SuperAdmin

После запуска бота необходимо выполнить первоначальную настройку через Telegram-интерфейс.

### 1. Запуск бота

Откройте бота в Telegram и отправьте `/start`. Поскольку ваш `SUPER_ADMIN_TELEGRAM_ID` совпадает с вашим Telegram ID, вы автоматически получите роль `super_admin` и соответствующее меню.

### 2. Установка курсов

Без установленных курсов клиенты не смогут создавать заявки.

- Нажмите **«🔄 Сменить курс (покупка)»** → введите курс покупки (руб/USDT)
- Нажмите **«🔄 Сменить курс (продажа)»** → введите курс продажи (руб/USDT)

### 3. Установка реквизитов

Реквизиты (ссылки на оплату) шифруются и хранятся в БД.

- Нажмите **«🔗 Сменить реквизиты»** → выберите тип (покупка/продажа) → введите ссылку или реквизиты

### 4. Добавление чатов уведомлений

Чаты уведомлений получают алерты о новых заявках, жалобах и назначении ролей.

- Нажмите **«➕ Чаты уведомлений»** → **«➕ Добавить чат»**
- Перешлите сообщение из нужного чата или введите Chat ID
- Бот проверит, что он является админом в чате, и сохранит его

### 5. Назначение операторов и админов

- Нажмите **«👤 Сделать Оператором»** → введите Telegram ID пользователя (он должен сначала запустить бота через `/start`)
- Нажмите **«👑 Сделать Админом»** (доступно только SuperAdmin) → введите Telegram ID

## Управление сервисами

### Остановка

```bash
docker-compose down
```

Данные PostgreSQL сохраняются в volume `pgdata`.

### Полная остановка с удалением данных

```bash
docker-compose down -v
```

### Перезапуск отдельного сервиса

```bash
docker-compose restart bot
docker-compose restart arq-worker
```

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f bot
docker-compose logs -f arq-worker

# Последние 100 строк
docker-compose logs --tail=100 bot
```

### Выполнение команд внутри контейнера

```bash
# Миграции
docker-compose exec bot uv run alembic upgrade head

# Python- shell
docker-compose exec bot uv run python

# Проверка подключения к PostgreSQL
docker-compose exec postgres psql -U usdt_bot -c "SELECT * FROM users;"
```

## Обновление

### Обновление кода

```bash
git pull
docker-compose build
docker-compose up -d
```

### Новая миграция

```bash
uv run alembic revision --autogenerate -m "описание_изменения"
uv run alembic upgrade head
```

### Пересоздание базы данных

```bash
docker-compose down -v
docker-compose up -d postgres redis
uv run alembic upgrade head
docker-compose up -d
```

## Устранение неполадок

| Проблема | Решение |
|----------|---------|
| `bot` падает с ошибкой подключения к PostgreSQL | Проверьте `DATABASE_URL` в `.env`, убедитесь что `postgres` healthy: `docker-compose ps` |
| `bot` падает с ошибкой `ENCRYPTION_KEY` | Убедитесь, что ключ — 64-символьная hex-строка |
| ARQ Worker не запускается | Проверьте `REDIS_URL` и что Redis healthy |
| Миграции не выполняются | Убедитесь, что PostgreSQL запущен и доступен по адресу из `DATABASE_URL` |
| Бот не отвечает на /start | Проверьте `BOT_TOKEN` в `.env`, проверьте логи: `docker-compose logs bot` |
| Курс не установлен | SuperAdmin должен задать курс через меню бота |
| Реквизиты не настроены | SuperAdmin должен задать реквизиты через «🔗 Сменить реквизиты» |
