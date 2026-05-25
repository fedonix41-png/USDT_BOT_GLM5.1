# Архитектура проекта

## Обзор

Telegram-бот для обмена USDT построен по модульной архитектуре с чётким разделением слоёв. Система развёртывается через Docker Compose и состоит из четырёх основных компонентов.

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

- **Назначение:** Основной компонент — Telegram-бот на базе Aiogram 3.x.
- **Режим работы:** Long Polling (получение обновлений через `bot.get_updates()`). FastAPI webhook не используется.
- **Функции:** Приём и обработка сообщений, FSM, отправка ответов, регистрация пользователей, маршрутизация по ролям.
- **Запуск:** `uv run python -m app.main`
- **Зависимости:** PostgreSQL (через SQLAlchemy async), Redis (кеш флагов).

### ARQ Worker

- **Назначение:** Фоновый обработчик задач через очередь ARQ.
- **Режим работы:** Постоянно опрашивает Redis на наличие задач.
- **Задачи:** `send_notification` (уведомления в чаты), `update_broken_links` (обновление реквизитов у клиентов с битыми ссылками).
- **Запуск:** `uv run arq app.tasks.worker.WorkerSettings`
- **Retry:** Максимум 3 попытки для каждой задачи, затем логирование ошибки.
- **Зависимости:** Redis (очередь задач), PostgreSQL (чтение данных), Bot instance (отправка сообщений).

### PostgreSQL 15

- **Назначение:** Основное хранилище данных.
- **Содержит:** 6 таблиц — `users`, `orders`, `rates`, `global_settings`, `notification_chats`, `audit_logs`.
- **Миграции:** Управляются через Alembic. Первая миграция создаёт все таблицы, enum-типы и индексы.
- **Доступ:** Подключение через `asyncpg` драйвер и SQLAlchemy async engine.
- **Healthcheck:** `pg_isready -U usdt_bot` каждые 5 секунд, 5 попыток.

### Redis 7

- **Назначение:** Кеш и очередь задач.
- **Кеш:** Флаги `bot_enabled`, `buy_enabled`, `sell_enabled` кешируются на 30 секунд для снижения нагрузки на PostgreSQL. Middleware проверяет кеш перед обращением к БД.
- **Очередь:** База данных 1 (`ARQ_REDIS_URL`) используется ARQ для хранения задач. База данных 0 (`REDIS_URL`) используется для кеша.
- **Healthcheck:** `redis-cli ping` каждые 5 секунд, 5 попыток.

## Слои приложения

```
┌─────────────────────────────────────────────┐
│  handlers/                                  │
│  Aiogram handlers + FSM                     │
│  Получение сообщений, отправка ответов      │
├─────────────────────────────────────────────┤
│  middlewares/                                │
│  DBSession, BotStatus, RoleGuard            │
│  Перехват и валидация запросов              │
├─────────────────────────────────────────────┤
│  services/                                  │
│  Бизнес-логика                              │
│  EncryptionService, UserService,            │
│  OrderService, RateService,                 │
│  SettingsService, NotificationService,       │
│  AuditService                               │
├─────────────────────────────────────────────┤
│  repositories/                               │
│  Доступ к данным                            │
│  SQLAlchemy queries, базовый CRUD           │
├─────────────────────────────────────────────┤
│  models/                                     │
│  SQLAlchemy ORM модели                      │
│  User, Order, Rate, GlobalSettings,         │
│  NotificationChat, AuditLog                 │
└─────────────────────────────────────────────┘
```

### Handlers (Обработчики)

Верхний слой — приём и обработка Telegram-обновлений. Разделены по ролям:

- `start.py` — `/start`, регистрация, главное меню
- `client/` — покупка, продажа, курсы, отмена, битая ссылка, поддержка
- `operator/` — активные заявки, завершение, статистика
- `admin/` — смена курса, реквизитов, управление флагами, чатами, ролями
- `common/` — общие обработчики (битая ссылка)

Каждый handler использует FSM (Finite State Machine) для многошаговых сценариев.

### Middlewares (Промежуточные слои)

Выполняются перед обработчиками, обеспечивают сквозную логику. **Порядок регистрации имеет значение:** первый зарегистрованный middleware — самый внешний (outermost), последний — самый внутренний (innermost, ближе к handler).

Порядок выполнения (от outermost к innermost):
1. **ThrottlingMiddleware** — защита от спама. Лимиты: команды 1/сек, FSM 5/мин, обычные сообщения 3/сек. Должен быть outermost, чтобы блокировать спам до любой обработки.
2. **DBSessionMiddleware** — инъекция `AsyncSession` в `data["session"]` для каждого handler. Открывает сессию перед обработкой, коммитит после, откатывает при ошибке. Обрабатывает потерю соединения с БД, отправляя пользователю уведомление.
3. **UserMiddleware** — загрузка пользователя из БД в `data["user"]`. Проверяет `is_blocked` и блокирует заблокированных клиентов. Зависит от `session` (от DBSessionMiddleware).
4. **BotStatusMiddleware** — проверка флага `bot_enabled` (с кешем на 30 сек). Если бот отключён и пользователь — клиент, перехватывает сообщение с ответом «Бот временно недоступен». Зависит от `user` (от UserMiddleware).
5. **RoleGuardMiddleware** — проверка прав пользователя. Используется как фильтр на роутерах. Зависит от `user` (от UserMiddleware).

