# Архитектура проекта

> **SSOT:** Этот документ — единственный источник истины для архитектурных компонентов и middleware.
> При упоминании в других документах используйте ссылки: `см. architecture.md`.

---

## Обзор

Telegram-бот для обмена USDT построен по модульной архитектуре с чётким разделением слоёв. Система развёртывается через Docker Compose и состоит из четырёх основных компонентов.

---

## Компоненты системы

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                         │
│                                                             │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │  Bot        │  │ ARQ      │  │PostgreSQL │  │  Redis  │ │
│  │  (Long      │  │ Worker   │  │   15      │  │  7-alpine│ │
│  │   Polling)  │  │ (tasks)  │  │           │  │         │ │
│  └──────┬──────┘  └────┬─────┘  └─────┬─────┘  └────┬────┘ │
│         │              │              │              │      │
│         └──────────────┴──────────────┴──────────────┘      │
│                    SQLAlchemy Async + ARQ                    │
└─────────────────────────────────────────────────────────────┘
```

### Bot (Long Polling)

| Параметр | Значение |
|----------|----------|
| **Назначение** | Основной компонент — Telegram-бот на базе Aiogram 3.x |
| **Режим работы** | Long Polling (получение обновлений через `bot.get_updates()`) |
| **Функции** | Приём и обработка сообщений, FSM, отправка ответов, регистрация пользователей, маршрутизация по ролям |
| **Запуск** | `uv run python -m app.main` |
| **Зависимости** | PostgreSQL (через SQLAlchemy async), Redis (кеш флагов) |

### ARQ Worker

| Параметр | Значение |
|----------|----------|
| **Назначение** | Фоновый обработчик задач через очередь ARQ |
| **Режим работы** | Постоянно опрашивает Redis на наличие задач |
| **Задачи** | `send_notification` (уведомления в чаты), `update_broken_links` (обновление реквизитов) |
| **Запуск** | `uv run arq app.tasks.worker.WorkerSettings` |
| **Retry** | Максимум 3 попытки для каждой задачи |
| **Зависимости** | Redis (очередь задач), PostgreSQL (чтение данных), Bot instance (отправка сообщений) |

### PostgreSQL 15

| Параметр | Значение |
|----------|----------|
| **Назначение** | Основное хранилище данных |
| **Содержит** | 7 таблиц — `users`, `orders`, `rates`, `global_settings`, `notification_chats`, `audit_logs`, `api_tokens` |
| **Миграции** | Управляются через Alembic |
| **Доступ** | Подключение через `asyncpg` драйвер |
| **Healthcheck** | `pg_isready -U usdt_bot` каждые 5 секунд |

### Redis 7

| Параметр | Значение |
|----------|----------|
| **Назначение** | Кеш и очередь задач |
| **Кеш (DB 0)** | Флаги `bot_enabled`, `buy_enabled`, `sell_enabled` с TTL=30 сек |
| **Очередь (DB 1)** | База данных 1 для ARQ (`ARQ_REDIS_URL`) |
| **Healthcheck** | `redis-cli ping` каждые 5 секунд |

---

## Слои приложения

```
┌─────────────────────────────────────────────┐
│  handlers/                                  │
│  Aiogram handlers + FSM                     │
│  Получение сообщений, отправка ответов      │
├─────────────────────────────────────────────┤
│  middlewares/                               │
│  DBSession, User, BotStatus, RoleGuard      │
│  Перехват и валидация запросов              │
├─────────────────────────────────────────────┤
│  services/                                  │
│  Бизнес-логика                              │
│  EncryptionService, UserService,            │
│  OrderService, RateService,                 │
│  SettingsService, NotificationService,      │
│  AuditService                               │
├─────────────────────────────────────────────┤
│  repositories/                               │
│  Доступ к данным                            │
│  SQLAlchemy queries, базовый CRUD           │
├─────────────────────────────────────────────┤
│  models/                                    │
│  SQLAlchemy ORM модели                      │
│  User, Order, Rate, GlobalSettings,         │
│  NotificationChat, AuditLog, APIToken       │
└─────────────────────────────────────────────┘
```

### Handlers (Обработчики)

Верхний слой — приём и обработка Telegram-обновлений. Разделены по ролям:

| Каталог | Назначение |
|---------|------------|
| `start.py` | `/start`, регистрация, главное меню |
| `client/` | Покупка, продажа, курсы, отмена, битая ссылка, поддержка |
| `operator/` | Активные заявки, завершение, статистика |
| `admin/` | Смена курса, реквизитов, управление флагами, чатами, ролями |
| `common/` | Общие обработчики (битая ссылка, календарь, глобальная отмена FSM) |

Каждый handler использует FSM (Finite State Machine) для многошаговых сценариев.

---

## Middleware (Единственный источник истины)

> **Важно:** Порядок и логика middleware описаны ТОЛЬКО в этом файле.
> При упоминании в modules.md используйте ссылку на этот раздел.

### Telegram Bot Middleware (Aiogram)

**Правило регистрации:** Первый зарегистрированный middleware — самый внешний (outermost), последний — самый внутренний (innermost).

**Порядок выполнения (от outermost к innermost):**

```
Request → ThrottlingMiddleware (outermost)
        → DBSessionMiddleware
        → UserMiddleware
        → BotStatusMiddleware
        → RoleGuardMiddleware (innermost)
        → Handler
