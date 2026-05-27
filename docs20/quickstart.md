# Быстрый старт

> Пошаговая инструкция для запуска проекта. Подробная документация — в остальных файлах `docs/`.

---

## Предварительные требования

| Инструмент | Версия |
|-----------|--------|
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| Python | 3.11+ |
| uv | latest |

---

## Установка за 5 шагов

### 1. Клонирование и настройка окружения

```bash
git clone <url-репозитория>
cd USDT_BOT_GLM5.1
cp .env.example .env
```

Отредактируйте `.env` — обязательные переменные:

```env
BOT_TOKEN=ваш_токен_бота                    # от @BotFather
DATABASE_URL=postgresql+asyncpg://usdt_bot:ПАРОЛЬ@postgres:5432/usdt_bot
POSTGRES_PASSWORD=ПАРОЛЬ                     # тот же, что в DATABASE_URL
REDIS_URL=redis://redis:6379/0
ENCRYPTION_KEY=...                            # 64 hex символа: python -c "import secrets; print(secrets.token_hex(32))"
SUPER_ADMIN_TELEGRAM_ID=ваш_telegram_id      # узнать у @userinfobot
API_SECRET_KEY=...                            # для REST API
```

> Полный список переменных — см. `modules.md#конфигурация`.

### 2. Установка зависимостей

```bash
pip install uv
uv sync
```

### 3. Запуск инфраструктуры

```bash
docker compose up -d postgres redis
# Дождитесь "healthy" статуса:
docker compose ps
```

### 4. Миграции БД

```bash
uv run alembic upgrade head
```

### 5. Запуск всех сервисов

```bash
docker compose up -d
docker compose ps  # все 4 сервиса: postgres, redis, bot, arq-worker
```

---

## Первый запуск: настройка SuperAdmin

1. Откройте бота в Telegram → `/start` → вы получите роль `super_admin`
2. Установите курсы: ⚙️ Управление → 🔄 Курс покупки / Курс продажи
3. Установите реквизиты: ⚙️ Управление → 🔗 Реквизиты
4. Добавьте чаты уведомлений: ⚙️ Управление → ➕ Чаты

---

## Управление

```bash
# Логи
docker compose logs -f bot
docker compose logs -f arq-worker

# Остановка (данные сохраняются)
docker compose down

# Остановка с удалением данных
docker compose down -v

# Перезапуск
docker compose restart bot

# Миграции
docker compose exec bot uv run alembic upgrade head
uv run alembic revision --autogenerate -m "описание"
```

---

## Устранение неполадок

| Проблема | Решение |
|----------|---------|
| Bot падает: ошибка PostgreSQL | Проверьте `DATABASE_URL` и `POSTGRES_PASSWORD` в `.env` |
| Bot падает: `ENCRYPTION_KEY` | Убедитесь, что ключ — 64 hex символа |
| ARQ Worker не запускается | Проверьте `REDIS_URL` и статус Redis |
| Бот не отвечает на /start | Проверьте `BOT_TOKEN`, смотрите логи |
| Курс не установлен | SuperAdmin должен задать курс через меню |

---

## См. также

- **Все переменные окружения:** `modules.md#конфигурация`
- **Архитектура:** `architecture.md`
- **Схема БД:** `database.md`
- **Технологии:** `stack.md`
