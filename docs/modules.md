# Структура проекта

```
app/
├── config.py           # Pydantic Settings — все переменные окружения
├── bot.py              # Dispatcher, роутеры, middleware registration
├── main.py             # Entry point — запуск Long Polling + health server
├── health.py           # HTTP healthcheck endpoints (/, /health, /ready, /live)
│
├── api/                # REST API модуль
│   ├── __init__.py
│   ├── app.py          # aiohttp Application, middleware, routes
│   ├── deps.py         # Dependencies: get_session, get_current_user
│   ├── auth.py         # JWT generation, verification, refresh
│   ├── middleware.py   # AuthMiddleware, RateLimitMiddleware, IPWhitelistMiddleware, CORS
│   ├── exceptions.py   # APIException, error handlers
│   ├── routers/
│   │   ├── auth.py     # POST /api/v1/auth/login, /refresh, /logout
│   │   ├── users.py    # GET/POST/PATCH /api/v1/users
│   │   ├── orders.py   # GET/PATCH /api/v1/orders
│   │   ├── rates.py    # GET/POST /api/v1/rates
│   │   ├── settings.py # GET/PATCH /api/v1/settings
│   │   └── statistics.py # GET /api/v1/statistics
│   └── schemas/
│       ├── auth.py     # LoginRequest, TokenResponse, RefreshRequest
│       ├── user.py     # UserResponse, UserListResponse, RoleUpdateRequest
│       ├── order.py    # OrderResponse, OrderListResponse, OrderStatusUpdate
│       ├── rate.py     # RateResponse, RateCreateRequest
│       ├── settings.py # SettingsResponse, SettingsUpdateRequest
│       └── statistics.py # StatisticsResponse
│
├── database/
│   ├── engine.py       # AsyncEngine, AsyncSessionMaker
│   ├── base.py         # DeclarativeBase
│   ├── types.py        # JSONBCompat (PostgreSQL JSONB / SQLite JSON)
│   └── models/         # ORM модели
│       ├── user.py, order.py, rate.py
│       ├── global_settings.py
│       ├── notification_chat.py, audit_log.py
│       └── api_token.py # APIToken для refresh токенов
│
├── repositories/       # Слой доступа к данным
│   ├── base.py         # Generic CRUD (get_by_id, get_all, create, update, delete)
│   ├── user_repo.py    # get_by_telegram_id, exists_by_telegram_id
│   ├── order_repo.py   # get_active_orders, get_statistics, get_broken_link_orders
│   ├── rate_repo.py    # get_current_rate, get_rate_history
│   ├── settings_repo.py # get/set по ключу
│   ├── notification_repo.py # get_all_chat_ids
│   ├── audit_repo.py   # log
│   └── api_token_repo.py # manage refresh tokens
│
├── services/           # Бизнес-логика
│   ├── encryption.py   # AES-256-CBC шифрование (encrypt/decrypt)
│   ├── user_service.py # get_or_create, set_role, is_super_admin
│   ├── order_service.py # create_order, cancel_order, complete_order, get_statistics
│   ├── rate_service.py # get_current_rate, set_rate
│   ├── settings_service.py # is_bot_enabled, get_payment_link, set_payment_link
│   ├── notification_service.py # send_to_all_chats, notify_*
│   └── audit_service.py # log
│
├── handlers/           # Aiogram handlers
│   ├── start.py        # /start — регистрация, меню по роли
│   ├── client/         # buy.py, sell.py, rates.py, cancel_order.py, support.py
│   ├── operator/       # active_orders.py, complete_order.py, statistics.py
│   ├── admin/          # change_rate.py, change_links.py, toggle_flags.py,
│   │                   # notification_chats.py, assign_roles.py
│   └── common/         # broken_link.py, cancel.py (глобальная отмена FSM), calendar.py
│
├── middlewares/
│   ├── throttling.py        # Антиспам (1/сек команды, 5/мин FSM, 3/сек сообщения)
│   ├── db_session.py       # Инъекция AsyncSession + обработка потери БД
│   ├── user_middleware.py  # Загрузка user + проверка is_blocked
│   ├── bot_status.py       # Проверка bot_enabled (Redis кеш 30 сек)
│   └── role_guard.py       # RoleFilter — проверка min_role
│
├── keyboards/
│   ├── client_kb.py    # ReplyKeyboard для клиента
│   ├── operator_kb.py  # ReplyKeyboard для оператора
│   ├── admin_kb.py     # ReplyKeyboard + inline-панель управления
│   ├── cancel_kb.py    # Клавиатура отмены + get_main_keyboard()
│   ├── calendar_kb.py  # Inline-календарь для выбора дат
│   └── inline_kb.py    # Inline-клавиатуры (пагинация, заявки, чаты)
│
├── fsm/                # FSM-состояния
│   ├── order_states.py     # OrderBuyStates, OrderSellStates
│   ├── statistics_states.py # StatisticsStates (waiting_start_date, waiting_end_date)
│   ├── rate_states.py      # ChangeRateStates
│   ├── links_states.py     # ChangeLinksStates
│   ├── role_states.py      # AssignRoleStates
│   └── support_states.py   # SupportStates
│
├── tasks/              # ARQ фоновые задачи
│   ├── worker.py       # WorkerSettings, RedisSettings
│   └── jobs.py         # send_notification, update_broken_links
│
└── utils/
    ├── formatting.py   # HTML-экранирование для Telegram
    ├── pagination.py   # Утилиты пагинации
    ├── helpers.py      # get_settings_flags, check_fsm_attempts, reset_fsm_attempts
    ├── redis.py        # Redis connection pool, cached flags
    └── logging_config.py # JSON logging formatter
```