```

| Порядок | Middleware | Файл | Назначение |
|---------|-----------|------|------------|
| 1 | `ThrottlingMiddleware` | `app/middlewares/throttling.py` | Защита от спама. Лимиты: команды 1/сек, FSM 5/мин, сообщения 3/сек. Должен быть outermost — блокирует спам до любой обработки. |
| 2 | `DBSessionMiddleware` | `app/middlewares/db_session.py` | Инъекция `AsyncSession` в `data["session"]`. Открывает сессию перед обработкой, коммитит после, откатывает при ошибке. |
| 3 | `UserMiddleware` | `app/middlewares/user_middleware.py` | Загрузка пользователя из БД в `data["user"]`. Блокирует заблокированных (`is_blocked=True`) клиентов. Зависит от `session`. |
| 4 | `BotStatusMiddleware` | `app/middlewares/bot_status.py` | Проверка флага `bot_enabled` (кеш Redis TTL=30с). Блокирует клиентов когда бот отключён. Операторы/админы проходят всегда. Зависит от `user`. |
| 5 | `RoleGuardMiddleware` | `app/middlewares/role_guard.py` | Проверка прав по ролям через `required_role`. Зависит от `user`. |

### REST API Middleware (aiohttp)

**Порядок выполнения:**

```
Request → logging → cors → rate_limit → login_rate_limit → auth → ip_whitelist → error_handler
```

| Порядок | Middleware | Файл | Назначение |
|---------|-----------|------|------------|
| 1 | `logging_middleware` | `app/api/middleware.py` | Логирование HTTP запросов с длительностью |
| 2 | `cors_middleware` | `app/api/middleware.py` | CORS заголовки для кросс-доменных запросов |
| 3 | `rate_limit_middleware` | `app/api/middleware.py` | Rate limiting по IP (Redis, лимит из настроек) |
| 4 | `login_rate_limit_middleware` | `app/api/middleware.py` | Блокировка IP после 5 неудачных попыток логина |
| 5 | `auth_middleware` | `app/api/deps.py` | JWT аутентификация, загрузка пользователя |
| 6 | `ip_whitelist_middleware` | `app/api/middleware.py` | Проверка IP whitelist для админских эндпоинтов |
| 7 | `api_error_middleware` | `app/api/exceptions.py` | Централизованная обработка ошибок API |

---

## Паттерны взаимодействия

### Long Polling (Bot ↔ Telegram)

```
Telegram API  ←─ Long Polling ─→  Bot (Aiogram Dispatcher)
                                       │
                                        ├── Middleware chain
                                        │   ├── ThrottlingMiddleware (outermost)
                                        │   ├── DBSessionMiddleware
                                        │   ├── UserMiddleware
                                        │   ├── BotStatusMiddleware
                                        │   └── RoleGuardMiddleware (innermost)
                                       │
                                       └── Handler
                                           ├── Service (бизнес-логика)
                                           ├── Repository (данные)
                                           └── Bot API (ответ)