### Services (Сервисы)

Бизнес-логика, не зависящая от Telegram API:

- **EncryptionService** — AES-256-CBC шифрование/дешифрование реквизитов
- **UserService** — регистрация, роли, проверка super_admin
- **OrderService** — создание/отмена/завершение заявок, статистика
- **RateService** — текущий курс, смена курса, история
- **SettingsService** — флаги и реквизиты (с шифрованием)
- **NotificationService** — отправка уведомлений в чаты через ARQ
- **AuditService** — логирование действий в audit_logs

### Repositories (Репозитории)

Слой доступа к данным. Базовый репозиторий `BaseRepository` предоставляет generic CRUD-операции. Специфичные репозитории расширяют его:

- `user_repo.py` — поиск по telegram_id, проверка роли
- `order_repo.py` — фильтрация по статусу, пагинация, агрегация статистики
- `rate_repo.py` — последний курс по типу, история изменений
- `settings_repo.py` — get/set по ключу в global_settings
- `notification_repo.py` — список чатов
- `audit_repo.py` — запись логов

### Models (Модели)

SQLAlchemy ORM модели, отображающие структуру БД:

- `User` — пользователи с ролями
- `Order` — заявки на покупку/продажу
- `Rate` — история курсов
- `GlobalSettings` — ключ-значение (флаги, реквизиты)
- `NotificationChat` — чаты для уведомлений
- `AuditLog` — аудит действий

## Паттерны взаимодействия

### Long Polling (Bot ↔ Telegram)

Бот периодически вызывает `bot.get_updates()` для получения новых сообщений и callback-запросов. Aiogram Dispatcher маршрутизирует обновления по зарегистрированным handlers.

```
Telegram API  ←─ Long Polling ─→  Bot (Aiogram Dispatcher)
                                      │
                                       ├── Middleware chain
                                       │   ├── DBSessionMiddleware (outermost)
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

Асинхронные задачи ставятся в очередь через Redis и обрабатываются ARQ Worker'ом:

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

1. Создание заявки — уведомление в чаты о новом заказе
2. Жалоба на ссылку — уведомление в чаты о проблеме
3. Завершение заявки — уведомление клиента и чатов
4. Назначение роли — уведомление пользователя и чатов
5. Смена реквизитов — массовое обновление сообщений с битыми ссылками

### Database Access (Bot/Worker → PostgreSQL)

Все обращения к PostgreSQL идут через SQLAlchemy async engine с пулом соединений:

```
Bot / ARQ Worker  ──→  AsyncSession  ──→  AsyncEngine  ──→  asyncpg  ──→  PostgreSQL
```

## Docker Compose развёртывание

### Конфигурация сервисов

```yaml
services:
  postgres:        # БД, healthcheck pg_isready
  redis:           # Кеш + очередь, healthcheck redis-cli ping
  bot:             # Основной бот, depends_on postgres+redis (healthy)
  arq-worker:      # Фоновый воркер, depends_on redis+postgres (healthy)
```

### Порядок запуска

1. `postgres` и `redis` запускаются первыми
2. Healthcheck проверяет их готовность
3. `bot` и `arq-worker` запускаются только после `service_healthy`
4. Все сервисы используют `restart: unless-stopped`

### Volumes

- `pgdata` — персистентное хранилище PostgreSQL (`/var/lib/postgresql/data`)

### Сеть

Все сервисы находятся в одной Docker-сети по умолчанию. Взаимодействие по именам сервисов: `postgres:5432`, `redis:6379`.

## Обработка ошибок

### Telegram API

- При отправке сообщений (уведомления) — retry 3 раза через ARQ с exponential backoff
- Если чат недоступен (Forbidden, BadRequest) — логировать ошибку, не удалять чат из БД
- Rate limits (429) — ARQ retry с задержкой

### База данных

- DBSessionMiddleware автоматически откатывает транзакцию при ошибке в handler
- Повторные попытки подключения через SQLAlchemy pool pre-ping

### Graceful Shutdown

- Обработка SIGTERM/SIGINT: `GracefulShutdown` класс управляет остановкой
- Порядок: stop_polling → close bot session → dispose engine
- ARQ Worker корректно завершает текущую задачу перед остановкой

### FSM Attempt Limits

- `check_fsm_attempts()` helper в `app/utils/helpers.py` — инкрементирует счётчик попыток
- Лимит: 3 попытки на каждое FSM-поле
- При превышении: `state.clear()`, сообщение "Слишком много ошибок. Операция отменена."
- Применяется к: `OrderBuyStates`, `OrderSellStates`, `ChangeBuyRateStates`, `ChangeSellRateStates`, `AssignOperatorStates`, `AssignAdminStates`

### Глобальная обработка ошибок

- `@dp.errors()` handler перехватывает все необработанные исключения
- Логирование ошибки с full traceback
- Уведомление пользователя: сообщение или callback alert
- Игнорирование TelegramAPIError при отправке уведомления об ошибке