---

## Слои и зависимости

```
handlers/ → services/ → repositories/ → models/
    │           │
    └───────────┴──→ middlewares/ (предварительная обработка)
    │
    └──→ keyboards/ (UI)
    │
    └──→ fsm/ (состояния)
    │
    └──→ tasks/ (ARQ jobs)
```

**Поток данных:**
1. Handler получает update от aiogram
2. Middleware: Throttling → DBSession → User → BotStatus → RoleGuard
3. Handler вызывает Service (бизнес-логика)
4. Service вызывает Repository (данные)
5. Repository работает с Model (ORM)
6. Handler отправляет ответ через Bot API или ставит ARQ-задачу

---

## Middleware: порядок выполнения

```
Request → ThrottlingMiddleware (outermost)
        → DBSessionMiddleware
        → UserMiddleware
        → BotStatusMiddleware
        → RoleGuardMiddleware (innermost)
        → Handler
```

**Важно:** 
- ThrottlingMiddleware должен быть первым (outermost), чтобы блокировать спам до любой обработки.
- DBSessionMiddleware должен быть вторым, чтобы все последующие middleware имели доступ к `session`.

---

## FSM-сценарии

| FSM | States | Назначение |
|-----|--------|------------|
| OrderBuyStates | waiting_amount, confirm_order | Покупка USDT |
| OrderSellStates | waiting_amount, confirm_order | Продажа USDT |
| StatisticsStates | waiting_start_date, waiting_end_date | Статистика за период |
| ChangeRateStates | waiting_new_rate | Смена курса |
| ChangeLinksStates | choosing_type, waiting_new_link | Смена реквизитов |
| AssignRoleStates | waiting_target_user | Назначение роли |
| SupportStates | waiting_message | Обращение в поддержку |

**Навигация:** Все FSM поддерживают кнопку «❌ Отмена» — при выходе восстанавливается основное меню по роли.

**Лимит попыток:** FSM с текстовым вводом ограничены 3 попытками (`check_fsm_attempts()`). После 3 ошибок — автоматическая отмена.

**Ввод дат:** Через inline-календарь (calendar_kb.py + handlers/common/calendar.py), не через текст.

---

## ARQ-задачи

| Задача | Триггер | Действие |
|--------|---------|----------|
| send_notification | Создание заявки, жалоба, назначение роли, завершение | Отправка сообщения в чат (max_tries=3, деактивация чата при ошибках) |
| update_broken_links | Смена реквизитов админом | Редактирование сообщений клиентов с битой ссылкой |

**Обработка ошибок send_notification:**
- `TelegramForbiddenError` — бот заблокирован → деактивация чата, уведомление SuperAdmin
- `TelegramNotFound` — чат не найден → деактивация чата, уведомление SuperAdmin
- Исчерпание попыток (max_tries=3) → деактивация чата, уведомление SuperAdmin

---

## Ключевые конфигурации

### config.py (Settings)

```python
BOT_TOKEN: str
DATABASE_URL: str
REDIS_URL: str = "redis://localhost:6379/0"
ENCRYPTION_KEY: str  # 64-char hex = 32 bytes AES-256
SUPER_ADMIN_TELEGRAM_ID: int
ORDERS_PER_PAGE: int = 5
ARQ_REDIS_URL: str = "redis://localhost:6379/1"
LOG_LEVEL: str = "INFO"
JSON_LOGS: bool = False
HEALTH_PORT: int = 8080
# API
API_SECRET_KEY: str
API_ACCESS_TOKEN_EXPIRE: int = 1800  # 30 мин
API_REFRESH_TOKEN_EXPIRE: int = 604800  # 7 дней
API_PORT: int = 8081
API_RATE_LIMIT: int = 100  # req/min per IP
API_CORS_ORIGINS: list[str] = []
API_ADMIN_IP_WHITELIST: list[str] = []
API_LOGIN_BLOCK_DURATION: int = 300  # 5 мин
```

### global_settings (ключи)

| Ключ | Значение | Назначение |
|------|----------|------------|
| bot_enabled | "1"/"0" | Глобальное включение бота |
| buy_enabled | "1"/"0" | Разрешена покупка |
| sell_enabled | "1"/"0" | Разрешена продажа |
| payment_link_buy | hex (зашифровано) | Реквизиты для покупки |
| payment_link_sell | hex (зашифровано) | Реквизиты для продажи |

---

## Enum-типы (PostgreSQL)

При объявлении `Enum()` в SQLAlchemy **всегда указывать `name=`** явно:

```python
# Правильно:
role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum, name="user_role"), ...)

# Неправильно (сгенерирует "roleenum"):
role: Mapped[RoleEnum] = mapped_column(Enum(RoleEnum), ...)
```

Имена: `user_role`, `order_type`, `order_status`, `rate_type`