```

### ARQ Tasks (Bot → Redis → Worker)

```
Bot (handler)  ──enqueue──→  Redis (ARQ queue, DB 1)  ──dequeue──→  ARQ Worker
                                                                               │
                                                                               ├── send_notification
                                                                               │   └── Bot API → NotificationChats
                                                                               │
                                                                               └── update_broken_links
                                                                                   └── Bot API → edit_message (клиенты)
```

**Когда используются ARQ-задачи:**

| Событие | Задача |
|---------|--------|
| Создание заявки | Уведомление в чаты о новом заказе |
| Жалоба на ссылку | Уведомление в чаты о проблеме |
| Завершение заявки | Уведомление клиента и чатов |
| Назначение роли | Уведомление пользователя и чатов |
| Смена реквизитов | Массовое обновление сообщений с битыми ссылками |

---

## Docker Compose развёртывание

### Порядок запуска

1. `postgres` и `redis` запускаются первыми
2. Healthcheck проверяет их готовность
3. `bot` и `arq-worker` запускаются только после `service_healthy`
4. Все сервисы используют `restart: unless-stopped`

### Volumes

- `pgdata` — персистентное хранилище PostgreSQL (`/var/lib/postgresql/data`)

### Сеть

Все сервисы находятся в одной Docker-сети. Взаимодействие по именам сервисов: `postgres:5432`, `redis:6379`.

---

## Обработка ошибок

### Telegram API

| Ситуация | Обработка |
|----------|-----------|
| Отправка сообщений | Retry 3 раза через ARQ с exponential backoff |
| Чат недоступен (Forbidden, BadRequest) | Логирование ошибки, без удаления чата из БД |
| Rate limits (429) | ARQ retry с задержкой |

### База данных

| Ситуация | Обработка |
|----------|-----------|
| Ошибка в handler | DBSessionMiddleware автоматически откатывает транзакцию |
| Потеря соединения | SQLAlchemy pool pre-ping |

### Graceful Shutdown

| Этап | Действие |
|------|----------|
| SIGTERM/SIGINT | `GracefulShutdown` класс управляет остановкой |
| Порядок | stop_polling → close bot session → dispose engine |
| ARQ Worker | Корректно завершает текущую задачу перед остановкой |

### FSM Attempt Limits

| Параметр | Значение |
|----------|----------|
| Функция | `check_fsm_attempts()` в `app/utils/helpers.py` |
| Лимит | 3 попытки на каждое FSM-поле |
| При превышении | `state.clear()`, сообщение "Слишком много ошибок. Операция отменена." |
| Применяется к | `OrderBuyStates`, `OrderSellStates`, `ChangeBuyRateStates`, `ChangeSellRateStates`, `AssignOperatorStates`, `AssignAdminStates` |

### Глобальная обработка ошибок

| Элемент | Реализация |
|---------|------------|
| Handler | `@dp.errors()` перехватывает все необработанные исключения |
| Логирование | Ошибка с full traceback |
| Уведомление пользователя | Сообщение или callback alert |
| TelegramAPIError | Игнорируется при отправке уведомления об ошибке |

---

## См. также

- **Структура файлов:** `modules.md`
- **Схема БД:** `database.md`
- **FSM-сценарии:** `scenarios.md`
- **Роли и права:** `roles.md`
- **Технологии:** `stack.md`
